"""Run control: the state machine over a background solve, and what it read back."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, TypeAlias

from nanopnp.core.errors import EXIT_OK, EXIT_UNEXPECTED
from nanopnp.gui.convergence import ConvergenceModel
from nanopnp.gui.solver import (
    Cancelled,
    Failed,
    Finished,
    Iteration,
    Produced,
    Progress,
    RunEvent,
    Rung,
    RunRequest,
    SolverProcess,
    Stage,
    Started,
)
from nanopnp.io.manifest import DEVIATIONS_GROUP, MANIFEST_FILENAME
from nanopnp.pipeline.run import RUN_RECORD_FILENAME

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from collections.abc import Iterable, Mapping

__all__ = [
    "DEVIATIONS_GROUP",
    "RunModel",
    "RunOutcome",
    "RunState",
    "run_outcome",
]

RunState: TypeAlias = Literal["idle", "running", "finished", "failed", "cancelled"]

RecordValue: TypeAlias = Any


@dataclass(frozen=True)
class RunOutcome:
    directory: Path
    quantities: Mapping[str, RecordValue]
    deviations: Mapping[str, RecordValue]
    stages: tuple[Mapping[str, RecordValue], ...]
    files: tuple[str, ...]


def run_outcome(directory: str | Path) -> RunOutcome:
    root = Path(directory)
    record_path = root / RUN_RECORD_FILENAME
    manifest_path = root / MANIFEST_FILENAME
    for path in (record_path, manifest_path):
        if not path.is_file():
            raise FileNotFoundError(f"{path} is not there, so this run has no record to show")
    record: dict[str, RecordValue] = json.loads(record_path.read_text(encoding="utf-8"))
    manifest: dict[str, RecordValue] = json.loads(manifest_path.read_text(encoding="utf-8"))
    # The eight groups sit at the manifest's top level, beside schema, created_at, hash and case.
    deviations = manifest.get(DEVIATIONS_GROUP)
    if not isinstance(deviations, dict):
        raise ValueError(
            f"{manifest_path} carries no {DEVIATIONS_GROUP!r} group; §5.3.3 requires all eight, "
            "and showing a number without the switches it was produced under would attribute "
            "it to the validated model"
        )
    return RunOutcome(
        directory=root,
        quantities=dict(record.get("quantities", {})),
        deviations=dict(deviations),
        stages=tuple(record.get("stages", ())),
        files=tuple(str(name) for name in record.get("files", ())),
    )


@dataclass
class RunModel:
    state: RunState = "idle"
    fraction: float = 0.0
    stage: Stage | None = None
    log: tuple[str, ...] = ()
    exit_code: int = EXIT_OK
    diagnosis: str = ""
    directory: Path | None = None
    convergence: ConvergenceModel = field(default_factory=ConvergenceModel)
    produced: tuple[Produced, ...] = ()
    walked: tuple[str, ...] = ()

    def consume(self, events: Iterable[RunEvent]) -> None:
        for event in events:
            self._apply(event)

    def _apply(self, event: RunEvent) -> None:
        if isinstance(event, Started):
            self.state = "running"
            self.fraction = 0.0
            self.stage = None
            self.exit_code = EXIT_OK
            self.diagnosis = ""
            self.directory = None
            self.produced = ()
            self.walked = ()
            self.convergence.reset()
            self._say(f"running {event.case}")
        elif isinstance(event, Stage):
            self.stage = event
            self.walked = (*self.walked, event.name)
            self._say(f"stage {event.index + 1} of {event.total}: {event.name}")
        elif isinstance(event, Produced):
            self.produced = (*self.produced, event)
            self._say(
                f"{event.name}: {event.hash[:12]} {'from the store' if event.cached else 'stored'}"
            )
        elif isinstance(event, Rung):
            # Not logged: the solve already reports the rung through progress.
            self.convergence.rung(
                event.name,
                event.stage,
                event.index,
                event.total,
                event.reporting,
                event.tolerance,
            )
        elif isinstance(event, Iteration):
            self.convergence.step(
                event.iteration,
                event.residual,
                event.update,
                event.damping,
                event.trials,
                event.forced,
            )
        elif isinstance(event, Progress):
            # Monotone by enforcement: a late event from a superseded stage must not move the bar
            # back.
            self.fraction = max(self.fraction, min(1.0, max(0.0, event.fraction)))
            self._say(event.message)
        elif isinstance(event, Finished):
            self.state = "finished"
            self.fraction = 1.0
            self.exit_code = event.exit_code
            self.directory = Path(event.directory)
            self._settle(finished=True)
            self._say(f"finished: {event.directory}")
        elif isinstance(event, Failed):
            self.state = "failed"
            self.exit_code = event.exit_code
            self.diagnosis = event.message
            self._settle(finished=False)
            self._say(f"failed ({event.error}, exit {event.exit_code}): {event.message}")
        elif isinstance(event, Cancelled):
            self.state = "cancelled"
            self.exit_code = event.exit_code
            self.diagnosis = event.where
            self._settle(finished=False)
            self._say(f"cancelled: {event.where}")
        else:
            # Named and not a trailing else, which once marked the first Newton step of every run
            # cancelled.
            raise TypeError(
                f"{type(event).__name__} is a RunEvent this model does not apply; a variant "
                "added to the union needs a branch here rather than a default"
            )

    def _settle(self, *, finished: bool) -> None:
        if "solve" not in self.walked and not self.convergence.bands:
            return
        self.convergence.settle(finished=finished)
        self.convergence.count_omitted()

    def _say(self, message: str) -> None:
        self.log = (*self.log, message)

    @property
    def settled(self) -> bool:
        return self.state in ("finished", "failed", "cancelled")

    def outcome(self) -> RunOutcome | None:
        if self.state != "finished" or self.directory is None:
            return None
        return run_outcome(self.directory)


@dataclass
class RunControl:
    model: RunModel = field(default_factory=RunModel)
    process: SolverProcess | None = None

    def start(
        self, case: str | Path, *, store: str | Path | None = None, upto: str | None = None
    ) -> None:
        if self.process is not None and self.process.running:
            raise RuntimeError("a run is already in flight; cancel it before starting another")
        self.model = RunModel()
        self.process = SolverProcess(
            RunRequest(case=str(case), store=None if store is None else str(store), upto=upto)
        )
        self.process.start()

    def poll(self) -> RunModel:
        if self.process is not None:
            # Liveness before the queue, so that a child which posts its last event and
            # exits between the two reads is not mistaken for a silent one.
            alive = self.process.running
            self.model.consume(self.process.drain())
            if not alive and not self.model.settled:
                self.model.consume(
                    (
                        Failed(
                            exit_code=EXIT_UNEXPECTED,
                            error="ChildExited",
                            message=(
                                f"the run process exited with status {self.process.exit_code} "
                                "without reporting a result (killed, out of memory, or a fault "
                                "in a compiled library)"
                            ),
                        ),
                    )
                )
        return self.model

    def cancel(self) -> None:
        if self.process is not None:
            self.process.cancel()

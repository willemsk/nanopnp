"""Run control: the state machine over a background solve."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Literal, TypeAlias

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
    SolverProcess,
    Stage,
    Started,
)

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from collections.abc import Iterable

__all__ = [
    "RunModel",
    "RunState",
]

RunState: TypeAlias = Literal["idle", "running", "finished", "failed", "cancelled"]


@dataclass
class RunModel:
    """The run panel's state; every transition happens in :meth:`consume`."""

    state: RunState = "idle"
    fraction: float = 0.0
    stage: Stage | None = None
    rung: Rung | None = None
    log: tuple[str, ...] = ()
    exit_code: int = EXIT_OK
    diagnosis: str = ""
    directory: Path | None = None
    convergence: ConvergenceModel = field(default_factory=ConvergenceModel)
    produced: tuple[Produced, ...] = ()
    walked: tuple[str, ...] = ()

    def consume(self, events: Iterable[RunEvent]) -> None:
        """Apply every event, in order."""
        for event in events:
            self._apply(event)

    def _apply(self, event: RunEvent) -> None:
        if isinstance(event, Started):
            self.state = "running"
            self.fraction = 0.0
            self.stage = None
            self.rung = None
            self.exit_code = EXIT_OK
            self.diagnosis = ""
            self.directory = None
            self.produced = ()
            self.walked = ()
            self.convergence.reset()
            self._say(f"running {event.case}")
        elif isinstance(event, Stage):
            self.stage = event
            self.rung = None
            self.walked = (*self.walked, event.name)
            self._say(f"stage {event.index + 1} of {event.total}: {event.name}")
        elif isinstance(event, Produced):
            self.produced = (*self.produced, event)
            self._say(
                f"{event.name}: {event.hash[:12]} {'from the store' if event.cached else 'stored'}"
            )
        elif isinstance(event, Rung):
            # Not logged: the solve already reports the rung through progress.
            self.rung = event
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

    def progress_line(self) -> str:
        """Return the running walk's stage and rung, or an empty string unless it runs."""
        if self.state != "running" or self.stage is None:
            return ""
        line = f"stage {self.stage.index + 1} of {self.stage.total}: {self.stage.name}"
        if self.rung is not None:
            line += f", rung {self.rung.index + 1} of {self.rung.total}"
        return line

    @property
    def settled(self) -> bool:
        """Whether the run reached one of its three terminal states."""
        return self.state in ("finished", "failed", "cancelled")


@dataclass
class RunControl:
    """A :class:`RunModel` and the solver process feeding it: poll and cancel."""

    model: RunModel = field(default_factory=RunModel)
    process: SolverProcess | None = None

    def poll(self) -> RunModel:
        """Drain the child's events into the model and return it."""
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
        """Ask the running solve to stop at its next cancellation check."""
        if self.process is not None:
            self.process.cancel()

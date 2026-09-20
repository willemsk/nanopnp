"""Run control: the state machine over a background solve, and what it read back.

The shell's run panel is a projection of this module (IF-09, FR-27). Like
:mod:`nanopnp.gui.case_model` it imports no PySide6 and no stage, which is what
lets the behaviour of the panel — the fraction, the stage, the log, the outcome
and the diagnosis — be asserted on every matrix job rather than on whichever ones
have a working Qt.

**The fraction is monotone, and the model enforces it rather than trusting it.**
:class:`~nanopnp.core.stages.Progress` promises monotone in [0, 1] ending at 1,
and :func:`~nanopnp.core.stages.report` clamps the range. It does not clamp the
*order*, and a queue drained after a cancellation can hand over a late event from
a stage that has already been superseded. A bar that went backwards would be
reporting the transport rather than the run, so the model keeps the maximum.

**A failure is diagnosed once.** The §3.1 exit class arrives on the event, from
:func:`nanopnp.cli.errors.classify` in the child; this module names it and shows
the QR-12 diagnostic the gate already wrote, and never re-derives either.

**The result is read from the run directory**, not carried through the queue. The
run directory is the record (§5.3.3) — ``manifest.json``, ``case.yaml`` and the
run record — so a result panel that read anything else would be showing something
the reproduction check could not reconstruct.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, TypeAlias

from nanopnp.cli.errors import EXIT_OK
from nanopnp.gui.solver import (
    Failed,
    Finished,
    Progress,
    RunEvent,
    RunRequest,
    SolverProcess,
    Stage,
    Started,
)
from nanopnp.io.manifest import GROUPS, MANIFEST_FILENAME
from nanopnp.io.run import RUN_RECORD_FILENAME

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from collections.abc import Iterable, Mapping

DEVIATIONS_GROUP = GROUPS[-1]
"""The Deviations group's key, taken from the manifest's own list of the eight
groups of §5.3.3 rather than written out again here."""

__all__ = [
    "DEVIATIONS_GROUP",
    "RunModel",
    "RunOutcome",
    "RunState",
    "run_outcome",
]

RunState: TypeAlias = Literal["idle", "running", "finished", "failed", "cancelled"]
"""Where a run is. The three terminal states are distinct on purpose: a cancelled
run wrote nothing and nothing is wrong with the case (§5.3.2), which is not what
a failed one says."""

RecordValue: TypeAlias = Any
"""One value out of a run record or a manifest: a string, a number, a nested
block of them. The files are JSON and this is the union a reader sees (the house
convention of :mod:`nanopnp.core.typing`)."""


@dataclass(frozen=True)
class RunOutcome:
    """What a finished run left in its run directory (§5.3.3).

    Parameters
    ----------
    directory
        The run directory.
    quantities
        The stage-11 scalars, as the run record holds them. Empty for a run that
        stopped before stage 11 — which is not a run whose numbers were zero.
    deviations
        The manifest's Deviations group: every switch set away from the
        validated default, and every departure a stage found in its inputs
        (FR-25). Shown beside the numbers because a number produced by a
        deviating configuration is not the validated model's number.
    stages
        One record per stage that ran, in order, with its hash and whether the
        store already held it.
    files
        Everything stage 12 wrote.
    """

    directory: Path
    quantities: Mapping[str, RecordValue]
    deviations: Mapping[str, RecordValue]
    stages: tuple[Mapping[str, RecordValue], ...]
    files: tuple[str, ...]


def run_outcome(directory: str | Path) -> RunOutcome:
    """Read a run directory back.

    Parameters
    ----------
    directory
        A directory holding ``run.json`` and ``manifest.json``.

    Returns
    -------
    RunOutcome
        The scalars and the deviations, for a result panel.

    Raises
    ------
    FileNotFoundError
        If either file is absent, naming it. A result panel showing a run whose
        record is not there would be showing the previous run's numbers.
    ValueError
        If the manifest carries no Deviations group. §5.3.3 requires all eight
        groups, a group no stage contributed carrying a status and a reason
        rather than being omitted — so an absent one is a manifest this build
        cannot read, and reporting "no deviations" for it would attribute the
        run to the validated model.
    """
    root = Path(directory)
    record_path = root / RUN_RECORD_FILENAME
    manifest_path = root / MANIFEST_FILENAME
    for path in (record_path, manifest_path):
        if not path.is_file():
            raise FileNotFoundError(f"{path} is not there, so this run has no record to show")
    record: dict[str, RecordValue] = json.loads(record_path.read_text(encoding="utf-8"))
    manifest: dict[str, RecordValue] = json.loads(manifest_path.read_text(encoding="utf-8"))
    # The eight groups sit at the manifest's top level, beside ``schema``,
    # ``created_at``, ``hash`` and ``case`` (:meth:`~nanopnp.io.manifest.Manifest.document`).
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
    """The run panel's state: driven by events, and by nothing else.

    Every transition happens in :meth:`consume`, so the panel is a pure function
    of the event stream a test can write by hand.
    """

    state: RunState = "idle"
    fraction: float = 0.0
    stage: Stage | None = None
    log: tuple[str, ...] = ()
    exit_code: int = EXIT_OK
    diagnosis: str = ""
    directory: Path | None = None

    def consume(self, events: Iterable[RunEvent]) -> None:
        """Apply every event, in order."""
        for event in events:
            self._apply(event)

    def _apply(self, event: RunEvent) -> None:
        """Apply one event."""
        if isinstance(event, Started):
            self.state = "running"
            self.fraction = 0.0
            self.stage = None
            self.exit_code = EXIT_OK
            self.diagnosis = ""
            self.directory = None
            self._say(f"running {event.case}")
        elif isinstance(event, Stage):
            self.stage = event
            self._say(f"stage {event.index + 1} of {event.total}: {event.name}")
        elif isinstance(event, Progress):
            # Monotone by enforcement, not by trust: see the module docstring.
            self.fraction = max(self.fraction, min(1.0, max(0.0, event.fraction)))
            self._say(event.message)
        elif isinstance(event, Finished):
            self.state = "finished"
            self.fraction = 1.0
            self.exit_code = event.exit_code
            self.directory = Path(event.directory)
            self._say(f"finished: {event.directory}")
        elif isinstance(event, Failed):
            self.state = "failed"
            self.exit_code = event.exit_code
            self.diagnosis = event.message
            self._say(f"failed ({event.error}, exit {event.exit_code}): {event.message}")
        else:
            self.state = "cancelled"
            self.exit_code = event.exit_code
            self.diagnosis = event.where
            self._say(f"cancelled: {event.where}")

    def _say(self, message: str) -> None:
        """Append one line to the log."""
        self.log = (*self.log, message)

    @property
    def settled(self) -> bool:
        """Whether the run reached one of its three terminal states."""
        return self.state in ("finished", "failed", "cancelled")

    def outcome(self) -> RunOutcome | None:
        """Read the run directory back, or ``None`` if there is nothing to read.

        ``None`` for anything but a finished run: a cancelled run wrote no
        artefact and a failed one wrote no record, so there is nothing a result
        panel could honestly show.
        """
        if self.state != "finished" or self.directory is None:
            return None
        return run_outcome(self.directory)


@dataclass
class RunControl:
    """A :class:`RunModel` and the :class:`~nanopnp.gui.solver.SolverProcess` feeding it.

    The whole of it: start a run, poll it, cancel it. The shell's run widget
    owns one of these and holds no state of its own, which is what keeps the
    state machine testable without Qt.
    """

    model: RunModel = field(default_factory=RunModel)
    process: SolverProcess | None = None

    def start(self, case: str | Path, *, store: str | Path | None = None) -> None:
        """Spawn a run of a case file.

        Parameters
        ----------
        case
            The case **file**. §5.3.1 makes it the unit of reproducibility, so
            the shell saves before it runs and never runs a document held only
            in memory.
        store
            The artefact store's root, or ``None`` for the process default.

        Raises
        ------
        RuntimeError
            If a run is already in flight. One control, one run: draining two
            children into one state machine would interleave their fractions.
        """
        if self.process is not None and self.process.running:
            raise RuntimeError("a run is already in flight; cancel it before starting another")
        self.model = RunModel()
        self.process = SolverProcess(
            RunRequest(case=str(case), store=None if store is None else str(store))
        )
        self.process.start()

    def poll(self) -> RunModel:
        """Drain the child's events into the model and return it."""
        if self.process is not None:
            self.model.consume(self.process.drain())
        return self.model

    def cancel(self) -> None:
        """Ask the running solve to stop at its next cancellation check."""
        if self.process is not None:
            self.process.cancel()

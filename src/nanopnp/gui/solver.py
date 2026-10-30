"""The bridge between the shell and a solve: one spawned process, plain data both ways."""

from __future__ import annotations

import logging
import multiprocessing
import queue as queue_module
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, TypeAlias

from nanopnp.core.errors import EXIT_CANCELLED, EXIT_OK, classify

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from multiprocessing.process import BaseProcess
    from multiprocessing.queues import Queue
    from multiprocessing.synchronize import Event as EventType

logger = logging.getLogger(__name__)

__all__ = [
    "Cancelled",
    "EventCancel",
    "Failed",
    "Finished",
    "Iteration",
    "Produced",
    "Progress",
    "QueueArtefact",
    "QueueProgress",
    "QueueSolve",
    "QueueStage",
    "RunEvent",
    "RunRequest",
    "Rung",
    "SolverProcess",
    "Stage",
    "Started",
    "failure_event",
]


@dataclass(frozen=True)
class RunRequest:
    """Everything the solver child needs, as strings it re-resolves for itself.

    Parameters
    ----------
    upto
        The last stage to walk, or ``None`` for the whole pipeline.
    """

    case: str
    store: str | None = None
    upto: str | None = None


@dataclass(frozen=True)
class Started:
    """The child is up and about to read the case."""

    case: str
    store: str | None


@dataclass(frozen=True)
class Stage:
    """A pipeline stage is about to run."""

    name: str
    index: int
    total: int


@dataclass(frozen=True)
class Produced:
    """A stage's artefact is in the store, named by its schema and hash."""

    name: str
    schema: str
    hash: str
    cached: bool
    store: str


@dataclass(frozen=True)
class Rung:
    """A continuation rung is about to be solved.

    Parameters
    ----------
    reporting
        Whether the rung's solve reports Newton steps; a silent rung is not a failed one.
    """

    name: str
    stage: int
    index: int
    total: int
    reporting: bool
    tolerance: float


@dataclass(frozen=True)
class Iteration:
    """One accepted Newton step of the rung most recently announced."""

    iteration: int
    residual: float
    update: float
    damping: float
    trials: int
    forced: bool


@dataclass(frozen=True)
class Progress:
    """A completion fraction in [0, 1] and its caption, ending at 1."""

    fraction: float
    message: str


@dataclass(frozen=True)
class Finished:
    """The run completed and wrote its run directory."""

    directory: str
    exit_code: int = EXIT_OK


@dataclass(frozen=True)
class Failed:
    """The run raised, with the exit class the command line would return.

    Parameters
    ----------
    exit_code
        The §3.1 class of the exception: 3 the case, 4 a gate, 5 convergence, 1 unclassified.
    """

    exit_code: int
    error: str
    message: str


@dataclass(frozen=True)
class Cancelled:
    """The run stopped because the token was set, naming where it stopped."""

    where: str
    exit_code: int = EXIT_CANCELLED


RunEvent: TypeAlias = (
    Started | Stage | Produced | Rung | Iteration | Progress | Finished | Failed | Cancelled
)


@dataclass(frozen=True)
class QueueProgress:
    """A progress callback that posts onto a queue."""

    queue: Queue[RunEvent]

    def __call__(self, fraction: float, message: str) -> None:
        """Post a ``Progress`` event."""
        self.queue.put(Progress(fraction=float(fraction), message=str(message)))


@dataclass(frozen=True)
class QueueStage:
    """A stage callback that posts onto a queue."""

    queue: Queue[RunEvent]

    def __call__(self, name: str, index: int, total: int) -> None:
        """Post a ``Stage`` event."""
        self.queue.put(Stage(name=str(name), index=int(index), total=int(total)))


@dataclass(frozen=True)
class QueueArtefact:
    """An artefact callback that posts onto a queue."""

    queue: Queue[RunEvent]
    store: str

    def __call__(self, name: str, schema: str, hash: str, cached: bool) -> None:
        """Post a ``Produced`` event."""
        self.queue.put(
            Produced(
                name=str(name),
                schema=str(schema),
                hash=str(hash),
                cached=bool(cached),
                store=self.store,
            )
        )


@dataclass(frozen=True)
class QueueSolve:
    """A solve callback that posts onto a queue, with numbers kept as numbers."""

    queue: Queue[RunEvent]

    def rung(
        self, name: str, stage: int, index: int, total: int, reporting: bool, tolerance: float
    ) -> None:
        """Post one continuation rung."""
        self.queue.put(
            Rung(
                name=str(name),
                stage=int(stage),
                index=int(index),
                total=int(total),
                reporting=bool(reporting),
                tolerance=float(tolerance),
            )
        )

    def step(
        self,
        iteration: int,
        residual: float,
        update: float,
        damping: float,
        trials: int,
        forced: bool,
    ) -> None:
        """Post one accepted Newton step."""
        self.queue.put(
            Iteration(
                iteration=int(iteration),
                residual=float(residual),
                update=float(update),
                damping=float(damping),
                trials=int(trials),
                forced=bool(forced),
            )
        )


class EventCancel:
    """A cancel token over a :class:`multiprocessing.Event`, for crossing processes."""

    def __init__(self, event: EventType) -> None:
        self._event = event

    def cancel(self) -> None:
        """Ask the running stage to stop at its next check."""
        self._event.set()

    def cancelled(self) -> bool:
        """Return whether the stage should raise ``Cancelled``."""
        return self._event.is_set()


def failure_event(error: BaseException) -> Failed:
    """Return the :class:`Failed` event that one exception produces."""
    return Failed(
        exit_code=classify(error),
        error=type(error).__qualname__,
        message=str(error),
    )


def _worker(request: RunRequest, events: Queue[RunEvent], cancel: EventType) -> None:
    from nanopnp.api.case import Case
    from nanopnp.api.session import Session
    from nanopnp.core.stages import Cancelled as CancelledError
    from nanopnp.io.store import Store

    events.put(Started(case=request.case, store=request.store))
    try:
        # Resolved here rather than left to the Session, so the root every
        # ``Produced`` names is the one the walk wrote into.
        store = Store(Path(request.store)) if request.store is not None else Store()
        result = Session(store).run(
            Case.load(request.case),
            upto=request.upto,
            progress=QueueProgress(events),
            cancel=EventCancel(cancel),
            on_stage=QueueStage(events),
            on_solve=QueueSolve(events),
            on_artefact=QueueArtefact(events, str(store.root)),
        )
    except CancelledError as cancelled:
        events.put(Cancelled(where=str(cancelled)))
    except BaseException as error:
        # failure_event, not a copy: the Tier-1 test pinning the §3.1 codes calls it,
        # so the path that runs is the path tested.
        events.put(failure_event(error))
    else:
        events.put(Finished(directory=str(result.directory)))


@dataclass
class SolverProcess:
    """One background solve: start it, cancel it, drain what it has said.

    Parameters
    ----------
    request
        The case and the store, as plain strings.
    """

    request: RunRequest
    _process: BaseProcess | None = field(default=None, repr=False)
    _events: Queue[RunEvent] | None = field(default=None, repr=False)
    _cancel: EventType | None = field(default=None, repr=False)

    def start(self) -> None:
        """Spawn the child and begin the run; raise RuntimeError if already started."""
        if self._process is not None:
            raise RuntimeError(
                "this SolverProcess has already been started; construct another one rather "
                "than restarting it, or its first run's events would be drained into the second"
            )
        context = multiprocessing.get_context("spawn")
        self._events = context.Queue()
        self._cancel = context.Event()
        self._process = context.Process(
            target=_worker,
            args=(self.request, self._events, self._cancel),
            name=f"nanopnp-solve-{Path(self.request.case).stem}",
            daemon=True,
        )
        self._process.start()
        logger.info("solving %s in process %s", self.request.case, self._process.pid)

    def cancel(self) -> None:
        """Ask the child to stop at its next cancellation check; nothing is written."""
        if self._cancel is not None:
            self._cancel.set()

    def drain(self) -> tuple[RunEvent, ...]:
        """Return every event posted since the last call, oldest first."""
        if self._events is None:
            return ()
        found: list[RunEvent] = []
        while True:
            try:
                found.append(self._events.get_nowait())
            except queue_module.Empty:
                return tuple(found)

    @property
    def running(self) -> bool:
        """Whether the child is alive."""
        return self._process is not None and self._process.is_alive()

    @property
    def exit_code(self) -> int | None:
        """The child's process exit status, or ``None`` while it is running."""
        return None if self._process is None else self._process.exitcode

    def join(self, timeout: float | None = None) -> None:
        """Wait for the child to exit."""
        if self._process is not None:
            self._process.join(timeout)

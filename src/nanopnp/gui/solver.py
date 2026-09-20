"""The bridge between the shell and a solve: one spawned process, plain data both ways.

ADR-004 requires the solver to run in a background process so the interface stays
responsive and can be interrupted. This module is that process and its transport,
and nothing else: it imports no PySide6, so the state machine built on it
(:mod:`nanopnp.gui.run_model`) is testable on every matrix job rather than on
whichever ones happen to have a working Qt.

**Spawn, not fork.** A forked child would inherit the parent's Qt event loop and
its already-imported numerical libraries, and ``spawn`` is the only start method
Windows has — the same reasoning :mod:`nanopnp.sweep.run` gives for the sweep
pool, arrived at for one more reason here.

**Three things cross, all plain and picklable.**

*Into the child*: a :class:`RunRequest` of strings, re-resolved on the far side
rather than pickled live. That is what makes the child identical to a command
line run of the same case, which is what makes its FR-25 manifest identical too.

*Out of the child*: :class:`RunEvent` values on a queue. :class:`QueueProgress`
satisfies the :class:`~nanopnp.core.stages.Progress` protocol by putting
``(fraction, message)`` on it, and :class:`QueueStage` satisfies
:class:`~nanopnp.core.stages.StageHook` the same way. The stage transitions cross
as *data* and not as parsed captions: a number or a name recovered from a display
format is a number whose meaning is a formatting decision.

*Into the child, continuously*: cancellation, as a :class:`multiprocessing.Event`.
:class:`~nanopnp.core.stages.CancelFlag` is an in-process boolean and says so, so
:class:`EventCancel` adapts the event to the :class:`~nanopnp.core.stages.CancelToken`
protocol here — the protocol is what crosses, and ``core/stages.py`` gains no
``multiprocessing`` import for it.

**No thread pinning.** :mod:`nanopnp.sweep.run` pins ``OMP_NUM_THREADS`` and its
siblings because N workers sharing one thread pool are not N independent workers
and QR-06's scaling claim would be measuring the pool. One interactive solve
makes no such claim and wants the threads.

**One classification of failure, not two.** The child classifies its own
exception through :func:`nanopnp.cli.errors.classify` and reports the §3.1 exit
class, so a case that exits 3 from ``nanopnp run`` is diagnosed as a case error
in the shell as well. A second classifier would be a second contract to keep in
step.
"""

from __future__ import annotations

import logging
import multiprocessing
import queue as queue_module
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, TypeAlias

from nanopnp.cli.errors import EXIT_CANCELLED, EXIT_OK, classify

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
    "Progress",
    "QueueProgress",
    "QueueStage",
    "RunEvent",
    "RunRequest",
    "SolverProcess",
    "Stage",
    "Started",
    "failure_event",
]


# -- what crosses into the child ---------------------------------------------


@dataclass(frozen=True)
class RunRequest:
    """Everything the child needs, as strings it re-resolves for itself.

    Parameters
    ----------
    case
        The case file. A path and not a document: §5.3.1 makes the file the unit
        of reproducibility, and a run of an unsaved document would emit a
        manifest naming an input that does not exist.
    store
        The artefact store's root, or ``None`` for the process default.
    """

    case: str
    store: str | None = None


# -- what crosses out of it ---------------------------------------------------


@dataclass(frozen=True)
class Started:
    """The child is up and about to read the case."""

    case: str
    store: str | None


@dataclass(frozen=True)
class Stage:
    """A pipeline stage is about to run (:class:`~nanopnp.core.stages.StageHook`)."""

    name: str
    index: int
    total: int


@dataclass(frozen=True)
class Progress:
    """A completion fraction in [0, 1] and its caption, monotone, ending at 1."""

    fraction: float
    message: str


@dataclass(frozen=True)
class Finished:
    """The run completed and wrote its run directory."""

    directory: str
    exit_code: int = EXIT_OK


@dataclass(frozen=True)
class Failed:
    """The run raised, with the §3.1 exit class the command line would return.

    Parameters
    ----------
    exit_code
        :func:`nanopnp.cli.errors.classify` of the exception — ``3`` the case,
        ``4`` a QR-12 gate, ``5`` convergence, ``1`` unclassified.
    error
        The exception's qualified class name, for a caller that wants to say
        which one it was without a traceback.
    message
        The diagnostic. For a gate this already names the gate, the offending
        quantity and its location (QR-12), which is why the shell shows it
        rather than a traceback.
    """

    exit_code: int
    error: str
    message: str


@dataclass(frozen=True)
class Cancelled:
    """The run stopped because the token was set, naming where it stopped.

    Not a failure, and deliberately not a :class:`Failed` carrying ``130``: a
    cancelled run wrote no artefact (§5.3.2) and nothing is wrong with the case.
    """

    where: str
    exit_code: int = EXIT_CANCELLED


RunEvent: TypeAlias = Started | Stage | Progress | Finished | Failed | Cancelled
"""Everything the child may post. Frozen, picklable, and plain."""


# -- the adapters the child hands to ``run_case`` -----------------------------


@dataclass(frozen=True)
class QueueProgress:
    """A :class:`~nanopnp.core.stages.Progress` that posts onto a queue."""

    queue: Queue[RunEvent]

    def __call__(self, fraction: float, message: str) -> None:
        """Post one progress report."""
        self.queue.put(Progress(fraction=float(fraction), message=str(message)))


@dataclass(frozen=True)
class QueueStage:
    """A :class:`~nanopnp.core.stages.StageHook` that posts onto a queue."""

    queue: Queue[RunEvent]

    def __call__(self, name: str, index: int, total: int) -> None:
        """Post one stage transition."""
        self.queue.put(Stage(name=str(name), index=int(index), total=int(total)))


class EventCancel:
    """A :class:`~nanopnp.core.stages.CancelToken` over a :class:`multiprocessing.Event`.

    :class:`~nanopnp.core.stages.CancelFlag` is an in-process boolean and its own
    docstring says so. This is the cross-process one, and it lives here rather
    than in ``core/stages.py`` so that the stage layer keeps no dependency on
    :mod:`multiprocessing`: what crosses the boundary is the protocol.
    """

    def __init__(self, event: EventType) -> None:
        self._event = event

    def cancel(self) -> None:
        """Ask the running stage to stop at its next check."""
        self._event.set()

    def cancelled(self) -> bool:  # noqa: D102 - documented on the protocol
        return self._event.is_set()


# -- the child ----------------------------------------------------------------


def failure_event(error: BaseException) -> Failed:
    """Return the :class:`Failed` one exception produces.

    A function rather than three lines inside :func:`_worker` so that the
    agreement between the shell and the command line is testable without
    spawning anything: what is asserted is that a case error reports ``3``, a
    QR-12 gate ``4`` and a divergence ``5`` — the §3.1 codes themselves, not
    that two callers of :func:`~nanopnp.cli.errors.classify` agree.
    """
    return Failed(
        exit_code=classify(error),
        error=type(error).__qualname__,
        message=str(error),
    )


def _worker(request: RunRequest, events: Queue[RunEvent], cancel: EventType) -> None:
    """Run one case and post what happened.

    Deferred imports throughout: this runs in a fresh interpreter under
    ``spawn``, and nothing above it in the parent should have paid for NGSolve.

    Never raises. An exception that escaped would reach the child's default
    handler, print a traceback nobody reads and leave the parent waiting on a
    queue that will never carry another event.
    """
    from nanopnp.core.stages import Cancelled as CancelledError
    from nanopnp.io.run import run_case
    from nanopnp.io.store import Store

    events.put(Started(case=request.case, store=request.store))
    try:
        result = run_case(
            Path(request.case),
            store=Store(Path(request.store)) if request.store is not None else None,
            progress=QueueProgress(events),
            cancel=EventCancel(cancel),
            on_stage=QueueStage(events),
        )
    except CancelledError as cancelled:
        events.put(Cancelled(where=str(cancelled)))
    except BaseException as error:
        events.put(
            Failed(
                exit_code=classify(error),
                error=type(error).__qualname__,
                message=str(error),
            )
        )
    else:
        events.put(Finished(directory=str(result.directory)))


# -- the parent ---------------------------------------------------------------


@dataclass
class SolverProcess:
    """One background solve: start it, cancel it, drain what it has said.

    Deliberately not a thread and not a callback: the parent polls
    :meth:`drain` from whatever loop it has, so the object is driven identically
    by a Qt timer and by a test.

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
        """Spawn the child and begin the run.

        Raises
        ------
        RuntimeError
            If this process has already been started. One object, one run: a
            restarted one would drain the previous run's events into the new
            run's state machine.
        """
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
        """Ask the child to stop at its next cancellation check.

        Cooperative, as :class:`~nanopnp.core.stages.CancelToken` is: a
        factorisation already inside UMFPACK runs to completion, and the run
        unwinds at the next stage or Newton iteration. Nothing is written
        (§5.3.2).
        """
        if self._cancel is not None:
            self._cancel.set()

    def drain(self) -> tuple[RunEvent, ...]:
        """Return every event posted since the last call, oldest first.

        Never blocks, so a caller may poll it from a user-interface timer.
        """
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
        """The child's process exit status, or ``None`` while it is running.

        The *process*' status, which is not the §3.1 class: the child reports
        that on :class:`Failed` and :class:`Cancelled`, because a child that
        died without reporting one has no diagnosis to give.
        """
        return None if self._process is None else self._process.exitcode

    def join(self, timeout: float | None = None) -> None:
        """Wait for the child to exit."""
        if self._process is not None:
            self._process.join(timeout)

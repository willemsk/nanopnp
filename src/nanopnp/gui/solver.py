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
    case: str
    store: str | None = None
    upto: str | None = None


@dataclass(frozen=True)
class Started:
    case: str
    store: str | None


@dataclass(frozen=True)
class Stage:
    name: str
    index: int
    total: int


@dataclass(frozen=True)
class Produced:
    name: str
    schema: str
    hash: str
    cached: bool
    store: str


@dataclass(frozen=True)
class Rung:
    name: str
    stage: int
    index: int
    total: int
    reporting: bool
    tolerance: float


@dataclass(frozen=True)
class Iteration:
    iteration: int
    residual: float
    update: float
    damping: float
    trials: int
    forced: bool


@dataclass(frozen=True)
class Progress:
    fraction: float
    message: str


@dataclass(frozen=True)
class Finished:
    directory: str
    exit_code: int = EXIT_OK


@dataclass(frozen=True)
class Failed:
    exit_code: int
    error: str
    message: str


@dataclass(frozen=True)
class Cancelled:
    where: str
    exit_code: int = EXIT_CANCELLED


RunEvent: TypeAlias = (
    Started | Stage | Produced | Rung | Iteration | Progress | Finished | Failed | Cancelled
)


@dataclass(frozen=True)
class QueueProgress:
    queue: Queue[RunEvent]

    def __call__(self, fraction: float, message: str) -> None:
        self.queue.put(Progress(fraction=float(fraction), message=str(message)))


@dataclass(frozen=True)
class QueueStage:
    queue: Queue[RunEvent]

    def __call__(self, name: str, index: int, total: int) -> None:
        self.queue.put(Stage(name=str(name), index=int(index), total=int(total)))


@dataclass(frozen=True)
class QueueArtefact:
    queue: Queue[RunEvent]
    store: str

    def __call__(self, name: str, schema: str, hash: str, cached: bool) -> None:
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
    queue: Queue[RunEvent]

    def rung(
        self, name: str, stage: int, index: int, total: int, reporting: bool, tolerance: float
    ) -> None:
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
    def __init__(self, event: EventType) -> None:
        self._event = event

    def cancel(self) -> None:
        self._event.set()

    def cancelled(self) -> bool:
        return self._event.is_set()


def failure_event(error: BaseException) -> Failed:
    return Failed(
        exit_code=classify(error),
        error=type(error).__qualname__,
        message=str(error),
    )


def _worker(request: RunRequest, events: Queue[RunEvent], cancel: EventType) -> None:
    from nanopnp.core.stages import Cancelled as CancelledError
    from nanopnp.io.store import Store
    from nanopnp.pipeline.run import run_case

    events.put(Started(case=request.case, store=request.store))
    try:
        # Resolved here rather than left to ``run_case``, so the root every
        # ``Produced`` names is the one the walk wrote into.
        store = Store(Path(request.store)) if request.store is not None else Store()
        result = run_case(
            Path(request.case),
            store=store,
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
    request: RunRequest
    _process: BaseProcess | None = field(default=None, repr=False)
    _events: Queue[RunEvent] | None = field(default=None, repr=False)
    _cancel: EventType | None = field(default=None, repr=False)

    def start(self) -> None:
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
        if self._cancel is not None:
            self._cancel.set()

    def drain(self) -> tuple[RunEvent, ...]:
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
        return self._process is not None and self._process.is_alive()

    @property
    def exit_code(self) -> int | None:
        return None if self._process is None else self._process.exitcode

    def join(self, timeout: float | None = None) -> None:
        if self._process is not None:
            self._process.join(timeout)

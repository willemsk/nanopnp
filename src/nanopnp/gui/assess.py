"""The contour editor's measuring side: one spawned process, the §5.2.1 criteria, plain data."""

from __future__ import annotations

import logging
import multiprocessing
import queue as queue_module
from dataclasses import dataclass, field
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any, TypeAlias

from nanopnp.core.stages import MissingExtraError, create
from nanopnp.io.artefact import StageInputs
from nanopnp.io.case import UnsupportedCaseSection
from nanopnp.io.store import Store
from nanopnp.pipeline.case import load_case, resolve
from nanopnp.pipeline.run import offered, stored_upstream
from nanopnp.structure.ensemble import PAYLOAD_NAME as ENSEMBLE_PAYLOAD
from nanopnp.structure.ensemble import AlignedEnsemble
from nanopnp.symmetry.reduce import PAYLOAD_NAME as REDUCED_PAYLOAD
from nanopnp.symmetry.reduce import ReducedMap

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from multiprocessing.process import BaseProcess
    from multiprocessing.queues import Queue

    import numpy as np

    from nanopnp.geometry.contour import ContourGateError, ContourMeasurement
    from nanopnp.io.artefact import Artefact
    from nanopnp.io.case import CaseDocument

logger = logging.getLogger(__name__)

__all__ = [
    "AssessFailed",
    "AssessProcess",
    "AssessRequest",
    "Assessed",
    "Assessment",
    "Refusal",
    "Seed",
    "Seeded",
    "assess",
    "seed",
]

Record: TypeAlias = Any


@dataclass(frozen=True)
class Refusal:
    criterion: str
    measured: str
    threshold: str
    where: str
    message: str
    location_nm: tuple[float, float] | None


@dataclass(frozen=True)
class Assessment:
    record: Record
    failures: tuple[Refusal, ...]

    @property
    def passed(self) -> bool:
        return not self.failures


@dataclass(frozen=True)
class Seed:
    vertices: tuple[tuple[float, float], ...]
    digest: str
    name: str
    assessment: Assessment


@dataclass(frozen=True)
class AssessRequest:
    case: str
    store: str | None = None
    vertices: tuple[tuple[float, float], ...] | None = None


@dataclass(frozen=True)
class Assessed:
    assessment: Assessment


@dataclass(frozen=True)
class Seeded:
    seed: Seed


@dataclass(frozen=True)
class AssessFailed:
    error: str
    message: str


AssessEvent: TypeAlias = Assessed | Seeded | AssessFailed


def _contour() -> ModuleType:
    try:
        from nanopnp.geometry import contour
    except ModuleNotFoundError as error:
        missing = error.name or ""
        if missing == "nanopnp" or missing.startswith("nanopnp."):
            raise
        raise MissingExtraError(
            f"measuring a contour needs the 'structure' extra: {missing!r} is not installed. "
            "Install the extras with `uv sync --all-extras`",
            name=missing,
        ) from error
    return contour


@dataclass(frozen=True)
class _Context:
    document: CaseDocument
    structure: Artefact
    symmetry: Artefact
    upstream: dict[str, Artefact] = field(default_factory=dict)


def _context(request: AssessRequest) -> _Context:
    document = load_case(Path(request.case))
    if document.structure is None:
        raise UnsupportedCaseSection(
            f"case {document.name!r} carries no structure: section, so there is no stage-1 "
            "structure to measure the probe radius on and no stage-3 map to take the planes "
            "from; the §5.2.1 criteria are measured against those"
        )
    store = Store(Path(request.store)) if request.store is not None else Store()
    upstream = stored_upstream(document, store=store, feeding="contour")
    return _Context(
        document=document,
        structure=upstream["structure"],
        symmetry=upstream["symmetry"],
        upstream=upstream,
    )


def _refusal(error: ContourGateError) -> Refusal:
    return Refusal(
        criterion=error.criterion,
        measured=error.measured,
        threshold=error.threshold,
        where=error.where,
        message=str(error),
        location_nm=error.location_nm,
    )


def _assessment(measured: ContourMeasurement) -> Assessment:
    return Assessment(
        record=measured.record, failures=tuple(_refusal(error) for error in measured.failures)
    )


def measure_loop(loop: np.ndarray, context: _Context) -> Assessment:
    import numpy as np

    contour = _contour()
    resolved = resolve(context.document)
    density = resolved.density
    assert density is not None  # a structure case always resolves one
    reduced = ReducedMap.read(context.symmetry.payload[REDUCED_PAYLOAD])
    ensemble = AlignedEnsemble.read(context.structure.payload[ENSEMBLE_PAYLOAD])
    points = np.asarray(loop, dtype=np.float64).reshape(-1, 2)
    planes, probe, _ = contour.gate_inputs(points, reduced.z_nm, ensemble, density)
    return _assessment(
        contour.measure(
            points, spacing_nm=density.grid_spacing_nm, planes_nm=planes, probe_nm=probe
        )
    )


def assess(request: AssessRequest) -> Assessment:
    import numpy as np

    if request.vertices is None:
        raise ValueError("an assessment needs a loop; ask for a seed instead")
    return measure_loop(np.asarray(request.vertices, dtype=np.float64), _context(request))


def seed(request: AssessRequest) -> Seed:
    contour = _contour()
    context = _context(request)
    resolved = resolve(context.document)
    assert resolved.contour is not None and resolved.density is not None
    reduced = ReducedMap.read(context.symmetry.payload[REDUCED_PAYLOAD])
    conditioned = contour.condition_map(reduced, resolved.contour, resolved.density)
    key = create("contour").key(
        StageInputs(resolved=resolved, upstream=offered("contour", context.upstream))
    )
    loop = conditioned.loop
    return Seed(
        vertices=tuple((float(r), float(z)) for r, z in loop),
        digest=reduced.digest(),
        name=f"contour-{key.hash[:12]}",
        assessment=measure_loop(loop, context),
    )


def _worker(request: AssessRequest, events: Queue[AssessEvent]) -> None:
    try:
        if request.vertices is None:
            events.put(Seeded(seed(request)))
        else:
            events.put(Assessed(assess(request)))
    except BaseException as error:
        events.put(AssessFailed(error=type(error).__qualname__, message=str(error)))


@dataclass
class AssessProcess:
    request: AssessRequest
    _process: BaseProcess | None = field(default=None, repr=False)
    _events: Queue[AssessEvent] | None = field(default=None, repr=False)
    # The child always ends by posting one event, so an exit before any was drained means it died
    # unanswered.
    answered: bool = field(default=False, repr=False)

    def start(self) -> None:
        if self._process is not None:
            raise RuntimeError(
                "this AssessProcess has already been started; construct another one rather than "
                "restarting it"
            )
        context = multiprocessing.get_context("spawn")
        self._events = context.Queue()
        self._process = context.Process(
            target=_worker,
            args=(self.request, self._events),
            name=f"nanopnp-assess-{Path(self.request.case).stem}",
            daemon=True,
        )
        self._process.start()

    def drain(self) -> tuple[AssessEvent, ...]:
        if self._events is None:
            return ()
        found: list[AssessEvent] = []
        while True:
            try:
                found.append(self._events.get_nowait())
            except queue_module.Empty:
                self.answered = self.answered or bool(found)
                return tuple(found)

    @property
    def running(self) -> bool:
        return self._process is not None and self._process.is_alive()

    def terminate(self, timeout: float = 1.0) -> None:
        if self._process is None:
            return
        if self._process.is_alive():
            self._process.terminate()
        self._process.join(timeout)
        if self._process.is_alive():
            self._process.kill()
            self._process.join(timeout)

    def join(self, timeout: float | None = None) -> None:
        if self._process is not None:
            self._process.join(timeout)

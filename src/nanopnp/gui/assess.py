"""The contour editor's measuring side: one spawned process, the §5.2.1 criteria, plain data back.

A hand edit enters a run as a supplied profile, which the §5.2.1 NOTE gates only
on validity, simplicity and topology; the editor enforces exactly that, through
the loader's own validator (:class:`~nanopnp.gui.geometry.ProfileEditor`). The
section's other criteria — axis clearance, vertex spacing, feature size and the
radius-profile band — are still worth *seeing*, because a contour inside the
probe radius is a plausible wrong geometry that nothing downstream refuses. So
they are measured here on request, recorded, and shown, and never enforced
(WP24 D8).

**One implementation of the criteria.** What is measured is
:func:`nanopnp.geometry.contour.measure` — stage 4's gate without its raise
(WP24 D9) — against the probe-radius profile of the case's own stored stage-1
structure on the mid-planes of its own stored stage-3 map. The thresholds come
from that measurement and are never written in ``gui/``, so the editor and the
gate cannot disagree about a number.

**Seeding after a refusal** (§8.2.2 B9, WP24 D10). A refused gate writes no
artefact (QR-12), so a case whose contour stage 4 refused has nothing to override.
:func:`seed` recomputes the loop with stage 4's own conditioning on the stored
stage-3 map and the case's contour parameters, and returns it with the refusal as
data — the criterion, the diagnostic and its ``(r, z)`` — and the digest and name
stage 4 would have recorded, which the edit then carries (D5).

**Why a child.** The probe profile is frames x atoms x planes distances, seconds
on an ensemble, and this path imports MDAnalysis, scikit-image and Shapely,
none of which the shell's process should pay for or hold. The view-models import
no such thing (VER-55); this module defers them into the functions that run in
the child, and without the ``structure`` extra refuses naming it.
"""

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
from nanopnp.pipeline.run import stored_upstream
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
"""A measurement record: nested plain data, as :func:`~nanopnp.geometry.contour.measure` has it."""


# -- what crosses the boundary ------------------------------------------------


@dataclass(frozen=True)
class Refusal:
    """One §5.2.1 criterion a loop fails, as data.

    The fields of :class:`~nanopnp.geometry.contour.ContourGateError`. ``message``
    is the diagnostic as the gate words it, and ``location_nm`` the ``(r, z)`` it
    names, as numbers, so the editor marks it without parsing ``where``.
    """

    criterion: str
    measured: str
    threshold: str
    where: str
    message: str
    location_nm: tuple[float, float] | None


@dataclass(frozen=True)
class Assessment:
    """Every §5.2.1 criterion measured on a loop, and the ones it fails.

    Parameters
    ----------
    record
        :attr:`~nanopnp.geometry.contour.ContourMeasurement.record`: equal to
        what stage 4's gate records for the same loop when it passes.
    failures
        In the gate's order; the first is the refusal stage 4 would make.
    """

    record: Record
    failures: tuple[Refusal, ...]

    @property
    def passed(self) -> bool:
        """Whether the loop meets every criterion."""
        return not self.failures


@dataclass(frozen=True)
class Seed:
    """A loop to edit after stage 4's gate refused it (§8.2.2 B9).

    Parameters
    ----------
    vertices
        :func:`~nanopnp.geometry.contour.condition`'s loop on the stored map, in
        the stage-1 frame.
    digest
        The stage-3 payload digest stage 4 would have recorded as ``sha256``.
    name
        The name stage 4 would have given its profile.
    assessment
        The loop measured, which carries the refusal.
    """

    vertices: tuple[tuple[float, float], ...]
    digest: str
    name: str
    assessment: Assessment


@dataclass(frozen=True)
class AssessRequest:
    """What the child is asked: measure a loop, or seed one.

    Parameters
    ----------
    case
        The case file the stage-1 and stage-3 artefacts belong to: a case with a
        ``structure:`` section, whose stages 1 to 3 are in the store.
    store
        The store's root, or ``None`` for the process default.
    vertices
        The loop to measure, in the stage-1 frame; ``None`` asks for a
        :class:`Seed` instead.
    """

    case: str
    store: str | None = None
    vertices: tuple[tuple[float, float], ...] | None = None


@dataclass(frozen=True)
class Assessed:
    """A loop was measured."""

    assessment: Assessment


@dataclass(frozen=True)
class Seeded:
    """A loop was recomputed from the stored map."""

    seed: Seed


@dataclass(frozen=True)
class AssessFailed:
    """Nothing was measured, and this is why, as the refusing code worded it."""

    error: str
    message: str


AssessEvent: TypeAlias = Assessed | Seeded | AssessFailed
"""Everything the child may post. Frozen, picklable and plain."""


# -- the child ----------------------------------------------------------------


def _contour() -> ModuleType:
    """Import stage 4's module, or refuse naming the extra it needs.

    Raises
    ------
    MissingExtraError
        If scikit-image or Shapely is missing: the ``structure`` extra.
    """
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
    """The stored stages a measurement reads, and the case's stage-4 parameters."""

    document: CaseDocument
    structure: Artefact
    symmetry: Artefact
    upstream: dict[str, Artefact] = field(default_factory=dict)


def _context(request: AssessRequest) -> _Context:
    """Load the case and take its stage-1 and stage-3 artefacts from the store.

    Keyed exactly as a walk keys them, through
    :func:`~nanopnp.pipeline.run.stored_upstream`, and never computed: an assessment
    that ran stage 2 would be minutes of work the shell did not ask for.

    Raises
    ------
    nanopnp.io.case.UnsupportedCaseSection
        If the case carries no ``structure:`` section: there is then no structure
        to measure a probe radius on.
    nanopnp.pipeline.run.MissingUpstreamError
        If stages 1 to 3 have not run into this store.
    """
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
    """Return one gate failure as plain data."""
    return Refusal(
        criterion=error.criterion,
        measured=error.measured,
        threshold=error.threshold,
        where=error.where,
        message=str(error),
        location_nm=error.location_nm,
    )


def _assessment(measured: ContourMeasurement) -> Assessment:
    """Return a measurement as plain data."""
    return Assessment(
        record=measured.record, failures=tuple(_refusal(error) for error in measured.failures)
    )


def measure_loop(loop: np.ndarray, context: _Context) -> Assessment:
    """Measure a loop as stage 4's gate would, against the case's stored stages 1 and 3.

    The planes are the mid-planes of the stage-3 map's z lattice that cross the
    loop, and the probe radius is the stage-1 structure's on each — stage 4's
    inputs to its gate, through the same
    :func:`~nanopnp.geometry.contour.gate_inputs` ``ContourStage.run`` calls, so
    a loop stage 4 produced measures to the record its summary carries.
    """
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
    """Measure the request's loop against the §5.2.1 criteria (WP24 D8).

    Raises
    ------
    ValueError
        If the request carries no loop.
    """
    import numpy as np

    if request.vertices is None:
        raise ValueError("an assessment needs a loop; ask for a seed instead")
    return measure_loop(np.asarray(request.vertices, dtype=np.float64), _context(request))


def seed(request: AssessRequest) -> Seed:
    """Recompute stage 4's loop from the stored map, for an edit after a refusal (§8.2.2 B9).

    Raises
    ------
    nanopnp.geometry.contour.ContourGateError
        If the conditioning itself refuses — an open contour, no region, more than
        one component. There is then no loop to seed from, and the refusal
        propagates with the gate's own words.
    """
    contour = _contour()
    context = _context(request)
    resolved = resolve(context.document)
    assert resolved.contour is not None and resolved.density is not None
    reduced = ReducedMap.read(context.symmetry.payload[REDUCED_PAYLOAD])
    conditioned = contour.condition_map(reduced, resolved.contour, resolved.density)
    key = create("contour").key(StageInputs(resolved=resolved, upstream=dict(context.upstream)))
    loop = conditioned.loop
    return Seed(
        vertices=tuple((float(r), float(z)) for r, z in loop),
        digest=reduced.digest(),
        name=f"contour-{key.hash[:12]}",
        assessment=measure_loop(loop, context),
    )


def _worker(request: AssessRequest, events: Queue[AssessEvent]) -> None:
    """Measure or seed, and post the answer or why there is none.

    Never raises, for the reason :func:`nanopnp.gui.solver._worker` gives.
    """
    try:
        if request.vertices is None:
            events.put(Seeded(seed(request)))
        else:
            events.put(Assessed(assess(request)))
    except BaseException as error:
        events.put(AssessFailed(error=type(error).__qualname__, message=str(error)))


# -- the parent ---------------------------------------------------------------


@dataclass
class AssessProcess:
    """One background measurement: start it, drain what it said, stop it if superseded.

    Polled, like :class:`~nanopnp.gui.render.RenderProcess`, so a Qt timer and a
    test drive it identically.
    """

    request: AssessRequest
    _process: BaseProcess | None = field(default=None, repr=False)
    _events: Queue[AssessEvent] | None = field(default=None, repr=False)
    answered: bool = field(default=False, repr=False)
    """Whether :meth:`drain` has ever returned an event.

    The child always ends by posting one, verdict or refusal, so a child that has
    exited while this is still false died without answering (killed, out of memory,
    a fault in a compiled library) and the caller must say so: the parent cannot
    tell that from a slow child by the queue alone (CODE_REVIEW_003 CR-7).
    """

    def start(self) -> None:
        """Spawn the child.

        Raises
        ------
        RuntimeError
            If this process has already been started.
        """
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
        """Return every event posted since the last call, oldest first."""
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
        """Whether the child is alive."""
        return self._process is not None and self._process.is_alive()

    def terminate(self, timeout: float = 1.0) -> None:
        """Stop a superseded measurement and wait for it to go."""
        if self._process is None:
            return
        if self._process.is_alive():
            self._process.terminate()
        self._process.join(timeout)
        if self._process.is_alive():
            self._process.kill()
            self._process.join(timeout)

    def join(self, timeout: float | None = None) -> None:
        """Wait for the child to exit."""
        if self._process is not None:
            self._process.join(timeout)

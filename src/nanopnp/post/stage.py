"""Stages 11 and 12 of section 5.2: the quantities of interest, and the report.

The registry stopped at stage 10, so ``nanopnp run`` had nowhere to put the two
things a run exists to produce — the NUM-27 scalars and whatever lands on disk.
Registering them here is what lets the driver be a walk over the stage graph
rather than a script that computes physics inside the CLI (section 5.1).

**Stage 11 restores rather than re-solves.** Its input is the stage-10 artefact,
whose payload is the self-describing coefficient record of
:mod:`nanopnp.solve.state`; :func:`~nanopnp.solve.state.restore` rebuilds the
state *and the residual* on the same operator the solve used, which is what lets
the NUM-25 route run at all on a solution served from a cache hit. Extraction is
then the same :func:`nanopnp.post.qoi.extract` a live solution goes through, so a
cached run and a fresh one cannot report different numbers by different routes.

**The band is derived from the mesh, not from a geometry object.**
:func:`~nanopnp.post.indicator.lumen_band` takes a
:class:`~nanopnp.mesh.primitives.CylindricalPoreGeometry`, and an ingested mesh
(FR-27) has no such object. :func:`membrane_band` reads the ``membrane``
material's own extent in ``z`` off the :class:`~nanopnp.mesh.adapter.MeshData`
and takes the middle ``fraction`` of it, which on a ``CylindricalPoreGeometry``
is *identically* ``lumen_band(geometry, fraction)`` — the identity is asserted,
because the band has to be the existing convention read off a different object
and not a second convention that happens to be close.

**What a word in ``outputs:`` cannot buy, it is refused rather than dropped**
(section 5.3.1 NOTE). ``rectification`` needs two operating points and a single
run has one; ``analyte_force`` needs an ``analyte`` material and a mesh either
carries one or does not. Both abort naming what is missing (QR-12), because a
run that quietly returns five of the six quantities asked for is a run whose
output list means nothing.
"""

from __future__ import annotations

import logging
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.charge.stage import read_fields
from nanopnp.core.paths import store_root
from nanopnp.core.stages import (
    CancelToken,
    Progress,
    StageDescription,
    check_cancelled,
    describe,
    report,
)
from nanopnp.geometry.analyte import ANALYTE_BOUNDARY, ANALYTE_DOMAIN
from nanopnp.io.artefact import Artefact, CaseArtefact, QoIArtefact, ReportArtefact, StageInputs
from nanopnp.io.case import resolve
from nanopnp.io.defaults import ContributedDeviation
from nanopnp.io.fields import export_fields
from nanopnp.mesh.ingest import ingest
from nanopnp.physics.measures import AXISYMMETRIC, Measures
from nanopnp.physics.models import CoupledModel
from nanopnp.post import forces as force_post
from nanopnp.post import qoi as qoi_post
from nanopnp.post.indicator import axial_indicator
from nanopnp.solve.stage import SolveStage
from nanopnp.solve.state import STATE_FILENAME, STATE_KEY, restore

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from collections.abc import Mapping

    from nanopnp.core.hashing import Canonicalisable
    from nanopnp.core.typing import Expression
    from nanopnp.io.case import ResolvedCase
    from nanopnp.mesh.adapter import MeshData
    from nanopnp.physics.models import ModelSolution

__all__ = [
    "BAND_FRACTION",
    "EXTENSION_INNER",
    "EXTENSION_OUTER",
    "MEMBRANE_MATERIAL",
    "QoIStage",
    "ReportStage",
    "SelectionError",
    "extension_shell",
    "membrane_band",
]

logger = logging.getLogger(__name__)

MEMBRANE_MATERIAL = "membrane"
"""Material whose axial extent the NUM-24 band is taken from."""

BAND_FRACTION = 0.8
"""Fraction of the membrane's z-extent ``grad(psi)`` is supported on.

The same default as :func:`nanopnp.post.indicator.lumen_band`, and the same
number for the same reason: it puts the transition wholly inside the lumen and
away from both mouths. VER-11 is what says the answer does not depend on it.
"""

EXTENSION_INNER = 1.2
"""Inner radius of the NUM-28 extension shell, in units of the body's semi-axis."""

EXTENSION_OUTER = 3.0
"""Outer radius of the same shell.

``(1.2, 3.0)`` is the shell WP6's Tier-2 electrophoretic-mobility benchmark was
measured on, expressed there as multiples of the sphere's radius. It is a
default and not a requirement: VER-19's convergence study is what establishes
that the force does not depend on it, and ``options["extension_shell_nm"]``
overrides it with absolute distances.
"""

WORKSPACE_DIRNAME = "tmp"
"""Directory under the store root an export is written to before it is stored."""


class SelectionError(ValueError):
    """A word in ``outputs:`` cannot be met by the run it was asked of.

    A :class:`ValueError` rather than a gate error: nothing numerical has gone
    wrong and no result is in doubt. The case asked for a quantity this run
    cannot produce, and section 5.3.1 requires that to be said rather than
    silently dropped.
    """


def membrane_band(
    data: MeshData,
    *,
    fraction: float = BAND_FRACTION,
    material: str = MEMBRANE_MATERIAL,
) -> tuple[float, float]:
    """Return the NUM-24 transition band, read off the mesh's own membrane.

    Parameters
    ----------
    data
        The tagged mesh, in nm.
    fraction
        Fraction of the membrane's axial extent the band occupies.
    material
        Material name the extent is taken from.

    Returns
    -------
    tuple of float
        ``(lower_nm, upper_nm)``, the middle ``fraction`` of the material's
        ``z``-extent.

    Raises
    ------
    SelectionError
        If ``fraction`` is not in ``(0, 1]``, or if the mesh carries no such
        material — naming it and listing the materials the mesh does carry
        (QR-12). It deliberately does not fall back to the whole domain: a band
        spanning the reservoirs puts ``grad(psi)`` on the caps, and
        :func:`~nanopnp.post.indicator.check_indicator` would then fail with a
        message about ``psi`` rather than about the band.
    """
    import numpy as np

    if not 0.0 < fraction <= 1.0:
        raise SelectionError(f"fraction must lie in (0, 1], got {fraction}")
    if material not in data.materials:
        known = ", ".join(data.materials) or "none"
        raise SelectionError(
            f"the NUM-24 indicator band is taken from the {material!r} material's axial extent "
            f"and this mesh carries no such material; it has {known}. Spanning the whole domain "
            "instead would put grad(psi) on the reservoir caps, where NUM-24's identity with the "
            "cap flux no longer holds"
        )
    index = data.materials.index(material)
    selected = data.triangles[data.triangle_material == index]
    z = data.vertices[np.unique(selected), 1]
    lower, upper = float(z.min()), float(z.max())
    middle = 0.5 * (lower + upper)
    half = 0.5 * (upper - lower) * fraction
    return (middle - half, middle + half)


def extension_shell(data: MeshData, *, material: str = ANALYTE_DOMAIN) -> tuple[float, float]:
    """Return the NUM-28 extension shell in nm, scaled to the body in the mesh.

    The body's semi-axis is the larger of its radial and axial half-extents, and
    the shell is :data:`EXTENSION_INNER` to :data:`EXTENSION_OUTER` multiples of
    it, measured as distances from the body's surface.

    Raises
    ------
    SelectionError
        If the mesh carries no such material, naming it and the materials it
        does carry (section 5.3.1 NOTE, QR-12).
    """
    import numpy as np

    if material not in data.materials:
        known = ", ".join(data.materials) or "none"
        raise SelectionError(
            f"outputs asks for analyte_force, which requires the mesh to carry an {material!r} "
            f"material; this mesh has {known}. The NUM-28 force is a force *on a body*, and "
            "there is none in this domain to take it on"
        )
    index = data.materials.index(material)
    selected = data.triangles[data.triangle_material == index]
    points = data.vertices[np.unique(selected)]
    radial = float(points[:, 0].max())
    axial = 0.5 * float(points[:, 1].max() - points[:, 1].min())
    semi_axis = max(radial, axial)
    return (EXTENSION_INNER * semi_axis, EXTENSION_OUTER * semi_axis)


def _band(data: MeshData, options: Mapping[str, Canonicalisable]) -> tuple[float, float]:
    """Return the band this run uses: the option if given, else the mesh's."""
    supplied = options.get("indicator_band_nm")
    if supplied is None:
        return membrane_band(data)
    lower, upper = supplied
    if not lower < upper:
        raise SelectionError(
            f"indicator_band_nm must be increasing in z, got ({lower}, {upper}); an inverted "
            "band flips the sign of every current"
        )
    return (float(lower), float(upper))


def _shell(data: MeshData, options: Mapping[str, Canonicalisable]) -> tuple[float, float]:
    """Return the extension shell this run uses: the option if given, else the mesh's."""
    supplied = options.get("extension_shell_nm")
    if supplied is None:
        return extension_shell(data)
    inner, outer = supplied
    return (float(inner), float(outer))


def _solution(inputs: StageInputs, *, solving: bool) -> Artefact:
    """Return the stage-10 artefact this stage describes, solving only if it must.

    Both post-processing stages are independently invocable (FR-27), so both have
    to cope with a caller that handed them a case and no ``solve`` artefact. What
    they need of it differs: a ``key`` needs its *hash*, which
    :meth:`~nanopnp.solve.stage.SolveStage.key` answers without entering Newton,
    while ``run`` needs the converged state under its payload. Asking for the
    state in both would converge the ladder twice for one extraction — once to
    answer the probe whose contract is that it does not do the work, and once to
    do it.

    Parameters
    ----------
    inputs
        What the driver, the CLI or a caller handed the stage.
    solving
        ``True`` when the payload is needed, ``False`` when the hash will do.
    """
    solution = inputs.upstream.get("solve")
    if solution is not None:
        return solution
    stage = SolveStage()
    return stage.run(inputs) if solving else stage.key(inputs)


def _check_selection(outputs: tuple[str, ...]) -> None:
    """Refuse every word in ``outputs`` this run cannot meet (section 5.3.1 NOTE).

    Raises
    ------
    SelectionError
        Naming the word and why a single run cannot produce it.
    """
    if "rectification" in outputs:
        raise SelectionError(
            "outputs asks for rectification, which is the two-point ratio I(+V)/I(-V); this run "
            "has one operating point. The second bias can only come from a sweep (FR-24), and "
            "inventing one would report a ratio the run did not measure"
        )


@dataclass(frozen=True)
class _Prepared:
    """Everything :meth:`QoIStage.key` and :meth:`QoIStage.run` must agree on."""

    resolved: ResolvedCase
    data: MeshData
    case_hash: str
    solution: Artefact
    outputs: tuple[str, ...]
    band: tuple[float, float]
    shell: tuple[float, float] | None
    check_routes: bool


def _selected(
    quantities: qoi_post.QuantitiesOfInterest, outputs: tuple[str, ...]
) -> dict[str, Canonicalisable]:
    """Return the summary fields the case asked for, and no others.

    The extraction is one calculation — NUM-27 requires it, so that a transport
    number and a current reported together cannot come from two of them — but
    what is *reported* is what ``outputs:`` selects. The bias, the route record,
    the ``2 pi`` convention, the PHY-13 clamp count and the stabilisation's own
    contribution are always present: they are not quantities, they are what makes
    the quantities readable. The clamp count in particular is provenance the
    manifest's Materials group takes from here, and a run that reported no current
    would otherwise record that no solution was sampled for it; the stabilisation
    contribution reaches the manifest's Stabilisation group the same way, and is
    what section 7.4 subtracts from a number the reference produced differently.
    """
    record = quantities.summary()
    always = {
        "bias_V",
        "clamp_activations",
        "route_agreement",
        "routes_checked",
        "stabilisation_currents_A",
        "two_pi_included",
    }
    wanted = set(always)
    if "current" in outputs:
        wanted |= {"current_A", "currents_A", "conductance_S"}
    if "transport_numbers" in outputs:
        wanted |= {"transport_number", "currents_A"}
    if "eof_rate" in outputs:
        wanted.add("eof_m3_s")
    return {key: value for key, value in record.items() if key in wanted}


class QoIStage:
    """Stage 11: a converged solution to the NUM-27 scalars (FR-23, QR-04)."""

    name = "qoi"

    def describe(self) -> StageDescription:
        """Return the registry's description of this stage (FR-27)."""
        return describe(self.name)

    def key(self, inputs: StageInputs) -> QoIArtefact:
        """Return the artefact key this extraction will produce, without running it.

        Everything that changes a number is in the parameters: which quantities
        were asked for, the band ``grad(psi)`` is supported on, the extension
        shell when a force is asked for, and whether the NUM-26 route check ran.
        The band is a parameter and not a summary field because two extractions
        differing only in it are two numbers — which is precisely what NUM-24
        claims they are not, and what VER-11 tests rather than assumes.
        """
        prepared = self._prepare(inputs, solving=False)
        return QoIArtefact(
            case_hash=prepared.case_hash,
            solution_hash=prepared.solution.hash,
            outputs=prepared.outputs,
            indicator_band_nm=prepared.band,
            check_routes=prepared.check_routes,
            extension_shell_nm=prepared.shell,
        )

    def _prepare(self, inputs: StageInputs, *, solving: bool) -> _Prepared:
        """Resolve the case, ingest the mesh and settle every parameter.

        Shared by :meth:`key` and :meth:`run`, so that the key the store is asked
        about and the key the extraction produces cannot be built two ways.

        Parameters
        ----------
        inputs
            What the driver, the CLI or a caller handed the stage.
        solving
            Whether the converged *state* is needed, or only the solve
            artefact's hash. ``key`` needs the hash and :meth:`run` needs the
            payload, and the difference is a whole continuation ladder: a stage
            invoked with no upstream ``solve`` (FR-27) would otherwise converge
            it once to answer the probe and once to do the work, and the probe's
            contract is that it does not do the work.
        """
        resolved = resolve(inputs.case)
        ingested = ingest(resolved.mesh, resolved)
        outputs = tuple(resolved.outputs)
        _check_selection(outputs)
        check_routes = bool(inputs.options.get("check_routes", True))
        shell = _shell(ingested.data, inputs.options) if "analyte_force" in outputs else None
        solution = _solution(inputs, solving=solving)
        case = inputs.upstream.get("case")
        case_hash = case.hash if case is not None else CaseArtefact(inputs.case).hash
        return _Prepared(
            resolved=resolved,
            data=ingested.data,
            case_hash=case_hash,
            solution=solution,
            outputs=outputs,
            band=_band(ingested.data, inputs.options),
            shell=shell,
            check_routes=check_routes,
        )

    def run(
        self,
        inputs: StageInputs,
        *,
        progress: Progress | None = None,
        cancel: CancelToken | None = None,
    ) -> QoIArtefact:
        """Extract every selected quantity and emit the stage-11 artefact.

        Parameters
        ----------
        inputs
            The case, the stage-10 ``solve`` artefact and optionally the stage-9
            ``case`` artefact. Without the solve artefact the stage runs the
            solve itself, which is what keeps it independently invocable (FR-27)
            and keys the same cache entry either way.
        progress
            Called with a fraction in [0, 1] and a message, monotone, ending at 1.
        cancel
            Checked on entry, after the restore and before each extraction.

        Raises
        ------
        SelectionError
            If ``outputs:`` asks for something this run cannot produce.
        Cancelled
            If ``cancel`` turns true. No artefact is written.
        """
        check_cancelled(cancel, "the extraction")
        report(progress, 0.0, "resolving the case")
        prepared = self._prepare(inputs, solving=True)

        report(progress, 0.2, "restoring the converged state")
        check_cancelled(cancel, "restoring the state")
        state_path = prepared.solution.payload.get(STATE_KEY)
        if state_path is None:
            carried = ", ".join(sorted(prepared.solution.payload)) or "nothing"
            raise KeyError(
                f"the solve artefact carries no {STATE_KEY!r} payload (the {STATE_FILENAME} "
                f"record); it carries {carried}. "
                "Stage 11 restores the state to reassemble the NUM-25 residual and cannot extract "
                "from a summary alone"
            )
        solution = restore(Path(state_path), case=inputs.case)
        order = int(prepared.resolved.model_options.get("order", AXISYMMETRIC.element_order))
        measures = replace(AXISYMMETRIC, element_order=order)
        mesh = solution.space.mesh

        report(progress, 0.4, "building the NUM-24 indicator")
        check_cancelled(cancel, "the indicator")
        lower, upper = prepared.band
        indicator = axial_indicator(mesh, lower_nm=lower, upper_nm=upper, order=order)

        report(progress, 0.5, "extracting the scalar quantities")
        check_cancelled(cancel, "the scalar extraction")
        quantities = qoi_post.extract(
            solution,
            measures,
            indicator,
            bias_V=prepared.resolved.bias_V,
            check_routes=prepared.check_routes,
        )

        summary: dict[str, Canonicalisable] = {
            "indicator_band_nm": list(prepared.band),
            **_selected(quantities, prepared.outputs),
        }
        if prepared.shell is not None:
            report(progress, 0.8, "extracting the NUM-28 force")
            check_cancelled(cancel, "the force extraction")
            summary["analyte_force"] = self._force(
                solution, measures, shell=prepared.shell, check_routes=prepared.check_routes
            )
            summary["extension_shell_nm"] = list(prepared.shell)

        report(progress, 1.0, f"extracted {len(prepared.outputs)} selected outputs")
        return QoIArtefact(
            case_hash=prepared.case_hash,
            solution_hash=prepared.solution.hash,
            outputs=prepared.outputs,
            indicator_band_nm=prepared.band,
            check_routes=prepared.check_routes,
            extension_shell_nm=prepared.shell,
            summary=summary,
        )

    def _force(
        self,
        solution: ModelSolution,
        measures: Measures,
        *,
        shell: tuple[float, float],
        check_routes: bool,
    ) -> dict[str, Canonicalisable]:
        """Return the NUM-28 force record, over the mesh-scaled extension shell."""
        inner, outer = shell
        extension = force_post.axial_extension(
            solution.space.mesh,
            inner_nm=inner,
            outer_nm=outer,
            order=measures.element_order,
        )
        record: dict[str, Canonicalisable] = force_post.extract(
            solution,
            measures,
            extension,
            boundary=ANALYTE_BOUNDARY,
            check_routes=check_routes,
        ).summary()
        return record

    def deviations(self, inputs: StageInputs) -> tuple[ContributedDeviation, ...]:
        """Return the departures this stage's *options* introduce (FR-25).

        Switching the NUM-26 route check off is a departure no case-file key
        selects, so the diff of :mod:`nanopnp.io.defaults` cannot see it and this
        stage has to say so. A check silently switched off is exactly RSK-03.
        """
        if bool(inputs.options.get("check_routes", True)):
            return ()
        return (
            ContributedDeviation(
                source="stage option 'check_routes'",
                description=(
                    "the NUM-26 cross-check between the NUM-24 indicator current and the NUM-25 "
                    "reaction flux was not run, so the reported current has one route and no "
                    "oracle (QR-04, RSK-03)"
                ),
            ),
        )


class ReportStage:
    """Stage 12: what the run wrote, and what it wrote it from (IF-07, FR-25).

    The only thing about this stage that changes what lands on disk is the export
    selection, so that is its only parameter. Its three inputs are the hashes of
    everything the report describes, which is what stops a report being served
    from the cache for a different case, a different solve or a different
    extraction.

    Figures are v0.9. What this stage writes today is the IF-07 field export, and
    it writes it only when ``outputs:`` asks for ``fields``: the export is of
    order ten megabytes per solve, and an envelope sweep (FR-24) of thousands of
    points would otherwise write tens of gigabytes nobody requested.
    """

    name = "report"

    def __init__(self, *, workspace: Path | None = None) -> None:
        """Build the stage.

        Parameters
        ----------
        workspace
            Directory the export is written to before the store copies it in.
            Defaults to a fresh directory under the store root, so that a report
            written without a store still leaves its fields somewhere findable.
        """
        self._workspace = Path(workspace) if workspace is not None else None

    def describe(self) -> StageDescription:
        """Return the registry's description of this stage (FR-27)."""
        return describe(self.name)

    def key(self, inputs: StageInputs) -> ReportArtefact:
        """Return the artefact key this report will produce, without writing it."""
        case_hash, qoi, solution = self._hashes(inputs, solving=False)
        return ReportArtefact(
            case_hash=case_hash,
            qoi_hash=qoi.hash,
            solution_hash=solution.hash,
            exports=self._exports(inputs),
        )

    def _exports(self, inputs: StageInputs) -> tuple[str, ...]:
        """Return the export selection: ``("fields",)`` or nothing."""
        return ("fields",) if "fields" in resolve(inputs.case).outputs else ()

    def _hashes(self, inputs: StageInputs, *, solving: bool) -> tuple[str, Artefact, Artefact]:
        """Return the case hash and the two upstream artefacts this report describes.

        ``solving`` is :func:`_solution`'s: the key needs the solve artefact's
        hash and the export needs its payload, and only the second is worth a
        continuation ladder.
        """
        qoi = inputs.require("qoi")
        solution = _solution(inputs, solving=solving)
        case = inputs.upstream.get("case")
        case_hash = case.hash if case is not None else CaseArtefact(inputs.case).hash
        return case_hash, qoi, solution

    def run(
        self,
        inputs: StageInputs,
        *,
        progress: Progress | None = None,
        cancel: CancelToken | None = None,
    ) -> ReportArtefact:
        """Write whatever ``outputs:`` selected and emit the stage-12 artefact.

        Parameters
        ----------
        inputs
            The case, the stage-11 ``qoi`` artefact, and the stage-10 ``solve``
            artefact whose payload the export is read from.
        progress
            Called with a fraction in [0, 1] and a message, monotone, ending at 1.
        cancel
            Checked on entry and before the export is written.

        Raises
        ------
        Cancelled
            If ``cancel`` turns true. No artefact and no file are written.
        """
        check_cancelled(cancel, "the report")
        report(progress, 0.0, "collecting the run's artefacts")
        exports = self._exports(inputs)
        # Only an export needs the converged state; a report that writes nothing
        # needs the solve artefact's hash and no ladder to get it.
        case_hash, qoi, solution = self._hashes(inputs, solving=bool(exports))

        payload: dict[str, Path] = {}
        summary: dict[str, Canonicalisable] = {"exports": list(exports)}
        if exports:
            report(progress, 0.3, "restoring the converged state for export")
            check_cancelled(cancel, "the field export")
            payload, written = self._export(inputs, solution)
            summary["files"] = written
        report(progress, 1.0, f"wrote {len(payload)} file(s)")
        return ReportArtefact(
            case_hash=case_hash,
            qoi_hash=qoi.hash,
            solution_hash=solution.hash,
            exports=exports,
            payload=payload,
            summary=summary,
        )

    def _export(
        self, inputs: StageInputs, solution: Artefact
    ) -> tuple[dict[str, Path], dict[str, Canonicalisable]]:
        """Write the IF-07 pair(s) and return the payload map and the record.

        The permittivity and the fixed charge are supplied here rather than left
        to :mod:`nanopnp.io.fields` to find, because only the run knows them: the
        first is the model's own ``eps_r`` evaluated through the correction chain
        against the *stored* distance field, and the second is whatever stage 7
        assembled, if anything. A field the run did not have is simply absent
        from the file rather than written as a zero, which would claim it was
        computed and found to vanish.
        """
        state_path = solution.payload.get(STATE_KEY)
        if state_path is None:
            carried = ", ".join(sorted(solution.payload)) or "nothing"
            raise KeyError(
                f"the solve artefact carries no {STATE_KEY!r} payload (the {STATE_FILENAME} "
                f"record); it carries {carried}. "
                "The IF-07 export is of the converged fields and there is nothing to export from"
            )
        restored = restore(Path(state_path), case=inputs.case)
        model = restored.model
        if not isinstance(model, CoupledModel):
            raise TypeError(
                f"{model.name!r} is not a model of the epnp-ns family; the IF-07 export writes "
                "the NUM-09 scale set alongside the fields so that the nondimensional state "
                "stays recoverable, and this model declares none"
            )
        resolved = resolve(inputs.case)
        directory = self._directory(resolved.name)
        export = export_fields(
            restored,
            directory,
            scales=model.scales,
            relative_permittivity=_permittivity(restored),
            fixed_charge_C_m3=_fixed_charge(resolved),
        )
        payload = {path.name: path for path in export.paths()}
        record: dict[str, Canonicalisable] = {
            "paths": sorted(payload),
            "attributes": {key: list(value) for key, value in export.attributes.items()},
        }
        return payload, record

    def _directory(self, name: str) -> Path:
        """Return the directory the export is written into, creating it."""
        directory = self._workspace
        if directory is None:
            root = store_root() / WORKSPACE_DIRNAME
            root.mkdir(parents=True, exist_ok=True)
            safe = "".join(character if character.isalnum() else "-" for character in name)
            directory = Path(tempfile.mkdtemp(prefix=f"{safe}-fields-", dir=root))
        directory.mkdir(parents=True, exist_ok=True)
        return directory


def _permittivity(solution: ModelSolution) -> Expression | None:
    """Return ``eps_r`` as the solved model evaluates it, or ``None``.

    Evaluated through the model's own coefficient chain against the *stored*
    distance field, so the permittivity in the file is the one the solve used
    and not a second evaluation that a different distance field could move.
    """
    model = solution.model
    if not isinstance(model, CoupledModel):
        return None
    values = {field.name: solution.component(field.name) for field in model.fields}
    coefficients = model.coefficients(
        model.concentration_variables(values), solution.wall_distance_nm
    )
    permittivity: Expression = model.permittivity(solution.space.mesh, coefficients)
    return permittivity


def _fixed_charge(resolved: ResolvedCase) -> Expression | None:
    """Return the supplied fixed-charge volume density, or ``None`` if there was none.

    A run that supplied no ``inputs.charge`` writes no ``rho_fixed_C_m3``
    attribute at all. "There was no charge field" and "there was one and it was
    zero" are different runs, and a colour map of a zero field says the second.
    """
    if resolved.charge is None:
        return None
    fields = read_fields(resolved)
    if fields.charge is None:
        return None
    density: Expression = fields.charge.volume_density_C_m3()
    return density

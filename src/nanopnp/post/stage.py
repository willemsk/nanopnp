"""Stages 11 and 12 of section 5.2: the quantities of interest, and the report."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.charge.stage import fixed_charge_density, read_fields
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
from nanopnp.io.defaults import ContributedDeviation
from nanopnp.io.workspace import scratch_directory
from nanopnp.mesh.ingest import deployed_mesh
from nanopnp.numerics.measures import AXISYMMETRIC, Measures
from nanopnp.physics.models import declaration
from nanopnp.post import forces as force_post
from nanopnp.post import qoi as qoi_post
from nanopnp.post.export import export_fields
from nanopnp.post.indicator import axial_indicator
from nanopnp.solve.stage import SolveStage
from nanopnp.solve.state import STATE_FILENAME, STATE_KEY, restore

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from collections.abc import Mapping

    from nanopnp.core.hashing import Canonicalisable
    from nanopnp.io.resolved import ResolvedCase
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

BAND_FRACTION = 0.8

EXTENSION_INNER = 1.2

EXTENSION_OUTER = 3.0


class SelectionError(ValueError):
    """A word in ``outputs:`` that this run cannot produce; a ValueError."""


def membrane_band(
    data: MeshData,
    *,
    fraction: float = BAND_FRACTION,
    material: str = MEMBRANE_MATERIAL,
) -> tuple[float, float]:
    """Return the transition band ``(lower_nm, upper_nm)`` of the membrane, in nm.

    Raises
    ------
    SelectionError
        If ``fraction`` is not in (0, 1], or the mesh carries no such material.
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
    """Return the extension shell in nm, scaled to the body; SelectionError if absent."""
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
    supplied = options.get("extension_shell_nm")
    if supplied is None:
        return extension_shell(data)
    inner, outer = supplied
    return (float(inner), float(outer))


def _solution(inputs: StageInputs, *, solving: bool) -> Artefact:
    solution = inputs.upstream.get("solve")
    if solution is not None:
        return solution
    stage = SolveStage()
    return stage.run(inputs) if solving else stage.key(inputs)


def _check_selection(outputs: tuple[str, ...]) -> None:
    if "rectification" in outputs:
        raise SelectionError(
            "outputs asks for rectification, which is the two-point ratio I(+V)/I(-V); this run "
            "has one operating point. The second bias can only come from a sweep (FR-24), and "
            "inventing one would report a ratio the run did not measure"
        )


@dataclass(frozen=True)
class _Prepared:
    resolved: ResolvedCase
    data: MeshData
    case_hash: str
    solution: Artefact
    outputs: tuple[str, ...]
    band: tuple[float, float] | None
    shell: tuple[float, float] | None
    check_routes: bool


def _selected(
    quantities: qoi_post.QuantitiesOfInterest, outputs: tuple[str, ...]
) -> dict[str, Canonicalisable]:
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
    """Stage 11: a converged solution to the scalar quantities of interest."""

    name = "qoi"

    def describe(self) -> StageDescription:
        """Return the registry's description of this stage."""
        return describe(self.name)

    def key(self, inputs: StageInputs) -> QoIArtefact:
        """Return the artefact key this extraction will produce, without running it."""
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
        resolved = inputs.resolved
        ingested = deployed_mesh(resolved, inputs.upstream.get("mesh"))
        outputs = tuple(resolved.outputs)
        _check_selection(outputs)
        check_routes = bool(inputs.options.get("check_routes", True))
        shell = _shell(ingested.data, inputs.options) if "analyte_force" in outputs else None
        # A model without transport has no current to take, and its mesh may carry no membrane.
        transport = declaration(resolved.model).transport
        band = _band(ingested.data, inputs.options) if transport else None
        solution = _solution(inputs, solving=solving)
        case = inputs.upstream.get("case")
        case_hash = case.hash if case is not None else CaseArtefact(inputs.resolved.document).hash
        return _Prepared(
            resolved=resolved,
            data=ingested.data,
            case_hash=case_hash,
            solution=solution,
            outputs=outputs,
            band=band,
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

        Raises
        ------
        SelectionError
            If ``outputs:`` asks for something this run cannot produce.
        Cancelled
            If ``cancel`` turns true; no artefact is written.
        """
        check_cancelled(cancel, "the extraction")
        report(progress, 0.0, "resolving the case")
        prepared = self._prepare(inputs, solving=True)
        bias_V = qoi_post.cis_referenced_bias(prepared.resolved.bias_V, prepared.resolved.ground)
        band = prepared.band
        if band is None:
            # No transport: nothing to extract, no indicator, and nothing to restore.
            report(progress, 1.0, "the model declares no quantity of interest")
            return QoIArtefact(
                case_hash=prepared.case_hash,
                solution_hash=prepared.solution.hash,
                outputs=prepared.outputs,
                indicator_band_nm=None,
                check_routes=prepared.check_routes,
                summary={"bias_V": bias_V},
            )

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
        solution = restore(
            Path(state_path),
            resolved=inputs.resolved,
            mesh_artefact=inputs.upstream.get("mesh"),
            charge_artefact=inputs.upstream.get("charge"),
        )
        order = int(prepared.resolved.model_options.get("order", AXISYMMETRIC.element_order))
        measures = AXISYMMETRIC.at_order(order)
        mesh = solution.space.mesh

        report(progress, 0.4, "building the NUM-24 indicator")
        check_cancelled(cancel, "the indicator")
        lower, upper = band
        indicator = axial_indicator(mesh, lower_nm=lower, upper_nm=upper, order=order)

        report(progress, 0.5, "extracting the scalar quantities")
        check_cancelled(cancel, "the scalar extraction")
        quantities = qoi_post.extract(
            solution,
            measures,
            indicator,
            # With trans grounded the bias sits on cis, and the +z current responds to its negative.
            bias_V=bias_V,
            check_routes=prepared.check_routes,
        )

        summary: dict[str, Canonicalisable] = {
            "indicator_band_nm": list(band),
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
        """Return the departures this stage's options introduce."""
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
    """Stage 12: what the run wrote, and the hashes of what it was written from."""

    name = "report"

    def __init__(self, *, workspace: Path | None = None) -> None:
        self._workspace = Path(workspace) if workspace is not None else None

    def describe(self) -> StageDescription:
        """Return the registry's description of this stage."""
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
        return ("fields",) if "fields" in inputs.resolved.outputs else ()

    def _hashes(self, inputs: StageInputs, *, solving: bool) -> tuple[str, Artefact, Artefact]:
        qoi = inputs.require("qoi")
        solution = _solution(inputs, solving=solving)
        case = inputs.upstream.get("case")
        case_hash = case.hash if case is not None else CaseArtefact(inputs.resolved.document).hash
        return case_hash, qoi, solution

    def run(
        self,
        inputs: StageInputs,
        *,
        progress: Progress | None = None,
        cancel: CancelToken | None = None,
    ) -> ReportArtefact:
        """Write whatever ``outputs:`` selected and emit the stage-12 artefact.

        Raises
        ------
        Cancelled
            If ``cancel`` turns true; no artefact and no file are written.
        """
        check_cancelled(cancel, "the report")
        report(progress, 0.0, "collecting the run's artefacts")
        exports = self._exports(inputs)
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
        state_path = solution.payload.get(STATE_KEY)
        if state_path is None:
            carried = ", ".join(sorted(solution.payload)) or "nothing"
            raise KeyError(
                f"the solve artefact carries no {STATE_KEY!r} payload (the {STATE_FILENAME} "
                f"record); it carries {carried}. "
                "The IF-07 export is of the converged fields and there is nothing to export from"
            )
        resolved = inputs.resolved
        supplied = (
            read_fields(resolved)
            if resolved.charge is not None or resolved.eps_r is not None
            else None
        )
        restored = restore(
            Path(state_path),
            resolved=inputs.resolved,
            mesh_artefact=inputs.upstream.get("mesh"),
            fields=supplied,
            charge_artefact=inputs.upstream.get("charge"),
        )
        # Any model reports its scale set and the permittivity its solve used, or none.
        model = restored.model
        directory = self._directory()
        export = export_fields(
            restored,
            directory,
            scales=model.scales,
            relative_permittivity=model.relative_permittivity(restored),
            # Through stage 7's one loader: deposit, else supplied interpolant.
            fixed_charge_C_m3=fixed_charge_density(
                resolved, supplied, inputs.upstream.get("charge"), restored.space.mesh
            ),
        )
        payload = {path.name: path for path in export.paths()}
        record: dict[str, Canonicalisable] = {
            "paths": sorted(payload),
            "attributes": {key: list(value) for key, value in export.attributes.items()},
        }
        return payload, record

    def _directory(self) -> Path:
        return scratch_directory(self._workspace, "post")

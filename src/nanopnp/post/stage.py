"""Stages 11 and 12 of section 5.2: the quantities of interest, and the report."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.charge.stage import fixed_charge_density
from nanopnp.core.stages import (
    CancelToken,
    Progress,
    StageDescription,
    check_cancelled,
    describe,
    report,
)
from nanopnp.io.artefact import Artefact, CaseArtefact, QoIArtefact, ReportArtefact, StageInputs
from nanopnp.io.workspace import scratch_directory
from nanopnp.mesh.ingest import deployed_mesh
from nanopnp.numerics.measures import AXISYMMETRIC
from nanopnp.physics.models import declaration
from nanopnp.post import qoi as qoi_post
from nanopnp.post.export import export_fields, restored
from nanopnp.post.indicator import axial_indicator
from nanopnp.post.outputs import (
    EXTENSION_INNER,
    EXTENSION_OUTER,
    Extraction,
    SelectionError,
    extension_shell,
    output,
)
from nanopnp.solve.stage import SolveStage
from nanopnp.solve.state import STATE_FILENAME, STATE_KEY, restore

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from collections.abc import Mapping

    from nanopnp.core.hashing import Canonicalisable
    from nanopnp.io.resolved import ResolvedCase
    from nanopnp.mesh.adapter import MeshData

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


def _solution(
    inputs: StageInputs, *, solving: bool, workspace: Path | None = None, overwrite: bool = False
) -> Artefact:
    solution = inputs.upstream.get("solve")
    if solution is not None:
        return solution
    stage = SolveStage(
        workspace=None if workspace is None else workspace / "solve", overwrite_workspace=overwrite
    )
    return stage.run(inputs) if solving else stage.key(inputs)


def _check_selection(outputs: tuple[str, ...]) -> None:
    for word in outputs:
        refusal = output(word).refusal
        if refusal is not None:
            raise SelectionError(refusal)


def _key_parameters(
    data: MeshData, outputs: tuple[str, ...], options: Mapping[str, Canonicalisable]
) -> dict[str, Canonicalisable]:
    merged: dict[str, Canonicalisable] = {}
    for word in outputs:
        parameters = output(word).parameters
        if parameters is not None:
            merged.update(parameters(data, options))
    return merged


@dataclass(frozen=True)
class _Prepared:
    resolved: ResolvedCase
    data: MeshData
    case_hash: str
    solution: Artefact
    outputs: tuple[str, ...]
    band: tuple[float, float] | None
    parameters: Mapping[str, Canonicalisable]


_ALWAYS = frozenset(
    {
        "bias_V",
        "clamp_activations",
        "route_agreement",
        "routes_checked",
        "stabilisation_currents_A",
        "two_pi_included",
    }
)


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
            output_parameters=prepared.parameters,
        )

    def _prepare(self, inputs: StageInputs, *, solving: bool) -> _Prepared:
        resolved = inputs.resolved
        ingested = deployed_mesh(resolved, inputs.upstream.get("mesh"))
        outputs = tuple(resolved.outputs)
        _check_selection(outputs)
        parameters = _key_parameters(ingested.data, outputs, inputs.options)
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
            parameters=parameters,
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
                output_parameters=prepared.parameters,
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
        )

        extraction = Extraction(
            solution=solution,
            measures=measures,
            data=prepared.data,
            bias_V=bias_V,
            band_nm=band,
            quantities=quantities,
            parameters=prepared.parameters,
        )
        record = quantities.summary()
        summary: dict[str, Canonicalisable] = {
            "indicator_band_nm": list(band),
            **{key: value for key, value in record.items() if key in _ALWAYS},
        }
        for word in prepared.outputs:
            extract = output(word).extract
            if extract is not None:
                report(progress, 0.8, f"extracting {word}")
                check_cancelled(cancel, f"the {word} extraction")
                extracted = extract(extraction)
                clash = sorted(set(extracted) & (_ALWAYS | {"indicator_band_nm"}))
                if clash:
                    raise ValueError(
                        f"the output {word!r} would overwrite {', '.join(clash)} of the summary, "
                        "which the stage always reports"
                    )
                summary.update(extracted)

        report(progress, 1.0, f"extracted {len(prepared.outputs)} selected outputs")
        return QoIArtefact(
            case_hash=prepared.case_hash,
            solution_hash=prepared.solution.hash,
            outputs=prepared.outputs,
            indicator_band_nm=prepared.band,
            output_parameters=prepared.parameters,
            summary=summary,
        )


class ReportStage:
    """Stage 12: what the run wrote, and the hashes of what it was written from."""

    name = "report"

    def __init__(self, *, workspace: Path | None = None, overwrite_workspace: bool = False) -> None:
        self._workspace = Path(workspace) if workspace is not None else None
        self._overwrite = overwrite_workspace

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
        return tuple(word for word in inputs.resolved.outputs if output(word).export)

    def _hashes(self, inputs: StageInputs, *, solving: bool) -> tuple[str, Artefact, Artefact]:
        qoi = inputs.require("qoi")
        solution = _solution(
            inputs, solving=solving, workspace=self._workspace, overwrite=self._overwrite
        )
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
        resolved = inputs.resolved
        restored_state, supplied = restored(inputs, solution)
        # Any model reports its scale set and the permittivity its solve used, or none.
        model = restored_state.model
        directory = self._directory()
        export = export_fields(
            restored_state,
            directory,
            scales=model.scales,
            relative_permittivity=model.relative_permittivity(restored_state),
            # Through stage 7's one loader: deposit, else supplied interpolant.
            fixed_charge_C_m3=fixed_charge_density(
                resolved, supplied, inputs.upstream.get("charge"), restored_state.space.mesh
            ),
        )
        payload = {path.name: path for path in export.paths()}
        record: dict[str, Canonicalisable] = {
            "paths": sorted(payload),
            "attributes": {key: list(value) for key, value in export.attributes.items()},
        }
        return payload, record

    def _directory(self) -> Path:
        return scratch_directory(self._workspace, self.name, overwrite=self._overwrite)

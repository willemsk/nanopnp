"""Stage 10 of section 5.2: the solve (IF-01, FR-25, FR-27)."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING, Any
from zipfile import BadZipFile

from nanopnp.charge.stage import (
    FieldStage,
    ResolvedFields,
    case_fields,
    read_fields,
    require_charge_artefact,
)
from nanopnp.core.hashing import canonical
from nanopnp.core.stages import (
    CancelToken,
    Progress,
    SolveHook,
    StageDescription,
    check_cancelled,
    describe,
    report,
)
from nanopnp.io.artefact import Artefact, SolutionArtefact, StageInputs
from nanopnp.io.workspace import require_workspace, scratch_directory
from nanopnp.materials.stage import MaterialsStage
from nanopnp.mesh.ingest import IngestedMesh, MeshStage, deployed_mesh
from nanopnp.numerics.measures import AXISYMMETRIC
from nanopnp.physics.models import CoupledBoundaries, declaration
from nanopnp.solve.continuation import Rung, RungResult, run_ladder
from nanopnp.solve.state import (
    NEWTON_HISTORY_FILENAME,
    NEWTON_HISTORY_KEY,
    STATE_FILENAME,
    STATE_KEY,
    StateMismatchError,
    WarmStart,
    check_wall_distance,
    cold_start,
    ladder,
    load_initial,
    reads_distance,
    save,
    wall_distance_field,
    warm_start_payload,
)

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.core.typing import Expression, Mesh
    from nanopnp.io.resolved import ResolvedCase
    from nanopnp.numerics.gates import WallDistanceMeasurement
    from nanopnp.numerics.measures import Measures
    from nanopnp.numerics.newton import NewtonStep
    from nanopnp.physics.models import ModelSolution

logger = logging.getLogger(__name__)


LOAD_FRACTION = 0.05


def _input_hashes(mesh: Artefact, materials: Artefact, fields: Artefact | None) -> dict[str, str]:
    hashes = {"mesh": mesh.hash, "materials": materials.hash}
    if fields is not None:
        hashes["charge"] = fields.hash
    return hashes


def _field_summary(fields: ResolvedFields) -> dict[str, object]:
    summary = fields.summary()
    return {"fields": summary} if summary else {}


def _wall_distance_summary(measured: WallDistanceMeasurement | None) -> dict[str, object]:
    return {} if measured is None else {"wall_distance": measured.summary()}


class SolveStage:
    """Stage 10: a case and a mesh to a converged state and its record."""

    name = "solve"

    def __init__(
        self,
        *,
        workspace: Path | None = None,
        overwrite_workspace: bool = False,
        warm_start: Artefact | None = None,
        cold_reason: str = "",
        solve_hook: SolveHook | None = None,
    ) -> None:
        self._workspace = Path(workspace) if workspace is not None else None
        self._overwrite = overwrite_workspace
        self._warm_start = warm_start
        self._cold_reason = cold_reason
        self._solve_hook = solve_hook

    def with_solve_hook(self, hook: SolveHook) -> SolveStage:
        """Return a copy of this stage reporting its progress through ``hook``."""
        return SolveStage(
            workspace=self._workspace,
            overwrite_workspace=self._overwrite,
            warm_start=self._warm_start,
            cold_reason=self._cold_reason,
            solve_hook=hook,
        )

    def describe(self) -> StageDescription:
        """Return the registry's description of this stage."""
        return describe(self.name)

    def key(self, inputs: StageInputs) -> SolutionArtefact:
        """Return the artefact key this case will produce, without solving it."""
        resolved, ingested, mesh, materials, fields, supplied = self._prepare(inputs, load=False)
        del ingested, supplied
        return SolutionArtefact(
            parameters=resolved.solve_provenance,
            inputs=_input_hashes(mesh, materials, fields),
        )

    def _prepare(
        self, inputs: StageInputs, *, load: bool
    ) -> tuple[
        ResolvedCase, IngestedMesh, Artefact, Artefact, Artefact | None, ResolvedFields | None
    ]:
        resolved = inputs.resolved
        mesh = inputs.upstream.get("mesh")
        ingested = deployed_mesh(resolved, mesh)
        if mesh is None:
            mesh = MeshStage().artefact(ingested)
        materials = inputs.upstream.get("materials")
        if materials is None:
            materials = MaterialsStage().run(StageInputs(resolved=inputs.resolved))
        fields = inputs.upstream.get("charge")
        # A deposited charge comes only from the stage-7 artefact handed down.
        require_charge_artefact(resolved, fields)
        # Read, not gated: the key must not need an integral over the mesh.
        supplied: ResolvedFields | None = None
        if (resolved.charge is not None or resolved.eps_r is not None) and (load or fields is None):
            supplied = read_fields(resolved)
        if fields is None and supplied is not None:
            fields = FieldStage().artefact(supplied, mesh.hash, resolved=resolved)
        return resolved, ingested, mesh, materials, fields, supplied

    def run(
        self,
        inputs: StageInputs,
        *,
        progress: Progress | None = None,
        cancel: CancelToken | None = None,
    ) -> SolutionArtefact:
        """Solve the case and emit the stage-10 artefact."""
        check_cancelled(cancel, "the solve")
        # The payload is written only after the ladder has run; refuse a missing workspace first.
        scratch_directory(self._workspace, self.name, overwrite=self._overwrite)
        report(progress, 0.0, "reading and gating the mesh")
        resolved, ingested, mesh_artefact, materials, fields_artefact, supplied = self._prepare(
            inputs, load=True
        )

        report(progress, 0.0, f"loading the mesh from {ingested.source.name}")
        check_cancelled(cancel, "loading the mesh")
        mesh = ingested.mesh
        order = int(resolved.model_options.get("order", AXISYMMETRIC.element_order))
        measures = AXISYMMETRIC.at_order(order)

        if reads_distance(resolved):
            report(progress, LOAD_FRACTION / 2, "solving for the wall distance field")
            check_cancelled(cancel, "the wall-distance solve")
        distance: Expression = wall_distance_field(resolved, mesh, order=order)
        # NUM-34 on the field the corrections read: a low sample would be clamped (PHY-02)
        # into a plausible wrong current.
        wall_distance = check_wall_distance(
            resolved, mesh, distance, coordinates=measures.coordinate_names
        )

        if supplied is not None or resolved.deposits_charge:
            report(progress, LOAD_FRACTION, "gating the supplied fields, reading the deposit")
            check_cancelled(cancel, "the fields")
        # Gated, not re-read: the reference table is 77 MB of text and two reads can key
        # one field and assemble another.
        fields = case_fields(
            resolved, supplied, fields_artefact, mesh, measures=measures, cancel=cancel
        )

        rungs = ladder(resolved, mesh, measures, distance, fields)
        warm, cold_reason = self._warm(
            resolved,
            mesh,
            measures,
            distance,
            fields,
            mesh_content_hash=ingested.content_hash,
        )
        if warm is not None:
            # The ladder's last rung is the target point; the rest is a path the
            # neighbour already supplies.
            rungs = rungs[-1:]
        history: list[dict[str, Any]] = []
        prepared, on_rung, on_solved = self._instrumented(
            resolved, rungs, history, progress=progress, cancel=cancel
        )
        result = run_ladder(
            prepared,
            initial=None if warm is None else warm.solution,
            on_rung=on_rung,
            on_solved=on_solved,
        )
        report(progress, 1.0, f"converged in {result.iterations} Newton iterations")

        payload = self._write(
            result.solution,
            resolved=resolved,
            mesh_content_hash=ingested.content_hash,
            boundaries=prepared[-1].boundaries,
        )
        payload[NEWTON_HISTORY_KEY] = self._write_history(history)
        return SolutionArtefact(
            parameters=resolved.solve_provenance,
            inputs=_input_hashes(mesh_artefact, materials, fields_artefact),
            payload=payload,
            summary={
                **result.summary(),
                **_field_summary(fields),
                **_wall_distance_summary(wall_distance),
                "warm_start": cold_start(cold_reason) if warm is None else warm.summary(),
            },
        )

    def _warm(
        self,
        resolved: ResolvedCase,
        mesh: Mesh,
        measures: Measures,
        distance: Expression,
        fields: ResolvedFields,
        *,
        mesh_content_hash: str,
    ) -> tuple[WarmStart | None, str]:
        if self._warm_start is None:
            return None, self._cold_reason or "no warm start was offered to this solve"
        try:
            payload = warm_start_payload(self._warm_start)
            found = load_initial(
                payload,
                resolved=resolved,
                mesh=mesh,
                measures=measures,
                distance=distance,
                fields=fields,
                mesh_content_hash=mesh_content_hash,
                source=self._warm_start.hash,
            )
        except (StateMismatchError, OSError, ValueError, BadZipFile) as error:
            logger.warning(
                "warm start from %s refused, climbing the ladder cold: %s",
                self._warm_start.short_hash,
                error,
            )
            return None, f"the neighbour's state was refused: {error}"
        return found, ""

    def _instrumented(
        self,
        resolved: ResolvedCase,
        rungs: tuple[Rung, ...],
        history: list[dict[str, Any]],
        *,
        progress: Progress | None,
        cancel: CancelToken | None,
    ) -> tuple[tuple[Rung, ...], Callable[[int, Rung], None], Callable[[int, RungResult], None]]:
        settings = resolved.newton
        hook = self._solve_hook
        span = 1.0 - LOAD_FRACTION
        total = max(len(rungs), 1)
        iterations = max(settings.max_iterations, 1)
        # One decision for both the hook and the injection, so they cannot disagree.
        reporting = tuple(declaration(rung.model.name).reports_newton for rung in rungs)
        # A cell: ``solve`` knows nothing of the ladder.
        current = [0]

        def on_rung(index: int, rung: Rung) -> None:
            current[0] = index
            history.append({"name": rung.name, "stage": rung.stage, "steps": []})
            check_cancelled(cancel, f"rung {rung.name!r}")
            report(progress, LOAD_FRACTION + span * index / total, f"rung {rung.name}")
            if hook is not None:
                hook.rung(
                    rung.name,
                    rung.stage,
                    index,
                    len(rungs),
                    reporting[index],
                    settings.relative_tolerance,
                )

        def on_solved(index: int, record: RungResult) -> None:
            if hook is not None:
                hook.rung_solved(record.name, record.seconds, record.iterations)

        def on_step(step: NewtonStep) -> None:
            history[-1]["steps"].append(
                {
                    "iteration": step.iteration,
                    "residual": step.residual,
                    "update": step.update,
                    "damping": step.damping,
                    "trials": step.trials,
                    "forced": step.forced,
                }
            )
            check_cancelled(cancel, f"Newton iteration {step.iteration}")
            within = min(1.0, step.iteration / iterations)
            report(
                progress,
                LOAD_FRACTION + span * (current[0] + within) / total,
                f"iteration {step.iteration}, residual {step.residual:.3e}",
            )
            if hook is not None:
                hook.step(
                    step.iteration,
                    step.residual,
                    step.update,
                    step.damping,
                    step.trials,
                    step.forced,
                )

        prepared = tuple(
            replace(
                rung,
                solve_kwargs={
                    **dict(rung.solve_kwargs),
                    "settings": settings,
                    "solver": resolved.linear_solver,
                    **({"callback": on_step} if takes_callback else {}),
                },
            )
            for rung, takes_callback in zip(rungs, reporting, strict=True)
        )
        return prepared, on_rung, on_solved

    def _write(
        self,
        solution: ModelSolution,
        *,
        resolved: ResolvedCase,
        mesh_content_hash: str,
        boundaries: CoupledBoundaries,
    ) -> dict[str, Path]:
        directory = scratch_directory(self._workspace, self.name, overwrite=self._overwrite)
        target = save(
            solution,
            directory / STATE_FILENAME,
            resolved=resolved,
            mesh_content_hash=mesh_content_hash,
            boundaries=boundaries,
        )
        return {STATE_KEY: target}

    def _write_history(self, history: list[dict[str, Any]]) -> Path:
        record = require_workspace(self._workspace, self.name) / NEWTON_HISTORY_FILENAME
        record.write_bytes(canonical({"rungs": history}))
        return record

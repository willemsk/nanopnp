"""Stage 10 of section 5.2: the solve (IF-01, FR-25, FR-27).

The stage that turns a case document into a converged state. Everything it needs
is already built: :func:`nanopnp.io.case.resolve` turns the document into models
and settings, :func:`nanopnp.solve.continuation.default_ladder` builds the NUM-18
ladder, and :func:`nanopnp.solve.continuation.run_ladder` climbs it. What this
module adds is the three things FR-27 asks of every stage.

**Invocable alone.** The mesh is ingested from the file the case names by stage 6
(:mod:`nanopnp.mesh.ingest`) when it was not handed down, and the materials
artefact is recomputed when it was not supplied. Both routes produce the same
digest, so running the solve on its own and running it after stages 6 and 8 key
the same cache entry rather than two.

**Cancellable.** Two granularities, because one is not enough: ``on_rung`` stops
the ladder between rungs, which is the only point the two Poisson-Boltzmann
stages offer, and the damped-Newton callback stops a coupled rung between
iterations. A cancelled run raises before any artefact exists, so the store never
holds a partial solve (section 5.3.2).

**Introspectable.** ``describe()`` comes from the registry, which is what lets the
CLI and the GUI say what this stage takes without importing NGSolve.

The mesh enters the digest as the stage-6 artefact's hash, never as its path: a
mesh substituted by hand (FR-27) is then a changed input by construction, the
same mesh under another name is the same run, and — because that artefact is
keyed on the mesh's *contents* and on the vocabulary mapping applied to it — a
mesh rewritten with a different header is not a second solve while the same file
read under a different ``inputs.mesh.groups`` map is.

Every mesh reaching this stage has been through the section 5.2.2 gate, so
nothing here checks a boundary name again. That is the point of there being one
route in: a boundary this stage selected on and the mesh did not supply would
carry the natural condition and be silently free (NUM-06), and stage 6 is where
that is caught.
"""

from __future__ import annotations

import tempfile
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.charge.stage import FieldStage, ResolvedFields, load_fields, read_fields
from nanopnp.core.constants import thermal_voltage
from nanopnp.core.paths import store_root
from nanopnp.core.stages import (
    CancelToken,
    Progress,
    StageDescription,
    check_cancelled,
    describe,
    report,
)
from nanopnp.io.artefact import Artefact, SolutionArtefact, StageInputs
from nanopnp.io.case import COUPLED_MODELS, resolve
from nanopnp.materials.stage import MaterialsStage
from nanopnp.mesh.ingest import IngestedMesh, MeshStage, ingest
from nanopnp.physics.coefficients import SATURATED_WALL_DISTANCE_NM
from nanopnp.physics.measures import AXISYMMETRIC, Measures
from nanopnp.physics.models import CoupledModel, create
from nanopnp.solve.continuation import ELECTRODES, Rung, default_ladder, run_ladder

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.core.typing import Expression, GridFunction, Mesh
    from nanopnp.io.case import ResolvedCase
    from nanopnp.materials.electrolyte import Electrolyte
    from nanopnp.solve.newton import NewtonStep

WORKSPACE_DIRNAME = "tmp"
"""Directory under the store root the payload is written to before it is stored."""

LOAD_FRACTION = 0.05
"""Share of the progress bar spent loading the mesh and the distance field."""


def _reads_wall(electrolyte: Electrolyte) -> bool:
    """Return whether any resolved correction of ``electrolyte`` evaluates ``d``.

    Asked of the corrections rather than of the model name, exactly as
    :func:`~nanopnp.solve.continuation.default_ladder` asks it: a run whose wall
    factors are all off must not pay for a screened-Poisson solve, and must not
    record a distance field nothing read.
    """
    return any(
        bool(getattr(correction, "use_wall", False))
        for correction in electrolyte.corrections.values()
    )


def _single_rung(
    resolved: ResolvedCase, mesh: Mesh, measures: Measures, fields: ResolvedFields
) -> Rung:
    """Return the one rung a case with ``continuation: none`` solves.

    Cold, at the target operating point. NUM-18 exists because that does not
    converge over most of the FR-17 envelope; the switch is offered because the
    electrostatic models of PHY-21 are not on the ladder at all, and because an
    ablation needs to be able to ask for the cold solve and watch it fail.
    """
    options = dict(resolved.model_options)
    if resolved.model in COUPLED_MODELS:
        model = create(
            resolved.model,
            electrolyte=resolved.electrolyte,
            concentration_M=resolved.concentration_M,
            **options,
        )
    else:
        model = create(resolved.model, **options)
    driven = next(iter(ELECTRODES - {resolved.ground}))
    supplied: dict[str, Expression] = {}
    if isinstance(model, CoupledModel):
        # The electrostatic models of PHY-21 take neither: ``pb`` screens with a
        # Debye length and carries no material permittivity, and handing one a
        # keyword it does not take aborts the run with a message about an
        # argument rather than about the physics.
        if fields.charge is not None:
            supplied["fixed_charge"] = (
                fields.charge.volume_density_C_m3() / model.scales.charge_density_C_m3
            )
        if fields.eps_r is not None:
            supplied["solid_fraction"] = fields.eps_r.chi()
    # Taken from the temperature rather than from ``model.scales``: the
    # electrostatic models of PHY-21 carry no scale set, and every model of the
    # table nondimensionalises the potential by the same ``V_T = RT/F`` (NUM-09).
    thermal_V = thermal_voltage(resolved.temperature_K)
    return Rung(
        name=f"target-{resolved.model}",
        stage=1,
        model=model,
        mesh=mesh,
        measures=measures,
        solve_kwargs={
            "potential_values": mesh.BoundaryCF(
                {resolved.ground: 0.0, driven: resolved.bias_V / thermal_V}
            ),
            **supplied,
        },
    )


def _input_hashes(mesh: Artefact, materials: Artefact, fields: Artefact | None) -> dict[str, str]:
    """Return the upstream hashes a solution artefact is keyed on (section 5.3.2).

    The fields enter by their artefact's hash and never by their paths, so a
    field substituted by hand is a changed input by construction and the same
    table under another name is the same run. A case supplying no field carries
    no entry at all rather than a null one: "there was no charge field" and
    "there was one, and it was empty" are different runs.
    """
    hashes = {"mesh": mesh.hash, "materials": materials.hash}
    if fields is not None:
        hashes["charge"] = fields.hash
    return hashes


def _field_summary(fields: ResolvedFields) -> dict[str, object]:
    """Return the solve summary's record of the supplied fields, if any."""
    summary = fields.summary()
    return {"fields": summary} if summary else {}


class SolveStage:
    """Stage 10: a case and a mesh to a converged state and its record."""

    name = "solve"

    def __init__(self, *, workspace: Path | None = None) -> None:
        """Build the stage.

        Parameters
        ----------
        workspace
            Directory the converged state is written to before the store copies
            it in. Defaults to a fresh directory under the store root, so that a
            solve run without a store still leaves its fields somewhere the
            caller can find them.
        """
        self._workspace = Path(workspace) if workspace is not None else None

    def describe(self) -> StageDescription:
        """Return the registry's description of this stage (FR-27)."""
        return describe(self.name)

    def key(self, inputs: StageInputs) -> SolutionArtefact:
        """Return the artefact key this case will produce, without solving it.

        The cache key of section 5.3.2 has to be computable *before* the stage
        runs, or :meth:`nanopnp.io.store.Store.get_or_compute` cannot decide
        whether to run it. For this stage that is the resolved case's
        provenance, the mesh file's digest and the materials artefact's hash —
        all of them cheap, none of them touching NGSolve.

        Returns
        -------
        SolutionArtefact
            The same schema, parameters and input hashes :meth:`run` returns,
            with no payload and no summary. Its
            :attr:`~nanopnp.io.artefact.Artefact.hash` is therefore equal to the
            hash of the artefact the solve will produce, which is what
            ``get_or_compute`` checks on the way out.
        """
        resolved, ingested, mesh, materials, fields = self._prepare(inputs)
        del ingested
        return SolutionArtefact(
            parameters=resolved.provenance,
            inputs=_input_hashes(mesh, materials, fields),
        )

    def _prepare(
        self, inputs: StageInputs
    ) -> tuple[ResolvedCase, IngestedMesh, Artefact, Artefact, Artefact | None]:
        """Resolve the case, ingest and gate the mesh, and obtain the two artefacts.

        Shared by :meth:`key` and :meth:`run` so that the key the store is asked
        about and the key the solve produces cannot be built two different ways.

        The mesh is ingested here even when stage 6 handed its artefact down,
        because the solve needs the geometry and not only the key; the supplied
        artefact is then what the digest is taken over, exactly as the materials
        artefact is. A hand-substituted one (FR-27) therefore changes the key
        rather than being checked against a recomputed one — section 5.3.2 asks
        for it recorded, not refused.
        """
        resolved = resolve(inputs.case)
        ingested = ingest(resolved.mesh, resolved)
        mesh = inputs.upstream.get("mesh")
        if mesh is None:
            mesh = MeshStage().artefact(ingested)
        materials = inputs.upstream.get("materials")
        if materials is None:
            materials = MaterialsStage().run(StageInputs(case=inputs.case))
        fields = inputs.upstream.get("charge")
        if fields is None and (resolved.charge is not None or resolved.eps_r is not None):
            # Read, not gated: the key must be computable without integrating
            # over the mesh, and the gates run in :meth:`run` where the fields
            # are actually assembled (section 5.3.2, stage 7).
            fields = FieldStage().artefact(read_fields(resolved), mesh.hash)
        return resolved, ingested, mesh, materials, fields

    def run(
        self,
        inputs: StageInputs,
        *,
        progress: Progress | None = None,
        cancel: CancelToken | None = None,
    ) -> SolutionArtefact:
        """Solve the case and emit the stage-10 artefact.

        Parameters
        ----------
        inputs
            The case, and optionally the ``mesh`` artefact of stage 6 and the
            ``materials`` artefact of stage 8. When either is absent the stage
            recomputes it, which keeps the artefact's key independent of how the
            run was invoked.
        progress
            Called with a fraction in [0, 1] and a message, monotone and ending
            at 1. Within the ladder the fraction is the rung index refined by
            Newton iteration over ``max_iterations``.
        cancel
            Checked on entry, between rungs, and at every accepted Newton step.

        Returns
        -------
        SolutionArtefact
            Keyed on the resolved case, the stage-6 mesh artefact and the
            materials artefact; carrying the ladder's per-rung record as its summary and
            the converged state as its payload.

        Raises
        ------
        Cancelled
            If ``cancel`` turns true. No artefact is written.
        """
        check_cancelled(cancel, "the solve")
        report(progress, 0.0, "reading and gating the mesh")
        resolved, ingested, mesh_artefact, materials, fields_artefact = self._prepare(inputs)

        report(progress, 0.0, f"loading the mesh from {ingested.source.name}")
        check_cancelled(cancel, "loading the mesh")
        mesh = ingested.mesh
        order = int(resolved.model_options.get("order", AXISYMMETRIC.element_order))
        measures = replace(AXISYMMETRIC, element_order=order)

        distance: Expression = SATURATED_WALL_DISTANCE_NM
        if _reads_wall(resolved.electrolyte):
            report(progress, LOAD_FRACTION / 2, "solving for the wall distance field")
            check_cancelled(cancel, "the wall-distance solve")
            from nanopnp.mesh.distance import wall_distance

            distance = wall_distance(
                mesh,
                resolved.wall_distance_sources,
                order=order,
                max_distance_nm=resolved.wall_distance_max_nm,
            )

        fields = ResolvedFields(charge=None, conservation=None, eps_r=None, material_means=())
        if resolved.charge is not None or resolved.eps_r is not None:
            report(progress, LOAD_FRACTION, "reading and gating the supplied fields")
            check_cancelled(cancel, "the supplied fields")
            fields = load_fields(resolved, mesh, measures=measures, cancel=cancel)

        prepared, on_rung = self._instrumented(
            resolved,
            self._ladder(resolved, mesh, measures, distance, fields),
            progress=progress,
            cancel=cancel,
        )
        result = run_ladder(prepared, on_rung=on_rung)
        report(progress, 1.0, f"converged in {result.iterations} Newton iterations")

        payload = self._write(result.solution.state, resolved.name)
        return SolutionArtefact(
            parameters=resolved.provenance,
            inputs=_input_hashes(mesh_artefact, materials, fields_artefact),
            payload=payload,
            summary={**result.summary(), **_field_summary(fields)},
        )

    def _ladder(
        self,
        resolved: ResolvedCase,
        mesh: Mesh,
        measures: Measures,
        distance: Expression,
        fields: ResolvedFields,
    ) -> tuple[Rung, ...]:
        """Return the rungs this case solves, ladder or single (NUM-18)."""
        if resolved.continuation == "none":
            return (_single_rung(resolved, mesh, measures, fields),)
        # The producer pipeline is still v0.9, so the charge a run carries is the
        # one it was handed through ``inputs.charge`` (FR-27, stage 7). With no
        # field supplied the stage-4 ramp is empty rather than silently zero, and
        # the ladder is the same one WP5 measured.
        return default_ladder(
            mesh,
            concentration_M=resolved.concentration_M,
            bias_V=resolved.bias_V,
            ground=resolved.ground,
            electrolyte=resolved.electrolyte,
            wall_distance_nm=distance,
            measures=measures,
            corrections_active=resolved.model == "epnp-ns",
            switches=resolved.electrolyte.switches,
            # The ladder builds its own models, so the case's ``physics.
            # solid_permittivities`` reaches them only here. Omitting it leaves
            # the membrane at the electrolyte's eps_r -- 24 times too large, and
            # a plausible wrong current with no diagnostic (PHY-03, PHY-20).
            solid_permittivities=dict(resolved.document.physics.solid_permittivities),
            fixed_charge_field=(
                None if fields.charge is None else fields.charge.volume_density_C_m3()
            ),
            solid_fraction=None if fields.eps_r is None else fields.eps_r.chi(),
        )

    def _instrumented(
        self,
        resolved: ResolvedCase,
        rungs: tuple[Rung, ...],
        *,
        progress: Progress | None,
        cancel: CancelToken | None,
    ) -> tuple[tuple[Rung, ...], Callable[[int, Rung], None]]:
        """Return ``rungs`` carrying this run's solver settings, and the rung hook.

        The settings are injected here rather than passed to
        :func:`~nanopnp.solve.continuation.default_ladder` because they are not
        the ladder's business: the ladder decides the *path*, the case decides
        how each rung is solved (NUM-16, NUM-20).

        The Newton callback goes only to the coupled rungs. An electrostatic
        model's ``solve`` rejects keywords it does not take, on purpose, so
        handing one a callback would abort the run at stage 1 with a message
        about an unknown argument rather than about the physics. That is also
        why cancellation cannot ride the callback alone, and why ``on_rung``
        exists.
        """
        settings = resolved.newton
        span = 1.0 - LOAD_FRACTION
        total = max(len(rungs), 1)
        iterations = max(settings.max_iterations, 1)
        # The rung the Newton callback is reporting within. A closure cell rather
        # than an argument because ``solve`` knows nothing about the ladder.
        current = [0]

        def on_rung(index: int, rung: Rung) -> None:
            current[0] = index
            check_cancelled(cancel, f"rung {rung.name!r}")
            report(progress, LOAD_FRACTION + span * index / total, f"rung {rung.name}")

        def on_step(step: NewtonStep) -> None:
            check_cancelled(cancel, f"Newton iteration {step.iteration}")
            within = min(1.0, step.iteration / iterations)
            report(
                progress,
                LOAD_FRACTION + span * (current[0] + within) / total,
                f"iteration {step.iteration}, residual {step.residual:.3e}",
            )

        prepared = tuple(
            replace(
                rung,
                solve_kwargs={
                    **dict(rung.solve_kwargs),
                    "settings": settings,
                    "solver": resolved.linear_solver,
                    **({"callback": on_step} if isinstance(rung.model, CoupledModel) else {}),
                },
            )
            for rung in rungs
        )
        return prepared, on_rung

    def _write(self, state: GridFunction, name: str) -> dict[str, Path]:
        """Write the converged state and return the payload map.

        The state is written before the artefact exists because the artefact
        names it: the payload is outside the content hash (section 5.3.2), and
        the store hashes each file as it copies it in.
        """
        directory = self._workspace
        if directory is None:
            root = store_root() / WORKSPACE_DIRNAME
            root.mkdir(parents=True, exist_ok=True)
            safe = "".join(character if character.isalnum() else "-" for character in name)
            directory = Path(tempfile.mkdtemp(prefix=f"{safe}-", dir=root))
        directory.mkdir(parents=True, exist_ok=True)
        target = directory / "state.gfu"
        state.Save(str(target))
        return {"state": target}

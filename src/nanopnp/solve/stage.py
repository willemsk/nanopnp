"""Stage 10 of section 5.2: the solve (IF-01, FR-25, FR-27).

The stage that turns a case document into a converged state. Everything it needs
is already built: :func:`nanopnp.io.case.resolve` turns the document into models
and settings, :func:`nanopnp.solve.continuation.default_ladder` builds the NUM-18
ladder, and :func:`nanopnp.solve.continuation.run_ladder` climbs it. What this
module adds is the three things FR-27 asks of every stage.

**Invocable alone.** The mesh is loaded from the file the case names, and the
materials artefact is recomputed when it was not supplied. Both routes produce
the same digest, so running the solve on its own and running it after stage 8
key the same cache entry rather than two.

**Cancellable.** Two granularities, because one is not enough: ``on_rung`` stops
the ladder between rungs, which is the only point the two Poisson-Boltzmann
stages offer, and the damped-Newton callback stops a coupled rung between
iterations. A cancelled run raises before any artefact exists, so the store never
holds a partial solve (section 5.3.2).

**Introspectable.** ``describe()`` comes from the registry, which is what lets the
CLI and the GUI say what this stage takes without importing NGSolve.

The mesh enters the digest as the hash of its *file*, never as its path: a mesh
substituted by hand (FR-27) is then a changed input by construction, and the same
mesh under another name is the same run.
"""

from __future__ import annotations

import tempfile
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.core.constants import thermal_voltage
from nanopnp.core.hashing import file_hash
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
from nanopnp.io.case import COUPLED_MODELS, UnsupportedCaseSection, resolve
from nanopnp.materials.stage import MaterialsStage
from nanopnp.physics.coefficients import SATURATED_WALL_DISTANCE_NM
from nanopnp.physics.measures import AXISYMMETRIC, Measures
from nanopnp.physics.models import CoupledModel, create
from nanopnp.solve.continuation import ELECTRODES, Rung, default_ladder, run_ladder

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.core.typing import Expression, GridFunction, Mesh
    from nanopnp.io.case import ResolvedCase, SuppliedArtefact
    from nanopnp.materials.electrolyte import Electrolyte
    from nanopnp.solve.newton import NewtonStep

MESH_SUFFIXES: tuple[str, ...] = (".vol", ".vol.gz")
"""Mesh files this release loads: netgen's own format, which round-trips the
boundary and material names the boundary vocabulary is written against."""

WORKSPACE_DIRNAME = "tmp"
"""Directory under the store root the payload is written to before it is stored."""

LOAD_FRACTION = 0.05
"""Share of the progress bar spent loading the mesh and the distance field."""


def _mesh_path(supplied: SuppliedArtefact) -> Path:
    """Return the mesh file the case names, checked.

    Raises
    ------
    UnsupportedCaseSection
        If the mesh is named by store hash rather than by path, which needs the
        meshing pipeline of v0.9.
    FileNotFoundError
        If the file is not there.
    ValueError
        If it is not one of :data:`MESH_SUFFIXES`. A mesh in another format would
        load without its boundary names, and every essential condition would then
        be applied to nothing at all.
    """
    if supplied.path is None:
        raise UnsupportedCaseSection(
            "inputs.mesh: artefact: names a mesh in the store, which the meshing "
            "pipeline of v0.9 fills; supply inputs.mesh: path: instead"
        )
    path = supplied.path
    if not any(path.name.endswith(suffix) for suffix in MESH_SUFFIXES):
        raise ValueError(
            f"inputs.mesh.path {str(path)!r} is not a netgen mesh; this release reads "
            f"{', '.join(MESH_SUFFIXES)}, which carry the boundary and material names "
            "the boundary conditions are written against"
        )
    if not path.is_file():
        raise FileNotFoundError(f"inputs.mesh.path {str(path)!r} does not exist")
    return path


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


def _single_rung(resolved: ResolvedCase, mesh: Mesh, measures: Measures) -> Rung:
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
            )
        },
    )


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
        resolved, mesh_path, materials = self._prepare(inputs)
        return SolutionArtefact(
            parameters=resolved.provenance,
            inputs={"mesh": file_hash(mesh_path), "materials": materials.hash},
        )

    def _prepare(self, inputs: StageInputs) -> tuple[ResolvedCase, Path, Artefact]:
        """Resolve the case, check the mesh file and obtain the materials artefact.

        Shared by :meth:`key` and :meth:`run` so that the key the store is asked
        about and the key the solve produces cannot be built two different ways.
        """
        resolved = resolve(inputs.case)
        mesh_path = _mesh_path(resolved.mesh)
        materials = inputs.upstream.get("materials")
        if materials is None:
            materials = MaterialsStage().run(StageInputs(case=inputs.case))
        return resolved, mesh_path, materials

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
            The case, and optionally the ``materials`` artefact of stage 8. When
            it is absent the stage recomputes it, which costs one YAML read and
            keeps the artefact's key independent of how the run was invoked.
        progress
            Called with a fraction in [0, 1] and a message, monotone and ending
            at 1. Within the ladder the fraction is the rung index refined by
            Newton iteration over ``max_iterations``.
        cancel
            Checked on entry, between rungs, and at every accepted Newton step.

        Returns
        -------
        SolutionArtefact
            Keyed on the resolved case, the mesh file's digest and the materials
            artefact; carrying the ladder's per-rung record as its summary and
            the converged state as its payload.

        Raises
        ------
        Cancelled
            If ``cancel`` turns true. No artefact is written.
        """
        check_cancelled(cancel, "the solve")
        resolved, mesh_path, materials = self._prepare(inputs)

        report(progress, 0.0, f"loading the mesh from {mesh_path.name}")
        check_cancelled(cancel, "loading the mesh")
        import ngsolve as ngs

        mesh = ngs.Mesh(str(mesh_path))
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

        prepared, on_rung = self._instrumented(
            resolved,
            self._ladder(resolved, mesh, measures, distance),
            progress=progress,
            cancel=cancel,
        )
        result = run_ladder(prepared, on_rung=on_rung)
        report(progress, 1.0, f"converged in {result.iterations} Newton iterations")

        payload = self._write(result.solution.state, resolved.name)
        return SolutionArtefact(
            parameters=resolved.provenance,
            inputs={"mesh": file_hash(mesh_path), "materials": materials.hash},
            payload=payload,
            summary=dict(result.summary()),
        )

    def _ladder(
        self,
        resolved: ResolvedCase,
        mesh: Mesh,
        measures: Measures,
        distance: Expression,
    ) -> tuple[Rung, ...]:
        """Return the rungs this case solves, ladder or single (NUM-18)."""
        if resolved.continuation == "none":
            return (_single_rung(resolved, mesh, measures),)
        # Phase 1 solves an uncharged pore: the charge pipeline is stages 4 and 5
        # of section 5.2 and lands in v0.9, and ``resolve`` refuses a case that
        # names ``inputs.charge``. So the stage-4 ramp is empty here rather than
        # silently zero, and the ladder is the same one WP5 measured.
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

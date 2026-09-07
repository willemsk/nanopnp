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

from nanopnp.charge.stage import FieldStage, ResolvedFields, gate_fields, read_fields
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
from nanopnp.io.case import resolve
from nanopnp.materials.stage import MaterialsStage
from nanopnp.mesh.ingest import IngestedMesh, MeshStage, ingest
from nanopnp.physics.measures import AXISYMMETRIC
from nanopnp.physics.models import CoupledBoundaries, CoupledModel
from nanopnp.solve.continuation import Rung, run_ladder
from nanopnp.solve.state import (
    STATE_FILENAME,
    ladder,
    reads_wall,
    save,
    wall_distance_field,
)

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.core.typing import Expression
    from nanopnp.io.case import ResolvedCase
    from nanopnp.physics.models import ModelSolution
    from nanopnp.solve.newton import NewtonStep

WORKSPACE_DIRNAME = "tmp"
"""Directory under the store root the payload is written to before it is stored."""

LOAD_FRACTION = 0.05
"""Share of the progress bar spent loading the mesh and the distance field."""


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
        *solve* provenance, the mesh file's digest and the materials artefact's
        hash — all of them cheap, none of them touching NGSolve. The case's
        ``name`` and ``outputs`` are excluded from that provenance because
        neither reaches the operator, so asking a converged case for one more
        quantity is a cache hit rather than another solve
        (:attr:`~nanopnp.io.case.ResolvedCase.solve_provenance`).

        Returns
        -------
        SolutionArtefact
            The same schema, parameters and input hashes :meth:`run` returns,
            with no payload and no summary. Its
            :attr:`~nanopnp.io.artefact.Artefact.hash` is therefore equal to the
            hash of the artefact the solve will produce, which is what
            ``get_or_compute`` checks on the way out.
        """
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
        """Resolve the case, ingest and gate the mesh, and obtain the two artefacts.

        Shared by :meth:`key` and :meth:`run` so that the key the store is asked
        about and the key the solve produces cannot be built two different ways.

        The mesh is ingested here even when stage 6 handed its artefact down,
        because the solve needs the geometry and not only the key; the supplied
        artefact is then what the digest is taken over, exactly as the materials
        artefact is. A hand-substituted one (FR-27) therefore changes the key
        rather than being checked against a recomputed one — section 5.3.2 asks
        for it recorded, not refused.

        Parameters
        ----------
        load
            Whether the caller will go on to gate and assemble the fields. The
            grids are read once here and handed back either way, because the
            stage-7 key *is* their digest; ``load=False`` only lets :meth:`key`
            skip the read entirely when stage 7 already handed its artefact
            down, and the digest is therefore known without opening a file.
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
        # Read, not gated: the key must be computable without integrating over
        # the mesh, and the gates run in :meth:`run`, on these same grids
        # (section 5.3.2, stage 7).
        supplied: ResolvedFields | None = None
        if (resolved.charge is not None or resolved.eps_r is not None) and (load or fields is None):
            supplied = read_fields(resolved)
        if fields is None and supplied is not None:
            fields = FieldStage().artefact(supplied, mesh.hash)
        return resolved, ingested, mesh, materials, fields, supplied

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
        resolved, ingested, mesh_artefact, materials, fields_artefact, supplied = self._prepare(
            inputs, load=True
        )

        report(progress, 0.0, f"loading the mesh from {ingested.source.name}")
        check_cancelled(cancel, "loading the mesh")
        mesh = ingested.mesh
        order = int(resolved.model_options.get("order", AXISYMMETRIC.element_order))
        measures = replace(AXISYMMETRIC, element_order=order)

        if reads_wall(resolved.electrolyte):
            report(progress, LOAD_FRACTION / 2, "solving for the wall distance field")
            check_cancelled(cancel, "the wall-distance solve")
        distance: Expression = wall_distance_field(resolved, mesh, order=order)

        fields = ResolvedFields(charge=None, conservation=None, eps_r=None, material_means=())
        if supplied is not None:
            report(progress, LOAD_FRACTION, "gating the supplied fields")
            check_cancelled(cancel, "the supplied fields")
            # The grids ``_prepare`` already read, gated here rather than read
            # again: the reference table is 77 MB of text, and two reads are two
            # chances to key one field and assemble another.
            fields = gate_fields(resolved, supplied, mesh, measures=measures, cancel=cancel)

        rungs = ladder(resolved, mesh, measures, distance, fields)
        prepared, on_rung = self._instrumented(resolved, rungs, progress=progress, cancel=cancel)
        result = run_ladder(prepared, on_rung=on_rung)
        report(progress, 1.0, f"converged in {result.iterations} Newton iterations")

        payload = self._write(
            result.solution,
            resolved=resolved,
            mesh_content_hash=ingested.content_hash,
            boundaries=prepared[-1].boundaries,
        )
        return SolutionArtefact(
            parameters=resolved.solve_provenance,
            inputs=_input_hashes(mesh_artefact, materials, fields_artefact),
            payload=payload,
            summary={**result.summary(), **_field_summary(fields)},
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

    def _write(
        self,
        solution: ModelSolution,
        *,
        resolved: ResolvedCase,
        mesh_content_hash: str,
        boundaries: CoupledBoundaries,
    ) -> dict[str, Path]:
        """Write the converged state and return the payload map.

        The state is written before the artefact exists because the artefact
        names it: the payload is outside the content hash (section 5.3.2), and
        the store hashes each file as it copies it in.

        What is written is the self-describing coefficient record of
        :mod:`nanopnp.solve.state`, not the backend's own ``state.gfu``: stage 11
        served from a cache hit here has to reassemble the residual to run the
        NUM-25 route at all, and it can only do that against the same mesh,
        model and *distance field* this solve used. That is the whole reason the
        payload carries a descriptor and the artefact schema is ``v2``.
        """
        directory = self._workspace
        if directory is None:
            root = store_root() / WORKSPACE_DIRNAME
            root.mkdir(parents=True, exist_ok=True)
            safe = "".join(character if character.isalnum() else "-" for character in resolved.name)
            directory = Path(tempfile.mkdtemp(prefix=f"{safe}-", dir=root))
        directory.mkdir(parents=True, exist_ok=True)
        target = save(
            solution,
            directory / STATE_FILENAME,
            resolved=resolved,
            mesh_content_hash=mesh_content_hash,
            boundaries=boundaries,
        )
        return {"state": target}

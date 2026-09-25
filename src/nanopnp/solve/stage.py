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

import logging
import tempfile
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING
from zipfile import BadZipFile

from nanopnp.charge.stage import FieldStage, ResolvedFields, gate_fields, read_fields
from nanopnp.core.paths import store_root
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
from nanopnp.io.case import resolve
from nanopnp.materials.stage import MaterialsStage
from nanopnp.mesh.ingest import IngestedMesh, MeshStage, ingest
from nanopnp.physics.measures import AXISYMMETRIC
from nanopnp.physics.models import CoupledBoundaries, CoupledModel
from nanopnp.solve.continuation import Rung, run_ladder
from nanopnp.solve.state import (
    STATE_FILENAME,
    STATE_KEY,
    StateMismatchError,
    WarmStart,
    check_wall_distance,
    cold_start,
    ladder,
    load_initial,
    reads_wall,
    save,
    wall_distance_field,
    warm_start_payload,
)

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.core.typing import Expression, Mesh
    from nanopnp.io.case import ResolvedCase
    from nanopnp.physics.measures import Measures
    from nanopnp.physics.models import ModelSolution
    from nanopnp.solve.gates import WallDistanceMeasurement
    from nanopnp.solve.newton import NewtonStep

logger = logging.getLogger(__name__)

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


def _wall_distance_summary(measured: WallDistanceMeasurement | None) -> dict[str, object]:
    """Return the NUM-34 measurement, or nothing when no correction read ``d``.

    Nothing rather than a null: "this run activated no wall correction" and
    "it did, and the field was fine" are different facts, and a null minimum
    would read as the second.
    """
    return {} if measured is None else {"wall_distance": measured.summary()}


class SolveStage:
    """Stage 10: a case and a mesh to a converged state and its record."""

    name = "solve"

    def __init__(
        self,
        *,
        workspace: Path | None = None,
        warm_start: Artefact | None = None,
        cold_reason: str = "",
        solve_hook: SolveHook | None = None,
    ) -> None:
        """Build the stage.

        Parameters
        ----------
        workspace
            Directory the converged state is written to before the store copies
            it in. Defaults to a fresh directory under the store root, so that a
            solve run without a store still leaves its fields somewhere the
            caller can find them.
        warm_start
            A neighbour's stage-10 artefact to start Newton from (FR-24). When
            one is given and it loads, the target rung is solved **alone** —
            that is stage 9 of NUM-18, the salt sweep, generalised to the other
            axes of the envelope, and re-climbing the nine rungs below a
            converged neighbour would re-derive the answer the neighbour already
            is (the §6.5 NOTE). It changes nothing about
            :meth:`key`: two members differing only in where Newton started must
            key one artefact, or the store would hold two entries for one
            converged state (§5.3.2).
        cold_reason
            Why no warm start was offered, recorded when ``warm_start`` is
            ``None``. A member that could not find its parent and a member that
            has no parent are different facts, and QR-06 asks that a sweep's
            timings say which members paid for what.
        solve_hook
            Where each continuation rung and each accepted Newton step is
            reported, as numbers (:class:`~nanopnp.core.stages.SolveHook`).
            Normally set through :meth:`with_solve_hook` rather than here. It is
            a callback and not an input: it reaches neither
            :attr:`~nanopnp.io.case.ResolvedCase.solve_provenance` nor
            :meth:`key`, so a run watched from the desktop shell keys the same
            artefact as the same run from the command line (§5.3.2).
        """
        self._workspace = Path(workspace) if workspace is not None else None
        self._warm_start = warm_start
        self._cold_reason = cold_reason
        self._solve_hook = solve_hook

    def with_solve_hook(self, hook: SolveHook) -> SolveStage:
        """Return a copy of this stage reporting its rungs and steps through ``hook``.

        The :class:`~nanopnp.core.stages.SolveReporting` capability. A copy
        rather than a mutation because the caller that rebinds is the pipeline
        driver, which has already taken this stage's artefact key: mutating the
        object it keyed would make the hook look like part of the run even
        though the key is unmoved, and the copy makes the ordering explicit.

        Parameters
        ----------
        hook
            The reporter.

        Returns
        -------
        SolveStage
            The same stage, with the same workspace, warm start and cold reason.
        """
        return SolveStage(
            workspace=self._workspace,
            warm_start=self._warm_start,
            cold_reason=self._cold_reason,
            solve_hook=hook,
        )

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
        ingested = ingest(resolved.require_mesh(), resolved)
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
        # NUM-34, once per solve, on the field the corrections actually read and
        # before the first rung assembles anything against it. A field that
        # samples below the threshold is under-resolved at the wall, and the
        # PHY-02 clamp would turn that into a converged, plausible, wrong
        # current rather than into a diagnostic (QR-12).
        wall_distance = check_wall_distance(
            resolved, mesh, distance, coordinates=measures.coordinate_names
        )

        fields = ResolvedFields(charge=None, conservation=None, eps_r=None, material_means=())
        if supplied is not None:
            report(progress, LOAD_FRACTION, "gating the supplied fields")
            check_cancelled(cancel, "the supplied fields")
            # The grids ``_prepare`` already read, gated here rather than read
            # again: the reference table is 77 MB of text, and two reads are two
            # chances to key one field and assemble another.
            fields = gate_fields(resolved, supplied, mesh, measures=measures, cancel=cancel)

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
            # The target rung alone. The ladder's own last rung *is* the target
            # operating point, and every rung below it is a path to a state the
            # neighbour already supplies (NUM-18 NOTE, FR-24).
            rungs = rungs[-1:]
        prepared, on_rung = self._instrumented(resolved, rungs, progress=progress, cancel=cancel)
        result = run_ladder(
            prepared, initial=None if warm is None else warm.solution, on_rung=on_rung
        )
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
        """Load the neighbour's state this run was handed, or return ``None``.

        A refusal is not an error here. FR-24 makes the members of a sweep
        *independent* jobs: one must be runnable alone, in any order, on a
        machine that has seen nothing else, and the warm start is an
        optimisation the store may or may not be able to supply. So a payload
        the space gate refuses is logged with its diagnostic and the full NUM-18
        ladder is climbed instead — which is exactly what the caller would do
        with an absent parent, by the same code path and with the same record.

        The caught set is wider than :class:`StateMismatchError` for the same
        reason: a neighbour's payload that is missing, unreadable or not a
        ``.npz`` at all is refused by NumPy and by ``zipfile`` rather than by the
        descriptor gate, and a member that aborted on one would have turned an
        optimisation into a dependency.
        """
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

        The :class:`~nanopnp.core.stages.SolveHook` rides the same two closures,
        beside the progress reports rather than instead of them, and the captions
        are left byte-identical: a hook is what a caller *acts* on and a caption
        is what it shows, and the two answering the same question differently is
        how they drift. Because the hook rides ``on_rung``, a rung whose model
        takes no Newton callback still reports itself — which is what makes the
        NUM-18 electrostatic stages visible as rungs that emitted no steps,
        rather than as a gap (VER-44).

        The hook is told *per rung* whether the callback was injected, from the
        same test that injects it, because a rung reports no step for two
        unrelated reasons and a reader cannot tell them apart from the silence.
        A rung whose model takes no callback reports none by construction; a
        coupled rung reports none when :func:`~nanopnp.solve.newton.damped_newton`
        found the entry residual already below its target and returned before the
        first step — which is not a missing record but the NUM-16 warm-start case
        itself, and is what most of the ladder does once a neighbour has been
        transferred onto it.
        """
        settings = resolved.newton
        hook = self._solve_hook
        span = 1.0 - LOAD_FRACTION
        total = max(len(rungs), 1)
        iterations = max(settings.max_iterations, 1)
        # One decision, read twice: whether this rung's ``solve`` takes a Newton
        # callback. Testing it separately where the hook is told and where the
        # callback is injected would let the two disagree, and the disagreement
        # would show as a band that promised steps and reported none.
        reporting = tuple(isinstance(rung.model, CoupledModel) for rung in rungs)
        # The rung the Newton callback is reporting within. A closure cell rather
        # than an argument because ``solve`` knows nothing about the ladder.
        current = [0]

        def on_rung(index: int, rung: Rung) -> None:
            current[0] = index
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

        def on_step(step: NewtonStep) -> None:
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
        return {STATE_KEY: target}

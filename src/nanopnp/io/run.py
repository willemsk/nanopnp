"""The pipeline driver: one case file to one run directory (FR-27, QR-08, IF-01).

Section 5.2 numbers twelve stages and section 5.3.2 makes each one a pure
function of its inputs. Nothing walked them. This module is that walk, and it is
deliberately the only one: the CLI, the desktop shell (ADR-004) and the sweep
runner (FR-24) each drive a run, and three walks over the same graph are three
chances for one of them to key a stage differently from the others.

**It lives in ``io/`` and not in ``core/``.** The driver needs
:mod:`nanopnp.io.store`, :mod:`nanopnp.io.manifest` and the lazy
:func:`nanopnp.core.stages.create`; putting it in ``core`` would make the base
layer depend on ``io``, which is the wrong direction in section 5.1's table.

**Every stage goes through the store, and its key is computed before it runs.**
That is what makes :meth:`~nanopnp.io.store.Store.get_or_compute` a cache rather
than a memo of work already done, and it is what lets a reproduction assert that
it *missed* — one served from the store asserts that a dictionary lookup is
deterministic and nothing else (QR-08).

**Nothing here imports NGSolve.** The stages are constructed through
:func:`nanopnp.core.stages.create`, which imports a stage's module only when the
run reaches it, so a walk that stops at stage 9 has still not paid the ~370 ms.
"""

from __future__ import annotations

import logging
import tempfile
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.core.hashing import Canonicalisable, canonical
from nanopnp.core.stages import (
    CancelToken,
    Progress,
    SolveHook,
    SolveReporting,
    Stage,
    StageHook,
    StageOption,
    check_cancelled,
    create,
    describe,
    report,
)
from nanopnp.io.artefact import Artefact, CaseArtefact, StageInputs
from nanopnp.io.case import load_case, refuse_walk, resolve
from nanopnp.io.manifest import Manifest, build
from nanopnp.io.store import Store

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.io.case import CaseDocument, ResolvedCase
    from nanopnp.io.defaults import ContributedDeviation

__all__ = [
    "PAYLOAD_FREE",
    "PIPELINE",
    "RUN_RECORD_FILENAME",
    "RUN_SCHEMA",
    "WORKSPACE_STAGES",
    "MissingUpstreamError",
    "RunResult",
    "StageRecord",
    "UnknownStageError",
    "run_case",
    "run_document",
]

logger = logging.getLogger(__name__)

RUN_SCHEMA = "nanopnp/run/v1"
"""Schema of the run record written beside the manifest."""

RUN_RECORD_FILENAME = "run.json"
"""Name the run record is written under inside a run directory.

Beside ``manifest.json`` and ``case.yaml`` rather than inside either. The
manifest is the FR-25 provenance record and says how the run was *configured*;
this says which artefacts it produced and where they are. Separating them is
what lets a reader with a run directory and no store tell a run that was served
from a cache from one that solved.
"""

PIPELINE: tuple[str, ...] = (
    "case",
    "structure",
    "density",
    "symmetry",
    "contour",
    "mesh",
    "charge",
    "materials",
    "solve",
    "qoi",
    "report",
)
"""The stages a run walks, in dependency order.

Not in section 5.2's *numbering* order: stage 9 resolves the case and stages 6,
7 and 8 all consume it, so the numbers say what each stage is and this tuple
says when it can run. A Tier-1 test asserts every name here is registered and
that each stage's declared inputs are produced by the ones before it.
"""

PAYLOAD_FREE: frozenset[str] = frozenset({"case", "materials"})
"""Stages whose artefact is a hash over the case and carries no file.

They are exactly the two stages with no ``key`` method, and for the same reason:
running one *is* computing its key, because resolving a validated case document
writes nothing and evaluates no fit. That is what lets ``only`` resolve them
rather than demand them from the store — there is no payload for a hand
substitution (FR-27) to substitute, so recomputing one cannot read past an
edited file.
"""

STRUCTURE_STAGES: tuple[str, ...] = ("structure", "density", "symmetry", "contour")
"""The stages a case runs only when it carries ``structure:`` (stages 1 to 4)."""

WORKSPACE_DIRNAME = "tmp"
"""Directory under the store root that a run's scratch workspaces are made in.

The same name the file-writing stages use for their own fallback, because it is
the same directory — the difference is only *which* store root it hangs from.
"""


def _scratch(store: Store) -> Path:
    """Return a fresh workspace directory under ``store`` for one run.

    Each stage falls back to ``store_root()`` when it is constructed without a
    workspace, and ``store_root()`` is the process default — ``$NANOPNP_STORE``
    or ``./nanopnp-store`` — rather than the store this run was handed. A sweep
    worker or a test that named its own store would then have the run's scratch
    meshes and field exports appear somewhere it never asked about, while the
    artefacts referencing them lived in the store it did. Naming the workspace
    here keeps a run's files inside its own store.

    Fresh per run rather than a fixed ``tmp/mesh``: two runs into one store hold
    different meshes, and a deterministic name would have the second overwrite
    a file the first's artefact still points at (section 5.3.2).

    Called from :meth:`_Walk.construct` on the first stage that writes a file
    rather than before the walk, so that a run served entirely from the store
    leaves no empty directory behind — under FR-24 that is one per member of a
    re-collected sweep, in the directory the cache exists to avoid touching.
    """
    root = store.root / WORKSPACE_DIRNAME
    root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="run-", dir=root))


WORKSPACE_STAGES: frozenset[str] = frozenset(
    {"structure", "density", "symmetry", "contour", "mesh", "charge", "solve", "report"}
)
"""Stages whose constructor takes the directory they write into.

Enumerated rather than discovered by catching :class:`TypeError` from
:func:`~nanopnp.core.stages.create`: a genuine ``TypeError`` raised *inside* a
stage's constructor would be indistinguishable from an unwanted keyword, and the
driver would silently rebuild the stage with no workspace and write into the
store root. A Tier-1 test asserts this set against the constructors themselves.
"""

_WEIGHTS: Mapping[str, float] = {
    # The solve is the run. The rest is reading files, hashing them and
    # integrating over a converged state, and a progress bar giving them equal
    # weight would sit at 5/7 for the whole of the ladder.
    "case": 0.01,
    "structure": 0.05,
    # Stage 2 deposits every frame's atoms, which is the longest thing a walk
    # through stage 3 does: seconds for a crystal structure, minutes for an ensemble.
    "density": 0.2,
    "symmetry": 0.05,
    # The probe profile is frames x atoms x planes distances: seconds on an ensemble.
    "contour": 0.03,
    "mesh": 0.05,
    "charge": 0.06,
    "materials": 0.01,
    "solve": 0.75,
    "qoi": 0.08,
    "report": 0.04,
}
"""Share of the overall progress fraction each stage is given."""


class MissingUpstreamError(RuntimeError):
    """An upstream artefact is not in the store and ``only`` forbade computing it."""


class UnknownStageError(KeyError):
    """``upto`` named a stage this run does not walk.

    A :class:`KeyError` still, so that a caller written against the mapping-like
    reading of ``upto`` keeps working, but a *named* one: IF-02 classifies it as
    ``3``, the case, because nothing numerical has gone wrong and the retry a
    job array would make on ``1`` fails identically (section 3.1 NOTE, QR-06).
    """

    def __str__(self) -> str:
        """Return the message as written, without :class:`KeyError`'s quoting.

        ``KeyError`` reprs its argument, which is right for a missing key and
        wrong for a sentence: the CLI prints ``str(error)`` as the QR-12
        diagnostic, and a diagnostic wrapped in quotes reads as a key nobody
        looked up.
        """
        return str(self.args[0]) if self.args else ""


@dataclass(frozen=True)
class StageRecord:
    """What one stage of a run produced, and whether it had to do the work.

    Parameters
    ----------
    name, number, schema
        The stage as the registry describes it (FR-27).
    hash
        Content hash of the artefact it produced: the artefact's identity, and
        its location in the store.
    cached
        Whether the store already held it. A run whose every stage is cached did
        no physics, and QR-08's reproduction check is precisely the assertion
        that this is ``False`` for the solve.
    seconds
        Wall time, including the store lookup that decided not to run it.
    """

    name: str
    number: int
    schema: str
    hash: str
    cached: bool
    seconds: float

    def summary(self) -> dict[str, Canonicalisable]:
        """Return this record as plain data, for the run record and the CLI."""
        return {
            "stage": self.name,
            "number": self.number,
            "schema": self.schema,
            "hash": self.hash,
            "cached": self.cached,
            "seconds": self.seconds,
        }


@dataclass(frozen=True)
class RunResult:
    """One completed run: its artefacts, its manifest and where they were written.

    Parameters
    ----------
    directory
        The run directory holding ``manifest.json``, ``case.yaml`` and
        :data:`RUN_RECORD_FILENAME`.
    manifest
        The FR-25 provenance record.
    artefacts
        Every stage's artefact, by stage name, as the store holds it.
    stages
        The per-stage record, in the order the stages ran.
    store
        The store the run went through, carrying its hit and miss counts.
    """

    directory: Path
    manifest: Manifest
    artefacts: Mapping[str, Artefact]
    stages: tuple[StageRecord, ...] = ()
    store: Store | None = None

    @property
    def quantities(self) -> Mapping[str, Canonicalisable]:
        """The stage-11 summary: every scalar this run extracted.

        Empty when the run stopped before stage 11 — a run that produced no
        number, which is not a run whose numbers were all zero.
        """
        qoi = self.artefacts.get("qoi")
        return dict(qoi.summary) if qoi is not None else {}

    @property
    def files(self) -> tuple[Path, ...]:
        """Every file stage 12 wrote, in the store."""
        written = self.artefacts.get("report")
        if written is None:
            return ()
        return tuple(path for _, path in sorted(written.payload.items()))

    def record(self) -> dict[str, Canonicalisable]:
        """Return the run record: what this run produced, and where it is."""
        return {
            "schema": RUN_SCHEMA,
            "case": self.manifest.case_hash,
            "manifest": self.manifest.hash,
            "directory": str(self.directory),
            "store": str(self.store.root) if self.store is not None else None,
            "stages": [record.summary() for record in self.stages],
            "artefacts": {
                name: {"schema": artefact.schema, "hash": artefact.hash}
                for name, artefact in sorted(self.artefacts.items())
            },
            "quantities": dict(self.quantities),
            "files": [str(path) for path in self.files],
        }

    def write(self) -> Path:
        """Write the manifest, the case and the run record into the run directory.

        Returns
        -------
        Path
            The path of the run record. The manifest and the case are written
            beside it by :meth:`nanopnp.io.manifest.Manifest.write`, from the
            same string the manifest embeds, so the three files cannot disagree.
        """
        self.manifest.write(self.directory)
        path = self.directory / RUN_RECORD_FILENAME
        path.write_bytes(canonical(self.record()) + b"\n")
        return path


@dataclass
class _Walk:
    """Mutable state of one walk over the pipeline.

    A dataclass rather than a pile of locals because the same four things — the
    document, the store, the artefacts produced so far and the deviations the
    stages contributed — are handed to every step, and threading them through as
    arguments would make the loop its own argument list.
    """

    document: CaseDocument
    resolved: ResolvedCase
    store: Store
    options: Mapping[str, Mapping[str, Canonicalisable]]
    arguments: Mapping[str, Mapping[str, StageOption]]
    workspace: Path | None
    only: bool
    artefacts: dict[str, Artefact] = field(default_factory=dict)
    records: list[StageRecord] = field(default_factory=list)
    contributed: list[ContributedDeviation] = field(default_factory=list)
    scratch: Path | None = None
    """The workspace :func:`_scratch` made, once a stage has needed one."""

    def inputs(self, name: str) -> StageInputs:
        """Return the inputs one stage is handed.

        Every artefact produced so far is offered, not only the ones the stage
        declares: a stage takes what it needs from the mapping by name (FR-27),
        and filtering here would mean this module knew each stage's signature.
        """
        return StageInputs(
            case=self.document,
            upstream=dict(self.artefacts),
            options=dict(self.options.get(name, {})),
        )

    def construct(self, name: str) -> Stage:
        """Return the stage object, giving the ones that write files a directory.

        The workspace is the one the caller named, or one made under this run's
        store the first time a file-writing stage asks for it — never the
        process-default :func:`~nanopnp.core.paths.store_root` the stages
        themselves fall back to (section 5.3.2, the workspace-locality NOTE).

        ``arguments`` carries anything else a caller needs to construct a stage
        with — today only the FR-24 warm start, which is an *artefact* and so
        cannot ride on :attr:`~nanopnp.io.artefact.StageInputs.options`, whose
        values are canonicalisable by contract because they reach a digest. A
        constructor argument reaches none, which is exactly right for a warm
        start: it changes where Newton starts and not what it converges to, and
        §5.3.2 requires it be recorded in provenance and kept out of the key.
        """
        extra = dict(self.arguments.get(name, {}))
        if name not in WORKSPACE_STAGES:
            return create(name, **extra)
        root = self.workspace
        if root is None:
            if self.scratch is None:
                self.scratch = _scratch(self.store)
            root = self.scratch
        directory = root / name
        directory.mkdir(parents=True, exist_ok=True)
        return create(name, workspace=directory, **extra)


def _selected(resolved: ResolvedCase, upto: str | None) -> tuple[str, ...]:
    """Return the stages this case runs, truncated after ``upto``.

    ``charge`` is dropped when the case supplies neither ``inputs.charge`` nor
    ``inputs.eps_r``: stage 7 refuses such a case as describing no work, and a
    run with no field to gate has not skipped a gate. ``structure``, ``density``
    ``symmetry`` and ``contour`` are dropped when the case carries no ``structure:`` section,
    for the same reason.

    Raises
    ------
    UnknownStageError
        If ``upto`` is not a stage this run walks; the message lists the ones it
        does, and says separately when the stage is registered but this case
        gives it nothing to do.
    """
    supplied = resolved.charge is not None or resolved.eps_r is not None
    dropped = set() if supplied else {"charge"}
    if resolved.structure is None:
        dropped.update(STRUCTURE_STAGES)
    stages = tuple(name for name in PIPELINE if name not in dropped)
    if upto is None:
        return stages
    if upto in stages:
        return stages[: stages.index(upto) + 1]
    if upto in STRUCTURE_STAGES:
        raise UnknownStageError(
            f"stage {upto!r} is registered but case {resolved.name!r} carries no structure: "
            "section, so there is nothing for it to read"
        )
    if upto in PIPELINE:
        raise UnknownStageError(
            f"stage {upto!r} is registered but case {resolved.name!r} supplies neither "
            "inputs.charge nor inputs.eps_r, so there is nothing for it to read"
        )
    raise UnknownStageError(f"no stage {upto!r} in the pipeline; it walks {', '.join(stages)}")


def _probe(stage: Stage, inputs: StageInputs) -> Artefact:
    """Return the artefact a stage will produce, without doing its work.

    A stage with a ``key`` method answers directly. The two of
    :data:`PAYLOAD_FREE` have none, because for them the key *is* the artefact:
    resolving a validated case writes no file and evaluates no fit, so there is
    nothing cheaper to compute than the answer itself.
    """
    key = getattr(stage, "key", None)
    if key is None:
        return stage.run(inputs)
    probed: Artefact = key(inputs)
    return probed


def _contributed(stage: Stage, inputs: StageInputs) -> tuple[ContributedDeviation, ...]:
    """Return the departures from the validated model a stage contributes (FR-25).

    Optional on the stage protocol, because most stages find none: a stage that
    reads no external file and takes no option has nothing to contribute that the
    case-file diff of :mod:`nanopnp.io.defaults` does not already see (FR-25,
    section 5.3.3).

    Called by :func:`run_document` **after** the stage's artefact has been
    recorded, with ``inputs`` rebuilt so that artefact appears under the stage's
    own name. That ordering is the protocol, and it is what lets
    :meth:`nanopnp.mesh.ingest.MeshStage.deviations` read the ``materials`` its
    artefact already carries instead of ingesting and quality-gating the mesh
    again, and :meth:`nanopnp.charge.stage.FieldStage.deviations` read the
    ``fields`` parameter instead of re-reading a field table of tens of
    megabytes. A stage whose deviations depend only on its options, as
    :meth:`nanopnp.post.stage.QoIStage.deviations` does, is unaffected by it.
    """
    contribute = getattr(stage, "deviations", None)
    if contribute is None:
        return ()
    found: tuple[ContributedDeviation, ...] = contribute(inputs)
    return found


def _slice(progress: Progress | None, low: float, high: float, name: str) -> Progress | None:
    """Return a callback mapping one stage's [0, 1] into ``[low, high]`` of the run.

    Monotone by construction, so the contract
    :class:`nanopnp.core.stages.Progress` states holds for the walk as well as
    for each stage.
    """
    if progress is None:
        return None

    def scaled(fraction: float, message: str) -> None:
        progress(low + (high - low) * min(1.0, max(0.0, fraction)), f"{name}: {message}")

    return scaled


def _resolve_stage(
    walk: _Walk,
    stage: Stage,
    name: str,
    inputs: StageInputs,
    key: Artefact,
    *,
    substitute: bool,
    progress: Progress | None,
    cancel: CancelToken | None,
    on_solve: SolveHook | None = None,
) -> Artefact:
    """Return one stage's artefact, from the store or by running it.

    Parameters
    ----------
    substitute
        Whether this stage is an *upstream* one under ``only``: it must then come
        from the store, and a miss aborts naming it rather than computing it.
        That is what makes a hand-substituted artefact testable (FR-27) — it
        proves the stage read the substituted file rather than recomputing past
        it.
    on_solve
        Where a :class:`~nanopnp.core.stages.SolveReporting` stage reports its
        continuation rungs and Newton steps. Only such a stage is rebound, and
        only *here*: ``key`` was taken from the unbound stage by the caller, so
        a watched run and an unwatched one key one artefact and land on one
        store entry (section 5.3.2). A stage that does not satisfy the protocol
        is left alone rather than given a keyword it would have to ignore.
    """
    if on_solve is not None and isinstance(stage, SolveReporting):
        stage = stage.with_solve_hook(on_solve)
    if name in PAYLOAD_FREE:
        # ``_probe`` already ran it. Running it again would be the whole stage
        # twice for an artefact that carries no file, so the key is the answer;
        # it still goes into the store, so the run record points somewhere.
        if walk.store.contains(key):
            walk.store.hits += 1
            return key
        walk.store.misses += 1
        return walk.store.put(key)
    if substitute:
        found = walk.store.get(key.schema, key.hash)
        if found is None:
            raise MissingUpstreamError(
                f"stage {name!r} produces {key.schema} {key.short_hash}, which is not in the "
                f"store at {walk.store.root}, and 'only' refuses to compute it. Run the "
                f"pipeline through {name!r} first, or drop 'only'"
            )
        walk.store.hits += 1
        return found
    return walk.store.get_or_compute(
        key, lambda: stage.run(inputs, progress=progress, cancel=cancel)
    )


def _input_files(resolved: ResolvedCase, case_path: Path | None) -> dict[str, Path]:
    """Return the run's input files by role, for the manifest's Inputs group.

    Only files that exist as paths: a mesh or a field named by store hash rather
    than by path is already recorded as an upstream artefact, and hashing it a
    second time under a made-up path would put one input in the manifest twice.
    """
    files: dict[str, Path] = {}
    if case_path is not None:
        files["case"] = case_path
    for role, supplied in (
        ("mesh", resolved.mesh),
        ("charge", resolved.charge),
        ("eps_r", resolved.eps_r),
    ):
        if supplied is not None and supplied.path is not None:
            files[role] = supplied.path
    if resolved.structure is not None:
        files["structure"] = resolved.structure.spec.source.path
        trajectory = resolved.structure.spec.ensemble.trajectory
        if trajectory is not None:
            files["trajectory"] = trajectory
    return files


def _mapping(
    summary: Mapping[str, Canonicalisable] | None, key: str
) -> Mapping[str, Canonicalisable] | None:
    """Return a mapping-valued entry of a stage summary, or ``None`` if it is absent.

    Checked for shape rather than assumed: the summary reaches here through the
    artefact, which FR-27 permits to have been edited by hand, and a manifest
    group built from a string would fail far from the edit that caused it.
    """
    if summary is None:
        return None
    found = summary.get(key)
    return found if isinstance(found, Mapping) else None


STRUCTURE_RECORD_KEYS: tuple[str, ...] = (
    "point_group",
    "chains_cyclic_order",
    "axis",
    "gates",
    "frames",
    "superposition",
    "drift_deg",
    "payload_digest",
)
"""The stage-1 summary entries the manifest's Geometry group records (FR-25, WP18 D14)."""

DENSITY_RECORD_KEYS: tuple[str, ...] = (
    "grid",
    "radius_set",
    "sharpness",
    "frames",
    "atoms",
    "hydrogens",
    "payload_digest",
)
"""The stage-2 summary entries the Geometry group records as ``density`` (WP19 D13)."""

REDUCTION_RECORD_KEYS: tuple[str, ...] = (
    "n",
    "bins",
    "unresolved_radius_nm",
    "maximum",
    "payload_digest",
)
"""The stage-3 summary entries the Geometry group records as ``reduction`` (WP19 D13)."""

CONTOUR_RECORD_KEYS: tuple[str, ...] = (
    "isolevel",
    "smoothing",
    "simplify_tol_nm",
    "h_c_nm",
    "vertex_count",
    "min_vertex_spacing_nm",
    "min_feature_size_nm",
    "holes_filled",
    "band",
    "constriction",
)
"""The stage-4 summary entries the Geometry group records as ``contour`` (WP20 D15)."""


def _record(artefact: Artefact | None, keys: tuple[str, ...]) -> dict[str, Canonicalisable] | None:
    """Return a Geometry-group record: the named entries of one stage's summary.

    Taken from the artefact and never recomputed, so the manifest cannot report an
    axis, a gate or a variance the stage did not measure.
    """
    if artefact is None:
        return None
    return {key: artefact.summary[key] for key in keys if key in artefact.summary}


def _manifest(walk: _Walk, *, case_text: str, case_path: Path | None) -> Manifest:
    """Assemble the FR-25 manifest from the artefacts the walk produced.

    Every group comes from the artefact that produced it rather than from a
    second computation: the geometry group is the stage-6 summary, the charge
    group the stage-7 summary, the solver group the stage-10 summary, the PHY-13
    clamp count the stage-11 summary. A group whose stage did not run is recorded
    as :func:`~nanopnp.io.manifest.not_run`, which is a different fact from a
    group that ran and found nothing.
    """
    case = walk.artefacts.get("case")
    structure = walk.artefacts.get("structure")
    density = walk.artefacts.get("density")
    symmetry = walk.artefacts.get("symmetry")
    contour = walk.artefacts.get("contour")
    mesh = walk.artefacts.get("mesh")
    charge = walk.artefacts.get("charge")
    solve = walk.artefacts.get("solve")
    qoi = walk.artefacts.get("qoi")

    solver = dict(solve.summary) if solve is not None else None
    stabilisation = str(solver["stabilisation"]) if solver and "stabilisation" in solver else None
    clamps = qoi.summary.get("clamp_activations") if qoi is not None else None
    # Both are written by stage 10 into its summary and read back out here
    # rather than recomputed: the manifest's record of what the solve did must
    # come from the solve, or the two can disagree. ``wall_distance`` is absent
    # when no wall correction read the field (NUM-34); ``warm_start`` is absent
    # only when no solve ran at all, because a solve that ran always records one
    # -- ``cold`` with its reason when it was offered no neighbour (FR-24).
    wall_distance = _mapping(solver, "wall_distance")
    warm_start = _mapping(solver, "warm_start")
    # Read from the stage that produced each: the mode and its constants from the
    # solve, the contribution to the current from the extraction. A manifest that
    # recomputed either could report a mode the run did not use (FR-25).
    stabilisation_parameters = _mapping(solver, "stabilisation_parameters")
    stabilisation_provenance = _mapping(solver, "stabilisation_provenance")
    peclet = _mapping(solver, "peclet")
    stabilisation_currents = _mapping(
        dict(qoi.summary) if qoi is not None else None, "stabilisation_currents_A"
    )

    return build(
        walk.document,
        case_text=case_text,
        case_hash=case.hash if case is not None else CaseArtefact(walk.document).hash,
        input_files=_input_files(walk.resolved, case_path),
        upstream=dict(walk.artefacts),
        mesh=dict(mesh.summary) if mesh is not None else None,
        structure=_record(structure, STRUCTURE_RECORD_KEYS),
        density=_record(density, DENSITY_RECORD_KEYS),
        reduction=_record(symmetry, REDUCTION_RECORD_KEYS),
        contour=_record(contour, CONTOUR_RECORD_KEYS),
        charge=dict(charge.summary) if charge is not None else None,
        electrolyte=walk.resolved.electrolyte,
        clamp_activations=clamps if isinstance(clamps, int) else None,
        ladder=solver,
        stabilisation=stabilisation,
        stabilisation_parameters=stabilisation_parameters,
        stabilisation_provenance=stabilisation_provenance,
        stabilisation_currents_A=stabilisation_currents,
        peclet=peclet,
        warm_start=warm_start,
        wall_distance=wall_distance,
        contributed_deviations=tuple(walk.contributed),
    )


def run_document(
    document: CaseDocument,
    *,
    case_text: str,
    case_path: Path | None = None,
    store: Store | None = None,
    upto: str | None = None,
    only: bool = False,
    options: Mapping[str, Mapping[str, Canonicalisable]] | None = None,
    arguments: Mapping[str, Mapping[str, StageOption]] | None = None,
    workspace: Path | None = None,
    write: bool = True,
    progress: Progress | None = None,
    cancel: CancelToken | None = None,
    on_stage: StageHook | None = None,
    on_solve: SolveHook | None = None,
) -> RunResult:
    """Walk the pipeline for one validated case and return what it produced.

    Parameters
    ----------
    document
        The validated case.
    case_text
        The case file verbatim, embedded in the manifest beside its hash so the
        two cannot disagree (section 5.3.3).
    case_path
        Where it was read from, recorded as an input file. ``None`` for a case
        assembled in memory, recorded then as having no source file rather than
        as having one that does not exist.
    store
        The artefact store; a default-rooted :class:`~nanopnp.io.store.Store` if
        omitted. Its hit and miss counts are carried onto the result, which is
        what lets QR-08's check assert that a reproduction re-entered Newton.
    upto
        Stop after this stage. ``None`` walks the whole pipeline.
    only
        Refuse to compute any upstream stage that writes a payload, taking it
        from the store instead and aborting naming it if it is not there.
    options
        Per-stage options, by stage name, passed through on
        :attr:`~nanopnp.io.artefact.StageInputs.options`.
    arguments
        Per-stage constructor arguments, by stage name; see
        :meth:`_Walk.construct`. Nothing here enters an artefact key.
    workspace
        Directory the file-writing stages use, one subdirectory each. When this
        is ``None`` the run takes a fresh one under ``store``, so that a caller
        who named a store gets every file the run wrote inside it — the stages'
        own fallback is to :func:`~nanopnp.core.paths.store_root`, which is the
        *process* default and not the store the run was handed.
    write
        Whether to write the run directory. ``False`` returns the result with the
        directory named and nothing in it, for a caller assembling several runs.
    progress
        Called with a fraction in [0, 1] and a message, monotone, ending at 1.
        Each stage's own fraction is mapped into its share of the total.
    cancel
        Checked before every stage and threaded into each of them.
    on_stage
        Called before each stage with its name and its position in the walk. The
        same transition ``progress`` reports as text, given as data, so a caller
        that has to act on it does not parse a caption (:class:`~nanopnp.core.stages.StageHook`).
    on_solve
        Called with each continuation rung and each accepted Newton step of the
        solve, as numbers (:class:`~nanopnp.core.stages.SolveHook`). Delivered by
        capability and not by keyword: only a stage satisfying
        :class:`~nanopnp.core.stages.SolveReporting` is rebound, and it is
        rebound after its artefact key has been taken, so watching a run cannot
        move a hash (section 5.3.2).

    Returns
    -------
    RunResult
        Every artefact, the manifest, and the run directory.

    Raises
    ------
    MissingUpstreamError
        If ``only`` is set and an upstream artefact is not in the store.
    nanopnp.core.stages.Cancelled
        If ``cancel`` turns true. No run directory is written.
    """
    target = store if store is not None else Store()
    walk = _Walk(
        document=document,
        resolved=resolve(document),
        store=target,
        options=dict(options or {}),
        arguments=dict(arguments or {}),
        workspace=Path(workspace) if workspace is not None else None,
        only=only,
    )
    refuse_walk(walk.resolved, upto)
    stages = _selected(walk.resolved, upto)
    weights = [_WEIGHTS[name] for name in stages]
    total = sum(weights)
    offsets = [sum(weights[:index]) / total for index in range(len(stages) + 1)]

    for index, name in enumerate(stages):
        check_cancelled(cancel, f"stage {name!r}")
        low, high = offsets[index], offsets[index + 1]
        if on_stage is not None:
            on_stage(name, index, len(stages))
        report(progress, low, f"stage {name}")
        started = time.perf_counter()
        hits = walk.store.hits
        stage = walk.construct(name)
        inputs = walk.inputs(name)
        artefact = _resolve_stage(
            walk,
            stage,
            name,
            inputs,
            _probe(stage, inputs),
            substitute=walk.only and index < len(stages) - 1,
            progress=_slice(progress, low, high, name),
            cancel=cancel,
            on_solve=on_solve,
        )
        walk.artefacts[name] = artefact
        # After the artefact is recorded, and on inputs rebuilt so that the
        # stage's own artefact is present under its own name: a stage that
        # already wrote what it found into its parameters answers from there
        # rather than reading and gating its input a second time.
        walk.contributed.extend(_contributed(stage, walk.inputs(name)))
        walk.records.append(
            StageRecord(
                name=name,
                number=describe(name).number,
                schema=artefact.schema,
                hash=artefact.hash,
                cached=walk.store.hits > hits,
                seconds=time.perf_counter() - started,
            )
        )
        logger.info(
            "stage %s %s %s in %.3f s",
            name,
            artefact.short_hash,
            "from the store" if walk.records[-1].cached else "computed",
            walk.records[-1].seconds,
        )
    report(progress, 1.0, f"{len(stages)} stages complete")

    manifest = _manifest(walk, case_text=case_text, case_path=case_path)
    result = RunResult(
        directory=walk.store.run_directory(document.name, manifest.case_hash),
        manifest=manifest,
        artefacts=dict(walk.artefacts),
        stages=tuple(walk.records),
        store=walk.store,
    )
    if write:
        result.write()
        logger.info("run %r written to %s", document.name, result.directory)
    return result


def run_case(
    path: str | Path,
    *,
    store: Store | None = None,
    upto: str | None = None,
    only: bool = False,
    options: Mapping[str, Mapping[str, Canonicalisable]] | None = None,
    arguments: Mapping[str, Mapping[str, StageOption]] | None = None,
    workspace: Path | None = None,
    write: bool = True,
    progress: Progress | None = None,
    cancel: CancelToken | None = None,
    on_stage: StageHook | None = None,
    on_solve: SolveHook | None = None,
) -> RunResult:
    """Load a case file and run it.

    The entry point the CLI and the reproduction check both use, so that "read
    the file, keep its text, walk the pipeline" happens once rather than in each
    caller — a second copy is a second chance for the manifest's embedded case to
    stop being the bytes that were read.

    Parameters
    ----------
    path
        The case file.
    store, upto, only, options, arguments, workspace, write, progress, cancel, on_stage, on_solve
        As :func:`run_document` documents them.
    """
    source = Path(path)
    return run_document(
        load_case(source),
        case_text=source.read_text(encoding="utf-8"),
        case_path=source,
        store=store,
        upto=upto,
        only=only,
        options=options,
        arguments=arguments,
        workspace=workspace,
        write=write,
        progress=progress,
        cancel=cancel,
        on_stage=on_stage,
        on_solve=on_solve,
    )

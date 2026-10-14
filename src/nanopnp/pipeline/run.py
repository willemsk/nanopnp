"""The pipeline driver: one case file to one run directory (FR-27, QR-08, IF-01)."""

from __future__ import annotations

import logging
import shutil
import tempfile
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.core.hashing import Canonicalisable, canonical
from nanopnp.core.stages import (
    ArtefactHook,
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
    walk_order,
)
from nanopnp.io.artefact import Artefact, CaseArtefact, StageInputs
from nanopnp.io.manifest import Manifest, build
from nanopnp.io.store import Store, atomic_write_bytes
from nanopnp.mesh.sizing import case_debye_record
from nanopnp.pipeline.case import loads_case, resolve

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.io.case import CaseDocument
    from nanopnp.io.defaults import ContributedDeviation
    from nanopnp.io.resolved import ResolvedCase

__all__ = [
    "RUN_RECORD_FILENAME",
    "RUN_SCHEMA",
    "MissingUpstreamError",
    "RunResult",
    "StageRecord",
    "UnknownStageError",
    "input_files",
    "offered",
    "run_case",
    "run_document",
    "selected_stages",
    "stored_upstream",
]

logger = logging.getLogger(__name__)

RUN_SCHEMA = "nanopnp/run/v0.5"

RUN_RECORD_FILENAME = "run.json"

WORKSPACE_DIRNAME = "tmp"


def _scratch(store: Store) -> Path:
    root = store.root / WORKSPACE_DIRNAME
    root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix="run-", dir=root))


class MissingUpstreamError(RuntimeError):
    """An upstream artefact is not in the store and only forbade computing it."""


class UnknownStageError(KeyError):
    """The upto argument named a stage this run does not walk."""

    def __str__(self) -> str:
        return str(self.args[0]) if self.args else ""


@dataclass(frozen=True)
class StageRecord:
    """What one stage of a run produced, and whether it had to do the work.

    Parameters
    ----------
    cached
        Whether the store already held the artefact; a run with every stage cached did no physics.
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
    """One completed run: its artefacts, its manifest and where they were written."""

    directory: Path
    manifest: Manifest
    artefacts: Mapping[str, Artefact]
    stages: tuple[StageRecord, ...] = ()
    store: Store | None = None

    @property
    def quantities(self) -> Mapping[str, Canonicalisable]:
        """The stage-11 summary: every scalar this run extracted; empty before stage 11."""
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
        """Write the manifest, the case and the run record; return the run record's path."""
        self.manifest.write(self.directory)
        path = self.directory / RUN_RECORD_FILENAME
        atomic_write_bytes(path, canonical(self.record()) + b"\n")
        return path


@dataclass
class _Walk:
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

    def inputs(self, name: str, *, own: bool = False) -> StageInputs:
        return StageInputs(
            resolved=self.resolved,
            upstream=offered(name, self.artefacts, own=own),
            options=dict(self.options.get(name, {})),
        )

    def construct(self, name: str) -> Stage:
        extra = dict(self.arguments.get(name, {}))
        description = describe(name)
        if description.takes_store:
            extra["store"] = self.store
        if not description.takes_workspace:
            return create(name, **extra)
        root = self.workspace
        if root is None:
            if self.scratch is None:
                self.scratch = _scratch(self.store)
            root = self.scratch
        directory = root / name
        directory.mkdir(parents=True, exist_ok=True)
        return create(name, workspace=directory, **extra)


def offered(
    name: str, artefacts: Mapping[str, Artefact], *, own: bool = False
) -> dict[str, Artefact]:
    """Return the artefacts a stage is handed: those its description declares."""
    declared = set(describe(name).inputs) | ({name} if own else set())
    return {key: artefact for key, artefact in artefacts.items() if key in declared}


def selected_stages(resolved: ResolvedCase, upto: str | None) -> tuple[str, ...]:
    """Return the stages this case runs: every one, or the inputs of upto and upto.

    Parameters
    ----------
    upto
        The stage to walk to, or None for every stage.
    """
    supplied = resolved.charge is not None or resolved.eps_r is not None or resolved.derives_eps_r
    deposits = resolved.deposits_charge
    dropped = set() if supplied or deposits else {"charge"}
    if not deposits and (upto != "protonation" or not resolved.protonates):
        # Protonation feeds nothing unless a deposition reads it, and costs about a
        # minute per frame, so it runs only as a walk's named target.
        dropped.add("protonation")
    order = walk_order()
    sections = type(resolved.document).model_fields
    absent: dict[str, str] = {}
    for name in order:
        section = describe(name).needs_section
        if section is None:
            continue
        if section not in sections:
            # ``register`` cannot check this: ``core`` does not import the case
            # schema. Named here rather than left to ``getattr``, because every
            # walk reads every registered stage's section, whatever its target.
            raise ValueError(
                f"stage {name!r} declares needs_section {section!r}, which is not a top-level "
                f"case section; the sections are {', '.join(sorted(sections))}"
            )
        if getattr(resolved.document, section) is None:
            absent[name] = section
    dropped.update(absent)
    if not resolved.generates_mesh:
        dropped.add("region")
    # A stage whose case drops one of its required inputs has nothing to read.
    # One pass suffices: registration order is a dependency order, so an input
    # is decided before the stage reading it.
    unfed: dict[str, str] = {}
    for name in order:
        if name in dropped:
            continue
        description = describe(name)
        for needed in description.inputs:
            if needed not in description.optional_inputs and needed in dropped:
                unfed[name] = needed
                dropped.add(name)
                break
    stages = tuple(name for name in order if name not in dropped)
    if upto is None:
        return stages
    if upto in stages:
        closure = {upto}
        for name in reversed(stages[: stages.index(upto) + 1]):
            if name in closure:
                closure.update(describe(name).inputs)
        return tuple(name for name in stages if name in closure)
    if upto in absent:
        raise UnknownStageError(
            f"stage {upto!r} is registered but case {resolved.name!r} carries no "
            f"{absent[upto]}: section, so there is nothing for it to read"
        )
    if upto in unfed:
        raise UnknownStageError(
            f"stage {upto!r} is registered but case {resolved.name!r} does not walk "
            f"{unfed[upto]!r}, an input it requires, so there is nothing for it to read"
        )
    if upto == "protonation":
        raise UnknownStageError(
            f"stage 'protonation' is registered but case {resolved.name!r} "
            + (
                "supplies inputs.charge, which replaces what stage 7 makes of the protonation"
                if resolved.charge is not None
                else "carries no structure: section and supplies no inputs.pqr, so there is "
                "nothing for it to protonate"
            )
        )
    if upto == "region":
        raise UnknownStageError(
            f"stage 'region' is registered but case {resolved.name!r} supplies inputs.mesh, so "
            "there is no region to assemble"
        )
    if upto in order:
        raise UnknownStageError(
            f"stage {upto!r} is registered but case {resolved.name!r} supplies neither "
            "inputs.charge nor inputs.eps_r and deposits no charge, so there is nothing for it "
            "to read"
        )
    raise UnknownStageError(f"no stage {upto!r} in the pipeline; it walks {', '.join(stages)}")


def _contributed(stage: Stage, inputs: StageInputs) -> tuple[ContributedDeviation, ...]:
    contribute = getattr(stage, "deviations", None)
    if contribute is None:
        return ()
    found: tuple[ContributedDeviation, ...] = contribute(inputs)
    return found


def _slice(progress: Progress | None, low: float, high: float, name: str) -> Progress | None:
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
    if on_solve is not None and isinstance(stage, SolveReporting):
        stage = stage.with_solve_hook(on_solve)
    if describe(name).key_is_artefact:
        # The key is the whole artefact. Running the stage as well would be its
        # whole work twice for an artefact that carries no file, so the key is
        # the answer; it still goes into the store, so the run record points
        # somewhere.
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


def input_files(resolved: ResolvedCase, case_path: Path | None) -> dict[str, Path]:
    """Return the run's input files by role, keeping only files that exist as paths."""
    files: dict[str, Path] = {}
    if case_path is not None:
        files["case"] = case_path
    for role, supplied in (
        ("mesh", resolved.mesh),
        ("profile", resolved.profile),
        ("charge", resolved.charge),
        ("eps_r", resolved.eps_r),
        ("pqr", resolved.pqr),
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

DENSITY_RECORD_KEYS: tuple[str, ...] = (
    "grid",
    "radius_set",
    "sharpness",
    "frames",
    "atoms",
    "hydrogens",
    "payload_digest",
)

REDUCTION_RECORD_KEYS: tuple[str, ...] = (
    "n",
    "bins",
    "unresolved_radius_nm",
    "maximum",
    "payload_digest",
)

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


PROTONATION_RECORD_KEYS: tuple[str, ...] = (
    "source",
    "q_net_e",
    "forcefield",
    "ph",
    "titration",
    "arguments",
    "variant",
    "frames",
    "versions",
    "unapplied",
    "chain_differences",
    "radii",
    "registration",
    "warnings",
    "pqr_sha256",
    "payload_digest",
)


def _record(artefact: Artefact | None, keys: tuple[str, ...]) -> dict[str, Canonicalisable] | None:
    if artefact is None:
        return None
    return {key: artefact.summary[key] for key in keys if key in artefact.summary}


def _mesh_record(walk: _Walk, mesh: Artefact | None) -> dict[str, Canonicalisable] | None:
    if mesh is None:
        return None
    record = dict(mesh.summary)
    if walk.resolved.generates_mesh:
        # Members whose salts size the wall alike share one stored mesh, so its summary holds the
        # Debye length of whichever member meshed first, not this run's.
        sizing = record["sizing"]
        assert isinstance(sizing, dict)  # a generated mesh's summary carries its sizing block
        record["sizing"] = {**sizing, **case_debye_record(walk.resolved)}
    return record


def _manifest(walk: _Walk, *, case_text: str, case_path: Path | None) -> Manifest:
    case = walk.artefacts.get("case")
    structure = walk.artefacts.get("structure")
    density = walk.artefacts.get("density")
    symmetry = walk.artefacts.get("symmetry")
    contour = walk.artefacts.get("contour")
    region = walk.artefacts.get("region")
    mesh = walk.artefacts.get("mesh")
    charge = walk.artefacts.get("charge")
    protonation = walk.artefacts.get("protonation")
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
        input_files=input_files(walk.resolved, case_path),
        upstream=dict(walk.artefacts),
        mesh=_mesh_record(walk, mesh),
        structure=_record(structure, STRUCTURE_RECORD_KEYS),
        density=_record(density, DENSITY_RECORD_KEYS),
        reduction=_record(symmetry, REDUCTION_RECORD_KEYS),
        contour=_record(contour, CONTOUR_RECORD_KEYS),
        region=dict(region.summary) if region is not None else None,
        charge=dict(charge.summary) if charge is not None else None,
        charge_reason=None if charge is not None else _charge_reason(walk),
        protonation=_record(protonation, PROTONATION_RECORD_KEYS),
        protonation_reason=None if protonation is not None else _protonation_reason(walk),
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


def _short_of_stage_7(walk: _Walk) -> str:
    order = walk_order()
    if walk.records and "charge" in order:
        target = str(walk.records[-1].name)
        if target in order and order.index(target) > order.index("charge"):
            return f"the walk to {target!r} does not read stage 7, so it did not run it"
    return "the walk stopped before stage 7"


def _protonation_reason(walk: _Walk) -> str:
    resolved = walk.resolved
    if not resolved.protonates:
        return (
            "this case supplies inputs.charge, which replaces what stage 7 makes of a protonation"
            if resolved.charge is not None
            else "this case carries no structure: section and supplies no inputs.pqr"
        )
    if not resolved.deposits_charge:
        return (
            f"physics.model {resolved.model!r} declares no fixed_charge, so nothing deposits a "
            "protonation; it runs only when a walk names it, as `nanopnp stage protonation`"
        )
    return _short_of_stage_7(walk)


def _charge_reason(walk: _Walk) -> str:
    resolved = walk.resolved
    if (
        resolved.deposits_charge
        or resolved.charge is not None
        or resolved.eps_r is not None
        or resolved.derives_eps_r
    ):
        return _short_of_stage_7(walk)
    if resolved.protonates:
        return (
            f"physics.model {resolved.model!r} declares no fixed_charge, so stage 7 deposits "
            "nothing, and the case supplies neither inputs.charge nor inputs.eps_r"
        )
    return (
        "this run supplied neither inputs.charge nor inputs.eps_r and carries no structure: "
        "section and no inputs.pqr, so stage 7 had nothing to deposit or read"
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
    on_artefact: ArtefactHook | None = None,
) -> RunResult:
    """Walk the pipeline for one validated case and return what it produced.

    Parameters
    ----------
    case_text
        The case file verbatim, embedded in the manifest.
    case_path
        Where the case was read from; ``None`` for a case assembled in memory.
    upto
        Stop after this stage; ``None`` walks the whole pipeline.
    only
        Take every upstream payload-writing stage from the store, aborting naming it if absent.
    options
        Per-stage options, by stage name.
    arguments
        Per-stage constructor arguments, by stage name; none enters an artefact key.
    workspace
        Directory for the file-writing stages; a fresh one under ``store`` when ``None``.
    write
        Whether to write the run directory.
    progress
        Called with a monotone fraction in [0, 1] and a message.
    cancel
        Checked before every stage and threaded into each of them.
    on_stage
        Called before each stage with its name and its position in the walk.
    on_solve
        Called with each continuation rung and accepted Newton step of the solve.
    on_artefact
        Called after each stage with its artefact's schema, hash and whether the store held it.

    Raises
    ------
    MissingUpstreamError
        If ``only`` is set and an upstream artefact is not in the store.
    nanopnp.core.stages.Cancelled
        If ``cancel`` turns true; no run directory is written.
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
    try:
        return _walk(
            walk,
            upto=upto,
            case_text=case_text,
            case_path=case_path,
            write=write,
            progress=progress,
            cancel=cancel,
            on_stage=on_stage,
            on_solve=on_solve,
            on_artefact=on_artefact,
        )
    finally:
        if walk.scratch is not None:
            # Store.put copied every payload a stage wrote here into the store,
            # and every artefact the walk holds points there, so nothing reads
            # this directory once the walk is over. Left behind, it doubled every
            # mesh, field export and solution on disk, once per sweep member.
            shutil.rmtree(walk.scratch, ignore_errors=True)


def stored_upstream(
    document: CaseDocument, *, store: Store, feeding: str = "solve"
) -> dict[str, Artefact]:
    """Return the artefacts a walk hands feeding, read from the store without running a stage.

    Parameters
    ----------
    store
        Where the payload-writing stages' artefacts are looked up.
    """
    artefacts: dict[str, Artefact] = {}
    resolved = resolve(document)
    for name in selected_stages(resolved, feeding)[:-1]:
        key = create(name).key(StageInputs(resolved=resolved, upstream=offered(name, artefacts)))
        if describe(name).key_is_artefact:
            artefacts[name] = key
            continue
        found = store.get(key.schema, key.hash)
        if found is None:
            raise MissingUpstreamError(
                f"stage {name!r} of case {document.name!r} produces {key.schema} "
                f"{key.short_hash}, which is not in the store at {store.root}"
            )
        artefacts[name] = found
    return artefacts


def _walk(
    walk: _Walk,
    *,
    upto: str | None,
    case_text: str,
    case_path: Path | None,
    write: bool,
    progress: Progress | None,
    cancel: CancelToken | None,
    on_stage: StageHook | None,
    on_solve: SolveHook | None,
    on_artefact: ArtefactHook | None,
) -> RunResult:
    document = walk.document
    stages = selected_stages(walk.resolved, upto)
    weights = [describe(name).weight for name in stages]
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
            stage.key(inputs),
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
        walk.contributed.extend(_contributed(stage, walk.inputs(name, own=True)))
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
        if on_artefact is not None:
            # After ``_resolve_stage`` has put the artefact in the store or found
            # it there, so a reader told this hash can read the entry at once.
            # Handed the record's values, never a key: the hook cannot reach one.
            on_artefact(name, artefact.schema, artefact.hash, walk.records[-1].cached)
    report(progress, 1.0, f"{len(stages)} stages complete")

    manifest = _manifest(walk, case_text=case_text, case_path=case_path)
    # A truncated walk is another record of the same case; it must not replace the
    # run record a complete walk wrote, because QR-08 reproduces from that one.
    # Complete when it walks every stage this case walks. Reaching the last one is
    # not enough: a walk runs its target's input closure, so a target
    # walked last that reads only some of the stages before it is still truncated.
    complete = stages == selected_stages(walk.resolved, None)
    label = document.name if complete else f"{document.name}-upto-{stages[-1]}"
    result = RunResult(
        directory=walk.store.run_directory(label, manifest.case_hash),
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
    on_artefact: ArtefactHook | None = None,
) -> RunResult:
    """Load a case file and run it; the keywords are those of :func:`run_document`."""
    source = Path(path)
    text = source.read_text(encoding="utf-8")
    return run_document(
        loads_case(text, source=str(source)),
        case_text=text,
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
        on_artefact=on_artefact,
    )

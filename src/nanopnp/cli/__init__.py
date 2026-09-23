"""Command-line entry points (IF-02).

The CLI drives the same stage objects as the Python API and the desktop shell
(SPECIFICATION.md section 5.1); it holds no logic of its own. Every subcommand
here is a few lines of argument marshalling in front of one call into
:mod:`nanopnp.io.run`, :mod:`nanopnp.io.reproduce` or the stage registry, which
is what makes the three shells demonstrably the same program.

**No flag changes what is solved** (section 3.1 NOTE, IF-02). Flags choose where
output is written, which stages run and how much is logged; every quantity that
changes a number lives in the case file, because a flag duplicating a case-file
setting would make the FR-25 manifest describe one of two disagreeing sources of
truth.

**Standard output carries only the command's own result.** Log records and
diagnostics go to standard error, so that a sweep parsing stdout — or a reader
of ``--json`` — receives the answer and nothing else. That is the other half of
the rule forbidding :func:`print` outside this module.

**Nothing here imports a stage module.** ``nanopnp stage --list`` answers from
:func:`nanopnp.core.stages.registered_stages`, and the modules that would pull in
NGSolve are imported inside the subcommand that needs them, keeping
``import nanopnp.cli`` at the ~70 ms the deferred-import rule protects.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import os
import platform
import sys
from pathlib import Path
from typing import TYPE_CHECKING, cast

from nanopnp import __version__
from nanopnp.cli.errors import EXIT_OK, EXIT_UNEXPECTED, classify
from nanopnp.core.paths import (
    CORRECTIONS_DIR,
    DATA_DIR,
    GEOMETRY_DIR,
    REFERENCE_DATA_VARIABLE,
    STORE_ROOT_VARIABLE,
    reference_data_root,
    store_root,
)

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from collections.abc import Mapping, Sequence

    import numpy as np

    from nanopnp.core.hashing import Canonicalisable
    from nanopnp.io.artefact import SweepArtefact
    from nanopnp.io.case import CaseDocument, ResolvedCase
    from nanopnp.io.store import Store
    from nanopnp.sweep.plan import SweepPlan
    from nanopnp.validation.comsol import Golden
    from nanopnp.validation.probe import ProbeDocument, ProbeGrid
    from nanopnp.validation.runs import ReopenedRun

__all__ = ["main"]

logger = logging.getLogger(__name__)

_LEVELS = (logging.WARNING, logging.INFO, logging.DEBUG)
"""Log level by ``-v`` count: none, ``-v``, ``-vv``."""


def _common(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Add the flags every subcommand shares.

    They are added to each subparser rather than to the top-level parser because
    an option declared in both positions has the subparser's default overwrite
    whatever the top level parsed — a silent one, since argparse reports no
    conflict.
    """
    parser.add_argument("--json", action="store_true", help="write the result to stdout as JSON")
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        dest="verbose",
        help="log at INFO; twice for DEBUG. Log records go to stderr",
    )
    parser.add_argument(
        "--log-file", type=Path, default=None, help="also write log records to this file"
    )
    parser.add_argument(
        "--traceback",
        action="store_true",
        help="print the traceback of a failure; suppressed by default, because a gate abort's "
        "diagnostic is the message (QR-12)",
    )
    return parser


def _configure_logging(verbose: int, log_file: Path | None) -> None:
    """Send log records to stderr, and to ``log_file`` if one was asked for."""
    level = _LEVELS[min(verbose, len(_LEVELS) - 1)]
    handlers: list[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    if log_file is not None:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    logging.basicConfig(
        level=level,
        handlers=handlers,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        force=True,
    )


def _emit(payload: dict[str, Canonicalisable], lines: Sequence[str], *, as_json: bool) -> None:
    """Write the command's result to stdout, as JSON or as text."""
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True, default=str))
        return
    for line in lines:
        print(line)


def _environment() -> dict[str, Canonicalisable]:
    """Return the resolved environment and data locations."""
    reference = reference_data_root()
    return {
        "version": __version__,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "data": str(DATA_DIR),
        "corrections": str(CORRECTIONS_DIR),
        "geometry": str(GEOMETRY_DIR),
        "store": str(store_root()),
        STORE_ROOT_VARIABLE: os.environ.get(STORE_ROOT_VARIABLE),
        "reference_data": str(reference) if reference is not None else None,
        REFERENCE_DATA_VARIABLE: os.environ.get(REFERENCE_DATA_VARIABLE),
    }


def _env(args: argparse.Namespace) -> int:
    """``nanopnp env`` — report the resolved environment and data locations."""
    found = _environment()
    lines = [
        f"nanopnp   {found['version']}",
        f"python    {found['python']} on {found['platform']}",
        f"data      {found['data']}",
        f"store     {found['store']} "
        f"({STORE_ROOT_VARIABLE}={found[STORE_ROOT_VARIABLE] or 'unset'})",
        f"reference {found['reference_data'] or 'none'} "
        f"({REFERENCE_DATA_VARIABLE}={found[REFERENCE_DATA_VARIABLE] or 'unset'})",
    ]
    _emit(found, lines, as_json=bool(getattr(args, "json", False)))
    return EXIT_OK


def _run(args: argparse.Namespace) -> int:
    """``nanopnp run`` — walk the pipeline for one case file (FR-27, IF-01)."""
    from nanopnp.io.run import run_case
    from nanopnp.io.store import Store

    result = run_case(
        args.case,
        store=Store(args.store),
        upto=args.upto,
        write=False,
    )
    if args.run_dir is not None:
        # The driver derives the run directory from the store and the case hash;
        # `--run-dir` moves where the three files land and nothing else, so it is
        # applied after the walk rather than fed into it. No number depends on it.
        result = dataclasses.replace(result, directory=Path(args.run_dir))
    record = result.write()

    payload = dict(result.record())
    lines = [f"run      {result.directory}", f"record   {record}"]
    lines += [
        f"stage {entry.number:>2} {entry.name:<10} {'cached' if entry.cached else 'computed':<8} "
        f"{entry.hash[:12]} {entry.seconds:8.3f} s"
        for entry in result.stages
    ]
    lines += [f"{name:<20} {value}" for name, value in sorted(result.quantities.items())]
    lines += [f"file     {path}" for path in result.files]
    _emit(payload, lines, as_json=args.json)
    return EXIT_OK


def _stage(args: argparse.Namespace) -> int:
    """``nanopnp stage`` — list the registry, or run one stage of a case."""
    from nanopnp.core.stages import registered_stages

    if args.list:
        # Answered from the registry alone: no stage module, no NGSolve, no
        # netgen (VER-25, VER-32). The import above is `nanopnp.core.stages`,
        # which holds descriptions and constructor paths as data.
        descriptions = registered_stages()
        payload: dict[str, Canonicalisable] = {
            "stages": [description.summary() for description in descriptions]
        }
        lines = [
            f"{description.number:>2}  {description.name:<10} {description.title:<28} "
            f"{description.artefact_schema}"
            for description in descriptions
        ]
        _emit(payload, lines, as_json=args.json)
        return EXIT_OK

    if args.name is None or args.case is None:
        # A usage error, so it exits 2 through argparse rather than being
        # classified: nothing was run and nothing is in doubt.
        args.parser.error("give a stage name and a case file, or --list")

    from nanopnp.io.run import run_case
    from nanopnp.io.store import Store

    result = run_case(
        args.case,
        store=Store(args.store),
        upto=args.name,
        only=args.only,
        write=False,
    )
    artefact = result.artefacts[args.name]
    found: dict[str, Canonicalisable] = {
        "stage": args.name,
        "schema": artefact.schema,
        "hash": artefact.hash,
        "parameters": dict(artefact.parameters),
        "summary": dict(artefact.summary),
        "payload": {name: str(path) for name, path in sorted(artefact.payload.items())},
        "stages": [entry.summary() for entry in result.stages],
    }
    lines = [
        f"stage    {args.name}",
        f"schema   {artefact.schema}",
        f"hash     {artefact.hash}",
        *(f"payload  {name} {path}" for name, path in sorted(artefact.payload.items())),
    ]
    _emit(found, lines, as_json=args.json)
    return EXIT_OK


def _inspect(args: argparse.Namespace) -> int:
    """``nanopnp inspect`` — read an artefact or a run directory back (FR-27).

    Takes what is on disk: a run directory, a stored artefact's directory, or
    either of their JSON records. Everything it prints was written by the run,
    so an artefact edited by hand reads back as edited — section 5.3.2 requires
    that be recorded rather than refused.
    """
    from nanopnp.core.hashing import decode_floats
    from nanopnp.io.manifest import MANIFEST_FILENAME
    from nanopnp.io.manifest import read as read_manifest
    from nanopnp.io.run import RUN_RECORD_FILENAME

    target = Path(args.target)
    if target.is_dir():
        for candidate in (MANIFEST_FILENAME, "meta.json", RUN_RECORD_FILENAME):
            if (target / candidate).is_file():
                target = target / candidate
                break
        else:
            raise FileNotFoundError(
                f"{args.target} holds no {MANIFEST_FILENAME}, meta.json or {RUN_RECORD_FILENAME}; "
                "give a run directory, a stored artefact directory, or one of those files"
            )
    # Both files are written through ``canonical``, which encodes every float as
    # ``{"__f__": <hex>}`` so that the digest is exact. That is the right thing
    # to hash and the wrong thing to read: undone here, so that the one command
    # whose job is to read a run back reports ``bias_V 0.02`` rather than the
    # wrapper -- and so that ``--json`` hands a sweep numbers it can compare.
    if target.name == MANIFEST_FILENAME:
        raw: Canonicalisable = dict(read_manifest(target))
    else:
        raw = json.loads(target.read_text(encoding="utf-8"))
    # ``cast`` and not a check: both files hold a JSON object at the top level
    # by construction, and one that does not is a file this command did not
    # write -- which the ``sorted(document.items())`` below reports as the
    # AttributeError it is, under exit 1, with ``--traceback`` to hand.
    document = cast("dict[str, Canonicalisable]", decode_floats(raw))

    lines = [f"{target}"]
    lines += [
        f"{key:<20} {json.dumps(value, default=str)}" for key, value in sorted(document.items())
    ]
    _emit(document, lines, as_json=args.json)
    return EXIT_OK


def _reproduce(args: argparse.Namespace) -> int:
    """``nanopnp reproduce`` — re-run an archived run and compare it (QR-08)."""
    from nanopnp.io.reproduce import reproduce
    from nanopnp.io.store import Store

    finding = reproduce(
        args.directory,
        store=Store(args.store) if args.store is not None else None,
        tolerance=args.tolerance,
        strict_environment=args.strict_environment,
    )
    payload = finding.summary()
    worst = finding.worst
    lines = [
        f"directory {finding.directory}",
        f"manifest  {finding.manifest_hash}",
        f"compared  {len(finding.quantities)} quantities at rtol {finding.tolerance:g}",
        f"worst     {'none compared' if worst is None else f'{worst:.3e}'}",
        f"result    {'reproduced' if finding.reproduced else 'NOT reproduced'}",
    ]
    lines += [
        f"drift     {drift.path}: {drift.recorded!r} -> {drift.reproduced!r}"
        for drift in finding.drifts
    ]
    lines += [
        f"env       {item.key}: {item.recorded!r} -> {item.current!r}"
        for item in finding.environment
    ]
    _emit(payload, lines, as_json=args.json)
    return EXIT_OK if finding.reproduced else 1


def _mesh(args: argparse.Namespace) -> int:
    """``nanopnp mesh`` — write a gated MSH 4.1 mesh for a case to read (IF-02).

    A generator, not a run: section 3.1's generators NOTE. The geometric flags of
    ``mesh cylinder`` shape the *file*, and the run that later reads it records
    it by content hash through ``inputs.mesh`` exactly as it would an external
    mesh, so no flag here changes what a run solves.

    The file is gated by the route a run ingests it by — written beside its
    destination, read back, mapped through the groups printed, then checked on
    element quality and radii (VER-10, VER-27) — and moved into place only once
    that passes. So the hash printed is the one the run's manifest records, and a
    mesh the gate refuses leaves no file for a case to pick up by mistake.
    """
    from nanopnp.mesh.adapter import from_ngsolve, read, write_msh41
    from nanopnp.mesh.ingest import apply_groups
    from nanopnp.mesh.quality import check_quality, check_radii

    # A destination that cannot be written is a usage error, refused before the
    # mesher runs (the reference geometry takes seconds): left to the write, a
    # missing directory would exit 3 as though a case were refused, naming the
    # staging file, and a directory would exit 1 as an unexpected failure.
    out = Path(args.out)
    if not out.name or out.is_dir():
        args.parser.error(f"--out {out} is a directory; name the .msh file to write")
    if not out.parent.is_dir():
        args.parser.error(f"--out {out}: the directory {out.parent} does not exist")

    if args.shape == "cylinder":
        from nanopnp.mesh.primitives import CylindricalPoreGeometry

        if args.pore_radius_nm >= args.reservoir_radius_nm:
            args.parser.error(
                f"--pore-radius-nm {args.pore_radius_nm:g} must be smaller than "
                f"--reservoir-radius-nm {args.reservoir_radius_nm:g}"
            )
        geometry = CylindricalPoreGeometry(
            pore_radius_nm=args.pore_radius_nm,
            membrane_thickness_nm=args.membrane_thickness_nm,
            reservoir_radius_nm=args.reservoir_radius_nm,
        )
        # Ungated here and gated below, on the file as written: one gate, on
        # the object a run will actually read.
        generated = geometry.generate(
            maxh_nm=args.maxh_nm, wall_h_nm=args.wall_h_nm, check_quality=False
        )
    else:
        from nanopnp.mesh.reference import ReferenceGeometry

        generated = ReferenceGeometry.from_fixture().generate(check_quality=False)
    data = from_ngsolve(generated)

    # OCC leaves the seams nothing names at NGSolve's ``default``: the two pore
    # mouths of the cylinder, which separate fluid from fluid. They map to
    # ``interface``, which nothing selects on. The reference geometry names its
    # own seams and needs no mapping. Anything else outside the vocabulary is
    # refused by ``apply_groups`` below, naming the group.
    groups = {"default": "interface"} if "default" in data.boundaries else {}

    # The process id keeps two generators aimed at one destination from sharing
    # a staging file, which would let one gate, hash and print the other's mesh.
    partial = out.with_name(f".{out.stem}.{os.getpid()}.partial{out.suffix}")
    where = f"the generated mesh {out.name!r}"
    try:
        write_msh41(data, partial)
        mapped, _applied = apply_groups(read(partial, format="msh41"), groups)
        quality = check_quality(mapped, where=where)
        check_radii(mapped, where=where)
        partial.replace(out)
    finally:
        partial.unlink(missing_ok=True)

    flow = "{" + ", ".join(f"{key}: {value}" for key, value in sorted(groups.items())) + "}"
    payload: dict[str, Canonicalisable] = {
        "path": str(out),
        "format": "msh41",
        "content_hash": mapped.content_hash,
        "groups": dict(sorted(groups.items())),
        "elements": mapped.element_count,
        "vertices": mapped.vertex_count,
        "materials": list(mapped.materials),
        "boundaries": list(mapped.boundaries),
        "min_sicn": quality.min_sicn,
        "min_gamma": quality.min_gamma,
    }
    lines = [
        f"mesh      {out}",
        f"hash      {mapped.content_hash}",
        f"elements  {mapped.element_count} ({mapped.vertex_count} vertices)",
        f"quality   min SICN {quality.min_sicn:.3f}, min gamma {quality.min_gamma:.3f}",
        f"domains   {', '.join(mapped.materials)}",
        f"groups    {flow}",
        "",
        "inputs:",
        "  mesh:",
        f"    path: {out}",
        "    format: msh41",
        f"    groups: {flow}",
    ]
    _emit(payload, lines, as_json=args.json)
    return EXIT_OK


def _positive_nm(text: str) -> float:
    """Parse a length in nm that must be positive and finite."""
    value = float(text)
    if not 0.0 < value < float("inf"):
        raise argparse.ArgumentTypeError(f"{text!r} is not a positive length in nm")
    return value


def _sweep(args: argparse.Namespace) -> int:
    """``nanopnp sweep`` — plan, dispatch or collect a parameter sweep (FR-24, IF-02).

    Three sub-subcommands over one plan file, and no flag among them changes a
    case-file field: the axes are in the sweep document, which is where a
    physics quantity belongs (the §3.1 configuration NOTE applied one level up).
    ``--index``, ``--wave`` and ``--workers`` choose *which* members run and on
    how many processes, which changes how long the sweep takes and no number it
    produces.
    """
    from nanopnp.io.store import Store
    from nanopnp.sweep.plan import plan_from_document, read_plan, write_plan

    store = Store(args.store)
    if args.action == "plan":
        plan = plan_from_document(args.document, check_meshes=not args.no_mesh_check)
        if args.directory is None:
            directory = store.sweep_directory(plan.name, plan.hash)
        else:
            # Where the plan and its member records go, and nothing else: the
            # members still solve into the store. A named directory is not keyed
            # by the plan hash, so one holding a *different* plan is refused
            # rather than overwritten -- its member records would otherwise be
            # collected against points they were never solved for.
            directory = Path(args.directory)
            _refuse_another_plan(directory, plan.hash)
        path = write_plan(plan, directory)
        payload: dict[str, Canonicalisable] = {
            "plan": str(path),
            "directory": str(directory),
            "hash": plan.hash,
            "points": len(plan.points),
            "waves": [list(span) for span in plan.waves()],
            "warnings": list(plan.warnings),
        }
        lines = [
            f"plan     {path}",
            f"hash     {plan.hash}",
            f"points   {len(plan.points)} in {len(plan.waves())} wave(s)",
        ]
        # The contiguous index range of each wave, which is the whole of the
        # scheduler integration this project does: a job array is two lines of
        # the user's own shell over these, and a scheduler library on the
        # end-user path is what CON-07 forbids.
        lines += [
            f"wave {wave:>3}  --index {first}..{last - 1}  ({last - first} point(s))"
            for wave, (first, last) in enumerate(plan.waves())
        ]
        lines += [f"warning  {line}" for line in plan.warnings]
        _emit(payload, lines, as_json=args.json)
        return EXIT_OK

    plan = read_plan(args.plan)
    directory = Path(args.plan).parent
    if args.action == "collect":
        return _sweep_collect(args, plan, directory)
    return _sweep_run(args, plan, directory, store=store)


def _refuse_another_plan(directory: Path, digest: str) -> None:
    """Refuse a ``--directory`` that already holds a plan with another hash (FR-24)."""
    from nanopnp.sweep.plan import PLAN_FILENAME, SweepPlanError, read_plan

    existing = directory / PLAN_FILENAME
    if existing.is_file() and read_plan(existing).hash != digest:
        raise SweepPlanError(
            f"{directory} already holds the plan of a different sweep; its member records "
            "would be collected against points they were not solved for. Choose another "
            "--directory, or remove that one"
        )


def _sweep_run(args: argparse.Namespace, plan: SweepPlan, directory: Path, *, store: Store) -> int:
    """Dispatch one member, one wave, or the whole plan (FR-24, QR-06)."""
    from nanopnp.sweep.plan import SweepPlanError
    from nanopnp.sweep.run import run_plan, run_point

    if args.index is not None:
        member = run_point(plan, args.index, store=store, directory=directory)
        _emit(
            member.row(),
            [f"point {member.index} {member.point_id} {member.status}"],
            as_json=args.json,
        )
        # The member's *own* exit code. The IF-02 exit NOTE exists so a job
        # array can branch per member, and per-member codes are what that means.
        return member.exit_class

    indices: range | None = None
    if args.wave is not None:
        waves = plan.waves()
        # Named rather than left to ``IndexError``, exactly as ``--index`` is:
        # a job array submitted over the wrong range is a configuration mistake,
        # and a negative index would otherwise select a wave from the end
        # silently (QR-12).
        if not 0 <= args.wave < len(waves):
            raise SweepPlanError(
                f"this plan has {len(waves)} waves, 0 to {len(waves) - 1}; "
                f"there is no wave {args.wave}"
            )
        first, last = waves[args.wave]
        indices = range(first, last)
    # ``--workers`` overrides the sweep document's own default, which the plan
    # carries; neither reaches a case-file field, so neither reaches a manifest.
    workers = args.workers if args.workers is not None else (plan.workers or 1)
    members = run_plan(
        plan,
        directory,
        store=store,
        workers=workers,
        indices=indices,
        fail_fast=args.fail_fast,
    )
    # The files a job array leaves behind are what `sweep collect` reads too, so
    # a wave-at-a-time dispatch and a local run build the same table by the same
    # route; see :func:`_sweep_dataset`.
    artefact = _sweep_dataset(args, plan, directory)
    counts: dict[str, int] = {}
    for member in members:
        counts[member.status] = counts.get(member.status, 0) + 1
    lines = [f"dataset  {directory / 'dataset.json'}"]
    lines += [f"{status:<16} {count}" for status, count in sorted(counts.items())]
    _emit(dict(artefact.summary), lines, as_json=args.json)
    # Zero when every member reached a terminal state and the dataset was
    # written. Non-convergence at the corners of a hard envelope is an expected
    # *result*, and turning it into a nonzero exit would make a sweep that
    # worked indistinguishable from one that was broken; ``--fail-fast`` is for
    # the caller who wants the other behaviour, and it stops at the first one.
    if args.fail_fast and any(member.status != "ok" for member in members):
        return next(member.exit_class for member in members if member.status != "ok")
    return EXIT_OK


def _sweep_collect(args: argparse.Namespace, plan: SweepPlan, directory: Path) -> int:
    """Build the dataset from whatever member records are on disk."""
    artefact = _sweep_dataset(args, plan, directory)
    counts = artefact.summary.get("counts", {})
    lines = [f"dataset  {directory / 'dataset.json'}"]
    lines += [f"{status:<16} {count}" for status, count in sorted(dict(counts).items())]
    if args.csv:
        lines.append(f"csv      {directory / 'dataset.csv'}")
    _emit(dict(artefact.summary), lines, as_json=args.json)
    return EXIT_OK


def _sweep_dataset(args: argparse.Namespace, plan: SweepPlan, directory: Path) -> SweepArtefact:
    """Collect and, if asked, export. Shared by ``run`` and ``collect``.

    Always from the member files on disk: ``--wave`` runs a subset, and a dataset
    built from the records this process happens to hold would overwrite the
    accumulated table with one whose other rows all read ``not_dispatched``.
    """
    from nanopnp.sweep.collect import collect, write_csv

    artefact = collect(plan, directory)
    if getattr(args, "csv", False):
        write_csv(artefact, directory)
    return artefact


def _validate(args: argparse.Namespace) -> int:
    """``nanopnp validate`` — the Tier-3 harness (VAL-01 … VAL-04, section 7.4).

    Six actions over one probe grid, and none of them changes what is solved:
    ``export-grid`` and ``case-hash`` emit what the author pastes into COMSOL and
    declares in a manifest; ``ingest-golden`` turns delivered tables into the
    archive; ``export-golden`` writes one of *our* runs in the same format, which
    is how the harness is exercisable before the exports land; ``compare`` and
    ``report`` read finished runs and produce the numbers.

    ``compare`` and ``report`` never solve. The ladder's twenty members are
    dispatched by ``nanopnp sweep run``, and a comparison that re-solved would
    compare a second solution while the manifest described the first
    (:mod:`nanopnp.validation.runs`).
    """
    actions = {
        "export-grid": _validate_export_grid,
        "case-hash": _validate_case_hash,
        "ingest-golden": _validate_ingest_golden,
        "export-golden": _validate_export_golden,
        "compare": _validate_compare,
        "report": _validate_report,
    }
    return actions[args.action](args)


def _validate_export_grid(args: argparse.Namespace) -> int:
    """Print a probe grid's hash and the ``%Grid`` axis lines COMSOL is given."""
    from nanopnp.validation.probe import load_probe

    document = load_probe(args.probe)
    text = document.write_comsol_axes()
    if args.output is not None:
        Path(args.output).write_text(text, encoding="utf-8")
    payload: dict[str, Canonicalisable] = {
        "probe": document.name,
        "probe_hash": document.hash,
        "points": document.count,
        "patches": [patch.summary() for patch in document.patches],
        "output": None if args.output is None else str(args.output),
    }
    lines = [f"probe      {document.name}", f"probe_hash {document.hash}"]
    lines += [
        f"patch      {patch.name}: n_r {patch.n_r} x n_z {patch.n_z} = {patch.count} points"
        for patch in document.patches
    ]
    lines.append(f"points     {document.count}")
    if args.output is not None:
        lines.append(f"axes       {args.output}")
    elif not args.json:
        lines += ["", text.rstrip("\n")]
    _emit(payload, lines, as_json=args.json)
    return EXIT_OK


def _validate_case_hash(args: argparse.Namespace) -> int:
    """Print the ``case_hash`` a golden for this case must declare."""
    from nanopnp.io.case import load_case, resolve
    from nanopnp.validation.comsol import case_identity

    document = load_case(args.case)
    identity = case_identity(resolve(document))
    payload: dict[str, Canonicalisable] = {"case": document.name, "case_hash": identity}
    _emit(payload, [f"case      {document.name}", f"case_hash {identity}"], as_json=args.json)
    return EXIT_OK


def _validate_ingest_golden(args: argparse.Namespace) -> int:
    """Turn a directory of exported ``%Grid`` tables into the archived golden."""
    from nanopnp.validation.comsol import ingest_golden, load_golden

    archive = ingest_golden(args.directory, probe=args.probe, destination=args.destination)
    golden = load_golden(archive)
    payload = dict(golden.summary())
    payload["archive"] = str(archive)
    lines = [
        f"archive     {archive}",
        f"golden_hash {golden.hash}",
        f"case        {golden.manifest.case} ({golden.manifest.refinement})",
        f"source      {golden.source}",
        f"fields      {', '.join(sorted(golden.values))}",
        "sign        "
        + (
            "flipped to the section 6.7 convention"
            if golden.current_sign_flipped
            else "as exported (cis)"
        ),
    ]
    _emit(payload, lines, as_json=args.json)
    return EXIT_OK


def _validate_export_golden(args: argparse.Namespace) -> int:
    """Write one of our own finished runs as a golden: the self-golden path.

    The report it later feeds carries ``golden_source: self`` and every consumer
    prints it, because a ladder run against one tests the machinery and nothing
    else.
    """
    from nanopnp.validation.comsol import (
        GOLDEN_SCHEMA,
        GoldenManifest,
        case_identity,
        export_golden,
    )

    document, sampled, resolved = _sampled_run(args)
    manifest = GoldenManifest.model_validate(
        {
            "schema": GOLDEN_SCHEMA,
            "case": resolved.case.name,
            "case_hash": case_identity(_resolved(resolved.case)),
            "probe": document.name,
            "probe_hash": document.hash,
            "refinement": args.refinement,
            "source": "self",
            "comsol_version": f"nanopnp {__version__} (self-golden, no COMSOL)",
            "model_file": str(resolved.directory),
            "export_date": args.export_date,
            "fields": {name: {"expression": name, "unit": _unit(name)} for name in sorted(sampled)},
            "current_boundary": "the NUM-24 domain indicator, not a boundary",
            "current_sign_reference": "cis",
            "quantities": _self_quantities(resolved.quantities),
        }
    )
    archive = export_golden(
        sampled, manifest, args.destination, tables=document if args.tables else None
    )
    payload: dict[str, Canonicalisable] = {
        "archive": str(archive),
        "case": manifest.case,
        "golden_source": "self",
        "fields": sorted(sampled),
    }
    _emit(
        payload,
        [
            f"archive {archive}",
            f"case    {manifest.case}",
            "source  self -- this golden tests the harness and nothing else",
            f"fields  {', '.join(sorted(sampled))}",
        ],
        as_json=args.json,
    )
    return EXIT_OK


def _validate_compare(args: argparse.Namespace) -> int:
    """Compare one finished run against one golden, field by field and QoI by QoI."""
    from nanopnp.validation.compare import (
        compare_fields,
        compare_quantities,
        unavailable_quantities,
    )
    from nanopnp.validation.comsol import case_identity, load_golden

    document, sampled, resolved = _sampled_run(args)
    golden = load_golden(args.golden)
    golden.check_case(case_identity(_resolved(resolved.case)))
    golden.check_probe(document)
    grid = _probe_grid(document, resolved)
    fields = compare_fields(sampled, golden, grid)
    quantities = compare_quantities(resolved.quantities, golden.quantities)
    payload: dict[str, Canonicalisable] = {
        "run": str(resolved.directory),
        "golden_hash": golden.hash,
        "golden_source": golden.source,
        "current_sign_flipped": golden.current_sign_flipped,
        "fields": [entry.summary() for entry in fields],
        "quantities": [entry.summary() for entry in quantities],
        "unavailable_fields": list(golden.unavailable(sorted(sampled))),
        "unavailable_quantities": list(
            unavailable_quantities(resolved.quantities, golden.quantities)
        ),
    }
    lines = [
        f"run          {resolved.directory}",
        f"golden       {golden.hash[:12]} ({golden.source}, {golden.manifest.refinement})",
    ]
    lines += [
        f"{entry.field:<12} rel_L2_r {entry.rel_L2_r:.4e}  rel_l2 {entry.rel_l2:.4e}  "
        f"max {entry.max_abs_rel:.4e} at (r, z) = "
        f"({entry.max_at_nm[0]:.4g}, {entry.max_at_nm[1]:.4g}) nm"
        for entry in fields
    ]
    lines += [f"{entry.name:<12} {entry.relative:+.4e} relative" for entry in quantities]
    _emit(payload, lines, as_json=args.json)
    return EXIT_OK


def _validate_report(args: argparse.Namespace) -> int:
    """Run the four-rung attribution ladder over a finished ladder sweep."""
    from nanopnp.sweep.collect import read_members
    from nanopnp.sweep.plan import read_plan
    from nanopnp.validation.attribution import (
        LADDER,
        LadderError,
        RungOutcome,
        attribute,
        write_report,
    )
    from nanopnp.validation.compare import compare_fields, compare_quantities
    from nanopnp.validation.comsol import load_golden
    from nanopnp.validation.probe import load_probe
    from nanopnp.validation.runs import reopen

    document = load_probe(args.probe)
    plan = read_plan(args.plan)
    golden = load_golden(args.golden)
    golden.check_probe(document)
    directory = Path(args.plan).parent
    store = None if args.store is None else _store(args)

    by_rung: dict[int, RungOutcome] = {}
    fields_sampled: list[str] = []
    for member in read_members(directory):
        plan.point(member.index)  # refuses a member this plan does not enumerate
        rung_index = _rung_of(member.assignments)
        if member.status != "ok" or member.directory is None:
            continue
        if rung_index is None or rung_index in by_rung:
            continue
        resolved = reopen(member.directory, store=store)
        if _identity(resolved.case) != golden.manifest.case_hash:
            continue
        grid = _probe_grid(document, resolved)
        sampled = _sample(resolved, grid)
        fields_sampled = sorted(sampled)
        by_rung[rung_index] = RungOutcome(
            rung=LADDER[rung_index],
            golden_hash=golden.hash,
            probe_hash=golden.manifest.probe_hash,
            case_hash=golden.manifest.case_hash,
            fields=compare_fields(sampled, golden, grid),
            quantities=compare_quantities(resolved.quantities, golden.quantities),
            stabilisation_currents_A=_stabilisation_currents(resolved.quantities),
        )
    missing = [rung.name for rung in LADDER if rung.index not in by_rung]
    if missing:
        raise LadderError(
            f"{directory} holds no completed member for rung(s) {', '.join(missing)} of the "
            "golden's case. The ladder attributes a discrepancy by differences between adjacent "
            "rungs, so a missing one does not make the remaining deltas mean less -- it makes "
            "them mean something else. Run the sweep to completion first"
        )
    report = attribute(
        [by_rung[index] for index in range(len(LADDER))],
        case=golden.manifest.case,
        golden=golden,
        reference_errors=_reference_errors(args, document, golden),
        sampled_fields=fields_sampled,
    )
    json_path, markdown = write_report(report, args.output or directory)
    payload = dict(report.summary())
    payload["files"] = [str(json_path), str(markdown)]
    _emit(payload, [report.markdown()], as_json=args.json)
    return EXIT_OK


def _rung_of(assignments: Mapping[str, Canonicalisable]) -> int | None:
    """Return which ladder rung a sweep member is, or ``None`` if it is none of them.

    Matched on the assignments the member actually carries rather than on a grid
    coordinate: the rung's position in the sweep document's axis list is not a
    fact about the ladder, and reading it off ``coordinates[0]`` labels a member
    by whichever axis happens to be written first.
    """
    from nanopnp.validation.attribution import LADDER

    for rung in LADDER:
        if all(assignments.get(path) == value for path, value in rung.assignments().items()):
            return rung.index
    return None


def _reference_errors(
    args: argparse.Namespace, document: ProbeDocument, golden: Golden
) -> dict[str, float] | None:
    """Return VAL-04's ``Delta_ref``, or ``None`` where no refinement pair was given."""
    from nanopnp.validation.attribution import reference_error
    from nanopnp.validation.compare import golden_grid
    from nanopnp.validation.comsol import load_golden

    if args.refined is None:
        return None
    refined = load_golden(args.refined)
    refined.check_probe(document)
    return reference_error(golden, refined, golden_grid(document, golden))


def _store(args: argparse.Namespace) -> Store:
    """Return the artefact store a validate subcommand was pointed at."""
    from nanopnp.io.store import Store

    return Store(args.store)


def _resolved(case: CaseDocument) -> ResolvedCase:
    """Return a case document resolved, for the identity hash."""
    from nanopnp.io.case import resolve

    return resolve(case)


def _identity(case: CaseDocument) -> str:
    """Return a case document's Tier-3 identity hash."""
    from nanopnp.validation.comsol import case_identity

    return case_identity(_resolved(case))


def _unit(field: str) -> str:
    """Return the SI unit a self-golden declares for one field."""
    from nanopnp.validation.comsol import field_unit

    return field_unit(field)


def _self_quantities(recorded: Mapping[str, Canonicalisable]) -> dict[str, Canonicalisable]:
    """Return the ``quantities`` block of a self-golden manifest, from a run record.

    ``bias_V`` and ``current_A`` are the two the manifest requires, and a run that
    recorded neither is refused rather than defaulted to zero: a golden declaring
    0 A is not a golden with a missing current, it is a golden whose current
    comparison :func:`~nanopnp.validation.compare.compare_quantities` then skips
    for having a reference of exactly zero — a comparison quietly covering one
    quantity fewer, which is the thing the unavailable list exists to prevent.
    """
    from nanopnp.validation.runs import RunError

    wanted = ("bias_V", "current_A", "currents_A", "transport_number", "conductance_S", "eof_m3_s")
    block = {key: recorded.get(key) for key in wanted if recorded.get(key) is not None}
    absent = [key for key in ("bias_V", "current_A") if key not in block]
    if absent:
        raise RunError(
            f"the run records no {' or '.join(absent)}, which a golden manifest must declare. The "
            "stage-11 summary carries both, so this run stopped before the quantities of interest "
            "were extracted; re-run it with 'current' among its outputs"
        )
    return block


def _stabilisation_currents(
    recorded: Mapping[str, Canonicalisable],
) -> Mapping[str, float] | None:
    """Return the section 6.7 per-species stabilisation contribution a run recorded."""
    value = recorded.get("stabilisation_currents_A")
    return dict(value) if isinstance(value, dict) else None


def _probe_grid(document: ProbeDocument, resolved: ReopenedRun) -> ProbeGrid:
    """Return the probe grid bound to a reopened run's own mesh."""
    from nanopnp.validation.compare import probe_domains
    from nanopnp.validation.probe import ProbeGrid

    return ProbeGrid.on_mesh(
        document, resolved.solution.space.mesh, probe_domains(resolved.solution)
    )


def _sample(resolved: ReopenedRun, grid: ProbeGrid) -> dict[str, np.ndarray]:
    """Return a reopened run's fields on a probe grid, in SI."""
    from nanopnp.validation.compare import sample_on_probe

    return sample_on_probe(resolved.solution, grid, scales=resolved.scales)


def _sampled_run(
    args: argparse.Namespace,
) -> tuple[ProbeDocument, dict[str, np.ndarray], ReopenedRun]:
    """Return the probe document, the sampled fields and the reopened run."""
    from nanopnp.validation.probe import load_probe
    from nanopnp.validation.runs import reopen

    document = load_probe(args.probe)
    resolved = reopen(args.run, store=None if args.store is None else _store(args))
    grid = _probe_grid(document, resolved)
    return document, _sample(resolved, grid), resolved


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser, importing nothing a subcommand does not need."""
    parser = argparse.ArgumentParser(prog="nanopnp", description=__doc__.splitlines()[0])
    parser.add_argument("--version", action="version", version=f"nanopnp {__version__}")
    parser.add_argument(
        "--env",
        action="store_true",
        dest="env_flag",
        help="alias for 'nanopnp env': report the resolved environment and data locations",
    )
    subparsers = parser.add_subparsers(dest="command")

    run = _common(subparsers.add_parser("run", help="run a case file through the pipeline"))
    run.add_argument("case", type=Path, help="the case file (schema: nanopnp/case/v1)")
    run.add_argument("--store", type=Path, default=None, help="artefact store root")
    run.add_argument("--run-dir", type=Path, default=None, help="where the run directory goes")
    run.add_argument("--upto", default=None, help="stop after this stage")
    run.set_defaults(handler=_run)

    stage = _common(subparsers.add_parser("stage", help="list the registry, or run one stage"))
    stage.add_argument("name", nargs="?", default=None, help="the stage to run")
    stage.add_argument("case", nargs="?", type=Path, default=None, help="the case file")
    stage.add_argument("--list", action="store_true", help="list the registered stages and exit")
    stage.add_argument("--store", type=Path, default=None, help="artefact store root")
    stage.add_argument(
        "--only",
        action="store_true",
        help="refuse to compute anything upstream; abort naming what the store lacks",
    )
    stage.set_defaults(handler=_stage, parser=stage)

    inspect = _common(subparsers.add_parser("inspect", help="read an artefact or run back"))
    inspect.add_argument("target", type=Path, help="a run directory, artefact directory or record")
    inspect.set_defaults(handler=_inspect)

    check = _common(subparsers.add_parser("reproduce", help="re-run an archived run (QR-08)"))
    check.add_argument("directory", type=Path, help="the run directory to reproduce")
    check.add_argument("--store", type=Path, default=None, help="store to reproduce into")
    check.add_argument(
        "--tolerance", type=float, default=None, help="relative agreement every scalar must reach"
    )
    check.add_argument(
        "--strict-environment",
        action="store_true",
        help="treat a library, interpreter or platform difference as a failure",
    )
    check.set_defaults(handler=_reproduce)

    mesh = subparsers.add_parser("mesh", help="write a gated MSH 4.1 mesh for a case to read")
    shapes = mesh.add_subparsers(dest="shape", required=True)

    # The defaults are the 392-element idealised pore of the Tier-2 throughput
    # benchmark: the coarsest mesh the NUM-34 wall-distance gate admits with the
    # wall corrections on, so a first run finishes in seconds.
    cylinder = _common(
        shapes.add_parser("cylinder", help="an idealised cylindrical pore through a membrane")
    )
    cylinder.add_argument(
        "--pore-radius-nm", type=_positive_nm, default=2.0, help="lumen radius (default 2)"
    )
    cylinder.add_argument(
        "--membrane-thickness-nm",
        type=_positive_nm,
        default=6.0,
        help="membrane thickness, the lumen's length (default 6)",
    )
    cylinder.add_argument(
        "--reservoir-radius-nm",
        type=_positive_nm,
        default=10.0,
        help="radius of each quarter-disc reservoir (default 10)",
    )
    cylinder.add_argument(
        "--maxh-nm", type=_positive_nm, default=4.0, help="global maximum element size (default 4)"
    )
    cylinder.add_argument(
        "--wall-h-nm",
        type=_positive_nm,
        default=0.35,
        help="element size on the pore wall (default 0.35)",
    )
    cylinder.add_argument("--out", type=Path, required=True, help="the .msh file to write")
    cylinder.set_defaults(handler=_mesh, parser=cylinder)

    reference = _common(
        shapes.add_parser(
            "reference",
            help="the ClyA reference geometry at the section 5.2.2 preset",
        )
    )
    reference.add_argument("--out", type=Path, required=True, help="the .msh file to write")
    reference.set_defaults(handler=_mesh, parser=reference)

    sweep = subparsers.add_parser("sweep", help="plan, run or collect a parameter sweep (FR-24)")
    actions = sweep.add_subparsers(dest="action", required=True)

    planner = _common(actions.add_parser("plan", help="enumerate and check every point"))
    planner.add_argument("document", type=Path, help="the sweep file (schema: nanopnp/sweep/v1)")
    planner.add_argument("--store", type=Path, default=None, help="artefact store root")
    planner.add_argument(
        "--no-mesh-check",
        action="store_true",
        help="skip the NUM-34 wall-distance gate on the meshes the points would solve on; "
        "the combinatorics alone, for a machine with no NGSolve",
    )
    planner.add_argument(
        "--directory",
        type=Path,
        default=None,
        help="write the plan and its member records here instead of the store's "
        "sweeps/<name>-<hash>/; refused if it already holds a different plan",
    )
    planner.set_defaults(handler=_sweep)

    runner = _common(actions.add_parser("run", help="dispatch a plan's members"))
    runner.add_argument("plan", type=Path, help="the plan file written by 'sweep plan'")
    runner.add_argument("--store", type=Path, default=None, help="artefact store root")
    runner.add_argument(
        "--index", type=int, default=None, help="run one member; exits with that member's own code"
    )
    runner.add_argument("--wave", type=int, default=None, help="run one wave of the forest")
    runner.add_argument(
        "--workers",
        type=int,
        default=None,
        help="independent worker processes; defaults to the sweep document's workers:, or 1",
    )
    runner.add_argument(
        "--fail-fast", action="store_true", help="stop at the first member that does not succeed"
    )
    runner.add_argument("--csv", action="store_true", help="also write the flat CSV export")
    runner.set_defaults(handler=_sweep)

    collector = _common(actions.add_parser("collect", help="build the dataset from the members"))
    collector.add_argument("plan", type=Path, help="the plan file written by 'sweep plan'")
    collector.add_argument("--store", type=Path, default=None, help="artefact store root")
    collector.add_argument("--csv", action="store_true", help="also write the flat CSV export")
    collector.set_defaults(handler=_sweep)

    validate = subparsers.add_parser(
        "validate", help="the Tier-3 COMSOL comparison harness (section 7.4)"
    )
    steps = validate.add_subparsers(dest="action", required=True)

    # ``%%`` throughout the help strings below: argparse percent-formats help text,
    # and a bare ``%G`` makes ``--help`` raise rather than print.
    grid = _common(steps.add_parser("export-grid", help="print the %%Grid axes COMSOL is given"))
    grid.add_argument("probe", type=Path, help="the nanopnp/probe/v1 document")
    grid.add_argument("--output", type=Path, default=None, help="write the axes to this file")
    grid.set_defaults(handler=_validate)

    identity = _common(
        steps.add_parser("case-hash", help="print the case_hash a golden must declare")
    )
    identity.add_argument("case", type=Path, help="a frozen case file")
    identity.set_defaults(handler=_validate)

    ingest = _common(
        steps.add_parser("ingest-golden", help="archive a directory of exported tables")
    )
    ingest.add_argument("directory", type=Path, help="holds manifest.yaml and the %%Grid tables")
    ingest.add_argument("--probe", type=Path, required=True, help="the probe document")
    ingest.add_argument("--destination", type=Path, default=None, help="where to write the archive")
    ingest.set_defaults(handler=_validate)

    self_golden = _common(
        steps.add_parser("export-golden", help="write one of our own runs as a self-golden")
    )
    self_golden.add_argument("run", type=Path, help="a finished run directory")
    self_golden.add_argument("--probe", type=Path, required=True, help="the probe document")
    self_golden.add_argument("--destination", type=Path, required=True, help="output directory")
    self_golden.add_argument("--store", type=Path, default=None, help="artefact store root")
    self_golden.add_argument(
        "--refinement", default="published", choices=("published", "refined_1"), help="VAL-04 level"
    )
    # Required, not defaulted: the manifest refuses a blank ``export_date``, so a
    # default of "" turns an omitted flag into an unclassified pydantic failure
    # and exit 1. argparse's own exit 2 is what a missing argument means (IF-02).
    self_golden.add_argument(
        "--export-date", required=True, help="date recorded in the manifest, e.g. 2026-09-18"
    )
    self_golden.add_argument(
        "--tables", action="store_true", help="also write the %%Grid transport tables"
    )
    self_golden.set_defaults(handler=_validate)

    against = _common(steps.add_parser("compare", help="compare one run against one golden"))
    against.add_argument("run", type=Path, help="a finished run directory")
    against.add_argument("--probe", type=Path, required=True, help="the probe document")
    against.add_argument("--golden", type=Path, required=True, help="an archived golden")
    against.add_argument("--store", type=Path, default=None, help="artefact store root")
    against.set_defaults(handler=_validate)

    ladder = _common(steps.add_parser("report", help="the four-rung attribution ladder"))
    ladder.add_argument("plan", type=Path, help="the ladder sweep's plan file")
    ladder.add_argument("--probe", type=Path, required=True, help="the probe document")
    ladder.add_argument("--golden", type=Path, required=True, help="the published-mesh golden")
    ladder.add_argument(
        "--refined", type=Path, default=None, help="the refined golden, for VAL-04's Delta_ref"
    )
    ladder.add_argument("--store", type=Path, default=None, help="artefact store root")
    ladder.add_argument("--output", type=Path, default=None, help="where to write the report")
    ladder.set_defaults(handler=_validate)

    env = _common(subparsers.add_parser("env", help="report the environment and data locations"))
    env.set_defaults(handler=_env)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the ``nanopnp`` command-line interface.

    Parameters
    ----------
    argv
        Argument vector, defaulting to ``sys.argv[1:]``.

    Returns
    -------
    int
        The process exit status of section 3.1's NOTE (IF-02): ``0`` success,
        ``1`` unexpected, ``2`` usage, ``3`` the case, ``4`` a gate, ``5``
        non-convergence, ``130`` cancellation. :func:`nanopnp.cli.errors.classify`
        maps the exception to the code; a traceback is printed only under
        ``--traceback``, because a gate abort's diagnostic *is* the message.
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        if getattr(args, "env_flag", False):
            return _env(argparse.Namespace(json=False))
        parser.print_help()
        return EXIT_OK

    _configure_logging(args.verbose, args.log_file)
    if args.command == "reproduce" and args.tolerance is None:
        from nanopnp.io.reproduce import DEFAULT_TOLERANCE

        args.tolerance = DEFAULT_TOLERANCE

    handler = args.handler
    try:
        code: int = handler(args)
    except SystemExit:
        raise
    except BaseException as error:
        if args.traceback:
            raise
        code = classify(error)
        print(f"nanopnp {args.command}: {error}", file=sys.stderr)
        if code == EXIT_UNEXPECTED:
            print(
                f"nanopnp {args.command}: unexpected {type(error).__name__}; "
                "re-run with --traceback",
                file=sys.stderr,
            )
    return code


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())

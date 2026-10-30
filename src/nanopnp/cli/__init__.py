"""Command-line entry points (IF-02)."""

from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import os
import platform
import sys
import traceback
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, cast

from nanopnp.cli.export import EXPORTS, export_artefact, refusal
from nanopnp.core.errors import EXIT_OK, EXIT_UNEXPECTED, classify
from nanopnp.core.paths import (
    CORRECTIONS_DIR,
    DATA_DIR,
    GEOMETRY_DIR,
    REFERENCE_DATA_VARIABLE,
    STORE_ROOT_VARIABLE,
    reference_data_root,
    store_root,
)
from nanopnp.core.public import __version__
from nanopnp.io.artefact import CASE_SCHEMA
from nanopnp.mesh.defaults import (
    DEFAULT_CYLINDER_MEMBRANE_THICKNESS_NM,
    DEFAULT_CYLINDER_RESERVOIR_RADIUS_NM,
    DEFAULT_CYLINDER_WALL_H_NM,
    DEFAULT_MAXH_NM,
    DEFAULT_PORE_RADIUS_NM,
)

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from collections.abc import Sequence

    import numpy as np

    from nanopnp.core.hashing import Canonicalisable
    from nanopnp.io.artefact import SweepArtefact
    from nanopnp.io.store import Store
    from nanopnp.sweep.plan import SweepPlan
    from nanopnp.validation.comsol import Golden
    from nanopnp.validation.probe import ProbeDocument, ProbeGrid
    from nanopnp.validation.runs import ReopenedRun

__all__ = ["main"]

logger = logging.getLogger(__name__)

_LEVELS = (logging.WARNING, logging.INFO, logging.DEBUG)


def _common(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    parser.add_argument(
        "--json",
        action="store_true",
        default=argparse.SUPPRESS,
        help="write the result to stdout as JSON",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=argparse.SUPPRESS,
        dest="subcommand_verbose",
        help="log at INFO; twice for DEBUG. Log records go to stderr",
    )
    parser.add_argument(
        "--log-file",
        type=Path,
        default=argparse.SUPPRESS,
        help="also write log records to this file",
    )
    parser.add_argument(
        "--traceback",
        action="store_true",
        default=argparse.SUPPRESS,
        help="print the traceback of a failure; suppressed by default, because a gate abort's "
        "diagnostic is the message (QR-12)",
    )
    return parser


def _configure_logging(verbose: int, log_file: Path | None) -> None:
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
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True, default=str))
        return
    for line in lines:
        print(line)


def _environment() -> dict[str, Canonicalisable]:
    reference = reference_data_root()
    return {
        "version": __version__,
        "python": platform.python_version(),
        "platform": platform.platform(),
        "data": str(DATA_DIR),
        "corrections": str(CORRECTIONS_DIR),
        "geometry": str(GEOMETRY_DIR),
        "store": str(Path(store_root()).resolve()),
        STORE_ROOT_VARIABLE: os.environ.get(STORE_ROOT_VARIABLE),
        "reference_data": str(reference) if reference is not None else None,
        REFERENCE_DATA_VARIABLE: os.environ.get(REFERENCE_DATA_VARIABLE),
    }


def _env(args: argparse.Namespace) -> int:
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
    from nanopnp.cli.reading import format_value, stage_line
    from nanopnp.io.store import Store
    from nanopnp.pipeline.run import run_case

    result = run_case(
        args.case,
        store=Store(args.store),
        upto=args.upto,
        write=False,
    )
    if args.run_dir is not None:
        # --run-dir moves the output files only, so it is applied after the walk, not fed into it.
        result = dataclasses.replace(result, directory=Path(args.run_dir))
    record = result.write()

    payload = dict(result.record())
    lines = [f"run      {result.directory}", f"record   {record}"]
    lines += [
        stage_line(entry.number, entry.name, entry.cached, entry.hash, entry.seconds)
        for entry in result.stages
    ]
    lines += [
        f"{name:<20} {format_value(value)}" for name, value in sorted(result.quantities.items())
    ]
    lines += [f"file     {path}" for path in result.files]
    _emit(payload, lines, as_json=args.json)
    return EXIT_OK


def _stage(args: argparse.Namespace) -> int:
    from nanopnp.core.stages import registered_stages

    if args.list:
        if args.export is not None:
            args.parser.error("--list writes no artefact; --export needs a stage and a case file")
        # Answered from the registry alone: no stage module, NGSolve or netgen is imported.
        descriptions = registered_stages()
        payload: dict[str, Canonicalisable] = {
            "stages": [description.summary() for description in descriptions]
        }
        lines = [
            f"{description.number:>2}  {description.name:<11} {description.title:<28} "
            f"{description.artefact_schema}"
            for description in descriptions
        ]
        _emit(payload, lines, as_json=args.json)
        return EXIT_OK

    if args.name is None or args.case is None:
        # A usage error (exit 2): nothing was run.
        args.parser.error("give a stage name and a case file, or --list")
    if args.export is not None:
        # Refused before the walk, which may take a minute.
        why = refusal(args.name, args.export)
        if why is not None:
            args.parser.error(why)

    from nanopnp.io.store import Store
    from nanopnp.pipeline.run import run_case

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
    if args.export is not None:
        # After the walk, from the store: the export path reaches no artefact key.
        written = export_artefact(args.name, artefact, args.export)
        found["export"] = [str(path) for path in written]
        lines += [f"export   {path}" for path in written]
    _emit(found, lines, as_json=args.json)
    return EXIT_OK


def _inspect(args: argparse.Namespace) -> int:
    from nanopnp.cli import reading
    from nanopnp.core.hashing import decode_floats
    from nanopnp.io.manifest import MANIFEST_FILENAME
    from nanopnp.io.manifest import read as read_manifest
    from nanopnp.pipeline.run import RUN_RECORD_FILENAME, read_run
    from nanopnp.sweep.collect import DATASET_FILENAME, read_dataset

    if args.other is not None:
        for given in (args.target, args.other):
            if not (Path(given) / RUN_RECORD_FILENAME).is_file():
                args.parser.error(
                    f"two targets are compared as runs, and {given} is not a run directory "
                    f"(it holds no {RUN_RECORD_FILENAME})"
                )
        if args.section is not None:
            args.parser.error("--section reads one run; give one target")
        payload, lines = reading.comparison(read_run(args.target), read_run(args.other))
        _emit(payload, lines, as_json=args.json)
        return EXIT_OK

    target = Path(args.target)
    if target.is_dir():
        for candidate in (MANIFEST_FILENAME, "meta.json", RUN_RECORD_FILENAME, DATASET_FILENAME):
            if (target / candidate).is_file():
                target = target / candidate
                break
        else:
            raise FileNotFoundError(
                f"{args.target} holds no {MANIFEST_FILENAME}, meta.json, {RUN_RECORD_FILENAME} or "
                f"{DATASET_FILENAME}; give a run directory, a stored artefact directory, a sweep "
                "directory, or one of those files"
            )
    is_run = target.name in (MANIFEST_FILENAME, RUN_RECORD_FILENAME) and (
        target.with_name(RUN_RECORD_FILENAME).is_file()
    )
    if args.section is not None:
        if not is_run:
            args.parser.error(f"--section reads a run directory's manifest; {target} is not one")
        if args.section not in reading.SECTIONS:
            args.parser.error(
                f"--section {args.section!r} names no manifest group; give one of "
                f"{', '.join(reading.SECTIONS)}"
            )
    # Undo canonical's {"__f__": hex} float wrapper so the printed and --json values are
    # plain numbers.
    if target.name == MANIFEST_FILENAME:
        raw: Canonicalisable = dict(read_manifest(target))
    else:
        raw = json.loads(target.read_text(encoding="utf-8"))
    # cast, not a check: both files are JSON objects by construction.
    document = cast("dict[str, Canonicalisable]", decode_floats(raw))

    if is_run:
        recorded = read_run(target.parent)
        if args.section is not None:
            group = recorded.manifest.document()[args.section]
            payload = cast("dict[str, Canonicalisable]", group)
            _emit(
                {args.section: payload},
                reading.section_lines(recorded, args.section),
                as_json=args.json,
            )
            return EXIT_OK
        lines = reading.run_lines(recorded)
    elif target.name == DATASET_FILENAME:
        lines = reading.dataset_lines(target, read_dataset(target.parent))
    elif target.name == "meta.json":
        lines = reading.artefact_lines(target, document)
    else:
        lines = [f"{target}"]
        lines += [
            f"{key:<20} {json.dumps(value, default=str)}" for key, value in sorted(document.items())
        ]
    _emit(document, lines, as_json=args.json)
    return EXIT_OK


def _reproduce(args: argparse.Namespace) -> int:
    from nanopnp.io.store import Store
    from nanopnp.pipeline.reproduce import reproduce

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
    from nanopnp.mesh.cylinder import generate_cylinder, write_gated_msh

    # Refused before the mesher runs: left to the write, a bad destination would exit 3 or 1
    # instead of 2.
    out = Path(args.out)
    if not out.name or out.is_dir():
        args.parser.error(f"--out {out} is a directory; name the .msh file to write")
    if not out.parent.is_dir():
        args.parser.error(f"--out {out}: the directory {out.parent} does not exist")

    if args.shape == "cylinder":
        if args.pore_radius_nm >= args.reservoir_radius_nm:
            args.parser.error(
                f"--pore-radius-nm {args.pore_radius_nm:g} must be smaller than "
                f"--reservoir-radius-nm {args.reservoir_radius_nm:g}"
            )
        generated = generate_cylinder(
            pore_radius_nm=args.pore_radius_nm,
            membrane_thickness_nm=args.membrane_thickness_nm,
            reservoir_radius_nm=args.reservoir_radius_nm,
            maxh_nm=args.maxh_nm,
            wall_h_nm=args.wall_h_nm,
        )
    else:
        from nanopnp.mesh.reference import ReferenceGeometry

        generated = ReferenceGeometry.from_fixture().generate(check_quality=False)
    mapped, quality, groups = write_gated_msh(generated, out)
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


def _positive_int(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{text!r} is not a valid integer") from None
    if value < 1:
        raise argparse.ArgumentTypeError(f"must be at least 1, found {value}")
    return value


def _positive_nm(text: str) -> float:
    try:
        value = float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{text!r} is not a valid number") from None
    if not 0.0 < value < float("inf"):
        raise argparse.ArgumentTypeError(f"{text!r} is not a positive length in nm")
    return value


def _sweep(args: argparse.Namespace) -> int:
    from nanopnp.io.store import Store
    from nanopnp.sweep.plan import plan_from_document, read_plan, write_plan

    store = Store(args.store)
    if args.action == "plan":
        plan = plan_from_document(args.document, check_meshes=not args.no_mesh_check)
        if args.directory is None:
            directory = store.sweep_directory(plan.name, plan.hash)
        else:
            # Where the plan and member records go; a directory holding a different
            # plan is refused, not overwritten.
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
        # Contiguous index range per wave: a job array is two shell lines over these
        # (CON-07 forbids a scheduler library).
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
    from nanopnp.sweep.plan import PLAN_FILENAME, SweepPlanError, read_plan

    existing = directory / PLAN_FILENAME
    if existing.is_file() and read_plan(existing).hash != digest:
        raise SweepPlanError(
            f"{directory} already holds the plan of a different sweep; its member records "
            "would be collected against points they were not solved for. Choose another "
            "--directory, or remove that one"
        )


def _sweep_run(args: argparse.Namespace, plan: SweepPlan, directory: Path, *, store: Store) -> int:
    from nanopnp.sweep.plan import SweepPlanError
    from nanopnp.sweep.run import run_plan, run_point

    if args.index is not None:
        member = run_point(plan, args.index, store=store, directory=directory)
        _emit(
            member.row(),
            [f"point {member.index} {member.point_id} {member.status}"],
            as_json=args.json,
        )
        # The member's own exit code, so a job array can branch per member.
        return member.exit_class

    indices: range | None = None
    if args.wave is not None:
        waves = plan.waves()
        # Named rather than IndexError; a negative index would silently select from the end.
        if not 0 <= args.wave < len(waves):
            raise SweepPlanError(
                f"this plan has {len(waves)} waves, 0 to {len(waves) - 1}; "
                f"there is no wave {args.wave}"
            )
        first, last = waves[args.wave]
        indices = range(first, last)
    # --workers overrides the plan's default and reaches no manifest.
    workers = args.workers if args.workers is not None else (plan.workers or 1)
    members = run_plan(
        plan,
        directory,
        store=store,
        workers=workers,
        indices=indices,
        fail_fast=args.fail_fast,
    )
    # Same files and route as a local run: see _sweep_dataset.
    artefact = _sweep_dataset(args, plan, directory)
    counts: dict[str, int] = {}
    for member in members:
        counts[member.status] = counts.get(member.status, 0) + 1
    lines = [f"dataset  {directory / 'dataset.json'}"]
    lines += [f"{status:<16} {count}" for status, count in sorted(counts.items())]
    _emit(dict(artefact.summary), lines, as_json=args.json)
    # Zero when every member reached a terminal state: non-convergence at a hard envelope's
    # corners is a result, not a failure (--fail-fast opts out).
    if args.fail_fast and any(member.status != "ok" for member in members):
        return next(member.exit_class for member in members if member.status != "ok")
    return EXIT_OK


def _sweep_collect(args: argparse.Namespace, plan: SweepPlan, directory: Path) -> int:
    artefact = _sweep_dataset(args, plan, directory)
    counts = artefact.summary.get("counts", {})
    lines = [f"dataset  {directory / 'dataset.json'}"]
    lines += [f"{status:<16} {count}" for status, count in sorted(dict(counts).items())]
    if args.csv:
        lines.append(f"csv      {directory / 'dataset.csv'}")
    _emit(dict(artefact.summary), lines, as_json=args.json)
    return EXIT_OK


def _sweep_dataset(args: argparse.Namespace, plan: SweepPlan, directory: Path) -> SweepArtefact:
    from nanopnp.sweep.collect import collect, write_csv

    artefact = collect(plan, directory)
    if getattr(args, "csv", False):
        write_csv(artefact, directory)
    return artefact


def _validate(args: argparse.Namespace) -> int:
    actions = {
        "case": _validate_case,
        "export-grid": _validate_export_grid,
        "case-hash": _validate_case_hash,
        "ingest-golden": _validate_ingest_golden,
        "export-golden": _validate_export_golden,
        "compare": _validate_compare,
        "report": _validate_report,
    }
    return actions[args.action](args)


def _validate_case(args: argparse.Namespace) -> int:
    from nanopnp.pipeline.case import load_case, resolve
    from nanopnp.pipeline.checks import check_referenced_files
    from nanopnp.pipeline.run import selected_stages

    document = load_case(args.case)
    if not getattr(args, "schema_only", False):
        check_referenced_files(document)
    resolved = resolve(document)
    stages = selected_stages(resolved, None)
    payload: dict[str, Canonicalisable] = {
        "case": document.name,
        "valid": True,
        "model": resolved.model,
        "stabilisation": resolved.stabilisation,
        "stages": list(stages),
    }
    lines = [
        f"case          {document.name}: valid",
        f"model         {resolved.model}",
        f"stabilisation {resolved.stabilisation}",
        f"stages        {' '.join(stages)}",
    ]
    _emit(payload, lines, as_json=args.json)
    return EXIT_OK


def _validate_export_grid(args: argparse.Namespace) -> int:
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
    from nanopnp.pipeline.case import load_case, resolve
    from nanopnp.validation.comsol import case_identity

    document = load_case(args.case)
    identity = case_identity(resolve(document))
    payload: dict[str, Canonicalisable] = {"case": document.name, "case_hash": identity}
    _emit(payload, [f"case      {document.name}", f"case_hash {identity}"], as_json=args.json)
    return EXIT_OK


def _validate_ingest_golden(args: argparse.Namespace) -> int:
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
    from nanopnp.validation.comsol import (
        GOLDEN_SCHEMA,
        GoldenManifest,
        export_golden,
    )

    document, sampled, resolved = _sampled_run(args)
    manifest = GoldenManifest.model_validate(
        {
            "schema": GOLDEN_SCHEMA,
            "case": resolved.case.name,
            "case_hash": _identity(resolved),
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
    from nanopnp.validation.compare import (
        compare_fields,
        compare_quantities,
        unavailable_quantities,
        zero_reference_quantities,
    )
    from nanopnp.validation.comsol import load_golden

    document, sampled, resolved = _sampled_run(args)
    golden = load_golden(args.golden)
    golden.check_case(_identity(resolved))
    golden.check_probe(document)
    grid = _probe_grid(document, resolved)
    fields = compare_fields(sampled, golden, grid)
    quantities = compare_quantities(resolved.quantities, golden.quantities)
    zero_reference = zero_reference_quantities(resolved.quantities, golden.quantities)
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
        "zero_reference_quantities": zero_reference,
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
    lines += [
        f"{name:<12} golden is zero; relative error undefined (ours {value:.4e})"
        for name, value in zero_reference.items()
    ]
    _emit(payload, lines, as_json=args.json)
    return EXIT_OK


def _validate_report(args: argparse.Namespace) -> int:
    from nanopnp.sweep.collect import read_members
    from nanopnp.sweep.plan import read_plan
    from nanopnp.validation.attribution import (
        LADDER,
        LadderError,
        RungOutcome,
        attribute,
        write_report,
    )
    from nanopnp.validation.compare import (
        compare_fields,
        compare_quantities,
        zero_reference_quantities,
    )
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
    # Every rung is the golden's case on one mesh, so any rung's grid carries the masks the
    # norms were taken over.
    rung_grid: ProbeGrid | None = None
    for member in read_members(directory):
        plan.point(member.index)  # refuses a member this plan does not enumerate
        rung_index = _rung_of(member.assignments)
        if member.status != "ok" or member.directory is None:
            continue
        if rung_index is None or rung_index in by_rung:
            continue
        resolved = reopen(member.directory, store=store)
        if _identity(resolved) != golden.manifest.case_hash:
            continue
        grid = rung_grid = _probe_grid(document, resolved)
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
            zero_reference=zero_reference_quantities(resolved.quantities, golden.quantities),
        )
    missing = [rung.name for rung in LADDER if rung.index not in by_rung]
    if missing:
        raise LadderError(
            f"{directory} holds no completed member for rung(s) {', '.join(missing)} of the "
            "golden's case. The ladder attributes a discrepancy by differences between adjacent "
            "rungs, so a missing one does not make the remaining deltas mean less -- it makes "
            "them mean something else. Run the sweep to completion first"
        )
    assert rung_grid is not None  # four rungs were found, and each built its grid
    report = attribute(
        [by_rung[index] for index in range(len(LADDER))],
        case=golden.manifest.case,
        golden=golden,
        reference_errors=_reference_errors(args, document, golden, rung_grid),
        sampled_fields=fields_sampled,
    )
    json_path, markdown = write_report(report, args.output or directory)
    payload = dict(report.summary())
    payload["files"] = [str(json_path), str(markdown)]
    _emit(payload, [report.markdown()], as_json=args.json)
    return EXIT_OK


def _rung_of(assignments: Mapping[str, Canonicalisable]) -> int | None:
    from nanopnp.validation.attribution import LADDER

    for rung in LADDER:
        if all(assignments.get(path) == value for path, value in rung.assignments().items()):
            return rung.index
    return None


def _reference_errors(
    args: argparse.Namespace, document: ProbeDocument, golden: Golden, grid: ProbeGrid
) -> dict[str, float] | None:
    from nanopnp.validation.attribution import reference_error
    from nanopnp.validation.comsol import load_golden

    if args.refined is None:
        return None
    refined = load_golden(args.refined)
    refined.check_probe(document)
    return reference_error(golden, refined, grid)


def _store(args: argparse.Namespace) -> Store:
    from nanopnp.io.store import Store

    return Store(args.store)


def _identity(run: ReopenedRun) -> str:
    from nanopnp.validation.comsol import case_identity

    return case_identity(run.resolved, recorded=run.upstream)


def _unit(field: str) -> str:
    from nanopnp.validation.comsol import field_unit

    return field_unit(field)


def _self_quantities(recorded: Mapping[str, Canonicalisable]) -> dict[str, Canonicalisable]:
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
    value = recorded.get("stabilisation_currents_A")
    return dict(value) if isinstance(value, dict) else None


def _probe_grid(document: ProbeDocument, resolved: ReopenedRun) -> ProbeGrid:
    from nanopnp.validation.compare import probe_domains
    from nanopnp.validation.probe import ProbeGrid

    return ProbeGrid.on_mesh(
        document, resolved.solution.space.mesh, probe_domains(resolved.solution)
    )


def _sample(resolved: ReopenedRun, grid: ProbeGrid) -> dict[str, np.ndarray]:
    from nanopnp.validation.compare import sample_on_probe

    return sample_on_probe(resolved.solution, grid, scales=resolved.scales)


def _sampled_run(
    args: argparse.Namespace,
) -> tuple[ProbeDocument, dict[str, np.ndarray], ReopenedRun]:
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
    parser.add_argument(
        "--json", action="store_true", default=False, help="write the result to stdout as JSON"
    )
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
        default=False,
        help="print the traceback of a failure; suppressed by default, because a gate abort's "
        "diagnostic is the message (QR-12)",
    )
    subparsers = parser.add_subparsers(dest="command")

    run = _common(subparsers.add_parser("run", help="run a case file through the pipeline"))
    run.add_argument("case", type=Path, help=f"the case file (schema: {CASE_SCHEMA})")
    run.add_argument("--store", type=Path, default=None, help="artefact store root")
    run.add_argument("--run-dir", type=Path, default=None, help="where the run directory goes")
    run.add_argument("--upto", default=None, help="stop after this stage")
    run.add_argument(
        "--threads",
        type=_positive_int,
        default=None,
        help="worker thread count for OpenMP and linear algebra",
    )
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
    stage.add_argument(
        "--export",
        type=Path,
        default=None,
        metavar="PATH",
        help="also write the stage's artefact here, in the format its suffix names: "
        + "; ".join(f"{name} {', '.join(suffixes)}" for name, suffixes in EXPORTS.items())
        + ". Lengths in the .pdb, .dcd, .dx, .ccp4, .mrc and .map files are in angstroms",
    )
    stage.set_defaults(handler=_stage, parser=stage)

    inspect = _common(subparsers.add_parser("inspect", help="read an artefact or run back"))
    inspect.add_argument(
        "target",
        type=Path,
        help="a run directory, a sweep directory, a stored artefact directory, or a record",
    )
    inspect.add_argument(
        "other",
        type=Path,
        nargs="?",
        default=None,
        help="a second run directory, compared with the first",
    )
    inspect.add_argument(
        "--section",
        default=None,
        metavar="GROUP",
        help="print one group of a run's manifest (inputs, solver, deviations, ...) or its case",
    )
    inspect.set_defaults(handler=_inspect, parser=inspect)

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

    # Defaults: the coarsest mesh the NUM-34 gate admits with wall corrections on (392 elements).
    cylinder = _common(
        shapes.add_parser("cylinder", help="an idealised cylindrical pore through a membrane")
    )
    cylinder.add_argument(
        "--pore-radius-nm",
        type=_positive_nm,
        default=DEFAULT_PORE_RADIUS_NM,
        help=f"lumen radius (default {DEFAULT_PORE_RADIUS_NM:g})",
    )
    cylinder.add_argument(
        "--membrane-thickness-nm",
        type=_positive_nm,
        default=DEFAULT_CYLINDER_MEMBRANE_THICKNESS_NM,
        help=(
            "membrane thickness, the lumen's length "
            f"(default {DEFAULT_CYLINDER_MEMBRANE_THICKNESS_NM:g})"
        ),
    )
    cylinder.add_argument(
        "--reservoir-radius-nm",
        type=_positive_nm,
        default=DEFAULT_CYLINDER_RESERVOIR_RADIUS_NM,
        help=(
            "radius of each quarter-disc reservoir "
            f"(default {DEFAULT_CYLINDER_RESERVOIR_RADIUS_NM:g})"
        ),
    )
    cylinder.add_argument(
        "--maxh-nm",
        type=_positive_nm,
        default=DEFAULT_MAXH_NM,
        help=f"global maximum element size (default {DEFAULT_MAXH_NM:g})",
    )
    cylinder.add_argument(
        "--wall-h-nm",
        type=_positive_nm,
        default=DEFAULT_CYLINDER_WALL_H_NM,
        help=f"element size on the pore wall (default {DEFAULT_CYLINDER_WALL_H_NM:g})",
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
    planner.add_argument("document", type=Path, help="the sweep file (schema: nanopnp/sweep/v0.5)")
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
    target = runner.add_mutually_exclusive_group()
    target.add_argument(
        "--index", type=int, default=None, help="run one member; exits with that member's own code"
    )
    target.add_argument("--wave", type=int, default=None, help="run one wave of the forest")
    runner.add_argument(
        "--workers",
        type=_positive_int,
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
        "validate", help="check a case file; the Tier-3 COMSOL comparison harness (section 7.4)"
    )
    steps = validate.add_subparsers(dest="action", required=True)

    checked = _common(
        steps.add_parser("case", help="check a case file as a run would, without solving it")
    )
    checked.add_argument("case", type=Path, help="the case file")
    checked.add_argument(
        "--schema-only",
        action="store_true",
        help="validate case document schema and resolution semantics only without "
        "checking disk files",
    )
    checked.set_defaults(handler=_validate)

    # %% throughout the help strings: argparse percent-formats help text, and a bare %G raises.
    grid = _common(steps.add_parser("export-grid", help="print the %%Grid axes COMSOL is given"))
    grid.add_argument("probe", type=Path, help="the nanopnp/probe/v0.5 document")
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
    # Required, not defaulted: a blank export_date is refused by the manifest and would exit
    # 1; argparse's exit 2 is right.
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
    """Run the ``nanopnp`` command-line interface and return its process exit status."""
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        if getattr(args, "env_flag", False):
            return _env(argparse.Namespace(json=getattr(args, "json", False)))
        parser.print_help()
        return EXIT_OK

    # Separate destinations before and after the subcommand: a shared one would collapse
    # `-vv run -v` to one level.
    _configure_logging(args.verbose + getattr(args, "subcommand_verbose", 0), args.log_file)
    if args.command == "reproduce" and args.tolerance is None:
        from nanopnp.pipeline.reproduce import DEFAULT_TOLERANCE

        args.tolerance = DEFAULT_TOLERANCE

    threads = getattr(args, "threads", None)
    if threads is not None:
        from nanopnp.sweep.run import THREAD_VARIABLES

        for var in THREAD_VARIABLES:
            os.environ[var] = str(threads)

    handler = args.handler
    try:
        code: int = handler(args)
    except SystemExit:
        raise
    except BaseException as error:
        code = classify(error)
        if args.traceback:
            traceback.print_exc(file=sys.stderr)
        else:
            print(f"nanopnp {args.command}: {error}", file=sys.stderr)
            if code == EXIT_UNEXPECTED:
                print(
                    f"nanopnp {args.command}: unexpected {type(error).__name__}; "
                    "re-run with --traceback",
                    file=sys.stderr,
                )
        return code
    return code


if __name__ == "__main__":  # pragma: no cover - run as a script, never imported by a test
    sys.exit(main())

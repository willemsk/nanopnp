"""The run, stage, inspect, plot and reproduce commands."""

from __future__ import annotations

import argparse
import dataclasses
import importlib.util
import json
import os
from pathlib import Path
from typing import TYPE_CHECKING, cast

from nanopnp.cli.common import _common, _emit, _positive_int, _progress, _progress_flag
from nanopnp.cli.export import EXPORTS, export_artefact, refusal
from nanopnp.core.errors import EXIT_OK, EXIT_USAGE
from nanopnp.io.artefact import CASE_SCHEMA

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.cli.common import Subparsers
    from nanopnp.core.hashing import Canonicalisable


def _run(args: argparse.Namespace) -> int:
    from nanopnp.api.case import Case
    from nanopnp.api.session import Session
    from nanopnp.cli.reading import format_value, stage_line
    from nanopnp.io.store import Store

    progress = _progress(args)
    try:
        result = Session(Store(args.store), write=False).run(
            Case.load(args.case), upto=args.upto, on_stage=progress, on_solve=progress
        )
    finally:
        if progress is not None:
            progress.close()
    if args.run_dir is not None:
        # --run-dir moves the output files only, so it is applied after the walk, not fed into it.
        result = dataclasses.replace(result, directory=Path(args.run_dir))
    record = result.write()

    payload = dict(result.record())
    lines = [f"run      {result.directory}", f"record   {record}"]
    lines += [stage_line(entry) for entry in result.stages]
    lines += [
        f"{name:<20} {format_value(value)}" for name, value in sorted(result.quantities.items())
    ]
    lines += [f"file     {path}" for path in result.files]
    _emit(payload, lines, as_json=args.json)
    return EXIT_OK


def _stage(args: argparse.Namespace) -> int:
    from nanopnp.api.session import Session
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

    from nanopnp.api.case import Case
    from nanopnp.io.store import Store

    progress = _progress(args)
    try:
        result = Session(Store(args.store), write=False).run(
            Case.load(args.case),
            upto=args.name,
            only=args.only,
            on_stage=progress,
            on_solve=progress,
        )
    finally:
        if progress is not None:
            progress.close()
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


def _inspect(args: argparse.Namespace) -> int:  # noqa: C901
    from nanopnp.api.session import Session
    from nanopnp.cli import reading
    from nanopnp.core.hashing import decode_floats
    from nanopnp.io.artefact import SWEEP_SCHEMA
    from nanopnp.io.manifest import (
        MANIFEST_FILENAME,
        MANIFEST_SCHEMA,
        RUN_RECORD_FILENAME,
        RUN_SCHEMA,
    )
    from nanopnp.io.manifest import read as read_manifest
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
        payload, lines = reading.comparison(Session.read(args.target), Session.read(args.other))
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
    if args.section is not None and args.section not in reading.SECTIONS:
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
    # A record of another schema, such as an older build's, is listed key by key (IF-02).
    expected = {
        MANIFEST_FILENAME: MANIFEST_SCHEMA,
        RUN_RECORD_FILENAME: RUN_SCHEMA,
        DATASET_FILENAME: SWEEP_SCHEMA,
    }.get(target.name)
    readable = expected is not None and document.get("schema") == expected
    is_run = (
        readable
        and target.name in (MANIFEST_FILENAME, RUN_RECORD_FILENAME)
        and target.with_name(RUN_RECORD_FILENAME).is_file()
    )
    if args.section is not None and not is_run:
        args.parser.error(
            f"--section reads a run directory's manifest of this build; {target} is not one"
        )
    if args.json and args.section is None:
        # The record as written, whatever its reading would make of it (IF-02).
        _emit(document, [], as_json=True)
        return EXIT_OK

    if is_run:
        recorded = Session.read(
            target.parent,
            manifest=document if target.name == MANIFEST_FILENAME else None,
            record=document if target.name == RUN_RECORD_FILENAME else None,
        )
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
    elif readable and target.name == DATASET_FILENAME:
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


_FIGURE_SUFFIXES: tuple[str, ...] = (".png", ".svg", ".pdf")


def _plot_refusal(stage: str) -> str | None:
    from nanopnp.core.stages import FIGURE_FREE, describe, figure_target

    try:
        schema = describe(stage).artefact_schema
    except KeyError as error:
        return str(error.args[0])
    if stage in FIGURE_FREE or figure_target(schema) is None:
        return f"stage {stage!r} declares no figure; it writes {schema}, which is not drawn"
    return None


def _is_region_file(path: Path) -> bool:
    from nanopnp.io.artefact import REGION_SCHEMA

    with path.open("rb") as handle:
        head = handle.read(4096).decode("utf-8", errors="replace")
    return any(line.strip() == f"schema: {REGION_SCHEMA}" for line in head.splitlines())


def _plot(args: argparse.Namespace) -> int:  # noqa: C901
    from nanopnp.core.stages import MissingExtraError
    from nanopnp.io.manifest import MANIFEST_FILENAME, RUN_RECORD_FILENAME
    from nanopnp.sweep.collect import DATASET_FILENAME

    out = Path(args.out)
    if out.suffix.lower() not in _FIGURE_SUFFIXES:
        args.parser.error(
            f"--out {out} has suffix {out.suffix or 'none'!r}; a figure is written as "
            f"{', '.join(_FIGURE_SUFFIXES)}"
        )
    if importlib.util.find_spec("matplotlib") is None:
        # Refused here, not by draw(): a case is drawn after its walk, which may be a long solve.
        raise MissingExtraError(
            "nanopnp plot needs the 'plot' extra: 'matplotlib' is not installed. Install the "
            "extras with `uv sync --all-extras`",
            name="matplotlib",
        )
    target = Path(args.target)
    if target.name in (DATASET_FILENAME, RUN_RECORD_FILENAME, MANIFEST_FILENAME):
        target = target.parent
    if (target / DATASET_FILENAME).is_file():
        kind = "sweep"
        if args.stage is not None:
            args.parser.error(f"{target} is a sweep, drawn as one figure; give no STAGE")
    elif (target / RUN_RECORD_FILENAME).is_file():
        kind = "run"
    elif target.is_file() and _is_region_file(target):
        kind = "region"
        if args.stage is not None:
            args.parser.error(f"{target} is a region file, drawn as one figure; give no STAGE")
    elif target.is_file():
        kind = "case"
        if args.stage is None:
            args.parser.error(f"{target} is a case file; name the STAGE whose figure to draw")
    else:
        args.parser.error(f"{target} is neither a case file, a run directory nor a sweep directory")
    stage = args.stage if args.stage is not None else "solve"
    if kind not in ("sweep", "region"):
        why = _plot_refusal(stage)
        if why is not None:
            args.parser.error(why)

    from nanopnp.core.stages import draw
    from nanopnp.io.store import Store, StoreError

    store = Store(args.store) if args.store is not None else None
    if kind == "sweep":
        from nanopnp.sweep.collect import read_dataset

        figure = draw(read_dataset(target))
    elif kind == "region":
        from nanopnp.io.artefact import RegionArtefact

        figure = draw(RegionArtefact(parameters={}, inputs={}, payload={"region": target}))
        stage = "region"
    elif kind == "run":
        from nanopnp.api.session import Session

        result = Session(store, write=False).open(target)
        if stage not in result.artefacts:
            if stage not in {record.name for record in result.stages}:
                args.parser.error(
                    f"the run in {target} did not walk stage {stage!r}; it walked "
                    f"{', '.join(record.name for record in result.stages)}"
                )
            where = result.store.root if result.store is not None else None
            raise StoreError(
                f"the store at {where} no longer holds the {stage!r} artefact of the run in "
                f"{target}; point --store at the store the run used, or run it again"
            )
        figure = result.figure(stage)
    else:
        from nanopnp.api.case import Case
        from nanopnp.api.session import Session

        figure = (
            Session(Store(args.store), write=False).run(Case.load(target), upto=stage).figure(stage)
        )
    if figure is None:
        args.parser.error(f"stage {stage!r} declares no figure")
        return EXIT_USAGE

    out.parent.mkdir(parents=True, exist_ok=True)
    # Not mkstemp: its file is private (0600), and a figure takes the user's umask.
    staged = out.with_name(f".{out.stem}.{os.getpid()}{out.suffix}")
    try:
        figure.savefig(staged)
        staged.replace(out)
    finally:
        staged.unlink(missing_ok=True)
    payload: dict[str, Canonicalisable] = {
        "target": str(target),
        "stage": None if kind == "sweep" else stage,
        "figure": str(out),
    }
    _emit(payload, [f"figure   {out}"], as_json=args.json)
    return EXIT_OK


def _reproduce(args: argparse.Namespace) -> int:
    from nanopnp.api.reproduce import reproduce
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


def _register_run(subparsers: Subparsers) -> None:
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
    _progress_flag(run)
    run.set_defaults(handler=_run)


def _register_stage(subparsers: Subparsers) -> None:
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
    _progress_flag(stage)
    stage.set_defaults(handler=_stage, parser=stage)


def _register_inspect(subparsers: Subparsers) -> None:
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


def _register_plot(subparsers: Subparsers) -> None:
    plot = _common(
        subparsers.add_parser(
            "plot",
            help="draw a stage's figure to a file",
            description="Draw the figure of a stage of a case file, of a completed run, or of a "
            "sweep's collected dataset, to a PNG, SVG or PDF file. Needs the 'plot' extra.",
        )
    )
    plot.add_argument(
        "target", type=Path, help="a case file, a run directory, or a sweep directory"
    )
    plot.add_argument(
        "stage",
        nargs="?",
        default=None,
        help="the stage whose figure to draw: required for a case file, 'solve' for a run by "
        "default, none for a sweep",
    )
    plot.add_argument(
        "--out",
        type=Path,
        required=True,
        metavar="PATH",
        help=f"the figure file; its suffix names the format: {', '.join(_FIGURE_SUFFIXES)}",
    )
    plot.add_argument(
        "--store",
        type=Path,
        default=None,
        help="artefact store root; for a run, overrides the one its record names",
    )
    plot.set_defaults(handler=_plot, parser=plot)


def _register_reproduce(subparsers: Subparsers) -> None:
    check = _common(
        subparsers.add_parser(
            "reproduce",
            help="re-run an archived run (QR-08)",
            description="Re-run an archived run in a fresh store and compare its quantities with "
            "the recorded ones. A run fails to reproduce when an input file changed, when the "
            "libraries or the platform moved the numbers past the tolerance, or when the store "
            "served a stale artefact; it solves in a fresh store (a scratch one unless --store "
            "names a store that does not hold the run), so no recorded artefact is reused.",
        )
    )
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


def register(subparsers: Subparsers) -> None:
    """Add the run, stage, inspect, plot and reproduce subcommands."""
    _register_run(subparsers)
    _register_stage(subparsers)
    _register_inspect(subparsers)
    _register_plot(subparsers)
    _register_reproduce(subparsers)

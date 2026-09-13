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
    from collections.abc import Sequence

    from nanopnp.core.hashing import Canonicalisable
    from nanopnp.io.artefact import SweepArtefact
    from nanopnp.io.store import Store
    from nanopnp.sweep.plan import SweepPlan

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
        directory = store.sweep_directory(plan.name, plan.hash)
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

"""The sweep command: plan, run and collect."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.cli.common import _common, _emit, _positive_int
from nanopnp.core.errors import EXIT_OK

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.cli.common import Subparsers
    from nanopnp.core.hashing import Canonicalisable
    from nanopnp.io.artefact import SweepArtefact
    from nanopnp.io.store import Store
    from nanopnp.sweep.forecast import Forecast
    from nanopnp.sweep.plan import SweepPlan


def _sweep(args: argparse.Namespace) -> int:
    from nanopnp.io.store import Store
    from nanopnp.sweep.forecast import forecast
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
        # The forecast is advisory: a failure to key the points must not fail the plan.
        rebuilds: Forecast | None
        unavailable: str | None = None
        try:
            rebuilds = forecast(plan, store=store)
        except Exception as error:
            rebuilds = None
            unavailable = str(error)
            rebuild_lines = [f"forecast  unavailable: {error}"]
        else:
            rebuild_lines = [f"forecast  {line}" for line in rebuilds.warnings()]
        payload: dict[str, Canonicalisable] = {
            "plan": str(path),
            "directory": str(directory),
            "hash": plan.hash,
            "points": len(plan.points),
            "waves": [list(span) for span in plan.waves()],
            "warnings": list(plan.warnings),
            "forecast": None if rebuilds is None else rebuilds.summary(),
            "forecast_unavailable": unavailable,
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
        lines += rebuild_lines
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
    from nanopnp.api.session import Session
    from nanopnp.api.sweep import run_plan, run_point
    from nanopnp.sweep.plan import SweepPlanError

    if args.index is not None:
        member = run_point(plan, args.index, session=Session(store), directory=directory)
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
        session=Session(store),
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


def register(subparsers: Subparsers) -> None:
    """Add the sweep subcommand with its plan, run and collect actions."""
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

    runner = _common(
        actions.add_parser(
            "run",
            help="dispatch a plan's members",
            description="Run the members of a sweep plan. With --workers above 1, each worker is "
            "pinned to one thread (sweep/run.py pin_threads sets OMP_NUM_THREADS, "
            "OPENBLAS_NUM_THREADS and MKL_NUM_THREADS to 1 in each worker), so --workers sets "
            "how many cores are used.",
        )
    )
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

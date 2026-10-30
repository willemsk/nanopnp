"""A one-axis sweep of a case held in Python, and the executor that runs a planned sweep."""

from __future__ import annotations

import logging
import multiprocessing
import tempfile
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, replace
from pathlib import Path

import yaml

from nanopnp.api.case import Case
from nanopnp.api.session import Session
from nanopnp.core.errors import classify
from nanopnp.core.hashing import Canonicalisable
from nanopnp.io.artefact import SOLUTION_SCHEMA, SWEEP_SCHEMA, Artefact, StageInputs, SweepArtefact
from nanopnp.io.case import CaseDocument, FieldValue, dumps_case
from nanopnp.io.case_paths import correction_paths, field_path, input_paths
from nanopnp.io.store import Store, atomic_write_bytes
from nanopnp.pipeline.case import resolve
from nanopnp.pipeline.run import MissingUpstreamError, stored_upstream
from nanopnp.sweep.collect import collect
from nanopnp.sweep.document import loads_sweep
from nanopnp.sweep.plan import (
    PLAN_FILENAME,
    Point,
    SweepPlan,
    SweepPlanError,
    build_plan,
    read_plan,
    write_plan,
)
from nanopnp.sweep.run import MEMBERS_DIRNAME, MemberResult, member_from_row, pin_threads

logger = logging.getLogger(__name__)

__all__ = [
    "BASE_FILENAME",
    "SWEEP_FILENAME",
    "Sweep",
    "SweepResult",
    "plan_sweep",
    "run_plan",
    "run_point",
    "sweep",
]

BASE_FILENAME = "base.case.yaml"

SWEEP_FILENAME = "sweep.yaml"


@dataclass(frozen=True)
class SweepResult:
    """A collected sweep: the dataset over its members, the plan and the directory of its files."""

    dataset: SweepArtefact
    plan: SweepPlan
    directory: Path

    @property
    def rows(self) -> list[Mapping[str, Canonicalisable]]:
        """The dataset's rows, one per point, in plan order."""
        rows = self.dataset.summary.get("rows")
        return list(rows) if isinstance(rows, list) else []


@dataclass(frozen=True)
class Sweep:
    """A planned sweep, its files in one directory of the store."""

    plan: SweepPlan
    directory: Path
    session: Session

    def run(self, *, workers: int = 1) -> SweepResult:
        """Run every point, warm-starting each from its parent, and collect the dataset."""
        write_plan(self.plan, self.directory)
        run_plan(self.plan, self.directory, session=self.session, workers=workers)
        return SweepResult(collect(self.plan, self.directory), self.plan, self.directory)


def _plain(value: FieldValue) -> FieldValue:
    # An element of an ndarray is a numpy scalar, and a row of a 2-D one an array: neither can be
    # written by YAML or the content hash, and ``tolist`` turns both into plain Python.
    tolist = getattr(value, "tolist", None)
    return tolist() if callable(tolist) else value


def sweep(
    case: Case,
    *,
    session: Session,
    axis: str,
    values: Sequence[FieldValue],
    origin: int = 0,
    workers: int = 1,
    check_meshes: bool = True,
) -> SweepResult:
    """Plan, run and collect a sweep of ``case`` over one field; see :func:`plan_sweep`.

    Parameters
    ----------
    workers
        Processes the points of a wave are spread over; 1 runs them in this one.
    """
    planned = plan_sweep(
        case,
        session=session,
        axis=axis,
        values=values,
        origin=origin,
        check_meshes=check_meshes,
    )
    return planned.run(workers=workers)


def plan_sweep(
    case: Case,
    *,
    session: Session,
    axis: str,
    values: Sequence[FieldValue],
    origin: int = 0,
    check_meshes: bool = True,
) -> Sweep:
    """Plan a sweep of ``case`` over one field, as a sweep file over the same base would.

    Parameters
    ----------
    session
        Whose store the sweep's files and members are written into.
    axis
        The field swept: a dotted case path, or the leaf name one field ends in.
    origin
        Index into ``values`` of the point every other point warm-starts towards.
    check_meshes
        Whether to run the mesh gate once per distinct mesh with a wall correction.

    Raises
    ------
    SweepPlanError
        The case names an input file by a relative path, which the store's copy of the case
        would read against another directory.
    """
    # A file case reads its relative paths beside it; the store's copy would not.
    case = case.with_()
    relative = [
        f"{dotted} = {value}"
        for dotted, value in {**input_paths(case), **correction_paths(case)}.items()
        if not Path(value).is_absolute()
    ]
    if relative:
        raise SweepPlanError(
            f"case {case.name!r} names {', '.join(relative)} by a relative path; its "
            "copy in the store would read it against another directory. Load the case from a "
            "file, or name the input by an absolute path"
        )
    dotted = field_path(axis)
    name = case.name
    document = {
        "schema": SWEEP_SCHEMA,
        "name": name,
        "base": BASE_FILENAME,
        "axes": [
            {
                "name": dotted.rsplit(".", 1)[-1],
                "path": dotted,
                "values": [_plain(value) for value in values],
                "origin": origin,
            }
        ],
    }
    store = session.store
    text = yaml.safe_dump(document, sort_keys=False)
    base_text = case.dumps().encode("utf-8")
    # The directory is named by the plan's hash, as the sweep command names it, so the plan is
    # first built beside its files in a staging directory to read that hash. The hash does not
    # depend on where the base case lies, so the plan is built once and moved.
    sweeps = store.root / "sweeps"
    sweeps.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=sweeps, prefix=".staging-") as scratch:
        staging = Path(scratch)
        atomic_write_bytes(staging / BASE_FILENAME, base_text)
        atomic_write_bytes(staging / SWEEP_FILENAME, text.encode("utf-8"))
        staged = build_plan(
            loads_sweep(text, source=str(staging / SWEEP_FILENAME)),
            source=staging / SWEEP_FILENAME,
            check_meshes=check_meshes,
        )
    directory = store.sweep_directory(name, staged.hash)
    directory.mkdir(parents=True, exist_ok=True)
    atomic_write_bytes(directory / BASE_FILENAME, base_text)
    atomic_write_bytes(directory / SWEEP_FILENAME, text.encode("utf-8"))
    plan = replace(staged, base_path=(directory / BASE_FILENAME).resolve())
    return Sweep(plan, directory, session)


def _parent_artefact(
    plan: SweepPlan, point: Point, session: Session, *, base: CaseDocument
) -> tuple[Artefact | None, str]:
    if point.parent is None:
        return None, "this point is the root of its tree and has no neighbour to start from"
    from nanopnp.solve.stage import SolveStage

    parent = plan.point(point.parent)
    document = plan.case(point.parent, base=base)
    try:
        # Keyed on the artefacts the parent's own walk handed its solve, not on
        # the bare case: a generated mesh exists only as stage 6's stored
        # artefact, and a bare-case key raised for every such sweep, which
        # silently made every member cold.
        upstream = stored_upstream(document, store=session.store)
    except MissingUpstreamError as error:
        # The parent has not run, which is a fallback rather than a failure. Any
        # other error is a defect and is left to raise.
        return None, (
            f"the store holds no converged state for parent point {parent.index} "
            f"({parent.point_id}); not even its upstream artefacts are stored: {error}"
        )
    key = SolveStage().key(StageInputs(resolved=resolve(document), upstream=upstream))
    found = session.store.get(SOLUTION_SCHEMA, key.hash)
    if found is None:
        return None, (
            f"the store holds no converged state for parent point {parent.index} "
            f"({parent.point_id}); its artefact would be {key.short_hash}"
        )
    return found, ""


def run_point(
    plan: SweepPlan,
    index: int,
    *,
    session: Session,
    directory: Path,
) -> MemberResult:
    """Run one member through ``session`` and return its record, capturing whatever it raised.

    A member always writes its run directory, and takes no workspace of the session's.

    Parameters
    ----------
    index
        Which point to run.
    """
    from nanopnp.core.stages import Cancelled

    point = plan.point(index)
    started = time.perf_counter()
    base = plan.base_case()
    try:
        warm, reason = _parent_artefact(plan, point, session, base=base)
    except Exception as error:
        # The parent's case resolves as this member's does, so an error keying
        # it is this member's to report, classified, rather than one that ends
        # the whole sweep.
        return _failed(point, error, started, directory)
    document = plan.case(index, base=base)
    # The *member's* case, not the base case it was substituted from. The
    # manifest embeds this text beside the member's own case hash and writes it
    # back out as the run directory's ``case.yaml``, which is the file QR-08's
    # reproduction re-runs (§5.3.3): the base case there would reproduce the
    # origin of every axis and report it under this member's identity. And
    # ``case_path`` stays ``None`` for the same reason — a member is a case
    # assembled in memory, and recording the base case as its source file would
    # make the manifest name a file whose contents are not the case that ran.
    case_text = dumps_case(document)
    logger.info(
        "point %d/%d (%s, wave %d) %s",
        index,
        len(plan.points),
        point.point_id,
        point.wave,
        "warm from " + warm.short_hash if warm is not None else "cold",
    )
    try:
        result = Session(session.store)._walk(
            document,
            case_text=case_text,
            arguments={"solve": {"warm_start": warm, "cold_reason": reason}},
        )
    except Cancelled as error:
        return _failed(point, error, started, directory, cancelled=True)
    except Exception as error:
        return _failed(point, error, started, directory)

    solve = result.artefacts.get("solve")
    solved = dict(solve.summary) if solve is not None else {}
    qoi = result.artefacts.get("qoi")
    # ``all([])`` is True, so the empty case is spelt out: a run that never
    # reached the solve did not have one served from the cache, and a row saying
    # it did would subtract that member from the QR-06 throughput figure.
    solves = [record for record in result.stages if record.name == "solve"]
    cached = bool(solves) and all(record.cached for record in solves)
    member = MemberResult(
        index=index,
        point_id=point.point_id,
        assignments=dict(point.assignments),
        wave=point.wave,
        status="ok",
        quantities=dict(result.quantities),
        directory=str(result.directory),
        manifest=result.manifest.hash,
        solution=solve.hash if solve is not None else None,
        seconds=time.perf_counter() - started,
        iterations=_count(solved.get("iterations")),
        cached=cached,
        warm_start=_mapping(solved.get("warm_start")),
        wall_distance=_mapping(solved.get("wall_distance")),
        route_agreement=_route_agreement(qoi),
    )
    member.write(directory / MEMBERS_DIRNAME)
    return member


def _mapping(value: Canonicalisable) -> dict[str, Canonicalisable] | None:
    return dict(value) if isinstance(value, Mapping) else None


def _count(value: Canonicalisable) -> int | None:
    return int(value) if isinstance(value, int) and not isinstance(value, bool) else None


def _route_agreement(qoi: Artefact | None) -> float | None:
    if qoi is None:
        return None
    routes = qoi.summary.get("route_agreement")
    if not isinstance(routes, Mapping):
        return None
    found = routes.get("relative_difference")
    return float(found) if isinstance(found, int | float) else None


def _failed(
    point: Point,
    error: BaseException,
    started: float,
    directory: Path,
    *,
    cancelled: bool = False,
) -> MemberResult:
    logger.warning("point %d (%s) %s: %s", point.index, point.point_id, type(error).__name__, error)
    member = MemberResult(
        index=point.index,
        point_id=point.point_id,
        assignments=dict(point.assignments),
        wave=point.wave,
        status="cancelled" if cancelled else "failed",
        exit_class=classify(error),
        error=f"{type(error).__name__}: {error}",
        quantities=None,
        seconds=time.perf_counter() - started,
    )
    member.write(directory / MEMBERS_DIRNAME)
    return member


def _worker(arguments: tuple[str, int, str | None, str]) -> dict[str, Canonicalisable]:
    plan_path, index, root, directory = arguments
    plan = read_plan(Path(plan_path))
    return run_point(plan, index, session=Session(Store(root)), directory=Path(directory)).row()


def run_plan(
    plan: SweepPlan,
    directory: Path,
    *,
    session: Session,
    workers: int = 1,
    indices: Sequence[int] | None = None,
    fail_fast: bool = False,
) -> tuple[MemberResult, ...]:
    """Run a plan wave by wave through ``session`` and return every member's record.

    ``workers=1`` runs in this process; ``indices`` restricts the points run; ``fail_fast`` stops at
    the first member that does not reach ``ok``.
    """
    selected = sorted(set(range(len(plan.points)) if indices is None else indices))
    waves: dict[int, list[int]] = {}
    for index in selected:
        waves.setdefault(plan.point(index).wave, []).append(index)

    results: list[MemberResult] = []
    # One pool for the whole plan, not one per wave. ``spawn`` re-imports the
    # package in each worker, which costs about a second, and paying that once
    # per wave would put the *dispatch's* startup cost into a measurement of the
    # dispatch (QR-06): on a nine-point grid in five waves it took the measured
    # efficiency at four workers from 0.75 to 0.29.
    with _pool(plan, directory, workers=workers) as run_wave:
        for wave in sorted(waves):
            batch = waves[wave]
            logger.info("wave %d: %d point(s) on %d worker(s)", wave, len(batch), workers)
            found = run_wave(batch, session)
            results.extend(found)
            if fail_fast and any(member.status != "ok" for member in found):
                failed = next(member for member in found if member.status != "ok")
                logger.error(
                    "stopping: point %d (%s) exited %d",
                    failed.index,
                    failed.point_id,
                    failed.exit_class,
                )
                break
    return tuple(sorted(results, key=lambda member: member.index))


@contextmanager
def _pool(
    plan: SweepPlan, directory: Path, *, workers: int
) -> Iterator[Callable[[Sequence[int], Session], list[MemberResult]]]:
    if workers <= 1:

        def sequential(batch: Sequence[int], session: Session) -> list[MemberResult]:
            return [run_point(plan, index, session=session, directory=directory) for index in batch]

        yield sequential
        return

    plan_path = directory / PLAN_FILENAME
    if not plan_path.is_file():
        raise FileNotFoundError(
            f"a parallel sweep runs its workers from {plan_path}, which is not there; "
            "write the plan into the sweep directory before dispatching it"
        )
    context = multiprocessing.get_context("spawn")
    with context.Pool(processes=workers, initializer=pin_threads) as pool:

        def parallel(batch: Sequence[int], session: Session) -> list[MemberResult]:
            arguments = [
                (str(plan_path), index, str(session.store.root), str(directory)) for index in batch
            ]
            return [member_from_row(row) for row in pool.map(_worker, arguments)]

        yield parallel

"""Dispatch of one sweep member, one wave, or a whole plan across independent workers."""

from __future__ import annotations

import logging
import multiprocessing
import os
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from nanopnp.core.errors import EXIT_OK, classify
from nanopnp.core.hashing import Canonicalisable, canonical
from nanopnp.io.artefact import SOLUTION_SCHEMA, Artefact, StageInputs
from nanopnp.io.case import CaseDocument, dumps_case
from nanopnp.io.store import Store, atomic_write_bytes
from nanopnp.pipeline.case import resolve
from nanopnp.pipeline.run import MissingUpstreamError, run_document, stored_upstream
from nanopnp.sweep.plan import PLAN_FILENAME, Point, SweepPlan, read_plan

logger = logging.getLogger(__name__)

__all__ = [
    "MEMBERS_DIRNAME",
    "THREAD_VARIABLES",
    "MemberResult",
    "member_from_row",
    "pin_threads",
    "run_plan",
    "run_point",
]

MEMBERS_DIRNAME = "members"

THREAD_VARIABLES: tuple[str, ...] = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
)


def pin_threads() -> dict[str, str]:
    for variable in THREAD_VARIABLES:
        os.environ[variable] = "1"
    return {variable: os.environ[variable] for variable in THREAD_VARIABLES}


@dataclass(frozen=True)
class MemberResult:
    index: int
    point_id: str
    assignments: Mapping[str, Canonicalisable]
    wave: int
    status: str
    exit_class: int = EXIT_OK
    error: str | None = None
    quantities: Mapping[str, Canonicalisable] | None = None
    directory: str | None = None
    manifest: str | None = None
    solution: str | None = None
    seconds: float = 0.0
    iterations: int | None = None
    cached: bool = False
    warm_start: Mapping[str, Canonicalisable] | None = None
    wall_distance: Mapping[str, Canonicalisable] | None = None
    route_agreement: float | None = None

    def row(self) -> dict[str, Canonicalisable]:
        return {
            "index": self.index,
            "id": self.point_id,
            "assignments": dict(self.assignments),
            "wave": self.wave,
            "status": self.status,
            "exit_class": self.exit_class,
            "error": self.error,
            "quantities": None if self.quantities is None else dict(self.quantities),
            "directory": self.directory,
            "manifest": self.manifest,
            "solution": self.solution,
            "seconds": self.seconds,
            "iterations": self.iterations,
            "cached": self.cached,
            "warm_start": None if self.warm_start is None else dict(self.warm_start),
            "wall_distance": None if self.wall_distance is None else dict(self.wall_distance),
            "route_agreement": self.route_agreement,
        }

    def write(self, directory: Path) -> Path:
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{self.index:06d}.json"
        atomic_write_bytes(path, canonical(self.row()) + b"\n")
        return path


def _parent_artefact(
    plan: SweepPlan, point: Point, store: Store, *, base: CaseDocument
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
        upstream = stored_upstream(document, store=store)
    except MissingUpstreamError as error:
        # The parent has not run, which is a fallback rather than a failure. Any
        # other error is a defect and is left to raise.
        return None, (
            f"the store holds no converged state for parent point {parent.index} "
            f"({parent.point_id}); not even its upstream artefacts are stored: {error}"
        )
    key = SolveStage().key(StageInputs(resolved=resolve(document), upstream=upstream))
    found = store.get(SOLUTION_SCHEMA, key.hash)
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
    store: Store,
    directory: Path,
) -> MemberResult:
    from nanopnp.core.stages import Cancelled

    point = plan.point(index)
    started = time.perf_counter()
    base = plan.base_case()
    try:
        warm, reason = _parent_artefact(plan, point, store, base=base)
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
        result = run_document(
            document,
            case_text=case_text,
            store=store,
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
    return run_point(plan, index, store=Store(root), directory=Path(directory)).row()


def run_plan(
    plan: SweepPlan,
    directory: Path,
    *,
    store: Store,
    workers: int = 1,
    indices: Sequence[int] | None = None,
    fail_fast: bool = False,
) -> tuple[MemberResult, ...]:
    """Run a plan wave by wave and return every member's record.

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
            found = run_wave(batch, store)
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
) -> Iterator[Callable[[Sequence[int], Store], list[MemberResult]]]:
    if workers <= 1:

        def sequential(batch: Sequence[int], store: Store) -> list[MemberResult]:
            return [run_point(plan, index, store=store, directory=directory) for index in batch]

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

        def parallel(batch: Sequence[int], store: Store) -> list[MemberResult]:
            arguments = [
                (str(plan_path), index, str(store.root), str(directory)) for index in batch
            ]
            return [member_from_row(row) for row in pool.map(_worker, arguments)]

        yield parallel


def member_from_row(row: Mapping[str, Canonicalisable]) -> MemberResult:
    return MemberResult(
        index=int(row["index"]),
        point_id=str(row["id"]),
        assignments=dict(row["assignments"]),
        wave=int(row["wave"]),
        status=str(row["status"]),
        exit_class=EXIT_OK if row["exit_class"] is None else int(row["exit_class"]),
        error=None if row["error"] is None else str(row["error"]),
        quantities=None if row["quantities"] is None else dict(row["quantities"]),
        directory=None if row["directory"] is None else str(row["directory"]),
        manifest=None if row["manifest"] is None else str(row["manifest"]),
        solution=None if row["solution"] is None else str(row["solution"]),
        seconds=float(row["seconds"]),
        iterations=None if row.get("iterations") is None else int(row["iterations"]),
        cached=bool(row["cached"]),
        warm_start=None if row["warm_start"] is None else dict(row["warm_start"]),
        wall_distance=None if row["wall_distance"] is None else dict(row["wall_distance"]),
        route_agreement=(None if row["route_agreement"] is None else float(row["route_agreement"])),
    )

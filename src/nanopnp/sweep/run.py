"""Dispatch: one member alone, one wave, or a whole plan across independent workers.

FR-24 asks for the points to be dispatched as *independent jobs* and each solve
to be warm-started from a converged neighbour. Both are true here, and what makes
them compatible is that **the warm start is an optimisation the store may or may
not be able to supply**. A member resolves its parent's stage-10 artefact from
the shared store; if it is there the target rung is solved from it, and if it is
not — the parent has not run yet, or ran on another machine, or failed — the
member climbs the full NUM-18 ladder and records that it did, with the reason. A
member is therefore runnable alone, in any order, on a machine that has seen
nothing else, which is what "independent" has to mean.

**Independent workers are independent.** QR-06's scaling claim is about
independent workers, and N processes sharing one BLAS thread pool are not
independent — the measurement would report the pool. So the pool is started with
``multiprocessing.get_context("spawn")`` and each worker's initialiser pins
``OMP_NUM_THREADS``, ``OPENBLAS_NUM_THREADS`` and ``MKL_NUM_THREADS`` to one
*before* the first deferred import. ``spawn`` rather than ``fork`` because a
forked worker inherits a parent that has already imported NumPy, which reads
those variables at import time and would have read them too late; the house rule
deferring ``numpy`` and ``ngsolve`` to the function that uses them is what makes
the initialiser early enough. ``spawn`` is also the only start method Windows
has.

**The sweep never changes directory.** ``inputs.mesh.path`` and the field
documents resolve against the process working directory, so a ``chdir`` into a
member's run directory would silently change which mesh a member reads, with no
diagnostic. Workers inherit the parent's.
"""

from __future__ import annotations

import logging
import multiprocessing
import os
import time
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

from nanopnp.cli.errors import EXIT_OK, classify
from nanopnp.core.hashing import Canonicalisable, canonical
from nanopnp.io.artefact import SOLUTION_SCHEMA, Artefact, StageInputs
from nanopnp.io.case import CaseDocument, dumps_case
from nanopnp.io.store import Store
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
"""Directory under a sweep directory holding one JSON record per member.

One file per member and not one shared file: a job array writes them from
independent processes on independent machines, and the collector reads whatever
is there. Appending to one file would need a lock the store deliberately does
not have (§5.3.2).
"""

THREAD_VARIABLES: tuple[str, ...] = (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
)
"""Thread-count variables pinned to 1 in every worker (QR-06, the §8.3 NOTE)."""


def pin_threads() -> dict[str, str]:
    """Pin the linear-algebra thread counts to one and return what was set.

    Called as the worker-process initialiser, *before* the first deferred import
    of NumPy or NGSolve: those libraries read these variables when they are
    imported, and setting them afterwards has no effect at all — the pool is
    already sized. It is a no-op in a process that has already imported them,
    which is why it is the initialiser and not something the member calls.
    """
    for variable in THREAD_VARIABLES:
        os.environ[variable] = "1"
    return {variable: os.environ[variable] for variable in THREAD_VARIABLES}


@dataclass(frozen=True)
class MemberResult:
    """What one member did, as its dataset row and as its own file on disk.

    Parameters
    ----------
    index, point_id, assignments, wave
        The point, from the plan.
    status
        ``"ok"``, ``"failed"`` or ``"cancelled"``.
    exit_class
        The §3.1 exit code the failure classifies as, or ``0``. Recorded rather
        than reduced away: non-convergence at the corners of a hard envelope is
        an expected *result*, and the IF-02 NOTE exists so a job array can branch
        on it per member.
    error
        The diagnostic, verbatim, or ``None``. A gate abort's message *is* the
        diagnostic (QR-12), so it is carried into the dataset rather than
        summarised.
    quantities
        The stage-11 scalars, or ``None`` on any non-``ok`` row. ``None`` and not
        an empty mapping: a failed member's current must not read as a number,
        and QR-06's whole demand is that a failed member be distinguishable.
    """

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
    """Newton iterations the solve took, over every rung it ran.

    In the row beside the seconds because it is the load-independent half of
    what a member cost: wall time on a shared machine is a statement about the
    machine, and a warm start's saving shows in both but is only *measurable* in
    this one. ``None`` for a member that did not reach the solve.
    """
    cached: bool = False
    warm_start: Mapping[str, Canonicalisable] | None = None
    wall_distance: Mapping[str, Canonicalisable] | None = None
    route_agreement: float | None = None

    def row(self) -> dict[str, Canonicalisable]:
        """Return this member's dataset row."""
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
        """Write this member's record into a sweep's ``members/`` directory."""
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / f"{self.index:06d}.json"
        path.write_bytes(canonical(self.row()) + b"\n")
        return path


def _parent_artefact(
    plan: SweepPlan, point: Point, store: Store, *, base: CaseDocument
) -> tuple[Artefact | None, str]:
    """Return the parent's stage-10 artefact if the store holds it, and why not if not.

    The key is *computed*, never looked up by name: it is the hash of the
    parent's own resolved solve provenance and its input artefacts, which this
    process can build from the plan alone. That is what makes a member
    independent — it needs the store, and it does not need the parent's process
    to have told it anything.

    ``base`` is the case the caller has already read and gated, so that a member
    parses and hashes the base case once rather than once for itself and once
    for its parent (QR-06).
    """
    if point.parent is None:
        return None, "this point is the root of its tree and has no neighbour to start from"
    from nanopnp.solve.stage import SolveStage

    parent = plan.point(point.parent)
    try:
        key = SolveStage().key(StageInputs(case=plan.case(point.parent, base=base)))
    except Exception as error:
        # A parent whose key cannot even be computed is a parent this member
        # cannot warm-start from, and that is a fallback rather than a failure:
        # the member's own run will raise the same error properly if it is a
        # real one, with its own diagnostic and its own exit class.
        return None, f"the parent's artefact key could not be computed: {error}"
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
    """Run one member and return its record, capturing whatever it raised.

    Never raises for a member's own failure. A sweep is the first thing in this
    project that runs unattended, and a member that fails for a reason nobody
    records is indistinguishable from one that was never dispatched (QR-06); so
    the exception is classified through the same :func:`~nanopnp.cli.errors.classify`
    the CLI uses, its message is kept verbatim, and the row says so. The caller
    decides what a failure means: ``--index`` exits with the member's own class,
    a local sweep records it and carries on.

    Parameters
    ----------
    plan
        The plan, read from disk.
    index
        Which point to run.
    store
        The shared artefact store. Shared is what makes the warm start reachable
        at all, and what makes a resumed sweep a cache hit rather than a re-solve.
    directory
        The sweep directory; the member's record is written under
        :data:`MEMBERS_DIRNAME` inside it.
    """
    from nanopnp.core.stages import Cancelled
    from nanopnp.io.run import run_document

    point = plan.point(index)
    started = time.perf_counter()
    base = plan.base_case()
    warm, reason = _parent_artefact(plan, point, store, base=base)
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
    """Return a mapping-valued summary entry, or ``None`` when it is absent."""
    return dict(value) if isinstance(value, Mapping) else None


def _count(value: Canonicalisable) -> int | None:
    """Return an integer-valued summary entry, or ``None`` when it is absent."""
    return int(value) if isinstance(value, int) and not isinstance(value, bool) else None


def _route_agreement(qoi: Artefact | None) -> float | None:
    """Return the NUM-26 relative route difference, or ``None`` if it was not checked.

    Carried into every dataset row deliberately: with the wall corrections on,
    route disagreement is a statement about the *resolution* of the mesh at the
    wall as much as about the extraction, and a sweep is where an under-resolved
    corner of the envelope should be visible in the collected table rather than
    only in the log of the one member that noticed (`.knowledge/06` §7.1.1,
    NUM-26). The stage-11 summary carries the pair of currents beside the
    difference; it is the difference that is the diagnostic.
    """
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
    """Return and write the record of a member that did not finish.

    Written here rather than by the caller so that the two ``except`` arms
    cannot come to disagree about what a failed member leaves behind: a member
    that failed and left no file is indistinguishable from one that was never
    dispatched, which is the distinction QR-06 asks for.
    """
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
    """Run one member in a worker process and return its row.

    Takes and returns plain data because it crosses a process boundary: the plan
    is re-read from its file rather than pickled, which is also what makes the
    worker identical to a job-array member invoked from a shell.
    """
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

    Wave by wave because a wave is exactly the set of points that are mutually
    independent: every point of wave ``w`` has its parent in wave ``w - 1``, so
    running the waves in order is what makes the warm start available and running
    a wave in parallel is what makes it fast. On the §8.3 reference grid the
    waves are 87 points wide on average, so the dependency structure is not what
    limits QR-06 — the last few waves are the serial tail, and they are short.

    Parameters
    ----------
    plan
        The plan.
    directory
        The sweep directory; member records go under :data:`MEMBERS_DIRNAME`.
    store
        The shared artefact store every member runs into.
    workers
        Number of independent worker processes. ``1`` runs in this process,
        which is not the pool with one worker: a single-worker measurement must
        not pay the ``spawn`` cost the pool does, or ``efficiency(1)`` would be
        a statement about process startup.
    indices
        Which points to run, defaulting to all of them. Used by ``--wave``.
    fail_fast
        Stop at the first member that does not reach ``ok``. Off by default,
        because non-convergence at the corners of a hard envelope is an expected
        result and aborting on it would throw away the members that worked.
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
    """Yield a function that runs one wave, on a pool held open for the whole plan.

    ``workers <= 1`` runs in this process and starts no pool at all. That is not
    the pool with one worker, and the difference is the point: a single-worker
    measurement must not pay the ``spawn`` cost, or ``efficiency(1)`` would be a
    statement about process startup rather than the baseline the curve is
    divided by.
    """
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
    """Rebuild a member's record from a row -- a worker's return value, or a file.

    Public because the collector reads the same rows back off disk, and a second
    reader would be a second place for the row's shape to be written down.
    """
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

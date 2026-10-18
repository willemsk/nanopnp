"""The cost study: three suspected costs measured against thresholds fixed before measuring."""

from __future__ import annotations

import argparse
import contextlib
import functools
import importlib
import inspect
import json
import logging
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import warnings
from collections.abc import Callable, Iterator, Mapping, Sequence
from importlib import metadata
from pathlib import Path
from types import ModuleType
from typing import cast

from nanopnp.io.case import dump_case, read_case
from nanopnp.io.case_paths import substitute

try:
    import resource
except ImportError:  # pragma: no cover - Windows has no resource module; the A1 leg needs it
    resource = None  # type: ignore[assignment]

__all__ = [
    "A1_FRAME_COUNTS",
    "A1_THRESHOLD_GB",
    "A8_BUILD",
    "A8_THRESHOLD",
    "A16_IO",
    "A16_READS",
    "A16_THRESHOLD",
    "A16_WRITES",
    "SOLVE_RUN",
    "THREAD_VARIABLES",
    "CategoryTimer",
    "CostStudyError",
    "check_stage_total",
    "environment_record",
    "instrument",
    "main",
    "measure_a1",
    "measure_walks",
    "project",
    "resolve",
    "walk_entry",
]

logger = logging.getLogger(__name__)

A1_THRESHOLD_GB = 4.0
A8_THRESHOLD = 0.05
A16_THRESHOLD = 0.10
"""The limits registered in the Phase 4 plan's WP49 table before any measurement."""

A1_FRAME_COUNTS: tuple[int, ...] = (16, 32, 64)

A1_PROJECTED_FRAMES = 1000

STAGE_TOTAL_TOLERANCE = 0.02

THREAD_VARIABLES: tuple[str, ...] = ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")

RECORD_PATH = Path("docs/project/cost-study.json")

QUICKSTART_CASE = Path("examples/01-quickstart/quickstart.case.yaml")

CHARGED_CASE = Path("examples/07-pdb-to-charged-run/2wcd.case.yaml")

A8_BUILD: tuple[str, ...] = (
    "ngsolve.BilinearForm",
    "ngsolve.BilinearForm.__iadd__",
    "nanopnp.physics.models.CoupledModel.residual_form",
    "nanopnp.physics.models.ElectrostaticModel.residual_form",
    "nanopnp.physics.models.PoissonModel.residual_form",
    "nanopnp.solve.continuation.create",
    "nanopnp.materials.electrolyte.Electrolyte.with_switches",
    "nanopnp.solve.state.ladder",
)

A16_WRITES: tuple[str, ...] = (
    "nanopnp.io.store.Store.put",
    "numpy.savez",
    "numpy.savez_compressed",
    "nanopnp.mesh.adapter.write_msh41",
    "nanopnp.structure.ensemble.AlignedEnsemble.write",
    "nanopnp.density.map.DensityMap.write",
    "nanopnp.symmetry.reduce.ReducedMap.write",
    "nanopnp.charge.deposit.Deposit.write",
    "nanopnp.charge.protonation.ProtonationTable.write",
    "nanopnp.density.grid.write_grid",
    "nanopnp.geometry.profile.write_profile",
    "nanopnp.geometry.region.write_region",
    "nanopnp.solve.state.save",
)

A16_READS: tuple[str, ...] = (
    "nanopnp.io.store.Store.get",
    "numpy.load",
    "nanopnp.mesh.adapter.read",
    "nanopnp.structure.ensemble.AlignedEnsemble.read",
    "nanopnp.density.map.DensityMap.read",
    "nanopnp.symmetry.reduce.ReducedMap.read",
    "nanopnp.charge.deposit.Deposit.read",
    "nanopnp.charge.protonation.ProtonationTable.read",
    "nanopnp.density.grid.read_grid",
    "nanopnp.geometry.profile.load_profile",
    "nanopnp.geometry.region.read_region",
    "nanopnp.solve.state.restore",
)

A16_IO: tuple[str, ...] = A16_WRITES + A16_READS

SOLVE_RUN = "nanopnp.solve.stage.SolveStage.run"

_STAGE_TOTAL_GROUP = "stage-total"


class CostStudyError(RuntimeError):
    """A measurement cannot be trusted, or a leg cannot be run."""


class CategoryTimer:
    """Wall time accumulated per category; a nested call of one group counts once."""

    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        self.totals: dict[str, float] = {}
        self._depth: dict[str, int] = {}
        self._clock = clock or time.perf_counter

    def active(self, group: str) -> bool:
        """Whether a call of ``group`` is running."""
        return self._depth.get(group, 0) > 0

    @contextlib.contextmanager
    def time(self, category: str, *, group: str | None = None) -> Iterator[None]:
        """Add the time of the block to ``category`` unless a call of its group is outermost."""
        key = group or category
        depth = self._depth.get(key, 0)
        self._depth[key] = depth + 1
        started = self._clock()
        try:
            yield
        finally:
            self._depth[key] = depth
            if depth == 0:
                self.totals[category] = self.totals.get(category, 0.0) + self._clock() - started


def resolve(name: str) -> tuple[object, str, Callable[..., object]]:
    """Return ``(owner, attribute, callable)`` for a dotted name; CostStudyError if none."""
    parts = name.split(".")
    for split in range(len(parts) - 1, 0, -1):
        try:
            owner: object = importlib.import_module(".".join(parts[:split]))
        except ImportError:
            continue
        try:
            for part in parts[split:-1]:
                owner = getattr(owner, part)
            found = getattr(owner, parts[-1])
        except AttributeError:
            break
        if not callable(found):
            raise CostStudyError(f"{name} is not callable")
        return owner, parts[-1], found
    raise CostStudyError(f"{name} names nothing that can be imported")


@contextlib.contextmanager
def instrument(
    timer: CategoryTimer,
    categories: Mapping[str, Sequence[str]],
    *,
    group: str | None = None,
    within: str | None = None,
) -> Iterator[None]:
    """Replace each named callable, and every ``nanopnp`` import of it, by a timed wrapper.

    Parameters
    ----------
    categories
        Category to the dotted names of the callables that count towards it.
    group
        Calls of one group nest as one; the outermost call's category receives the time.
    within
        A group that must be running for a call to count.
    """
    # Resolved before any is replaced, so that a class and one of its methods named together
    # patch the class itself rather than the wrapper standing in for it.
    targets = [
        (category, owner, attribute, original, inspect.getattr_static(owner, attribute))
        for category, names in categories.items()
        for name in names
        for owner, attribute, original in (resolve(name),)
    ]
    undo: list[Callable[[], None]] = []
    replaced: list[tuple[object, object]] = []
    try:
        for category, owner, attribute, original, raw in targets:
            replacement = _replacement(timer, category, original, raw, group, within)
            undo.append(_restorer(owner, attribute, raw))
            setattr(owner, attribute, replacement)
            if isinstance(owner, ModuleType) and not isinstance(raw, type):
                # A ``from module import name`` taken before this block calls the original.
                for module, key in _imports_of(raw):
                    undo.append(functools.partial(setattr, module, key, raw))
                    setattr(module, key, replacement)
                replaced.append((replacement, raw))
        yield
    finally:
        for action in reversed(undo):
            action()
        for replacement, raw in replaced:
            for module, key in _imports_of(replacement):
                setattr(module, key, raw)


def _replacement(
    timer: CategoryTimer,
    category: str,
    original: Callable[..., object],
    raw: object,
    group: str | None,
    within: str | None,
) -> object:
    if isinstance(raw, staticmethod):
        return staticmethod(_timed(timer, category, raw.__func__, group, within))
    if isinstance(raw, classmethod):
        return classmethod(_timed(timer, category, raw.__func__, group, within))
    return _timed(timer, category, original, group, within)


def _restorer(owner: object, attribute: str, raw: object) -> Callable[[], None]:
    if isinstance(owner, type) and attribute not in vars(owner):
        return functools.partial(delattr, owner, attribute)
    return functools.partial(setattr, owner, attribute, raw)


def _imports_of(value: object) -> list[tuple[ModuleType, str]]:
    found: list[tuple[ModuleType, str]] = []
    for name, module in list(sys.modules.items()):
        if isinstance(module, ModuleType) and name.partition(".")[0] == "nanopnp":
            found.extend((module, key) for key, held in list(vars(module).items()) if held is value)
    return found


def _timed(
    timer: CategoryTimer,
    category: str,
    original: Callable[..., object],
    group: str | None,
    within: str | None,
) -> Callable[..., object]:
    @functools.wraps(original)
    def wrapper(*args: object, **kwargs: object) -> object:
        if within is not None and not timer.active(within):
            return original(*args, **kwargs)
        with timer.time(category, group=group):
            return original(*args, **kwargs)

    return wrapper


def project(points: Sequence[tuple[float, float]], at: float) -> float:
    """Return the least-squares line through ``points`` evaluated at ``at``."""
    import numpy as np

    x = np.array([point[0] for point in points], dtype=float)
    y = np.array([point[1] for point in points], dtype=float)
    slope, intercept = np.polyfit(x, y, 1)
    return float(slope * at + intercept)


def check_stage_total(measured_s: float, recorded_s: float) -> None:
    """Refuse a run whose timed stage total is more than 2 % off the recorded stage seconds."""
    if abs(measured_s - recorded_s) > STAGE_TOTAL_TOLERANCE * recorded_s:
        raise CostStudyError(
            f"the timed stage total {measured_s:.3f} s is more than "
            f"{STAGE_TOTAL_TOLERANCE:.0%} off the recorded {recorded_s:.3f} s; the run is refused"
        )


def walk_entry(
    totals: Mapping[str, float], wall_s: float, solve_s: float, legs: Sequence[str]
) -> dict[str, object]:
    """Return one walk's record: each requested leg's share, beside the denominator it used.

    Raises CostStudyError if stage 10 was not timed or its timed total is off the recorded one.
    """
    measured = totals.get("solve-stage")
    if measured is None:
        raise CostStudyError("stage 10 ran untimed: a stored solve answered the walk")
    check_stage_total(measured, solve_s)
    entry: dict[str, object] = {}
    if "a8" in legs:
        build = totals.get("build", 0.0)
        entry["a8"] = {
            "build_s": build,
            "stage10_s": solve_s,
            "share": build / solve_s,
            "threshold": A8_THRESHOLD,
            "over": build / solve_s > A8_THRESHOLD,
        }
    if "a16" in legs:
        writes, reads = totals.get("io-write", 0.0), totals.get("io-read", 0.0)
        share = (writes + reads) / wall_s
        entry["a16"] = {
            "write_s": writes,
            "read_s": reads,
            "wall_s": wall_s,
            "share": share,
            "write_share": writes / wall_s,
            "read_share": reads / wall_s,
            "threshold": A16_THRESHOLD,
            "over": share > A16_THRESHOLD,
        }
    return entry


def environment_record(repository: Path | None = None) -> dict[str, object]:
    """Return the machine, thread settings, library versions and commit a measurement ran on."""
    versions = {"python": platform.python_version(), "platform": platform.platform()}
    for package in ("nanopnp", "numpy", "scipy", "ngsolve", "MDAnalysis"):
        try:
            versions[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            versions[package] = "not installed"
    root = repository or _repository()
    status = _git(root, "status", "--porcelain", "--untracked-files=no")
    return {
        "cpu_count": os.cpu_count() or 0,
        "threads": {name: os.environ.get(name, "unset") for name in THREAD_VARIABLES},
        "versions": versions,
        "commit": _git(root, "rev-parse", "HEAD") or "unknown",
        "dirty": None if status is None else bool(status),
    }


def _repository() -> Path:
    return Path(__file__).resolve().parents[3]


def _git(repository: Path, *arguments: str) -> str | None:
    try:
        done = subprocess.run(
            ["git", "-C", str(repository), *arguments],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip()


def _peak_rss_mb() -> float:
    if resource is None:  # pragma: no cover - Windows
        raise CostStudyError(
            "peak resident memory is read from the resource module, which is absent"
        )
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return peak / 1024.0 if sys.platform != "darwin" else peak / 1024.0**2


def _run_child(arguments: Sequence[str]) -> dict[str, object]:
    done = subprocess.run(
        [sys.executable, "-m", "nanopnp.validation.costs", *arguments],
        capture_output=True,
        text=True,
        check=False,
    )
    if done.returncode != 0:
        raise CostStudyError(f"{' '.join(arguments)} failed: {done.stderr[-2000:]}")
    for line in reversed(done.stdout.splitlines()):
        with contextlib.suppress(json.JSONDecodeError):
            found = json.loads(line)
            if isinstance(found, dict):
                return found
    raise CostStudyError(f"{' '.join(arguments)} printed no result: {done.stdout[-2000:]}")


def _emit(result: Mapping[str, object]) -> None:
    sys.stdout.write(json.dumps(result) + "\n")


def _nanopnp() -> str:
    found = shutil.which("nanopnp", path=str(Path(sys.executable).parent))
    if found is None:
        raise CostStudyError(f"no nanopnp command is installed beside {sys.executable}")
    return found


def _prepare_2wcd(  # pragma: no cover - runs example 06's preparation; the script, not CI, does
    repository: Path, directory: Path
) -> Path:
    prepared = directory / "2wcd-prepared.pdb"
    subprocess.run(
        [
            sys.executable,
            str(repository / "examples" / "06-pdb-to-mesh" / "prepare.py"),
            str(repository / "tests" / "data" / "structures" / "2wcd.pdb.gz"),
            str(prepared),
        ],
        check=True,
        capture_output=True,
    )
    return prepared


def _a1_case(repository: Path, pdb: Path, dcd: Path, target: Path) -> Path:
    base = read_case(repository / CHARGED_CASE)
    document = substitute(
        base.model_copy(update={"charge": None}),
        {
            "name": "cost-a1",
            "structure.source.path": str(pdb),
            "structure.ensemble": {"trajectory": str(dcd)},
        },
    )
    return dump_case(document, target)


JITTER_DEG = 0.5
JITTER_NM = 0.02


def _write_dcd(  # pragma: no cover - writes the A1 leg's 2WCD trajectories; the script, not CI
    pdb: Path, frames: int, target: Path
) -> None:
    import MDAnalysis as mda  # noqa: N813 - the alias the library documents
    import numpy as np

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        universe = mda.Universe(str(pdb))
        base = universe.atoms.positions.astype(np.float64)
        centre = base.mean(axis=0)
        rng = np.random.default_rng(0)
        with mda.Writer(str(target), len(universe.atoms), dt=1.0) as writer:
            for _ in range(frames):
                axis = rng.normal(size=3)
                axis /= np.linalg.norm(axis)
                angle = np.radians(JITTER_DEG) * rng.normal()
                cross = np.array(
                    [[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]]
                )
                rotation = np.eye(3) + np.sin(angle) * cross + (1 - np.cos(angle)) * cross @ cross
                shift = rng.normal(scale=JITTER_NM * 10.0, size=3)
                universe.atoms.positions = (base - centre) @ rotation.T + centre + shift
                writer.write(universe.atoms)


def _a1_child(  # pragma: no cover - runs stages 1 and 2 on the protein; the script, not CI
    case: Path, store: Path, upto: str
) -> dict[str, object]:
    from nanopnp.io.store import Store
    from nanopnp.pipeline.run import run_case

    started = time.perf_counter()
    run_case(case, store=Store(store), upto=upto, write=False)
    return {"peak_mb": _peak_rss_mb(), "seconds": time.perf_counter() - started}


def measure_a1(  # pragma: no cover - runs six protein walks; the script, not CI, runs them
    repository: Path,
) -> dict[str, object]:
    """Measure stage 1's peak resident memory per frame count; project it to 1,000 frames."""
    points: list[dict[str, object]] = []
    stage1: list[tuple[float, float]] = []
    stage2: list[tuple[float, float]] = []
    with tempfile.TemporaryDirectory(prefix="cost-a1-") as scratch:
        directory = Path(scratch)
        pdb = _prepare_2wcd(repository, directory)
        for frames in A1_FRAME_COUNTS:
            dcd = directory / f"jitter-{frames}.dcd"
            _write_dcd(pdb, frames, dcd)
            case = _a1_case(repository, pdb, dcd, directory / f"a1-{frames}.case.yaml")
            store = directory / f"store-{frames}"
            first = _run_child(["_a1", str(case), str(store), "structure"])
            second = _run_child(["_a1", str(case), str(store), "density"])
            stage1.append((frames, cast(float, first["peak_mb"])))
            stage2.append((frames, cast(float, second["peak_mb"])))
            points.append(
                {
                    "frames": frames,
                    "stage1_peak_mb": first["peak_mb"],
                    "stage1_seconds": first["seconds"],
                    "stage2_peak_mb": second["peak_mb"],
                }
            )
            shutil.rmtree(store, ignore_errors=True)
            dcd.unlink()
    projected_gb = project(stage1, A1_PROJECTED_FRAMES) / 1024.0
    return {
        "points": points,
        "projected_frames": A1_PROJECTED_FRAMES,
        "projected_stage1_gb": projected_gb,
        "projected_stage2_gb": project(stage2, A1_PROJECTED_FRAMES) / 1024.0,
        "threshold_gb": A1_THRESHOLD_GB,
        "prediction_gb": 1.0,
        "over": projected_gb > A1_THRESHOLD_GB,
    }


def _quickstart_case(  # pragma: no cover - runs the mesher through the CLI; the script, not CI
    repository: Path, directory: Path
) -> Path:
    subprocess.run(
        [_nanopnp(), "mesh", "cylinder", "--out", "pore.msh"],
        check=True,
        capture_output=True,
        cwd=directory,
    )
    document = substitute(
        read_case(repository / QUICKSTART_CASE), {"inputs.mesh.path": str(directory / "pore.msh")}
    )
    return dump_case(document, directory / "quickstart.case.yaml")


def _charged_case(  # pragma: no cover - prepares 2WCD through example 06; the script, not CI
    repository: Path, directory: Path
) -> Path:
    prepared = _prepare_2wcd(repository, directory)
    document = substitute(
        read_case(repository / CHARGED_CASE), {"structure.source.path": str(prepared)}
    )
    return dump_case(document, directory / "2wcd.case.yaml")


def _walk(  # pragma: no cover - runs a full walk; the script, not CI, runs it
    case: Path, store: Path, legs: Sequence[str]
) -> dict[str, object]:
    from nanopnp.io.store import Store
    from nanopnp.pipeline.run import run_case

    timer = CategoryTimer()
    with contextlib.ExitStack() as stack:
        stack.enter_context(
            instrument(timer, {"solve-stage": [SOLVE_RUN]}, group=_STAGE_TOTAL_GROUP)
        )
        if "a8" in legs:
            stack.enter_context(instrument(timer, {"build": A8_BUILD}, within=_STAGE_TOTAL_GROUP))
        if "a16" in legs:
            stack.enter_context(
                instrument(timer, {"io-write": A16_WRITES, "io-read": A16_READS}, group="io")
            )
        started = time.perf_counter()
        result = run_case(case, store=Store(store), write=False)
        wall = time.perf_counter() - started
    solve_s = next(record.seconds for record in result.stages if record.name == "solve")
    return {"totals": dict(timer.totals), "wall_s": wall, "solve_s": solve_s}


def measure_walks(  # pragma: no cover - runs the quick-start and 2WCD walks; the script, not CI
    repository: Path, legs: Sequence[str]
) -> dict[str, dict[str, object]]:
    """Walk the quick-start and the 2WCD case cold, each in a fresh process, timing each leg."""
    record: dict[str, dict[str, object]] = {}
    with tempfile.TemporaryDirectory(prefix="cost-walk-") as scratch:
        root = Path(scratch)
        for name in ("quickstart", "2wcd"):
            (root / name).mkdir()
        cases = {
            "quickstart": _quickstart_case(repository, root / "quickstart"),
            "2wcd": _charged_case(repository, root / "2wcd"),
        }
        for name, case in cases.items():
            child = _run_child(["_walk", str(case), str(root / f"store-{name}"), *legs])
            record[name] = walk_entry(
                cast(Mapping[str, float], child["totals"]),
                cast(float, child["wall_s"]),
                cast(float, child["solve_s"]),
                legs,
            )
    return record


def main(argv: Sequence[str] | None = None) -> int:
    """Run a leg of the cost study and write the record."""
    parser = argparse.ArgumentParser(prog="python -m nanopnp.validation.costs")
    parser.add_argument("leg", choices=["a1", "a8", "a16", "walks", "all", "_a1", "_walk"])
    parser.add_argument("rest", nargs="*")
    parser.add_argument("--repository", type=Path, default=_repository())
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    if args.leg == "_a1":
        case, store, upto = args.rest
        _emit(_a1_child(Path(case), Path(store), upto))
        return 0
    if args.leg == "_walk":
        case, store, *walked = args.rest
        _emit(_walk(Path(case), Path(store), walked))
        return 0

    repository = args.repository
    out = args.out or repository / RECORD_PATH
    legs = {"all": ["a1", "a8", "a16"], "walks": ["a8", "a16"]}.get(args.leg, [args.leg])
    record: dict[str, object] = {}
    if out.is_file() and args.leg != "all":
        record = json.loads(out.read_text(encoding="utf-8"))
    stored = record.get("environment")
    environments = dict(stored) if isinstance(stored, dict) else {}
    environments.update(dict.fromkeys(legs, environment_record(repository)))
    record["environment"] = environments
    if "a1" in legs:
        record["a1"] = measure_a1(repository)
    walks = [leg for leg in legs if leg != "a1"]
    if walks:
        held = record.get("walks")
        merged: dict[str, dict[str, object]] = dict(held) if isinstance(held, dict) else {}
        for name, entry in measure_walks(repository, walks).items():
            merged[name] = {**merged.get(name, {}), **entry}
        record["walks"] = merged
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    logger.info("wrote %s", out)
    return 0


if __name__ == "__main__":  # pragma: no cover - the module is run as a script
    raise SystemExit(main())

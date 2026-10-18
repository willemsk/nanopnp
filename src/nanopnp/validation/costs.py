"""The cost study: three suspected costs measured against thresholds fixed before measuring."""

from __future__ import annotations

import argparse
import contextlib
import functools
import importlib
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
    "A16_THRESHOLD",
    "CategoryTimer",
    "CostStudyError",
    "check_stage_total",
    "environment_record",
    "instrument",
    "main",
    "project",
    "resolve",
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

A16_IO: tuple[str, ...] = (
    "nanopnp.io.store.Store.get",
    "nanopnp.io.store.Store.put",
    "numpy.savez",
    "numpy.savez_compressed",
    "numpy.load",
    "nanopnp.mesh.adapter.read",
    "nanopnp.mesh.adapter.write_msh41",
)

SOLVE_RUN = "nanopnp.solve.stage.SolveStage.run"

_STAGE_TOTAL_GROUP = "stage-total"


class CostStudyError(RuntimeError):
    """A measurement cannot be trusted, or a leg cannot be run."""


class CategoryTimer:
    """Wall time accumulated per category; a nested call of one group counts once."""

    def __init__(self) -> None:
        self.totals: dict[str, float] = {}
        self._depth: dict[str, int] = {}

    def active(self, group: str) -> bool:
        """Whether a call of ``group`` is running."""
        return self._depth.get(group, 0) > 0

    @contextlib.contextmanager
    def time(self, category: str, *, group: str | None = None) -> Iterator[None]:
        """Add the time of the block to ``category`` unless a call of its group is outermost."""
        key = group or category
        depth = self._depth.get(key, 0)
        self._depth[key] = depth + 1
        started = time.perf_counter()
        try:
            yield
        finally:
            self._depth[key] = depth
            if depth == 0:
                self.totals[category] = (
                    self.totals.get(category, 0.0) + time.perf_counter() - started
                )


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
    """Replace each named callable by a timed wrapper for the duration of the block.

    Parameters
    ----------
    categories
        Category to the dotted names of the callables that count towards it.
    group
        Calls of one group nest as one; the outermost call's category receives the time.
    within
        A group that must be running for a call to count.
    """
    patched: list[tuple[object, str, Callable[..., object]]] = []
    try:
        for category, names in categories.items():
            for name in names:
                owner, attribute, original = resolve(name)
                patched.append((owner, attribute, original))
                setattr(owner, attribute, _timed(timer, category, original, group, within))
        yield
    finally:
        for owner, attribute, original in reversed(patched):
            setattr(owner, attribute, original)


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


def environment_record(repository: Path | None = None) -> dict[str, object]:
    """Return the machine, thread settings, library versions and commit a measurement ran on."""
    versions = {"python": platform.python_version(), "platform": platform.platform()}
    for package in ("nanopnp", "numpy", "scipy", "ngsolve", "MDAnalysis"):
        try:
            versions[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            versions[package] = "not installed"
    return {
        "cpu_count": os.cpu_count() or 0,
        "threads": {name: os.environ.get(name, "unset") for name in THREAD_VARIABLES},
        "versions": versions,
        "commit": _commit(repository or _repository()),
    }


def _repository() -> Path:
    return Path(__file__).resolve().parents[3]


def _commit(repository: Path) -> str:
    try:
        done = subprocess.run(
            ["git", "-C", str(repository), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return "unknown"
    return done.stdout.strip() or "unknown"


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
    return dict(json.loads(done.stdout.strip().splitlines()[-1]))


def _prepare_2wcd(repository: Path, directory: Path) -> Path:
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


A1_CASE = """\
schema: nanopnp/case/v0.5
name: cost-a1
structure:
  source: {{path: {pdb}}}
  symmetry: {{point_group: C12}}
  ensemble: {{trajectory: {dcd}}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 0.15
  parameters: willems2020_nacl
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics: {{model: epnp-ns, solid_permittivities: {{protein: 20.0, membrane: 3.2}}}}
"""

JITTER_DEG = 0.5
JITTER_NM = 0.02


def _write_dcd(pdb: Path, frames: int, target: Path) -> None:
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


def _a1_child(case: Path, store: Path, upto: str) -> dict[str, object]:
    from nanopnp.io.store import Store
    from nanopnp.pipeline.run import run_case

    started = time.perf_counter()
    run_case(case, store=Store(store), upto=upto, write=False)
    return {"peak_mb": _peak_rss_mb(), "seconds": time.perf_counter() - started}


def measure_a1(repository: Path) -> dict[str, object]:
    """Measure stage 1's peak resident memory per frame count; project it to 1,000 frames."""
    points: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="cost-a1-") as scratch:
        directory = Path(scratch)
        pdb = _prepare_2wcd(repository, directory)
        for frames in A1_FRAME_COUNTS:
            dcd = directory / f"jitter-{frames}.dcd"
            _write_dcd(pdb, frames, dcd)
            case = directory / f"a1-{frames}.case.yaml"
            case.write_text(A1_CASE.format(pdb=pdb, dcd=dcd), encoding="utf-8")
            store = directory / f"store-{frames}"
            first = _run_child(["_a1", str(case), str(store), "structure"])
            second = _run_child(["_a1", str(case), str(store), "density"])
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
    line = [(float(str(p["frames"])), float(str(p["stage1_peak_mb"]))) for p in points]
    stage2 = [(float(str(p["frames"])), float(str(p["stage2_peak_mb"]))) for p in points]
    projected_gb = project(line, A1_PROJECTED_FRAMES) / 1024.0
    return {
        "points": points,
        "projected_frames": A1_PROJECTED_FRAMES,
        "projected_stage1_gb": projected_gb,
        "projected_stage2_gb": project(stage2, A1_PROJECTED_FRAMES) / 1024.0,
        "threshold_gb": A1_THRESHOLD_GB,
        "prediction_gb": 1.0,
        "over": projected_gb > A1_THRESHOLD_GB,
    }


def _quickstart_case(repository: Path, directory: Path) -> Path:
    source = repository / "examples" / "01-quickstart"
    text = (source / "quickstart.case.yaml").read_text(encoding="utf-8")
    (directory / "quickstart.case.yaml").write_text(
        text.replace("path: pore.msh", f"path: {directory / 'pore.msh'}"), encoding="utf-8"
    )
    subprocess.run(
        [str(Path(sys.executable).with_name("nanopnp")), "mesh", "cylinder", "--out", "pore.msh"],
        check=True,
        capture_output=True,
        cwd=directory,
    )
    return directory / "quickstart.case.yaml"


def _charged_case(repository: Path, directory: Path) -> Path:
    _prepare_2wcd(repository, directory)
    text = (repository / "examples" / "07-pdb-to-charged-run" / "2wcd.case.yaml").read_text(
        encoding="utf-8"
    )
    case = directory / "2wcd.case.yaml"
    case.write_text(
        text.replace("path: 2wcd-prepared.pdb", f"path: {directory / '2wcd-prepared.pdb'}"),
        encoding="utf-8",
    )
    return case


def _walk(case: Path, store: Path, legs: Sequence[str]) -> tuple[dict[str, float], float, float]:
    from nanopnp.io.store import Store
    from nanopnp.pipeline.run import run_case

    timer = CategoryTimer()
    with contextlib.ExitStack() as stack:
        stack.enter_context(
            instrument(timer, {"solve-stage": [SOLVE_RUN]}, group=_STAGE_TOTAL_GROUP)
        )
        if "a8" in legs:
            stack.enter_context(
                instrument(timer, {"build": list(A8_BUILD)}, within=_STAGE_TOTAL_GROUP)
            )
        if "a16" in legs:
            stack.enter_context(_split_io(timer))
        started = time.perf_counter()
        result = run_case(case, store=Store(store), write=False)
        wall = time.perf_counter() - started
    solve_s = next(record.seconds for record in result.stages if record.name == "solve")
    return dict(timer.totals), wall, solve_s


@contextlib.contextmanager
def _split_io(timer: CategoryTimer) -> Iterator[None]:
    writes = ("nanopnp.io.store.Store.put", "numpy.savez", "numpy.savez_compressed")
    reads = tuple(name for name in A16_IO if name not in writes)
    with (
        instrument(timer, {"io-write": writes}, group="io"),
        instrument(timer, {"io-read": reads}, group="io"),
    ):
        yield


def measure_walks(repository: Path, legs: Sequence[str]) -> dict[str, object]:
    """Walk the quick-start and the 2WCD case cold, timing what each requested leg counts."""
    record: dict[str, object] = {}
    with tempfile.TemporaryDirectory(prefix="cost-walk-") as scratch:
        root = Path(scratch)
        cases = {
            "quickstart": _quickstart_case(repository, _fresh(root / "quickstart")),
            "2wcd": _charged_case(repository, _fresh(root / "2wcd")),
        }
        for name, case in cases.items():
            totals, wall, solve_s = _walk(case, root / f"store-{name}", legs)
            check_stage_total(totals["solve-stage"], solve_s)
            entry: dict[str, object] = {"wall_s": wall, "stage10_s": solve_s}
            if "a8" in legs:
                build = totals.get("build", 0.0)
                entry["a8"] = {
                    "build_s": build,
                    "share": build / solve_s,
                    "threshold": A8_THRESHOLD,
                    "over": build / solve_s > A8_THRESHOLD,
                }
            if "a16" in legs:
                writes, reads = totals.get("io-write", 0.0), totals.get("io-read", 0.0)
                share = (writes + reads) / wall
                entry["a16"] = {
                    "write_s": writes,
                    "read_s": reads,
                    "share": share,
                    "write_share": writes / wall,
                    "read_share": reads / wall,
                    "threshold": A16_THRESHOLD,
                    "over": share > A16_THRESHOLD,
                }
            record[name] = entry
    return record


def _fresh(directory: Path) -> Path:
    directory.mkdir(parents=True)
    return directory


def main(argv: Sequence[str] | None = None) -> int:
    """Run a leg of the cost study and write the record."""
    parser = argparse.ArgumentParser(prog="python -m nanopnp.validation.costs")
    parser.add_argument("leg", choices=["a1", "a8", "a16", "walks", "all", "_a1"])
    parser.add_argument("rest", nargs="*")
    parser.add_argument("--repository", type=Path, default=_repository())
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    if args.leg == "_a1":
        case, store, upto = args.rest
        print(json.dumps(_a1_child(Path(case), Path(store), upto)))
        return 0

    repository = args.repository
    out = args.out or repository / RECORD_PATH
    record: dict[str, object] = {}
    if out.is_file():
        record = json.loads(out.read_text(encoding="utf-8"))
    record["environment"] = environment_record(repository)
    legs = {
        "all": ["a1", "a8", "a16"],
        "walks": ["a8", "a16"],
    }.get(args.leg, [args.leg])
    if "a1" in legs:
        record["a1"] = measure_a1(repository)
    walks = [leg for leg in legs if leg != "a1"]
    if walks:
        stored = record.get("walks")
        merged: dict[str, dict[str, object]] = dict(stored) if isinstance(stored, dict) else {}
        for name, entry in measure_walks(repository, walks).items():
            merged.setdefault(name, {}).update(dict(entry))  # type: ignore[call-overload]
        record["walks"] = merged
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    logger.info("wrote %s", out)
    return 0


if __name__ == "__main__":  # pragma: no cover - the module is run as a script
    raise SystemExit(main())

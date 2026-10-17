"""Fixtures every tier shares: the vendored 2WCD, its prepared and seeded stores, the backends."""

from __future__ import annotations

import copy
import logging
import math
import os
import pickle
import shutil
import sys
import warnings
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING, Any

import numpy as np
import pytest
import yaml
from filelock import FileLock

from nanopnp.io.artefact import CASE_SCHEMA as CASE_SCHEMA
from nanopnp.pipeline.case import resolve

# Make ``tests.conftest`` name this module, so both import paths share its fixtures.
sys.modules["tests.conftest"] = sys.modules[__name__]
if "tests" in sys.modules:
    sys.modules["tests"].conftest = sys.modules[__name__]

if TYPE_CHECKING:
    import MDAnalysis as mda  # noqa: N813 - the alias the library documents
    import ngsolve

logger = logging.getLogger(__name__)

STRUCTURES = Path(__file__).parent / "data" / "structures"
DEPOSITED_2WCD = STRUCTURES / "2wcd.pdb.gz"
DODECAMER = "A,B,C,D,E,F,G,H,I,J,K,L"

REQUIRE_GMSH = "NANOPNP_REQUIRE_GMSH"

EXTENDED = "--extended"

os.environ.setdefault("GIT_CONFIG_GLOBAL", "/dev/null")


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        EXTENDED,
        action="store_true",
        help="also run the tests marked extended: the executed examples and the 2WCD "
        "walks, which CI gates after a merge (SPECIFICATION.md section 7.6)",
    )


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if not config.getoption(EXTENDED):
        named = {
            Path(argument.split("::")[0]).resolve()
            for argument in config.args
            if Path(argument.split("::")[0]).is_file()
        }
        kept, left_out = [], []
        for item in items:
            if (
                item.get_closest_marker("extended")
                and not item.get_closest_marker("slow")
                and Path(item.path).resolve() not in named
            ):
                left_out.append(item)
            else:
                kept.append(item)
        if left_out:
            config.hook.pytest_deselected(items=left_out)
            items[:] = kept
    for item in items:
        if item.get_closest_marker("extended"):
            item.add_marker(pytest.mark.no_cover)


def import_gmsh() -> ModuleType:
    try:
        import gmsh
    except (ImportError, OSError) as error:  # pragma: no cover - environment-dependent
        reason = f"gmsh does not import: {type(error).__name__}: {error}"
        if os.environ.get(REQUIRE_GMSH) == "1":
            pytest.fail(
                f"{REQUIRE_GMSH}=1 and {reason}. On Debian or Ubuntu: apt-get install -y "
                "--no-install-recommends libglu1-mesa libxft2 libxinerama1 libxcursor1"
            )
        pytest.skip(reason)
    return gmsh


@pytest.fixture
def gmsh_module() -> ModuleType:
    return import_gmsh()


def require_apbs() -> None:
    from nanopnp.validation.apbs import REQUIRE_APBS, apbs_available

    reason = apbs_available()
    if reason is None:
        return
    if os.environ.get(REQUIRE_APBS) == "1":  # pragma: no cover - environment-dependent
        pytest.fail(f"{REQUIRE_APBS}=1 and {reason}")
    pytest.skip(reason)  # pragma: no cover - environment-dependent


@pytest.fixture(scope="session")
def apbs() -> None:
    require_apbs()


CASE_YAML_TEMPLATE: str = f"""\
schema: {CASE_SCHEMA}
name: minimal
inputs: {{mesh: {{path: pore.vol, format: vol}}}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 1.0
  parameters: willems2020_nacl
boundary_conditions: {{bias_V: 0.1}}
physics: {{model: pnp-ns}}
"""


@pytest.fixture
def case_yaml_template() -> str:
    return CASE_YAML_TEMPLATE


def _deep_merge_dict(target: dict[str, Any], source: Mapping[str, Any]) -> dict[str, Any]:
    for key, value in source.items():
        if key in target and isinstance(target[key], dict) and isinstance(value, Mapping):
            _deep_merge_dict(target[key], value)
        else:
            target[key] = copy.deepcopy(value) if isinstance(value, (dict, list)) else value
    return target


def _set_nested_override(
    target: dict[str, Any],
    path: str,
    value: Any,  # noqa: ANN401
) -> None:
    parts = path.split(".")
    curr = target
    for part in parts[:-1]:
        if part not in curr or not isinstance(curr[part], dict):
            curr[part] = {}
        curr = curr[part]
    last = parts[-1]
    if last in curr and isinstance(curr[last], dict) and isinstance(value, Mapping):
        _deep_merge_dict(curr[last], value)
    else:
        curr[last] = copy.deepcopy(value) if isinstance(value, (dict, list)) else value


def make_case_dict(**overrides: Any) -> dict[str, Any]:  # noqa: ANN401
    base: dict[str, Any] = {
        "schema": CASE_SCHEMA,
        "name": "minimal",
        "inputs": {"mesh": {"path": "pore.vol", "format": "vol"}},
        "electrolyte": {
            "species": [{"name": "Na+", "z": 1}, {"name": "Cl-", "z": -1}],
            "concentration_M": 1.0,
            "parameters": "willems2020_nacl",
        },
        "boundary_conditions": {"bias_V": 0.1},
        "physics": {"model": "pnp-ns"},
    }
    for path, value in overrides.items():
        _set_nested_override(base, path, value)
    return base


@pytest.fixture
def make_case() -> Callable[..., dict[str, Any]]:
    return make_case_dict


PREPARED_TILT_DEG = 4.0

PREPARED_SHIFT_NM = (0.6, -0.35, 1.2)


@dataclass(frozen=True)
class Prepared2WCD:
    path: Path
    tilt_deg: float
    rotation: np.ndarray
    shift_nm: np.ndarray


def rotation_about(axis: np.ndarray, angle: float) -> np.ndarray:
    k = np.asarray(axis, dtype=np.float64) / np.linalg.norm(axis)
    skew = np.array([[0.0, -k[2], k[1]], [k[2], 0.0, -k[0]], [-k[1], k[0], 0.0]])
    return np.eye(3) + math.sin(angle) * skew + (1.0 - math.cos(angle)) * (skew @ skew)


def _prepared_rotation(group: mda.AtomGroup) -> np.ndarray:
    # The deposited +z end is trans, so the axis is taken to -z
    # (knowledge/04-clya-geometry-and-charge/01-geometry-pipeline-as-executed.md).
    from nanopnp.structure.axis import measure_axis

    chains = []
    for chain in DODECAMER.split(","):
        ca = group.select_atoms(f"chainID {chain} and name CA and resid 8:292")
        chains.append(ca.positions / 10.0)
    record = measure_axis(np.asarray(chains), 12)
    flat = np.concatenate(chains)
    height = (flat - record.centroid_nm) @ record.axis
    radial = np.linalg.norm((flat - record.centroid_nm) - np.outer(height, record.axis), axis=1)
    top = radial[height > np.quantile(height, 0.8)].mean()
    bottom = radial[height < np.quantile(height, 0.2)].mean()
    cis = record.axis if top > bottom else -record.axis
    logger.info("deposited 2WCD: +axis end radius %.2f nm, -axis end %.2f nm", top, bottom)
    to_z = (
        rotation_about(np.cross(cis, [0, 0, 1.0]), math.acos(float(cis[2])))
        if cis[2] < 1
        else np.eye(3)
    )
    tilt = rotation_about(np.array([1.0, 1.0, 0.0]), math.radians(PREPARED_TILT_DEG))
    return tilt @ to_z


@pytest.fixture(scope="session")
def dodecamer_2wcd() -> mda.AtomGroup:
    from nanopnp.structure.read import load_universe

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        universe = load_universe(DEPOSITED_2WCD)
    return universe.select_atoms("protein and chainID " + " ".join(DODECAMER.split(",")))


def shared_directory(tmp_path_factory: pytest.TempPathFactory) -> Path:
    base = tmp_path_factory.getbasetemp()
    return base.parent if os.environ.get("PYTEST_XDIST_WORKER") else base


@pytest.fixture(scope="session")
def prepared_2wcd(
    dodecamer_2wcd: mda.AtomGroup, tmp_path_factory: pytest.TempPathFactory
) -> Prepared2WCD:
    # Imported here: this conftest loads on every run, and listing the stages must import no extra.
    import MDAnalysis as mda  # noqa: N813 - the alias the library documents
    from MDAnalysis.coordinates.memory import MemoryReader

    group = dodecamer_2wcd
    rotation = _prepared_rotation(group)
    shift = np.asarray(PREPARED_SHIFT_NM)
    shared = shared_directory(tmp_path_factory)
    path = shared / "prepared" / "2wcd-prepared.pdb"
    with FileLock(str(shared / "prepared.lock")):
        if not path.is_file():
            moved = group.positions @ rotation.T + shift * 10.0
            universe = mda.Merge(group)
            universe.load_new(np.asarray(moved[None], dtype=np.float32), format=MemoryReader)
            path.parent.mkdir(parents=True, exist_ok=True)
            staging = path.with_suffix(f".{os.getpid()}.pdb")
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                universe.atoms.write(str(staging))
            staging.replace(path)
    return Prepared2WCD(path=path, tilt_deg=PREPARED_TILT_DEG, rotation=rotation, shift_nm=shift)


SEED_CASE = (
    f"schema: {CASE_SCHEMA}\n"
    """name: 2wcd-seed
structure:
  source: {{path: {pdb}}}
  symmetry: {{point_group: C12}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 0.15
  parameters: willems2020_nacl
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics: {{model: epnp-ns, solid_permittivities: {{protein: 20.0, membrane: 3.2}}}}
"""
)

SEED_UPTO = "mesh"


def _structure_case(directory: Path, pdb: Path, name: str = "seed.case.yaml") -> Path:
    case = directory / name
    case.write_text(SEED_CASE.format(pdb=pdb), encoding="utf-8")
    return case


@pytest.fixture(scope="session")
def structure_2wcd(prepared_2wcd: Prepared2WCD, tmp_path_factory: pytest.TempPathFactory) -> Path:
    from nanopnp.io.store import Store
    from nanopnp.pipeline.run import run_case

    shared = shared_directory(tmp_path_factory)
    seed = shared / "2wcd-structure"
    ready = seed / "READY"
    with FileLock(str(shared / "2wcd-structure.lock")):
        if not ready.is_file():
            seed.mkdir(parents=True, exist_ok=True)
            case = _structure_case(seed, prepared_2wcd.path)
            run_case(case, store=Store(seed / "store"), upto="structure", write=False)
            ready.write_text("", encoding="utf-8")
    return seed / "store"


@dataclass(frozen=True)
class Seed2WCD:
    store: Path
    centre_z_nm: float

    @property
    def geometry(self) -> str:
        return f"geometry: {{membrane: {{centre_z_nm: {self.centre_z_nm!r}}}}}\n"

    def __call__(self, root: Path) -> Path:
        shutil.copytree(self.store / "artefacts", root / "artefacts", dirs_exist_ok=True)
        return root


def register_2wcd(structure_artefact: object) -> float:
    from nanopnp.structure.ensemble import PAYLOAD_NAME, AlignedEnsemble
    from nanopnp.validation.geometry import register_by_centroid

    ensemble = AlignedEnsemble.read(structure_artefact.payload[PAYLOAD_NAME])  # type: ignore[attr-defined]
    return register_by_centroid(
        ensemble.positions_nm, name=ensemble.name, resid=ensemble.resid, chain=ensemble.chain
    )


@pytest.fixture(scope="session")
def seeded_2wcd(
    prepared_2wcd: Prepared2WCD,
    structure_2wcd: Path,
    tmp_path_factory: pytest.TempPathFactory,
) -> Seed2WCD:
    from nanopnp.io.store import Store
    from nanopnp.pipeline.run import run_case

    shared = shared_directory(tmp_path_factory)
    seed = shared / "2wcd-seed"
    ready = seed / "READY"
    centre_file = seed / "centre_z_nm"
    with FileLock(str(shared / "2wcd-seed.lock")):
        if not ready.is_file():
            seed.mkdir(parents=True, exist_ok=True)
            store = Store(seed / "store")
            # dirs_exist_ok: a worker whose seeding raised left the copy behind,
            # and the next worker to take the lock must meet that error, not this.
            shutil.copytree(
                structure_2wcd / "artefacts", store.root / "artefacts", dirs_exist_ok=True
            )
            case = _structure_case(seed, prepared_2wcd.path)
            stage4 = run_case(case, store=store, upto="contour", write=False)
            centre = register_2wcd(stage4.artefacts["structure"])
            seeded = Seed2WCD(store=store.root, centre_z_nm=centre)
            meshed = seed / "mesh.case.yaml"
            meshed.write_text(
                SEED_CASE.format(pdb=prepared_2wcd.path).replace(
                    "electrolyte:", seeded.geometry + "electrolyte:", 1
                ),
                encoding="utf-8",
            )
            walked = run_case(meshed, store=store, upto=SEED_UPTO, write=False)
            # The one place stages 4 to 6 of the default-size 2WCD are computed in a
            # session: the modules that read them log a store lookup, not this.
            logger.info(
                "2WCD seed, centre_z_nm = %.4f nm: stage times %s s",
                centre,
                {
                    record.name: round(record.seconds, 2)
                    for record in (*stage4.stages, *walked.stages)
                    if not record.cached
                },
            )
            centre_file.write_text(repr(centre), encoding="utf-8")
            ready.write_text("", encoding="utf-8")
    return Seed2WCD(store=seed / "store", centre_z_nm=float(centre_file.read_text("utf-8")))


@pytest.fixture(scope="session")
def clya_reference_mesh(tmp_path_factory: pytest.TempPathFactory) -> Callable[[], ngsolve.Mesh]:
    shared = shared_directory(tmp_path_factory)
    path = shared / "reference-mesh" / "mesh.pickle"
    with FileLock(str(shared / "reference-mesh.lock")):
        if not path.is_file():
            from nanopnp.mesh.reference import ReferenceGeometry

            mesh = ReferenceGeometry.from_fixture().generate(check_quality=False)
            path.parent.mkdir(parents=True, exist_ok=True)
            # A pickle, not a .vol: the .vol text moves vertices by up to 5.6e-17 nm and
            # changes the geometry digest
            # (knowledge/06-numerics-fem/17-tier-3-test-evidence-the-mesh-geometry.md).
            staging = path.with_suffix(f".{os.getpid()}.pickle")
            staging.write_bytes(pickle.dumps(mesh))
            staging.replace(path)

    def load() -> ngsolve.Mesh:
        mesh: ngsolve.Mesh = pickle.loads(path.read_bytes())
        return mesh

    return load


SYNTHETIC_RESIDUES = 8

_ALANINE_NM: dict[str, tuple[float, float, float]] = {
    # A rough alanine about its C-alpha, in nm: bond lengths of 0.13-0.15 nm.
    "N": (-0.12, 0.06, -0.05),
    "CA": (0.0, 0.0, 0.0),
    "C": (0.12, 0.07, 0.05),
    "O": (0.13, 0.19, 0.06),
    "CB": (0.0, -0.15, 0.03),
}


def synthetic_c12_positions_nm(turn_rad: float = 0.0) -> tuple[np.ndarray, list[str], list[str]]:
    positions: list[np.ndarray] = []
    names: list[str] = []
    chains: list[str] = []
    for chain in range(12):
        angle = turn_rad + 2.0 * math.pi * chain / 12
        rotation = rotation_about(np.array([0.0, 0.0, 1.0]), angle)
        for residue in range(SYNTHETIC_RESIDUES):
            radius = 2.6 + 0.1 * residue
            phase = 0.06 * residue
            centre = np.array([radius * math.cos(phase), radius * math.sin(phase), 0.45 * residue])
            for name, offset in _ALANINE_NM.items():
                positions.append(rotation @ (centre + np.asarray(offset)))
                names.append(name)
                chains.append("ABCDEFGHIJKL"[chain])
    return np.asarray(positions), names, chains


def write_synthetic_pdb(path: Path, positions_nm: np.ndarray, names: list[str]) -> Path:
    lines = []
    for index, (position, name) in enumerate(zip(positions_nm, names, strict=True)):
        chain = "ABCDEFGHIJKL"[index // (5 * SYNTHETIC_RESIDUES)]
        resid = 1 + (index // 5) % SYNTHETIC_RESIDUES
        x, y, z = position * 10.0
        lines.append(
            f"ATOM  {index + 1:5d} {name:<4s} ALA {chain}{resid:4d}    "
            f"{x:8.3f}{y:8.3f}{z:8.3f}  1.00  0.00           {name[0]}"
        )
    path.write_text("\n".join([*lines, "END"]) + "\n", encoding="utf-8")
    return path


@pytest.fixture(scope="session")
def synthetic_c12(tmp_path_factory: pytest.TempPathFactory) -> Path:
    positions, names, _ = synthetic_c12_positions_nm()
    return write_synthetic_pdb(tmp_path_factory.mktemp("synthetic") / "c12.pdb", positions, names)


@pytest.fixture(scope="session")
def c12_assembly() -> Callable[[float], tuple[np.ndarray, list[str], list[str]]]:
    return synthetic_c12_positions_nm


TUBE_NAMES = ("N", "CA", "C", "O", "CB")


def write_tube_pdb(path: Path) -> Path:
    lines = []
    serial = 0
    for chain in range(12):
        points = [
            (rho, 2.0 * math.pi * (5 * chain + k) / 60, 0.3 * layer)
            for layer in range(9)
            for rho in (2.7, 3.0, 3.3)
            for k in range(5)
        ]
        for index, (rho, angle, z) in enumerate(points):
            serial += 1
            name = TUBE_NAMES[index % 5]
            x, y = 10 * rho * math.cos(angle), 10 * rho * math.sin(angle)
            lines.append(
                f"ATOM  {serial:5d} {name:<4s} ALA {'ABCDEFGHIJKL'[chain]}{1 + index // 5:4d}    "
                f"{x:8.3f}{y:8.3f}{10 * z:8.3f}  1.00  0.00           {name[0]}"
            )
    path.write_text("\n".join([*lines, "END"]) + "\n", encoding="utf-8")
    return path


@pytest.fixture(scope="session")
def tube_pdb(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return write_tube_pdb(tmp_path_factory.mktemp("tube") / "tube.pdb")


def write_parallelogram_profile(path: Path, *, citation: str = "tests/conftest.py") -> Path:
    from nanopnp.geometry.profile import (
        PROFILE_SCHEMA,
        PoreProfile,
        ProfileProvenance,
        min_feature_size,
        min_vertex_spacing,
        signed_area,
        write_profile,
    )

    points = [(2.0, -3.0), (3.0, -3.0), (6.0, 3.0), (5.0, 3.0)]
    array = np.asarray(points, dtype=np.float64)
    profile = PoreProfile(
        schema=PROFILE_SCHEMA,
        name="parallelogram",
        provenance=ProfileProvenance(
            source="test",
            citation=citation,
            sha256="0" * 64,
            vertex_count=len(points),
            min_vertex_spacing_nm=min_vertex_spacing(array),
            min_feature_size_nm=min_feature_size(array),
            signed_area_nm2=signed_area(array),
        ),
        vertices=points,
    )
    return write_profile(profile, path)


@pytest.fixture(scope="session")
def parallelogram_profile(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return write_parallelogram_profile(tmp_path_factory.mktemp("parallelogram") / "profile.yaml")


CHARGED_TUBE_ATOMS: tuple[tuple[str, float, float, float, float], ...] = (
    ("NZ", 32.5, 0.0, -15.0, 1.0),
    ("OE1", 0.0, 47.5, 15.0, -2.0),
)

CHARGED_TUBE_RADIUS_A = 1.5

CHARGED_TUBE_SECOND_FRAME_E: tuple[float, float] = (1.0, -3.0)


# size_scale 5, not the 20 of the uncharged case: at 20 the deployed field's worst plane fails the
# 1e-3 quadrature gate
# (knowledge/04-clya-geometry-and-charge/13-tier-3-test-evidence-the-charged-tube.md).
def write_charged_tube(
    directory: Path, *, frames: int = 1, size_scale: float = 5.0, charge_block: str | None = None
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    profile = write_parallelogram_profile(directory / "profile.yaml")
    charges = [tuple(atom[4] for atom in CHARGED_TUBE_ATOMS), CHARGED_TUBE_SECOND_FRAME_E]
    lines: list[str] = []
    for frame in range(frames):
        if frames > 1:
            lines.append(f"MODEL     {frame + 1:4d}")
        for serial, ((name, x, y, z, _), charge) in enumerate(
            zip(CHARGED_TUBE_ATOMS, charges[frame], strict=True), start=1
        ):
            lines.append(
                f"ATOM  {serial:5d} {name:<4} GLU A  18    {x:8.3f}{y:8.3f}{z:8.3f}"
                f" {charge:7.4f} {CHARGED_TUBE_RADIUS_A:6.4f}"
            )
        if frames > 1:
            lines.append("ENDMDL")
    pqr = directory / "atoms.pqr"
    pqr.write_text("\n".join(lines) + "\n", encoding="utf-8")
    case = directory / "case.yaml"
    case.write_text(
        f"""schema: {CASE_SCHEMA}
name: charged-tube
inputs:
  profile: {{path: {profile}}}
  pqr: {{path: {pqr}, format: pqr}}
geometry: {{reservoir: {{radius_nm: 30.0}}}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 1.0
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics: {{model: pnp-ns, solid_permittivities: {{protein: 20.0, membrane: 3.2}}}}
numerics: {{mesh: {{size_scale: {size_scale}}}}}
"""
        + ("" if charge_block is None else f"charge: {charge_block}\n"),
        encoding="utf-8",
    )
    return case


@dataclass(frozen=True)
class ChargedTube:
    write: Callable[..., Path]
    atoms: tuple[tuple[str, float, float, float, float], ...]
    radius_A: float
    second_frame_e: tuple[float, float]


@pytest.fixture(scope="session")
def charged_tube() -> ChargedTube:
    return ChargedTube(
        write=write_charged_tube,
        atoms=CHARGED_TUBE_ATOMS,
        radius_A=CHARGED_TUBE_RADIUS_A,
        second_frame_e=CHARGED_TUBE_SECOND_FRAME_E,
    )


def cut_2wcd(chain: str, first: int, last: int) -> list[str]:
    import gzip

    with gzip.open(DEPOSITED_2WCD, "rt", encoding="ascii") as handle:
        return [
            line.rstrip("\n")
            for line in handle
            if line.startswith("ATOM")
            and line[21] == chain
            and first <= int(line[22:26]) <= last
            and line[16] in " A"
        ]


@pytest.fixture(scope="session")
def fragment_2wcd() -> Callable[..., object]:
    from nanopnp.structure.ensemble import AlignedEnsemble

    def fragment(first: int, last: int, *, chain: str = "A", frames: int = 1) -> AlignedEnsemble:
        lines = cut_2wcd(chain, first, last)
        positions = np.array(
            [[float(line[30:38]), float(line[38:46]), float(line[46:54])] for line in lines]
        )
        return AlignedEnsemble(
            positions_nm=np.repeat((positions / 10.0)[None], frames, axis=0).astype(np.float32),
            element=np.array([line[76:78].strip() for line in lines]),
            name=np.array([line[12:16].strip() for line in lines]),
            resname=np.array([line[17:20].strip() for line in lines]),
            resid=np.array([int(line[22:26]) for line in lines]),
            icode=np.array([line[26].strip() for line in lines]),
            chain=np.array([chain] * len(lines)),
            header={"frames": {"indices": list(range(frames))}},
        )

    return fragment


PROTONATED_2WCD_CASE = SEED_CASE.replace("name: 2wcd-seed", "name: 2wcd-protonated")


@dataclass(frozen=True)
class Protonated2WCD:
    store: Path
    case: Path
    structure: str
    protonation: str
    seconds: float


@pytest.fixture(scope="session")
def protonated_2wcd(
    prepared_2wcd: Prepared2WCD,
    structure_2wcd: Path,
    tmp_path_factory: pytest.TempPathFactory,
) -> Protonated2WCD:
    import time

    from nanopnp.core.stages import create
    from nanopnp.io.artefact import StageInputs
    from nanopnp.io.store import Store
    from nanopnp.pipeline.case import load_case

    shared = shared_directory(tmp_path_factory)
    root = shared / "2wcd-protonated"
    ready = root / "READY"
    with FileLock(str(shared / "2wcd-protonated.lock")):
        # Seeded once. A later worker that re-seeded it would rewrite files that a
        # worker already past this lock may be copying out (:func:`seeded_protonated_2wcd`);
        # on Windows that copy fails on the open file (WinError 32).
        store = Store(root / "store")
        if not ready.is_file():
            shutil.copytree(
                structure_2wcd / "artefacts", store.root / "artefacts", dirs_exist_ok=True
            )
        case = root / "protonated.case.yaml"
        if not case.is_file():
            case.write_text(PROTONATED_2WCD_CASE.format(pdb=prepared_2wcd.path), encoding="utf-8")
        document = load_case(case)
        structure_stage = create("structure")
        key = structure_stage.key(StageInputs(resolved=resolve(document)))  # type: ignore[attr-defined]
        structure = store.get(key.schema, key.hash)
        assert structure is not None, "the seed holds stage 1 of the prepared 2WCD"
        inputs = StageInputs(resolved=resolve(document), upstream={"structure": structure})
        stage = create("protonation", workspace=root / "workspace", store=store)
        started = time.perf_counter()
        protonation = store.get_or_compute(
            stage.key(inputs),  # type: ignore[attr-defined]
            lambda: stage.run(inputs),
        )
        seconds = time.perf_counter() - started
        ready.write_text("", encoding="utf-8")
    return Protonated2WCD(
        store=store.root,
        case=case,
        structure=structure.hash,
        protonation=protonation.hash,
        seconds=seconds,
    )


@pytest.fixture(scope="session")
def seeded_protonated_2wcd(
    seeded_2wcd: Seed2WCD, protonated_2wcd: Protonated2WCD
) -> Callable[[Path], Path]:

    def seed_store(root: Path) -> Path:
        seeded_2wcd(root)
        shutil.copytree(protonated_2wcd.store / "artefacts", root / "artefacts", dirs_exist_ok=True)
        return root

    return seed_store


CYLINDRICAL_PORE_CASE = (
    f"schema: {CASE_SCHEMA}\n"
    """name: run-probe
inputs:
  mesh:
    path: {mesh_path}
    format: vol
    groups: {{default: interface}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 0.1
  temperature_K: 298.15
  parameters: willems2020_nacl
  corrections:
    diffusivity:  {{model: none}}
    mobility:     {{model: none}}
    viscosity:    {{model: none}}
    permittivity: {{model: none}}
    density:      {{model: none}}
boundary_conditions:
  bias_V: 0.02
  ground: cis
physics:
  model: epnp-ns
  solid_permittivities: {{membrane: 3.2}}
numerics:
  continuation: default_ladder
  stabilisation: none
outputs: [current, transport_numbers, eof_rate]
"""
)


@pytest.fixture(scope="session")
def cylindrical_pore_case(tmp_path_factory: pytest.TempPathFactory) -> Path:
    from nanopnp.mesh.primitives import CylindricalPoreGeometry

    shared = shared_directory(tmp_path_factory)
    pore_dir = shared / "cylindrical_pore"
    lock = shared / "cylindrical_pore.lock"
    mesh_path = pore_dir / "pore.vol"
    case_path = pore_dir / "case.yaml"

    with FileLock(str(lock)):
        if not case_path.is_file():
            pore_dir.mkdir(parents=True, exist_ok=True)
            if not mesh_path.is_file():
                staging_mesh = mesh_path.with_suffix(f".{os.getpid()}.vol")
                pore = CylindricalPoreGeometry(
                    pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0
                )
                pore.generate(maxh_nm=4.0, wall_h_nm=1.0).ngmesh.Save(str(staging_mesh))
                staging_mesh.replace(mesh_path)
            staging_case = case_path.with_suffix(f".{os.getpid()}.yaml")
            staging_case.write_text(
                CYLINDRICAL_PORE_CASE.format(mesh_path=mesh_path), encoding="utf-8"
            )
            staging_case.replace(case_path)

    return case_path


# Reference COMSOL mesh: SPECIFICATION.md section 5.2.2.
VAL05_REFERENCE_TRIANGLES = 120_917

# Reference mesh quality: SPECIFICATION.md section 5.2.2;
# knowledge/09-comsol-reference-settings/index.md.
VAL05_REFERENCE_MIN_QUALITY = 0.6378

# Reference mesh quality: SPECIFICATION.md section 5.2.2.
VAL05_REFERENCE_MEAN_QUALITY = 0.9765

VAL05_FROZEN_CASE = (
    f"schema: {CASE_SCHEMA}\n"
    """name: {name}
{source}electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 1.0
  parameters: willems2020_nacl
  corrections:
    diffusivity:  {{model: none}}
    mobility:     {{model: none}}
    viscosity:    {{model: none}}
    permittivity: {{model: none}}
    density:      {{model: none}}
    steric:       {{model: none}}
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics:
  model: pnp
  flow: false
  variable_density: false
  inertia: false
  solid_permittivities: {{protein: 20.0, membrane: 3.2}}
numerics:
  continuation: none
  stabilisation: none
  mesh: {{size_scale: {size_scale}}}
outputs: [current]
"""
)


@dataclass(frozen=True)
class D10Figures:
    triangles: int = VAL05_REFERENCE_TRIANGLES
    min_quality: float = VAL05_REFERENCE_MIN_QUALITY
    mean_quality: float = VAL05_REFERENCE_MEAN_QUALITY


@pytest.fixture(scope="session")
def reference_triangles() -> int:
    return VAL05_REFERENCE_TRIANGLES


@pytest.fixture(scope="session")
def d10_figures() -> D10Figures:
    return D10Figures()


@pytest.fixture(scope="session")
def val05_frozen_case() -> str:
    return VAL05_FROZEN_CASE


@pytest.fixture(scope="session")
def as_yaml() -> Callable[[object], str]:
    return lambda record: yaml.safe_dump(record.model_dump(mode="json"), sort_keys=False)  # type: ignore[attr-defined]


@dataclass(frozen=True)
class Exclusion2WCD:
    offset_nm: float = 0.25
    delta_nm: float = 0.15
    h_c_nm: float = 0.05


@pytest.fixture(scope="session")
def exclusion_2wcd() -> Exclusion2WCD:
    return Exclusion2WCD()


STABILITY_GOLDEN = Path(__file__).parent / "tier2" / "data" / "number_stability.json"

STABILITY_RECORD = "NANOPNP_RECORD_STABILITY"

STABILITY_QUANTITIES = ("current_A", "currents_A", "conductance_S", "transport_number", "eof_m3_s")

STABILITY_PROPERTY = "number_stability"


def stability_values(
    quantities: Mapping[str, object], extra: Mapping[str, float] | None = None
) -> dict[str, float]:
    values: dict[str, float] = {}
    for name in STABILITY_QUANTITIES:
        value = quantities.get(name)
        if isinstance(value, Mapping):
            values.update({f"{name}[{species}]": float(v) for species, v in value.items()})
        elif value is not None:
            values[name] = float(value)  # type: ignore[arg-type]
    values.update(extra or {})
    return values


@dataclass(frozen=True)
class NumberStability:
    record_property: Callable[[str, object], None]

    values = staticmethod(stability_values)

    def __call__(
        self,
        walk: str,
        mesh_hash: str,
        quantities: Mapping[str, object],
        extra: Mapping[str, float] | None = None,
    ) -> None:
        from nanopnp.validation.stability import StabilityGolden, compare, entry_for, environment

        values = stability_values(quantities, extra)
        where = environment()
        directory = os.environ.get(STABILITY_RECORD)
        if directory:
            if os.environ.get("CI"):
                pytest.fail(f"{STABILITY_RECORD} is refused under CI: a gate never records itself")
            zero = sorted(q for q, v in values.items() if v == 0.0 or not math.isfinite(v))
            if zero:
                pytest.fail(f"{walk}: {zero} are zero or not finite; a golden cannot hold them")
            path = Path(directory) / f"{walk}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(entry_for(walk, mesh_hash, values, where) + "\n", encoding="utf-8")
            return
        verdict = compare(StabilityGolden.read(STABILITY_GOLDEN), walk, mesh_hash, values, where)
        for quantity, drift in verdict.drifts.items():
            self.record_property(STABILITY_PROPERTY, (walk, verdict.mode, quantity, drift))
        if verdict.failure is not None:
            pytest.fail(verdict.failure, pytrace=False)


@pytest.fixture
def number_stability(record_property: Callable[[str, object], None]) -> NumberStability:
    return NumberStability(record_property)


def pytest_terminal_summary(terminalreporter: pytest.TerminalReporter) -> None:
    largest: dict[str, tuple[float, str, str]] = {}
    for reports in terminalreporter.stats.values():
        for report in reports:
            for name, value in getattr(report, "user_properties", ()):
                if name != STABILITY_PROPERTY:
                    continue
                walk, mode, quantity, drift = value
                if walk not in largest or drift > largest[walk][0]:
                    largest[walk] = (float(drift), str(mode), str(quantity))
    if largest:
        from nanopnp.validation.stability import environment

        terminalreporter.section(f"number stability on {environment()}")
        for walk, (drift, mode, quantity) in sorted(largest.items()):
            terminalreporter.write_line(
                f"{walk}: {mode}, largest relative drift {drift:.3e} ({quantity})"
            )

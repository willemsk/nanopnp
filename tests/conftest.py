"""Fixtures every tier shares: the vendored 2WCD, rigidly prepared (WP19 D14).

The wwPDB entry 2WCD as deposited holds two dodecamers (chains A-L and M-X) in
the crystal frame, where the pore axis is 22.9 degrees from z and +z points to
*trans*, so stage 1 refuses it by its orientation gate (the section 5.3.1 NOTE on
``structure:``). ``prepared_2wcd`` is chains A-L moved rigidly into a frame the
stage admits: *cis* up, tilted 4 degrees and shifted, so the frame transform is
not the identity. Preparing a structure is outside the pipeline, so this is a
test-time move, as the WP18 Outcomes record.

It moved here from ``tests/tier1/test_structure_stage.py`` because stages 2 and 3
need it at Tiers 1 and 2, and WP22's VAL-05 needs it next. MDAnalysis is imported
inside the fixtures: a conftest at the root is loaded by every run, and the
registry tests assert that listing the stages imports no extra.

Stages 2 and 3 of the prepared entry take about 32 s, and six Tier-2 files walk
through them. ``seeded_2wcd`` computes them once per session, in a directory every
``pytest-xdist`` worker shares, and the object it returns copies the result into
a test's own fresh store. It runs on to stage 6 (WP33 D2): the contour, the
registration and the 0.15 M default-size mesh that four modules walk to. The
store is content-addressed, so a test that reads a seeded artefact reads the
bytes its own walk would have written, computed by the same code in the same
session; every stage the seed does not key alike still runs in the test. A test
that asserts a stage was *computed* rather than found -- VER-55's cold build, the
example executors, VER-49's budget -- does not take the seed.

The ``gmsh_module`` fixture is the one way a test reaches the optional Gmsh
backend (WP23 D11). It skips, naming the error, where ``gmsh`` does not import,
and fails instead under ``NANOPNP_REQUIRE_GMSH=1``, which CI sets on the legs
where it does: a backend whose every test can skip unseen is untested.
"""

from __future__ import annotations

import json
import logging
import math
import os
import pickle
import platform
import shutil
import sys
import warnings
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

import numpy as np
import pytest
from filelock import FileLock

if TYPE_CHECKING:
    import MDAnalysis as mda  # noqa: N813 - the alias the library documents
    import ngsolve

logger = logging.getLogger(__name__)

STRUCTURES = Path(__file__).parent / "data" / "structures"
DEPOSITED_2WCD = STRUCTURES / "2wcd.pdb.gz"
DODECAMER = "A,B,C,D,E,F,G,H,I,J,K,L"

REQUIRE_GMSH = "NANOPNP_REQUIRE_GMSH"
"""Set to ``1`` where ``gmsh`` must import, so its tests fail rather than skip (WP23 D11)."""

EXTENDED = "--extended"
"""Selects the ``extended`` tests, which the development selection leaves out (section 7.6)."""


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        EXTENDED,
        action="store_true",
        help="also run the tests marked extended: the executed examples and the 2WCD "
        "walks, which CI gates on every push (SPECIFICATION.md section 7.6)",
    )


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Leave out the ``extended`` tests unless asked for, or their file is named.

    An ``extended`` test is an end-to-end walk -- an executed example or the 2WCD
    entry through the pipeline -- whose claims CI gates on every push with
    ``--extended``. The development selection, which ``uv run pytest`` and the
    commit hook run, leaves them out; a file or test named on the command line runs
    whole, so ``uv run pytest tests/tier2/test_charge_2wcd.py`` needs no flag.

    A ``slow`` test is never in the development selection, which ``addopts``
    already bounds to ``not slow``: it is selected only by an explicit
    ``-m slow``, and that request is kept, so the recorded measurements of an
    ``extended`` file still run under CLAUDE.md's ``uv run pytest -m slow``.
    """
    if config.getoption(EXTENDED):
        return
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


def import_gmsh() -> ModuleType:
    """Import ``gmsh``, or skip naming why; under :data:`REQUIRE_GMSH` fail instead.

    ``OSError`` as well as ``ImportError``: the wheel dlopens X and GL at import
    and raises ``OSError: libGLU.so.1`` in a bare container, which
    ``pytest.importorskip`` turns into an error rather than a skip
    (``.knowledge/07-software-stack.md`` section 5).
    """
    try:
        import gmsh
    except (ImportError, OSError) as error:  # pragma: no cover - environment-dependent
        reason = f"gmsh does not import: {type(error).__name__}: {error}"
        if os.environ.get(REQUIRE_GMSH) == "1":
            pytest.fail(f"{REQUIRE_GMSH}=1 and {reason}")
        pytest.skip(reason)
    return gmsh


@pytest.fixture
def gmsh_module() -> ModuleType:
    """Return the ``gmsh`` module, through :func:`import_gmsh`."""
    return import_gmsh()


def require_apbs() -> None:
    """Skip naming why APBS cannot run here; under ``NANOPNP_REQUIRE_APBS=1`` fail instead.

    WP29 D12, the rule of WP23 D11: CI sets the variable on the Linux and macOS
    legs, where the ``apbs-binary`` wheel exists, so VAL-06 cannot skip unseen
    there; Windows has no wheel and skips, named, under ``-rs``.
    """
    from nanopnp.validation.apbs import REQUIRE_APBS, apbs_available

    reason = apbs_available()
    if reason is None:
        return
    if os.environ.get(REQUIRE_APBS) == "1":  # pragma: no cover - environment-dependent
        pytest.fail(f"{REQUIRE_APBS}=1 and {reason}")
    pytest.skip(reason)  # pragma: no cover - environment-dependent


@pytest.fixture(scope="session")
def apbs() -> None:
    """Require APBS through :func:`require_apbs`: a test or fixture taking this one runs it."""
    require_apbs()


PREPARED_TILT_DEG = 4.0
"""The tilt the prepared copy is left with, so the frame transform is not the identity."""

PREPARED_SHIFT_NM = (0.6, -0.35, 1.2)
"""The prepared copy's shift, so the axis does not pass through the file's origin."""


@dataclass(frozen=True)
class Prepared2WCD:
    """Chains A-L of 2WCD written to a PDB, and the rigid move that put them there."""

    path: Path
    tilt_deg: float
    rotation: np.ndarray
    """Applied to the deposited coordinates: ``x' = R x + t``."""
    shift_nm: np.ndarray


def rotation_about(axis: np.ndarray, angle: float) -> np.ndarray:
    """Return the rotation by ``angle`` (radians) about ``axis``."""
    k = np.asarray(axis, dtype=np.float64) / np.linalg.norm(axis)
    skew = np.array([[0.0, -k[2], k[1]], [k[2], 0.0, -k[0]], [-k[1], k[0], 0.0]])
    return np.eye(3) + math.sin(angle) * skew + (1.0 - math.cos(angle)) * (skew @ skew)


def _prepared_rotation(group: mda.AtomGroup) -> np.ndarray:
    """Return a rotation taking the deposited dodecamer's axis to z, *cis* up, then tilting it 4°.

    Which end is *cis* is read from the structure, not assumed: the ClyA cap is the
    wide end (``.knowledge/04-clya-geometry-and-charge.md``). In the deposited
    frame the axis signed to +z has its narrow end up, so +z there points to
    *trans* — the same finding as a Kabsch superposition of chains A-L onto the
    author's aligned copy, which maps it to -z (WP18 Outcomes).
    """
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
    """Chains A-L of the deposited 2WCD, protein only, in the crystal frame."""
    from nanopnp.structure.read import load_universe

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        universe = load_universe(DEPOSITED_2WCD)
    return universe.select_atoms("protein and chainID " + " ".join(DODECAMER.split(",")))


def shared_directory(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Return a directory every ``pytest-xdist`` worker of this session shares.

    Each worker's base temporary directory is a sibling under one session root, so
    that root is the shared one; without workers it is the base itself. Anything
    written here must be written under a :class:`~filelock.FileLock`, once.
    """
    base = tmp_path_factory.getbasetemp()
    return base.parent if os.environ.get("PYTEST_XDIST_WORKER") else base


@pytest.fixture(scope="session")
def prepared_2wcd(
    dodecamer_2wcd: mda.AtomGroup, tmp_path_factory: pytest.TempPathFactory
) -> Prepared2WCD:
    """Chains A-L of 2WCD, rigidly moved to *cis* up, tilted 4° and shifted: a prepared file.

    Written once per session to :func:`shared_directory`, so every worker's stage 1
    reads one file and keys one artefact (stage 1 keys the source by its SHA-256).
    """
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


SEED_CASE = """\
schema: nanopnp/case/v2
name: 2wcd-seed
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
"""The structure block and the default ``geometry.density`` every 2WCD file walks.

Stages 1 to 3 key on these alone -- the source's digest, the point group and the
density settings -- so a test's case with its own name, electrolyte and physics
reads the seeded artefacts, and a case that changes one of them simply misses the
seed and computes its own."""

SEED_UPTO = "mesh"
"""The last seeded stage (WP33 D2).

Stages 2 and 3 are the 32 s. Stage 4 keys on the same block as they do, so it is
seeded with them, and so are stages 5 and 6 at the C-alpha registration
(:attr:`Seed2WCD.centre_z_nm`) and the default sizes at 0.15 M: that 8 s mesh is
the one the ``charge``, ``val06``, ``pipeline`` and ``val05`` modules all walk to,
measured to key alike. A case that differs from :data:`SEED_CASE` in anything a
stage keys on misses that stage's seed and computes its own."""


def _structure_case(directory: Path, pdb: Path, name: str = "seed.case.yaml") -> Path:
    """Write :data:`SEED_CASE` for ``pdb`` into ``directory`` and return its path."""
    case = directory / name
    case.write_text(SEED_CASE.format(pdb=pdb), encoding="utf-8")
    return case


@pytest.fixture(scope="session")
def structure_2wcd(prepared_2wcd: Prepared2WCD, tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Return a shared store holding stage 1 of the prepared 2WCD, computed once per session.

    Both seeds start from it, so neither waits on the other (WP33 D2): the
    protonation reads only stage 1 (``charge/protonation.py``), and under
    ``pytest-xdist`` PROPKA runs in one worker while another computes stages 2
    to 6. Copied out, never handed out.
    """
    from nanopnp.io.run import run_case
    from nanopnp.io.store import Store

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
    """Seeds a fresh store with stages 1 to 6 of the prepared 2WCD; called like a function.

    ``seed(root)`` copies the seeded artefacts into the store at ``root`` and
    returns ``root``; ``runs/`` stays the test's own. The shared seed itself is
    never handed out, so no test can write into it.
    """

    store: Path
    """The shared seed store. Read it only through a call."""
    centre_z_nm: float
    """The C-alpha-centroid registration of WP22 D6, ``register_by_centroid``'s."""

    @property
    def geometry(self) -> str:
        """Return the ``geometry:`` block that registers the dodecamer, as the modules write it."""
        return f"geometry: {{membrane: {{centre_z_nm: {self.centre_z_nm!r}}}}}\n"

    def __call__(self, root: Path) -> Path:
        """Copy the seeded artefacts into the store at ``root`` and return ``root``."""
        shutil.copytree(self.store / "artefacts", root / "artefacts", dirs_exist_ok=True)
        return root


def register_2wcd(structure_artefact: object) -> float:
    """Return the C-alpha-centroid registration (WP22 D6) of a stage-1 artefact of 2WCD."""
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
    """Return a :class:`Seed2WCD`: stages 1 to 6 of the prepared 2WCD, computed once per session.

    The first worker to ask computes them under a lock, from the stage-1 store,
    and the others wait and reuse the result. Stage 4 runs on the seed case as
    it stands; the registration is read off stage 1, and stages 5 and 6 run on
    the seed case with that ``geometry:`` block added.
    """
    from nanopnp.io.run import run_case
    from nanopnp.io.store import Store

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
    """Return a function giving a fresh copy of the WP8 ClyA reference mesh (WP33 D10).

    ``ReferenceGeometry.from_fixture().generate(check_quality=False)``, at the
    section 5.2.2 size fields: about 7 s, and five modules built it. It is meshed
    once per session under a lock and pickled into :func:`shared_directory`;
    each call unpickles a copy of its own, so no test can change another's mesh.
    A pickle and not a ``.vol``: NGSolve's pickle round-trips the vertices to the
    bit, and the ``.vol`` text moves them by up to 5.6e-17 nm, which changes the
    mesh's geometry digest (measured, WP33 Outcomes).
    """
    shared = shared_directory(tmp_path_factory)
    path = shared / "reference-mesh" / "mesh.pickle"
    with FileLock(str(shared / "reference-mesh.lock")):
        if not path.is_file():
            from nanopnp.mesh.reference import ReferenceGeometry

            mesh = ReferenceGeometry.from_fixture().generate(check_quality=False)
            path.parent.mkdir(parents=True, exist_ok=True)
            staging = path.with_suffix(f".{os.getpid()}.pickle")
            staging.write_bytes(pickle.dumps(mesh))
            staging.replace(path)

    def load() -> ngsolve.Mesh:
        """Return a copy of the reference mesh, unpickled from the session's file."""
        mesh: ngsolve.Mesh = pickle.loads(path.read_bytes())
        return mesh

    return load


SYNTHETIC_RESIDUES = 8
"""Residues per chain of :func:`synthetic_c12`: eight alanines, 40 heavy atoms."""

_ALANINE_NM: dict[str, tuple[float, float, float]] = {
    # A rough alanine about its C-alpha, in nm: bond lengths of 0.13-0.15 nm.
    "N": (-0.12, 0.06, -0.05),
    "CA": (0.0, 0.0, 0.0),
    "C": (0.12, 0.07, 0.05),
    "O": (0.13, 0.19, 0.06),
    "CB": (0.0, -0.15, 0.03),
}


def synthetic_c12_positions_nm(turn_rad: float = 0.0) -> tuple[np.ndarray, list[str], list[str]]:
    """Return an exact C12 assembly of 12 chains x 8 alanines, turned by ``turn_rad`` about z.

    Each chain winds from r = 2.6 to 3.3 nm while rising 0.45 nm per residue, so
    the assembly is a corrugated barrel with no mirror symmetry and no axial
    symmetry beyond its C12. Returns the ``(atoms, 3)`` positions in nm, and each
    atom's name and chain.
    """
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
    """Write :func:`synthetic_c12_positions_nm`'s atoms as a PDB, elements included."""
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
    """Write the exact synthetic C12 of :func:`synthetic_c12_positions_nm` as a PDB, axis on z."""
    positions, names, _ = synthetic_c12_positions_nm()
    return write_synthetic_pdb(tmp_path_factory.mktemp("synthetic") / "c12.pdb", positions, names)


@pytest.fixture(scope="session")
def c12_assembly() -> Callable[[float], tuple[np.ndarray, list[str], list[str]]]:
    """Return :func:`synthetic_c12_positions_nm`, for a test that turns the assembly itself."""
    return synthetic_c12_positions_nm


TUBE_NAMES = ("N", "CA", "C", "O", "CB")
"""The atom names of :func:`write_tube_pdb`'s alanine-like residues, one per slot."""


def write_tube_pdb(path: Path) -> Path:
    """Write a synthetic C12 tube: per chain, five atoms on each of three rings over nine layers.

    Rings of radius 2.7, 3.0 and 3.3 nm, layers 0.3 nm apart from z = 0, so stages
    1 to 4 run on it in seconds. Moved here from ``tests/tier1/test_contour.py``
    because the WP24 geometry and assess tests build on it too.
    """
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
    """Return :func:`write_tube_pdb`'s file, written once per session."""
    return write_tube_pdb(tmp_path_factory.mktemp("tube") / "tube.pdb")


def write_parallelogram_profile(path: Path, *, citation: str = "tests/conftest.py") -> Path:
    """Write a slanted body 1 nm wide across the slab as a ``profile/v1`` document.

    Meshed in a 30 nm reservoir at ``size_scale`` 20, it generates in a fraction of
    a second (``tests/tier1/test_mesh_generate.py``). The nanopnp imports are here
    for the reason the module docstring gives for MDAnalysis's.
    """
    from nanopnp.mesh.profile import (
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
    """Return :func:`write_parallelogram_profile`'s file, written once per session."""
    return write_parallelogram_profile(tmp_path_factory.mktemp("parallelogram") / "profile.yaml")


CHARGED_TUBE_ATOMS: tuple[tuple[str, float, float, float, float], ...] = (
    ("NZ", 32.5, 0.0, -15.0, 1.0),
    ("OE1", 0.0, 47.5, 15.0, -2.0),
)
"""The charged tube's two atoms: name, ``x, y, z`` in Å, and the charge of frame 0 in e.

On the parallelogram's midline, at ``(r, z) = (3.25, -1.5)`` and ``(4.75, 1.5)`` nm,
so each sits half a nanometre inside the body; the second off the ``x`` axis, so a
picture that dropped ``y`` would put it at ``r = 0`` (WP31's VER-60). Opposite in
sign and unequal, because a net-neutral deposit is refused (WP28 D6).
"""

CHARGED_TUBE_RADIUS_A = 1.5
"""Their radius: ``w = 0.75`` Å, so an areal peak sits ``w^2/2r`` < 0.001 nm off its atom."""

CHARGED_TUBE_SECOND_FRAME_E: tuple[float, float] = (1.0, -3.0)
"""The second frame's charges, where a two-frame tube is asked for: ``Q_net`` -2 e."""


def write_charged_tube(
    directory: Path, *, frames: int = 1, size_scale: float = 5.0, charge_block: str | None = None
) -> Path:
    """Write the cheapest case that deposits a charge, and return its path (WP31's VER-60).

    The parallelogram through ``inputs.profile`` in a 30 nm reservoir, with an
    ``inputs.pqr`` of :data:`CHARGED_TUBE_ATOMS`. A walk through stage 7 takes
    about two seconds. ``size_scale`` 5 rather than the 20 of the uncharged hook
    case: at 20 the deployed field's worst plane is off by 5.7e-3 of ``Q_net``
    and at 10 by 1.9e-3, both refused by PHY-19's 1e-3 gate; at 5 it is 1.2e-4.

    Parameters
    ----------
    frames
        1, or 2 for a PQR whose second ``MODEL`` carries
        :data:`CHARGED_TUBE_SECOND_FRAME_E`.
    charge_block
        A ``charge:`` block as a YAML flow mapping, such as
        ``"{dielectric_transition_nm: 0.2}"``; none is written by default.
    """
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
        f"""schema: nanopnp/case/v2
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
    """What a test of the charged tube needs: the writer, and the atoms it writes."""

    write: Callable[..., Path]
    atoms: tuple[tuple[str, float, float, float, float], ...]
    radius_A: float
    second_frame_e: tuple[float, float]


@pytest.fixture(scope="session")
def charged_tube() -> ChargedTube:
    """Return :func:`write_charged_tube` and its atoms; each test writes into its own directory."""
    return ChargedTube(
        write=write_charged_tube,
        atoms=CHARGED_TUBE_ATOMS,
        radius_A=CHARGED_TUBE_RADIUS_A,
        second_frame_e=CHARGED_TUBE_SECOND_FRAME_E,
    )


def cut_2wcd(chain: str, first: int, last: int) -> list[str]:
    """Return the ATOM lines of residues ``first`` to ``last`` of one chain of the deposited 2WCD.

    Read by columns from the vendored file, so a fragment needs neither MDAnalysis
    nor stage 1, and the coordinates are the crystal frame's to 0.001 Å.
    """
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
    """Return a function cutting a fragment of 2WCD into a stage-1 ensemble (WP27).

    ``fragment(first, last, chain="A", frames=1)`` returns an
    :class:`~nanopnp.structure.ensemble.AlignedEnsemble` of those residues, heavy
    atoms only as deposited, in the crystal frame, with ``frames`` identical
    frames; a test perturbs one to make the frames differ. No new vendored file:
    the fragments are cut from ``2wcd.pdb.gz`` (WP27 work item 6).
    """
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
"""The seed case: the prepared dodecamer at the default pH 7.5, CHARMM and PROPKA."""


@dataclass(frozen=True)
class Protonated2WCD:
    """The prepared 2WCD dodecamer protonated once per session (WP27 D17)."""

    store: Path
    """A store holding stage 1 and the protonation artefact."""
    case: Path
    """The case that keys them."""
    structure: str
    """Stage 1's hash."""
    protonation: str
    """The protonation artefact's hash."""
    seconds: float
    """Wall time of the protonation, or of reading it from the shared store."""


@pytest.fixture(scope="session")
def protonated_2wcd(
    prepared_2wcd: Prepared2WCD,
    structure_2wcd: Path,
    tmp_path_factory: pytest.TempPathFactory,
) -> Protonated2WCD:
    """Protonate the prepared 2WCD dodecamer with PROPKA once per session (WP27 D17).

    Through the stage API rather than a walk, so that stages 2 to 6 are not paid
    for: stage 1 comes from :func:`structure_2wcd`, and the ``protonation`` stage
    runs on it into a store every ``pytest-xdist`` worker shares, under a lock,
    about a minute, while another worker may be computing :func:`seeded_2wcd`
    (WP33 D2). WP28 and WP29 reuse it.
    """
    import time

    from nanopnp.core.stages import create
    from nanopnp.io.artefact import StageInputs
    from nanopnp.io.case import load_case
    from nanopnp.io.store import Store

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
        key = structure_stage.key(StageInputs(case=document))  # type: ignore[attr-defined]
        structure = store.get(key.schema, key.hash)
        assert structure is not None, "the seed holds stage 1 of the prepared 2WCD"
        inputs = StageInputs(case=document, upstream={"structure": structure})
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
    """Return a function seeding a fresh store with stages 1 to 6 and the protonation of 2WCD.

    WP28 D14: a ``structure:`` case whose model declares a fixed charge walks both
    halves of stage 7, so a charged walk reads the session's protonation from its
    store rather than paying PROPKA again. The protonation key is the structure's
    hash and the protonation block, so any case with the seed's structure block and
    the default ``charge.protonation`` reads it. The shared store is copied, never
    handed out.
    """

    def seed_store(root: Path) -> Path:
        """Copy both seeds' artefacts into ``root``; ``runs/`` stays the test's own."""
        seeded_2wcd(root)
        shutil.copytree(protonated_2wcd.store / "artefacts", root / "artefacts", dirs_exist_ok=True)
        return root

    return seed_store


# -- VER-62: the number-stability golden (WP35 D12-D16; section 8.2.7 G10) ----------

STABILITY_GOLDEN = Path(__file__).parent / "tier2" / "data" / "number_stability.json"
"""The golden every gated walk computing a current asserts (WP35 D13)."""

STABILITY_SCHEMA = "nanopnp/golden/stability/v1"

STABILITY_TOLERANCE = 1e-8
"""Relative, on every value of a walk within its key (G10; WP35 Design section 2)."""

STABILITY_RECORD = "NANOPNP_RECORD_STABILITY"
"""Names a directory: each assertion writes ``<dir>/<walk>.json`` and passes (WP35 D14)."""

STABILITY_QUANTITIES = ("current_A", "currents_A", "conductance_S", "transport_number", "eof_m3_s")
"""The quantities a walk's golden holds, each scalar of each (WP35 D12).

``route_agreement`` is left out: it is a difference of two routes, and the relative
drift of a difference amplifies round-off by the inverse of its size."""

STABILITY_PROPERTY = "number_stability"
"""The ``record_property`` name of each ``(walk, quantity, relative drift)`` (WP35 D16)."""


def stability_key() -> str:
    """Return the running platform's golden key, ``<sys.platform>-<machine>`` (WP35 D13)."""
    return f"{sys.platform}-{platform.machine()}"


def stability_values(
    quantities: Mapping[str, object], extra: Mapping[str, float] | None = None
) -> dict[str, float]:
    """Return the golden's scalars of one run's quantities, flattened as ``currents_A[Na+]``."""
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
    """Asserts one walk's values against the golden, or records them (WP35 D13, D14)."""

    record_property: Callable[[str, object], None]

    values = staticmethod(stability_values)
    """:func:`stability_values`, for a walk that combines several runs into one entry."""

    def __call__(
        self,
        walk: str,
        mesh_hash: str,
        quantities: Mapping[str, object],
        extra: Mapping[str, float] | None = None,
    ) -> None:
        """Assert ``walk``'s mesh hash exactly and each value at 1e-8 relative, or record them.

        The values are :func:`stability_values` of the run's ``quantities``, and
        ``extra`` adds a walk's own scalars, such as stage 7's ``q_mesh_e``.

        Recording refuses a zero or non-finite value; a key with no entry fails,
        printing the entry to commit once the values have been checked.
        """
        values = stability_values(quantities, extra)
        entry = {"mesh_hash": mesh_hash, "values": {q: float(v).hex() for q, v in values.items()}}
        keys = json.loads(STABILITY_GOLDEN.read_text(encoding="utf-8"))["keys"]
        # The key this interpreter asserts against, and so the one it records under:
        # once D13 splits a key by Python, a re-pin must reach the split entry.
        key = stability_key()
        python = f"{key}-py3.{sys.version_info.minor}"
        chosen = python if python in keys else key
        directory = os.environ.get(STABILITY_RECORD)
        if directory:
            if os.environ.get("CI"):
                pytest.fail(f"{STABILITY_RECORD} is refused under CI: a gate never records itself")
            zero = sorted(q for q, v in values.items() if v == 0.0 or not math.isfinite(v))
            if zero:
                pytest.fail(f"{walk}: {zero} are zero or not finite; a golden cannot hold them")
            path = Path(directory) / f"{walk}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            record = {"schema": STABILITY_SCHEMA, "key": chosen, "walk": walk, **entry}
            path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            return
        expected = keys.get(chosen, {}).get(walk)
        if expected is None:
            printed = json.dumps({chosen: {walk: entry}}, indent=2, sort_keys=True)
            pytest.fail(
                f"no number-stability golden for walk {walk!r} on key {chosen!r}; after "
                f"checking these values, commit this entry to {STABILITY_GOLDEN.name}:\n{printed}"
            )
        assert mesh_hash == expected["mesh_hash"], (
            f"{walk} on {chosen}: the deployed mesh moved ({mesh_hash} against the golden's "
            f"{expected['mesh_hash']}), so the golden's numbers do not apply; investigate the "
            "mesh before the numbers (section 8.2.7 G10)"
        )
        golden_values = {q: float.fromhex(v) for q, v in expected["values"].items()}
        assert set(values) == set(golden_values), (
            f"{walk}: the walk computes {sorted(values)}, the golden holds {sorted(golden_values)}"
        )
        misses = []
        for quantity, value in sorted(values.items()):
            reference = golden_values[quantity]
            drift = abs(value - reference) / abs(reference)
            self.record_property(STABILITY_PROPERTY, (walk, quantity, drift))
            if not abs(value - reference) <= STABILITY_TOLERANCE * abs(reference):
                misses.append(f"{quantity}: {value!r} against {reference!r}, drift {drift:.3e}")
        assert not misses, (
            f"{walk} on {chosen} moved beyond {STABILITY_TOLERANCE:g} relative (section 8.2.7 "
            "G10): investigate, then revert, or rule it a deliberate fix that amends its clause "
            "and re-pins the golden in the same commit\n" + "\n".join(misses)
        )


@pytest.fixture
def number_stability(record_property: Callable[[str, object], None]) -> NumberStability:
    """Return the VER-62 assertion; a walk calls it as ``number_stability("<walk>", ...)``."""
    return NumberStability(record_property)


def pytest_terminal_summary(terminalreporter: pytest.TerminalReporter) -> None:
    """Print the largest VER-62 drift per walk, which works under xdist (WP35 D16)."""
    largest: dict[str, tuple[float, str]] = {}
    for reports in terminalreporter.stats.values():
        for report in reports:
            for name, value in getattr(report, "user_properties", ()):
                if name != STABILITY_PROPERTY:
                    continue
                walk, quantity, drift = value
                if walk not in largest or drift > largest[walk][0]:
                    largest[walk] = (float(drift), str(quantity))
    if largest:
        terminalreporter.section(f"number stability on {stability_key()}")
        for walk, (drift, quantity) in sorted(largest.items()):
            terminalreporter.write_line(f"{walk}: largest relative drift {drift:.3e} ({quantity})")

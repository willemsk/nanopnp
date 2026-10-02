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
``pytest-xdist`` worker shares, and the function it returns copies the result
into a test's own fresh store. The store is content-addressed, so a test that
reads a seeded artefact reads the bytes its own walk would have written, computed
by the same code in the same session; every stage from 4 on still runs in the
test. A test that asserts a stage was *computed* rather than found -- VER-55's
cold build -- does not take the seed.

The ``gmsh_module`` fixture is the one way a test reaches the optional Gmsh
backend (WP23 D11). It skips, naming the error, where ``gmsh`` does not import,
and fails instead under ``NANOPNP_REQUIRE_GMSH=1``, which CI sets on the legs
where it does: a backend whose every test can skip unseen is untested.
"""

from __future__ import annotations

import logging
import math
import os
import shutil
import warnings
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

import numpy as np
import pytest
from filelock import FileLock

if TYPE_CHECKING:
    import MDAnalysis as mda  # noqa: N813 - the alias the library documents

logger = logging.getLogger(__name__)

STRUCTURES = Path(__file__).parent / "data" / "structures"
DEPOSITED_2WCD = STRUCTURES / "2wcd.pdb.gz"
DODECAMER = "A,B,C,D,E,F,G,H,I,J,K,L"

REQUIRE_GMSH = "NANOPNP_REQUIRE_GMSH"
"""Set to ``1`` where ``gmsh`` must import, so its tests fail rather than skip (WP23 D11)."""


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

SEED_UPTO = "symmetry"
"""The last seeded stage. Stages 2 and 3 are the 32 s; stage 4 and beyond stay each test's."""


@pytest.fixture(scope="session")
def seeded_2wcd(
    prepared_2wcd: Prepared2WCD, tmp_path_factory: pytest.TempPathFactory
) -> Callable[[Path], Path]:
    """Return a function seeding a fresh store with stages 1 to 3 of the prepared 2WCD.

    The stages are computed once per session: the first worker to ask computes them
    under a lock, and the others wait and reuse the result. The function copies
    them into the store root it is given and returns that root; the shared seed
    itself is never handed out, so no test can write into it.
    """
    from nanopnp.io.run import run_case
    from nanopnp.io.store import Store

    shared = shared_directory(tmp_path_factory)
    seed = shared / "2wcd-seed"
    ready = seed / "READY"
    with FileLock(str(shared / "2wcd-seed.lock")):
        if not ready.is_file():
            seed.mkdir(parents=True, exist_ok=True)
            case = seed / "seed.case.yaml"
            case.write_text(SEED_CASE.format(pdb=prepared_2wcd.path), encoding="utf-8")
            run_case(case, store=Store(seed / "store"), upto=SEED_UPTO, write=False)
            ready.write_text("", encoding="utf-8")

    def seed_store(root: Path) -> Path:
        """Copy the seeded artefacts into the store at ``root``; ``runs/`` stays the test's own."""
        shutil.copytree(seed / "store" / "artefacts", root / "artefacts", dirs_exist_ok=True)
        return root

    return seed_store


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
    seeded_2wcd: Callable[[Path], Path],
    tmp_path_factory: pytest.TempPathFactory,
) -> Protonated2WCD:
    """Protonate the prepared 2WCD dodecamer with PROPKA once per session (WP27 D17).

    Through the stage API rather than a walk, so that stages 4 to 6 are not paid
    for: stage 1 comes from the seed, and the ``protonation`` stage runs on it into
    a store every ``pytest-xdist`` worker shares, under a lock, about a minute.
    WP28 and WP29 reuse it.
    """
    import time

    from nanopnp.core.stages import create
    from nanopnp.io.artefact import StageInputs
    from nanopnp.io.case import load_case
    from nanopnp.io.store import Store

    shared = shared_directory(tmp_path_factory)
    root = shared / "2wcd-protonated"
    with FileLock(str(shared / "2wcd-protonated.lock")):
        store = Store(seeded_2wcd(root / "store"))
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
    return Protonated2WCD(
        store=store.root,
        case=case,
        structure=structure.hash,
        protonation=protonation.hash,
        seconds=seconds,
    )


@pytest.fixture(scope="session")
def seeded_protonated_2wcd(protonated_2wcd: Protonated2WCD) -> Callable[[Path], Path]:
    """Return a function seeding a fresh store with stages 1 to 3 and the protonation of 2WCD.

    WP28 D14: a ``structure:`` case whose model declares a fixed charge walks both
    halves of stage 7, so a charged walk reads the session's protonation from its
    store rather than paying PROPKA again. The protonation key is the structure's
    hash and the protonation block, so any case with the seed's structure block and
    the default ``charge.protonation`` reads it. The shared store is copied, never
    handed out.
    """

    def seed_store(root: Path) -> Path:
        """Copy the protonated store's artefacts into ``root``; ``runs/`` stays the test's own."""
        shutil.copytree(protonated_2wcd.store / "artefacts", root / "artefacts", dirs_exist_ok=True)
        return root

    return seed_store

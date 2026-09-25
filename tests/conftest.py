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
"""

from __future__ import annotations

import logging
import math
import warnings
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pytest

if TYPE_CHECKING:
    import MDAnalysis as mda  # noqa: N813 - the alias the library documents

logger = logging.getLogger(__name__)

STRUCTURES = Path(__file__).parent / "data" / "structures"
DEPOSITED_2WCD = STRUCTURES / "2wcd.pdb.gz"
DODECAMER = "A,B,C,D,E,F,G,H,I,J,K,L"

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


@pytest.fixture(scope="session")
def prepared_2wcd(
    dodecamer_2wcd: mda.AtomGroup, tmp_path_factory: pytest.TempPathFactory
) -> Prepared2WCD:
    """Chains A-L of 2WCD, rigidly moved to *cis* up, tilted 4° and shifted: a prepared file."""
    import MDAnalysis as mda  # noqa: N813 - the alias the library documents
    from MDAnalysis.coordinates.memory import MemoryReader

    group = dodecamer_2wcd
    rotation = _prepared_rotation(group)
    shift = np.asarray(PREPARED_SHIFT_NM)
    moved = group.positions @ rotation.T + shift * 10.0
    universe = mda.Merge(group)
    universe.load_new(np.asarray(moved[None], dtype=np.float32), format=MemoryReader)
    path = tmp_path_factory.mktemp("prepared") / "2wcd-prepared.pdb"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        universe.atoms.write(str(path))
    return Prepared2WCD(path=path, tilt_deg=PREPARED_TILT_DEG, rotation=rotation, shift_nm=shift)


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

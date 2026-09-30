"""Prepare the deposited 2WCD entry for nanopnp: one dodecamer, its pore axis on z, *cis* up.

Run from this directory::

    python prepare.py ../../tests/data/structures/2wcd.pdb.gz 2wcd-prepared.pdb

Preparing a structure is the user's job, not the pipeline's: nanopnp's stage 1
refuses a file whose pore axis is more than 10° from z, and never re-orients one
itself. This script is one way to do it, and it deliberately imports nothing
from nanopnp. It needs MDAnalysis and NumPy, which the ``structure`` extra
installs.

What it does, to the dodecamer of chains A-L, protein only:

1. **Estimates the axis.** For a ring of n ≥ 3 identical chains, the covariance
   of the C-alpha positions is unchanged by the rotation by 2π/n about the pore
   axis. So two of its eigenvalues are equal, and the axis is the eigenvector of
   the third. The script refuses when no eigenvalue stands apart from the other
   two. Real chains are not exactly identical, so this is an estimate: it needs
   only to land inside stage 1's 10° gate, and stage 1 then finds the axis
   itself, by superposing the chains on one another.
2. **Signs it.** The wide end of ClyA, the cap, faces *cis*, and nanopnp's +z
   points from *trans* to *cis*. The script compares the mean C-alpha radius of
   the top and bottom fifths along the axis, and points +z at the wider end.
3. **Rotates and places it.** The signed axis is turned onto z, and the C-alpha
   centroid of residues 8-292 is moved to (0, 0, 5.655) nm. That is where the
   centroid of the molecular-dynamics structure sits when the bilayer centre is
   at z = 0, so the case can keep ``geometry.membrane.centre_z_nm`` at its
   default of 0.
"""

from __future__ import annotations

import argparse
import logging
import warnings
from pathlib import Path

import MDAnalysis as mda  # noqa: N813 - the alias the library documents
import numpy as np

log = logging.getLogger("prepare")

CHAINS = "A B C D E F G H I J K L"
"""The first dodecamer of the deposited entry; chains M-X are the second."""

REGISTRATION_RESIDUES = "8:292"
"""The residues whose C-alpha centroid is placed on the axis."""

CENTROID_Z_NM = 5.655
"""Where that centroid goes on z, in nm: the molecular-dynamics structure's, bilayer centre at 0."""

DEGENERACY = 0.25
"""The largest ratio of the closest eigenvalue gap to the spread for which an axis is distinct."""


def pore_axis(calpha: np.ndarray) -> np.ndarray:
    """Return the unit eigenvector of the C-alpha covariance's distinct eigenvalue.

    Raises
    ------
    ValueError
        If the two closest eigenvalues are not much closer to each other than to
        the third, so that no axis stands out.
    """
    values, vectors = np.linalg.eigh(np.cov(calpha.T))
    low, high = values[1] - values[0], values[2] - values[1]
    spread = values[2] - values[0]
    if spread <= 0.0 or min(low, high) / spread > DEGENERACY:
        raise ValueError(
            f"the C-alpha covariance has eigenvalues {np.round(values / 100.0, 3).tolist()} nm²; "
            "none stands apart from the other two, so there is no pore axis to estimate"
        )
    axis = vectors[:, 2] if low < high else vectors[:, 0]
    return axis / np.linalg.norm(axis)


def signed_to_cis(calpha: np.ndarray, axis: np.ndarray) -> np.ndarray:
    """Return ``axis`` pointing at the wider end of the assembly, the ClyA cap."""
    centred = calpha - calpha.mean(axis=0)
    height = centred @ axis
    radius = np.linalg.norm(centred - np.outer(height, axis), axis=1)
    top = radius[height > np.quantile(height, 0.8)].mean()
    bottom = radius[height < np.quantile(height, 0.2)].mean()
    log.info("mean C-alpha radius %.2f nm at +axis, %.2f nm at -axis", top / 10, bottom / 10)
    return axis if top > bottom else -axis


def rotation_onto_z(axis: np.ndarray) -> np.ndarray:
    """Return the rotation taking the unit vector ``axis`` onto +z (Rodrigues' formula)."""
    z = np.array([0.0, 0.0, 1.0])
    cross = np.cross(axis, z)
    sine, cosine = float(np.linalg.norm(cross)), float(axis @ z)
    if sine < 1e-12:
        return np.eye(3) if cosine > 0 else np.diag([1.0, -1.0, -1.0])
    k = cross / sine
    skew = np.array([[0.0, -k[2], k[1]], [k[2], 0.0, -k[0]], [-k[1], k[0], 0.0]])
    return np.eye(3) + sine * skew + (1.0 - cosine) * (skew @ skew)


def prepare(source: Path, destination: Path) -> None:
    """Write chains A-L of ``source``, axis on z and *cis* up, to ``destination``."""
    with warnings.catch_warnings():
        # The deposited entry's header and the writer's defaults each warn; none
        # of it concerns the coordinates.
        warnings.simplefilter("ignore")
        universe = mda.Universe(str(source))
    protein = universe.select_atoms(f"protein and chainID {CHAINS}")
    calpha = protein.select_atoms("name CA").positions.astype(np.float64)
    axis = signed_to_cis(calpha, pore_axis(calpha))
    tilt = float(np.degrees(np.arccos(abs(axis[2]))))
    log.info("estimated pore axis %s, %.2f° from the file's z", np.round(axis, 4).tolist(), tilt)

    rotation = rotation_onto_z(axis)
    anchor = protein.select_atoms(f"name CA and resid {REGISTRATION_RESIDUES}").positions
    centroid = anchor.astype(np.float64).mean(axis=0)
    target = np.array([0.0, 0.0, CENTROID_Z_NM * 10.0])  # Å, the PDB's unit
    moved = (protein.positions.astype(np.float64) - centroid) @ rotation.T + target
    protein.positions = moved.astype(np.float32)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        protein.write(str(destination))
    log.info("wrote %s: %d atoms in %d chains", destination, len(protein), len(CHAINS.split()))


def main() -> None:
    """Parse the two paths and prepare the structure."""
    # This script's own records at INFO; MDAnalysis's at WARNING, since it
    # reports every attribute it guesses at INFO.
    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    log.setLevel(logging.INFO)
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", type=Path, help="the deposited entry, PDB format, may be gzipped")
    parser.add_argument("destination", type=Path, help="the prepared PDB to write")
    arguments = parser.parse_args()
    prepare(arguments.source, arguments.destination)


if __name__ == "__main__":
    main()

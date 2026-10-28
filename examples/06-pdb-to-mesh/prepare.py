"""Prepare the deposited 2WCD entry for nanopnp: one dodecamer, its pore axis on z, *cis* up.

Run from this directory::

    python prepare.py ../../tests/data/structures/2wcd.pdb.gz 2wcd-prepared.pdb

Preparing a structure is the user's choice, not the pipeline's: nanopnp's stage 1
refuses a file whose pore axis is more than 10° from z, and never re-orients one
itself. This script makes the choices for ClyA and hands them to
``nanopnp.structure.orient_pore``, which needs the ``structure`` extra:

1. **The chains.** The first dodecamer, chains A-L, protein only; chains M-X are
   the second.
2. **The flip.** The wide end of ClyA, the cap, faces *cis*, and nanopnp's +z
   points from *trans* to *cis*, so ``cis_end="wider"``. ``orient_pore`` estimates
   the axis from the C-alpha covariance, which is enough to land inside stage 1's
   gate; stage 1 then finds the axis itself, by superposing the chains.
3. **The membrane's place.** The C-alpha centroid of residues 8-292 goes to
   (0, 0, 5.655) nm. That is where the centroid of the molecular-dynamics
   structure sits when the bilayer centre is at z = 0, so the case can keep
   ``geometry.membrane.centre_z_nm`` at its default of 0.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from nanopnp.structure import orient_pore

CHAINS = "A,B,C,D,E,F,G,H,I,J,K,L"
"""The first dodecamer of the deposited entry; chains M-X are the second."""

REGISTRATION_RESIDUES = (8, 292)
"""The residues whose C-alpha centroid is placed on the axis."""

CENTROID_Z_NM = 5.655
"""Where that centroid goes on z, in nm: the molecular-dynamics structure's, bilayer centre at 0."""


def main() -> None:
    """Parse the two paths and prepare the structure."""
    # nanopnp's own records at INFO; MDAnalysis's at WARNING, since it reports every
    # attribute it guesses at INFO.
    logging.basicConfig(level=logging.WARNING, format="%(message)s")
    logging.getLogger("nanopnp").setLevel(logging.INFO)
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("source", type=Path, help="the deposited entry, PDB format, may be gzipped")
    parser.add_argument("destination", type=Path, help="the prepared PDB to write")
    arguments = parser.parse_args()
    orient_pore(
        arguments.source,
        chains=CHAINS,
        cis_end="wider",
        registration_residues=REGISTRATION_RESIDUES,
        centroid_z_nm=CENTROID_Z_NM,
        out=arguments.destination,
    )


if __name__ == "__main__":
    main()

"""Build the spike's data set: 2WCD walked to stage 7, and the arrays the link needs."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from nanopnp import Case, Session
from nanopnp.charge.kernel import source_atoms
from nanopnp.charge.protonation import PAYLOAD_NAME, ProtonationTable
from nanopnp.charge.stage import frame_shift_nm, stored_lattice
from nanopnp.gui.charge import charge_image
from nanopnp.io.store import Store
from nanopnp.structure import orient_pore

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent / "out"


def main() -> None:
    OUT.mkdir(exist_ok=True)
    prepared = OUT / "2wcd-prepared.pdb"
    if not prepared.exists():
        orient_pore(
            ROOT / "tests/data/structures/2wcd.pdb.gz",
            chains="A,B,C,D,E,F,G,H,I,J,K,L",
            cis_end="wider",
            registration_residues=(8, 292),
            centroid_z_nm=5.655,
            out=prepared,
        )
    case = OUT / "2wcd.case.yaml"
    shutil.copy(ROOT / "examples/07-pdb-to-charged-run/2wcd.case.yaml", case)
    result = Session(Store(OUT / "store"), write=False).run(Case.load(case), upto="charge")
    resolved = result.resolved
    lattice = stored_lattice(result.artefacts["charge"])
    table = ProtonationTable.read(Path(result.artefacts["protonation"].payload[PAYLOAD_NAME]))
    shift = frame_shift_nm(resolved)
    atoms = source_atoms(table, sharpness=resolved.smearing.sharpness, shift_z_nm=shift)
    keys = np.array(
        [
            f"{str(table.chain[i]).strip()}:{int(table.resid[i])}{str(table.icode[i]).strip()}"
            for i in atoms.atom
        ]
    )
    names = np.array([str(table.resname[i]).strip() for i in atoms.atom])
    np.savez_compressed(
        OUT / "atoms.npz",
        r_nm=atoms.r_nm,
        z_nm=atoms.z_nm,
        width_nm=atoms.width_nm,
        weight_e=atoms.weight_e,
        key=keys,
        resname=names,
        shift_z_nm=shift,
    )
    np.savez_compressed(
        OUT / "lattice.npz", r_nm=lattice.grid.r_nm, z_nm=lattice.grid.z_nm, values=lattice.grid.values
    )
    shown = charge_image(lattice)
    height, width = shown.image.height, shown.image.width
    rgba = np.frombuffer(shown.image.rgba(), dtype=np.uint8).reshape(height, width, 4)
    Image.fromarray(rgba, "RGBA").save(OUT / "map.png")
    x_low, x_high, z_low, z_high = shown.image.extent_nm
    (OUT / "extent.json").write_text(
        json.dumps(
            {
                "r_low": x_low, "r_high": x_high, "z_low": z_low, "z_high": z_high,
                "width": width, "height": height, "limit": shown.limit, "units": shown.units,
            }
        )
    )
    print(f"fixture ready: {atoms.count} charged atoms, {len(set(keys))} residues, {width}x{height} px")


if __name__ == "__main__":
    sys.exit(main())

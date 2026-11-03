"""The link between a residue on the molecule and its charge on the (r, z) map, and back."""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.charge.kernel import source_atoms, volume_density
from nanopnp.charge.protonation import PAYLOAD_NAME, ProtonationTable
from nanopnp.charge.stage import frame_shift_nm, stored_lattice
from nanopnp.gui.charge import charge_image

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

    from nanopnp.pipeline.run import RunResult

__all__ = ["Extent", "Link", "residue_key"]

STRIP_MIN_CHARGE_E = 0.5
"""A residue is offered in the strip when its charge is at least this, in e."""

REACH_WIDTHS = 4.0
"""The distance, in smearing widths, beyond which an atom's density is not summed."""


def _chain_id(chain: str) -> str:
    # The one column of a PDB chain, which is all that Mol* reads back; a blank chain is "A".
    return chain.strip()[:1] or "A"


def residue_key(chain: str, resid: int, icode: str) -> str:
    """Return the name a residue goes by on both sides of the link.

    Built from the fields as the PDB text of :class:`Link` carries them, which is how Mol* names
    the residue it picks.
    """
    return f"{_chain_id(chain)}:{resid}{icode.strip()[:1]}"


@dataclass(frozen=True)
class Extent:
    """The map picture's outer edges in nm and its size in pixels."""

    r_low: float
    r_high: float
    z_low: float
    z_high: float
    width: int
    height: int

    def pixel(self, r_nm: float, z_nm: float) -> tuple[float, float]:
        """Return the picture position of a point."""
        x = (r_nm - self.r_low) / (self.r_high - self.r_low) * self.width
        y = (self.z_high - z_nm) / (self.z_high - self.z_low) * self.height
        return x, y

    def point(self, x: float, y: float) -> tuple[float, float]:
        """Return ``(r_nm, z_nm)`` of a picture position."""
        r = self.r_low + x / self.width * (self.r_high - self.r_low)
        z = self.z_high - y / self.height * (self.z_high - self.z_low)
        return r, z


def png(rgba: bytes, width: int, height: int) -> bytes:
    """Return a PNG of tightly packed RGBA8888 rows, top row first."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        body = kind + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body))

    rows = b"".join(b"\x00" + rgba[y * width * 4 : (y + 1) * width * 4] for y in range(height))
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(rows))
        + chunk(b"IEND", b"")
    )


# The first frame as PDB text, which Mol* reads; the positions are in Å.
def _pdb(table: ProtonationTable) -> str:
    lines = []
    stop = int(table.frame_offsets[1])
    for row in range(stop):
        x, y, z = (float(v) * 10.0 for v in table.positions_nm[row])
        name = str(table.name[row]).strip()
        resid = int(table.resid[row])
        # The four columns hold -999 to 9999, which the protonation stage keeps to; only a number
        # past them wraps (a negative one wrapped here would be named otherwise by Mol*).
        if not -999 <= resid <= 9999:
            resid %= 10000
        lines.append(
            f"ATOM  {(row + 1) % 100000:5d} {name:<4s} {str(table.resname[row]).strip():>3s} "
            f"{_chain_id(str(table.chain[row]))}{resid:4d}"
            f"{str(table.icode[row]).strip()[:1] or ' '}   {x:8.3f}{y:8.3f}{z:8.3f}"
            f"  1.00  0.00          {name[:1]:>2s}"
        )
    return "\n".join([*lines, "END"]) + "\n"


class Link:
    """Residue to map markers, and map point to ranked residues, for one charged run.

    Parameters
    ----------
    result
        A run walked to the ``charge`` stage.
    """

    def __init__(self, result: RunResult) -> None:
        import numpy as np

        artefact = result.artefacts["charge"]
        lattice = stored_lattice(artefact)
        resolved = result.resolved
        if lattice is None or resolved is None:
            raise ValueError("the run holds no stored charge lattice to draw")
        table = ProtonationTable.read(Path(result.artefacts["protonation"].payload[PAYLOAD_NAME]))
        atoms = source_atoms(
            table,
            sharpness=resolved.smearing.sharpness,
            shift_z_nm=frame_shift_nm(resolved),
        )
        shown = charge_image(lattice)
        r_low, r_high, z_low, z_high = shown.image.extent_nm
        self.extent = Extent(r_low, r_high, z_low, z_high, shown.image.width, shown.image.height)
        self.map_png = png(shown.image.rgba(), shown.image.width, shown.image.height)
        self.structure_pdb = _pdb(table)
        self._r, self._z = atoms.r_nm, atoms.z_nm
        self._width, self._weight = atoms.width_nm, atoms.weight_e
        # Every charged atom of every frame (an ensemble is tens of frames of tens of thousands of
        # atoms), keyed through plain lists and grouped in one pass in order of first appearance,
        # which the strip's order and its first chain follow.
        chain, resid, icode = table.chain.tolist(), table.resid.tolist(), table.icode.tolist()
        resname = table.resname.tolist()
        rows = atoms.atom.tolist()
        self._keys: list[str] = [
            residue_key(str(chain[i]), int(resid[i]), str(icode[i])) for i in rows
        ]
        self._names = np.array([str(resname[i]).strip() for i in rows])
        grouped: dict[str, list[int]] = {}
        for position, key in enumerate(self._keys):
            grouped.setdefault(key, []).append(position)
        self._rows: dict[str, np.ndarray] = {
            key: np.array(found, dtype=np.intp) for key, found in grouped.items()
        }

    def __contains__(self, key: object) -> bool:
        """Say whether a residue key names a residue that carries charge."""
        return key in self._rows

    def residues(self) -> list[tuple[str, str, float]]:
        """Return ``(key, name, charge_e)`` of the first chain's strongly charged residues."""
        first = next(iter(self._rows), "").partition(":")[0]
        found = []
        for key, rows in self._rows.items():
            charge = float(self._weight[rows].sum())
            if key.partition(":")[0] == first and abs(charge) >= STRIP_MIN_CHARGE_E:
                found.append((key, str(self._names[rows[0]]), charge))
        return found

    def residue_markers(self, key: str) -> list[tuple[float, float, float]]:
        """Return the ``(r_nm, z_nm, q_e)`` of each charged atom of a residue."""
        return [
            (float(self._r[i]), float(self._z[i]), float(self._weight[i])) for i in self._rows[key]
        ]

    def residues_at(self, r_nm: float, z_nm: float, n: int = 5) -> list[tuple[str, float]]:
        """Return the residues that add most charge density at a point, as ``(key, e/nm^3)``."""
        import numpy as np

        reach = REACH_WIDTHS * self._width
        near = np.flatnonzero((np.abs(self._z - z_nm) < reach) & (np.abs(self._r - r_nm) < reach))
        totals: dict[str, float] = {}
        for i in near:
            density = float(
                volume_density(
                    np.array(r_nm), np.array(z_nm), self._r[i], self._z[i], self._width[i]
                )
            )
            key = str(self._keys[i])
            totals[key] = totals.get(key, 0.0) + float(self._weight[i]) * density
        return sorted(totals.items(), key=lambda item: -abs(item[1]))[:n]

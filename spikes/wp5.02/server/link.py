"""The spike's link between a residue and the charge map (a display aid, not the library's)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

OUT = Path(__file__).resolve().parents[1] / "fixture" / "out"


class Link:
    """Residue to map markers, and map point to ranked residues."""

    def __init__(self, out: Path = OUT) -> None:
        data = np.load(out / "atoms.npz")
        self.r = data["r_nm"]
        self.z = data["z_nm"]
        self.width = data["width_nm"]
        self.weight = data["weight_e"]
        # The pore is C12: the twelve chains average onto one (r, z), so a residue is its number.
        raw = data["key"]
        self.chains = np.array([k.split(":")[0] for k in raw])
        self.keys = np.array([k.split(":")[1] for k in raw])
        self.names = data["resname"]
        self.extent = json.loads((out / "extent.json").read_text())
        first = str(self.chains[0])
        self._rows: dict[str, np.ndarray] = {}
        for key in np.unique(self.keys):
            self._rows[str(key)] = np.flatnonzero((self.keys == key) & (self.chains == first))

    def residues(self, min_q: float = 0.5) -> list[dict[str, object]]:
        """Residues whose net charge is at least min_q in magnitude, with that charge."""
        out = []
        for key, rows in self._rows.items():
            q = float(self.weight[rows].sum())
            if abs(q) >= min_q:
                out.append({"key": key, "name": str(self.names[rows[0]]), "q_e": q})
        out.sort(key=lambda item: int("".join(c for c in str(item["key"]) if c.isdigit())))
        return out

    def residue_markers(self, key: str) -> list[tuple[float, float, float]]:
        """The (r, z, q) of each charged atom of one residue."""
        rows = self._rows[key]
        return [(float(self.r[i]), float(self.z[i]), float(self.weight[i])) for i in rows]

    def residues_at(self, r_nm: float, z_nm: float, n: int = 5) -> list[dict[str, object]]:
        """The n residues contributing most to the charge density at one point."""
        reach = 4.0 * self.width
        near = np.flatnonzero(
            (np.abs(self.z - z_nm) < reach) & (np.abs(self.r - r_nm) < reach)
        )
        if near.size == 0:
            return []
        radius = abs(r_nm)
        axial = z_nm - self.z[near]
        from scipy.special import i0e

        w = self.width[near]
        density = (
            np.pi**-1.5
            * w**-3
            * np.exp(-(((radius - self.r[near]) ** 2) + axial**2) / w**2)
            * i0e(2.0 * radius * self.r[near] / w**2)
        )
        contribution = self.weight[near] * density
        totals: dict[str, float] = {}  # summed over the twelve chains
        for row, value in zip(near, contribution, strict=True):
            key = str(self.keys[row])
            totals[key] = totals.get(key, 0.0) + float(value)
        ranked = sorted(totals.items(), key=lambda item: -abs(item[1]))[:n]
        return [
            {"key": key, "name": str(self.names[self._rows[key][0]]), "density": value}
            for key, value in ranked
        ]

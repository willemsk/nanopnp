"""The link between a residue on the molecule and its charge on the (r, z) map, and back."""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from nanopnp.charge.protonation import PAYLOAD_NAME, ProtonationTable
from nanopnp.charge.stage import CHARGE_PAYLOAD, stored_lattice
from nanopnp.gui.charge import charge_image
from nanopnp.gui.geometry import Palette
from nanopnp.gui.web.molview import first_frame_pdb
from nanopnp.gui.web.plane import png
from nanopnp.plot.data import ResidueCharges, residue_key

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.pipeline.run import RunResult

__all__ = ["Extent", "Link", "residue_key"]


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


class Link:
    """Residue to map markers, and map point to ranked residues, for one charged run.

    Parameters
    ----------
    result
        A run walked to the ``charge`` stage.
    """

    @classmethod
    def from_run(cls, result: RunResult) -> Link | None:
        """Return the link of a run, or None where its charge has no structure behind it."""
        if "protonation" not in result.artefacts:
            return None
        if CHARGE_PAYLOAD not in result.artefacts["charge"].payload:
            return None
        return cls(result)

    def __init__(self, result: RunResult) -> None:
        artefact = result.artefacts["charge"]
        lattice = stored_lattice(artefact)
        resolved = result.resolved
        if lattice is None or resolved is None:
            raise ValueError("the run holds no stored charge lattice to draw")
        protonation = result.artefacts["protonation"]
        charges = ResidueCharges.of(protonation, artefact, resolved)
        if charges is None:
            raise ValueError("the run holds no deposited charge to link")
        self._charges = charges
        shown = charge_image(lattice)
        r_low, r_high, z_low, z_high = shown.image.extent_nm
        self.extent = Extent(r_low, r_high, z_low, z_high, shown.image.width, shown.image.height)
        self._image = shown.image
        self._maps: dict[str, bytes] = {}
        table = ProtonationTable.read(Path(protonation.payload[PAYLOAD_NAME]))
        self.structure_pdb = first_frame_pdb(table)

    def map_png(self, positive: Literal["blue", "red"] = "blue") -> bytes:
        """Return the charge map as a PNG, a positive charge in the named colour."""
        if positive not in self._maps:
            palette: Palette = "diverging_r" if positive == "blue" else "diverging"
            image = replace(self._image, palette=palette)
            self._maps[positive] = png(image.rgba(), image.width, image.height)
        return self._maps[positive]

    def __contains__(self, key: object) -> bool:
        """Say whether a residue key names a residue that carries charge."""
        return key in self._charges

    def residues(self) -> list[tuple[str, str, float]]:
        """Return ``(key, name, charge_e)`` of the first chain's strongly charged residues."""
        return self._charges.residues()

    def residue_markers(self, key: str) -> list[tuple[float, float, float]]:
        """Return the ``(r_nm, z_nm, q_e)`` of each charged atom of a residue."""
        return self._charges.markers(key)

    def residues_at(self, r_nm: float, z_nm: float, n: int = 5) -> list[tuple[str, float]]:
        """Return the residues that add most charge density at a point, as ``(key, e/nm^3)``."""
        return self._charges.at(r_nm, z_nm, n)

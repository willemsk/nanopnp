"""Stage 5's region interface: what every consumer reads of either kind of region record (FR-09)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from nanopnp.core.hashing import Canonicalisable

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np


@dataclass(frozen=True, eq=False)
class RegionOutlines:
    """A stage-5 region's named outlines in nm, in the model frame.

    Parameters
    ----------
    pore_nm
        The pore's closed polygon, ``(n, 2)`` in ``(r, z)``.
    membrane_nm
        The membrane face's outline, from its inner edge on the trans side round to the cis side.
    exclusion_nm
        The ion-exclusion shell's outer loop, or ``None`` without one.
    membrane_centre_z_nm
        The membrane's centre in the structure's frame, the shift into the model frame; 0 for an
        idealised pore.
    z_extent_nm
        The pore's z extent.
    """

    pore_nm: np.ndarray
    membrane_nm: np.ndarray
    exclusion_nm: np.ndarray | None
    membrane_half_thickness_nm: float
    membrane_centre_z_nm: float
    reservoir_radius_nm: float
    z_extent_nm: tuple[float, float]

    @property
    def chord_nm(self) -> tuple[tuple[float, float], tuple[float, float]]:
        """Return the membrane's inner edge: its outline's first and last points."""
        first, last = self.membrane_nm[0], self.membrane_nm[-1]
        return (float(first[0]), float(first[1])), (float(last[0]), float(last[1]))


class Stage5Region(Protocol):
    """What a consumer reads of a stage-5 region record, whichever kind of pore wrote it."""

    @property
    def face_areas_nm2(self) -> dict[str, float]:
        """The area of each named face, in nm²."""

    @property
    def edge_counts(self) -> dict[str, int]:
        """The number of edges of each named boundary."""

    @property
    def is_idealised(self) -> bool:
        """Whether the case declared the pore rather than a structure's outline."""

    @property
    def has_exclusion(self) -> bool:
        """Whether the region carries an ion-exclusion shell."""

    @property
    def membrane_centre_z_nm(self) -> float:
        """The membrane's centre in the structure's frame; 0 for an idealised pore."""

    def outlines_nm(self) -> RegionOutlines:
        """Return the region's named outlines in nm, in the model frame."""

    def summary(self) -> dict[str, Canonicalisable]:
        """Return what the manifest's Geometry group records as ``region``."""

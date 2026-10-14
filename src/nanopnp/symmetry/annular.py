"""Exact cell-annulus overlap weights for the (r, z) binning of stage 3."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np
    from scipy.sparse import csr_matrix


def _segment(x: np.ndarray, radius: np.ndarray) -> np.ndarray:
    import numpy as np

    # atan2, not asin: asin is ill-conditioned near x = R
    # (.knowledge/07-software-stack/02-structure-trajectory-and-density.md).
    s = np.sqrt(np.maximum((radius - x) * (radius + x), 0.0))
    area: np.ndarray = 0.5 * (x * s + radius**2 * np.arctan2(x, s))
    return area


def _quadrant(x: np.ndarray, y: np.ndarray, radius: np.ndarray) -> np.ndarray:
    import numpy as np

    sign = np.sign(x) * np.sign(y)
    x = np.minimum(np.abs(x), radius)
    y = np.minimum(np.abs(y), radius)
    corner = np.sqrt(np.maximum((radius - y) * (radius + y), 0.0))
    inside = np.minimum(x, corner) * y
    area = np.where(x > corner, inside + _segment(x, radius) - _segment(corner, radius), inside)
    signed: np.ndarray = sign * area
    return signed


def disc_overlap(
    x0: np.ndarray, x1: np.ndarray, y0: np.ndarray, y1: np.ndarray, radius: np.ndarray
) -> np.ndarray:
    """Return the area of each rectangle ``[x0, x1] x [y0, y1]`` inside the disc of ``radius``."""
    overlap: np.ndarray = (
        _quadrant(x1, y1, radius)
        - _quadrant(x0, y1, radius)
        - _quadrant(x1, y0, radius)
        + _quadrant(x0, y0, radius)
    )
    return overlap


@dataclass(frozen=True)
class AnnularWeights:
    """The bin matrix of one grid slice, reused for every z."""

    matrix: csr_matrix
    areas_nm2: np.ndarray
    spacing_nm: float
    half_width: int

    @property
    def bins(self) -> int:
        """Number of bins, ``I + 1``."""
        return self.half_width + 1

    @property
    def r_nm(self) -> np.ndarray:
        """The bin centres ``r_j = j·h``, in nm."""
        import numpy as np

        return np.arange(self.bins, dtype=np.float64) * self.spacing_nm

    def cell_coordinates(self) -> tuple[np.ndarray, np.ndarray]:
        """Return each cell centre's radius (nm) and azimuth (rad), flattened ``[y, x]``."""
        import numpy as np

        nodes = np.arange(-self.half_width, self.half_width + 1, dtype=np.float64)
        y, x = np.meshgrid(nodes, nodes, indexing="ij")
        h = self.spacing_nm
        return np.hypot(x, y).reshape(-1) * h, np.arctan2(y, x).reshape(-1)


def annular_weights(half_width: int, spacing_nm: float) -> AnnularWeights:
    """Return the exact overlap weights of a ``(2I + 1)²`` slice with bins ``0 … I``."""
    import numpy as np
    from scipy.sparse import coo_matrix

    size = half_width
    nodes = np.arange(-size, size + 1, dtype=np.float64)
    y, x = (axis.reshape(-1) for axis in np.meshgrid(nodes, nodes, indexing="ij"))
    near = np.hypot(np.maximum(np.abs(x) - 0.5, 0.0), np.maximum(np.abs(y) - 0.5, 0.0))
    # The first boundary (k + 1/2) at or beyond the cell's nearest point.
    first = np.maximum(np.ceil(near - 0.5), 0.0).astype(np.int64)
    rows: list[np.ndarray] = []
    columns: list[np.ndarray] = []
    values: list[np.ndarray] = []
    cells = np.arange(x.size)
    previous = np.zeros_like(x)
    for step in range(3):
        bin_index = first + step
        radius = bin_index + 0.5
        inside = disc_overlap(x - 0.5, x + 0.5, y - 0.5, y + 0.5, radius)
        weight = inside - previous
        previous = inside
        keep = (bin_index <= size) & (weight > 0.0)
        rows.append(bin_index[keep])
        columns.append(cells[keep])
        values.append(weight[keep])
    h = float(spacing_nm)
    matrix = coo_matrix(
        (np.concatenate(values) * h * h, (np.concatenate(rows), np.concatenate(columns))),
        shape=(size + 1, x.size),
    ).tocsr()
    areas = np.asarray(matrix.sum(axis=1)).reshape(-1)
    return AnnularWeights(matrix=matrix, areas_nm2=areas, spacing_nm=h, half_width=size)

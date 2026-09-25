"""Exact cell-annulus overlap weights: the (r, z) binning of stage 3 (FR-05, WP19 D8).

Bin ``j`` is the annulus ``[(j - ½)h, (j + ½)h]`` about ``r_j = j·h``, and bin 0 the
disc of radius ``h/2``, which lies inside the axis cell, so ``μ_0`` is the exact axis
sample. A cell's weight in a bin is the exact area of their overlap. So an annulus's
weights sum to its area, ``2πjh²`` (``πh²/4`` for bin 0), and every cell inside the
outermost circle has weights summing to ``h²``: with stage 2's spare ring, binning
conserves the map's integral slice by slice. **No bin is interpolated** (the
section 5.2 stage-3 note as amended; WP19 Design §3).

The disc-rectangle overlap is a closed form. For ``X, Y ≥ 0`` let ``G(X, Y; R)`` be
the area of ``{0 ≤ x ≤ X, 0 ≤ y ≤ Y, x² + y² ≤ R²}``. With X and Y clipped to R,
``x* = √((R - Y)(R + Y))`` and ``F(x) = ½(x s + R² atan2(x, s))``,
``s = √((R - x)(R + x))``:

    G = min(X, x*)·Y + [X > x*]·(F(X) - F(x*)).

A cell ``[x₀, x₁] x [y₀, y₁]`` overlaps the disc in ``G₁₁ - G₀₁ - G₁₀ + G₀₀``, with G
extended oddly in each sign. **The segment primitive is written with ``atan2``**: with
``asin(x/R)`` the weights summed to the exact areas only to 2.3e-7, because ``asin`` is
ill-conditioned as x → R and R² amplifies it; ``atan2`` gives 4e-13 [tested],
``.knowledge/07-software-stack.md`` §2.

Phase 3's charge projection (FR-13) reuses these weights.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np
    from scipy.sparse import csr_matrix


def _segment(x: np.ndarray, radius: np.ndarray) -> np.ndarray:
    """Return ``∫₀ˣ √(R² - t²) dt`` for ``0 ≤ x ≤ R``, in the well-conditioned form."""
    import numpy as np

    s = np.sqrt(np.maximum((radius - x) * (radius + x), 0.0))
    area: np.ndarray = 0.5 * (x * s + radius**2 * np.arctan2(x, s))
    return area


def _quadrant(x: np.ndarray, y: np.ndarray, radius: np.ndarray) -> np.ndarray:
    """Return the signed area of the disc of ``radius`` inside ``[0, x] x [0, y]``.

    Odd in each of ``x`` and ``y``, so four evaluations give any rectangle.
    """
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
    """Return the area of each rectangle ``[x0, x1] x [y0, y1]`` inside the disc of ``radius``.

    The disc is centred at the origin. All arguments broadcast.
    """
    overlap: np.ndarray = (
        _quadrant(x1, y1, radius)
        - _quadrant(x0, y1, radius)
        - _quadrant(x1, y0, radius)
        + _quadrant(x0, y0, radius)
    )
    return overlap


@dataclass(frozen=True)
class AnnularWeights:
    """The bin matrix of one grid slice, reused for every z.

    Parameters
    ----------
    matrix
        Sparse ``(bins, cells)``: the overlap area of each cell with each bin, in
        nm². The cells run over a ``(2I + 1)²`` slice flattened ``[y, x]``, as a
        stage-2 map's plane ``values[k].reshape(-1)`` is.
    areas_nm2
        Each bin's weights summed: its area.
    spacing_nm
        ``h``.
    half_width
        ``I``: the slice's nodes run ``-I … I`` on each axis, and the bins
        ``0 … I``.
    """

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
        """The bin centres ``r_j = j·h``."""
        import numpy as np

        return np.arange(self.bins, dtype=np.float64) * self.spacing_nm

    def cell_coordinates(self) -> tuple[np.ndarray, np.ndarray]:
        """Return each cell centre's radius (nm) and azimuth (rad), flattened ``[y, x]``.

        The axis cell's azimuth is 0 by ``atan2(0, 0)``; it overlaps only bins 0
        and 1, where no harmonic is resolved for n ≥ 4.
        """
        import numpy as np

        nodes = np.arange(-self.half_width, self.half_width + 1, dtype=np.float64)
        y, x = np.meshgrid(nodes, nodes, indexing="ij")
        h = self.spacing_nm
        return np.hypot(x, y).reshape(-1) * h, np.arctan2(y, x).reshape(-1)


def annular_weights(half_width: int, spacing_nm: float) -> AnnularWeights:
    """Return the exact overlap weights of a ``(2I + 1)²`` slice with bins ``0 … I``.

    Computed in units of ``h`` and scaled by ``h²``, so the half-integer cell
    edges and the bin radii are exact. A cell reaches at most three bins: its
    radial extent is at most ``√2`` spacings. Weights in bins beyond ``I`` are
    dropped; by stage 2's spare ring (WP19 D5) those cells hold no density.
    """
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

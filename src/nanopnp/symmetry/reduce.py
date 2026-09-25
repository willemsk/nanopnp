"""Stage 3's computation: the (r, z) mean and the azimuthal variances (FR-05, FR-06, CON-04).

**The Cₙ average is a projection in the angular harmonic basis** (WP19 D7). At fixed
(r, z) write ``rho(θ) = Σ_m c_m e^{imθ}``. A rotation by alpha multiplies ``c_m`` by
``e^{-imalpha}``, so the average of the n rotated copies keeps ``c_m`` where n | m and
drops the rest. Hence:

- the azimuthal mean is ``c_0``, which the average does not move, so the mean needs
  no average at all;
- the Cₙ-averaged map's azimuthal variance is ``2 Σ_{k≥1} |c_kn|²``, FR-06's
  residual variance;
- the raw map's is ``2 Σ_{m≥1} |c_m|²``, and the difference is the variation that is
  not Cₙ-symmetric: chain asymmetry and thermal disorder.

Both come from the unrotated map, with neither rotated deposition nor interpolation.
Rotating the voxel map bilinearly would smooth eight of twelve copies and bias the
peak variance low by 3-6 %, hiding RSK-07 rather than exposing it (Design §2).

**Detrended first** (D9). Inside a bin of width h a cell's value still varies with
its own radius, and binned, that radial gradient reads as azimuthal variance —
about ``(∂rho/∂r)² h²/12``, which for an axisymmetric ring of width 0.2 nm is a C12
variance of 1.9e-4 against a genuine C12 signal of 8.7e-4. So the binned mean is
fitted by a cubic spline extended evenly about r = 0, evaluated at each cell's own
radius and subtracted, before either variance is taken; the same ring then reads
2e-8 (Design §3, ``.knowledge/07-software-stack.md`` §2).

**Only resolved harmonics are summed.** A ring of radius ``r_j`` sampled at spacing h
resolves ``m < π r_j/h``, so bin j sums ``k = 1 … K_j = ⌊π j/n⌋``. Below
``r = nh/π`` nothing is resolved; the artefact records that radius and every
``K_j`` rather than presenting the zero as a measurement. ``n = 1`` has no
rotation to average over, and its Cₙ variance is the raw variance.

Neither variance is gated: no threshold is specified (RSK-07).
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from nanopnp.core.hashing import Canonicalisable, content_hash
from nanopnp.core.stages import CancelToken, Progress, check_cancelled, report
from nanopnp.density.grid import GridFormatError, RadialGrid
from nanopnp.io.artefact import REDUCED_SCHEMA
from nanopnp.symmetry.annular import AnnularWeights, annular_weights

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

    from nanopnp.density.map import DensityMap

PAYLOAD_NAME = "reduced"
"""The artefact's payload key, and the ``.npz`` file's stem."""

DETREND = "even-cubic"
"""The detrending rule, recorded in the stage-3 key (WP19 D11)."""

HARMONICS = "nyquist"
"""The harmonic truncation rule, ``k n ≤ π r_j/h``, recorded in the stage-3 key."""

SLAB_PLANES = 16
"""z planes reduced together: bounds the detrended slab and its harmonic products."""

QUANTITIES: tuple[str, ...] = ("mean", "cn_variance", "raw_variance")
"""The three ``[z, r]`` fields a reduction carries, in order."""


@dataclass(frozen=True)
class ReducedMap:
    """The (r, z) reduction of one density map.

    Parameters
    ----------
    r_nm, z_nm
        The bin centres ``j·h`` and the density's z nodes.
    mean, cn_variance, raw_variance
        float64, indexed ``[z, r]`` as :class:`~nanopnp.density.grid.RadialGrid`
        indexes its values.
    harmonics
        ``K_j``, the number of Cₙ harmonics resolved in each bin.
    header
        Everything else, as plain data.
    """

    r_nm: np.ndarray
    z_nm: np.ndarray
    mean: np.ndarray
    cn_variance: np.ndarray
    raw_variance: np.ndarray
    harmonics: np.ndarray
    header: Mapping[str, Canonicalisable]

    def digest(self) -> str:
        """Return a content hash over the arrays and the header (recorded, never keyed)."""
        return content_hash(
            f"{REDUCED_SCHEMA}/payload",
            {
                "r_nm": self.r_nm,
                "z_nm": self.z_nm,
                **{name: getattr(self, name) for name in QUANTITIES},
                "harmonics": self.harmonics,
                "header": dict(self.header),
            },
        )

    def grids(self) -> dict[str, RadialGrid]:
        """Return the mean and both variances as RadialGrid objects, which stage 4 reads."""
        return {
            name: RadialGrid.from_axes(self.r_nm, self.z_nm, getattr(self, name))
            for name in QUANTITIES
        }

    def write(self, path: Path) -> Path:
        """Write the reduction to ``path`` as compressed ``.npz``; return the path."""
        import numpy as np

        arrays: dict[str, Any] = {
            "r_nm": self.r_nm,
            "z_nm": self.z_nm,
            **{name: getattr(self, name) for name in QUANTITIES},
            "harmonics": self.harmonics,
            "header": np.asarray(json.dumps(dict(self.header), sort_keys=True)),
        }
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as handle:
            np.savez_compressed(handle, **arrays)
        return path

    @classmethod
    def read(cls, path: Path) -> ReducedMap:
        """Read a reduction written by :meth:`write`.

        Raises
        ------
        GridFormatError
            If an array is missing or does not fit the two axes.
        """
        import numpy as np

        keys = ("r_nm", "z_nm", *QUANTITIES, "harmonics", "header")
        with np.load(path, allow_pickle=False) as data:
            missing = [key for key in keys if key not in data.files]
            if missing:
                raise GridFormatError(
                    f"{path.name!r} is not a stage-3 reduction: it lacks {', '.join(missing)}"
                )
            arrays = {key: np.asarray(data[key]) for key in keys if key != "header"}
            header = json.loads(str(data["header"]))
        shape = (arrays["z_nm"].size, arrays["r_nm"].size)
        for name in QUANTITIES:
            if arrays[name].shape != shape:
                raise GridFormatError(
                    f"{path.name!r}: {name} has shape {arrays[name].shape}, and the axes need "
                    f"{shape} (z, r)"
                )
        return cls(header=header, **arrays)


def harmonic_counts(bins: int, n: int) -> np.ndarray:
    """Return ``K_j = ⌊π j/n⌋``: the Cₙ harmonics bin j resolves (D9)."""
    import numpy as np

    return np.floor(np.pi * np.arange(bins) / n).astype(np.int64)


def unresolved_radius_nm(n: int, spacing_nm: float) -> float:
    """Return ``n h/π``, below which no Cₙ harmonic is resolved."""
    return n * spacing_nm / math.pi


def _detrended(
    values: np.ndarray, mean: np.ndarray, r_nm: np.ndarray, radii: tuple[np.ndarray, np.ndarray]
) -> np.ndarray:
    """Subtract the even cubic spline of the binned mean at each cell's own radius.

    ``radii`` is :func:`_distinct_radii`'s pair, so the spline is evaluated once
    per distinct radius rather than once per cell.
    """
    import numpy as np
    from scipy.interpolate import CubicSpline

    mirrored_r = np.concatenate((-r_nm[:0:-1], r_nm))
    mirrored = np.concatenate((mean[:, :0:-1], mean), axis=1)
    spline = CubicSpline(mirrored_r, mirrored, axis=1)
    distinct, index = radii
    trend: np.ndarray = spline(distinct)[:, index]
    detrended: np.ndarray = values - trend
    return detrended


def _distinct_radii(weights: AnnularWeights) -> tuple[np.ndarray, np.ndarray]:
    """Return the distinct cell radii and each cell's index into them.

    A cell at nodes (i, j) has radius ``h √(i² + j²)``, so cells sharing ``i² + j²``
    share a radius exactly; grouping on the integer avoids a float comparison.
    """
    import numpy as np

    size = weights.half_width
    nodes = np.arange(-size, size + 1, dtype=np.int64)
    y, x = np.meshgrid(nodes, nodes, indexing="ij")
    squares, index = np.unique((x * x + y * y).reshape(-1), return_inverse=True)
    return np.sqrt(squares.astype(np.float64)) * weights.spacing_nm, index.reshape(-1)


def reduce_map(
    density: DensityMap,
    n: int,
    *,
    detrend: bool = True,
    progress: Progress | None = None,
    cancel: CancelToken | None = None,
) -> ReducedMap:
    """Reduce a stage-2 map to (r, z): mean, Cₙ variance and raw variance.

    Parameters
    ----------
    density
        The map, on its canonical grid.
    n
        The point group's order.
    detrend
        Subtract the even-cubic trend before taking the variances. The stage
        always does, and its key records :data:`DETREND`; ``False`` exists so a
        test can show that detrending is what removes the variance an
        axisymmetric input would otherwise read (VER-50).
    progress, cancel
        Reported and checked once per slab of :data:`SLAB_PLANES` z planes.

    Raises
    ------
    nanopnp.core.stages.Cancelled
        If ``cancel`` turns true between slabs.
    """
    import numpy as np

    grid = density.grid
    weights = annular_weights(grid.half_width, grid.spacing_nm)
    matrix = weights.matrix
    areas = weights.areas_nm2
    bins = weights.bins
    counts = harmonic_counts(bins, n)
    top = int(counts.max()) if n > 1 else 0
    _, theta = weights.cell_coordinates()
    radii = _distinct_radii(weights)
    # e^{-i n θ}; the k-th harmonic's phase is its k-th power, built by recurrence.
    step = np.exp(-1j * n * theta)
    cells = grid.n * grid.n

    shape = (grid.nz, bins)
    mean = np.empty(shape)
    raw = np.empty(shape)
    cn = np.zeros(shape)
    for first in range(0, grid.nz, SLAB_PLANES):
        last = min(first + SLAB_PLANES, grid.nz)
        check_cancelled(cancel, f"reducing z planes {first}-{last - 1} of {grid.nz}")
        values = density.values[first:last].reshape(last - first, cells).astype(np.float64)
        slab_mean = (matrix @ values.T).T / areas
        mean[first:last] = slab_mean
        delta = _detrended(values, slab_mean, weights.r_nm, radii) if detrend else values
        first_moment = (matrix @ delta.T).T / areas
        second_moment = (matrix @ (delta * delta).T).T / areas
        raw[first:last] = second_moment - first_moment**2
        phase = np.ones_like(step)
        for k in range(1, top + 1):
            phase = phase * step
            resolved = counts >= k
            coefficient = (matrix @ (delta * phase).T).T / areas
            cn[first:last, resolved] += 2.0 * np.abs(coefficient[:, resolved]) ** 2
        report(progress, last / grid.nz, f"reduced z planes to {last} of {grid.nz}")
    if n == 1:
        cn = raw.copy()

    r_nm = weights.r_nm
    z_nm = grid.axis_nm("z")
    header: dict[str, Canonicalisable] = {
        "n": n,
        "bins": bins,
        "spacing_nm": grid.spacing_nm,
        "detrend": DETREND if detrend else "none",
        "harmonics": HARMONICS,
        "unresolved_radius_nm": unresolved_radius_nm(n, grid.spacing_nm),
        "maximum": {
            "cn_variance": _peak(cn, r_nm, z_nm),
            "non_cn_variance": _peak(raw - cn, r_nm, z_nm),
            "raw_variance": _peak(raw, r_nm, z_nm),
        },
        "source_payload_digest": density.digest(),
    }
    return ReducedMap(
        r_nm=r_nm,
        z_nm=z_nm,
        mean=mean,
        cn_variance=cn,
        raw_variance=raw,
        harmonics=counts,
        header=header,
    )


def _peak(values: np.ndarray, r_nm: np.ndarray, z_nm: np.ndarray) -> dict[str, Canonicalisable]:
    """Return the maximum of a ``[z, r]`` field and where it is."""
    import numpy as np

    k, j = np.unravel_index(int(np.argmax(values)), values.shape)
    return {"value": float(values[k, j]), "r_nm": float(r_nm[j]), "z_nm": float(z_nm[k])}

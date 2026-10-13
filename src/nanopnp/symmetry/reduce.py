"""Stage 3's computation: the (r, z) mean and the azimuthal variances."""

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

DETREND = "even-cubic"

HARMONICS = "nyquist"

SLAB_PLANES = 16

QUANTITIES: tuple[str, ...] = ("mean", "cn_variance", "raw_variance")


@dataclass(frozen=True)
class ReducedMap:
    """The (r, z) reduction of one density map."""

    r_nm: np.ndarray
    z_nm: np.ndarray
    mean: np.ndarray
    cn_variance: np.ndarray
    raw_variance: np.ndarray
    harmonics: np.ndarray
    header: Mapping[str, Canonicalisable]

    def digest(self) -> str:
        """Return a content hash over the arrays and the header."""
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
        """Return the mean and both variances as radial grids."""
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
    """Return ``K_j = ⌊π j/n⌋``: the Cₙ harmonics each bin ``j`` resolves."""
    import numpy as np

    return np.floor(np.pi * np.arange(bins) / n).astype(np.int64)


def unresolved_radius_nm(n: int, spacing_nm: float) -> float:
    """Return ``n h/π``, in nm, below which no Cₙ harmonic is resolved."""
    return n * spacing_nm / math.pi


def _detrended(
    values: np.ndarray, mean: np.ndarray, r_nm: np.ndarray, radii: tuple[np.ndarray, np.ndarray]
) -> np.ndarray:
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
    import numpy as np

    k, j = np.unravel_index(int(np.argmax(values)), values.shape)
    return {"value": float(values[k, j]), "r_nm": float(r_nm[j]), "z_nm": float(z_nm[k])}

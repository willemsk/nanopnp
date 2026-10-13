"""Stage 2's field: the ensemble mean of per-frame probabilistic-union densities (FR-04)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from nanopnp.core.hashing import Canonicalisable
from nanopnp.core.stages import CancelToken, Progress, check_cancelled, report
from nanopnp.density.radii import DensityInputError

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

# A term is kept iff g >= EPSILON; the truncation error bound is in .knowledge/07-software-stack.md.
EPSILON = 1e-6

# Below ln 2**-53, 1 - rho is under float64's spacing at 1.
LOG_FLOOR = math.log(2.0**-53)

CUTOFF_FACTOR = math.sqrt(math.log(1.0 / EPSILON))

GATE_TOLERANCE = 2.0**-24

SLAB_CELLS = 4_000_000

BATCH_TERMS = 1_000_000


class DensityGateError(RuntimeError): ...


@dataclass(frozen=True)
class DensityGrid:
    spacing_nm: float
    half_width: int
    z_first: int
    nz: int

    @property
    def n(self) -> int:
        return 2 * self.half_width + 1

    @property
    def shape(self) -> tuple[int, int, int]:
        return (self.nz, self.n, self.n)

    @property
    def origin_nm(self) -> tuple[float, float, float]:
        h = self.spacing_nm
        return (-self.half_width * h, -self.half_width * h, self.z_first * h)

    def axis_nm(self, axis: str) -> np.ndarray:
        import numpy as np

        h = self.spacing_nm
        if axis == "z":
            return (self.z_first + np.arange(self.nz, dtype=np.float64)) * h
        if axis in ("x", "y"):
            return np.arange(-self.half_width, self.half_width + 1, dtype=np.float64) * h
        raise ValueError(f"axis {axis!r} is not one of 'x', 'y', 'z'")

    def summary(self) -> dict[str, Canonicalisable]:
        return {
            "spacing_nm": self.spacing_nm,
            "half_width": self.half_width,
            "z_first": self.z_first,
            "shape_zyx": list(self.shape),
            "origin_nm": list(self.origin_nm),
        }

    @classmethod
    def from_summary(cls, summary: dict[str, Canonicalisable]) -> DensityGrid:
        shape = summary["shape_zyx"]
        assert isinstance(shape, list)
        return cls(
            spacing_nm=float(summary["spacing_nm"]),
            half_width=int(summary["half_width"]),
            z_first=int(summary["z_first"]),
            nz=int(shape[0]),
        )


def cutoff_nm(width_nm: np.ndarray) -> np.ndarray:
    return width_nm * CUTOFF_FACTOR


def check_positions(positions_nm: np.ndarray) -> None:
    import numpy as np

    bad = ~np.isfinite(positions_nm).all(axis=2)
    if bad.any():
        frame, atom = (int(value) for value in np.argwhere(bad)[0])
        raise DensityInputError(
            f"frame {frame} of the aligned ensemble holds a non-finite coordinate for atom "
            f"{atom}, so stage 2 cannot place it"
        )


def canonical_grid(
    positions_nm: np.ndarray, widths_nm: np.ndarray, spacing_nm: float
) -> DensityGrid:
    import numpy as np

    h = float(spacing_nm)
    reach = float(np.max(cutoff_nm(widths_nm)))
    # One frame at a time: a float64 copy of the float32 ensemble plus radii is 2.7x its size.
    radius, z_min, z_max = 0.0, math.inf, -math.inf
    for frame in positions_nm:
        xyz = np.asarray(frame, dtype=np.float64)
        radius = max(radius, float(np.max(np.hypot(xyz[:, 0], xyz[:, 1]))))
        z_min = min(z_min, float(xyz[:, 2].min()))
        z_max = max(z_max, float(xyz[:, 2].max()))
    half_width = math.ceil((radius + reach) / h) + 1
    z_low = math.floor((z_min - reach) / h) - 1
    z_high = math.ceil((z_max + reach) / h) + 1
    return DensityGrid(spacing_nm=h, half_width=half_width, z_first=z_low, nz=z_high - z_low + 1)


@dataclass(frozen=True)
class _Stencil:
    atoms: np.ndarray
    m: int
    ox: np.ndarray
    oy: np.ndarray
    oz: np.ndarray


def _stencils(widths_nm: np.ndarray, spacing_nm: float) -> list[_Stencil]:
    import numpy as np

    reach = cutoff_nm(widths_nm) / spacing_nm
    half = np.ceil(reach + 0.5).astype(np.int64)
    stencils: list[_Stencil] = []
    for m in np.unique(half).tolist():
        atoms = np.flatnonzero(half == m)
        limit = float(np.max(reach[atoms])) ** 2
        span = np.arange(-m, m + 1)
        oz, oy, ox = (axis.reshape(-1) for axis in np.meshgrid(span, span, span, indexing="ij"))
        slack = sum(np.maximum(np.abs(axis) - 0.5, 0.0) ** 2 for axis in (ox, oy, oz))
        inside = slack <= limit
        stencils.append(
            _Stencil(atoms=atoms, m=int(m), ox=ox[inside], oy=oy[inside], oz=oz[inside])
        )
    return stencils


def _accumulate(
    total: np.ndarray,
    *,
    stencil: _Stencil,
    atoms: np.ndarray,
    node: np.ndarray,
    fraction: np.ndarray,
    widths_nm: np.ndarray,
    grid: DensityGrid,
    first: int,
    last: int,
) -> None:
    import numpy as np

    h = grid.spacing_nm
    m = stencil.m
    plane = node[atoms, 2]
    start = np.searchsorted(stencil.oz, first - plane, side="left")
    lengths = np.searchsorted(stencil.oz, last - plane, side="left") - start
    reached = int(lengths.sum())
    if reached == 0:
        return
    span = np.arange(-m, m + 1, dtype=np.float64)
    scale = h / widths_nm[atoms][:, None]
    factors = [
        np.exp(-(((span[None, :] - fraction[atoms, axis][:, None]) * scale) ** 2))
        for axis in range(3)
    ]
    n = grid.n
    base = ((plane - first) * n + node[atoms, 1]) * n + node[atoms, 0]
    offset = (stencil.oz * n + stencil.oy) * n + stencil.ox
    if reached == atoms.size * stencil.oz.size:
        # The common case at the default spacing: the one-array gather is cheaper.
        g = (
            factors[0][:, stencil.ox + m]
            * factors[1][:, stencil.oy + m]
            * factors[2][:, stencil.oz + m]
        ).reshape(-1)
        keep = g >= EPSILON
        index = (base[:, None] + offset[None, :]).reshape(-1)[keep]
    else:
        row = np.repeat(np.arange(atoms.size), lengths)
        column = np.arange(reached) - np.repeat(np.cumsum(lengths) - lengths - start, lengths)
        g = (
            factors[0][row, stencil.ox[column] + m]
            * factors[1][row, stencil.oy[column] + m]
            * factors[2][row, stencil.oz[column] + m]
        )
        keep = g >= EPSILON
        index = (base[row] + offset[column])[keep]
    if index.size == 0:
        return
    # log1p(-g) at g = 1 - 2**-53 is ln 2**-53: clipping g is the floor.
    terms = np.log1p(-np.minimum(g[keep], 1.0 - 2.0**-53))
    low = int(index.min())
    counts = np.bincount(index - low, weights=terms)
    total[low : low + counts.size] += counts


def deposit(
    positions_nm: np.ndarray,
    widths_nm: np.ndarray,
    grid: DensityGrid,
    *,
    float64: bool = False,
    progress: Progress | None = None,
    cancel: CancelToken | None = None,
) -> np.ndarray:
    import numpy as np

    frames = int(positions_nm.shape[0])
    widths = np.asarray(widths_nm, dtype=np.float64)
    stencils = _stencils(widths, grid.spacing_nm)
    n = grid.n
    planes = max(1, SLAB_CELLS // (n * n))
    result = np.empty(grid.shape, dtype=np.float64 if float64 else np.float32)

    shift = np.array([grid.half_width, grid.half_width, -grid.z_first], dtype=np.int64)

    for first in range(0, grid.nz, planes):
        last = min(first + planes, grid.nz)
        mean = np.zeros((last - first) * n * n, dtype=np.float64)
        for frame in range(frames):
            check_cancelled(
                cancel,
                f"depositing frame {frame + 1} of {frames} in z planes {first}-{last - 1} "
                f"of {grid.nz}",
            )
            report(
                progress,
                (first + (last - first) * frame / frames) / grid.nz,
                f"depositing z planes {first}-{last - 1} of {grid.nz}, frame {frame + 1} "
                f"of {frames}",
            )
            # Recomputed per slab so memory does not grow with the frame count.
            scaled = np.asarray(positions_nm[frame], dtype=np.float64) / grid.spacing_nm
            nearest = np.rint(scaled)
            node = nearest.astype(np.int64) + shift
            fraction = scaled - nearest
            total = np.zeros_like(mean)
            for stencil in stencils:
                plane = node[stencil.atoms, 2]
                reached = (plane + stencil.m >= first) & (plane - stencil.m < last)
                chosen = stencil.atoms[reached]
                if chosen.size == 0:
                    continue
                chosen = chosen[np.argsort(node[chosen, 2], kind="stable")]
                size = max(1, BATCH_TERMS // stencil.ox.size)
                for start in range(0, chosen.size, size):
                    _accumulate(
                        total,
                        stencil=stencil,
                        atoms=chosen[start : start + size],
                        node=node,
                        fraction=fraction,
                        widths_nm=widths,
                        grid=grid,
                        first=first,
                        last=last,
                    )
            mean -= np.expm1(total)
        mean /= frames
        slab = mean.reshape(last - first, n, n)
        gate_density(slab, grid, first=first)
        result[first:last] = slab
        report(progress, last / grid.nz, f"deposited z planes to {last} of {grid.nz}")
    return result


def gate_density(values: np.ndarray, grid: DensityGrid, *, first: int = 0) -> None:
    import numpy as np

    bad = ~np.isfinite(values) | (values < -GATE_TOLERANCE) | (values > 1.0 + GATE_TOLERANCE)
    if not bad.any():
        return
    k, j, i = (int(value) for value in np.argwhere(bad)[0])
    value = float(values[k, j, i])
    x, y, z = grid.axis_nm("x")[i], grid.axis_nm("y")[j], grid.axis_nm("z")[first + k]
    raise DensityGateError(
        f"density gate: the map is {value!r} at voxel [z={first + k}, y={j}, x={i}], "
        f"(x, y, z) = ({x:.3f}, {y:.3f}, {z:.3f}) nm; a union density is finite and within "
        f"[0, 1] (QR-12, section 5.3.1 NOTE on geometry.density)"
    )

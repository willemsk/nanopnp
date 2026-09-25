"""Stage 2's field: the ensemble mean of per-frame probabilistic-union densities (FR-04).

Each frame's density is ``rho_f = 1 - Π_i (1 - g_i)`` over that frame's atoms, with
``g_i = exp(-d²/(sigma R_i)²)``: the probability that at least one atom is present, after
Li (2013) and the reference workflow (``.knowledge/04-clya-geometry-and-charge.md``
§1). The ensemble map is ``(1/F) Σ_f rho_f`` (WP19 D4). **A union across frames would
be wrong**: it counts a fluctuating side chain as present wherever it ever was, and
thickens every wall.

Three numerical facts decide how it is computed; the WP19 plan's Design §1 and §5
derive them.

**The product is a sum of logarithms.** ``S = Σ_i log1p(-g_i) ≤ 0`` and
``rho_f = -expm1(S)``, both accurate at either end of [0, 1]. At an atom centre
``g = 1`` and the logarithm is ``-∞``, so each term is floored at ``ln 2⁻⁵³``, below
which ``1 - rho`` is under float64's spacing at 1. S accumulates in float64.

**A term is kept iff ``g_i ≥ ε = 10⁻⁶``** — a sphere of radius ``sigma R_i √ln(1/ε)``, not a
cube. The error this makes at a voxel is at most ``Σ_dropped g/(1 - g)``, which
VER-49 asserts voxel by voxel; at the protein's heavy-atom density it is about
1e-5, four orders below the 0.25 isolevel.

**The grid is canonical.** Nodes sit at integer multiples of the spacing ``h`` in
the stage-1 frame, so the pore axis is a column of nodes and two maps of one
structure share their nodes wherever they overlap. The (x, y) square is symmetric
about the axis and one node wider than every kept term needs, which is what lets
stage 3 conserve the map exactly (D5).

The deposition is vectorised over atoms that share a stencil half-width, with the
Gaussian separable into three one-dimensional factors, and scattered with
``np.bincount`` into one z-slab at a time: never ``np.add.at``, and never a
full-grid ``minlength``, which cost a prototype 31 s in allocations alone (D6).
The loops run slabs outer and frames inner, so memory is the float32 map plus one
float64 slab and one frame's node indices, whatever the frame count.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING

from nanopnp.core.hashing import Canonicalisable
from nanopnp.core.stages import CancelToken, Progress, check_cancelled, report
from nanopnp.density.radii import DensityInputError

if TYPE_CHECKING:  # pragma: no cover - annotations only
    import numpy as np

EPSILON = 1e-6
"""A term ``g_i`` is kept iff it is at least this (section 5.2, stage 2; WP19 D4)."""

LOG_FLOOR = math.log(2.0**-53)
"""The floor on each ``log1p(-g_i)``: ``ln 2⁻⁵³ = -36.74`` (WP19 Design §1).

``1 - 2⁻⁵³`` is the largest float64 below 1, so a term at an atom centre stays
finite and still drives ``1 - rho`` below float64's spacing at 1.
"""

CUTOFF_FACTOR = math.sqrt(math.log(1.0 / EPSILON))
"""``√ln(1/ε) = 3.7169``: a kept term lies within this many widths of its atom."""

GATE_TOLERANCE = 2.0**-24
"""float32 round-off at 1, by which the stored map may leave [0, 1] before the gate fires."""

SLAB_CELLS = 4_000_000
"""Target cells per z-slab: 32 MB of float64, with each slab at least one plane thick."""

BATCH_TERMS = 1_000_000
"""Target stencil terms per vectorised batch, which bounds the batch's temporaries."""


class DensityGateError(RuntimeError):
    """The density map is not finite or leaves [0, 1] (QR-12), naming the voxel."""


@dataclass(frozen=True)
class DensityGrid:
    """The canonical stage-2 grid: nodes at integer multiples of the spacing.

    Parameters
    ----------
    spacing_nm
        ``h``, the node spacing, in every direction.
    half_width
        ``I``: the x and y nodes are ``i·h`` for ``i = -I … I``.
    z_first
        The first z node is ``z_first·h``.
    nz
        The number of z nodes.
    """

    spacing_nm: float
    half_width: int
    z_first: int
    nz: int

    @property
    def n(self) -> int:
        """Nodes along x and along y, ``2I + 1``."""
        return 2 * self.half_width + 1

    @property
    def shape(self) -> tuple[int, int, int]:
        """``(nz, ny, nx)``: the map's array shape, indexed ``[z, y, x]``."""
        return (self.nz, self.n, self.n)

    @property
    def origin_nm(self) -> tuple[float, float, float]:
        """``(x, y, z)`` of node ``[0, 0, 0]``."""
        h = self.spacing_nm
        return (-self.half_width * h, -self.half_width * h, self.z_first * h)

    def axis_nm(self, axis: str) -> np.ndarray:
        """Return the node coordinates along ``"x"``, ``"y"`` or ``"z"``, in nm."""
        import numpy as np

        h = self.spacing_nm
        if axis == "z":
            return (self.z_first + np.arange(self.nz, dtype=np.float64)) * h
        if axis in ("x", "y"):
            return np.arange(-self.half_width, self.half_width + 1, dtype=np.float64) * h
        raise ValueError(f"axis {axis!r} is not one of 'x', 'y', 'z'")

    def summary(self) -> dict[str, Canonicalisable]:
        """Return the grid as plain data, for the header and the manifest."""
        return {
            "spacing_nm": self.spacing_nm,
            "half_width": self.half_width,
            "z_first": self.z_first,
            "shape_zyx": list(self.shape),
            "origin_nm": list(self.origin_nm),
        }

    @classmethod
    def from_summary(cls, summary: dict[str, Canonicalisable]) -> DensityGrid:
        """Rebuild a grid from :meth:`summary`."""
        shape = summary["shape_zyx"]
        assert isinstance(shape, list)
        return cls(
            spacing_nm=float(summary["spacing_nm"]),
            half_width=int(summary["half_width"]),
            z_first=int(summary["z_first"]),
            nz=int(shape[0]),
        )


def cutoff_nm(width_nm: np.ndarray) -> np.ndarray:
    """Return the radius inside which each atom's term is kept, ``w √ln(1/ε)``."""
    return width_nm * CUTOFF_FACTOR


def check_positions(positions_nm: np.ndarray) -> None:
    """Refuse an ensemble holding a coordinate that is not finite, naming the frame and atom.

    Raises
    ------
    DensityInputError
        Naming the first frame and atom with a NaN or infinite coordinate.
    """
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
    """Return the grid that holds every kept term of every frame, with a node to spare (D5).

    Parameters
    ----------
    positions_nm
        ``(frames, atoms, 3)`` in the stage-1 frame.
    widths_nm
        Each atom's width ``sigma R_i``.
    spacing_nm
        ``h``.
    """
    import numpy as np

    h = float(spacing_nm)
    reach = float(np.max(cutoff_nm(widths_nm)))
    positions = np.asarray(positions_nm, dtype=np.float64)
    radius = float(np.max(np.hypot(positions[..., 0], positions[..., 1])))
    half_width = math.ceil((radius + reach) / h) + 1
    z_low = math.floor((float(np.min(positions[..., 2])) - reach) / h) - 1
    z_high = math.ceil((float(np.max(positions[..., 2])) + reach) / h) + 1
    return DensityGrid(spacing_nm=h, half_width=half_width, z_first=z_low, nz=z_high - z_low + 1)


@dataclass(frozen=True)
class _Stencil:
    """The node offsets a class of atoms may reach, sharing one half-width ``m``."""

    atoms: np.ndarray
    """Indices of the atoms in this class."""
    m: int
    ox: np.ndarray
    oy: np.ndarray
    oz: np.ndarray


def _stencils(widths_nm: np.ndarray, spacing_nm: float) -> list[_Stencil]:
    """Group the atoms by stencil half-width and build each group's offset set.

    An atom's nearest node is ``rint(x/h)``, so its fractional offset ``f`` lies in
    ``[-½, ½]`` on each axis and a node within the cutoff ``d`` of it has
    ``|o| ≤ d/h + ½``. The offsets kept are those with
    ``Σ (|o| - ½)₊² ≤ (d/h)²``, the tightest set that holds every node within ``d``
    of any atom whose nearest node is the origin: a sphere, not a cube.
    """
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
    """Add one batch's ``log1p(-g)`` terms into the slab ``[first, last)`` of z planes.

    ``node`` is each atom's nearest node as grid indices ``(i_x, i_y, i_z)``, and
    ``fraction`` its offset from it in units of ``h``.
    """
    import numpy as np

    h = grid.spacing_nm
    m = stencil.m
    span = np.arange(-m, m + 1, dtype=np.float64)
    scale = h / widths_nm[atoms][:, None]
    factors = [
        np.exp(-(((span[None, :] - fraction[atoms, axis][:, None]) * scale) ** 2))
        for axis in range(3)
    ]
    g = (
        factors[0][:, stencil.ox + m]
        * factors[1][:, stencil.oy + m]
        * factors[2][:, stencil.oz + m]
    )
    plane = node[atoms, 2][:, None] + stencil.oz[None, :]
    keep = (g >= EPSILON) & (plane >= first) & (plane < last)
    if not keep.any():
        return
    n = grid.n
    base = ((node[atoms, 2] - first) * n + node[atoms, 1]) * n + node[atoms, 0]
    offset = (stencil.oz * n + stencil.oy) * n + stencil.ox
    index = (base[:, None] + offset[None, :])[keep]
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
    """Return the ensemble-mean union density on ``grid``, float32, indexed ``[z, y, x]``.

    Parameters
    ----------
    positions_nm
        ``(frames, atoms, 3)`` in the stage-1 frame.
    widths_nm
        Each atom's Gaussian width ``sigma R_i``, in nm.
    grid
        The grid, as :func:`canonical_grid` builds it; every kept term must lie
        inside it.
    float64
        Return the float64 map the slabs accumulate rather than the float32 one
        the artefact stores (D10), so a test can hold the accumulation itself to
        float64 round-off.
    progress, cancel
        Reported and checked once per frame of each slab.

    Raises
    ------
    DensityGateError
        If the map is not finite or leaves [0, 1] by more than float32
        round-off, naming the voxel (QR-12).
    nanopnp.core.stages.Cancelled
        If ``cancel`` turns true between frames.
    """
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
            # A slab of an ensemble takes minutes, so cancellation and progress
            # are per frame within it (FR-27).
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
            # Each atom's nearest node, as grid indices, and its offset from it in
            # units of h: recomputed per slab, so memory does not grow with frames.
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
    """Refuse a map that is not finite or leaves [0, 1] beyond float32 round-off (QR-12).

    Parameters
    ----------
    values
        ``[z, y, x]`` values, or a slab of them starting at z plane ``first``.
    grid
        The grid they sit on, which places the offending voxel.

    Raises
    ------
    DensityGateError
        Naming the first offending voxel's indices, coordinates and value.
    """
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

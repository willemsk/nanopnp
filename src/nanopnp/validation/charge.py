"""The deposited fixed charge against the reference's own table (WP28, VAL-15 at Tier 3)."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from nanopnp.charge.kernel import (
    PATCH_HALF_WIDTHS,
    TILE_NM,
    SourceAtoms,
    _accumulate,
    _patches,
)
from nanopnp.core.constants import ELEMENTARY_CHARGE
from nanopnp.density.grid import RadialGrid

if TYPE_CHECKING:
    from collections.abc import Sequence

    import numpy as np

NM_TO_M = 1e-9

ALIGNMENT_TOL = 1e-6


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class PlaneDifference(_Strict):
    """One plane's cumulative charge under ``1/2 erfc((z - p)/s)``, on both grids, in e."""

    z_nm: float
    ours_e: float
    theirs_e: float
    relative: float


class AreaComparison(_Strict):
    """Two areal densities on the same nodes: totals, field differences and planes."""

    q_ours_e: float
    q_theirs_e: float
    q_relative: float
    rms_difference_C_m2: float
    max_difference_C_m2: float
    max_difference_at_nm: tuple[float, float]
    max_theirs_C_m2: float
    smoothing_nm: float
    planes: list[PlaneDifference]
    worst_plane_relative: float


def reference_construction(atoms: SourceAtoms, like: RadialGrid) -> RadialGrid:
    """Return the reference's areal density, in C m^-2, on ``like``'s nodes.

    Parameters
    ----------
    like
        The grid whose nodes to sample, the delivered table's own.
    """
    import numpy as np

    h_r, h_z = like.spacing_nm
    if not math.isclose(h_r, h_z, rel_tol=1e-12):
        raise ValueError(f"the grid is not square: spacing {like.spacing_nm} nm")
    h = h_r
    n_z, n_r = like.values.shape
    k0 = round(like.origin_nm[1] / h)
    r0 = round(like.origin_nm[0] / h)
    if (
        abs(like.origin_nm[1] / h - k0) > ALIGNMENT_TOL
        or abs(like.origin_nm[0] / h - r0) > ALIGNMENT_TOL
    ):
        raise ValueError(f"the grid's origin {like.origin_nm} nm is not a multiple of {h} nm")
    values = np.zeros((n_z, n_r), dtype=np.float64)
    tile_z = np.floor(atoms.z_nm / TILE_NM).astype(np.int64)
    tile_r = np.floor(atoms.r_nm / TILE_NM).astype(np.int64)
    order = np.lexsort((tile_r, tile_z, atoms.frame))
    keys = np.stack([atoms.frame[order], tile_z[order], tile_r[order]], axis=1)
    breaks = np.flatnonzero(np.any(np.diff(keys, axis=0) != 0, axis=1)) + 1
    for tile in np.split(order, breaks):
        r_i, z_i, w = atoms.r_nm[tile], atoms.z_nm[tile], atoms.width_nm[tile]
        z_first, z_count = _patches(z_i, w, h, k0, n_z, PATCH_HALF_WIDTHS)
        r_first, r_count = _patches(r_i, w, h, r0, n_r, PATCH_HALF_WIDTHS)
        z_span, r_span = int(z_count.max()), int(r_count.max())
        z_index = z_first[:, None] + np.arange(z_span)[None, :]
        r_index = r_first[:, None] + np.arange(r_span)[None, :]
        z_nodes = (k0 + z_index) * h
        r_nodes = (r0 + r_index) * h
        z_values = np.where(
            np.arange(z_span)[None, :] < z_count[:, None],
            np.exp(-(((z_nodes - z_i[:, None]) / w[:, None]) ** 2)),
            0.0,
        )
        r_values = np.where(
            np.arange(r_span)[None, :] < r_count[:, None],
            np.exp(-(((r_nodes - r_i[:, None]) / w[:, None]) ** 2)),
            0.0,
        )
        scale = atoms.weight_e[tile] * ELEMENTARY_CHARGE / (math.pi * (w * NM_TO_M) ** 2)
        _accumulate(values, z_first, z_values * scale[:, None], r_first, r_values)
    return RadialGrid(origin_nm=like.origin_nm, spacing_nm=like.spacing_nm, values=values)


def _embed(grid: RadialGrid, h: float, r0: int, k0: int, shape: tuple[int, int]) -> np.ndarray:
    import numpy as np

    out = np.zeros(shape, dtype=np.float64)
    i_r = round(grid.origin_nm[0] / h) - r0
    i_z = round(grid.origin_nm[1] / h) - k0
    n_z, n_r = grid.values.shape
    out[i_z : i_z + n_z, i_r : i_r + n_r] = grid.values
    return out


def compare_areal(
    ours: RadialGrid,
    theirs: RadialGrid,
    planes_nm: Sequence[float],
    *,
    smoothing_nm: float,
) -> AreaComparison:
    """Compare two areal densities in C m^-2 on the nodes they share, zero outside each.

    Parameters
    ----------
    planes_nm
        The planes of the per-plane comparison.
    smoothing_nm
        The smoothing width ``s`` of each plane's erfc profile.

    Raises
    ------
    ValueError
        If the two grids do not share one spacing and one lattice.
    """
    import numpy as np
    from scipy.special import erfc

    h = ours.spacing_nm[0]
    for grid in (ours, theirs):
        if any(not math.isclose(step, h, rel_tol=1e-12) for step in grid.spacing_nm):
            raise ValueError(
                f"the grids' spacings differ: {ours.spacing_nm} and {theirs.spacing_nm}"
            )
        for origin in grid.origin_nm:
            if abs(origin / h - round(origin / h)) > ALIGNMENT_TOL:
                raise ValueError(f"a grid's origin {grid.origin_nm} nm is off the {h} nm lattice")
    r0 = min(round(grid.origin_nm[0] / h) for grid in (ours, theirs))
    k0 = min(round(grid.origin_nm[1] / h) for grid in (ours, theirs))
    r1 = max(round(grid.origin_nm[0] / h) + grid.values.shape[1] for grid in (ours, theirs))
    k1 = max(round(grid.origin_nm[1] / h) + grid.values.shape[0] for grid in (ours, theirs))
    shape = (k1 - k0, r1 - r0)
    a = _embed(ours, h, r0, k0, shape)
    b = _embed(theirs, h, r0, k0, shape)
    union = RadialGrid(origin_nm=(r0 * h, k0 * h), spacing_nm=(h, h), values=a)
    other = RadialGrid(origin_nm=(r0 * h, k0 * h), spacing_nm=(h, h), values=b)
    q_ours = union.planar_integral() / ELEMENTARY_CHARGE
    q_theirs = other.planar_integral() / ELEMENTARY_CHARGE
    difference = a - b
    at = np.unravel_index(int(np.argmax(np.abs(difference))), difference.shape)
    z = union.z_nm
    planes = []
    for plane in planes_nm:
        weight = 0.5 * erfc((z - plane) / smoothing_nm)
        mine = union.integral(z_weight=weight) / ELEMENTARY_CHARGE
        yours = other.integral(z_weight=weight) / ELEMENTARY_CHARGE
        planes.append(
            PlaneDifference(
                z_nm=float(plane),
                ours_e=mine,
                theirs_e=yours,
                relative=(mine - yours) / abs(q_theirs),
            )
        )
    return AreaComparison(
        q_ours_e=q_ours,
        q_theirs_e=q_theirs,
        q_relative=(q_ours - q_theirs) / abs(q_theirs),
        rms_difference_C_m2=float(np.sqrt(np.mean(difference**2))),
        max_difference_C_m2=float(difference[at]),
        max_difference_at_nm=(float(union.r_nm[at[1]]), float(z[at[0]])),
        max_theirs_C_m2=float(np.max(np.abs(b))),
        smoothing_nm=smoothing_nm,
        planes=planes,
        worst_plane_relative=max((abs(entry.relative) for entry in planes), default=0.0),
    )

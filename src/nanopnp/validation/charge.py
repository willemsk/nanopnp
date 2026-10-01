"""The deposited fixed charge against the reference's own table (WP28, VAL-15 at Tier 3).

The reference built ``rhoq_pore`` as a 2D Gaussian in ``(r, z)`` about each atom's
``(r_i, z_i)``, normalised in the plane, summed over the atoms and averaged over the
frames, in ``e/m^2`` (``.knowledge/04`` §3, gap G4, G5). PHY-17 forbids that
construction in the pipeline, which sums PHY-16 step 5's azimuthal mean of a 3D
Gaussian instead. To say how much of a difference between our export and the
delivered table is that choice, Tier 3 rebuilds the reference's construction from
the same PQRs (:func:`reference_construction`) and splits the difference through
it (:func:`compare_areal`):

    ours - table = (ours - G4 rebuilt) + (G4 rebuilt - table)

The first term is the construction and the frame, the second what our
reconstruction of the reference misses: the frames, the radii, the archive's
own rounding. Both grids are areal densities, ``∫ a dr dz = Q``, in C m^-2.

Nothing here is a gate. The records are logged and written into the WP28
plan's Outcomes (section 7.1: Tier 3 is recorded, not gated).
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from nanopnp.charge.kernel import PATCH_HALF_WIDTHS, TILE_NM, SourceAtoms, _patches, _scatter
from nanopnp.core.constants import ELEMENTARY_CHARGE
from nanopnp.density.grid import RadialGrid

if TYPE_CHECKING:
    from collections.abc import Sequence

    import numpy as np

NM_TO_M = 1e-9
"""Metres per nanometre."""

ALIGNMENT_TOL = 1e-6
"""How far, in spacings, two grids' nodes may lie apart and still be the same nodes."""


class _Strict(BaseModel):
    """Base for the records here: frozen, and unknown keys are rejected."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class PlaneDifference(_Strict):
    """One plane's cumulative charge under ``1/2 erfc((z - p)/s)``, on both grids, in e."""

    z_nm: float
    ours_e: float
    theirs_e: float
    relative: float
    """``(ours - theirs) / |Q_theirs|``."""


class AreaComparison(_Strict):
    """Two areal densities on the same nodes: totals, field differences and planes."""

    q_ours_e: float
    q_theirs_e: float
    q_relative: float
    """``(Q_ours - Q_theirs) / |Q_theirs|``."""
    rms_difference_C_m2: float
    """Over the union of the two boxes, zero outside each grid."""
    max_difference_C_m2: float
    max_difference_at_nm: tuple[float, float]
    """``(r, z)`` of the largest ``|ours - theirs|``."""
    max_theirs_C_m2: float
    """The largest ``|theirs|``, the scale the two differences are read against."""
    smoothing_nm: float
    planes: list[PlaneDifference]
    worst_plane_relative: float


def reference_construction(atoms: SourceAtoms, like: RadialGrid) -> RadialGrid:
    """Return the reference's construction of the areal density on ``like``'s nodes (G4).

    ``a(r, z) = Σ_i (q_i e / n_frames) / (π w_i²) exp(-((r - r_i)² + (z - z_i)²)/w_i²)``,
    in C m^-2, each Gaussian cut to a square of half-width ``6 w_i``, as the
    pipeline cuts its own. Not renormalised: the reference was not, and the part
    of an atom's Gaussian at ``r < 0`` is lost from it, as from the table.

    Parameters
    ----------
    atoms
        The source atoms, in the frame ``like`` is in.
    like
        The grid whose nodes to sample: the delivered table's, to compare with it.
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
        z_low, r_low = int(z_first.min()), int(r_first.min())
        z_high = int((z_first + z_span).max())
        r_high = int((r_first + r_span).max())
        z_window = _scatter(z_first - z_low, z_values * scale[:, None], z_high - z_low)
        r_window = _scatter(r_first - r_low, r_values, r_high - r_low)
        z_end, r_end = min(z_high, n_z), min(r_high, n_r)
        product = z_window.T @ r_window
        values[z_low:z_end, r_low:r_end] += product[: z_end - z_low, : r_end - r_low]
    return RadialGrid(origin_nm=like.origin_nm, spacing_nm=like.spacing_nm, values=values)


def _embed(grid: RadialGrid, h: float, r0: int, k0: int, shape: tuple[int, int]) -> np.ndarray:
    """Return the values of ``grid`` in a zero array of ``shape`` whose node 0 is ``(r0, k0) h``."""
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

    The two grids must have one spacing and nodes on one lattice; a grid whose
    nodes fall between the other's is refused rather than interpolated, which
    would add an error of its own to the difference being measured.

    Parameters
    ----------
    planes_nm
        The planes of the per-plane comparison, each under ``1/2 erfc((z - p)/s)``.
    smoothing_nm
        ``s``.
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

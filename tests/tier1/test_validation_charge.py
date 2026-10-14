"""The Tier 3 charge comparison's own machinery, on atoms whose answers are known (WP28)."""

from __future__ import annotations

import math

import numpy as np
import pytest

from nanopnp.charge.kernel import SourceAtoms, sum_kernel
from nanopnp.core.constants import ELEMENTARY_CHARGE
from nanopnp.density.grid import RadialGrid
from nanopnp.validation.charge import compare_areal, reference_construction

H = 0.005


def _atoms(r_nm: float, z_nm: float, width_nm: float, charge_e: float = 1.0) -> SourceAtoms:
    return SourceAtoms(
        r_nm=np.array([r_nm]),
        z_nm=np.array([z_nm]),
        width_nm=np.array([width_nm]),
        weight_e=np.array([charge_e]),
        frame=np.zeros(1, dtype=np.int64),
        atom=np.zeros(1, dtype=np.int64),
        frames=1,
        shift_z_nm=0.0,
    )


def _grid(r_max: float, z_low: float, z_high: float) -> RadialGrid:
    r = np.arange(round(r_max / H) + 1) * H
    z = np.arange(round(z_low / H), round(z_high / H) + 1) * H
    return RadialGrid.from_axes(r, z, np.zeros((z.size, r.size)))


def test_ver01_the_rebuilt_construction_is_the_reference_2d_gaussian() -> None:
    atoms = _atoms(1.7, 0.3, 0.1, charge_e=-2.0)
    built = reference_construction(atoms, _grid(3.0, -1.0, 1.5))
    assert built.planar_integral() / ELEMENTARY_CHARGE == pytest.approx(-2.0, rel=1e-12)
    i_z, i_r = 140, 330  # z = -0.3 + ... : any node inside the patch
    r, z = float(built.r_nm[i_r]), float(built.z_nm[i_z])
    expected = (
        -2.0
        * ELEMENTARY_CHARGE
        / (math.pi * (0.1e-9) ** 2)
        * math.exp(-((r - 1.7) ** 2 + (z - 0.3) ** 2) / 0.1**2)
    )
    assert float(built.values[i_z, i_r]) == pytest.approx(expected, rel=1e-12, abs=1e-300)


# PHY-17
def test_ver01_the_rebuilt_construction_loses_the_half_across_the_axis() -> None:
    built = reference_construction(_atoms(0.0, 0.0, 0.05), _grid(1.0, -1.0, 1.0))
    assert built.planar_integral() / ELEMENTARY_CHARGE == pytest.approx(0.5, rel=1e-12)
    kernel = sum_kernel(_atoms(0.0, 0.0, 0.05), H).grid
    assert kernel.planar_integral() / ELEMENTARY_CHARGE == pytest.approx(1.0, rel=1e-12)


# PHY-16
def test_ver01_the_two_constructions_differ_at_first_order_and_odd_about_the_atom() -> None:
    width = 0.1
    for ratio in (10.0, 20.0, 40.0):
        r_i = ratio * width
        atoms = _atoms(r_i, 0.0, width)
        ours = sum_kernel(atoms, H).grid
        theirs = reference_construction(atoms, ours)
        comparison = compare_areal(ours, theirs, (-0.05, 0.0, 0.05), smoothing_nm=0.5)
        assert abs(comparison.q_relative) < 1e-12
        assert comparison.worst_plane_relative < 1e-12
        peak = abs(comparison.max_difference_C_m2) / comparison.max_theirs_C_m2
        assert peak == pytest.approx(width / (2.0 * r_i) / math.sqrt(2.0 * math.e), rel=0.02)
        centroid = [
            float(grid.r_nm @ grid.values.sum(axis=0) / grid.values.sum())
            for grid in (ours, theirs)
        ]
        assert centroid[0] - centroid[1] == pytest.approx(width**2 / (4.0 * r_i), rel=0.02)


def test_ver01_the_comparison_aligns_offset_grids_by_their_nodes() -> None:
    atoms = _atoms(2.0, 1.0, 0.1)
    ours = sum_kernel(atoms, H).grid
    wide = reference_construction(atoms, _grid(4.0, -2.0, 4.0))
    narrow = reference_construction(atoms, ours)
    comparison = compare_areal(wide, narrow, (0.5, 1.0, 1.5), smoothing_nm=0.5)
    assert comparison.rms_difference_C_m2 == 0.0
    assert comparison.q_relative == 0.0
    shifted = RadialGrid(
        origin_nm=(ours.origin_nm[0], ours.origin_nm[1] + 0.5 * H),
        spacing_nm=ours.spacing_nm,
        values=ours.values,
    )
    with pytest.raises(ValueError, match="off the"):
        compare_areal(ours, shifted, (1.0,), smoothing_nm=0.5)

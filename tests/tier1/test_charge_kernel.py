"""VER-58, Tier 1: the closed-form azimuthal kernel and its sum on the export lattice (WP28 D1, D2).

Every oracle is a route the implementation does not take. The kernel's integral
is checked by adaptive quadrature of the closed form; the closed form against
the literal PHY-16 steps 4-5 -- a 3D Cartesian Gaussian binned by the exact
annular weights of VER-50 -- in the limit of fine spacing; the tiled sum against
a direct per-atom outer product; the axis deficit against the Euler-Maclaurin
end correction ``-h^2/(6 w^2)`` (`.knowledge/04` §3.3).
"""

from __future__ import annotations

import logging
import math

import numpy as np
import pytest
from scipy.integrate import quad
from scipy.special import erfc, i0e

from nanopnp.charge.fields import ChargeFieldError
from nanopnp.charge.kernel import (
    PATCH_HALF_WIDTHS,
    SourceAtoms,
    areal_density,
    atom_lattice_sum,
    check_spacing,
    lattice_axes,
    sum_kernel,
    volume_density,
)
from nanopnp.core.constants import ELEMENTARY_CHARGE
from nanopnp.core.stages import CancelFlag, Cancelled
from nanopnp.symmetry.annular import annular_weights

logger = logging.getLogger(__name__)

H = 0.005
"""The default export lattice spacing, nm (PHY-16 step 6)."""


def _atoms(
    r_nm: list[float],
    z_nm: list[float],
    width_nm: list[float],
    charge_e: list[float],
    *,
    frames: int = 1,
) -> SourceAtoms:
    """Return source atoms given directly, one frame unless told otherwise."""
    count = len(r_nm)
    return SourceAtoms(
        r_nm=np.asarray(r_nm, dtype=np.float64),
        z_nm=np.asarray(z_nm, dtype=np.float64),
        width_nm=np.asarray(width_nm, dtype=np.float64),
        weight_e=np.asarray(charge_e, dtype=np.float64) / frames,
        frame=np.arange(count, dtype=np.int64) % frames,
        atom=np.arange(count, dtype=np.int64),
        frames=frames,
        shift_z_nm=0.0,
    )


@pytest.mark.parametrize("ratio", [0.0, 0.3, 1.0, 3.0, 30.0, 600.0])
def test_ver58_kernel_integrates_to_its_charge(ratio: float) -> None:
    """The closed form integrates to ``q`` under ``2 pi r dr dz`` to 1e-12, at any ``r_i/w``."""
    width = 0.1
    r_i = ratio * width
    # Separable: the z factor integrates to w sqrt(pi) exactly, and the r factor
    # by adaptive quadrature over the twelve widths that carry it.
    low, high = max(0.0, r_i - 12.0 * width), r_i + 12.0 * width
    radial, error = quad(
        lambda r: float(areal_density(np.array([r]), np.array([0.0]), r_i, 0.0, width)[0]),
        low,
        high,
        points=[r_i] if low < r_i < high else None,
        epsabs=0.0,
        epsrel=1e-13,
        limit=400,
    )
    total = radial * width * math.sqrt(math.pi)
    logger.info("r_i/w = %g: integral %.16f (quadrature error %.1e)", ratio, total, error)
    assert abs(total - 1.0) < 1e-12


def test_ver58_kernel_is_finite_and_even_on_the_axis() -> None:
    """The volume density is finite on the axis and even across it (PHY-17)."""
    width = 0.08
    for r_i in (0.0, 0.05, 0.4):
        radius = np.array([-1e-4, -1e-6, 0.0, 1e-6, 1e-4])
        values = volume_density(radius, np.full(5, 0.01), r_i, 0.0, width)
        assert np.all(np.isfinite(values))
        assert np.allclose(values, values[::-1], rtol=1e-15, atol=0.0)
        # The even extension has no kink: the one-sided slopes vanish with the step.
        slope = (values[3] - values[2]) / 1e-6
        assert abs(slope) * width / max(values[2], 1e-300) < 1e-3


def test_ver58_kernel_is_the_limit_of_the_3d_deposition_binned_by_annular_weights() -> None:
    """PHY-16 steps 4-5 run literally converge to the closed form: >= 3.5x per halving, < 1e-3.

    A 3D Cartesian Gaussian sampled on a plane at three spacings and binned by
    the exact annular overlap weights of VER-50, against the closed form
    integrated over each annulus by Gauss-Legendre.
    """
    width, r_i, theta = 0.1, 0.3, 0.4
    x_i, y_i = r_i * math.cos(theta), r_i * math.sin(theta)
    nodes, gauss = np.polynomial.legendre.leggauss(20)
    errors: list[float] = []
    for spacing in (0.02, 0.01, 0.005):
        half = math.ceil((r_i + PATCH_HALF_WIDTHS * width) / spacing) + 2
        axis = np.arange(-half, half + 1) * spacing
        y, x = np.meshgrid(axis, axis, indexing="ij")
        plane = math.pi**-1.5 * width**-3 * np.exp(-((x - x_i) ** 2 + (y - y_i) ** 2) / width**2)
        binned = annular_weights(half, spacing).matrix @ plane.reshape(-1)
        reference = np.empty(half + 1)
        for j in range(half + 1):
            low, high = max(0.0, (j - 0.5) * spacing), (j + 0.5) * spacing
            r = 0.5 * (high - low) * nodes + 0.5 * (high + low)
            values = areal_density(r, np.zeros_like(r), r_i, 0.0, width)
            reference[j] = 0.5 * (high - low) * float(np.sum(gauss * values))
        errors.append(float(np.max(np.abs(binned - reference)) / np.max(np.abs(reference))))
    rates = [errors[index] / errors[index + 1] for index in range(2)]
    logger.info("3D deposition binned against the closed form: errors %s, rates %s", errors, rates)
    assert min(rates) >= 3.5
    assert errors[-1] < 1e-3


def test_ver58_tiled_sum_equals_the_direct_sum() -> None:
    """The tiled dense products equal a per-atom outer product of the separable factors to 1e-13."""
    rng = np.random.default_rng(58)
    count = 400
    r = rng.uniform(0.0, 1.8, count)
    r[:5] = [0.0, 0.004, 0.02, 0.6, 1.0]
    z = rng.uniform(-1.0, 1.0, count)
    width = rng.choice([0.0112, 0.05, 0.085, 0.11], count)
    charge = rng.normal(0.0, 0.4, count)
    atoms = _atoms(r.tolist(), z.tolist(), width.tolist(), charge.tolist(), frames=2)
    lattice = sum_kernel(atoms, H)
    grid = lattice.grid

    r_axis, z_axis = grid.r_nm, grid.z_nm
    tau_r = np.ones_like(r_axis)
    tau_r[[0, -1]] = 0.5
    tau_z = np.ones_like(z_axis)
    tau_z[[0, -1]] = 0.5
    direct = np.zeros_like(grid.values)
    for row in range(count):
        w = atoms.width_nm[row]
        z_mask = np.abs(z_axis - atoms.z_nm[row]) <= PATCH_HALF_WIDTHS * w + 1e-12
        r_mask = np.abs(r_axis - atoms.r_nm[row]) <= PATCH_HALF_WIDTHS * w + 1e-12
        z_factor = np.where(z_mask, np.exp(-(((z_axis - atoms.z_nm[row]) / w) ** 2)), 0.0)
        r_factor = np.where(
            r_mask,
            2.0
            * math.pi
            * r_axis
            * np.exp(-(((r_axis - atoms.r_nm[row]) / w) ** 2))
            * i0e(2.0 * r_axis * atoms.r_nm[row] / w**2),
            0.0,
        )
        lattice_sum = float(tau_z @ z_factor) * float(tau_r @ r_factor) * (H * 1e-9) ** 2
        scale = atoms.weight_e[row] * ELEMENTARY_CHARGE / lattice_sum
        direct += scale * np.outer(z_factor, r_factor)
    error = float(np.max(np.abs(grid.values - direct)) / np.max(np.abs(direct)))
    logger.info("tiled against direct: %.2e", error)
    assert error < 1e-13
    total = grid.planar_integral() / ELEMENTARY_CHARGE
    assert abs(total - atoms.q_net_e()) <= 1e-12 * float(np.sum(np.abs(charge)))


def test_ver58_unrenormalised_axis_sum_is_short_by_the_end_correction() -> None:
    """On the axis the raw sum is short by ``h^2/(6 w^2)`` to 10 %; renormalised it is exact."""
    width = 0.05
    predicted = -(H**2) / (6.0 * width**2)
    raw = atom_lattice_sum(0.0, 0.0, width, H) - 1.0
    logger.info("on-axis raw deficit %.4e against -h^2/(6 w^2) = %.4e", raw, predicted)
    assert raw == pytest.approx(predicted, rel=0.1)
    # Off the axis the trapezoid rule on a Gaussian is exact to round-off.
    assert abs(atom_lattice_sum(3.0, 0.0, 0.0112, H) - 1.0) < 1e-14

    atoms = _atoms([0.0], [0.0], [width], [1.0])
    renormalised = sum_kernel(atoms, H).grid.planar_integral() / ELEMENTARY_CHARGE
    broken = sum_kernel(atoms, H, renormalise=False)
    assert renormalised == pytest.approx(1.0, abs=1e-14)
    assert broken.grid.planar_integral() / ELEMENTARY_CHARGE - 1.0 == pytest.approx(raw, rel=1e-9)
    assert broken.raw_deviation[0] == pytest.approx(abs(raw), rel=1e-12)


def test_ver58_lattice_has_a_node_on_the_axis_and_clears_the_atoms() -> None:
    """The lattice starts at ``r = 0``, puts ``z`` on multiples of ``h``, and clears 6 ``w_max``."""
    atoms = _atoms([1.0, 2.5], [-0.31, 0.77], [0.05, 0.1], [1.0, -1.0])
    n_r, k0, n_z = lattice_axes(atoms, H)
    grid = sum_kernel(atoms, H).grid
    assert grid.origin_nm[0] == 0.0
    assert grid.shape == (n_r, n_z)
    assert grid.origin_nm[1] == pytest.approx(k0 * H, abs=1e-15)
    (_, r_max), (z_min, z_max) = grid.extent_nm
    reach = PATCH_HALF_WIDTHS * 0.1
    assert r_max >= 2.5 + reach
    assert z_min <= -0.31 - reach
    assert z_max >= 0.77 + reach
    # Nothing reaches the boundary ring: the box is the support, snapped outward.
    assert grid.boundary_ring_maximum().value <= 1e-12 * grid.interior_maximum()


def test_ver58_spacing_above_half_the_narrowest_width_is_refused_naming_the_atom() -> None:
    """``h > w_min / 2`` is refused, naming the atom and both lengths (PHY-16 NOTE)."""
    atoms = _atoms([1.0, 1.2], [0.0, 0.0], [0.1, 0.0112], [1.0, -1.0])
    check_spacing(atoms, 0.0056)
    with pytest.raises(ChargeFieldError) as raised:
        check_spacing(atoms, 0.0057)
    message = str(raised.value)
    assert "atom 1 of frame 0" in message
    assert "0.0112" in message
    assert "grid_spacing_nm" in message
    with pytest.raises(ChargeFieldError, match="no charged atom"):
        sum_kernel(_atoms([], [], [], []), H)


def test_ver58_source_cumulative_is_the_closed_form_marginal() -> None:
    """The per-plane reference ``q 1/2 erfc((z_i - p)/sqrt(s^2 + w^2))`` agrees with quadrature."""
    atoms = _atoms([1.0], [0.2], [0.1], [1.0])
    plane, smoothing = 0.35, 0.5
    (closed,) = atoms.cumulative_e((plane,), smoothing_nm=smoothing)

    def marginal(z: float) -> float:
        return math.exp(-((z - 0.2) ** 2) / 0.1**2) / (0.1 * math.sqrt(math.pi))

    numeric, _ = quad(
        lambda z: marginal(z) * 0.5 * float(erfc((z - plane) / smoothing)),
        -2.0,
        2.0,
        epsabs=0.0,
        epsrel=1e-13,
        limit=200,
    )
    assert closed == pytest.approx(numeric, rel=1e-12)
    # And the lattice agrees with it once summed: the z-marginal survives exactly.
    grid = sum_kernel(atoms, H).grid
    weight = 0.5 * erfc((grid.z_nm - plane) / smoothing)
    assert grid.integral(z_weight=weight) / ELEMENTARY_CHARGE == pytest.approx(closed, rel=1e-12)


def test_ver58_sum_cancels_between_frames() -> None:
    """A set token stops the sum before its first frame (FR-27, D12)."""
    flag = CancelFlag()
    flag.cancel()
    with pytest.raises(Cancelled, match="frame 0"):
        sum_kernel(_atoms([1.0], [0.0], [0.1], [1.0]), H, cancel=flag)

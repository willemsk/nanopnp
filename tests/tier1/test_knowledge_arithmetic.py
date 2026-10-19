"""VER-68, G8: executable checks for calculations recorded in the knowledge bundle (WP48 D2)."""

from __future__ import annotations

import math

import numpy as np
import pytest
from scipy.integrate import quad
from scipy.special import erfc, iv

from nanopnp.charge.kernel import areal_density
from nanopnp.core.constants import (
    AVOGADRO,
    BOLTZMANN,
    ELEMENTARY_CHARGE,
    GAS_CONSTANT,
    VACUUM_PERMITTIVITY,
)
from nanopnp.core.hashing import SHORT_LENGTH
from nanopnp.geometry import contour
from nanopnp.materials.electrolyte import Electrolyte
from nanopnp.mesh.primitives import CylindricalPoreGeometry
from nanopnp.physics import models
from nanopnp.physics.coefficients import (
    SATURATED_WALL_DISTANCE_NM,
    NondimensionalCoefficients,
    mesh_unit_scales,
)
from nanopnp.physics.flow import strain_rate
from nanopnp.physics.nernst_planck import ConcentrationVariables, excess_potential_gradient
from nanopnp.solve.continuation import transfer
from nanopnp.validation.attribution import Attribution
from nanopnp.validation.geometry import pqr2grid_radius


def test_permittivity_cap_gavish_and_buchner_at_5_3_m() -> None:
    from nanopnp.materials.forms import gavish_langevin

    shipped = Electrolyte.from_parameter_file("willems2020_nacl")
    buchner_p = {"P0": 78.15, "P1": 29.50, "P2": 11.74}
    eps_gavish = float(shipped.relative_permittivity(5.3))
    eps_buchner = 78.15 * float(gavish_langevin(buchner_p, 5.3))
    assert eps_gavish == pytest.approx(42.67, abs=0.01)
    assert eps_buchner == pytest.approx(42.13, abs=0.01)
    assert abs(eps_gavish - eps_buchner) / eps_gavish == pytest.approx(0.0127, abs=2e-3)
    eps_1m_g = float(shipped.relative_permittivity(1.0))
    eps_1m_b = 78.15 * float(gavish_langevin(buchner_p, 1.0))
    assert abs(eps_1m_g - eps_1m_b) / eps_1m_g < 5e-3


def test_md_restraint_and_isolated_atom_isolevel() -> None:
    kcal_mol_a2_to_pn_nm = 4184.0 / AVOGADRO / 1e-20 * 1e3
    assert kcal_mol_a2_to_pn_nm == pytest.approx(694.77, abs=0.05)
    sigma = 0.93
    factor = sigma * math.sqrt(math.log(4.0))
    assert math.sqrt(math.log(4.0)) == pytest.approx(1.17741, abs=1e-4)
    assert factor == pytest.approx(1.095, abs=5e-4)
    assert math.exp(-(factor**2) / sigma**2) == pytest.approx(0.25, rel=1e-12)


def test_pqr2grid_bin_width_and_coordinate_shift() -> None:
    h = 0.05
    for length_nm, expected_ratio in ((15.0, 1.0316), (6.75, 1.0701)):
        nx = round(2.0 * length_nm / h) + 1
        w = (2.0 * length_nm + 1.0) / nx
        assert w / h == pytest.approx(expected_ratio, abs=1e-4)
    assert pqr2grid_radius(1.65) == pytest.approx(1.5744, abs=1e-4)
    assert pqr2grid_radius(5.66) == pytest.approx(5.4615, abs=1e-4)


def test_taubin_circulant_pass_band_and_staircase_attenuation() -> None:
    lam, mu, passes = contour.TAUBIN_LAMBDA, contour.TAUBIN_MU, contour.TAUBIN_PASSES
    assert (lam, mu, passes) == (0.5, -0.53, 10)

    def gain(k: float) -> float:
        return float(((1.0 - lam * k) * (1.0 - mu * k)) ** passes)

    wavelength = 13.08
    k_pass = 1.0 - math.cos(2.0 * math.pi / wavelength)
    assert gain(k_pass) == pytest.approx(1.0, abs=5e-3)
    assert wavelength * 0.025 == pytest.approx(0.327, abs=5e-3)
    assert gain(1.0) == pytest.approx(0.069, abs=1e-3)


def test_exclusion_shell_planar_chi_mean() -> None:
    delta_nm, a_nm = 0.15, 0.25
    assert 3.0 * delta_nm / (32.0 * a_nm) == pytest.approx(0.05625, rel=1e-12)


def test_charge_kernel_z_marginal_and_erfc_cumulative() -> None:
    r_i, z_i, w, s, p = 0.8, 0.3, 0.12, 0.09, 0.25
    integral, _ = quad(
        lambda z: float(
            quad(
                lambda r: (
                    float(areal_density(np.array([r]), np.array([z]), r_i, z_i, w)[0])
                    * 0.5
                    * float(erfc((z - p) / s))
                ),
                0.0,
                r_i + 12.0 * w,
                epsabs=0.0,
                epsrel=1e-12,
            )[0]
        ),
        z_i - 12.0 * w,
        z_i + 12.0 * w,
        epsabs=0.0,
        epsrel=1e-12,
    )
    closed = 0.5 * float(erfc((z_i - p) / math.hypot(s, w)))
    assert integral == pytest.approx(closed, rel=1e-11)


def test_reynolds_number_and_pspg_parameter_at_reference_scales() -> None:
    electrolyte = Electrolyte.from_parameter_file("willems2020_nacl")
    scales = mesh_unit_scales(electrolyte, 1.0)
    coeffs = NondimensionalCoefficients(
        electrolyte=electrolyte,
        scales=scales,
        concentrations={"Na+": 1.0, "Cl-": 1.0},
        wall_distance_nm=SATURATED_WALL_DISTANCE_NM,
    )
    assert coeffs.reynolds == pytest.approx(6.0e-4, abs=3.0e-5)
    h_k = 0.03
    convective = 2.0 * 6.0e-4 / h_k
    viscous = 4.0 / (h_k**2)
    tau_m = (convective**2 + viscous**2) ** -0.5
    pure_pspg = h_k**2 / 4.0
    assert convective == pytest.approx(4.0e-2, rel=1e-12)
    assert viscous == pytest.approx(4.444444e3, rel=1e-6)
    assert tau_m == pytest.approx(pure_pspg, rel=1e-5)
    tau_c = 6.0e-4 * 1.0 * 1.0 * h_k / 2.0
    assert tau_c == pytest.approx(9.0e-6, rel=1e-12)


def test_concentration_rung_transfer_copies_vector_entries() -> None:
    mesh = CylindricalPoreGeometry(
        pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0
    ).generate(maxh_nm=4.0)
    low = models.create("pnp", concentration_M=0.05, classical=True)
    high = models.create("pnp", concentration_M=1.0, classical=True)
    space = low.space(mesh)
    state = low.cold_state(mesh)
    state.vec.FV().NumPy()[:] = np.linspace(0.1, 1.5, space.ndof)
    sol = models.ModelSolution(model=low, space=space, state=state)
    moved = transfer(sol, high, mesh)
    assert low.scales.debye_length_nm != high.scales.debye_length_nm
    assert np.array_equal(moved.state.vec.FV().NumPy(), state.vec.FV().NumPy())


def test_axisymmetric_strain_rate_omits_hoop_component_and_stress_contraction_is_2x2() -> None:
    import ngsolve as ngs
    from netgen.occ import OCCGeometry, Rectangle

    mesh = ngs.Mesh(OCCGeometry(Rectangle(1.0, 1.0).Face(), dim=2).GenerateMesh(maxh=0.5))
    vec = ngs.VectorH1(mesh, order=2)
    u = ngs.GridFunction(vec)
    u.Set(ngs.CF((0.3 * ngs.x + 0.1 * ngs.y, -0.2 * ngs.x + 0.4 * ngs.y)))
    sym = strain_rate(u)
    assert tuple(sym.dims) == (2, 2)
    point = mesh(0.4, 0.4)
    expected = ((0.3, -0.05), (-0.05, 0.4))
    for i in range(2):
        for j in range(2):
            assert float(sym[i, j](point)) == pytest.approx(expected[i][j], abs=1e-12)


def test_ngsolve_physics_small_facts() -> None:
    import ngsolve as ngs
    from netgen.occ import OCCGeometry, Rectangle

    electrolyte = Electrolyte.from_parameter_file("willems2020_nacl")
    scales = mesh_unit_scales(electrolyte, 3.0)
    lambda_tilde = scales.debye_length_nm / 2.0
    assert 1.0 / (lambda_tilde**2) == pytest.approx(130.0, rel=0.05)

    mesh = ngs.Mesh(OCCGeometry(Rectangle(1.0, 1.0).Face(), dim=2).GenerateMesh(maxh=0.5))
    space = ngs.H1(mesh, order=2)
    v = space.TestFunction()
    integral = v * ngs.ds("default")
    with pytest.raises(TypeError):
        _ = -integral  # type: ignore[operator]

    phi = ngs.GridFunction(space)
    phi.Set(0.3 * ngs.x * ngs.x - 0.2 * ngs.x * ngs.y + 0.5 * ngs.y * ngs.y)
    c_na = ngs.GridFunction(space)
    c_cl = ngs.GridFunction(space)
    c_na.Set(1.0 + 0.1 * ngs.x)
    c_cl.Set(1.0 - 0.1 * ngs.y)
    variables = ConcentrationVariables.primitive({"Na+": c_na, "Cl-": c_cl})
    coeffs = NondimensionalCoefficients(
        electrolyte=electrolyte,
        scales=scales,
        concentrations=variables.values,
        wall_distance_nm=SATURATED_WALL_DISTANCE_NM,
    )
    grad_phi_ex = excess_potential_gradient(
        "Na+", coefficients=coeffs, variables=variables, potential=phi
    )
    pt = mesh(0.4, 0.4)
    assert all(math.isfinite(float(grad_phi_ex[i](pt))) for i in range(2))


def test_short_hash_collision_probability_bound() -> None:
    assert SHORT_LENGTH == 12
    n = 3675 * 6
    space = float(16**SHORT_LENGTH)
    prob = (n**2) / (2.0 * space)
    assert prob == pytest.approx(8.6e-7, rel=2e-2)


def test_gouy_chapman_and_debye_huckel_closed_forms() -> None:
    eps = VACUUM_PERMITTIVITY * 78.15
    c0_mol_m3 = 100.0
    vt = BOLTZMANN * 298.15 / ELEMENTARY_CHARGE
    lambda_d = math.sqrt(
        eps * GAS_CONSTANT * 298.15 / (2.0 * (ELEMENTARY_CHARGE * AVOGADRO) ** 2 * c0_mol_m3)
    )
    zeta_tilde = 2.0

    def phi_gc(x: float) -> float:
        return 4.0 * vt * math.atanh(math.tanh(zeta_tilde / 4.0) * math.exp(-x / lambda_d))

    dx = 1e-7 * lambda_d
    dphi_dx_0 = (phi_gc(dx) - phi_gc(0.0)) / dx
    sigma_from_slope = -eps * dphi_dx_0
    sigma_grahame = math.sqrt(8.0 * eps * GAS_CONSTANT * 298.15 * c0_mol_m3) * math.sinh(
        zeta_tilde / 2.0
    )
    assert sigma_from_slope == pytest.approx(sigma_grahame, rel=1e-6)

    a = 2.0e-9
    r = 0.7e-9
    dr = 1e-4 * lambda_d

    def phi_dh(rad: float) -> float:
        return float(iv(0, rad / lambda_d) / iv(0, a / lambda_d))

    d2 = (phi_dh(r + dr) - 2.0 * phi_dh(r) + phi_dh(r - dr)) / (dr**2)
    d1 = (phi_dh(r + dr) - phi_dh(r - dr)) / (2.0 * dr)
    laplacian = d2 + d1 / r
    assert laplacian == pytest.approx(phi_dh(r) / (lambda_d**2), rel=1e-6)


def test_telescoping_identity_round_off_scales_with_error_magnitude() -> None:
    rng = np.random.default_rng(13)
    for low, high, min_fail in ((0.0, 2.0, 0.0), (10.0, 100.0, 0.01), (100.0, 1000.0, 0.10)):
        draws = rng.uniform(low, high, size=(5000, 4))
        e0, e1, e2, e3 = draws[:, 0], draws[:, 1], draws[:, 2], draws[:, 3]
        residual = np.abs((e0 + (e1 - e0) + (e2 - e1) + (e3 - e2)) - e3)
        fail_rate = float(np.mean(residual > 1e-14))
        if min_fail == 0.0:
            assert fail_rate == 0.0
        else:
            assert fail_rate >= min_fail
    large = Attribution(key="potential", kind="field", errors=(500.0, 120.0, 800.0, 310.0))
    assert abs(large.identity_residual()) <= 1e-14 * max(1.0, *large.errors)


def test_limiting_current_depletion_debye_and_mobility_ratios() -> None:
    from nanopnp.core.scaling import debye_length_nm

    epnpns = Electrolyte.from_parameter_file("willems2020_nacl")
    mu_ratio = epnpns.mobility("Na+", 1.0, 50.0) / epnpns.ion("Na+").mobility_0
    d_ratio = epnpns.diffusivity("Na+", 1.0, 50.0) / epnpns.ion("Na+").diffusivity_0
    assert mu_ratio == pytest.approx(0.63, abs=0.01)
    assert d_ratio == pytest.approx(0.92, abs=0.01)
    assert debye_length_nm(0.001) == pytest.approx(9.6, abs=0.05)

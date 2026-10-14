"""VER-22 and NUM-29 (with NUM-28, PHY-23): the three NUM-28 force routes on one solution."""

import ngsolve as ngs
import pytest

from nanopnp.geometry.analyte import AnalyteInBoxGeometry, SphereBody
from nanopnp.numerics.measures import AXISYMMETRIC, FixedCharge
from nanopnp.physics import models
from nanopnp.physics.models import CoupledBoundaries, CoupledModel
from nanopnp.post.forces import FORCE_ROUTE_TOLERANCE_N, AnalyteForces, axial_extension, extract

RADIUS_NM, OUTER_NM = 2.0, 12.0

CONCENTRATION_M = 0.3

FIELD = 0.2

# Charge scale of SPECIFICATION.md RSK-04 (both force halves reach 10 pN).
CHARGE_E = -20.0

MESH = (0.8, 0.1)

SHELL_NM = (2.5, 6.0)

# NUM-29
ORACLE_TOLERANCE_N = 1e-15


# NUM-29, VER-22
@pytest.fixture(scope="module")
def forces() -> tuple[CoupledModel, AnalyteForces]:
    body = SphereBody(radius_nm=RADIUS_NM)
    model = models.create(
        "pnp-ns",
        concentration_M=CONCENTRATION_M,
        inertia=False,
        variable_density=False,
        pressure_constraint=True,
        solid_permittivities={"analyte": 20.0},
    )
    assert isinstance(model, CoupledModel)
    mesh = AnalyteInBoxGeometry(body, outer_radius_nm=OUTER_NM).generate(
        maxh_nm=MESH[0], wall_h_nm=MESH[1]
    )
    density = body.charge_density_C_m3(CHARGE_E) / model.scales.charge_density_C_m3
    solution = model.solve(
        mesh,
        AXISYMMETRIC,
        boundaries=CoupledBoundaries(
            potential="outer",
            concentration="outer",
            velocity="analyte|outer",
            velocity_axis="axis",
        ),
        potential_values=-FIELD * ngs.y,
        velocity_values=ngs.CF((0.0, 0.0)),
        fixed_charge=FixedCharge(mesh.MaterialCF({"analyte": density}, default=0.0), None),
    )
    extension = axial_extension(mesh, inner_nm=SHELL_NM[0], outer_nm=SHELL_NM[1])
    return model, extract(solution, AXISYMMETRIC, extension)


def test_ver22_both_halves_of_the_force_are_large_and_opposed(
    forces: tuple[CoupledModel, AnalyteForces],
) -> None:
    model, result = forces
    split = result.forces
    unit_N = model.scales.force_N
    assert split.em_N < -5e-12 < 0.0 < 5e-12 < split.hd_N, (
        f"F^em = {split.em_N * 1e12:+.4f} pN and F^hd = {split.hd_N * 1e12:+.4f} pN are not the "
        "opposed, several-piconewton pair this test is posed to produce; the route agreements "
        "below would then be checking a force with a single origin"
    )
    assert abs(split.total_N) < 0.6 * min(abs(split.em_N), abs(split.hd_N)), (
        f"the net {split.total_N * 1e12:+.4f} pN is not small against its parts "
        f"({split.em_N * 1e12:+.4f} and {split.hd_N * 1e12:+.4f} pN), so this is no longer the "
        "near-cancellation RSK-04 describes"
    )
    assert unit_N == pytest.approx(4.5677e-13, rel=1e-4), (
        f"the force unit eps V_T^2 came out at {unit_N:.6e} N; the 0.1 pN of NUM-29 is "
        f"{FORCE_ROUTE_TOLERANCE_N / unit_N:.3f} in these variables and this test's margins "
        "are quoted against it"
    )


def test_ver22_the_domain_and_surface_routes_agree_to_better_than_a_tenth_of_a_piconewton(
    forces: tuple[CoupledModel, AnalyteForces],
) -> None:
    _, result = forces
    agreement = result.agreement
    assert agreement is not None, "extract was asked to check the routes and did not"
    difference_N = agreement.total_difference_N
    assert difference_N < FORCE_ROUTE_TOLERANCE_N, (
        f"the domain route gives {agreement.domain.total_N * 1e12:+.4f} pN and the surface route "
        f"{agreement.surface.total_N * 1e12:+.4f} pN, {difference_N * 1e12:.4f} pN apart, beyond "
        f"the NUM-29 tolerance of {FORCE_ROUTE_TOLERANCE_N * 1e12:.1f} pN"
    )


def test_ver22_the_reaction_route_confirms_the_hydrodynamic_split(
    forces: tuple[CoupledModel, AnalyteForces],
) -> None:
    _, result = forces
    agreement = result.agreement
    assert agreement is not None, "extract was asked to check the routes and did not"
    assert agreement.reaction_hd_N is not None, "route C was not taken"
    difference_N = agreement.hydrodynamic_difference_N
    assert difference_N < ORACLE_TOLERANCE_N, (
        f"route A puts F^hd at {agreement.domain.hd_N * 1e12:+.4f} pN and route C at "
        f"{agreement.reaction_hd_N * 1e12:+.4f} pN, {difference_N * 1e12:.5f} pN apart. C is a "
        "discrete identity, so a gap this large is a missing or mis-signed consistency term in "
        "the domain form rather than quadrature error"
    )


# NUM-28, PHY-23
def test_ver22_the_korteweg_helmholtz_residual_vanishes_in_the_classical_model(
    forces: tuple[CoupledModel, AnalyteForces],
) -> None:
    _, result = forces
    assert result.dielectric_gradient_N == pytest.approx(0.0, abs=1e-18), (
        f"the classical model reports {result.dielectric_gradient_N * 1e12:.3e} pN of "
        "Korteweg-Helmholtz force; with grad(eps) = 0 there is nothing for it to come from"
    )
    record = result.summary()
    assert record["two_pi_included"] is True, "the 2 pi of NUM-27 is not recorded as restored"
    assert record["routes_checked"] is True, "the summary does not record that NUM-29 was checked"

"""VER-20: the Maxwell stress on a dielectric sphere in a uniform field."""

import math

import ngsolve as ngs
import pytest

from nanopnp.core.constants import ELEMENTARY_CHARGE
from nanopnp.core.scaling import REFERENCE_PERMITTIVITY, Scales
from nanopnp.geometry.analyte import AnalyteInBoxGeometry, SphereBody
from nanopnp.numerics.linear import solve_linear
from nanopnp.numerics.measures import AXISYMMETRIC
from nanopnp.physics.models import set_boundary_values
from nanopnp.physics.poisson import charge_source, poisson_operator
from nanopnp.post.forces import (
    axial_extension,
    electrostatic_domain_force,
    electrostatic_surface_force,
)

RADIUS_NM, OUTER_NM = 1.0, 10.0

FIELD = 0.5

# PHY-20
ANALYTE_PERMITTIVITY = 20.0

# Haemoglobin charge at pH 7.4: the PlyAB reference.
CHARGE_E = -4.0

MESH = (0.4, 0.08)

SHELL_NM = (1.5, 4.0)

# NUM-29
ZERO_TOLERANCE_N = 1e-15

# Tolerance on F_z = q E_0: SPECIFICATION.md VER-20.
ANCHOR_TOLERANCE = 0.01

# NUM-09
SCALES = Scales(length_nm=1.0, concentration_M=0.3)


def _solve(
    mesh: ngs.Mesh, permittivity: ngs.CoefficientFunction, charge_density: ngs.CoefficientFunction
) -> ngs.GridFunction:
    space = ngs.H1(mesh, order=2, dirichlet="outer")
    potential = ngs.GridFunction(space, name="phi_tilde")
    set_boundary_values(potential, -FIELD * ngs.y, mesh.Boundaries("outer"))
    trial, test = space.TnT()
    operator = ngs.BilinearForm(
        poisson_operator(trial, test, AXISYMMETRIC, permittivity=permittivity)
    ).Assemble()
    source = ngs.LinearForm(space)
    source += charge_source(charge_density, test, AXISYMMETRIC)
    source.Assemble()
    solve_linear(operator, source, potential)
    return potential


@pytest.fixture(scope="module")
def box() -> tuple[ngs.Mesh, ngs.GridFunction]:
    mesh = AnalyteInBoxGeometry(SphereBody(radius_nm=RADIUS_NM), outer_radius_nm=OUTER_NM).generate(
        maxh_nm=MESH[0], wall_h_nm=MESH[1]
    )
    return mesh, axial_extension(mesh, inner_nm=SHELL_NM[0], outer_nm=SHELL_NM[1])


@pytest.fixture(scope="module")
def dielectric(
    box: tuple[ngs.Mesh, ngs.GridFunction],
) -> tuple[ngs.GridFunction, ngs.CoefficientFunction]:
    mesh, _ = box
    ratio = ANALYTE_PERMITTIVITY / REFERENCE_PERMITTIVITY
    permittivity = mesh.MaterialCF({"analyte": ratio}, default=1.0)
    return _solve(mesh, permittivity, ngs.CF(0.0)), permittivity


def test_ver20_the_dielectric_sphere_matches_its_closed_form(
    box: tuple[ngs.Mesh, ngs.GridFunction],
    dielectric: tuple[ngs.GridFunction, ngs.CoefficientFunction],
) -> None:
    mesh, _ = box
    potential, _ = dielectric
    ratio = ANALYTE_PERMITTIVITY / REFERENCE_PERMITTIVITY
    beta = (ratio - 1.0) / (ratio + 2.0)

    for axial in (0.2, 0.5, 0.8):
        exact = -FIELD * axial * 3.0 / (ratio + 2.0)
        computed = potential(mesh(0.0, axial))
        assert computed == pytest.approx(exact, rel=1e-2), (
            f"phi on the axis inside the body at z = {axial} nm is {computed:.6f} against the "
            f"exact {exact:.6f}; the interior field should be uniform at "
            f"{3.0 / (ratio + 2.0):.4f} E_0"
        )
    for axial in (1.5, 3.0, 6.0):
        exact = -FIELD * axial * (1.0 - beta * RADIUS_NM**3 / axial**3)
        computed = potential(mesh(0.0, axial))
        assert computed == pytest.approx(exact, rel=1e-2), (
            f"phi on the axis outside the body at z = {axial} nm is {computed:.6f} against the "
            f"exact {exact:.6f}; the dipole term is beta = {beta:.4f} times (a/z)^3"
        )


def test_ver20_the_net_force_on_a_dielectric_sphere_vanishes(
    box: tuple[ngs.Mesh, ngs.GridFunction],
    dielectric: tuple[ngs.GridFunction, ngs.CoefficientFunction],
) -> None:
    mesh, extension = box
    potential, permittivity = dielectric
    domain_N = electrostatic_domain_force(
        mesh, ngs.grad(potential), 1.0, extension, AXISYMMETRIC, force_N=SCALES.force_N
    )
    surface_N = electrostatic_surface_force(
        mesh,
        ngs.grad(potential),
        1.0,
        AXISYMMETRIC,
        force_N=SCALES.force_N,
        piecewise_permittivity=permittivity,
    )
    assert abs(domain_N) < ZERO_TOLERANCE_N, (
        f"the domain route puts {domain_N * 1e12:.3e} pN on an uncharged dielectric sphere in a "
        f"uniform field, beyond the {ZERO_TOLERANCE_N * 1e12:.3e} pN this test allows. The "
        "traction is antisymmetric about the equator, so a surviving force means the two "
        "hemispheres are not being contracted the same way"
    )
    assert abs(surface_N) < ZERO_TOLERANCE_N, (
        f"the surface route puts {surface_N * 1e12:.3e} pN on the same body, beyond "
        f"{ZERO_TOLERANCE_N * 1e12:.3e} pN. Check the normal's orientation and that the lift "
        "landed on the fluid side of the dielectric jump"
    )


def test_ver20_a_charged_body_in_a_uniform_field_feels_q_e_zero(
    box: tuple[ngs.Mesh, ngs.GridFunction],
) -> None:
    mesh, extension = box
    body = SphereBody(radius_nm=RADIUS_NM)
    charge_C = CHARGE_E * ELEMENTARY_CHARGE
    volume_m3 = body.volume_nm3 * 1e-27
    density = (charge_C / volume_m3) / SCALES.charge_density_C_m3
    potential = _solve(mesh, ngs.CF(1.0), mesh.MaterialCF({"analyte": density}, default=0.0))

    expected_N = density * body.volume_nm3 * FIELD * SCALES.force_N
    assert expected_N == pytest.approx(charge_C * FIELD * SCALES.potential_V / 1e-9), (
        "the nondimensional anchor rho~ V~ E~_0 and the SI q E_0 disagree; one of the two "
        "scalings is wrong and the test would then be checking itself"
    )
    domain_N = electrostatic_domain_force(
        mesh, ngs.grad(potential), 1.0, extension, AXISYMMETRIC, force_N=SCALES.force_N
    )
    surface_N = electrostatic_surface_force(
        mesh, ngs.grad(potential), 1.0, AXISYMMETRIC, force_N=SCALES.force_N
    )
    for name, measured in (("domain", domain_N), ("surface", surface_N)):
        error = abs(measured / expected_N - 1.0)
        assert error < ANCHOR_TOLERANCE, (
            f"the {name} route puts {measured * 1e12:.5f} pN on a body of {CHARGE_E:g} e in a "
            f"field of {FIELD * SCALES.potential_V / 1e-9 * 1e-6:.1f} MV/m, against the exact "
            f"q E_0 = {expected_N * 1e12:.5f} pN: a relative error of {error:.3g} beyond the "
            f"stated {ANCHOR_TOLERANCE:.0%}. This is the only check on the scale of the Maxwell "
            "route, so a failure here is a factor, not a distribution"
        )
    assert math.copysign(1.0, domain_N) == math.copysign(1.0, CHARGE_E * FIELD), (
        f"a charge of {CHARGE_E:g} e in a field of +{FIELD} V_T/nm is pulled towards -z, but the "
        f"force came out at {domain_N * 1e12:+.5f} pN"
    )

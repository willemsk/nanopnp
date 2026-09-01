"""VER-20: the Maxwell stress on a dielectric sphere in a uniform field.

Two problems on one mesh, because a zero test and a magnitude test catch
disjoint errors and neither is sufficient alone.

**The zero test.** An uncharged dielectric sphere in a uniform applied field is
polarised but not pulled: the traction on its upper hemisphere is the mirror of
the traction on its lower one, so the net axial force vanishes identically at
any dielectric contrast. It is a strong test of the *distribution* — a sign
error in one component of ``T_M``, a normal pointing into the body, or a
quadrature that misses the ``r`` weight all break the cancellation — and it says
nothing at all about the scale.

**The magnitude anchor**, which is why the zero test is not the whole of VER-20.
Give the body a uniform charge density ``rho = q/V`` at the fluid's own
permittivity and the closed form is ``F_z = q E_0`` exactly: the self-force
vanishes by symmetry and only the applied field survives. In the NUM-09
variables this is ``F/(eps V_T^2) = rho~ V~ E~_0`` with the volume in mesh units,
so the anchor pins the ``2 pi``, the ``r`` weight and the force scale together in
one number. ``.knowledge/05-analyte-and-forces.md`` section 9.1 is the source of
the argument; the reference charge, ``q = -4 e``, is haemoglobin's at the PlyAB
operating point, and it lands at 8.2 pN, squarely in the RSK-04 range.

**No consistency term is needed here and none is taken.** The identity behind
NUM-28 is exact where ``div(T_M) = 0`` over the region ``w`` varies on, and the
fluid of both problems is charge-free with a uniform permittivity. The charge in
the anchor sits inside the body, where ``w`` is constant and outside the domain
of integration. That is what makes :func:`electrostatic_domain_force` — which
carries no consistency term — the right entry point, and it is the same code the
coupled route A calls.

The solve is plain Poisson with a piecewise permittivity, assembled here from
``physics.poisson`` rather than routed through ``models.create("poisson")``,
which does not yet forward a permittivity.
"""

import math

import ngsolve as ngs
import pytest

from nanopnp.core.constants import ELEMENTARY_CHARGE
from nanopnp.core.scaling import REFERENCE_PERMITTIVITY, Scales
from nanopnp.geometry.analyte import AnalyteInBoxGeometry, SphereBody
from nanopnp.physics.measures import AXISYMMETRIC
from nanopnp.physics.models import set_boundary_values
from nanopnp.physics.poisson import charge_source, poisson_operator
from nanopnp.post.forces import (
    axial_extension,
    electrostatic_domain_force,
    electrostatic_surface_force,
)
from nanopnp.solve.linear import solve_linear

RADIUS_NM, OUTER_NM = 1.0, 10.0
"""Sphere radius and the far boundary, in nm."""

FIELD = 0.5
"""``E~_0``, the applied axial field in ``V_T`` per nm. 12.8 mV/nm."""

ANALYTE_PERMITTIVITY = 20.0
"""``eps_r`` of the body: author ruling 5's calibration value (PHY-20)."""

CHARGE_E = -4.0
"""``q`` in elementary charges: haemoglobin at pH 7.4, the PlyAB reference."""

MESH = (0.4, 0.08)
"""``(maxh_nm, wall_h_nm)``. 0.6 s and about 5700 degrees of freedom."""

SHELL_NM = (1.5, 4.0)
"""``w``'s transition shell, as distances from the body's surface."""

ZERO_TOLERANCE_N = 1e-15
"""1e-3 pN on the net force on an uncharged sphere.

A hundredth of the NUM-29 route tolerance and a ten-thousandth of the anchor's
own magnitude, so "zero" here means zero rather than small.
"""

ANCHOR_TOLERANCE = 0.01
"""VER-20's stated tolerance on ``F_z = q E_0``: 1 %.

The specification leaves it open; this states it. The measured errors on this
mesh are 0.19 % on the domain route and 0.53 % on the surface route, both set by
the straight-sided facets of the meshed sphere.
"""

SCALES = Scales(length_nm=1.0, concentration_M=0.3)
"""The NUM-09 scale set on a mesh in nanometres.

``force_N`` does not depend on the reference length and no concentration enters
a Poisson-only problem, so only ``length_nm`` is load-bearing: it fixes
``charge_density_C_m3 = eps V_T / a^2``, the unit ``rho~`` is measured in.
"""


def _solve(
    mesh: ngs.Mesh, permittivity: ngs.CoefficientFunction, charge_density: ngs.CoefficientFunction
) -> ngs.GridFunction:
    """Return ``phi~`` for a uniform applied field ``-E~_0 z`` on the far boundary."""
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
    """Return the mesh and ``w`` on it; both problems are posed on the same pair."""
    mesh = AnalyteInBoxGeometry(SphereBody(radius_nm=RADIUS_NM), outer_radius_nm=OUTER_NM).generate(
        maxh_nm=MESH[0], wall_h_nm=MESH[1]
    )
    return mesh, axial_extension(mesh, inner_nm=SHELL_NM[0], outer_nm=SHELL_NM[1])


@pytest.fixture(scope="module")
def dielectric(
    box: tuple[ngs.Mesh, ngs.GridFunction],
) -> tuple[ngs.GridFunction, ngs.CoefficientFunction]:
    """Solve the uncharged dielectric sphere and return ``phi~`` and ``eps~_r``."""
    mesh, _ = box
    ratio = ANALYTE_PERMITTIVITY / REFERENCE_PERMITTIVITY
    permittivity = mesh.MaterialCF({"analyte": ratio}, default=1.0)
    return _solve(mesh, permittivity, ngs.CF(0.0)), permittivity


def test_ver20_the_dielectric_sphere_matches_its_closed_form(
    box: tuple[ngs.Mesh, ngs.GridFunction],
    dielectric: tuple[ngs.GridFunction, ngs.CoefficientFunction],
) -> None:
    """``phi`` inside and outside the sphere, against the textbook solution.

    Inside, ``phi = -E_0 z 3/(eps~_p + 2)``; outside,
    ``phi = -E_0 z (1 - beta a^3/R^3)`` with ``beta = (eps~_p - 1)/(eps~_p + 2)``.
    Checked first because a net force of zero on a wrong field is still zero:
    this is what makes the cancellation test below mean something.

    The far boundary carries ``-E_0 z`` rather than the closed form, so the
    computed field differs from the unbounded solution by ``beta (a/R)^3``,
    3.3e-4 here — which is what the measured departure comes out at.
    """
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
    """Both routes return zero for a polarised but uncharged body.

    A traction that is antisymmetric about ``z = 0`` integrates to nothing, so
    any surviving force is a defect in the contraction, the normal or the
    quadrature rather than physics.
    """
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
    """The magnitude anchor: ``F_z = q E_0``, to 1 %, by both routes.

    The only Tier-2 test that pins the *scale* of the Maxwell route. ``F^em`` has
    no reaction-route oracle — ``phi`` is not constrained on the body's surface —
    so without this the electromagnetic half rests on a cancellation test that a
    uniform factor would pass unchanged.
    """
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

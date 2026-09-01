"""VER-22 and NUM-29: the three NUM-28 routes on one solution, and RSK-04.

A charged sphere held in a uniform applied field, with mobile ions. The applied
field pulls on the body's own charge and, through the space charge of the double
layer, drives an electro-osmotic flow past it in the opposite sense; the two
forces are of the same order and of opposite sign. At the configuration below
they come out at ``F^em = -15.4 pN`` and ``F^hd = +9.9 pN`` for a net
``-5.5 pN`` — which is RSK-04 in miniature, and the reason this test measures the
*split* rather than only the total.

**Three routes, two of which are independent of the first.**

* **A**, the domain form of NUM-28, ``-int T:grad(w)`` plus each component's
  body-force consistency term. This is the reported force.
* **B**, the surface form ``surface_int (T.n).e_z``, taken over the body's own
  boundary. It shares no quadrature points with A and does not see ``w`` at all.
* **C**, the variational reaction force: the assembled momentum residual paired
  with a velocity-block test function equal to ``e_z`` on the analyte surface.
  Because the residual vanishes on every free degree of freedom, C is *exactly*
  independent of ``w`` and is a discrete identity rather than an approximation.
  It is the oracle on the split — the one route that can tell a missing
  consistency term from a correct one.

**The tolerance is absolute, and that is the point.** A relative test on a total
that is a small difference of two large numbers reports agreement that the split
does not have. NUM-29 asks for 0.1 pN absolute, which is 0.219 in the
nondimensional force unit ``eps V_T^2``; the measured disagreement here is
0.027 pN between A and B and 1.3e-4 pN between A and C.

**Classical, so the identity is exact.** With the permittivity correction off,
``grad(eps) = 0`` and the Korteweg-Helmholtz residual of PHY-23 — the term by
which NUM-28 as printed falls short of the force all three routes agree on — is
identically zero. This test asserts that it is, so that a future run with the
correction active is measuring the omission rather than discovering it.
"""

import ngsolve as ngs
import pytest

from nanopnp.core.constants import ELEMENTARY_CHARGE
from nanopnp.geometry.analyte import AnalyteInBoxGeometry, SphereBody
from nanopnp.physics import models
from nanopnp.physics.measures import AXISYMMETRIC
from nanopnp.physics.models import CoupledBoundaries, CoupledModel
from nanopnp.post.forces import FORCE_ROUTE_TOLERANCE_N, AnalyteForces, axial_extension, extract

RADIUS_NM, OUTER_NM = 2.0, 12.0
"""Body radius and far boundary, in nm. ``kappa a = 3.6`` at 0.3 M."""

CONCENTRATION_M = 0.3
"""Bulk NaCl, near the PlyAB reference operating point."""

FIELD = 0.2
"""``E~_0``, the applied axial field in ``V_T`` per nm: 5.1 MV/m."""

CHARGE_E = -20.0
"""``q`` in elementary charges, spread as ``rho = q/V`` over the body.

Large enough that both halves of the force reach 10 pN, which is the scale
RSK-04 is stated at; the ``slow`` study carries the PlyAB-shaped case itself.
"""

MESH = (0.8, 0.1)
"""``(maxh_nm, wall_h_nm)``. ``wall_h`` is under a fifth of the 0.554 nm Debye
length, which is what the double layer on the body needs."""

SHELL_NM = (2.5, 6.0)
"""``w``'s transition shell, as distances from the body's surface."""

ORACLE_TOLERANCE_N = 1e-15
"""1e-3 pN between route A's split and route C.

A hundredth of the NUM-29 tolerance. C is a discrete identity, not a second
approximation, so the two should agree to very much better than A and B do, and
a slack tolerance here would hide the one signal that separates a wrong split
from a right one.
"""


@pytest.fixture(scope="module")
def forces() -> tuple[CoupledModel, AnalyteForces]:
    """Solve the charged sphere in an applied field and take the force three ways.

    ``extract`` checks the routes against the NUM-29 tolerance itself and raises
    if they disagree, so reaching this fixture at all is most of VER-22; the
    tests below then say what was checked and how much margin there was.
    """
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
    density = (CHARGE_E * ELEMENTARY_CHARGE / (body.volume_nm3 * 1e-27)) / (
        model.scales.charge_density_C_m3
    )
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
        fixed_charge=mesh.MaterialCF({"analyte": density}, default=0.0),
    )
    extension = axial_extension(mesh, inner_nm=SHELL_NM[0], outer_nm=SHELL_NM[1])
    return model, extract(solution, AXISYMMETRIC, extension)


def test_ver22_both_halves_of_the_force_are_large_and_opposed(
    forces: tuple[CoupledModel, AnalyteForces],
) -> None:
    """The premise of the test: a near-cancellation, not a force with one origin.

    Asserted first because every agreement below is vacuous without it. If the
    configuration ever drifts to one where ``F^hd`` is negligible, the routes
    would agree on a total that no longer tests the split, and this is the
    assertion that says so instead of passing quietly.
    """
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
    """A against B, absolutely, at the NUM-29 tolerance.

    They share the solution and nothing else: A integrates a stress against
    ``grad(w)`` over the fluid, B a traction over the body's surface with the
    normal's orientation measured rather than assumed.
    """
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
    """A's ``F^hd`` against C, the oracle — the assertion RSK-04 turns on.

    A body-force consistency term omitted from both halves of route A cancels in
    the total and leaves A and B in perfect agreement on a split that is wrong
    by O(10 pN). C cannot be fooled that way: it never sees ``w``, and it reads
    the hydrodynamic traction straight off the residual the solve assembled.
    """
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


def test_ver22_the_korteweg_helmholtz_residual_vanishes_in_the_classical_model(
    forces: tuple[CoupledModel, AnalyteForces],
) -> None:
    """PHY-23's omitted term is identically zero with a constant permittivity.

    It is the gap between NUM-28 as printed and the force the three routes agree
    on, so it has to be zero here for the identity to be exact — and it has to
    be *reported* as zero rather than absent, or a later run with the ``eps_r``
    correction active would have nothing to compare against.
    """
    _, result = forces
    assert result.dielectric_gradient_N == pytest.approx(0.0, abs=1e-18), (
        f"the classical model reports {result.dielectric_gradient_N * 1e12:.3e} pN of "
        "Korteweg-Helmholtz force; with grad(eps) = 0 there is nothing for it to come from"
    )
    record = result.summary()
    assert record["two_pi_included"] is True, "the 2 pi of NUM-27 is not recorded as restored"
    assert record["routes_checked"] is True, "the summary does not record that NUM-29 was checked"

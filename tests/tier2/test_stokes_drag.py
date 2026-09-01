"""VER-19: the Stokes drag on a sphere, by all three NUM-28 routes.

``F_z = -6 pi eta a U`` is the one force in this package with a closed form that
owes nothing to the double layer, so it is where the NUM-28 machinery is pinned
before any of it is trusted on a charged body. The sphere is uncharged, the
electrolyte classical and the flow driven entirely by the boundary data, which
leaves the drag as the only thing the three routes can be measuring.

**The far field is the exact Stokes solution, not a uniform stream.** A uniform
``u = U e_z`` on a boundary at ``R = 10 a`` adds a wall correction of order
``a/R`` — measured here at 28.5 % on this domain, against the ``1 + (9/4)(a/b)``
leading term of a concentric container — so a benchmark posed that way measures
the truncation rather than the discretisation. Imposing

    u_r = -(3aU/4) z r / R^3 + (3a^3 U/4) z r / R^5
    u_z = U - (3aU/4)(1/R + z^2/R^3) - (a^3 U/4)(1/R^3 - 3 z^2/R^5)

makes the continuous solution on the annulus exact, so the whole of the measured
error is discretisation error, and ``R = 10 a`` is sufficient. The same field is
identically zero on ``|x| = a``, so one coefficient function serves both the
no-slip body and the far boundary.

The velocity is essential on the entire flow boundary, so the pressure is
determined only up to a constant and ``pressure_constraint=True`` is required.
The force is invariant to that datum; ``tests/tier1/test_forces.py`` asserts it.

Sanity anchor from ``.knowledge/05-analyte-and-forces.md`` section 7: a 5 nm
sphere at 0.1 m/s in water drags at about 4 pN. Here ``U~ = 0.05`` in
``u_0 = eps V_T^2/(eta L_0)``, which is 0.0592 m/s on a 1 nm sphere, and the
drag lands at 0.43 pN.
"""

import math
from collections.abc import Callable
from itertools import pairwise

import ngsolve as ngs
import pytest

from nanopnp.geometry.analyte import AnalyteInBoxGeometry, SphereBody
from nanopnp.physics import models
from nanopnp.physics.measures import AXISYMMETRIC
from nanopnp.physics.models import CoupledBoundaries, CoupledModel, ModelSolution
from nanopnp.post.forces import AnalyteForces, axial_extension, extract

RADIUS_NM = 1.0
"""Sphere radius ``a``, in nm. One mesh unit, so ``U~`` is also ``U a / u_0 a``."""

OUTER_NM = 10.0
"""``R = 10 a``. Far enough that the exact far field is cheap to impose."""

VELOCITY = 0.05
"""``U~``, the translation speed in ``u_0``. Small enough that Stokes is Stokes."""

SHELL_NM = (1.5, 4.0)
"""``w``'s transition shell, as distances from the body's surface.

Its inner radius must exceed the element size at the body, or the interpolated
``w`` comes off the surface at slightly less than one; ``check_extension``
catches that. The force is independent of the shell, which is what makes the
choice free.
"""

TOLERANCE = 0.01
"""VER-19's stated tolerance on the finest mesh: 1 % of ``6 pi eta a U``.

The specification leaves it open; this states it. It is set by the straight-sided
boundary of the body, not by the velocity space — the measured error on the
finest mesh here is 2.0e-5, so a 1 % gate has three orders of headroom and fails
only on a genuine defect.
"""

MESHES = ((1.6, 0.2), (0.8, 0.1), (0.4, 0.05))
"""``(maxh_nm, wall_h_nm)`` of the refinement ladder."""


def _exact_stokes(radius_nm: float, velocity: float) -> ngs.CoefficientFunction:
    """Return the Stokes field past a translating sphere, in the ``(r, z)`` half-plane.

    Zero on ``|x| = radius_nm`` and tending to ``velocity e_z`` at infinity, so
    it is simultaneously the no-slip condition on the body and the far field.
    """
    radial, axial = ngs.x, ngs.y
    # The +1e-30 keeps the expression finite where the quadrature samples the
    # origin; that point lies inside the body and is never integrated over.
    distance = ngs.sqrt(radial * radial + axial * axial + 1e-30)
    a, u = radius_nm, velocity
    radial_component = -(3 * a * u / 4) * (axial * radial / distance**3) + (3 * a**3 * u / 4) * (
        axial * radial / distance**5
    )
    axial_component = (
        u
        - (3 * a * u / 4) * (1 / distance + axial**2 / distance**3)
        - (a**3 * u / 4) * (1 / distance**3 - 3 * axial**2 / distance**5)
    )
    return ngs.CF((radial_component, axial_component))


def _model() -> CoupledModel:
    """Return the classical, flow-carrying model VER-19 is posed on.

    Classical because ``6 pi eta a U`` assumes a constant viscosity: with the
    corrections active ``eta`` inherits the wall function and the closed form is
    no longer the right target. Inertia off because Stokes is the zero-Reynolds
    limit, and ``pressure_constraint`` on because ``u`` is essential everywhere.
    """
    model = models.create(
        "pnp-ns",
        concentration_M=0.3,
        inertia=False,
        variable_density=False,
        pressure_constraint=True,
        solid_permittivities={"analyte": 20.0},
    )
    assert isinstance(model, CoupledModel)
    return model


BOUNDARIES = CoupledBoundaries(
    potential="outer",
    concentration="outer",
    velocity="analyte|outer",
    velocity_axis="axis",
)
"""No-slip on the body and the exact field on the far boundary, both essential."""


def _solve(
    model: CoupledModel,
    maxh_nm: float,
    wall_h_nm: float,
    values: Callable[[ngs.Mesh], ngs.CoefficientFunction],
) -> tuple[ModelSolution, AnalyteForces]:
    """Solve on one mesh and take the force by all three routes.

    The boundary data arrives as a factory because the negative control's is
    per-boundary, and ``BoundaryCF`` is a method of the mesh.
    """
    mesh = AnalyteInBoxGeometry(SphereBody(radius_nm=RADIUS_NM), outer_radius_nm=OUTER_NM).generate(
        maxh_nm=maxh_nm, wall_h_nm=wall_h_nm
    )
    solution = model.solve(mesh, AXISYMMETRIC, boundaries=BOUNDARIES, velocity_values=values(mesh))
    extension = axial_extension(mesh, inner_nm=SHELL_NM[0], outer_nm=SHELL_NM[1])
    return solution, extract(solution, AXISYMMETRIC, extension)


@pytest.fixture(scope="module")
def drag() -> tuple[float, list[AnalyteForces]]:
    """Return ``6 pi eta a U`` in newtons and the force on each mesh of the ladder."""
    model = _model()
    field = _exact_stokes(RADIUS_NM, VELOCITY)
    expected_N = 6.0 * math.pi * RADIUS_NM * VELOCITY * model.scales.force_N
    return expected_N, [_solve(model, maxh, wall, lambda _: field)[1] for maxh, wall in MESHES]


def test_ver19_stokes_drag_converges_to_the_closed_form(
    drag: tuple[float, list[AnalyteForces]],
) -> None:
    """The domain route reaches ``6 pi eta a U`` to 1 %, monotonically.

    A failure here is either the axisymmetric viscous operator, the hoop term it
    carries, or the NUM-28 contraction. The rate is asserted as well as the
    floor because a force that happens to be right on one mesh and does not
    improve under refinement is right by accident.
    """
    expected_N, forces = drag
    errors = [abs(force.total_N / expected_N - 1.0) for force in forces]
    assert errors[-1] < TOLERANCE, (
        f"the drag on the finest mesh is {forces[-1].total_N * 1e12:.5f} pN against the exact "
        f"{expected_N * 1e12:.5f} pN, a relative error of {errors[-1]:.3g} beyond the stated "
        f"{TOLERANCE:.0%}"
    )
    assert all(fine < coarse for coarse, fine in pairwise(errors)), (
        f"the error {errors} does not fall monotonically under refinement; a drag that is close "
        "on one mesh without improving on the next is close by accident"
    )
    rate = math.log2(errors[0] / errors[-1]) / (len(errors) - 1)
    assert rate > 1.5, (
        f"the observed convergence rate {rate:.2f} per halving is below 1.5; the errors are "
        f"{errors}, and a first-order rate on a P2 velocity means the geometry, not the space, "
        "is setting the accuracy"
    )


def test_ver19_the_three_routes_agree_on_the_drag(
    drag: tuple[float, list[AnalyteForces]],
) -> None:
    """Domain, surface and reaction routes agree well inside the NUM-29 tolerance.

    The drag is the whole force here — there is no electromagnetic half to
    cancel against — so this is the cleanest available check that the surface
    traction and the assembled residual measure the same thing the volume form
    does.
    """
    expected_N, forces = drag
    finest = forces[-1]
    agreement = finest.agreement
    assert agreement is not None, "extract was asked to check the routes and did not"
    assert agreement.reaction_hd_N is not None, "route C was not taken"
    assert abs(agreement.reaction_hd_N / expected_N - 1.0) < TOLERANCE, (
        f"the reaction route gives {agreement.reaction_hd_N * 1e12:.5f} pN against the exact "
        f"{expected_N * 1e12:.5f} pN. It is the oracle for the split, so a failure here and not "
        "in the domain route means the residual and the volume form disagree"
    )
    assert finest.forces.em_N == pytest.approx(0.0, abs=1e-16), (
        f"an uncharged sphere in an unbiased box carries {finest.forces.em_N * 1e12:.3e} pN of "
        "electromagnetic force; it should carry none"
    )


def test_ver19_a_uniform_far_field_measures_the_wall_correction_instead() -> None:
    """The negative control: ``u = U e_z`` on ``outer`` is *not* the Stokes benchmark.

    A bounded domain with a uniform stream imposed at ``R = 10 a`` confines the
    return flow and raises the drag by order ``a/R`` — the ``1 + (9/4)(a/b)``
    correction of a sphere in a concentric container, about 22 % here. This test
    exists so that anyone who simplifies the boundary condition sees the reason
    it was not simple, rather than a benchmark that quietly passes at 20 % off.
    """
    model = _model()
    still = ngs.CF((0.0, 0.0))
    _, forces = _solve(
        model,
        0.8,
        0.1,
        lambda mesh: mesh.BoundaryCF({"outer": ngs.CF((0.0, VELOCITY))}, default=still),
    )
    expected_N = 6.0 * math.pi * RADIUS_NM * VELOCITY * model.scales.force_N
    excess = forces.total_N / expected_N - 1.0
    assert excess > 0.2, (
        f"a uniform stream at R = {OUTER_NM / RADIUS_NM:g} a gives {forces.total_N * 1e12:.5f} pN "
        f"against the unbounded {expected_N * 1e12:.5f} pN, an excess of {excess:.1%}. It was "
        "expected to over-predict by about the 22 % wall correction; if it no longer does, either "
        "the far field is being imposed somewhere else or the drag itself has changed"
    )

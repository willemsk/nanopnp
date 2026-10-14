"""VER-19: the Stokes drag on a sphere, by all three NUM-28 routes."""

import math
from collections.abc import Callable
from itertools import pairwise

import ngsolve as ngs
import pytest

from nanopnp.geometry.analyte import AnalyteInBoxGeometry, SphereBody
from nanopnp.numerics.measures import AXISYMMETRIC
from nanopnp.physics import models
from nanopnp.physics.models import CoupledBoundaries, CoupledModel, ModelSolution
from nanopnp.post.forces import AnalyteForces, axial_extension, extract

RADIUS_NM = 1.0

OUTER_NM = 10.0

VELOCITY = 0.05

SHELL_NM = (1.5, 4.0)

TOLERANCE = 0.01

MESHES = ((1.6, 0.2), (0.8, 0.1), (0.4, 0.05))


def _exact_stokes(radius_nm: float, velocity: float) -> ngs.CoefficientFunction:
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


# VER-19
def _model() -> CoupledModel:
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


def _solve(
    model: CoupledModel,
    maxh_nm: float,
    wall_h_nm: float,
    values: Callable[[ngs.Mesh], ngs.CoefficientFunction],
) -> tuple[ModelSolution, AnalyteForces]:
    mesh = AnalyteInBoxGeometry(SphereBody(radius_nm=RADIUS_NM), outer_radius_nm=OUTER_NM).generate(
        maxh_nm=maxh_nm, wall_h_nm=wall_h_nm
    )
    solution = model.solve(mesh, AXISYMMETRIC, boundaries=BOUNDARIES, velocity_values=values(mesh))
    extension = axial_extension(mesh, inner_nm=SHELL_NM[0], outer_nm=SHELL_NM[1])
    return solution, extract(solution, AXISYMMETRIC, extension)


@pytest.fixture(scope="module")
def drag() -> tuple[float, list[AnalyteForces]]:
    model = _model()
    field = _exact_stokes(RADIUS_NM, VELOCITY)
    expected_N = 6.0 * math.pi * RADIUS_NM * VELOCITY * model.scales.force_N
    return expected_N, [_solve(model, maxh, wall, lambda _: field)[1] for maxh, wall in MESHES]


# NUM-28
def test_ver19_stokes_drag_converges_to_the_closed_form(
    drag: tuple[float, list[AnalyteForces]],
) -> None:
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


# NUM-29
def test_ver19_the_three_routes_agree_on_the_drag(
    drag: tuple[float, list[AnalyteForces]],
) -> None:
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

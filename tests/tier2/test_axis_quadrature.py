"""VER-07 and VER-08: 1/r forms must be integrated at order >= 3.

Gauss rules on triangles do sample r = 0. NGSolve's order-2 rule puts its three
points at the edge midpoints (0, 1/2), (1/2, 0), (1/2, 1/2), so an element with
an edge on the axis is sampled exactly on it and any 1/r factor returns NaN -
silently, through the assembled form, into a plausible wrong answer.

These tests pin both halves: that the trap is real at order 2, and that the
`Measures` API cannot fall into it.
"""

import math

import ngsolve as ngs
import pytest

from nanopnp.mesh.primitives import CylinderGeometry
from nanopnp.physics.measures import SINGULAR_MIN_ORDER, Measures


@pytest.fixture(scope="module")
def axis_mesh() -> ngs.Mesh:
    """Return a mesh with elements touching r = 0."""
    return CylinderGeometry(radius_nm=1.0, length_nm=1.0).generate(maxh_nm=0.25)


def _radial_gridfunction(mesh: ngs.Mesh) -> ngs.GridFunction:
    """Interpolate f(r, z) = r, so that f^2/r^2 is identically 1."""
    space = ngs.H1(mesh, order=2)
    gf = ngs.GridFunction(space)
    gf.Set(ngs.x)
    return gf


def test_ver07_order_two_returns_nan_on_an_axis_touching_mesh(axis_mesh: ngs.Mesh) -> None:
    """The trap itself: this is what a defaulted integration order does."""
    gf = _radial_gridfunction(axis_mesh)
    naive = ngs.Integrate(gf * gf / (ngs.x * ngs.x) * ngs.x, axis_mesh, order=2)
    assert math.isnan(naive), "order 2 no longer samples the axis; revisit NUM-07 and this test"


def test_ver08_singular_integral_is_correct_at_the_guaranteed_order(axis_mesh: ngs.Mesh) -> None:
    """The integral of (f^2/r^2) r dr dz over the unit square is 1/2, obtained exactly."""
    gf = _radial_gridfunction(axis_mesh)
    measures = Measures(symmetry="axisymmetric", element_order=2)
    value = measures.integrate(
        gf * gf / (ngs.x * ngs.x), axis_mesh, singular=True, what="hoop-strain probe"
    )
    assert value == pytest.approx(0.5, rel=1e-12)


def test_singular_forms_are_integrated_at_order_three_or_better() -> None:
    """NUM-07 is asserted by construction, not left to a default."""
    for order in (1, 2, 3):
        measures = Measures(symmetry="axisymmetric", element_order=order)
        assert measures.integration_order(singular=True) >= SINGULAR_MIN_ORDER
        # Non-singular terms are left alone; the bonus is not free.
        assert measures.bonus_order() == 0


def test_a_non_finite_integral_aborts_with_the_quantity_named(axis_mesh: ngs.Mesh) -> None:
    """QR-12: a gate failure names the gate and the offending quantity.

    The integrand is non-finite at every quadrature point rather than only on the
    axis, because ``integrate`` floors its order above the order-2 rule that
    samples ``r = 0``. VER-07 above pins that rule itself.
    """
    measures = Measures(symmetry="axisymmetric", element_order=2)
    with pytest.raises(ValueError, match=r"hoop-strain term.*NUM-07"):
        measures.integrate(
            ngs.CF(1.0) / (ngs.x - ngs.x),
            axis_mesh,
            singular=False,
            what="hoop-strain term",
        )


def test_bonus_intorder_cannot_be_passed_behind_the_guarantee() -> None:
    """The escape hatch that would defeat NUM-07 is closed."""
    measures = Measures()
    with pytest.raises(ValueError, match="pass extra_order"):
        measures.volume(ngs.CF(1.0), bonus_intorder=5)


def test_num04_the_measure_applies_the_radial_weight(axis_mesh: ngs.Mesh) -> None:
    """The r weight is applied by the measure, not by the call site (NUM-04).

    Over the unit square in (r, z) the axisymmetric measure of 1 is
    ``int_0^1 int_0^1 r dr dz = 1/2`` and the planar one is 1. The 1D benchmarks
    are genuinely planar, so weighting them would be wrong in the other
    direction.
    """
    assert Measures(symmetry="planar").radial_weight == 1.0
    assert Measures(symmetry="planar").integrate(ngs.CF(1.0), axis_mesh) == pytest.approx(
        1.0, rel=1e-12
    )
    assert Measures(symmetry="axisymmetric").integrate(ngs.CF(1.0), axis_mesh) == pytest.approx(
        0.5, rel=1e-12
    )

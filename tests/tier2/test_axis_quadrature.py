"""VER-07: forms carrying 1/r are integrated at order three or better."""

import math

import ngsolve as ngs
import pytest

from nanopnp.mesh.primitives import CylinderGeometry
from nanopnp.numerics.measures import SINGULAR_MIN_ORDER, Measures


@pytest.fixture(scope="module")
def axis_mesh() -> ngs.Mesh:
    return CylinderGeometry(radius_nm=1.0, length_nm=1.0).generate(maxh_nm=0.25)


def _radial_gridfunction(mesh: ngs.Mesh) -> ngs.GridFunction:
    space = ngs.H1(mesh, order=2)
    gf = ngs.GridFunction(space)
    gf.Set(ngs.x)
    return gf


def test_ver07_order_two_returns_nan_on_an_axis_touching_mesh(axis_mesh: ngs.Mesh) -> None:
    gf = _radial_gridfunction(axis_mesh)
    naive = ngs.Integrate(gf * gf / (ngs.x * ngs.x) * ngs.x, axis_mesh, order=2)
    assert math.isnan(naive), "order 2 no longer samples the axis; revisit NUM-07 and this test"


def test_ver07_singular_integral_is_correct_at_the_guaranteed_order(axis_mesh: ngs.Mesh) -> None:
    gf = _radial_gridfunction(axis_mesh)
    measures = Measures(symmetry="axisymmetric", element_order=2)
    value = measures.integrate(
        gf * gf / (ngs.x * ngs.x), axis_mesh, singular=True, what="hoop-strain probe"
    )
    assert value == pytest.approx(0.5, rel=1e-12)


# NUM-07
def test_singular_forms_are_integrated_at_order_three_or_better() -> None:
    for order in (1, 2, 3):
        measures = Measures(symmetry="axisymmetric", element_order=order)
        assert measures.integration_order(singular=True) >= SINGULAR_MIN_ORDER
        assert measures.bonus_order() == 0


# QR-12, VER-07
def test_a_non_finite_integral_aborts_with_the_quantity_named(axis_mesh: ngs.Mesh) -> None:
    measures = Measures(symmetry="axisymmetric", element_order=2)
    with pytest.raises(ValueError, match=r"hoop-strain term.*NUM-07"):
        measures.integrate(
            ngs.CF(1.0) / (ngs.x - ngs.x),
            axis_mesh,
            singular=False,
            what="hoop-strain term",
        )


# NUM-07
def test_bonus_intorder_cannot_be_passed_behind_the_guarantee() -> None:
    measures = Measures()
    with pytest.raises(ValueError, match="pass extra_order"):
        measures.volume(ngs.CF(1.0), bonus_intorder=5)


def test_num04_the_measure_applies_the_radial_weight(axis_mesh: ngs.Mesh) -> None:
    assert Measures(symmetry="planar").radial_weight == 1.0
    assert Measures(symmetry="planar").integrate(ngs.CF(1.0), axis_mesh) == pytest.approx(
        1.0, rel=1e-12
    )
    assert Measures(symmetry="axisymmetric").integrate(ngs.CF(1.0), axis_mesh) == pytest.approx(
        0.5, rel=1e-12
    )


# NUM-07
def _weighted_stiffness_energy(mesh: ngs.Mesh, measures: Measures) -> tuple[float, float]:
    space = ngs.H1(mesh, order=2)
    trial, test = space.TnT()
    u = ngs.GridFunction(space)
    u.Set(ngs.y**2)
    form = ngs.BilinearForm(measures.volume(ngs.grad(trial) * ngs.grad(test))).Assemble()
    assembled = ngs.InnerProduct(u.vec, form.mat * u.vec)
    exact = ngs.Integrate(4.0 * ngs.y**2 * ngs.x, mesh, order=8)
    return float(assembled), float(exact)


def test_num07_weight_extra_order_closes_the_r_weight_deficit(axis_mesh: ngs.Mesh) -> None:
    default, exact = _weighted_stiffness_energy(axis_mesh, Measures())
    raised, _ = _weighted_stiffness_energy(axis_mesh, Measures(weight_extra_order=1))
    assert abs(default - exact) / exact > 1e-9, "the default should be one order short"
    assert abs(raised - exact) / exact < 1e-13


def test_num07_weight_extra_order_leaves_the_rest_alone() -> None:
    default = Measures()
    raised = Measures(weight_extra_order=1)
    planar = Measures(symmetry="planar", weight_extra_order=1)
    assert default._form_bonus(singular=False, extra=0) == default.bonus_order()
    assert raised._form_bonus(singular=False, extra=1) == 2
    assert raised._form_bonus(singular=True, extra=0) == default.bonus_order(singular=True)
    assert planar._form_bonus(singular=False, extra=0) == 0
    assert raised.integration_order() == default.integration_order()
    with pytest.raises(ValueError, match="weight_extra_order"):
        Measures(weight_extra_order=-1)

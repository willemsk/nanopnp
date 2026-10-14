"""The axisymmetric flow forms: the hoop term and the 1/r quadrature (NUM-04, NUM-05, NUM-07)."""

import ngsolve as ngs
import pytest

from nanopnp.mesh.primitives import CylinderGeometry
from nanopnp.numerics.measures import SINGULAR_MIN_ORDER, Measures
from nanopnp.physics.flow import (
    axisymmetric_divergence,
    continuity_term,
    electrical_body_force,
    inertia_term,
    strain_rate,
    viscous_operator,
)

RADIUS_NM, LENGTH_NM = 3.0, 2.0
AXISYMMETRIC = Measures(symmetry="axisymmetric", element_order=2)
PLANAR = Measures(symmetry="planar", element_order=2)

WEIGHTED_AREA = 0.5 * RADIUS_NM**2 * LENGTH_NM

PLANAR_AREA = RADIUS_NM * LENGTH_NM


@pytest.fixture(scope="module")
def mesh() -> ngs.Mesh:
    return CylinderGeometry(radius_nm=RADIUS_NM, length_nm=LENGTH_NM).generate(maxh_nm=0.5)


@pytest.fixture(scope="module")
def velocity(mesh: ngs.Mesh) -> ngs.GridFunction:
    space = ngs.VectorH1(mesh, order=2)
    field = ngs.GridFunction(space, name="u")
    field.Set(ngs.CF((ngs.x, -2.0 * ngs.y)))
    return field


def _energy(mesh: ngs.Mesh, term, field: ngs.GridFunction) -> float:
    form = ngs.BilinearForm(field.space)
    form += term
    form.Assemble()
    return float(ngs.InnerProduct(form.mat * field.vec, field.vec))


def test_num05_hoop_strain_term_is_assembled(mesh: ngs.Mesh, velocity: ngs.GridFunction) -> None:
    space = velocity.space
    trial, test = space.TnT()
    full = _energy(mesh, viscous_operator(trial, test, AXISYMMETRIC), velocity)
    deviatoric_only = _energy(
        mesh,
        AXISYMMETRIC.volume(2.0 * ngs.InnerProduct(strain_rate(trial), strain_rate(test))),
        velocity,
    )
    assert full == pytest.approx(12.0 * WEIGHTED_AREA, rel=1e-10)
    assert deviatoric_only == pytest.approx(10.0 * WEIGHTED_AREA, rel=1e-10)


def test_num05_divergence_carries_the_axisymmetric_hoop_term(
    mesh: ngs.Mesh, velocity: ngs.GridFunction
) -> None:
    pressure_space = ngs.H1(mesh, order=1)
    unit = ngs.GridFunction(pressure_space)
    unit.Set(ngs.CF(1.0))

    for measures, expected in ((AXISYMMETRIC, 0.0), (PLANAR, PLANAR_AREA)):
        form = ngs.BilinearForm(trialspace=velocity.space, testspace=pressure_space)
        form += continuity_term(
            velocity.space.TrialFunction(), pressure_space.TestFunction(), measures
        )
        form.Assemble()
        residual = float(ngs.InnerProduct(form.mat * velocity.vec, unit.vec))
        assert residual == pytest.approx(expected, abs=1e-9, rel=1e-10)


def test_num07_singular_flow_forms_declare_the_quadrature_guarantee() -> None:
    assert AXISYMMETRIC.bonus_order(singular=True) >= SINGULAR_MIN_ORDER
    assert AXISYMMETRIC.integration_order(singular=True) >= SINGULAR_MIN_ORDER


def test_num07_flow_block_assembles_finitely_on_an_axis_touching_mesh(
    mesh: ngs.Mesh, velocity: ngs.GridFunction
) -> None:
    import numpy as np

    space = velocity.space * ngs.H1(mesh, order=1)
    trial_u, _ = space.TrialFunction()
    test_u, test_p = space.TestFunction()
    form = ngs.BilinearForm(space)
    form += viscous_operator(trial_u, test_u, AXISYMMETRIC)
    form += continuity_term(trial_u, test_p, AXISYMMETRIC)
    form += inertia_term(trial_u, test_u, AXISYMMETRIC, reynolds=1.0)
    form.Assemble()
    entries = np.asarray(form.mat.AsVector().FV())
    assert np.isfinite(entries).all(), "a 1/r factor was sampled on the axis"
    assert np.abs(entries).max() > 0.0


def test_phy08_body_force_is_the_mobile_charge_times_the_field(
    mesh: ngs.Mesh, velocity: ngs.GridFunction
) -> None:
    screening = 3.0
    space = velocity.space
    potential = ngs.GridFunction(ngs.H1(mesh, order=2))
    potential.Set(ngs.y)
    axial = ngs.GridFunction(space)
    axial.Set(ngs.CF((0.0, 1.0)))

    load = ngs.LinearForm(space)
    load += electrical_body_force(
        ngs.CF(1.0), potential, space.TestFunction(), AXISYMMETRIC, screening=screening
    )
    load.Assemble()
    assert float(ngs.InnerProduct(load.vec, axial.vec)) == pytest.approx(
        screening * WEIGHTED_AREA, rel=1e-10
    )


def test_axisymmetric_divergence_reduces_to_the_planar_one(
    mesh: ngs.Mesh, velocity: ngs.GridFunction
) -> None:
    point = mesh(1.0, 1.0)
    assert axisymmetric_divergence(velocity, AXISYMMETRIC)(point) == pytest.approx(0.0, abs=1e-12)
    assert axisymmetric_divergence(velocity, PLANAR)(point) == pytest.approx(-1.0, rel=1e-12)

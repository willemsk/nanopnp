"""The axisymmetric flow forms: the hoop term and the 1/r quadrature (NUM-04, NUM-05, NUM-07).

Both defects these tests exist for are silent. Omitting the hoop-strain term
``2 eta u_r v_r / r^2`` gives a plausible but wrong velocity field with no solver
diagnostic, and omitting the ``u_r/r`` inside the axisymmetric divergence makes a
genuinely solenoidal field look compressible. Each is checked against a field
whose exact answer is arithmetic rather than another run of the same code.

The field is ``u = (r, -2z)``, for which

    div^(u) = d_r u_r + u_r/r + d_z u_z = 1 + 1 - 2 = 0

so it is exactly solenoidal in cylindrical geometry and exactly *not* in planar
geometry, where the same expression gives -1. Its rate-of-strain is
``diag(1, -2)`` in plane with hoop component ``u_r/r = 1``, so
``2 eps:eps = 10`` without the hoop and 12 with it.
"""

import ngsolve as ngs
import pytest

from nanopnp.mesh.primitives import CylinderGeometry
from nanopnp.physics.flow import (
    axisymmetric_divergence,
    continuity_term,
    electrical_body_force,
    inertia_term,
    strain_rate,
    viscous_operator,
)
from nanopnp.physics.measures import SINGULAR_MIN_ORDER, Measures

RADIUS_NM, LENGTH_NM = 3.0, 2.0
AXISYMMETRIC = Measures(symmetry="axisymmetric", element_order=2)
PLANAR = Measures(symmetry="planar", element_order=2)

WEIGHTED_AREA = 0.5 * RADIUS_NM**2 * LENGTH_NM
"""``int r dr dz`` over the test cylinder, the weight an axisymmetric integral carries."""

PLANAR_AREA = RADIUS_NM * LENGTH_NM
"""``int dr dz`` over the same rectangle. Deliberately different from
:data:`WEIGHTED_AREA`, so that a form using the wrong measure cannot pass."""


@pytest.fixture(scope="module")
def mesh() -> ngs.Mesh:
    """Return a cylinder whose axis edge touches ``r = 0``, which is the point."""
    return CylinderGeometry(radius_nm=RADIUS_NM, length_nm=LENGTH_NM).generate(maxh_nm=0.5)


@pytest.fixture(scope="module")
def velocity(mesh: ngs.Mesh) -> ngs.GridFunction:
    """Return ``u = (r, -2z)``, represented exactly by P2."""
    space = ngs.VectorH1(mesh, order=2)
    field = ngs.GridFunction(space, name="u")
    field.Set(ngs.CF((ngs.x, -2.0 * ngs.y)))
    return field


def _energy(mesh: ngs.Mesh, term, field: ngs.GridFunction) -> float:
    """Return ``u^T A u`` for the bilinear form of one term."""
    form = ngs.BilinearForm(field.space)
    form += term
    form.Assemble()
    return float(ngs.InnerProduct(form.mat * field.vec, field.vec))


def test_num05_hoop_strain_term_is_assembled(mesh: ngs.Mesh, velocity: ngs.GridFunction) -> None:
    """``2 eta eps:eps`` is 10 without the hoop term and 12 with it.

    The difference is 20 % on this field and would be invisible in any residual:
    a solver missing the term converges happily to the wrong flow.
    """
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
    """``u = (r, -2z)`` is solenoidal in cylindrical geometry and not in planar.

    The continuity residual against the constant pressure test function is
    therefore zero in the axisymmetric measure and ``+1`` times the weighted area
    in the planar one. Dropping ``u_r/r`` turns the first into the second.
    """
    pressure_space = ngs.H1(mesh, order=1)
    unit = ngs.GridFunction(pressure_space)
    unit.Set(ngs.CF(1.0))

    # continuity_term returns -q div^(u): zero in cylindrical geometry, and
    # -(-1) times the unweighted area in planar geometry.
    for measures, expected in ((AXISYMMETRIC, 0.0), (PLANAR, PLANAR_AREA)):
        form = ngs.BilinearForm(trialspace=velocity.space, testspace=pressure_space)
        form += continuity_term(
            velocity.space.TrialFunction(), pressure_space.TestFunction(), measures
        )
        form.Assemble()
        residual = float(ngs.InnerProduct(form.mat * velocity.vec, unit.vec))
        assert residual == pytest.approx(expected, abs=1e-9, rel=1e-10)


def test_num07_singular_flow_forms_declare_the_quadrature_guarantee() -> None:
    """Every ``1/r`` term of the flow block asks for integration order >= 3."""
    assert AXISYMMETRIC.bonus_order(singular=True) >= SINGULAR_MIN_ORDER
    assert AXISYMMETRIC.integration_order(singular=True) >= SINGULAR_MIN_ORDER


def test_num07_flow_block_assembles_finitely_on_an_axis_touching_mesh(
    mesh: ngs.Mesh, velocity: ngs.GridFunction
) -> None:
    """No NaN reaches the matrix from a ``1/r`` factor sampled on the axis.

    The hoop term and the divergence both carry ``1/r``, and both are evaluated
    before the ``r`` weight multiplies them, so an order-2 rule that samples
    ``r = 0`` returns ``inf * 0``. NGSolve raises nothing; the NaN simply
    propagates into the factorisation.
    """
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
    """``S rho~_ion grad(phi~) . v``, and nothing else, enters the momentum residual.

    With ``rho~_ion = 1`` and ``phi~ = z`` the force is uniform and axial, so the
    residual against ``v = e_z`` is exactly ``S int r dr dz``.
    """
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
    """The planar measure drops the ``u_r/r`` term rather than weighting it by 1."""
    point = mesh(1.0, 1.0)
    assert axisymmetric_divergence(velocity, AXISYMMETRIC)(point) == pytest.approx(0.0, abs=1e-12)
    assert axisymmetric_divergence(velocity, PLANAR)(point) == pytest.approx(-1.0, rel=1e-12)

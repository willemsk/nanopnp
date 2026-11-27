"""The axisymmetric flow forms: the hoop term and the 1/r quadrature (NUM-04, NUM-05, NUM-07)."""

import ngsolve as ngs
import pytest

from nanopnp.io.vocabulary import POTENTIAL, PRESSURE, VELOCITY
from nanopnp.mesh.primitives import CylinderGeometry
from nanopnp.numerics.measures import SINGULAR_MIN_ORDER, Measures
from nanopnp.physics import flow, kernel
from nanopnp.physics.backend import NGSOLVE_OPERATORS, geometry_of
from nanopnp.physics.coupled import coupled_slots
from nanopnp.physics.operators import divergence, strain
from nanopnp.physics.stabilisation import create as create_stabilisation

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


class _UnitCoefficients:
    # Unit viscosity and Reynolds number, so that each form is the bare operator.
    reynolds = 1.0

    def __init__(self, screening: float = 1.0) -> None:
        self.screening = screening

    def viscosity(self) -> float:
        return 1.0

    def ionic_charge_density(self) -> float:
        return 1.0


def _context(
    mesh: ngs.Mesh,
    measures: Measures,
    trial: dict,
    tests: dict,
    coefficients: _UnitCoefficients | None = None,
) -> kernel.Context:
    side = kernel.Side(
        functions=trial, variables=None, coefficients=coefficients or _UnitCoefficients()
    )
    return kernel.Context(
        ops=NGSOLVE_OPERATORS,
        geometry=geometry_of(mesh, measures),
        measures=measures,
        fluid=mesh.Materials(".*"),
        trial=side,
        lagged=side,
        tests=tests,
        inputs=kernel.Inputs(),
        steric=None,
        stabilisation=create_stabilisation("none"),
    )


def _slots(*families: str) -> tuple[kernel.Slot, ...]:
    every = coupled_slots((), {POTENTIAL, VELOCITY, PRESSURE}, None, ())
    return tuple(slot for slot in every if slot.family in families)


VISCOUS = kernel.KernelTerm(
    "viscous",
    "PHY-07",
    contributions=(
        kernel.Contribution("momentum.viscous", flow.viscous_stress),
        kernel.Contribution("momentum.hoop", flow.hoop_stress),
    ),
)
CONTINUITY = kernel.KernelTerm(
    "continuity", "NUM-04", contributions=(kernel.Contribution("continuity", flow.continuity),)
)
INERTIA = kernel.KernelTerm("inertia", "NUM-04", force=flow.inertia_force)
BODY_FORCE = kernel.KernelTerm("body force", "PHY-08", force=flow.ionic_force)


def _energy(mesh: ngs.Mesh, term, field: ngs.GridFunction) -> float:
    form = ngs.BilinearForm(field.space)
    form += term
    form.Assemble()
    return float(ngs.InnerProduct(form.mat * field.vec, field.vec))


def test_num05_hoop_strain_term_is_assembled(mesh: ngs.Mesh, velocity: ngs.GridFunction) -> None:
    space = velocity.space
    trial, test = space.TnT()
    context = _context(mesh, AXISYMMETRIC, {VELOCITY: trial}, {VELOCITY: test})
    full = _energy(
        mesh,
        kernel.compose((VISCOUS,), _slots("momentum.viscous", "momentum.hoop"), context),
        velocity,
    )
    deviatoric_only = _energy(
        mesh,
        AXISYMMETRIC.volume(
            2.0
            * ngs.InnerProduct(strain(NGSOLVE_OPERATORS, trial), strain(NGSOLVE_OPERATORS, test))
        ),
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
        context = _context(
            mesh,
            measures,
            {VELOCITY: velocity.space.TrialFunction()},
            {PRESSURE: pressure_space.TestFunction()},
        )
        form += kernel.compose((CONTINUITY,), _slots("continuity"), context)
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
    context = _context(
        mesh, AXISYMMETRIC, {VELOCITY: trial_u}, {VELOCITY: test_u, PRESSURE: test_p}
    )
    form = ngs.BilinearForm(space)
    form += kernel.compose(
        (VISCOUS, CONTINUITY, INERTIA),
        _slots("momentum.viscous", "momentum.hoop", "continuity", kernel.FORCE),
        context,
    )
    state = ngs.GridFunction(space)
    state.components[0].vec.data = velocity.vec
    form.AssembleLinearization(state.vec)
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

    context = _context(
        mesh,
        AXISYMMETRIC,
        {POTENTIAL: potential},
        {VELOCITY: space.TestFunction()},
        _UnitCoefficients(screening=screening),
    )
    load = ngs.LinearForm(space)
    load += kernel.compose((BODY_FORCE,), _slots(kernel.FORCE), context)
    load.Assemble()
    assert float(ngs.InnerProduct(load.vec, axial.vec)) == pytest.approx(
        screening * WEIGHTED_AREA, rel=1e-10
    )


def test_axisymmetric_divergence_reduces_to_the_planar_one(
    mesh: ngs.Mesh, velocity: ngs.GridFunction
) -> None:
    point = mesh(1.0, 1.0)
    ops = NGSOLVE_OPERATORS
    axisymmetric = divergence(ops, geometry_of(mesh, AXISYMMETRIC), velocity)
    planar = divergence(ops, geometry_of(mesh, PLANAR), velocity)
    assert axisymmetric(point) == pytest.approx(0.0, abs=1e-12)
    assert planar(point) == pytest.approx(-1.0, rel=1e-12)

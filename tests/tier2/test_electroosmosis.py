"""VER-14 and VER-15 (with NUM-09, PHY-08): electro-osmosis in a capillary."""

import ngsolve as ngs
import numpy as np
import pytest
from scipy.special import i0

from nanopnp.io.vocabulary import POTENTIAL, PRESSURE, VELOCITY
from nanopnp.mesh.primitives import CylinderGeometry
from nanopnp.numerics.linear import solve_linear
from nanopnp.numerics.measures import Measures
from nanopnp.physics import kernel
from nanopnp.physics.backend import NGSOLVE_OPERATORS, geometry_of
from nanopnp.physics.coupled import COUPLED_TERMS, coupled_slots
from nanopnp.physics.pb import solve_pb_recorded
from nanopnp.physics.stabilisation import create as create_stabilisation

AXISYMMETRIC = Measures(symmetry="axisymmetric", element_order=2)
RADIUS_NM, LENGTH_NM = 2.0, 8.0
ZETA, FIELD = 1.0, 0.5


class _UnitViscosity:
    # A Stokes fluid of unit viscosity, so that the operator is the bare one.
    def viscosity(self) -> float:
        return 1.0


def _stokes_context(
    mesh: ngs.Mesh, space: ngs.FESpace, applied: ngs.GridFunction
) -> kernel.Context:
    trial_u, trial_p = space.TrialFunction()
    test_u, test_p = space.TestFunction()
    side = kernel.Side(
        functions={VELOCITY: trial_u, PRESSURE: trial_p, POTENTIAL: applied},
        variables=None,
        coefficients=_UnitViscosity(),
    )
    return kernel.Context(
        ops=NGSOLVE_OPERATORS,
        geometry=geometry_of(mesh, AXISYMMETRIC),
        measures=AXISYMMETRIC,
        fluid=mesh.Materials(".*"),
        trial=side,
        lagged=side,
        tests={VELOCITY: test_u, PRESSURE: test_p},
        inputs=kernel.Inputs(),
        steric=None,
        stabilisation=create_stabilisation("none"),
    )


def _electroosmotic_flow(
    debye_length_nm: float, *, maxh_nm: float = 0.2
) -> tuple[ngs.Mesh, ngs.GridFunction, ngs.GridFunction]:
    mesh = CylinderGeometry(radius_nm=RADIUS_NM, length_nm=LENGTH_NM).generate(
        maxh_nm=maxh_nm, wall_h_nm=min(maxh_nm, debye_length_nm / 4.0)
    )
    double_layer = solve_pb_recorded(
        mesh,
        AXISYMMETRIC,
        debye_length_nm=debye_length_nm,
        dirichlet="wall",
        boundary_values=ngs.CF(ZETA),
        nonlinear=False,
    )[0]
    # Debye-Hueckel for a symmetric monovalent salt: rho~_ion = -2 psi~, and the
    # Poisson source coefficient S is 1/(2 lambda^2).
    screening = 1.0 / (2.0 * debye_length_nm**2)
    charge = -2.0 * double_layer
    # The applied field is carried as a finite-element potential so that the
    # body force is built by the production function rather than by hand.
    applied = ngs.GridFunction(double_layer.space, name="applied_potential")
    applied.Set(-FIELD * ngs.y)

    velocity_space = ngs.VectorH1(mesh, order=2, dirichlet="wall", dirichletx="axis|end")
    pressure_space = ngs.H1(mesh, order=1)
    space = velocity_space * pressure_space
    context = _stokes_context(mesh, space, applied)
    slots = coupled_slots((), {VELOCITY, PRESSURE}, None, ())
    stokes = tuple(
        term for term in COUPLED_TERMS if term.name in ("Momentum", "Velocity continuity")
    )

    def charge_force(context: kernel.Context, side: kernel.Side) -> ngs.CoefficientFunction:
        return -screening * charge * ngs.grad(side.functions[POTENTIAL])

    force = kernel.KernelTerm("Body force", "PHY-08", force=charge_force)

    operator = ngs.BilinearForm(space)
    operator += kernel.compose(stokes, slots, context)
    operator.Assemble()

    # The force slot is the residual's, -int f.v; the load is its negative.
    (force_slot,) = (slot for slot in slots if slot.family == kernel.FORCE)
    load = ngs.LinearForm(space)
    load += AXISYMMETRIC.volume(-kernel.integrand((force,), force_slot, context))
    load.Assemble()

    state = ngs.GridFunction(space, name="stokes")
    solve_linear(operator, load, state)
    return mesh, state.components[0], state.components[1]


def _exact_profile(radii: np.ndarray, debye_length_nm: float) -> np.ndarray:
    return FIELD * ZETA * (i0(radii / debye_length_nm) / i0(RADIUS_NM / debye_length_nm) - 1.0)


@pytest.mark.parametrize(
    ("debye_length_nm", "regime"),
    [(2.0, "thick double layer, kappa a = 1"), (0.2, "thin double layer, kappa a = 10")],
)
def test_ver14_rice_and_whitehead_capillary_profile(debye_length_nm: float, regime: str) -> None:
    mesh, velocity, pressure = _electroosmotic_flow(debye_length_nm)
    radii = np.linspace(0.0, RADIUS_NM, 41)
    midplane = 0.5 * LENGTH_NM
    computed = np.array([velocity(mesh(float(r), midplane))[1] for r in radii])
    exact = _exact_profile(radii, debye_length_nm)

    error = np.linalg.norm(computed - exact) / np.linalg.norm(exact)
    assert error < 1e-3, f"{regime}: relative profile error {error:.3g}"

    radial = np.array([velocity(mesh(float(r), midplane))[0] for r in radii])
    assert np.abs(radial).max() < 1e-4 * np.abs(exact).max(), (
        f"{regime}: the exact flow is purely axial"
    )
    assert abs(pressure(mesh(0.5 * RADIUS_NM, midplane))) < 1e-3, (
        f"{regime}: electro-osmosis at a uniform capillary develops no pressure"
    )
    assert abs(pressure(mesh(0.5 * RADIUS_NM, 0.0))) < 1e-3
    assert abs(pressure(mesh(0.5 * RADIUS_NM, LENGTH_NM))) < 1e-3


def test_ver15_helmholtz_smoluchowski_limit_and_its_approach_rate() -> None:
    slip = -ZETA * FIELD
    midplane = 0.5 * LENGTH_NM
    deviations = []
    for debye_length_nm in (1.0, 0.5, 0.2):
        mesh, velocity, _ = _electroosmotic_flow(debye_length_nm)
        centreline = velocity(mesh(0.0, midplane))[1]
        deviation = (centreline - slip) / abs(slip)
        expected = 1.0 / i0(RADIUS_NM / debye_length_nm)
        assert deviation == pytest.approx(expected, rel=5e-3), (
            f"lambda = {debye_length_nm} nm: deviation {deviation:.4g} against 1/I0 {expected:.4g}"
        )
        deviations.append(deviation)

    assert deviations[0] > deviations[1] > deviations[2] > 0.0, (
        "the approach to the Helmholtz-Smoluchowski limit must be monotone in lambda/a"
    )
    assert deviations[-1] < 1e-3, "the thinnest double layer must reach the limit"

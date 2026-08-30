"""VER-14 and VER-15: electro-osmosis in a cylindrical capillary.

Rice & Whitehead, *J. Phys. Chem.* **69**, 4017 (1965). For a capillary of
radius ``a`` with a Debye-Hueckel double layer of zeta potential ``zeta`` under a
uniform axial field ``E``, the fully developed axial velocity is

    u_z(r) = -(eps zeta E / eta) [ 1 - I0(kappa r) / I0(kappa a) ]

which in the NUM-09 variables — potential in ``V_T``, velocity in
``u_0 = eps V_T^2/(eta L_0)``, lengths in the mesh's nanometre — carries no
material constants at all:

    u~_z(r) = E~ zeta~ [ I0(r/lambda) / I0(a/lambda) - 1 ]

VER-15 is its thin-double-layer limit: as ``lambda/a -> 0`` the centreline
velocity approaches the Helmholtz-Smoluchowski slip ``-zeta~ E~``, and the
deviation is exactly ``1/I0(a/lambda)``, which is the asymptotic rate the
acceptance criterion asks about.

The radial part of the electrical body force, ``2 S psi~ psi~'``, is a pure
gradient and is balanced entirely by the pressure. It is taken into the pressure
here — the body force is built from the *applied* potential ``-E~ z`` — which is
the same decomposition Rice & Whitehead make and which leaves ``p~ = 0``, so the
traction-free condition at the two ends is satisfied exactly rather than
approximately. The forms under test are unchanged by that choice: the viscous
operator with its hoop term, the axisymmetric divergence, the pressure coupling
and the PHY-08 body force all appear as they do in the coupled model.
"""

import ngsolve as ngs
import numpy as np
import pytest
from scipy.special import i0

from nanopnp.mesh.primitives import CylinderGeometry
from nanopnp.physics.flow import (
    continuity_term,
    electrical_body_force,
    pressure_term,
    viscous_operator,
)
from nanopnp.physics.measures import Measures
from nanopnp.physics.pb import solve_pb
from nanopnp.solve.linear import solve_linear

AXISYMMETRIC = Measures(symmetry="axisymmetric", element_order=2)
RADIUS_NM, LENGTH_NM = 2.0, 8.0
ZETA, FIELD = 1.0, 0.5
"""Wall potential in ``V_T`` and applied axial field in ``V_T`` per nm."""


def _electroosmotic_flow(
    debye_length_nm: float, *, maxh_nm: float = 0.2
) -> tuple[ngs.Mesh, ngs.GridFunction, ngs.GridFunction]:
    """Solve Debye-Hueckel then Stokes, and return the mesh, velocity and pressure."""
    mesh = CylinderGeometry(radius_nm=RADIUS_NM, length_nm=LENGTH_NM).generate(
        maxh_nm=maxh_nm, wall_h_nm=min(maxh_nm, debye_length_nm / 4.0)
    )
    double_layer = solve_pb(
        mesh,
        AXISYMMETRIC,
        debye_length_nm=debye_length_nm,
        dirichlet="wall",
        boundary_values=ngs.CF(ZETA),
        nonlinear=False,
    )
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
    trial_u, trial_p = space.TrialFunction()
    test_u, test_p = space.TestFunction()

    operator = ngs.BilinearForm(space)
    operator += viscous_operator(trial_u, test_u, AXISYMMETRIC)
    operator += pressure_term(trial_p, test_u, AXISYMMETRIC)
    operator += continuity_term(trial_u, test_p, AXISYMMETRIC)
    operator.Assemble()

    # electrical_body_force returns the *residual* contribution, which the load
    # form carries with the opposite sign; the negated coefficient is how that
    # is expressed without rewriting the term.
    load = ngs.LinearForm(space)
    load += electrical_body_force(charge, applied, test_u, AXISYMMETRIC, screening=-screening)
    load.Assemble()

    state = ngs.GridFunction(space, name="stokes")
    solve_linear(operator, load, state)
    return mesh, state.components[0], state.components[1]


def _exact_profile(radii: np.ndarray, debye_length_nm: float) -> np.ndarray:
    """Return the Rice & Whitehead profile in the nondimensional variables."""
    return FIELD * ZETA * (i0(radii / debye_length_nm) / i0(RADIUS_NM / debye_length_nm) - 1.0)


@pytest.mark.parametrize(
    ("debye_length_nm", "regime"),
    [(2.0, "thick double layer, kappa a = 1"), (0.2, "thin double layer, kappa a = 10")],
)
def test_ver14_rice_and_whitehead_capillary_profile(debye_length_nm: float, regime: str) -> None:
    """The coupled Poisson-Stokes velocity profile, in both double-layer regimes.

    The thick case has the double layer filling the capillary and the thin case
    has it confined to a tenth of the radius; a solver that had dropped the hoop
    term or the ``u_r/r`` in the divergence would fail the second in particular,
    where the shear is concentrated near the wall.
    """
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


def test_ver15_helmholtz_smoluchowski_limit_and_its_approach_rate() -> None:
    """``u_slip -> -eps zeta E / eta`` as ``lambda/a -> 0``, at the rate ``1/I0(kappa a)``.

    Asserting only the limit would be satisfied by any solver that happens to
    saturate; the deviation from it is a closed form of its own, and matching
    that is the stronger statement the acceptance criterion asks for.
    """
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

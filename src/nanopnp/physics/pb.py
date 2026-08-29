"""Poisson-Boltzmann, linear and nonlinear (PHY-21, PHY-24, FR-19).

Poisson-Boltzmann is a **distinct physics model**, not the PNP solver evaluated
at zero bias. In ePNP-NS the diffusivity and the mobility carry different
concentration corrections, so the model violates the Einstein relation at finite
concentration and its zero-bias limit is not a Boltzmann distribution (PHY-14).
Treating PB as "PNP at V = 0" would therefore be wrong in exactly the regime
where PB is most useful.

Both variants are written in the **nondimensional potential** ``phi~ = phi/V_T``
with lengths in the mesh's unit (nm, per ``mesh.primitives``). In those variables
the equations carry no material constants at all:

    linear (Debye-Hueckel):   -laplacian(phi~) + phi~ / lambda^2      = 0
    nonlinear:                -laplacian(phi~) + sinh(phi~)/lambda^2  = 0

for a symmetric monovalent electrolyte, with ``lambda`` the Debye length in mesh
units. That is the NUM-09 scaling, and it is why these two rungs of the
continuation ladder are cheap and robust enough to initialise everything else.
"""

from __future__ import annotations

import math

from nanopnp.core.constants import (
    FARADAY,
    GAS_CONSTANT,
    REFERENCE_TEMPERATURE_K,
    VACUUM_PERMITTIVITY,
)
from nanopnp.core.typing import Expression, GridFunction, IntegralTerm, Mesh
from nanopnp.physics.measures import Measures
from nanopnp.physics.poisson import poisson_operator
from nanopnp.solve.linear import DEFAULT_SOLVER, solve_linear

NEWTON_MAX_ITERATIONS = 50
"""Iteration cap for the interim nonlinear driver below."""

ELECTROLYTE_PERMITTIVITY = 78.15
"""``eps_r,f0``, the infinite-dilution relative permittivity of the electrolyte.

Gavish 2016, via SPECIFICATION.md section 8.2 and
``.knowledge/01-physics-epnpns.md`` section 4; it is the ``P0`` of the
``permittivity`` correction in ``data/corrections/willems2020_nacl.yaml``.
"""


def debye_length_nm(
    concentration_M: float,
    *,
    relative_permittivity: float = ELECTROLYTE_PERMITTIVITY,
    temperature_K: float = REFERENCE_TEMPERATURE_K,
    valence: int = 1,
) -> float:
    """Return the Debye length in nm for a symmetric ``z:z`` electrolyte.

    ``lambda_D^2 = eps R T / (2 F^2 z^2 c_0)``. Reference values it must
    reproduce (NUM-09): 1.357 nm at 0.05 M, 0.304 nm at 1 M, 0.175 nm at 3 M.

    Parameters
    ----------
    concentration_M
        Bulk concentration in mol/L.
    relative_permittivity
        Electrolyte relative permittivity.
    temperature_K
        Absolute temperature.
    valence
        Ion valence magnitude.

    Raises
    ------
    ValueError
        If the concentration is not positive.
    """
    if concentration_M <= 0.0:
        raise ValueError(f"concentration must be positive, got {concentration_M} M")
    permittivity = VACUUM_PERMITTIVITY * relative_permittivity
    concentration_SI = concentration_M * 1e3  # mol/L -> mol/m^3
    squared = (
        permittivity
        * GAS_CONSTANT
        * temperature_K
        / (2.0 * FARADAY**2 * valence**2 * concentration_SI)
    )
    return math.sqrt(squared) * 1e9  # m -> nm


def linear_pb_operator(
    trial: Expression, test: Expression, measures: Measures, *, debye_length_nm: float
) -> IntegralTerm:
    """Return the Debye-Hueckel operator ``int (grad phi~ . grad v + phi~ v / lambda^2) r``."""
    screening = 1.0 / debye_length_nm**2
    return poisson_operator(trial, test, measures) + measures.volume(screening * trial * test)


def nonlinear_pb_residual(
    potential: Expression, test: Expression, measures: Measures, *, debye_length_nm: float
) -> IntegralTerm:
    """Return the nonlinear PB residual ``int (grad phi~ . grad v + sinh(phi~) v / lambda^2) r``.

    The ``sinh`` is the Boltzmann-distributed mobile charge of a symmetric
    monovalent electrolyte: ``rho_ion = -2 F c_0 sinh(phi~)``.

    ``potential`` MUST be the **trial function**, not the grid function holding
    the current iterate. NGSolve linearises a nonlinear form by differentiating
    with respect to the trial function and substituting the state vector in
    ``AssembleLinearization``; a form written directly in terms of a grid
    function assembles a Jacobian that is **identically zero**, with no error
    raised, and Newton then fails with "matrix is singular" from the linear
    solver rather than from the actual mistake.
    """
    import ngsolve as ngs

    screening = 1.0 / debye_length_nm**2
    return poisson_operator(potential, test, measures) + measures.volume(
        screening * ngs.sinh(potential) * test
    )


def solve_pb(
    mesh: Mesh,
    measures: Measures,
    *,
    debye_length_nm: float,
    dirichlet: str,
    boundary_values: Expression,
    nonlinear: bool = True,
    order: int = 2,
    solver: str = DEFAULT_SOLVER,
) -> GridFunction:
    """Solve Poisson-Boltzmann and return the nondimensional potential.

    Parameters
    ----------
    mesh
        Meshed domain.
    measures
        Symmetry and quadrature policy; its ``element_order`` must match
        ``order``, which is checked.
    debye_length_nm
        Debye length in mesh units.
    dirichlet
        Boundary-name regular expression carrying the essential condition. The
        axis must not appear here: its condition is natural (NUM-06).
    boundary_values
        Values to set on those boundaries, in units of ``V_T``.
    nonlinear
        Solve the full ``sinh`` form, or the Debye-Hueckel linearisation.
    order
        Lagrange element order.
    solver
        Direct linear solver.

    Returns
    -------
    GridFunction
        The converged ``phi~``.

    Raises
    ------
    ValueError
        If ``measures.element_order`` does not match ``order``.
    RuntimeError
        If the nonlinear branch does not converge.

    Notes
    -----
    The nonlinear branch uses NGSolve's own damped Newton as an interim driver.
    The project's damped Newton with the gates of NUM-17 arrives in WP3 and
    replaces this call without changing the forms.
    """
    import ngsolve as ngs
    from ngsolve.solvers import Newton

    if measures.element_order != order:
        raise ValueError(
            f"measures.element_order is {measures.element_order} but the space is order {order}; "
            "the quadrature bonus of NUM-07 is computed from the element order, so a mismatch "
            "under-integrates the forms it is meant to protect"
        )

    space = ngs.H1(mesh, order=order, dirichlet=dirichlet)
    potential = ngs.GridFunction(space, name="phi_tilde")
    potential.Set(boundary_values, definedon=mesh.Boundaries(dirichlet))

    if not nonlinear:
        trial, test = space.TnT()
        a = ngs.BilinearForm(
            linear_pb_operator(trial, test, measures, debye_length_nm=debye_length_nm)
        ).Assemble()
        f = ngs.LinearForm(space).Assemble()
        solve_linear(a, f, potential, solver=solver)
        return potential

    trial, test = space.TnT()
    residual = ngs.BilinearForm(space)
    residual += nonlinear_pb_residual(trial, test, measures, debye_length_nm=debye_length_nm)
    converged, _ = Newton(
        residual,
        potential,
        freedofs=space.FreeDofs(),
        maxit=NEWTON_MAX_ITERATIONS,
        inverse=solver,
        printing=False,
    )
    if converged != 0:
        raise RuntimeError(
            f"nonlinear Poisson-Boltzmann did not converge in {NEWTON_MAX_ITERATIONS} iterations "
            f"at lambda_D = {debye_length_nm} nm"
        )
    return potential

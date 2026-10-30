"""Poisson-Boltzmann, linear and nonlinear (PHY-21, PHY-24, FR-19)."""

from __future__ import annotations

import logging

from nanopnp.core.constants import (
    REFERENCE_TEMPERATURE_K,
    VACUUM_PERMITTIVITY,
    thermal_voltage,
)
from nanopnp.core.scaling import REFERENCE_PERMITTIVITY, debye_length_nm
from nanopnp.core.typing import Expression, GridFunction, IntegralTerm, Mesh, Option
from nanopnp.numerics.gates import FieldSampler, PotentialIncrementGate
from nanopnp.numerics.linear import DEFAULT_SOLVER, solve_linear
from nanopnp.numerics.measures import Measures
from nanopnp.numerics.newton import (
    DEFAULT_SETTINGS,
    NewtonResult,
    NewtonSettings,
    damped_newton,
)
from nanopnp.physics.poisson import (
    poisson_operator,
    surface_charge_region,
    surface_charge_source,
)
from nanopnp.physics.spaces import set_boundary_values

__all__ = [
    "ELECTROLYTE_PERMITTIVITY",
    "debye_length_nm",
    "linear_pb_operator",
    "nonlinear_pb_residual",
    "solve_pb_recorded",
]

logger = logging.getLogger(__name__)

# eps_r,f0 after Gavish 2016, knowledge/01-physics-epnpns/03-the-corrections.md; held once in
# core.scaling.
ELECTROLYTE_PERMITTIVITY = REFERENCE_PERMITTIVITY


def dimensionless_surface_charge(
    surface_charge_C_m2: float,
    *,
    relative_permittivity: float,
    temperature_K: float = REFERENCE_TEMPERATURE_K,
    length_nm: float = 1.0,
) -> float:
    """Return the Neumann datum a surface charge imposes on phi~, by Gauss's law.

    Parameters
    ----------
    relative_permittivity
        The electrolyte's eps_r, the same one the Debye length was built from.
    """
    return (
        surface_charge_C_m2
        * length_nm
        * 1e-9
        / (VACUUM_PERMITTIVITY * relative_permittivity * thermal_voltage(temperature_K))
    )


def linear_pb_operator(
    trial: Expression,
    test: Expression,
    measures: Measures,
    *,
    debye_length_nm: float,
    ions: Option | None = None,
) -> IntegralTerm:
    """Return the Debye-Hueckel operator ``int (grad phi~ . grad v + phi~ v / lambda^2) r``."""
    screening = 1.0 / debye_length_nm**2
    return poisson_operator(trial, test, measures) + measures.volume(
        screening * trial * test, **_ion_region(ions)
    )


def _ion_region(ions: Option | None) -> dict[str, Option]:
    return {} if ions is None else {"definedon": ions}


def nonlinear_pb_residual(
    potential: Expression,
    test: Expression,
    measures: Measures,
    *,
    debye_length_nm: float,
    ions: Option | None = None,
) -> IntegralTerm:
    """Return the nonlinear Poisson-Boltzmann residual, in the trial function."""
    import ngsolve as ngs

    screening = 1.0 / debye_length_nm**2
    return poisson_operator(potential, test, measures) + measures.volume(
        screening * ngs.sinh(potential) * test, **_ion_region(ions)
    )


def solve_pb_recorded(
    mesh: Mesh,
    measures: Measures,
    *,
    debye_length_nm: float,
    dirichlet: str,
    boundary_values: Expression,
    ions: str | None = None,
    surface_charge: float = 0.0,
    surface_charge_boundary: str = "wall",
    nonlinear: bool = True,
    order: int = 2,
    solver: str = DEFAULT_SOLVER,
    settings: NewtonSettings = DEFAULT_SETTINGS,
    initial: GridFunction | None = None,
) -> tuple[GridFunction, NewtonResult | None]:
    """Solve Poisson-Boltzmann, returning the potential and its convergence record."""
    import ngsolve as ngs

    if measures.element_order != order:
        raise ValueError(
            f"measures.element_order is {measures.element_order} but the space is order {order}; "
            "the quadrature bonus of NUM-07 is computed from the element order, so a mismatch "
            "under-integrates the forms it is meant to protect"
        )

    space = ngs.H1(mesh, order=order, dirichlet=dirichlet)
    potential = ngs.GridFunction(space, name="phi_tilde")
    if initial is not None:
        potential.vec.data = initial.vec
    # ``Set(..., definedon=)`` zeroes everything outside the region, so the
    # essential data is written through the same projector split the coupled
    # model uses; on a cold start the interior is zero either way.
    set_boundary_values(potential, boundary_values, mesh.Boundaries(dirichlet))

    region = None if ions is None else mesh.Materials(ions)
    if region is not None and region.Mask().NumSet() == 0:
        raise ValueError(
            f"ions={ions!r} matches no material of the mesh; it carries "
            f"{', '.join(sorted(set(mesh.GetMaterials())))}. A screening term restricted to "
            "nothing would solve Laplace's equation and converge"
        )
    charged = (
        None if surface_charge == 0.0 else surface_charge_region(mesh, surface_charge_boundary)
    )

    def _charge_term(test: Expression, *, sign: float) -> IntegralTerm | None:
        if charged is None:
            return None
        return surface_charge_source(sign * surface_charge, test, measures, definedon=charged)

    if not nonlinear:
        trial, test = space.TnT()
        a = ngs.BilinearForm(
            linear_pb_operator(trial, test, measures, debye_length_nm=debye_length_nm, ions=region)
        ).Assemble()
        f = ngs.LinearForm(space)
        term = _charge_term(test, sign=1.0)
        if term is not None:
            f += term
        f.Assemble()
        solve_linear(a, f, potential, solver=solver)
        return potential, None

    trial, test = space.TnT()
    residual = ngs.BilinearForm(space)
    residual += nonlinear_pb_residual(
        trial, test, measures, debye_length_nm=debye_length_nm, ions=region
    )
    # The Poisson boundary term is +int_Gamma (dphi~/dn) v ds on the right-hand
    # side, so it is subtracted from the residual exactly as
    # CoupledModel.residual_form subtracts its own.
    term = _charge_term(test, sign=-1.0)
    if term is not None:
        residual += term

    increment = ngs.GridFunction(space, name="delta_phi_tilde")
    sampler = FieldSampler.shared(mesh, coordinates=measures.coordinate_names)
    result = damped_newton(
        residual,
        potential,
        settings=settings,
        solver=solver,
        increment=increment,
        increment_gates=[PotentialIncrementGate(sampler, increment)],
    )
    logger.debug("nonlinear Poisson-Boltzmann converged: %s", result.summary())
    return potential, result

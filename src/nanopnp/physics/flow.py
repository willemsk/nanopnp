"""The flow equations, axisymmetric (PHY-07, PHY-08, NUM-04, NUM-05)."""

from __future__ import annotations

from collections.abc import Mapping

from nanopnp.core.typing import Expression, IntegralTerm, Numeric, Option
from nanopnp.numerics.measures import Measures
from nanopnp.physics.coefficients import NondimensionalCoefficients
from nanopnp.physics.nernst_planck import ConcentrationVariables

__all__ = [
    "axisymmetric_divergence",
    "continuity_term",
    "dielectric_gradient_force",
    "electrical_body_force",
    "inertia_term",
    "permittivity_gradient",
    "pressure_term",
    "strain_rate",
    "viscous_operator",
]


def _singular(kwargs: Mapping[str, Option]) -> dict[str, Option]:
    return {**kwargs, "singular": True}


def strain_rate(velocity: Expression) -> Expression:
    """Return the in-plane rate-of-strain tensor ``eps(u) = sym grad(u)``."""
    import ngsolve as ngs

    gradient = ngs.grad(velocity)
    return 0.5 * (gradient + gradient.trans)


def axisymmetric_divergence(velocity: Expression, measures: Measures) -> Expression:
    """Return ``div^(u) = d_r u_r + u_r/r + d_z u_z``, or the planar divergence."""
    import ngsolve as ngs

    planar = ngs.Trace(ngs.grad(velocity))
    if not measures.is_axisymmetric:
        return planar
    return planar + velocity[0] / ngs.x


def viscous_operator(
    velocity: Expression,
    test: Expression,
    measures: Measures,
    *,
    viscosity: Numeric = 1.0,
    **kwargs: Option,
) -> IntegralTerm:
    """Return the viscous term ``int [2 eta eps(u):eps(v) + 2 eta u_r v_r / r^2] r``."""
    import ngsolve as ngs

    deviatoric = measures.volume(
        2.0 * viscosity * ngs.InnerProduct(strain_rate(velocity), strain_rate(test)), **kwargs
    )
    if not measures.is_axisymmetric:
        return deviatoric
    hoop = measures.volume(
        2.0 * viscosity * velocity[0] * test[0] / (ngs.x * ngs.x), **_singular(kwargs)
    )
    return deviatoric + hoop


def pressure_term(
    pressure: Expression,
    test: Expression,
    measures: Measures,
    **kwargs: Option,
) -> IntegralTerm:
    """Return ``-int p div^(v) r``, the pressure contribution to momentum."""
    return measures.volume(-pressure * axisymmetric_divergence(test, measures), **_singular(kwargs))


def continuity_term(
    velocity: Expression,
    test: Expression,
    measures: Measures,
    *,
    mass_density: Numeric | None = None,
    **kwargs: Option,
) -> IntegralTerm:
    """Return the continuity residual ``-int q rho~ div^(u~) r``."""
    divergence = axisymmetric_divergence(velocity, measures)
    if mass_density is not None:
        divergence = mass_density * divergence
    return measures.volume(-test * divergence, **_singular(kwargs))


def inertia_term(
    velocity: Expression,
    test: Expression,
    measures: Measures,
    *,
    reynolds: float,
    mass_density: Numeric = 1.0,
    **kwargs: Option,
) -> IntegralTerm:
    """Return the convective momentum term ``Re int rho~ (u~.grad) u~ . v r``."""
    import ngsolve as ngs

    convective = ngs.grad(velocity) * velocity
    return measures.volume(reynolds * mass_density * ngs.InnerProduct(convective, test), **kwargs)


def electrical_body_force(
    charge_density: Expression,
    potential: Expression,
    test: Expression,
    measures: Measures,
    *,
    screening: float,
    **kwargs: Option,
) -> IntegralTerm:
    """Return the electrical body force term ``+S int (sum_i z_i c~_i) grad(phi~) . v r``."""
    import ngsolve as ngs

    return measures.volume(
        screening * charge_density * ngs.InnerProduct(ngs.grad(potential), test), **kwargs
    )


def permittivity_gradient(
    coefficients: NondimensionalCoefficients,
    variables: ConcentrationVariables,
) -> Expression:
    """Return ``grad(eps~_r)`` by the chain rule over the concentrations."""
    if variables.logarithmic:
        raise NotImplementedError(
            "the dielectric-gradient body force is not implemented for the NUM-02 log branch: "
            "d(eps~_r)/d(c~_i) would come back as the derivative in w_i"
        )
    names = list(variables.values)
    total = coefficients.permittivity_sensitivity(names[0]) * variables.gradients[names[0]]
    for name in names[1:]:
        total = total + coefficients.permittivity_sensitivity(name) * variables.gradients[name]
    return total


def dielectric_gradient_force(
    potential: Expression,
    permittivity_gradient_expression: Expression,
    test: Expression,
    measures: Measures,
    **kwargs: Option,
) -> IntegralTerm:
    """Return the dielectric-gradient term ``+1/2 int |grad phi~|^2 grad(eps~_r) . v r``."""
    import ngsolve as ngs

    field = ngs.grad(potential)
    return measures.volume(
        0.5 * (field * field) * ngs.InnerProduct(permittivity_gradient_expression, test), **kwargs
    )

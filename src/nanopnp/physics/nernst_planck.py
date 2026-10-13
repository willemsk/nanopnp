"""The size-modified Nernst-Planck equations (PHY-04, PHY-05, NUM-02, NUM-04)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from nanopnp.core.typing import Expression, IntegralTerm, Option
from nanopnp.numerics.measures import Measures
from nanopnp.physics.coefficients import NondimensionalCoefficients

__all__ = [
    "ConcentrationVariables",
    "excess_potential_gradient",
    "nernst_planck_residual",
    "packing_fraction",
    "species_flux",
    "steric_flux",
]


@dataclass(frozen=True)
class ConcentrationVariables:
    values: Mapping[str, Expression]
    gradients: Mapping[str, Expression]
    variables: Mapping[str, Expression]
    logarithmic: bool = False

    @classmethod
    def primitive(cls, fields: Mapping[str, Expression]) -> ConcentrationVariables:
        import ngsolve as ngs

        return cls(
            values=dict(fields),
            gradients={name: ngs.grad(field) for name, field in fields.items()},
            variables=dict(fields),
            logarithmic=False,
        )

    @classmethod
    def logarithmic_branch(cls, fields: Mapping[str, Expression]) -> ConcentrationVariables:
        import ngsolve as ngs

        values = {name: ngs.exp(field) for name, field in fields.items()}
        return cls(
            values=values,
            gradients={name: values[name] * ngs.grad(field) for name, field in fields.items()},
            variables=dict(fields),
            logarithmic=True,
        )


def packing_fraction(
    values: Mapping[str, Expression], packing_coefficients: Mapping[str, float]
) -> Expression:
    terms = [packing_coefficients[name] * values[name] for name in values]
    total = terms[0]
    for term in terms[1:]:
        total = total + term
    return total


def steric_flux(
    variables: ConcentrationVariables,
    *,
    packing_coefficients: Mapping[str, float],
    volume_ratio: float,
) -> Expression:
    names = list(variables.values)
    gradient_sum = packing_coefficients[names[0]] * variables.gradients[names[0]]
    for name in names[1:]:
        gradient_sum = gradient_sum + packing_coefficients[name] * variables.gradients[name]
    occupied = packing_fraction(variables.values, packing_coefficients)
    return volume_ratio * gradient_sum / (1.0 - occupied)


def excess_potential_gradient(
    species: str,
    *,
    coefficients: NondimensionalCoefficients,
    variables: ConcentrationVariables,
    potential: Expression,
) -> Expression:
    import ngsolve as ngs

    if variables.logarithmic:
        raise NotImplementedError(
            "the dielectric-decrement term is not implemented for the NUM-02 log branch: "
            "d(eps~_r)/d(c~_i) would come back as the derivative in w_i and be wrong by a "
            "factor c~_i"
        )
    field = ngs.grad(potential)
    hessian = potential.Operator("hesse")
    sensitivity = coefficients.permittivity_sensitivity(species)
    first = 2.0 * (hessian * field) * sensitivity
    second = (field * field) * _sensitivity_gradient(sensitivity, variables)
    return -(first + second) / (2.0 * coefficients.screening)


def _sensitivity_gradient(sensitivity: Expression, variables: ConcentrationVariables) -> Expression:
    names = list(variables.values)
    total = sensitivity.Diff(variables.variables[names[0]]) * variables.gradients[names[0]]
    for name in names[1:]:
        total = total + sensitivity.Diff(variables.variables[name]) * variables.gradients[name]
    return total


def species_flux(
    species: str,
    *,
    coefficients: NondimensionalCoefficients,
    variables: ConcentrationVariables,
    potential: Expression,
    velocity: Expression | None = None,
    steric: bool = True,
    dielectric_gradient: bool = False,
) -> Expression:
    ion = coefficients.electrolyte.ion(species)
    concentration = variables.values[species]
    diffusivity = coefficients.diffusivity(species)

    import ngsolve as ngs

    bracket = diffusivity * variables.gradients[species]
    bracket = bracket + float(ion.valence) * coefficients.mobility(
        species
    ) * concentration * ngs.grad(potential)
    if steric:
        bracket = bracket + diffusivity * concentration * steric_flux(
            variables,
            packing_coefficients=coefficients.packing_coefficients,
            volume_ratio=coefficients.steric_volume_ratio(species),
        )
    if dielectric_gradient:
        bracket = bracket + diffusivity * concentration * excess_potential_gradient(
            species, coefficients=coefficients, variables=variables, potential=potential
        )
    if velocity is not None:
        bracket = bracket - coefficients.peclet * velocity * concentration
    return -bracket


def nernst_planck_residual(
    flux: Expression,
    test: Expression,
    measures: Measures,
    **kwargs: Option,
) -> IntegralTerm:
    import ngsolve as ngs

    return measures.volume(flux * ngs.grad(test), **kwargs)

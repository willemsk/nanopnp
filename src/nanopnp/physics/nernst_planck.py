"""The size-modified Nernst-Planck equations' terms (PHY-04, PHY-05, PHY-23, NUM-02, NUM-04)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, TypeAlias

from nanopnp.core.typing import Expression
from nanopnp.io.vocabulary import POTENTIAL, VELOCITY
from nanopnp.materials.fields import SolidBlend, blend_sensitivity
from nanopnp.physics.coefficients import NondimensionalCoefficients
from nanopnp.physics.operators import Operators

if TYPE_CHECKING:
    from nanopnp.physics.kernel import Context, Side

__all__ = [
    "ConcentrationVariables",
    "StericForm",
    "advection_drift",
    "borukhov_flux",
    "decrement_drift",
    "diffusion",
    "excess_potential_gradient",
    "migration_drift",
    "packing_fraction",
    "steric_drift",
    "steric_flux",
]


@dataclass(frozen=True)
class ConcentrationVariables:
    """The concentrations and their gradients, in either formulation of NUM-02."""

    values: Mapping[str, Expression]
    gradients: Mapping[str, Expression]
    variables: Mapping[str, Expression]
    logarithmic: bool = False

    @classmethod
    def primitive(cls, fields: Mapping[str, Expression], ops: Operators) -> ConcentrationVariables:
        """Return primitive variables: the unknown is the concentration."""
        return cls(
            values=dict(fields),
            gradients={name: ops.grad(field) for name, field in fields.items()},
            variables=dict(fields),
            logarithmic=False,
        )

    @classmethod
    def logarithmic_branch(
        cls, fields: Mapping[str, Expression], ops: Operators
    ) -> ConcentrationVariables:
        """Return log variables ``c~_i = exp(w_i)``, which keep positivity exact by construction."""
        values = {name: ops.exp(field) for name, field in fields.items()}
        return cls(
            values=values,
            gradients={name: values[name] * ops.grad(field) for name, field in fields.items()},
            variables=dict(fields),
            logarithmic=True,
        )


def packing_fraction(
    values: Mapping[str, Expression], packing_coefficients: Mapping[str, float]
) -> Expression:
    """Return ``Phi = sum_j nu_j c~_j``, the dimensionless packing fraction."""
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
    """Return the steric flux ``beta~_i`` (a sign error diverges).

    Parameters
    ----------
    variables
        Concentrations and their gradients.
    packing_coefficients
        ``nu_j = N_A a_j^3 c_0`` by species name.
    volume_ratio
        ``a_i^3 / a_0^3`` for the species this flux belongs to.
    """
    names = list(variables.values)
    gradient_sum = packing_coefficients[names[0]] * variables.gradients[names[0]]
    for name in names[1:]:
        gradient_sum = gradient_sum + packing_coefficients[name] * variables.gradients[name]
    occupied = packing_fraction(variables.values, packing_coefficients)
    return volume_ratio * gradient_sum / (1.0 - occupied)


StericForm: TypeAlias = Callable[
    [ConcentrationVariables, NondimensionalCoefficients, str], Expression
]


def borukhov_flux(
    variables: ConcentrationVariables, coefficients: NondimensionalCoefficients, species: str
) -> Expression:
    """Return the steric flux of one species in the form PHY-05 gives."""
    return steric_flux(
        variables,
        packing_coefficients=coefficients.packing_coefficients,
        volume_ratio=coefficients.steric_volume_ratio(species),
    )


def excess_potential_gradient(
    species: str,
    *,
    ops: Operators,
    coefficients: NondimensionalCoefficients,
    variables: ConcentrationVariables,
    potential: Expression,
    solid: SolidBlend | None = None,
) -> Expression:
    """Return ``grad(mu~_ex,i)``, the dielectric-decrement term (a deviation).

    Parameters
    ----------
    solid
        The blend's solid side where a solid fraction is supplied; None for the sharp split.

    Raises
    ------
    NotImplementedError
        In the log branch.
    """
    if variables.logarithmic:
        raise NotImplementedError(
            "the dielectric-decrement term is not implemented for the NUM-02 log branch: "
            "d(eps~_r)/d(c~_i) would come back as the derivative in w_i and be wrong by a "
            "factor c~_i"
        )
    field = ops.grad(potential)
    sensitivity = coefficients.permittivity_sensitivity(species)
    sensitivity_gradient = _sensitivity_gradient(ops, sensitivity, variables)
    if solid is not None:
        sensitivity, sensitivity_gradient = blend_sensitivity(
            solid, sensitivity, sensitivity_gradient
        )
    first = 2.0 * ops.apply(ops.hessian(potential), field) * sensitivity
    second = ops.dot(field, field) * sensitivity_gradient
    return -(first + second) / (2.0 * coefficients.screening)


def _sensitivity_gradient(
    ops: Operators, sensitivity: Expression, variables: ConcentrationVariables
) -> Expression:
    names = list(variables.values)
    total = (
        ops.derivative(sensitivity, variables.variables[names[0]]) * variables.gradients[names[0]]
    )
    for name in names[1:]:
        total = total + (
            ops.derivative(sensitivity, variables.variables[name]) * variables.gradients[name]
        )
    return total


def diffusion(context: Context) -> Expression:
    """Return the diffusive part of the flux bracket, ``D~_i grad(c~_i)``, on the trial side."""
    species = context.require_species()
    trial = context.trial
    return trial.coefficients.diffusivity(species) * trial.variables.gradients[species]


def migration_drift(context: Context, side: Side, species: str) -> Expression:
    """Return the migration drift ``z_i mu~_i grad(phi~)``."""
    coefficients = side.coefficients
    valence = float(coefficients.electrolyte.ion(species).valence)
    return valence * coefficients.mobility(species) * context.ops.grad(side.functions[POTENTIAL])


def steric_drift(context: Context, side: Side, species: str) -> Expression | None:
    """Return the steric drift ``D~_i beta~_i``; None where no steric model is in force."""
    if context.steric is None:
        return None
    coefficients = side.coefficients
    return coefficients.diffusivity(species) * context.steric(side.variables, coefficients, species)


def advection_drift(context: Context, side: Side, species: str) -> Expression | None:
    """Return the advective drift ``-Pe u~``; None on a side with no velocity."""
    del context, species
    velocity = side.functions.get(VELOCITY)
    if velocity is None:
        return None
    return -(side.coefficients.peclet * velocity)


def decrement_drift(context: Context, side: Side, species: str) -> Expression:
    """Return PHY-23's decrement drift ``D~_i grad(mu~_ex,i)``."""
    coefficients = side.coefficients
    return coefficients.diffusivity(species) * excess_potential_gradient(
        species,
        ops=context.ops,
        coefficients=coefficients,
        variables=side.variables,
        potential=side.functions[POTENTIAL],
        solid=context.inputs.solid,
    )

"""The size-modified Nernst-Planck equations (PHY-04, PHY-05, NUM-02, NUM-04).

In the nondimensional variables of :mod:`nanopnp.physics.coefficients` the flux
of species ``i`` on the fluid domain is

    J~_i = -[ D~_i grad(c~_i) + z_i mu~_i c~_i grad(phi~)
              + D~_i beta~_i c~_i - Pe u~ c~_i ]

and the weak form is ``int J~_i . grad(w) r dr dz = 0``, with the no-flux
condition on the pore and membrane walls left natural.

Formulation is in **primitive concentrations** (NUM-02). The log-variable branch
``c~_i = exp(w_i)`` is available through :class:`ConcentrationVariables` and
gives exact positivity at the cost of a harder nonlinear problem. Slotboom
variables are rejected outright: ``phi~`` spans +/-7.78 over the +/-200 mV
envelope, so the exponential weights ``exp(-z_i phi~)`` span six decades inside
one solve.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from nanopnp.core.typing import Expression, IntegralTerm, Option
from nanopnp.physics.coefficients import NondimensionalCoefficients
from nanopnp.physics.measures import Measures

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
    """The ``c~_i`` and their gradients, in either formulation of NUM-02.

    The forms below never call ``ngsolve.grad`` on a concentration themselves,
    because in the log branch the concentration is ``exp(w_i)`` and is not a
    finite-element function. Both the value and its gradient come from here, so
    one flux expression serves both formulations.

    Parameters
    ----------
    values
        ``c~_i`` by species name.
    gradients
        ``grad(c~_i)`` by species name.
    variables
        The finite-element unknowns themselves, ``c~_i`` or ``w_i``. Kept so
        that a caller which needs to differentiate a coefficient with respect to
        the solved variable — the PHY-23 dielectric-decrement terms — can tell
        which it is holding.
    logarithmic
        Whether the log branch is in force.
    """

    values: Mapping[str, Expression]
    gradients: Mapping[str, Expression]
    variables: Mapping[str, Expression]
    logarithmic: bool = False

    @classmethod
    def primitive(cls, fields: Mapping[str, Expression]) -> ConcentrationVariables:
        """Return primitive variables: the unknown *is* the concentration."""
        import ngsolve as ngs

        return cls(
            values=dict(fields),
            gradients={name: ngs.grad(field) for name, field in fields.items()},
            variables=dict(fields),
            logarithmic=False,
        )

    @classmethod
    def logarithmic_branch(cls, fields: Mapping[str, Expression]) -> ConcentrationVariables:
        """Return log variables ``c~_i = exp(w_i)`` (NUM-02 fallback branch).

        Positivity is then exact by construction, which is what the branch is
        for: the primitive form gives no such guarantee and relies on the NUM-17
        gate to catch a negative iterate.
        """
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
    """Return ``Phi = sum_j nu_j c~_j``, the dimensionless packing fraction (PHY-06).

    ``beta_i`` carries ``1/(1 - Phi)`` and is singular at ``Phi = 1``; the
    NUM-17 gate watches the same quantity on the sampled state.
    """
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
    """Return the steric flux vector ``beta~_i`` of PHY-05.

    ``beta~_i = (a_i^3/a_0^3) sum_j nu_j grad(c~_j) / (1 - sum_j nu_j c~_j)``

    .. warning::

       **This is the most likely place for a sign error in the entire model.**
       ``beta_i`` enters the flux bracket of :func:`species_flux` with a **plus**
       and the whole bracket is then negated, so the steric contribution drives
       ions *out of* crowded regions. A flipped sign drives them *into* them,
       pushes the packing fraction towards 1, makes the denominator vanish and
       diverges — after producing plausible intermediate iterates.

    Two further things must not be simplified away. The sum over ``j`` runs over
    **all** species and couples them: it is not a self-interaction, and
    collapsing it changes the physics. And the ``a_i^3/a_0^3`` prefactor is
    4.16 for the reference NaCl parameters, not a normalisation that can be
    dropped (PHY-05).

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


def excess_potential_gradient(
    species: str,
    *,
    coefficients: NondimensionalCoefficients,
    variables: ConcentrationVariables,
    potential: Expression,
) -> Expression:
    """Return ``grad(mu~_ex,i)``, the dielectric-decrement term of PHY-23.

    The excess chemical potential is ``mu_ex,i = -1/2 |grad phi|^2 d(eps)/d(c_i)``,
    which in the NUM-09 variables is ``-|grad phi~|^2 g_i / (2 S)`` with
    ``g_i = d(eps~_r)/d(c~_i)`` and ``S`` the screening coefficient. Its gradient
    is taken by the chain rule,

        grad(mu~_ex,i) = -(1/2S) [ 2 (Hess phi~) grad(phi~) g_i
                                   + |grad phi~|^2 sum_j (d g_i/d c~_j) grad(c~_j) ]

    so the only NGSolve construct beyond a first derivative is the Hessian of
    ``phi~``, which for P2 is element-wise constant.

    **This term is a deviation from the validated model** and is reachable only
    through ``dielectric_gradient_forces``, which enables it together with the
    momentum term of :func:`nanopnp.physics.flow.dielectric_gradient_force`.
    PHY-23 forbids either in isolation: including one without the other is
    thermodynamically inconsistent.

    Raises
    ------
    NotImplementedError
        In the log branch. The sensitivity is differentiated with respect to the
        solved variable, and in that branch the variable is ``w_i``, not
        ``c~_i``; returning the ``w`` derivative would silently scale the term
        by ``c~_i``.
    """
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
    """Return ``sum_j (d g_i / d c~_j) grad(c~_j)`` by symbolic differentiation."""
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
    """Return the dimensionless total flux ``J~_i`` of one species (PHY-04).

    ``J~_i = -[ D~_i grad(c~_i) + z_i mu~_i c~_i grad(phi~)
                + D~_i beta~_i c~_i - Pe u~ c~_i ]``

    The bracket is assembled term by term with the signs above and negated once,
    at the end. The steric term enters with a ``+`` (PHY-05, and see
    :func:`steric_flux`); the convective term enters with a ``-`` so that after
    the negation ions are carried *with* the flow.

    Parameters
    ----------
    species
        Ion name.
    coefficients
        Nondimensional material coefficients.
    variables
        Concentrations and their gradients.
    potential
        The dimensionless potential ``phi~``.
    velocity
        The dimensionless velocity ``u~``, or ``None`` for a model with no flow
        (``pnp``), which drops the convective term rather than multiplying by a
        zero field.
    steric
        Whether ``beta~_i`` is included. ``False`` is ``beta_i = 0``, the
        classical PNP flux (PHY-21, PHY-22).
    dielectric_gradient
        Whether the PHY-23 dielectric-decrement term is included. A deviation
        from the validated model; default off.
    """
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
    """Return ``int J~_i . grad(w) r``, the weak Nernst-Planck residual (NUM-04).

    The boundary term this integration by parts leaves is ``-int_Gamma w n.J_i``,
    so the no-flux condition of PHY-09 on the pore and membrane walls is natural
    and must not be imposed. Pass ``definedon=mesh.Materials(...)`` to restrict
    the equation to the fluid.

    The integrand carries no ``1/r`` factor: the axisymmetric divergence is
    never formed, only the two-dimensional gradient against the test function.
    """
    import ngsolve as ngs

    return measures.volume(flux * ngs.grad(test), **kwargs)

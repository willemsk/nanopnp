"""The flow equations' terms (PHY-07, PHY-08, PHY-23, NUM-04, NUM-05)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from nanopnp.core.typing import Expression
from nanopnp.io.vocabulary import POTENTIAL, PRESSURE, PRESSURE_MEAN, VELOCITY
from nanopnp.materials.fields import SolidBlend, blend_gradient
from nanopnp.physics.coefficients import NondimensionalCoefficients
from nanopnp.physics.nernst_planck import ConcentrationVariables
from nanopnp.physics.operators import divergence, hoop, strain

if TYPE_CHECKING:
    from nanopnp.physics.kernel import Context, Side

__all__ = [
    "continuity",
    "dielectric_force",
    "hoop_stress",
    "inertia_force",
    "ionic_force",
    "permittivity_gradient",
    "pressure",
    "pressure_constraint",
    "viscous_stress",
]


def viscous_stress(context: Context) -> Expression:
    """Return the in-plane viscous stress ``2 eta~ eps(u~)``."""
    trial = context.trial
    return 2.0 * trial.coefficients.viscosity() * strain(context.ops, trial.functions[VELOCITY])


def hoop_stress(context: Context) -> Expression | None:
    """Return the hoop stress ``2 eta~ u~_r / r``; None without a radial direction."""
    trial = context.trial
    part = hoop(context.ops, context.geometry, trial.functions[VELOCITY])
    return None if part is None else 2.0 * trial.coefficients.viscosity() * part


def pressure(context: Context) -> Expression:
    """Return the pressure's part of the stress against the test's divergence, ``-p~``."""
    return -context.trial.functions[PRESSURE]


def continuity(context: Context) -> Expression:
    """Return the continuity residual ``rho~ div(u~)``, the density held at 1 where it is None."""
    trial = context.trial
    rate = divergence(context.ops, context.geometry, trial.functions[VELOCITY])
    return rate if trial.density is None else trial.density * rate


def inertia_force(context: Context, side: Side) -> Expression:
    """Return the inertia as a force density, ``-Re rho~ (grad u~) u~``."""
    velocity = side.functions[VELOCITY]
    density = 1.0 if side.density is None else side.density
    convective = context.ops.apply(context.ops.grad(velocity), velocity)
    return -(side.coefficients.reynolds * density * convective)


def ionic_force(context: Context, side: Side) -> Expression:
    """Return the ionic body force density ``-S (sum_i z_i c~_i) grad(phi~)``."""
    coefficients = side.coefficients
    field = context.ops.grad(side.functions[POTENTIAL])
    return -(coefficients.screening * coefficients.ionic_charge_density()) * field


def dielectric_force(context: Context, side: Side) -> Expression | None:
    """Return PHY-23's force density ``-1/2 |grad phi~|^2 grad(eps~_r)``; None where it is zero."""
    gradient = permittivity_gradient(side.coefficients, side.variables, solid=context.inputs.solid)
    if gradient is None:
        return None
    field = context.ops.grad(side.functions[POTENTIAL])
    return -0.5 * context.ops.dot(field, field) * gradient


def pressure_constraint(context: Context) -> Expression:
    """Return ``p~ q_lambda + lambda q``, the saddle-point form of a prescribed mean pressure."""
    trial, tests = context.trial.functions, context.tests
    return trial[PRESSURE] * tests[PRESSURE_MEAN] + trial[PRESSURE_MEAN] * tests[PRESSURE]


def permittivity_gradient(
    coefficients: NondimensionalCoefficients,
    variables: ConcentrationVariables,
    *,
    solid: SolidBlend | None = None,
) -> Expression | None:
    """Return ``grad(eps~_r)`` in the electrolyte, by the chain rule over the concentrations.

    Parameters
    ----------
    solid
        The blend's solid side where a solid fraction is supplied; None for the sharp split,
        under which ``eps~_r`` is the fluid's own in the electrolyte.

    Returns
    -------
    Expression or None
        None where the gradient is zero: no fit moves ``eps_r,f`` and no blend is supplied.
    """
    fluid = coefficients.relative_permittivity()
    total: Expression | None
    if not coefficients.permittivity_varies:
        total = None
    elif variables.logarithmic:
        raise NotImplementedError(
            "the dielectric-gradient body force is not implemented for the NUM-02 log branch: "
            "d(eps~_r)/d(c~_i) would come back as the derivative in w_i"
        )
    else:
        names = list(variables.values)
        total = coefficients.permittivity_sensitivity(names[0]) * variables.gradients[names[0]]
        for name in names[1:]:
            total = total + coefficients.permittivity_sensitivity(name) * variables.gradients[name]
    if solid is None:
        return total
    return blend_gradient(solid, fluid, total)

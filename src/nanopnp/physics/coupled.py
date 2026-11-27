"""The coupled models' terms and slots: today's integrals of ``pnp``, ``pnp-ns`` and ``epnp-ns``."""

from __future__ import annotations

from collections.abc import Collection, Sequence

from nanopnp.core.typing import Expression
from nanopnp.io.vocabulary import (
    POTENTIAL,
    PRESSURE,
    PRESSURE_MEAN,
    VELOCITY,
    concentration_field_name,
)
from nanopnp.physics import flow, nernst_planck
from nanopnp.physics.kernel import FLUX, FORCE, Close, Context, Contribution, KernelTerm, Slot
from nanopnp.physics.operators import divergence, hoop, strain
from nanopnp.physics.stabilisation import (
    CROSSWIND_BONUS_ORDER,
    FLOW_BONUS_ORDER,
    STREAMLINE_BONUS_ORDER,
    flow_contribution,
    transport_contribution,
)
from nanopnp.physics.terms import EPNP_NS_TERMS, Term

__all__ = [
    "COUPLED_TERMS",
    "PRESSURE_CONSTRAINT",
    "SOURCES",
    "STABILISATION",
    "coupled_slots",
]

PRESSURE_CONSTRAINT = "Pressure constraint"
STABILISATION = "Stabilisation"
SOURCES = "Sources"


def _times_test(total: Expression, context: Context) -> Expression:
    return total * context.tests[context.require_field()]


def _dot_test(total: Expression, context: Context) -> Expression:
    return context.ops.dot(total, context.tests[context.require_field()])


def _dot_test_gradient(total: Expression, context: Context) -> Expression:
    return context.ops.dot(total, context.ops.grad(context.tests[context.require_field()]))


def _negated_flux(total: Expression, context: Context) -> Expression:
    return -_dot_test_gradient(total, context)


def _identity(total: Expression, context: Context) -> Expression:
    del context
    return total


def _strain_of_test(total: Expression, context: Context) -> Expression:
    return context.ops.inner(total, strain(context.ops, context.tests[VELOCITY]))


def _hoop_of_test(total: Expression, context: Context) -> Expression:
    part = hoop(context.ops, context.geometry, context.tests[VELOCITY])
    if part is None:
        raise RuntimeError("the hoop slot was closed without a radial direction")
    return total * part


def _divergence_of_test(total: Expression, context: Context) -> Expression:
    return total * divergence(context.ops, context.geometry, context.tests[VELOCITY])


def _continuity_test(total: Expression, context: Context) -> Expression:
    return -context.tests[PRESSURE] * total


def _force_on_test(total: Expression, context: Context) -> Expression:
    return -context.ops.dot(total, context.tests[VELOCITY])


def _source_close(field: str) -> Close:
    return _dot_test if field == VELOCITY else _times_test


def coupled_slots(
    species: Sequence[str],
    fields: Collection[str],
    fixed_charge_rule: int | None,
    sources: Collection[str],
) -> tuple[Slot, ...]:
    """Return the coupled residual's slots in assembly order, those of absent fields left out.

    Parameters
    ----------
    fields
        The fields the model solves.
    fixed_charge_rule
        The fixed charge's own rule, or None for the estimated one.
    sources
        The fields a manufactured source is given for.
    """
    slots = [
        Slot("poisson.stiffness", POTENTIAL, "omega", _dot_test_gradient),
        Slot("poisson.mobile_charge", POTENTIAL, "fluid", _times_test),
        Slot("poisson.fixed_charge", POTENTIAL, "omega", _times_test, rule_order=fixed_charge_rule),
        Slot("poisson.surface_charge", POTENTIAL, "surface", _times_test, kind="surface"),
    ]
    for name in species:
        field = concentration_field_name(name)
        slots += [
            Slot(FLUX, field, "fluid", _negated_flux, species=name),
            Slot(
                "streamline",
                field,
                "fluid",
                _identity,
                extra_order=STREAMLINE_BONUS_ORDER,
                species=name,
            ),
            Slot(
                "crosswind",
                field,
                "fluid",
                _identity,
                extra_order=CROSSWIND_BONUS_ORDER,
                species=name,
            ),
        ]
    slots += [
        Slot("momentum.viscous", VELOCITY, "fluid", _strain_of_test),
        Slot("momentum.hoop", VELOCITY, "fluid", _hoop_of_test, singular=True),
        Slot("momentum.pressure", VELOCITY, "fluid", _divergence_of_test, singular=True),
        Slot("continuity", PRESSURE, "fluid", _continuity_test, singular=True),
        Slot(FORCE, VELOCITY, "fluid", _force_on_test),
        Slot("constraint", PRESSURE_MEAN, "fluid", _identity),
        Slot("flow.gls_momentum", VELOCITY, "fluid", _identity, extra_order=FLOW_BONUS_ORDER),
        Slot("flow.gls_pressure", PRESSURE, "fluid", _identity, extra_order=FLOW_BONUS_ORDER),
        Slot(
            "flow.grad_div",
            VELOCITY,
            "fluid",
            _identity,
            extra_order=FLOW_BONUS_ORDER,
            singular=True,
        ),
    ]
    slots += [
        Slot(
            "source",
            field,
            "omega" if field == POTENTIAL else "fluid",
            _source_close(field),
            per_field=True,
        )
        for field in fields
        if field in sources
    ]
    return tuple(slot for slot in slots if slot.test in fields)


def _permittivity_flux(context: Context) -> Expression:
    permittivity = context.inputs.permittivity
    if permittivity is None:
        raise ValueError("Poisson's stiffness needs the permittivity among the inputs")
    return permittivity * context.ops.grad(context.trial.functions[POTENTIAL])


def _mobile_charge(context: Context) -> Expression:
    coefficients = context.trial.coefficients
    return -(coefficients.screening * coefficients.ionic_charge_density())


def _fixed_charge(context: Context) -> Expression | None:
    charge = context.inputs.fixed_charge
    return None if charge is None else -charge.density


def _surface_charge(context: Context) -> Expression | None:
    charge = context.inputs.surface_charge
    return None if charge is None else -1.0 * charge


def _source(context: Context) -> Expression | None:
    source = context.inputs.sources.get(context.require_field())
    return None if source is None else -source


def _display(name: str) -> Term:
    for term in EPNP_NS_TERMS:
        if term.name == name:
            return term
    raise KeyError(f"no display term {name!r} in EPNP_NS_TERMS")


_NERNST_PLANCK = "Nernst\N{EN DASH}Planck"

COUPLED_TERMS: tuple[KernelTerm, ...] = (
    KernelTerm(
        "Poisson",
        "PHY-03",
        _display("Poisson"),
        (
            Contribution("poisson.stiffness", _permittivity_flux),
            Contribution("poisson.mobile_charge", _mobile_charge),
            Contribution("poisson.fixed_charge", _fixed_charge),
            Contribution("poisson.surface_charge", _surface_charge),
        ),
    ),
    KernelTerm(
        _NERNST_PLANCK,
        "PHY-04",
        _display(_NERNST_PLANCK),
        (Contribution(FLUX, nernst_planck.diffusion),),
        drift=nernst_planck.migration_drift,
        drift_text="z_i mu_i grad(phi~)",
    ),
    KernelTerm(
        "Steric flux",
        "PHY-05",
        _display("Steric flux"),
        drift=nernst_planck.steric_drift,
        drift_text="D_i beta_i",
    ),
    KernelTerm(
        "Advection",
        "PHY-04",
        _display("Advection"),
        drift=nernst_planck.advection_drift,
        drift_text="- Pe u~",
    ),
    KernelTerm(
        "Dielectric decrement",
        "PHY-23",
        _display("Dielectric decrement"),
        drift=nernst_planck.decrement_drift,
        drift_text="D_i grad(mu~_ex,i)",
    ),
    KernelTerm(
        "Momentum",
        "PHY-07",
        _display("Momentum"),
        (
            Contribution("momentum.viscous", flow.viscous_stress),
            Contribution("momentum.hoop", flow.hoop_stress),
            Contribution("momentum.pressure", flow.pressure),
        ),
    ),
    KernelTerm("Inertia", "NUM-04", _display("Inertia"), force=flow.inertia_force),
    KernelTerm(
        "Velocity continuity",
        "NUM-04",
        _display("Velocity continuity"),
        (Contribution("continuity", flow.continuity),),
    ),
    KernelTerm("Variable density", "NUM-04", _display("Variable density")),
    KernelTerm("Body force", "PHY-08", _display("Body force"), force=flow.ionic_force),
    KernelTerm(
        "Dielectric-gradient force",
        "PHY-23",
        _display("Dielectric-gradient force"),
        force=flow.dielectric_force,
    ),
    KernelTerm("Corrections", "PHY-10", _display("Corrections")),
    KernelTerm(
        PRESSURE_CONSTRAINT,
        "NUM-04",
        contributions=(Contribution("constraint", flow.pressure_constraint),),
    ),
    KernelTerm(
        STABILISATION,
        "NUM-11",
        contributions=(
            Contribution("streamline", transport_contribution("streamline")),
            Contribution("crosswind", transport_contribution("crosswind")),
            Contribution("flow.gls_momentum", flow_contribution("flow.gls_momentum")),
            Contribution("flow.gls_pressure", flow_contribution("flow.gls_pressure")),
            Contribution("flow.grad_div", flow_contribution("flow.grad_div")),
        ),
    ),
    KernelTerm(SOURCES, "VER-18", contributions=(Contribution("source", _source),)),
)
"""The coupled models' terms: ``EPNP_NS_TERMS``' records in order, then three of the kernel's."""

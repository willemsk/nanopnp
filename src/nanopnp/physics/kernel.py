"""A prototype of the kernel: terms add contributions to slots, and each slot is integrated once."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, Literal

from nanopnp.core.typing import Expression, IntegralTerm, Mesh, Option
from nanopnp.io.vocabulary import POTENTIAL, PRESSURE, PRESSURE_MEAN, VELOCITY
from nanopnp.materials.electrolyte import NO_STERIC_MODEL
from nanopnp.materials.fields import SolidBlend
from nanopnp.numerics.measures import FixedCharge, Measures
from nanopnp.physics.coefficients import NondimensionalCoefficients
from nanopnp.physics.flow import (
    axisymmetric_divergence,
    permittivity_gradient,
    strain_rate,
)
from nanopnp.physics.nernst_planck import ConcentrationVariables, excess_potential_gradient
from nanopnp.physics.stabilisation import (
    CROSSWIND_BONUS_ORDER,
    FLOW_BONUS_ORDER,
    STREAMLINE_BONUS_ORDER,
)
from nanopnp.physics.terms import EPNP_NS_TERMS, Term

if TYPE_CHECKING:
    from nanopnp.physics.models import CoupledModel

__all__ = [
    "COUPLED_TERMS",
    "DROP_VARIABLE",
    "SWITCH_RECORDS",
    "Context",
    "Contribution",
    "KernelTerm",
    "Slot",
    "Switch",
    "compose",
    "compose_integrals",
    "coupled_slots",
    "dielectric_force",
    "in_force",
    "ionic_force",
]

DROP_VARIABLE = "NANOPNP_PROTOTYPE_DROP"
"""The environment variable naming, comma-separated, the terms the prototype leaves out."""

Domain = Literal["omega", "fluid", "surface_charge"]


@dataclass(frozen=True)
class Context:
    """What a contribution reads: the functions, the coefficients and the model at one assembly."""

    model: CoupledModel
    mesh: Mesh
    measures: Measures
    fluid: Expression
    trials: Mapping[str, Expression]
    tests: Mapping[str, Expression]
    lagged: Mapping[str, Expression]
    variables: ConcentrationVariables
    lagged_variables: ConcentrationVariables
    coefficients: NondimensionalCoefficients
    lagged_coefficients: NondimensionalCoefficients
    permittivity: Expression
    terms_in_force: frozenset[str]
    solid: SolidBlend | None = None
    fixed_charge: FixedCharge | None = None
    surface_charge: Expression | None = None
    surface_region: Expression | None = None
    sources: Mapping[str, Expression] | None = None
    species: str | None = None
    field: str | None = None

    def at(self, species: str | None, field: str | None) -> Context:
        """Return this context with the species at hand and its concentration field set."""
        return replace(self, species=species, field=field)

    @property
    def density(self) -> Expression | None:
        """Return the mass density the variable-density term brings in force, else None."""
        if "Variable density" in self.terms_in_force:
            return self.coefficients.mass_density()
        return None

    def require_species(self) -> str:
        """Return the species at hand; RuntimeError on a slot that has none."""
        if self.species is None:
            raise RuntimeError("a per-species contribution was evaluated with no species at hand")
        return self.species

    def require_field(self) -> str:
        """Return the concentration field of the species at hand."""
        if self.field is None:
            raise RuntimeError("a per-species contribution was evaluated with no field at hand")
        return self.field


Closer = Callable[[Expression, Context], Expression]


@dataclass(frozen=True)
class Slot:
    """One integral of one equation: its test field, domain, quadrature rule and closing.

    Parameters
    ----------
    family
        The name a contribution addresses; a per-species slot shares it across species.
    test
        The field whose test function the slot takes.
    close
        Turns the summed contributions into the integrand; the identity where each
        contribution carries its own test function.
    """

    family: str
    test: str
    kind: Literal["volume", "surface"]
    domain: Domain
    close: Closer
    singular: bool = False
    extra_order: int = 0
    rule_order: int | None = None
    species: str | None = None

    @property
    def name(self) -> str:
        """Return the slot's name: its family, and its species where it has one."""
        return self.family if self.species is None else f"{self.family}:{self.species}"


@dataclass(frozen=True)
class Contribution:
    """An expression a term adds to one slot family; None where it adds nothing."""

    slot: str
    build: Callable[[Context], Expression | None]


@dataclass(frozen=True)
class KernelTerm:
    """A term of the model: its display term, if any, and the contributions it adds."""

    name: str
    contributions: tuple[Contribution, ...]
    display: Term | None = None


@dataclass(frozen=True)
class Switch:
    """A switch as data: its case path, validated default and what it brings in force."""

    name: str
    path: str
    default: bool
    terms: tuple[str, ...]
    requires: tuple[str, ...] = ()
    excludes: tuple[str, ...] = ()


SWITCH_RECORDS: tuple[Switch, ...] = (
    Switch(
        "flow",
        "physics.flow",
        default=True,
        terms=("Advection", "Momentum", "Inertia", "Velocity continuity", "Body force"),
    ),
    Switch(
        "variable_density",
        "physics.variable_density",
        default=True,
        terms=("Variable density",),
        requires=("flow",),
    ),
    Switch("inertia", "physics.inertia", default=True, terms=("Inertia",), requires=("flow",)),
    Switch(
        "dielectric_gradient_forces",
        "physics.dielectric_gradient_forces",
        default=False,
        terms=("Dielectric-gradient force", "Dielectric decrement"),
        requires=("flow",),
        excludes=("log_variables",),
    ),
)
"""The four switches of PHY-08, PHY-23 and NUM-04 as records; PHY-23's pair stands under one."""


def _leaf_is_none(model: CoupledModel, leaf: str) -> bool:
    parts = leaf.split(".")
    if parts[:2] != ["electrolyte", "corrections"] or parts[-1] != "model":
        raise ValueError(f"the prototype reads no correction leaf {leaf!r}")
    value = getattr(model.electrolyte.switches, parts[2])
    name = value if isinstance(value, str) else value.model
    return bool(name == NO_STERIC_MODEL)


def in_force(term: KernelTerm, model: CoupledModel) -> bool:
    """Return whether a term is in force on ``model``: its switches true, its correction on."""
    dropped = {name.strip() for name in os.environ.get(DROP_VARIABLE, "").split(",")}
    if term.name in dropped:
        return False
    display = term.display
    if display is None:
        return True
    if not all(bool(getattr(model, switch)) for switch in display.switches):
        return False
    return display.correction is None or not _leaf_is_none(model, display.correction)


def _region(slot: Slot, context: Context) -> Expression | None:
    if slot.domain == "omega":
        return None
    if slot.domain == "fluid":
        return context.fluid
    return context.surface_region


def compose_integrals(
    terms: Sequence[KernelTerm], slots: Sequence[Slot], context: Context
) -> list[tuple[str, IntegralTerm]]:
    """Return one integral per slot with a contribution, in the slots' order, by slot name."""
    integrals: list[tuple[str, IntegralTerm]] = []
    for slot in slots:
        at_hand = context.at(slot.species, _field(context, slot.species))
        parts = [
            built
            for term in terms
            for contribution in term.contributions
            if contribution.slot == slot.family
            and (built := contribution.build(at_hand)) is not None
        ]
        if not parts:
            continue
        total = parts[0]
        for part in parts[1:]:
            total = total + part
        integrand = slot.close(total, at_hand)
        options: dict[str, Option] = {}
        region = _region(slot, context)
        if region is not None:
            options["definedon"] = region
        if slot.kind == "surface":
            integral = context.measures.surface(
                integrand, singular=slot.singular, extra_order=slot.extra_order, **options
            )
        else:
            integral = context.measures.volume(
                integrand,
                singular=slot.singular,
                extra_order=slot.extra_order,
                rule_order=slot.rule_order,
                **options,
            )
        integrals.append((slot.name, integral))
    return integrals


def compose(terms: Sequence[KernelTerm], slots: Sequence[Slot], context: Context) -> IntegralTerm:
    """Return the residual: the sum over the slots, in order, of one integral each."""
    integrals = compose_integrals(terms, slots, context)
    if not integrals:
        raise ValueError("no term in force contributes to any slot")
    residual = integrals[0][1]
    for _, integral in integrals[1:]:
        residual = residual + integral
    return residual


def _field(context: Context, species: str | None) -> str | None:
    return None if species is None else f"c_{species}"


def _times_test(total: Expression, context: Context, field: str) -> Expression:
    return total * context.tests[field]


def _grad_test(field: str | None) -> Closer:
    def close(total: Expression, context: Context) -> Expression:
        import ngsolve as ngs

        name = field if field is not None else context.require_field()
        return total * ngs.grad(context.tests[name])

    return close


def _negated_flux(total: Expression, context: Context) -> Expression:
    import ngsolve as ngs

    return (-total) * ngs.grad(context.tests[context.require_field()])


def _identity(total: Expression, context: Context) -> Expression:
    del context
    return total


def _test_of(field: str) -> Closer:
    def close(total: Expression, context: Context) -> Expression:
        return _times_test(total, context, field)

    return close


def _strain_of_test(total: Expression, context: Context) -> Expression:
    import ngsolve as ngs

    return ngs.InnerProduct(total, strain_rate(context.tests[VELOCITY]))


def _radial_test(total: Expression, context: Context) -> Expression:
    return total * context.tests[VELOCITY][0]


def _divergence_of_test(total: Expression, context: Context) -> Expression:
    return total * axisymmetric_divergence(context.tests[VELOCITY], context.measures)


def _continuity_test(total: Expression, context: Context) -> Expression:
    return -context.tests[PRESSURE] * total


def _velocity_test(total: Expression, context: Context) -> Expression:
    import ngsolve as ngs

    return ngs.InnerProduct(total, context.tests[VELOCITY])


def _force_on_test(total: Expression, context: Context) -> Expression:
    import ngsolve as ngs

    return -ngs.InnerProduct(total, context.tests[VELOCITY])


def coupled_slots(context: Context, species: Sequence[str], fields: Sequence[str]) -> list[Slot]:
    """Return today's integrals of the coupled residual as slots, in today's order."""
    rule = context.fixed_charge.rule_order if context.fixed_charge is not None else None
    slots = [
        Slot("poisson.stiffness", POTENTIAL, "volume", "omega", _grad_test(POTENTIAL)),
        Slot("poisson.mobile_charge", POTENTIAL, "volume", "fluid", _test_of(POTENTIAL)),
        Slot(
            "poisson.fixed_charge",
            POTENTIAL,
            "volume",
            "omega",
            _test_of(POTENTIAL),
            rule_order=rule,
        ),
        Slot("poisson.surface_charge", POTENTIAL, "surface", "surface_charge", _test_of(POTENTIAL)),
    ]
    for name in species:
        field = f"c_{name}"
        slots += [
            Slot("flux", field, "volume", "fluid", _negated_flux, species=name),
            Slot(
                "streamline",
                field,
                "volume",
                "fluid",
                _identity,
                extra_order=STREAMLINE_BONUS_ORDER,
                species=name,
            ),
            Slot(
                "crosswind",
                field,
                "volume",
                "fluid",
                _identity,
                extra_order=CROSSWIND_BONUS_ORDER,
                species=name,
            ),
        ]
    slots += [
        Slot("momentum.viscous", VELOCITY, "volume", "fluid", _strain_of_test),
        Slot("momentum.hoop", VELOCITY, "volume", "fluid", _radial_test, singular=True),
        Slot("momentum.pressure", VELOCITY, "volume", "fluid", _divergence_of_test, singular=True),
        Slot("continuity", PRESSURE, "volume", "fluid", _continuity_test, singular=True),
        Slot("momentum.inertia", VELOCITY, "volume", "fluid", _velocity_test),
        Slot("momentum.body_force", VELOCITY, "volume", "fluid", _force_on_test),
        Slot("constraint", PRESSURE_MEAN, "volume", "fluid", _identity),
        Slot("momentum.dielectric_force", VELOCITY, "volume", "fluid", _force_on_test),
        Slot(
            "flow.gls_momentum",
            VELOCITY,
            "volume",
            "fluid",
            _identity,
            extra_order=FLOW_BONUS_ORDER,
        ),
        Slot(
            "flow.gls_pressure",
            PRESSURE,
            "volume",
            "fluid",
            _identity,
            extra_order=FLOW_BONUS_ORDER,
        ),
        Slot(
            "flow.grad_div",
            VELOCITY,
            "volume",
            "fluid",
            _identity,
            extra_order=FLOW_BONUS_ORDER,
            singular=True,
        ),
    ]
    slots += [
        Slot(
            f"source.{field}",
            field,
            "volume",
            "omega" if field == POTENTIAL else "fluid",
            _test_of(field),
        )
        for field in fields
        if context.sources is not None and field in context.sources
    ]
    return slots


def _display(name: str) -> Term:
    for term in EPNP_NS_TERMS:
        if term.name == name:
            return term
    raise KeyError(f"no display term {name!r} in EPNP_NS_TERMS")


def _permittivity_flux(context: Context) -> Expression:
    import ngsolve as ngs

    return context.permittivity * ngs.grad(context.trials[POTENTIAL])


def _mobile_charge(context: Context) -> Expression:
    coefficients = context.coefficients
    return -(coefficients.screening * coefficients.ionic_charge_density())


def _fixed_charge(context: Context) -> Expression | None:
    return None if context.fixed_charge is None else -context.fixed_charge.density


def _surface_charge(context: Context) -> Expression | None:
    return None if context.surface_charge is None else -1.0 * context.surface_charge


def _diffusion_migration(context: Context) -> Expression:
    import ngsolve as ngs

    species = context.require_species()
    coefficients = context.coefficients
    ion = coefficients.electrolyte.ion(species)
    concentration = context.variables.values[species]
    bracket = coefficients.diffusivity(species) * context.variables.gradients[species]
    return bracket + float(ion.valence) * coefficients.mobility(species) * concentration * ngs.grad(
        context.trials[POTENTIAL]
    )


def _steric(context: Context) -> Expression | None:
    form = context.model.steric_form
    if form is None:
        return None
    species = context.require_species()
    coefficients = context.coefficients
    concentration = context.variables.values[species]
    return (
        coefficients.diffusivity(species)
        * concentration
        * form(context.variables, coefficients, species)
    )


def _decrement(context: Context) -> Expression:
    species = context.require_species()
    coefficients = context.coefficients
    concentration = context.variables.values[species]
    return (
        coefficients.diffusivity(species)
        * concentration
        * excess_potential_gradient(
            species,
            coefficients=coefficients,
            variables=context.variables,
            potential=context.trials[POTENTIAL],
            solid=context.solid,
        )
    )


def _advection(context: Context) -> Expression:
    species = context.require_species()
    concentration = context.variables.values[species]
    return -(context.coefficients.peclet * context.trials[VELOCITY] * concentration)


def _viscous_stress(context: Context) -> Expression:
    return 2.0 * context.coefficients.viscosity() * strain_rate(context.trials[VELOCITY])


def _hoop(context: Context) -> Expression | None:
    import ngsolve as ngs

    if not context.measures.is_axisymmetric:
        return None
    velocity = context.trials[VELOCITY]
    return 2.0 * context.coefficients.viscosity() * velocity[0] / (ngs.x * ngs.x)


def _pressure(context: Context) -> Expression:
    return -context.trials[PRESSURE]


def _continuity(context: Context) -> Expression:
    divergence = axisymmetric_divergence(context.trials[VELOCITY], context.measures)
    density = context.density
    return divergence if density is None else density * divergence


def _inertia(context: Context) -> Expression:
    import ngsolve as ngs

    velocity = context.trials[VELOCITY]
    density = context.density
    convective = ngs.grad(velocity) * velocity
    return context.coefficients.reynolds * (1.0 if density is None else density) * convective


def ionic_force(coefficients: NondimensionalCoefficients, potential: Expression) -> Expression:
    """Return the ionic body force density ``f = -S (sum_i z_i c~_i) grad(phi~)``, written once."""
    import ngsolve as ngs

    return -coefficients.screening * coefficients.ionic_charge_density() * ngs.grad(potential)


def dielectric_force(
    coefficients: NondimensionalCoefficients,
    variables: ConcentrationVariables,
    potential: Expression,
    solid: SolidBlend | None,
) -> Expression:
    """Return PHY-23's force density ``-1/2 |grad phi~|^2 grad(eps~_r)``, written once."""
    import ngsolve as ngs

    field = ngs.grad(potential)
    return -0.5 * (field * field) * permittivity_gradient(coefficients, variables, solid=solid)


def _ionic_force(context: Context) -> Expression:
    return ionic_force(context.coefficients, context.trials[POTENTIAL])


def _dielectric_force(context: Context) -> Expression:
    return dielectric_force(
        context.coefficients, context.variables, context.trials[POTENTIAL], context.solid
    )


_NERNST_PLANCK = "Nernst\N{EN DASH}Planck"

COUPLED_TERMS: tuple[KernelTerm, ...] = (
    KernelTerm(
        "Poisson",
        (
            Contribution("poisson.stiffness", _permittivity_flux),
            Contribution("poisson.mobile_charge", _mobile_charge),
            Contribution("poisson.fixed_charge", _fixed_charge),
            Contribution("poisson.surface_charge", _surface_charge),
        ),
        _display("Poisson"),
    ),
    KernelTerm(
        _NERNST_PLANCK,
        (Contribution("flux", _diffusion_migration),),
        _display(_NERNST_PLANCK),
    ),
    KernelTerm("Steric flux", (Contribution("flux", _steric),), _display("Steric flux")),
    KernelTerm("Advection", (Contribution("flux", _advection),), _display("Advection")),
    KernelTerm(
        "Dielectric decrement",
        (Contribution("flux", _decrement),),
        _display("Dielectric decrement"),
    ),
    KernelTerm(
        "Momentum",
        (
            Contribution("momentum.viscous", _viscous_stress),
            Contribution("momentum.hoop", _hoop),
            Contribution("momentum.pressure", _pressure),
        ),
        _display("Momentum"),
    ),
    KernelTerm("Inertia", (Contribution("momentum.inertia", _inertia),), _display("Inertia")),
    KernelTerm(
        "Velocity continuity",
        (Contribution("continuity", _continuity),),
        _display("Velocity continuity"),
    ),
    KernelTerm("Variable density", (), _display("Variable density")),
    KernelTerm(
        "Body force", (Contribution("momentum.body_force", _ionic_force),), _display("Body force")
    ),
    KernelTerm(
        "Dielectric-gradient force",
        (Contribution("momentum.dielectric_force", _dielectric_force),),
        _display("Dielectric-gradient force"),
    ),
    KernelTerm("Corrections", (), _display("Corrections")),
)
"""The coupled model's terms, each wrapping its display term of ``EPNP_NS_TERMS``."""

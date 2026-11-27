"""The kernel's records: terms add contributions to slots, and each slot is integrated once."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Literal

from nanopnp.core.typing import Expression, IntegralTerm, Option
from nanopnp.materials.fields import SolidBlend
from nanopnp.numerics.measures import FixedCharge, Measures
from nanopnp.physics.coefficients import NondimensionalCoefficients
from nanopnp.physics.operators import Geometry, Operators
from nanopnp.physics.terms import Term

if TYPE_CHECKING:
    from nanopnp.physics.nernst_planck import ConcentrationVariables, StericForm
    from nanopnp.physics.stabilisation import StabilisationModel

__all__ = [
    "FLUX",
    "FORCE",
    "Context",
    "Contribution",
    "Domain",
    "Inputs",
    "KernelTerm",
    "Side",
    "Slot",
    "compose",
    "contributions",
    "force_density",
    "integrals",
    "integrand",
    "wind",
    "wind_text",
]

FLUX = "flux"
"""The family of a species' flux slot, to which each drift adds ``c~_i b``."""

FORCE = "momentum.force"
"""The family of the momentum slot to which each force density adds ``f``."""

Domain = Literal["omega", "fluid", "surface"]


@dataclass(frozen=True)
class Side:
    """One side of an assembly, trial or lagged: the fields and what is built from them.

    Parameters
    ----------
    functions
        Each solved field's function, by field name.
    density
        ``rho~`` where the variable density is in force; None holds ``rho~ = 1``.
    """

    functions: Mapping[str, Expression]
    variables: ConcentrationVariables
    coefficients: NondimensionalCoefficients
    density: Expression | None = None


@dataclass(frozen=True)
class Inputs:
    """What an assembly is given beside the fields.

    Parameters
    ----------
    permittivity
        ``eps~_r`` over all of Omega, on the trial side.
    solid
        The blend's solid side where a solid fraction is supplied and PHY-23 is in force.
    surface_region
        The boundary the surface charge is applied to.
    sources
        A manufactured source per field, by field name.
    """

    permittivity: Expression | None = None
    solid: SolidBlend | None = None
    fixed_charge: FixedCharge | None = None
    surface_charge: Expression | None = None
    surface_region: Expression | None = None
    sources: Mapping[str, Expression] = field(default_factory=dict)


@dataclass(frozen=True)
class Context:
    """What a contribution reads at one assembly.

    Parameters
    ----------
    fluid
        The region the fluid's equations are posed on.
    lagged
        The side every stabilisation parameter is read from: the solve state, else the trial side.
    tests
        Each field's test function, by field name.
    terms
        The terms of the assembly at hand, which the readers sum over.
    species
        The species of the slot at hand, or None.
    """

    ops: Operators
    geometry: Geometry
    measures: Measures
    fluid: Expression
    trial: Side
    lagged: Side
    tests: Mapping[str, Expression]
    inputs: Inputs
    steric: StericForm | None
    stabilisation: StabilisationModel
    terms: tuple[KernelTerm, ...] = ()
    species: str | None = None

    def require_species(self) -> str:
        """Return the species at hand; RuntimeError on a slot that has none."""
        if self.species is None:
            raise RuntimeError("a per-species contribution was built for a slot with no species")
        return self.species


Build = Callable[[Context], Expression | None]
Close = Callable[[Expression, Context], Expression]
Drift = Callable[[Context, Side, str], Expression | None]
Force = Callable[[Context, Side], Expression | None]


@dataclass(frozen=True)
class Contribution:
    """An expression a term adds to one slot family; None where it adds nothing."""

    slot: str
    build: Build


@dataclass(frozen=True)
class KernelTerm:
    """One term of a model: its display record and what it adds to the slots.

    Parameters
    ----------
    clause
        The PHY or NUM clause the term is written from.
    display
        The display record of the model's equations, or None for a term the display lists not.
    drift
        A flux term's drift ``b``, stated once: the flux slot takes ``c~_i b`` and every reader
        sums it into the wind.
    drift_text
        The drift as the manifest's Peclet expression writes it.
    force
        A force term's density ``f``, stated once: the momentum slot takes it and every reader
        sums it into the force.
    """

    name: str
    clause: str
    display: Term | None = None
    contributions: tuple[Contribution, ...] = ()
    drift: Drift | None = None
    drift_text: str = ""
    force: Force | None = None

    @property
    def slots(self) -> tuple[str, ...]:
        """Return the slot families the term adds to, in order, its drift's and force's included."""
        families = [contribution.slot for contribution in self.contributions]
        if self.drift is not None:
            families.append(FLUX)
        if self.force is not None:
            families.append(FORCE)
        return tuple(dict.fromkeys(families))


@dataclass(frozen=True)
class Slot:
    """One integral of one equation: its test field, domain, closing and quadrature rule.

    Parameters
    ----------
    family
        The name a contribution addresses; a per-species slot shares it across the species.
    test
        The field whose test function the slot takes.
    close
        Turns the summed contributions into the integrand; the identity where each contribution
        carries its own test function.
    singular
        Whether the integrand carries ``1/r``, which takes NUM-07's minimum order.
    rule_order
        A fixed rule for the slot, in place of the estimated one.
    """

    family: str
    test: str
    domain: Domain
    close: Close
    kind: Literal["volume", "surface"] = "volume"
    singular: bool = False
    extra_order: int = 0
    rule_order: int | None = None
    species: str | None = None

    @property
    def name(self) -> str:
        """Return the slot's name: its family, and its species where it has one."""
        return self.family if self.species is None else f"{self.family}:{self.species}"


def _total(parts: Sequence[Expression]) -> Expression | None:
    if not parts:
        return None
    total = parts[0]
    for part in parts[1:]:
        total = total + part
    return total


def _bound(terms: Sequence[KernelTerm], slot: Slot, context: Context) -> Context:
    return replace(context, terms=tuple(terms), species=slot.species)


def _parts(term: KernelTerm, family: str, context: Context) -> list[Expression]:
    parts = [
        built
        for contribution in term.contributions
        if contribution.slot == family and (built := contribution.build(context)) is not None
    ]
    if family == FLUX and term.drift is not None:
        species = context.require_species()
        drift = term.drift(context, context.trial, species)
        if drift is not None:
            parts.append(context.trial.variables.values[species] * drift)
    if family == FORCE and term.force is not None:
        density = term.force(context, context.trial)
        if density is not None:
            parts.append(density)
    return parts


def contributions(terms: Sequence[KernelTerm], slot: Slot, context: Context) -> Expression | None:
    """Return the sum of every contribution to ``slot`` before its closing; None if none adds."""
    bound = _bound(terms, slot, context)
    return _total([part for term in terms for part in _parts(term, slot.family, bound)])


def integrand(terms: Sequence[KernelTerm], slot: Slot, context: Context) -> Expression | None:
    """Return ``slot``'s integrand, its contributions summed and closed; None if none adds."""
    total = contributions(terms, slot, context)
    if total is None:
        return None
    return slot.close(total, _bound(terms, slot, context))


def _region(slot: Slot, context: Context) -> Expression | None:
    if slot.domain == "omega":
        return None
    if slot.domain == "fluid":
        return context.fluid
    if context.inputs.surface_region is None:
        raise ValueError(f"the slot {slot.name!r} is on the charged boundary, and none is given")
    return context.inputs.surface_region


def integrals(
    terms: Sequence[KernelTerm], slots: Sequence[Slot], context: Context
) -> list[tuple[str, IntegralTerm]]:
    """Return one integral per slot that a term adds to, in the slots' order, with its name."""
    named: list[tuple[str, IntegralTerm]] = []
    for slot in slots:
        closed = integrand(terms, slot, context)
        if closed is None:
            continue
        options: dict[str, Option] = {}
        region = _region(slot, context)
        if region is not None:
            options["definedon"] = region
        measures = context.measures
        if slot.kind == "surface":
            integral = measures.surface(
                closed, singular=slot.singular, extra_order=slot.extra_order, **options
            )
        else:
            integral = measures.volume(
                closed,
                singular=slot.singular,
                extra_order=slot.extra_order,
                rule_order=slot.rule_order,
                **options,
            )
        named.append((slot.name, integral))
    return named


def compose(terms: Sequence[KernelTerm], slots: Sequence[Slot], context: Context) -> IntegralTerm:
    """Return the residual: the sum, in the slots' order, of one integral per slot."""
    named = integrals(terms, slots, context)
    if not named:
        raise ValueError("no term in force adds to any slot")
    residual = named[0][1]
    for _, integral in named[1:]:
        residual = residual + integral
    return residual


def wind(context: Context, side: Side, species: str) -> Expression | None:
    """Return ``b~_i``, the sum of the drifts of ``context.terms`` on ``side``; None if none."""
    parts = [
        drift
        for term in context.terms
        if term.drift is not None and (drift := term.drift(context, side, species)) is not None
    ]
    return _total(parts)


def force_density(context: Context, side: Side) -> Expression | None:
    """Return ``f``, the sum of the force densities of ``context.terms`` on ``side``, or None."""
    parts = [
        density
        for term in context.terms
        if term.force is not None and (density := term.force(context, side)) is not None
    ]
    return _total(parts)


def wind_text(terms: Sequence[KernelTerm]) -> str:
    """Return the wind as the Peclet expression writes it: each drift's text, joined by signs."""
    text = ""
    for term in terms:
        part = term.drift_text
        if not part:
            continue
        if not text:
            text = part
        elif part.startswith("-"):
            text += f" - {part[1:].lstrip()}"
        else:
            text += f" + {part}"
    return text

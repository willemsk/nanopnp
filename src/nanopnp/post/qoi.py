"""Quantities of interest: current, transport number, EOF, rectification (FR-23)."""

from __future__ import annotations

import logging
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from nanopnp.core.typing import AssembledForm, Expression, GridFunction, Option
from nanopnp.io.vocabulary import (
    POTENTIAL,
    VELOCITY,
)
from nanopnp.numerics.gates import FieldSampler
from nanopnp.numerics.measures import Measures
from nanopnp.physics.coefficients import species_concentrations_SI
from nanopnp.physics.models import (
    ModelSolution,
    TransportModel,
    concentration_field_name,
    transport_model,
)
from nanopnp.physics.nernst_planck import species_flux
from nanopnp.post.reaction_flux import boundary_reaction_flux

__all__ = [
    "ROUTE_AGREEMENT_TOLERANCE",
    "TWO_PI",
    "QuantitiesOfInterest",
    "RouteAgreement",
    "RouteDisagreementError",
    "cis_referenced_bias",
    "conductance",
    "extract",
    "indicator_currents",
    "indicator_eof",
    "reaction_flux_currents",
    "rectification",
    "rectification_ratio",
    "report_clamp_activations",
    "summarise",
    "total_current",
    "transport_number",
]

logger = logging.getLogger(__name__)

TWO_PI = 2.0 * math.pi

ROUTE_AGREEMENT_TOLERANCE = 1.0e-3


class RouteDisagreementError(RuntimeError): ...


def _coupled(solution: ModelSolution) -> TransportModel:
    return transport_model(solution)


def _check_indicator_matches(
    solution: ModelSolution, model: TransportModel, indicator: GridFunction
) -> None:
    if indicator.space.mesh is not solution.space.mesh:
        raise ValueError(
            "the indicator was built on a different mesh from the solution; grad(psi) would "
            "then be evaluated outside its own domain, which returns a plausible number "
            "rather than raising"
        )
    order = int(indicator.space.globalorder)
    if order != model.order:
        raise ValueError(
            f"the indicator is order {order} but {model.name!r} solves at order {model.order}; "
            "grad(psi) would be represented in a coarser space than the flux it is integrated "
            "against, and the two routes of NUM-26 would no longer test the same discretisation"
        )


def _functions(solution: ModelSolution) -> dict[str, Expression]:
    return {field.name: solution.component(field.name) for field in solution.model.fields}


def indicator_currents(
    solution: ModelSolution,
    measures: Measures,
    indicator: GridFunction,
    *,
    wall_distance_nm: Expression | None = None,
    stabilisation: Mapping[str, float] | None = None,
) -> dict[str, float]:
    import ngsolve as ngs

    model = _coupled(solution)
    _check_indicator_matches(solution, model, indicator)
    mesh = solution.space.mesh
    distance = solution.wall_distance_nm if wall_distance_nm is None else wall_distance_nm
    functions = _functions(solution)
    variables = model.concentration_variables(functions)
    coefficients = model.coefficients(variables, distance)
    velocity = functions[VELOCITY] if model.flow else None
    gradient = ngs.grad(indicator)
    scale = TWO_PI * model.scales.current_A

    if stabilisation is None:
        stabilisation = stabilisation_currents(
            solution, measures, indicator, wall_distance_nm=distance
        )
    currents: dict[str, float] = {}
    for name in model.species:
        flux = species_flux(
            name,
            coefficients=coefficients,
            variables=variables,
            potential=functions[POTENTIAL],
            velocity=velocity,
            steric=model.steric,
            dielectric_gradient=model.dielectric_gradient_forces,
        )
        integral = measures.integrate(
            flux * gradient,
            mesh,
            definedon=mesh.Materials(model.fluid),
            what=f"the indicator flux of {name!r}",
        )
        valence = float(model.electrolyte.ion(name).valence)
        # NUM-26: the reaction flux carries the stabilisation term, so this route must.
        currents[name] = valence * scale * integral + stabilisation[name]
    logger.debug("indicator currents (A): %s", currents)
    return currents


def stabilisation_currents(
    solution: ModelSolution,
    measures: Measures,
    indicator: GridFunction,
    *,
    wall_distance_nm: Expression | None = None,
) -> dict[str, float]:
    model = _coupled(solution)
    _check_indicator_matches(solution, model, indicator)
    mesh = solution.space.mesh
    distance = solution.wall_distance_nm if wall_distance_nm is None else wall_distance_nm
    stabilisation = model.stabilisation_model
    scale = TWO_PI * model.scales.current_A
    states = model.transport_states(_functions(solution), distance)

    contributions: dict[str, float] = {}
    for name, state in states.items():
        valence = float(model.electrolyte.ion(name).valence)
        contributions[name] = (
            valence
            * scale
            * stabilisation.indicator_term(
                measures,
                mesh,
                state=state,
                indicator=indicator,
                definedon=mesh.Materials(model.fluid),
            )
        )
    logger.debug("stabilisation currents in %r (A): %s", stabilisation.name, contributions)
    return contributions


def indicator_eof(solution: ModelSolution, measures: Measures, indicator: GridFunction) -> float:
    import ngsolve as ngs

    model = _coupled(solution)
    if not model.flow:
        raise TypeError(
            f"{model.name!r} solves no flow block, so it has no Q_EOF to report; enable the "
            "flow or read the current only"
        )
    _check_indicator_matches(solution, model, indicator)
    mesh = solution.space.mesh
    integral = measures.integrate(
        solution.velocity * ngs.grad(indicator),
        mesh,
        definedon=mesh.Materials(model.fluid),
        what="the indicator volumetric flow",
    )
    return TWO_PI * model.scales.volumetric_flow_m3_s * integral


def reaction_flux_currents(
    solution: ModelSolution,
    boundary: str = "cis",
    *,
    load_form: AssembledForm | None = None,
) -> dict[str, float]:
    model = _coupled(solution)
    if solution.residual is None:
        raise ValueError(
            "this solution carries no residual form, so the NUM-25 reaction flux cannot be "
            "taken from it; solve through the model's own solve, which records it"
        )
    names = [field.name for field in model.fields]
    scale = TWO_PI * model.scales.current_A
    currents: dict[str, float] = {}
    for species in model.species:
        block = names.index(concentration_field_name(species))
        flux = boundary_reaction_flux(
            solution.residual,
            solution.state,
            boundary,
            component=block,
            load_form=load_form,
        )
        valence = float(model.electrolyte.ion(species).valence)
        currents[species] = valence * scale * flux
    logger.debug("reaction-flux currents (A) on %r: %s", boundary, currents)
    return currents


def total_current(currents: Mapping[str, float]) -> float:
    return math.fsum(currents.values())


def transport_number(currents: Mapping[str, float], cations: Iterable[str]) -> float:
    unknown = sorted(set(cations) - set(currents))
    if unknown:
        raise ValueError(
            f"no current for {', '.join(unknown)}; the currents are for "
            f"{', '.join(sorted(currents))}"
        )
    total = total_current(currents)
    if total == 0.0:
        raise ValueError("the transport number is undefined at zero total current")
    return math.fsum(currents[name] for name in cations) / total


def rectification_ratio(current_plus_A: float, current_minus_A: float) -> float:
    if current_minus_A == 0.0:
        raise ValueError("the rectification ratio is undefined at zero reverse current")
    return abs(current_plus_A) / abs(current_minus_A)


def cis_referenced_bias(bias_V: float, ground: str) -> float:
    if ground == "cis":
        return bias_V
    if ground == "trans":
        return -bias_V
    raise ValueError(f"ground={ground!r} must be 'cis' or 'trans'")


def conductance(current_A: float, bias_V: float) -> float:
    if bias_V == 0.0:
        raise ValueError("the conductance is undefined at zero bias")
    return current_A / bias_V


@dataclass(frozen=True)
class RouteAgreement:
    indicator_A: float
    reaction_A: float

    @property
    def relative_difference(self) -> float:
        if not (math.isfinite(self.indicator_A) and math.isfinite(self.reaction_A)):
            return math.inf
        scale = max(abs(self.indicator_A), abs(self.reaction_A))
        if scale == 0.0:
            return 0.0
        return abs(self.indicator_A - self.reaction_A) / scale

    def check(self, tolerance: float = ROUTE_AGREEMENT_TOLERANCE) -> None:
        difference = self.relative_difference
        # ``not <=`` so that NaN fails the gate.
        if not difference <= tolerance:
            # Referencing the reaction flux to trans negates it exactly.
            opposite = (
                "\nThe two are opposite in sign and close in magnitude, which is what "
                "referencing the NUM-25 route to the *other* electrode looks like: psi is 1 on "
                "cis, so the reaction flux has to be taken on cis too."
                if self.indicator_A * self.reaction_A < 0.0
                else ""
            )
            raise RouteDisagreementError(
                f"the NUM-24 indicator current is {self.indicator_A:.6e} A and the NUM-25 "
                f"reaction flux is {self.reaction_A:.6e} A, a relative difference of "
                f"{difference:.3e} against a declared tolerance of {tolerance:.3e}. One of "
                "the two is wrong; a difference of this size can manufacture or erase the "
                f"rectification signal (NUM-23, RSK-03){opposite}"
            )
        logger.debug("current routes agree to %.3e", difference)

    def summary(self) -> dict[str, float]:
        return {
            "indicator_A": self.indicator_A,
            "reaction_A": self.reaction_A,
            "relative_difference": self.relative_difference,
        }


def _check_species_routes(
    indicator: Mapping[str, float], reaction: Mapping[str, float], *, tolerance: float
) -> None:
    scale = abs(math.fsum(indicator.values()))
    if scale == 0.0:
        return
    for species, value in indicator.items():
        other = reaction[species]
        difference = abs(value - other) / scale
        # ``not <=`` so that a NaN route fails.
        if not difference <= tolerance:
            raise RouteDisagreementError(
                f"the two current routes disagree on {species!r}: the NUM-24 indicator gives "
                f"{value:.6e} A and the NUM-25 reaction flux {other:.6e} A, a difference of "
                f"{difference:.3e} of the total current against a declared tolerance of "
                f"{tolerance:.3e}. The totals may still agree — two per-species errors that "
                "cancel leave the current right and the NUM-27 transport number wrong"
            )


@dataclass(frozen=True)
class QuantitiesOfInterest:
    bias_V: float
    currents_A: Mapping[str, float]
    current_A: float
    transport_number: float | None
    conductance_S: float | None
    eof_m3_s: float | None
    agreement: RouteAgreement | None
    stabilisation_currents_A: Mapping[str, float] | None = None

    clamp_activations: int | None = None

    def summary(self) -> dict[str, Option]:
        record: dict[str, Option] = {
            "bias_V": self.bias_V,
            "currents_A": dict(self.currents_A),
            "current_A": self.current_A,
            "transport_number": self.transport_number,
            "conductance_S": self.conductance_S,
            "eof_m3_s": self.eof_m3_s,
            "stabilisation_currents_A": (
                None
                if self.stabilisation_currents_A is None
                else dict(self.stabilisation_currents_A)
            ),
            "clamp_activations": self.clamp_activations,
            "two_pi_included": True,
            # FR-25: a skipped NUM-26 check is a switch away from the default.
            "routes_checked": self.agreement is not None,
        }
        if self.agreement is not None:
            record["route_agreement"] = self.agreement.summary()
        return record


def extract(
    solution: ModelSolution,
    measures: Measures,
    indicator: GridFunction,
    *,
    bias_V: float,
    boundary: str = "cis",
    wall_distance_nm: Expression | None = None,
    load_form: AssembledForm | None = None,
    tolerance: float = ROUTE_AGREEMENT_TOLERANCE,
    check_routes: bool = True,
) -> QuantitiesOfInterest:
    model = _coupled(solution)
    # Measured once: it enters the currents and is also reported, as section 7.4 subtracts it.
    stabilisation = stabilisation_currents(
        solution, measures, indicator, wall_distance_nm=wall_distance_nm
    )
    currents = indicator_currents(
        solution,
        measures,
        indicator,
        wall_distance_nm=wall_distance_nm,
        stabilisation=stabilisation,
    )
    current = total_current(currents)

    # At zero bias both routes are round-off, so their relative difference is of order one.
    equilibrium = bias_V == 0.0
    agreement: RouteAgreement | None = None
    if check_routes and equilibrium:
        logger.info(
            "zero bias: the NUM-26 route check is not applied, both currents being round-off "
            "(%.3e A by the NUM-24 indicator)",
            current,
        )
    elif check_routes:
        reaction = reaction_flux_currents(solution, boundary, load_form=load_form)
        agreement = RouteAgreement(indicator_A=current, reaction_A=total_current(reaction))
        agreement.check(tolerance)
        # Two errors that cancel in the sum would pass the total and invert the transport number.
        _check_species_routes(currents, reaction, tolerance=tolerance)

    clamped = report_clamp_activations(solution, measures)

    cations = [ion.name for ion in model.electrolyte.species if ion.valence > 0]
    return QuantitiesOfInterest(
        bias_V=bias_V,
        currents_A=currents,
        current_A=current,
        transport_number=None if equilibrium else transport_number(currents, cations),
        conductance_S=None if equilibrium else conductance(current, bias_V),
        eof_m3_s=indicator_eof(solution, measures, indicator) if model.flow else None,
        agreement=agreement,
        stabilisation_currents_A=stabilisation,
        clamp_activations=clamped,
    )


def report_clamp_activations(solution: ModelSolution, measures: Measures) -> int:
    model = _coupled(solution)
    sampler = FieldSampler.shared(
        solution.space.mesh, coordinates=measures.coordinate_names, materials=model.fluid
    )
    variables = model.concentration_variables(_functions(solution))
    concentrations_SI = species_concentrations_SI(model.scales, variables.values)
    sampled = [sampler.evaluate(concentrations_SI[name]) for name in model.species]
    coordinates = [(float(point[0]), float(point[1])) for point in sampler.points]
    return model.electrolyte.report_clamp_activations(sampled, coordinates=coordinates)


def rectification(forward: QuantitiesOfInterest, reverse: QuantitiesOfInterest) -> float:
    if not forward.bias_V > 0.0:
        raise ValueError(
            f"'forward' must be the positive bias: RR is |I(+V)|/|I(-V)|, so a swapped pair "
            f"returns the reciprocal and inverts the rectification direction with no other "
            f"symptom. Got forward={forward.bias_V} V and reverse={reverse.bias_V} V"
        )
    if not forward.bias_V * reverse.bias_V < 0.0:
        raise ValueError(
            f"a rectification ratio compares opposite biases, got {forward.bias_V} V and "
            f"{reverse.bias_V} V"
        )
    return rectification_ratio(forward.current_A, reverse.current_A)


def summarise(quantities: Sequence[QuantitiesOfInterest]) -> list[dict[str, Option]]:
    return [point.summary() for point in quantities]

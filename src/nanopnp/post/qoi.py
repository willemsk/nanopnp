"""Quantities of interest: current, transport number, EOF, rectification (FR-23).

Two routes to the ionic current are implemented and neither is optional.

* **NUM-24, the domain-indicator form.** With ``psi`` a smooth function equal to 1
  in the cis reservoir and 0 in the trans reservoir,
  ``int_Omega J_i.grad(psi) r dr dz`` is, by the divergence theorem and
  ``div J_i = 0``, exactly the flux of species ``i`` out through the cis cap. It
  is a volume integral over a band rather than a line integral across one
  section, which is what makes it independent of where the section is taken.
* **NUM-25, the variational reaction flux**, in :mod:`nanopnp.post.reaction_flux`.

They are not two spellings of one calculation. NUM-23 forbids the third route —
integrating the continuous-Galerkin flux over an interior cross-section — because
a CG flux is not pointwise conservative and that integral drifts between sections
by amounts that can exceed the rectification signal at low bias (RSK-03). Having
two independent routes is what turns that risk into a test: NUM-26 asserts their
agreement in continuous integration, against the tolerance declared as
:data:`ROUTE_AGREEMENT_TOLERANCE`.

The ``2 pi`` convention (NUM-27's NOTE)
---------------------------------------
:class:`~nanopnp.physics.measures.Measures` writes every axisymmetric integral as
``int f r dr dz``, the ``2 pi`` having cancelled from both sides of the weak form.
Every integral in this project therefore arrives here short of that factor, and
**this module restores it, once**. Both routes inherit the same convention, so
their *agreement* would hold either way; their SI values would not. Every number
this module returns is a true three-dimensional quantity — an ampere is an
ampere, a cubic metre per second is a volumetric flow through the whole annulus.

Sign convention
---------------
``psi`` increases towards cis, which is at ``+z``. The current is referenced to
the grounded cis electrode (SPECIFICATION.md section 5.2.2: ``phi = 0`` on
``Gamma_w,c``, ``phi = V_bias`` on ``Gamma_w,t``), so a positive current is one
flowing trans to cis, in ``+z``, and an uncharged ohmic pore has
``G = I / V_bias > 0`` at either sign of the bias. Referencing the trans
electrode instead flips every current and would make ``G`` negative; the two
differ only by that choice, and VER-17 is what pins it down.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from nanopnp.core.typing import AssembledForm, Expression, GridFunction, Option
from nanopnp.physics.coefficients import species_concentrations_SI
from nanopnp.physics.measures import Measures
from nanopnp.physics.models import (
    POTENTIAL,
    VELOCITY,
    CoupledModel,
    ModelSolution,
    concentration_field_name,
)
from nanopnp.physics.nernst_planck import species_flux
from nanopnp.post.reaction_flux import boundary_reaction_flux
from nanopnp.solve.gates import FieldSampler

__all__ = [
    "ROUTE_AGREEMENT_TOLERANCE",
    "TWO_PI",
    "QuantitiesOfInterest",
    "RouteAgreement",
    "RouteDisagreementError",
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
"""The azimuthal Jacobian ``Measures`` cancels from the weak form.

Restored here and nowhere else, so that there is exactly one place in the
package where a dimensionless ``int f r dr dz`` becomes an SI quantity.
"""

ROUTE_AGREEMENT_TOLERANCE = 1.0e-3
"""The declared tolerance of NUM-26, as a relative difference.

Chosen against what the agreement protects: the rectification signal. At the
lowest bias of the FR-17 envelope, +/-50 mV, a charged pore's ``|RR - 1|`` is of
order 1e-1, and a current route wrong by more than a tenth of a per cent would
be capable of manufacturing or erasing that signal. The two routes are
algebraically the same integral — ``psi`` differs from the NUM-25 boundary
indicator by a function that vanishes on both electrodes, hence by a legitimate
test function of the converged residual — so what this tolerance actually bounds
is the difference in their quadrature and the residual Newton left behind. It is
therefore a ceiling on a bug, not a numerical budget to be spent.
"""


class RouteDisagreementError(RuntimeError):
    """The two current routes of NUM-24 and NUM-25 disagree beyond the tolerance.

    One of them is wrong, and there is no way to tell which from the numbers
    alone, so no current is reported (QR-12).
    """


def _coupled(solution: ModelSolution) -> CoupledModel:
    """Return the solution's model, insisting it solves for ions.

    Raises
    ------
    TypeError
        If the model has no ionic species, which every quantity here needs.
    """
    model = solution.model
    if not isinstance(model, CoupledModel):
        raise TypeError(
            f"{model.name!r} solves no ionic species, so it carries no current; the "
            "quantities of interest of NUM-27 need a model of the epnp-ns family"
        )
    return model


def _check_indicator_matches(
    solution: ModelSolution, model: CoupledModel, indicator: GridFunction
) -> None:
    """Reject a ``psi`` that was not built for this solution (QR-12).

    Both failures are silent. A ``psi`` on another mesh makes ``grad(psi)`` a
    point evaluation outside its own domain, which returns a plausible number
    rather than raising — the same reason
    :func:`nanopnp.solve.continuation.transfer` refuses to cross a mesh. A
    ``psi`` at a lower element order represents ``grad(psi)`` in a coarser space
    than the flux it is integrated against, so the two no longer test the same
    discretisation and the NUM-26 agreement is measured on the wrong pair.

    Raises
    ------
    ValueError
        Naming which of the two does not match.
    """
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
    """Return the solved fields keyed by name, in the model's own variables.

    The *raw* components, not :meth:`ModelSolution.concentration`: the flux is
    rebuilt with :meth:`CoupledModel.concentration_variables`, which applies the
    NUM-02 log branch itself. Unwrapping here as well would exponentiate twice.
    """
    return {field.name: solution.component(field.name) for field in solution.model.fields}


def indicator_currents(
    solution: ModelSolution,
    measures: Measures,
    indicator: GridFunction,
    *,
    wall_distance_nm: Expression | None = None,
) -> dict[str, float]:
    """Return the per-species current in amperes by the NUM-24 indicator form.

    ``I_i = 2 pi F z_i S_I int_Omega J~_i . grad(psi) r dr dz`` with
    ``S_I = F D_0 c_0 a`` the current scale of NUM-09.

    The flux is rebuilt from the converged state through the model's own public
    seams — :meth:`~nanopnp.physics.models.CoupledModel.concentration_variables`,
    :meth:`~nanopnp.physics.models.CoupledModel.coefficients` and
    :func:`~nanopnp.physics.nernst_planck.species_flux` — so that it is the same
    expression the residual was assembled from, correction for correction.

    Parameters
    ----------
    solution
        A converged solution of a coupled model.
    measures
        The symmetry and quadrature policy the model was solved with.
    indicator
        ``psi``, from :func:`nanopnp.post.indicator.axial_indicator`.
    wall_distance_nm
        The PHY-02 distance field. Defaults to the one the solve recorded on the
        solution, which is the whole reason it is recorded: rebuilding the flux
        with a *different* distance field silently evaluates a different model.

    Returns
    -------
    dict[str, float]
        Current per species, in amperes.

    Raises
    ------
    ValueError
        If the indicator was not built on this solution's mesh at the model's
        element order; see :func:`_check_indicator_matches`.
    """
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
        currents[name] = valence * scale * integral
    logger.debug("indicator currents (A): %s", currents)
    return currents


def indicator_eof(solution: ModelSolution, measures: Measures, indicator: GridFunction) -> float:
    """Return the electro-osmotic flow rate in m^3/s by the NUM-24 indicator form.

    ``Q_EOF = 2 pi u_0 a^2 int_Omega u~ . grad(psi) r dr dz``. Positive is trans
    to cis, the same convention as the current.

    Raises
    ------
    TypeError
        If the model has no flow block, where the quantity does not exist. It is
        not reported as zero: a ``pnp`` run has not computed a vanishing flow, it
        has not modelled one.
    """
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
    """Return the per-species current in amperes by the NUM-25 reaction flux.

    The residual assembled by the solve is evaluated against a test function
    equal to 1 on ``boundary``, block by block, so each species' own equation is
    picked out rather than the sum over all of them.

    Parameters
    ----------
    solution
        A converged solution carrying its residual form. A solve produces one;
        a hand-built :class:`~nanopnp.physics.models.ModelSolution` may not, and
        rebuilding the form here without the solve's ``wall_distance_nm`` would
        give a different operator and a silently wrong flux.
    boundary
        The electrode to reference the current to. ``cis`` is the ground of
        SPECIFICATION.md section 5.2.2 and the sign convention of this module.
    load_form
        The assembled load vector, if the problem has one. A physical case has
        no body source and needs none; a manufactured solution does.

    Returns
    -------
    dict[str, float]
        Current per species, in amperes.

    Raises
    ------
    ValueError
        If the solution carries no residual form.
    """
    model = _coupled(solution)
    if solution.residual is None:
        raise ValueError(
            "this solution carries no residual form, so the NUM-25 reaction flux cannot be "
            "taken from it; solve through CoupledModel.solve, which records it"
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
    """Return the total ionic current, the sum of the per-species currents."""
    return math.fsum(currents.values())


def transport_number(currents: Mapping[str, float], cations: Iterable[str]) -> float:
    """Return ``t+ = I+ / (I+ + I-)`` (NUM-27).

    Parameters
    ----------
    currents
        Per-species currents, as returned by either route.
    cations
        Names of the positively charged species. Passed in rather than inferred,
        because the sum in the numerator is over species and only the model
        knows their valences; :func:`extract` supplies them from the electrolyte.

    Raises
    ------
    ValueError
        If the total current vanishes, where the transport number is undefined,
        or if ``cations`` names a species that is not in ``currents``.
    """
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
    """Return ``RR = |I(+V)| / |I(-V)|`` (NUM-27).

    Raises
    ------
    ValueError
        If the reverse current vanishes.
    """
    if current_minus_A == 0.0:
        raise ValueError("the rectification ratio is undefined at zero reverse current")
    return abs(current_plus_A) / abs(current_minus_A)


def conductance(current_A: float, bias_V: float) -> float:
    """Return ``G = I / V_bias`` in siemens (NUM-27).

    Raises
    ------
    ValueError
        If the bias vanishes, where the chord conductance is undefined.
    """
    if bias_V == 0.0:
        raise ValueError("the conductance is undefined at zero bias")
    return current_A / bias_V


@dataclass(frozen=True)
class RouteAgreement:
    """How far apart the NUM-24 and NUM-25 currents are on one solution."""

    indicator_A: float
    reaction_A: float

    @property
    def relative_difference(self) -> float:
        """``|I_psi - I_reaction|`` over the larger magnitude, or 0 if both vanish."""
        scale = max(abs(self.indicator_A), abs(self.reaction_A))
        if scale == 0.0:
            return 0.0
        return abs(self.indicator_A - self.reaction_A) / scale

    def check(self, tolerance: float = ROUTE_AGREEMENT_TOLERANCE) -> None:
        """Assert the two routes agree (NUM-26, VER-11, QR-04).

        Raises
        ------
        RouteDisagreementError
            If they do not, naming both currents and the difference. One of them
            is wrong and the numbers cannot say which, so neither is reported.
        """
        difference = self.relative_difference
        if difference > tolerance:
            # The one disagreement with a benign cause: referencing the reaction
            # flux to ``trans`` rather than to ``cis`` negates it exactly, and
            # arriving at that through a bare "one of the two is wrong" costs an
            # afternoon.
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
        """Return the pair and their difference, for the manifest (FR-25)."""
        return {
            "indicator_A": self.indicator_A,
            "reaction_A": self.reaction_A,
            "relative_difference": self.relative_difference,
        }


def _check_species_routes(
    indicator: Mapping[str, float], reaction: Mapping[str, float], *, tolerance: float
) -> None:
    """Assert the two routes agree species by species (NUM-26, NUM-27).

    :meth:`RouteAgreement.check` compares the totals, and a total is blind to two
    per-species errors that cancel in the sum — which is exactly the shape a
    swapped species block has. The transport number is derived from the
    *per-species* currents, so such a pair leaves ``I`` right and ``t+``
    inverted, and nothing else says so.

    The difference is measured against the **total** current rather than against
    each species' own, so a species carrying almost none of it does not turn its
    own round-off into a relative difference of order one.

    Raises
    ------
    RouteDisagreementError
        Naming the species and both of its currents.
    """
    scale = abs(math.fsum(indicator.values()))
    if scale == 0.0:
        return
    for species, value in indicator.items():
        other = reaction[species]
        difference = abs(value - other) / scale
        if difference > tolerance:
            raise RouteDisagreementError(
                f"the two current routes disagree on {species!r}: the NUM-24 indicator gives "
                f"{value:.6e} A and the NUM-25 reaction flux {other:.6e} A, a difference of "
                f"{difference:.3e} of the total current against a declared tolerance of "
                f"{tolerance:.3e}. The totals may still agree — two per-species errors that "
                "cancel leave the current right and the NUM-27 transport number wrong"
            )


@dataclass(frozen=True)
class QuantitiesOfInterest:
    """The NUM-27 quantities of one converged solution, in SI units.

    Every one is derived from the same ``psi`` integrals, as NUM-27 requires, so
    a transport number and a current reported together cannot come from
    different extractions.
    """

    bias_V: float
    currents_A: Mapping[str, float]
    current_A: float
    transport_number: float
    conductance_S: float
    eof_m3_s: float | None
    agreement: RouteAgreement | None
    clamp_activations: int | None = None
    """PHY-13 clamp activations counted over this converged solution.

    ``None`` only on a record built by hand: :func:`extract` samples the
    solution on every operating point and always sets an integer. The manifest's
    Materials group distinguishes the two — "no solution was sampled" is not the
    same fact as "none was clamped" — so the distinction is carried rather than
    collapsed to zero (FR-25, section 5.3.3).
    """

    def summary(self) -> dict[str, Option]:
        """Return every quantity, for logs and the provenance manifest (FR-25)."""
        record: dict[str, Option] = {
            "bias_V": self.bias_V,
            "currents_A": dict(self.currents_A),
            "current_A": self.current_A,
            "transport_number": self.transport_number,
            "conductance_S": self.conductance_S,
            "eof_m3_s": self.eof_m3_s,
            "clamp_activations": self.clamp_activations,
            "two_pi_included": True,
            # FR-25 wants every switch set away from the validated default, and
            # skipping NUM-26 is one. Absence of the ``route_agreement`` key
            # would not say so: a hand-built record has none either.
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
    """Return every NUM-27 quantity of one converged solution, in SI units.

    The current is the NUM-24 indicator current; the NUM-25 reaction flux is
    computed alongside it and the two are checked against each other before any
    number is returned (NUM-26, QR-04). That check is not an optional diagnostic:
    it is the mechanism by which RSK-03 — a plausible, stable, publishable wrong
    current — is retired.

    Parameters
    ----------
    solution
        A converged solution of a coupled model, carrying its residual.
    measures
        The symmetry and quadrature policy the model was solved with.
    indicator
        ``psi``, from :func:`nanopnp.post.indicator.axial_indicator`.
    bias_V
        The applied bias, in volts, for the conductance.
    boundary
        The electrode the reaction-flux route is referenced to.
    wall_distance_nm
        Overrides the distance field recorded on the solution; see
        :func:`indicator_currents`.
    load_form
        The assembled load vector, if the problem has one.
    tolerance
        Route-agreement tolerance; :data:`ROUTE_AGREEMENT_TOLERANCE` by default.
    check_routes
        Whether to compute and check the second route. ``False`` skips it, for a
        sweep that has already established agreement on a representative point
        and is paying for the second assembly at every one of a thousand others.
        It is a deviation from NUM-26 and is recorded as such in the summary.
        When on, the two routes are compared both in total and species by
        species; the second comparison is what protects the transport number,
        which the total is blind to.

    Raises
    ------
    RouteDisagreementError
        If the two routes disagree beyond ``tolerance``.
    """
    model = _coupled(solution)
    currents = indicator_currents(solution, measures, indicator, wall_distance_nm=wall_distance_nm)
    current = total_current(currents)

    agreement: RouteAgreement | None = None
    if check_routes:
        reaction = reaction_flux_currents(solution, boundary, load_form=load_form)
        agreement = RouteAgreement(indicator_A=current, reaction_A=total_current(reaction))
        agreement.check(tolerance)
        # The total is not enough: the transport number below is built from the
        # per-species currents, and two errors that cancel in the sum pass the
        # check above while inverting it.
        _check_species_routes(currents, reaction, tolerance=tolerance)

    # PHY-13: a high-salt operating point may have extrapolated the concentration
    # fits past their validity range near a charged wall. The clamp that caps them
    # there is silent in the solve, so the record is emitted here, once per
    # extracted operating point, over the converged concentrations.
    clamped = report_clamp_activations(solution, measures)

    cations = [ion.name for ion in model.electrolyte.species if ion.valence > 0]
    return QuantitiesOfInterest(
        bias_V=bias_V,
        currents_A=currents,
        current_A=current,
        transport_number=transport_number(currents, cations),
        conductance_S=conductance(current, bias_V),
        eof_m3_s=indicator_eof(solution, measures, indicator) if model.flow else None,
        agreement=agreement,
        clamp_activations=clamped,
    )


def report_clamp_activations(solution: ModelSolution, measures: Measures) -> int:
    """Log every PHY-13 clamp activation over a converged solution and return the count.

    The concentration fits hold only to the parameter file's validity limit
    (5.3 M for NaCl) and every property is capped at its value there by clamping
    the correction driver (PHY-13). That clamp is silent inside the symbolic
    solve — :meth:`~nanopnp.materials.electrolyte.Electrolyte.average_concentration`
    clamps each ``c_i`` *before* the average, so the driver it returns can never
    exceed the limit — yet a real high-salt run near a charged wall, where a
    counter-ion is enriched past the cap, extrapolates the fits there. ``.knowledge/01``
    §3 names that silent extrapolation "a plausible source of confusion"; PHY-13
    requires it to be logged with its location and property instead.

    This samples the converged species concentrations on the fluid nodal set,
    exactly as the NUM-17 gates do (:meth:`CoupledModel.gates` builds the same
    fluid-restricted sampler), and hands them to
    :meth:`~nanopnp.materials.electrolyte.Electrolyte.report_clamp_activations`,
    which owns the "logged with location and property" half of the requirement.
    :func:`extract` calls it on every operating point, so a QoI extraction emits
    the record automatically; it is public so an end-of-solve diagnostic can call
    it without extracting.

    Parameters
    ----------
    solution
        A converged solution of a coupled model.
    measures
        The symmetry policy the model was solved with; only its coordinate names
        are read, for the location in the log line.

    Returns
    -------
    int
        Total number of clamped samples, summed over species; 0 when the whole
        solution stayed inside the fit range.
    """
    model = _coupled(solution)
    sampler = FieldSampler(
        solution.space.mesh, coordinates=measures.coordinate_names, materials=model.fluid
    )
    variables = model.concentration_variables(_functions(solution))
    concentrations_SI = species_concentrations_SI(model.scales, variables.values)
    sampled = [sampler.evaluate(concentrations_SI[name]) for name in model.species]
    coordinates = [(float(point[0]), float(point[1])) for point in sampler.points]
    return model.electrolyte.report_clamp_activations(sampled, coordinates=coordinates)


def rectification(forward: QuantitiesOfInterest, reverse: QuantitiesOfInterest) -> float:
    """Return the rectification ratio of a matched pair of biases (NUM-27).

    Raises
    ------
    ValueError
        If ``forward`` is not the positive bias, or if the two biases are not
        opposite in sign, where the ratio compares unrelated operating points
        rather than the two directions of one.
    """
    if forward.bias_V <= 0.0:
        raise ValueError(
            f"'forward' must be the positive bias: RR is |I(+V)|/|I(-V)|, so a swapped pair "
            f"returns the reciprocal and inverts the rectification direction with no other "
            f"symptom. Got forward={forward.bias_V} V and reverse={reverse.bias_V} V"
        )
    if forward.bias_V * reverse.bias_V >= 0.0:
        raise ValueError(
            f"a rectification ratio compares opposite biases, got {forward.bias_V} V and "
            f"{reverse.bias_V} V"
        )
    return rectification_ratio(forward.current_A, reverse.current_A)


def summarise(quantities: Sequence[QuantitiesOfInterest]) -> list[dict[str, Option]]:
    """Return the summaries of several operating points, for a sweep's manifest."""
    return [point.summary() for point in quantities]

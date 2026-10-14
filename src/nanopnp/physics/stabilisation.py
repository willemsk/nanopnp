"""The residual stabilisation registry and its terms (NUM-11, NUM-14, NUM-15)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Protocol, TypeAlias

from nanopnp.core.typing import Expression, IntegralTerm, Mesh, Numeric, Option
from nanopnp.numerics.measures import Measures
from nanopnp.physics.coefficients import NondimensionalCoefficients
from nanopnp.physics.flow import axisymmetric_divergence
from nanopnp.physics.nernst_planck import ConcentrationVariables, steric_flux

__all__ = [
    "CROSSWIND_BONUS_ORDER",
    "CROSSWIND_COEFFICIENT",
    "FLOW_BONUS_ORDER",
    "GRAD_DIV_COEFFICIENT",
    "MAGNITUDE_FLOOR",
    "SHAKIB_CONVECTIVE",
    "SHAKIB_VISCOUS",
    "STREAMLINE_BONUS_ORDER",
    "STREAMLINE_CUTOFF",
    "WIND_FLOOR",
    "WIND_THRESHOLD",
    "FlowState",
    "NoStabilisation",
    "ReferenceStabilisation",
    "StabilisationIntegrand",
    "StabilisationModel",
    "StreamlineStabilisation",
    "TransportState",
    "advective_velocity",
    "approximate_residual",
    "cell_peclet",
    "create",
    "crosswind_projector",
    "crosswind_viscosity",
    "element_size",
    "grad_div_parameter",
    "momentum_parameter",
    "momentum_residual",
    "register",
    "registered_stabilisations",
    "streamline_parameter",
]

# Chaudhry, Comer, Aksimentiev & Olson, Commun. Comput. Phys. 15, 93 (2014); section 6.4.1.
STREAMLINE_CUTOFF = 1.0

# COMSOL exports no tuning for tds.crosswind
# (knowledge/09-comsol-reference-settings/07-differences-that-cannot-be-removed.md).
# Not a case-file field: a variant is a second registered mode.
CROSSWIND_COEFFICIENT = 1.0

# tau_c = Re rho~ ||u~|| h_K / 2, the standard scaling.
GRAD_DIV_COEFFICIENT = 0.5

SHAKIB_CONVECTIVE = 2.0

# Coefficients of the two branches of the Shakib parameter (section 6.4.2).
SHAKIB_VISCOUS = 4.0

# NUM-15 order 4, read as a lower bound: Measures takes a bonus over its own estimate.
STREAMLINE_BONUS_ORDER = 4

# The reference exported tds.crosswind at order 6.
CROSSWIND_BONUS_ORDER = 6

# NUM-07's minimum governs the grad-div term over the reference's order 2 (section 6.2 NOTE).
FLOW_BONUS_ORDER = 4

# Denominator guard on a speed; the diffusive branch of tau_i is the finite limit of 0/0.
WIND_FLOOR = 1.0e-30

# Derivative guard inside sqrt of a squared vector: NGSolve's 0/0 is NaN in the Jacobian under
# AssembleLinearization (knowledge/06-numerics-fem/04-stabilisation.md).
MAGNITUDE_FLOOR = WIND_FLOOR * WIND_FLOOR

# No wind, no crosswind: the projector would degenerate to isotropic diffusion,
# which the reference had off.
WIND_THRESHOLD = 1.0e-12


def element_size() -> Expression:
    """Return ``h_K = sqrt(2|K|)``, the element size the stabilisation parameters are built on."""
    import ngsolve as ngs

    return ngs.specialcf.mesh_size


@dataclass(frozen=True)
class StabilisationIntegrand:
    """One stabilisation contribution and its quadrature."""

    integrand: Expression
    extra_order: int = 0
    singular: bool = False


@dataclass(frozen=True)
class TransportState:
    """Everything a transport stabilisation term needs about one species."""

    species: str
    coefficients: NondimensionalCoefficients
    variables: ConcentrationVariables
    potential: Expression
    velocity: Expression | None
    steric: bool = True

    @property
    def diffusivity(self) -> Expression:
        """Return ``D~_i``."""
        return self.coefficients.diffusivity(self.species)

    @property
    def concentration_gradient(self) -> Expression:
        """Return ``grad(c~_i)``, in whichever branch is in force."""
        return self.variables.gradients[self.species]


@dataclass(frozen=True)
class FlowState:
    """Everything the flow stabilisation needs about the momentum block."""

    coefficients: NondimensionalCoefficients
    velocity: Expression
    pressure: Expression
    density: Numeric = 1.0
    body_force: Expression | None = None
    inertia: bool = True
    source: Expression | None = None


def _magnitude(vector: Expression) -> Expression:
    import ngsolve as ngs

    return ngs.sqrt(vector * vector + MAGNITUDE_FLOOR)


def _absolute(scalar: Expression) -> Expression:
    import ngsolve as ngs

    return ngs.IfPos(scalar, scalar, -scalar)


def _positive_part(scalar: Expression) -> Expression:
    import ngsolve as ngs

    return ngs.IfPos(scalar, scalar, 0.0)


def advective_velocity(state: TransportState) -> Expression:
    """Return ``b~_i``, the non-diffusive part of the flux bracket."""
    import ngsolve as ngs

    coefficients = state.coefficients
    ion = coefficients.electrolyte.ion(state.species)
    velocity = float(ion.valence) * coefficients.mobility(state.species) * ngs.grad(state.potential)
    if state.steric:
        velocity = velocity + state.diffusivity * steric_flux(
            state.variables,
            packing_coefficients=coefficients.packing_coefficients,
            volume_ratio=coefficients.steric_volume_ratio(state.species),
        )
    if state.velocity is not None:
        velocity = velocity - coefficients.peclet * state.velocity
    return velocity


def cell_peclet(state: TransportState, *, size: Expression | None = None) -> Expression:
    """Return the cell Peclet number ``Pe_K = ||b~_i|| h_K / (2 D~_i)``.

    Parameters
    ----------
    state
        The state to evaluate at; the converged one, for a diagnostic.
    """
    return (
        _magnitude(advective_velocity(state))
        * (element_size() if size is None else size)
        / (2.0 * state.diffusivity)
    )


def approximate_residual(state: TransportState, *, source: Expression | None = None) -> Expression:
    """Return the approximate transport residual ``R~_i = b~_i . grad(c~_i) - s~_i``."""
    residual = advective_velocity(state) * state.concentration_gradient
    if source is not None:
        residual = residual - source
    return residual


def streamline_parameter(
    state: TransportState,
    *,
    size: Expression | None = None,
    cutoff: float = STREAMLINE_CUTOFF,
) -> Expression:
    """Return the streamline parameter ``tau_i = (h_K / 2||b~_i||) psi(Pe_K)``."""
    import ngsolve as ngs

    h = element_size() if size is None else size
    speed = _magnitude(advective_velocity(state))
    diffusivity = state.diffusivity
    peclet = speed * h / (2.0 * diffusivity)
    return ngs.IfPos(
        peclet - cutoff,
        h / (2.0 * (speed + WIND_FLOOR)),
        h * h / (4.0 * cutoff * diffusivity),
    )


def crosswind_projector(state: TransportState) -> Expression:
    """Return the streamline-crosswind projector ``P_b = I - b^ (x) b^``."""
    import ngsolve as ngs

    direction = advective_velocity(state)
    unit = direction / (_magnitude(direction) + WIND_FLOOR)
    return ngs.Id(2) - ngs.OuterProduct(unit, unit)


def crosswind_viscosity(
    state: TransportState,
    *,
    source: Expression | None = None,
    size: Expression | None = None,
    coefficient: float = CROSSWIND_COEFFICIENT,
) -> Expression:
    """Return the crosswind viscosity ``nu_K``, zero below the wind threshold ``1/C_cw``."""
    import ngsolve as ngs

    h = element_size() if size is None else size
    residual = _absolute(approximate_residual(state, source=source))
    gradient = _magnitude(state.concentration_gradient)
    raw = coefficient * h * residual / (2.0 * (gradient + WIND_FLOOR)) - state.diffusivity
    return ngs.IfPos(
        _magnitude(advective_velocity(state)) - WIND_THRESHOLD, _positive_part(raw), 0.0
    )


def momentum_residual(state: FlowState) -> Expression:
    """Return the approximate momentum residual ``R~_m``."""
    import ngsolve as ngs

    residual = ngs.grad(state.pressure)
    if state.inertia:
        residual = residual + state.coefficients.reynolds * state.density * (
            ngs.grad(state.velocity) * state.velocity
        )
    if state.body_force is not None:
        residual = residual - state.body_force
    if state.source is not None:
        residual = residual - state.source
    return residual


def momentum_parameter(state: FlowState, *, size: Expression | None = None) -> Expression:
    """Return the momentum stabilisation parameter ``tau_m``, bounded at zero velocity."""
    import ngsolve as ngs

    h = element_size() if size is None else size
    convective = (
        SHAKIB_CONVECTIVE
        * state.coefficients.reynolds
        * state.density
        * _magnitude(state.velocity)
        / h
    )
    viscous = SHAKIB_VISCOUS * state.coefficients.viscosity() / (h * h)
    return 1.0 / ngs.sqrt(convective * convective + viscous * viscous)


def grad_div_parameter(state: FlowState, *, size: Expression | None = None) -> Expression:
    """Return the grad-div parameter ``tau_c = Re rho~ ||u~|| h_K / 2``."""
    h = element_size() if size is None else size
    return (
        GRAD_DIV_COEFFICIENT
        * state.coefficients.reynolds
        * state.density
        * _magnitude(state.velocity)
        * h
    )


class StabilisationModel(Protocol):
    """One residual stabilisation mode; immutable, carrying its provenance and tuning constants."""

    @property
    def name(self) -> str:
        """Registered name of the mode."""

    @property
    def parameters(self) -> Mapping[str, float]:
        """The tuning constants in force, flattened for reporting."""

    @property
    def provenance(self) -> Mapping[str, str]:
        """Where the mode and its constants came from."""

    @property
    def terms(self) -> tuple[str, ...]:
        """The terms this mode assembles, in assembly order; empty for ``none``."""

    @property
    def permits_equal_order(self) -> bool:
        """Whether this mode supplies the flow stabilisation an equal-order pair requires."""

    def transport_term(
        self,
        measures: Measures,
        *,
        trial: TransportState,
        lagged: TransportState,
        test: Expression,
        source: Expression | None = None,
        **kwargs: Option,
    ) -> IntegralTerm | None:
        """Return this mode's contribution to one species' residual, or ``None``."""

    def flow_term(
        self,
        measures: Measures,
        *,
        trial: FlowState,
        lagged: FlowState,
        velocity_test: Expression,
        pressure_test: Expression,
        **kwargs: Option,
    ) -> IntegralTerm | None:
        """Return this mode's contribution to the flow residual, or ``None``."""

    def transport_contributions(
        self,
        *,
        trial: TransportState,
        lagged: TransportState,
        test: Expression,
        source: Expression | None = None,
    ) -> tuple[StabilisationIntegrand, ...]:
        """Return one species' transport contributions as unweighted integrands."""

    def indicator_term(
        self,
        measures: Measures,
        mesh: Mesh,
        *,
        state: TransportState,
        indicator: Expression,
        source: Expression | None = None,
        **kwargs: Option,
    ) -> float:
        """Return this mode's contribution to the indicator of the current."""


@dataclass(frozen=True)
class NoStabilisation:
    """The ``none`` mode: unstabilised Galerkin; it assembles nothing."""

    @property
    def name(self) -> str:
        """Registered name of the mode."""
        return "none"

    @property
    def parameters(self) -> Mapping[str, float]:
        """The tuning constants in force, flattened for reporting."""
        return {}

    @property
    def provenance(self) -> Mapping[str, str]:
        """Where the mode and its constants came from."""
        return {
            "mode": "none",
            "terms": "",
            "note": "unstabilised Galerkin; no term is assembled (NUM-11)",
        }

    @property
    def terms(self) -> tuple[str, ...]:
        """The terms this mode assembles, in assembly order; empty for ``none``."""
        return ()

    @property
    def permits_equal_order(self) -> bool:
        """Whether this mode supplies the flow stabilisation an equal-order pair requires."""
        return False

    def transport_contributions(
        self,
        *,
        trial: TransportState,
        lagged: TransportState,
        test: Expression,
        source: Expression | None = None,
    ) -> tuple[StabilisationIntegrand, ...]:
        """Return one species' transport contributions as unweighted integrands."""
        del trial, lagged, test, source
        return ()

    def transport_term(
        self,
        measures: Measures,
        *,
        trial: TransportState,
        lagged: TransportState,
        test: Expression,
        source: Expression | None = None,
        **kwargs: Option,
    ) -> IntegralTerm | None:
        """Return this mode's contribution to one species' residual, or ``None``."""
        del measures, trial, lagged, test, source, kwargs
        return None

    def flow_term(
        self,
        measures: Measures,
        *,
        trial: FlowState,
        lagged: FlowState,
        velocity_test: Expression,
        pressure_test: Expression,
        **kwargs: Option,
    ) -> IntegralTerm | None:
        """Return this mode's contribution to the flow residual, or ``None``."""
        del measures, trial, lagged, velocity_test, pressure_test, kwargs
        return None

    def indicator_term(
        self,
        measures: Measures,
        mesh: Mesh,
        *,
        state: TransportState,
        indicator: Expression,
        source: Expression | None = None,
        **kwargs: Option,
    ) -> float:
        """Return this mode's contribution to the indicator of the current."""
        del measures, mesh, state, indicator, source, kwargs
        return 0.0


@dataclass(frozen=True)
class StreamlineStabilisation:
    """``supg``: the transport streamline term alone.

    Parameters
    ----------
    crosswind_coefficient
        The crosswind coefficient ``C_cw``.
    """

    crosswind: bool = False
    flow: bool = False
    crosswind_coefficient: float = CROSSWIND_COEFFICIENT
    streamline_cutoff: float = STREAMLINE_CUTOFF

    @property
    def name(self) -> str:
        """Registered name of the mode."""
        return "supg"

    @property
    def permits_equal_order(self) -> bool:
        """Whether this mode supplies the flow stabilisation an equal-order pair requires."""
        # Read off the flow term rather than declared per class: the pair is legal
        # exactly when the PSPG content of the GLS term is assembled, so a mode
        # that claimed otherwise would be claiming something about an operator it
        # does not build.
        return self.flow

    @property
    def parameters(self) -> Mapping[str, float]:
        """The tuning constants in force, flattened for reporting."""
        values = {"streamline_cutoff": float(self.streamline_cutoff)}
        if self.crosswind:
            values["crosswind_coefficient"] = float(self.crosswind_coefficient)
        if self.flow:
            values["grad_div_coefficient"] = GRAD_DIV_COEFFICIENT
            values["shakib_convective"] = SHAKIB_CONVECTIVE
            values["shakib_viscous"] = SHAKIB_VISCOUS
        return values

    @property
    def terms(self) -> tuple[str, ...]:
        """Return the names of the terms this mode assembles, in assembly order."""
        assembled = ["streamline"]
        if self.crosswind:
            assembled.append("crosswind")
        if self.flow:
            assembled += ["flow_gls", "grad_div"]
        return tuple(assembled)

    @property
    def provenance(self) -> Mapping[str, str]:
        """Where the mode and its constants came from."""
        return {
            "mode": self.name,
            "terms": ",".join(self.terms),
            "residual": "approximate: every second derivative of a trial field dropped (NUM-14)",
            "element_size": "ngsolve.specialcf.mesh_size = sqrt(2|K|), measured (VER-41)",
            "parameters_evaluated_at": "iterate",
            "streamline_source": (
                "Chaudhry, Comer, Aksimentiev & Olson, Commun. Comput. Phys. 15, 93 (2014); "
                "SPECIFICATION.md section 6.4.1"
            ),
            "crosswind_source": (
                "Do Carmo-Galeao type, SPECIFICATION.md NUM-14; COMSOL's own tds.crosswind is "
                "not exported"
                if self.crosswind
                else "off"
            ),
            "flow_source": (
                "GLS with the Shakib parameter plus grad-div, SPECIFICATION.md section 6.4.2"
                if self.flow
                else "off"
            ),
            "integration_bonus": (
                f"streamline {STREAMLINE_BONUS_ORDER}, crosswind {CROSSWIND_BONUS_ORDER}, "
                f"flow {FLOW_BONUS_ORDER} (NUM-15, lower bounds)"
            ),
        }

    def transport_contributions(
        self,
        *,
        trial: TransportState,
        lagged: TransportState,
        test: Expression,
        source: Expression | None = None,
    ) -> tuple[StabilisationIntegrand, ...]:
        """Return the transport contributions as unweighted integrands."""
        import ngsolve as ngs

        size = element_size()
        drift = advective_velocity(trial)
        residual = approximate_residual(trial, source=source)
        tau = streamline_parameter(lagged, size=size, cutoff=self.streamline_cutoff)
        contributions = [
            StabilisationIntegrand(
                -tau * residual * (drift * ngs.grad(test)),
                extra_order=STREAMLINE_BONUS_ORDER,
            )
        ]
        if self.crosswind:
            viscosity = crosswind_viscosity(
                lagged,
                source=source,
                size=size,
                coefficient=self.crosswind_coefficient,
            )
            projected = crosswind_projector(lagged) * trial.concentration_gradient
            contributions.append(
                StabilisationIntegrand(
                    -viscosity * (projected * ngs.grad(test)),
                    extra_order=CROSSWIND_BONUS_ORDER,
                )
            )
        return tuple(contributions)

    def transport_term(
        self,
        measures: Measures,
        *,
        trial: TransportState,
        lagged: TransportState,
        test: Expression,
        source: Expression | None = None,
        **kwargs: Option,
    ) -> IntegralTerm | None:
        """Return this mode's contribution to one species' residual, or ``None``."""
        contributions = self.transport_contributions(
            trial=trial, lagged=lagged, test=test, source=source
        )
        return _assemble(measures, contributions, **kwargs)

    def flow_term(
        self,
        measures: Measures,
        *,
        trial: FlowState,
        lagged: FlowState,
        velocity_test: Expression,
        pressure_test: Expression,
        **kwargs: Option,
    ) -> IntegralTerm | None:
        """Return this mode's contribution to the flow residual, or ``None``."""
        if not self.flow:
            return None
        import ngsolve as ngs

        size = element_size()
        tau_m = momentum_parameter(lagged, size=size)
        tau_c = grad_div_parameter(lagged, size=size)
        residual = momentum_residual(trial)
        reynolds = trial.coefficients.reynolds

        # The velocity row is coercive, so its GLS part enters with a plus; the continuity row
        # is -int q rho~ div^(u~), minus that orientation, so its pressure-test part enters
        # with a minus. Grad-div is on the velocity row (plus) and carries 1/r through div^,
        # so it is integrated with the singular rule.
        convective_test = reynolds * lagged.density * (ngs.grad(velocity_test) * lagged.velocity)
        return _assemble(
            measures,
            (
                StabilisationIntegrand(
                    tau_m * (residual * convective_test), extra_order=FLOW_BONUS_ORDER
                ),
                StabilisationIntegrand(
                    -tau_m * (residual * ngs.grad(pressure_test)), extra_order=FLOW_BONUS_ORDER
                ),
                StabilisationIntegrand(
                    tau_c
                    * axisymmetric_divergence(velocity_test, measures)
                    * axisymmetric_divergence(trial.velocity, measures),
                    extra_order=FLOW_BONUS_ORDER,
                    singular=True,
                ),
            ),
            **kwargs,
        )

    def indicator_term(
        self,
        measures: Measures,
        mesh: Mesh,
        *,
        state: TransportState,
        indicator: Expression,
        source: Expression | None = None,
        **kwargs: Option,
    ) -> float:
        """Return this mode's contribution to the indicator of the current."""
        total = 0.0
        for index, contribution in enumerate(
            self.transport_contributions(trial=state, lagged=state, test=indicator, source=source)
        ):
            total += measures.integrate(
                contribution.integrand,
                mesh,
                singular=contribution.singular,
                extra_order=contribution.extra_order,
                what=f"the {self.name!r} stabilisation term {index} of {state.species!r}",
                **kwargs,
            )
        return total


@dataclass(frozen=True)
class ReferenceStabilisation(StreamlineStabilisation):
    """``reference``: the full stabilisation table; the only mode permitting equal orders."""

    crosswind: bool = True
    flow: bool = True

    @property
    def name(self) -> str:
        """Registered name of the mode."""
        return "reference"


def _assemble(
    measures: Measures,
    contributions: tuple[StabilisationIntegrand, ...],
    **kwargs: Option,
) -> IntegralTerm | None:
    if not contributions:
        return None
    terms = [
        measures.volume(
            contribution.integrand,
            singular=contribution.singular,
            extra_order=contribution.extra_order,
            **kwargs,
        )
        for contribution in contributions
    ]
    total = terms[0]
    for term in terms[1:]:
        total = total + term
    return total


ModelBuilder: TypeAlias = Callable[[], StabilisationModel]

_REGISTRY: dict[str, ModelBuilder] = {}


def register(name: str, builder: ModelBuilder) -> None:
    """Register a stabilisation mode under ``name``; ValueError if taken."""
    if name in _REGISTRY:
        raise ValueError(f"stabilisation mode {name!r} is already registered")
    _REGISTRY[name] = builder


def registered_stabilisations() -> tuple[str, ...]:
    """Return every selectable mode name, sorted."""
    return tuple(sorted(_REGISTRY))


def create(name: str) -> StabilisationModel:
    """Build the stabilisation mode registered as ``name``; KeyError if none is."""
    try:
        builder = _REGISTRY[name]
    except KeyError:
        known = ", ".join(registered_stabilisations())
        raise KeyError(
            f"unknown stabilisation mode {name!r}; registered modes are {known}"
        ) from None
    return builder()


register("none", NoStabilisation)
register("supg", StreamlineStabilisation)
register("reference", ReferenceStabilisation)

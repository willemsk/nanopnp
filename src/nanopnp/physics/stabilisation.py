"""The residual stabilisation registry and its terms."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, TypeAlias

from nanopnp.core.typing import Expression, Numeric
from nanopnp.io.vocabulary import PRESSURE, VELOCITY
from nanopnp.physics.kernel import force_density, wind
from nanopnp.physics.operators import Geometry, Operators, divergence

if TYPE_CHECKING:
    from nanopnp.physics.kernel import Build, Context, Side

__all__ = [
    "CROSSWIND_BONUS_ORDER",
    "CROSSWIND_COEFFICIENT",
    "FLOW_BONUS_ORDER",
    "FLOW_SLOTS",
    "GRAD_DIV_COEFFICIENT",
    "MAGNITUDE_FLOOR",
    "SHAKIB_CONVECTIVE",
    "SHAKIB_VISCOUS",
    "STREAMLINE_BONUS_ORDER",
    "STREAMLINE_CUTOFF",
    "TRANSPORT_SLOTS",
    "WIND_FLOOR",
    "WIND_THRESHOLD",
    "FlowState",
    "NoStabilisation",
    "ReferenceStabilisation",
    "StabilisationModel",
    "StreamlineStabilisation",
    "TransportState",
    "approximate_residual",
    "cell_peclet",
    "create",
    "crosswind_projector",
    "crosswind_viscosity",
    "flow_contribution",
    "flow_state",
    "grad_div_parameter",
    "momentum_parameter",
    "momentum_residual",
    "register",
    "registered_stabilisations",
    "streamline_parameter",
    "transport_contribution",
    "transport_state",
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


TRANSPORT_SLOTS = ("streamline", "crosswind")
"""The families of a species' transport stabilisation slots, in assembly order."""

FLOW_SLOTS = ("flow.gls_momentum", "flow.gls_pressure", "flow.grad_div")
"""The families of the flow stabilisation slots, in assembly order."""


@dataclass(frozen=True)
class TransportState:
    """Everything a transport stabilisation term reads about one species on one side.

    Parameters
    ----------
    gradient
        ``grad(c~_i)``, in whichever branch is in force.
    wind
        ``b~_i``, the sum of the drifts in force.
    """

    species: str
    diffusivity: Expression
    gradient: Expression
    wind: Expression
    ops: Operators
    geometry: Geometry


@dataclass(frozen=True)
class FlowState:
    """Everything the flow stabilisation reads about the momentum block on one side.

    Parameters
    ----------
    density
        ``rho~``, 1 where the variable density is not in force.
    force
        ``f``, the sum of the force densities in force, or None.
    source
        A manufactured momentum source, or None.
    """

    velocity: Expression
    pressure: Expression
    density: Numeric
    viscosity: Expression
    reynolds: float
    force: Expression | None
    source: Expression | None
    ops: Operators
    geometry: Geometry


def transport_state(context: Context, side: Side, species: str) -> TransportState:
    """Return one species' transport state on ``side``, its wind summed over ``context.terms``."""
    drift = wind(context, side, species)
    if drift is None:
        raise ValueError(f"no term in force states a drift of {species!r}; there is no wind")
    return TransportState(
        species=species,
        diffusivity=side.coefficients.diffusivity(species),
        gradient=side.variables.gradients[species],
        wind=drift,
        ops=context.ops,
        geometry=context.geometry,
    )


def flow_state(context: Context, side: Side) -> FlowState:
    """Return the flow state on ``side``, its force summed over ``context.terms``."""
    return FlowState(
        velocity=side.functions[VELOCITY],
        pressure=side.functions[PRESSURE],
        density=1.0 if side.density is None else side.density,
        viscosity=side.coefficients.viscosity(),
        reynolds=side.coefficients.reynolds,
        force=force_density(context, side),
        source=context.inputs.sources.get(VELOCITY),
        ops=context.ops,
        geometry=context.geometry,
    )


def _magnitude(ops: Operators, vector: Expression) -> Expression:
    return ops.sqrt(ops.dot(vector, vector) + MAGNITUDE_FLOOR)


def _absolute(ops: Operators, scalar: Expression) -> Expression:
    return ops.where_positive(scalar, scalar, -scalar)


def _positive_part(ops: Operators, scalar: Expression) -> Expression:
    return ops.where_positive(scalar, scalar, 0.0)


def cell_peclet(state: TransportState, *, size: Expression | None = None) -> Expression:
    """Return the cell Peclet number ``Pe_K = ||b~_i|| h_K / (2 D~_i)``.

    Parameters
    ----------
    state
        The state to evaluate at; the converged one, for a diagnostic.
    """
    h = state.ops.element_size() if size is None else size
    return _magnitude(state.ops, state.wind) * h / (2.0 * state.diffusivity)


def approximate_residual(state: TransportState, *, source: Expression | None = None) -> Expression:
    """Return the approximate transport residual ``R~_i = b~_i . grad(c~_i) - s~_i``."""
    residual = state.ops.dot(state.wind, state.gradient)
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
    ops = state.ops
    h = ops.element_size() if size is None else size
    speed = _magnitude(ops, state.wind)
    diffusivity = state.diffusivity
    peclet = speed * h / (2.0 * diffusivity)
    return ops.where_positive(
        peclet - cutoff,
        h / (2.0 * (speed + WIND_FLOOR)),
        h * h / (4.0 * cutoff * diffusivity),
    )


def crosswind_projector(state: TransportState) -> Expression:
    """Return the streamline-crosswind projector ``P_b = I - b^ (x) b^``."""
    ops = state.ops
    unit = state.wind / (_magnitude(ops, state.wind) + WIND_FLOOR)
    return state.geometry.identity - ops.outer(unit, unit)


def crosswind_viscosity(
    state: TransportState,
    *,
    source: Expression | None = None,
    size: Expression | None = None,
    coefficient: float = CROSSWIND_COEFFICIENT,
) -> Expression:
    """Return the crosswind viscosity ``nu_K``, zero below the wind threshold ``1/C_cw``."""
    ops = state.ops
    h = ops.element_size() if size is None else size
    residual = _absolute(ops, approximate_residual(state, source=source))
    gradient = _magnitude(ops, state.gradient)
    raw = coefficient * h * residual / (2.0 * (gradient + WIND_FLOOR)) - state.diffusivity
    return ops.where_positive(
        _magnitude(ops, state.wind) - WIND_THRESHOLD, _positive_part(ops, raw), 0.0
    )


def momentum_residual(state: FlowState) -> Expression:
    """Return the approximate momentum residual ``R~_m = grad(p~) - f - s``."""
    residual = state.ops.grad(state.pressure)
    if state.force is not None:
        residual = residual - state.force
    if state.source is not None:
        residual = residual - state.source
    return residual


def momentum_parameter(state: FlowState, *, size: Expression | None = None) -> Expression:
    """Return the momentum stabilisation parameter ``tau_m``, bounded at zero velocity."""
    ops = state.ops
    h = ops.element_size() if size is None else size
    convective = (
        SHAKIB_CONVECTIVE * state.reynolds * state.density * _magnitude(ops, state.velocity) / h
    )
    viscous = SHAKIB_VISCOUS * state.viscosity / (h * h)
    return 1.0 / ops.sqrt(convective * convective + viscous * viscous)


def grad_div_parameter(state: FlowState, *, size: Expression | None = None) -> Expression:
    """Return the grad-div parameter ``tau_c = Re rho~ ||u~|| h_K / 2``."""
    ops = state.ops
    h = ops.element_size() if size is None else size
    return (
        GRAD_DIV_COEFFICIENT * state.reynolds * state.density * _magnitude(ops, state.velocity) * h
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

    def transport_contributions(
        self,
        *,
        trial: TransportState,
        lagged: TransportState,
        test: Expression,
        source: Expression | None = None,
    ) -> Mapping[str, Expression]:
        """Return one species' transport integrands by slot family; empty for no term."""

    def flow_contributions(
        self,
        *,
        trial: FlowState,
        lagged: FlowState,
        velocity_test: Expression,
        pressure_test: Expression,
    ) -> Mapping[str, Expression]:
        """Return the flow integrands by slot family; empty for no term."""


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
    ) -> Mapping[str, Expression]:
        """Return one species' transport integrands by slot family; empty for no term."""
        del trial, lagged, test, source
        return {}

    def flow_contributions(
        self,
        *,
        trial: FlowState,
        lagged: FlowState,
        velocity_test: Expression,
        pressure_test: Expression,
    ) -> Mapping[str, Expression]:
        """Return the flow integrands by slot family; empty for no term."""
        del trial, lagged, velocity_test, pressure_test
        return {}


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
    ) -> Mapping[str, Expression]:
        """Return one species' transport integrands by slot family."""
        ops = trial.ops
        size = ops.element_size()
        residual = approximate_residual(trial, source=source)
        tau = streamline_parameter(lagged, size=size, cutoff=self.streamline_cutoff)
        contributions = {"streamline": -tau * residual * ops.dot(trial.wind, ops.grad(test))}
        if self.crosswind:
            viscosity = crosswind_viscosity(
                lagged,
                source=source,
                size=size,
                coefficient=self.crosswind_coefficient,
            )
            projected = ops.apply(crosswind_projector(lagged), trial.gradient)
            contributions["crosswind"] = -viscosity * ops.dot(projected, ops.grad(test))
        return contributions

    def flow_contributions(
        self,
        *,
        trial: FlowState,
        lagged: FlowState,
        velocity_test: Expression,
        pressure_test: Expression,
    ) -> Mapping[str, Expression]:
        """Return the flow integrands by slot family; empty without the flow terms."""
        if not self.flow:
            return {}
        ops, geometry = trial.ops, trial.geometry
        size = ops.element_size()
        tau_m = momentum_parameter(lagged, size=size)
        tau_c = grad_div_parameter(lagged, size=size)
        residual = momentum_residual(trial)

        # The velocity row is coercive, so its GLS part enters with a plus; the continuity row
        # is -int q rho~ div^(u~), minus that orientation, so its pressure-test part enters
        # with a minus. Grad-div is on the velocity row (plus) and carries 1/r through div^,
        # so its slot takes the singular rule.
        convective_test = (
            trial.reynolds * lagged.density * ops.apply(ops.grad(velocity_test), lagged.velocity)
        )
        return {
            "flow.gls_momentum": tau_m * ops.dot(residual, convective_test),
            "flow.gls_pressure": -tau_m * ops.dot(residual, ops.grad(pressure_test)),
            "flow.grad_div": tau_c
            * divergence(ops, geometry, velocity_test)
            * divergence(ops, geometry, trial.velocity),
        }


@dataclass(frozen=True)
class ReferenceStabilisation(StreamlineStabilisation):
    """``reference``: the full stabilisation table; the only mode permitting equal orders."""

    crosswind: bool = True
    flow: bool = True

    @property
    def name(self) -> str:
        """Registered name of the mode."""
        return "reference"


def transport_contribution(family: str) -> Build:
    """Return the build of the mode's transport integrand of ``family`` for the species at hand."""

    def build(context: Context) -> Expression | None:
        if not context.stabilisation.terms:
            return None
        species = context.require_species()
        field = context.require_field()
        integrands = context.stabilisation.transport_contributions(
            trial=transport_state(context, context.trial, species),
            lagged=transport_state(context, context.lagged, species),
            test=context.tests[field],
            source=context.inputs.sources.get(field),
        )
        return integrands.get(family)

    return build


def flow_contribution(family: str) -> Build:
    """Return the build of the mode's flow integrand of ``family``."""

    def build(context: Context) -> Expression | None:
        if not context.stabilisation.terms:
            return None
        integrands = context.stabilisation.flow_contributions(
            trial=flow_state(context, context.trial),
            lagged=flow_state(context, context.lagged),
            velocity_test=context.tests[VELOCITY],
            pressure_test=context.tests[PRESSURE],
        )
        return integrands.get(family)

    return build


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

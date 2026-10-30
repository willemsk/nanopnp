"""The physics-model registry (PHY-21, PHY-22, FR-20, section 5.4.3)."""

from __future__ import annotations

import logging
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any, Literal, Protocol, TypeAlias, cast

from nanopnp.core.scaling import NM_PER_M, Scales
from nanopnp.core.typing import (
    AssembledForm,
    Expression,
    FESpace,
    GridFunction,
    IntegralTerm,
    Mesh,
    Option,
)
from nanopnp.io.vocabulary import (
    POTENTIAL,
    PRESSURE,
    PRESSURE_MEAN,
    VELOCITY,
    VELOCITY_AXIS,
)
from nanopnp.materials.electrolyte import CorrectionSwitches, Electrolyte
from nanopnp.materials.fields import blend, nearest_solid_permittivity
from nanopnp.mesh.primitives import (
    DEFAULT_BOUNDARIES,
    ELECTROLYTE_DOMAINS,
    PERMITTIVITY_EXEMPT,
    CoupledBoundaries,
)
from nanopnp.numerics.gates import (
    FieldSampler,
    Gate,
    PackingFractionGate,
    PositivityGate,
    PotentialIncrementGate,
)
from nanopnp.numerics.linear import DEFAULT_SOLVER, solve_correction
from nanopnp.numerics.measures import FixedCharge, Measures
from nanopnp.numerics.newton import (
    DEFAULT_SETTINGS,
    NewtonResult,
    NewtonSettings,
    NewtonStep,
    damped_newton,
)
from nanopnp.physics.coefficients import (
    SATURATED_WALL_DISTANCE_NM,
    NondimensionalCoefficients,
    mesh_unit_scales,
    species_concentrations_SI,
)
from nanopnp.physics.flow import (
    continuity_term,
    dielectric_gradient_force,
    electrical_body_force,
    inertia_term,
    permittivity_gradient,
    pressure_term,
    viscous_operator,
)
from nanopnp.physics.nernst_planck import (
    ConcentrationVariables,
    nernst_planck_residual,
    species_flux,
)
from nanopnp.physics.pb import (
    linear_pb_operator,
    nonlinear_pb_residual,
    solve_pb_recorded,
)
from nanopnp.physics.poisson import charge_source, poisson_operator, surface_charge_source
from nanopnp.physics.spaces import set_boundary_values
from nanopnp.physics.stabilisation import (
    FlowState,
    StabilisationModel,
    TransportState,
    registered_stabilisations,
)
from nanopnp.physics.stabilisation import cell_peclet as species_cell_peclet
from nanopnp.physics.stabilisation import create as create_stabilisation

if TYPE_CHECKING:
    from nanopnp.io.resolved import ResolvedCase

__all__ = [
    "COEFFICIENTS",
    "DEFAULT_BOUNDARIES",
    "LADDER_STRATEGY",
    "LADDER_TARGETS",
    "SWITCHES",
    "CoupledBoundaries",
    "CoupledModel",
    "ElectrostaticModel",
    "Field",
    "ModelDeclaration",
    "ModelSolution",
    "PhysicsModel",
    "PoissonModel",
    "TransportModel",
    "create",
    "declaration",
    "equal_order_stabilisations",
    "inf_sup_problem",
    "register_model",
    "registered_models",
    "registered_stabilisations",
    "relative_permittivity_field",
    "solves_transport",
    "transport_model",
]

logger = logging.getLogger(__name__)

ElementKind: TypeAlias = Literal["h1", "vector_h1", "number"]

SWITCHES: tuple[str, ...] = ("flow", "variable_density", "inertia", "dielectric_gradient_forces")

COEFFICIENTS: tuple[str, ...] = ("fixed_charge", "solid_fraction", "surface_charge")

LADDER_STRATEGY = "default_ladder"

LADDER_TARGETS: tuple[str, ...] = ("epnp-ns", "pnp-ns")


def equal_order_stabilisations() -> tuple[str, ...]:
    """Return the registered modes that permit an equal-order velocity-pressure pair."""
    return tuple(
        name
        for name in registered_stabilisations()
        if create_stabilisation(name).permits_equal_order
    )


def inf_sup_problem(*, velocity_order: int, pressure_order: int, stabilisation: str) -> str | None:
    """Return why a velocity-pressure order pair is inadmissible, or None.

    Parameters
    ----------
    stabilisation
        Registered mode name; an unregistered name returns None.
    """
    if pressure_order < velocity_order:
        return None
    if (
        stabilisation in registered_stabilisations()
        and create_stabilisation(stabilisation).permits_equal_order
    ):
        return None
    permitting = ", ".join(equal_order_stabilisations()) or "no registered mode"
    return (
        f"velocity order {velocity_order} with pressure order {pressure_order} is not inf-sup "
        "stable; NUM-03 allows equal order only together with the flow stabilisation of "
        f"section 6.4.2, which the {permitting} stabilisation supplies and {stabilisation!r} "
        "does not"
    )


def _check_fixed_charge(fixed_charge: object) -> None:
    if not isinstance(fixed_charge, FixedCharge):
        raise TypeError(
            f"fixed_charge must be a FixedCharge (a density with the rule it is assembled "
            f"with, rule_order=None for NGSolve's estimate), got {type(fixed_charge).__name__}"
        )


def _reject_unknown(kwargs: Mapping[str, Option], where: str) -> None:
    if kwargs:
        raise TypeError(f"{where} got unexpected keyword(s) {', '.join(sorted(kwargs))}")


@dataclass(frozen=True)
class Field:
    """One solved field of a model.

    Parameters
    ----------
    domain
        Material-name regular expression the field lives on; None for the whole domain.
    """

    name: str
    element: ElementKind
    order: int
    domain: str | None = None


@dataclass
class ModelSolution:
    """A converged state and the record of how it was reached.

    Parameters
    ----------
    newton
        The convergence record, or None for a linear model.
    solid_fraction
        The solid fraction assembled with, or None for the sharp split.
    """

    model: PhysicsModel
    space: FESpace
    state: GridFunction
    newton: NewtonResult | None = None
    residual: AssembledForm | None = None
    wall_distance_nm: Expression = SATURATED_WALL_DISTANCE_NM
    solid_fraction: Expression | None = None

    def component(self, name: str) -> Expression:
        """Return one field of the solution by name; KeyError if the model does not solve for it."""
        names = [f.name for f in self.model.fields]
        if name not in names:
            raise KeyError(
                f"{self.model.name!r} has no field {name!r}; it solves {', '.join(names)}"
            )
        if len(names) == 1:
            return self.state
        return self.state.components[names.index(name)]

    @property
    def potential(self) -> Expression:
        """Return the dimensionless potential ``phi~``."""
        return self.component(POTENTIAL)

    @property
    def velocity(self) -> Expression:
        """Return the dimensionless velocity ``u~``."""
        return self.component(VELOCITY)

    @property
    def pressure(self) -> Expression:
        """Return the dimensionless pressure ``p~``."""
        return self.component(PRESSURE)

    def concentration(self, species: str) -> Expression:
        """Return the dimensionless concentration ``c~_i`` of one species, whichever branch ran."""
        import ngsolve as ngs

        field = self.component(concentration_field_name(species))
        if transport_model(self.model).log_variables:
            return ngs.exp(field)
        return field


def concentration_field_name(species: str) -> str:
    """Return the field name holding one species' concentration."""
    return f"c_{species}"


@dataclass(frozen=True)
class ModelDeclaration:
    """What a registered model admits, readable without building it (section 5.4.3 NOTE)."""

    options: tuple[str, ...]
    switches: Mapping[str, tuple[bool, ...]]
    solids: bool
    coefficients: tuple[str, ...] = ()
    wall_distance: bool = False
    strategies: tuple[str, ...] = ("none",)
    quantities: tuple[str, ...] = ()
    transport: bool = False
    reports_newton: bool = False
    unread: frozenset[str] = frozenset()

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "switches", {name: tuple(values) for name, values in self.switches.items()}
        )
        if sorted(self.switches) != sorted(SWITCHES) or not all(self.switches.values()):
            raise ValueError(
                f"a model declaration states the honoured values of every switch of "
                f"{', '.join(SWITCHES)}; this one states {dict(self.switches)}"
            )
        unknown = sorted(set(self.coefficients) - set(COEFFICIENTS))
        if unknown:
            raise ValueError(
                f"coefficients {', '.join(unknown)} are not supplied coefficients; a model may "
                f"accept {', '.join(COEFFICIENTS)}"
            )


class PhysicsModel(Protocol):
    """One physics model, as section 5.4.3 requires it (FR-20)."""

    @property
    def name(self) -> str:
        """Registered name of the model."""
        ...

    @property
    def fields(self) -> tuple[Field, ...]:
        """The solved fields, in the order of the product space."""
        ...

    @property
    def species(self) -> tuple[str, ...]:
        """Names of the solved ionic species; empty for a model with one field."""
        ...

    @property
    def boundary_conditions(self) -> Mapping[str, Mapping[str, str]]:
        """The boundary-condition vocabulary, per field (PHY-09)."""
        ...

    @property
    def scales(self) -> Scales:
        """The NUM-09 scale set the state is solved in, on the mesh's nanometre unit."""
        ...

    @property
    def provenance(self) -> Mapping[str, Any]:
        """Everything a result manifest must record about the model (FR-25)."""
        ...

    def essential_boundaries(self, boundaries: CoupledBoundaries) -> Mapping[str, str]:
        """Return the boundary pattern of every essential condition, keyed by field."""
        ...

    def relative_permittivity(self, solution: ModelSolution) -> Expression | None:
        """Return ``eps~_r`` as the solve used it, or ``None`` if it carries none."""
        ...

    def space(self, mesh: Mesh, boundaries: CoupledBoundaries) -> FESpace:
        """Return the finite-element space the model is posed on."""
        ...

    def cold_state(
        self,
        mesh: Mesh,
        boundaries: CoupledBoundaries,
        *,
        initial_concentrations: Mapping[str, float] | None = None,
    ) -> GridFunction:
        """Return an admissible fresh state on this model's space."""
        ...

    def residual_form(self, space: FESpace, measures: Measures, **kwargs: Option) -> IntegralTerm:
        """Return the weak residual, written in the trial functions."""
        ...

    def solve(self, mesh: Mesh, measures: Measures, **kwargs: Option) -> ModelSolution:
        """Solve the model with its default strategy."""
        ...


class TransportModel(PhysicsModel, Protocol):
    """A model that solves ionic transport: the members used outside ``physics/``."""

    @property
    def electrolyte(self) -> Electrolyte:
        """Reference properties and the correction model per property."""
        ...

    @property
    def fluid(self) -> str:
        """Material pattern the transport and the flow are solved on."""
        ...

    @property
    def order(self) -> int:
        """Element order of ``phi`` and ``c_i``."""
        ...

    @property
    def flow(self) -> bool:
        """Whether the flow block is solved."""
        ...

    @property
    def variable_density(self) -> bool:
        """Whether continuity and inertia carry ``rho~`` (PHY-07)."""
        ...

    @property
    def inertia(self) -> bool:
        """Whether the convective momentum term is assembled."""
        ...

    @property
    def dielectric_gradient_forces(self) -> bool:
        """Whether the PHY-23 deviation is assembled."""
        ...

    @property
    def steric(self) -> bool:
        """Whether ``beta_i`` is active."""
        ...

    @property
    def log_variables(self) -> bool:
        """Whether the NUM-02 log branch is solved."""
        ...

    @property
    def pressure_constraint(self) -> bool:
        """Whether a multiplier fixes the mean pressure."""
        ...

    @property
    def stabilisation_model(self) -> StabilisationModel:
        """The resolved stabilisation mode (NUM-11, NUM-13)."""
        ...

    def coefficients(
        self, variables: ConcentrationVariables, wall_distance_nm: Expression
    ) -> NondimensionalCoefficients:
        """Return the nondimensional material coefficients for a state."""
        ...

    def concentration_variables(
        self, functions: Mapping[str, Expression]
    ) -> ConcentrationVariables:
        """Return the NUM-02 concentration variables."""
        ...

    def transport_states(
        self, functions: Mapping[str, Expression], wall_distance_nm: Expression
    ) -> dict[str, TransportState]:
        """Return one stabilisation state per species."""
        ...

    def cell_peclet(
        self, state: GridFunction, wall_distance_nm: Expression
    ) -> dict[str, Expression]:
        """Return ``Pe_K`` per species (NUM-12)."""
        ...

    def permittivity(
        self,
        mesh: Mesh,
        coefficients: NondimensionalCoefficients,
        *,
        solid_fraction: Expression | None = None,
    ) -> Expression:
        """Return ``eps~_r`` over all of Omega at a state."""
        ...


def relative_permittivity_field(
    mesh: Mesh,
    *,
    model_name: str,
    fluid: str,
    fluid_permittivity: Expression,
    permittivity_0: float,
    scale_permittivity: float,
    solid_permittivities: Mapping[str, float],
    solid_fraction: Expression | None = None,
) -> Expression:
    """Return the relative permittivity ``eps~_r`` over all of Omega.

    Parameters
    ----------
    solid_permittivities
        Per solid; a material that is neither fluid nor listed is reported and takes ion-free water.
    solid_fraction
        The supplied solid fraction, if any; it replaces the sharp split by a blend.
    """
    # eps_r,f^0 over the scale the fluid permittivity is divided by: 1 exactly.
    ion_free = permittivity_0 / scale_permittivity
    fluid_mask = mesh.Materials(fluid).Mask()
    off_fluid = {
        material for index, material in enumerate(mesh.GetMaterials()) if not fluid_mask[index]
    }
    unassigned = sorted(
        material
        for material in off_fluid
        if material not in solid_permittivities and material not in PERMITTIVITY_EXEMPT
    )
    if unassigned:
        logger.warning(
            "%r has no solid_permittivities entry for %s, so Poisson carries the "
            "ion-free water permittivity eps_r,f^0 there (PHY-03)",
            model_name,
            ", ".join(unassigned),
        )
    named = {material: value / permittivity_0 for material, value in solid_permittivities.items()}
    # Every off-fluid material that is not a named solid is ion-free water.
    water_off_fluid = dict.fromkeys(sorted(off_fluid - set(named)), ion_free)
    sharp: Expression = mesh.MaterialCF({**water_off_fluid, **named}, default=fluid_permittivity)
    if solid_fraction is None:
        return sharp
    # The water branch: the fluid's value where the ions are, eps_r,f^0 where
    # they are not. The solid branch: each element's own eps_p, or its nearest
    # solid's where the transition reaches past the boundary. Written once, in
    # materials.fields: a second copy of the blend here is a second place for it
    # to drift.
    water = mesh.MaterialCF(dict.fromkeys(sorted(off_fluid), ion_free), default=fluid_permittivity)
    return blend(solid_fraction, nearest_solid_permittivity(mesh, named), water)


@dataclass(frozen=True)
class CoupledModel:
    """Poisson with Nernst-Planck, and optionally flow: the ``epnp-ns`` family.

    Parameters
    ----------
    flow
        Whether the Navier-Stokes block is solved; False gives ``pnp``.
    dielectric_gradient_forces
        Assembled together and never alone; a deviation from the validated model, default off.
    velocity_order
        Element order of ``u``; None means ``order``.
    pressure_order
        Element order of ``p``; equal order is selectable only with a stabilisation that permits it.
    """

    electrolyte: Electrolyte
    concentration_M: float = 1.0
    name: str = "epnp-ns"
    flow: bool = True
    variable_density: bool = True
    inertia: bool = True
    dielectric_gradient_forces: bool = False
    log_variables: bool = False
    order: int = 2
    velocity_order: int | None = None
    pressure_order: int = 1
    fluid: str = ELECTROLYTE_DOMAINS
    solid_permittivities: Mapping[str, float] = field(default_factory=dict)
    pressure_constraint: bool = False
    stabilisation: str = "none"

    def __post_init__(self) -> None:
        if self.stabilisation not in registered_stabilisations():
            known = ", ".join(registered_stabilisations())
            raise ValueError(
                f"stabilisation {self.stabilisation!r} is not a registered mode; the available "
                f"modes are {known}. Recording a mode the solver does not apply would make the "
                "FR-25 manifest describe a run that never happened"
            )
        if self.flow:
            problem = inf_sup_problem(
                velocity_order=self.resolved_velocity_order,
                pressure_order=self.pressure_order,
                stabilisation=self.stabilisation,
            )
            if problem is not None:
                raise ValueError(problem)
        if self.pressure_constraint and not self.flow:
            raise ValueError("pressure_constraint has no meaning without a flow block")
        if self.dielectric_gradient_forces and self.log_variables:
            raise ValueError(
                "dielectric_gradient_forces cannot be combined with the NUM-02 log branch: the "
                "permittivity sensitivity d(eps~_r)/d(c~_i) would be differentiated in w_i"
            )

    @property
    def resolved_velocity_order(self) -> int:
        """Return the element order of ``u``: :attr:`velocity_order`, else :attr:`order`."""
        return self.order if self.velocity_order is None else self.velocity_order

    @property
    def stabilisation_model(self) -> StabilisationModel:
        """Return the resolved stabilisation mode, read from the registry on each access."""
        return create_stabilisation(self.stabilisation)

    @property
    def steric(self) -> bool:
        """Whether ``beta_i`` is active; owned by the electrolyte's switches."""
        return self.electrolyte.switches.steric

    @property
    def species(self) -> tuple[str, ...]:
        """Names of the solved ionic species."""
        return tuple(ion.name for ion in self.electrolyte.species)

    @property
    def fields(self) -> tuple[Field, ...]:
        """The solved fields, in the order of the product space."""
        declared = [Field(POTENTIAL, "h1", self.order, None)]
        declared += [
            Field(concentration_field_name(name), "h1", self.order, self.fluid)
            for name in self.species
        ]
        if self.flow:
            declared.append(Field(VELOCITY, "vector_h1", self.resolved_velocity_order, self.fluid))
            declared.append(Field(PRESSURE, "h1", self.pressure_order, self.fluid))
            if self.pressure_constraint:
                declared.append(Field(PRESSURE_MEAN, "number", 0, self.fluid))
        return tuple(declared)

    @property
    def boundary_conditions(self) -> Mapping[str, Mapping[str, str]]:
        """The boundary-condition vocabulary, per field (PHY-09)."""
        vocabulary: dict[str, Mapping[str, str]] = {
            POTENTIAL: {
                "cis": "phi = 0",
                "trans": "phi = V_bias",
                "membrane": "n.D = 0, zero charge",
                "wall": "continuity of n.D",
                "axis": "natural",
            }
        }
        for name in self.species:
            vocabulary[concentration_field_name(name)] = {
                "cis": "c_i = c_bulk",
                "trans": "c_i = c_bulk",
                "wall": "n.J_i = 0, natural",
                "membrane": "n.J_i = 0, natural",
                "axis": "natural",
            }
        if self.flow:
            vocabulary[VELOCITY] = {
                "cis": "sigma.n = 0, natural",
                "trans": "sigma.n = 0, natural",
                "wall": "u = 0",
                "membrane": "u = 0",
                "axis": "u_r = 0 essential, u_z natural",
            }
        return vocabulary

    def essential_boundaries(
        self, boundaries: CoupledBoundaries = DEFAULT_BOUNDARIES
    ) -> dict[str, str]:
        """Return the pattern of every essential condition :meth:`space` imposes."""
        essential = {POTENTIAL: boundaries.potential}
        for name in self.species:
            essential[concentration_field_name(name)] = boundaries.concentration_boundary(name)
        if self.flow:
            essential[VELOCITY] = boundaries.velocity
            essential[VELOCITY_AXIS] = boundaries.velocity_axis
        return essential

    @property
    def scales(self) -> Scales:
        """The scale set of this case, on the mesh's nanometre unit."""
        return mesh_unit_scales(self.electrolyte, self.concentration_M)

    @property
    def provenance(self) -> Mapping[str, Any]:
        """Everything a result manifest must record about the model (FR-25)."""
        return {
            "model": self.name,
            "fields": {
                f.name: {"element": f.element, "order": f.order, "domain": f.domain}
                for f in self.fields
            },
            "switches": {
                "flow": self.flow,
                "variable_density_flow": self.variable_density,
                "inertia": self.inertia,
                "steric": self.steric,
                "dielectric_gradient_forces": self.dielectric_gradient_forces,
                "log_variables": self.log_variables,
                "pressure_constraint": self.pressure_constraint,
            },
            "deviations_from_validated_default": sorted(self._deviations()),
            "elements": {
                "potential": self.order,
                "concentration": self.order,
                "velocity": self.resolved_velocity_order,
                "pressure": self.pressure_order,
            },
            "stabilisation": self.stabilisation,
            # The mode name alone does not identify the operator: ``reference``
            # with ``C_cw = 1`` and ``reference`` with ``C_cw = 0.35`` are
            # different discretisations (FR-25, section 5.3.3).
            "stabilisation_parameters": dict(self.stabilisation_model.parameters),
            "stabilisation_provenance": dict(self.stabilisation_model.provenance),
            "scales": self.scales.summary(),
            "materials": dict(self.electrolyte.provenance),
        }

    def _deviations(self) -> set[str]:
        deviations: set[str] = set()
        if not self.flow:
            deviations.add("physics.flow")
        if not self.variable_density:
            deviations.add("physics.variable_density")
        if not self.inertia:
            deviations.add("physics.inertia")
        if self.dielectric_gradient_forces:
            deviations.add("physics.dielectric_gradient_forces")
        if not self.steric:
            deviations.add("electrolyte.corrections.steric.model")
        return deviations

    def space(self, mesh: Mesh, boundaries: CoupledBoundaries = DEFAULT_BOUNDARIES) -> FESpace:
        """Return the product space of the declared fields, with ``u_r = 0`` on the axis."""
        import ngsolve as ngs

        fluid = mesh.Materials(self.fluid)
        spaces = [ngs.H1(mesh, order=self.order, dirichlet=boundaries.potential)]
        spaces += [
            ngs.H1(
                mesh,
                order=self.order,
                dirichlet=boundaries.concentration_boundary(name),
                definedon=fluid,
            )
            for name in self.species
        ]
        if self.flow:
            spaces.append(
                ngs.VectorH1(
                    mesh,
                    order=self.resolved_velocity_order,
                    dirichlet=boundaries.velocity,
                    dirichletx=boundaries.velocity_axis,
                    definedon=fluid,
                )
            )
            spaces.append(ngs.H1(mesh, order=self.pressure_order, definedon=fluid))
            if self.pressure_constraint:
                spaces.append(ngs.NumberSpace(mesh, definedon=fluid))
        product = spaces[0]
        for component in spaces[1:]:
            product = product * component
        return product

    def _split(self, functions: Sequence[Expression]) -> dict[str, Expression]:
        return {f.name: g for f, g in zip(self.fields, functions, strict=True)}

    def coefficients(
        self, variables: ConcentrationVariables, wall_distance_nm: Expression
    ) -> NondimensionalCoefficients:
        """Return the nondimensional material coefficients for a state."""
        return NondimensionalCoefficients(
            electrolyte=self.electrolyte,
            scales=self.scales,
            concentrations=variables.values,
            wall_distance_nm=wall_distance_nm,
        )

    def concentration_variables(
        self, functions: Mapping[str, Expression]
    ) -> ConcentrationVariables:
        """Return the concentration variables for the current branch."""
        fields = {name: functions[concentration_field_name(name)] for name in self.species}
        if self.log_variables:
            return ConcentrationVariables.logarithmic_branch(fields)
        return ConcentrationVariables.primitive(fields)

    def cell_peclet(
        self, state: GridFunction, wall_distance_nm: Expression
    ) -> dict[str, Expression]:
        """Return ``Pe_K`` per species at ``state``, the cell-Peclet diagnostic.

        Parameters
        ----------
        state
            A grid function on this model's product space, normally the converged one.
        """
        states = self.transport_states(self._split(list(state.components)), wall_distance_nm)
        return {name: species_cell_peclet(species) for name, species in states.items()}

    def transport_states(
        self, functions: Mapping[str, Expression], wall_distance_nm: Expression
    ) -> dict[str, TransportState]:
        """Return one transport state per species, from the solved fields."""
        variables = self.concentration_variables(functions)
        coefficients = self.coefficients(variables, wall_distance_nm)
        return {
            name: self._transport_state(name, functions, variables, coefficients)
            for name in self.species
        }

    def permittivity(
        self,
        mesh: Mesh,
        coefficients: NondimensionalCoefficients,
        *,
        solid_fraction: Expression | None = None,
    ) -> Expression:
        """Return ``eps~_r`` over all of Omega, corrected in the fluid.

        Parameters
        ----------
        solid_fraction
            The supplied solid fraction, if any; it replaces the sharp split by a blend.
        """
        return relative_permittivity_field(
            mesh,
            model_name=self.name,
            fluid=self.fluid,
            fluid_permittivity=coefficients.relative_permittivity(),
            permittivity_0=self.electrolyte.permittivity_0,
            scale_permittivity=coefficients.scales.relative_permittivity,
            solid_permittivities=self.solid_permittivities,
            solid_fraction=solid_fraction,
        )

    def relative_permittivity(self, solution: ModelSolution) -> Expression:
        """Return ``eps~_r`` as the solve used it, at the converged state."""
        values = {field.name: solution.component(field.name) for field in self.fields}
        coefficients = self.coefficients(
            self.concentration_variables(values), solution.wall_distance_nm
        )
        return self.permittivity(
            solution.space.mesh, coefficients, solid_fraction=solution.solid_fraction
        )

    def residual_form(
        self,
        space: FESpace,
        measures: Measures,
        *,
        wall_distance_nm: Expression = SATURATED_WALL_DISTANCE_NM,
        fixed_charge: FixedCharge | None = None,
        solid_fraction: Expression | None = None,
        surface_charge: Expression | None = None,
        surface_charge_boundary: str = "wall",
        sources: Mapping[str, Expression] | None = None,
        state: GridFunction | None = None,
        **kwargs: Option,
    ) -> IntegralTerm:
        """Return the coupled weak residual, written in the trial functions.

        Parameters
        ----------
        measures
            Symmetry and quadrature policy; its element order must match the model's.
        fixed_charge
            The dimensionless protein space charge, if any.
        """
        _reject_unknown(kwargs, f"{self.name!r}.residual_form")
        if measures.element_order != self.order:
            raise ValueError(
                f"measures.element_order is {measures.element_order} but the model is order "
                f"{self.order}; the NUM-07 quadrature bonus is computed from the element order, "
                "so a mismatch under-integrates the 1/r forms it exists to protect"
            )
        mesh = space.mesh
        fluid = mesh.Materials(self.fluid)
        trials = self._split(list(space.TrialFunction()))
        tests = self._split(list(space.TestFunction()))
        sources = dict(sources or {})
        unknown = set(sources) - set(trials)
        if unknown:
            raise ValueError(
                f"sources name fields {', '.join(sorted(unknown))} that {self.name!r} does not "
                f"solve for; it solves {', '.join(trials)}"
            )

        variables = self.concentration_variables(trials)
        coefficients = self.coefficients(variables, wall_distance_nm)
        potential, potential_test = trials[POTENTIAL], tests[POTENTIAL]
        velocity = trials[VELOCITY] if self.flow else None

        stabilisation = self.stabilisation_model
        if stabilisation.terms and state is None:
            raise ValueError(
                f"the {stabilisation.name!r} stabilisation assembles "
                f"{', '.join(stabilisation.terms)} and needs the solve state to evaluate its "
                "parameters at the iterate; pass state=. Building them from the trial functions "
                "instead would put max(0, .) and 1/||grad c~|| into the Jacobian, which the "
                "NUM-16 damping policy is not tuned for"
            )
        # The lagged side, from which every stabilisation parameter is read. When
        # no state is supplied the mode assembles nothing, so the trial side stands
        # in rather than a branch on the mode name (PHY-22).
        lagged = self._split(list(state.components)) if state is not None else trials
        lagged_variables = self.concentration_variables(lagged) if state is not None else variables
        lagged_coefficients = (
            self.coefficients(lagged_variables, wall_distance_nm)
            if state is not None
            else coefficients
        )

        # Poisson over all of Omega; the mobile charge lives on the fluid only.
        residual = poisson_operator(
            potential,
            potential_test,
            measures,
            permittivity=self.permittivity(mesh, coefficients, solid_fraction=solid_fraction),
        )
        residual -= charge_source(
            coefficients.screening * coefficients.ionic_charge_density(),
            potential_test,
            measures,
            definedon=fluid,
        )
        if fixed_charge is not None:
            _check_fixed_charge(fixed_charge)
            residual -= charge_source(
                fixed_charge.density, potential_test, measures, rule_order=fixed_charge.rule_order
            )
        if surface_charge is not None:
            # The Poisson boundary term is +int_Gamma sigma_s v r ds on the
            # right-hand side, so it is subtracted from the residual exactly as
            # the volumetric source is.
            residual -= surface_charge_source(
                surface_charge,
                potential_test,
                measures,
                definedon=mesh.Boundaries(surface_charge_boundary),
            )

        for name in self.species:
            flux = species_flux(
                name,
                coefficients=coefficients,
                variables=variables,
                potential=potential,
                velocity=velocity,
                steric=self.steric,
                dielectric_gradient=self.dielectric_gradient_forces,
            )
            field_name = concentration_field_name(name)
            residual += nernst_planck_residual(flux, tests[field_name], measures, definedon=fluid)
            # Guarded on the capability, not the mode name (PHY-22); a mode with no terms
            # is the one case where the lagged state falls back to the trial side.
            if stabilisation.terms:
                stabilisation_term = stabilisation.transport_term(
                    measures,
                    trial=self._transport_state(name, trials, variables, coefficients),
                    lagged=self._transport_state(
                        name, lagged, lagged_variables, lagged_coefficients
                    ),
                    test=tests[field_name],
                    source=sources.get(field_name),
                    definedon=fluid,
                )
                if stabilisation_term is not None:
                    residual += stabilisation_term

        if self.flow:
            residual += self._flow_residual(
                trials, tests, measures, coefficients, variables, definedon=fluid
            )
            if stabilisation.terms:
                flow_term = stabilisation.flow_term(
                    measures,
                    trial=self._flow_state(trials, coefficients, variables, sources=sources),
                    lagged=self._flow_state(
                        lagged, lagged_coefficients, lagged_variables, sources=sources
                    ),
                    velocity_test=tests[VELOCITY],
                    pressure_test=tests[PRESSURE],
                    definedon=fluid,
                )
                if flow_term is not None:
                    residual += flow_term

        for name, source in sources.items():
            # Poisson is posed on all of Omega and everything else on the fluid,
            # so a source follows its own equation's domain.
            options = {} if name == POTENTIAL else {"definedon": fluid}
            residual -= measures.volume(source * tests[name], **options)
        return residual

    def _transport_state(
        self,
        species: str,
        functions: Mapping[str, Expression],
        variables: ConcentrationVariables,
        coefficients: NondimensionalCoefficients,
    ) -> TransportState:
        return TransportState(
            species=species,
            coefficients=coefficients,
            variables=variables,
            potential=functions[POTENTIAL],
            velocity=functions[VELOCITY] if self.flow else None,
            steric=self.steric,
        )

    def _flow_state(
        self,
        functions: Mapping[str, Expression],
        coefficients: NondimensionalCoefficients,
        variables: ConcentrationVariables,
        *,
        sources: Mapping[str, Expression],
    ) -> FlowState:
        import ngsolve as ngs

        force = (
            -coefficients.screening
            * coefficients.ionic_charge_density()
            * ngs.grad(functions[POTENTIAL])
        )
        if self.dielectric_gradient_forces:
            # The Korteweg-Helmholtz force of PHY-23, which survives the
            # approximate residual: it carries first derivatives only.
            field = ngs.grad(functions[POTENTIAL])
            force = force - 0.5 * (field * field) * permittivity_gradient(coefficients, variables)
        return FlowState(
            coefficients=coefficients,
            velocity=functions[VELOCITY],
            pressure=functions[PRESSURE],
            density=coefficients.mass_density() if self.variable_density else 1.0,
            body_force=force,
            inertia=self.inertia,
            source=sources.get(VELOCITY),
        )

    def _flow_residual(
        self,
        trials: Mapping[str, Expression],
        tests: Mapping[str, Expression],
        measures: Measures,
        coefficients: NondimensionalCoefficients,
        variables: ConcentrationVariables,
        *,
        definedon: Option,
    ) -> IntegralTerm:
        velocity, pressure = trials[VELOCITY], trials[PRESSURE]
        velocity_test, pressure_test = tests[VELOCITY], tests[PRESSURE]
        viscosity = coefficients.viscosity()
        density = coefficients.mass_density() if self.variable_density else None

        residual = viscous_operator(
            velocity, velocity_test, measures, viscosity=viscosity, definedon=definedon
        )
        residual += pressure_term(pressure, velocity_test, measures, definedon=definedon)
        residual += continuity_term(
            velocity, pressure_test, measures, mass_density=density, definedon=definedon
        )
        if self.inertia:
            residual += inertia_term(
                velocity,
                velocity_test,
                measures,
                reynolds=coefficients.reynolds,
                mass_density=density if density is not None else 1.0,
                definedon=definedon,
            )
        residual += electrical_body_force(
            coefficients.ionic_charge_density(),
            trials[POTENTIAL],
            velocity_test,
            measures,
            screening=coefficients.screening,
            definedon=definedon,
        )
        if self.pressure_constraint:
            # int p q_lambda + int lambda q, the saddle-point form of
            # "the mean pressure is prescribed". Without it a solve whose
            # velocity is essential on the whole boundary has a constant
            # pressure null mode, and a direct solver factorises that happily
            # and returns a plausible, useless answer.
            multiplier, multiplier_test = trials[PRESSURE_MEAN], tests[PRESSURE_MEAN]
            residual += measures.volume(
                pressure * multiplier_test + multiplier * pressure_test, definedon=definedon
            )
        if self.dielectric_gradient_forces:
            residual += dielectric_gradient_force(
                trials[POTENTIAL],
                permittivity_gradient(coefficients, variables),
                velocity_test,
                measures,
                definedon=definedon,
            )
        return residual

    def gates(
        self,
        mesh: Mesh,
        state: GridFunction,
        measures: Measures,
        *,
        increment: GridFunction | None = None,
    ) -> tuple[Sequence[Gate], Sequence[Gate]]:
        """Return the state and increment gates for a solve.

        Parameters
        ----------
        increment
            The Newton direction; the increment gates are returned only if it is given.
        """
        fields = self._split(list(state.components))
        fluid_sampler = FieldSampler.shared(
            mesh, coordinates=measures.coordinate_names, materials=self.fluid
        )
        variables = self.concentration_variables(fields)
        concentrations_SI = species_concentrations_SI(self.scales, variables.values)
        diameters = {ion.name: ion.steric_diameter * NM_PER_M for ion in self.electrolyte.species}
        state_gates: list[Gate] = [
            PositivityGate(fluid_sampler, concentrations_SI),
            PackingFractionGate(fluid_sampler, concentrations_SI, diameters_nm=diameters),
        ]
        if increment is None:
            return state_gates, []
        potential_sampler = FieldSampler.shared(mesh, coordinates=measures.coordinate_names)
        potential_increment = self._split(list(increment.components))[POTENTIAL]
        return state_gates, [PotentialIncrementGate(potential_sampler, potential_increment)]

    def solve(
        self,
        mesh: Mesh,
        measures: Measures,
        *,
        boundaries: CoupledBoundaries = DEFAULT_BOUNDARIES,
        potential_values: Expression = 0.0,
        concentration_values: Mapping[str, Expression] | None = None,
        initial_concentrations: Mapping[str, float] | None = None,
        velocity_values: Expression | None = None,
        wall_distance_nm: Expression = SATURATED_WALL_DISTANCE_NM,
        fixed_charge: FixedCharge | None = None,
        solid_fraction: Expression | None = None,
        surface_charge: Expression | None = None,
        surface_charge_boundary: str = "wall",
        sources: Mapping[str, Expression] | None = None,
        initial: ModelSolution | None = None,
        settings: NewtonSettings = DEFAULT_SETTINGS,
        solver: str = DEFAULT_SOLVER,
        callback: Callable[[NewtonStep], None] | None = None,
        **kwargs: Option,
    ) -> ModelSolution:
        """Solve the coupled system by damped Newton, gated at every iterate.

        Parameters
        ----------
        potential_values
            Essential data for phi~, in units of V_T.
        concentration_values
            Essential data for each c~_i, dimensionless; bulk, that is 1, by default.
        velocity_values
            Essential data for u~; zero (no-slip) by default.
        """
        import ngsolve as ngs

        _reject_unknown(kwargs, f"{self.name!r}.solve")
        if initial is not None:
            space = initial.space
            state = ngs.GridFunction(space, name=f"{self.name}_state")
            state.vec.data = initial.state.vec
        else:
            state = self.cold_state(mesh, boundaries, initial_concentrations=initial_concentrations)
            space = state.space
        self._apply_essential(
            state, mesh, boundaries, potential_values, concentration_values, velocity_values
        )

        residual = ngs.BilinearForm(space)
        residual += self.residual_form(
            space,
            measures,
            wall_distance_nm=wall_distance_nm,
            fixed_charge=fixed_charge,
            solid_fraction=solid_fraction,
            surface_charge=surface_charge,
            surface_charge_boundary=surface_charge_boundary,
            sources=sources,
            state=state,
        )
        increment = ngs.GridFunction(space, name=f"{self.name}_increment")
        state_gates, increment_gates = self.gates(mesh, state, measures, increment=increment)
        result = damped_newton(
            residual,
            state,
            settings=settings,
            solver=solver,
            state_gates=state_gates,
            increment=increment,
            increment_gates=increment_gates,
            callback=callback,
        )
        logger.debug("%s converged: %s", self.name, result.summary())
        return ModelSolution(
            model=self,
            space=space,
            state=state,
            newton=result,
            residual=residual,
            wall_distance_nm=wall_distance_nm,
            solid_fraction=solid_fraction,
        )

    def cold_state(
        self,
        mesh: Mesh,
        boundaries: CoupledBoundaries = DEFAULT_BOUNDARIES,
        *,
        initial_concentrations: Mapping[str, float] | None = None,
    ) -> GridFunction:
        """Return a fresh state on this model's space: bulk ions, zero potential and flow."""
        import ngsolve as ngs

        state = ngs.GridFunction(self.space(mesh, boundaries), name=f"{self.name}_state")
        values = initial_concentrations or {}
        fields = self._split(list(state.components))
        for name in self.species:
            bulk = float(values.get(name, 1.0))
            target = math.log(bulk) if self.log_variables else bulk
            fields[concentration_field_name(name)].Set(ngs.CF(target))
        return state

    def _apply_essential(
        self,
        state: GridFunction,
        mesh: Mesh,
        boundaries: CoupledBoundaries,
        potential_values: Expression,
        concentration_values: Mapping[str, Expression] | None,
        velocity_values: Expression | None,
    ) -> None:
        import ngsolve as ngs

        fields = self._split(list(state.components))
        set_boundary_values(
            fields[POTENTIAL], potential_values, mesh.Boundaries(boundaries.potential)
        )
        values = concentration_values or {}
        for name in self.species:
            bulk = values.get(name, 1.0)
            target = ngs.log(ngs.CF(bulk)) if self.log_variables else ngs.CF(bulk)
            set_boundary_values(
                fields[concentration_field_name(name)],
                target,
                mesh.Boundaries(boundaries.concentration_boundary(name)),
            )
        if self.flow and velocity_values is not None:
            set_boundary_values(
                fields[VELOCITY], velocity_values, mesh.Boundaries(boundaries.velocity)
            )


class _SingleFieldModel:
    name: str
    electrolyte: Electrolyte
    concentration_M: float
    order: int

    @property
    def species(self) -> tuple[str, ...]:
        return ()

    @property
    def fields(self) -> tuple[Field, ...]:
        return (Field(POTENTIAL, "h1", self.order, None),)

    @property
    def scales(self) -> Scales:
        return mesh_unit_scales(self.electrolyte, self.concentration_M)

    def essential_boundaries(
        self, boundaries: CoupledBoundaries = DEFAULT_BOUNDARIES
    ) -> dict[str, str]:
        return {POTENTIAL: boundaries.potential}

    def space(self, mesh: Mesh, boundaries: CoupledBoundaries = DEFAULT_BOUNDARIES) -> FESpace:
        import ngsolve as ngs

        return ngs.H1(mesh, order=self.order, dirichlet=boundaries.potential)

    def cold_state(
        self,
        mesh: Mesh,
        boundaries: CoupledBoundaries = DEFAULT_BOUNDARIES,
        *,
        initial_concentrations: Mapping[str, float] | None = None,
    ) -> GridFunction:
        _refuse_concentrations(self.name, initial_concentrations)
        import ngsolve as ngs

        return ngs.GridFunction(self.space(mesh, boundaries), name="phi_tilde")


@dataclass(frozen=True)
class ElectrostaticModel(_SingleFieldModel):
    """``pb`` and ``pb-linear``: one screened field, no transport.

    Parameters
    ----------
    screening
        ``linear`` for Debye-Hueckel, ``sinh`` for nonlinear Poisson-Boltzmann.
    screening_length_nm
        A Debye length stated by the caller, in nm, in place of the case's.
    """

    name: str
    screening: Literal["linear", "sinh"]
    electrolyte: Electrolyte
    concentration_M: float = 1.0
    order: int = 2
    screening_length_nm: float | None = None

    @property
    def boundary_conditions(self) -> Mapping[str, Mapping[str, str]]:
        """The boundary-condition vocabulary, per field (PHY-09)."""
        return {
            POTENTIAL: {
                "cis": "phi = 0",
                "trans": "phi = V_bias",
                "wall": "phi = zeta, or continuity of n.D",
                "membrane": "n.D = 0, zero charge",
                "axis": "natural",
            }
        }

    @property
    def debye_length_nm(self) -> float:
        """``lambda_D`` in nm: :attr:`screening_length_nm` if stated, else the case's."""
        if self.screening_length_nm is not None:
            return self.screening_length_nm
        return self.scales.debye_length_nm

    @property
    def provenance(self) -> Mapping[str, Any]:
        """Everything a result manifest must record about the model (FR-25)."""
        return {
            "model": self.name,
            "fields": {POTENTIAL: {"element": "h1", "order": self.order, "domain": None}},
            "screening": self.screening,
            "stabilisation": "none",
            "stabilisation_parameters": {},
            "stabilisation_provenance": dict(create_stabilisation("none").provenance),
            "deviations_from_validated_default": [],
        }

    def relative_permittivity(self, solution: ModelSolution) -> Expression | None:
        """Return ``None``: the screened models carry no material permittivity."""
        return None

    def residual_form(
        self,
        space: FESpace,
        measures: Measures,
        *,
        debye_length_nm: float | None = None,
        surface_charge: Expression | None = None,
        surface_charge_boundary: str = "wall",
        state: GridFunction | None = None,
        **kwargs: Option,
    ) -> IntegralTerm:
        """Return the weak residual in the trial function; TypeError for an unknown keyword.

        Parameters
        ----------
        debye_length_nm
            Overrides the case's Debye length.
        surface_charge, surface_charge_boundary
            A uniform surface charge, dimensionless, and the boundary carrying it.
        """
        _reject_unknown(kwargs, f"{self.name!r}.residual_form")
        trial, test = space.TnT()
        screening_nm = self.debye_length_nm if debye_length_nm is None else debye_length_nm
        if self.screening == "linear":
            residual = linear_pb_operator(trial, test, measures, debye_length_nm=screening_nm)
        else:
            residual = nonlinear_pb_residual(trial, test, measures, debye_length_nm=screening_nm)
        if surface_charge is not None:
            residual -= surface_charge_source(
                surface_charge,
                test,
                measures,
                definedon=space.mesh.Boundaries(surface_charge_boundary),
            )
        return residual

    def solve(
        self,
        mesh: Mesh,
        measures: Measures,
        *,
        boundaries: CoupledBoundaries = DEFAULT_BOUNDARIES,
        potential_values: Expression = 0.0,
        debye_length_nm: float | None = None,
        surface_charge: float = 0.0,
        surface_charge_boundary: str = "wall",
        initial: ModelSolution | None = None,
        settings: NewtonSettings = DEFAULT_SETTINGS,
        solver: str = DEFAULT_SOLVER,
        **kwargs: Option,
    ) -> ModelSolution:
        """Solve the screened model by the Poisson-Boltzmann solver."""
        import ngsolve as ngs

        _reject_unknown(kwargs, f"{self.name!r}.solve")
        screening_nm = self.debye_length_nm if debye_length_nm is None else debye_length_nm
        state, record = solve_pb_recorded(
            mesh,
            measures,
            debye_length_nm=screening_nm,
            dirichlet=boundaries.potential,
            boundary_values=potential_values,
            surface_charge=surface_charge,
            surface_charge_boundary=surface_charge_boundary,
            nonlinear=self.screening == "sinh",
            order=self.order,
            solver=solver,
            settings=settings,
            initial=None if initial is None else initial.state,
        )
        # The residual is rebuilt rather than returned by ``solve_pb_recorded``, which
        # owns its own; it is written in the same trial function and on the same
        # space, so the two are the same operator.
        residual = ngs.BilinearForm(state.space)
        residual += self.residual_form(
            state.space,
            measures,
            debye_length_nm=screening_nm,
            surface_charge=None if surface_charge == 0.0 else ngs.CF(surface_charge),
            surface_charge_boundary=surface_charge_boundary,
        )
        return ModelSolution(
            model=self, space=state.space, state=state, newton=record, residual=residual
        )


# NGSolve's order estimate does not see the r weight;
# knowledge/06-numerics-fem/02-axisymmetric-weak-forms.md#22-quadrature-verified-experimentally.
RADIAL_WEIGHT_ORDER = 1


@dataclass(frozen=True)
class PoissonModel(_SingleFieldModel):
    """``poisson``: electrostatics over all of Omega, with no mobile ions.

    Parameters
    ----------
    fluid
        Material pattern of the fluid, where the relative permittivity is 1.
    solid_permittivities
        Relative permittivity per solid material.
    """

    electrolyte: Electrolyte
    concentration_M: float = 1.0
    name: str = "poisson"
    order: int = 2
    fluid: str = ELECTROLYTE_DOMAINS
    solid_permittivities: Mapping[str, float] = field(default_factory=dict)

    @property
    def boundary_conditions(self) -> Mapping[str, Mapping[str, str]]:
        """The boundary-condition vocabulary, per field (PHY-09)."""
        return {
            POTENTIAL: {
                "cis": "phi = 0",
                "trans": "phi = V_bias",
                "membrane": "n.D = 0, zero charge",
                "wall": "continuity of n.D",
                "axis": "natural",
            }
        }

    @property
    def provenance(self) -> Mapping[str, Any]:
        """Everything a result manifest must record about the model (FR-25)."""
        return {
            "model": self.name,
            "fields": {POTENTIAL: {"element": "h1", "order": self.order, "domain": None}},
            "fluid": self.fluid,
            "fluid_permittivity": "eps_r,f^0, ion-free water (author ruling 13)",
            "solid_permittivities": dict(sorted(self.solid_permittivities.items())),
            "scales": self.scales.summary(),
            "stabilisation": "none",
            "stabilisation_parameters": {},
            "stabilisation_provenance": dict(create_stabilisation("none").provenance),
            "deviations_from_validated_default": [],
        }

    def permittivity(self, mesh: Mesh, *, solid_fraction: Expression | None = None) -> Expression:
        """Return ``eps~_r`` over all of Omega: 1 in the fluid, each solid its own ratio."""
        scale = self.scales.relative_permittivity
        return relative_permittivity_field(
            mesh,
            model_name=self.name,
            fluid=self.fluid,
            fluid_permittivity=self.electrolyte.permittivity_0 / scale,
            permittivity_0=self.electrolyte.permittivity_0,
            scale_permittivity=scale,
            solid_permittivities=self.solid_permittivities,
            solid_fraction=solid_fraction,
        )

    def relative_permittivity(self, solution: ModelSolution) -> Expression:
        """Return ``eps~_r`` with the solid fraction the solve used."""
        return self.permittivity(solution.space.mesh, solid_fraction=solution.solid_fraction)

    def _check_order(self, measures: Measures) -> None:
        if measures.element_order != self.order:
            raise ValueError(
                f"measures.element_order is {measures.element_order} but {self.name!r} is order "
                f"{self.order}; the NUM-07 quadrature bonus is computed from the element order"
            )

    def residual_form(
        self,
        space: FESpace,
        measures: Measures,
        *,
        fixed_charge: FixedCharge | None = None,
        solid_fraction: Expression | None = None,
        surface_charge: Expression | None = None,
        surface_charge_boundary: str = "wall",
        state: GridFunction | None = None,
        **kwargs: Option,
    ) -> IntegralTerm:
        """Return the Poisson residual ``int eps~ grad(phi~).grad(v) r - int rho~_pore v r``."""
        _reject_unknown(kwargs, f"{self.name!r}.residual_form")
        self._check_order(measures)
        trial, test = space.TnT()
        permittivity = self.permittivity(space.mesh, solid_fraction=solid_fraction)
        residual = poisson_operator(
            trial, test, measures, permittivity=permittivity, extra_order=RADIAL_WEIGHT_ORDER
        )
        if fixed_charge is not None:
            _check_fixed_charge(fixed_charge)
            # An explicit rule replaces the bonus, so the r-weight order is added only
            # where NGSolve's estimate is still the base.
            residual -= charge_source(
                fixed_charge.density,
                test,
                measures,
                rule_order=fixed_charge.rule_order,
                extra_order=0 if fixed_charge.rule_order is not None else RADIAL_WEIGHT_ORDER,
            )
        if surface_charge is not None:
            residual -= surface_charge_source(
                surface_charge,
                test,
                measures,
                definedon=space.mesh.Boundaries(surface_charge_boundary),
            )
        return residual

    def solve(
        self,
        mesh: Mesh,
        measures: Measures,
        *,
        boundaries: CoupledBoundaries = DEFAULT_BOUNDARIES,
        potential_values: Expression = 0.0,
        fixed_charge: FixedCharge | None = None,
        solid_fraction: Expression | None = None,
        surface_charge: Expression | None = None,
        surface_charge_boundary: str = "wall",
        initial: ModelSolution | None = None,
        settings: NewtonSettings = DEFAULT_SETTINGS,
        solver: str = DEFAULT_SOLVER,
        **kwargs: Option,
    ) -> ModelSolution:
        """Solve the linear problem once with the direct solver, as one Newton step."""
        import ngsolve as ngs

        _reject_unknown(kwargs, f"{self.name!r}.solve")
        self._check_order(measures)
        space = self.space(mesh, boundaries)
        state = ngs.GridFunction(space, name="phi_tilde")
        if initial is not None:
            state.vec.data = initial.state.vec
        set_boundary_values(state, potential_values, mesh.Boundaries(boundaries.potential))
        residual = ngs.BilinearForm(space)
        residual += self.residual_form(
            space,
            measures,
            fixed_charge=fixed_charge,
            solid_fraction=solid_fraction,
            surface_charge=surface_charge,
            surface_charge_boundary=surface_charge_boundary,
        )
        # Linear, so one undamped step from any state with the right essential
        # data is the solution: J delta = -R(u), with R(u) = A u - f.
        residual.AssembleLinearization(state.vec)
        rhs = state.vec.CreateVector()
        residual.Apply(state.vec, rhs)
        rhs.data *= -1.0
        correction = state.vec.CreateVector()
        correction[:] = 0.0
        solve_correction(residual.mat, rhs, correction, space.FreeDofs(), solver=solver)
        state.vec.data += correction
        return ModelSolution(
            model=self, space=space, state=state, residual=residual, solid_fraction=solid_fraction
        )


def _refuse_concentrations(name: str, initial_concentrations: Mapping[str, float] | None) -> None:
    if initial_concentrations is not None:
        raise TypeError(
            f"{name!r} solves no concentrations, so initial_concentrations has no meaning for it"
        )


ModelBuilder: TypeAlias = Callable[..., PhysicsModel]


@dataclass(frozen=True)
class _Registration:
    builder: ModelBuilder
    declaration: ModelDeclaration


_REGISTRY: dict[str, _Registration] = {}


def register_model(name: str, builder: ModelBuilder, declaration: ModelDeclaration) -> None:
    """Register a physics model under ``name``, with what it admits (section 5.4.3)."""
    if name in _REGISTRY:
        raise ValueError(f"physics model {name!r} is already registered")
    if LADDER_STRATEGY in declaration.strategies and name not in LADDER_TARGETS:
        raise ValueError(
            f"physics model {name!r} declares numerics.continuation {LADDER_STRATEGY!r}, but "
            f"the NUM-18 ladder is a path through named models and ends at "
            f"{' or '.join(LADDER_TARGETS)} only (section 6.5); declare strategies=('none',)"
        )
    _REGISTRY[name] = _Registration(builder=builder, declaration=declaration)


def registered_models() -> tuple[str, ...]:
    """Return every selectable model name, sorted."""
    return tuple(sorted(_REGISTRY))


def _registration(name: str) -> _Registration:
    try:
        return _REGISTRY[name]
    except KeyError:
        known = ", ".join(registered_models())
        raise KeyError(f"unknown physics model {name!r}; registered models are {known}") from None


def declaration(name: str) -> ModelDeclaration:
    """Return what the model registered as ``name`` admits; KeyError if unregistered."""
    return _registration(name).declaration


def create(name: str, **kwargs: Option) -> PhysicsModel:
    """Build the physics model registered as ``name``; ValueError on a name mismatch."""
    model = _registration(name).builder(**kwargs)
    if model.name != name:
        raise ValueError(
            f"the builder registered as {name!r} built a model named {model.name!r}; the "
            "declaration is found by the built model's own name, so the two must agree "
            "(section 5.4.3)"
        )
    return model


def build_case_model(
    model: str, electrolyte: Electrolyte, concentration_M: float, options: Mapping[str, Option]
) -> PhysicsModel:
    """Build the named model at a case's operating point, importing no backend."""
    return create(model, electrolyte=electrolyte, concentration_M=concentration_M, **options)


def case_model(resolved: ResolvedCase) -> PhysicsModel:
    """Build a resolved case's model at its operating point."""
    return build_case_model(
        resolved.model, resolved.electrolyte, resolved.concentration_M, resolved.model_options
    )


def solves_transport(model: PhysicsModel) -> bool:
    """Return whether ``model`` solves ionic transport, by its declaration."""
    if model.name in _REGISTRY:
        return _REGISTRY[model.name].declaration.transport
    return isinstance(model, CoupledModel)


def transport_model(subject: PhysicsModel | ModelSolution) -> TransportModel:
    """Return the model, or the solution's model, as a transport model; TypeError otherwise."""
    model = subject.model if isinstance(subject, ModelSolution) else subject
    if not solves_transport(model):
        raise TypeError(
            f"{model.name!r} solves no ionic transport, so it has no species, no flux and no "
            "current; the quantities of NUM-27 and NUM-28 are defined for a model that declares "
            "transport"
        )
    return cast(TransportModel, model)


if TYPE_CHECKING:  # pragma: no cover - checked by mypy, never executed

    def _coupled_is_transport(model: CoupledModel) -> TransportModel:
        return model

    def _models_are_physics(
        coupled: CoupledModel, screened: ElectrostaticModel, poisson: PoissonModel
    ) -> tuple[PhysicsModel, PhysicsModel, PhysicsModel]:
        return coupled, screened, poisson


def _coupled_electrolyte(
    electrolyte: Electrolyte | None, corrections: str, classical: bool
) -> Electrolyte:
    if electrolyte is not None:
        # ``with_switches``, not ``replace``: the corrections are resolved at
        # construction and every property reads the resolved model, so replacing
        # the switches alone would return an electrolyte that calls itself
        # classical and evaluates the full correction set.
        if classical:
            return electrolyte.with_switches(CorrectionSwitches.classical())
        return electrolyte
    switches = (
        CorrectionSwitches.classical() if classical else CorrectionSwitches.for_model(corrections)
    )
    return Electrolyte.from_parameter_file(corrections, switches=switches)


def _build_epnp_ns(
    *,
    electrolyte: Electrolyte | None = None,
    corrections: str = "willems2020_nacl",
    **kwargs: Option,
) -> PhysicsModel:
    return CoupledModel(
        electrolyte=_coupled_electrolyte(electrolyte, corrections, classical=False),
        name="epnp-ns",
        **kwargs,
    )


def _build_pnp_ns(
    *,
    electrolyte: Electrolyte | None = None,
    corrections: str = "willems2020_nacl",
    **kwargs: Option,
) -> PhysicsModel:
    return CoupledModel(
        electrolyte=_coupled_electrolyte(electrolyte, corrections, classical=True),
        name="pnp-ns",
        **kwargs,
    )


def _build_pnp(
    *,
    electrolyte: Electrolyte | None = None,
    corrections: str = "willems2020_nacl",
    classical: bool = False,
    **kwargs: Option,
) -> PhysicsModel:
    return CoupledModel(
        electrolyte=_coupled_electrolyte(electrolyte, corrections, classical=classical),
        name="pnp",
        flow=False,
        **kwargs,
    )


def _symmetric_monovalent(name: str, electrolyte: Electrolyte) -> Electrolyte:
    valences = sorted(ion.valence for ion in electrolyte.species)
    if valences != [-1, 1]:
        carried = ", ".join(f"{ion.name} (z = {ion.valence:+d})" for ion in electrolyte.species)
        raise ValueError(
            f"{name!r} is posed for a symmetric monovalent salt, for which its Debye length and "
            f"its screening term are exact; this electrolyte carries {carried}"
        )
    return electrolyte


def _screened_builder(name: str, screening: Literal["linear", "sinh"]) -> ModelBuilder:
    def build(
        *,
        electrolyte: Electrolyte | None = None,
        corrections: str = "willems2020_nacl",
        concentration_M: float = 1.0,
        order: int = 2,
        debye_length_nm: float | None = None,
        **kwargs: Option,
    ) -> PhysicsModel:
        _reject_unknown(kwargs, f"the {name!r} builder")
        resolved = (
            electrolyte if electrolyte is not None else Electrolyte.from_parameter_file(corrections)
        )
        if debye_length_nm is None:
            resolved = _symmetric_monovalent(name, resolved)
        elif not (math.isfinite(debye_length_nm) and debye_length_nm > 0.0):
            raise ValueError(
                f"{name!r} was given debye_length_nm={debye_length_nm!r}; a screening length is "
                "finite and positive"
            )
        return ElectrostaticModel(
            name=name,
            screening=screening,
            electrolyte=resolved,
            concentration_M=concentration_M,
            order=order,
            screening_length_nm=debye_length_nm,
        )

    return build


def _build_poisson(
    *,
    electrolyte: Electrolyte | None = None,
    corrections: str = "willems2020_nacl",
    concentration_M: float = 1.0,
    order: int = 2,
    solid_permittivities: Mapping[str, float] | None = None,
    **kwargs: Option,
) -> PhysicsModel:
    _reject_unknown(kwargs, "the 'poisson' builder")
    return PoissonModel(
        electrolyte=(
            electrolyte if electrolyte is not None else Electrolyte.from_parameter_file(corrections)
        ),
        concentration_M=concentration_M,
        order=order,
        solid_permittivities=dict(solid_permittivities or {}),
    )


_BOTH: tuple[bool, ...] = (False, True)

_COUPLED_OPTIONS: tuple[str, ...] = (
    "solid_permittivities",
    "variable_density",
    "inertia",
    "dielectric_gradient_forces",
    "order",
    "velocity_order",
    "pressure_order",
    "stabilisation",
)

_QUANTITIES: tuple[str, ...] = (
    "current",
    "transport_numbers",
    "rectification",
    "eof_rate",
    "analyte_force",
)

CORRECTION_PROPERTIES_ALL = ("diffusivity", "mobility", "permittivity", "viscosity", "density")
PARTS = ("model", "concentration", "wall")
CORRECTION_LEAVES = frozenset(
    {f"electrolyte.corrections.{p}.{k}" for p in CORRECTION_PROPERTIES_ALL for k in PARTS}
    | {"electrolyte.corrections.steric.model", "electrolyte.driver"}
)
WALL_DISTANCE_LEAVES = frozenset(
    {"numerics.wall_distance.sources", "numerics.wall_distance.max_distance_nm"}
)
VELOCITY_PRESSURE = frozenset({"numerics.elements.u", "numerics.elements.p"})
ELECTROSTATIC = (
    CORRECTION_LEAVES
    | VELOCITY_PRESSURE
    | WALL_DISTANCE_LEAVES
    | frozenset({"numerics.stabilisation"})
)
LINEAR = frozenset({"numerics.nonlinear.max_iter", "numerics.nonlinear.rtol"})

_COUPLED = ModelDeclaration(
    options=(*_COUPLED_OPTIONS, "flow"),
    switches=dict.fromkeys(SWITCHES, _BOTH),
    solids=True,
    coefficients=COEFFICIENTS,
    wall_distance=True,
    strategies=(LADDER_STRATEGY, "none"),
    quantities=_QUANTITIES,
    transport=True,
    reports_newton=True,
)

_ELECTROSTATIC_SWITCHES: dict[str, tuple[bool, ...]] = {
    "flow": (False,),
    "variable_density": (False,),
    "inertia": (False,),
    "dielectric_gradient_forces": (False,),
}

register_model("epnp-ns", _build_epnp_ns, _COUPLED)
register_model(
    "pnp-ns",
    _build_pnp_ns,
    replace(
        _COUPLED,
        switches={
            **_COUPLED.switches,
            "variable_density": (True,),
            "dielectric_gradient_forces": (False,),
        },
        unread=CORRECTION_LEAVES | WALL_DISTANCE_LEAVES,
    ),
)
register_model(
    "pnp",
    _build_pnp,
    replace(
        _COUPLED,
        options=_COUPLED_OPTIONS,
        switches={
            **dict.fromkeys(SWITCHES, _BOTH),
            "flow": (False,),
            "variable_density": (False,),
            "inertia": (False,),
        },
        strategies=("none",),
        quantities=("current", "transport_numbers", "rectification"),
        unread=frozenset(
            {f"electrolyte.corrections.{p}.{k}" for p in ("viscosity", "density") for k in PARTS}
            | VELOCITY_PRESSURE
        ),
    ),
)
register_model(
    "pb",
    _screened_builder("pb", "sinh"),
    ModelDeclaration(
        options=("order",),
        switches=_ELECTROSTATIC_SWITCHES,
        solids=False,
        unread=ELECTROSTATIC,
    ),
)
register_model(
    "pb-linear",
    _screened_builder("pb-linear", "linear"),
    ModelDeclaration(
        options=("order",),
        switches=_ELECTROSTATIC_SWITCHES,
        solids=False,
        unread=ELECTROSTATIC | LINEAR,
    ),
)
register_model(
    "poisson",
    _build_poisson,
    ModelDeclaration(
        options=("order", "solid_permittivities"),
        switches=_ELECTROSTATIC_SWITCHES,
        solids=True,
        coefficients=COEFFICIENTS,
        unread=ELECTROSTATIC | LINEAR | frozenset({"electrolyte.concentration_M"}),
    ),
)

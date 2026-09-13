"""The physics-model registry (PHY-21, PHY-22, FR-20, section 5.4.3).

A physics model is named by string in the case file and resolved here. It
declares its field set, its weak-form contributions, its boundary-condition
vocabulary and its default solve strategy; the geometry, mesh, charge, solver,
post-processing, sweep and provenance layers know nothing else about it, which
is what FR-20 asks for.

The registry follows :mod:`nanopnp.materials.models` deliberately, down to the
error message that lists the known names. The two levels of pluggability of
section 5.5 are then the same shape at both levels: a correction is a data file,
a physics model is one class.

**``pnp-ns`` is a configuration of ``epnp-ns``, not a second code path.** Both
resolve to the same :class:`CoupledModel`; what differs is that every correction
of the electrolyte is the registered ``none`` model and ``steric`` is off, which
is exactly the reduction PHY-21 states. The same holds for ``pnp``, which is the
coupled model with the flow block absent. A correction-by-correction ablation is
therefore a sweep over configurations rather than a rebuild, and that is the
project's primary differential-testing instrument (section 7.4).
"""

from __future__ import annotations

import logging
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, TypeAlias

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
from nanopnp.materials.electrolyte import CorrectionSwitches, Electrolyte
from nanopnp.materials.fields import blend
from nanopnp.mesh.primitives import ELECTROLYTE_DOMAINS, PERMITTIVITY_EXEMPT
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
from nanopnp.physics.measures import Measures
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
from nanopnp.solve.gates import (
    FieldSampler,
    Gate,
    PackingFractionGate,
    PositivityGate,
    PotentialIncrementGate,
)
from nanopnp.solve.linear import DEFAULT_SOLVER, solve_linear
from nanopnp.solve.newton import (
    DEFAULT_SETTINGS,
    NewtonResult,
    NewtonSettings,
    NewtonStep,
    damped_newton,
)

__all__ = [
    "DEFAULT_BOUNDARIES",
    "PRESSURE_MEAN",
    "CoupledBoundaries",
    "CoupledModel",
    "ElectrostaticModel",
    "Field",
    "ModelSolution",
    "PhysicsModel",
    "create",
    "equal_order_stabilisations",
    "inf_sup_problem",
    "register",
    "registered_models",
    "registered_stabilisations",
]

logger = logging.getLogger(__name__)

ElementKind: TypeAlias = Literal["h1", "vector_h1", "number"]
"""The element families a field may be discretised with (NUM-01)."""

POTENTIAL = "potential"
"""Name of the potential field, shared by every model."""

VELOCITY = "velocity"
PRESSURE = "pressure"
PRESSURE_MEAN = "pressure_mean"
"""Name of the scalar multiplier fixing the pressure level; see ``pressure_constraint``."""


def equal_order_stabilisations() -> tuple[str, ...]:
    """Return the registered modes that permit an equal-order velocity-pressure pair.

    Read off each mode's own ``permits_equal_order`` rather than listed, so
    :func:`inf_sup_problem` can name the mode that would permit the pair instead
    of merely refusing it (NUM-03).

    Queried live, like :func:`registered_stabilisations` itself: a snapshot taken at
    import would refuse a mode registered afterwards — an out-of-tree variant, or a
    retuned ``C_cw`` — which is a gate failing on a mode that *is* implemented.
    """
    return tuple(
        name
        for name in registered_stabilisations()
        if create_stabilisation(name).permits_equal_order
    )


def inf_sup_problem(*, velocity_order: int, pressure_order: int, stabilisation: str) -> str | None:
    """Return why this velocity-pressure-mode triple is inadmissible, or ``None``.

    NUM-03 specifies the Taylor-Hood pair ``P2/P1``, and allows an equal-order
    pair only together with the flow stabilisation of section 6.4.2 — the
    pressure-test piece of the GLS operator is what makes ``P1/P1`` legal, and
    without it the discrete inf-sup condition fails and the pressure carries a
    checkerboard mode the solve will happily converge to.

    One implementation, two callers: :meth:`CoupledModel.__post_init__` gates the
    model and :meth:`nanopnp.io.case.CaseDocument` gates the case file, so that a
    case is refused at validation rather than after the continuation ladder has
    been built. Two separate copies of the condition could disagree about which
    pairs are admissible, and the one that mattered would be whichever ran first.

    Parameters
    ----------
    velocity_order, pressure_order
        The resolved polynomial orders of ``u`` and ``p``.
    stabilisation
        Registered mode name. An unregistered name is **not** this function's
        refusal to make: it returns ``None``, and the caller's own registry check
        reports it.

    Returns
    -------
    str or None
        The clause for the caller's message, or ``None`` when the pair is
        admissible.
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


def _reject_unknown(kwargs: Mapping[str, Option], where: str) -> None:
    """Raise on keywords a model does not understand.

    The :class:`PhysicsModel` protocol declares ``**kwargs`` so that models with
    different vocabularies satisfy one interface (FR-20). That freedom must not
    become silence: a case file naming ``debye_length_nm`` for a coupled model,
    or ``tractions`` for Poisson-Boltzmann, has asked for something the model
    will not do, and dropping the keyword would run the wrong problem.

    Raises
    ------
    TypeError
        If any keyword is left over.
    """
    if kwargs:
        raise TypeError(f"{where} got unexpected keyword(s) {', '.join(sorted(kwargs))}")


@dataclass(frozen=True)
class Field:
    """One solved field of a model (NUM-01, NUM-03).

    Parameters
    ----------
    name
        Field name, used as the key of source terms and of the solution
        accessors.
    element
        Element family.
    order
        Polynomial degree. Recorded in the run provenance, as NUM-03 requires.
    domain
        Material-name regular expression the field lives on, or ``None`` for the
        whole domain. Poisson is solved over all of ``Omega`` including protein
        and membrane; Nernst-Planck and the flow are solved on the fluid only
        (PHY-03).
    """

    name: str
    element: ElementKind
    order: int
    domain: str | None = None


@dataclass(frozen=True)
class CoupledBoundaries:
    """The boundary-name vocabulary a coupled solve is posed on (PHY-09).

    Parameters
    ----------
    potential
        Boundaries carrying an essential condition on ``phi``.
    concentration
        Boundaries carrying ``c_i = c_bulk``, either shared by every species or
        given per species. A benchmark needs the per-species form — the 1D
        limiting-current problem of VER-16 blocks the anion at the electrode
        while the cation is consumed there — and the reference case does not.
    velocity
        Boundaries carrying no-slip ``u = 0``.
    velocity_axis
        The axis, carrying ``u_r = 0`` and nothing else. It is a separate entry
        because it constrains one component only: ``u_z``, ``phi`` and ``c_i``
        are natural there and imposing them is a modelling error (NUM-06).
    """

    potential: str = "cis|trans"
    concentration: str | Mapping[str, str] = "cis|trans"
    velocity: str = "wall|membrane"
    velocity_axis: str = "axis"

    def concentration_boundary(self, species: str) -> str:
        """Return the boundaries carrying essential data for one species.

        Raises
        ------
        KeyError
            If a per-species mapping omits the species. There is deliberately no
            fallback: a missing entry would leave that species with no essential
            condition anywhere, and a pure-Neumann Nernst-Planck equation has a
            constant null mode that a direct solver factorises without complaint
            (see ``.knowledge/06-numerics-fem.md`` section 8.1).
        """
        if isinstance(self.concentration, str):
            return self.concentration
        try:
            return self.concentration[species]
        except KeyError:
            known = ", ".join(sorted(self.concentration))
            raise KeyError(
                f"no concentration boundary for {species!r}; the mapping names {known}"
            ) from None


DEFAULT_BOUNDARIES = CoupledBoundaries()
"""The boundary vocabulary of the analytic pore geometry of ``mesh/primitives``."""


@dataclass
class ModelSolution:
    """A converged state and the record of how it was reached.

    Parameters
    ----------
    model
        The model that produced it.
    space
        The finite-element space, kept so a warm start can reuse it.
    state
        The solution grid function.
    newton
        The convergence record, or ``None`` for a linear model.
    residual
        The assembled form the state solves, kept so the NUM-25 reaction flux
        can be taken without rebuilding it. Rebuilding is not merely wasteful:
        a coupled residual reassembled without the *same* ``wall_distance_nm``
        is a different operator, and the flux taken against it is then wrong
        with no diagnostic at all. Carrying the form removes that trap.
    wall_distance_nm
        The PHY-02 distance field the residual was assembled with, so that a
        consumer rebuilding any part of the model — the NUM-24 indicator form
        rebuilds ``J~_i`` — reproduces the coefficients exactly.
    """

    model: PhysicsModel
    space: FESpace
    state: GridFunction
    newton: NewtonResult | None = None
    residual: AssembledForm | None = None
    wall_distance_nm: Expression = SATURATED_WALL_DISTANCE_NM

    def component(self, name: str) -> Expression:
        """Return one field of the solution by name.

        Raises
        ------
        KeyError
            If the model does not solve for that field; the message lists the
            fields it does solve for.
        """
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
        """Return the dimensionless concentration ``c~_i`` of one species.

        In the NUM-02 log branch the solved variable is ``w_i`` and the
        concentration is ``exp(w_i)``; this returns the concentration either
        way, so a caller reading a result never has to know which branch ran.
        """
        import ngsolve as ngs

        field = self.component(concentration_field_name(species))
        if isinstance(self.model, CoupledModel) and self.model.log_variables:
            return ngs.exp(field)
        return field


def concentration_field_name(species: str) -> str:
    """Return the field name holding one species' concentration."""
    return f"c_{species}"


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
    def boundary_conditions(self) -> Mapping[str, Mapping[str, str]]:
        """The boundary-condition vocabulary, per field (PHY-09)."""
        ...

    @property
    def provenance(self) -> Mapping[str, Any]:
        """Everything a result manifest must record about the model (FR-25)."""
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
        """Return an admissible fresh state on this model's space.

        Part of the protocol because the continuation ladder (NUM-18) transfers
        a solution onto a *larger* field set and must fill the new fields from
        something the model itself calls admissible — a cold start at
        ``c~_i = 0`` fails the NUM-17 positivity gate before Newton takes a step.
        """
        ...

    def residual_form(self, space: FESpace, measures: Measures, **kwargs: Option) -> IntegralTerm:
        """Return the weak residual, written in the trial functions."""
        ...

    def solve(self, mesh: Mesh, measures: Measures, **kwargs: Option) -> ModelSolution:
        """Solve the model with its default strategy."""
        ...


@dataclass(frozen=True)
class CoupledModel:
    """Poisson + Nernst-Planck (+ flow), the ``epnp-ns`` family (PHY-21).

    Parameters
    ----------
    electrolyte
        Reference properties and the correction model per property. It also owns
        the ``steric`` switch, so that a model and its electrolyte cannot
        disagree about whether ``beta_i`` is active.
    concentration_M
        Bulk concentration ``c_0``, in mol/L; the concentration scale.
    name
        Registered name.
    flow
        Whether the Navier-Stokes block is solved. ``False`` is ``pnp``.
    variable_density
        Whether continuity carries ``rho~`` and inertia is weighted by it
        (PHY-07). ``False`` is constant-density Stokes/NS.
    inertia
        Whether the convective momentum term is assembled. The reference model
        retained it at ``Re`` of order 1e-4 (PHY-22).
    dielectric_gradient_forces
        Whether the Korteweg-Helmholtz body force and the dielectric-decrement
        Nernst-Planck term are assembled, **together and never one alone**
        (PHY-23). A deviation from the validated model; default off.
    log_variables
        Whether the NUM-02 log branch ``c~_i = exp(w_i)`` is used.
    order
        Element order of ``phi`` and ``c_i``, and of ``u`` unless
        ``velocity_order`` overrides it.
    velocity_order
        Element order of ``u``. ``None`` means ``order``, which is the two-order
        model every case before WP12 was written against; the reference
        configuration of section 7.4 is ``phi`` and ``c`` at P2 with ``u`` and
        ``p`` at P1, which needs the third order (NUM-03).
    pressure_order
        Element order of ``p``. The Taylor-Hood pair
        ``velocity_order``/``velocity_order - 1`` is inf-sup stable and needs no
        pressure stabilisation of its own; equal order is selectable only with the
        flow stabilisation of section 6.4.2, which the ``reference`` mode supplies
        (NUM-03).
    fluid
        Material-name regular expression selecting the domains Nernst-Planck and
        the flow are solved on.
    solid_permittivities
        Relative permittivity per solid material, ``{"membrane": 3.2}``. The
        fluid takes the corrected ``eps_r,f(<c>)``.
    pressure_constraint
        Whether to carry a scalar multiplier fixing the mean pressure. Needed
        only when the velocity is essential on the whole flow boundary, which
        leaves the pressure determined up to a constant and the Jacobian
        singular; the analytic pore has traction-free reservoir caps and needs
        no such constraint. The target mean is supplied as a source on the
        :data:`PRESSURE_MEAN` field.
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
    """The residual stabilisation mode in force (NUM-11, NUM-13, §5.3.3, §6.4).

    ``"none"`` is the unstabilised Galerkin discretisation of this phase. The
    reference COMSOL model ran with streamline and crosswind stabilisation *on*
    in both transport and flow (§6.4, §7.4), so a number recorded without its
    stabilisation mode is not comparable to it: Phase 1's COMSOL comparison must
    attribute a per-cent discrepancy to stabilised-vs-unstabilised rather than to
    a bug, and a manifest that cannot state the mode cannot do that. Carrying it
    here, sourced from the model rather than written as a literal into the
    manifest, is what lets NUM-14's stabilised mode populate the provenance
    automatically when it is added.
    """

    def __post_init__(self) -> None:
        """Reject a configuration that cannot be assembled.

        Raises
        ------
        ValueError
            If the velocity-pressure pair is equal-order in a mode that supplies
            no flow stabilisation, which NUM-03 refuses, if
            ``dielectric_gradient_forces`` is combined with the log branch, where
            the permittivity sensitivity would come back in the wrong variable, or
            if ``stabilisation`` names a mode that is not registered.
        """
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

    # -- declaration -------------------------------------------------------

    @property
    def resolved_velocity_order(self) -> int:
        """Return the element order of ``u``: :attr:`velocity_order`, else :attr:`order`.

        Defaulting rather than duplicating keeps every case written before the
        third order existed byte-identical: ``velocity_order=None`` reproduces the
        two-order model exactly, field set and provenance included (NUM-03).
        """
        return self.order if self.velocity_order is None else self.velocity_order

    @property
    def stabilisation_model(self) -> StabilisationModel:
        """Return the resolved stabilisation mode (NUM-11, NUM-13, PHY-22).

        Resolved from the registry on every access rather than stored, because the
        model is frozen and the mode is a small immutable value object; the cost is
        a dataclass construction. Selecting ``none`` returns the entry that
        assembles nothing, which is why :meth:`residual_form` carries no ``if`` on
        the mode name.
        """
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
    def fields(self) -> tuple[Field, ...]:  # noqa: D102 - documented on the protocol
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
    def boundary_conditions(self) -> Mapping[str, Mapping[str, str]]:  # noqa: D102
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

    @property
    def scales(self) -> Scales:
        """The NUM-09 scale set of this case, on the mesh's nanometre unit."""
        return mesh_unit_scales(self.electrolyte, self.concentration_M)

    @property
    def provenance(self) -> Mapping[str, Any]:  # noqa: D102
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
        """Return the switches *this model* holds that deviate from PHY-22.

        Named by their case-file path, and narrowed to the switches the model
        object actually carries. The manifest's authority on "every switch set
        away from the validated default" is
        :func:`nanopnp.io.defaults.deviations`, which diffs the whole case
        against ``VALIDATED_DEFAULT_CASE`` and so also sees the correction
        switches, the solver settings and the boundary conditions this object
        knows nothing about. ``physics/`` must not import ``io/`` (section 5.4.1),
        so the two computations are independent by construction and
        ``tests/tier1/test_manifest.py`` asserts they agree on the overlap: two
        records that must agree, with a test that says so, beats one that
        silently under-reports.

        ``log_variables`` is not in the overlap: it is a numerics choice with no
        case-file field, and it is reported under ``switches`` in
        :attr:`provenance` rather than pretending to a path.
        """
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

    # -- discretisation ----------------------------------------------------

    def space(self, mesh: Mesh, boundaries: CoupledBoundaries = DEFAULT_BOUNDARIES) -> FESpace:
        """Return the product space of the declared fields.

        The axis carries ``u_r = 0`` and nothing else, which NGSolve expresses as
        ``dirichletx`` on the vector space; ``phi`` and ``c_i`` are left natural
        there (NUM-06).
        """
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
        """Return the trial or test functions keyed by field name."""
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
        """Return the concentration variables of NUM-02 for the current branch."""
        fields = {name: functions[concentration_field_name(name)] for name in self.species}
        if self.log_variables:
            return ConcentrationVariables.logarithmic_branch(fields)
        return ConcentrationVariables.primitive(fields)

    def cell_peclet(
        self, state: GridFunction, wall_distance_nm: Expression
    ) -> dict[str, Expression]:
        """Return ``Pe_K`` per species at ``state``, for the NUM-12 diagnostic.

        Built from the same :class:`~nanopnp.physics.stabilisation.TransportState`
        the stabilisation terms read their parameters from, so the number the
        diagnostic reports is the one the mode was formed on rather than a second
        expression that could drift from it. There is no ``grad(phi~)`` before a
        solve, so this is meaningful on a converged state only (NUM-12's second
        NOTE), and it is evaluated in every mode including ``none``.

        Parameters
        ----------
        state
            A grid function on this model's product space, normally the converged
            one.
        wall_distance_nm
            The distance field the corrections read, as
            :meth:`residual_form` was given it: ``D~_i`` carries the wall
            correction, so a diagnostic built on a different field would report a
            different Peclet number from the one the solver saw.
        """
        states = self.transport_states(self._split(list(state.components)), wall_distance_nm)
        return {name: species_cell_peclet(state) for name, state in states.items()}

    def transport_states(
        self, functions: Mapping[str, Expression], wall_distance_nm: Expression
    ) -> dict[str, TransportState]:
        """Return one :class:`TransportState` per species, built from ``functions``.

        The public seam onto the stabilisation's own view of a state, alongside
        :meth:`concentration_variables` and :meth:`coefficients`. Post-processing
        needs it to evaluate ``S_i(c~; psi)`` for the NUM-24 indicator route, and
        the diagnostic of NUM-12 needs it for ``Pe_K``; both must see the state the
        residual was assembled from rather than a second construction of it, or the
        NUM-26 identity between the two current routes stops being an identity.

        Parameters
        ----------
        functions
            The solved fields keyed by field name, in the model's own NUM-02
            variables.
        wall_distance_nm
            The PHY-02 distance field the solve used.
        """
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
        """Return the relative permittivity ``eps~_r`` over all of Omega.

        The fluid carries the corrected ``eps_r,f(<c>)/eps_r,f^0`` and each solid
        its own constant ratio (PHY-03). Poisson is solved over the whole domain,
        so a missing solid entry would leave the protein or the membrane at the
        electrolyte's permittivity - a plausible, wrong answer with no solver
        diagnostic, since ``eps_r`` is about 24 times too large there. Any
        material that is neither fluid nor named in ``solid_permittivities`` is
        therefore reported before the form is assembled, except the ion-exclusion
        shell, which takes the fluid's value by design (section 5.3.1 NOTE).

        Parameters
        ----------
        mesh
            The deployed mesh.
        coefficients
            The state the fluid permittivity is evaluated at.
        solid_fraction
            The supplied ``chi`` of section 4.4's NOTE, if any. It replaces the
            sharp material split by the blend
            ``chi * eps_p + (1 - chi) * eps_r,f(<c>)``, and with ``chi`` the
            material indicator it reproduces the piecewise assignment exactly —
            which is why this is a refinement of PHY-20 and not a replacement
            for it. The mesh still carries the material split, so Nernst-Planck
            is still not solved inside the protein: the field smooths the
            coefficient, not the domain.
        """
        fluid_permittivity = coefficients.relative_permittivity()
        fluid_mask = mesh.Materials(self.fluid).Mask()
        unassigned = sorted(
            {
                material
                for index, material in enumerate(mesh.GetMaterials())
                if not fluid_mask[index]
                and material not in self.solid_permittivities
                and material not in PERMITTIVITY_EXEMPT
            }
        )
        if unassigned:
            logger.warning(
                "%r has no solid_permittivities entry for %s, so Poisson carries the "
                "electrolyte permittivity there (PHY-03)",
                self.name,
                ", ".join(unassigned),
            )
        if not self.solid_permittivities:
            solids: Expression = fluid_permittivity
        else:
            reference = self.electrolyte.permittivity_0
            solids = mesh.MaterialCF(
                {
                    material: value / reference
                    for material, value in self.solid_permittivities.items()
                },
                default=fluid_permittivity,
            )
        if solid_fraction is None:
            return solids
        # The whole piecewise branch rather than one material's constant, so a
        # mesh carrying a protein *and* a membrane blends each towards its own
        # eps_p. Where chi is zero the branch's value is irrelevant, which is why
        # its fluid default costs nothing. Written once, in materials.fields:
        # a second copy of the blend here is a second place for it to drift.
        return blend(solid_fraction, solids, fluid_permittivity)

    # -- weak form ---------------------------------------------------------

    def residual_form(
        self,
        space: FESpace,
        measures: Measures,
        *,
        wall_distance_nm: Expression = SATURATED_WALL_DISTANCE_NM,
        fixed_charge: Expression | None = None,
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
        space
            The product space of :meth:`space`.
        measures
            Symmetry and quadrature policy; its element order must match the
            model's, because the NUM-07 bonus is computed from it.
        wall_distance_nm
            The PHY-02 distance field. Pass
            :data:`~nanopnp.physics.coefficients.SATURATED_WALL_DISTANCE_NM`
            when no wall correction is active.
        fixed_charge
            The dimensionless protein space charge ``rho~_pore``, if any. Its
            SI scale is :attr:`~nanopnp.core.scaling.Scales.charge_density_C_m3`.
        solid_fraction
            The supplied ``chi`` of section 4.4's NOTE, if any; see
            :meth:`permittivity`. It enters the Poisson operator alone: the
            material split the mesh carries is what keeps Nernst-Planck out of
            the protein, and the field smooths the coefficient rather than the
            domain.
        surface_charge
            The dimensionless surface charge ``sigma~_s`` on
            ``surface_charge_boundary``, if any. Its SI scale is
            :attr:`~nanopnp.core.scaling.Scales.surface_charge_C_m2`. Rung 4 of
            the NUM-18 ladder ramps this together with ``fixed_charge``, which is
            why the term is here rather than folded into the wall's natural
            condition.
        surface_charge_boundary
            Boundary-name regular expression the surface charge sits on. The
            pore wall by default; the membrane faces carry zero charge in the
            reference case (PHY-09).
        sources
            Body sources by field name, added to the right-hand side of each
            equation. This is what the manufactured solutions of VER-18 supply;
            a physical case has none. A source on a concentration field also
            enters the stabilisation residual ``R~_i``, and a source on the
            velocity enters ``R~_m``: leaving it out there is what NUM-14's NOTE
            warns about, and it shows up as a degraded convergence rate rather
            than as an error (VER-42).
        state
            The solve's own state grid function, from which the stabilisation
            parameters are evaluated. NGSolve treats a grid function in an
            integrand as data, so ``tau_i``, ``nu_K``, ``tau_m`` and ``tau_c``
            follow the current iterate on every ``Apply`` and are omitted from the
            linearisation — COMSOL's ``nojac()``, and the reason the non-smooth
            ``max(0, .)`` in ``nu_K`` never reaches the Jacobian. Required by every
            mode that assembles a term; a mode that assembles none ignores it.

        Raises
        ------
        ValueError
            If the measure's element order disagrees with the model's, if a
            source names a field the model does not solve for, or if the
            stabilisation mode assembles a term and no ``state`` was given.
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
            residual -= charge_source(fixed_charge, potential_test, measures)
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
            stabilisation_term = stabilisation.transport_term(
                measures,
                trial=self._transport_state(name, trials, variables, coefficients),
                lagged=self._transport_state(name, lagged, lagged_variables, lagged_coefficients),
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
        """Return one species' stabilisation state, from the trial or the lagged side.

        One builder for both sides, so that the wind the term is linear in and the
        wind its parameters are read from cannot be assembled differently.
        """
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
        """Return the momentum stabilisation state, from the trial or the lagged side.

        The body force is built here, from the same coefficients
        :meth:`_flow_residual` uses, and passed into the state rather than rebuilt
        inside it: the momentum residual the stabilisation is defined against must
        be the one the Galerkin form assembles, including whether the PHY-23
        deviation is enabled. Note the sign — :func:`~nanopnp.physics.flow.electrical_body_force`
        returns the *residual* contribution ``-int f.v``, so ``f`` itself is the
        negative of its integrand.
        """
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
        """Return the momentum and continuity contributions (PHY-07, PHY-08)."""
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

    # -- gates and solve ---------------------------------------------------

    def gates(
        self,
        mesh: Mesh,
        state: GridFunction,
        measures: Measures,
        *,
        increment: GridFunction | None = None,
    ) -> tuple[Sequence[Gate], Sequence[Gate]]:
        """Return the NUM-17 state gates and increment gates for a solve.

        The concentration gates sample the fluid only: a field evaluated outside
        its ``definedon`` region comes back as zero, and a positivity gate
        sampling the membrane would abort on a solid every time.

        Parameters
        ----------
        mesh, state, measures
            The meshed domain, the iterate to gate and the symmetry policy.
        increment
            The Newton direction, when one exists. The increment gates are
            returned only if it is given, so that the whole NUM-17 policy - both
            halves of it - is owned by this method rather than half of it living
            in :meth:`solve`.
        """
        fields = self._split(list(state.components))
        fluid_sampler = FieldSampler(
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
        potential_sampler = FieldSampler(mesh, coordinates=measures.coordinate_names)
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
        fixed_charge: Expression | None = None,
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

        The default strategy of section 5.4.3: monolithic damped Newton (NUM-16)
        with the NUM-17 gates active, warm-started from ``initial`` when one is
        given. The continuation ladder of NUM-18 drives this method rung by rung;
        it is not implemented here.

        Parameters
        ----------
        mesh, measures
            The meshed domain and the symmetry and quadrature policy.
        boundaries
            The boundary vocabulary the space is built on.
        potential_values
            Essential data for ``phi~``, in units of ``V_T``.
        concentration_values
            Essential data for each ``c~_i``, dimensionless; bulk, that is 1, by
            default. In the log branch these are still concentrations and are
            converted here.
        initial_concentrations
            Interior cold-start values, 1 by default. Separate from
            ``concentration_values`` because that may be a spatially varying
            boundary coefficient function, which has no meaning in the volume.
        velocity_values
            Essential data for ``u~``; zero (no-slip) by default.
        wall_distance_nm, fixed_charge, solid_fraction, surface_charge,
        surface_charge_boundary, sources
            As :meth:`residual_form`.
        initial
            A previous solution to warm-start from. Its space is reused, so it
            must have been produced on the same mesh by the same model. A rung
            of the ladder that *changes* the field set — adding ``c_i``, or
            adding ``u`` and ``p`` — must be handed a solution already
            transferred onto this model's space by
            :func:`nanopnp.solve.continuation.transfer`.
        settings, solver
            Newton policy and the direct linear solver.
        callback
            Called with every accepted :class:`~nanopnp.solve.newton.NewtonStep`,
            for continuation logging and progress reporting (FR-27).

        Returns
        -------
        ModelSolution
            The converged state and its convergence record.

        Raises
        ------
        nanopnp.solve.gates.GateViolationError
            If any NUM-17 assertion fails. The state is then the last admissible
            iterate, not the rejected one.
        nanopnp.solve.newton.NewtonDivergenceError
            If Newton reaches its iteration cap.
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
        )

    def cold_state(
        self,
        mesh: Mesh,
        boundaries: CoupledBoundaries = DEFAULT_BOUNDARIES,
        *,
        initial_concentrations: Mapping[str, float] | None = None,
    ) -> GridFunction:
        """Return a fresh state on this model's space: bulk ions, zero potential and flow.

        ``c~_i = 1`` *is* the bulk, by the definition of the concentration scale
        ``c_0``, so that is the default. It is written over the whole fluid
        rather than only on the boundary because a cold start at ``c~_i = 0``
        fails the NUM-17 positivity gate on entry, before Newton takes a step —
        and in the log branch ``log(0)`` is not even representable.

        Public because the continuation ladder needs it: transferring a solution
        onto a *larger* field set fills the fields the previous rung did not
        solve for from a cold start, and only the model knows what admissible
        means for them.

        Parameters
        ----------
        mesh
            The meshed domain.
        boundaries
            The boundary vocabulary the space is built on.
        initial_concentrations
            Interior values per species, 1 (bulk) by default.
        """
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
        """Write the essential boundary data into the state, leaving the interior alone."""
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


@dataclass(frozen=True)
class ElectrostaticModel:
    """``poisson``, ``pb`` and ``pb-linear``: one field, no transport (PHY-21).

    Poisson-Boltzmann is a **distinct model**, not the coupled solver evaluated
    at zero bias. In ePNP-NS the diffusivity and the mobility carry different
    concentration corrections, so the model violates the Einstein relation at
    finite concentration and its zero-bias limit is not a Boltzmann distribution
    (PHY-14, PHY-24).

    Parameters
    ----------
    name
        Registered name.
    screening
        ``"none"`` for plain Poisson, ``"linear"`` for Debye-Hueckel,
        ``"sinh"`` for nonlinear Poisson-Boltzmann.
    order
        Element order.
    """

    name: str
    screening: Literal["none", "linear", "sinh"]
    order: int = 2

    @property
    def fields(self) -> tuple[Field, ...]:  # noqa: D102
        return (Field(POTENTIAL, "h1", self.order, None),)

    @property
    def boundary_conditions(self) -> Mapping[str, Mapping[str, str]]:  # noqa: D102
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
    def provenance(self) -> Mapping[str, Any]:  # noqa: D102
        return {
            "model": self.name,
            "fields": {POTENTIAL: {"element": "h1", "order": self.order, "domain": None}},
            "screening": self.screening,
            "deviations_from_validated_default": [],
        }

    def space(self, mesh: Mesh, boundaries: CoupledBoundaries = DEFAULT_BOUNDARIES) -> FESpace:
        """Return the scalar space for ``phi~``."""
        import ngsolve as ngs

        return ngs.H1(mesh, order=self.order, dirichlet=boundaries.potential)

    def cold_state(
        self,
        mesh: Mesh,
        boundaries: CoupledBoundaries = DEFAULT_BOUNDARIES,
        *,
        initial_concentrations: Mapping[str, float] | None = None,
    ) -> GridFunction:
        """Return a fresh state on this model's space: ``phi~ = 0`` everywhere.

        The signature matches :meth:`CoupledModel.cold_state` so the continuation
        ladder can cold-start any model through one call;
        ``initial_concentrations`` has no meaning here and is rejected rather
        than ignored, because a caller passing it has misunderstood the model.

        Raises
        ------
        TypeError
            If ``initial_concentrations`` is given.
        """
        import ngsolve as ngs

        if initial_concentrations is not None:
            raise TypeError(
                f"{self.name!r} solves no concentrations, so initial_concentrations has no "
                "meaning for it"
            )
        return ngs.GridFunction(self.space(mesh, boundaries), name="phi_tilde")

    def residual_form(
        self,
        space: FESpace,
        measures: Measures,
        *,
        debye_length_nm: float | None = None,
        permittivity: Expression = 1.0,
        **kwargs: Option,
    ) -> IntegralTerm:
        """Return the weak residual in the trial function.

        Raises
        ------
        ValueError
            If a screened model is asked for without a Debye length.
        TypeError
            If a keyword this model does not understand is passed.
        """
        _reject_unknown(kwargs, f"{self.name!r}.residual_form")
        trial, test = space.TnT()
        if self.screening == "none":
            return poisson_operator(trial, test, measures, permittivity=permittivity)
        if debye_length_nm is None:
            raise ValueError(f"{self.name!r} needs a debye_length_nm; it screens with 1/lambda^2")
        if self.screening == "linear":
            return linear_pb_operator(trial, test, measures, debye_length_nm=debye_length_nm)
        return nonlinear_pb_residual(trial, test, measures, debye_length_nm=debye_length_nm)

    def solve(
        self,
        mesh: Mesh,
        measures: Measures,
        *,
        boundaries: CoupledBoundaries = DEFAULT_BOUNDARIES,
        potential_values: Expression = 0.0,
        debye_length_nm: float | None = None,
        initial: ModelSolution | None = None,
        settings: NewtonSettings = DEFAULT_SETTINGS,
        solver: str = DEFAULT_SOLVER,
        **kwargs: Option,
    ) -> ModelSolution:
        """Solve the electrostatic model, delegating to :mod:`nanopnp.physics.pb`.

        Parameters
        ----------
        initial
            A previous solution to warm-start from, on the same mesh and at the
            same order. Stage 2 of the NUM-18 ladder warm-starts nonlinear
            Poisson-Boltzmann from the linear solution, which is why both stages
            are on the ladder at all.

        Raises
        ------
        ValueError
            If a screened model is asked for without a Debye length.
        TypeError
            If a keyword this model does not understand is passed.
        """
        import ngsolve as ngs

        _reject_unknown(kwargs, f"{self.name!r}.solve")

        if self.screening == "none":
            space = self.space(mesh, boundaries)
            state = ngs.GridFunction(space, name="phi_tilde")
            if initial is not None:
                state.vec.data = initial.state.vec
            set_boundary_values(state, potential_values, mesh.Boundaries(boundaries.potential))
            a = ngs.BilinearForm(self.residual_form(space, measures)).Assemble()
            f = ngs.LinearForm(space).Assemble()
            solve_linear(a, f, state, solver=solver)
            return ModelSolution(model=self, space=space, state=state, residual=a)

        if debye_length_nm is None:
            raise ValueError(f"{self.name!r} needs a debye_length_nm; it screens with 1/lambda^2")
        state, record = solve_pb_recorded(
            mesh,
            measures,
            debye_length_nm=debye_length_nm,
            dirichlet=boundaries.potential,
            boundary_values=potential_values,
            nonlinear=self.screening == "sinh",
            order=self.order,
            solver=solver,
            settings=settings,
            initial=None if initial is None else initial.state,
        )
        # The residual is rebuilt rather than returned by ``solve_pb``, which
        # owns its own; it is written in the same trial function and on the same
        # space, so the two are the same operator.
        residual = ngs.BilinearForm(state.space)
        residual += self.residual_form(state.space, measures, debye_length_nm=debye_length_nm)
        return ModelSolution(
            model=self, space=state.space, state=state, newton=record, residual=residual
        )


ModelBuilder: TypeAlias = Callable[..., PhysicsModel]
"""Builds one physics model from case-file keywords."""

_REGISTRY: dict[str, ModelBuilder] = {}


def register(name: str, builder: ModelBuilder) -> None:
    """Register a physics model under ``name``.

    Raises
    ------
    ValueError
        If the name is already registered, which would silently change the
        meaning of existing case files.
    """
    if name in _REGISTRY:
        raise ValueError(f"physics model {name!r} is already registered")
    _REGISTRY[name] = builder


def registered_models() -> tuple[str, ...]:
    """Return every selectable model name, sorted."""
    return tuple(sorted(_REGISTRY))


def create(name: str, **kwargs: Option) -> PhysicsModel:
    """Build the physics model registered as ``name``.

    Parameters
    ----------
    name
        Registered model name, one of the table of PHY-21.
    **kwargs
        Passed to the model's builder; ``electrolyte`` and ``concentration_M``
        for the coupled family, ``order`` for all of them.

    Raises
    ------
    KeyError
        If no such model is registered; the message lists the known names.
    """
    try:
        builder = _REGISTRY[name]
    except KeyError:
        known = ", ".join(registered_models())
        raise KeyError(f"unknown physics model {name!r}; registered models are {known}") from None
    return builder(**kwargs)


def _coupled_electrolyte(
    electrolyte: Electrolyte | None, corrections: str, classical: bool
) -> Electrolyte:
    """Return the electrolyte a coupled model is built on.

    ``classical`` selects the ``none`` model for every correction and turns the
    steric term off, which is PHY-21's exact reduction of ePNP-NS to PNP-NS. It
    is applied to the *switches*, never by branching in the forms.
    """
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
    """Build ``epnp-ns``: the validated default, every correction on."""
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
    """Build ``pnp-ns``: the same class with every correction resolving to ``none``."""
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
    """Build ``pnp``: Poisson and Nernst-Planck with no flow coupling."""
    return CoupledModel(
        electrolyte=_coupled_electrolyte(electrolyte, corrections, classical=classical),
        name="pnp",
        flow=False,
        **kwargs,
    )


def _electrostatic_builder(name: str, screening: Literal["none", "linear", "sinh"]) -> ModelBuilder:
    """Return a builder for one of the single-field electrostatic models."""

    def build(*, order: int = 2, **kwargs: Option) -> PhysicsModel:
        _reject_unknown(kwargs, f"the {name!r} builder")
        return ElectrostaticModel(name=name, screening=screening, order=order)

    return build


register("epnp-ns", _build_epnp_ns)
register("pnp-ns", _build_pnp_ns)
register("pnp", _build_pnp)
register("pb", _electrostatic_builder("pb", "sinh"))
register("pb-linear", _electrostatic_builder("pb-linear", "linear"))
register("poisson", _electrostatic_builder("poisson", "none"))

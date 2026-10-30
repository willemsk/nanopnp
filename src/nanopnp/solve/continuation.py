"""The NUM-18 continuation ladder and the warm start between its rungs."""

from __future__ import annotations

import logging
import math
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace

from nanopnp.core.scaling import debye_length_nm
from nanopnp.core.stages import Cancelled
from nanopnp.core.typing import Expression, GridFunction, Mesh, Option
from nanopnp.materials.electrolyte import CorrectionSwitches, Electrolyte
from nanopnp.numerics.gates import FieldSampler, PecletDiagnostic, PecletMeasurement
from nanopnp.numerics.measures import AXISYMMETRIC, FixedCharge, Measures
from nanopnp.physics.coefficients import SATURATED_WALL_DISTANCE_NM
from nanopnp.physics.models import (
    DEFAULT_BOUNDARIES,
    LADDER_TARGETS,
    CoupledBoundaries,
    ModelSolution,
    PhysicsModel,
    concentration_field_name,
    create,
    declaration,
    solves_transport,
    transport_model,
)

__all__ = [
    "LadderResult",
    "Rung",
    "RungResult",
    "TransferError",
    "bias_schedule",
    "default_ladder",
    "mesh_report",
    "model_reads_wall",
    "ramp_schedule",
    "reads_wall",
    "run_ladder",
    "transfer",
]

logger = logging.getLogger(__name__)

# The bias ramp and the salt ladder's foot: SPECIFICATION.md NUM-18 stages 5 and 9.
BIAS_ONSET_V = 0.05

FINE_BIAS_STEP_V = 0.01

COARSE_BIAS_STEP_V = 0.025

ELECTRODES: frozenset[str] = frozenset({"cis", "trans"})

LADDER_START_CONCENTRATION_M = 0.05


class TransferError(RuntimeError):
    """A solution cannot be carried onto the next rung's space; raised rather than guessed at."""


@dataclass(frozen=True)
class Rung:
    """One rung of the ladder: a model, a mesh, and the arguments to solve it with.

    Parameters
    ----------
    stage
        Which stage the rung belongs to.
    """

    name: str
    stage: int
    model: PhysicsModel
    mesh: Mesh
    boundaries: CoupledBoundaries = DEFAULT_BOUNDARIES
    measures: Measures = AXISYMMETRIC
    solve_kwargs: Mapping[str, Option] = field(default_factory=dict)


def _read_stabilisation_entry(model: object, key: str, *, expect_mapping: bool = False) -> object:
    name = getattr(model, "name", "unknown")
    provenance = getattr(model, "provenance", {})
    if key not in provenance:
        raise ValueError(
            f"model {name!r} records no {key} in its provenance; every model names its "
            "stabilisation mode, that mode's parameters and their provenance, 'none' where it "
            "assembles no transport term (NUM-13, section 5.3.3)"
        )
    value = provenance[key]
    if expect_mapping and not isinstance(value, Mapping):
        raise ValueError(
            f"model {name!r} records {key} as {type(value).__name__}, not a mapping "
            "(NUM-13, section 5.3.3)"
        )
    return value


@dataclass(frozen=True)
class RungResult:
    """What one rung cost and how it converged, for the manifest."""

    name: str
    stage: int
    model: str
    seconds: float
    transferred_fields: tuple[str, ...]
    cold_fields: tuple[str, ...]
    stabilisation: str
    newton: Mapping[str, Option] | None
    deviations: tuple[str, ...] = ()

    @property
    def iterations(self) -> int:
        """Newton iterations this rung took; 0 for a linear model."""
        return 0 if self.newton is None else int(self.newton["iterations"])

    @property
    def minimum_damping_used(self) -> float:
        """Smallest damping any accepted step of this rung was taken with."""
        return 1.0 if self.newton is None else float(self.newton["minimum_damping_used"])

    def summary(self) -> dict[str, Option]:
        """Return the record of this rung."""
        return {
            "rung": self.name,
            "stage": self.stage,
            "model": self.model,
            "seconds": self.seconds,
            "transferred_fields": list(self.transferred_fields),
            "cold_fields": list(self.cold_fields),
            "deviations_from_validated_default": list(self.deviations),
            "stabilisation": self.stabilisation,
            "newton": dict(self.newton) if self.newton is not None else None,
        }


@dataclass(frozen=True)
class LadderResult:
    """The converged state at the top of the ladder, and the record of getting there."""

    solution: ModelSolution
    rungs: tuple[RungResult, ...]
    mesh: Mapping[str, Option]
    peclet: PecletMeasurement | None = None

    @property
    def seconds(self) -> float:
        """Total wall time of the ladder."""
        return math.fsum(rung.seconds for rung in self.rungs)

    @property
    def iterations(self) -> int:
        """Total Newton iterations over every rung."""
        return sum(rung.iterations for rung in self.rungs)

    @property
    def minimum_damping_used(self) -> float:
        """Smallest damping any rung needed."""
        return min((rung.minimum_damping_used for rung in self.rungs), default=1.0)

    @property
    def stabilisation(self) -> str:
        """The stabilisation mode the top rung's number was produced on."""
        return str(_read_stabilisation_entry(self.solution.model, "stabilisation"))

    @property
    def stabilisation_parameters(self) -> Mapping[str, Option]:
        """The tuning constants of the mode the top rung was solved in."""
        found = _read_stabilisation_entry(
            self.solution.model, "stabilisation_parameters", expect_mapping=True
        )
        assert isinstance(found, Mapping)
        return dict(found)

    @property
    def stabilisation_provenance(self) -> Mapping[str, Option]:
        """Where the mode's constants came from, as the mode itself reports them."""
        found = _read_stabilisation_entry(
            self.solution.model, "stabilisation_provenance", expect_mapping=True
        )
        assert isinstance(found, Mapping)
        return dict(found)

    @property
    def max_cell_peclet(self) -> float | None:
        """The largest cell Peclet number on the converged top rung, or ``None`` if unmeasured."""
        return None if self.peclet is None else self.peclet.maximum

    def summary(self) -> dict[str, Option]:
        """Return the whole ladder's record for the provenance manifest."""
        return {
            "rungs": [rung.summary() for rung in self.rungs],
            "stages": sorted({rung.stage for rung in self.rungs}),
            "mesh": dict(self.mesh),
            "seconds": self.seconds,
            "iterations": self.iterations,
            "minimum_damping_used": self.minimum_damping_used,
            "stabilisation": self.stabilisation,
            "stabilisation_parameters": dict(self.stabilisation_parameters),
            "stabilisation_provenance": dict(self.stabilisation_provenance),
            "max_cell_peclet": self.max_cell_peclet,
            "peclet": None if self.peclet is None else self.peclet.summary(),
        }


def reads_wall(electrolyte: Electrolyte) -> bool:
    """Return whether any resolved correction of ``electrolyte`` reads the distance field."""
    return any(
        bool(getattr(correction, "use_wall", False))
        for correction in electrolyte.corrections.values()
    )


def model_reads_wall(model: PhysicsModel) -> bool:
    """Return whether this built model evaluates the distance field."""
    if not declaration(model.name).wall_distance:
        return False
    if not solves_transport(model):
        return True
    return reads_wall(transport_model(model).electrolyte)


def mesh_report(mesh: Mesh) -> dict[str, Option]:
    """Return the mesh's size, for the record."""
    return {
        "elements": mesh.ne,
        "vertices": mesh.nv,
        "materials": list(mesh.GetMaterials()),
        "boundaries": sorted(set(mesh.GetBoundaries())),
    }


def bias_schedule(
    target_V: float,
    *,
    onset_V: float = BIAS_ONSET_V,
    fine_step_V: float = FINE_BIAS_STEP_V,
    coarse_step_V: float = COARSE_BIAS_STEP_V,
) -> tuple[float, ...]:
    """Return the bias ramp in volts, ending exactly on the target.

    Parameters
    ----------
    fine_step_V, coarse_step_V
        Step magnitudes below and above the onset; ValueError unless both are positive.
    """
    if fine_step_V <= 0.0 or coarse_step_V <= 0.0:
        raise ValueError(
            f"the bias steps must be positive, got {fine_step_V} V and {coarse_step_V} V"
        )
    magnitude = abs(target_V)
    if magnitude == 0.0:
        return ()
    sign = math.copysign(1.0, target_V)
    tolerance = 1e-12 * max(magnitude, 1.0)
    schedule: list[float] = []
    reached = 0.0
    while reached < magnitude - tolerance:
        step = fine_step_V if reached < onset_V - tolerance else coarse_step_V
        reached = min(reached + step, magnitude)
        schedule.append(sign * reached)
    return tuple(schedule)


def ramp_schedule(steps: int) -> tuple[float, ...]:
    """Return ``(1/n, 2/n, ..., 1)``, the fractions of a linear ramp."""
    if steps < 1:
        raise ValueError(f"a ramp needs at least one step, got {steps}")
    return tuple((index + 1) / steps for index in range(steps))


def _fields_of(model: PhysicsModel) -> dict[str, tuple[str, int]]:
    return {declared.name: (declared.element, declared.order) for declared in model.fields}


def _shared_fields(source: PhysicsModel, target: PhysicsModel) -> tuple[str, ...]:
    before = _fields_of(source)
    return tuple(name for name, kind in _fields_of(target).items() if before.get(name) == kind)


def _log_branch(model: PhysicsModel) -> bool:
    return solves_transport(model) and transport_model(model).log_variables


def _component(state: GridFunction, model: PhysicsModel, name: str) -> GridFunction:
    names = list(_fields_of(model))
    if len(names) == 1:
        return state
    return state.components[names.index(name)]


def transfer(
    previous: ModelSolution,
    model: PhysicsModel,
    mesh: Mesh,
    boundaries: CoupledBoundaries = DEFAULT_BOUNDARIES,
    *,
    initial_concentrations: Mapping[str, float] | None = None,
) -> ModelSolution:
    """Carry a converged solution onto another model's space, interpolating shared fields by name.

    Parameters
    ----------
    initial_concentrations
        Cold-start values for concentrations the previous model did not solve.

    Raises
    ------
    TransferError
        If the meshes differ.
    """
    import ngsolve as ngs

    if previous.space.mesh is not mesh:
        raise TransferError(
            "a transfer between rungs must stay on one mesh; NUM-19 allows the mesh to be "
            "adapted between rungs, but interpolating a solution onto a different mesh is a "
            "point evaluation that returns a plausible number outside the source domain "
            "rather than raising, so that path is not taken implicitly"
        )

    source = _fields_of(previous.model)
    target = _fields_of(model)
    shared = _shared_fields(previous.model, model)
    cold = tuple(name for name in target if name not in shared)

    if not shared:
        raise TransferError(
            f"{previous.model.name!r} and {model.name!r} share no field at the same "
            f"discretisation ({sorted(source)} against {sorted(target)}), so there is nothing to "
            "warm-start from; solve the next rung cold instead of pretending otherwise"
        )

    space = model.space(mesh, boundaries)
    # A log-variable and a primitive model share names, order and ndof, so a shape
    # test alone would copy w_i across as c~_i (NUM-02).
    same_branch = _log_branch(previous.model) == _log_branch(model)
    # Ordered items: a verbatim copy needs the product-space blocks in the same order.
    same_shape = list(target.items()) == list(source.items())
    if same_branch and same_shape and space.ndof == previous.space.ndof:
        # No cold start: the copy would overwrite it, and each interpolation is a mass-matrix solve.
        state = ngs.GridFunction(space, name=f"{model.name}_state")
        state.vec.data = previous.state.vec
        logger.debug("transfer to %r: copied %d fields verbatim", model.name, len(shared))
        return ModelSolution(model=model, space=state.space, state=state)

    # A model with no species refuses ion data.
    state = model.cold_state(mesh, boundaries, initial_concentrations=initial_concentrations)

    species = set(model.species)
    for name in shared:
        matched = [ion for ion in species if concentration_field_name(ion) == name]
        if matched:
            # The concentration, not the solved variable (they differ by an exponential
            # in the log branch).
            value: Expression = previous.concentration(matched[0])
            if _log_branch(model):
                value = ngs.log(value)
        else:
            value = previous.component(name)
        _component(state, model, name).Set(value)

    logger.debug(
        "transfer to %r: interpolated %s, cold-started %s", model.name, list(shared), list(cold)
    )
    return ModelSolution(model=model, space=state.space, state=state)


def run_ladder(
    rungs: Sequence[Rung],
    *,
    initial: ModelSolution | None = None,
    on_rung: Callable[[int, Rung], None] | None = None,
    on_solved: Callable[[int, RungResult], None] | None = None,
) -> LadderResult:
    """Solve every rung in order, each warm-started from the one before.

    Parameters
    ----------
    on_rung
        Called with the 0-based index and the rung; an exception from it cancels the ladder.
    on_solved
        Called with the 0-based index and the rung's record once the rung is solved.

    Raises
    ------
    ValueError
        If the ladder is empty.
    """
    if not rungs:
        raise ValueError("a continuation ladder needs at least one rung")

    previous: ModelSolution | None = initial
    records: list[RungResult] = []
    for index, rung in enumerate(rungs):
        if on_rung is not None:
            on_rung(index, rung)
        declared = tuple(_fields_of(rung.model))
        transferred_fields: tuple[str, ...] = ()
        cold_fields = declared
        carried: ModelSolution | None = None
        if previous is not None:
            # Cold-started concentrations take the rung's own value; ``solve`` ignores
            # it on a warm start.
            carried = transfer(
                previous,
                rung.model,
                rung.mesh,
                rung.boundaries,
                initial_concentrations=rung.solve_kwargs.get("initial_concentrations"),
            )
            transferred_fields = _shared_fields(previous.model, rung.model)
            cold_fields = tuple(name for name in declared if name not in transferred_fields)
            # Released before the next solve: the residual form keeps a system matrix alive, and one
            # factorisation of the five-field system is 6.2 GB at the reference mesh (section 6.6).
            previous = None

        # Read before the solve so a model recording no mode is refused before its rung is paid for.
        stabilisation = str(_read_stabilisation_entry(rung.model, "stabilisation"))
        started = time.perf_counter()
        try:
            solution = rung.model.solve(
                rung.mesh,
                rung.measures,
                boundaries=rung.boundaries,
                **({"initial": carried} if carried is not None else {}),
                **dict(rung.solve_kwargs),
            )
        except Cancelled:
            # A cancel is not a failure; it stays out of the failure log.
            logger.info("continuation cancelled on rung %r (stage %d)", rung.name, rung.stage)
            raise
        except Exception:
            # Re-raised unchanged: the gate's diagnostic names field and location.
            logger.error(
                "continuation failed on rung %r (stage %d, model %r)",
                rung.name,
                rung.stage,
                rung.model.name,
            )
            raise
        seconds = time.perf_counter() - started

        record = RungResult(
            name=rung.name,
            stage=rung.stage,
            model=rung.model.name,
            seconds=seconds,
            transferred_fields=transferred_fields,
            cold_fields=cold_fields,
            stabilisation=stabilisation,
            newton=solution.newton.summary() if solution.newton is not None else None,
            deviations=tuple(rung.model.provenance.get("deviations_from_validated_default", ())),
        )
        records.append(record)
        if on_solved is not None:
            on_solved(index, record)
        logger.info(
            "rung %-28s stage %d  %6.2f s  %2d iterations  damping >= %.3f",
            rung.name,
            rung.stage,
            seconds,
            record.iterations,
            record.minimum_damping_used,
        )
        previous = solution

    if previous is None:  # pragma: no cover - the empty ladder was refused above
        raise ValueError("a continuation ladder needs at least one rung")
    return LadderResult(
        solution=previous,
        rungs=tuple(records),
        mesh=mesh_report(rungs[-1].mesh),
        peclet=_report_peclet(previous, rungs[-1].measures),
    )


def _report_peclet(solution: ModelSolution, measures: Measures) -> PecletMeasurement | None:
    if not solves_transport(solution.model):
        return None
    model = transport_model(solution)
    return PecletDiagnostic(
        FieldSampler.shared(
            solution.space.mesh,
            coordinates=measures.coordinate_names,
            materials=model.fluid,
        ),
        model.cell_peclet(solution.state, solution.wall_distance_nm),
    ).report()


def default_ladder(
    mesh: Mesh,
    *,
    concentration_M: float = 1.0,
    bias_V: float = 0.2,
    ground: str = "cis",
    electrolyte: Electrolyte | None = None,
    corrections: str = "willems2020_nacl",
    surface_charge_C_m2: float = 0.0,
    fixed_charge_C_m3: float = 0.0,
    fixed_charge_domain: str | None = None,
    fixed_charge_field: FixedCharge | None = None,
    solid_fraction: Expression | None = None,
    wall_potential_V: float = 0.0,
    wall_distance_nm: Expression = SATURATED_WALL_DISTANCE_NM,
    solid_permittivities: Mapping[str, float] | None = None,
    boundaries: CoupledBoundaries = DEFAULT_BOUNDARIES,
    measures: Measures = AXISYMMETRIC,
    start_concentration_M: float | None = LADDER_START_CONCENTRATION_M,
    charge_steps: int = 4,
    concentration_steps: int = 4,
    surface_charge_boundary: str = "wall",
    corrections_active: bool = True,
    target: str | None = None,
    switches: CorrectionSwitches | None = None,
    stabilisation: str = "none",
    velocity_order: int | None = None,
    pressure_order: int = 1,
) -> tuple[Rung, ...]:
    """Build the stages of the ladder for one target operating point.

    Parameters
    ----------
    bias_V
        Target applied bias, of either sign.
    ground
        Which electrode is held at zero, ``"cis"`` or ``"trans"``.
    fixed_charge_domain
        Material the fixed charge is confined to; None spreads it over the whole domain.
    solid_fraction
        Passed to every rung that solves Poisson; not ramped.
    """
    import ngsolve as ngs

    # The models the ladder can end at, shared with ``register_model``.
    targets = LADDER_TARGETS
    if target is not None:
        if target not in targets:
            raise ValueError(f"the NUM-18 ladder ends at {' or '.join(targets)}, not at {target!r}")
        corrections_active = target == targets[0]
    if ground not in ELECTRODES:
        raise ValueError(f"ground={ground!r} must be one of {', '.join(sorted(ELECTRODES))}")
    driven = next(iter(ELECTRODES - {ground}))

    # ``MaterialCF`` leaves unmatched keys at the default, so a misspelt domain would silently
    # charge nothing (QR-12).
    if fixed_charge_domain is not None and mesh.Materials(fixed_charge_domain).Mask().NumSet() == 0:
        raise ValueError(
            f"fixed_charge_domain={fixed_charge_domain!r} matches no material of the mesh; "
            f"it carries {', '.join(sorted(set(mesh.GetMaterials())))}"
        )
    if fixed_charge_field is not None and fixed_charge_C_m3 != 0.0:
        raise ValueError(
            "default_ladder takes either fixed_charge_C_m3 (a uniform density) or "
            "fixed_charge_field (a gridded one), not both: the ladder would ramp their sum and "
            "the FR-25 manifest would record two charges, neither of which the solve carried"
        )

    solids = dict(solid_permittivities or {})
    build_M = concentration_M if start_concentration_M is None else start_concentration_M
    base = electrolyte if electrolyte is not None else Electrolyte.from_parameter_file(corrections)

    def _coupled(
        name: str, switches: CorrectionSwitches, *, flow: bool, salt: float
    ) -> PhysicsModel:
        return create(
            name,
            # ``replace`` would change only the record, not what each stage evaluates.
            electrolyte=base.with_switches(switches),
            concentration_M=salt,
            **({"flow": flow} if "flow" in declaration(name).options else {}),
            order=measures.element_order,
            velocity_order=velocity_order,
            pressure_order=pressure_order,
            solid_permittivities=solids,
            # Every rung: a mode switched on at the top would warm-start from a different operator.
            stabilisation=stabilisation,
        )

    classical = CorrectionSwitches.classical()
    # The fit follows the supplied electrolyte, not the ``corrections`` default, or one fit's
    # functions would be evaluated over the other's reference properties.
    correction_model = base.parameter_file or corrections
    corrected = switches if switches is not None else CorrectionSwitches.for_model(correction_model)
    without_steric = corrected.without("steric")

    reference = _coupled("pnp", classical, flow=False, salt=build_M)
    thermal_V = reference.scales.potential_V

    def _potential(bias: float) -> Expression:
        return mesh.BoundaryCF({ground: 0.0, driven: bias / thermal_V})

    zero_bias = _potential(0.0)
    rungs: list[Rung] = []

    def _dielectric() -> dict[str, Option]:
        return {} if solid_fraction is None else {"solid_fraction": solid_fraction}

    # -- stages 1 and 2: Poisson-Boltzmann --------------------------------
    screening_nm = debye_length_nm(build_M, relative_permittivity=base.permittivity_0)
    if wall_potential_V == 0.0:
        pb_boundaries = boundaries
        pb_values: Expression = zero_bias
    else:
        pb_boundaries = replace(
            boundaries, potential=f"{boundaries.potential}|{surface_charge_boundary}"
        )
        pb_values = mesh.BoundaryCF(
            {"cis": 0.0, "trans": 0.0, surface_charge_boundary: wall_potential_V / thermal_V}
        )
    pb_stages: tuple[tuple[int, str], ...] = ((1, "pb-linear"), (2, "pb"))
    for stage, name in pb_stages:
        rungs.append(
            Rung(
                name=f"{stage}-{name}",
                stage=stage,
                # Stated to the builder too: an initialiser must not be refused a
                # salt the case model is exact for only.
                model=create(
                    name,
                    electrolyte=base,
                    concentration_M=build_M,
                    order=measures.element_order,
                    debye_length_nm=screening_nm,
                ),
                mesh=mesh,
                boundaries=pb_boundaries,
                measures=measures,
                solve_kwargs={
                    "debye_length_nm": screening_nm,
                    "potential_values": pb_values,
                },
            )
        )

    # -- stage 3: equilibrium PNP -----------------------------------------
    rungs.append(
        Rung(
            name="3-equilibrium-pnp",
            stage=3,
            model=reference,
            mesh=mesh,
            boundaries=boundaries,
            measures=measures,
            solve_kwargs={"potential_values": zero_bias, **_dielectric()},
        )
    )

    # -- stage 4: ramp the fixed and surface charges together --------------
    # Reused by every later rung: eps V_T / a^2 and eps V_T / a carry no c_0, so they do not
    # move with the salt.
    charge_scale = reference.scales.charge_density_C_m3
    surface_scale = reference.scales.surface_charge_C_m2

    def _charges(fraction: float = 1.0) -> dict[str, Option]:
        charges: dict[str, Option] = {}
        if fixed_charge_field is not None:
            charges["fixed_charge"] = fixed_charge_field.scaled(fraction / charge_scale)
        elif fixed_charge_C_m3 != 0.0:
            density = fraction * fixed_charge_C_m3 / charge_scale
            charges["fixed_charge"] = FixedCharge(
                ngs.CF(density)
                if fixed_charge_domain is None
                else mesh.MaterialCF({fixed_charge_domain: density}, default=0.0),
                None,
            )
        if surface_charge_C_m2 != 0.0:
            charges["surface_charge"] = ngs.CF(fraction * surface_charge_C_m2 / surface_scale)
            charges["surface_charge_boundary"] = surface_charge_boundary
        return charges

    if surface_charge_C_m2 != 0.0 or fixed_charge_C_m3 != 0.0 or fixed_charge_field is not None:
        for fraction in ramp_schedule(charge_steps):
            rungs.append(
                Rung(
                    name=f"4-ramp-charge-{fraction:.2f}",
                    stage=4,
                    model=reference,
                    mesh=mesh,
                    boundaries=boundaries,
                    measures=measures,
                    solve_kwargs={
                        "potential_values": zero_bias,
                        **_charges(fraction),
                        **_dielectric(),
                    },
                )
            )

    # -- stage 5: ramp the bias -------------------------------------------
    for bias in bias_schedule(bias_V):
        rungs.append(
            Rung(
                name=f"5-ramp-bias-{bias * 1e3:+.0f}mV",
                stage=5,
                model=reference,
                mesh=mesh,
                boundaries=boundaries,
                measures=measures,
                solve_kwargs={
                    "potential_values": _potential(bias),
                    **_charges(),
                    **_dielectric(),
                },
            )
        )

    # -- stages 6 to 8: turn the physics on, one block at a time -----------
    physics_stages: tuple[tuple[int, str, str, CorrectionSwitches], ...] = (
        (6, "flow", "pnp-ns", classical),
    )
    if corrections_active:
        physics_stages += (
            (7, "corrections", "epnp-ns", without_steric),
            (8, "steric", "epnp-ns", corrected),
        )
    target_switches = corrected if corrections_active else classical
    target_name = targets[0] if corrections_active else targets[1]

    def _wall(model: PhysicsModel) -> dict[str, Option]:
        return {"wall_distance_nm": wall_distance_nm} if model_reads_wall(model) else {}

    for stage, label, name, switches in physics_stages:
        model = _coupled(name, switches, flow=True, salt=build_M)
        rungs.append(
            Rung(
                name=f"{stage}-{label}",
                stage=stage,
                model=model,
                mesh=mesh,
                boundaries=boundaries,
                measures=measures,
                solve_kwargs={
                    "potential_values": _potential(bias_V),
                    **_charges(),
                    **_dielectric(),
                    **_wall(model),
                },
            )
        )

    # -- stage 9: sweep the salt ------------------------------------------
    if start_concentration_M is not None and not math.isclose(build_M, concentration_M):
        # Geometric: the Debye length goes as c^(-1/2), so the ratio measures how far the
        # double layer moved.
        ratio = concentration_M / build_M
        for fraction in ramp_schedule(concentration_steps):
            salt = build_M * ratio**fraction
            target_model = _coupled(target_name, target_switches, flow=True, salt=salt)
            rungs.append(
                Rung(
                    name=f"9-salt-{salt:.4g}M",
                    stage=9,
                    model=target_model,
                    mesh=mesh,
                    boundaries=boundaries,
                    measures=measures,
                    solve_kwargs={
                        "potential_values": _potential(bias_V),
                        **_charges(),
                        **_dielectric(),
                        **_wall(target_model),
                    },
                )
            )

    return tuple(rungs)

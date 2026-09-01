"""The continuation ladder of NUM-18, and the warm start it rests on.

A cold monolithic Newton solve of ePNP-NS at 3 M against a strongly charged wall
does not converge. It does not converge *correctly*: the NUM-17 positivity gate
aborts it on the first over-long step, which is the right behaviour and no help
at all. The way to the hard operating point is to arrive at it from a converged
neighbour, and the ladder is the sequence of neighbours (FR-17):

1. Linear Poisson-Boltzmann.
2. Nonlinear Poisson-Boltzmann.
3. Equilibrium PNP at ``V_bias = 0``, ``u = 0``.
4. Ramp ``sigma_s`` and ``rho_pore`` from 0 to target.
5. Ramp ``V_bias`` from 0 to +/-200 mV, in steps of about 10 mV near onset.
6. Enable the Stokes / Navier-Stokes coupling.
7. Enable the ``<c>``- and ``d``-dependent ``D``, ``mu``, ``eps``, ``rho`` corrections.
8. Enable the steric flux ``beta_i``.
9. Sweep the salt concentration from 0.05 M to 3 M.

Stages 4, 5 and 9 are ramps and expand into several rungs each; the rest are one
apiece. Enabling the corrections last is what isolates their contribution to any
convergence failure, and it is why this order rather than another.

Why a warm start terminates
---------------------------
Every rung re-solves a state that is already nearly converged. A Newton
criterion measured on the residual *relative to the residual on entry* would
demand a further six orders of magnitude from a residual already at its floor,
so it would never be met and the ladder would stall at rung 2. NUM-16's
relative-update test on the undamped direction is what makes re-solving a
converged state cost zero iterations, and this module depends on it entirely.

Why a warm start needs help across a changed field set
------------------------------------------------------
:meth:`CoupledModel.solve` warm-starts by reusing ``initial.space``, which is
correct and sufficient whenever the field set does not change. Three transitions
change it: stage 2 to 3 adds the concentrations, stage 5 to 6 adds the velocity
and the pressure, and any change of element order would too. :func:`transfer`
is the missing piece: it builds the target model's space, cold-starts it so the
new fields begin somewhere admissible, and interpolates every field the two
models share, by name. The result is a :class:`ModelSolution` *on the target
space*, so ``model.solve(initial=transferred)`` needs no special case.

This is also where a silent error would live. An interpolation that landed the
potential on the wrong component, or that confused the NUM-02 log variable with
the concentration itself, would produce a converged, plausible, wrong answer. The
property that catches it is idempotence: re-solving a converged rung from its own
transferred output must cost zero Newton iterations. It is asserted in
``tests/tier2/test_ladder.py``.

Why the concentration sweep of stage 9 warm-starts at all
---------------------------------------------------------
Changing ``concentration_M`` changes the whole NUM-09 scale set, hence ``S``,
``Pe`` and every nondimensional coefficient — but not the field set, so the
transfer is a vector copy. The previous solution stays a good initial guess
because the nondimensionalisation leaves every field O(1) in the *new* scaling
too: ``c~_i = 1`` is bulk by the definition of ``c_0``, and ``phi~`` is measured
in ``V_T``, which does not move with the salt. That is the payoff of solving in
scaled variables rather than in SI.

NUM-19 (the mesh is adapted between rungs, never within one) is satisfied
structurally: a :class:`Rung` carries its own mesh and nothing here changes it
during a solve. This phase runs one fixed mesh for the whole ladder, sized for
the tightest double layer in the envelope, so there is no adaptation to confine.
"""

from __future__ import annotations

import logging
import math
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from typing import Literal

from nanopnp.core.scaling import debye_length_nm
from nanopnp.core.typing import Expression, GridFunction, Mesh, Option
from nanopnp.materials.electrolyte import CorrectionSwitches, Electrolyte
from nanopnp.physics.coefficients import SATURATED_WALL_DISTANCE_NM
from nanopnp.physics.measures import AXISYMMETRIC, Measures
from nanopnp.physics.models import (
    DEFAULT_BOUNDARIES,
    CoupledBoundaries,
    CoupledModel,
    ElectrostaticModel,
    ModelSolution,
    PhysicsModel,
    concentration_field_name,
)

__all__ = [
    "LadderResult",
    "Rung",
    "RungResult",
    "TransferError",
    "bias_schedule",
    "default_ladder",
    "mesh_report",
    "ramp_schedule",
    "run_ladder",
    "transfer",
]

logger = logging.getLogger(__name__)

BIAS_ONSET_V = 0.05
"""Below this magnitude the bias ramp takes fine steps (NUM-18 stage 5)."""

FINE_BIAS_STEP_V = 0.01
"""The "about 10 mV near onset" of NUM-18 stage 5."""

COARSE_BIAS_STEP_V = 0.025
"""Step above the onset, where the response is closer to linear."""

LADDER_START_CONCENTRATION_M = 0.05
"""Bottom of the NUM-18 stage 9 sweep, and the easiest rung of the envelope.

The double layer is widest and the packing fraction smallest at low salt, so a
ladder built here and swept upwards meets the hard configuration last and warm.
"""


class TransferError(RuntimeError):
    """A solution cannot be carried onto the next rung's space.

    Raised rather than worked around: a transfer that quietly did something else
    would hand Newton an initial guess for a different problem, and the run that
    followed would converge to a plausible wrong answer (QR-12).
    """


@dataclass(frozen=True)
class Rung:
    """One rung of the ladder: a model, a mesh, and the arguments to solve it with.

    Parameters
    ----------
    name
        Human-readable rung name, used in logs and in the run record.
    stage
        Which of the nine NUM-18 stages this rung belongs to. A ramp expands into
        several rungs sharing a stage, so the stage is what makes the ladder's
        conformance to NUM-18 checkable.
    model
        The physics model of this rung.
    mesh
        The mesh to solve it on. Carried per rung so that NUM-19's
        between-rungs-only adaptation drops in without changing this signature.
    boundaries
        The boundary vocabulary the space is built on.
    measures
        Symmetry and quadrature policy. Its element order must match the model's.
    solve_kwargs
        Everything else the model's ``solve`` takes: ``potential_values``,
        ``fixed_charge``, ``surface_charge``, ``wall_distance_nm``,
        ``debye_length_nm`` and so on.
    """

    name: str
    stage: int
    model: PhysicsModel
    mesh: Mesh
    boundaries: CoupledBoundaries = DEFAULT_BOUNDARIES
    measures: Measures = AXISYMMETRIC
    solve_kwargs: Mapping[str, Option] = field(default_factory=dict)


@dataclass(frozen=True)
class RungResult:
    """What one rung cost and how it converged, for the FR-25 manifest."""

    name: str
    stage: int
    model: str
    seconds: float
    transferred_fields: tuple[str, ...]
    cold_fields: tuple[str, ...]
    newton: Mapping[str, Option] | None

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
            "newton": dict(self.newton) if self.newton is not None else None,
        }


@dataclass(frozen=True)
class LadderResult:
    """The converged state at the top of the ladder, and the record of getting there."""

    solution: ModelSolution
    rungs: tuple[RungResult, ...]
    mesh: Mapping[str, Option]

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
        """Smallest damping any rung needed.

        The end-of-phase report asks which rungs needed damping below 0.1; this
        is the number it is asking for, and :meth:`summary` carries the per-rung
        breakdown that says *which*.
        """
        return min((rung.minimum_damping_used for rung in self.rungs), default=1.0)

    def summary(self) -> dict[str, Option]:
        """Return the whole ladder's record, for the provenance manifest (FR-25).

        A result whose manifest cannot reconstruct the run is not a result, and a
        continuation run is not reconstructible from its final state alone: the
        path taken to it is part of how it was obtained.
        """
        return {
            "rungs": [rung.summary() for rung in self.rungs],
            "stages": sorted({rung.stage for rung in self.rungs}),
            "mesh": dict(self.mesh),
            "seconds": self.seconds,
            "iterations": self.iterations,
            "minimum_damping_used": self.minimum_damping_used,
        }


def mesh_report(mesh: Mesh) -> dict[str, Option]:
    """Return the mesh's size, for the record NUM-19 and FR-25 need.

    A continuation run's numbers mean nothing without the mesh they were obtained
    on, and "the mesh" is not reconstructible from the geometry alone once a size
    field has been applied.
    """
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
    """Return the bias ramp of NUM-18 stage 5, in volts, ending exactly on the target.

    About 10 mV per step up to ``onset_V`` and 25 mV above it. The onset is where
    the double layer starts to be driven appreciably out of equilibrium, and it
    is the part of the ramp a coarse step overshoots.

    Parameters
    ----------
    target_V
        The bias to reach, of either sign.
    onset_V
        Magnitude below which the fine step is used.
    fine_step_V, coarse_step_V
        Step magnitudes below and above the onset.

    Returns
    -------
    tuple[float, ...]
        Increasing in magnitude, of the target's sign, ending on the target.
        Empty at zero target, which needs no ramp.

    Raises
    ------
    ValueError
        If either step is not positive, which would not terminate.
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
    """Return ``(1/n, 2/n, ..., 1)``, the fractions of a linear ramp.

    Used for NUM-18 stage 4, where the fixed and surface charges are raised
    together from zero to their target, and for the concentration sweep of stage
    9, where it interpolates geometrically instead (see :func:`default_ladder`).

    Raises
    ------
    ValueError
        If ``steps`` is not positive.
    """
    if steps < 1:
        raise ValueError(f"a ramp needs at least one step, got {steps}")
    return tuple((index + 1) / steps for index in range(steps))


def _fields_of(model: PhysicsModel) -> dict[str, int]:
    """Return the model's field names and element orders."""
    return {declared.name: declared.order for declared in model.fields}


def _shared_fields(source: PhysicsModel, target: PhysicsModel) -> tuple[str, ...]:
    """Return the fields two models hold in common *at the same element order*.

    The one place the warm-start rule is written. A field carried at a different
    order cannot be copied and is cold-started instead, so :func:`run_ladder`
    asks here rather than restating the test: a record that counted it as
    transferred would claim a warm start that did not happen (FR-25).
    """
    before = _fields_of(source)
    return tuple(name for name, order in _fields_of(target).items() if before.get(name) == order)


def _component(state: GridFunction, model: PhysicsModel, name: str) -> GridFunction:
    """Return one field of a state by name, single-field spaces included.

    A product space exposes ``components``; a one-field space does not, and
    indexing it raises. Both appear in the ladder — stages 1 and 2 solve for
    ``phi`` alone — so the distinction is handled here rather than at four call
    sites.
    """
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
    """Carry a converged solution onto another model's space.

    Fields the two models share are interpolated by name; fields only the target
    has are left at their cold-start values, which is where
    :meth:`CoupledModel.cold_state` matters — a concentration left at zero would
    fail the NUM-17 positivity gate before Newton took a step.

    When the two field sets are identical the state is copied verbatim rather
    than interpolated. That is not only faster: an interpolation of a function
    already in the space is the identity only up to round-off, and stages 4, 5, 7,
    8 and 9 all transfer within one space, so an accumulating round-off would be
    paid a dozen times over.

    Concentrations go through :meth:`ModelSolution.concentration`, so the NUM-02
    log branch is unwrapped on the way out and reapplied on the way in. Reading
    the raw component instead would carry ``w_i`` across as though it were
    ``c~_i`` — a state that is still admissible, still converges, and is wrong.

    Parameters
    ----------
    previous
        The converged solution to start from.
    model
        The model whose space to land on.
    mesh
        The mesh. It must be the one ``previous`` was solved on.
    boundaries
        The boundary vocabulary of the target space.
    initial_concentrations
        Cold-start values for concentrations the previous model did not solve.

    Returns
    -------
    ModelSolution
        The transferred state, on the target model's space, with no convergence
        record: nothing has been solved.

    Raises
    ------
    TransferError
        If the meshes differ. Interpolating across meshes is a point evaluation
        outside the source domain wherever the two do not overlap, which returns
        a plausible number rather than raising; the cross-mesh path is deferred
        rather than approximated.
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
            f"{previous.model.name!r} and {model.name!r} share no field at the same element "
            f"order ({sorted(source)} against {sorted(target)}), so there is nothing to warm-"
            "start from; solve the next rung cold instead of pretending otherwise"
        )

    space = model.space(mesh, boundaries)
    if tuple(target) == tuple(source) and space.ndof == previous.space.ndof:
        # The cold start is not built at all here: every value it interpolated
        # would be overwritten by the copy, and each one is a mass-matrix solve
        # over the whole fluid. Most rungs of the default ladder take this path.
        state = ngs.GridFunction(space, name=f"{model.name}_state")
        state.vec.data = previous.state.vec
        logger.debug("transfer to %r: copied %d fields verbatim", model.name, len(shared))
        return ModelSolution(model=model, space=state.space, state=state)

    if isinstance(model, CoupledModel):
        state = model.cold_state(mesh, boundaries, initial_concentrations=initial_concentrations)
    else:
        state = model.cold_state(mesh, boundaries)

    species = set(model.species) if isinstance(model, CoupledModel) else set()
    for name in shared:
        matched = [ion for ion in species if concentration_field_name(ion) == name]
        if matched:
            # The concentration, not the solved variable: in the NUM-02 log
            # branch those differ by an exponential.
            value: Expression = previous.concentration(matched[0])
            if isinstance(model, CoupledModel) and model.log_variables:
                value = ngs.log(value)
        else:
            value = previous.component(name)
        _component(state, model, name).Set(value)

    logger.debug(
        "transfer to %r: interpolated %s, cold-started %s", model.name, list(shared), list(cold)
    )
    return ModelSolution(model=model, space=state.space, state=state)


def run_ladder(rungs: Sequence[Rung], *, initial: ModelSolution | None = None) -> LadderResult:
    """Solve every rung in order, each warm-started from the one before (NUM-18).

    Parameters
    ----------
    rungs
        The ladder, from the easiest configuration to the target one.
    initial
        A converged solution to warm-start the *first* rung from, transferred
        onto its space like any other. This is what makes a ladder resumable, and
        it is how a sweep walks the FR-17 envelope: the ladder is climbed once to
        one corner and every other operating point is one rung away from a
        converged neighbour, rather than another climb from cold.

    Returns
    -------
    LadderResult
        The converged state at the top and the per-rung record.

    Raises
    ------
    ValueError
        If the ladder is empty.
    nanopnp.solve.gates.GateViolationError
        If any NUM-17 assertion fails on any rung. It is allowed to propagate
        with the rung named: a ladder that swallowed a gate and carried on would
        be doing exactly what the gate exists to prevent (QR-12).
    """
    if not rungs:
        raise ValueError("a continuation ladder needs at least one rung")

    previous: ModelSolution | None = initial
    records: list[RungResult] = []
    for rung in rungs:
        transferred_fields: tuple[str, ...] = ()
        cold_fields = tuple(_fields_of(rung.model))
        carried: ModelSolution | None = None
        if previous is not None:
            # ``initial_concentrations`` is what a cold-started concentration
            # field is filled with, so the rung's own value has to reach the
            # transfer; ``solve`` ignores it once a warm start is supplied.
            carried = transfer(
                previous,
                rung.model,
                rung.mesh,
                rung.boundaries,
                initial_concentrations=rung.solve_kwargs.get("initial_concentrations"),
            )
            transferred_fields = _shared_fields(previous.model, rung.model)
            cold_fields = tuple(
                name for name in _fields_of(rung.model) if name not in transferred_fields
            )

        started = time.perf_counter()
        try:
            solution = rung.model.solve(
                rung.mesh,
                rung.measures,
                boundaries=rung.boundaries,
                **({"initial": carried} if carried is not None else {}),
                **dict(rung.solve_kwargs),
            )
        except Exception:
            # Re-raised unchanged, traceback intact: a gate violation names the
            # field and the location (QR-12) and is the diagnostic; the rung is
            # the context and belongs in the log beside it, not wrapped around
            # an exception whose type the ladder would have to reconstruct.
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
            newton=solution.newton.summary() if solution.newton is not None else None,
        )
        records.append(record)
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
    return LadderResult(solution=previous, rungs=tuple(records), mesh=mesh_report(rungs[-1].mesh))


def default_ladder(
    mesh: Mesh,
    *,
    concentration_M: float = 1.0,
    bias_V: float = 0.2,
    electrolyte: Electrolyte | None = None,
    corrections: str = "willems2020_nacl",
    surface_charge_C_m2: float = 0.0,
    fixed_charge_C_m3: float = 0.0,
    fixed_charge_domain: str | None = None,
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
) -> tuple[Rung, ...]:
    """Build the nine stages of NUM-18 for one target operating point.

    Stages 4, 5 and 9 expand into several rungs each; every rung carries the
    ``stage`` it belongs to, so conformance to NUM-18's order is a property of
    the returned sequence rather than of its length.

    Parameters
    ----------
    mesh
        The mesh every rung is solved on. One fixed mesh for the whole ladder is
        this phase's policy, which satisfies NUM-19 trivially; a future adaptive
        scheme changes only what is put in each :class:`Rung`.
    concentration_M
        Target bulk concentration.
    bias_V
        Target applied bias, of either sign, on the trans electrode.
    electrolyte, corrections
        The electrolyte, or the correction parameter file to build one from.
    surface_charge_C_m2, fixed_charge_C_m3
        Targets of the stage-4 ramp, in SI. Converted to the nondimensional
        variables through the NUM-09 scale set of the model that carries them.
    fixed_charge_domain
        Material the fixed charge is confined to. ``None``, the default, spreads
        it over the whole domain, which is what a uniformly charged medium means.
        An *analyte* charge is not that: ``rho_part = q/V`` lives in the body and
        nowhere else, so a body charge passed without this argument would also
        charge the electrolyte it is suspended in and drive a space charge the
        physical problem does not have.
    wall_potential_V
        Zeta potential imposed on the pore wall during the two Poisson-Boltzmann
        stages, in volts. Zero by default, and then those two stages are
        trivially ``phi = 0``: NUM-18 puts the charge ramp at stage 4, *after*
        them, so with no zeta there is nothing yet for PB to screen. Supplying
        one turns stages 1 and 2 into the Poisson-Boltzmann initialiser NUM-20
        names as the cure for the high-surface-charge failure mode.
    wall_distance_nm
        The PHY-02 distance field, used from stage 7 onwards where the wall
        corrections come on.
    solid_permittivities
        Relative permittivity per solid material. Omitting it leaves the membrane
        at the electrolyte's permittivity, which is about 24 times too large and
        changes the field the current is driven by.
    boundaries, measures
        The boundary vocabulary and the quadrature policy of every rung.
    start_concentration_M
        Concentration the first eight stages are built at, swept to
        ``concentration_M`` in stage 9. ``None`` builds the whole ladder at the
        target and omits stage 9.
    charge_steps, concentration_steps
        Number of sub-rungs in the stage-4 and stage-9 ramps.
    surface_charge_boundary
        Boundary the surface charge sits on.
    corrections_active
        Whether the ladder ends at ``epnp-ns`` or at classical ``pnp-ns``.
        ``False`` **omits stages 7 and 8** rather than running them as no-ops —
        there is nothing to enable — and sweeps stage 9 classically. It is what
        makes the PHY-21 ablation a sweep over configurations rather than a
        rebuild: the same ladder, the same mesh, the same operating point, and
        the difference attributable to the corrections alone (section 7.4).

    Returns
    -------
    tuple[Rung, ...]
        The ladder, ready for :func:`run_ladder`.
    """
    import ngsolve as ngs

    solids = dict(solid_permittivities or {})
    build_M = concentration_M if start_concentration_M is None else start_concentration_M
    base = electrolyte if electrolyte is not None else Electrolyte.from_parameter_file(corrections)

    def _coupled(
        name: str, switches: CorrectionSwitches, *, flow: bool, salt: float
    ) -> CoupledModel:
        """Return one coupled configuration of the ladder.

        Every rung is the same class with different switches, which is what
        makes "enable the corrections last" a change of configuration rather
        than a change of code path (PHY-21).
        """
        return CoupledModel(
            # ``with_switches`` rebuilds the resolved corrections; ``replace``
            # would change only the record and leave every stage of the ladder
            # evaluating whatever ``base`` was built with.
            electrolyte=base.with_switches(switches),
            concentration_M=salt,
            name=name,
            flow=flow,
            order=measures.element_order,
            solid_permittivities=solids,
        )

    classical = CorrectionSwitches.classical()
    corrected = CorrectionSwitches.for_model(corrections)
    without_steric = corrected.without("steric")

    reference = _coupled("pnp", classical, flow=False, salt=build_M)
    thermal_V = reference.scales.potential_V

    def _potential(bias: float) -> Expression:
        """Return the essential potential data for one applied bias, in ``V_T``."""
        return mesh.BoundaryCF({"cis": 0.0, "trans": bias / thermal_V})

    zero_bias = _potential(0.0)
    rungs: list[Rung] = []

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
    pb_stages: tuple[tuple[int, str, Literal["linear", "sinh"]], ...] = (
        (1, "pb-linear", "linear"),
        (2, "pb", "sinh"),
    )
    for stage, name, screening in pb_stages:
        rungs.append(
            Rung(
                name=f"{stage}-{name}",
                stage=stage,
                model=ElectrostaticModel(
                    name=name, screening=screening, order=measures.element_order
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
            solve_kwargs={"potential_values": zero_bias},
        )
    )

    # -- stage 4: ramp the fixed and surface charges together --------------
    # Taken from the reference model and reused by every later rung, including
    # the stage-9 sweep at other concentrations. That is correct rather than
    # convenient: eps V_T / a^2 and eps V_T / a carry no c_0, so unlike the
    # current and flux scales these two do not move with the salt.
    charge_scale = reference.scales.charge_density_C_m3
    surface_scale = reference.scales.surface_charge_C_m2

    def _charges(fraction: float = 1.0) -> dict[str, Option]:
        """Return the charges of one rung: the stage-4 ramp, or its converged end.

        A charge left at zero is omitted rather than passed as ``CF(0.0)``: the
        form would then assemble an integral that is identically zero on every
        rung from stage 4 onwards, and the surface term would name a boundary
        the geometry need not even carry.
        """
        charges: dict[str, Option] = {}
        if fixed_charge_C_m3 != 0.0:
            density = fraction * fixed_charge_C_m3 / charge_scale
            charges["fixed_charge"] = (
                ngs.CF(density)
                if fixed_charge_domain is None
                else mesh.MaterialCF({fixed_charge_domain: density}, default=0.0)
            )
        if surface_charge_C_m2 != 0.0:
            charges["surface_charge"] = ngs.CF(fraction * surface_charge_C_m2 / surface_scale)
            charges["surface_charge_boundary"] = surface_charge_boundary
        return charges

    if surface_charge_C_m2 != 0.0 or fixed_charge_C_m3 != 0.0:
        for fraction in ramp_schedule(charge_steps):
            rungs.append(
                Rung(
                    name=f"4-ramp-charge-{fraction:.2f}",
                    stage=4,
                    model=reference,
                    mesh=mesh,
                    boundaries=boundaries,
                    measures=measures,
                    solve_kwargs={"potential_values": zero_bias, **_charges(fraction)},
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
                solve_kwargs={"potential_values": _potential(bias), **_charges()},
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
    # Same rule as stage 6 below: a classical rung has no wall correction able
    # to read the distance field, and recording one it never evaluated would
    # make the PHY-21 ablation and its reference disagree on the manifest.
    wall_field: dict[str, Option] = (
        {"wall_distance_nm": wall_distance_nm} if corrections_active else {}
    )
    target_name = "epnp-ns" if corrections_active else "pnp-ns"
    for stage, label, name, switches in physics_stages:
        # The distance field is passed only where a wall correction can read it;
        # stage 6 is still classical and would carry it unused.
        extra: dict[str, Option] = {} if stage == 6 else wall_field
        rungs.append(
            Rung(
                name=f"{stage}-{label}",
                stage=stage,
                model=_coupled(name, switches, flow=True, salt=build_M),
                mesh=mesh,
                boundaries=boundaries,
                measures=measures,
                solve_kwargs={"potential_values": _potential(bias_V), **_charges(), **extra},
            )
        )

    # -- stage 9: sweep the salt ------------------------------------------
    if start_concentration_M is not None and not math.isclose(build_M, concentration_M):
        # Geometric rather than linear: the Debye length goes as c^(-1/2), so it
        # is the ratio between rungs that measures how far the double layer has
        # moved, not the difference.
        ratio = concentration_M / build_M
        for fraction in ramp_schedule(concentration_steps):
            salt = build_M * ratio**fraction
            rungs.append(
                Rung(
                    name=f"9-salt-{salt:.4g}M",
                    stage=9,
                    model=_coupled(target_name, target_switches, flow=True, salt=salt),
                    mesh=mesh,
                    boundaries=boundaries,
                    measures=measures,
                    solve_kwargs={
                        "potential_values": _potential(bias_V),
                        **_charges(),
                        **wall_field,
                    },
                )
            )

    return tuple(rungs)

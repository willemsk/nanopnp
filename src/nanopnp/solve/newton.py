"""Monolithic damped Newton for the coupled system (NUM-16, NUM-17).

The five fields are solved together, with no segregation groups, because the
coupling that makes the problem hard is exactly the coupling a segregated scheme
throws away: the potential sees the ion charge, the ions see the potential and
the flow, and the flow sees the electrical body force. The reference model
solved this fully coupled, and so does this.

Damping is the mechanism that makes a cold start survivable, and its policy is
the delicate part. Two rules from NUM-16 shape it:

* the damping factor is bounded below (1e-2 by default), and
* **if the minimally damped step still fails to reduce the residual, that step
  is accepted rather than the solve aborted.**

The second rule looks like giving up, and it is not. A Newton step that raises
the residual is usually a step across a fold in a strongly nonlinear region; the
next linearisation is taken at the new point, and the sequence recovers. Aborting
there instead throws away a run that was going to converge. What must *not* be
tolerated is a step into an unphysical state, and that is what the NUM-17 gates
are for: they abort, and this loop makes no attempt to talk them out of it.

The reference settings of NUM-16 (initial damping 0.2, minimum 1e-2, recovery
0.2, 100 iterations, relative tolerance 1e-6) are the defaults. What the
reference does *not* record is how the damping recovers after a successful step,
so :attr:`NewtonSettings.growth_factor` is this project's own choice and is
flagged as such.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from nanopnp.core.typing import Expression, GridFunction, Option
from nanopnp.solve.gates import Gate, GateViolationError, check_all
from nanopnp.solve.linear import DEFAULT_SOLVER, check_solver, solve_correction

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NewtonSettings:
    """Damped-Newton parameters; the defaults are the NUM-16 reference settings.

    Parameters
    ----------
    initial_damping
        Damping factor of the first step. 0.2 in the reference.
    minimum_damping
        Lower bound. At this value a step that fails to reduce the residual is
        accepted anyway (NUM-16).
    recovery_damping
        Factor by which the damping is cut when a trial step is rejected.
    growth_factor
        Factor by which the damping is restored after an accepted step, capped
        at 1. **Not a reference setting** — the reference records no recovery
        rule — so it is named separately rather than folded into
        ``recovery_damping``.
    max_iterations
        Iteration cap. 100 in the reference.
    relative_tolerance
        Convergence tolerance, 1e-6 in the reference. Two tests share it and
        either one suffices: the residual has fallen to this multiple of its
        value on entry, or the relative Newton update ``||du|| / ||u||`` is
        below it.

        The second test is the one the reference actually used — COMSOL's
        relative tolerance is on the solution update, not on the residual — and
        it is what makes a warm start idempotent. A residual-only criterion
        measured against the entry residual has the pathology that re-solving an
        already-converged state demands another six orders of magnitude, which
        is exactly the operation the continuation ladder performs at every rung
        (NUM-18).
    absolute_tolerance
        Residual floor, for the case where the initial residual is already at
        round-off.
    reference_norm
        Floor on the solution norm in the relative-update test, so that a state
        near zero does not make every update look large. 1 is the right value
        because NUM-09 leaves every field O(1).
    """

    initial_damping: float = 0.2
    minimum_damping: float = 1.0e-2
    recovery_damping: float = 0.2
    growth_factor: float = 2.0
    max_iterations: int = 100
    relative_tolerance: float = 1.0e-6
    absolute_tolerance: float = 1.0e-12
    reference_norm: float = 1.0

    def __post_init__(self) -> None:
        """Reject settings that cannot describe a damping schedule."""
        if not 0.0 < self.minimum_damping <= self.initial_damping <= 1.0:
            raise ValueError(
                "damping factors must satisfy 0 < minimum <= initial <= 1, got "
                f"minimum {self.minimum_damping}, initial {self.initial_damping}"
            )
        if not 0.0 < self.recovery_damping < 1.0:
            raise ValueError(
                f"recovery_damping must cut the step, so 0 < f < 1, got {self.recovery_damping}"
            )
        if self.growth_factor < 1.0:
            raise ValueError(
                f"growth_factor must restore damping, so f >= 1, got {self.growth_factor}"
            )
        if self.max_iterations < 1:
            raise ValueError(f"max_iterations must be positive, got {self.max_iterations}")


DEFAULT_SETTINGS = NewtonSettings()
"""The NUM-16 reference settings."""


@dataclass(frozen=True)
class NewtonStep:
    """One accepted Newton step, for the convergence record.

    Parameters
    ----------
    iteration
        1-based index.
    residual
        Residual norm *after* the step.
    damping
        Damping factor the step was taken with.
    trials
        How many trial step lengths were tried before acceptance.
    forced
        Whether the step was accepted at minimum damping without reducing the
        residual, per NUM-16.
    """

    iteration: int
    residual: float
    damping: float
    trials: int
    forced: bool


@dataclass
class NewtonResult:
    """Outcome of a damped-Newton solve, for the provenance manifest (FR-25)."""

    converged: bool
    iterations: int
    initial_residual: float
    residual: float
    history: list[NewtonStep] = field(default_factory=list)

    @property
    def relative_residual(self) -> float:
        """Final residual as a fraction of the initial one."""
        if self.initial_residual == 0.0:
            return 0.0
        return self.residual / self.initial_residual

    @property
    def minimum_damping_used(self) -> float:
        """Smallest damping factor any accepted step was taken with.

        The diagnostic the phase report asks for: which continuation rungs
        needed damping below 0.1.
        """
        return min((step.damping for step in self.history), default=1.0)

    @property
    def forced_steps(self) -> int:
        """How many steps were accepted at minimum damping without reduction."""
        return sum(1 for step in self.history if step.forced)

    def summary(self) -> dict[str, Option]:
        """Return a record of the solve, for logs and the manifest."""
        return {
            "converged": self.converged,
            "iterations": self.iterations,
            "initial_residual": self.initial_residual,
            "residual": self.residual,
            "relative_residual": self.relative_residual,
            "minimum_damping_used": self.minimum_damping_used,
            "forced_steps": self.forced_steps,
        }


class NewtonDivergenceError(RuntimeError):
    """Newton reached its iteration cap without meeting the tolerance."""


def damped_newton(
    residual_form: Expression,
    solution: GridFunction,
    *,
    settings: NewtonSettings = DEFAULT_SETTINGS,
    solver: str = DEFAULT_SOLVER,
    state_gates: Sequence[Gate] = (),
    increment: GridFunction | None = None,
    increment_gates: Sequence[Gate] = (),
    freedofs: Option = None,
    callback: Callable[[NewtonStep], None] | None = None,
    raise_on_failure: bool = True,
) -> NewtonResult:
    """Solve ``residual_form(u) = 0`` by damped Newton, gated at every step.

    Parameters
    ----------
    residual_form
        An unassembled ``BilinearForm`` holding the residual, written in the
        **trial function**. A residual written in the grid function assembles a
        Jacobian that is identically zero, silently; see
        ``physics/pb.py::nonlinear_pb_residual``.
    solution
        Grid function holding the initial guess on entry, including any
        inhomogeneous Dirichlet data, and the solution on exit. It is updated in
        place at every accepted step, so any coefficient function built from it
        — including those the gates hold — sees the current iterate.
    settings
        Damping and tolerance policy.
    solver
        Direct linear solver for the Jacobian.
    state_gates
        NUM-17 gates checked on the entry state and on each accepted iterate:
        concentration positivity and packing fraction. A violation propagates as
        :class:`~nanopnp.solve.gates.GateViolationError`, restores the last
        admissible iterate and stops the solve. Checking on entry matters
        because a warm start whose entry residual is already at the floor
        returns without taking a step, and an unphysical state would otherwise
        pass through unexamined (NUM-18).
    increment
        Grid function that the *damped* increment is written into before each
        acceptance test, so that ``increment_gates`` can inspect it. One is
        allocated if omitted, which is only valid when ``increment_gates`` is
        empty: a gate built over a grid function this loop does not write would
        assert nothing.
    increment_gates
        NUM-17 gates checked on the damped increment, namely the potential
        increment cap. These are treated as a step-length condition first: a
        violation reduces the damping and retries, and only aborts if the
        minimally damped step still violates the cap. That reading reconciles
        NUM-16 (accept the minimally damped step) with NUM-17 (a violation
        aborts): damping exists precisely to shorten an over-long step, and a
        cap that survives maximal damping is a genuine failure of the state.
    freedofs
        Degrees of freedom to solve for; ``solution.space.FreeDofs()`` by
        default.
    callback
        Called with each accepted step, for continuation logging.
    raise_on_failure
        Raise :class:`NewtonDivergenceError` when the iteration cap is reached
        without convergence. Set ``False`` to inspect the result instead.

    Returns
    -------
    NewtonResult
        The convergence record.

    Raises
    ------
    ValueError
        If ``increment_gates`` is given without the ``increment`` they inspect.
    NewtonDivergenceError
        If the iteration cap is reached and ``raise_on_failure``.
    nanopnp.solve.gates.GateViolationError
        If any NUM-17 assertion fails.
    """
    import ngsolve as ngs

    check_solver(solver)
    if increment_gates and increment is None:
        raise ValueError(
            "increment_gates were given without an increment; the gates would inspect a grid "
            "function this loop never writes and the NUM-17 cap would pass unconditionally"
        )
    space = solution.space
    if freedofs is None:
        freedofs = space.FreeDofs()
    projector = ngs.Projector(freedofs, True)

    step = increment if increment is not None else ngs.GridFunction(space)
    direction = solution.vec.CreateVector()
    residual = solution.vec.CreateVector()
    previous = solution.vec.CreateVector()

    def residual_norm() -> float:
        """Return the free-DOF norm of the residual at the current iterate."""
        residual_form.Apply(solution.vec, residual)
        projector.Project(residual)
        return float(ngs.Norm(residual))

    check_all(state_gates)  # NUM-17 also holds of the state the caller handed in
    initial = residual_norm()
    target = max(settings.relative_tolerance * initial, settings.absolute_tolerance)
    result = NewtonResult(
        converged=initial <= target, iterations=0, initial_residual=initial, residual=initial
    )
    if result.converged:
        logger.debug("Newton: initial residual %.3e already below tolerance", initial)
        return result

    damping = settings.initial_damping
    current = initial

    for iteration in range(1, settings.max_iterations + 1):
        residual_form.AssembleLinearization(solution.vec)
        solve_correction(residual_form.mat, residual, direction, freedofs, solver=solver)
        previous.data = solution.vec
        relative_update = float(ngs.Norm(direction)) / max(
            float(ngs.Norm(solution.vec)), settings.reference_norm
        )

        trials = 0
        forced = False
        while True:
            trials += 1
            step.vec.data = -damping * direction
            projector.Project(step.vec)  # the gates must see the increment the state took
            solution.vec.data = previous + step.vec
            at_minimum = damping <= settings.minimum_damping

            try:
                check_all(increment_gates)
            except GateViolationError:
                if at_minimum:
                    solution.vec.data = previous
                    raise
                damping = max(settings.minimum_damping, damping * settings.recovery_damping)
                continue

            trial_residual = residual_norm()
            if trial_residual < current or at_minimum:
                forced = trial_residual >= current
                break
            damping = max(settings.minimum_damping, damping * settings.recovery_damping)

        if forced:
            logger.warning(
                "Newton step %d accepted at minimum damping %.3g without reducing the residual "
                "(%.3e -> %.3e); NUM-16 prefers this to aborting",
                iteration,
                damping,
                current,
                trial_residual,
            )
        try:
            check_all(state_gates)
        except GateViolationError:
            # Same contract as the increment gates: an abort leaves the caller
            # holding the last admissible iterate, not the rejected one, so a
            # continuation driver that catches this can still warm-start.
            solution.vec.data = previous
            raise

        current = trial_residual
        record = NewtonStep(
            iteration=iteration,
            residual=current,
            damping=damping,
            trials=trials,
            forced=forced,
        )
        result.history.append(record)
        result.iterations = iteration
        result.residual = current
        logger.debug(
            "Newton step %d: residual %.3e, damping %.3g, %d trial(s)",
            iteration,
            current,
            damping,
            trials,
        )
        if callback is not None:
            callback(record)

        # The update test is damping-independent because it uses the full Newton
        # direction, not the damped step; a forced step is never convergence.
        if current <= target or (not forced and relative_update <= settings.relative_tolerance):
            result.converged = True
            return result

        damping = min(1.0, damping * settings.growth_factor)

    if raise_on_failure:
        raise NewtonDivergenceError(
            f"damped Newton did not converge in {settings.max_iterations} iterations: "
            f"residual {result.residual:.3e}, initial {initial:.3e}, relative "
            f"{result.relative_residual:.3e}, target {settings.relative_tolerance:.3e}"
        )
    return result

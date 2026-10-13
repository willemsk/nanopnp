"""Monolithic damped Newton for the coupled system (NUM-16, NUM-17)."""

from __future__ import annotations

import logging
import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field

from nanopnp.core.typing import Expression, GridFunction, Option
from nanopnp.numerics.defaults import DEFAULT_NONLINEAR_MAX_ITER, DEFAULT_NONLINEAR_RTOL
from nanopnp.numerics.gates import Gate, GateViolationError, check_all
from nanopnp.numerics.linear import DEFAULT_SOLVER, check_solver, solve_correction

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class NewtonSettings:
    initial_damping: float = 0.2
    minimum_damping: float = 1.0e-2
    recovery_damping: float = 0.2
    # Not recorded by the reference model: this project's own choice.
    growth_factor: float = 2.0
    max_iterations: int = DEFAULT_NONLINEAR_MAX_ITER
    relative_tolerance: float = DEFAULT_NONLINEAR_RTOL
    absolute_tolerance: float = 1.0e-12
    reference_norm: float = 1.0
    field_floor_ratio: float = 1.0e-6

    def __post_init__(self) -> None:
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
        # ``not 0 < x < inf`` rather than ``x <= 0``, so that NaN is refused too.
        if not 0.0 < self.field_floor_ratio < math.inf:
            raise ValueError(
                f"field_floor_ratio must be positive and finite, got {self.field_floor_ratio}"
            )


DEFAULT_SETTINGS = NewtonSettings()


@dataclass(frozen=True)
class NewtonStep:
    iteration: int
    residual: float
    update: float
    damping: float
    trials: int
    forced: bool


@dataclass
class NewtonResult:
    converged: bool
    iterations: int
    initial_residual: float
    residual: float
    history: list[NewtonStep] = field(default_factory=list)

    @property
    def relative_residual(self) -> float:
        if self.initial_residual == 0.0:
            return 0.0
        return self.residual / self.initial_residual

    @property
    def minimum_damping_used(self) -> float:
        return min((step.damping for step in self.history), default=1.0)

    @property
    def forced_steps(self) -> int:
        return sum(1 for step in self.history if step.forced)

    def summary(self) -> dict[str, Option]:
        return {
            "converged": self.converged,
            "iterations": self.iterations,
            "initial_residual": self.initial_residual,
            "residual": self.residual,
            "relative_residual": self.relative_residual,
            "minimum_damping_used": self.minimum_damping_used,
            "forced_steps": self.forced_steps,
        }


class NewtonDivergenceError(RuntimeError): ...


def _largest_update(ratios: Sequence[float]) -> float:
    return max(ratios, key=lambda ratio: math.inf if math.isnan(ratio) else ratio)


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
    # A grid function, so per-field blocks are read off its components without a copy.
    direction_gf = ngs.GridFunction(space)
    direction = direction_gf.vec
    residual = solution.vec.CreateVector()
    previous = solution.vec.CreateVector()

    def residual_norm() -> float:
        residual_form.Apply(solution.vec, residual)
        projector.Project(residual)
        return float(ngs.Norm(residual))

    check_all(state_gates)  # NUM-17 also holds of the state the caller handed in
    initial = residual_norm()
    result = NewtonResult(
        converged=initial <= settings.absolute_tolerance,
        iterations=0,
        initial_residual=initial,
        residual=initial,
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

        global_ref = max(float(ngs.Norm(solution.vec)), settings.reference_norm)
        field_floor = settings.field_floor_ratio * global_ref
        if solution.components:
            relative_update = _largest_update(
                [
                    float(ngs.Norm(d_comp.vec)) / max(float(ngs.Norm(s_comp.vec)), field_floor)
                    for d_comp, s_comp in zip(
                        direction_gf.components, solution.components, strict=True
                    )
                ]
            )
        else:
            relative_update = float(ngs.Norm(direction)) / max(
                float(ngs.Norm(solution.vec)), field_floor
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
                # ``not <``, not ``>=``: a NaN trial residual is a forced step,
                # which can never be taken as convergence on the update alone.
                forced = not trial_residual < current
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
            # An abort leaves the last admissible iterate, so a caller can warm-start.
            solution.vec.data = previous
            raise

        current = trial_residual
        record = NewtonStep(
            iteration=iteration,
            residual=current,
            update=relative_update,
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

        # The update test uses the full Newton direction, not the damped step.
        if current <= settings.absolute_tolerance or (
            not forced and relative_update <= settings.relative_tolerance
        ):
            result.converged = True
            return result

        damping = min(1.0, damping * settings.growth_factor)

    if raise_on_failure:
        # Name both NUM-16 tests and what each measured, not the relative residual.
        last_update = result.history[-1].update if result.history else math.nan
        raise NewtonDivergenceError(
            f"damped Newton did not converge in {settings.max_iterations} iterations: "
            f"largest per-field relative update {last_update:.3e} on the undamped direction "
            f"against {settings.relative_tolerance:.3e}, residual {result.residual:.3e} "
            f"against the absolute floor {settings.absolute_tolerance:.3e} "
            f"(initial {initial:.3e})"
        )
    return result

"""Damped Newton: the NUM-16 damping policy and its interaction with the NUM-17 gates.

The two rules worth testing here are the ones that are easy to get subtly wrong
and impossible to notice afterwards. First, that a step which fails to reduce
the residual at minimum damping is **accepted rather than aborted** — the rule
that keeps a run alive across a fold in the residual. Second, that a gate
violation on the increment is treated as a step-length problem first, so the
damping loop gets a chance to fix it, and only aborts when the minimally damped
step still violates the cap.

The nonlinear problem used throughout is scalar Poisson-Boltzmann on a planar
slab, whose ``sinh`` is nonlinear enough to need damping from a cold start and
whose answer is known in closed form.
"""

from __future__ import annotations

import logging

import ngsolve as ngs
import pytest

from nanopnp.mesh.primitives import SlabGeometry
from nanopnp.physics.measures import PLANAR
from nanopnp.physics.pb import debye_length_nm, nonlinear_pb_residual
from nanopnp.solve.gates import FieldSampler, GateViolationError, PotentialIncrementGate
from nanopnp.solve.newton import (
    DEFAULT_SETTINGS,
    NewtonDivergenceError,
    NewtonSettings,
    damped_newton,
)

CONCENTRATION_M = 0.1
"""Bulk concentration of the test problem, in mol/L."""

WALL_POTENTIAL = 4.0
"""Wall potential in thermal voltages: sinh(4) = 27, so the problem is genuinely nonlinear."""


class _AlwaysFails:
    """A gate that rejects every state, standing in for a positivity failure."""

    name = "test gate"

    def check(self) -> None:
        """Reject the state unconditionally."""
        raise GateViolationError(self.name, "c_test", -1.0, (0.5, 0.5), ("x", "y"))


@pytest.fixture
def problem() -> tuple[ngs.Mesh, ngs.FESpace, float]:
    """Return a slab mesh, a P2 space with the wall constrained, and the Debye length."""
    screening_nm = debye_length_nm(CONCENTRATION_M)
    mesh = SlabGeometry(width_nm=8.0 * screening_nm).generate(maxh_nm=screening_nm / 3.0)
    space = ngs.H1(mesh, order=2, dirichlet="wall")
    return mesh, space, screening_nm


def _residual_form(space: ngs.FESpace, screening_nm: float) -> ngs.BilinearForm:
    """Return the nonlinear PB residual, written in the trial function."""
    trial, test = space.TnT()
    form = ngs.BilinearForm(space)
    form += nonlinear_pb_residual(trial, test, PLANAR, debye_length_nm=screening_nm)
    return form


def _initial_state(space: ngs.FESpace, mesh: ngs.Mesh) -> ngs.GridFunction:
    """Return a cold start carrying only the inhomogeneous Dirichlet data."""
    state = ngs.GridFunction(space)
    state.Set(ngs.CF(WALL_POTENTIAL), definedon=mesh.Boundaries("wall"))
    return state


def test_num16_reference_settings_are_the_defaults() -> None:
    """The defaults are the reference values of the NUM-16 table."""
    assert DEFAULT_SETTINGS.initial_damping == 0.2
    assert DEFAULT_SETTINGS.minimum_damping == 1.0e-2
    assert DEFAULT_SETTINGS.recovery_damping == 0.2
    assert DEFAULT_SETTINGS.max_iterations == 100
    assert DEFAULT_SETTINGS.relative_tolerance == 1.0e-6


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("initial_damping", 1.5),
        ("minimum_damping", 0.0),
        ("recovery_damping", 1.0),
        ("growth_factor", 0.5),
        ("max_iterations", 0),
    ],
)
def test_num16_incoherent_settings_are_rejected(field: str, value: float) -> None:
    """A damping schedule that cannot work is refused at construction, not at step 40."""
    with pytest.raises(ValueError, match=field.split("_")[0]):
        NewtonSettings(**{field: value})  # type: ignore[arg-type]


def test_num16_converges_on_nonlinear_poisson_boltzmann(
    problem: tuple[ngs.Mesh, ngs.FESpace, float],
) -> None:
    """A cold start at a strongly nonlinear wall potential converges and holds its data."""
    mesh, space, screening_nm = problem
    state = _initial_state(space, mesh)

    result = damped_newton(_residual_form(space, screening_nm), state)

    assert result.converged
    assert result.relative_residual <= DEFAULT_SETTINGS.relative_tolerance
    assert state(mesh(0.0, 0.5)) == pytest.approx(WALL_POTENTIAL, rel=1e-12)


def test_num16_damping_starts_at_the_initial_factor_and_recovers(
    problem: tuple[ngs.Mesh, ngs.FESpace, float],
) -> None:
    """Damping opens at 0.2 and reaches 1 once the iterates enter the quadratic regime."""
    mesh, space, screening_nm = problem
    state = _initial_state(space, mesh)

    result = damped_newton(_residual_form(space, screening_nm), state)

    assert result.history[0].damping == pytest.approx(DEFAULT_SETTINGS.initial_damping)
    assert max(step.damping for step in result.history) == pytest.approx(1.0)
    assert result.history[-1].residual < result.history[0].residual


def test_num16_residual_history_is_monotone_and_ends_quadratic(
    problem: tuple[ngs.Mesh, ngs.FESpace, float],
) -> None:
    """Once undamped, the residual squares each step; that is the check on the Jacobian.

    A Jacobian that is merely approximate still converges, but linearly. Seeing
    the last reduction beat the square of the previous one is the evidence that
    the linearisation is exact, and therefore that the residual form was written
    in the trial function rather than in the grid function.
    """
    mesh, space, screening_nm = problem
    state = _initial_state(space, mesh)

    result = damped_newton(_residual_form(space, screening_nm), state)
    residuals = [step.residual for step in result.history]

    assert residuals == sorted(residuals, reverse=True)
    assert residuals[-1] < residuals[-2] ** 1.8


def test_num17_increment_cap_is_a_step_length_condition_first(
    problem: tuple[ngs.Mesh, ngs.FESpace, float],
) -> None:
    """An over-long step is damped down rather than aborted, and the solve still converges.

    A cap so tight that the first undamped step must violate it: if the gate
    aborted on sight the solve would fail, and if it were ignored the cap would
    be decorative. Neither happens — the damping loop shortens the step.
    """
    mesh, space, screening_nm = problem
    state = _initial_state(space, mesh)
    increment = ngs.GridFunction(space)
    sampler = FieldSampler(mesh, coordinates=("x", "y"))

    result = damped_newton(
        _residual_form(space, screening_nm),
        state,
        increment=increment,
        increment_gates=[PotentialIncrementGate(sampler, increment, limit=0.35)],
    )

    assert result.converged
    assert any(step.trials > 1 for step in result.history)
    assert result.minimum_damping_used < DEFAULT_SETTINGS.initial_damping


def test_num17_increment_cap_aborts_when_even_the_minimal_step_violates_it(
    problem: tuple[ngs.Mesh, ngs.FESpace, float],
) -> None:
    """A cap the minimally damped step cannot meet is a genuine failure and aborts."""
    mesh, space, screening_nm = problem
    state = _initial_state(space, mesh)
    increment = ngs.GridFunction(space)
    sampler = FieldSampler(mesh, coordinates=("x", "y"))

    with pytest.raises(GateViolationError, match="increment"):
        damped_newton(
            _residual_form(space, screening_nm),
            state,
            increment=increment,
            increment_gates=[PotentialIncrementGate(sampler, increment, limit=1e-8)],
        )


def test_num17_a_rejected_step_leaves_the_state_untouched(
    problem: tuple[ngs.Mesh, ngs.FESpace, float],
) -> None:
    """When a gate aborts, the solution holds the last admissible iterate, not the bad one."""
    mesh, space, screening_nm = problem
    state = _initial_state(space, mesh)
    increment = ngs.GridFunction(space)
    sampler = FieldSampler(mesh, coordinates=("x", "y"))
    before = state.vec.CreateVector()
    before.data = state.vec

    with pytest.raises(GateViolationError):
        damped_newton(
            _residual_form(space, screening_nm),
            state,
            increment=increment,
            increment_gates=[PotentialIncrementGate(sampler, increment, limit=1e-8)],
        )

    assert ngs.Norm(state.vec - before) == pytest.approx(0.0, abs=1e-14)


def test_num16_state_gate_violation_stops_the_solve(
    problem: tuple[ngs.Mesh, ngs.FESpace, float],
) -> None:
    """A state gate aborts unconditionally; damping is not an answer to an unphysical state."""
    mesh, space, screening_nm = problem
    state = _initial_state(space, mesh)

    with pytest.raises(GateViolationError, match="c_test"):
        damped_newton(_residual_form(space, screening_nm), state, state_gates=[_AlwaysFails()])


def test_num17_state_gates_run_on_the_entry_state() -> None:
    """NUM-17 holds of the state the caller handed in, not only of the steps taken.

    A warm start whose entry residual is already at the floor returns without
    taking a step (NUM-18 does exactly that at every rung), so a gate checked
    only after an accepted step would never look at it.
    """
    mesh = SlabGeometry(width_nm=1.0).generate(maxh_nm=1.0)
    space = ngs.H1(mesh, order=1)
    trial, test = space.TnT()
    form = ngs.BilinearForm(space)
    form += trial * test * ngs.dx
    state = ngs.GridFunction(space)
    state.vec[:] = 0.0  # residual is exactly zero: no step will be taken

    unconditional = _AlwaysFails()
    assert damped_newton(form, state).converged
    with pytest.raises(GateViolationError, match="c_test"):
        damped_newton(form, state, state_gates=[unconditional])


def test_num17_a_state_gate_abort_restores_the_last_admissible_iterate(
    problem: tuple[ngs.Mesh, ngs.FESpace, float],
) -> None:
    """A state gate aborts on the same contract as an increment gate: the state rolls back.

    A continuation driver catches the violation to retry the rung with a smaller
    ramp; it can only do that if the grid function still holds an admissible
    warm start rather than the iterate that failed the gate.
    """
    mesh, space, screening_nm = problem
    state = _initial_state(space, mesh)
    before = state.vec.CreateVector()
    before.data = state.vec

    class FailsAfterTheFirstStep:
        """Passes on the entry state and rejects every iterate after it."""

        name = "test gate"

        def __init__(self) -> None:
            self.calls = 0

        def check(self) -> None:
            """Reject every state but the first one seen."""
            self.calls += 1
            if self.calls > 1:
                raise GateViolationError(self.name, "c_test", -1.0, (0.5, 0.5), ("x", "y"))

    with pytest.raises(GateViolationError):
        damped_newton(
            _residual_form(space, screening_nm), state, state_gates=[FailsAfterTheFirstStep()]
        )

    assert ngs.Norm(state.vec - before) == pytest.approx(0.0, abs=1e-14)


def test_num17_increment_gates_without_an_increment_are_refused(
    problem: tuple[ngs.Mesh, ngs.FESpace, float],
) -> None:
    """A gate over a grid function the loop never writes would assert nothing."""
    mesh, space, screening_nm = problem
    state = _initial_state(space, mesh)
    orphan = ngs.GridFunction(space)
    sampler = FieldSampler(mesh, coordinates=("x", "y"))

    with pytest.raises(ValueError, match="without an increment"):
        damped_newton(
            _residual_form(space, screening_nm),
            state,
            increment_gates=[PotentialIncrementGate(sampler, orphan)],
        )


def test_num16_iteration_cap_raises_with_the_residual_in_the_message(
    problem: tuple[ngs.Mesh, ngs.FESpace, float],
) -> None:
    """Hitting the cap is a diagnosable failure, not a silent return of a partial solve."""
    mesh, space, screening_nm = problem
    state = _initial_state(space, mesh)
    settings = NewtonSettings(max_iterations=2)

    with pytest.raises(NewtonDivergenceError, match="did not converge in 2 iterations"):
        damped_newton(_residual_form(space, screening_nm), state, settings=settings)


def test_num16_iteration_cap_can_be_inspected_instead_of_raised(
    problem: tuple[ngs.Mesh, ngs.FESpace, float],
) -> None:
    """The continuation ladder needs to see a failed rung, not catch an exception."""
    mesh, space, screening_nm = problem
    state = _initial_state(space, mesh)

    result = damped_newton(
        _residual_form(space, screening_nm),
        state,
        settings=NewtonSettings(max_iterations=2),
        raise_on_failure=False,
    )

    assert not result.converged
    assert result.iterations == 2
    assert result.residual < result.initial_residual


def test_num16_a_warm_start_onto_its_own_solution_is_idempotent(
    problem: tuple[ngs.Mesh, ngs.FESpace, float],
) -> None:
    """Re-solving a converged state converges immediately and does not move it.

    This is the property the continuation ladder depends on (NUM-18): every rung
    warm-starts from the previous one, and a rung whose state already solves it
    must cost one step, not the six orders of residual reduction a criterion
    measured against the entry residual would demand.
    """
    mesh, space, screening_nm = problem
    state = _initial_state(space, mesh)
    form = _residual_form(space, screening_nm)
    damped_newton(form, state)
    converged = state.vec.CreateVector()
    converged.data = state.vec

    again = damped_newton(form, state)

    assert again.converged
    assert again.iterations <= 1
    # Not bit-identical: the first solve stopped at its tolerance, so one more
    # step remains available. It must be smaller than that tolerance allows.
    moved = ngs.Norm(state.vec - converged) / ngs.Norm(converged)
    assert moved < DEFAULT_SETTINGS.relative_tolerance


def test_num16_minimally_damped_step_is_accepted_not_aborted(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """NUM-16's central rule: a step that raises the residual at minimum damping is taken.

    Contrived on purpose, and the classic counterexample to undamped Newton:
    ``arctan(u) = 0`` started at ``u = 10``, where the tangent line crosses the
    axis at ``u = -139`` and the residual rises. Pinning the minimum damping at
    0.5 leaves the loop no admissible step that reduces the residual, so it must
    fall through to acceptance. Aborting here instead is what NUM-16 forbids.
    """
    mesh = SlabGeometry(width_nm=1.0).generate(maxh_nm=1.0)
    space = ngs.H1(mesh, order=1)
    trial, test = space.TnT()
    form = ngs.BilinearForm(space)
    form += ngs.atan(trial) * test * ngs.dx
    state = ngs.GridFunction(space)
    state.Set(ngs.CF(10.0))
    settings = NewtonSettings(
        initial_damping=0.5, minimum_damping=0.5, max_iterations=3, growth_factor=1.0
    )

    with caplog.at_level(logging.WARNING, logger="nanopnp.solve.newton"):
        result = damped_newton(form, state, raise_on_failure=False, settings=settings)

    assert result.forced_steps >= 1
    assert not result.converged
    assert "NUM-16 prefers this to aborting" in caplog.text
    assert result.minimum_damping_used == pytest.approx(0.5)


def test_newton_result_summary_records_the_damping_for_the_manifest(
    problem: tuple[ngs.Mesh, ngs.FESpace, float],
) -> None:
    """The phase report asks which rungs needed damping below 0.1; the record carries it."""
    mesh, space, screening_nm = problem
    state = _initial_state(space, mesh)

    summary = damped_newton(_residual_form(space, screening_nm), state).summary()

    assert summary["converged"] is True
    assert "minimum_damping_used" in summary
    assert "forced_steps" in summary
    assert summary["relative_residual"] <= DEFAULT_SETTINGS.relative_tolerance

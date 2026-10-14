"""Damped Newton: the NUM-16 damping policy and its interaction with the NUM-17 gates."""

from __future__ import annotations

import logging

import ngsolve as ngs
import pytest

from nanopnp.mesh.primitives import SlabGeometry
from nanopnp.numerics.gates import FieldSampler, GateViolationError, PotentialIncrementGate
from nanopnp.numerics.measures import PLANAR
from nanopnp.numerics.newton import (
    DEFAULT_SETTINGS,
    NewtonDivergenceError,
    NewtonSettings,
    damped_newton,
)
from nanopnp.physics.pb import debye_length_nm, nonlinear_pb_residual

CONCENTRATION_M = 0.1

WALL_POTENTIAL = 4.0


class _AlwaysFails:
    name = "test gate"

    def check(self) -> None:
        raise GateViolationError(self.name, "c_test", -1.0, (0.5, 0.5), ("x", "y"))


@pytest.fixture
def problem() -> tuple[ngs.Mesh, ngs.FESpace, float]:
    screening_nm = debye_length_nm(CONCENTRATION_M)
    mesh = SlabGeometry(width_nm=8.0 * screening_nm).generate(maxh_nm=screening_nm / 3.0)
    space = ngs.H1(mesh, order=2, dirichlet="wall")
    return mesh, space, screening_nm


def _residual_form(space: ngs.FESpace, screening_nm: float) -> ngs.BilinearForm:
    trial, test = space.TnT()
    form = ngs.BilinearForm(space)
    form += nonlinear_pb_residual(trial, test, PLANAR, debye_length_nm=screening_nm)
    return form


def _initial_state(space: ngs.FESpace, mesh: ngs.Mesh) -> ngs.GridFunction:
    state = ngs.GridFunction(space)
    state.Set(ngs.CF(WALL_POTENTIAL), definedon=mesh.Boundaries("wall"))
    return state


def test_num16_reference_settings_are_the_defaults() -> None:
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
    with pytest.raises(ValueError, match=field.split("_")[0]):
        NewtonSettings(**{field: value})  # type: ignore[arg-type]


def test_num16_converges_on_nonlinear_poisson_boltzmann(
    problem: tuple[ngs.Mesh, ngs.FESpace, float],
) -> None:
    mesh, space, screening_nm = problem
    state = _initial_state(space, mesh)

    result = damped_newton(_residual_form(space, screening_nm), state)

    assert result.converged
    assert result.relative_residual <= DEFAULT_SETTINGS.relative_tolerance
    assert state(mesh(0.0, 0.5)) == pytest.approx(WALL_POTENTIAL, rel=1e-12)


def test_num16_damping_starts_at_the_initial_factor_and_recovers(
    problem: tuple[ngs.Mesh, ngs.FESpace, float],
) -> None:
    mesh, space, screening_nm = problem
    state = _initial_state(space, mesh)

    result = damped_newton(_residual_form(space, screening_nm), state)

    assert result.history[0].damping == pytest.approx(DEFAULT_SETTINGS.initial_damping)
    assert max(step.damping for step in result.history) == pytest.approx(1.0)
    assert result.history[-1].residual < result.history[0].residual


def test_num16_residual_history_is_monotone_and_ends_quadratic(
    problem: tuple[ngs.Mesh, ngs.FESpace, float],
) -> None:
    mesh, space, screening_nm = problem
    state = _initial_state(space, mesh)

    result = damped_newton(_residual_form(space, screening_nm), state)
    residuals = [step.residual for step in result.history]

    assert residuals == sorted(residuals, reverse=True)
    assert residuals[-1] < residuals[-2] ** 1.8


def test_num17_increment_cap_is_a_step_length_condition_first(
    problem: tuple[ngs.Mesh, ngs.FESpace, float],
) -> None:
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
    mesh, space, screening_nm = problem
    state = _initial_state(space, mesh)

    with pytest.raises(GateViolationError, match="c_test"):
        damped_newton(_residual_form(space, screening_nm), state, state_gates=[_AlwaysFails()])


# NUM-18
def test_num17_state_gates_run_on_the_entry_state() -> None:
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
    mesh, space, screening_nm = problem
    state = _initial_state(space, mesh)
    before = state.vec.CreateVector()
    before.data = state.vec

    class FailsAfterTheFirstStep:
        name = "test gate"

        def __init__(self) -> None:
            self.calls = 0

        def check(self) -> None:
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
    mesh, space, screening_nm = problem
    state = _initial_state(space, mesh)
    settings = NewtonSettings(max_iterations=2)

    with pytest.raises(NewtonDivergenceError, match="did not converge in 2 iterations"):
        damped_newton(_residual_form(space, screening_nm), state, settings=settings)


def test_num16_iteration_cap_can_be_inspected_instead_of_raised(
    problem: tuple[ngs.Mesh, ngs.FESpace, float],
) -> None:
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


# NUM-18
def test_num16_a_warm_start_onto_its_own_solution_is_idempotent(
    problem: tuple[ngs.Mesh, ngs.FESpace, float],
) -> None:
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

    with caplog.at_level(logging.WARNING, logger="nanopnp.numerics.newton"):
        result = damped_newton(form, state, raise_on_failure=False, settings=settings)

    assert result.forced_steps >= 1
    assert not result.converged
    assert "NUM-16 prefers this to aborting" in caplog.text
    assert result.minimum_damping_used == pytest.approx(0.5)


def test_num16_a_nan_trial_residual_at_minimum_damping_is_a_forced_step() -> None:
    mesh = SlabGeometry(width_nm=1.0).generate(maxh_nm=1.0)
    space = ngs.H1(mesh, order=1)
    trial, test = space.TnT()
    form = ngs.BilinearForm(space)
    form += (ngs.sqrt(trial) - 0.1) * test * ngs.dx
    state = ngs.GridFunction(space)
    state.Set(ngs.CF(4.0))
    settings = NewtonSettings(
        initial_damping=1.0, minimum_damping=1.0, max_iterations=1, growth_factor=1.0
    )

    result = damped_newton(form, state, raise_on_failure=False, settings=settings)

    (step,) = result.history
    assert step.residual != step.residual, "the trial residual is NaN"
    assert step.forced
    assert not result.converged


def test_newton_result_summary_records_the_damping_for_the_manifest(
    problem: tuple[ngs.Mesh, ngs.FESpace, float],
) -> None:
    mesh, space, screening_nm = problem
    state = _initial_state(space, mesh)

    summary = damped_newton(_residual_form(space, screening_nm), state).summary()

    assert summary["converged"] is True
    assert "minimum_damping_used" in summary
    assert "forced_steps" in summary
    assert summary["relative_residual"] <= DEFAULT_SETTINGS.relative_tolerance


def test_ver44_every_step_records_the_undamped_relative_update(
    problem: tuple[ngs.Mesh, ngs.FESpace, float],
) -> None:
    mesh, space, screening_nm = problem
    state = _initial_state(space, mesh)
    reference = DEFAULT_SETTINGS.reference_norm

    iterates = [state.vec.CreateVector()]
    iterates[0].data = state.vec

    def remember(step: object) -> None:
        kept = state.vec.CreateVector()
        kept.data = state.vec
        iterates.append(kept)

    result = damped_newton(_residual_form(space, screening_nm), state, callback=remember)

    assert result.history
    damped = 0
    for index, step in enumerate(result.history, start=1):
        before, after = iterates[index - 1], iterates[index]
        taken = after.CreateVector()
        taken.data = after - before
        denominator = max(float(ngs.Norm(before)), reference)
        undamped = float(ngs.Norm(taken)) / step.damping / denominator

        assert step.update == pytest.approx(undamped, rel=1e-12)
        if step.damping < 1.0:
            damped += 1
            assert step.update != pytest.approx(float(ngs.Norm(taken)) / denominator, rel=1e-9), (
                "the recorded update is the damped step, not the Newton direction"
            )
    assert damped, "no step was damped, so the undamped/damped distinction went untested"


def test_ver44_the_newton_summary_gains_no_per_iteration_key(
    problem: tuple[ngs.Mesh, ngs.FESpace, float],
) -> None:
    mesh, space, screening_nm = problem
    state = _initial_state(space, mesh)

    summary = damped_newton(_residual_form(space, screening_nm), state).summary()

    assert set(summary) == {
        "converged",
        "iterations",
        "initial_residual",
        "residual",
        "relative_residual",
        "minimum_damping_used",
        "forced_steps",
    }

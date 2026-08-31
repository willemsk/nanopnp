"""The NUM-18 ladder end to end, and the warm start the whole thing rests on.

Everything here is about ``transfer``. It is the one genuinely new mechanism in
the continuation package and the one place a silent error would live: an
interpolation that landed the potential on the wrong component, or that carried
the NUM-02 log variable across as though it were the concentration, would hand
Newton a plausible initial guess for a different problem, converge, and be wrong.

The property that catches all of that at once is **idempotence**: a converged
rung, transferred onto its own model's space and re-solved, must cost zero Newton
iterations. Nothing about the state has changed, so nothing about the answer may.
A transfer that scrambled a component would need iterations to recover, and one
that lost a field would need many. It is also the property that only works
because of NUM-16's relative-update convergence test: measured on the residual
alone, relative to the residual on entry, re-solving an already-converged state
demands another six orders of magnitude from a residual already at its floor, and
this test would fail on every rung.

The ladder is run on a deliberately small pore at mild conditions. It is a
structural test — every stage completes, the fields survive the two space
changes, the record is complete — not a physics one; §8.2 criterion 2 is where
the hard corner of the envelope is met, in ``test_envelope.py``.
"""

import logging

import ngsolve as ngs
import pytest

from nanopnp.mesh.primitives import CylindricalPoreGeometry
from nanopnp.physics.measures import AXISYMMETRIC
from nanopnp.physics.models import POTENTIAL, PRESSURE, VELOCITY
from nanopnp.solve.continuation import LadderResult, default_ladder, run_ladder, transfer

logger = logging.getLogger(__name__)

PORE = CylindricalPoreGeometry(
    pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=12.0
)
CONCENTRATION_M = 0.5
BIAS_V = 0.03
SURFACE_CHARGE_C_M2 = -0.02
MEMBRANE_PERMITTIVITY = {"membrane": 2.0}


@pytest.fixture(scope="module")
def ladder() -> LadderResult:
    """Run the whole nine-stage ladder once and share the result.

    The salt is swept from the ladder's 0.05 M start to 0.5 M, so stage 9 is
    exercised rather than skipped, and the charge ramp is present so stage 4 is
    too. Two sub-steps apiece: this is a structural test and the ramps only need
    to have more than one rung for the transfer between them to be under test.
    """
    mesh = PORE.generate(maxh_nm=3.0, wall_h_nm=0.5)
    rungs = default_ladder(
        mesh,
        concentration_M=CONCENTRATION_M,
        bias_V=BIAS_V,
        surface_charge_C_m2=SURFACE_CHARGE_C_M2,
        solid_permittivities=MEMBRANE_PERMITTIVITY,
        charge_steps=2,
        concentration_steps=2,
    )
    result = run_ladder(rungs)
    logger.info(
        "ladder: %d rungs, %d iterations, %.1f s, minimum damping %.3f, mesh %s",
        len(result.rungs),
        result.iterations,
        result.seconds,
        result.minimum_damping_used,
        result.mesh,
    )
    for record in result.rungs:
        logger.info(
            "  %-24s stage %d  %5.2f s  %2d it  damping >= %.3f  warm %s  cold %s",
            record.name,
            record.stage,
            record.seconds,
            record.iterations,
            record.minimum_damping_used,
            list(record.transferred_fields),
            list(record.cold_fields),
        )
    return result


def test_num18_every_stage_of_the_ladder_completes(ladder: LadderResult) -> None:
    """All nine stages run, in order, and the top of the ladder is ePNP-NS."""
    stages = [record.stage for record in ladder.rungs]
    assert stages == sorted(stages)
    assert set(stages) == {1, 2, 3, 4, 5, 6, 7, 8, 9}
    top = ladder.solution.model
    assert top.name == "epnp-ns"
    assert top.flow is True
    assert top.steric is True
    assert top.concentration_M == pytest.approx(CONCENTRATION_M)


def test_num18_every_nonlinear_rung_carries_a_convergence_record(
    ladder: LadderResult,
) -> None:
    """A rung with no Newton record has not been solved, whatever it returned."""
    for record in ladder.rungs:
        if record.stage in (1,):
            # Linear Poisson-Boltzmann is a single linear solve and has none.
            assert record.newton is None
            continue
        assert record.newton is not None, record.name
        assert record.newton["converged"] is True, record.summary()


def test_num18_the_two_space_changes_carry_the_fields_they_should(
    ladder: LadderResult,
) -> None:
    """Stage 3 adds the concentrations to ``phi``; stage 6 adds ``u`` and ``p``.

    These are the only two transitions in the default ladder that change the
    field set, and they are exactly what ``CoupledModel.solve`` cannot warm-start
    on its own. The record says which fields came across warm and which started
    cold, so a transfer that silently cold-started everything would show here.
    """
    by_stage = {record.stage: record for record in ladder.rungs}

    third = by_stage[3]
    assert third.transferred_fields == (POTENTIAL,)
    assert set(third.cold_fields) == {"c_Na+", "c_Cl-"}

    sixth = by_stage[6]
    assert POTENTIAL in sixth.transferred_fields
    assert set(sixth.cold_fields) == {VELOCITY, PRESSURE}

    # Everything after stage 6 transfers the whole field set.
    for record in ladder.rungs:
        if record.stage > 6:
            assert record.cold_fields == (), record.summary()


def test_num18_re_solving_a_converged_rung_costs_one_iteration_and_moves_nothing(
    ladder: LadderResult,
) -> None:
    """The warm-start idempotence the whole ladder rests on (NUM-16, NUM-18).

    The converged top of the ladder is transferred onto its *own* model's space
    and re-solved with the same arguments. The state has not changed, so Newton
    must recognise that at once and the re-solved state must be the one it
    started from.

    "At once" is one iteration, not zero, and the one is a real cost worth being
    explicit about. NUM-16's convergence test is on the relative *update*, and an
    update cannot be known without assembling the Jacobian and solving once; the
    entry-side test is on the residual alone, which a converged warm start does
    not pass because it is measured relative to itself. So every rung of the
    ladder pays one Jacobian assembly and one direct solve to establish that it
    has nothing to do. The alternative — a residual-only criterion — does not
    cost zero either: it demands another six orders of magnitude from a residual
    already at its floor, and the ladder never gets past stage 2.

    A transfer that put a field on the wrong component, or that confused ``w_i``
    with ``c~_i`` in the NUM-02 log branch, fails this immediately: the guess is
    then wrong and Newton has to work for it.
    """
    solution = ladder.solution
    model = solution.model
    mesh = solution.space.mesh
    thermal_V = model.scales.potential_V

    carried = transfer(solution, model, mesh)
    difference = carried.state.vec.CreateVector()
    difference.data = carried.state.vec - solution.state.vec
    assert difference.Norm() == pytest.approx(0.0, abs=1e-12 * solution.state.vec.Norm()), (
        "a transfer onto the same field set must be a copy, not an interpolation"
    )

    scale = model.scales
    again = model.solve(
        mesh,
        AXISYMMETRIC,
        initial=carried,
        potential_values=mesh.BoundaryCF({"cis": 0.0, "trans": BIAS_V / thermal_V}),
        surface_charge=ngs.CF(SURFACE_CHARGE_C_M2 / scale.surface_charge_C_m2),
    )
    assert again.newton is not None
    logger.info("re-solving the converged top of the ladder: %s", again.newton.summary())
    assert again.newton.converged is True
    assert again.newton.iterations == 1, (
        "re-solving a converged state must cost exactly the one iteration the "
        "update-based criterion needs to see that there is nothing to do; more than "
        "that means the transfer is lossy, and the ladder is paying for it at every "
        f"rung ({again.newton.summary()})"
    )
    assert again.newton.forced_steps == 0

    # The state may not move by more than the tolerance it converged to: one
    # damped step along a direction of relative size <= rtol.
    drift = again.state.vec.CreateVector()
    drift.data = again.state.vec - solution.state.vec
    relative = drift.Norm() / solution.state.vec.Norm()
    logger.info("the re-solved state moved by %.3e relative", relative)
    assert relative < 1e-6


def test_num18_the_transfer_preserves_the_potential_across_a_space_change(
    ladder: LadderResult,
) -> None:
    """``phi`` interpolated onto a larger space is the same function it was.

    The space change is what makes the transfer necessary and what makes it able
    to go wrong. Checked as a *function*, in L2 over the whole domain, not
    coefficient by coefficient: the P2 basis is hierarchical, so equal functions
    need not have equal coefficient vectors on two different spaces.
    """
    mesh = ladder.solution.space.mesh
    rungs = default_ladder(
        mesh,
        concentration_M=CONCENTRATION_M,
        bias_V=BIAS_V,
        surface_charge_C_m2=SURFACE_CHARGE_C_M2,
        solid_permittivities=MEMBRANE_PERMITTIVITY,
        start_concentration_M=None,
        charge_steps=1,
    )
    electrostatic = next(rung for rung in rungs if rung.stage == 2)
    coupled = next(rung for rung in rungs if rung.stage == 3)

    solved = electrostatic.model.solve(
        mesh, AXISYMMETRIC, boundaries=electrostatic.boundaries, **electrostatic.solve_kwargs
    )
    carried = transfer(solved, coupled.model, mesh, coupled.boundaries)

    departure = ngs.Integrate((carried.potential - solved.potential) ** 2, mesh)
    magnitude = ngs.Integrate(solved.potential**2 + 1.0, mesh)
    assert departure / magnitude == pytest.approx(0.0, abs=1e-20)

    # And the fields the previous model did not solve for start where the model
    # says is admissible, not at zero: c~_i = 0 fails the NUM-17 positivity gate
    # before Newton takes a step.
    for species in coupled.model.species:
        concentration = carried.concentration(species)
        assert ngs.Integrate(
            (concentration - 1.0) ** 2, mesh, definedon=mesh.Materials(coupled.model.fluid)
        ) == pytest.approx(0.0, abs=1e-20)


def test_fr25_the_ladder_record_can_reconstruct_the_run(ladder: LadderResult) -> None:
    """A continuation result is not reconstructible from its final state alone.

    The path is part of how the answer was obtained, so FR-25 needs the rungs,
    their models, the mesh they ran on and the damping they needed — in
    particular which rungs went below 0.1, which is what the end-of-phase report
    asks for.
    """
    summary = ladder.summary()
    assert summary["stages"] == [1, 2, 3, 4, 5, 6, 7, 8, 9]
    assert summary["mesh"]["elements"] > 0
    assert summary["iterations"] == ladder.iterations
    assert 0.0 < summary["minimum_damping_used"] <= 1.0

    hard = [record.name for record in ladder.rungs if record.minimum_damping_used < 0.1]
    logger.info("rungs that needed damping below 0.1: %s", hard or "none")
    for record in summary["rungs"]:
        assert record["model"]
        assert record["seconds"] >= 0.0

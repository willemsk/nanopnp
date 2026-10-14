"""NUM-18 (with NUM-02, NUM-12, NUM-13, NUM-16, FR-25, PHY-22): the ladder and warm starts."""

import logging

import ngsolve as ngs
import pytest

from nanopnp.io.vocabulary import (
    POTENTIAL,
    PRESSURE,
    VELOCITY,
)
from nanopnp.mesh.primitives import CylindricalPoreGeometry
from nanopnp.numerics.measures import AXISYMMETRIC
from nanopnp.physics.distance import wall_distance
from nanopnp.solve.continuation import LadderResult, default_ladder, run_ladder, transfer

logger = logging.getLogger(__name__)

PORE = CylindricalPoreGeometry(
    pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=12.0
)
CONCENTRATION_M = 0.5
BIAS_V = 0.03
SURFACE_CHARGE_C_M2 = -0.02
MEMBRANE_PERMITTIVITY = {"membrane": 2.0}


# NUM-13
@pytest.fixture(scope="module")
def stabilised() -> LadderResult:
    mesh = PORE.generate(maxh_nm=3.0, wall_h_nm=0.5)
    rungs = default_ladder(
        mesh,
        concentration_M=CONCENTRATION_M,
        bias_V=BIAS_V,
        surface_charge_C_m2=SURFACE_CHARGE_C_M2,
        solid_permittivities=MEMBRANE_PERMITTIVITY,
        wall_distance_nm=wall_distance(mesh, "wall", order=AXISYMMETRIC.element_order),
        start_concentration_M=None,
        charge_steps=1,
        stabilisation="reference",
    )
    result = run_ladder(rungs)
    logger.info(
        "reference ladder: %d rungs, %d iterations, %.1f s, max cell Peclet %.3f, mesh %s",
        len(result.rungs),
        result.iterations,
        result.seconds,
        result.max_cell_peclet or float("nan"),
        result.mesh,
    )
    return result


# NUM-18, PHY-22
def test_num13_every_coupled_rung_of_a_reference_ladder_reports_that_mode(
    stabilised: LadderResult,
) -> None:
    by_stage: dict[int, list[str]] = {}
    for record in stabilised.rungs:
        by_stage.setdefault(record.stage, []).append(record.stabilisation)

    assert by_stage[1] == ["none"]
    assert by_stage[2] == ["none"]
    for stage in sorted(by_stage):
        if stage >= 3:
            assert set(by_stage[stage]) == {"reference"}, (
                f"stage {stage} was assembled in {sorted(set(by_stage[stage]))}, not 'reference'"
            )

    # And the top of the ladder agrees with its own rung record, with the tuning
    # constants beside it: 'reference' at C_cw = 1 and at C_cw = 0.35 are different
    # operators and the mode name alone does not separate them (FR-25).
    assert stabilised.stabilisation == "reference"
    assert stabilised.rungs[-1].stabilisation == "reference"
    parameters = dict(stabilised.stabilisation_parameters)
    logger.info("reference parameters: %s", parameters)
    assert parameters["crosswind_coefficient"] == 1.0
    assert parameters["streamline_cutoff"] == 1.0
    assert stabilised.summary()["stabilisation"] == "reference"


def test_num12_the_reference_ladder_measures_the_cell_peclet_it_ran_at(
    stabilised: LadderResult,
) -> None:
    measured = stabilised.peclet
    assert measured is not None, "a ladder whose top rung solves transport must measure Pe_K"
    logger.info(
        "cell Peclet on the converged top rung: max %.4f in %r at (r, z) = (%.3f, %.3f); "
        "%d of %d samples above 1",
        measured.maximum,
        measured.species,
        measured.location[0],
        measured.location[1],
        measured.exceeding,
        measured.samples,
    )
    assert measured.samples > 0
    assert measured.maximum >= 0.0
    assert set(measured.per_species) == set(stabilised.solution.model.species)
    assert stabilised.max_cell_peclet == pytest.approx(measured.maximum)


@pytest.fixture(scope="module")
def ladder() -> LadderResult:
    mesh = PORE.generate(maxh_nm=3.0, wall_h_nm=0.5)
    rungs = default_ladder(
        mesh,
        concentration_M=CONCENTRATION_M,
        bias_V=BIAS_V,
        surface_charge_C_m2=SURFACE_CHARGE_C_M2,
        solid_permittivities=MEMBRANE_PERMITTIVITY,
        # A real PHY-02 distance field, from the pore wall alone: the saturated
        # constant would make every wall factor identically 1 and leave stages 7
        # and 8 exercising only the concentration half of the corrections.
        wall_distance_nm=wall_distance(mesh, "wall", order=AXISYMMETRIC.element_order),
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
    by_stage = {record.stage: record for record in ladder.rungs}

    third = by_stage[3]
    assert third.transferred_fields == (POTENTIAL,)
    assert set(third.cold_fields) == {"c_Na+", "c_Cl-"}

    sixth = by_stage[6]
    assert POTENTIAL in sixth.transferred_fields
    assert set(sixth.cold_fields) == {VELOCITY, PRESSURE}

    for record in ladder.rungs:
        if record.stage > 6:
            assert record.cold_fields == (), record.summary()


# NUM-16
def test_num18_re_solving_a_converged_rung_costs_one_iteration_and_moves_nothing(
    ladder: LadderResult,
) -> None:
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
        # Read off the solution rather than rebuilt. A distance field is a
        # discrete grid function, so a second call to ``wall_distance`` would
        # give a numerically different one and this would no longer be the same
        # operator — which is precisely why ``ModelSolution`` carries it.
        wall_distance_nm=solution.wall_distance_nm,
    )
    assert again.newton is not None
    logger.info("re-solving the converged top of the ladder: %s", again.newton.summary())
    assert again.newton.converged is True
    assert again.newton.iterations in (0, 1), (
        "re-solving a converged state must cost at most one iteration the "
        "update-based criterion needs to see that there is nothing to do; more than "
        "that means the transfer is lossy, and the ladder is paying for it at every "
        f"rung ({again.newton.summary()})"
    )
    assert again.newton.forced_steps == 0

    drift = again.state.vec.CreateVector()
    drift.data = again.state.vec - solution.state.vec
    relative = drift.Norm() / solution.state.vec.Norm()
    logger.info("the re-solved state moved by %.3e relative", relative)
    assert relative < 1e-6


def test_num18_the_transfer_preserves_the_potential_across_a_space_change(
    ladder: LadderResult,
) -> None:
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
    summary = ladder.summary()
    assert summary["stages"] == [1, 2, 3, 4, 5, 6, 7, 8, 9]
    assert summary["mesh"]["elements"] > 0
    assert summary["iterations"] == ladder.iterations
    assert 0.0 < summary["minimum_damping_used"] <= 1.0
    # The stabilisation mode is load-bearing for the Phase-1 COMSOL comparison
    # (§6.4/§7.4): unstabilised this phase, and recorded so the comparison can
    # attribute a discrepancy to the discretisation rather than to a bug (FR-25).
    assert summary["stabilisation"] == "none"

    hard = [record.name for record in ladder.rungs if record.minimum_damping_used < 0.1]
    logger.info("rungs that needed damping below 0.1: %s", hard or "none")
    for record in summary["rungs"]:
        assert record["model"]
        assert record["seconds"] >= 0.0

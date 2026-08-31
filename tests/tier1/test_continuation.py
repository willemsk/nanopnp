"""The NUM-18 ladder's schedules and its structure, without solving anything.

The ladder's *behaviour* — that every rung converges, and that a converged rung
re-solved from its own output costs zero iterations — is Tier 2 and lives in
``tests/tier2/test_ladder.py``. What is checked here is everything that can be
got wrong before a single Newton step is taken: a ramp that overshoots its
target, a stage order that puts the corrections on before the bias, and a
transfer asked to cross a mesh.
"""

from dataclasses import replace
from itertools import pairwise

import pytest

from nanopnp.mesh.primitives import CylindricalPoreGeometry
from nanopnp.physics import models
from nanopnp.physics.measures import AXISYMMETRIC
from nanopnp.solve.continuation import (
    BIAS_ONSET_V,
    COARSE_BIAS_STEP_V,
    FINE_BIAS_STEP_V,
    TransferError,
    bias_schedule,
    default_ladder,
    mesh_report,
    ramp_schedule,
    run_ladder,
    transfer,
)

PORE = CylindricalPoreGeometry(
    pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0
)
MEMBRANE_PERMITTIVITY = {"membrane": 2.0}
"""An insulating membrane. Not a fitted parameter: the ladder's *structure* is
what is under test here and nothing is solved, so any insulating value serves."""


@pytest.fixture(scope="module")
def mesh() -> object:
    """Return a coarse mesh; every test here builds a ladder without running it."""
    return PORE.generate(maxh_nm=3.0)


# -- the bias ramp of stage 5 ------------------------------------------------


def test_num18_bias_ramp_steps_finely_near_onset_and_ends_on_the_target() -> None:
    """Steps of about 10 mV near onset, then coarser, landing exactly on target."""
    schedule = bias_schedule(0.2)
    assert schedule[-1] == pytest.approx(0.2)
    assert schedule[0] == pytest.approx(FINE_BIAS_STEP_V)
    steps = [later - earlier for earlier, later in pairwise((0.0, *schedule))]
    for arrival, step in zip(schedule, steps, strict=True):
        expected = FINE_BIAS_STEP_V if arrival <= BIAS_ONSET_V + 1e-12 else COARSE_BIAS_STEP_V
        assert step == pytest.approx(expected), f"step onto {arrival} V"


def test_num18_bias_ramp_is_monotone_in_magnitude_and_keeps_the_sign() -> None:
    """The envelope runs to +/-200 mV, so both signs must ramp the same way."""
    for target in (0.2, -0.2):
        schedule = bias_schedule(target)
        assert schedule[-1] == pytest.approx(target)
        assert all(value * target > 0.0 for value in schedule)
        magnitudes = [abs(value) for value in schedule]
        assert magnitudes == sorted(magnitudes)


def test_num18_bias_ramp_never_overshoots_a_target_between_two_steps() -> None:
    """A target that is not a whole number of steps still ends exactly on itself."""
    schedule = bias_schedule(0.037)
    assert schedule[-1] == pytest.approx(0.037)
    assert max(abs(value) for value in schedule) == pytest.approx(0.037)


def test_num18_a_zero_bias_needs_no_ramp() -> None:
    """Stage 5 is empty at zero target rather than a single no-op rung."""
    assert bias_schedule(0.0) == ()


def test_num18_a_non_positive_bias_step_is_refused() -> None:
    """A zero step would not terminate, and a negative one would run backwards."""
    with pytest.raises(ValueError, match="must be positive"):
        bias_schedule(0.2, fine_step_V=0.0)


def test_num18_ramp_schedule_ends_at_one() -> None:
    """Stage 4 raises the charges to their full target, not to a fraction of it."""
    assert ramp_schedule(4) == pytest.approx((0.25, 0.5, 0.75, 1.0))
    assert ramp_schedule(1) == (1.0,)
    with pytest.raises(ValueError, match="at least one step"):
        ramp_schedule(0)


# -- the structure of the default ladder -------------------------------------


def test_num18_default_ladder_runs_the_nine_stages_in_order(mesh: object) -> None:
    """Every stage appears, and no rung of a later stage precedes an earlier one.

    The order is the requirement, not the count: stages 4, 5 and 9 are ramps and
    expand into several rungs apiece. Enabling the corrections last is what
    isolates their contribution to a convergence failure, so a ladder that put
    stage 7 before stage 5 would still converge and would no longer be doing
    what NUM-18 asks.
    """
    rungs = default_ladder(
        mesh,
        concentration_M=1.0,
        bias_V=0.1,
        surface_charge_C_m2=-0.02,
        solid_permittivities=MEMBRANE_PERMITTIVITY,
    )
    stages = [rung.stage for rung in rungs]
    assert stages == sorted(stages)
    assert set(stages) == {1, 2, 3, 4, 5, 6, 7, 8, 9}


def test_num18_the_corrections_come_on_last_and_one_block_at_a_time(mesh: object) -> None:
    """Stage 6 is classical with flow, 7 adds the corrections, 8 adds the steric term."""
    rungs = default_ladder(mesh, bias_V=0.05, solid_permittivities=MEMBRANE_PERMITTIVITY)
    by_stage = {rung.stage: rung for rung in rungs if rung.stage in (3, 6, 7, 8)}

    assert by_stage[3].model.flow is False
    assert by_stage[6].model.flow is True
    assert by_stage[6].model.provenance["switches"]["steric"] is False
    # ``classical`` is the registered ``none`` correction, not a code branch
    # (PHY-21): every stage is the same class with different switches.
    assert by_stage[6].model.electrolyte.switches.diffusivity.model == "none"

    assert by_stage[7].model.electrolyte.switches.diffusivity.model != "none"
    assert by_stage[7].model.steric is False

    assert by_stage[8].model.steric is True
    assert by_stage[8].model.electrolyte.switches.mobility.model != "none"
    assert type(by_stage[6].model) is type(by_stage[8].model)


def test_num18_stage_nine_sweeps_the_salt_to_the_target(mesh: object) -> None:
    """The ladder is built at the easy end and swept to the requested concentration."""
    rungs = default_ladder(
        mesh, concentration_M=3.0, bias_V=0.05, solid_permittivities=MEMBRANE_PERMITTIVITY
    )
    sweep = [rung for rung in rungs if rung.stage == 9]
    assert sweep, "a target away from the ladder's starting salt needs stage 9"
    concentrations = [rung.model.concentration_M for rung in sweep]
    assert concentrations == sorted(concentrations)
    assert concentrations[-1] == pytest.approx(3.0)
    built_at = next(rung for rung in rungs if rung.stage == 8).model.concentration_M
    assert built_at == pytest.approx(0.05)


def test_num18_no_sweep_is_built_when_the_ladder_starts_at_the_target(mesh: object) -> None:
    """Stage 9 is omitted rather than emitted as a rung that changes nothing."""
    rungs = default_ladder(
        mesh,
        concentration_M=1.0,
        bias_V=0.05,
        start_concentration_M=None,
        solid_permittivities=MEMBRANE_PERMITTIVITY,
    )
    assert not [rung for rung in rungs if rung.stage == 9]
    assert all(rung.model.concentration_M == 1.0 for rung in rungs if rung.stage >= 3)


def test_num18_stage_four_is_omitted_when_there_is_no_charge_to_ramp(mesh: object) -> None:
    """An uncharged pore has nothing to raise from zero, so it gets no rungs for it."""
    rungs = default_ladder(mesh, bias_V=0.05, solid_permittivities=MEMBRANE_PERMITTIVITY)
    assert not [rung for rung in rungs if rung.stage == 4]


def test_num18_the_charge_ramp_reaches_the_target_and_is_held_afterwards(
    mesh: object,
) -> None:
    """Stage 4 raises ``sigma_s`` to its target, and every later rung carries it.

    A ramp that reached the target and then dropped it would leave the top of the
    ladder solving an uncharged pore, converging beautifully, and answering a
    different question.
    """
    import ngsolve as ngs

    target = -0.05
    rungs = default_ladder(
        mesh,
        bias_V=0.05,
        surface_charge_C_m2=target,
        solid_permittivities=MEMBRANE_PERMITTIVITY,
    )
    scale = next(r for r in rungs if r.stage == 3).model.scales.surface_charge_C_m2
    ramp = [rung for rung in rungs if rung.stage == 4]
    assert len(ramp) == 4
    values = [float(ngs.Integrate(r.solve_kwargs["surface_charge"], mesh)) for r in ramp]
    assert values[-1] == pytest.approx(values[0] * 4.0)
    for rung in [r for r in rungs if r.stage >= 5]:
        assert "surface_charge" in rung.solve_kwargs
        assert rung.solve_kwargs["surface_charge_boundary"] == "wall"
    held = next(r for r in rungs if r.stage == 8).solve_kwargs["surface_charge"]
    area = float(ngs.Integrate(ngs.CF(1.0), mesh))
    assert float(ngs.Integrate(held, mesh)) / area == pytest.approx(target / scale, rel=1e-9)


def test_num19_every_rung_carries_its_own_mesh(mesh: object) -> None:
    """The mesh is a rung's property, so adaptation *between* rungs needs no new API.

    This phase runs one fixed mesh throughout, which satisfies NUM-19 trivially:
    there is nothing to confine to a rung boundary because nothing adapts.
    """
    rungs = default_ladder(mesh, bias_V=0.05, solid_permittivities=MEMBRANE_PERMITTIVITY)
    assert all(rung.mesh is mesh for rung in rungs)


def test_fr25_the_mesh_report_names_what_the_run_was_solved_on(mesh: object) -> None:
    """A continuation result without its mesh cannot be reconstructed (FR-25)."""
    report = mesh_report(mesh)
    assert report["elements"] > 0
    assert "electrolyte" in report["materials"]
    assert {"axis", "cis", "trans", "wall"} <= set(report["boundaries"])


# -- transfer ----------------------------------------------------------------


def test_num18_transfer_refuses_to_cross_a_mesh(mesh: object) -> None:
    """Interpolating onto another mesh evaluates outside the source domain silently."""
    model = models.create("pnp", classical=True)
    other = PORE.generate(maxh_nm=4.0)
    previous = models.ModelSolution(
        model=model, space=model.space(mesh), state=model.cold_state(mesh)
    )
    with pytest.raises(TransferError, match="stay on one mesh"):
        transfer(previous, model, other)


def test_num18_transfer_refuses_two_models_with_nothing_in_common(mesh: object) -> None:
    """There is no warm start between disjoint field sets, and pretending there is is worse."""
    source = models.create("pnp", classical=True)
    target = replace(source, order=3)
    previous = models.ModelSolution(
        model=source, space=source.space(mesh), state=source.cold_state(mesh)
    )
    with pytest.raises(TransferError, match="share no field"):
        transfer(previous, target, mesh)


def test_an_empty_ladder_is_refused() -> None:
    """Running nothing and returning a result would be the wrong kind of success."""
    with pytest.raises(ValueError, match="at least one rung"):
        run_ladder([])


def test_the_ladder_measures_match_the_model_order(mesh: object) -> None:
    """NUM-07's quadrature bonus is computed from the element order; a mismatch raises."""
    rungs = default_ladder(
        mesh, bias_V=0.05, measures=AXISYMMETRIC, solid_permittivities=MEMBRANE_PERMITTIVITY
    )
    for rung in rungs:
        assert rung.measures.element_order == AXISYMMETRIC.element_order
        assert all(field.order <= rung.measures.element_order for field in rung.model.fields)

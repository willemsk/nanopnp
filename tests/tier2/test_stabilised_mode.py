"""VER-42: the reference-matching stabilised mode, measured rather than assumed."""

from __future__ import annotations

import functools
import itertools
import logging
import math
from dataclasses import replace
from typing import TYPE_CHECKING

import pytest

from nanopnp.io.vocabulary import (
    POTENTIAL,
    VELOCITY,
)
from nanopnp.materials.electrolyte import CorrectionSwitches, Electrolyte
from nanopnp.mesh.primitives import CylinderGeometry, CylindricalPoreGeometry
from nanopnp.numerics.gates import GateViolationError
from nanopnp.numerics.measures import AXISYMMETRIC, Measures
from nanopnp.physics import stabilisation as stabilisation_module
from nanopnp.physics.models import (
    CoupledBoundaries,
    CoupledModel,
    ModelSolution,
    concentration_field_name,
)
from nanopnp.post import qoi
from nanopnp.solve.continuation import LadderResult, default_ladder, run_ladder
from nanopnp.validation.mms import (
    ManufacturedSolution,
    convergence_rates,
    weighted_l2_error,
)

if TYPE_CHECKING:
    from ngsolve import Mesh

logger = logging.getLogger(__name__)


# -- 1 and 2: the manufactured solution ----------------------------------------


MMS_MEASURES = Measures(symmetry="axisymmetric", element_order=2)
MMS_RADIUS_NM, MMS_LENGTH_NM = 2.0, 4.0
# Refinement sequence: SPECIFICATION.md VER-18.
MMS_SIZES_NM = (0.4, 0.2, 0.1)

MMS_FLOW_SIZES_NM = (0.4, 0.2)

# NUM-06
MMS_BOUNDARIES = CoupledBoundaries(
    potential="wall|end",
    concentration="wall|end",
    velocity="wall|end",
    velocity_axis="axis",
)

# 2 - 0.2: the margin tests/tier2/test_mms.py already allows on its 3.
STABILISED_RATE_FLOOR = 1.8

MMS_GATED_MODE = "supg"


# VER-18
def _mms_model(mode: str) -> CoupledModel:
    electrolyte = Electrolyte.from_parameter_file(
        switches=replace(CorrectionSwitches.classical(), steric=True)
    )
    return CoupledModel(
        electrolyte=electrolyte,
        concentration_M=0.1,
        name="mms",
        fluid="electrolyte",
        pressure_constraint=True,
        stabilisation=mode,
    )


# NUM-14
def _mms_errors(
    mode: str,
    *,
    withhold_source: bool = False,
    sizes: tuple[float, ...] = MMS_SIZES_NM,
) -> dict[str, list[float]]:
    model = _mms_model(mode)
    manufactured = ManufacturedSolution.polynomial(model)
    exact = manufactured.coefficient_functions()
    sources = manufactured.source_functions(MMS_MEASURES)

    intact = stabilisation_module.approximate_residual

    def without_source(state: object, *, source: object = None) -> object:
        del source
        return intact(state, source=None)  # type: ignore[arg-type]

    if withhold_source:
        stabilisation_module.approximate_residual = without_source  # type: ignore[assignment]
    try:
        errors: dict[str, list[float]] = {name: [] for name in exact}
        for maxh_nm in sizes:
            mesh = CylinderGeometry(radius_nm=MMS_RADIUS_NM, length_nm=MMS_LENGTH_NM).generate(
                maxh_nm=maxh_nm
            )
            solution = model.solve(
                mesh,
                MMS_MEASURES,
                boundaries=MMS_BOUNDARIES,
                potential_values=exact[POTENTIAL],
                concentration_values={
                    species: exact[concentration_field_name(species)] for species in model.species
                },
                velocity_values=exact[VELOCITY],
                sources=sources,
            )
            for name, reference in exact.items():
                errors[name].append(
                    weighted_l2_error(
                        solution.component(name), reference, mesh, MMS_MEASURES, what=name
                    )
                )
    finally:
        stabilisation_module.approximate_residual = intact  # type: ignore[assignment]
    return errors


def _report_rates(
    label: str,
    errors: dict[str, list[float]],
    sizes: tuple[float, ...] = MMS_SIZES_NM,
) -> dict[str, list[float]]:
    rates: dict[str, list[float]] = {}
    for name, values in errors.items():
        rates[name] = convergence_rates(values, sizes)
        logger.info(
            "%s: %s errors %s, rates %s (maxh %s nm)",
            label,
            name,
            " ".join(f"{value:.4e}" for value in values),
            " ".join(f"{rate:.3f}" for rate in rates[name]),
            ", ".join(str(size) for size in sizes),
        )
    return rates


def _transport_fields(model: CoupledModel) -> list[str]:
    return [concentration_field_name(species) for species in model.species]


# VER-18
@pytest.fixture(scope="module")
def streamline_errors() -> dict[str, list[float]]:
    return _mms_errors(MMS_GATED_MODE)


# VER-18
@pytest.fixture(scope="module")
def streamline_rates(streamline_errors: dict[str, list[float]]) -> dict[str, list[float]]:
    return _report_rates(MMS_GATED_MODE, streamline_errors)


@pytest.fixture(scope="module")
def unstabilised_errors() -> dict[str, list[float]]:
    return _mms_errors("none")


@pytest.fixture(scope="module")
def unstabilised_rates(unstabilised_errors: dict[str, list[float]]) -> dict[str, list[float]]:
    return _report_rates("none", unstabilised_errors)


# NUM-14
def test_ver42_the_stabilised_mode_loses_an_order_and_no_more(
    streamline_rates: dict[str, list[float]],
) -> None:
    for name in _transport_fields(_mms_model(MMS_GATED_MODE)):
        rates = streamline_rates[name]
        assert min(rates) > STABILISED_RATE_FLOOR, (
            f"{name}: observed rates {rates} fall below the {STABILISED_RATE_FLOOR} floor, "
            "which is one order short of VER-18's own rate; a rate this low usually means "
            "the manufactured source never reached R~_i"
        )


# PHY-22
def test_ver42_the_unstabilised_mode_on_the_same_meshes_still_gives_ver18s_rate(
    unstabilised_rates: dict[str, list[float]],
) -> None:
    for name in _transport_fields(_mms_model("none")):
        rates = unstabilised_rates[name]
        assert min(rates) > 2.8, f"{name}: observed rates {rates} fall short of P2"


# Measured footprint ratios of 24 to 213 with the source withheld.
WITHHELD_FOOTPRINT_FACTOR = 5.0


# NUM-14
def test_ver42_withholding_the_manufactured_source_switches_the_term_off(
    streamline_errors: dict[str, list[float]],
    unstabilised_errors: dict[str, list[float]],
) -> None:
    damaged = _mms_errors(MMS_GATED_MODE, withhold_source=True, sizes=MMS_FLOW_SIZES_NM)
    _report_rates(f"{MMS_GATED_MODE}, source withheld", damaged, MMS_FLOW_SIZES_NM)

    for name in _transport_fields(_mms_model(MMS_GATED_MODE)):
        for level, maxh_nm in enumerate(MMS_FLOW_SIZES_NM):
            plain = unstabilised_errors[name][level]
            intact = streamline_errors[name][level] / plain - 1.0
            broken = damaged[name][level] / plain - 1.0
            logger.info(
                "%s at maxh %s nm: footprint intact %.3f, source withheld %.3f (%.1fx)",
                name,
                maxh_nm,
                intact,
                broken,
                intact / broken if broken > 0.0 else float("inf"),
            )
            assert intact > WITHHELD_FOOTPRINT_FACTOR * broken, (
                f"{name} at maxh {maxh_nm} nm: the stabilisation's footprint on the error "
                f"is {intact:.3f} intact and {broken:.3f} with the manufactured source "
                "withheld, which is not the collapse that mistake produces; either the "
                "source never reached R~_i in the first place, or the patch in this test "
                "no longer covers the seam it reads it through"
            )


# Measured velocity-error factor of 125 with the flow pair on.
FLOW_PAIR_VELOCITY_FACTOR = 10.0


# NUM-14, NUM-03
@pytest.mark.slow
def test_ver42_the_flow_pair_and_not_the_transport_term_sets_the_reference_rate(
    streamline_errors: dict[str, list[float]],
    unstabilised_errors: dict[str, list[float]],
) -> None:
    errors = _mms_errors("reference", sizes=MMS_FLOW_SIZES_NM)
    rates = _report_rates("reference", errors, MMS_FLOW_SIZES_NM)

    model = _mms_model("reference")
    coarsest = MMS_FLOW_SIZES_NM[0]
    mesh = CylinderGeometry(radius_nm=MMS_RADIUS_NM, length_nm=MMS_LENGTH_NM).generate(
        maxh_nm=coarsest
    )
    manufactured = ManufacturedSolution.polynomial(model)
    exact = manufactured.coefficient_functions()
    solution = model.solve(
        mesh,
        MMS_MEASURES,
        boundaries=MMS_BOUNDARIES,
        potential_values=exact[POTENTIAL],
        concentration_values={
            species: exact[concentration_field_name(species)] for species in model.species
        },
        velocity_values=exact[VELOCITY],
        sources=manufactured.source_functions(MMS_MEASURES),
    )
    samples = _crosswind_samples(solution)
    for species, (active, exceeding, total, largest) in samples.items():
        logger.info(
            "reference on the MMS mesh at maxh %s nm, %s: %d of %d samples above unit "
            "Pe_K, crosswind active at %d, peak nu_K %.3e",
            coarsest,
            species,
            exceeding,
            total,
            active,
            largest,
        )
        assert active == 0, (
            f"{species}: the crosswind is active at {active} of {total} samples on the "
            "manufactured problem, so the reference-minus-supg difference is not the "
            "flow pair's alone and this test's attribution no longer holds"
        )

    streamline = _report_rates(
        "supg, the same two levels",
        {name: values[:2] for name, values in streamline_errors.items()},
        MMS_FLOW_SIZES_NM,
    )
    for name in _transport_fields(model):
        logger.info(
            "%s: reference rate %.3f against supg %.3f on maxh %s nm",
            name,
            rates[name][0],
            streamline[name][0],
            ", ".join(str(size) for size in MMS_FLOW_SIZES_NM),
        )

    stabilised = streamline_errors[VELOCITY][0]
    plain = unstabilised_errors[VELOCITY][0]
    flowed = errors[VELOCITY][0]
    logger.info(
        "velocity L2 at maxh %s nm: none %.4e, supg %.4e, reference %.4e",
        coarsest,
        plain,
        stabilised,
        flowed,
    )
    assert abs(stabilised - plain) < 0.05 * plain, (
        f"the transport stabilisation moved the velocity error from {plain:.4e} to "
        f"{stabilised:.4e}; it touches only the transport rows, so this contradicts the "
        "attribution the reference measurement rests on"
    )
    assert flowed > FLOW_PAIR_VELOCITY_FACTOR * plain, (
        f"the reference mode's velocity error is {flowed:.4e} against {plain:.4e} "
        f"unstabilised, less than the factor {FLOW_PAIR_VELOCITY_FACTOR} this "
        "attribution expects; if the flow pair has become inert on a Taylor-Hood pair "
        "the plan's original prediction was right after all and this test should say so"
    )


# -- 3: the coarse mesh, where the mode earns its place -------------------------


COARSE_PORE = CylindricalPoreGeometry(
    pore_radius_nm=2.0, membrane_thickness_nm=13.0, reservoir_radius_nm=25.0
)

# Coarse wall spacing against SPECIFICATION.md NUM-30, at 0.5 M.
COARSE_WALL_H_NM = 1.0

RESOLVED_WALL_H_NM = 0.2

COARSE_CONCENTRATION_M = 0.5
COARSE_BIAS_V = 0.05
COARSE_CHARGE_C_M2 = -0.12

MEMBRANE_PERMITTIVITY = {"membrane": 2.0}


@functools.cache
def _pore_mesh(wall_h_nm: float) -> Mesh:
    return COARSE_PORE.generate(maxh_nm=5.0, wall_h_nm=wall_h_nm)


# NUM-18
def _climb(wall_h_nm: float, mode: str, *, charge_C_m2: float = COARSE_CHARGE_C_M2) -> LadderResult:
    mesh = _pore_mesh(wall_h_nm)
    rungs = default_ladder(
        mesh,
        concentration_M=COARSE_CONCENTRATION_M,
        bias_V=COARSE_BIAS_V,
        surface_charge_C_m2=charge_C_m2,
        solid_permittivities=MEMBRANE_PERMITTIVITY,
        start_concentration_M=None,
        charge_steps=2,
        stabilisation=mode,
    )
    return run_ladder([rung for rung in rungs if rung.stage <= 5])


@pytest.fixture(scope="module")
def coarse_reference() -> LadderResult:
    result = _climb(COARSE_WALL_H_NM, "reference")
    logger.info(
        "reference on wall_h %.1f nm (mesh %s): %d iterations, %.1f s, max cell Peclet %.4f",
        COARSE_WALL_H_NM,
        result.mesh,
        result.iterations,
        result.seconds,
        result.max_cell_peclet or float("nan"),
    )
    return result


# NUM-12, VER-42, QR-12
def test_num17_plain_galerkin_trips_positivity_where_reference_converges(
    coarse_reference: LadderResult,
) -> None:
    assert coarse_reference.peclet is not None
    assert coarse_reference.max_cell_peclet is not None
    assert coarse_reference.max_cell_peclet > 1.0, (
        "this benchmark needs an under-resolved double layer to be about anything; "
        f"max Pe_K measured {coarse_reference.max_cell_peclet:.4f}"
    )

    with pytest.raises(GateViolationError) as raised:
        _climb(COARSE_WALL_H_NM, "none")
    message = str(raised.value)
    logger.info("none on the same mesh: %s", message.splitlines()[0])
    assert "concentration positivity" in message
    assert "r = " in message and "z = " in message


# NUM-17, NUM-12
def _crosswind_samples(solution: ModelSolution) -> dict[str, tuple[int, int, int, float]]:
    from nanopnp.numerics.gates import FieldSampler

    model = solution.model
    functions = {field.name: solution.component(field.name) for field in model.fields}
    states = model.transport_states(functions, solution.wall_distance_nm)
    sampler = FieldSampler(mesh=solution.space.mesh, materials=model.fluid)

    found: dict[str, tuple[int, int, int, float]] = {}
    for species, state in states.items():
        viscosity = sampler.evaluate(stabilisation_module.crosswind_viscosity(state))
        peclet = sampler.evaluate(stabilisation_module.cell_peclet(state))
        active = viscosity > 0.0
        exceeding = peclet >= 1.0
        # Cauchy-Schwarz bounds nu_K by D max(0, C_cw Pe_K - 1), so an active sample at or below
        # unit Peclet contradicts the bound.
        stray = int((active & ~exceeding).sum())
        assert stray == 0, (
            f"{species}: {stray} samples carry a positive crosswind viscosity at "
            "Pe_K <= 1, which the Cauchy-Schwarz bound nu_K <= D~_i (C_cw Pe_K - 1) "
            "forbids; either C_cw moved or the residual is not b~_i . grad(c~_i)"
        )
        found[species] = (
            int(active.sum()),
            int(exceeding.sum()),
            int(viscosity.size),
            float(viscosity.max()),
        )
    return found


# NUM-14, VER-42
def test_num12_the_crosswind_is_active_where_the_cell_peclet_exceeds_one(
    coarse_reference: LadderResult,
) -> None:
    samples = _crosswind_samples(coarse_reference.solution)
    for species, (active, exceeding, total, largest) in samples.items():
        logger.info(
            "reference on wall_h %.1f nm: %s crosswind active at %d of %d fluid samples "
            "(%.1f %%), %d at Pe_K >= 1, max nu_K %.4e",
            COARSE_WALL_H_NM,
            species,
            active,
            total,
            100.0 * active / total,
            exceeding,
            largest,
        )
        assert active > 0, (
            f"{species}: the crosswind term is inactive everywhere on a mesh whose "
            "cell Peclet number reaches 4.7, so this benchmark is not exercising it"
        )
        assert largest > 0.0


# NUM-14
@pytest.fixture(scope="module")
def resolved_reference() -> LadderResult:
    return _climb(RESOLVED_WALL_H_NM, "reference", charge_C_m2=-0.05)


# NUM-30, VER-42
def test_num14_the_crosswind_contributes_exactly_zero_on_a_resolved_mesh(
    resolved_reference: LadderResult,
) -> None:
    import ngsolve as ngs
    import numpy as np

    result = resolved_reference
    logger.info(
        "reference on wall_h %.1f nm (mesh %s): max cell Peclet %.4f",
        RESOLVED_WALL_H_NM,
        result.mesh,
        result.max_cell_peclet or float("nan"),
    )
    assert result.max_cell_peclet is not None
    assert result.max_cell_peclet < 1.0, (
        "this half of the claim needs a resolved mesh; max Pe_K measured "
        f"{result.max_cell_peclet:.4f}"
    )

    solution = result.solution
    model = solution.model
    mesh = solution.space.mesh
    functions = {field.name: solution.component(field.name) for field in model.fields}
    states = model.transport_states(functions, solution.wall_distance_nm)
    mode = model.stabilisation_model

    # Any test function serves: where nu_K vanishes the integrand vanishes whatever it multiplies,
    # which is the statement under test.
    space = ngs.H1(mesh, order=MMS_MEASURES.element_order, definedon=mesh.Materials(model.fluid))
    for species, state in states.items():
        contributions = mode.transport_contributions(
            trial=state, lagged=state, test=space.TestFunction()
        )
        assert len(contributions) == 2, (
            f"the {mode.name!r} mode produced {len(contributions)} transport contributions; "
            "this test reads the second as the crosswind"
        )
        form = ngs.LinearForm(space)
        form += AXISYMMETRIC.volume(
            contributions[1].integrand,
            definedon=mesh.Materials(model.fluid),
            extra_order=contributions[1].extra_order,
            singular=contributions[1].singular,
        )
        form.Assemble()
        entries = np.asarray(form.vec.FV())
        largest = float(np.abs(entries).max())
        logger.info(
            "%s: assembled crosswind term on the resolved mesh, max |entry| = %.3e",
            species,
            largest,
        )
        assert largest == 0.0, (
            f"{species}: the crosswind term assembles {largest:.3e} on a mesh whose cell "
            f"Peclet number peaks at {result.max_cell_peclet:.4f}; the Cauchy-Schwarz bound "
            "makes it identically zero below 1, so a non-zero entry means the parameter or "
            "the bound is wrong, not that the mesh is marginal"
        )


# -- 4: the two modes' currents converge to each other --------------------------


CURRENT_WALL_H_NM = (0.8, 0.4, 0.2)

# Measured |I_reference - I_none| / |I_none| at 0.5 M, +50 mV, -0.05 C/m^2.
CURRENT_DIFFERENCES = (2.00e-1, 7.38e-2, 1.99e-2)


# NUM-11
def test_ver42_the_two_modes_currents_converge_to_each_other_under_refinement(
    resolved_reference: LadderResult,
) -> None:
    differences: list[float] = []
    for wall_h_nm in CURRENT_WALL_H_NM:
        currents: dict[str, float] = {}
        for mode in ("none", "reference"):
            result = (
                resolved_reference
                if (wall_h_nm, mode) == (RESOLVED_WALL_H_NM, "reference")
                else _climb(wall_h_nm, mode, charge_C_m2=-0.05)
            )
            currents[mode] = qoi.total_current(qoi.reaction_flux_currents(result.solution, "cis"))
        difference = abs(currents["reference"] - currents["none"]) / abs(currents["none"])
        differences.append(difference)
        logger.info(
            "wall_h %.1f nm: I(none) %.6e A, I(reference) %.6e A, difference %.4e",
            wall_h_nm,
            currents["none"],
            currents["reference"],
            difference,
        )

    rates = [
        math.log(differences[index] / differences[index + 1])
        / math.log(CURRENT_WALL_H_NM[index] / CURRENT_WALL_H_NM[index + 1])
        for index in range(len(differences) - 1)
    ]
    logger.info(
        "mode-to-mode current difference %s, rates %s over wall_h %s nm",
        " ".join(f"{value:.4e}" for value in differences),
        " ".join(f"{rate:.3f}" for rate in rates),
        ", ".join(str(size) for size in CURRENT_WALL_H_NM),
    )

    for coarser, finer in itertools.pairwise(differences):
        assert finer < coarser, (
            f"the two modes' currents moved apart under refinement ({coarser:.4e} to "
            f"{finer:.4e}); a stabilisation bias that does not vanish with h is a change "
            "of model, not a discretisation error"
        )
    assert rates[-1] > 1.5, (
        f"the finest interval converges at {rates[-1]:.3f}, short of the O(h^2) the "
        f"streamline term's Pe_K^2 scaling predicts; measured rates {rates}"
    )


# -- the equal-order pair: recorded, not gated ----------------------------------


def _climb_equal_order(mode: str) -> LadderResult:
    mesh = _pore_mesh(0.4)
    rungs = default_ladder(
        mesh,
        concentration_M=COARSE_CONCENTRATION_M,
        bias_V=COARSE_BIAS_V,
        surface_charge_C_m2=-0.05,
        solid_permittivities=MEMBRANE_PERMITTIVITY,
        start_concentration_M=None,
        charge_steps=2,
        stabilisation=mode,
        velocity_order=1,
        pressure_order=1,
    )
    return run_ladder([rung for rung in rungs if rung.stage <= 6])


# VER-41
def test_num03_the_equal_order_pair_is_refused_in_every_mode_without_flow_stabilisation() -> None:
    for mode in ("none", "supg"):
        with pytest.raises(ValueError, match="inf-sup") as raised:
            _climb_equal_order(mode)
        message = str(raised.value)
        assert "reference" in message, message


# NUM-03, NUM-18
@pytest.mark.slow
def test_ver42_the_equal_order_pair_is_recorded_and_not_gated() -> None:
    import ngsolve as ngs

    equal = _climb_equal_order("reference")
    mesh = _pore_mesh(0.4)
    taylor_hood = run_ladder(
        [
            rung
            for rung in default_ladder(
                mesh,
                concentration_M=COARSE_CONCENTRATION_M,
                bias_V=COARSE_BIAS_V,
                surface_charge_C_m2=-0.05,
                solid_permittivities=MEMBRANE_PERMITTIVITY,
                start_concentration_M=None,
                charge_steps=2,
                stabilisation="reference",
            )
            if rung.stage <= 6
        ]
    )

    difference = weighted_l2_error(
        equal.solution.velocity,
        taylor_hood.solution.velocity,
        equal.solution.space.mesh,
        AXISYMMETRIC,
        what="equal-order velocity",
        definedon=equal.solution.space.mesh.Materials(equal.solution.model.fluid),
    )
    logger.info(
        "equal order P1/P1 in reference: %d iterations, %.1f s, velocity %.4e relative L2 "
        "from Taylor-Hood (%d iterations, %.1f s) on wall_h 0.4 nm, mesh %s",
        equal.iterations,
        equal.seconds,
        difference,
        taylor_hood.iterations,
        taylor_hood.seconds,
        equal.mesh,
    )
    assert math.isfinite(difference)
    assert isinstance(equal.solution.velocity, ngs.CoefficientFunction)

"""VER-11 (with FR-17, NUM-23 to NUM-26, QR-04, RSK-03, VER-17): the routes agree."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import ngsolve as ngs
import pytest

from nanopnp.mesh.primitives import CylindricalPoreGeometry
from nanopnp.numerics.measures import AXISYMMETRIC
from nanopnp.physics import models
from nanopnp.post import qoi
from nanopnp.post.indicator import axial_indicator, lumen_band
from nanopnp.solve.continuation import default_ladder, run_ladder

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.pipeline.run import RunResult

logger = logging.getLogger(__name__)

# VER-17
PORE = CylindricalPoreGeometry(
    pore_radius_nm=2.0, membrane_thickness_nm=13.0, reservoir_radius_nm=25.0
)
CONCENTRATION_M = 0.5
# FR-17
BIAS_V = 0.05

SURFACE_CHARGE_C_M2 = -0.05

MEMBRANE_PERMITTIVITY = {"membrane": 2.0}


# NUM-18
@pytest.fixture(scope="module")
def solutions() -> dict[float, models.ModelSolution]:
    mesh = PORE.generate(maxh_nm=5.0, wall_h_nm=0.4)
    converged: dict[float, models.ModelSolution] = {}
    for bias in (BIAS_V, -BIAS_V):
        ladder = default_ladder(
            mesh,
            concentration_M=CONCENTRATION_M,
            bias_V=bias,
            surface_charge_C_m2=SURFACE_CHARGE_C_M2,
            solid_permittivities=MEMBRANE_PERMITTIVITY,
            start_concentration_M=None,
            charge_steps=2,
        )
        # Stages 6 to 8 add the flow and the corrections, which this benchmark
        # does not need: the claim is about extraction, not about physics.
        classical = [rung for rung in ladder if rung.stage <= 5]
        result = run_ladder(classical)
        logger.info(
            "bias %+0.0f mV: %d rungs, %d iterations, %.1f s",
            bias * 1e3,
            len(result.rungs),
            result.iterations,
            result.seconds,
        )
        converged[bias] = result.solution
    return converged


def _indicator(
    solution: models.ModelSolution, *, fraction: float = 0.8, shift_nm: float = 0.0
) -> ngs.GridFunction:
    lower, upper = lumen_band(PORE, fraction=fraction)
    return axial_indicator(
        solution.space.mesh,
        lower_nm=lower + shift_nm,
        upper_nm=upper + shift_nm,
        order=AXISYMMETRIC.element_order,
    )


# NUM-24, NUM-25, NUM-26
@pytest.mark.parametrize("sign", [1.0, -1.0])
def test_ver11_the_two_current_routes_agree_at_the_lowest_envelope_bias(
    solutions: dict[float, models.ModelSolution], sign: float
) -> None:
    solution = solutions[sign * BIAS_V]
    indicator = _indicator(solution)
    by_indicator = qoi.indicator_currents(solution, AXISYMMETRIC, indicator)
    by_reaction = qoi.reaction_flux_currents(solution, "cis")

    agreement = qoi.RouteAgreement(
        indicator_A=qoi.total_current(by_indicator),
        reaction_A=qoi.total_current(by_reaction),
    )
    logger.info(
        "bias %+0.0f mV: psi %.6e A, reaction %.6e A, relative difference %.2e",
        sign * BIAS_V * 1e3,
        agreement.indicator_A,
        agreement.reaction_A,
        agreement.relative_difference,
    )
    agreement.check()

    # Species by species as well as in total: two per-species errors that cancel
    # in the sum would pass the check above and still corrupt the transport
    # number, which NUM-27 derives from the same integrals.
    for species, current in by_indicator.items():
        pair = qoi.RouteAgreement(indicator_A=current, reaction_A=by_reaction[species])
        assert pair.relative_difference < qoi.ROUTE_AGREEMENT_TOLERANCE, (
            f"{species}: {pair.summary()}"
        )


def test_ver11_a_symmetric_pore_shows_no_rectification_the_extraction_invented(
    solutions: dict[float, models.ModelSolution],
) -> None:
    forward = qoi.extract(
        solutions[BIAS_V], AXISYMMETRIC, _indicator(solutions[BIAS_V]), bias_V=BIAS_V
    )
    reverse = qoi.extract(
        solutions[-BIAS_V], AXISYMMETRIC, _indicator(solutions[-BIAS_V]), bias_V=-BIAS_V
    )
    ratio = qoi.rectification(forward, reverse)
    spurious = abs(ratio - 1.0)
    assert forward.agreement is not None
    assert reverse.agreement is not None
    worst = max(forward.agreement.relative_difference, reverse.agreement.relative_difference)
    logger.info(
        "symmetric pore at +/-%.0f mV: RR = %.6f, spurious signal %.2e, worst route "
        "difference %.2e, declared tolerance %.1e",
        BIAS_V * 1e3,
        ratio,
        spurious,
        worst,
        qoi.ROUTE_AGREEMENT_TOLERANCE,
    )
    assert worst < qoi.ROUTE_AGREEMENT_TOLERANCE
    assert spurious < qoi.ROUTE_AGREEMENT_TOLERANCE, (
        f"a pore symmetric in z cannot rectify, but the extraction reports "
        f"RR - 1 = {spurious:.3e}; that is the failure mode RSK-03 names"
    )


# NUM-24
def test_ver11_conductance_is_positive_at_both_signs_of_the_bias(
    solutions: dict[float, models.ModelSolution],
) -> None:
    for bias in (BIAS_V, -BIAS_V):
        solution = solutions[bias]
        quantities = qoi.extract(solution, AXISYMMETRIC, _indicator(solution), bias_V=bias)
        assert quantities.conductance_S > 0.0, quantities.summary()
        assert 0.0 < quantities.transport_number < 1.0


def test_ver11_a_negatively_charged_pore_is_cation_selective(
    solutions: dict[float, models.ModelSolution],
) -> None:
    solution = solutions[BIAS_V]
    quantities = qoi.extract(solution, AXISYMMETRIC, _indicator(solution), bias_V=BIAS_V)
    logger.info(
        "t+ = %.4f at %.2f M against %.3f C/m^2",
        quantities.transport_number,
        CONCENTRATION_M,
        SURFACE_CHARGE_C_M2,
    )
    assert quantities.transport_number > 0.5, (
        "a negatively charged wall excludes the anion, so the cation must carry "
        f"more than half the current; got {quantities.transport_number:.4f}"
    )


@pytest.mark.parametrize(
    ("fraction", "shift_nm"),
    [(0.8, 0.0), (0.5, 2.0), (0.5, -2.0), (0.3, 0.0), (0.98, 0.0)],
    ids=["centred", "shifted-up", "shifted-down", "narrow", "whole-lumen"],
)
def test_num24_the_indicator_current_does_not_depend_on_the_band(
    solutions: dict[float, models.ModelSolution], fraction: float, shift_nm: float
) -> None:
    solution = solutions[BIAS_V]
    reference = qoi.total_current(qoi.reaction_flux_currents(solution, "cis"))
    current = qoi.total_current(
        qoi.indicator_currents(
            solution, AXISYMMETRIC, _indicator(solution, fraction=fraction, shift_nm=shift_nm)
        )
    )
    difference = abs(current - reference) / abs(reference)
    logger.info(
        "band fraction %.2f shifted %+.1f nm: I = %.6e A, %.2e from the reaction flux",
        fraction,
        shift_nm,
        current,
        difference,
    )
    assert difference < qoi.ROUTE_AGREEMENT_TOLERANCE, (
        f"the current moved by {difference:.3e} when the psi band moved; the domain form "
        "is cross-section independent or it is not usable (NUM-23, NUM-24)"
    )


# NUM-34
CORRECTED_PORE = CylindricalPoreGeometry(
    pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0
)

CORRECTED_CASE = """
schema: nanopnp/case/v0.5
name: corrected-routes
inputs:
  mesh: {{path: {path}, format: vol, groups: {{default: interface}}}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 0.1
  temperature_K: 298.15
  parameters: willems2020_nacl
  corrections:
    diffusivity:  {{model: willems2020_nacl, wall: true, concentration: true}}
    mobility:     {{model: willems2020_nacl, wall: true, concentration: true}}
    viscosity:    {{model: willems2020_nacl, wall: true, concentration: true}}
    permittivity: {{model: willems2020_nacl}}
    density:      {{model: willems2020_nacl}}
boundary_conditions: {{bias_V: 0.02, ground: cis}}
physics: {{model: epnp-ns, solid_permittivities: {{membrane: 3.2}}}}
numerics: {{continuation: default_ladder, stabilisation: none}}
outputs: [current]
"""

# Measured at maxh 4.0 nm on the 124-element mesh of
# .knowledge/06-numerics-fem/07-quantities-of-interest-and-the-flux-trap.md.
INADMISSIBLE_WALL_H_NM = 1.0

# NUM-26, PHY-02
PLAUSIBLE_WALL_H_NM = 0.5

# NUM-34
ADMISSIBLE_WALL_H_NM = 0.35

# Measured at wall_h 0.35 nm (2.6514e-11 A) and 0.25 nm (2.6538e-11 A).
RESOLVED_CURRENT_A = 2.65e-11


# NUM-34
def _run_corrected(tmp_path: Path, wall_h_nm: float) -> RunResult:
    from nanopnp.io.store import Store
    from nanopnp.pipeline.case import loads_case
    from nanopnp.pipeline.run import run_document

    work = tmp_path / f"wall-{wall_h_nm}"
    work.mkdir(parents=True, exist_ok=True)
    path = work / "pore.vol"
    CORRECTED_PORE.generate(maxh_nm=4.0, wall_h_nm=wall_h_nm).ngmesh.Save(str(path))
    text = CORRECTED_CASE.format(path=path)
    return run_document(
        loads_case(text),
        case_text=text,
        store=Store(work / "store"),
        workspace=work / "scratch",
        write=False,
    )


# NUM-34, QR-12
def test_ver40_the_coarse_mesh_is_refused_rather_than_returning_a_current(tmp_path) -> None:
    from nanopnp.numerics.gates import GateViolationError

    with pytest.raises(GateViolationError) as raised:
        _run_corrected(tmp_path, INADMISSIBLE_WALL_H_NM)
    message = str(raised.value)
    logger.info("wall_h %.2f nm refused: %s", INADMISSIBLE_WALL_H_NM, message)
    assert "wall-distance admissibility" in message
    assert "min d" in message


# NUM-34
def test_ver40_the_plausible_mesh_passes_num26_and_is_still_refused(tmp_path) -> None:
    from dataclasses import replace as replace_dataclass

    from nanopnp.charge.stage import ResolvedFields
    from nanopnp.mesh.ingest import ingest
    from nanopnp.numerics.gates import GateViolationError
    from nanopnp.numerics.measures import AXISYMMETRIC as MEASURES
    from nanopnp.pipeline.case import loads_case, resolve
    from nanopnp.post.indicator import axial_indicator
    from nanopnp.solve.continuation import run_ladder as climb
    from nanopnp.solve.state import check_wall_distance, ladder, wall_distance_field

    work = tmp_path / "plausible"
    work.mkdir()
    path = work / "pore.vol"
    CORRECTED_PORE.generate(maxh_nm=4.0, wall_h_nm=PLAUSIBLE_WALL_H_NM).ngmesh.Save(str(path))
    resolved = resolve(loads_case(CORRECTED_CASE.format(path=path)))
    ingested = ingest(resolved.mesh, resolved)
    order = int(resolved.model_options.get("order", MEASURES.element_order))
    measures = replace_dataclass(MEASURES, element_order=order)
    distance = wall_distance_field(resolved, ingested.mesh, order=order)

    # The gate refuses it. Raised here rather than through the run driver so that
    # the solve below can still be performed: what this test needs is both facts
    # about *one* mesh, and the production path stops at the first.
    with pytest.raises(GateViolationError):
        check_wall_distance(resolved, ingested.mesh, distance)

    empty = ResolvedFields(charge=None, conservation=None, eps_r=None, material_means=())
    solution = climb(ladder(resolved, ingested.mesh, measures, distance, empty)).solution
    psi = axial_indicator(solution.space.mesh, lower_nm=-2.4, upper_nm=2.4, order=order)
    agreement = qoi.RouteAgreement(
        indicator_A=qoi.total_current(qoi.indicator_currents(solution, measures, psi)),
        reaction_A=qoi.total_current(qoi.reaction_flux_currents(solution)),
    )
    error = abs(agreement.reaction_A - RESOLVED_CURRENT_A) / RESOLVED_CURRENT_A
    logger.info(
        "wall_h %.2f nm: current %.6e A (%.1f %% from the resolved value), route agreement %.2e",
        PLAUSIBLE_WALL_H_NM,
        agreement.reaction_A,
        error * 100.0,
        agreement.relative_difference,
    )

    assert agreement.relative_difference < qoi.ROUTE_AGREEMENT_TOLERANCE, (
        "if NUM-26 caught this mesh, the gate would not be the only thing that does "
        "and this test would be asserting nothing"
    )
    assert error > 0.10, (
        "the whole point of this row is that the passing number is badly wrong; "
        f"measured {error:.1%} against the resolved value"
    )


# NUM-26
def test_ver40_the_admissible_mesh_passes_the_gate_and_both_routes(tmp_path) -> None:
    result = _run_corrected(tmp_path, ADMISSIBLE_WALL_H_NM)
    quantities = result.quantities
    routes = dict(quantities["route_agreement"])
    current = float(quantities["current_A"])
    error = abs(current - RESOLVED_CURRENT_A) / RESOLVED_CURRENT_A
    logger.info(
        "wall_h %.2f nm: current %.6e A (%.2f %% from the resolved value), route agreement %.2e",
        ADMISSIBLE_WALL_H_NM,
        current,
        error * 100.0,
        routes["relative_difference"],
    )
    assert routes["relative_difference"] < qoi.ROUTE_AGREEMENT_TOLERANCE
    assert error < 0.02

    # NUM-34 requires the measured minimum in the provenance manifest, whether or
    # not the gate fired: a field that passed narrowly is a fact about the mesh.
    measured = dict(result.manifest.geometry_and_mesh["wall_distance"])
    assert measured["minimum_nm"] > 0.0
    assert measured["negative_fraction"] == 0.0
    logger.info("NUM-34 recorded min d = %.3e nm", measured["minimum_nm"])


# NUM-26, NUM-30, VER-42
STABILISED_CONTRIBUTION = -1.906e-11


# NUM-26
@pytest.fixture(scope="module")
def stabilised() -> models.ModelSolution:
    mesh = PORE.generate(maxh_nm=5.0, wall_h_nm=0.4)
    ladder = default_ladder(
        mesh,
        concentration_M=CONCENTRATION_M,
        bias_V=BIAS_V,
        surface_charge_C_m2=SURFACE_CHARGE_C_M2,
        solid_permittivities=MEMBRANE_PERMITTIVITY,
        start_concentration_M=None,
        charge_steps=2,
        stabilisation="reference",
    )
    result = run_ladder([rung for rung in ladder if rung.stage <= 5])
    logger.info(
        "reference at %+0.0f mV: %d rungs, %d iterations, %.1f s, max cell Peclet %.4f",
        BIAS_V * 1e3,
        len(result.rungs),
        result.iterations,
        result.seconds,
        result.max_cell_peclet or float("nan"),
    )
    return result.solution


# NUM-11, NUM-14, NUM-24, NUM-25, NUM-27, QR-04, VER-11
def test_num26_the_routes_agree_in_reference_only_because_psi_carries_the_term(
    stabilised: models.ModelSolution,
) -> None:
    indicator = _indicator(stabilised)
    by_indicator = qoi.indicator_currents(stabilised, AXISYMMETRIC, indicator)
    by_reaction = qoi.reaction_flux_currents(stabilised, "cis")
    contribution = qoi.stabilisation_currents(stabilised, AXISYMMETRIC, indicator)

    agreement = qoi.RouteAgreement(
        indicator_A=qoi.total_current(by_indicator),
        reaction_A=qoi.total_current(by_reaction),
    )
    total_contribution = qoi.total_current(contribution)
    bare = agreement.indicator_A - total_contribution
    without_the_term = abs(bare - agreement.reaction_A) / abs(agreement.reaction_A)
    logger.info(
        "reference: psi %.6e A, reaction %.6e A, agreement %.2e; bare psi integral %.6e A, "
        "%.2e from the reaction flux; S_i(psi) %.6e A (%.2f %% of I)",
        agreement.indicator_A,
        agreement.reaction_A,
        agreement.relative_difference,
        bare,
        without_the_term,
        total_contribution,
        100.0 * total_contribution / agreement.reaction_A,
    )
    agreement.check()

    # The gap the term closes, against the term measured on its own. Relative to
    # the contribution, not to the current: this is an assertion about whether the
    # reported number *is* the gap, and 1e-3 of the current would admit a reported
    # value wrong by a fifth of itself.
    gap = agreement.reaction_A - bare
    assert abs(gap - total_contribution) < 1.0e-3 * abs(total_contribution), (
        f"the two routes differ by {gap:.6e} A and the reported stabilisation "
        f"contribution is {total_contribution:.6e} A; NUM-26's amended identity says "
        "those are the same integral"
    )

    # And the gap matters: if it were inside the tolerance, the clause would be
    # bookkeeping rather than the reason the routes agree at all.
    assert without_the_term > 10.0 * qoi.ROUTE_AGREEMENT_TOLERANCE, (
        f"without S_i(psi) the routes are only {without_the_term:.2e} apart, inside "
        "ten times NUM-26's tolerance, so this solve cannot demonstrate the identity; "
        "the mesh is too fine or the mode is not active"
    )

    for species, current in by_indicator.items():
        pair = qoi.RouteAgreement(indicator_A=current, reaction_A=by_reaction[species])
        assert pair.relative_difference < qoi.ROUTE_AGREEMENT_TOLERANCE, (
            f"{species}: {pair.summary()}"
        )
        species_gap = by_reaction[species] - (current - contribution[species])
        assert abs(species_gap - contribution[species]) < 1.0e-3 * abs(contribution[species]), (
            f"{species}: gap {species_gap:.6e} A against a reported contribution of "
            f"{contribution[species]:.6e} A"
        )


# NUM-26, PHY-22
def test_num11_the_stabilisation_current_is_the_bias_and_is_exactly_zero_in_none(
    solutions: dict[float, models.ModelSolution], stabilised: models.ModelSolution
) -> None:
    unstabilised = solutions[BIAS_V]
    bare_none = qoi.stabilisation_currents(unstabilised, AXISYMMETRIC, _indicator(unstabilised))
    for species, value in bare_none.items():
        assert value == 0.0, (
            f"{species}: the 'none' mode assembles no stabilisation term, so its "
            f"contribution is exactly zero, not {value!r}"
        )

    indicator = _indicator(stabilised)
    contribution = qoi.total_current(
        qoi.stabilisation_currents(stabilised, AXISYMMETRIC, indicator)
    )
    plain = qoi.total_current(qoi.reaction_flux_currents(unstabilised, "cis"))
    biased = qoi.total_current(qoi.reaction_flux_currents(stabilised, "cis"))
    measured_bias = biased - plain
    logger.info(
        "current in none %.6e A, in reference %.6e A: bias %.6e A (%.2f %%); reported "
        "S_i(psi) %.6e A, residual %.2e of I",
        plain,
        biased,
        measured_bias,
        100.0 * measured_bias / plain,
        contribution,
        abs(measured_bias - contribution) / abs(plain),
    )

    assert abs(contribution) > 10.0 * qoi.ROUTE_AGREEMENT_TOLERANCE * abs(plain), (
        "a contribution inside ten times the route tolerance cannot be distinguished "
        f"from the routes' own disagreement; got {contribution:.6e} A against "
        f"{plain:.6e} A"
    )
    assert abs(measured_bias - contribution) < 5.0e-3 * abs(plain), (
        f"the single-run contribution {contribution:.6e} A does not reproduce the "
        f"two-run bias {measured_bias:.6e} A to the accuracy of the bare indicator "
        "integral; either the term is not the whole difference or one solve moved"
    )

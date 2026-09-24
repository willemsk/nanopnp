"""VER-11: the two current-extraction routes agree, and neither depends on a section.

This is the test RSK-03 exists for. A continuous-Galerkin flux is not pointwise
conservative, so integrating it across an interior cross-section gives a current
that drifts from section to section by per-cent amounts — comfortably more than
the rectification signal at low bias, and entirely invisible in the answer. NUM-23
therefore forbids that route, NUM-24 and NUM-25 mandate two others, and NUM-26
asks for their agreement in CI. That agreement is what this file asserts.

Two claims are made, and they are different claims.

1. **The routes agree** (VER-11, QR-04) to better than
   :data:`~nanopnp.post.qoi.ROUTE_AGREEMENT_TOLERANCE`, which is 10⁻³ relative
   and, by the derivation recorded under NUM-26, well below the rectification
   signal at the lowest bias of the FR-17 envelope. Both signs of the bias are
   checked, because a sign error in either route survives a single-sign test.

2. **The indicator route does not care where the band is** — the property that
   makes NUM-24 legitimate and NUM-23 unnecessary. Moving the band up the lumen,
   down the lumen, or widening it to the whole membrane thickness must not change
   the current. This is the direct evidence, on this discretisation, that the
   smeared cross-section removes the section dependence a sharp one has.

The pore is charged, which is what makes the currents unequal between species and
gives the rectification something to be a signal *of*; and it is run at ±50 mV,
the lowest bias of the envelope, where the signal is smallest and the tolerance
therefore hardest to justify.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import ngsolve as ngs
import pytest

from nanopnp.mesh.primitives import CylindricalPoreGeometry
from nanopnp.physics import models
from nanopnp.physics.measures import AXISYMMETRIC
from nanopnp.post import qoi
from nanopnp.post.indicator import axial_indicator, lumen_band
from nanopnp.solve.continuation import default_ladder, run_ladder

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.io.run import RunResult

logger = logging.getLogger(__name__)

PORE = CylindricalPoreGeometry(
    pore_radius_nm=2.0, membrane_thickness_nm=13.0, reservoir_radius_nm=25.0
)
"""A modest reservoir on a coarse mesh. Nothing here is compared against a closed
form — VER-17 is where the absolute magnitude has to be right — so the mesh is
sized for the solve to converge and no finer. The route agreement is set by the
residual Newton leaves behind rather than by the discretisation, and it measures
3.8e-6 at every mesh tried, from 3 400 to 7 300 degrees of freedom [tested]."""
CONCENTRATION_M = 0.5
BIAS_V = 0.05
"""The lowest bias of the FR-17 envelope: the hardest place for the tolerance."""

SURFACE_CHARGE_C_M2 = -0.05
"""A charged pore, so that the two species carry unequal currents and there is a
selectivity for a wrong current to corrupt. The magnitude is a modelling choice
for this benchmark, not a fitted property of any pore."""

MEMBRANE_PERMITTIVITY = {"membrane": 2.0}
"""An insulating membrane. Any small value serves: the benchmark asks whether two
extraction routes agree on one solution, not what that solution is."""


@pytest.fixture(scope="module")
def solutions() -> dict[float, models.ModelSolution]:
    """Return a converged ``pnp`` solution at each sign of the bias.

    Reached through the NUM-18 ladder rather than cold, and shared across the
    tests below: the solve is the expensive part and every assertion here is a
    reading of the same two fields.
    """
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
    """Return psi over the fluid, with the band optionally moved along the lumen.

    ``axial_indicator`` runs :func:`check_indicator` itself, so an inverted or
    mispositioned band never reaches an assertion below as a wrong number.
    """
    lower, upper = lumen_band(PORE, fraction=fraction)
    return axial_indicator(
        solution.space.mesh,
        lower_nm=lower + shift_nm,
        upper_nm=upper + shift_nm,
        order=AXISYMMETRIC.element_order,
    )


@pytest.mark.parametrize("sign", [1.0, -1.0])
def test_ver11_the_two_current_routes_agree_at_the_lowest_envelope_bias(
    solutions: dict[float, models.ModelSolution], sign: float
) -> None:
    """NUM-24 and NUM-25 on the same solution, to the tolerance declared in NUM-26.

    Both signs, because a sign error in either route is invisible in a
    single-sign test: the two would still agree, and both would be wrong.
    """
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
    """A pore symmetric in ``z`` must give ``RR = 1``, and this one does to 1e-4.

    This is where RSK-03 would show. Rectification is the ratio of the forward
    and reverse currents, so an extraction error that depends on the direction of
    the flux — which a cross-section integral of a non-conservative CG flux is —
    manufactures a rectification ratio out of nothing, on a pore that cannot
    rectify at all. ``CylindricalPoreGeometry`` is a straight lumen with a
    uniform wall charge and is symmetric about ``z = 0``, so the physical answer
    is exactly 1 and any departure is the extraction's own.

    The test therefore reads the other way round from the requirement's wording.
    VER-11 asks for agreement finer than the rectification signal; the reference
    pore's signal is a property of *its* asymmetry, which this geometry does not
    have and which no Tier-2 benchmark can measure. What can be measured here is
    the spurious signal the extraction itself contributes, and the assertion is
    that it is far below the smallest signal the envelope must resolve.
    """
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


def test_ver11_conductance_is_positive_at_both_signs_of_the_bias(
    solutions: dict[float, models.ModelSolution],
) -> None:
    """The sign convention, asserted where a mistake in it would be visible.

    ``psi`` is 1 on cis and the current is referenced to the grounded cis
    electrode, so a positive bias on trans drives a positive current and
    ``G = I / V_bias > 0`` at either sign. An inverted indicator, or the minus
    sign the NUM-24 clause carried before this implementation, makes every
    conductance negative and nothing else changes.
    """
    for bias in (BIAS_V, -BIAS_V):
        solution = solutions[bias]
        quantities = qoi.extract(solution, AXISYMMETRIC, _indicator(solution), bias_V=bias)
        assert quantities.conductance_S > 0.0, quantities.summary()
        assert 0.0 < quantities.transport_number < 1.0


def test_ver11_a_negatively_charged_pore_is_cation_selective(
    solutions: dict[float, models.ModelSolution],
) -> None:
    """The transport number is above 1/2, which localises a species-block mix-up.

    Both routes read a species by its block index in the product space. Reading
    the wrong block would leave the *total* current right and the transport
    number inverted, so the total is not enough to check.
    """
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
    """Move the band, widen it, narrow it: the current must not move (NUM-24, NUM-23).

    This is the whole justification for the domain form. A cross-section integral
    of the CG flux — the route NUM-23 bans — is a *sharp* version of this same
    band, and it is precisely its dependence on where the section is taken that
    makes it unusable. Smearing the section over a band averages that dependence
    away, and the assertion below is the measurement of by how much.

    The reaction flux is the reference here rather than the centred band, because
    it is the route that does not involve a band at all.

    Every band stays inside the lumen. That is a constraint of this check rather
    than of the method: a band running past the pore mouth is still legitimate —
    the flux is conserved there too — but ``psi`` would then no longer be exactly
    1 on the cis cap, and :func:`check_indicator` refuses it for the reason
    ``axial_indicator`` documents.
    """
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


# -- VER-40: the NUM-34 gate discriminates the regime NUM-26 was reporting ------


CORRECTED_PORE = CylindricalPoreGeometry(
    pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0
)
"""The toy pore of ``.knowledge/06`` section 7.1.1, where the undershoot was measured.

A different geometry from :data:`PORE` above and deliberately so: the classical
benchmark's mesh is sized for a solve that reads no distance field at all, and
this one is sized to sit on either side of NUM-34's threshold.
"""

CORRECTED_CASE = """
schema: nanopnp/case/v2
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

INADMISSIBLE_WALL_H_NM = 1.0
"""``min d = -0.94`` nm over the fluid, 9.7 % of samples negative. **[tested]**

Measured on this pore at ``maxh`` 4.0 nm, where it is the 124-element mesh of
``.knowledge/06`` section 7.1.1.
"""

PLAUSIBLE_WALL_H_NM = 0.5
"""``min d = -1.2`` nm — and the routes agree to 2.6e-05 anyway. **[tested]**

This is the row that makes the gate necessary rather than merely tidy. With the
PHY-02 clamp in place the sign inversion is gone, so the two extraction routes
agree forty times inside NUM-26's tolerance — and the current is 13 % away from
the resolved value. The clamp removed the only signal the run had.
"""

ADMISSIBLE_WALL_H_NM = 0.35
"""``min d = +9.5e-06`` nm. The coarsest wall spacing NUM-34 admits here. **[tested]**"""

RESOLVED_CURRENT_A = 2.65e-11
"""The current the two admissible meshes agree on, to the per-cent this test needs.

Measured at ``wall_h`` 0.35 nm (2.6514e-11 A) and 0.25 nm (2.6538e-11 A) on this
pore at 0.1 M and +20 mV. Not a reference value and not asserted as one: it is
the scale against which the *inadmissible* mesh's 17 % error is stated, and the
assertions below are on that difference rather than on this number. **[tested]**
"""


def _run_corrected(tmp_path: Path, wall_h_nm: float) -> RunResult:
    """Run the corrected case on one mesh, through the production path.

    Through :func:`~nanopnp.io.run.run_document` rather than by building a ladder
    here, because the NUM-34 gate lives in stage 10 and what is under test is
    that a run *cannot reach Newton* on an inadmissible field. A test that
    assembled its own ladder would bypass the very thing it is asserting.
    """
    from nanopnp.io.case import loads_case
    from nanopnp.io.run import run_document
    from nanopnp.io.store import Store

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


def test_ver40_the_coarse_mesh_is_refused_rather_than_returning_a_current(tmp_path) -> None:
    """NUM-34 aborts the run before Newton, naming what it measured (QR-12).

    The 124-element mesh of ``.knowledge/06`` section 7.1.1 is where the P2
    distance field undershoots to -0.94 nm at the re-entrant corner of the pore
    mouth. Unclamped, that put the ion wall function below its root and reversed
    the sign of ``D_i`` and ``mu_i`` over a tenth of the sampled fluid; clamped,
    it merely returns a wrong current. Neither is a result, and the gate is what
    makes the run stop rather than report one.
    """
    from nanopnp.solve.gates import GateViolationError

    with pytest.raises(GateViolationError) as raised:
        _run_corrected(tmp_path, INADMISSIBLE_WALL_H_NM)
    message = str(raised.value)
    logger.info("wall_h %.2f nm refused: %s", INADMISSIBLE_WALL_H_NM, message)
    assert "wall-distance admissibility" in message
    assert "min d" in message


def test_ver40_the_plausible_mesh_passes_num26_and_is_still_refused(tmp_path) -> None:
    """The row that says why the clamp needs the gate beside it, not instead of it.

    At ``wall_h`` 0.5 nm the distance field goes about a nanometre below zero —
    deeper than the coarser mesh above — and yet, with the driver clamped, the
    two extraction routes of NUM-26 agree to 2.6e-05, forty times inside their
    tolerance, while the current is 13 % below the resolved value. Route
    agreement is not a resolution test once the clamp has removed the sign
    inversion that was making it one, and this is the mesh that proves it: every
    check the run has except NUM-34 comes back clean, and the answer is wrong by
    a factor no experiment could excuse.

    Asserted by measuring both halves rather than by assuming either. The
    unclamped route disagreement is not reproducible here — the clamp is now
    unconditional — so what is measured is what a *reader* would see today.
    """
    from dataclasses import replace as replace_dataclass

    from nanopnp.charge.stage import ResolvedFields
    from nanopnp.io.case import loads_case, resolve
    from nanopnp.mesh.ingest import ingest
    from nanopnp.physics.measures import AXISYMMETRIC as MEASURES
    from nanopnp.post.indicator import axial_indicator
    from nanopnp.solve.continuation import run_ladder as climb
    from nanopnp.solve.gates import GateViolationError
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


def test_ver40_the_admissible_mesh_passes_the_gate_and_both_routes(tmp_path) -> None:
    """The other side of the regime: gated clean, and the routes agree.

    ``wall_h`` 0.35 nm gives ``min d = +9.5e-06`` nm, so the gate passes and
    records the measurement; the run completes, and its NUM-26 agreement is what
    the stage-11 artefact reports. The current is within a per cent of the
    resolved value, which is the difference between this mesh and the one above.
    """
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


# -- NUM-26 under a stabilisation mode: the identity, measured -------------------


STABILISED_CONTRIBUTION = -1.906e-11
"""``S_i(psi)`` summed over species on this pore in ``reference``: -8.1 % of I. **[tested]**

Measured at ``maxh`` 5.0 nm / ``wall_h`` 0.4 nm, 0.5 M, +50 mV, -0.05 C/m^2, where
the maximum cell Peclet number is 0.775. Recorded for the scale, not asserted as a
reference value: the assertions below are on the *identity* and on the fraction
being far outside NUM-26's tolerance, both of which hold at any resolution.

Larger than the per-cent the plan's section 1 predicted, and legitimately so: that
estimate is for a mesh meeting NUM-30, where ``Pe_K`` is 0.3 and the added
diffusivity ratio ``Pe_K^2`` is 0.09. This mesh sits at ``Pe_K = 0.775``, so the
ratio is 0.6 and the bias is correspondingly bigger. VER-42 is where the number is
watched under refinement.
"""


@pytest.fixture(scope="module")
def stabilised() -> models.ModelSolution:
    """Return the same solve in ``reference``, for the stabilised half of NUM-26.

    One sign only. Both signs are already checked in ``none`` above, and what this
    fixture exists for is the *term*, which is even in the bias to the accuracy
    anything here measures.
    """
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


def test_num26_the_routes_agree_in_reference_only_because_psi_carries_the_term(
    stabilised: models.ModelSolution,
) -> None:
    """NUM-26's amended identity, measured from the gap rather than assumed.

    Three numbers are read off one solution: the NUM-25 reaction flux, the NUM-24
    indicator form as this implementation builds it, and the stabilisation term
    tested against ``psi`` on its own. The first two agree to NUM-26's tolerance.
    Subtract the third from the indicator form — the bare
    ``int J~_i . grad(psi)`` the clause carried before the NUM-14 NOTE — and the
    two routes come apart by eighty times that tolerance.

    That is the content of the NOTE: in a stabilised mode the assembled residual
    *contains* the stabilisation term, so the reaction flux carries it whether or
    not anyone decided it should, and a NUM-24 route that omits it differs from
    NUM-25 by exactly the quantity the mode exists to measure. The assertion is
    therefore that the gap **equals the independently computed contribution**, to
    a relative tolerance on the contribution itself. A test that only checked the
    routes agreed would pass with the term added to both routes from one shared
    integral and could not tell that apart from the identity holding.

    Per species as well as in total, because the term is per species and two
    contributions that cancelled in the sum would satisfy the total and corrupt
    the NUM-27 transport number (NUM-11, NUM-24, NUM-25, NUM-26, QR-04, VER-11).
    """
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


def test_num11_the_stabilisation_current_is_the_bias_and_is_exactly_zero_in_none(
    solutions: dict[float, models.ModelSolution], stabilised: models.ModelSolution
) -> None:
    """``stabilisation_current_A`` is the SUPG bias on the QoI, from one run.

    NUM-11 says SUPG biases the current quantity of interest; the NUM-26 NOTE says
    the size of that bias SHALL be reportable "from a single run rather than from a
    difference of two". This test is the calibration of that claim: it takes the
    difference of two — the same pore, same mesh, same bias, solved in ``none`` and
    in ``reference`` — and checks that the single-run number reproduces it.

    It does, to 2 % of itself, because the *bare* indicator integral is nearly
    mode-independent: 2.5327e-10 against 2.5288e-10, 0.15 % apart, so essentially
    the whole difference between the two currents lives in ``S_i(psi)``. The
    tolerance is therefore stated on the residual difference as a fraction of the
    **current**, where 0.15 % is the honest scale, rather than as a fraction of the
    contribution, where it would be 2 %.

    ``none`` contributes exactly ``0.0`` and not approximately zero: that mode
    assembles no term at all, so the integral is never taken (PHY-22, NUM-11,
    NUM-26).
    """
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

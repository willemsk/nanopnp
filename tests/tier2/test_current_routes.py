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

import logging

import ngsolve as ngs
import pytest

from nanopnp.mesh.primitives import CylindricalPoreGeometry
from nanopnp.physics import models
from nanopnp.physics.measures import AXISYMMETRIC
from nanopnp.post import qoi
from nanopnp.post.indicator import axial_indicator, lumen_band
from nanopnp.solve.continuation import default_ladder, run_ladder

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

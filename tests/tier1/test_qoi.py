"""The NUM-27 derived quantities and the NUM-26 route-agreement check.

The arithmetic here is elementary and that is the point: every one of these
quantities is a ratio, so a sign error or a swapped argument produces a number of
the right order that is simply wrong. The route-agreement check is the one piece
of machinery, and what it defends is RSK-03 — a current wrong by per-cent amounts
is a plausible, stable, publishable result, and only a second independent route
notices.

The end-to-end value of a current, ``2 pi`` and all, is pinned by VER-17 in
``tests/tier2/test_access_conductance.py``, which is the only place an absolute
magnitude is checked against a closed form.
"""

import math

import pytest

from nanopnp.post.qoi import (
    ROUTE_AGREEMENT_TOLERANCE,
    QuantitiesOfInterest,
    RouteAgreement,
    RouteDisagreementError,
    conductance,
    rectification,
    rectification_ratio,
    summarise,
    total_current,
    transport_number,
)

CURRENTS = {"Na": 3.0e-9, "Cl": 1.0e-9}
"""A cation-selective pore: both species carry current the same way."""


def test_num27_total_current_is_the_sum_over_species() -> None:
    """``I = sum_i I_i``, the per-species currents already carrying their valence."""
    assert total_current(CURRENTS) == pytest.approx(4.0e-9, rel=1e-15)


def test_num27_transport_number_is_the_cation_share() -> None:
    """``t+ = I+ / (I+ + I-)``; 0.75 for a pore carrying three parts cation to one."""
    assert transport_number(CURRENTS, ["Na"]) == pytest.approx(0.75, rel=1e-15)
    assert transport_number(CURRENTS, ["Cl"]) == pytest.approx(0.25, rel=1e-15)
    assert transport_number(CURRENTS, ["Na", "Cl"]) == pytest.approx(1.0, rel=1e-15)


def test_num27_transport_number_names_a_species_it_has_no_current_for() -> None:
    """A misspelt species is a typo, not a perfectly selective pore."""
    with pytest.raises(ValueError, match="no current for K"):
        transport_number(CURRENTS, ["K"])


def test_num27_transport_number_is_undefined_at_zero_current() -> None:
    """Zero over zero is not 1/2, and returning it would be a fabricated result."""
    with pytest.raises(ValueError, match="undefined at zero total current"):
        transport_number({"Na": 1.0e-9, "Cl": -1.0e-9}, ["Na"])


def test_num27_rectification_ratio_is_the_ratio_of_magnitudes() -> None:
    """``RR = |I(+V)| / |I(-V)|``; the currents have opposite signs, the ratio does not."""
    assert rectification_ratio(4.0e-9, -2.0e-9) == pytest.approx(2.0, rel=1e-15)
    assert rectification_ratio(-4.0e-9, 2.0e-9) == pytest.approx(2.0, rel=1e-15)


def test_num27_rectification_ratio_is_undefined_at_zero_reverse_current() -> None:
    """An infinite rectification ratio is a division by zero, and is refused."""
    with pytest.raises(ValueError, match="zero reverse current"):
        rectification_ratio(1.0e-9, 0.0)


def test_num27_conductance_is_the_chord_conductance() -> None:
    """``G = I / V_bias``. A positive bias gives a positive conductance (the convention)."""
    assert conductance(4.0e-9, 0.2) == pytest.approx(2.0e-8, rel=1e-15)
    assert conductance(-4.0e-9, -0.2) == pytest.approx(2.0e-8, rel=1e-15)


def test_num27_conductance_is_undefined_at_zero_bias() -> None:
    """The chord conductance at zero bias is the slope, which is a different quantity."""
    with pytest.raises(ValueError, match="undefined at zero bias"):
        conductance(1.0e-9, 0.0)


def _point(bias_V: float, current_A: float) -> QuantitiesOfInterest:
    """Return a minimal operating point, for the pairwise quantities."""
    return QuantitiesOfInterest(
        bias_V=bias_V,
        currents_A={"Na": current_A},
        current_A=current_A,
        transport_number=1.0,
        conductance_S=current_A / bias_V,
        eof_m3_s=None,
        agreement=None,
    )


def test_num27_rectification_compares_two_operating_points() -> None:
    """``RR`` is read off a matched pair, so the pair is what the function takes."""
    assert rectification(_point(0.05, 4.0e-9), _point(-0.05, -2.0e-9)) == pytest.approx(2.0)


def test_num27_rectification_refuses_two_biases_of_the_same_sign() -> None:
    """A "ratio" of two forward points compares unrelated operating points."""
    with pytest.raises(ValueError, match="opposite biases"):
        rectification(_point(0.05, 4.0e-9), _point(0.1, 8.0e-9))


def test_num26_agreeing_routes_pass_the_declared_tolerance() -> None:
    """Two routes within the declared tolerance report a difference and no error."""
    agreement = RouteAgreement(indicator_A=1.0e-9, reaction_A=1.0e-9 * (1.0 + 1e-9))
    assert agreement.relative_difference == pytest.approx(1e-9, rel=1e-6)
    agreement.check()


def test_num26_disagreeing_routes_name_both_currents_and_the_difference() -> None:
    """The message has to say what disagreed; neither number is reported as the answer.

    A relative difference of 1 % is a hundredfold worse than the tolerance and,
    on the ClyA rectification signal, entirely capable of manufacturing or
    erasing it (RSK-03).
    """
    agreement = RouteAgreement(indicator_A=1.0e-9, reaction_A=1.01e-9)
    assert agreement.relative_difference == pytest.approx(1.0 / 101.0, rel=1e-9)
    with pytest.raises(RouteDisagreementError) as raised:
        agreement.check()
    message = str(raised.value)
    assert "1.000000e-09" in message
    assert "1.010000e-09" in message
    assert "NUM-23" in message


def test_num26_the_tolerance_is_declared_and_below_the_rectification_signal() -> None:
    """QR-04 requires a *stated* tolerance, not a relational one.

    It has to sit well below the smallest signal the current is asked to
    resolve. The rectification signal ``|RR - 1|`` of a charged pore at the
    lowest envelope bias is of order 1e-1, so a tenth of a per cent is two
    orders of margin.
    """
    assert ROUTE_AGREEMENT_TOLERANCE == 1e-3
    assert ROUTE_AGREEMENT_TOLERANCE < 1e-2


def test_num26_two_vanishing_currents_do_not_divide_by_zero() -> None:
    """At zero bias both routes give zero and the difference is zero, not NaN."""
    agreement = RouteAgreement(indicator_A=0.0, reaction_A=0.0)
    assert agreement.relative_difference == 0.0
    agreement.check()


def test_fr25_the_summary_states_the_two_pi_convention() -> None:
    """NUM-27's NOTE: a reported quantity must say whether the Jacobian is in it."""
    point = _point(0.05, 4.0e-9)
    summary = point.summary()
    assert summary["two_pi_included"] is True
    assert summary["current_A"] == pytest.approx(4.0e-9)
    assert math.isfinite(summary["conductance_S"])
    assert "route_agreement" not in summary

    checked = _point(0.05, 4.0e-9)
    checked = QuantitiesOfInterest(
        **{**checked.__dict__, "agreement": RouteAgreement(4.0e-9, 4.0e-9)}
    )
    assert checked.summary()["route_agreement"]["relative_difference"] == 0.0


def test_summarise_returns_one_record_per_operating_point() -> None:
    """A sweep's manifest is a list of these, in the order the points were run."""
    records = summarise([_point(0.05, 4.0e-9), _point(-0.05, -2.0e-9)])
    assert [record["bias_V"] for record in records] == [0.05, -0.05]

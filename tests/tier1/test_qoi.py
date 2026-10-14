"""The NUM-27 derived quantities and the NUM-26 route-agreement check."""

import math

import pytest

from nanopnp.post.qoi import (
    ROUTE_AGREEMENT_TOLERANCE,
    QuantitiesOfInterest,
    RouteAgreement,
    RouteDisagreementError,
    _check_species_routes,
    cis_referenced_bias,
    conductance,
    rectification,
    rectification_ratio,
    summarise,
    total_current,
    transport_number,
)

CURRENTS = {"Na": 3.0e-9, "Cl": 1.0e-9}


def test_num27_total_current_is_the_sum_over_species() -> None:
    assert total_current(CURRENTS) == pytest.approx(4.0e-9, rel=1e-15)


def test_num27_transport_number_is_the_cation_share() -> None:
    assert transport_number(CURRENTS, ["Na"]) == pytest.approx(0.75, rel=1e-15)
    assert transport_number(CURRENTS, ["Cl"]) == pytest.approx(0.25, rel=1e-15)
    assert transport_number(CURRENTS, ["Na", "Cl"]) == pytest.approx(1.0, rel=1e-15)


def test_num27_transport_number_names_a_species_it_has_no_current_for() -> None:
    with pytest.raises(ValueError, match="no current for K"):
        transport_number(CURRENTS, ["K"])


def test_num27_transport_number_is_undefined_at_zero_current() -> None:
    with pytest.raises(ValueError, match="undefined at zero total current"):
        transport_number({"Na": 1.0e-9, "Cl": -1.0e-9}, ["Na"])


def test_num27_rectification_ratio_is_the_ratio_of_magnitudes() -> None:
    assert rectification_ratio(4.0e-9, -2.0e-9) == pytest.approx(2.0, rel=1e-15)
    assert rectification_ratio(-4.0e-9, 2.0e-9) == pytest.approx(2.0, rel=1e-15)


def test_num27_rectification_ratio_is_undefined_at_zero_reverse_current() -> None:
    with pytest.raises(ValueError, match="zero reverse current"):
        rectification_ratio(1.0e-9, 0.0)


def test_num27_conductance_is_the_chord_conductance() -> None:
    assert conductance(4.0e-9, 0.2) == pytest.approx(2.0e-8, rel=1e-15)
    assert conductance(-4.0e-9, -0.2) == pytest.approx(2.0e-8, rel=1e-15)


def test_num27_a_trans_grounded_bias_is_read_as_its_cis_referenced_negative() -> None:
    assert cis_referenced_bias(0.1, "cis") == 0.1
    assert cis_referenced_bias(0.1, "trans") == -0.1
    with pytest.raises(ValueError, match="'cis' or 'trans'"):
        cis_referenced_bias(0.1, "bath")


def test_num27_conductance_is_undefined_at_zero_bias() -> None:
    with pytest.raises(ValueError, match="undefined at zero bias"):
        conductance(1.0e-9, 0.0)


def _point(bias_V: float, current_A: float) -> QuantitiesOfInterest:
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
    assert rectification(_point(0.05, 4.0e-9), _point(-0.05, -2.0e-9)) == pytest.approx(2.0)


def test_num27_rectification_refuses_two_biases_of_the_same_sign() -> None:
    with pytest.raises(ValueError, match="opposite biases"):
        rectification(_point(0.05, 4.0e-9), _point(0.1, 8.0e-9))


def test_num27_rectification_refuses_a_swapped_pair() -> None:
    with pytest.raises(ValueError, match="must be the positive bias"):
        rectification(_point(-0.05, -2.0e-9), _point(0.05, 4.0e-9))


def test_qr12_rectification_refuses_a_nan_bias_on_either_side() -> None:
    with pytest.raises(ValueError, match="must be the positive bias"):
        rectification(_point(float("nan"), 4.0e-9), _point(-0.05, -2.0e-9))
    with pytest.raises(ValueError, match="opposite biases"):
        rectification(_point(0.05, 4.0e-9), _point(float("nan"), -2.0e-9))


def test_num26_agreeing_routes_pass_the_declared_tolerance() -> None:
    agreement = RouteAgreement(indicator_A=1.0e-9, reaction_A=1.0e-9 * (1.0 + 1e-9))
    assert agreement.relative_difference == pytest.approx(1e-9, rel=1e-6)
    agreement.check()


def test_num26_disagreeing_routes_name_both_currents_and_the_difference() -> None:
    agreement = RouteAgreement(indicator_A=1.0e-9, reaction_A=1.01e-9)
    assert agreement.relative_difference == pytest.approx(1.0 / 101.0, rel=1e-9)
    with pytest.raises(RouteDisagreementError) as raised:
        agreement.check()
    message = str(raised.value)
    assert "1.000000e-09" in message
    assert "1.010000e-09" in message
    assert "NUM-23" in message


# QR-04
def test_num26_the_tolerance_is_declared_and_below_the_rectification_signal() -> None:
    assert ROUTE_AGREEMENT_TOLERANCE == 1e-3
    assert ROUTE_AGREEMENT_TOLERANCE < 1e-2


@pytest.mark.parametrize(
    ("indicator", "reaction"), [(1.0e-9, math.nan), (math.nan, 1.0e-9), (1.0e-9, math.inf)]
)
def test_num26_a_route_that_is_not_finite_fails_the_check(
    indicator: float, reaction: float
) -> None:
    agreement = RouteAgreement(indicator_A=indicator, reaction_A=reaction)
    assert agreement.relative_difference == math.inf
    with pytest.raises(RouteDisagreementError):
        agreement.check()


def test_num26_a_species_route_that_is_nan_fails_the_per_species_check() -> None:
    with pytest.raises(RouteDisagreementError, match="'Cl'"):
        _check_species_routes(
            {"Na": 3.0e-9, "Cl": 1.0e-9}, {"Na": 3.0e-9, "Cl": math.nan}, tolerance=1e-3
        )


def test_num26_two_vanishing_currents_do_not_divide_by_zero() -> None:
    agreement = RouteAgreement(indicator_A=0.0, reaction_A=0.0)
    assert agreement.relative_difference == 0.0
    agreement.check()


def test_fr25_the_summary_states_the_two_pi_convention() -> None:
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
    records = summarise([_point(0.05, 4.0e-9), _point(-0.05, -2.0e-9)])
    assert [record["bias_V"] for record in records] == [0.05, -0.05]

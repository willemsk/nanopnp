"""Nondimensionalisation against the reference table of NUM-09."""

from __future__ import annotations

import math

import pytest

from nanopnp.core.constants import REFERENCE_TEMPERATURE_K, thermal_voltage
from nanopnp.core.scaling import Scales

CLYA_RADIUS_NM = 2.0
"""Pore radius the NUM-09 table is quoted at."""


def _scales(concentration_M: float) -> Scales:
    """Return the reference scale set at one concentration."""
    return Scales(length_nm=CLYA_RADIUS_NM, concentration_M=concentration_M)


@pytest.mark.parametrize(
    ("concentration_M", "expected_nm"),
    [(0.05, 1.357), (1.0, 0.304), (3.0, 0.175)],
)
def test_num09_debye_length_table(concentration_M: float, expected_nm: float) -> None:
    """The Debye length reproduces the NUM-09 table to its quoted precision."""
    assert _scales(concentration_M).debye_length_nm == pytest.approx(expected_nm, abs=5e-4)


def test_num09_debye_ratio_envelope() -> None:
    """``lambda~`` spans 0.088 to 0.679 over 0.05-3 M at a = 2 nm (NUM-09)."""
    assert _scales(3.0).debye_ratio == pytest.approx(0.088, abs=5e-4)
    assert _scales(0.05).debye_ratio == pytest.approx(0.679, abs=5e-4)


def test_num09_peclet_number_is_below_one() -> None:
    """``Pe = eps V_T^2/(eta D_0)`` is 0.385, so ion transport is not convection-dominated.

    NUM-09 quotes 0.386; that value corresponds to ``eps_r`` near 78.4, whereas
    the model's own fitted ``eps_r,f0`` is 78.15, which gives 0.3847. The
    difference is 0.3 % and changes nothing physically, but it is worth pinning
    rather than rediscovering.
    """
    peclet = _scales(1.0).peclet
    assert peclet == pytest.approx(0.3847, abs=1e-3)
    assert peclet < 1.0


def test_num09_peclet_at_twenty_degrees_is_the_commonly_quoted_value() -> None:
    """At ``eta = 1.00 mPa s`` the Peclet number is the frequently quoted 0.34.

    NUM-09 warns that the two numbers differ only by the temperature at which
    the viscosity was taken. Mixing them across material properties is a silent
    error, so both are pinned here.
    """
    twenty = Scales(length_nm=CLYA_RADIUS_NM, concentration_M=1.0, viscosity_Pa_s=1.00e-3)
    assert twenty.peclet == pytest.approx(0.342, abs=2e-3)


def test_num09_potential_scale_is_the_thermal_voltage() -> None:
    """The potential scale is ``V_T = RT/F``, 25.693 mV at 298.15 K."""
    scales = _scales(1.0)
    assert scales.potential_V == thermal_voltage(REFERENCE_TEMPERATURE_K)
    assert scales.potential_V == pytest.approx(25.693e-3, abs=1e-6)


def test_num09_bias_envelope_in_thermal_voltages() -> None:
    """The +/-200 mV envelope of FR-17 is +/-7.78 thermal voltages."""
    assert _scales(1.0).bias_to_dimensionless(0.2) == pytest.approx(7.784, abs=1e-3)


def test_num09_velocity_and_pressure_scales_are_consistent() -> None:
    """``p_0 = u_0 eta / a``: the pressure and velocity scales share one definition."""
    scales = _scales(1.0)
    assert scales.pressure_Pa == pytest.approx(
        scales.velocity_m_s * scales.viscosity_Pa_s / scales.length_m, rel=1e-12
    )


def test_num09_peclet_equals_advective_over_diffusive_rate() -> None:
    """``Pe`` is equivalently ``u_0 a / D_0``, which is the reading that makes it physics."""
    scales = _scales(1.0)
    assert scales.peclet == pytest.approx(
        scales.velocity_m_s * scales.length_m / scales.diffusivity_m2_s, rel=1e-12
    )


@pytest.mark.parametrize(
    "quantity",
    ["length", "potential", "concentration", "velocity", "pressure", "diffusivity", "current"],
)
def test_num09_conversions_round_trip(quantity: str) -> None:
    """Nondimensionalising and redimensionalising is the identity on every field."""
    scales = _scales(1.0)
    value = 3.7
    assert scales.redimensionalise(
        quantity, scales.nondimensionalise(quantity, value)
    ) == pytest.approx(value, rel=1e-14)


def test_num09_unknown_quantity_names_the_alternatives() -> None:
    """A misnamed field fails loudly and says what it could have been."""
    with pytest.raises(KeyError, match="concentration"):
        _scales(1.0).nondimensionalise("charge", 1.0)


@pytest.mark.parametrize(
    ("field", "value"),
    [("length_nm", 0.0), ("concentration_M", -1.0), ("viscosity_Pa_s", 0.0)],
)
def test_num09_non_positive_scale_is_rejected(field: str, value: float) -> None:
    """A zero or negative scale would divide by zero downstream, so it is refused."""
    arguments = {"length_nm": CLYA_RADIUS_NM, "concentration_M": 1.0, field: value}
    with pytest.raises(ValueError, match=field):
        Scales(**arguments)  # type: ignore[arg-type]


def test_num09_debye_length_scales_as_inverse_square_root_of_concentration() -> None:
    """``lambda_D ~ c^(-1/2)``, the property that makes the mesh requirement predictable."""
    ratio = _scales(0.05).debye_length_nm / _scales(3.0).debye_length_nm
    assert ratio == pytest.approx(math.sqrt(3.0 / 0.05), rel=1e-12)


def test_num09_summary_carries_every_scale_for_the_manifest() -> None:
    """The provenance summary is complete enough to reconstruct the scaling (FR-25)."""
    summary = _scales(1.0).summary()
    for key in ("potential_V", "velocity_m_s", "pressure_Pa", "debye_ratio", "peclet"):
        assert key in summary
        assert math.isfinite(summary[key])

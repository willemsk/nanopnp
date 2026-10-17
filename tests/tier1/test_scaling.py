"""Nondimensionalisation against the reference table of NUM-09."""

from __future__ import annotations

import math

import pytest

from nanopnp.core.constants import REFERENCE_TEMPERATURE_K, thermal_voltage
from nanopnp.core.scaling import Scales

# Pore radius the NUM-09 table is quoted at: SPECIFICATION.md NUM-09.
CLYA_RADIUS_NM = 2.0


def _scales(concentration_M: float) -> Scales:
    return Scales(length_nm=CLYA_RADIUS_NM, concentration_M=concentration_M)


@pytest.mark.parametrize(
    ("concentration_M", "expected_nm"),
    [(0.05, 1.357), (1.0, 0.304), (3.0, 0.175)],
)
def test_num09_debye_length_table(concentration_M: float, expected_nm: float) -> None:
    assert _scales(concentration_M).debye_length_nm == pytest.approx(expected_nm, abs=5e-4)


def test_num09_debye_ratio_envelope() -> None:
    assert _scales(3.0).debye_ratio == pytest.approx(0.088, abs=5e-4)
    assert _scales(0.05).debye_ratio == pytest.approx(0.679, abs=5e-4)


def test_num09_peclet_number_is_below_one() -> None:
    peclet = _scales(1.0).peclet
    assert peclet == pytest.approx(0.3847, abs=1e-3)
    assert peclet < 1.0
    assert Scales(
        length_nm=CLYA_RADIUS_NM, concentration_M=1.0, relative_permittivity=78.4
    ).peclet == pytest.approx(0.386, abs=5e-4)


def test_num09_peclet_at_twenty_degrees_is_the_commonly_quoted_value() -> None:
    twenty = Scales(length_nm=CLYA_RADIUS_NM, concentration_M=1.0, viscosity_Pa_s=1.00e-3)
    assert twenty.peclet == pytest.approx(0.342, abs=2e-3)


def test_num09_potential_scale_is_the_thermal_voltage() -> None:
    scales = _scales(1.0)
    assert scales.potential_V == thermal_voltage(REFERENCE_TEMPERATURE_K)
    assert scales.potential_V == pytest.approx(25.693e-3, abs=1e-6)


# FR-17
def test_num09_bias_envelope_in_thermal_voltages() -> None:
    assert _scales(1.0).bias_to_dimensionless(0.2) == pytest.approx(7.784, abs=1e-3)


def test_num09_velocity_and_pressure_scales_are_consistent() -> None:
    scales = _scales(1.0)
    assert scales.pressure_Pa == pytest.approx(
        scales.velocity_m_s * scales.viscosity_Pa_s / scales.length_m, rel=1e-12
    )


def test_num09_peclet_equals_advective_over_diffusive_rate() -> None:
    scales = _scales(1.0)
    assert scales.peclet == pytest.approx(
        scales.velocity_m_s * scales.length_m / scales.diffusivity_m2_s, rel=1e-12
    )


# NUM-29
def test_num28_force_scale_is_the_permittivity_times_the_thermal_voltage_squared() -> None:
    scales = _scales(1.0)
    assert scales.force_N == pytest.approx(4.568e-13, rel=1e-3)
    assert 0.1e-12 / scales.force_N == pytest.approx(0.219, rel=1e-2)


# NUM-29
def test_num28_force_scale_does_not_depend_on_the_reference_length() -> None:
    small = Scales(length_nm=1.0, concentration_M=1.0)
    large = Scales(length_nm=20.0, concentration_M=1.0)
    assert small.force_N == pytest.approx(large.force_N, rel=1e-15)
    assert small.pressure_Pa != pytest.approx(large.pressure_Pa, rel=1e-3)


def test_num28_force_scale_is_the_pressure_scale_through_a_pore_sized_area() -> None:
    scales = _scales(1.0)
    assert scales.force_N == pytest.approx(scales.pressure_Pa * scales.length_m**2, rel=1e-14)


@pytest.mark.parametrize(
    "quantity",
    [
        "length",
        "potential",
        "concentration",
        "velocity",
        "pressure",
        "force",
        "diffusivity",
        "current",
        "volumetric_flow",
        "charge_density",
        "surface_charge",
    ],
)
def test_num09_conversions_round_trip(quantity: str) -> None:
    scales = _scales(1.0)
    value = 3.7
    assert scales.redimensionalise(
        quantity, scales.nondimensionalise(quantity, value)
    ) == pytest.approx(value, rel=1e-14)


def test_num09_unknown_quantity_names_the_alternatives() -> None:
    with pytest.raises(KeyError, match="concentration"):
        _scales(1.0).nondimensionalise("charge", 1.0)


@pytest.mark.parametrize(
    ("field", "value"),
    [("length_nm", 0.0), ("concentration_M", -1.0), ("viscosity_Pa_s", 0.0)],
)
def test_num09_non_positive_scale_is_rejected(field: str, value: float) -> None:
    arguments = {"length_nm": CLYA_RADIUS_NM, "concentration_M": 1.0, field: value}
    with pytest.raises(ValueError, match=field):
        Scales(**arguments)  # type: ignore[arg-type]


def test_num09_debye_length_scales_as_inverse_square_root_of_concentration() -> None:
    ratio = _scales(0.05).debye_length_nm / _scales(3.0).debye_length_nm
    assert ratio == pytest.approx(math.sqrt(3.0 / 0.05), rel=1e-12)


# FR-25
def test_num09_summary_carries_every_scale_for_the_manifest() -> None:
    scales = _scales(1.0)
    summary = scales.summary()
    for key in ("potential_V", "velocity_m_s", "pressure_Pa", "force_N", "debye_ratio", "peclet"):
        assert key in summary
        assert math.isfinite(summary[key])

    defining = {
        field: getattr(scales, field)
        for field in (
            "length_nm",
            "concentration_M",
            "temperature_K",
            "diffusivity_m2_s",
            "viscosity_Pa_s",
            "relative_permittivity",
        )
    }
    assert defining.items() <= summary.items()
    assert Scales(**defining).summary() == summary  # the manifest reconstructs the run
    twenty = Scales(
        length_nm=CLYA_RADIUS_NM, concentration_M=1.0, temperature_K=293.15, viscosity_Pa_s=1.00e-3
    )
    assert all(
        abs(getattr(twenty, k) - getattr(scales, k)) / getattr(scales, k) > 0.03
        for k in ("velocity_m_s", "pressure_Pa", "peclet")
    )


# NUM-27
def test_num09_volumetric_flow_scale_is_the_velocity_through_a_pore_aperture() -> None:
    scales = _scales(1.0)
    assert scales.volumetric_flow_m3_s == pytest.approx(
        scales.velocity_m_s * scales.length_m**2, rel=1e-14
    )


# NUM-18
def test_num09_charge_scales_balance_the_poisson_operator() -> None:
    scales = _scales(1.0)
    expected_volumetric = scales.permittivity * scales.potential_V / scales.length_m**2
    assert scales.charge_density_C_m3 == pytest.approx(expected_volumetric, rel=1e-14)
    assert scales.surface_charge_C_m2 == pytest.approx(
        scales.charge_density_C_m3 * scales.length_m, rel=1e-14
    )

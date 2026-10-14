"""VAL-05's harness, nanopnp.validation.geometry, against closed forms (WP22 Verification)."""

from __future__ import annotations

import json
import math
import re
import subprocess
import sys

import numpy as np
import pytest

from nanopnp.core.paths import profile_file
from nanopnp.geometry.contour import innermost_crossings
from nanopnp.geometry.profile import load_profile
from nanopnp.geometry.region import to_model_frame
from nanopnp.validation.geometry import (
    CONSTRICTION_WINDOW_NM,
    TOLERANCES,
    GeometryComparisonError,
    GeometryToleranceError,
    IsolevelPoint,
    MissingPlaneError,
    attribute_to_construction,
    calpha_centroid_z_nm,
    compare_profiles,
    comparison_planes,
    pqr2grid_polygon,
    pqr2grid_radius,
    register_by_centroid,
    rms_optimal_offset,
    zero_crossing,
)

LOW, HIGH = -1.85, 12.25


def _body(lumen: list[tuple[float, float]], outer_nm: float = 6.0) -> np.ndarray:
    top, bottom = lumen[-1][1], lumen[0][1]
    return np.asarray([*lumen, (outer_nm, top), (outer_nm, bottom)], dtype=np.float64)


def _straight(radius_nm: float = 3.0, low: float = LOW, high: float = HIGH) -> np.ndarray:
    return _body([(radius_nm, low), (radius_nm, high)])


@pytest.fixture(scope="module")
def reference() -> np.ndarray:
    return load_profile(profile_file("clya_reference_profile")).as_array()


def test_val05_the_planes_are_the_282_mid_planes_of_the_reference(reference) -> None:
    planes = comparison_planes(reference)
    assert planes.size == 282
    assert planes[0] == pytest.approx(-1.825)
    assert planes[-1] == pytest.approx(12.225)
    assert np.allclose(np.diff(planes), 0.05)


def test_val05_a_polygon_against_itself_is_zero(reference) -> None:
    comparison = compare_profiles(reference, reference)
    assert comparison.compared_planes == comparison.planes == 282
    assert comparison.uncrossed_planes_nm == []
    for value in (
        comparison.conductance_deviation,
        comparison.conductance_ratio_exact,
        comparison.rms_nm,
        comparison.mean_nm,
        comparison.constriction_difference_nm,
        comparison.outer_mean_nm,
        comparison.outer_rms_nm,
    ):
        assert value == 0.0
    assert comparison.constriction_reference.value_nm == pytest.approx(1.65)
    assert comparison.constriction_reference.z_nm == pytest.approx(-1.225)
    assert comparison.tips_ours_nm == comparison.tips_reference_nm == (LOW, HIGH)
    comparison.check("ensemble")


@pytest.mark.parametrize("scale", [-0.02, 0.01, 0.03])
def test_val05_a_uniform_scale_gives_two_s_and_the_exact_ratio(reference, scale: float) -> None:
    scaled = reference * np.array([1.0 + scale, 1.0])
    comparison = compare_profiles(scaled, reference)
    assert comparison.conductance_deviation == pytest.approx(2.0 * scale, rel=1e-12)
    assert comparison.conductance_ratio_exact == pytest.approx((1.0 + scale) ** 2 - 1.0, rel=1e-12)
    assert comparison.constriction_difference_nm == pytest.approx(1.65 * scale, rel=1e-9)
    assert math.copysign(1.0, comparison.mean_nm) == math.copysign(1.0, scale)
    assert math.copysign(1.0, comparison.outer_mean_nm) == math.copysign(1.0, scale)


def test_val05_each_constriction_is_located_on_its_own_polygon() -> None:
    reference = _body([(3.0, LOW), (1.6, -1.0), (3.0, 0.0), (3.0, HIGH)])
    ours = _body([(3.0, LOW), (3.0, -0.5), (1.7, 0.5), (3.0, 1.5), (3.0, HIGH)])
    comparison = compare_profiles(ours, reference)
    assert comparison.constriction_reference.z_nm == pytest.approx(-0.975)
    assert comparison.constriction_ours.z_nm == pytest.approx(0.475)
    assert comparison.constriction_reference.value_nm == pytest.approx(1.6 + 1.4 * 0.025)
    assert comparison.constriction_ours.value_nm == pytest.approx(1.7 + 1.3 * 0.025)
    assert comparison.constriction_difference_nm == pytest.approx(
        comparison.constriction_ours.value_nm - comparison.constriction_reference.value_nm
    )


def test_val05_the_constriction_is_taken_only_inside_its_window() -> None:
    reference = _straight()
    ours = _body([(3.0, LOW), (3.0, 4.0), (1.0, 5.0), (3.0, 6.0), (3.0, HIGH)])
    comparison = compare_profiles(ours, reference)
    assert comparison.constriction_ours.value_nm == pytest.approx(3.0)
    assert comparison.constriction_ours.z_nm <= CONSTRICTION_WINDOW_NM[1]
    assert comparison.max_abs.z_nm == pytest.approx(4.975)


def test_val05_an_uncrossed_plane_inside_the_tip_band_is_admitted() -> None:
    comparison = compare_profiles(_straight(low=-1.76, high=12.17), _straight())
    assert comparison.uncrossed_planes_nm == pytest.approx([-1.825, -1.775, 12.175, 12.225])
    assert comparison.compared_planes == 278
    assert comparison.tips_ours_nm == (-1.76, 12.17)


# QR-12
@pytest.mark.parametrize(
    ("low", "high", "named"), [(-1.7, HIGH, "-1.7250"), (LOW, 12.1, "12.1250")]
)
def test_val05_an_uncrossed_plane_outside_the_tip_band_fails_naming_z(
    low: float, high: float, named: str
) -> None:
    with pytest.raises(MissingPlaneError, match=rf"the first at z = {named} nm") as caught:
        compare_profiles(_straight(low=low, high=high), _straight())
    assert "tip band" in str(caught.value)
    assert "[-1.8500, 12.2500] nm in the model frame" in str(caught.value)
    # Not strict, for the sweep's record: compared on the planes both cross, if there are any.
    loose = compare_profiles(_straight(low=low, high=high), _straight(), strict=False)
    assert loose.compared_planes == 282 - len(loose.uncrossed_planes_nm)
    assert loose.conductance_deviation == 0.0


def test_val05_the_conductance_tolerance_fires_naming_leg_value_threshold_and_z() -> None:
    reference = _body([(3.0, LOW), (1.7, -1.0), (3.0, 0.5), (3.0, HIGH)])
    comparison = compare_profiles(reference * np.array([1.06, 1.0]), reference)
    for leg, threshold in (("2wcd", "10%"), ("ensemble", "5%")):
        with pytest.raises(GeometryToleranceError) as caught:
            comparison.check(leg)  # type: ignore[arg-type]
        message = str(caught.value)
        assert caught.value.leg == leg
        assert caught.value.quantity == "|ε_G|"
        assert f"({leg} leg)" in message
        assert "12.00%" in message
        assert f"the tolerance {threshold}" in message
        assert "at z = " in message


def test_val05_the_constriction_tolerance_fires_naming_both_minima() -> None:
    reference = _straight()
    ours = _body([(3.0, LOW), (3.0, -0.1), (2.8, 0.0), (3.0, 0.1), (3.0, HIGH)])
    comparison = compare_profiles(ours, reference)
    assert abs(comparison.conductance_deviation) < 0.01
    assert comparison.rms_nm < 0.05
    with pytest.raises(GeometryToleranceError, match=r"\|Δr_c\| is 0\.1500 nm") as caught:
        comparison.check("2wcd")
    message = str(caught.value)
    # The notch is symmetric, so which of its two equal planes is the minimum is the last bit.
    assert re.search(r"ours 2\.8500 nm at z = -?0\.025 nm against the reference's", message)
    assert "the reference's 3.0000 nm" in message
    assert caught.value.quantity == "|Δr_c|"


def test_val05_the_rms_tolerance_fires_naming_the_largest_deviation() -> None:
    lumen = [(3.0, LOW), (3.0, 2.0)]
    lumen += [(3.3 if k % 2 else 2.7, 2.0 + 0.5 * k) for k in range(1, 20)]
    lumen += [(3.0, 12.0), (3.0, HIGH)]
    comparison = compare_profiles(_body(lumen), _straight())
    assert abs(comparison.conductance_deviation) < TOLERANCES["ensemble"].conductance_deviation
    assert comparison.constriction_difference_nm == 0.0
    assert comparison.rms_nm > TOLERANCES["ensemble"].rms_nm
    comparison.check("2wcd")
    with pytest.raises(GeometryToleranceError, match="the rms lumen deviation") as caught:
        comparison.check("ensemble")
    # The mid-planes sit 0.025 nm off each 0.3 nm vertex: 0.3 x (1 - 0.025/0.5).
    assert "the largest |Δ| 0.2850 nm at z = 2.475 nm" in str(caught.value)
    assert "the tolerance 0.1 nm" in str(caught.value)


def test_val05_pqr2grid_radius_check_values() -> None:
    assert pqr2grid_radius(1.65) == pytest.approx(1.5744, abs=1e-4)
    assert pqr2grid_radius(5.66) == pytest.approx(5.4615, abs=1e-4)
    # r_a = 0.96935 r - 0.025 nm, the map's closed form at h = 0.05 nm.
    assert pqr2grid_radius(1.0) == pytest.approx(30.05 / 31 - 0.025, rel=1e-12)
    points = pqr2grid_polygon(np.array([[1.65, 0.3], [5.66, -1.2]]))
    assert points[:, 0] == pytest.approx([pqr2grid_radius(1.65), pqr2grid_radius(5.66)])
    assert points[:, 1] == pytest.approx([0.3, -1.2])


def test_val05_the_attribution_splits_the_offset_into_erratum_and_edit(reference) -> None:
    attribution = attribute_to_construction(reference, reference)
    planes = comparison_planes(reference)
    lumen = innermost_crossings([reference], planes)
    expected = float(np.mean([pqr2grid_radius(r) - r for r in lumen]))
    assert attribution.erratum_lumen_mean_nm == pytest.approx(expected, rel=1e-12)
    assert attribution.hand_edit_lumen_mean_nm == pytest.approx(-expected, rel=1e-12)
    assert attribution.erratum_outer_mean_nm < attribution.erratum_lumen_mean_nm < 0.0
    assert attribution.binned.conductance_deviation < 0.0


def test_val05_the_centroid_registration_returns_the_translation(c12_assembly) -> None:
    positions, names, chains = c12_assembly(0.0)
    resid = [1 + (index // 5) % 8 for index in range(len(names))]
    shift = np.array([0.3, -0.2, 1.7])
    original = calpha_centroid_z_nm(
        positions, name=names, resid=resid, chain=chains, residues=(1, 8)
    )
    moved = register_by_centroid(
        positions + shift, name=names, resid=resid, chain=chains, residues=(1, 8), z_md_nm=original
    )
    assert moved == pytest.approx(1.7, abs=1e-12)
    frames = np.stack([positions, positions + shift])
    both = calpha_centroid_z_nm(frames, name=names, resid=resid, chain=chains, residues=(1, 8))
    assert both == pytest.approx(original + 0.85, abs=1e-12)


def test_val05_the_registration_refuses_a_chain_with_no_selected_atom(c12_assembly) -> None:
    positions, names, chains = c12_assembly(0.0)
    resid = [1 + (index // 5) % 8 for index in range(len(names))]
    with pytest.raises(GeometryComparisonError, match=r"chain\(s\) M over residues 8-292"):
        register_by_centroid(
            positions, name=names, resid=resid, chain=chains, chains=tuple("ABCDEFGHIJKLM")
        )


def test_val05_the_zero_crossing_interpolates_between_passing_levels(reference) -> None:
    base = compare_profiles(reference, reference)
    points = [
        IsolevelPoint(isolevel=0.2, refusal="gate"),
        IsolevelPoint(
            isolevel=0.3, comparison=base.model_copy(update={"conductance_deviation": -0.04})
        ),
        IsolevelPoint(
            isolevel=0.4, comparison=base.model_copy(update={"conductance_deviation": 0.04})
        ),
    ]
    assert zero_crossing(points) == pytest.approx(0.35)
    assert zero_crossing(points[:2]) is None
    at_zero = IsolevelPoint(
        isolevel=0.5, comparison=base.model_copy(update={"conductance_deviation": 0.0})
    )
    assert zero_crossing([*points[:2], at_zero]) == pytest.approx(0.5)
    assert zero_crossing([at_zero]) == pytest.approx(0.5)


def test_val05_no_plane_sits_on_a_reference_tip() -> None:
    reference = _straight(low=-1.85, high=-1.85 + 29.5 * 0.05)
    planes = comparison_planes(reference)
    assert planes.size == 29
    assert planes[-1] < reference[:, 1].max()
    assert compare_profiles(reference, reference).compared_planes == 29


def test_val05_the_registration_refuses_an_empty_selection(c12_assembly) -> None:
    positions, names, chains = c12_assembly(0.0)
    resid = [1 + (index // 5) % 8 for index in range(len(names))]
    with pytest.raises(GeometryComparisonError, match="selects no atom over residues 1-8"):
        calpha_centroid_z_nm(
            positions, name=names, resid=resid, chain=chains, residues=(1, 8), chains=()
        )


def test_val05_the_rms_optimal_offset_recovers_a_known_shift(reference) -> None:
    stage1 = reference + np.array([0.0, 4.5])
    fitted = rms_optimal_offset(stage1, reference, centre_nm=4.47, half_width_nm=0.05)
    assert fitted == pytest.approx(4.5, abs=1e-9)
    for offset in (4.49, 4.51):
        direct = compare_profiles(to_model_frame(stage1, offset), reference).rms_nm
        assert direct > compare_profiles(to_model_frame(stage1, fitted), reference).rms_nm


def test_val05_the_attribution_refuses_a_comparison_on_other_planes(reference) -> None:
    coarse = compare_profiles(reference, reference, spacing_nm=0.1)
    with pytest.raises(GeometryComparisonError, match="do not split one offset"):
        attribute_to_construction(reference, reference, coarse)


def test_lax_comparison_is_refused_by_attribution() -> None:
    ours = _straight(low=-1.7, high=HIGH)
    lax = compare_profiles(ours, _straight(), strict=False)
    assert lax.uncrossed_planes_nm
    with pytest.raises(GeometryComparisonError, match="strict=False") as raised:
        attribute_to_construction(ours, _straight(), lax)
    assert not isinstance(raised.value, MissingPlaneError)


def test_val05_importing_the_harness_imports_no_numpy() -> None:
    script = (
        "import json, sys; import nanopnp.validation.geometry;"
        "print(json.dumps([m for m in ('numpy', 'skimage', 'shapely') if m in sys.modules]))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=True
    )
    assert json.loads(completed.stdout) == []


def test_val05_a_polygon_crossing_no_plane_is_refused_even_when_not_strict() -> None:
    with pytest.raises(MissingPlaneError, match="crosses none of the 282 comparison planes"):
        compare_profiles(_straight(low=13.0, high=14.0), _straight(), strict=False)

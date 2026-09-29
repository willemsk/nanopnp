"""VAL-05's harness, :mod:`nanopnp.validation.geometry`, against closed forms (WP22 Verification).

Every assertion here has an oracle that is not the harness: a polygon against
itself, a uniform radial scale whose first-order and exact conductance changes
are ``2s`` and ``(1 + s)² - 1``, constructed bodies whose minima and missing
planes are placed by hand, ``.knowledge/04`` §1.2's check values for the
``pqr2grid`` erratum, and a translated synthetic C12 whose centroid moves by the
translation.
"""

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
from nanopnp.geometry.region import to_model_frame
from nanopnp.mesh.profile import load_profile
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
"""The delivered table's z extent, which the constructed bodies share."""


def _body(lumen: list[tuple[float, float]], outer_nm: float = 6.0) -> np.ndarray:
    """Return a clockwise body: the lumen bottom to top, then the outer wall top to bottom."""
    top, bottom = lumen[-1][1], lumen[0][1]
    return np.asarray([*lumen, (outer_nm, top), (outer_nm, bottom)], dtype=np.float64)


def _straight(radius_nm: float = 3.0, low: float = LOW, high: float = HIGH) -> np.ndarray:
    """Return a body with a straight lumen at ``radius_nm`` from ``low`` to ``high``."""
    return _body([(radius_nm, low), (radius_nm, high)])


@pytest.fixture(scope="module")
def reference() -> np.ndarray:
    """Return the delivered 185-vertex polygon, already in the model frame."""
    return load_profile(profile_file("clya_reference_profile")).as_array()


def test_val05_the_planes_are_the_282_mid_planes_of_the_reference(reference) -> None:
    """D2: ``z_k = -1.85 + (k + 1/2)·0.05`` nm, k = 0 … 281."""
    planes = comparison_planes(reference)
    assert planes.size == 282
    assert planes[0] == pytest.approx(-1.825)
    assert planes[-1] == pytest.approx(12.225)
    assert np.allclose(np.diff(planes), 0.05)


def test_val05_a_polygon_against_itself_is_zero(reference) -> None:
    """Every deviation vanishes, and the constriction is the table's 1.650 nm at z = -1.225."""
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
    """``r -> (1 + s) r`` gives ``ε_G = 2s`` and the exact series ratio ``(1 + s)² - 1``.

    A radial scale maps each innermost crossing to ``(1 + s)`` times itself, so
    ``Δ/r = s`` on every plane and the first-order sum is ``2s`` exactly.
    """
    scaled = reference * np.array([1.0 + scale, 1.0])
    comparison = compare_profiles(scaled, reference)
    assert comparison.conductance_deviation == pytest.approx(2.0 * scale, rel=1e-12)
    assert comparison.conductance_ratio_exact == pytest.approx((1.0 + scale) ** 2 - 1.0, rel=1e-12)
    assert comparison.constriction_difference_nm == pytest.approx(1.65 * scale, rel=1e-9)
    assert math.copysign(1.0, comparison.mean_nm) == math.copysign(1.0, scale)
    assert math.copysign(1.0, comparison.outer_mean_nm) == math.copysign(1.0, scale)


def test_val05_each_constriction_is_located_on_its_own_polygon() -> None:
    """Δr_c is the difference of two minima at different z, not a difference at one plane."""
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
    """A narrower lumen above z = 1.6 nm is not the constriction."""
    reference = _straight()
    ours = _body([(3.0, LOW), (3.0, 4.0), (1.0, 5.0), (3.0, 6.0), (3.0, HIGH)])
    comparison = compare_profiles(ours, reference)
    assert comparison.constriction_ours.value_nm == pytest.approx(3.0)
    assert comparison.constriction_ours.z_nm <= CONSTRICTION_WINDOW_NM[1]
    assert comparison.max_abs.z_nm == pytest.approx(4.975)


def test_val05_an_uncrossed_plane_inside_the_tip_band_is_admitted() -> None:
    """A rounded end one or two planes short, within 2h of a tip, is recorded and admitted."""
    comparison = compare_profiles(_straight(low=-1.76, high=12.17), _straight())
    assert comparison.uncrossed_planes_nm == pytest.approx([-1.825, -1.775, 12.175, 12.225])
    assert comparison.compared_planes == 278
    assert comparison.tips_ours_nm == (-1.76, 12.17)


@pytest.mark.parametrize(
    ("low", "high", "named"), [(-1.7, HIGH, "-1.7250"), (LOW, 12.1, "12.1250")]
)
def test_val05_an_uncrossed_plane_outside_the_tip_band_fails_naming_z(
    low: float, high: float, named: str
) -> None:
    """QR-12: the first uncrossed plane beyond 2h of a tip is named, with both extents."""
    with pytest.raises(MissingPlaneError, match=rf"the first at z = {named} nm") as caught:
        compare_profiles(_straight(low=low, high=high), _straight())
    assert "tip band" in str(caught.value)
    assert "[-1.8500, 12.2500] nm in the model frame" in str(caught.value)
    # Not strict, for the sweep's record: compared on the planes both cross, if there are any.
    loose = compare_profiles(_straight(low=low, high=high), _straight(), strict=False)
    assert loose.compared_planes == 282 - len(loose.uncrossed_planes_nm)
    assert loose.conductance_deviation == 0.0


def test_val05_the_conductance_tolerance_fires_naming_leg_value_threshold_and_z() -> None:
    """A 6 % wider lumen is ε_G = 12 %: over 2WCD's 10 % and the ensemble's 5 %."""
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
    """A 0.2 nm notch of four planes moves r_c by 0.15 nm, and barely moves ε_G or the rms."""
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
    """A ±0.3 nm zigzag above the window: ε_G and Δr_c stay small, the rms does not."""
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
    """``.knowledge/04`` §1.2: at L = 15 nm, 1.65 nm reads 1.5744 nm and 5.66 nm 5.4615 nm."""
    assert pqr2grid_radius(1.65) == pytest.approx(1.5744, abs=1e-4)
    assert pqr2grid_radius(5.66) == pytest.approx(5.4615, abs=1e-4)
    # r_a = 0.96935 r - 0.025 nm, the map's closed form at h = 0.05 nm.
    assert pqr2grid_radius(1.0) == pytest.approx(30.05 / 31 - 0.025, rel=1e-12)
    points = pqr2grid_polygon(np.array([[1.65, 0.3], [5.66, -1.2]]))
    assert points[:, 0] == pytest.approx([pqr2grid_radius(1.65), pqr2grid_radius(5.66)])
    assert points[:, 1] == pytest.approx([0.3, -1.2])


def test_val05_the_attribution_splits_the_offset_into_erratum_and_edit(reference) -> None:
    """Against itself, the erratum is the map's own mean shift and the edit is its negative.

    The map is affine and increasing in r, so it maps each crossing to itself mapped.
    """
    attribution = attribute_to_construction(reference, reference)
    planes = comparison_planes(reference)
    lumen = innermost_crossings([reference], planes)
    expected = float(np.mean([pqr2grid_radius(r) - r for r in lumen]))
    assert attribution.erratum_lumen_mean_nm == pytest.approx(expected, rel=1e-12)
    assert attribution.hand_edit_lumen_mean_nm == pytest.approx(-expected, rel=1e-12)
    assert attribution.erratum_outer_mean_nm < attribution.erratum_lumen_mean_nm < 0.0
    assert attribution.binned.conductance_deviation < 0.0


def test_val05_the_centroid_registration_returns_the_translation(c12_assembly) -> None:
    """A synthetic C12 translated by ``t``: ``centre_z_nm`` moves by ``t_z`` and nothing else."""
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
    # Frames average: the centroid of two frames is the centroid of their mean.
    frames = np.stack([positions, positions + shift])
    both = calpha_centroid_z_nm(frames, name=names, resid=resid, chain=chains, residues=(1, 8))
    assert both == pytest.approx(original + 0.85, abs=1e-12)


def test_val05_the_registration_refuses_a_chain_with_no_selected_atom(c12_assembly) -> None:
    """A chain the registration names but the structure lacks is refused, and named."""
    positions, names, chains = c12_assembly(0.0)
    resid = [1 + (index // 5) % 8 for index in range(len(names))]
    with pytest.raises(GeometryComparisonError, match=r"chain\(s\) M over residues 8-292"):
        register_by_centroid(
            positions, name=names, resid=resid, chain=chains, chains=tuple("ABCDEFGHIJKLM")
        )


def test_val05_the_zero_crossing_interpolates_between_passing_levels(reference) -> None:
    """ε_G of -4 % at 0.3 and +4 % at 0.4 crosses at 0.35; a refused level is skipped."""
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
    # A level at exactly zero is the crossing, the last passing level included.
    at_zero = IsolevelPoint(
        isolevel=0.5, comparison=base.model_copy(update={"conductance_deviation": 0.0})
    )
    assert zero_crossing([*points[:2], at_zero]) == pytest.approx(0.5)
    assert zero_crossing([at_zero]) == pytest.approx(0.5)


def test_val05_no_plane_sits_on_a_reference_tip() -> None:
    """An extent of 29.5 h rounds to 30 planes, the last on the top tip: it is dropped.

    The crossing test is half-open, so a plane on the top vertex is never crossed,
    and the reference would be refused against itself.
    """
    reference = _straight(low=-1.85, high=-1.85 + 29.5 * 0.05)
    planes = comparison_planes(reference)
    assert planes.size == 29
    assert planes[-1] < reference[:, 1].max()
    assert compare_profiles(reference, reference).compared_planes == 29


def test_val05_the_registration_refuses_an_empty_selection(c12_assembly) -> None:
    """No chain named selects no atom, and is refused rather than averaged to NaN."""
    positions, names, chains = c12_assembly(0.0)
    resid = [1 + (index // 5) % 8 for index in range(len(names))]
    with pytest.raises(GeometryComparisonError, match="selects no atom over residues 1-8"):
        calpha_centroid_z_nm(
            positions, name=names, resid=resid, chain=chains, residues=(1, 8), chains=()
        )


def test_val05_the_rms_optimal_offset_recovers_a_known_shift(reference) -> None:
    """D6's diagnostic: the reference moved up 4.5 nm is best registered at 4.5 nm.

    It agrees with :func:`compare_profiles`' rms at the neighbouring offsets, which
    it must, since it is that rms computed on the lumen alone.
    """
    stage1 = reference + np.array([0.0, 4.5])
    fitted = rms_optimal_offset(stage1, reference, centre_nm=4.47, half_width_nm=0.05)
    assert fitted == pytest.approx(4.5, abs=1e-9)
    for offset in (4.49, 4.51):
        direct = compare_profiles(to_model_frame(stage1, offset), reference).rms_nm
        assert direct > compare_profiles(to_model_frame(stage1, fitted), reference).rms_nm


def test_val05_the_attribution_refuses_a_comparison_on_other_planes(reference) -> None:
    """A supplied comparison on another plane set cannot be split against the binned one."""
    coarse = compare_profiles(reference, reference, spacing_nm=0.1)
    with pytest.raises(GeometryComparisonError, match="do not split one offset"):
        attribute_to_construction(reference, reference, coarse)


def test_val05_importing_the_harness_imports_no_numpy() -> None:
    """``CLAUDE.md``: NumPy, and stage 4's scikit-image and shapely, load on first use only."""
    script = (
        "import json, sys; import nanopnp.validation.geometry;"
        "print(json.dumps([m for m in ('numpy', 'skimage', 'shapely') if m in sys.modules]))"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=True
    )
    assert json.loads(completed.stdout) == []


def test_val05_a_polygon_crossing_no_plane_is_refused_even_when_not_strict() -> None:
    """A body wholly above the reference has nothing to compare, and says so."""
    with pytest.raises(MissingPlaneError, match="crosses none of the 282 comparison planes"):
        compare_profiles(_straight(low=13.0, high=14.0), _straight(), strict=False)

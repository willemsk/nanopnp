"""VER-52: stage 5, the membrane junction on any profile (FR-09, QR-12)."""

from __future__ import annotations

import math
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import yaml

from nanopnp.core.paths import profile_file
from nanopnp.geometry import region as region_module
from nanopnp.geometry.profile import (
    PROFILE_SCHEMA,
    PoreProfile,
    ProfileProvenance,
    load_profile,
    min_feature_size,
    min_vertex_spacing,
    signed_area,
    write_profile,
)
from nanopnp.geometry.region import (
    JUNCTION_CLEARANCE_NM,
    KEY_CONSTANTS,
    RegionGateError,
    RegionStage,
    best_chord,
    build_region,
    check_junction,
    derive_region,
    lumen_interval,
    measure,
    profile_digest,
    read_region,
    to_model_frame,
    write_region,
)
from nanopnp.io.artefact import CASE_SCHEMA, StageInputs
from nanopnp.io.case import (
    CaseValidationError,
    Membrane,
    Reservoir,
)
from nanopnp.io.store import Store
from nanopnp.mesh.reference import ReferenceGeometry
from nanopnp.pipeline.case import (
    loads_case,
    resolve,
)
from nanopnp.pipeline.run import selected_stages

FIXTURE = "clya_reference_profile"

MEMBRANE = Membrane()
RESERVOIR = Reservoir()


def _profile(points: list[tuple[float, float]], name: str = "synthetic") -> PoreProfile:
    array = np.asarray(points, dtype=np.float64)
    return PoreProfile.model_validate(
        {
            "schema": PROFILE_SCHEMA,
            "name": name,
            "provenance": ProfileProvenance(
                source="test",
                citation="tests/tier1/test_region.py",
                sha256="0" * 64,
                vertex_count=len(points),
                min_vertex_spacing_nm=min_vertex_spacing(array),
                min_feature_size_nm=min_feature_size(array),
                signed_area_nm2=signed_area(array),
            ).model_dump(),
            "vertices": points,
        }
    )


def _parallelogram(slope: float, width_nm: float = 1.0) -> PoreProfile:
    return _profile(
        [
            (2.0, -3.0),
            (2.0 + width_nm, -3.0),
            (2.0 + width_nm + 6.0 * slope, 3.0),
            (2.0 + 6.0 * slope, 3.0),
        ]
    )


HOOK = [
    (2.0, -3.0),
    (3.0, -3.0),
    (3.0, 1.8),
    (4.5, 1.8),
    (4.5, 1.0),
    (5.0, 1.0),
    (5.0, 2.4),
    (2.0, 2.4),
]

BRIDGE = [
    (2.0, -3.0),
    (3.0, -3.0),
    (3.0, -1.0),
    (5.0, -1.0),
    (5.0, 3.0),
    (4.5, 3.0),
    (4.5, -0.5),
    (3.0, -0.5),
    (3.0, 3.0),
    (2.0, 3.0),
]


@pytest.fixture(scope="module")
def fixture_profile() -> PoreProfile:
    return load_profile(FIXTURE)


@pytest.fixture(scope="module")
def fixture_region(fixture_profile: PoreProfile) -> region_module.RegionRecord:
    return derive_region(fixture_profile, MEMBRANE, RESERVOIR)


def test_ver52_a_parallelogram_s_best_chord_is_its_mid_line() -> None:
    slope = 0.5
    points = _parallelogram(slope).as_array()
    half = MEMBRANE.thickness_nm / 2.0
    trans = lumen_interval(points, -half, centre_z_nm=0.0)
    cis = lumen_interval(points, half, centre_z_nm=0.0)
    r_trans, r_cis, clearance = best_chord(points, trans, cis, half)
    assert r_trans == pytest.approx(2.5 + slope * (3.0 - half), abs=1e-12)
    assert r_cis == pytest.approx(2.5 + slope * (3.0 + half), abs=1e-12)
    assert clearance == pytest.approx(0.5 / math.sqrt(1.0 + slope**2), abs=1e-12)


def test_ver52_the_fixture_s_chord_and_the_drawn_one_give_one_region(
    fixture_profile: PoreProfile, fixture_region: region_module.RegionRecord
) -> None:
    membrane = fixture_region.membrane
    assert membrane.inner_trans_nm == pytest.approx(1.981845238095238, abs=1e-12)
    assert membrane.inner_cis_nm == pytest.approx(3.47, abs=1e-12)
    assert membrane.clearance_nm == pytest.approx(0.23645835468143087, abs=1e-9)
    assert fixture_region.junction_nm == pytest.approx({"trans": 2.7523809523809524, "cis": 4.88})

    from shapely.geometry import LineString, Polygon

    poly = Polygon(fixture_profile.vertices)
    mid_trans = 0.5 * (1.725 + 2.7523809523809524)
    mid_cis = 0.5 * (2.96 + 4.88)
    chord = LineString([(mid_trans, -1.4), (mid_cis, 1.4)])
    crossings = sorted(
        [(p.x, p.y) for p in chord.intersection(poly.exterior).geoms], key=lambda pt: pt[1]
    )
    assert crossings[0] == pytest.approx((3.070, -0.016), abs=1e-3)
    assert crossings[1] == pytest.approx((3.235, 0.260), abs=1e-3)

    drawn = ReferenceGeometry(profile=fixture_profile)
    areas, counts = measure(build_region(drawn.record()))
    assert counts == fixture_region.edge_counts
    assert counts == {
        "axis": 3,
        "cis": 1,
        "interface": 35,
        "membrane": 2,
        "membrane_outer": 2,
        "trans": 1,
        "wall": 151,
    }
    for name, area in areas.items():
        assert fixture_region.face_areas_nm2[name] == pytest.approx(area, rel=1e-10)


def test_ver52_a_translated_profile_registered_by_its_shift_is_the_same_region(
    fixture_profile: PoreProfile, fixture_region: region_module.RegionRecord
) -> None:
    shift = 7.25
    moved = _profile(
        [(r, z + shift) for r, z in fixture_profile.vertices],
        name="moved",
    )
    record = derive_region(moved, Membrane(centre_z_nm=shift), RESERVOIR)
    assert np.allclose(record.points(), fixture_region.points(), atol=1e-12)
    assert record.membrane.inner_trans_nm == pytest.approx(
        fixture_region.membrane.inner_trans_nm, abs=1e-12
    )
    assert record.membrane.inner_cis_nm == pytest.approx(
        fixture_region.membrane.inner_cis_nm, abs=1e-12
    )
    assert record.edge_counts == fixture_region.edge_counts
    assert record.membrane.centre_z_nm == shift


@pytest.mark.parametrize(
    ("points", "domain", "centroid"),
    [(HOOK, "electrolyte", "(3.7500, 1.6000)"), (BRIDGE, "membrane", "(3.7500, 0.4500)")],
    ids=["hook", "bridge"],
)
def test_ver52_a_body_cut_four_times_is_refused_naming_its_pocket(
    points: list[tuple[float, float]], domain: str, centroid: str
) -> None:
    profile = _profile(points, name=domain)
    half = MEMBRANE.thickness_nm / 2.0
    assert lumen_interval(profile.as_array(), half, centre_z_nm=0.0) == (2.0, 3.0)
    _, r_cis, _ = best_chord(profile.as_array(), (2.0, 3.0), (2.0, 3.0), half)
    assert 2.0 < r_cis < 3.0
    with pytest.raises(RegionGateError) as caught:
        derive_region(profile, MEMBRANE, RESERVOIR)
    message = _gate_message(caught)
    assert f"{domain} domain topology" in message
    assert "2 faces" in message
    assert f"centroid {centroid} nm" in message


def _gate_message(error: pytest.ExceptionInfo[RegionGateError]) -> str:
    raised = error.value
    for part in (raised.criterion, raised.measured, raised.threshold, raised.where):
        assert part and part in str(raised)
    return str(raised)


def test_ver52_a_bilayer_that_misses_the_profile_names_the_extent_and_centre() -> None:
    with pytest.raises(RegionGateError) as caught:
        derive_region(_parallelogram(0.0), Membrane(centre_z_nm=-5.0), RESERVOIR)
    message = _gate_message(caught)
    assert "bilayer plane crossings" in message
    assert "z = [2.0000, 8.0000] nm" in message
    assert "centre_z_nm = -5 nm" in message


def test_ver52_a_body_too_thin_for_a_chord_names_the_clearance() -> None:
    with pytest.raises(RegionGateError) as caught:
        derive_region(_parallelogram(0.0, width_nm=0.015), MEMBRANE, RESERVOIR)
    message = _gate_message(caught)
    assert "chord clearance" in message
    assert f"at least {JUNCTION_CLEARANCE_NM:g} nm" in message
    assert "(r, z) = (2.0075, -1.4000)" in message


def test_ver52_a_profile_outside_the_reservoir_names_the_vertex() -> None:
    with pytest.raises(RegionGateError) as caught:
        derive_region(_parallelogram(0.0), MEMBRANE, Reservoir(radius_nm=3.5))
    message = _gate_message(caught)
    assert "profile inside the reservoir" in message
    assert "(r, z) = (3.0000, -3.0000)" in message


def test_ver52_a_junction_off_r2_names_the_offset(
    fixture_region: region_module.RegionRecord,
) -> None:
    shape = build_region(fixture_region)
    check_junction(fixture_region, shape)
    edited = fixture_region.model_copy(update={"junction_nm": {"trans": 2.7, "cis": 4.88}})
    with pytest.raises(RegionGateError) as caught:
        check_junction(edited, shape)
    message = _gate_message(caught)
    assert "membrane junction" in message
    assert "trans plane" in message


def test_ver52_the_record_round_trips_and_rebuilds(
    fixture_region: region_module.RegionRecord, tmp_path: Path
) -> None:
    path = write_region(fixture_region, tmp_path / "region.yaml")
    read = read_region(path)
    assert read == fixture_region
    areas, counts = measure(build_region(read))
    assert counts == fixture_region.edge_counts
    for name, area in areas.items():
        assert area == pytest.approx(fixture_region.face_areas_nm2[name], rel=1e-12)

    other = yaml.safe_load(path.read_text(encoding="utf-8"))
    other["schema"] = "nanopnp/region/v0"
    wrong = tmp_path / "wrong.yaml"
    wrong.write_text(yaml.safe_dump(other), encoding="utf-8")
    with pytest.raises(ValueError, match=r"expected schema 'nanopnp/region/v0.5'"):
        read_region(wrong)


PROFILE_CASE = (
    f"schema: {CASE_SCHEMA}\n"
    """name: profile-case
inputs:
  profile: {{path: {path}}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 1.0
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics: {{model: pnp-ns, solid_permittivities: {{protein: 20.0, membrane: 3.2}}}}
{extra}"""
)


def profile_case(path: Path, extra: str = "") -> str:
    return PROFILE_CASE.format(path=path, extra=extra)


def test_ver52_a_supplied_profile_is_read_by_stage_5(tmp_path: Path) -> None:
    resolved = resolve(loads_case(profile_case(profile_file(FIXTURE))))
    assert resolved.profile is not None
    assert resolved.generates_mesh
    assert resolved.membrane == Membrane()
    assert selected_stages(resolved, None) == (
        "case",
        "region",
        "mesh",
        "materials",
        "solve",
        "qoi",
        "report",
    )


def _key(text: str) -> str:
    return RegionStage().key(StageInputs(resolved=resolve(loads_case(text)))).hash


def test_ver52_the_key_is_stable_across_processes_and_moves_with_each_input(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture = profile_file(FIXTURE)
    base = _key(profile_case(fixture))

    code = (
        "import sys\n"
        "from nanopnp.geometry.region import RegionStage\n"
        "from nanopnp.io.artefact import StageInputs\n"
        "from nanopnp.pipeline.case import loads_case, resolve\n"
        "print(RegionStage().key(StageInputs(resolved=resolve(loads_case(sys.stdin.read())))).hash)\n"
    )
    fresh = subprocess.run(
        [sys.executable, "-c", code],
        input=profile_case(fixture),
        capture_output=True,
        text=True,
        check=True,
    )
    assert fresh.stdout.strip() == base

    moved = {
        _key(profile_case(fixture, "geometry: {membrane: {thickness_nm: 3.0}}\n")),
        _key(profile_case(fixture, "geometry: {membrane: {centre_z_nm: 0.5}}\n")),
        _key(profile_case(fixture, "geometry: {reservoir: {radius_nm: 200.0}}\n")),
    }
    for name in KEY_CONSTANTS:
        with monkeypatch.context() as patch:
            patch.setitem(region_module.KEY_CONSTANTS, name, "moved")
            moved.add(_key(profile_case(fixture)))
    assert base not in moved
    assert len(moved) == 3 + len(KEY_CONSTANTS)

    # A reformatted copy is the same input; an edited vertex is a new one.
    profile = load_profile(fixture)
    copy = write_profile(profile, tmp_path / "copy.yaml")
    assert _key(profile_case(copy)) == base
    edited = profile.model_copy(
        update={
            "vertices": [
                (profile.vertices[0][0] + 1e-3, profile.vertices[0][1]),
                *profile.vertices[1:],
            ]
        }
    )
    assert profile_digest(edited) != profile_digest(profile)


def test_ver52_the_stage_writes_its_record_and_a_hand_edit_is_recorded(tmp_path: Path) -> None:
    case = loads_case(profile_case(profile_file(FIXTURE)))
    stage = RegionStage(workspace=tmp_path / "work")
    assert stage.describe().number == 5
    store = Store(tmp_path / "store")
    key = stage.key(StageInputs(resolved=resolve(case)))
    artefact = store.get_or_compute(key, lambda: stage.run(StageInputs(resolved=resolve(case))))
    assert artefact.hash == key.hash
    record = read_region(artefact.payload["region"])
    assert record.membrane.clearance_nm == pytest.approx(0.2364583547, abs=1e-9)
    summary = artefact.summary
    assert summary["junction_nm"] == {"cis": 4.88, "trans": pytest.approx(2.7523809523809524)}

    path = artefact.payload["region"]
    path.write_text(path.read_text(encoding="utf-8").replace("250.0", "240.0"), encoding="utf-8")
    reloaded = store.get(key.schema, key.hash)
    assert reloaded is not None and reloaded.hand_substituted


def test_ver52_to_model_frame_shifts_z_only() -> None:
    points = np.array([[1.0, 2.0], [3.0, -4.0]])
    assert np.array_equal(to_model_frame(points, 1.5), np.array([[1.0, 0.5], [3.0, -5.5]]))
    assert np.array_equal(points, np.array([[1.0, 2.0], [3.0, -4.0]]))


@pytest.mark.parametrize(
    ("points", "junction"),
    [
        # A bilayer plane can lie along a flat edge of the body; the half-open crossing rule
        # must count the far end of that edge, or the junction gate refuses a valid region.
        pytest.param(
            [(2.0, -3.0), (2.0, 5.0), (3.0, 5.0), (3.0, 1.4), (5.0, 1.4), (5.0, -3.0)],
            {"trans": 5.0, "cis": 5.0},
            id="cis-wide-lower",
        ),
        pytest.param(
            [(2.0, -3.0), (2.0, 5.0), (6.0, 5.0), (6.0, 1.4), (3.0, 1.4), (3.0, -3.0)],
            {"trans": 3.0, "cis": 6.0},
            id="cis-cap-flush",
        ),
        pytest.param(
            [(2.0, -3.0), (2.0, 5.0), (3.0, 5.0), (3.0, -1.4), (5.0, -1.4), (5.0, -3.0)],
            {"trans": 5.0, "cis": 3.0},
            id="trans-wide-foot",
        ),
        pytest.param(
            [(2.0, -3.0), (2.0, 5.0), (5.0, 5.0), (5.0, -1.4), (3.0, -1.4), (3.0, -3.0)],
            {"trans": 5.0, "cis": 5.0},
            id="trans-body-above",
        ),
    ],
)
def test_ver52_an_edge_lying_on_a_bilayer_plane_extends_the_interval_along_it(
    points: list[tuple[float, float]], junction: dict[str, float]
) -> None:
    reservoir = Reservoir(radius_nm=30.0)
    assert derive_region(_profile(points), MEMBRANE, reservoir).junction_nm == junction


@pytest.mark.parametrize(
    ("inputs", "extra", "fragment"),
    [
        ("{artefact: " + "a" * 64 + "}", "", "inputs.profile: artefact:"),
        ("{path: p.yaml, groups: {a: wall}}", "", "inputs.profile.groups"),
        ("{path: p.yaml, format: csv}", "", "inputs.profile.format is 'csv'"),
        ("{path: p.yaml}", "geometry: {density: {grid_spacing_nm: 0.03}}\n", "geometry.density"),
        ("{path: p.yaml}", "geometry: {contour: {isolevel: 0.3}}\n", "geometry.contour"),
    ],
)
def test_ver52_a_supplied_profile_s_refusals_name_the_key(
    inputs: str, extra: str, fragment: str
) -> None:
    text = profile_case(Path("p.yaml"), extra).replace("{path: p.yaml}", inputs, 1)
    with pytest.raises(CaseValidationError, match=re.escape(fragment)):
        resolve(loads_case(text))


def test_ver52_structure_beside_a_supplied_profile_is_refused_naming_both(tmp_path: Path) -> None:
    text = profile_case(
        Path("p.yaml"),
        "structure:\n  source: {path: s.pdb}\n  symmetry: {point_group: C12}\n",
    )
    with pytest.raises(
        CaseValidationError, match=r"structure: section and supplies inputs\.profile"
    ):
        resolve(loads_case(text))

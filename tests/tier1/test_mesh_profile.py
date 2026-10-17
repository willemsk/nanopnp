"""Section 5.2.1: the pore profile fixture, and that it is still the delivered table."""

from pathlib import Path

import numpy as np
import pytest
import yaml

from nanopnp.core.paths import GEOMETRY_DIR, profile_file
from nanopnp.geometry.profile import (
    LOCAL_EDGES,
    PROFILE_SCHEMA,
    PoreProfile,
    ProfileProvenance,
    load_profile,
    min_feature_size,
    min_vertex_spacing,
    profile_from_csv,
    signed_area,
)

CSV = GEOMETRY_DIR / "clya_as_radial_geometry.csv"
"""The delivered table, kept verbatim; nothing but the derivation reads it."""

REFERENCE = "clya_reference_profile"
"""The shipped fixture derived from it."""

MEASURED_TOL = 1e-9
"""Tolerance on the measured properties of the delivered table, in nm or nm^2."""


def unit_square(**overrides: object) -> PoreProfile:
    vertices = overrides.pop("vertices", [(1.0, 0.0), (2.0, 0.0), (2.0, 1.0), (1.0, 1.0)])
    points = np.asarray(vertices, dtype=float)
    # A loop too short to measure is one the polygon gate rejects before the
    # provenance is looked at, so the measurements are left at zero there.
    measurable = len(points) >= 3
    provenance = {
        "source": "nominal",
        "citation": "a stand-in, not the reference geometry",
        "sha256": "0" * 64,
        "vertex_count": len(points),
        "min_vertex_spacing_nm": min_vertex_spacing(points) if measurable else 0.0,
        "min_feature_size_nm": min_feature_size(points) if measurable else 0.0,
        "signed_area_nm2": signed_area(points) if measurable else 0.0,
    }
    provenance.update(overrides.pop("provenance", {}))  # type: ignore[arg-type]
    fields: dict[str, object] = {
        "schema": PROFILE_SCHEMA,
        "name": "unit_square",
        "provenance": ProfileProvenance(**provenance),  # type: ignore[arg-type]
        "vertices": [(float(r), float(z)) for r, z in points],
    }
    fields.update(overrides)
    return PoreProfile(**fields)  # type: ignore[arg-type]


def test_the_shipped_fixture_is_the_delivered_table_re_derived() -> None:
    fixture = load_profile(REFERENCE)
    derived = profile_from_csv(
        CSV,
        name=fixture.name,
        source=fixture.provenance.source,
        citation=fixture.provenance.citation,
        description=fixture.description,
    )
    assert derived == fixture


def test_the_delivered_table_has_the_published_properties() -> None:
    from shapely.geometry import LineString, Polygon

    fixture = load_profile(REFERENCE)
    points = fixture.as_array()
    assert len(points) == 185
    assert fixture.extent_r_nm == pytest.approx((1.65, 5.66), abs=MEASURED_TOL)
    assert fixture.extent_z_nm == pytest.approx((-1.85, 12.25), abs=MEASURED_TOL)
    assert fixture.is_clockwise
    assert signed_area(points) == pytest.approx(-26.4939, abs=1e-4)
    assert min_vertex_spacing(points) == pytest.approx(0.0361, abs=1e-4)
    assert min_feature_size(points) == pytest.approx(0.0806, abs=1e-4)

    h = 0.05
    on_r = np.isclose(points[:, 0] % h, 0, atol=1e-5) | np.isclose(points[:, 0] % h, h, atol=1e-5)
    on_z = np.isclose(points[:, 1] % h, 0, atol=1e-5) | np.isclose(points[:, 1] % h, h, atol=1e-5)
    assert np.mean(on_r | on_z) == pytest.approx(0.58, abs=0.01)
    assert np.mean(on_r & on_z) == pytest.approx(0.32, abs=0.01)

    edges = np.linalg.norm(np.roll(points, -1, axis=0) - points, axis=1)
    assert np.sum(edges < 0.05) == 10
    assert np.sum(edges < 0.1) == 45

    poly = Polygon(points)
    cut_trans = LineString([(0, -1.4), (10, -1.4)]).intersection(poly.exterior)
    cut_cis = LineString([(0, 1.4), (10, 1.4)]).intersection(poly.exterior)
    pts_trans = sorted(
        [p.x for p in (cut_trans.geoms if hasattr(cut_trans, "geoms") else [cut_trans])]
    )
    pts_cis = sorted([p.x for p in (cut_cis.geoms if hasattr(cut_cis, "geoms") else [cut_cis])])
    assert pts_trans[-1] == pytest.approx(2.7524, abs=1e-4)
    assert pts_cis[-1] == pytest.approx(4.88, abs=1e-4)



def test_the_reference_fixture_is_accepted_for_tier_three_work() -> None:
    fixture = load_profile(REFERENCE)
    assert fixture.is_reference
    fixture.require_reference("a VAL-01 comparison")


def test_signed_area_is_negative_for_a_clockwise_loop() -> None:
    counter_clockwise = np.array([[1.0, 0.0], [2.0, 0.0], [2.0, 1.0], [1.0, 1.0]])
    assert signed_area(counter_clockwise) == pytest.approx(1.0)
    assert signed_area(counter_clockwise[::-1]) == pytest.approx(-1.0)


def test_the_local_feature_size_skips_the_vertexs_own_neighbourhood() -> None:
    arc = np.array(
        [[2.0 + np.cos(angle), np.sin(angle)] for angle in np.linspace(0.0, 2.0 * np.pi, 60)[:-1]]
    )
    assert LOCAL_EDGES == 2
    assert min_feature_size(arc, local_edges=1) == pytest.approx(min_vertex_spacing(arc), rel=1e-6)
    assert min_feature_size(arc) > min_vertex_spacing(arc)


def test_the_local_feature_size_sees_a_self_approach() -> None:
    hairpin = np.array(
        [
            [1.0, 0.0],
            [3.0, 0.0],
            [3.0, 1.0],
            [1.0, 1.0],
            [1.0, 0.55],
            [2.5, 0.55],
            [2.5, 0.45],
            [1.0, 0.45],
        ]
    )
    assert min_feature_size(hairpin) == pytest.approx(0.1)


def test_a_profile_whose_provenance_describes_another_polygon_is_refused() -> None:
    with pytest.raises(ValueError, match="does not describe this polygon"):
        unit_square(provenance={"min_vertex_spacing_nm": 0.5})
    with pytest.raises(ValueError, match="vertex_count is 4 but the table carries 5"):
        unit_square(
            vertices=[(1.0, 0.0), (2.0, 0.0), (2.0, 1.0), (1.5, 1.5), (1.0, 1.0)],
            provenance={"vertex_count": 4},
        )


def test_a_repeated_closing_vertex_is_named_as_such() -> None:
    with pytest.raises(ValueError, match="closing edge is implied"):
        unit_square(vertices=[(1.0, 0.0), (2.0, 0.0), (2.0, 1.0), (1.0, 0.0)])


def test_a_self_intersecting_loop_is_refused() -> None:
    with pytest.raises(ValueError, match="the loop is not simple: edge"):
        unit_square(vertices=[(1.0, 0.0), (2.0, 1.0), (2.0, 0.0), (1.0, 1.0)])


# CON-04
def test_a_negative_radius_is_refused() -> None:
    with pytest.raises(ValueError, match="radius must be non-negative"):
        unit_square(vertices=[(-1.0, 0.0), (2.0, 0.0), (2.0, 1.0), (1.0, 1.0)])


# The helper measures the provenance off the same vertices, and NumPy warns
# doing arithmetic on the NaN it is handed; the refusal is what is under test.
@pytest.mark.filterwarnings("ignore::RuntimeWarning")
@pytest.mark.parametrize("bad", [float("nan"), float("inf")])
def test_a_vertex_that_is_not_finite_is_refused_naming_it(bad: float) -> None:
    with pytest.raises(ValueError, match=r"vertex 2 is .* finite number"):
        unit_square(vertices=[(1.0, 0.0), (2.0, 0.0), (bad, 1.0), (1.0, 1.0)])


def test_too_few_vertices_for_a_loop_is_refused() -> None:
    with pytest.raises(ValueError, match="at least three vertices"):
        unit_square(vertices=[(1.0, 0.0), (2.0, 0.0)])


def test_an_unknown_key_in_the_fixture_is_named(tmp_path: Path) -> None:
    raw = yaml.safe_load(profile_file(REFERENCE).read_text(encoding="utf-8"))
    raw["vertex_spacing"] = 0.05
    path = tmp_path / "extra.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="vertex_spacing"):
        load_profile(path)


def test_a_fixture_declaring_another_schema_names_the_file_and_the_schema(tmp_path: Path) -> None:
    raw = yaml.safe_load(profile_file(REFERENCE).read_text(encoding="utf-8"))
    raw["schema"] = "nanopnp/profile/v99"
    path = tmp_path / "future.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(ValueError, match=r"expected schema 'nanopnp/profile/v0\.5'"):
        load_profile(path)


def test_a_missing_fixture_names_the_directory_searched() -> None:
    with pytest.raises(FileNotFoundError, match="no geometry profile 'mrpa'"):
        load_profile("mrpa")


def test_a_stand_in_profile_is_refused_for_tier_three_work() -> None:
    stand_in = unit_square()
    assert not stand_in.is_reference
    with pytest.raises(ValueError, match="needs the reference geometry"):
        stand_in.require_reference("a VAL-01 comparison")


def test_a_path_is_read_as_a_path_whatever_its_suffix(tmp_path: Path) -> None:
    bare = tmp_path / "pore"
    bare.write_text(profile_file(REFERENCE).read_text(encoding="utf-8"), encoding="utf-8")
    assert load_profile(bare) == load_profile(REFERENCE)
    with pytest.raises(FileNotFoundError):
        load_profile(tmp_path / "missing")

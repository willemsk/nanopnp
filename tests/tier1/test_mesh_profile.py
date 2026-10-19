"""Section 5.2.1: the pore profile fixture, and that it is still the delivered table."""

import numpy as np
import pytest

from nanopnp.core.paths import GEOMETRY_DIR
from nanopnp.geometry.profile import (
    LOCAL_EDGES,
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

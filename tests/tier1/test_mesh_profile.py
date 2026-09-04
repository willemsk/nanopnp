"""Section 5.2.1: the pore profile fixture, and that it still is the delivered table.

The fixture is derived data. What can go wrong is drift — the YAML edited and the
CSV not, or the other way round — and a provenance block that describes a polygon
other than the one beside it, which would justify the wrong element size with a
number nobody re-measured. Both are checked here by re-deriving rather than by
comparing a stored digest, so the test fails with the quantity that moved.
"""

from pathlib import Path

import numpy as np
import pytest
import yaml

from nanopnp.core.paths import GEOMETRY_DIR, profile_file
from nanopnp.mesh.profile import (
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
    """Return a valid minimal profile, with fields replaced for the failure cases."""
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


# --- the shipped fixture ---------------------------------------------------


def test_the_shipped_fixture_is_the_delivered_table_re_derived() -> None:
    """`profile_from_csv` on the CSV in the tree reproduces the YAML beside it.

    Field for field, vertices included: the fixture is derived data and this is
    the only thing keeping it derived. The provenance that cannot be measured —
    the source and the citation — is taken from the fixture, so what is compared
    is everything the table decides.
    """
    fixture = load_profile(REFERENCE)
    derived = profile_from_csv(
        CSV,
        name=fixture.name,
        source=fixture.provenance.source,
        citation=fixture.provenance.citation,
        description=fixture.description,
    )
    assert derived == fixture


def test_the_fixture_records_the_sha256_of_the_table_it_came_from() -> None:
    """The digest is over the delivered bytes, CRLF line endings included."""
    import hashlib

    fixture = load_profile(REFERENCE)
    assert fixture.provenance.sha256 == hashlib.sha256(CSV.read_bytes()).hexdigest()
    assert fixture.provenance.sha256.startswith("d0c2008140dc43d4")


def test_the_delivered_table_has_the_published_properties() -> None:
    """Section 5.2.1's measured row, to 1e-9: extent, count, topology, area.

    The extents are section 2.2's published ones to the digit, which is the
    check that this table is the geometry the reference model was solved on.
    """
    fixture = load_profile(REFERENCE)
    points = fixture.as_array()
    assert len(points) == 185
    assert fixture.extent_r_nm == pytest.approx((1.65, 5.66), abs=MEASURED_TOL)
    assert fixture.extent_z_nm == pytest.approx((-1.85, 12.25), abs=MEASURED_TOL)
    assert fixture.is_clockwise
    assert signed_area(points) == pytest.approx(-26.4939, abs=1e-4)
    assert min_vertex_spacing(points) == pytest.approx(0.0361, abs=1e-4)
    assert min_feature_size(points) == pytest.approx(0.0806, abs=1e-4)


def test_the_reference_fixture_is_accepted_for_tier_three_work() -> None:
    """`author-supplied` is a reference source: the delivered table is the geometry."""
    fixture = load_profile(REFERENCE)
    assert fixture.is_reference
    fixture.require_reference("a VAL-01 comparison")


def test_the_fixture_fails_two_conditioning_criteria_and_is_shipped_anyway() -> None:
    """Section 5.2.1 NOTE: the gate is on contours FR-08 produces, not on a fixture.

    Pinned because it is the surprising half of the amendment. At the reference
    wall size of 0.05 nm this polygon's spacing and feature size are below the
    thresholds, and it is still what the reference mesh was built from. A later
    change that started gating the fixture on them would fail here rather than
    quietly refuse to load the reference geometry.
    """
    wall_size_nm = 0.05
    points = load_profile(REFERENCE).as_array()
    assert min_vertex_spacing(points) < wall_size_nm
    assert min_feature_size(points) < 2.0 * wall_size_nm


# --- the measures ----------------------------------------------------------


def test_signed_area_is_negative_for_a_clockwise_loop() -> None:
    """The sign is the orientation, and the closing edge is implied."""
    counter_clockwise = np.array([[1.0, 0.0], [2.0, 0.0], [2.0, 1.0], [1.0, 1.0]])
    assert signed_area(counter_clockwise) == pytest.approx(1.0)
    assert signed_area(counter_clockwise[::-1]) == pytest.approx(-1.0)


def test_the_local_feature_size_skips_the_vertexs_own_neighbourhood() -> None:
    """With only the incident edges excluded the measure is the shortest edge.

    That is why :data:`LOCAL_EDGES` is 2. On a densely sampled convex arc every
    vertex is within one edge length of its neighbour's edge, so a feature size
    that excluded only the incident edges would report sampling density — 0.0361
    nm on the reference polygon, its shortest edge — and never see a genuine
    self-approach.
    """
    arc = np.array(
        [[2.0 + np.cos(angle), np.sin(angle)] for angle in np.linspace(0.0, 2.0 * np.pi, 60)[:-1]]
    )
    assert LOCAL_EDGES == 2
    assert min_feature_size(arc, local_edges=1) == pytest.approx(min_vertex_spacing(arc), rel=1e-6)
    assert min_feature_size(arc) > min_vertex_spacing(arc)


def test_the_local_feature_size_sees_a_self_approach() -> None:
    """A hairpin closing to 0.1 nm is measured at 0.1 nm, not at its edge length."""
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


# --- the gate --------------------------------------------------------------


def test_a_profile_whose_provenance_describes_another_polygon_is_refused() -> None:
    """Recorded measurements are re-checked against the vertices at load."""
    with pytest.raises(ValueError, match="does not describe this polygon"):
        unit_square(provenance={"min_vertex_spacing_nm": 0.5})
    with pytest.raises(ValueError, match="vertex_count is 4 but the table carries 5"):
        unit_square(
            vertices=[(1.0, 0.0), (2.0, 0.0), (2.0, 1.0), (1.5, 1.5), (1.0, 1.0)],
            provenance={"vertex_count": 4},
        )


def test_a_repeated_closing_vertex_is_named_as_such() -> None:
    """The closing edge is implied by the format; repeating it is the usual slip."""
    with pytest.raises(ValueError, match="closing edge is implied"):
        unit_square(vertices=[(1.0, 0.0), (2.0, 0.0), (2.0, 1.0), (1.0, 0.0)])


def test_a_self_intersecting_loop_is_refused() -> None:
    """A bow tie is not a pore boundary, and the message names both edges."""
    with pytest.raises(ValueError, match="the loop is not simple: edge"):
        unit_square(vertices=[(1.0, 0.0), (2.0, 1.0), (2.0, 0.0), (1.0, 1.0)])


def test_a_negative_radius_is_refused() -> None:
    """CON-04: there is no geometry at r < 0 in the half-plane."""
    with pytest.raises(ValueError, match="radius must be non-negative"):
        unit_square(vertices=[(-1.0, 0.0), (2.0, 0.0), (2.0, 1.0), (1.0, 1.0)])


def test_too_few_vertices_for_a_loop_is_refused() -> None:
    with pytest.raises(ValueError, match="at least three vertices"):
        unit_square(vertices=[(1.0, 0.0), (2.0, 0.0)])


def test_an_unknown_key_in_the_fixture_is_named(tmp_path: Path) -> None:
    """IF-03's house standard: the offending key at load, not a KeyError later."""
    raw = yaml.safe_load(profile_file(REFERENCE).read_text(encoding="utf-8"))
    raw["vertex_spacing"] = 0.05
    path = tmp_path / "extra.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="vertex_spacing"):
        load_profile(path)


def test_a_fixture_declaring_another_schema_names_the_file_and_the_schema(tmp_path: Path) -> None:
    """Checked before the fields, so a future schema is one message and not a wall."""
    raw = yaml.safe_load(profile_file(REFERENCE).read_text(encoding="utf-8"))
    raw["schema"] = "nanopnp/profile/v99"
    path = tmp_path / "future.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="expected schema 'nanopnp/profile/v1'"):
        load_profile(path)


def test_a_missing_fixture_names_the_directory_searched() -> None:
    with pytest.raises(FileNotFoundError, match="no geometry profile 'mrpa'"):
        load_profile("mrpa")


def test_a_stand_in_profile_is_refused_for_tier_three_work() -> None:
    """A Tier-3 agreement measured against a stand-in geometry means nothing."""
    stand_in = unit_square()
    assert not stand_in.is_reference
    with pytest.raises(ValueError, match="needs the reference geometry"):
        stand_in.require_reference("a VAL-01 comparison")

"""VER-28: the assembled ClyA reference region, and its membrane-to-pore junction.

The failure this file exists to catch is the one a coordinate check cannot see.
The membrane's drawn inner corners, ``(2, -1.4)`` and ``(3.5, +1.4)``, lie 0.275
and 0.540 nm *inside* the pore body on the delivered geometry, so a gate written
against them asserts numbers the reference geometry never produces. What the
assembly must actually get right is that the bilayer meets the pore on the pore's
own outer surface, over one node chain rather than two coincident ones - the
second of which gives conforming coordinates and a non-conformal mesh, and would
leave the potential free to jump across the seam with nothing raising.
"""

from __future__ import annotations

from collections import Counter

import numpy as np
import pytest

from nanopnp.mesh.adapter import from_ngsolve
from nanopnp.mesh.ingest import BOUNDARY_VOCABULARY, FLUID_MATERIALS
from nanopnp.mesh.primitives import TOL_NM
from nanopnp.mesh.profile import PoreProfile
from nanopnp.mesh.quality import QUALITY_FLOOR, check_quality
from nanopnp.mesh.reference import (
    ReferenceGeometry,
    plane_crossings,
)

REFERENCE_MIN_QUALITY = 0.6378
"""Minimum element quality of the reference COMSOL mesh (section 5.2.2)."""

REFERENCE_MEAN_QUALITY = 0.9765
"""Average element quality of the same mesh."""

JUNCTION_TOL_NM = 1e-9
"""Fragmentation tolerance on the cut radii; OCC's gluing tolerance is far below."""


@pytest.fixture(scope="module")
def geometry() -> ReferenceGeometry:
    """Return the shipped ClyA fixture, assembled."""
    return ReferenceGeometry.from_fixture()


@pytest.fixture(scope="module")
def meshed(geometry: ReferenceGeometry):
    """Return the reference region meshed at the section 5.2.2 size fields."""
    return from_ngsolve(geometry.generate(check_quality=False))


def _inside_polygon(profile: PoreProfile, points: np.ndarray) -> np.ndarray:
    """Return a boolean mask of which ``(r, z)`` points lie inside the polygon.

    Ray casting along ``+r``, with the half-open interval test that counts a
    vertex on the ray once. Written here rather than imported so that the test
    does not share a routine with the code it is checking.
    """
    starts = profile.as_array()
    ends = np.roll(starts, -1, axis=0)
    inside = np.zeros(len(points), dtype=bool)
    for (r0, z0), (r1, z1) in zip(starts, ends, strict=True):
        if z0 == z1:
            continue
        straddles = (points[:, 1] >= min(z0, z1)) & (points[:, 1] < max(z0, z1))
        fraction = (points[:, 1] - z0) / (z1 - z0)
        crossing_r = r0 + fraction * (r1 - r0)
        inside ^= straddles & (crossing_r > points[:, 0])
    return inside


def _centroids(data, material: str) -> np.ndarray:
    """Return the centroids of every element carrying ``material``."""
    index = data.materials.index(material)
    selected = data.triangles[data.triangle_material == index]
    return data.vertices[selected].mean(axis=1)


def test_ver28_the_region_has_three_domains_and_carries_the_vocabulary(
    geometry: ReferenceGeometry, meshed
) -> None:
    """Three domains, seven boundary names, and no bilayer inside the fluid.

    Three and not four is the non-obvious half. The cap's underside is
    re-entrant, so the membrane fills a cleft beneath it; that cleft opens
    downward past the cap edge at ``z ~ -0.7`` and is continuous with the rest of
    the bilayer. An assembly that fragments it off has a bug, and the domain
    count is the cheapest test for it.
    """
    assert set(meshed.materials) == {"electrolyte", "membrane", "protein"}
    assert set(meshed.boundaries) <= set(BOUNDARY_VOCABULARY)
    assert set(meshed.boundaries) == {
        "axis",
        "cis",
        "interface",
        "membrane",
        "membrane_outer",
        "trans",
        "wall",
    }
    assert "membrane" not in FLUID_MATERIALS

    # No bilayer element anywhere the electrolyte belongs, and none inside the
    # pore body: this is what the slanted inner edge buys, and a vertical edge at
    # r = 2 would put membrane inside the lumen for every z > 0.
    membrane = _centroids(meshed, "membrane")
    assert np.all(np.abs(membrane[:, 1]) <= geometry.half_thickness_nm + TOL_NM)
    assert not np.any(_inside_polygon(geometry.profile, membrane))
    assert not np.any(_inside_polygon(geometry.profile, _centroids(meshed, "electrolyte")))
    assert np.all(_inside_polygon(geometry.profile, _centroids(meshed, "protein")))


def test_ver28_the_junction_is_conformal_and_lands_on_the_pore_outer_surface(
    geometry: ReferenceGeometry, meshed
) -> None:
    """The bilayer meets the pore where the polygon puts it, over one node chain.

    ``r_out(-1.4) = 2.7524`` and ``r_out(+1.4) = 4.88`` are read from the fixture
    by :func:`plane_crossings` rather than written down, so the assertion stays
    true of whatever profile is supplied; the drawn corners at 2.0 and 3.5 appear
    nowhere in it, and asserting them instead is the mistake this test replaces.

    Conformality is then asserted on the mesh, not the coordinates: two
    coincident chains agree to the last digit and put two nodes at every seam
    point. A compound of the same three faces meshes that way and a glue does
    not [tested].
    """
    half = geometry.half_thickness_nm
    report = geometry.junction_report()

    lower = plane_crossings(geometry.profile, -half)
    upper = plane_crossings(geometry.profile, half)
    assert lower == pytest.approx((1.725, 2.7523809523809524))
    assert upper == pytest.approx((2.96, 4.88))
    assert report.expected_trans_nm == pytest.approx(max(lower))
    assert report.expected_cis_nm == pytest.approx(max(upper))
    assert report.worst_offset_nm < JUNCTION_TOL_NM
    assert report.assembled_trans_nm != pytest.approx(geometry.membrane_inner_trans_nm)
    assert report.assembled_cis_nm != pytest.approx(geometry.membrane_inner_cis_nm)

    # One node chain, not two: no two vertices of the mesh coincide.
    vertices = meshed.vertices
    unique = np.unique(np.round(vertices, 9), axis=0)
    assert len(unique) == len(vertices)

    # membrane_outer is the arc segment, not a straight edge at r = 250: its
    # mid-height radius exceeds its ends by the sagitta of a 1.4 nm half-chord.
    radius = geometry.reservoir_radius_nm
    sagitta = radius - float(np.sqrt(radius**2 - half**2))
    outer = meshed.vertices[
        np.unique(meshed.edges[meshed.edge_group == meshed.boundaries.index("membrane_outer")])
    ]
    assert outer[:, 0].max() == pytest.approx(radius, abs=1e-9)
    assert outer[:, 0].min() == pytest.approx(radius - sagitta, abs=1e-6)
    assert sagitta == pytest.approx(3.92e-3, rel=1e-2)


def test_ver10_the_reference_mesh_is_in_the_published_quality_band(meshed) -> None:
    """The assembled region meshes into the band section 5.2.2 records.

    Measured here, netgen at the section 5.2.2 size fields, grading 0.2,
    ``optsteps2d=5``: 44,316 triangles, minimum SICN 0.6559, mean 0.9870,
    minimum gamma 0.6157, mean 0.9852, no inverted elements. The reference
    COMSOL mesh is 120,917 triangles at minimum quality 0.6378 and average
    0.9765 — a third of the elements in the same quality band, which is the
    claim worth recording; the element count is not asserted against COMSOL's
    because the two meshers' size fields are not the same knobs.
    """
    report = check_quality(meshed)
    assert report.element_count == 44316
    assert report.min_sicn == pytest.approx(0.6559, abs=5e-4)
    assert report.mean_sicn == pytest.approx(0.9870, abs=5e-4)
    assert report.min_gamma == pytest.approx(0.6157, abs=5e-4)
    assert not report.inverted
    assert report.min_sicn > QUALITY_FLOOR
    assert report.min_sicn >= REFERENCE_MIN_QUALITY
    assert report.mean_sicn >= REFERENCE_MEAN_QUALITY


def test_ver28_the_assembled_topology_matches_the_section_5_2_1_count(
    geometry: ReferenceGeometry,
) -> None:
    """The region's vertex and edge counts, against the count section 5.2.1 derives.

    Section 5.2.1 assembles the delivered 185-vertex table to 190 vertices and
    192 boundaries: the polygon, one plane cut at ``z = -1.4`` (the table already
    carries a vertex on the cis plane), the membrane's two outer corners on the
    arc, the arc's two endpoints on the axis, and six closing edges. This
    assembly adds three of each to that, both deliberate and both recorded where
    they are made: two from splitting the axis at the pore's axial extent, which
    is the only way section 5.2.2's 0.075 nm axis-in-pore size field can be
    applied at all, and one from the seam OCC places on a closed circle at
    ``(250, 0)``, which halves ``membrane_outer``.

    Counted on unique geometry rather than on the shape's own lists: OCC reports
    an edge once per face it bounds, so a glued three-face region lists 383 edges
    and 766 vertices for the 195 and 193 that exist.
    """
    shape = geometry.shape()
    vertices = {(round(v.p[0], 9), round(v.p[1], 9)) for v in shape.vertices}
    edges = {
        (
            frozenset(
                {
                    (round(e.start[0], 9), round(e.start[1], 9)),
                    (round(e.end[0], 9), round(e.end[1], 9)),
                }
            ),
            e.name,
        )
        for e in shape.edges
    }
    assert len(vertices) == 193
    assert len(edges) == 195

    named = Counter(name for _, name in edges)
    assert named["axis"] == 3
    assert named["membrane_outer"] == 2
    assert named["membrane"] == 2
    assert named["cis"] == named["trans"] == 1
    # The polygon's own 185 edges plus the trans-plane cut, split between the
    # part the bilayer covers and the part the electrolyte sees.
    assert named["wall"] + named["interface"] == 186

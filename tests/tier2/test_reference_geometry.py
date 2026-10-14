"""VER-28: the assembled ClyA reference region, and its membrane-to-pore junction."""

from __future__ import annotations

from collections import Counter

import numpy as np
import pytest

from nanopnp.geometry.profile import PoreProfile
from nanopnp.geometry.tolerance import TOL_NM
from nanopnp.mesh.adapter import from_ngsolve
from nanopnp.mesh.ingest import BOUNDARY_VOCABULARY, FLUID_MATERIALS
from nanopnp.mesh.quality import QUALITY_FLOOR, check_quality
from nanopnp.mesh.reference import (
    ReferenceGeometry,
    plane_crossings,
)

# Reference COMSOL mesh: SPECIFICATION.md section 5.2.2.
REFERENCE_MIN_QUALITY = 0.6378

# Reference COMSOL mesh: SPECIFICATION.md section 5.2.2.
REFERENCE_MEAN_QUALITY = 0.9765

JUNCTION_TOL_NM = 1e-9


@pytest.fixture(scope="module")
def geometry() -> ReferenceGeometry:
    return ReferenceGeometry.from_fixture()


@pytest.fixture(scope="module")
def meshed(clya_reference_mesh):  # type: ignore[no-untyped-def]
    return from_ngsolve(clya_reference_mesh())


def _inside_polygon(profile: PoreProfile, points: np.ndarray) -> np.ndarray:
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
    index = data.materials.index(material)
    selected = data.triangles[data.triangle_material == index]
    return data.vertices[selected].mean(axis=1)


def test_ver28_the_region_has_three_domains_and_carries_the_vocabulary(
    geometry: ReferenceGeometry, meshed
) -> None:
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

    # The slanted inner edge keeps the bilayer out of the lumen; a vertical edge at r = 2
    # would put membrane inside it for every z > 0.
    membrane = _centroids(meshed, "membrane")
    assert np.all(np.abs(membrane[:, 1]) <= geometry.half_thickness_nm + TOL_NM)
    assert not np.any(_inside_polygon(geometry.profile, membrane))
    assert not np.any(_inside_polygon(geometry.profile, _centroids(meshed, "electrolyte")))
    assert np.all(_inside_polygon(geometry.profile, _centroids(meshed, "protein")))


def test_ver28_the_junction_is_conformal_and_lands_on_the_pore_outer_surface(
    geometry: ReferenceGeometry, meshed
) -> None:
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

    radius = geometry.reservoir_radius_nm
    sagitta = radius - float(np.sqrt(radius**2 - half**2))
    outer = meshed.vertices[
        np.unique(meshed.edges[meshed.edge_group == meshed.boundaries.index("membrane_outer")])
    ]
    assert outer[:, 0].max() == pytest.approx(radius, abs=1e-9)
    assert outer[:, 0].min() == pytest.approx(radius - sagitta, abs=1e-6)
    assert sagitta == pytest.approx(3.92e-3, rel=1e-2)


def test_ver10_the_reference_mesh_is_in_the_published_quality_band(meshed) -> None:
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
    assert named["wall"] + named["interface"] == 186

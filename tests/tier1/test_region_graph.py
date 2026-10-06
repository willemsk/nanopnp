"""VER-54: the region graph the Gmsh backend meshes is stage 5's region, exactly (WP23 D2, QR-12).

The graph is read from the glued, named netgen shape and needs no ``gmsh``, so
this file runs on every leg. Its oracles are the record's own measurements, made
by OCC when stage 5 assembled the region: the edge-name counts, and each face's
area, against which the graph's closed-form area (Green's theorem over segments
and arcs about the origin) is checked. A graph that dropped, split or bent an
edge fails one of them.
"""

from __future__ import annotations

import math
import subprocess
import sys

import numpy as np
import pytest

from nanopnp.geometry.profile import (
    PROFILE_SCHEMA,
    PoreProfile,
    ProfileProvenance,
    load_profile,
    min_feature_size,
    min_vertex_spacing,
    signed_area,
)
from nanopnp.geometry.region import (
    GRAPH_AREA_RTOL,
    RegionGateError,
    RegionGraph,
    RegionRecord,
    build_region,
    derive_region,
    region_graph,
)
from nanopnp.io.case import MembraneSpec, ReservoirSpec

PARALLELOGRAM = [(2.0, -3.0), (3.0, -3.0), (6.0, 3.0), (5.0, 3.0)]
"""The slanted body of ``test_mesh_generate.py``, counter-clockwise."""


def _profile(points: list[tuple[float, float]]) -> PoreProfile:
    """Return a validated profile over ``points``."""
    array = np.asarray(points, dtype=np.float64)
    return PoreProfile.model_validate(
        {
            "schema": PROFILE_SCHEMA,
            "name": "graph",
            "provenance": ProfileProvenance(
                source="test",
                citation="tests/tier1/test_region_graph.py",
                sha256="0" * 64,
                vertex_count=len(points),
                min_vertex_spacing_nm=min_vertex_spacing(array),
                min_feature_size_nm=min_feature_size(array),
                signed_area_nm2=signed_area(array),
            ).model_dump(),
            "vertices": points,
        }
    )


@pytest.fixture(scope="module")
def fixture_region() -> RegionRecord:
    """Return the shipped ClyA profile assembled at the default membrane and reservoir."""
    return derive_region(load_profile("clya_reference_profile"), MembraneSpec(), ReservoirSpec())


@pytest.fixture(scope="module", params=["counter-clockwise", "clockwise"])
def parallelogram_region(request: pytest.FixtureRequest) -> RegionRecord:
    """Return the parallelogram in a 30 nm reservoir, its profile in either orientation."""
    points = PARALLELOGRAM if request.param == "counter-clockwise" else PARALLELOGRAM[::-1]
    return derive_region(_profile(points), MembraneSpec(), ReservoirSpec(radius_nm=30.0))


def _check_graph(record: RegionRecord, graph: RegionGraph) -> None:
    """Assert the D2 contract on a graph: counts, closed CCW loops, arcs on the circle."""
    assert graph.edge_counts() == dict(sorted(record.edge_counts.items()))
    assert set(graph.faces) == set(record.face_areas_nm2)
    for name, loop in graph.faces.items():
        walked = [graph.walk(signed) for signed in loop]
        for (_, end), (start, _) in zip(walked, walked[1:] + walked[:1], strict=True):
            assert end == start, f"{name}: the loop breaks at vertex {end}"
        area = graph.area(name)
        assert area > 0.0, f"{name} runs clockwise"
        assert area == pytest.approx(record.face_areas_nm2[name], rel=GRAPH_AREA_RTOL)
    radius = record.reservoir_radius_nm
    arcs = [index for index, edge in enumerate(graph.edges) if edge.kind == "arc"]
    assert {graph.edges[i].name for i in arcs} == {"cis", "trans", "membrane_outer"}
    for index in arcs:
        edge = graph.edges[index]
        for vertex in (edge.start, edge.end):
            assert math.hypot(*graph.vertices[vertex]) == pytest.approx(radius, rel=1e-9)
        assert graph.length(index) < math.pi * radius  # a circle-arc primitive's limit
    # Every seam is one edge shared by index: the two faces that meet on it both list it.
    listed = [s if s >= 0 else ~s for loop in graph.faces.values() for s in loop]
    shared = {name: 0 for name in ("interface", "wall", "membrane")}
    for index in listed:
        if graph.edges[index].name in shared:
            shared[graph.edges[index].name] += 1
    for name, count in shared.items():
        assert count == 2 * record.edge_counts[name], name


def test_ver54_the_fixture_s_graph_is_its_region(fixture_region: RegionRecord) -> None:
    """D2 on the reference fixture: 193 vertices, 195 edges, every profile vertex kept."""
    shape = build_region(fixture_region)
    graph = region_graph(shape, fixture_region)
    _check_graph(fixture_region, graph)
    assert len(graph.vertices) == 193
    assert len(graph.edges) == 195
    # The coordinates are the shape's own, bit for bit, and the profile's every vertex.
    assert set(graph.vertices) == {(float(v.p[0]), float(v.p[1])) for v in shape.vertices}
    assert set(map(tuple, fixture_region.points().tolist())) <= set(graph.vertices)


def test_ver54_a_parallelogram_s_graph_is_its_region(parallelogram_region: RegionRecord) -> None:
    """D2 on either orientation of the profile: the loops come out counter-clockwise."""
    graph = region_graph(build_region(parallelogram_region), parallelogram_region)
    _check_graph(parallelogram_region, graph)
    assert set(map(tuple, parallelogram_region.points().tolist())) <= set(graph.vertices)


def test_ver54_an_arc_off_the_reservoir_circle_is_refused_naming_its_midpoint(
    fixture_region: RegionRecord,
) -> None:
    """QR-12: an edge neither straight nor the reservoir's arc is named, with its midpoint."""
    shape = build_region(fixture_region)
    elsewhere = fixture_region.model_copy(update={"reservoir_radius_nm": 251.0})
    with pytest.raises(RegionGateError) as caught:
        region_graph(shape, elsewhere)
    message = str(caught.value)
    assert "edge geometry" in message
    assert "neither straight nor the shorter arc" in message
    assert "at (r, z) = (" in message
    assert "r^2 + z^2 = 251^2" in message


@pytest.mark.parametrize(
    ("update", "fragment"),
    [
        ({"edge_counts": {"wall": 1}}, "graph edge counts"),
        ({"face_areas_nm2": {"electrolyte": 1.0, "membrane": 1.0, "protein": 1.0}}, "face area"),
    ],
)
def test_ver54_a_graph_that_is_not_the_record_s_region_is_refused(
    fixture_region: RegionRecord, update: dict[str, object], fragment: str
) -> None:
    """QR-12: the graph's counts and areas are checked against what stage 5 measured."""
    shape = build_region(fixture_region)
    with pytest.raises(RegionGateError, match=fragment):
        region_graph(shape, fixture_region.model_copy(update=update))


GRAPH_IN_A_FRESH_PROCESS = """
import sys
from nanopnp.geometry.region import build_region, derive_region, region_graph
from nanopnp.io.case import MembraneSpec, ReservoirSpec
from nanopnp.geometry.profile import load_profile

record = derive_region(load_profile("clya_reference_profile"), MembraneSpec(), ReservoirSpec())
region_graph(build_region(record), record)
print("gmsh" in sys.modules)
"""


def test_ver54_the_graph_needs_no_gmsh() -> None:
    """CON-10: reading the graph imports netgen and NumPy only."""
    completed = subprocess.run(
        [sys.executable, "-c", GRAPH_IN_A_FRESH_PROCESS], capture_output=True, text=True, check=True
    )
    assert completed.stdout.strip().splitlines()[-1] == "False"

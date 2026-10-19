"""IF-06: the mesh seam, one in-memory mesh and every route in and out of it."""

import re
import subprocess
import sys
from pathlib import Path

import ngsolve as ngs
import numpy as np
import pytest

from nanopnp.mesh.adapter import (
    MeshData,
    MeshFormatError,
    from_ngsolve,
    read,
    read_physical_names,
    to_ngsolve,
    write_msh41,
)
from nanopnp.mesh.primitives import SlabGeometry


def square_mesh(
    *,
    materials: tuple[str, str] = ("electrolyte", "membrane"),
    boundaries: tuple[str, str, str, str] = ("axis", "wall", "cis", "trans"),
) -> MeshData:
    vertices = np.array([[i / 2.0, j / 2.0] for j in range(3) for i in range(3)], dtype=float)
    triangles = np.array(
        [
            row
            for j in range(2)
            for i in range(2)
            for row in (
                [3 * j + i, 3 * j + i + 1, 3 * j + i + 4],
                [3 * j + i, 3 * j + i + 4, 3 * j + i + 3],
            )
        ]
    )
    return MeshData(
        vertices=vertices,
        triangles=triangles,
        triangle_material=np.array([0, 0, 0, 0, 1, 1, 1, 1]),
        materials=materials,
        edges=np.array([[0, 3], [3, 6], [2, 5], [5, 8], [0, 1], [1, 2], [6, 7], [7, 8]]),
        edge_group=np.array([0, 0, 1, 1, 2, 2, 3, 3]),
        boundaries=boundaries,
    )


SQUARE = square_mesh()
"""The reference mesh, built once; :class:`MeshData` is frozen."""


def replacing(**fields: object) -> MeshData:
    arguments: dict[str, object] = {
        "vertices": SQUARE.vertices,
        "triangles": SQUARE.triangles,
        "triangle_material": SQUARE.triangle_material,
        "materials": SQUARE.materials,
        "edges": SQUARE.edges,
        "edge_group": SQUARE.edge_group,
        "boundaries": SQUARE.boundaries,
    }
    arguments.update(fields)
    return MeshData(**arguments)  # type: ignore[arg-type]


def assert_same_mesh(left: MeshData, right: MeshData) -> None:
    a, b = left.canonical(), right.canonical()
    np.testing.assert_allclose(a.vertices, b.vertices, rtol=0.0, atol=0.0)
    np.testing.assert_array_equal(a.triangles, b.triangles)
    np.testing.assert_array_equal(a.triangle_material, b.triangle_material)
    np.testing.assert_array_equal(a.edges, b.edges)
    np.testing.assert_array_equal(a.edge_group, b.edge_group)
    assert a.materials == b.materials
    assert a.boundaries == b.boundaries
    assert a.content_hash == b.content_hash


def test_if06_meshdata_normalises_the_dtypes_the_hash_is_taken_over() -> None:
    narrow = replacing(
        vertices=SQUARE.vertices.astype(np.float32),
        triangles=SQUARE.triangles.astype(np.int32),
        triangle_material=SQUARE.triangle_material.astype(np.int32),
        edges=SQUARE.edges.astype(np.int32),
        edge_group=SQUARE.edge_group.astype(np.int32),
    )
    assert narrow.triangles.dtype == np.int64
    assert narrow.content_hash == SQUARE.content_hash


def test_if06_material_and_edge_selection_by_name() -> None:
    assert SQUARE.material_of("membrane").tolist() == [False] * 4 + [True] * 4
    np.testing.assert_array_equal(SQUARE.edges_of("cis"), np.array([[0, 1], [1, 2]]))
    with pytest.raises(KeyError, match="no boundary group 'lateral'"):
        SQUARE.edges_of("lateral")


def test_if06_renamed_merges_the_groups_that_map_together() -> None:
    merged = SQUARE.renamed(boundaries={"cis": "wall", "trans": "wall"})
    assert merged.boundaries == ("axis", "wall")
    assert merged.edge_group.tolist() == [0, 0, 1, 1, 1, 1, 1, 1]
    assert len(merged.edges_of("wall")) == 6


def test_if06_the_content_hash_ignores_the_order_the_arrays_arrive_in() -> None:
    order = np.array([3, 0, 8, 4, 2, 1, 7, 6, 5])
    renumber = np.empty(9, dtype=np.int64)
    renumber[order] = np.arange(9)
    shuffled = MeshData(
        vertices=SQUARE.vertices[order],
        triangles=renumber[SQUARE.triangles][::-1],
        triangle_material=SQUARE.triangle_material[::-1],
        materials=SQUARE.materials,
        edges=renumber[SQUARE.edges][:, ::-1],
        edge_group=SQUARE.edge_group,
        boundaries=SQUARE.boundaries,
    )
    assert shuffled.content_hash == SQUARE.content_hash


def test_if06_the_content_hash_changes_when_one_edge_moves_group() -> None:
    moved = replacing(edge_group=np.array([0, 0, 1, 1, 2, 2, 2, 3]))
    assert moved.content_hash != SQUARE.content_hash


def test_if06_the_content_hash_changes_when_a_group_is_renamed() -> None:
    assert replacing(materials=("electrolyte", "protein")).content_hash != SQUARE.content_hash


def test_if06_the_content_hash_is_stable_across_processes(tmp_path: Path) -> None:
    path = tmp_path / "square.msh"
    write_msh41(SQUARE, path)
    script = (
        "import sys;"
        "from pathlib import Path;"
        "from nanopnp.mesh.adapter import read;"
        "sys.stdout.write(read(Path(sys.argv[1])).content_hash)"
    )
    # meshio.read writes a bare newline to stdout, so the digest is stripped.
    digests = {
        subprocess.run(
            [sys.executable, "-c", script, str(path)],
            check=True,
            capture_output=True,
            text=True,
            env={"PYTHONHASHSEED": seed, "PATH": ""},
        ).stdout.strip()
        for seed in ("1", "12345")
    }
    assert digests == {SQUARE.content_hash}


@pytest.mark.parametrize("binary", [False, True])
def test_if06_a_tagged_mesh_survives_an_msh41_round_trip(tmp_path: Path, binary: bool) -> None:
    path = write_msh41(SQUARE, tmp_path / f"square-{binary}.msh", binary=binary)
    back = read(path)
    assert back.boundaries == SQUARE.boundaries
    assert back.materials == SQUARE.materials
    assert_same_mesh(SQUARE, back)


def test_if06_ascii_msh41_is_bit_exact_on_float64(tmp_path: Path) -> None:
    awkward = SQUARE.vertices.copy()
    awkward[4] = [np.pi / 7.0, np.sqrt(2.0) / 3.0]
    exact = replacing(vertices=awkward)
    back = read(write_msh41(exact, tmp_path / "exact.msh"))
    assert back.canonical().vertices.tobytes() == exact.canonical().vertices.tobytes()


def test_if06_every_group_gets_its_own_physical_name(tmp_path: Path) -> None:
    path = write_msh41(SQUARE, tmp_path / "square.msh")
    assert sorted(read_physical_names(path).items()) == [
        ((1, 3), "axis"),
        ((1, 4), "wall"),
        ((1, 5), "cis"),
        ((1, 6), "trans"),
        ((2, 1), "electrolyte"),
        ((2, 2), "membrane"),
    ]


def test_if06_a_name_used_as_a_domain_and_as_a_boundary_survives(tmp_path: Path) -> None:
    mesh = square_mesh(materials=("cis", "trans"))
    back = read(write_msh41(mesh, tmp_path / "collide.msh"))
    assert back.materials == ("cis", "trans")
    assert back.boundaries == ("axis", "wall", "cis", "trans")
    assert_same_mesh(mesh, back)


def test_if06_the_hash_ignores_a_file_meshio_rewrote(tmp_path: Path) -> None:
    first = write_msh41(SQUARE, tmp_path / "first.msh")
    second = write_msh41(read(first), tmp_path / "second.msh", binary=True)
    assert first.read_bytes() != second.read_bytes()
    assert read(second).content_hash == SQUARE.content_hash


# CON-04
def test_if06_a_mesh_off_the_half_plane_is_refused(tmp_path: Path) -> None:
    path = write_msh41(SQUARE, tmp_path / "flat.msh")
    head, marker, rest = path.read_text().partition("$EndNodes")
    lifted = re.sub(
        r"^(\S+) (\S+) 0\.0+e\+00$", r"\1 \2 5.0e+00", head, count=1, flags=re.MULTILINE
    )
    assert lifted != head, "no node coordinate line was found to lift"
    path.write_text(lifted + marker + rest)
    with pytest.raises(MeshFormatError, match="three-dimensional"):
        read(path)


@pytest.mark.parametrize("kind", ["quad", "triangle6"])
def test_if06_a_cell_that_is_not_a_straight_sided_triangle_is_refused_not_dropped(
    tmp_path: Path, kind: str
) -> None:
    import meshio

    points = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [2.0, 0.0], [2.0, 1.0]])
    extra = (
        ("quad", np.array([[1, 4, 5, 2]]))
        if kind == "quad"
        else ("triangle6", np.array([[1, 4, 5, 0, 2, 3]]))
    )
    mesh = meshio.Mesh(
        points,
        [
            ("vertex", np.array([[0]])),
            ("line", np.array([[0, 1], [1, 4]])),
            ("triangle", np.array([[0, 1, 2], [0, 2, 3]])),
            extra,
        ],
        cell_data={
            "gmsh:physical": [np.array([3]), np.array([1, 1]), np.array([2, 2]), np.array([2])],
            "gmsh:geometrical": [np.array([1]), np.array([1, 1]), np.array([1, 1]), np.array([1])],
        },
    )
    path = tmp_path / f"{kind}.msh"
    # MSH 2.2: meshio's 4.1 writer wants entity tags for a mixed mesh, and the
    # reader takes either version through the same cell loop.
    meshio.write(str(path), mesh, file_format="gmsh22", binary=False)
    with pytest.raises(MeshFormatError, match=rf"1 '{kind}' cells"):
        read(path)


def test_if06_to_ngsolve_then_from_ngsolve_is_the_identity_on_the_tag_maps() -> None:
    mesh = square_mesh()
    ngmesh = to_ngsolve(mesh)
    assert set(ngmesh.GetMaterials()) == set(mesh.materials)
    assert set(ngmesh.GetBoundaries()) == set(mesh.boundaries)
    assert_same_mesh(mesh, from_ngsolve(ngmesh))


def test_if06_a_generated_mesh_round_trips_through_the_file_and_back() -> None:
    mesh = from_ngsolve(SlabGeometry(width_nm=2.0, height_nm=1.0).generate(maxh_nm=0.5))
    assert mesh.materials == ("electrolyte",)
    assert set(mesh.boundaries) == {"wall", "bulk", "lateral"}
    assert_same_mesh(mesh, from_ngsolve(to_ngsolve(mesh)))


def test_if06_a_generated_mesh_survives_the_archival_format(tmp_path: Path) -> None:
    mesh = from_ngsolve(SlabGeometry(width_nm=2.0, height_nm=1.0).generate(maxh_nm=0.5))
    back = read(write_msh41(mesh, tmp_path / "slab.msh"))
    assert_same_mesh(mesh, back)
    assert back.element_count == mesh.element_count


def test_a_reversed_boundary_segment_does_not_flip_the_normal() -> None:
    vertices = np.array([[0, 0], [1, 0], [1, 1], [0, 1], [1, 0.5]], dtype=float)
    triangles = np.array([[0, 1, 4], [0, 4, 2], [0, 2, 3]])
    reversed_segment = np.array([[0, 1], [4, 1], [4, 2], [2, 3], [3, 0]])
    data = MeshData(
        vertices,
        triangles,
        np.zeros(3, dtype=np.int64),
        ("electrolyte",),
        reversed_segment,
        np.array([0, 1, 1, 0, 0]),
        ("other", "right"),
    )
    mesh = to_ngsolve(data)
    normal = ngs.specialcf.normal(2)
    right = mesh.Boundaries("right")
    lower = ngs.Integrate(normal[0] * ngs.IfPos(0.5 - ngs.y, 1, 0), mesh, definedon=right)
    upper = ngs.Integrate(normal[0] * ngs.IfPos(ngs.y - 0.5, 1, 0), mesh, definedon=right)
    assert lower == pytest.approx(0.5)
    assert upper == pytest.approx(0.5)

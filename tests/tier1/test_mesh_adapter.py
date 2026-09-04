"""IF-06: the mesh seam — one in-memory mesh, and every route in and out of it.

The round-trip tests are not bookkeeping. Each of the three meshio behaviours
the adapter works around (its docstring names them) is silent: the write reports
success and the mesh comes back subtly wrong — three boundary groups collapsed
into one, a name replaced by ``group-3``, a node order permuted under a hash that
was taken in file order. A test that only checked "the file exists and reads"
would pass through all three, so these compare the tag maps element by element
and compare the content hash across every transformation that must not change it.
"""

import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

from nanopnp.mesh.adapter import (
    MeshData,
    MeshDataError,
    MeshFormatError,
    detect_format,
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
    """Return the unit square as a two-by-two grid of cells, split into triangles.

    Nine vertices, eight triangles, two domains stacked in z and four named
    boundaries. Small enough to compare by eye, and large enough to carry the
    two things that break a writer: several groups of the same element type, and
    boundary groups that share every one of their nodes with a neighbour.
    """
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
    """Return :data:`SQUARE` with the named fields replaced, validation and all."""
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
    """Assert that two meshes agree on geometry and on both tag maps.

    Compared in canonical form, because a round trip is allowed to permute the
    nodes and is not allowed to change which group an element is in.
    """
    a, b = left.canonical(), right.canonical()
    np.testing.assert_allclose(a.vertices, b.vertices, rtol=0.0, atol=0.0)
    np.testing.assert_array_equal(a.triangles, b.triangles)
    np.testing.assert_array_equal(a.triangle_material, b.triangle_material)
    np.testing.assert_array_equal(a.edges, b.edges)
    np.testing.assert_array_equal(a.edge_group, b.edge_group)
    assert a.materials == b.materials
    assert a.boundaries == b.boundaries
    assert a.content_hash == b.content_hash


# --- format detection ------------------------------------------------------


@pytest.mark.parametrize(
    ("name", "route"),
    [("mesh.msh", "gmsh"), ("mesh.vol", "netgen"), ("mesh.vol.gz", "netgen")],
)
def test_if06_detect_format_reads_the_route_off_the_suffix(name: str, route: str) -> None:
    assert detect_format(Path(name)) == route


def test_if06_a_declared_format_wins_over_the_suffix() -> None:
    """A case file naming the format can read a mesh whose name says nothing."""
    assert detect_format(Path("mesh.dat"), "msh41") == "gmsh"
    assert detect_format(Path("mesh.msh"), "netgen") == "netgen"


def test_if06_an_unknown_format_names_the_ones_that_work() -> None:
    """The fix is one word in the case file, so the message lists the words."""
    with pytest.raises(MeshFormatError, match="netgen"):
        detect_format(Path("mesh.dat"), "exodus")
    with pytest.raises(MeshFormatError, match=r"\.vol"):
        detect_format(Path("mesh.dat"))


def test_if06_reading_a_missing_file_says_so(tmp_path: Path) -> None:
    with pytest.raises(MeshFormatError, match="no mesh file"):
        read(tmp_path / "absent.msh")


# --- MeshData itself -------------------------------------------------------


def test_if06_meshdata_normalises_the_dtypes_the_hash_is_taken_over() -> None:
    """int32 and int64 connectivity are the same mesh, and hash the same.

    ``canonical`` digests an array as dtype, shape and bytes, so without the
    normalisation a mesh read by one reader would miss the cache entry written
    by another for no reason a user could see.
    """
    narrow = replacing(
        vertices=SQUARE.vertices.astype(np.float32),
        triangles=SQUARE.triangles.astype(np.int32),
        triangle_material=SQUARE.triangle_material.astype(np.int32),
        edges=SQUARE.edges.astype(np.int32),
        edge_group=SQUARE.edge_group.astype(np.int32),
    )
    assert narrow.triangles.dtype == np.int64
    assert narrow.content_hash == SQUARE.content_hash


@pytest.mark.parametrize(
    ("fields", "message"),
    [
        ({"triangle_material": np.array([0, 0, 1])}, "triangle_material has"),
        ({"edge_group": np.array([0, 1, 2])}, "edge_group has"),
        ({"triangles": np.where(SQUARE.triangles == 4, 99, SQUARE.triangles)}, "out of range"),
        ({"vertices": np.zeros((9, 3))}, r"\(n, 2\)"),
        ({"edges": np.zeros((8, 3), dtype=int)}, r"\(k, 2\)"),
        (
            {"triangles": np.zeros((0, 3), dtype=int), "triangle_material": np.zeros(0, dtype=int)},
            "no domain to solve on",
        ),
        ({"boundaries": ("axis", "wall", "cis", "cis")}, "must be unique"),
    ],
)
def test_if06_a_malformed_mesh_is_refused_at_construction(
    fields: dict[str, object], message: str
) -> None:
    """QR-12: the arrays are checked where they enter, not where they diverge."""
    with pytest.raises(MeshDataError, match=message):
        replacing(**fields)


def test_if06_a_name_no_element_uses_is_refused() -> None:
    """An unused name is a mesh that lost elements, or a vocabulary typo.

    Either way the ingestion gate downstream would report the name as present
    and the solve would then find nothing to integrate over it.
    """
    with pytest.raises(MeshDataError, match="names no element uses: protein"):
        replacing(materials=("electrolyte", "membrane", "protein"))


def test_if06_material_and_edge_selection_by_name() -> None:
    assert SQUARE.material_of("membrane").tolist() == [False] * 4 + [True] * 4
    np.testing.assert_array_equal(SQUARE.edges_of("cis"), np.array([[0, 1], [1, 2]]))
    with pytest.raises(KeyError, match="no boundary group 'lateral'"):
        SQUARE.edges_of("lateral")


def test_if06_renamed_merges_the_groups_that_map_together() -> None:
    """A CAD export splitting one wall into several curves is the expected case."""
    merged = SQUARE.renamed(boundaries={"cis": "wall", "trans": "wall"})
    assert merged.boundaries == ("axis", "wall")
    assert merged.edge_group.tolist() == [0, 0, 1, 1, 1, 1, 1, 1]
    assert len(merged.edges_of("wall")) == 6


def test_if06_canonical_refuses_coincident_vertices() -> None:
    """Two vertices in one place leave the canonical order ambiguous."""
    vertices = SQUARE.vertices.copy()
    vertices[8] = vertices[0]
    with pytest.raises(MeshDataError, match="no canonical vertex order"):
        replacing(vertices=vertices).canonical()


# --- the content hash ------------------------------------------------------


def test_if06_the_content_hash_ignores_the_order_the_arrays_arrive_in() -> None:
    """A permuted mesh is the same mesh; that is what makes the round trip safe."""
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
    """The one thing a permutation-invariant hash must still see."""
    moved = replacing(edge_group=np.array([0, 0, 1, 1, 2, 2, 2, 3]))
    assert moved.content_hash != SQUARE.content_hash


def test_if06_the_content_hash_changes_when_a_group_is_renamed() -> None:
    assert replacing(materials=("electrolyte", "protein")).content_hash != SQUARE.content_hash


def test_if06_the_content_hash_is_stable_across_processes(tmp_path: Path) -> None:
    """A cache key that depended on the hash seed would silently never hit.

    ``canonical`` orders its name tables through ``sorted`` and the writer picks
    node owners out of dicts, so the guard is against an iteration order leaking
    into the digest; the subprocesses run under different values of
    ``PYTHONHASHSEED`` for exactly that reason.
    """
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


# --- MSH 4.1, the archival format ------------------------------------------


@pytest.mark.parametrize("binary", [False, True])
def test_if06_a_tagged_mesh_survives_an_msh41_round_trip(tmp_path: Path, binary: bool) -> None:
    """Vertices, connectivity, per-group tags and names all come back unchanged.

    The four boundary groups are the point: meshio writes a whole cell block
    under the *first* geometrical tag it carries, so packing them into one block
    would bring them all back as ``axis`` with no error raised anywhere.
    """
    path = write_msh41(SQUARE, tmp_path / f"square-{binary}.msh", binary=binary)
    back = read(path)
    assert back.boundaries == SQUARE.boundaries
    assert back.materials == SQUARE.materials
    assert_same_mesh(SQUARE, back)


def test_if06_ascii_msh41_is_bit_exact_on_float64(tmp_path: Path) -> None:
    """Archival means archival: the coordinates come back to the last bit.

    ``.vol`` does not — netgen writes 16 fixed decimals and loses about one ulp
    [tested] — which is why IF-06 names MSH 4.1 and not netgen's own format.
    """
    awkward = SQUARE.vertices.copy()
    awkward[4] = [np.pi / 7.0, np.sqrt(2.0) / 3.0]
    exact = replacing(vertices=awkward)
    back = read(write_msh41(exact, tmp_path / "exact.msh"))
    assert back.canonical().vertices.tobytes() == exact.canonical().vertices.tobytes()


def test_if06_every_group_gets_its_own_physical_name(tmp_path: Path) -> None:
    """``$PhysicalNames`` is written here, keyed by ``(dimension, tag)`` as gmsh keys it."""
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
    """The section 5.3.1 vocabulary spends ``cis`` twice, in two dimensions.

    meshio's ``field_data`` is keyed by name alone, so routing the names through
    it loses one of the pair and the mesh comes back with a ``group-<tag>``
    where a reservoir should be — which the ingestion gate would then reject as
    an unclaimed group, blaming the mesher for the writer's bug.
    """
    mesh = square_mesh(materials=("cis", "trans"))
    back = read(write_msh41(mesh, tmp_path / "collide.msh"))
    assert back.materials == ("cis", "trans")
    assert back.boundaries == ("axis", "wall", "cis", "trans")
    assert_same_mesh(mesh, back)


def test_if06_every_group_owns_a_node_in_the_file(tmp_path: Path) -> None:
    """Every entity must own a node, or meshio omits it and the file will not read.

    Each of the four boundary groups here shares both ends of its every edge
    with a neighbour, so a per-node greedy assignment starves one of them: the
    write succeeded and the read raised ``KeyError`` [tested]. The header count
    is asserted because that omission is what it shows.
    """
    path = write_msh41(SQUARE, tmp_path / "shared.msh")
    header = path.read_text().split("$Entities")[1].split()[:4]
    assert header == ["0", "4", "2", "0"]  # no points, four curves, two surfaces
    assert read(path).boundaries == SQUARE.boundaries


def test_if06_more_groups_than_nodes_is_refused_with_a_diagnostic() -> None:
    """The one mesh the node-owning rule cannot satisfy is named, not mis-written.

    Four triangles about a centre give five nodes and six groups, so some group
    must go without; QR-12 says that aborts with the offending quantity rather
    than writing a file whose reader will fail.
    """
    pinwheel = MeshData(
        vertices=np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.5, 0.5]]),
        triangles=np.array([[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4]]),
        triangle_material=np.array([0, 0, 1, 1]),
        materials=("electrolyte", "membrane"),
        edges=np.array([[0, 1], [1, 2], [2, 3], [3, 0]]),
        edge_group=np.array([0, 1, 2, 3]),
        boundaries=("axis", "wall", "cis", "trans"),
    )
    with pytest.raises(MeshDataError, match="fewer nodes than groups"):
        write_msh41(pinwheel, Path("unreachable.msh"))


def test_if06_the_hash_ignores_a_file_meshio_rewrote(tmp_path: Path) -> None:
    """Read, write, read: the bytes differ, the mesh does not (section 5.3.2)."""
    first = write_msh41(SQUARE, tmp_path / "first.msh")
    second = write_msh41(read(first), tmp_path / "second.msh", binary=True)
    assert first.read_bytes() != second.read_bytes()
    assert read(second).content_hash == SQUARE.content_hash


def test_if06_a_mesh_off_the_half_plane_is_refused(tmp_path: Path) -> None:
    """CON-04: a mesh with a third coordinate is a 3-D mesh, not an (r, z) one."""
    path = write_msh41(SQUARE, tmp_path / "flat.msh")
    head, marker, rest = path.read_text().partition("$EndNodes")
    lifted = re.sub(
        r"^(\S+) (\S+) 0\.0+e\+00$", r"\1 \2 5.0e+00", head, count=1, flags=re.MULTILINE
    )
    assert lifted != head, "no node coordinate line was found to lift"
    path.write_text(lifted + marker + rest)
    with pytest.raises(MeshFormatError, match="three-dimensional"):
        read(path)


def test_if06_a_mesh_with_no_boundary_segments_is_refused(tmp_path: Path) -> None:
    """A mesh that names no boundary cannot carry a boundary condition.

    Every condition of section 5.3.1 is imposed by name, so this is a mesh the
    solver could only misinterpret.
    """
    bare = replacing(
        edges=np.zeros((0, 2), dtype=int), edge_group=np.zeros(0, dtype=int), boundaries=()
    )
    path = write_msh41(bare, tmp_path / "bare.msh")
    with pytest.raises(MeshFormatError, match="no boundary segments"):
        read(path)


# --- the NGSolve routes ----------------------------------------------------


def test_if06_to_ngsolve_then_from_ngsolve_is_the_identity_on_the_tag_maps() -> None:
    """The route an ingested mesh takes into the solver, there being no geometry.

    ``SetBCName`` is 0-based where ``Element1D(index=...)`` is 1-based; an
    off-by-one there names the axis ``wall`` and raises nothing, so the tag maps
    are compared group by group rather than counted.
    """
    mesh = square_mesh()
    ngmesh = to_ngsolve(mesh)
    assert set(ngmesh.GetMaterials()) == set(mesh.materials)
    assert set(ngmesh.GetBoundaries()) == set(mesh.boundaries)
    assert_same_mesh(mesh, from_ngsolve(ngmesh))


def test_if06_a_generated_mesh_round_trips_through_the_file_and_back() -> None:
    """A real netgen mesh, out through MSH 4.1 and back into NGSolve.

    ``SlabGeometry`` gives its two lateral edges one name over two face
    descriptors, so this also pins the merge ``from_ngsolve`` does: NGSolve
    selects on the name, and so does everything downstream.
    """
    mesh = from_ngsolve(SlabGeometry(width_nm=2.0, height_nm=1.0).generate(maxh_nm=0.5))
    assert mesh.materials == ("electrolyte",)
    assert set(mesh.boundaries) == {"wall", "bulk", "lateral"}
    assert_same_mesh(mesh, from_ngsolve(to_ngsolve(mesh)))


def test_if06_a_generated_mesh_survives_the_archival_format(tmp_path: Path) -> None:
    """The full ingestion path for a mesh nanopnp did not itself build."""
    mesh = from_ngsolve(SlabGeometry(width_nm=2.0, height_nm=1.0).generate(maxh_nm=0.5))
    back = read(write_msh41(mesh, tmp_path / "slab.msh"))
    assert_same_mesh(mesh, back)
    assert back.element_count == mesh.element_count

"""The pore geometry's shape/mesh split, and the edge-naming guard it exists for."""

import netgen.occ as occ

from nanopnp.mesh.primitives import CylindricalPoreGeometry

PORE = CylindricalPoreGeometry(
    pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=12.0
)


def test_the_shape_split_leaves_the_boundary_vocabulary_unchanged() -> None:
    mesh = PORE.generate(maxh_nm=2.0)
    assert set(mesh.GetMaterials()) == {"electrolyte", "membrane", "cis", "trans"}
    assert set(mesh.GetBoundaries()) == {
        "axis",
        "wall",
        "membrane",
        "membrane_outer",
        "cis",
        "trans",
        "default",
    }


def test_faces_returns_the_lumen_first_and_names_every_domain() -> None:
    # A boolean result is an OCC compound and refuses a ``name`` query, so the
    # name is read off its one face rather than off the shape.
    parts = PORE.faces()
    assert [shape.faces[0].name for shape in parts] == [
        "electrolyte",
        "membrane",
        "cis",
        "trans",
    ]


def test_name_edges_leaves_an_already_named_edge_alone() -> None:
    shape = occ.Glue(list(PORE.faces()))
    on_the_wall = [
        edge
        for edge in shape.edges
        if abs(edge.center[0] - PORE.pore_radius_nm) < 1e-9
        and abs(edge.center[1]) < PORE.half_thickness_nm
    ]
    assert on_the_wall, "the pore has no wall edge; the geometry has changed"
    on_the_wall[0].name = "analyte"

    PORE.name_edges(shape)

    assert on_the_wall[0].name == "analyte"
    assert {edge.name for edge in shape.edges} >= {"axis", "analyte", "cis", "trans"}

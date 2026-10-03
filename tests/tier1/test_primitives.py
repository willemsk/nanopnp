"""The pore geometry's shape/mesh split, and the edge-naming guard it exists for.

``CylindricalPoreGeometry`` classifies its boundaries by edge centre of mass in
an unconditional chain, which is fine while it is the only thing in the picture.
Embedding an analyte in the lumen puts edges into that chain that it has no name
for, so the chain now skips edges that already carry one. These tests pin the
guard and pin that the refactor left the geometry's vocabulary alone.
"""

import netgen.occ as occ

from nanopnp.mesh.primitives import CylindricalPoreGeometry

PORE = CylindricalPoreGeometry(
    pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=12.0
)
"""A small pore; the vocabulary is what is under test, not the resolution."""


def test_the_shape_split_leaves_the_boundary_vocabulary_unchanged() -> None:
    """``generate`` still produces exactly the domains and boundaries it always did."""
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
    """The lumen comes first because that is the face an embedded body is cut from."""
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
    """A pre-named edge keeps its name even where the position chain would rename it.

    The edge chosen sits on the pore wall, which the chain would call ``wall``.
    Without the guard an analyte surface crossing that position — or any other —
    would be swallowed into the pore's own vocabulary, and the force integral
    would then be taken over the wrong boundary with no diagnostic at all.
    """
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

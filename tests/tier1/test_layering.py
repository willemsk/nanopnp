"""VER-61: the subpackage import relation is the one the modularity report records (WP35, G1).

``docs/project/modularity-layering.yaml`` lists every subpackage edge of the static
relation (imports at module scope, inside a function or under ``TYPE_CHECKING``)
and of the string relation (a constant naming a module, as the stage registry and
``PUBLIC`` do). The live relation, measured from the syntax tree by
:mod:`nanopnp.validation.modularity`, must equal it in both directions, so a new
coupling between layers is a decision recorded in the commit that makes it, and a
removed one cannot leave a stale row.

The guard is shown to fire on the code that should trip it: an upward import
substituted into ``core/constants.py`` fails naming the edge, the module and the
line; a recorded edge with no import behind it fails as removed. The classifier
and the component search are each checked against a package and a graph whose
answers are written down by hand, so neither can pass by agreeing with itself.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from nanopnp.validation.findings import REPOSITORY, parse_log
from nanopnp.validation.modularity import (
    DEFERRED_UPWARD,
    LAYER_ORDER,
    PACKAGE,
    RATCHETS,
    UPWARD,
    AcceptedEdge,
    ImportEdge,
    accepted_relation,
    accepted_upward,
    compare,
    component_edges,
    components,
    import_edges,
    measured_relations,
    module_graph,
    node_of,
    parse_package,
    upward_edges,
)

CONSTANTS = PACKAGE / "core" / "constants.py"
ANALYTE = PACKAGE / "geometry" / "analyte.py"


def test_ver61_live_relation_equals_the_recorded_layering() -> None:
    comparison = compare(measured_relations(import_edges()), accepted_relation())
    assert comparison.equal, comparison.describe()


def test_ver61_every_annotated_edge_names_a_finding_of_the_log() -> None:
    """An edge's ``finding`` is a ``MOD-nn`` or ``REV-nn`` row, so a typo or a dropped row fails."""
    project = REPOSITORY / "docs" / "project"
    ids = {
        row.id
        for name in ("modularity-findings.md", "review-findings.md")
        for row in parse_log(project / name).rows
    }
    recorded = (*accepted_relation(), *(e for r in RATCHETS for e in accepted_upward(ratchet=r)))
    named = {edge.finding for edge in recorded} - {None}
    assert named <= ids, sorted(named - ids)


def test_ver61_every_ratchet_row_names_its_finding() -> None:
    """An edge kept against the order says why, so the YAML header's rule is a test (H12)."""
    for ratchet in RATCHETS:
        unexplained = [e for e in accepted_upward(ratchet=ratchet) if e.finding is None]
        assert unexplained == [], (ratchet, unexplained)


def test_ver61_the_measurement_adds_no_edge_of_its_own() -> None:
    """The measuring modules name what they read by path, so they couple to nothing."""
    own = {"validation/modularity.py", "validation/findings.py"}
    assert [edge for edge in import_edges() if edge.path in own] == []


def test_ver61_upward_top_edges_equal_the_recorded_ratchet() -> None:
    """The ``top`` edges pointing up the layer order are exactly the ``upward:`` rows (H11).

    WP38's split leaves one, ``cli -> nanopnp``, which WP39 removes (REV-05): the
    stages read the base ``io`` and are handed the resolved case, so none imports
    the assembler ``pipeline`` above them.
    """
    comparison = compare({UPWARD: upward_edges(import_edges())}, accepted_upward())
    assert comparison.equal, comparison.describe()
    assert {(edge.source, edge.target) for edge in accepted_upward()} == {("cli", "nanopnp")}


def test_ver61_a_stage_importing_the_assembler_fails_naming_the_edge() -> None:
    """A stage that resolved its own case again would import ``pipeline`` upward (WP38 D4)."""
    ingest = PACKAGE / "mesh" / "ingest.py"
    text = ingest.read_text(encoding="utf-8")
    line = len(text.splitlines()) + 1
    edges = import_edges(
        sources={"mesh/ingest.py": f"{text}from nanopnp.pipeline.case import resolve\n"}
    )
    comparison = compare({UPWARD: upward_edges(edges)}, accepted_upward())
    assert [pair for _, pair, _ in comparison.added] == [("mesh", "pipeline")]
    message = comparison.describe()
    assert "new upward edge mesh -> pipeline" in message
    assert f"mesh/ingest.py:{line}" in message


def test_ver61_the_base_importing_materials_at_run_time_fails_naming_the_edge() -> None:
    """The resolved case annotates the electrolyte; importing it is ``io -> materials`` (D2)."""
    resolved = PACKAGE / "io" / "resolved.py"
    text = resolved.read_text(encoding="utf-8")
    guarded = "    from nanopnp.materials.electrolyte import Electrolyte\n"
    assert guarded in text
    moved = text.replace(guarded, "") + "from nanopnp.materials.electrolyte import Electrolyte\n"
    edges = import_edges(sources={"io/resolved.py": moved})
    assert compare(measured_relations(edges), accepted_relation()).equal
    comparison = compare({UPWARD: upward_edges(edges)}, accepted_upward())
    assert [pair for _, pair, _ in comparison.added] == [("io", "materials")]
    assert "new upward edge io -> materials" in comparison.describe()


def test_ver61_upward_deferred_edges_equal_the_recorded_ratchet() -> None:
    """Imports inside a function that point up the order are the ``deferred_upward:`` rows (H12).

    One is left: the desktop shell's probe reads ``nanopnp.__version__`` (REV-05).
    """
    measured = upward_edges(import_edges(), kinds=RATCHETS[DEFERRED_UPWARD])
    accepted = accepted_upward(ratchet=DEFERRED_UPWARD)
    comparison = compare({DEFERRED_UPWARD: measured}, accepted)
    assert comparison.equal, comparison.describe()
    assert {(edge.source, edge.target) for edge in accepted} == {("gui", "nanopnp")}


def test_ver61_an_annotation_cut_deferred_into_a_function_fails_as_deferred_upward() -> None:
    """``geometry -> mesh`` stays a static edge, so only the deferred ratchet sees this (D12)."""
    text = ANALYTE.read_text(encoding="utf-8")
    line = len(text.splitlines()) + 2
    late = "def _late():\n    from nanopnp.mesh.primitives import CylindricalPoreGeometry\n"
    deferred = f"{text}{late}"
    edges = import_edges(sources={"geometry/analyte.py": deferred})
    assert compare(measured_relations(edges), accepted_relation()).equal
    assert compare({UPWARD: upward_edges(edges)}, accepted_upward()).equal
    comparison = compare(
        {DEFERRED_UPWARD: upward_edges(edges, kinds=RATCHETS[DEFERRED_UPWARD])},
        accepted_upward(ratchet=DEFERRED_UPWARD),
    )
    assert [pair for _, pair, _ in comparison.added] == [("geometry", "mesh")]
    message = comparison.describe()
    assert "new deferred_upward edge geometry -> mesh" in message
    assert f"geometry/analyte.py:{line}" in message
    assert "only shrinks" in message
    assert "a deferred import is not a cut" in message


def test_ver61_accepted_upward_refuses_an_unknown_ratchet() -> None:
    with pytest.raises(ValueError, match="'edges' is not a ratchet"):
        accepted_upward(ratchet="edges")


def test_ver61_the_layer_order_places_every_subpackage_once() -> None:
    assert len(set(LAYER_ORDER)) == len(LAYER_ORDER)
    assert set(LAYER_ORDER) == {node_of(module.name) for module in parse_package()}


def test_ver61_an_annotation_cut_returning_to_module_scope_fails_as_upward() -> None:
    """``geometry -> mesh`` is a ``typing`` edge after D6, so the static relation keeps it.

    Moving ``CylindricalPoreGeometry`` back out of ``TYPE_CHECKING`` changes no row
    of ``edges:``; only the ratchet sees it, naming the edge, the module and the line.
    """
    text = ANALYTE.read_text(encoding="utf-8")
    line = len(text.splitlines()) + 1
    restored = f"{text}from nanopnp.mesh.primitives import CylindricalPoreGeometry\n"
    edges = import_edges(sources={"geometry/analyte.py": restored})
    assert compare(measured_relations(edges), accepted_relation()).equal
    comparison = compare({UPWARD: upward_edges(edges)}, accepted_upward())
    assert [pair for _, pair, _ in comparison.added] == [("geometry", "mesh")]
    message = comparison.describe()
    assert "new upward edge geometry -> mesh" in message
    assert f"geometry/analyte.py:{line}" in message
    # The ratchet only shrinks, so its diagnostic must not offer recording the edge.
    assert "only shrinks" in message
    assert "record the edge" not in message


def test_ver61_an_unplaced_subpackage_is_refused_naming_it() -> None:
    edges = (ImportEdge("nanopnp.core.x", "nanopnp.extra.y", "top", 1, "core/x.py"),)
    with pytest.raises(ValueError, match="extra has no place in the layer order"):
        upward_edges(edges)


def test_ver61_accepted_upward_refuses_a_repeated_row(tmp_path: Path) -> None:
    path = tmp_path / "layering.yaml"
    row = "  - {from: mesh, to: io, finding: MOD-04}\n"
    path.write_text(f"upward:\n{row}{row}", encoding="utf-8")
    with pytest.raises(ValueError, match="upward edge 2 repeats mesh -> io"):
        accepted_upward(path)


def test_ver61_top_level_module_imports_are_acyclic() -> None:
    graph = module_graph(import_edges(), {"top"}, packages=True)
    assert components(graph) == ()


def test_ver61_a_cycle_through_a_package_init_is_a_cycle() -> None:
    """A load-time cycle that no two modules close between themselves.

    ``a.m`` imports ``b.n``, which runs ``b/__init__`` first; that imports ``b.k``,
    which imports ``a.m``, and Python meets ``a.m`` half-initialised.
    """
    edges = (
        ImportEdge("nanopnp.a.m", "nanopnp.b.n", "top", 1, "a/m.py"),
        ImportEdge("nanopnp.b", "nanopnp.b.k", "top", 1, "b/__init__.py"),
        ImportEdge("nanopnp.b.k", "nanopnp.a.m", "top", 1, "b/k.py"),
        ImportEdge("nanopnp.b.k", "nanopnp.b.n", "top", 2, "b/k.py"),
    )
    assert components(module_graph(edges, {"top"})) == ()
    graph = module_graph(edges, {"top"}, packages=True)
    assert graph["nanopnp.a.m"] == {"nanopnp.b.n", "nanopnp.b"}
    # ``b.k`` reaches ``a``'s ``__init__`` on the way to ``a.m``, but not its own ``b``'s.
    assert graph["nanopnp.b.k"] == {"nanopnp.a", "nanopnp.a.m", "nanopnp.b.n"}
    assert components(graph) == (("nanopnp.a.m", "nanopnp.b", "nanopnp.b.k"),)


def test_ver61_upward_import_fails_naming_edge_module_and_line() -> None:
    text = CONSTANTS.read_text(encoding="utf-8")
    line = len(text.splitlines()) + 1
    edges = import_edges(sources={"core/constants.py": f"{text}import nanopnp.gui\n"})
    comparison = compare(measured_relations(edges), accepted_relation())
    assert not comparison.equal
    assert [(relation, pair) for relation, pair, _ in comparison.added] == [
        ("static", ("core", "gui"))
    ]
    message = comparison.describe()
    assert "core -> gui" in message
    assert f"core/constants.py:{line}" in message
    assert "modularity-layering.yaml" in message


def test_ver61_recorded_edge_without_an_import_fails_as_removed() -> None:
    accepted = (*accepted_relation(), AcceptedEdge("symmetry", "gui", "static"))
    comparison = compare(measured_relations(import_edges()), accepted)
    assert comparison.removed == (("static", ("symmetry", "gui")),)
    assert "removed static edge symmetry -> gui" in comparison.describe()


def test_ver61_accepted_relation_refuses_a_repeated_row(tmp_path: Path) -> None:
    path = tmp_path / "layering.yaml"
    row = "  - {from: io, to: core, relation: static, finding: null}\n"
    path.write_text(f"edges:\n{row}{row}", encoding="utf-8")
    with pytest.raises(ValueError, match="edge 2 repeats io -> core"):
        accepted_relation(path)


SYNTHETIC = {
    "__init__.py": '"""Root; ``nanopnp.y.n`` in a docstring is not an edge."""\n',
    "x/__init__.py": "",
    "x/m.py": (
        "from __future__ import annotations\n"  # 1
        "from typing import TYPE_CHECKING\n"  # 2
        "import nanopnp.y.n\n"  # 3
        "if TYPE_CHECKING:\n"  # 4
        "    from nanopnp.z import w\n"  # 5
        "try:\n"  # 6
        "    from ..z.w import thing\n"  # 7
        "except ImportError:\n"  # 8
        "    pass\n"  # 9
        "def f() -> None:\n"  # 10
        '    """Names nanopnp.y.n, as text."""\n'  # 11
        "    from nanopnp.z.w import thing\n"  # 12
        'TARGET = "nanopnp.y.n:thing"\n'  # 13
        'MISSING = "nanopnp.y.absent"\n'  # 14
    ),
    "y/__init__.py": "",
    "y/n.py": "thing = 1\n",
    "z/__init__.py": "",
    "z/w.py": "thing = 2\n",
}
"""Three subpackages; ``x/m.py`` imports in every kind, its line numbers written by hand."""


def test_ver61_classifier_assigns_each_kind_by_hand(tmp_path: Path) -> None:
    for relative, text in SYNTHETIC.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    edges = set(import_edges(tmp_path))
    assert edges == {
        ImportEdge("nanopnp.x.m", "nanopnp.y.n", "top", 3, "x/m.py"),
        ImportEdge("nanopnp.x.m", "nanopnp.z.w", "typing", 5, "x/m.py"),
        ImportEdge("nanopnp.x.m", "nanopnp.z.w", "top", 7, "x/m.py"),
        ImportEdge("nanopnp.x.m", "nanopnp.z.w", "deferred", 12, "x/m.py"),
        ImportEdge("nanopnp.x.m", "nanopnp.y.n", "string", 13, "x/m.py"),
    }
    relations = measured_relations(edges)
    assert set(relations["static"]) == {("x", "y"), ("x", "z")}
    assert set(relations["string"]) == {("x", "y")}


def test_ver61_components_match_a_graph_solved_by_hand() -> None:
    graph = {
        "a": {"b"},
        "b": {"c"},
        "c": {"a", "d"},
        "d": {"e"},
        "e": {"d"},
        "f": {"a"},
        "g": set(),
    }
    assert components(graph) == (("a", "b", "c"), ("d", "e"))
    edge = ImportEdge("nanopnp.a", "nanopnp.b", "top", 1, "a.py")
    relation = {
        ("a", "b"): (edge, ImportEdge("nanopnp.a", "nanopnp.b", "top", 2, "a.py")),
        ("b", "c"): (ImportEdge("nanopnp.b", "nanopnp.c", "top", 1, "b.py"),),
        ("c", "a"): (ImportEdge("nanopnp.c", "nanopnp.a", "top", 1, "c.py"),),
        ("c", "d"): (ImportEdge("nanopnp.c", "nanopnp.d", "top", 1, "c.py"),),
    }
    assert component_edges(("a", "b", "c"), relation) == (
        ("b", "c", 1),
        ("c", "a", 1),
        ("a", "b", 2),
    )


SPLIT_BOUND = 1266
"""``MOD-13``'s bound for the modules WP38's split produces: the smallest module the
finding names (``cli/__init__.py`` at ``fd4308f``), since the finding states none."""


@pytest.mark.parametrize(
    "path",
    [
        "io/case.py",
        "io/case_paths.py",
        "io/resolved.py",
        "io/vocabulary.py",
        "pipeline/case.py",
        "pipeline/checks.py",
    ],
)
def test_mod13_no_module_of_the_io_split_exceeds_the_bound(path: str) -> None:
    """Each module ``io/case.py`` became is at most 1,266 lines (WP38 D14)."""
    lines = len((PACKAGE / path).read_text(encoding="utf-8").splitlines())
    assert lines <= SPLIT_BOUND, f"{path} has {lines} lines"

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

from nanopnp.validation.modularity import (
    PACKAGE,
    AcceptedEdge,
    ImportEdge,
    accepted_relation,
    compare,
    component_edges,
    components,
    import_edges,
    measured_relations,
    module_graph,
)

CONSTANTS = PACKAGE / "core" / "constants.py"


def test_ver61_live_relation_equals_the_recorded_layering() -> None:
    comparison = compare(measured_relations(import_edges()), accepted_relation())
    assert comparison.equal, comparison.describe()


def test_ver61_the_measurement_adds_no_edge_of_its_own() -> None:
    """The measuring modules name what they read by path, so they couple to nothing."""
    own = {"validation/modularity.py", "validation/findings.py"}
    assert [edge for edge in import_edges() if edge.path in own] == []


def test_ver61_top_level_module_imports_are_acyclic() -> None:
    graph = module_graph(import_edges(), {"top"})
    assert components(graph) == ()


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

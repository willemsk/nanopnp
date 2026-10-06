"""Measure the package's structure from its source, for the modularity report (WP35, G1).

Every number of ``docs/project/modularity.md`` is produced here, and VER-61 pins the
subpackage import relation this module computes against
``docs/project/modularity-layering.yaml``. The code is read by its syntax tree only
(WP35 D2): nothing here imports an implementation module, so the measurements run
in the documentation job without extras, and a stage's conformance is read from its
class's source rather than from the class.

The nodes of the import relation are the subpackages of ``nanopnp``, plus
``nanopnp`` itself for ``__init__.py`` (D3). An import edge has one of four kinds
(D4):

- ``top``: at module scope, outside ``if TYPE_CHECKING:``;
- ``deferred``: inside a function;
- ``typing``: inside ``if TYPE_CHECKING:``;
- ``string``: a non-docstring string constant naming an existing ``nanopnp``
  module, as ``module`` or ``module:attribute``, which is how the stage registry,
  ``PUBLIC`` and the exit-code table of ``core/errors.py`` reach a module.

The **static** relation is the union of the first three, and the **string**
relation is the fourth (D5). A deferral or an annotation still couples two layers,
so moving an import into a function changes a kind and never the static relation.
"""

from __future__ import annotations

import ast
import re
from collections import Counter, defaultdict
from collections.abc import Collection, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

PACKAGE = Path(__file__).resolve().parents[1]
"""The ``nanopnp`` package directory measured by default."""

LAYERING = PACKAGE.parents[1] / "docs" / "project" / "modularity-layering.yaml"
"""The accepted subpackage relation VER-61 pins (WP35 D6)."""

ROOT_NODE = "nanopnp"
"""The node of ``nanopnp/__init__.py``, the only top-level module (D3)."""

KINDS: tuple[str, ...] = ("top", "deferred", "typing", "string")
"""Every kind an import edge takes (D4)."""

STATIC_KINDS: frozenset[str] = frozenset({"top", "deferred", "typing"})
"""The kinds whose union is the static relation (D5)."""

RELATIONS: dict[str, frozenset[str]] = {
    "static": STATIC_KINDS,
    "string": frozenset({"string"}),
}
"""The two relations VER-61 pins, each by the kinds it unites (D5)."""

MODULE_STRING = re.compile(r"^nanopnp(\.\w+)+(:[\w.]+)?$")
"""A string naming a ``nanopnp`` module, optionally with ``:attribute`` (D4)."""

VERSION_LITERAL = re.compile(r"\bv0\.\d+\b")
"""A release name, ``v0.N``, written into a string the code uses (D8 g)."""

BACKEND_PACKAGES: frozenset[str] = frozenset({"ngsolve", "netgen"})
"""The finite-element backend's top-level packages (QR-13, section 5.4.1)."""

BACKEND_STRING = re.compile(r"^(ngsolve|netgen)((\.\w+)+(:[\w.]+)?|:[\w.]+)$")
"""A string naming a backend module below its top level, or an attribute of one (VER-65).

A dot or a colon is required, as :data:`MODULE_STRING` requires one: a bare
``"netgen"`` is also the mesher's name in the case schema, which couples nothing
to the backend's code.
"""

LAYER_ORDER: tuple[str, ...] = (
    "core",
    "io",
    "structure",
    "density",
    "symmetry",
    "geometry",
    "mesh",
    "numerics",
    "charge",
    "materials",
    "physics",
    "solve",
    "post",
    "pipeline",
    "sweep",
    "validation",
    "cli",
    "gui",
    ROOT_NODE,
)
"""The accepted order of the relation's nodes, lowest first (section 8.2.8 H6, H11).

An edge from a node to one later in this order points **up** it. VER-61's
``upward:`` list records the ``top`` edges that do, until WP39 empties it.
"""

BACKEND_INTERFACE: tuple[str, ...] = (
    "FunctionSpace",
    "TrialFn",
    "TestFn",
    "dx_axi",
    "Coefficient",
)
"""The names section 5.4.1 puts in scope of the backend interface, as defined names."""

STAGE_RUN = "(inputs, *, progress, cancel)"
"""The parameters of :meth:`nanopnp.core.stages.Stage.run`, as :func:`_signature` writes them."""

STAGE_KEY = "(inputs)"
"""The parameters of :meth:`nanopnp.core.stages.Stage.key`, as :func:`_signature` writes them."""


# -- parsing ---------------------------------------------------------------------


@dataclass(frozen=True)
class Module:
    """One parsed source file of the package."""

    name: str
    """Dotted module name, ``nanopnp.core.stages``; a package is its ``__init__``."""
    path: str
    """Path relative to the package directory, POSIX-style: ``core/stages.py``."""
    tree: ast.Module
    lines: int
    is_package: bool


def node_of(module: str) -> str:
    """Return the relation node of a dotted module name (D3)."""
    parts = module.split(".")
    return parts[1] if len(parts) > 1 else ROOT_NODE


def _module_name(relative: str) -> tuple[str, bool]:
    parts = relative.removesuffix(".py").split("/")
    if parts[-1] == "__init__":
        return ".".join([ROOT_NODE, *parts[:-1]]), True
    return ".".join([ROOT_NODE, *parts]), False


@lru_cache(maxsize=8)
def _parse(root: Path, sources: tuple[tuple[str, str], ...]) -> tuple[Module, ...]:
    texts = {
        path.relative_to(root).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(root.rglob("*.py"))
    }
    texts.update(sources)
    modules = []
    for relative, text in sorted(texts.items()):
        name, is_package = _module_name(relative)
        tree = ast.parse(text, filename=relative)
        modules.append(Module(name, relative, tree, len(text.splitlines()), is_package))
    return tuple(modules)


def parse_package(
    root: Path | None = None, sources: Mapping[str, str] | None = None
) -> tuple[Module, ...]:
    """Parse every module of the package under ``root``.

    Parameters
    ----------
    root
        The package directory; :data:`PACKAGE` by default.
    sources
        ``{relative path: text}`` substituted for, or added to, the files on disk,
        so that a test can measure a package that differs from this one by a line.
    """
    base = (root or PACKAGE).resolve()
    return _parse(base, tuple(sorted((sources or {}).items())))


def _docstrings(tree: ast.AST) -> set[int]:
    """Return the ``id`` of every string constant that is a bare expression statement.

    That covers module, class and function docstrings and the attribute docstrings
    this codebase writes under an assignment: text for a reader, never a value.
    """
    return {
        id(node.value)
        for node in ast.walk(tree)
        if isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    }


def _strings(tree: ast.AST) -> Iterator[ast.Constant]:
    """Yield every string constant of ``tree`` that is not a docstring."""
    skip = _docstrings(tree)
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in skip:
            yield node


@lru_cache(maxsize=1024)
def _module_strings(module: Module) -> tuple[tuple[str, int], ...]:
    """Return ``(text, line)`` of every non-docstring string of one module, cached."""
    return tuple((str(c.value), c.lineno) for c in _strings(module.tree))


# -- the import relation (D3-D5, Design section 1) ---------------------------------


@dataclass(frozen=True, order=True)
class ImportEdge:
    """One import of one ``nanopnp`` module by another."""

    source: str
    """The importing module."""
    target: str
    """The imported module."""
    kind: str
    """One of :data:`KINDS`."""
    line: int
    path: str
    """The importing module's file, relative to the package directory."""

    @property
    def nodes(self) -> tuple[str, str]:
        """The subpackage edge this import makes."""
        return node_of(self.source), node_of(self.target)


def _is_type_checking(test: ast.expr) -> bool:
    if isinstance(test, ast.Name):
        return test.id == "TYPE_CHECKING"
    return isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"


def _scoped_imports(tree: ast.Module) -> Iterator[tuple[ast.Import | ast.ImportFrom, str]]:
    """Yield each import statement with its kind: ``top``, ``deferred`` or ``typing``."""
    stack: list[tuple[ast.AST, str]] = [(statement, "top") for statement in reversed(tree.body)]
    while stack:
        node, kind = stack.pop()
        if isinstance(node, ast.Import | ast.ImportFrom):
            yield node, kind
            continue
        children: list[tuple[ast.AST, str]] = []
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.Lambda):
            children = [(child, "deferred") for child in ast.iter_child_nodes(node)]
        elif isinstance(node, ast.If) and kind == "top" and _is_type_checking(node.test):
            children = [(child, "typing") for child in node.body]
            children += [(child, kind) for child in node.orelse]
        else:
            children = [(child, kind) for child in ast.iter_child_nodes(node)]
        stack.extend(reversed(children))


def _resolve(
    module: Module, node: ast.Import | ast.ImportFrom, known: Collection[str]
) -> list[str]:
    """Return the ``nanopnp`` modules one import statement names (Design section 1)."""
    targets: list[str] = []
    if isinstance(node, ast.Import):
        for alias in node.names:
            targets.append(alias.name)
        return [_existing(name, known) for name in targets if _in_package(name)]
    if node.level:
        package = module.name if module.is_package else module.name.rpartition(".")[0]
        for _ in range(node.level - 1):
            package = package.rpartition(".")[0]
        base = f"{package}.{node.module}" if node.module else package
    else:
        base = node.module or ""
    if not _in_package(base):
        return []
    for alias in node.names:
        candidate = f"{base}.{alias.name}"
        targets.append(candidate if candidate in known else _existing(base, known))
    return targets


def _in_package(name: str) -> bool:
    return name == ROOT_NODE or name.startswith(f"{ROOT_NODE}.")


def _existing(name: str, known: Collection[str]) -> str:
    """Return the longest prefix of ``name`` that is a module of the package."""
    while name not in known and "." in name:
        name = name.rpartition(".")[0]
    return name


def import_edges(
    root: Path | None = None, sources: Mapping[str, str] | None = None
) -> tuple[ImportEdge, ...]:
    """Return every import of a ``nanopnp`` module by another, with its kind (D4).

    Module self-imports are dropped; imports between two modules of one subpackage
    are kept, because the ``top`` module graph needs them. A ``string`` edge is a
    non-docstring constant matching :data:`MODULE_STRING` whose module part is a
    module of the package.
    """
    modules = parse_package(root, sources)
    known = frozenset(module.name for module in modules)
    edges: set[ImportEdge] = set()
    for module in modules:
        for statement, kind in _scoped_imports(module.tree):
            for target in _resolve(module, statement, known):
                if target != module.name:
                    edges.add(ImportEdge(module.name, target, kind, statement.lineno, module.path))
        for text, line in _module_strings(module):
            if MODULE_STRING.match(text):
                target = text.partition(":")[0]
                if target in known and target != module.name:
                    edges.add(ImportEdge(module.name, target, "string", line, module.path))
    return tuple(sorted(edges))


def subpackage_relation(
    edges: Iterable[ImportEdge], kinds: Collection[str]
) -> dict[tuple[str, str], tuple[ImportEdge, ...]]:
    """Return each subpackage edge of the given kinds, with the imports that make it.

    Self-edges are dropped. The imports are sorted by module and line, so the first
    one is the place a diagnostic names.
    """
    relation: dict[tuple[str, str], list[ImportEdge]] = defaultdict(list)
    for edge in edges:
        source, target = edge.nodes
        if edge.kind in kinds and source != target:
            relation[(source, target)].append(edge)
    return {pair: tuple(sorted(found, key=_place)) for pair, found in sorted(relation.items())}


def _place(edge: ImportEdge) -> tuple[str, int]:
    return edge.path, edge.line


def measured_relations(
    edges: Iterable[ImportEdge],
) -> dict[str, dict[tuple[str, str], tuple[ImportEdge, ...]]]:
    """Return the static and the string relation, by name (D5)."""
    collected = tuple(edges)
    return {name: subpackage_relation(collected, kinds) for name, kinds in RELATIONS.items()}


def module_graph(
    edges: Iterable[ImportEdge], kinds: Collection[str], *, packages: bool = False
) -> dict[str, set[str]]:
    """Return the module-to-module graph of the given kinds.

    With ``packages``, an import also reaches every package whose ``__init__``
    Python runs on the way to its target, except the importer's own, which are
    already initialising: ``from nanopnp.core.errors import classify`` runs
    ``core/__init__.py`` first, so a load-time cycle through a package's
    ``__init__`` is a cycle of this graph and not only of the interpreter.
    """
    graph: dict[str, set[str]] = defaultdict(set)
    for edge in edges:
        if edge.kind not in kinds:
            continue
        graph[edge.source].add(edge.target)
        if packages:
            parts = edge.target.split(".")
            for end in range(2, len(parts)):
                package = ".".join(parts[:end])
                if package != edge.source and not edge.source.startswith(f"{package}."):
                    graph[edge.source].add(package)
    return dict(graph)


def node_graph(relation: Iterable[tuple[str, str]]) -> dict[str, set[str]]:
    """Return a relation's pairs as an adjacency mapping."""
    graph: dict[str, set[str]] = defaultdict(set)
    for source, target in relation:
        graph[source].add(target)
    return dict(graph)


def components(graph: Mapping[str, Collection[str]]) -> tuple[tuple[str, ...], ...]:
    """Return the strongly connected components with more than one member.

    Tarjan's algorithm, iterative so that a deep graph cannot reach the recursion
    limit (Design section 1). Members are sorted, and so are the components, by size
    and then by first member.
    """
    vertices = sorted({*graph, *(target for targets in graph.values() for target in targets)})
    index: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    on_stack: set[str] = set()
    stack: list[str] = []
    found: list[tuple[str, ...]] = []
    counter = 0
    for start in vertices:
        if start in index:
            continue
        work: list[tuple[str, Iterator[str]]] = [(start, iter(sorted(graph.get(start, ()))))]
        index[start] = lowlink[start] = counter
        counter += 1
        stack.append(start)
        on_stack.add(start)
        while work:
            vertex, successors = work[-1]
            advanced = False
            for successor in successors:
                if successor not in index:
                    index[successor] = lowlink[successor] = counter
                    counter += 1
                    stack.append(successor)
                    on_stack.add(successor)
                    work.append((successor, iter(sorted(graph.get(successor, ())))))
                    advanced = True
                    break
                if successor in on_stack:
                    lowlink[vertex] = min(lowlink[vertex], index[successor])
            if advanced:
                continue
            work.pop()
            if work:
                parent = work[-1][0]
                lowlink[parent] = min(lowlink[parent], lowlink[vertex])
            if lowlink[vertex] == index[vertex]:
                members = []
                while True:
                    member = stack.pop()
                    on_stack.discard(member)
                    members.append(member)
                    if member == vertex:
                        break
                if len(members) > 1:
                    found.append(tuple(sorted(members)))
    return tuple(sorted(found, key=lambda c: (-len(c), c)))


def component_edges(
    component: Collection[str], relation: Mapping[tuple[str, str], Collection[ImportEdge]]
) -> tuple[tuple[str, str, int], ...]:
    """Return a component's internal edges and the import statements behind each, lightest first.

    The lightest edges are the cheap cuts a finding can name. A minimum feedback arc
    set is NP-hard, so these are candidates, never an optimum (Design section 1).
    """
    members = set(component)
    weighted = [
        (source, target, len({(edge.path, edge.line) for edge in found}))
        for (source, target), found in relation.items()
        if source in members and target in members
    ]
    return tuple(sorted(weighted, key=lambda e: (e[2], e[0], e[1])))


# -- the accepted relation (D6) ----------------------------------------------------


@dataclass(frozen=True, order=True)
class AcceptedEdge:
    """One row of ``modularity-layering.yaml``."""

    source: str
    target: str
    relation: str
    finding: str | None = field(default=None, compare=False)


def _rows(path: Path, key: str) -> list[object]:
    """Return the list under ``key`` of ``modularity-layering.yaml``, refusing any other shape."""
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    rows = document.get(key) if isinstance(document, dict) else None
    if not isinstance(rows, list):
        raise ValueError(f"{path}: expected a mapping with a {key!r} list")
    return rows


def accepted_relation(path: Path = LAYERING) -> tuple[AcceptedEdge, ...]:
    """Read the accepted subpackage relation (D6).

    Raises
    ------
    ValueError
        If a row lacks a key, names an unknown relation, or repeats an edge.
    """
    accepted: list[AcceptedEdge] = []
    seen: set[tuple[str, str, str]] = set()
    for number, row in enumerate(_rows(path, "edges"), start=1):
        if not isinstance(row, dict) or set(row) != {"from", "to", "relation", "finding"}:
            raise ValueError(f"{path}: edge {number} needs exactly from, to, relation and finding")
        if row["relation"] not in RELATIONS:
            raise ValueError(
                f"{path}: edge {number} has relation {row['relation']!r}; "
                f"expected one of {', '.join(RELATIONS)}"
            )
        key = (str(row["from"]), str(row["to"]), str(row["relation"]))
        if key in seen:
            raise ValueError(f"{path}: edge {number} repeats {key[0]} -> {key[1]} ({key[2]})")
        seen.add(key)
        finding = row["finding"]
        accepted.append(AcceptedEdge(*key, None if finding is None else str(finding)))
    return tuple(accepted)


@dataclass(frozen=True)
class Comparison:
    """The difference between the measured and the accepted relation."""

    added: tuple[tuple[str, tuple[str, str], ImportEdge], ...]
    """``(relation, edge, first import)`` measured and not accepted."""
    removed: tuple[tuple[str, tuple[str, str]], ...]
    """``(relation, edge)`` accepted and not measured."""

    @property
    def equal(self) -> bool:
        """Whether the two relations agree in both directions."""
        return not self.added and not self.removed

    def describe(self, path: Path = LAYERING) -> str:
        """Return a diagnostic naming each differing edge, its import and the file to edit."""
        lines = []
        for relation, (source, target), edge in self.added:
            # The ratchet's lists only shrink (section 8.2.8 H11, H12; WP37 D12), so
            # an upward edge is never fixed by recording it.
            remedy = (
                f"The {relation}: list of {path.name} only shrinks: cut the dependency by "
                "moving the definition down, passing it in as an argument, or putting an "
                "annotation-only import under TYPE_CHECKING; a deferred import is not a cut"
                if relation in RATCHETS
                else f"Remove the import, or record the edge in {path.name}"
            )
            lines.append(
                f"new {relation} edge {source} -> {target}: {edge.path}:{edge.line} imports "
                f"{edge.target} ({edge.kind}). {remedy}"
            )
        for relation, (source, target) in self.removed:
            lines.append(
                f"removed {relation} edge {source} -> {target}: no import makes it any more. "
                f"Delete its row from {path.name}"
            )
        return "\n".join(lines)


def compare(
    measured: Mapping[str, Mapping[tuple[str, str], Collection[ImportEdge]]],
    accepted: Iterable[AcceptedEdge],
) -> Comparison:
    """Compare the measured relations with the accepted rows, in both directions (D5)."""
    rows = {(edge.relation, (edge.source, edge.target)) for edge in accepted}
    added = []
    for relation, pairs in measured.items():
        for pair, found in pairs.items():
            if (relation, pair) not in rows:
                added.append((relation, pair, min(found, key=_place)))
    measured_pairs = {(relation, pair) for relation, pairs in measured.items() for pair in pairs}
    removed = sorted(rows - measured_pairs)
    return Comparison(tuple(sorted(added, key=lambda a: (a[0], a[1]))), tuple(removed))


# -- the upward ratchet (VER-61, section 8.2.8 H11) ---------------------------------

UPWARD = "upward"
"""The relation name :func:`compare` reports an upward ``top`` edge under."""

DEFERRED_UPWARD = "deferred_upward"
"""The relation name :func:`compare` reports an upward ``deferred`` edge under (H12)."""

RATCHETS: dict[str, tuple[str, ...]] = {UPWARD: ("top",), DEFERRED_UPWARD: ("deferred",)}
"""Each ratchet list of ``modularity-layering.yaml`` and the import kinds it records.

An import moved into a function is not a cut (WP37 D12), and the static relation
cannot tell it from the ``TYPE_CHECKING`` import it may replace, so the deferred
upward edges are recorded too and only shrink (section 8.2.8 H12).
"""


def upward_edges(
    edges: Iterable[ImportEdge],
    order: Sequence[str] = LAYER_ORDER,
    *,
    kinds: Collection[str] = ("top",),
) -> dict[tuple[str, str], tuple[ImportEdge, ...]]:
    """Return the subpackage edges of ``kinds`` that point up ``order``, with their imports.

    Raises
    ------
    ValueError
        If an edge has a node ``order`` does not place: a new subpackage needs a
        place in the order before its edges can be judged.
    """
    rank = {node: position for position, node in enumerate(order)}
    relation = subpackage_relation(edges, kinds=kinds)
    unplaced = sorted({node for pair in relation for node in pair} - set(rank))
    if unplaced:
        raise ValueError(
            f"{', '.join(unplaced)} has no place in the layer order; add it to LAYER_ORDER "
            "and to the header of modularity-layering.yaml"
        )
    return {pair: found for pair, found in relation.items() if rank[pair[0]] < rank[pair[1]]}


def accepted_upward(path: Path = LAYERING, ratchet: str = UPWARD) -> tuple[AcceptedEdge, ...]:
    """Read one recorded ratchet list, ``upward:`` by default (VER-61).

    Raises
    ------
    ValueError
        If ``ratchet`` is not one of :data:`RATCHETS`, or a row lacks a key or
        repeats an edge.
    """
    if ratchet not in RATCHETS:
        raise ValueError(f"{ratchet!r} is not a ratchet; expected one of {', '.join(RATCHETS)}")
    label = ratchet.replace("_", " ")
    accepted: list[AcceptedEdge] = []
    seen: set[tuple[str, str]] = set()
    for number, row in enumerate(_rows(path, ratchet), start=1):
        if not isinstance(row, dict) or set(row) != {"from", "to", "finding"}:
            raise ValueError(f"{path}: {label} edge {number} needs exactly from, to and finding")
        pair = (str(row["from"]), str(row["to"]))
        if pair in seen:
            raise ValueError(f"{path}: {label} edge {number} repeats {pair[0]} -> {pair[1]}")
        seen.add(pair)
        finding = row["finding"]
        accepted.append(AcceptedEdge(*pair, ratchet, None if finding is None else str(finding)))
    return tuple(accepted)


# -- stage conformance (D8 b) ------------------------------------------------------


@dataclass(frozen=True)
class StageConformance:
    """How one registered stage's class meets the :class:`~nanopnp.core.stages.Stage` protocol."""

    name: str
    target: str
    has_describe: bool
    run_signature: str | None
    """``run``'s parameters as :func:`_signature` writes them, or ``None`` if it has none."""
    key_signature: str | None
    """``key``'s parameters as :func:`_signature` writes them, or ``None`` if it has none."""

    @property
    def has_key(self) -> bool:
        """Whether the class defines ``key``, whatever its parameters."""
        return self.key_signature is not None

    @property
    def has_run(self) -> bool:
        """Whether the class defines ``run``, whatever its parameters."""
        return self.run_signature is not None

    @property
    def conforms(self) -> bool:
        """Whether ``describe``, ``key`` and ``run`` exist with the protocol's parameters."""
        return (
            self.has_describe
            and self.key_signature == STAGE_KEY
            and self.run_signature == STAGE_RUN
        )


@dataclass(frozen=True)
class StageSet:
    """A collection of stage names written into the walk rather than read from a stage."""

    path: str
    name: str
    line: int
    members: tuple[str, ...]


def _module_map(modules: Iterable[Module]) -> dict[str, Module]:
    """Index modules by dotted name and by path.

    This module names the modules it reads by path, never as a dotted ``nanopnp``
    name: one would be a ``string`` edge of the relation it measures.
    """
    return {key: module for module in modules for key in (module.name, module.path)}


def _assignment(node: ast.stmt) -> tuple[str, ast.expr] | None:
    """Return ``(name, value)`` of a module-level assignment to one name, else ``None``."""
    if isinstance(node, ast.Assign) and len(node.targets) == 1:
        target: ast.expr = node.targets[0]
    elif isinstance(node, ast.AnnAssign) and node.value is not None:
        target = node.target
    else:
        return None
    if not isinstance(target, ast.Name) or node.value is None:
        return None
    return target.id, node.value


def _registered_stages(stages: Module) -> list[tuple[str, str]]:
    """Return ``(name, target)`` of every ``register(StageDescription(name=...), target)`` call."""
    found = []
    for node in ast.walk(stages.tree):
        if not (isinstance(node, ast.Call) and _called(node) == "register" and len(node.args) >= 2):
            continue
        description, target = node.args[0], node.args[1]
        if not (isinstance(target, ast.Constant) and isinstance(target.value, str)):
            continue
        if isinstance(description, ast.Call):
            for keyword in description.keywords:
                if keyword.arg == "name" and isinstance(keyword.value, ast.Constant):
                    found.append((str(keyword.value.value), target.value))
    return found


def _called(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""


def _class_methods(
    modules: Mapping[str, Module], module_name: str, class_name: str, seen: set[str] | None = None
) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    """Return a class's methods, its own over those of bases this package defines."""
    seen = seen if seen is not None else set()
    module = modules.get(module_name)
    if module is None or f"{module_name}:{class_name}" in seen:
        return {}
    seen.add(f"{module_name}:{class_name}")
    definition = next(
        (
            node
            for node in module.tree.body
            if isinstance(node, ast.ClassDef) and node.name == class_name
        ),
        None,
    )
    if definition is None:
        return {}
    methods: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    # Local name -> (home module, the name the home defines): a base imported
    # ``as`` another name is looked up under its own.
    imported = {
        alias.asname or alias.name: (node.module, alias.name)
        for node in module.tree.body
        if isinstance(node, ast.ImportFrom) and node.module and _in_package(node.module)
        for alias in node.names
    }
    for base in definition.bases:
        if isinstance(base, ast.Name):
            home, defined = imported.get(base.id, (module_name, base.id))
            methods.update(_class_methods(modules, home, defined, seen))
    for node in definition.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            methods[node.name] = node
    return methods


def _signature(function: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Return a method's parameters less ``self``, as ``(a, b, *, c)``."""
    arguments = function.args
    positional = [a.arg for a in [*arguments.posonlyargs, *arguments.args]][1:]
    parts = list(positional)
    if arguments.vararg is not None:
        parts.append(f"*{arguments.vararg.arg}")
    elif arguments.kwonlyargs:
        parts.append("*")
    parts += [a.arg for a in arguments.kwonlyargs]
    if arguments.kwarg is not None:
        parts.append(f"**{arguments.kwarg.arg}")
    return f"({', '.join(parts)})"


def stage_conformance(
    root: Path | None = None, sources: Mapping[str, str] | None = None
) -> tuple[StageConformance, ...]:
    """Return each registered stage's protocol members and the signatures of ``key`` and ``run``."""
    modules = _module_map(parse_package(root, sources))
    found = []
    for name, target in _registered_stages(modules["core/stages.py"]):
        module_name, _, class_name = target.partition(":")
        methods = _class_methods(modules, module_name, class_name)
        run = methods.get("run")
        key = methods.get("key")
        found.append(
            StageConformance(
                name=name,
                target=target,
                has_describe="describe" in methods,
                run_signature=None if run is None else _signature(run),
                key_signature=None if key is None else _signature(key),
            )
        )
    return tuple(found)


@dataclass(frozen=True)
class UndeclaredRead:
    """A stage reading an upstream artefact by a literal name its description does not declare."""

    stage: str
    name: str
    path: str
    line: int

    def describe(self) -> str:
        """Return the diagnostic: the stage, the name, and where it is read."""
        return (
            f"stage {self.stage!r} reads the {self.name!r} artefact at {self.path}:{self.line} "
            f"and does not declare it among its inputs; the walk hands a stage only what it "
            f"declares (WP38 D11), so declare {self.name!r} in core/stages.py, as optional "
            "if a case can drop it"
        )


def undeclared_reads(
    root: Path | None = None, sources: Mapping[str, str] | None = None
) -> tuple[UndeclaredRead, ...]:
    """Return each literal upstream read a registered stage makes without declaring it.

    A read is ``inputs.require("x")``, ``inputs.upstream.get("x")`` or
    ``inputs.upstream["x"]``, on any receiver, in a method of the stage's class
    or in a function of its module those methods call, transitively. A stage's
    own name is admitted: the deviations pass hands a stage its own artefact. A
    read whose name is not a literal is not judged here; the walk's filtering
    starves it of an undeclared input whatever the name (REV-63).
    """
    modules = _module_map(parse_package(root, sources))
    stages = modules["core/stages.py"]
    found: list[UndeclaredRead] = []
    for name, target, declared in _registered_inputs(stages):
        module_name, _, class_name = target.partition(":")
        module = modules.get(module_name)
        if module is None:
            continue
        for literal, line in _reads_reaching(
            module, _class_methods(modules, module_name, class_name)
        ):
            if literal not in declared and literal != name:
                found.append(UndeclaredRead(name, literal, module.path, line))
    return tuple(sorted(found, key=lambda read: (read.stage, read.path, read.line)))


def _registered_inputs(stages: Module) -> list[tuple[str, str, frozenset[str]]]:
    """Return ``(name, target, inputs)`` of every registration, read from its description."""
    found = []
    for node in ast.walk(stages.tree):
        if not (isinstance(node, ast.Call) and _called(node) == "register" and len(node.args) >= 2):
            continue
        description, target = node.args[0], node.args[1]
        if not (isinstance(target, ast.Constant) and isinstance(target.value, str)):
            continue
        if not isinstance(description, ast.Call):
            continue
        facts = {keyword.arg: keyword.value for keyword in description.keywords}
        name, inputs = facts.get("name"), facts.get("inputs")
        if isinstance(name, ast.Constant) and isinstance(inputs, ast.Tuple):
            declared = frozenset(
                str(item.value) for item in inputs.elts if isinstance(item, ast.Constant)
            )
            found.append((str(name.value), target.value, declared))
    return found


def _reads_reaching(
    module: Module, methods: Mapping[str, ast.FunctionDef | ast.AsyncFunctionDef]
) -> list[tuple[str, int]]:
    """Return ``(name, line)`` of every literal upstream read the methods reach in ``module``."""
    functions = {
        node.name: node
        for node in module.tree.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
    }
    pending: list[ast.AST] = list(methods.values())
    visited: set[int] = set()
    reads: list[tuple[str, int]] = []
    while pending:
        body = pending.pop()
        if id(body) in visited:
            continue
        visited.add(id(body))
        for node in ast.walk(body):
            literal = _upstream_literal(node)
            if literal is not None:
                reads.append((literal, getattr(node, "lineno", 0)))
            if isinstance(node, ast.Call):
                callee = node.func
                if isinstance(callee, ast.Name) and callee.id in functions:
                    pending.append(functions[callee.id])
                elif (
                    isinstance(callee, ast.Attribute)
                    and isinstance(callee.value, ast.Name)
                    and callee.value.id == "self"
                    and callee.attr in methods
                ):
                    pending.append(methods[callee.attr])
    return reads


def _upstream_literal(node: ast.AST) -> str | None:
    """Return the literal name an upstream read takes, or ``None`` if ``node`` is none."""
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.args:
        first = node.args[0]
        if not (isinstance(first, ast.Constant) and isinstance(first.value, str)):
            return None
        if node.func.attr == "require":
            return first.value
        receiver = node.func.value
        if node.func.attr == "get" and isinstance(receiver, ast.Attribute):
            return first.value if receiver.attr == "upstream" else None
    if (
        isinstance(node, ast.Subscript)
        and isinstance(node.value, ast.Attribute)
        and node.value.attr == "upstream"
        and isinstance(node.slice, ast.Constant)
        and isinstance(node.slice.value, str)
    ):
        return node.slice.value
    return None


def stage_sets(
    root: Path | None = None,
    sources: Mapping[str, str] | None = None,
    module: str = "pipeline/run.py",
) -> tuple[StageSet, ...]:
    """Return the module-level collections of two or more stage names in ``module``.

    Each one is knowledge about the stages that the walk holds instead of the stages
    (WP35 Design section 4, seed 2).
    """
    modules = _module_map(parse_package(root, sources))
    names = {name for name, _ in _registered_stages(modules["core/stages.py"])}
    names.add("case")
    found = []
    for node in modules[module].tree.body:
        assigned = _assignment(node)
        if assigned is None:
            continue
        name, value = assigned
        strings = [
            str(c.value)
            for c in ast.walk(value)
            if isinstance(c, ast.Constant) and isinstance(c.value, str)
        ]
        if len(strings) >= 2 and all(s in names for s in strings):
            found.append(StageSet(modules[module].path, name, node.lineno, tuple(strings)))
    return tuple(found)


def function_literals(
    names: Collection[str],
    function: str,
    root: Path | None = None,
    sources: Mapping[str, str] | None = None,
    module: str = "pipeline/run.py",
) -> tuple[tuple[str, int], ...]:
    """Return ``(literal, line)`` of each string in ``names`` that ``function`` writes."""
    modules = _module_map(parse_package(root, sources))
    for node in modules[module].tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == function:
            return tuple(
                sorted((str(c.value), c.lineno) for c in _strings(node) if c.value in names)
            )
    raise KeyError(f"{module} defines no function {function!r}")


# -- extension points (D8 c) -------------------------------------------------------


@dataclass(frozen=True)
class ExtensionPoint:
    """A registry or a closed branch, with the modules outside its home that spell a member."""

    name: str
    kind: str
    """``registry`` (members registered by a call) or ``branch`` (members written in a literal)."""
    home: str
    """The module that defines the members, relative to the package directory."""
    members: tuple[str, ...]
    """Every member except ``none``, which every switch takes."""
    spelled: tuple[tuple[str, int], ...]
    """``(module path, literal count)`` per module outside the home spelling a member."""

    @property
    def spelling_modules(self) -> int:
        """The number of modules outside the home that spell a member."""
        return len(self.spelled)


@dataclass(frozen=True)
class _Point:
    name: str
    kind: str
    home: str
    how: str
    """How the members are read: ``stages``, ``call:<registering function>``,
    ``assign:<module-level name>``, ``literal:<annotated attribute>``, or
    ``files:<directory under data/>``, whose YAML stems are the members."""


EXTENSION_POINTS: tuple[_Point, ...] = (
    _Point("stages", "registry", "core/stages.py", "stages"),
    _Point("corrections", "registry", "materials/models.py", "files:corrections"),
    _Point("physics models", "registry", "physics/models.py", "call:register_model"),
    _Point("stabilisation", "registry", "physics/stabilisation.py", "call:register"),
    _Point("charge forms", "registry", "charge/fields.py", "call:register_form"),
    _Point("mesher", "registry", "mesh/meshers.py", "call:register_mesher"),
    _Point("linear solver", "registry", "numerics/linear.py", "call:register_solver"),
    _Point("outputs", "branch", "io/case.py", "assign:OUTPUTS"),
    _Point("steric models", "branch", "io/case.py", "assign:STERIC_MODELS"),
    _Point("correction forms", "branch", "materials/forms.py", "assign:FORMS"),
)
"""The registries and the branches WP35 D8 (c) measures, and how each one's members are read."""


def _members(module: Module, how: str, data: Path) -> tuple[str, ...]:
    mode, _, name = how.partition(":")
    found: list[str] = []
    if mode == "stages":
        found = [stage for stage, _ in _registered_stages(module)]
    elif mode == "call":
        for node in module.tree.body:
            if (
                isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Call)
                and _called(node.value) == name
                and node.value.args
                and isinstance(node.value.args[0], ast.Constant)
            ):
                found.append(str(node.value.args[0].value))
    elif mode == "assign":
        for statement in module.tree.body:
            assigned = _assignment(statement)
            if assigned is None or assigned[0] != name:
                continue
            value = assigned[1]
            keys = value.keys if isinstance(value, ast.Dict) else [value]
            found = [
                str(c.value)
                for key in keys
                if key is not None
                for c in ast.walk(key)
                if isinstance(c, ast.Constant) and isinstance(c.value, str)
            ]
    elif mode == "files":
        found = [path.stem for path in sorted((data / name).glob("*.yaml"))]
    elif mode == "literal":
        for item in ast.walk(module.tree):
            if (
                isinstance(item, ast.AnnAssign)
                and isinstance(item.target, ast.Name)
                and item.target.id == name
            ):
                found += [
                    str(c.value)
                    for c in ast.walk(item.annotation)
                    if isinstance(c, ast.Constant) and isinstance(c.value, str)
                ]
    return tuple(dict.fromkeys(member for member in found if member != "none"))


def extension_points(
    root: Path | None = None, sources: Mapping[str, str] | None = None
) -> tuple[ExtensionPoint, ...]:
    """Return each registry and branch, its members, and who else spells them (D8 c).

    The literal count is the measurable form of QR-14's "only one class or one file":
    a module outside the home that writes a member's name is a module a new member
    may have to be added to.
    """
    modules = parse_package(root, sources)
    by_name = _module_map(modules)
    data = (root or PACKAGE).resolve().parents[1] / "data"
    points = []
    for point in EXTENSION_POINTS:
        home = by_name[point.home]
        members = frozenset(_members(home, point.how, data))
        spelled = []
        for module in modules:
            if module.path == point.home or module.name == __name__:
                continue
            count = sum(1 for value, _ in _module_strings(module) if value in members)
            if count:
                spelled.append((module.path, count))
        points.append(
            ExtensionPoint(
                point.name,
                point.kind,
                home.path,
                tuple(sorted(members)),
                tuple(sorted(spelled, key=lambda s: (-s[1], s[0]))),
            )
        )
    return tuple(points)


# -- the backend (D8 d) ------------------------------------------------------------


@dataclass(frozen=True, order=True)
class BackendImport:
    """One reference to ``ngsolve`` or ``netgen`` from a module of the package."""

    node: str
    """The importing module's subpackage."""
    path: str
    """The importing module's file, relative to the package directory."""
    line: int
    kind: str
    """One of :data:`KINDS`; ``string`` is a constant matching :data:`BACKEND_STRING`."""
    target: str
    """The backend module or ``module:attribute`` named."""


@dataclass(frozen=True)
class BackendUse:
    """Who imports the finite-element backend, and whether section 5.4.1's interface exists."""

    imports: tuple[BackendImport, ...]
    """Every reference to the backend, in any of the four kinds, by path and line."""
    interface: tuple[str, ...]
    """The names of :data:`BACKEND_INTERFACE` the package defines at module level."""

    @property
    def modules(self) -> dict[str, tuple[str, ...]]:
        """Per subpackage, the modules referring to the backend, sorted."""
        found: dict[str, set[str]] = defaultdict(set)
        for reference in self.imports:
            found[reference.node].add(reference.path)
        return {node: tuple(sorted(paths)) for node, paths in sorted(found.items())}

    @property
    def module_count(self) -> int:
        """The number of modules referring to the backend."""
        return sum(len(found) for found in self.modules.values())


def backend_imports(
    root: Path | None = None, sources: Mapping[str, str] | None = None
) -> BackendUse:
    """Return every reference to NGSolve or Netgen, with its path, line and kind (QR-13, VER-65)."""
    modules = parse_package(root, sources)
    found: set[BackendImport] = set()
    defined: set[str] = set()
    for module in modules:
        node = node_of(module.name)
        for statement, kind in _scoped_imports(module.tree):
            if isinstance(statement, ast.Import):
                names = [alias.name for alias in statement.names]
            elif statement.module and not statement.level:
                names = [statement.module]
            else:
                names = []
            for name in names:
                if name.split(".")[0] in BACKEND_PACKAGES:
                    found.add(BackendImport(node, module.path, statement.lineno, kind, name))
        for text, line in _module_strings(module):
            if BACKEND_STRING.match(text):
                found.add(BackendImport(node, module.path, line, "string", text))
        defined |= {
            statement.name
            for statement in module.tree.body
            if isinstance(statement, ast.ClassDef | ast.FunctionDef)
        }
    return BackendUse(
        tuple(sorted(found)),
        tuple(name for name in BACKEND_INTERFACE if name in defined),
    )


def accepted_backend(path: Path = LAYERING) -> tuple[str, ...]:
    """Read the recorded subpackages that reach the backend, the ``backend:`` list (VER-65).

    Raises
    ------
    ValueError
        If an entry is not a subpackage name or repeats one.
    """
    recorded: list[str] = []
    for number, row in enumerate(_rows(path, "backend"), start=1):
        if not isinstance(row, str):
            raise ValueError(f"{path}: backend entry {number} is not a subpackage name")
        if row in recorded:
            raise ValueError(f"{path}: backend entry {number} repeats {row}")
        recorded.append(row)
    return tuple(recorded)


@dataclass(frozen=True)
class BackendComparison:
    """The difference between the subpackages reaching the backend and the record (VER-65)."""

    gained: tuple[BackendImport, ...]
    """The first reference of each subpackage that reaches the backend and is not recorded."""
    lost: tuple[str, ...]
    """Recorded subpackages that no longer reach the backend."""

    @property
    def equal(self) -> bool:
        """Whether the live set and the record agree in both directions."""
        return not self.gained and not self.lost

    def describe(self, path: Path = LAYERING) -> str:
        """Return a diagnostic naming each gain's module and line, and each loss's subpackage."""
        lines = [
            f"{reference.node} now reaches the finite-element backend: {reference.path}:"
            f"{reference.line} names {reference.target} ({reference.kind}). Section 5.4.1 keeps "
            "NGSolve behind the backend interface (QR-13): move the code below one of the "
            f"recorded subpackages, or record {reference.node} under backend: in {path.name}"
            for reference in self.gained
        ]
        lines += [
            f"{node} no longer reaches the finite-element backend. Delete it from backend: "
            f"in {path.name}, so the record shrinks with the code"
            for node in self.lost
        ]
        return "\n".join(lines)


def compare_backend(use: BackendUse, recorded: Iterable[str]) -> BackendComparison:
    """Compare the subpackages reaching the backend with the record, in both directions."""
    expected = set(recorded)
    first: dict[str, BackendImport] = {}
    for reference in use.imports:
        if reference.node not in expected and reference.node not in first:
            first[reference.node] = reference
    return BackendComparison(
        tuple(first[node] for node in sorted(first)),
        tuple(sorted(expected - set(use.modules))),
    )


# -- the public surface (D8 e) -----------------------------------------------------


@dataclass(frozen=True)
class Surface:
    """``PUBLIC``, its hand-kept ``TYPE_CHECKING`` mirror, and names a user reaches outside it."""

    public: tuple[str, ...]
    mirror: tuple[str, ...]
    outside: tuple[str, ...]
    """Of ``with_section`` and ``core.stages.register``, those not in ``PUBLIC`` (WP34 D9)."""
    public_modules: tuple[tuple[str, str], ...] = ()
    """``(name, module)`` as ``PUBLIC`` writes each name's defining module."""
    mirror_modules: tuple[tuple[str, str], ...] = ()
    """``(name, module)`` as the mirror imports each name (REV-54, WP38 D12)."""

    @property
    def mirror_differs(self) -> tuple[str, ...]:
        """Names in exactly one of ``PUBLIC`` and its mirror."""
        return tuple(sorted(set(self.public) ^ set(self.mirror)))

    @property
    def module_differs(self) -> tuple[tuple[str, str, str], ...]:
        """``(name, PUBLIC's module, the mirror's module)`` for each name the two place apart.

        A name mirrored from the module it used to live in type-checks against
        a definition ``PUBLIC`` no longer resolves to (REV-54).
        """
        imported = dict(self.mirror_modules)
        return tuple(
            (name, module, imported[name])
            for name, module in sorted(self.public_modules)
            if name in imported and imported[name] != module
        )


def surface(root: Path | None = None, sources: Mapping[str, str] | None = None) -> Surface:
    """Return the public surface as ``core/public.py`` and the facade write it."""
    modules = _module_map(parse_package(root, sources))
    init = modules.get(ROOT_NODE)
    public_mod = modules.get(f"{ROOT_NODE}.core.public")
    public: list[tuple[str, str]] = []
    mirror: list[tuple[str, str]] = []

    nodes_for_public: list[ast.stmt] = []
    if public_mod is not None:
        nodes_for_public.extend(public_mod.tree.body)
    if init is not None:
        nodes_for_public.extend(init.tree.body)

    for node in nodes_for_public:
        assigned = _assignment(node)
        if assigned is not None and assigned[0] == "PUBLIC" and isinstance(assigned[1], ast.Dict):
            public = [
                (str(key.value), str(value.value) if isinstance(value, ast.Constant) else "")
                for key, value in zip(assigned[1].keys, assigned[1].values, strict=True)
                if isinstance(key, ast.Constant)
            ]
            break

    if init is not None:
        for node in init.tree.body:
            if isinstance(node, ast.If) and _is_type_checking(node.test):
                mirror = [
                    (alias.asname or alias.name, statement.module or "")
                    for statement in node.body
                    if isinstance(statement, ast.ImportFrom)
                    for alias in statement.names
                ]
    names = tuple(name for name, _ in public)
    outside = tuple(name for name in ("with_section", "register") if name not in names)
    return Surface(
        names,
        tuple(name for name, _ in mirror),
        outside,
        public_modules=tuple(public),
        mirror_modules=tuple(mirror),
    )


# -- size and version literals (D8 f, g) ---------------------------------------------


@dataclass(frozen=True)
class Sizes:
    """Lines per module and the longest functions."""

    modules: tuple[tuple[str, int], ...]
    """``(path, lines)``, longest first."""
    functions: tuple[tuple[str, str, int], ...]
    """``(path, qualified name, lines)``, longest first."""


def sizes(root: Path | None = None, sources: Mapping[str, str] | None = None) -> Sizes:
    """Return every module's line count and every function's, longest first (D8 f)."""
    modules = parse_package(root, sources)
    functions: list[tuple[str, str, int]] = []
    for module in modules:
        stack: list[tuple[ast.AST, str]] = [(module.tree, "")]
        while stack:
            node, prefix = stack.pop()
            for child in ast.iter_child_nodes(node):
                if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                    name = f"{prefix}{child.name}"
                    if not isinstance(child, ast.ClassDef):
                        length = (child.end_lineno or child.lineno) - child.lineno + 1
                        functions.append((module.path, name, length))
                    stack.append((child, f"{name}."))
                else:
                    # A definition under ``if``, ``try`` or ``with`` keeps its scope's prefix.
                    stack.append((child, prefix))
    return Sizes(
        tuple(sorted(((m.path, m.lines) for m in modules), key=lambda s: (-s[1], s[0]))),
        tuple(sorted(functions, key=lambda f: (-f[2], f[0], f[1]))),
    )


def version_literals(
    root: Path | None = None, sources: Mapping[str, str] | None = None
) -> tuple[tuple[str, int, str], ...]:
    """Return ``(path, line, text)`` of each non-docstring string naming a release (D8 g)."""
    found = []
    for module in parse_package(root, sources):
        for text, line in _module_strings(module):
            if VERSION_LITERAL.search(text):
                found.append((module.path, line, text))
    return tuple(sorted(found))


# -- the generated page (D1, D7) -----------------------------------------------------


def _matrix(relation: Mapping[tuple[str, str], Collection[ImportEdge]], nodes: list[str]) -> str:
    """Render a relation as a matrix of import-statement counts, rows importing columns.

    A statement importing two modules of one subpackage is two edges and one
    statement, so the count is of ``(path, line)``, as :func:`component_edges` counts.
    """
    counts = Counter(
        {pair: len({_place(edge) for edge in found}) for pair, found in relation.items()}
    )
    header = "| from \\ to | " + " | ".join(f"`{n}`" for n in nodes) + " |"
    rows = [header, "|---|" + "---:|" * len(nodes)]
    for source in nodes:
        cells = [
            str(counts[(source, target)]) if counts[(source, target)] else "" for target in nodes
        ]
        rows.append(f"| `{source}` | " + " | ".join(cells) + " |")
    return "\n".join(rows)


def render_measurements(root: Path | None = None) -> str:
    """Return the live measurements as a Markdown page (D1, D7).

    ``docs/scripts/generate.py`` writes it to
    ``docs/_generated/project/modularity-measurements.md``. The report quotes the
    numbers of one commit; this page is the same measurement on the tree it is built
    from.
    """
    edges = import_edges(root)
    relations = measured_relations(edges)
    nodes = sorted({node_of(m.name) for m in parse_package(root)})
    out = [
        "# Modularity measurements",
        "",
        "Generated by `nanopnp.validation.modularity.render_measurements` from the source tree",
        "this site was built from. The [modularity report](../../project/modularity.md) quotes",
        "these measurements at a named commit; VER-61 pins the static and string relations.",
        "",
        "## Import relation",
        "",
        f"{len(edges)} import edges between `nanopnp` modules, by kind: "
        + ", ".join(f"{kind} {sum(1 for e in edges if e.kind == kind)}" for kind in KINDS)
        + ". Measured by `import_edges` and `subpackage_relation`.",
        "",
        "### Static relation (`top`, `deferred` and `typing`)",
        "",
        "Each cell counts the import statements by which the row's subpackage imports the "
        "column's.",
        "",
        _matrix(relations["static"], nodes),
        "",
        "### String relation",
        "",
        _matrix(relations["string"], nodes),
        "",
        "### Strongly connected components",
        "",
        "Measured by `components`. Each lists its internal edges, the number of import",
        "statements carrying each, lightest first: those are the candidate cuts.",
        "",
    ]
    for label, kinds in (
        ("top", {"top"}),
        ("runtime (top and deferred)", {"top", "deferred"}),
        ("static", STATIC_KINDS),
        ("static and string", STATIC_KINDS | {"string"}),
    ):
        relation = subpackage_relation(edges, kinds)
        found = components(node_graph(relation))
        out.append(f"- **{label}**: " + ("none" if not found else ""))
        for component in found:
            cuts = component_edges(component, relation)
            out.append(
                f"    - {len(component)} members: "
                + ", ".join(f"`{m}`" for m in component)
                + ". Lightest edges: "
                + ", ".join(f"`{s} → {t}` ({n})" for s, t, n in cuts[:6])
            )
    cycles = components(module_graph(edges, {"top"}, packages=True))
    out += [
        "",
        "Module-level cycles among `top` imports, each package `__init__` an import runs "
        f"included: {len(cycles)}.",
        "",
        "## Stage conformance",
        "",
        "Measured by `stage_conformance`, against `Stage.key"
        + STAGE_KEY
        + "` and `Stage.run"
        + STAGE_RUN
        + "`.",
        "",
        "| Stage | Class | `key` signature | `describe` | `run` signature |",
        "|---|---|---|---|---|",
    ]
    for stage in stage_conformance(root):
        out.append(
            f"| `{stage.name}` | `{stage.target}` | "
            f"{f'`{stage.key_signature}`' if stage.has_key else '**no**'} | "
            f"{'yes' if stage.has_describe else '**no**'} | `{stage.run_signature}` |"
        )
    out += ["", "Stage sets written into `pipeline/run.py`, measured by `stage_sets`:", ""]
    written = stage_sets(root)
    for stage_set in written:
        out.append(f"- `{stage_set.name}` (line {stage_set.line}): {len(stage_set.members)} stages")
    if not written:
        out.append("- none")
    out += [
        "",
        "## Extension points",
        "",
        "Measured by `extension_points`. *Spelled in* counts the modules outside the home that",
        "write a member's name as a string; `none` is not counted.",
        "",
        "| Point | Kind | Home | Members | Spelled in |",
        "|---|---|---|---|---|",
    ]
    for point in extension_points(root):
        out.append(
            f"| {point.name} | {point.kind} | `{point.home}` | {len(point.members)} | "
            f"{point.spelling_modules} |"
        )
    backend = backend_imports(root)
    shown = surface(root)
    size = sizes(root)
    versions = version_literals(root)
    out += [
        "",
        "## The backend (QR-13)",
        "",
        f"{backend.module_count} modules in {len(backend.modules)} subpackages import NGSolve or "
        "Netgen, measured by `backend_imports`. Section 5.4.1 names defined: "
        + (", ".join(f"`{n}`" for n in backend.interface) or "none")
        + ".",
        "",
        "| Subpackage | Modules |",
        "|---|---:|",
        *(f"| `{node}` | {len(paths)} |" for node, paths in backend.modules.items()),
        "",
        "## The public surface",
        "",
        f"`PUBLIC` has {len(shown.public)} names; its `TYPE_CHECKING` mirror has "
        f"{len(shown.mirror)}, differing in "
        + (", ".join(f"`{n}`" for n in shown.mirror_differs) or "none")
        + ". Outside `PUBLIC`: "
        + (", ".join(f"`{n}`" for n in shown.outside) or "none")
        + ". Measured by `surface`.",
        "",
        "## Size",
        "",
        "The ten longest modules and functions, measured by `sizes`.",
        "",
        "| Module | Lines |",
        "|---|---:|",
        *(f"| `{path}` | {lines} |" for path, lines in size.modules[:10]),
        "",
        "| Function | Lines |",
        "|---|---:|",
        *(f"| `{path}` `{name}` | {lines} |" for path, name, lines in size.functions[:10]),
        "",
        "## Version literals",
        "",
        f"{len(versions)} non-docstring strings name a release `v0.N`, measured by "
        "`version_literals`.",
        "",
        *(f"- `{path}:{line}`" for path, line, _ in versions),
        "",
    ]
    return "\n".join(out)

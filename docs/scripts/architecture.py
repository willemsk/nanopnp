"""Render the architecture page of the documentation site from the source tree.

``docs/scripts/generate.py`` writes the page beside the modularity measurements. It reads
``src/nanopnp/`` through ``nanopnp.validation.modularity`` (the syntax trees, the import
edges and the layer order), ``src/nanopnp/core/stages.py`` for the registered stages and
``specification/05-software-design/01-architectural-overview.md`` for the module table of
section 5.1. The page lists, per subpackage, its modules with their lines, public names and
first docstring line, the pipeline stages it implements, and the measured subpackage edges in
and out (static imports, and string references apart); then the diff of that table against
the tree. Read-only: nothing under ``src/`` changes, and nothing is imported but the measuring
module.

Run it as ``uv run docs/scripts/architecture.py`` to print the page.
"""

from __future__ import annotations

import ast
import re
import sys
from collections import defaultdict
from pathlib import Path

from nanopnp.validation.modularity import (
    LAYER_ORDER,
    STATIC_KINDS,
    Module,
    import_edges,
    node_of,
    parse_package,
    subpackage_relation,
)

ROOT = Path(__file__).resolve().parents[2]
OVERVIEW = ROOT / "specification" / "05-software-design" / "01-architectural-overview.md"
STAGES = ROOT / "src" / "nanopnp" / "core" / "stages.py"
TABLE_ROW = re.compile(r"^\|\s*`([a-z_]+)/`\s*\|\s*(.*?)\s*\|\s*$")

Relation = dict[tuple[str, str], list]


def _public_names(tree: ast.Module) -> list[str]:
    names: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            if not node.name.startswith("_"):
                names.append(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and not target.id.startswith("_"):
                    names.append(target.id)
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and not node.target.id.startswith("_")
        ):
            names.append(node.target.id)
    return names


def _summary(tree: ast.Module) -> str:
    docstring = ast.get_docstring(tree)
    return docstring.strip().splitlines()[0] if docstring else "(no docstring)"


def _stages() -> dict[str, list[tuple[int, str, str]]]:
    """Return, per subpackage, each registered stage as (number, name, target)."""
    tree = ast.parse(STAGES.read_text(encoding="utf-8"))
    found: dict[str, list[tuple[int, str, str]]] = defaultdict(list)
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
            continue
        if node.func.id != "register" or len(node.args) != 2:
            continue
        description, target = node.args
        if not (isinstance(description, ast.Call) and isinstance(target, ast.Constant)):
            continue
        number = next((k.value.value for k in description.keywords if k.arg == "number"), None)
        name = next(
            (
                ast.unparse(k.value).rsplit(".", 1)[-1].lower()
                for k in description.keywords
                if k.arg == "name"
            ),
            "?",
        )
        module = str(target.value).partition(":")[0]
        found[node_of(module)].append(
            (int(number) if number is not None else 0, name, str(target.value))
        )
    return {node: sorted(stages) for node, stages in found.items()}


def _overview_rows() -> dict[str, str]:
    rows: dict[str, str] = {}
    for line in OVERVIEW.read_text(encoding="utf-8").splitlines():
        match = TABLE_ROW.match(line)
        if match:
            rows[match.group(1)] = match.group(2)
    return rows


def _escape(text: str) -> str:
    return text.replace("|", "\\|")


def _out_edges(node: str, relation: Relation) -> list[tuple[str, int]]:
    return [(t, len(v)) for (s, t), v in relation.items() if s == node]


def _in_edges(node: str, relation: Relation) -> list[tuple[str, int]]:
    return [(s, len(v)) for (s, t), v in relation.items() if t == node]


def _summary_table(
    nodes: list[str],
    by_node: dict[str, list[Module]],
    stages: dict[str, list[tuple[int, str, str]]],
    static: Relation,
    strings: Relation,
) -> list[str]:
    lines = [
        "| Subpackage | Modules | Lines | Public names | Stages | Static edges out | "
        "Static edges in | String edges out |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for node in nodes:
        mods = by_node[node]
        public = sum(len(_public_names(m.tree)) for m in mods)
        stage_text = ", ".join(f"{n} {name}" for n, name, _ in stages.get(node, [])) or "—"
        counts = (
            len(_out_edges(node, static)),
            len(_in_edges(node, static)),
            len(_out_edges(node, strings)),
        )
        total = sum(m.lines for m in mods)
        lines.append(
            f"| `{node}` | {len(mods)} | {total:,} | {public} | {stage_text} | "
            f"{counts[0]} | {counts[1]} | {counts[2]} |"
        )
    return lines


def _edge_text(label: str, pairs: list[tuple[str, int]]) -> str:
    return f"{label}: " + (", ".join(f"`{t}` ({n})" for t, n in pairs) or "none") + "."


def _module_table(mods: list[Module]) -> list[str]:
    lines = [
        "| Module | Lines | Public names | First docstring line |",
        "|---|---|---|---|",
    ]
    for module in sorted(mods, key=lambda m: m.path):
        names = _public_names(module.tree)
        shown = ", ".join(f"`{n}`" for n in names[:8]) + (
            f" and {len(names) - 8} more" if len(names) > 8 else ""
        )
        summary = _escape(_summary(module.tree))
        lines.append(f"| `{module.path}` | {module.lines} | {shown or '—'} | {summary} |")
    return lines


def _subpackage_sections(
    nodes: list[str],
    by_node: dict[str, list[Module]],
    stages: dict[str, list[tuple[int, str, str]]],
    static: Relation,
    strings: Relation,
) -> list[str]:
    lines: list[str] = []
    for node in nodes:
        lines += [f"### `{node}`", ""]
        if node in stages:
            lines.append(
                "Stages: " + "; ".join(f"{n} `{name}` (`{t}`)" for n, name, t in stages[node]) + "."
            )
            lines.append("")
        lines.append(
            _edge_text("Static imports out", sorted(_out_edges(node, static)))
            + " "
            + _edge_text("Static imports in", sorted(_in_edges(node, static)))
            + " "
            + _edge_text("String references out", sorted(_out_edges(node, strings)))
        )
        lines += ["", *_module_table(by_node[node]), ""]
    return lines


def _overview_section(nodes: list[str], by_node: dict[str, list[Module]]) -> list[str]:
    rows = _overview_rows()
    tree_nodes = {node for node in nodes if node != "nanopnp"}
    missing = sorted(tree_nodes - set(rows))
    extra = sorted(set(rows) - tree_nodes)
    lines = [
        "## The module table of the architectural overview against the tree",
        "",
        f"The overview lists {len(rows)} modules; the tree has {len(tree_nodes)} subpackages.",
        "",
        "In the tree and not in the overview's table: "
        + (", ".join(f"`{n}/`" for n in missing) or "none")
        + ".",
        "In the overview's table and not in the tree: "
        + (", ".join(f"`{n}/`" for n in extra) or "none")
        + ".",
        "",
        "| Module | The overview says | The package docstring says | Modules |",
        "|---|---|---|---|",
    ]
    for node in nodes:
        if node == "nanopnp":
            continue
        package = next((m for m in by_node[node] if m.is_package), None)
        doc = _summary(package.tree) if package else "(no package module)"
        says = _escape(rows.get(node, "(no row)"))
        lines.append(f"| `{node}/` | {says} | {_escape(doc)} | {len(by_node[node])} |")
    return lines


def render() -> str:
    """Return the architecture page as Markdown."""
    modules = parse_package()
    edges = import_edges()
    static = subpackage_relation(edges, STATIC_KINDS)
    strings = subpackage_relation(edges, frozenset({"string"}))
    stages = _stages()
    by_node: dict[str, list[Module]] = defaultdict(list)
    for module in modules:
        by_node[node_of(module.name)].append(module)
    nodes = [node for node in LAYER_ORDER if node in by_node]
    nodes += sorted(node for node in by_node if node not in LAYER_ORDER)

    lines = [
        "# Architecture",
        "",
        "Written by `docs/scripts/architecture.py` from `src/nanopnp/` through "
        "`nanopnp.validation.modularity`, from the stage registry of `core/stages.py` and "
        "from the module table of the architectural overview, on the tree this site was "
        f"built from. {len(modules)} modules, {sum(m.lines for m in modules):,} lines, "
        f"{len(edges)} module-to-module imports, {len(static)} static subpackage edges and "
        f"{len(strings)} string edges. Nodes are in the layer order of the measuring module, "
        "lowest first; `nanopnp` is the package's own `__init__` and `case.py`.",
        "",
        "## Summary",
        "",
        *_summary_table(nodes, by_node, stages, static, strings),
        "",
        "## Each subpackage",
        "",
        *_subpackage_sections(nodes, by_node, stages, static, strings),
        *_overview_section(nodes, by_node),
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    """Print the architecture page to standard output and return the exit status."""
    sys.stdout.write(render())
    return 0


if __name__ == "__main__":
    sys.exit(main())

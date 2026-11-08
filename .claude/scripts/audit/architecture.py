"""Describe the package's architecture from its source, for the written-knowledge audit.

Reads ``src/nanopnp/`` through ``nanopnp.validation.modularity`` (the syntax trees, the import
edges and the layer order), ``src/nanopnp/core/stages.py`` for the registered stages and
``specification/05-software-design/01-architectural-overview.md`` for §5.1's module table.
Writes one Markdown page: per subpackage, its modules with their lines, public names and
first docstring line, the pipeline stages it implements, and the measured subpackage edges in
and out (static imports, and string references apart); then the diff of §5.1's table against
the tree. Read-only: nothing under ``src/`` changes, and nothing is imported but the measuring
module. ``--at`` names the commit the counts belong to.

Run it as ``uv run .claude/scripts/audit/architecture.py --at <sha>``.
"""

from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scope import ROOT

from nanopnp.validation.modularity import (
    LAYER_ORDER,
    STATIC_KINDS,
    Module,
    import_edges,
    node_of,
    parse_package,
    subpackage_relation,
)

ATTACHMENTS = ROOT / "docs" / "code_reviews" / "CODE_REVIEW_039"
OVERVIEW = ROOT / "specification" / "05-software-design" / "01-architectural-overview.md"
STAGES = ROOT / "src" / "nanopnp" / "core" / "stages.py"
TABLE_ROW = re.compile(r"^\|\s*`([a-z_]+)/`\s*\|\s*(.*?)\s*\|\s*$")


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


def render(at: str) -> str:
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

    def out_edges(node: str, relation: dict) -> list[tuple[str, int]]:
        return [(t, len(v)) for (s, t), v in relation.items() if s == node]

    def in_edges(node: str, relation: dict) -> list[tuple[str, int]]:
        return [(s, len(v)) for (s, t), v in relation.items() if t == node]

    lines = [
        "# CODE_REVIEW_039: the architecture as the tree states it",
        "",
        f"Written by `.claude/scripts/audit/architecture.py` at `{at}` from `src/nanopnp/` through "
        "`nanopnp.validation.modularity`, from the stage registry of `core/stages.py` and from "
        f"§5.1's module table. {len(modules)} modules, {sum(m.lines for m in modules):,} lines, "
        f"{len(edges)} module-to-module imports, {len(static)} static subpackage edges and "
        f"{len(strings)} string edges. Nodes are in the layer order of the measuring module, "
        "lowest first; `nanopnp` is the package's own `__init__` and `case.py`.",
        "",
        "## Summary",
        "",
        "| Subpackage | Modules | Lines | Public names | Stages | Static edges out | "
        "Static edges in | String edges out |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for node in nodes:
        mods = by_node[node]
        public = sum(len(_public_names(m.tree)) for m in mods)
        stage_text = ", ".join(f"{n} {name}" for n, name, _ in stages.get(node, [])) or "—"
        counts = (
            len(out_edges(node, static)),
            len(in_edges(node, static)),
            len(out_edges(node, strings)),
        )
        total = sum(m.lines for m in mods)
        lines.append(
            f"| `{node}` | {len(mods)} | {total:,} | {public} | {stage_text} | "
            f"{counts[0]} | {counts[1]} | {counts[2]} |"
        )
    lines += ["", "## Each subpackage", ""]
    for node in nodes:
        mods = sorted(by_node[node], key=lambda m: m.path)
        lines += [f"### `{node}`", ""]
        if node in stages:
            lines.append(
                "Stages: " + "; ".join(f"{n} `{name}` (`{t}`)" for n, name, t in stages[node]) + "."
            )
            lines.append("")
        outs = sorted(out_edges(node, static))
        ins = sorted(in_edges(node, static))
        souts = sorted(out_edges(node, strings))
        lines.append(
            "Static imports out: " + (", ".join(f"`{t}` ({n})" for t, n in outs) or "none") + ". "
            "Static imports in: " + (", ".join(f"`{s}` ({n})" for s, n in ins) or "none") + ". "
            "String references out: "
            + (", ".join(f"`{t}` ({n})" for t, n in souts) or "none")
            + "."
        )
        lines += [
            "",
            "| Module | Lines | Public names | First docstring line |",
            "|---|---|---|---|",
        ]
        for module in mods:
            names = _public_names(module.tree)
            shown = ", ".join(f"`{n}`" for n in names[:8]) + (
                f" and {len(names) - 8} more" if len(names) > 8 else ""
            )
            summary = _escape(_summary(module.tree))
            lines.append(f"| `{module.path}` | {module.lines} | {shown or '—'} | {summary} |")
        lines.append("")
    rows = _overview_rows()
    tree_nodes = {node for node in nodes if node != "nanopnp"}
    lines += [
        "## §5.1's module table against the tree",
        "",
        f"§5.1 lists {len(rows)} modules; the tree has {len(tree_nodes)} subpackages.",
        "",
    ]
    missing = sorted(tree_nodes - set(rows))
    extra = sorted(set(rows) - tree_nodes)
    lines.append(
        "In the tree and not in §5.1's table: "
        + (", ".join(f"`{n}/`" for n in missing) or "none")
        + "."
    )
    lines.append(
        "In §5.1's table and not in the tree: "
        + (", ".join(f"`{n}/`" for n in extra) or "none")
        + "."
    )
    lines += [
        "",
        "| Module | §5.1 says | The package docstring says | Modules |",
        "|---|---|---|---|",
    ]
    for node in nodes:
        if node == "nanopnp":
            continue
        package = next((m for m in by_node[node] if m.is_package), None)
        doc = _summary(package.tree) if package else "(no package module)"
        says = _escape(rows.get(node, "(no row)"))
        lines.append(f"| `{node}/` | {says} | {_escape(doc)} | {len(by_node[node])} |")
    return "\n".join(lines) + "\n"


def _head() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )
    return result.stdout.strip() or "unknown"


def main(argv: list[str] | None = None) -> int:
    """Run the command line and return the process exit status."""
    parser = argparse.ArgumentParser(
        description="Describe the package's architecture from its source."
    )
    parser.add_argument("--at", default=None, help="the commit the counts name (default: HEAD)")
    parser.add_argument("--out", type=Path, default=ATTACHMENTS / "architecture.md")
    arguments = parser.parse_args(argv)
    arguments.out.write_text(render(arguments.at or _head()), encoding="utf-8")
    sys.stdout.write(f"written to {arguments.out.relative_to(ROOT).as_posix()}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Check that changed Python files differ from a git ref only in prose (§8.2.11 L5).

Usage: ``uv run .claude/scripts/same_tree.py <ref> [paths...]``.

Every changed ``.py`` file is compared with its version at ``<ref>``. The syntax trees, after
deleting every bare string statement, ``pass`` and bare ``...``, must be equal, and the multiset
of directive comments must be unchanged. A module that reads ``__doc__`` keeps its first line. A
deleted, added or unparsable file fails. Exit status is 1 on any difference, with the file named
on standard output.
"""

from __future__ import annotations

import ast
import io
import re
import subprocess
import sys
import tokenize
from collections import Counter
from pathlib import Path

_DIRECTIVE = re.compile(r"#\s*(type:|noqa|pragma|fmt:|mypy:|ruff:)|^#!|coding[:=]")


def is_directive(comment: str) -> bool:
    """Return whether a comment token is a directive: a tool marker, a shebang or a coding line."""
    return _DIRECTIVE.search(comment) is not None


class _Strip(ast.NodeTransformer):
    def _body(self, nodes: list[ast.stmt]) -> list[ast.stmt]:
        kept: list[ast.stmt] = []
        for node in nodes:
            if isinstance(node, ast.Pass):
                continue
            if (
                isinstance(node, ast.Expr)
                and isinstance(node.value, ast.Constant)
                and (isinstance(node.value.value, str) or node.value.value is Ellipsis)
            ):
                continue
            kept.append(node)
        return kept

    def generic_visit(self, node: ast.AST) -> ast.AST:
        super().generic_visit(node)
        for field in ("body", "orelse", "finalbody"):
            nodes = getattr(node, field, None)
            if isinstance(nodes, list) and nodes and isinstance(nodes[0], ast.stmt):
                setattr(node, field, self._body(nodes))
        return node


def normalised_tree(source: str) -> str:
    """Return the dump of ``source``'s syntax tree with docstrings, ``pass`` and ``...`` removed."""
    return ast.dump(_Strip().visit(ast.parse(source)), include_attributes=False)


def directives(source: str) -> Counter[str]:
    """Return the multiset of directive comments of ``source``."""
    found: Counter[str] = Counter()
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type == tokenize.COMMENT and is_directive(token.string):
            found[token.string.strip()] += 1
    return found


def _summary(tree: ast.Module) -> str:
    return (ast.get_docstring(tree) or "").split("\n", 1)[0]


def _reads_doc(tree: ast.Module) -> bool:
    return any(isinstance(node, ast.Name) and node.id == "__doc__" for node in ast.walk(tree))


def differences(before: str | None, after: str | None) -> str | None:
    """Return why two versions of a file differ beyond prose, or ``None``."""
    if before is None or after is None:
        return "file added" if before is None else "file deleted"
    try:
        old, new = ast.parse(before), ast.parse(after)
        if normalised_tree(before) != normalised_tree(after):
            return "syntax tree changed"
        if directives(before) != directives(after):
            return "directive comments changed"
    except (SyntaxError, tokenize.TokenError):
        return "does not parse"
    # A module that reads its own __doc__ runs its summary line, as an argparse description.
    if (_reads_doc(old) or _reads_doc(new)) and _summary(old) != _summary(new):
        return "module docstring's first line changed, and the module reads __doc__"
    return None


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True, encoding="utf-8"
    ).stdout


def check(root: Path, ref: str, paths: list[str] | None = None) -> dict[str, str]:
    """Return ``{file: reason}`` for every changed ``.py`` file that is not prose-only."""
    spec = ["--", *paths] if paths else []
    changed = _git(root, "diff", "--name-only", "--no-renames", ref, *spec).split("\n")
    changed += _git(root, "ls-files", "--others", "--exclude-standard", *spec).split("\n")
    failures: dict[str, str] = {}
    for name in sorted({n for n in changed if n.endswith(".py")}):
        shown = subprocess.run(
            ["git", "show", f"{ref}:{name}"],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        before = shown.stdout if shown.returncode == 0 else None
        path = root / name
        after = path.read_text(encoding="utf-8") if path.exists() else None
        reason = differences(before, after)
        if reason:
            failures[name] = reason
    return failures


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__, file=sys.stderr)
        return 2
    root = Path(_git(Path.cwd(), "rev-parse", "--show-toplevel").strip())
    failures = check(root, argv[0], argv[1:] or None)
    for name, reason in failures.items():
        print(f"{name}: {reason}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

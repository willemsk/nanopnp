"""Reconcile the knowledge base's claim markers with the tests and sources they name.

Reads every Markdown file under ``knowledge/`` and the Python under ``tests/``, skipping code spans
and fenced blocks, where a marker is an example of its syntax. Writes one Markdown report to
standard output with four sections: every ``[tested: <test>]`` marker whose test file or
test function does not exist; every concept file whose front-matter ``verified:`` list of
``process:tests/...`` entries differs from the tests its markers name, in either direction; every
``[verified]`` claim with no footnote reference on its line, so that a reader can judge whether
the paragraph's or the concept's footnote covers it; and every ``[verified]`` claim with its
footnote references classified by the source the footnote's definition names (thesis, ESI, paper,
COMSOL report, specification, plan, code or test, other), for the accuracy check against the
thesis. Counts head each section.

Run it as ``uv run .claude/scripts/audit/markers.py``.
"""

from __future__ import annotations

import ast
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scope import ROOT, relative

TESTED = re.compile(r"\[tested:\s*([^\]]+?)\s*\]")
VERIFIED = re.compile(r"\[verified\]")
FOOTREF = re.compile(r"\[\^([^\]]+)\](?!:)")
FOOTDEF = re.compile(r"^\[\^([^\]]+)\]:\s*(.*)$")
FRONT = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
TEST_REF = re.compile(r"^(tests/[\w/.-]+\.py)(?:::([\w\[\]().,:= -]+))?$")
CODE_SPAN = re.compile(r"`[^`\n]*`")
FENCE = re.compile(r"^\s*(```|~~~)")

SOURCE_KINDS: tuple[tuple[str, str], ...] = (
    ("thesis", r"thesis|phdthesis"),
    ("ESI", r"supplementary|suppdata|\bESI\b"),
    ("paper", r"Nanoscale|10\.1039|bioRxiv|10\.1101"),
    ("COMSOL report", r"COMSOL model report|model report \(5\.4\)|COMSOL Multiphysics"),
    ("plan or review", r"docs/plans|docs/code_reviews|docs/design|\bWP\d|work package|\bplan\b"),
    ("code or test", r"tests/|src/|\.py\b|conftest|git show|commit|`[0-9a-f]{7}`"),
    ("specification", r"SPECIFICATION\.md|specification/|§"),
)


def _classify(definition: str) -> str:
    for kind, pattern in SOURCE_KINDS:
        if re.search(pattern, definition, re.I):
            return kind
    return "other"


def _test_functions(path: Path) -> set[str]:
    """Return every test name of a file, bare and as ``Class::method`` where it is a method."""
    names: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    names.add(f"{node.name}::{item.name}")
                    names.add(item.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
    return names


def _front_tests(text: str) -> set[str]:
    match = FRONT.match(text)
    if not match:
        return set()
    return set(re.findall(r"by:\s*process:(tests/\S+)", match.group(1)))


def _prose_lines(lines: list[str]) -> list[str]:
    """Return the lines with inline code spans and fenced blocks blanked, keeping their numbers.

    A marker quoted in code is an example, not a claim: the knowledge base's own provenance pages
    show the markers' syntax in code spans.
    """
    prose: list[str] = []
    fenced = False
    for line in lines:
        if FENCE.match(line):
            fenced = not fenced
            prose.append("")
            continue
        prose.append("" if fenced else CODE_SPAN.sub("", line))
    return prose


def main() -> int:
    """Print the reconciliation report."""
    files = sorted(p for p in (ROOT / "knowledge").rglob("*.md"))
    missing_tests: list[str] = []
    front_mismatch: list[str] = []
    bare_verified: list[str] = []
    classified: list[str] = []
    by_kind: dict[str, int] = defaultdict(int)
    total_tested = total_verified = 0
    function_cache: dict[Path, set[str]] = {}
    for path in files:
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        definitions = {m.group(1): m.group(2) for line in lines if (m := FOOTDEF.match(line))}
        named: set[str] = set()
        for number, (line, shown) in enumerate(zip(_prose_lines(lines), lines, strict=True), 1):
            for match in TESTED.finditer(line):
                ref = match.group(1)
                total_tested += 1
                if ref == "<test>":
                    continue
                named.add(ref)
                parsed = TEST_REF.match(ref)
                if not parsed:
                    missing_tests.append(f"`{relative(path)}:{number}` unparseable marker `{ref}`")
                    continue
                file, function = parsed.group(1), parsed.group(2)
                test_path = ROOT / file
                if not test_path.exists():
                    missing_tests.append(f"`{relative(path)}:{number}` no file `{file}`")
                    continue
                if function:
                    base = re.sub(r"\[.*$", "", function)
                    if test_path not in function_cache:
                        function_cache[test_path] = _test_functions(test_path)
                    if base not in function_cache[test_path]:
                        missing_tests.append(
                            f"`{relative(path)}:{number}` no function `{base}` in `{file}`"
                        )
            for _ in VERIFIED.finditer(line):
                total_verified += 1
                refs = FOOTREF.findall(line)
                if not refs:
                    bare_verified.append(f"`{relative(path)}:{number}`: {shown.strip()[:160]}")
                    continue
                kinds = []
                for ref in refs:
                    definition = definitions.get(ref, "")
                    kind = _classify(definition) if definition else "undefined footnote"
                    kinds.append(f"`[^{ref}]` → {kind}")
                    by_kind[kind] += 1
                classified.append(
                    f"`{relative(path)}:{number}` {'; '.join(kinds)}: {shown.strip()[:120]}"
                )
        front = _front_tests(text)
        marker_tests = {re.sub(r"\[.*$", "", n) for n in named}
        if front != marker_tests:
            only_front = sorted(front - marker_tests)
            only_markers = sorted(marker_tests - front)
            front_mismatch.append(
                f"`{relative(path)}`: in `verified:` only: {only_front or '—'}; "
                f"in markers only: {only_markers or '—'}"
            )
    print("# Claim markers of `knowledge/` reconciled")
    print()
    print(f"`[tested:]` markers: {total_tested}. `[verified]` markers: {total_verified}.")
    print()
    print(f"## `[tested:]` markers whose test does not exist ({len(missing_tests)})")
    print()
    print("\n".join(f"- {m}" for m in missing_tests) or "none")
    print()
    print(
        "## Files whose `verified:` list differs from the tests their markers name "
        f"({len(front_mismatch)})"
    )
    print()
    print("\n".join(f"- {m}" for m in front_mismatch) or "none")
    print()
    print(f"## `[verified]` claims with no footnote reference on their line ({len(bare_verified)})")
    print()
    print("\n".join(f"- {m}" for m in bare_verified) or "none")
    print()
    print("## `[verified]` claims by the source their footnotes name")
    print()
    for kind, n in sorted(by_kind.items(), key=lambda kv: -kv[1]):
        print(f"- {kind}: {n}")
    print()
    print("\n".join(f"- {m}" for m in classified) or "none")
    return 0


if __name__ == "__main__":
    sys.exit(main())

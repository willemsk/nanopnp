"""Build the audit's inventory: every file in scope with what reaches it.

Reads the files ``scope.py`` names, every other Markdown file of the tree outside
``docs/_generated/``, ``mkdocs.yml``'s navigation, and the Python under ``src/`` and ``tests/``.
Writes one Markdown table to standard output, a row per file: path; words; estimated tokens;
``live``, ``record`` or ``out``; the OKF ``type`` of its front matter; whether the site's
navigation lists it (``nav``, ``generated`` for a page the build copies and lists from its
directory's ``index.md``, ``excluded`` for a folder ``mkdocs.yml`` excludes, or ``no``); the
index files that link to it; how many other Markdown files link to or name it; and how many
``src/`` or ``tests/`` files name its path. Totals by folder follow the table.

Run it as ``uv run .claude/scripts/audit/inventory.py``.
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scope import (
    ROOT,
    live_files,
    out_of_scope,
    record_files,
    relative,
    tokens,
    words,
)

LINK = re.compile(r"\[[^\]]*\]\(([^)\s#]+)(?:#[^)]*)?\)")
FRONT = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
INDEX_NAMES = {"index.md", "README.md", "SPECIFICATION.md", "CLAUDE.md", "AGENTS.md", "current.md"}
EXCLUDED_NAV = (
    "docs/plans/",
    "docs/user-testing/",
    "docs/code_reviews/",
    "docs/superpowers/",
    "docs/design/reviews/",
    "docs/design/spike/",
    "docs/design/concepts/",
    "docs/design/style/",
    "docs/design/choices/",
    "docs/design/mockups/",
    "docs/design/generators/",
)


def _okf_type(text: str) -> str:
    match = FRONT.match(text)
    if not match:
        return ""
    for line in match.group(1).splitlines():
        if line.startswith("type:"):
            return line.split(":", 1)[1].strip().strip('"')
    return ""


def _nav_pages() -> set[str]:
    pages: set[str] = set()
    for line in (ROOT / "mkdocs.yml").read_text(encoding="utf-8").splitlines():
        match = re.search(r":\s*([\w./-]+\.md)\s*$", line) or re.match(
            r"\s*-\s*([\w./-]+\.md)\s*$", line
        )
        if match:
            pages.add("docs/" + match.group(1))
    return pages


def _nav_state(path: str, nav: set[str]) -> str:
    if path in nav:
        return "nav"
    if path.startswith(("knowledge/", "specification/")) or path == "SPECIFICATION.md":
        return "generated"
    if path == "CHANGELOG.md" or re.match(r"examples/[^/]+/README\.md$", path):
        return "generated"
    if path.startswith(EXCLUDED_NAV):
        return "excluded"
    return "no"


def _all_markdown() -> list[Path]:
    return sorted(
        p
        for p in ROOT.rglob("*.md")
        if "_generated" not in p.parts and ".venv" not in p.parts and "node_modules" not in p.parts
    )


def main() -> int:  # noqa: C901
    """Print the inventory."""
    live = {relative(p): "live" for p in live_files()}
    records = {relative(p): "record" for p in record_files()}
    out = {relative(p): "out" for p in out_of_scope()}
    kinds = {**out, **records, **live}
    nav = _nav_pages()
    inbound_links: dict[str, set[str]] = defaultdict(set)
    mentions: dict[str, set[str]] = defaultdict(set)
    names = list(kinds)
    basenames = defaultdict(list)
    for p in names:
        basenames[Path(p).name].append(p)
    unique_basename = {Path(p).name: p for p in names if len(basenames[Path(p).name]) == 1}
    for md in _all_markdown():
        source = relative(md)
        text = md.read_text(encoding="utf-8")
        for match in LINK.finditer(text):
            target = match.group(1)
            if re.match(r"^[a-z][a-z0-9+.-]*:", target):
                continue
            resolved = (md.parent / target).resolve()
            try:
                key = resolved.relative_to(ROOT).as_posix()
            except ValueError:
                continue
            if key in kinds and key != source:
                inbound_links[key].add(source)
        for p in names:
            if p != source and p in text:
                mentions[p].add(source)
        for base, p in unique_basename.items():
            if p != source and base in text:
                mentions[p].add(source)
    code = [p for p in [*ROOT.glob("src/**/*.py"), *ROOT.glob("tests/**/*.py")]]
    code_texts = {relative(p): p.read_text(encoding="utf-8") for p in code}
    cited_from_code: dict[str, int] = {}
    for p in kinds:
        cited_from_code[p] = sum(1 for text in code_texts.values() if p in text)
    print("# Inventory of the files in scope")
    print()
    print(
        "Tokens are estimated as characters divided by four. `indexed by` lists the index "
        "files (`index.md`, `README.md`, `SPECIFICATION.md`, `CLAUDE.md`, `AGENTS.md`, "
        "`current.md`) that link to the file; `inbound` counts every other Markdown file that "
        "links to it or names its path; `code` counts the `src/` and `tests/` files naming "
        "its path."
    )
    print()
    print("| Path | Words | Tokens | Kind | OKF type | Site nav | Indexed by | Inbound | Code |")
    print("|---|---|---|---|---|---|---|---|---|")
    totals: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    for p in sorted(kinds):
        full = ROOT / p
        try:
            text = full.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            text = ""
        w, t = words(text), tokens(text)
        folder = "/".join(Path(p).parts[:2]) if len(Path(p).parts) > 1 else "(root)"
        totals[folder][0] += 1
        totals[folder][1] += w
        totals[folder][2] += t
        indexed = sorted(
            s for s in inbound_links[p] if Path(s).name in INDEX_NAMES or "/plans/phase-" in s
        )
        inbound = len((inbound_links[p] | mentions[p]) - set(indexed))
        print(
            f"| `{p}` | {w} | {t} | {kinds[p]} | {_okf_type(text)} | {_nav_state(p, nav)} | "
            f"{', '.join(f'`{s}`' for s in indexed) or '—'} | {inbound} | {cited_from_code[p]} |"
        )
    print()
    print("## Totals by folder")
    print()
    print("| Folder | Files | Words | Tokens |")
    print("|---|---|---|---|")
    for folder, (n, w, t) in sorted(totals.items()):
        print(f"| `{folder}` | {n} | {w} | {t} |")
    n, w, t = (sum(v[i] for v in totals.values()) for i in range(3))
    print(f"| **all** | {n} | {w} | {t} |")
    unreached = [
        p for p in sorted(kinds) if kinds[p] != "out" and not inbound_links[p] and not mentions[p]
    ]
    print()
    print(f"## Files no other Markdown links to or names ({len(unreached)})")
    print()
    for p in unreached:
        print(f"- `{p}` ({kinds[p]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())

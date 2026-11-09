"""Check every relative link of every tracked Markdown file (SPECIFICATION.md §7.6; §8.2.36 AL28).

Reads ``git ls-files '*.md'``, less the attachments of ``docs/code_reviews/CODE_REVIEW_039/``,
which copy links from other folders; writes a Markdown report to standard output: the count of
relative links, then every broken one as ``file:line target``, then, with ``--anchors``, every
anchor that names a heading the target file does not have. A link is relative when it has no
scheme and does not start with ``#``. Code spans and fenced blocks are masked first, as
``docs/scripts/generate.py`` masks them, so an ``a[i](x)`` in code is not a link. A link into
``docs/_generated/`` resolves only after ``docs/scripts/generate.py`` has run, as CI runs it. The
broken links of ``KNOWN`` are records and pass. The exit status is 1 when any other path is
broken.

Run it as ``uv run .claude/scripts/links.py [--anchors]``.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ATTACHMENTS = "docs/code_reviews/CODE_REVIEW_039/"
LINK = re.compile(r"(!?\[[^\]]*\])\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
CODE = re.compile(r"(```.*?```|`[^`\n]*`)", re.DOTALL)
SCHEME = re.compile(r"^[a-z][a-z0-9+.-]*:")
HEADING = re.compile(r"^(#+)\s+(.*?)\s*#*\s*$")
EXPLICIT = re.compile(r"\{#([^}\s]+)\}\s*$")
# A record keeps a link as it was written; these two never resolved.
KNOWN = frozenset(
    {
        ("docs/code_reviews/CODE_REVIEW_013.md", "specification/index.md"),
        (
            "docs/plans/phase-4/wp52-specification-and-plans-split.md",
            "../../history/index.md",
        ),
    }
)


def _slug(heading: str) -> str:
    """Return the anchor MkDocs' ``toc`` extension gives a heading (Python-Markdown's slugify)."""
    text = re.sub(r"`([^`]*)`", r"\1", heading)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", text)


def _anchors(path: Path) -> set[str]:
    anchors: set[str] = set()
    counts: dict[str, int] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = HEADING.match(line)
        if not match:
            continue
        explicit = EXPLICIT.search(match.group(2))
        if explicit:
            anchors.add(explicit.group(1).lower())
            continue
        slug = _slug(match.group(2))
        n = counts.get(slug, 0)
        counts[slug] = n + 1
        anchors.add(slug if n == 0 else f"{slug}_{n}")
    return anchors


def markdown_files() -> list[str]:
    """Return every tracked Markdown file the check reads, relative to the root."""
    result = subprocess.run(
        ["git", "ls-files", "-z", "*.md"], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return sorted(
        name
        for name in result.stdout.split("\0")
        if name and not name.startswith(ATTACHMENTS) and (ROOT / name).is_file()
    )


def main(argv: list[str] | None = None) -> int:
    """Print the link report and return 1 when a relative link's path does not exist."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--anchors", action="store_true", help="also check #anchors")
    arguments = parser.parse_args(argv)
    total = 0
    broken: list[str] = []
    known = 0
    bad_anchor: list[str] = []
    anchor_cache: dict[Path, set[str]] = {}
    for name in markdown_files():
        path = ROOT / name
        text = path.read_text(encoding="utf-8")
        masked = CODE.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), text)
        for match in LINK.finditer(masked):
            target = match.group(2)
            if SCHEME.match(target) or target.startswith("#"):
                continue
            total += 1
            line = masked.count("\n", 0, match.start()) + 1
            target_path, _, anchor = target.partition("#")
            resolved = (path.parent / target_path).resolve()
            if not resolved.exists():
                if (name, target) in KNOWN:
                    known += 1
                else:
                    broken.append(f"{name}:{line} `{target}`")
                continue
            if arguments.anchors and anchor and resolved.suffix == ".md":
                if resolved not in anchor_cache:
                    anchor_cache[resolved] = _anchors(resolved)
                if anchor.lower() not in anchor_cache[resolved]:
                    bad_anchor.append(f"{name}:{line} `{target}`")
    print("# Relative links of the tracked Markdown")
    print()
    print(f"Relative links: {total}. Broken paths: {len(broken)}, and {known} known.")
    print()
    print("## Broken paths")
    print()
    for item in broken:
        print(f"- {item}")
    if arguments.anchors:
        print()
        print(f"## Anchors naming no heading ({len(bad_anchor)})")
        print()
        for item in bad_anchor:
            print(f"- {item}")
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())

"""The files the written-knowledge audit reads, by its brief's scope.

The brief is ``docs/plans/sessions/kb-audit-brief.md``. Reads nothing but the tree; writes
nothing. Every audit script imports its scope from here so
that each measures the same files. ``live_files()`` are audited on all five axes;
``record_files()`` for reachability only; ``out_of_scope()`` names the Markdown the brief leaves
out, so an inventory can say so rather than silently skip it.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

LIVE_GLOBS: tuple[str, ...] = (
    "SPECIFICATION.md",
    "CLAUDE.md",
    "README.md",
    "CONTRIBUTING.md",
    "AGENTS.md",
    "docs/index.md",
    "docs/getting-started.md",
    "docs/guide/*.md",
    "docs/model/*.md",
    "docs/reference/*.md",
    "docs/examples/index.md",
    "docs/project/*.md",
    "docs/design/workbench.md",
    "docs/design/tokens.css",
    "docs/plans/current.md",
    "docs/plans/phase-5/phase-5-workbench.md",
    ".claude/workflow/**/*.md",
    ".claude/skills/**/*.md",
    ".claude/agents/*.md",
    ".claude/rules/*.md",
    ".claude/scripts/*.py",
    ".claude/hooks/*.sh",
)

RECORD_GLOBS: tuple[str, ...] = (
    "specification/history/*.md",
    "docs/plans/**/*.md",
    "docs/code_reviews/**/*.md",
    "docs/design/reviews/**/*.md",
    "docs/design/spike/**/*.md",
    "docs/superpowers/**/*.md",
    "docs/user-testing/**/*.md",
    "CHANGELOG.md",
)

OUT_GLOBS: tuple[str, ...] = (
    "docs/sweeps/**/*",
    "docs/validation/**/*",
    "docs/design/concepts/**/*",
    "docs/design/style/**/*",
    "docs/design/choices/**/*",
    "docs/design/mockups/**/*",
    "docs/design/generators/**/*",
    "docs/overrides/**/*",
    "docs/scripts/**/*",
)

LIVE_PLANS = frozenset({"docs/plans/current.md", "docs/plans/phase-5/phase-5-workbench.md"})


def _own_output(path: Path) -> bool:
    """Return whether ``path`` is under this audit's own attachment folder, which it never reads."""
    return "CODE_REVIEW_039" in path.parts


def _expand(globs: tuple[str, ...]) -> list[Path]:
    found: set[Path] = set()
    for pattern in globs:
        for path in ROOT.glob(pattern):
            if path.is_file() and "_generated" not in path.parts and not _own_output(path):
                found.add(path)
    return sorted(found)


def live_files() -> list[Path]:
    """Return every live file in scope.

    The specification outside its history, the knowledge base, the live docs and ``.claude/``.
    """
    files = set(_expand(LIVE_GLOBS))
    for path in ROOT.glob("specification/**/*.md"):
        if "history" not in path.relative_to(ROOT).parts:
            files.add(path)
    files.update(ROOT.glob("knowledge/**/*.md"))
    return sorted(files)


def record_files() -> list[Path]:
    """Return every record in scope, audited for reachability only."""
    files = set(_expand(RECORD_GLOBS))
    return sorted(p for p in files if p.relative_to(ROOT).as_posix() not in LIVE_PLANS)


def out_of_scope() -> list[Path]:
    """Return the Markdown the brief leaves out, so an inventory can say so."""
    return [p for p in _expand(OUT_GLOBS) if p.suffix == ".md"]


def relative(path: Path) -> str:
    """Return ``path`` relative to the repository root, POSIX-style."""
    return path.relative_to(ROOT).as_posix()


def markdown_in_scope() -> list[Path]:
    """Return every Markdown file in scope, live and record."""
    return sorted({p for p in [*live_files(), *record_files()] if p.suffix == ".md"})


def words(text: str) -> int:
    """Return the number of whitespace-separated words in ``text``."""
    return len(text.split())


def tokens(text: str) -> int:
    """Return the estimated token count of ``text``: its characters divided by four, rounded up.

    The audit has no tokenizer of the serving model in the environment and adds no dependency, so
    every token count it reports is this estimate, stated as such.
    """
    return -(-len(text) // 4)

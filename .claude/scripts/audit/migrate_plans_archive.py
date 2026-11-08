"""Move the delivered plans to ``docs/plans/archive/`` and rewrite the links that can be rewritten.

A proposal of CODE_REVIEW_039, never applied to ``main``: run it on a scratch branch, verify,
delete the branch. History-prose-review item I allows the move ("optionally move delivered plans
to ``docs/plans/archive/``").

Reads ``docs/plans/*.md``: a ``wp*.md`` or ``phase-*.md`` whose first bold status line begins
with *delivered* or *closed* is moved; every other file stays (``current.md``, the live phase plan,
the input notes, the records of amended plans). Writes: ``git mv`` of each moved plan; the
relative links to a moved plan rewritten in every live file (the brief's scope) and in the record
indexes, never in a record, which stays byte for byte; ``.claude/scripts/duplicates.py``'s plan
glob widened to the archive. Prints what it moved, what it rewrote, and what it leaves broken:
every link to a moved plan from a record, by file. ``--dry-run`` prints the same and writes nothing.

Run it as ``uv run .claude/scripts/audit/migrate_plans_archive.py [--dry-run]``.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scope import ROOT, live_files, record_files

PLANS = ROOT / "docs" / "plans"
ARCHIVE = PLANS / "archive"
STATUS = re.compile(r"\*\*Status:\s*(delivered|closed)\b", re.I)
LINK = re.compile(r"(\]\()([^)\s#]+)((?:#[^)]*)?\))")
DUPLICATES = ROOT / ".claude" / "scripts" / "duplicates.py"
INDEXES = (
    PLANS / "index.md",
    ROOT / "docs" / "code_reviews" / "index.md",
    ROOT / "docs" / "design" / "reviews" / "index.md",
)


def _moved() -> list[Path]:
    found = []
    for path in sorted(PLANS.glob("*.md")):
        if not (path.name.startswith("wp") or path.name.startswith("phase-")):
            continue
        if STATUS.search(path.read_text(encoding="utf-8")):
            found.append(path)
    return found


def _rewrite(path: Path, moved: set[Path]) -> tuple[str, int]:
    """Return ``path``'s text with every link to a moved plan rewritten, and the count."""
    text = path.read_text(encoding="utf-8")
    count = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal count
        target = match.group(2)
        if target.startswith(("http:", "https:", "mailto:")):
            return match.group(0)
        resolved = (path.parent / target).resolve()
        if resolved not in moved:
            return match.group(0)
        new = ARCHIVE / resolved.name
        relative = Path(new).relative_to(path.parent.resolve(), walk_up=True).as_posix()
        count += 1
        return f"{match.group(1)}{relative}{match.group(3)}"

    return LINK.sub(replace, text), count


def _record_links(moved: set[Path]) -> dict[Path, int]:
    """Return, per record, the number of links to a moved plan it holds; these stay broken."""
    found: dict[Path, int] = {}
    for path in record_files():
        if path.suffix != ".md" or path in moved or path in INDEXES:
            continue
        text = path.read_text(encoding="utf-8")
        count = sum(
            1
            for match in LINK.finditer(text)
            if not match.group(2).startswith(("http:", "https:"))
            and (path.parent / match.group(2)).resolve() in moved
        )
        if count:
            found[path] = count
    return found


def main(argv: list[str] | None = None) -> int:
    """Perform or rehearse the move and return the process exit status."""
    parser = argparse.ArgumentParser(description="Move the delivered plans to docs/plans/archive/.")
    parser.add_argument("--dry-run", action="store_true", help="print the plan and write nothing")
    arguments = parser.parse_args(argv)
    moved_list = _moved()
    moved = {path.resolve() for path in moved_list}
    sys.stdout.write(f"plans to move: {len(moved_list)} of {len(list(PLANS.glob('*.md')))}\n")
    rewrites: list[tuple[Path, str, int]] = []
    for path in [*live_files(), *INDEXES]:
        if path.suffix != ".md" or not path.exists():
            continue
        text, count = _rewrite(path, moved)
        if count:
            rewrites.append((path, text, count))
    for path, _, count in rewrites:
        sys.stdout.write(f"rewrite {path.relative_to(ROOT).as_posix()}: {count} links\n")
    broken = _record_links(moved)
    sys.stdout.write(
        f"links left broken in records (byte for byte): {sum(broken.values())} "
        f"in {len(broken)} files\n"
    )
    for path, count in sorted(broken.items()):
        sys.stdout.write(f"  {path.relative_to(ROOT).as_posix()}: {count}\n")
    if arguments.dry_run:
        return 0
    ARCHIVE.mkdir(exist_ok=True)
    for path in moved_list:
        subprocess.run(["git", "mv", str(path), str(ARCHIVE / path.name)], check=True, cwd=ROOT)
    for path, text, _ in rewrites:
        path.write_text(text, encoding="utf-8")
    duplicates = DUPLICATES.read_text(encoding="utf-8")
    widened = duplicates.replace(
        '(ROOT / "docs/plans").glob("wp*.md")', '(ROOT / "docs/plans").rglob("wp*.md")'
    )
    if widened != duplicates:
        DUPLICATES.write_text(widened, encoding="utf-8")
        sys.stdout.write("duplicates.py: plan glob widened to docs/plans/**\n")
    sys.stdout.write("moved; re-run index_records.py for docs/plans/index.md\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

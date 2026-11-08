"""Give every NOTE of §4 and §6 that does not name its parent clause the parent's identifier.

A proposal of CODE_REVIEW_039 (finding SPB-01), never applied to ``main``: run it on a scratch
branch, verify with ``clause.py``, delete the branch. ``clause.py`` attaches a NOTE to the
identifiers the NOTE names, so a NOTE that follows ``NUM-16`` without naming it is not printed
with ``NUM-16``.

Reads ``specification/04-physics.md`` and ``specification/06-numerics.md``. For each ``NOTE``
paragraph, the parent is the last clause defined before it (a ``| **PHY-nn** |`` row or a
``**NUM-nn.**`` paragraph); a NOTE under a heading with no clause before it is left alone, and so
is a NOTE whose text already names its parent. Writes the parent into the label: ``NOTE:`` becomes
``NOTE (NUM-08):``, ``NOTE (sign):`` becomes ``NOTE (NUM-24, sign):`` and ``NOTE on the relative
tolerance.`` becomes ``NOTE (NUM-16, on the relative tolerance).``. The NOTE's text is otherwise
unchanged; no SHALL, tolerance or default moves. Prints each relabelled line. ``--dry-run``
prints and writes nothing.

Run it as ``uv run .claude/scripts/audit/migrate_note_labels.py [--dry-run]``.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scope import ROOT

FILES = (
    ROOT / "specification" / "04-physics.md",
    ROOT / "specification" / "06-numerics.md",
)
ROW = re.compile(r"^\|\s*\*\*([A-Z]+-\d+)\*\*\s*\|")
PARAGRAPH = re.compile(r"^\*\*([A-Z]+-\d+)\.\*\*")
HEADING = re.compile(r"^#+ ")
LABELLED = re.compile(r"^NOTE \(([^)]*)\)(:?)")
ON = re.compile(r"^NOTE on (.+?)\.(?=\s|$)")
BARE = re.compile(r"^NOTE:")


def _pattern(identifier: str) -> re.Pattern[str]:
    return re.compile(rf"(?<![A-Za-z0-9§.-]){re.escape(identifier)}(?![A-Za-z0-9]|\.\d|-\d)")


def _note_end(lines: list[str], start: int) -> int:
    end = start
    while end < len(lines) and lines[end].strip():
        end += 1
    return end


def relabel(lines: list[str]) -> list[tuple[int, str, str]]:
    """Return (line index, old line, new line) for every NOTE that gains its parent."""
    changes: list[tuple[int, str, str]] = []
    parent: str | None = None
    index = 0
    while index < len(lines):
        line = lines[index]
        if HEADING.match(line):
            parent = None
        elif (match := ROW.match(line)) or (match := PARAGRAPH.match(line)):
            parent = match.group(1)
        elif line.startswith("NOTE") and parent:
            end = _note_end(lines, index)
            text = "\n".join(lines[index:end])
            if not _pattern(parent).search(text):
                new = None
                if labelled := LABELLED.match(line):
                    new = (
                        f"NOTE ({parent}, {labelled.group(1)}){labelled.group(2)}"
                        + line[labelled.end() :]
                    )
                elif on := ON.match(line):
                    new = f"NOTE ({parent}, on {on.group(1)})." + line[on.end() :]
                elif BARE.match(line):
                    new = f"NOTE ({parent}):" + line[len("NOTE:") :]
                if new:
                    changes.append((index, line, new))
            index = end
            continue
        index += 1
    return changes


def main(argv: list[str] | None = None) -> int:
    """Relabel or rehearse, and return the process exit status."""
    parser = argparse.ArgumentParser(description="Name each NOTE's parent clause in its label.")
    parser.add_argument(
        "--dry-run", action="store_true", help="print the changes and write nothing"
    )
    arguments = parser.parse_args(argv)
    total = 0
    for path in FILES:
        lines = path.read_text(encoding="utf-8").splitlines()
        changes = relabel(lines)
        total += len(changes)
        sys.stdout.write(
            f"{path.relative_to(ROOT).as_posix()}: {len(changes)} NOTEs gain their parent\n"
        )
        for index, old, new in changes:
            sys.stdout.write(f"  {index + 1}: {old[:60]!r} -> {new[:70]!r}\n")
            lines[index] = new
        if not arguments.dry_run and changes:
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    sys.stdout.write(f"{total} NOTEs relabelled{' (dry run)' if arguments.dry_run else ''}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

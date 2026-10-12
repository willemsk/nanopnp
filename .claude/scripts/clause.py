"""Print specification clauses by identifier (WP43 D13; SPECIFICATION.md §8.2.10 J8).

For each identifier (``VER-62``, ``FR-16``, ``§7.6``, ``J8``) the script prints, with line
ranges, the section or table row that defines it, every NOTE that names it and every §8.2
ruling row that names it. Matching is on whole identifiers, so ``VER-6`` never matches
``VER-62``. An identifier with no definition is named on standard error and the exit status
is non-zero.

Run it as ``uv run .claude/scripts/clause.py VER-62 §7.6``.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

SPECIFICATION = Path(__file__).resolve().parents[2] / "SPECIFICATION.md"
RULING_ROW = re.compile(r"^\|\s*([A-Z]\d+)\s*\|")


def _pattern(identifier: str) -> re.Pattern[str]:
    """Return a regex matching ``identifier`` as a whole token, not as part of a longer one."""
    return re.compile(rf"(?<![A-Za-z0-9§.-])(?:{re.escape(identifier)})(?![A-Za-z0-9]|\.\d|-\d)")


def _heading_level(line: str) -> int:
    match = re.match(r"(#+) ", line)
    return len(match.group(1)) if match else 0


def _first_cell(line: str) -> str:
    cells = line.split("|")
    return cells[1].replace("*", "").strip() if line.startswith("|") and len(cells) > 2 else ""


def _section_end(lines: list[str], start: int) -> int:
    level = _heading_level(lines[start])
    end = start + 1
    while end < len(lines) and not 0 < _heading_level(lines[end]) <= level:
        end += 1
    return end


def _definition(lines: list[str], identifier: str) -> tuple[int, int] | None:
    """Return the 0-based half-open line range defining ``identifier``, or ``None``."""
    heading = rf"#+ {re.escape(identifier[1:] if identifier.startswith('§') else identifier)}(\s|$)"
    for start, line in enumerate(lines):
        if _heading_level(line) and re.match(heading, line):
            return start, _section_end(lines, start)
        if not identifier.startswith("§") and _first_cell(line) == identifier:
            return start, start + 1
    return None


def _notes(lines: list[str]) -> list[tuple[int, int]]:
    """Return the line ranges of every NOTE paragraph."""
    found: list[tuple[int, int]] = []
    start = 0
    while start < len(lines):
        if lines[start].startswith("NOTE"):
            end = start
            while end < len(lines) and lines[end].strip():
                end += 1
            found.append((start, end))
            start = end
        else:
            start += 1
    return found


def _rulings(lines: list[str]) -> list[int]:
    """Return the 0-based lines of every ruling row in §8.2."""
    begin = next((i for i, line in enumerate(lines) if line.startswith("### 8.2 ")), None)
    if begin is None:
        return []
    end = next((i for i in range(begin + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
    return [i for i in range(begin, end) if RULING_ROW.match(lines[i])]


def _emit(lines: list[str], label: str, start: int, end: int) -> None:
    sys.stdout.write(f"--- {label} (lines {start + 1}-{end}) ---\n")
    sys.stdout.write("\n".join(lines[start:end]) + "\n")


def clause(lines: list[str], identifier: str) -> bool:
    """Print the clause for ``identifier``.

    Parameters
    ----------
    lines
        The specification, one string per line.
    identifier
        A requirement identifier, a ruling identifier or a section number with ``§``.

    Returns
    -------
    bool
        ``False`` when the identifier has no definition, ``True`` otherwise.
    """
    definition = _definition(lines, identifier)
    if definition is None:
        return False
    pattern = _pattern(identifier)
    sys.stdout.write(f"=== {identifier} ===\n")
    _emit(lines, "definition", *definition)
    for start, end in _notes(lines):
        inside = definition[0] <= start and end <= definition[1]
        if not inside and pattern.search("\n".join(lines[start:end])):
            _emit(lines, "NOTE", start, end)
    for row in _rulings(lines):
        if not (definition[0] <= row < definition[1]) and pattern.search(lines[row]):
            _emit(lines, "ruling", row, row + 1)
    return True


def main(argv: list[str] | None = None) -> int:
    """Run the command line and return the process exit status."""
    parser = argparse.ArgumentParser(description="Print specification clauses by identifier.")
    parser.add_argument("identifiers", nargs="+", help="e.g. VER-62, FR-16, §7.6, J8")
    arguments = parser.parse_args(argv)
    lines = SPECIFICATION.read_text(encoding="utf-8").splitlines()
    status = 0
    for identifier in arguments.identifiers:
        if not clause(lines, identifier):
            sys.stderr.write(f"clause.py: no definition of {identifier} in {SPECIFICATION.name}\n")
            status = 1
    return status


if __name__ == "__main__":
    sys.exit(main())

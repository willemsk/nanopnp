"""Print specification clauses by identifier (SPECIFICATION.md §8.2.10 J8, §8.2.16 R2).

For each identifier (``VER-62``, ``FR-16``, ``§7.6``, ``J8``) the script prints, with the file and
line range, every section or table row that defines it, every NOTE that names it and every ruling
row of ``specification/history/`` that names it. The current files are searched before the
history, each in path order with ``index.md`` first. Matching is on whole identifiers, so
``VER-6`` never matches ``VER-62``. An identifier with no definition is named on standard error and
the exit status is non-zero.

Run it as ``uv run .claude/scripts/clause.py VER-62 §7.6``.
"""

from __future__ import annotations

import argparse
import io
import re
import sys
from pathlib import Path

BUNDLE = Path(__file__).resolve().parents[2] / "specification"
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


def _definitions(lines: list[str], identifier: str) -> list[tuple[int, int]]:
    """Return the 0-based half-open line ranges defining ``identifier`` in one file."""
    heading = rf"#+ {re.escape(identifier[1:] if identifier.startswith('§') else identifier)}(\s|$)"
    found: list[tuple[int, int]] = []
    start = 0
    while start < len(lines):
        line = lines[start]
        if _heading_level(line) and re.match(heading, line):
            end = _section_end(lines, start)
        elif not identifier.startswith("§") and _first_cell(line) == identifier:
            end = start + 1
        else:
            start += 1
            continue
        found.append((start, end))
        start = end
    return found


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
    """Return the 0-based lines of every ruling row of one history file."""
    return [i for i, line in enumerate(lines) if RULING_ROW.match(line)]


def _files() -> list[Path]:
    """Return the bundle files, current before history, in path order with ``index.md`` first."""

    def key(path: Path) -> tuple[bool, str]:
        relative = path.relative_to(BUNDLE).as_posix()
        return relative.startswith("history/"), relative.replace("index.md", "!index.md")

    return sorted(BUNDLE.rglob("*.md"), key=key)


def _emit(path: Path, lines: list[str], label: str, start: int, end: int) -> None:
    where = f"{path.relative_to(BUNDLE.parent).as_posix()}:{start + 1}-{end}"
    sys.stdout.write(f"--- {label} ({where}) ---\n")
    sys.stdout.write("\n".join(lines[start:end]) + "\n")


def clause(identifier: str) -> bool:
    """Print every definition of ``identifier``, then the NOTEs and ruling rows that name it.

    Parameters
    ----------
    identifier
        A requirement identifier, a ruling identifier or a section number with ``§``.

    Returns
    -------
    bool
        ``False`` when the identifier has no definition, ``True`` otherwise.
    """
    texts = {path: path.read_text(encoding="utf-8").splitlines() for path in _files()}
    definitions = {path: _definitions(lines, identifier) for path, lines in texts.items()}
    if not any(definitions.values()):
        return False
    pattern = _pattern(identifier)
    sys.stdout.write(f"=== {identifier} ===\n")
    for path, ranges in definitions.items():
        for start, end in ranges:
            _emit(path, texts[path], "definition", start, end)
    for path, lines in texts.items():
        for start, end in _notes(lines):
            inside = any(a <= start and end <= b for a, b in definitions[path])
            if not inside and pattern.search("\n".join(lines[start:end])):
                _emit(path, lines, "NOTE", start, end)
        if "history" not in path.relative_to(BUNDLE).parts:
            continue
        for row in _rulings(lines):
            if not any(a <= row < b for a, b in definitions[path]) and pattern.search(lines[row]):
                _emit(path, lines, "ruling", row, row + 1)
    return True


def main(argv: list[str] | None = None) -> int:
    """Run the command line and return the process exit status."""
    parser = argparse.ArgumentParser(description="Print specification clauses by identifier.")
    parser.add_argument("identifiers", nargs="+", help="e.g. VER-62, FR-16, §7.6, J8")
    arguments = parser.parse_args(argv)
    # Windows' console encoding (cp1252) cannot carry the specification's Greek and
    # mathematical characters; escape what the stream cannot encode rather than fail.
    # UTF-8 streams (Linux, macOS) still receive the text verbatim.
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(errors="backslashreplace")
    status = 0
    for identifier in arguments.identifiers:
        if not clause(identifier):
            sys.stderr.write(f"clause.py: no definition of {identifier} in {BUNDLE.name}/\n")
            status = 1
    return status


if __name__ == "__main__":
    sys.exit(main())

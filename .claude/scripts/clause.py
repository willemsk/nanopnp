"""Print specification clauses by identifier (SPECIFICATION.md §8.2.10 J8, §8.2.16 R2).

For each identifier (``VER-62``, ``FR-16``, ``PHY-11``, ``§7.6``, ``J8``) the script prints, with
the file and line range, every section, table row or ``**PHY-nn.**`` paragraph that defines it,
every NOTE that names it and every ruling row of ``specification/history/`` that names it. A
section that runs on past the end of its file, such as §5.3 or §8.2, continues into the files after
it. The current files are searched before the history, each in path order with ``index.md`` first.
Matching is on whole identifiers, so ``VER-6`` never matches ``VER-62``. An identifier with no
definition is named on standard error and the exit status is non-zero.

Run it as ``uv run .claude/scripts/clause.py VER-62 §7.6``.
"""

from __future__ import annotations

import argparse
import io
import re
import sys
from pathlib import Path

BUNDLE = Path(__file__).resolve().parents[2] / "specification"
RULING_ROW = re.compile(r"^\|\s*([A-Z]+\d+)\s*\|")
PARAGRAPH_DEFINITION = re.compile(r"\*\*[A-Z]+-\d+\.\*\*")


def _pattern(identifier: str) -> re.Pattern[str]:
    """Return a regex matching ``identifier`` as a whole token, not as part of a longer one."""
    return re.compile(rf"(?<![A-Za-z0-9§.-])(?:{re.escape(identifier)})(?![A-Za-z0-9]|\.\d|-\d)")


def _heading_level(line: str) -> int:
    match = re.match(r"(#+) ", line)
    return len(match.group(1)) if match else 0


def _first_cell(line: str) -> str:
    cells = line.split("|")
    return cells[1].replace("*", "").strip() if line.startswith("|") and len(cells) > 2 else ""


def _section_end(lines: list[str], start: int, level: int) -> int:
    end = start + 1
    while end < len(lines) and not 0 < _heading_level(lines[end]) <= level:
        end += 1
    return end


def _paragraph_end(lines: list[str], start: int) -> int:
    end = start + 1
    while end < len(lines) and not (
        _heading_level(lines[end])
        or lines[end].startswith("NOTE")
        or PARAGRAPH_DEFINITION.match(lines[end])
    ):
        end += 1
    return end


def _in_history(path: Path) -> bool:
    return path.relative_to(BUNDLE).parts[0] == "history"


def _continue_section(
    texts: dict[Path, list[str]],
    following: list[Path],
    level: int,
    found: dict[Path, list[tuple[int, int]]],
) -> None:
    for path in following:
        lines = texts[path]
        first = next((i for i, line in enumerate(lines) if _heading_level(line)), None)
        if first is None or _heading_level(lines[first]) <= level:
            return
        end = _section_end(lines, first, level)
        found[path].append((first, end))
        if end < len(lines):
            return


def _definitions(
    texts: dict[Path, list[str]], identifier: str
) -> dict[Path, list[tuple[int, int]]]:
    """Return, per file, the 0-based half-open line ranges defining ``identifier``."""
    section = identifier.startswith("§")
    heading = rf"#+ {re.escape(identifier[1:] if section else identifier)}(\s|$)"
    paragraph = f"**{identifier}.**"
    paths = list(texts)
    found: dict[Path, list[tuple[int, int]]] = {path: [] for path in paths}
    for position, path in enumerate(paths):
        lines = texts[path]
        start = 0
        while start < len(lines):
            line = lines[start]
            level = _heading_level(line)
            if level and re.match(heading, line):
                end = _section_end(lines, start, level)
                if end == len(lines):
                    _continue_section(texts, paths[position + 1 :], level, found)
            elif not section and _first_cell(line) == identifier:
                end = start + 1
            elif not section and line.startswith(paragraph):
                end = _paragraph_end(lines, start)
            else:
                start += 1
                continue
            found[path].append((start, end))
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
        return _in_history(path), relative.replace("index.md", "!index.md")

    return sorted(BUNDLE.rglob("*.md"), key=key)


def _emit(path: Path, lines: list[str], label: str, start: int, end: int) -> None:
    where = f"{path.relative_to(BUNDLE.parent).as_posix()}:{start + 1}-{end}"
    sys.stdout.write(f"--- {label} ({where}) ---\n")
    sys.stdout.write("\n".join(lines[start:end]) + "\n")


def clause(texts: dict[Path, list[str]], identifier: str) -> bool:
    """Print every definition of ``identifier``, then the NOTEs and ruling rows that name it.

    Parameters
    ----------
    texts
        The bundle's files in search order, each as its lines.
    identifier
        A requirement identifier, a ruling identifier or a section number with ``§``.

    Returns
    -------
    bool
        ``False`` when the identifier has no definition, ``True`` otherwise.
    """
    definitions = _definitions(texts, identifier)
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
        if not _in_history(path):
            continue
        for row in _rulings(lines):
            if not any(a <= row < b for a, b in definitions[path]) and pattern.search(lines[row]):
                _emit(path, lines, "ruling", row, row + 1)
    return True


def main(argv: list[str] | None = None) -> int:
    """Run the command line and return the process exit status."""
    parser = argparse.ArgumentParser(description="Print specification clauses by identifier.")
    parser.add_argument("identifiers", nargs="+", help="e.g. VER-62, FR-16, PHY-11, §7.6, J8")
    arguments = parser.parse_args(argv)
    # Windows' console encoding (cp1252) cannot carry the specification's Greek and
    # mathematical characters; escape what the stream cannot encode rather than fail.
    # UTF-8 streams (Linux, macOS) still receive the text verbatim.
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(errors="backslashreplace")
    texts = {path: path.read_text(encoding="utf-8").splitlines() for path in _files()}
    status = 0
    for identifier in arguments.identifiers:
        if not clause(texts, identifier):
            sys.stderr.write(f"clause.py: no definition of {identifier} in {BUNDLE.name}/\n")
            status = 1
    return status


if __name__ == "__main__":
    sys.exit(main())

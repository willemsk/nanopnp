"""Read the findings logs under ``docs/``, for the layering guard (VER-61)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

REPOSITORY = Path(__file__).resolve().parents[3]

COLUMNS: tuple[str, ...] = ("ID", "Area", "Severity", "Status", "Ruling", "Finding")

FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


@dataclass(frozen=True)
class Row:
    """One finding of a log, its cells as written."""

    line: int
    cells: tuple[str, ...]

    def cell(self, column: str) -> str:
        """Return the cell under ``column``, or an empty string on a short row."""
        index = COLUMNS.index(column)
        return self.cells[index] if index < len(self.cells) else ""

    @property
    def id(self) -> str:
        """Return the finding's identifier."""
        return self.cell("ID")


@dataclass(frozen=True)
class FindingsLog:
    """A parsed findings log."""

    path: Path
    prefix: str
    status: str
    areas: tuple[str, ...]
    rows: tuple[Row, ...]


class LogFormatError(ValueError):
    """Raised when a findings log cannot be parsed."""


def front_matter(text: str) -> dict[str, object] | None:
    """Return a page's YAML front matter as a mapping, or ``None`` if it has none."""
    match = FRONT_MATTER.match(text)
    if match is None:
        return None
    try:
        loaded = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        return None
    return loaded if isinstance(loaded, dict) else None


def _cells(line: str) -> tuple[str, ...]:
    return tuple(cell.strip() for cell in line.strip().strip("|").split("|"))


def parse_log(path: Path) -> FindingsLog:
    """Parse one log's front matter and the first table after it.

    Raises
    ------
    LogFormatError
        If the front matter is not a findings declaration, or no table with the expected
        header follows it.
    """
    text = path.read_text(encoding="utf-8")
    match = FRONT_MATTER.match(text)
    header = front_matter(text)
    declared = header.get("findings") if header else None
    if match is None or not isinstance(declared, dict):
        raise LogFormatError(f"{path}: no front matter declaring findings")
    if set(declared) != {"prefix", "status", "areas"}:
        raise LogFormatError(f"{path}: findings must declare exactly prefix, status and areas")
    areas = declared["areas"]
    if not isinstance(areas, list) or not areas:
        raise LogFormatError(f"{path}: findings.areas must be a non-empty list")
    lines = text.splitlines()
    first = text[: match.end()].count("\n")
    table = next((n for n in range(first, len(lines)) if lines[n].startswith("|")), None)
    if table is None:
        raise LogFormatError(f"{path}: no table follows the front matter")
    if _cells(lines[table]) != COLUMNS:
        raise LogFormatError(f"{path}:{table + 1}: the header must be {' | '.join(COLUMNS)}")
    rows = []
    for number in range(table + 2, len(lines)):
        if not lines[number].startswith("|"):
            break
        rows.append(Row(number + 1, _cells(lines[number])))
    return FindingsLog(
        path,
        str(declared["prefix"]),
        str(declared["status"]),
        tuple(str(area) for area in areas),
        tuple(rows),
    )

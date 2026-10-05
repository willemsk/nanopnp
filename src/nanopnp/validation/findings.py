"""Read and check the findings logs under ``docs/`` (VER-63; section 8.2.7 G4).

A findings log is a Markdown file named ``*findings.md``: YAML front matter
declaring its prefix, its status and its areas, then one table with a row per
finding. Phase 4 keeps two, the modularity report's ``MOD-nn`` and the user
testing's ``UT-nn``, and its close is asserted by this check on logs whose header
says ``closed`` (WP35 D17, Design section 3)::

    ---
    findings:
      prefix: MOD
      status: open        # open | closed
      areas: [stages, coupling, extension, surface]
    ---

    | ID | Area | Severity | Status | Ruling | Finding |

A row's ruling is ``—`` while it is ``open``; a section 8.2 row, written
``§8.2.N Xk``, for ``accepted``, ``deferred``, ``post-1.0`` and ``declined``; and a
link to a plan under ``docs/plans/`` for ``fixed``. Its finding cell links to the
finding's section of the report, and the anchor must name a heading there.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from collections.abc import Iterator
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

REPOSITORY = Path(__file__).resolve().parents[3]
"""The repository root, holding ``SPECIFICATION.md`` and ``docs/``."""

COLUMNS: tuple[str, ...] = ("ID", "Area", "Severity", "Status", "Ruling", "Finding")
"""The log table's header, in order (D17)."""

SEVERITIES: tuple[str, ...] = ("high", "medium", "low")
"""High: a SHALL the code does not meet. Medium: a property held only by convention, or
an extension needing an edit outside its home. Low: size or tidiness (WP35 D9)."""

STATUSES: tuple[str, ...] = ("open", "accepted", "fixed", "deferred", "post-1.0", "declined")
"""Every status a row may take (Design section 3)."""

TERMINAL: frozenset[str] = frozenset({"fixed", "deferred", "post-1.0", "declined"})
"""The statuses a ``closed`` log admits (G4)."""

RULED_BY_SPEC: frozenset[str] = frozenset({"accepted", "deferred", "post-1.0", "declined"})
"""The statuses whose ruling is a section 8.2 row."""

UNRULED = "—"
"""The ruling cell of an ``open`` row."""

LOG_SUFFIX = "findings.md"
"""The ending that makes a Markdown file under ``docs/`` a findings log."""

SPEC_ROW = re.compile(r"^§8\.2\.(\d+) ([A-Z]\d+)$")
"""A ruling naming a section 8.2 row: ``§8.2.7 G4``."""

LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
"""An inline Markdown link, capturing its target."""

FRONT_MATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
"""A page's YAML front matter."""


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
        """The finding's identifier."""
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
    """A findings log cannot be parsed: no front matter, no table, or a wrong header."""


def front_matter(text: str) -> dict[str, object] | None:
    """Return a page's YAML front matter as a mapping, or ``None`` if it has none."""
    match = FRONT_MATTER.match(text)
    if match is None:
        return None
    loaded = yaml.safe_load(match.group(1))
    return loaded if isinstance(loaded, dict) else None


def _cells(line: str) -> tuple[str, ...]:
    return tuple(cell.strip() for cell in line.strip().strip("|").split("|"))


def parse_log(path: Path) -> FindingsLog:
    """Parse one log's front matter and the first table after it.

    Raises
    ------
    LogFormatError
        If the front matter does not declare ``findings`` with exactly ``prefix``,
        ``status`` and a non-empty ``areas``, or if no table with the
        :data:`COLUMNS` header follows it.
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


@lru_cache(maxsize=4)
def _spec_rows(specification: Path) -> frozenset[tuple[str, str]]:
    """Return ``(N, first cell)`` of every table row under each ``#### 8.2.N`` heading."""
    rows: set[tuple[str, str]] = set()
    section: str | None = None
    for line in specification.read_text(encoding="utf-8").splitlines():
        heading = re.match(r"^(#{1,4}) ", line)
        if heading:
            numbered = re.match(r"^#### 8\.2\.(\d+)\b", line)
            section = numbered.group(1) if numbered else None
        elif section is not None and line.startswith("|"):
            rows.add((section, _cells(line)[0]))
    return frozenset(rows)


def slugify(heading: str) -> str:
    """Return a heading's anchor as Python-Markdown's ``toc`` extension writes it."""
    text = unicodedata.normalize("NFKD", heading).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", text)


@lru_cache(maxsize=16)
def _anchors(page: Path) -> frozenset[str]:
    return frozenset(
        slugify(line.lstrip("#").strip())
        for line in page.read_text(encoding="utf-8").splitlines()
        if re.match(r"^#{1,6} ", line)
    )


def _link(cell: str) -> str | None:
    match = LINK.search(cell)
    return match.group(1) if match else None


def _row_errors(log: FindingsLog, row: Row, repository: Path) -> Iterator[str]:
    if len(row.cells) != len(COLUMNS):
        yield f"has {len(row.cells)} columns, not {len(COLUMNS)}"
        return
    if not re.fullmatch(rf"{re.escape(log.prefix)}-\d{{2,}}", row.id):
        yield f"id {row.id!r} is not {log.prefix}-nn"
    area, severity, status = row.cell("Area"), row.cell("Severity"), row.cell("Status")
    ruling = row.cell("Ruling")
    if area not in log.areas:
        yield f"area {area!r} is not one of {', '.join(log.areas)}"
    if severity not in SEVERITIES:
        yield f"severity {severity!r} is not one of {', '.join(SEVERITIES)}"
    if status not in STATUSES:
        yield f"status {status!r} is not one of {', '.join(STATUSES)}"
    elif status == "open" and ruling != UNRULED:
        yield f"is open, so its ruling must be {UNRULED!r}, not {ruling!r}"
    elif status in RULED_BY_SPEC:
        spec = SPEC_ROW.match(ruling)
        if spec is None:
            yield f"is {status}, so its ruling must be a section 8.2 row, not {ruling!r}"
        elif (spec.group(1), spec.group(2)) not in _spec_rows(repository / "SPECIFICATION.md"):
            yield f"ruling {ruling!r} names no row of SPECIFICATION.md section 8.2.{spec.group(1)}"
    elif status == "fixed":
        target = _link(ruling)
        plans = (repository / "docs" / "plans").resolve()
        resolved = (log.path.parent / target).resolve() if target else None
        if (
            resolved is None
            or resolved.parent != plans
            or resolved.suffix != ".md"
            or not resolved.exists()
        ):
            yield f"is fixed, so its ruling must link to a plan under docs/plans/, not {ruling!r}"
    if log.status == "closed" and status not in TERMINAL:
        yield f"is {status!r} under a closed log; only {', '.join(sorted(TERMINAL))} close one"
    target = _link(row.cell("Finding"))
    if target is None or "#" not in target:
        yield "its finding must link to its section of the report, with an anchor"
    else:
        page, _, anchor = target.partition("#")
        resolved_page = (log.path.parent / page).resolve()
        if not resolved_page.exists():
            yield f"its finding links to {page!r}, which does not exist"
        elif anchor not in _anchors(resolved_page):
            yield f"its finding's anchor #{anchor} names no heading of {page}"


def check_log(path: Path, repository: Path = REPOSITORY) -> tuple[str, ...]:
    """Return every error of one log, each naming the file, the line and the row; empty if none.

    Refused: a header without the front matter or the reverse (D17), a log status
    other than ``open`` or ``closed``, a wrong column count, a malformed or repeated
    id, an area, severity or status outside the vocabulary, a ruling that does not
    resolve or is of the wrong kind for the status, an ``open`` row with a ruling,
    a non-terminal row under a ``closed`` log, and a finding cell that does not link
    to an existing heading of the report (Design section 3).
    """
    named = path.name.endswith(LOG_SUFFIX)
    declared = front_matter(path.read_text(encoding="utf-8"))
    has_header = declared is not None and "findings" in declared
    if has_header and not named:
        return (f"{path}: declares findings front matter but is not named *{LOG_SUFFIX}",)
    if not has_header:
        return (f"{path}: is named *{LOG_SUFFIX} but declares no findings front matter",)
    try:
        log = parse_log(path)
    except LogFormatError as error:
        return (str(error),)
    errors = []
    if log.status not in ("open", "closed"):
        errors.append(f"{path}: status {log.status!r} is neither open nor closed")
    if not log.rows:
        errors.append(f"{path}: the log has no rows")
    seen: dict[str, int] = {}
    for row in log.rows:
        place = f"{path}:{row.line}: row {row.id or '?'}"
        if row.id in seen:
            errors.append(f"{place} repeats the id of line {seen[row.id]}")
        seen.setdefault(row.id, row.line)
        errors += [f"{place} {error}" for error in _row_errors(log, row, repository)]
    return tuple(errors)


def logs(repository: Path = REPOSITORY) -> tuple[Path, ...]:
    """Return every Markdown file under ``docs/`` that is a log by name or by front matter."""
    found = []
    for path in sorted((repository / "docs").rglob("*.md")):
        if "_generated" in path.parts:
            continue
        if path.name.endswith(LOG_SUFFIX):
            found.append(path)
            continue
        declared = front_matter(path.read_text(encoding="utf-8"))
        if declared is not None and "findings" in declared:
            found.append(path)
    return tuple(found)


@dataclass(frozen=True)
class Counts:
    """A log's rows counted by area, severity and status, for the end-of-phase report."""

    area: dict[str, int]
    severity: dict[str, int]
    status: dict[str, int]


def counts(log: FindingsLog) -> Counts:
    """Count a log's rows by area, by severity and by status."""
    return Counts(
        dict(Counter(row.cell("Area") for row in log.rows)),
        dict(Counter(row.cell("Severity") for row in log.rows)),
        dict(Counter(row.cell("Status") for row in log.rows)),
    )

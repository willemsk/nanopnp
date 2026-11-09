"""Write the decisions register, ``docs/project/decisions.md``, from the records (§8.2.36 AL3).

Reads every ruling row of ``specification/history/*.md``, with where it holds now from
``specification/history/holds-now.yaml``; every ``Dn`` row of a plan under ``docs/plans/``; every
``REV`` and ``MOD`` row of ``docs/project/review-findings.md`` and ``modularity-findings.md``;
every ``OPN`` row of ``specification/10-open-items.md``; every ``WB`` row of
``docs/design/workbench.md``; the knowledge base's rulings of
``knowledge/00-orientation/05-*.md``; and the *Not to be re-decided* bullets of
``docs/plans/current.md``. Writes one row per decision in eight columns (source; decided by; where;
date; package; what was decided; where it holds now; status), ordered by date, undated last, then
by source, path and reading order, under the counts by source and by decider. Nothing is read but
the tree, and *Where* names a file without a line, so an edit elsewhere leaves the page as it is.

Run it as ``uv run .claude/scripts/decisions.py`` to rewrite the page, or with ``--check`` to
compare it with the tree and write nothing; the check exits 1 on a difference.
"""

from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
PAGE = ROOT / "docs/project/decisions.md"
HISTORY = ROOT / "specification/history"
HOLDS_NOW = HISTORY / "holds-now.yaml"
COMMAND = "uv run .claude/scripts/decisions.py"

MONTH_NAMES = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)
MONTHS = "|".join(MONTH_NAMES)
DATE = re.compile(rf"\b(?:(\d{{1,2}}) )?({MONTHS}) (\d{{4}})\b")
ISO_DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
RULING_ROW = re.compile(r"^\|\s*([A-Z]{1,2}\d+)\b([^|]*)\|(.*)$")
RECORD_HEADING = re.compile(r"^#+\s+(8\.2(?:\.\d+)?)\s+(.*)$")
D_ROW = re.compile(r"^\|\s*\*{0,2}(D\d+[a-z]?)\b\.?[^|]*\|(.*)$")
WB_ROW = re.compile(r"^\|\s*(WB-\d+)\s*\|(.*)$")
OPN_ROW = re.compile(r"^\|\s*\*{0,2}(OPN-\d+)\*{0,2}\s*\|(.*)$")
REGISTER_ROW = re.compile(r"^\|\s*((?:REV|MOD)-\d+)\s*\|(.*)$")
KB_ROW = re.compile(r"^\|\s*(\d+)\s*\|(.*)$")
AUTHOR_MARK = re.compile(r"\((author[^)]*|my call[^)]*)\)")
CLAUSE_ID = re.compile(
    r"\b(?:FR|QR|CON|IF|PHY|NUM|VER|VAL|ADR|RSK|OPN|REV|MOD|WB)-\d+\b"
    r"|§\d+(?:\.\d+)*(?: [A-Z]{1,2}\d+)?"
)
# A plan whose head says it was delivered, merged, implemented or closed is no longer in flight.
PLAN_DONE = re.compile(r"\b(?:delivered|merged|implemented|closed)\b", re.I)
PLAN_NAME = re.compile(r"^(wp(\d+(?:\.\d+)?)|phase-(\d)|[a-z0-9-]+)")
LINK = re.compile(r"!?\[([^\]]*)\]\([^)\s]*(?:\s+\"[^\"]*\")?\)")
CODE = re.compile(r"`[^`\n]*`")
CELL = re.compile(r"((?:`[^`\n]*`|\\\||[^|])*)\|?")
# The order of the source kinds on the page and in its counts.
KINDS = (
    "history ruling",
    "plan decision row",
    "REV row",
    "MOD row",
    "OPN row",
    "WB row",
    "knowledge-base ruling",
    "not-to-be-re-decided bullet",
)
COLUMNS = ("Source", "Decided by", "Where", "Date", "Package", "What was decided", "Holds now")
HEADER = "| " + " | ".join((*COLUMNS, "Status")) + " |"


@dataclass(frozen=True)
class Decision:
    """One row of the register."""

    source_id: str
    decided_by: str
    where: str
    date: str
    package: str
    decided: str
    holds_now: str
    status: str
    kind: str
    order: int


def _relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _cells(text: str) -> list[str]:
    """Split a table row's remainder on its unescaped pipes outside code spans."""
    cells = [match.group(1).strip() for match in CELL.finditer(text)]
    while cells and not cells[-1]:
        cells.pop()
    return cells


def _escape(text: str) -> str:
    """Write ``<``, ``>`` and ``|`` so the site's table shows them, code spans left as they are."""

    def plain(piece: str) -> str:
        return re.sub(r"(?<!\\)\|", r"\\|", piece.replace("<", "&lt;").replace(">", "&gt;"))

    pieces: list[str] = []
    cursor = 0
    for match in CODE.finditer(text):
        pieces += [plain(text[cursor : match.start()]), match.group(0)]
        cursor = match.end()
    return "".join([*pieces, plain(text[cursor:])])


def _clean(text: str, limit: int = 220) -> str:
    """Return a cell's plain text: links reduced to their text, clipped, escaped."""
    text = LINK.sub(lambda match: match.group(1), text)
    text = re.sub(r"\s+", " ", text).strip(" *")
    if len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
        if text.count("`") % 2:
            text += "`"
    return _escape(text)


def _iso(text: str) -> str:
    """Return the first date of ``text`` in ISO form: ``2026-11-08``, or ``2026-08`` for a month."""
    match = DATE.search(text)
    if match:
        day, month, year = match.groups()
        number = MONTH_NAMES.index(month) + 1
        return f"{year}-{number:02d}-{int(day):02d}" if day else f"{year}-{number:02d}"
    iso = ISO_DATE.search(text)
    return iso.group(1) if iso else ""


def _holds_from(text: str) -> str:
    ids = CLAUSE_ID.findall(text)
    return ", ".join(dict.fromkeys(ids)) if ids else "unstated"


def _package_of(path: Path, text: str = "") -> str:
    match = re.search(r"\bWP(\d+(?:\.\d+)?)\b", text)
    if match:
        return f"WP{match.group(1)}"
    name = PLAN_NAME.match(path.stem)
    if name and name.group(2):
        return f"WP{name.group(2)}"
    if name and name.group(3):
        return f"Phase {name.group(3)}"
    return ""


def _records() -> list[Path]:
    return sorted(path for path in HISTORY.glob("*.md") if path.name != "index.md")


def ruling_letters() -> list[str]:
    """Return the identifier of every ruling row of the history, in reading order."""
    letters: list[str] = []
    for path in _records():
        for line in path.read_text(encoding="utf-8").splitlines():
            match = RULING_ROW.match(line)
            if match:
                letters.append(match.group(1))
    return letters


def holds_now() -> dict[str, str]:
    """Return where each ruling holds now, by its identifier, from ``holds-now.yaml``."""
    entries = yaml.safe_load(HOLDS_NOW.read_text(encoding="utf-8"))
    return {str(letter): str(entry) for letter, entry in entries.items()}


def _status_of_ruling(entry: str) -> str:
    if entry.startswith("spent"):
        return "spent"
    if entry.startswith("superseded by"):
        return "superseded"
    if entry.startswith("open"):
        return "open"
    if not entry:
        return "unstated"
    return "in force"


def history() -> list[Decision]:
    """Return every ruling row of the history, with where it holds now."""
    holds = holds_now()
    rows: list[Decision] = []
    for path in _records():
        record_date = record = package = ""
        for line in path.read_text(encoding="utf-8").splitlines():
            heading = RECORD_HEADING.match(line)
            if heading:
                record = f"§{heading.group(1)}"
                record_date = _iso(heading.group(2))
                package = _package_of(path, heading.group(2)) or "phase ruling"
            match = RULING_ROW.match(line)
            if not match:
                continue
            letter, annotation, rest = match.group(1), match.group(2).strip(), match.group(3)
            cells = _cells(rest)
            decided = cells[0] if cells else ""
            row_date = _iso(decided) if re.match(r"\*Added", decided) else ""
            entry = holds.get(letter, "")
            rows.append(
                Decision(
                    source_id=f"{record} {letter}",
                    decided_by="author",
                    where=_relative(path),
                    date=row_date or record_date,
                    package=_package_of(path, decided) or package,
                    decided=_clean(decided),
                    holds_now=_clean(
                        (entry or "unstated") + (f" ({annotation})" if annotation else ""), 160
                    ),
                    status=_status_of_ruling(entry),
                    kind="history ruling",
                    order=len(rows),
                )
            )
    return rows


def _plan_decider(body: str, letter: str, put_to_author: set[str]) -> str:
    mark = AUTHOR_MARK.search(body)
    if mark:
        return "author" if "author" in mark.group(1) else "session, own call"
    if "ruled by the author" in body.lower():
        return "author"
    if letter in put_to_author or "your call" in body.lower():
        return "session, put to the author"
    return "session, own call"


def plans() -> list[Decision]:
    """Return every row of a plan's Decisions table."""
    rows: list[Decision] = []
    plans_root = ROOT / "docs/plans"
    for path in sorted(plans_root.rglob("*.md")):
        if path.parent == plans_root and path.name in {"current.md", "index.md"}:
            continue
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        head = "\n".join(lines[:6])
        plan_date = _iso(head)
        package = _package_of(path)
        status = "delivered plan" if PLAN_DONE.search(head) else "plan in flight"
        your_call = re.search(r"\*\*Your call\.?\*\*(.*?)(?:\n\n|\Z)", text, re.S)
        put_to_author = (
            set(re.findall(r"\bD\d+[a-z]?\b", your_call.group(1))) if your_call else set()
        )
        for line in lines:
            match = D_ROW.match(line)
            if not match:
                continue
            letter, body = match.group(1), match.group(2)
            rows.append(
                Decision(
                    source_id=f"{package or path.stem} {letter}",
                    decided_by=_plan_decider(body, letter, put_to_author),
                    where=_relative(path),
                    date=plan_date,
                    package=package,
                    decided=_clean(body),
                    holds_now=_holds_from(body),
                    status=status,
                    kind="plan decision row",
                    order=len(rows),
                )
            )
    return rows


def registers() -> list[Decision]:
    """Return the ruling and status of every REV and MOD row."""
    rows: list[Decision] = []
    for name in ("review-findings.md", "modularity-findings.md"):
        path = ROOT / "docs/project" / name
        header: list[str] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("| ID |"):
                header = [cell.lower() for cell in _cells(line.strip().removeprefix("|"))]
                continue
            match = REGISTER_ROW.match(line)
            if not match or not header:
                continue
            values = dict(zip(header[1:], _cells(match.group(2)), strict=False))
            ruling = values.get("ruling", "")
            by_author = "§8.2" in ruling or "ruled" in ruling.lower()
            rows.append(
                Decision(
                    source_id=match.group(1),
                    decided_by="author" if by_author else "session, own call",
                    where=_relative(path),
                    date="",
                    package=_package_of(path, ruling),
                    decided=_clean(values.get("finding", "")),
                    holds_now=_clean(ruling, 160) or "unstated",
                    status=_clean(values.get("status", "")),
                    kind=f"{match.group(1)[:3]} row",
                    order=len(rows),
                )
            )
    return rows


def open_items() -> list[Decision]:
    """Return every OPN row."""
    rows: list[Decision] = []
    path = ROOT / "specification/10-open-items.md"
    for line in path.read_text(encoding="utf-8").splitlines():
        match = OPN_ROW.match(line)
        if not match:
            continue
        cells = _cells(match.group(2))
        closed = len(cells) > 1 and cells[1].strip(" *").lower().startswith("closed")
        rows.append(
            Decision(
                source_id=match.group(1),
                decided_by="author" if closed else "open",
                where=_relative(path),
                date=_iso(match.group(2)),
                package=_package_of(path, match.group(2)),
                decided=_clean(cells[0] if cells else ""),
                holds_now=_holds_from(" ".join(cells[1:])) if closed else "open",
                status="closed" if closed else "open",
                kind="OPN row",
                order=len(rows),
            )
        )
    return rows


def workbench() -> list[Decision]:
    """Return every WB row of the design document."""
    rows: list[Decision] = []
    path = ROOT / "docs/design/workbench.md"
    for line in path.read_text(encoding="utf-8").splitlines():
        match = WB_ROW.match(line)
        if match:
            rows.append(
                Decision(
                    source_id=match.group(1),
                    decided_by="author",
                    where=_relative(path),
                    date="",
                    package="WP5.01",
                    decided=_clean(" / ".join(_cells(match.group(2))[:2])),
                    holds_now="docs/design/workbench.md",
                    status="in the design document",
                    kind="WB row",
                    order=len(rows),
                )
            )
    return rows


def orientation() -> list[Decision]:
    """Return the knowledge base's rulings by the author."""
    rows: list[Decision] = []
    path = min((ROOT / "knowledge/00-orientation").glob("05-*.md"))
    for line in path.read_text(encoding="utf-8").splitlines():
        match = KB_ROW.match(line)
        if match:
            rows.append(
                Decision(
                    source_id=f"KB ruling {match.group(1)}",
                    decided_by="author",
                    where=_relative(path),
                    date="2026-08",
                    package="",
                    decided=_clean(" / ".join(_cells(match.group(2))[:2])),
                    holds_now=_holds_from(match.group(2)),
                    status="in force",
                    kind="knowledge-base ruling",
                    order=len(rows),
                )
            )
    return rows


def current() -> list[Decision]:
    """Return the bullets of ``current.md``'s *Not to be re-decided*."""
    rows: list[Decision] = []
    path = ROOT / "docs/plans/current.md"
    inside = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            inside = "not to be re-decided" in line.lower()
        elif inside and line.startswith("- "):
            rows.append(
                Decision(
                    source_id="current.md bullet",
                    decided_by="author",
                    where=_relative(path),
                    date="",
                    package="",
                    decided=_clean(line[2:]),
                    holds_now=_holds_from(line),
                    status="in force (cache)",
                    kind="not-to-be-re-decided bullet",
                    order=len(rows),
                )
            )
    return rows


def decisions() -> list[Decision]:
    """Return every row of the register, in the page's order."""
    rows = [
        *history(),
        *plans(),
        *registers(),
        *open_items(),
        *workbench(),
        *orientation(),
        *current(),
    ]
    return sorted(
        rows, key=lambda row: (row.date or "9999", KINDS.index(row.kind), row.where, row.order)
    )


def _counts(counts: dict[str, int]) -> str:
    return "; ".join(f"{name} {count:,}" for name, count in counts.items())


def render() -> str:
    """Return the page as the records stand."""
    rows = decisions()
    by_kind = {kind: sum(row.kind == kind for row in rows) for kind in KINDS}
    by_decider: dict[str, int] = {}
    for row in rows:
        by_decider[row.decided_by] = by_decider.get(row.decided_by, 0) + 1
    lines = [
        "# Decisions register",
        "",
        "Every decision the records hold, one row each, written by `.claude/scripts/decisions.py` "
        f"from the tree; `{COMMAND}` rewrites it, and the gate refuses a page that differs from "
        "the records. A ruling's *Holds now* is read from `specification/history/holds-now.yaml`. "
        "Each row names the file that holds the decision in full.",
        "",
        f"Rows: {len(rows):,}. By source: {_counts(by_kind)}.",
        "",
        f"By decider: {_counts(dict(sorted(by_decider.items())))}.",
        "",
        HEADER,
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        lines.append(
            f"| {row.source_id} | {row.decided_by} | `{row.where}` | {row.date} | {row.package} | "
            f"{row.decided} | {row.holds_now} | {row.status} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Write the page, or with ``--check`` compare it, and return the exit status."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="compare the page, write nothing")
    arguments = parser.parse_args(argv)
    page = render()
    if not arguments.check:
        PAGE.write_text(page, encoding="utf-8")
        return 0
    expected = page.splitlines()
    written = PAGE.read_text(encoding="utf-8").splitlines() if PAGE.exists() else []
    for number, (want, have) in enumerate(zip(expected, written, strict=False), 1):
        if want != have:
            print(f"{_relative(PAGE)}:{number} differs from the records; run `{COMMAND}`.")
            print(f"  expected: {want[:200]}")
            print(f"  found:    {have[:200]}")
            return 1
    if len(expected) != len(written):
        print(
            f"{_relative(PAGE)} has {len(written)} lines, the records give {len(expected)}; "
            f"run `{COMMAND}`."
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

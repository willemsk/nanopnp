"""Build the prototype decisions register from the text that records nanopnp's decisions.

Reads, as the audit brief's Appendix D lists: every ruling row of ``specification/history/*.md``
with its record's date and its *Where each ruling holds now* entry; every ``| Dn |`` row of a
Decisions table, every *Your call* paragraph and *Decisions for you* checklist item, every
``(author …)`` or ``(my call)`` mark and every Outcome annotation that records a choice, in
``docs/plans/*.md``; every row's ruling and status of ``docs/project/review-findings.md`` and
``modularity-findings.md``; every ``WB-nn`` row of ``docs/design/workbench.md``; the fourteen
rulings of ``knowledge/00-orientation/05-…``; every sentence of ``docs/code_reviews/*.md`` that
records a ruling by the author; the *Not to be re-decided* bullets of ``docs/plans/current.md``;
and every ``OPN-`` row of ``specification/10-open-items.md``.

Writes one row per decision, in Appendix D's columns (source identifier; decided by; where; date;
package; what was decided; where it holds now; status), as a Markdown table to the path given by
``--markdown`` and as JSON to ``--json`` (both default to the audit's attachment folder), with
counts by source and by decider at the top of the Markdown. Deterministic: rows are ordered by
file and line, and nothing is read but the tree.

Run it as ``uv run .claude/scripts/audit/decisions.py``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scope import ROOT, relative

ATTACHMENTS = ROOT / "docs" / "code_reviews" / "CODE_REVIEW_039"

MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
DATE = re.compile(rf"\b(\d{{1,2}} (?:{MONTHS}) \d{{4}})\b")
ISO_DATE = re.compile(r"\b(\d{4}-\d{2}-\d{2})\b")
RULING_ROW = re.compile(r"^\|\s*([A-Z]{1,2}\d+)\b([^|]*)\|(.*)$")
RECORD_HEADING = re.compile(r"^#+\s+(8\.2(?:\.\d+)?)\s+(.*)$")
HOLDS = re.compile(r"^\* ([A-Z]{1,2}\d+) - (.*)$")
D_ROW = re.compile(r"^\|\s*\*{0,2}(D\d+)\*{0,2}\s*\|(.*)$")
WB_ROW = re.compile(r"^\|\s*(WB-\d+)\s*\|(.*)$")
OPN_ROW = re.compile(r"^\|\s*\*{0,2}(OPN-\d+)\*{0,2}\s*\|(.*)$")
REGISTER_ROW = re.compile(r"^\|\s*((?:REV|MOD)-\d+)\s*\|(.*)$")
AUTHOR_MARK = re.compile(r"\((author[^)]*|my call[^)]*)\)")
OUTCOME = re.compile(r"^>\s*\*\*Outcome\b")
CHOICE_WORDS = re.compile(
    r"\b(decid|chose|chosen|ruled|ruling|instead|rather than|the author|opted|kept|dropped"
    r"|deferred)\b",
    re.I,
)
AUTHOR_VERBS = (
    "ruled|chose|decided|directed|confirmed|accepted|answered|asked for|agreed|approved"
    "|declined|picked|settled"
)
AUTHOR_SENTENCE = re.compile(rf"[^.!?\n]*\bthe author(?:'s)? (?:{AUTHOR_VERBS})\b[^.!?\n]*[.!?]")
CLAUSE_ID = re.compile(
    r"\b(?:FR|QR|CON|IF|PHY|NUM|VER|VAL|ADR|RSK|OPN|REV|MOD|WB)-\d+\b"
    r"|§\d+(?:\.\d+)*(?: [A-Z]{1,2}\d+)?"
)
PLAN_NAME = re.compile(r"^(wp(\d+(?:\.\d+)?)|phase-(\d)|[a-z0-9-]+)")


@dataclass
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


def _clean(text: str, limit: int = 220) -> str:
    text = re.sub(r"\s+", " ", text.replace("|", "/")).strip(" *")
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _first_date(text: str) -> str:
    match = DATE.search(text) or ISO_DATE.search(text)
    return match.group(1) if match else ""


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


def history() -> list[Decision]:
    """Return every ruling row of the history, with its holds-now entry."""
    holds: dict[str, str] = {}
    for line in (ROOT / "specification/history/index.md").read_text(encoding="utf-8").splitlines():
        match = HOLDS.match(line)
        if match:
            holds[match.group(1)] = match.group(2)
    rows: list[Decision] = []
    for path in sorted((ROOT / "specification/history").glob("*.md")):
        if path.name == "index.md":
            continue
        record_date = ""
        record = ""
        package = ""
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            heading = RECORD_HEADING.match(line)
            if heading:
                record = f"§{heading.group(1)}"
                record_date = _first_date(heading.group(2))
                package = _package_of(path, heading.group(2)) or "phase ruling"
            match = RULING_ROW.match(line)
            if not match or match.group(1) == "ID":
                continue
            letter, annotation, rest = match.group(1), match.group(2).strip(), match.group(3)
            cells = [c.strip() for c in rest.split("|")]
            decided = cells[0] if cells else ""
            row_date = _first_date(decided) if re.match(r"\*Added", decided) else ""
            entry = holds.get(letter, "not in the index")
            if entry.startswith("spent"):
                status = "spent"
            elif "superseded by" in entry and "its" not in entry[:4].lower():
                status = "superseded"
            elif entry.startswith("open"):
                status = "open"
            elif entry == "not in the index":
                status = "unindexed"
            else:
                status = "in force"
            rows.append(
                Decision(
                    source_id=f"{record} {letter}",
                    decided_by="author",
                    where=f"{relative(path)}:{number}",
                    date=row_date or record_date,
                    package=_package_of(path, decided) or package,
                    decided=_clean(decided),
                    holds_now=_clean(entry + (f" ({annotation})" if annotation else ""), 160),
                    status=status,
                    kind="history ruling",
                )
            )
    return rows


def plans() -> list[Decision]:
    """Return the decisions recorded in the plans."""
    rows: list[Decision] = []
    for path in sorted((ROOT / "docs/plans").glob("*.md")):
        if path.name == "current.md":
            continue
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        head = "\n".join(lines[:6])
        plan_date = _first_date(head)
        package = _package_of(path)
        delivered = "delivered" in head.lower()
        your_call = re.search(r"\*\*Your call\.?\*\*(.*?)(?:\n\n|\Z)", text, re.S)
        put_to_author = set(re.findall(r"\bD\d+\b", your_call.group(1))) if your_call else set()
        in_decisions_for_you = False
        for number, line in enumerate(lines, 1):
            if line.startswith("#"):
                in_decisions_for_you = "decisions for you" in line.lower()
            d_row = D_ROW.match(line)
            if d_row:
                body = d_row.group(2)
                if AUTHOR_MARK.search(body):
                    by = (
                        "author"
                        if "author" in AUTHOR_MARK.search(body).group(1)
                        else "session, own call"
                    )
                elif d_row.group(1) in put_to_author or "your call" in body.lower():
                    by = "session, put to the author"
                else:
                    by = "session, own call"
                rows.append(
                    Decision(
                        source_id=f"{package} {d_row.group(1)}",
                        decided_by=by,
                        where=f"{relative(path)}:{number}",
                        date=plan_date,
                        package=package,
                        decided=_clean(body),
                        holds_now=_holds_from(body),
                        status="delivered plan" if delivered else "plan in flight",
                        kind="plan decision row",
                    )
                )
                continue
            if in_decisions_for_you and re.match(r"^- \[[ xX]\]", line):
                rows.append(
                    Decision(
                        source_id=f"{path.stem} checklist",
                        decided_by="session, put to the author",
                        where=f"{relative(path)}:{number}",
                        date=plan_date,
                        package=package,
                        decided=_clean(line[6:]),
                        holds_now=_holds_from(line),
                        status="answered" if "[x]" in line.lower() else "open",
                        kind="decisions-for-you item",
                    )
                )
                continue
            if line.startswith("**Your call") and "none" not in line.lower()[:40]:
                rows.append(
                    Decision(
                        source_id=f"{path.stem} your call",
                        decided_by="session, put to the author",
                        where=f"{relative(path)}:{number}",
                        date=plan_date,
                        package=package,
                        decided=_clean(line),
                        holds_now=_holds_from(line),
                        status="put",
                        kind="your-call paragraph",
                    )
                )
                continue
            mark = AUTHOR_MARK.search(line)
            if mark and not D_ROW.match(line):
                rows.append(
                    Decision(
                        source_id=f"{path.stem} mark",
                        decided_by="author" if "author" in mark.group(1) else "session, own call",
                        where=f"{relative(path)}:{number}",
                        date=_first_date(mark.group(1)) or plan_date,
                        package=package,
                        decided=_clean(line),
                        holds_now=_holds_from(line),
                        status="recorded",
                        kind="author or my-call mark",
                    )
                )
                continue
            if OUTCOME.match(line) and CHOICE_WORDS.search(line):
                rows.append(
                    Decision(
                        source_id=f"{path.stem} outcome",
                        decided_by="author" if "author" in line.lower() else "session, own call",
                        where=f"{relative(path)}:{number}",
                        date=_first_date(line) or plan_date,
                        package=package,
                        decided=_clean(line.lstrip("> ")),
                        holds_now=_holds_from(line),
                        status="recorded",
                        kind="outcome annotation",
                    )
                )
    return rows


def registers() -> list[Decision]:
    """Return the ruling and status of every REV and MOD row."""
    rows: list[Decision] = []
    for name in ("review-findings.md", "modularity-findings.md"):
        path = ROOT / "docs/project" / name
        header: list[str] = []
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.startswith("| ID |"):
                header = [c.strip().lower() for c in line.strip("|").split("|")]
                continue
            match = REGISTER_ROW.match(line)
            if not match or not header:
                continue
            cells = [c.strip() for c in match.group(2).split("|")]
            values = dict(zip(header[1:], cells, strict=False))
            ruling = values.get("ruling", "")
            rows.append(
                Decision(
                    source_id=match.group(1),
                    decided_by="author"
                    if "§8.2" in ruling or "ruled" in ruling.lower()
                    else "session, own call",
                    where=f"{relative(path)}:{number}",
                    date="",
                    package=_package_of(path, ruling),
                    decided=_clean(values.get("finding", "")),
                    holds_now=_clean(ruling) or "unstated",
                    status=values.get("status", ""),
                    kind=f"{match.group(1)[:3]} row",
                )
            )
    return rows


def workbench() -> list[Decision]:
    """Return every WB row of the design document."""
    rows: list[Decision] = []
    path = ROOT / "docs/design/workbench.md"
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        match = WB_ROW.match(line)
        if match:
            cells = [c.strip() for c in match.group(2).split("|")]
            rows.append(
                Decision(
                    source_id=match.group(1),
                    decided_by="author",
                    where=f"{relative(path)}:{number}",
                    date="",
                    package="WP5.01",
                    decided=_clean(" / ".join(cells[:2])),
                    holds_now="docs/design/workbench.md",
                    status="in the design document",
                    kind="WB row",
                )
            )
    return rows


def orientation() -> list[Decision]:
    """Return the fourteen author rulings of the knowledge base."""
    rows: list[Decision] = []
    path = next((ROOT / "knowledge/00-orientation").glob("05-*.md"))
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        match = re.match(r"^\|\s*(\d+)\s*\|(.*)$", line)
        if match:
            cells = [c.strip() for c in match.group(2).split("|")]
            rows.append(
                Decision(
                    source_id=f"KB ruling {match.group(1)}",
                    decided_by="author",
                    where=f"{relative(path)}:{number}",
                    date="August 2026",
                    package="",
                    decided=_clean(" / ".join(cells[:2])),
                    holds_now=_holds_from(match.group(2)),
                    status="in force",
                    kind="knowledge-base ruling",
                )
            )
    return rows


def reviews() -> list[Decision]:
    """Return every sentence of a code review that records a ruling by the author."""
    rows: list[Decision] = []
    for path in sorted((ROOT / "docs/code_reviews").glob("CODE_REVIEW_*.md")):
        if "039" in path.name:
            continue
        text = path.read_text(encoding="utf-8")
        for match in AUTHOR_SENTENCE.finditer(text):
            number = text.count("\n", 0, match.start()) + 1
            rows.append(
                Decision(
                    source_id=f"{path.stem} sentence",
                    decided_by="author",
                    where=f"{relative(path)}:{number}",
                    date=_first_date(match.group(0)) or _first_date(text[:600]),
                    package=_package_of(path, text[:400]),
                    decided=_clean(match.group(0)),
                    holds_now=_holds_from(match.group(0)),
                    status="recorded",
                    kind="code-review sentence",
                )
            )
    return rows


def current() -> list[Decision]:
    """Return the bullets of current.md's *Not to be re-decided*."""
    rows: list[Decision] = []
    path = ROOT / "docs/plans/current.md"
    inside = False
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.startswith("## "):
            inside = "not to be re-decided" in line.lower()
        elif inside and line.startswith("- "):
            rows.append(
                Decision(
                    source_id="current.md bullet",
                    decided_by="author",
                    where=f"{relative(path)}:{number}",
                    date="",
                    package="",
                    decided=_clean(line[2:]),
                    holds_now=_holds_from(line),
                    status="in force (cache)",
                    kind="not-to-be-re-decided bullet",
                )
            )
    return rows


def open_items() -> list[Decision]:
    """Return every OPN row."""
    rows: list[Decision] = []
    path = ROOT / "specification/10-open-items.md"
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        match = OPN_ROW.match(line)
        if match:
            cells = [c.strip() for c in match.group(2).split("|")]
            closed = "closed" in match.group(2).lower()
            rows.append(
                Decision(
                    source_id=match.group(1),
                    decided_by="author" if closed else "open",
                    where=f"{relative(path)}:{number}",
                    date=_first_date(match.group(2)),
                    package=_package_of(path, match.group(2)),
                    decided=_clean(cells[0] if cells else ""),
                    holds_now=_holds_from(" ".join(cells[1:])) if closed else "open",
                    status="closed" if closed else "open",
                    kind="OPN row",
                )
            )
    return rows


def main(argv: list[str] | None = None) -> int:
    """Write the register as Markdown and JSON."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--markdown", type=Path, default=ATTACHMENTS / "decisions.md")
    parser.add_argument("--json", type=Path, default=ATTACHMENTS / "decisions.json")
    arguments = parser.parse_args(argv)
    rows = [
        *history(),
        *plans(),
        *registers(),
        *workbench(),
        *orientation(),
        *reviews(),
        *current(),
        *open_items(),
    ]
    rows.sort(key=lambda r: (r.where.rsplit(":", 1)[0], int(r.where.rsplit(":", 1)[1])))
    by_kind: dict[str, int] = {}
    by_decider: dict[str, int] = {}
    unstated = 0
    for row in rows:
        by_kind[row.kind] = by_kind.get(row.kind, 0) + 1
        by_decider[row.decided_by] = by_decider.get(row.decided_by, 0) + 1
        unstated += row.holds_now == "unstated"
    lines = [
        "# The decisions register, prototype",
        "",
        f"Generated by `.claude/scripts/audit/decisions.py` from the tree. Rows: {len(rows)}. "
        f"With no stated home (`unstated`): {unstated}.",
        "",
        "By source: " + "; ".join(f"{k} {v}" for k, v in sorted(by_kind.items())) + ".",
        "",
        "By decider: " + "; ".join(f"{k} {v}" for k, v in sorted(by_decider.items())) + ".",
        "",
        "| Source | Decided by | Where | Date | Package | What was decided | Holds now | Status |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(
            f"| {r.source_id} | {r.decided_by} | `{r.where}` | {r.date} | {r.package} | "
            f"{r.decided} | {r.holds_now} | {r.status} |"
        )
    arguments.markdown.parent.mkdir(parents=True, exist_ok=True)
    arguments.markdown.write_text("\n".join(lines) + "\n", encoding="utf-8")
    arguments.json.write_text(
        json.dumps([asdict(r) for r in rows], indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"{len(rows)} rows; by source: {by_kind}; by decider: {by_decider}; unstated: {unstated}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

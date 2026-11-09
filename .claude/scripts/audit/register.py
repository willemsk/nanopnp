"""Number the written-knowledge audit's findings ``AUD-nn`` and write its findings register.

Reads, under ``docs/code_reviews/CODE_REVIEW_039/raw/``: every ``| XXX-nn |`` row of
``reader-*.md`` and ``own-findings.md`` (ten cells in the brief's schema, split on a bar with
whitespace on both sides, so a bar inside a code span or a formula stays in its cell);
``dispositions.tsv`` (``id``, ``status``, ``note``, ``extra_where``), which gives a finding its
state, an unlisted id being ``your call``; ``commits.tsv`` (``category``, ``sha``), which turns a
``fix:<category>`` state into ``fixed <sha>``; and the ``| Hit | Reason |`` rows of
``own-dismissals.md``.

Writes ``docs/code_reviews/CODE_REVIEW_039/findings.md``: the counts, the source-to-``AUD`` map,
the findings by axis ranked high, medium, low, and the dismissed table (the dismissed findings,
then the mechanical hits dismissed). ``AUD-nn`` runs in the order ORC, SPA, SPB, SPC, SPD, KGE,
KNU, DOC, CLD, KST, KPH, WLK, each prefix in numeric order, so a re-run on the same rows gives the
same numbers. Nothing is read but the tree; ``--at`` names the commit the counts belong to.

Run it as ``uv run .claude/scripts/audit/register.py --at <sha>``.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scope import ROOT

ATTACHMENTS = ROOT / "docs" / "code_reviews" / "CODE_REVIEW_039"
RAW = ATTACHMENTS / "raw"
PREFIXES = ("ORC", "SPA", "SPB", "SPC", "SPD", "KGE", "KNU", "DOC", "CLD", "KST", "KPH", "WLK")
AXES = ("accuracy", "clarity", "efficiency", "redundancy", "organisation")
SEVERITIES = ("high", "medium", "low")
COLUMNS = (
    "ID (AUD-nn)",
    "Axis",
    "Severity",
    "Where",
    "Defect",
    "Evidence",
    "Proposed edit",
    "Saves",
    "Breaks",
    "Status",
)
FINDING_ROW = re.compile(r"^\|\s*([A-Z]{3})-(\d+)\s*\|")
SEPARATOR = re.compile(r"(?<=\s)\|(?=\s)")
BARE_BAR = re.compile(r"(?<!\\)\|")


@dataclass
class Finding:
    """One row of a reader's or the orchestrator's table, with its disposition applied."""

    source: str
    cells: list[str]
    state: str = "your call"
    note: str = ""
    aud: str = ""

    @property
    def axis(self) -> str:
        return self.cells[1].lower()

    @property
    def severity(self) -> str:
        return self.cells[2].lower()

    @property
    def reader_status(self) -> str:
        return self.cells[9]


@dataclass
class Register:
    """The findings in ``AUD`` order and the mechanical hits dismissed."""

    findings: list[Finding] = field(default_factory=list)
    hits: list[tuple[str, str]] = field(default_factory=list)


def _cells(line: str) -> list[str]:
    """Split a table row on the bars that have whitespace on both sides."""
    text = line.strip()
    text = text[1:] if text.startswith("|") else text
    text = text[:-1] if text.endswith("|") else text
    return [cell.strip() for cell in SEPARATOR.split(text)]


def _escape(cell: str) -> str:
    """Escape a bare bar so the cell survives a Markdown table."""
    return BARE_BAR.sub(r"\\|", cell)


def _read_tsv(path: Path, width: int) -> list[list[str]]:
    rows: list[list[str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        parts = line.rstrip("\n").split("\t")
        rows.append([part.strip() for part in parts] + [""] * (width - len(parts)))
    return rows


def _read_findings() -> list[Finding]:
    found: dict[str, Finding] = {}
    for path in [*sorted(RAW.glob("reader-*.md")), RAW / "own-findings.md"]:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            match = FINDING_ROW.match(line)
            if not match:
                continue
            cells = _cells(line)
            if len(cells) != len(COLUMNS):
                raise SystemExit(
                    f"register.py: {path.name}:{number} has {len(cells)} cells, not {len(COLUMNS)}"
                )
            source = f"{match.group(1)}-{int(match.group(2)):02d}"
            if source in found:
                raise SystemExit(f"register.py: {source} appears twice ({path.name}:{number})")
            if cells[1].lower() not in AXES or cells[2].lower() not in SEVERITIES:
                raise SystemExit(
                    f"register.py: {source} has axis {cells[1]!r}, severity {cells[2]!r}"
                )
            found[source] = Finding(source, cells)
    return list(found.values())


def _apply_dispositions(findings: list[Finding]) -> None:
    commits = {category: sha for category, sha, *_ in _read_tsv(RAW / "commits.tsv", 2)}
    dispositions = {row[0]: row for row in _read_tsv(RAW / "dispositions.tsv", 4)}
    for finding in findings:
        row = dispositions.get(finding.source)
        if row is None:
            continue
        _, status, note, extra_where = row
        if extra_where:
            finding.cells[3] = f"{finding.cells[3]}; {extra_where}"
        if status.startswith("fix:"):
            category = status[4:]
            sha = commits.get(category)
            finding.state = f"fixed {sha}" if sha else f"to fix ({category})"
        elif status == "dismissed":
            finding.state = "dismissed"
        elif status == "your call":
            finding.state = "your call"
        else:
            raise SystemExit(f"register.py: {finding.source} has the unknown state {status!r}")
        finding.note = note
    unknown = set(dispositions) - {finding.source for finding in findings}
    if unknown:
        raise SystemExit(f"register.py: dispositions.tsv names unknown ids {sorted(unknown)}")


def _number(findings: list[Finding]) -> list[Finding]:
    def key(finding: Finding) -> tuple[int, int]:
        prefix, number = finding.source.split("-")
        return PREFIXES.index(prefix), int(number)

    ordered = sorted(findings, key=key)
    for index, finding in enumerate(ordered, 1):
        finding.aud = f"AUD-{index:02d}"
    return ordered


def _read_hits() -> list[tuple[str, str]]:
    hits: list[tuple[str, str]] = []
    for line in (RAW / "own-dismissals.md").read_text(encoding="utf-8").splitlines():
        if not line.startswith("| ") or line.startswith("| Hit") or line.startswith("|---"):
            continue
        cells = _cells(line)
        if len(cells) != 2:
            raise SystemExit(
                f"register.py: own-dismissals.md row has {len(cells)} cells: {line[:60]}"
            )
        hits.append((cells[0], cells[1]))
    return hits


def build() -> Register:
    """Read the raw tables, apply the dispositions and number the findings."""
    findings = _read_findings()
    _apply_dispositions(findings)
    return Register(_number(findings), _read_hits())


def _status(finding: Finding) -> str:
    """Render the Status cell: the state, the disposition's note and a reader's unchecked mark."""
    parts = [finding.state]
    if finding.state == "dismissed":
        return f"dismissed: {finding.note}" if finding.note else "dismissed"
    if finding.note:
        parts.append(f"({finding.note})")
    if finding.reader_status.lower().startswith("unchecked"):
        parts.append(f"({finding.reader_status})")
    return " ".join(parts)


def _row(cells: list[str]) -> str:
    return "| " + " | ".join(_escape(cell) for cell in cells) + " |"


def _header(columns: tuple[str, ...]) -> list[str]:
    return [_row(list(columns)), "|" + "---|" * len(columns)]


def _finding_cells(finding: Finding) -> list[str]:
    cells = list(finding.cells)
    cells[0] = f"{finding.aud} ({finding.source})"
    cells[9] = _status(finding)
    return cells


def _live(register: Register) -> list[Finding]:
    return [finding for finding in register.findings if finding.state != "dismissed"]


def _counts(register: Register) -> list[str]:
    live = _live(register)
    lines = ["## Counts", ""]
    lines += _header(("Axis", *SEVERITIES, "Total"))
    for axis in AXES:
        by_axis = [finding for finding in live if finding.axis == axis]
        counts = [str(sum(1 for finding in by_axis if finding.severity == s)) for s in SEVERITIES]
        lines.append(_row([axis, *counts, str(len(by_axis))]))
    totals = [str(sum(1 for finding in live if finding.severity == s)) for s in SEVERITIES]
    lines.append(_row(["all axes", *totals, str(len(live))]))
    states = Counter(
        "fixed"
        if finding.state.startswith("fixed")
        else "to fix"
        if finding.state.startswith("to fix")
        else finding.state
        for finding in register.findings
    )
    lines += ["", _row(["State", "Findings"]), "|---|---|"]
    for state in ("fixed", "to fix", "your call", "dismissed"):
        if states.get(state):
            lines.append(_row([state, str(states[state])]))
    sources = Counter(finding.source.split("-")[0] for finding in register.findings)
    lines += ["", _row(["Source", "Findings", "AUD range"]), "|---|---|---|"]
    for prefix in PREFIXES:
        auds = [finding.aud for finding in register.findings if finding.source.startswith(prefix)]
        if auds:
            lines.append(_row([prefix, str(sources[prefix]), f"{auds[0]} to {auds[-1]}"]))
    return lines


def _map(register: Register) -> list[str]:
    lines = ["## Source to AUD map", ""]
    lines += _header(("AUD", "Source", "Axis", "Severity", "State"))
    for finding in register.findings:
        state = finding.state.split(" (")[0]
        lines.append(_row([finding.aud, finding.source, finding.axis, finding.severity, state]))
    return lines


def _by_axis(register: Register) -> list[str]:
    lines = ["## Findings by axis", ""]
    lines.append(
        "Ranked high, medium, low within each axis, then by number. A dismissed finding is in "
        "*Dismissed* below, not here."
    )
    for axis in AXES:
        rows = [finding for finding in _live(register) if finding.axis == axis]
        lines += ["", f"### {axis.capitalize()} ({len(rows)})", ""]
        lines += _header(COLUMNS)
        for severity in SEVERITIES:
            for finding in rows:
                if finding.severity == severity:
                    lines.append(_row(_finding_cells(finding)))
    return lines


def _dismissed(register: Register) -> list[str]:
    dismissed = [finding for finding in register.findings if finding.state == "dismissed"]
    lines = ["## Dismissed", "", f"### Findings dismissed ({len(dismissed)})", ""]
    lines += _header(("AUD", "Source", "Where", "Defect", "Reason"))
    for finding in dismissed:
        lines.append(
            _row([finding.aud, finding.source, finding.cells[3], finding.cells[4], finding.note])
        )
    lines += ["", f"### Mechanical hits dismissed ({len(register.hits)})", ""]
    lines.append("Every step 1 hit that became no finding, from `raw/own-dismissals.md`.")
    lines += ["", *_header(("Hit (file, probe)", "Reason"))]
    for hit, reason in register.hits:
        lines.append(_row([hit, reason]))
    return lines


def render(register: Register, at: str) -> str:
    """Return the findings register as Markdown."""
    live = len(_live(register))
    lines = [
        "# CODE_REVIEW_039: the findings register",
        "",
        f"Written by `.claude/scripts/audit/register.py` at `{at}` from the tables under `raw/`: "
        "the ten readers' returns (`reader-*.md`), the orchestrator's own findings and the task "
        "walks "
        "(`own-findings.md`), the dispositions (`dispositions.tsv`) and the fix commits "
        f"(`commits.tsv`). {len(register.findings)} findings, {live} of them live; every one has "
        "one `AUD-nn` number and one state. The schema is the brief's: `fixed <sha>`, `your call` "
        "or `dismissed <reason>`; a `to fix (<category>)` state is a fix not yet committed. The "
        "line numbers in *Where* are those of the audited commit, a5039af.",
        "",
    ]
    lines += _counts(register)
    lines += ["", *_map(register)]
    lines += ["", *_by_axis(register)]
    lines += ["", *_dismissed(register)]
    return "\n".join(lines) + "\n"


def commit(ref: str = "HEAD") -> str:
    """Return the short sha a ref names, so that a record never says ``HEAD``."""
    result = subprocess.run(
        ["git", "rev-parse", "--short", ref],
        capture_output=True,
        text=True,
        check=False,
        cwd=ROOT,
    )
    return result.stdout.strip() or "unknown"


def main(argv: list[str] | None = None) -> int:
    """Run the command line and return the process exit status."""
    parser = argparse.ArgumentParser(
        description="Number the audit's findings and write the register."
    )
    parser.add_argument("--at", default=None, help="the commit the counts name (default: HEAD)")
    parser.add_argument(
        "--out", type=Path, default=ATTACHMENTS / "findings.md", help="the Markdown to write"
    )
    arguments = parser.parse_args(argv)
    register = build()
    arguments.out.write_text(render(register, commit(arguments.at or "HEAD")), encoding="utf-8")
    live = _live(register)
    sys.stdout.write(
        f"{len(register.findings)} findings ({len(live)} live, "
        f"{len(register.findings) - len(live)} dismissed), {len(register.hits)} hits dismissed, "
        f"written to {arguments.out.relative_to(ROOT).as_posix()}\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

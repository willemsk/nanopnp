"""Draw the redundancy map and the sediment list from the audit's findings register.

Reads ``docs/code_reviews/CODE_REVIEW_039/findings.md`` (the output of ``register.py``). Writes,
beside it, ``redundancy-map.md``: every live finding on the redundancy axis as one meaning with
its homes and its proposed home; and ``sediment.md``: every live finding on the efficiency axis,
the text to move to a record or to delete, ordered by the token delta its *Saves* cell states
(a figure in tokens where the cell gives one, the cell's own words otherwise). Deterministic:
nothing is read but the register.

Run it as ``uv run .claude/scripts/audit/maps.py``.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scope import ROOT

ATTACHMENTS = ROOT / "docs" / "code_reviews" / "CODE_REVIEW_039"
SEPARATOR = re.compile(r"(?<=\s)\|(?=\s)")
TOKENS = re.compile(r"([\d][\d,.]*)\s*(k)?\s*tokens", re.I)


def _cells(line: str) -> list[str]:
    text = line.strip()
    text = text[1:] if text.startswith("|") else text
    text = text[:-1] if text.endswith("|") else text
    return [cell.strip() for cell in SEPARATOR.split(text)]


def _rows(axis: str) -> list[list[str]]:
    rows: list[list[str]] = []
    current = None
    for line in (ATTACHMENTS / "findings.md").read_text(encoding="utf-8").splitlines():
        heading = re.match(r"^### (\w+)", line)
        if heading:
            current = heading.group(1).lower()
        if current == axis and line.startswith("| AUD-"):
            rows.append(_cells(line))
    return rows


def _tokens(saves: str) -> int | None:
    match = TOKENS.search(saves)
    if not match:
        return None
    number = float(match.group(1).replace(",", ""))
    return int(number * 1000) if match.group(2) else int(number)


def _redundancy(at: str) -> str:
    rows = _rows("redundancy")
    lines = [
        "# CODE_REVIEW_039: the redundancy map",
        "",
        f"Written by `.claude/scripts/audit/maps.py` at `{at}` from `findings.md`. One row per "
        f"live finding on the redundancy axis ({len(rows)} rows): the meaning that has more than "
        "one home, its homes as the finding names them, and the home the finding proposes. The "
        "author rules each; none is applied here.",
        "",
        "| Finding | Severity | The meaning | Its homes | Proposed home | Saves | Status |",
        "|---|---|---|---|---|---|---|",
    ]
    for cells in rows:
        picked = (cells[0], cells[2], cells[4], cells[3], cells[6], cells[7], cells[9])
        lines.append("| " + " | ".join(picked) + " |")
    return "\n".join(lines) + "\n"


def _sediment(at: str) -> str:
    rows = _rows("efficiency")
    keyed = sorted(rows, key=lambda c: -(_tokens(c[7]) or 0))
    total = sum(_tokens(c[7]) or 0 for c in rows)
    lines = [
        "# CODE_REVIEW_039: the sediment list",
        "",
        f"Written by `.claude/scripts/audit/maps.py` at `{at}` from `findings.md`. One row per "
        f"live finding on the efficiency axis ({len(rows)} rows): text on a live reading path that "
        "a dated event made history, that restates a record, or that a reader of the path does not "
        "need, with where the finding would move it or whether it goes, ordered by the token "
        f"delta the finding states. The stated deltas sum to about {total:,} tokens; a row with no "
        "figure counts as nought. The author rules each; none is applied here.",
        "",
        "| Finding | Severity | Where | What is sediment | Move or delete | Token delta | Status |",
        "|---|---|---|---|---|---|---|",
    ]
    for cells in keyed:
        tokens = _tokens(cells[7])
        delta = f"≈{tokens:,} ({cells[7]})" if tokens is not None else cells[7]
        picked = (cells[0], cells[2], cells[3], cells[4], cells[6], delta, cells[9])
        lines.append("| " + " | ".join(picked) + " |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    """Write both maps and return the process exit status."""
    at = (argv or sys.argv[1:] or ["HEAD"])[0]
    (ATTACHMENTS / "redundancy-map.md").write_text(_redundancy(at), encoding="utf-8")
    (ATTACHMENTS / "sediment.md").write_text(_sediment(at), encoding="utf-8")
    sys.stdout.write("written redundancy-map.md and sediment.md\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

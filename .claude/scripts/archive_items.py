"""Move each closed review item to the archive beside its register (SPECIFICATION.md §8.4.6).

A row of ``docs/project/review-findings.md`` is closed when its status is ``fixed``, ``declined``
or ``wontfix``. The script moves each closed row, and its section of ``review-items.md``, to
``docs/project/review-archive.md``, merging into what the archive holds, in number order. Then it
points every link to a moved section at the archive: in each tracked Markdown file and in
``docs/code_reviews/CODE_REVIEW_039/decisions.json``. No ``REV`` number is reused, and nothing
else in the two register files changes (§8.2.50 AZ12). A phase's close runs it.

It moves nothing, and exits 1, while a line of the log's table is not a ``REV`` row, two items
share a number, or a closed item's number is already in the archive: rewriting the files then
would drop a row or a section.

Run it as ``uv run .claude/scripts/archive_items.py``.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PROJECT = ROOT / "docs" / "project"
LOG = PROJECT / "review-findings.md"
ITEMS = PROJECT / "review-items.md"
ARCHIVE = PROJECT / "review-archive.md"
ATTACHMENT = ROOT / "docs" / "code_reviews" / "CODE_REVIEW_039" / "decisions.json"
CLOSED = {"fixed", "declined", "wontfix"}
ROW = re.compile(r"^\|\s*REV-(\d+)\s*\|")
SECTION = re.compile(r"^### REV-(\d+)\b")
# A link's anchor is the section heading's slug, which starts with the item's number.
TO_ITEMS = re.compile(r"review-items\.md#rev-(\d+)(?=-)")
IN_PAGE = re.compile(r"\(#rev-(\d+)(?=-)")
# The archive's link to itself by name. One with a folder before the name keeps it.
OWN = re.compile(r"\(review-archive\.md#rev-(\d+)(?=-)")
HEADER = "| ID | Area | Severity | Status | Ruling | Finding |"
INTRODUCTION = """# Review archive

The closed items of [the review register](review-items.md) (§8.2.50 AZ12): each row the log set
`fixed`, `declined` or `wontfix`, with its section, moved here by `.claude/scripts/archive_items.py`
at the phase's close that closed it. Numbers are never reused; the open and owned items stay in
[the findings log](review-findings.md)."""


def _rows(lines: list[str]) -> tuple[int, int, dict[int, str]]:
    start = next(i for i, line in enumerate(lines) if line.startswith("| ID |"))
    end = start + 2
    rows: dict[int, str] = {}
    while end < len(lines) and lines[end].startswith("|"):
        match = ROW.match(lines[end])
        if match:
            rows[int(match.group(1))] = lines[end]
        end += 1
    return start, end, rows


def _sections(lines: list[str]) -> tuple[list[str], dict[int, list[str]]]:
    starts = [i for i, line in enumerate(lines) if SECTION.match(line)]
    sections: dict[int, list[str]] = {}
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else len(lines)
        match = SECTION.match(lines[start])
        if match:
            body = lines[start:end]
            while body and not body[-1].strip():
                body.pop()
            sections[int(match.group(1))] = body
    return lines[: starts[0]] if starts else lines, sections


def _status(row: str) -> str:
    return row.split("|")[4].strip()


def _front_matter(log: list[str]) -> list[str]:
    end = log.index("---", 1)
    return [line.replace("status: open", "status: closed") for line in log[: end + 1]]


def _relink_archive(text: str, kept: set[int]) -> str:
    # A section that is not kept is the archive's own: a link to it is in-page. An in-page link
    # to a kept section came with a moved one, and gains the register's name.
    text = TO_ITEMS.sub(
        lambda m: m.group(0) if int(m.group(1)) in kept else f"review-archive.md#rev-{m.group(1)}",
        text,
    )
    text = OWN.sub(lambda m: f"(#rev-{m.group(1)}", text)
    return IN_PAGE.sub(
        lambda m: f"(review-items.md#rev-{m.group(1)}" if int(m.group(1)) in kept else m.group(0),
        text,
    )


def _relink(text: str, moved: set[int], *, in_page: bool) -> str:
    text = TO_ITEMS.sub(
        lambda m: f"review-archive.md#rev-{m.group(1)}" if int(m.group(1)) in moved else m.group(0),
        text,
    )
    if in_page:
        text = IN_PAGE.sub(
            lambda m: (
                f"(review-archive.md#rev-{m.group(1)}" if int(m.group(1)) in moved else m.group(0)
            ),
            text,
        )
    return text


def _linking_files() -> list[Path]:
    listed = subprocess.run(
        ["git", "ls-files", "-z", "*.md"], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.split("\0")
    paths = [ROOT / name for name in listed if name]
    files = [path for path in paths if path.is_file() and path not in {LOG, ITEMS, ARCHIVE}]
    return [*files, ATTACHMENT] if ATTACHMENT.exists() else files


def main() -> int:
    """Move the closed items and rewrite the links; return the process exit status."""
    log = LOG.read_text(encoding="utf-8").splitlines()
    items = ITEMS.read_text(encoding="utf-8").splitlines()
    start, end, rows = _rows(log)
    head, sections = _sections(items)
    headed = sum(bool(SECTION.match(line)) for line in items)
    if len(rows) != end - start - 2 or len(sections) != headed:
        print(
            "archive_items.py: a line of the log's table is not a `| REV-nn |` row, or two items "
            "share a number (`uv run .claude/scripts/duplicates.py` names it); nothing is moved"
        )
        return 1
    moved = {number for number, row in rows.items() if _status(row) in CLOSED}
    kept = set(rows) - moved
    if not moved:
        print("archive_items.py: no closed item to move")
        return 0

    archived_rows: dict[int, str] = {}
    archived_sections: dict[int, list[str]] = {}
    if ARCHIVE.exists():
        archive = ARCHIVE.read_text(encoding="utf-8").splitlines()
        archived_rows = _rows(archive)[2]
        archived_sections = _sections(archive)[1]
    if reused := sorted(moved & (set(archived_rows) | set(archived_sections))):
        numbers = ", ".join(f"REV-{number}" for number in reused)
        print(f"archive_items.py: already in the archive: {numbers}; nothing is moved")
        return 1
    archived_rows |= {number: rows[number] for number in moved}
    archived_sections |= {number: sections[number] for number in moved if number in sections}

    body = [*_front_matter(log), "", INTRODUCTION, "", HEADER, "|---|---|---|---|---|---|"]
    body += [archived_rows[number] for number in sorted(archived_rows)]
    body += ["", "## Items", ""]
    for number in sorted(archived_sections):
        body += [*archived_sections[number], ""]
    ARCHIVE.write_text(_relink_archive("\n".join(body), kept), encoding="utf-8")

    log = [*log[: start + 2], *(rows[n] for n in sorted(kept)), *log[end:]]
    LOG.write_text(_relink("\n".join(log) + "\n", moved, in_page=False), encoding="utf-8")
    remaining: list[str] = list(head)
    for number in sorted(n for n in sections if n not in moved):
        remaining += [*sections[number], ""]
    ITEMS.write_text(_relink("\n".join(remaining), moved, in_page=True), encoding="utf-8")

    for path in _linking_files():
        text = path.read_text(encoding="utf-8")
        new = _relink(text, moved, in_page=False)
        if new != text:
            path.write_text(new, encoding="utf-8")
    print(f"archive_items.py: moved {len(moved)} items; {len(kept)} stay in the register")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

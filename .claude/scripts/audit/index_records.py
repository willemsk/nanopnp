"""Write an index for each record folder that has none, one line per file with its own status line.

Reads the Markdown files of ``docs/plans/``, ``docs/code_reviews/`` and ``docs/design/reviews/``:
each file's title (its first ``#`` heading) and its own status line, which is the first bold
``**Status: …**`` span of a plan, the dated header line under a code review's title, and the
first body line of a design review (which carries no status line). Writes ``index.md`` in each
of the three folders, listing the files in name order with their status lines, and nothing
else: no record changes. Deterministic: a re-run on the same files writes the same indexes.

Run it as ``uv run .claude/scripts/audit/index_records.py``.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scope import ROOT

STATUS = re.compile(r"\*\*Status:\s*(.*?)\*\*", re.DOTALL)
HEADING = re.compile(r"^#\s+(.*)$", re.MULTILINE)
LIMIT = 220

FOLDERS: dict[str, tuple[str, str]] = {
    "docs/plans": (
        "The plans",
        "Planning, not requirements: `SPECIFICATION.md` governs. `current.md` is the live "
        "navigation; every other file is a record. Each line quotes the file's own status line.",
    ),
    "docs/code_reviews": (
        "The code reviews",
        "One report per review, numbered in order (CLAUDE.md, *Code review reports*). Each line "
        "quotes the report's own header line: date, commit, scope, focus and status.",
    ),
    "docs/design/reviews": (
        "The design reviews",
        "The author's verdicts and the GUI reviewer's findings on each design round of the "
        "workbench (`docs/design/workbench.md`). Each line quotes the review's first sentence.",
    ),
}


def _title(text: str, path: Path) -> str:
    match = HEADING.search(text)
    return match.group(1).strip() if match else path.stem


def _first_paragraph(text: str) -> str:
    """Return the first paragraph after the title that is not front matter or a heading."""
    lines = text.splitlines()
    start = 0
    if lines and lines[0].strip() == "---":
        start = next((i + 1 for i in range(1, len(lines)) if lines[i].strip() == "---"), 0)
    for index in range(start, len(lines)):
        stripped = lines[index].strip()
        if stripped and not stripped.startswith("#"):
            paragraph = []
            for line in lines[index:]:
                if not line.strip():
                    break
                paragraph.append(line.strip())
            return " ".join(paragraph)
    return ""


def _clip(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= LIMIT else text[: LIMIT - 1].rstrip() + "…"


def _status(folder: str, text: str) -> str:
    if folder == "docs/plans":
        match = STATUS.search(text)
        return (_clip(match.group(1)) if match else "") or "no status line"
    return _clip(_first_paragraph(text)) or "no status line"


def _escape(text: str) -> str:
    return text.replace("|", "\\|")


def render(folder: str) -> str:
    """Return the index of ``folder`` as Markdown."""
    title, intro = FOLDERS[folder]
    lines = [
        f"# {title}",
        "",
        intro,
        "",
        "Written by `.claude/scripts/audit/index_records.py`; "
        "re-run it when a file is added or its status line changes.",
        "",
    ]
    for path in sorted((ROOT / folder).glob("*.md")):
        if path.name == "index.md":
            continue
        text = path.read_text(encoding="utf-8")
        lines.append(
            f"- [{_escape(_title(text, path))}]({path.name}): {_escape(_status(folder, text))}"
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    """Write the three indexes and return the process exit status."""
    for folder in FOLDERS:
        target = ROOT / folder / "index.md"
        target.write_text(render(folder), encoding="utf-8")
        count = sum(
            1 for line in target.read_text(encoding="utf-8").splitlines() if line.startswith("- [")
        )
        sys.stdout.write(f"{target.relative_to(ROOT).as_posix()}: {count} files\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

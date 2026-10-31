"""Name every number that two items of one register share (SPECIFICATION.md §8.4.4, §8.2.17 S20).

The registers are the requirement identifiers that the current specification defines, as a table
row ``| **VER-62** |`` or a ``**PHY-11.**`` paragraph; the ruling letters and the §8.2 numbers of
``specification/history/``; the ``REV-nn`` rows of ``docs/project/review-findings.md``; the
code-review reports; and the work-package plans of ``docs/plans/``. Two lanes that each add an
item can merge one number twice without a textual conflict, so ``/np-ship`` runs this after it
merges ``main``. The exit status is non-zero when any number is shared.

Run it as ``uv run .claude/scripts/duplicates.py``.
"""

from __future__ import annotations

import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "specification"
DEFINITION_ROW = re.compile(r"^\|\s*\*\*([A-Z]+-\d+)\*\*\s*\|")
DEFINITION_PARAGRAPH = re.compile(r"^\*\*([A-Z]+-\d+)\.\*\*")
RULING_ROW = re.compile(r"^\|\s*([A-Z]+\d+)\s*\|")
RECORD_HEADING = re.compile(r"^#+\s+(8\.2\.\d+)\s")
REV_ROW = re.compile(r"^\|\s*(REV-\d+)\s*\|")
REPORT = re.compile(r"CODE_REVIEW_(\d+)")
PLAN = re.compile(r"^wp(\d+(?:\.\d+)?)-")


def _scan(paths: list[Path], pattern: re.Pattern[str]) -> dict[str, list[str]]:
    """Map each number the pattern captures to the places it occurs."""
    found: dict[str, list[str]] = defaultdict(list)
    for path in paths:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            match = pattern.match(line)
            if match:
                found[match.group(1)].append(f"{path.relative_to(ROOT)}:{number}")
    return found


def _names(paths: list[Path], pattern: re.Pattern[str]) -> dict[str, list[str]]:
    """Map each number the pattern captures from a file name to the files that carry it."""
    found: dict[str, list[str]] = defaultdict(list)
    for path in paths:
        match = pattern.search(path.name)
        if match:
            found[match.group(1)].append(str(path.relative_to(ROOT)))
    return found


def main() -> int:
    """Print each shared number with its places, and return 1 if there is one."""
    history = sorted((BUNDLE / "history").glob("*.md"))
    current = sorted(
        p for p in BUNDLE.rglob("*.md") if "history" not in p.relative_to(BUNDLE).parts
    )
    registers = {
        "requirement identifier": _scan(current, DEFINITION_ROW),
        "ruling letter": _scan(history, RULING_ROW),
        "history record": _scan(history, RECORD_HEADING),
        "review finding": _scan([ROOT / "docs/project/review-findings.md"], REV_ROW),
        "code-review report": _names(sorted((ROOT / "docs/code_reviews").glob("*.md")), REPORT),
        "work package": _names(sorted((ROOT / "docs/plans").glob("wp*.md")), PLAN),
    }
    for key, places in _scan(current, DEFINITION_PARAGRAPH).items():
        registers["requirement identifier"].setdefault(key, []).extend(places)
    shared = 0
    for register, numbers in registers.items():
        for key, places in sorted(numbers.items()):
            if len(places) > 1:
                shared += 1
                print(f"{register} {key}: {', '.join(places)}")
    return 1 if shared else 0


if __name__ == "__main__":
    sys.exit(main())

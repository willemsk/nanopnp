"""Count the words a work package's session reads (WP43 D14; SPECIFICATION.md §8.2.10 J11).

The reading set is ``CLAUDE.md``, the ``wp-implement`` skill, the model policy, the knowledge
index, ``docs/plans/current.md`` and the plan's Execution brief (the text from
``## Execution brief`` to the next ``## `` heading), plus each rule file in ``.claude/rules/``
whose ``paths`` match a path the plan's *Work items* name in backticks. Words are
``str.split`` tokens. The script prints each file's count, the total, and the total without the
brief, and fails on a brief over 1,600 words.

With ``--at <rev>`` every file is read at that revision through ``git show``.

Run it as ``uv run .claude/scripts/reading_set.py docs/plans/wp43-development-loop.md``.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIXED = (
    "CLAUDE.md",
    ".claude/skills/wp-implement/SKILL.md",
    ".claude/model-policy.md",
    ".knowledge/00-index.md",
    "docs/plans/current.md",
)
RULES = ".claude/rules"
BRIEF_LIMIT = 1600
"""Words an Execution brief may hold (D14: `/wp-plan`'s former 1,200 target, made a limit)."""


def _show(rev: str, name: str) -> str:
    """Return ``name`` as committed at ``rev``."""
    result = subprocess.run(
        ["git", "show", f"{rev}:{name}"], cwd=ROOT, capture_output=True, text=True, check=True
    )
    return result.stdout


def _words(text: str) -> int:
    """Count whitespace-separated tokens holding an ASCII character (``wc -w`` in the C locale).

    A lone dash or arrow is not a word. The plan's figures (9,849 at ``d630f85``) were
    counted so, and ``wc`` in a UTF-8 locale would count differently.
    """
    return sum(1 for token in text.split() if any(ord(char) < 0x80 for char in token))


def execution_brief(plan_text: str) -> str:
    """Return the text after the ``## Execution brief`` heading up to the next ``## `` heading."""
    match = re.search(r"^## Execution brief\n(.*?)(?=^## |\Z)", plan_text, re.S | re.M)
    return match.group(1) if match else ""


def _glob(pattern: str) -> re.Pattern[str]:
    """Translate a rule's path glob: ``**`` crosses directories, ``*`` does not."""
    out = ""
    index = 0
    while index < len(pattern):
        if pattern.startswith("**/", index):
            out += "(?:.*/)?"
            index += 3
        elif pattern.startswith("**", index):
            out += ".*"
            index += 2
        elif pattern[index] == "*":
            out += "[^/]*"
            index += 1
        else:
            out += re.escape(pattern[index])
            index += 1
    return re.compile(out)


def rule_paths(text: str) -> list[str]:
    """Return the ``paths`` globs of a rule file's frontmatter."""
    front = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if front is None:
        return []
    return re.findall(r"^\s*-\s*\"?([^\"\n]+?)\"?\s*$", front.group(1), re.M)


def named_paths(plan_text: str) -> list[str]:
    """Return the backticked tokens of the plan's *Work items* section."""
    match = re.search(r"^### Work items\n(.*?)(?=^#{1,3} |\Z)", plan_text, re.S | re.M)
    return re.findall(r"`([^`\s]+)`", match.group(1)) if match else []


def triggered_rules(plan_text: str, rules_dir: Path) -> list[Path]:
    """Return the rule files whose ``paths`` match a path the plan's Work items name."""
    named = named_paths(plan_text)
    found: list[Path] = []
    for rule in sorted(rules_dir.glob("*.md")):
        patterns = [_glob(path) for path in rule_paths(rule.read_text(encoding="utf-8"))]
        if any(pattern.fullmatch(name) for pattern in patterns for name in named):
            found.append(rule)
    return found


def _rules_at(rev: str, into: Path) -> Path:
    """Write the rule files committed at ``rev`` into ``into`` and return that directory."""
    listing = subprocess.run(
        ["git", "ls-tree", "--name-only", rev, f"{RULES}/"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    directory = into / RULES
    directory.mkdir(parents=True)
    for name in listing:
        (directory / Path(name).name).write_text(_show(rev, name), encoding="utf-8")
    return directory


def main(argv: list[str] | None = None) -> int:
    """Run the command line and return the process exit status."""
    parser = argparse.ArgumentParser(description="Count a work package's reading set.")
    parser.add_argument("plan", help="the plan, relative to the repository root")
    parser.add_argument("--at", metavar="REV", help="read every file at this revision")
    arguments = parser.parse_args(argv)
    with tempfile.TemporaryDirectory() as scratch:
        if arguments.at:
            rev = arguments.at
            texts = {name: _show(rev, name) for name in FIXED}
            plan_text = _show(rev, arguments.plan)
            rules_dir = _rules_at(rev, Path(scratch))
        else:
            texts = {name: (ROOT / name).read_text(encoding="utf-8") for name in FIXED}
            plan_path = Path(arguments.plan)
            plan_text = (plan_path if plan_path.is_absolute() else ROOT / plan_path).read_text(
                encoding="utf-8"
            )
            rules_dir = ROOT / RULES
        counts = {name: _words(text) for name, text in texts.items()}
        for rule in triggered_rules(plan_text, rules_dir) if rules_dir.is_dir() else []:
            counts[f"{RULES}/{rule.name}"] = _words(rule.read_text(encoding="utf-8"))
    brief = _words(execution_brief(plan_text))
    fixed = sum(counts.values())
    for name, count in counts.items():
        sys.stdout.write(f"{count:>7,}  {name}\n")
    sys.stdout.write(f"{brief:>7,}  Execution brief\n")
    sys.stdout.write(f"{fixed + brief:>7,}  total\n{fixed:>7,}  total without the brief\n")
    if brief > BRIEF_LIMIT:
        sys.stderr.write(
            f"reading_set.py: the Execution brief has {brief:,} words, "
            f"over the {BRIEF_LIMIT:,} limit\n"
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

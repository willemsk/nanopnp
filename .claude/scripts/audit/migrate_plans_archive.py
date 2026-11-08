"""Move every plan of ``docs/plans/`` into its phase's folder once, and rewrite every path to it.

The one move of §8.2.36 AL5 as amended by AL28; run once by WP5.10 and not kept among the
scripts. A plan goes by phase membership: ``wp1`` to ``wp6`` and the Phase 0 plans to
``phase-0/``, ``wp7`` to ``wp16`` to ``phase-1/``, ``wp17`` to ``wp25`` to ``phase-2/``, ``wp26``
to ``wp34`` to ``phase-3/``, ``wp35`` to ``wp60`` to ``phase-4/``, ``wp5.<nn>`` to ``phase-5/``; a
phase plan or record by its number; the six standalone briefs and reviews to ``sessions/``;
``current.md`` and ``index.md`` stay. A file it cannot place stops it.

In every tracked file that decodes as UTF-8: in Markdown, each relative link (``links.py``'s
``LINK``, code masked) whose source or target moved is written again relative to the source's new
folder, its anchor kept; then, everywhere, code included, each written ``docs/plans/<name>`` of a
moved plan becomes its new path, unless ``<commit>:`` pins it to a revision where the old path
holds. Nothing else changes. ``--dry-run`` prints the counts, by folder, and writes nothing.

Run it as ``uv run .claude/scripts/audit/migrate_plans_archive.py [--dry-run]``.
"""

from __future__ import annotations

import argparse
import posixpath
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from links import CODE, LINK, SCHEME

ROOT = Path(__file__).resolve().parents[3]
PLANS = "docs/plans"
STAY = frozenset({"current.md", "index.md"})
SESSIONS = frozenset(
    {
        "copilot-host.md",
        "history-prose-review.md",
        "kb-audit-brief.md",
        "notebooks-review-for-wp54.md",
        "okf-converter-rules.md",
        "okf-knowledge-bundle.md",
    }
)
WP = re.compile(r"^wp(\d+)-")
WP_PHASE_5 = re.compile(r"^wp5\.\d+-")
PHASE = re.compile(r"^phase-(\d+)-")
# The first and last package of each phase before Phase 5's numbering.
PHASE_OF_WP = ((0, 1, 6), (1, 7, 16), (2, 17, 25), (3, 26, 34), (4, 35, 60))


def _folder(name: str) -> str:
    if name in SESSIONS:
        return "sessions"
    if WP_PHASE_5.match(name):
        return "phase-5"
    if match := WP.match(name):
        number = int(match.group(1))
        for phase, first, last in PHASE_OF_WP:
            if first <= number <= last:
                return f"phase-{phase}"
    if match := PHASE.match(name):
        return f"phase-{match.group(1)}"
    raise SystemExit(f"{PLANS}/{name}: no phase folder")


def _tracked() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return [name for name in result.stdout.split("\0") if name]


def moved_plans(tracked: list[str]) -> dict[str, str]:
    """Map each moved plan's repository path to its new one."""
    moved = {}
    for path in tracked:
        folder, name = posixpath.split(path)
        if folder == PLANS and path.endswith(".md") and name not in STAY:
            moved[path] = f"{PLANS}/{_folder(name)}/{name}"
    return moved


def _area(path: str) -> str:
    parts = path.split("/")
    if len(parts) == 1:
        return path
    if parts[0] == "docs":
        return "/".join(parts[:2])
    return parts[0]


def _links(text: str, old: str, new: str, moved: dict[str, str]) -> tuple[str, int]:
    masked = CODE.sub(lambda match: " " * len(match.group(0)), text)
    pieces: list[str] = []
    cursor = count = 0
    for match in LINK.finditer(masked):
        target = match.group(2)
        if SCHEME.match(target) or target.startswith("#"):
            continue
        path, hash_, anchor = target.partition("#")
        if not path:
            continue
        old_target = posixpath.normpath(posixpath.join(posixpath.dirname(old), path))
        new_target = moved.get(old_target, old_target)
        if old_target not in moved and old not in moved:
            continue
        written = posixpath.relpath(new_target, posixpath.dirname(new) or ".")
        if path.endswith("/") and not written.endswith("/"):
            written += "/"
        rewritten = f"{written}{hash_}{anchor}"
        if rewritten == target:
            continue
        pieces += [text[cursor : match.start(2)], rewritten]
        cursor = match.end(2)
        count += 1
    pieces.append(text[cursor:])
    return "".join(pieces), count


def main(argv: list[str] | None = None) -> int:
    """Perform or rehearse the move and return the process exit status."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="print the counts, write nothing")
    arguments = parser.parse_args(argv)
    tracked = _tracked()
    moved = moved_plans(tracked)
    names = sorted((posixpath.basename(path) for path in moved), key=len, reverse=True)
    written_path = re.compile(
        rf"(?<![0-9a-f]{{7}}:){re.escape(PLANS)}/({'|'.join(map(re.escape, names))})(?![\w.-])"
    )
    links: Counter[str] = Counter()
    written: Counter[str] = Counter()
    changed: dict[str, str] = {}
    for path in tracked:
        source = ROOT / path
        if source.is_symlink() or not source.is_file():
            continue
        try:
            text = source.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        new = moved.get(path, path)
        result = text
        if path.endswith(".md"):
            result, count = _links(result, path, new, moved)
            links[_area(path)] += count
        result, count = written_path.subn(lambda match: moved[f"{PLANS}/{match.group(1)}"], result)
        written[_area(path)] += count
        if result != text:
            changed[path] = result
    folders = Counter(posixpath.dirname(new) for new in moved.values())
    sys.stdout.write(f"plans moved: {len(moved)}\n")
    for folder, count in sorted(folders.items()):
        sys.stdout.write(f"  {folder}: {count}\n")
    for label, counts in (("relative links", links), ("written paths", written)):
        sys.stdout.write(f"{label} rewritten: {sum(counts.values())}\n")
        for area, count in counts.most_common():
            if count:
                sys.stdout.write(f"  {area}: {count}\n")
    sys.stdout.write(f"files changed: {len(changed)}\n")
    if arguments.dry_run:
        return 0
    for path, text in changed.items():
        (ROOT / path).write_text(text, encoding="utf-8")
    for old, new in moved.items():
        (ROOT / new).parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "mv", old, new], cwd=ROOT, check=True)
    subprocess.run(["git", "add", "--", *(moved.get(p, p) for p in changed)], cwd=ROOT, check=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())

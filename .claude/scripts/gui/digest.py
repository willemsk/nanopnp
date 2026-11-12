"""Group a render's near-identical shots, and build the digest page the author marks.

    uv run python .claude/scripts/gui/digest.py similar <index.json>...
    uv run python .claude/scripts/gui/digest.py build <picks.json> <index.json>... <out-dir>

``similar`` prints the groups of light shots whose pictures differ by at most ``NEAR`` of the 256
bits of a difference hash: the shots one pick can stand for. ``build`` reads the picks
(`.claude/skills/np-gui/publish.md` gives their form), assigns every shot of the indexes to one
pick, the pick itself or the pick whose matching ``stands_for`` pattern is the most specific, and
writes ``index.html``, ``digest.json`` and the picks' PNGs into ``<out-dir>``. A later index
replaces an earlier one's shot of the same id. It exits 1 if a shot is left to no pick, a pick is
not in the render, or there are more than ``MAX_PICKS``.
"""

from __future__ import annotations

import fnmatch
import html
import json
import re
import shutil
import sys
from pathlib import Path

from PIL import Image

MAX_PICKS = 20
NEAR = 8
TEMPLATE = Path(__file__).with_name("digest.tpl.html")


def shots(indexes: list[str]) -> dict[str, Path]:
    """Return each shot id's PNG, a later index's over an earlier one's."""
    found: dict[str, Path] = {}
    for index in indexes:
        root = Path(index).parent
        for entry in json.loads(Path(index).read_text()):
            found[entry["id"]] = root / entry["file"]
    return found


def dhash(path: Path, size: int = 16) -> int:
    """Return a picture's difference hash: one bit per neighbouring pair of a grey thumbnail."""
    grey = Image.open(path).convert("L").resize((size + 1, size))
    bits = 0
    for row in range(size):
        for col in range(size):
            bits = bits << 1 | (grey.getpixel((col, row)) > grey.getpixel((col + 1, row)))
    return bits


def similar(indexes: list[str]) -> None:
    """Print the groups of light shots that one pick can stand for."""
    hashes = {sid: dhash(path) for sid, path in shots(indexes).items() if sid.endswith("-light")}
    left = sorted(hashes)
    while left:
        first = left.pop(0)
        group = [first] + [s for s in left if (hashes[first] ^ hashes[s]).bit_count() <= NEAR]
        left = [s for s in left if s not in group]
        print(f"{len(group):3d}  " + "  ".join(group))


def expand(pattern: str) -> list[str]:
    """Expand shell braces: ``a-{b,c}-d`` gives ``a-b-d`` and ``a-c-d``."""
    match = re.search(r"\{([^{}]*)\}", pattern)
    if not match:
        return [pattern]
    head, tail = pattern[: match.start()], pattern[match.end() :]
    return [x for alt in match.group(1).split(",") for x in expand(head + alt + tail)]


def build(picks_path: str, indexes: list[str], out: Path) -> int:
    """Write the digest page; return 1 if the picks do not cover the render."""
    spec = json.loads(Path(picks_path).read_text())
    picks = spec["picks"]
    found = shots(indexes)
    if len(picks) > MAX_PICKS:
        print(f"{len(picks)} picks; a digest holds at most {MAX_PICKS}", file=sys.stderr)
        return 1
    absent = [p["id"] for p in picks if p["id"] not in found]
    if absent:
        print(f"picks not in the render: {absent}", file=sys.stderr)
        return 1
    members: dict[str, list[str]] = {p["id"]: [] for p in picks}
    for sid in found:
        if sid in members:
            members[sid].append(sid)
            continue
        best, score = None, -1
        for pick in picks:
            for pattern in (q for raw in pick["stands_for"] for q in expand(raw)):
                if fnmatch.fnmatchcase(sid, pattern) and len(pattern) - pattern.count("*") > score:
                    best, score = pick["id"], len(pattern) - pattern.count("*")
        if best is None:
            print(f"{sid} is left to no pick", file=sys.stderr)
            return 1
        members[best].append(sid)
    (out / "shots").mkdir(parents=True, exist_ok=True)
    for pick in picks:
        source = found[pick["id"]]
        shutil.copy2(source, out / "shots" / source.name)
        pick["file"] = f"shots/{source.name}"
        pick["members"] = sorted(members[pick["id"]])
    spec["total"] = len(found)
    (out / "digest.json").write_text(json.dumps(spec, indent=1, ensure_ascii=False))
    data = json.dumps(spec, ensure_ascii=False).replace("</", "<\\/")
    page = TEMPLATE.read_text().replace("/*DATA*/null", data)
    # The page's name is the digest's own title, which the gallery shows.
    title = html.escape(str(spec.get("title", "GUI digest")))
    (out / "index.html").write_text(page.replace("/*TITLE*/", title))
    for pick in picks:
        print(f"{len(pick['members']):3d}  {pick['id']}")
    print(f"{len(picks)} picks cover {len(found)} shots")
    return 0


def main(argv: list[str]) -> int:
    """Run ``similar`` or ``build``."""
    if argv[:1] == ["similar"] and len(argv) > 1:
        similar(argv[1:])
        return 0
    if argv[:1] == ["build"] and len(argv) > 3:
        return build(argv[1], argv[2:-1], Path(argv[-1]))
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

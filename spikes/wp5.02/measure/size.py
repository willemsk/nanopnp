"""Count each candidate's hand-written source: non-blank, non-comment lines (D3 measure 1)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CANDIDATES = {
    "nicegui": [ROOT / "ngui" / "main.py", ROOT / "ngui" / "bridge.js"],
    "react": [
        ROOT / "react" / "main.py",
        ROOT / "react" / "index.html",
        ROOT / "react" / "vite.config.ts",
        ROOT / "react" / "tsconfig.json",
        ROOT / "react" / "package.json",
        *sorted((ROOT / "react" / "src").glob("*")),
    ],
}
COMMENT = {".py": "#", ".js": "//", ".ts": "//", ".tsx": "//", ".css": None, ".html": None, ".json": None}


def count(path: Path) -> int:
    marker = COMMENT.get(path.suffix)
    lines = 0
    for raw in path.read_text().splitlines():
        text = raw.strip()
        if not text or (marker and text.startswith(marker)) or text.startswith(('"""', "/*", "*")):
            continue
        lines += 1
    return lines


def main() -> None:
    out: dict[str, dict[str, int]] = {}
    for name, files in CANDIDATES.items():
        by_language: dict[str, int] = {}
        for path in files:
            by_language[path.suffix] = by_language.get(path.suffix, 0) + count(path)
        by_language["total"] = sum(by_language.values())
        out[name] = by_language
    json.dump(out, sys.stdout, indent=1)
    print()


if __name__ == "__main__":
    main()

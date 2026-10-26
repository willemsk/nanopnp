"""Write a render manifest for /np-gui render: the mockups at 1440 and 1280, the choice panels at 960, light and dark."""

import json
import sys
from pathlib import Path

DESIGN = Path(__file__).resolve().parents[1]
SIZES = {"mockups": ((1440, 900), (1280, 800)), "choices": ((960, 640),)}


def entries(kind):
    pages = sorted(DESIGN.glob(f"{kind}/*/*.html" if kind == "mockups" else f"{kind}/*.html"))
    for p in pages:
        stem = f"{p.parent.name}-{p.stem}" if kind == "mockups" else p.stem
        for w, h in SIZES[kind]:
            for scheme in ("light", "dark"):
                yield {"id": f"{kind}-{stem}-{w}-{scheme}", "url": p.as_uri(), "viewport": [w, h], "scheme": scheme,
                       "wait_ms": 300, "expand": "[data-screen]"}


if __name__ == "__main__":
    kind, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    m = list(entries(kind))
    (out / "manifest.json").write_text(json.dumps(m, indent=1))
    print(len(m), "entries")

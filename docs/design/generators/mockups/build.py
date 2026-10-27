"""Build docs/design/mockups/: mockups A and B, one page per area, the guided route, an index each, and the stylesheet."""

import json
import re
from pathlib import Path

# isort: off
import mk  # noqa: F401, puts the choice panels on the path
import gen

# isort: on
import route
import s_analysis
import s_continuum
import s_molecular
import s_study
from mk import CTX

HERE = Path(__file__).parent
OUT = Path(__file__).resolve().parents[2] / "mockups"
(OUT / "mockups.css").write_text(
    (HERE / "head.css").read_text()
    + "\n"
    + (HERE / "body.css")
    .read_text()
    .replace(
        "/* A highlight on the part the choice is about. */\n.focus-ring { outline: 2px dashed var(--accent); outline-offset: 3px; border-radius: var(--radius); }\n",
        "",
    )
)

HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="../mockups.css">
</head>
<body>
"""

PAGES = [  # (stem, name, screens), in the order a session walks the suites
    ("00-guided-route", "The guided route", route.build_screens),
    ("01-molecular", "Molecular", lambda: s_molecular.SCREENS),
    ("02-geometry", "Continuum: geometry and region", lambda: s_continuum.GEOMETRY),
    ("03-mesh", "Continuum: mesh", lambda: s_continuum.MESH),
    ("04-physics", "Continuum: physics defaults", lambda: s_continuum.PHYSICS),
    ("06-study", "Study", s_study.screens),
    ("05-results", "Analysis", s_analysis.screens),
]

DIFFERS = {
    "a": [
        "the changed count opens B's side panel, grouped by model, since round 2 (FR6)",
        "a study opens as a form, its graph a switch away (RE1)",
        "a run in progress is followed in the queue, unfolded wherever you are (RE2 A)",
        "a comparison opens side by side, the difference a switch away (RE4)",
    ],
    "b": [
        "the changed count opens a side panel, grouped by model (FR6 B)",
        "a study opens as a graph, its form a switch away (RE1)",
        "a run in progress has its own page in the Study suite (RE2 B)",
        "a comparison opens on the difference, the two runs small beside it (RE4)",
    ],
}


def glyph(m):
    """A charged residue in the 3D view carries its sign, never colour alone (WB-20)."""
    x, y, c = m.group(1), m.group(2), m.group(3)
    sign = "−" if c == "#ef6f6c" else "+"
    return (
        f'<circle cx="{x}" cy="{y}" r="7" fill="{c}"/>'
        f'<text x="{x}" y="{int(y) + 4}" text-anchor="middle" font-size="11" font-weight="700" fill="#0d0f13" font-family="sans-serif">{sign}</text>'
    )


def build(v):
    CTX["v"] = v
    walk = [
        (stem, name, [(sid, title, fn) for sid, title, fn in screens()])
        for stem, name, screens in PAGES
    ]
    flat = [(stem, sid, title) for stem, _, sc in walk for sid, title, _ in sc]
    shots = []
    for stem, name, sc in walk:
        sections = []
        for sid, title, fn in sc:
            k = flat.index((stem, sid, title))
            prev = flat[k - 1] if k else None
            nxt = flat[k + 1] if k + 1 < len(flat) else None
            link = lambda e: (
                f"#{e[1]}" if e[0] == stem else f"{e[0]}.html#{e[1]}",
                e[2].split(" · ")[-1],
            )  # noqa: E731
            i = [s for s, _, _ in sc].index(sid) + 1
            cls = ' class="route"' if sid.startswith("r-") else ""
            from mk import mockbar

            sections.append(
                f'<section data-screen="{sid}" id="{sid}" aria-label="{title}"{cls}>\n{fn()}\n'
                f"{mockbar(v, stem + '.html', sid, title, i, len(sc), link(prev) if prev else None, link(nxt) if nxt else None)}\n</section>\n"
            )
            shots.append({"id": sid, "page": stem, "area": name, "title": title})
        text = "".join(sections)
        defs = re.sub(
            r'<circle cx="(\d+)" cy="(\d+)" r="5" fill="(#ef6f6c|#6fa8ff)"/>', glyph, gen.GRADS
        ) + (gen.MESH if "#mesh-rz" in text else "")
        html = (
            HEAD.format(title=f"Mockup {v.upper()}: {name.lower()}")
            + f'<svg width="0" height="0" style="position:absolute" aria-hidden="true" focusable="false"><defs>{defs}\n</defs></svg>\n'
            + text
            + "</body>\n</html>\n"
        )
        (OUT / v / f"{stem}.html").write_text(gen.finish(html))
    other = "b" if v == "a" else "a"
    cards = "".join(
        f'<section class="ixs"><h2>{name}</h2><ul class="ixl">'
        + "".join(
            f'<li><a href="{stem}.html#{sid}">{title.split(" · ", 1)[-1]}</a></li>'
            for sid, title, _ in sc
        )
        + "</ul></section>"
        for stem, name, sc in walk
    )
    differs = "".join(f"<li>{d}</li>" for d in DIFFERS[v])
    (OUT / v / "index.html").write_text(
        gen.finish(
            HEAD.format(title=f"Workbench mockup {v.upper()}")
            + f"""<style>
  body {{ overflow: auto; }}
  .ix {{ max-width: 980px; margin: 0 auto; padding: 16px; display: grid; gap: 14px; }}
  .ix h1 {{ font-size: var(--text-2xl); margin: 0; }}
  .ixs {{ background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius); padding: 10px 14px; }}
  .ixs h2 {{ font-size: var(--text-lg); margin: 0 0 6px; }}
  .ixl {{ margin: 0; padding-left: 18px; columns: 2; }}
  .ixl a {{ display: inline-flex; align-items: center; min-height: var(--target-min); }}
</style>
<main class="ix">
  <h1>Workbench mockup {v.upper()}</h1>
  <p>One working session on the ClyA pore, 2WCD, through the four suites: Molecular, Continuum, Study and Analysis,
  with the project rail, the run queue and the changed count always on screen. It is built from the picks on the
  choice panels; where a pick was "either", this mockup differs from <a href="../{other}/index.html">mockup {other.upper()}</a>:</p>
  <ul>{differs}</ul>
  <p>Numbers are placeholders (x.xx): no artefact supplies them. The (r, z) views are not to scale. Parts of a later
  tool phase carry a <span class="later" style="display:inline;padding:0 4px"><b>banner</b></span> and no working control.
  The bar under each screen moves through the session and to the same screen in the other mockup.</p>
  {ROUND[v]}
  {cards}
</main>
</body>
</html>
"""
        )
    )
    return shots


ROUND = {
    "a": """<p><b>Round 2.</b> The author chose this mockup; it is revised after the verdicts on its screens
  (<code>docs/design/reviews/2026-10-26-mockups.md</code>): Prepare and Protonation dock their settings beside the view,
  the physics defaults' settings sit on the left, the overview lists the physics, the sweep ranges over any value with
  the rebuilds it needs, the charge on the mesh says what it is for, and the changed count opens B's side panel.</p>""",
    "b": "",
}

# Mockup B stays as the author marked it in round 1; only the chosen mockup is rebuilt.
manifest = {v: build(v) for v in ("a",)}
json.dump(manifest, open(HERE / "mockups.json", "w"), ensure_ascii=False, indent=1)
print({v: len(s) for v, s in manifest.items()}, "screens")

"""Build docs/design/choices/: the pages and the index."""

import json
from pathlib import Path

import p00_frame
import p01_molecular
import p02_continuum
import p05_results
from gen import HEAD, OUT, page

PAGES = [
    ("00-frame", "The frame", p00_frame.CHOICES),
    ("01-molecular", "Molecular", p01_molecular.CHOICES),
    ("02-geometry", "Geometry and region", p02_continuum.GEOMETRY),
    ("03-mesh", "Mesh", p02_continuum.MESH),
    ("04-physics", "Physics", p02_continuum.PHYSICS),
    ("05-results", "Studies and results", p05_results.RESULTS),
    ("06-guided-route", "The guided route", p05_results.ROUTE),
]

index = []
for i, (stem, name, choices) in enumerate(PAGES):
    nxt = (f"{PAGES[i + 1][0]}.html", PAGES[i + 1][1]) if i + 1 < len(PAGES) else None
    prev = (f"{PAGES[i - 1][0]}.html#{PAGES[i - 1][2][-1][0].lower()}-b", PAGES[i - 1][1]) if i else None
    index.append((stem, name, page(stem, f"Choices: {name.lower()}", choices, nxt=nxt, prev=prev)))

cards = []
for stem, name, choices in index:
    rows = "".join(
        f'<li><span class="cid">{cid}</span> {q}<div class="row" style="margin:2px 0 6px 2.6rem">'
        f'<a class="chip" href="{stem}.html#{cid.lower()}-a">A · {t["a"]}</a>'
        f'<a class="chip" href="{stem}.html#{cid.lower()}-b">B · {t["b"]}</a></div></li>'
        for cid, q, t in choices)
    cards.append(f'<section class="ixs"><h2>{name}</h2><ul class="ixl">{rows}</ul></section>')

n = sum(len(c) for _, _, c in index)
(OUT / "index.html").write_text(HEAD.format(title="Workbench choice panels") + f"""<style>
  .ix {{ max-width: 980px; margin: 0 auto; padding: 16px; display: grid; gap: 14px; }}
  .ix h1 {{ font-size: var(--text-2xl); margin: 0; }}
  .ixs {{ background: var(--panel); border: 1px solid var(--line); border-radius: var(--radius); padding: 10px 14px; }}
  .ixs h2 {{ font-size: var(--text-lg); margin: 0 0 6px; }}
  .ixl {{ list-style: none; margin: 0; padding: 0; }}
  .ixl .cid {{ display: inline-block; width: 2.4rem; font: 600 var(--text-sm) var(--font-num); color: var(--muted); }}
  .ixl .chip {{ text-decoration: none; }}
</style>
<main class="ix">
  <h1>Workbench choice panels</h1>
  <p>{n} open choices of the workbench, each drawn twice, A and B, on the same placeholder data (x.xx: no artefact supplies
  the numbers). What the design round ruled (WB-01 to WB-28 in the design document) is not offered again: the suites,
  the project browser and the run queue always on screen, the library of models paired in studies, the changed-from-default diamond, the tokens.
  Pick A, B, either or neither for each, with a note if you like; the picks are assembled into two whole workbenches to
  choose between. A dashed outline marks the part each choice is about; the rest of the screen is context. Parts of a
  later tool phase carry a <span class="later" style="display:inline;padding:0 4px"><b>banner</b></span> and no working control.</p>
  {"".join(cards)}
</main>
</body>
</html>
""")

json.dump([{"id": f"{cid.lower()}", "page": stem, "area": name, "question": q, "takes": t}
           for stem, name, choices in index for cid, q, t in choices],
          open(Path(__file__).parent / "choices.json", "w"), ensure_ascii=False, indent=1)
print(n, "choices")

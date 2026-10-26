"""Build the mockup verdict gallery: index.html, shots/, mockups/, tokens.css."""

import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).parent
RENDER = Path(sys.argv[1])
REPO = Path(__file__).resolve().parents[3]
SCREENS = json.loads((HERE.parent.parent / "mockups" / "mockups.json").read_text())
findings = json.loads((HERE / "findings.json").read_text()) if (HERE / "findings.json").exists() else {}
TAKES = {
    "st-changes": ("The changed count opens a pop-over list", "The changed count opens a side panel, grouped by model"),
    "st-form": ("The study opens as a form; the graph is a switch away", "The form, reached from the graph by its switch"),
    "st-graph": ("The graph, reached from the form by its switch", "The study opens as a graph; the form is a switch away"),
    "st-runs": ("A run followed in the queue, unfolded wherever you are", "A run followed on its own page in the Study suite"),
    "a-compare-side": ("The comparison opens side by side", "Side by side, reached from the difference by its switch"),
    "a-compare-diff": ("The difference, reached by the switch", "The comparison opens on the difference"),
}

for d in ("shots", "mockups"):
    shutil.rmtree(HERE / d, ignore_errors=True)
    (HERE / d).mkdir()
for v in ("a", "b"):
    (HERE / "mockups" / v).mkdir()
    for f in REPO.joinpath("mockups", v).glob("*.html"):
        shutil.copy(f, HERE / "mockups" / v / f.name)
shutil.copy(REPO / "mockups" / "mockups.css", HERE / "mockups" / "mockups.css")
shutil.copy(REPO / "tokens.css", HERE / "tokens.css")

out = []
for s in SCREENS["a"]:
    sid, page = s["id"], s["page"]
    pics = {sc: {} for sc in ("light", "dark")}
    for sc in ("light", "dark"):
        for v in ("a", "b"):
            name = f"mockups-{v}-{page}-1440-{sc}-{sid}.png"
            shutil.copy(RENDER / name, HERE / "shots" / name)
            pics[sc][v] = f"shots/{name}"
    differs = sid in TAKES
    takes = dict(zip("ab", TAKES[sid])) if differs else {"a": "The same in both mockups", "b": "The same in both mockups"}
    out.append({"id": sid, "area": s["area"], "question": s["title"], "takes": takes, "differs": differs,
                "pages": {v: f"mockups/{v}/{page}.html#{sid}" for v in "ab"}, "pictures": pics, "findings": findings.get(sid, [])})

overall = ("Mockup A: the changed list as a pop-over, a study opening as a form, a run followed in the queue, a comparison "
           "opening side by side. Mockup B: the changed list as a side panel, a study opening as a graph, a run on its own page, "
           "a comparison opening on the difference. Everything else is the same.")
data = json.dumps({"round": 1, "choices": out, "general": findings.get("_general", []), "overallText": overall}, ensure_ascii=False)
t = (HERE / "template.html").read_text()
(HERE / "index.html").write_text(t.replace("/*DATA*/null", data.replace("</", "<\\/")))
files = {f"shots/{p.name}": str(p) for p in sorted((HERE / "shots").glob("*.png"))}
files |= {f"mockups/{v}/{p.name}": str(p) for v in "ab" for p in sorted((HERE / "mockups" / v).glob("*.html"))}
files["mockups/mockups.css"] = str(HERE / "mockups" / "mockups.css")
files["tokens.css"] = str(HERE / "tokens.css")
(HERE / "files.json").write_text(json.dumps(files, indent=1))
print(len(out), "cards,", len(files), "files")

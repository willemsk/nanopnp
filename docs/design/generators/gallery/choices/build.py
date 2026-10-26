"""Build the choice-panel verdict gallery: index.html, shots/, choices/, tokens.css."""

import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).parent
RENDER = Path(sys.argv[1])
REPO = Path(__file__).resolve().parents[3]
CHOICES = json.loads((HERE.parent.parent / "choices" / "choices.json").read_text())
findings = json.loads((HERE / "findings.json").read_text()) if (HERE / "findings.json").exists() else {}

for d in ("shots", "choices"):
    shutil.rmtree(HERE / d, ignore_errors=True)
    (HERE / d).mkdir()
for f in REPO.joinpath("choices").glob("*"):
    shutil.copy(f, HERE / "choices" / f.name)
shutil.copy(REPO / "tokens.css", HERE / "tokens.css")

out = []
for c in CHOICES:
    pics = {}
    for sc in ("light", "dark"):
        pics[sc] = {}
        for v in ("a", "b"):
            name = f"choices-{c['page']}-960-{sc}-{c['id']}-{v}.png"
            shutil.copy(RENDER / name, HERE / "shots" / name)
            pics[sc][v] = f"shots/{name}"
    out.append({"id": c["id"], "area": c["area"], "question": c["question"], "takes": c["takes"],
                "page": f"choices/{c['page']}.html", "pictures": pics, "findings": findings.get(c["id"], [])})

data = json.dumps({"round": 1, "choices": out, "general": findings.get("_general", [])}, ensure_ascii=False)
t = (HERE / "template.html").read_text()
(HERE / "index.html").write_text(t.replace("/*DATA*/null", data.replace("</", "<\\/")))
files = {f"shots/{p.name}": str(p) for p in sorted((HERE / "shots").glob("*.png"))}
files |= {f"choices/{p.name}": str(p) for p in sorted((HERE / "choices").glob("*"))}
files["tokens.css"] = str(HERE / "tokens.css")
(HERE / "files.json").write_text(json.dumps(files, indent=1))
print(len(out), "cards,", len(files), "files")

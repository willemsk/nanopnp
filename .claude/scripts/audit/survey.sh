#!/usr/bin/env bash
# Survey of packages that track or assess code quality and architecture (audit brief, Appendix E).
# Reads: src/nanopnp and the project environment. Writes: one file per candidate under the
# directory given as $1 (default docs/code_reviews/CODE_REVIEW_039/raw/survey), each holding the
# command run, its exit status and the head of its output; and pypi.json, the registry metadata
# (licence, home page, latest version and its upload date, number of releases) per candidate.
# Each tool runs from an ephemeral environment (`uvx` or `uv run --with`), so nothing is added to
# the project's lock, and nothing under src/ changes. A tool that needs a configuration file gets
# one in the scratch directory $2 (default /tmp/nanopnp-survey), never in the tree.
set -u
OUT=${1:-docs/code_reviews/CODE_REVIEW_039/raw/survey}
SCRATCH=${2:-/tmp/nanopnp-survey}
mkdir -p "$OUT" "$SCRATCH"
ROOT=$(git rev-parse --show-toplevel)
cd "$ROOT"

run() { # name, then the command
  local name=$1; shift
  { echo "\$ $*"; echo; timeout 600 "$@" 2>&1 | head -c 20000; echo; echo "[exit ${PIPESTATUS[0]}]"; } > "$OUT/$name.txt"
  echo "$name: $(tail -1 "$OUT/$name.txt")"
}

# import-linter: a layers contract in the order docs/project/modularity.md reads the subpackages
cat > "$SCRATCH/importlinter.ini" <<'INI'
[importlinter]
root_package = nanopnp
[importlinter:contract:1]
name = Layers in the order of docs/project/modularity.md
type = layers
layers =
    nanopnp.gui
    nanopnp.cli
    nanopnp.api
    nanopnp.sweep
    nanopnp.pipeline
    nanopnp.post
    nanopnp.solve
    nanopnp.physics
    nanopnp.materials
    nanopnp.charge
    nanopnp.mesh
    nanopnp.geometry
    nanopnp.symmetry
    nanopnp.density
    nanopnp.structure
    nanopnp.io
    nanopnp.core
INI
run import-linter uv run --with import-linter lint-imports --config "$SCRATCH/importlinter.ini" --no-cache
run grimp uv run --with grimp python -c "
import grimp
g = grimp.build_graph('nanopnp', include_external_packages=False)
print('modules', len(g.modules))
print('imports', g.count_imports())
chains = g.find_shortest_chains('nanopnp.physics', 'nanopnp.mesh')
print('shortest chains physics->mesh', len(chains)); print(sorted(chains)[:5])
print('downstream of nanopnp.physics', len(g.find_downstream_modules('nanopnp.physics', as_package=True)))
"
# tach: configuration written in scratch over a symlink to src, so the tree stays untouched
rm -rf "$SCRATCH/tach"; mkdir -p "$SCRATCH/tach"; ln -s "$ROOT/src" "$SCRATCH/tach/src"
cat > "$SCRATCH/tach/tach.toml" <<'TOML'
source_roots = ["src"]
exclude = []
[[modules]]
path = "nanopnp.physics"
depends_on = []
[[modules]]
path = "nanopnp.mesh"
depends_on = []
[[modules]]
path = "nanopnp.io"
depends_on = []
[[modules]]
path = "nanopnp.core"
depends_on = []
TOML
run tach bash -c "cd '$SCRATCH/tach' && uvx tach sync && cat tach.toml | head -60 && uvx tach check; uvx tach report nanopnp.physics | head -40"
run pydeps uvx pydeps src/nanopnp --no-output --show-deps --only nanopnp --max-bacon 1
run deptry uvx deptry src
run radon uvx radon cc src/nanopnp -s -a --total-average -nC
run radon-mi uvx radon mi src/nanopnp -s -n B
run xenon uvx xenon src/nanopnp --max-absolute C --max-modules B --max-average A
run wily bash -c "uvx wily --cache '$SCRATCH/wily' --path '$ROOT' build src/nanopnp -n 3 && uvx wily --cache '$SCRATCH/wily' --path '$ROOT' rank src/nanopnp maintainability.mi --limit 10"
run lizard uvx lizard src/nanopnp -l python -w -C 15
run lizard-summary uvx lizard src/nanopnp -l python -s cyclomatic_complexity -T nloc=200
run interrogate uvx interrogate -v src/nanopnp
run vulture uvx vulture src/nanopnp --min-confidence 80
run pylint-design uv run --with pylint pylint src/nanopnp --disable=all --enable=design --reports=y --score=n --max-line-length=100
run ruff-families uv run ruff check src --select C90,PL,PERF,FBT,A,ARG,PTH,ERA,T20,TRY,FURB,S --statistics --no-fix
run mypy-reports uv run --with lxml mypy src/ --linecount-report "$SCRATCH/mypy" --html-report "$SCRATCH/mypy-html"
{ echo "linecount.txt head"; head -20 "$SCRATCH/mypy/linecount.txt" 2>/dev/null; echo; echo "html index exists: $(test -f "$SCRATCH/mypy-html/index.html" && echo yes || echo no)"; } >> "$OUT/mypy-reports.txt"
run pyreverse bash -c "uv run --with pylint pyreverse -o dot -p nanopnp -d '$SCRATCH/pyreverse' src/nanopnp && ls -la '$SCRATCH/pyreverse' && grep -c -- '->' '$SCRATCH/pyreverse/packages_nanopnp.dot'"
run code2flow uvx code2flow src/nanopnp/solve --output "$SCRATCH/code2flow.json" --language py
run pyan3 bash -c "uvx pyan3 src/nanopnp/solve/*.py --uses --no-defines --dot | head -40"
echo "sourcery: not run (proprietary; needs an account token)" > "$OUT/sourcery.txt"

# Registry metadata
python3 - "$OUT/pypi.json" <<'PY'
import json, sys, urllib.request
out = {}
for pkg in ["import-linter","grimp","tach","pydeps","deptry","radon","xenon","wily","lizard","interrogate","vulture","pylint","ruff","mypy","code2flow","pyan3","sourcery"]:
    try:
        with urllib.request.urlopen(f"https://pypi.org/pypi/{pkg}/json", timeout=30) as r:
            d = json.load(r)
        info = d["info"]; rel = d["releases"]
        latest = info["version"]
        uploads = [f["upload_time"] for f in rel.get(latest, [])]
        first = min((f["upload_time"] for files in rel.values() for f in files), default="")
        out[pkg] = {"license": (info.get("license") or "")[:80], "license_expression": info.get("license_expression"),
                    "classifiers_license": [c for c in info.get("classifiers", []) if c.startswith("License")],
                    "home": info.get("home_page") or (info.get("project_urls") or {}).get("Homepage") or (info.get("project_urls") or {}).get("Source"),
                    "project_urls": info.get("project_urls"), "author": info.get("author") or info.get("author_email"),
                    "latest": latest, "latest_upload": max(uploads) if uploads else None, "releases": len(rel), "first_release": first,
                    "requires_python": info.get("requires_python")}
    except Exception as e:  # noqa: BLE001
        out[pkg] = {"error": str(e)}
json.dump(out, open(sys.argv[1], "w"), indent=1, sort_keys=True)
print("pypi.json written")
PY
echo "survey done"

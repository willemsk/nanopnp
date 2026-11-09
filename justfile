# The commands people and agents run, in one place (CLAUDE.md, Commands). `uv sync` installs just
# with the dev tools; `uv run just` lists the recipes and `uv run just <recipe>` runs one.
#
# No recipe commits or pushes: the gate hook judges the command as typed, so `git commit` and
# `git push` stay commands of their own.

set shell := ["bash", "-euo", "pipefail", "-c"]
set positional-arguments

# List the recipes
default:
    @{{just_executable()}} --list --unsorted

# Refresh .venv from uv.lock as it is, as the session hook does
sync:
    uv sync --all-extras --frozen

# The default test selection: Tiers 1 and 2 without the nightly walks and the slow tests
test *args:
    uv run pytest "$@"

# The default selection in parallel, then the widget tests that run serially
test-parallel:
    OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
        uv run pytest -n auto --dist loadfile --ignore=tests/tier1/test_gui_widgets.py
    uv run pytest tests/tier1/test_gui_widgets.py

# Lint, format check and strict types, as the gate runs them
lint:
    uv run ruff check .
    uv run ruff format --check .
    uv run mypy src/

# Apply ruff's fixes and format
fix:
    uv run ruff check --fix .
    uv run ruff format .

# The documentation build with CI's checks: the docs tools, the decisions page, links, strict build
docs:
    uv sync --all-extras --group docs --frozen
    uv run .claude/scripts/decisions.py --check
    uv run docs/scripts/generate.py
    uv run .claude/scripts/links.py
    uv run mkdocs build --strict

# Rewrite the decisions page and the indexes of the plans and reviews
records:
    uv run .claude/scripts/decisions.py
    uv run .claude/scripts/index_records.py

# Check the records: the decisions page, numbers two items share, relative links
check-records:
    uv run .claude/scripts/decisions.py --check
    uv run .claude/scripts/duplicates.py
    uv run .claude/scripts/links.py

# Print a clause of the specification with its NOTEs and rulings
clause id:
    uv run .claude/scripts/clause.py "$1"

# The push gate into a log that ends in "exit <status>"; an agent starts it in the background
gate log=(env("TMPDIR", "/tmp") / "nanopnp-gate.log"):
    status=0; .claude/hooks/gate.sh run > "$1" 2>&1 || status=$?; echo "exit $status" >> "$1"; exit $status

# The commit gate by hand, to reproduce a refusal or on a host where the hook does not fire
commit-gate:
    echo '{"tool_input":{"command":"git commit"}}' | .claude/hooks/gate.sh

# The resolved environment and data locations
env:
    uv run nanopnp --env

# Gmsh's system libraries, which the push gate needs (Debian or Ubuntu, as root)
gmsh-libs:
    apt-get install -y --no-install-recommends libglu1-mesa libxft2 libxinerama1 libxcursor1

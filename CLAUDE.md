# Project: nanopnp

Open-source Python reimplementation of the **ePNP-NS** framework for biological nanopores
(Willems et al., *Nanoscale* **12**, 16775–16795, 2020). It replaces a COMSOL workflow.
2D-axisymmetric steady state; structure → mesh → solve → analyse. Python 3.11–3.14, developed on 3.14.

## Before doing anything

- **Read `knowledge/index.md`.** It is the verified knowledge base.
- **`SPECIFICATION.md` is normative** (`FR-`, `QR-`, `CON-`, `PHY-`, `NUM-`, `VER-`, `VAL-`). It is the
  entry point and the map. The text is in `specification/`. Dated rulings are in
  `specification/history/`; read them on demand. `uv run .claude/scripts/clause.py <ID>` prints a
  clause. Cite the identifier when you implement or test one. A change to specified behaviour changes
  the specification in the same commit.
- **Never web-search the model equations, correction functions or parameters.** Popular summaries are
  wrong. The concepts under `knowledge/01-physics-epnpns/` are normative. Where sources disagree, the
  COMSOL model report governs (§1.6). Web search is fine for library versions and APIs (prefer
  Context7) and for literature newer than the knowledge base.
- **Rules by path.** `.claude/rules/physics-numerics.md` and `.claude/rules/python.md` load when you
  read or edit a file they cover. A session that writes only Markdown reads them explicitly.

## Setup

`uv` owns the environment. Use no `pip`, no manual `activate`, no bare `python` or `pytest`.

- `uv sync --all-extras` creates or refreshes `.venv` from `uv.lock`.
- A stale `.venv` in a session takes `uv sync --all-extras --frozen`, as the session hook runs it.
  `--frozen` installs `uv.lock` as it is and does not fail on a stale lock. `UV_LOCKED=1`, which the
  gate and CI set, and `uv lock --check` fail on one.
- `uv add [--group dev] <pkg>` adds a dependency.
- `uv run <anything>` is the only way to run code.
- After you edit `pyproject.toml` by hand, run `uv lock`. CI fails on a stale lock.

## Commands

| Command | Purpose |
|---|---|
| `uv run pytest` | Tiers 1–2 without `nightly` and `slow` tests: the default selection |
| `uv run pytest --nightly` | Adds the `nightly` walks. `-m "(tier1 or tier2) and slow"` adds the `slow` tests, as the nightly run does. Naming a `nightly` test's file runs it without the flag |
| `uv run pytest -n auto --dist loadfile` | Parallel. Set `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS` and `MKL_NUM_THREADS` to 1. `tests/tier1/test_gui_widgets.py` runs serially, apart |
| `uv run pytest -m tier1` / `-m tier3` / `-m slow` | Unit tests / reference comparison / benchmarks (the last two are not gated) |
| `uv run ruff check . && uv run ruff format .`; `uv run mypy src/` | Lint and format; strict types |
| `uv run nanopnp --env` | The resolved environment and data locations |
| `uv sync --all-extras --group docs && uv run docs/scripts/generate.py && uv run mkdocs build --strict` | The documentation build, as CI's `docs` job (VER-45) |

**The gate before a commit** is the commit hook. `gate.sh` runs before each `git commit` that Claude
Code makes (`--no-verify` skips it). It runs the lock check, lint, format, types and the Tier 1 tests
without `slow` and without `nightly`. Do not run these checks by hand before a commit: a manual run
writes no stamp, so the hook runs them all again. Run the hook itself by hand only to reproduce a
refusal, or on a host where it does not fire (`.claude/workflow/hosts.md`):
`echo '{"tool_input":{"command":"git commit"}}' | .claude/hooks/gate.sh`.

**The gate before a push:** `.claude/hooks/gate.sh run`. It runs lint, format and types, then the
per-push selection:

- Tier 1;
- the Tier 2 tests that neither walk the pipeline nor carry `slow`;
- example 01, while it solves in under 60 s;
- example 02's charged ePNP-NS walk.

No coverage is measured. A commit-hook pass never stands in for `run`.

1. Start `run` with Bash `run_in_background`: `.claude/hooks/gate.sh run > <log> 2>&1; echo "exit $?" >> <log>`.
2. Wait for it in the same turn: `until grep -q '^exit ' <log>; do sleep 10; done` in the foreground.
   If the 10-minute limit ends the wait, wait again.
3. Push when the log ends in `exit 0`. The hook refuses a push of a tree it has not passed. End the
   turn only then. A turn that ends on an unpushed commit trips the environment's stop hook.

`run` sets `NANOPNP_REQUIRE_GMSH=1`, `NANOPNP_REQUIRE_BROWSER=1`, and `NANOPNP_REQUIRE_APBS=1` where
the wheel exists. `tests/tier1/test_gui_screens.py` launches Chromium: the one `NANOPNP_CHROMIUM`
names, which `run` sets to one under `/opt/pw-browsers/` where it finds one, or else Playwright's own.
A backend or browser that cannot start then fails; it does not skip.

When only Markdown outside `packaging/`, `src/`, `data/` and `examples/` changed, the hook runs ruff
alone (`.github/scripts/prose-only.sh`). CI's documentation build still runs.

## Project structure

`src/nanopnp/` has one subpackage per module of SPECIFICATION.md §5.1:

- `core/` units, constants, provenance, caching; `structure/` PDB/mmCIF and trajectory IO;
  `density/` smearing, ensemble averaging; `symmetry/` Cₙ averaging and reduction to (r, z)
- `geometry/` contours, CAD assembly, analyte bodies; `mesh/` mesher adapters (netgen, gmsh), size
  fields, quality gates; `numerics/` linear solvers, damped Newton, gates, the axisymmetric measure
- `charge/` PDB2PQR, partial charges, projection, dielectric; `materials/` electrolytes and the
  correction registry; `physics/` weak forms and the wall-distance field; `solve/` continuation
  ladder, warm start; `post/` QoI (current, transport number, EOF, forces); `plot/` figures of the
  artefacts (Matplotlib, the `plot` extra); `sweep/` sweeps
- `io/` case schema, artefact and resolved-case types, result store, manifests. It is the base layer
  and imports only `core` at run time. `pipeline/` case resolution, the walk, the assembler; `api/`
  the Python interface (`Case`, `Session`, sweeps, reproduction), above `sweep/`; `cli/` and
  `gui/` are thin shells that hold no physics; `validation/` benchmarks, MMS, COMSOL comparison

Outside it: `data/corrections/*.yaml` (fitted parameters, shipped in the wheel), `specification/`,
`knowledge/`, `tests/tier{1,2,3,4}/`, `docs/`, and `docs/plans/` (planning, not requirements;
`SPECIFICATION.md` wins).

A stage takes typed inputs and emits a typed, serialisable artefact that carries a content hash.
Every stage stays independently invocable, cancellable and introspectable (FR-27).

## Testing

Tests live in `tests/tier{1,2,3,4}/` (§7.1). The directory's `conftest.py` sets the marker, so the
location decides the tier.

| Tier | Content | Runtime | When |
|---|---|---|---|
| 1 | Unit and property tests (VER-01 … VER-11) | seconds | every push |
| 2 | Analytic benchmarks (VER-12 … VER-22) | minutes | every push |
| 3 | Cross-implementation comparison (VAL-01 … VAL-06, VAL-16, VAL-17) | hours | nightly, recorded not gated |
| 4 | Experimental reproduction (VAL-07 … VAL-14) | hours | before a tagged release |

- **The test scope** is `SPECIFICATION.md` §7.1 and §8.2.13 N1. Write a test only for physics and
  numerics, core mechanisms, and the licence and architecture guards (CON-10, CON-12, VER-61,
  VER-65, no backend import). Each entry point keeps a thin smoke test. Test a refusal only where
  it is a numerical or physical gate.
- A new test's name or first line says which silent failure it catches, for example
  `test_ver03_ion_wall_function_check_values`.
- Name a requirement identifier in a test only where the requirement is physics, numerics or a core
  mechanism. Other identifiers are verified at review (§7.1; N3).
- `/np-ship` deletes off-scope tests (its §4). No tolerance is slackened and no kept test is weakened.
- Fix Tier 2 before you chase a Tier 3 discrepancy.
- Tests use no network and no COMSOL licence. Tier 3 reads archived reference data.

## Provenance and reproducibility

The case file (`schema: nanopnp/case/v0.6`) is the unit of reproducibility. Every artefact carries a
content hash over its payload and producing parameters. The hash is its cache key. Every result
carries a manifest (FR-25, §5.3.3). The manifest holds the input hashes, library versions, mesh
hash, solver settings, stabilisation mode, correction file versions and **every switch set away from
the validated default**. A result whose manifest cannot reconstruct the run is not a result.

## Implementation workflow

One work package per PR, green on tiers 1–2 before the next one in its lane (at most two lanes,
§8.4.4). To plan or resume, read `docs/plans/current.md`, then the WP's Execution brief and the
sections it cites. A brief never overrides a normative requirement.

| Step | Command | What it does |
|---|---|---|
| 0 | `/np-plan project`, `/np-plan phase <n>`, `/np-plan amend <n>` | Puts the decisions to the author; writes the rulings into `specification/history/` and the plan; pushes; opens its PR; pauses for `/compact` |
| 1 | `/np-plan wp <n>` | Writes and commits the WP plan; pushes; opens the package's PR; pauses for `/compact` |
| 0–1 | `/np-plan <level> [n] review` | Reviews the plan (`/code-review medium --fix`); fixes it; gates; pushes; gives the summary for approval |
| 2 | `/np-implement [wp <n>]` | Executes the plan; gates; pushes; opens or reuses the PR; pauses for `/compact` |
| 3–4 | `/np-ship [wp <n>]` | Gates; pushes; reviews (`/code-review xhigh --fix`); drives CI to green; prints the tag commands |
| close | `/np-ship phase <n>` | Ships the close package and tags the release |

Step 2 pauses for `/compact`; `/np-ship` then runs in that session or a fresh one, and puts to the
author each finding against a decision the implementing session took (`.claude/workflow/core.md`,
*Report and stop*). A cloud session cannot push a tag; after the merge `/np-ship` dispatches `tag.yml` and prints the
commands. A choice put to the author follows the core's *Putting a choice to the author*. The steward skill governs a PR in flight. `/np-gui <render | review | publish | collect | grill>`
renders screens and mockups headless, reviews them, publishes them for the author's verdicts, and runs
a design round (§8.4.4).

**Models:** implementation runs on Haiku for an easy mechanical item and on Sonnet by default. It
moves to Opus only after Sonnet fails on the item. The kept helpers are the `physics-reviewer`,
`gui-reviewer` and `ci-log-classifier` sub-agents and three scripts in `.claude/scripts/`:
`clause.py` prints a clause, `duplicates.py` names a number that two items of one register share,
and `same_tree.py` checks that changed Python files differ only in prose (§8.2.11 L5). The
caps on a WP plan, and its executors, are in `.claude/skills/np-plan/wp.md` (§8.4.4; §8.2.15 Q1;
§8.2.16 R11).

**Code review reports** go to `docs/code_reviews/CODE_REVIEW_NNN.md`, with NNN one above the highest
present. The skill that runs the review gives that path in the brief after `--`.

**Open items** are a finding not fixed, a deferral, or a question for the author. Each is a `REV-nn`
row in `docs/project/review-findings.md` with a section in `review-items.md`. It stays until the
commit that resolves it sets it `fixed` (§8.4.6; §8.2.8 H12). A PR body is never its only record.

## Other hosts

The workflow also runs on the GitHub Copilot app, as a WSL host (§8.4.4; §8.2.25). `.claude/` stays
the single source. Another host reads its map through `.claude/workflow/hosts.md`. One host drives a
branch at a time.

## Git

- Use conventional commits (`feat:`, `fix:`, `test:`, `docs:`, `chore:`). Name the identifier in the
  body (`VER-03`).
- A version is a git tag, never a number in `pyproject.toml` or the package (§2.7). The procedure is
  in `CONTRIBUTING.md`, *Versions and releases*.

## Prose in code

- A public function, class or method of `src/` has a docstring. Public means no leading underscore; a
  dunder method is public. The docstring has a summary line, and NumPy-style parameters only where
  name and type do not say. It has no derivation and no history.
- Every module has a one-line docstring. A test or private code has none.
- A comment says why the code is so, where the code cannot say it, or gives the source of a physical
  constant.
- Identifiers live in test names and commit messages (`.claude/rules/python.md`; §8.4.2; §8.2.11 L4).

## Durable learnings

Write a durable fact as a concept in the relevant `knowledge/` directory, or into an existing one,
with its source:

- Mark a claim `[tested: <test>]`, naming a test in scope, or `[verified]`, with a source footnote.
- List the concept in the directory's `index.md`.
- Add a line to `knowledge/log.md`.

The procedure is `knowledge/00-orientation/04-provenance-and-how-to-extend-this.md`. Status and
scope opinions belong in the specification.

## Do NOT

- Use `pip`, a hand-activated venv, or bare `python` or `pytest`.
- Import `gmsh` on the default path. It is GPLv2+ and an optional backend only (CON-10, ADR-002).
- Depend on Triangle, MeshPy or TetGen (CON-12).
- Use PyQt. Use PySide6 only (CON-09).
- Add anything to the end-user path that needs a C++ compiler, a source build or a JIT (CON-07).
- Write the weak forms twice, or put backend-specific constructs in `physics/` (QR-13).
- Hard-code correction coefficients, `ε_protein` or any fitted parameter in Python.
- Add COMSOL import or export (N7), transient solves (N3), 3D (N4) or off-axis analytes (N5). The
  architecture must not preclude them.

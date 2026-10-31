# Project: nanopnp

Open-source Python reimplementation of the **ePNP-NS** framework for biological nanopores
(Willems et al., *Nanoscale* **12**, 16775–16795, 2020), replacing a COMSOL workflow.
2D-axisymmetric steady state; structure → mesh → solve → analyse. Python 3.11–3.14, developed on 3.14.

## Before doing anything

- **Read `knowledge/index.md`**: the verified knowledge base.
- **`SPECIFICATION.md` is normative** (`FR-`, `QR-`, `CON-`, `PHY-`, `NUM-`, `VER-`, `VAL-`): it is
  the entry point and map; the text is in `specification/`, its dated rulings in
  `specification/history/`, read on demand; `uv run .claude/scripts/clause.py <ID>` prints a clause. Cite the
  identifier when you implement or test one. Changing specified behaviour means changing the
  specification in the same commit.
- **Never web-search the model equations, correction functions or parameters.** Popular summaries are
  wrong. The concepts under `knowledge/01-physics-epnpns/` are normative; where sources disagree, the COMSOL model
  report governs (§1.6). Web search is fine for library versions/APIs (prefer Context7) and
  post-knowledge-base literature.
- **Rules by path:** `.claude/rules/physics-numerics.md` and `.claude/rules/python.md` load when you
  read or edit a file they cover; a session writing only Markdown plans reads them explicitly.

## Setup

`uv` owns the environment: no `pip`, no manual `activate`, no bare `python`/`pytest`.

- `uv sync --all-extras` creates or refreshes `.venv` from `uv.lock`; `uv add [--group dev] <pkg>`
  adds a dependency; `uv run <anything>` is the only way code is executed.
- After hand-editing `pyproject.toml`, run `uv lock`; CI fails on a stale lock.

## Commands

| Command | Purpose |
|---|---|
| `uv run pytest` | Tiers 1–2 without `nightly` and `slow` tests: the default selection |
| `uv run pytest --nightly` | Adds the `nightly` walks; `-m "(tier1 or tier2) and slow"` adds the `slow` tests, as the nightly run does. Naming a `nightly` test's file runs it without the flag |
| `uv run pytest -n auto --dist loadfile` | Parallel; set `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS` to 1. `tests/tier1/test_gui_widgets.py` runs serially, apart |
| `uv run pytest -m tier1` / `-m tier3` / `-m slow` | Unit tests / reference comparison / benchmarks (the last two not gated) |
| `uv run ruff check . && uv run ruff format .`; `uv run mypy src/` | Lint and format; strict types |
| `uv run nanopnp --env` | Resolved environment and data locations |
| `uv sync --all-extras --group docs && uv run docs/scripts/generate.py && uv run mkdocs build --strict` | Documentation build, as CI's `docs` job (VER-45) |

Gate before committing: `uv run ruff check . && uv run ruff format --check . && uv run mypy src/ && uv run pytest -m tier1`.
Gate before pushing: `.claude/hooks/gate.sh run` (lint, format and types, then the per-push selection: Tier 1, the
Tier 2 tests that neither walk the pipeline nor carry `slow`, example 01 while it solves in under 60 s, and example
02's charged ePNP-NS walk). No coverage is measured. `gate.sh` also runs before each `git commit` that Claude Code
makes (`--no-verify` skips it): the lock check, lint, format, types and the Tier 1 tests without the `nightly`
marker. A hook pass never stands in for `run`.

1. Start `run` with Bash `run_in_background`: `.claude/hooks/gate.sh run > <log> 2>&1; echo "exit $?" >> <log>`.
2. Wait for it in the same turn: `until grep -q '^exit ' <log>; do sleep 10; done` in the foreground. If the
   10-minute limit ends the wait, run it again.
3. Push when the log ends in `exit 0`; the hook refuses a push of a tree it has not passed. Only then end the
   turn: a turn that ends on an unpushed commit trips the environment's stop hook.

On the GitHub Copilot app, start and wait for `run` as `.claude/workflow/hosts.md` says.

- `run` sets `NANOPNP_REQUIRE_GMSH=1` (and `NANOPNP_REQUIRE_APBS=1` where the wheel exists): a
  backend that cannot import fails, not skips.
- When only Markdown outside `packaging/`, `src/`, `data/` and `examples/` changed, the hook runs ruff alone
  (`.github/scripts/prose-only.sh`); CI's documentation build still runs.

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
- `io/` case schema, artefact and resolved-case types, result store, manifests; the base layer,
  importing only `core` at run time; `pipeline/` case resolution, the walk, the assembler; `api/` the
  Python interface (`Case`, `Session`, sweeps, reproduction), above `sweep/`; `cli/`,
  `gui/` thin shells that hold no physics; `validation/` benchmarks, MMS, COMSOL comparison

Outside it: `data/corrections/*.yaml` (fitted parameters, shipped in the wheel), `specification/`, `knowledge/`,
`tests/tier{1,2,3,4}/`, `docs/`, `docs/plans/` (planning, not requirements; `SPECIFICATION.md` wins).

A stage takes typed inputs and emits a typed, serialisable artefact carrying a content hash. Every
stage must stay independently invocable, cancellable and introspectable (FR-27).

## Testing

Tests live in `tests/tier{1,2,3,4}/` (§7.1); the directory's `conftest.py`
sets the marker, so location decides the tier.

| Tier | Content | Runtime | When |
|---|---|---|---|
| 1 | Unit and property tests (VER-01 … VER-11) | seconds | every push |
| 2 | Analytic benchmarks (VER-12 … VER-22) | minutes | every push |
| 3 | Cross-implementation comparison (VAL-01 … VAL-06, VAL-16, VAL-17) | hours | nightly, recorded not gated |
| 4 | Experimental reproduction (VAL-07 … VAL-14) | hours | before a tagged release |

- Write a test only for the test scope (`SPECIFICATION.md` §7.1; §8.2.13 N1): physics and numerics, core mechanisms,
  and the licence and architecture guards (CON-10, CON-12, VER-61, VER-65, no backend import). Each entry point
  keeps a thin smoke test. A refusal is tested only where it is a numerical or physical gate.
- A new test's name or first line says which silent failure it catches, e.g. `test_ver03_ion_wall_function_check_values`.
- A requirement identifier is named in a test only where the requirement is physics, numerics or a core mechanism;
  other identifiers are verified at review (§7.1; N3).
- Off-scope tests are deleted in their own `test: drop tests outside the test scope` commit by `/np-ship`. No
  tolerance is slackened and no kept test is weakened.
- Fix Tier 2 before chasing a Tier 3 discrepancy.
- No network and no COMSOL licence in tests; Tier 3 reads archived reference data.

## Provenance and reproducibility

The case file (`schema: nanopnp/case/v0.5`) is the unit of reproducibility. Every artefact carries a
content hash over its payload and producing parameters, which is its cache key. Every result carries a
manifest (input hashes, library versions, mesh hash, solver settings, stabilisation mode, correction
file versions, **every switch set away from the validated default**; FR-25, §5.3.3); one that cannot
reconstruct the run is not a result.

## Implementation workflow

One work package per PR, green on tiers 1–2 before the next in its lane (at most two lanes, §8.4.4). To plan or resume, read
`docs/plans/current.md`, then the WP's Execution brief and the sections it cites. A brief never
overrides a normative requirement.

| Step | Command | What it does |
|---|---|---|
| 0 | `/np-plan project`, `/np-plan phase <n>`, `/np-plan amend <n>` | Puts the decisions to the author; writes the rulings into `specification/history/` and the plan, pushes, opens its PR |
| 1 | `/np-plan wp <n>` | Writes and commits the WP plan, pushes, opens the package's PR |
| 2 | `/np-implement [wp <n>]` | Executes the plan, gates, pushes, opens or reuses the PR, stops |
| 3–4 | `/np-ship [wp <n>]` | Gates, pushes, reviews (`/code-review xhigh --fix`), drives CI to green |
| close | `/np-ship phase <n>` | Ships the close package and tags the release |

Step 2 does not chain into 3: `/np-ship` starts in a fresh session (`.claude/workflow/core.md`, *Report and
stop*). Plans before WP53 name these `/phase-plan`, `/wp-plan`, `/wp-implement` and `/wp-ship`. The steward skill
governs a PR in flight. Beside them, `/np-gui <render | review | publish | collect | grill>` pictures screens and
mockups headless, reviews them, publishes them for the author's verdicts and runs a design round (§8.4.4).

**Models:** implementation runs on Haiku for an easy mechanical item and on Sonnet by default. It moves to Opus
only after Sonnet fails on the item. Kept: the `physics-reviewer`, `gui-reviewer` and `ci-log-classifier` sub-agents and the
`.claude/scripts/clause.py` script. A WP plan is grounded in the code. It holds at most 3,500 words (1,500 outside
its Grounding and Implementation details) and six decisions. Its compaction checkpoints are work items, and each
ends the turn with a `/compact` prompt. It names the implementing model and the executor of each item: the main
session, or a sub-agent by type and model (§8.4.4; §8.2.15 Q1; §8.2.16 R11).

**Code review reports** go to `docs/code_reviews/CODE_REVIEW_NNN.md`, one above the highest present;
pass `out=`.

**Open items** (a finding not fixed, a deferral, a question for the author) are `REV-nn` rows in
`docs/project/review-findings.md` with a section in `review-items.md`, until the commit that
resolves one sets it `fixed` (§8.4.6; §8.2.8 H12). A PR body is never their only record.

## Git

- Conventional commits (`feat:`, `fix:`, `test:`, `docs:`, `chore:`), the identifier
  discharged in the body (`VER-03`).
- Versions are git tags, never a number in `pyproject.toml` or the package (§2.7); the procedure is
  `CONTRIBUTING.md`, *Versions and releases*.

## Prose in code

A docstring on every public function, class and method of `src/` (no leading underscore; a dunder method is public): a summary
line and NumPy-style parameters only where name and type do not say, without derivations or history. A one-line docstring on every
module; none on a test or private code. A comment only where the code cannot
say why it is so, and for the source of a physical constant. Identifiers live in test names and commit
messages (`.claude/rules/python.md`; §8.4.2; §8.2.11 L4).

## Durable learnings

Write a durable fact as a concept in the relevant `knowledge/` directory, or into an existing one, with
its source: mark a claim `[tested: <test>]`, naming a test in scope, or `[verified]`, with a source footnote, list the concept in the
directory's `index.md` and add a line to `knowledge/log.md`
(`knowledge/00-orientation/04-provenance-and-how-to-extend-this.md`). Status and scope opinions belong in
the specification.

## Do NOT

- Use `pip`, a hand-activated venv, or bare `python`/`pytest`.
- Import `gmsh` on the default path (GPLv2+, optional backend only; CON-10, ADR-002). Depend on
  Triangle, MeshPy or TetGen (CON-12). Use PyQt (PySide6 only; CON-09).
- Add anything to the end-user path needing a C++ compiler, source build or JIT (CON-07).
- Write the weak forms twice, or put backend-specific constructs in `physics/` (QR-13).
- Hard-code correction coefficients, `ε_protein` or any fitted parameter in Python.
- Add COMSOL import/export (N7), transient solves (N3), 3D (N4) or off-axis analytes (N5); the
  architecture must not preclude them.

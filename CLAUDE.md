# Project: nanopnp

Open-source Python reimplementation of the **ePNP-NS** framework for biological nanopores
(Willems et al., *Nanoscale* **12**, 16775–16795, 2020), replacing a COMSOL workflow.
2D-axisymmetric steady state; structure → mesh → solve → analyse. Python 3.11–3.14, developed on 3.14.

## Before doing anything

- **Read `.knowledge/00-index.md`**: the verified knowledge base.
- **`SPECIFICATION.md` is normative** (`FR-`, `QR-`, `CON-`, `PHY-`, `NUM-`, `VER-`, `VAL-`). Cite the
  identifier when you implement or test one. Changing specified behaviour means changing the
  specification in the same commit.
- **Never web-search the model equations, correction functions or parameters.** Popular summaries are
  wrong. `.knowledge/01-physics-epnpns.md` is normative; where sources disagree, the COMSOL model
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
| `uv run pytest` | Tiers 1–2 without `extended` tests: the development selection |
| `uv run pytest --extended` | All of tiers 1–2, as CI runs it. Naming an `extended` test's file runs it without the flag |
| `uv run pytest -n auto --dist loadfile` | Parallel; set `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS` to 1. `tests/tier1/test_gui_widgets.py` runs serially, apart |
| `uv run pytest -m tier1` / `-m tier3` / `-m slow` | Unit tests / reference comparison / benchmarks (the last two not gated) |
| `uv run ruff check . && uv run ruff format .`; `uv run mypy src/` | Lint and format; strict types |
| `uv run nanopnp --env` | Resolved environment and data locations |
| `uv sync --all-extras --group docs && uv run docs/scripts/generate.py && uv run mkdocs build --strict` | Documentation build, as CI's `docs` job (VER-45) |

Gate before committing: `uv run ruff check . && uv run ruff format --check . && uv run mypy src/ && uv run pytest -m tier1`.
Gate before pushing: `.claude/hooks/gate.sh run` (the above with `pytest --extended` over the whole suite, no
coverage). `gate.sh` runs before each `git commit` Claude Code makes (`--no-verify` skips it): the lock check,
lint, format, types and every Tier 1 test without the `extended` marker. A hook pass never stands in for `run`.
Start `run` with Bash `run_in_background` and push when it passes; the hook refuses a push of
a tree it has not passed.

- Changed-line branch coverage (`src/nanopnp/` outside `gui/`, `diff-cover` against `main`) is checked by CI alone.
  An exempt line says `# pragma: no cover - <reason>`. Coverage misses missing code and the untaken arm of
  `a if c else b`; write the tests with the item.
- `run` sets `NANOPNP_REQUIRE_GMSH=1` (and `NANOPNP_REQUIRE_APBS=1` where the wheel exists): a
  backend that cannot import fails, not skips.
- When only prose changed, the hook runs ruff alone (`.github/scripts/prose-only.sh`;
  `SPECIFICATION.md`, `docs/`, example READMEs and `.claude/{agents,skills,rules}/` are not prose,
  and `docs/plans/` neither: a change to only those runs the tests); CI's documentation build still runs.

## Project structure

`src/nanopnp/` has one subpackage per module of SPECIFICATION.md §5.1:

- `core/` units, constants, provenance, caching; `structure/` PDB/mmCIF and trajectory IO;
  `density/` smearing, ensemble averaging; `symmetry/` Cₙ averaging and reduction to (r, z)
- `geometry/` contours, CAD assembly, analyte bodies; `mesh/` mesher adapters (netgen, gmsh), size
  fields, quality gates; `numerics/` linear solvers, damped Newton, gates, the axisymmetric measure
- `charge/` PDB2PQR, partial charges, projection, dielectric; `materials/` electrolytes and the
  correction registry; `physics/` weak forms and the wall-distance field; `solve/` continuation
  ladder, warm start; `post/` QoI (current, transport number, EOF, forces); `sweep/` sweeps
- `io/` case schema, artefact and resolved-case types, result store, manifests; the base layer,
  importing only `core` at run time; `pipeline/` case resolution, the walk, the assembler; `cli/`,
  `gui/` thin shells that hold no physics; `validation/` benchmarks, MMS, COMSOL comparison

Outside it: `data/corrections/*.yaml` (fitted parameters, shipped in the wheel), `.knowledge/`,
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

- Name tests for the requirement they discharge: `test_ver03_ion_wall_function_check_values`.
- Fix Tier 2 before chasing a Tier 3 discrepancy.
- No network and no COMSOL licence in tests; Tier 3 reads archived reference data.

## Provenance and reproducibility

The case file (`schema: nanopnp/case/v0.5`) is the unit of reproducibility. Every artefact carries a
content hash over its payload and producing parameters, which is its cache key. Every result carries a
manifest (input hashes, library versions, mesh hash, solver settings, stabilisation mode, correction
file versions, **every switch set away from the validated default**; FR-25, §5.3.3); one that cannot
reconstruct the run is not a result.

## Implementation workflow

One work package per PR, green on tiers 1–2 before the next. To plan or resume, start at
`docs/plans/current.md`, then the WP's Execution brief and its cited sections; a brief never
overrides a normative requirement.

| Step | Command | What it does |
|---|---|---|
| 0 | `/phase-plan <n\|amend>` | Puts the phase's decisions to the author; writes rulings into §8.2 and the plan |
| 1 | `/wp-plan <n>` | Writes and commits the WP plan |
| 2 | `/wp-implement` | Executes the plan, gates, pushes, opens or reuses the PR, stops |
| 3–4 | `/wp-ship` | Gates, pushes, reviews (`/code-review xhigh --fix`), drives CI to green |

Step 2 does not chain into 3: `/wp-ship` starts in a fresh session (`wp-ship` §4). The steward skill
governs a PR in flight.

**Models:** implementation runs on Haiku for an easy mechanical item and on Sonnet by default, and
moves to Opus only after Sonnet has failed on the item. Sub-agents kept: `physics-reviewer`,
`ci-log-classifier` and the `.claude/scripts/clause.py` script. Plans hold at most 1,500 words and six
decisions, with compaction checkpoints (VER-72 g).

**Code review reports** go to `docs/code_reviews/CODE_REVIEW_NNN.md`, one above the highest present;
pass `out=`.

**Open items** (a finding not fixed, a deferral, a question for the author) are `REV-nn` rows in
`docs/project/review-findings.md` with a section in `review-items.md`, until the commit that
resolves one sets it `fixed` (§8.2.8 H12). A PR body is never their only record.

## Git

- Conventional commits (`feat:`, `fix:`, `test:`, `docs:`, `chore:`), the identifier
  discharged in the body (`VER-03`).
- Versions are git tags, never a number in `pyproject.toml` or the package (§2.7); the procedure is
  `CONTRIBUTING.md`, *Versions and releases*.

## Prose in code

A docstring only on the public API (`nanopnp.PUBLIC`, the CLI commands, the GUI entry points) and a
one-line docstring on every module; none on a test or private code. A comment only where the code cannot
say why it is so, and for the source of a physical constant. Identifiers live in test names and commit
messages (`.claude/rules/python.md`; §8.2.11 L4).

## Durable learnings

Write a durable fact into the relevant `.knowledge/` file, with its source, marked **[tested]** or
**[verified]** (`.knowledge/00-index.md`, *Conventions*). Status and scope opinions belong in the
specification.

## Do NOT

- Use `pip`, a hand-activated venv, or bare `python`/`pytest`.
- Import `gmsh` on the default path (GPLv2+, optional backend only; CON-10, ADR-002). Depend on
  Triangle, MeshPy or TetGen (CON-12). Use PyQt (PySide6 only; CON-09).
- Add anything to the end-user path needing a C++ compiler, source build or JIT (CON-07).
- Write the weak forms twice, or put backend-specific constructs in `physics/` (QR-13).
- Hard-code correction coefficients, `ε_protein` or any fitted parameter in Python.
- Add COMSOL import/export (N7), transient solves (N3), 3D (N4) or off-axis analytes (N5); the
  architecture must not preclude them.

# Project: nanopnp

Open-source Python reimplementation of the **ePNP-NS** continuum framework for simulating
biological nanopores (Willems et al., *Nanoscale* **12**, 16775–16795, 2020), replacing a COMSOL
workflow. 2D-axisymmetric steady state; structure → mesh → solve → analyse as one pipeline.
Python 3.11–3.14, developed on 3.12.

## Before doing anything

- **Read `.knowledge/00-index.md`**: the verified knowledge base (physics, numerics, biology, tooling).
- **`SPECIFICATION.md` is normative** (`FR-`, `QR-`, `CON-`, `PHY-`, `NUM-`, `VER-`, `VAL-`). Cite the
  identifier when you implement or test one. Changing specified behaviour means changing the
  specification in the same commit.
- **Never web-search the model equations, correction functions or parameters.** Popular summaries are
  wrong. `.knowledge/01-physics-epnpns.md` is normative and documents five errata; where sources
  disagree, the COMSOL model report governs (§1.6). Web search is fine for library versions/APIs
  (prefer Context7) and post-knowledge-base literature.

## Setup

`uv` owns the environment: no `pip`, no manual `activate`, no bare `python`/`pytest`.

- `uv sync --all-extras` — create or refresh `.venv` from `uv.lock`
- `uv add <pkg>` / `uv add --group dev <pkg>` — add a dependency
- `uv run <anything>` — the only way code is executed
- After hand-editing `pyproject.toml`, run `uv lock`; CI runs with `UV_LOCKED` and fails on a stale lock.

## Commands

| Command | Purpose |
|---|---|
| `uv run pytest` | Tiers 1–2 without `extended` tests; the commit hook's selection |
| `uv run pytest --extended` | All of tiers 1–2; the push gate, as CI runs it |
| `uv run pytest -n auto --dist loadfile` | Parallel; set `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS` to 1. `tests/tier1/test_gui_widgets.py` runs separately and serially |
| `uv run pytest -m tier1` / `-m tier3` / `-m slow` | Unit tests / reference comparison (nightly, not gated) / benchmarks (not gated) |
| `uv run pytest <file>::<test> -v` | One test |
| `uv run ruff check . && uv run ruff format .` | Lint and format |
| `uv run mypy src/` | Type check (strict) |
| `uv run nanopnp --env` | Resolved environment and data locations |
| `uv sync --all-extras --group docs && uv run docs/scripts/generate.py && uv run mkdocs build --strict` | Documentation build, as CI's `docs` job (VER-45) |

Gate before committing: `uv run ruff check . && uv run ruff format --check . && uv run mypy src/ && uv run pytest`.
Gate before pushing: `.claude/hooks/gate.sh run` (the above with `--extended`, plus coverage of changed lines).
`.claude/hooks/gate.sh` runs automatically before each `git commit` Claude Code makes; `--no-verify`
skips it. A pass of the hook's development selection never stands in for `run`.

## Project structure

`src/nanopnp/` has one subpackage per module of SPECIFICATION.md §5.1. `cli/` and `gui/` are thin
shells holding no physics. Outside it: `data/corrections/*.yaml` (fitted parameters, shipped in the
wheel), `.knowledge/`, `tests/tier{1,2,3,4}/`, `docs/`, `docs/plans/` (delivery plan for the current
phase; planning, not requirements — `SPECIFICATION.md` wins).

A stage takes typed inputs and emits a typed, serialisable artefact carrying a content hash. Every
stage must stay independently invocable, cancellable and introspectable (FR-27).

## Physics ground rules

- **Corrections are data, not code.** Parameters live in `data/corrections/*.yaml`; a new electrolyte
  never touches solver code.
- **Classical PNP-NS is a configuration, not a branch.** Each correction is independently switchable;
  disabling one selects the `none` model, not a code branch.
- **Deviations from the validated model go behind a flag, default off**, and must be verified against
  COMSOL before becoming default (e.g. dielectric-gradient body force, mollified distance field, an
  added mobility correction).
- **`⟨c⟩` is `(1/n)Σcᵢ`, not the ionic strength.** `d` is the distance to the nearest **pore**
  boundary; the membrane is excluded.
- **Einstein holds only at infinite dilution.** Never assert `D_i/μ_i = kT/e` at finite concentration
  (VER-05, PHY-14). Poisson–Boltzmann is not "PNP at zero bias" (PHY-24).
- **Ion wall function: `1 − exp(−6.2(d̄ + 0.01))`** — plus, 6.2 nm⁻¹. The viscosity wall function takes
  a minus. Steric `β_i` enters the flux bracket with `+`, and the bracket is negated; a flipped sign
  diverges.

## Numerics rules

- **Assert, don't hope.** Charge conservation, packing fraction < 1, concentration positivity at every
  Newton iterate, mesh quality (min SICN/gamma > 0.3). A gate failure aborts with a diagnostic naming
  the gate, quantity and location (QR-12). Never return a plausible wrong answer.
- **Integration order ≥ 3 on every form carrying `1/r`** (VER-07); order 2 samples `r = 0` and gives NaN.
- **Never compute ionic current from a cross-section integral of the CG flux.** Use the indicator form
  or the variational reaction flux, and cross-check both (FR-23, QR-04; `.knowledge/06` §7).
- **Newton convergence needs the relative update on the undamped direction as well as the residual**;
  residual alone breaks warm starts. Never call a step that raised the residual convergence.
- **Reach hard cases by continuation, not a cold solve** (FR-17); warm-start sweeps from a converged
  neighbour.
- **Record the stabilisation mode with every number.** COMSOL ran streamline and crosswind
  stabilisation on; results are not comparable until matched (§6.4, §7.4).

## Coding conventions

- `from __future__ import annotations` in every module; type hints on every signature; `mypy --strict` clean.
- NumPy-style docstrings on public functions.
- SI internally; units in the name at the boundary (`radius_nm`, `bias_V`). No bare floats in interfaces.
- British spelling in prose and identifiers (`normalise`, `analyse`).
- `pathlib.Path`, never `os.path`. f-strings, never `%`/`.format()` (exceptions: one `%` over a whole
  numeric array as in `validation/apbs.py`'s `write_dx`; lazy `logging` arguments).
- Pydantic models at every serialisation boundary; never raw dicts across a stage boundary.
- `logging`, never `print()`, outside the CLI's own output. No `import *`.
- Cite the source (`.knowledge/` file or specification section) of every physical constant and fit
  coefficient in a comment.
- **Imports at the top of the module.** Exceptions, imported inside the function that uses them:
  `ngsolve`, `netgen`, `numpy`, `scipy` (import cost; stage modules are imported just to introspect),
  and an optional extra's package in a module that must work without it (a missing extra is refused
  naming it). Defer nothing else.

## Testing

Tests live in `tests/tier{1,2,3,4}/` (tiers per SPECIFICATION.md §7.1); the directory's `conftest.py`
sets the marker, so the file's location decides its tier.

- Name tests for the requirement they discharge: `test_ver03_ion_wall_function_check_values`.
- Fix Tier 2 before chasing a Tier 3 discrepancy; an analytic test localises an error, a whole-model
  comparison does not.
- No network and no COMSOL licence in tests; Tier 3 reads archived reference data.

## Provenance and reproducibility

The case file (`schema: nanopnp/case/v2`) is the unit of reproducibility. Every artefact carries a
content hash over its payload and producing parameters, which is its cache key. Every result carries a
manifest (input hashes, library versions, mesh hash, solver settings, stabilisation mode, correction
file versions, **every switch set away from the validated default**; FR-25, §5.3.3). A result whose
manifest cannot reconstruct the run is not a result.

## Implementation workflow

One work package per PR, green on tiers 1–2 before the next. To plan or resume, start at
`docs/plans/current.md`, then the WP's Execution brief and its cited sections. Keep the brief bounded;
a brief never overrides a normative requirement.

| Step | Command | What it does |
|---|---|---|
| 0 | `/phase-plan <n\|amend>` | Puts the phase's decisions to the author; writes rulings into §8.2 and the plan into `docs/plans/` |
| 1 | `/wp-plan <n>` | Writes and commits the WP implementation plan |
| 2 | `/wp-implement` | Executes the plan, keeps specification/knowledge/plan in step, gates, pushes, opens or reuses the PR, stops |
| 3–4 | `/wp-ship` | Gates, pushes, runs `/code-review xhigh --fix`, drives CI to green |

Step 2 does not chain into 3: the user starts `/wp-ship` in a fresh session. `.claude/skills/steward/SKILL.md`
governs a PR in flight and is read when a PR event wakes a session.

**Sub-agent models:** work whose error would be a plausible wrong number runs on Opus; work whose error
is loud (lint, types, search, mechanical edits) runs on Sonnet. State the choice when delegating
(`.claude/model-policy.md`).

**Code review reports** from `/codebase-review` go to `docs/code_reviews/CODE_REVIEW_NNN.md`, numbered
one above the highest present, never reused; pass `out=` so no root `CODE_REVIEW.md` remains.

**Open items** (a confirmed finding not fixed, a deferral, a question for the author) are `REV-nn` rows
in `docs/project/review-findings.md` with a section in `docs/project/review-items.md`, until the commit
that resolves one sets it `fixed` (§8.2.8 H12). A PR body may summarise them, never be their only record.

## Git

- Conventional commits (`feat:`, `fix:`, `test:`, `docs:`, `chore:`); name the requirement identifier
  discharged in the body (`VER-03`, `FR-16`).
- Versions are git tags, never a number in `pyproject.toml` or the package (§2.7). A WP's PR writes its
  `CHANGELOG.md` section under `vX.Y.Z-alpha.N`; after merge, tag its last commit on `main`
  (`CONTRIBUTING.md`, *Versions and releases*).

## Durable learnings

Write a durable fact into the relevant `.knowledge/` file, marked **[tested]** or **[verified]** with
its source. Keep status, task lists and scope opinions out of `.knowledge/`; they belong in the specification.

## Do NOT

- Use `pip`, a hand-activated venv, or bare `python`/`pytest`.
- Import `gmsh` on the default path (GPLv2+, optional backend only; CON-10, ADR-002). Depend on
  Triangle, MeshPy or TetGen (CON-12). Use PyQt (PySide6 only; CON-09).
- Add anything to the end-user path needing a C++ compiler, source build or JIT (CON-07).
- Write the weak forms twice, or put backend-specific constructs in `physics/` (QR-13).
- Hard-code correction coefficients, `ε_protein` or any fitted parameter in Python.
- Add COMSOL import/export (N7), transient solves (N3), 3D (N4) or off-axis analytes (N5); the
  architecture must not preclude them.

# Project: nanopnp

Open-source Python reimplementation of the **ePNP-NS** continuum framework for simulating
biological nanopores (Willems et al., *Nanoscale* **12**, 16775–16795, 2020), replacing a COMSOL
workflow. 2D-axisymmetric steady state first; structure → mesh → solve → analyse as one pipeline.
Python 3.10–3.14, developed on 3.12. Environment, tests and runs all go through `uv`.

## Before doing anything

**Read `.knowledge/00-index.md`.** It indexes a local knowledge base covering the physics,
numerics, biology and tooling of this project, extracted from primary sources and numerically
verified.

**`SPECIFICATION.md` is normative** for requirements (`FR-`, `QR-`, `CON-`), physics (`PHY-`),
numerics (`NUM-`) and verification (`VER-`, `VAL-`). Cite the identifier when you implement or test
one. Changing specified behaviour means changing the specification in the same commit, not
diverging from it quietly.

**Do not search the web for the model equations, the correction functions, or their parameters.**
Several widely-copied summaries of this model are wrong. `.knowledge/01-physics-epnpns.md` is the
normative reference and documents five errata in the original sources, with the arithmetic. Where
the printed sources, author recollection and the COMSOL model report disagree, **the model report
governs** (§1.6).

Web search *is* appropriate for: current library versions and APIs (prefer the Context7 MCP for
library docs), and literature published after the knowledge base was written.

## Setup

`uv` owns the environment. There is no `pip`, no manual `activate`, no bare `python`.

- `uv sync --all-extras` — create or refresh `.venv` from `uv.lock`
- `uv add <pkg>` / `uv add --group dev <pkg>` — add a dependency and update the lock
- `uv run <anything>` — run inside the environment; the only way code is executed here

`uv.lock` is committed and CI runs with `UV_LOCKED`, which fails every job when the lock no longer
matches `pyproject.toml`: if you edit `pyproject.toml` by hand, run `uv lock` before committing.
(`--frozen` would not catch that; it installs the stale lock as it stands.)

## Commands

| Command | Purpose |
|---|---|
| `uv run pytest` | Tiers 1 and 2 — the default selection, and the push gate |
| `uv run pytest -n auto --dist loadfile` | The same, in parallel as CI and the gate run it; set `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS` and `MKL_NUM_THREADS` to 1 or the workers oversubscribe (`.knowledge/07` §12). CI and the gate run `tests/tier1/test_gui_widgets.py` separately and serially, because it waits on a real web page by the wall clock |
| `uv run pytest -m tier1` | Unit and property tests only (seconds) |
| `uv run pytest -m tier3` | COMSOL comparison; nightly, not a push gate |
| `uv run pytest -m slow --log-cli-level=INFO` | Benchmarks and envelope runs; measured, never gated |
| `uv run pytest tests/tier1/test_corrections.py::test_ver03_ion_wall_function_check_values -v` | One test |
| `uv run pytest --cov=src/nanopnp --cov-report=term-missing` | Coverage |
| `uv run ruff check . && uv run ruff format .` | Lint and format |
| `uv run mypy src/` | Type check (strict) |
| `uv run nanopnp --env` | Report the resolved environment and data locations |
| `uv sync --group docs && uv run docs/scripts/generate.py && uv run mkdocs build --strict` | The documentation site, as CI's `docs` job builds it (VER-45); generated pages go to the gitignored `docs/_generated/` |

Before committing, run the whole gate:

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src/ && uv run pytest
```

`.claude/hooks/gate.sh` runs that gate, plus `uv lock --check`, automatically before any `git commit`
Claude Code makes, and refuses the commit with the failing output if a stage fails or its 25-minute
budget runs out. It gates the working tree and remembers a pass, so a tree that already passed is
not re-run. When only prose changed it runs ruff alone. Prose means Markdown outside `packaging/`,
`src/`, `data/` and `examples/`; `docs/` as a whole doesn't count, because tests read its YAML, and
an example's README is executed by its test (VER-46). The rule is `.github/scripts/prose-only.sh`,
and CI uses the same script. CI's strict documentation build runs on every push, prose included.
`.claude/hooks/gate.sh run` runs the same gate by hand; the skills use it. `git commit --no-verify`
(or `-n`) skips it. It does not fire for commits you make yourself in a terminal.

## Project structure

`src/` layout: the package is `src/nanopnp/`, one subpackage per module of SPECIFICATION.md §5.1.

- `core/` — units, constants, validation, provenance, caching, logging
- `structure/` — PDB/mmCIF and trajectory IO, alignment, symmetry-axis detection
- `density/` — Gaussian smearing to grid, ensemble averaging, grid IO
- `symmetry/` — Cₙ averaging, azimuthal reduction to (r, z), variance diagnostics
- `geometry/` — contour extraction, polyline conditioning, CAD assembly, analyte bodies
- `mesh/` — mesher adapters (netgen, gmsh), size fields, boundary layers, quality gates
- `charge/` — PDB2PQR driver, partial charges, smearing, axisymmetric projection, dielectric
- `materials/` — electrolyte models and the pluggable correction registry
- `physics/` — weak forms: Poisson, Nernst–Planck, Navier–Stokes; axisymmetric measures
- `solve/` — backend adapters, continuation ladder, nonlinear and linear strategies, warm start
- `post/` — QoI extraction: current, transport number, EOF, rectification, forces
- `sweep/` — parameter sweeps, job-array dispatch, result collection
- `io/` — case-file schema, result store, provenance manifests
- `cli/`, `gui/` — thin shells over the stage objects; they hold no physics
- `validation/` — benchmarks, MMS, COMSOL comparison harness, regression fixtures

Outside the package: `data/corrections/*.yaml` (fitted parameters, shipped in the wheel),
`.knowledge/` (verified domain knowledge), `tests/tier{1,2,3,4}/`, `docs/`.

`docs/plans/` holds the delivery plan for the phase in progress — the work-package breakdown,
what has merged, and the decisions still open. It is planning, not requirements: `SPECIFICATION.md`
still governs, and a plan that disagrees with it is the thing that is wrong.

A stage takes typed inputs and emits a typed, serialisable artefact carrying a content hash. Every
stage must stay independently invocable, cancellable and introspectable (FR-27) — that is what the
CLI, the GUI and the sweep runner all depend on.

## Physics ground rules

- **The corrections are data, not code.** Parameters live in `data/corrections/*.yaml`. Adding an
  electrolyte should never require touching solver code.
- **Classical PNP-NS is a configuration, not a branch.** Every correction is independently
  switchable; that is what makes ablation studies and differential testing possible. Disabling one
  selects the `none` model rather than taking a code branch.
- **Deviations from the validated model go behind a flag, default off.** The published agreement
  with experiment was obtained with a specific set of terms. Anything extra — the
  dielectric-gradient body force, a mollified distance field, an added mobility correction — is
  opt-in and must be verified against COMSOL before it becomes default.
- **`⟨c⟩` is the average ion concentration `(1/n)Σcᵢ`, not the ionic strength.** They coincide for a
  symmetric 1:1 salt and diverge otherwise. `d` is the distance to the nearest **pore** boundary;
  the membrane is deliberately excluded from the distance field.
- **The Einstein relation holds only at infinite dilution.** `D` and `μ` carry different
  concentration corrections, so `D_i/μ_i` drifts to 1.2–1.7 × kT/e between 0.15 M and 3 M. Never
  assert `D_i/μ_i = kT/e` at finite concentration (VER-05, PHY-14), and never implement
  Poisson–Boltzmann as "the PNP solver at zero bias" — it is a distinct model (PHY-24).
- **The ion wall function is `1 − exp(−6.2(d̄ + 0.01))`** — plus, not minus, and 6.2 nm⁻¹. The
  viscosity wall function takes a minus. The steric `β_i` enters the flux bracket with a `+` and the
  bracket is negated; a flipped sign drives ions into crowded regions and diverges.

## Numerics rules

- **Assert, don't hope.** Charge conservation, packing fraction < 1, concentration positivity at
  every Newton iterate, mesh quality gates (min SICN/gamma > 0.3). Every gate failure aborts the run
  with a diagnostic naming the gate, the offending quantity and its location (QR-12). Never return a
  plausible wrong answer.
- **Integration order ≥ 3 on every form carrying `1/r`** (VER-07). NGSolve's order-2 triangle rule
  samples `r = 0` exactly on axis-touching elements and returns NaN.
- **Never compute the ionic current from a cross-section integral of the CG flux.** Use the
  domain/indicator form or the variational reaction flux, and check the two routes against each
  other (FR-23, QR-04). See `.knowledge/06-numerics-fem.md` §7.
- **A Newton convergence test on the residual alone breaks warm starts.** Relative to the entry
  residual, re-solving a converged state demands another six orders of magnitude — and that is what
  every rung of the continuation ladder does. Test the relative update on the *undamped* direction
  as well, and never call a step that raised the residual convergence.
- **Reach hard cases by continuation, not by a cold solve.** The ladder is how the 0.005–5 M ×
  ±200 mV envelope converges (FR-17); warm-start sweeps from a converged neighbour.
- **Record the stabilisation mode with every number.** The reference COMSOL model had streamline and
  crosswind stabilisation *on*; ours is not comparable until that is matched (§6.4, §7.4).

## Coding conventions

- `from __future__ import annotations` at the top of every module; type hints on every signature —
  `mypy --strict` runs over `src/` and must stay clean.
- NumPy-style docstrings on public functions (scientific convention here, not Google style).
- **SI internally, units in the name at the boundary**: `radius_nm`, `bias_V`, `temperature_K`. A
  bare float in an interface is a bug waiting to happen.
- British spelling in prose and identifiers (`normalise`, `analyse`), matching the specification.
- `pathlib.Path`, never `os.path`. f-strings, never `%` or `.format()`.
- Pydantic models at every serialisation boundary — case files, artefacts, manifests. Never pass
  raw dicts across a stage boundary.
- `logging`, never `print()`, outside the CLI's own output.
- Cite the source of every physical constant and fit coefficient in a comment, pointing at the
  `.knowledge/` file or the specification section it came from.
- **Imports go at the top of the module. `ngsolve`, `netgen` and `numpy` are the exceptions**, and
  are imported inside the function that uses them. `import ngsolve` costs ~370 ms and `import numpy`
  ~67 ms, and the CLI, the GUI and the sweep runner all import stage modules purely to introspect a
  stage (FR-27) without ever assembling a form — so a sweep dispatching a job array pays that per
  process. Deferring keeps `import nanopnp.cli` at ~70 ms; at module scope the physics and mesh
  modules alone would cost 424 ms rather than 56 ms. Defer nothing else: a stdlib import buys
  microseconds and just makes the module harder to read.

## Testing

Tests live in `tests/tier{1,2,3,4}/`, matching the four verification tiers of §7.1; the directory's
`conftest.py` applies the tier marker, so placing the file decides its tier.

| Tier | Content | Runtime | When |
|---|---|---|---|
| 1 | Unit and property tests (VER-01 … VER-11) | seconds | every push |
| 2 | Analytic benchmarks (VER-12 … VER-22) | minutes | every push |
| 3 | COMSOL cross-implementation comparison (VAL-01 … VAL-06) | hours | nightly, recorded not gated |
| 4 | Experimental reproduction (VAL-07 … VAL-14) | hours | before a tagged release |

- **Name tests for the requirement they discharge**: `test_ver03_ion_wall_function_check_values`,
  `test_val05_contour_against_published_polygon`. Appendix A traceability is then mechanical.
- An analytic test localises an error to a single term; a whole-model comparison localises nothing.
  Fix Tier 2 before chasing a Tier 3 discrepancy.
- Tests must not reach the network and must not need a COMSOL licence; Tier 3 reads archived golden
  files.

## Provenance and reproducibility

The case file (`schema: nanopnp/case/v1`) is the unit of reproducibility; everything else is
derived. Every artefact carries a content hash over its payload and the parameters that produced it,
and that hash is the cache key. Every result carries a provenance manifest — input hashes, library
versions, mesh hash, solver settings, stabilisation mode, correction file versions, and **every
switch set away from the validated default** (FR-25, §5.3.3). A result whose manifest cannot
reconstruct the run is not a result.

## Implementation workflow

Work is delivered one work package at a time, one PR per package, green on tiers 1 and 2 before the
next starts. Four steps, in three skills under `.claude/skills/`:

For planning or resuming work, start at `docs/plans/current.md`, then the requested WP's Execution
brief and its cited sections. Load historical summaries and derivations on demand, not by default.
Keep the current brief bounded and replace stale entries; preserve detailed evidence in its owning
specification, knowledge or plan section. A brief never overrides a normative requirement.

| Step | Command | What it does |
|---|---|---|
| 1 | `/wp-plan <n\|phase-n>` | Writes the implementation plan into `docs/plans/` and commits it. The decisions table is the deliverable |
| 2 | `/wp-implement` | Executes the plan; keeps the specification, knowledge and Outcomes in step; gates, pushes, opens or reuses the PR, then stops |
| 3–4 | `/wp-ship` | Gates, pushes, reuses the PR (opens one if missing), runs `/code-review xhigh --fix`, then drives CI to green |

`.claude/skills/steward/SKILL.md` carries the conventions for a PR already in flight — what each CI
failure class means here, and why a failing Tier 2 benchmark is evidence rather than a chore. It is
read automatically when a PR event wakes a session, so it governs the autofix loop whether or not
`/wp-ship` started it.

Step 2 does not chain into step 3. The user starts `/wp-ship` in a fresh session, so the review
pass runs from a session that did not make the physics decisions; `wp-ship` §4 says how that pass is
invoked and what counts as its completion.

**Sub-agent models: the failure mode decides, not the size of the task.** Work whose error would be
a plausible wrong number runs on Opus; work whose error is loud — lint, types, search, mechanical
edits — runs on Sonnet. State the choice when delegating so it can be redirected. The rubric is
`.claude/model-policy.md`.

## Git

- Conventional commits: `feat:`, `fix:`, `test:`, `docs:`, `chore:`.
- Name the requirement identifier the commit discharges in the body (`VER-03`, `FR-16`).
- Run the full gate above before committing (`.claude/hooks/gate.sh run`).

## When you learn something durable

Write it into the relevant `.knowledge/` file, marked **[tested]** (verified by running code) or
**[verified]** (verified by arithmetic), with its source. A fact re-derived twice should have been
written down the first time.

Keep project status, task lists and scope opinions out of `.knowledge/` — those belong in the
specification.

## Do NOT

- Do not use `pip`, a hand-activated venv, or a bare `python`/`pytest`. Everything is `uv run`.
- Do not import `gmsh` on the default path — GPLv2+, optional backend only (CON-10, ADR-002). Never
  depend on Triangle, MeshPy or TetGen at all (CON-12). Never use PyQt; PySide6 only (CON-09).
- Do not add anything to the end-user path that needs a C++ compiler, a source build or a JIT
  toolchain (CON-07) — that constraint is why NGSolve was chosen over DOLFINx.
- Do not write the weak forms twice. They are expressed once against the internal backend interface
  (QR-13); backend-specific constructs stay out of `physics/`.
- Do not hard-code correction coefficients, `ε_protein`, or any fitted parameter in Python.
- Do not add COMSOL import or export (N7), transient solves (N3), 3D (N4) or off-axis analytes (N5)
  — all out of scope for v1, though the architecture must not preclude them.
- Do not use `import *`, `print()`, or `os.path`.

# Project: nanopnp

Open-source Python reimplementation of the **ePNP-NS** framework for biological nanopores
(Willems et al., *Nanoscale* **12**, 16775–16795, 2020). It replaces a COMSOL workflow.
2D-axisymmetric steady state; structure → mesh → solve → analyse. Python 3.11–3.14, developed on 3.14.

## Before doing anything

- **Read `knowledge/index.md`.** It is the verified knowledge base.
- **`SPECIFICATION.md` is normative** (`FR-`, `QR-`, `CON-`, `PHY-`, `NUM-`, `VER-`, `VAL-`). It is the
  map; the text is in `specification/`, the dated rulings in `specification/history/`, read on
  demand. `uv run .claude/scripts/clause.py <ID>` prints a clause. Cite the identifier when you
  implement or test one. A change to specified behaviour changes the specification in the same commit.
- **Never web-search the model equations, correction functions or parameters.** Popular summaries are
  wrong. §4 of `SPECIFICATION.md` states the model's equations and governs them; the concepts under
  `knowledge/01-physics-epnpns/` back it. Where sources disagree, the COMSOL model report governs
  (§1.6). Web search is fine for library versions and APIs (prefer Context7) and for literature
  newer than the knowledge base.
- **Rules by path.** `.claude/rules/physics-numerics.md` and `.claude/rules/python.md` load when you
  read or edit a file they cover. The second governs prose in code (§8.4.2). A session that writes
  only Markdown reads them explicitly.

## Setup

`uv` owns the environment. Use no `pip`, no manual `activate`, no bare `python` or `pytest`.

- `uv sync --all-extras` creates or refreshes `.venv` from `uv.lock`. A stale `.venv` in a session
  takes `--frozen` too: it installs `uv.lock` as it is. The gate and CI fail on a stale lock.
- `uv add [--group dev] <pkg>` adds a dependency. After a hand edit of `pyproject.toml`, run `uv lock`.
- `uv run <anything>` is the only way to run code.

## Commands

| Command | Purpose |
|---|---|
| `uv run pytest` | Tiers 1–2 without `nightly` and `slow` tests: the default selection |
| `uv run pytest --nightly` | Adds the `nightly` walks; `-m "(tier1 or tier2) and slow"` adds the `slow` tests. Naming a `nightly` test's file runs it without the flag |
| `uv run pytest -n auto --dist loadfile` | Parallel. Set `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS` and `MKL_NUM_THREADS` to 1 |
| `uv run pytest -m tier1` / `-m tier3` / `-m slow` | Unit tests / reference comparison / benchmarks (the last two are not gated) |
| `uv run ruff check . && uv run ruff format .`; `uv run mypy src/` | Lint and format; strict types |
| `uv run nanopnp --env` | The resolved environment and data locations |
| `uv run just docs` | The strict documentation build with CI's `docs` checks (VER-45) |
| `uv run just` | Lists `justfile`'s recipes. None commits or pushes |

**The gate.** The commit hook, `.claude/hooks/gate.sh`, runs lint, format, types and Tier 1 before each
`git commit` that Claude Code makes. Do not run them by hand first: a manual run writes no stamp, so
the hook runs them again. A push needs `.claude/hooks/gate.sh run` to pass on its tree, as the core's
*Gate and push* says (`.claude/workflow/core.md`); a main session runs it, through `just land`, and a
helper of `/np-carry` only commits (§8.2.56 BF11). A change confined to Markdown and `.claude/`, but
`.claude/scripts/decisions.py`, runs only ruff, the decisions check and the `records` tests
(`.github/scripts/prose-only.sh`).

## Project structure

`src/nanopnp/` has one subpackage per module of SPECIFICATION.md §5.1:

- `core/` units, constants, content hashing, errors, paths, the stage registry; `structure/` PDB/mmCIF
  and trajectory IO; `density/` smearing, ensemble averaging; `symmetry/` Cₙ averaging and reduction
  to (r, z)
- `geometry/` contours, CAD assembly, analyte bodies; `mesh/` mesher adapters (netgen, gmsh), size
  fields, quality gates; `numerics/` linear solvers, damped Newton, gates, the axisymmetric measure
- `charge/` PDB2PQR, partial charges, projection, dielectric; `materials/` electrolytes and the
  correction registry; `physics/` weak forms and the wall-distance field; `solve/` continuation
  ladder, warm start; `post/` QoI (current, transport number, EOF, forces); `plot/` figures of the
  artefacts (Matplotlib, the `plot` extra); `sweep/` sweeps
- `io/` case schema, artefact and resolved-case types, result store, provenance manifests. It is the
  base layer and imports only `core` at run time. `pipeline/` case resolution, the walk, the
  assembler; `api/` the Python interface (`Case`, `Session`, sweeps, reproduction), above `sweep/`;
  `cli/` and `gui/` are thin shells that hold no physics; `validation/` benchmarks, MMS, COMSOL
  comparison

Outside it: `data/corrections/*.yaml` (fitted parameters, shipped in the wheel) and `docs/plans/`
(planning, not requirements; `SPECIFICATION.md` wins).

A stage takes typed inputs and emits a typed, serialisable artefact that carries a content hash.
Every stage stays independently invocable, cancellable and introspectable (FR-27).

## Testing

A test's directory, `tests/tier{1,2,3,4}/`, decides its tier (§7.1).

| Tier | Content | Runtime | When |
|---|---|---|---|
| 1 | Unit and property tests (VER-01 … VER-11) | seconds | every push |
| 2 | Analytic benchmarks (VER-12 … VER-22) | minutes | every push |
| 3 | Cross-implementation comparison (VAL-01 … VAL-06, VAL-16, VAL-17) | hours | nightly, recorded not gated |
| 4 | Experimental reproduction (VAL-07 … VAL-14) | hours | before a tagged release |

- **The test scope** is §7.1 and §8.2.13 N1. Write a test only for physics and
  numerics, core mechanisms, and the licence and architecture guards (CON-10, CON-12, VER-61,
  VER-65, VER-79, no backend import). Each entry point keeps a thin smoke test. Test a refusal only
  where it is a numerical or physical gate.
- A new test's name or first line says which silent failure it catches, for example
  `test_ver03_ion_wall_function_check_values`.
- Name a requirement identifier in a test only where the requirement is physics, numerics or a core
  mechanism. Other identifiers are verified at review (§7.1; N3).
- No tolerance is slackened and no kept test is weakened.
- Fix Tier 2 before you chase a Tier 3 discrepancy.
- Tests use no network and no COMSOL licence. Tier 3 reads archived reference data.

## Provenance and reproducibility

The case file (`schema: nanopnp/case/v0.6`) is the unit of reproducibility. Every artefact carries a
content hash over its payload and producing parameters: its cache key. Every result
carries a manifest (FR-25, §5.3.3). The manifest holds the input hashes, library versions, mesh
hash, solver settings, stabilisation mode, correction file versions and **every switch set away from
the validated default**. A result whose manifest cannot reconstruct the run is not a result.

## Implementation workflow

One work package per PR, green on tiers 1–2 before the next one in its lane (at most two lanes,
§8.4.4).

- `/np-plan <project | phase n | amend n | wp n>` puts the decisions to the author and commits the
  plan; with `review` after the level it reviews the plan and summarises it for approval.
- `/np-implement [wp <n>]` executes the plan, gates, pushes and opens the PR.
- `/np-ship [wp <n> | phase <n>]` runs the `/code-review` hunt in the main session, has `np-reviewer`
  review the package and its findings and fix them once, drives CI to green and prints the tag
  commands. A phase's close also tags the release.
- `/np-carry wp <n>` runs all three in one session through fresh helpers, which commit; the main
  session lands each hand-back's commits with `just land`.
- `/np-chore <what>` makes one change no package owns, in a session of its own where no carry runs:
  a branch from `main`, a review unless it is Markdown alone, `just land`, a `chore:` PR the author merges.

§8.4.4 holds the workflow's rules and pauses; §8.4.5 the agents, the models and the kept scripts. A
choice put to the author follows `.claude/workflow/author.md`.

**Models:** by role, fixed in `.claude/agents/` (§8.4.5). `/np-plan` asks first, and plans on Fable 5.2
at high effort, or on Opus 5.5 at xhigh when Fable's quota is spent. Opus 5.5 at high builds and
reviews; Sonnet 5.5 at medium ships, fixing a red CI's format and lint alone, and runs `/np-carry`'s
main session. Every session and agent names
its effort. A scoped item goes to a Sonnet 5.5 sub-agent; Haiku 5.5 takes only mechanical, repetitive
work that is fully specified and needs under 100k tokens of context.

**Code review reports** go to `docs/code_reviews/CODE_REVIEW_NNN.md`, with NNN one above the highest
present.

**Open items** are a deferral to a later package, a doubt only the author can settle, or a finding
whose fix is more than a small edit: an item that outlives the session that found it. Each is a
`REV-nn` row in `docs/project/review-findings.md` with a section in `review-items.md`, until the
commit that resolves it sets it `fixed` (§8.4.6). A small finding, a doubt among them whose fix moves
no ruling, is fixed in the session that finds it and gets no row; a review, a ship and a chore are not
done until each is fixed (§8.2.58 BH1). A PR body is never the only record of an open item.

## Git

- Use conventional commits (`feat:`, `fix:`, `test:`, `docs:`, `chore:`). Name the identifier in the
  body (`VER-03`).
- A version is a git tag, never a number in `pyproject.toml` or the package (§2.7). The procedure is
  in `CONTRIBUTING.md`, *Versions and releases*.
- `main` keeps a linear history. Rebase a branch on `main`, never merge `main` into it, and push a
  rebased branch with `--force-with-lease` (`.claude/workflow/core.md`, *Gate and push*).

## Durable learnings

Write a durable fact as a concept in the relevant `knowledge/` directory, or into an existing one,
with its source:

- Mark a claim `[tested: <test>]`, naming a test in scope, or `[verified]`, with a source footnote.
- List the concept in the directory's `index.md`.
- Add a line to `knowledge/log.md`.

The procedure is `knowledge/00-orientation/04-provenance-and-how-to-extend-this.md`. Status and
scope opinions belong in the specification.

## Do NOT

- Import `gmsh` on the default path. It is GPLv2+ and an optional backend only (CON-10, ADR-002).
- Depend on Triangle, MeshPy or TetGen (CON-12).
- Use PyQt, or a front-end dependency under a licence CON-09 does not allow (CON-09).
- Add anything to the end-user path that needs a C++ compiler, a source build or a JIT (CON-07).
- Write the weak forms twice, or put backend-specific constructs in `physics/` (QR-13).
- Hard-code correction coefficients, `ε_protein` or any fitted parameter in Python.
- Add COMSOL import or export (N7), transient solves (N3), 3D (N4) or off-axis analytes (N5). The
  architecture must not preclude them. 3D is solved in Phase 6's benchmarks alone (CON-01's NOTE).

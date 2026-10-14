---
name: steward
description: Repo conventions for driving a nanopnp pull request to green — how CI is shaped, what each failure class means here, and which failures must never be made to pass. Read automatically when a PR event wakes the session; also use when asked to watch, babysit or autofix a nanopnp PR.
---

# Stewarding a nanopnp PR

Conventions, not permissions. This file says how failures are diagnosed **here** and which are
evidence rather than chores.

## The environment

`uv` owns it (`CLAUDE.md`, *Setup*).

The gate is `.claude/hooks/gate.sh run`. Start it with Bash `run_in_background` on the committed
fix and push when it passes: the hook refuses a push of a tree it has not passed, and every fix is
gated in full. `--no-verify` exists and is not for you.

## Bounded wakes

Read live PR state before plans or logs. Keep one compact checkpoint in the PR's Verification
section: base and head SHAs, check-run states, mergeability, last handled review and comment IDs,
last action or blocker, the unchanged-fallback count and the check-in ID. Update it on meaningful
transitions only; an event caused by your own checkpoint edit is not new work.

- A new failure or conflict needs a fix or an explicit diagnostic and handoff; never abandon a
  new red check silently. Reuse the diagnosis of an unchanged, recorded blocker.
- While CI is pending, schedule at most one fallback check-in, starting one hour out and backing off
  to 2, 4, 8, 12 and 24 hours while nothing changes. After six unchanged fallbacks, cancel them
  and tell the user the state and how to resume. Reset the counter only for a new base or head,
  check-run state, conflict or actionable review.
- Stop fallbacks when green and mergeable, merged, closed or handed off; cancel the timer, or make
  a queued wake a no-op. If nothing changed, reload and rerun nothing.
- Once CI is green and the PR mergeable, report once, unsubscribe from the PR and cancel the
  check-in: a merge then wakes no session, and `/wp-ship` resumes the package.
- If subscription or scheduling is unavailable, say so and hand off; never poll in a loop.

Source context for a failure starts with the WP's Execution brief.

## What CI runs

`.github/workflows/ci.yml`, with `UV_LOCKED: "1"` throughout, so a `uv.lock` that no longer matches
`pyproject.toml` fails every job at `uv sync`. pytest runs `-n auto --dist loadfile` with
`OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS` and `MKL_NUM_THREADS` set to 1 (`.knowledge/07` §12), and
NumPy's SIMD dispatch capped at `X86_V3` by `NPY_DISABLE_CPU_FEATURES` (VER-62's reference environment,
`.knowledge/06` §8.1.5), except `tests/tier1/test_gui_widgets.py`. That module runs serially in its own step on Windows and
macOS only, because it waits on a real QtWebEngine page by the wall clock and busy workers starved it
(run 113). On ubuntu it skips itself, because PySide6 does not import there.

- **`changes`** — names the run's mode (`pr`, `main`, `full`, `nightly`) and diffs the whole PR
  (`base...head`), or the push range on `main`, through `.github/scripts/prose-only.sh`. When
  everything is prose, the test jobs skip their steps and report success. On a push to `main` it
  reads the PR head's `ci/tested-tree` status: when the merged tree is the one the PR passed, ubuntu
  runs only the `extended` walks.
- **A pull request** (§7.6, §8.2.10 J4, J10) — ubuntu, 3.14 only. **`lint`** (`ruff check`, `ruff
  format --check`, `mypy src/`); **`docs`**; **`tests (tier1)`** and **`tests (tier2)`**,
  the development selection (no `extended` walks) under branch coverage, split by marker
  (`-m "tier1 and not slow"`, `-m "tier2 and not slow"`); **`coverage`**, which combines the
  shards and runs `diff-cover` at 100 % of the changed `src/nanopnp` lines outside `gui/` (§7.6 NOTE,
  VER-72 f); and **`CI result`**, the one required check, which fails unless
  every one of those succeeded and posts `ci/tested-tree`. Reproduce a shard with `uv run pytest
  -m "tier1 and not slow"` (or `tier2`); the gate does not measure coverage, so reproduce a
  `diff-cover` miss with `--cov=src/nanopnp --cov-branch` and `diff-cover`.
- **`docs`** — VER-45's strict build: `docs/scripts/generate.py`, then `mkdocs build --strict`, on
  **every** push, prose-only ones included, because a broken link or anchor is exactly what a prose
  edit introduces. Reproduce with `uv sync --all-extras --group docs && uv run
  docs/scripts/generate.py && uv run mkdocs build --strict`.
- **`platforms`** — after a merge and nightly: `pytest --extended` on ubuntu, macOS and Windows,
  3.14, and the GUI file serially on the last two. A walk-only or platform-only failure surfaces
  here, on `main`, and is fixed forward in a new PR.
- **`full-matrix`** — `full: true` (a dispatch, or `release.yml` before it builds a tag): the three
  platforms × 3.11 to 3.14, `--extended` (QR-09, CON-13).
- **`nightly`** — 3.11 to 3.13 on the three platforms, dependencies from wheels only, Tier 1;
  `continue-on-error`, recorded, never gated.
- **`bundle`** — **gated**. Windows PyInstaller build of `packaging/nanopnp-probe.spec`, then the
  bundle's own `--selftest` (RSK-13, §8.2.1 A4), after a merge, before a release and nightly, as the
  runner-image drift probe.
- **`tier3`** — nightly, on a dispatch and before a release, `continue-on-error`: recorded, never
  gated (§7.1, §7.6). Without `$NANOPNP_REFERENCE_DATA` every Tier 3 test skips visibly; a skip
  there is missing evidence, not a defect.

The default `pytest` selection is tiers 1 and 2 without the `extended` tests, which CI adds after a merge. Tier 4
gates releases; `-m slow` is measured, never gated. Nothing in the suite reaches the network or
needs a COMSOL licence, so a failure in `ruff`, `mypy` or `pytest` is always a real one — a lint, a
type error, or a tier 1–2 assertion, never an environment excuse.

The steps that do reach the network are `astral-sh/setup-uv`, `uv sync` and the artefact uploads. A
failure there is infrastructure: re-run the job. Read the log and establish which of the two you
have before changing a line — a stale `uv.lock` also fails at `uv sync`, and that one is a real
failure with a real fix.

Reproduce the failing job's exact command locally before changing anything. For a matrix-only
failure, reproduce under that interpreter (`uv run --python 3.11 pytest …`).


## Failure classes

| Symptom | What it is | What to do |
|---|---|---|
| `ruff` | Formatting drift or a real lint | `uv run ruff format .`; fix the code. A `noqa` needs a same-line reason |
| `docs` | A broken link, anchor or nav entry, or a moved generated page | Fix it. Never drop `--strict` or exclude the page |
| `mypy src/` | Strict-mode gap | Annotate; extend `core/typing.py`'s aliases rather than `Any` or a bare `type: ignore` |
| Lockfile out of date | `pyproject.toml` moved without `uv lock` | `uv lock`, commit it |
| `bundle` | A binary dependency defeating packaging (RSK-13) | Root-cause it. Never add `continue-on-error` (§8.2.1 A4) |
| One Python version only | A compatibility gap | Fix across 3.11–3.14; **never** narrow `requires-python` (QR-09) |
| Windows or macOS only | Paths, line endings, thread counts, float repr | `pathlib` everywhere; pin thread counts in the test |
| A tier 1 test | A real regression | Root-cause it |
| `diff-cover` below 100 % | A changed line, or one branch arm, no gated test executes | Write the test that executes and asserts it. `# pragma: no cover - <reason>` only for a line no test on this leg can reach, never to get green (VER-72 f) |
| `gmsh does not import` | The runner lacks the X and GL libraries | Install them (`.knowledge/07` §4); never unset the variable |
| Fails under `-n`, passes serially | Order dependence or leaked state (a global, a patched attribute, a cwd) | Name the state and isolate it. Never drop `-n`, pin a worker or call it a flake |
| A tier 2 analytic benchmark | **Evidence** | Read the next section first |
| VER-62 number stability | The message decides: a recorded mesh or a moved mesh on the reference environment is G10 evidence; an unseen mesh on another leg is a platform deploying a mesh the golden has not seen | Investigate, then revert or rule and re-pin (§8.2.7 G10). For an unseen mesh, fold it in with `tests/tier2/data/merge_number_stability.py --entry` and say so in the PR; never fold a reference-environment record or edit `moved_tolerance` by hand |
| Timeout or OOM | A benchmark outgrew the budget | Reduce the *mesh*, never the assertion; else ask |

## Tier 2 failures are physics evidence

An analytic benchmark localises an error to a single term; a failure is worth more than a green
PR. Never make one pass by weakening it: never slacken a tolerance, `xfail`, skip or delete it,
coarsen the assertion, swap the reference quantity, or re-run until it passes. A tolerance is specified (§7.3); changing one is a
specification amendment arguing why the *reference* was the wrong quantity (§7.3's Henry versus
Smoluchowski amendment is the precedent).

"Flake" is not a diagnosis: the benchmarks are deterministic. Name the mechanism (a thread count,
an ordering, a seed) and fix it. If the physics or discretisation is wrong, stop and report the
failing quantity, its location and what it implies. Diagnosis stays in the main session; a sub-agent
may only read a long log (`ci-log-classifier`).

## Fixes stay in scope

Fix what the failure needs. A behaviour change needs its `SPECIFICATION.md` edit in the same
commit; one that widens the package, adds a dependency or trades off a `CON-`/`QR-` constraint
goes to the user first. The standing constraints are `CLAUDE.md`'s *Do NOT* and the rule files.

## Commits and reporting

Conventional prefix, identifier in the body, gate green before each commit; review findings land
as `fix: close the review gaps in <what>`. Report once per resolved round, naming the failing
check, the cause and the change.

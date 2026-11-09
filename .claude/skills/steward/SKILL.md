---
name: steward
description: Repo conventions for driving a nanopnp pull request to green — how CI is shaped, what each failure class means here, and which failures must never be made to pass. Read automatically when a PR event wakes the session; also use when asked to watch, babysit or autofix a nanopnp PR.
---

# Stewarding a nanopnp PR

These are conventions, not permissions. This file says how to diagnose a failure **here**, and which
failures are evidence rather than chores.

## The environment

`uv` owns it (`CLAUDE.md`, *Setup*).

Gate and push each committed fix in full as the core's *Gate and push* says
(`.claude/workflow/core.md`). `--no-verify` exists. Do not use it.

## Bounded wakes

Read the live PR state before plans or logs. Keep one compact checkpoint in the PR's Verification
section. It holds:

- the base and head SHAs;
- the check-run states and the mergeability;
- the last handled review and comment IDs;
- the last action or blocker;
- the unchanged-fallback count and the check-in ID.

Update it on meaningful transitions only. An event caused by your own checkpoint edit is not new work.

- A new failure or conflict needs a fix, or an explicit diagnosis and handoff. Never abandon a new red
  check silently. Reuse the diagnosis of an unchanged, recorded blocker.
- While CI is pending, schedule at most one fallback check-in. Start one hour out. Back off to 2, 4,
  8, 12 and 24 hours while nothing changes. After six unchanged fallbacks, cancel them and tell the
  user the state and how to resume. Reset the counter only for a new base or head, a new check-run
  state, a conflict or an actionable review.
- Stop the fallbacks when the PR is green and mergeable, merged, closed or handed off. Cancel the
  timer, or make a queued wake a no-op. If nothing changed, reload and rerun nothing.
- When CI is green and the PR mergeable, report once. Then unsubscribe from the PR and cancel the
  check-in. A merge then wakes no session, and `/np-ship` resumes the package.
- If subscription or scheduling is unavailable, say so and hand off. Never poll in a loop.

A failure's source context starts with the WP's Execution brief.

## What CI runs

The workflow is `.github/workflows/ci.yml`. It sets `UV_LOCKED: "1"` throughout, so a `uv.lock` that
no longer matches `pyproject.toml` fails every job at `uv sync`.

pytest runs `-n auto --dist loadfile`. Three settings apply:

- `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS` and `MKL_NUM_THREADS` are 1
  (`knowledge/07-software-stack/12-the-suites-blas-threads-buy-nothing.md`).
- `NPY_DISABLE_CPU_FEATURES` caps NumPy's SIMD dispatch at `X86_V3`. This is VER-62's reference
  environment
  (`knowledge/06-numerics-fem/09-ngsolve-traps-found-by-implementing.md#815-within-one-build-a-deployed-walks-quantities-repeat-bit-for-bit`).
- `tests/tier1/test_gui_widgets.py` is the exception. It runs serially in its own step, on Windows and
  macOS only. It waits on a real QtWebEngine page by the wall clock, and busy workers starved it
  (run 113). On ubuntu it skips itself, because PySide6 does not import there.

The jobs:

- **`changes`** names the run's mode (`pr`, `main`, `full`, `nightly`). It diffs the whole PR
  (`base...head`), or the push range on `main`, through `.github/scripts/prose-only.sh`. When
  everything is prose, the test jobs skip their steps and report success.
- **A pull request** (§7.6, §8.2.10 J4, §8.2.13 N4) runs on ubuntu, 3.14 only. Its jobs are:
    - **`lint`**: `ruff check`, `ruff format --check`, `mypy src/`.
    - **`docs`**.
    - **`tests (tier1)`** and **`tests (tier2)`**. They run the per-push selection
      (`CLAUDE.md`, *Commands*), split by marker (`-m "tier1 and not slow"`, `-m "tier2 and not slow"`).
    - **`CI result`**, the one required check. It fails unless every job above succeeded.

  Reproduce a shard with `uv run pytest -m "tier1 and not slow"` (or `tier2`). There is no coverage
  job (§8.2.13 N2).
- **`docs`** is VER-45's strict build: `docs/scripts/generate.py`, then `mkdocs build --strict`. It
  runs on **every** push, prose-only ones included, because a prose edit is what breaks a link or
  anchor. Reproduce it with
  `uv sync --all-extras --group docs && uv run docs/scripts/generate.py && uv run mkdocs build --strict`.
- **`platforms`** runs after a merge. It runs the per-push selection on ubuntu, macOS and Windows,
  3.14, and the GUI file serially on the last two. A platform-only failure shows up here, on `main`.
  Fix it forward in a new PR.
- **`full-matrix`** runs when `full: true` (a dispatch, or `release.yml` before it builds a tag). It
  covers the three platforms × 3.11 to 3.14, with `--nightly`: the whole of Tiers 1 and 2 (QR-09,
  CON-13).
- **`nightly`** is the scheduled run. It has two parts:
    - every Tier 1 and Tier 2 test outside the per-push selection, under `--nightly`, on the three
      platforms (§8.2.13 N4);
    - Tier 1 on 3.11 to 3.13 on the three platforms, with dependencies from wheels only.

  A failure of the first part, or of `bundle`, opens an issue and blocks nothing; the 3.11–3.13 legs
  and `tier3` are recorded in the run only. Fix it forward in a PR.
- **`bundle`** is **gated**. It builds the Windows PyInstaller bundle of `packaging/nanopnp-probe.spec`,
  then runs the bundle's own `--selftest` (RSK-13, §8.2.1 A4). It runs after a merge, before a release
  and nightly, as the runner-image drift probe.
- **`tier3`** runs nightly, on a dispatch and before a release, with `continue-on-error`. It is
  recorded and never gated (§7.1, §7.6). Without `$NANOPNP_REFERENCE_DATA`, every Tier 3 test skips
  visibly. That skip is missing evidence, not a defect.

The default `pytest` selection is tiers 1 and 2 without the `nightly` and without the `slow` tests,
both of which the nightly run adds. Tier 4 gates releases. `-m slow` is measured and never gated.
Nothing in the suite reaches the network or needs a COMSOL licence. A failure in `ruff`, `mypy` or
`pytest` is therefore always a real one: a lint, a type error or a tier 1–2 assertion, never an
environment excuse.

These steps do reach the network: `actions/checkout`, `astral-sh/setup-uv`, the apt cache action
(`awalsh128/cache-apt-pkgs-action`), `uv sync`, `playwright install` and the artefact uploads. A
failure there is infrastructure, so re-run the job. Read the log first, and establish which of the
two you have before you change a line. A stale `uv.lock` also fails at `uv sync`, and that one is a real
failure with a real fix.

Before you change anything, reproduce the failing job's exact command locally. For a failure in one
matrix leg, reproduce it under that interpreter (`uv run --python 3.11 pytest …`).

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
| A `nightly` run | A test outside the per-push selection failed (a walk, a golden or a platform); the run opened an issue and blocks nothing | Reproduce it locally with `uv run pytest --nightly <node id>`, root-cause it and fix forward in a PR, under the Tier 2 rules below |
| `gmsh does not import` | The runner lacks the X and GL libraries | Install them (`knowledge/07-software-stack/04-geometry-meshing-and-io.md`); never unset the variable |
| Fails under `-n`, passes serially | Order dependence or leaked state (a global, a patched attribute, a cwd) | Name the state and isolate it. Never drop `-n`, pin a worker or call it a flake |
| A tier 2 analytic benchmark | **Evidence** | Read the next section first |
| VER-62 number stability | The message decides: a recorded mesh or a moved mesh on the reference environment is evidence of a moved physics number (§8.2.7 G10); an unseen mesh on another leg is a platform deploying a mesh the golden has not seen | Investigate, then revert or rule and re-pin (§8.2.7 G10). For an unseen mesh, fold it in with `tests/tier2/data/merge_number_stability.py --entry` and say so in the PR; never fold a reference-environment record or edit `moved_tolerance` by hand |
| Timeout or OOM | A benchmark outgrew the budget | Reduce the *mesh*, never the assertion; else ask |

## Tier 2 failures are physics evidence

An analytic benchmark localises an error to a single term. A failure is worth more than a green PR.
Never make one pass by weakening it. That bans each of these:

- slackening a tolerance;
- `xfail`, skip or delete;
- coarsening the assertion;
- swapping the reference quantity;
- re-running until it passes.

A tolerance is specified (§7.3). Changing one is a specification amendment, and it must argue why the
*reference* was the wrong quantity. §7.3's Henry versus Smoluchowski amendment is the precedent.

"Flake" is not a diagnosis, because the benchmarks are deterministic. Name the mechanism (a thread
count, an ordering, a seed) and fix it. If the physics or the discretisation is wrong, stop and report
the failing quantity, its location and what it implies. Diagnosis stays in the main session. A
sub-agent may only read a long log (`ci-log-classifier`).

## Fixes stay in scope

Fix what the failure needs. A behaviour change needs its `SPECIFICATION.md` edit in the same commit.
A change that widens the package, adds a dependency or trades off a `CON-`/`QR-` constraint goes to
the user first. The standing constraints are `CLAUDE.md`'s *Do NOT* and the rule files.

## Commits and reporting

Use a conventional prefix, name the identifier in the body, and gate green before each commit. Review
findings land as `fix: close the review gaps in <what>`. Report once per resolved round. Name the
failing check, the cause and the change.

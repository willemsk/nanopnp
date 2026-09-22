---
name: steward
description: Repo conventions for driving a nanopnp pull request to green — how CI is shaped, what each failure class means here, and which failures must never be made to pass. Read automatically when a PR event wakes the session; also use when asked to watch, babysit or autofix a nanopnp PR.
---

# Stewarding a nanopnp PR

Conventions, not permissions. Everything the session's own PR rules state as a *never* stays a
never; this file says how failures are diagnosed **in this repository** and which of them are
evidence rather than chores.

## The environment

`uv` owns it. `uv sync --all-extras --frozen` to prepare, `uv run <anything>` to execute. No `pip`,
no activated venv, no bare `python` or `pytest` — a fix validated outside `uv run` is not validated.
The `SessionStart` hook syncs automatically in web sessions.

The gate is `.claude/hooks/gate.sh run` (the CLAUDE.md chain plus `uv lock --check`). The hook
runs the same script before every commit and skips a working tree that has already passed, so run
it once on the finished fix and let the commit reuse the pass. `--no-verify` exists and is not for you.

## Bounded wakes

Read live PR state before loading plans or logs. Keep one compact checkpoint in the PR's
Verification section: base/head SHAs, check-run IDs and states/conclusions, mergeability, last
handled review/comment IDs, last action or blocker, consecutive unchanged fallback count, and
scheduled check-in ID if any. Update it on meaningful transitions or fallback checks, not on every
duplicate event. An event caused only by your checkpoint edit is not new work.

- A new failure or conflict needs a fix or an explicit diagnostic and handoff. Reuse the diagnosis
  of an unchanged, already-recorded blocker; do not reopen logs or repeat the same comment. Never
  silently abandon a new red check. Physics/scope blockers follow the rules below.
- While CI is pending, schedule at most one fallback check-in. Start one hour out; consecutive
  unchanged fallbacks back off to 2, 4, 8, 12 and 24 hours. After six unchanged fallback checks,
  cancel further fallbacks and tell the user the remaining state and how to resume the watch.
  Reset the counter only for a new base/head, check-run/state, conflict or actionable review,
  not for duplicate webhooks, timestamps or your own checkpoint comments.
- Stop fallbacks when green and mergeable, merged/closed, or handed off for a human decision.
  Cancel the timer where supported; otherwise an already queued wake checks the checkpoint and
  does no work unless live state has meaningfully changed. New events can restart attention.
- If nothing changed, do not reload the specification/history or rerun a review/gate. Advance
  only the fallback counter/timer when a fallback fired; duplicate events must not add timers.
- If subscription or scheduling is unavailable, say so and hand off the current status. Do not
  emulate a watcher with a polling shell loop or claim that a nonexistent timer will wake you.

When a failure needs source context, start with the requested WP's Execution brief and cited
sections. Historical phase summaries and unrelated knowledge files are not routine wake context.

## What CI runs

`.github/workflows/ci.yml`, with `UV_LOCKED: "1"` throughout, so a `uv.lock` that no longer matches
`pyproject.toml` fails every job at `uv sync`:

- **`check`** — ubuntu, 3.12: `ruff check`, `ruff format --check`, `mypy src/`, `pytest --cov`.
- **`test-matrix`** — `pytest` on ubuntu × 3.10–3.14, plus 3.12 on windows and macOS (QR-09, CON-13).
- **`bundle`** — **gated**. Windows PyInstaller build of `packaging/nanopnp-probe.spec`, then the
  bundle's own `--selftest` (RSK-13, §8.2.1 A4).
- **`tier3`** — nightly and on `workflow_dispatch` only, `continue-on-error`: recorded, never gated
  (§7.1, §7.6). Without `$NANOPNP_REFERENCE_DATA` every Tier 3 test skips visibly; a skip there is
  missing evidence, not a defect.

The default `pytest` selection is tiers 1 and 2. Tier 4 gates releases; `-m slow` is measured, never
gated. Nothing in the suite reaches the network or needs a COMSOL licence, so a failure in `ruff`,
`mypy` or `pytest` is always a real one — a lint, a type error, or a tier 1–2 assertion, never an
environment excuse.

The steps that do reach the network are `astral-sh/setup-uv`, `uv sync` and the artefact uploads. A
failure there is infrastructure: re-run the job. Read the log and establish which of the two you
have before changing a line — a stale `uv.lock` also fails at `uv sync`, and that one is a real
failure with a real fix.

Reproduce the failing job's exact command locally before changing anything. For a matrix-only
failure, reproduce under that interpreter (`uv run --python 3.10 pytest …`).

## Failure classes

| Symptom | What it is | What to do |
|---|---|---|
| `ruff format --check` | Formatting drift | `uv run ruff format .` |
| `ruff check` | A real lint | Fix the code. A `noqa` needs a reason on the same line and is a last resort |
| `mypy src/` | Strict-mode gap | Annotate properly. NGSolve ships no type information: extend the protocol aliases in `core/typing.py` rather than reaching for `Any` or a bare `type: ignore` |
| Lockfile out of date | `pyproject.toml` moved without `uv lock` | `uv lock`, commit it |
| `bundle` build or `--selftest` | A binary dependency defeating desktop packaging — RSK-13's detector doing its job | Root-cause it on the spec or the dependency. Never add `continue-on-error`: demotion is recorded with the failure that caused it (ci.yml comment, §8.2.1 A4), and that is the author's call |
| One Python version only | A compatibility gap (3.10 syntax floors, 3.13/3.14 stdlib moves) | Fix compatibly across 3.10–3.14. **Never** narrow `requires-python` or drop a matrix entry — QR-09 is a requirement |
| Windows or macOS only | Path handling, line endings, thread counts, float repr | `pathlib` everywhere, never `os.path`; pin thread counts in the test, not in the library |
| A tier 1 property test | A real regression in a unit | Root-cause it. These are seconds long and localise precisely |
| A tier 2 analytic benchmark | **Evidence.** See below | Read the next section before touching it |
| Timeout or OOM in a job | A benchmark outgrew the gate budget | Reduce the *mesh*, never the assertion; if the test genuinely cannot gate, that is a scope decision — ask |

## Tier 2 failures are physics evidence

An analytic benchmark exists to localise an error to a single term. When one fails, the finding is
"the model disagrees with a closed-form solution", and that is worth more than a green PR.

Never make one pass by weakening it. Specifically: never slacken a tolerance, never `xfail`, `skip`
or delete it, never coarsen the assertion, never swap the reference quantity for an easier one, and
never quietly re-run until it passes. A tolerance in this project is specified (§7.3) — changing one
is a specification amendment with an argument attached, and the amendment has to say why the
*reference* was the wrong quantity, not why the number was inconvenient. §7.3's Henry versus
Smoluchowski amendment is the only worked precedent and it took a derivation.

"Flake" is not available as a diagnosis here. The benchmarks are deterministic: same mesh, same
solver, same answer. Claiming a flake means naming the mechanism — a thread count, an ordering, a
seed — and fixing that mechanism.

If the failure means the physics or the discretisation is wrong, stop and report it to the user with
the failing quantity, its location, and what you think it implies. That is the outcome the whole
verification strategy is built to produce; do not paper over it to get a green tick.

## Fixes stay in scope

Fix what the failure needs and no more. A fix that changes what the software does needs the matching
`SPECIFICATION.md` edit in the same commit. A fix that would widen the work package, add a
dependency, or trade off a `CON-`/`QR-` constraint goes to the user first.

The standing constraints a hurried fix tends to break: corrections are data in
`data/corrections/*.yaml`, never coefficients in Python; deviations from the validated model go
behind a flag, default off, and into the FR-25 manifest; `ngsolve`, `netgen` and `numpy` are
imported inside the function that uses them and nothing else is deferred; no `gmsh` on the default
path (CON-10); PySide6 never PyQt (CON-09); nothing on the end-user path that needs a compiler
(CON-07); no `import *`, no `print()`, no `os.path`.

## Commits and reporting

Conventional prefix, requirement identifier in the body, gate green before each commit. Review
findings land as commits on the PR branch — `fix: close the review gaps in <what>` — not as replies
describing what could be done.

Report once per resolved round, not once per fix, and refresh the PR's status checklist so the
thread shows live state. A comment that only says "fixed" is noise; one that names the failing
check, the cause and the change is the record.

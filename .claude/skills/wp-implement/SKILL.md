---
name: wp-implement
description: Implement a planned nanopnp work package from its docs/plans/ file, keeping the specification, knowledge base and plan in step. Use when the user asks to implement or build a work package, start work on WP7, execute the plan, or invokes /wp-implement.
---

# Implement a work package

Step 2 of the implementation workflow. The plan under `docs/plans/` is the brief; this skill
executes it and records what the execution taught. It does not chain into `/wp-ship` — that is a
separate invocation, by design (see **Finishing** below).

## Load the brief

1. `docs/plans/wp<n>-*.md` in full — the decisions table is binding. A decision it took is not
   re-litigated mid-implementation; a decision it got *wrong* is corrected in the specification and
   annotated in the plan (see **Keeping the record straight** below).
2. `.knowledge/00-index.md`, then the files the package touches.
3. The `SPECIFICATION.md` sections and Appendix A rows the plan cites.
4. `uv sync --all-extras --frozen` if `.venv` is not already current (the `SessionStart` hook does
   this in web sessions).
5. Check the branch. If it is `main`, stop and ask before writing anything — `wp-ship` §1 refuses to
   ship from `main`, and by the time it says so the whole package has already been committed there.

Then build a task list from the plan's work items, in dependency order, and work it. Physics and
numerics decisions stay with the orchestrator on Opus; delegate surveys, mechanical edits and long
test runs per `.claude/model-policy.md`, saying which model you chose and why.

## How the work lands

**One commit per coherent unit**, not one per file and not one at the end. Conventional prefix,
requirement identifier in the body (`VER-19`, `NUM-28`). The gate hook runs the whole gate before
each commit and refuses it with the failing output, so a commit is proof the tree was green.

A unit is done when its test exists and passes, not when the code compiles. Name every test for the
requirement it discharges — `test_ver19_stokes_drag_against_six_pi_eta_a_u` — and place it in the
tier directory that decides its marker. An analytic test that localises the error to a single term
beats a whole-model comparison that localises nothing; write the localising one first.

Watch for the failure modes `CLAUDE.md` names, because each of them passes a test suite:

- a tolerance met for the wrong reason — a benchmark whose far field makes it measure nothing;
- two routes that agree because they share a mistake, rather than because the answer is right;
- a quantity that is a function of a discretisation choice (a band, a mesh, a `w`) rather than of
  the physics;
- a "flake" that is a real dependence on threading, ordering or seed.

When one of these is even possible, assert against a third route or an oracle rather than reasoning
that it is fine.

## Keeping the record straight

Implementation that changes what the finished software does changes `SPECIFICATION.md` **in the same
commit** — the identifier, the NOTE, the amended tolerance, with the derivation. A tolerance is
never slackened to accommodate a number: either the number is wrong, or the specified reference was
the wrong quantity and the amendment says so in those terms (§7.3's Henry/Smoluchowski amendment is
the worked example).

Three records move together as the work lands:

| Record | Gets |
|---|---|
| `SPECIFICATION.md` | Amendments, NOTEs, argued tolerances — normative changes only |
| `.knowledge/<file>.md` | Durable findings, marked **[tested]** (verified by running code) or **[verified]** (verified by arithmetic), with the source. No status, no task lists, no scope opinions |
| `docs/plans/wp<n>-*.md` | `> **Outcome — <what changed>.**` blockquotes in place, wherever a prediction was wrong or incomplete, plus the measured numbers the plan asked for |

The phase plan's `### WP<n>` section gains the delivered summary — what was built, what was built
*beyond* the plan, which identifiers are discharged, and the findings the next package inherits —
when the package is finished. That section, not the WP plan, is the authoritative record.

Both plans' **Status** lines move with that summary, and they are easy to forget because nothing
fails when you do. `.claude/hooks/session-start.sh` prints the first `**Status: …**` span of every
`docs/plans/*.md` as the opening context of every session, so a stale one tells each future session
that finished work is unstarted:

- the WP plan's own — `**Status: planned, not started**` → `**Status: delivered, <date>.**`, keeping
  the sentence that follows it;
- the phase plan's roll-up — the `WP<n>` moves from the planned list to the delivered one.

## Measurements are deliverables

Timings, convergence rates, minimum damping factors, route-agreement figures, memory at the
reference mesh size: run them, record the number with the mesh and the configuration it came from,
and put it where the plan asked. A rate quoted without the meshes it was measured on is not
evidence. Record the stabilisation mode with every number.

## Finishing

Before handing off, confirm every one of these yourself:

- every work item in the plan is done, or explicitly deferred with a reason written into the plan;
- every `VER-`/`VAL-` identifier the plan claimed has a test named for it, and it passes;
- `uv run ruff check . && uv run ruff format --check . && uv run mypy src/ && uv run pytest` is
  green on the current tree;
- the specification, the knowledge base and the plan's Outcome annotations are all committed;
- both **Status** lines are updated;
- `git status` is clean, and the branch is pushed (`git push -u origin <branch>`) — `wp-ship` §2
  would push it, but that is a later session, possibly on a container this one's commits never
  reach.

Then stop and report to the user: the work package delivered, the identifiers discharged, and that
it is ready to ship. Do not invoke `/wp-ship` yourself and do not open the PR by hand — this session
carries the physics reasoning behind every decision the implementation made, and `wp-ship`'s review
pass (§4 of that skill) is meant to run from a session that does not, so it catches what this one
might rationalise past rather than confirm. The user starts `/wp-ship` when they are ready.

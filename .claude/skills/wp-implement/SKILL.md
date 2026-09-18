---
name: wp-implement
description: Implement a planned nanopnp work package, keep the specification, knowledge base and plan in step, then gate, push and open its PR. Use when the user asks to implement or build a work package, start work on WP7, execute the plan, or invokes /wp-implement.
---

# Implement a work package

Step 2 of the implementation workflow. The plan under `docs/plans/` is the brief; this skill
executes it, records what the execution taught, and opens the PR after validation. It does not chain
into `/wp-ship`: independent review and CI stewardship remain a separate invocation (see **Finishing**).

## Load the brief

1. Read `docs/plans/current.md` and the requested WP's Execution brief. Its current decisions are
  binding, subject to the specification. Read each work item's linked Design sections before
  implementing it; do not reload unrelated delivered packages. For legacy plans, read Decisions,
  Work items, Verification and their correcting Outcomes first, then the relevant Design sections.
  Correct a wrong decision in the brief and, if needed, the specification, preserving the original
  argument as labelled history (see **Keeping the record straight** below).
2. `.knowledge/00-index.md`, then the relevant sections of the files the package touches.
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
| `docs/plans/wp<n>-*.md` | Current Execution brief and concise `> **Outcome — <what changed>.**` annotations linking the evidence; measured numbers the plan requested, unless already recorded at a linked authoritative location |

The phase plan's `### WP<n>` section gains a short delivered summary (target 150 words): scope,
identifiers, live inherited constraints and links to evidence. Do not repeat derivations or measurement
tables from the specification, knowledge base or WP plan. Preserve existing historical summaries.
Update `docs/plans/current.md` in place with the current position, next package and live dependency
links (target 800 words). It is navigation, not another source of requirements.

Both plans' **Status** lines move with that summary. Startup points to `docs/plans/current.md`
without loading historical statuses; keep that brief consistent with both plans:

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
- both **Status** lines and `docs/plans/current.md` are updated;
- `git status` is clean, and the branch is pushed (`git push -u origin <branch>`).

Then open or reuse the branch's PR against `main`, without asking again. Follow only the PR lookup
and title/body contract in `wp-ship` §3; do not invoke that skill. On a new PR, state under
**Verification** that independent review is pending `/wp-ship`, alongside the local gate result.
When resuming an existing PR, preserve its review evidence and human edits; do not reset its state
or create a duplicate. If PR creation is blocked by authentication or unavailable tooling, report
the blocker and pushed branch rather than claiming a PR exists.

Stop and report the PR link, identifiers discharged, and readiness for `/wp-ship`. Do not start the
review pass, subscribe to PR activity, or schedule CI monitoring from this session. It carries the
physics reasoning behind the implementation; `wp-ship`'s independent review (§4) should run from a
fresh session so it can challenge those decisions. The user starts `/wp-ship` when ready.

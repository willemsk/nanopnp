---
name: wp-implement
description: Implement a planned nanopnp work package, keep the specification, knowledge base and plan in step, then gate, push and open its PR. Use when the user asks to implement or build a work package, start work on WP7, execute the plan, or invokes /wp-implement.
---

# Implement a work package

Step 2 of the implementation workflow: execute the plan under `docs/plans/`, record what the
execution taught, and open the PR. It does not chain into `/wp-ship`.

## Load the brief

1. Read `docs/plans/current.md` and the requested WP's Execution brief. Its decisions are binding,
   subject to the specification. Correct a wrong decision in the brief (and the specification).
2. `.knowledge/index.md`, then the sections of the files the package touches.
3. The `SPECIFICATION.md` sections and Appendix A rows the plan cites; `.claude/scripts/clause.py
   <ID>` prints one with its NOTEs and rulings.
4. `uv sync --all-extras --frozen` if `.venv` is not current.
5. Check the branch. On `main`, switch to the development branch this session was given; if none
   was given, stop and ask before writing anything.

Build a task list from the work items, starting at the first unticked one. Models (`CLAUDE.md`): Haiku
for an easy mechanical item, Sonnet by default, Opus only after Sonnet has failed on the item. At a
compaction checkpoint of the plan, compact the context; the next item resumes from the plan and
`git log`.

**Fresh worker per item** (§8.2.11 L9; a trial, WP45 only unless the author adopts it): when the
plan says so, hand each item to a new sub-agent (Agent tool, the model above) with the item's text,
its done-criterion, the clauses it cites and this skill's *How the work lands*. It edits, runs the
item's checks, commits and ticks, and replies with the commit and the checks it ran, nothing more.
Re-run the item's check yourself before the next item; on a failure, revert and hand the item to
a fresh worker once, then the next model. Do not read the worker's files into this session.

## How the work lands

**One commit per work item**, done when the tests its done-criterion names pass. Conventional
prefix, requirement identifier in the body. Tick each item `[x] <short sha>` in that commit or the
next, so a later session resumes from the first unticked one. The gate hook refuses a failing commit and remembers a pass, so a
gated tree can be split into several commits.

Write each item's tests with the item, from the plan's *Verification* rows; the plan commits none.
Name each test for the requirement it discharges, in the tier directory that decides its marker.
Write the analytic test that localises an error to one term first. Where a tolerance could be met
for the wrong reason, or two routes could share a mistake, assert against a third route.

## Keeping the record straight

A change to what the finished software does changes `SPECIFICATION.md` **in the same commit**: the
identifier, the NOTE, the amended tolerance, with the derivation. A tolerance is never slackened to
fit a number (the steward's *Tier 2 failures* section says why).

State every rule in the present tense; history lives in the log, `CHANGELOG.md`, plans and §8.2.

| Record | Gets |
|---|---|
| `SPECIFICATION.md` | Amendments, NOTEs, argued tolerances: normative changes only |
| `.knowledge/<file>.md` | Durable findings marked **[tested]** or **[verified]**, with the source (see `.knowledge/index.md`) |
| `docs/plans/wp<n>-*.md` | The current Execution brief and concise `> **Outcome — <what changed>.**` annotations linking the evidence; measured numbers the plan requested |
| `docs/project/review-findings.md` | A `REV-nn` row, with its section in `review-items.md`, for every item left open: a deferral, a known limitation, a question for the author (§8.2.8 H12). A row the package resolves is set `fixed` |

The phase plan's `### WP<n>` section gains a delivered summary (target 150 words): scope,
identifiers, live inherited constraints, links to evidence. Update `docs/plans/current.md` in place
(its word target is in its *Handoff Rules*). Both plans' **Status** lines move with the summary:
the WP plan's becomes `**Status: delivered, <date>.**` and the phase plan's roll-up moves the
`WP<n>` to the delivered list.

## Measurements are deliverables

Timings, convergence rates, minimum damping, route-agreement figures, memory at the reference mesh
size: run them, record the number with the mesh, configuration and stabilisation mode it came from,
and put it where the plan asked.

## Finishing

Confirm yourself:

- every work item is done and ticked, or deferred with a reason in the plan and a `REV-nn` row;
- every `VER-`/`VAL-` the plan claimed has a passing test named for it;
- the specification, knowledge base and Outcome annotations are committed, both **Status** lines
  and `current.md` are updated, and `CHANGELOG.md` has the package's section under
  `vX.Y.Z-alpha.N` (`CONTRIBUTING.md`, *Versions and releases*, also covers the close package);
- `git status` is clean. Start `.claude/hooks/gate.sh run` with Bash `run_in_background` and push
  (`git push -u origin <branch>`) when it passes; the push guard refuses a tree it has not passed.

Then open or reuse the branch's PR against `main` without asking again, by the lookup and
title/body contract of `wp-ship` §3 (do not invoke that skill). A new PR states under
**Verification** that review is pending `/wp-ship`. If creation is blocked, report the blocker and
the pushed branch.

The PR body opens with `## In brief`, for a reader who does not code: at most 250 words, no
backticks or identifiers. **What changes** and why; **Cost**; **What could go wrong**, each risk
and how it would be noticed; **Your call**, each decision the author owns with *Recommendation:*
and one reason.

Once the PR exists, write `PR: [#<n>](<url>), branch <head>` under the title of
`docs/plans/wp<n>-*.md`, commit it (`docs: record WP<n>'s PR`), start `.claude/hooks/gate.sh run`
again in the background (the commit is a new tree, and the push guard names the tree) and push when it
passes; `/wp-ship` finds the package from this line (`wp-ship` §0).

Stop and report the PR link, the identifiers discharged, the tag the last commit takes after the
merge, and readiness for `/wp-ship`. Do not start the review or CI monitoring: the review should
come from a fresh session that did not make these decisions.

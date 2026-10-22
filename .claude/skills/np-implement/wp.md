# Implement a work package

`/np-implement [wp <n>]`. Step 2 of the implementation workflow: execute the plan under
`docs/plans/`, record what the execution taught, and open the PR. It does not chain into `/np-ship`.

## Load the brief

1. Read `docs/plans/current.md` and the requested WP's Execution brief. Its decisions are binding,
   subject to the specification. Correct a wrong decision in the brief (and the specification).
   Its `### Grounding` is what the code held when the plan was written. A fact that has since gone
   wrong is corrected in the plan, in the commit of the item that found it. If the correction
   changes a decision, it is a wrong decision, handled as above.
2. `knowledge/index.md`, then the sections of the files the package touches.
3. The `SPECIFICATION.md` sections and Appendix A rows the plan cites; `.claude/scripts/clause.py
   <ID>` prints one with its NOTEs and rulings.

Build a task list from the work items, starting at the first unticked one. A
**compaction checkpoint** is a work item (§8.2.16 R11). Tick it in its own commit, run the push gate
and push as in *Finishing*. Then print a prompt in a `text` block: `/compact`, followed by the
package, the next item's number, any values later items need that are not in the plan or
`git log`, and "resume with `/np-implement`". End the turn there. The author compacts and resumes,
and the next item starts from the plan and `git log`.

**Sub-agent items** (§8.2.16 R6, R11): hand each item whose **Executor** names a sub-agent to a new
one of that type and model (Agent tool), with the item's text, its done-criterion, the plan's
*Implementation details* for it, the clauses it cites and this file's *How the work lands*. Items
marked `main` stay in this session. It edits, runs the
item's checks, commits and ticks, and replies with the commit and the checks it ran, nothing more.
Re-run the item's check yourself before the next item; on a failure, revert and hand the item to
a fresh worker once, then the next model. Do not read the worker's files into this session.

## How the work lands

**One commit per work item**, done when the tests its done-criterion names pass. Conventional
prefix, requirement identifier in the body. Tick each item `[x] <short sha>` in that commit or the
next, so a later session resumes from the first unticked one. The gate hook refuses a failing commit and remembers a pass, so a
gated tree can be split into several commits.

Write each item's tests with the item, from the plan's *Verification* rows; the plan commits none.
Write a test only inside the test scope (`SPECIFICATION.md` §8.2.13 N1): physics, numerics, core
mechanisms, the licence and architecture guards, and a thin smoke test per entry point. Name each
test for the silent failure it catches, in the tier directory that decides its marker.
Write the analytic test that localises an error to one term first. Where a tolerance could be met
for the wrong reason, or two routes could share a mistake, assert against a third route.

## Keeping the record straight

The core's *Records* table says what each record gets.

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
- every in-scope `VER-`/`VAL-` the plan claimed has a passing test (N3); each other claimed identifier is checked against the code and the PR says so;
- the specification, knowledge base and Outcome annotations are committed, both **Status** lines
  and `current.md` are updated, and `CHANGELOG.md` has the package's section under
  `vX.Y.Z-alpha.N` (`CONTRIBUTING.md`, *Versions and releases*, also covers the close package);
- gate and push (the core).

Then open or reuse the PR by the core's *PR contract*. A new PR states under
**Verification** that review is pending `/np-ship`. Record its `PR:` line as the core says.

Stop and report the PR link, the identifiers discharged, the tag the last commit takes after the
merge, and readiness for `/np-ship`. Do not start the review or CI monitoring: the review should
come from a fresh session that did not make these decisions.

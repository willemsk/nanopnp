# Implement a work package

`/np-implement [wp <n>]` is step 2 of the implementation workflow. It executes the plan under
`docs/plans/`, records what the execution taught, and opens the PR. It chains into `/np-ship` only when the author sets `NANOPNP_AUTO_SHIP=1` (*Finishing*).

## Load the brief

1. Find the package's PR and branch (the core). Then read the WP's Execution brief.
   - Its decisions are binding, subject to the specification. If a decision is wrong, correct it in the
     brief and in the specification.
   - Its `### Grounding` is what the code held when the plan was written. If a fact is no longer true,
     correct it in the plan, in the commit of the item that found it. If the correction changes a
     decision, the decision is wrong: correct it as above.
2. Read `knowledge/index.md`, then the sections of the files that the package touches.
3. Read the `SPECIFICATION.md` sections and Appendix A rows that the plan cites (`clause.py`, the core).

Make a task list from the work items. Start at the first unticked item.

A **compaction checkpoint** is a work item (§8.2.16 R11):

1. Tick it in its own commit. Gate and push as in *Finishing*.
2. Write a prompt. It holds `/compact`, the package, the number of the next item, the values that later
   items need and that the plan and `git log` do not hold, and "resume with `/np-implement wp <n>`".
   Pipe it to `.claude/hooks/checkpoint.sh save implement <plan> <n>`, and print it in a `text` block.
3. If that printed `off`, end the turn. The author compacts and resumes. The next item starts from the
   plan and `git log`.
4. If it printed `on`, the author set `NANOPNP_AUTO_CHECKPOINT=1`: go on with the next item in this
   turn. No hook can compact, so Claude Code's own compaction comes when the context fills. The hooks
   give the saved prompt to that compaction as its instructions and to the context after it, and the
   Stop hook blocks once a turn that ends while items remain. Nothing is left to the author unless a
   question stops the turn.

**Sub-agent items** (§8.2.16 R6, R11). If an item's **Executor** names a sub-agent, give the item to a
new agent of that type and model (Agent tool). Give it:

- the item's text and its done-criterion;
- the plan's *Implementation details* for the item;
- the clauses the item cites;
- this file's *How the work lands*.

Items marked `main` stay in this session.

- The worker edits, runs the item's checks and commits. It replies with the commit and the checks it
  ran, and nothing more. This session ticks the item.
- Before the next item, run the item's check again yourself. If it fails, revert the commit and give
  the item to a new worker once, then to the next model.
- Do not read the worker's files into this session.

## How the work lands

**One commit per work item.** An item is done when the tests of its done-criterion pass. Use a
conventional prefix, and put the requirement identifier in the body. Tick each item
`[x] <short sha>` in the next commit. A checkpoint ticks itself and the item before it. A later
session then resumes from the first unticked item. The gate hook refuses a failing commit and
remembers a pass, so you can split a gated tree into several commits.

An item that changes a screen (`src/nanopnp/gui/`, the front end, `docs/design/`) runs `/np-gui render
<target>` and reads each changed screen before its commit. A page error or a failed check stops the
item.

Write the tests of an item with the item, from the plan's *Verification* rows. The plan commits no
tests. Each test is in the test scope and is named as `CLAUDE.md`'s *Testing* says (§8.2.13 N1).

- Write first the analytic test that localises an error to one term.
- If a tolerance can pass for the wrong reason, or two routes can share a mistake, assert against a
  third route.

## Keeping the record straight

The core's *Records* table says what each record gets.

- The phase plan's `### WP<n>` section gets a delivered summary (target 150 words): scope,
  identifiers, live inherited constraints and links to evidence.
- Update `docs/plans/current.md` in place. With two lanes open, update only your lane's position line
  (the core's *Two lanes*). Its word target is in its *Handoff Rules*.
- Change both plans' **Status** lines with the summary. The WP plan's line becomes
  `**Status: delivered, <date>.**`. The phase plan's roll-up moves `WP<n>` to the delivered list.

## Measurements are deliverables

Run the measurements the plan asks for: timings, convergence rates, minimum damping, route-agreement
figures, memory at the reference mesh size. Record each number with its mesh, configuration and
stabilisation mode, where the plan asks.

## Finishing

Confirm these yourself:

- Each work item is done and ticked, or deferred with a reason in the plan and a `REV-nn` row.
- Each in-scope `VER-`/`VAL-` that the plan claims has a passing test (N3). Check each other claimed
  identifier against the code, and say so in the PR.
- The specification, the knowledge base and the Outcome annotations are committed.
- Both **Status** lines and `current.md` are updated.
- `CHANGELOG.md` has the package's section under `vX.Y.Z-alpha.N` (`CONTRIBUTING.md`, *Versions and
  releases*; this also covers the close package). A package that merges before its previous phase's
  release writes its entry under the next release instead, and takes no tag (the core's *Two lanes*).
- Gate and push (the core).

Then open or reuse the PR by the core's *PR contract*. A new PR states under **Verification** that the
review waits for `/np-ship`.

Report the PR link, the identifiers discharged, the tag that the last commit gets after the merge
(or that it gets none), and that the package is ready for `/np-ship`. Do not start the review or
monitor CI in this turn. Then pause (§8.2.33 AI4):

1. Write a prompt. It holds `/compact`, the package, the PR, its head, each decision this session took
   that the plan does not hold, the values the review needs that the plan and `git log` do not hold,
   and "resume with `/np-ship wp <n>`". Pipe it to `.claude/hooks/checkpoint.sh save ship <plan> <n>`,
   and print it in a `text` block.
2. If that printed `off`, end the turn. The author compacts and resumes here, or starts `/np-ship` in a
   fresh session.
3. If it printed `on`, the author set `NANOPNP_AUTO_SHIP=1`: run the `np-ship` skill with `wp <n>` in
   this turn. The hooks carry the prompt across the compaction that comes when the context fills, as at
   a checkpoint. `/np-ship` still puts to the author each finding against this session's decisions.

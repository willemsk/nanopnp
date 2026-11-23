# Implement a work package

`/np-implement [wp <n>]` is step 2 of the implementation workflow. It executes the plan under
`docs/plans/`, records what the execution taught, and opens the PR. It chains into `/np-ship` only
when the author sets `NANOPNP_AUTO_SHIP=1` (`finish.md`, *Finishing*).

## Load the brief

1. Find the package's PR and branch (the core). Then read the WP's plan whole.
   - Its decisions are binding, subject to the specification. If a decision is wrong, correct it in the
     brief and in the specification.
   - Its `### Grounding` is what the code held when the plan was written. If a fact is no longer true,
     correct it in the plan, in the commit of the item that found it. If the correction changes a
     decision, the decision is wrong: correct it as above.
2. Read `knowledge/index.md`, then the sections of the files that the package touches.
3. Read a clause or an Appendix A row that the plan cites when the item that cites it starts, not
   before (`uv run .claude/scripts/clause.py <ID>`).

**The task list** is the one the app shows: Claude Code's `TaskCreate`, `TaskUpdate` and `TaskList`,
loaded with `ToolSearch` where they are deferred.

1. Call `TaskList`. If the list does not match the plan, delete the stale tasks and create one task per
   work item, checkpoints included, with the subject `Item <k>: <what it delivers>`. A ticked item is
   `completed`, the rest `pending`.
2. Do this at the start, after each compaction and in a fresh session: the plan's ticks, not the
   session's memory, say what is done. The session-start hook reminds you after a compaction.
3. Start at the first unticked item.

**`finish.md`**, beside this file, holds the compaction checkpoint, *Keeping the record straight* and
*Finishing*. Read it when the first checkpoint comes, or when the last item is done, and not before.

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
session then resumes from the first unticked item. Set an item's task `in_progress` when you start it
and `completed` when its commit lands; a deferred item's task is `deleted`, its reason in the plan. The gate hook refuses a failing commit and
remembers a pass, so you can split a gated tree into several commits.

An item that changes a screen (`src/nanopnp/gui/`, the front end, `docs/design/`) runs `/np-gui render
<target>` and reads each changed screen before its commit; before it builds the screen it reads the
`impeccable:impeccable` craft floor, where the host has the plugin (`/np-gui`). A page error or a failed check stops the
item.

Write the tests of an item with the item, from the plan's *Verification* rows. The plan commits no
tests. Each test is in the test scope and is named as `CLAUDE.md`'s *Testing* says (§8.2.13 N1).

- Write first the analytic test that localises an error to one term.
- If a tolerance can pass for the wrong reason, or two routes can share a mistake, assert against a
  third route.

An open item, a durable finding and an Outcome annotation go where the core's *Records* table says,
in the commit of the item that made them.

## Measurements are deliverables

Run the measurements the plan asks for: timings, convergence rates, minimum damping, route-agreement
figures, memory at the reference mesh size. Record each number with its mesh, configuration and
stabilisation mode, where the plan asks.

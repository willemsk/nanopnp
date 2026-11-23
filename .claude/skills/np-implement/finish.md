# Checkpoints and finishing a work package

`wp.md` beside this file sends a session here at each compaction checkpoint, or when the last
item is done.

## The compaction checkpoint

A compaction checkpoint is a work item (§8.2.16 R11):

1. Tick it in its own commit. Gate and push (the core).
2. Write a prompt. It holds `/compact`, the package, the number of the next item, the values that later
   items need and that the plan and `git log` do not hold, the model of the next step (the core's
   *Models and executors*), and "resume with `/np-implement wp <n>`".
   Pipe it to `.claude/hooks/checkpoint.sh save implement <plan> <n>`, and print it in a `text` block.
3. If that printed `off`, end the turn. The author compacts and resumes. The next item starts from the
   plan and `git log`.
4. If it printed `on`, the author set `NANOPNP_AUTO_CHECKPOINT=1`: go on with the next item in this
   turn. No hook can compact, so Claude Code's own compaction comes when the context fills. The hooks
   give the saved prompt to that compaction as its instructions and to the context after it, and the
   Stop hook blocks once a turn that ends while items remain. Nothing is left to the author unless a
   question stops the turn.

## Keeping the record straight

The core's *Records* table says what each record gets.

- The delivered summary (target 150 words) goes under the WP plan's **Status** line: scope,
  identifiers, live inherited constraints and links to evidence. The phase plan's `### WP<n>` section
  becomes one line: *Delivered <date>.*, the link to the plan, and `Live:` the constraints for later
  packages (§8.4.4).
- Update `docs/plans/current.md` in place. With two lanes open, update only your lane's position line
  (the core's *Two lanes*). Its word target is in its *Handoff Rules*.
- Change both plans' **Status** lines with the summary. The WP plan's line becomes
  `**Status: delivered, <date>.**`. The phase plan's roll-up moves `WP<n>` to the delivered list.

## Finishing

Confirm these yourself:

- Each work item is done and ticked, or deferred with a reason in the plan and a `REV-nn` row.
- Each in-scope `VER-`/`VAL-` that the plan claims has a passing test (N3). Check each other claimed
  identifier against the code, and say so in the PR.
- The specification, the knowledge base and the Outcome annotations are committed.
- Both **Status** lines and `current.md` are updated.
- `CHANGELOG.md` carries the package's entry as `CONTRIBUTING.md`'s *Versions and releases* says.
- Gate and push (the core).

Then read `.claude/workflow/finish.md`, and open or reuse the PR by its *PR contract*, its In brief as
`.claude/workflow/author.md` says. A new PR states under **Verification** that the review waits for
`/np-ship`.

Report the PR link, the identifiers discharged, the tag that the last commit gets after the merge
(or that it gets none), and that the package is ready for `/np-ship`. Do not start the review or
monitor CI in this turn. Then pause (§8.2.33 AI4):

1. Write a prompt. It holds `/compact`, the package, the PR, its head, each decision this session took
   that the plan does not hold, the values the review needs that the plan and `git log` do not hold,
   the shipping model that the plan names, and "resume with `/np-ship wp <n>`". Print it in a `text`
   block.
2. Where the plan names another model for the ship than for the implementation, the ship never chains
   (§8.2.50 AZ21): run `.claude/hooks/checkpoint.sh clear` and end the turn. The author switches the
   model, then compacts and resumes here or starts `/np-ship` in a fresh session.
3. Where it names one model for both, pipe the prompt to
   `.claude/hooks/checkpoint.sh save ship <plan> <n>`.
   - If that printed `off`, end the turn. The author compacts and resumes here, or starts `/np-ship`
     in a fresh session.
   - If it printed `on`, the author set `NANOPNP_AUTO_SHIP=1`: run the `np-ship` skill with `wp <n>`
     in this turn. The hooks carry the prompt across the compaction that comes when the context
     fills, as at a checkpoint. `/np-ship` still puts to the author each finding against this
     session's decisions.

---
name: np-carry
description: Carry one nanopnp work package from its plan to the merge in one session that hands each step to a fresh helper and serves what a helper cannot do — the author's questions, agents, reviews, the PR's wakes and the measures. Use on /np-carry, or when asked to carry or orchestrate a work package.
argument-hint: "wp n"
---

# Carry: `$ARGUMENTS`

This session is the package's main session (§8.4.4). It asks the author, starts the helpers, the
reviews and the workers, holds the PR's subscription and check-in, and measures. A helper keeps the
task list, which this session shares.
It commits nothing and edits only through a review's `--fix`. Each step runs in a helper:
`.claude/workflow/helper.md` says what a helper hands back. The three commands stay the way back: a
`BLOCKED` names the one that continues.

## 1. The package

An argument other than `wp <n>` (`54` or `5.01`): print `Usage: /np-carry wp n` and stop. A ruling
round, a phase or an amendment is not carried.

Read the core, `${CLAUDE_SKILL_DIR}/../../workflow/core.md` (`.claude/workflow/core.md`), the
*Position* of `docs/plans/current.md`, and the package's entry in its phase plan. A package absent
from the phase plan, or marked **Provisional**, stops: it needs `/np-plan amend <phase>` first.

## 2. The stage

Find the package's PR and branch as the core says, and read the stage from the branch's commit
subjects and the plan's ticks:

| The branch shows | Stage |
|---|---|
| no plan of the package | plan |
| the commit `docs: WP<n> implementation plan`, no `, review fixes` after it | plan-review |
| that commit, no item ticked | approval, then implement |
| an item unticked | implement, from the first unticked item |
| every item ticked, the PR open | ship (`np-ship/wp.md` §0 resumes) |
| the PR merged | after the merge |

The plan's models are on the line `**Implementing session: …; ship: …**` of its Execution brief. The
plan and its review run on Fable 5.2.

## 3. A helper

Note the time, `date -u +%FT%TZ`. Start the helper in the foreground with `Agent`:
`subagent_type: "general-purpose"`, `effort: "high"`, and `model` by the stage: `fable` for plan and
plan-review, the plan's implementing model for implement, its shipping model for ship. Its prompt:

```text
/np-<level> wp <n>[ review] as a helper of /np-carry. Read .claude/workflow/helper.md, then
.claude/skills/np-<level>/SKILL.md, and follow it with these arguments.
```

`<level>` is `plan`, `implement` or `ship`; `review` follows for plan-review. Add `Start at item <k>.`
for an implement helper past its first item, and `The review has run: start at review.md's step 3.`
in plan-review.

## 4. Its hand-backs

A helper ends each turn with one `HANDBACK` block. Serve it, then resume the same helper with the
answer by `SendMessage`. A resume names no `/np-` command.

- `ASK`: print the brief, call `AskUserQuestion` with the questions unchanged, and send the answers
  unchanged, free text included.
- `WORKER`: start the agent it names, on its model, in the foreground, at `effort: "high"`, with its
  prompt unchanged; send the worker's reply.
- `REVIEW`: call `Skill(skill="code-review", args=<its args>)` from this session, never inside an
  `Agent`; send the skill's final report.
- `WAIT`: subscribe to the PR once (`subscribe_pr_activity`), schedule at most one check-in at the
  delay it gives, and end the turn. Send the event that wakes you, unchanged.
- `BLOCKED`: tell the author the reason and the command that continues, and stop.
- `DONE`: the step is over. Go on by its stage:
  - **plan**: start the plan-review stage.
  - **plan-review**: call the `code-review` skill first, with the arguments `np-plan/review.md`'s
    step 2 gives, then start the helper. After its `DONE`, print the manager's summary it carries and
    ask the author, with `AskUserQuestion`, to approve the plan or name the decision to change. Send a
    change to that helper in the author's words and serve it again; on approval, start implement.
  - **implement**: a `DONE` at a checkpoint starts a new helper at the next item; the last `DONE`
    starts the ship.
  - **ship**: print its report, and stay subscribed. On the merge, or on the author's word, resume
    the ship helper for `np-ship/wp.md`'s *7. After the merge*.

## 5. The measures

After each `DONE`, run `uv run .claude/scripts/usage.py --label <stage> --since <the noted time>`,
and after an implement helper's also `uv run .claude/scripts/usage.py --reading`. Add the lines to
the PR's **Measured**, where the ship helper reads them. Tell the author of an implement helper that
read over 8,000 words of project text before its first edit (§8.4.4).

## 6. The rules

- One helper at a time. A worker or a review runs while its helper waits.
- Read nothing of a helper's but its hand-backs, the plan's ticks and the models line.
- The core's *Gate and push* binds the helpers; this session pushes nothing.

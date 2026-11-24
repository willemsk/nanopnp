---
name: np-carry
description: Carry one nanopnp work package from its plan to the merge in one session that hands each step to a fresh helper and serves what a helper cannot do — the author's questions, agents, reviews, the PR's wakes and the measures. Use on /np-carry, or when asked to carry or orchestrate a work package.
argument-hint: "wp n"
---

# Carry: `$ARGUMENTS`

This session is the package's main session (§8.4.4). It asks the author, starts the helpers, the
reviews and the workers, holds the PR's subscription and check-in, and measures. A helper keeps the
task list.
It commits nothing and edits only through a review's `--fix`. Each step runs in a helper:
`.claude/workflow/helper.md` says what a helper hands back. The three commands stay the way back.

## 1. The package

An argument other than `wp <n>` (`54` or `5.01`): print `Usage: /np-carry wp n` and stop.

Read the core, `${CLAUDE_SKILL_DIR}/../../workflow/core.md`, the
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

With neither a PR nor a plan the stage is plan: ask for no branch.

The plan's models are on the line `**Implementing session: …; ship: …**` of its Execution brief.

## 3. A helper

Note the time, `date -u +%FT%TZ`: in plan-review, before the review. Start the helper in the
foreground with `Agent`:
`subagent_type: "general-purpose"`, `effort: "high"`, and `model` by the stage: `fable` for plan and
plan-review, the plan's implementing model for implement, its shipping model for ship. Its prompt:

```text
/np-<level> wp <n>[ review] as a helper of /np-carry. Read .claude/workflow/helper.md, then
.claude/skills/np-<level>/SKILL.md, and follow it with these arguments.
```

`<level>` is `plan`, `implement` or `ship`; `review` follows for plan-review. Add `Start at item <k>.`
for an implement helper past its first item, and in plan-review
`The review has run: start at review.md's step 3.` with the skill's final report.

## 4. Its hand-backs

A helper ends each turn with one `HANDBACK` block. Serve it, then resume the same helper with the
answer by `SendMessage`. A resume adds no `/np-` command of its own.

- `ASK`: print the brief, call `AskUserQuestion` with the questions unchanged, and send the answers
  unchanged, free text included.
- `WORKER`: start the agent it names, on its model, in the foreground, at `effort: "high"`, with its
  prompt unchanged; send the worker's reply.
- `REVIEW`: call `Skill(skill="code-review", args=<its args>)` from this session, never inside an
  `Agent`; send the skill's final report.
- `WAIT`: subscribe to the PR once (`subscribe_pr_activity`), schedule a check-in at the delay it
  gives in place of an earlier one, and end the turn. Send the event that wakes you, unchanged.
- `BLOCKED`: tell the author the reason and the command that continues, and stop.
- `DONE`: go on by its stage:
  - **plan**: start the plan-review stage.
  - **plan-review**: call the `code-review` skill first, with the arguments `np-plan/review.md`'s
    step 2 gives, then start the helper. After its `DONE`, print the manager's summary it carries and
    ask the author, with `AskUserQuestion`, to approve the plan or name the decision to change. Send a
    change to that helper in the author's words and serve it again; on approval, start implement.
  - **implement**: a `DONE` at a checkpoint starts a new helper at the next item; the last `DONE`
    starts the ship.
  - **ship**: print its report, cancel the check-in and stay subscribed. On the merge, or on the
    author's word, resume the ship helper for `np-ship/wp.md`'s *7. After the merge*.

## 5. The measures

After each `DONE` or `BLOCKED`, run
`uv run .claude/scripts/usage.py --label <stage> --since <the noted time>`; the session's first
measure takes no `--since`, so that the `/np-carry` prompt counts. After an implement helper's, also
run `uv run .claude/scripts/usage.py --reading` and take the line named `agent-<its id>`. Add the
lines to the PR's **Measured**, where the ship helper reads them. Tell the author of an implement
helper that read over 8,000 words of project text before its first edit (§8.4.4).

With the ship's `REVIEW` answer, send `usage.py --label carry`'s line, taken with no `--since`: the
package's cost so far, which the plan's Outcome takes whole, not summed (§8.3).

## 6. The rules

- One helper at a time.
- A helper may run on after `Agent` or `SendMessage` returns: end the turn and wait for its
  hand-back. If a stop hook then asks for a commit or a push, make neither: the tree is the helper's.
- Read nothing of a helper's but its hand-backs, the plan's ticks and the models line.
- The core's *Gate and push* binds the helpers; this session pushes nothing.

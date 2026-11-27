---
name: np-carry
description: Carry one nanopnp work package from its plan to the merge in one session that hands each step to a fresh helper and serves what a helper cannot do — the author's questions, agents, the review, the PR's wakes and the measures. Use on /np-carry, or when asked to carry or orchestrate a work package.
argument-hint: "wp n"
---

# Carry: `$ARGUMENTS`

This session is the package's main session (§8.4.4). The author starts it on Sonnet 5.5 at medium
effort (`/model sonnet`, `/effort medium`; §8.2.56 BF1). It asks the author, starts the helpers, the
`/code-review` hunt, the review and the workers, lands what they commit, holds the PR's subscription and check-in, and
measures. A helper keeps the task list. This session edits nothing, and commits only what `just land`
commits itself: the registers and the navigation. Each step runs in a helper:
`.claude/workflow/helper.md` says what a helper hands back. The three commands stay the way back.

## 1. The package

An argument other than `wp <n>` (`54` or `5.01`): print `Usage: /np-carry wp n` and stop.

Read the core, `${CLAUDE_SKILL_DIR}/../../workflow/core.md`, the
*Position* of `docs/plans/current.md`, and the package's entry in its phase plan. A package absent
from the phase plan, or marked **Provisional**, stops: it needs `/np-plan amend <phase>` first.

## 2. The stage

Find the package's PR and branch as the core says, and read the stage from the branch's commit
subjects, the plan's ticks and the hand-off note, `docs/plans/phase-<p>/wp<n>-handoff.md`:

| The branch shows | Stage |
|---|---|
| no plan of the package, or only its draft (`docs: WP<n> plan draft`) | plan; a hand-off note of the plan goes on from its **Next** |
| the commit `docs: WP<n> implementation plan`, no item ticked | approval, then implement |
| an item unticked | implement, from the first unticked item |
| every item ticked, the PR open | ship (`np-ship/wp.md` §0 resumes) |
| the PR merged | after the merge |

With neither a PR nor a plan the stage is plan: ask for no branch.

## 3. A helper

Note the time, `date -u +%FT%TZ`. Start the helper in the foreground with `Agent`, its
`subagent_type` by the stage: `np-planner` for the plan, `np-builder` for implement, `np-shipper` for
the ship. Pass no `model` and no `effort`: the agent's file sets both (§8.2.56 BF1), but for the plan's.

**The planning model** (§8.2.56 BF9). At the plan stage's start, before its first helper, ask the
author with `AskUserQuestion` which model plans: "Fable 5.2 at high (Recommended)", or "Opus 5.5 at
xhigh", for when Fable's quota is spent. On Opus, pass `model: "opus"` and `effort: "xhigh"` on each
`np-planner` call of the stage, and name the choice in the first helper's prompt, for its note's
**Decided**.

A first helper's prompt:

```text
/np-<level> wp <n> as a helper of /np-carry. Read .claude/workflow/helper.md, then
.claude/skills/np-<level>/SKILL.md, and follow it with these arguments.
```

`<level>` is `plan`, `implement` or `ship`. Add `Start at item <k>.` for an implement helper past its
first item. A helper that follows a hand-back gets instead:

```text
/np-<level> wp <n> as a helper of /np-carry. Read .claude/workflow/helper.md, then <the note>, and
continue at its Next with: <the answer>
```

Either prompt, after a land, ends with the land's last line, `land: pushed <sha>` (§4).

## 4. Its hand-backs

A helper ends with one `HANDBACK` block, and the hand-back ends it. Serve it, then start a fresh helper
of the same agent with the answer, as §3 says. Never resume a helper with `SendMessage` (§8.2.56 BF2).

**Land first** (§8.2.56 BF11). A hand-back whose `land:` is not `no`, an `np-builder` worker's
included, is landed before it is served: this session holds the 1-hour prompt cache, a helper the
5-minute one. Run `uv run just land <log>`, with `--lease <sha>` for `lease <sha>`, and wait as the
core's *Gate and push* says. On `land: pushed <sha>`, serve the hand-back; where a `REVIEW` prompt
names another head than that sha, give it that sha, as the land's own commits or its rebase moved
it. On `land: failed at <step>`, keep the hand-back and start a fresh `np-builder` in the foreground:

```text
Fix the failed land of WP<n>, at <step>; its log is <log>. Read .claude/workflow/helper.md, fix that
failure and nothing else, commit, and hand back DONE.
```

Land its commits, then serve the hand-back you kept. A failure at the push itself is retried once
first; a second failure at the same step is `BLOCKED`.

- `ASK`: print the brief, call `AskUserQuestion` with the questions unchanged, and pass the answers
  unchanged, free text included.
- `WORKER`: start the agent it names in the foreground, with its prompt unchanged: a project agent on
  its file's model and effort, another on the model named at `effort: "high"`. Pass the worker's reply.
- `REVIEW`: where the block asks no `effort: medium` and the prompt ends `The hunt's findings: <to be
  added>`, first run the hunt on the landed head as `np-ship/wp.md` §4 says, directly, never inside
  an `Agent`, and put its findings on that line (§8.2.61 BK1, BK2); a review at medium effort runs no
  hunt (BK3). Then start `np-reviewer` in the foreground with the prompt otherwise unchanged, at
  `effort: "medium"` where the block asks for it (§8.2.56 BF8). Pass the reviewer's reply, the hunt's
  findings as the reviewer got them, against which the helper checks the reply and which a second
  start of the reviewer takes unchanged, and `usage.py --label carry`'s line taken with no
  `--since`: the package's cost so far, which the plan's Outcome takes whole, not summed (§8.3).
- `WAIT`: subscribe to the PR once (`subscribe_pr_activity`), schedule a check-in at the delay it
  gives in place of an earlier one, and end the turn. Start a fresh `np-shipper` with §3's first
  prompt and the event that wakes you, unchanged: a `WAIT` leaves no note. Only a CI result, a
  review or a person's comment, the merge, or the check-in starts one; a `subscription.created`
  event or a bot's comment starts none, and the turn ends again.
- `RUN`: serve none whose command is a test selection the land's push gate already ran on that head;
  answer it with the land's log. Otherwise start its command with Bash `run_in_background` and
  `timeout: 7200000`, as the default stops it at 30 minutes, and wait on its log in the foreground,
  as the core waits on a land. Decide on the log's `exit` line, never on a partial log. Start a
  fresh helper with §3's prompt after a hand-back and the log's path.
- `BLOCKED`: tell the author the reason and the command that continues, and stop.
- `DONE`: go on by its stage:
  - **plan**: print the manager's summary it carries and ask the author, with `AskUserQuestion`, to
    approve the plan or name the decision to change. A change goes to a fresh `np-planner`, on the
    planning model, in the author's words; on approval, start implement.
  - **implement**: a `DONE` at a checkpoint starts a fresh `np-builder` with §3's prompt after a
    hand-back, its note and `Start at item <k>.` for the next item; the last `DONE` starts the ship.
  - **ship**: print its report, cancel the check-in and stay subscribed. On the merge, or on the
    author's word, start a fresh `np-shipper`, whose `np-ship/wp.md` §0 goes to *7. After the merge*.

## 5. The measures

After each `DONE` or `BLOCKED`, and the land before it, run
`uv run .claude/scripts/usage.py --label <stage> --since <the noted time>`; the session's first
measure takes no `--since`, so that the `/np-carry` prompt counts. After an implement helper's, also
run `uv run .claude/scripts/usage.py --reading` and take the line named `agent-<its id>`. Pass the
lines to the next helper, for the PR's **Measured**, where the ship reads them. Tell the author of an
implement helper that read over 8,000 words of project text before its first edit (§8.4.4).

## 6. The rules

- One helper at a time.
- A helper may run on after `Agent` returns: end the turn and wait for its hand-back. If a stop hook
  then asks for a commit or a push, make neither: the tree is the helper's until it hands back.
- Read nothing of a helper's but its hand-backs, its note and the plan's ticks.
- The helpers commit and this session lands (§8.2.56 BF11): it runs `just land` and waits, and
  starts no helper or agent while a land or a `RUN` runs.

# WP6.05 — The orchestrator

**Status: planned, not started.** Written 24 November 2026, grounded in the code at `8b54c5f`. Inherits §8.2.53 BC10
and BC15, the rulings of this plan (§8.2.54 BD2 to BD6), §8.2.50 AZ15, AZ17, AZ18, AZ20 and AZ21, §8.2.37 AM10 and
AM11, and the test scope (§8.2.13 N1, N3). Its last commit on `main` takes `v0.7.0-alpha.5` (§8.4.1).

The [Phase 6 plan](phase-6-library-foundations.md)'s WP6.05 entry sets this scope; `SPECIFICATION.md` governs, and
where it and this plan disagree this plan is wrong. Identifiers are pointers into it.

## In brief

**What changes.** You start one session for a package, with one new command, and it carries the package to the
merge. It gives the plan, the building and the shipping to fresh helpers, so you run no compaction. It comes to you for
your rulings, the plan's approval and the merge. Today's checks showed that
a helper cannot ask you a question or start a helper of its own, so your session does both for it. The
three commands stay as the way back. The package also counts how often, in the last hundred pushes that ran tests, the slow
browser tests could have been left to the pull request's checks, and makes that the rule above a third.

**Cost.** About five sessions, three to six agent hours and eight times you act, three of them today. A user of the
program sees no change.

**What could go wrong.** The session you start may fill up from the two reviews it runs: its size is measured on the
next two packages, and the three commands remain. A helper may read more than the limit: every helper is measured,
and a miss continues the cleanup. The path rule could skip a browser test that a change broke: the pull request's
checks still run every one. The count could flatter the rule: both ways of
counting are reported.

**Your call.** Settled today: helpers, with your session filling their two gaps; the limit binds every helper that
builds; the count takes pushes that ran tests; Opus 5.5 builds and Fable 5.2 ships; the command is called carry.
Still yours: approve this plan after its review. *Recommendation:* approve.

## Execution brief

Scope: the Phase 6 plan's WP6.05 entry; BC10, BC15; BD2 to BD6. It depends on nothing unmerged. It claims no new
identifier and writes no test: instructions, hooks and workflow scripts are outside the test scope (N1), and each
item is done when the code and review say so. The package changes no `src/` and no `tests/`. Its clauses, §7.6,
§8.3, §8.4.4 and §8.4.5, change in the items that land the behaviour (BC10's row; the core's *Normativity*); this
plan's commit adds the rulings alone. This package is carried by the three commands.
**Implementing session: Opus 5.5, high effort; ship: Fable 5.2, high effort** (ruled by the author, BD5). The two
differ, so the ship never chains: the pause's prompt names Fable 5.2.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| **D1 The shape** | `/np-carry wp <n>` starts the main session of one package. It hands each step to a new `general-purpose` helper with an empty context, at high effort, on the step's model: the plan and the plan's fixes on Fable 5.2, each stretch of the implementation up to its checkpoint on the plan's implementing model, the ship on its shipping model. The main session alone asks the author, starts the review and worker agents, holds the PR's subscription and check-in, keeps the task list and measures. It edits and commits nothing. It takes `wp <n>` only: a ruling round stays a session of its own | Ruled by the author, BD2 and BD6 (BC10's fallback amended) |
| **D2 The hand-back** | A helper's last message is one block, `HANDBACK` with a kind: `ASK`, `WORKER`, `REVIEW`, `WAIT`, `DONE` or `BLOCKED`. The main session serves it and resumes the same helper with the answer (`SendMessage`); `DONE` and `BLOCKED` end the helper. A question's text and the author's answer pass unchanged in both directions | The two facts that failed; a finished helper resumes with its context; decided by the plan |
| **D3 The files** | Two new files: `.claude/skills/np-carry/SKILL.md`, at most 900 words, and `.claude/workflow/helper.md`, at most 250, which says what a helper does where a level's file names something it cannot do. No level file, core or hook changes, so the three commands run as today. The stage is read from the branch's commit subjects and the plan's ticks, so `/np-carry` resumes in any session | BC10: the three commands stay, and the plan and the commits carry the state; decided by the plan |
| **D4 The reading limit** | Every helper that implements reads at most 8,000 words of project text before its first edit; the main session's reading is reported, not limited. `usage.py --reading` reports each helper's window | Ruled by the author, BD3 (open decision 13) |
| **D5 The measure** | `usage.py` takes agent hours from the main transcript and its sub-agents' as one timeline, and its line names the count of sub-agents. Touches and sessions stay the main transcript's. §8.3 states a carried package as one session and its helpers | Today a wait on a helper of over 30 minutes is taken as the author away; decided by the plan |
| **D6 The facts** | Item 1 checks the three facts again on the implementing host and records them with the host and version. If all three hold, or the commit gate does not run in a helper, the item stops and goes to the author: BD2 was ruled on today's result. If a helper cannot gate and push, the main session does, on a further kind `PUSH` | Criterion 11 of the phase; decided by the plan |
| **D7 The count** | A push is one `pull_request` run of `ci.yml` with a new head. Its changed paths run from the branch's previous pushed head, or from its merge base with `main` where there is none or the branch was rebased. The last 100 pushes whose paths are not prose-only are taken; the rule applies if it skips 34 or more. The figure on each push's whole branch is reported beside it | Ruled by the author, BD4 (BC15); the delta is what the gate judges inside one session, which a carried package is; decided by the plan |
| **D8 The rule** | `.github/scripts/browser-paths.sh` exits 0 when no path on its input can change a browser test. If the count passes, `gate.sh run` leaves `tests/tier1/test_gui_screens.py` out on such a change, and §7.6 says so. CI is unchanged. If the count fails, the script is not added, nothing changes and BC15 is spent | BC15: safe, and CI still runs every browser test; decided by the plan |

### Grounding

Facts at `8b54c5f`, on the cloud host, Claude Code 2.1.331.

**D1, D2, D6 (probed 24 November 2026 with a `general-purpose` helper on Sonnet).**

- The commit gate runs in a helper: its `git commit --dry-run` made `.claude/hooks/gate.sh` write
  `hook development 51 … passed` to `<git dir>/nanopnp-gate.log`, which did not exist before. The helper saw no
  message of the hook on a pass.
- The helper had `Bash`, `Edit`, `Write`, `Read`, `Skill`, `ToolSearch` and, deferred, `SendMessage` and the
  `mcp__github__*` tools. It had no `Agent`, `AskUserQuestion` or `TaskCreate`, and `ToolSearch` returned no schema
  for them.
- `SendMessage` to the finished helper's id resumed it, and it answered from its earlier output.
- The main session's `Agent` tool takes `model` (`sonnet`, `opus`, `haiku`, `fable`) and `effort`; it says to set
  `effort` only where an instruction asks, so `np-carry/SKILL.md` asks.
- `mcp__claude-code-remote__create_session` was refused by the auto-mode classifier, so separate sessions are
  untested.
- Not probed: that a helper can start `gate.sh run` in the background, wait and push. Item 1 does it.

**D3.**

- `.claude/skills/np-plan/SKILL.md`, *The pause*, and `np-implement/finish.md`, *The compaction checkpoint* and
  *Finishing*, end a step by printing a `/compact` prompt and ending the turn.
- `np-plan/wp.md` and `np-ship/wp.md` §4 ask the author through `AskUserQuestion`.
- `np-plan/review.md` step 2 and `np-ship/wp.md` §4 call `Skill(skill="code-review", …)` "never inside an `Agent`":
  inside one it returns no findings. `--fix` writes to the working tree, which a helper shares.
- `np-implement/wp.md`, *Sub-agent items*, and `np-ship/wp.md` §4 (the `physics-reviewer`) start agents;
  `np-implement/wp.md` keeps the task list with `TaskCreate`.
- `np-ship/wp.md` §4 and §5 subscribe to the PR and follow the steward's *Bounded wakes*; a PR event wakes the main
  conversation, not a helper.
- A stage shows in the subjects the levels already commit: `docs: WP<n> implementation plan`, the same with
  `, review fixes` (`review.md` step 4), the ticks `- [x]` of its *Work items*, and `fix: close the review gaps` or
  `docs: code review <NNN>` (`np-ship/wp.md` §4).
- The plan's models are on the line `**Implementing session: …; ship: …**` of its Execution brief.
- `.claude/hooks/checkpoint.sh` acts only on a saved checkpoint; a helper saves none.
- `CLAUDE.md` holds 1,490 words and WP6.03 held it to 1,500; a helper that implements reads it.

**D4.**

- `usage.py` `reading()` opens a window at a typed event that `_np_command()` matches. A helper's transcript is
  `<project>/<session>/subagents/agent-<id>.jsonl`; its first event is `type: user` with the hand-over prompt as a
  string, so `usage.py --reading --transcript <that file>` already measures it when the prompt starts with the
  command. `NP_COMMAND` does not match the command's name inside a path.
- `_main_reading()` reads one transcript, or `--pages`; it does not read the sub-agents' beside it.
- A first window read 7,186 words under WP6.03. The standing files a helper reads are `CLAUDE.md` 1,490, the core
  898, `np-implement/SKILL.md` 103 and `wp.md` 739, and a plan up to 3,850: 7,080, which leaves 920 for
  `helper.md`, the prompt and the clauses.

**D5.**

- `usage.py` `measure()` sums the gaps of the main transcript alone, and drops a gap over `AWAY_S`, 1,800 s. Its
  token loop already reads `path.parent / path.stem / "subagents"`.
- `_typed()` is true for a helper's first event, so touches must stay the main transcript's.

**D7, D8.**

- `gate.sh` in `run` mode sets `base` to the branch's last commit whose tree holds a `push` stamp, else to the merge
  base with `origin/main`; `docs_only` comes from `.github/scripts/prose-only.sh` on the paths since `base`. The
  stamp file keeps one line for each selection.
- The push selection is one call: `check "pytest (push selection)" uv run pytest -q -rsfE -n auto --dist loadfile`.
- The browser tests are `tests/tier1/test_gui_screens.py` alone: 149 tests, 468 s of the gate's 539 s (BC15). It
  imports `nanopnp.api.project` and `nanopnp.gui.web`, and starts the server through `nanopnp.cli`.
- Importing those loads 170 of the 203 modules of `src/nanopnp`, in every subpackage; the rest are stages reached
  through the registry. `core/paths.py` reads `data/` and `tests/data/structures`.
- `mcp__github__actions_list` (`list_workflow_runs`, `ci.yml`, event `pull_request`) returns each run's
  `head_branch`, `head_sha` and `created_at`; 611 such runs exist. `git fetch origin <sha>` fetched two heads of a
  branch that was merged by rebase. The clone is shallow, 50 commits.
- `.github/workflows/ci.yml`'s `tests` job runs `-m "tier1 and not slow"` with `NANOPNP_REQUIRE_BROWSER=1` on every
  pull request that changes code; it reads no path rule.

### Implementation details

**Item 1, the facts.** Start one `general-purpose` helper on Sonnet. Its prompt: list your tools, and say whether
`Agent`, `AskUserQuestion` and `TaskCreate` are among them, also after `ToolSearch`; write the note, commit it, run
the push gate in the background and wait as the core says, push, and reply with the gate log's
last line and the push's output. Resume it once with `SendMessage` and ask for its commit's subject. The note
marks each fact `[verified]`, with the date, the host and Claude Code's version in its footnote.

**Item 2, `.claude/workflow/helper.md`.** It says: `/np-carry` started you for one step; follow the level's files,
but for this table.

| Where a level's file says | A helper |
|---|---|
| ask the author | hands back `ASK` |
| give an item or a read to an agent | hands back `WORKER` |
| call the `code-review` skill | hands back `REVIEW` |
| subscribe to a PR, wait for CI, schedule a check-in | hands back `WAIT` |
| keep the task list, run `usage.py` or `checkpoint.sh` | skips it |
| print a prompt, pause, report, end the turn | hands back `DONE` |

Two rules follow, make your first change with an edit tool (AZ17) and go on after a resume, then the block:

```text
HANDBACK <kind>
step: <plan | plan-review | implement | ship>
next: <item k, or the step that follows>
<body>
```

- `ASK`: the round's brief, then a fenced JSON array of at most three questions in `AskUserQuestion`'s shape, as
  `.claude/workflow/author.md` writes them.
- `WORKER`: `agent: <type>`, `model: <name>`, then the worker's whole prompt.
- `REVIEW`: `args: <the skill's arguments>`.
- `WAIT`: `pr: <number>` and the steward's check-in delay.
- `DONE`: the PR, the head's sha and what no record holds, in 200 words; after a plan's review, the manager's
  summary in full.
- `BLOCKED`: the reason, whether the tree is clean and pushed, and which of the three commands continues.

**Item 3, `.claude/skills/np-carry/SKILL.md`.** Front matter as `np-ship/SKILL.md`'s. Its steps:

1. An argument other than `wp <n>`: print `Usage: /np-carry wp n` and stop. Read the core, `current.md`'s position
   and the package's entry in its phase plan. A package absent or **Provisional** stops for `/np-plan amend`.
2. Find the branch (the core) and read the stage:

   | The branch shows | Stage |
   |---|---|
   | no plan of the package | plan |
   | the plan's commit, no `, review fixes` commit | plan-review |
   | that commit, no item ticked | approval, then implement |
   | an item unticked | implement, from the first unticked item |
   | every item ticked, no code review's commit after the last tick | ship |
   | the PR merged | after the merge |

3. Note the time (`date -u +%FT%TZ`). Start the stage's helper in the foreground: `Agent`,
   `subagent_type: "general-purpose"`, `effort: "high"`, `model` by D1. Its prompt, in full: `/np-<level> wp <n>[
   review] as a helper of /np-carry. Read .claude/workflow/helper.md, then .claude/skills/np-<level>/SKILL.md, and
   follow it with these arguments.` Where it applies, add `Start at item <k>.` or `The review has run: start at
   review.md's step 3.`
4. Serve each hand-back, then resume the helper with `SendMessage`; a resume names no `/np-` command.
   - `ASK`: print the brief, call `AskUserQuestion` with the questions unchanged, send the answers unchanged. Never
     answer for the author.
   - `WORKER`: start the agent named, in the foreground, at high effort; send its reply.
   - `REVIEW`: call the skill from this session; send its final report.
   - `WAIT`: subscribe to the PR once, schedule at most one check-in, end the turn; send the event that wakes you.
   - `BLOCKED`: tell the author, with the command that continues, and stop.
   - `DONE`: go to the next stage. In plan-review, call the skill first, as `review.md`'s step 2 gives it, then
     start the helper; after its `DONE`, print the manager's summary and ask the author to approve or to change a
     decision, and send a change to that helper in the author's words. After an implement `DONE`, start a new
     helper. After the ship's `DONE`, print its report and stay subscribed; on the merge, or the author's word,
     resume the ship helper for *7. After the merge*.
5. While implementing, set the task list from the plan's ticks after each hand-back. After each `DONE`, run
   `uv run .claude/scripts/usage.py --label <stage> --since <the noted time>`, and after an implement helper's also
   `--reading`; the ship helper writes the lines to the PR's **Measured**. Tell the author of a helper over 8,000
   words.
6. One helper at a time. Read nothing a helper wrote but the plan's ticks and its models line.

**Item 4, `usage.py`.**

- `measure()`: walk the events at or after `start` of the main transcript and of every `subagents/*.jsonl` as one
  list by time, and add each gap unless its later event is a main event that is typed or answers a question, or the
  gap is over `AWAY_S`. Touches and sessions stay. Add `"helpers"`, the count of sub-agent transcripts in the list;
  when it is not zero the line reads `1 session, 6 sub-agents, 3.2 agent hours, …`.
- `_main_reading()`: with neither `--transcript` nor `--pages`, add each sub-agent transcript beside the main one,
  by its first event's time, named by its file's stem.

**Item 6, the count.** From the scratchpad; no script is kept.

1. `git fetch --unshallow origin main`.
2. Page `mcp__github__actions_list` (`list_workflow_runs`, `resource_id: ci.yml`, event `pull_request`,
   `perPage: 100`), newest first; keep `head_branch`, `head_sha` and `created_at`; drop a repeated sha.
3. For each sha, oldest first within its branch: `git fetch origin <sha>`; drop and count one that cannot be
   fetched. `base` is the branch's previous kept sha if `git merge-base --is-ancestor` holds, else
   `git merge-base <sha> origin/main`. The paths are `git diff --name-only --no-renames <base> <sha>`; the
   whole-branch paths run from the merge base.
4. A push whose paths pass `prose-only.sh`, or are empty, does not count. Page until 100 count.
5. `k` is how many of the 100 match nothing in item 7's pattern; `k_branch` the same on the whole-branch paths.

**Item 7, the rule.** `.github/scripts/browser-paths.sh`, in the shape of `prose-only.sh`: exit 1 at the first path
that matches `src/* | data/* | examples/* | tests/data/* | tests/conftest.py | tests/tier1/conftest.py |
tests/tier1/test_gui_screens.py | pyproject.toml | uv.lock | .claude/hooks/gate.sh | .github/scripts/*`, else
exit 0. In `gate.sh`, before the push selection's `check`: where `base` is not empty and the paths that feed
`docs_only` pass the script, add `--ignore=tests/tier1/test_gui_screens.py` to that call, and `say` that the browser
tests are left to the pull request's CI, in the summary line too.

### Work items

- [ ] 1. The facts checked again and recorded: `knowledge/07-software-stack/26-what-a-claude-code-helper-can-do.md`,
  its `index.md`, `knowledge/log.md`, and an Outcome here (D6); done when the code and review say so.
  **Executor:** main
- [ ] 2. `.claude/workflow/helper.md` (D2, D3); done when the code and review say so, at 250 words or fewer.
  **Executor:** main
- [ ] 3. `.claude/skills/np-carry/SKILL.md` (D1 to D3); done when the code and review say so, at 900 words or
  fewer. **Executor:** main
- [ ] 4. `.claude/scripts/usage.py`: the timeline and the helpers' reading (D4, D5); done when the gate passes and
  both modes print this session's lines with its sub-agents. **Executor:** main
- [ ] 5. Compaction checkpoint. **Executor:** main
- [ ] 6. The count, `docs/plans/sessions/browser-path-count.md` (D7); done when the record holds the date, `main`'s
  sha, the runs paged, the shas dropped, `k`, `k_branch`, a table by branch, the commands and the verdict, `k ≥ 34`.
  **Executor:** `general-purpose` on Sonnet, high effort
- [ ] 7. On a pass alone: `.github/scripts/browser-paths.sh`, `.claude/hooks/gate.sh` and a sentence in §7.6's
  NOTE on the per-push selection (D8); done when `gate.sh run` passes on a tree that changes `src/`, and leaves the browser tests out on one that does not. On a
  miss: tick it with the verdict. **Executor:** main
- [ ] 8. The clauses (D1 to D8). §8.4.4: `/np-carry wp n` beside the three commands and what it hands over; the
  reading rule binds every helper that implements; under it a checkpoint ends a helper. §8.4.5: a helper's model
  and effort, what `usage.py` measures, item 1's facts. §8.3: a carried package is one session and its helpers.
  `CLAUDE.md`, *Implementation workflow*: one line, the file at 1,500 words or fewer. `holds-now.yaml`: BC10, BC15
  and BD2 to BD6 name their clauses; `decisions.py`. `CHANGELOG.md`: `## [0.7.0-alpha.5]`. Done when
  `uv run just docs` passes and the code and review say so. **Executor:** main

### Verification

No in-scope test: the package changes instructions, hooks and workflow scripts (N1), and its done-criteria are the
items'. The kept tests stay green on the push gate. The review reads: the record of the three facts; the count's
record and its commands; that `ci.yml` is unchanged (BC15); `helper.md`'s table against each place *Grounding* (D3)
lists; and that a question and its answer pass unchanged (D2).

```bash
.claude/hooks/gate.sh run
uv run just docs
```

### Out of scope

- The first two carried packages, their sessions, agent hours and touches: WP6.06 and WP6.07 (criterion 11).
- The target for the author's touches: the round after WP6.08 (open decision 15).
- Separate sessions that the main session starts: not built (BD2).
- `NANOPNP_AUTO_CHECKPOINT` and `NANOPNP_AUTO_SHIP`: unchanged; their trial is not run (BC10).
- A carried phase, amendment or ruling round: none (BC10).

### Open questions

None blocks the implementation.

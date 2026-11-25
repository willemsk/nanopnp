# WP6.07 — The lean carry

**Status: built and reviewed, awaiting its merge.** Written 25 November 2026 on Opus 5.5 at high effort, grounded in
the workflow at `5946602`; built the same day on the same model. Inherits §8.2.53
BC10, §8.2.54 BD2 to BD6, the rulings of this plan (§8.2.56 BF1 to BF11) and WP6.06's measured cost. WP6.08 is the first package carried the
lean way and measures it. Its last commit on `main` takes `v0.7.0-alpha.7` (§8.4.1; BF10).

The [Phase 6 plan](phase-6-library-foundations.md)'s WP6.07 entry sets this scope; `SPECIFICATION.md` governs, and
where it and this plan disagree this plan is wrong. Identifiers are pointers into it.

## In brief

**What changes.** Carrying a package costs far less. On the last package the most expensive model did 85% of the
work, most of it outside planning: three code reviews, the ship, and the main session. A helper resumed after a
question or a review paid to reload its whole memory, a fifth of the cost; mechanical steps such as pushing ran on
the dearest model; and every helper began by loading tools the project never uses. Now the dearest model only plans, or
at your pick the mid-priced one at a higher effort;
a mid-priced model builds and reviews once; the cheapest ships; a helper that waits for you ends with a short note
and a fresh one carries on; the mechanics are one script.

**Cost.** About 1 session and 2 to 3 agent hours, planned and built in this conversation, and 2 times you act: the
nine rulings, done, and the merge. Nothing changes for a user of the program.

**What could go wrong.** A hand-off note can drop a detail a fresh helper then lacks; the note has a fixed shape,
and the next package shows it. With one review, a fault a second reader would have caught can merge; the review
keeps the physics questions, and the next package's cost and findings are compared with the last's. A helper
limited to a list of tools may miss one it needs; the first item probes them.

**Your call.** All nine decisions are ruled. Still yours: approve this plan. *Recommendation:* approve; the
next package measures what it saves.

## Execution brief

Scope: the workflow of §8.4.4 and §8.4.5 and the files that carry it. It changes no code under `src/`, no test and no
physics. It amends §8.4.4, §8.4.5 and `CLAUDE.md`'s *Models*, and supersedes §8.2.50 AZ20 and AZ21 (each plan
proposes its models) and the parts of §8.2.54 BD2 that make a helper resume. It claims no `VER-` identifier: its
checks are the code and the review (§8.2.13 N3).

**Built and shipped in this conversation, on Opus 5.5 at high effort** (BF7). No helper and no Fable call.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| D1 Models by role | Fable plans (both plan helpers) at high effort, or Opus at `xhigh` where the author picks it when asked at each plan invocation; Sonnet runs `/np-carry`'s main session and ships at medium; Opus builds and reviews at high; a red CI that is a test or a numerical gate goes to a fresh Opus helper. Each role's model and effort are fixed in its agent file, not proposed per plan | Models ruled by the author, BF1 and BF9; efforts decided by the plan |
| D2 No resume | A helper that needs the author, a worker or a review ends with a hand-off note in a fixed shape; the answer goes to a fresh helper of the same role that reads the note. The plan stage is two helpers: survey-measure-ask, then write | Ruled by the author, BF2 |
| D3 The plan's check | No review run of the plan. The plan-writing helper checks its own plan against a fixed list before it commits; `/np-plan wp n review` becomes that check alone and the approval summary | Ruled by the author, BF3 |
| D4 The code's review | One review at the ship by a project agent `np-reviewer` on Opus at high, its prompt holding standards, specification and the physics questions; no separate physics reviewer, no `code-review` fork. The reviewer applies and commits the fix of each confirmed finding; the shipper writes no fix | Ruled by the author, BF4; who fixes decided by the plan |
| D5 After the review | A finding left to the author is a `REV` row by default and the PR merges as reviewed; one the author pulls in gets a review of its own diff by `np-reviewer` on Opus at medium effort, set by the `Agent` call's `effort` | Ruled by the author, BF5 and BF8 |
| D6 Starting context | Each helper agent file lists its tools; `.claude/settings.json` disables each plugin this project never uses | Ruled by the author, BF6 |
| D7 The mechanics | `just land` runs the registers, the docs build when a source changed, a commit of what they wrote, the push gate and its wait, the rebase and the push with retries, and prints one line | Decided by the plan, from BF1 |

### Grounding

- **D1.** `.claude/skills/np-carry/SKILL.md` §3 starts every helper as `general-purpose` with `model` by stage, the
  ship's from the plan's `**Implementing session: …; ship: …**` line; §8.4.5's first two bullets state the same. A
  forked skill takes the main session's model, so the WP6.06 reviews ran on Fable (the post-mortem's table). The
  main session's model is the author's at start: `/np-carry`'s report names Sonnet for the next.
- **D1, effort.** Opus 5.5 runs at `medium` when no effort is given; Sonnet 5.5 defaults to `high`, and its
  guidance starts multi-step tool use at `medium`; Fable 5.2's starts at `high`, with `xhigh` only where a gain is
  measured. `np-carry` §3 passes `effort: "high"` on each `Agent` call today, and `physics-reviewer.md` and
  `gui-reviewer.md` carry `effort: high` in their front matter. Once the call passes no model, an agent file
  without `effort` leaves the builder and the reviewer at Opus's `medium`.
- **D1.** `.claude/agents/physics-reviewer.md` shows the shape of an agent file: front matter `model:` and `tools:`;
  the `Agent` call's `model` overrides it, so `/np-carry` passes none for these agents.
- **D2.** Cache rewrites after a gap above 5 minutes: ship helper 1.34 M of 1.67 M written tokens, plan helper
  0.86 M of 1.41 M (post-mortem). `.claude/workflow/helper.md` defines `ASK`, `WORKER`, `REVIEW`, `WAIT`, `BLOCKED`,
  `DONE`; `np-carry` §4 resumes "the same helper by `SendMessage`".
- **D3.** `.claude/skills/np-plan/review.md` step 2 calls `code-review medium --fix`; steps 3 to 5 fix, commit and
  summarise; its summary template (the manager's summary) stays.
- **D4.** `.claude/skills/np-ship/wp.md` §4 asks the physics reviewer and then `code-review xhigh --fix`; the
  helper passes both back to the main session. `np-reviewer` is an `Agent`, so a helper still cannot start it: the
  ship helper hands back `REVIEW` with the prompt and ends, and a fresh ship helper reads the report (D2). The
  reviewer holds the diff when it finds a fault, as `code-review --fix` did; a fix written by the Sonnet shipper
  would put the package's physics fixes on the model with the least judgement.
- **D5.** `.claude/workflow/author.md` *Putting a choice to the author* and `np-ship/wp.md` §4 put each finding not
  fixed to the author; §8.4.6 makes it a `REV` row when left open.
- **D6.** Helpers started at 73k to 76k tokens, the physics reviewer with three tools at 14k (post-mortem). The
  plugins come from the account, not `.claude/settings.json`, which has no `enabledPlugins` key today. A helper
  needs `TaskCreate`, `TaskList`, `TaskUpdate`, `SendMessage` absent, and `mcp__claude-code-remote__*` only for the
  ship's subscription, which the main session holds.
- **D7.** The core's *Gate and push* steps 1 to 6; `justfile` has a `gate` recipe; `decisions.py`,
  `index_records.py` and `uv run just docs` are the registers and the docs build.

### Implementation details

**Item 1, the agent files.** Each in `.claude/agents/`, front matter `name`, `description`, `model`, `effort`,
`tools`: `np-planner` (fable, high; Read, Edit, Write, Grep, Glob, Bash, the task tools, Context7's two),
`np-builder` (opus, high; the same without Context7), `np-shipper` (sonnet, medium; Read, Edit, Write, Grep, Glob,
Bash, the task tools, the GitHub tools the ship uses), `np-reviewer` (opus, high; Read, Grep, Glob, Bash, Edit,
Write). The body says which skill file the agent follows and points to `helper.md`. Probe each once with a
one-line task: it lists its tools, names the model and effort it runs at, and its start context is under 30k
tokens; record the numbers in the knowledge note 07/26.

**Item 2, the hand-off note.** `helper.md` gains *The hand-off note*: `docs/plans/phase-<p>/wp<n>-handoff.md`,
committed, overwritten at each hand-off, deleted by the ship. Sections: **Step**, **Done** (commits), **Measured**
(numbers only), **Decided**, **Open** (the questions, verbatim), **Next** (the exact first action). At most 600
words. `np-carry` §4: every hand-back ends the helper; the answer starts a fresh helper of the same agent with
"Read `<note>`, then continue at Next with: <answer>". `np-carry` §3 passes neither `model` nor `effort` for these
agents, so their files decide, except the plan stage's (item 3); its report names the main session's start as
Sonnet 5.5 at medium effort (`/model sonnet`, `/effort medium`).

**Item 3, the planning model (BF9).** At every plan invocation the author is asked once, by `AskUserQuestion`:
"Fable 5.2 at high (Recommended)" or "Opus 5.5 at xhigh (Fable's quota spent)". In `/np-carry` the main session
asks at the plan stage's start; the answer holds for both plan helpers and the self-check, goes into the hand-off
note's **Decided**, and on Opus sets `model: "opus"`, `effort: "xhigh"` on their `Agent` calls over
`np-planner`'s front matter. A direct `/np-plan`, at any level, asks first; where the session runs on another
model or effort than the one chosen, it prints the `/model` and `/effort` commands and waits for the author. The
plan's status line names the model and effort that wrote it.

**Item 3, the plan.** `np-plan/wp.md` splits at *Putting the decisions to the author*: the first helper ends there
with `ASK` and the note; the second writes, self-checks and commits. `np-plan/review.md` keeps steps 3 to 5 without
the `code-review` call; its new step 2 is the self-check list of D3.

**Item 4, the ship.** `np-ship/wp.md` §4: hand back `REVIEW` with `np-reviewer`'s prompt (standards, the clauses
cited, the numerics questions as WP6.06's ship wrote them), end. The reviewer fixes and commits each confirmed
finding and reports each doubt and each finding left to the author; a fresh `np-shipper` records each finding not
fixed as a `REV` row (D5) and writes no fix. A red CI classified by `ci-log-classifier` as a test or a
gate failure goes back as `WORKER` for `np-builder` with the log.

**Item 5, `just land`.** A recipe calling `.claude/scripts/land.sh`, which runs the core's steps 1 to 6 in order and
stops on the first failure, printing `land: pushed <sha>` or `land: failed at <step>`.

### Work items

- [x] 8397623 1. `.claude/agents/np-planner.md`, `np-builder.md`, `np-shipper.md`, `np-reviewer.md`, each with its model
  and effort; the probe; knowledge note 07/26 (D1, D4, D6). Done when the code and review say so. **Executor:** main
  > **Outcome — the probe waits for the next session.** An agent file is loaded when a session starts, so this one
  > could not start the four. The next session probed them: each runs on its file's model and effort, and starts at
  > 12.6k to 12.8k tokens, beside 73k to 76k before (REV-289, fixed).
- [x] 91d6b4d 2. `.claude/workflow/helper.md`, `.claude/skills/np-carry/SKILL.md`: the note, no resume, the agents by role
  (D1, D2). Done when the code and review say so. **Executor:** main
- [x] fc30625 3. `.claude/skills/np-plan/wp.md`, `review.md`, `SKILL.md`, `np-carry/SKILL.md` §3: the split and the
  self-check; the models proposal removed; the planning model asked at each invocation (D1, D2, D3). Done when the code and review say so. **Executor:** main
- [x] faf8fa8 4. `.claude/skills/np-ship/wp.md`, `SKILL.md`, `.claude/workflow/author.md`: one review that fixes what it
  confirms, `REV` by default, red CI to Opus (D4, D5). Done when the code and review say so. **Executor:** main
- [x] 624ef01 5. `justfile`, `.claude/scripts/land.sh`, the core's *Gate and push*; `.claude/settings.json`'s
  `enabledPlugins` (D6, D7). Done when `just land` pushes a no-op branch and the code and review say so.
  > **Outcome — the plugins are the account's.** A session started after `enabledPlugins` was pushed still loaded the
  > account's plugins, so the block did nothing and is removed. The tool lists alone keep them out of a helper; the
  > main session keeps them until the author disables them in the account.
  **Executor:** main
- [x] 903ca78 6. §8.4.4, §8.4.5, `CLAUDE.md` *Models*, `holds-now.yaml` (AZ20, AZ21, BD2 superseded), `CHANGELOG.md`,
  the plan's Outcome. Done when `uv run just docs` and `decisions.py --check` pass. **Executor:** main
  > **Outcome — the workflow is lean; its saving is measured on WP6.08.** `just land` pushed this branch end to end
  > (`624ef01`; the push gate 486 s). REV-288 is fixed by BF1 and BF4; REV-289 the agents' probe. Measured
  > to this item: 1 session, 0.7 agent hours, 5 touches, all on Opus 5.5 (0.07 M tokens out, 20 M cached), beside
  > the estimate of 1 session and 2 to 3 agent hours.
  > **Outcome — one review, nine fixes, four rows.** `np-reviewer` reviewed `5946602`..`251cca8` once
  > ([CODE_REVIEW_090](../../code_reviews/CODE_REVIEW_090.md)), fixed nine findings in `f8ebc52` and left REV-290 to
  > REV-293 open. Measured in all: 2 sessions, 1 sub-agent, 0.9 agent hours, 7 touches, all on Opus 5.5 (0.13 M
  > tokens out, 30 M cached), beside the estimate of 1 session and 2 to 3 agent hours.
  > The author pulled in the four rows, now fixed: REV-290 in `ac4fb37`, REV-291 in `ac4fb37` and `5806145`,
  > REV-292 in `f9f4554`, which renumbers this package WP6.07 (§8.2.56 BF10), and REV-293 in `5806145`.
  > The author then ruled BF11: a helper commits and hands back and the main session runs `just land`, as the push
  > gate's 466 to 506 s outlast a helper's 5-minute prompt cache; and a change confined to `.claude/`, but
  > `decisions.py`, is prose to `prose-only.sh`, so it skips the lock check, `mypy` and the suite.

### Verification

No test is added: the package is outside the test scope (§8.2.13 N1). Its checks are item 1's probe, item 5's
no-op push, the docs build and the one review of D4, run on this package's own PR. WP6.08 reports its cost by role
against WP6.06's: the planning model at most a third of its units, and no cache rewrite above 100k tokens after a gap.

### Out of scope

- `/np-gui`, `/np-plan phase`, `amend` and `project`: unchanged but for item 3's question of the planning model;
  a later round may take the same rules.
- The account's plugins outside this project: the author's.
- A change to how `usage.py` measures: none is needed for WP6.08's comparison.

### Open questions

None.

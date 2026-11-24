# Code review 086: WP6.05, the orchestrator

2026-11-24 · PR #217, branch `claude/eager-wozniak-epsjwa`, head `c2927cf` on base `8a92752` (`main`) · scope: the
PR's 18 files, +489 and −87, read from `gh pr diff 217`; the checkout was at the PR's head. Read in place:
`.claude/scripts/usage.py` whole, `.claude/skills/np-carry/SKILL.md`, `.claude/workflow/` (`helper.md`, `core.md`,
`finish.md`, `author.md`), every file of `np-plan/`, `np-implement/` and `np-ship/` that a helper follows, the
steward, `.claude/hooks/checkpoint.sh`, `.claude/settings.json`, the environment's stop hook, §8.3, §8.4.4 and
§8.4.5, §8.2.53's BC10 and BC15, §8.2.54's BD2 to BD6, the WP6.05 plan, and this session's own transcripts, which
hold the probe's helper, the check helper and the count's worker · level: xhigh, with `--fix` · status: completed.

Static review: no test, no `gate.sh` and no run of `usage.py`'s two modes. Read-only checks were run:
`decisions.py --check`; `links.py`; `ruff check` and `ruff format --check` on `usage.py`; the word counts of the
capped files; the count's sums against its worker's data; `git diff` and `git log` on the one push the count's
table marks as odd; the shape of the events in this session's transcripts. After the fixes `index_records.py` was
re-run. The plan's copies of `helper.md` and of the skill's steps (*Implementation details*, items 2 and 3) are
left as the plan's record.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Important | `.claude/workflow/helper.md`, the `WAIT` row | A helper handed back `WAIT` wherever a level's file says "subscribe to a PR". `np-ship/wp.md` §4 subscribes before the review, and the main session serves a `WAIT` by ending its turn until a PR event or the check-in, one hour out. The ship stopped before its review had begun | Fixed: a helper skips the subscription and hands back `WAIT` only to wait; the main session subscribes at the first `WAIT`, as the skill already says |
| 2 | Important | `.claude/skills/np-carry/SKILL.md`, §6 | The skill did not say how the main session waits for a helper. This session's transcript shows a foreground `Agent` call return after 120 s as `Async agent launched`, and `SendMessage` return at once: the main session then ends its turn while the helper's tree is dirty or unpushed. The environment's stop hook (`~/.claude/stop-hook-git-check.sh`) answers such a turn with "Please commit and push these changes", against "It commits nothing" and "this session pushes nothing" | Fixed: a rule in §6 says to end the turn and wait for the hand-back, and to make neither a commit nor a push on a stop hook's word |
| 3 | Important | The skill, §5; `helper.md`, the row that skips `usage.py` | The ship's own cost never reaches the plan's Outcome. `np-ship/wp.md` §4 sums "the PR's **Measured** lines and this session's so far"; a helper skips `usage.py`, and the main session adds the ship's line only after the ship's `DONE`, when the Outcome is committed. Each stage's line also says "1 session", so the sum of the lines gives the number of stages where §8.3 says a carried package is one session. This is what review 085's finding 3 left open | Fixed by `/np-ship` after the pass: with the answer to the ship's `REVIEW` the main session sends `usage.py --label carry`'s line, the package's cost so far as one session, which the Outcome takes whole |
| 4 | Important | The skill, §3 and §5 | The stage's window opened when its helper started. In plan-review the main session runs the review first, so the review's time and tokens fell in no window. The `/np-carry` prompt, a touch by §8.3, preceded the first noted time and was counted nowhere. A helper that ended `BLOCKED` was not measured | Fixed: in plan-review the time is noted before the review; the session's first measure takes no `--since`, so its window opens at the `/np-carry` prompt; a `BLOCKED` is measured too |
| 5 | Important | The skill, the opening lines; `docs/plans/current.md`, **Next** | Nothing names the model of the main session. The plan's review and the ship's review are called from it, and the review agent takes the session's model (this review's agent ran on the session's Fable 5.2 with no model named). §8.4.5 puts a plan's review on Fable 5.2 and the ship on the plan's shipping model; started on another model, `/np-carry` runs both reviews on that one and says nothing | Put to the author by `/np-ship`, who left it open until the round after WP6.08: REV-288 |
| 6 | Important | The skill, §3, the plan-review helper's prompt | The main session runs the plan's review and then starts a helper at `review.md`'s step 3, and the prompt carried none of the review's result. The findings the review could not fix are in its final report alone; `review.md` asks for a `REV` row for each | Fixed: the prompt carries the skill's final report |
| 7 | Important | `.claude/scripts/usage.py`, `NOT_TYPED` | `_typed()` takes a `user` event as the author's prompt unless it starts with one of three tags, `<task-notification>` among them. A hand-back reaches the main session as `<agent-message from=…>`. In this session each arrived during a turn, as an attachment; one that wakes an idle main session, the usual case under `/np-carry`, may be recorded as a `user` event as a task's notification is, and would then count as a touch and open a window | Fixed, not verified: `<agent-message` joins `NOT_TYPED`. The change does nothing if no such event is recorded |
| 8 | Nit | `docs/plans/index.md` | The index was not written again: it lacked `sessions/browser-path-count.md` and quoted the old status lines of the Phase 6 plan and of the WP6.05 plan ("planned, not started") | Fixed: `index_records.py` re-run |
| 9 | Nit | The skill, §4, `WAIT` and the ship's `DONE` | A helper skips "cancel a check-in" because the main session holds it, and the skill never told the main session to cancel it: after the ship's report a check-in still fired, and a second `WAIT` added one to the first | Fixed: a `WAIT` schedules its check-in in place of an earlier one, and the ship's `DONE` cancels it |
| 10 | Nit | The skill, §5 | `usage.py --reading` prints every window of the session each time: the main session's, each earlier helper's, and that of any sub-agent whose prompt names an `/np-` command anywhere, as the probe's and a worker's brief do. "Add the lines" repeated the earlier lines, and a worker's line could be taken for an implement helper's | Fixed: the main session takes the line named by the helper's id |
| 11 | Nit | §8.4.5, the sentence on `--reading` | "For each window an `/np-` command opens and for each sub-agent": a sub-agent whose prompt names no `/np-` command opens no window and has no line (the count's worker has none). The plan's *Grounding* and review 085 say a window opens where a prompt starts with the command; `_np_command()` searches the whole prompt | Fixed: the clause says each window an `/np-` command opens, in the session's transcript and in each sub-agent's |
| 12 | Nit | The skill, §2 | For a package with no PR and no plan, the usual start, "as the core says" ends in the core's "ask for the PR or branch", though the table's first row makes that the plan stage | Fixed: one sentence under the table |
| 13 | Nit | `helper.md`, `DONE` | `DONE` holds 200 words and excepts the manager's summary alone. `np-ship/wp.md` §6's report, which the main session prints, holds the checks, what the review changed, what is left to decide, the cost and four tag commands | Fixed: the ship's report goes whole, as the manager's summary does |
| 14 | Nit | The skill, §4 | "A resume names no `/np-` command" beside "send the answers unchanged" and "send the skill's final report": a report or an answer may name a command. A resume is recorded in the helper's transcript as a meta event and opens no window | Fixed: a resume adds no command of its own |
| 15 | Nit | The Phase 6 plan, open decisions 13 and 17 | "The browser tests' rule waits for WP6.05's count", after the count | Fixed: the row gives the result. §8.1's Phase 6 row still says "if a count supports it", which is true and was left |
| 16 | Nit | `docs/plans/sessions/browser-path-count.md` | One counted push, `17ebf87` on `claude/sleepy-carson-oomrxu`, is a merge commit: its delta holds what the merge brought in from `main`, so it is counted as not skippable while its whole branch (14 paths) is. It is the table's one row where the whole-branch figure is the larger. D7's rule was followed to the letter; read on its whole branch, `k` is 33 | Fixed: the record says so, and `/np-ship` checked that it is the only such push. The verdict stands, 33 < 34 |
| 17 | Nit | `knowledge/07-software-stack/26-what-a-claude-code-helper-can-do.md` | "A PR event still wakes the main conversation" stood under the probe's `[verified]`, and the footnote lists no PR event among what the probe did | Fixed: the sentence says it was not probed |
| 18 | Nit | The note, *Keep the task list*; `helper.md` | The plan's probe found no task tools in a helper and item 1's probe, the same day on the same version, found them; the cause is not known. D1 and `helper.md` now rest on the second, and `helper.md` has no row for a helper without the tools. Under `/np-carry` the main session creates no task | Fixed by `/np-ship` after the pass: a helper skips a task tool it lacks, and `helper.md` is trimmed to hold the row |
| 19 | Nit | `CHANGELOG.md`, the entry's first paragraph | "The package changes no code" beside "`usage.py` measures a session and its helpers" | Fixed: no `src/` and no `tests/`, as the plan says |
| 20 | Nit | `usage.py`, `_subagents` | A docstring on a private function (`.claude/rules/python.md`: "No docstring on a test or on private code"; `CLAUDE.md`, *Rules by path*) | Fixed: removed |
| 21 | Nit | `knowledge/07-software-stack/index.md` | The new line's text was not the note's `description`, which every other line of the index quotes | Fixed |
| 22 | Nit | §8.4.5, the bullet on a helper | The clause restates what the note measured ("on Claude Code 2.1.331 a helper has no `Agent`…"), where the knowledge base's rule is one home for a measurement and a pointer from the clause (§8.2.36 AL17). The fact on the task tools moved once within the day | Fixed by `/np-ship` after the pass: the clause states what a helper can and cannot do as its rule, and points to the note for what was measured and on which version |
| 23 | Nit | Commit `3cb2ef4` | `usage.py`'s measure changed in item 4's commit and its clause, §8.4.5, in item 8's (`9761235`), against `CLAUDE.md`'s "A change to specified behaviour changes the specification in the same commit". The plan's work items put every clause in item 8 | Not fixed: the branch's history is pushed |

No finding touches a ruling of the author. The pass fixed 18 findings and left five; `/np-ship` then fixed
findings 3, 18 and 22, put finding 5 to the author (REV-288) and left finding 23, which a pushed history cannot
take. After all the fixes `np-carry/SKILL.md` holds 881 words against 900 and `helper.md` 249 against 250, and the
plan's delivered summary gives both numbers.

## Checked and found true

- **The diff and the head.** The checkout is the PR's head, `c2927cf`, on `8a92752`; CI's `CI result` is green on
  it. `ci.yml` and `gate.sh` are not in the diff (BC15).
- **`usage.py`'s timeline.** A helper's events carry `_helper`, so touches, the answered questions and the
  compactions stay the main transcript's; the gaps are those of one list sorted by time, so two agents at once are
  counted once; the token loop is unchanged; the line reads `1 session, 6 sub-agents, …`. A helper's first event is
  a `user` event with the prompt as a string, and a resume is a meta event of origin `coordinator`: the first
  opens a window and the second does not.
- **The helpers' models.** The three helpers of this session ran on `claude-sonnet-5-5`, as their `Agent` calls
  named, at high effort.
- **The note against the probe.** The tools, the eight tasks of `TaskList`, the commit gate's 206 s, the push
  gate's 480 s and the two resumes are what the helper's hand-backs say.
- **The count.** The table sums to 100 pushes, 32 and 23 over 46 branches; 399 shas, none dropped; 62 pushes
  passed over. The worker's script follows D7 and uses `prose-only.sh` as it is.
- **The level files.** The stage table's subjects are the levels' own: `docs: WP<n> implementation plan`, the same
  with `, review fixes`, the ticks. Each place the plan's *Grounding* (D3) lists has a row in `helper.md`. A
  question and its answer pass unchanged (D2).
- **The registers.** `decisions.py --check` passes; the ten rows that left the open page are BC15, BD4 and D1 to
  D8. `holds-now.yaml` names a clause for BC10, BD2, BD3 and BD6. `links.py` finds no broken path.
- **The words.** `CLAUDE.md` 1,499; `current.md` 649, its In brief 163; the Phase 6 plan 2,591 outside its
  end-of-phase report.

## Not assessed

- How Claude Code records a hand-back, a PR event or a check-in that wakes an idle main session. This session's
  transcript holds none; finding 7 rests on it, and a PR event may count as a touch in the same way.
- `usage.py`'s two modes on a carried session: the run was not made in this review, and no package has been
  carried yet.
- Whether a main session would commit on the stop hook's word (finding 2): the hook was read, not tried.
- The strict documentation build and the push gate, which `/np-ship` runs on the fixes.

## For the author

- Finding 5, the model the `/np-carry` session runs on: put to the author on 24 November 2026, who left it open
  until the round after WP6.08, with WP6.06's and WP6.07's measured lines (REV-288).
- Findings 3 and 18 needed no ruling: `/np-ship` fixed both.

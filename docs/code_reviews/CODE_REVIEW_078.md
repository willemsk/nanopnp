# Code review 078: PR 209, WP6.03, the instructions cut and the Copilot host retired

2026-11-23 · PR #209 at `c91eca0` (`claude/gifted-hopper-bxr8bg`) on `main` (`e11ef54`) · scope: the pull request's
diff (49 files, from `gh pr diff 209`) · focus: correctness, convention · effort: xhigh, with `--fix` · status:
completed.

Static review: no test, no benchmark and no `gate.sh` run; `/np-ship` gates the fixes. The checkout is the PR's head,
so each file read for context holds the diff's added lines. Read-only checks were run: `git grep` for every live
file that names the host, `hosts.md`, the adapter, the audit folder or the session plan; every citation of a heading
the diff moves or removes; `wc -w` of the start path under `LC_ALL=C` and `LC_ALL=C.UTF-8`, at `e11ef54`, `20bb8b4`
and the head; Verification's row 1; `clause.py` on AA1, AA5, AZ19 and OPN-08; `decisions.py --check`, `links.py
--anchors` and `duplicates.py`. After the fixes `decisions.py` and `index_records.py` were re-run.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Important | `.claude/skills/np-implement/wp.md`, the line on `finish.md`; `np-implement/finish.md`'s opening | `wp.md` no longer holds the compaction checkpoint and sends a session to `finish.md` "when the first checkpoint comes". A session that resumes after a compaction, or a fresh one, reaches the plan's second checkpoint with no instruction to read it: it ticks the item and goes on, without the prompt, `checkpoint.sh save` or the end of the turn. WP6.02's plan has two checkpoints | Fixed: both files say each checkpoint; `wp.md` keeps 739 words |
| 2 | Important | `.claude/workflow/core.md`, *Reading order* and *The package's PR and branch* step 1 | `current.md` is no longer read at the start, and it was what named the package. `/np-implement` with no `wp <n>` and no open package PR reaches "None, and the plan is on `main`" with no way to know which plan | Fixed: with no `wp <n>`, n is taken from what `current.md` names next; the core keeps 899 words. Narrowed at `/np-ship`: step 1 keeps its rule for a PR whose title names a package, and only its "None, and the plan is on `main`" case takes the package `current.md` names next, so `current.md` is not read at every start (D2) |
| 3 | Nit | `CLAUDE.md`; REV-272's section; `CHANGELOG.md`; the plan's delivered summary | Row 4's oracle is 1,500 words or fewer. The records give `CLAUDE.md` 1,505 "by `wc -w` under `LC_ALL=C.UTF-8`", and that count is right: plain `wc -w` in the C locale reads 1,498 because it skips the four `…` and three `→`. The row passes or fails by the locale. REV-272 also gives `.claude/workflow/finish.md` 348, its C count; under its stated locale it is 349 | Fixed: `CLAUDE.md` drops "Each command reads `.claude/workflow/core.md`, then its level's file", which each `SKILL.md` and the core's first line say: 1,497 words, 1,490 in the C locale. The changelog and the delivered summary give 3,238; REV-272 gives 349 and records the cut; its counts at `20bb8b4` and the measured 7,186 stand |
| 4 | Nit | `specification/history/holds-now.yaml`, AZ14 | AZ14 holds in `np-implement/wp.md`, its rule that a delivered package's phase entry becomes one line. That rule moved to `np-implement/finish.md`, *Keeping the record straight* | Fixed; the decisions page re-written |
| 5 | Nit | `.claude/skills/np-ship/wp.md`, opening | The ship's model is cited to AZ20, the implementing model's ruling. AZ21 rules the shipping model | Fixed: AZ21 |
| 6 | Nit | The opening lines of `np-plan/wp.md`, `np-implement/wp.md` and `np-ship/wp.md` | "Step 1", "step 2" and "steps 3 and 4 of the implementation workflow" number the table that the diff removes from `CLAUDE.md`; no live file numbers the steps now | Fixed: each line names the commands it follows or runs; `np-implement/wp.md` keeps its count |
| 7 | Nit | `.claude/workflow/core.md`, *Gate and push* step 4 | The rule to rebase on `origin/<head>` moved from *Host coordination* into the steps every push follows. On a branch's first push `origin/<head>` does not exist and `git rebase` stops with "invalid upstream" | Fixed: "an existing `origin/<head>`", in the same number of words. Shortened at `/np-ship` to "unless step 7 rewrote the branch on `main`", which keeps the core at 898 words (plain `wc -w`) after finding 2's narrowing |
| 8 | Nit | `CLAUDE.md`, *Implementation workflow* (removed); `.claude/hooks/checkpoint.sh` | Where the author sets `NANOPNP_AUTO_CHECKPOINT` and `NANOPNP_AUTO_SHIP` (the shell, the cloud environment's variables, `env` in `.claude/settings.local.json`) left with the paragraph; §8.4.4 and `checkpoint.sh` name the switches but not where they are set | Fixed: `checkpoint.sh`'s header says it |
| 9 | Nit | `.claude/scripts/audit/markers.py` (deleted) | It was the one script that checked each knowledge `[tested: <test>]` marker against `tests/`. No test, gate step or kept script does now, so a renamed test leaves its marker pointing nowhere | Skipped: D6 deletes the folder, and the tag keeps the script; whether to keep a check is the rescoping round's or the author's. Declined at `/np-ship`: the script was a one-off report of code review 039's audit that no gate, CI job, hook or `justfile` recipe ran, so no check was lost; D6, which the author approved with the plan, deletes it, and the tag `copilot-host` keeps it |

## Checked and found true

No live file outside the plans and records names the host, the adapter, `hosts.md`, `copilot-instructions.md` or the
session plan; row 1 prints nothing. `.claude/settings.json` wires the hooks straight to `.claude/hooks/` and still
refuses the three GitHub write tools, so AA5's refusal holds on Claude Code. `session-start.sh` keeps no redirect or
trap of the removed block, and `checkpoint.sh`'s logic is unchanged but for the guard. Every relative link resolves;
`links.py --anchors` names no file of the diff. Each citation of the moved sections, *The PR contract*, *Report and
stop*, *The author's page*, *Keeping the record straight* and *Finishing*, names its new file; the core's step 7 is
the one `np-ship/wp.md` cites. `CLAUDE.md`'s *Setup*, *Testing*, *Durable learnings*, *Do NOT*, **Models**, **Open
items** and **Code review reports** keep the names other files cite. §8.4.4 states the two switches and the pause,
§8.4.5 the agents, the models and the eight scripts with `gui/`, and §7.6 the per-push selection. The decisions page
moves 18 rows to the closed page: AA1 to AA4, AA7, AA8, D1 to D8, REV-166 to REV-168 and REV-278; 484 and 1,105 make
its 1,589. `release.yml` starts on `v*` alone and hatch-vcs reads only tags that hold a digit, so `copilot-host` starts
no release and moves no version. `main` takes a branch by rebase, so the commit that deletes `hosts.md` is item 1's
and its parent holds the host, the audit folder and the session plan. The plan holds 3,622 words outside its Outcome
annotations, `current.md` 699 and its In brief 156.

## Not assessed

- The measured window itself (row 5): `usage.py --reading` was not run on the measuring session's transcript.
- Whether the gate's commit hook passes on the fixes: `/np-ship` runs it.

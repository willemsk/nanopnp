# Code review 085: WP6.05's plan, the orchestrator

2026-11-24 · branch `claude/youthful-meitner-6ztncd` at `5a0c7ee` on `main` (`8b54c5f`) · scope: the plan commit's
10 files, +383 and −48, read from `git diff origin/main...HEAD`. Read in place: `.claude/skills/np-plan/`
(`SKILL.md`, `wp.md`, `review.md`), the core, `finish.md` and `author.md`, `np-implement/finish.md`,
`np-ship/wp.md`, `.claude/hooks/gate.sh`, `.claude/scripts/usage.py`, `.github/scripts/prose-only.sh`,
`.github/workflows/ci.yml`, §7.6, §8.2.53's BC10 and BC15, §8.2.54's BD2 to BD6, and the code each claim rests
on · level: medium, with `--fix` · status: completed.

Static review of prose: no test and no `gate.sh` run. Read-only checks were run: `clause.py` on §7.6; `grep` for
each code fact the plan states; the plan's word count by section. The review ran after a compaction of the session
that wrote the plan. After the fixes `decisions.py` and `index_records.py` were re-run.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Important | The plan, D8 and item 7's pattern | The path rule listed no path under `docs/`. In a checkout `src/nanopnp/gui/web/assets.py` reads `docs/design/tokens.css`, which `prose-only.sh` does not take as prose: a push that changes it alone would have left the browser tests out, though it can move a screen's colours and layout | Fixed: `docs/design/*` is in the pattern, and *Grounding* states the fact |
| 2 | Important | The plan, item 3's stage table | A branch was at the ship only while no code review's commit followed the last tick. `/np-carry` started again while CI ran after that commit matched no row | Fixed: every item ticked and the PR open is the ship; `np-ship/wp.md` §0 resumes after a review |
| 3 | Important | The plan, item 3, step 5 | The ship helper was to write the main session's measured lines to the PR, but the hand-over prompt carries none and the ship's own line exists only after it ends. `np-ship/wp.md` §4 sums the PR's **Measured** lines into the plan's Outcome | Fixed: the main session adds each line to the PR's **Measured** after each step, where the ship helper reads them |
| 4 | Nit | The plan, item 4's done-criterion | `--reading` opens a window only at a prompt that starts with an `/np-` command, and no sub-agent of the implementing session has one, so the criterion could not show a helper's window | Fixed: a one-line check helper whose prompt starts as a hand-over does, named in *Implementation details* and in the criterion |
| 5 | Nit | The plan, D1 | The main session "edits and commits nothing", but it calls the review skill with `--fix`, which applies its fixes from the calling session | Fixed: it commits nothing, and edits only through a review's `--fix` |
| 6 | Nit | The plan, D3 | "No level file, core or hook changes" beside D8, which changes `gate.sh` on a pass of the count | Fixed: the sentence is the orchestrator's |
| 7 | Nit | The plan, item 2's table | `np-ship/wp.md` §6 cancels the check-ins and unsubscribes; a helper holds neither, and the table had no row for it | Fixed: a helper skips it |

No finding touches a ruling of the author. *Implementation details* held 1,137 words after the fixes and holds
1,099 after a trim of prose alone; the plan holds 3,435 words, and 1,613 outside *Grounding* and the details.

## Checked and found true

- **The rulings.** BD2 to BD6 each quote the author's choice and name the recommendation; BC10's row points to
  BD2; `holds-now.yaml` has a line for each. D1, D4, D7 and the models line follow them. BD4's "34 or more" is
  BC15's "more than a third" of 100.
- **`usage.py`.** `AWAY_S` is 1,800 s; `measure()` sums the main transcript's gaps alone and its token loop reads
  `subagents/*.jsonl`; `_typed()` is true for a string prompt; `reading()` opens at a typed event that
  `_np_command()` matches; `NP_COMMAND` refuses a name inside a path; `_main_reading()` reads one transcript or
  `--pages`.
- **`gate.sh`.** `run` takes `base` from the last commit whose tree holds a `push` stamp, else the merge base;
  `docs_only` comes from `prose-only.sh`; the push selection is the one `check` the plan quotes; `say` and the
  summary line exist.
- **The browser tests** are `tests/tier1/test_gui_screens.py` alone: no other file under `tests/` or `src/` names
  Playwright or `NANOPNP_REQUIRE_BROWSER`. CI's Tier 1 leg sets it on every pull request that changes code.
- **The level files.** The pauses, the questions, the review calls, the agents, the task list and the PR's
  subscription are where *Grounding* (D3) puts them; the commit subjects of the stage table are the levels' own.
- **The words.** `CLAUDE.md` 1,490, the core 898, `np-implement/SKILL.md` 103 and `wp.md` 739. The plan's In brief
  holds 274 words with no backtick or identifier; `current.md` holds 700 or fewer.
- **§7.6** has the NOTE on the per-push selection that item 7 amends. `knowledge/07-software-stack/` ends at 25.

## Not assessed

- The helper's tools, the gate inside a helper and the resume: the plan's probe is carried, and item 1 checks them
  again.
- The 170 of 203 modules, the 611 runs and the 468 s of 539 s: carried from the plan and BC15, not measured again.
- That a helper can run the push gate in the background and push: item 1.

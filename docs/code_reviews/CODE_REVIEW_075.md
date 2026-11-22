# Code review 075: WP6.02's plan, the cleanup's measure, audit and records

2026-11-22 · branch `ccr-7f71a93c-ebh88d` at `280ab9c` on `main` (`eacad07`) · scope: the plan commit's 10 files,
read from `git diff HEAD~1`. Read in place: `.claude/skills/np-plan/` (`wp.md`, `review.md`, `rulings.md`),
`.claude/workflow/author.md`, §8.2.47 AW5, §8.2.49 AY5, AY7 and AY8, §8.2.50, §8.4.6, `holds-now.yaml`,
`.claude/scripts/` (`usage.py`, `clause.py`, `decisions.py`, `duplicates.py`, `links.py`),
`src/nanopnp/validation/findings.py`, `tests/tier1/test_layering.py` and `test_written_architecture.py`,
`docs/scripts/generate.py`, `mkdocs.yml`, `.claude/skills/np-ship/phase.md`, the `claude-api` skill's
`shared/prompt-audit.md`, this session's transcript and one page of `list_events` · level: medium, with `--fix` ·
status: completed.

Static review of a plan commit: no test and no `gate.sh` run. Read-only checks were run: the plan's counts against
`holds-now.yaml`, `review-findings.md`, `decisions.md` and `git grep`; `clause.py` on the eighteen identifiers of the
plan's verification row and on AY5; `links.py --anchors`; the plan's word counts; the form of a typed command, of a
skill's text and of a saved `list_events` page in this session's transcript. After the fixes `decisions.py` was
re-run and `decisions.py --check` passes. The plan holds 3,538 words, 1,499 of them outside its Grounding (979) and
its Implementation details (1,060); its In brief holds 274; `current.md` holds 698.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Important | The plan, Grounding D1 and item 1's steps 2 and 5 | "The text of the command's skill arrives inside the typed prompt." In this session's transcript the typed prompt is 14 words, `<command-name>/np-plan</command-name>` with its arguments, and the skill's text is the next `user` event, with `isMeta` true, which `usage.py:_typed` refuses. Step 5 counted "the window's own prompt" as instructions, so every window would have lost its command's skill text, and each `Skill` call's, from the count the limit binds | Fixed: the grounding states the two events; step 5 counts a skill's text as instructions when its base directory is under `.claude/`, else as commands |
| 2 | Important | The plan, item 1's step 1 and item 2 | A page event is normalised to `{"type", "message", "_t", "session"}`, which drops `isMeta`. The one page read here shows no `isMeta` on its events. If a page does not mark a skill's text, `_typed` takes it for a typed prompt that holds `/np-`, and each command opens two windows: an empty one, and one named from the skill's first words. The baseline's table would then have double the rows and no `/np-implement` window by name | Fixed: the normalised event keeps `isMeta` where the page gives it; an event that starts `Base directory for this skill:` opens no window; item 2's step 1 reads how a page gives the prompt and the skill's text before the reader is written |
| 3 | Important | The plan, D2 and Grounding D2 | "Both forms are in the calling agent's transcript." A page over the inline limit is not: the tool result holds a file name, and the page is in `<project>/<session>/tool-results/mcp-claude-code-remote-list_events-*.txt`, behind an `<other-session …>` notice. A reader given the sub-agents' transcripts alone finds no event of any long session. D2 also said the pages stay in the scratch folder, which is not where the harness writes them | Fixed: the grounding gives the file's place and opening; the reader opens the file the result names; D2 says the pages stay on the session's machine, outside the tree |
| 4 | Important | The plan, item 1's step 5 | Only `Read`, and `Grep` with a path, were classed by path. A record read with `cat`, `sed -n`, `head` or `tail` through `Bash` counted as command output, outside the project text that AZ9 limits. The prototype's own numbers show the size of the hole: 13,325 words of command output against 13,824 of instructions and records. A session could meet the limit by reading its plan with `cat` | Fixed: a `Bash` call that is one of those four commands on one file is classed by the file's path. Other command output stays commands, printed beside the count |
| 5 | Nit | The plan, item 1's step 5 | A path that holds `/.claude/` is instructions and one that holds `/docs/` is records, tested before the code rule. `.claude/scripts/usage.py`, `.claude/hooks/gate.sh` and `docs/scripts/generate.py` are code, and item 1 itself reads the first | Fixed: a path that ends `.py` or `.sh` is code, tested first |
| 6 | Nit | The plan, item 1's self-check | The check asks that the two token numbers equal the `usage` sums of the messages the script itself names. It cannot fail, and it checks no word count, which is what the limit binds | Fixed: it also asks that the words of one whole-file `Read` of a record equal `wc -w` of the file |
| 7 | Nit | The plan, D2, D5 and D6; `decisions.md` | Their *Why/source* cites `AZ10`, `AZ11` and `AZ12` bare. `decisions.py:_holds_from` reads a ruling only as `§8.2.50 AZ10`, so the three rows said "Holds now: unstated" beside rulings of the author | Fixed: the three cells carry `§8.2.50`; `decisions.py` re-run |
| 8 | Nit | `docs/plans/current.md`, *Not to be re-decided*; `decisions.md` | The new bullet's citation was on its second line. `decisions.py:current` reads a bullet's first line, so the row said "unstated" | Fixed: the citation follows the first statement, on the first line; `current.md` still holds 698 words |
| 9 | Nit | The plan, Grounding D6 and item 7's step 4 | "605 links, in 8 files" counts Markdown alone. `docs/code_reviews/CODE_REVIEW_039/decisions.json` holds 222 more, which step 4 did not rewrite and `links.py` does not check, so they would point at sections that have moved | Fixed: the grounding names the file and step 4 rewrites it |
| 10 | Nit | The plan, Grounding D6 | "in force 333": the page at `eacad07` gives 334, and the fifteen counts then sum to its 1,556 rows. At this head the page holds 1,569 rows, the plan's own eight and AZ9 to AZ12 among them; the 1,066 closed rows are unchanged | Fixed: 334. The other counts stay as at `eacad07`, which the plan's status line names |
| 11 | Nit | The plan, items 2 and 3 | Both add a file to `docs/plans/sessions/`. `docs/plans/index.md` is written by `index_records.py`, which no gate runs, and no item named it | Fixed: item 2's step 4 runs it for both files |
| 12 | Nit | The plan, In brief | 276 words against `author.md`'s 275 | Fixed: 274 |
| 13 | Nit | The plan, item 6 and its done-criterion | "Prints AA6 and AV6 as one line each": the steps give a label line and then the identifier with its bold phrase, two lines | Fixed by the review turn: the done-criterion says "a label and one line each" |
| 14 | Nit | The plan, item 1 | `usage.py` already has `--all` and `--since`; the plan does not say whether they combine with `--reading`, nor what `--reading` prints on a host with no transcript | Fixed by the review turn: item 1 says `--reading` is refused with `--since` or `--all`, and prints `Reading: not measured` with exit 0 where there is no transcript |

Checked and found true: `CLAUDE.md` holds 2,220 words and the two rules 715; `holds-now.yaml` has 409 entries, 62
`spent`, 18 `superseded by` and 34 with `open:`; AA6 and AV6 are `superseded by AY5`, and `clause.py AY5` prints
both rows in full; the review log's 278 rows have the seven status counts given, 218 closed and 60 kept;
`parse_log` reads an archive of the form the plan gives; the VER-61 test, `decisions.py:registers`,
`duplicates.py:main`, `generate.py:REGISTERS` and `mkdocs.yml` read the log as the plan says;
`test_ver79_the_decisions_page_equals_what_the_script_renders` calls `main(["--check"])`, so it covers a second page
unchanged; `links.py --anchors` names no anchor of `review-items.md` today; `.claude/scripts/audit/` holds ten
scripts; `phase.md` says "Target 1,500 words, without the report" and the Phase 6 plan holds 1,877; the audit
guide's steps and its six fields are as the plan lists them; a page of `list_events` has the envelope the plan
gives, with `has_more`, `first_id` and a `parent_tool_use_id` on a sub-agent's event; record 01, 11 and 42 show
that a row is added to a record on a later date, so AZ13 and AZ14 may join record 50; every identifier of the
verification row resolves; the plan has each section of `wp.md`, each item names its executor, and the In brief has
no backtick or identifier.

The review turn also brought §8.2.50 AZ10's row into step with finding 3: its pages "stay on the session's
machine, outside the tree", where it said "in the session's scratch folder". The author's choice is unchanged.
`current.md` names `/np-implement wp 6.02` as the next step.

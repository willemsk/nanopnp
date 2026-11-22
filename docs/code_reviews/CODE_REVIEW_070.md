# Code review 070: WP5.28's plan, the close of Phase 5

2026-11-22 · branch `claude/np-plan-wp-5-28-apae19` at `c7c944c` on `main` (`f853d52`) · scope: the plan commit's 17
files, read from `git diff origin/main...HEAD`. Read in place: `docs/plans/phase-5/wp5.28-the-close.md`,
`.claude/skills/np-plan/wp.md` and `review.md`, `.claude/workflow/author.md`, `.claude/skills/np-ship/phase.md`,
`specification/history/holds-now.yaml`, `.claude/scripts/decisions.py`, `.github/workflows/ci.yml`, the `tier12`
action, `tests/tier1/test_gui_screens.py`, `.claude/scripts/gui/redraw.cjs` and `render_shell.py`, `CHANGELOG.md`,
`CITATION.cff`, `README.md`, `docs/overrides/main.html`, Appendix A and the review register · level: medium as called,
with `--fix` · status: completed.

Static review of a plan: no test and no `gate.sh` was run. Read-only checks were run: the register's status counts
and the plan's owner check, the `open:` lines of `holds-now.yaml` sorted against the plan's three lists, the
capability record's counts, the Qt search, three `--collect-only` counts, the registries' lengths, a script resolving
the twelve Appendix A rows, the plan's word counts, and `git ls-remote --tags`. After the fixes,
`index_records.py` and `decisions.py` were re-run, and `decisions.py --check` and `links.py` pass.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Important | The plan, *Verification*, first row; D3; item 3, step 1 | The row gives VER-78 "on three platforms" by "the dispatched run". The `platforms` job installs no Chromium and leaves `NANOPNP_REQUIRE_BROWSER` unset, so `test_gui_screens.py:_launch` skips all 149 screen tests on every leg; only `gate.sh run` and the pull request's `tests (tier1)` job, both Linux, require a browser. Appendix A's CON-13 row already says "VER-78 on ubuntu". The report would have claimed the screens on three operating systems from a run that skipped them | Fixed: the row is split, VER-78 on Linux by the gate and the Tier 1 leg; D3 and the grounding state the skip; step 1 reads the skipped count and reports VER-78 as Linux alone |
| 2 | Important | The plan's status line, Execution brief and *Out of scope*; `current.md`; the Phase 5 plan's status and WP5.27 entry; `docs/plans/index.md` | Each says the tag `v0.6.0-alpha.27` is "not yet pushed" or "to be pushed". `git ls-remote --tags origin` shows it on `f853d52`, created six minutes after the plan's commit. The plan's dependency and its first deferral row are stale | Fixed: each place names the tag as pushed; the deferral row is removed; the index is regenerated |
| 3 | Important | The plan, *Implementation details*, item 1 | The Sonnet item's rules assume `open: <package> (<parenthesis>)`. Seven of the 49 lines do not have that shape: T2 (`REV-nn in WPn` pairs), S9 and S10 (a sentence after the package), AS3 (a parenthesis naming a plan's open decision), AN1 and AJ2 (a parenthesis naming neither a clause nor a ruling), AR8 (a parenthesis naming both). AN5's example left the sub-agent a condition to settle ("only if the record names WB-37"; the record does not). `wp.md`: a sub-agent's item "chooses nothing" where it is mechanical | Fixed: the item gives the value of S9, S10, T2, AS3, AN1 and AN5 from each ruling's record, a rule for a mixed parenthesis with AR8's value, and AJ2's drop. *Implementation details* stays within its cap |
| 4 | Nit | The plan's first six lines; `docs/project/decisions.md` | `decisions.py:PLAN_DONE` reads `delivered`, `merged`, `implemented` or `closed` in a plan's first six lines as a delivered plan. The title's "Phase 5 closed" and the status line's "WP5.27 merged" made the register list D1 to D6 of a plan not started as `delivered plan` | Fixed: the title reads "The close of Phase 5", the status line "WP5.27's merge"; the register now reads `plan in flight` for the six rows |
| 5 | Nit | The plan, D5 and its grounding; work item 6 | The grounding calls `docs/getting-started.md`'s line "the one stale mention of the Qt shell in the user pages". `docs/overrides/main.html` line 5, the banner on every page, lists "the desktop shell" as delivered, and item 6 changed only the banner's version sentence | Fixed: the grounding names both; D5 and item 6 change the banner's wording too |
| 6 | Nit | The plan, item 3, step 1 | `ref: <head>` for the dispatch. A `workflow_dispatch` takes a branch or a tag, not a commit, and D3 says "the branch head" | Fixed: the step names the branch and confirms the run's head is the pushed commit; the grounding states the rule |
| 7 | Nit | The plan, D1 | "Every row not `fixed` names its owner, checked by item 2's script." The script reads `accepted` and `deferred` rows only; the 14 `declined`, `wontfix` and `post-1.0` rows name a ruling and no owner, as §8.4.6 allows. The oracle and the decision disagreed | Fixed: D1 says every `accepted` or `deferred` row names its owner, and the other three statuses name their ruling |
| 8 | Nit | The plan, D2's grounding | `_status_of_ruling` is said to read "anything else as `in force`". It also reads `superseded by` as `superseded` and an empty entry as `unstated`, which matters for a line the sub-agent leaves empty | Fixed: the grounding lists all five |
| 9 | Nit | The plan, item 2's owner script | The pattern `Phase 6\|phase\|FR-43\|Copilot\|next change` passes any ruling that holds the word "phase", such as "a later phase", so a row with no named owner could pass | Fixed by the review turn: the pattern names the owners, `Phase 6\|(composer\|mutator\|sketcher)'s phase\|FR-43\|Copilot\|next change`, and prints nothing on the register; the grounding names the four rows a tool's phase owns |
| 10 | Nit | `holds-now.yaml`, AJ10, among the plan's 49 lines | AJ10's open part names "WP5.15 to WP5.28", which includes this package and the retired numbers WP5.22 to WP5.26, so it is not strictly a line that "names only a delivered Phase 5 package" when item 1 runs | Fixed by the review turn: item 1 gives AJ10's value and says its range ends at this package; the value names AW1 and AW4 beside the earlier amendments |

Checked and found true: 276 rows with the counts D1's grounding gives, none `open`; the owner check prints nothing;
71 lines of `holds-now.yaml` hold `open:` beside the header's comment, and the plan's 49, 3 and 19 partition them, so
22 remain; `_status_of_ruling` and the gate's `decisions.py --check`; 41 capability rows, 31 present, one as ruled,
nine carried; the Qt search's two files; 32 screens and 4 states; 1,954 of 2,068 collected, 1,758 Tier 1, 220 Tier 2,
149 in `test_gui_screens.py`, 128 of them the grid; a dispatch without `full` takes mode `main` and is always
`code`; the `number stability on` section; `redraw.cjs`'s arguments and defaults; `render_shell.py --only 2wcd`
builds `cache/2wcd-<key>/project` beside the output directory; WP5.19's 297 / 380 ms; the twelve Appendix A rows
name 17 files and 13 tests, all resolving; 21 alpha sections of `CHANGELOG.md` and three lines that say "migration";
`CITATION.cff`, the README's two lines, `tag.yml`'s inputs and `release.yml`'s check; §8.1's Phase 4 gate ends
"Closed with v0.5.0". After the review turn's two fixes the plan holds 3,211 words, 1,489 outside *Grounding* and *Implementation
details*, 874 in *Implementation details*, and its In brief 275: each within its cap. `current.md` holds 696 words. The specification's four amended places (§8.1's GUI
row, §2.7, RSK-15, the design document's *Later tools*) say what AX1 rules, and REV-273's row and section say what
AX2 rules.

Not checked: the wheel's install time and size and the self-test's time (D3's last bullet), which need a build.

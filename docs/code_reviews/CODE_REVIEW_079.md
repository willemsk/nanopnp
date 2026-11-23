# Code review 079: the project re-planned, the rescoping round of §8.2.51

2026-11-23 · branch `ccr-a184c192-2cslg6` at `57f5702` on `main` (`9f735e9`) · scope: the plan commit's 37 files,
read from `git diff origin/main...HEAD`. Read in place: `.claude/skills/np-plan/` (`project.md`, `review.md`,
`rulings.md`, `amend.md`, `SKILL.md`), `.claude/skills/np-ship/wp.md`, the steward, `.claude/hooks/gate.sh`,
`.claude/scripts/decisions.py`, §2.7, §3, §7.5, §7.6, §8.1, §8.3, §8.4.4, records 49 to 51, `holds-now.yaml`, the
review register, the input note, the Phase 6 plan, the instructions audit's F3, `src/nanopnp/pipeline/checks.py`,
`tests/tier1/` and `tests/tier2/` by name · level: medium asked, high as the reviewer reports it, with `--fix` · status: completed.

Static review of a plan commit: no test and no `gate.sh` run. Read-only checks were run: `wc -w` on `current.md`
and its In brief; `git grep` for every live mention of Phase 11, v0.12 and the package numbers WP6.04 to WP6.18;
`git ls-remote --tags` for `v0.7*` and `copilot-host`; `clause.py VER-48`; the sums of §8.3. After the fixes
`decisions.py` was re-run, and `decisions.py --check`, `links.py` and `duplicates.py` pass. `current.md` holds 697
words and its In brief 248.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Important | §8.4.4's new rule; record 51, BA7 | The rule says a free restructure is safe while "every test of the push gate passes: Tiers 1 and 2, with the number-stability golden (VER-62)". `gate.sh run` runs the per-push selection, Tier 2 without `nightly` and `slow` (§7.6). Five of the eight Tier 2 files that hold a number-stability walk are `nightly`, `test_examples_02_classical.py` among them. A restructure can move a number on one of those and pass the gate; the nightly run finds it after the merge | Fixed in the wording: §8.4.4 and BA7 say what a push selects and that the other walks run nightly. Not fixed: whether a restructure of code a nightly walk solves must run that walk first. That narrows BA7 and is the author's |
| 2 | Important | Record 51, BA11; `holds-now.yaml` AZ3 and AV1; §3's NOTE on FR-35; REV-242, REV-254 | BA11 makes WP6.04 the ground-up review. Four live places still gave WP6.04 as the error base, one of them normative: §3's NOTE said the texts follow the rule "on the error base of WP6.04". A reader of `holds-now.yaml` found two packages under one number | Fixed: the five lines name the error base and the refusals by scope, with BA4 |
| 3 | Important | `holds-now.yaml` AM2 | "Phase 11 (the measurement)". BA5 moves the measurement against the published results to Phase 12, and NUM-04's NOTE was changed in this commit; the line that says where AM2 holds was not | Fixed |
| 4 | Important | §8.1, Phase 11's gate | The gate is "its own Tier 1 and Tier 2 tests (VER-19 to VER-22)". Those four and VAL-11 pass at this head (`tests/tier2/test_stokes_drag.py`, `test_maxwell_sphere.py`, `test_electrophoretic_mobility.py`, `test_force_routes.py`, `test_force_convergence.py`), on a body a benchmark geometry embeds (PHY-11). What the phase builds has no test named: an analyte in a generated region, which `pipeline/checks.py:_check_generation` refuses, and `ΔU` over a series of positions. The gate as written is met before the phase starts | Fixed: the row says which tests pass today and that `/np-plan phase 11` names the tests of what it builds |
| 5 | Nit | §8.3 and §8.1, Phase 6's provisional content | "About ten packages at the text and clean-up rate" gives 50 sessions, 30 to 60 agent hours and 80 touches at that rate (5, 3 to 6, 8). The rows hold 45 to 90 hours, which is 15 packages. The sum 53 to 106 and the In brief follow it. Phase 11's row names a "library rate" that §8.3 does not define; its numbers are the text and clean-up rate's | Fixed in the wording: the hours are those of the 15 drafted packages, whose content BA4 keeps; no number moved. Phase 11's row names the rate §8.3 defines |
| 6 | Nit | §7.5's first sentence | "No Tier 4 test exists before Phase 12", but BA5 has Phase 11's round ask for the PlyAB files, without which VAL-12 to VAL-14 "stay unmet". With them, a Tier 4 test would exist in Phase 11. §8.1's Phase 12 gate names VAL-07 to VAL-10 alone | Fixed: the sentence excepts VAL-12 to VAL-14 where that round places them |
| 7 | Nit | `.claude/skills/np-ship/wp.md`, step 4 | The new sentence says a restructure "is not wider". The sentence before it also sends each "architectural" finding to the author, and a restructure is one. BA7 says such a finding is not put to the author | Fixed: "is neither: make it and name it in the pull request" |
| 8 | Nit | Record 51, BA13's last cell | "None", while §8.4.4's new rule cites BA13 for its last sentence and `holds-now.yaml` gives BA13 as §8.4.4 | Fixed: the cell names the sentence |
| 9 | Nit | `current.md`, In brief | "Validation is now the twelfth phase": Phase 12 is the thirteenth, since the phases start at 0 | Fixed: "Phase 12" |
| 10 | Nit | `.claude/skills/steward/SKILL.md`, *Fixes stay in scope* | The audit's F3 cited this section beside `np-ship/wp.md`. BA7 changed the second and left "a change that widens the package … goes to the user first" here as it was | Not fixed: BA7 names an implementing session and a ship, and whether a CI fix may restructure is not ruled |
| 11 | Nit | `holds-now.yaml` T3, Z6, AC4, AM2, AY3, AZ2, AZ5, AZ6; the review register's rows for WP6.07 and WP6.13 to WP6.17; the Phase 6 plan | The input note says the numbers of AZ4 from WP6.04 "no longer hold". These lines still name them, and the axis package will take one | Not fixed: AZ7 gives the renumbering to `/np-plan amend 6`, the next step. Only the colliding WP6.04 was changed (finding 2) |
| 12 | Pre-existing | `docs/project/decisions.md`, the rows of BA4 and BA7 to BA9; `decisions.py:_package_of` | The page gives BA4 as ruled at WP6.04, BA7 and BA9 at WP6.02 and BA8 at WP6.01. All four are rulings of the round. The script takes the first `WP<n>` a decision's cell mentions | Not fixed: it is the script's rule, outside this commit |

## Checked and found true

`v0.7.0-alpha.1` to `v0.7.0-alpha.3` and `copilot-host` are published, and `CHANGELOG.md`'s head is
`[0.7.0-alpha.3]`. Record 51 has its front matter, heading, paragraph and table as `rulings.md` asks, the series
continues at BA, and the author chose the recommendation five times (BA2, BA8, BA9, BA11, BA13) and against it seven
(BA1, BA3 to BA7, BA12). `holds-now.yaml` has one line for each of BA1 to BA13, in order, and parses. Each clause a
row's last cell names is changed in the commit. §2.7, §3's Release column, §8.1, §8.3, Appendix A, `CHANGELOG.md`,
`CONTRIBUTING.md`, the README and the two workflows agree on v0.12 for Phase 11 and v0.13 for Phase 12; no live file
outside the history, the Phase 6 plan and the dated *Placed* lines gives Phase 11 or v0.12 as validation.
`src/nanopnp/pipeline/checks.py` says "FR-21, v0.12", which still holds. No requirement reads "a later phase".
§8.3's Phase 6 row sums to 65, 53 to 106 and 101. `structure/cavity.py:channel_axis`, REV-279's 0.22° to 0.62° and
VER-48 read as BA8 says; no golden walk and no example uses `axis: cavity`. The audit's F3 and WP6.02's Outcome on
REV-183 read as BA7 and BA9 say. VER-62's Tier 1 tests, VER-61 and VER-65 are in the per-push selection. The Phase 6
plan is unchanged, and `current.md` names `/np-plan project review` first, then `/np-plan amend 6`.

## Not assessed

- What the author answered at each of the thirteen questions: the session's transcript was not read, so each
  "the author chose" stands as the record gives it.
- The estimates of BA1, BA5, BA8 and BA10 beyond their arithmetic.
- Whether `/np-plan project` is the right level for the round after WP6.04, which BA11 marks as the plan's reading.

The author's thirteen rulings are unchanged by the fixes.

## After the review: the review turn's decisions

The review turn read each fix as a diff against the code and the records, and kept the nine. It then decided:

| # | Outcome |
|---|---|
| 1 | Confirmed against `gate.sh` and the markers: two of VER-62's seven walks run per push, examples 01 and 02's ePNP-NS leg. Put to the author, who ruled the push checks as written (§8.2.51 BA14); the fix's wording stands and no nightly walk is asked before a push |
| 4 | Confirmed: `pipeline/checks.py` refuses `geometry.analyte` in a generated region as "FR-21, v0.12" |
| 5 | Confirmed: the hours are kept at the 15 drafted packages' because BA4 keeps their content and merges only the packages |
| 6 | Kept, its sentence reworded to "except VAL-12 to VAL-14 where…"; the placement is an open decision of the input note, owned by `/np-plan phase 11` |
| 10 | Rejected. The steward's section opens "Fix what the failure needs", which bounds a CI fix whatever BA7 allows, and BA7 names an implementing session and a ship's review. The steward is unchanged |
| 11 | Carried as an open decision of the input note, owned by the next `/np-plan amend 6` |
| 12 | Put to the author, who ruled the fix now (§8.2.51 BA15). `decisions.py` gives a history ruling to a package only where its opening mark, *Added* or *Ruled*, names one; about 95 rows of the two generated pages change |

The round now holds fifteen rulings, BA1 to BA15. BA1 to BA13 are unchanged.

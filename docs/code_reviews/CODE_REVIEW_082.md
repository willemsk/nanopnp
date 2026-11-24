# Code review 082: WP6.04, the ground-up review

2026-11-24 · pull request 213, branch `ccr-2e0edb08-u4c476` at `0145fff` on `main` (`f862212`) · scope: the pull
request's 26 files, +3,600 and −101, read from `gh pr diff 213`; no file under `src/`, `tests/`, `data/` or
`examples/` · level: xhigh, with `--fix` · status: completed.

**Who reviewed.** The author ruled on 24 November 2026 that this package ships on Fable 5.2 in the session that
implemented it (§8.2.52 BB7), where BB5 had named Opus 5.5 in a new session. The reviewer therefore wrote what it
read. It checked each claim against a source outside its own memory: the code, the specification's clauses, the
agents' returned texts, the session's transcript and `git`.

Static review of prose: no test and no `gate.sh` run. Read-only checks were run: `clause.py` on 45 identifiers the
report cites; a script that counts the walk's 259 rows by verdict and by the designers' marks and checks each
identifier range against the specification; `grep` and `wc` for each code fact a card rests on; `git log` for the
order of the commits and the plan's ticks; the sums of every table of `evidence.md` and `method.md`; a
token-by-token comparison of the three designs, the three judgements and the three challenge reports with the
texts the agents returned; a recount of the main session's calls from its transcript; PHY-11 and PHY-12 evaluated
for the permittivity that REV-283 quotes. After the fixes `decisions.py` and `index_records.py` were re-run.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Important | The report, GU-13 (table and card); `walk.md`, §7.6; `challenge.md`, the answer on GU-12 and GU-13 | The card says that CI's legs install no browser and skip 142 of the 149 browser tests, and gives as its reason for waiting that the gate can skip the tests only once CI runs them. A pull request's `tests (tier1)` job installs Chromium and sets `NANOPNP_REQUIRE_BROWSER=1` (`.github/workflows/ci.yml`, lines 241 to 247, since WP5.02). Phase 5's report said it of run 837's platform legs, which run after a merge | Fixed: the card, the table row, the walk's row and the answer say where the tests run. The verdict stays change later, Phase 7, on the reason left, that Phase 7 rebuilds those tests; the second challenger's objection, that the gate could choose by path in Phase 6, is shown on the card as not met |
| 2 | Important | The report, group 11, GU-25's records; `challenge.md`, the answer on GU-25's records | The three newest plans' 3,885 to 4,779 words are set against a cap of 3,500. The cap counts a plan outside its Outcome annotations and allows a tenth over (`np-plan/wp.md`, *The caps*); the figures are `wc -w` of the whole files, and the challenger's own row asks for the net count | Fixed: net of the annotations the three hold 3,623, 3,728 and 4,099 words against 3,850, and the answer says what was corrected. WP6.04's plan held 3,684 at its approval |
| 3 | Important | The report's table, GU-15 | The row names FR-29, goal-oriented mesh adaptivity, as the clause the sensitivities move. The draft's row moved "NUM-33, FR-29" while the adjoint also replaced the error estimator; the challenge cut that link | Fixed: FR-41, the mutator's requirement, beside which the capability lands in Phase 9 |
| 4 | Important | `walk.md`, §2.7 v0.8 | The reason says that with the kernel's shape in Phase 6 the rebuild meets the designers' order, workbench after kernel. After the challenge the kernel is built in Phase 8, after the rebuild | Fixed: the row says that the keep goes against that order, and what Phase 6 gives the rebuild |
| 5 | Nit | `method.md`, *The main session's calls* | "None of the 57 `Read`, `Write`, `Edit` and `Bash` calls": the table lists 3, 12 and 51, which sum to 66. The transcript holds 3, 12 and 54 at the unblinding's commit, the three later ones the build and the commit | Fixed: 66 |
| 6 | Nit | `walk.md`, §2.7 post-1.0 | "The interview ranks three of the nine": the backlog's nine items hold 3D, the molecular link only as a toolkit that fits the corrections, and not inverse design | Fixed |
| 7 | Nit | The plan's In brief | 279 words after the commit that records BB7, against the 275 of `.claude/workflow/author.md` | Fixed: 275 |
| 8 | Nit | `walk.md`, BB5; the report's *Limits* | BB5's row reads "Spent at the ship"; BB7 amended it. The limits say that the main session wrote the report, and not that it also checked it | Fixed: the row names BB7 and the limits say who checked |
| 9 | Nit | `CHANGELOG.md`; the report's status line; the Phase 6 plan's WP6.04 heading; the plan's Status and Scope | Each cites §8.2.52 BB2 to BB6; BB7 is a ruling on this package | Fixed: BB7 |
| 10 | Nit | The report, *What stays open* | The seven trials are "each to become a row of the review register"; the pull request holds them as REV-281 to REV-287 | Fixed |
| 11 | Nit | The report, *What the guard showed*; the plan's Outcome | The first run was set aside "because one line of the pack still named the engine". `method.md` records a second fault, a line that listed the workbench's terms, by which the first was found | Fixed in both |
| 12 | Nit | `walk.md`, §8.4.4 (2) | "None better found" on a row that all three designers oppose | Fixed: §7.6's alternative, three systems on every change |
| 13 | Nit | `walk.md`, IF-01 | The report's GU-18 moves IF-01's text; the walk's row is a keep with no pointer | Fixed: a sentence that points to IF-03's row. The verdict and the counts stay |
| 14 | Nit | `evidence.md`, *Cited, not measured again* | REV-156's mesh is 16,562 elements here and 16,444 in the report, the walk and REV-282 | Fixed: the measured 16,444 and 761 s, with the title's figure beside them |
| 15 | Nit | `review-items.md`, REV-280 | A sentence starts with a lower-case link text | Fixed |

The report holds 5,497 words after the fixes, against 5,500. No verdict of the walk changed: 209 keep, 22 change
now, 16 change later, one drop, 9 add and 2 lacks not added.

## Checked and found true

The walk holds one row for each of IF-01 to IF-09, FR-01 to FR-44, QR-01 to QR-16, CON-01 to CON-14, N1 to N7,
ADR-001 to ADR-005, NUM-01 to NUM-34, BA1 to BA15 and BB1 to BB6, 259 rows in all, and its counts by verdict are
those its head, the report and the plan give, in each part. Of the 209 keeps 91 have a designer for and none
against, 64 no designer's mark and 54 a designer against. The rows that go against all three designers are the
eight and the five its two parts name. The guard's table agrees with the walk's marks: five rows of eleven where all
three chose today's, five where all three chose otherwise, one split.

Each design appendix equals the text its designer returned, token by token, but for the pack's path, which the
appendix says it writes as `<pack>`. The three judgements after the unblinding and the three challenge reports are
contained whole. The pack's word counts sum to 16,947 in 25 files; the designers' flagged calls are nine and their
web calls 27. The commits of the interview, the designs and the unblinding precede the evidence's, and each tick of
the plan names its item's commit.

`gui/` imports nine names from `physics/`, those the report lists. `CoupledModel` is lines 589 to 1346 of
`physics/models.py`, which holds 2,076. Eleven of the twenty subpackages import the engine. `Compile(` appears once
in `src/nanopnp`, and `TaskManager` nowhere. `io/variables.py`, `sweep/forecast.py` and `physics/stabilisation.py`
hold 678, 120 and 716 lines. `geometry.pore.shape` is `Literal["cylinder"]`; `inputs.profile` and
`numerics.mesh.size_scale` exist. Example 05 holds one case file. The engine's wheel holds
`ngsolve/solvers/mkl_pardiso.py`, which looks for `mkl_rt`; the installed version is 6.2.2606. Pint is held below
0.26. The workbench design's four spent sections hold about 3,000 of its 16,450 words.

The clauses read as the cards quote them: QR-11 and its four rows under IF-09, FR-03, CON-08, QR-07, FR-37, IF-01,
FR-42, FR-20, FR-40, FR-29, NUM-32, NUM-33, NUM-30, FR-11, IF-07, PHY-08, PHY-23, QR-16, CON-01, N1, NUM-16, NUM-18,
VER-62 and the benchmarks named. AZ1, AZ5, AZ8, AZ20, AZ21, BA1, BA3 and BA5 rule what the report says, BA3 with no
reason recorded. REV-156 measures 761 s, 62 % assembly and 24 % factorisation on 16,444 elements. By PHY-11 and
PHY-12 the fluid's relative permittivity is 77.6 at 0.05 M and 51 at 3 M, as REV-283 quotes. §8.3 holds the two
rates, and the sum of the proposals for Phase 6 follows from them: two and a half to three and a half small
packages. Every table of `evidence.md` sums as its text says.

## Not assessed

- The six survey tables of `technologies.md` against what the six agents returned, and each cell against its
  source. *Checked at the source* was read; the facts the cards use agree with it.
- The package index's records of 24 November (the releases and their Python floors): they were read then and are
  not fetched again.
- Whether a path rule for the browser tests would skip many pushes: GU-13's gain stays "not measured".
- The interview's five rounds against the dialog's own record.

## For the author

GU-13 is the one finding that bears on a ruling. With CI already running the browser tests, the review's reason
for waiting is only that Phase 7 rebuilds them; the second challenger asks for the change in Phase 6. The verdict
is left as it was and the objection is shown, because a verdict of the report is a proposal that the ruling round
decides (BA13), and the reviewer is the session that wrote it (§8.2.33 AI4; BB7).

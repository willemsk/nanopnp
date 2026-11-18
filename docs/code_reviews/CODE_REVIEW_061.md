# Code review 061: the fifth Phase 5 amendment, the meso suite and the performance package placed

2026-11-18 · PR #190, branch `claude/serene-pascal-dmnl60`, head `25130bf` on base `0c52f48` · scope: the amendment's
56 files. The Phase 5 plan's status, In brief, design decisions, WP5.19 to WP5.24, open decisions, supply rows,
verification rows and criterion 6 were read in full; ruling record §8.2.43; `holds-now.yaml`; §8.1's Phase 5 row and
§8.3's shell row; REV-244, REV-258 and REV-259; `current.md`; the record's 18 November section. The plan's claims were
checked against the code: `gui/web/screens.py` (the suites' tools), `core/stages.py` (the stage order),
`.claude/scripts/gui/redraw.cjs` (its address and flags), `tests/tier1/test_gui_screens.py`, and VER-60, VER-62,
VER-78, FR-31 and FR-33 · level: medium, with `--fix` · status: completed.

Static review of a plan commit: no test and no `gate.sh` ran during the review. The review turn gates afterwards.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Medium | Phase 5 plan, WP5.20 | The entry moves Charge on the mesh out of Study but does not name what is bound to its old place: VER-78 (a)'s suites and (m)'s `/study/charge`, `test_gui_screens.py`'s route, `redraw.cjs`'s hard-coded `/study/charge`, which WP5.22 runs, and the capability list's rows for Q14 to Q20 and Q24 to Q30 | Fixed: the entry names each to follow the moved tools; the verification row holds VER-78 as amended, each moved tool's page at its new address |
| 2 | Medium | Phase 5 plan, WP5.22 | `redraw.cjs --headed` is said to time Analysis's field and plot views, but the script only picks on the charge map; nothing extends it before the author's one GPU session | Fixed: the script gains Analysis's views first |
| 3 | Low | Phase 5 plan, Open decisions | A blank line before row 15 ended the table, so the meso suite's name did not render as a row | Fixed |
| 4 | Low | Phase 5 plan, WP5.22 | "The front end's share is fixed first" puts the fix before the measurement; AS2 and REV-258 measure first, then fix, the keyed walk first | Fixed: measured, then fixed, one keyed walk per pick first, and timed again |
| 5 | Low | `docs/plans/current.md` | Shortening the list of rulings not to be re-decided dropped rulings that bind the remaining packages: AI1 (a user's theme sets its contrast; the meso round's dark-theme question), the mesh read only through `deployed_mesh` (Charge map), AH1 (Analysis's outputs), §8.2.41, and AM1 and AM2 (WP5.23's documentation increment) | Fixed: restored in short form; 668 words, under the 700 cap |
| 6 | Low | Phase 5 plan, WP5.20; §8.1 | §8.1's deliverable still reads "five suites", and WP5.20's list of clauses to amend did not name it | Fixed: WP5.20 amends §8.1's Phase 5 deliverable with FR-31 (AR8) |
| 7 | Low | `review-items.md`, REV-258 and REV-259 | The edits left broken line wraps, one of which splits the code span `redraw.cjs --headed` | Fixed: reflowed |
| 8 | Low | Phase 5 plan, In brief | The cost of the five packages left (19 sessions, 23 to 41 agent hours, 54 touches) differs from §8.3's per-package rate for the same packages (30, 30 to 60, 50) | Not changed: the In brief states its basis, the four suites measured (§8.3: an estimate comes from measured comparable packages). §8.3's row carries the phase's planning rate, which the close reconciles |
| 9 | Low | Phase 5 plan | The plan is 6,390 words against phase.md's 1,500-word target; this amendment adds about 510 | Not changed: the excess predates this amendment (5,878 on `main`). Trimming the delivered packages' entries would rewrite the plan beyond this amendment |

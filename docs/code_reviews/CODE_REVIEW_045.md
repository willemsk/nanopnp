# Code review 045: WP5.12's plan, the knowledge base and the guide

2026-11-09 · branch `ccr-eb7edaa4-ck187i`, the plan commit `a457f32` on `f8960d1` · scope: the commit's 14 files,
read in full: `docs/plans/phase-5/wp5.12-the-knowledge-base-and-the-guide.md`, the Phase 5 plan and record,
`current.md`, the ruling record §8.2.38, `holds-now.yaml`, the history and specification indexes, the decisions page
· focus: each claim the plan makes about the code against the code at `a457f32`, each decision against
`SPECIFICATION.md` and the rulings, the verification row's object, the caps and sections of
`.claude/skills/np-plan/wp.md` and `rulings.md` · status: completed.

Static review (`/np-plan wp 5.12 review`, `/code-review medium --fix`). No test or gate ran; the review turn gates.
Probed and found to hold: the 164 AUD ids of Grounding D1's item lists equal the register's `your call` rows, no
id twice; the plan's SHALL command counts 517; `Electrolyte.from_parameter_file("willems2020_nacl").diffusivity("Na+",
5.3, 50.0)` is 8.1134e-10, 4.6e-5 from 8.113e-10; `markers.py` reports the 21 unfootnoted hits, the one missing test
(`log.md`:44) and `04/02`'s three `test_exclusion_shell.py` tests as Grounding D4 says; the thesis repository's
HEAD is `43d0f0f`; `materials/stage.py` keys stage 8 on `file_hash(correction_source(...))`; the 110
`## REV-nn:` headings and their unchanged slugs; the `epnpns` fixture the verification row's test reads. Caps after
the fixes: 3,017 words, 1,647 outside Grounding and Implementation details (cap 1,650), 526 in Implementation
details.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | High | AN1; plan item 2, Pointers, item 12; `holds-now.yaml` | AN1 and the plan move the sodium cap's oracle in §4.6 and the test only. VER-03's row in `specification/07-verification/02-tier-1.md` states `D_Na(5.3 M) = 8.13 × 10⁻¹⁰` "to four significant figures", and `knowledge/08-validation-benchmarks/01`'s `[tested:]` line states the same: after item 2 the test asserts 8.113e-10 at 10⁻³ against a clause that names 8.13 | Fixed: item 2, Grounding D2 and the Pointers name VER-03's row and `08/01`; AN1's clause cell and `holds-now.yaml` name VER-03; item 12's `holds-now` value too |
| 2 | Medium | Plan item 2; Grounding D2 | AUD-86 replaces §4.6's Evidence arithmetic with a link, while AUD-73 and AN1 put `D_Na = 8.11 × 10⁻¹⁰` in row 4's Evidence cell; and the link's anchor is `#…`, though the errata concept has one heading (`## 8.`) and its E1 to E5 are bold paragraphs with no anchor, so the implementer must choose | Fixed: the link names `#8-errata-in-the-source-with-the-arithmetic`, and row 4 keeps its cap values |
| 3 | Medium | Plan D5; Phase 5 plan *In brief* and *What the author supplies* | AL20 ruled an eight-row checklist of CODE_REVIEW_039 section 3's list (AUD-316, 343, 346, 371, 372 and three KST rows). The plan reads it as the readers' eight `unchecked` rows and gives the author six, cites "Ruled by the author", and rewrites the phase entry and `current.md`'s bullet, while the phase plan's In brief and supplies table still say eight. The grounding that AUD-316, 371 and 372 rest on neither source holds; narrowing a ruled deliverable is the author's (`wp.md`, *The author's*) | Ruled: the author chose six rows (§8.2.37 AM16); both phase-plan lines say six (REV-227), AL20 points to AM16, and the record quotes the old lines |
| 4 | Medium | Plan D6, item 10 | REV-226's acceptance says the fix is "a prose-only change `same_tree.py` confirms"; the refusal messages are string constants, which `same_tree.py` compares as code, so item 10's check reports them, departing silently from the accepted text | Fixed: Grounding D6 states the departure, and item 10 adds a `git diff` check that only citations change |
| 5 | Low | Plan D7 | REV-230 `accepted` "for the next change to that file": `review-findings.md` defines `accepted` as owned by a named later package | Fixed: `open` until a package is named |
| 6 | Low | Plan D5, D7 | REV-227's status is unstated, and item 9 moves every `## REV-nn:` heading to `###` before items 11 and 12 add four sections at an unstated level | Fixed: REV-227 `open`, REV-228 `accepted`, new sections at `###` |
| 7 | Low | §8.2.38 | `rulings.md`: "A ruling taken at a package's plan, on a record's date, is a row added to that record." §8.2.37 is dated 9 November 2026, and AL28 and AL29 went into §8.2.36 at WP5.10's plan the same way; AN1 to AN3 open a new record instead | Fixed in the review turn: the rule settles the filing, and the identifiers are not a user's choice. AN1 to AN3 are §8.2.37 AM13 to AM15, the review's two rulings AM16 and AM17; §8.2.38's file is gone and the ruling range reads §8.2.1 to §8.2.37 |
| 8 | Low | Phase 5 plan *Cost*; `current.md` | Twelve packages became eleven and WP5.11 is spent, but "about 70 sessions, 60 to 120 hours" stand unchanged in both | No change: WP5.11 measured 1.6 agent hours and 9 touches, so "about 70 sessions, 60 to 120 hours" still holds at its precision |
| 9 | Low | Plan *Grounding* D4 | Cites line numbers (`07/02`:123, `log.md` line 117) where `wp.md` says "Cite symbols, not line numbers, which drift" | Recorded: Markdown targets have no symbols, and `markers.py` reports by line, so the lines are the check's own key |
| 10 | Low | Phase 5 plan WP5.12 entry | "The 164 findings filed under `knowledge/` and `docs/`" includes specification rows (AUD-73, 86, 90, 91, 95) and `src/` rows (AUD-216, 351) | Fixed in the review turn: "The 164 findings WP5.11 left, most filed under `knowledge/` and `docs/`" |
| 11 | Low | Plan *Execution brief* | The main session runs on Sonnet while items 2 and 3 edit §4.6 and §6's mirrors; AM8 moved WP5.11 to Opus because such edits fail silently, and kept Sonnet for every other package | Ruled: the author chose Opus at high effort for the main session (§8.2.37 AM17); the Execution brief says so |

`decisions.py` re-run after the fixes; `decisions.py --check` passes.

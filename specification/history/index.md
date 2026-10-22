---
okf_version: "0.2"
---

# History of the specification

The dated rulings of the author and the Phase 0 exit criteria, moved here verbatim from §8.2 of the
specification. Read them when the reason behind a rule is wanted, not by default: every ruling's
effect is in a current clause or in §8.4, unless the ruling is spent, superseded or still open, and `uv run .claude/scripts/clause.py <identifier>` prints a
clause and, after it, every ruling row that names it. The rulings are lettered, one letter per dated record, and numbered
within it (A1, B3, R10).

* [8.2 Phase 0 exit criteria](00-phase-0-exit-criteria.md) - States the four Phase 0 exit criteria, all four of which SHALL be met.
* [8.2.1 Amendments to Phase 0, agreed 19 August 2026](01-amendments-to-phase-0-agreed-19-august-2026.md) - Records the amendments to Phase 0 agreed on 19 August 2026, with the consequence of each.
* [8.2.2 Phase 2 decisions, agreed 24 September 2026](02-phase-2-decisions-agreed-24-september-2026.md) - Records the author's Phase 2 rulings, agreed 24 September 2026, and the commit that amends any clause each changes.
* [8.2.3 Phase 1 exit, agreed 24 September 2026](03-phase-1-exit-agreed-24-september-2026.md) - Records the agreed Phase 1 exit gate of §8.1 and the end-of-phase report that measures the phase against it, dated 24 September 2026.
* [8.2.4 Phase 2 exit and Phase 3 decisions, agreed 30 September 2026](04-phase-2-exit-and-phase-3-decisions-agreed-30-septe.md) - Records the author's rulings closing Phase 2 and planning Phase 3, agreed 30 September 2026.
* [8.2.5 Phase 3 exit and the Phase 4 release, agreed 3 October 2026](05-phase-3-exit-and-the-phase-4-release-agreed-3-octo.md) - Records the author's rulings on the Phase 3 exit and Phase 4 release, agreed 3 October 2026, taken while planning WP34.
* [8.2.6 Phases 4 to 6 re-planned, agreed 4 October 2026](06-phases-4-to-6-re-planned-agreed-4-october-2026.md) - Records the author's rulings re-planning Phases 4 to 6, agreed 4 October 2026, taken while WP34 was still planned.
* [8.2.7 Phase 4 decisions, agreed 5 October 2026](07-phase-4-decisions-agreed-5-october-2026.md) - Records the author's rulings on Phase 4 decisions, agreed 5 October 2026, taken after Phase 3 closed as v0.4.0.
* [8.2.8 Phase 4 rulings on the modularity report, agreed 5 October 2026](08-phase-4-rulings-on-the-modularity-report-agreed-5.md) - Records the author's rulings on the Phase 4 modularity report's 17 findings, agreed 5 October 2026, with later amendments as H10 to H12.
* [8.2.9 Phase 4 amended: the review register planned, agreed 6 October 2026](09-phase-4-amended-the-review-register-planned-agreed.md) - Records the rulings deciding when accepted review items land and how the 43 items left open are ruled, agreed 6 October 2026.
* [8.2.10 Phase 4 amended: the development loop, agreed 11 October 2026](10-phase-4-amended-the-development-loop-agreed-11-oct.md) - Records the author's rulings on the development loop, agreed 11 October 2026, from measured commit-hook and push-gate timings.
* [8.2.11 Phase 4 amended: the development loop simplified, agreed 13 October 2026](11-phase-4-amended-the-development-loop-simplified-ag.md) - Records the rulings simplifying the development loop, agreed 13 October 2026, on WP43's measured hook, gate and session costs.
* [8.2.12 Phase 4 amended: the architecture review checked, agreed 18 October 2026](12-phase-4-amended-the-architecture-review-checked-ag.md) - Records the rulings on an external architecture review's eighteen proposed packages, agreed 18 October 2026, each claim checked against the code.
* [8.2.13 Phase 4 amended: the test scope, agreed 18 October 2026](13-phase-4-amended-the-test-scope-agreed-18-october-2.md) - Records the rulings on the test scope, agreed 18 October 2026, after measuring about 1,880 test functions.
* [8.2.14 Phase 4 amended: the plotting library and the notebooks, agreed 22 October 2026](14-phase-4-amended-the-plotting-library-and-the-noteb.md) - Records the rulings on the plotting library and notebooks, agreed 22 October 2026, prompted by REV-123.
* [8.2.15 The work-package plan grounded in the code, agreed 22 October 2026](15-the-work-package-plan-grounded-in-the-code-agreed.md) - Records the ruling on WP51's plan, agreed 22 October 2026, which read the plan against the code, finding points an implementer could guess at.
* [8.2.16 Phase 4 amended: the specification and the workflow restructured, agreed 22 October 2026](16-phase-4-amended-the-specification-and-the-workflow.md) - Records the rulings on the specification's restructuring and the workflow, agreed 22 October 2026, after WP51 merged.

## Where each ruling holds now

Each ruling is in a current clause (named), a rule of §8.4 (`§8.4.k`), `superseded by` a later one, `open` until a named package or session rules, or `spent`: a one-time act the record keeps.

* A1 - FR-21, FR-22, §8.1
* A2 - spent
* A3 - spent
* A4 - ADR-004 packaging NOTE, VER-55
* B1 - spent
* B2 - VAL-05
* B3 - superseded by G6
* B4 - QR-09, §2.5
* B5 - §5.2 stage 3, §5.2.1
* B6 - OPN-02
* B7 - §8.1 NOTE
* B8 - ADR-004 packaging NOTE, VER-55
* B9 - §5.3.1 NOTE on `geometry.contour`
* B10 - IF-05 NOTE on length units, VER-49
* C1 - spent
* C2 - QR-06
* D1 - superseded by E2 and F1
* D2 - PHY-16, PHY-18, §5.2 stage 7
* D3 - VAL-06, §2.6
* D4 - §5.3.1 NOTE on `inputs:`
* D5 - FR-15
* D6 - QR-02, VAL-16, VAL-17, §7.4
* D7 - spent
* E1 - spent
* E2 - §2.7
* E3 - OPN-07, VAL-03
* E4 - NUM-07 NOTE
* E5 - §8.4.1
* F1 - §2.7, §8.1
* F2 - §2.7 Versioning NOTE
* F3 - spent (§8.1)
* F4 - IF-01 NOTE
* F5 - §8.1, RSK-15
* F6 - §11
* G1 - spent
* G2 - spent (§8.1)
* G3 - spent; its ratchet superseded by N3
* G4 - superseded by N3
* G5 - spent
* G6 - §5.3.1 NOTE on the compatibility rule
* G7 - §8.4.6; its push-gate execution superseded by N4
* G8 - superseded by N3
* G9 - spent
* G10 - VER-62
* G11 - §8.4.1
* G12 - spent
* H1 - spent
* H2 - open: the user-testing sessions rule `MOD-11`
* H3 - QR-13, §5.4.1 NOTE, VER-65
* H4 - spent (deferred to Phase 5)
* H5 - spent (post-1.0)
* H6 - VER-61
* H7 - spent
* H8 - spent
* H9 - superseded by I5
* H10 - spent (deferred to Phase 5)
* H11 - §5.1, VER-61, VER-65
* H12 - §8.4.6
* I1 - spent
* I2 - spent
* I3 - spent
* I4 - VER-62
* I5 - §8.3
* J1 - spent
* J2 - superseded by L2
* J3 - superseded by L3
* J4 - §7.6
* J5 - §8.4.2
* J6 - §8.4.2, OPN-09
* J7 - superseded by L3 and L8
* J8 - superseded by L6
* J9 - §8.4.4
* J10 - superseded by N4
* J11 - superseded by L8
* J12 - §8.3
* L1 - spent
* L2 - §7.6
* L3 - §7.6, §8.4.2
* L4 - §8.4.2
* L5 - superseded by N3
* L6 - §8.4.5
* L7 - §8.4.4
* L8 - spent
* L9 - §8.4.5
* L10 - §8.4.2
* M1 - spent
* M2 - VER-76
* M3 - ADR-004, CON-09, §8.1
* M4 - spent
* M5 - §8.3
* N1 - §7.1 to §7.3, §8.4.3
* N2 - §7.6
* N3 - §7.1, §7.2, §7.3, Appendix A
* N4 - §7.6
* N5 - §8.4.3
* N6 - spent
* N7 - §8.3
* P1 - superseded by R1
* P2 - FR-30
* P3 - §5.1
* P4 - FR-30
* P5 - open: WP54 revises the notebooks
* P6 - FR-30
* P7 - §8.3
* P8 - spent
* P9 - spent
* P10 - §5.3.1 NOTE on `numerics.mesh`, VER-53
* Q1 - §8.4.4
* R1 - spent
* R2 - §11
* R3 - §8.4.4
* R4 - §8.4.4
* R5 - open: WP53 rebuilds the commands
* R6 - §8.4.5
* R7 - open: WP53 changes the session-start hook
* R8 - open: WP54 sets its own scope
* R9 - spent
* R10 - spent
* R11 - §8.4.4, §8.4.5

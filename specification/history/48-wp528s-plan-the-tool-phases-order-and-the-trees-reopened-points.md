---
type: Ruling Record
title: "8.2.48 WP5.28's plan: the tool phases' order handed to Phase 6's scope round, the tree's reopened points owned by its package, and the Windows leg carried, agreed 22 November 2026"
description: "Records the author's rulings at WP5.28's plan, the close of Phase 5: the order of the three tool phases against Phase 6 is set at Phase 6's scope round, not at Phase 5's close; the four points the tree round's verdicts reopened are accepted and owned by Phase 6's tree of results, put to the author at its design round; and, at WP5.28's implementation, v0.6.0 is released with the Windows test leg failing, the gap carried to Phase 6."
---

#### 8.2.48 WP5.28's plan: the tool phases' order handed to Phase 6's scope round, the tree's reopened points owned by its package, and the Windows leg carried, agreed 22 November 2026

Rulings by the author on 22 November 2026, at `/np-plan wp 5.28`, after WP5.27's merge. The survey for the close found
two things that only the author could settle before the phase closes. The Phase 5 plan's open decision 5, the order of
the tool phases, was the author's at the close or handed by it to Phase 6's scope round. REV-273 was the one row of the
review register still `open`, and a phase does not close over an open row (§8.4.6). Two questions went through
`AskUserQuestion` in one call, each with its context, options and previews, after a brief of what the plan had settled.
The author chose the recommendation in both. The letter series continues at AX.

AX3 was ruled on the same day at `/np-implement wp 5.28`. The run the close dispatched for its report (run 837 on
`13f72c3`) passed on Linux and macOS, and its Windows leg met its 40-minute limit: one test failed at about a third of
the run, and the last tests did not finish. `main`'s Windows leg had ended the same way on every push run with tests
since run 733 on 10 November, and on every nightly run since; a pull request's CI tests on Linux alone, so no package
saw it. One question went through `AskUserQuestion`, with three options: fix it in the close (the recommendation),
release and carry the gap, or a separate fix package first. The author chose to release and carry the gap.

| # | Decision | Consequence | Clause changed, and when |
|---|---|---|---|
| AX1 *Ruled by AY2.* | **The tool phases are numbered and ordered at Phase 6's scope round.** S7 set the order of the physics composer, the structural mutator and the sketcher against validation "when Phase 5 closes". The author has since ruled that Phase 6 opens with a round that plans the later phases again (REV-272). The author chose "Phase 6's scope round" (*the recommendation*), over fixing the order at the close: validation first, then the composer, the structural mutator and the sketcher | The close orders nothing and reports the hand-over. The Phase 5 plan's open decision 5 closes. Phase 6's scope round gains the question. A requirement tagged for a tool phase keeps its name until that round numbers the phase. S7's other parts stand: each tool is a library capability first and a phase of its own, and validation is not held behind the tools | §8.1's GUI row; §2.7's sentence on a requirement's release; RSK-15's mitigation; the design document's *Later tools*; the Phase 5 plan, in this commit; S7's ordering at the close is amended by this row; open: Phase 6's scope round |
| AX2 | **The tree round's four reopened points are Phase 6's tree of results'.** REV-273 holds the points the verdicts on the tree's boards reopened: every run in Data, an editor-like view area, a properties pane of its own and the render's size. The author chose "Phase 6's tree round" (*the recommendation*), over ruling the four points now, on today's frame and with no new boards | REV-273 is `accepted`, owned by Phase 6's tree of results, and its four points are put to the author at that package's design round, on boards drawn for the restructured frame. No row of the review register is `open` at v0.6.0. It would be ruled earlier if Phase 6's scope round needs the layout to size the foundations | REV-273's row and section, in this commit; open: Phase 6's tree of results |
| AX3 *Its placement in V&V in CI is amended by AY4.* | **v0.6.0 is released with the Windows test leg failing; the gap is carried.** Phase 5's gate asks that Tiers 1 and 2 pass, and the Phase 5 plan's criterion 1 adds "no waiver". Tiers 1 and 2 pass on Linux and macOS; on Windows one test fails and the run meets its limit. The author chose "Release, carry the gap", over fixing it in the close (*the recommendation*) or in a separate package first | The close reports criterion 1 met on Linux and macOS and not on Windows, a waiver the author ruled. REV-277 holds the failing test and the stall, for Phase 6's V&V in CI, placed by its scope round. `CHANGELOG.md`'s `[0.6.0]` says the Windows leg is untested since 10 November 2026. A Windows user may meet a fault the tests would have found | §8.1's Phase 5 gate; the Phase 5 plan's criterion 1; REV-277's row and section, in this commit; open: Phase 6's V&V in CI |

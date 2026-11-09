---
type: Ruling Record
title: "8.2.38 WP5.12's plan: the sodium cap's test, the idea notes and the site's register links, agreed 9 November 2026"
description: "Records the author's rulings at WP5.12's plan on the three CODE_REVIEW_039 findings filed in knowledge/ and docs/ whose edits touch a number a test reads or a decision: the Tier 1 test of the sodium diffusivity cap is tightened to the value the governing coefficients give; three ideas the knowledge base records without a requirement move to one open item after v1.0; and the site's dead links from the registers to the plans and reviews wait for the guide package, WP5.21."
---

#### 8.2.38 WP5.12's plan: the sodium cap's test, the idea notes and the site's register links, agreed 9 November 2026

Rulings by the author on 9 November 2026, at `/np-plan wp 5.12`, after WP5.11's merge (PR #173). AL21
sends to the author each finding of CODE_REVIEW_039 whose edit touches a rule, a number or a decision. The
session checked the 164 findings still `your call` against the tree at `f8960d1` (every one stands, six in
part) and against the code, and sorted out three whose edits do not follow from the code, a clause, a
ruling or the source: a test's target, ideas with no requirement behind them, and a change to how the site
is built. It put them through `AskUserQuestion` in one call, each question with its context, options and
previews; the author took each recommendation. The other findings that touch a number follow the code, a
clause, a ruling or the source, and land without a round (the WP5.12 plan, D2). The letter series continues
at AN.

| # | Decision | Consequence | Clause changed, and when |
|---|---|---|---|
| AN1 | **The sodium diffusivity cap's test is tightened** (AUD-73), as recommended, against the text alone and against an open item: §4.6's erratum 4 and the errata concept give `D_Na(5.3 M) = 8.11 × 10⁻¹⁰ m² s⁻¹`, the value the governing coefficients give (8.113 × 10⁻¹⁰), and `test_ver03_bulk_properties_at_the_validity_limit` checks 8.113 × 10⁻¹⁰ at a relative 10⁻³, as its neighbours check theirs | The guard catches a 0.1 % drift of the sodium cap; WP5.12 changes one Tier 1 test, and no result moves | §4.6; open: WP5.12 |
| AN2 | **Three ideas the knowledge base records without a requirement move to one open item for after v1.0** (AUD-357, AUD-192), as recommended, against deleting them and against leaving them: a solve-time print of `D_i/μ_i` against `V_T`; an axial force sweep that would resolve the several minima the measured current levels imply; and a test that `N_eo` depends only on the analyte's size and shape | The knowledge files state facts only, as `knowledge/00-orientation/04` asks, and the ideas stay visible to the planning of v1.0 | `docs/project/review-findings.md`; open: WP5.12 |
| AN3 | **The site's dead links from the registers to the plans and reviews wait for the guide package** (AUD-14), as recommended, against a change to `docs/scripts/generate.py` here and against absolute links: the site excludes `docs/plans/` and `docs/code_reviews/`, so about 150 links of `docs/project/` lead nowhere on the site, while they resolve in the repository | An open item owned by WP5.21, which rewrites the guide and changes the site; the link check keeps checking the relative links meanwhile | open: WP5.21 |

---
type: Ruling Record
title: "8.2.28 Phase 5 amended: the library packages, agreed 1 November 2026"
description: "Records the author's rulings at the first amendment of Phase 5: the four library packages that need no front-end stack are ordered now, after the spike, while the shell packages, the sweep's design round and REV-136's cut line wait for a second amendment; the stage-5 region interface joins the Geometry tool's package, and the review's QoI seam joins the outputs registry."
---

#### 8.2.28 Phase 5 amended: the library packages, agreed 1 November 2026

Rulings by the author on 1 November 2026, in the session that took the architecture review into Phase 4 (§8.2.27).
WP5.01 is merged and WP5.02, the spike, starts after `v0.5.0`. §8.2.17 S14 keeps every later package provisional until
`/np-plan amend 5`, and §8.2.19 U4 runs the sweep's design round in it only after WP5.02 has chosen the stack, so the
first question was how much this amendment settles. Five questions were put through `AskUserQuestion` in two calls:
the scope, the spike's place, REV-170 and the library order; then the review's QoI seam. The author took the
recommendation on all five. The letter series continues at AD.

| # | Decision | Consequence | Clause changed, and when |
|---|---|---|---|
| AD1 | **This amendment plans the library packages that need no front-end stack**: protonation before the density (U2), the charge mutator's library step (FR-38), named models and study overrides in the case (WB-11, FR-39), and the outputs and steric registries (MOD-09, T4). The shell packages, the sweep's design round (U4), REV-136's v0.6 cut line (U3) and the phase estimate wait for a second `/np-plan amend 5` after WP5.02's framework ruling | Four packages are ordered and can be planned with `/np-plan wp`; nothing about a screen is planned before the stack is known | The Phase 5 plan, in this commit |
| AD2 | **The spike comes first**: WP5.02, then the library packages from WP5.03 | The framework ruling comes earliest, and anything the spike shows the server needs from the library (an event stream, a project folder) can join the library packages before they are planned | The Phase 5 plan, in this commit |
| AD3 | **The library packages run in this order**: WP5.03, protonation before the density; WP5.04, the charge mutator's library step; WP5.05, named models and study overrides in the case; WP5.06, the outputs and steric registries. Each takes `v0.6.0-alpha.N` (S19) | The physics lands first, with U2 before the mutator as U2 requires; the two case-schema changes land last and adjacent, each taking the release's schema identifier (G6) | The Phase 5 plan, in this commit; PHY-16, FR-04 and §5.2's stage 2 and 7 rows in WP5.03 (U2) |
| AD4 | **REV-170, the stage-5 region interface, lands in the shell package that builds the Continuum suite's Geometry tool, library step first** (*places AC3*). REV-121 stays with the package that surfaces structure preparation, as Z5 rules | The interface is fixed by its first real consumer; the sketcher phase (FR-42) adapts to it. VER-62's mesh hash is checked in that package | REV-170's row; the Phase 5 plan, in this commit |
| AD5 | **The review's QoI seam rides with MOD-09** (*amends AC4 for that part*): WP5.06 takes one QoI extraction interface and one boundary-existence check shared by `physics/distance.py` and the three `post/` modules, while it builds the outputs registry. REV-171 keeps the cost items, the coefficient expressions among them, for Phase 6's measurement | The module WP5.06 rewrites anyway is consolidated once; no cost item is fixed without its measurement (§8.2.12 M2) | REV-171's row; the Phase 5 plan, in this commit |

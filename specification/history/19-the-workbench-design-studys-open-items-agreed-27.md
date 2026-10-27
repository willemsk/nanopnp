---
type: Ruling Record
title: "8.2.19 The workbench design study's open items, agreed 27 October 2026"
description: "Records the author's rulings on the review rows WP5.01 left open: the Qt Result tab, protonation before the density, the library capabilities and the sweep's design round, the rows WP5.02 owns, and two items of its review."
---

#### 8.2.19 The workbench design study's open items, agreed 27 October 2026

Rulings by the author, taken through `AskUserQuestion` after WP5.01 was delivered, on the review rows
it left open (REV-134 to REV-139 and REV-141). Four questions came first. Moving protonation before the
density raised two more, its validated default and its owner, asked with the owners proposed for the
rows WP5.02 holds. The author chose against the recommendation twice: to carry REV-134 rather than fix
it before the user-testing sessions, and to move protonation before the geometry stages rather than
keep the order and measure. U6 and U7 came after, from `/np-ship`'s review of WP5.01 (REV-142, REV-143), each
as recommended. The letter series continues at U.

| # | Decision | Consequence | Clause changed, and when |
|---|---|---|---|
| U1 | **REV-134 is carried until Qt leaves.** The Qt Result tab keeps printing the stored float wrapper in `v0.5.0`; the browser shell reads the numbers through `plot/data.py` and replaces it | The user-testing sessions of Phase 4 meet the wrapper on the Result tab, and read the numbers from the command line or the run record. No `src/` change before `v0.5.0` | The register, in this commit; closed by the package that removes Qt |
| U2 | **Protonation moves before the geometry stages, and the protonated density is the validated default.** Stage 2 smears the protonated frames, so a protonation state or a charge-level variant (§8.2.17 S4) moves the density, the contour and the mesh; smearing the hydrogens as loaded, as the reference did from its MD frames, is a switch away from it that the reference-reproduction cases set | A library package in Phase 5, after WP5.02 and before the charge mutator, set by `/np-plan amend 5`. A walk truncated at the mesh then protonates, about a minute per frame of a ClyA dodecamer (WP27). The VAL-03 golden and the Tier 3 cases carry the switch, so their numbers do not move | A NOTE beside PHY-16 step 3, in this commit; PHY-16, FR-04 and §5.2's stage 2 and 7 rows when the package lands |
| U3 | **REV-136's library capabilities are ordered by `/np-plan amend 5`**, as proposed: each becomes a library package with its Tier 1 and 2 tests before the shell surfaces it, or moves to a later phase, the author ruling the cut line in that amendment | RSK-15 and §8.2.17 S7 hold for each | The register, in this commit; open: `/np-plan amend 5` |
| U4 | **The sweep's design round runs in `/np-plan amend 5`**, as a `/np-gui grill` after WP5.02 has chosen the stack (REV-139). Its library capabilities, user-defined variables in a case (a case-schema change) and the stages a value invalidates, join U3's packages | Mockup A's round-2 sweep stays a first take until then | The register, in this commit; open: `/np-plan amend 5` |
| U5 | **WP5.02 owns REV-137, REV-138 and REV-141**, as proposed: it names the renderer for each view and checks the explorer's controls against `webgui`'s interface, a second renderer's licence coming to the author under CON-09; it extends `/np-gui render` to measure non-text contrast; and it restates CON-08 and CON-11 for an installed workbench beside ADR-004 | WP5.02's plan cites each row; until REV-138 lands a review states non-text contrast as not measured | The register, in this commit; open: WP5.02 |
| U6 | **The charge-level mutator edits a residue's charge and radius as well as its protonation**, as §8.2.17 S4 rules: FR-38 had kept only the protonation state, with no ruling for the cut (REV-142) | The Charge edit tool offers the three edits, each saved as a variant shown as its difference from its parent; all ride on stage 7's PQR step | FR-38 and the design document's Charge edit row, in this commit |
| U7 | **The light theme's control edge on a selected row is WP5.02's**: `--control-edge` on `--sel` is 2.80:1, under WCAG 2.2 1.4.11's 3:1 (REV-143). The token changes, and the pages are rendered again, with REV-138's non-text contrast measure | The mockups stay as published; `tokens.css` keeps its value until then | The register, in this commit; open: WP5.02 |

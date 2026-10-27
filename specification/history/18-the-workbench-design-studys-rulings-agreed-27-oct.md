---
type: Ruling Record
title: "8.2.18 The workbench design study's rulings, agreed 27 October 2026"
description: "Records the author's rulings at the end of WP5.01: the review rows and modularity findings inherited by the Phase 5 shell, what partial protonation means, and the look-and-feel notes taken from the galleries."
---

#### 8.2.18 The workbench design study's rulings, agreed 27 October 2026

Rulings by the author, taken through `AskUserQuestion` at WP5.01's item 16, after the design document
(`docs/design/workbench.md`) proposed a ruling for each row the Phase 5 shell inherits (Phase 5 open
decision 3; WP5.01 D6). The first four questions put those proposals in groups; three more asked what
two of the author's marks on the mockups meant (REV-140) and whether the rulings taken from the
author's notes on the galleries, WB-30 to WB-32, stood. On the last, the author answered in prose: "I
think many of these should fall under user settings or even a "theme" approach. The mouse wheel not
changing a field was not a literal constraint, just an annoyance that we should address in one way or
another." The letter series continues at T.

| # | Decision | Consequence | Clause changed, and when |
|---|---|---|---|
| T1 | **The rows bound to the Qt bundle or the Qt code are `wontfix`, and what they still ask is carried into the workbench**: REV-20, REV-31, REV-65, REV-56 and MOD-18 | Nothing frozen or bundled remains once Qt leaves (§8.2.17 S12). The Contour tool checks its edits off the interface's thread and asks before discarding one (REV-56); the workbench lists stages from the registry, a stage without a view of its own showing its record and verdict (MOD-18) | The registers, in this commit; the design document's *Inherited rows* |
| T2 | **The rows the workbench's packages fix keep the owners the design document proposed**: REV-28 and REV-30 the Analysis package; REV-32 the project-folder package; REV-39 the Continuum package; REV-52 the first shell package, library first; REV-62 the named-model capability (REV-136); MOD-13's command-line part the package that adds `nanopnp gui` | `/np-plan amend 5` carries each row into the package named | The registers, in this commit; open until the packages land |
| T3 | **REV-41, REV-45 and REV-67 go to later work as proposed**: REV-41's `prepare` command with structure preparation (FR-37), `upto` on reproduce with the Study package, its region export with FR-28; REV-45 with FR-28, v0.7; REV-67 with the composer phase and MOD-11 | v0.6's scope does not grow for them | The registers, in this commit |
| T4 | **MOD-09 comes into v0.6.** The author chose to "Bring MOD-09 into v0.6" over deferring it to the composer: the outputs, and the steric models the finding names beside them, become registries in a Phase 5 library package, so a new quantity of interest needs no edit of the case schema | A library package joins REV-136's in Phase 5, before the study's outputs are offered in the workbench; a case-schema change after `v0.5.0` (§8.2.17 S1) | The registers, in this commit; open: `/np-plan amend 5` |
| T5 | **REV-114 is fixed by WP5.01**: the shell's gating clauses are restated for the browser shell as NOTEs beside them | The package that removes Qt makes the NOTEs the text (§8.2.17 S17) | The register, in this commit |
| T6 | **"Partial protonation" means a fractional charge at the pH**: each titratable group carrying its charge averaged over its states at the pH, from its pKa | A physics change: a switch away from the validated default of PHY-16 step 3, whose text, knowledge-base concept and tests come with its library package. It is a later capability; v0.6's Protonation tool shows it with the later-phase banner | FR-43, tagged for a later phase, in this commit |
| T7 | **The `change` mark on the Protein geometry screen was a slip** | The screen stands as `fine`; REV-140 is fixed with T6 | The mockups' review record, in this commit |
| T8 | **WB-30 to WB-32 are restated.** The 3D view's background and the spacing are user settings within a theme approach, not fixed rulings of the tokens; the mouse wheel "was not a literal constraint, just an annoyance that we should address in one way or another" | `tokens.css` is the default theme; a user adjusts or chooses a theme (its colours, density, spacing and the 3D view's background), saved per user. WB-32 keeps the aim, no setting hidden and none changed by accident, and leaves the means to the shell's package | FR-34 and the design document's WB-30 to WB-32, in this commit |

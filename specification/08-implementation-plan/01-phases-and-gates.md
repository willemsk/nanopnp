---
type: Specification
title: "8.1 Phases and gates"
description: "Lists each implementation phase with its deliverable, gate and estimate, from the Phase 0 spike onwards."
---

### 8.1 Phases and gates

| Phase | Deliverable | Gate | Estimate |
|---|---|---|---|
| 0. Spike | Coupled ePNP-NS on an analytic cylindrical pore; continuation ladder; Tier 1 and Tier 2 suites (§8.2.1) | §8.2 exit criteria, as amended by §8.2.1 | 3–5 weeks |
| 1. Solver core | Production solver on an externally supplied mesh, full QoI extraction, frozen case-file schema, sweep runner | Tier 1 and Tier 2 pass; Tier 3 enabled and differences attributed; met as amended by §8.2.3 | 6–10 weeks |
| 2. Geometry pipeline | Structure and trajectory ingestion, density, symmetry reduction, contour, CAD, mesh | VAL-05: the auto-generated mesh reproduces the hand-conditioned reference geometry; met as amended by §8.2.4 D7 | 8–12 weeks |
| 3. Charge pipeline | PDB2PQR to smeared volumetric `ρ_fixed` and dielectric field | VER-01, VER-02 and VAL-06 pass | 3–5 weeks |
| 4. Polish and user testing | The modularity report and the refactors the author accepted from it; the knowledge base as an Open Knowledge Format bundle; a faster development loop; a plotting library and notebooks over the API; a user-testing pass over the physics, the numerics, the Python API and the command line; the specification and the plans split into a current state and a history; v0.5 | The modularity report and the user-testing findings log closed, each finding resolved or deferred by the author's ruling; the number-stability golden unmoved (VER-62); the development loop's timings reported; Tiers 1 and 2 pass. Closed with v0.5.0 | 4–6 weeks |
| 5. Graphical interface | A design and requirements document with mockups for the whole workbench, a visual-feedback workflow, then the browser workbench over the capabilities the library already has, with its suite, tool and live-view architecture, six suites building and using the project's molecular, continuum and physics models, the charge-level mutator, and structure preparation, a library capability first, replacing the Qt shell (§8.2.12 M3; §8.2.17 S2, S4, S7; the design document's WB-01, WB-02, WB-14, WB-34; §8.2.34 AJ2; §8.2.42 AR8); v0.6 (§8.2.6 F5). The tree of results, the structure's layers, the performance package, the polish pass and the guided route with new models are Phase 7's, and the library's refusals Phase 6's (§8.2.47 AW1; §8.2.49 AY1) | The shell's gating clauses as the design document restates them; every capability of the Qt shell present before it leaves, a vertex's typed move standing for its drag and five details carried (§8.2.47 AW7, AW11; REV-274); each v0.6 requirement checked; Tiers 1 and 2 pass on Linux and macOS (§8.2.17 S13), the Windows leg's failure carried to Phase 6's first package (§8.2.48 AX3; §8.2.49 AY4; REV-277). QR-10 gates no phase before v1.0: it is observed on v1.0's release candidate (§8.2.47 AW2). Closed with v0.6.0 | From 9 November 2026, thirteen packages, WP5.11 to WP5.21, WP5.27 and WP5.28: about 74 sessions, 66 to 132 agent hours and 122 of the author's touches (§8.3); the packages as its seventh amendment sets them (§8.2.17 S14; §8.2.31 AG1; §8.2.34 AJ10; §8.2.36 AL22, AL25; §8.2.37 AM12; §8.2.43 AS1; §8.2.47 AW1, AW4) |
| 6. Cleanup and the library's foundations | The Windows leg fixed first (REV-277); the records and instructions cleaned up to a measured reading limit, the Copilot host retired with them (REV-271, REV-272); the library's results side, its registries and its error base restructured as the [architecture survey](../../docs/project/architecture-survey.md) proposes, the numbers the shell computes moved into the library (QR-13); the model's open terms, the tolerances argued and the exports (FR-28); the library's refusals; the speed-up last; v0.7 (§8.2.49 AY1, AY3 to AY6, AY8) | Tiers 1 and 2 pass on Linux, macOS and Windows, with no waiver (§8.2.49 AY4); the number-stability golden unmoved but for the one re-pin the equations package makes (VER-62; §8.2.46 AV5); the layering guard holds (VER-61); a fresh package session starts under the reading limit (§8.2.49 AY8) | About 15 packages at Phase 5's text and clean-up rate: 75 sessions, 45 to 90 agent hours and 120 of the author's touches, until `/np-plan phase 6` estimates it again (§8.3) |
| 7. The workbench rebuilt | The workbench's foundations as the survey orders them (a state per browser client, view hosts, one form, a workspace of splits and tabs, Plotly for every chart and (r, z) view), the style built into those shared parts; then the packages Phase 5's seventh amendment moved: the tree of results (FR-32), the structure's layers, the performance package, the polish pass and the guided route with new models (FR-36), with the full guide; v0.8 (§8.2.47 AW1; §8.2.49 AY1; REV-272) | The shell's gating clauses and VER-78 on every fixture state; FR-32's tree and FR-36 each with its test or review check; QR-16's keyboard gaps and REV-274's five details closed; the 200 ms redraw measured on a GPU (REV-258); Tiers 1 and 2 pass on the three platforms | About 14 packages at Phase 5's shell rate: 85 sessions, 85 to 170 agent hours and 140 touches, and the author's design rounds, until `/np-plan phase 7` estimates it again (§8.3) |
| 8. The physics composer | A physics model composed from registered building blocks, a library capability in `physics/` first, then its tool in the workbench (FR-40; §8.2.17 S3); v0.9 (§8.2.49 AY2) | Its own Tier 1 and Tier 2 tests before the workbench surfaces it; the rest set by `/np-plan phase 8` | Set by its round |
| 9. The structural mutator | A residue's side chain replaced in 3D, with density, contour, mesh and charge run again, library first, with a vetted dependency (FR-41; §8.2.17 S4); the structure pipeline's loose ends (§8.2.49 AY6); v0.10 (§8.2.49 AY2) | As Phase 8's, set by `/np-plan phase 9` | Set by its round |
| 10. The 2D sketcher | The (r, z) domain drawn by hand with lines, arcs, booleans and named boundaries, meshed by the library (FR-42; §8.2.17 S5); v0.11 (§8.2.49 AY2) | As Phase 8's, set by `/np-plan phase 10` | Set by its round |
| 11. Validation and release | Full V&V suite in CI, the analyte forces (FR-21, FR-22), the published results reproduced, tutorials, JOSS paper, DOI archive, v0.12 (§8.2.5 E2; §8.2.6 F1; §8.2.49 AY2) | Tier 4 passes (VAL-07 to VAL-10), and Tier 3 against the published results passes (VAL-16, VAL-17; §8.2.4 D6) | About seven packages: 40 sessions, 35 to 70 agent hours and 70 touches, and the machine time of its Tier 3 and Tier 4 runs, until its round estimates it again (§8.3) |
| GUI | One increment per phase from Phase 0 to Phase 3, then the dedicated Phase 5 (§8.2.6 F5), its rebuild in Phase 7, then one phase per workbench tool, each library first: the physics composer (Phase 8), the structural mutator (Phase 9) and the 2D sketcher (Phase 10), before validation (§8.2.17 S3 to S5; §8.2.49 AY1, AY2) | QR-10: an experimentalist runs a case unaided, observed on v1.0's release candidate (§8.2.47 AW2) | Phases 5 and 7, then the tool phases |
| Documentation | Continuous track from Phase 1 onward, one increment per phase | VER-45's strict build passes on every push, and VER-46's examples 01 and 02 with it; the rest nightly (§8.2.13 N4) | continuous |

GUI increments, one per phase to Phase 3 (ADR-004), then the GUI phase (§8.2.6 F5):

| Phase | GUI increment |
|---|---|
| 0 | Packaging probe: a trivial PySide6 and NGSolve `webgui` application that builds into a double-clickable Windows bundle; Phase 5 replaces it with the server's self-test (§8.2.17 S17) |
| 1 | Case editor over the frozen schema, run control, live convergence plot, field viewer; meshes supplied externally |
| 2 | Geometry pipeline surfaced: load a structure, inspect the density, contour and mesh steps, override the contour by hand |
| 3 | Charge pipeline surfaced: pH selector, force field, charge map viewer, conservation report |
| 4 | None. The shell follows every change Phase 4 makes to the API and the case schema, so that QR-11 holds at v0.5, and gains nothing |
| 5 | The GUI phase: the design and requirements document and its mockups, the visual-feedback workflow, then the browser workbench, six suites in a project (molecular, meso, continuum and physics, which build its models, and study and analysis, which use them) with a run queue, and tools linked both ways to live views, for every user from P1 to P3, after which PySide6, the Qt widgets and the PyInstaller bundle leave (§8.2.12 M3; §8.2.17 S2, S6; the design document's WB-01, WB-02, WB-29, WB-34; §8.2.34 AJ2). The tree of results, the structure's layers, the polish pass and the guided route are Phase 7's (§8.2.47 AW1; §8.2.49 AY1). The former Phase 4 increment (sweep builder, result browser, figure export, case comparison) is an input to the document, not a commitment |
| 6 | None. The shell follows every change Phase 6 makes to the library, and the numbers it computed are read from the library (QR-13); a screen changes only where a refusal's words do |
| 7 | The residuals of Phase 5, after the restructure of the shell: the workbench's foundations, then the tree of results, the structure's layers, the performance package, the polish pass and the guided route with new models, as `/np-plan phase 7` sets them (§8.2.47 AW1; §8.2.49 AY1; REV-272) |
| 8 to 10 | The tool phases: the physics composer over registered building blocks, with room for user-authored equations later; the structural mutator; the full 2D sketcher of the (r, z) domain. Each is a library capability with its own Tier 1 and Tier 2 tests before the workbench surfaces it (§8.2.17 S3 to S5; §8.2.49 AY2) |
| 11 | None but what a validation finding changes on a screen (RSK-15) |
| post-1.0 | Installers for all three platforms, in-application tutorials |

Documentation increments, one per phase (QR-15 NOTE). Each phase
documents what it ships, and a phase's examples are executed by VER-46. The model itself is
documented by rendering this specification and the companion knowledge base (§11) verbatim, never
by a restatement of their equations:

| Phase | Documentation increment |
|---|---|
| 1 | Documentation site and its build; user guide for the solver core, the case file, meshes and fields, runs, sweeps, provenance and the desktop shell; generated case-file, command-line and exit-code references; the API reference over the IF-01 public surface; worked examples on an idealised pore and on the reference geometry |
| 2 | The geometry pipeline: structure and trajectory input, density, symmetry reduction, contour, meshing; an example from a PDB entry to a mesh |
| 3 | The charge pipeline: protonation, force field, smearing, the conservation report; an example from a PDB entry to a charged run |
| 4 | The modularity report; the user guide, the API reference and the command-line reference revised with the user-testing findings, every stale statement removed and the language made plainer, with a hand-written page over the Python interface and one listing the notebooks; the examples revised in prose alone. Every break of the phase is listed with its migration in `CHANGELOG.md`, in the entry of the package that made it, and no migration page is written (§8.2.6 F4; §8.2.24 Z2 to Z4) |
| 5 | A short application guide for the browser workbench: how to start it and what each of the six suites does, with a rendered screen for each; the desktop shell's pages leave (§8.2.47 AW3) |
| 6 | The references generated again over the restructured library; every break listed with its migration in `CHANGELOG.md` (§8.2.6 F4) |
| 7 | The full application guide, with the guided route, against the restructured screens (§8.2.47 AW3; §8.2.49 AY1) |
| 8 to 10 | Each tool's pages in the guide and the references, with an example |
| 11 | Tutorials completed against the validated release, the JOSS paper, and the DOI-archived v0.12 (QR-15 in full; §8.2.5 E2, §8.2.6 F1; §8.2.49 AY2) |
| post-1.0 | In-application tutorials, with the GUI track |

NOTE (FR-19, FR-20): FR-19 is tagged
v0.4, the end of the scope the old v0.9 named, and its `pb` and `pb-linear` models shipped in
Phase 0. FR-20, the documented physics-model
interface, is assigned to **Phase 3**, which is where the table above leaves room for it (§8.2.2 B7).

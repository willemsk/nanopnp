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
| 4. Polish and user testing | An exploration of the modularity of the implementation architecture, reported first, and the refactors the author accepts from it; the companion knowledge base restructured as an Open Knowledge Format bundle (§8.2.6 F6; §8.2.13 N3); then a user-testing pass over the physics, the numerics, the Python API and the command line, in scripted sessions; before the knowledge-base work, a faster development loop (§8.2.10); before the protocol, a plotting library over every stage's artefact and interactive notebooks over the API (§8.2.14); then the specification and the plans split into a current state and a history, the skills restructured and the notebooks revised (§8.2.16); v0.5 (§8.2.6 F3; §8.2.7) | The modularity report is merged, with each finding resolved or deferred by the author's ruling; the user-testing findings log is closed, each finding fixed or deferred by the author's ruling, both logs closed, read at review (§8.2.7 G4; §8.2.13 N3); no number of the pinned number-stability golden moves by more than 10⁻⁸ relative on a mesh it holds, nor beyond its measured mesh-moved tolerance on one it does not (§8.2.7 G10; VER-62); the development loop is simple and the prose small, as §8.2.11 L2 to L8 rule, with the loop's timings reported and a miss ruled by the author; Tiers 1 and 2 pass | 4–6 weeks (§8.2.9 I5) |
| 5. Graphical interface | A design and requirements document with mockups, a visual-feedback workflow, then the browser shell its implementation plan sets, replacing the Qt shell (§8.2.12 M3); v0.6 (§8.2.6 F5) | QR-10, observed by a person: an experimentalist runs a case unaided; Tiers 1 and 2 pass | Set by the phase plan |
| 6. Validation and release | Full V&V suite in CI, documentation, JOSS paper, v0.7 (§8.2.5 E2; §8.2.6 F1) | Tier 4 passes (VAL-07 to VAL-10), and Tier 3 against the published results passes (VAL-16, VAL-17; §8.2.4 D6) | 4–6 weeks |
| GUI | One increment per phase from Phase 0 to Phase 3, then the dedicated Phase 5 (§8.2.6 F5) | QR-10: an experimentalist runs a case unaided, which is Phase 5's gate | Phase 5 |
| Documentation | Continuous track from Phase 1 onward, one increment per phase | VER-45's strict build passes on every push, and VER-46's examples 01 and 02 with it; the rest nightly (§8.2.13 N4) | continuous |

GUI increments, one per phase to Phase 3 (ADR-004), then the GUI phase (§8.2.6 F5):

| Phase | GUI increment |
|---|---|
| 0 | Packaging probe: a trivial PySide6 and NGSolve `webgui` application that builds into a double-clickable Windows bundle |
| 1 | Case editor over the frozen schema, run control, live convergence plot, field viewer; meshes supplied externally |
| 2 | Geometry pipeline surfaced: load a structure, inspect the density, contour and mesh steps, override the contour by hand |
| 3 | Charge pipeline surfaced: pH selector, force field, charge map viewer, conservation report |
| 4 | None. The shell follows every change Phase 4 makes to the API and the case schema, so that QR-11 holds at v0.5, and gains nothing |
| 5 | The GUI phase: the design and requirements document and its mockups, the visual-feedback workflow, then the browser shell, after which PySide6, the Qt widgets and the PyInstaller bundle leave (§8.2.12 M3). The former Phase 4 increment (sweep builder, result browser, figure export, case comparison) is an input to the document, not a commitment |
| 6 | None planned. Residuals of Phase 5 only |
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
| 4 | The modularity report; the user guide, the API reference and the command-line reference revised with the user-testing findings, and every break listed with its migration (§8.2.6 F4) |
| 5 | The application guide rewritten against the Phase 5 browser workflow, with the screens the visual-feedback workflow renders |
| 6 | Tutorials completed against the validated release, the JOSS paper, and the DOI-archived v0.7 (QR-15 in full; §8.2.5 E2, §8.2.6 F1) |
| post-1.0 | In-application tutorials, with the GUI track |

Phase 2 SHALL NOT start before the Phase 0 exit criteria are met.

NOTE (FR-19, FR-20): FR-19 is tagged
v0.4, the end of the scope the old v0.9 named, and its `pb` and `pb-linear` models shipped in
Phase 0. FR-20, the documented physics-model
interface, is assigned to **Phase 3**, which is where the table above leaves room for it (§8.2.2 B7).


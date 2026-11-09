---
type: Specification
title: "2. Product overview"
description: "Places nanopnp beside COMSOL in the source work, and describes the reference implementation, product functions, users, environment and release scope."
---

## 2. Product overview

### 2.1 Product context

`nanopnp` occupies the position held by COMSOL Multiphysics in the source work and additionally
automates the manual steps preceding the solve. The source Methods section records "manual removal
of overlapping and superfluous vertices to improve the quality of the final computational mesh",
and the COMSOL model report tabulates the conditioned ClyA boundary as a 190-vertex polygon (§5.2.1). COMSOL is
retained during development as a differential-testing oracle (§7.4), not as a runtime dependency.

### 2.2 Reference implementation

The geometry and conditions of the COMSOL model being replaced, as recorded in the model report and the
ESI; Appendix B gives its solver, mesh and sweep settings. The model is 2D axisymmetric, exploiting
ClyA's C₁₂ symmetry.

| Aspect | Value |
|---|---|
| Domains | Pore dielectric body, DPhPC bilayer, two electrolyte reservoirs |
| Reservoirs | Hemispherical half-discs, R = 250 nm, one either side of the membrane |
| Membrane | 2.8 nm thick; quadrilateral with vertices (r = 2, z = −1.4), (3.5, +1.4), (250, +1.4), (250, −1.4) nm; the slanted inner edge lies *inside* the pore body over its whole length, so the assembled membrane meets the pore on the pore's own outer surface (§5.2.1) |
| Pore extent | z from −1.85 nm (`z_trans`) to +12.25 nm (`z_cis`); r ≈ 1.65–5.66 nm |
| Pore boundary | Closed polygon; the delivered 185-vertex table is the geometry of record, the model report tabulates 190 after its import conditioning (§5.2.1) |
| Geometry vertices | 196 for the assembled region (3 domains, 198 boundaries): the 190 polygon vertices, the two points where the membrane planes z = ±1.4 cut the pore's outer surface, the membrane's two outer corners on the reservoir arc, and the arc's two endpoints on the axis (§5.2.1) |
| Structure | PDB 2WCD (Mueller et al., *Nature* **459**, 726, 2009), as the ClyA-AS variant, not wild type |
| Electrolyte | Aqueous NaCl, binary monovalent |
| Bias range | −200 to +200 mV; 0.05–3 M experimentally, 0.005–5 M simulated |
| Temperature | 298.15 K (experiments at 25 ± 1 °C) |
| Pore treatment | Dielectric body, impermeable to ions and to water |

### 2.3 Product functions

| ID | Function |
|---|---|
| S1 | Sweep over salt concentration × bias × pore mutant as independent steady solves, dispatched as an HPC job array, warm-started from neighbouring points, collected into one dataset. |
| S2 | Axial force profile on an analyte at a series of positions through the lumen, integrated to an electro-osmotic PMF. |
| S3 | Desktop run: load a PDB, accept defaults, run, obtain an I–V curve and a field map, export figure and case file. |
| S4 | Regeneration of the published ClyA figure set from one command, as a CI regression test. |

### 2.4 User classes

| ID | Persona | Environment | Primary need |
|---|---|---|---|
| P1 | Method developers | Linux workstation and HPC, Python | Scriptable API, sweeps, ability to change the physics, full introspection |
| P2 | Collaborating computational scientists | Linux/macOS, Python-literate | Config-file-driven CLI runs, reproducible cases, sensible defaults |
| P3 | Experimental nanopore laboratories | Windows/macOS laptop, no Python | Desktop application: select a PDB, set salt and voltage, obtain a prediction and a visualisation |

NOTE (P3; lands with WP5.21, Qt's removal). When it lands, P3's primary need
reads: "The workbench, installed with one documented command and opened in the browser: select a
PDB, set salt and voltage, obtain a prediction and a visualisation." Until then the text above gates
the Qt shell (§8.2.17 S2, S12, S17).

### 2.5 Operating environment

| Aspect | Value |
|---|---|
| Operating systems | Windows, macOS, Linux |
| Python | 3.11 to 3.14 (§8.2.2 B4) |
| Execution modes | Headless library and CLI; HPC job arrays; packaged desktop application |
| Solver hardware | Single node, serial per solve; parallelism at the job level |
| Direct-solve ceiling | About 2–5 × 10⁶ DOF for a sparse direct factorisation |
| Reference problem size | About 1.2 × 10⁵ cells, five fields, factorisable on a laptop |

### 2.6 Assumptions and dependencies

| Dependency | Licence | Role |
|---|---|---|
| NGSolve / Netgen 6.2.2606+ | LGPL-2.1 | FEM backend and default mesher (ADR-001) |
| Gmsh | GPLv2+ | Optional mesher backend (ADR-002) |
| MDAnalysis 2.10+ | LGPLv3 | Structure and trajectory input, alignment |
| gemmi 0.7+ | MPL-2.0 | mmCIF structure input, which MDAnalysis 2.10 does not read (WP18) |
| PDB2PQR 3.8+ | BSD-3 | Protonation states and partial charges |
| PROPKA 3.5+ | LGPL-2.1 | pKa prediction, installed as a PDB2PQR dependency. Licensed LGPL-2.1 (its package metadata), acceptable under CON-09 |
| APBS 3.4.1 | BSD-3 | Poisson-only cross-check (VAL-06), run from the `apbs-binary` wheels (Apache-2.0 packaging; Linux x86_64 and macOS) in a test-only dependency group, never on the end-user path (§8.2.4 D3) |
| scikit-image, Shapely | BSD-3 | Contour extraction, polyline conditioning |
| meshio (MIT), GridDataFormats (LGPL) | as noted | Mesh interchange; OpenDX/CCP4 grid IO |
| SuiteSparse UMFPACK | GPL-2+ | Direct linear solver, default (built into the NGSolve wheel; CON-11) |
| scipy SuperLU | BSD | Direct linear solver, selectable fallback |
| PySide6 | LGPL-3 | Desktop shell (ADR-004) |

NOTE (§2.5, §2.6; lands with WP5.21, Qt's removal): §2.5's execution modes read "Headless library and
CLI; HPC job arrays; the browser workbench"; the PySide6 row goes, and NiceGUI and FastAPI (MIT, BSD-3,
the workbench's server and front end) join.

Assumptions: the published physics, parameters and COMSOL implementation details are CC-BY-4.0 and
suffice for reimplementation; a COMSOL licence remains available during development for
reference-solution generation; MD trajectories are supplied as input.

### 2.7 Release scope

| Release | Phase | Content |
|---|---|---|
| v0.1 | 0 | Spike. Analytic cylindrical/conical pore, coupled steady axisymmetric ePNP-NS, continuation ladder, analytic benchmarks, one COMSOL comparison. No structure pipeline, no GUI. |
| v0.2 | 1 | Solver core on an externally supplied mesh and material/charge fields; full QoI extraction; pluggable correction models; a versioned case-file schema; the Python API (stable from v1.0, IF-01); CLI; sweep runner. |
| v0.3 | 2 | Geometry pipeline: structure and trajectory ingestion, density, symmetry reduction, contour, CAD, mesh. |
| v0.4 | 3 | Charge pipeline: PDB2PQR to smeared ρ_fixed and dielectric field; the physics-model interface (FR-20). Runs the paper's pipeline end to end, from structure to current; the reproduction of the published results is measured at v0.7 (VAL-16, VAL-17; §8.2.4 D6). |
| v0.5 | 4 | Polish and user testing (§8.2.6 F3): an exploration of the modularity of the implementation architecture, then a user-testing pass over the physics, the numerics, the Python API and the command line. No GUI increment. |
| v0.6 | 5 | Graphical interface (§8.2.6 F5): a design and requirements document with mockups, a visual-feedback workflow, then the browser workbench its plan sets (FR-31 to FR-39): five suites over a project folder, a run queue, and the guided route of QR-10. |
| v0.7 | 6 | Validated release: V&V suite in CI, the published current–voltage relationships and in-pore averages reproduced (VAL-16, VAL-17), documentation, tutorials, JOSS submission, DOI-archived. Released before v1.0. |
| v1.0 | — | Stable release: the API stability promise of IF-01. Its content and gate are the author's to define (OPN-08). |
| post-1.0 | — | Backlog: installers for all three platforms and in-application tutorials; 3D; transient; ion-specific rather than mean-concentration-driven property models; MD-fitting toolkit for corrections; solid-state pores; charge regulation; multi-species electrolytes beyond binary; non-axisymmetric analytes. |

A requirement's release in §3 is a release of the table above, or one of the tool phases of §8.1
(composer, structural mutator, sketcher, or "a later phase"), which takes a number when Phase 5 closes.

NOTE (Versioning; §8.2.4 D1): the
releases above are git tags `vX.Y.Z`, one minor version per phase, on the commit that merges the
phase's end-of-phase report (§8.1): `v0.1.0` for Phase 0, `v0.2.0` for Phase 1, `v0.3.0` for
Phase 2, `v0.4.0` for Phase 3, `v0.5.0` for Phase 4, `v0.6.0` for Phase 5 and `v0.7.0` for Phase 6
(§8.2.5 E2, §8.2.6 F1 and F2). Each merged work package is tagged
`vX.Y.Z-alpha.N` on its last commit on `main`, where N counts the phase's work packages toward
that release; from Phase 5, N is the package's number within its phase (`WP5.02` takes
`v0.6.0-alpha.2`), and a package merged before its previous phase's release takes no tag (§8.4.1;
§8.2.17 S15, S16, S19). The tag names are SemVer, and PEP 440 reads them as
`X.Y.ZaN` (`0.2.0a10`). The package version is derived from the tag (hatch-vcs), so a commit between
tags installs as a development version naming that commit, and the provenance manifest's recorded
`nanopnp` version identifies the code that produced a result (FR-25). The version enters no artefact
key: the environment is recorded beside an artefact, never hashed into it (§5.3.2). `CHANGELOG.md`
records every tag, and a milestone tag publishes a GitHub Release with its section as the notes. A tag name is never moved to another commit once published and never reused for
another phase. A manifest that records a version from before the renumbering of 30 September 2026 is
decoded in `CHANGELOG.md`'s head. A milestone tag's
release workflow enforces that `CITATION.cff` names its version only for the highest milestone
tag, the release that *Cite this repository* shows; an older milestone's citation metadata is
fixed in its commit and a re-release cannot change it.

---

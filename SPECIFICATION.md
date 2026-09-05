# Software Specification — nanopnp

Open-source continuum simulation of biological nanopores (ePNP-NS)

| Field | Value |
|---|---|
| Package | `nanopnp` |
| Version | 0.5 |
| Date | 16 August 2026 |
| Author of record | Kherim Willems |
| Status | Draft for review |
| Structure | ISO/IEC/IEEE 29148 (requirements), IEEE 1016 (design), IEEE 1012 (verification and validation) |

---

## 1. Introduction

### 1.1 Purpose

This document specifies `nanopnp`, an open-source Python program replacing a COMSOL Multiphysics
workflow for continuum simulation of biological nanopores. It states the requirements (§3), the
normative physics model (§4), the software design (§5), the numerical methods (§6) and the
verification and validation plan (§7).

### 1.2 Scope

`nanopnp` accepts an atomistic structure (PDB or mmCIF, optionally with a molecular-dynamics
trajectory), an electrolyte specification and an applied bias, and returns ionic conductance,
transport numbers, current rectification, electro-osmotic flow rate, and axial force and PMF on an
embedded analyte. It solves the extended Poisson–Nernst–Planck / Navier–Stokes (**ePNP-NS**)
equations of Willems et al., *Nanoscale* **12**, 16775 (2020), at steady state, on a
2D-axisymmetric finite-element mesh generated automatically from the structure. Coverage runs from
density mapping, symmetry reduction, contour extraction, geometry and mesh construction and
fixed-charge assembly through solution, QoI extraction, sweeps and provenance. Exclusions are
in §3.5.

### 1.3 Definitions and acronyms

| Term | Definition |
|---|---|
| ePNP-NS | Extended Poisson–Nernst–Planck / Navier–Stokes model of Willems et al. (2020): PNP-NS with concentration- and wall-distance-dependent corrections to D, μ, η, ε and ϱ |
| PNP-NS | Classical Poisson–Nernst–Planck / Navier–Stokes; ePNP-NS at β = 0 with all f^c = f^w = 1 |
| PB | Poisson–Boltzmann, equilibrium; PB-linear is its Debye–Hückel linearisation |
| EDL / EOF | Electrical double layer / electro-osmotic flow |
| QoI | Quantity of interest: conductance G, transport number t₊, rectification ratio RR, EOF rate, analyte force |
| PMF | Potential of mean force, ΔU(z) = −∫F dz |
| MMS | Method of manufactured solutions |
| ClyA-AS | Cysteine-free ClyA variant modelled in the source work, built on PDB 2WCD |
| ESI | Electronic supplementary information of the Nanoscale paper |
| Case file | Declarative YAML document that is the unit of reproducibility (§5.3) |

### 1.4 References

References are collected in §12. The normative sources are the Nanoscale paper and its ESI, the
CC-BY-4.0 thesis (`github.com/willemsk/phdthesis-text`, chs. 5–6), and the COMSOL model report
of §1.6.

### 1.5 Document conventions

Requirements use RFC 2119 keywords: SHALL (mandatory), SHOULD (recommended), MAY (optional). Each
carries a unique identifier, numbered within its class and zero-padded to two digits.

| Prefix | Class | Location |
|---|---|---|
| `IF-nn` | External interface | §3.1 |
| `FR-nn` | Functional | §3.2 |
| `QR-nn` | Quality of service | §3.3 |
| `CON-nn` | Design or implementation constraint | §3.4 |
| `PHY-nn` | Physics/model | §4 |
| `NUM-nn` | Numerical method | §6 |
| `VER-nn` / `VAL-nn` | Verification / validation activity | §7 |
| `ADR-nn` | Architecture decision record | §5.6 |
| `RSK-nn` | Risk register entry | §9 |
| `OPN-nn` | Open item | §10 |

Units are SI and explicit: nm, mol/L (M), K, V or mV, pN. Spelling is British.

### 1.6 Provenance and verification status

Of 118 discrete claims in v0.1, ten were wrong and were corrected, including a factor-of-two error
in the Maxwell–Hall access-conductance benchmark, an inverted sign in the steric flux, and the
finding that the NGSolve pip wheel ships without MUMPS. Transcription of the ePNP-NS
parameterisation from the CC-BY-4.0 thesis LaTeX source surfaced five further errata, one of which
contradicted a correction supplied by the author from memory.

The overriding authority is the 162-page COMSOL model report `npgrid_clya_v8_NaCl_report.mph`
(COMSOL 5.4 build 388, dated 22 May 2020), read in full. Where it disagrees with the printed
sources or with author recollection, the model file governs. It settles the mesh, solver and
stabilisation questions, supplies full-precision fit coefficients, and reverses the earlier ruling
on the permittivity parameters. It also resolves the "0.62" discrepancy: the ESI writes the wall
coefficient as `0.62e1`, which is 6.2.

Claims that could not be verified are marked in place. Errata in the source material are in §4.6.

---

## 2. Product overview

### 2.1 Product context

`nanopnp` occupies the position held by COMSOL Multiphysics in the source work and additionally
automates the manual steps preceding the solve. The source Methods section records "manual removal
of overlapping and superfluous vertices to improve the quality of the final computational mesh",
and the ESI records a delivered ClyA boundary of 190 vertices after that conditioning. COMSOL is
retained during development as a differential-testing oracle (§7.4), not as a runtime dependency.

### 2.2 Reference implementation

The COMSOL model being replaced, as recorded in the model report and the ESI.

| Aspect | Value |
|---|---|
| Solver | COMSOL Multiphysics 5.4 build 388, FEM, coupled nonlinear, fully coupled PARDISO |
| Model file | `npgrid_clya_v8_NaCl_report.mph`, 162-page report, 22 May 2020 |
| Dimensionality | 2D axisymmetric (exploiting ClyA's C₁₂ symmetry), steady state |
| Domains | Pore dielectric body, DPhPC bilayer, two electrolyte reservoirs |
| Reservoirs | Hemispherical half-discs, R = 250 nm, one either side of the membrane |
| Membrane | 2.8 nm thick; quadrilateral with vertices (r = 2, z = −1.4), (3.5, +1.4), (250, +1.4), (250, −1.4) nm; the slanted inner edge lies *inside* the pore body over its whole length, so the assembled membrane meets the pore on the pore's own outer surface (§5.2.1) |
| Pore extent | z from −1.85 nm (`z_trans`) to +12.25 nm (`z_cis`); r ≈ 1.65–5.66 nm |
| Pore boundary | Closed 190-vertex polygon, tabulated in the model report; delivered as a 185-vertex table (§5.2.1) |
| Geometry vertices | 196 for the assembled region (3 domains, 198 boundaries): the 190 polygon vertices, the two points where the membrane planes z = ±1.4 cut the pore's outer surface, the membrane's two outer corners on the reservoir arc, and the arc's two endpoints on the axis (§5.2.1) |
| Structure | PDB 2WCD (Mueller et al., *Nature* **459**, 726, 2009), as the ClyA-AS variant, not wild type |
| Electrolyte | Aqueous NaCl, binary monovalent |
| Bias range | −200 to +200 mV; 0.05–3 M experimentally, 0.005–5 M simulated |
| Temperature | 298.15 K (experiments at 25 ± 1 °C) |
| Pore treatment | Dielectric body, impermeable to ions and to water |
| Mesh | Free triangular, no boundary layers, 120,917 triangles, isotropic grading to 0.05 nm at the pore wall |
| Sweep | 5 physics cases × 35 bias values × 21 salt concentrations = 3,675 solves, 41 h on 12 cores |

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

### 2.5 Operating environment

| Aspect | Value |
|---|---|
| Operating systems | Windows, macOS, Linux |
| Python | 3.10 to 3.14 |
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
| PDB2PQR 3.7+, PROPKA3 | BSD | Protonation states and partial charges |
| APBS 3.4.1 | BSD-3 | Poisson-only cross-check |
| scikit-image, Shapely | BSD-3 | Contour extraction, polyline conditioning |
| meshio (MIT), GridDataFormats (LGPL) | as noted | Mesh interchange; OpenDX/CCP4 grid IO |
| SuiteSparse UMFPACK | GPL-2+ | Direct linear solver, default (built into the NGSolve wheel; CON-11) |
| scipy SuperLU | BSD | Direct linear solver, selectable fallback |
| PySide6 | LGPL-3 | Desktop shell (ADR-004) |

Assumptions: the published physics, parameters and COMSOL implementation details are CC-BY-4.0 and
suffice for reimplementation; a COMSOL licence remains available during development for
reference-solution generation; MD trajectories are supplied as input.

### 2.7 Release scope

| Release | Phase | Content |
|---|---|---|
| v0.1 | 0 | Spike. Analytic cylindrical/conical pore, coupled steady axisymmetric ePNP-NS, continuation ladder, analytic benchmarks, one COMSOL comparison. No structure pipeline, no GUI. |
| v0.5 | 1 | Solver core on an externally supplied mesh and material/charge fields; full QoI extraction; pluggable correction models; frozen case-file schema; stable Python API; CLI; sweep runner. |
| v0.9 | 2–3 | Full pipeline: structure and trajectory ingestion, density, symmetry reduction, contour, CAD, mesh; PDB2PQR to smeared ρ_fixed and dielectric field. Reproduces the paper end to end. |
| v1.0 | 4 | Validated release: V&V suite in CI, documentation, tutorials, JOSS submission, DOI-archived. |
| v1.5 | 5 | Desktop application: packaged installers, in-app case builder, live convergence monitoring, field visualisation. |
| post-1.0 | — | Backlog: 3D; transient; ion-specific rather than ionic-strength-based property models; MD-fitting toolkit for corrections; solid-state pores; charge regulation; multi-species electrolytes beyond binary; non-axisymmetric analytes. |

Release tags in §3 take four values: v0.5, v0.9, v1.0, post-1.0. Items scheduled for v1.5 are
tagged post-1.0.

---

## 3. Requirements

The subject of each requirement is the product unless stated otherwise.

### 3.1 External interfaces

| ID | Requirement |
|---|---|
| **IF-01** | SHALL expose a Python API in which every pipeline stage is a separately importable, invocable object, stable from v0.5 onward. |
| **IF-02** | SHALL provide a CLI over the same stage objects, able to execute a case file, run one stage, and dispatch a sweep. |
| **IF-03** | SHALL accept one declarative YAML case file, identified by `schema: nanopnp/case/v1`, as the complete run specification, rejecting unknown keys with a diagnostic naming the key. |
| **IF-04** | SHALL read structures in PDB and mmCIF, and trajectories in DCD, XTC, TRR and NetCDF. |
| **IF-05** | SHALL read and write volumetric density and charge grids in OpenDX and CCP4. |
| **IF-06** | SHALL write meshes in Gmsh MSH 4.1 as the archival format, and SHOULD read any format meshio supports. |
| **IF-07** | SHALL write solution fields in XDMF with HDF5 heavy data. |
| **IF-08** | SHALL accompany every result artefact with a machine-readable provenance manifest (FR-25). |
| **IF-09** | SHALL provide a desktop graphical interface covering case editing, run control, convergence monitoring and field visualisation, as a thin shell over the IF-01 stage objects. |

Rationale (IF-06): MSH 4.1 is the only format in the toolchain carrying physical-group tags,
higher-order elements and mixed element types without loss.

### 3.2 Functional requirements

| ID | Requirement | Release |
|---|---|---|
| **FR-01** | SHALL ingest a structure and optional trajectory ensemble and superpose all frames on a reference frame's Cα set. | v0.9 |
| **FR-02** | SHALL determine the Cₙ axis by chain-permutation superposition, taking the eigenvector of eigenvalue 1 of the chain-to-chain rotation, and place it on z at r = 0. | v0.9 |
| **FR-03** | SHALL verify the expected oligomeric state (ClyA 12, αHL 7, MspA 8) and abort on missing chains. | v0.9 |
| **FR-04** | SHALL build an ensemble-averaged density map from per-atom Gaussians whose width is tied to each atom's van der Waals radius, on a 0.25–0.5 Å grid. | v0.9 |
| **FR-05** | SHALL reduce the 3D map to (r, z) by averaging the n rotated copies before azimuthal averaging, with area-weighted binning over exact annular volumes. | v0.9 |
| **FR-06** | SHALL report residual azimuthal variance as a first-class output of every reduced geometry. | v0.9 |
| **FR-07** | SHALL extract the pore surface as a closed contour of the reduced map at a configurable isolevel, default 0.25, and condition it to a watertight, non-self-intersecting polyline. | v0.9 |
| **FR-08** | SHALL gate the conditioned contour on validity, simplicity, minimum vertex spacing, minimum local feature size, single closed loop and radius-profile agreement, aborting on failure. | v0.9 |
| **FR-09** | SHALL assemble the (r, z) region from pore contour, membrane and reservoir half-discs, fragmented for conformal interfaces, the membrane being representable as a quadrilateral with a slanted inner edge. | v0.9 |
| **FR-10** | SHALL generate a graded triangular mesh resolving the wall Debye length against the reservoir scale, isotropically by default, aborting with the worst element and its location reported when quality gates fail. | v0.9 |
| **FR-11** | MAY generate structured boundary layers along the pore wall as an element-count optimisation. | post-1.0 |
| **FR-12** | SHALL derive protonation states and partial charges at a configurable pH and force field, and record the net charge Q_net. | v0.9 |
| **FR-13** | SHALL assemble the axisymmetric fixed-charge density by depositing per-atom Gaussians in 3D Cartesian space, then projecting azimuthally over exact annular volumes with the configured axis guard. | v0.9 |
| **FR-14** | SHALL assert charge conservation on the deployed finite-element mesh and check per-z-slice cumulative charge against the source charge list. | v0.9 |
| **FR-15** | SHALL build the dielectric field and the ion-exclusion surface from the same density field, with independently configurable protein permittivity and exclusion offset. | v0.9 |
| **FR-16** | SHALL implement each empirical correction as a named component registered by string, its fit coefficients held in versioned data files, so a new electrolyte or surface is a data file rather than a code change. | v0.5 |
| **FR-17** | SHALL solve the steady 2D-axisymmetric ePNP-NS system across 0.005–5 M and ±200 mV with all corrections active, via a continuation ladder, without negative concentrations at any nonlinear iterate. | v0.5 |
| **FR-18** | SHALL provide physics models `ePNP-NS`, `PNP-NS`, `PNP` and `Poisson`, selected by name in the case file, `PNP-NS` being a configuration of `ePNP-NS` with corrections disabled rather than separate code. | v0.5 |
| **FR-19** | SHALL provide nonlinear Poisson–Boltzmann (`PB`) and Debye–Hückel (`PB-linear`) as separate equilibrium physics models. | v0.9 |
| **FR-20** | SHALL admit a new physics model as one implementation of a documented interface (field set, weak-form contributions, boundary-condition vocabulary, default solve strategy), with no change to the mesh, geometry, charge, sweep, provenance or interface layers. | v0.9 |
| **FR-21** | SHALL support a rigid analyte body of revolution on the pore axis, subtracted from the fluid domain and treated as a hard dielectric with no ion flux, no-slip and a dielectric jump, charged as either a surface density or a smeared volumetric charge. | v1.0 |
| **FR-22** | SHALL compute F^em(z), F^hd(z), their sum, and ΔU(z) = −∫F dz with barriers and minima in kT, over a series of axial analyte positions. | v1.0 |
| **FR-23** | SHALL extract ionic current, cation and anion transport numbers, rectification ratio and EOF rate by two independent routes whose agreement is checked automatically. | v0.5 |
| **FR-24** | SHALL sweep any case-file field, dispatch the points as independent jobs, warm-start each solve from a converged neighbour, and collect results into one dataset. | v0.5 |
| **FR-25** | SHALL emit with every result a provenance manifest recording input hashes, library versions, mesh hash, solver settings, stabilisation mode and correction parameter file versions. | v0.5 |
| **FR-26** | SHALL round-trip a case file, a written and re-read case yielding a semantically identical run configuration. | v0.5 |
| **FR-27** | SHALL make every stage independently invocable, cancellable, progress-reporting and introspectable, emitting a typed, serialisable, content-hashed artefact that may be inspected, exported, edited and substituted by hand. | v0.5 |
| **FR-28** | SHALL export figures, fields and the originating case file from a completed run. | v1.0 |
| **FR-29** | MAY perform goal-oriented (dual-weighted-residual) mesh adaptivity targeting the ionic current. | post-1.0 |

Rationale (FR-23): continuous-Galerkin fluxes are not pointwise conservative, so a current obtained
by integrating flux over an interior cross-section varies between cross-sections by amounts that
can exceed the rectification signal at low bias.

Rationale (FR-26): "semantically identical" is asserted on the content hash of the validated case
document and on the resolved run configuration it produces, never on the YAML text. A case file
written by hand omits defaults, orders keys freely and carries comments, none of which survive a
round trip and none of which change the run; requiring textual identity would test the serialiser
instead of the schema (VER-09).

### 3.3 Quality of service

| ID | Requirement | Class |
|---|---|---|
| **QR-01** | Tier-2 analytic benchmarks SHALL pass, including Maxwell–Hall access conductance to better than 2 % and MMS convergence at O(h³) in L² for P2 on the full coupled axisymmetric system. | Correctness |
| **QR-02** | Once the matching stabilised mode exists and meshes are convergence-matched, comparison against COMSOL reference solutions SHALL agree to better than 1 % relative L² error on fields and 0.5 % on integrated QoIs; until then, differences SHALL be recorded and attributed, not gated on. | Correctness |
| **QR-03** | Assembled fixed charge SHALL be conserved to better than 0.1 % of Q_net on the deployed mesh. | Correctness |
| **QR-04** | The two current-extraction routes of FR-23 SHALL agree within a stated tolerance, checked in CI. | Correctness |
| **QR-05** | End-to-end reproduction of published conductance, transport-number and rectification data SHALL agree with experiment no worse than the source work's own agreement with experiment. | Correctness |
| **QR-06** | A full-envelope sweep of 3,675 solves SHOULD complete within a day-scale wall-clock time on 12 cores, throughput scaling linearly with the number of independent workers. | Performance |
| **QR-07** | A sparse direct factorisation of a production-sized problem (about 1.2 × 10⁵ cells, five fields) SHALL complete in acceptable time and memory on a laptop. | Performance |
| **QR-08** | Re-running a case file with the recorded library versions SHALL reproduce every scalar QoI to within the solver tolerance, the FR-25 manifest sufficing to reconstruct the run. | Reproducibility |
| **QR-09** | SHALL install from binary wheels on Windows, macOS and Linux for Python 3.10–3.14, with no compilation on the target machine. | Portability |
| **QR-10** | A nanopore experimentalist without Python knowledge SHALL be able to load a structure, accept defaults and obtain a conductance prediction and a field visualisation in the desktop application unaided. | Usability |
| **QR-11** | Each release from v0.5 onward SHALL ship a usable graphical surface over the functionality existing at that release. | Usability |
| **QR-12** | Every automatic gate failure SHALL abort the run with a diagnostic naming the gate, the offending quantity and its location. | Usability |
| **QR-13** | The ePNP-NS weak forms SHALL be expressed once against the internal backend interface and SHALL NOT be duplicated per backend. | Maintainability |
| **QR-14** | Adding a correction parameterisation SHALL require only a data file; adding a physics model SHALL require only one class (FR-20). | Maintainability |
| **QR-15** | v1.0 SHALL ship user documentation, tutorials, a JOSS submission and a DOI-archived release. | Maintainability |

Rationale (QR-02): the reference implementation uses linear velocity and pressure on a mesh from a
different generator with stabilisation active, so two correct codes disagree at the per-cent level
until those differences are matched.

### 3.4 Design and implementation constraints

| ID | Constraint |
|---|---|
| **CON-01** | v1 SHALL be restricted to 2D-axisymmetric, steady-state solution. The architecture SHALL NOT preclude a later 3D or transient extension. |
| **CON-02** | Consequent on CON-01, an analyte SHALL be a body of revolution centred on the pore axis (sphere, spheroid, cylinder or revolved profile). |
| **CON-03** | Consequent on CON-01, only the axial force component is meaningful; radial force is zero by symmetry, and the radial stiffness of an electro-osmotic trap SHALL NOT be reported. |
| **CON-04** | Consequent on CON-01, azimuthal averaging of a Cₙ structure systematically widens the constriction, the most conductance-sensitive geometric parameter; residual azimuthal variance SHALL therefore accompany every reduced geometry (FR-06). |
| **CON-05** | All concentration-dependent parameters use local ionic strength rather than individual ion concentrations, inherited from the source model. This breaks down inside double layers, where local electroneutrality is violated, and SHALL be documented as the origin of residual discrepancy below 0.05 M. |
| **CON-06** | The single production FEM backend SHALL be NGSolve/Netgen 6.2.2606+ (LGPL-2.1), behind a thin internal interface sized only to make a future second backend bounded work. |
| **CON-07** | No component on the end-user execution path SHALL require a C++ compiler, a source build or a JIT toolchain on the end-user machine. |
| **CON-08** | The distributed wheels are serial-only and ship without MUMPS, and the reference model's PARDISO is equally unavailable; the desktop path SHALL use UMFPACK or scipy SuperLU. |
| **CON-09** | The core library SHALL be licensed BSD-3-Clause. LGPL dependencies are acceptable under dynamic linking (NGSolve/Netgen LGPL-2.1, MDAnalysis LGPLv3, PySide6 LGPL-3). PyQt SHALL NOT be used, being GPL-3 or commercial only. |
| **CON-10** | Gmsh (GPLv2+) SHALL be an optional backend only; the default path SHALL NOT link Gmsh, and the core library SHALL remain functional without it. |
| **CON-11** | SuiteSparse UMFPACK is GPL-2+, so a bundle defaulting to UMFPACK carries GPL obligations even though the library does not. The core library SHALL remain BSD-3 and SHALL NOT itself depend on UMFPACK; the redistributable bundle SHALL default to UMFPACK, SHALL be distributed under the resulting GPL-2+ obligations and SHALL state them in its licence notice, scipy SuperLU remaining selectable at runtime. **Amended 2 September 2026**, reversing the earlier "SHOULD default to scipy SuperLU with UMFPACK opt-in", on the §6.6 measurement: SuperLU did not factorise the reference-sized problem at all, so a SuperLU-default bundle could not run the published case. |
| **CON-12** | Meshing components with distribution-restricting licences SHALL NOT be depended upon, specifically Triangle (and MeshPy, which wraps it) and TetGen 1.5 (AGPLv3). |
| **CON-13** | SHALL support Windows, macOS and Linux on desktop hardware, and Linux for headless and HPC execution. |
| **CON-14** | The repository SHALL carry a `CITATION.cff` pointing at the Nanoscale paper and the software DOI. |

### 3.5 Exclusions

Outside the scope of v1. Identifiers retained from v0.4.

| ID | Exclusion |
|---|---|
| N1 | A general-purpose PDE framework. Users do not write weak forms; a physics model may be swapped or extended, an unrelated multiphysics problem may not be posed. |
| N2 | Molecular dynamics. MD is an input; the product consumes trajectories and does not produce them. |
| N3 | Time-dependent or transient simulation, including translocation event traces, Brownian dynamics and simulated current traces. |
| N4 | Full 3D solution. The architecture must not preclude it; v1 does not ship it. |
| N5 | Flexible or deforming analytes, and analytes off the symmetry axis. |
| N6 | Parameterisation of corrections from MD. The product consumes correction parameter files; deriving new ones is a separate, later tool. |
| N7 | COMSOL file import or export. |
## 4. Physics specification (normative)

This section states the mathematical model. Requirements carry `PHY-nn` IDs and use the keywords
of §1.5. Symbols follow Willems K. et al., *Nanoscale* **12**, 16775–16795 (2020) and
`.knowledge/01-physics-epnpns.md`. Where the reference and the published text differ, the COMSOL
model report governs and §4.6 records the divergence.

### 4.1 Domains, boundaries and symbols

#### 4.1.1 Domains and boundaries

| Name | Region | Equations and conditions |
|---|---|---|
| `Ω_w` | electrolyte: both reservoirs and the pore lumen | Poisson, Nernst–Planck, Navier–Stokes |
| `Ω_p` | pore protein | Poisson |
| `Ω_m` | lipid bilayer | Poisson |
| `Ω_a` | analyte body, when one is present (FR-21) | Poisson |
| `Ω` | `Ω_w ∪ Ω_p ∪ Ω_m ∪ Ω_a` | Poisson |
| `Γ_w,c`, `Γ_w,t` | exterior reservoir boundaries, cis and trans | Dirichlet φ, c; stress-free |
| `Γ_m` | exterior bilayer boundary | zero charge |
| `Γ_p+m` | interior interface, fluid to protein and membrane | dielectric continuity, no-flux, no-slip |
| `Γ_a` | analyte surface | dielectric continuity, no-flux, no-slip; the NUM-28 force is taken over it |
| `r = 0` | symmetry axis | axis conditions |

NOTE: reference geometry is a hemispherical reservoir of radius R = 250 nm on each side and a
DPhPC bilayer of thickness 2.8 nm.

#### 4.1.2 Symbols

| Symbol | Meaning | Units |
|---|---|---|
| `φ` | electric potential | V |
| `V_bias` | applied bias on `Γ_w,t` | V |
| `c_i`, `c_bulk` | concentration of ion *i*; reservoir value | mol m⁻³ |
| `u`, `p`, `σ` | fluid velocity; pressure; stress tensor | m s⁻¹; Pa; Pa |
| `J_i`, `β_i` | molar flux of ion *i*; its steric flux vector | mol m⁻² s⁻¹; m⁻¹ |
| `Φ` | packing fraction `Σ_j N_A a_j³ c_j` | 1 |
| `ρ_pore`, `ρ_ion` | fixed protein space charge; mobile charge `F Σ_i z_i c_i` | C m⁻³ |
| `σ_s` | prescribed surface charge density | C m⁻² |
| `⟨c⟩`, `d` | average ion concentration; wall distance (§4.1.3) | mol L⁻¹; nm |
| `D_i`, `μ_i` | diffusivity; mobility of ion *i* | m² s⁻¹; m² V⁻¹ s⁻¹ |
| `η`, `ϱ`, `ε_r` | viscosity; mass density; relative permittivity | Pa s; kg m⁻³; 1 |
| `a_i`, `a_0`, `z_i` | steric diameter ion / water; valence | m; m; 1 |
| `ε_0`, `F` | 8.85419 × 10⁻¹² F m⁻¹; 96485.33 C mol⁻¹ | — |
| `R`, `N_A` | 8.314463 J mol⁻¹ K⁻¹; 6.022 × 10²³ mol⁻¹ | — |
| `T`, `V_T` | 298.15 K; thermal voltage `RT/F` = 25.693 mV | — |

#### 4.1.3 Derived scalar fields

**PHY-01.** The correction driver `⟨c⟩` SHALL be the arithmetic mean of the ion concentrations,
`⟨c⟩ = (1/n) Σ_i c_i` over the n solved species, with each `c_i` clamped to
[1 × 10⁻⁶ M, 5.3 M] before the average is taken (COMSOL: `(cdf.dcpos + cdf.dcneg)*0.5`). The
ionic-strength form `½ Σ_i z_i² c_i` SHALL be available as a separately named option.

Rationale: the published prose calls `⟨c⟩` the local ionic strength. The two coincide for a
symmetric 1:1 salt, so the published results do not discriminate; the arithmetic mean is what the
model evaluates and generalises unambiguously to multivalent species.

**PHY-02.** The wall distance `d` SHALL be the distance to the nearest pore boundary, with the
membrane excluded from the distance source set. `d` SHALL be computed once per mesh as a field
(eikonal solve or screened-Poisson smoothing) and mollified to C¹ continuity.

Rationale: the reference model used a general-extrusion operator over the pore boundaries only;
electrolyte properties near the bilayer do not affect the pore's figures of merit. That field was
unsmoothed. Mollification is an implementation change, not a model change, and is required because
`D`, `μ` and `η` all depend on `d`, so a kinked `d` enters the Jacobian.

### 4.2 Governing equations

**PHY-03.** Poisson's equation SHALL be solved over the whole domain `Ω`, with piecewise
permittivity and a volumetric fixed charge in the solid domains:

```
−∇·( ε_0 ε_r(⟨c⟩, x) ∇φ ) = ρ_pore(x) + ρ_ion ,      ρ_ion = F Σ_i z_i c_i
```

**PHY-04.** The steady size-modified Nernst–Planck equation SHALL be solved on `Ω_w` for each
species i:

```
∇·J_i = 0
J_i = −[ D_i(⟨c⟩,d) ∇c_i  +  z_i μ_i(⟨c⟩,d) c_i ∇φ  +  D_i(⟨c⟩,d) β_i c_i  −  u c_i ]
```

**PHY-05.** The steric flux enters the flux bracket with a positive sign; the bracket is then
negated. The steric flux vector SHALL be

```
            (a_i³ / a_0³) · Σ_j N_A a_j³ ∇c_j
    β_i  =  ─────────────────────────────────
              1 − Σ_j N_A a_j³ c_j
```

with `a_i = 0.5 nm` for all ions (maximum packing 13.3 M) and `a_0 = 0.311 nm` for water (maximum
packing 55.2 M). The reference implementation is

```
smp.alpha_cpos*cpos*(smp.rad3_cpos*(−tds.D_cposrr*cposr − …) + smp.rad3_cneg*(…))
```

The sum over j SHALL retain all species; it SHALL NOT be collapsed to a self-interaction term.

Rationale: the `a_i³/a_0³` prefactor makes the steric drive species-dependent; it evaluates to
4.16 for the reference NaCl parameters and is therefore not a normalisation that can be dropped.

**PHY-06.** The solver SHALL assert `Φ = Σ_j N_A a_j³ c_j < 1` at every nonlinear iteration and
SHALL fail with the offending coordinate if the assertion is violated. `β_i` is singular at
`Φ = 1`.

**PHY-07.** The flow SHALL be solved on `Ω_w` in the variable-density incompressible formulation
of Axelsson et al. (2015), as three equations:

```
u·∇ϱ = 0                                             (density continuity)
(u·∇)(ϱu) + ∇·σ = f                                  (momentum)
∇·(ϱu) − u·∇ϱ = 0                                    (velocity continuity)
σ = p I − η [ ∇u + (∇u)ᵀ ]
```

In the reference model the density-continuity contribution is supplied as the hand-added weak term
`(u*d(rho,r) + w*d(rho,z))*test(p)`.

**PHY-08.** The body force SHALL be the electrostatic force on the mobile ionic charge only:

```
f = ρ_ion E = −( F Σ_i z_i c_i ) ∇φ
```

Rationale: the published model contains no dielectric-gradient (Korteweg–Helmholtz) body force
`−½|∇φ|²∇(ε_0 ε_r)` and no dielectric-decrement term `−½|∇φ|² ∂ε/∂c_i` in the Nernst–Planck flux,
although `ε_r` varies with `⟨c⟩`; the model report records `spf.Fr = es.Er*scd_ions` and
`spf.Fz = es.Ez*scd_ions` and nothing further. Both terms are available together behind one switch
(§4.5), default off. The published agreement with experiment was obtained without them, and
including one without the other is thermodynamically inconsistent.

**PHY-09.** Boundary conditions SHALL be as follows.

| Boundary | φ | c_i | u, p |
|---|---|---|---|
| `Γ_w,c` (cis) | `φ = 0` | `c_i = c_bulk` | `σ·n = 0` (no normal stress) |
| `Γ_w,t` (trans) | `φ = V_bias` | `c_i = c_bulk` | `σ·n = 0` |
| `Γ_p+m` (fluid to protein, fluid to membrane) | continuity of `n·D`, `D = ε_0 ε_r ∇φ` | `n·J_i = 0` | `u = 0` (no-slip) |
| `Γ_m` (exterior membrane boundary) | `n·D = 0` (zero charge) | not solved | not solved |
| Analyte surface (when present) | dielectric interface, optional `σ_s` | `n·J_i = 0` | `u = 0` |
| `r = 0` (axis) | natural | natural | `u_r = 0` (essential) |

Rationale: `∂_r φ = ∂_r c_i = ∂_r u_z = 0` on the axis are natural conditions under the `r`-weighted
axisymmetric forms. Imposing them as Dirichlet conditions is a modelling error.

### 4.3 Empirical corrections

**PHY-10.** Every concentration- and wall-dependent property SHALL be evaluated as
`X(⟨c⟩, d) = X⁰ · f^c(c̄) · f^w(d̄)`, with `c̄ = ⟨c⟩/(1 M)`, `d̄ = d/(1 nm)`.

**PHY-11.** The functional forms SHALL be:

| Property | `f^c` | `f^w` |
|---|---|---|
| `D_i` | `(1 + P₁c̄^½ + P₂c̄ + P₃c̄^{3/2} + P₄c̄²)⁻¹`, separate coefficients per ion | `1 − exp(−P₁(d̄ + P₂))` |
| `μ_i` | same form, own per-ion coefficients | `1 − exp(−P₁(d̄ + P₂))`, same coefficients as `D_i` |
| `η` | `1 + P₁c̄^½ + P₂c̄ + P₃c̄² + P₄c̄^{7/2}` (Jones–Dole) | `1 + exp(−P₁(d̄ − P₂))` |
| `ϱ` | `1 + P₁c̄ + P₂c̄²` | — |
| `ε_r,f` | `1 − (1 − P₁/P₀)·L(3P₂c̄/(P₀ − P₁))`, `L(x) = coth x − 1/x` | — |

The two wall functions carry opposite offset signs, `(d̄ + P₂)` for `D` and `μ` and `(d̄ − P₂)` for
`η`; both are verified in §4.6.

**PHY-12.** The coefficients SHALL be those of the COMSOL model report
(`npgrid_clya_v8_NaCl_report.mph`, COMSOL 5.4 build 388, 2020-05-22) for NaCl at 298.15 K, at the
precision below.

| Quantity | `X⁰` | P₁ | P₂ | P₃ | P₄ | Cap at 5.3 M |
|---|---|---|---|---|---|---|
| `D_Na⁺` | 1.334 × 10⁻⁹ m² s⁻¹ | 0.202 | −0.3048 | 0.219 | −0.03124 | 0.81 × 10⁻⁹ m² s⁻¹ |
| `D_Cl⁻` | 2.032 × 10⁻⁹ m² s⁻¹ | 0.149 | −0.04933 | 0.03392 | 0.01431 | 1.07 × 10⁻⁹ m² s⁻¹ |
| `μ_Na⁺` | 5.192 × 10⁻⁸ m² V⁻¹ s⁻¹ | 0.7907 | −0.3529 | 0.1459 | 0.009241 | 1.74 × 10⁻⁸ m² V⁻¹ s⁻¹ |
| `μ_Cl⁻` | 7.909 × 10⁻⁸ m² V⁻¹ s⁻¹ | 0.6289 | −0.4286 | 0.2123 | −0.01068 | 3.21 × 10⁻⁸ m² V⁻¹ s⁻¹ |
| `η` | 8.904 × 10⁻⁴ Pa s | 0.007558 | 0.07769 | 0.01192 | 5.951 × 10⁻⁴ | 1.75 × 10⁻³ Pa s |
| `ϱ` | 997.0 kg m⁻³ | 0.04047 | −6.149 × 10⁻⁴ | — | — | 1.19 × 10³ kg m⁻³ |
| `ε_r,f` | 78.15 (`P₀`) | 30.08 (`epsr_ms`) | 11.5 (`epsr_alpha`) | — | — | 42.67 |
| `f^w` for `D`, `μ` | — | 6.2 nm⁻¹ | 0.01 nm | — | — | — |
| `f^w` for `η` | — | 3.36 nm⁻¹ | 1.47 × 10⁻¹ nm | — | — | — |
| `t_Na⁺` (auxiliary) | 0.3963 | 9.38 × 10⁻² | 2.86 × 10⁻³ | −1.88 × 10⁻² | 4.51 × 10⁻³ | — |

Fit standard errors and R² (0.99 throughout, except 0.97 for the η wall function and 0.98 for
`t_Na⁺`) are carried in `data/corrections/willems2020_nacl.yaml`. The transport-number fit is
auxiliary, not evaluated at solve time: it derives per-ion mobilities from molar conductivity via
`μ_i(c) = Λ(c) t_i(c) / (z_i F)`, `t_Cl = 1 − t_Na`. Self-consistency values a conformance test
SHALL reproduce: `f^w_D(0) = 0.06`, `f^w_D(0.75 nm) = 0.99`, `η⁰/η^w(0) = 0.37`,
`η⁰/η^w(1.45 nm) = 0.99`.

NOTE: the density coefficients differ from the thesis table by more than rounding, `P₁ = 0.04047`
(thesis 4.06 × 10⁻²) and `P₂ = −6.149 × 10⁻⁴` (thesis −6.39 × 10⁻⁴, 3.8 % apart). The COMSOL values
govern.

**PHY-13.** The fits are valid over 0–5.3 M. Above 5.3 M every property SHALL be clamped to its
cap value from the table above, and each clamp activation SHALL be logged with the location and
property. Diffusivities between 4 M and 5.3 M are extrapolated (no experimental data above 4 M)
and SHALL be documented as such.

**PHY-14.** `μ_i` SHALL be derived from `D_i⁰`, not fitted independently. The reference model sets
`l0 = e² N_A /(k_B T) · D0` and `mu = l0 · L(c) · f_w(d) / F²`, that is

```
μ_i = D_i⁰ · L_i^c(⟨c⟩) · f_i^w(d) / (RT)
```

where `L_i^c` are the conductivity-fitted coefficients (`l1…l4` above) and `f_i^w` the shared ion
wall function. In this form `μ_i` is a molar mobility in mol m² J⁻¹ s⁻¹ and the drift term carries
an explicit factor F; multiplying by F recovers the tabulated `μ_i` in m² V⁻¹ s⁻¹ used in PHY-04.

Rationale: `μ_i⁰ = D_i⁰/V_T` therefore holds at infinite dilution by construction. At finite
concentration `D` and `μ` carry different concentration corrections (`cdf.D_*` fitted to
self-diffusion data, `cdf.L_*` to conductivity data), so `D_i/μ_i` drifts to 1.2–1.7 × kT/e between
0.15 M and 3 M. Poisson–Boltzmann is therefore a separate model, not the PNP solver at zero bias.
Tests SHALL assert the expected drift profile rather than `D_i/μ_i = kT/e`.

**PHY-15.** The implementation SHALL NOT apply a reduction of ion motility by the ratio of ion
radius to pore radius. If such a correction is added later it SHALL be an opt-in experimental
model.

Rationale: Simakov and Pederson include this term; the source work excluded it, extrapolation to
ions whose hydrodynamic radius is comparable to a solvent molecule being questionable.

### 4.4 Fixed charge and dielectric model

**PHY-16.** The volumetric fixed charge `ρ_pore` SHALL be produced by the following pipeline.

| Step | Operation | Normative settings |
|---|---|---|
| 1 | Structure preparation | strip waters and ligands, verify oligomeric state, fill loops |
| 2 | Ensemble | aligned MD frames (reference: 50, from the last 5 ns of a 30 ns run) |
| 3 | Protonation, partial charges | PDB2PQR 3.7+ driving PROPKA at pH 7.5 with the CHARMM force field: `--ff=CHARMM --ffout=CHARMM --with-ph=7.5 --titration-state-method=propka --drop-water --keep-chain`; record `Q_net = Σ_i q_i` |
| 4 | Per-atom smearing | normalised 3D Cartesian Gaussian, `σ_i = 0.5 · R_i` (`R_i` from the PQR); grid 0.005 nm; extend ≥ 4σ_max beyond the protein |
| 5 | Azimuthal projection | bin to (r, z) by exact annular volume `π(r_out² − r_in²)Δz`; average over frames and over the Cₙ group |
| 6 | Assembly | `scd_pore = if(r < 0.01[nm], 0, e_const * rhoq_pore(r,z) / (2*π*r))` [C m⁻³] |
| 7 | Conservation check | `\|∫ρ_pore · 2πr dr dz − Q_net\| / \|Q_net\| < 10⁻³` |

**PHY-17.** Smearing SHALL be performed in 3D Cartesian space and only then averaged azimuthally.
A Gaussian applied directly in (r, z) leaks charge across `r = 0` and SHALL NOT be used.

**PHY-18.** The azimuthal contribution of each atom SHALL carry the `1/(2π r)` factor and the axis
guard `r < 0.01 nm → 0` of the reference model. Deposition SHALL conserve charge, by quintic
B-spline (PME `spl4`-equivalent) partition-of-unity or by renormalising each atom's kernel to
`δ_i`.

**PHY-19.** The conservation assertion of step 7 SHALL be evaluated on the deployed finite-element
mesh, not on the source Cartesian grid. Per-z-slice cumulative charge SHALL additionally be checked
against the PQR sorted by z.

Rationale: the axis guard deletes charge, and bin-centre division by `2πr` near the axis can be
wrong by orders of magnitude. A globally satisfied check can hide a compensating Jacobian error,
which the per-slice check detects.

**PHY-20.** Relative permittivities SHALL be:

| Domain | `ε_r` | Source | Status |
|---|---|---|---|
| `Ω_p` (protein) | 20 | Li/Li/Zhang/Alexov 2013 | calibration parameter, reported in every output |
| `Ω_m` (membrane) | 3.2 | Gramse 2013 (DPhPC) | fixed |
| `Ω_w` (electrolyte) | `78.15 · f^c(c̄)` per PHY-11 and PHY-12 | Gavish 2016 | concentration-dependent |
| `Ω_a` (analyte) | 20 by default, as for `Ω_p` | Li/Li/Zhang/Alexov 2013 | calibration parameter, reported in every output |

The dielectric and ion-exclusion contours SHALL be built from the same Gaussian density field,
with the transition to `ε_w` smoothed over 1–2 Å and the ion-exclusion contour offset outward by
the hydrated-ion radius. `ε_p` and that offset are fitted, not measured, and SHALL be surfaced in
the case file.

### 4.5 Model variants and switches

**PHY-21.** The following physics models SHALL be selectable by name in the case file.

| Model | Equations solved | Corrections |
|---|---|---|
| `epnp-ns` | Poisson + size-modified NP + variable-density NS | all, per §4.3 |
| `pnp-ns` | Poisson + NP + NS | none (`β_i = 0`, all factors 1) |
| `pnp` | Poisson + NP, `u ≡ 0` | selectable |
| `pb` | nonlinear Poisson–Boltzmann | n/a |
| `pb-linear` | linearised Poisson–Boltzmann (Debye–Hückel) | n/a |
| `poisson` | Poisson only, prescribed `ρ_ion` or none | n/a |

Classical PNP-NS SHALL be recovered exactly by setting `β_i = 0` and
`ε_r,f^c = D_i^c = μ_i^c = η^c = ϱ^c = 1` and `D_i^w = μ_i^w = η^w = 1`; no separate code path is
permitted for it.

**PHY-22.** The corrections SHALL be independently switchable, each resolving to a named model in
the correction registry, with "off" a named model rather than a code branch.

| Switch | Default | Effect when off |
|---|---|---|
| `diffusivity_correction` | on | `f_D^c = f_D^w = 1` |
| `mobility_correction` | on | `f_μ^c = f_μ^w = 1` |
| `viscosity_correction` | on | `f_η^c = f_η^w = 1` |
| `permittivity_correction` | on | `ε_r,f = 78.15` |
| `density_correction` | on | `ϱ = 997.0 kg m⁻³` |
| `steric` | on | `β_i = 0` |
| `variable_density_flow` | on | constant-density Stokes/NS |
| `inertia` | on | Stokes flow (reference model retained inertia; Re ≈ 10⁻⁴) |
| `dielectric_gradient_forces` | off | no Korteweg–Helmholtz body force, no dielectric-decrement term in the NP flux |

**PHY-23.** `dielectric_gradient_forces` SHALL enable both the momentum term
`−½|∇φ|²∇(ε_0 ε_r)` and the Nernst–Planck term `−½|∇φ|² ∂ε/∂c_i` together, and SHALL NOT permit
either in isolation. Enabling it is a deviation from the validated model and SHALL be recorded in
the run provenance.

**PHY-24.** Poisson–Boltzmann SHALL be implemented as a distinct model, not as the PNP solver
evaluated at zero bias (see PHY-14 and ADR-005).

### 4.6 Errata in the source material

Each row records a statement in the published source that the implementation SHALL NOT follow.
Evidence values are computed, not asserted.

| # | Source statement | Correct form | Evidence |
|---|---|---|---|
| 1 | Thesis eq. 5.11 prints the D/μ wall function as `1 − exp(−P₁(d̄ − P₂))` | offset is `(d̄ + P₂)`, as in Table 5.1 | `(d̄+P₂)`: f(0) = +0.0601, f(0.75) = +0.9910, matching the stated 0.06 and 0.99; `(d̄−P₂)`: f(0) = −0.0640, negative at the wall |
| 2 | ESI writes the wall coefficient as `0.62e1`, read in circulation as 62 or 0.62 | `P₁ = 6.2 nm⁻¹` (Table 5.2, Simakov 2010) | f(0)/f(0.75): 62 → 0.4621/1.0000; 0.62 → 0.0062/0.3757; 6.2 → 0.0601/0.9910, the only match |
| 3 | Table 5.1 lists `μ_Na⁰ = 5.192 × 10⁻⁴ m² V⁻¹ s⁻¹` | exponent is 10⁻⁸, per Table 5.2 note (b) | `μ = D⁰/V_T`, `V_T = 25.693 mV`: 5.1922 × 10⁻⁸ (Na⁺), 7.9089 × 10⁻⁸ (Cl⁻), matching Table 5.2 to four figures |
| 4 | Text states `η(c > 5.3 M) = 1.75 × 10⁻⁴ Pa s` | cap is 1.75 × 10⁻³ Pa s | the fit at 5.3 M gives 1.752 × 10⁻³ Pa s; 1.75 × 10⁻⁴ is below pure water (8.904 × 10⁻⁴) while salt raises viscosity. Other caps verified: ϱ = 1194 kg m⁻³, `D_Na` = 8.13 × 10⁻¹⁰, `D_Cl` = 1.071 × 10⁻⁹ m² s⁻¹ |
| 5 | Table 5.2 lists viscosity `P₀ = 0.8904` under a 10⁻⁴ scaling note, implying 8.904 × 10⁻⁵ Pa s | `η⁰ = 8.904 × 10⁻⁴ Pa s`; the scaling is 10⁻³ | Hai-Lang 1996 gives 8.904 × 10⁻⁴ Pa s for water at 298.15 K; 8.904 × 10⁻⁵ is an order of magnitude below any aqueous value |
| 6 | Thesis prints the permittivity cap `ε_r(5.3 M) = 42.12`, reproducible only from the authors' own Buchner-1999 fit (29.50, 11.74) | the model used Gavish's NaCl parameters (30.08, 11.5); the cap is 42.67 | the model parameter table and the solver log both record `epsr_ms = 30.08`, `epsr_alpha = 11.5`; these give 42.67 at 5.3 M against the Buchner fit's 42.13, so the printed cap is stale. An earlier author recollection favouring the Buchner fit is superseded by the model file |
## 5. Software design description

### 5.1 Architectural overview

The product is a linear pipeline of pure, cacheable stages. A stage takes typed inputs and emits a
typed, serialisable artefact carrying a content hash; every stage runs standalone, and every
artefact may be inspected, exported, edited and substituted by hand (FR-27). The Python API, the
CLI and the desktop shell drive the same stage objects (IF-01, IF-02, IF-09).

```
 PDB/mmCIF ──┐
 trajectory ─┼─►[1 structure]─►[2 density]─┬─►[3 symmetry]─►[4 contour]─►[5 CAD]─►[6 mesh]─┐
 pH, force field ┘                         │                                               │
                                           └─►[7 charge]────────────────────────────────────┤
 electrolyte, corrections ────────────────────►[8 materials]────────────────────────────────┼─►[9 case]
 bias, BCs, analyte ───────────────────────────────────────────────────────────────────────►┘     │
                                                                                                  ▼
                                                    [12 report / export]◄──[11 QoI]◄──[10 solve]
```

| Module | Responsibility |
|---|---|
| `core/` | Units, constants, validation, provenance, caching, logging |
| `structure/` | PDB/mmCIF and trajectory IO, alignment, symmetry-axis detection |
| `density/` | Gaussian smearing to grid, ensemble averaging, grid IO |
| `symmetry/` | Cₙ averaging, azimuthal reduction to (r, z), variance diagnostics |
| `geometry/` | Contour extraction, polyline conditioning, CAD assembly, analyte bodies |
| `mesh/` | Mesher adapters (netgen, gmsh), size fields, boundary layers, quality gates |
| `charge/` | PDB2PQR driver, partial charges, smearing, axisymmetric projection, dielectric |
| `materials/` | Electrolyte models and the pluggable correction registry |
| `physics/` | Weak forms: Poisson, Nernst–Planck, Navier–Stokes; axisymmetric measures |
| `solve/` | Backend adapters, continuation ladder, nonlinear and linear strategies, warm start |
| `post/` | QoI extraction: current, transport number, EOF, rectification, forces |
| `sweep/` | Parameter sweeps, job-array dispatch, result collection |
| `io/` | Case-file schema, result store, provenance manifests |
| `cli/` | Command-line entry points |
| `gui/` | Desktop application |
| `validation/` | Benchmarks, MMS, COMSOL comparison harness, regression fixtures |

### 5.2 Pipeline stages

| # | Stage | Inputs | Outputs | Tools | Validation gate |
|---|---|---|---|---|---|
| 1 | Structure ingestion and alignment | PDB/mmCIF, optional trajectory, expected point group | Aligned ensemble; Cₙ axis on z at r = 0 | MDAnalysis 2.10+ (LGPLv3), `AlignTraj`, `rotation_matrix`; MDTraj as alternative reader; PDBFixer or Modeller for missing loops | Oligomeric state matches (ClyA 12, αHL 7, MspA 8); abort on missing chains (FR-03) |
| 2 | Density map | Aligned ensemble, grid spacing, kernel | 3D density map | Vectorised scipy Gaussian deposition over a local stencil, per-atom width from the van der Waals radius, sharpness 0.93; MDAnalysis `DensityAnalysis` for accumulation and units; `gridData` IO; optional `gmx densmap` check | Grid spacing 0.25–0.5 Å (FR-04) |
| 3 | Symmetry reduction to (r, z) | 3D map, n | (r, z) map; residual azimuthal variance | numpy; `np.bincount` with voxel-volume weights; `mdahole2` (HOLE) | Variance emitted with the geometry (FR-06, CON-04); radius profile within tolerance of the HOLE profile |
| 4 | Contour extraction and conditioning | (r, z) map, isolevel, smoothing and simplification parameters | Closed conditioned polyline | scikit-image, Shapely, scipy (all BSD-3), per §5.2.1 | §5.2.1 (FR-08) |
| 5 | CAD assembly | Polyline, membrane specification, reservoir radius, optional analyte | Fragmented (r, z) region, domains and boundaries tagged | `netgen.occ` (LGPL-2.1, OpenCASCADE, in-process) primary; Gmsh OCC Python API (GPLv2+) optional | All bodies fragmented and imprinted, interfaces conformal, no gap or overlap at the membrane-to-pore junction (FR-09) |
| 6 | Meshing | Fragmented region, size fields | Graded triangular mesh | Netgen (LGPL-2.1) default, Gmsh (GPLv2+) optional, behind the mesh adapter | §5.2.2 (FR-10, QR-12) |
| 7 | Charge assembly | Prepared ensemble, pH, force field | ρ_pore(r, z), Q_net, dielectric field, ion-exclusion surface | PDB2PQR 3.7+ (BSD-3) driving PROPKA3; quintic B-spline (`spl4`) deposition; APBS 3.4.1 (BSD-3) cross-check; settings per PHY-16 | Charge conservation to 10⁻³ of Q_net on the deployed FE mesh, plus the per-z-slice cumulative check (FR-14, QR-03, PHY-19) |
| 8 | Materials | Electrolyte specification, correction model names, coefficient files | D_i, μ_i, η, ϱ, ε_r as fields in ⟨c⟩ and d | Correction registry, `data/corrections/willems2020_nacl.yaml` | Conformance values of §4.3 reproduced; clamps above 5.3 M logged with location and property (PHY-13) |
| 9 | Case assembly | Mesh, charge and dielectric fields, materials, boundary conditions, bias, analyte, numerics | Resolved case document, assembled discrete problem | `io/` schema validator, `physics/` model registry | Schema `nanopnp/case/v1` validates, unknown keys rejected with a diagnostic naming the key (IF-03); round trip semantically identical (FR-26) |
| 10 | Solve | Assembled problem, continuation ladder, optional warm start | Converged fields, iteration history | NGSolve 6.2.2606+ (LGPL-2.1), damped Newton; UMFPACK (GPL-2+) or scipy SuperLU (BSD) (CON-08) | No negative concentration at any nonlinear iterate; ladder completed to the target rung (FR-17); §6.5, §6.6 govern |
| 11 | QoI extraction | Converged fields | I, t₊, RR, EOF rate, F^em(z), F^hd(z), ΔU(z) | Domain/indicator form and variational reaction flux, both implemented | The two routes agree within the stated tolerance, checked in CI (FR-23, QR-04); §6.7 governs |
| 12 | Reporting and export | Results, artefact hashes, environment | Figures, XDMF/HDF5 fields, dataset, case file, manifest | `io/`, `sweep/` result store | Manifest complete and sufficient to reconstruct the run (FR-25, QR-08) |

Design notes, recorded where an implementer would otherwise choose wrongly.

| Stage | Note |
|---|---|
| 1 | The Cₙ axis comes from chain-permutation superposition: superpose chain A onto chain B, take the rotation's eigenvector of eigenvalue 1 (FR-02). Principal axes are unusable, a truncated cone having near-degenerate inertia axes that drift between frames. |
| 2 | Histogram plus uniform `gaussian_filter` is rejected: van der Waals-weighted smearing preserves the exclusion surface, uniform post-smoothing rounds the constriction. The grid is not coarsened, the *trans* constriction being about 3.3 nm across with a contour position that moves measurably with resolution. |
| 3 | The n rotated copies are averaged before azimuthal averaging. Binning is area-weighted over exact annular volumes (about 4 voxels per annulus near r = 0, about 600 at r = 5 nm), innermost 2–3 bins interpolated. A 1° axis error adds about 0.2 nm of apparent radius to a 3.3 nm constriction. |
| 3, 5 | The bilayer is absent from the density map. It is defined analytically in (r, z) over the hydrophobic belt and fragmented against the pore contour. |
| 5 | Reference geometry: reservoir half-disc R = 250 nm, membrane thickness 2.8 nm, `z_cis` = 12.25 nm, `z_trans` = −1.85 nm. The membrane is a quadrilateral, not a rectangle: vertices (r = 2, z = −1.4), (3.5, +1.4), (250, +1.4), (250, −1.4) nm, inner edge slanted to meet the pore's outer surface. Code assuming a rectangle leaves a wedge of gap or overlap at the junction. CadQuery and build123d are 3D-solid-centric and unused; pythonocc serves BRep edge cases only. |

#### 5.2.1 Contour conditioning and its gate

Pipeline: `find_contours` (sub-pixel marching squares) at isolevel 0.25, longest closed contour,
Taubin λ|μ smoothing (volume-preserving, where Chaikin shrinks), Shapely `simplify`
(Douglas–Peucker, tolerance about 0.02 nm), minimum vertex spacing, optional periodic B-spline fit.

| Gate criterion | Threshold |
|---|---|
| `LinearRing.is_valid`, `is_simple` | both true |
| Minimum vertex spacing | ≥ target element size |
| Minimum local feature size | > 2 × target element size |
| Loop topology | single closed loop, no detached islands |
| Radius profile | within tolerance of the HOLE profile |

Rationale (feature size): near-tangential self-approaches at the constriction generate slivers the
mesher cannot repair.

The reference pore boundary is published in the COMSOL model report as a closed 190-vertex polygon
(r ≈ 1.65–5.66 nm, z from −1.85 to 12.25 nm) and SHALL be shipped as a regression fixture (§7.2),
so solver work proceeds on the reference polygon without the contour pipeline. The table is held in
the repository as `data/geometry/clya_as_radial_geometry.csv`, supplied by the reference model's
author: 185 `r,z` pairs in nm tracing a simple closed loop, r ∈ [1.65, 5.66], z ∈ [−1.85, 12.25],
enclosing 26.4939 nm².

NOTE (the membrane junction): the membrane's slanted inner edge, (2, −1.4) → (3.5, +1.4), lies
strictly **inside** the pore body along its whole length. At z = −1.4 the pore spans
r ∈ [1.725, 2.7524] and the edge enters at 2.0 — 0.275 nm clear of the lumen wall and 0.752 nm clear
of the outer surface; at z = +1.4 the pore spans r ∈ [2.96, 4.88] and the edge leaves at 3.5, with
0.540 and 1.380 nm of clearance. The assembled membrane is therefore the quadrilateral **minus** the
pore body, and it meets the pore on the pore's own outer surface, not on the drawn edge. The slant is
necessary rather than cosmetic: the lumen wall passes through (2.0, 0) exactly and has opened to
r = 2.96 by z = +1.4, so a vertical inner edge at r = 2 would place membrane material inside the
electrolyte for every z > 0. The cap's underside is re-entrant, so the membrane also fills a cleft
beneath it and its boundary is not monotone in z; it remains one connected domain, which is what
makes the reported domain count come out at three — pore body, membrane, and a single electrolyte,
the lumen joining the two reservoirs.

NOTE (vertex counts): the model report's geometry section records **190 vertices for the pore
polygon** and **3 domains, 198 boundaries and 196 vertices for the assembled region**. Earlier
revisions of this document attached the geometry-wide 196 to the pore boundary, and identified the
extra six as the membrane quadrilateral's own corners; both are corrected here against the delivered
table. Assembling as above, the region adds to the 190-vertex polygon: the two points where the
planes z = ±1.4 cut the pore's outer surface, each splitting a polygon edge (+2 vertices, +2 edges);
the membrane's two outer corners on the reservoir arc at r = √(250² − 1.4²) = 249.99608 nm (+2, +2);
and the arc's two endpoints on the axis at (0, ±250) (+2, +2). Closing the region takes six further
edges — the axis, the `cis` and `trans` arc segments, the `membrane_outer` arc between the corners,
and the membrane's two faces at z = ±1.4. That is 190 + 6 = **196 vertices** and
190 + 2 + 6 = **198 boundaries**, both as reported; Euler closes it, 196 − 198 + 4 = 2 over the three
domains and the unbounded face; and 196 is also the mesh's 196 vertex elements (§5.2.2), one per
geometry vertex.

The delivered table carries 185 vertices, five short of the report's 190, and — unlike the report's
polygon, which the count above requires to be cut at both planes — it already has a vertex exactly on
the cis plane at (4.88, +1.4), so under the same construction it assembles to 190 vertices and 192
boundaries (190 − 192 + 4 = 2 likewise). The difference is recorded, not reconciled: it changes
neither the geometry the table describes nor anything computed from it. The model report governs
(`CLAUDE.md`). OPN-05 stays open on that count alone.

NOTE (what `nanopnp.mesh.reference` assembles): 193 vertices and 195 edges, three more of each than
the count above, and both deviations are deliberate. Two come from breaking the side on `r = 0` into
three collinear segments at the pore's axial extent: OCC keeps collinear segments as separate edges,
the pore polygon never touches the axis, and this is therefore the only way §5.2.2's 0.075 nm
"symmetry axis inside pore" can be applied as a size field at all. The third is the seam OCC places
at parameter zero on a closed circle, at (250, 0), which survives the clip to `r ≥ 0` and halves
`membrane_outer` into two arcs meeting there — a closed circle has a seam somewhere, and this one
costs one vertex element on the reservoir rim. The named edges are then 186 around the pore
(151 `wall`, 35 `interface`), 3 `axis`, 2 `membrane`, 2 `membrane_outer`, and one each of `cis` and
`trans`. VER-28 asserts these counts.

NOTE (the conditioning gate and a supplied fixture): the gate above applies to contours the FR-08
pipeline *produces*. The delivered reference polygon does not meet two of its criteria at the
reference wall size of 0.05 nm — minimum vertex spacing 0.0361 nm, with 10 of its 185 edges shorter
than that wall size, and minimum local feature size 0.0806 nm against a 0.1 nm threshold — and yet
it is what the reference mesh of §5.2.2 was built from, at that wall size, reaching minimum element
quality 0.6378. A supplied profile fixture is therefore NOT gated on those two criteria. It is gated
on validity, simplicity and loop topology, and its measured spacing and feature size are recorded in
its provenance block, so that a mesh size chosen against it can be checked rather than assumed.

#### 5.2.2 Meshing

The mesh resolves a Debye length of 0.18–1.4 nm against a 250 nm reservoir, a scale span of 10³,
without degenerate elements at the pore, membrane and reservoir triple junctions or at r = 0.
Near-wall target h₁ ≈ λ_D/5 (about 0.04 nm at 3 M), grading to 5–10 nm in the far reservoir,
expected size 5 × 10⁴ to 2 × 10⁵ cells.

Isotropic graded refinement is the default strategy (FR-10). The reference model reached the
published results with free triangular meshing, no boundary layers anywhere in the sequence, and
isotropic grading to 0.05 nm at the pore wall.

| Region | Max element | Min element | Curvature factor | Growth rate |
|---|---|---|---|---|
| Global ("Finer" preset) | 10 nm | 0.001 nm | 0.25 | 1.05 |
| Pore boundary | 0.05 nm | 0.001 nm | 0.25 | 1.05 |
| Pore domain ("Extremely fine") | 0.1 nm | 0.004 nm | 0.2 | — |
| Reservoir domain | 2.8 nm | 0.04 nm | — | 1.04 |
| Reservoir outer boundary | 5 nm | 0.025 nm | — | 1.25 |
| Symmetry axis inside pore | 0.075 nm | 0.04 nm | — | — |

That mesh has 120,917 triangles, 1,879 edge elements and 196 vertex elements, minimum element
quality 0.6378, average 0.9765, which set the target. Quality gate, enforced in code: minimum
SICN/gamma > 0.3, an `optimize("Netgen")` pass, worst element and its location reported, run
aborted on failure (QR-12).

NOTE (SICN and gamma): these are two distinct measures and both SHALL be gated. For a straight-sided
triangle, SICN is the signed inverse condition number of the Jacobian taken relative to the unit
equilateral element and gamma is the normalised inradius-to-circumradius ratio `2 r_in / R_circ`;
both equal 1 on the equilateral element and both are scale-invariant. They are not interchangeable:
on the isoceles family over a unit base, `SICN = 0.3` occurs at `gamma = 0.1298` and `gamma = 0.3` at
`SICN = 0.4687`, a factor of 1.6208 in element height (0.215508/0.132966), so a single
"SICN/gamma > 0.3" reading admits
two different meshes. Gamma is unsigned — an inverted equilateral element scores `gamma = 1` and
`SICN = −1` — so gamma alone cannot detect inversion, and `SICN ≤ 0` SHALL be reported as its own
failure ("inverted element") rather than folded into the quality gate. Under the axisymmetric
`r`-weighted forms an inverted element contributes negative volume and nothing else raises.

Anisotropic boundary layers are an optional element-count optimisation (FR-11, post-1.0), not a
dependency of the default path.

| Route | Mechanism and status |
|---|---|
| Geometric, in project code | Offset the conditioned contour inward by a geometric progression (Shapely `buffer(-d)` or `offset_curve`), mesh the strips as structured quads, let the unstructured mesher fill the interior; growth ratio 1.15–1.2 over about 15 layers. Preferred, deterministic. The legacy `parallel_offset` still works in Shapely 2.1.2 but is retained only for backwards compatibility and uses different sign and segment conventions |
| Mesher-native, Netgen | `netgen.meshing.Mesh.BoundaryLayer2(domain, thicknesses, make_new_domain=True, boundaries=[])`, binding C++ `GenerateBoundaryLayer2`. Best-effort: an unresolved August 2024 NGSolve forum report has it failing to fill a zone adjacent to the new advancing front. The 3D `Mesh.BoundaryLayer` now unconditionally raises "Call syntax has changed! Pass a list of BoundaryLayerParameters to the GenerateMesh call instead" |
| Mesher-native, Gmsh | `BoundaryLayer`, `Distance`/`Threshold`, `Min`/`Restrict` size-field algebra, `Fan` points, quads-in-BL. Best-in-class, available only on the optional GPLv2+ backend |

Excluded components (CON-12): MeshPy, maintained at 2026.1 but wrapping Triangle, whose licence
permits distribution as part of a commercial system "ONLY BY DIRECT ARRANGEMENT WITH THE AUTHOR";
TetGen 1.5 (AGPLv3); pygmsh (2022-01) and pygalmesh (2022-09), both stale. The `gmsh` API is called
directly.

#### 5.2.3 Embedded analyte

| Approach | Verdict |
|---|---|
| Body-fitted remeshing per axial position: for each z_a, rebuild the (r, z) geometry with the analyte subtracted and remesh | Specified. In 2D a remesh takes seconds and the positions are embarrassingly parallel |
| ALE or moving mesh | Rejected: needed only for transient trajectories, and with analyte diameter comparable to pore diameter, distortion at the constriction forces a remesh regardless |
| Fictitious domain, immersed boundary or level set | Rejected: a diffuse interface cannot carry a sharp dielectric jump, zero ion flux and no-slip without degrading Debye-layer accuracy |

The analyte is a hard dielectric body with no ion flux, no-slip and a dielectric jump, as at the
pore wall (FR-21). Both charge models ship as named options, a surface charge density and a smeared
volumetric charge, sharing the smearing machinery of §4.4.

### 5.3 Data design

#### 5.3.1 Case file

One declarative YAML document is the unit of reproducibility (IF-03). Everything else is derived.

```yaml
schema: nanopnp/case/v1
name: clya-wt-1M-100mV

inputs:                             # optional; supplied artefacts, §5.3.2
  mesh: {path: clya.msh, format: msh41,
         groups: {lumen: electrolyte, upper: cis, lower: trans,
                  clya: protein, bilayer: membrane,
                  pore_wall: wall, outer_rim: membrane_outer,
                  symmetry_axis: axis}}

structure:
  source: {pdb: 2WCD.pdb, variant: ClyA-AS, chains: all}
  ensemble: {trajectory: eq.xtc, frames: {last_ns: 5, count: 50}}
  symmetry: {point_group: C12, axis: auto}

geometry:
  density:  {grid_spacing_nm: 0.05, kernel: gaussian_vdw, sharpness: 0.93}   # 0.5 Å, as the paper
  contour:  {isolevel: 0.25, smoothing: taubin, simplify_tol_nm: 0.02}
  membrane: {thickness_nm: 2.8, eps_r: 3.2}
  reservoir: {radius_nm: 250}
  analyte:  {shape: prolate_spheroid, a_nm: 2.0, b_nm: 3.0, z_nm: 6.0, charge_e: -8}

charge:
  ph: 7.5
  forcefield: CHARMM
  titration: propka
  smearing: {sharpness: 0.5, grid_spacing_nm: 0.005, axis_cutoff_nm: 0.01}
  eps_protein: 20.0

electrolyte:
  species: [{name: Na+, z: +1}, {name: Cl-, z: -1}]
  concentration_M: 1.0
  temperature_K: 298.15
  parameters: willems2020_nacl      # reference D_i^0, eta^0, rho^0, eps_r,f^0, a_i, a_0
  driver: average                   # PHY-01; `ionic_strength` is a deviation
  corrections:                      # the pluggable registry, §5.5
    diffusivity:  {model: willems2020_nacl, wall: true, concentration: true}
    mobility:     {model: willems2020_nacl, wall: true, concentration: true}
    viscosity:    {model: willems2020_nacl, wall: true, concentration: true}
    permittivity: {model: willems2020_nacl}
    density:      {model: willems2020_nacl}
    steric:       {model: borukhov, a_ion_nm: 0.50, a_water_nm: 0.311}

boundary_conditions:
  bias_V: 0.100
  ground: cis
  walls: {ion_flux: no_flux, slip: no_slip}

physics:                            # the named model of PHY-21
  model: epnp-ns
  flow: true
  variable_density: true
  inertia: true                      # PHY-22; the reference model retained it
  dielectric_gradient_forces: false  # PHY-23; off in the validated model

numerics:
  elements: {phi: P2, c: P2, u: P2, p: P1}
  mesh: {backend: netgen, wall_h_nm: auto, boundary_layer: false}
  nonlinear: {strategy: newton, damping: residual, max_iter: 100, rtol: 1e-6}   # NUM-16
  continuation: default_ladder
  stabilisation: none                # NUM-11; `reference` matches §6.4
  wall_distance: {sources: wall, max_distance_nm: 3.0}                         # PHY-02
  linear: {solver: umfpack}          # see §6.6; MUMPS requires a source build

outputs: [current, transport_numbers, rectification, eof_rate, analyte_force, fields]
```

NOTE (`inputs:`, FR-27): the optional top-level `inputs:` block is hand substitution (FR-27) applied
at stage granularity. Each key names a stage output supplied from outside — a mesh, a charge field,
a dielectric field — by path and format. A stage whose output is supplied does not run, and neither
does anything upstream of it; the substituted file is hashed by content and enters the FR-25
manifest as an input like any other. Releases before v0.9 accept an externally generated mesh
this way, which is what makes the solver core testable ahead of the meshing pipeline (§8.1).

NOTE (`inputs.mesh.groups`, IF-06, QR-12): the mapping reads **file group name → vocabulary name**.
The key is the physical-group name the mesh file carries; the value is the name the solver selects
on. Several file groups MAY map to one vocabulary name — a CAD export routinely splits one physical
wall into several curves — and the reverse is not expressible, which is why the direction is this
way round. The vocabulary is fixed and carries no aliases: materials `electrolyte`, `cis`, `trans`,
`protein`, `membrane`, `analyte`; boundaries `axis`, `wall`, `membrane`, `membrane_outer`, `cis`,
`trans`, `analyte`, `interface`. `protein` is the pore's dielectric body (§2.2), a solid domain
Poisson is solved on and Nernst–Planck and the flow are not; `pore` is deliberately **not** a name,
because it reads as both that body and the lumen fluid, and a mesh that uses it SHALL disambiguate
through the mapping. `interface` is the interior fluid-to-fluid seam a fragmented region carries —
the pore-mouth interfaces the reservoir-to-lumen split leaves behind — and **nothing selects on it**;
it is in the vocabulary because every group must be claimed by some name, and calling an interior
seam `wall` would put it in the PHY-02 distance source set and impose no-slip across the middle of
the electrolyte. Ingestion SHALL abort when any group in the file is left unclaimed by the mapping,
or when any name the resolved run selects on — the boundary-condition names,
`numerics.wall_distance.sources` and the fluid material set — is supplied by no group, and the
diagnostic SHALL name both lists (QR-12). A mapping whose keys are all vocabulary names while its
values are not is almost certainly written backwards, and the diagnostic SHALL say so rather than
reporting every group unclaimed.

NOTE (a group that claims itself, IF-06): a group whose own name is already a vocabulary name needs
no entry in the mapping, and is claimed by that fact. The failure the gate exists to catch is a name
the solver does *not* speak reaching a solve unnoticed, and a name it does speak is not one of
those; requiring `wall: wall` of a mesh this implementation generated would be ceremony that a
reader learns to write without reading. Which names the run selects on is derived from the resolved
case — the model's boundary vocabulary, both electrodes, the species, the fluid material set and
`numerics.wall_distance.sources` — and never from a constant list, so the diagnostic is exactly
true of the run that produced it: *this run will select on this name, and no group supplies it*. A
selection pattern that is not a flat `a|b|c` alternation of literal names SHALL be refused rather
than parsed heuristically, since a requirement derived from a mis-parsed pattern is a gate that can
only pass.

NOTE (a solid without a permittivity, PHY-03, QR-12): `physics.solid_permittivities` is a map from
material name to relative permittivity, defaulting to empty; PHY-20 gives ε_r = 3.2 for the membrane
and 20 for the protein and the analyte, and it is not defaulted because the mesh decides which
solids exist. It is the one member of `physics:` that is not a switch, and the electrostatic models
of PHY-21 carry no solids, so a non-empty map beside one of them SHALL be refused as
§5.3.1's other inapplicable switches are. On an **ingested** mesh, a material that is
neither in the fluid set nor named in `physics.solid_permittivities` SHALL abort the run, naming the
material. Poisson is solved over the whole domain, so the alternative is the electrolyte's ε_r about
24 times too large in a solid — a plausible wrong answer with no solver diagnostic. Meshes built in
process by the benchmark geometries keep the warning they have today; the difference is that an
ingested mesh's material names were not written by this codebase. Rationale: boundary conditions are selected by name and the natural condition under the
`r`-weighted forms is the *free* one (§6.2, NUM-06), so an unmapped wall becomes an open boundary,
the solve converges, and the current is wrong with no residual, no gate and no diagnostic.

NOTE (`electrolyte.parameters`, `electrolyte.driver`): `parameters` names the correction file the
*reference* properties are read from — `D_i^0`, `η^0`, `ϱ^0`, `ε_r,f^0` and the steric diameters
`a_i`, `a_0` — and is separate from the per-property correction models because a classical PNP-NS
run turns every correction to `none` and still needs those values. Steric diameters given under
`corrections.steric` SHALL be checked against that file and SHALL NOT override it: they are fitted
parameters of the correction set (FR-16), and a case file that could override them silently would
be a second source of truth for a physical constant. `driver` selects the argument the
concentration corrections are evaluated at: `average`, `⟨c⟩ = (1/n)Σc_i` (PHY-01), or
`ionic_strength`, which is a deviation from the validated model and is recorded as one.

NOTE (`numerics.nonlinear`): the values shown are the NUM-16 reference settings — the monolithic
damped Newton of the reference model, 100 iterations, relative tolerance 10⁻⁶, tested on the
residual and on the relative update alike. `strategy: hybrid` and `damping: backtracking` select
the NUM-20 fallbacks.

NOTE (`numerics.wall_distance`): `sources` is the boundary-name pattern the PHY-02 distance field
`d` is measured from, and its validated default is the pore wall alone. PHY-02 excludes the
membrane from the source set deliberately, so widening `sources` is a deviation from the validated
model and SHALL be recorded in the run provenance (FR-25). `max_distance_nm` is the saturation
distance beyond which the wall functions are 1 to within round-off.

NOTE (`walls`): the wall values name the condition applied, not its absence. `ion_flux` takes
`no_flux | prescribed` and `slip` takes `no_slip | navier | free`. Under the `r`-weighted forms of
§6.2 the natural condition is the free one, so a value reading as "none applied" would silently
remove no-slip while appearing to be the validated default.

#### 5.3.2 Artefacts and interchange formats

| Stage | Artefact | Format |
|---|---|---|
| 1 | Aligned ensemble, axis transform | Trajectory (DCD, XTC, TRR, NetCDF) plus transform record (IF-04) |
| 2, 3, 7 | Density map, reduced (r, z) map and variance, ρ_pore, dielectric and exclusion fields | OpenDX or CCP4 via GridDataFormats (LGPL) (IF-05) |
| 4 | Conditioned polyline | Vertex table |
| 5 | Tagged (r, z) region | OCC BRep plus tag map |
| 6 | Mesh | Gmsh MSH 4.1 archival, any meshio (MIT) format on read (IF-06) |
| 8 | Resolved material coefficient set | Correction file references and evaluated parameters |
| 9 | Resolved case document | YAML, schema `nanopnp/case/v1` |
| 10 | Field set, iteration history | XDMF with HDF5 heavy data (IF-07) |
| 11, 12 | Scalar QoIs, profiles, figures, dataset, manifest | Result store record, figure files, manifest |

Every artefact carries a content hash over a canonical serialisation of its payload and the
parameters that produced it. The hash is the cache key: a stage whose input hashes and parameters
are unchanged is not recomputed, and a hand-substituted artefact registers as a changed input.
MSH 4.1 is archival because it is the only format in the toolchain carrying physical-group tags,
higher-order elements and mixed element types without loss.

NOTE (canonical serialisation): the hash is taken over the *validated* artefact payload and the
producing parameters, not over their file text. Mappings are serialised with sorted keys, sequence
order is preserved as meaning, floats are encoded by `float.hex()` with `-0.0` normalised to `0.0`,
arrays by dtype, shape and a digest of their contiguous bytes, and input files by the digest of
their contents rather than by their path. Wall-clock fields such as `created_at` are recorded beside
the hash and excluded from it, so that re-running a case reproduces the hash. A stored hash is
re-computed on load as a cross-check: a mismatch means the artefact was edited by hand, which FR-27
permits, and is recorded in the manifest as a substituted input rather than aborting the run.

#### 5.3.3 Provenance manifest

Emitted with every result artefact (FR-25, IF-08) and sufficient alone to reconstruct the run
(QR-08).

| Field group | Contents |
|---|---|
| Inputs | Content hash of every input file and every upstream artefact |
| Environment | Package version, version of every library in §2.6, Python version, operating system |
| Geometry and mesh | Mesh hash, element counts, quality statistics, size-field settings |
| Charge | Q_net, force field, pH, titration method, conservation residual |
| Materials | Correction model names, version of each parameter data file, clamp activations |
| Solver | Physics model, element orders, continuation rungs, nonlinear and linear settings, iteration counts |
| Stabilisation | The stabilisation mode that produced the number (§6.4) |
| Deviations | Every switch set away from the validated default, including `dielectric_gradient_forces` (PHY-23) |

### 5.4 Component design

#### 5.4.1 Backend abstraction layer

`physics/` expresses the weak forms once against a thin internal interface, with one production
implementation on NGSolve (QR-13, CON-06). Its purpose is to make a future DOLFINx backend for 3D
and MPI bounded work.

| In scope | Out of scope |
|---|---|
| `FunctionSpace`, product spaces | A general symbolic layer or user-facing PDE language (§5.5) |
| `TrialFn`, `TestFn`, `grad` | Mesh generation, held by the mesh adapters |
| `dx_axi`, the axisymmetric measure | Continuation, warm start, linear-solver selection, held by `solve/` |
| `ds`, boundary measures | IO, provenance and caching, held by `core/` and `io/` |
| `Coefficient` | Any construct required by only one backend |

#### 5.4.2 Correction-model interface

A correction model is a class implementing `evaluate(c_avg, wall_distance) -> value` plus
`parameters` and `provenance`, registered by string name, with fit coefficients in versioned data
files such as `data/corrections/willems2020_nacl.yaml` (FR-16). The case file names models by
string. Disabling a correction selects the `none` model rather than taking a code branch (PHY-22).

#### 5.4.3 Physics-model interface

A `PhysicsModel` declares its field set, its weak-form contributions, its boundary-condition
vocabulary and its default solve strategy (FR-20). The geometry, mesh, charge, solver,
post-processing, sweep, provenance and interface layers are model-agnostic, so adding a model
changes none of them.

### 5.5 Extension points

Pluggability has two levels, matching the two kinds of change users make (QR-14).

| Level | Unit of extension | Requires | Obtained free |
|---|---|---|---|
| 1, correction models | A versioned data file naming a registered model and its coefficients | No code | Recording of the model version on every result; correction-by-correction switching as a configuration sweep |
| 2, physics models | One class against the §5.4.3 interface | One file | Meshing, geometry, charge assembly, continuation, QoI extraction, sweeps, provenance and the GUI |

Shipped physics models (PHY-21, FR-18, FR-19).

| Model | Fields | Notes |
|---|---|---|
| `epnp-ns` | φ, c_i, u, p | The validated default |
| `pnp-ns` | φ, c_i, u, p | The same model with corrections off; a configuration, not code |
| `pnp` | φ, c_i | No flow coupling |
| `pb` | φ | Nonlinear Poisson–Boltzmann, equilibrium; a separate model, not the PNP solver at zero bias (PHY-14, PHY-24) |
| `pb-linear` | φ | Debye–Hückel; an initialiser and the basis of the DWR error estimator |
| `poisson` | φ | Electrostatics only; the APBS cross-check target |

Since ePNP-NS reduces exactly to PNP-NS at β_i = 0 with all f^c = f^w = 1, the PNP-against-ePNP
comparison and the contribution of each individual correction are configuration sweeps, and are the
project's primary differential-testing instrument (§7.4).

Boundary of the framework (N1): a nanopore transport solver with swappable physics models, which
will not become a general symbolic PDE framework. Users do not write weak forms. A model may be
swapped or extended; an unrelated multiphysics problem may not be posed, and users wanting
arbitrary weak forms should use NGSolve or FEniCS directly. Deriving new correction
parameterisations from MD is a separate later tool (N6).

### 5.6 Architecture decisions

#### ADR-001 FEM backend

Decision: NGSolve 6.2.2606+ (LGPL-2.1) as the single production backend, behind the abstraction of
§5.4.1.

| Alternative | Assessment |
|---|---|
| DOLFINx 0.11 | Best numerics, best documentation, PETSc SNES, largest community. JIT-compiles, so the end user needs a C++ compiler; its README states PETSc and petsc4py are not available on Windows and that Visual Studio must be installed. Heavyweight conda environment. API break every 8.5 months on average: v0.8 (Apr 2024) retired the legacy `ufl.FiniteElement` constructor, v0.9 (Oct 2024) moved `Function.vector` to `Function.x.petsc_vec`, v0.10 (Oct 2025) renamed `dolfinx.io.gmshio` to `dolfinx.io.gmsh`, v0.11 (Jun 2026) |
| Firedrake 2026.4 | Excellent solver composition, and EchemFEM already runs on it. No Windows support, no binary wheels, PETSc built from source |
| scikit-fem 12 | BSD-3, 0.2 MB wheel, trivially bundleable, but Newton, block assembly, preconditioning and stabilisation are hand-rolled and MPI is token |
| SfePy 2026.2 | BSD-3 and covers coupled multi-field, but PyPI ships sdist only, parallel support is self-described work-in-progress, and it is effectively single-maintainer |
| PyMFEM, deal.II | No symbolic language, no automatic differentiation; Jacobian integrators for a five-field system must be hand-coded |

Grounds: self-contained wheels (15 MB Windows, 44 MB macOS universal2) for Python 3.10–3.14 on all
three operating systems, no compiler at runtime; Netgen built in, so the default path never links
GPL Gmsh; product spaces `X = V*Q` giving the five-field monolithic system and Taylor–Hood
directly; symbolic differentiation giving `Newton(a, gfu, dampfactor=...)`; axisymmetric assembly
as `... * x * dx`; embeddable webgui (three.js); a decade of API stability. DOLFINx and Firedrake would each need a second
backend for the desktop path, so the weak forms would be maintained twice indefinitely.

| Consequence | Detail and mitigation |
|---|---|
| MPI | Pip wheels are serial-only (verified: no MPI symbols in any shipped `.so`, no mpi4py); parallel mesh generation, adaptive refinement and multigrid are unsupported. This costs v1 nothing: 2D axisymmetric solves are direct-solver territory and sweeps parallelise at the job level |
| No MUMPS in the wheel | The wheel reports `USE_MUMPS: False` (also `USE_HYPRE`, `USE_PARDISO`, `USE_MKL`), and `inverse="mumps"` raises `SparseMatrix::InverseMatrix: no inverse available for type mumps`. MUMPS needs a source build with MPI, reintroducing the compiler dependency this decision exists to avoid. The desktop path uses UMFPACK or scipy SuperLU (CON-08); the reference COMSOL model used PARDISO, equally absent from the wheel |
| Direct-solver performance | Whether UMFPACK factorises the coupled five-field system at production mesh size in acceptable time and memory is a Phase 0 exit criterion (§8.2, QR-07) |
| 3D phase | Mitigations in order: prototype 3D scaling before committing; route parallel solves through ngsPETSc to reach PETSc fieldsplit and AMG; if 3D scaling proves fatal, add a DOLFINx backend for HPC only behind the existing abstraction, taking EchemFEM (LLNL, MIT, Firedrake) as the reference implementation of SUPG-stabilised Nernst–Planck |

#### ADR-002 Meshing backend and the Gmsh licence

Decision: mesher adapters, Netgen (LGPL-2.1) as default and Gmsh (GPLv2+) as optional backend, with
the geometric boundary-layer construction of §5.2.2 so the default path does not depend on Netgen's
less-mature 2D boundary-layer generator.

| Alternative | Assessment |
|---|---|
| Gmsh as default | Best boundary-layer tooling for this problem, but the `gmsh` PyPI wheel is GPLv2+ and use through its Python API is linking, which would make the core library GPL |
| Netgen only, no adapter | Forgoes the Gmsh size-field algebra for users who accept GPL, at no gain |
| MeshPy, TetGen 1.5, pygmsh, pygalmesh | Excluded by CON-12: Triangle's distribution restriction, AGPLv3, and staleness respectively |

Consequences: the core library stays permissively licensable and functional without Gmsh (CON-10);
the contents of the distributed desktop bundle remain a later decision.

#### ADR-003 Project licence

Decision: BSD-3-Clause core library with GPL-compatible optional extras. No institutional
constraint applies.

| Alternative | Assessment |
|---|---|
| GPL core, Gmsh in the default path | Deferred, not foreclosed: the package has no other GPL entanglement, so this stays a one-line relicense should GPL become acceptable |
| PyQt for the desktop shell | Rejected: GPL-3 or commercial only. PySide6 (LGPL-3) is used instead (CON-09) |
| Bundle defaulting to scipy SuperLU | Rejected on measurement (§6.6): SuperLU was OOM-killed on the reference-sized factorisation, so a SuperLU-default bundle cannot run the published case. The bundle defaults to UMFPACK and carries the GPL-2+ obligations that follow, stated in its licence notice; the library itself stays BSD-3 and depends on neither (CON-11, amended 2 September 2026) |

Consequences: BSD-3 maximises adoption where both academic and industrial reuse matter and matches
the scientific Python stack. Dependencies are compatible: NGSolve and Netgen LGPL-2.1 (dynamic
linking), MDAnalysis LGPLv3, PDB2PQR BSD, APBS BSD-3, scikit-image BSD-3, Shapely BSD-3, meshio
MIT, PySide6 LGPL-3. Gmsh is GPLv2+, hence optional. The repository carries a `CITATION.cff`
pointing at the Nanoscale paper and the software DOI (CON-14).

#### ADR-004 Desktop application

Decision: Python core, PySide6 (LGPL-3) shell, NGSolve webgui in a `QWebEngineView` for field
rendering, and a background solver process communicating over a queue so the interface stays
responsive and can show live convergence. Packaged with briefcase or conda-constructor. The
graphical surface grows from Phase 1 onward.

| Alternative | Assessment |
|---|---|
| PyQt6 shell | Rejected: GPL-3 only |
| Local web application: FastAPI plus browser frontend wrapped in `pywebview` | On the table. Identical core, different shell; it would serve a future hosted version and works over an SSH port-forward to HPC, at the cost of feeling less native. The choice may wait until Phase 1 provided the stage interface stays clean |
| Defer the interface to a terminal phase | Rejected on two failure modes: an interface bolted on at the end exposes the API's accidental structure rather than the user's workflow, and a nine-month gap before any non-programmer touches the tool is a nine-month gap in shaping feedback |

Consequences: every pipeline stage must be independently invocable, cancellable, progress-reporting
and introspectable (FR-27), which §5.1 requires on scientific grounds in any case, so the interface
is a thin shell over the stage objects the CLI drives (IF-09). Each release from v0.5 onward ships
a usable graphical surface over the functionality existing at that release (QR-11); the per-phase
increments are in §8.1.

#### ADR-005 Two levels of pluggability

Decision: correction models as data files (level 1) and physics models as classes (level 2), per
§5.5, so that a user comfortable with a little coding can modify or add implementations
transparently and Poisson–Boltzmann is available alongside PNP-NS.

| Alternative | Assessment |
|---|---|
| One extension point, data files only | Insufficient: `pb` and `pb-linear` have a different field set and solve strategy, which no coefficient file expresses |
| One extension point, code only | Makes a new electrolyte a patch to the source tree and loses per-result recording of the parameter version |
| A general symbolic PDE framework | Rejected as N1; the validation surface would be unbounded |

Consequences: a new electrolyte or surface is a data file rather than a code change (FR-16); every
result records which correction version produced it (FR-25); PNP-NS is a configuration of ePNP-NS
rather than separate code (FR-18, PHY-21); Poisson–Boltzmann is a distinct model rather than the
PNP solver at zero bias (PHY-24); correction-by-correction differential testing is a sweep (§7.4).
## 6. Numerical methods specification

This section fixes the discretisation and the solution algorithm for the model of §4. Requirements
carry `NUM-nn` identifiers and use the keywords of §1.5; verification activities that exercise them
are in §7. Settings of the reference implementation (§2.2) that differ from what is required here
are recorded, so that the cross-implementation comparison of §7.4 can account for them.

### 6.1 Discretisation

**NUM-01.** The discretisation SHALL be continuous Galerkin on triangles in the (r, z) half-plane,
with the element degrees below, and every volume and surface measure SHALL carry the `r` weight
of §6.2.

| Field | Element | Domain | Reference implementation |
|---|---|---|---|
| `φ` | P2 | `Ω` | Lagrange, quadratic |
| `c_i` | P2 | `Ω_w` | Lagrange, quadratic |
| `u` | P2, vector-valued | `Ω_w` | Lagrange, linear |
| `p` | P1 | `Ω_w` | Lagrange, linear |

Rationale: the Taylor–Hood P2/P1 pair is inf-sup stable, so the flow block needs no pressure
stabilisation of its own.

**NUM-02.** The Nernst–Planck equations SHALL be discretised in primitive concentrations `c_i` by
default. A log-variable branch `c_i = exp(w_i)` SHALL be provided behind a flag. Slotboom variables
SHALL NOT be used.

| Form | Positivity | Conditioning at ±200 mV | Status |
|---|---|---|---|
| Primitive `c_i` | not guaranteed | good | default |
| Slotboom `c_i = c₀ e^(−z_i φ̃) ρ_i` | yes | coefficient spread `e^(2φ̃)` ≈ 5.8 × 10⁶ | rejected |
| Log / entropy `c_i = e^(w_i)` | exact | moderate, requires damping | fallback branch |
| Mixed / HDG | yes | locally conservative | deferred to post-v1 |

Rationale: `φ̃ = φF/RT` spans ±7.78 over the ±200 mV envelope, so the Slotboom exponential weights
span six decades within one solve. The log form (Metti, Xu & Liu, *J. Comput. Phys.* **306**, 1,
2016) gives provable positivity and a discrete energy law, at the cost of a harder nonlinear
problem.

**NUM-03.** The velocity–pressure element pair SHALL be configurable. Equal-order P1/P1 SHALL be
selectable only together with the flow stabilisation of §6.4.2. The element degree of every field
SHALL be recorded in the run provenance record.

The reference used P1+P1 for velocity and pressure and quadratic elements for potential and
concentrations (NUM-01, last column). That flow pair is a known source of cross-implementation
discrepancy: a stabilised P1+P1 solve and a Taylor–Hood solve are different discretisations of the
same PDE, so only the converged velocity field is comparable, not the operator.

### 6.2 Axisymmetric weak forms

**NUM-04.** The weak forms SHALL be those below, with `∇ = (∂_r, ∂_z)` and the `r` weight on every
integral. The `2π` factor cancels and SHALL be dropped consistently from both sides.

Poisson, over all of `Ω` including protein and membrane, test function `v`:

```
∫ ε ∇φ·∇v  r dr dz  =  ∫ ( ρ_pore + F Σ_i z_i c_i ) v  r dr dz  +  ∫_Γ σ_s v  r ds
```

Nernst–Planck, per species on `Ω_w`, test function `w`, with `J_i` as defined in PHY-04:

```
∫ J_i·∇w  r dr dz  =  0
J_i = −[ D_i ∇c_i  +  z_i μ_i c_i ∇φ  +  D_i β_i c_i  −  u c_i ]
```

Navier–Stokes / Stokes on `Ω_w`, test functions `(v, q)`:

```
∫ [ 2η ε̂(u):ε̂(v) + 2η u_r v_r / r²  −  p d̂iv v  −  q d̂iv u ]  r dr dz  =  ∫ f·v  r dr dz
d̂iv u = ∂_r u_r + u_r/r + ∂_z u_z
```

**NUM-05.** The cylindrical hoop-strain term `2η u_r v_r / r²` SHALL be assembled. After
multiplication by the `r` weight it appears as `2η u_r v_r / r`, which is integrable because
`u_r → 0` on the axis.

Rationale: the term is the weak-form counterpart of the strong-form `−u_r/r²` contribution the
reference carries inside its axisymmetric interface. Omitting it produces plausible but incorrect
flow fields with no solver diagnostic.

**NUM-06.** At `r = 0` the only essential condition SHALL be `u_r = 0`. The conditions
`∂_r φ = ∂_r c_i = ∂_r u_z = 0` SHALL be left natural. Dirichlet conditions on `φ` or `c_i` at the
axis SHALL NOT be imposed.

Rationale: the `r` weight annihilates the axis boundary term. The analysis is set in the weighted
space `H¹_1(Ω)` (Mercier & Raugel 1982; Bernardi, Dauge & Maday) with standard convergence rates.

**NUM-07.** Every form containing a `1/r` factor SHALL be assembled at integration order ≥ 3, and
the implementation SHALL assert this at assembly time rather than rely on defaults.

Rationale: Gauss rules on triangles do sample `r = 0`. The NGSolve order-2 triangle rule places its
three points at the edge midpoints (0, ½), (½, 0), (½, ½), so an element with an edge on the axis is
sampled exactly at `r = 0`: on NGSolve 6.2.2606 `Integrate(gf*gf/(x*x)*x, mesh, order=2)` returns
NaN, while orders 3 and 4 return the correct value. Any term left at order 2 (a P1 pressure block, a
coarse continuation mesh, an unset `bonus_intorder`) silently yields NaN in the hoop-strain term.

**NUM-08.** A unit test SHALL integrate a known `1/r`-weighted quantity on an axis-touching mesh
and SHALL fail on NaN or on deviation from the analytic value.

NOTE: the reference assembled its flow momentum, continuity, stabilisation and density-continuity
terms at integration order 2. NUM-07 governs here irrespective of that setting.

### 6.3 Scaling

**NUM-09.** The equations SHALL be solved in the nondimensional variables below.

| Scale | Definition | Value or range |
|---|---|---|
| Length | `L₀ = a`, the pore radius | ≈ 2 nm |
| Potential | `φ̃ = φ/V_T`, `V_T = RT/F` | 25.693 mV at 298.15 K |
| Concentration | `c̃ = c/c₀` | — |
| Diffusivity | `D₀` | 1.334 × 10⁻⁹ m² s⁻¹ |
| Velocity | `u₀ = ε V_T²/(η a)` | — |
| Pressure | `p₀ = ε V_T²/a²` | — |
| Debye parameter | `λ̃ = λ_D/a`, `λ_D² = ε RT/(2 F² c₀)` | `λ̃ ∈ [0.088, 0.679]` at a = 2 nm |
| Péclet number | `Pe = ε V_T²/(η D₀)` | 0.386 at 298.15 K, η = 0.890 mPa·s |

NOTE: the commonly quoted `Pe` = 0.34 corresponds to η = 1.00 mPa·s, that is ≈ 20 °C; the
temperature SHALL be consistent across all material properties. At either value, convective
transport of ions is not dominant.

Debye lengths for a 1:1 electrolyte at 25 °C, which set the near-wall mesh requirement of §6.8:

| Salt concentration | `λ_D` |
|---|---|
| 0.05 M | 1.357 nm |
| 1 M | 0.304 nm |
| 3 M | 0.175 nm |

**NUM-10.** Field-wise row scaling (`-ksp_diagonal_scale` or equivalent) SHALL be applied after
nondimensionalisation so that all diagonal Jacobian blocks have O(1) norm.

### 6.4 Stabilisation

#### 6.4.1 Production policy

Electromigration is the advective operator in the Nernst–Planck equation, with velocity
`b_i = z_i D_i ∇φ̃ / L₀` and cell Péclet number `Pe_h = ½ |z_i| |∇φ̃| h̃`. Inside the double layer
`|∇φ̃| ≈ |ζ̃|/λ̃_D`, so resolving it with five elements (`h̃ = λ̃_D/5`, NUM-30) gives
`Pe_h = |z_i| |ζ̃| / 10`, below 1 for a monovalent electrolyte whenever |ζ| ≲ 257 mV.

`Pe_h < 1` is a heuristic sufficient condition derived for one-dimensional linear
constant-coefficient advection–diffusion on a uniform mesh. It is stated here as a mesh design rule,
not as a proof for this nonlinear, coupled, `r`-weighted system. Chaudhry, Comer, Aksimentiev &
Olson (*Commun. Comput. Phys.* **15**, 93, 2014) report spurious negative concentrations near
charged nanopore walls with plain Galerkin on under-resolved meshes, removed by SUPG with
`σ_± = (h_τ / 2‖b_±‖)·ψ(Pe_τ)`, `ψ(q) = min(q, 1)`.

**NUM-11.** The production solve SHALL run without stabilisation. SUPG SHALL be available behind a
flag for coarse continuation meshes and default to off for the final solve.

Rationale: SUPG biases the current quantity of interest and destroys Jacobian symmetry.

**NUM-12.** The solver SHALL evaluate `Pe_h` on the assembled mesh and SHALL emit a warning naming
the element location when `Pe_h ≥ 1` anywhere in `Ω_w`.

**NUM-13.** The stabilisation mode in force SHALL be recorded in the run provenance record.

#### 6.4.2 Optional reference-matching stabilised mode

The published currents were computed with consistent stabilisation active in both the transport and
the flow interfaces. An unstabilised solve is therefore a different discretisation of the same PDE,
and per-cent-level disagreement is an implementation difference rather than a defect.

**NUM-14.** An optional stabilised mode reproducing the reference settings below SHALL be provided,
and SHALL be used for like-for-like comparison against published currents (§7.4).

| Setting | Transport of Diluted Species | Flow |
|---|---|---|
| Streamline diffusion | on | on |
| Crosswind diffusion | on | on |
| Crosswind diffusion type | Do Carmo and Galeão | not recorded in the report |
| Equation residual | Approximate residual | not recorded in the report |
| Isotropic diffusion | off | off |
| Convective term | conservative form | not applicable |

**NUM-15.** In the mode of NUM-14 the crosswind term SHALL be assembled at integration order 6 and
the streamline term at integration order 4.

NOTE: the reference gated pseudo-time stepping off (`spf.usePseudoTimeStepping = 0`). Its
equal-order P1+P1 flow elements are LBB-unstable without this stabilisation (NUM-03).

### 6.5 Nonlinear solution and continuation

**NUM-16.** The primary nonlinear strategy SHALL be monolithic damped Newton on the fully coupled
system with a direct linear solve (§6.6), damping adapted on residual reduction and bounded below.
If the minimally damped step still fails to reduce the residual, that step SHALL be accepted rather
than the solve aborted. The reference settings SHALL be the starting point for the defaults:

| Setting | Value |
|---|---|
| Coupling | fully coupled, no segregation groups |
| Initial damping factor | 0.2 |
| Minimum damping factor | 1.0 × 10⁻² |
| Recovery damping factor | 0.2 |
| Maximum iterations | 100 |
| Relative tolerance | 1 × 10⁻⁶ |

NOTE on the relative tolerance. A criterion measured on the residual alone, relative to the
residual on entry, makes a warm start onto an already-converged state demand a further six orders of
magnitude from a residual already at its floor — which is the operation every rung of the ladder in
NUM-18 performs. The implementation therefore converges on **either** the residual test **or** a
relative-update test `‖δu‖ / max(‖u‖, 1) ≤ rtol` evaluated on the *undamped* Newton direction, the
latter being the criterion the reference itself used. A step that failed to reduce the residual
never counts as convergence.

**NUM-17.** The following SHALL be asserted at every Newton step, and a violation SHALL abort the
solve with a diagnostic naming the field and the spatial location:

| Assertion | Condition |
|---|---|
| Concentration positivity | `min_i c_i > 0` |
| Packing fraction | `Φ = Σ_j N_A a_j³ c_j < 1` |
| Potential increment cap | `‖δφ‖_∞ ≤ V_T` |

Rationale: `β_i` is singular at `Φ = 1`. A silently negative concentration produces a plausible but
wrong current.

**NUM-18.** The solve SHALL proceed along the continuation ladder below, each rung warm-started
from the converged state of the previous one.

1. Linear Poisson–Boltzmann.
2. Nonlinear Poisson–Boltzmann.
3. Equilibrium PNP at `V_bias` = 0, `u` = 0.
4. Ramp `σ_s` and `ρ_pore` from 0 to target.
5. Ramp `V_bias` from 0 to ±200 mV, in steps of ≈ 10 mV near onset.
6. Enable the Stokes / Navier–Stokes coupling.
7. Enable the `⟨c⟩`- and `d`-dependent `D`, `μ`, `ε`, `ϱ` corrections.
8. Enable the steric flux `β_i`.
9. Sweep salt concentration from 0.05 M to 3 M.

Rationale: enabling the corrections last isolates their contribution to any convergence failure.

NOTE: the ladder above is a fixed path, not a configuration. Flow is enabled at rung 6 and the
corrections at rung 7, so a run with `physics.flow` off, `variable_density` off, `inertia` off, or
the PHY-23 dielectric-gradient forces on is not a rung of this ladder but a different run. An
implementation SHALL NOT read those four switches from the case when `numerics.continuation` selects
the ladder, and SHALL refuse such a case rather than solve it: the FR-25 manifest would otherwise
record a deviation the solve never carried, which §5.3.3 exists to make impossible. The same applies
to `physics.model: pnp`, whose flow-free transport no rung above 6 carries. Single-rung runs
(`numerics.continuation: none`) take all four switches as given; that is how an ablation asks for a
configuration the ladder cannot express.

**NUM-19.** The mesh SHALL be adapted between continuation rungs only, never within a rung.

**NUM-20.** The fallbacks below SHOULD be implemented in the order given, after NUM-16 is in
place.

| Fallback | Specification | Source |
|---|---|---|
| Pseudo-transient continuation | Add `M/Δt` to the Poisson and Nernst–Planck diagonal blocks and grow `Δt` by SER | Kelley & Keyes, *SIAM J. Numer. Anal.* **35**, 508 (1998) |
| Hybrid segregated | Newton on the PNP block, fixed point for Stokes, with a corrected Poisson step adding the linearised screening term `χ_F (2q²c₀/kT) φ^(k+1)` to the LHS, evaluated at `φ^k` on the RHS | Mitscha-Baude et al., *J. Comput. Phys.* **338**, 452 (2017); semiconductor Gummel map |
| Poisson–Boltzmann initial guess | Initialise from the PB solution rather than `φ = 0`, `u = 0`, `c_i = c₀`, to cure the high-surface-charge failure mode | Mitscha-Baude et al. (2017) |
| Damped Newton with ℓ₂ backtracking | Backtracking line search under the NUM-17 increment cap | Bank & Rose, *Numer. Math.* **37**, 279 (1981) |

NOTE: because the ePNP-NS model violates the Einstein relation (§4.3), the PB solution is an
approximate initialiser and not the exact zero-bias limit.

### 6.6 Linear solution

**NUM-21.** The linear systems of the 2D axisymmetric problem SHALL be solved by a sparse direct
method by default, per the configuration table below. `sparsecholesky` SHALL NOT be used.

| Path | Solver | Settings and constraints |
|---|---|---|
| Desktop, pip wheel (default) | `umfpack`, or scipy `superlu` as a BSD-licensed fallback | `sparsecholesky` is SPD-only and cannot factorise this unsymmetric coupled system; SuiteSparse UMFPACK is GPL-2+, which bears on the redistributable bundle (ADR-003) |
| HPC, source build | MUMPS via ngsPETSc / PETSc | `icntl_14 = 40` because the block system is badly scaled; BLR via `icntl_35` when memory-constrained; also unlocks `PCFIELDSPLIT` for the 3D phase |

Rationale: in 2D, nested-dissection fill is O(N log N) and factorisation O(N^1.5); direct methods
become impractical in 3D at 10⁵ to 10⁶ DOF. The NGSolve pip wheel reports `USE_MUMPS: False`
(likewise `USE_HYPRE`, `USE_PARDISO`, `USE_MKL`) and `inverse="mumps"` raises
`SparseMatrix::InverseMatrix: no inverse available for type mumps`, so MUMPS requires a source
build with MPI.

NOTE: measured on the development laptop (WSL2, 24 cores, 15 GB) on the five-field system of
NUM-01 over the analytic cylindrical pore, one configuration per process. This discharges §8.2
criterion 3 and closes the measurement RSK-10 asked for.

| Cells | DOF | Nonzeros | UMFPACK | Peak RSS | scipy SuperLU | Peak RSS |
|---|---|---|---|---|---|---|
| 1.50 × 10⁴ | 1.43 × 10⁵ | 8.4 × 10⁶ | 4.4 s | 855 MB | 24.0 s | 2593 MB |
| 3.84 × 10⁴ | 3.68 × 10⁵ | 2.2 × 10⁷ | 14.0 s | 2157 MB | 140.3 s | 8656 MB |
| 1.09 × 10⁵ | 1.04 × 10⁶ | 6.2 × 10⁷ | 41.1 s | 6171 MB | OOM-killed | > 15.4 GB |

UMFPACK meets criterion 3 with margin, at 41 s and 6.2 GB for the reference mesh size. scipy
SuperLU costs about 3.4 × the memory and 6–10 × the time, both gaps widening with problem size, and
**did not complete the reference-sized factorisation at all**, being killed by the kernel at
15.4 GB on two separate runs.

> **This conflicted with CON-11**, which said the bundled build SHOULD default to scipy SuperLU with
> UMFPACK opt-in. On this evidence that default would ship a bundle unable to run the reference
> problem. **Resolved 2 September 2026** in favour of the measurement: the bundle defaults to
> UMFPACK and accepts the GPL-2+ obligation, the alternatives — restricting the bundled build to
> smaller meshes, or bringing NUM-22's iterative fallback forward as the BSD-licensed path — being
> rejected as shipping less capability than the reference implementation. CON-11 and ADR-003 carry
> the amended wording; the core library remains BSD-3 and depends on neither solver, UMFPACK being
> built into the NGSolve wheel.

NOTE: the reference used PARDISO with pivoting perturbation 1 × 10⁻¹³ and sparsity-pattern reuse.
PARDISO is likewise absent from the NGSolve wheel, so the reference linear solver cannot be
reproduced on the default path. The converged solution does not depend on this choice; timings do.

**NUM-22.** An iterative fallback SHALL be implemented before any 3D capability: multiplicative
`PCFIELDSPLIT` over the blocks `{(φ, c_i), (u, p)}`, algebraic multigrid per scalar block, and a
Stokes Schur complement approximated by `selfp` or the pressure mass matrix `S ≈ −μ⁻¹ M_p`.

Rationale: the multiplicative split reflects the weak PNP-to-NS coupling direction.

### 6.7 Quantity-of-interest extraction

**NUM-23.** The ionic current SHALL NOT be computed by integrating the continuous-Galerkin flux
over an interior cross-section.

Rationale: CG fluxes are not pointwise conservative, so the current differs between cross-sections
by per-cent-level amounts, which can exceed the rectification signal at low bias.

**NUM-24.** The domain-indicator form SHALL be implemented, `ψ` being a smooth indicator equal to 1
in the cis reservoir and 0 in the trans reservoir:

```
I     = F Σ_i z_i ∫_Ω J_i·∇ψ  r dr dz
Q_EOF =           ∫_Ω u·∇ψ  r dr dz
```

Rationale: it is superconvergent and cross-section independent.

NOTE (sign): with `ψ = 1` on cis, `∫_Ω J_i·∇ψ r dr dz` is by the divergence theorem and
`∇·J_i = 0` the flux of species `i` *out through the cis cap*, so the sign above references the
current to the grounded cis electrode of §5.2.2 and a positive current flows trans → cis, in `+z`.
That is the sign for which an uncharged ohmic pore has `G = I/V_bias > 0` at either sign of the
bias, which is what VER-17 asserts; earlier revisions of this clause carried a minus, which
references the trans electrode instead and negates every conductance. It is also the sign that
makes this route agree with NUM-25 evaluated on `Γ_w,c`, whose reaction flux is the same
`∮ ψ J_i·n` with the same outward normal — so a minus here would have made the NUM-26 agreement
check fail on every solution.

**NUM-25.** The variational reaction flux SHALL also be implemented: the assembled residual
evaluated against a test function equal to 1 on a Dirichlet electrode (Hughes, Engel, Mazzei &
Larson, *J. Comput. Phys.* **163**, 467, 2000).

**NUM-26.** Both routes SHALL be exercised on the same solution in continuous integration and their
agreement asserted against a declared tolerance. **That tolerance is 1 × 10⁻³ relative**, on the
total current, at every operating point of the FR-17 envelope.

Rationale for the number: the tolerance has to sit well below the smallest signal the current is
asked to resolve, which is the rectification signal `|RR − 1|` at the lowest envelope bias of
±50 mV — of order 10⁻¹ for a charged pore. A tenth of a per cent leaves two orders of margin. It is
a ceiling on a bug rather than a numerical budget: `ψ` differs from the NUM-25 boundary indicator by
a function vanishing on both electrodes, hence by a legitimate test function of the converged
residual, so the two routes are the *same* integral and what remains between them is quadrature and
the residual Newton left behind. Measured: 6 × 10⁻⁶ on the VER-11 configuration (0.5 M,
−0.05 C/m², ±50 mV, classical PNP) and 5 × 10⁻⁷ on VER-17's uncharged pore. The remainder does not
fall with the mesh — it is unchanged from 3 400 to 7 300 degrees of freedom — because it is set by
the residual Newton leaves behind and not by the discretisation.

NOTE (a precondition, not a detail): the identity above holds only where `ψ` is *exactly* 1 and 0 on
the two electrodes. Interpolated over the whole mesh it is not — the membrane spans the transition
band, and an element straddling the band shares its corner vertex with a reservoir cap, smearing
about 8 × 10⁻³ of `ψ` onto an electrode where it must vanish. `ψ` SHALL therefore be built on the
fluid domain alone. Over the whole mesh the measured route agreement on the VER-11 configuration
degrades by a factor of 170, from 4 × 10⁻⁶ to 6 × 10⁻⁴, which would pass this tolerance while being
a real error.

NOTE: the reference computed `F*(z_cpos*tds.ntflux_cpos + z_cneg*tds.ntflux_cneg)` at integration
order 4, `ntflux` being the variational reaction flux from the assembled weak residual, so the
published currents are unaffected by NUM-23.

**NUM-27.** The derived quantities below SHALL be computed from the same `ψ` integrals as NUM-24.

| Quantity | Definition |
|---|---|
| Transport number | `t₊ = I₊ / (I₊ + I₋)` |
| Rectification ratio | `RR = |I(+V)| / |I(−V)|` |
| Conductance | `G = I / V_bias` |
| Electro-osmotic flow rate | `Q_EOF` as defined in NUM-24 |

NOTE: any pore-averaged quantity reported as a regression target SHALL state whether the `2πr`
Jacobian is included, because the source work's pore averages appear to omit it while being
described as volume averages.

NOTE (this implementation's convention): the axisymmetric weak forms of §6.2 carry the `r` weight
only, the `2π` having cancelled from both sides, so every integral in the solver — including both
current routes above — is `∫ f r dr dz`. The `2π` is restored **once**, in the quantity-of-interest
extraction, so every SI quantity reported (`I`, `Q_EOF`, and everything derived from them) is a true
three-dimensional quantity and includes the full Jacobian. Because both routes inherit the same
convention, their NUM-26 agreement is independent of it while their SI values are not.

**NUM-28.** The force on an embedded analyte SHALL be evaluated in domain form,

```
F_z = −∫_Ω ( T_M + T_H ) : ∇w  dV
T_M = ε ( E⊗E − ½|E|² I )        T_H = −p I + η ( ∇u + ∇uᵀ )
```

with `w` a smooth extension of `e_z` from the body, rather than as the surface integral
`F = ∮_S (T_M + T_H)·n dS`, for the superconvergence reason of NUM-24.

NOTE: the form as printed is exact only where `∇·(T_M + T_H) = 0` in the fluid. The divergence
theorem gives, in full,

```
F_z = ∮_∂B (T·n_B)·e_z dS = −∫_Ω T : ∇w dV − ∫_Ω (∇·T)·w dV
```

and in this model neither tensor is divergence-free: `∇·T_M = ρ_ion E − ½|E|²∇ε` and, from PHY-07
and PHY-08, `∇·T_H = −f + Re ϱ(u·∇)u` with `f` the body force the momentum equation actually
carries. Each contribution SHALL therefore carry its own consistency term,

```
F^em = −∫ T_M : ∇w − ∫ f_ion·w − ∫ f_KH·w
F^hd = −∫ T_H : ∇w + ∫ f·w − Re ∫ ϱ (u·∇)u·w
```

with `f_ion = ρ_ion E` (PHY-08) and `f_KH = −½|E|²∇ε` the Korteweg–Helmholtz force. Written this
way each contribution equals the traction of its own tensor over the body's surface, so the domain
and surface routes agree contribution by contribution. Omitting the consistency terms leaves the
*split* a function of where the transition shell of `w` was placed — `∫ f_ion·w` is the electrical
force on all the fluid inside that shell, a quantity of the same order as the contributions
themselves — while leaving the total almost unaffected, which is exactly the plausible wrong answer
RSK-04 describes.

NOTE: the two consistency terms cancel in the sum only when the momentum equation carries every
force the Maxwell tensor implies, that is when `f = f_ion + f_KH`. The validated model omits `f_KH`
(PHY-23), so wherever the permittivity correction is active the printed form above differs from the
force by exactly `−∫ f_KH·w`. That term SHALL be reported alongside the force rather than absorbed
into it, so that the omission is a recorded measurement and not an unexplained route discrepancy.
It vanishes identically in a classical configuration and whenever the dielectric-gradient body force
is enabled, which is why VER-22 gates classically.

NOTE: the contraction carries no `1/r` factor. For an axial `w`, `(∇w)_φφ = w_r/r = 0`, so the hoop
components of both tensors are contracted against zero and `T : ∇w = T_rz ∂_r w_z + T_zz ∂_z w_z`.
The integrals still carry the `r` weight and the NUM-07 integration-order floor, but they are not
singular forms.

NOTE: `w` SHALL be built by interpolation on the fluid alone, for the reasons NUM-24 gives for `ψ`,
and SHALL be verified to equal `e_z` on the body and zero on every other boundary before it is used;
an inverted or leaking extension returns the force on a different body with no other symptom
(QR-12).

**NUM-29.** The electromechanical and hydrodynamic contributions SHALL each be resolved to well
below 1 pN, the domain-form and surface-integral evaluations SHALL agree to better than 0.1 pN, and
the force feature SHALL carry its own mesh convergence study.

Rationale: at `V_bias` = +50 mV, `q_Hb` = −4 e and 300 mM NaCl the reference analyte case has
`|F^em| ≈ |F^hd| ≈ 10 pN` of opposite sign, so the net force is a near-cancellation of two
approximately 10 pN terms; an error in either integral flips the sign of the total and with it the
trapping landscape (RSK-04).

NOTE: agreement of the two routes on the *total* does not establish the split, and the split is what
RSK-04 concerns. An implementation MAY take a third route for `F^hd` alone — the analyte surface is
a Dirichlet boundary for `u`, so the assembled momentum residual paired with a test function equal
to `e_z` there is the traction integral itself, by the NUM-25 argument. It is independent of `w`
exactly, so it disagrees with the domain form precisely when a NUM-28 consistency term is missing or
mis-signed, which no comparison of the two stress routes can detect.

### 6.8 Mesh resolution and adaptivity

**NUM-30.** The mesh SHALL resolve the double layer to the following targets.

| Parameter | Value |
|---|---|
| First wall layer `h₁` | `λ_D/5`; 0.035 nm at 3 M, 0.27 nm at 0.05 M |
| Geometric growth ratio | 1.15 to 1.2 over ≈ 15 layers |
| Far-reservoir element size | 5 to 10 nm |
| Expected element count | 5 × 10⁴ to 2 × 10⁵ |

NOTE: the reference reached the published results with graded free triangular meshing and no
boundary-layer node, at 120,917 triangles with minimum element quality 0.6378 and average 0.9765.

**NUM-31.** The wall-distance field `d` SHALL be computed once per mesh (eikonal solve or
screened-Poisson smoothing) and mollified to C¹ continuity, as required by PHY-02.

Rationale: `D`, `μ` and `η` depend on `d`, so a kinked distance field enters the Jacobian and
degrades Newton convergence.

**NUM-32.** Goal-oriented dual-weighted-residual adaptivity targeting the ionic current (Becker &
Rannacher, *Acta Numerica* **10**, 1, 2001) MAY be provided as an optional refinement loop. It
SHALL NOT be a v1 default.

**NUM-33.** Where the loop of NUM-32 is provided, the error estimator SHOULD be built from the
linear Poisson–Boltzmann surrogate rather than the full coupled adjoint.

Rationale: the surrogate estimator is justified on heuristic grounds only, but empirically retains
the optimal O(h²) rate in the quantity of interest at a fraction of the cost of the full adjoint.

NOTE: the published results carry no discretisation error bar. The COMSOL model report gives
element counts and mesh quality but no convergence study, so the mesh convergence study of §7 is new
work, and small disagreements with published numbers may originate in the reference's own
discretisation error.
## 7. Verification and validation plan

Verification activities carry `VER-nn` identifiers and establish that the software solves the
specified equations correctly. Validation activities carry `VAL-nn` identifiers and establish that
those equations describe the physical system. The structure follows IEEE 1012.

### 7.1 Strategy and ordering

| Tier | Content | Runtime | Frequency | Role |
|---|---|---|---|---|
| 1 | Unit and property tests (§7.2) | seconds | every push | Acceptance gate for Phases 0 and 1 |
| 2 | Analytic benchmarks (§7.3) | minutes | every push | Acceptance gate for Phases 0 and 1 |
| 3 | Cross-implementation comparison (§7.4) | hours | nightly and on demand, once Tier 2 passes | Recorded, not gated, until §7.4 preconditions hold |
| 4 | Experimental reproduction (§7.5) | hours | before a tagged release | Release gate |

Tiers 1 and 2 are the acceptance gate for Phases 0 and 1. Tier 3 runs only after Tier 2 passes.
Tier 4 gates releases.

Rationale: an analytic test localises an error to a single term, so a Debye–Hückel failure points
at the axis condition or the r-weighted Poisson form and an MMS failure at the hoop-strain term. A
whole-model comparison localises nothing, so a per-cent-level discrepancy found first offers no
route to a cause and invites adjusting the solver until the number matches.

### 7.2 Tier 1 unit and property tests

| ID | Activity | Acceptance criterion |
|---|---|---|
| **VER-01** | Charge conservation under smearing and azimuthal projection | Assembled charge on the deployed mesh within 1 × 10⁻³ relative to `Q_net` (PHY-19) |
| **VER-02** | Per-z-slice cumulative charge | Cumulative charge below each z plane matches the partial sum over the source charge list, to the VER-01 tolerance |
| **VER-03** | Correction models reproduce their published check values | `f^w_D(0) = 0.0601`, `f^w_D(0.75) = 0.9910`, `η⁰/η^w(0) = 0.3790`, `η⁰/η^w(1.45) = 0.9876`, `η(5.3 M) = 1.752 × 10⁻³ Pa s`, `ϱ(5.3 M) = 1194 kg m⁻³`, `D_Na(5.3 M) = 8.13 × 10⁻¹⁰ m² s⁻¹`, `D_Cl(5.3 M) = 1.071 × 10⁻⁹ m² s⁻¹`, each to four significant figures; clamping above 5.3 M activates and is logged |
| **VER-04** | Nernst–Einstein consistency at infinite dilution | `μ_i⁰ = D_i⁰/V_T` with `V_T = 25.693 mV`: 5.1922 × 10⁻⁸ (Na⁺) and 7.9089 × 10⁻⁸ (Cl⁻) m² V⁻¹ s⁻¹, to four figures |
| **VER-05** | Einstein-ratio drift | `D_i/μ_i` rises to 1.2–1.7 × kT/e between 0.15 M and 3 M and matches the expected profile. A test asserting `D_i/μ_i = kT/e` at finite concentration SHALL NOT be written (PHY-14) |
| **VER-06** | Wall-distance field | Mollified field has continuous gradient across element boundaries to a stated tolerance; `d = 0` on the pore boundary; membrane absent from the distance source set (PHY-02) |
| **VER-07** | Integration order on 1/r forms | Every form carrying a 1/r factor asserts integration order ≥ 3; assembly on an axis-touching mesh returns no NaN and no Inf |
| **VER-08** | Packing fraction and positivity | `Φ = Σ_j N_A a_j³ c_j < 1` and `min_i c_i > 0` at every nonlinear iterate; violation aborts with the offending quantity and its location (PHY-06) |
| **VER-09** | Case-file schema round-trip | A written and re-read case file yields a semantically identical run configuration; an unknown key is rejected with a diagnostic naming the key |
| **VER-10** | Mesh quality gates | On known-bad input the gates fire: min SICN/gamma > 0.3 required, run aborts, diagnostic names the worst element and its location. Reference figures: minimum 0.6378, mean 0.9765 |
| **VER-11** | Current-extraction route agreement | On a stored converged fixture, the ψ-domain-integral and the variational reaction flux agree to a tolerance smaller than the rectification signal at the lowest bias in the envelope |
| **VER-23** | Artefact content addressing | The hash of a fixed artefact is a stated constant, reproduced in a fresh process under a varied `PYTHONHASHSEED`; every leaf change of the parameters or of an input hash moves it; representational differences that validation removes (`1` against `1.0`, `-0.0` against `0.0`, key order) do not; an unhashable payload is refused naming its path; a payload file edited on disk loads as hand-substituted rather than aborting (§5.3.2, FR-27) |
| **VER-24** | Provenance manifest completeness | All eight field groups of §5.3.3 are present, a group no stage contributed carrying a status and a reason rather than being omitted; every switch-typed field of the case schema is classified either as a switch with a validated default or as a configuration choice with a written reason, in both directions, so that a switch added later without a default fails this test; the physics model's own deviation enumeration agrees with the case's on the switches they share; the environment group is populated without importing NGSolve (FR-25, IF-08) |
| **VER-25** | Stage protocol | Every stage registered in §5.2 reports its name, number, inputs, outputs and artefact schema without importing its implementation module, asserted on `sys.modules` in a fresh process; each stage's own description is the registry's, so the two cannot drift; progress is monotone in [0, 1] and ends at 1; a cancellation token raises naming where the stage stopped, and is not a subclass of the numerical gate errors (FR-27, IF-01) |
| **VER-27** | Mesh ingestion and tagging | A tagged mesh written as Gmsh MSH 4.1 and read back preserves vertices, connectivity, per-group physical tags and group names (IF-06); a group left unclaimed by `inputs.mesh.groups`, or a vocabulary name the run selects on that no group supplies, aborts with a diagnostic naming both lists (QR-12); the default ingestion path imports neither `gmsh` nor netgen's Gmsh reader, asserted on `sys.modules` in a fresh process (CON-10) |
| **VER-28** | Reference-geometry conformance | The assembled (r, z) region has exactly three domains — pore body, one membrane, one electrolyte — and is conformal at the membrane-to-pore junction: the membrane meets the pore on the pore's own outer surface, at r = 2.7524 nm on z = −1.4 and r = 4.88 nm on z = +1.4 within the fragmentation tolerance and read from the fixture rather than hard-coded, *and* over one shared edge chain rather than two coincident ones; no membrane material lies inside the fluid set; the region carries exactly the §5.3.1 vocabulary and its mesh meets the §5.2.2 quality figures (FR-09) |

### 7.3 Tier 2 analytic benchmarks

These verify the model against closed-form solutions, establishing that the axisymmetric weak
forms, the axis treatment and the coupling are correct without reference to another code's mesh,
discretisation or stabilisation.

| ID | Benchmark | Reference form | Acceptance criterion |
|---|---|---|---|
| **VER-12** | Gouy–Chapman, 1D | `φ̃(x) = 4 artanh(tanh(ζ̃/4) e^(−x/λ_D))`, Grahame `σ_s = √(8εRTc₀) sinh(ζ̃/2)` | Poisson–Boltzmann equilibrium reproduced to solver tolerance under mesh refinement |
| **VER-13** | Debye–Hückel in a cylinder | `φ(r) = ζ I₀(r/λ_D)/I₀(a/λ_D)` | Axisymmetric Poisson weak form and axis condition (§6.2) reproduced to solver tolerance |
| **VER-14** | Rice & Whitehead (1965) capillary electro-osmosis | thick and thin EDL regimes | Coupled Poisson and Stokes velocity profile reproduced in both regimes |
| **VER-15** | Helmholtz–Smoluchowski limit | `u_slip = −εζE_t/η` as λ_D/a → 0 | Computed slip velocity approaches the limit at the expected asymptotic rate |
| **VER-16** | 1D steady PNP with limiting current | Bazant, Chu & Bayly, *SIAM J. Appl. Math.* **65**, 1463 (2005) | Full PNP current-voltage response including the limiting-current plateau |
| **VER-17** | Maxwell–Hall access conductance | `G = σ[L/(πa²) + 1/(2a)]⁻¹` (radius form) ≡ `σ[4L/(πd²) + 1/d]⁻¹` (diameter form) | Uncharged pore at 1 M reproduced to better than 2 % |
| **VER-18** | Method of manufactured solutions, full coupled axisymmetric system | manufactured `φ, c_i, u, p` with consistent source terms | Observed convergence O(h³) in L² for P2; the only route that verifies the `u_r/r²` term and the axis treatment |
| **VER-19** | Stokes drag on a sphere | `F = −6πηaU` | Drag on the analyte body in creeping flow to better than **1 %** on the finest mesh, falling monotonically under refinement |
| **VER-20** | Maxwell stress on a dielectric sphere in a uniform field | analytic potential for a sphere of permittivity `ε_p` in medium `ε_m`, and `F_z = qE₀` for a uniformly charged body at `ε_p = ε_m` | Field matched to the closed form, net force below **10⁻³ pN** by both routes, and the `qE₀` magnitude anchor to better than **1 %** |
| **VER-21** | Electrophoretic mobility limits | Hückel `μ_e = 2εζ/3η` (κa ≪ 1) and Smoluchowski `μ_e = εζ/η` (κa ≫ 1), with Henry's `μ_e = (2εζ/3η) f(κa)` as the reference between them | Henry's function recovered to better than **5 %** at every κa tested and the Hückel limit to **5 %** at κa ≲ 0.5; `μ_e/(εζ/η)` rising monotonically towards 1 with the residual gap at the largest κa under **15 %** and no larger than Henry's own gap there |
| **VER-26** | Artefact cache and manifest against a real run | the key computed before the stage runs against the artefact it produces | On a converged solve: the two hashes are equal and the key carries no payload; re-running the same case is a store hit that does not re-enter Newton; a changed bias, or a mesh whose *contents* changed, misses, while the same mesh under another path hits; a cancelled run leaves no artefact in the store at either cancellation granularity; the manifest names every input hash the artefact was keyed on, from the same source (§5.3.2, FR-25, FR-26, FR-27, QR-08 in part) |
| **VER-22** | Force-evaluation route agreement | domain form `F_z = −∫_Ω (T_M + T_H) : ∇w dV` against surface form `F = ∮_S (T_M + T_H)·n dS`, with the variational reaction force on the no-slip surface as a third route for the hydrodynamic half | Agreement to better than **0.1 pN absolute** on the same solution, on a solution whose two halves are individually of order 10 pN and opposite in sign; the reaction route confirming `F^hd` to better than **10⁻³ pN** |

NOTE: Hall's result is `R_access = ρ/(4a)` per side, so the two sides give `ρ/(2a)`. The form
`G = σ[L/(πa²) + 1/a]⁻¹` substitutes radius for diameter in the access term and is wrong there by a
factor of two; for `a = 2 nm`, `L = 13 nm` it under-predicts `G` by about 16 %. Used as a target it
would fail a correct solver.

NOTE (VER-19): the far field SHALL be the exact Stokes solution imposed on the outer boundary, not a
uniform stream. A uniform `u = U e_z` at `R = 10a` confines the return flow and raises the drag by
about 28 %, of order `a/R` — the `1 + (9/4)(a/b)` wall correction of a sphere in a concentric
container — so a benchmark posed that way measures the domain truncation and not the discretisation.

NOTE (VER-20): the zero test and the magnitude anchor are both required. `F^em` has no reaction-route
oracle, because `φ` is not constrained on the analyte surface, so the Maxwell route's *scale* rests on
quadrature alone; a net force of zero on a polarised sphere is invariant under a uniform factor and
cannot catch a scale error. The anchor is exact — the self-force of a symmetric charge distribution
vanishes — and in the NUM-09 variables reads `F/(εV_T²) = ρ̃ Ṽ Ẽ₀`, which pins the `2π` of NUM-27, the
`r` weight and `Scales.force_N` together in one number. Neither VER-20 problem needs the NUM-28
consistency term: the fluid is charge-free with a uniform permittivity in both, and the anchor's charge
lies inside the body, where `w` is constant.

NOTE (VER-21): the acceptance is stated against Henry's function rather than against the two limits
alone, because the limits are limits. `μ_e = (2εζ/3η) f(κa)` with `f(0) = 1` and `f(∞) = 3/2` is the
closed form at every κa in the low-ζ limit, and Ohshima's approximation to it,
`f(x) = 1 + 1/(2[1 + 2.5/(x(1 + 2e^{−x}))]³)`, is the reference used. The approach to Smoluchowski goes
as `1/κa` and is slow: at κa = 16.5, the largest a Tier-2 budget affords, Henry is still 11.5 % below
`εζ/η`, so a 5 % gate against Smoluchowski there would be asserting something untrue. The 15 % gate is
the honest one, and the monotone approach carries the rest of the claim. The Hückel end needs no such
allowance: at κa = 0.5, `f = 1.014`.

NOTE (VER-21): the far field for this benchmark SHALL be a uniform stream, reversing VER-19's rule, and
the reversal is not an inconsistency. VER-19 measures one confined solve, where a uniform stream adds
the `a/R` wall correction that NOTE (VER-19) quantifies. VER-21 measures the ratio of two solves, whose
force-free combination has a far field that is uniform to `O((a/R)³)` — a force-free particle radiates
no Stokeslet — so imposing the exact translating-sphere field would inject the `O(a/R)` Stokeslet the
physical solution does not have. The wall corrections common to the field and drag solves divide out of
the ratio. ζ SHALL be measured as the `r`-weighted mean of `φ` over the body surface rather than
prescribed there: a prescribed potential makes the body an equipotential, which expels the applied
field instead of refracting it through the dielectric, and solves a different problem with a different
`f(κa)`.

NOTE (VER-22): the third route is the oracle on the *split*, which is what RSK-04 is about. The analyte
surface is a Dirichlet boundary for `u`, so the assembled momentum residual paired with a velocity-block
test function equal to `e_z` there equals `∮_S (T_H·n)·e_z dS` discretely, and — because the residual
vanishes on every free degree of freedom — it is exactly independent of `w`. It therefore disagrees with
the domain route precisely when the NUM-28 consistency term is missing or mis-signed, which is the
failure mode invisible in the total. The agreement threshold is **absolute**: the total is a small
difference of two large numbers by construction, so a relative test on it measures nothing.

NOTE (VER-26): this is a property test, not an analytic benchmark, and it is in Tier 2 by *runtime*
rather than by kind — it needs a converged solve, and §7.2 is seconds. It is listed here because
§7.1 maps Tier 2 to this section; the tier a test belongs to is decided by which directory it is
placed in, and this one is placed in Tier 2. Its acceptance criteria are equalities and exceptions,
so it carries no tolerance.

### 7.4 Tier 3 cross-implementation comparison

For frozen cases spanning the envelope, solutions are compared field by field against exported
COMSOL reference solutions (`φ`, `c_i`, `u`, `p`) on a common probe grid, together with all scalar
QoIs. Golden files are stored as compressed arrays with the generating model archived alongside.

Tight agreement is not expected at first: the reference uses a different discretisation (linear
velocity and pressure) on a mesh from a different generator, with streamline and crosswind
stabilisation active in both interfaces. Acceptance targets of better than 1 % relative L² error on
fields and 0.5 % on integrated quantities therefore apply only once the matching stabilised mode of
§6.4 exists and the meshes have been convergence-matched. Until both preconditions hold,
differences are recorded and attributed rather than gated on.

| ID | Activity | Acceptance criterion |
|---|---|---|
| **VAL-01** | Field comparison on the common probe grid | < 1 % relative L² error per field, once the preconditions above hold |
| **VAL-02** | Integrated-quantity comparison (`G`, `t₊`, `RR`, EOF rate) | < 0.5 % relative error, once the preconditions above hold |
| **VAL-03** | Reference-solution generation and archival, in Phase 1 | Full reference set for the frozen cases archived with the generating model, independent of continued licence access |
| **VAL-04** | Reference discretisation-error probe | The reference case re-solved at two refinement levels while licence access lasts, bounding the reference's own discretisation error |
| **VAL-05** | Geometry pipeline against the published boundary | Auto-generated contour compared against the delivered reference pore polygon (§5.2.1): radius profile and constriction radius within a stated tolerance |
| **VAL-06** | Poisson-only comparison against APBS | Potential from the assembled fixed-charge and dielectric fields agrees with an APBS solve on the same structure within a stated tolerance |

NOTE: the reference model carries no mesh convergence study, so part of any residual difference may
originate in the reference (RSK-09). The project's own discretisation error is quantified first
(§7.3), and the residual is then attributed.

### 7.5 Tier 4 experimental reproduction

| ID | Activity | Acceptance criterion |
|---|---|---|
| **VAL-07** | Conductance versus salt concentration | Experimental range 0.05–3 M, simulated range 0.005–5 M; agreement with experiment no worse than the source paper's own agreement |
| **VAL-08** | I–V response and rectification `α(V_b)` over ±200 mV | Agreement with experiment no worse than the source paper's own agreement, over the full ±200 mV envelope |
| **VAL-09** | Cation transport number `t_Na⁺` | Agreement with experiment no worse than the source paper's own agreement |
| **VAL-10** | Classical PNP-NS ablation | The uncorrected model reproduces the published over-estimation of current, in the same direction and of the same order |

Rationale (VAL-08): a ±150 mV envelope would drop the highest-|V| quarter, where rectification is
largest and Newton convergence hardest.

Rationale (VAL-10): reproducing the documented failure of the uncorrected model is as diagnostic as
reproducing the success of the corrected one.

### 7.5.1 Analyte force validation targets

The analyte force and PMF capability has a published continuum reference: Huang et al.,
*Angew. Chem. Int. Ed.* **61**, e202206227 (2022), DOI `10.1002/anie.202206227`. That work solved
the full ePNP-NS system in COMSOL 5.5, 2D-axisymmetric, with haemoglobin represented as a body of
revolution of height 6.7 nm and width 5.8 nm carrying a uniform volumetric charge
`rho_part = q_Hb/V`, scanned over −100 ≤ z ≤ 100 nm, and integrated the force to a PMF.

| ID | Activity | Acceptance criterion |
|---|---|---|
| **VAL-11** | Force components against the PlyAB reference | At `V_b` = +50 mV, `q_Hb` = −4 e, 300 mM NaCl: `F^em` and `F^hd` each of magnitude approximately 10 pN and of opposite sign, `F^em` directed towards *trans* and `F^hd` towards *cis* |
| **VAL-12** | PMF minima | Energy minima recovered at z = −2.5 nm and z = +5.25 nm |
| **VAL-13** | Residual current on lumen entry | Simulated residual current falls to approximately 40 % on lumen entry; experimental `I_res` for HbA is 18.5 ± 0.4 % and 40.2 ± 0.7 % |
| **VAL-14** | Electro-osmotic force coefficient, ClyA | `F_eo` = 9 pN at −50 mV, equivalently 0.178 pN/mV, corresponding to `N_eo` = 15.5 ± 0.9 e |

NOTE: `F^em` and `F^hd` nearly cancel, so the accuracy requirement on each integral (NUM-29) is set
by the residual rather than by the magnitude of either term.

NOTE: the ACS Nano 2019 trapping work is not a continuum analyte calculation. It uses equilibrium
Poisson–Boltzmann in APBS on a coarse-grained bead model with a one-dimensional analytic rate
model, and provides no stress-tensor force profile. Detail in
`.knowledge/05-analyte-and-forces.md` §10.

### 7.6 Continuous integration

| Trigger | Tiers run |
|---|---|
| Every push | 1 and 2 |
| Nightly, once enabled | 3 |
| Before a tagged release | 1, 2, 3 and 4 |

Every run SHALL emit a provenance manifest recording input hashes, library versions, mesh hash,
solver settings, stabilisation mode and correction parameter file versions (FR-25).

---

## 8. Implementation plan

### 8.1 Phases and gates

| Phase | Deliverable | Gate | Estimate |
|---|---|---|---|
| 0. Spike | Coupled ePNP-NS on an analytic cylindrical pore; continuation ladder; Tier 1 and Tier 2 suites (§8.2.1) | §8.2 exit criteria, as amended by §8.2.1 | 3–5 weeks |
| 1. Solver core | Production solver on an externally supplied mesh, full QoI extraction, frozen case-file schema, sweep runner | Tier 1 and Tier 2 pass; Tier 3 enabled and differences attributed | 6–10 weeks |
| 2. Geometry pipeline | Structure and trajectory ingestion, density, symmetry reduction, contour, CAD, mesh | VAL-05: the auto-generated mesh reproduces the hand-conditioned reference geometry | 8–12 weeks |
| 3. Charge pipeline | PDB2PQR to smeared volumetric `ρ_fixed` and dielectric field | VER-01, VER-02 and VAL-06 pass | 3–5 weeks |
| 4. Validation and release | Full V&V suite in CI, documentation, JOSS paper, v1.0 | Tier 4 passes (VAL-07 to VAL-10) | 4–6 weeks |
| GUI | Continuous track from Phase 0 onward, one increment per phase | QR-10: an experimentalist runs a case unaided | continuous |

GUI increments, one per phase (ADR-004):

| Phase | GUI increment |
|---|---|
| 0 | Packaging probe: a trivial PySide6 and NGSolve `webgui` application that builds into a double-clickable Windows bundle |
| 1 | Case editor over the frozen schema, run control, live convergence plot, field viewer; meshes supplied externally |
| 2 | Geometry pipeline surfaced: load a structure, inspect the density, contour and mesh steps, override the contour by hand |
| 3 | Charge pipeline surfaced: pH selector, force field, charge map viewer, conservation report |
| 4 | Sweep builder, result browser, figure export, case comparison |
| post-1.0 | Installers for all three platforms, in-application tutorials |

Phase 2 SHALL NOT start before the Phase 0 exit criteria are met.

### 8.2 Phase 0 exit criteria

All four SHALL be met.

1. All Tier 2 analytic benchmarks (VER-12 to VER-22) pass, including MMS convergence at O(h³) in L²
   for P2 on the full coupled axisymmetric system. This is the primary criterion: it establishes
   that the physics and the axisymmetric discretisation are correct, independently of any other
   implementation.
2. Converged solutions across the full 0.05–3 M × ±200 mV envelope with all corrections active,
   obtained from the continuation ladder, with no negative concentrations at any Newton step.
3. UMFPACK or scipy SuperLU factorises a production-sized problem, about 1.2 × 10⁵ cells with five
   fields, in acceptable time and memory on a laptop. The reference mesh size sets the target.
4. A trivial PySide6 and NGSolve `webgui` application builds into a working double-clickable bundle
   on Windows.

COMSOL comparison is not a Phase 0 gate. Tier 3 runs once criterion 1 is met, and early
disagreement at the per-cent level is expected for the reasons in §7.4.

#### 8.2.1 Amendments to Phase 0, agreed 19 August 2026

| # | Amendment | Consequence |
|---|---|---|
| A1 | Criterion 1 stands in full, including VER-19 to VER-22. Those four benchmarks require an embedded body, so Phase 0 SHALL implement a rigid analyte body of revolution and the domain-form force integral of NUM-28 to the extent the benchmarks exercise them | Brings part of FR-21 and FR-22 forward from v1.0 into the spike, and verifies RSK-04 — a near-cancellation of two approximately 10 pN terms — against analytic results at the earliest point at which it can be verified at all. The case-file surface for analytes remains v1.0 work |
| A2 | Criterion 4, the PySide6 and `webgui` Windows bundle, is deferred out of Phase 0 and is recorded as deliberately unmet | RSK-13 (desktop packaging defeated by a binary dependency) stays open and undetected for longer than ADR-004 intends. The GUI track of §8.1 resumes at Phase 1 |
| A3 | The Phase 0 COMSOL comparison is deferred in full to Phase 1, together with the Tier 3 harness, the export contract and reference-set generation (VAL-03) | Phase 0 verifies against analytic solutions only. This tightens rather than weakens the gate, criterion 1 being the criterion that localises an error to a single term; §8.2 already excluded the comparison from the gate |

Phase 0 is therefore met by criteria 1 to 3 as written, with criterion 4 explicitly outstanding.

### 8.3 Effort estimate

Estimate to a validated v1.0 without the desktop GUI: 6–9 months of part-time work. With the
desktop GUI: 9–14 months. Both figures are for one person; the calendar halves at full-time effort.

Factors making the work more tractable:

- The reference implementation is retained as a differential-testing oracle, with reference
  solutions available on demand.
- The v1 target is 2D axisymmetric and steady, so a direct sparse solve stays viable to about
  2–5 × 10⁶ DOF and MPI is off the critical path.
- The parallelism required is many independent serial solves, which is job-array dispatch rather
  than domain decomposition.
- The physics is published, validated and CC-BY-4.0: correction functions, parameters and
  implementation details are in the ESI, the thesis source and the model report.
- The final pore polygon is published and the table is in the repository (§5.2.1), so solver work
  can proceed on it as a fixture.
- The reference mesh used isotropic grading only, with no boundary layers.

Factors making the work less tractable:

- The contour to CAD to mesh handoff: a raw iso-contour of an ensemble-averaged density is a
  many-hundred-vertex polyline with sub-Ångström wiggles and near-tangential self-approaches at the
  constriction.
- Newton convergence with the corrections active, which makes `D`, `μ`, `ε` and `ϱ` functions of
  local ionic strength and wall distance.
- The desktop GUI, the largest single scope item and the strongest constraint on the backend.
- The analyte net force, a near-cancellation of two terms of about 10 pN and opposite sign.
- A single maintainer.

Throughput datum: the reference sweep of 3,675 solves (5 physics cases × 35 bias values × 21 salt
concentrations) took 41 h on 12 cores. A full-envelope sweep is a day-scale job.

---

## 9. Risk register

| ID | Risk | Severity | Likelihood | Mitigation | Detection phase |
|---|---|---|---|---|---|
| **RSK-01** | Newton stagnates once `⟨c⟩`- and `d`-dependent `D`, `μ`, `ε`, `ϱ` are active | High | Low–Med | Corrections enabled last in the continuation ladder; pseudo-transient continuation and hybrid fallbacks; mollified C¹ distance field (VER-06). The reference converged on this system with a fully coupled direct solver and lower-bounded variable damping | Phase 0 |
| **RSK-02** | Under-resolved Debye layer at 3 M (λ_D = 0.18 nm) gives negative concentrations and a silently wrong current | High | Med | Mesh criterion `h ≤ λ_D/5`; `min c_i` monitored per Newton step and failed loudly (VER-08) | Phase 0–1 |
| **RSK-03** | Current QoI wrong from non-conservative CG flux, corrupting the rectification signal | High | Med | Both the ψ-domain-integral and the variational reaction flux mandated, with automatic agreement check (VER-11) | Phase 1 |
| **RSK-04** | Analyte net force is a near-cancellation of two terms of about 10 pN and opposite sign; a small error in either integral flips the sign of the total | High | Med–High | Domain-form force evaluation (§6.7) rather than surface integration; dedicated force convergence study; both routes cross-checked to better than 0.1 pN (VER-22) | Analyte phase |
| **RSK-05** | Contour to mesh produces slivers at the constriction | Low–Med | Low | The published 190-vertex pore polygon is usable as a fixture; the reference mesh used no boundary layers, only isotropic grading to 0.05 nm at the pore wall; contour validity gate (FR-08); isotropic fallback; mesh quality gates abort the run (VER-10) | Phase 2 |
| **RSK-06** | The author's contour script proves tightly coupled to its original context and is not portable | Med | Med | Read it in week 1 of Phase 2, before the rest of the phase is planned; fall back to the specified contour pipeline | Phase 2 |
| **RSK-07** | Axisymmetric reduction invalid for a given pore through large azimuthal variance | Med | Med | Residual azimuthal variance reported as a first-class output (FR-06) and documented as a validity criterion | Phase 2 |
| **RSK-08** | Charge non-conservation through smearing and 1/r projection | Med | Med | Exact annular volumes; analytic annulus integration; assertion on the deployed mesh and per-z-slice check (VER-01, VER-02) | Phase 3 |
| **RSK-09** | The reference model carries no mesh convergence study, so a Tier 3 discrepancy of a few per cent may originate in the reference | Med | Med–High | Quantify this project's discretisation error first (§7.3), then attribute the residual; re-solve the reference case at two refinement levels while licence access lasts (VAL-04); never adjust the solver to close such a gap | Tier 3 |
| **RSK-10** | The NGSolve pip wheel ships without MUMPS, and UMFPACK or SuperLU may not handle production-size coupled factorisations | Med | Med | Two solver configurations (§6.6); measured on day one of Phase 0 (§8.2 criterion 3); iterative fieldsplit through ngsPETSc in reserve | Phase 0 |
| **RSK-11** | NaN from 1/r terms at integration order 2, silent rather than a crash | Med | Med–High | Integration order ≥ 3 asserted on all 1/r forms; dedicated test on an axis-touching mesh (VER-07) | Tier 1 |
| **RSK-12** | Transcription errors in the correction coefficients, the per-ion `D` and `μ` sets being easy to conflate | Med | Med | Coefficient files reviewed against the model report in a second pass; each `f(c)` property-tested against published check values (VER-03) | Tier 1 |
| **RSK-13** | Desktop packaging defeated by a binary dependency | Med | Low–Med | NGSolve wheels chosen for this reason; packaging prototyped in Phase 0 (§8.2 criterion 4), not at the end | Phase 0 |
| **RSK-14** | COMSOL licence access lapses, removing the oracle | Med | Low | Full reference set generated and archived in Phase 1 (VAL-03) | Continuous |
| **RSK-15** | Scope creep from the GUI drawing effort away from validation | Med | High | Each increment stays thin and follows the physics it exposes; no GUI is built for an unvalidated capability | Continuous |
| **RSK-16** | Sole-maintainer bus factor | Med | Med | JOSS paper and DOI; small dependency surface; every stage independently usable | Continuous |
| **RSK-17** | NGSolve MPI weakness blocks a future 3D phase | Med | Med | Not on the v1 path; 3D scaling prototyped before commitment; ngsPETSc and a DOLFINx backend as fallbacks | Post-v1 |
| **RSK-18** | Reference stabilisation settings unknown. Resolved: stabilisation was on. Transport of Diluted Species used streamline and crosswind diffusion, crosswind type "Do Carmo and Galeão", approximate residual and conservative convective form; Laminar Flow used streamline and crosswind with P1+P1 elements | Closed | Closed | Consequence: cross-comparison requires either a matching stabilised mode (§6.4) or a systematic offset acknowledged as such when Tier 3 tolerances are set | Resolved |
| **RSK-19** | Analyte force computation has no prior implementation. Retired. The PlyAB work (*Angew. Chem. Int. Ed.* 2022, DOI 10.1002/anie.202206227) is a full ePNP-NS continuum force computation with published targets and a retained COMSOL model | Closed | Closed | Superseded by RSK-04 | Retired |

---

## 10. Open items

| ID | Item | Owner | Blocks |
|---|---|---|---|
| **OPN-01** | Radial potential at 0.15 M: the text quotes −14/−47 mV, the appendix table −29/−57 mV | Author | Use of the radial potential as a regression target; excluded from Tier 3 and Tier 4 targets until settled |
| **OPN-02** | Location of the author's contour script | Author | Nothing on the critical path. Phase 2 is planned against the specified contour pipeline; the script is upside if it arrives (RSK-06) |
| **OPN-03** | PlyAB supporting-information details: analyte relative permittivity, per-position mesh strategy (remesh against ALE), barrier heights in kT, electro-osmotic flow velocities | Author, from the retained model files | Analyte force regression targets and adoption of PlyAB as a second reference case after v1.0 |
| **OPN-04** | ClyA-AS mutation list: 8 mutations relative to the *S. typhi* wild type in one place, 27 relative to the *E. coli* 2WCD structure in another. Both internally correct | Author, with the structure-preparation stage | Provenance of `Q_net` (FR-12); the structure-preparation stage must record which list was applied to which PDB |
| **OPN-05** | Pore-polygon vertex table. **Delivered** as `data/geometry/clya_as_radial_geometry.csv`, 185 vertices, extents as published; §2.2 and §5.2.1 are amended to it and the §5.2.1 fixture and VAL-05 proceed on it. Outstanding only: whether the model report's 190-vertex polygon differs from this table by more than the five vertices the assembly arithmetic accounts for, and which of the two a Tier-3 comparison should cite | Author, on the 185-versus-190 count | None on the implementation — the fixture is the delivered table, and a later reconciliation is a data drop, not a code change |

---

## 11. Companion knowledge base

Shipped alongside this specification as `nanopnp-kb/` and held in the repository root from the
first commit, so that agents and people working on the codebase read from local, verified sources.

| Path | Content |
|---|---|
| `CLAUDE.md` | Agent instructions; points at the index; carries the maintenance rule |
| `.knowledge/00-index.md` | Index, conventions, provenance, open questions |
| `.knowledge/01-physics-epnpns.md` | Normative equations, corrections, parameters, errata |
| `.knowledge/02-electrokinetics-background.md` | EDL, Poisson–Boltzmann, electro-osmosis, selectivity, rectification |
| `.knowledge/03-nanopore-biology.md` | Biological nanopores, ClyA, electrophysiology, glossary |
| `.knowledge/04-clya-geometry-and-charge.md` | The pipeline as executed, with numeric validation targets |
| `.knowledge/05-analyte-and-forces.md` | Analyte representation, forces, trapping |
| `.knowledge/06-numerics-fem.md` | Weak forms, solvers, continuation, QoI extraction |
| `.knowledge/07-software-stack.md` | Libraries, versions, licences, tested behaviours |
| `.knowledge/08-validation-benchmarks.md` | The four-tier benchmark ladder with formulas |
| `.knowledge/09-comsol-reference-settings.md` | Reference mesh, solver and stabilisation settings |
| `data/corrections/willems2020_nacl.yaml` | Fitted correction parameters, transcribed and verified |

Claims verified by running code are marked `[tested]`, claims verified by arithmetic `[verified]`,
and anything unverified says so. The maintenance rule, stated in `CLAUDE.md`: when something
durable is learned, it is written here.

---

## 12. References

### 12.1 Normative sources

- Willems K., Ruić D., Lucas F.L.R., Barman U., Verellen N., Hofkens J., Maglia G., Van Dorpe P.
  *Accurate modeling of a biological nanopore with an extended continuum framework.*
  **Nanoscale 12, 16775–16795 (2020).** DOI [10.1039/D0NR03114C](https://pubs.rsc.org/en/content/articlelanding/2020/nr/d0nr03114c)
- Preprint (open access): bioRxiv [10.1101/2020.01.08.897819](https://www.biorxiv.org/content/10.1101/2020.01.08.897819v1.full)
- ESI with COMSOL implementation detail, correction coefficients pp. 4–5:
  [d0nr03114c1.pdf](https://www.rsc.org/suppdata/d0/nr/d0nr03114c/d0nr03114c1.pdf)
- Willems K., PhD thesis (CC-BY-4.0), chs. 5–6:
  [github.com/willemsk/phdthesis-text](https://github.com/willemsk/phdthesis-text) ·
  arXiv mirror [2103.05043](https://arxiv.org/abs/2103.05043)
- COMSOL model report `npgrid_clya_v8_NaCl_report.mph` (COMSOL 5.4 build 388, 22 May 2020),
  162 pages; Appendix B.
- Mueller M., Grauschopf U., Maier T., Glockshuber R., Ban N. *The structure of a cytolytic
  α-helical toxin pore reveals its assembly mechanism.* **Nature 459, 726 (2009)**;
  [PDB 2WCD](https://www.rcsb.org/structure/2WCD)
- Huang G., Willems K., Bartelds M., van Dorpe P., Soskine M., Maglia G., *Nano Lett.* **20**,
  3819–3827 (2020) (PlyAB electro-osmotic vortices); *ACS Nano* **13**, 9980 (2019)
  ([protein trapping in ClyA](https://pmc.ncbi.nlm.nih.gov/articles/PMC6764111));
  *Angew. Chem. Int. Ed.* 2022, DOI [10.1002/anie.202206227](https://doi.org/10.1002/anie.202206227)
  (PlyAB force and PMF computation)
- Li L., Li C., Zhang Z., Alexov E. *On the dielectric "constant" of proteins: smooth dielectric
  function for macromolecular modeling and its implementation in DelPhi.* **J. Chem. Theory
  Comput. 9, 2126–2136 (2013).**

### 12.2 Numerical methods

- Mitscha-Baude G., Buttinger-Kreuzhuber A., Tulzer G., Heitzinger C. *Adaptive and iterative
  methods for simulations of nanopores with the PNP–Stokes equations.* **J. Comput. Phys. 338,
  452 (2017).** [arXiv:1608.05313](https://arxiv.org/abs/1608.05313) · code:
  [mitschabaude/nanopores](https://github.com/mitschabaude/nanopores) (MIT)
- Metti M.S., Xu J., Liu C. *Energetically stable discretizations for charge transport and
  electrokinetic models.* **J. Comput. Phys. 306, 1 (2016).**
- Chaudhry J.H., Comer J., Aksimentiev A., Olson L.N. *A stabilized finite element method for
  modified Poisson–Nernst–Planck equations…* **Commun. Comput. Phys. 15, 93 (2014).**
  [PMC3867981](https://pmc.ncbi.nlm.nih.gov/articles/PMC3867981/)
- Hughes T.J.R., Engel G., Mazzei L., Larson M.G. *The continuous Galerkin method is locally
  conservative.* **J. Comput. Phys. 163, 467 (2000).**
- Becker R., Rannacher R. *An optimal control approach to a posteriori error estimation in finite
  element methods.* **Acta Numerica 10, 1–102 (2001).**
- Bank R.E., Rose D.J. **Numer. Math. 37, 279 (1981)** (damped Newton);
  Kelley C.T., Keyes D.E. **SIAM J. Numer. Anal. 35, 508 (1998)** (pseudo-transient continuation)
- Bazant M.Z., Chu K.T., Bayly B.J. **SIAM J. Appl. Math. 65, 1463 (2005)** (1D PNP limiting
  current)
- Rice C.L., Whitehead R. **J. Phys. Chem. 69, 4017 (1965)** (capillary electro-osmosis);
  Hall J.E. **J. Gen. Physiol. 66, 531 (1975)** (access resistance)

### 12.3 Software

- [NGSolve/Netgen](https://ngsolve.org/) (LGPL-2.1) ·
  [ngsPETSc](https://joss.theoj.org/papers/10.21105/joss.07359) ·
  [DOLFINx](https://github.com/FEniCS/dolfinx) (LGPL-3) ·
  [EchemFEM](https://github.com/LLNL/echemfem) (MIT) · [Gmsh](https://gmsh.info) (GPLv2+)
- [MDAnalysis](https://docs.mdanalysis.org/) (LGPLv3) ·
  [GridDataFormats](https://github.com/MDAnalysis/GridDataFormats) ·
  [mdahole2](https://github.com/MDAnalysis/mdahole2)
- [PDB2PQR](https://github.com/Electrostatics/pdb2pqr) (BSD) ·
  [PROPKA3](https://github.com/jensengroup/propka) ·
  [APBS](https://github.com/Electrostatics/apbs) (BSD-3)
- [scikit-image](https://scikit-image.org/) · [Shapely](https://shapely.readthedocs.io/) ·
  [meshio](https://pypi.org/project/meshio/)

### 12.4 Standards

- ISO/IEC/IEEE 29148:2018, *Systems and software engineering — Life cycle processes — Requirements
  engineering.* Structure of §§1–3.
- IEEE 1016-2009, *IEEE Standard for Information Technology — Systems Design — Software Design
  Descriptions.* Structure of §5.
- IEEE 1012-2016, *IEEE Standard for System, Software, and Hardware Verification and Validation.*
  Structure of §7.
- IETF RFC 2119, *Key words for use in RFCs to Indicate Requirement Levels.* §1.5.

---

## Appendix A. Requirements traceability matrix

Each requirement of §3 is mapped to the activity of §7 that demonstrates it. "None yet" records
that no verification or validation activity has been specified; it is not a statement that none is
needed.

| Requirement | Verification or validation activity |
|---|---|
| IF-01 | VER-25 |
| IF-02 | None yet |
| IF-03 | VER-09 |
| IF-04 | None yet |
| IF-05 | None yet |
| IF-06 | VER-27 |
| IF-07 | None yet |
| IF-08 | VER-24 |
| IF-09 | None yet |
| FR-01 | None yet |
| FR-02 | None yet |
| FR-03 | None yet |
| FR-04 | None yet |
| FR-05 | VER-01 (shared annular-volume integration) |
| FR-06 | None yet |
| FR-07 | VAL-05 |
| FR-08 | None yet |
| FR-09 | VER-28, VAL-05 |
| FR-10 | VER-10, VAL-05 |
| FR-11 | None yet |
| FR-12 | VAL-06 |
| FR-13 | VER-01, VER-02, VAL-06 |
| FR-14 | VER-01, VER-02 |
| FR-15 | VAL-06 |
| FR-16 | VER-03 |
| FR-17 | VER-08, VER-16, VER-18 |
| FR-18 | VER-13, VAL-10 |
| FR-19 | VER-12, VER-13 |
| FR-20 | None yet |
| FR-21 | VER-20, VER-22 |
| FR-22 | VER-19, VER-21, VER-22 |
| FR-23 | VER-11 |
| FR-24 | None yet |
| FR-25 | VER-24, VER-26 (manifest emitted per §7.6) |
| FR-26 | VER-09, VER-26 |
| FR-27 | VER-23, VER-25, VER-26 |
| FR-28 | None yet |
| FR-29 | None yet |
| QR-01 | VER-12 to VER-22, in particular VER-17 and VER-18 |
| QR-02 | VAL-01, VAL-02 |
| QR-03 | VER-01 |
| QR-04 | VER-11 |
| QR-05 | VAL-07, VAL-08, VAL-09 |
| QR-06 | None yet |
| QR-07 | None yet (§8.2 criterion 3) |
| QR-08 | VER-26 for manifest sufficiency; QoI reproduction none yet |
| QR-09 | None yet |
| QR-10 | None yet |
| QR-11 | None yet |
| QR-12 | VER-10 |
| QR-13 | None yet |
| QR-14 | VER-03 |
| QR-15 | None yet |
| CON-01 | None yet |
| CON-02 | VER-20, VER-22 |
| CON-03 | None yet |
| CON-04 | None yet |
| CON-05 | VAL-07 (residual discrepancy below 0.05 M) |
| CON-06 | None yet |
| CON-07 | None yet |
| CON-08 | §6.6 measurement table (§8.2 criterion 3, discharged) |
| CON-09 | None yet |
| CON-10 | VER-27 (the default ingestion path imports no Gmsh) |
| CON-11 | §6.6 measurement table — measured; the conflict it exposed is resolved by the 2 September 2026 amendment to CON-11 and ADR-003 |
| CON-12 | None yet |
| CON-13 | None yet |
| CON-14 | None yet |

Coverage: 35 of the 67 requirements in §3 have a specified activity; 32 are recorded as "none yet",
predominantly interface, portability, licensing and documentation requirements whose demonstration
is by inspection rather than by test.

---

## Appendix B. Reference COMSOL model settings

Condensed from the 162-page model report. Full detail is in
`.knowledge/09-comsol-reference-settings.md`.

| Aspect | Setting |
|---|---|
| Model file | `npgrid_clya_v8_NaCl_report.mph`, report dated 22 May 2020 |
| Software version | COMSOL Multiphysics 5.4, build 388 |
| Dimensionality | 2D axisymmetric, steady state |
| Mesh type | Free triangular throughout, no boundary layers |
| Mesh statistics | 120,917 triangles, 1,879 edge elements, 196 vertex elements; minimum element quality 0.6378, average 0.9765 |
| Global size ("Finer") | max 10 nm, min 0.001 nm, curvature factor 0.25, growth rate 1.05 |
| Pore boundary size | max 0.05 nm, min 0.001 nm, curvature factor 0.25, growth rate 1.05 |
| Pore domain size ("Extremely fine") | max 0.1 nm, min 0.004 nm, curvature factor 0.2 |
| Reservoir domain size | max 2.8 nm, min 0.04 nm, growth rate 1.04 |
| Reservoir outer boundary size | max 5 nm, min 0.025 nm, growth rate 1.25 |
| Symmetry axis inside pore | max 0.075 nm, min 0.04 nm |
| Linear solver | PARDISO, pivoting perturbation 1 × 10⁻¹³ |
| Nonlinear solver | Fully coupled; initial damping 0.2, minimum damping 0.01, recovery damping 0.2; maximum 100 iterations; relative tolerance 1 × 10⁻⁶ |
| Continuation | On `V_bias` |
| Stabilisation, Transport of Diluted Species | Streamline diffusion on; crosswind diffusion on, type "Do Carmo and Galeão", equation residual "Approximate residual"; isotropic diffusion off; convective term in conservative form |
| Stabilisation, Laminar Flow | Streamline and crosswind diffusion on, isotropic off |
| Discretisation | Potential quadratic, concentrations quadratic, velocity and pressure both linear (P1+P1, not Taylor–Hood) |
| Assembly integration orders | Crosswind terms order 6, streamline order 4, most other weak terms order 4, order 2 in the flow interface |
| Current extraction | Variational reaction flux at integration order 4: `F*(z_cpos*tds.ntflux_cpos + z_cneg*tds.ntflux_cneg)` over an electrode boundary |
| Permittivity parameters | `epsr_ms = 30.08`, `epsr_alpha = 11.5` (Gavish NaCl) |
| Sweep | Parameter switch over 5 physics cases × 35 bias values × 21 salt concentrations = 3,675 solves |
| Runtime | 41 h on 12 cores |
| Mesh convergence study | None present in the report (RSK-09) |

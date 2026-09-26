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
| Pore boundary | Closed polygon; the delivered 185-vertex table is the geometry of record, the model report tabulates 190 after its import conditioning (§5.2.1) |
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
| Python | 3.11 to 3.14 (**amended 24 September 2026**, §8.2.2 B4) |
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
| gemmi 0.7+ | MPL-2.0 | mmCIF structure input, which MDAnalysis 2.10 does not read (**added 25 September 2026**, WP18) |
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

NOTE (Versioning; **added 23 September 2026**): the releases above are git tags `vX.Y.Z` on the
commit that closes the phase: `v0.1.0` for Phase 0, and `v0.5.0` for Phase 1 on the merge of its
end-of-phase report (§8.1). Each merged work package is tagged `vX.Y.Z-alpha.N` on its last commit
on `main`, where N counts the phase's work packages toward that release. The history before this
NOTE was tagged retroactively on the same rule. The tag names are SemVer, and PEP 440 reads them as
`X.Y.ZaN` (`0.5.0a10`). The package version is derived from the tag (hatch-vcs), so a commit between
tags installs as a development version naming that commit, and the provenance manifest's recorded
`nanopnp` version identifies the code that produced a result (FR-25). The version enters no artefact
key: the environment is recorded beside an artefact, never hashed into it (§5.3.2). `CHANGELOG.md`
records every tag, and a milestone tag publishes a GitHub Release with its section as the notes.

---

## 3. Requirements

The subject of each requirement is the product unless stated otherwise.

### 3.1 External interfaces

| ID | Requirement |
|---|---|
| **IF-01** | SHALL expose a Python API in which every pipeline stage is a separately importable, invocable object, stable from v0.5 onward. |
| **IF-02** | SHALL provide a CLI over the same stage objects, able to execute a case file, run one stage, and dispatch a sweep. |
| **IF-03** | SHALL accept one declarative YAML case file, identified by `schema: nanopnp/case/v2`, as the complete run specification, rejecting unknown keys with a diagnostic naming the key. A document declaring `nanopnp/case/v1` SHALL be read losslessly as its v2 upgrade (§5.3.1). **Amended 24 September 2026** from v1 (§8.2.2 B3). |
| **IF-04** | SHALL read structures in PDB and mmCIF, and trajectories in DCD, XTC, TRR and NetCDF. |
| **IF-05** | SHALL read and write volumetric density and charge grids in OpenDX and CCP4. |
| **IF-06** | SHALL write meshes in Gmsh MSH 4.1 as the archival format, and SHOULD read any format meshio supports. |
| **IF-07** | SHALL write solution fields in XDMF with HDF5 heavy data. |
| **IF-08** | SHALL accompany every result artefact with a machine-readable provenance manifest (FR-25). |
| **IF-09** | SHALL provide a desktop graphical interface covering case editing, run control, convergence monitoring and field visualisation, as a thin shell over the IF-01 stage objects. |

Rationale (IF-06): MSH 4.1 is the only format in the toolchain carrying physical-group tags,
higher-order elements and mixed element types without loss.

NOTE (IF-05, QR-09; **retired 24 September 2026**, §8.2.2 B4): the CCP4 write side was
conditional while the floor was Python 3.10, where GridDataFormats resolved to 1.0.2 and had no MRC
writer. The 3.11 floor takes GridDataFormats 1.2 or later everywhere, so IF-05 is met
unconditionally and VER-29 asserts the CCP4 round trip without a refusal branch.

NOTE (IF-02, exit codes): the CLI's exit status is a contract, because the job-array dispatch of
FR-24 branches on it and QR-06 requires a failed member to be distinguishable from a refused one.
`0` success; `1` an unexpected failure, the only class whose traceback is worth keeping; `2` a usage
error; `3` a case rejected by validation or by schema; `4` a numerical gate abort of the QR-12
family; `5` nonlinear non-convergence; `130` cancellation. A dispatch of a single sweep member SHALL exit
with that member's own code, which is what a job array branches on; a local multi-worker sweep SHALL
exit `0` once every member has reached a terminal state and the dataset has been written, the
per-member codes being recorded in the dataset (§5.3.4) rather than reduced to one. Non-convergence
at the corners of the FR-17 envelope is an expected result of a sweep, and an exit status that could
not distinguish it from a broken dispatch would answer the wrong question. The mapping from exception to code SHALL
be an explicit enumeration rather than a base-class test, and every public exception type of the
package SHALL be either classified by it or listed as deliberately excluded with a reason, in both
directions, so that an error type added later fails the enumeration rather than silently becoming
`1`. Diagnostics and log records go to standard error; standard output carries only the command's
own result, so that a caller may parse it.

NOTE (IF-02, configuration): no command-line flag SHALL change what is solved. Flags select where
output is written, which stages run and how much is logged; every quantity that changes a number
lives in the case file (IF-03). A flag duplicating a case-file setting would make the FR-25 manifest
describe one of two disagreeing sources of truth.

NOTE (IF-02, generators; **added 23 September 2026**): `nanopnp mesh cylinder` and
`nanopnp mesh reference` write an *input artefact*, a Gmsh MSH 4.1 mesh (IF-06), rather than run a
case. The geometric flags of `mesh cylinder` shape that file, and a run that later consumes it
records it by content hash through `inputs.mesh` (§5.3.1, §5.3.2), exactly as it would any
externally supplied mesh. So they do not change what a run solves, and the configuration NOTE above
is not breached. `mesh reference` takes no geometric flag, since its preset is fixed by §5.2.2 and
the geometry of record. Both commands print the written mesh's content hash and the
`inputs.mesh.groups` mapping a case needs to read it. Both are subject to the mesh quality gate of
VER-10. These commands are the v0.5 means of producing a mesh without Python, and they are not the
meshing pipeline of FR-10, which remains v0.9.

NOTE (IF-01, public surface; **added 23 September 2026**): the stable API is the set of names in
`nanopnp.__all__`, together with the modules the user documentation's API reference names. Every
other module is internal and may change without notice before v1.0. The top-level names are
resolved lazily (PEP 562 `__getattr__`), so `import nanopnp` imports neither NGSolve, Netgen nor
numpy. The command line, the shell and the sweep runner import the package purely to introspect
it, and an eager re-export would charge every one of them for a solver it never assembles.

NOTE (IF-07, field export): solution fields are written as XDMF with HDF5 heavy data at the P2 node
set — the mesh vertices together with the edge midpoints, `ndof = nv + nedge` — with topology
`Triangle_6`. A P2 function on a straight-sided triangle is determined by its six nodal values, and a
P1 function's midpoint value is the mean of its endpoints, so one node set records both orders of
NUM-01 exactly and no interpolation error is introduced by the export. Midside nodes SHALL be
identified by the unordered pair of vertices they lie between rather than by any backend's local edge
numbering. Ω and Ω_w are written as separate files: the fields of NUM-01 that live on the fluid alone
SHALL NOT be padded over the solid, because a zero concentration inside a wall is indistinguishable
in a viewer from a converged depletion. Coordinates are in nm, matching the MSH 4.1 archival mesh
(IF-06); values are in SI with the unit in the attribute name, and the §6.3 scale set is recorded in
the file so that the nondimensional state remains recoverable. The `2π` of the axisymmetric measure
SHALL NOT be applied: exported fields are pointwise, and §6.7 restores that factor exactly once, in
the quantity-of-interest extraction. Heavy data is compressed.

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

NOTE (FR-05, FR-06; **added 25 September 2026**, WP19): the n rotated copies are averaged in the
angular harmonic basis. There the average keeps the harmonics that are multiples of n, so it leaves
the azimuthal mean unchanged and defines FR-06's residual variance. The binning weights are exact
cell–annulus overlaps. The §5.3.1 NOTE on `geometry.density` is the contract.

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
| **QR-09** | SHALL install from binary wheels on Windows, macOS and Linux for Python 3.11–3.14, with no compilation on the target machine. **Amended 24 September 2026** from 3.10–3.14 (§8.2.2 B4). | Portability |
| **QR-10** | A nanopore experimentalist without Python knowledge SHALL be able to load a structure, accept defaults and obtain a conductance prediction and a field visualisation in the desktop application unaided. | Usability |
| **QR-11** | Each release from v0.5 onward SHALL ship a usable graphical surface over the functionality existing at that release. | Usability |
| **QR-12** | Every automatic gate failure SHALL abort the run with a diagnostic naming the gate, the offending quantity and its location. | Usability |
| **QR-13** | The ePNP-NS weak forms SHALL be expressed once against the internal backend interface and SHALL NOT be duplicated per backend. | Maintainability |
| **QR-14** | Adding a correction parameterisation SHALL require only a data file; adding a physics model SHALL require only one class (FR-20). | Maintainability |
| **QR-15** | v1.0 SHALL ship user documentation, tutorials, a JOSS submission and a DOI-archived release. | Maintainability |

NOTE (QR-15; **added 23 September 2026**): the user documentation and the worked examples are
delivered incrementally from v0.5, by the documentation track of §8.1, each phase documenting what
it ships. The requirement itself is unchanged. v1.0 is where it is met in full, including the JOSS
submission and the DOI-archived release, which no earlier phase delivers. VER-45 and VER-46
demonstrate the documentation part at every release. They do not demonstrate the JOSS or DOI parts.

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
| **CON-09** | The core library SHALL be licensed BSD-3-Clause. LGPL dependencies are acceptable under dynamic linking (NGSolve/Netgen LGPL-2.1, MDAnalysis LGPLv3, PySide6 LGPL-3). MPL-2.0 dependencies are acceptable used unmodified as separate packages (gemmi, the mmCIF reader of the `structure` extra; **added 25 September 2026**). The field viewer's renderer, npm `webgui` (LGPL-2.1-or-later, bundling three.js under MIT and dat.gui under Apache-2.0), MAY be redistributed with the package, **unmodified and as a separate file** loaded at run time, beside its licence texts and a notice naming its corresponding source, which the repository and the source distribution carry verbatim; nothing in the library SHALL be linked against it. PyQt SHALL NOT be used, being GPL-3 or commercial only. |
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

NOTE (the driver clamp): the wall functions of PHY-11 are stated for `d̄ ≥ 0`, and the ion form
`1 − exp(−P₁(d̄ + P₂))` has its root at `d̄ = −P₂`. A negative sample of a discrete distance field
therefore does not attenuate `D_i` and `μ_i`, it reverses their sign, giving an anti-diffusion
operator in the one neighbourhood where the wall correction is supposed to hold ions back. The
driver SHALL be clamped to `max(d̄, 0)` before any wall form evaluates it, exactly as PHY-13
requires of the concentration driver, and the clamp SHALL be applied where the correction reads the
driver so that adding an electrolyte inherits it. The clamp is a floor on a discretisation artefact
and SHALL NOT be relied on to make an under-resolved field admissible; NUM-34 is what decides that.

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

NOTE (the smoothed dielectric is a blend, PHY-11, PHY-12, PHY-20): a smoothed transition **to `ε_w`**
cannot be expressed as a static `ε_r` field, because `ε_w = ε_r,f⁰ · ε_r,f^c(⟨c⟩)` and `⟨c⟩` is
solved for. A supplied dielectric field SHALL therefore be a solid fraction `χ ∈ [0, 1]`, and the
permittivity SHALL be

```
ε_r(r, z) = χ(r, z) · ε_p  +  (1 − χ(r, z)) · ε_r,f(⟨c⟩)
```

with the 1–2 Å transition carried by `χ` alone. Setting `χ` to the sharp material indicator
reproduces PHY-20's piecewise assignment exactly, so the smoothed field is a refinement of the
validated model rather than a replacement for it, and is recorded as a deviation when supplied. An
absolute `ε_r` field SHALL be refused, naming this clause: accepting one would silently disable the
permittivity correction while the run continued to report ePNP-NS. The mesh still carries the
material split, so Nernst–Planck is still not solved inside the protein; the field smooths the
coefficient, not the domain.

NOTE (the `2πr` cancels, PHY-16, PHY-19): under the axisymmetric volume element `dV = 2πr dr dz`,
the Jacobian and the `1/(2πr)` of PHY-16 step 6 cancel identically, so

```
∫_Ω ρ_pore · 2πr dr dz  =  ∫_{Ω, r ≥ r_guard} rhoq_pore(r, z) dr dz
```

and the conservation check of step 7 is **blind to the Jacobian** for an `areal_charge_density`
source: an error in how `r` enters cancels against itself. This is the compensating error PHY-19's
rationale names. Two consequences are normative. First, the check SHALL be reported as two legs — a
producer leg comparing the planar integral of the source grid against the declared `Q_net`, and a
consumer leg comparing the integral over the deployed mesh against that planar integral — each gated
at QR-03's tolerance, so that a failure names which side of the interface it belongs to; where no
`Q_net` is declared, the producer leg SHALL be recorded as not run and the consumer leg SHALL still
gate. Second, the per-`z`-slice cumulative check SHALL be evaluated against a Lipschitz weight of
stated width rather than a step, applied identically to both sides, since a step is integrated
inside every element the plane crosses and its quadrature error exceeds the tolerance it is meant to
enforce.

NOTE (the consumer leg is a resolution question, not a tolerance one, QR-03, PHY-19): measured on
the delivered ClyA `rhoq_pore` table — 1401 x 3401 at 0.005 nm, `r` in [0, 7] nm, `z` in
[-3.5, 13.5] nm — the producer leg is `4.7 x 10^-12` (`Q_grid = -71.999999999663 e` against a
declared `-72 e`) while the consumer leg on the WP8 reference mesh, 44 316 elements graded to
0.05 nm at the pore wall, is `9.9 x 10^-3`: ten times QR-03's budget, from a field the producer
delivered essentially exactly. Neither refinement route closes it. Refining `h` to 3 463 372
elements leaves the leg at `-1.1 x 10^-2` — *worse* than at 44 316, and non-monotone in between —
and raising the quadrature to order 37 on the fixed mesh oscillates through `+5.9 x 10^-4`,
`-3.0 x 10^-3`, `+2.8 x 10^-3` without settling. The cause is that the field's own structure is
below element scale: along the densest `z` the table changes sign 49 times, with extrema a median
0.035 nm apart, so pointwise quadrature of the bilinear interpolant is aliased rather than
inaccurate, and an aliased integral converges in neither `h` nor order.

Three consequences are normative. First, **the tolerance SHALL NOT be slackened to accommodate
this**: 10^-3 is what a conserved deposition achieves and the gate stays there, so a field whose
structure the deployed mesh cannot carry is refused rather than integrated badly. Second, the
quadrature-agreement gate is what SHALL name that case — on the delivered table it fires first, at
`9.3 x 10^-3` against its own `10^-4`, and reports that the mesh under-resolves the supplied field
rather than that charge was lost. Third, the remedy is on the **producer** side and is out of scope
until it exists (FR-13, FR-14, Phase 3): a charge deposited onto the finite-element space and
rescaled to `Q_net` conserves by construction, where sampling somebody else's interpolant at
quadrature points cannot. Until then a supplied `areal_charge_density` of this character SHALL be
ingested only with the gate's verdict recorded in the manifest.

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
| 1 | Structure ingestion and alignment | PDB/mmCIF, optional trajectory, expected point group | Aligned ensemble; Cₙ axis on z at r = 0 | MDAnalysis 2.10+ (LGPLv3) for PDB and every trajectory format; gemmi 0.7+ (MPL-2.0) for mmCIF, which MDAnalysis 2.10 does not read; the Kabsch rotation for superposition, cross-checked against MDAnalysis `rotation_matrix`; MDTraj as alternative reader; PDBFixer or Modeller for missing loops | Oligomeric state matches (ClyA 12, αHL 7, MspA 8); abort on missing chains (FR-03) |
| 2 | Density map | Aligned ensemble, grid spacing, kernel | 3D density map | Vectorised numpy Gaussian deposition over a spherical stencil truncated at 10⁻⁶, per-atom width σR_i from the CHARMM radius set of the §5.3.1 NOTE on `geometry.density`, sharpness 0.93; `gridData` IO. MDAnalysis `DensityAnalysis` is histogram-only and is not used (**amended 25 September 2026**, WP19) | Grid spacing 0.25–0.5 Å (FR-04); every atom has a radius; the map is finite and within [0, 1] |
| 3 | Symmetry reduction to (r, z) | 3D map, n | (r, z) map; residual azimuthal variance, Cₙ-averaged and raw | numpy and `scipy.sparse`; exact cell–annulus overlap weights; the Cₙ average in the angular harmonic basis (**amended 25 September 2026**, WP19) | Variance emitted with the geometry (FR-06, CON-04); annular weights summing to the exact annulus areas. The radius profile against the probe-radius profile is stage 4's gate (§5.2.1, §8.2.2 B5) |
| 4 | Contour extraction and conditioning | Stage 3's (r, z) mean; the aligned ensemble and its radius set, for the probe-radius profile; isolevel, smoothing and simplification tolerance | Closed conditioned polyline, a `nanopnp/profile/v1` document | scikit-image, Shapely (both BSD-3) and numpy, per §5.2.1 (**amended 26 September 2026**, WP20) | §5.2.1 (FR-08) |
| 5 | CAD assembly | Stage 4's polyline or a supplied `inputs.profile`, membrane specification with its `centre_z_nm` shift, reservoir radius, optional analyte | Fragmented (r, z) region, domains and boundaries tagged, as a declarative region record | `netgen.occ` (LGPL-2.1, OpenCASCADE, in-process) primary; Gmsh OCC Python API (GPLv2+) optional | All bodies fragmented and imprinted, interfaces conformal, no gap or overlap at the membrane-to-pore junction, each domain one face, the membrane's inner edge strictly inside the body (FR-09; §5.2.1 NOTE on the membrane junction on any profile). **Amended 26 September 2026** (WP21) |
| 6 | Meshing | Fragmented region, size fields | Graded triangular mesh | Netgen (LGPL-2.1) default, Gmsh (GPLv2+) optional, behind the mesh adapter | §5.2.2 (FR-10, QR-12): the VER-10 and VER-27 gates, as on an ingested mesh, and the wall-size gate of the §5.3.1 NOTE on `numerics.mesh` (**amended 26 September 2026**, WP21) |
| 7 | Charge assembly | Prepared ensemble, pH, force field, **and the deployed mesh** (its gate is evaluated there, PHY-19); on the consumer path, a supplied field document instead of the ensemble | ρ_pore(r, z), Q_net, dielectric field, ion-exclusion surface | PDB2PQR 3.7+ (BSD-3) driving PROPKA3; quintic B-spline (`spl4`) deposition; APBS 3.4.1 (BSD-3) cross-check; settings per PHY-16 | Charge conservation to 10⁻³ of Q_net on the deployed FE mesh, plus the per-z-slice cumulative check (FR-14, QR-03, PHY-19) |
| 8 | Materials | Electrolyte specification, correction model names, coefficient files | D_i, μ_i, η, ϱ, ε_r as fields in ⟨c⟩ and d | Correction registry, `data/corrections/willems2020_nacl.yaml` | Conformance values of §4.3 reproduced; clamps above 5.3 M logged with location and property (PHY-13) |
| 9 | Case assembly | Mesh, charge and dielectric fields, materials, boundary conditions, bias, analyte, numerics | Resolved case document, assembled discrete problem | `io/` schema validator, `physics/` model registry | Schema `nanopnp/case/v2` validates, a v1 document upgraded losslessly, unknown keys rejected with a diagnostic naming the key (IF-03); round trip semantically identical (FR-26) |
| 10 | Solve | Assembled problem, continuation ladder, optional warm start | Converged fields, iteration history | NGSolve 6.2.2606+ (LGPL-2.1), damped Newton; UMFPACK (GPL-2+) or scipy SuperLU (BSD) (CON-08) | No negative concentration at any nonlinear iterate; ladder completed to the target rung (FR-17); §6.5, §6.6 govern |
| 11 | QoI extraction | Converged fields | I, t₊, RR, EOF rate, F^em(z), F^hd(z), ΔU(z) | Domain/indicator form and variational reaction flux, both implemented | The two routes agree within the stated tolerance, checked in CI (FR-23, QR-04); §6.7 governs |
| 12 | Reporting and export | Results, artefact hashes, environment | Figures, XDMF/HDF5 fields, dataset, case file, manifest | `io/`, `sweep/` result store | Manifest complete and sufficient to reconstruct the run (FR-25, QR-08) |

Design notes, recorded where an implementer would otherwise choose wrongly.

| Stage | Note |
|---|---|
| 1 | The Cₙ axis comes from chain-permutation superposition: superpose chain A onto chain B, take the rotation's eigenvector of eigenvalue 1 (FR-02). Principal axes are unusable because they drift between frames. Over the 98 frames of the ClyA-AS ensemble, the largest-variance axis of the Cα set moved by up to 1.54° (rms 0.66°), while the chain-permutation axis moved by at most 0.010°. The cause is not degeneracy: the axial eigenvalue is well separated (1432 Å² against 801 and 881 Å² on the first frame). It is the chains' asymmetric fluctuation, which the permutation fit averages out by construction (**measured 25 September 2026**, WP18 plan, Design §4). Stage 1 is specified in full in the §5.3.1 NOTE on `structure:`. |
| 2 | Histogram plus uniform `gaussian_filter` is rejected: van der Waals-weighted smearing preserves the exclusion surface, uniform post-smoothing rounds the constriction. The grid is not coarsened, the *trans* constriction being about 3.3 nm across with a contour position that moves measurably with resolution. |
| 3 | The n rotated copies are averaged before azimuthal averaging. Binning is area-weighted over exact annular volumes (about 6 cells per annulus of width h at r = h, about 630 at r = 5 nm, per slice at h = 0.05 nm). **Amended 25 September 2026** (WP19 plan, Design §2–§3): the overlap weights are exact, so no bin is interpolated. The earlier "innermost 2–3 bins interpolated" compensated for centre-assigned binning, and against exact weights every interpolant tried was worse somewhere. The rotated copies are averaged in the angular harmonic basis, where the average keeps the harmonics m ≡ 0 (mod n): it is exact and costs one deposition. Depositing n rotated copies costs n, and rotating the voxel map by interpolation smooths it, lowering the peak Cₙ variance of a C12 ring by 3–6 %. The binned mean is subtracted at each cell's own radius before any variance is taken, or the radial gradient across a bin reads as azimuthal variance. A 1° axis error adds about 0.2 nm of apparent radius to a 3.3 nm constriction. |
| 3, 5 | The bilayer is absent from the density map. It is defined analytically in (r, z) over the hydrophobic belt and fragmented against the pore contour. |
| 5 | Reference geometry: reservoir half-disc R = 250 nm, membrane thickness 2.8 nm, `z_cis` = 12.25 nm, `z_trans` = −1.85 nm. The membrane is a quadrilateral, not a rectangle: vertices (r = 2, z = −1.4), (3.5, +1.4), (250, +1.4), (250, −1.4) nm, inner edge slanted to meet the pore's outer surface. Code assuming a rectangle leaves a wedge of gap or overlap at the junction. CadQuery and build123d are 3D-solid-centric and unused; pythonocc serves BRep edge cases only. |

#### 5.2.1 Contour conditioning and its gate

Pipeline (**amended 26 September 2026**, WP20):

1. `find_contours` (sub-pixel marching squares, diagonal neighbours above the level joined) runs
   on stage 3's mean at the isolevel, default 0.25. Each point is placed by the grid's own axes,
   so bin j sits at its centre `r_j = j·h`.
2. The closed contours are assembled into the region above the isolevel. A contour left open at the
   grid's edge is refused.
3. The region is closed, then opened, by a disc of radius 2h, with h the density grid spacing.
   Every hole left is filled and recorded, and exactly one component is admitted.
4. The loop is resampled at uniform arc length h/2 and smoothed by Taubin λ|μ, which preserves the
   area where Laplacian and Chaikin smoothing shrink it.
5. Shapely `simplify` (Douglas–Peucker, topology preserved) runs at `simplify_tol_nm`, default
   0.02 nm, which must be below h.
6. Vertices are removed until no edge is shorter than `h_c`.
7. An optional periodic B-spline fit is not implemented.

The constants are recorded in the WP20 plan, D4–D9. They key the stage-4 artefact and are not case
keys.

| Gate criterion | Threshold |
|---|---|
| `LinearRing.is_valid`, `is_simple` | both true |
| Minimum vertex spacing | ≥ `h_c` |
| Minimum local feature size, measured two edges either side of each vertex | > 2 `h_c` |
| Loop topology | one component after the closing and opening, with no contour open at the grid's edge, holes filled and recorded, and the loop clear of the axis by `h_c` |
| Radius profile | `−h_c ≤ r_c(z) − R_p(z) ≤ 1.5 nm` on every mid-plane between z nodes that crosses the loop. `r_c` is the loop's innermost crossing, and `R_p` the frame-mean radius of the largest sphere centred on the axis that clears every atom's radius in the aligned structure. HOLE is an optional cross-check (§8.2.2 B5) |

Rationale (feature size): near-tangential self-approaches at the constriction generate slivers the
mesher cannot repair.

NOTE (the contour's size target, **added 26 September 2026**, WP20): `h_c`, the "target element
size" of the criteria above, is the density grid spacing h, 0.05 nm by default. It is not the
stage-6 wall size. NUM-30's `λ_D/5` is 0.27 nm at 0.05 M: read as the target, it would make the
contour depend on the electrolyte concentration, and at 0.05 M erase the lumen's corrugation.
Step 3's radius is set by the margin the feature-size criterion needs. Simplification moves each
wall by up to its tolerance, so the gap left by a closing of radius δ stays above `2h_c` only if
`δ > h + simplify_tol_nm`, and 2h meets that for every admitted tolerance. The gaps and fins it
removes, under 0.2 nm at the default grid, admit no water molecule and are thinner than one heavy
atom. Step 3 automates the "manual removal of overlapping and superfluous vertices" that the source
work records. On the ClyA-AS ensemble, a closing of radius h leaves a groove that fails the
criterion at 0.058 nm, and 2h passes it at 0.229 nm (WP20 plan, Design §2 and §4).

NOTE (the radius band, **added 26 September 2026**, WP20): the lower bound is geometric. Inside
the axis-centred sphere every atom is at least its own radius away, so the 25 % contour of the
azimuthal mean can enter that sphere by at most a fraction of an atom's width. The upper bound is a
gross-error check on the lumen's corrugation. `r_c − R_p` measures between +0.061 and +0.908 nm
on 2WCD (chains A–L), and between +0.173 and +0.869 nm on the ClyA-AS ensemble. The band does not
detect a radial scale error of a few per cent; VAL-05 does (WP20 plan, Design §5).

The reference pore boundary is published in the COMSOL model report as a closed 190-vertex polygon
(r ≈ 1.65–5.66 nm, z from −1.85 to 12.25 nm). The author's delivered tabulation of that boundary
SHALL be shipped as the regression fixture (§7.2), so solver work proceeds on the reference polygon
without the contour pipeline. The table is held in
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

NOTE (the membrane junction on any profile, stage 5, FR-09; **added 26 September 2026**, WP21): the
profile is first moved into the model frame, `z ← z − geometry.membrane.centre_z_nm`. On each plane
`z = ±t/2` the **lumen-adjacent body interval** `[r₁, r₂]` is bounded by the profile's two
smallest crossings of that plane. The inner edge of the membrane quadrilateral is the chord from
the lower plane's interval to the upper plane's that has the largest minimum distance to the
profile. It is searched on the 63 × 63 interior points `r₁ + (r₂ − r₁)k/64` of the two intervals.
Any chord with its ends in those intervals that lies inside the body yields the same region: a
fluid pocket between two such chords would be enclosed by them, by the body and by the plane
segments between their ends, which are body too, while the complement of a simple polygon is
connected. The widest-margin chord is taken because it is the choice furthest from failure. The
chord between the intervals' mid-points is **not** admissible in general. On the delivered fixture
it runs from (2.2387, −1.4) to (3.92, +1.4) and crosses the cleft under the cap between
(3.070, −0.016) and (3.235, 0.260), which splits the electrolyte in two. On the fixture the
widest-margin chord is (1.982, 3.464) nm, with a clearance of 0.237 nm. Stage 5 SHALL abort,
naming the criterion, the measured value, the threshold and the (r, z), on any of these:

- a plane crossing the profile fewer than twice, with the profile's model-frame z extent and
  `centre_z_nm` named;
- a best chord closer than 0.01 nm to the profile, so that the membrane is not representable as a
  quadrilateral with a slanted inner edge;
- a domain assembled as other than one face, with each face's centroid and area named;
- a profile vertex not strictly inside the reservoir disc;
- a membrane whose innermost radius on either plane differs from that plane's `r₂` by more than
  the fragmentation tolerance.

The last criterion is VER-28's junction measure, made generic. The shipped reference geometry keeps
its drawn corners (2.0, 3.5), and its mesh is unchanged. The fixture assembled with either chord
meshes to one connectivity, with vertices within 4.2 × 10⁻⁹ nm (WP21 plan, Design §1).

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
neither the geometry the table describes nor anything computed from it.

DECISION (the author, 5 September 2026): **the delivered 185-vertex table is the geometry of
record.** It is what the fixture ships, what `mesh/reference.py` assembles, and what VAL-05 and any
Tier-3 comparison cite. The model report's 190 stays recorded above as the count of the polygon
COMSOL held after its own import conditioning; no further reconciliation is sought, and the five
vertices are not chased. This settles which of two tabulations of one curve to use and touches
nothing the model report governs (`CLAUDE.md` §1.6) — not an equation, a correction or a fitted
parameter. OPN-05 is closed.

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
schema: nanopnp/case/v2
name: clya-wt-1M-100mV

inputs:                             # optional; supplied artefacts, §5.3.2
  mesh: {path: clya.msh, format: msh41,
         groups: {lumen: electrolyte, upper: cis, lower: trans,
                  clya: protein, bilayer: membrane,
                  pore_wall: wall, outer_rim: membrane_outer,
                  symmetry_axis: axis}}
  charge: {path: clya_charge.yaml, format: field1}
  eps_r:  {path: clya_solid_fraction.yaml, format: field1}
  # profile: {path: clya_profile.yaml, format: profile1}   # stage 4, nanopnp/profile/v1
  # pqr:     {path: clya.pqr, format: pqr}                 # stage 7's PDB2PQR step

structure:
  source: {path: 2WCD.pdb, variant: ClyA-AS, chains: all, selection: protein}
  ensemble: {trajectory: eq.xtc, frames: {last_ns: 5, count: 50}}
  symmetry: {point_group: C12, axis: auto}

geometry:
  density:  {grid_spacing_nm: 0.05, kernel: gaussian_vdw, sharpness: 0.93}   # 0.5 Å, as the paper
  contour:  {isolevel: 0.25, smoothing: taubin, simplify_tol_nm: 0.02}
  membrane: {thickness_nm: 2.8, centre_z_nm: 0.0}   # centre in the structure's frame, along the axis
  reservoir: {radius_nm: 250}
  analyte:  {shape: prolate_spheroid, a_nm: 2.0, b_nm: 3.0, z_nm: 6.0, charge_e: -8}

charge:
  ph: 7.5
  forcefield: CHARMM
  titration: propka
  smearing: {sharpness: 0.5, grid_spacing_nm: 0.005, axis_cutoff_nm: 0.01}
  exclusion_offset_nm: 0.0           # FR-15, PHY-20; 0 is the validated model, no exclusion shell
  dielectric_transition_nm: 0.0      # PHY-20 NOTE; 0 is the sharp indicator of the validated model

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
  solid_permittivities: {protein: 20.0, membrane: 3.2}   # PHY-20; the only place they are set

numerics:
  elements: {phi: P2, c: P2, u: P2, p: P1}
  mesh: {backend: netgen, wall_h_nm: auto, size_scale: 1.0, boundary_layer: false}
  nonlinear: {strategy: newton, damping: residual, max_iter: 100, rtol: 1e-6}   # NUM-16
  continuation: default_ladder
  stabilisation: none                # NUM-11; `supg` is its flag, `reference` matches §6.4
  wall_distance: {sources: wall, max_distance_nm: 3.0}                         # PHY-02
  linear: {solver: umfpack}          # see §6.6; MUMPS requires a source build

outputs: [current, transport_numbers, rectification, eof_rate, analyte_force, fields]
```

NOTE (`nanopnp/case/v2`, and reading a v1 document; **added 24 September 2026**, §8.2.2 B3): the
schema moved once, carrying every key Phases 2 and 3 are foreseen to need. Against v1 it **adds**
`inputs.profile`, `inputs.pqr`, `structure.source.selection`, `geometry.membrane.centre_z_nm`,
`charge.exclusion_offset_nm`, `charge.dielectric_transition_nm` and `numerics.mesh.size_scale`;
**renames** `structure.source.pdb` to `structure.source.path`, since IF-04 reads mmCIF as well; and
**removes** `charge.eps_protein` and `geometry.membrane.eps_r`, whose values
`physics.solid_permittivities` already carries. A permittivity set in two places is a calibration
parameter (PHY-20) with two sources of truth, and a default of 20 or 3.2 written in code would be a
fitted parameter hard-coded in Python; the author ruled on 24 September 2026 that the map is the one
place they are set. The seven added keys default to the validated configuration, so a v1 document
means under v2 exactly what it meant under v1. A document declaring `nanopnp/case/v1` SHALL be
read as its upgrade: the schema string is replaced, `structure.source.pdb` is renamed, and a written
`charge.eps_protein` or `geometry.membrane.eps_r` moves to `physics.solid_permittivities.protein` or
`.membrane`. The upgrade SHALL refuse, naming both keys and both values, a moved value that
disagrees with one the map already holds, and SHALL refuse a key v1 did not have, naming the key and
the schema it belongs to: a document is valid against the schema it declares or not at all. A v2
document that uses a removed or renamed key SHALL be refused with a diagnostic naming the v2 key
that replaced it. The upgrade is not a deviation and does not reach the solve: the schema string is
excluded from the provenance that keys a solve (§5.3.2), as `name:` and `outputs:` are, so a v1
document and its v2 rewrite key one stage-10 artefact and one VER-34 restore digest. Those are not
the keys v1 recorded for the same file, which carried the schema string: they moved once, at this
move (§5.3.2 NOTE). The stage-9 key
of a v1 document is the key of its upgrade, which differs from any key v1 recorded, and the
manifest's embedded case text stays the file as it was read. The frozen v1 field tree and the map
from it to v2 are held as test data, so VER-47 can hold the upgrade to them in both directions.

NOTE (the v2 keys that change a number; **added 24 September 2026**): `charge.exclusion_offset_nm`
and `charge.dielectric_transition_nm` are the fitted exclusion offset of FR-15 and the width of
PHY-20's transition to `ε_w`. Both SHALL be non-negative, and both are switches whose validated
default is `0`: the validated model has no exclusion shell and a sharp material permittivity (PHY-20
NOTEs). A non-zero value is therefore a deviation that the FR-25 manifest records. When the
`charge:` block is absent, each reads as its validated default. `numerics.mesh.size_scale`, default
`1`, SHALL multiply every element-size target of §5.2.2 and NUM-30, the resolved `wall_h_nm`
included. It exists so that a mesh-convergence study (RSK-09, §6.8) is a sweep over a case-file
field (FR-24) rather than a code edit. It is a discretisation choice recorded with the mesh, not a
deviation. With a supplied `inputs.mesh` a value other than `1` would be a knob with no effect, so
it SHALL be refused.

NOTE (`inputs:`, FR-27): the optional top-level `inputs:` block is hand substitution (FR-27) applied
at stage granularity. Each key names a stage output supplied from outside — a mesh, a charge field,
a dielectric field — by path and format. A stage whose output is supplied does not run, and neither
does anything upstream of it; the substituted file is hashed by content and enters the FR-25
manifest as an input like any other. Releases before v0.9 accept an externally generated mesh
this way, which is what makes the solver core testable ahead of the meshing pipeline (§8.1).
`inputs.profile` supplies stage 4's conditioned polyline as a `nanopnp/profile/v1` document
(`format: profile1`), which is how a hand-edited contour enters a run (§8.1, GUI increment 2), and
`inputs.pqr` supplies the per-atom charges and radii of stage 7's PDB2PQR step (`format: pqr`). The
two chains are structure → density → profile → mesh and structure → PQR → charge field, and the
dielectric field comes from the density (FR-15). Supplying an artefact together with one downstream
of it on the same chain SHALL be refused, naming both. The upstream one would be hashed into the
manifest as an input to a run that never read it. Until the stage that consumes a supplied
artefact is delivered, the case is refused as an unsupported section, naming that stage.
`inputs.profile` is consumed by stage 5 (**added 26 September 2026**, WP21). It is named by `path`
with `format: profile1`, and `artefact:` or `groups` beside it is refused. The profile is
hashed by the canonical digest of its validated payload. `structure:` beside it is refused naming
both, by the upstream rule, and so are `geometry.density` and `geometry.contour` where the document
writes them; `geometry.membrane` and `geometry.reservoir` are read.

NOTE (`structure:`, stage 1, FR-01 to FR-03, IF-04; **added 25 September 2026**, WP18):
`source.path` names a PDB or mmCIF file, optionally gzipped. MDAnalysis reads PDB and gemmi reads
mmCIF. `source.selection` is an MDAnalysis selection applied to the file, and one MDAnalysis cannot
parse SHALL be refused naming the key. The selected atoms are those of the selection in the chains
`source.chains` lists. Every selected atom SHALL
carry its element in the file, in the PDB element columns or the mmCIF `type_symbol`, and a file
that leaves one blank SHALL be refused naming the atom: a guessed element is how a Cα becomes
calcium. A selection carrying alternate locations SHALL be refused naming the first, because
choosing between them is structure preparation, which the pipeline does not do. A trajectory that
does not hold the structure's atoms, and an mmCIF model that does not list model 1's atoms in model
1's order, SHALL be refused naming the file (**clarified 25 September 2026**, WP18 review).

A chain is identified by its chain identifier, or by its segment identifier where the chain column
is blank. `source.chains` is `all` or a comma-separated list of chain identifiers, such as
`A,B,C`, which SHALL number `n` (a string, so the key's type is unchanged: **clarified 25 September
2026**, WP18). `symmetry.point_group` is `C<n>`
with `n ≥ 1`, and any other group SHALL be refused naming the accepted form. The selected chains
SHALL number exactly `n`, and a listed chain that is absent SHALL be named (FR-03). Each chain SHALL
carry at least half the Cα atoms of the most complete chain. Chains SHALL agree in residue name at
every residue number they share, with the histidine protonation variants read as one name. A
failure of either SHALL be refused naming the chain.

The ensemble is the frames of `ensemble.trajectory` when one is given, and otherwise the models of
the source file. `frames.last_ns` keeps the frames within that many nanoseconds of the last one, by
the times the file records. A value exceeding the recorded span by more than one frame interval
SHALL be refused naming the span and the interval. A file written without a timestep reads as 1 ps
or 0 ps per frame, and without this refusal it would yield the whole trajectory in silence.
`frames.count` keeps `count` frames at the uniform stride `⌊N/count⌋`, ending on the last frame of
the window of `N` frames. A count exceeding the window SHALL be refused naming both. The selected
frame indices and their times are recorded as read. Every selected frame is superposed on the Cα
set of the earliest selected frame (FR-01).

`symmetry.axis: auto` takes the Cₙ axis from the ensemble-mean Cα structure by chain-permutation
superposition (FR-02). The chains are ordered by azimuth, and the whole assembly is superposed on
itself with each chain mapped to its neighbour. The axis is that rotation's eigenvector of
eigenvalue 1, through the Cα centroid. It SHALL refuse the point group, naming the measured
quantity, when the chains' azimuths are not spaced 360°/n to within a quarter of that spacing, or
when the rotation angle differs from 360°/n by more than 1°. It SHALL refuse `C1`, which has no
permutation to superpose.

The axis carries no sign of its own. It is signed to agree with the file's +z, so the structure
file SHALL point +z from the *trans* side to the *cis* side. A detected axis more than 10° from the
file's z SHALL be refused, naming the angle, because such a frame does not name an end.
`symmetry.axis: z` takes the file's z axis through its origin. Where `n ≥ 2`, it SHALL be refused
when its lateral displacement from the detected axis exceeds 0.01 nm anywhere over the Cα axial
extent, naming the tilt, the offset and the displacement. The detected axis it is measured
against passes the spacing, angle and orientation refusals above first.

The aligned frame puts the axis on z at r = 0 and keeps the file's axial coordinate, `z = â · x`. So
`geometry.membrane.centre_z_nm` is read in the frame it is written in, and stage 5 applies that
shift. The four thresholds above are constants of the code and never case keys. Their derivation
and the margins measured on the author's aligned copy of 2WCD, on 6MRT and on the ClyA-AS ensemble
are in the WP18 plan, Design §2–§4. The wwPDB entry 2WCD as deposited is not such a file: its
asymmetric unit holds two dodecamers, chains A–L and M–X, in the crystal frame, with the pore axis
22.9° from z and +z towards *trans*, so it SHALL be refused by the 10° rule like any other file. Its
chains A–L are the author's copy moved rigidly (RMSD 1e-4 nm), and moving them is structure
preparation (WP18 Outcomes, **added 25 September 2026**).
Until stage 2 is delivered, a walk that extends past stage 1 on a case carrying `structure:` SHALL be
refused as an unsupported section naming stage 2. Once stages 2 and 3 are delivered, and until
stage 4 is, a walk that extends past stage 3 SHALL be refused in the same way, naming stage 4
(**added 25 September 2026**, WP19). Once stage 4 is delivered, and until stage 5 is, a walk that
extends past stage 4 SHALL be refused naming stage 5 (**added 26 September 2026**, WP20). With
stages 5 and 6 delivered, a walk runs the whole pipeline and no stage is refused on this ground
(**added 26 September 2026**, WP21). Stage 1
alone runs through the stage command (IF-02). A case carrying `structure:` and `inputs.mesh` SHALL be refused naming both: a stage whose
output is supplied does not run, and neither does anything upstream of it (the `inputs:` NOTE), so
the structure would be recorded as an input to a run that never read it (**added 25 September
2026**, WP18).

NOTE (`geometry.density`, stages 2 and 3, FR-04 to FR-06, CON-04, IF-05; **added 25 September
2026**, WP19): the `geometry:` block is read on a case carrying `structure:`. Beside `inputs.mesh`
it SHALL be refused naming both, by the upstream rule of the `inputs:` NOTE. `grid_spacing_nm`
SHALL lie in [0.025, 0.05] nm (FR-04) and `sharpness` SHALL be finite and positive, and each is refused naming
its value rather than narrowed in the schema.

`kernel: gaussian_vdw` takes each atom's width as `σ R_i`, with σ the `sharpness`. R_i is the
atom's CHARMM van der Waals radius (Rmin/2) by residue and atom name, from the radius set of
PDB2PQR's `CHARMM.DAT`, held as data under `data/radii/`. This is an **author ruling of 25
September 2026**: it is the set carried by the per-frame PQR files of the reference ensemble
(`.knowledge/04` §1.1). The histidine names `HID`, `HIE` and `HIP` read as CHARMM's `HSD`, `HSE`
and `HSP`. `HIS` resolves only where every one of those three that names the atom gives the same
radius. `ILE CD1` reads as `CD`, `OXT` as `OT2`,
and terminal atoms resolve through the patch residues. An atom the set does not name SHALL be
refused, naming its chain, residue number, residue and atom. There is no fallback by element: a
guessed radius is a plausible wrong geometry. Which atoms are deposited, hydrogens included, is
`structure.source.selection`'s to decide, and the count of each element is recorded.

Each frame's density is the probabilistic union `ρ_f = 1 − Π_i (1 − g_i)` over that frame's atoms,
with `g_i = exp(−d_i²/(σR_i)²)`. A term is kept where `g_i ≥ 10⁻⁶`. The ensemble map is the mean
of the per-frame maps, not a union over frames. Grid nodes lie at integer multiples of the spacing
in the stage-1 frame, so the axis is a column of nodes. The grid is square in (x, y) about the
axis and holds every kept term with one cell to spare. The map SHALL be finite and within [0, 1],
or the run aborts naming the voxel (QR-12).

Stage 3 bins the map in (r, z) at `r_j = j·h`, each bin being the annulus of half-width h/2 about
r_j. Its weights are the exact areas of overlap between each grid cell and each annulus, so an
annulus's weights sum to its exact area, and each nonzero cell's to the cell's area. No bin is
interpolated. FR-05's average over the n rotated copies SHALL be taken in the angular harmonic
basis. There a rotation by α multiplies the m-th coefficient by `e^{−imα}`, so the average keeps
exactly the harmonics with m ≡ 0 (mod n). The averaged map's azimuthal mean is then the map's own,
and its azimuthal variance is `2Σ_{k≥1}|c_{kn}|²`. Both are computed from the unrotated map, with
neither rotated deposition nor interpolation. That variance is FR-06's residual azimuthal variance.
It SHALL be computed after the binned mean profile, interpolated at each cell's own radius, is
subtracted, because otherwise the radial gradient across a bin reads as azimuthal variation. It
uses only harmonics below the ring's sampling limit `π r_j/h`. Below `r = n h/π` no harmonic is
resolved, and the artefact records that radius and each bin's harmonic count rather than
presenting a measured zero. The variance of the map without the Cₙ average is reported beside it,
and their difference is the part of the azimuthal variation that is not Cₙ-symmetric. Neither is
gated: RSK-07 makes the variance a validity criterion to be documented, and no threshold is
specified. The derivations and measurements are in the WP19 plan, Design §1–§4.

NOTE (`geometry.contour`, stage 4, FR-07, FR-08; **added 26 September 2026**, WP20): `isolevel`
SHALL be finite and lie in (0, 1). `simplify_tol_nm` SHALL be finite, positive and below the
density grid spacing h, because a larger tolerance discards resolved geometry and breaks the margin
of the §5.2.1 NOTE on the contour's size target. Each is refused naming its value, and the second
names h as well. `smoothing` is `taubin` or `none`. No other contour parameter and no gate
threshold is a case key: they are the constants of §5.2.1, and they key the stage-4 artefact.
Stage 4 emits a `nanopnp/profile/v1` document with `provenance.source: pipeline`, and its `sha256`
is the digest of the stage-3 payload it was drawn from. The loop runs clockwise from its lowest
vertex and stays in the stage-1 frame, so stage 5 applies `geometry.membrane.centre_z_nm` to it
exactly as to a supplied profile. The document read back through `inputs.profile` is a supplied
profile (the §5.2.1 NOTE on a supplied fixture). The conditioning and gate records belong to the
stage-4 artefact, not to the document, so a hand edit cannot carry a stale one.

NOTE (`inputs.charge`, `inputs.eps_r`, IF-05, IF-03): a supplied field is named by a
pydantic-validated header document, `schema: nanopnp/field/v1`, which carries the `quantity`, its
units, the grid descriptor (origin, spacing, shape), the axis cutoff of PHY-18 (default 0.01 nm),
the declared `Q_net` where the producer knows one, the provenance of the file, and the data file it
refers to. `format: field1` names that document; the *data* format is read from it, `.npz` on the
default path, OpenDX or CCP4 through GridDataFormats, which SHALL remain optional, and
`comsolgrid` — the reference model's own `%Grid`/`%Data` interpolation table, in metres, **read
only**, since it is an input to the reference rather than an output of ours and writing it would
invite a round trip that is not one. A grid axis SHALL be uniform to round-off or the file SHALL
be refused naming the axis: the interpolant of PHY-19 takes a box and a shape, so a non-uniform
axis would otherwise be resampled onto a uniform one in silence. A header
document SHALL reject an unknown key naming the key, as every other schema in §5.3 does. `quantity`
is one of `areal_charge_density` (the reference's `rhoq_pore`, C m⁻²), `volume_charge_density`
(C m⁻³) or `solid_fraction` (dimensionless), and the `1/(2πr)` projection and the axis guard of
PHY-16 step 6 SHALL be applied to `areal_charge_density` **only** — applying them twice, or not at
all, is invisible in the conservation check of PHY-19, for the reason given there. The interpolant
SHALL be zero outside the grid box rather than continued by its edge value, and a grid whose
boundary values are not negligible against its interior SHALL be refused rather than truncated
silently. An `inputs.eps_r` field SHALL supply a solid fraction, not an absolute `ε_r`: see §4.4.

NOTE (`inputs.mesh.groups`, IF-06, QR-12): the mapping reads **file group name → vocabulary name**.
The key is the physical-group name the mesh file carries; the value is the name the solver selects
on. Several file groups MAY map to one vocabulary name — a CAD export routinely splits one physical
wall into several curves — and the reverse is not expressible, which is why the direction is this
way round. The vocabulary is fixed and carries no aliases: materials `electrolyte`, `cis`, `trans`,
`protein`, `membrane`, `analyte`, `exclusion`; boundaries `axis`, `wall`, `membrane`,
`membrane_outer`, `cis`, `trans`, `analyte`, `interface`. `protein` is the pore's dielectric body (§2.2), a solid domain
Poisson is solved on and Nernst–Planck and the flow are not; `pore` is deliberately **not** a name,
because it reads as both that body and the lumen fluid, and a mesh that uses it SHALL disambiguate
through the mapping. `interface` is the interior fluid-to-fluid seam a fragmented region carries —
the pore-mouth interfaces the reservoir-to-lumen split leaves behind — and **nothing selects on it**;
it is in the vocabulary because every group must be claimed by some name, and calling an interior
seam `wall` would put it in the PHY-02 distance source set and impose no-slip across the middle of
the electrolyte. `exclusion` is the ion-exclusion region of FR-15 — the shell between the dielectric
contour and the exclusion contour, offset outward by the hydrated-ion radius. It is a solid for
Nernst–Planck and for the flow, so the no-slip surface sits at the outer edge of the shell, which is
the conventional hydrodynamic shear plane; it takes the **fluid's** `ε_r` for Poisson, so
`physics.solid_permittivities` SHALL NOT require an entry for it and SHALL NOT abort on its absence.
ePNP-NS carries no explicit Stern layer, so a mesh presenting this material is a deviation from the
validated model and SHALL be recorded as one in the run provenance (FR-25), even though no case-file
switch selects it. Ingestion SHALL abort when any group in the file is left unclaimed by the mapping,
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
ingested mesh's material names were not written by this codebase. A mesh stage 6 generates from a
profile is gated as an ingested one is: its `protein` is a structure's body, not a benchmark's, and
the same wrong answer follows from a missing entry (**added 26 September 2026**, WP21). Rationale: boundary conditions are selected by name and the natural condition under the
`r`-weighted forms is the *free* one (§6.2, NUM-06), so an unmapped wall becomes an open boundary,
the solve converges, and the current is wrong with no residual, no gate and no diagnostic.

NOTE (`geometry.membrane`, `geometry.reservoir`, `numerics.mesh`; stages 5 and 6, FR-09, FR-10,
NUM-30; **added 26 September 2026**, WP21): `membrane.thickness_nm`, `reservoir.radius_nm` and an
explicit `wall_h_nm` SHALL each be finite and positive, and each is refused naming its value.
Stage 5 applies `membrane.centre_z_nm` as `z ← z − centre_z_nm` and gates the junction as the
§5.2.1 NOTE on the membrane junction on any profile says. `wall_h_nm: auto` resolves to
`size_scale × min(0.05 nm, λ_D/5)`. λ_D is §6.3's `√(ε₀ ε_r,f⁰ RT / (2F² I))`, with `ε_r,f⁰`
from `electrolyte.parameters`, the case's temperature and the ionic strength I of the bulk species.
The 0.05 nm ceiling is §5.2.2's pore-boundary maximum, which the validated reference applied at
every concentration. It governs below 1.474 M, and above that NUM-30's target is finer and governs.
`ε_r,f⁰` is used rather than the concentration-corrected permittivity, so the mesh does not move
when the permittivity correction is switched. An explicit value is used as written, times
`size_scale`. A resolved wall size coarser than λ_D/5 is logged and recorded in the manifest, not
refused: it is a discretisation choice, and a mesh-convergence study needs coarse meshes. §5.2.2's
other sizes are each multiplied by `size_scale`. After meshing, the mean length of the `wall`
boundary segments SHALL NOT exceed 1.15 × the resolved wall size, and the longest SHALL NOT exceed
2.0 ×, or the run aborts naming the statistic, the segment and its midpoint (QR-12). Netgen treats
the size as a target, and 1.045–1.078 and 1.25–1.62 are the measured means and maxima (WP21 plan,
Design §3). `backend: gmsh` is refused until the Gmsh adapter is delivered (WP23, ADR-002), and
`boundary_layer: true` naming FR-11. `geometry.analyte` on a generated mesh is refused naming FR-21.
Beside `inputs.mesh`, any `numerics.mesh` key away from its default is refused naming it, because
nothing meshes and the key would change nothing.

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

NOTE (`numerics.elements`, NUM-03): `phi` and `c_i` carry one element order; `u` is independent of
them and `p` is independent of both, so the reference implementation's own discretisation —
quadratic `phi` and `c_i` with linear `u` and `p` — is expressible. An order for `u` at or below
the order of `p` SHALL be refused unless `numerics.stabilisation` selects a mode supplying the flow
stabilisation of §6.4.2, and the refusal SHALL name both the inf-sup condition and the mode that
would permit the pair. All three orders are recorded in the run provenance record (NUM-03).

NOTE (`numerics.stabilisation`, and the compatibility rule for the case schema): the value set is
`none | supg | reference`. `none` is the validated default and the production policy of NUM-11;
`supg` is NUM-11's flag, the streamline term alone; `reference` is the mode of NUM-14, streamline
and crosswind on the transport operator together with the flow stabilisation of §6.4.2, and is the
only value permitting an equal-order velocity–pressure pair. More generally: **widening the accepted
value set of an existing key is compatible and SHALL NOT move the schema version, because every
document that validated before still validates; adding, removing, renaming or narrowing a key SHALL
move it.** The mode a run actually solved is in its FR-25 manifest, so no artefact of an earlier
revision becomes ambiguous under a widening.

NOTE (`numerics.wall_distance`): `sources` is the boundary-name pattern the PHY-02 distance field
`d` is measured from, and its validated default is the pore wall alone. PHY-02 excludes the
membrane from the source set deliberately, so widening `sources` is a deviation from the validated
model and SHALL be recorded in the run provenance (FR-25). `max_distance_nm` is the saturation
distance beyond which the wall functions are 1 to within round-off.

NOTE (`walls`): the wall values name the condition applied, not its absence. `ion_flux` takes
`no_flux | prescribed` and `slip` takes `no_slip | navier | free`. Under the `r`-weighted forms of
§6.2 the natural condition is the free one, so a value reading as "none applied" would silently
remove no-slip while appearing to be the validated default.

NOTE (`outputs:`): the list selects what the run produces, and each word is refused rather than
silently ignored where it cannot be met. `current`, `transport_numbers` and `eof_rate` select scalar
quantities of interest (§6.7). `fields` gates the IF-07 field export, which is off unless asked for:
the export is of order ten megabytes per solve and an envelope sweep of thousands of points would
otherwise write tens of gigabytes nobody requested. `analyte_force` requires the mesh to carry an
`analyte` material, and a case asking for it on a mesh without one SHALL abort naming the missing
material (QR-12). `rectification` is a two-point quantity, `I(+V)/I(−V)`; a case asking for it at a
single operating point SHALL be refused naming it as such, because the second bias can only come
from a sweep (FR-24) and inventing one would report a ratio the run did not measure. A sweep
(§5.3.4) SHALL therefore strip `rectification` from each member's `outputs:` and produce it in
collection, from pairs of members whose case-file assignments are equal except at
`boundary_conditions.bias_V` and whose two biases are exactly opposite. Exactly, not approximately:
a tolerance on the pairing would report the ratio of two unrelated operating points as a
rectification. A sweep asking for `rectification` whose axes produce no such pair SHALL be refused
when the plan is built, naming the axis, rather than collecting a column of absent values (QR-12).

#### 5.3.2 Artefacts and interchange formats

| Stage | Artefact | Format |
|---|---|---|
| 1 | Aligned ensemble: coordinates in nm, atom table (element, name, residue name, number and insertion code, chain) and axis-transform record | Native `.npz` (float32 coordinates) with its header record; exported as a PDB topology with a DCD trajectory (IF-04). **Amended 25 September 2026** (WP18) from "trajectory plus transform record": a trajectory file carries no atom table and no gate record |
| 2, 3 | Density map (3D, float32), and the reduced (r, z) mean with its Cₙ-averaged and raw azimuthal variance | Native `.npz` with its header record; exported to, and read from, OpenDX or CCP4 via GridDataFormats (LGPL) (IF-05), the (r, z) grids as `RadialGrid`s with a singleton axis. **Amended 25 September 2026** (WP19) |
| 7 | ρ_pore, dielectric and exclusion fields | OpenDX or CCP4 via GridDataFormats (LGPL) (IF-05) |
| 4 | Conditioned polyline | `nanopnp/profile/v1` YAML: the vertex table with its provenance block (§5.2.1). The conditioning and gate record is in the artefact's summary. **Amended 26 September 2026** (WP20) |
| 5 | Tagged (r, z) region | `nanopnp/region/v1` YAML: a declarative record of the model-frame profile, the membrane with its derived inner edge, the reservoir and the tag counts, from which the OCC region is rebuilt deterministically. **Amended 26 September 2026** (WP21) from "OCC BRep plus tag map": a record hashes by content, where a BRep's bytes need not be stable |
| 6 | Mesh | Gmsh MSH 4.1 archival, any meshio (MIT) format on read (IF-06). A supplied mesh is keyed on its canonical contents; a generated one on its recipe, the stage-5 key and the resolved size fields, with its content hash recorded beside the key (**amended 26 September 2026**, WP21) |
| 8 | Resolved material coefficient set | Correction file references and evaluated parameters |
| 9 | Resolved case document | YAML, schema `nanopnp/case/v2` |
| 10 | Field set, iteration history | XDMF with HDF5 heavy data (IF-07) |
| 11, 12 | Scalar QoIs, profiles, figures, dataset, manifest | Result store record, figure files, manifest |
| — (a sweep, §5.3.4) | Collected dataset over the members of a sweep | Result store record, schema `nanopnp/sweep/v1` |

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
permits, and is recorded in the manifest as a substituted input rather than aborting the run. This
encoding is also the on-disk form of the manifest and the run record of §5.3.3, which are written
through it so that the file a reader sees and the bytes that were hashed cannot disagree; a decoder
for the float encoding SHALL therefore exist beside it, because a consumer comparing recorded
numbers against live ones otherwise compares two encodings and reads a present number as a missing
one.

NOTE (workspace locality): a run given an artefact store SHALL write every file it produces inside
that store, scratch included, and SHALL NOT fall back to the process-default store root for the
files a stage writes before its artefact is put away. FR-24's job array runs many members
concurrently, each with its own store; a member whose scratch mesh went to the process default
would leave the artefact and the file it points at in different stores, and QR-06 could not
attribute either to the member that produced it. The scratch directory is fresh per run rather than
named after the stage: two runs sharing a store hold different meshes, and a deterministic name
would have the second overwrite a file the first's artefact still references.

NOTE (solution payload, warm start): the stage-10 artefact's payload SHALL be a self-describing
coefficient record — one array per field component, together with the discrete wall-distance
coefficient vector and a descriptor — rather than a backend-native binary. The distance field is
*stored* and not recomputed on restore: a residual reassembled against a freshly solved distance
field is a different operator, so re-solving it would make a restored state depend on the machine
that restored it. The descriptor SHALL carry the mesh content hash, the ordered field names, each
field's element type, order, domain restriction and degree-of-freedom count, the physics model and
its options, the wall-distance sources and saturation distance, the stabilisation mode (§6.4) and
the digest of the case's *solve-relevant* provenance defined in the NOTE below; restore SHALL
compare it key by key and abort naming the first difference with both values (QR-12), never adapt.
That digest is deliberately not the case document's own hash: `name:` and `outputs:` move the
document hash and move no field, so a gate keyed on it would refuse a converged state to a run
differing only in what it intends to report — and would refuse precisely the stage-10 cache entry
the store had just served that run. A coefficient vector loaded into a space that differs in any of these
is silently a different function and there is no residual it would fail to reduce. Because the
payload is excluded from the content hash, a change to this payload contract is a change of artefact
*schema* and SHALL bump its version, or a stale cache entry would read as a hit whose payload the
loader cannot open.

NOTE (warm start from a neighbour, FR-24): the gate above is stated for reloading a run's *own*
converged state, where every descriptor key must match. A sweep warm-starts one operating point from
another, and two of those keys differ by construction — the solve-provenance digest carries the bias
and everything else that keys a solve, and the model record carries the §6.3 scale set, which is a
function of the concentration. The descriptor's keys SHALL therefore be partitioned into those that
determine the **space** — the mesh, the ordered field record with each field's element, order,
domain restriction and degree count, the total degree count, the boundary sets that fix which degrees
of freedom are constrained, the declared field set, and the NUM-02 variable branch — and those that
determine the **operator**. A warm-start load SHALL gate the space keys exactly as a restore does and
SHALL record every operator key that differed; it SHALL NOT read the stored wall-distance vector,
the operator being assembled belonging to the target run. The NUM-02 branch is in the first set
because a log-variable model and a primitive one declare the same field names at the same order with
the same degree count and mean different things by them, so no shape test would catch the confusion.
The partition SHALL be enumerated in both directions against the descriptor a solve actually
produces, so that a key added later fails verification rather than silently becoming ungated.

The warm-start source SHALL be recorded in the run provenance (FR-25) and SHALL NOT enter the
stage-10 artefact key. Two members differing only in where Newton started must key one artefact, or
the store would hold two entries for one converged state and the QR-08 reproduction would compare a
warm result against a cold key. That is admissible only because it is *asserted*: a converged state
that depended on its starting point is a defect, and the verification of FR-24 measures the
difference between the warm and cold paths rather than assuming it away.

NOTE (what keys a solve): the parameters of the stage-10 artefact SHALL be the resolved case's
provenance restricted to what can change a converged field. The case's `name:` and its `outputs:`
selection are excluded: neither reaches the mesh, the operator or the boundary data, and a key
carrying them re-solves a converged case because the run asked for one more quantity to be
reported — on the reference pore, minutes of work discarded for a question about post-processing.
Both remain in the §5.3.3 manifest, which records what was asked for and not only what was
computed, and both remain in the stage-11 key, where `outputs:` does change the artefact. The
`schema:` string is excluded for the same reason (**added 24 September 2026**): a v1 document and its
lossless v2 upgrade describe one run (§5.3.1), and a key that told them apart would re-solve every
converged case in a store because the loader, not the case, had changed. The v1 key **did** carry
the string, so this exclusion moved the stage-10 key, the VER-34 restore digest and the Tier-3 case
identity of every v1 case once, at the move to v2 (**author ruling, 24 September 2026**, correcting
WP17 D6, which had assumed the three would survive): a solve stored under a v1 key is a miss and
re-solves once, and a golden declaring a v1 `case_hash` is refused naming both hashes. The stage-8
materials key never carried the schema and survives. The exclusion is what makes this the last move
of the schema to re-key a solve.

NOTE (QR-08, reproduction): the check that a run reproduces its scalar quantities of interest from
its manifest SHALL re-enter the solve rather than be served from the artefact store. Run against a
populated store the check reduces to a dictionary lookup and asserts nothing; it is therefore
performed against a fresh store, with the store miss and the re-entry into the nonlinear solve
themselves asserted. The agreement required is the nonlinear relative tolerance of §5.3.1
(`1 × 10⁻⁶`), and the *measured* difference is reported alongside the verdict, so that the figure
across operating systems is on the record rather than inferred from a pass. The check SHALL be
reachable as a command over a run directory and not only as a test: a promise only the project's own
test harness can exercise is not one a user holding an archived result can rely on. Drift in an
*input* is fatal and names the file, a reproduction against moved contents being a different
calculation reported as the same one; drift in a recorded library version is reported and not fatal
unless the caller asks for a strict environment, because a version that moved a number is caught by
the quantity comparison, which is the assertion that matters.

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
| Stabilisation | The stabilisation mode that produced the number, its tuning parameters and the provenance of each, and — where a mode is active — its own contribution to the current and the largest cell Péclet number per species (§6.4, NUM-12, NUM-13) |
| Deviations | Every switch set away from the validated default, including `dielectric_gradient_forces` (PHY-23) |

#### 5.3.4 Sweep specification and dataset

A sweep (FR-24) is a set of runs, not a pipeline stage: it produces no field, and a stage keyed on
thousands of upstream artefacts has no meaningful key. It is specified by its own declarative
document, `schema: nanopnp/sweep/v1`, which names a base case by path and the axes to vary. Nothing
is added to the case schema for it: a sweep block inside a case would make that case's
content hash — and every artefact key derived from it — a function of a sweep the run does not
perform.

An **axis** is a named, ordered list of **assignments**, an assignment being a mapping of dotted
case-file paths to values; an axis varying one path may be written as a path and a list of values.
Axes combine as a Cartesian product in declaration order. Each axis MAY declare the index of its
**origin**, defaulting to its first value. A dotted path SHALL be validated against the case schema's
own field tree before any substitution, refusing an unknown component by naming it and the prefix
that does exist, and a value whose type the schema does not accept SHALL be refused there too.
Substitution SHALL re-validate the whole document, so that a path which resolves but produces an
inadmissible case is refused by the same diagnostic a hand-written case would receive (IF-03). Every
point SHALL be substituted, validated and resolved when the plan is built, before any solve: a plan
whose two-thousandth point is inadmissible must fail in seconds rather than after a day of compute.

A point's **identity** is the content hash of its assignment mapping; its **index** is its position
in the plan. The identity keys the collected dataset and the index keys the dispatch, because
inserting one value on one axis renumbers every index after it and a dataset keyed on the index would
relabel results the sweep did not re-run. A member's `name:` SHALL carry its point identity, `name`
reaching the manifest and the run directory and nothing that keys a solve.

Warm starting and independent dispatch are reconciled by a **forest** over the axis grid. The parent
of a point is that point with the last index differing from its axis origin moved one step towards
it; every point therefore has exactly one parent one grid step away, the depth of a point is the sum
of its index distances from the origins, and all points at one depth are mutually independent. A plan
SHALL order its points by depth, so that each wave is a contiguous range of indices a job array can
be submitted over. A member whose parent's stage-10 artefact is not in the store SHALL run the full
NUM-18 ladder and SHALL record that it did, with the reason: a member must be runnable alone, in any
order, on a machine that has seen nothing else, and the warm start is an optimisation the store may
or may not be able to supply.

Members SHALL share one artefact store, which is what makes a neighbour's converged state reachable
at all, and the workspace-locality NOTE above applies to each member individually. Independent
workers SHALL be independent: each worker SHALL be started with the thread counts of the underlying
linear-algebra libraries pinned to one before those libraries are imported, and the pinning SHALL be
recorded, because N workers sharing one thread pool are not N independent workers and QR-06's scaling
claim would otherwise measure the pool.

The collected **dataset** is an artefact, `schema: nanopnp/sweep/v1`, written through the canonical
serialisation above, carrying one record per point: its index and identity, its assignments, its
status and — where it failed — the exit class of §3.1, the scalar quantities of interest or their
explicit absence, the run directory, the manifest and solution hashes, the elapsed time, whether it
was served from cache, and the warm-start record. The quantities of a member that did not succeed
SHALL be absent rather than defaulted, QR-06 requiring that a failed member be distinguishable from a
refused one and from one that was never dispatched. A flat tabular export MAY be written beside it
and is derived rather than normative.

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
responsive and can show live convergence. Packaged with PyInstaller, briefcase or
conda-constructor. The graphical surface grows from Phase 1 onward.

| Alternative | Assessment |
|---|---|
| PyQt6 shell | Rejected: GPL-3 only |
| Local web application: FastAPI plus browser frontend wrapped in `pywebview` | **Rejected, 20 September 2026**, closing the deferral below. The stage interface did stay clean — `run_case` takes a `Progress` callback and a `CancelToken`, and every stage is introspectable without importing it (FR-27) — so the alternative remained available and was declined on its own merits: it buys a hosted future and an SSH port-forward this project has no requirement for, and pays in a second rendering path for the same webgui scene. Originally recorded as "on the table… the choice may wait until Phase 1", which is where it was made |
| Defer the interface to a terminal phase | Rejected on two failure modes: an interface bolted on at the end exposes the API's accidental structure rather than the user's workflow, and a nine-month gap before any non-programmer touches the tool is a nine-month gap in shaping feedback |

NOTE (packaging, amended 20 September 2026). The redistributable bundle SHALL be built one-**dir**
rather than one-file, for two independent reasons. PySide6 and Qt are used under the LGPL option
(CON-09), which requires that a recipient be able to replace the covered libraries; a directory of
shared libraries satisfies that plainly. And Qt WebEngine runs a separate helper executable, which a
one-file extractor must locate at runtime inside a temporary directory. The bundle SHALL carry the
licence notice CON-11 requires, stating that the bundle as a whole is distributed under GPL-2+
because its default linear solver is, while the library itself remains BSD-3. The background solver
process SHALL be started with the `spawn` start method: it is the only one Windows has, and a forked
child would inherit both the parent's Qt event loop and its already-imported numerical libraries.

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

NOTE (which `Pe_h`): the form printed above assumes the Einstein relation, `μ_i = D_i/V_T`, which
PHY-14 and VER-05 forbid at finite concentration — `D` and `μ` carry different concentration
corrections and `D_i/μ_i` drifts to 1.2–1.7 × kT/e between 0.15 M and 3 M. The implementation SHALL
therefore evaluate the cell Péclet as `Pe_K = ‖b_i‖ h_K / (2 D_i)` on the advective velocity it
actually assembles, `b_i = z_i μ_i ∇φ̃ + D_i β_i − Pe u`, and SHALL record which expression produced
the number. The printed form is the `c → 0` limit of that one and overestimates it by
`D_i/(μ_i V_T)`, so it errs towards warning early rather than late.

NOTE (when): there is no `∇φ̃` before a solve, so "on the assembled mesh" means on that mesh's
converged state. The evaluation SHALL run in every stabilisation mode, `none` included: a diagnostic
that runs only when the stabilisation is on is a diagnostic that never runs in production.

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

NOTE (what the reference's setting names are taken to mean): COMSOL exports none of
`tds.streamline`, `tds.crosswind`, `spf.streamlinens` or `spf.crosswindns`, so the mode above
reproduces the reference's *settings* and not its operator, and the difference between the two is an
irreducible systematic in any §7.4 comparison, bounded only by mesh refinement. Three readings are
therefore fixed here rather than left to the implementation.

- **Approximate residual** means every second derivative of a trial field is dropped from the
  residual the stabilisation is built on, leaving the advective residual and its sources. The
  streamline term is then inconsistent by construction — its residual does not vanish on the exact
  solution — and the resulting loss of one order in the L² convergence rate of VER-18 is a property
  of the mode rather than a defect, and SHALL be measured and reported rather than assumed away.
- **Crosswind diffusion, Do Carmo and Galeão** means a term of that family: residual-scaled, acting
  across the streamline, and vanishing identically where the element Péclet number is at or below
  the reciprocal of its tuning constant. On a mesh meeting NUM-30 that condition holds everywhere, so
  the term SHALL be verified on a mesh coarse enough to activate it, and the fraction of elements on
  which it is active SHALL be reported with any comparison that relies on the mode.
- **Convective term in conservative form** costs nothing to match: the Nernst–Planck weak form of
  NUM-04 is already the divergence form integrated by parts.
- **The flow row's equation residual is not recorded in the report**, so the approximation above is
  applied to the momentum residual on the same rule, and that choice is this project's rather than
  the reference's. Its cost SHALL be measured and reported rather than assumed: on a stable
  (Taylor–Hood) velocity–pressure pair the flow terms are **not** asymptotically inert, and the
  resulting loss is one further order in L² — the mode converges at first order where the transport
  stabilisation alone converges at second. The reference ran its flow stabilisation on an equal-order
  pair (RSK-18), where it is what makes the pair admissible at all, so no configuration the reference
  itself ran is affected. A §7.4 comparison that pairs this mode with a stable element pair SHALL
  record that its residual is dominated by the flow terms rather than by the transport ones.

NOTE (the zero-wind linearisation): every magnitude the mode takes of a vector SHALL be floored
inside the square root. The parameters are evaluated at the iterate, so their derivative with
respect to the trial functions is structurally zero — but a backend that evaluates
`d/du ‖g‖ = (g · ∂g/∂u)/‖g‖` numerically rather than folding that zero away returns `0/0` wherever
`g` vanishes identically, and the assembled Jacobian is then singular with no diagnostic naming a
stabilisation term. `b̃_i = 0` exactly is the converged state of every rung of the NUM-18 ladder
below stage 4, so this is the ordinary path and not a corner of the envelope. The floor SHALL be
small enough to be invisible against any magnitude a solve produces, and the property SHALL be
verified on the assembled Jacobian and not on the residual, which is finite there in every mode
(VER-41).

**NUM-15.** In the mode of NUM-14 the crosswind term SHALL be assembled at integration order 6 and
the streamline term at integration order 4.

NOTE: "at integration order *n*" SHALL be read as a lower bound. The quadrature order reaching the
finite-element backend is a bonus added to an integrand-dependent estimate rather than an absolute
setting, so an implementation SHALL request a bonus of *n*, which guarantees at least order *n*.
Overshoot costs quadrature points and not correctness, which is the same trade NUM-07 already makes.

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

NOTE (FR-24, a member warm-started from a neighbour): a sweep member that starts from the converged
state of a neighbouring operating point SHALL solve the target rung alone rather than re-climbing the
ladder. That is not a departure from the fixed path above but stage 9 of it — the salt sweep, whose
rungs are warm starts one step apart — generalised to the other axes of the envelope, and re-solving
the nine rungs below a converged neighbour would re-derive the answer the neighbour already is. The
provenance manifest SHALL record the rungs actually run and the artefact hash of the state the member
started from, and a member whose neighbour is unavailable SHALL take the full ladder and record that
it did, so that a sweep's timings say which members paid for what.

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

NOTE (a stabilised mode, NUM-14): under a stabilisation mode the functional above SHALL carry the
stabilisation form of the species evaluated with `ψ` as its test function, in addition to
`∫ J_i·∇ψ r dr dz`. The NUM-26 identity below is an identity between two evaluations of *the
assembled residual*, and in a stabilised mode the assembled residual contains that term; omitting it
from this route alone would make the two routes differ by exactly the quantity the mode exists to
measure, failing NUM-26 on every stabilised solve for the one reason that is not a defect. The
difference the term makes SHALL be reported per species as the stabilisation's contribution to the
current, which is NUM-11's "SUPG biases the current quantity of interest" turned into a number from a
single run rather than from a difference of two.

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

NOTE (the wall target and its ceiling; **added 26 September 2026**, WP21): `h₁` is resolved as
`min(0.05 nm, λ_D/5)`, so the table's 0.27 nm at 0.05 M is never used. It would be coarser than the
ion wall function's decay length, 1/6.2 = 0.161 nm, and than stage 4's contour resolution, and
five times the validated reference's pore-boundary size. λ_D is taken at `ε_r,f⁰`, as are the
values above. The §5.3.1 NOTE on `numerics.mesh` is the contract.

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

**NUM-34.** Where any wall correction is active, the discrete wall-distance field of NUM-31 — as the
corrections read it, after mollification where the smoothing pass is applied — SHALL satisfy
`min d̄ ≥ −1 × 10⁻³ nm` over the fluid domain. A field violating it SHALL abort the run with the
QR-12 diagnostic naming the gate, the measured minimum, its location and the fraction of samples
below zero, and the measured minimum SHALL be recorded in the provenance manifest. A configuration
activating no wall correction reads no distance field and SHALL NOT be gated.

Rationale: the threshold is bounded on both sides and chosen between them. It cannot be zero,
because interpolating the field projects element-wise and leaves an interior residual of a few times
`10⁻⁴` nm whose sign is platform-dependent, so a gate at zero would gate the rounding mode. It
cannot be `10⁻²` nm, which is the ion wall function's own root `−P₂`: a gate there admits a
diffusivity of exactly zero as its last passing state, and it would restate a fitted coefficient
outside the correction data. One order inside the root and one order outside the projection residual
leaves the PHY-02 clamp free to absorb round-off — worst effect `5.8 × 10⁻³` on a factor whose wall
value is `6.0 × 10⁻²` — while refusing a field that is genuinely negative. Such a field is
under-resolved at the wall rather than marginally inaccurate, which NUM-26's route disagreement
reports independently and which the measured transition confirms: the minimum steps from
`−9.6 × 10⁻¹` nm to `+7.9 × 10⁻³` nm across a single refinement, so this gate discriminates a regime
and does not shave a tolerance.

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

NOTE (Tier-3 reference files are named, not vendored): the archived golden files Tier 3 compares
against are too large to carry in the repository — the delivered ClyA charge table alone is 77 MB
of text — and no lossy reduction of one is a fair reference: cropping the ClyA table at a
`10⁻⁶` relative threshold still costs 28 MB, and subsampling it by four moves its planar integral
by 1.5 %, which is fifteen times QR-03's budget. The archive SHALL therefore be located by the
environment variable `NANOPNP_REFERENCE_DATA`, naming a directory of files by name, and a Tier-3
test whose file is absent SHALL **skip** rather than fail: Tier 3 is recorded and not gated, so an
unavailable reference is missing evidence, not a defect. Tier 1 and Tier 2 SHALL NOT read the
archive, so the push gate is unaffected by whether it is present.

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
| **VER-29** | External field ingestion and charge conservation | An (r, z) grid round-trips through the native format and through OpenDX and CCP4 with the singleton-axis convention, origin, spacing and values preserved, on every supported interpreter (the IF-05 NOTE of §3.1, **amended 24 September 2026**); a genuinely two-dimensional array is refused naming its shape; the interpolant's axis order is asserted against a field that is not symmetric in its arguments, so a transposed array fails rather than agreeing on the diagonal; the field is zero outside the grid box rather than continued by its edge value; on the deployed finite-element mesh `|Q_mesh − Q_net|/|Q_net| < 10⁻³`, reported as the producer and consumer legs of the §4.4 NOTE and gated separately, with the axis-guard deficit and the boundary-ring maximum reported beside them; the ramped per-plane cumulative agrees to the same tolerance at every plane; a grid whose boundary values are not negligible against its interior aborts naming the value and its (r, z); a field declaring no `Q_net` gates the consumer leg and records the producer leg as not run. The conservation half is asserted at Tier 2 on the reference mesh of §5.2.1, against a field whose `Q_net` is known in closed form, and a deliberately coarsened mesh there fails the quadrature-agreement gate rather than the conservation gate — which is the distinction the §4.4 NOTE makes normative (QR-03, PHY-18, PHY-19, IF-05, FR-14 in part) |
| **VER-30** | Dielectric blend | The sharp solid fraction reproduces PHY-20's piecewise assignment to round-off at every quadrature point; a `χ` outside [0, 1] and an inverted `χ` both abort with the offending quantity and its location, the latter on the per-material means; an absolute `ε_r` field is refused with the §4.4 NOTE named (FR-15) |
| **VER-32** | Command-line surface and exit-code contract | Every subcommand parses and dispatches to the stage objects it names; the registry is listed in a fresh process that imports no stage implementation module, no NGSolve and no netgen, asserted on `sys.modules`; each exit class of the §3.1 IF-02 NOTE is produced by an input that triggers it; every public exception type in the package is either classified by the exit-code enumeration or excluded from it with a written reason, in both directions, so that a type added later fails this test; diagnostics appear on standard error and standard output carries only the command's result; a gate abort prints its QR-12 diagnostic without a traceback unless one is requested; a run given a store writes every file it produces inside that store, asserted by running from a working directory the process-default fallback would land in and requiring it to stay empty; `mesh cylinder` and `mesh reference` write an MSH 4.1 file that a case using the `inputs.mesh.groups` mapping they print ingests through the VER-27 gate unchanged, the hash they print is the mesh hash that run's manifest records, a mesh failing the VER-10 quality gate is refused with its QR-12 diagnostic and exit class `4` and leaves no file behind, and `--help` on either imports no netgen (IF-02, FR-27, the §5.3.2 workspace-locality NOTE, the §3.1 IF-02 generators NOTE) |
| **VER-33** | Field export exactness and the Ω/Ω_w split | A quadratic exported and read back is reproduced *exactly* at all six nodes of every element, which a permutation of the midside nodes fails; the exported node count is `nv + nedge`; the two files carry the whole-domain and fluid-only field sets respectively and the fluid file contains no solid node; attribute names carry SI units and the values match the §6.3 scale conversion to round-off, with the `2π` of the axisymmetric measure absent; heavy data is compressed (IF-07) |
| **VER-34** | Solution-state round trip and descriptor gate | Save followed by restore reproduces every component's coefficients to zero difference; the stored wall-distance vector is restored rather than re-solved; a descriptor differing in the solve-provenance digest, mesh hash, element order, domain restriction, degree-of-freedom count, model options, wall-distance sources or saturation distance, or stabilisation mode each abort naming the key and both values; a payload of the superseded schema version is refused by schema rather than misread; a case differing only in `name:` or `outputs:` restores, and keys the same stage-10 artefact (FR-27, QR-08 in part) |
| **VER-36** | Sweep plan: substitution, validation and the warm-start forest | A product of axes enumerates the points of §5.3.4 in wave order; an assignment-valued axis moves several case-file paths together; a point identity is stable across processes and unchanged by a value inserted on another axis, while its index is not; every point has exactly one parent one grid step nearer its axis origin, its wave is its depth, and the points of one wave are pairwise independent; an axis rooted away from its first value walks outward in both directions; a misspelt path is refused naming the component and the prefix that exists, and a value of the wrong declared type is refused before any solve; a point the case schema resolves but §6.5 refuses fails when the plan is built, naming the point and the reason; a plan asking for `rectification` whose axes produce no exactly-opposite bias pair is refused naming the axis (FR-24, IF-03, QR-12) |
| **VER-37** | Warm start across a sweep step: the descriptor partition | Every leaf of the descriptor a real solve produces appears in exactly one of the space and operator sets, and every entry of both sets appears in the descriptor, in both directions; a warm-start load accepts a payload differing only in operator keys and records each of them; it aborts naming the key and both values on a differing mesh hash, degree count, field record, boundary set, variable branch or stabilisation mode; a payload of a superseded schema version is refused by schema; the loaded state carries no residual and does not read the stored wall-distance vector; and a point reached warm reproduces the same point solved cold to better than the `1 × 10⁻⁶` nonlinear relative tolerance, with the measured difference reported. The partition is verified at Tier 1, on the descriptor alone; the warm-against-cold agreement is a Tier 2 activity, needing a converged pair (FR-24, the §5.3.2 warm-start NOTE) |
| **VER-38** | Sweep dispatch and collection | A single-member dispatch exits with that member's own class for each of the case, gate, convergence and cancellation classes, and produces the same scalars run alone into an empty store as it does inside the sweep; a local multi-worker sweep exits `0` with a failed member present and nonzero under fail-fast; a member whose parent artefact is absent falls back to the full ladder and records the reason; the worker thread pinning is in place before the linear-algebra libraries are imported, asserted in a spawned process; the dataset round-trips to identical values, a failed member's quantities are absent rather than defaulted, and the rectification of an exactly-opposite bias pair equals the two-point ratio of §6.7 taken from the same two records. The dispatch and collection surface is verified at Tier 1; the equivalence of a member solved alone and the same member solved inside the sweep is a Tier 2 activity (FR-24, IF-02, FR-23) |
| **VER-40** | Wall-distance admissibility and the correction driver clamp | Both wall forms are continuous across `d̄ = 0` and return their wall values for every non-positive sample, rather than the sign-reversed values the ion form's root at `−P₂` would otherwise give, on the numeric and the symbolic evaluation path alike; a distance field whose minimum falls below the NUM-34 threshold aborts naming the gate, the measured minimum, its location and the fraction of samples below zero, and one above the threshold passes; the field gated is the mollified one wherever NUM-31's smoothing is applied, and a configuration activating no wall correction is not gated; and a mesh coarse enough to violate the gate is refused rather than returning the current whose two extraction routes disagree by 40 %, while a mesh that passes agrees between the routes to better than the NUM-26 tolerance. The clamp and the gate diagnostic are verified at Tier 1, on the correction functions and one field; the route-agreement half needs a converged pair and is a Tier 2 activity (PHY-02, NUM-34, NUM-26, QR-04, QR-12) |
| **VER-41** | Stabilisation terms, the mode registry and the `Pe_h` diagnostic | The element size the stabilisation parameters are defined against is asserted elementwise against its measured convention rather than assumed, so a backend that changed it fails here rather than retuning the mode in silence; the registry lists exactly the modes of §5.3.1 and refuses an unknown name listing them; the `none` entry produces an assembled residual *identical* to the unstabilised one, asserted on the vector and not on the mode string; the streamline parameter takes both branches of `ψ(q) = min(q, 1)` and is continuous at the crossover; the crosswind viscosity is exactly zero on every element at or below the Péclet number its tuning constant sets, positive on one above it, and bounded by `D_i(C Pe_K − 1)`; the crosswind projector annihilates the advective velocity and is idempotent; the crosswind, streamline and grad-div terms request the integration orders of NUM-15 and the `1/r` minimum of NUM-07 respectively, asserted on the quadrature request rather than on a number; an equal-order velocity–pressure pair is refused in every mode that supplies no flow stabilisation, naming both inf-sup and the mode that would permit it, and accepted in the mode that does; a velocity order left unset reproduces the previous two-order model exactly; the `Pe_h` diagnostic warns naming the species, the value and its `(r, z)`, is silent below the threshold, and runs in the unstabilised mode; and every mode's **linearisation** is finite at the zero-wind cold state `φ̃ = 0`, `c̃_i = 1`, `u̅ = 0`, asserted on the assembled Jacobian entries rather than on the residual, because the residual is finite there in every mode and only the linearisation is not (NUM-03, NUM-11, NUM-12, NUM-14, NUM-15, QR-12) |
| **VER-43** | Desktop shell, schema-generated editor, solver process and packaging probe | The schema walk enumerates exactly the editable dotted paths of the current case schema (`nanopnp/case/v2`), asserted in both directions so that a field added later fails this test rather than becoming silently uneditable, and the switch classification of FR-25 is checked against that same walk rather than a second one; the shell's view-model layer imports neither PySide6 nor NGSolve, asserted on `sys.modules` in a fresh process, and no `PyQt` module is reachable from any import path the shell takes (CON-09); every option the editor offers comes from the schema's own declared type or from a live registry, so no value set is written in `gui/`; a value the schema refuses is refused at the field before any substitution, naming the path, the value and the declared type, and a document the registries refuse produces the same diagnostic text the command line prints for the same file; run control drives the case through a **spawned** process, forwards a monotone completion fraction ending at 1, receives each stage transition as data — the stage's name and its position in the walk, through a structural hook, never recovered by parsing a progress caption — and cancels through a token the child honours, a cancelled run writing no artefact; a failed run reports the §3.1 exit class the command line would return for the same case; and the packaging probe imports PySide6, `QtWebEngineWidgets`, NGSolve, Netgen and `ngsolve.webgui` in one process, its bundle carrying the CON-11 licence notice (IF-09, QR-11, FR-27, CON-09, CON-11, RSK-13, §8.2 criterion 4 as amended by A4) |
| **VER-44** | Live convergence monitoring and field visualisation | The rung and the Newton step reach the shell through a structural hook carrying the residual and the undamped relative update as numbers, never recovered from a progress caption; the hook is not an input, asserted by running the same case watched and unwatched and requiring one artefact hash and one store entry; a rung that reports no Newton step yields a rung record all the same, and the plot shows it as a labelled band rather than interpolating a line across it, naming **which of the two silences** it is: a rung whose model takes no Newton callback and can report no step, or a coupled rung whose damped-Newton solve found the entry residual already below its target and returned before its first step — the NUM-16 warm-start case, which most of a warm ladder does. The hook SHALL carry that distinction as data, taken from the same test that injects the callback, because the two silences are identical from the far side and annotating either as the other states something about the solve that is not true; a solve served from the store is named as such rather than drawn as an empty plot; the plot draws no convergence threshold, the criterion of NUM-16 being per rung and disjunctive, and reports per rung which test the recorded numbers **prove** ended it rather than which the solver evaluated first: the two tests are not exclusive, so what may be asserted is the exclusion — a forced last step, which NUM-16 bars from the update test, and a last relative update above the rung's own tolerance each leave the residual test as the only one that can have closed the rung, and otherwise the update test is reported as met without also claiming the residual test was not. That tolerance SHALL travel with the rung rather than be assumed from the reference settings, so the reading is against the number the solve used; the band also reports the minimum damping and how many steps were forced; the field viewer renders a solution restored through the stage-10 gate rather than an export, its field names and units come from the IF-07 attribute vocabulary rather than from `gui/`, the scene reaches the view as a file rather than a data URL, a sample no logarithmic axis can place is omitted and counted rather than drawn at the axis floor, and a document that loaded without its renderer is reported as a diagnostic naming the renderer source rather than shown as a blank panel; the renderer is shipped with the package rather than fetched, is byte-identical to the npm tarball the repository keeps as its corresponding source, that tarball's SHA-512 is npm's published integrity, and its version is the one the installed `netgen.webgui` pins, so an upgrade that moves the pin fails the gate rather than drawing nothing; and the packaging probe's selftest fails when the bundled renderer does not reach its document (IF-09, QR-11, FR-27, NUM-16, NUM-18, QR-12, CON-09, RSK-13) |
| **VER-45** | Documentation surface and the public API | The generated case-file reference enumerates exactly the editable dotted paths of the VER-43 schema walk, in both directions, with each field's declared type, default and option set taken from the schema or a live registry, so a field added later appears without a documentation edit; the generated command-line reference covers every subcommand `build_parser()` defines, and its exit-code table is the §3.1 IF-02 enumeration, both in both directions; every name in `nanopnp.__all__` resolves and is the object at its documented module path, and the documented public surface equals `__all__`, in both directions; `import nanopnp` in a fresh process imports no `ngsolve`, `netgen` or `numpy` module, asserted on `sys.modules`; the documentation site builds with the generator's strict mode, so that a broken internal link or cross-reference fails the build, on every push including prose-only ones (§7.6) (IF-01, IF-02, IF-03, QR-15 in part; §3.1 IF-01 public-surface NOTE) |
| **VER-46** | Executed worked examples | Every command in an example's tagged console blocks is executed verbatim, from a copy of that example's directory, and exits `0`; each example meets an oracle stated in its README that is a property of the model rather than a transcribed number: an uncharged pore with symmetric reservoirs rectifies to unity within solver tolerance; a pore carrying negative fixed charge has a cation transport number above one half; a run with every correction set to `none` lists each of them under the manifest's deviations from the validated default; the two current-extraction routes of FR-23 agree to the tolerance QR-04 already gates; and fields read back from the IF-07 export carry the attribute names that vocabulary defines. No number appears in the user documentation as a result unless an example asserts it. Runs in the Tier 2 directory for its runtime; an example whose solve takes minutes (the reference geometry) is marked `slow` and is recorded rather than gated, its cheap steps still gated at Tier 1 (QR-15 in part, IF-02, FR-23, FR-24, FR-25) |
| **VER-47** | Case schema v2, the v1 upgrade and the supported interpreter range | Every case file the project shipped under `nanopnp/case/v1`, frozen as a test corpus, loads as v2. For each of them, the resolved solve provenance equals, entry by entry, the record the v1 loader made before the move less its `schema:` string; the VER-34 solve-provenance digest and the Tier-3 case identity are the hashes of that record, and the recorded v1 digests are shown to be the hashes of the recorded record, so the comparison is against what v1 keyed; the stage-8 materials key equals the recorded one; and the v1 file and its v2 rewrite share one stage-9 key and one resolved configuration; the frozen v1 field tree maps onto the v2 tree through the declared added, renamed and moved sets, in both directions, so that a key changed later without a map entry fails this test; a v1 document carrying a v2 key, a moved permittivity disagreeing with `physics.solid_permittivities`, and a v2 document using a removed or renamed key are each refused naming the keys; an undeclared schema string is refused naming both accepted ones; each supplied artefact given beside one downstream of it on the same chain is refused naming both, and each new `inputs:` key is refused as unsupported naming the stage that would consume it; `charge.exclusion_offset_nm` and `charge.dielectric_transition_nm` are classified switches whose non-zero values are listed as deviations, and read as their defaults where the block is absent; `numerics.mesh.size_scale` other than 1 beside `inputs.mesh` is refused; the Python range declared by `requires-python`, the trove classifiers, the ruff target and the CI matrix agree with each other and with §2.5 (IF-03, FR-25, FR-26, FR-27, QR-09; §5.3.1 v2 NOTEs; **added 24 September 2026**; the solve-provenance clause **amended** the same day, when the v1 keys were found to carry the schema string, §5.3.2 NOTE) |
| **VER-48** | Structure ingestion, the Cₙ axis and the oligomeric state | A synthetic Cₙ assembly (n = 7, 8, 12) about a known axis tilted 35° and offset by (3, −1.5, 40) nm, its chains lettered in a shuffled order, recovers that axis to 1e-9 in direction and in offset; with per-atom noise of 0.02 nm on an assembly whose second moments are isotropic, the permutation axis stays within the 0.01 nm displacement budget over the axial extent while the principal axis nearest the truth does not; a 6 × 2 arrangement, a D6 assembly, a ring whose chains do not turn with it, `auto` on C1, an axis 30° from the file's z and `axis: z` 0.02 nm off the detected axis are each refused naming the gate and the measured value; the in-project Kabsch rotation equals MDAnalysis `rotation_matrix` to 1e-12; a blank element, an alternate location, a missing, surplus, unlisted or truncated chain, a residue-name disagreement, a non-cyclic point group, a chain list not numbering n, a non-positive frame window, a selection MDAnalysis cannot parse, a trajectory of other atoms and an mmCIF model listing its atoms in another order are each refused naming the atom, chain, key or file, while an alternate location in a chain `source.chains` leaves out is not; PDB and mmCIF of 2WCD read to the same atom table and coordinates within 5e-5 nm, and DCD, XTC, TRR and NetCDF read back the bytes written within each format's precision; the frame stride ends on the last frame, and a `last_ns` beyond an untimed DCD's recorded span and a `count` beyond the window are refused naming both; rigidly moved frames superpose to within 1e-5 nm; the deposited 2WCD frame is refused by the orientation gate, and its chains A–L moved rigidly into an admitted frame run as stage 1 with 12 chains and 285 common C-alpha, recover the applied tilt to 1e-6 degrees, keep `z = â·x`, and re-detect their own axis as z through r = 0 to 1e-6; the artefact round-trips, its key is stable across processes, a hand edit of its payload is recorded as one, and its PDB and DCD export reloads, with residues that differ only in insertion code kept apart; a full walk and a sweep over a `structure:` case are refused naming the first stage not yet delivered (stage 2 when WP18 landed; stage 4 since WP19, **amended 25 September 2026**), `structure:` beside `inputs.mesh` is refused, and the stage is listed with neither MDAnalysis nor gemmi imported while a missing extra is named when it is created. At Tier 3 the author's ClyA-AS ensemble passes every gate over all 98 frames, recorded (IF-04, FR-01, FR-02, FR-03, FR-27, QR-12; §5.3.1 NOTE on `structure:`; **added 25 September 2026**, WP18) |
| **VER-49** | The density map | One atom gives `g` exactly and two give `g₁ + g₂ − g₁g₂`, to 1e-15 in float64 and within the float32 store's rounding; on random clusters with coincident atoms the map is finite and within [0, 1], and a NaN or out-of-range value injected into a slab aborts the run naming the voxel; the truncated map differs from an untruncated evaluation, at every voxel, by no more than the sum of `g/(1 − g)` over the terms dropped there; two frames of one displaced atom average to `(g_a + g_b)/2`, not to their union; the grid nodes are integer multiples of the spacing, the axis is a node column, every kept term lies inside the box, and the node set is unchanged by permuting frames; each lookup route of the radius set resolves — a residue, a histidine name, `HIS` where the histidines agree, `ILE CD1`, `OXT` and each terminal patch — while an unknown residue, an unknown atom, a zero radius and a `HIS` atom the histidines disagree on are each refused naming chain, residue number, residue and atom; the shipped table equals PDB2PQR's `CHARMM.DAT` entry for entry; the map round-trips through `.npz` exactly and through OpenDX and CCP4/MRC with the origin, spacing and shape exact and the values within each format's precision, and a file whose origin is off the lattice of the spacing is refused; the stage-2 key is stable across processes, moves with every density key and with the radius file's digest, and a hand edit of the payload is recorded as one; a `grid_spacing_nm` outside [0.025, 0.05] nm and a non-positive or non-finite `sharpness` are refused naming the value; a `structure:` case walks to stage 3, while a full walk and a sweep are refused naming stage 4, `geometry:` beside `inputs.mesh` is refused naming both, and the stages are listed without importing their modules or numpy. At Tier 2 every heavy atom of the prepared 2WCD dodecamer resolves and its map is bounded; at Tier 3 the author's ClyA-AS ensemble runs over the paper's final 50 frames, DCD frames 48 to 97, recorded (FR-04, FR-27, IF-05, QR-12; §5.3.1 NOTE on `geometry.density`; **added 25 September 2026**, WP19) |
| **VER-50** | The reduction to (r, z) | The annular weights sum to each annulus's exact area to 1e-11 relative, each interior cell's weights to its area, and the integral of a map is conserved slice by slice to 1e-12; an off-axis Gaussian matches the closed forms for the azimuthal mean, the Cₙ variance and the raw variance (WP19 plan, Design §2) for n = 7 and 12; an on-axis Gaussian and thin rings give a Cₙ variance below 1e-6, while the same computation without the detrend reads above 1e-4, so the test discriminates; a `cos(mθ)` modulation of amplitude b gives `b²/2` for both variances when n divides m, and otherwise a Cₙ variance of zero and a raw variance of `b²/2`; a synthetic C12 assembly deposited through stage 2 reduces unchanged to round-off when turned by 90°, to the float32 rounding of its map when turned by 30°, which maps it onto itself, and within the off-axis tolerances when turned by 15°, which does not; no harmonic is used below `n h/π`, the header names that radius, and the artefact round-trips, exports as three radial grids, and records a hand edit. At Tier 2 the prepared 2WCD reduces with its integral conserved to 1e-9 relative, its Cₙ variance nowhere above its raw variance by more than 1e-4, and an open lumen on the axis (FR-05, FR-06, FR-27, CON-04, IF-05; §5.3.1 NOTE on `geometry.density`; **added 25 September 2026**, WP19) |
| **VER-51** | Contour extraction, conditioning and its gate | A square pyramid `1 − max(|r − r₀|, |z − z₀|)/a` centred on a node, linear along every grid edge, is contoured on its square to 1e-12, with the area `(2a(1 − l))² − h²/2` to 1e-12; a Gaussian section's contour lies within 1e-3 nm of its circle of radius `s√ln 4`, against a linear-interpolation bound of 4.7e-4 nm; Taubin scales the area of a regular 64-gon by its closed form `f(k₁)^{2N}` = 1.002770, where a Laplacian of the same N passes scales it by `(1 − λk₁)^{2N}` = 0.952933, both to 1e-12; closing and opening by 2h fill a 0.1 nm slot, remove a 0.1 nm fin and keep a 0.3 nm slot, within the corner-rounding bound `δ²(1 − π/4)` per corner, and the conditioned loop's feature size exceeds 2h; a void is filled and recorded with its area, an island is refused naming its centroid and area, and a lumen closed on the axis is refused naming its z range; each §5.2.1 criterion fires on a loop built to fail it, naming the criterion, the value, the threshold and the (r, z); the probe profile of a ring of atoms matches `√(ρ₀² + (z − z₀)²) − R_a` to 1e-12 and two frames give their mean; the artefact loads through `load_profile` as a `pipeline` profile, its key is stable across processes and moves with each constant that moves a vertex or a verdict, and a hand edit is recorded; the refusals of the §5.3.1 NOTE on `geometry.contour` and the stage-5 walk refusal hold. At Tier 2 the prepared 2WCD passes the gate and its payload loads as a profile; at Tier 3 the ClyA-AS ensemble's verdict and measurements are recorded (FR-07, FR-08, FR-27, QR-12; §5.2.1; §5.3.1 NOTE on `geometry.contour`; **added 26 September 2026**, WP20) |

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
| **VER-31** | Gouy–Chapman–**Stern**, 1D | `φ_0 = φ_d + σ_s λ_S/(ε₀ε_r)` with `φ_d` and `σ_s` from VER-12's Grahame relation, the shell carrying no space charge so `φ` is linear across it | The wall potential reproduced to better than **1 %** at 0.1 M, `ζ̃_d = 2`, `λ_S = 0.25 nm` — a 30.6 % effect, so a shell the solver treats as fluid fails by 24 %; `λ_S = 0` reproduces VER-12 on the same mesh to solver tolerance (FR-15) |
| **VER-35** | End-to-end reproduction from the manifest | a case run to convergence, then reproduced from its run directory alone | Every scalar quantity of interest reproduced to better than the `1 × 10⁻⁶` nonlinear relative tolerance of §5.3.1, with the measured difference reported rather than only the verdict; run against a *fresh* store, with the store miss and the re-entry into Newton asserted, so that the cache cannot satisfy the check (the §5.3.2 QR-08 NOTE); an input file whose contents have moved aborts naming it; a library-version difference is reported and non-fatal unless the run asks for a strict environment (QR-08, IF-08) |
| **VER-39** | Sweep throughput and parallel scaling | one grid, run at several worker counts into a fresh store each time | Points per worker-hour over the members actually solved, and the parallel efficiency `T(1)/(N·T(N))`, reported with the core count, the thread pinning and the wave widths beside them. **Recorded, never gated**: completing the sweep is the assertion, and a scaling figure measured on shared hardware is a statement about that hardware (QR-06, §8.3) |
| **VER-42** | The reference-matching stabilised mode | the mode of NUM-14 exercised against the manufactured solution of VER-18, against the unstabilised solve on the same geometry under refinement, and against a mesh coarse enough to activate every term | On VER-18's manufactured solution the transport stabilisation converges at a **measured** L² rate, reported rather than asserted exact and gated only from below, one order short of VER-18's own rate by the NUM-14 NOTE on the approximate residual. That rate SHALL be measured in the mode that assembles the streamline term **alone**, because the prediction is about that term: the full reference mode additionally assembles the flow pair, whose own approximate residual costs a further order on a stable element pair, so a rate measured there would be the flow pair's wearing the transport term's name. The full mode's rate on the same problem SHALL also be measured and **recorded rather than gated**, together with the evidence attributing the difference to the flow pair — that the crosswind viscosity is identically zero on those meshes, and that the velocity error, which no transport term can reach, is the quantity that moves. The unstabilised mode on the same meshes still gives VER-18's rate, unchanged. The same run with the manufactured source withheld from the stabilisation residual SHALL be shown to change the term's effect visibly; the **direction** of that change is regime-dependent and SHALL NOT be assumed — where the manufactured problem is diffusion-dominated the source is the dominant part of the residual and withholding it switches the term off rather than corrupting it, raising the rate towards the unstabilised one, which a floor with no ceiling would pass. The assertion SHALL therefore be on the term's footprint against the unstabilised error on the same mesh rather than on the rate. On a mesh whose cell Péclet number exceeds 1 in the double layer, plain Galerkin trips the NUM-17 positivity gate and the stabilised mode converges without tripping it — the spurious negative concentrations §6.4.1 cites — and the crosswind term is active on a reported non-zero fraction of the sampled fluid and **nowhere** at or below unit cell Péclet number, which is the assertable form of "the same elements the NUM-12 warning names": that warning is a point sample and the viscosity is an element quantity, so the two counts are not comparable but the inclusion follows from the Cauchy–Schwarz bound of NUM-14 and SHALL be asserted sample by sample; on a mesh meeting NUM-30 the crosswind contributes exactly zero, asserted on the assembled term. The stabilised and unstabilised currents approach each other under refinement, with the measured rate reported and the difference asserted to fall at every level rather than against a fixed exponent, because the sequence reaches `O(h²)` from below and its coarsest interval is pre-asymptotic; the two extraction routes of NUM-24 and NUM-25 agree to NUM-26's tolerance in the stabilised mode, and disagree by the reported stabilisation contribution when that term is removed from the indicator route, so the identity is measured rather than assumed. The equal-order velocity–pressure pair converges in the mode that permits it and its velocity field is compared against the Taylor–Hood solve, **recorded and not gated**: it is an input to the §7.4 attribution rather than a verdict (NUM-03, NUM-11, NUM-12, NUM-14, NUM-15, NUM-24, NUM-26, VER-18) |

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
| **VAL-03** | Reference-solution generation and archival, in Phase 1 | Full reference set for the frozen cases archived with the generating model, independent of continued licence access, and **declaring** per field its source expression and its unit, and for the current its evaluation boundary and which electrode it references; a golden leaving any of those unstated is refused rather than interpreted |
| **VAL-04** | Reference discretisation-error probe | The reference case re-solved at two refinement levels while licence access lasts, bounding the reference's own discretisation error |
| **VAL-05** | Geometry pipeline against the published boundary | Auto-generated contour compared against the delivered reference pore polygon (§5.2.1): radius profile and constriction radius within a stated tolerance. Measured on two inputs (§8.2.2 B2): the public 2WCD entry, gated at Tier 2 to a looser tolerance, and the author's ClyA-AS ensemble, archived under `NANOPNP_REFERENCE_DATA` and run at Tier 3; the Phase 2 gate requires the ensemble leg. Each leg's tolerance is stated with its argument when the comparison is implemented |
| **VAL-06** | Poisson-only comparison against APBS | Potential from the assembled fixed-charge and dielectric fields agrees with an APBS solve on the same structure within a stated tolerance |
| **VAL-15** | The reference model's own `rhoq_pore` table, on our mesh | The delivered table reads with the grid its header declares, its planar integral is the declared `Q_net` to better than 10⁻⁹, and its boundary ring is negligible against its interior, so the producer leg of §4.4 is exact and the reference's 1.25 % is the consumer's (OPN-06); the consumer leg on the reference mesh is recorded with the mesh it came from, and the quadrature-agreement gate refuses it, per cent-level, rather than reporting a conserved number it cannot defend |

NOTE (the comparison surface, and why VAL-01 reports two norms; WP13): the probe grid is **this
project's**, a content-hashed document of named tensor-product patches that the reference is
interpolated onto, so the comparison does not depend on the reference's mesh and a re-export cannot
silently move the sample points; the grid's hash is declared in every golden and a mismatch is
refused. A probe point is retained for a field only where the point *and* its four `±0.05 nm`
neighbours lie inside that field's domain — the reference model's own maximum element size on the
pore wall — because a solver returns zero outside a field's domain rather than refusing, and a
concentration norm taken over the membrane is dominated by fabricated zeros and reads as agreement.
Where the two implementations then still disagree about where a field exists, the comparison SHALL
abort naming the worst point and its distance rather than intersecting the two sets.

The VAL-01 quantity is the **`r`-weighted** axisymmetric relative L² error, which is the norm the
axisymmetric weak forms of §6.2 are posed in. It SHALL be reported together with the unweighted
relative L² and with the located maximum, because the `r` weight vanishes on the axis — the weight
is three orders smaller on a near-axis sample than at the pore wall — and the axis is exactly where
the `1/r` forms of §6.2 and the NUM-06 natural condition are fragile. A comparison reporting the
weighted norm alone would be least sensitive precisely where this implementation is most likely to
be wrong. The pressure SHALL be compared **gauge-free**, its `r`-weighted mean removed from both
fields and the removed constants reported: `p` enters the momentum equation only through `∇p`, the
reference's gauge is not in the model report, and a gauge offset compared raw presents as a
discrepancy of order one that is not a discrepancy at all.

NOTE: the reference model carries no mesh convergence study, so part of any residual difference may
originate in the reference (RSK-09). The project's own discretisation error is quantified first
(§7.3), and the residual is then attributed.

NOTE (the frozen cases, closing VAL-03's scope; author ruling, 18 September 2026): the reference set
is **five cases** on the §5.2.1 reference geometry, in the validated ePNP-NS configuration — the
four envelope corners 0.05 M and 3 M × ±200 mV, and the centre point 0.5 M / +50 mV. The corners
span the experimental range of VAL-07 and supply VAL-02 a matched opposite-bias pair at each salt,
so `RR` is comparable and not only `I`; the centre point separates a discrepancy linear in bias from
one quadratic in it. The §7.5.1 analyte case is **not** in the set. VAL-04's refinement pair is the
published mesh and one uniform refinement of it, on the centre case alone: RSK-09 needs a bound on
the reference's own discretisation error, not a field of them, and a comparison whose residual falls
below that bound SHALL be reported as *reference-limited* rather than as agreement.

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
| Every push, prose-only pushes included | The strict documentation build of VER-45 (**added 23 September 2026**) |

Every run SHALL emit a provenance manifest recording input hashes, library versions, mesh hash,
solver settings, stabilisation mode and correction parameter file versions (FR-25).

---

## 8. Implementation plan

### 8.1 Phases and gates

| Phase | Deliverable | Gate | Estimate |
|---|---|---|---|
| 0. Spike | Coupled ePNP-NS on an analytic cylindrical pore; continuation ladder; Tier 1 and Tier 2 suites (§8.2.1) | §8.2 exit criteria, as amended by §8.2.1 | 3–5 weeks |
| 1. Solver core | Production solver on an externally supplied mesh, full QoI extraction, frozen case-file schema, sweep runner | Tier 1 and Tier 2 pass; Tier 3 enabled and differences attributed; met as amended by §8.2.3 | 6–10 weeks |
| 2. Geometry pipeline | Structure and trajectory ingestion, density, symmetry reduction, contour, CAD, mesh | VAL-05: the auto-generated mesh reproduces the hand-conditioned reference geometry | 8–12 weeks |
| 3. Charge pipeline | PDB2PQR to smeared volumetric `ρ_fixed` and dielectric field | VER-01, VER-02 and VAL-06 pass | 3–5 weeks |
| 4. Validation and release | Full V&V suite in CI, documentation, JOSS paper, v1.0 | Tier 4 passes (VAL-07 to VAL-10) | 4–6 weeks |
| GUI | Continuous track from Phase 0 onward, one increment per phase | QR-10: an experimentalist runs a case unaided | continuous |
| Documentation | Continuous track from Phase 1 onward, one increment per phase (**added 23 September 2026**) | VER-45 and VER-46 pass on every push | continuous |

GUI increments, one per phase (ADR-004):

| Phase | GUI increment |
|---|---|
| 0 | Packaging probe: a trivial PySide6 and NGSolve `webgui` application that builds into a double-clickable Windows bundle |
| 1 | Case editor over the frozen schema, run control, live convergence plot, field viewer; meshes supplied externally |
| 2 | Geometry pipeline surfaced: load a structure, inspect the density, contour and mesh steps, override the contour by hand |
| 3 | Charge pipeline surfaced: pH selector, force field, charge map viewer, conservation report |
| 4 | Sweep builder, result browser, figure export, case comparison |
| post-1.0 | Installers for all three platforms, in-application tutorials |

Documentation increments, one per phase (QR-15 NOTE; **added 23 September 2026**). Each phase
documents what it ships, and a phase's examples are executed by VER-46. The model itself is
documented by rendering this specification and the companion knowledge base (§11) verbatim, never
by a restatement of their equations:

| Phase | Documentation increment |
|---|---|
| 1 | Documentation site and its build; user guide for the solver core, the case file, meshes and fields, runs, sweeps, provenance and the desktop shell; generated case-file, command-line and exit-code references; the API reference over the IF-01 public surface; worked examples on an idealised pore and on the reference geometry |
| 2 | The geometry pipeline: structure and trajectory input, density, symmetry reduction, contour, meshing; an example from a PDB entry to a mesh |
| 3 | The charge pipeline: protonation, force field, smearing, the conservation report; an example from a PDB entry to a charged run |
| 4 | Tutorials completed against the validated release, the JOSS paper, and the DOI-archived v1.0 (QR-15 in full) |
| post-1.0 | In-application tutorials, with the GUI track |

Phase 2 SHALL NOT start before the Phase 0 exit criteria are met.

NOTE (FR-19, FR-20; **added 24 September 2026**): v0.9 is released by Phases 2 and 3 together.
FR-19's `pb` and `pb-linear` models shipped in Phase 0. FR-20, the documented physics-model
interface, is assigned to **Phase 3**, which is where the table above leaves room for it (§8.2.2 B7).

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
| A4 | **Added 20 September 2026.** Criterion 4 is discharged in Phase 1, and how: a gated `windows-latest` continuous-integration job SHALL build the bundle on every push from a probe application that imports PySide6, `QtWebEngineWidgets`, NGSolve, Netgen and `ngsolve.webgui` in one process, and SHALL launch the built bundle headlessly. The criterion is closed by the author's observation that the uploaded bundle double-clicks, recorded with the build that produced it | Turns RSK-13 from a risk detected once into one detected on every push, which is what amendment A2 cost. A probe that omitted Qt WebEngine would retire RSK-13 without exercising the payload most likely to defeat packaging, so the import set is named here rather than left to the builder. "Double-clickable" remains a human observation: a process exit code on a headless runner does not establish it, and the criterion says desktop |

Phase 0 is therefore met by criteria 1 to 3 as written, with criterion 4 explicitly outstanding
until amendment A4's build and observation have both happened.

NOTE — **Criterion 4 closed, 24 September 2026.** The author double-clicked the bundle uploaded as
`nanopnp-probe-windows` by the gated `bundle` job of CI run
[36045057612](https://github.com/willemsk/nanopnp/actions/runs/36045057612), built from commit
`52fd531` (reported version `0.5.0a11.dev4+g52fd531b4`), on a Windows desktop. The executable opened
a window drawing a basic mesh with its controls. The author called it "still a bit janky", which is
a usability remark on the probe and not a packaging failure: the criterion asks that the bundle
build and open, and it did. Amendment A4's build and observation have both happened, so criterion 4
is met and RSK-13 is retired as a risk. The `bundle` job keeps detecting it on every push.

#### 8.2.2 Phase 2 decisions, agreed 24 September 2026

Rulings by the author, taken while planning Phase 2 (`docs/plans/phase-2-geometry-pipeline.md`).
Where a ruling changes a clause, the clause is amended in the commit named in the last column.

| # | Decision | Consequence | Clause changed, and when |
|---|---|---|---|
| B1 | Phase 2 starts only after the Phase 1 end-of-phase report has merged (tag `v0.5.0`) and the author has recorded the double-click observation of amendment A4 | The start condition of §8.1 is met as written, not amended: criterion 4 and RSK-13 close on the observation | None |
| B2 | VAL-05 is measured on two inputs. The public 2WCD entry (wwPDB, CC0) is vendored as test data and gated at Tier 2 to a looser tolerance. The author's 50-frame ClyA-AS ensemble, or the prepared structure it came from, is archived under `NANOPNP_REFERENCE_DATA` and run at Tier 3. The Phase 2 gate requires the ensemble leg | 2WCD lacks residues 1–7 at the *trans* constriction and the MD relaxation, so only the ensemble can be held to a tight tolerance. The 2WCD leg still exercises the whole pipeline on every push | §7.4 VAL-05, in the Phase 2 plan's commit. The tolerances are stated in the VAL-05 work package |
| B3 | The case schema moves **once**, to `nanopnp/case/v2`, in the first Phase 2 work package. That move carries every key Phases 2 and 3 are foreseen to need, among them stage-4 hand substitution under `inputs:` and the membrane's axial position. A v1 document reads losslessly as v2 | The §5.3.1 compatibility rule stands: adding a key moves the version, and it moves once rather than once per phase | §5.3.1, in the first Phase 2 work package |
| B4 | The Python floor rises to 3.11 (Python 3.10 reaches end of life in October 2026) | One MDAnalysis (2.10) and one GridDataFormats (1.2) across the supported range, as §2.6 names them. The IF-05 NOTE's conditional CCP4 write side is retired | QR-09 and §2.5, in the Phase 2 plan's commit. The IF-05 NOTE, `requires-python` and the CI matrix change with the code, in the first Phase 2 work package |
| B5 | The radius-profile criterion of stage 3 and §5.2.1 is checked against a probe-radius profile computed in project code on the aligned structure. HOLE, through `mdahole2`, becomes an optional cross-check that skips when absent | HOLE is a compiled binary with no wheel, so it cannot sit on the end-user path (CON-07, QR-09) | §5.2 stage 3 and §5.2.1, in the Phase 2 plan's commit |
| B6 | The author's contour script is available (OPN-02) | It is read before the contour work package is planned, as RSK-06 intends. The specified pipeline remains the fallback | §10 OPN-02, in the Phase 2 plan's commit |
| B7 | FR-20 moves to Phase 3. The optional Gmsh mesher adapter of ADR-002 is delivered in Phase 2 | Phase 2 stays on the geometry chain. The Gmsh backend is optional and never imported on the default path (CON-10) | §8.1 NOTE, in the Phase 2 plan's commit |

#### 8.2.3 Phase 1 exit, agreed 24 September 2026

The Phase 1 gate of §8.1 is "Tier 1 and Tier 2 pass; Tier 3 enabled and differences attributed".
The end-of-phase report (`docs/plans/phase-1-solver-core.md`) measures the phase against it.

| # | Amendment | Consequence |
|---|---|---|
| C1 | The gate's last clause is met by Tier 3 being **enabled and its attribution machinery verified**: the four-rung ladder against a self-golden, with `golden_source: self` on every report. The attribution of differences **against COMSOL** is recorded as outstanding until the author's reference exports exist (VAL-03, `docs/validation/comsol-export-contract.md`). When they land, it is reported as an addendum to the Phase 1 report, and it gates nothing retroactively. v0.5.0 is released on this basis | Phase 1 closes without the one comparison that needs data the project does not yet hold. The consequence is the same as A2's: a risk stays open longer than planned, here RSK-09 (a Tier-3 discrepancy originating in the reference) and the attribution of any residual. Nothing in Phase 2 touches a weak form, so the addendum can land at any point without re-opening a Phase 2 result |
| C2 | The §8.3 reference sweep (3,675 points on 12 cores) is planned and checked in, but not run. QR-06's scaling is measured on 4 cores (VER-39, recorded and never gated) | QR-06 remains a SHOULD, measured only at the scale the development machine allows. The day-scale run is the author's to make, on HPC hardware |

Phase 0 criterion 4 is not changed by this section. It was closed by the author's double-click,
recorded in the NOTE to §8.2.1 on the same day, which met the last condition of §8.2.2 B1.

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

NOTE (QR-06): the scaling claim is about *independent* workers. Processes sharing one linear-algebra
thread pool are not independent, and a scaling curve measured without the thread counts pinned per
worker (§5.3.4) reports the pool rather than the dispatch. A throughput figure SHALL likewise be
computed over the members that were actually solved, cache hits being dictionary lookups that would
otherwise report unbounded throughput for a resumed sweep.

---

## 9. Risk register

| ID | Risk | Severity | Likelihood | Mitigation | Detection phase |
|---|---|---|---|---|---|
| **RSK-01** | Newton stagnates once `⟨c⟩`- and `d`-dependent `D`, `μ`, `ε`, `ϱ` are active | High | Low–Med | Corrections enabled last in the continuation ladder; pseudo-transient continuation and hybrid fallbacks; mollified C¹ distance field (VER-06). The reference converged on this system with a fully coupled direct solver and lower-bounded variable damping | Phase 0 |
| **RSK-02** | Under-resolved Debye layer at 3 M (λ_D = 0.18 nm) gives negative concentrations and a silently wrong current | High | Med | Mesh criterion `h ≤ λ_D/5`; `min c_i` monitored per Newton step and failed loudly (VER-08) | Phase 0–1 |
| **RSK-03** | Current QoI wrong from non-conservative CG flux, corrupting the rectification signal | High | Med | Both the ψ-domain-integral and the variational reaction flux mandated, with automatic agreement check (VER-11) | Phase 1 |
| **RSK-04** | Analyte net force is a near-cancellation of two terms of about 10 pN and opposite sign; a small error in either integral flips the sign of the total | High | Med–High | Domain-form force evaluation (§6.7) rather than surface integration; dedicated force convergence study; both routes cross-checked to better than 0.1 pN (VER-22) | Analyte phase |
| **RSK-05** | Contour to mesh produces slivers at the constriction | Low–Med | Low | The delivered 185-vertex pore polygon ships as a fixture (§5.2.1); the reference mesh used no boundary layers, only isotropic grading to 0.05 nm at the pore wall; contour validity gate (FR-08); isotropic fallback; mesh quality gates abort the run (VER-10) | Phase 2 |
| **RSK-06** | The author's contour script proves tightly coupled to its original context and is not portable | Med | Med | Read it in week 1 of Phase 2, before the rest of the phase is planned; fall back to the specified contour pipeline. **Retired 26 September 2026**: it was read (OPN-02). It is 20 lines, coupled to nothing beyond MDAnalysis, scikit-image and Shapely | Phase 2 |
| **RSK-07** | Axisymmetric reduction invalid for a given pore through large azimuthal variance | Med | Med | Residual azimuthal variance reported as a first-class output (FR-06) and documented as a validity criterion | Phase 2 |
| **RSK-08** | Charge non-conservation through smearing and 1/r projection | Med | Med | Exact annular volumes; analytic annulus integration; assertion on the deployed mesh and per-z-slice check (VER-01, VER-02) | Phase 3 |
| **RSK-09** | The reference model carries no mesh convergence study, so a Tier 3 discrepancy of a few per cent may originate in the reference | Med | Med–High | Quantify this project's discretisation error first (§7.3), then attribute the residual; re-solve the reference case at two refinement levels while licence access lasts (VAL-04); never adjust the solver to close such a gap | Tier 3 |
| **RSK-10** | The NGSolve pip wheel ships without MUMPS, and UMFPACK or SuperLU may not handle production-size coupled factorisations | Med | Med | Two solver configurations (§6.6); measured on day one of Phase 0 (§8.2 criterion 3); iterative fieldsplit through ngsPETSc in reserve | Phase 0 |
| **RSK-11** | NaN from 1/r terms at integration order 2, silent rather than a crash | Med | Med–High | Integration order ≥ 3 asserted on all 1/r forms; dedicated test on an axis-touching mesh (VER-07) | Tier 1 |
| **RSK-12** | Transcription errors in the correction coefficients, the per-ion `D` and `μ` sets being easy to conflate | Med | Med | Coefficient files reviewed against the model report in a second pass; each `f(c)` property-tested against published check values (VER-03) | Tier 1 |
| **RSK-13** | Desktop packaging defeated by a binary dependency | Med | Low–Med | NGSolve wheels chosen for this reason; packaging prototyped in Phase 0 (§8.2 criterion 4), not at the end. **Retired 24 September 2026** on the author's double-click (§8.2.1 NOTE); the gated `bundle` job re-detects it on every push | Phase 0 |
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
| **OPN-02** | Location of the author's contour script. **Closed, 26 September 2026 (WP20 plan, Design §1).** It is `create_polygon_contour` in the author's `pqr2grid`, first committed 7 October 2019. It takes the first contour found at 0.25, applies Shapely `simplify(0.1)` and writes at `%.2f`, with no smoothing, spacing step or gate. Its radial binning places column j at `jh`, where the bin's centre is `(j + ½)w`, with `w = (2L + 1)h/(2L + h)`. That is an index-to-radius erratum (`.knowledge/04` §1.2). The WP20 plan, D2, records what ports | Closed | Closed |
| **OPN-03** | PlyAB supporting-information details: analyte relative permittivity, per-position mesh strategy (remesh against ALE), barrier heights in kT, electro-osmotic flow velocities | Author, from the retained model files | Analyte force regression targets and adoption of PlyAB as a second reference case after v1.0 |
| **OPN-04** | ClyA-AS mutation list: 8 mutations relative to the *S. typhi* wild type in one place, 27 relative to the *E. coli* 2WCD structure in another. Both internally correct | Author, with the structure-preparation stage | Provenance of `Q_net` (FR-12); the structure-preparation stage must record which list was applied to which PDB |
| **OPN-05** | Pore-polygon vertex table. **Delivered** as `data/geometry/clya_as_radial_geometry.csv`, 185 vertices, extents as published. **Closed by the author, 5 September 2026: the delivered table is the geometry of record**, and the model report's 190 is the count after COMSOL's import conditioning. §2.2 and §5.2.1 are amended to it; the §5.2.1 fixture, `mesh/reference.py` and VAL-05 all cite it | Closed | Closed |
| **OPN-06** | Attribution of the reference's own charge-conservation gap: `−72.9 e` against `−72 e` atomistic is 1.25 %, twelve times QR-03's budget. **Answered from the delivered `rhoq_pore` table, 6 September 2026: it is the consumer's.** The table's own planar integral is `−71.999999999663 e`, exact to `4.7 × 10⁻¹²`, so the producer leg is not where the 1.25 % went, and the published net charges are not different constructs on this axis. Our own consumer leg on a comparable mesh is `−0.99 %` by the same interpolate-and-integrate route — the same size and character, opposite sign — which is aliasing of a sub-element-scale field, not lost charge (§4.4 NOTE) | Closed | Closed: any Tier-3 comparison of pore charge (VAL-06, WP13) compares two consumer legs, and ours is gated ten times more strictly than the reference achieved |

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
| IF-01 | VER-25, VER-32, VER-45 (the public surface and its import cost) |
| IF-02 | VER-32, VER-38, VER-45 (the generated command-line and exit-code references), VER-46 (every documented command executed) |
| IF-03 | VER-09, VER-36 (dotted-path substitution against the schema), VER-47 (schema v2 and the v1 upgrade) |
| IF-04 | VER-48 (PDB, mmCIF and each trajectory format read; PDB and mmCIF of one entry agree) |
| IF-05 | VER-29, VER-49 (the density map in `.npz`, OpenDX and CCP4), VER-50 (the reduced map exported as radial grids), VAL-15 |
| IF-06 | VER-27 |
| IF-07 | VER-33 |
| IF-08 | VER-24, VER-35 |
| IF-09 | VER-43, VER-44 |
| FR-01 | VER-48 (frame window, superposition on the earliest frame's C-alpha, Kabsch against MDAnalysis) |
| FR-02 | VER-48 (the permutation axis against a known axis, and against principal axes) |
| FR-03 | VER-48 (missing, surplus and truncated chains, residue names and the point group refused) |
| FR-04 | VER-49 (the union density, its truncation bound, the frame average and the radius set) |
| FR-05 | VER-01 (shared annular-volume integration), VER-50 (exact annular weights and the harmonic Cₙ average) |
| FR-06 | VER-50 (the Cₙ and raw variance against closed forms) |
| FR-07 | VER-51 (marching squares against exact and closed-form level sets, the morphology, Taubin and the conditioning), VAL-05 |
| FR-08 | VER-51 (each §5.2.1 gate criterion fires on constructed input; the radius band against the probe profile) |
| FR-09 | VER-28, VAL-05 |
| FR-10 | VER-10, VAL-05 |
| FR-11 | None yet |
| FR-12 | VAL-06 |
| FR-13 | VER-01, VER-02, VAL-06 |
| FR-14 | VER-01, VER-02, VER-29 (the deployed-mesh half), VAL-15 |
| FR-15 | VER-30, VER-31, VAL-06 |
| FR-16 | VER-03 |
| FR-17 | VER-08, VER-16, VER-18 |
| FR-18 | VER-13, VAL-10 |
| FR-19 | VER-12, VER-13 |
| FR-20 | None yet |
| FR-21 | VER-20, VER-22 |
| FR-22 | VER-19, VER-21, VER-22 |
| FR-23 | VER-11, VER-38 (the two-point ratio) |
| FR-24 | VER-36, VER-37, VER-38 |
| FR-25 | VER-24, VER-26 (manifest emitted per §7.6) |
| FR-26 | VER-09, VER-26, VER-47 (a v1 document and its v2 rewrite are one run) |
| FR-27 | VER-23, VER-25, VER-26, VER-32, VER-34, VER-51 (the stage-4 payload is an `inputs.profile` document) |
| FR-28 | None yet |
| FR-29 | None yet |
| QR-01 | VER-12 to VER-22, in particular VER-17 and VER-18 |
| QR-02 | VAL-01, VAL-02 |
| QR-03 | VER-01, VER-29, VAL-15 |
| QR-04 | VER-11, VER-40 (the route disagreement as a resolution gate), VER-42 (the identity under a stabilisation mode) |
| QR-05 | VAL-07, VAL-08, VAL-09 |
| QR-06 | VER-39 (measured, recorded, not gated) |
| QR-07 | None yet (§8.2 criterion 3) |
| QR-08 | VER-26 for manifest sufficiency; VER-34, VER-35 for QoI reproduction |
| QR-09 | VER-47 (the declared interpreter range agrees with §2.5); the wheel-only install itself is exercised by the §7.6 matrix, not asserted by a test |
| QR-10 | None yet |
| QR-11 | VER-43, VER-44 |
| QR-12 | VER-10, VER-32, VER-40, VER-41, VER-48 (the stage-1 input and symmetry gates), VER-49 (the radius refusal and the density bounds gate), VER-51 (each contour gate criterion names its value, threshold and (r, z)) |
| QR-13 | None yet |
| QR-14 | VER-03 |
| QR-15 | VER-45, VER-46 — the documentation part only, delivered incrementally by the §8.1 documentation track; the JOSS submission and the DOI-archived release remain unverified until v1.0 |
| CON-01 | None yet |
| CON-02 | VER-20, VER-22 |
| CON-03 | None yet |
| CON-04 | VER-50 (axisymmetric inputs read no variance, and a Cₙ turn leaves the reduction unchanged) |
| CON-05 | VAL-07 (residual discrepancy below 0.05 M) |
| CON-06 | None yet |
| CON-07 | None yet |
| CON-08 | §6.6 measurement table (§8.2 criterion 3, discharged) |
| CON-09 | VER-43 (no PyQt module is reachable from the shell's import paths); VER-44 (the shipped renderer is byte-identical to the npm tarball kept as its source, whose SHA-512 is npm's published integrity) |
| CON-10 | VER-27 (the default ingestion path imports no Gmsh) |
| CON-11 | §6.6 measurement table — measured; the conflict it exposed is resolved by the 2 September 2026 amendment to CON-11 and ADR-003. VER-43 asserts that the bundle's licence notice states the resulting GPL-2+ obligation, and the probe refuses to start without it |
| CON-12 | None yet |
| CON-13 | VER-43 in part (the Windows bundle builds and launches headlessly on every push; widget construction is asserted on `windows-latest` and `macos-latest`). Linux *desktop* Qt is deliberately not asserted: the push gate installs no system packages, and PySide6 does not import on the runner image |
| CON-14 | None yet |

Coverage: 54 of the 67 requirements in §3 have a specified activity; 13 are recorded as "none yet",
predominantly interface, portability, licensing and documentation requirements whose demonstration
is by inspection rather than by test. Recounted row by row on 26 September 2026, after FR-08 gained
VER-51 (WP20); FR-07, FR-27 and QR-12, which already had an activity, gained it too. The line
before that, 53 and 14, was recounted on 25 September 2026, after FR-04, FR-06 and CON-04 gained
VER-49 and VER-50 (WP19). The line before that, after IF-04 and FR-01 to FR-03 gained VER-48, read 50 and 17,
and corrected an earlier 45 and 22 that was one off. QR-07 is counted as "none yet", its entry
naming §8.2 criterion 3 as the measurement it is still waiting for rather than as one it has.

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

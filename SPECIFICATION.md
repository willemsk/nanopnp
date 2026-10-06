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
| PDB2PQR 3.7+ | BSD-3 | Protonation states and partial charges |
| PROPKA 3.5+ | LGPL-2.1 | pKa prediction, installed as a PDB2PQR dependency. Licensed LGPL-2.1 (its package metadata), acceptable under CON-09 |
| APBS 3.4.1 | BSD-3 | Poisson-only cross-check (VAL-06), run from the `apbs-binary` wheels (Apache-2.0 packaging; Linux x86_64 and macOS) in a test-only dependency group, never on the end-user path (§8.2.4 D3) |
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
| v0.2 | 1 | Solver core on an externally supplied mesh and material/charge fields; full QoI extraction; pluggable correction models; frozen case-file schema; stable Python API; CLI; sweep runner. |
| v0.3 | 2 | Geometry pipeline: structure and trajectory ingestion, density, symmetry reduction, contour, CAD, mesh. |
| v0.4 | 3 | Charge pipeline: PDB2PQR to smeared ρ_fixed and dielectric field; the physics-model interface (FR-20). Runs the paper's pipeline end to end, from structure to current; the reproduction of the published results is measured at v0.7 (VAL-16, VAL-17; §8.2.4 D6). |
| v0.5 | 4 | Polish and user testing (§8.2.6 F3): an exploration of the modularity of the implementation architecture, then a user-testing pass over the physics, the numerics, the Python API and the command line. No GUI increment. |
| v0.6 | 5 | Graphical interface (§8.2.6 F5): a design and requirements document with mockups, a visual-feedback workflow, then the desktop application its plan sets: case builder, run control and live convergence monitoring, field visualisation. Absorbs the former v1.5 row. |
| v0.7 | 6 | Validated release: V&V suite in CI, the published current–voltage relationships and in-pore averages reproduced (VAL-16, VAL-17), documentation, tutorials, JOSS submission, DOI-archived. Released before the stable version (§8.2.5 E2, from v1.0; §8.2.6 F1, from v0.5 and Phase 4). |
| v1.0 | — | Stable release: the API stability promise of IF-01. Its content and gate are the author's to define (OPN-08). |
| post-1.0 | — | Backlog: installers for all three platforms and in-application tutorials (the former v1.5 row's remainder, §8.2.6 F5); 3D; transient; ion-specific rather than ionic-strength-based property models; MD-fitting toolkit for corrections; solid-state pores; charge regulation; multi-species electrolytes beyond binary; non-axisymmetric analytes. |

Release tags in §3 take five values: v0.2, v0.3, v0.4, v0.7, post-1.0. A
requirement the Phase 5 design document adds is tagged v0.6 (§8.2.6 F5).

NOTE (Versioning; §8.2.4 D1): the
releases above are git tags `vX.Y.Z`, one minor version per phase, on the commit that merges the
phase's end-of-phase report (§8.1): `v0.1.0` for Phase 0, `v0.2.0` for Phase 1, `v0.3.0` for
Phase 2, `v0.4.0` for Phase 3, `v0.5.0` for Phase 4, `v0.6.0` for Phase 5 and `v0.7.0` for Phase 6
(§8.2.5 E2, §8.2.6 F1 and F2). Each merged work package is tagged
`vX.Y.Z-alpha.N` on its last commit on `main`, where N counts the phase's work packages toward
that release. The tag names are SemVer, and PEP 440 reads them as
`X.Y.ZaN` (`0.2.0a10`). The package version is derived from the tag (hatch-vcs), so a commit between
tags installs as a development version naming that commit, and the provenance manifest's recorded
`nanopnp` version identifies the code that produced a result (FR-25). The version enters no artefact
key: the environment is recorded beside an artefact, never hashed into it (§5.3.2). `CHANGELOG.md`
records every tag, and a milestone tag publishes a GitHub Release with its section as the notes. A tag name is never moved to another commit once published and never reused for
another phase. The names `v0.5.0` and `v0.5.0-alpha.N` are Phase 4's; a manifest recording
`0.5.0` or `0.5.0aN` from code that does not descend from `v0.4.0` is Phase 1's `0.2.0` or `0.2.0aN`,
and a recorded `0.9.0aN` is Phase 2's `0.3.0aN` (`CHANGELOG.md`, head). A milestone tag's
release workflow enforces that `CITATION.cff` names its version only for the highest milestone
tag, the release that *Cite this repository* shows; an older milestone's citation metadata is
fixed in its commit and a re-release cannot change it.

---

## 3. Requirements

The subject of each requirement is the product unless stated otherwise.

### 3.1 External interfaces

| ID | Requirement |
|---|---|
| **IF-01** | SHALL expose a Python API in which every pipeline stage is a separately importable, invocable object, stable from v1.0 onward (§8.2.6 F4). |
| **IF-02** | SHALL provide a CLI over the same stage objects, able to execute a case file, run one stage, and dispatch a sweep. |
| **IF-03** | SHALL accept one declarative YAML case file, identified by `schema: nanopnp/case/v2`, as the complete run specification, rejecting unknown keys with a diagnostic naming the key. A document declaring `nanopnp/case/v1` SHALL be read losslessly as its v2 upgrade (§5.3.1; §8.2.2 B3). |
| **IF-04** | SHALL read structures in PDB and mmCIF, and trajectories in DCD, XTC, TRR and NetCDF. |
| **IF-05** | SHALL read and write volumetric density and charge grids in OpenDX and CCP4. |
| **IF-06** | SHALL write meshes in Gmsh MSH 4.1 as the archival format, and SHOULD read any format meshio supports. |
| **IF-07** | SHALL write solution fields in XDMF with HDF5 heavy data. |
| **IF-08** | SHALL accompany every result artefact with a machine-readable provenance manifest (FR-25). |
| **IF-09** | SHALL provide a desktop graphical interface covering case editing, run control, convergence monitoring and field visualisation, as a thin shell over the IF-01 stage objects. |

Rationale (IF-06): MSH 4.1 is the only format in the toolchain carrying physical-group tags,
higher-order elements and mixed element types without loss.

NOTE (IF-05, QR-09; §8.2.2 B4): the 3.11 floor takes GridDataFormats 1.2 or later everywhere, which
has an MRC writer, so IF-05 is met unconditionally and VER-29 asserts the CCP4 round trip without a
refusal branch.

NOTE (IF-05, length units; §8.2.2 B10, WP25): the length unit at the
interchange boundary follows the reader each file is written for. The stage-2 density map is a
3D map for a molecular viewer, so its OpenDX and CCP4/MRC files carry origin and spacing in
ångströms. CCP4/MRC defines the cell in ångströms, and the aligned structure it overlays is
exported as a PDB, which is in ångströms by its format. Reading such a file back converts to nm and
places the origin on the lattice of the spacing. The native `.npz` stays in nm, as does everything
inside the package. The 2D `(r, z)` grids of the `inputs.charge` and `inputs.eps_r` NOTE, and the
reduced map exported as radial grids, stay in nm, because their `field1` header declares the grid
in nm and is checked against the file. Changing that is a decision for the Phase 3 charge grids.

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

NOTE (IF-02, generators): `nanopnp mesh cylinder` and
`nanopnp mesh reference` write an *input artefact*, a Gmsh MSH 4.1 mesh (IF-06), rather than run a
case. The geometric flags of `mesh cylinder` shape that file, and a run that later consumes it
records it by content hash through `inputs.mesh` (§5.3.1, §5.3.2), exactly as it would any
externally supplied mesh. So they do not change what a run solves, and the configuration NOTE above
is not breached. `mesh reference` takes no geometric flag, since its preset is fixed by §5.2.2 and
the geometry of record. Both commands print the written mesh's content hash and the
`inputs.mesh.groups` mapping a case needs to read it. Both are subject to the mesh quality gate of
VER-10. These commands are the v0.2 means of producing a mesh without Python, and they are not the
meshing pipeline of FR-10, which is v0.3.

NOTE (IF-02, export; WP25): `nanopnp stage <name> <case> --export
PATH` writes the artefact that stage stored, in an interchange format chosen by the suffix of
`PATH`: the aligned ensemble as a PDB of its first frame with a DCD of every frame beside it
(IF-04); the density map as `.npz`, OpenDX or CCP4/MRC (IF-05, in the units of the IF-05 NOTE on
length units); the reduced map as `.npz`; the stage-4 profile as its stored `nanopnp/profile/v1`
document; a stage-6 mesh as its stored MSH 4.1 file (IF-06); and the protonation artefact as a
`.pqr`, in stage 1's frame and in ångströms, one `MODEL` per frame where there is more than one
(WP27). The profile and the mesh are copied byte for byte, and the PQR
read back through `inputs.pqr` gives the artefact's payload exactly. `PATH` is an output
location, so the configuration NOTE is not breached, and no artefact key depends on it. A stage
without an export, or a suffix that stage does not write, SHALL be refused as
a usage error naming the accepted ones before any stage runs. No partial file SHALL be left behind
by a failure. A profile exported this way and supplied through `inputs.profile` is a supplied
profile (§5.3.1 NOTE on `geometry.contour`).

NOTE (IF-01, public surface): the stable API is the set of names in
`nanopnp.__all__`, together with the modules the user documentation's API reference names. Every
other module is internal and may change without notice before v1.0. Before v1.0 the public surface
may change too, in any phase (§8.2.6 F4), but never without notice: each
change is a decision recorded in `tests/tier1/test_public_api.py`, and each break is listed in
`CHANGELOG.md` with its migration. The top-level names are
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
| **FR-01** | SHALL ingest a structure and optional trajectory ensemble and superpose all frames on a reference frame's Cα set. | v0.3 |
| **FR-02** | SHALL determine the Cₙ axis by chain-permutation superposition, taking the eigenvector of eigenvalue 1 of the chain-to-chain rotation, and place it on z at r = 0. | v0.3 |
| **FR-03** | SHALL verify the expected oligomeric state (ClyA 12, αHL 7, MspA 8) and abort on missing chains. | v0.3 |
| **FR-04** | SHALL build an ensemble-averaged density map from per-atom Gaussians whose width is tied to each atom's van der Waals radius, on a 0.25–0.5 Å grid. | v0.3 |
| **FR-05** | SHALL reduce the 3D map to (r, z) by averaging the n rotated copies before azimuthal averaging, with area-weighted binning over exact annular volumes. | v0.3 |
| **FR-06** | SHALL report residual azimuthal variance as a first-class output of every reduced geometry. | v0.3 |
| **FR-07** | SHALL extract the pore surface as a closed contour of the reduced map at a configurable isolevel, default 0.25, and condition it to a watertight, non-self-intersecting polyline. | v0.3 |
| **FR-08** | SHALL gate the conditioned contour on validity, simplicity, minimum vertex spacing, minimum local feature size, single closed loop and radius-profile agreement, aborting on failure. | v0.3 |
| **FR-09** | SHALL assemble the (r, z) region from pore contour, membrane and reservoir half-discs, fragmented for conformal interfaces, the membrane being representable as a quadrilateral with a slanted inner edge. | v0.3 |
| **FR-10** | SHALL generate a graded triangular mesh resolving the wall Debye length against the reservoir scale, isotropically by default, aborting with the worst element and its location reported when quality gates fail. | v0.3 |
| **FR-11** | MAY generate structured boundary layers along the pore wall as an element-count optimisation. | post-1.0 |
| **FR-12** | SHALL derive protonation states and partial charges at a configurable pH and force field, and record the net charge Q_net. | v0.4 |
| **FR-13** | SHALL assemble the axisymmetric fixed-charge density from per-atom Gaussians in 3D Cartesian space, averaged exactly over the azimuth and deposited on the deployed finite-element mesh with each atom's charge conserved (PHY-16 to PHY-18; WP28, §8.2.4 D2). The closed form is the limit of the exact-annular-volume construction and is regular on the axis. | v0.4 |
| **FR-14** | SHALL assert charge conservation on the deployed finite-element mesh and check per-z-slice cumulative charge against the source charge list. | v0.4 |
| **FR-15** | SHALL build the dielectric field and the ion-exclusion surface from the same density field, with independently configurable protein permittivity and exclusion offset. | v0.4 |
| **FR-16** | SHALL implement each empirical correction as a named component registered by string, its fit coefficients held in versioned data files, so a new electrolyte or surface is a data file rather than a code change. | v0.2 |
| **FR-17** | SHALL solve the steady 2D-axisymmetric ePNP-NS system across 0.005–5 M and ±200 mV with all corrections active, via a continuation ladder, without negative concentrations at any nonlinear iterate. | v0.2 |
| **FR-18** | SHALL provide physics models `ePNP-NS`, `PNP-NS`, `PNP` and `Poisson`, selected by name in the case file, `PNP-NS` being a configuration of `ePNP-NS` with corrections disabled rather than separate code. | v0.2 |
| **FR-19** | SHALL provide nonlinear Poisson–Boltzmann (`PB`) and Debye–Hückel (`PB-linear`) as separate equilibrium physics models. | v0.4 |
| **FR-20** | SHALL admit a new physics model as one implementation of a documented interface (field set, weak-form contributions, boundary-condition vocabulary, default solve strategy), with no change to the mesh, geometry, charge, sweep, provenance or interface layers. | v0.4 |
| **FR-21** | SHALL support a rigid analyte body of revolution on the pore axis, subtracted from the fluid domain and treated as a hard dielectric with no ion flux, no-slip and a dielectric jump, charged as either a surface density or a smeared volumetric charge. | v0.7 |
| **FR-22** | SHALL compute F^em(z), F^hd(z), their sum, and ΔU(z) = −∫F dz with barriers and minima in kT, over a series of axial analyte positions. | v0.7 |
| **FR-23** | SHALL extract ionic current, cation and anion transport numbers, rectification ratio and EOF rate by two independent routes whose agreement is checked automatically. | v0.2 |
| **FR-24** | SHALL sweep any case-file field, dispatch the points as independent jobs, warm-start each solve from a converged neighbour, and collect results into one dataset. | v0.2 |
| **FR-25** | SHALL emit with every result a provenance manifest recording input hashes, library versions, mesh hash, solver settings, stabilisation mode and correction parameter file versions. | v0.2 |
| **FR-26** | SHALL round-trip a case file, a written and re-read case yielding a semantically identical run configuration. | v0.2 |
| **FR-27** | SHALL make every stage independently invocable, cancellable, progress-reporting and introspectable, emitting a typed, serialisable, content-hashed artefact that may be inspected, exported, edited and substituted by hand. | v0.2 |
| **FR-28** | SHALL export figures, fields and the originating case file from a completed run. | v0.7 |
| **FR-29** | MAY perform goal-oriented (dual-weighted-residual) mesh adaptivity targeting the ionic current. | post-1.0 |

Rationale (FR-23): continuous-Galerkin fluxes are not pointwise conservative, so a current obtained
by integrating flux over an interior cross-section varies between cross-sections by amounts that
can exceed the rectification signal at low bias.

Rationale (FR-26): "semantically identical" is asserted on the content hash of the validated case
document and on the resolved run configuration it produces, never on the YAML text. A case file
written by hand omits defaults, orders keys freely and carries comments, none of which survive a
round trip and none of which change the run; requiring textual identity would test the serialiser
instead of the schema (VER-09).

NOTE (FR-05, FR-06; WP19): the n rotated copies are averaged in the
angular harmonic basis. There the average keeps the harmonics that are multiples of n, so it leaves
the azimuthal mean unchanged and defines FR-06's residual variance. The binning weights are exact
cell–annulus overlaps. The §5.3.1 NOTE on `geometry.density` is the contract.

### 3.3 Quality of service

| ID | Requirement | Class |
|---|---|---|
| **QR-01** | Tier-2 analytic benchmarks SHALL pass, including Maxwell–Hall access conductance to better than 2 % and MMS convergence at O(h³) in L² for P2 on the full coupled axisymmetric system. | Correctness |
| **QR-02** | By v0.7 (Phase 6; §8.2.5 E2, §8.2.6 F1), the current–voltage relationships and in-pore averages computed in the validated configuration on the reference inputs SHALL agree with the published ePNP-NS results within the tolerances VAL-16 and VAL-17 state. A field comparison against exported COMSOL solutions, where exports exist, SHALL agree to better than 1 % relative L² error on fields and 0.5 % on integrated QoIs once the matching stabilised mode exists and meshes are convergence-matched; it is not required. Until a comparison is gated, differences SHALL be recorded and attributed, not gated on (§8.2.4 D6). | Correctness |
| **QR-03** | Assembled fixed charge SHALL be conserved to better than 0.1 % of Q_net on the deployed mesh. | Correctness |
| **QR-04** | The two current-extraction routes of FR-23 SHALL agree within a stated tolerance, checked in CI. | Correctness |
| **QR-05** | End-to-end reproduction of published conductance, transport-number and rectification data SHALL agree with experiment no worse than the source work's own agreement with experiment. | Correctness |
| **QR-06** | A full-envelope sweep of 3,675 solves SHOULD complete within a day-scale wall-clock time on 12 cores, throughput scaling linearly with the number of independent workers. | Performance |
| **QR-07** | A sparse direct factorisation of a production-sized problem (about 1.2 × 10⁵ cells, five fields) SHALL complete in acceptable time and memory on a laptop. | Performance |
| **QR-08** | Re-running a case file with the recorded library versions SHALL reproduce every scalar QoI to within the solver tolerance, the FR-25 manifest sufficing to reconstruct the run. | Reproducibility |
| **QR-09** | SHALL install from binary wheels on Windows, macOS and Linux for Python 3.11–3.14, with no compilation on the target machine (§8.2.2 B4). | Portability |
| **QR-10** | A nanopore experimentalist without Python knowledge SHALL be able to load a structure, accept defaults and obtain a conductance prediction and a field visualisation in the desktop application unaided. | Usability |
| **QR-11** | Each release from v0.2 onward SHALL ship a usable graphical surface over the functionality existing at that release. | Usability |
| **QR-12** | Every automatic gate failure SHALL abort the run with a diagnostic naming the gate, the offending quantity and its location. | Usability |
| **QR-13** | The ePNP-NS weak forms SHALL be expressed once and SHALL NOT be duplicated per backend. Until a second backend is planned they are expressed against NGSolve directly, and the subpackages that import NGSolve or Netgen SHALL stay within a recorded set, which may shrink and grows only by the author's ruling (§5.4.1 NOTE; §8.2.8 H3). | Maintainability |
| **QR-14** | Adding a correction parameterisation SHALL require only a data file; adding a physics model SHALL require only one class (FR-20); adding a mesher, a linear solver or a stabilisation mode SHALL require only a registration, with no file of the package edited (§5.5; §8.2.8 H7). | Maintainability |
| **QR-15** | v0.7 (Phase 6; §8.2.5 E2, §8.2.6 F1) SHALL ship user documentation, tutorials, a JOSS submission and a DOI-archived release. | Maintainability |

NOTE (QR-15): the user documentation and the worked examples are
delivered incrementally from v0.2, by the documentation track of §8.1, each phase documenting what
it ships. The requirement itself is unchanged. v0.7, the Phase 6 release (§8.2.5 E2, §8.2.6 F1), is where it is met in full, including the JOSS
submission and the DOI-archived release, which no earlier phase delivers. VER-45 and VER-46
demonstrate the documentation part at every release. They do not demonstrate the JOSS or DOI parts.

Rationale (QR-02): the reference implementation uses linear velocity and pressure on a mesh from a
different generator with stabilisation active, so two correct codes disagree at the per-cent level
until those differences are matched. The comparison against the published results is the one a
user relies on, because those are the numbers the model is cited for. It needs no licence and no
export, and its reference cannot lapse. It localises a discrepancy less well than a field
comparison would, which is why the Tier-2 benchmarks, which localise to a single term, come first
(§7.1).

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
| **CON-09** | The core library SHALL be licensed BSD-3-Clause. LGPL dependencies are acceptable under dynamic linking (NGSolve/Netgen LGPL-2.1, MDAnalysis LGPLv3, PROPKA LGPL-2.1, PySide6 LGPL-3). MPL-2.0 dependencies are acceptable used unmodified as separate packages (gemmi, the mmCIF reader of the `structure` extra). The field viewer's renderer, npm `webgui` (LGPL-2.1-or-later, bundling three.js under MIT and dat.gui under Apache-2.0), MAY be redistributed with the package, **unmodified and as a separate file** loaded at run time, beside its licence texts and a notice naming its corresponding source, which the repository and the source distribution carry verbatim; nothing in the library SHALL be linked against it. PyQt SHALL NOT be used, being GPL-3 or commercial only. |
| **CON-10** | Gmsh (GPLv2+) SHALL be an optional backend only; the default path SHALL NOT link Gmsh, and the core library SHALL remain functional without it. |
| **CON-11** | SuiteSparse UMFPACK is GPL-2+, so a bundle defaulting to UMFPACK carries GPL obligations even though the library does not. The core library SHALL remain BSD-3 and SHALL NOT itself depend on UMFPACK; the redistributable bundle SHALL default to UMFPACK, SHALL be distributed under the resulting GPL-2+ obligations and SHALL state them in its licence notice, scipy SuperLU remaining selectable at runtime. The default follows the §6.6 measurement: SuperLU did not factorise the reference-sized problem at all, so a SuperLU-default bundle could not run the published case. |
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
| 4 | Per-atom smearing | normalised 3D Cartesian Gaussian `ρ_i(x) = q_i e π^(−3/2) w_i^(−3) exp(−\|x − x_i\|²/w_i²)`, width `w_i = 0.5 · R_i` (`R_i` from the PQR) |
| 5 | Azimuthal projection | the exact azimuthal mean of step 4, in closed form: `ρ̄_i(r, z) = q_i e π^(−3/2) w_i^(−3) exp(−((r − r_i)² + (z − z_i)²)/w_i²) · Ĩ₀(2 r r_i/w_i²)`, with `Ĩ₀(x) = e^(−x) I₀(x)` and `r_i = (x_i² + y_i²)^(1/2)`; summed over the atoms and averaged over the frames. The Cₙ average is contained in the azimuthal mean |
| 6 | Assembly | `ρ_pore = Σ_i ρ̄_i`, deposited onto an element-wise field on the deployed mesh by `r`-weighted L² projection, each atom's element integrals renormalised to `q_i e` (PHY-18). The areal density `2πr ρ_pore`, sampled on a 0.005 nm (r, z) grid extending ≥ 4 w_max beyond the protein, is the exported artefact and the producer leg's grid. A supplied areal density keeps the reference's assembly, `scd_pore = if(r < 0.01[nm], 0, e_const * rhoq_pore(r,z) / (2*π*r))` [C m⁻³] |
| 7 | Conservation check | `\|∫ρ_pore · 2πr dr dz − Q_net\| / \|Q_net\| < 10⁻³` |

NOTE (PHY-16 steps 4–6; §8.2.4 D2): smearing each atom on a 3D grid at 0.005 nm and binning the
grid to (r, z) by exact annular volume is not what the pipeline does. The closed form of step 5 is
that construction's limit as the spacing goes to zero, without its cost, which would be about 10¹³
voxel updates for the 50-frame ClyA ensemble. Step 6 deposits onto the
deployed mesh rather than sampling a grid there, which removes the aliasing of the consumer leg
that the §4.4 NOTE measures on the delivered table. The reference built its table from a 2D Gaussian
in (r, z) divided by `2πr` at the field point (`.knowledge/04` §3, gap G4). PHY-17 forbids that
construction, so it is not reproduced. Off the axis the two carry the same charge and the same
z-marginal, and differ pointwise by `(r − r_i)/(2 r_i)` of the local value: first order in
`w_i/r_i` and odd about the atom, so the 3D construction's radial centroid lies `w_i²/(4 r_i)`
further out (`.knowledge/04` §3.3 [tested]). The difference on the ClyA
ensemble is measured at Tier 3 rather than accommodated.

NOTE (PHY-16 step 3, protonation as run; WP27): PDB2PQR SHALL be run
once per selected frame (§8.2.4 D4) on that frame's heavy atoms, with every hydrogen and every water
removed (PDB2PQR 3.7.1's `--drop-water` drops only `HOH` and `WAT`; WP27
review) and every protonation-variant residue name (`HSD`, `HSE`, `HSP`, `HID`, `HIE`, `HIP`, `ASH`, `ASPP`,
`GLH`, `GLUP`, `LYN`, `LSN`, `CYM`, `TYM`, `ARN`) written as its titratable parent, so that the
states are PROPKA's at the case's pH and not the source file's. The disulfide name `CYX`, which
PDB2PQR writes under `SWANSON` and `PEOEPB`, is read as `CYS` the same way (WP27 review: without it every disulfide-bonded cysteine named a residue the ensemble does
not hold). PDB2PQR 3.7.1 treats `HSD` and
`HSE` as fixed residues that PROPKA does not titrate, and refuses `HSE` with its hydrogens present,
so a CHARMM-named MD frame passed through verbatim would pin every histidine. The reference passed
its frames verbatim to PDB2PQR 2.1.1, and its PQRs keep `HSE`; the difference is measured at Tier 3
rather than reproduced. Under CHARMM, PDB2PQR cannot represent a neutral terminus, `CYS⁻`, `LYS⁰`,
`TYR⁻` or `ARG⁰`, and keeps the standard state where PROPKA prefers one of these; it never applies
PROPKA's terminal pKa at all. Every such residue SHALL be recorded per frame as an unapplied state,
derived by comparing each residue's applied charge with the sum of PROPKA's group states at the pH,
never parsed from log text. On 2WCD at pH 7.5 these are `CYS 285` (pKa 6.25) in every chain, and
the N-terminus of `LYS 8` wherever its pKa, 7.48 to 7.50 across the chains, falls below the pH. They are the validated model's states, so they are recorded and
not gated. The protonation states of the chains of a homo-oligomer are not symmetrised: a residue
whose charge differs between chains of identical sequence is recorded as a per-chain diagnostic.

NOTE (PHY-16 steps 4–6, the deposition as run; WP28): the closed form of
step 5 SHALL be evaluated on the export lattice of step 6, whose spacing is
`charge.smearing.grid_spacing_nm` and which carries a node on `r = 0`. Each atom's kernel is cut
to a patch of half-width `6 w_i` about it in `r` and `z`, which leaves out `1 − erf(6)² =
4.3 × 10⁻¹⁷` of its charge. Its trapezoid sum on the lattice is then renormalised to `q_i e`, divided
by the number of frames. That renormalisation is PHY-18's: on the lattice the sum is exact to
10⁻¹⁵ off the axis, but an atom within a few `w_i` of the axis is short by `h²/(6 w_i²)`
(`.knowledge/04` §3.3). A spacing above half the smallest `w_i` of a charged atom SHALL be refused
naming that atom. The lattice and the atoms are in the model frame, `z ← z −
geometry.membrane.centre_z_nm` when the case generates its mesh, as stage 5 moves the profile, and
unshifted beside a supplied mesh. Atoms of zero charge are not deposited. The `r`-weighted L²
projection of step 6 is onto discontinuous polynomials of the potential's element order on each
triangle, with its integrals taken by the lattice's trapezoid rule, each node counted in the one
element containing it. Every test function of the potential's space is a polynomial of that order on
each element, so the assembled source equals the lattice integral of the kernel against every test
function, and the projection adds no error of its own. The charge is deposited on every material, as
the reference applied `ρ_pore` across all computational domains (`.knowledge/04` §3). The deposit
SHALL be refused, naming the quantity and its location (QR-12), where lattice charge falls on no
element of the mesh, or where less than half of `Σ|q_i|` has its atom centres in solid materials,
which is how a structure in another frame than its mesh shows.

**PHY-17.** Smearing SHALL be performed in 3D Cartesian space and only then averaged azimuthally.
A Gaussian applied directly in (r, z) leaks charge across `r = 0` and SHALL NOT be used.

**PHY-18.** Where an areal density is converted to a volume density, as for a supplied
`areal_charge_density` (§5.3.1 NOTE on `inputs.charge`), the conversion SHALL carry the
`1/(2π r)` factor and the axis guard `r < 0.01 nm → 0` of the reference model. The closed form of
PHY-16 step 5 is a volume density, regular on the axis, and needs neither. Deposition SHALL
conserve charge by renormalising each atom's kernel to `q_i e` on the deployed mesh
(§8.2.4 D2). The quintic B-spline partition of unity, the other
option this clause first named, belongs to a Cartesian grid, and the producer no longer builds one.

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

The two branches of the blend SHALL be evaluated where they have a meaning (author ruling 13). `⟨c⟩` has no meaning inside a solid, because ions do not exist
there in the model, so `ε_r,f(⟨c⟩)` SHALL be evaluated only in the fluid materials; the water share
of the blend inside a solid material, and in the ion-exclusion shell, is ion-free water, `ε_r,f⁰`.
`ε_p` is the element's own solid permittivity inside a solid material and, where the 1–2 Å
transition reaches past the mesh boundary into the fluid or the shell, the permittivity of the
nearest solid material, whose solid fraction `χ` there is. A single `ε_p` for the whole field would
blend the fluid beside the membrane towards the protein. With `χ` the sharp material indicator every
one of these choices drops out, and PHY-20's piecewise assignment is recovered exactly.

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

NOTE (the producer path's conservation report, PHY-19, FR-14, QR-03; WP28): for a deposited charge, the producer leg compares the trapezoid integral of the exported
lattice with `Q_net`, the mean over frames of `Σ q_i`. The consumer leg compares the deployed field,
integrated at the solve's order, with the lattice. Both are exact by construction, the first by
per-atom renormalisation and the second because each element carries its lattice charge, so they
guard the construction and SHALL be shown to fail on a broken one. The discriminating check is the
per-plane one, and PHY-19 names its reference: **the source atoms**, not the lattice. Azimuthal
averaging keeps each atom's z-marginal, a Gaussian of variance `w_i²/2`, so under the weight
`½ erfc((z − p)/s)` atom `i` contributes `q_i · ½ erfc((z_i − p)/√(s² + w_i²))` below plane `p`
exactly. On this path the weight SHALL be that Gaussian-smoothed step, with `s = 0.5 nm`, and both
the lattice and the deployed field SHALL agree with the atoms at every plane to QR-03's tolerance.
The consumer path keeps its linear ramp. The smoothed weight is Lipschitz, as the NOTE above
requires, and smooth: a polynomial of the deposit's order approximates it to about `0.064 h³ |W'''|`
on an element of size `h`, `6 × 10⁻⁴` on ClyA's 0.1 nm protein elements. A 0.2 nm ramp's kinks
leave `h/(16 s) = 0.03` there, which is too little margin for a gate meant to discriminate. The
planes span the atoms' z-extent. The guard deficit the exported lattice would suffer if re-read
through `inputs.charge` is recorded beside the legs.

NOTE (the derived solid fraction, FR-15, PHY-20; WP30): a non-zero
`charge.dielectric_transition_nm`, `δ`, makes stage 7 derive `χ` from the stage-4 profile as stage 5
placed it in the model frame. Let `W` be the profile's water-facing part, meaning its edges, split
at the bilayer planes, whose outward side is not membrane. Let `s` be the distance to `W`, positive
inside the body and negative outside. Then

```
χ = S(s/δ + 1/2),   S(x) = 3x² − 2x³ on [0, 1],  0 below it,  1 above it
```

which is C¹, is exactly `1/2` on `W`, and changes only where `|s| < δ/2`. On every solid material
other than `protein` `χ` SHALL be 1, because the membrane is analytic and not drawn from the
density, and its interface stays sharp. `χ` is built from the profile and not by remapping the
stage-3 mean. The mesh's material interface is the conditioned profile, and conditioning moves it
off the raw isolevel by up to the closing radius. A remap would put its 1/2-level on that isolevel
and give it a width that varies with `|∇ρ|`. The limit δ → 0 of the profile's `χ` is the material
indicator, and therefore PHY-20's piecewise assignment exactly. FR-15's "same density field" holds
because the shell is offset from the same profile (§5.2.1 NOTE on the ion-exclusion shell).

`χ` is sampled at the nodes of a lattice of spacing `δ/20` and read bilinearly, as a supplied field
is. The lattice covers the body's bounding box widened by `δ` and clipped at `r = 0`, so its
boundary samples are 0 by construction. Away from the profile's vertices the interpolation error is
then at most `0.75 (h/δ)² = 1.9 × 10⁻³` (WP30 plan, *Design* §1). A `δ` below
`geometry.density.grid_spacing_nm` would be finer than the grid the contour is placed on, and SHALL
be refused naming both keys.

VER-30's range and registration gates apply, with one amendment that holds for every `χ`, supplied
or derived. `exclusion` lies wholly on the water side of the dielectric contour, so its mean `χ`
SHALL be below 1/2. The fluid ceiling does not apply to it, because a 1–2 Å transition into a thin
shell exceeds that ceiling: a planar shell of width `a` averages `3δ/(32a)`.

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

NOTE (the electrostatic models as case-file models, PHY-20, PHY-24, FR-19, FR-20; WP26): `poisson` solves `∇·(ε_0 ε_r ∇φ) = −ρ_pore` over all of Ω, with the fixed
charge, `physics.solid_permittivities` and the §4.4 `χ` taken as the coupled models take them. It
carries no mobile ions, so the fluid is ion-free water at `ε_r,f⁰` whatever the permittivity
correction (author ruling 13), and `ρ_ion` is none: case schema v2 has no key that prescribes one.
This is the configuration VAL-06 compares with APBS. `pb` and `pb-linear` take `λ_D` from the case,
at `ε_r,f⁰`, the case temperature and `c_0` with unit valence (NUM-09), and SHALL be refused for any
electrolyte other than a symmetric monovalent salt, for which that `λ_D` and the `sinh` form are
exact. They carry no solids, no fixed charge and no `χ`: their screening term is posed on all of Ω,
so a solid domain would screen as if it held ions. They are therefore run only on a mesh with no
solid domain, and an ingested mesh that carries one SHALL be refused naming the model and the
domain (§5.3.1 NOTE on a solid without a permittivity).

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
| `numerics/` | Linear-solver adapters, damped Newton, the state and increment gates, the axisymmetric measure (§8.2.8 H11) |
| `charge/` | PDB2PQR driver, partial charges, smearing, axisymmetric projection, dielectric |
| `materials/` | Electrolyte models and the pluggable correction registry |
| `physics/` | Weak forms: Poisson, Nernst–Planck, Navier–Stokes; the wall-distance field |
| `solve/` | Continuation ladder, warm start, the solve stage |
| `post/` | QoI extraction: current, transport number, EOF, rectification, forces |
| `sweep/` | Parameter sweeps, job-array dispatch, result collection |
| `io/` | Case-file schema, artefact and resolved-case types, the solution-field vocabulary, result store, provenance manifests: the base every stage imports, importing only `core` at run time (`MOD-04`; WP38) |
| `pipeline/` | Case resolution and the checks against the registries, the pipeline walk, reproduction: the assembler, which imports the stages (`MOD-04`; WP38) |
| `cli/` | Command-line entry points |
| `gui/` | Desktop application |
| `validation/` | Benchmarks, MMS, COMSOL comparison harness, regression fixtures |

### 5.2 Pipeline stages

| # | Stage | Inputs | Outputs | Tools | Validation gate |
|---|---|---|---|---|---|
| 1 | Structure ingestion and alignment | PDB/mmCIF, optional trajectory, expected point group | Aligned ensemble; Cₙ axis on z at r = 0 | MDAnalysis 2.10+ (LGPLv3) for PDB and every trajectory format; gemmi 0.7+ (MPL-2.0) for mmCIF, which MDAnalysis 2.10 does not read; the Kabsch rotation for superposition, cross-checked against MDAnalysis `rotation_matrix`; MDTraj as alternative reader; PDBFixer or Modeller for missing loops | Oligomeric state matches (ClyA 12, αHL 7, MspA 8); abort on missing chains (FR-03) |
| 2 | Density map | Aligned ensemble, grid spacing, kernel | 3D density map | Vectorised numpy Gaussian deposition over a spherical stencil truncated at 10⁻⁶, per-atom width σR_i from the CHARMM radius set of the §5.3.1 NOTE on `geometry.density`, sharpness 0.93; `gridData` IO. MDAnalysis `DensityAnalysis` is histogram-only and is not used (WP19) | Grid spacing 0.25–0.5 Å (FR-04); every atom has a radius; the map is finite and within [0, 1] |
| 3 | Symmetry reduction to (r, z) | 3D map, n | (r, z) map; residual azimuthal variance, Cₙ-averaged and raw | numpy and `scipy.sparse`; exact cell–annulus overlap weights; the Cₙ average in the angular harmonic basis (WP19) | Variance emitted with the geometry (FR-06, CON-04); annular weights summing to the exact annulus areas. The radius profile against the probe-radius profile is stage 4's gate (§5.2.1, §8.2.2 B5) |
| 4 | Contour extraction and conditioning | Stage 3's (r, z) mean; the aligned ensemble and its radius set, for the probe-radius profile; isolevel, smoothing and simplification tolerance | Closed conditioned polyline, a `nanopnp/profile/v1` document | scikit-image, Shapely (both BSD-3) and numpy, per §5.2.1 (WP20) | §5.2.1 (FR-08) |
| 5 | CAD assembly | Stage 4's polyline or a supplied `inputs.profile`, membrane specification with its `centre_z_nm` shift, reservoir radius, optional analyte | Fragmented (r, z) region, domains and boundaries tagged, as a declarative region record | `netgen.occ` (LGPL-2.1, OpenCASCADE, in-process). The optional Gmsh backend meshes this region at stage 6 and assembles none of its own (WP23 D1) | All bodies fragmented and imprinted, interfaces conformal, no gap or overlap at the membrane-to-pore junction, each domain one face, the membrane's inner edge strictly inside the body (FR-09, WP21; §5.2.1 NOTE on the membrane junction on any profile) |
| 6 | Meshing | Fragmented region, size fields | Graded triangular mesh | Netgen (LGPL-2.1) default, Gmsh (GPLv2+) optional, behind the mesh adapter | §5.2.2 (FR-10, QR-12): the VER-10 and VER-27 gates, as on an ingested mesh, and the wall-size gate of the §5.3.1 NOTE on `numerics.mesh` (WP21) |
| 7 | Protonation (`protonation`) | Stage 1's aligned ensemble, pH, force field, titration method; or a supplied `inputs.pqr` | Per-frame atom table in stage 1's frame (identity, coordinates, charge, radius), `Q_net` and every titratable residue's state per frame | PDB2PQR 3.7+ (BSD-3) driving PROPKA 3 (LGPL-2.1), one call per frame with the flags of PHY-16 step 3 (WP27) | Every atom carries a charge and a radius, and every charged atom a positive radius; `Q_net` an integer to 10⁻⁶ e on every frame; a supplied frame registered to its stage-1 frame to 0.01 Å (§5.3.1 NOTE on `inputs:`) |
| 7 | Charge assembly (`charge`) | The protonation artefact, **and the deployed mesh** (its gate is evaluated there, PHY-19); on the consumer path, a supplied field document instead | ρ_pore(r, z), Q_net, dielectric field, ion-exclusion surface | The closed-form azimuthal kernel deposited on the deployed mesh (PHY-16, §8.2.4 D2); APBS 3.4.1 (BSD-3) cross-check through the test-only `apbs-binary` package; settings per PHY-16 | Charge conservation to 10⁻³ of Q_net on the deployed FE mesh, plus the per-z-slice cumulative check (FR-14, QR-03, PHY-19) |
| 8 | Materials | Electrolyte specification, correction model names, coefficient files | D_i, μ_i, η, ϱ, ε_r as fields in ⟨c⟩ and d | Correction registry, `data/corrections/willems2020_nacl.yaml` | Conformance values of §4.3 reproduced; clamps above 5.3 M logged with location and property (PHY-13) |
| 9 | Case assembly | Mesh, charge and dielectric fields, materials, boundary conditions, bias, analyte, numerics | Resolved case document, assembled discrete problem | `io/` schema validator, `physics/` model registry | Schema `nanopnp/case/v2` validates, a v1 document upgraded losslessly, unknown keys rejected with a diagnostic naming the key (IF-03); round trip semantically identical (FR-26) |
| 10 | Solve | Assembled problem, continuation ladder, optional warm start | Converged fields, iteration history | NGSolve 6.2.2606+ (LGPL-2.1), damped Newton; UMFPACK (GPL-2+) or scipy SuperLU (BSD) (CON-08) | No negative concentration at any nonlinear iterate; ladder completed to the target rung (FR-17); §6.5, §6.6 govern |
| 11 | QoI extraction | Converged fields | I, t₊, RR, EOF rate, F^em(z), F^hd(z), ΔU(z) | Domain/indicator form and variational reaction flux, both implemented | The two routes agree within the stated tolerance, checked in CI (FR-23, QR-04); §6.7 governs |
| 12 | Reporting and export | Results, artefact hashes, environment | Figures, XDMF/HDF5 fields, dataset, case file, manifest | `io/`, `sweep/` result store | Manifest complete and sufficient to reconstruct the run (FR-25, QR-08) |

Design notes, recorded where an implementer would otherwise choose wrongly.

| Stage | Note |
|---|---|
| 1 | The Cₙ axis comes from chain-permutation superposition: superpose chain A onto chain B, take the rotation's eigenvector of eigenvalue 1 (FR-02). Principal axes are unusable because they drift between frames. Over the 98 frames of the ClyA-AS ensemble, the largest-variance axis of the Cα set moved by up to 1.54° (rms 0.66°), while the chain-permutation axis moved by at most 0.010°. The cause is not degeneracy: the axial eigenvalue is well separated (1432 Å² against 801 and 881 Å² on the first frame). It is the chains' asymmetric fluctuation, which the permutation fit averages out by construction (measured; WP18 plan, Design §4). Stage 1 is specified in full in the §5.3.1 NOTE on `structure:`. |
| 2 | Histogram plus uniform `gaussian_filter` is rejected: van der Waals-weighted smearing preserves the exclusion surface, uniform post-smoothing rounds the constriction. The grid is not coarsened, the *trans* constriction being about 3.3 nm across with a contour position that moves measurably with resolution. |
| 3 | The n rotated copies are averaged before azimuthal averaging. Binning is area-weighted over exact annular volumes (about 6 cells per annulus of width h at r = h, about 630 at r = 5 nm, per slice at h = 0.05 nm). The overlap weights are exact, so no bin is interpolated (WP19 plan, Design §2–§3). The earlier "innermost 2–3 bins interpolated" compensated for centre-assigned binning, and against exact weights every interpolant tried was worse somewhere. The rotated copies are averaged in the angular harmonic basis, where the average keeps the harmonics m ≡ 0 (mod n): it is exact and costs one deposition. Depositing n rotated copies costs n, and rotating the voxel map by interpolation smooths it, lowering the peak Cₙ variance of a C12 ring by 3–6 %. The binned mean is subtracted at each cell's own radius before any variance is taken, or the radial gradient across a bin reads as azimuthal variance. A 1° axis error adds about 0.2 nm of apparent radius to a 3.3 nm constriction. |
| 3, 5 | The bilayer is absent from the density map. It is defined analytically in (r, z) over the hydrophobic belt and fragmented against the pore contour. |
| 5 | Reference geometry: reservoir half-disc R = 250 nm, membrane thickness 2.8 nm, `z_cis` = 12.25 nm, `z_trans` = −1.85 nm. The membrane is a quadrilateral, not a rectangle: vertices (r = 2, z = −1.4), (3.5, +1.4), (250, +1.4), (250, −1.4) nm, inner edge slanted to meet the pore's outer surface. Code assuming a rectangle leaves a wedge of gap or overlap at the junction. CadQuery and build123d are 3D-solid-centric and unused; pythonocc serves BRep edge cases only. |
| 7 | Stage 7 is two registered stages, `protonation` and then `charge`, sharing the number so that stages 8 to 12, which this specification, the CLI's output and every recorded manifest cite by number, do not move (WP27). The registry lists stages by number and then in registration order. A run walks `protonation` after `mesh` and immediately before `charge`, so a walk truncated at the mesh, as the desktop shell's geometry build is, never protonates; protonating an ensemble costs about a minute per frame of a ClyA dodecamer (WP27 plan, *Design* §1). Both halves run when the case has something to protonate (`structure:` or `inputs.pqr`, and no `inputs.charge`) and its model declares a fixed charge (§5.4.3), and are otherwise recorded as not run with the reason. A consumer of a deposited charge reads it from stage 7's artefact and from nowhere else (WP28). With a non-zero `charge.dielectric_transition_nm` the `charge` half also runs, reading stage 5's record, to derive `χ` (§4.4 NOTE on the derived solid fraction), whether or not it deposits a charge; the solve reads that `χ` from stage 7's artefact likewise (WP30). |

#### 5.2.1 Contour conditioning and its gate

Pipeline (WP20):

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

NOTE (the contour's size target, WP20): `h_c`, the "target element
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

NOTE (the radius band, WP20): the lower bound is geometric. Inside
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

NOTE (the membrane junction on any profile, stage 5, FR-09; WP21): the
profile is first moved into the model frame, `z ← z − geometry.membrane.centre_z_nm`. On each plane
`z = ±t/2` the **lumen-adjacent body interval** `[r₁, r₂]` is bounded by the profile's two
smallest crossings of that plane, an edge crossing it when `lower ≤ z < upper`. Where an edge of
the profile lies exactly on the plane, `r₂` runs on to that edge's far end, because the body's
section continues along it and the membrane meets the body there (CODE_REVIEW_003 CR-4; without it a valid step flush with a bilayer plane was refused by the
junction criterion below). The inner edge of the membrane quadrilateral is the chord from
the lower plane's interval to the upper plane's that has the largest minimum distance to the
profile. It is searched on the 63 × 63 interior points `r₁ + (r₂ − r₁)k/64` of the two intervals.
Any chord with its ends in those intervals that lies inside the body yields the same region: a
fluid pocket between two such chords would be enclosed by them, by the body and by the plane
segments between their ends, which are body too, while the complement of a simple polygon is
connected. The widest-margin chord is taken because it is the choice furthest from failure. The
chord between the intervals' mid-points is **not** admissible in general. On the delivered fixture
it runs from (2.2387, −1.4) to (3.92, +1.4) and crosses the cleft under the cap between
(3.070, −0.016) and (3.235, 0.260), which splits the electrolyte in two. On the fixture the
widest-margin chord is (1.982, 3.470) nm, with a clearance of 0.236 nm (WP21: the plan's prototype printed 3.464, a grid point the search does not visit). A plane
that crosses the profile more than twice always splits a domain, and the one-face criterion below
refuses it. The gap between the first two body intervals on the plane is a segment of fluid
bounded by body at both ends. The body arms on either side of it join above the plane or below
it, because the profile is one simple polygon. If they join above, the fluid over the gap is
enclosed by body and the gap, and is a second electrolyte face. If they join below, the pocket
under the gap is enclosed alike: bilayer where it lies in the slab, a second membrane face, and
electrolyte where it reaches past the other plane (WP21 Outcomes, [verified]). Stage 5 SHALL abort,
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

NOTE (the ion-exclusion shell, stage 5, FR-15, PHY-20; WP30): a non-zero
`charge.exclusion_offset_nm`, `a`, makes stage 5 build the exclusion contour from the model-frame
profile `P`, with `h_c` as in the NOTE on the contour's size target:

1. `O` is the dilation of `P` by `a`, with round joins at 8 segments per quarter circle (WP20 D5).
2. `O` is closed by a disc of radius `2h_c`, as in step 3 of §5.2.1 and for the same reason.
3. Every hole of `O` is filled and recorded with its centroid and area. A hole is fluid enclosed by
   the shell, which no ion can reach.
4. `O`'s ring is resampled at uniform arc length `L/⌊L/(1.05 h_c)⌋`, and step 6 of §5.2.1 runs on
   it (WP30 Outcomes; see below).
5. §5.2.1's validity, simplicity and spacing criteria are applied to that ring, together with its
   clearance of `h_c` from the axis.

The shell is `O − P − M` and the electrolyte is `D − M − O`, where `M` is the membrane quadrilateral
and `D` is the reservoir disc. The membrane, its chord and its junction are unchanged. The shell
SHALL be one face. It runs from the membrane's upper face round the cap, down the lumen, and round
the *trans* end to the membrane's lower face. Its outer surface, against the electrolyte, is `wall`.
The no-slip surface, the no-flux surface and the PHY-02 distance source therefore move there, with
no change to `numerics.wall_distance.sources`. The shell's seams with the protein and with the
membrane are `interface`. The outer surface lies at most `max(h_c²/a, a/100)` inside the exact
offset (0.01 nm at `a` = 0.25 nm), and stage 5 gates that on every edge of the ring. Away from the
closing and the filled holes it never lies more than 10⁻⁶ nm outside the exact offset (WP30 plan,
*Design* §2). The `exclusion` domain is meshed at the wall size. On netgen, each `wall` edge of the
shell, of length `L`, is cut into `n = ⌈L/(1.1 h_wall)⌉` equal segments by a size of `L/n` where
`n > 1`, and keeps `h_wall` where `n = 1`; Gmsh needs no such rule (WP30 review; see below).

The resampling of step 4 is what makes the bound hold, and its argument is this. A ring at least
`2πa > 4πh_c` long is cut into at least 11 arcs, so each chord `s` is below `1.15 h_c` and above
`h_c`, and step 6 removes nothing. A chord then lies at most `a(1 − cos(π/32)) + s²/(8a)` inside
the offset, the round join's own sagitta plus the chord's. That is at most 0.62 of the bound for
every `a` [verified], and measured 0.16–0.53 of it on four bodies and nine offsets from 0.11 to
2 nm [tested]. WP30 Outcomes. Without the resampling, the bound was
first argued as twice the sagitta of the longest chord, on the premise that step 6 leaves no
round-join chord longer than `2h_c`. That premise is false. At 8 segments a quarter circle's
chords are `aπ/16`, 0.049 nm at `a` = 0.25 nm, and step 6 merges runs of them into chords near
`3h_c`. The surface then reached 0.0106 nm inside the offset on a rectangle at `a` = 0.25 nm, which
the gate refused [tested]. The resampling length is held near `h_c` because netgen meshes an edge of
1.5 times its size target as one segment, which the wall-size gate refuses at the default wall
target of 0.05 nm [tested].

The same rounding is why stage 6 divides the shell's `wall` edges (WP30
review). Netgen must keep a node at each end of every ring edge, and given only `h_wall` it cuts an
edge into about `⌊L/h_wall + 0.4⌋` segments [tested]. With ring edges of 1.05–1.15 `h_c`, every wall
target a little under `L`, or under `L/2`, therefore left segments up to 1.6 times it. On 2WCD at
`a` = 0.25 nm the gate refused 0.045, 0.04, 0.035 and 0.0225 nm, which `auto` reaches between about
1.5 and 1.9 M and at 3 M, while 0.05, 0.03 and 0.0272 nm passed [tested]. A shell-free profile is
not affected: after step 6 its edges are long (2WCD's median is 0.22 nm), and it passed at every
one of those targets. `⌈L/(1.1 h_wall)⌉` fixes the count whatever netgen's rounding, so the
segments average at most 1.1 times the target, under the gate's 1.15. An edge needing one segment
keeps `h_wall`, so the mesh is unchanged wherever no edge needed dividing, as at the 0.05 nm default
on 2WCD. Gmsh already cuts each edge into `⌈L/h_wall⌉` segments, and passed at every target [tested].
Two alternatives were measured and set aside. The shell's outer surface as one spline through the
ring passed every target too, but bulges past `a + 10⁻⁶` nm between its vertices, and the `geo`
kernel of the Gmsh backend cannot reproduce OCC's curve. An exact OCC offset of the body cannot be
built through netgen's interface whenever the dilation encloses a pocket, which step 3 requires.

Stage 5 SHALL abort, naming the criterion, the value, the threshold and the (r, z), on any of these:

- an offset that comes within `h_c` of the axis and so closes the constriction, naming the z
  interval and the body's least radius over it;
- an offset vertex that is not strictly inside the reservoir disc;
- an edge of the outer surface closer to the body than `a − max(h_c²/a, a/100)`, naming its
  midpoint;
- a domain assembled as other than one face.

`0 < a ≤ 2h_c` SHALL be refused naming both keys. The shell is a face of width `a`, and §5.2.1's
feature-size criterion admits nothing narrower than `2h_c`. The construction reads Shapely, which
is in the `structure` extra. Without the extra, the case SHALL be refused naming the extra and the
key. The record carries the offset loop, so stage 6 rebuilds the region without Shapely. With
`a = 0` none of this NOTE runs, and the record, its key and the mesh are those of §5.2.1.

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

DECISION (the author): **the delivered 185-vertex table is the geometry of
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
SICN/gamma > 0.3, the mesher's own optimisation pass (netgen's `optsteps2d` 5, Gmsh's
`Mesh.Smoothing` 5; WP23 D5), worst element and its location
reported, run aborted on failure (QR-12).

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

NOTE (the Gmsh backend's size field; FR-10, CON-10; WP23): the Gmsh
backend meshes the region stage 5 assembled, never one of its own. It applies the table above
through the classification netgen's sizes use. Gmsh has nothing like netgen's built-in restriction
of the element size by edge length and by the proximity of close edges. It does not grade outwards
from a domain's size either. Given the table alone it clears the quality gate on the reference
fixture at a minimum gamma of 0.3143 and fails it at `size_scale` 2 and 4 (WP23 plan, Design §2).
The backend therefore states those restrictions as size fields. Each is graded outwards as
`h + 0.2 d`, 0.2 being the constant netgen is given as its grading:

- every sized boundary (`wall`, the reservoir arc, the axis inside the pore) is a source at its
  size;
- the boundary of every sized domain is a source at the domain's size, the domain being held to
  that size inside;
- each vertex whose shortest incident curve is shorter than the smallest target of its incident
  curves is a source at that curve's length;
- the membrane is a sized domain at its own thickness, not multiplied by `size_scale`, because it is
  a feature of the geometry and not an entry of the table.

None of these touches a netgen mesh, which already meets them. On the fixture, the WP22 frozen case
gives conductances 1.25e-4 apart on the two backends' meshes at `size_scale` 2. Refining netgen to
`size_scale` 1 moves its own value by 2.0e-4 (WP23 plan, Design §4).

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

NOTE (`nanopnp/case/v2`, and reading a v1 document; §8.2.2 B3): the
schema moved once, carrying every key Phases 2 and 3 are foreseen to need. Against v1 it **adds**
`inputs.profile`, `inputs.pqr`, `structure.source.selection`, `geometry.membrane.centre_z_nm`,
`charge.exclusion_offset_nm`, `charge.dielectric_transition_nm` and `numerics.mesh.size_scale`;
**renames** `structure.source.pdb` to `structure.source.path`, since IF-04 reads mmCIF as well; and
**removes** `charge.eps_protein` and `geometry.membrane.eps_r`, whose values
`physics.solid_permittivities` already carries. A permittivity set in two places is a calibration
parameter (PHY-20) with two sources of truth, and a default of 20 or 3.2 written in code would be a
fitted parameter hard-coded in Python; the author ruled that the map is the one
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

NOTE (the v2 keys that change a number): `charge.exclusion_offset_nm`
and `charge.dielectric_transition_nm` are the fitted exclusion offset of FR-15 and the width of
PHY-20's transition to `ε_w`. Both SHALL be non-negative, and both are switches whose validated
default is `0`: the validated model has no exclusion shell and a sharp material permittivity (PHY-20
NOTEs). A non-zero value is therefore a deviation that the FR-25 manifest records. When the
`charge:` block is absent, each reads as its validated default. Both are built from the stage-4
profile (§5.2.1 NOTE on the ion-exclusion shell; §4.4 NOTE on the derived solid fraction), so
either set away from `0` beside `inputs.mesh`, or in a case carrying neither `structure:` nor
`inputs.profile`, is a knob with no effect and SHALL be refused naming both keys. A non-zero
`dielectric_transition_nm` beside `inputs.eps_r` supplies one quantity twice and SHALL be refused
naming both. Each is refused below its resolution limit as its NOTE says, and a model that declares
no solid fraction refuses the transition as it refuses `inputs.eps_r` (§5.4.3) (WP30). `numerics.mesh.size_scale`, default
`1`, SHALL multiply every element-size target of §5.2.2 and NUM-30, the resolved `wall_h_nm`
included. It exists so that a mesh-convergence study (RSK-09, §6.8) is a sweep over a case-file
field (FR-24) rather than a code edit. It is a discretisation choice recorded with the mesh, not a
deviation. With a supplied `inputs.mesh` a value other than `1` would be a knob with no effect, so
it SHALL be refused.

NOTE (`charge.ph`, `charge.forcefield`, `charge.titration`; the `protonation` stage, PHY-16 step 3,
FR-12; WP27): `ph` is a number in [0, 14], the range PDB2PQR accepts.
`titration` is `propka` or `none`; `none` runs PDB2PQR without a titration method, so every
residue keeps the force field's standard state and the pH reaches no calculation. A `ph` set away
from its default beside `titration: none` is therefore a knob with no effect and SHALL be refused
naming both keys, as `numerics.mesh.size_scale` is beside `inputs.mesh`. `forcefield` is one of
`CHARMM`, `PEOEPB` and `SWANSON`, and is passed to PDB2PQR as both `--ff` and `--ffout`. PDB2PQR 3.7
also ships `AMBER`, `PARSE` and `TYL06`, but each gives charged atoms a zero radius (53, 93 and 2269
of them on one chain of 2WCD, measured), and PHY-16 step 4's kernel width
`w_i = 0.5 R_i` is then zero, so they are refused naming the atom count rather than admitted to
fail at deposition; the stage refuses a charged atom with a radius that is not positive from any
source, `inputs.pqr` included, naming the frame and the atom. The schema had admitted any string
here, but no case carrying `charge:` was runnable before this package, so narrowing the value set
breaks no document that ran. `titration` and `forcefield` are switches whose validated defaults
are `propka` and `CHARMM` (PHY-16 step 3); any other value is a deviation that the FR-25 manifest
records. `ph` is a condition of the experiment, as `concentration_M` is, and not a deviation. The
case's `structure.source.variant` is recorded beside `Q_net`, which it is the provenance of
(OPN-04). `charge.exclusion_offset_nm` is read by stage 5 and `charge.dielectric_transition_nm`
by stage 7 (WP30; see the NOTE on the v2 keys that change a number,
which says when each is refused). `charge.smearing` is read
by stage 7's deposition (WP28; see the NOTE on `charge.smearing`).

NOTE (`charge.smearing`, PHY-16 steps 4–6, PHY-18; WP28): `sharpness`
is the `0.5` of PHY-16 step 4's `w_i = 0.5 R_i`. It is a switch whose validated default is `0.5`,
and any other value is a deviation that the FR-25 manifest records. `grid_spacing_nm` is the
spacing of the export lattice, on which the kernel is summed and the deposit's integrals are taken.
It is a discretisation choice recorded with the artefact, as `numerics.mesh.size_scale` is, and not
a deviation. A spacing above half the smallest kernel width of a charged atom SHALL be refused naming
that atom (PHY-16 NOTE on the deposition). `axis_cutoff_nm` set away from its default SHALL be
refused naming PHY-18 on every path. The deposited kernel is regular on the axis and takes no
guard, and a supplied field declares its own guard in its header (§5.3.1 NOTE on `inputs.charge`),
so the key would change nothing. The exported field declares the default `0.01 nm` for a later
re-read. As with the protonation keys, `charge.smearing` set away from its defaults beside
`inputs.charge`, or in a case carrying neither `structure:` nor `inputs.pqr`, configures a step
that does not run and SHALL be refused naming both keys.

NOTE (`inputs:`, FR-27): the optional top-level `inputs:` block is hand substitution (FR-27) applied
at stage granularity. Each key names a stage output supplied from outside — a mesh, a charge field,
a dielectric field — by path and format. A stage whose output is supplied does not run, and neither
does anything upstream of it; the substituted file is hashed by content and enters the FR-25
manifest as an input like any other. Releases before v0.3 accept an externally generated mesh
this way, which is what makes the solver core testable ahead of the meshing pipeline (§8.1).
`inputs.profile` supplies stage 4's conditioned polyline as a `nanopnp/profile/v1` document
(`format: profile1`), which is how a hand-edited contour enters a run (§8.1, GUI increment 2), and
`inputs.pqr` supplies the per-atom charges and radii of stage 7's PDB2PQR step (`format: pqr`). The
two chains are structure → density → profile → mesh and structure → PQR → charge field, and the
dielectric field comes from the density (FR-15). Supplying an artefact together with one downstream
of it on the same chain SHALL be refused, naming both. The upstream one would be hashed into the
manifest as an input to a run that never read it. Until the stage that consumes a supplied
artefact is delivered, the case is refused as an unsupported section, naming that stage.
`inputs.profile` is consumed by stage 5 (WP21). It is named by `path`
with `format: profile1`, and `artefact:` or `groups` beside it is refused. The profile is
hashed by the canonical digest of its validated payload. `structure:` beside it is refused naming
both, by the upstream rule, and so are `geometry.density` and `geometry.contour` where either is
set away from its default; `geometry.membrane` and `geometry.reservoir` are read. A section set to
its defaults is not refused, because a case dumped from its resolved document writes every section
out, and FR-26 requires that dump to load back (WP21).

`inputs.pqr` is consumed by the `protonation` stage, the first half of stage 7 (WP27, §8.2.4 D4). It is named by `path` with `format: pqr`, and `artefact:` or `groups`
beside it is refused. The file is a PQR of one frame, or one `MODEL` per frame; every frame SHALL
hold the same residues, and every atom a charge and a radius. ATOM and HETATM records are read by
the PDB columns through the coordinates and then by the two whitespace-separated numbers after
them, which is the layout PDB2PQR writes, whose coordinate fields may run together; a line those
columns do not read is read as whitespace-separated fields, and a line read both ways with
different values is refused naming its line number. A whitespace field that cannot be an atom
name, a residue name or a chain (more than four, four and one characters) does not read the line:
PDB2PQR writes a four-character residue name from the alternate-location column and runs a
four-character atom field into it (`OD2ASPP`, measured, WP27), which the columns
read. A record type run into a five-digit serial (`HETATM12345`, PDB2PQR's own layout) is split
before the fields are read. A residue is identified by chain, number and insertion code, and its
name is the one its atoms carry other than PDB2PQR's CHARMM patch names `TER` and `DISU` (a
disulfide-bonded cysteine's `CB` and `SG`, written `1CB` and `1SG`; WP27
review), or, where its atoms carry a parent and one of its
protonation variants, the variant: PDB2PQR writes a patched residue's backbone under the parent and
its side chain under the variant (`ASP` and `ASPP` in one residue). Unlike
`inputs.profile`, `inputs.pqr` stands beside `structure:`, because stage 1 still runs for the
geometry chain: there the PQR SHALL hold exactly the ensemble's frames, in order, and each frame is
registered to its stage-1 frame by superposing its Cα atoms on the ensemble's, residue for residue,
after which every heavy atom of the ensemble SHALL lie within 0.01 Å of a distinct heavy atom of the
same residue of the PQR, other than the atoms PDB2PQR's hydrogen-bond optimisation may flip: the
amide `OD1` and `ND2` of asparagine, `OE1` and `NE2` of glutamine, and the ring `ND1`, `CD2`,
`CE1` and `NE2` of histidine. A flip turns the group through 180° about the bond to it, and the
group is not symmetric about that bond, so a flipped atom lands 0.13–0.40 Å from every atom it was
given (138 heavy atoms of the prepared 2WCD, measured, WP27; the criterion is not over every heavy atom, because a flip does not exchange positions exactly and
such a criterion would refuse PDB2PQR's own output); they are not compared, their worst distance is recorded,
and the rest of each residue fixes where it is. A flip moves atoms and never removes them or changes their
element, so a residue of these three whose PQR holds fewer heavy atoms of an element than the
ensemble's is refused (WP27 review: without it a PQR missing a flippable atom registered). 0.01 Å is about ten times the rounding of a PQR's coordinate columns
and a hundredth of the shortest bond between heavy atoms, so a frame count that differs, a residue
the two do not share, or a frame whose atoms have moved is refused naming the frame. Heavy atoms the PQR adds, as PDB2PQR
adds a missing terminal oxygen, are counted, not refused; hydrogens are not compared. The
registered coordinates are what the artefact carries, so a PQR written in another frame, as the
reference's MD-frame PQRs are, lands in stage 1's. A frame whose heavy atoms already meet the
criterion where they stand is not moved, so the stage's own export reads back exactly. Without
`structure:` the coordinates are taken to be in stage 1's frame already, which is the frame the
stage exports. Beside `inputs.pqr`,
`charge.ph`, `charge.forcefield` and `charge.titration` configure a step that does not run, so any
of them set away from its default SHALL be refused naming both keys, as `geometry.density` is beside
`inputs.profile`. The same holds beside `inputs.charge`, which supplies the field stage 7 would
make of a protonation, and in a case carrying neither `structure:` nor `inputs.pqr`, which has
nothing to protonate (WP27).

NOTE (`structure:`, stage 1, FR-01 to FR-03, IF-04; WP18):
`source.path` names a PDB or mmCIF file, optionally gzipped. MDAnalysis reads PDB and gemmi reads
mmCIF. `source.selection` is an MDAnalysis selection applied to the file, and one MDAnalysis cannot
parse SHALL be refused naming the key. The selected atoms are those of the selection in the chains
`source.chains` lists. Every selected atom SHALL
carry its element in the file, in the PDB element columns or the mmCIF `type_symbol`, and a file
that leaves one blank SHALL be refused naming the atom: a guessed element is how a Cα becomes
calcium. A selection carrying alternate locations SHALL be refused naming the first, because
choosing between them is structure preparation, which the pipeline does not do. A trajectory that
does not hold the structure's atoms, and an mmCIF model that does not list model 1's atoms in model
1's order, SHALL be refused naming the file (WP18 review).

A chain is identified by its chain identifier, or by its segment identifier where the chain column
is blank. `source.chains` is `all` or a comma-separated list of chain identifiers, such as
`A,B,C`, which SHALL number `n` (a string, so the key's type is unchanged: WP18). `symmetry.point_group` is `C<n>`
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
preparation (WP18 Outcomes).
Until stage 2 is delivered, a walk that extends past stage 1 on a case carrying `structure:` SHALL be
refused as an unsupported section naming stage 2. Once stages 2 and 3 are delivered, and until
stage 4 is, a walk that extends past stage 3 SHALL be refused in the same way, naming stage 4
(WP19). Once stage 4 is delivered, and until stage 5 is, a walk that
extends past stage 4 SHALL be refused naming stage 5 (WP20). With
stages 5 and 6 delivered, a walk runs the whole pipeline and no stage is refused on this ground
(WP21). Stage 1
alone runs through the stage command (IF-02). A case carrying `structure:` and `inputs.mesh` SHALL be refused naming both: a stage whose
output is supplied does not run, and neither does anything upstream of it (the `inputs:` NOTE), so
the structure would be recorded as an input to a run that never read it (WP18).

NOTE (`geometry.density`, stages 2 and 3, FR-04 to FR-06, CON-04, IF-05; WP19): the `geometry:` block is read on a case carrying `structure:`. Beside `inputs.mesh`
it SHALL be refused naming both, by the upstream rule of the `inputs:` NOTE. `grid_spacing_nm`
SHALL lie in [0.025, 0.05] nm (FR-04) and `sharpness` SHALL be finite and positive, and each is refused naming
its value rather than narrowed in the schema.

`kernel: gaussian_vdw` takes each atom's width as `σ R_i`, with σ the `sharpness`. R_i is the
atom's CHARMM van der Waals radius (Rmin/2) by residue and atom name, from the radius set of
PDB2PQR's `CHARMM.DAT`, held as data under `data/radii/`. This is an **author ruling**: it is the set carried by the per-frame PQR files of the reference ensemble
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

NOTE (`geometry.contour`, stage 4, FR-07, FR-08; WP20): `isolevel`
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
A hand edit written by the desktop shell (§8.1, GUI increment 2) is a `nanopnp/profile/v1`
document with `provenance.source: hand-edit`, which is never a reference source. Its `sha256` is the
canonical digest of the profile it was edited from, or, where it was started from a loop stage 4's
gate refused (§8.2.2 B9), the digest of the stage-3 payload that loop was drawn from, as stage 4
records it. Its measurements are re-derived from its own vertices. It enters a run only through
`inputs.profile`, and is gated as a supplied profile (WP24 D5).

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
the pore-mouth interfaces the reservoir-to-lumen split leaves behind — and, in a region stage 5
generates, every solid-to-solid seam: the protein against the membrane and, with an exclusion
shell, the shell against the protein and the membrane (WP30). **Nothing
selects on it**;
it is in the vocabulary because every group must be claimed by some name, and calling an interior
seam `wall` would put it in the PHY-02 distance source set and impose no-slip across the middle of
the electrolyte. `exclusion` is the ion-exclusion region of FR-15 — the shell between the dielectric
contour and the exclusion contour, offset outward by the hydrated-ion radius. It is a solid for
Nernst–Planck and for the flow, so the no-slip surface sits at the outer edge of the shell, which is
the conventional hydrodynamic shear plane; it is **water** for Poisson, so
`physics.solid_permittivities` SHALL NOT require an entry for it and SHALL NOT abort on its absence.
Ions do not exist in it, so `⟨c⟩` has no meaning there (author ruling 13, §4.4 NOTE) and the water
is ion-free: the shell SHALL take `ε_r,f⁰` exactly, never `ε_r,f(⟨c⟩)` evaluated where the
concentrations are undefined. The resulting step at the shear plane is the salt correction of the
fluid side, which the shell by construction does not carry.
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
solids exist. It is the one member of `physics:` that is not a switch, and `pb` and `pb-linear`
carry no solids, so a non-empty map beside one of them SHALL be refused as §5.3.1's other
inapplicable switches are; `poisson` carries them as the coupled models do (WP26: the refusal covered all three electrostatic models, which left none of them runnable
on any mesh with a membrane). On an **ingested** mesh, a material that is
neither in the fluid set nor named in `physics.solid_permittivities` SHALL abort the run, naming the
material; for a model that carries no solids the abort SHALL say that the model cannot be posed on
a mesh with a solid domain, rather than ask for an entry the case would then refuse. Poisson is
solved over the whole domain, so the alternative is the electrolyte's ε_r about
24 times too large in a solid — a plausible wrong answer with no solver diagnostic. Meshes built in
process by the benchmark geometries keep the warning they have today; the difference is that an
ingested mesh's material names were not written by this codebase. A mesh stage 6 generates from a
profile is gated as an ingested one is: its `protein` is a structure's body, not a benchmark's, and
the same wrong answer follows from a missing entry (WP21). Rationale: boundary conditions are selected by name and the natural condition under the
`r`-weighted forms is the *free* one (§6.2, NUM-06), so an unmapped wall becomes an open boundary,
the solve converges, and the current is wrong with no residual, no gate and no diagnostic.

NOTE (`geometry.membrane`, `geometry.reservoir`, `numerics.mesh`; stages 5 and 6, FR-09, FR-10,
NUM-30; WP21): `membrane.thickness_nm`, `reservoir.radius_nm` and an
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
Design §3). `backend: gmsh` meshes the stage-5 region with the optional backend of ADR-002, under
the §5.2.2 NOTE on its size field, and passes the same three gates. It needs the `gmsh` extra.
Without it, stage 6 refuses the run, naming the extra and the import error, whether that error is a
missing module, a native library the wheel could not load, or a library that loads and then fails
to initialise (CON-10; REV-37). The resolved case is not refused: `backend` is checked only against
the registered meshers, `netgen` and `gmsh` as shipped (§5.5). A generated mesh's key records the backend and that backend's own settings, and the Gmsh
version is recorded beside the key (WP23 D8, D9).
`boundary_layer: true` is refused naming FR-11. `geometry.analyte` on a generated mesh is refused naming FR-21.
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
`electrolyte.temperature_K` is checked against that file the same way and SHALL be refused naming
both values when it differs: every reference property, every scale and `V_T` are taken from the
file, whose fits are temperature-specific, so a case at another temperature would be solved at the
file's while its manifest recorded the case's (code review CR-1).

NOTE (`numerics.nonlinear`): the values shown are the NUM-16 reference settings — the monolithic
damped Newton of the reference model, 100 iterations, relative tolerance 10⁻⁶, tested on the
residual and on the relative update alike. `strategy: hybrid` and `damping: backtracking` select
the NUM-20 fallbacks.

NOTE (`numerics.elements`, NUM-03): `phi` and `c_i` carry one element order; `u` is independent of
them and `p` is independent of both, so the reference implementation's own discretisation —
quadratic `phi` and `c_i` with linear `u` and `p` — is expressible. An order for `u` at or below
the order of `p` SHALL be refused unless `numerics.stabilisation` selects a mode supplying the flow
stabilisation of §6.4.2, and the refusal SHALL name both the inf-sup condition and the mode that
would permit the pair. The refusal is made when the case is loaded, so `nanopnp validate case`
and the desktop shell's commit make it with the same text as a run. All three orders are recorded
in the run provenance record (NUM-03).

NOTE (`numerics.stabilisation`, and the compatibility rule for the case schema): the value set is
the registered modes, shipped as `none | supg | reference`; a mode registered at run time widens it
(§5.5; §8.2.8 H7). `none` is the validated default and the production policy of NUM-11;
`supg` is NUM-11's flag, the streamline term alone; `reference` is the mode of NUM-14, streamline
and crosswind on the transport operator together with the flow stabilisation of §6.4.2, and is the
only shipped value permitting an equal-order velocity–pressure pair; a registered mode permits
one by declaring it (`permits_equal_order`). More generally: **widening the accepted
value set of an existing key is compatible and SHALL NOT move the schema version, because every
document that validated before still validates; adding, removing, renaming or narrowing a key SHALL
move it.** The mode a run actually solved is in its FR-25 manifest, so no artefact of an earlier
revision becomes ambiguous under a widening. From Phase 4 the identifier that a move takes names
the release that ships it (§8.2.7 G6): the first move inside v0.5 makes the schema
`nanopnp/case/v0.5`, a move inside v0.6 makes it `nanopnp/case/v0.6`, and the stable schema of v1.0
is `nanopnp/case/v1.0`, which is distinct from the retired `nanopnp/case/v1`. A release whose
packages move nothing keeps the identifier it inherited. Between that release's work packages, the
schema under its identifier may change again without a new identifier, because a pre-release makes
no compatibility promise. The manifest of every run records the package version (FR-25), and that
version settles which revision the run read. The identifier is fixed when `vX.Y.0` is
tagged. A document declaring any earlier identifier SHALL be read as its upgrade. A value the
upgrade cannot carry SHALL be refused, naming the key and its migration in `CHANGELOG.md`.

NOTE (`numerics.wall_distance`): `sources` is the boundary-name pattern the PHY-02 distance field
`d` is measured from, and its validated default is the pore wall alone. PHY-02 excludes the
membrane from the source set deliberately, so widening `sources` is a deviation from the validated
model and SHALL be recorded in the run provenance (FR-25). `max_distance_nm` is the saturation
distance beyond which the wall functions are 1 to within round-off. A value other than the
validated 3.0 nm SHALL be recorded as a deviation for the same reason: below about 1 nm the ion
wall function no longer reaches 1 inside the cap, which changes the model. A value that is not
finite and positive SHALL be refused by `resolve()`, naming the key (codebase review CR-4).

NOTE (`walls`): the wall values name the condition applied, not its absence. `ion_flux` takes
`no_flux | prescribed` and `slip` takes `no_slip | navier | free`. Under the `r`-weighted forms of
§6.2 the natural condition is the free one, so a value reading as "none applied" would silently
remove no-slip while appearing to be the validated default. The forms pose `no_flux` and `no_slip`
only, so every other value SHALL be refused by name until the condition is implemented, and the
refusal lifted in the same commit that implements it: a condition recorded in the manifest but not
applied would be a plausible wrong answer (code review CR-2).

NOTE (`outputs:`): the list selects what the run produces, and each word is refused rather than
silently ignored where it cannot be met. `current`, `transport_numbers` and `eof_rate` select scalar
quantities of interest (§6.7). Each model declares the quantities it provides (§5.4.3), and a word
the named model does not declare SHALL be refused when the case is resolved, naming the model and
the quantities it declares, rather than when stage 11 reaches it (WP26); the electrostatic models declare none, so a case naming one of them writes `outputs: []` or
`outputs: [fields]`. `fields` gates the IF-07 field export, which is off unless asked for:
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
| 1 | Aligned ensemble: coordinates in nm, atom table (element, name, residue name, number and insertion code, chain) and axis-transform record | Native `.npz` (float32 coordinates) with its header record; exported as a PDB topology with a DCD trajectory (IF-04; WP18): a trajectory file carries no atom table and no gate record |
| 2, 3 | Density map (3D, float32), and the reduced (r, z) mean with its Cₙ-averaged and raw azimuthal variance | Native `.npz` with its header record; exported to, and read from, OpenDX or CCP4 via GridDataFormats (LGPL) (IF-05), the (r, z) grids as `RadialGrid`s with a singleton axis (WP19) |
| 7 | Protonation: the per-frame atom table (identity, coordinates in nm in stage 1's frame, charge, radius), `Q_net`, and each titratable residue's charge, PROPKA pKa, histidine tautomer and any unapplied state, per frame | Native `.npz` with its header record; exported as a PQR in ångströms, one `MODEL` per frame where there is more than one. Produced, it is keyed on the stage-1 key and the protonation parameters, among them the PDB2PQR argument list, and each frame is also stored under its own key, the digest of the heavy-atom PDB PDB2PQR is given, so a changed frame selection re-protonates only the new frames; the PDB2PQR and PROPKA versions are recorded beside the key. Supplied, it is keyed on the file's contents and, beside `structure:`, the stage-1 key (WP27) |
| 7 | ρ_pore, dielectric and exclusion fields | OpenDX or CCP4 via GridDataFormats (LGPL) (IF-05). Keyed on each field's grid digest and physical declarations, on the mesh, and on what its gates are evaluated at: the element order of the conservation quadrature and, with a dielectric field, the names of the solid materials its per-material means are classified by. A deposited charge (PHY-16 NOTE on the deposition) is two entries. Its lattice is `nanopnp/charge-grid/v2`, keyed on the protonation artefact, `charge.smearing`'s sharpness and spacing, the patch half-width, the frame shift and the kernel, and not on the mesh, so a mesh-convergence sweep re-deposits without re-summing. Stage 7's artefact adds the protonation and lattice keys to its inputs and the deposit's element order and per-plane weight to its gates. Its payload is the `nanopnp/field/v1` document and its `.npz` lattice, which read back through `inputs.charge`, and the element-wise coefficients with a digest of the element geometry they belong to, which no other mesh is given (WP28). Stage 7's artefact is `nanopnp/fields/v2` and its lattice `nanopnp/charge-grid/v2`: their `v1` payload and summaries recorded wall-clock seconds, and an entry served from the store carries its summary into the manifest unchanged, so a changed summary contract is a changed schema version, as a changed payload contract is (WP32, VER-23) |
| 4 | Conditioned polyline | `nanopnp/profile/v1` YAML: the vertex table with its provenance block (§5.2.1). The conditioning and gate record is in the artefact's summary (WP20) |
| 5 | Tagged (r, z) region | `nanopnp/region/v1` YAML: a declarative record of the model-frame profile, the membrane with its derived inner edge, the reservoir and the tag counts, from which the OCC region is rebuilt deterministically (WP21): a record hashes by content, where a BRep's bytes need not be stable |
| 6 | Mesh | Gmsh MSH 4.1 archival, any meshio (MIT) format on read (IF-06). A supplied mesh is keyed on its canonical contents; a generated one on its recipe, the stage-5 key and the resolved size fields, with its content hash recorded beside the key (WP21) |
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
`schema:` string is excluded for the same reason: a v1 document and its
lossless v2 upgrade describe one run (§5.3.1), and a key that told them apart would re-solve every
converged case in a store because the loader, not the case, had changed. The v1 key **did** carry
the string, so this exclusion moved the stage-10 key, the VER-34 restore digest and the Tier-3 case
identity of every v1 case once, at the move to v2 (author ruling, correcting
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
The plan SHALL also record the content hash of every input file its points name (a mesh, a profile,
a field, a structure or a trajectory), by the path as the case writes it, and carry those hashes in
its own digest: a case's hash covers the path strings and not the bytes behind them, and a path
resolves against the working directory of whoever dispatches. Building a member SHALL refuse a file
whose hash has moved, or which is not there, naming the path and both digests, and reading a plan
file that records no digests SHALL be refused with an instruction to re-plan (CODE_REVIEW_003 CR-5, QR-12).

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

NOTE (QR-13, §8.2.8 H3): the interface above is not built for v1. With one backend it cannot be
tested for the property it exists for, and a wrapper written now would wrap NGSolve without showing
that it fits DOLFINx. QR-13 is met by the single statement of the weak forms, against NGSolve
directly, and the backend's reach is pinned instead: the subpackages that import `ngsolve` or
`netgen` are the `backend:` list of `docs/project/modularity-layering.yaml`, which VER-65 asserts
in both directions: eleven, the eleven `MOD-10` measured and `numerics/` (§8.2.8 H11), less `io/`,
whose field export is `post/export.py`. The table
is the shape a second backend takes when N4 is planned, and Phase 6 or a later plan decides it.

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

NOTE (what a model declares; WP26): a model is registered by name
together with a declaration that can be read without building it. The declaration states the
case-derived options its builder takes, which are the resolved `model_options`; the value set of each
`physics:` switch it honours; whether it carries solid materials, and which supplied coefficients it
accepts (the fixed charge, `χ`); whether it reads the PHY-02 distance field; the values of
`numerics.continuation` it admits; the quantities of interest it provides (§6.7); and whether it
solves ionic transport. Every built model reports its field set, boundary vocabulary, essential
boundaries, NUM-09 scale set and provenance. A layer outside `physics/` reads these, and SHALL NOT
branch on a model's name or on its class: case validation refuses what the declaration does not
admit, the mesh gate requires the boundaries the model declares, the solve passes the coefficients
it accepts, and QoI extraction reaches the transport members through the declaration. The NUM-18
ladder is the one place outside `physics/` that names models, because §6.5 defines it as a path
through named models; it is a strategy a model admits, not a branch on the model, and only the
models it ends at, `epnp-ns` and `pnp-ns`, may admit it.

### 5.5 Extension points

Pluggability has two levels, matching the two kinds of change users make (QR-14). Below them, the
backends of the discretisation are registries as well (§8.2.8 H7): a mesher (`numerics.mesh.backend`,
`mesh/meshers.py`), a linear solver (`numerics.linear.solver`, `numerics/linear.py`) and a
stabilisation mode (`numerics.stabilisation`, `physics/stabilisation.py`) are each added by one
registration, and each key is a string checked against its registry when a case is loaded, as
`physics.model` is. Registering the Gmsh mesher imports nothing (CON-10), and `sparsecholesky`
cannot be registered (NUM-21). Whether the registering functions are public waits for `MOD-11`'s
ruling (§8.2.8 H2).

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

**Delivered** (WP23, VER-54). `numerics.mesh.backend: gmsh` meshes the region
stage 5 assembled with `netgen.occ`, read from its named edges into Gmsh's built-in kernel, under the
size field of the §5.2.2 NOTE on the Gmsh backend, and joins netgen's route at the MSH 4.1 writer,
so every gate is shared. Gmsh assembles no region of its own. Boundary layers remain FR-11, after
v1.0, and whether the bundle carries Gmsh remains the later decision above.

#### ADR-003 Project licence

Decision: BSD-3-Clause core library with GPL-compatible optional extras. No institutional
constraint applies.

| Alternative | Assessment |
|---|---|
| GPL core, Gmsh in the default path | Deferred, not foreclosed: the package has no other GPL entanglement, so this stays a one-line relicense should GPL become acceptable |
| PyQt for the desktop shell | Rejected: GPL-3 or commercial only. PySide6 (LGPL-3) is used instead (CON-09) |
| Bundle defaulting to scipy SuperLU | Rejected on measurement (§6.6): SuperLU was OOM-killed on the reference-sized factorisation, so a SuperLU-default bundle cannot run the published case. The bundle defaults to UMFPACK and carries the GPL-2+ obligations that follow, stated in its licence notice; the library itself stays BSD-3 and depends on neither (CON-11) |

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
| Local web application: FastAPI plus browser frontend wrapped in `pywebview` | **Rejected**, closing the deferral below. The stage interface did stay clean — `run_case` takes a `Progress` callback and a `CancelToken`, and every stage is introspectable without importing it (FR-27) — so the alternative remained available and was declined on its own merits: it buys a hosted future and an SSH port-forward this project has no requirement for, and pays in a second rendering path for the same webgui scene. Originally recorded as "on the table… the choice may wait until Phase 1", which is where it was made |
| Defer the interface to a terminal phase | Rejected on two failure modes: an interface bolted on at the end exposes the API's accidental structure rather than the user's workflow, and a nine-month gap before any non-programmer touches the tool is a nine-month gap in shaping feedback |

NOTE (packaging). The redistributable bundle SHALL be built one-**dir**
rather than one-file, for two independent reasons. PySide6 and Qt are used under the LGPL option
(CON-09), which requires that a recipient be able to replace the covered libraries; a directory of
shared libraries satisfies that plainly. And Qt WebEngine runs a separate helper executable, which a
one-file extractor must locate at runtime inside a temporary directory. The bundle SHALL carry the
licence notice CON-11 requires, stating that the bundle as a whole is distributed under GPL-2+
because its default linear solver is, while the library itself remains BSD-3. The packaging probe
SHALL carry, and its `--selftest` SHALL exercise once each, failing naming the payload: PySide6's
widgets and Qt WebEngine, NGSolve, Netgen and `ngsolve.webgui` (§8.2.1 A4), and since WP24 the
geometry pipeline's compiled payloads, MDAnalysis and gemmi reading a structure, scikit-image's
contour extraction, Shapely's polygon checks through GEOS, and Gmsh meshing a square (§8.2.2 B8).
An extension that imports and then cannot load its library is RSK-13's failure, which an import
alone does not detect: Gmsh's Python module imports with its library missing and fails on its first
call (`.knowledge/07-software-stack.md` §5). Since WP31 the bundle also carries the charge
pipeline's protonation payloads, PDB2PQR and PROPKA, with the data files each reads beside its own
modules. `--selftest` protonates a nine-residue peptide at two pH values and requires the two net
charges measured for it, so that a bundle missing PROPKA's parameter file fails naming PROPKA,
where a single run without titration would pass (WP31 D14). A
pure-Python payload used under the LGPL SHALL be collected as source files on disk, and not into
the bundle's module archive: a module inside the archive cannot be replaced in place, and the
one-dir layout exists so that an LGPL component can be. That applies to PROPKA (LGPL-2.1),
MDAnalysis and GridDataFormats (LGPL-3.0-or-later) (WP31 D15). The background solver
process SHALL be started with the `spawn` start method: it is the only one Windows has, and a forked
child would inherit both the parent's Qt event loop and its already-imported numerical libraries.

Consequences: every pipeline stage must be independently invocable, cancellable, progress-reporting
and introspectable (FR-27), which §5.1 requires on scientific grounds in any case, so the interface
is a thin shell over the stage objects the CLI drives (IF-09). Each release from v0.2 onward ships
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

NOTE (the `r` weight and the default order; WP26): NGSolve estimates
an integrand's order from its trial and test functions and does not count the coordinate, so a form
that is not singular is integrated one order short of its degree in `r`: at P2 the axisymmetric
stiffness `ε ∇u·∇v r` and the source `ρ v r` are of degree 3 and are integrated at order 2. It is a
consistency error, not a NaN, and it converges with the mesh. `poisson` assembles both terms with
one extra order: on the three-layer capacitor of VER-56, whose exact solution the P2 space contains,
the error is 0.38 `V_T` (3 %) next to the axis at the default and 1.1 × 10⁻¹³ with it. The coupled
models keep the default here, and whether their forms should gain the same order is open: it moves
every number they produce, so it is a decision with a measurement, not a side effect of WP26
(`.knowledge/06-numerics-fem.md` §2.2). **Measured by WP34**, through `Measures.weight_extra_order`, a seam no case key,
option or flag reaches (`tests/tier2/test_axis_weight_order.py`, `slow`, stabilisation `none`). On
VER-18's coupled manufactured solution at `maxh` 0.4, 0.2 and 0.1 nm, one extra order leaves the
finest-pair rates at about 3 for the P2 fields and 2.7 for the P1 pressure (`c_Cl−` 3.19 → 3.01,
`c_Na+` 3.11 → 3.03), and lowers the error at fixed `h`. The coarse-pair rates of the
concentrations fall, `c_Cl−` 3.98 → 3.65 and `c_Na+` 3.55 → 2.99: at 0 the quadrature error is a
larger share of the coarse-mesh error, and its faster decay inflates the observed rate. At 0.1 nm the error ratio is 0.42 for `c_Cl−`, 0.77 for `c_Na+`, 0.98 for `φ` and `u`
and 0.91 for `p`. So it is a consistency constant of the same order as the discretisation error, as
this NOTE predicts. On example 05's frozen case, 0.5 M at +50 mV on the reference mesh, each state
is a root of its own form (`|R|` about 2 × 10⁻¹¹) and violates the other's at 7.3 × 10⁻⁴. The
states differ by 4.9 × 10⁻⁷ relative. The current, the conductance and `t₊` move by about 10⁻¹⁰
relative or less, the electro-osmotic flow by 7.6 × 10⁻⁸, and the in-pore concentrations, mobile
charge and mean potential by 10⁻⁹ or less. At the reference mesh, the order is invisible in every
number VAL-16 and VAL-17 compare. Phase 6 decides (§8.2.5 E4, §8.2.6 F1).

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
> problem. **Resolved** in favour of the measurement: the bundle defaults to
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

NOTE (`boundary_conditions.ground: trans`): the case may ground trans instead, which puts its bias
on cis. The current is still referenced to cis, so every quantity SHALL be reported against the
cis-referenced bias `φ_trans − φ_cis`, which is the negative of the case's `bias_V`, and that is the
bias the quantities record. One physical state then reports one set of numbers whichever electrode
is grounded, `G > 0` holds under either, and a sweep pairs its rectification members by the biases
they recorded (code review CR-3).

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

NOTE (zero bias): at `V_bias = 0` exactly, as on the equilibrium rung of §6.5 or the 0 V member of an
I–V sweep, every current is round-off (1e-27 A against 1e-25 A for the two routes on a coarse
uncharged pore), so the transport number and the conductance, each a ratio to it, SHALL be
reported as undefined (`null`) rather than computed, and the NUM-26 check SHALL NOT be applied,
because a relative difference between two round-offs is of order one whatever the extraction does.
The summary records `routes_checked: false`. The currents and `Q_EOF` are still reported, and a
case asking only for `eof_rate` at zero bias SHALL run (code review
CR-8).

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

NOTE (the wall target and its ceiling; WP21): `h₁` is resolved as
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
| **VER-01** | Charge conservation under smearing and azimuthal projection | Assembled charge on the deployed mesh within 1 × 10⁻³ relative to `Q_net` (PHY-19). On the producer path the export lattice's integral against `Q_net` (producer leg) and the deposit's against the lattice's (consumer leg) are gated separately, beside the quadrature agreement and the boundary ring; each broken construction of the WP28 plan's *Design* §5 fails its own gate and only it. At Tier 2 on the protonated 2WCD at the default sizes and on the charged walk at `size_scale` 4 (WP28) |
| **VER-02** | Per-z-slice cumulative charge | Cumulative charge below each z plane matches the partial sum over the source charge list, to the VER-01 tolerance. On the producer path the source is the atoms in closed form under `½ erfc((z − p)/s)`, `s = 0.5` nm, at 12 planes over their z-extent, and the export lattice and the deposit are each gated against it (§4.4 NOTE on the producer path; WP28) |
| **VER-03** | Correction models reproduce their published check values | `f^w_D(0) = 0.0601`, `f^w_D(0.75) = 0.9910`, `η⁰/η^w(0) = 0.3790`, `η⁰/η^w(1.45) = 0.9876`, `η(5.3 M) = 1.752 × 10⁻³ Pa s`, `ϱ(5.3 M) = 1194 kg m⁻³`, `D_Na(5.3 M) = 8.13 × 10⁻¹⁰ m² s⁻¹`, `D_Cl(5.3 M) = 1.071 × 10⁻⁹ m² s⁻¹`, each to four significant figures; clamping above 5.3 M activates and is logged |
| **VER-04** | Nernst–Einstein consistency at infinite dilution | `μ_i⁰ = D_i⁰/V_T` with `V_T = 25.693 mV`: 5.1922 × 10⁻⁸ (Na⁺) and 7.9089 × 10⁻⁸ (Cl⁻) m² V⁻¹ s⁻¹, to four figures |
| **VER-05** | Einstein-ratio drift | `D_i/μ_i` rises to 1.2–1.7 × kT/e between 0.15 M and 3 M and matches the expected profile. A test asserting `D_i/μ_i = kT/e` at finite concentration SHALL NOT be written (PHY-14) |
| **VER-06** | Wall-distance field | Mollified field has continuous gradient across element boundaries to a stated tolerance; `d = 0` on the pore boundary; membrane absent from the distance source set (PHY-02) |
| **VER-07** | Integration order on 1/r forms | Every form carrying a 1/r factor asserts integration order ≥ 3; assembly on an axis-touching mesh returns no NaN and no Inf |
| **VER-08** | Packing fraction and positivity | `Φ = Σ_j N_A a_j³ c_j < 1` and `min_i c_i > 0` at every nonlinear iterate; violation aborts with the offending quantity and its location (PHY-06) |
| **VER-09** | Case-file schema round-trip | A written and re-read case file yields a semantically identical run configuration; an unknown key is rejected with a diagnostic naming the key |
| **VER-10** | Mesh quality gates | On known-bad input the gates fire: min SICN/gamma > 0.3 required, run aborts, diagnostic names the worst element and its location. Reference figures: minimum 0.6378, mean 0.9765 |
| **VER-11** | Current-extraction route agreement | On a stored converged fixture, the ψ-domain-integral and the variational reaction flux agree to a tolerance smaller than the rectification signal at the lowest bias in the envelope |
| **VER-23** | Artefact content addressing | The hash of a fixed artefact is a stated constant, reproduced in a fresh process under a varied `PYTHONHASHSEED`; every leaf change of the parameters or of an input hash moves it; representational differences that validation removes (`1` against `1.0`, `-0.0` against `0.0`, key order) do not; an unhashable payload is refused naming its path; a payload file edited on disk loads as hand-substituted rather than aborting; a stage computed twice from one recipe writes byte-identical payload files, and no wall-clock time enters a payload, or stage 7's summary, which the manifest's charge group copies (WP32) (§5.3.2, FR-27) |
| **VER-24** | Provenance manifest completeness | All eight field groups of §5.3.3 are present, a group no stage contributed carrying a status and a reason rather than being omitted; every switch-typed field of the case schema is classified either as a switch with a validated default or as a configuration choice with a written reason, in both directions, so that a switch added later without a default fails this test; the physics model's own deviation enumeration agrees with the case's on the switches they share; the environment group is populated without importing NGSolve (FR-25, IF-08) |
| **VER-25** | Stage protocol | Every stage registered in §5.2 reports its name, number, inputs, outputs and artefact schema, and the facts a walk acts on (whether its constructor takes a workspace and a store, whether its key is its artefact, its progress weight and the case section it needs), without importing its implementation module, asserted on `sys.modules` in a fresh process; each stage's own description is the registry's, so the two cannot drift; progress is monotone in [0, 1] and ends at 1; a cancellation token raises naming where the stage stopped, and is not a subclass of the numerical gate errors (FR-27, IF-01) |
| **VER-27** | Mesh ingestion and tagging | A tagged mesh written as Gmsh MSH 4.1 and read back preserves vertices, connectivity, per-group physical tags and group names (IF-06); a group left unclaimed by `inputs.mesh.groups`, or a vocabulary name the run selects on that no group supplies, aborts with a diagnostic naming both lists (QR-12); the default ingestion path imports neither `gmsh` nor netgen's Gmsh reader, asserted on `sys.modules` in a fresh process (CON-10) |
| **VER-28** | Reference-geometry conformance | The assembled (r, z) region has exactly three domains — pore body, one membrane, one electrolyte — and is conformal at the membrane-to-pore junction: the membrane meets the pore on the pore's own outer surface, at r = 2.7524 nm on z = −1.4 and r = 4.88 nm on z = +1.4 within the fragmentation tolerance and read from the fixture rather than hard-coded, *and* over one shared edge chain rather than two coincident ones; no membrane material lies inside the fluid set; the region carries exactly the §5.3.1 vocabulary and its mesh meets the §5.2.2 quality figures (FR-09) |
| **VER-29** | External field ingestion and charge conservation | An (r, z) grid round-trips through the native format and through OpenDX and CCP4 with the singleton-axis convention, origin, spacing and values preserved, on every supported interpreter (the IF-05 NOTE of §3.1); a genuinely two-dimensional array is refused naming its shape; the interpolant's axis order is asserted against a field that is not symmetric in its arguments, so a transposed array fails rather than agreeing on the diagonal; the field is zero outside the grid box rather than continued by its edge value; on the deployed finite-element mesh `|Q_mesh − Q_net|/|Q_net| < 10⁻³`, reported as the producer and consumer legs of the §4.4 NOTE and gated separately, with the axis-guard deficit and the boundary-ring maximum reported beside them; the ramped per-plane cumulative agrees to the same tolerance at every plane; a grid whose boundary values are not negligible against its interior aborts naming the value and its (r, z); a field declaring no `Q_net` gates the consumer leg and records the producer leg as not run. The conservation half is asserted at Tier 2 on the reference mesh of §5.2.1, against a field whose `Q_net` is known in closed form, and a deliberately coarsened mesh there fails the quadrature-agreement gate rather than the conservation gate — which is the distinction the §4.4 NOTE makes normative (QR-03, PHY-18, PHY-19, IF-05, FR-14 in part) |
| **VER-30** | Dielectric blend | The sharp solid fraction reproduces PHY-20's piecewise assignment to round-off at every quadrature point; a `χ` outside [0, 1] and an inverted `χ` both abort with the offending quantity and its location, the latter on the per-material means; an absolute `ε_r` field is refused with the §4.4 NOTE named; the ion-exclusion shell is `ε_r,f⁰` exactly at 3 M with the permittivity correction on; a smooth `χ` blends towards `ε_r,f⁰` inside a solid and towards the nearest solid's `ε_p` in the fluid, each checked at a point; `exclusion`'s mean `χ` is held below 1/2, not to the fluid ceiling, for a supplied `χ` as for a derived one (FR-15; the last two clauses but one, author ruling 13; the last, WP30 D6) |
| **VER-32** | Command-line surface and exit-code contract | Every subcommand parses and dispatches to the stage objects it names; the registry is listed in a fresh process that imports no stage implementation module, no NGSolve and no netgen, asserted on `sys.modules`; each exit class of the §3.1 IF-02 NOTE is produced by an input that triggers it; every public exception type in the package is either classified by the exit-code enumeration or excluded from it with a written reason, in both directions, so that a type added later fails this test; diagnostics appear on standard error and standard output carries only the command's result; a gate abort prints its QR-12 diagnostic without a traceback unless one is requested; a run given a store writes every file it produces inside that store, asserted by running from a working directory the process-default fallback would land in and requiring it to stay empty; `mesh cylinder` and `mesh reference` write an MSH 4.1 file that a case using the `inputs.mesh.groups` mapping they print ingests through the VER-27 gate unchanged, the hash they print is the mesh hash that run's manifest records, a mesh failing the VER-10 quality gate is refused with its QR-12 diagnostic and exit class `4` and leaves no file behind, and `--help` on either imports no netgen; `stage <name> --export` writes each stage's interchange file, the profile and the mesh equal to the store's bytes and the PDB and DCD reloading with the artefact's coordinates, moves no artefact key, and refuses a stage or a suffix it does not write with exit class `2` before any stage runs and without leaving a file (WP25) (IF-02, IF-05, FR-27, the §5.3.2 workspace-locality NOTE, the §3.1 IF-02 generators and export NOTEs) |
| **VER-33** | Field export exactness and the Ω/Ω_w split | A quadratic exported and read back is reproduced *exactly* at all six nodes of every element, which a permutation of the midside nodes fails; the exported node count is `nv + nedge`; the two files carry the whole-domain and fluid-only field sets respectively and the fluid file contains no solid node; attribute names carry SI units and the values match the §6.3 scale conversion to round-off, with the `2π` of the axisymmetric measure absent; heavy data is compressed (IF-07) |
| **VER-34** | Solution-state round trip and descriptor gate | Save followed by restore reproduces every component's coefficients to zero difference; the stored wall-distance vector is restored rather than re-solved; a descriptor differing in the solve-provenance digest, mesh hash, element order, domain restriction, degree-of-freedom count, model options, wall-distance sources or saturation distance, or stabilisation mode each abort naming the key and both values; a payload of the superseded schema version is refused by schema rather than misread; a case differing only in `name:` or `outputs:` restores, and keys the same stage-10 artefact (FR-27, QR-08 in part) |
| **VER-36** | Sweep plan: substitution, validation and the warm-start forest | A product of axes enumerates the points of §5.3.4 in wave order; an assignment-valued axis moves several case-file paths together; a point identity is stable across processes and unchanged by a value inserted on another axis, while its index is not; every point has exactly one parent one grid step nearer its axis origin, its wave is its depth, and the points of one wave are pairwise independent; an axis rooted away from its first value walks outward in both directions; a misspelt path is refused naming the component and the prefix that exists, and a value of the wrong declared type is refused before any solve; a point the case schema resolves but §6.5 refuses fails when the plan is built, naming the point and the reason; a plan asking for `rectification` whose axes produce no exactly-opposite bias pair is refused naming the axis; the plan records each input file's hash, moves its own hash with them, and refuses to build a member from a file that has changed or gone, and a plan file whose recorded point ids, hash or file digests no longer match what it enumerates is refused (FR-24, IF-03, QR-12; CODE_REVIEW_003 CR-5, CR-6) |
| **VER-37** | Warm start across a sweep step: the descriptor partition | Every leaf of the descriptor a real solve produces appears in exactly one of the space and operator sets, and every entry of both sets appears in the descriptor, in both directions; a warm-start load accepts a payload differing only in operator keys and records each of them; it aborts naming the key and both values on a differing mesh hash, degree count, field record, boundary set, variable branch or stabilisation mode; a payload of a superseded schema version is refused by schema; the loaded state carries no residual and does not read the stored wall-distance vector; and a point reached warm reproduces the same point solved cold to better than the `1 × 10⁻⁶` nonlinear relative tolerance, with the measured difference reported. The partition is verified at Tier 1, on the descriptor alone; the warm-against-cold agreement is a Tier 2 activity, needing a converged pair (FR-24, the §5.3.2 warm-start NOTE) |
| **VER-38** | Sweep dispatch and collection | A single-member dispatch exits with that member's own class for each of the case, gate, convergence and cancellation classes, and produces the same scalars run alone into an empty store as it does inside the sweep; a local multi-worker sweep exits `0` with a failed member present and nonzero under fail-fast; a member whose parent artefact is absent falls back to the full ladder and records the reason; the worker thread pinning is in place before the linear-algebra libraries are imported, asserted in a spawned process; the dataset round-trips to identical values, a failed member's quantities are absent rather than defaulted, and the rectification of an exactly-opposite bias pair equals the two-point ratio of §6.7 taken from the same two records. The dispatch and collection surface is verified at Tier 1; the equivalence of a member solved alone and the same member solved inside the sweep is a Tier 2 activity (FR-24, IF-02, FR-23) |
| **VER-40** | Wall-distance admissibility and the correction driver clamp | Both wall forms are continuous across `d̄ = 0` and return their wall values for every non-positive sample, rather than the sign-reversed values the ion form's root at `−P₂` would otherwise give, on the numeric and the symbolic evaluation path alike; a distance field whose minimum falls below the NUM-34 threshold aborts naming the gate, the measured minimum, its location and the fraction of samples below zero, and one above the threshold passes; the field gated is the mollified one wherever NUM-31's smoothing is applied, and a configuration activating no wall correction is not gated; and a mesh coarse enough to violate the gate is refused rather than returning the current whose two extraction routes disagree by 40 %, while a mesh that passes agrees between the routes to better than the NUM-26 tolerance. The clamp and the gate diagnostic are verified at Tier 1, on the correction functions and one field; the route-agreement half needs a converged pair and is a Tier 2 activity (PHY-02, NUM-34, NUM-26, QR-04, QR-12) |
| **VER-41** | Stabilisation terms, the mode registry and the `Pe_h` diagnostic | The element size the stabilisation parameters are defined against is asserted elementwise against its measured convention rather than assumed, so a backend that changed it fails here rather than retuning the mode in silence; the registry lists exactly the modes of §5.3.1 and refuses an unknown name listing them; the `none` entry produces an assembled residual *identical* to the unstabilised one, asserted on the vector and not on the mode string; the streamline parameter takes both branches of `ψ(q) = min(q, 1)` and is continuous at the crossover; the crosswind viscosity is exactly zero on every element at or below the Péclet number its tuning constant sets, positive on one above it, and bounded by `D_i(C Pe_K − 1)`; the crosswind projector annihilates the advective velocity and is idempotent; the crosswind, streamline and grad-div terms request the integration orders of NUM-15 and the `1/r` minimum of NUM-07 respectively, asserted on the quadrature request rather than on a number; an equal-order velocity–pressure pair is refused in every mode that supplies no flow stabilisation, naming both inf-sup and the mode that would permit it, and accepted in the mode that does; a velocity order left unset reproduces the previous two-order model exactly; the `Pe_h` diagnostic warns naming the species, the value and its `(r, z)`, is silent below the threshold, and runs in the unstabilised mode; and every mode's **linearisation** is finite at the zero-wind cold state `φ̃ = 0`, `c̃_i = 1`, `u̅ = 0`, asserted on the assembled Jacobian entries rather than on the residual, because the residual is finite there in every mode and only the linearisation is not (NUM-03, NUM-11, NUM-12, NUM-14, NUM-15, QR-12) |
| **VER-43** | Desktop shell, schema-generated editor, solver process and packaging probe | The schema walk enumerates exactly the editable dotted paths of the current case schema (`nanopnp/case/v2`), asserted in both directions so that a field added later fails this test rather than becoming silently uneditable, and the switch classification of FR-25 is checked against that same walk rather than a second one; the shell's view-model layer imports neither PySide6 nor NGSolve, asserted on `sys.modules` in a fresh process, and no `PyQt` module is reachable from any import path the shell takes (CON-09); every option the editor offers comes from the schema's own declared type or from a live registry, so no value set is written in `gui/`; a value the schema refuses is refused at the field before any substitution, naming the path, the value and the declared type, and a document the registries refuse produces the same diagnostic text the command line prints for the same file; run control drives the case through a **spawned** process, forwards a monotone completion fraction ending at 1, receives each stage transition as data — the stage's name and its position in the walk, through a structural hook, never recovered by parsing a progress caption — and cancels through a token the child honours, a cancelled run writing no artefact; a failed run reports the §3.1 exit class the command line would return for the same case; and the packaging probe imports PySide6, `QtWebEngineWidgets`, NGSolve, Netgen and `ngsolve.webgui` in one process, its bundle carrying the CON-11 licence notice (IF-09, QR-11, FR-27, CON-09, CON-11, RSK-13, §8.2 criterion 4 as amended by A4) |
| **VER-44** | Live convergence monitoring and field visualisation | The rung and the Newton step reach the shell through a structural hook carrying the residual and the undamped relative update as numbers, never recovered from a progress caption; the hook is not an input, asserted by running the same case watched and unwatched and requiring one artefact hash and one store entry; a rung that reports no Newton step yields a rung record all the same, and the plot shows it as a labelled band rather than interpolating a line across it, naming **which of the two silences** it is: a rung whose model takes no Newton callback and can report no step, or a coupled rung whose damped-Newton solve found the entry residual already below its target and returned before its first step — the NUM-16 warm-start case, which most of a warm ladder does. The hook SHALL carry that distinction as data, taken from the same test that injects the callback, because the two silences are identical from the far side and annotating either as the other states something about the solve that is not true; a solve served from the store is named as such rather than drawn as an empty plot; the plot draws no convergence threshold, the criterion of NUM-16 being per rung and disjunctive, and reports per rung which test the recorded numbers **prove** ended it rather than which the solver evaluated first: the two tests are not exclusive, so what may be asserted is the exclusion — a forced last step, which NUM-16 bars from the update test, and a last relative update above the rung's own tolerance each leave the residual test as the only one that can have closed the rung, and otherwise the update test is reported as met without also claiming the residual test was not. That tolerance SHALL travel with the rung rather than be assumed from the reference settings, so the reading is against the number the solve used; the band also reports the minimum damping and how many steps were forced; the field viewer renders a solution restored through the stage-10 gate rather than an export, its field names and units come from the IF-07 attribute vocabulary rather than from `gui/`, the scene reaches the view as a file rather than a data URL, a sample no logarithmic axis can place is omitted and counted rather than drawn at the axis floor, and a document that loaded without its renderer is reported as a diagnostic naming the renderer source rather than shown as a blank panel; the renderer is shipped with the package rather than fetched, is byte-identical to the npm tarball the repository keeps as its corresponding source, that tarball's SHA-512 is npm's published integrity, and its version is the one the installed `netgen.webgui` pins, so an upgrade that moves the pin fails the gate rather than drawing nothing; and the packaging probe's selftest fails when the bundled renderer does not reach its document (IF-09, QR-11, FR-27, NUM-16, NUM-18, QR-12, CON-09, RSK-13) |
| **VER-45** | Documentation surface and the public API | The generated case-file reference enumerates exactly the editable dotted paths of the VER-43 schema walk, in both directions, with each field's declared type, default and option set taken from the schema or a live registry, so a field added later appears without a documentation edit; the generated command-line reference covers every subcommand `build_parser()` defines, and its exit-code table is the §3.1 IF-02 enumeration, both in both directions; every name in `nanopnp.__all__` resolves and is the object at its documented module path, and the `TYPE_CHECKING` mirror imports each name from the module `PUBLIC` names, an `__init__.py` mirroring `resolve` from another module failing naming the name and both modules, and the documented public surface equals `__all__`, in both directions; `import nanopnp` in a fresh process imports no `ngsolve`, `netgen` or `numpy` module, asserted on `sys.modules`; the documentation site builds with the generator's strict mode, so that a broken internal link or cross-reference fails the build, on every push including prose-only ones (§7.6) (IF-01, IF-02, IF-03, QR-15 in part; §3.1 IF-01 public-surface NOTE) |
| **VER-46** | Executed worked examples | Every command in an example's tagged console blocks is executed verbatim, from a copy of that example's directory, and exits `0`, or `4` in a block tagged as a gate refusal (WP25); each example meets an oracle stated in its README that is a property of the model rather than a transcribed number: an uncharged pore with symmetric reservoirs rectifies to unity within solver tolerance; a pore carrying negative fixed charge has a cation transport number above one half; a run with every correction set to `none` lists each of them under the manifest's deviations from the validated default; the two current-extraction routes of FR-23 agree to the tolerance QR-04 already gates; and fields read back from the IF-07 export carry the attribute names that vocabulary defines. On the geometry pipeline (WP25): the deposited 2WCD entry is refused by stage 1's orientation gate, naming an angle above its limit; the entry prepared outside the pipeline walks stages 1 to 6 through every gate, and the manifest records the artefact of each; the aligned structure's export passes stage 1 under `symmetry.axis: z`; the exported density map, read in ångströms as a viewer reads it, contains every heavy atom of that export and reads at least the single-frame bound `exp(−(√3h/2)²/(σR_min)²)` at each atom's nearest node; and the exported stage-4 profile, supplied through `inputs.profile`, meshes to the same mesh content hash under a different key. On the charge pipeline (WP32): the prepared entry walks every stage to a charged solve under the validated model, listing no deviation; the manifest's `Q_net` is the integer the exported PQR's charge column sums to; the conservation report is in the manifest with each leg and each worst plane below its tolerance; the negatively charged lumen is cation-selective, `t₊ > ½`; the exported PQR, supplied through `inputs.pqr`, gives the same atom table and the same deposit; both FR-15 switches set away from `0` are listed as deviations and mesh an `exclusion` material; and the exported charge lattice, re-supplied through `inputs.charge` on a mesh that does not resolve it, is refused by stage 7's gate. No number appears in the user documentation as a result unless an example asserts it. Runs in the Tier 2 directory for its runtime; an example whose solve takes minutes (the reference geometry) is marked `slow` and is recorded rather than gated, its cheap steps still gated at Tier 1 (QR-15 in part, IF-02, IF-05, FR-01 to FR-10, FR-12 to FR-15, FR-23, FR-24, FR-25, FR-27) |
| **VER-47** | Case schema v2, the v1 upgrade and the supported interpreter range | Every case file the project shipped under `nanopnp/case/v1`, frozen as a test corpus, loads as v2. For each of them, the resolved solve provenance equals, entry by entry, the record the v1 loader made before the move less its `schema:` string; the VER-34 solve-provenance digest and, for a case supplying no charge or `ε_r` field, the Tier-3 case identity are the hashes of that record (a supplied field's contents are part of the identity, which moved it for the three corpus examples supplying one and for no frozen validation case), and the recorded v1 digests are shown to be the hashes of the recorded record, so the comparison is against what v1 keyed; the stage-8 materials key equals the recorded one; and the v1 file and its v2 rewrite share one stage-9 key and one resolved configuration; the frozen v1 field tree maps onto the v2 tree through the declared added, renamed and moved sets, in both directions, so that a key changed later without a map entry fails this test; a v1 document carrying a v2 key, a moved permittivity disagreeing with `physics.solid_permittivities`, and a v2 document using a removed or renamed key are each refused naming the keys; an undeclared schema string is refused naming both accepted ones; each supplied artefact given beside one downstream of it on the same chain is refused naming both, and each new `inputs:` key is refused as unsupported naming the stage that would consume it; `charge.exclusion_offset_nm` and `charge.dielectric_transition_nm` are classified switches whose non-zero values are listed as deviations, and read as their defaults where the block is absent; `numerics.mesh.size_scale` other than 1 beside `inputs.mesh` is refused; the Python range declared by `requires-python`, the trove classifiers, the ruff target and the CI matrix agree with each other and with §2.5 (IF-03, FR-25, FR-26, FR-27, QR-09; §5.3.1 v2 NOTEs; the solve-provenance clause, because the v1 keys carry the schema string, §5.3.2 NOTE) |
| **VER-48** | Structure ingestion, the Cₙ axis and the oligomeric state | A synthetic Cₙ assembly (n = 7, 8, 12) about a known axis tilted 35° and offset by (3, −1.5, 40) nm, its chains lettered in a shuffled order, recovers that axis to 1e-9 in direction and in offset; with per-atom noise of 0.02 nm on an assembly whose second moments are isotropic, the permutation axis stays within the 0.01 nm displacement budget over the axial extent while the principal axis nearest the truth does not; a 6 × 2 arrangement, a D6 assembly, a ring whose chains do not turn with it, `auto` on C1, an axis 30° from the file's z and `axis: z` 0.02 nm off the detected axis are each refused naming the gate and the measured value; the in-project Kabsch rotation equals MDAnalysis `rotation_matrix` to 1e-12; a blank element, an alternate location, a missing, surplus, unlisted or truncated chain, a residue-name disagreement, a non-cyclic point group, a chain list not numbering n, a non-positive frame window, a selection MDAnalysis cannot parse, a trajectory of other atoms and an mmCIF model listing its atoms in another order are each refused naming the atom, chain, key or file, while an alternate location in a chain `source.chains` leaves out is not; PDB and mmCIF of 2WCD read to the same atom table and coordinates within 5e-5 nm, and DCD, XTC, TRR and NetCDF read back the bytes written within each format's precision; the frame stride ends on the last frame, and a `last_ns` beyond an untimed DCD's recorded span and a `count` beyond the window are refused naming both; rigidly moved frames superpose to within 1e-5 nm; the deposited 2WCD frame is refused by the orientation gate, and its chains A–L moved rigidly into an admitted frame run as stage 1 with 12 chains and 285 common C-alpha, recover the applied tilt to 1e-6 degrees, keep `z = â·x`, and re-detect their own axis as z through r = 0 to 1e-6; the artefact round-trips, its key is stable across processes and does not move when `structure.source.variant` is relabelled, an export of chains keyed by segment identifiers or by keys longer than one character keeps every chain distinct (CODE_REVIEW_003 CR-9, CR-13), a hand edit of its payload is recorded as one, and its PDB and DCD export reloads, with residues that differ only in insertion code kept apart; a full walk and a sweep over a `structure:` case are refused naming the first stage not yet delivered (stage 2 when WP18 landed; stage 4 since WP19), `structure:` beside `inputs.mesh` is refused, and the stage is listed with neither MDAnalysis nor gemmi imported while a missing extra is named when it is created. At Tier 3 the author's ClyA-AS ensemble passes every gate over all 98 frames, recorded (IF-04, FR-01, FR-02, FR-03, FR-27, QR-12; §5.3.1 NOTE on `structure:`; WP18) |
| **VER-49** | The density map | One atom gives `g` exactly and two give `g₁ + g₂ − g₁g₂`, to 1e-15 in float64 and within the float32 store's rounding; on random clusters with coincident atoms the map is finite and within [0, 1], and a NaN or out-of-range value injected into a slab aborts the run naming the voxel; the truncated map differs from an untruncated evaluation, at every voxel, by no more than the sum of `g/(1 − g)` over the terms dropped there; two frames of one displaced atom average to `(g_a + g_b)/2`, not to their union; the grid nodes are integer multiples of the spacing, the axis is a node column, every kept term lies inside the box, and the node set is unchanged by permuting frames; each lookup route of the radius set resolves — a residue, a histidine name, `HIS` where the histidines agree, `ILE CD1`, `OXT` and each terminal patch — while an unknown residue, an unknown atom, a zero radius and a `HIS` atom the histidines disagree on are each refused naming chain, residue number, residue and atom; the shipped table equals PDB2PQR's `CHARMM.DAT` entry for entry; the map round-trips through `.npz` exactly and through OpenDX and CCP4/MRC, written in ångströms (§8.2.2 B10), whose own headers read without conversion carry ten times the origin and spacing in nm, with the origin, spacing and shape exact once read back into nm and the values within each format's precision, and a file whose origin is off the lattice of the spacing is refused; the stage-2 key is stable across processes, moves with every density key and with the radius file's digest, and a hand edit of the payload is recorded as one; a `grid_spacing_nm` outside [0.025, 0.05] nm and a non-positive or non-finite `sharpness` are refused naming the value; a `structure:` case walks to stage 3, while a full walk and a sweep are refused naming stage 4, `geometry:` beside `inputs.mesh` is refused naming both, and the stages are listed without importing their modules or numpy. At Tier 2 every heavy atom of the prepared 2WCD dodecamer resolves and its map is bounded; at Tier 3 the author's ClyA-AS ensemble runs over the paper's final 50 frames, DCD frames 48 to 97, recorded (FR-04, FR-27, IF-05, QR-12; §5.3.1 NOTE on `geometry.density`; WP19) |
| **VER-50** | The reduction to (r, z) | The annular weights sum to each annulus's exact area to 1e-11 relative, each interior cell's weights to its area, and the integral of a map is conserved slice by slice to 1e-12; an off-axis Gaussian matches the closed forms for the azimuthal mean, the Cₙ variance and the raw variance (WP19 plan, Design §2) for n = 7 and 12; an on-axis Gaussian and thin rings give a Cₙ variance below 1e-6, while the same computation without the detrend reads above 1e-4, so the test discriminates; a `cos(mθ)` modulation of amplitude b gives `b²/2` for both variances when n divides m, and otherwise a Cₙ variance of zero and a raw variance of `b²/2`; a synthetic C12 assembly deposited through stage 2 reduces unchanged to round-off when turned by 90°, to the float32 rounding of its map when turned by 30°, which maps it onto itself, and within the off-axis tolerances when turned by 15°, which does not; no harmonic is used below `n h/π`, the header names that radius, and the artefact round-trips, exports as three radial grids, and records a hand edit. At Tier 2 the prepared 2WCD reduces with its integral conserved to 1e-9 relative, its Cₙ variance nowhere above its raw variance by more than 1e-4, and an open lumen on the axis (FR-05, FR-06, FR-27, CON-04, IF-05; §5.3.1 NOTE on `geometry.density`; WP19) |
| **VER-51** | Contour extraction, conditioning and its gate | A square pyramid `1 − max(|r − r₀|, |z − z₀|)/a` centred on a node, linear along every grid edge, is contoured on its square to 1e-12, with the area `(2a(1 − l))² − h²/2` to 1e-12; a Gaussian section's contour lies within 1e-3 nm of its circle of radius `s√ln 4`, against a linear-interpolation bound of 4.7e-4 nm; Taubin scales the area of a regular 64-gon by its closed form `f(k₁)^{2N}` = 1.002770, where a Laplacian of the same N passes scales it by `(1 − λk₁)^{2N}` = 0.952933, both to 1e-12; closing and opening by 2h fill a 0.1 nm slot, remove a 0.1 nm fin and keep a 0.3 nm slot, within the corner-rounding bound `δ²(1 − π/4)` per corner, and the conditioned loop's feature size exceeds 2h; a void is filled and recorded with its area, an island is refused naming its centroid and area, and a lumen closed on the axis is refused naming its z range; each §5.2.1 criterion fires on a loop built to fail it, naming the criterion, the value, the threshold and the (r, z); the probe profile of a ring of atoms matches `√(ρ₀² + (z − z₀)²) − R_a` to 1e-12 and two frames give their mean; the artefact loads through `load_profile` as a `pipeline` profile, its key is stable across processes and moves with each constant that moves a vertex or a verdict, and a hand edit is recorded; the refusals of the §5.3.1 NOTE on `geometry.contour` hold, and a walk past stage 4 runs once stage 5 is delivered (the stage-5 walk refusal, which held until WP21). At Tier 2 the prepared 2WCD passes the gate and its payload loads as a profile; at Tier 3 the ClyA-AS ensemble's verdict and measurements are recorded (FR-07, FR-08, FR-27, QR-12; §5.2.1; §5.3.1 NOTE on `geometry.contour`; WP20) |
| **VER-52** | CAD assembly on any profile (stage 5) | A parallelogram body's widest-margin chord is its mid-line, with clearance half its perpendicular width; on the fixture the drawn (2.0, 3.5) and the derived chord give face areas equal to 1e-10 relative and equal edge-name counts; a profile translated by Δ with `centre_z_nm = Δ` gives the untranslated region; a body cut more than twice by a plane is refused by the one-face criterion, naming each face's centroid and area; each criterion of the §5.2.1 NOTE on the membrane junction fires on a profile built to fail it, naming the criterion, the value, the threshold and the (r, z); the `nanopnp/region/v1` record round-trips and rebuilds equal areas; the key is stable across processes, moves with each constant and records a hand edit; an edge lying on a bilayer plane extends the interval to its far end in each of the four orientations of a step flush with either plane (CODE_REVIEW_003 CR-4); the stage is listed without importing netgen; the refusals of the §5.3.1 NOTE on `inputs:` for `inputs.profile` hold. At Tier 2 the fixture through `inputs.profile` has 193 vertices and 195 edges named as VER-28's, the junction at 2.7524 and 4.88 nm over one node chain and no bilayer in the fluid (FR-09, FR-27, QR-12; §5.2.1 NOTE on the membrane junction; WP21) |
| **VER-53** | Meshing a generated region (stage 6) | `wall_h_nm: auto` is 0.05, 0.05, 0.03505 and 0.02715 nm at 0.05, 1, 3 and 5 M, crossing at 1.4741 M, and λ_D matches NUM-30's check values to 5e-4 nm; `size_scale` multiplies every size and temperature enters λ_D as √T; each refusal of the §5.3.1 NOTE on `numerics.mesh` names its key; a salt axis severs warm starts only where it moves the wall size; a coarse synthetic region meshes through VER-27 and VER-10, round-trips its content hash through MSH 4.1, gives one content hash in two fresh processes without importing Gmsh, fails the wall-size gate with its wall field withheld, naming the segment, and is refused without a `protein` permittivity; every consumer to the IF-07 export reads stage 6's file; a reproduced mesh with another content hash aborts naming both. At Tier 2 the fixture's element count is within 0.1 % of the drawn reference's and meets §5.2.2's quality band, and the prepared 2WCD meshes at the default sizes, passes both gates and walks to stage 12 with every stage keyed in the manifest (FR-10, FR-27, QR-08, QR-12, CON-10, NUM-30; WP21) |
| **VER-54** | The optional Gmsh backend (stage 6) | The region graph read from stage 5's glued shape has the record's edge-name counts and, in closed form, its face areas to 1e-9, every loop closed and counter-clockwise, every arc on the reservoir circle, and needs no Gmsh; an edge neither straight nor a reservoir arc is refused naming its midpoint. The coarse synthetic region meshes on both backends through VER-27, VER-10 and the wall-size gate with one vocabulary, each domain's triangle area equal to the record's less the circular segments its arc chords cut off to 1e-10, every region vertex a mesh node; a clockwise profile meshes with no inverted element, where a loop handed to Gmsh clockwise inverts every triangle of its face; two fresh processes give one content hash and write nothing to standard output; an open Gmsh session keeps its model and options; a Gmsh failure is refused quoting its log, classified with the gates; the stage-6 key names the backend and its settings, and netgen's equals the one recorded before the backend existed. Without the extra, a missing module or a native library the wheel could not load is refused at stage 6 naming the extra and the error, classified as a case refusal, and resolving and keying a Gmsh case imports no Gmsh; the lock names no component CON-12 excludes. At Tier 2 the reference fixture meshes on both backends to one vocabulary with its 185 profile vertices as nodes, Gmsh holds the wall-size gate at 0.05, 0.03505 and 0.02715 nm and VER-10 at `size_scale` 1, 2, 4 and 8, and WP22's frozen case conducts alike on both backends' meshes at `size_scale` 2: \|G_gmsh/G_netgen − 1\| ≤ 1e-3, eight times the measured 1.24e-4 and below the 2.0e-4 that refining netgen from `size_scale` 2 to 1 moves its own value. Every Gmsh-dependent test skips naming its reason where Gmsh does not import, and fails instead under `NANOPNP_REQUIRE_GMSH=1` (FR-10, QR-12, CON-10, CON-12; WP23) |
| **VER-55** | Geometry pipeline surfaced in the desktop shell | A third structural hook reports each stage's artefact after it is in the store, with the run record's schema and hash and whether the store already held it; a re-run reports every stage cached, and a watched walk and an unwatched one write one run record, one set of store entries and one manifest hash, the hook being bound after every key is taken. A spawned `upto: mesh` walk posts that report for each stage it stores and then finishes, writing no artefact when cancelled and leaving the convergence plot a plot of no solve. The geometry view-models import no Qt, NGSolve, Netgen, MDAnalysis, scikit-image, Shapely or Gmsh in a fresh process. A planted off-axis Gaussian's maximum lands in the display pixel centred on its (r, z), the top row at maximum z and r increasing to the right, the image's edges half a spacing beyond the first and last nodes; the stage-2 section of an axisymmetric map is symmetric about x = 0. The editor's move, insertion, deletion, undo and redo return exactly to the prior vertices; a self-crossing, negative-radius or coincident-vertex edit cannot be saved and is refused with the loader's own text, naming the vertex. The null edit reproduces its parent's vertices bitwise, records `source: hand-edit`, the parent's canonical digest as `sha256` and the parent's name, and re-derives every measurement; the edited reference fixture is refused as a reference. The derived case (`with_profile`) has no `structure:`, loads and resolves, and differs from the original only in `structure.*`, `inputs.profile.*` and any `geometry.density.*` or `geometry.contour.*` the original set away from its default, which it resets because stages 2 to 4 do not run, field by field over the schema walk. `measure` equals stage 4's `gate` record wherever the gate passes and reports its first refusal's criterion, value and (r, z) wherever it raises; on stage 4's own loop it reproduces the artefact's `gate` record exactly, against the stored stage-1 and stage-3 artefacts. A contour stage 4 refused is recomputed from the stored map as stage 4's conditioning computes it, fails first where the refusal named, and a hand edit of it records that map's payload digest. The null edit, run through the derived case, gives stage 5 the same model-frame profile to the bit and stage 6 the same mesh content hash under a new key; moving the constriction vertex 0.1 nm outward changes both, and the manifest records the profile by content and no stage 1–4 artefact. The render child draws a run's stage-6 mesh by material under the run's `viewer/`, never as an artefact, its element count the MSH file's triangle count and its gate figures the quality report's on that file. The packaging probe declares and exercises MDAnalysis, gemmi, scikit-image, Shapely and Gmsh, failing naming the payload that does not work. At Tier 2 the prepared 2WCD is built, measured, null-edited and moved as above (IF-09, QR-11, FR-27, FR-07, FR-08, CON-04, CON-09, CON-10, CON-11, RSK-13, §8.2.2 B8, B9; WP24) |
| **VER-56** | The physics-model interface | A walk of the package source outside `physics/` finds no concrete model class, no comparison or `match` against a registered model name and no model name spelt as a literal, except in `default_ladder`, which §6.5 defines as a path through named models, and, for the literal alone, the schema's default `physics.model` and the validated default case; the walk is shown to fire on the registry, on each form of dispatch it names and on each exempt scope once the exemption is lifted. Every refusal a declaration makes — an unhonoured switch value, solids or a supplied `inputs.charge` or `inputs.eps_r` beside a model that does not accept them (`pb` beside a fixed charge among them, PHY-24), an unadmitted `numerics.continuation`, an undeclared `outputs:` quantity, a builder's own refusal, a generated mesh beside a model without solids, and a solid domain on the mesh of a model without solids — names the model, the key and what is admitted; resolving a case builds its model and imports no NGSolve or Netgen. A declaration admitting `default_ladder` for a model the ladder does not end at is refused at registration, and a builder returning a model under another name is refused by `create`; the ladder's two Poisson–Boltzmann rungs, which state their own `λ_D`, are built for a salt the case-file `pb` refuses. Whether the PHY-02 distance field is read is asked of the built model, the rule every rung follows: the quick-start case as `pnp-ns` with its corrections on, which `pnp-ns` resolves to `none`, runs to stage 12 on the ladder and on a single rung, stores no distance field, restores, and equals the same case with every correction `none` bitwise. The stage-10 keys of `epnp-ns`, `pnp-ns`, `pnp`, `pb` and `pb-linear` on the quick-start case, and the model of every rung of both NUM-18 ladders on it, equal goldens recorded before the interface existed. A forwarding class defined in the test tree, subclassing no shipped model and registered at run time, runs a case file through stages 10 to 12; its state and stage-11 summary equal `pnp`'s on the same case bitwise, and stage 11 restores the forwarding class. `pb-linear` and `poisson` run from case files on a solid-free slab and equal direct API solves to 1e-12 relative, `pb-linear`'s with `λ_D` from `case_debye_length_nm`; a `poisson` case with a membrane and a supplied `volume_charge_density` equals the API solve given `fields.charge.assemble(scales)` likewise, and differs from the uncharged solve. At Tier 2 `poisson` reproduces the three-layer capacitor of PHY-20, whose piecewise-quadratic solution the P2 space contains, to 1e-10 of `max |φ̃|` (FR-20, FR-19, QR-14, PHY-20, PHY-21, PHY-24, §5.4.3; WP26) |
| **VER-57** | Protonation and the PQR artefact | On fragments of 2WCD chain A, every atom's charge equals `CHARMM.DAT`'s, parsed independently of PDB2PQR, to 10⁻⁶ e, and `Q_net` the hand count of the standard states; `titration: none` passes neither the pH nor a titration method, and gives identical charges at two pH values; PROPKA at a pH across a residue's pKa changes exactly that residue (`GLU 18`, `ASP 21`, `ASP 25` between pH 2 and 8); a histidine named `HSE`, with or without its hydrogens, protonates as the `HIS`-named one; a terminal pKa PDB2PQR does not apply is recorded as unapplied from PROPKA's groups and the applied charges. Each gate — an atom PDB2PQR could not parameterise, an atom without a charge or radius, a charged atom whose radius is not positive, a `Q_net` further than 10⁻⁶ e from an integer, a PQR not holding the frame it was given — fires on its defect and names the frame. The PQR reader reads PDB2PQR's fixed columns, its fused coordinates, its four-character residue names and fused atom fields, a patched residue by its variant name, and a whitespace-separated file, and refuses, naming the line, a line the two readings read differently; `MODEL` frames holding different residues are refused naming the frame; the writer reads back exactly. A supplied `inputs.pqr` with another frame count, a residue the ensemble lacks or the frames out of order is refused naming the frame; one rigidly moved registers to 0.01 Å; the stage's export re-supplied beside the same `structure:` gives the atom table bit for bit. One frame changed of two re-protonates one. Without PDB2PQR a `structure:` case is refused naming the extra before its first frame and `inputs.pqr` runs. The stage is listed, and a walk that does not name it records it not run, without importing PDB2PQR or PROPKA; each protonation key's refusal names its keys. At Tier 2 the prepared 2WCD dodecamer at pH 7.5 gives its pinned `Q_net` of −60 e, −5 e on every chain, with the PDB2PQR and PROPKA versions named on failure; every heavy atom's radius equals the stage-2 CHARMM table's; twelve terminal oxygens are added; `CYS 285` is unapplied in every chain and the `LYS 8` N-terminus exactly where its pKa is below the pH; the export supplied beside the structure gives the payload. At Tier 3, recorded, DCD frames 48–97 are compared residue by residue with the archived PQRs 50–99, and the archived PQRs register through `inputs.pqr` (FR-12, IF-03, FR-27, QR-12, PHY-16 step 3; WP27) |
| **VER-58** | The deposited fixed charge | PHY-16 step 5's kernel integrates to `q_i` to 10⁻¹² at `r_i/w` ∈ {0, 0.3, 1, 3, 30, 600}, is finite and even on the axis, and is the limit of the 3D Cartesian deposition binned by exact annular volumes, which converges to it at ≥ 3.5× per halving; the tiled separable sum equals the direct one to 10⁻¹³; an atom on the axis is short by `h²/(6w²)` unrenormalised and exact renormalised; a spacing above `w_min/2` is refused naming the atom. The projection's element moments against every monomial of degree ≤ `k` equal the lattice's to 10⁻¹², NGSolve's field equals the payload's, and a payload on a permuted mesh is refused by its geometry digest. At Tier 2 one atom in a grounded sphere, solved with `poisson`, against its Kelvin-image closed form: the `r`-weighted L² error over a 2 nm disc about the atom falls at a rate ≥ 2.5 between the finest two of three near-atom meshes with the `P2` deposit, and `P0`'s falls slower; the on-axis error and an unresolved atom beside `P0`'s are recorded (FR-13, FR-14, QR-03, PHY-16 steps 5–6, PHY-18; WP28) |
| **VER-59** | The dielectric field and the ion-exclusion shell | With both keys at 0, the region, mesh, fields and stage-10 keys of a profile-driven case, and its region record's bytes, equal goldens recorded before WP30; the fields and stage-10 keys are recomputed under stage 7's `v1` schema strings for that comparison, and also compared at `v2` (WP32 D15). **The shell:** on a parallelogram body every `wall` node lies at a distance in `[a − max(h_c²/a, a/100), a + 10⁻⁶]` nm from the body; the shell is one `exclusion` face, `wall` outside and `interface` against the protein and the membrane, and a body edge left facing the electrolyte beside a shell is refused naming it; the membrane, its chord and its junction equal the shell-free region's; a body within `a + h_c` of the axis is refused naming the z interval; a necked pocket is filled and recorded; `0 < a ≤ 2h_c`, the key beside `inputs.mesh` or without a profile, and a missing `structure` extra are each refused naming the keys; the record round-trips, rebuilds equal areas without Shapely and keys `a` only when it is non-zero; the Gmsh region graph reads its four faces; on netgen each shell `wall` edge is cut into at least `⌈L/(1.1 h)⌉` segments, so the shell meshes at 3 M (0.035 nm), where whole edges were refused; the manifest lists the switch and the mesh-material deviation. **The dielectric:** on the same body, along the normal at each water-facing edge's midpoint, the lattice `χ` equals `S(s/δ + 1/2)` to 4 × 10⁻³ for `\|s\| ≤ δ`, so its 1/2-level lies on the profile and its width is `δ`; `χ` is 1 in the membrane and in the protein away from water; the lattice's boundary samples are 0; `W` equals the region's protein-to-water edges; the range and registration gates pass, with `exclusion` below 1/2 on a 0.12 nm shell at δ = 0.2 nm, and an inverted derived `χ` fails registration; `δ < h_c` and `δ` beside `inputs.eps_r` are refused naming both keys. **At Tier 2:** through a generated shell on a cylindrical body at 0.1 M, solved with `pnp` at zero bias, the mid-plane potential across the shell is logarithmic in `r` and drops by `λ_enc ln(R/(R − a)) / (2π ε₀ ε_r,f⁰)` to 1 %, where `R` is the body's inner radius and `λ_enc` the mobile charge per unit length the shell encloses, and that drop is at least 10 % of the wall potential; VER-31's slab with its shell generated by this construction equals the drawn slab; the prepared 2WCD with `a` = 0.25 nm has every `wall` node at least `a − max(h_c²/a, a/100)` from the body, records the share beyond `a + 10⁻⁶` nm that the closing and the filled holes leave, and passes VER-10 and the wall-size gate, at 0.15 M and at 3 M with the wall segments averaging at most 1.1 times the target, and with δ = 0.15 nm added walks to stage 12 with every gate passing and both deviations in its manifest (FR-15, FR-09, FR-10, PHY-02, PHY-20, QR-12; §4.4 NOTE on the derived solid fraction; §5.2.1 NOTE on the ion-exclusion shell; WP30; the 3 M and edge-division clauses WP30 review) |
| **VER-60** | Charge pipeline surfaced in the desktop shell | On a profile-driven tube with a two-atom `inputs.pqr`, the artefact hook reports `protonation` and then `charge` after their store entries exist, both `cached` on a re-run, and a spawned `upto: charge` walk posts them after `region` and `mesh` and finishes, writing no artefact when cancelled. The charge map draws the export lattice as stored, the areal density in its `nanopnp/field/v1` quantity and unit, in the model frame, the top row at maximum z: the positive atom's pixel holds its maximum and the negative atom's its minimum; its trapezoid-weighted block means carry the record's `q_grid_e` to 10⁻¹² relative at `k` = 1 and at `k` = 7 with partial last blocks; zero sits at the centre of a diverging table whose limit is the largest magnitude drawn; the recorded worst planes are marked at their z. The conservation view shows each leg's value, tolerance and ratio as the record holds them, a doubled tolerance doubled, and a leg not run as not run with its reason. The protonation view switches the charges and `Q_net` between the frames of a two-`MODEL` PQR, and through PDB2PQR and PROPKA on `GLU 18`–`LEU 26` of 2WCD chain A shows 0 e at pH 2 and −3 e at pH 8, each frame's applied charges summing to it, the pKa column equal to the artefact's and the unapplied rows the summary's. The render child draws the coefficient the solve assembles, to `viewer/charge.*` and `viewer/chi.*` and never an artefact: `∫ ρ 2πr dA` at the solve's order equals `q_mesh_e` to 10⁻¹², and the derived `χ`'s mean over `protein` equals `material_means`. A generated shell's mesh lists `exclusion`. Each bounded number's spin range equals its schema bounds in both directions; an integer field steps by whole numbers, and a field that admits `null` is never a spin box, which cannot say "unset" (WP32); and a loaded pH of 7.25 is shown and not rewritten. `NEUTRAL_SECTIONS` is checked in both directions: a listed section written empty resolves as its absence, and keys every stage of 1 to 10 as its absence but stage 9, whose key is the validated dump and moves as the case hash does; every unlisted optional section is refused empty or resolves differently somewhere. The view-models import no Qt, NGSolve, PDB2PQR or PROPKA in a fresh process. The Charge tab drives the Geometry tab's run control to `upto: charge` and shows each stage's hash, the protonation row, the marked planes, the five legs and the deployed field under IF-07's name. The probe carries PDB2PQR and PROPKA, each exercised: the shipped fragment is the stage's own PDB of the deposited residues, its `Q_net` is 0 e at pH 2 and −3 e at pH 8, a stubbed data lookup fails naming `pdb2pqr`, and removed titration arguments, or PROPKA's parameter file out of reach, fail naming `propka`; the licence notice has a row for each payload. At Tier 2 the prepared 2WCD's picture carries −60 e to 10⁻¹² relative, its conservation view is its record, and its protonation view shows −60 e, no chain difference and the recorded unapplied rows, `CYS 285` and the `LYS 8` N-terminus in every chain (IF-09, QR-10, QR-11, FR-12, FR-14, FR-27, CON-09, CON-11, RSK-13, RSK-15, §8.1 Phase 3 increment; WP31) |
| **VER-61** | The subpackage layering | The subpackage import relation of `src/nanopnp`, read from the syntax tree by `nanopnp.validation.modularity` with no implementation module imported, equals `docs/project/modularity-layering.yaml` in both directions, separately for the static relation (imports at module scope, inside a function and under `TYPE_CHECKING`) and the string relation (a non-docstring constant naming a module, as the stage registry and `PUBLIC` do), and each row's `finding` is null or a row of `docs/project/modularity-findings.md` or `docs/project/review-findings.md`; the module graph of module-scope imports, with each package `__init__` an import runs on the way to its target, is acyclic, and a hand-built cycle through a package's `__init__` is found; the subpackage `top` import relation has no strongly connected components of more than one subpackage, verified with Tarjan's algorithm, and a module-scope `import nanopnp.mesh.primitives` in `geometry/analyte.py` fails naming the component `('geometry', 'mesh')` (H6; WP39); both `upward:` and `deferred_upward:` are empty (REV-05; WP39); and the measuring modules add no edge of their own. The `top` edges (module scope, outside `TYPE_CHECKING`) that point up the layer order of §8.2.8 H11 equal the file's `upward:` list in both directions, the `deferred` edges (imports inside a function) that point up it equal its `deferred_upward:` list in both directions (§8.2.8 H12), every row of either list names its finding, every subpackage has exactly one place in that order, and an edge from a subpackage the order does not place is refused naming it. An `import nanopnp.gui` substituted into `core/constants.py` fails naming `core -> gui`, the module and the line, and a recorded edge with no import behind it fails as removed; a module-scope import of `nanopnp.mesh.primitives` substituted into `geometry/analyte.py` leaves the static relation unchanged and fails as the upward edge `geometry -> mesh`, naming the module and the line, and the same import inside a function leaves both the static relation and `upward:` unchanged and fails as the `deferred_upward` edge `geometry -> mesh`, naming the module and the line; neither diagnostic offers recording the edge. A synthetic three-subpackage package is classified import by import into the four kinds, a relative import and a module-level `try` among them, its line numbers written by hand, and the strongly connected components and the lightest internal edges of a hand-solved graph are reproduced (§5.1, §8.2.7 G1, §8.2.8 H11, H12; WP35, WP37) |
| **VER-63** | The findings logs | Every `docs/**/*findings.md` declares `findings: {prefix, status, areas}` front matter, and a page with that front matter is so named; its first table has the columns `ID`, `Area`, `Severity`, `Status`, `Ruling` and `Finding`. Each row has a unique `<prefix>-nn` id, a declared area, a severity of `high`, `medium` or `low`, and a status of `open`, `accepted`, `fixed`, `deferred`, `post-1.0` or `declined`; an `open` row's ruling is `—`, a `fixed` row's links to a plan under `docs/plans/`, and any other's names a row of a `#### 8.2.N` section of this specification as `§8.2.N Xk`; its finding links to a heading of the report that exists. Under a `closed` header only `fixed`, `deferred`, `post-1.0` and `declined` are admitted. Every real log passes, and a log built in the test, valid but for one row, is refused naming the file, the line and the row for each defect (§8.2.7 G4; WP35) |
| **VER-64** | Stage conformance | Every registered stage class defines `describe`, `key(inputs)` and `run(inputs, *, progress, cancel)`, read from the syntax tree by `nanopnp.validation.modularity.stage_conformance` with no stage imported, and each constructed stage's `name` is its registry name; a stage written in the test without `key`, or with `key(inputs, cancel)`, does not conform; `pipeline/run.py` writes no collection of stage names, every one the walk uses being read from the registry. A stage is handed only the upstream artefacts it declares as inputs, and its own in the deviations pass; a walk to a stage runs that stage's transitive input closure, in walk order, so a walk to `protonation` on example 07 is `case`, `structure`, `protonation`, and a walk to `solve` on a depositing case includes `charge`. `nanopnp.validation.modularity.undeclared_reads` reads each registered stage's module, and the functions and methods it reaches, and finds no literal name passed to `require`, `upstream.get` or `upstream[…]` that the stage does not declare; the solve stage with `charge` taken out of its declaration is found, naming the stage, the name and the line. Each description's facts are the code's: `takes_workspace` and `takes_store` are its constructor's parameters, a stage whose `key_is_artefact` holds returns from `key` the artefact `run` returns, summary included and with no payload, and `needs_section` names an optional top-level case field outside `NEUTRAL_SECTIONS`, a `needs_section` naming no case section being refused by the walk, naming the stage and the section. Each declared optional input is one a shipped case drops while walking the stage, and the walks of those cases, written in the test, are unchanged; a stage whose case drops an input it does not declare optional is not walked, and is refused as the walk's target naming the input. `register` refuses, leaving the registry unchanged, an input that is neither `case_path` nor a stage registered before it, an optional input that is not one of its inputs and a weight of 0, −1, NaN or ∞; a description missing a fact is a `TypeError`. The walk's order, registration order with stage 9 first, equals the 13 names written in the test, and a stage registered later is walked after them (FR-27, IF-01; §8.2.8 H1; WP36) |
| **VER-65** | The backend guard | The subpackages with a module that imports `ngsolve` or `netgen` at module scope, inside a function or under `TYPE_CHECKING`, or that names a backend submodule or attribute in a non-docstring string (`"ngsolve.webgui"`, not the bare mesher name `"netgen"`), read from the syntax tree by `nanopnp.validation.modularity.backend_imports`, equal the `backend:` list of `docs/project/modularity-layering.yaml` in both directions, and that list is the eleven subpackages written in the test. An `import ngsolve` substituted at line 1 of `structure/axis.py` fails naming `structure`, the module and line 1; `density/grid.py` with its one backend import removed fails naming `density` as lost; a synthetic package is classified reference by reference into the four kinds, its line numbers written by hand, a bare `"netgen"` string and a package-relative import counted as none (QR-13; §8.2.8 H3; WP37) |
| **VER-66** | The backend registries | Each of the mesher, linear solver and stabilisation mode is a registry in the shape of §5.5, and `numerics.mesh.backend`, `numerics.linear.solver` and `numerics.stabilisation` are strings validated against them; an unregistered name of each key is refused naming the registered ones, in the same text in `check_document`, on the command line and in the editor; `register_solver("sparsecholesky", …)` is refused naming NUM-21, an unregistered solver `mumps` is refused naming its NUM-21 reason, and duplicate registration is refused. A stub mesher, solver and mode registered at run time in the test validate through `loads_case`, `check_document` and `nanopnp validate case`, and the editor offers them; on the quick-start pore a solve naming the stub solver forwarding to UMFPACK and stub mode forwarding to `none` equals the plain run bitwise, and both stubs record calls; a generated mesh using a stub mesher forwarding to netgen gives netgen's vertices and triangles exactly and keys the stub in its recipe. Gmsh registration imports nothing, and in a fresh process `registered_meshers()` contains `gmsh` with neither `gmsh`, `nanopnp.mesh.gmsh_backend`, `netgen` nor `ngsolve` in `sys.modules`; a borrowed Gmsh session leaves the caller's logger untouched, sequential cleanup steps run with failures attached as notes without masking the meshing error, and the session is always finalised (QR-11, QR-14, IF-03, CON-10, NUM-21, §5.5; §8.2.8 H7, H11, H12; WP39) |
| **VER-72** | Source conventions | Read from the source with no checked module imported: (a) a function-level import in `src/nanopnp` names only `nanopnp`, `ngsolve`, `netgen`, `numpy`, `scipy`, `meshio`, `h5py` or an optional extra's package; (b) no module imports another's private name beyond a recorded list with a reason per entry, which fails on an entry no longer imported; (c) no name the package defines (function, class, argument, assignment target) has an `-ize` ending, *size*, *seize* and *prize* excepted; (d) every `xfail` with reason `planned: WP<n>` is strict and names a planned, undelivered package; (e) every `name()` quoted in an Outcome of a plan from WP40 on is defined in `src/nanopnp`; (f) every `# pragma: no cover` states its reason. Each check is shown to fail on a substituted violation, naming its file, line and name (CLAUDE.md *Coding conventions*, *Implementation workflow*) |

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
| **VER-31** | Gouy–Chapman–**Stern**, 1D | `φ_0 = φ_d + σ_s λ_S/(ε₀ε_r)` with `φ_d` and `σ_s` from VER-12's Grahame relation, the shell carrying no space charge so `φ` is linear across it | The wall potential reproduced to better than **1 %** at 0.1 M, `ζ̃_d = 2`, `λ_S = 0.25 nm` — a 30.6 % effect, so a shell the solver treats as fluid fails by 24 %; `λ_S = 0` reproduces VER-12 on the same mesh to solver tolerance; the shell generated by stage 5's construction from the wall's body, clipped to the slab, is the drawn one to 10⁻¹² nm and gives the same `φ_0` (FR-15; the last clause WP30, with the cylindrical form through the pipeline in VER-59) |
| **VER-35** | End-to-end reproduction from the manifest | a case run to convergence, then reproduced from its run directory alone | Every scalar quantity of interest reproduced to better than the `1 × 10⁻⁶` nonlinear relative tolerance of §5.3.1, with the measured difference reported rather than only the verdict; run against a *fresh* store, with the store miss and the re-entry into Newton asserted, so that the cache cannot satisfy the check (the §5.3.2 QR-08 NOTE); an input file whose contents have moved aborts naming it; a library-version difference is reported and non-fatal unless the run asks for a strict environment (QR-08, IF-08) |
| **VER-39** | Sweep throughput and parallel scaling | one grid, run at several worker counts into a fresh store each time | Points per worker-hour over the members actually solved, and the parallel efficiency `T(1)/(N·T(N))`, reported with the core count, the thread pinning and the wave widths beside them. **Recorded, never gated**: completing the sweep is the assertion, and a scaling figure measured on shared hardware is a statement about that hardware (QR-06, §8.3) |
| **VER-42** | The reference-matching stabilised mode | the mode of NUM-14 exercised against the manufactured solution of VER-18, against the unstabilised solve on the same geometry under refinement, and against a mesh coarse enough to activate every term | On VER-18's manufactured solution the transport stabilisation converges at a **measured** L² rate, reported rather than asserted exact and gated only from below, one order short of VER-18's own rate by the NUM-14 NOTE on the approximate residual. That rate SHALL be measured in the mode that assembles the streamline term **alone**, because the prediction is about that term: the full reference mode additionally assembles the flow pair, whose own approximate residual costs a further order on a stable element pair, so a rate measured there would be the flow pair's wearing the transport term's name. The full mode's rate on the same problem SHALL also be measured and **recorded rather than gated**, together with the evidence attributing the difference to the flow pair — that the crosswind viscosity is identically zero on those meshes, and that the velocity error, which no transport term can reach, is the quantity that moves. The unstabilised mode on the same meshes still gives VER-18's rate, unchanged. The same run with the manufactured source withheld from the stabilisation residual SHALL be shown to change the term's effect visibly; the **direction** of that change is regime-dependent and SHALL NOT be assumed — where the manufactured problem is diffusion-dominated the source is the dominant part of the residual and withholding it switches the term off rather than corrupting it, raising the rate towards the unstabilised one, which a floor with no ceiling would pass. The assertion SHALL therefore be on the term's footprint against the unstabilised error on the same mesh rather than on the rate. On a mesh whose cell Péclet number exceeds 1 in the double layer, plain Galerkin trips the NUM-17 positivity gate and the stabilised mode converges without tripping it — the spurious negative concentrations §6.4.1 cites — and the crosswind term is active on a reported non-zero fraction of the sampled fluid and **nowhere** at or below unit cell Péclet number, which is the assertable form of "the same elements the NUM-12 warning names": that warning is a point sample and the viscosity is an element quantity, so the two counts are not comparable but the inclusion follows from the Cauchy–Schwarz bound of NUM-14 and SHALL be asserted sample by sample; on a mesh meeting NUM-30 the crosswind contributes exactly zero, asserted on the assembled term. The stabilised and unstabilised currents approach each other under refinement, with the measured rate reported and the difference asserted to fall at every level rather than against a fixed exponent, because the sequence reaches `O(h²)` from below and its coarsest interval is pre-asymptotic; the two extraction routes of NUM-24 and NUM-25 agree to NUM-26's tolerance in the stabilised mode, and disagree by the reported stabilisation contribution when that term is removed from the indicator route, so the identity is measured rather than assumed. The equal-order velocity–pressure pair converges in the mode that permits it and its velocity field is compared against the Taylor–Hood solve, **recorded and not gated**: it is an input to the §7.4 attribution rather than a verdict (NUM-03, NUM-11, NUM-12, NUM-14, NUM-15, NUM-24, NUM-26, VER-18) |
| **VER-62** | Number stability | the quantities seven gated walks compute — examples 01, 02 (both cases), 03 (the charged sweep, every member) and 07, and the charged 2WCD walk with and without the ion-exclusion shell and a derived `χ` — recorded on a tree that computes as `v0.4.0` does, in `tests/tier2/data/number_stability.json`, keyed per walk by the deployed mesh's content hash, each mesh listing the environments (`<sys.platform>-<machine>/<NumPy SIMD level>`) that deployed it | Every scalar of `current_A`, `currents_A`, `conductance_S`, `transport_number` and `eof_m3_s` the walk produces, and the 2WCD walks' `q_mesh_e`. On a mesh the golden holds, each within **10⁻⁸ relative** of that mesh's value. On a mesh it does not hold, each within the walk's *mesh-moved tolerance* of its reference mesh's value: 10 times the largest relative spread between the walk's recorded meshes, at least 10⁻⁸ and never above **10⁻³**; a walk with one recorded mesh has none, and an unseen mesh fails. In the *reference environment*, `linux-x86_64/X86_V3`, which CI and the gate pin (§7.6), an unseen mesh always fails. A failure prints the record to fold in; a gate never records itself, and a fold that would derive a tolerance above 10⁻³ is refused. A difference or an error estimate is never held, nor a value recorded as zero. A Tier-1 check asserts that every walk of the file is asserted by exactly one test, that no value is zero, that every mesh of a walk holds the same quantities, that each walk's reference mesh was deployed in the reference environment, and that each mesh-moved tolerance equals the one its meshes derive. A miss is investigated and reverted, or ruled a deliberate fix that amends its clause and re-pins the golden in the same commit (§8.2.7 G10; WP35) |

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

This implementation is compared with the reference on what the paper publishes: the current–voltage
relationships and the in-pore averages of its ePNP-NS results (VAL-16, VAL-17), which gate v0.7, the Phase 6 release (§8.2.5 E2, §8.2.6 F1).
The reference numbers are the paper's tables, shipped as test data, and the data behind its
figures, which the author supplies under `NANOPNP_REFERENCE_DATA` (§8.2.4 D6). The second route, VAL-01 to VAL-04, a field-by-field comparison against exported COMSOL
solutions, runs wherever exports exist, but no release waits on it.

On the field route, frozen cases spanning the envelope are compared field by field against exported
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
| **VAL-01** | Field comparison on the common probe grid | **Not required** (§8.2.4 D6); runs where exports exist. < 1 % relative L² error per field, once the preconditions above hold |
| **VAL-02** | Integrated-quantity comparison (`G`, `t₊`, `RR`, EOF rate) against the exports | **Not required** (§8.2.4 D6); VAL-16 compares the same quantities with the published results. < 0.5 % relative error, once the preconditions above hold |
| **VAL-03** | Reference-solution generation and archival, in Phase 1 | **Not required** (§8.2.4 D6), and not generated in Phase 1 (§8.2.3 C1); the harness ingests and refuses as below whenever a set arrives. Full reference set for the frozen cases archived with the generating model, independent of continued licence access, and **declaring** per field its source expression and its unit, and for the current its evaluation boundary and which electrode it references; a golden leaving any of those unstated is refused rather than interpreted. A golden's case identity names a fixed charge that stage 7 deposits by its stage-7 recipe: the stage-1 key's parameters, the protonation key's parameters without its gate tolerances, which move a verdict and never a charge, any input file's digest, and the kernel's parameters. It names a `χ` that stage 7 derives by its derivation parameters and the stage-1 key's parameters, and a non-zero `charge.exclusion_offset_nm` by the offset, because the ion-exclusion shell is a physics switch rather than a refinement of the geometry. Keys enter by their parameters, never their hashes, so an artefact schema string does not move an identity. A finished run's identity is read from the stage-1 and protonation artefacts the run recorded, never from the files its case names (§8.2.5 E3; OPN-07, closed) |
| **VAL-04** | Reference discretisation-error probe | **Not required** (§8.2.4 D6). The reference case re-solved at two refinement levels while licence access lasts, bounding the reference's own discretisation error |
| **VAL-05** | Geometry pipeline against the published boundary | Auto-generated contour compared against the delivered reference pore polygon (§5.2.1): radius profile and constriction radius within a stated tolerance. Measured on two inputs (§8.2.2 B2): the public 2WCD entry, gated at Tier 2 to a looser tolerance, and the author's ClyA-AS ensemble, archived under `NANOPNP_REFERENCE_DATA` and run at Tier 3; the Phase 2 gate requires the ensemble leg. Each leg's metric, registration and tolerance are stated, with their argument, in the NOTE on VAL-05 below (WP22) |
| **VAL-06** | Poisson-only comparison against APBS | Potential from the assembled fixed-charge and dielectric fields agrees with an APBS solve on the same structure within a stated tolerance. Two legs (§8.2.4 D3). The **gated** leg gives APBS, at zero ionic strength, our assembled charge and solid fraction as 3D maps, so that only the two solvers differ. The **recorded** leg runs APBS from the PQR with its own charge assignment and molecular surface, which measures the azimuthal averaging of CON-04. APBS runs from the test-only `apbs-binary` package on every CI leg its wheels cover, so VAL-06 is gated at Tier 2 on 2WCD and skips visibly where no wheel exists; the ensemble is recorded at Tier 3. The tolerance is stated, with its argument, by the work package that implements it, before the comparison is run: ≤ 3 % max, ≤ 1 % rms and ≤ 1.5 % on the axis, within a refinement budget of half of each (WP29 plan; NOTE on VAL-06 below) |
| **VAL-15** | The reference model's own `rhoq_pore` table, on our mesh | The delivered table reads with the grid its header declares, its planar integral is the declared `Q_net` to better than 10⁻⁹, and its boundary ring is negligible against its interior, so the producer leg of §4.4 is exact and the reference's 1.25 % is the consumer's (OPN-06); the consumer leg on the reference mesh is recorded with the mesh it came from, and the quadrature-agreement gate refuses it, per cent-level, rather than reporting a conserved number it cannot defend |
| **VAL-16** | Current–voltage relationships against the published results | The ionic current, conductance `G`, rectification ratio, cation transport number and electro-osmotic flow rate agree with the paper's published ePNP-NS results within a stated tolerance, at the published concentrations and biases. Two legs, as for VAL-06. The **gated** leg solves on the reference inputs, the §5.2.1 geometry and the delivered `rhoq_pore` table, so that only the solver differs. The **recorded** leg solves on the geometry and charge that stages 1–7 generate from the author's ensemble. Gates v0.7, the Phase 6 release (§8.2.4 D6; §8.2.5 E2; §8.2.6 F1). The tolerance is stated, with its argument, by the work package that implements it, before the comparison is run |
| **VAL-17** | In-pore averages against the published results | The pore-averaged ion concentrations, the peak radially averaged equilibrium potential, and the mobile charge in the pore with its wall and bulk split agree with the paper's published values within a stated tolerance. The same two legs, reference sources and tolerance rule as VAL-16. Gates v0.7, the Phase 6 release (§8.2.4 D6; §8.2.5 E2; §8.2.6 F1) |

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

NOTE (VAL-16 and VAL-17; §8.2.4 D6): the gated leg solves on the
reference inputs in the validated configuration, so a difference there belongs to the solver or to
the reference's own discretisation (RSK-09). The recorded leg solves the same cases on the geometry
and charge generated from the ensemble. Its difference from the gated leg is what the pipeline adds,
and it gates nothing. Every published number compared SHALL be declared with its unit and sign
convention. A current SHALL also declare the boundary it was evaluated on (`.knowledge/04` §6.6),
and an average its weight. The published pore averages may omit the `2πr` Jacobian
(`.knowledge/04` G6), so the declaration settles G6 and the comparison does not guess it. A
reference value missing its declaration is refused, as VAL-03 refuses a golden. The tolerances are
not QR-02's 1 % and 0.5 %. The published values carry no discretisation error bar, were solved with
streamline and crosswind stabilisation on, and are quoted to two or three significant figures. The
work package states each tolerance with that argument before the comparison is run. The published
correction-ablation percentages (`.knowledge/04` §6.5) are recorded beside the verdict. A
discrepancy that appears under one correction family alone localises to it, which recovers part of
what a field comparison would have localised.

NOTE: the reference model carries no mesh convergence study, so part of any residual difference may
originate in the reference (RSK-09). The project's own discretisation error is quantified first
(§7.3), and the residual is then attributed.

NOTE (the frozen cases, closing VAL-03's scope; author ruling): the reference set
is **five cases** on the §5.2.1 reference geometry, in the validated ePNP-NS configuration — the
four envelope corners 0.05 M and 3 M × ±200 mV, and the centre point 0.5 M / +50 mV. The corners
span the experimental range of VAL-07 and supply VAL-02 a matched opposite-bias pair at each salt,
so `RR` is comparable and not only `I`; the centre point separates a discrepancy linear in bias from
one quadratic in it. The §7.5.1 analyte case is **not** in the set. VAL-04's refinement pair is the
published mesh and one uniform refinement of it, on the centre case alone: RSK-09 needs a bound on
the reference's own discretisation error, not a field of them, and a comparison whose residual falls
below that bound SHALL be reported as *reference-limited* rather than as agreement. The bound and the
residual SHALL be taken over the same probe points: the margin band beside every fluid/solid
interface, which the comparison against the rungs drops, is dropped from `Δ_ref` too, although the
two exports carry values there. Kept, it would put the near-wall disagreement of the two
refinements into a bound on errors that never saw it, and the verdict would read
*reference-limited* too readily.

NOTE (VAL-05's metric, registration and tolerances; WP22; author
ruling of the same date): both legs compare polygons in the model frame. Ours is the stage-5
region's profile. The reference is the delivered 185-vertex table of §5.2.1. The comparison runs
on the 282 mid-planes `z_k = −1.85 + (k + ½)·0.05` nm, where the lumen radius is each polygon's
innermost crossing. The generated polygon SHALL cross every plane except within 0.1 nm of the
reference's tips. The rule binds the gated comparison; the recorded isolevel sweep compares each
level on the planes both polygons cross and records the rest, since a high level shortens the body
at both tips (WP22 Outcomes). With `Δ = r_ours − r_ref` and `r = r_ref`, three quantities are gated:

- `ε_G = 2 Σ (Δ/r) r⁻² / Σ r⁻²`, the first-order relative conductance change of a bulk series
  resistor, which is the phase plan's `G ∝ r²` made a number;
- the rms of `Δ`;
- `Δr_c`, the difference of the two minimum lumen radii over `z ∈ [−1.85, 1.6]` nm, each
  located on its own polygon.

| Leg | Tier | `\|ε_G\|` | `\|Δr_c\|` | rms `Δ` | Axial registration |
|---|---|---|---|---|---|
| ClyA-AS ensemble, DCD frames 48–97 (the Phase 2 gate) | 3 | ≤ 5 % | ≤ 0.1 nm | ≤ 0.1 nm | `centre_z_nm = 0` in the MD frame (G9) |
| Vendored 2WCD, chains A–L | 2 | ≤ 10 % | ≤ 0.1 nm | ≤ 0.2 nm | Cα centroid of residues 8–292 at `Z_MD = 5.655` nm, the MD structure's over DCD frames 48–97, which the Tier-3 leg pins to 0.01 nm (the centroid with residue 7 included is 5.63 nm and is not the reference; §8.2.4 D7) |

The argument for the tolerances follows. ±1 % on G (`.knowledge/04` G3) was a floor set while the
vertex list was unavailable. The author has since confirmed that the table was made with
`pqr2grid`'s radial binning at a 15 nm half-extent, an index-to-radius erratum worth about −8 % of
ε_G, and then by a hand edit that moved vertices by about the same amount the other way. Neither
step belongs to the method the pipeline implements, so ±1 % is unreachable by construction. The
tolerance is instead the method's own definitional uncertainty. The 25 % isolevel is unjustified
in the source (G2), and ±0.1 of isolevel moves ε_G by about ±5 %. The radius bounds are 2h, below
which stage 4 erases features by design. The 2WCD leg is looser because 2WCD lacks residues 1–7,
its hydrogens and the MD relaxation (§8.2.2 B2). No offset is fitted, and the isolevel is not
varied to pass. The isolevel sensitivity, the attribution to the erratum and the hand edit, one
frozen case's conductance on both meshes, the mesh figures and the FR-06 variance are recorded
beside the verdict (WP22 plan, D2–D11 and Design §1–§4).

NOTE (VAL-06's construction, metric and tolerance; WP29 plan; author
ruling of the same date): the problem is `poisson` on the case's deployed mesh with its stage-7
deposit, both electrodes grounded, and the fluid at the ion-free `ε_r,f⁰` (PHY-21 NOTE). APBS solves
the same problem at zero ionic strength (`lpbe`, no ions) at the case temperature, on a cubic grid
of 0.1 nm that holds all of the charge at least 1 nm inside each face. The box faces take our own
solution (`bcfl map`). Our domain's grounded outer arc and the membrane's natural edge cannot be
posed in APBS. A multipole boundary would assume a homogeneous far field, which the membrane slab
breaks. With the face data imposed, the leg compares the two interior solves, which is what it is
for.

On the **gated** leg, APBS's charge map is the stage-7 export lattice moved onto the grid nodes by
hat weights, conserving its charge and first moments. Its three staggered dielectric maps are the
permittivity the solve assembled, sampled on the deployed mesh and harmonically averaged along each
grid edge. The **recorded** leg keeps the box, grid and face data. It takes APBS's `spl4` charge
from the PQR and its `smol` surface, with the mesh's membrane imposed wherever APBS's map is on the
solvent side.

The probes are the nodes of the nested 0.2 nm grid that lie in a fluid material, at least 0.3 nm
from every solid and at least 0.4 nm inside the faces. APBS is read at its nodes. With
`Δ = φ_APBS − φ_ours` over the probes, three quantities are gated:

| Quantity | Tolerance |
|---|---|
| `e_max = max\|Δ\| / max\|φ_ours\|` | ≤ 3 % |
| `e_rms = rms Δ / rms φ_ours` | ≤ 1 % |
| `e_axis`, `e_max` over the probes on `r = 0` | ≤ 1.5 % |

Before the comparison, each solver's own error SHALL be estimated by refinement in the same run:
APBS by its 0.1 nm against its 0.2 nm solution, and ours by `P2` against `P3`. The difference is
taken as the error, a first-order bound. The sum of the two estimates SHALL lie within half of
each tolerance, or the run fails naming the budget, not the agreement.

The argument follows (WP29 plan, *Design* §4). Measured on 2WCD without forming `Δ`, the two
estimates sum to 1.22 %, 0.18 % and 0.58 % of the three norms. APBS's share is 0.98 %, 0.17 % and
0.57 %: its staircase of the protein surface, largest in the constriction. Halving the tolerance
for the two known errors leaves the other half for a disagreement, and a broken construction of
either input exceeds it (*Design* §6). The max norm is the looser of the three, because the
staircase layer meets the probes at 0.3 nm, which is three grid cells. The rms and axial norms are
the sharp ones. The tolerance is not re-argued after the comparison runs (§8.2.4 D7's reasoning).
On the analytic ring of the same plan, each solver is gated against the exact series at half of
each tolerance.

Measured (WP29, `tests/tier2/test_val06_2wcd.py`): on the protonated 2WCD at the
default sizes (44,985 elements), over 569,541 probes and the 93 on the axis, the budget is 1.20 %,
0.18 % and 0.59 % (APBS 0.95 %, 0.17 % and 0.58 %; ours 0.25 %, 0.010 % and 0.013 %). Zeroing the
charge moves the probes by 45 % rms, where 10 `τ_rms` is required, so the charge and not the faces
carries the comparison. The agreement is **0.41 %, 0.10 % and 0.23 %**, seven, ten and six times
inside the tolerance. A focused 0.05 nm grid on the lumen measures APBS's order at 1.6 in both max
and rms, so its 0.1-against-0.2 nm difference is the bound the budget assumes. On the ring
(`tests/tier2/test_val06_ring.py`) APBS and our `P2` are within 0.13 % and 0.010 % of the series in
the max norm, and each of the eight broken constructions exceeds half the tolerance. The recorded
leg's ring means differ from ours by 15.7 %, 6.7 % and 13.6 %, and the spread around a ring reaches
46 % of `max|φ|` (4.1 % rms). That is the azimuthal averaging of CON-04 together with APBS's own
charge and surface models, recorded and not gated.

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
| Every push, prose-only pushes included | The strict documentation build of VER-45 |

Every run SHALL emit a provenance manifest recording input hashes, library versions, mesh hash,
solver settings, stabilisation mode and correction parameter file versions (FR-25).

NOTE (a gated test's runtime; WP33): every push pays for the tests of
Tiers 1 and 2, so their runtime is a cost. It is reduced in four ways only: by sharing identical
work, by dropping work whose result no assertion reads, by coarsening a discretisation where every
gate the test carries is measured to pass at the coarser setting with at least three times its
headroom, or by splitting a file so that its parts run in parallel. No tolerance is loosened and no
oracle weakened to save time. A test that asserts a cold computation is never given a warm store.
A test moves to `slow` only if another test on every push gates the same claim on the same kind of
input, so that no requirement this tier gates is left ungated.

NOTE (the development selection; the WP33 follow-up): a Tier-1 or Tier-2
test that walks the pipeline end to end carries the marker `extended`: an executed worked example
of VER-46, or the vendored 2WCD entry taken through the stages. CI runs these tests on every push,
on every leg, so the table above is unchanged and no requirement leaves the push gate. The
development selection leaves them out unless `--extended` is passed or the test's file is named.
That selection is what `uv run pytest` and the commit hook run; the skills run the whole gate before
they push. The marker never goes on an analytic benchmark, which is the test that localises a
failure (§7.1); it goes only on the walks that compose stages whose claims a faster test also
exercises. A test is deleted, rather than marked, only when another test on every push gates the
same claim on the same kind of input.

NOTE (a golden asserted on more than one platform; WP35): a test that holds a computed number
against a recorded one, on every leg, asks one of two questions, and its tolerance follows the
question. Whether a change moved a number is asked on the mesh the number was recorded on, at
round-off, because one mesh and one build repeat bit for bit. Whether a platform's answer is still
right is asked on whatever mesh that platform deploys, and netgen's mesh moves with the platform and
with NumPy's runtime SIMD dispatch upstream of it, so it is held at a tolerance derived from the
spread measured between recorded meshes, with a stated safety factor and a ceiling well inside the
quantity's physical significance. The mesh's content hash decides which question a run answers; it
is never the assertion itself, except in one pinned reference environment, where a moved mesh is a
moved code path and fails. CI and the gate cap NumPy's dispatch at `X86_V3` with
`NPY_DISABLE_CPU_FEATURES`, so that every x86-64 Linux leg is that environment. VER-62 is the
instance, and `nanopnp.validation.stability` the mechanism a later golden reuses.

---

## 8. Implementation plan

### 8.1 Phases and gates

| Phase | Deliverable | Gate | Estimate |
|---|---|---|---|
| 0. Spike | Coupled ePNP-NS on an analytic cylindrical pore; continuation ladder; Tier 1 and Tier 2 suites (§8.2.1) | §8.2 exit criteria, as amended by §8.2.1 | 3–5 weeks |
| 1. Solver core | Production solver on an externally supplied mesh, full QoI extraction, frozen case-file schema, sweep runner | Tier 1 and Tier 2 pass; Tier 3 enabled and differences attributed; met as amended by §8.2.3 | 6–10 weeks |
| 2. Geometry pipeline | Structure and trajectory ingestion, density, symmetry reduction, contour, CAD, mesh | VAL-05: the auto-generated mesh reproduces the hand-conditioned reference geometry; met as amended by §8.2.4 D7 | 8–12 weeks |
| 3. Charge pipeline | PDB2PQR to smeared volumetric `ρ_fixed` and dielectric field | VER-01, VER-02 and VAL-06 pass | 3–5 weeks |
| 4. Polish and user testing | An exploration of the modularity of the implementation architecture, reported first, and the refactors the author accepts from it; the companion knowledge base restructured as an Open Knowledge Format bundle with a test-backed claim ledger (§8.2.6 F6); then a user-testing pass over the physics, the numerics, the Python API and the command line, in scripted sessions; v0.5 (§8.2.6 F3; §8.2.7) | The modularity report is merged, with each finding resolved or deferred by the author's ruling; the user-testing findings log is closed, each finding fixed or deferred by the author's ruling, both logs closed as a Tier-1 check reads them (§8.2.7 G4); no number of the pinned number-stability golden moves by more than 10⁻⁸ relative on a mesh it holds, nor beyond its measured mesh-moved tolerance on one it does not (§8.2.7 G10; VER-62); Tiers 1 and 2 pass | 4–6 weeks (§8.2.9 I5) |
| 5. Graphical interface | A design and requirements document with mockups, a visual-feedback workflow, then the desktop application its implementation plan sets; v0.6 (§8.2.6 F5) | QR-10, observed by a person: an experimentalist runs a case unaided; Tiers 1 and 2 pass | Set by the phase plan |
| 6. Validation and release | Full V&V suite in CI, documentation, JOSS paper, v0.7 (§8.2.5 E2; §8.2.6 F1) | Tier 4 passes (VAL-07 to VAL-10), and Tier 3 against the published results passes (VAL-16, VAL-17; §8.2.4 D6) | 4–6 weeks |
| GUI | One increment per phase from Phase 0 to Phase 3, then the dedicated Phase 5 (§8.2.6 F5) | QR-10: an experimentalist runs a case unaided, which is Phase 5's gate | Phase 5 |
| Documentation | Continuous track from Phase 1 onward, one increment per phase | VER-45 and VER-46 pass on every push | continuous |

GUI increments, one per phase to Phase 3 (ADR-004), then the GUI phase (§8.2.6 F5):

| Phase | GUI increment |
|---|---|
| 0 | Packaging probe: a trivial PySide6 and NGSolve `webgui` application that builds into a double-clickable Windows bundle |
| 1 | Case editor over the frozen schema, run control, live convergence plot, field viewer; meshes supplied externally |
| 2 | Geometry pipeline surfaced: load a structure, inspect the density, contour and mesh steps, override the contour by hand |
| 3 | Charge pipeline surfaced: pH selector, force field, charge map viewer, conservation report |
| 4 | None. The shell follows every change Phase 4 makes to the API and the case schema, so that QR-11 holds at v0.5, and gains nothing |
| 5 | The GUI phase: the design and requirements document and its mockups, the visual-feedback workflow, then the desktop application. The former Phase 4 increment (sweep builder, result browser, figure export, case comparison) is an input to the document, not a commitment |
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
| 5 | The desktop-application guide rewritten against the Phase 5 workflow, with the screens the visual-feedback workflow renders |
| 6 | Tutorials completed against the validated release, the JOSS paper, and the DOI-archived v0.7 (QR-15 in full; §8.2.5 E2, §8.2.6 F1) |
| post-1.0 | In-application tutorials, with the GUI track |

Phase 2 SHALL NOT start before the Phase 0 exit criteria are met.

NOTE (FR-19, FR-20): FR-19 is tagged
v0.4, the end of the scope the old v0.9 named, and its `pb` and `pb-linear` models shipped in
Phase 0. FR-20, the documented physics-model
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
`52fd531` (reported version `0.5.0a11.dev4+g52fd531b4`, which is `0.2.0a11.dev4+g52fd531b4` under the renumbering of §8.2.4 D1), on a Windows desktop. The executable opened
a window drawing a basic mesh with its controls. The author called it "still a bit janky", which is
a usability remark on the probe and not a packaging failure: the criterion asks that the bundle
build and open, and it did. Amendment A4's build and observation have both happened, so criterion 4
is met and RSK-13 is retired as a risk. The `bundle` job keeps detecting it on every push.

#### 8.2.2 Phase 2 decisions, agreed 24 September 2026

Rulings by the author, taken while planning Phase 2 (`docs/plans/phase-2-geometry-pipeline.md`).
Where a ruling changes a clause, the clause is amended in the commit named in the last column.

| # | Decision | Consequence | Clause changed, and when |
|---|---|---|---|
| B1 | Phase 2 starts only after the Phase 1 end-of-phase report has merged (tag `v0.2.0`) and the author has recorded the double-click observation of amendment A4 | The start condition of §8.1 is met as written, not amended: criterion 4 and RSK-13 close on the observation | None |
| B2 | VAL-05 is measured on two inputs. The public 2WCD entry (wwPDB, CC0) is vendored as test data and gated at Tier 2 to a looser tolerance. The author's 50-frame ClyA-AS ensemble, or the prepared structure it came from, is archived under `NANOPNP_REFERENCE_DATA` and run at Tier 3. The Phase 2 gate requires the ensemble leg | 2WCD lacks residues 1–7 at the *trans* constriction and the MD relaxation, so only the ensemble can be held to a tight tolerance. The 2WCD leg still exercises the whole pipeline on every push | §7.4 VAL-05, in the Phase 2 plan's commit. The tolerances are stated in the VAL-05 work package |
| B3 | The case schema moves **once**, to `nanopnp/case/v2`, in the first Phase 2 work package. That move carries every key Phases 2 and 3 are foreseen to need, among them stage-4 hand substitution under `inputs:` and the membrane's axial position. A v1 document reads losslessly as v2 | The §5.3.1 compatibility rule stands: adding a key moves the version, and it moves once rather than once per phase | §5.3.1, in the first Phase 2 work package |
| B4 | The Python floor rises to 3.11 (Python 3.10 reaches end of life in October 2026) | One MDAnalysis (2.10) and one GridDataFormats (1.2) across the supported range, as §2.6 names them. The IF-05 NOTE's conditional CCP4 write side is retired | QR-09 and §2.5, in the Phase 2 plan's commit. The IF-05 NOTE, `requires-python` and the CI matrix change with the code, in the first Phase 2 work package |
| B5 | The radius-profile criterion of stage 3 and §5.2.1 is checked against a probe-radius profile computed in project code on the aligned structure. HOLE, through `mdahole2`, becomes an optional cross-check that skips when absent | HOLE is a compiled binary with no wheel, so it cannot sit on the end-user path (CON-07, QR-09) | §5.2 stage 3 and §5.2.1, in the Phase 2 plan's commit |
| B6 | The author's contour script is available (OPN-02) | It is read before the contour work package is planned, as RSK-06 intends. The specified pipeline remains the fallback | §10 OPN-02, in the Phase 2 plan's commit |
| B7 | FR-20 moves to Phase 3. The optional Gmsh mesher adapter of ADR-002 is delivered in Phase 2 | Phase 2 stays on the geometry chain. The Gmsh backend is optional and never imported on the default path (CON-10) | §8.1 NOTE, in the Phase 2 plan's commit |
| B8 | The desktop bundle carries the optional Gmsh backend (while planning WP24) | `numerics.mesh.backend: gmsh` runs in the bundle; netgen stays the default, so CON-10 holds. The bundle is already GPL-2+ under CON-11, so Gmsh's licence adds no obligation; the packaging probe imports and exercises it and the licence notice names it | The ADR-004 packaging NOTE and VER-55, with the WP24 code |
| B9 | The shell's contour editor may start from a loop stage 4's gate refused (while planning WP24) | A refused gate writes no artefact (QR-12), so otherwise there is nothing to override. The loop is recomputed from the stored stage-3 map by stage 4's own conditioning; the edit is saved as a supplied profile with `provenance.source: hand-edit`, gated as §5.2.1's NOTE on a supplied fixture states, and stages 5 and 6 apply their gates unchanged. The §5.2.1 criteria are measured and shown, not enforced | The §5.3.1 NOTE on `geometry.contour`, in the WP24 plan's commit |
| B10 | The stage-2 density map is exported in ångströms (while planning WP25) | CCP4/MRC defines the cell in ångströms, and viewers read OpenDX in ångströms, so the map overlays the aligned structure's PDB export, which is in ångströms by its format. Inside the package, and in the native `.npz`, lengths stay in nm. The `field1` grids stay in nm, as their header declares | The IF-05 NOTE on length units and VER-49, in the WP25 plan's commit. `DensityMap.export` and `read` change with the WP25 code |

#### 8.2.3 Phase 1 exit, agreed 24 September 2026

The Phase 1 gate of §8.1 is "Tier 1 and Tier 2 pass; Tier 3 enabled and differences attributed".
The end-of-phase report (`docs/plans/phase-1-solver-core.md`) measures the phase against it.

| # | Amendment | Consequence |
|---|---|---|
| C1 | The gate's last clause is met by Tier 3 being **enabled and its attribution machinery verified**: the four-rung ladder against a self-golden, with `golden_source: self` on every report. The attribution of differences **against COMSOL** is recorded as outstanding until the author's reference exports exist (VAL-03, `docs/validation/comsol-export-contract.md`). When they land, it is reported as an addendum to the Phase 1 report, and it gates nothing retroactively. v0.2.0 is released on this basis | Phase 1 closes without the one comparison that needs data the project does not yet hold. The consequence is the same as A2's: a risk stays open longer than planned, here RSK-09 (a Tier-3 discrepancy originating in the reference) and the attribution of any residual. Nothing in Phase 2 touches a weak form, so the addendum can land at any point without re-opening a Phase 2 result. **Superseded 30 September 2026** (§8.2.4 D6): the exports are no longer required, so no addendum is owed, and the comparison against the published results gates v1.0 instead |
| C2 | The §8.3 reference sweep (3,675 points on 12 cores) is planned and checked in, but not run. QR-06's scaling is measured on 4 cores (VER-39, recorded and never gated) | QR-06 remains a SHOULD, measured only at the scale the development machine allows. The day-scale run is the author's to make, on HPC hardware |

Phase 0 criterion 4 is not changed by this section. It was closed by the author's double-click,
recorded in the NOTE to §8.2.1 on the same day, which met the last condition of §8.2.2 B1.

#### 8.2.4 Phase 2 exit and Phase 3 decisions, agreed 30 September 2026

Rulings by the author, taken while closing Phase 2 and planning Phase 3
(`docs/plans/phase-3-charge-pipeline.md`). Where a ruling changes a clause, the clause is amended in
the commit named in the last column.

| # | Decision | Consequence | Clause changed, and when |
|---|---|---|---|
| D1 | Versions are renumbered so that the minor version names the phase: Phase 0 is v0.1, Phase 1 v0.2, Phase 2 v0.3, Phase 3 v0.4 and Phase 4 v1.0. The existing tags are re-created on the same commits under the new names, and the old names are retired | Each phase closes with its own release, and no release spans two phases. A manifest written before the renumber records the old version, and the head of `CHANGELOG.md` maps it | §2.7 (the table and the Versioning NOTE), the Release column of §3.2 and the §8.1 NOTE on FR-19 and FR-20, in the renumbering commit |
| D2 | The fixed charge is each atom's 3D Gaussian averaged over the azimuth in closed form, and deposited onto the deployed mesh with each atom renormalised to its own charge. No 3D grid is built | The total is conserved by construction, so VER-01 guards the construction, while VER-02's per-slice check and a closed-form potential discriminate. VAL-15's consumer-leg aliasing cannot arise on the producer path. The reference's 2D (r, z) Gaussian is not reproduced (PHY-17), and its difference is measured at Tier 3 | PHY-16 steps 4–6 and a NOTE, PHY-18 and §5.2 stage 7, in the Phase 3 plan's commit |
| D3 | VAL-06 runs APBS in CI, through the test-only `apbs-binary` package, with a gated like-for-like leg and a recorded leg from the PQR | The Phase 3 gate is evidence on every push, not a nightly record. `apbs-binary` has no Windows wheel, so VAL-06 skips visibly there and is required on Linux and macOS | VAL-06 in §7.4, §2.6 and §5.2 stage 7, in the Phase 3 plan's commit |
| D4 | Protonation runs on every selected frame, as the reference did. `inputs.pqr` takes a single-frame PQR or a multi-MODEL PQR, one MODEL per frame | `Q_net` and the protonation states are recorded per frame, and a per-chain difference is a diagnostic, never symmetrised. The schema does not move: `inputs.pqr` keeps `format: pqr` and reads either form | The §5.3.1 NOTE on `inputs:`, in the work package that consumes `inputs.pqr` |
| D5 | FR-15's ion-exclusion shell is built in Phase 3, beside the smoothed solid fraction | Both are deviations that default to off. A non-zero `charge.exclusion_offset_nm` adds the `exclusion` region to stages 5 and 6 | None: FR-15 stands as written |
| D6 | Tier 3 compares the current–voltage relationships and in-pore averages the paper publishes (VAL-16, VAL-17), and that comparison gates v1.0. The reference is the paper's tables, shipped as test data, and the data behind its figures, which the author supplies under `NANOPNP_REFERENCE_DATA`. The gated leg runs on the reference geometry and charge, and a recorded leg on the pipeline's. The COMSOL field-export route (VAL-01 to VAL-04) and its harness are kept, but no release waits on them | The author chose the published results over producing the field exports of the export contract, and asked for the comparison to gate v1.0 so that the reference data can follow. Those results are what the model is cited for, need no licence and cannot lapse, which retires RSK-14. They localise a discrepancy less than fields would, so the Tier-2 benchmarks keep that job, and the ablation percentages are recorded beside the verdict. The Phase 1 addendum of §8.2.3 C1 is withdrawn. Phases 2 and 3 are unaffected | §2.7, QR-02 and its rationale, §7.4 (its preamble, VAL-01 to VAL-04, the new VAL-16 and VAL-17, and their NOTE), §8.1 Phase 4, §8.2.3 C1, RSK-09, RSK-14 and Appendix A, in this commit |
| D7 | Phase 2 closes with criterion 3 waived. On the ensemble leg VAL-05 measures `ε_G` = −5.56 % against the 5 % tolerance, while `Δr_c` = −0.039 nm and the rms of 0.089 nm pass. The tolerance is not changed, and the Tier-3 test keeps asserting it. `Z_MD` is corrected to 5.655 nm, as WP22 D6 provides | The miss is 0.56 pp, inside the definitional uncertainty the tolerance was argued from: on the ensemble, ±0.1 of isolevel moves `ε_G` by −7.4 and +6.6 pp, not the ±5 pp measured on 2WCD. The D7 attribution puts the gap in the reference's hand edit, which widened the lumen by 0.187 nm and which the method does not reproduce by design. A solve on the generated mesh gives a conductance 4.40 % below the fixture's. Re-arguing the tolerance after the result would weaken every tolerance stated before its run (VAL-06, VAL-16, VAL-17), so the miss is recorded, not absorbed. What the geometry costs in current is measured at v1.0 by VAL-16's recorded leg. The measured `Z_MD` is 5.6553 nm, 0.025 nm above the constant, which had included residue 7 (5.6293 nm). Re-registered, the 2WCD leg passes D5 at `ε_G` −8.49 % | §8.1 (Phase 2) and the §7.4 NOTE on VAL-05 (the 2WCD registration), in the Phase 2 report's commit. v0.3.0 is released on this basis |

#### 8.2.5 Phase 3 exit and the Phase 4 release, agreed 3 October 2026

Rulings by the author, taken while planning WP34, the last Phase 3 work package
(`docs/plans/wp34-phase-3-close.md`). Where a ruling changes a clause, the clause is amended in the
commit named in the last column.

| # | Decision | Consequence | Clause changed, and when |
|---|---|---|---|
| E1 | Phase 3 closes on its Tier 1 and Tier 2 evidence. The ensemble half of the phase's second criterion (VER-01 and VER-02 on the ensemble at Tier 3) and the end-of-phase report's numbers that need the author's archive are waived from the Phase 3 close and carried to Phase 4. Those numbers are `Q_net` per frame, protonation agreement with the archived PQRs, the deposition against the delivered `rhoq_pore` table, VAL-06's recorded leg on the ensemble, and the end-to-end charged case against the reference mesh and table | Every waived item was a recorded Tier-3 leg that gated nothing, and none is a property the 2WCD legs do not already gate. The Tier-3 tests stay as written and run when the archive is supplied. Their numbers are reported in Phase 4's end-of-phase report, beside VAL-16's recorded leg, which needs the same archive. v0.4.0 is released on this basis | None in this section's text. The Phase 3 plan's verification section and end-of-phase report record the waiver, in WP34 |
| E2 | Phase 4 is released as **v0.5**, not v1.0, because the project is not yet ready for a stable release. Phase 4 keeps its deliverable and its gate (§8.1). v1.0 becomes a later stable release whose content and gate the author defines (OPN-08). The retired `v0.5.0` tag names are reused for Phase 4, and a pre-renumber manifest recording `0.5.0aN` is read by its `created_at` | Every requirement tagged v1.0 is a Phase 4 requirement and is retagged v0.5. Where an earlier ruling in §8.2 (A1, C1, D1, D6, D7) says v1.0 for Phase 4's release, it now reads v0.5. Phase 5's v1.5 and the post-1.0 backlog do not move, and IF-01's "before v1.0" still names the stable release. The stray retired tag `v0.5.0-alpha.5`, left on origin by the 30 September renumber on the commit of `v0.2.0-alpha.5`, is deleted before Phase 4 tags its first package | §2.7 (the table, the tag values and the Versioning NOTE), the Release column of FR-21, FR-22 and FR-28, QR-02, QR-15 and its NOTE, §7.4 and VAL-16 and VAL-17, §8.1 (Phase 4 and the documentation increment), §8.3 and Appendix A, in the WP34 plan's commit |
| E3 | A golden's case identity represents a fixed charge that stage 7 deposits by the **stage-7 recipe**. That is the stage-1 key's parameters and the protonation key's (the structure or PQR digest, the frames, pH, force field and titration, without the gate tolerances), together with the kernel's physical parameters. A `χ` that stage 7 derives is represented by its derivation parameters and the stage-1 key's parameters. The export lattice's spacing and the element order are left out, as discretisation | It closes OPN-07. The identity is still computed from the resolved case without running a stage, and it reads no lattice. Non-producer identities and every solve key are unchanged, and `fields.charge` keeps meaning "supplied" | §10 OPN-07, in the WP34 plan's commit. The implementation and its VAL-03 test are WP34's |
| E4 | NUM-07's open question, whether the coupled models' `r`-weighted forms gain one quadrature order as `poisson`'s do, is measured in WP34 and decided in Phase 4 | No number moves in v0.4.0. The measurement goes into the NUM-07 NOTE, and the decision is taken with VAL-16 and VAL-17, which can judge it | The NUM-07 NOTE, in WP34 |
| E5 | The end-of-phase report is written in WP34, and WP34's last commit on `main` is tagged `v0.4.0` alone, with no `v0.4.0-alpha.9` | The release commit is the one that merges the report, as the Versioning NOTE of §2.7 requires, without a second tag on the same commit | None |

#### 8.2.6 Phases 4 to 6 re-planned, agreed 4 October 2026

Rulings by the author, taken while WP34, the last Phase 3 work package, was still planned
(`docs/plans/wp34-phase-3-close.md`). Where a ruling changes a clause, the clause is amended in the
commit named in the last column.

| # | Decision | Consequence | Clause changed, and when |
|---|---|---|---|
| F1 | The validation and release phase is **postponed to v0.7** and renumbered **Phase 6**, its deliverable and gate unchanged. Two phases are inserted before it: **Phase 4**, polish and user testing (v0.5, F3), and **Phase 5**, the graphical interface (v0.6, F5). The minor version still names the phase (§8.2.4 D1) | The validation phase's gate waits on data the author holds (§8.2.4 D6, §8.2.5 E1), and the two inserted phases do not, so the waiting goes to work that can proceed. Every requirement E2 retagged v0.5 is retagged v0.7. Where an earlier ruling (A1, C1, D1, D6, D7, E1, E2, E4) names Phase 4, or v1.0 or v0.5, for the validation release, it now reads Phase 6 and v0.7. So E1's carried numbers are reported in Phase 6's end-of-phase report, and E4's NUM-07 decision is taken in Phase 6 with VAL-16 and VAL-17. IF-01's "before v1.0" still names the stable release, and OPN-08 is unchanged in substance | §2.7 (the table, the tag values and the Versioning NOTE), the Release column of FR-21, FR-22 and FR-28, QR-02, QR-15 and its NOTE, §7.4, VAL-16 and VAL-17, §8.1, §8.3, OPN-08 and Appendix A, in the commit amending the WP34 plan |
| F2 | The `v0.5.0` names E2 reused go to the polish phase, Phase 4 | Phase 4's work packages are tagged `v0.5.0-alpha.1` onwards. A manifest recording `0.5.0aN` is read by its `created_at` as E2 states, and after 30 September 2026 it is the polish phase's. `v0.6.0` and `v0.7.0` were never used. The stray `v0.5.0-alpha.5` is still deleted before Phase 4 tags its first package | The §2.7 Versioning NOTE, in the commit amending the WP34 plan |
| F3 | **Phase 4 opens with an exploration of the modularity of the implementation architecture**: the stage boundaries and FR-27, the coupling between subpackages, and the extension points of FR-16, FR-20 and QR-14 and of the mesher and solver backends. Its report is merged before the user-testing pass is planned. The pass covers the physics, the numerics, the Python API and the command line, in **scripted sessions the author runs** against a test protocol the phase writes. Its findings are kept in a log | The gate is that the report is merged with each of its findings resolved or deferred by the author's ruling, the findings log is closed with each finding fixed or deferred by the author's ruling, and Tiers 1 and 2 pass. No one outside the project is on the phase's critical path. Phase 4 has no GUI increment, but QR-11 holds: the shell follows every change | §2.7 and §8.1, in the commit amending the WP34 plan |
| F4 | **The case schema and the public API may change in any phase before v1.0**. IF-01's stability promise starts at v1.0, which supersedes "stable from v0.2 onward" and B3's single move | A schema change still moves the version by the §5.3.1 compatibility rule, and whether a document of an earlier version still reads is decided with each move. A change to `nanopnp.PUBLIC` is still a decision recorded in `tests/tier1/test_public_api.py`. Each break is listed in `CHANGELOG.md` with its migration. QR-08 is unaffected, because a run is reproduced with its recorded library versions. **Refined 5 October 2026** (§8.2.7 G6): the schema's identifier names the release that ships a move, and a document of an earlier identifier reads as its upgrade | IF-01 and its NOTE, in the commit amending the WP34 plan |
| F5 | **Phase 5 opens with a GUI design and requirements document, mockups, and a visual-feedback workflow** through which the implementer renders and inspects the shell's screens without a display (the Qt widgets offscreen, the `webgui` page in a headless browser), and only then writes its implementation plan. The requirements the document settles enter this specification as identifiers, tagged v0.6, in the same commit. The phase absorbs the former v1.5 row: the case builder, live convergence monitoring and field visualisation are Phase 5's, and installers for all three platforms and in-application tutorials stay post-1.0. The continuous GUI track ends at Phase 3 | QR-10, observed by a person, is Phase 5's gate, and VER-43, VER-44, VER-55 and VER-60 keep gating the shell. RSK-15 now runs ahead of validation, so its mitigation is restated: the shell surfaces only capabilities that Tiers 1 and 2 verify, holds no physics, and no workflow depends on a Tier-3 number. The author accepts the residual risk that a Phase 6 finding changes a number the shell shows, or forces rework of a screen | §2.7, §8.1 (the GUI track and its increments, the documentation increments) and RSK-15, in the commit amending the WP34 plan |
| F6 | **The companion knowledge base becomes an Open Knowledge Format (OKF) v0.2 bundle**, in a Phase 4 package after the modularity report and before the user-testing protocol. One concept file per `##` section of today's files, in one directory per file, each with OKF frontmatter (`type`, `title`, `description`, `tags`, `sources` with stable ids cited per claim by footnote). Every citation of the form `.knowledge/0N §x`, history included, is rewritten to a bundle path. Every `[tested]` claim names the test that re-establishes it, inline, and a claim no existing test re-establishes gets one; the concept's `verified` list carries one `process:<test node id>` per distinct test, and author rulings carry `human:willemsk`. Agent-written concepts record `generated.by: claude-code/<nanopnp version>`, never a model identifier. A library-behaviour concept records the versions it was tested at in a `tested_with` key, checked against `uv.lock`; OKF's `stale_after` is not used | The knowledge base's purpose, provenance, trust and freshness, is OKF's, and its finest unit of trust becomes machine-checkable: a Tier-1 check SHALL refuse a non-conformant concept, a citation that resolves to no concept or heading, a `[tested]` claim naming no collected test, a `verified` list that disagrees with its inline markers, and a `tested_with` version that `uv.lock` has moved past. The format is checked in project code against the pinned v0.2 text; OKF's reference agent is not a dependency. The evaluation and the open questions for the package's plan are in `docs/plans/okf-knowledge-bundle.md` | §8.1 (Phase 4) and the §11 NOTE, in the commit recording this ruling. §11's table, the `CLAUDE.md` maintenance rule and the documentation build change with the package |

#### 8.2.7 Phase 4 decisions, agreed 5 October 2026

Rulings by the author, taken while planning Phase 4 (`docs/plans/phase-4-polish-and-user-testing.md`)
after Phase 3 closed as `v0.4.0`. Where a ruling changes a clause, the clause is amended in the
commit named in the last column.

| # | Decision | Consequence | Clause changed, and when |
|---|---|---|---|
| G1 | **The modularity exploration delivers a report and a guard.** The report holds numbered findings (`MOD-nn`). A committed script produces its measurements: the import-dependency matrix, the stage protocol's conformance, and the extension points of FR-16, FR-20, QR-14 and the mesher and solver backends. A Tier-1 test pins the layering the report records, so no later package can regress it. The package refactors nothing | Each finding is ruled before any code moves, as F3's gate intends, and every number in the report can be reproduced. The guard is checked in project code, so no dependency enters the lock | None. The guard's identifier is claimed by the package |
| G2 | **Every refactor the author accepts from the report lands before the user-testing protocol**, whether it is visible to users or internal | The testers judge the surface v0.5 ships. The sessions wait for the refactors. **One exception, 5 October 2026** (§8.2.8 H2): `MOD-11` is decided after the sessions | §8.1 (Phase 4's deliverable), in this commit |
| G3 | **The OKF work is two packages, joined by a ratchet.** The first builds the bundle, rewrites the citations and adds the F6 Tier-1 check. That check carries a committed list of the claims not yet backed by a test, and the list may only shrink. The second package backfills the tests and empties the list, and from then on the check refuses any unbacked `[tested]` | Each PR can be reviewed on its own terms: one is a mechanical move, the other is tests whose oracles need physics review. The push gate never carries a half-finished ledger | None. F6 stands, and so does the input note `docs/plans/okf-knowledge-bundle.md`, whose open question 1 this settles |
| G4 | **The findings are logged in the repository, and a test checks the logs.** Each log is a Markdown table under `docs/`, one row per finding, giving its id, area, severity, status and the ruling behind that status (a §8.2 row or a work-package plan). A Tier-1 check refuses a malformed row at any time. Once the log's header says `closed`, it also refuses a row whose status is not terminal | The gate's "each finding fixed or deferred by the author's ruling" is a test, and the close package flips both headers | §8.1 (Phase 4's gate), in this commit |
| G5 | **The sequence**: the modularity exploration; the refactors it leads to; the OKF bundle and then its backfill; the user-testing protocol; the author's sessions; the fixes the sessions lead to; the documentation increment; the close. Everything after the exploration stays provisional until `/phase-plan amend 4` plans it, once after the report and once after the sessions | The OKF bundle follows the refactors, so the test node ids it writes are not renamed under it | None |
| G6 | **The case schema moves as needed until v1.0, and its identifier keeps step with the package's releases.** The identifier a move takes names the release that ships it (`nanopnp/case/v0.5`, `v0.6`, `v0.7`), and the stable schema at v1.0 is `nanopnp/case/v1.0`. Between a release's work packages the schema may change under that release's identifier, and the identifier is fixed when the release is tagged. A document of any earlier identifier is read as its upgrade | The author said that the final schema is released with v1, and that until then the schema keeps step with the package's v0.x.y releases. F4's "whether a document of an earlier version still reads is decided with each move" becomes "it reads, upgraded, or is refused naming its migration". The manifest's package version identifies a revision inside a pre-release | The §5.3.1 NOTE on the compatibility rule, in this commit. IF-03, the stage-9 row of §5.2, §5.3's format table and the texts of VER-43 and VER-47, in the package that first moves the schema |
| G7 | **The user-testing protocol is executed by the push gate, and findings come only from the author's sessions.** Each script's commands and code run verbatim in the gate, as an example's do (VER-46). An agent may dry-run a script to debug it, and a dry run records no finding | The protocol cannot go stale between its package and the sessions. The findings are those of a tester who did not write the code (F3) | None |
| G8 | **A `[verified]` claim whose arithmetic can be executed gets a Tier-1 test** and becomes `[tested: …]`. A claim that cannot be executed, such as the reading of a source or the conversion of a printed figure, stays `[verified]` with its source footnote required, under a `process:arithmetic` actor. G3's ratchet covers both kinds | This is consistent with K6. A test never restates a printed number against itself | None. It settles the input note's open question 2 |
| G9 | **The input note's open questions 3 to 7** (each file's preamble, `00-index.md`, the `type` vocabulary, `log.md` and the documentation site) **are left to the first OKF package's `/wp-plan`**, which puts them to the author | They are package-level decisions, and none of them changes the sequence | None |
| G10 | **No physics number moves silently.** The exploration package records a number-stability golden on `v0.4.0`'s tree, from numbers the gated walks already compute. Every later package asserts that golden at 10⁻⁸ relative on a mesh the golden holds, a figure the package argues from a measured rerun on each CI platform; a mesh the golden has not seen is held at the spread measured between recorded meshes, under a 10⁻³ ceiling, except in the reference environment CI pins, where an unseen mesh fails (VER-62). A miss is investigated: the change is reverted, or it is ruled a deliberate fix, and that fix amends the clause it changes and re-pins the golden in the same commit | A refactor or fix in a polish phase cannot change a result inside a benchmark's tolerance unnoticed. 10⁻⁸ is two orders inside VER-35's 10⁻⁶ nonlinear tolerance, and the predicted drift is round-off. **Amended in part, 6 October 2026** (§8.2.9 I4): an accuracy fix of WP41 re-pins the golden by a pre-ruled path, within a bound its plan argues | §8.1 (Phase 4's gate), in this commit |
| G11 | **The close package's last commit on `main` is tagged `v0.5.0` alone**, as E5 ruled for Phase 3. Each package's `v0.5.0-alpha.N`, and the release tag, are pushed by the session if its GitHub access allows it. Otherwise the session prints the commands and the author pushes them | The release commit is the one that merges the end-of-phase report (§2.7 NOTE), with no second tag on it | None |

#### 8.2.8 Phase 4 rulings on the modularity report, agreed 5 October 2026

Rulings by the author, taken through `/phase-plan amend 4` after WP35 merged as `v0.5.0-alpha.1`,
on the 17 findings of the modularity report (`docs/project/modularity.md`), and, as H10, on
`MOD-18`, which WP36's shipping review added, as H11, on WP37's plan, and, as H12, on WP37's
shipping review and the review register. Each `MOD-nn` row of
`docs/project/modularity-findings.md` names the ruling below that sets its status. Where a ruling
changes a clause, the clause is amended in the commit named in the last column.

| # | Decision | Consequence | Clause changed, and when |
|---|---|---|---|
| H1 | **Accepted, to be fixed in Phase 4, as the report recommends**: `MOD-01` (`key()` on the stage protocol), `MOD-02` (per-stage facts in the registry, not the walk), `MOD-05` (exit classification to `core`), `MOD-12` (a Tier-1 check that `PUBLIC` and its `TYPE_CHECKING` mirror agree), `MOD-13` for `io/case.py` only, `MOD-14` (no refusal names a shipped release, with a Tier-1 check) and `MOD-15` (`core`'s upward annotation import) | Each lands before the user-testing protocol (G2), keeps VER-61 and VER-62 green, and lists any break in `CHANGELOG.md`. The rest of `MOD-13` is deferred: `cli/__init__.py` to Phase 5 with the GUI's shell work, and `physics/models.py` and `default_ladder` to Phase 6 with `MOD-10` | None |
| H2 | **`MOD-11` is accepted, and the choice between adding `with_section` and `core.stages.register` to `PUBLIC` and ruling them internal waits for the user-testing sessions**, as the report recommends | The one accepted finding that does not land before the protocol, an exception to G2. A fix package after the sessions makes the change, which is additive either way, and the author's ruling of the relevant `UT-nn`, or of this finding, decides which | G2 gains a pointer to this ruling, in this commit |
| H3 | **`MOD-10` is deferred to Phase 6, and QR-13 is restated.** QR-13 is met by the single statement of the weak forms against NGSolve. §5.4.1's interface is the shape a second backend takes when N4 is planned. The subpackages that import `ngsolve` or `netgen` are confined to a recorded set by a Tier-1 guard, proposed as VER-65 and claimed by WP37. The set may shrink, and it grows only by the author's ruling | No wrapper is written that cannot be tested for the property it exists for. The backend's reach can no longer grow unnoticed. Appendix A's QR-13 row names the guard | QR-13, the §5.4.1 NOTE and Appendix A, in this commit. VER-65's row, in WP37 |
| H4 | **`MOD-09` is deferred to Phase 5**: the GUI's design document decides how outputs are offered, and the `OUTPUTS` and `STERIC_MODELS` enumerations follow it | Phase 5's plan inherits the finding | None |
| H5 | **`MOD-08` and `MOD-17` are post-1.0** | The five registry shapes and the eight repeated defaults stay. A registry added by H7 follows the nearest existing shape and adds none | None |
| H6 | **The coupling refactors (`MOD-03`, `MOD-04`) have a pre-registered target: the subpackage `top` import relation is acyclic, in the report's layer order, which is accepted as the project's order.** The routes are the report's: the twelve single-import cuts, moving the wall-distance solve out of `mesh/`, and splitting `io` into a base, imported downward only, and an assembler | When the target is met, VER-61 asserts it, so the cycle cannot return. On a miss, the residual cycle is reported with the cut it would need, and the author rules that edge accepted (recorded in `modularity-layering.yaml`) or deferred. No cut is forced | None. VER-61's row gains the assertion in the package that meets the target |
| H7 | **`MOD-06`, `MOD-07` and `MOD-16` are fixed in Phase 4**, departing from the report's deferral of the first two. The mesher, the linear solver and the stabilisation mode each become a registry, and `numerics.mesh.backend`, `numerics.linear.solver` and `numerics.stabilisation` become strings validated against it, as `physics.model` already is | Each is a widening of an existing key's value set, so the schema identifier does not move (the §5.3.1 NOTE). Gmsh stays off the default path (CON-10, ADR-002): registering the mesher imports nothing. The schema stops importing `solve.linear`, which removes one of `MOD-04`'s edges | None. The JSON schema of the three keys loses its enumeration, which `CHANGELOG.md` records |
| H8 | **The sequence**: WP36, the stage protocol and the walk (`MOD-01`, `MOD-02`, `MOD-12`); WP37, the cycle cuts outside `io`, the exit codes and the backend guard (`MOD-03`, `MOD-05`, `MOD-10`); WP38, the `io` split (`MOD-04`, `MOD-13`, `MOD-15`, and `io`'s cuts of `MOD-03`); WP39, the backend registries (`MOD-06`, `MOD-07`, `MOD-16`); WP40, the stale refusals (`MOD-14`); then WP41, the OKF bundle; WP42, its backfill; WP43, the user-testing protocol. The fix packages, the documentation increment and the close take their numbers at the second amendment | The interface later packages read goes first. The `io` split follows the cuts that do not touch it, and the registries follow the split that moves the schema they edit. Numbering the close once the fixes are counted keeps the numbers in order. **Amended, 6 October 2026** (§8.2.9 I1): WP41 to WP43 are the review register's fixes, the OKF bundle, backfill and protocol are WP44 to WP46, and the fix packages after the sessions start at WP47 | None. G5's order stands, refined |
| H9 | **Phase 4 is estimated at 3–5 weeks**: about two for WP36 to WP43, and the rest for the author's sessions, the rulings of each `UT-nn`, the fixes and the close | §8.1's "Set by the phase plan" is replaced. **Superseded, 6 October 2026** (§8.2.9 I5): 4–6 weeks | §8.1 (Phase 4's estimate) and §8.3, in this commit |
| H10 | **`MOD-18`, the Geometry tab's closed set of views, is deferred to Phase 5 with `MOD-09`** (added 6 October 2026, ruled by the author on WP36's shipping review, PR #79). The shell's design document decides how it shows a stage it has no view for, and `GEOMETRY_STAGES` is read from the registry when it is asked for, not at import | Phase 5's plan inherits the finding. A stage registered from outside the package is walked but has no Geometry-tab view until then | None |
| H11 | **WP37's cuts follow the accepted order, and the solver kernel becomes a subpackage of its own** (ruled 6 October 2026 on WP37's plan, the author asking for the most stable and long-term maintainable cut of `physics ↔ solve`). (a) The cuts H6's target needs are the `top` edges that point up the order, outside `io`. Of `MOD-03`'s single-import edges, those pointing down the order (`charge → mesh`, `geometry → density`, `physics → mesh`) stay. The upward edges the table did not list (`charge → materials`, `geometry → mesh`, and `mesh → physics` through `mesh/ingest.py`) are cut. (b) `physics ↔ solve` is cut by moving `solve/gates.py`, `solve/linear.py`, `solve/newton.py` and `physics/measures.py`, which import only `core`, into a new subpackage, `numerics/`. In the order it comes after `mesh` and before `charge` | Measured at `a346419`, H6's routes leave a `top` cycle of five subpackages (`charge`, `geometry`, `mesh`, `physics`, `solve`) even with `io` split (WP37 plan, Design §1). With (a), (b) and WP38's split, none is left. `numerics` joins VER-65's recorded set, which therefore starts at twelve. WP39's linear-solver registry (H7) lives in `numerics/` | §5.1, in this commit, and `CLAUDE.md`'s structure list with it. H6's order gains `numerics` from WP37's `modularity-layering.yaml`. VER-61's and VER-65's rows, in WP37 |
| H12 | **Open items of a work package's implementation or review are kept in a checked register until they are resolved** (ruled 6 October 2026 on WP37's shipping review). (a) `docs/project/review-findings.md` logs them as `REV-nn`, each with its section of `docs/project/review-items.md`; VER-63 checks it as it checks every findings log. `/wp-implement` and `/wp-ship` add a row for every item they leave open (a confirmed finding not fixed, a deferral, a question to the author) in the commit that leaves it, and the commit that resolves one sets it `fixed`. The log is a rolling register: it is not one of the two logs Phase 4's gate closes. (b) On WP37's review: `TOL_NM` moves to an import-free `geometry/tolerance.py` (REV-01); `cli/errors.py` is removed, `core/errors.py` being the table's one home (REV-02, amending WP37 D9); the split solution-field vocabulary is accepted for WP38 (REV-03); VER-61's ratchet is extended to imports inside a function by a `deferred_upward:` list (REV-04); and the shells' reads of the `nanopnp` facade (`cli → nanopnp`, `gui → nanopnp`) are accepted for WP39 under D11 (REV-05). (c) On the items earlier packages' PRs left open, swept from WP1 to WP36: the accuracy items REV-06 to REV-09, the conventions REV-11 to REV-13 and the correctness and cost items REV-14 to REV-19 are accepted for Phase 4's second amendment, which plans them into fix packages; REV-10 is fixed in WP37 (`prose-only.sh` treats `SPECIFICATION.md` and the report pages as read by tests); REV-20, `freeze_support`, is deferred to Phase 5 with the bundle; REV-21 and REV-22 are declined, `CLAUDE.md` exempting `scipy` from the import rule and one `%` over a whole numeric array from the f-string rule; the low items REV-23 onward stay `open`, one row each, until ruled | Nothing left open by a package lives only in a PR body or a chat. VER-61's D12 is a test, not a review convention. A bare import of `nanopnp.mesh.primitives` is back to its pre-WP37 cost. **Amended, 6 October 2026** (§8.2.9 I1 to I3): the accepted items land in WP41 to WP43, before the OKF bundle, and REV-23 onward are ruled | VER-61's row and the WP37 plan's Outcomes, in WP37's review commit. `/wp-implement` and `/wp-ship`, in the same commit |

#### 8.2.9 Phase 4 amended: the review register planned, agreed 6 October 2026

Rulings by the author, taken through `/phase-plan amend 4` after WP37 merged as
`v0.5.0-alpha.3`. They decide when the review items accepted by §8.2.8 H12 land, and how the 43
items H12 left `open` are ruled. Each `REV-nn` row of `docs/project/review-findings.md` names the
ruling below that sets its status. Where a ruling changes a clause, the clause is amended in the
commit named in the last column.

| # | Decision | Consequence | Clause changed, and when |
|---|---|---|---|
| I1 | **The review items H12 accepted land before the OKF bundle and the user-testing protocol.** They become three packages after WP40: WP41, the accuracy fixes; WP42, the verification checks; WP43, the small fixes. The OKF bundle, its backfill and the protocol are renumbered WP44, WP45 and WP46. The fix packages after the sessions are numbered from WP47 | Converged numbers, and the gates over them, settle before the claim ledger re-establishes them and before the testers judge the surface. This is G2's reason, applied to fixes. The OKF bundle is written against the test node ids that WP41 to WP43 leave, as G5 intends. For these items, I1 supersedes H12(c)'s "second amendment" and H8's numbering | H8 and H12 gain a pointer to this ruling, in this commit |
| I2 | **The accepted items are grouped by kind.** WP41, the accuracy fixes, run on Opus: REV-06, REV-07, REV-08, REV-09, REV-17 and REV-26. WP42, the verification checks: REV-11, a check that no gate comparison passes a NaN (proposed VER-70); REV-12, a check that every case leaf changes the assembled forms or is listed as provenance-only (proposed VER-71); REV-13; and REV-23, REV-29, REV-34, REV-42, REV-44 and REV-48. WP43, the small fixes: REV-14 to REV-16, REV-18 and REV-19, with REV-24, REV-25, REV-40, REV-43, REV-49 to REV-51, REV-55, REV-57 and REV-59 | The physics review of a fix does not share a diff with a new lint. VER-66 to VER-69 stay with WP39, WP40, the OKF bundle and the protocol, and each identifier is claimed when it is implemented. REV-42 refuses keys that `pnp` accepts today. That is a narrowing, so the case schema takes `nanopnp/case/v0.5` (G6; the §5.3.1 NOTE) | None. VER-70's and VER-71's rows are added in WP42 |
| I3 | **The open items REV-23 to REV-65 are ruled.** Into Phase 4: REV-27, REV-54 and REV-63 with WP38, which brings `nanopnp validate` up to the assembler's checks, the `PUBLIC` mirror's check up to modules, and the walk down to the requested stage's input closure; REV-36 to REV-38 with WP39, for the Gmsh session and its refusal; the items I2 names with WP42 and WP43; and REV-47 with the close, which reports the gate's durations and re-argues or retires WP33's targets. Deferred to Phase 5, with the shell, the bundle and `MOD-13`'s CLI split: REV-28, REV-30, REV-31, REV-32, REV-39, REV-41, REV-45, REV-52, REV-56, REV-62 and REV-65. Deferred to Phase 6: REV-46 (the ensemble, E1); REV-60 (UMFPACK's symbolic reuse, with the envelope's throughput); REV-61 (the HOLE cross-check, B5, with VAL-05); and REV-64 (NUM-34 on a generated mesh at a sweep's plan). Post-1.0: REV-35 and REV-58. Declined: REV-33, because the extra's floor is GridDataFormats 1.2, at which `mrc` is writable; and REV-53, because WP36 ruled that the drop rules are case logic | Every row of the register now has an owner or a terminal status. Phases 5 and 6 inherit their rows, as Phase 5 and Phase 6 inherited `MOD-09` and `MOD-10` | None |
| I4 | **An accuracy fix may move the number-stability golden by a pre-ruled path.** Before it changes the code, WP41's plan argues a bound for each VER-62 QoI that a fix of REV-07 or REV-08 can move, from the measured convergence of each block or the measured difference between the two quadratures. If the fix then moves a QoI by more than 10⁻⁸ relative, the package records the drift, shows that it lies within that bound, amends the clause the fix changes, and re-pins the golden, all in the same commit. A drift beyond the bound stops the package for the author's ruling | G10's "ruled a deliberate fix" is given in advance for a fix whose purpose is to change a number. The bound keeps it from passing anything larger. A refactor still has no such path | G10 gains a pointer to this ruling, in this commit |
| I5 | **Phase 4 is estimated at 4–6 weeks**, a week more than H9's estimate, for WP41 to WP43 | Supersedes H9 | §8.1 (Phase 4's estimate) and §8.3, in this commit. H9 gains a pointer |

### 8.3 Effort estimate

Estimate to the validated release (v0.7, Phase 6; §8.2.5 E2, §8.2.6 F1) without the desktop GUI: 6–9
months of part-time work. With the desktop GUI: 9–14 months. Both figures are for one person; the
calendar halves at full-time effort. Since §8.2.6 F1 the GUI phase precedes the validated release, so
the second figure is the one that applies, and Phase 4, which neither figure counts, adds 4–6 weeks
(§8.2.9 I5).

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
| **RSK-05** | Contour to mesh produces slivers at the constriction | Low–Med | Low | The delivered 185-vertex pore polygon ships as a fixture (§5.2.1); the reference mesh used no boundary layers, only isotropic grading to 0.05 nm at the pore wall; contour validity gate (FR-08); isotropic fallback; mesh quality gates abort the run (VER-10). **Retired 26 September 2026**: the stage-4 profile of the prepared 2WCD assembles and meshes at the default sizes with minimum SICN 0.7111 and gamma 0.6196, above the reference mesh's 0.6378, and the wall-size gate passes (VER-53, WP21) | Phase 2 |
| **RSK-06** | The author's contour script proves tightly coupled to its original context and is not portable | Med | Med | Read it in week 1 of Phase 2, before the rest of the phase is planned; fall back to the specified contour pipeline. **Retired 26 September 2026**: it was read (OPN-02). It is 20 lines, coupled to nothing beyond MDAnalysis, scikit-image and Shapely | Phase 2 |
| **RSK-07** | Axisymmetric reduction invalid for a given pore through large azimuthal variance | Med | Med | Residual azimuthal variance reported as a first-class output (FR-06) and documented as a validity criterion | Phase 2 |
| **RSK-08** | Charge non-conservation through smearing and 1/r projection | Med | Med | The closed-form azimuthal mean of each atom's 3D Gaussian, renormalised per atom (PHY-16, PHY-18; WP28, from exact annular volumes, which §8.2.4 D2 replaced); assertion on the deployed mesh and per-z-slice check against the source atoms (VER-01, VER-02). **Retired 1 October 2026** (WP28): on the protonated 2WCD both legs hold to 10⁻¹³ and the worst plane to 4 × 10⁻⁶ at the default sizes, and the deposited potential converges at the potential's own rate (VER-58) | Phase 3 |
| **RSK-09** | The reference model carries no mesh convergence study, so a Tier 3 discrepancy of a few per cent may originate in the reference | Med | Med–High | Quantify this project's discretisation error first (§7.3), then attribute the residual; the published results carry no error bar, so VAL-16 and VAL-17 state tolerances that include it (§8.2.4 D6); re-solving the reference at two refinement levels (VAL-04) is kept but not required; never adjust the solver to close such a gap | Tier 3 |
| **RSK-10** | The NGSolve pip wheel ships without MUMPS, and UMFPACK or SuperLU may not handle production-size coupled factorisations | Med | Med | Two solver configurations (§6.6); measured on day one of Phase 0 (§8.2 criterion 3); iterative fieldsplit through ngsPETSc in reserve | Phase 0 |
| **RSK-11** | NaN from 1/r terms at integration order 2, silent rather than a crash | Med | Med–High | Integration order ≥ 3 asserted on all 1/r forms; dedicated test on an axis-touching mesh (VER-07) | Tier 1 |
| **RSK-12** | Transcription errors in the correction coefficients, the per-ion `D` and `μ` sets being easy to conflate | Med | Med | Coefficient files reviewed against the model report in a second pass; each `f(c)` property-tested against published check values (VER-03) | Tier 1 |
| **RSK-13** | Desktop packaging defeated by a binary dependency | Med | Low–Med | NGSolve wheels chosen for this reason; packaging prototyped in Phase 0 (§8.2 criterion 4), not at the end. **Retired 24 September 2026** on the author's double-click (§8.2.1 NOTE); the gated `bundle` job re-detects it on every push | Phase 0 |
| **RSK-14** | COMSOL licence access lapses, removing the oracle | Med | Low | The gating comparison is against the published results (VAL-16, VAL-17), which need no licence (§8.2.4 D6); the field route stays available while access lasts | Continuous |
| **RSK-15** | Scope creep from the GUI drawing effort away from validation | Med | High | Each increment stays thin and follows the physics it exposes; no GUI is built for a capability Tiers 1 and 2 do not verify. **Amended 4 October 2026** (§8.2.6 F5): the GUI phase, Phase 5, precedes validation, so the shell holds no physics, no workflow depends on a Tier-3 number, and the residual risk that Phase 6 changes a number shown or forces rework of a screen is accepted by the author | Continuous |
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
| **OPN-07** | A golden's `case_hash` does not identify a **deposited** fixed charge. `validation/comsol.py` `case_identity` hashes `ResolvedCase.solve_provenance`, whose `fields.charge` says only whether `inputs.charge` was *supplied*. It replaces a supplied field with its contents' record (VAL-03), and on that rule two cases that differ only in their charge table are two cases. Since WP28 (FR-13, FR-14), stage 7 deposits a charge from `structure:` or `inputs.pqr`, and that charge reaches no key in the solve provenance. Its structure, `charge.ph`, `charge.forcefield`, `charge.titration` and `charge.smearing` are all invisible to the identity, and `fields.charge` reads `False`. **[tested]** on `examples/06-pdb-to-mesh/2wcd.case.yaml`, 1 October 2026: pH 7.5 (default), pH 5, pH 9 and `smearing.sharpness` 0.8 all give `case_hash` `8559ee13…`; only the model moves it. Such a case is therefore indistinguishable from the same physics on a supplied mesh with no fixed charge at all. A `χ` that stage 7 derives (§4.4 NOTE on the derived solid fraction; WP30) is invisible in the same way, and for the same reason it does not set `fields.eps_r`. Found by the WP28 review (PR #57, finding #7). The solve's own key is not affected, because the stage-7 artefact's hash already carries the protonation and the deposit (§5.3.2). The decision for the WP that resolves it: what represents a deposited charge in the identity. The candidates are the stage-7 inputs (the protonation key and the smearing parameters, not the mesh, which §7.4 deliberately leaves out), or the export lattice's grid digest, as a supplied field contributes it. Constraints: do not do it by setting `fields.charge` true in the provenance, which would move every producer case's solve key; leave every non-producer case's identity unchanged; and test it with a `test_val03_…` that fails on the example above **Representation decided by the author, 3 October 2026 (§8.2.5 E3): the stage-7 recipe**, with the lattice spacing and the element order left out as discretisation. **Closed, 4 October 2026 (WP34).** `case_identity` adds a key `deposited_charge` to a depositing case's record, holding the stage-1 key's parameters, the protonation key's parameters without `gates` and its input digests, and the kernel's parameters without `grid_spacing_nm`. It adds a key `derived_eps_r` to a deriving case's, holding `derived_parameters` and the stage-1 key's parameters, and a key `exclusion_shell` to a case with a non-zero `charge.exclusion_offset_nm`, holding the offset. The recipe is built through the stages' own key functions without running a stage, or, for a finished run, read from the stage-1 and protonation artefacts the run recorded (`ReopenedRun.upstream`), so `validate compare` and `export-golden` neither depend on the working directory nor follow a structure file edited after the run. **[tested]** `test_val03_case_identity_names_a_deposited_charge` on the example above: the four cases give four hashes, `grid_spacing_nm` and the element order give the default's, and two PQRs differ where a moved copy does not. `…_ignores_the_protonation_gate_tolerances`, `…_names_the_exclusion_shell`, `…_run_identity_is_read_from_the_recorded_artefacts` and `…_reopen_reads_the_runs_own_upstream_artefacts` cover the rest. Non-producer identities, every solve key and `fields.charge` are unchanged | Closed | Closed |
| **OPN-08** | The content and gate of the stable v1.0 release, now that the validation phase is released before it, as v0.7 and Phase 6 (§8.2.5 E2; §8.2.6 F1). IF-01's stability promise is v1.0's, and the case schema and public API may change until then (§8.2.6 F4) | Author | Nothing before v1.0. The §2.7 row for v1.0 and any requirement retagged to it |

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

NOTE (§8.2.6 F6): a Phase 4 package restructures this knowledge base as an
Open Knowledge Format v0.2 bundle, one concept per `##` section, every `[tested]` claim naming its
test. Until it merges, the table above is the layout, and every citation of it stays valid.

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
| IF-01 | VER-25, VER-32, VER-45 (the public surface, the modules its mirror imports from, and its import cost) |
| IF-02 | VER-32, VER-38, VER-45 (the generated command-line and exit-code references), VER-46 (every documented command executed) |
| IF-03 | VER-09, VER-36 (dotted-path substitution against the schema), VER-47 (schema v2 and the v1 upgrade), VER-57 (`inputs.pqr` read, registered and refused; the protonation keys' refusals); the registry and inf-sup refusals made at load, through `nanopnp validate case` and the shell's commit with a run's text (`tests/tier1/test_case_schema.py`, `test_cli.py`, `test_gui_viewmodels.py`) |
| IF-04 | VER-48 (PDB, mmCIF and each trajectory format read; PDB and mmCIF of one entry agree), VER-32 (the aligned ensemble exported as a PDB and a DCD) |
| IF-05 | VER-29, VER-49 (the density map in `.npz`, OpenDX and CCP4, in ångströms at the file boundary), VER-50 (the reduced map exported as radial grids), VER-32 and VER-46 (the map exported from the command line and overlaid on its structure), VAL-15 |
| IF-06 | VER-27 |
| IF-07 | VER-33 |
| IF-08 | VER-24, VER-35 |
| IF-09 | VER-43, VER-44, VER-55 (the geometry pipeline built, inspected and hand-edited from the shell), VER-60 (the charge pipeline built and inspected from the shell, every number read from its stage's artefact) |
| FR-01 | VER-48 (frame window, superposition on the earliest frame's C-alpha, Kabsch against MDAnalysis) |
| FR-02 | VER-48 (the permutation axis against a known axis, and against principal axes) |
| FR-03 | VER-48 (missing, surplus and truncated chains, residue names and the point group refused) |
| FR-04 | VER-49 (the union density, its truncation bound, the frame average and the radius set) |
| FR-05 | VER-01 (shared annular-volume integration), VER-50 (exact annular weights and the harmonic Cₙ average) |
| FR-06 | VER-50 (the Cₙ and raw variance against closed forms), VAL-05 (the largest Cₙ and non-Cₙ variance and where, recorded on both legs: `tests/tier2/test_val05_2wcd.py`, `tests/tier3/test_val05_ensemble.py`) |
| FR-07 | VER-51 (marching squares against exact and closed-form level sets, the morphology, Taubin and the conditioning), VAL-05 (the stage-4 polygon against the reference: `tests/tier1/test_val05_geometry.py`, the harness; `tests/tier2/test_val05_2wcd.py`; `tests/tier3/test_val05_ensemble.py`) |
| FR-08 | VER-51 (each §5.2.1 gate criterion fires on constructed input; the radius band against the probe profile) |
| FR-09 | VER-28, VER-52 (the membrane junction derived on any profile), VER-59 (the ion-exclusion shell assembled from the profile's offset, the membrane unchanged), VAL-05 (stage 5's model-frame polygon is the compared one: `tests/tier2/test_val05_2wcd.py`, `tests/tier3/test_val05_ensemble.py`) |
| FR-10 | VER-10, VER-53 (the size fields, the wall-size gate and the generated mesh's gates), VER-59 (the shell meshed at the wall size, through the same gates, on the parallelogram and on 2WCD), VER-54 (the same region meshed by the optional Gmsh backend through the same gates, and solved on both backends' meshes), VAL-05 (the generated mesh against §5.2.2's figures, and one frozen case's conductance on it against the fixture's, recorded: `tests/tier2/test_val05_2wcd.py`, `tests/tier3/test_val05_ensemble.py`) |
| FR-11 | None yet |
| FR-12 | VER-57 (the protonation stage: the force field's own charges, PROPKA's states, unapplied states recorded, the PQR artefact and `inputs.pqr`), VAL-06 (the protonated 2WCD's potential against APBS, and the recorded leg from its PQR: `tests/tier2/test_val06_2wcd.py`; the archived PQRs: `tests/tier3/test_val06_archive.py`), VER-46 (example 07: `Q_net` against the exported PQR, and the PQR supplied back) |
| FR-13 | VER-01, VER-02, VER-58, VAL-06 (the export lattice hat-weighted onto APBS's grid, against the deposit's potential: `tests/tier1/test_apbs_maps.py`, `tests/tier2/test_val06_ring.py`, `tests/tier2/test_val06_2wcd.py`), VER-46 (example 07: the same deposit from the exported PQR) |
| FR-14 | VER-01, VER-02, VER-29 (the deployed-mesh half), VER-58 (the deposit onto the deployed mesh), VAL-15, VER-46 (example 07: the conservation report read from the manifest, and the re-supplied lattice refused) |
| FR-15 | VER-30, VER-31, VER-59 (the shell and the derived `chi` from the one stage-4 profile, both off by default: `tests/tier1/test_exclusion_shell.py`, `tests/tier1/test_derived_dielectric.py`, `tests/tier2/test_exclusion_keys.py`, `tests/tier2/test_exclusion_stern.py`, `tests/tier2/test_exclusion_2wcd.py`, `tests/tier2/test_stern_layer.py`), VAL-06 (the assembled permittivity as APBS's staggered harmonic maps: `tests/tier1/test_apbs_maps.py`, `tests/tier2/test_val06_ring.py`, `tests/tier2/test_val06_2wcd.py`), VER-46 (example 07: both switches listed as deviations, with the `exclusion` material meshed) |
| FR-16 | VER-03 |
| FR-17 | VER-08, VER-16, VER-18 |
| FR-18 | VER-13, VAL-10 |
| FR-19 | VER-12, VER-13 |
| FR-20 | VER-56 (a model defined as one class in the test tree, registered at run time, runs from a case file through stages 10 to 12; no layer outside `physics/` names a model) |
| FR-21 | VER-20, VER-22 |
| FR-22 | VER-19, VER-21, VER-22 |
| FR-23 | VER-11, VER-38 (the two-point ratio), VAL-16 (the published currents, transport numbers, rectification and flow rate) |
| FR-24 | VER-36, VER-37, VER-38 |
| FR-25 | VER-24, VER-26 (manifest emitted per §7.6) |
| FR-26 | VER-09, VER-26, VER-47 (a v1 document and its v2 rewrite are one run) |
| FR-27 | VER-23, VER-25, VER-26, VER-32, VER-34, VER-51 (the stage-4 payload is an `inputs.profile` document), VER-52, VER-53 (stages 5 and 6 keyed and walked to stage 12), VER-55 (each stage's artefact reported as it is stored, by a hook that keys nothing), VER-57 (the protonation stage cached per frame, its export read back exactly through `inputs.pqr`), VER-60 (both halves of stage 7 reported as each is stored, and a cancelled charge build writing no artefact), VER-64 (every stage keyed before it runs, the facts the walk reads and the upstream artefacts it reads declared by the stage, and a walk running its target's input closure) |
| FR-28 | None yet |
| FR-29 | None yet |
| QR-01 | VER-12 to VER-22, in particular VER-17 and VER-18 |
| QR-02 | VAL-16, VAL-17 (gating v0.7); VAL-01, VAL-02 (kept, not required) |
| QR-03 | VER-01, VER-29, VER-58, VAL-15 |
| QR-04 | VER-11, VER-40 (the route disagreement as a resolution gate), VER-42 (the identity under a stabilisation mode) |
| QR-05 | VAL-07, VAL-08, VAL-09 |
| QR-06 | VER-39 (measured, recorded, not gated) |
| QR-07 | None yet (§8.2 criterion 3) |
| QR-08 | VER-26 for manifest sufficiency; VER-34, VER-35 for QoI reproduction; VER-53 (a regenerated mesh's content hash against the recorded one) |
| QR-09 | VER-47 (the declared interpreter range agrees with §2.5); the wheel-only install itself is exercised by the §7.6 matrix, not asserted by a test |
| QR-10 | None yet; Phase 5's gate, observed by a person (§8.2.6 F5) |
| QR-11 | VER-43, VER-44, VER-55, VER-60 |
| QR-12 | VER-10, VER-32, VER-40, VER-41, VER-48 (the stage-1 input and symmetry gates), VER-49 (the radius refusal and the density bounds gate), VER-51 (each contour gate criterion names its value, threshold and (r, z)), VER-52 (each stage-5 criterion likewise), VER-53 (the wall-size gate names the segment), VER-54 (the region graph's refusals name the edge's midpoint), VER-57 (each protonation gate names its frame), VER-59 (the shell's refusals name the z interval or the edge, and the derived `chi`'s gates name the material) |
| QR-13 | VER-65 (the subpackages reaching NGSolve or Netgen equal a recorded set, in both directions). The §5.4.1 interface is absent (`MOD-10`), deferred to Phase 6 by §8.2.8 H3, which restated QR-13 as the single statement of the weak forms plus this guard |
| QR-14 | VER-03 (a correction is a data file), VER-56 (a physics model is one class), VER-66 (a backend registry is one registration) |
| QR-15 | VER-45, VER-46 — the documentation part only, delivered incrementally by the §8.1 documentation track; the JOSS submission and the DOI-archived release remain unverified until v0.7 |
| CON-01 | None yet |
| CON-02 | VER-20, VER-22 |
| CON-03 | None yet |
| CON-04 | VER-50 (axisymmetric inputs read no variance, and a Cₙ turn leaves the reduction unchanged) |
| CON-05 | VAL-07 (residual discrepancy below 0.05 M) |
| CON-06 | None yet |
| CON-07 | None yet |
| CON-08 | §6.6 measurement table (§8.2 criterion 3, discharged) |
| CON-09 | VER-43 (no PyQt module is reachable from the shell's import paths); VER-44 (the shipped renderer is byte-identical to the npm tarball kept as its source, whose SHA-512 is npm's published integrity); VER-55 (nor from the geometry view-models'); VER-60 (nor from the charge view-models', which import neither PDB2PQR nor PROPKA) |
| CON-10 | VER-27 (the default ingestion path imports no Gmsh), VER-53 (nor does generating a mesh through stages 5 and 6), VER-54 (nor resolving or keying a case that names the Gmsh backend; without the extra that backend is refused naming it), VER-55 (nor do the geometry view-models; the bundle carries it as the optional backend, §8.2.2 B8) |
| CON-11 | §6.6 measurement table — measured; the conflict it exposed is resolved by CON-11 and ADR-003. VER-43 asserts that the bundle's licence notice states the resulting GPL-2+ obligation, and the probe refuses to start without it; VER-55 adds the geometry payloads, Gmsh (GPL-2+) and Shapely's GEOS (LGPL-2.1) among them, each exercised by the probe; VER-60 adds PDB2PQR (BSD-3) and PROPKA (LGPL-2.1, collected as source files), exercised by protonating a peptide at two pH values |
| CON-12 | VER-54 (the lock names none of Triangle, MeshPy, TetGen, pygmsh or pygalmesh, and the `gmsh` API is called directly) |
| CON-13 | VER-43 in part (the Windows bundle builds and launches headlessly on every push; widget construction is asserted on `windows-latest` and `macos-latest`). Linux *desktop* Qt is deliberately not asserted: the push gate installs no system packages, and PySide6 does not import on the runner image |
| CON-14 | None yet |

Coverage: 57 of the 67 requirements in §3 have a specified activity; 10 are recorded as "none yet",
predominantly interface, portability, licensing and documentation requirements whose demonstration
is by inspection rather than by test. QR-07 is counted as "none yet", its entry
naming §8.2 criterion 3 as the measurement it is still waiting for rather than as one it has. VER-61, VER-62 and VER-63 verify Phase 4's gate (§8.1; §8.2.7 G1, G4 and
G10), and VER-72 the source conventions of `CLAUDE.md` and the plans' records, rather than a
requirement of §3, so they leave the count unchanged.

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

---
type: Specification
title: "3. Requirements"
description: "Sets out the external interfaces, functional requirements, quality of service, design constraints and exclusions the product must meet."
---

## 3. Requirements

The subject of each requirement is the product unless stated otherwise.

### 3.1 External interfaces

| ID | Requirement |
|---|---|
| **IF-01** | SHALL expose a Python API in which every pipeline stage is a separately importable, invocable object, stable from v1.0 onward (§8.2.6 F4). |
| **IF-02** | SHALL provide a CLI over the same stage objects, able to execute a case file, run one stage, and dispatch a sweep. |
| **IF-03** | SHALL accept one declarative YAML case file, identified by `schema: nanopnp/case/v0.5`, as the complete run specification, rejecting unknown keys with a diagnostic naming the key (§5.3.1). |
| **IF-04** | SHALL read structures in PDB and mmCIF, and trajectories in DCD, XTC, TRR and NetCDF. |
| **IF-05** | SHALL read and write volumetric density and charge grids in OpenDX and CCP4. |
| **IF-06** | SHALL write meshes in Gmsh MSH 4.1 as the archival format, and SHOULD read any format meshio supports. |
| **IF-07** | SHALL write solution fields in XDMF with HDF5 heavy data. |
| **IF-08** | SHALL accompany every result artefact with a machine-readable provenance manifest (FR-25). |
| **IF-09** | SHALL provide a desktop graphical interface covering case editing, run control, convergence monitoring and field visualisation, as a thin shell over the IF-01 stage objects. |

NOTE (the browser shell, v0.6). When the package that removes the Qt shell lands, IF-09 reads:
"SHALL provide a graphical workbench, served by a local server and opened in the browser by
`nanopnp gui`, covering the four suites of the workbench design (Molecular, Continuum, Study and
Analysis), the run queue and the project folder, as a thin shell over the IF-01 stage objects that
speaks to its server through a network API." Until then the text above gates the Qt shell (§8.2.17
S12, S17; `docs/design/workbench.md`, WB-01, WB-29).

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
places the origin on the lattice of the spacing. A file whose spacing, read in ångströms, falls
outside the stage-2 range of [0.025, 0.05] nm SHALL be refused, saying that a map written in nm
reads ten times small: the two ranges are disjoint, so no unit marker is needed and maps exported
before the marker question arose still read (REV-40; WP46). The native `.npz` stays in nm, as does everything
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

NOTE (IF-02, reading; §8.2.21 W2): a command's text output is a reading for a person, and `--json`
prints the whole record a caller parses, unchanged by that reading. `nanopnp inspect` reads a record
by its schema: a run directory or its manifest as its model, its stages, each rung with its Newton
iterations and time, its quantities and its deviations; a sweep dataset as a table of its points,
with each rectification ratio beside the values that make its pair; a stored artefact as its schema,
key and summary. A record of another schema is listed key by key. Two run directories given together
are compared: the case fields that differ, the deviations of each run, and each quantity of either
side by side with their relative difference. A comparison exits `0`, being a reading and not a test.

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
change is a decision made in review (§8.2.13 N3), and each break is listed in
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
| **FR-28** | SHALL export fields and the originating case file from a completed run; its figures are FR-44's (§8.2.21 W3). | v0.7 |
| **FR-29** | MAY perform goal-oriented (dual-weighted-residual) mesh adaptivity targeting the ionic current. | post-1.0 |
| **FR-30** | SHALL draw a figure of the artefact of every stage that declares one, of the solve's Newton and continuation history, and of a sweep's collected results, from the stored artefacts alone, in SI units and the model frame, through an optional extra the default import path does not load; SHALL draw a solved potential in mV on a colour scale centred at 0 mV whose reach the caller may set, a concentration relative to the bulk the solve imposed on that species, on a logarithmic scale, the signed axial velocity with streamlines in the lumen, the lumen being read from the pore wall of the mesh, and a mesh as its element edges and its whole domain beside its lumen with λ_D/5 marked, and SHALL draw an axial or radial cutline of any solved field from the stored nodes; and SHALL let a notebook display any artefact and run result, as its stage's figure where one is declared (§8.2.14 P2 to P6; §8.2.20 V4, V6, V12, V16). | v0.5 |
| **FR-31** | SHALL provide the workbench as four suites in a project, Molecular, Continuum, Study and Analysis, each tool's settings docked beside its live view, with the project rail, the changed-from-default count and the run queue always on screen (§8.2.17 S2; WB-01 to WB-03, WB-05, WB-07, WB-29). | v0.6 |
| **FR-32** | SHALL keep a workbench project as a plain folder of named molecular and continuum models, studies pairing one of each, comparisons, runs each with its resolved case file and manifest, the store, and a project file holding no physics; and SHALL export it as a portable copy of readable files (§8.2.17 S11; WB-04, WB-11, WB-13). | v0.6 |
| **FR-33** | SHALL link, both ways and until unlinked, a residue and the charge map, a geometry and its parameters, a field and its probes and cuts, and a run and its result (§8.2.17 S6; WB-06). | v0.6 |
| **FR-34** | SHALL mark every value set away from its default and every study override where it is shown, count them on screen, and list them grouped by model with each default and a reset; and SHALL keep every setting of a tool on its pane, guarded against being changed by accident (FR-25; WB-03, WB-28, WB-32; §8.2.18 T8). | v0.6 |
| **FR-35** | SHALL refuse a value at its field, naming the rule, the value entered, the case path and a remedy, and SHALL list each refusal of a later build in a problems list that leads to its field (QR-12; WB-12, WB-25). | v0.6 |
| **FR-36** | SHALL offer QR-10's guided run as a route through the suites from a clean project, a layer that lifts the next control, fills defaults, marks a changed value, refuses a missing or out-of-range value at its step, and may be left at any step (WB-08). | v0.6 |
| **FR-37** | SHALL prepare a structure: estimate its pore axis, choose its chains, and let the user set the flip and the membrane's place, with no rule specific to one pore, as a library capability (v0.5) before the workbench surfaces it (v0.6) (§8.2.17 S4 as amended; WB-14; §8.2.20 V1). | v0.5, v0.6 |
| **FR-38** | SHALL set a titratable residue's protonation state, or a residue's charge or radius, at stage 7's PQR step on every chain, and save the result as a variant of its molecular model, shown as its difference from its parent (§8.2.17 S4; WB-04; §8.2.19 U6). | v0.6 |
| **FR-39** | SHALL let a study override any of its continuum model's physics defaults, sweep over its values and over the library's models, and reuse each built molecular and continuum model in every study that names it without rebuilding it, rebuilding only the stages a changed value or a molecular variant moves (WB-11, WB-16, WB-29; §8.2.19 U2). | v0.6 |
| **FR-40** | SHALL compose a physics model from registered building blocks, in `physics/` with its own Tier 1 and Tier 2 tests, its architecture leaving room for equations the user writes (§8.2.17 S3). | composer phase |
| **FR-41** | SHALL replace a residue's side chain in 3D and rebuild the density, the contour, the mesh and the charge from it, library first with a vetted dependency (§8.2.17 S4). | structural-mutator phase |
| **FR-42** | SHALL draw the (r, z) domain by hand with lines, arcs, booleans and named boundaries, meshed by the library, the solve staying 2D axisymmetric (§8.2.17 S5; N4). | sketcher phase |
| **FR-43** | MAY assign each titratable group, as a switch away from the validated default of PHY-16 step 3, its charge averaged over its protonation states at the pH, from its pKa; its physics is written into §4 with its library package (§8.2.18 T6). | a later phase |
| **FR-44** | SHALL draw from the command line, to a PNG, SVG or PDF file, the declared figure of a stage of a case, of a completed run and of a sweep's collected dataset, through FR-30's figures and their optional extra, and SHALL refuse before any stage runs a suffix it does not write or a stage that declares no figure (§8.2.21 W3). | v0.5 |

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
| **QR-16** | The workbench SHALL meet WCAG 2.2 AA in both its themes, the contrast of controls, focus rings and colour bars included, and SHALL be operable by keyboard alone, every action on a canvas having a keyboard path (WB-19, WB-24). | Usability |

NOTE (QR-12, the remedy; §8.2.21 W5): a diagnostic that names a remedy SHALL name a setting the
run reads. The wall-distance gate of NUM-34 names `numerics.mesh.wall_h_nm` for a mesh stage 6
generates, and for a supplied mesh the file it reads and its generator (`nanopnp mesh cylinder
--wall-h-nm`), `numerics.mesh` being refused beside `inputs.mesh`. Where a document states one quantity
twice, a refusal of their disagreement SHALL name both keys. An analytic form that carries a charge
(`gaussian_ring`'s `charge_e`) need not equal `q_net_e`, the field's integral over `r ≥ 0`, planar for
an areal density and `2πr`-weighted for a volume density: an areal ring on the axis integrates to half
its charge. A charge and a `q_net_e` of opposite sign, or one of them zero
and the other not, are refused when the document is read, before its grid is built; a disagreement in
size is the producer leg's of PHY-19, whose refusal names `q_net_e` and the form's charge parameter.

NOTE (the browser shell, v0.6). When the package that removes the Qt shell lands, QR-10 reads: "A
nanopore experimentalist without Python knowledge SHALL be able to install the workbench, load a
structure, accept defaults and obtain a conductance prediction and a field visualisation in it
unaided." Until then the text above gates the Qt shell (§8.2.17 S12, S13, S17).

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
| **CON-09** | The core library SHALL be licensed BSD-3-Clause. LGPL dependencies are acceptable under dynamic linking (NGSolve/Netgen LGPL-2.1, MDAnalysis LGPLv3, PROPKA LGPL-2.1, PySide6 LGPL-3). MPL-2.0 dependencies are acceptable used unmodified as separate packages (gemmi, the mmCIF reader of the `structure` extra). The field viewer's renderer, npm `webgui` (LGPL-2.1-or-later, bundling three.js under MIT and dat.gui under Apache-2.0), MAY be redistributed with the package, **unmodified and as a separate file** loaded at run time, beside its licence texts and a notice naming its corresponding source, which the repository and the source distribution carry verbatim; nothing in the library SHALL be linked against it. PyQt SHALL NOT be used, being GPL-3 or commercial only. The PySide6 clause lapses when Phase 5 removes the Qt shell; the renderer clause binds the browser shell (§8.2.12 M3). |
| **CON-10** | Gmsh (GPLv2+) SHALL be an optional backend only; the default path SHALL NOT link Gmsh, and the core library SHALL remain functional without it. |
| **CON-11** | SuiteSparse UMFPACK is GPL-2+, so a bundle defaulting to UMFPACK carries GPL obligations even though the library does not. The core library SHALL remain BSD-3 and SHALL NOT itself depend on UMFPACK; the redistributable bundle SHALL default to UMFPACK, SHALL be distributed under the resulting GPL-2+ obligations and SHALL state them in its licence notice, scipy SuperLU remaining selectable at runtime. The default follows the §6.6 measurement: SuperLU did not factorise the reference-sized problem at all, so a SuperLU-default bundle could not run the published case. |
| **CON-12** | Meshing components with distribution-restricting licences SHALL NOT be depended upon, specifically Triangle (and MeshPy, which wraps it) and TetGen 1.5 (AGPLv3). |
| **CON-13** | SHALL support Windows, macOS and Linux on desktop hardware, and Linux for headless and HPC execution. |
| **CON-14** | The repository SHALL carry a `CITATION.cff` pointing at the Nanoscale paper and the software DOI. |

NOTE (the browser shell, v0.6). When the package that removes the Qt shell lands, CON-09 reads: "The
core library SHALL be licensed BSD-3-Clause. LGPL dependencies are acceptable under dynamic linking
(NGSolve/Netgen LGPL-2.1, MDAnalysis LGPLv3, PROPKA LGPL-2.1). MPL-2.0 dependencies are acceptable
used unmodified as separate packages (gemmi, the mmCIF reader of the `structure` extra). The field
viewer's renderer, npm `webgui` (LGPL-2.1-or-later, bundling three.js under MIT and dat.gui under
Apache-2.0), MAY be redistributed with the package, **unmodified and as a separate file** loaded at
run time, beside its licence texts and a notice naming its corresponding source, which the repository
and the source distribution carry verbatim; nothing in the library SHALL be linked against it. A
dependency of the workbench's front end SHALL be under a permissive licence, or under the LGPL or the
MPL-2.0 used unmodified as a separate file as the renderer is. PyQt SHALL NOT be used, being GPL-3 or
commercial only." Until then the text above gates the Qt shell (§8.2.12 M3; §8.2.17 S17).

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

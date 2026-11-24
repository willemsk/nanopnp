# Ground-up review: the walk

One row for each requirement, constraint, method, decision and process rule the review opens: its best alternative,
what the three blind designs chose, a verdict and a reason. An appendix of
[the ground-up review](../ground-up-review.md).

## How to read a row

- **Today** says in at most 15 words what the program or its plan holds.
- **Best alternative** is the strongest other choice found, in a blind design, in
  [today's alternatives](technologies.md) or by the main session. "None better found" means that nobody proposed one.
- **A, B and C** are the three blind designers. `=` means that the designer kept the row after the unblinding, or that
  its design chose the same; `≠` that it changed or dropped the row, or chose otherwise; `–` that it did not say. For
  the requirements, the constraints, the exclusions and the architecture decisions the marks are the designers' own
  tables, in [design A](design-a.md), [design B](design-b.md) and [design C](design-c.md). The designers did not
  judge the other rows one by one, so those marks are read from each design's text.
- **Verdict** is the main session's: keep, change now (in Phase 6), change later (in the phase named), drop or add.
  A phase's number is today's, from §2.7.
- **Reason** names the evidence. A number without a source here is from [the evidence](evidence.md). The reason behind
  a ruling or a knowledge note counts as evidence and not as authority (`wp6.04`'s D4).

A verdict is a proposal. Nothing changes until the author has ruled on the report. The walk holds 259 rows: 207 are
kept, 24 change now, 16 change later, one is dropped, 9 are added and 2 lacks are not added. A keep means that a
start-over would choose the same, unless its reason says otherwise.

## The requirements, the releases and the rulings

The 141 rows of this part hold 109 verdicts of keep, 13 of change now, 9 of change later, one of drop, 7 of add and 2
lacks that are not added.

Seven rows go against all three designers. FR-39, the two structure readers of §2.6, NiceGUI, and the places of the
workbench's rebuild and of validation in §2.7 are kept although no designer chose them; QR-09's floor changes
although each designer kept it. Each row says why.

### External interfaces, IF-01 to IF-09

| ID | Today, in 15 words | Best alternative | A | B | C | Verdict | Reason |
|---|---|---|---|---|---|---|---|
| IF-01 | Python interface of `Case` and `Session`; each stage runs alone; stable from v1.0. | One service layer that every interface calls | = | = | = | keep | Each design puts one layer under every interface, and `Session` is it. A start-over would choose it. |
| IF-02 | Command line over the same interface, with an exit-code contract for job arrays. | None better found | = | = | = | keep | All three keep it and name the exit codes as what makes a job array reliable. |
| IF-03 | One YAML case file, schema `nanopnp/case/v0.6`; unknown keys and earlier schemas refused. | A versioned schema with migration functions, so an old case and record open | ≠ | ≠ | ≠ | change later: version 1's gate | B and C ask for migrations. Until v1.0 the author is the one user, so a migration per schema change buys little; the stability promise of IF-01 names neither the case file nor the run record, and should. |
| IF-04 | Reads PDB and mmCIF structures, and DCD, XTC, TRR and NetCDF trajectories. | None better found | = | = | = | keep | All three keep it. |
| IF-05 | Reads and writes density and charge grids in OpenDX and CCP4. | An optional export (C) | = | = | ≠ | keep | The reader is installed already, and A names these grids as what a molecular simulation would take back. |
| IF-06 | Writes meshes as Gmsh MSH 4.1, the archive format; reads what meshio reads. | The mesh inside the run's HDF5 file, MSH for exchange only (A, B) | ≠ | ≠ | = | keep | No cost of MSH was measured. B's reason holds only for adaptive curved meshes, which the program does not have. meshio has had no release for 22 months, which the SHOULD rests on. |
| IF-07 | Writes fields as XDMF with HDF5, at the exact second-order node set. | HDF5 in the VTKHDF layout (A); any container ParaView reads (C) | ≠ | = | ≠ | keep | The survey favours HDF5 with a sidecar; VTKHDF's specification calls itself incomplete. Whether ParaView shows a second-order field from either without resampling needs a trial. |
| IF-08 | A machine-readable provenance manifest with every result. | None better found | = | = | = | keep | All three designs write the same record. |
| IF-09 | Browser workbench on a local server: six named suites, a thin shell over the interface. | The requirement keeps server, browser, thin shell and network interface; the layout is the design's | ≠ | ≠ | ≠ | change later: Phase 7's round | A wants three workspaces, B one route first, C a list of tasks: three layouts and one shared boundary. With the layout in the design document alone, a design round changes one record. |

### Functional requirements, FR-01 to FR-44

| ID | Today, in 15 words | Best alternative | A | B | C | Verdict | Reason |
|---|---|---|---|---|---|---|---|
| FR-01 | Ingests a structure and an optional trajectory; superposes the frames on Cα atoms. | None better found | = | = | = | keep | All three keep it. |
| FR-02 | Finds the symmetry axis by chain-permutation superposition and places it on z. | None better found | = | = | = | keep | All three keep it; A notes that the same axis defines a 3D wedge. |
| FR-03 | Checks the chains against the case's point group; the text names three pores. | The clause says what the program does: the case declares the oligomer | ≠ | ≠ | ≠ | change now: text | All three read the clause as a built-in table of pores. The program has none: `symmetry.point_group` takes any `C<n>`. One line of §3 misleads its reader. |
| FR-04 | Density map from per-atom Gaussians on a 3D grid of 0.25 to 0.5 Å. | The closed-form azimuthal mean, with no 3D grid (B) | = | ≠ | ≠ | keep | The 3D map is what FR-06's variance, the molecular viewer and a later 3D mesh read (A's level set). B's closed form would remove it and re-pin every structure's numbers. |
| FR-05 | Reduces the map to (r, z): rotated copies averaged, exact annular binning. | The closed form of FR-04's row (B) | = | ≠ | = | keep | It follows FR-04. |
| FR-06 | Reports the residual azimuthal variance of every reduced geometry. | None better found | = | = | = | keep | All three call it the honest measure of what the reduction costs. |
| FR-07 | Extracts the pore surface as a contour at isolevel 0.25, conditioned to a polyline. | A smooth spline with curved elements (B) | = | ≠ | = | keep | B argues that each corner of a polygon is a field singularity. The refinement ladder of FR-29's row measures the observed order on a structure's polygon and settles it; no result supports a change yet. |
| FR-08 | Gates the contour: validity, simplicity, spacing, feature size, one loop, radius profile. | None better found | = | = | = | keep | All three keep the gates. |
| FR-09 | Assembles the (r, z) region from contour, membrane and reservoirs, with conformal interfaces. | Regions from a level set in any dimension (A) | ≠ | = | = | keep | A's level set earns its cost only in 3D, which is after version 1. |
| FR-10 | Graded triangular mesh that resolves the wall's Debye length; aborts on a quality gate. | Size from the correction's own length (A); refinement towards the quantity (B) | ≠ | ≠ | = | keep | NUM-30 already caps the wall size at 0.05 nm for the wall function's decay length, which is A's rule. The refinement ladder of FR-29's row tests the rule by measurement. |
| FR-11 | May build structured boundary layers at the wall; after version 1. | Required for 3D (A); dropped under adaptivity (B) | ≠ | ≠ | = | keep | A MAY costs nothing. Whether Netgen meshes a wall layer at the Debye length needs a trial. |
| FR-12 | Derives protonation and partial charges at a pH and force field; records the net charge. | None better found | = | = | = | keep | All three keep it; the pack named the route, so the choice is prompted. |
| FR-13 | Assembles the fixed charge from 3D Gaussians, averaged exactly, conserved on the mesh. | None; the physics of §4 | = | = | = | keep | Given physics, outside the review's reach (BA12). |
| FR-14 | Asserts charge conservation on the mesh and per axial slice. | None better found | = | = | = | keep | Each design carries the same evidence in every run. |
| FR-15 | Builds the dielectric field and the exclusion surface from the one density field. | None better found | = | = | = | keep | All three keep it. |
| FR-16 | Each correction is a named component; its coefficients are versioned data files. | None better found | = | = | = | keep | The first level of extension in every design. Its registration from another package is QR-14's row. |
| FR-17 | Solves the full model over 0.005 to 5 M and ±200 mV; no negative concentration. | Detect and recover, or solve for log-concentrations (C) | = | = | ≠ | keep | Both timed cases converge on the ladder with no stabilisation. The unknowns are a method of §6; NUM-01's row holds that question. |
| FR-18 | Provides the models `epnp-ns`, `pnp-ns`, `pnp` and `poisson` by name. | None better found | = | = | = | keep | All three build the simpler models as the full one with neutral parts. |
| FR-19 | Provides the equilibrium models `pb` and `pb-linear`. | None better found | = | = | = | keep | All three keep them. |
| FR-20 | A new physics model is one class behind a documented interface. | A model is a composition of registered terms; a variant is a difference from its parent | ≠ | = | ≠ | change now: with FR-40 | `physics/models.py` holds 2,076 lines and one class for the coupled model; its four switches are a closed tuple, and `physics/terms.py` lists each model's terms a second time, in LaTeX. FR-20 merges into FR-40. |
| FR-21 | A rigid analyte of revolution on the axis; planned for v0.12. | None better found | = | = | = | keep | All three designs hold the same analyte. |
| FR-22 | Electric and hydrodynamic force and their potential over axial positions; v0.12. | The same series also reports the residual current (B) | = | ≠ | = | change later: Phase 11 | The residual current is what an experiment records. Each analyte position is solved already and FR-23 reads the current from any solve, so it costs no new physics. |
| FR-23 | Current, transport numbers, rectification and flow rate by two checked routes. | None better found | = | = | = | keep | Each design names two routes and never a cross-section integral of the flux, unprompted. |
| FR-24 | Sweeps any case field as independent jobs, warm-started from a converged neighbour. | The unit of work is a continuation chain (B; A and C design so) | = | ≠ | = | keep | All three plan chains, and NUM-18's note has one: a member that starts from a converged neighbour solves its target rung alone. |
| FR-25 | A manifest with hashes, versions, solver settings and every switch off its default. | The same, with each term's verification status (A) | = | = | = | keep | All three keep it. A's addition is the ledger's row below. |
| FR-26 | A case file read back gives the same run configuration. | None better found | = | = | = | keep | All three keep the test on meaning and not on text. |
| FR-27 | Every stage runs alone, can be cancelled and emits a typed, hashed artefact. | None better found | = | = | = | keep | The same staged, content-addressed artefacts in all three designs. |
| FR-28 | Exports fields and the case file from a completed run; v0.7. | None better found | = | = | = | keep | All three keep it; B's single-file bundle is `nanopnp project`'s pack. |
| FR-29 | May adapt the mesh to the current by dual-weighted residuals; after version 1. | Each quantity carries an error estimate from a refinement ladder; adaptivity follows | ≠ | ≠ | ≠ | change now: split | All three promote it: a number without an error estimate cannot be compared across models, nor with the paper at v0.13. A ladder of three meshes runs on today's sweep; the adjoint route stays later. |
| FR-30 | Draws each stage's figure from stored artefacts, by an optional extra; fixed drawing rules. | Parts (a), (c), (d) stay; the drawing rules of (b) go to the design (C) | ≠ | = | ≠ | keep | Delivered at v0.5 and in use. Moving (b) saves words, and that waits for the clause's next amendment. |
| FR-31 | The workbench as six suites in a project, with rail, count and queue on screen. | The requirement states the tasks and what stays on screen; the suites are the design's | ≠ | ≠ | ≠ | change later: Phase 7's round | As IF-09: three designers, three layouts. The clause cites seven rows of the design document, which already governs. |
| FR-32 | A project is a plain folder of named models, studies, results and runs. | A case plus differences in place of three kinds of model (A) | ≠ | = | = | keep | B and C keep it for openness. A's difference from a parent is taken for physics models in FR-40's row. |
| FR-33 | Links, both ways, residue and charge map, geometry and parameters, field and probes. | The same, held in the design document (C) | = | = | ≠ | keep | B: the link from a residue to the charge map is what a laboratory reads. |
| FR-34 | Marks and counts every value off its default, in one table. | None better found | = | = | = | keep | Each design shows deviations the same way. |
| FR-35 | Refuses a value at its field, with the rule, the value and a remedy. | None better found | = | = | = | keep | All three keep it. |
| FR-36 | A guided route through the suites from a clean project; v0.8. | The guided route as the first surface built (B) | = | ≠ | = | keep | A and C keep its place. The author ranks the laboratory third, after two kinds of developer. |
| FR-37 | Prepares a structure: axis, chains, flip and membrane place, with no pore-specific rule. | None better found | = | = | = | keep | All three keep it. |
| FR-38 | Sets a residue's protonation, charge or radii; saved as a variant of its model. | None better found | = | = | = | keep | The cheap mutation scan in each design. |
| FR-39 | Studies override and sweep model values, with variables, expressions and a build forecast. | One study planner (A); without the expression language and the forecast (B, C) | ≠ | ≠ | ≠ | keep | The objection is to its cost, and it is built and delivered at v0.6. The author names today's feature scope as not to lose. |
| FR-40 | A physics model composed from registered building blocks; planned for v0.9. | The composition is the kernel's shape from the start: terms, then models as lists of terms | ≠ | ≠ | ≠ | change now: the kernel; change later: its surfaces, Phase 8 | All three rank it first, as the author does. AZ1 leaves `physics/models.py` whole until Phase 8 so that its lines are redrawn once; yet Phase 6 turns its switches into data and adds the open terms, and Phase 7 rebuilds the Physics suite over it, before that redraw. |
| FR-41 | Replaces a side chain in 3D and rebuilds from it; v0.10. | None better found | = | = | = | keep | All three keep it, behind a vetted optional dependency. |
| FR-42 | Draws the (r, z) domain by hand with lines, arcs and booleans; v0.11. | Registered parametric shapes and a supplied profile first; drawing by hand later (A), or never (B, C) | ≠ | ≠ | ≠ | change later: Phase 10's round | Two designers drop it and one puts parametric shapes first. `geometry.pore.shape` accepts `cylinder` alone; cones and hourglasses serve the ledger and solid-state pores at a fraction of a sketcher's cost. |
| FR-43 | May average a titratable group's charge over its protonation states; v0.10. | None better found | = | = | = | keep | All three keep it as an optional, recorded switch. |
| FR-44 | Draws a stage's, a run's or a sweep's figure from the command line. | None better found | = | = | = | keep | All three keep it. |

### Quality of service, QR-01 to QR-16

| ID | Today, in 15 words | Best alternative | A | B | C | Verdict | Reason |
|---|---|---|---|---|---|---|---|
| QR-01 | Tier 2 analytic benchmarks pass: access conductance to 2 %, manufactured solutions at third order. | The same, with one analytic limit for each term, published | = | = | = | keep | All three keep it and extend it; the extension is the ledger's row below. |
| QR-02 | Published currents and averages within stated bands by v0.13; field comparison not required. | The bands alone, without the clause on a matching stabilised mode (A, B) | ≠ | ≠ | = | keep | The clause already says the field comparison is not required and is recorded, not gated. C reads it so. |
| QR-03 | Fixed charge conserved to 0.1 % of the net charge on the mesh. | None; the physics of §4 | = | = | = | keep | All three keep it. |
| QR-04 | The two current routes agree within a stated tolerance, checked in CI. | None better found | = | = | = | keep | All three keep it. |
| QR-05 | Reproduction of published data agrees with experiment no worse than the source did. | None better found | = | = | = | keep | A: the right bar. |
| QR-06 | A full sweep of 3,675 solves in about a day; throughput linear in workers. | None better found | = | = | = | keep | All three scale at the level of jobs. |
| QR-07 | A direct factorisation of the production problem in acceptable time and memory. | The whole solve, in seconds and gigabytes on a named machine (B, C) | = | ≠ | = | change now: with the speed-up package | "Acceptable" cannot fail, and factorisation is not the cost: at 16,444 elements, an eighth of the clause's size, the full model takes 761 s on four cores, 62 % of it assembly on one thread (REV-156). |
| QR-08 | A case re-run with the recorded versions reproduces every scalar quantity. | None better found | = | = | = | keep | All three keep it. |
| QR-09 | Installs from binary wheels on three systems for Python 3.11 to 3.14. | The same from Python 3.12 | = | = | = | change now: the floor | All three keep wheels only. The newest SciPy, Pint, Zarr and Panel need Python 3.12, and the program pins Pint below 0.26 for that floor. uv fetches a newer Python for a user who has 3.11. |
| QR-10 | An experimentalist installs, loads a structure and gets a prediction unaided; seen at v1.0. | Seen at each workbench release with a timed script (B) | = | ≠ | = | keep | A and C keep it. The laboratory is the author's third user, and each observed trial costs the author's time. |
| QR-11 | Each release from v0.2 ships a graphical surface over what exists then. | A capability is built and tested in the library first; the workbench follows | ≠ | ≠ | ≠ | drop | No designer keeps it. The plan stopped following it: v0.5 added no surface, v0.7 adds none, and v0.9 to v0.12 are library first by BA1 and BA5. It produced the Qt shell that v0.6 replaced. |
| QR-12 | Each gate failure aborts with the gate, the quantity and its location. | None better found | = | = | = | keep | All three keep it. |
| QR-13 | The weak forms are written once, against NGSolve; its importers are a recorded set. | A coordinate object between forms and engine (A) | ≠ | = | = | keep | B and C reject a neutral layer above the engine: it would double the cost of each new term. `numerics/measures.py` already gives the forms their measure, axisymmetric or planar. |
| QR-14 | A new correction is a data file; a model, mesher, solver or stabilisation a registration. | The same from another group's installed package, each registered term with its own analytic case | ≠ | = | ≠ | change now | The program has nine registries and nothing that finds a registration in an installed package: a search of `src/` and `pyproject.toml` for entry points finds none. "Others extend it without you" is the author's measure of success. |
| QR-15 | v0.13 ships documentation, tutorials, a JOSS submission and an archived release. | None better found | = | = | = | keep | All three keep it. |
| QR-16 | The workbench meets WCAG 2.2 AA and works by keyboard alone. | None better found | = | = | = | keep | A and B say their own designs omitted it. The survey found no audit of NiceGUI's components against it. |

### Constraints, CON-01 to CON-14

| ID | Today, in 15 words | Best alternative | A | B | C | Verdict | Reason |
|---|---|---|---|---|---|---|---|
| CON-01 | Version 1 is 2D-axisymmetric and steady; the architecture must not preclude 3D. | The same, with a test: each term assembles under a 3D measure (A, B) | ≠ | ≠ | = | change later: Phase 8 | "Not preclude" cannot fail. The forms already take a measure with two symmetries; a third, Cartesian 3D, on a coarse mesh would make the clause a test when the terms are registered. |
| CON-02 | An analyte is a body of revolution on the pore axis. | None while CON-01 holds | = | = | = | keep | It follows CON-01. |
| CON-03 | Only the axial force is reported. | None while CON-01 holds | = | = | = | keep | It follows CON-01. |
| CON-04 | Azimuthal averaging widens the constriction, so the variance goes with each geometry. | None better found | = | = | = | keep | All three keep it. |
| CON-05 | One mean concentration drives every correction, as in the paper; documented as a limit. | Not a constraint (A); the driver as a registered part (C) | ≠ | = | ≠ | keep | The driver is the paper's physics, PHY-01, which the review takes as given (BA12). The case already names it, `average` or `ionic_strength`. |
| CON-06 | NGSolve and Netgen are the one production backend, within a recorded reach. | FEniCSx, each designer's runner-up | = | = | = | keep | All three chose it unprompted. The survey found no other engine with an automatic Jacobian, curved second-order elements and wheels on three systems without a compiler. |
| CON-07 | Nothing on the user's path needs a compiler, a source build or a JIT. | None; fixed from outside | = | = | = | keep | The author's "any ordinary computer". It is the constraint that decides the engine. |
| CON-08 | The wheels have no MUMPS and no PARDISO; the workbench uses UMFPACK or SuperLU. | The constraint: the default path needs no closed part. The fact moves to ADR-001 (C) | = | = | ≠ | change now: text | The fact is out of date: the installed engine takes PARDISO from pip's `mkl` on Windows and Linux x86-64. MKL is closed, so it can be an option a user registers and never a default. |
| CON-09 | The library is BSD-3-Clause; LGPL and MPL parts unmodified; no PyQt. | Apache-2.0 (A, B) | ≠ | = | = | keep | B: not worth reopening. The renderer's clause leaves when NGSolve's viewer leaves the workbench (WB-57). |
| CON-10 | Gmsh is an optional backend only; the default path does not link it. | None better found | = | = | = | keep | All three keep it. |
| CON-11 | UMFPACK is GPL; the library reaches it through the engine and states the obligation. | None better found | = | = | = | keep | A and B say their designs missed the obligation. `nanopnp --env` states it, checked. |
| CON-12 | No Triangle, MeshPy or TetGen. | None better found | = | = | = | keep | All three keep it. |
| CON-13 | Windows, macOS and Linux on the desktop; Linux for clusters. | None; fixed from outside | = | = | = | keep | All three keep it. Linux means x86-64: the engine has no wheel for Linux on ARM. |
| CON-14 | The repository carries a `CITATION.cff`. | None better found | = | = | = | keep | All three keep it. |

### Exclusions, N1 to N7

| ID | Today, in 15 words | Best alternative | A | B | C | Verdict | Reason |
|---|---|---|---|---|---|---|---|
| N1 | Not a general framework: users do not write weak forms. | A developer writes terms within electrolyte transport; unrelated problems stay out | ≠ | ≠ | ≠ | change later: Phase 8 | It contradicts the author ("change equations") and FR-40, whose text leaves room for equations the user writes. |
| N2 | No molecular dynamics; trajectories are an input. | None better found | = | = | = | keep | All three keep it. |
| N3 | No time-dependent simulation. | None better found | = | = | = | keep | All three keep it and leave room. |
| N4 | No full 3D in version 1; the architecture must not preclude it. | A release of its own for 3D (A, B) | ≠ | ≠ | = | keep | The author puts the base first. The change is in the backlog's order, §2.7's last row. |
| N5 | No flexible analytes, and none off the axis. | Off-axis analytes with 3D (A) | ≠ | = | = | keep | It follows CON-01. |
| N6 | No fitting of corrections from molecular dynamics. | A planned capability (A) | ≠ | = | = | keep | B and C keep it for version 1; the backlog names the toolkit. |
| N7 | No COMSOL file import or export. | None better found | = | = | = | keep | All three keep it. |

### The dependencies of §2.6

| ID | Today, in 15 words | Best alternative | A | B | C | Verdict | Reason |
|---|---|---|---|---|---|---|---|
| §2.6 NGSolve | NGSolve and Netgen 6.2.2606 or later: the finite-element backend and default mesher. | FEniCSx | = | = | = | keep | Three of three, unprompted. Checked at its source: wheels for three systems, no compiler, UMFPACK inside. |
| §2.6 Gmsh | Gmsh as an optional mesher backend. | Netgen alone (B) | = | ≠ | = | keep | `mesh/` changed in 3 of 20 packages, so the second backend costs little to keep. Gmsh's size fields are the fallback if Netgen cannot mesh a wall layer. |
| §2.6 MDAnalysis | MDAnalysis reads PDB files and trajectories and aligns frames. | MDAnalysis for trajectories alone, gemmi for both structure formats | ≠ | ≠ | ≠ | keep | The survey favours today's stack. One reader for both formats is tidier, and nothing measured shows a cost of two. |
| §2.6 gemmi | gemmi reads mmCIF, which MDAnalysis does not. | gemmi for PDB too, and for the entry's assembly | ≠ | ≠ | ≠ | keep | As the row above. B's oligomer from the entry's assembly would need it, and FR-03 takes the oligomer from the case. |
| §2.6 PDB2PQR | PDB2PQR assigns protonation states and partial charges. | Force-field charges through OpenMM (A's runner-up) | = | = | = | keep | Prompted: the pack's physics names it. Pure Python and installed everywhere. |
| §2.6 PROPKA | PROPKA predicts pKa values, as a dependency of PDB2PQR. | None better found | = | = | = | keep | Prompted, as PDB2PQR. Its last release is of January 2024, which the mutator's phase should weigh. |
| §2.6 APBS | APBS cross-checks Poisson alone, from test-only wheels. | None better found | = | = | = | keep | Each design holds the same cross-code check. |
| §2.6 scikit-image, Shapely | scikit-image extracts the contour and Shapely conditions the polyline. | None better found | = | – | = | keep | A and C name the same pair; both are wheels on every platform. |
| §2.6 meshio, GridDataFormats | meshio exchanges meshes; GridDataFormats reads and writes the grids. | The engine's own writer for the archive mesh | – | – | – | keep | No designer names either. meshio has had no release for 22 months: a risk to watch, with no fault found. |
| §2.6 UMFPACK | UMFPACK from the engine's wheel is the default direct solver. | PARDISO where a user installs it | = | ≠ | = | keep | B's SuperLU floor did not factorise the reference problem (CON-11), as B then granted. UMFPACK is the one direct solver in the wheel on all three systems. |
| §2.6 SuperLU | scipy's SuperLU is the selectable fallback. | None better found | – | = | = | keep | The open floor in B's and C's designs. |
| §2.6 NiceGUI, FastAPI | NiceGUI and FastAPI are the workbench's front end and server. | A React application on FastAPI (A, B); trame (C) | ≠ | ≠ | ≠ | keep | ADR-004's row holds the argument. No designer chose NiceGUI blind; C kept it once it read of the measured spike, A called its own verdict its weakest, and B granted that the spike may outweigh its choice. |

### The releases of §2.7, from v0.7

| ID | Today, in 15 words | Best alternative | A | B | C | Verdict | Reason |
|---|---|---|---|---|---|---|---|
| §2.7 v0.7 | Phase 6: the cleanup, this review, then the library's foundations, provisional. | The same, with what this review proposes for now | – | – | – | change now | Its content waits on these rulings (BA4, BA11). The rows marked change now are its additions. |
| §2.7 v0.8 | Phase 7: the workbench rebuilt on its foundations, with five moved packages. | The workbench built once, after the kernel holds | ≠ | ≠ | ≠ | keep | Each design builds its workbench after the composed kernel. With the kernel's shape in Phase 6 (FR-40) the rebuild meets that order where it stands. |
| §2.7 v0.9 | Phase 8: the physics composer, library first. | Its kernel in Phase 6; its surfaces here | ≠ | ≠ | ≠ | change now | As FR-40's row. What stays here is composition from the case file, terms from another package under N1's new text, and the workbench's surface. |
| §2.7 v0.10 | Phase 9: the structural mutator, with fractional protonation. | The same, with per-residue sensitivities | – | = | = | keep | B and C place mutation after the base, as here. The sensitivities are a row of their own below. |
| §2.7 v0.11 | Phase 10: the hand-drawn sketcher of the (r, z) domain. | Parametric shapes; the sketcher after version 1 | ≠ | ≠ | ≠ | change later: Phase 10's round | As FR-42's row. |
| §2.7 v0.12 | Phase 11: the analyte forces, library first. | None better found | = | = | = | keep | Each design holds the capability after its base. |
| §2.7 v0.13 | Phase 12: validation against the published results, documentation and release, last. | A first comparison with the paper before the workbench is built on the model | ≠ | ≠ | ≠ | keep | The validated release stays last. Each design compares with the published pore before it builds a workbench; that is BA3's row. |
| §2.7 v1.0 | Version 1: the stability promise; its content decided at Phase 12's close. | None better found | – | – | – | keep | No designer speaks to it; BA6's row. |
| §2.7 post-1.0 | The backlog after version 1: nine items in no order. | The author's order: 3D, the molecular link, inverse design, then the rest | ≠ | ≠ | = | change now: text | The interview ranks three of the nine. A and B would schedule 3D. Ranking the row costs one line and tells each phase which room to leave. |

### The rulings BA1 to BA15 and BB1 to BB6

| ID | Today, in 15 words | Best alternative | A | B | C | Verdict | Reason |
|---|---|---|---|---|---|---|---|
| BA1 | All three tools, composer, mutator and sketcher, are built before validation. | Composer and mutator before validation; parametric shapes in the sketcher's place | ≠ | ≠ | ≠ | change later: Phase 10's round | No design builds a sketcher before it validates. The composer and the mutator stand; FR-42's row reduces the third. |
| BA2 | Phase 7 rebuilds the workbench in full, then builds the five moved packages. | A trial of the kit before the rebuild starts | – | – | – | keep | 28 of the 59 open items are the interface's and `gui/` changed in 15 of 20 packages. A full rebuild is also the one cheap moment to settle the kit, which ADR-004's row asks. |
| BA3 | No early check against the published results; validation is last. | One recorded, ungated comparison with the paper's ClyA curves in Phase 6 | ≠ | ≠ | ≠ | change now | Three of three blind designs compare with the published pore before a workbench. The author's reason, that exact digits are not the aim, is met by bands; a gap found at Phase 12 reaches five phases. |
| BA4 | Phase 6 keeps its drafted content in about ten packages. | The same, grouped again with what the round rules | – | – | – | change now | Provisional until this round by its own text. |
| BA5 | The analyte forces are Phase 11, before validation. | After validation (A, B) | ≠ | ≠ | – | keep | The published model has no analyte, so the order of Phases 11 and 12 moves neither one's result. |
| BA6 | Version 1's content and gate are decided at validation's close. | None better found | – | – | – | keep | No evidence speaks against it. IF-03's row adds one thing for that gate to name. |
| BA7 | A session may restructure any code it works with while every test passes. | None better found | – | – | – | keep | The median package changed 7 to 8 subpackages, so a plan cannot name every file. A start-over would give the same freedom under the stored numbers. |
| BA8 | The channel axis's fault at a ragged rim is fixed in Phase 6. | None better found | – | – | – | keep | A fault of correctness in a capability users have. No proposal moves it. |
| BA9 | Fractional protonation joins the mutator's phase. | None better found | = | = | = | keep | All three keep FR-43 where it is. |
| BA10 | Phase 6 gains a review of the program from the ground up. | None | – | – | – | keep | This report. Spent when the round has ruled. |
| BA11 | The review is the next package; the rest of Phase 6 waits for its rulings. | None | – | – | – | keep | Spent with the round. Its order let FR-40's row reach the restructure in time. |
| BA12 | The review may question everything but the paper's physics. | None | – | – | – | keep | The reach of this walk. |
| BA13 | The review hands back a report; the author rules; no code changes. | A report with throwaway trials | – | – | – | keep | Five questions needed a trial and are open items for the round; nothing else was held back by the rule. |
| BA14 | A restructure is pushed on the per-push tests; five golden walks run nightly. | The walks chosen by the paths a push changes | – | – | – | keep | The cost of the five walks is not measured. §7.6's row holds the gate's selection. |
| BA15 | The decisions register gives a ruling to a package only where it was ruled there. | None | – | – | – | keep | Mechanical, and done. |
| BB1 | The author rules on the review's proposals before the axis fix is built. | None | – | – | – | keep | No proposal changes how a pore's axis is found, so the fix stands as BA8 has it. |
| BB2 | The review designs for the whole program, built and planned. | None | – | – | – | keep | The reach of the design in the report. |
| BB3 | Blind designs from the purpose first, then a walk rule by rule. | None | – | – | – | keep | The guard changed verdicts: on QR-11, FR-42 and BA3 the walk follows three blind designs against the plan. The report says what it showed. |
| BB4 | The report is one page on the project's site, with appendices. | None | – | – | – | keep | Spent. |
| BB5 | Fable 5.2 writes the review and Opus 5.5 checks it. | None | – | – | – | keep | Spent at the ship. |
| BB6 | The review opens with an interview of the author. | None | – | – | – | keep | The interview gave the ranks that decide FR-40, N1 and the backlog's order. A start-over would open so. |

### What the lists lack

| ID | Today, in 15 words | Best alternative | A | B | C | Verdict | Reason |
|---|---|---|---|---|---|---|---|
| add-1 | No page maps each term and correction to the analytic case that proves it. | A ledger generated from the tests and published with each release; the cheap cases run by a command | ≠ | ≠ | ≠ | add now | Named by all three. "Every part holds against its analytic limits" is the author's first measure of success, and QR-01 gates the limits without showing them. A term with no case is marked unverified in the manifest: a badge, not a gate. |
| add-2 | No quantity carries an estimate of its discretisation error. | An error estimate for each quantity, from a ladder of three meshes | ≠ | ≠ | ≠ | add now | FR-29's row. Named by all three. |
| add-3 | No sensitivity of a quantity to a residue's charge. | One transposed solve gives a quantity's sensitivity to every atomic charge | ≠ | ≠ | ≠ | add later: Phase 9 | Named by all three as the foothold of inverse design. The engine solves the transposed system with the same factors (checked), and the fixed charge is linear in each atom's charge. |
| add-4 | Solved fields leave only as XDMF; nothing is written for a molecular simulation. | Potential, concentration and flow on a 3D lattice for molecular or Brownian dynamics | ≠ | – | ≠ | add later: after version 1 | The author's second horizon after the base. IF-05 already writes the formats. |
| add-5 | The one idealised pore is a cylinder. | Cone, hourglass and a given surface charge as registered shapes | ≠ | ≠ | ≠ | add later: Phase 10 | FR-42's row. Named by all three, for solid-state pores and as the ledger's public cases. |
| add-6 | A result does not say whether its conditions lie inside the validated range. | Each result classed validated, extrapolated or outside (B) | – | ≠ | – | add later: Phase 12 | Validation defines the range, so the class can be stated when it is measured. The manifest already lists each switch off its default. |
| add-7 | One bulk concentration for both reservoirs; no measured data beside a curve. | Asymmetric reservoirs with the reversal potential; an overlay of measured current–voltage data (B) | – | ≠ | – | add later: after version 1 | What a laboratory measures. It is a boundary value and not an equation, and the author ranks the laboratory third; it joins the backlog. |
| add-8 | The same wheels on a cluster; no container, no MPI. | A container image with MPI for heavy work (A, C) | ≠ | – | ≠ | not added | FR-24 dispatches job arrays from the wheels. A container earns its upkeep when 3D needs a distributed solve, and not before. |
| add-9 | Model comparison is a sweep over `models.physics`. | Comparison as a product of its own (C) | – | – | ≠ | not added | FR-39 (b) already sweeps over physics models on one pore; FR-40's variants make the differences small to state. |

In the last table `≠` marks a designer who named the lack. Lacks that fall under a row above are not repeated: the
registration from another package is QR-14's, records that open again IF-03's, the residual current FR-22's, a
number for the solve's time QR-07's, room for 3D CON-01's, and a check that computes numbers on the user's machine
add-1's. Two lacks are of the next part: a second pore in validation and a measurable target for the process.

## The design, the methods, the verification, the process and the workbench

The 118 rows of this part hold 98 verdicts of keep, 11 of change now, 7 of change later and 2 of add.

Four rows go against all three designers. NUM-18's fixed ladder is kept until a trial, and the platforms of a pull
request's CI are kept as AZ8 ruled them, although each designer chose otherwise. §7.3 gains a manufactured solution
for each term, and the Python floor of §8.4.2 moves, although each designer kept them.

The eleven verdicts of change now are five proposals: the composed kernel (ADR-005, §5.4, §7.3), registration from
installed packages (§5.5), the error estimate (NUM-32), the Python floor (§8.4.2), and one command that carries a
package (§8.4.4 (1), (8), (14), (16) and §8.4.5 (1)).

### The architecture decisions, ADR-001 to ADR-005

| ID | Today, in 15 words | Best alternative | A | B | C | Verdict | Reason |
|---|---|---|---|---|---|---|---|
| ADR-001 | NGSolve is the one production backend; the weak forms are stated once against it. | FEniCSx, each designer's runner-up | = | = | = | keep | Three of three, unprompted, on the grounds the decision records. Its consequence row calls PARDISO absent, which CON-08's row corrects. |
| ADR-002 | Netgen is the default mesher; Gmsh an optional one behind an adapter. | Netgen alone (B) | = | ≠ | = | keep | As §2.6's Gmsh row. |
| ADR-003 | BSD-3-Clause core; extras may be GPL-compatible. | Apache-2.0 (A, B) | = | = | = | keep | All three keep it after the unblinding. |
| ADR-004 | The workbench is NiceGUI on FastAPI, written in Python, with no build step. | A React application over a JSON interface (A, B); trame (C) | ≠ | ≠ | = | keep | The author chose it on a measured spike of one screen: 169 lines against 246, redraw 22 ms against 14 ms. At 18,183 lines a like paint takes 315 ms (REV-258). Phase 7's rebuild is the one cheap moment to measure again on a rebuilt suite, before the rest follows. |
| ADR-005 | Two levels of extension: corrections as data files, physics models as classes. | Three levels: corrections as data, terms as registered functions, models as compositions; from any installed package | ≠ | ≠ | ≠ | change now: with FR-40 | Each designer adds the same third level. Two levels cannot say "swap one term" or "compare two models" (C). Its rejected alternative cites N1, whose row changes. |

### The software design of §5, but §5.6

| File | Today, in 15 words | Best alternative | A | B | C | Verdict | Reason |
|---|---|---|---|---|---|---|---|
| §5 index | The index page of the software design. | None | – | – | – | keep | A list of its pages. |
| §5.1 | A linear pipeline of twelve cacheable stages in twenty subpackages. | Seven to eleven components with the same content-addressed stages | = | = | = | keep | Each design has the same pure, hashed stages. The median package changed 7 to 8 of the 20 subpackages and `pipeline/run.py` changed in 12 of 20; Phase 6's typed run record and stages that take their upstream answer that, and nothing here adds to it. |
| §5.2 | The contract of each stage, in 8,742 words and 19 notes. | An implicit geometry first (A); a spline profile and adaptive mesh (B) | ≠ | ≠ | = | keep | The rows FR-04 to FR-10 hold each particular; none is supported by a measurement yet. |
| §5.3.1 | The case file key by key, in 10,164 words and 29 notes. | The reference generated from the schema, whose fields carry their descriptions | = | = | = | keep | Prompted: the pack names a YAML case. All three generate forms and reference from the schema. The clause says in prose what the schema's field descriptions also say; trimming it waits for an amendment. |
| §5.3.2 | Artefacts keyed by a content hash; the interchange formats. | None better found | = | = | = | keep | The same content-addressed store in every design. |
| §5.3.3 | The provenance manifest's fields. | The same, with each term's verification status | = | = | = | keep | As FR-25's row. |
| §5.3.4 | The sweep document and the collected dataset. | Continuation chains as the planner's unit (B) | = | ≠ | = | keep | NUM-18's note already has a member that starts from a neighbour solve its target rung alone, so a chain exists wherever a neighbour is stored. |
| §5.3.5 | The project folder: named models, studies, runs, a project file with no physics. | A case plus differences (A) | ≠ | = | = | keep | As FR-32's row. |
| §5.4 | The backend interface, not built; the correction and physics-model interfaces. | The term as the unit: its weak form, its equation as text, its switches and its analytic case in one object | ≠ | ≠ | ≠ | change now: with FR-40 | AZ1 hands §5.4.1 and the size of `physics/models.py` to Phase 8's round. Eleven of twenty subpackages import the engine, where each design confines it to two or three layers; `gui` leaves that list when NGSolve's viewer does. |
| §5.5 | The extension points: two levels, and registries added by one registration. | Registrations found in installed packages, each with its analytic case | ≠ | ≠ | ≠ | change now | As QR-14's row. REV-67 already asks whether the registering functions are public. |

### The numerical methods, NUM-01 to NUM-34

| ID | Today, in 15 words | Best alternative | A | B | C | Verdict | Reason |
|---|---|---|---|---|---|---|---|
| NUM-01 | Continuous Galerkin on triangles: second order, Taylor–Hood for the flow. | Hybridised discontinuous Galerkin (A's runner-up) | = | = | = | keep | Three of three chose the same elements unprompted; the reference's linear flow pair was in the pack. |
| NUM-02 | Primitive concentrations by default; a log branch behind a flag. | Log-concentrations by default (B) | = | ≠ | = | keep | A and C choose primitive variables, C with the log form as a registered alternative, which the program has. Both timed cases converge in primitive variables with no negative concentration. |
| NUM-03 | The velocity–pressure pair is configurable; equal order only with stabilisation. | None better found | – | – | – | keep | No designer speaks to it. |
| NUM-04 | The axisymmetric weak forms, each integral with the r weight. | A grad-div term on the flow (A) | = | = | = | keep | The forms follow from §4. A's worry, that Taylor–Hood is not pressure-robust against a body force that is mostly a gradient, is what VER-14's capillary flow tests; it passes. |
| NUM-05 | The hoop-strain term is assembled. | None; it is the equation | – | – | – | keep | Part of the form. |
| NUM-06 | On the axis only the radial velocity is essential; the rest is natural. | None better found | – | = | = | keep | B and C state the same condition. |
| NUM-07 | Every form with a 1/r factor is assembled at order three or above, asserted. | None better found | – | – | – | keep | A trap found by implementing; a start-over would meet it again. |
| NUM-08 | A unit test integrates a 1/r-weighted quantity on an axis-touching mesh. | None better found | – | – | – | keep | It guards NUM-07. |
| NUM-09 | The equations are solved in nondimensional variables: nm, thermal voltage, bulk concentration. | None better found | = | – | – | keep | A scales the same way. |
| NUM-10 | Row scaling after nondimensionalisation, done by the direct solvers. | None better found | – | – | – | keep | No designer speaks to it. |
| NUM-11 | The production solve runs without stabilisation; SUPG behind a flag. | None better found | = | = | = | keep | Three of three, each by the cell Péclet argument. Measured: the largest cell Péclet of the two timed cases is 0.074 and 0.334. |
| NUM-12 | The cell Péclet number is evaluated on each converged state, with a warning. | None better found | = | – | = | keep | A computes the same per-run gate. |
| NUM-13 | The stabilisation mode is recorded with each run. | None better found | = | – | = | keep | A and C record it. |
| NUM-14 | An optional stabilised mode reproduces the reference's settings. | No such mode (A, B) | ≠ | ≠ | – | keep | A start-over would not build it: it reproduces settings and not an operator, and the author puts extension above exact digits. It is built, off by default, and Phase 12 may still want the like-for-like run, so deleting it gains little. |
| NUM-15 | Integration orders of the stabilised mode's terms. | None better found | – | – | – | keep | It follows NUM-14. |
| NUM-16 | Monolithic damped Newton on the coupled system with a direct solve. | A segregated iteration, each designer's runner-up | = | = | = | keep | Three of three chose a fully coupled Newton with the exact Jacobian, unprompted. |
| NUM-17 | Positivity and packing fraction asserted at every Newton step. | None better found | = | = | = | keep | Each design asserts the same, B beside its log variables. |
| NUM-18 | A fixed ladder of nine stages; corrections on before the salt ramp. | Adaptive steps (A, B, C); the salt ramp in the classical model, before the corrections | ≠ | ≠ | ≠ | keep | Kept until a trial. The corrections make a Newton step six to thirteen times dearer (the timed cases; REV-156), and six of a run's rungs carry them, four of those the salt ramp. Whether the corrections switch on at the target concentration over FR-17's envelope only a run can say. |
| NUM-19 | The mesh adapts between rungs only. | None better found | – | – | – | keep | No adaptivity is built. |
| NUM-20 | Fallbacks, in order: pseudo-transient, hybrid segregated, a PB start, backtracking. | None better found | = | = | = | keep | Each design keeps a segregated or pseudo-time fallback. |
| NUM-21 | A sparse direct solve by default: UMFPACK, or SuperLU. | PARDISO where installed | = | = | = | keep | Prompted: the pack names a sparse direct solve. The factorisation is not the cost: 24 % of the measured solve, against 62 % for the Jacobian's assembly on one thread (REV-156). |
| NUM-22 | An iterative fallback before any 3D capability. | None better found | = | = | = | keep | Each design names block-preconditioned Krylov methods for 3D. |
| NUM-23 | The current is never a cross-section integral of the flux. | None better found | = | = | = | keep | Three of three, unprompted. |
| NUM-24 | The current and flow rate by the domain-indicator form. | None better found | = | = | = | keep | Each design's volume functional. |
| NUM-25 | The variational reaction flux as the second route. | None better found | = | – | = | keep | A's and C's first route. |
| NUM-26 | The two routes agree to 10⁻³ relative, checked in CI. | None better found | = | = | = | keep | Each design cross-checks two routes. |
| NUM-27 | Transport number, rectification, conductance and flow rate from the same integrals. | None better found | – | – | – | keep | It follows NUM-24. |
| NUM-28 | The force on an analyte in domain form, each part with its consistency term. | None better found | = | = | = | keep | Each design evaluates forces as volume functionals. |
| NUM-29 | Each force part resolved below 1 pN; the routes agree to 0.1 pN. | None better found | – | – | – | keep | No designer speaks to it. |
| NUM-30 | First wall layer min(0.05 nm, a fifth of the Debye length); graded outwards. | Refinement towards the quantity from a coarse start (B) | = | ≠ | – | keep | A's rule, a third of the wall function's length and a quarter of the Debye length, gives the same 0.05 nm. The refinement ladder of FR-29's row tests the rule by measurement. |
| NUM-31 | The wall-distance field, mollified where the physics allows. | None better found | – | – | – | keep | PHY-02's field; each design computes it its own way. |
| NUM-32 | Goal-oriented adaptivity may be provided; never a default in version 1. | An error estimate for each quantity first, from a refinement ladder | ≠ | ≠ | ≠ | change now: with FR-29 | As FR-29's row. NUM-33's own note says the published results carry no error bar, so the convergence study is new work that validation needs. |
| NUM-33 | The estimator should use a linear PB surrogate, not the full adjoint. | The full adjoint: one transposed solve with the factors Newton already holds | ≠ | ≠ | ≠ | change later: Phase 9 | The surrogate's reason is cost. With a direct solver the factors exist, and the engine solves the transposed system with them (checked), so the full adjoint costs one back-substitution. |
| NUM-34 | The wall-distance field is gated at −10⁻³ nm where a wall correction is on. | None better found | – | – | – | keep | A gate with its tolerance argued; a start-over would need it. |

### Verification: §7.1 to §7.6, VER-61, VER-62 and VER-65

| ID | Today, in 15 words | Best alternative | A | B | C | Verdict | Reason |
|---|---|---|---|---|---|---|---|
| §7.1 | Four tiers, analytic benchmarks before any whole-model comparison; a narrow test scope. | None better found | = | = | = | keep | Each design builds the same ladder of trust in the same order. |
| §7.2 | Tier 1: 61 rows of unit and property tests, on every push. | The browser grid nightly (A) | = | = | = | keep | The grid of 149 browser tests takes 468 s of the push gate's 539 s; §7.6's row holds that. |
| §7.3 | Tier 2: eleven analytic benchmarks and a manufactured solution of the coupled system. | The same, with one manufactured solution for each registered term, derived by the harness (B, C) | = | = | = | change now: with FR-40 | The benchmarks stand. A term from another package is trusted only if it brings its own case, and the program holds SymPy already, so the harness can derive a term's source. |
| §7.4 | Tier 3: comparison with the reference model, APBS and the published results; not gated. | The same, earlier (BA3's row) | = | = | = | keep | Each design holds the same cross-code rung, as bands. |
| §7.5 | Tier 4: reproduction of experiments before a release; no job yet. | The same, with a second pore (B) | = | = | = | keep | Each design's last rung. The second pore is a row below. |
| §7.6 | A pull request tests on Linux; three platforms on `main`, nightly and at a release. | Three systems on every change (A, B, C); the browser grid chosen by the paths a push changes | ≠ | ≠ | ≠ | change later: Phase 7 | AZ8 keeps the platforms off a pull request for their cost, and nothing measured argues against it. The browser grid runs in the push gate alone, on every change of code, and CI's legs skip it; when Phase 7 rebuilds those tests, CI's Linux leg can run them and the gate choose them by path. |
| VER-61 | The import relation of the subpackages equals a recorded file, both ways. | None better found | – | – | – | keep | It is what makes BA7's freedom safe. A start-over would hold the same guard. |
| VER-62 | The numbers of seven walks are held at 10⁻⁸ against stored values. | None better found | – | = | – | keep | B holds the same golden bundles. Every proposal on a numerical method names its re-pin against it. |
| VER-65 | The subpackages that import the engine equal a recorded list of eleven. | The same guard over two or three layers | = | = | = | keep | Each design confines the engine and would guard it. The list is long; §5.4's row says where it shrinks. |

### The process: the 41 rules of §8.4

| Rule | Today, in 15 words | Best alternative | A | B | C | Verdict | Reason |
|---|---|---|---|---|---|---|---|
| §8.4.1 (1) | A version is a git tag, never a number in the package. | None better found | – | – | – | keep | No cost found. |
| §8.4.1 (2) | Each merged package takes an alpha tag, pushed by a workflow. | None better found | – | – | – | keep | It gave the evidence its 24 ranges; a package's cost can be read from the tags. |
| §8.4.1 (3) | A phase's close takes the release tag alone. | None better found | – | – | – | keep | No cost found. |
| §8.4.1 (4) | A package merged before the previous release takes no tag. | None better found | – | – | – | keep | No cost found. |
| §8.4.2 (1) | The push gate passes on the tree before a push. | The browser grid chosen by path | – | – | – | keep | §7.6's row holds the one change. |
| §8.4.2 (2) | How the gate refuses, and git's own pre-push hook. | None better found | – | – | – | keep | Mechanism. |
| §8.4.2 (3) | The session-start hook brings `main` up to date. | None better found | – | – | – | keep | Mechanism. |
| §8.4.2 (4) | Python 3.14 is the default and 3.11 the minimum. | 3.12 the minimum | = | = | = | change now: with QR-09 | As QR-09's row. |
| §8.4.2 (5) | One rule for prose in code: docstrings on public names, few comments. | None better found | – | – | – | keep | No cost found. |
| §8.4.3 (1) | A test names the silent failure it catches; a plan commits none. | None better found | – | – | – | keep | C asks the same of a requirement: one without a test is a wish. |
| §8.4.3 (2) | The ship deletes tests outside the scope. | None better found | – | – | – | keep | It keeps the gate's time down. |
| §8.4.4 (1) | Three commands with levels: plan, implement, ship. | One command that carries a package from its brief to its pull request | ≠ | ≠ | ≠ | change now | The author's one complaint is the sessions he must start. A package takes at least four windows, each ended by a compaction he runs, and about eight touches, most of them a command or a compaction and not a judgement. Each designer keeps the form and cuts the starts. |
| §8.4.4 (2) | A pull request's CI tests on Linux; the close reads three platforms. | None better found | ≠ | ≠ | ≠ | keep | §7.6's row. |
| §8.4.4 (3) | `/np-gui` renders screens for the author's verdicts; a suite opens with prototypes. | None better found | = | = | = | keep | Each design puts mockups and the author's verdicts before the code. |
| §8.4.4 (4) | The workflow runs on Claude Code alone. | None better found | – | – | – | keep | Ruled at WP6.03; no cost found. |
| §8.4.4 (5) | A package is named by phase and number. | None better found | – | – | – | keep | No cost found. |
| §8.4.4 (6) | A plan lives in its phase's folder. | None better found | – | – | – | keep | No cost found. |
| §8.4.4 (7) | A commit that changes a decision regenerates the decisions pages. | The register generated from the tests and the rulings alone (B) | – | ≠ | – | keep | Generated already; the cost is one command a commit. |
| §8.4.4 (8) | One package, one pull request; implement pauses before the ship. | No pause where the author has nothing to judge | ≠ | ≠ | ≠ | change now: with (1) | The pause before the ship is a compaction and a command. The switch that removes it exists and is off by default. |
| §8.4.4 (9) | A session may restructure what it works with while the gate passes. | None better found | – | – | – | keep | BA7's row. |
| §8.4.4 (10) | At most two lanes; the second is the next phase's design study. | None better found | – | – | – | keep | A study beside the build is how each design starts its workbench early. |
| §8.4.4 (11) | Each plan and pull request opens with a brief a non-coder can read. | None better found | = | = | = | keep | B's one-page brief and one-page result. |
| §8.4.4 (12) | A package's plan is grounded in the code, within 3,500 words. | A plan as one issue with executable acceptance tests (A) | ≠ | – | – | keep | The plans hold 453,720 words in 104 files. The caps were set at the cleanup, two packages ago, and their effect is not yet measured. |
| §8.4.4 (13) | Each work item names its executor; one commit an item. | None better found | – | – | – | keep | It let this package resume after each compaction from the plan's ticks alone. |
| §8.4.4 (14) | Each plan pauses for a compaction, then a review in a new window. | The review chained to the plan | ≠ | ≠ | ≠ | change now: with (1) | Two of a package's four windows are its plan and the plan's review. |
| §8.4.4 (15) | A choice put to the author carries what a non-coder needs to judge it. | Batched rulings, each with a default that applies unless overruled (A, B) | ≠ | ≠ | – | keep | The form is the author's. A default that applies unanswered would change who decides, which the author did not ask for. |
| §8.4.4 (16) | A compaction checkpoint is a work item that ends the turn, unless switched off. | The switch set by default | ≠ | ≠ | ≠ | change now: with (1) | This package pauses at four checkpoints, each a compaction and a command with nothing for the author to judge. |
| §8.4.4 (17) | A phase plan states each package's current scope. | None better found | – | – | – | keep | No cost found. |
| §8.4.4 (18) | A phase plan holds 2,500 words. | None better found | – | – | – | keep | As (12). |
| §8.4.4 (19) | Every ruling lands in a current clause. | None better found | – | – | – | keep | It is why a clause could be walked here without its history. |
| §8.4.4 (20) | No ruling leaves the history. | A decision log of half-page entries (A, C) | ≠ | – | ≠ | keep | The history holds 72,141 words and is read on demand, so its weight costs a session nothing. |
| §8.4.4 (21) | An implementing session's first window reads at most 8,000 words. | None better found | – | – | – | keep | Two packages old; not yet measured against a later phase. |
| §8.4.5 (1) | The model follows the session's kind; the author picks it at each start. | A level whose model differs runs as a sub-agent of the one session | – | – | – | change now: with (1) | A change of model is what forces a new session between implement and ship. This package's designers ran on two models as sub-agents of one session. |
| §8.4.5 (2) | Three agents and eight scripts are kept. | None better found | – | – | – | keep | Cut to these at WP6.03. |
| §8.4.5 (3) | Each level's report ends with its measured usage. | None better found | – | – | – | keep | The measure a target for touches would be read from. |
| §8.4.5 (4) | Mechanical batches go item by item to sub-agents. | None better found | – | – | – | keep | No cost found. |
| §8.4.6 (1) | An open item is a row of the review register. | None better found | – | – | – | keep | 279 rows gave the evidence its count by area. |
| §8.4.6 (2) | Closed rows move to an archive at a phase's close. | None better found | – | – | – | keep | No cost found. |
| §8.4.6 (3) | A phase closes when each row it owns is fixed or ruled. | None better found | – | – | – | keep | No cost found. |
| §8.4.6 (4) | User-testing findings come only from the author's sessions. | None better found | – | – | – | keep | No cost found. |
| §8.4.6 (5) | Review reports are numbered files. | None better found | – | – | – | keep | 115 reports hold 413,493 words and are read on demand, so no session pays for them. |

### The workbench design, by its 17 sections

| Section | Today, in 15 words | Best alternative | A | B | C | Verdict | Reason |
|---|---|---|---|---|---|---|---|
| Purpose and users | One workbench for three personas; a thin shell that computes no number. | None better found | = | = | = | keep | Each design's workbench is a client that holds no physics. |
| Today's shell | The retired Qt shell's capabilities, in 1,634 words. | Out of the design document | – | – | – | change later: Phase 7's round | It describes a shell removed at v0.6. With *Tabs or areas*, *Restated clauses* and *Inherited rows* it is spent: about 3,000 of the document's 16,450 words. |
| The areas | The author's areas placed in six suites. | None better found | – | – | – | keep | The author's own list. |
| Organisation | Suites in a project: four build models, two use them. | Three workspaces (A); one route first (B) | ≠ | ≠ | – | keep | The author ruled it over concept boards, in his own words. No blind designer saw a board, and a verdict on a picture outweighs a design made without one. The laboratory's route is the guided route. |
| Look and feel | One token set; each suite borrows the idiom of a tool the author named. | None better found | – | – | – | keep | The author's taste, ruled on tiles. |
| Tabs or areas | Where each Qt tab's capability went. | Out of the design document | – | – | – | change later: Phase 7's round | Spent, as *Today's shell*. |
| Tools | Each tool's settings and live view, by suite. | None better found | – | – | – | keep | What Phase 7 rebuilds on its foundations. |
| The four live links | Four pairs linked both ways until unlinked. | None better found | = | = | ≠ | keep | As FR-33's row. |
| The project folder | A plain folder, readable without the workbench. | None better found | ≠ | = | = | keep | As FR-32's row. |
| Install and start | One `uv` command; a local server; the browser speaks through a network interface. | A documented interface that a script or another front end could drive | ≠ | ≠ | = | keep | The interface that exists serves pictures and scenes: 21 GET routes, and none starts a build. The boundary that holds is the view-models over the `Session`. "A remote server later without a redesign" is untested. |
| The guided route | A layer over the one interface, from a clean project. | The first surface built (B) | = | ≠ | = | keep | As FR-36's row. |
| Later tools | Composer, mutator and sketcher, each a later phase. | As FR-40's and FR-42's rows | ≠ | ≠ | ≠ | change later: Phase 7's round | It follows those rows. |
| The shell's reading of artefacts | The server reads artefacts through the library; Mol\* and Plotly draw. | vtk.js or an own renderer for fields (A, B) | ≠ | ≠ | = | keep | Three of three chose Mol\* unprompted, and C chose Plotly. The shell computes numbers at 12 sites today, which Phase 6 moves into the library. Whether Plotly pans a field map of 10⁵ cells needs a trial. |
| Restated clauses | How the Qt shell's clauses were restated. | Out of the design document | – | – | – | change later: Phase 7's round | Spent, as *Today's shell*. |
| Inherited rows | Seventeen rows that waited on the document. | Out of the design document | – | – | – | change later: Phase 7's round | Spent, as *Today's shell*. |
| Decision log | The 63 rulings WB-01 to WB-63, in the author's words. | None better found | – | – | – | keep | Each is the author's verdict on something seen. The review found no evidence against one; 28 open items of the interface are Phase 7's to close. |
| Glossary | One glossary for the workbench's own terms. | None better found | – | – | – | keep | C's records include one. |

### What these lists lack

| ID | Today, in 15 words | Best alternative | A | B | C | Verdict | Reason |
|---|---|---|---|---|---|---|---|
| add-10 | Validation is planned on ClyA alone. | A second pore, with published conductances, in validation (B) | – | ≠ | – | add later: Phase 12 | The pipeline claims no rule specific to one pore (FR-37), and B notes that the protein permittivity, the exclusion offset and the isolevel were set on ClyA. One other pore tests the claim. |
| add-11 | The process has no target for what it asks of the author. | A target for the author's touches a package, read from the measured usage (C) | – | – | ≠ | add now | §8.3 measures about eight touches a package and nothing says how many are wanted. With a number, the change of §8.4.4 (1) can be seen to work or not. |

A rule of §8.4 is named by its subsection and its place in it: §8.4.4 (8) is the eighth bullet of §8.4.4. In the last
table `≠` marks the designer who named the lack.

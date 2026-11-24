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
  the requirements, the constraints and the exclusions the marks are the designers' own tables, in
  [design A](design-a.md), [design B](design-b.md) and [design C](design-c.md). The designers did not judge the
  dependencies, the releases and the rulings row by row, so those marks are read from each design's text.
- **Verdict** is the main session's: keep, change now (in Phase 6), change later (in the phase named), drop or add.
  A phase's number is today's, from §2.7.
- **Reason** names the evidence. A number without a source here is from [the evidence](evidence.md). The reason behind
  a ruling or a knowledge note counts as evidence and not as authority (`wp6.04`'s D4).

A verdict is a proposal. Nothing changes until the author has ruled on the report.

## The requirements, the releases and the rulings

The 141 rows of this part hold 109 verdicts of keep, 13 of change now, 9 of change later, one of drop, 7 of add and 2
lacks that are not added. A keep means that a start-over would choose the same, unless its reason says otherwise.

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
| FR-10 | Graded triangular mesh that resolves the wall's Debye length; aborts on a quality gate. | Size from the correction's own length (A); refinement towards the quantity (B) | ≠ | ≠ | = | keep | The size rule is a judgement nobody has measured. The refinement ladder of FR-29's row measures it. |
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
| FR-24 | Sweeps any case field as independent jobs, warm-started from a converged neighbour. | The unit of work is a continuation chain (B; A and C design so) | = | ≠ | = | keep | All three plan chains. 85 to 92 % of a timed solve is in the six rungs that carry the corrections; whether a warm start skips them is §5's row. |
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
number for the solve's time QR-07's, and room for 3D CON-01's. Three lacks are of the next part: a second pore in
validation, a self-check that computes numbers on the user's machine, and a measurable target for the process.

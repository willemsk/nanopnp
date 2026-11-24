# Ground-up review: blind design A

The design of blind designer A, on Fable 5.2, who had no lead user. It read the purpose pack alone, and its text
stands below as it returned it, unedited; `<pack>` in a path of its closing lines is the folder [How it was
made](method.md) describes. Its judgement of today's requirements, after the unblinding, follows the design. An
appendix of [the ground-up review](../ground-up-review.md).

---

Basis: the pack texts only; no other file and no project page was opened. Library facts were checked on 24 November 2026 against the public package index and the projects' own documentation.

## 1 What the program should become, for whom, its capabilities in rank order, and what it leaves out

**What.** A modelling and design platform for charged, confined electrolytes at the boundary between molecular and continuum descriptions, with biological nanopores as the case it must do well. In three years it is the place where a new closure, term or equation set is written, checked against analytic limits and compared with the published model on the same pore within days; a code another group extends unaided; and a tool a laboratory installs with one command.

**For whom, in order.** The author (method papers, then devices beyond pores); other groups' method developers; experimental laboratories; pore designers. Developer power beats laboratory ease; extensibility beats reproducing published digits; the graphical interface is a goal of its own, not a wrapper.

**Capabilities, ranked.**

1. A model kernel: the Poisson, Nernst–Planck, Navier–Stokes family and its equilibrium relatives as named, composable terms and closures, swappable and run side by side.
2. A verification ledger: every term tied to an analytic limiting case, shown openly.
3. Structure to prediction, axisymmetric: PDB or mmCIF (optionally a trajectory) to geometry, fixed charge, conductance, I–V curve, transport numbers, rectification, electro-osmotic flow, analyte force and PMF. Idealised and solid-state shapes take the same route.
4. Rebuildable runs and studies: salt × bias × variant × model sweeps on a laptop or a cluster, collected into one dataset.
5. The workbench: a laboratory's path from structure to I–V curve and field map.
6. Full 3D: symmetry wedges, non-axisymmetric pores, off-axis analytes.
7. The molecular link, both ways: MD ensembles and MD-derived closures in; potential, concentration and flow maps out, for MD and Brownian dynamics.
8. Inverse design: per-residue sensitivities, then proposed mutations for a stated target.
9. Devices beyond pores: solid regions with their own carriers and electrode conditions.

Items 1 to 5 are the base and come first, as the author ruled; 6 to 9 are prepared for from the first day and built after.

**Left out.** Time-dependent solves (room is left); an MD or BD engine of its own; ion-correlation or quantum physics except as closures; structure prediction; simulated current traces with noise and kinetics; digit-exact reproduction of the paper; any commercial code at run time; a hosted service; any generality that no nanopore case exercises.

## 2 The architecture: components, data, boundaries

Three artefacts carry everything, and each is the only way across its boundary: the **Case** (declarative input), the **Problem** (in memory: domain, mesh, model, data) and the **Run record** (output).

| Component | Responsibility | Knows nothing of |
|---|---|---|
| scene | structure and trajectory to atoms, charges, radii, frames; mutations | equations |
| geometry | scene or idealised shape to an implicit description (signed distance per material, solid fraction, wall distance), tagged regions, then a mesh | the model |
| model | fields, regions, terms, closures, conditions, observables | where the geometry came from |
| solve | engine adapter, continuation strategy, linear-solver interface | case files |
| observe | quantities of interest as functionals; adjoints; error indicators | interfaces |
| store | content-addressed run records | physics |
| study | expanding a parameter product, executors, collection | physics |
| service | the single application layer: validate, plan, run, query | presentation |
| interfaces | Python API, command line, local HTTP API, workbench, notebook widgets | each other |

The decisions that shape it:

- **A model is data plus small functions.** A term is a function returning one weak-form contribution, written against a facade (gradient, divergence, measure, normal) that a coordinate object supplies. Axisymmetric and Cartesian 3D are two coordinate objects, so one term text serves both. A closure is a named object (property = reference value × concentration factor × wall factor) with its coefficient file; "off" is the identity closure, so the classical model is the same code path, as the physics requires. A variant is a diff of terms and closures against a parent model, which makes side-by-side comparison a one-line study axis.
- **Extension without forking.** Models, closures, geometry producers, charge sources and observables register through package entry points; another group ships its own package.
- **The kernel is not about pores.** It takes regions, fields and coefficient fields. A semiconductor region with electrons and holes is two more species on a solid region; that is the room left for devices.
- **Geometry is implicit first.** The level set built from the atomic density is the canonical geometry in any dimension. Contours, meshes, the solid fraction and the wall distance all derive from it. That removes hand-cleaning of vertices and makes 3D a change of consumer, not of pipeline.
- **One adjoint, three uses.** The transposed Jacobian at the converged state gives goal-oriented error estimates, per-residue sensitivities and, later, design gradients.
- **Interfaces are clients.** The workbench holds no state that the case file and the run store do not hold. Engine types appear only inside model terms and solve.
- **The workbench has three workspaces.** Setup (structure, geometry, charge, each with a visual check), Run (queue, live convergence) and Results (curves, maps, runs and models side by side). Validated defaults come first, the full case tree is one click away, and every deviation is badged.

Flow: Case, scene, geometry, (mesh, charge, solid fraction, wall distance), Problem, solve, observe, Run record, study dataset.

## 3 The technologies, each with its runner-up and the reason

| Concern | Choice | Runner-up | Reason |
|---|---|---|---|
| Language | Python 3.11 to 3.14; TypeScript for the workbench | Julia with Gridap | Structure tools and the laboratory install live in Python. |
| Simulation engine | NGSolve | FEniCSx | It is the one symbolic-form engine with automatic linearisation that installs from binary wheels on Windows, macOS and x86 Linux for Python 3.10 to 3.14 (release of October 2026, LGPL-2.1; no ARM Linux wheel). It has spaces restricted to subdomains, 2D and 3D, hybrid and H(div) elements and its own mesher. FEniCSx has the better form language and PETSc scaling but publishes no wheels; its Windows build is conda-only, called beta, lacks PETSc and needs Visual Studio for run-time compilation, which breaks the no-compiler constraint. Third: scikit-fem, the simplest install, but hand-written Jacobians defeat rapid new physics. |
| Discretisation | Continuous Galerkin, order 2 for potential and concentrations; Taylor–Hood 2/1 with a grad-div term for flow; no artificial diffusion by default | Hybridised discontinuous Galerkin with H(div) velocity | The simplest forms for a developer to write and read, and the best preconditioner support in 3D. The hybrid method buys local conservation and pressure robustness at higher cost; it stays an option the ledger can adjudicate. |
| Geometry and mesh, 2D | Level set on a grid (NumPy, SciPy, scikit-image contours), automatic contour simplification, Netgen through its OpenCascade kernel | Gmsh | Netgen ships in the engine wheel and is LGPL. Gmsh has richer size fields and wheels for all three systems but is GPL, so it is an optional plug-in. |
| Geometry and mesh, 3D | Isosurface of the level set, robust tetrahedralisation with fTetWild (pytetwild wheels for all three systems, MPL-2), regions classified by level-set sign | Unfitted elements (ngsxfem) on a background mesh | Body-fitted meshes keep no-flux and no-slip walls exact. The unfitted route avoids the fragile step and is the fallback. |
| Linear solution | 2D: sparse direct factorisation of the coupled Jacobian behind a solver interface (the engine-bundled solver always; PARDISO or MUMPS when present). 3D: GMRES with block preconditioning (multigrid on potential and concentrations, a pressure Schur complement), under MPI | Block-iterative everywhere | Direct is robust for the 2D problem of about a million unknowns on a laptop; 3D exceeds the direct ceiling. Which direct solvers each wheel bundles must be measured. |
| Nonlinear solution | Fully coupled Newton with the exact Jacobian from symbolic differentiation, an admissibility line search, a staged start and bias continuation | Gummel (segregated) iteration | Newton holds where coupling is strong, as in overlapping double layers. Gummel is kept as an initialiser. |
| Structure | Gemmi (reading, assemblies, symmetry); MDAnalysis (trajectories); PDBFixer with OpenMM as an optional extra (missing atoms, loops, mutations, relaxation) | Biotite; MDTraj | Fast, permissive, wheeled. PDBFixer is pure Python but needs OpenMM, whose wheels for the newest Python I could not confirm; hence optional. |
| Charge | PROPKA and PDB2PQR behind a charge-source interface that also accepts a PQR file or an MD topology | OpenMM force-field assignment | Pure Python and the route the physics describes. The OpenMM route makes continuum and MD charges identical and becomes preferred when the molecular link is built. |
| Front end and visualisation | A local web application: a Python ASGI server with a JSON and WebSocket API; a prebuilt React and TypeScript single-page app shipped as static files in the wheel; Mol* for structures, vtk.js for meshes and fields, Vega-Lite for charts; the same views wrapped with anywidget for notebooks | trame (Python-defined interface over VTK) | Full control of design and interaction, which the author names as a goal; no Node at install; one laboratory machine can serve several laptops. trame costs far less code but caps the design. |
| Storage and formats | Case: YAML validated by a versioned schema generated from typed models. Mesh and fields: one HDF5 file per run in the VTKHDF layout, plus raw coefficient vectors for exact warm starts. Quantities: Parquet long tables | TOML; Zarr; NetCDF | YAML reads well for deep trees. HDF5 opens in ParaView and has wheels everywhere. Parquet takes ragged studies that labelled grids cannot. |
| Record of a run | A JSON manifest: the fully resolved case, model identity (terms, closures, coefficient hashes), input hashes, package lock, mesh hash, solver history, every gate result, deviations from validated defaults, verification status of each term | RO-Crate packaging | Small, diffable, sufficient. RO-Crate can wrap it later. |
| Distribution | Wheels on the package index. Laboratory: one uv command that fetches Python and the program and opens the workbench. Scientist: tool install and the command line. Developer: clone, locked environment, editable install. Cluster: the same wheels, plus a container image with MPI and PETSc for 3D | conda or pixi; frozen desktop installers | Wheels are the one route with no compiler on all three systems. Installers come when laboratories ask. |
| Many runs | A study planner producing content-addressed points grouped into continuation chains; executors for a local process pool and for scheduler job arrays (Slurm first) from generated scripts; idempotent, resumable collection | Snakemake; Dask | Points are independent and chains are the unit of work. A workflow engine adds a second language for little gain. |

Own code is Apache-2.0; every mandatory dependency is permissive, LGPL or MPL.

## 4 The numerical method and how its results are trusted

**Method.**

- Unknowns are scaled (nm, thermal voltage, 1 M, a reference diffusivity). The potential lives on all regions; concentrations, velocity and pressure on the fluid only.
- Fixed charge is the analytic kernel sum of the physics, deposited element by element with each atom renormalised, so conservation holds by construction. Wall distance is read from the level set with the membrane excluded.
- Mesh size follows the physics, not a preset: at the pore wall at most a third of the shortest closure length (about 0.05 nm for the published wall factor), at most a quarter of the Debye length in the double layer, graded to the reservoir. In 3D the wall needs anisotropic layers.
- Start: Poisson, then Nernst–Planck at zero bias with the fixed charge ramped, then flow, then bias continuation with a secant predictor and adaptive steps. Sweeps warm-start from neighbours.
- Newton uses the exact Jacobian, closures and clamps included. The line search rejects any step with a negative concentration or a packing fraction at or above one, and a failure names the coordinate.
- Stabilisation is off by default because cell Péclet numbers are below one at the resolution the closures demand. A per-run gate computes them; streamline diffusion is a named, recorded deviation for coarse 3D meshes.
- The electric body force is largely a gradient balanced by pressure, and Taylor–Hood is not pressure-robust. The charged-cylinder flow case in the ledger is the gate; if it fails at practical resolution, the H(div) option becomes the default.
- Currents, flow rates and forces are evaluated as weighted volume functionals of the residual (the reaction route), never as cross-section integrals of a pointwise flux. They are conservative between electrodes and converge faster than the pointwise flux. A second, independent route cross-checks each.

**Trust, in five tiers.**

1. Closures: unit tests on tabulated values, caps and the errata, each erratum a test.
2. Manufactured solutions per operator and coupled, in both coordinate systems, gated on convergence rate.
3. The limits ledger: each term maps to at least one analytic case that fails if the term is wrong. Debye–Hückel and Gouy–Chapman profiles and the Grahame relation; the steric saturated layer; electro-osmotic flow in a charged cylinder with its Bessel overlap factor and the Helmholtz–Smoluchowski limit; Poiseuille flow and sphere drag in a tube; pore plus access resistance; reversal potential under Nernst–Einstein; equilibrium with a constant ratio of diffusivity to mobility; Onsager reciprocity between electro-osmosis and streaming current in the classical model. The ledger is generated from the tests and published with each release.
4. Cross-code: Poisson and Poisson–Boltzmann against APBS; stored outputs of the commercial reference as data only.
5. Experiment: the published ClyA curves as tolerance bands on magnitude and trend, not digits.

Every run also carries its own evidence: charge conservation legs, current balance between electrodes, agreement of the two flux routes, Péclet and clamp reports and, on request, a three-mesh Richardson error bar per quantity; later the adjoint estimate replaces it. A term or closure with no ledger entry runs, but is marked unverified in the record and in the workbench: a badge, not a gate, because the author ranks extensibility first.

## 5 How it is developed: process, tests, records

**Order.** (0) Two weeks of spikes that settle section 6 by measurement. (1) Idealised geometries, the classical model, the ledger green. (2) Closures, the extended model, model comparison. (3) Structure to geometry to charge; ClyA validation. (4) Studies on a cluster; workbench first release. (5) Analyte force and PMF. Then 3D, the molecular link and the adjoint with design. Workbench design starts in step 1 as clickable prototypes over recorded runs, since the run record is its only contract.

**Process.** The form is kept and its cost cut. Three living documents only: the normative physics, a decision log of half-page entries, and the generated ledger. A work package is one issue with executable acceptance tests. One command starts it, and one agent session carries it through plan, implementation, review and merge without a further start from the author. Agents settle anything derivable from the physics, the decision log or the author interview; questions of direction are batched into one weekly digest of yes-or-no rulings, each with a default that applies if unanswered.

**Tests.** A fast suite under ten minutes on a laptop (tiers 1 and 2, coarse tier 3). Continuous integration on the three systems at the oldest and newest Python, installing wheels only, which proves the no-compiler promise on every change. Nightly: full ledger, convergence studies, a small study through the array executor, workbench end-to-end tests in a headless browser with screenshot comparison. Per release: ClyA validation and a clean-machine install test on each system.

**Records.** The run manifest; the ledger; the decision log; a changelog; a performance history of the reference problem. Nothing else is kept by hand.

## 6 The three choices you are least sure of

1. **The engine.** NGSolve wins on installation; FEniCSx wins on form language, adjoint tooling and large 3D solves. I have not measured whether wheel-only NGSolve solves a coupled 3D wedge of several million unknowns in acceptable time, nor which direct solvers each wheel carries, nor how exposed a sole maintainer is to its small core team. The mitigation is that terms sit behind a facade and the ledger is engine-independent, so a port is bounded.
2. **3D geometry and the wall.** The wall closures demand about 0.05 nm resolution normal to the wall. Whether automatic anisotropic layers on a protein isosurface are robust, or whether an unfitted or diffuse-interface treatment must replace body-fitted meshing, is unknown until tried, and it decides whether 3D runs on a workstation or only on a cluster.
3. **The workbench stack.** A custom single-page app gives the design quality the author wants but is a second codebase for one maintainer with no interface experience, carried by agents. trame or a notebook-first interface would cost a fraction and might serve laboratories well enough. I chose the app because the author made the interface a goal; I would revisit it if the first release costs more than a quarter of total effort.

### Critical Files for Implementation

A from-nothing design has no source files yet; the plan rests on these inputs:

- <pack>/04-physics.md
- <pack>/author.md
- <pack>/purpose.md
- <pack>/b-comsol-settings.md

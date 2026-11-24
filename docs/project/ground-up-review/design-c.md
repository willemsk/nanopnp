# Ground-up review: blind design C

The design of blind designer C, on Opus 5.5, who designed first for the method developer. It read the purpose pack
alone, and its text stands below as it returned it, unedited; `<pack>` in a path of its closing lines is the folder
[How it was made](method.md) describes. Its judgement of today's requirements, after the unblinding, follows the
design. An appendix of [the ground-up review](../ground-up-review.md).

---

## 1 What the program should become

**What it becomes, and for whom.** nanopnp becomes an open workbench for electrokinetic transport through molecular pores. Its first job is to let a method developer write a new piece of physics, test it against an analytic limit, and run it beside the published ePNP-NS model on the same pore and mesh within a day. The users come in the author's order:
1. The author's own method papers, then devices beyond pores.
2. Method developers in other groups.
3. Experimental laboratories.
4. Pore designers.

The design follows the rulings "extensible over exact" and "developer over ease". Its baseline is the physics of `04-physics.md`, proven term by term against analytic limiting cases. It is open throughout, and simple cases run on a laptop without a compiler.

**Capabilities, in rank order:**
1. **Composable physics.** A model is a set of fields, terms, property models and boundary conditions. Correction functions, steric fluxes, body forces and whole equations are named, swappable parts. An "off" setting is itself a named model, not a code branch, so PNP-NS is ePNP-NS with neutral parts. Several models solve side by side on one pore, and their differences come back as a dataset.
2. **A baseline the reader can check.** Every term is checked by manufactured solutions, and the whole model by analytic limits (§4). The result is published as a generated verification report with each release.
3. **Structure to mesh, unattended.** The pipeline goes PDB or mmCIF (optionally a trajectory) → protonation and charges → closed-form azimuthal charge deposition → density contour → conditioned profile → membrane and reservoirs → mesh. It also accepts idealised pores (cylinder, cone, given σ_s) and solid-state geometries.
4. **Quantities of interest with error bars.** It computes I, G, per-species G_i, t₊, rectification, the EOF rate Q, the Maxwell plus hydrodynamic force on an analyte, the PMF, and PB energy differences. Current comes by two independent routes, and every value carries a mesh-refinement error estimate.
5. **Studies.** Sweeps over salt × bias × variant × model, with continuation chains and warm starts, run on a laptop pool or as HPC job arrays and collect into one dataset.
6. **A record of every run.** Every result can be rebuilt from its case file plus its run record.
7. **Case files and a command line** for collaborators (P2).
8. **A browser workbench** for laboratories: load a PDB, set salt and voltage, get an I–V curve and field maps, and export a figure and a case file. Later it also serves designers: mutate a residue and see ΔG, Δt and ΔQ.
9. **Room left for later, not built now:**
   - 3D geometry: the same term code, a 3D mesh path and an iterative solver.
   - Exchange with molecular simulation: import MD ensembles and densities, export potential, flow and PMF grids for MD or BD.
   - Inverse design: adjoint sensitivities of a QoI to every atomic charge, which rank candidate mutations with one extra linear solve.

**What it leaves out:**
- Time-dependent solves. The EDL relaxes in nanoseconds, against microsecond dwell times, so steady state is justified.
- Running MD or BD itself; it exchanges data with them instead.
- Charge regulation coupled to the solve; protonation stays a preprocessing step.
- An explicit Stern layer.
- Distributed-memory parallel solves, until 3D needs them.
- A hosted multi-user server.
- A CAD-style geometry editor.
- Matching COMSOL's numbers to the last digit. COMSOL is a comparison oracle, never a dependency.
- Being a general multiphysics framework: the abstractions stop at electrolyte transport near charged dielectric bodies.

## 2 The architecture

The program is built in layers, and each layer depends only on the layers below it. Only one layer knows the finite-element engine.

**Layers, from the bottom up:**
1. **`units` and `constants`:** physical constants and a thin layer for quantities with units, used at the input and output edges only.
2. **`structure`:** reading, cleaning, mutating and protonating structures, and handling ensembles. Its output is an atom table (x, y, z, q, R, residue, frame weight). It knows nothing of meshes.
3. **`charge`:** turns an atom table into a charge field, using the closed-form azimuthally averaged Gaussian kernel. It also builds the dielectric solid fraction χ and runs the conservation and per-plane checks. Its output is engine-free: a callable plus per-atom patches.
4. **`geometry`:** the pore description. Three kinds exist:
   - the axisymmetric profile, a closed polygon in (r, z);
   - later, a 3D solid;
   - a parametric pore.
   Membrane, reservoirs and analyte are separate named parts, and the builders compose them. Boundary and region names are the contract with the layers above.
5. **`mesh`:** a size-field policy turns the geometry into a mesh, with named regions and boundaries.
6. **`physics`:** the core of P1's work.
   - *Fields:* φ, c_i, u, p, and others.
   - *Property models:* D, μ, η, ϱ, ε as registered functions of the drivers ⟨c⟩ and d.
   - *Terms:* Poisson, Nernst–Planck flux pieces, steric flux, body forces, the dielectric-gradient pair, and so on. Each term contributes a symbolic weak form and declares the fields it couples, its switches and its manufactured-solution source.
   - *Models:* named compositions of terms: epnp-ns, pnp-ns, pnp, pb, pb-linear, poisson. A model is data: a list of terms and property models, validated for consistency. For example, the dielectric-gradient pair is all or nothing, and a switch with nothing to switch is refused.
7. **`discretise` and `solve`:** finite-element spaces, assembly of the composed form, Newton with damping and continuation, a fallback decoupled iteration, and a linear-solver adapter. **This is the only engine-specific layer** besides the term bodies.
8. **`qoi`:** reaction-flux current, indicator-function current, flow rate, stress-tensor forces, PMF integration, energies and error estimates. Each QoI states its route.
9. **`study`:** a sweep is turned into a task graph with continuation edges and handed to an executor (local, SLURM array).
10. **`record` and `store`:** case schema, content-addressed cache of intermediate products, run records, datasets.
11. **Interfaces:** a Python API first; a CLI as a thin wrapper over the API; the workbench as a client of a local job service that calls the same API. The workbench holds no physics.

**Extension points.** Property models, terms, models, geometry builders, QoIs and executors register through Python entry points. That lets another group publish a correction model or a pore as its own package, without forking and without the author.

**Data.** Each object below is immutable and hashed, so the cache can reuse a charge field or mesh across a 3,675-point sweep:
- *Case:* declarative YAML, versioned schema.
- *AtomTable.*
- *ChargeField:* kernel patches, Q_net and conservation legs.
- *Geometry:* named parts and a profile.
- *Mesh.*
- *Solution:* fields, model, mesh hash, solver statistics.
- *QoISet:* values, routes and error estimates.
- *RunRecord.*

**Boundaries:**
- Upstream layers (structure, charge, geometry, case, store) exchange NumPy arrays and files, so they survive an engine change.
- Physics terms are written in the engine's symbolic language. A neutral symbolic layer above the engine was rejected, because it would double the cost of every new term for the method developer.

## 3 The technologies

**Simulation engine and discretisation: NGSolve (with Netgen).**
- *Why:*
  - Weak forms are symbolic Python expressions, so a new correction or equation is a few lines.
  - Newton Jacobians come from automatic linearisation of the symbolic forms.
  - Elements are high-order, and H(div), HDG and Taylor–Hood spaces are available for the later 3D and flux-conservative work.
  - It is LGPL.
  - PyPI wheels exist for Windows, macOS and Linux x86-64 on CPython 3.10–3.14 (checked today), and expressions are evaluated without a runtime C compiler. That is what P3's one-command, no-compiler install needs.
- *Runner-up: FEniCSx/DOLFINx.* It has a larger developer community, the UFL form language and first-class PETSc. It lost because its forms are JIT-compiled, which needs a C compiler at run time. Its Windows builds are conda-only and come without PETSc, so laptops would get a second-class engine.
- *Discretisation:* conforming Lagrange P2 for φ and c_i, and Taylor–Hood P2/P1 for (u, p) in place of the reference's stabilised P1/P1. All forms are r-weighted on the axisymmetric domain. Section 4 gives the reasons.

**Geometry and mesh: Netgen's OCC kernel and 2D/3D mesher, behind the `mesh` layer.**
- *Why:*
  - It is the same toolchain as the engine, so there is no format conversion and region names survive.
  - Curved boundaries and geometry-aware refinement keep adaptive and uniform refinement studies on the true profile.
  - The same OCC kernel builds 3D solids later.
- *Contour extraction and conditioning:* scikit-image marching squares on the radially averaged density, then Shapely to simplify, close, offset the ion-exclusion shell, and remove the overlapping vertices that were once removed by hand.
- *Runner-up: Gmsh.* Its distance and threshold size fields are richer, and it also has wheels on all three systems. Its meshes then need importing, and refinement loses the geometry.

**Linear and nonlinear solution.**
- *Linear:* a sparse direct factorisation behind an adapter.
  - Use the engine's built-in direct solver where the wheel provides one. Otherwise export to CSR and use PARDISO (via pypardiso, on x86) or SciPy's SuperLU.
  - The reference problem, about 10⁵ cells and five fields, factorises on a laptop.
  - For 3D, use the same adapter with PETSc (MUMPS, field-split preconditioners), installed on clusters from conda-forge.
  - *Runner-up:* PETSc everywhere. Rejected because it has no Windows support.
- *Nonlinear:* nanopnp's own Newton method, fully coupled.
  - Damping comes from backtracking on the residual norm.
  - Continuation runs in bias and concentration, with an adaptive step.
  - The packing-fraction assertion (Φ < 1) and the clamp logging run at each iterate.
  - For hard starts, a decoupled Gummel-type iteration (Poisson, then each NP, then Stokes) produces the initial guess.
  - Newton is about 200 lines here, and owning it gives P1 full introspection: residual history per field and per region.
  - *Runner-up:* PETSc SNES, rejected for the same platform reason.

**Structure and charge preparation.**
- *Reading:* gemmi for PDB and mmCIF (fast, wheels everywhere); MDAnalysis for trajectories and frame alignment.
- *Charges:* PDB2PQR with PROPKA for protonation and partial charges; both are pure Python.
- *Loop filling and mutation:* PDBFixer on OpenMM, an optional extra.
- *Deposition:* NumPy with Numba kernels evaluating the closed form `exp(·)·Ĩ₀` (SciPy `i0e`).
  - The kernel is evaluated at element quadrature points inside a 6w patch per atom, and each atom is renormalised to q_i e on the mesh. This deposits straight onto the solve's own space instead of through a lattice, so conservation holds by construction at whatever order the solve assembles.
- *Runner-ups:* Biopython for reading (slower); a lattice deposition, which is 10¹⁰–10¹¹ kernel evaluations for a 50-frame ensemble.

**Front end and visualisation.**
- *Python API:* primary. Typed, documented, notebook-friendly.
- *CLI:* Typer.
- *Workbench:* trame (Kitware). It is pure Python with a Vue/Vuetify component layer, and VTK renders fields in the browser, which carries straight over to 3D later. Mol* is embedded for the structure view, and Plotly for I–V and sweep plots.
- *Design work:* the workbench is designed as a product (§5), with mockups agreed before any code.
- *Runner-up:* a FastAPI service with a TypeScript single-page app (React with vtk.js). It gives more design freedom, but a second language is a burden on a single maintainer.
- *Field post-processing for P1:* PyVista and ParaView files.

**Storage, file formats and the record of a run.**
- *Case:* YAML validated by a Pydantic schema with an explicit version and migration functions. Comments survive, and the schema itself produces the documentation and the workbench forms.
- *Fields:* VTU for viewing, plus a native engine snapshot for warm starts.
- *Sweeps:* an xarray dataset in Zarr, with dimensions salt × bias × variant × model × QoI-route and error-estimate variables. Separate tasks can write their own chunks at the same time.
- *Run record:* JSON beside each run, holding:
  - the input and case hashes and the hash of every cached intermediate;
  - the code version, the package versions and the platform;
  - deviations from the validated defaults;
  - solver statistics, clamp activations, gate results, and the QoI routes and their agreement.
- *Runner-ups:* HDF5/NetCDF for datasets, a stable single-writer format with weaker concurrent writes; RO-Crate for records, which could later wrap the JSON for publication.

**Distribution to the three kinds of user.**
- *P1 and P2:* the package from PyPI, developed with uv, with locked environments.
- *P3:* one documented command that installs uv and then runs `uvx nanopnp workbench`. uv fetches its own Python, so no Python or compiler needs to be present beforehand. This only works because every hard dependency ships wheels.
- *Clusters:* an Apptainer image built in CI.
- *Runner-up:* conda-forge with pixi. It is stronger for PETSc and MPI, and it is the cluster path for 3D, but heavier for a laboratory laptop.

**Many runs at once.**
- The `study` layer turns a sweep into tasks. Continuation edges chain the bias points within each salt column, and the columns run independently.
- *Local executor:* a process pool.
- *HPC:* SLURM job arrays through submitit, one array element per column chain.
- *Cache:* shared mesh and charge artefacts sit in a content-addressed cache on the shared file system. Results land in Zarr chunks, and a collect step checks completeness against the task graph.
- *Runner-up:* Snakemake. It is mature, but its file-centric rules express warm-start chains and in-memory reuse awkwardly, and it adds a second language.

## 4 The numerical method and how its results are trusted

**Formulation.**
- Steady, fully coupled ePNP-NS in r-weighted axisymmetric weak form.
- Axis conditions are natural, except for the essential u_r = 0.
- The wall distance d is solved once per mesh from an eikonal or screened-Poisson problem, with the clamp max(d̄, 0) where it is read.
- Concentrations are clamped where the property models read them.
- Primitive variables (φ, c_i, u, p) are the default, because they match the stated model and the reference's discretisation.
- A log-concentration formulation is a registered alternative. It keeps concentrations positive and often makes Newton more robust at low salt and high bias. The two are compared through the same tests, so the choice can rest on evidence.
- No streamline stabilisation by default. The cell Péclet number of migration and advection at pore-scale mesh sizes is below 1, by a rough estimate. Stabilisation is a registered option, and its effect on the QoIs is reported whenever it is on.
- Taylor–Hood flow avoids pressure stabilisation entirely.

**Current and other QoIs.**
- *Current, route 1:* the variational reaction flux at the grounded boundary, i.e. the residual of the NP equations tested with the boundary's basis functions.
- *Current, route 2:* a volume indicator-function integral, a smooth ψ going from 0 to 1 across the pore.
- The two routes must agree to a set tolerance. A cross-section integral of the continuous-Galerkin flux is never used.
- *Forces:* volume (domain) forms of the Maxwell and hydrodynamic stress, which are more accurate than surface integrals for the same reason.

**Error control.**
- Every reported QoI comes from a refinement ladder of at least three meshes, using geometry-aware refinement.
- The report gives the observed order, a Richardson-extrapolated value and an error bar.
- Later, dual-weighted-residual estimates from adjoint solves on the QoI drive adaptive refinement. That adjoint machinery is the same one inverse design needs.

**Trust: a ladder, each rung automated.**
1. **Property conformance.** Correction functions reproduce the stated self-consistency values (f^w_D(0) = 0.06, η⁰/η^w(0) = 0.379, the caps, the erratum forms), and the D/μ drift profile is checked rather than Nernst–Einstein.
2. **Manufactured solutions per term and per coupled model.**
   - Symbolic sources come from SymPy in axisymmetric coordinates.
   - The expected order is P2 → 3 in L², P1 pressure → 2.
   - This includes the axis, the steric sum over all species, and variable-density flow.
3. **Analytic limits of the baseline:**
   - Debye–Hückel and Gouy–Chapman screening at a planar wall and a cylinder, and the nonlinear PB Grahame relation.
   - Born energy and a charged sphere in a dielectric, for Poisson with jumps.
   - Ohmic conductance of a cylinder plus the 1/(2σd) access terms.
   - Hagen–Poiseuille flow, and Sampson flow through an orifice.
   - The charged-cylinder EOF rate with its I₂/I₁ overlap factor, and the Smoluchowski slip limit.
   - Zero-current PNP reducing to the Boltzmann distribution when the corrections are off.
   - Stokes drag 6πηRu, and qE on a sphere in a uniform field.
   - Charge conservation and the per-plane cumulative checks against the source atoms.
4. **Cross-code checks:** APBS for the poisson and pb models on the same structure; the reference COMSOL figures as a differential oracle, with tolerance bands rather than equality.
5. **Validation:** the published ClyA I–V, selectivity and EOF figures regenerated by one command (S4), and experimental I–V curves where available.

Every rung runs in CI at a cost suited to its tier (§5). The verification report is a build artefact, so "it matches the limits" can be pointed at.

## 5 How it is developed

**Process.** Keep the form the author approved, but cut the number of sessions he must start.
- **One ordered backlog of work packages.** Each states its purpose, its physics or behaviour, and the verification case that proves it. The verification catalogue is the backbone of the specification: a requirement without a test is a wish.
- **One command per package.** An agent plans, implements, tests, reviews and opens the pull request in a single run. It stops only for a ruling on direction or on a result that fails a gate.
- **Batched rulings.** The author decides at most once per package, from a one-page summary.
- **Decisions as short architecture records**, one per choice, with the alternatives rejected.
- **Order of the work: prove the physics first.**
  1. Poisson and PB on idealised geometry against analytic results.
  2. PNP against the conductance and Boltzmann limits.
  3. Flow and EOF against the cylinder results.
  4. The corrections, switched in one at a time.
  5. The ClyA pipeline.
  6. Studies and the CLI.
  7. The workbench, whose design starts early as mockups and is built once the API is stable.
- **The workbench is designed as a product.** Short rounds of personas, tasks and clickable mockups come before code, because the author names GUI design as a goal of its own.

**Tests, in tiers.**
- *Every commit:* unit and property tests (Hypothesis on case validation and property models), manufactured-solution tests on coarse meshes, and the cheap analytic limits. The matrix is three operating systems by the supported Python versions.
- *Nightly:* the full limit suite with convergence orders, the ClyA figure regeneration with tolerance bands, the APBS comparison, and performance benchmarks.
- *Release:* the verification report, a cluster smoke test of a small job array, and an install test of the one-command workbench on clean Windows and macOS machines.
- *Plugin contract:* every registered term and property model must ship its own manufactured-solution source and pass the same harness. That rule is what lets others extend the code without breaking trust.

**Records.**
- Run records for every computed result.
- The architecture decision records.
- A changelog.
- A glossary.
- The generated verification report.
- An errata table for the source literature, each row with its arithmetic.

Nothing else is required reading.

## 6 The three choices I am least sure of

1. **NGSolve over FEniCSx.** The install argument is solid. But the FEniCSx community is larger among method developers, and its PETSc integration suits the 3D and distributed future better. The direct solvers bundled in NGSolve's pip wheels are also unclear: forum reports disagree on whether PARDISO or UMFPACK is present. Confining the engine to the `discretise`, `solve` and term layers limits the cost of reversing this choice, but does not remove it.
2. **Unstabilised P2 Galerkin in primitive variables as the default.** It is faithful and simple. But robustness at 5 M, at ±200 mV and at low salt in a strongly charged pore is untested. The log-concentration form or an exponentially fitted (Scharfetter–Gummel-like) scheme may prove necessary, and the default may have to change after the first ClyA sweeps.
3. **trame for the workbench.** It keeps one language and gives VTK-quality fields that carry over to 3D. But the author wants a clean, attractive design, and a TypeScript single-page app may achieve that better. The workbench's dependence on the job service keeps a later switch possible.

### Critical Files for Implementation
These are the pack's inputs; the program itself does not exist yet.
- <pack>/04-physics.md
- <pack>/purpose.md
- <pack>/author.md
- <pack>/b-comsol-settings.md
- <pack>/02-electrokinetics-background/09-quantities-the-software-must-compute.md

---

## After the unblinding

Designer C then read §2.6 and §2.7 of `specification/02-product-overview.md`, `specification/03-requirements.md` and
`specification/05-software-design/06-architecture-decisions.md`, and nothing else, and returned the judgement below. It
is unedited, and the design above was not revised.

I judged each identifier against the design I already handed back, without revising that design. I read only the three files named. Most rows are keep. The changes cluster in four places:
- **Composable physics comes too late.** FR-40, FR-20, ADR-005 and N1 put it at v0.9 and fence it, while my design ranks it first.
- **Error bars on results come too late.** FR-29 is post-1.0, but trust in a reported number needs them.
- **Some requirements are written as designs.** FR-30(b), FR-31, FR-33 and IF-09 fix screens and drawings, which change faster than requirements should.
- **N1 contradicts the author.** He wants to change the equations.

## IF

| ID | Verdict | Reason |
|---|---|---|
| IF-01 | keep | The scriptable, introspectable API is P1's first need. |
| IF-02 | keep | P2's route; the exit-code contract makes job arrays reliable. |
| IF-03 | change | Require a versioned schema with migrations, rather than naming one version string in a requirement. |
| IF-04 | keep | Covers the formats MD users actually have. |
| IF-05 | change | Make OpenDX/CCP4 an optional export; it is interchange, not core. |
| IF-06 | keep | A lossless archival mesh with region tags is right. |
| IF-07 | change | Keep the exact P2 node set and the separate fluid file; let the container be any ParaView-readable format. |
| IF-08 | keep | A record with every result is the reproducibility promise. |
| IF-09 | change | Keep "thin shell over IF-01 through a network API"; move the six suites to the design document. |

## FR

| ID | Verdict | Reason |
|---|---|---|
| FR-01 | keep | Ensembles are an input the physics needs. |
| FR-02 | keep | A general way to find the axis. |
| FR-03 | change | Take the expected oligomer from the case, not a built-in list of pores. |
| FR-04 | change | State the resolution as a gate the contour must pass, not a fixed grid range. |
| FR-05 | keep | Correct symmetry reduction. |
| FR-06 | keep | Honest reporting of what the 2D reduction costs. |
| FR-07 | keep | Automates the manual step. |
| FR-08 | keep | Gates catch bad geometry before the solve. |
| FR-09 | keep | Matches the reference domain. |
| FR-10 | keep | Needed. |
| FR-11 | keep | Rightly optional. |
| FR-12 | keep | Needed. |
| FR-13 | keep | Same construction as my design. |
| FR-14 | keep | Conservation by construction, with a check that can fail. |
| FR-15 | keep | Needed. |
| FR-16 | keep | Level-1 extension. |
| FR-17 | change | "No negative concentration at any iterate" prescribes a method; require detection and recovery, or the log-variable form. |
| FR-18 | keep | Models are named compositions. |
| FR-19 | keep | Needed. |
| FR-20 | change | Make it term-level composition, not one class per whole model. |
| FR-21 | keep | Needed; the scheduled release is fine. |
| FR-22 | keep | Needed. |
| FR-23 | keep | Two current routes are central to trust. |
| FR-24 | keep | Matches my study layer. |
| FR-25 | keep | Needed. |
| FR-26 | keep | Asserted on meaning, not text: correct. |
| FR-27 | keep | Full introspection for P1. |
| FR-28 | keep | Needed. |
| FR-29 | change | Bring a refinement ladder with an error bar on each QoI before v0.13; DWR adaptivity can follow. |
| FR-30 | change | Keep (a), (c) and (d); colour-scale rules in (b) belong in the design. |
| FR-31 | change | Screen layout is design; state the tasks a user must complete instead. |
| FR-32 | keep | A plain-folder project that exports to readable files serves openness. |
| FR-33 | drop | Interaction detail; move it to the workbench design. |
| FR-34 | keep | Visible deviations are trust, shown in the interface. |
| FR-35 | keep | Refusal at the field, with a remedy. |
| FR-36 | keep | Serves the laboratory user, QR-10. |
| FR-37 | keep | General, not tied to one pore. |
| FR-38 | keep | First step of design work. |
| FR-39 | change | Split it; part (d)'s expression language is scope risk. Keep (a)–(c), (e) and (f). |
| FR-40 | change | My design ranks composable physics first; at v0.9 it comes too late. Bring it to v0.2–v0.4 and reconcile with N1. |
| FR-41 | keep | The designer's core action. |
| FR-42 | drop | A hand-drawn (r, z) sketcher costs a lot; scripted parametric geometry serves P1. |
| FR-43 | keep | A switchable variant, rightly behind a switch. |
| FR-44 | keep | Cheap and useful. |

## QR

| ID | Verdict | Reason |
|---|---|---|
| QR-01 | keep | The analytic-limit gate the author asked for. |
| QR-02 | keep | Bands with attribution, not exact digits: matches "extensible over exact". |
| QR-03 | keep | Needed. |
| QR-04 | keep | Needed. |
| QR-05 | keep | Proper validation. |
| QR-06 | keep | Job-level scaling. |
| QR-07 | keep | Needs a number in place of "acceptable". |
| QR-08 | keep | Reproducibility. |
| QR-09 | keep | Fixed from outside. |
| QR-10 | keep | Serves the laboratory user. |
| QR-11 | drop | A GUI at every release produced a Qt shell that was later discarded; build the workbench once the API is stable. |
| QR-12 | keep | Diagnostics that name gate, quantity and location. |
| QR-13 | keep | Limits the cost of changing the engine. |
| QR-14 | change | Add two things: external packages register through entry points, and every term ships its own MMS case. |
| QR-15 | keep | Needed. |
| QR-16 | keep | Accessibility is part of good design. |

## CON

| ID | Verdict | Reason |
|---|---|---|
| CON-01 | keep | Matches the author's "base first". |
| CON-02 | keep | Follows from CON-01. |
| CON-03 | keep | Follows from CON-01. |
| CON-04 | keep | Honest about the reduction. |
| CON-05 | change | Keep the documented limitation; make the driver a plug-in so ion-specific drivers can replace it. |
| CON-06 | keep | Same engine choice as mine. |
| CON-07 | keep | Fixed from outside. |
| CON-08 | change | A fact about today's wheels, not a constraint; move it to ADR-001 behind a linear-solver adapter. |
| CON-09 | keep | Open throughout. |
| CON-10 | keep | Licence hygiene. |
| CON-11 | keep | States the GPL obligation honestly; the default rests on a measurement. |
| CON-12 | keep | Licence hygiene. |
| CON-13 | keep | Fixed from outside. |
| CON-14 | keep | Supports citation. |

## N1 to N7

| ID | Verdict | Reason |
|---|---|---|
| N1 | change | The author wants to "change the equations". Allow terms the user writes within electrolyte transport, under the MMS contract; exclude only unrelated multiphysics. |
| N2 | keep | Exchange with MD, not MD itself. |
| N3 | keep | Steady state is justified by the timescale separation. |
| N4 | keep | Leave room for 3D, do not ship it. |
| N5 | keep | Follows from CON-01. |
| N6 | keep | For v1; record it as the planned molecular link. |
| N7 | keep | COMSOL is an oracle only. |

## ADR

| ID | Verdict | Reason |
|---|---|---|
| ADR-001 | keep | Same choice and reasoning as mine. Its 3D mitigation path is sound. |
| ADR-002 | keep | Adapter with a permissive default. |
| ADR-003 | keep | BSD core, honest about the GPL default. |
| ADR-004 | keep | NiceGUI was chosen on a measured spike, so I would not overturn it. Freeze the renderer: it has moved from webgui to uPlot to Plotly. |
| ADR-005 | change | Add a third level, terms composed into models, and registration from outside packages. Two levels cannot express "swap a term" or "compare models". |

## What the lists lack

- **An error estimate on every reported QoI.** The reference model had no mesh-convergence study, and FR-29 is post-1.0. A number without an error bar cannot be compared across models.
- **A verification report published with each release.** The author's success criterion is "matches the limits, shown openly". QR-01 gates the limits in CI but publishes nothing a reader can point to.
- **Model comparison as a first-class product.** Same pore and mesh, several models, the differences as a dataset. FR-39(b) only implies it.
- **Extension by others without the author.** There is no requirement for outside packages to register parts through entry points, and no plugin test contract.
- **The physics-first order of work as a requirement.** No list makes a new capability wait until the existing one holds against its analytic limits; the author ticked "proven over new" only in spirit, through the order of the work.
- **Preparation for inverse design.** There are no adjoint sensitivities of QoIs to atomic charges, though they are the cheap path to ranking mutations.
- **Preparation for the molecular link.** Nothing exports fields or PMFs for MD or BD; only imports exist.
- **Idealised and solid-state pores beyond the cylinder.** They sit in the post-1.0 backlog, against the author's "devices beyond pores".
- **A single-solve time target on a laptop.** QR-07 says "acceptable"; P3 needs a number.
- **A cluster distribution path.** There is no container or HPC install requirement.
- **Requirements on the process.** The author's one complaint, too many sessions started per package, has no measurable target.
- **Balance.** Workbench detail (FR-30 to FR-39, QR-16) outweighs physics extensibility. That inverts the author's order: developer over ease.

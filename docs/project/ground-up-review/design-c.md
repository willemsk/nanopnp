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

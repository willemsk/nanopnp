# Ground-up review: blind design B

The design of blind designer B, on Fable 5.2, who designed first for the experimental laboratory. It read the
purpose pack alone, and its text stands below as it returned it, unedited; `<pack>` in a path of its closing lines
is the folder [How it was made](method.md) describes. Its judgement of today's requirements, after the unblinding,
follows the design. An appendix of [the ground-up review](../ground-up-review.md).

---

## 1 What the program should become, for whom, its capabilities in rank order, and what it leaves out

In three years it is the tool with which an experimental nanopore group computes what its own pore should do, before or after a measurement, with no modeller in the room, and can see why the number deserves belief. The same kernel is the author's base for method papers.

I design for P3 first because a laboratory tolerates least: no failed install, no solver tuning, no unexplained refusal. A kernel that meets that standard is one a developer can build on; the reverse does not hold. This inverts the author's own order (his research, other developers, laboratories, designers). Where the two collide, his rule "developer's power over the lab's ease" stands: the workbench hides options, the kernel never removes them.

Users: P3 through the browser workbench; P2 through case files and a command line; P1 through the Python library and plug-ins.

Capabilities, in rank order:

1. **Structure to prediction.** A PDB or mmCIF entry, salt, pH and a bias range give an I-V curve, conductance, rectification, transport number and electro-osmotic flow rate, each with a numerical error estimate and a statement of whether the conditions lie inside the validated envelope.
2. **What the laboratory actually measures.** Overlay of the group's own I-V data (CSV, ABF); asymmetric reservoirs and the reversal potential as a root find, since that is how selectivity is measured.
3. **Seeing it.** Linked views: the 3D structure, the (r, z) section with potential, concentrations, flow and fixed charge, and profiles along the axis.
4. **Variants.** Mutations typed as "S110R", compared side by side; a per-residue map of which charges control G, t+ and Q, from one adjoint solve.
5. **Analyte on the axis.** Residual current, axial force, PMF.
6. **Idealised pores** (cylinder, cone, hourglass, surface charge): for solid-state users, and as the public proof against analytic limits.
7. **Sweeps** on a laptop or a cluster from the same case.
8. **Model development.** Swap a correction, add a term, run models side by side on one mesh.

Left out: transients, gating and noise; running MD (trajectories are read, never produced); off-axis analytes and non-symmetric pores until 3D; charge regulation; automated design proposals (gradients are delivered, the optimiser is not); Brownian dynamics; a hosted service. A salt without a recorded fit runs only as classical PNP-NS, flagged.

## 2 The architecture: components, data, boundaries

Seven stages. Each is a pure function from immutable inputs to an immutable artefact, keyed by a hash of its inputs and code version.

1. **Case.** A declarative document validated against a schema, with every default resolved and written out.
2. **Structure.** Read or fetch, biological assembly, symmetry-axis detection and alignment, repair, mutation, protonation, charges and radii, optional ensemble. Output: an atom table per frame and a preparation report (oligomer, which mutation list was applied to which entry).
3. **Geometry.** Density, contour, smooth profile, ion-exclusion offset, membrane placement, analyte. Output: tagged regions and boundaries, signed wall distance, charge-source description, solid fraction. The representation is a tagged boundary plus a level set, so a 3D molecular surface fits the same slot.
4. **Mesh.** Tagged mesh and its refinement history.
5. **Model.** Fields, residual terms, material laws from a registry, boundary conditions, functionals. One composition path: classical PNP-NS is ePNP-NS with unit factors.
6. **Solve.** Discretisation, continuation, Newton, adaptivity. Output: fields and diagnostics.
7. **Quantities.** Functionals, closures, adjoint sensitivities, error estimates.

Around them: a **store** (content-addressed directory holding run records), a **runner** (expands a case into chains and executes them locally or on a cluster), a **service** (local HTTP API with an event stream; solves run in worker processes), the **workbench** (a static single-page application the service serves) and a **CLI**.

Boundaries:

- The kernel imports neither service nor workbench. The workbench speaks only to the API, and the API exposes nothing the CLI cannot do, so every laboratory result has a case file that a P2 user can rerun.
- The case schema is the single source: validation, API, workbench forms and reference documentation are generated from it. It is versioned with migrations; old cases always open.
- The engine is confined to stages 5 and 6. Everything else exchanges plain arrays and neutral files. Models are written directly in the engine's symbolic language, with no private abstraction over it; changing engine means rewriting the model terms and nothing else.
- A coordinates module supplies gradient, divergence, symmetric gradient and measure for the axisymmetric and the Cartesian 3D case. A model term is written once.
- Extension is by Python entry points: an outside package registers corrections, electrolytes, terms, geometry builders and quantities without a fork. Each registered item carries its data provenance and validity range, and the record names every item used.
- The hash keys give caching: a charge mutation reuses the mesh; a bias sweep reuses everything before the solve.

## 3 The technologies, each with its runner-up and the reason

Statements marked (checked) were looked up on 24 November 2026.

**Simulation engine and discretisation.** NGSolve. It gives symbolic weak forms with automatic linearisation, so any new term gets an exact Jacobian and an adjoint at no cost; symbolic differentiation of coefficients; 2D and 3D; adaptive and hp refinement; LGPL-2.1. Its PyPI wheels cover CPython 3.11 to 3.15 on Windows x64, macOS universal and Linux x86-64, and depend only on its mesher, NumPy and an OpenBLAS runtime (checked). Discretisation: plain continuous Galerkin, potential P2, log-concentrations P2, Taylor-Hood velocity P2 and pressure P1, no artificial diffusion. Runner-up: DOLFINx, for its larger community, PETSc scaling and adjoint tooling. Rejected for P3: on Windows it has no PETSc and needs Visual Studio for just-in-time compilation, and its pip wheels are beta builds on Test PyPI (checked). Third: scikit-fem with JAX linearisation, pure Python, but with no route to parallel 3D.

**Geometry and mesh.** Netgen with its OpenCascade kernel, installed with the engine: spline profile, material and boundary tags, curved elements, bisection refinement driven by an error estimator. Runner-up: Gmsh, whose size fields are better; its GPL would bind the whole program through the API, and it is a second tool to reconcile with the engine's curving and refinement. The program itself is Apache-2.0.

**Linear and nonlinear solution.** The program owns the linear seam: the Jacobian leaves the engine as a sparse matrix, and backends come in tiers. SciPy's SuperLU is the open floor, present everywhere. The engine's bundled factorisation, or MKL Pardiso where found, is used when faster; MKL is closed and so never required. Clusters use MUMPS from a conda or source build. Block-preconditioned Krylov methods come with 3D. Runner-up: MUMPS as the one default; it is the best open direct solver, but python-mumps, scikit-umfpack and scikit-sparse are source-only on PyPI (checked), which means a compiler. Nonlinear: fully coupled damped Newton with limited updates and the exact Jacobian; homotopy first in fixed charge, then in bias, with automatic step control; pseudo-time stepping as the last fallback. Runner-up: Gummel decoupling, robust at low bias but stalling under strong coupling.

**Structure and charge preparation.** gemmi (reading, assemblies, symmetry); PDBFixer on OpenMM (missing atoms, loops, mutations); PDB2PQR with PROPKA (protonation, CHARMM charges, radii, as PHY-16 states); MDAnalysis as an optional extra for trajectories; SciPy's scaled Bessel function for the closed-form kernel. All are wheels or pure Python. Runner-up: Biopython with Modeller; Modeller needs a licence key, which breaks "free throughout". Membrane placement: an own hydrophobic-belt heuristic that the user confirms by dragging the slab in the section view. Runner-up: lookup in an orientation database, which needs the network and covers only deposited entries.

**Front end and visualisation.** A TypeScript and React single-page application, built in CI and shipped as static files inside the wheel; a FastAPI service with server-sent events. Mol* shows the structure; a small own WebGL2 renderer shows the section (colour maps, isolines, streamlines, probe, linked cursor); Observable Plot draws charts as SVG; publication figures export as data plus a generated Matplotlib script. Runner-up: a Python-native kit (trame with PyVista, or NiceGUI): one language and far less code, but a ceiling on interaction and visual design, which the author names as a goal of its own. A desktop shell is rejected: signing certificates cost money, and a browser tab on a local server also serves a whole laboratory from one shared workstation.

**Storage, file formats and the record of a run.** Case: YAML with a JSON Schema (runner-up TOML; YAML nests deep cases more readably). Fields: HDF5 with an XDMF sidecar that ParaView opens (runner-up VTU). Quantity tables: Parquet (runner-up NetCDF). Record: one manifest per run holding the resolved case, input-file hashes, versions and lock hash, platform, artefact hashes, convergence trace, check results, error estimates, envelope class, deviations from validated defaults and warnings. The unit of exchange is a bundle, a zip of case, manifest and data that any install reopens. The filesystem is the truth; an SQLite index is disposable. Runner-up for the record: RO-Crate, kept as a later export.

**Distribution to the three kinds of user.** P3: one pasted line installs uv and then the program as an isolated tool with exactly pinned dependencies and its own Python; `open` starts the workbench. A `doctor` command runs the analytic checks on that machine in about a minute. Runner-up: a conda or pixi installer, which would bring MUMPS and DOLFINx but not remove the Windows compiler obstacle; signed native installers are rejected on cost. P2: pip into their own environment. P1: clone and `uv sync`, plus plug-in packages. Clusters: the same Linux wheel, with an Apptainer image built in CI as fallback.

**Many runs at once.** The unit is a chain (one variant, one concentration, bias continued from zero in both directions), not a point. A plan file lists chains with their hashes. Executors are a local process pool and a generated SLURM array script. Each chain writes its record atomically; collection is a query over records; a rerun skips what exists. Standard library only. Runner-up: Snakemake; the content-addressed stages already give its caching, and it is one more dependency that is weak on Windows.

## 4 The numerical method and how its results are trusted

Method:

- Unknowns are potential, log-concentrations, velocity and pressure. Log variables keep concentrations positive by construction where ions are depleted. Newton updates are limited so the packing fraction stays below one, and PHY-06 is still asserted.
- Axisymmetric forms are weighted by r; only u_r = 0 is imposed on the axis.
- No stabilisation. From the pack's own figures (0.1 m/s, 0.1 nm cells, D of order 10^-9 m^2/s) the cell Peclet number is of order 10^-2, so artificial diffusion buys nothing and costs consistency. Taylor-Hood removes the pressure stabilisation too.
- The pore profile is a smooth closed spline fitted to the contour. A 190-corner polygon puts a field singularity at every corner and makes convergence unmeasurable. Polygon tables are still accepted.
- Wall distance is computed geometrically from the spline, interpolated continuously, and clamped at zero where a law reads it (PHY-02).
- Fixed charge follows PHY-16 to PHY-19: the closed-form azimuthal kernel and a conserving projection.
- The mesh starts coarse and conforming, then refines towards the quantity of interest using the adjoint of the current functional. The user sees one mesh parameter: a tolerance on the result.
- Quantities are volume-weighted functionals: the current is the integral of J against the gradient of a weight that is one at one electrode and zero at the other; forces likewise. This is consistent with Galerkin, ready for the adjoint, and avoids integrating a non-conservative flux over a surface.
- One transposed solve per quantity gives its sensitivity to every atomic charge, to the protein permittivity and to the exclusion offset, and the refinement indicator.

Trust has five rungs. Each is a named case anyone can run with `verify`, published as a gallery that CI rebuilds:

1. **Law tables.** Every correction against PHY-12's self-consistency values (0.06, 0.99, 0.379), caps and clamps.
2. **Manufactured solutions, generated.** The harness differentiates any registered model symbolically to make its source terms, in axisymmetric and 3D form, and checks the convergence order. A plug-in is verified without its author writing a test.
3. **Analytic limits.** Debye-Huckel and Gouy-Chapman layers with the Grahame relation; electro-osmotic flow in a charged cylinder with H = I2/I1, for thin and overlapping layers; access resistance of an aperture and the series formula; Stokes drag and qE on a sphere; bulk conductivity and the bulk transport number 0.3963; the non-Boltzmann equilibrium drift of PHY-14.
4. **Cross-code.** Poisson against APBS; the COMSOL data for ClyA within stated bands, not digits; later, 3D against axisymmetric.
5. **Experiment.** ClyA-AS I-V over 0.05 to 3 M and +/-200 mV; the rectification peak near 0.15 M; the wild-type and ReFraC conductance pair.

Every run reports, beside the number and in plain words: the discretisation error per quantity (the adjoint estimate, confirmed by one finer solve); closures (current equal at both electrodes and per species, the charge-conservation legs, the force balance, sensitivity to reservoir radius); the envelope class (validated, extrapolated such as 4 to 5.3 M, or outside); and a first-order band from the fitted parameters (protein permittivity, exclusion offset, contour level). A refusal names the quantity and the place.

## 5 How it is developed: process, tests, records

Order: prove, then extend.

- **Phase 0, throwaway spikes.** Clean-machine installs of the engine on three operating systems in CI, with factorisation time at 10^6 unknowns per backend; classical PNP-Stokes in a charged cylinder against rung 3; one workbench screen on recorded data.
- **Phase 1.** The kernel on idealised pores: all models and corrections, rungs 1 to 3, record, CLI. This is released; it already serves solid-state pores.
- **Phase 2.** Structure, geometry and charge; ClyA; rungs 4 and 5.
- **Phase 3.** Workbench version 1 on the P3 path, with three partner-laboratory users observed installing and running it.
- **Phase 4.** Variants, sensitivities, analyte, cluster sweeps. Then 3D, molecular exchange, inverse design.

Workbench design starts in phase 1 as mock screens for the author's verdicts, and is built against recorded bundles, so it neither waits for the solver nor precedes the proof.

Process: the same form, fewer starts.

- The normative texts are the physics section, the case schema and short decision records. Numerical requirements live as tests that carry requirement identifiers; the traceability register is generated, not written.
- One command starts a work package, and an agent carries it from brief to merged pull request. The author acts twice: he approves a one-page brief (scope, acceptance tests, exclusions) and reads a one-page result with its evidence. Open questions arrive as a weekly digest, each with a proposed default that takes effect unless he overrules it.
- Gates: types and lint; unit tests; rungs 1 and 2 on every change; rungs 3 and 4 nightly; rung 5 and the golden bundles of earlier releases weekly, within tolerance bands; the install matrix on clean runners; browser end-to-end tests with screenshot comparison; a laboratory acceptance script (from install to a ClyA I-V within fifteen minutes on a clean laptop).
- Monthly releases. Schema migrations are tested against every old golden case.

## 6 The three choices you are least sure of

1. **NGSolve as the engine.** It is chosen for the install. DOLFINx is the better platform for community and for 3D at scale. I could not confirm which nonsymmetric direct solver the current wheels carry on each operating system now that MKL is no longer a dependency, and the SuperLU floor may be slow near 10^6 unknowns. Phase 0 decides. Because the engine is confined to two stages, reversing costs the model terms only.
2. **Plain Galerkin in log variables on fitted, adaptive meshes.** Finite volumes with exponentially fitted fluxes are the standard of device simulation, positive and locally conservative, and the author is heading for solid-state electronics. Unfitted methods may also suit 3D molecular surfaces better than fitted tetrahedra. The tests: 5 mM at +/-200 mV, current closure, and twenty different pores meshed unattended.
3. **The laboratory default: one static structure, with automatic orientation, membrane placement and spline profile,** using calibration values (protein permittivity, offset, contour level) fitted on ClyA from an MD ensemble. If predictions for other pores move by more than the reported band, the P3 promise fails whatever the numerics. The tests: static against ensemble on ClyA, then FraC and alpha-hemolysin against published conductances, before the workbench is released.

### Critical Files for Implementation

Nothing exists yet; these pack files bind the design.

- <pack>/04-physics.md
- <pack>/purpose.md
- <pack>/author.md
- <pack>/b-comsol-settings.md
- <pack>/02-electrokinetics-background/09-quantities-the-software-must-compute.md

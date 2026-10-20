# Code review: nanopnp architectural review and extensibility analysis

2026-10-20 · commit `dfdbb1a` (main) · scope: whole repository (`src/`, `tests/`, `docs/`, `knowledge/`) · focus: architecture, physics and numerics, 3D extensibility, physics modularity, and notebook usability

## Summary

This review assesses the architectural design, physical and numerical rigor, 3D extensibility, physics modularity, and notebook usability of `nanopnp` at commit `dfdbb1a` (v0.5.0-alpha.16).

The codebase is an open-source Python reimplementation of the extended Poisson–Nernst–Planck / Navier–Stokes (ePNP-NS) continuum modeling framework for biological nanopores (Willems et al., *Nanoscale* **12**, 16775–16795, 2020), replacing a legacy, manual COMSOL Multiphysics workflow. It solves steady coupled 2D-axisymmetric partial differential equations on atomistic structures.

The review found the numerical core and architectural hygiene to be exceptionally rigorous. In multiple domains (singularity-free coordinate integration, closed-form Bessel charge projection, dual-route superconvergent current gating, and compile-time AST layering ratchets), `nanopnp` significantly outperforms both the COMSOL baseline and standard academic finite-element codes.

| Finding Category | Critical | High | Medium | Low | Total |
|---|---:|---:|---:|---:|---:|
| Physics & Numerics (Core) | 0 | 0 | 3 | 2 | 5 |
| Frontend Geometry & CAD | 0 | 0 | 1 | 4 | 5 |
| 3D Extensibility Scaling | 0 | 1 | 1 | 0 | 2 |
| Physics Modularity & Schema | 0 | 0 | 1 | 2 | 3 |
| Notebook Tooling & Visualization | 0 | 0 | 1 | 1 | 2 |
| **Total** | **0** | **1** | **7** | **9** | **17** |

---

## Findings at a Glance

| ID | Area | Severity | Finding Summary | Recommendation |
|---|---|---|---|---|
| AR-01 | Numerics | Medium | Varadhan screened-Poisson distance approximation smooths sharp concave protein corners and risks negative undershoots. | Replace with an upwind Hamilton–Jacobi or fast marching Eikonal solver. |
| AR-02 | Numerics | Medium | Reference-matching stabilization drops second derivatives in residuals, causing loss of Galerkin consistency and sub-optimal $O(h^2)$ convergence. | Maintain unstabilized Galerkin as normative; implement consistent Variational Multiscale stabilization for future non-reference runs. |
| AR-03 | Physics | Medium | Baseline model omits Korteweg–Helmholtz dielectric-gradient body forces, creating a minor thermodynamic fluid momentum imbalance. | Keep bundled behind `dielectric_gradient_forces`; document thermodynamic trade-off for users. |
| AR-04 | Physics | Low | Continuum Navier–Stokes and mean-field PNP break down in sub-1.5 nm pore constrictions due to water structuring and dehydration energy barriers. | Augment 1D/2D models with empirical potential-of-mean-force dehydration barriers for sub-nanometer pores. |
| AR-05 | Numerics | Low | SciPy SuperLU suffers from fill-in explosion on fine meshes (>15 GB RAM at 1M DOFs), leaving large runs dependent on GPL SuiteSparse UMFPACK. | Bring the BSD-licensed iterative fallback (`NUM-22`) forward; reusing UMFPACK's symbolic analysis (REV-60) saves time on the UMFPACK path but does not reduce SuperLU's fill-in. |
| AR-06 | Post | Medium | Interface normal orientation in `MeshData.oriented_edges` can flip direction on boundaries touching multiple fluid zones (REV-120). | Assert uniform adjacent material pairs along any force-evaluated boundary in `post/forces.py`. |
| AR-07 | Geometry | Low | Slanted membrane-protein triple junctions can create acute contact angles (<25°), stressing Netgen element conditioning near SICN 0.3. | Add a minimum-angle check or local chamfer at the bilayer junction. |
| AR-08 | Geometry | Low | Advancing-front mesher in Netgen rounds edge subdivisions on thin ion-exclusion shells, requiring an explicit subdivision override. | Retain `divide_wall` workaround; document Netgen advance-front thin-layer behavior. |
| AR-09 | Structure | Low | `symmetry.axis: auto` requires the chains to agree in residue name wherever they share a residue number, and a chain to carry at least half the C-alpha of the most complete one, so hetero-oligomers are refused; a monomeric ($C_1$) pore is accepted only with `symmetry.axis: z`, which takes the file's z axis unchecked. | Consider a channel-cavity axis estimate for $C_1$ and hetero-oligomeric assemblies, in place of the unchecked `axis: z`. |
| AR-10 | Density | Low | Stage 2 refuses (`DensityInputError`, naming chain, residue and atom) an atom the CHARMM radius set does not name, so non-standard residues and cofactors must be deselected or added to the radius set. | Keep the refusal: "there is no fallback by element" is an author ruling (`SPECIFICATION.md` §5.2, stage 2), since a guessed radius is a plausible wrong geometry. An elemental fallback would first need that ruling changed. |
| AR-11 | 3D Extensibility | High | Direct sparse solvers (UMFPACK, SuperLU) collapse on 3D meshes ($10^6 - 10^7$ DOFs) due to $O(N^2)$ operation and memory scaling. | Implement `NUM-22` distributed-memory PETSc block preconditioning (`PCFIELDSPLIT`, AMG, Stokes Schur complement). |
| AR-12 | 3D Extensibility | Medium | Stages 3–6 are inherently two-dimensional; 3D requires solid OpenCASCADE booleans, 3D surface extraction, and tetrahedral meshing. | Build 3D Marching Cubes/MSMS pipeline and extend `MeshData` to 3D tetrahedra. |
| AR-13 | Physics Modularity | Medium | `default_ladder` in `solve/continuation.py` builds the fixed nine-stage NUM-18 path and ends only at `LADDER_TARGETS` (`epnp-ns`, `pnp-ns`); `solve_ladder` already takes any rung sequence, but the case schema can reach only the default ladder or a single rung (`numerics.continuation: none`). | Expose a model-declared ladder through the physics-model declaration, so a new coupled PDE brings its own rungs without a case-level ladder configuration (the NUM-18 NOTE keeps the ePNP-NS path fixed). |
| AR-14 | Physics Modularity | Low | Surface charge density weak form is fully implemented in `physics/poisson.py` but omitted from the case YAML schema. | Expose `surface_charge_C_m2` in `BoundaryConditions` (`io/case.py`). |
| AR-15 | Physics Modularity | Low | Custom empirical parameter files are confined to `data/corrections/` inside the repository and cannot be loaded by external path. | Allow absolute or case-relative paths in electrolyte parameter resolution. |
| AR-16 | Notebook Usability | Medium | The core package contains zero plotting imports (`matplotlib`, `pyvista`, `plotly`), and GUI plots are coupled to PySide6 Qt widgets. | Add a lightweight `nanopnp.post.plotting` module with Matplotlib convenience helpers. |
| AR-17 | Notebook Usability | Low | Core objects (`RunResult`, `CaseDocument`, `PoreProfile`, `MeshData`) lack rich display methods (`_repr_html_`, `_repr_svg_`). | Implement rich display methods for instant visual rendering in Jupyter cells. |

---

## 1. Architectural Overview & Pipeline Breakdown

`nanopnp` coordinates twelve discrete stages in a pure, content-addressed directed acyclic graph.

```
 PDB / mmCIF ──┐
 Trajectory ───┼─► [1 Structure] ─► [2 Density] ─► [3 Symmetry] ─► [4 Contour] ─► [5 Region] ─► [6 Mesh] ─┐
 pH, ForceField ┘          │                                                                              │
                           ▼                                                                              │
                   [7a Protonation]                                                                       │
                           │                                                                              │
                           └──────────────────────────────────────► [7b Charge / Fields] ─────────────────┤
                                                                                                          ▼
 Electrolyte, Corrections ─► [8 Materials] ────────────────────────────────────────────────────────► [9 Case]
                                                                                                          │
                                                                                                          ▼
                               [12 Report / Export] ◄── [11 QoI Extraction] ◄── [10 Nonlinear Solve] ◄────┘
```

### Stages 1–3: Structure Ingestion, Density Mapping & Symmetry Reduction
- **Structure Ingestion (`structure/`):** Ingests PDB and mmCIF structures. Superposition across frames uses Kabsch alignment. Symmetry detection uses cyclic chain-permutation SVD ($k \to k+1$) rather than principal moments of inertia. Over 98 ClyA frames, principal axes drift by up to $1.54^\circ$ due to thermal loop motions, whereas cyclic permutation restricts drift to $<0.010^\circ$ by construction.
- **Probabilistic Union Density (`density/`):** Deposition maps atoms to a 3D Cartesian grid ($h \in [0.025, 0.05]\text{ nm}$) using CHARMM van der Waals radii ($w_i = 0.93 R_i$). The density $\rho(x) = 1 - \prod_i (1 - g_i(x))$ is computed via numerically stable $\operatorname{expm1}/\operatorname{log1p}$ compositions, bounding density strictly to $[0, 1]$ and preventing density accumulation in overlapping cores.
- **Annular Integration (`symmetry/`):** Maps 3D Cartesian voxels to $(r, z)$ using exact geometric intersection areas between Cartesian grid cells and concentric circular annuli (`annular_weights`), eliminating bin-center sampling errors. Radial cubic splines detrend each annulus prior to azimuthal variance calculation, ensuring steep radial boundary gradients do not read as azimuthal asymmetry.

### Stages 4–6: Contour Extraction, CAD Assembly & Meshing
- **Contour Conditioning (`geometry/contour.py`):** Sub-pixel marching squares extract the isolevel contour (default $0.25$). Crevices and cavities are regularized via morphological closing and opening (disc radius $2h$). Volume-preserving Taubin smoothing ($\lambda = 0.5, \mu = -0.53$) eliminates high-frequency noise without constriction shrinkage. Douglas–Peucker simplification and edge-length thresholding enforce minimum feature sizes ($h_c = h$).
- **CAD Region Assembly (`geometry/region.py`):** Assembles a non-manifold B-Rep via `netgen.occ`. A $63 \times 63$ candidate chord search on the bilayer planes ($z = \pm 1.4\text{ nm}$) finds the widest-margin inner membrane edge meeting the outer pore wall, preventing accidental domain fragmentation at re-entrant caps.
- **Discrete Meshing (`mesh/`):** Netgen (LGPL-2.1) default, with an optional quarantined Gmsh (GPLv2+) backend. Wall sizing is governed by the electrolyte Debye length: $h_{\text{wall}} \le \min(0.05\text{ nm}, \lambda_D/5)$. Quality gates enforce minimum Signed Inverse Condition Number ($\text{SICN} > 0.3$) and inradius/circumradius ratio ($\gamma > 0.3$).

### Stage 7: Protonation, Charge Deposition & Dielectric Transition
- **Protonation (`charge/protonation.py`):** Drives PDB2PQR and PROPKA 3 at specified pH. Enforces heavy-atom coordinate registration to $0.01\text{ \AA}$ and net charge integrality to $10^{-6} e$.
- **Closed-Form Azimuthal Gaussian Kernel (`charge/kernel.py`):** Fixed charges are projected analytically using modified Bessel functions:
  $$\bar{\rho}_i(r, z) = q_i e \pi^{-3/2} w_i^{-3} \exp\left(-\frac{(r - r_i)^2 + (z - z_i)^2}{w_i^2}\right) \tilde{I}_0\left(\frac{2 r r_i}{w_i^2}\right)$$
  where $\tilde{I}_0(x) = e^{-x} I_0(x)$ is evaluated via `scipy.special.i0e`. The kernel is completely smooth and finite at $r = 0$, replacing singular $1/(2\pi r)$ approximations on the deposition path; a supplied `areal_charge_density` field (`charge/fields.py`) still takes the $1/(2\pi r)$ projection, guarded by an axis cutoff.
- **$r$-Weighted $L^2$ Projection (`charge/deposit.py`):** Charge is projected onto discontinuous finite-element spaces ($P_k$) by inverting local Gram matrices with exact collapsed-Gauss triangle quadrature, conserving net charge on the discrete mesh to $10^{-13}$.
- **Smooth Dielectric Transition (`charge/dielectric.py`):** Signed distance to fluid-facing walls generates a $C^1$ cubic Hermite solid fraction $\chi(r, z)$. Permittivity transitions smoothly over width $\delta$: $\varepsilon_r(r, z) = \chi(r, z) \varepsilon_p + (1 - \chi(r, z)) \varepsilon_{r,f}(\langle c \rangle)$.

### Stages 8–10: Materials, Case Assembly & Nonlinear Solve
- **Materials (`materials/`):** Evaluates local diffusivity $D_i(\langle c \rangle, d)$, mobility $\mu_i(\langle c \rangle, d)$, viscosity $\eta(\langle c \rangle, d)$, density $\varrho(\langle c \rangle)$, and permittivity $\varepsilon_r(\langle c \rangle)$. Drivers are floored ($\langle c \rangle \ge 10^{-6}\text{ M}$, $d \ge 0$) and clamped ($5.3\text{ M}$), logging all clamp activations.
- **Finite-Element Formulation (`physics/`):** Discretized using Taylor–Hood $P_2/P_1$ elements for velocity and pressure, combined with $P_2$ elements for electric potential $\varphi$ and ion concentrations $c_i$. Weak forms assemble cylindrical hoop strain ($2\eta u_r v_r / r$). Quadrature orders on all singular forms ($1/r$) are clamped to $\ge 3$.
- **Monolithic Damped Newton Solver (`numerics/`):** Automatic differentiation in C++ via NGSolve builds exact Jacobians. Backtracking line search enforces physical state gates ($c_i > 0$, $\Phi < 1.0$) and thermal potential increment caps ($\|\delta\varphi\|_\infty \le 25.693\text{ mV}$).
- **9-Stage Continuation Homotopy (`solve/`):** Solves severe non-convexities by stepping through:
  $$\text{Debye–Hückel} \to \text{PB} \to \text{Equilibrium PNP} \to \text{Charge Ramp} \to \text{Bias Ramp} \to \text{Flow Coupling} \to \text{Corrections} \to \text{Steric Flux} \to \text{Salt Sweep}$$

### Stages 11–12 & Orchestration: QoI, Provenance & Sweeps
- **Dual-Route Current Extraction (`post/qoi.py`):** Evaluates current via smooth indicator volume integrals and variational Dirichlet boundary reaction fluxes, gating agreement to $<10^{-3}$.
- **Analyte Forces (`post/forces.py`):** Evaluates axial force on rigid inclusions by integrating Maxwell and hydrodynamic stress tensors via volume domain extensions, boundary surface tractions, and boundary variational reaction forces, enforcing agreement to $< 0.1\text{ pN}$.
- **Result Store & Sweeps (`io/store.py`, `sweep/`):** Content-addressed store indexed by SHA-256 digests. Multi-parameter sweeps construct a warm-start dependency forest, sorting points into dependency waves with thread pinning and atomic staging rename.

---

## 2. Comparison with the State-of-the-Art

| Capability / Dimension | `nanopnp` | COMSOL Multiphysics 5.4/6.x | FEniCS / FEniCSx | Academic PNP / OpenPNP |
|---|---|---|---|---|
| **Discretization Stability** | Inf-sup stable Taylor–Hood $P_2/P_1$ velocity/pressure; $P_2$ for $\varphi, c_i$. | Equal-order $P_1+P_1$ with pressure stabilization (GLS/PSPG). | User-specified (typically Taylor–Hood or MINI). | Often Finite Difference or unstabilized low-order FEM. |
| **Singularity Handling ($r=0$)** | Quadrature order $\ge 3$ on all $1/r$ terms; hoop stress assembled; natural BCs on $\varphi, c_i$. | Proprietary internal handling; prone to unphysical flux near axis on coarse grids. | Requires manual assembly tricks and custom quadrature rules. | Often restricted to 1D Cartesian or unweighted approximations. |
| **Fixed Charge Deposition** | Exact analytical Bessel $\tilde{I}_0$ azimuthal kernel; conservative $L^2$ projection ($10^{-13}$). | 2D Gaussian divided by $2\pi r$. Singular at $r=0$; leaks charge; aliasing errors $\approx 1\%$. | Manual interpolation or Dirac delta point sources. | Point charges or uniform continuum slab approximations. |
| **QoI Verification** | Automated dual-route verification (indicator volume vs reaction flux) gated to $<0.1\%$. | Single-route cross-sectional integration; subject to CG flux errors. | Manual post-processing; no built-in dual-route gating. | Single-surface flux calculation; non-conservative. |
| **Solvers & Continuation** | Automated 9-stage continuation homotopy; state gates on $c_i > 0$ and $\Phi < 1$. | Parameter sweeps; manual tuning of damping and continuation steps. | Manual script loops; Newton solver frequently diverges on cold starts. | Basic Picard iteration or undamped Newton; fragile at high bias. |
| **Pipeline Integration** | End-to-end: PDB/trajectory $\to$ CAD $\to$ Mesh $\to$ Solve $\to$ QoI $\to$ Provenance. | Disjoint: manual PDB alignment, manual CAD vertex cleanup, manual solver setup. | Solvers only; external tools required for CAD, meshing, and chemistry. | Fragmented standalone scripts; limited geometry automation. |
| **Licensing & Architecture** | BSD-3-Clause core on the LGPL-2.1 NGSolve/Netgen backend; zero upward AST import ratchets; quarantined optional GPL backends (Gmsh), and the bundle's GPL-2+ UMFPACK default (CON-11). | Commercial, proprietary closed-source binary; costly licensing per core. | Open source (LGPL/GPL); solver library only. | Academic open source; often unmaintained. |

---

## 3. Extensibility Analysis: 2D-Axisymmetric to Full 3D

Extending `nanopnp` from 2D-axisymmetric to full 3D is a split-difficulty architectural challenge.

### 3.1 Specification Mandates
- **`CON-01` (`SPECIFICATION.md` line 413):** *"v1 SHALL be restricted to 2D-axisymmetric, steady-state solution. The architecture SHALL NOT preclude a later 3D or transient extension."*
- **Linear Solver Mandate (`NUM-22`, line 2778):** *"An iterative fallback SHALL be implemented before any 3D capability: multiplicative `PCFIELDSPLIT` over the blocks `{(φ, c_i), (u, p)}`, algebraic multigrid per scalar block, and a Stokes Schur complement approximated by `selfp` or the pressure mass matrix."*

### 3.2 Subsystem Breakdown for 3D

1. **Physics & Weak Forms (Easy to Moderate):**
   - Symbolic forms in `physics/poisson.py` and `physics/nernst_planck.py` evaluate identically in 3D Cartesian space without modification.
   - The hoop stress term in `physics/flow.py` vanishes in 3D; the code already branches on `if not measures.is_axisymmetric: return deviatoric`.
   - Measure weights become 1.0; singular $1/r$ quadrature rules are dropped.
   - Hardcoded 2D identity tensors sit at three sites in two files (`physics/stabilisation.py` line 222, `post/forces.py` lines 202 and 213). The second coordinate is also read as the pore axis outside the measures, in `post/indicator.py` (the indicator's `ngs.y`), `post/forces.py` (the `(ngs.x, ngs.y)` position) and `charge/fields.py` (the membrane planes), and each needs the same change.
2. **Post-Processing & QoI (Easy):**
   - Dual-route volume indicators and boundary reaction fluxes carry over directly. The pore axis direction updates from the second coordinate component to the third, and the azimuthal $2\pi$ multiplier is removed.
   - Force evaluation expands from axial force $F_z$ to full 3D force vectors $(F_x, F_y, F_z)$ and torques $(\tau_x, \tau_y, \tau_z)$.
3. **Frontend Geometry and Meshing (Hard):**
   - Stage 2 already builds a true 3D Cartesian density map. However, Stages 3 through 6 collapse this to two dimensions.
   - A 3D implementation requires bypassing azimuthal reduction, implementing 3D Marching Cubes or molecular surface extraction, performing solid OpenCASCADE boolean operations, and overhauling `MeshData` from triangles to tetrahedra.
4. **Linear Solvers and Scalability (Fundamental Redesign):**
   - A 3D nanopore mesh with resolved Debye layers requires between 5 million and 20 million degrees of freedom.
   - Direct sparse solvers (UMFPACK and SuperLU) scale with $\mathcal{O}(N^2)$ operations in 3D and are expected to exhaust memory: already in 2D, SuperLU was killed at 15.4 GB on the 1.04 × 10⁶-DOF reference mesh (`SPECIFICATION.md` §6.6, measured); the 3D figure is an extrapolation, not a measurement.
   - A 3D extension strictly requires distributed-memory preconditioned iterative solvers (PETSc/ngsPETSc with `PCFIELDSPLIT`, algebraic multigrid, and a Stokes Schur complement).

---

## 4. Extensibility and Modifiability of Physics Models

The physics architecture is modular at the solver layer, but guarded by an intentionally strict schema at the orchestration layer.

### 4.1 Model Registration & Abstractions (`physics/models.py`)
- Models implement the `PhysicsModel` or `TransportModel` protocol and are registered in `_REGISTRY`. Six models exist: `epnp-ns`, `pnp-ns`, `pnp`, `pb`, `pb-linear`, and `poisson`.
- Invariant `VER-56` prohibits code outside `physics/` from branching on model names or classes.

### 4.2 Material and Electrolyte Customization
- **Adding New Salts (e.g. $MgCl_2$, $CaCl_2$): Configuration Only.**
  Users place a validated YAML file in `data/corrections/` specifying ionic valences, bulk diffusivities, steric diameters, and empirical fit parameters. In `CoupledModel`, the solver loops dynamically over all declared species, assembling independent trial and test spaces.
- **Adding New Empirical Material Forms: Minor Code Edit.**
  Adding a new mathematical fit formula (such as Pitzer equations) requires implementing the function across both NumPy operations and symbolic NGSolve operations in `nanopnp/materials/forms.py`.
- **Directory Confinement Limitation:**
  `available_corrections()` currently restricts search paths to `data/corrections/*.yaml` inside the package root. Loading arbitrary custom YAML files by absolute path from `case.yaml` is not currently permitted by `_resolve()`.

### 4.3 Boundary Condition Extensibility
- **Surface Charge Density ($\sigma_s$):**
  A surface charge density weak form is already implemented in `physics/poisson.py`, but its parameter is not yet exposed in the case schema.
- **Robin / Stern Capacitance:**
  Requires adding a boundary bilinear form in `poisson.py` and freeing wall potential degrees of freedom in `CoupledModel.space()`.
- **Navier Slip Hydrodynamics:**
  Currently rejected by `pipeline/checks.py:325` with `UnsupportedCaseSection`. Implementation requires unconstraining tangential wall velocities and assembling boundary friction dissipation in `physics/flow.py`.

### 4.4 Adding Entirely New Coupled PDEs (e.g., Temperature / Joule Heating)
- Adding an entirely new coupled field requires coordinated edits across six modules: `physics/models.py`, `physics/spaces.py`, `io/case.py`, `pipeline/checks.py`, `solve/state.py`, and `solve/continuation.py`.
- NGSolve automatic differentiation builds the coupled Jacobian automatically.
- However, `default_ladder` in `solve/continuation.py` builds the fixed nine-stage NUM-18 path and ends only at `LADDER_TARGETS` (`epnp-ns`, `pnp-ns`). `solve_ladder` itself takes any rung sequence, so a new model's ladder is a new rung builder, but the case schema reaches only the default ladder or a single rung (`numerics.continuation: none`).

---

## 5. Notebook Usability, Interactive Execution & Visualization Tooling

### 5.1 In-Notebook Programmatic Execution: Fully Functional
- `nanopnp` can be imported and executed inside Jupyter notebooks without display servers or GUI event loops.
- Top-level symbols are resolved lazily via `__getattr__`, keeping initial import overhead low.
- Truncated walks using `upto="mesh"` or `upto="materials"` allow interactive execution and inspection of intermediate stages.
- Interactive callback hooks on `run_case` (`progress`, `on_stage`, `on_solve`, `on_artefact`) report stage progress and Newton residuals dynamically, and `cancel` takes a cancellation token.

### 5.2 Data Interoperability: High
- Users can extract raw NumPy arrays directly from stage artefacts (`PoreProfile.as_array()`, `ReducedMap.mean`, `MeshData.vertices`, and `MeshData.triangles`).
- Solution states can be reconstructed via `restore()` and evaluated at arbitrary spatial coordinates via `sample_at()`.
- Completed runs export standard XDMF and HDF5 files for ParaView or PyVista.

### 5.3 Built-in Visualization Tooling: Non-Existent
- The core library contains zero plotting library imports (`matplotlib`, `pyvista`, `plotly`, `vtk`).
- Plotting in the desktop shell is coupled to PySide6 Qt widgets (`QPainter` in `ConvergencePlot` and `GeometryCanvas`).
- Headless rendering code in `gui/render.py` generates static Three.js HTML and JSON files on disk. Notebook users must currently write their own Matplotlib boilerplate to visualize geometries, meshes, and heatmaps.

---

## 6. Recommendations & Roadmap

Items for findings the author declined (§7) are left out.

1. **Immediate (v0.5.x):**
   - Enforce uniform interface materials along force-evaluated boundaries (REV-120).
   - Provide lightweight Matplotlib plotting helpers and rich notebook display (REV-123).
2. **Mid-Term (v0.6 – v0.7):**
   - Admit a correction parameter file by path, hashed into the stage-8 key and the manifest (REV-122).
   - Estimate the axis of a monomeric or hetero-oligomeric pore (REV-121).
   - Reuse UMFPACK's symbolic analysis across Newton steps on a fixed mesh (REV-60, deferred to Phase 6 by §8.2.9 I3).
   - Implement store garbage collection (`nanopnp store gc`) for entries of an earlier schema (REV-32, deferred to Phase 5 by §8.2.9 I3), and zstandard array payload compression.
   - Migrate GUI to a decoupled browser architecture (REV-114).
3. **Long-Term (v1.0+):**
   - Implement distributed-memory PETSc block preconditioning (`PCFIELDSPLIT`, AMG, Stokes Schur complement) per `NUM-22`.

---

## 7. Disposition

The author ruled on each finding on 20 October 2026. Three items stay open in the
[review register](../project/review-items.md); the rest are declined, with the reason.

| ID | Ruling | Reason or item |
|---|---|---|
| AR-01 | declined | NUM-31 admits the screened-Poisson field. `physics/distance.py` clamps the decayed field to at most 1 and zeroes the source degrees of freedom, so `d ≥ 0` by construction; corner smoothing is its measured accuracy. |
| AR-02 | declined | Already the design: `stabilisation: none` is the default, and NUM-14 makes the dropped second derivatives a deliberate reproduction of the reference settings. The O(h²) claim has no evidence. |
| AR-03 | declined | Already the design: PHY-23 keeps the force off by default and records it as a deviation when on. |
| AR-04 | declined | A change to the model physics, which the COMSOL report fixes (§1.6). |
| AR-05 | declined | Duplicates NUM-22 and the SuperLU measurement of §6.6 (CON-11). |
| AR-06 | declined | Duplicates REV-120, open. |
| AR-07 | declined | No measurement; the SICN > 0.3 quality gate refuses such a mesh. |
| AR-08 | declined | No defect: it recommends keeping `divide_wall`. |
| AR-09 | open | [REV-121](../project/review-items.md#rev-121-stage-1-checks-no-axis-for-a-monomeric-or-hetero-oligomeric-pore) |
| AR-10 | declined | The §5.2 ruling: no fallback by element. |
| AR-11 | declined | Duplicates NUM-22, which already precedes any 3D capability. |
| AR-12 | declined | 3D is out of scope (N4); CON-01 asks only that the architecture not preclude it. |
| AR-13 | declined | QR-14 holds: a model registered as one class runs as a single rung, and no model yet needs another ladder. |
| AR-14 | declined | No requirement asks for a pore-wall surface charge in the case; surface charge belongs to the analyte, FR-21, v0.7. |
| AR-15 | open | [REV-122](../project/review-items.md#rev-122-a-case-cannot-load-a-correction-file-from-outside-the-installed-package) |
| AR-16 | open | [REV-123](../project/review-items.md#rev-123-the-library-has-no-plotting-helpers-or-notebook-display), with AR-17 |
| AR-17 | open | Merged into REV-123 |

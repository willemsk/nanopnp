# WP54 Author Review Notes & Comments: Notebooks and Scientific Visualization Revised

**Document Status:** Grounding specification for WP54 (`/np-plan wp 54`)  
**Date:** 28 October 2026  
**Scope:** Review, architectural constraints, and revision requirements for `notebooks/01`–`06`, `nanopnp.plot`, `nanopnp.mesh`, `nanopnp.sweep`, and case ergonomics (§8.2.16 R8).

---

## 1. Executive Summary & Motivation

The notebooks introduced in Phase 4 (WP51) established that each stage of the `nanopnp` pipeline can produce a visual artifact. However, an in-depth review from the perspective of an experimental and computational biophysicist reveals that **the notebooks currently function as test scripts for YAML string manipulation and disk-file orchestration rather than an intuitive, interactive Python workbench**.

### The Core Deficiencies
1. **Dotted-String YAML Mutation vs. Raw Python API**:
   Instead of using typed Python objects, notebooks load YAML cases from `examples/` and modify them by passing dictionaries of untyped dotted string paths (`case.with_(**{"geometry.density.grid_spacing_nm": 0.05})`). This eliminates autocompletion, type validation, parameter documentation on hover, and structural clarity.
2. **CLI and File-System Leaks**:
   Notebooks invoke terminal CLI entry points (`main(["mesh", "cylinder", ...])`), manually dump YAML strings (`yaml.safe_dump`), compute SHA-256 hashes to create disk folders, and write temporary `.msh` and `.pdb` files into repository example directories.
3. **Parasitic Coupling to `examples/`**:
   Every notebook calls `os.chdir(example)`, mutating process-wide working directories, dirtying the git working tree, and dynamically executing external scripts (`prepare.py`) via `importlib.util` with monkey-patched globals.
4. **Biophysical Blind Spots in Visualization (`nanopnp.plot`)**:
   - The pore lumen ($r \sim 1.5\text{ nm}$) is compressed into an illegible 2-pixel sliver inside large reservoir boxes ($R = 50\text{--}250\text{ nm}$).
   - Potential is plotted in `V` rather than laboratory **`mV`**, with uncentered colormaps where 0 V appears charged.
   - Fluid velocity is plotted as unsigned scalar speed $|u|$, completely concealing electro-osmotic flow (EOF) directionality and vortices.
   - Linear concentration scales wash out electric double layer (EDL) depletion and enrichment.
   - **Crucial 1D cutlines** ($\phi(0, z)$, $c_i(0, z)$, $u_z(0, z)$), the primary quantitative diagnostic in nanopore literature, do not exist.
5. **Fighting Marimo's Reactive Model**:
   Notebooks enforce linear execution with `only=True` (which throws `MissingUpstreamError` on parameter adjustments) and defensive assertions (`assert run_prev.stages[-1].name == "..."`), bloating notebooks `05` and `06` into 40+ repetitive cells.

---

## 2. Architectural Guardrails & Conformance

Any enhancements must strictly observe the repository's foundational architecture rules:

1. **Layer Ordering (VER-61)**:
   - In `modularity-layering.yaml`, the layer order is:
     $$\dots \to \text{post (13)} \to \text{plot (14)} \to \text{pipeline (15)} \to \text{sweep (16)} \to \dots \to \text{core.public (20)}$$
   - `Case` resides in `nanopnp.pipeline.handle` (layer 15). It must **not** import `nanopnp.sweep` (layer 16), which would create an illegal upward edge.
   - Programmatic sweeps must be defined in `nanopnp.sweep` (e.g., `from nanopnp.sweep import sweep` or `Sweep(case, ...)`), which imports `Case` downwards. It is re-exported lazily at the public boundary (`nanopnp.PUBLIC`).
2. **Backend Isolation (VER-65)**:
   - `plot/`, `structure/`, and `pipeline/` are strictly non-backend packages and must never import `ngsolve` or `netgen`.
   - Field sampling for 1D cutlines must live in `nanopnp.post.export` (which is permitted to import NGSolve) and return pure NumPy arrays to `nanopnp.plot.data`.
   - `nanopnp.structure.orient_pore` must use only NumPy and MDAnalysis.
3. **Lazy Public Imports (VER-45)**:
   - `import nanopnp` and `dir(nanopnp)` must remain fast, solver-free, and numpy-free. New public functions join `nanopnp.core.public.PUBLIC` as lazy string entries resolved via `__getattr__`.
4. **Word and Decision Caps**:
   - The WP54 plan is capped at 6 decisions and 3,500 words (§8.4.4; §8.2.16 R11). To maintain scope discipline, full fluent section builders (`with_density`, `with_numerics`) are deferred to Phase 5; leaf-name editing on `case.with_(...)` and a typed constructor `Case.cylinder(...)` suffice for WP54.

---

## 3. Key Pillars of the Revision

### Pillar A: Expose & Emphasize the Raw Python API

#### 1. Programmatic Mesh Generation (`nanopnp.mesh`)
Calling `nanopnp.cli.main(["mesh", "cylinder", ...])` in a Python notebook is an anti-pattern. `nanopnp.mesh` must export a first-class Python function:
```python
# Before (04-sweep / 05-cylinder):
flags = [str(item) for pair in cylinder.items() for item in pair]
main(["mesh", "cylinder", *flags, "--out", str(mesh_file)])

# After:
from nanopnp.mesh import mesh_cylinder

mesh_file = mesh_cylinder(
    pore_radius_nm=2.0,
    membrane_thickness_nm=6.0,
    reservoir_radius_nm=10.0,
    maxh_nm=4.0,
    wall_h_nm=0.35,
    out=local_dir / "pore.msh",
)
```

#### 2. In-Memory Programmatic Sweeps (`nanopnp.sweep`)
Eliminate the 30-line ceremony of `yaml.safe_dump`, `sha256` hashing, directory creation, and disk-plan dumping:
```python
# In nanopnp.sweep:
from nanopnp.sweep import sweep

dataset = sweep(
    case,
    axis="boundary_conditions.bias_V",
    values=[-0.1, -0.05, 0.05, 0.1],
    origin=0.05,
).run()
```
The sweep engine uses a local temporary scratch directory for worker communication and warm-start forest resolution while returning the collected `SweepDataset` directly in memory.

#### 3. Typed Case Construction
Provide a clean typed factory for synthetic pores while preserving leaf-key editing for custom settings:
```python
case = Case.cylinder(
    radius_nm=1.5,
    length_nm=10.0,
    membrane_thickness_nm=13.0,
    concentration_M=0.15,
    bias_V=0.05,
    store=local_store,
)
```

#### 4. Ergonomic `RunResult` Accessors
Researchers should easily extract numerical arrays and physical scalars for custom plotting or calculations:
```python
current_nA = run_solve.current_nA  # Scalar current in nA from QoI
conductance_nS = run_solve.conductance_nS  # Conductance in nS
fields = run_solve.fields  # Access to field arrays
```

---

### Pillar B: Complete Decoupling from `examples/`

1. **Remove `os.chdir`**: Notebooks must not mutate the global process working directory. All paths must be relative to the notebook file or explicitly configured.
2. **Local Notebook Storage**: Each notebook writes its cache into a local directory (`Path(__file__).parent / "store"` or a user-specified path). Running notebooks must never pollute `examples/` with `.msh`, `.pdb`, or `store/` directories.
3. **Pore Alignment in `nanopnp.structure`**:
   The logic in `examples/06-pdb-to-mesh/prepare.py` (covariance eigenvalue analysis, registration, and Rodrigues rotation) is promoted to a library function:
   ```python
   from nanopnp.structure import orient_pore

   prepared_pdb = orient_pore(
       "2wcd.pdb.gz",
       chains="A-L",
       point_group="C12",
       registration_residues="8:292",
       centroid_z_nm=5.655,
       out=local_dir / "2wcd-oriented.pdb",
   )
   ```
   This eliminates dynamic `importlib` calls and external script execution.
4. **Standard Sample Assets**: Provide a clean path helper to access bundled test structures (`nanopnp.data.sample_structure("2wcd.pdb.gz")`).

---

### Pillar C: Scientific & Graph Visualization Enhancements (`nanopnp.plot`)

#### 1. Dual-View Geometry & Mesh (Resolving the 250 nm vs. 2 nm Trap)
- **Problem**: When reservoirs are 250 nm wide, a 2 nm pore is an unresolvable 2-pixel vertical line.
- **Solution**:
  - `mesh_figure`: Add a dual-panel layout or inset.
    - Panel 1: Full domain overview (reservoirs, membrane, far-field boundary).
    - Panel 2: Zoomed lumen view ($r \le 5\text{ nm}, |z| \le 10\text{ nm}$) displaying element wireframes (`ax.triplot`), wall refinement, and element quality.
  - Overlay a visual indication of the Debye length $\lambda_D$ to verify boundary layer sizing against the NUM-30 threshold ($\lambda_D / 5$).

#### 2. Essential 1D Cutlines (Axial & Radial Profiles)
1D profiles are the standard quantitative figures in nanopore electrophysiology.
- In `nanopnp.post.export`:
  - `sample_axial_cutline(mesh, fields, num_points=200)`: Evaluates exact FE polynomials along $r = 0$, $z \in [-L, L]$.
  - `sample_radial_cutline(mesh, fields, z_nm=0.0, num_points=100)`: Evaluates across the pore lumen up to the wall boundary.
- In `nanopnp.plot.figures`:
  - `axial_cutline_figure(artefact, inputs=inputs)`: 3-panel figure showing potential $\phi(0, z)$ in mV, ion concentrations $c_{\text{cation}}, c_{\text{anion}}$, and axial velocity $u_z(0, z)$.

#### 3. Biophysical Units, Colormaps, and Scaling
- **Potential in `mV`**: Scale electrostatic potential to millivolts ($\text{V} \times 10^3$). Center `RdBu_r` at 0 mV using a guarded `TwoSlopeNorm(vmin=min(0.0, vmin_data), vcenter=0.0, vmax=max(0.0, vmax_data))` so neutral bulk is white and polarities are visually unambiguous without crashing on unipolar solves.
- **Logarithmic Ion Concentrations**: Provide logarithmic scaling options ($\log_{10}(c / c_{\text{bulk}})$ or `LogNorm`) so that deep co-ion depletion zones ($10^{-3}\text{ M}$) and counter-ion condensation ($2.5\text{ M}$) are visible simultaneously.
- **Signed Velocity & Streamlines**: Replace or augment scalar speed $|u|$ with signed axial velocity $u_z$ and 2D vector streamlines (`ax.streamplot` sampled on a regular grid) to clearly indicate cis-to-trans vs. trans-to-cis pumping and recirculation vortices.
- **Constriction Annotations**: Annotate the minimum pore radius $r_{\min}$ and its axial position $z(r_{\min})$ on contour figures.
- **$I\text{--}V$ Enhancements**: Annotate the rectification ratio $r(V) = |I(+V) / I(-V)|$ and Ohmic conductance slope ($G = I/V$) directly on the primary sweep panel.

#### 4. Granular, Modular Plotting Functions
Refactor `src/nanopnp/plot/figures.py` so functions accept explicit keywords and existing Matplotlib `Axes`:
```python
plot_field(fields, "potential", ax=ax, unit="mV", clim=(-100, 100), zoom_nm=(5, 10))
plot_mesh(mesh_elements, ax=ax, show_wireframe=True, zoom_lumen=True)
plot_axial_cutline(fields, "potential", r=0.0, ax=ax)
plot_iv(sweep_dataset, ax=ax, annotate_rectification=True)
```

---

### Pillar D: Marimo Ergonomics & Workflow Streamlining

1. **Enable Natural Reactive Caching (`only=False`)**:
   - Remove `only=True` and all `assert run_prev.stages[-1].name == "..."` defensive assertions.
   - Let Marimo's DAG recompute invalidated stages automatically while `nanopnp.io.store` transparently reuses cached stages (< 1 ms).
2. **In-Situ Reactive Controls**:
   - Replace the detached top-level `scale = 1.5; interactive = False` cell with localized controls.
   - Use Marimo UI widgets (`mo.ui.slider` for voltage/concentration/isolevel, `mo.ui.dropdown` for field selection, `mo.ui.table` for QoI metrics).
3. **Consolidate Redundant Notebooks**:
   - `05-cylinder` and `06-2wcd` currently repeat 40+ cells of boilerplate. Streamline them into focused narrative workflows:
     - `05-cylinder`: Fast, end-to-end synthetic pore benchmark (Mesh $\to$ Solve $\to$ 1D Cutlines $\to$ $I\text{--}V$ Sweep).
     - `06-2wcd`: Biological nanopore showcase (Orient $\to$ Contour $\to$ Mesh $\to$ Titration $\to$ Solve).

---

## 4. Specific Notebook-by-Notebook Action Plan

| Notebook | Current Issues | Proposed Revisions for WP54 |
| :--- | :--- | :--- |
| **`01-geometry`** (2WCD PDB to Mesh) | • `os.chdir(example)`<br>• Dynamic `importlib` execution of `prepare.py`<br>• Dotted-string dicts (`"geometry.density.grid_spacing_nm"`)<br>• Linear `only=True` locking | • Use `nanopnp.structure.orient_pore(...)`<br>• Use `Case.from_structure(...)`<br>• Add `mo.ui.slider` for grid spacing and sharpness<br>• Add dual-view (Full + Lumen inset) to mesh figure |
| **`02-charge`** (2WCD Charge & Materials) | • Rigid setup cell running stages 1–6<br>• Dotted strings for salt concentration and models<br>• Material validity bounds don't mark operating point | • Typed electrolyte specification<br>• Highlight current operating concentration on correction curves<br>• Show dielectric boundary contour ($\varepsilon_r = 2 \to 80$) |
| **`03-solve`** (Cylinder ePNP-NS Solve) | • Calls CLI `main(["mesh", "cylinder", ...])`<br>• Potential plotted in `V` without 0 V centering<br>• Speed $|u|$ hides flow direction<br>• Grid layout leaves 3 empty blank panel holes | • Use `nanopnp.mesh.mesh_cylinder(...)`<br>• Switch potential to `mV` with bounded `TwoSlopeNorm(0)`<br>• Add streamlines/signed $u_z$ for EOF<br>• Add 1D axial cutlines ($\phi, c_i, u_z$ along $r=0$)<br>• Reorganize multi-panel grid cleanly |
| **`04-sweep`** (Cylinder I-V Sweep) | • Calls CLI `main(["mesh", "cylinder", ...])`<br>• 30 lines of `yaml.safe_dump`, `sha256`, and disk dirs<br>• Pollutes `examples/03-iv-sweep/` | • Use `nanopnp.sweep.sweep(case, axis="bias_V", values=[...]).run()`<br>• Annotate rectification ratio $r(V)$ on $I\text{--}V$ curve<br>• Replace image pixel table with native `mo.ui.table(...)` |
| **`05-cylinder`** (End-to-End Cylinder) | • 373 lines duplicating `03-solve` and `04-sweep`<br>• 4-cell ritual per stage with `only=True` assertions | • Consolidate into a sleek 4-block workflow<br>• Reactive voltage slider<br>• Combined 2D field display + 1D cutline comparison |
| **`06-2wcd`** (End-to-End 2WCD) | • 478 lines / 44 cells of copy-paste ritual<br>• Dynamic `prepare.py` monkeypatching<br>• Writes 2.4 MB PDB and stores into `examples/07/` | • Streamline stage execution into logical biophysical steps<br>• Clean orientation via library API<br>• Focus on biological parameters (pH, salt, titration) |

---

## 5. Proposed Plan Decisions for `wp54-notebooks-and-figures-revised.md`

| # | Decision | Choice | Why/Source |
|---|---|---|---|
| **D1** | **Programmatic Meshing & Structure Orientation** | Expose `nanopnp.mesh.mesh_cylinder(...)` (layer 9) and `nanopnp.structure.orient_pore(...)` (layer 2). Both join `PUBLIC` lazily. | Eliminates CLI subprocesses and external script monkeypatching. `structure` uses NumPy + MDAnalysis (VER-65 backend-free). |
| **D2** | **In-Memory Programmatic Sweeps** | Expose `nanopnp.sweep.sweep(case, ...)` in `nanopnp.sweep` (layer 16), re-exported lazily at `PUBLIC`. | Eliminates 30-line disk YAML ceremony while strictly preserving VER-61 layer order (sweep $\to$ pipeline is downward). |
| **D3** | **Biophysical Visualization Standards in `plot`** | Potential in `mV` with bounded `TwoSlopeNorm(0.0)`; signed axial velocity $u_z$ and EOF streamlines; log ion concentration scaling. | Aligns with electrophysiology literature; unipolar solutions do not crash; reveals EOF directionality and EDL depletion. |
| **D4** | **1D Cutlines (Axial & Radial Profiles)** | Exact FE sampling in `nanopnp.post.export.sample_axial_cutline` (backend); drawing in `nanopnp.plot.figures.axial_cutline_figure`. | Core biophysical diagnostic for access resistance, Donnan drops, and Debye screening. Preserves VER-65 (plot imports no backend). |
| **D5** | **Dual-View Mesh & Geometry Inspection** | `mesh_figure` adds a dual-view (domain overview + zoomed lumen inset with element wireframes and $\lambda_D / 5$ threshold). | Resolves the 250 nm vs. 2 nm visual compression trap. Direct visual check for NUM-30. |
| **D6** | **Decoupled, Reactive Notebook Workflows** | Remove `os.chdir(example)`, drop `only=True` assertions, use local `./store` directories, and streamline notebooks 01–06 with native Marimo UI widgets. | Restores natural Marimo reactivity; prevents git tree pollution; transforms notebooks from test harnesses to interactive workbench tools. |

---

## 6. Verification Strategy

1. **Tier 1 (`tests/tier1/test_figures.py` & `test_public_api.py`)**:
   - Unit tests for `mesh_cylinder` and `orient_pore` parameter validation and execution.
   - Assert `mV` scaling, `TwoSlopeNorm` bounds handling, and cutline sampling arrays.
   - Verify that `PUBLIC` additions remain lazy and `import nanopnp` loads no solver, Netgen, or NumPy (VER-45).
   - Verify VER-61 layering (`test_layering.py`) and VER-65 backend guard (`test_backend_guard.py`) remain completely green.
2. **Tier 2 (`tests/tier2/test_notebooks.py`)**:
   - All 6 notebooks run headless via `python notebook.py` from their own directories and exit `0` without errors or warnings.

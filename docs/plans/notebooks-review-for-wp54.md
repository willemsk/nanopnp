# WP54 Review and Specification: Notebooks and Scientific Plots

**Status:** Input specification for WP54 (`/np-plan wp 54`)  
**Date:** 28 October 2026  
**Scope:** Requirements for `notebooks/01` through `06`, `nanopnp.plot`, `nanopnp.mesh`, `nanopnp.structure`, `nanopnp.sweep`, and `nanopnp.pipeline` (§8.2.16 R8).

---

## 1. Summary and Problem Statement

Phase 4 (WP51) added one notebook for each stage group of the `nanopnp` pipeline. Each notebook produces a stage figure. However, the current notebooks operate as test scripts for YAML string edits and file commands rather than an interactive Python interface.

### Current Problems
1. **Dotted-String YAML Edits Instead of Typed Python Calls**
   - The notebooks load YAML case files from `examples/`. They change parameters with untyped dotted strings (`case.with_(**{"geometry.density.grid_spacing_nm": 0.05})`).
   - This approach prevents IDE autocompletion, static type checks, and parameter documentation.
2. **CLI Calls and Manual File Management**
   - The notebooks call the CLI entry point (`main(["mesh", "cylinder", ...])`).
   - They format YAML strings with `yaml.safe_dump`, compute SHA-256 hashes manually, and write temporary `.msh` and `.pdb` files into `examples/`.
3. **Dependency on `examples/` and Process Working Directory**
   - Every notebook calls `os.chdir(example)`. This call changes the global process directory and leaves untracked files in the git working tree.
   - The structure notebooks load `examples/06-pdb-to-mesh/prepare.py` through `importlib.util` and overwrite its module globals.
4. **Missing Information in `nanopnp.plot` Figures**
   - A pore with radius $r \sim 1.5\text{ nm}$ appears as a 2-pixel line inside a large reservoir box ($R = 50\text{--}250\text{ nm}$).
   - Electrostatic potential plots use `V` instead of `mV`. The colormap does not center at `0 mV`, so neutral bulk fluid appears charged.
   - Velocity plots show unsigned scalar speed $|u|$. They do not show the flow direction or vortices.
   - Linear concentration scales hide ion depletion and accumulation in the electric double layer (EDL).
   - The plotting module does not provide 1D axial or radial cutlines ($\phi(0, z)$, $c_i(0, z)$, $u_z(0, z)$).
5. **Linear Execution Locks in Marimo**
   - Each stage cell sets `only=True` and checks `assert run_prev.stages[-1].name == "..."`.
   - Changing one parameter raises `MissingUpstreamError`. Notebooks `05` and `06` repeat 40+ cells of boilerplate.

---

## 2. Architectural Rules

All changes must obey the repository verification rules:

1. **Layer Order (`VER-61`)**
   - `LAYER_ORDER` in `src/nanopnp/validation/modularity.py` (0-indexed) defines the package order:
     $$\text{core (0)} \to \text{io (1)} \to \text{structure (2)} \to \dots \to \text{mesh (6)} \to \dots \to \text{post (12)} \to \text{plot (13)} \to \text{pipeline (14)} \to \text{sweep (15)} \to \dots \to \text{nanopnp (19)}$$
   - `Case` lives in `nanopnp.pipeline.handle` (layer 14). It must not import `nanopnp.sweep` (layer 15).
   - Define programmatic sweeps in `nanopnp.sweep` (`from nanopnp.sweep import sweep`). `nanopnp.sweep` imports `Case` downwards.
   - Re-export new public functions lazily in `nanopnp.core.public.PUBLIC`. Add matching `if TYPE_CHECKING:` imports and `__all__` entries in `src/nanopnp/__init__.py`. Record all new `static` and `string` edges in `docs/project/modularity-layering.yaml`.
2. **Backend Isolation and Optional Extras (`VER-65`, `VER-72`)**
   - `plot/`, `structure/`, and `pipeline/` must not import `ngsolve` or `netgen`.
   - Compute 1D cutlines in `nanopnp.plot` directly from `SolutionFields` (`P2Nodes`). `P2Nodes` already stores the exact 6-node P2 polynomial values from `nanopnp.post.export.sampled_fields`. This avoids a second finite-element restore call and keeps `plot/` free of solver imports.
   - In `nanopnp.structure.orient_pore`, import `numpy` and `MDAnalysis` inside the function. Raise `MissingExtraError` naming `structure` when `MDAnalysis` is not installed (`VER-72`).
3. **Lazy Public Imports (`VER-45`)**
   - `import nanopnp` and `dir(nanopnp)` must not load `ngsolve`, `netgen`, `MDAnalysis`, or `numpy`.
4. **Plan Limits and Specification Sync**
   - Limit the WP54 plan to at most 6 decisions and 3,500 words (§8.4.4; §8.2.16 R11).
   - Defer section builder methods (`with_density`, `with_numerics`) to Phase 5. Use leaf-key updates on `case.with_(...)` and typed constructors `Case.cylinder(...)` and `Case.from_structure(...)` in WP54.
   - Update `SPECIFICATION.md` and `specification/history/` in the same commit as the code changes (`FR-30`, `FR-37`, Ruling P5, and Ruling P9).

---

## 3. Core Revision Areas

### Area A: Python API

#### 1. Mesh Generation Function (`nanopnp.mesh`)
Export `mesh_cylinder` in `nanopnp.mesh` so notebooks do not call `nanopnp.cli.main`:
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

#### 2. In-Memory Sweeps (`nanopnp.sweep`)
Export `sweep` in `nanopnp.sweep` to run parameter sweeps without manual YAML files or SHA-256 directory scripts:
```python
from nanopnp.sweep import sweep

artefact = sweep(
    case,
    axis="boundary_conditions.bias_V",
    values=[-0.1, -0.05, 0.05, 0.1],
    origin=2,  # 0-based index into values (0.05 V), or origin_value=0.05
).run()
```
Update `SweepPlan` to accept an in-memory `CaseDocument`. Compute `base_case_sha256` from `CaseArtefact(document).hash` when `base_path` is not on disk. Return a `SweepArtefact` directly.

#### 3. Typed Case Constructors (`Case.cylinder` and `Case.from_structure`)
Add typed factory methods on `Case` while keeping the `CaseDocument` schema unchanged:
```python
case = Case.cylinder(
    pore_radius_nm=1.5,
    membrane_thickness_nm=13.0,
    reservoir_radius_nm=15.0,
    concentration_M=0.15,
    bias_V=0.05,
    surface_charge_C_m2=-0.02,
    store=local_store,
)
```
`Case.cylinder(...)` builds the `.msh` file in `store.root / "meshes"` (addressed by the hash of the cylinder parameters) and sets `inputs.mesh.path`. `Case.from_structure(path, point_group="C12", ...)` builds a structure-backed `Case` in memory.

#### 4. `RunResult` Properties
Add properties on `RunResult` to return physical scalars and field arrays:
```python
current_nA = run_qoi.current_nA  # Current in nA from stage 11 (qoi)
conductance_nS = run_qoi.conductance_nS  # I / V in nS (None when bias_V == 0.0)
fields = run_solve.fields  # SolutionFields from nanopnp.plot.data.solution_fields
```

---

### Area B: Decoupling from `examples/`

1. **Remove `os.chdir` and Rebase Relative Paths in `Case.load`**
   - Remove all `os.chdir` calls from the notebooks.
   - Update `Case.load(path, store=...)` to resolve relative `inputs.*.path` and `structure.source.path` values against `Path(path).resolve().parent`.
2. **Use One Shared Gitignored Notebook Store**
   - Set the default notebook store to `nanopnp.core.paths.REPO_ROOT / "notebooks" / ".store"` (or `$NANOPNP_STORE` via `store_root()`).
   - Use a module-scoped store fixture in `tests/tier2/test_notebooks.py`.
   - Notebooks `01-geometry`, `02-charge`, and `06-2wcd` run the same 2WCD stages 1 through 8. Sharing the store reuses cached stages in $< 10\text{ ms}$ and saves ~4.5 minutes per run.
3. **Move Pore Orientation to `nanopnp.structure` (Amending `FR-37`)**
   - Move the orientation algorithm from `examples/06-pdb-to-mesh/prepare.py` (covariance eigenvalue analysis, chain registration, and Rodrigues rotation) to `nanopnp.structure.orient_pore`:
   ```python
   from nanopnp.structure import orient_pore

   prepared_pdb = orient_pore(
       structure_file("2wcd.pdb.gz"),
       chains="A,B,C,D,E,F,G,H,I,J,K,L",
       registration_residues=(8, 292),
       centroid_z_nm=5.655,
       out=store.root / "structures" / "2wcd-oriented.pdb",
   )
   ```
   - Accept `"all"` or comma-separated chain identifiers matching `nanopnp.io.resolved.parse_chains`.
4. **Bundle `2wcd.pdb.gz` for `structure_file`**
   - Place `2wcd.pdb.gz` in `data/structures/` (or fall back to `tests/data/structures/` in editable checkouts) so `nanopnp.core.paths.structure_file("2wcd.pdb.gz")` returns a valid path. Do not create a `nanopnp.data` package.

---

### Area C: Scientific Plots (`nanopnp.plot`)

#### 1. Dual-View `mesh_figure`
- Update `mesh_figure` (amending Ruling P9 and `FR-30`) to draw two panels:
  - **Panel 1:** Full domain view showing the reservoirs, the membrane, and the outer boundary.
  - **Panel 2:** Zoomed pore lumen view ($r \le 5\text{ nm}, |z| \le 10\text{ nm}$) showing the element wireframe (`ax.triplot`), wall refinement, and element quality.
- Draw a scale bar for the Debye target $\lambda_D / 5$ to verify `NUM-30`. Read $\lambda_D / 5$ from `case_debye_record(inputs.resolved)` when `inputs` is present, or from `artefact.summary.get("sizing")`.

#### 2. 1D Axial and Radial Cutlines
- Interpolate 1D axial ($r = r_0, z \in [-L, L]$) and radial ($z = z_0, r \in [0, r_{\text{wall}}(z_0)]$) profiles in `nanopnp.plot` from `SolutionFields` (`P2Nodes`) with `matplotlib.tri.LinearTriInterpolator`.
- Use `fields.fluid` for ion concentrations, velocity, and pressure, and use `fields.potential` for electrostatic potential.
- Export `plot_axial_cutline(fields, ...)` and `plot_radial_cutline(fields, ...)` in `nanopnp.plot`.

#### 3. Physical Units, Colormaps, and Annotations
- **Potential in `mV`:** Scale potential by $10^3$ in `DISPLAY["potential"]` and `solve_figure`. Center `RdBu_r` at `0.0 mV` with `matplotlib.colors.CenteredNorm(vcenter=0.0, halfrange=max(abs(vmin_data), abs(vmax_data), 1e-12))`.
- **Logarithmic Concentrations:** Support logarithmic scaling ($\log_{10}(c / c_{\text{bulk}})$ or `LogNorm`) to show co-ion depletion and counter-ion accumulation on the same axis.
- **Signed Velocity and Streamlines:** Plot signed axial velocity $u_z$ and draw 2D streamlines (`ax.streamplot` on a $60 \times 120$ grid in the zoomed lumen view) to show flow direction and vortices.
- **Geometry and Dielectric Annotations:** Mark the minimum pore radius $r_{\min}$ and its axial position $z(r_{\min})$ on contour figures. Draw the $\chi = 0.5$ solid-fraction contour on `fields_figure`.
- **$I\text{--}V$ Annotations:** Annotate the rectification ratio $r(V) = |I(+V) / I(-V)|$ and the Ohmic conductance slope $G = I / V$ on `sweep_figure`.

#### 4. Composable Plotting Functions
Provide plotting functions in `nanopnp.plot` that accept an optional Matplotlib `Axes` and explicit keyword arguments:
```python
plot_field(fields, "potential", ax=ax, unit="mV", clim=(-100, 100), zoom_nm=(5, 10))
plot_mesh(mesh_elements, ax=ax, show_wireframe=True, zoom_lumen=True)
plot_axial_cutline(fields, "potential", r=0.0, ax=ax)
plot_radial_cutline(fields, "potential", z_nm=0.0, ax=ax)
plot_iv(sweep_artefact, ax=ax, annotate_rectification=True)
```

---

### Area D: Marimo Reactivity and Notebook Structure (Amending Ruling P5)

1. **Use Store-Backed Execution (`only=False`)**
   - Remove `only=True` and all `assert run_prev.stages[-1].name == "..."` checks.
   - Let `nanopnp.io.store.Store` return cached upstream stages in $< 1\text{ ms}$.
2. **Add Cost-Guarded Marimo Controls**
   - Remove the top-level `scale = 1.5; interactive = False` setup cell.
   - Set `debounce=True` on all `mo.ui.slider` controls.
   - Connect live sliders to fast stages (`contour`) and post-solve plot views (cutline position `z_nm`, field selector dropdown, zoom window).
   - Wrap slow stage parameters (`solve`, `protonation`) in `.form()` so the solver runs only when the user clicks submit.
3. **Shorten Notebooks `05` and `06`**
   - Replace the 40+ stage-by-stage cells in `05-cylinder` and `06-2wcd` with concise workflows:
     - `05-cylinder`: Mesh $\to$ Solve $\to$ 1D Cutlines $\to$ $I\text{--}V$ Sweep.
     - `06-2wcd`: Orient $\to$ Contour $\to$ Mesh $\to$ Protonation $\to$ Solve and Cutlines.

---

## 4. Changes by Notebook

| Notebook | Current Problems | WP54 Changes |
| :--- | :--- | :--- |
| **`01-geometry`** (2WCD PDB to Mesh) | • Calls `os.chdir(example)`<br>• Loads `prepare.py` via `importlib`<br>• Uses dotted-string dicts<br>• Sets `only=True` | • Call `orient_pore(structure_file("2wcd.pdb.gz"), ...)`<br>• Build case with `Case.from_structure(...)`<br>• Add `mo.ui.slider(debounce=True)` for contour isolevel<br>• Show dual-view `mesh_figure` with $\lambda_D / 5$ scale bar |
| **`02-charge`** (2WCD Charge and Materials) | • Re-runs stages 1 through 6 in a setup cell<br>• Uses dotted strings for salt concentration<br>• Does not mark the operating point on material curves | • Reuse the shared notebook store so stages 1 through 6 hit cache<br>• Mark the active concentration on electrolyte correction curves<br>• Draw the $\chi = 0.5$ solid-fraction contour on `fields_figure` |
| **`03-solve`** (Cylinder ePNP-NS Solve) | • Calls CLI `main(["mesh", "cylinder", ...])`<br>• Plots potential in `V` without centering at 0<br>• Plots unsigned speed $|u|$<br>• Leaves 3 empty subplot slots | • Build case with `Case.cylinder(...)`<br>• Plot potential in `mV` with `CenteredNorm(vcenter=0.0)`<br>• Plot signed $u_z$ and zoomed lumen streamlines<br>• Plot 1D axial and radial cutlines with a live `z_nm` slider |
| **`04-sweep`** (Cylinder $I\text{--}V$ Sweep) | • Calls CLI `main(["mesh", "cylinder", ...])`<br>• Uses 30 lines of `yaml.safe_dump` and SHA-256 paths<br>• Writes files into `examples/03-iv-sweep/` | • Call `sweep(case, axis="boundary_conditions.bias_V", values=[...], origin=...).run()`<br>• Annotate rectification ratio $r(V)$ and Ohmic slope on `sweep_figure`<br>• Show summary metrics with `mo.ui.table(...)` |
| **`05-cylinder`** (End-to-End Cylinder) | • Repeats 373 lines from `03-solve` and `04-sweep`<br>• Uses 4 cells per stage with `only=True` assertions | • Condense into 4 sections with `Case.cylinder(...)`<br>• Gate bias and concentration changes with `.form()`<br>• Combine 2D field plots, 1D cutlines, and $I\text{--}V$ curve |
| **`06-2wcd`** (End-to-End 2WCD) | • Repeats 478 lines across 44 cells<br>• Monkeypatches `prepare.py`<br>• Writes 2.4 MB PDB and store files into `examples/07/` | • Group execution into 5 biophysical steps using the shared store<br>• Orient 2WCD with `orient_pore`<br>• Add interactive post-solve cutlines and field plots |

---

## 5. Planned Decisions for `wp54-notebooks-and-figures-revised.md`

| # | Decision | Choice | Rationale |
|---|---|---|---|
| **D1** | **Meshing, Pore Orientation, and Case Factories** | Export `nanopnp.mesh.mesh_cylinder` (layer 6), `nanopnp.structure.orient_pore` (layer 2, amending `FR-37`), and `Case.cylinder` / `Case.from_structure` (layer 14). Add lazy entries to `PUBLIC` and update `modularity-layering.yaml`. | Removes CLI subprocess calls, external script loading, and manual YAML files. Keeps `CaseDocument` unchanged and keeps `structure` free of solver backends (`VER-65`, `VER-72`). |
| **D2** | **In-Memory Sweeps** | Export `nanopnp.sweep.sweep(case, ...)` in `nanopnp.sweep` (layer 15). Accept an in-memory `Case` and return a `SweepArtefact`. Re-export lazily in `PUBLIC`. | Removes disk YAML setup while obeying `VER-61` (`sweep` $\to$ `pipeline` is a downward import). |
| **D3** | **Biophysical Plot Defaults** | Amend Ruling P9 and `FR-30`. Plot potential in `mV` with `CenteredNorm(vcenter=0.0)`. Plot signed axial velocity $u_z$ and zoomed lumen streamlines. Support log concentration scaling. Add $\chi = 0.5$ and $r_{\min}$ annotations. | Matches nanopore literature conventions. Prevents crashes on unipolar or zero-bias solves. Shows flow direction and EDL ion depletion. |
| **D4** | **1D Cutlines and `RunResult` Properties** | Interpolate 1D axial and radial cutlines (`plot_axial_cutline`, `plot_radial_cutline`) in `nanopnp.plot` from `SolutionFields` (`P2Nodes`). Add `current_nA`, `conductance_nS`, and `fields` on `RunResult`. | Avoids a second NGSolve `restored()` call. Masks non-fluid regions on radial slices automatically. Updates interactive cutline sliders in $< 5\text{ ms}$ (`VER-65`). |
| **D5** | **Dual-View Mesh Figure** | Update `mesh_figure` (amending Ruling P9) to show a full-domain panel and a zoomed lumen panel with element wireframes and a $\lambda_D / 5$ scale bar. | Makes both the reservoir geometry and the pore wall mesh legible. Visually verifies `NUM-30`. |
| **D6** | **Reactive Notebooks and Shared Store** | Amend Ruling P5. Remove `os.chdir(example)` and rebase relative paths in `Case.load`. Remove `only=True` checks. Share a gitignored `notebooks/.store` directory and use `debounce=True` and `.form()` on Marimo widgets. | Restores Marimo reactivity without triggering unintended multi-minute solves. Saves ~4.5 minutes of duplicate 2WCD work. Keeps `git status` clean. |

---

## 6. Verification Plan

1. **Tier 1 (`tests/tier1/test_figures.py`, `test_public_api.py`, `test_layering.py`, `test_backend_guard.py`)**
   - Test `mesh_cylinder`, `orient_pore`, `Case.cylinder`, `Case.from_structure`, and in-memory `sweep(...)`.
   - Test `mV` scaling, `CenteredNorm(vcenter=0.0)` on unipolar and zero-bias data, dual-view `mesh_figure`, and 1D axial and radial cutlines from `SolutionFields`.
   - Verify that `PUBLIC` matches `src/nanopnp/__init__.py` (`test_all_matches_public_table`) and that `import nanopnp` does not load `ngsolve`, `netgen`, `MDAnalysis`, or `numpy` (`VER-45`, `VER-72`).
   - Run `test_layering.py` (`VER-61`) and `test_backend_guard.py` (`VER-65`).
2. **Tier 2 (`tests/tier2/test_notebooks.py`)**
   - Run all 6 notebooks headlessly with `python notebook.py` using a module-scoped shared store fixture.
   - Verify that each process exits with code `0`, emits no warnings, and leaves `git status` clean.

---

## 7. Audit Constraints and Author Rulings (28 October 2026)

This section records the author rulings and codebase constraints verified during the audit.

### 7.1 Author Rulings on Specification Conflicts

1. **Ruling A1 (`orient_pore` vs. Phase 5 `FR-37`)**
   - Implement `nanopnp.structure.orient_pore` in WP54. Amend `FR-37` (`specification/03-requirements.md`) and `docs/plans/phase-4-polish-and-user-testing.md` so notebooks `01`, `02`, and `06` run directly from `2wcd.pdb.gz`.
2. **Ruling A2 (Notebook Reactivity vs. Ruling P5)**
   - Amend Ruling P5 (`specification/history/14-phase-4-amended-the-plotting-library-and-the-noteb.md`) to use `only=False`, `mo.ui.slider(debounce=True)` on fast stages and post-solve views, and `.form()` on expensive solves.
3. **Ruling A3 (`Case.cylinder` vs. `IF-02` Case Schema)**
   - Keep the `CaseDocument` YAML schema unchanged. `Case.cylinder(...)` generates the mesh file in the `Store` (`store.root / "meshes"`, keyed by parameter hash) via `mesh_cylinder` and sets `inputs.mesh.path`.
4. **Ruling A4 (Stage Figures and 1D Cutlines vs. Ruling P9 and `FR-30`)**
   - Amend Ruling P9 and `FR-30` to use `mV` potential with `CenteredNorm(vcenter=0.0)`, a dual-view `mesh_figure` with a $\lambda_D / 5$ bar, and lumen streamlines in `solve_figure`. Export `plot_axial_cutline` and `plot_radial_cutline` in `nanopnp.plot`.

### 7.2 Codebase Correctness Constraints (C1–C9)

- **C1 (`CenteredNorm` Instead of `TwoSlopeNorm`):** `matplotlib.colors.TwoSlopeNorm(vmin=min(0.0, vmin_data), vcenter=0.0, vmax=max(0.0, vmax_data))` raises `ValueError` whenever `vmin_data >= 0` or `vmax_data <= 0` because `vmin` or `vmax` equals `vcenter=0.0`. Use `matplotlib.colors.CenteredNorm(vcenter=0.0, halfrange=max(abs(vmin_data), abs(vmax_data), 1e-12))`. Update both `DISPLAY["potential"]` in `src/nanopnp/plot/data.py` and the `("potential", ..., "V", 1.0, "RdBu_r")` tuple in `src/nanopnp/plot/figures.py:solve_figure`.
- **C2 (`Case.cylinder` Parameters):** In `CylindricalPoreGeometry` (`src/nanopnp/mesh/primitives.py`), the pore lumen length equals `membrane_thickness_nm`. Do not add a separate `length_nm` parameter. Accept `pore_radius_nm`, `membrane_thickness_nm`, `reservoir_radius_nm: float | None = None`, and `surface_charge_C_m2: float | None = None`. Set `inputs.mesh.groups` to `{"default": "interface"}`.
- **C3 (Path Rebasing in `Case.load`):** `load_case` (`src/nanopnp/pipeline/case.py`) does not rebase relative paths in `CaseDocument`. Update `Case.load(path, store=...)` to resolve relative `inputs.*.path` and `structure.source.path` entries against `Path(path).resolve().parent`.
- **C4 (In-Memory `sweep` Types):** In `SweepDocument.Axis` (`src/nanopnp/sweep/document.py`), `origin: int = 0` is a 0-based integer index into `values`. `sweep(...).run()` returns a `SweepArtefact` (`src/nanopnp/io/artefact.py`). Update `SweepPlan` (`src/nanopnp/sweep/plan.py`) to accept an in-memory `CaseDocument` and compute `base_case_sha256` from `CaseArtefact(base_document).hash` when `base_path` is not on disk.
- **C5 (`orient_pore` Signature and `structure_file`):** Omit the unused `point_group` argument from `orient_pore`. Use `"all"` or comma-separated chain names (`"A,B,C,..."`) matching `nanopnp.io.resolved.parse_chains`. Import `numpy` and `MDAnalysis` lazily inside `orient_pore` (`VER-72`). Use `nanopnp.core.paths.structure_file("2wcd.pdb.gz")` instead of creating a new `nanopnp.data` package (`VER-61`).
- **C6 (`RunResult` Properties and Stage 11 `qoi`):** Stage 11 (`qoi`) populates `result.quantities`, whereas stage 10 (`solve`) leaves `result.quantities` empty. `RunResult.current_nA` must read `quantities["current_A"] * 1e9` and raise a clear error if stage `qoi` has not run. `RunResult.conductance_nS` must return `None` when `bias_V == 0.0`. `RunResult.fields` must import `nanopnp.plot.data.solution_fields` lazily inside the property to use the existing `pipeline -> plot` string edge in `modularity-layering.yaml`.
- **C7 (Stage 7 Solid Fraction $\chi = 0.5$):** Stage 7 writes the solid fraction $\chi \in [0, 1]$ (`SOLID_FRACTION` in `src/nanopnp/charge/dielectric.py`) to `eps_r.npz`, not the relative permittivity $\varepsilon_r$. Draw the boundary contour at $\chi = 0.5$ on `fields_figure`.
- **C8 (`PUBLIC`, `__init__.py`, and `modularity-layering.yaml`):** For every symbol added to `PUBLIC` in `src/nanopnp/core/public.py` (`mesh_cylinder`, `orient_pore`, `sweep`), add a matching `if TYPE_CHECKING:` import and `__all__` entry in `src/nanopnp/__init__.py`. Record the new `static` edges (`{from: nanopnp, to: mesh}`, `{from: nanopnp, to: structure}`) and `string` edges (`{from: core, to: mesh}`, `{from: core, to: structure}`) in `docs/project/modularity-layering.yaml`.
- **C9 (Debye Scale Bar on Supplied Meshes):** In `mesh_figure(artefact, inputs=None)`, `artefact.summary["sizing"]` is `None` for supplied meshes (`inputs.mesh`). Read $\lambda_D / 5$ from `case_debye_record(inputs.resolved)` when `inputs` is present, fall back to `artefact.summary.get("sizing")`, and omit the scale bar when neither value is available.

### 7.3 Efficiency Constraints (E1–E4)

- **E1 (Single Finite-Element Restore):** Do not call `nanopnp.post.export.restored(inputs, artefact)` a second time to compute 1D cutlines. Evaluate axial and radial cutlines in `nanopnp.plot` directly from `SolutionFields` (`P2Nodes`) using `matplotlib.tri.LinearTriInterpolator`. Interpolating on `fields.fluid` also masks solid regions ($r > r_{\text{wall}}(z)$) automatically and completes in $< 5\text{ ms}$.
- **E2 (Shared Store Across `01`, `02`, and `06`):** Share one gitignored store (`notebooks/.store` or `$NANOPNP_STORE`) across all notebooks and use a module-scoped store fixture in `tests/tier2/test_notebooks.py`. This reuses stages 1 through 8 on 2WCD and saves ~4.5 minutes in interactive and CI runs.
- **E3 (Debounced and Form-Gated Widgets):** Pass `debounce=True` to all `mo.ui.slider` widgets. Attach live sliders only to fast stages (`contour`) or post-solve views (cutline `z_nm`, field selector, zoom window). Gate slow stages (`solve`, `protonation`) behind `.form()`.
- **E4 (Zoomed-Lumen Streamplot Grid):** Compute and draw `ax.streamplot` only inside the zoomed lumen bounds ($r \in [0, r_{\text{zoom}}], z \in [-z_{\text{zoom}}, z_{\text{zoom}}]$) on a $60 \times 120$ grid interpolated from `fields.fluid`.

# Software stack — libraries, versions, licences, gotchas

Verified August 2026 against PyPI, project docs and, where marked **[tested]**, by installing and
running the library. Re-verify versions before relying on them; the *facts about behaviour* age
more slowly than the version numbers.

---

## 1. FEM backend — NGSolve/Netgen

**Chosen backend.** `ngsolve` / `netgen-mesher` **6.2.2606** (29 Jun 2026), **LGPL-2.1-only**.

| Fact | Value |
|---|---|
| Wheels | cp310–cp314, all three OSes. win_amd64 14.6 MB, macOS universal2 44.0 MB **[tested]** |
| Compiler at runtime | **not needed** — forms are evaluated by the compiled C++ core. `Compile(realcompile=True)` is opt-in and *does* need one |
| Mixed spaces | `X = V*Q` product spaces; Taylor–Hood directly |
| Newton | `ngsolve.solvers.Newton(a, gfu, dampfactor=...)`, symbolic differentiation for the Jacobian **[tested]** |
| Axisymmetric | one-liner: `... * x * dx` where `x` is the radial coordinate. Natural but **undocumented** |
| Rendering | `ngsolve.webgui` / `netgen.webgui`; `WebGLScene.GenerateHTML()` makes it embeddable **[tested]** |
| Meshing | Netgen built in, with OpenCASCADE geometry — no external mesher needed |
| API stability | remarkably stable for a decade |

**Known limitations, both verified:**

1. **No MPI in the wheels** — no MPI symbols in any shipped `.so`, no mpi4py **[tested]**. Parallel
   mesh generation, parallel adaptive refinement and parallel multigrid are documented as
   unsupported. Irrelevant for 2D axisymmetric v1 (direct solves; sweeps parallelise at job level);
   becomes real in 3D. Mitigations: ngsPETSc, or a DOLFINx backend for HPC only.
2. **No MUMPS/PARDISO/HYPRE/MKL in the wheels** — `ngsolve.config` reports all False **[tested]**.
   See `06-numerics-fem.md` §6.
3. **2D boundary layers are immature.** Python API is
   `netgen.meshing.Mesh.BoundaryLayer2(domain, thicknesses, make_new_domain=True, boundaries=[])`
   (binding C++ `GenerateBoundaryLayer2`). The forum carries an unresolved Aug 2024 report of the
   generator failing to fill a zone adjacent to the new advancing front. Separately, the *3D*
   `Mesh.BoundaryLayer` now unconditionally raises *"Call syntax has changed! Pass a list of
   BoundaryLayerParameters to the GenerateMesh call instead"* — a trap when porting 2D code to 3D.

### 1.1 Why not the alternatives

| | Verdict |
|---|---|
| **DOLFINx 0.11.0** (9 Jun 2026, LGPL-3) | Best numerics, best docs, PETSc SNES, `MixedFunctionSpace`/`extract_blocks` for fieldsplit. **But it JIT-compiles.** README verbatim: *"PETSc and petsc4py are not available on Windows. Because FEniCS uses just-in-time compilation it necessary to install [Microsoft Visual Studio]"*. Structurally cannot become a double-clickable app. API breaks every ~8.5 months on average (0.8 Apr 2024 retired legacy `ufl.FiniteElement`; 0.9 Oct 2024 `Function.vector`→`Function.x.petsc_vec`; 0.10 Oct 2025 `io.gmshio`→`io.gmsh`). |
| **Firedrake 2026.4.x** (LGPL-3) | Excellent solver composition; **EchemFEM** already exists on it. No native Windows, no binary wheels, PETSc from source. Disqualified by the desktop requirement. |
| **scikit-fem 12.0.2** (BSD-3, 0.178 MB wheel) | Trivially bundleable, but you hand-roll Newton, block assembly, preconditioning, stabilisation; MPI is token. Good for prototyping. |
| **SfePy 2026.2** (BSD-3) | Genuinely permissive, covers coupled multi-field, but PyPI ships **sdist only**, parallel is self-described WIP, effectively single-maintainer. Weakest 5-year bet. |
| **PyMFEM 4.8 / deal.II** | No symbolic language, no AD — hand-coded Jacobian integrators for a five-field system. Non-starter. |

**The decisive argument:** choosing DOLFINx or Firedrake means needing a *second* backend for the
desktop app anyway, i.e. writing and maintaining the ePNP-NS weak forms twice, forever.

### 1.2 Prior art worth mining

| Project | Framework | Licence | Status | Use |
|---|---|---|---|---|
| **LLNL/echemfem** | Firedrake | **MIT** | active, JOSS 2024 | Best reference for SUPG-stabilised Nernst–Planck, GMPNP finite-size effects, NS/NS-Brinkman flow. No axisymmetric support. |
| **mitschabaude/nanopores** | FEniCS 2016.2, **Python 2** | MIT | dormant | *The* PNP–Stokes nanopore paper (JCP 338:452, 2017). Mine the goal-oriented adaptivity and molecule-in-pore approach. **Do not try to run it.** |
| pdelab/PyPNP | legacy dolfin | GPL-3 | dormant | No — dead API + GPL. |
| CINPLA/KNPsim | legacy FEniCS | GPL-3 | dormant | Electroneutral KNP, no flow. |
| divyabohra/GMPNP | legacy FEniCS | research artifact | dormant | 1D/3D GMPNP reference only. |
| mrshariati/FEMCorrosionSimulation | legacy FEniCS | research artifact | ~2021 | AFC/FCT flux-corrected PNP stabilisation reference. |

---

## 2. Structure, trajectory and density

| Tool | Version | Licence | Notes |
|---|---|---|---|
| **MDAnalysis** | 2.10.0 | LGPLv3+ | PDB/mmCIF, DCD/XTC/TRR/NCDF; `analysis.align.AlignTraj`, `rotation_matrix` **[tested]** |
| MDTraj | 1.11.1 | LGPLv2.1+ | Faster I/O, leaner; no density-on-grid |
| **GridDataFormats** | 1.2.0 | LGPL | OpenDX/CCP4 I/O; `Density` subclasses `gridData.core.Grid` |
| mdahole2 (MDAKit) | current | GPL-ish + HOLE binary academic licence | Pore-radius profile — use to *validate* the contour |
| PDBFixer / Modeller | — | MIT / academic | Fill missing loops **before** anything else |

**`DensityAnalysis` is histogram-only** (`np.histogramdd`), no kernel option **[tested]**. The
paper's per-atom VdW-weighted Gaussian must be written by hand. Do **not** substitute "histogram
then `gaussian_filter`" — uniform post-smoothing rounds the constriction, whereas VdW-weighted
smearing preserves the exclusion surface.

**gridData 1.2.0, as it actually behaves [tested].** Three things a reader of the docs would not
predict, all found while building the `(r, z)` grid IO:

- **There is no `CCP4` writer.** `file_format="ccp4"` raises `ValueError: File format CCP4 not
  available, choose one of dict_keys(['DX', 'PKL', 'PICKLE', 'PYTHON', 'VDB', 'MRC'])`. Its `MRC`
  writer *is* the CCP4-2000 map format and accepts a `.ccp4` filename, so route `.ccp4` and `.map`
  to `MRC` and say so.
- **MRC stores float32.** A round trip through it is therefore not bit-exact and changes any content
  hash taken over the values. Record that rather than hide it; `.npz` stays the native format.
- **A 2D array fails inside the writer, not at its door.** `Grid(values_2d, ...).export(...)` raises
  `TypeError: not enough arguments for format string` from inside the DX writer. Write a `(r, z)`
  grid as a 3D grid whose third axis is a **singleton**: gridData round-trips `(4, 3, 1)` through
  both DX and MRC with `origin` and `delta` intact. Refuse a genuinely 2D array yourself, naming the
  shape, so the user gets a diagnostic instead of a format-string traceback.

**The MRC writer is not in every gridData a supported interpreter resolves to [tested].**
GridDataFormats 1.2.0 requires Python ≥ 3.11, so on 3.10 a resolver takes **1.0.2**, whose
`Grid()._exporters` registry is `DX, PKL, PICKLE, PYTHON` — no `MRC` and no `VDB`. Its `_loaders`
registry *does* carry `CCP4, DX, MRC, PLT, PKL, PICKLE, PYTHON`, and `gridData.mrc` imports on both,
so **reading** MRC and CCP4 works on 1.0.2 and only **writing** them does not. Measured by running
each version: `griddataformats==1.0.2` on 3.10 exports a `(4, 3, 1)` grid to DX and refuses MRC with
`ValueError: File format MRC not available`; 1.2.0 on 3.12 does both.

Two consequences for anything that writes these formats across a 3.10–3.14 matrix:

- `hasattr(gridData, "mrc")` and the module version are both **the wrong capability test** — the
  first is true on 1.0.2 and the second is a proxy. `Grid()._exporters` is the registry
  `Grid.export` itself looks the format up in, so it is the only authoritative answer. It is
  private; guard the read and fall back to translating the `ValueError`.
- A test guarded on "is gridData importable?" passes on 3.10 and then fails inside the writer. Guard
  on **writer availability** and assert the refusal on the other branch, so both interpreters
  assert something rather than one of them skipping.

**Symmetry-axis detection:** do not use raw principal axes. ClyA is a truncated cone; the inertia
tensor's axes are near-degenerate and drift between frames. Use **chain-permutation
superposition** — superpose chain A onto chain B; the resulting rotation's eigenvector with
eigenvalue 1 *is* the Cₙ axis. ~40 lines, markedly more stable.

---

## 3. Charge and electrostatics

| Tool | Version | Licence | Notes |
|---|---|---|---|
| **PDB2PQR** | 3.7.1 (Dec 2024) | BSD-3 | Python API `pdb2pqr.main`. Produces protonated structure **+ per-atom partial charges + radii** |
| PROPKA3 | 3.5.1 | LGPL-2.1 | pKa only; shipped as a PDB2PQR dependency |
| **APBS** | 3.4.1 | BSD-3 | Poisson–Boltzmann cross-check. Driven by input files; read `.dx` with `gridData`. `apbs-binary` pip wrapper exists |
| pKAI / pKa-ANI / PypKa | — | MIT / — / LGPL-3 + proprietary DelPhi | ML or PB pKa. Not integrated with PDB2PQR |

**Verified CLI facts [tested]:** `--ff`, `--ffout`, `--with-ph`, `--titration-state-method`,
`--drop-water`, `--keep-chain` all exist; `CHARMM`, `AMBER`, `PARSE` are valid force fields.
**`--titration-state-method` accepts `propka` ONLY** — `pkaani` is rejected by argparse. ML pKa
predictors must be run separately and their states applied by hand.

PDB2PQR ignores PROPKA's `chains` option (relevant for homo-oligomeric pores) but *does* log a
warning — surface it rather than swallowing it.

APBS keywords for the cross-check: `chgm` ∈ {spl0, spl2, **spl4**} (spl4 = quintic B-spline,
least grid-sensitive); `srfm` ∈ {mol, **smol**, spl2, spl4}. Note `spl2`/`spl4` surfaces "may
produce unphysical results at non-zero ionic strengths" — run the cross-check at **zero** ionic
strength, which also isolates charge-projection error from model differences.

---

## 4. Geometry, meshing and I/O

| Tool | Version | Licence | Verdict |
|---|---|---|---|
| **Netgen OCC** (`netgen.occ`) | 6.2.2606 | LGPL-2.1 | **Default.** Same OpenCASCADE kernel, in-process, no extra binary, no GPL exposure |
| **Gmsh** (Python API) | 4.15.2 | **GPLv2+** | Optional backend. Best-in-class: `BoundaryLayer` (works in 2D), `Distance`/`Threshold`, `Min`/`Restrict` field algebra, `Fan` points, quads-in-BL |
| **scikit-image** | 0.26.0 | BSD-3 | `measure.find_contours` (sub-pixel marching squares), `marching_cubes` |
| **Shapely** | 2.1.2 | BSD-3 | `LinearRing`, `is_valid`, `is_simple`, `make_valid`, `simplify`, `buffer` |
| **meshio** | 5.3.5 | MIT | Reliable but last release 2024-01 — treat as stable-frozen |
| CadQuery / build123d | — | Apache-2.0 | 3D-solid-centric; overkill for a 2D (r,z) region |
| pythonocc-core | — | LGPLv3 | Raw OCCT; only for BRep edge cases |

**Avoid:** MeshPy — actively maintained (2026.1) but wraps **Triangle**, whose licence states
distribution as part of a commercial system is *"permissible ONLY BY DIRECT ARRANGEMENT WITH THE
AUTHOR"*, and **TetGen 1.5** (AGPLv3). Also avoid **pygmsh** (last release 2022-01) and
**pygalmesh** (2022-09), both stale — call the `gmsh` API directly instead.

**Shapely offsetting:** `parallel_offset` is *not* removed and emits *no* DeprecationWarning in
2.1.2 **[tested]**, but its docstring marks it legacy in favour of `offset_curve` (different
sign/`quad_segs` convention). For a closed contour, `buffer(-d)` is more robust than either.

**Keep MSH 4.1 as the archival interchange format** — physical groups survive round-trips there
and get mangled in some VTU paths.

**Netgen's own `.vol` round-trips boundary and material names [tested].** `mesh.ngmesh.Save(path)`
followed by `ngsolve.Mesh(path)` returns `GetMaterials()` and `GetBoundaries()` unchanged, so a
mesh written by one process and solved by another keeps the vocabulary the essential conditions and
the `definedon` restrictions are written against. Measured on a `CylindricalPoreGeometry` at
`maxh = 4 nm`: materials `['electrolyte', 'membrane', 'cis', 'trans']` and boundaries `['axis',
'cis', 'default', 'membrane', 'membrane_outer', 'trans', 'wall']` on both sides of the write. This
is what makes an externally supplied mesh usable at all — a format that dropped the names would
apply every essential condition to nothing and converge to the wrong problem in silence, so a
release that reads a mesh from a case file must restrict itself to formats that carry them.

**Netgen's own reader is an MSH 2.2 parser and cannot read the archival format [tested].**
`netgen.read_gmsh.ReadGmsh` handed a 4.1 file dies inside `int()` on the entity-block header, so the
reader for the format IF-06 mandates cannot be the one netgen ships. `meshio` is therefore not
optional bookkeeping — it is the only route in. CON-10 keeps `gmsh` itself off the default path for
an unrelated reason (GPLv2+), and the two constraints agree.

**meshio 5.3.5's MSH 4.1 writer gets entity bookkeeping wrong in two ways, both silent [tested].**

- *One cell block is one entity.* `_write_elements` takes the **first** `gmsh:geometrical` tag of a
  block and writes the whole block under it. Four boundary groups packed into a single `line` block
  come back with all four physical tags equal to the first — three no-flux walls silently becoming
  one. Cure: emit one cell block per (group, element type).
- *An entity that owns no node is never written.* `_write_entities` builds `$Entities` from
  `np.unique(point_data["gmsh:dim_tags"])` alone, so an entity a cell block references but no node
  claims is omitted, and reading the file back raises `KeyError` — after the write reported success.
  Cure: assign each node its lowest-dimensional entity, then repair any group left with none.

**`meshio.Mesh.field_data` is keyed by name, so it cannot carry the same name in two dimensions
[tested].** The §5.3.1 vocabulary uses `cis`, `trans`, `membrane` and `analyte` as both a domain name
and a boundary name, which is exactly the collision. Read `$PhysicalNames` off the file and key it
`(dimension, tag)` instead.

**A round trip through MSH 4.1 permutes both nodes and cells [tested]**, because meshio's reader
returns nodes grouped by entity and cell blocks in entity order. A content hash taken over the arrays
in file order would therefore make a mesh differ from itself. Hash a canonical form: vertices sorted
by `(r, z)`, connectivity renumbered into that order, elements sorted by group name — invariant under
everything the round trip does, and changing the moment an edge moves group.

**netgen.occ facts, all measured on 6.2.2606 [tested]:**

- **A clockwise wire gives OCC a face of negative area, and a negative face subtracts as an
  addition.** With the delivered ClyA table's own orientation (signed area −26.4939 nm²),
  `disc - quad` returns the disc split in two rather than the disc with a hole, and `quad * disc`
  returns nothing at all. Fix the orientation once, where the face is built.
- **`Glue` is conformal and `Compound` is not.** `occ.Glue([a, b])` meshes with one node chain per
  seam; `occ.Compound([a, b])` meshes with two coincident chains. On two unit rectangles sharing
  the edge `x = 1`, meshed at `maxh = 0.5`: glue gives 13 points, 13 of them distinct, 3 on the seam;
  compound gives 16 points, still 13 distinct, 6 on the seam. Two chains agree to the last digit on
  coordinates, so only a mesh-level check catches it, and what it costs is a potential free to jump
  across the seam with nothing raising.
- **`edge.center` is the centre of mass, and for an arc it lies off the curve.** A
  classify-by-centre chain works for straight edges and silently misplaces every curved one. Use
  `edge.parameter_interval` with `edge.Value(t)` to get a point that is actually on the edge.
- **`edge.faces` is empty.** Traversal is downward only, so an edge cannot be named by which faces
  adjoin it; classify by geometry instead.
- **`Circle(...).Face()` is one closed edge with a seam at parameter zero**, and the seam survives
  a boolean clip as an ordinary vertex. A half-disc of radius 250 clipped to `r ≥ 0` carries a vertex
  at `(250, 0)` that splits whatever arc segment spans it.
- **A boolean on shapes returns a compound.** `.mass` and `.name` on the result raise
  `NgException: Cannot query properties of compound shapes`; read them off `list(shape.faces)[0]`.
- **The mesh netgen generates is not bit-reproducible across platforms.**
  `CylindricalPoreGeometry(2.0, 13.0, 50.0)` at `maxh = 2.0 nm`, `wall_h = 0.05 nm` meshes to
  **8141 triangles on Linux and macOS and 8147 on Windows** — same version, same options, a drift
  of 0.07 %. The advancing front takes its decisions on floating-point comparisons, and the
  compiler decides those. So an element count, or a minimum element quality read to four decimals,
  is a property of the *build* and not of the geometry: assert a band on either, and keep exact
  check values for figures computed in closed form on hand-built elements. The three smaller
  phase-0 geometries (192, 811 and 124 elements) do agree exactly across all three platforms,
  which is what makes this easy to miss until a mesh is large enough to have a choice to make.

---

## 5. GUI and packaging

| Tool | Licence | Note |
|---|---|---|
| **PySide6** 6.11.1 | LGPL-3 OR GPL-2 OR GPL-3 | **Use this.** LGPL option means no licence conflict |
| PyQt6 | **GPL-3 only** | Avoid unless the project is GPL |
| `PySide6.QtWebEngineWidgets.QWebEngineView` | — | Hosts NGSolve webgui **[tested]**. The earlier "imports cleanly" held on a machine with the GL libraries present; see the caveat below, which is a property of the machine and not of the wheel |
| PyInstaller | — | **Chosen** for the bundle, one-dir (ADR-004, amended 20 September 2026). `collect_all` over `ngsolve`, `netgen` and `ngsolve_openblas`, plus the `netgen-occt` libraries collected by hand (below); `upx=False`, which mangles Qt WebEngine's helper executable |
| briefcase / conda-constructor | — | The other two candidates; not used |

### PySide6 imports are a system-library question, not a wheel question **[tested]**

Measured 20 September 2026, PySide6 6.11.2, in the Linux development container:

```
from PySide6 import QtWidgets            -> ImportError: libEGL.so.1: cannot open shared object file
from PySide6 import QtWebEngineWidgets   -> ImportError: libEGL.so.1: cannot open shared object file
```

`QtWidgets` itself, not only WebEngine. The wheel installs perfectly and `import PySide6` succeeds;
a GL-dependent payload then dlopens and fails. This is the same failure class the gmsh wheel has
(`OSError: libGLU.so.1`, handled at `tests/tier1/test_mesh_quality.py`), which is why the skip idiom
for either is `except (ImportError, OSError)` and never `pytest.importorskip`.

Consequence for testing a GUI: anything that must run on the push gate has to be Qt-free. Widget
construction belongs on the `windows-latest` and `macos-latest` matrix jobs, where Qt's platform
plugin works unaided and `QT_QPA_PLATFORM=offscreen` is all that is needed. Installing system
packages on a Linux gate job to work around this buys Linux coverage at the price of a portability
promise per runner image.

### A missing `libEGL.so.1` can be shimmed for local work, never for the gate **[tested]**

Measured 20 September 2026. The pre-installed Playwright Chromium carries a real
`libEGL.so`, and symlinking it as `libEGL.so.1` (with `libGLESv2.so` as `libGLESv2.so.2`) into a
scratch directory on `LD_LIBRARY_PATH` makes `from PySide6 import QtWidgets` succeed, a
`QApplication` construct under `QT_QPA_PLATFORM=offscreen`, and the whole Qt widget suite run.
Useful for checking widget code that would otherwise ship having never been executed.

It is **not** a way to get Linux widget coverage on the push gate. It depends on a browser bundle
that has nothing to do with this project, and CON-07's posture is that nothing on the user path
needs a build or an install step. Widget coverage belongs on `windows-latest` and `macos-latest`,
where Qt's platform plugin works unaided.

### `QWebEngineView` loads a webgui document with no GPU at all **[tested]**

Measured 20 September 2026, PySide6 6.11.2, Linux, no display and no GPU, with
`QT_QPA_PLATFORM=offscreen` and `QTWEBENGINE_CHROMIUM_FLAGS=--disable-gpu --no-sandbox`. Qt logs

```
QRhiGles2: Failed to create temporary context
Failed to create RHI for backend: OpenGL
```

and then reaches `loadFinished(True)` anyway. So a headless packaging check *can* wait for the
document load rather than merely constructing the view.

What it does not establish is that the scene **rendered**. `WebGLScene.GenerateHTML()` emits a
document that fetches its renderer from `https://cdn.jsdelivr.net/npm/webgui@<version>/dist/webgui.js`,
so on a machine with no network the page loads and the console says `webgui is not defined`.
`loadFinished` is a statement about the document, not about the picture.

### A webgui scene is JSON, costs ~200–320 B per element, and needs no Jupyter **[tested]**

Measured 21 September 2026, P2 `GridFunction` on a unit-square mesh,
`Draw(gf, mesh, order=k, show=False).GetData()` then `json.dumps`:

| elements | order | `GetData` | JSON | per element |
|---|---|---|---|---|
| 224 | 1 | 3.0 ms | 0.045 MB | 202 B |
| 224 | 2 | 2.3 ms | 0.075 MB | 334 B |
| 2,550 | 1 | 15.7 ms | 0.496 MB | 194 B |
| 2,550 | 2 | 25.4 ms | 0.825 MB | 324 B |
| 16,036 | 1 | 157.9 ms | 3.094 MB | 193 B |
| 16,036 | 2 | 142.6 ms | 5.153 MB | 321 B |

Linear in elements to within 5 %. Extrapolated to the 120,917-triangle reference mesh that is
**23.3 MB at order 1 and 38.8 MB at order 2**, built in roughly 1.2 s. A scene of a production mesh
is therefore a file, not a queue payload and not a `setHtml` argument — `QWebEngineView.setHtml`
percent-encodes into a data URL.

`GetData()` runs headlessly and **without `anywidget`**: `netgen.webgui` defines `WebGuiWidget`
inside a `try: import anywidget` and falls back to a stub with the same constructor
(`netgen/webgui.py:423–435`), so `WebGLScene.__init__` succeeds with no Jupyter stack present.
The returned dict is plain numbers and base64 strings, so it crosses a process boundary and
serialises without help.

### `netgen.webgui.GenerateHTML` ignores its `template` argument **[verified]**

Read from the installed source, 21 September 2026:

```text
def GenerateHTML(data, filename=None, template=None):
    if template is None:
        template = _html_template
    ...
    html = _html_template.replace('{render}', jscode)
```

`template` is assigned and never read; the substitution is always into the module global. So a
caller cannot redirect the renderer `<script src=…>` by passing a template, and anything that
needs a different renderer source has to build the host document itself. The document is four lines
plus the render data, so that is cheap — but it is not optional.

The renderer itself is npm `webgui`, `"license": "LGPL-2.1-or-later"`, 1,206,946 B unpacked for
version 0.2.39 (npm registry metadata, **[verified]**). Redistributing it inside a bundle is
permitted and is the only way a packaged application draws a field offline; it is a new
redistributed work and belongs in the licence notice if it is shipped. `cdn.jsdelivr.net` is
blocked from this development container (proxy 403), so the file has to be fetched elsewhere and
checked against the integrity hash npm publishes.

### A webgui scene draws on a material *region*, not only on a whole mesh **[tested]**

Measured 21 September 2026 on a restored four-material ePNP-NS solution, 124 triangles.
`Draw(cf, mesh.Materials("electrolyte|cis|trans"), show=False, order=2).GetData()` succeeds and
returns a smaller scene than the whole-mesh draw of the same field (30.5 kB against 43.1 kB here),
because it carries only the retained elements.

That matters for honesty rather than for size. A field declared on the fluid alone evaluates to
zero inside the membrane, and a whole-mesh draw of a concentration therefore paints a zero *inside
a wall* that a reader cannot distinguish from a converged depletion — which is the same trap
`io/fields.py` documents for the IF-07 export, and it is avoided the same way.

The same call draws a **two-component vector** field without special handling: all five fields of
the `epnp-ns` family (the potential, two concentrations, the velocity and the pressure) produce a
scene from one code path, the vector one costing about 1.5x the scalars.

### `QWebEngineView` can be constructed in this container with the Playwright GL shim **[tested]**

Measured 21 September 2026. With `libEGL.so.1` and `libGLESv2.so.2` symlinked from
`/opt/pw-browsers/chromium-*/chrome-linux/` onto `LD_LIBRARY_PATH`, and
`QT_QPA_PLATFORM=offscreen`, both `from PySide6 import QtWidgets` and
`from PySide6.QtWebEngineWidgets import QWebEngineView` succeed and the whole Tier-1 widget suite
runs — including a `QPainter` repaint into a `QPixmap` and a `QWebEngineView` construction.

This is the §5 shim recorded above, used for the purpose that section already states: checking
widget code that would otherwise ship having never been executed. It stays off the push gate, where
widget coverage remains `windows-latest` and `macos-latest`.

### A PyInstaller bundle carries neither OCCT nor OpenBLAS unless told to **[tested]**

Measured 22 September 2026: PyInstaller 6.22.3, contrib hooks 2026.7, NGSolve and Netgen
6.2.2606, `netgen-occt` 7.8.1, `ngsolve-openblas` 0.3.33. The Windows build log and a Linux
rebuild of the same recipe in this container agree.

**OCCT.** `import netgen` runs `netgen.load_occ_libs()`, which does three things in order:

1. calls `importlib.metadata.metadata("netgen-occt")`;
2. builds a stem-to-path map from `metadata.files("netgen-occt")`;
3. `ctypes.CDLL`s 28 `TK*` libraries in dependency order, starting with `lib_paths["tkernel"]`.

The `netgen-occt` wheel installs those libraries **outside site-packages**, through its `.data/data`
scheme: `bin/TK*.dll` at the environment root on Windows, and `lib/libTK*.so.7.8.1` on Linux. So
its RECORD names them `../../bin/TKernel.dll`, relative to the dist-info's parent. A one-dir
bundle then fails twice, independently:

- **PyInstaller does not find the libraries.** The build log carries `Library not found: could not
  resolve 'TKernel.dll', dependency of ...\netgen\nglib.dll` for every one of them. `collect_all`
  cannot help, because they belong to no importable package.
- **PyInstaller does collect the dist-info.** So `metadata()` succeeds, and the
  `PackageNotFoundError` no-op branch is not taken. But since Python 3.12, `Distribution.files`
  filters its result through `skip_missing_files`, and from `_internal/` every `../../` entry
  points outside the bundle. The map comes back **empty**, and the first lookup raises
  `KeyError: 'tkernel'`. That is the exact failure of the gated `bundle` job, before any Qt is
  touched.

**The fix makes netgen's own loader work unchanged** (`packaging/nanopnp-probe.spec`):

- collect the existing `netgen-occt` files that match its filter (`*libTK*` or `*.dll`) into the
  bundle root;
- replace the collected dist-info with one whose RECORD names them by bare file name.

**OpenBLAS.** `ngsolve/__init__.py` imports `ngsolve_openblas` and preloads the libraries it
ships as package data. Static analysis collects the module but not the libraries, so the frozen
`import ngsolve` fails with `libopenblas.so.0: cannot open shared object file`.
`collect_all("ngsolve_openblas")` carries them. There is no macOS wheel, and `ngsolve` does not
import it there.

With both fixes, the probe bundle built here runs `--selftest` to completion on Linux under the §5
GL shim. The unresolved-library warnings that remain in the build log are `libopenblas.so.0` and
the optional CUDA libraries of `_ngscuda.so`. The first is satisfied at run time by the preload;
the second is never loaded unless a CUDA solver is asked for.

### `nanopnp.io.case` pulls in neither NGSolve nor NumPy, and costs 250–350 ms **[tested]**

Measured 20 September 2026 on the development interpreter (3.12). After `import nanopnp.io.case`,
`"ngsolve" in sys.modules` and `"numpy" in sys.modules` are both `False`. The cost is pydantic and
PyYAML building the `nanopnp/case/v1` model tree, paid once.

So a caller can enumerate, display and validate an entire case document without the solver — which
is what lets a schema-generated editor stay near the CLI's 56 ms stage-introspection budget in
spirit, with NGSolve imported only in whatever process actually solves. Note that `io/case.py` does
import `nanopnp.physics.models` at module scope for its registry check; that module defers its own
NGSolve import, which is why the claim above holds.

**Re-measured 20 September 2026 on an idle container: 349 ms cold (no `__pycache__`), 253 ms warm**,
against the 622 ms first recorded the same day. Neither cache state reproduces 622 ms here, so that
figure was taken under load or by a different method. **Treat the absolute number as
machine-dependent and the ratio as the fact**: importing the case schema costs roughly what one
NGSolve import (~370 ms) costs, and the load-bearing half — neither `ngsolve` nor `numpy` in
`sys.modules` afterwards — is re-confirmed and is not a timing claim at all.

### The desktop shell's view-model layer costs what the schema costs **[tested]**

Measured 20 September 2026, best of three on an idle container, warm cache:

| Module | Cost | What it pulls in |
|---|---|---|
| `nanopnp.io.case` | 253 ms | pydantic and PyYAML building the `nanopnp/case/v1` model tree |
| `nanopnp.gui.case_model` | 251 ms | the above, and about a millisecond of its own |
| `nanopnp.gui.run_model` | 273 ms | the above, plus `io/manifest.py` and `io/run.py` |
| `nanopnp.gui.solver` | 73 ms | `cli/errors.py` and `multiprocessing`; everything else is deferred into the child |
| `nanopnp.gui.probe` | 59 ms | `core/paths.py` only — every payload is deferred |
| `nanopnp.cli` | 62 ms | the comparison, and the budget the deferred-import rule protects |

After importing all three view-models, **none** of `PySide6`, `PyQt5`, `PyQt6`, `ngsolve`, `netgen`
or `numpy` is in `sys.modules` — asserted in a subprocess by
`tests/tier1/test_gui_viewmodels.py::test_if09_the_view_models_import_no_qt_and_no_ngsolve`. The
editor therefore enumerates and validates the whole schema at the cost of the schema, and a shell
that is only browsing a case never pays for a solver or a toolkit.

---

## 6. Licence summary

Permissive core is achievable. Everything is LGPL/BSD/MIT/Apache **except**:

- **Gmsh** GPLv2+ → optional mesher backend only.
- **SuiteSparse UMFPACK** GPL-2+ → if it is the bundled default linear solver, the *bundle*
  carries GPL even though the library does not, so the distribution licence follows the solver
  chosen as default. **[tested]** SciPy's SuperLU (BSD) is not an alternative at production size:
  on the reference-sized factorisation (~1.2 × 10⁵ cells, five fields) it was OOM-killed, while
  UMFPACK completed — the measurement behind SPECIFICATION.md §6.6 and the CON-11 amendment of
  2 September 2026.
- **Triangle / TetGen** → avoid entirely.

LGPL dependencies (NGSolve, MDAnalysis, PySide6) are fine for a permissively-licensed project when
dynamically linked.

---

## 7. Local assets

| Path | What |
|---|---|
| `thesis/` | `github.com/willemsk/phdthesis-text`, CC-BY-4.0. LaTeX source of the full thesis incl. all parameter tables |
| `data/corrections/willems2020_nacl.yaml` | The fitted ePNP-NS correction parameters, transcribed and numerically verified |
| Author's contour script | **Exists** — semi-automatic density-contour extraction, to be supplied. Likely the fastest route through the riskiest pipeline stage |
| COMSOL models | Author retains a licence and can regenerate reference solutions on demand — the project's numerical oracle |

---

## 8. Python version floor — the 3.10 target is not free

Resolved with `uv 0.12.5`, August 2026, against live PyPI **[tested]**.

The specification asks for Python 3.10–3.14 (QR-09). The FEM backend delivers: `ngsolve` 6.2.2606
publishes wheels for **cp310 through cp314 on manylinux_2_28_x86_64, macosx_10_15_universal2 and
win_amd64** — fifteen wheels, no gaps **[tested]**.

The *structure* pipeline does not. Both of the versions named in the specification have dropped
Python 3.10:

| Package | Version in SPECIFICATION.md §2.6 | Requires |
|---|---|---|
| MDAnalysis | 2.10.0 | Python ≥ 3.11 |
| GridDataFormats | 1.2.0 (and 1.1.0) | Python ≥ 3.11 |

A dependency set naming both and `requires-python = ">=3.10"` is **unsatisfiable** — uv fails
resolution for the 3.10 split rather than silently excluding it. Two ways out: lower the floors to
the last releases that still support 3.10 (MDAnalysis 2.7, GridDataFormats 1.0.2), which is what
`pyproject.toml` currently does with a comment, so that 3.11+ still resolves to the specified
versions; or raise the project floor to 3.11 and amend QR-09. The choice becomes forced the moment
the geometry pipeline needs an API that only MDAnalysis 2.10 has.

Separately, and more happily: with all extras enabled (`structure`, `gui`, `gmsh`, dev group), the
resolved lock contains **no sdist-only package** — every dependency, `ngsolve`, `PySide6`, `gmsh`,
`pdb2pqr`, `MDAnalysis`, `scikit-image` and `h5py` included, installs from a binary wheel
**[tested]**. Nothing in the current dependency set contradicts CON-07.

**The local gate cannot see a 3.10 floor break; only the CI matrix can [tested].** The gate of
`CLAUDE.md` runs on the development interpreter — 3.12 — so a 3.11+ stdlib API compiles, typechecks
and passes every test locally while failing `tier 1-2 (ubuntu-latest, py3.10)` at *collection*.
`datetime.UTC` is the worked example: it is 3.11+, `datetime.timezone.utc` is the equivalent
available across the whole supported range, and the import error takes down every test module that
transitively reaches it rather than one assertion.

Typechecking at the floor would catch this class — `mypy --python-version=3.10` reports
`Module "datetime" has no attribute "UTC"  [attr-defined]` on a two-line file **[tested]** — but it
cannot currently be run over `src/`: NumPy's own bundled stubs use a PEP 695 `type` statement, and
mypy aborts the whole check with `numpy/__init__.pyi:737: error: Type statement is only supported in
Python 3.12 and greater  [syntax]` before reaching project code **[tested]**. So the guard is the
3.10 matrix job, and reproducing a matrix-only failure means `uv run --python 3.10 --all-extras
pytest`, which resolves and installs a separate 3.10 environment in about a minute.

---

## 9. The CLI's import budget, measured **[tested]**

`import nanopnp.cli` costs **55.6 ms cumulative** (`python -X importtime`), and a cold subprocess
that imports it and exits takes **0.082 s**. `import ngsolve` alone is ~370 ms, and the physics and
mesh modules at module scope would take the package's own share from 56 ms to 424 ms. A sweep
dispatching a job array pays that per process, which is what the deferred-import rule of
`CLAUDE.md` buys.

Two mechanisms keep it there, and both are load-bearing rather than tidy:

- **The stage registry holds descriptions beside `"module:attribute"` target strings**, and
  `nanopnp.core.stages.create` is the only function that resolves one. `nanopnp stage --list`
  therefore answers from data. Asserted in a subprocess: after `main(["stage", "--list"])` no
  module matching `ngsolve*` or `netgen*` is in `sys.modules` **[tested]**.

- **The IF-02 exit-code table is keyed on `f"{cls.__module__}:{cls.__qualname__}"` strings**, and
  `classify` walks `type(error).__mro__` looking each name up. Classifying an error therefore
  imports no exception module — which matters because the table names classes in `solve`, `mesh`,
  `charge` and `post`, and a table of *class objects* would import all four at CLI start.
  Asserted the same way, on the table's own module list **[tested]**.

The MRO walk is not incidental: it is what makes a subclass of a classified exception inherit its
exit code, so a narrower gate error added later is still a `4` rather than falling to `1`.

## 10. `canonical()` is the on-disk format, not only the hash input

`nanopnp.core.hashing.canonical` produces the bytes that are hashed **and** the bytes that
`manifest.json` and `run.json` hold — both are written through it, so the file a reader opens and
the bytes that were hashed cannot disagree. The consequence is easy to miss and produces a
confusing failure: every float on disk is a one-key wrapper `{"__f__": <float.hex()>}`, so
`json.loads` of a run record yields `{"current_A": {"__f__": "0x1.3e...p-35"}}` rather than a
number.

Comparing such a record against live values without decoding it does not report a *different*
number — it reports a **missing** one, because a flatten-to-dotted-paths comparison yields
`current_A.__f__` on one side and `current_A` on the other **[tested]**. `decode_floats` is the
inverse and belongs to any reader of these files.

It is deliberately not a full inverse of `canonical`: an array encodes as dtype, shape and a
*digest* of its bytes (`"__a__"`), which nothing can undo, and is left as it stands.

## 11. A stage's workspace falls back to the process store root, not the run's store **[tested]**

`mesh/ingest.py`, `charge/stage.py`, `solve/stage.py` and `post/stage.py` each fall back to
`store_root() / "tmp"` plus a `mkdtemp` when constructed without a workspace — and `store_root()`
is `$NANOPNP_STORE` or `./nanopnp-store`, the *process* default, never the `Store` the caller
handed the run. Running the test suite from a checkout therefore left a `nanopnp-store/tmp/mesh-*`
behind while every artefact lived in a `tmp_path` store.

`io.run.run_case` now names a fresh workspace under the store in use when the caller gives none.
Fresh per run and not a fixed `tmp/mesh`: two runs into one store hold different meshes, and a
deterministic name has the second overwrite a file the first's artefact still points at.

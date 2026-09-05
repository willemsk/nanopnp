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

---

## 5. GUI and packaging

| Tool | Licence | Note |
|---|---|---|
| **PySide6** 6.11.1 | LGPL-3 OR GPL-2 OR GPL-3 | **Use this.** LGPL option means no licence conflict |
| PyQt6 | **GPL-3 only** | Avoid unless the project is GPL |
| `PySide6.QtWebEngineWidgets.QWebEngineView` | — | Imports cleanly; hosts NGSolve webgui **[tested]** |
| briefcase / conda-constructor / PyInstaller | — | Packaging candidates; probe early |

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

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
| **MDAnalysis** | 2.10.0 | LGPLv3+ | PDB, DCD/XTC/TRR/NCDF; `analysis.align.AlignTraj`, `rotation_matrix` **[tested]**. **Not mmCIF**; see below |
| **gemmi** | 0.7.5 | MPL-2.0 | mmCIF (and PDB) reader; wheels cp311–cp314 on manylinux, musllinux, macOS and win_amd64 **[tested]**, 25 Sep 2026 |
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
- **The reference grid's axes are uniform to round-off.** Its COMSOL table is written in metres to
  ten significant figures, and its axes vary by 1e-15 nm about the 0.005 nm spacing, which is why
  `nanopnp.density.grid` refuses a non-uniform axis at 1e-9 nm. **[tested]**
- **The reader is guessed from the extension, and `.map` has none.** `Grid("x.map")` raises
  `ValueError: File format MAP not available, choose one of dict_keys(['CCP4', 'MRC', 'DX', …])`,
  although the writer, told `file_format="MRC"`, wrote that file without complaint. Pass the
  reader's `file_format` explicitly, from the same suffix table as the writer. `DensityMap.read`
  exported `.map` and failed to read it back until WP25 did so **[tested]**, 29 September 2026.
- **It carries no length unit.** `origin` and `delta` are written as given. CCP4/MRC defines its
  cell in ångströms, and molecular viewers read OpenDX in ångströms too, so a map written in nm
  overlays its structure at a tenth of its size. The 3D density map is therefore exported in Å and
  converted back on reading (the author's ruling, `SPECIFICATION.md` §8.2.2 B10). On the prepared
  2WCD, an overlay oracle that reads the exported MRC header raw and looks up each heavy atom's
  nearest node rejects all three errors a converter can make: read as nm, every atom falls outside
  the box; with the axes fully transposed, 89 % of atoms read below the single-frame bound; with x
  and y alone swapped, 57 % do **[tested]**, WP25, 29 September 2026.

**GridDataFormats before 1.2 has no MRC writer [tested].**
GridDataFormats 1.2.0 requires Python ≥ 3.11, so a Python 3.10 resolver takes **1.0.2**, whose
`Grid()._exporters` registry is `DX, PKL, PICKLE, PYTHON` — no `MRC` and no `VDB`. Its `_loaders`
registry *does* carry `CCP4, DX, MRC, PLT, PKL, PICKLE, PYTHON`, and `gridData.mrc` imports on both,
so **reading** MRC and CCP4 works on 1.0.2 and only **writing** them does not. Measured by running
each version: `griddataformats==1.0.2` on 3.10 exports a `(4, 3, 1)` grid to DX and refuses MRC with
`ValueError: File format MRC not available`; 1.2.0 on 3.12 does both.

Two consequences for anything that writes these formats across versions of gridData:

- `hasattr(gridData, "mrc")` and the module version are both **the wrong capability test** — the
  first is true on 1.0.2 and the second is a proxy. `Grid()._exporters` is the registry
  `Grid.export` itself looks the format up in, so it is the only authoritative answer. It is
  private; guard the read and fall back to translating the `ValueError`.
- A test guarded on "is gridData importable?" passes on 3.10 and then fails inside the writer. Guard
  on **writer availability**.

**The 3.11 floor makes this moot [tested].** With `requires-python = ">=3.11"` and
`GridDataFormats>=1.2`, every supported interpreter resolves to 1.2.0 and writes MRC, so the code has
no writer-availability branch (§8.2.2 B4). The facts above describe 1.0.2, should an older
environment turn up.

**Symmetry-axis detection:** do not use raw principal axes. Use **chain-permutation
superposition**: superpose chain A onto chain B, and the rotation's eigenvector with eigenvalue 1
*is* the Cₙ axis. It is about 40 lines and markedly more stable.

**Why principal axes fail on ClyA: they drift, but not from degeneracy [tested].** Measured on
25 September 2026 on the author's ClyA-AS ensemble (`prod5_clya_as.{pdb,dcd}`, 98 frames), using
the Cα set:

- **The axial eigenvalue is well separated.** The Cα covariance eigenvalues are 801, 881 and
  1432 Å² on frame 0, and 794, 809 and 1416 Å² on 2WCD. The two *perpendicular* eigenvalues are
  near-degenerate, which does not affect the axis. The earlier wording, "near-degenerate inertia
  axes", was wrong about the cause.
- **The principal axis still drifts.** Across the frames it moves by up to 1.54° (rms 0.66°), and
  it differs from the permutation axis by up to 1.54° (mean 0.74°). The cause is the chains'
  asymmetric fluctuation.
- **The cyclic permutation axis is stable.** Fitted to the whole assembly, it moves by at most
  0.010° (rms 0.005°), and its rotation angle stays within 0.031° of 30°.
- **Averaging chain A's rotations is noisier than the whole-assembly fit.** Averaging chain A's
  rotations onto every other chain (`(1/n)Σ_k R^k = â âᵀ` for an exact Cₙ) differs from the
  cyclic fit by up to 1.12° per frame. Use it only to order the chains.
- **A synthetic has to be built for principal axes to fail.** With the second moments made
  isotropic (`h = √(6⟨ρ²⟩)` for points on a cylinder), 0.02 nm of per-atom noise sends the principal
  axis up to 6° astray, and 0.1 nm sends it up to 24°. The permutation axis stays within 0.02° and
  0.1° respectively.

**MDAnalysis 2.10 reads no mmCIF [tested].** `mda._PARSERS` and `mda._READERS` in 2.10.0 have no
`CIF`, `MMCIF` or `PDBX` entry, and `MDAnalysis.topology.PDBxParser` does not import. Only the
retired `MMTF` format is there. IF-04's mmCIF leg goes through gemmi (§2.6, WP18).

**What the readers do with a blank or odd field [tested].** Measured 25 September 2026 on MDAnalysis
2.10.0 and gemmi 0.7.5, while building stage 1 (WP18):

- A PDB atom whose element columns are blank reads as element `''`. If **every** atom's are blank,
  the `elements` attribute is absent altogether. MDAnalysis 2.10 does not guess elements unless
  asked, so a blank stays blank.
- A blank segment identifier in a PDB is filled from the chain identifier ("Setting segids from
  chainIDs").
- gemmi reads an mmCIF `type_symbol` of `?` as element `X`, without guessing from the atom name.
  gemmi's `Chain.name` is the `auth_asym_id` and `Residue.seqid.num` the `auth_seq_id`.
- `Universe.trajectory.dt` warns "Reader has no dt information, set to 1.0 ps" and returns 1.0 for
  a PDB and for an untimed DCD.

**What each trajectory format gives back [tested].** Coordinates written in float32 ångströms from a
`MemoryReader` universe and read again: DCD and NetCDF store ångströms and return the written bytes
exactly. TRR stores float32 nanometres, so the ångström-to-nanometre conversion costs up to two
float32 ulps, 1.1e-6 nm measured at 13 nm. XTC is quantised to 0.001 nm and returns within
5.02e-4 nm, which is half the quantum plus the same float32 round-off.

**The permutation axis on synthetic assemblies [tested].** Measured with `nanopnp.structure.axis`
(`tests/tier1/test_structure_axis.py`):

- An exact C7, C8 or C12 about an axis tilted 35° and offset by (3, −1.5, 40) nm is recovered to
  about 4e-14° and 4e-14 nm, with the chain letters shuffled.
- A C12 of 285-point chains with its second moments made exactly isotropic, plus 0.02 nm of per-atom
  noise, gives a permutation axis within 0.0014 nm of the true one over the axial extent. The
  principal axis nearest the truth is 35° off and 3.2 nm away: with the moments exactly isotropic,
  the noise alone picks the principal axes.
- **A D6 assembly defeats the ordering average.** The rotations from chain 0 onto the others sum to
  zero: six turns about the axis give `6 ẑẑᵀ`, and six two-folds perpendicular to it give
  `−6 ẑẑᵀ`. The ordering axis is then arbitrary, and the **spacing** gate refuses the assembly (the
  worst gap is 281° from nominal), before the angle gate is reached.
- **The angle gate is the one that catches a ring whose chains are not rotational copies.** Twelve
  chains exactly 30° apart, whose own orientation turns at a quarter of the ring's rate, have a
  spacing error of 0.001° and a cyclic turn of 28.07°. At half the rate the turn is 29.03°, inside
  the 1° tolerance. Helical rises and partial turn-overs move the spacing before they move the
  angle.

**MDAnalysis trajectory readers and their time metadata [tested].** Each writer (DCD, XTC, TRR,
NCDF) round-trips three frames written from a static `Universe`. NCDF needs no `netCDF4`, because
the scipy fallback suffices. The times are the trap:

- A DCD written without a timestep reads **1.0 ps per frame**, while XTC, TRR and NCDF read
  **0 ps**.
- The author's `prod5_clya_as.dcd` reads 1.0 ps per frame, a 0.097 ns span for what is about 10 ns
  of production.
- A "last *n* ns" selection trusted to that metadata silently takes the whole trajectory, or the
  wrong window. Gate a `last_ns` longer than the recorded span, and record the times as read
  (`SPECIFICATION.md` §5.3.1 NOTE on `structure:`).

**Density deposition and the (r, z) reduction, measured [tested].** Measured on 25 September 2026
with scratch prototypes while planning WP19. They are not the implementation, and the plan's Design
§1–§5 has the derivations. At h = 0.05 nm:

- **Deposition cost.** One probabilistic-union deposition of the 2WCD dodecamer (26,844 heavy
  atoms, ε = 1e-6 spherical truncation, a 295 × 287 × 341 grid) took 31.2 s in numpy. Most of that
  was a full-grid `np.bincount(..., minlength=N)` per 256-atom batch, which allocates a 231 MB array
  105 times. Scatter per z-slab instead. Depositing n rotated copies costs n times this.
- **Cell–annulus overlap areas.** The closed form for the area of a square inside a disc needs the
  circular-segment primitive `½(x s + R² θ)`. With `θ = asin(x/R)`, the weights summed to the exact
  annulus areas only to 2.3e-7, because `asin` is ill-conditioned as x → R and R² amplifies the
  error. With `θ = atan2(x, s)` and `s = √((R − x)(R + x))` they sum to 4.0e-13.
- **The inner bins need no interpolation once the weights are exact.** Interpolating bins 1–2 from
  the axis sample, linearly in r² or by an even quartic, was worse than the binned value in some of
  15 on- and off-axis Gaussians. The worst was 7.6e-2 against 2.9e-2.
- **A binned variance is not an azimuthal variance.** Within a bin of width h, the radial gradient
  contributes about `(∂ρ/∂r)² h²/12`. An axisymmetric ring (r₀ = 2 nm, w = 0.2 nm) reads a raw
  variance of 7.0e-3 and a C12 harmonic variance of 1.9e-4, where a genuine C12 ring of the same
  width reads 8.7e-4. Subtracting the binned mean, as an even cubic spline evaluated at each cell's
  own radius, brings those to 3.6e-6 and 2.0e-8. Linear interpolation brings the C12 figure only
  to 5.4e-6.
- **The Cₙ average is a projection [verified].** In the angular harmonic basis, averaging n rotated
  copies multiplies `c_m` by `[n | m]`. It therefore leaves the azimuthal mean unchanged and needs
  no rotated map. Against the closed form `2E²Σ I_{kn}(β)²` for a C12 ring of Gaussians, the peak
  variance came out −0.3 to −0.7 % by harmonic projection, −1.4 to −2.4 % from exactly rotated
  copies binned, and −3.3 to −6.1 % from `scipy.ndimage.map_coordinates(order=1)` rotation. The
  bilinear route is biased low, and its k = 0, 3, 6 and 9 copies are exact while the other eight are
  smoothed.
- **`cos(mθ)` modulations** with a smooth radial envelope give both variances within 1.5e-3 of
  `b²/2` (relative to the peak) at r ≥ 1 nm when n | m. When n ∤ m, the Cₙ variance stays below
  7.1e-5 of it.

**Stages 2 and 3 as implemented [tested].** Measured on 25 September 2026 with
`nanopnp.density` and `nanopnp.symmetry` (WP19; `tests/tier1/test_density.py`,
`tests/tier1/test_reduction.py`, `tests/tier2/test_density_2wcd.py`), at h = 0.05 nm and
σ = 0.93:

- **Deposition.** Atoms are grouped by stencil half-width, each group gathers a separable
  Gaussian over a spherical offset set, and the terms are scattered by `np.bincount` into a z-slab
  of at most 4e6 cells, 1e6 terms at a time. The prepared 2WCD dodecamer (26,844 heavy atoms, a
  315 × 271 × 271 grid in the aligned frame) deposits in **17.0 s**, and stage 3 reduces it in
  **6.9 s**. A fresh interpreter running stages 1–3 peaks at **0.47 GB** RSS. The prototype above
  took 31.2 s for the deposition alone.
- **Fine spacing needs the slab-clipped stencil.** Evaluating a whole stencil in every z-slab it
  reaches did 6.8x the work at h = 0.025 nm, where a slab is a few planes of a stencil tens of
  planes deep. Evaluating only the offsets that land in the slab (one contiguous run, because the
  stencil's z offsets ascend) leaves the map bit-identical. **[tested]** (`nanopnp.density.union`,
  `_accumulate`.)
- **The truncation error sits inside its bound.** On 200 random atoms against an untruncated
  evaluation, the largest voxel error was 7.8e-6. At every voxel it stayed below the sum of
  `g/(1 − g)` over the dropped terms, which peaked at 1.15e-5.
- **The exact annular weights**, with the `atan2` segment, sum to the annulus areas to 1.2e-13 to
  1.6e-13 relative, and each interior cell's to `h²` to 3e-16. A 2WCD slice's integral is conserved
  through the binning to 6e-16.
- **2WCD's reduction.** The largest C12 variance is 0.204, at r = 5.40 nm and z = 12.95 nm. The
  largest non-C12 variance, raw minus C12, is 9.5e-3, at r = 1.65 nm and z = 3.10 nm: the crystal's
  chains are not exact copies. The axis bin's mean is exactly 0 over the central 80 % of the Cα
  extent, because the lumen is wider than the 3.72σR kernel cutoff.
- **Turning a C12 by a non-symmetry angle moves it measurably.** A synthetic C12 of 480 atoms,
  turned by 90° before deposition, reduces unchanged to round-off. Turned by 30°, one of its own symmetries,
  it agrees to the float32 map's rounding. Turned by 15°, it moves the mean by 5.5e-4 and each
  variance by 0.26 % of its 0.175 peak. That is the grid's own anisotropy, and why a 30° turn alone
  is too weak an invariance test.
- **gridData's precision on export.** OpenDX writes the origin with `%f`, the delta with `%.7g`
  and the values with six decimals, so a float32 map comes back within 5e-7 plus its own
  re-rounding, 2⁻²⁴. MRC stores the values and the voxel size as float32: 0.05 reads back as
  0.05000000074505806. A grid identity check must round the spacing, as `%.7g` does, before
  comparing.
- **numpy's fixed-width strings drop trailing NULs.** `np.char.add(a, "\x00")` returns `a`
  unchanged, because a `<U` array treats trailing NULs as padding. So a `"\x00"` separator between
  residue and atom names silently vanishes, and `ALA`+`CA` reads `ALACA`. Use a printable separator
  that no name contains, such as a tab.
- **The ClyA-AS ensemble through stages 2 and 3.** This is `prod5_clya_as`, DCD frames 48–97:
  54,075 atoms, 27,134 of them hydrogens, on a 339 × 293 × 293 grid. The 50 depositions took
  980.6 s, 19.6 s a frame, and stage 3 took 9.9 s. The session peaked at 0.56 GB. The largest C12
  variance is 0.171, at r = 4.70 nm and z = 6.55 nm. The largest non-C12 variance is 0.088, at
  r = 2.00 nm and z = −1.70 nm, inside the lumen. That is nine times the crystal's 9.5e-3, which
  is consistent with the ensemble's chains fluctuating independently. The cause is not measured
  (`tests/tier3/test_density_ensemble.py`).
- **The CHARMM radius set against 2WCD.** All 26,844 atoms resolve, with radii of 0.170 to
  0.2275 nm. Its 216 `ILE CD1` resolve through the alias to `CD`, and its 120 `HIS` atoms because
  HSD, HSE and HSP agree on every heavy atom. `CHARMM.DAT` in PDB2PQR 3.7.1 holds 2,587 entry
  lines, and `CAL` and `DUM` appear twice with identical values. `DUM`'s radius is 0, which the
  set refuses, because a zero-width kernel deposits nothing.

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

**Package facts, read from PyPI's metadata on 30 September 2026 [verified]:** `pdb2pqr` 3.7.1 is
BSD-3, a pure-Python wheel, and requires Python ≥ 3.11, < 4. `propka` 3.5.1 is **LGPL-2.1** by its
licence field and classifier, and is a pure-Python wheel. `SPECIFICATION.md` §2.6 called it BSD
until that day. There is no `apbs` package on PyPI. `apbs-binary` 3.4.1.1 packages the BSD-3 APBS
under Apache-2.0 and ships wheels for manylinux_2_28 x86_64, macOS 10.15 x86_64 and macOS 12
arm64, **none for Windows**. So VAL-06 can run on the Linux and macOS CI legs only (§8.2.4 D3).

APBS keywords for the cross-check: `chgm` ∈ {spl0, spl2, **spl4**} (spl4 = quintic B-spline,
least grid-sensitive); `srfm` ∈ {mol, **smol**, spl2, spl4}. Note `spl2`/`spl4` surfaces "may
produce unphysical results at non-zero ionic strengths" — run the cross-check at **zero** ionic
strength, which also isolates charge-projection error from model differences.

### PDB2PQR 3.7.1 and PROPKA 3.5.1 as a per-frame driver **[tested]**, 1 October 2026

Measured in this container while planning WP27, with `--ff=CHARMM --ffout=CHARMM --with-ph=7.5
--titration-state-method=propka --drop-water --keep-chain` unless stated. Inputs were cut from the
vendored `tests/data/structures/2wcd.pdb.gz` (chains A–L, 26,844 heavy atoms, no hydrogens, crystal
frame).

- **Python API.** `pdb2pqr.main.run_pdb2pqr(args)` runs in-process and returns
  `(missed_residues, pka_df, biomolecule)`. It always writes the PQR to the output path in `args`,
  and it does not set up logging. `pka_df` is a list of dicts with `res_name`, `res_num`,
  `ins_code`, `chain_id`, `group_label`, `group_type` and `pKa`. Atoms carry `ffcharge` and
  `radius`. `io.get_pdb_file` **fetches from rcsb.org when the input path is not a file**, so a
  driver must pass a path that exists. A multi-MODEL input is read to its first model only.
- **Cost.** The 2WCD dodecamer takes 63.7 s with PROPKA and 11.5 s without it. Chain A alone with
  PROPKA takes 1.6 s, so the cost of PROPKA on the assembly is superlinear in its size. A nine-residue
  fragment takes 0.1 s. Plan for about a minute per frame of a ClyA ensemble, 50 minutes for 50 frames.
- **Q_net.** 2WCD at pH 7.5 gives −60 e, −5 e on every chain, with no residue whose charge
  differs between chains. ClyA-AS is −72 e (`04-clya-geometry-and-charge.md` §3). OPN-04 lists 27
  mutations between the 2WCD sequence and ClyA-AS; whether they account for the −1 e per chain is
  not checked.
- **States that CHARMM cannot hold.** `Biomolecule.apply_pka_values` logs a tuple warning and keeps
  the standard state for `CYS⁻`, `LYS⁰`, `TYR⁻` and `ARG⁰` under CHARMM. On 2WCD that is
  `('CYS 285 A', 'negative')` in every chain (pKa 6.25). Terminal pKas are **never applied**,
  under any force field: the dictionary is filtered by `group_label.startswith(res_name)`, which
  drops the `N+` and `C-` groups, so the terminal branches are dead. PROPKA puts the N-terminus of
  `LYS 8` at pKa 7.48–7.50 across the chains (7.49 in chain A, below pH 7.5), and PDB2PQR keeps it
  charged without a warning. Derive
  unapplied states from `pka_df` and the applied charges, not from the log.
- **Changeable states under CHARMM** are `ASP`/`ASH`, `GLU`/`GLH` and `HIS`/`HIP`. On the fragment
  `GLU 18`–`LEU 26` of chain A, PROPKA at pH 2 gives +0 e, and at pH 8 −3 e. Without a titration
  method, `--with-ph` changes nothing: pH 3 and pH 9 give identical charges.
- **Histidine names pin the state.** With hydrogens stripped, a residue named `HSD` or `HSE` keeps
  that tautomer and is not titrated by PROPKA. `HSE` with its hydrogens present makes PDB2PQR give
  up with a `RuntimeError`. `HIS` is titrated. A driver must therefore strip hydrogens and rename
  protonation variants to their parent before calling PDB2PQR.
- **Output naming.** `--ffout=CHARMM` writes terminal-patch atoms under the residue name `TER`
  (`N TER A 8`, `OT1 TER A 292`). It renames `ILE CD1` to `CD` and the C-terminal `O` and `OXT` to
  `OT1` and `OT2`, and it writes histidines as `HIS` whatever their tautomer. PDB2PQR 2.1.1 had kept
  the real residue name (`GLU HT1`) and `HSE`. Identify a residue by chain, number and insertion code.
- **Coordinates move by relabelling, and flipped groups move a little.** PDB2PQR renames heavy
  atoms in place (`ILE CD1` to `CD`, the C-terminal `O` to `OT1`) and adds 12 terminal `OXT`, as
  `OT2`, by repair. Hydrogen-bond optimisation flips `ASN`/`GLN` amides and `HIS` rings through
  180° about the bond to the group, which is not symmetric about it, so a flipped atom does **not**
  land on its partner's position: on the 2WCD dodecamer in the crystal frame, 140 heavy atoms (the
  `OD1`/`ND2` of 22 asparagines, the `OE1`/`NE2` of 46 glutamines, one histidine's `ND1`, `CD2`,
  `CE1`, `NE2`) lie 0.13–0.15 Å (amides) and 0.19–0.40 Å (the ring) from every input heavy atom, and
  no other heavy atom moves. On the prepared dodecamer of the tests it is 138, worst 0.397 Å. Match
  heavy atoms by position within a residue, never by name, and leave the flippable atoms out of any
  tight positional criterion **[tested]**, 1 October 2026 (WP27; this bullet first said the 140
  carried another atom's position exactly).
- **Fused columns.** The PQR is written in PDB fixed columns, so a coordinate at or below −100 Å
  runs into its neighbour (`-37.705-115.041`). `pdb2pqr.io.read_pqr` splits on whitespace and
  cannot read PDB2PQR's own output in that case.
- **Four-character residue names and patched residues.** `Atom.get_common_string_rep` writes a
  four-character residue name (`ASPP`, `GLUP`) from column 17, the PDB alternate-location column,
  and a shorter one from column 18; a four-character atom field then runs into it (`OD2ASPP`). A
  residue patched to a protonation variant is written with its backbone under the parent and its
  side chain under the variant: `ASP 21` of the fragment `GLU 18`–`LEU 26` at pH 2 carries both `ASP`
  and `ASPP`. A reader that takes columns 18–21 reads `SPP` **[tested]**, 1 October 2026 (WP27).
- **Disulfides, waters, `HETATM` and the C-terminal carboxyl.** Under `--ffout=CHARMM` a
  disulfide-bonded cysteine's `CB` and `SG` are written `1CB` and `1SG` under the patch residue
  `DISU` (`1CBDISU A 285`), its other atoms under `CYS`; under `SWANSON` and `PEOEPB` the whole
  residue is `CYX`. A reader naming residues by their atoms must treat `DISU` as it treats `TER`
  **[tested]**, 1 October 2026, `CYS 285` of 2WCD chain A bonded to a mirrored copy (WP27 review).
  `--drop-water` drops only `HOH` and `WAT` (`aa.WAT.water_residue_names`), and a water kept under
  CHARMM is `TP3M`. `HETATM` with a five-digit serial is written with nothing between them
  (`HETATM12345`, `get_common_string_rep`) **[verified]**, read from the 3.7.1 source. PROPKA types
  the C-terminus `COO`, as it does a side-chain carboxyl, and only its label says `C-`: a C-terminal
  `ASP` or `GLU` carries two `COO` groups (`ASP  21 A`, `C-   21 A`) **[tested]**, 1 October 2026.
- **`run_pdb2pqr`'s first return is missing atoms**, not residues: the atoms
  `Biomolecule.apply_force_field` could not parameterise, which the PQR leaves out. An atom
  written with no charge gets `0.0000` (`get_pqr_string`) **[verified]**, read from the 3.7.1
  source, 1 October 2026.
- **PROPKA 3.5.1 fails on Python 3.14.** `Parameters.parse_line` dispatches on
  `self.__annotations__`, and under PEP 649/749 annotations are a class attribute only: on an
  instance the lookup raises `AttributeError: 'Parameters' object has no attribute '__annotations__'`
  on the parameter file's first line, so every titrated PDB2PQR run fails (CI, Python 3.14.7;
  reproduced on 3.14.0rc2). Assigning `Parameters.__annotations__` does not help, because the type's
  descriptor stores it where instance lookup does not look. A `__getattr__` on the class answering
  that one name from `type(self).__annotations__` does, and the dispatch is unchanged: the fragment
  `GLU 18`–`LEU 26` at pH 2 gives byte-identical PQRs and equal pKas on 3.12 and on 3.14 with it.
  3.5.1 is the latest release (PyPI, 1 October 2026). `charge/protonation.py`'s
  `restore_propka_annotations` installs it only where the instance lacks the attribute
  **[tested]**, 1 October 2026 (WP27).
- **The stage's cost.** Protonating the prepared 2WCD dodecamer through the `protonation` stage
  takes 97.4 s and 0.44 GB peak RSS for one cold frame, in a fresh process; with the frame cached
  the stage's own work (reading the PQR, registering it, tabulating the states, checking the radii)
  is 3.4 s. PDB2PQR alone on the crystal-frame dodecamer took 98 s in the same container that
  day, against the 63.7 s above: the difference is the machine, not the stage. On that frame PROPKA puts the `LYS 8` N+ pKa at 7.481–7.499 in every chain, so all twelve
  N-termini are unapplied at pH 7.5, and it warns `Missing atoms or failed protonation for HIS 292
  A`; `Q_net` is −60 e **[tested]**, 1 October 2026 (WP27, `tests/tier2/test_protonation_2wcd.py`).
- **Zero radii.** On chain A, `AMBER` gives 53 charged atoms radius 0, `PARSE` 93, and `TYL06`
  2269. `CHARMM`, `PEOEPB` and `SWANSON` give none. Every force field gives −5 e on chain A, and
  every printed charge has at most four decimals.
- **Logging.** The loggers are `PDB2PQR3.7.1` (`pdb2pqr.main.VERSION`), `pdb2pqr.*` and
  `propka.*`. PROPKA's full report is logged at INFO, about 400 kB for the dodecamer. Importing
  `pdb2pqr` calls `logging.captureWarnings(True)`.

### APBS 3.4.1 driven by maps **[tested]**, 1 October 2026

Measured in this container while planning WP29 (VAL-06), with `apbs-binary` 3.4.1.1 installed into
a scratch environment. Lengths in the deck and the maps are in Å, and the potential is in `kT/e` at
the deck's `temp`.

- **The package.** The Linux wheel is tagged `py3-none-manylinux_2_28_x86_64`, so one wheel serves
  every Python. It holds a static `apbs` (banner `APBS 3.4.1`, built 29 April 2022) and the tools,
  33 MB in all. On macOS arm64 the binary needs `DYLD_LIBRARY_PATH` set to the package's `lib/`.
  `apbs_binary.run_apbs` and `popen_apbs` set it, and they take `subprocess.run` and `Popen`
  arguments.
- **A molecule is mandatory.** A deck with every input supplied as a map, but no `mol`, stops with
  `PBEparm_check: MOL not set!`. A one-atom, zero-charge PQR placed outside the box satisfies it.
- **`READ charge` is in e Å⁻³.** A unit Gaussian sampled at the nodes is reported as `Charge map
  integral = 1.00e+00 e`. With `usemap charge`, `chgm` has no effect on the map.
- **The three `READ diel` maps are staggered.** The x-map's origin is the grid's plus `h/2` in x,
  and likewise for y and z. APBS samples each at the edge midpoints. An x-map on the node grid
  aborts with `Vpmg_fillco: Off dielXMap at: (x,y,z) = …` and `VASSERT: ASSERTION FAILURE` at
  `vpmg.c:4191`.
- **No kappa map at zero ionic strength.** A deck with no `ion` line and no `kappa` map runs.
- **`bcfl map` exists.** It needs `usemap pot`, takes the face values of the potential map, and warns
  `External energies are not used in BCFL_MAP calculations`.
- **Accuracy on closed forms.** All runs use `bcfl map` from the exact potential.
  - **A unit Gaussian** (`w` = 0.1 nm) in uniform ε, point-sampled, has a maximum interior error of
    0.32, 0.079 and 0.020 `kT/e` at `h` = 0.0625, 0.031 and 0.016 nm. That is second order.
  - **A Gaussian ring in a dielectric sphere** has radius 1 nm, height 0.5 nm and `w` = 0.1 nm. The
    sphere has `a` = 2 nm and ε 20, in water at 78.15. The charge map is hat-weighted from an
    (r, z) lattice and conserves to 10⁻¹⁶. The table gives the maximum fluid error, at least
    0.2 nm outside the sphere, relative to the fluid's maximum |φ|.

    | `h` (nm) | Point-sampled diel | Harmonic mean (8 per edge) |
    |---|---|---|
    | 0.2 | 0.53 % | 0.27 % |
    | 0.1 | 0.25 % | 0.14 % |
    | 0.05 | 0.11 % | 0.043 % |

    Point sampling is first order. Inside the sphere the harmonic mean's rms error falls by 4 per
    halving. Averaging arithmetically across each edge's dual face before the harmonic mean is
    *worse* than the harmonic mean alone: 0.42 % and 0.25 % at 0.2 and 0.1 nm.
  - **Node-centred values declared at the staggered origin** give 2.05 % max and 0.53 % rms on the
    fluid at 0.1 nm. That is wrong, but within a loose gate, so it is caught against the closed
    form and not by a two-solver comparison.
- **Cost.**

  | Grid | Wall-clock | Peak RSS |
  |---|---|---|
  | 65³ | 1 s | 0.11 GB |
  | 129³ | 11 s | 0.52 GB |
  | 193³ | 44 s | 1.9 GB |

  This is about 250 B per node.
  The maps APBS reads are about 0.6 GB of text at 193³, which `run_apbs` deletes once read **[verified]**.
- **Case identity cost** (`validation/comsol.py`): hashing the 84 MB reference charge table takes about 1.6 s;
  hashing the 9.2 MB deposited 2WCD structure files takes 12 ms, plus 0.7 s on the first import of stage 1 and
  MDAnalysis **[tested]**.
- **Self-refinement on 2WCD.** The problem is `poisson` on the protonated, prepared 2WCD at the
  default mesh (44,987 elements), with both electrodes grounded. The box is 19.2 nm, with the faces
  from our own `P2` solution. The probes are 555,535 fluid nodes of the 0.2 nm grid, at least 0.3 nm
  from every solid. On them, max |φ| is 19.3 `V_T` (0.50 V) and the rms is 7.2 `V_T`.

  | Difference | max | rms | axis, 93 nodes |
  |---|---|---|---|
  | APBS 0.1 nm against 0.2 nm | 0.189 `V_T` (0.98 %) | 0.17 % | 0.57 % |
  | Our `P3` against `P2` | 0.047 `V_T` (0.24 %) | 0.01 % | 0.013 % |

  APBS's maximum lies in the lumen. At 0.5 nm from the solids it is 0.77 %. The difference between
  the two solvers was not formed; VAL-06's tolerance was stated first (`SPECIFICATION.md` §7.4
  NOTE on VAL-06).

### APBS in the VAL-06 driver **[tested]**, 1 October 2026

Measured while implementing WP29 (`src/nanopnp/validation/apbs.py`), in this container with 24
cores, on `apbs-binary` 3.4.1.1 from the `apbs` dependency group.

- **APBS's log reports its own memory**: `Final memory usage: … MB total, X MB high water`. The
  child's `ru_maxrss` from `wait4` is not that number on Linux. It is a high-water mark kept across
  `execve`, so it includes the pages of the Python process that forked it. Under pytest it read
  1.42 GB for a 97³ run whose own high water was 0.24 GB. The driver reads the log.
- **At `h` = 0.1 nm, "e per node" and "e per Å³" are the same number**, because a cell is 1 Å³. A
  charge map left undivided by `h³` is therefore invisible at 0.1 nm. It shows at 0.2 nm as a factor
  of 8, so the ring checks that broken construction on the nested grid.
- **APBS writes an OpenDX header's `origin` and `delta` at `%12.6e`**, seven significant figures,
  whatever precision the input maps carried. A 33³ grid at 0.1234567891 nm comes back at
  0.1234568 nm, so a check that the output matches the problem's grid must allow about 5 × 10⁻⁷
  relative (the driver allows 10⁻⁶, and 10⁻⁴ `h` on the origin). Found by the WP29 review.
- **The ring in a grounded dielectric sphere** (`r_b` 1 nm, `z_b` 0.5 nm, `w` 0.1 nm, `a` 2 nm, ε 20
  in `ε_r,f⁰`, `R` 20 nm), with the faces from the series, 65³ at 0.1 nm and about 18,000 fluid
  probes. APBS is within 0.13 % max, 0.027 % rms and 0.13 % on the axis of the series. Our `P2`
  deposit and solve (53,009 elements, 0.05 nm inside 6 nm) is within 0.010 %, 0.016 % and 0.010 %.
  The broken constructions, against half the tolerance (1.5 %, 0.5 %, 0.75 %):

  | Construction | max | rms | axis |
  |---|---|---|---|
  | No `1/h³`, on the 0.2 nm grid | 364 % | 208 % | 341 % |
  | `2πr` dropped from the lattice mass | 44 % | 25 % | 41 % |
  | Charge point-sampled, `w` = 0.0112 nm | 409 % | 234 % | 384 % |
  | Node-centred diel declared staggered | 1.98 % | 0.59 % | 1.67 % |
  | `temp` 310 K against 298.15 K | 1.96 % | 1.13 % | 1.99 % |
  | Charge 0.5 nm off in z | 31 % | 11 % | 29 % |
  | `bcfl zero` | 54 % | 74 % | 54 % |
  | Charge zeroed | 52 % | 30 % | 49 % |

  The temperature row is half of the 3.8 % that the ratio 310/298.15 predicts, because the faces
  hold our potential and only the charge's part of the interior scales.
- **The gated leg on 2WCD.** This is the protonated, prepared dodecamer at the default sizes
  (44,985 elements), solved with `poisson` and both electrodes grounded. The box is 193³ at 0.1 nm
  from (−9.6, −9.6, −4.35) nm, with 569,541 probes and 93 on the axis. The refinement estimates
  and the agreement are in `SPECIFICATION.md` §7.4 (the NOTE on VAL-06): 0.41 %, 0.10 % and
  0.23 %, inside a budget of 1.20 %, 0.18 % and 0.59 %. The largest difference, 0.080 `kT/e`
  where ours is −17.8, lies at r = 1.80 nm, z = 0.25 nm, beside the constriction.
- **APBS's order on 2WCD.** A focused 193³ grid at 0.05 nm on the axis takes its faces from the
  0.1 nm solution, interpolated trilinearly, and the charge inside it, clipped. Over 34,637 probes,
  `|φ(0.1) − φ(0.2)|` is 0.184 and `|φ(0.05) − φ(0.1)|` is 0.059 `kT/e` at most. That is an order of
  1.64 in max and 1.61 in rms, so the 0.1-against-0.2 nm difference bounds APBS's error at 0.1 nm.
- **The recorded leg on 2WCD.** APBS takes `spl4` and `smol` (`srad` 1.4 Å, `swin` 0.3 Å, `pdie`
  20) from the same PQR in the model frame. 2,651,142 edges in our membrane are set to 3.2. The
  comparison is over the 454,325 probes whose ring lies inside the box, at 24 angles. The ring means
  differ from ours by 15.7 % max, 6.7 % rms and 13.6 % on the axis. APBS at the nodes differs by
  77 % max, near atoms. The spread around a ring reaches 46 % of `max|φ|`, at 4.1 % rms.
- **Cost on 2WCD.** The `P2` walk takes 15 s and the `P3` walk 8 s, with stages 1–3 and the
  protonation seeded. The raster of 2.7 M cells takes 10 s and the maps 3 s. APBS takes 29 s at
  193³ (1.83 GB high water) and 3.3 s at 97³ (0.24 GB). The test process peaks at 1.38 GB. Writing
  one 193³ OpenDX map takes 3.5 s and 126 MB, and GridDataFormats reads it back in 2.4 s. The
  module, with the recorded leg and the focus under `-m slow`, takes 5 minutes.

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

**`find_contours` orientation in (r, z) [tested].** On a `[z, r]` array with
`positive_orientation="high"`, a point `(row, col)` maps to `(r, z) = (col·Δr, row·Δz)`, which
swaps the axes, so the winding flips from the one the docstring describes. A loop around values
above the level has a **negative** shoelace area in (r, z), clockwise, and a loop around a void
inside it is counter-clockwise. Stage 4 tells bodies from holes that way (`nanopnp.geometry.contour`,
WP20 D4). A contour that reaches the array's edge comes back open, with its first and last points
distinct, and `fully_connected="high"` joins diagonal neighbours above the level. Measured with
scikit-image 0.26.0 on 26 September 2026.

**Shapely closing and opening [tested].** `region.buffer(δ, quad_segs=8, join_style="round")
.buffer(−δ, …)` is a closing and the reverse order an opening; both keep a straight wall straight,
fill a slot narrower than 2δ completely, and remove a fin thinner than 2δ with no bump at its root.
A 90° corner moves by `δ²(1 − π/4)` in area, concave corners gaining and convex ones losing. The
output ring is densely sampled on its arcs, with edges of about `δπ/16`, which is why stage 4
resamples before it measures a feature size. Measured with Shapely 2.1.2 (VER-51).

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

**Netgen's mesh tables mix 1-based and 0-based indices [tested].** Through `ngsolve.Mesh.ngmesh`,
`el.vertices[i].nr`, `Element2D.index` (into `GetMaterial`) and `Element1D.index` (into
`GetBCName(index - 1)`) are 1-based, and `FaceDescriptor.SetBCName` is 0-based. Mixing the two shifts every
boundary name by one (`wall` becomes the axis) and nothing raises. Names survive an OCC boolean and a
glue, so naming an embedded body's edges before the chain of position-based names leaves them alone.
When every boundary node is shared by two groups (a closed loop of named edges), a greedy choice of one
node per entity can fail; choose the representatives by bipartite matching with augmenting paths, then
give each leftover node its lowest-dimensional entity, as gmsh does. Source: `mesh/adapter.py`
(`from_ngsolve`, `to_ngsolve`, `_node_entities`), `mesh/primitives.py` (`name_edges`).

**`meshio.Mesh.field_data` is keyed by name, so it cannot carry the same name in two dimensions
[tested].** The §5.3.1 vocabulary uses `cis`, `trans`, `membrane` and `analyte` as both a domain name
and a boundary name, which is exactly the collision. Read `$PhysicalNames` off the file and key it
`(dimension, tag)` instead.

**A round trip through MSH 4.1 permutes both nodes and cells [tested]**, because meshio's reader
returns nodes grouped by entity and cell blocks in entity order. A content hash taken over the arrays
in file order would therefore make a mesh differ from itself. Hash a canonical form: vertices sorted
by `(r, z)`, connectivity renumbered into that order, elements sorted by group name — invariant under
everything the round trip does, and changing the moment an edge moves group.

**`meshio.read` on a `.msh` file prints an empty line to standard output unless told the format
[tested].** meshio 5.3.5 maps the `.msh` suffix to both `ansys` and `gmsh`, tries `ansys` first, and
`print`s that reader's `ReadError` — whose text is empty — before falling through to `gmsh`. Found by
WP16 (23 September 2026) when a CLI test asserted that a refused `nanopnp mesh` wrote nothing to
stdout; every `nanopnp run` on an MSH case had been writing the same stray line, which a caller
parsing the IF-02 result stream would read. Pass `file_format="gmsh"`.

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
  **The other direction works** **[tested]** (WP21, netgen 6.2.2606): a shape hashes and compares
  equal to the same topological entity reached another way, so `set(face.edges)` per named face
  after a `Glue` gives each edge's adjacency by membership. A seam shared by two faces is in both
  sets, and `set(shape.edges)` removes the per-face duplicates (383 listed edges become 195 on the
  ClyA region). Stage 5 names every edge this way: `protein` with `membrane` is `interface`,
  `protein` with `electrolyte` is `wall`, `membrane` with `electrolyte` is `membrane`. Geometry is
  left to the two tests adjacency cannot make, `r = 0` and the reservoir arc.
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

**Gmsh facts, measured on 4.15.2 with netgen 6.2.2606, Linux (WSL2), 29 September 2026 [tested]**
(WP23; the implementation is `mesh/gmsh_backend.py`, the evidence the WP23 plan's Design and
Outcomes):

- **`gmsh.initialize()` from Python turns the terminal on.** `General.Terminal` reads 1 straight
  after it, so meshing writes Gmsh's progress to standard output, which IF-02 reserves. Set it to 0
  before anything else, and collect the messages with `gmsh.logger` instead. Pass
  `readConfigFiles=False` too, or a user's `~/.gmsh-options` changes a mesh under an unchanged key.
  Pass `interruptible=False`, because the default installs a SIGINT handler, which only the main
  thread may do.
- **A stage-5 region goes into the built-in `geo` kernel from netgen's own coordinates.** Reading
  `set(shape.vertices)`, `set(shape.edges)` and each face's `set(face.edges)` off the glued shape
  gives the graph: 193 vertices and 195 edges on the ClyA fixture. Its face areas, in closed form
  (Green's theorem, `½(a × b)` per segment and `½R²Δθ` per arc), agree with OCC's `face.mass` to
  1e-15 on the electrolyte and 1e-12 on the membrane. No BREP passes between netgen-occt and Gmsh's
  own OpenCASCADE. Every region vertex survives as a mesh node, the 185 profile vertices included.
- **The only curved edges are the reservoir arcs, and each spans less than π,** which
  `geo.addCircleArc` requires. OCC's seam at `(R, 0)` is what splits the membrane's outer arc in two.
  A straight edge is told from an arc by its parameter midpoint lying on its chord, to 1e-9.
- **A clockwise curve loop meshes every triangle of its surface inverted.** On the coarse
  parallelogram region, the protein's loop handed to Gmsh reversed gave 14 triangles, all 14
  inverted. Orient each loop counter-clockwise by its signed area before `addCurveLoop`, as the
  pore face is oriented for OCC above.
- **Given only §5.2.2's size table, Gmsh does not match netgen's quality.** Netgen limits the
  element size near short edges and close edges by itself, and grades outwards from a face's
  `maxh`. A Gmsh `Constant` field does neither. On the fixture, with the table as `Distance` and
  `Threshold` sources and `Constant` domains, the minimum gamma is 0.3143 against VER-10's 0.3.
  With the domain boundaries also as graded sources it fails at `size_scale` 2 (0.2084, beside a
  0.0412 nm profile edge) and at 4 (0.2348, where the 2.8 nm membrane strip meets the arc). The
  field the backend uses fixes that: sources `h + 0.2 d` on every sized boundary and domain
  boundary, on each vertex whose shortest curve is shorter than its curves' smallest target, and on
  the membrane at its unscaled thickness. Its minimum gamma is 0.5840, 0.5241, 0.5655 and 0.5072
  at `size_scale` 1, 2, 4 and 8. `Mesh.MeshSizeExtendFromBoundary` 1 is the tempting shortcut. It
  doubles the element count, to 95,103 at `size_scale` 1, and still gives only 0.3876 at 4.
- **Frontal-Delaunay (`Mesh.Algorithm` 6) is the algorithm, and one thread makes the mesh
  reproducible.** With the table-only field, algorithm 5 gives 10 % more triangles at a mean gamma
  of 0.95 against 0.99, and MeshAdapt (1) is slower and worse (WP23 plan, Design §3). `Mesh.Smoothing`
  5 is its optimisation pass, as `optsteps2d` is netgen's. With `General.NumThreads` and
  `Mesh.MaxNumThreads2D` at 1, two fresh processes give one content hash.
- **Gmsh's wall runs at or under its target, and netgen's over it.** With the backend's field on the
  fixture, the mean `wall` segment is 0.909, 0.931 and 0.945 of the target at 0.05, 0.03505 and
  0.02715 nm, and the longest is 1.029–1.055 of it. Netgen's mean is 1.045–1.078. The mesh has
  48,941 triangles in 3.3–4.2 s, against netgen's 44,316 in 6.4–7.0 s.
- **`Distance`'s sampling option is `Sampling`** (formerly `NumPointsPerCurve`). A source curve
  needs about `⌈L/h⌉` samples, so a reservoir arc hundreds of nm long, sized at 5 nm, needs 80 or
  more, where the default is 20.
- **The wheel can install and still fail to import.** On a bare Linux container `import gmsh`
  raises `OSError: libGLU.so.1`, not `ImportError`. A dispatch that turns a missing extra into a
  refusal has to catch both, as `tests/conftest.py`'s `import_gmsh` does for the tests.
- **On `ubuntu-latest`, four packages make it import [tested].** GitHub's image lacks
  `libGLU.so.1`. After `apt-get install --no-install-recommends libglu1-mesa libxft2 libxinerama1
  libxcursor1`, Gmsh 4.15 imports and meshes on Python 3.11 to 3.14 (WP23 PR, run 36574260470,
  29 September 2026).
- **Session cleanup and borrowed sessions [tested].** `gmsh_backend._session` records each undo step (`gmsh.model.remove()`, restoring options, `gmsh.finalize()`) only once the change it reverses has been made, and runs every recorded step in reverse order, so a session it opened is finalised even when an intermediate step or the setup itself fails, and a borrowed session's own model is never removed in place of one that was never added. When an exception is active during cleanup, secondary failures are logged at WARNING and attached to the exception via `add_note()`, preventing the original error from being masked (REV-38). A borrowed session (`gmsh.isInitialized()` true on entry) leaves the caller's logger untouched (no `start` or `stop`), preserving caller messages (REV-36). If `gmsh.initialize()` fails, a `GmshInitialisationError` is raised, translated to `MissingExtraError` naming `gmsh` (REV-37).
- **The IF-07 export samples a fluid-restricted field through a whole-domain carrier [tested].**
  Point evaluation of a space built with `definedon=fluid` returns zero at an interface node whose
  point search lands in a membrane element. On the coarse four-material pore that is 16 of the 208
  fluid nodes, with a maximum error of 13.0 against a linear test function. Interpolating into a
  whole-domain space of the same order first and evaluating that is exact to 5.5e-14, because a P2
  node's value depends only on the entities carrying it, each a fluid entity (`post/export.py`
  `sample_at`).
- **meshio 5.3.5 reads an XDMF `Information` element only in its own `field_data` encoding
  [tested].** Children carry `key` and `dim` attributes with integer text; anything else raises
  `ParseError`. The IF-07 scale set is therefore written as HDF5 root attributes (`post/export.py`).
- **Discontinuous export fields are cell-centred [verified].** `material_id` and `eps_r` jump across
  a material interface, so a node value there is one side chosen arbitrarily and a viewer draws a
  ramp across every boundary element; a barycentre lies strictly inside its element, so the point
  search is unambiguous.

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

The renderer itself is npm `webgui`, `"license": "LGPL-2.1-or-later"` (npm registry metadata,
**[verified]**). Its tarball for 0.2.39 is 503,052 B, and its published `dist.integrity` is
`sha512-yDd6YR7E…Zubqw==`. The 1,206,946 B figure npm reports is the *unpacked* tarball. The file a
page loads, `package/dist/webgui.js`, is **779,484 B**: a minified IIFE that defines the global
`webgui`.

That build **bundles two further works**: three.js r152 (MIT, which keeps its `@license` banner)
and dat.gui 0.7 (Apache-2.0, which keeps no banner). The tarball also carries `src/*.ts`, the
shaders and the vite configuration, so it is the corresponding source of the LGPL part as it
stands. **[tested]**, 22 September 2026.

`cdn.jsdelivr.net` answers this development container's proxy with 403, but
**`registry.npmjs.org` does not**. The tarball downloads here, and its SHA-512 matches the
published integrity exactly. That is how it is vendored: `third_party/webgui-0.2.39.tgz`, with
`webgui.js` shipped from it under `nanopnp/gui/assets/webgui/`.

Loaded from there as a `file:` URL by a host document that is itself a `file:` URL in another
directory, it reaches the page in Qt WebEngine 6.11.2. `renderer_loaded` is true offline, both in
the frozen probe bundle and in a plain `QWebEngineView`. With no GPU, `new webgui.Scene()` then
throws `TypeError: Cannot read properties of null (reading 'getExtension')`: WebGL has no
context, which is a property of the machine and not of the renderer.

### A webgui scene draws on a material *region*, not only on a whole mesh **[tested]**

Measured 21 September 2026 on a restored four-material ePNP-NS solution, 124 triangles.
`Draw(cf, mesh.Materials("electrolyte|cis|trans"), show=False, order=2).GetData()` succeeds and
returns a smaller scene than the whole-mesh draw of the same field (30.5 kB against 43.1 kB here),
because it carries only the retained elements.

That matters for honesty rather than for size. A field declared on the fluid alone evaluates to
zero inside the membrane, and a whole-mesh draw of a concentration therefore paints a zero *inside
a wall* that a reader cannot distinguish from a converged depletion — which is the same trap
`post/export.py` documents for the IF-07 export, and it is avoided the same way.

The same call draws a **two-component vector** field without special handling: all five fields of
the `epnp-ns` family (the potential, two concentrations, the velocity and the pressure) produce a
scene from one code path, the vector one costing about 1.5x the scalars.

### A fixed colour range needs the scene's keys and the viewer's own settings **[verified]**

webgui 0.2.39 has one colour map per scene, and by default it autoscales to the sampled
`funcmin`/`funcmax`, which `Draw(...).GetData()` returns. A diverging map centred on zero, or χ on
[0, 1], needs that range fixed, and the scene keys alone do not fix it. `funcmin`, `funcmax` and
`autoscale: false` in the scene set the defaults. The viewer then reads `gui_settings`, maps its
`autoscale`, `colormap_min` and `colormap_max` onto its `Colormap` settings, and autoscales again
unless `gui_settings.autoscale` is false too. So `gui/render.py` writes all five. Read from the
shipped `webgui.js` and from the scenes the render child writes, 2 October 2026 (WP31 D8). The
fixed range has not been watched drawing in a browser here, because this container has no GPU for
WebGL.

### `QWebEngineView` can be constructed in this container with the Playwright GL shim **[tested]**

Measured 21 September 2026. With `libEGL.so.1` and `libGLESv2.so.2` symlinked from
`/opt/pw-browsers/chromium-*/chrome-linux/` onto `LD_LIBRARY_PATH`, and
`QT_QPA_PLATFORM=offscreen`, both `from PySide6 import QtWidgets` and
`from PySide6.QtWebEngineWidgets import QWebEngineView` succeed and the whole Tier-1 widget suite
runs — including a `QPainter` repaint into a `QPixmap` and a `QWebEngineView` construction.

This is the §5 shim recorded above, used for the purpose that section already states: checking
widget code that would otherwise ship having never been executed. It stays off the push gate, where
widget coverage remains `windows-latest` and `macos-latest`.

### SIGTERM stops a child busy inside netgen in milliseconds **[tested]**

Neither netgen nor NGSolve installs a SIGTERM handler, so the signal's default action ends a
`spawn` child at once even while it is inside compiled meshing code; only a Python-level handler
would defer it until the interpreter is re-entered. Measured: a child in `GenerateMesh(maxh=0.002)`
joined **14 ms** after `terminate()`, exit code −15. `RenderProcess.terminate`'s synchronous join
therefore does not stall the Qt thread, and it is what keeps two render children of one run from
sweeping each other's files. (Codebase review of 2026-09-28.)

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

### The geometry payloads bundle through `collect_all`; Gmsh's library does not **[tested]**

Measured 29 September 2026 on a Linux rebuild of the probe recipe in this container (WP24 D16, D17):
PyInstaller 6.22.3, MDAnalysis 2.10.0, gemmi 0.7.5, scikit-image 0.26.0, Shapely 2.1.2 with GEOS
3.13.1, and Gmsh 4.15.2. The Windows bundle is the gated `bundle` job's to confirm; nothing here
was measured on Windows.

**MDAnalysis, gemmi, scikit-image and Shapely need nothing but `collect_all`.** It carries
Shapely's GEOS pair from `shapely.libs/`, and the frozen `--selftest` exercises all four. Their
footprint in `_internal/` is:

| Payload | Size |
|---|---|
| MDAnalysis | 45 MB |
| scikit-image | 30 MB |
| gemmi | 6.8 MB |
| Shapely | 5.0 MB, plus 5.6 MB of GEOS |

**Gmsh repeats the OCCT problem, differently.** The wheel installs `gmsh.py` in site-packages and
`libgmsh.so.4.15` in `lib/` at the environment root; on Windows it is `Lib/gmsh-4.15.dll`.
`gmsh.py` does not use metadata to find it. Instead it tries a fixed list of paths relative to its
own `__file__`, and then `ctypes.util.find_library`. The first path is the module's own directory,
which for a PYZ module in a one-dir bundle is `_internal/`. So the library goes to the bundle root,
and Gmsh then loads unchanged. The library is 89 MB.

**`import gmsh` succeeds without its library.** With `libgmsh.so.4.15` removed from the built
bundle, the import prints a warning listing the paths it searched and returns. The first call then
raises `AttributeError: ...: undefined symbol: gmshInitialize`. A probe that only imported Gmsh
would pass on a bundle that cannot mesh. This is why the probe exercises each payload once, and it
is RSK-13's failure in its plainest form.

The whole bundle is 1.3 GB, 501 MB of it PySide6, and builds in 74 s. The five exercises take
0.46 s together, unfrozen. One detail of the exercise: `skimage.measure.find_contours` needs an
ndarray and raises `AttributeError: 'list' object has no attribute 'shape'` on a nested list. The
probe therefore builds its 3 × 3 input with `skimage.morphology.disk(1)`, so that it imports no
undeclared NumPy.

### PDB2PQR and PROPKA bundle through `collect_all`, and fail inside PDB2PQR's run **[tested]**

Measured 2 October 2026 on a Linux rebuild of the probe recipe in this container (WP31 D14, D15),
with PyInstaller 6.22.3, PDB2PQR 3.7.1 and PROPKA 3.5.1. As with the geometry payloads, Windows
is the `bundle` job's to confirm.

**Both are pure Python, and both find their data through `Path(__file__).parent`.** For PDB2PQR
that is `pdb2pqr/dat/`, the force-field and naming files. For PROPKA it is `propka.cfg` and
`protein_bonds.json`. `collect_all` puts both trees beside the modules in `_internal/`. The frozen
`--selftest` then protonates `GLU 18`–`LEU 26` of 2WCD chain A to +0 e at pH 2 and −3 e at pH 8,
the unfrozen values. The cost to the bundle is small:

| Payload | Size in `_internal/` |
|---|---|
| PDB2PQR | 1.1 MB, of which `dat/` is 0.50 MB |
| PROPKA | 0.34 MB, as 26 source files and its two data files |
| GridDataFormats | 0.12 MB, as source files |

The whole bundle is 1.23 GB and builds in 2 min 25 s from clean. The exercise takes 0.82 s unfrozen
in a fresh process, and 0.23 s once warm.

**A missing data file surfaces out of PDB2PQR's run.** With `propka.cfg` removed from the built
bundle, the run raises `FileNotFoundError` naming the file. With `pdb2pqr/dat/` removed, it raises
a bare `AssertionError` from `pdb2pqr.io.test_for_file` (`assert dirpath_dat.is_dir()`). Both come
out of `pdb2pqr.main.run_pdb2pqr`, so a probe that named the failing call would name PDB2PQR for
PROPKA's missing file. The probe names the library whose code is in the traceback instead. PDB2PQR
calls PROPKA and PROPKA never calls back, so a traceback that enters PROPKA's directory is PROPKA's
failure. Rebuilt and rerun, the bundle without `propka.cfg` fails naming `propka`.

**`module_collection_mode="py"` puts the modules on disk.** With it set for `propka`, `MDAnalysis`
and `gridData`, each package's modules are in `_internal/` as `.py` files. MDAnalysis keeps its
compiled extensions beside them, at the same 45.7 MB. A traceback through them then carries real
file paths, which is what lets the probe tell PROPKA's failure from PDB2PQR's.

**Without a titration method, the pH reaches nothing.** With `--with-ph` and
`--titration-state-method` removed, PDB2PQR runs cleanly and gives equal charges at pH 2 and pH 8
(section 3). So the probe compares the two charges, and fails naming PROPKA when they are equal.

In this container the frozen `--selftest` stops at Gmsh, because `libGLU.so.1` is not installed.
The figures above come from a local build whose selftest left Gmsh out. That edit was never
committed.

### The geometry tab's view-models stay under the schema's cost **[tested]**

Measured 29 September 2026, best of three fresh processes, warm cache:

| Module | Cost |
|---|---|
| `nanopnp.gui.geometry` | 157 ms |
| `nanopnp.gui.assess` | 52 ms |
| `nanopnp.gui.run_model` | 200 ms, the comparison |

Neither of the two new modules brings in PySide6, NGSolve, Netgen, NumPy, MDAnalysis,
scikit-image, Shapely or Gmsh. `nanopnp.gui.assess` imports `geometry.contour`, and with it
scikit-image, only inside the spawned child. A drag on the editor canvas can be driven offscreen by
sending `QMouseEvent`s through `QApplication.sendEvent`: press, move, release. That is how
`test_gui_widgets.py` asserts it.

### `nanopnp.io.case` pulls in neither NGSolve nor NumPy, and costs 250–350 ms **[tested]**

Measured 20 September 2026 on the development interpreter (3.12). After `import nanopnp.io.case`,
`"ngsolve" in sys.modules` and `"numpy" in sys.modules` are both `False`. The cost is pydantic and
PyYAML building the `nanopnp/case/v1` model tree, paid once.

So a caller can enumerate, display and validate an entire case document without the solver — which
is what lets a schema-generated editor stay near the CLI's 56 ms stage-introspection budget in
spirit, with NGSolve imported only in whatever process actually solves. `io/case.py` imports only
`core` at run time: the registry checks that need `materials` and `physics` live in
`pipeline/checks.py`. After `import nanopnp.io.case` the only `nanopnp` subpackages in
`sys.modules` are `core` and `io` **[tested]**, 6 October 2026. `import nanopnp.pipeline.case`,
which `load_case` and `resolve` come from, also loads `charge`, `density`, `geometry`, `materials`,
`mesh`, `numerics` and `physics`, and still leaves `ngsolve` and `numpy` out of `sys.modules`; that
holds because those modules defer their own NGSolve and NumPy imports.

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
| `nanopnp.gui.run_model` | 273 ms | the above, plus `io/manifest.py` and `pipeline/run.py` |
| `nanopnp.gui.solver` | 73 ms | `core/errors.py` and `multiprocessing`; everything else is deferred into the child |
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
dynamically linked. gemmi is MPL-2.0. That copyleft is file-level, so it is fine used unmodified as
a separate package (CON-09, amended 25 September 2026).

---

## 7. Local assets

| Path | What |
|---|---|
| `thesis/` | `github.com/willemsk/phdthesis-text`, CC-BY-4.0. LaTeX source of the full thesis incl. all parameter tables |
| `data/corrections/willems2020_nacl.yaml` | The fitted ePNP-NS correction parameters, transcribed and numerically verified |
| Author's contour script | **Read, 26 September 2026**: `create_polygon_contour` in the author's `pqr2grid` (`~/repos/pqr2grid`, MIT, 2019). It is marching squares, the first contour, and Douglas–Peucker at 0.1 nm, with a radial-binning erratum. → `04-clya-geometry-and-charge.md` §1.2 |
| COMSOL models | Author retains a licence and can regenerate reference solutions on demand — the project's numerical oracle |

---

## 8. Python version floor — the 3.10 target is not free

**Resolved, 24 September 2026 [tested]: the floor is now 3.11** (§8.2.2 B4, WP17). With
`requires-python = ">=3.11,<3.15"` and the `structure` extra at `MDAnalysis>=2.10`,
`GridDataFormats>=1.2`, `pdb2pqr>=3.7`, `uv lock` resolves one version of each across the range:
MDAnalysis 2.10.0, GridDataFormats 1.2.0, pdb2pqr 3.7.1. The 3.10 splits the lock carried for
numpy, scipy, scikit-image and tifffile went with it. The rest of this section is the analysis that
led there.

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
`CLAUDE.md` runs on the development interpreter — 3.14 — so a 3.11+ stdlib API compiles, typechecks
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

**The development interpreter is 3.14, and it computes VER-62's numbers as 3.12 does [tested].**
`uv.lock` splits its resolution only at 3.12, so 3.12 and 3.14 install the same version of every
package (NumPy 2.5.2, SciPy 1.18.0, NGSolve 6.2.2606), each from a wheel (cp314, abi3 or pure Python; none built from source). On CPython
3.14.6, `linux-x86_64` with NumPy's dispatch capped at `X86_V3` (`NPY_DISABLE_CPU_FEATURES`, as CI
and the gate set it), the six walk files of the number-stability golden pass under `--extended`:
all seven walks deploy their recorded reference mesh, and the largest relative drift against the
golden recorded on 3.12 is 6.9 × 10⁻¹⁴ (example 01's `eof_m3_s`; every other walk at or below
2.7 × 10⁻¹⁵), 12 October 2026 (WP43, D12). Every locked package has a cp314 wheel on Linux, macOS
and Windows except `watchdog` on macOS arm64, which only the `docs` group pulls and the
documentation builds on ubuntu. PROPKA needs the 3.14 shim of §3 there as everywhere.

---

## 9. The CLI's import budget, measured **[tested]**

`import nanopnp.cli` costs **55.6 ms cumulative** (`python -X importtime`), and a cold subprocess
that imports it and exits takes **0.082 s**. `import ngsolve` alone is ~370 ms, and the physics and
mesh modules at module scope would take the package's own share from 56 ms to 424 ms. A sweep
dispatching a job array pays that per process, which is what the deferred-import rule of
`CLAUDE.md` buys. `import numpy` alone is ~67 ms, which is why `core/hashing.py` detects arrays by
duck-typing rather than importing NumPy **[tested]**.

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

The 12-hex-character display prefix (`core.hashing.SHORT_LENGTH`) is 48 bits; over the 3,675-solve
datum at about six artefacts each (n ≈ 2.2 × 10⁴) the collision probability is n²/2N ≈ 8.6 × 10⁻⁷, adequate
for a label. The store keys on the full digest, never on the prefix **[verified]** (`core/hashing.py`).

## 11. A stage's workspace falls back to the process store root, not the run's store **[tested]**

`mesh/ingest.py`, `charge/stage.py`, `solve/stage.py` and `post/stage.py` each fall back to
`store_root() / "tmp"` plus a `mkdtemp` when constructed without a workspace — and `store_root()`
is `$NANOPNP_STORE` or `./nanopnp-store`, the *process* default, never the `Store` the caller
handed the run. Running the test suite from a checkout therefore left a `nanopnp-store/tmp/mesh-*`
behind while every artefact lived in a `tmp_path` store.

`pipeline.run.run_case` now names a fresh workspace under the store in use when the caller gives none.
Fresh per run and not a fixed `tmp/mesh`: two runs into one store hold different meshes, and a
deterministic name has the second overwrite a file the first's artefact still points at.

## 12. The suite's BLAS threads buy nothing; parallelism has to come from workers **[tested]**

Tiers 1 and 2 were measured on four cores, 923 tests, after the VER-36 fix. Serially the suite takes
6m10s whether or not the BLAS threads are pinned to one. Pinned, it uses half the CPU time
(6m07s of user time against about 12 min), so the threads were spinning, not computing: the systems
here are too small to split. Under `pytest-xdist`, `-n 4 --dist loadfile`, unpinned workers
oversubscribe the cores and the suite gets *slower* (7m20s, 26 min of user time). With
`OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS` and `MKL_NUM_THREADS` all set to 1 it takes 3m19s. CI and
the commit gate therefore run `-n auto --dist loadfile` with the three pinned, and the long pole is
`tests/tier2/test_stabilised_mode.py`, whose module fixture (146 s) cannot be split across workers
(`.knowledge/06-numerics-fem.md` §4.3.3).

Re-measured on 30 September 2026, four cores, 1504 tests in the default selection (tiers 1 and 2,
`not slow`, the GUI file apart). Before the changes below: **353 s wall, 1147 s of test time**. The
long pole was still `test_stabilised_mode.py` at 259 s, and six Tier-2 files each walked stages 2 and
3 of the prepared 2WCD (19.7 s and 12.2 s). Two changes, neither touching a weak form or a tolerance:

- the MMS sources are built with shared subexpressions (`06-numerics-fem.md` §4.3.3), which took
  that module from 259 s to 60 s;
- `tests/conftest.py`'s `seeded_2wcd` computes 2WCD's stages 1 to 3 once per session, under a
  `FileLock` in a directory every worker shares, and copies those artefacts into each test's own
  fresh store. The store is content-addressed, so the bytes are the ones the test's own walk would
  write. Tests that assert a *cold* computation (VER-55's build, the example executors, the VER-49
  budget) do not take the seed.

After both: **271 s wall, 852 s of test time**, every test passing. `-m tier2` on the command line
*replaces* the default `not slow` filter and pulls in the `slow` tests: the example-05 ClyA solve alone
is about 30 min on one core. Pass `-m 'tier2 and not slow'` to time what the gate runs.

`--dist loadfile` keeps each module's fixtures in one worker, so a module-scoped solve is paid once,
as it is serially. A failure that appears only under `-n` means a test depends on the order it runs
in, or on state another module leaves behind, and that is a real isolation defect.

One test measures wall time and therefore fails under xdist for a different reason.
`test_ver44_the_shipped_renderer_reaches_a_document_with_no_network` waits 60 s for a real
QtWebEngine page. On a 3-core macOS runner it passed twice under `-n auto` and then failed once
(run 113), in the window where the other two workers were in the heavy solver modules. That points
to Chromium's helper processes being starved of CPU. It is not proven, because macOS was not
reproducible from here. CI and the gate therefore run `tests/tier1/test_gui_widgets.py` serially and
alone. The wait and the assertion are unchanged.

Re-measured on 3 October 2026 for WP33, one core, `OMP_NUM_THREADS=1`, the same four-core
container, 1,781 tests: **1,508.9 s of test time before and 1,334.5 s after**; four workers under
`-n auto --dist loadfile`, 458 s and 394 s of wall clock. Example 07 alone is 312 s, cold by design.
What was learnt on the way, each measured:

- **Profile before sharing.** In VER-58's grounded-sphere test the mesh was 3 s and the lattice
  0.08 s of a 21 s solve; the closed-form oracle at 257,750 quadrature points was 19.4 s. A test's
  own oracle can be the cost, and evaluating it once per mesh rather than once per deposit order is
  sharing, not weakening it. A periodic trapezoid rule over an integrand even in `θ` can be summed on
  `[0, π]` with interior points doubled: the same rule, 7× cheaper there, equal to 9.5 × 10⁻¹⁶.
- **On 2WCD, stage 4 is 0.41 s and the C-alpha registration 3 ms; the default-size mesh is 8.2 s.**
  Seeding to the mesh is what saves time; seeding to the contour saves nothing.
- **An NGSolve mesh pickles to the bit, and a `.vol` does not**: the text format moved the ClyA
  reference mesh's vertices by up to 5.6 × 10⁻¹⁷ nm, enough to change its geometry digest.
- **Under the serial order, the first file to ask for a session seed carries it** (`charge_2wcd`,
  99.9 s of setup). Read a per-file time with that in mind; between two baseline runs a single
  file's time also varied by up to 20 %.
- **`copy.deepcopy` and per-call `TypeAdapter` construction** were half of `build_plan` on the
  3,675-member sweep (12.3 s → 7.0 s once removed, WP33 D12).
- **Parsing the correction YAML dominated planning until it was cached by text.** PyYAML's pure-Python
  parser was 92 % of planning the 3,675-point reference sweep (29.4 s against 4.3 s cached); the cache
  is keyed on the file text, not on path and mtime, so an edit is re-parsed however quickly it was
  written (source: `materials/corrections.py`, `_parse`). **[tested]**
- **Where the suite's time goes** **[tested]**, after WP33. The 54 `extended` tests are the
  executed examples and the 2WCD walks. They are 3 % of the tests and 59 % of the test time: the
  development selection without them is 542.9 s of test time and 168 s of four-worker wall, against
  1,334.5 s and 394 s with them. Deleting duplicated or history-pinning tests recovered about 1 s.
  A walk is slow because it composes the stages, not because it repeats a check.
- **pytest: a custom option, not `addopts -m`, for a selection a named file should override.**
  `--extended` is read in the root conftest's `pytest_collection_modifyitems`, which keeps an
  `extended` item whose file is named on the command line. A `-m` in `addopts` would deselect it
  even then, and the user would have to restate the whole marker expression.

### 12.1 Test-impact selection was built, measured and removed **[tested]**

WP43 built a recorder (`sys.monitoring` `PY_START`, `DISABLE` after the first hit, re-armed per
test) and a selector for the commit hook; WP44 deleted both (§8.2.11 L2). Recording cost about 1 %
(four shared cores, `-n auto --dist loadfile`, Python 3.12.3, 2,129 tests: 239.8 s without and
240.0 s with it; coverage's per-test contexts cost +83 %). Selection did not pay: most past commits
fell back to the whole development selection, and the recorder, selector and map were about 1,400
lines of code and test. What stays true:

- **A warm `functools` cache hides a dependency from every test but the first**, so a recording of
  what a test touched must empty the caches first (`validation/modularity.py` caches its parse of
  every module).
- **A throwaway index must keep the real index's mtime.** Git re-reads an entry as racy only when
  the file is no older than the index file, and under `core.checkStat=minimal` it compares only
  whole-second mtimes and sizes. Copied with a fresh mtime, the index hid a same-size edit made in
  its second, and `git add -A` wrote the old tree. Copy it with `cp -p`; `gate.sh` does.
- **`sys._getframe` raises an audit event of its own**, and a `co_filename` can be `<frozen runpy>`
  or `<string>`, which `realpath` resolves against the working directory.

### 12.2 Where the time goes on 3.14, and coverage's `sysmon` core **[tested]**

Measured for WP43 D8 on 12 October 2026: CPython 3.14.6, coverage 7.15.4, pytest-cov 7.1.0, four
cores shared with another agent's runs, `-n 4 --dist loadfile`, BLAS threads 1,
`NPY_DISABLE_CPU_FEATURES` at the X86_V3 cap, the GUI file left out, tree `f2e48e9` plus the
ordering conftest (the order's re-measurement, below, on a quiet machine). Each figure carries the 1-minute load average at its start and end.

- **Per-file time**, from a `--durations=0` log of the development selection with `--extended`
  (2,176 passed; 510 s wall, load 0.5 rising to 3.9): 1,849 s of test time in 141 files, of which
  the 16 wholly `extended` files are 1,070 s and the development selection 778 s. Example 07 alone
  is 416 s, the 2WCD VAL-06 and charge walks 128 s and 125 s. No file mixes `extended` and
  development tests. The longest development file is 60.5 s (`test_exclusion_stern.py`); the median
  file 2.0 s.
- **Longest-first order is inert under xdist's defaults.** pytest-xdist 3.8's `loadfile` (a
  `LoadScopeScheduling`) re-sorts the files by their number of tests, most first, unless
  `--no-loadscope-reorder` is passed (`--loadscope-reorder` defaults to true), so the collection
  order only breaks ties, and example 07, which holds few tests, still starts late. Re-measured on
  a quiet machine (WP43 item 10, tree `4d9c306`, load under 1 at the first start; the same flags,
  `--extended`, no coverage), back to back: **534 s and 512 s** in the default schedule with the
  order, **477 s** without a duration record (path order, then re-sorted), and **474 s** with
  the order and `--no-loadscope-reorder`. The spread between the two like runs, 22 s, is as large
  as any difference between schedules; every run sits on example 07's floor, 421 to 477 s alone, so
  no order can gain more than the minute above it. The same 2,213 tests pass in each. The earlier
  measurement under another agent's load (937 s ordered against 830 s in path order) is noise of
  the same kind.
- **`COVERAGE_CORE=sysmon` against `ctrace`**, the development selection under
  `--cov=src/nanopnp --cov-branch`, 2,118 passed: **292 s** (load 4.4 to 6.7) against **511 s**
  (6.7 to 7.8). The two XML reports are byte-identical once the `timestamp` attribute is removed:
  21,879 lines and 5,058 branches valid, 18,888 and 3,944 covered. **coverage 7.15 already
  defaults to `sysmon` on CPython 3.14 and later** (`coverage/env.py`, `SYSMON_DEFAULT`), with
  branch coverage, so the gate and CI use it without configuration; pinning `core` in
  `pyproject.toml` would make every coverage run on 3.11 to 3.13 warn and fall back.
- **pytest-cov's `no_cover` marker stops coverage for the call phase only**
  (`pytest_runtest_call`): a fixture's setup is still measured. The root conftest puts it on every
  `extended` item, so the walks no longer pay the tracer in their calls, where their time is.

## 13. Documentation tooling: MkDocs, Material and Zensical

Read 23 September 2026 from the publishers' own announcements. **Not tested here**; the WP16
implementation confirms the versions it pins against current releases (Context7) before locking.

- **Material for MkDocs has been in maintenance mode since 5 November 2025.** Its maintainers fix
  critical bugs and security issues for at least twelve months from then, and add no features.
  Feature work moved to **Zensical**, an MIT-licensed successor from the same team, which reads an
  existing `mkdocs.yml`.
  → [squidfunk.github.io/mkdocs-material/blog](https://squidfunk.github.io/mkdocs-material/blog/)
- **MkDocs 2.0 is not compatible with Material.** A Material site therefore pins `mkdocs<2`.
  → [What MkDocs 2.0 means for your documentation projects](https://squidfunk.github.io/mkdocs-material/blog/2026/02/18/mkdocs-2.0/)
- **Zensical renders mkdocstrings API pages** (since its 0.0.11 release), but **cross-references and
  backlinks between pages are not yet supported**.
  → [zensical/zensical#237](https://github.com/zensical/zensical/issues/237),
  [release 0.0.11](https://github.com/zensical/zensical/releases/tag/v0.0.11)

What follows from those three facts: a Material site today pins `mkdocs<2`. It stays portable to
Zensical only if its `mkdocs.yml` avoids what Zensical does not read, such as MkDocs `hooks:` and
plugins it has no shim for. A page generated by a separate step before the build is portable, and
one generated by a build hook is not.

**What the build actually did, 23 September 2026 [tested].** Locked by WP16 at MkDocs 1.6.1,
mkdocs-material 9.7.7, mkdocstrings 1.0.6 and mkdocstrings-python 2.0.9 (griffe 2.3.0), on
Python 3.12:

- `mkdocs build --strict` over the twenty public names of `nanopnp.__all__`, with
  `docstring_style: numpy`, emits **no warning**. The package's NumPy-style docstrings parse as they
  stand, and their Sphinx roles (`` :func:`…` ``, `` :class:`…` ``) render as literal text rather
  than failing the build. So the strict build gates links and navigation, not docstring prose.
- mkdocstrings-python reads the source statically through griffe. It never imports `nanopnp`, so
  the API page builds without NGSolve. `docs/scripts/generate.py` does import it, to render the
  case-file, CLI and exit-code references, which is why the `docs` group is synced on top of the
  project and not in place of it.
- Material 9.7 prints a boxed "MkDocs 2.0" warning to standard error on every build. It is not a
  MkDocs log record, so `--strict` does not count it.
- Setting `validation.nav.omitted_files`, `validation.links.not_found`, `anchors`,
  `absolute_links` and `unrecognized_links` to `warn` makes `--strict` fail on each of them. The
  MkDocs 1.6 defaults leave several at `info`, which strict mode ignores.

## 14. A Windows checkout rewrites the bytes a hash identifies **[tested]**

GitHub's Windows runners, and most Windows installs of git, check out with `core.autocrlf=true`, so
every text file in the index arrives with CRLF line endings. Any hash over a checked-out file's
bytes then differs by platform. `file_hash` is such a hash, and it is the version of a correction
file (FR-25) and part of the stage-8 materials key: on WP17's branch the VER-47 materials keys,
recorded on Linux, failed for all 13 corpus cases on Windows alone, and converting
`data/corrections/willems2020_nacl.yaml` to CRLF reproduces the same 13 failures on Linux.

A wheel is not affected — it ships the committed bytes — but a source checkout is, and that is what
CI and developers run. `.gitattributes` marks `data/**` `-text`, as it already did the vendored
renderer, so a checkout keeps the committed bytes (LF for the YAML, CRLF for the verbatim
`clya_as_radial_geometry.csv`). A new directory of files identified by their hash needs the same
line.

## 15. An `.npz` is reproducible bytes only if nothing in it moves with the clock **[tested]**

`numpy.savez` writes a zip whose entries carry a fixed modification date, so the same arrays saved
twice give the same bytes, seconds apart. A payload's recorded digest is therefore reproducible as
long as the arrays are. One scalar that is not, such as a wall-clock duration saved beside the
data, changes the bytes and so the digest: stage 7 once wrote `seconds` into `deposit.npz`,
and the same deposit computed twice read as two different payloads, and a reloaded one would have
read as hand-substituted (VER-23). The same holds for a summary the manifest copies: a time in it
gives every run its own manifest hash.

The rule (WP32 D15): no payload, and no stage-7 summary, records wall-clock time. Timings go
to the log and to the run record's per-stage `seconds`, which no key or manifest reads.
`tests/tier1/test_artefact_hashing.py::test_ver23_a_charged_walk_writes_the_same_bytes_into_two_stores`
walks a charged tube into two empty stores, finds every payload byte-identical, and shows that
restoring one `seconds` entry breaks it. Source: WP32 plan D15 and its Outcomes.

**Removing the time is a schema change, not just a code change [verified].** A store hit serves the
stored payload and summary unchanged, and the content hash covers the schema, the parameters and the
input hashes, not the payload. An entry written before the change keeps its key, so it keeps being
served with its old timings. Stage 7 therefore moved to `nanopnp/fields/v2` and
`nanopnp/charge-grid/v2`, which makes every old entry a miss (§5.3.2 stage-7 row, amended for WP32).
Source: the WP32 `/wp-ship` review.

## 16. NGSolve's bundled stubs cannot type-check, so the aliases in `core/typing.py` are `Any` **[tested]**

NGSolve 6.2.2606 ships pybind11-stubgen output (24 `.pyi` files) but no `py.typed` marker, so mypy
skips them (PEP 561) and every NGSolve name resolves to `Any`. Supplying the marker only exposes that
`ngsolve/__init__.pyi` does not parse (it ends in `ngslib =` and `ngsolve =` with empty right-hand
sides). Netgen ships no stubs. The aliases of `core/typing.py` therefore stay `Any` and name what a
value is, until upstream ships stubs that parse behind a marker (source: `core/typing.py`).

## Tier-1 test evidence: the viewer and the positivity gate (WP45 item 21)

- **[tested]** A webgui scene of the reference mesh is 23 to 39 MB, and it is written twice, once as data and once inside the document. The render child therefore keeps only one field's pair and re-renders the next field, about a second, rather than keeping five. Source: `tests/tier1/test_gui_render.py` (`test_ver44_only_one_fields_scene_is_kept`).
- **[tested]** On Linux, `Set` projects element-wise, so a coordinate field set to zero at a wall comes back as about -3e-16, not 0; the positivity gate therefore evaluates the coefficient function, which samples `x = 0` exactly. **[verified]** The test's author records the same round-off, of positive sign, on macOS and Windows. Source: `tests/tier1/test_gates.py` (`test_ver08_positivity_gate_rejects_exactly_zero`).

## Tier-1 test evidence: the mesh seam and the layering ratchet (WP45 item 22)

- **[tested]** meshio writes a whole cell block under the first geometrical tag it carries, so boundary groups packed into one block all read back under the first group's name, with no error raised. Source: `tests/tier1/test_mesh_adapter.py` (`test_if06_a_tagged_mesh_survives_an_msh41_round_trip`).
- **[verified]** Each module into which `io/case.py` was split measures at most 1,266 lines (WP38 D14). Source: `tests/tier1/test_layering.py` (`test_mod13_no_module_of_the_io_split_exceeds_the_bound`).

## Tier-1 test evidence: stores, paths, OCC names, NaN and reduction tolerances (WP45 item 23)

- **[tested]** `Store.put` copies every payload, so a run's scratch workspace would hold a second copy of each. The driver removes the scratch it made once the store holds the payloads and leaves a caller-named workspace alone. Source: `tests/tier1/test_run.py` (`test_ver32_a_run_removes_its_scratch_once_the_store_holds_the_payloads`).
- **[verified]** `repr` doubles every backslash, so a message that quotes a Windows path with `repr` names `C:\\Users\\...` where the file is `C:\Users\...`. A POSIX backslash is a legal file-name character, so a diagnostic check must drive a separator on either platform. Source: `tests/tier1/test_reproduce_diagnostics.py`.
- **[verified]** A boolean result of OCC is a compound and refuses a `name` query, so an edge's name is read off its one face. Source: `tests/tier1/test_primitives.py` (`test_name_edges_leaves_an_already_named_edge_alone`).
- **[verified]** Every ordering comparison with NaN is false, so `if value > tol: raise` is skipped by a NaN; the house form `if not value <= tol: raise` fails it. Source: `tests/tier1/test_nan_gates.py`.
- **[verified]** The sub-agent frontmatter keys that code.claude.com documented on 12 October 2026 are the set that `tests/tier1/test_plan_shape.py` checks.
- **[tested]** The VER-50 tolerances rest on values the WP19 plan recorded when it was written: the off-axis Gaussian's Cn variance is 1.2 × 10⁻⁵ (limit 3 × 10⁻⁵) and its raw variance 3.2 × 10⁻⁴ (limit 10⁻³), with the Cn variance 0.8 % of its peak; the `cos(mθ)` mean is 2.5 × 10⁻⁴ of its peak. Source: `tests/tier1/test_reduction.py` (`test_ver50_off_axis_gaussian_closed_forms`, `test_ver50_cos_modulation`).

## Tier-1 test evidence: import costs, trajectory precision and the gate's pipefail trap (WP45 item 24)

- **[tested]** Import costs under `python -X importtime`, measured for VER-72: `scipy.sparse` ~260 ms, `meshio` ~170 ms, `h5py` ~140–180 ms (`ngsolve` ~370 ms and `numpy` ~67 ms are recorded above). These are why the deferred-import rule names them. Source: `tests/tier1/test_source_conventions.py`.
- **[verified]** NumPy and the BLAS behind it read the thread variables when they are imported and size their pool then, so setting them afterwards has no effect. A forked worker inherits a parent that has already imported NumPy; the sweep pool therefore uses `spawn`, which is also the only start method Windows has. Source: `tests/tier1/test_sweep_cli.py` (`test_ver38_the_thread_pinning_is_set_before_numpy_is_imported`).
- **[tested]** A DCD stores its timestep as a float32: 1 ps reads back as 1.0000000328 ps and 10 ps as 9.99999996 ps, so times accumulated as `frame · dt` drift in opposite directions. The `last_ns` window is therefore taken per frame, and the frame exactly `last_ns` before the last one is always inside. Source: `tests/tier1/test_structure_stage.py` (`test_ver48_the_last_ns_window_does_not_depend_on_the_float32_timestep`).
- **[tested]** TRR stores float32 nanometres, so the ångström-to-nanometre conversion costs up to two float32 ulps at 13 nm (`2 × 2⁻²³ × 13 nm = 3.1 × 10⁻⁶ nm`); XTC quantises to 0.001 nm and rounds by half of that, plus float32 round-off. Source: `tests/tier1/test_structure_stage.py`.
- **[verified]** `grep -q` exits at the first match; under `pipefail` the writer's SIGPIPE once made a tracked Gmsh change read as a miss in the hook's Gmsh requirement check. Source: `tests/tier1/test_workflow_hooks.py` (`test_gate_hook_requires_gmsh_for_a_tracked_change_beside_an_untracked_file`).

## Tier-2 test evidence: budgets, timings and reference checks (WP45 item 25)

- **[verified]** The WP19/WP20 plan predicted stages 2 and 3 on the 2WCD structure at 0.05 nm to take at most 60 s and under 1.5 GB peak RSS (plan, Design §5). The budget test records the wall clock and `ru_maxrss` (kB on Linux) in a fresh interpreter and never gates on them. Source: `tests/tier2/test_density_2wcd.py` (`test_ver49_2wcd_budget`).
- **[tested]** Example 05's frozen solve on the ClyA reference mesh took 2,512 s on one core (WP16 D11 Outcome); its Tier-2 wrapper is `slow` and records rather than gates, and the budget assumes about twice that. Source: `tests/tier2/test_examples_05_clya_reference.py`.
- **[verified]** A PDB coordinate column is written to 0.001 Å, so a written atom lies at most half of that from the true one; the map bound of example 06 therefore allows `√3` times that rounding. For a single Gaussian frame the map at distance `d` from an atom is at least `exp(−d²/(σR)²)`; the grid node nearest the written atom lies within `√3h/2` of it. `R` is the smallest shipped radius of any heavy atom, which gives 0.928 at `h = 0.05 nm` (WP25 plan, Design §2), so a map in nm or with transposed axes fails. Source: `tests/tier2/test_examples_06_pdb_to_mesh.py` (`test_ver46_06_the_exported_map_overlays_the_aligned_structure`).
- **[verified]** A residue table names some hydrogens without a leading `H` (NAD's `NH2T`), so a radius looked up by name filtered on `H` takes a hydrogen's radius and makes a bound vacuous; the lookup goes through the set's own table. Source: `test_examples_06_pdb_to_mesh.py` (comment at the bound).
- **[verified]** Example 07's ePNP-NS solve at `size_scale` 4 (chosen for runtime) takes a few minutes on one core (WP32 D9). Source: `tests/tier2/test_examples_07_pdb_to_charged_run.py`.

## Tier-2 test evidence: analytic benchmarks and reference checks (WP45 item 26)

- **[verified]** A dielectric sphere `ε_p` in a uniform field `E₀` has `φ = −E₀z·3/(ε_p+2)` inside and `φ = −E₀z(1 − βa³/R³)` outside, `β = (ε_p−1)/(ε_p+2)`. With the far boundary carrying `−E₀z` rather than this closed form, the computed field differs from the unbounded one by `β(a/R)³`, 3.3 × 10⁻⁴ at the test's `R`. Source: `tests/tier2/test_maxwell_sphere.py` (`test_ver20_the_dielectric_sphere_matches_its_closed_form`).
- **[tested]** On the test's sphere mesh the magnitude anchor `F_z = qE₀` misses by 0.19 % on the domain route and 0.53 % on the surface route, both set by the straight-sided facets; VER-20 leaves its tolerance open and the test states 1 %. The anchor's reference charge `q = −4e` at 5.1 MV/m is 8.2 pN, inside RSK-04's range. Source: `tests/tier2/test_maxwell_sphere.py`.
- **[verified]** `electrostatic_domain_force` carries no consistency term, which is exact where `div(T_M) = 0` over the region `w` varies on; the fluid of the VER-20 problems is charge-free and uniform, so it is the right entry point. Source: `tests/tier2/test_maxwell_sphere.py`.
- **[tested]** The Gmsh and netgen conductances of the reference fixture at `size_scale` 2 differ by 1.25 × 10⁻⁴; refining netgen from `size_scale` 2 to 1 moves its own conductance by 2.0 × 10⁻⁴. The 1 × 10⁻³ bound in VER-54 is eight times the measured value, chosen from that comparison (WP23 plan, Design §4) and not fitted. Source: `tests/tier2/test_mesh_backends.py`.
- **[verified]** The Taylor-Hood pressure of the MMS problem converges at `O(h²)`, the pair's own rate, and asserting `O(h³)` there would assert something untrue of a correct solver. The MMS sequence is a 2 × 4 nm cylinder at `maxh` 0.4, 0.2 and 0.1 nm, with the finest level near 2 × 10⁴ degrees of freedom, three orders below the 1.04 × 10⁶ at which WP3 measured 41 s and 6.2 GB for one factorisation. Source: `tests/tier2/test_mms.py`.
- **[tested]** The prepared 2WCD structure meshes at the default sizes with VER-10 and the D9 wall gate passing (RSK-05 retired). Its axial registration places the C-alpha centroid of residues 8 to 292 at `Z_MD`; WP21 used the trans tip plus 1.85 nm, which is 0.056 nm away. Source: `tests/tier2/test_pipeline_2wcd.py`.
- **[verified]** The 2WCD walk to stage 12 uses `pnp` at `size_scale` 4, with flow and corrections off, because the electrostatic models refuse a solid domain with no transport to screen it (section 5.3.1 NOTE). Source: `tests/tier2/test_pipeline_2wcd.py`.
- **[verified]** Limiting current of the thin film. With the anion blocked at the electrode, `J₋ = 0` gives `c₋ = A exp(φ̃)`; electroneutrality outside the double layers gives `J₊ = −2D₊ grad c`, linear `c`, and `|J₊| = 2D₊c₀(1 − δ)/L`, so `|J̃₊| = 2D̃₊(1 − δ)/L̃`. The factor 2 is migration doubling diffusion and depends on the reservoir convention, which is why the test states the derivation rather than a published number. Source: `tests/tier2/test_pnp_benchmarks.py` (`test_ver16_current_saturates_at_the_limiting_value`).
- **[tested]** The benchmark's two ionic diffusivities are set equal, a property of the test electrolyte; NaCl's `D_Na` and `D_Cl` differ by 52 %. Source: `tests/tier2/test_pnp_benchmarks.py`.
- **[tested]** The factor 2 holds only where `μ̃ᵢ = D̃ᵢ` (infinite dilution, PHY-14, VER-05). With the concentration corrections active, `μ/μ₀` is 0.63 at 1 M against `D/D₀` = 0.92, the factor falls to about 1.7 and the current drops by about 15 %. An earlier version of this benchmark passed because two errors cancelled: space-charge limitation raised the current by 14 % and silently active corrections lowered it by about as much. Source: `tests/tier2/test_pnp_benchmarks.py`.
- **[tested]** At `δ` = 10⁻³ and classical PNP, the current over the closed form is 1.138 at `L` = 100 nm, 1.050 at 400 nm, 1.026 at 1000 nm and 1.017 at 2000 nm. `λ_D` is 0.30 nm at 1 M but goes as `c^(−1/2)`, so at the electrode's 10⁻³ of bulk it is 9.6 nm, 32 times larger; a 100 nm film is then space-charge limited, which is why the benchmark uses 2000 nm. Source: `tests/tier2/test_pnp_benchmarks.py` (module docstring at `3782c43`, before WP45).
- **[verified]** The ohmic prediction at the top of the sweep, `2Ṽ/L̃` with conductivity `Σ z²μ̃c̃ = 2`, is twenty times what a depleting solve returns at 20 `V_T` (514 mV). Source: `tests/tier2/test_pnp_benchmarks.py` (`test_ver16_the_plateau_is_the_departure_from_ohm_s_law`).
- **[tested]** The quality gate is off for the 2000 nm × 0.5 nm strip at `maxh` 50 nm: it is a chain of 100:1 triangles with minimum SICN 0.019, and the solution is constant along the stretched direction, so the interpolation error of those elements is zero. Source: `tests/tier2/test_pnp_benchmarks.py`.
- **[verified]** The three-layer capacitor: `D(z) = D₀ + ρ₀z` with `D₀ = −(V + ρ₀I₂)/I₁`, `φ(z) = −[D₀F₁(z) + ρ₀F₂(z)]`, `F₁ = ∫₀ᶻ ds/(ε₀ε_r)`, `F₂ = ∫₀ᶻ s ds/(ε₀ε_r)`; `φ` is piecewise quadratic, so P2 on a mesh with edges at `z = a` and `z = b` holds it exactly. The `r` weight adds `RADIAL_WEIGHT_ORDER` to both terms so that they integrate exactly (NUM-07 NOTE). Check values: `L` = 10, `a` = 4, `b` = 6 nm, `ε_f` = 78.15, `ε_s` = 3.2, `ρ₀` = −10⁷ C m⁻³, `V` = 0.05 V, 298.15 K. Source: `tests/tier2/test_poisson_layers.py`.
- **[tested]** Without an entry for the membrane's permittivity, the membrane is ion-free water (`ε_r,f⁰`) and its middle moves by volts; the three-layer test therefore discriminates a model that dropped `solid_permittivities`. Source: `tests/tier2/test_poisson_layers.py` (`test_ver56_the_capacitor_distinguishes_the_permittivity_it_was_given`).
- **[tested]** The reference region has three domains, not four: the cap's underside is re-entrant, and the membrane fills a cleft beneath it that opens downward past the cap edge at `z ≈ −0.7` and is continuous with the bilayer. Source: `tests/tier2/test_reference_geometry.py`.
- **[tested]** The drawn membrane corners `(2, −1.4)` and `(3.5, +1.4)` lie 0.275 and 0.540 nm inside the pore body, so gates read the junction from the fixture (`r_out(−1.4) = 2.7524`, `r_out(+1.4) = 4.88`). A coincident-chain junction gives conforming coordinates and a non-conformal mesh. Source: `tests/tier2/test_reference_geometry.py`.
- **[tested]** The assembled topology adds three vertices and three edges to section 5.2.1's count of 190 vertices and 192 boundaries: two from splitting the axis at the pore's axial extent (the only way the 0.075 nm axis-in-pore size field applies) and one from the seam OCC places on the closed circle at `(250, 0)`. A glued three-face region lists 383 edges and 766 vertices for the 195 and 193 that exist, because OCC reports an edge once per face it bounds. Source: `tests/tier2/test_reference_geometry.py` (`test_ver28_the_assembled_topology_matches_the_section_5_2_1_count`).
- **[tested]** `membrane_outer` is an arc, and its mid-height radius exceeds its ends by the sagitta of a 1.4 nm half-chord. Source: `tests/tier2/test_reference_geometry.py`.
- **[tested]** The derived region's wall statistics were logged at 0.05 and 0.035 nm for the WP21 Outcomes; the derived chord mesh is within 0.1 % of the drawn one's element count. Source: `tests/tier2/test_region_reference.py`.
- **[verified]** A reproduction must not be served from the cache: `Store.get_or_compute` would return the stored solution and show only that a dictionary lookup is deterministic, so the reproduction runs into a store that does not hold the run, and that the fresh store missed. Source: `tests/tier2/test_reproducibility.py`.
- **[verified]** An input whose contents moved since the run is fatal by name, because the reproduction would be a different sum. A library version that moved is recorded, and a quantity comparison catches it if it moved a number; refusing on the version would fail for a reason no number connects to. Source: `tests/tier2/test_reproducibility.py`.
- **[verified]** A deterministic direct solve in one process is expected to reproduce every scalar exactly; the measured worst relative difference is logged so that a drift is visible inside tolerance. Source: `tests/tier2/test_reproducibility.py`.
- **[verified]** The VAL-01 round trip is exactly zero, not 1e-14: `%.17g` round-trips `float64`, so a one-ulp difference is a defect in the transport format. Source: `tests/tier2/test_self_golden_round_trip.py`.
- **[verified]** NGSolve returns `0` outside a `definedon` region, so a masked point must travel as `NaN` through the text format, `np.fromstring` and the archive, or it enters the norm as fabricated agreement. The text reader was verified against the 77 MB reference table to 4.7 × 10⁻¹². Source: `tests/tier2/test_self_golden_round_trip.py` (`test_val01_the_round_trip_preserves_the_masked_points_as_nan`).
- **[tested]** Stabilised mode, MMS: with `supg`, the concentration rate is 2.012 and 2.040 on `maxh` 0.4, 0.2 and 0.1 nm (none: 3 on the same meshes), 26 s (208 s before the manufactured sources shared subexpressions, `.knowledge/06` §4.3.3). With `reference` the Na⁺ rate is 0.984 and the Cl⁻ rate 0.702 against `supg`'s 2.012 and 1.908 on the same meshes, with 31 Newton iterations against 5, and 126 s and 436 s against 7 s and 25 s. Source: `tests/tier2/test_stabilised_mode.py`.
- **[tested]** Withholding the manufactured source `s̃ᵢ` from `R̃ᵢ` makes the error footprint `error(mode)/error(none) − 1` collapse. Intact it is 4.83 and 15.97 for Na⁺ and 2.99 and 15.77 for Cl⁻ at `maxh` 0.4 and 0.2 nm; withheld, 0.065, 0.666, 0.014 and 0.198, a ratio of 24 to 213. The gate's factor is a floor with five times that headroom. Source: `tests/tier2/test_stabilised_mode.py`.
- **[tested]** The velocity error of `supg` (2.7617 × 10⁻⁴) is 0.2 % from `none`'s (2.7567 × 10⁻⁴), so the flow pair owns any velocity error an order above both: `reference` measures 3.4483 × 10⁻², a factor of 125. Source: `tests/tier2/test_stabilised_mode.py`.
- **[tested]** On the coarse pore (313 elements, `max Pe_K` = 4.71), `none` reaches Na⁺ = −72.9 at `(r, z)` = (1.001, −4.376) nm and the NUM-17 gate stops it; `reference` converges in 126 Newton iterations over ten classical rungs, with the crosswind active at 125 of 1344 fluid samples for Na⁺ and 123 for Cl⁻ (peak `ν_K` 3.71 and 5.61). The fine pore (1491 elements, `max Pe_K` = 0.457) has no crosswind anywhere. Source: `tests/tier2/test_stabilised_mode.py`.
- **[verified]** The surface charge of `−0.05 C/m²` is a benchmark choice. Below about `−0.10 C/m²` on that mesh both modes converge and the comparison measures nothing. Source: `tests/tier2/test_stabilised_mode.py`.
- **[verified]** The climbs refine `wall_h` and not `maxh`, because the stabilisation is a double-layer effect by three orders of magnitude (`.knowledge/06` §4.2); the reservoir spacing is held at 5 nm. Source: `tests/tier2/test_stabilised_mode.py`.
- **[tested]** The `reference`-minus-`none` current difference at 0.5 M, +50 mV and `−0.05 C/m²`, `maxh` 5 nm, falls with rates 1.44 and 1.89; the assertions are on the falling ratio and the measured rate, since the plan predicts the exponent and not the constant. Source: `tests/tier2/test_stabilised_mode.py` (`test_ver42_the_two_modes_currents_converge_to_each_other_under_refinement`).
- **[tested]** An equal-order P1/P1 pair in `reference`, against Taylor-Hood on 708 elements at `wall_h` 0.4 nm, 0.5 M, +50 mV: 6.86 × 10⁻² relative `r`-weighted L² velocity difference, 34 Newton iterations either way. Recorded, not gated. Source: `tests/tier2/test_stabilised_mode.py` (`test_ver42_the_equal_order_pair_is_recorded_and_not_gated`).
- **[verified]** On the MMS mesh `max Pe_K` ≤ 0.084, so the crosswind viscosity is identically zero and `supg` and `reference` differ by the flow pair alone; the first interval of the mode-to-mode convergence is pre-asymptotic, so the gate's finest-rate floor is 1.5, not the asymptotic 2. Source: `tests/tier2/test_stabilised_mode.py`.
- **[verified]** Gouy-Chapman-Stern: an ion-free layer of thickness `λ_S` carries no space charge, so `φ` is linear across it and `φ₀ = φ_d + σ_s λ_S/(ε₀ε_r)`, `σ_s = (8εRTc₀)^(1/2) sinh(ζ̃_d/2)`. At 0.1 M, `ζ̃_d` = 2, 298.15 K, `ε_r` = 78.15 and `λ_S` = 0.25 nm: `σ_s` = 0.0435342 C m⁻², `Δφ_S` = 15.7287 mV, and the wall potential rises from 51.3852 to 67.1139 mV, 30.6 %. A shell that is silently fluid is wrong by 24 %. Source: `tests/tier2/test_stern_layer.py`.
- **[tested]** The Stern profile is linear to the nonlinear solve's own tolerance (measured 2.5 × 10⁻⁶); a shell holding ions would curve by percent. The shell agreement is 2.8 × 10⁻⁵ at `λ/4`, 7.2 × 10⁻⁷ at `λ/8` and 1.2 × 10⁻⁹ at `λ/16`. Source: `tests/tier2/test_stern_layer.py`.
- **[verified]** The Stokes far field imposed on `R` = 10 `a` is the exact solution, `u_r = −(3aU/4) z r/R³ + (3a³U/4) z r/R⁵`, `u_z = U − (3aU/4)(1/R + z²/R³) − (a³U/4)(1/R³ − 3z²/R⁵)`. A uniform stream there adds a wall correction of about `a/R`, measured as 28.5 % on this domain and near 22 % in the negative control, against the `1 + (9/4)(a/b)` of a concentric container. Source: `tests/tier2/test_stokes_drag.py`.
- **[tested]** The domain route's error on the finest Stokes mesh is 2.0 × 10⁻⁵, so the 1 % gate has three orders of headroom. The classical model is required because `6πηaU` assumes constant viscosity. Source: `tests/tier2/test_stokes_drag.py`.
- **[verified]** Sanity anchor: a 5 nm sphere at 0.1 m/s drags at about 4 pN. The test's `Ũ = 0.05` in `u₀ = εV_T²/(ηL₀)`, which is 0.0592 m/s on a 1 nm sphere, gives 0.43 pN. Source: `tests/tier2/test_stokes_drag.py`.
- **[tested]** The smallest admissible mesh with wall corrections has 392 elements: `wall_h` 0.4 nm gives a negative minimum distance and is refused, and 0.35 nm gives `min d` = +9.5 × 10⁻⁶ nm. Source: `tests/tier2/test_sweep.py`.
- **[verified]** Warm against cold Newton solves of one fixed point differ by the residual each left, which `numerics.nonlinear.rtol` (NUM-16) bounds; the test compares every reported scalar, not only the current. Source: `tests/tier2/test_sweep.py` (`test_ver37_a_warm_start_does_not_move_the_answer`).
- **[tested]** Warm 34.3 s against cold 26.7 s when measured alongside the rest of the suite; on an idle machine the same code gave 10.0 s against 21.6 s. The warm test therefore asserts Newton iterations, which are a property of the solves. Source: `tests/tier2/test_sweep.py` (`test_ver37_the_warm_path_costs_strictly_fewer_newton_iterations`).
- **[verified]** A `canonical` manifest encodes each float as `{"__f__": <hex>}` for an exact digest, so a decoder is required beside it (§5.3.2) and a comparison against a recorded number has to use it. Source: `tests/tier2/test_sweep.py`.
- **[verified]** The cold pass runs members in reverse index order into an empty store, so no parent has been solved when its child looks for it: the state of a job-array member on a machine that has seen nothing else (FR-24). Source: `tests/tier2/test_sweep.py` (`swept`).
- **[verified]** A zero-bias member makes the route check inapplicable: `I_ψ` = 2.3 × 10⁻²⁷ A against `I_reaction` = 4.6 × 10⁻²⁵ A is a relative difference of 0.995 and aborts the member. Source: `tests/tier2/test_sweep_throughput.py`.
- **[verified]** The throughput measurement uses 25 points in seven waves of widths 1, 3, 5, 5, 5, 4 and 2, over two axes; the one-worker point runs in-process so that `efficiency(1)` does not pay `spawn`. The development machine reports four cores, so N = 4 is the whole machine. Source: `tests/tier2/test_sweep_throughput.py`.
- **[verified]** A sweep over a generated mesh keys its parent from the stored stage-6 artefact. Until that was fixed, the member runner keyed the parent from the bare case, raised for every such sweep, and fell back to cold starts silently, so every member climbed the full ladder. Source: `tests/tier2/test_sweep_generated_mesh.py`.
- **[tested]** VAL-05's predicted values from the plan's prototype are `ε_G` = −8.08 %, `Δr_c` = −0.0205 nm and rms 0.158 nm; the isolevel steps are 2.0 to 5.3 percentage points against a conditioning rms of 0.01 nm. Source: `tests/tier2/test_val05_2wcd.py`.
- **[verified]** The frozen-case conductance on the generated mesh is recorded beside `ε_G` as a bulk-resistor proxy: access resistance dilutes the difference. Source: `tests/tier2/test_val05_2wcd.py` (`test_val05_2wcd_frozen_case_conductance`).
- **[verified]** APBS's error is bounded by `|φ(h) − φ(2h)|` only at first order or better; the focused check is a 193³ grid at 0.05 nm whose faces come from APBS's own 0.1 nm solution, and the ratio `(φ(0.1) − φ(0.2))/(φ(0.05) − φ(0.1))` is `2^p`. Source: `tests/tier2/test_val06_2wcd.py` (`test_val06_2wcd_a_focused_grid_confirms_apbs_converges_at_first_order_or_better`).
- **[tested]** The 0.2 nm APBS run tracks the 0.1 nm run within the budget; a cubic Ångström slip at its coarse grid would move it by a factor of 8. Source: `tests/tier2/test_val06_2wcd.py`.
- **[verified]** At `h` = 0.1 nm = 1 Å, `e` per node and `e` per cubic Ångström are the same number, so the charge-density row of the ring's construction table is invisible on the fine grid and runs on the nested 0.2 nm grid, where the factor is 8. Source: `tests/tier2/test_val06_ring.py`.
- **[verified]** The Gaussian ring's exterior is the point ring to `erfc` of the gap over `w`, about 10⁻³⁵ here. The series in `ρ` is `(b/a)^l` = 0.56^l inside, so 80 terms converge; the APBS box is 6.4 nm at 0.1 nm, which holds the ring 1.8 nm inside every face. Source: `tests/tier2/test_val06_ring.py`.
- **[verified]** Ring coefficients per `l`: with `β'ₗ = k pₗ (b/a)^l/(ε₁a)` and `γ = (a/R)^(2l+1)`, grounding gives `B' = −γC'`, continuity `A' = (1 − γ)C' − β'`, and `C' = ε₁(2l+1)β'/(ε₁l(1 − γ) + ε₂(l(1 + γ) + 1))`. As `R → ∞`, `C_l` tends to Kirkwood's `k pₗ bˡ(2l+1)/(ε₁l + ε₂(l+1))`. Source: `tests/tier2/test_val06_ring.py`.
- **[verified]** The VER-58 oracle, one smeared atom in a uniform dielectric inside a grounded sphere of radius `R`: a unit smeared charge at `(r_i, z_i)` has `φ = (q/4πε)⟨erf(d/w)/d⟩_θ − (qR/a)/(4πε)⟨1/d′⟩_θ`, with `a = (r_i² + z_i²)^(1/2)`, the image of each ring point a charge `−qR/a` at `R²/a` along the same ray, and the azimuthal mean taken by the periodic trapezoid rule, spectrally accurate for these smooth periodic integrands. Source: `tests/tier2/ver58_sphere.py`.
- **[tested]** VER-58's on-axis lattice spacing `H` = 0.0025 nm is the one at which the disc-error rate reaches 2.99 (deposit and solve); at 0.005 nm the floor holds the rate to 2.80. Source: `tests/tier2/ver58_sphere.py`.
- **[verified]** The folding procedure for the number-stability golden (`tests/tier2/data/merge_number_stability.py`): a walk run with `NANOPNP_RECORD_STABILITY=<dir>` writes `<dir>/<walk>.json`, folded by `uv run tests/tier2/data/merge_number_stability.py <dir>`, with `--entry` for a record a CI leg printed. Folding widens that walk's mesh-moved tolerance for every unseen mesh and is refused past the ceiling; a known mesh's values change only with `--replace`, which a G10 re-pin uses in the commit that rules the change (section 8.2.7 G10).

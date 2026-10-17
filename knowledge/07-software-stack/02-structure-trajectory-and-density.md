---
type: Library Behaviour
title: 2. Structure, trajectory and density
description: The structure, trajectory and density libraries and how they behave.
tags:
- software
- library-behaviour
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
verified:
- by: process:tests/tier1/test_reduction.py::test_ver50_off_axis_gaussian_closed_forms
  at: '2026-10-16T00:00:00Z'
---

## 2. Structure, trajectory and density

| Tool | Version | Licence | Notes |
|---|---|---|---|
| **MDAnalysis** | 2.10.0 | LGPLv3+ | PDB, DCD/XTC/TRR/NCDF; `analysis.align.AlignTraj`, `rotation_matrix` **[tested: pending]**. **Not mmCIF**; see below |
| **gemmi** | 0.7.5 | MPL-2.0 | mmCIF (and PDB) reader; wheels cp311–cp314 on manylinux, musllinux, macOS and win_amd64 **[tested: pending]**, 25 Sep 2026 |
| MDTraj | 1.11.1 | LGPLv2.1+ | Faster I/O, leaner; no density-on-grid |
| **GridDataFormats** | 1.2.0 | LGPL | OpenDX/CCP4 I/O; `Density` subclasses `gridData.core.Grid` |
| mdahole2 (MDAKit) | current | GPL-ish + HOLE binary academic licence | Pore-radius profile — use to *validate* the contour |
| PDBFixer / Modeller | — | MIT / academic | Fill missing loops **before** anything else |

**`DensityAnalysis` is histogram-only** (`np.histogramdd`), no kernel option **[tested: pending]**. The
paper's per-atom VdW-weighted Gaussian must be written by hand. Do **not** substitute "histogram
then `gaussian_filter`" — uniform post-smoothing rounds the constriction, whereas VdW-weighted
smearing preserves the exclusion surface.

**gridData 1.2.0, as it actually behaves [tested: pending].** Three things a reader of the docs would not
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
  `nanopnp.density.grid` refuses a non-uniform axis at 1e-9 nm. **[tested: pending]**
- **The reader is guessed from the extension, and `.map` has none.** `Grid("x.map")` raises
  `ValueError: File format MAP not available, choose one of dict_keys(['CCP4', 'MRC', 'DX', …])`,
  although the writer, told `file_format="MRC"`, wrote that file without complaint. Pass the
  reader's `file_format` explicitly, from the same suffix table as the writer. `DensityMap.read`
  exported `.map` and failed to read it back until WP25 did so **[tested: pending]**, 29 September 2026.
- **It carries no length unit.** `origin` and `delta` are written as given. CCP4/MRC defines its
  cell in ångströms, and molecular viewers read OpenDX in ångströms too, so a map written in nm
  overlays its structure at a tenth of its size. The 3D density map is therefore exported in Å and
  converted back on reading (the author's ruling, `SPECIFICATION.md` §8.2.2 B10). On the prepared
  2WCD, an overlay oracle that reads the exported MRC header raw and looks up each heavy atom's
  nearest node rejects all three errors a converter can make: read as nm, every atom falls outside
  the box; with the axes fully transposed, 89 % of atoms read below the single-frame bound; with x
  and y alone swapped, 57 % do **[tested: pending]**, WP25, 29 September 2026.

**GridDataFormats before 1.2 has no MRC writer [tested: pending].**
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

**The 3.11 floor makes this moot [tested: pending].** With `requires-python = ">=3.11"` and
`GridDataFormats>=1.2`, every supported interpreter resolves to 1.2.0 and writes MRC, so the code has
no writer-availability branch (§8.2.2 B4). The facts above describe 1.0.2, should an older
environment turn up.

**Symmetry-axis detection:** do not use raw principal axes. Use **chain-permutation
superposition**: superpose chain A onto chain B, and the rotation's eigenvector with eigenvalue 1
*is* the Cₙ axis. It is about 40 lines and markedly more stable.

**Why principal axes fail on ClyA: they drift, but not from degeneracy [tested: pending].** Measured on
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

**MDAnalysis 2.10 reads no mmCIF [tested: pending].** `mda._PARSERS` and `mda._READERS` in 2.10.0 have no
`CIF`, `MMCIF` or `PDBX` entry, and `MDAnalysis.topology.PDBxParser` does not import. Only the
retired `MMTF` format is there. IF-04's mmCIF leg goes through gemmi (§2.6, WP18).

**What the readers do with a blank or odd field [tested: pending].** Measured 25 September 2026 on MDAnalysis
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

**What each trajectory format gives back [tested: pending].** Coordinates written in float32 ångströms from a
`MemoryReader` universe and read again: DCD and NetCDF store ångströms and return the written bytes
exactly. TRR stores float32 nanometres, so the ångström-to-nanometre conversion costs up to two
float32 ulps, 1.1e-6 nm measured at 13 nm. XTC is quantised to 0.001 nm and returns within
5.02e-4 nm, which is half the quantum plus the same float32 round-off.

**The permutation axis on synthetic assemblies [tested: pending].** Measured with `nanopnp.structure.axis`
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

**MDAnalysis trajectory readers and their time metadata [tested: pending].** Each writer (DCD, XTC, TRR,
NCDF) round-trips three frames written from a static `Universe`. NCDF needs no `netCDF4`, because
the scipy fallback suffices. The times are the trap:

- A DCD written without a timestep reads **1.0 ps per frame**, while XTC, TRR and NCDF read
  **0 ps**.
- The author's `prod5_clya_as.dcd` reads 1.0 ps per frame, a 0.097 ns span for what is about 10 ns
  of production.
- A "last *n* ns" selection trusted to that metadata silently takes the whole trajectory, or the
  wrong window. Gate a `last_ns` longer than the recorded span, and record the times as read
  (`SPECIFICATION.md` §5.3.1 NOTE on `structure:`).

**Density deposition and the (r, z) reduction, measured [tested: pending].** Measured on 25 September 2026
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
- **The Cₙ average is a projection [tested: tests/tier1/test_reduction.py::test_ver50_off_axis_gaussian_closed_forms].** In the angular harmonic basis, averaging n rotated
  copies multiplies `c_m` by `[n | m]`. It therefore leaves the azimuthal mean unchanged and needs
  no rotated map. Against the closed form `2E²Σ I_{kn}(β)²` for a C12 ring of Gaussians, the peak
  variance came out −0.3 to −0.7 % by harmonic projection, −1.4 to −2.4 % from exactly rotated
  copies binned, and −3.3 to −6.1 % from `scipy.ndimage.map_coordinates(order=1)` rotation. The
  bilinear route is biased low, and its k = 0, 3, 6 and 9 copies are exact while the other eight are
  smoothed.
- **`cos(mθ)` modulations** with a smooth radial envelope give both variances within 1.5e-3 of
  `b²/2` (relative to the peak) at r ≥ 1 nm when n | m. When n ∤ m, the Cₙ variance stays below
  7.1e-5 of it.

**Stages 2 and 3 as implemented [tested: pending].** Measured on 25 September 2026 with
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
  stencil's z offsets ascend) leaves the map bit-identical. **[tested: pending]** (`nanopnp.density.union`,
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


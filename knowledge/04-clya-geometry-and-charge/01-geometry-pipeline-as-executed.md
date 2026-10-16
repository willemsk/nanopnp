---
type: Pipeline
title: 1. Geometry pipeline, as executed
description: The geometry pipeline as executed, with measurements on the MD archive,
  the contour script and 2WCD.
tags:
- clya
- pipeline
sources:
- id: thesis
  resource: https://github.com/willemsk/phdthesis-text
  title: Willems, PhD thesis (LaTeX source)
- id: paper
  resource: https://doi.org/10.1039/D0NR03114C
  title: Willems et al., Nanoscale 12, 16775-16795 (2020)
- id: wp18-plan
  resource: docs/plans/wp18-structure-stage.md
  title: WP18 structure stage plan, Design §4 archive record
- id: wp20-plan
  resource: docs/plans/wp20-contour-and-probe.md
  title: WP20 contour and probe plan, Design §1 pqr2grid audit
- id: wp22-plan
  resource: docs/plans/wp22-val05-reference-geometry.md
  title: WP22 VAL-05 reference geometry plan, Outcome — item 4
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
verified:
- by: process:arithmetic
  at: '2026-10-14T00:00:00Z'
- by: process:tests/tier1/test_structure_stage.py::test_ver48_frame_selection_and_the_time_gate
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_structure_stage.py::test_ver48_the_deposited_2wcd_has_no_pair_near_the_wrap_bound
  at: '2026-10-14T00:00:00Z'
---

## 1. Geometry pipeline, as executed

| Stage | Detail | Source |
|---|---|---|
| Start structure | Dodecameric *E. coli* ClyA crystal **2WCD**; missing N-term res. 1-7 and C-term 293-303; **Glu7 added back manually** (N-term sits at the trans entry and matters electrostatically); C-term left missing | E L301-308 |
| Variant | ClyA-AS built with `psfgen` by 27 point mutations: Q8K, N15S, Q38K, A57E, T67V, C87A, A90V, A95S, L99Q, E103G, K118R, L119I, I124V, T125K, V136T, F166Y, K172R, V185I, K212N, K214R, S217T, T224S, N227A, T244A, E276G, C285S, K290Q | E L312-315 |
| Membrane | 200 x 200 Angstrom **DPhPC** patch, CHARMM-GUI membrane builder; lipids with headgroups inside the lumen/protein core deleted; 100 ps steered-MD push-out using ClyA mass density as a virtual repulsive force | E L315-319 |
| Solvation / ions | **213364 TIP3P** waters (VMD `solvate`); neutralised to 0.15 M with **674 Na+ and 602 Cl-** (VMD `autoionize`) | E L320-322 |
| Pre-equilibration | **NAMD**, **CHARMM36** (Best 2012), **NPT**, Langevin thermostat + Nose-Hoover Langevin barostat, **5 ns at 298.15 K**, C-alpha harmonic restraint k = 1 kcal/mol/A^2 | E L322-325 |
| Production | **30 ns NVT at 298.15 K**, explicit solvent, coordinates every **5 ps**, C-alpha harmonically restrained to their *crystal* positions with **k = 695 pN/nm** | T `sec:transport:pore_geometry` L270-277 |
| Frame set | **50 coordinate sets from the final 5 ns**, aligned by backbone-RMSD minimisation (VMD `RMSD tool`) | T L279-282 |

`k = 1 kcal/mol/A^2 = 694.8 pN/nm`, so the two restraint numbers are the same constant expressed
twice. Verified arithmetic, not stated in the thesis.

**Molecular density map** (T L373-397, eq. `eq:denspore`):

```
rho_mol(x,y,z) = 1 - PROD_i [ 1 - exp( -d_i^2 / (sigma * R_i)^2 ) ]
d_i = sqrt((x-x_i)^2 + (y-y_i)^2 + (z-z_i)^2)
sigma = 0.93        R_i = Van der Waals radius of atom i
```

**Which radii.** The thesis says only "Van der Waals radius". The author ruled on 25 September 2026 that R_i is the CHARMM Rmin/2 of PDB2PQR's `CHARMM.DAT`, the set carried by the reference ensemble's per-frame PQR files (§1.1). For an isolated atom `ρ = g`, so the 25 % isolevel sits at `d = σR√ln 4 = 0.93 × 1.1774 R = 1.095 R`, just outside the van der Waals radius itself. The contour therefore moves one-for-one with the radius set **[verified][^thesis]**.

A probabilistic-union ("at least one atom here") field bounded in [0,1], after Li 2013. Grid
**0.5 Angstrom** isotropic, computed in **3D for each of the 50 frames**, then the **50 maps are
averaged in 3D**, and only then **radially averaged about the z-axis** relative to the pore centre
to give `rho_mol(r,z)`. Order matters: average-then-project, not project-then-average.

**Isolevel and manual step.** The pore wall is the **25 % density contour**. The thesis gives *no*
justification, sensitivity study or alternative isolevel for 25 % — it is asserted (T L394-395). The
contour polyline was then edited by hand: "manual removal of overlapping and superfluous vertices to
improve the quality of the final computational mesh" (T L395-396). The resulting outline is stated to
follow a 30-degree wedge of the all-atom structure (T L396-397). The edited vertex list is not
reproduced in the thesis and **the number of boundary vertices is nowhere stated**.

Sanity check on the isolevel (TA `sec:transport_appendix:radius_comparision`): the MD structure does
not deviate materially from 2WCD or the cryo-EM 6MRT; mean lumen diameter is **6.0 nm** (all
corrugations included), whereas the frequently quoted **5.5 nm** is the largest protein that fits
without touching the wall.

### 1.1 The author's MD archive, measured [verified][^wp18-plan] {#11-the-authors-md-archive-measured}

Measured on 25 September 2026. The archive is held locally by the author at
`~/repos/will2018-data/md_data/`. It is not vendored; Tier 3 reads it through
`NANOPNP_REFERENCE_DATA`.

| Item | Measured |
|---|---|
| `prod5_clya_as.pdb` | 54,075 atoms, all protein and hydrogens included: no lipids, waters or ions. Chains A–L, with the chain identifier equal to the segment identifier. Residues 7–292, 286 Cα per chain, histidines as `HSE`. Elements present in the file. Written by MDAnalysis |
| `prod5_clya_as.dcd` | **98 frames. The time metadata reads 1.0 ps per frame**, a 0.097 ns span, which is the default of a DCD written without a timestep. **The true spacing is 100 ps**, and the frames are PQRs 02–99 of the archive below, in order. The paper's 50 frames are DCD frames 48–97 (G1, closed) |
| `prod5_trajectory_last_10ns.7z` | **99 PQR files**, `prod5_protein_aligned_100ps_NN.pdb.pqr` with NN = 01–99, written by PDB2PQR 2.1.1 with `--with-ph=7.5 --ph-calc-method=propka --ff=charmm --ffout=charmm --chain`. Each holds 54,075 atoms, 27,134 of them hydrogens. The author confirmed on 25 September 2026 that these are all the PQR files, taken from the full-atom MD trajectory. **The frames are 100 ps apart**, and the DCD was built from them. Matched by coordinates, **DCD frames 0–97 are PQRs 02–99 in time order**, to 3.8e-6 Å, and PQR 01 is not in the DCD. `notebooks/clya_md_trajectory_analysis.ipynb` built the pair with `mda.Universe(*glob(...), dt=100)`, and its first file served as the topology only. The PDB's coordinates are PQR 02's. So the paper's "50 coordinate sets from the final 5 ns" at 100 ps are **PQRs 50–99, which are DCD frames 48–97**. That is inferred from the thesis's own wording, the spacing and the order both being measured. **The radii are CHARMM Rmin/2.** Frame 01 holds 318 distinct (residue, atom) pairs. 313 of them carry exactly the radius of PDB2PQR 3.7.1's `dat/CHARMM.DAT`, and the other five (`GLU HT1–HT3`, `HSE OT1–OT2`) are that file's `NTER` and `CTER` patch entries. By element the radii span C 1.80–2.275, N 1.85, O 1.70–1.77, S 2.00 and H 0.2245–1.468 Å. The author ruled on 25 September 2026 that these are the density map's van der Waals radii, and that the map was built from the full-atom trajectory, hydrogens included (`SPECIFICATION.md` §5.3.1 NOTE on `geometry.density`) **[verified][^wp18-plan]**, 25 Sep 2026 |
| Also present | `2wcd.pdb` (12 × 285 Cα, residues 8–292, protein only), `6mrt.pdb`, and a `prod5_trajectory_last_10ns.7z`. `radius_comparison/2wcd_h.pdb` is 2WCD **flipped** (+z at the narrow *trans* end) |
| Frame orientation | The Cₙ axis is 0.69° from the file's z in the MD frame, through (0.35, 0.02) Å. It is 0.047° from z in 2WCD and 0.006° in 6MRT. In all three the wide *cis* cap lies at +z |
| The deposited 2WCD | **Not the author's `2wcd.pdb`.** The wwPDB entry's asymmetric unit holds two dodecamers, chains A–L and M–X (53,832 atoms, 24 × 285 Cα), in the crystal frame. The A–L axis is 22.92° from z and the M–X axis 22.98°, nearly parallel. Signed to +z, the axis has its narrow *trans* end up (mean Cα radius 3.42 nm in the top fifth of the axial extent, 4.28 nm in the bottom fifth). Chains A–L superpose on the author's copy with an RMSD of 1.0e-4 nm, and that superposition takes the deposited +z-signed axis to −z. So the author's file is chains A–L moved rigidly and flipped, *cis* up. Stage 1 refuses the deposited frame by its 10° rule. On the author's copy it measures a 29.99896° turn, a worst spacing error of 0.193°, a permutation RMSD of 0.0262 nm, a tilt of 0.047° and an `axis: z` displacement of 0.0062 nm. The Design §4 "2WCD" column of the WP18 plan is this copy **[tested: pending]**, 25 Sep 2026 |
| Consecutive Cα on the deposited 2WCD | Chains A–L, residues without an insertion code, 3,408 pairs of consecutive residue numbers (284 per chain): **0.374 to 0.386 nm**, the largest at chain D, residues 266–267 (0.3856 nm). The PDB and mmCIF copies agree to the last digit. Stage 1's wrap gate refuses a pair over 1.0 nm in any selected frame, so the vendored structure sits at 0.39 of the bound; a wrapped pair would be a box length (about 10 nm) apart **[tested: tests/tier1/test_structure_stage.py::test_ver48_the_deposited_2wcd_has_no_pair_near_the_wrap_bound]**, `tests/tier1/test_structure_stage.py` (`test_ver48_the_deposited_2wcd_has_no_pair_near_the_wrap_bound`), 14 Oct 2026 |
| Stage 1 on the archive | All 98 frames, superposed on frame 0 over every Cα (0.095–0.219 nm RMSD to it), 12 chains × 286 common Cα. On the ensemble-mean structure the cyclic turn is 29.9954°, the worst spacing error 0.679°, the permutation RMSD 0.136 nm and the tilt from the file's z 0.695°. Each frame's own permutation axis lies within 0.0163° of the ensemble-mean axis. This is a different reference from the ≤ 0.010° frame-to-frame figure of §5.2 (stage 1), which compared the frames' axes with one another **[verified][^wp18-plan]**. The DCD's interval reads 0.001 ns, so `last_ns: 5` is refused **[tested: tests/tier1/test_structure_stage.py::test_ver48_frame_selection_and_the_time_gate]**, `tests/tier3/test_structure_ensemble.py`, 25 Sep 2026 |
| Axial placement | The Cα centroid is at z = 56.3 Å (MD; residues 7–292. Over residues 8–292 and DCD frames 48–97 it is 56.553 Å, §1.5) and 57.0 Å (2WCD), which matches G9's "(0, 0, 55 Å)". The MD all-atom extent is z = −2.28 to 12.52 nm, bracketing the model's pore extent of −1.85 to 12.25 nm by 0.43 and 0.27 nm. **Author ruling, 25 September 2026: the MD trajectory was centred on the middle of the bilayer, so in the MD frame `centre_z_nm` = 0** (G9, closed). The author's `2wcd.pdb` copy has its Cα centroid 0.07 nm from the MD one, but the vendored wwPDB 2WCD takes whatever axial position its test-time move gives it, so WP22 must register it to the MD frame |

### 1.2 The author's contour script, read [verified][^wp20-plan] {#12-the-authors-contour-script-read}

Read on 26 September 2026 (`SPECIFICATION.md` OPN-02, closed). The script is
`create_polygon_contour` in the author's `pqr2grid` repository, held locally at
`~/repos/pqr2grid`, MIT. It first appears in commit `a8e2898`, 7 October 2019, and is unchanged in
the 2023 package. The PlyAB and MspA scripts use the same lines. The paper's archive does not call
it for ClyA.

| Step | What the script does | Consequence |
|---|---|---|
| Density | The union of §1, `sigma=0.93`, radii from the PQR, on a Cartesian grid over `[−L, L]` at h | The model of `SPECIFICATION.md` §5.2 stage 2 |
| Radial average | `np.histogram` of the node radii, at bin width `w = (x_max − x_min + 1)/N_x` | `w/h = (2L + 1)/(2L + h)`, not 1: the `+1` is in nm, where one spacing was meant. It is 1.0316 at L = 15 nm and 1.0701 at L = 6.75 nm **[verified]** |
| Contour | `find_contours(D, 0.25)`, then `contours[0]` | The first contour in scan order, not the largest |
| Coordinates | `r = col·h`, `z = row·h + z_min` | Bin j's centre is `(j + ½)w`, so a feature at true radius r is written at `r_a = (r/w − ½)h`. At L = 15, 1.65 nm reads 1.574 nm and 5.66 nm reads 5.462 nm **[verified]** |
| Simplify | `Polygon.simplify(0.1)`, topology preserved | Douglas–Peucker, with no smoothing, no spacing step and no gate |
| Output | A z offset (PlyAB: −0.5 nm), then `savetxt(fmt='%.2f')` | Vertices rounded to 0.01 nm |

**The erratum, measured.** We applied the script's binning and coordinate map to the 2WCD density
from `nanopnp` stage 2 (L = 6.75 nm). The script's 0.25 contour lies 0.13–0.24 nm inside the exact
reduction's at the lumen, and 0.21–0.40 nm inside at the outer surface. The same bins, placed at
their centres `(j + ½)w`, agree with the exact reduction to ≤ 0.01 nm. So the error lies entirely
in the index-to-radius map, not in the binning **[tested: pending]** (WP20 plan, Design §1, 26 Sep 2026).
At L = 15 nm a feature at 1.65 nm reads 1.5744 nm and one at 5.66 nm reads 5.4615 nm **[verified]**
(`validation/geometry.py`, `pqr2grid_radius`).

**Answered by the author, 28 September 2026: it was.** The delivered 185-vertex polygon was made
with `pqr2grid`'s radial binning at **L = 15 nm** (h = 0.05 nm), so `w/h = 31/30.05 = 1.03161` and
`r_a = 0.96935 r − 0.025` nm. **The hand edit then moved vertices**, not only removed them. The
evidence below had argued against the binning. It is kept because it measures the edit: the erratum
moves both surfaces inward, so the edit moved them outward by more than the erratum did (§1.4). Its lumen is on average 0.08–0.14 nm *wider* than the exact contour of
2WCD, of one MD frame, and of the 50-frame ensemble, and its outer surface is up to 0.12 nm
narrower. The erratum would move both surfaces inward (WP20 plan, Design §7).

**The delivered polygon's lattice fingerprint [tested: pending].** Of its 185 vertices, 58 % have at least
one coordinate on the 0.05 nm lattice, and 32 % have both. A subset of marching-squares vertices on
a 0.05 nm grid, written at `%.2f`, would have at least one lattice coordinate on *every* vertex,
and both on about a fifth. So the table is not a vertex subset of such a contour. About four in ten
of its vertices were moved or placed by hand. That is consistent with the Methods' "manual removal
of overlapping and superfluous vertices", and it goes beyond it.

**The 2023 charge map.** The same repository deposits
`q/(π(σR)²)·exp(−((r − r_i)² + (z − z_i)²)/(σR)²)` per atom in (r, z). That is a planar Gaussian
with no `1/(2πr)`, whose planar integral is the net charge: the `e/m²` convention of the delivered
table (G5). It is a pointer for Phase 3's FR-13.

### 1.3 Stage 4 on real and synthetic inputs, measured [tested: pending] {#13-stage-4-on-real-and-synthetic-inputs-measured}

`nanopnp` stage 4 at its defaults (isolevel 0.25, Taubin, `simplify_tol_nm` 0.02, h = 0.05 nm,
closing and opening by 2h), 26 September 2026 (`SPECIFICATION.md` §5.2.1; VER-51).

| | 2WCD, vendored and prepared | ClyA-AS, DCD frames 48–97 | Synthetic C12 tube |
|---|---|---|---|
| Raw contours at 0.25 | 2: the body and a void the closing removes | 1 | 1 |
| Vertices: raw, after the morphology, resampled, final | 962, 2,529, 1,510, 161 | 866, 2,156, 1,386, 114 | 156, 432, 296, 12 |
| Area, raw and final (nm²) | 28.145, 28.109 | 29.541, 29.545 | 2.956, 2.908 |
| Minimum spacing and feature size (nm) | 0.0727, 0.157 | 0.0732, 0.229 | 0.124, 0.239 |
| `r_c − R_p` (nm) | +0.062 to +0.908 | +0.170 to +0.916 | **−0.011** to +0.198 |
| Constriction `r_c` (nm) | 1.630 | 1.611 at z = −1.33 | 2.464 |
| Lumen moved by conditioning: max, rms (nm) | 0.039, 0.010 | 0.101 at z = 1.63, 0.013 | 0.030, 0.010 |
| Stage 4, probe included | 0.28 s | 4.6 s | 0.17 s |

The tube is 12 chains of alanine atoms on three rings (2.7, 3.0, 3.3 nm) and nine layers 0.3 nm
apart. Its inner wall is flat, with every atom of the inner ring touching the probe sphere. That is
the worst case for the radius band's lower bound (the §5.2.1 NOTE): the union of many atoms at one
radius raises the density just inside the sphere. Even so, the contour enters the sphere by only
0.011 nm, a fifth of h. A real lumen is corrugated, and the azimuthal mean pulls its contour
outward, so on 2WCD the margin stays positive. The 2WCD numbers agree with the plan's prototype,
which ran on the author's copy of chains A–L: 157 vertices, a feature size of 0.173 nm and a
margin of +0.061 to +0.908 nm. The ensemble agrees with it too: a feature size of 0.229 nm, a
margin of +0.173 to +0.869 nm and the constriction at 1.610 nm. The largest margin here, 0.916 nm,
sits at z = −1.925 nm, the lowest mid-plane that crosses the loop. The ensemble's z is the MD
frame, whose bilayer centre is z = 0 (G9) (WP20 plan, Design §6).

Taubin's umbrella operator on a closed loop is circulant: mode `k = 1 - cos θ` is scaled by
`(1 - λk)(1 - μk)` per pass, with λ = 0.5, μ = -0.53, N = 10. The pass band is wavelengths above 13.08
samples (0.33 nm at h/2 spacing), and the grid-scale staircase (k = 1) keeps 0.069 of its amplitude
[verified]. Source: `geometry/contour.py` (`taubin`), WP20 plan Design §3.

The probe-radius profile costs frames x atoms x planes distances, 7.8e8 for the 50-frame ClyA-AS
ensemble, a few seconds, batched per frame and bounded by `CHUNK_ELEMENTS` (32 MB of float64) [tested: pending].
Source: `geometry/probe.py`, WP20 plan Design §5.

### 1.4 2WCD against the reference polygon, and the isolevel lever [tested: pending] {#14-2wcd-against-the-reference-polygon-and-the-isolevel-lever}

> **Registration.** 2WCD sits at `Z_MD` = 5.6553 nm over residues 8–292 (§1.5); the bullets below
> were computed at 5.63 nm, the centroid with residue 7 included, and are a sensitivity reference.
> At 5.655 nm, `centre_z_nm` = 4.5477 nm and, at isolevel
> 0.25, ε_G = −8.49 % (exact −8.54 %), Δr_c = −0.0203 nm (1.6297 nm at z = −1.425), rms 0.159 nm,
> mean Δ −0.136 nm, max |Δ| 0.339 nm at z = 3.425, on 280 planes (−1.825 and −1.775 fall in the
> tip band). The sweep is −12.95, −10.86, −8.49, −6.07, −3.50, −0.87 and +4.41 %, crossing zero
> at 0.416. The frozen case at `size_scale` 2 gives −6.59 % (14,116 triangles). The default-size
> mesh is 44,987 triangles, minimum SICN 0.6956 (mean 0.9862), minimum gamma 0.6223 (mean
> 0.9843). The rms-optimal offset, 4.5827 nm, now lies 0.035 nm from the registration. It is a
> diagnostic and is never used **[tested: pending]**, `tests/tier2/test_val05_2wcd.py`, 30 Sep 2026.

Measured on 28 September 2026 by the WP22 plan's prototype (Design §4), and again by the
implementation, `nanopnp.validation.geometry` through `tests/tier2/test_val05_2wcd.py`, the same
day; the two agree to the last printed digit except where noted. The prepared vendored 2WCD
(chains A–L) ran through stages 1–5 at the defaults. Stage 5's model-frame polygon was compared with
the delivered table on the 282 mid-planes `z = −1.85 + (k + ½)0.05` nm, lumen radius taken as the
innermost crossing. `ε_G = 2Σ(Δ/r)r⁻²/Σr⁻²` is the first-order relative conductance change of a bulk
series resistor. It is the `G ∝ r²` sensitivity weighted by where the resistance sits
(`SPECIFICATION.md` §7.4 NOTE on VAL-05).

- **Registration.** The Cα centroid of residues 8–292 lies at z = 10.2027 nm in the stage-1 frame.
  Placing it at the MD structure's 5.63 nm (§1.1) gives `centre_z_nm` = 4.5727 nm. The offset that
  minimises the rms lumen deviation is 4.5827 nm on a 0.005 nm grid about the centroid's, and
  4.580 nm on the prototype's grid from 4.2 nm: the minimum lies between, 0.007–0.010 nm from the
  centroid's. The *trans* tip + 1.85 nm of WP21 gives 4.6289 nm.
- **At isolevel 0.25:** ε_G = −8.08 % (exact series −8.19 %), lumen mean Δ −0.132 nm, rms 0.158,
  max |Δ| 0.333 nm at z = 3.375, and r_c = 1.6295 nm at z = −1.475 against the table's 1.650 nm at
  z = −1.225, so Δr_c = −0.0205 nm. The constriction window's mean Δ is −0.051 nm and the *cis*
  lumen's −0.158 nm. The outer surface's mean Δ is −0.023 nm, rms 0.154. The polygon misses one
  plane, z = −1.825, inside the 0.1 nm tip band. The largest single term of ε_G is −0.15 pp, at
  z = −0.625. Conditioning moved the lumen by at most 0.039 nm, rms 0.010 nm (stage 4's
  `lumen_change`).
- **The isolevel lever (G2).** ε_G is −13.23, −10.08, −8.08, −5.81, −3.26, −0.40 and +4.87 % at
  0.15, 0.20, 0.25, 0.30, 0.35, 0.40 and 0.50, strictly increasing, and crosses zero at 0.408. ±0.1
  of isolevel is about ±5 % of G. That is the size of the source's unjustified choice. **The body
  shortens at both tips as the level rises**: at 0.40 it misses four planes, all in the tip band,
  and at 0.50 it spans z = −1.684 to 11.907 nm and misses ten, so that level is compared on the 272
  planes both cross. Stage 4 passes at every level.
- **The erratum at L = 15 nm, applied to our contour:** ε_G = −16.01 %, lumen mean Δ −0.242 nm
  (constriction window −0.139, *cis* lumen −0.275), outer surface −0.191 nm. The erratum alone moves
  our lumen by −0.110 nm and our outer surface by −0.169 nm on average. With 2WCD standing in for the
  ensemble, the hand edit therefore widened the lumen by about 0.24 nm and moved the outer surface
  out by about 0.19 nm. G3's ±1 % floor cannot be reached by any reproduction of the method, because
  the reference is the method plus two opposite several-per-cent steps outside it.
- **The conductance proxy against a solve.** One frozen case, uncharged `pnp`, flow off, every
  correction `none`, 1 M NaCl, +50 mV, stabilisation `none`, at `size_scale` 2: 1.3786e-8 S on the
  generated mesh (14,162 triangles) and 1.4756e-8 S on the fixture through `inputs.profile`
  (14,511), so `G_gen/G_ref − 1` = −6.57 % against ε_G's −8.08 % and the exact series −8.19 %. Access
  resistance and the electrolyte past the pore ends carry about a fifth of the resistance, and dilute
  the bulk-resistor figure by that much.
- **The mesh at the default sizes** (0.05 nm at the wall): 44,762 triangles, minimum SICN 0.6267,
  mean 0.9862, minimum gamma 0.5222, mean 0.9843, re-measured on 29 September 2026 at `2bb1a34`
  and on the WP23 branch alike. The 44,998 triangles (means 0.9867 and 0.9848) recorded when WP22
  delivered predate `32fecf1`, which changed how the C-alpha centroid is computed and so the
  registration. The minima did not move. The cause of the count's move was not isolated further. On
  the Gmsh backend the same region meshes to 49,617 triangles, minimum SICN 0.6805 and gamma 0.5749
  (WP23 D13). The reference COMSOL mesh has 120,917 elements,
  minimum quality 0.6378 and mean 0.9765 by a measure its report does not state
  (`knowledge/09-comsol-reference-settings/index.md`). WP21's 44,688 triangles and 0.7111 were at its *trans*-tip
  registration, which places the bilayer 0.056 nm higher.
- **The Cₙ variance (FR-06)**, from stage 3 in the stage-1 frame: the largest Cₙ variance is 0.204 at
  (r, z) = (5.40, 12.95) nm, the *cis* rim, and the largest non-Cₙ variance 0.0095 at (1.65, 3.10) nm,
  which is the *trans* constriction's lumen wall.

### 1.5 The ensemble against the reference polygon [verified][^wp22-plan] {#15-the-ensemble-against-the-reference-polygon}

Run by the author on 30 September 2026, `tests/tier3/test_val05_ensemble.py` on
`$NANOPNP_REFERENCE_DATA`: DCD frames 48–97, stages 1–5 at the defaults, `centre_z_nm` = 0 in the
MD frame (G9). It uses the same planes and metric as §1.4.

- **`Z_MD`.** The Cα centroid of residues 8–292 over the 50 frames is **5.6553 nm**, and 5.6293 nm
  with residue 7. §1.1's 56.3 Å is therefore the residue-7-inclusive figure, and residue 7 pulls
  the centroid 0.026 nm towards *trans*, as WP22 Design §3 estimated.
- **At isolevel 0.25:** ε_G = **−5.56 %** (exact series −5.57 %), Δr_c = **−0.039 nm**
  (1.6112 nm at z = −1.325 against 1.650 at −1.225), rms **0.089 nm**, mean Δ −0.075 nm, max |Δ|
  0.295 nm at z = 1.725. All 282 planes are crossed. The constriction window's mean Δ is −0.073 nm
  and the *cis* lumen's −0.076 nm. The outer surface's mean is +0.167 nm and its rms 0.337 nm.
  The tips are at −1.944 and 12.277 nm. The largest ε_G term is −0.096 pp, at z = −1.375.
  Conditioning moved the lumen by at most 0.101 nm (z = 1.625), rms 0.013 nm.
- **The isolevel lever.** ε_G is −12.98, −8.92, −5.56, −2.12, +1.02, +3.93 and +9.80 % at 0.15,
  0.20, 0.25, 0.30, 0.35, 0.40 and 0.50, strictly increasing. It crosses zero at 0.334 (2WCD:
  0.416). **±0.1 of isolevel is −7.4 and +6.6 pp here**, against about ±5 pp on 2WCD. r_c is
  1.510, 1.578, 1.611, 1.646, 1.684, 1.718 and 1.758 nm. From 0.40 up, the minimum moves from the
  constriction's *trans* end to z = −0.325 nm.
- **The erratum at L = 15 nm, applied to our contour:** ε_G = −13.57 % (exact −13.20 %), lumen
  mean Δ −0.187 nm, r_c 1.537 nm. The erratum moves our lumen by −0.111 nm and our outer surface by
  −0.174 nm. **The hand edit therefore widened the lumen by 0.187 nm** and left the outer surface
  where it was (+0.008 nm). 2WCD's stand-in estimate, 0.24 nm, was high by 0.05 nm.
- **The conductance proxy against a solve.** For the §1.4 frozen case at `size_scale` 1, the
  generated mesh gives 1.4103e-8 S (45,272 triangles) and the fixture 1.4753e-8 S (44,316), so
  `G_gen/G_ref − 1` = **−4.40 %**, against ε_G −5.56 %.
- **The mesh at the default sizes.** Netgen gives 45,272 triangles, minimum SICN 0.7087 (mean
  0.9866), minimum gamma 0.6763 (mean 0.9847), with 555 wall segments at 1.053 × the target on
  average and 1.464 at most. Gmsh 4.15.2 gives 49,100, 0.7317 (0.9886) and 0.6441 (0.9867), with
  613 wall segments at 0.953 × on average and 1.043 at most.
- **The C12 variance (FR-06).** The largest Cₙ variance is 0.171 at (r, z) = (4.70, 6.55) nm. The
  largest non-Cₙ variance is **0.088 at (2.00, −1.70) nm**, the *trans* entrance of the
  constriction, nine times 2WCD's 0.0095. The raw variance peaks at 0.186 at (4.60, 0.65) nm.
- **Timing, on the author's machine.** Stage 1 took 9.2 s. Stage 2 took 596.6 s, 11.9 s a frame on
  a 339 × 293 × 293 grid at 0.05 nm. Stages 3 to 5 took 13.7, 3.3 and 1.5 s. Stage 6 took 12.3 s
  cold and 4.9 s warm, and Gmsh 2.2 s. The whole file ran in 12 min 54 s. `knowledge/07-software-stack/index.md`
  §2 has the development container's 980.6 s for stage 2.

---

[^thesis]: Willems, PhD thesis (LaTeX source).
[^wp18-plan]: `docs/plans/wp18-structure-stage.md`, Design §4 and Outcomes (25 September 2026).
[^wp20-plan]: `docs/plans/wp20-contour-and-probe.md`, Design §1 (`pqr2grid` `create_polygon_contour`, commit `a8e2898`).
[^wp22-plan]: `docs/plans/wp22-val05-reference-geometry.md`, Outcome — item 4 (30 September 2026).

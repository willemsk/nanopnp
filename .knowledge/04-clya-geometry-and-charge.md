# ClyA-AS — geometry, fixed charge, and validation targets

**Status:** authoritative for the *reference case*. Transcribed from the thesis ch. 6 and ch. 6 SI
(`chapters/transport/transport.tex`, `chapters/transport_appendix/transport_appendix.tex`) =
Willems et al., *Nanoscale* **12**, 16775 (2020). MD setup details are cross-referenced by ch. 6
into ch. 4 (`chapters/electrostatics/electrostatics.tex`, `sec:elec:methods:molec`) and are
transcribed from there.

**Scope.** This file covers *only* the ClyA-specific pipeline and numbers. Governing equations,
correction functions, their parameters, and the errata belong to `01-physics-epnpns.md` and are not
repeated. Citation keys below: **T** = `transport.tex`, **TA** = `transport_appendix.tex`,
**E** = `electrostatics.tex`; `Lnnn` = line number at time of transcription.

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

**Which radii.** The thesis says only "Van der Waals radius". The author ruled on 25 September 2026 that R_i is the CHARMM Rmin/2 of PDB2PQR's `CHARMM.DAT`, the set carried by the reference ensemble's per-frame PQR files (§1.1). For an isolated atom `ρ = g`, so the 25 % isolevel sits at `d = σR√ln 4 = 0.93 × 1.1774 R = 1.095 R`, just outside the van der Waals radius itself. The contour therefore moves one-for-one with the radius set **[verified]**.

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

### 1.1 The author's MD archive, measured [tested]

Measured on 25 September 2026. The archive is held locally by the author at
`~/repos/will2018-data/md_data/`. It is not vendored; Tier 3 reads it through
`NANOPNP_REFERENCE_DATA`.

| Item | Measured |
|---|---|
| `prod5_clya_as.pdb` | 54,075 atoms, all protein and hydrogens included: no lipids, waters or ions. Chains A–L, with the chain identifier equal to the segment identifier. Residues 7–292, 286 Cα per chain, histidines as `HSE`. Elements present in the file. Written by MDAnalysis |
| `prod5_clya_as.dcd` | **98 frames. The time metadata reads 1.0 ps per frame**, a 0.097 ns span, which is the default of a DCD written without a timestep. **The true spacing is 100 ps**, and the frames are PQRs 02–99 of the archive below, in order. The paper's 50 frames are DCD frames 48–97 (G1, closed) |
| `prod5_trajectory_last_10ns.7z` | **99 PQR files**, `prod5_protein_aligned_100ps_NN.pdb.pqr` with NN = 01–99, written by PDB2PQR 2.1.1 with `--with-ph=7.5 --ph-calc-method=propka --ff=charmm --ffout=charmm --chain`. Each holds 54,075 atoms, 27,134 of them hydrogens. The author confirmed on 25 September 2026 that these are all the PQR files, taken from the full-atom MD trajectory. **The frames are 100 ps apart**, and the DCD was built from them. Matched by coordinates, **DCD frames 0–97 are PQRs 02–99 in time order**, to 3.8e-6 Å, and PQR 01 is not in the DCD. `notebooks/clya_md_trajectory_analysis.ipynb` built the pair with `mda.Universe(*glob(...), dt=100)`, and its first file served as the topology only. The PDB's coordinates are PQR 02's. So the paper's "50 coordinate sets from the final 5 ns" at 100 ps are **PQRs 50–99, which are DCD frames 48–97**. That is inferred from the thesis's own wording, the spacing and the order both being measured. **The radii are CHARMM Rmin/2.** Frame 01 holds 318 distinct (residue, atom) pairs. 313 of them carry exactly the radius of PDB2PQR 3.7.1's `dat/CHARMM.DAT`, and the other five (`GLU HT1–HT3`, `HSE OT1–OT2`) are that file's `NTER` and `CTER` patch entries. By element the radii span C 1.80–2.275, N 1.85, O 1.70–1.77, S 2.00 and H 0.2245–1.468 Å. The author ruled on 25 September 2026 that these are the density map's van der Waals radii, and that the map was built from the full-atom trajectory, hydrogens included (`SPECIFICATION.md` §5.3.1 NOTE on `geometry.density`) **[tested]**, 25 Sep 2026 |
| Also present | `2wcd.pdb` (12 × 285 Cα, residues 8–292, protein only), `6mrt.pdb`, and a `prod5_trajectory_last_10ns.7z`. `radius_comparison/2wcd_h.pdb` is 2WCD **flipped** (+z at the narrow *trans* end) |
| Frame orientation | The Cₙ axis is 0.69° from the file's z in the MD frame, through (0.35, 0.02) Å. It is 0.047° from z in 2WCD and 0.006° in 6MRT. In all three the wide *cis* cap lies at +z |
| The deposited 2WCD | **Not the author's `2wcd.pdb`.** The wwPDB entry's asymmetric unit holds two dodecamers, chains A–L and M–X (53,832 atoms, 24 × 285 Cα), in the crystal frame. The A–L axis is 22.92° from z and the M–X axis 22.98°, nearly parallel. Signed to +z, the axis has its narrow *trans* end up (mean Cα radius 3.42 nm in the top fifth of the axial extent, 4.28 nm in the bottom fifth). Chains A–L superpose on the author's copy with an RMSD of 1.0e-4 nm, and that superposition takes the deposited +z-signed axis to −z. So the author's file is chains A–L moved rigidly and flipped, *cis* up. Stage 1 refuses the deposited frame by its 10° rule. On the author's copy it measures a 29.99896° turn, a worst spacing error of 0.193°, a permutation RMSD of 0.0262 nm, a tilt of 0.047° and an `axis: z` displacement of 0.0062 nm. The Design §4 "2WCD" column of the WP18 plan is this copy **[tested]**, 25 Sep 2026 |
| Stage 1 on the archive | All 98 frames, superposed on frame 0 over every Cα (0.095–0.219 nm RMSD to it), 12 chains × 286 common Cα. On the ensemble-mean structure the cyclic turn is 29.9954°, the worst spacing error 0.679°, the permutation RMSD 0.136 nm and the tilt from the file's z 0.695°. Each frame's own permutation axis lies within 0.0163° of the ensemble-mean axis. This is a different reference from the ≤ 0.010° frame-to-frame figure of §5.2 (stage 1), which compared the frames' axes with one another. The DCD's interval reads 0.001 ns, so `last_ns: 5` is refused **[tested]**, `tests/tier3/test_structure_ensemble.py`, 25 Sep 2026 |
| Axial placement | The Cα centroid is at z = 56.3 Å (MD) and 57.0 Å (2WCD), which matches G9's "(0, 0, 55 Å)". The MD all-atom extent is z = −2.28 to 12.52 nm, bracketing the model's pore extent of −1.85 to 12.25 nm by 0.43 and 0.27 nm. **Author ruling, 25 September 2026: the MD trajectory was centred on the middle of the bilayer, so in the MD frame `centre_z_nm` = 0** (G9, closed). The author's `2wcd.pdb` copy has its Cα centroid 0.07 nm from the MD one, but the vendored wwPDB 2WCD takes whatever axial position its test-time move gives it, so WP22 must register it to the MD frame |

---

## 2. Model geometry and conventions

| Quantity | Value | Source |
|---|---|---|
| Reservoir | one sphere R = **250 nm**, split through the middle by the bilayer into cis and trans hemispheres (2D-axisym: half-disc r in [0,250], z in [-250,250] nm) | T `sec:transport:global_geometry` L240-244 |
| Bilayer | dielectric block, thickness **h = 2.8 nm**, impermeable to ions and water | T L242 |
| Pore axial extent | **-1.85 <= z <= 12.25 nm** (this is the definition of "the pore" for all pore-averaged quantities) | TA `eq:pore_surface_integral` beta definitions |
| Trans constriction | **-1.85 < z < 1.6 nm**, ~3.3 nm diameter (nominal cylinder: 3.3 nm dia x 4 nm high) | T L881-883, L1076 |
| Cis lumen | **1.6 < z < 12.25 nm**, ~6 nm diameter (nominal cylinder: 6 nm dia x 10 nm high) | T L882-883, L136-137 |
| Pore radius field | `r_p(z)`, from the 25 % contour | TA |
| Radial-average radius | `R(z) = r_p(z)` inside the pore; **fixed 4 nm** for z > 12.25 (cis) and **fixed 2 nm** for z < -1.85 (trans) | T `sect:esp` L1097-1099 |
| Charge clusters | constriction: E7, E11, K14, E18, D21, D25. Mid-lumen (4 < z < 6): E53, E57, D64, K147. Cis mouth (10 < z < 12): D114, R118, D121, D122 | T L1075-1078 |

**Bias sign convention** (T `sec:transport:global_geometry` L249-258): **cis is grounded**
(`phi = 0` on the cis reservoir edge), `phi = V_bias` is applied on the **trans** edge.
Consequences that must be reproduced: at **V_bias > 0** cations move **trans -> cis**; at
**V_bias < 0** cations and the EOF move **cis -> trans** (T L1185, L1205, L1367). Experimentally the
pore is added to the grounded cis reservoir (T `sec:transport:methods` L1631-1633). Current is
integrated over the **cis** boundary (eq. `eq:currentsim`).

---

## 3. Fixed-charge pipeline

Protonation and parameters: partial charges and radii from **CHARMM36**, assigned at **pH 7.5** with
**PROPKA** + **PDB2PQR** (printed "PBD2PQR" in the source) — T L421-423.

Same 50 aligned frames as the geometry. Each atom's charge is spread over all azimuthal angles,
`q_i -> q_i / (2 pi r_i)` with `r_i = sqrt(x_i^2 + y_i^2)`, and smeared as a 2D Gaussian in (r,z)
(T L402-416, eq. `eq:scdpore`):

```
rhoq_pore(r,z) = SUM_i  e * q_i / (pi * (sigma * R_i)^2)
                        * exp( -((r - r_i)^2 + (z - z_i)^2) / (sigma * R_i)^2 )
sigma = 0.5   (sharpness factor)      R_i = atom radius
```

`1/(pi w^2)` with `w = sigma*R_i` is the correct 2D normalisation (`integral exp(-(x^2+y^2)/w^2) = pi w^2`),
so the printed expression is a *surface* charge density (C/m^2). Do not confuse `sigma = 0.5` here
with `sigma = 0.93` in the density map.

Discretisation and use: gridded at **0.005 nm** spacing over the domain of `rhoq_pore`, precomputed,
loaded into COMSOL as a **2D linear interpolation function**, and converted to a pseudo-3D volumetric
density by dividing by the **local circumference 2 pi r** of each element, **applied across all
computational domains** (T L418-429). Axis guard, verbatim COMSOL (see `01-physics-epnpns.md` §5):

```
scd_pore = if(r < 0.01[nm], 0, e_const * rhoq_pore(r,z) / (2*pi*r))     [C m^-3]
```

**Net charge check (a regression target):** integrating the resulting volumetric density over the
final mesh gives **-72.9 e**, against **-72 e** for the atomistic model (T L425-427). Any
reimplementation must land within ~1 % of -72 e.

### 3.1 The delivered table, measured [tested]

`prod5_clya_charge` is the interpolation table the published model loads — COMSOL's
`%Grid`/`%Data` text export, 77 MB, coordinates in metres. Measured directly (6 September 2026;
too large to vendor, so it is named by `$NANOPNP_REFERENCE_DATA` and Tier 3 skips without it):

| Property | Value |
|---|---|
| Shape | 1401 x 3401, `values[i_z, i_r]` float64 |
| Spacing | 0.005 nm on both axes, uniform to 1e-15 nm |
| Extent | `r` in [0, 7] nm, `z` in [-3.5, 13.5] nm |
| Value range | -2.81e20 to +6.90e20 (in `e/m^2`; 110.5 C/m^2 after the `e` factor) |
| Planar integral | **-71.999999999663 e**, i.e. exactly -72 e to 4.7e-12 relative |
| Boundary ring / interior max | 8.5e-24 — not truncated, by 20 decades |
| Axis-guard deficit (`r < 0.01 nm`) | 1.4e-68 e — the innermost atoms sit at `r >~ 1.6 nm` |

Two of the section-8 gaps close on these numbers.

**G5 closes: there is no `e` in the file.** The integral is the *integer* -72, not
`-72 x 1.6e-19`. So the stored table is the sum in units of `e/m^2` and the COMSOL assembly's
`e_const` supplies the coulombs — exactly once. Eq. `eq:scdpore` as transcribed in §3 above, with
an `e` inside the sum, is the published expression and not the file; implementing it literally and
then applying `e_const` double-counts by 1.6e-19.

**G10 closes:** the bounding box is `r` in [0, 7], `z` in [-3.5, 13.5] nm, 4.76e6 nodes — the
order the gap predicted. The pore spans `z` in [-1.85, 12.25], so the box clears it by 1.25-1.65 nm
either way, which is the ">= 4 sigma_max beyond the protein" of PHY-16 step 4 (4 x 0.085 = 0.34 nm)
with a wide margin.

### 3.2 The reference's 1.25 % is the *consumer's*, and it is aliasing [tested]

The producer leg is exact (4.7e-12, above), so the published `-72.9 e` against `-72 e` cannot be a
smearing or projection error: it is COMSOL's own integral of its own table over its own mesh.
Reproduced here by the same route — `VoxelCoefficient` bilinear interpolation sampled at quadrature
points — on the WP8 reference mesh, 44,316 elements graded to 0.05 nm at the pore wall:

| Quantity | Value |
|---|---|
| `Q_grid` | -72.000000000 e |
| `Q_mesh` | -71.289538 e |
| Consumer leg `(Q_mesh - Q_grid)/\|Q_grid\|` | **+9.868e-03** |
| Order vs order+3 quadrature agreement | 9.273e-03 |
| Worst ramped plane cumulative | 2.032e-02, at `z = 8.269 nm` |

Ours is -0.99 %, the reference's is +1.25 %: same magnitude, same character, opposite sign. That is
the signature of an aliasing error rather than lost charge. **Neither refinement route converges
it**, which is the finding:

| maxh / wall (nm) | Elements | Consumer leg | Quadrature agreement |
|---|---|---|---|
| 10 / 0.05 | 44,316 | +9.868e-03 | 9.273e-03 |
| 10 / 0.025 | 56,696 | -2.544e-03 | 6.062e-03 |
| 10 / 0.0125 | 82,384 | -3.008e-03 | 1.097e-02 |
| 2 / 0.0125 | 111,283 | -6.437e-03 | 5.363e-03 |
| 0.5 / 0.05 | 884,759 | +3.051e-03 | 6.800e-03 |
| 0.25 / 0.05 | 3,463,372 | **-1.062e-02** | 2.226e-02 |

and on the fixed 44,316-element mesh, raising the integration order instead (extra_order 0 -> 32,
i.e. order 8 -> 37) gives -71.289538, -71.289538, -71.957178, -72.212549, -71.800760, -72.053253,
-71.965410 e — oscillating at the 1e-3 to 1e-2 level and never settling. (The first two are
identical because `Measures.bonus_order` takes `max(extra, 3)` on a singular form, so `extra=3` *is*
the assembly order; see `06-numerics-fem.md`.)

**The cause is the field's own structure.** Along the densest `z` the table changes sign **49
times**, with extrema a **median 0.035 nm** apart — an order below the finest element the reference
mesh places. Pointwise quadrature of the bilinear interpolant therefore samples an oscillation it
cannot resolve, and an aliased integral converges in neither `h` nor order. The remedy is on the
producer side: depositing onto the finite-element space and rescaling to `Q_net` conserves by
construction, where sampling somebody else's interpolant at quadrature points cannot.

---

## 4. Mesh

**Nothing is stated.** No element count, element type, element order, refinement rule, boundary-layer
strategy, or mesh-convergence study appears anywhere in ch. 6, ch. 6 SI, ch. 5 or ch. 5 SI. The only
mesh reference is "integration ... over the final mesh" (T L425).

**Measured on the delivered vertex table [tested].** 185 vertices, traced **clockwise** (signed area
−26.4939 nm²), `r ∈ [1.65, 5.66]` nm, `z ∈ [−1.85, 12.25]` nm, sha256
`d0c2008140dc43d4cf7465d2c345f927a7b77110936f5d941976fc2122b0b386`. Minimum vertex spacing
**0.0361 nm**, on one edge; 10 of its 185 edges are shorter than the 0.05 nm reference wall size,
and 45 are shorter than 0.1 nm. Minimum local feature size **0.0806 nm**. Both minima are *below*
the conditioning thresholds the FR-08 contour pipeline enforces, and the reference mesh was
nevertheless built from this polygon at a 0.05 nm wall size and reached minimum element quality
0.6378 — which is why a *supplied* fixture is gated on validity, simplicity and loop topology but
not on spacing or feature size.

Measuring the local feature size needs a neighbourhood of **two edges either side**, not one: a
vertex is always within an edge length of the edge beyond its immediate neighbour, so excluding only
the two incident edges collapses the measure onto the shortest edge and reports 0.0361 nm — sampling
density — rather than 0.0806 nm, which is a feature.

The membrane's drawn inner corners, `(2.0, −1.4)` and `(3.5, +1.4)`, lie **0.275 and 0.540 nm inside
the pore body** on this table. The plane cuts on the pore's own outer surface are at **r = 2.7524 nm**
on `z = −1.4` and **r = 4.88 nm** on `z = +1.4`; the table already carries a vertex exactly at
`(4.88, +1.4)`. A junction gate written against the drawn corners asserts numbers the geometry never
produces.

## 5. Solver and sweeps

Stated: **COMSOL Multiphysics v5.4** (`epnpns.tex` L234-235). Everything else — PARDISO direct
solver, damped Newton with a lower-bounded variable damping factor — is author correspondence, not
the thesis; see `01-physics-epnpns.md` §7. No tolerances, no continuation/ramping scheme, no initial
guess, and no sweep ordering are recorded.

What the *outputs* imply about the sweep: `c_bulk` spans **0.005 to 5 M** and `V_bias` spans
**-200 to +200 mV** on a grid dense enough for contour plots (T L663-665). Tabulated points are
`c_bulk` in {0.005, 0.05, 0.15, 0.5, 1, 2, 5} M and `V_bias` in {+-50, +-100, +-150} mV (TA
`tab:ion_selectivities`). Experimental comparison used {0.05, 0.15, 0.5, 1, 3} M, +-200 mV, n = 3,
25 +- 1 C. The energy-barrier figure distinguishes **+0 mV from -0 mV** (they diverge for
c_bulk < 0.3 M), i.e. zero was approached from both signs rather than solved once (T L1160-1163).

---

## 6. Validation targets

### 6.1 Cation transport number `t_Na = G_Na/(G_Na+G_Cl)` and `P_Na = G_Na/G_Cl` (TA `tab:ion_selectivities`)

| c_bulk [M] | +150 mV | +100 | +50 | -150 | -100 | -50 |
|---|---|---|---|---|---|---|
| 0.005 | 0.996 (235) | 0.997 (313) | 0.998 (410) | 0.998 (500) | 0.998 (535) | 0.998 (542) |
| 0.050 | 0.906 (9.62) | 0.925 (12.3) | 0.941 (16.0) | 0.967 (29.6) | 0.966 (28.2) | 0.962 (25.1) |
| 0.150 | 0.786 (3.68) | 0.805 (4.13) | 0.824 (4.69) | 0.882 (7.51) | 0.874 (6.91) | 0.860 (6.16) |
| 0.500 | 0.642 (1.79) | 0.649 (1.85) | 0.657 (1.91) | 0.687 (2.20) | 0.680 (2.12) | 0.672 (2.05) |
| 1.000 | 0.566 (1.30) | 0.569 (1.32) | 0.572 (1.33) | 0.582 (1.39) | 0.579 (1.38) | 0.577 (1.36) |
| 2.000 | 0.502 (1.00) | 0.503 (1.01) | 0.503 (1.01) | 0.505 (1.02) | 0.505 (1.02) | 0.504 (1.02) |
| 5.000 | 0.445 (0.803) | 0.445 (0.803) | 0.445 (0.803) | 0.445 (0.802) | 0.445 (0.802) | 0.445 (0.802) |

Derived claims: cation-selective (`t_Na > 0.5`) for all voltages up to **c_bulk ~ 2 M**; minimum
**0.445 at 5 M**, still **~1.27x** the bulk NaCl value **0.35** (T L758-764). `t_Na ~ 0.9` requires
0.05 M at +150 mV but only 0.125 M at -150 mV (T L766-768).

### 6.2 Peak radially averaged equilibrium potential, V_bias = 0 (TA `tab:radial_potential`) [mV]

| c_bulk [M] | cis, z ~ 10 nm | lumen, z ~ 5 nm | trans, z ~ 0 nm |
|---|---|---|---|
| 0.005 | -80 | -108 | -144 |
| 0.05 | -34 | -50 | -86 |
| 0.15 | -19 | -29 | -57 |
| 0.5 | -9.3 | -14 | -30 |
| 5 | -1.9 | -1.7 | -4.2 |

Thermal voltage used for kT/e conversions: **25.7 mV** (-86 mV = -3.35 kT/e, checked).

### 6.3 Conductance, rectification, ion populations

| Quantity | Value | Source |
|---|---|---|
| Ionic conductance G | contour data only; no table. G is flat vs V for c > 1 M; log-log G(c) at +150 mV is linear, at -150 mV bi-linear with a knee near 0.15 M | T L662-679 |
| PNP-NS vs ePNP-NS | PNP-NS overestimates G over the whole range, converging to ePNP-NS below 0.01 M | T L683-685 |
| ICR = G(+V)/G(-V) | rises monotonically with abs(V); non-monotonic in c with a **peak at c = 0.15 M**, decaying to 1 at saturation | T L702-708 |
| Pore-average Na+ (rel.) | 0 mV: **34 at 0.005 M -> 4.4 at 0.05 M**; **2.1 at 0.15 M**; 1.14 >= x >= 1 for c >= 1 M | T L866-871 |
| Pore-average Cl- (rel.) | 0 mV: **0.05 at 0.005 M -> 0.31 at 0.05 M**; **0.58 at 0.15 M**; 0.89 <= x <= 1 for c >= 1 M | T L866-871 |
| Voltage sensitivity at 0.15 M | -150 -> +150 mV: Na+ **1.6 -> 2.7** (1.7x), Cl- **0.28 -> 1.06** (3.8x) | T L876-878 |
| Mobile charge in pore | up to ~0.15 M split evenly: **PS ~ +27 e**, **PB ~ +22 e**; at 5 M **PS = +58 e**, **PB ~ 0 e**; PT is **+10 to +15 e** higher at +150 than -150 mV across all c | T L961-969 |
| PS/PB split | wall distance d = 0.5 nm | T L951-955, TA |
| Debye length | ~1.4 nm at 0.05 M; < 0.2 nm at 5 M | T L721, L762 |
| Trans energy barrier | 0.005 -> 0.15 M: **1.8 -> 0.73 kT** at +150 mV; **4.4 -> 1.5 kT** at -150 mV; falls below 1 kT for c > 0.1-0.5 M | T L1243-1245, L1236-1238 |
| Cis anion barrier | 1.7 -> 0.5 kT for 0.005 -> 0.05 M | T L1195-1197 |

### 6.4 Electro-osmosis and pressure

| Quantity | Value | Source |
|---|---|---|
| Water velocity | at -100 mV, 0.5 M: **~0.07 m/s** at the lumen centre, **~0.21 m/s** at the constriction centre | T L1372-1374 |
| Profile shape | parabolic at low c; plug-like above 0.5 M; a **central dimple** in the constriction for c >= 1 M (self-induced pressure gradient at the pore exit) | T L1376-1386 |
| EOF conductance Q/V at -150 mV | **1.85** nm^3 ns^-1 V^-1 at 0.005 M -> **11.3** at 0.5 M (peak) -> **4.00** at 5 M | T L1400-1405 |
| EOF rectification EOR(V)=Q/V(+V) / Q/V(-V) | maximum at **c ~ 0.045 M**; crosses **unity at c ~ 0.45 M**; minimum at ~1 M; -> 1 at 5 M | T L1409-1414 |
| Pressure | osmotic hotspots **5-30 atm** at 0.15 M, 0 mV, peaking at **z = 11 nm** (cis entry), **z = 4.5 nm** (mid-lumen), **z = -1 nm** (constriction); magnitude roughly c-independent up to ~0.5 M | T L1444-1467 |

Cross-check (derived here): `Q(-100 mV, 0.5 M) ~ 1.13 nm^3/ns`; over a constriction of radius 1.65 nm
that is a mean velocity 0.13 m/s, parabolic peak 0.26 m/s, against the stated 0.21 m/s — consistent
to ~25 %, as expected for a partly flattened profile. Treat both as loose targets.

### 6.5 Correction-ablation targets (T `sec:transport:comparison_corrections`)

| Model | Ionic conductance vs full ePNP-NS | Water conductance vs full |
|---|---|---|
| no WDF (`D^w = mu^w = eta^w = 1`) | **+10 %** | **+25 to +50 %** |
| no CDF (`eps^c = D^c = mu^c = eta^c = rho^c = 1`) | **+5 %, +13 %, +29 %, +152 %** at 0.005, 0.05, 0.5, 5 M | -9 % at 0.005 M, +2 % at 1 M, **+82 % between 1 and 5 M** |
| no SMP (`beta = 0`) | within **+-3 %** everywhere | **-10 % at 0.5 M** |

### 6.6 Auxiliary formulas needed to compute the targets

- Simulated current: `I = F * integral_S ( SUM_i z_i * n . J_i ) dS` over the **cis** boundary (`eq:currentsim`).
- Bulk two-resistor reference: `I = (sigma(c) * pi / 4) * (l_cis/d_cis^2 + l_trans/d_trans^2)^-1 * V_bias`
  with `l_cis = 10 nm, d_cis = 6 nm, l_trans = 4 nm, d_trans = 3.3 nm` (`eq:bulk_nanopore_current`). No access resistance.
- Flow rate: `Q = integral_S (n . u) dS` (`eq:flowrate`).
- Radial average: `<phi>(z) = (1/(pi R(z)^2)) * integral_0^R(z) phi(r,z) 2 pi r dr` (`eq:epnp-ns_radpot`).
- Pore average: `<X>_a = II beta_a X dr dz / II beta_a dr dz` (`eq:pore_surface_integral`) — see gap G6.
- B-factor: `B_i = (8/3) pi^2 MSD_i`, last 10 ns, QCP via MDAnalysis (`eq:bfactor`).

---

## 7. Stated limitations and caveats

- ePNP-NS **slightly overestimates** the current for c_bulk < 0.15 M; agreement is best for
  c_bulk >= 0.15 M (T L646-654).
- ICR does not match quantitatively below 0.5 M — trends only (T L711-715).
- Two reasons offered for the low-salt failure: (i) mobilities were fitted to *bulk* conductances in
  locally electroneutral solution, and inside a co-ion-depleted pore only one ion species is present,
  so the mobility model breaks down; (ii) the pore may narrow slightly at low salt, which a static
  geometry and static charge map cannot capture (T L724-731).
- Results are steady-state continuum: they represent a **10-100 ns time average** (T L847-849).
- Reversal-potential selectivity is not the symmetric-condition selectivity: the measured
  `t_Na = 0.66` (`P_Na = 1.9`) of Franceschini et al. sits between the simulated cis (1 M, 0.57) and
  trans (0.15 M, 0.84) values; the GHK equation ignores EOF-driven flux and assumes Nernst-Einstein
  holds at all concentrations (T L770-781).
- Radial averaging is expected to fail for narrow or non-axisymmetric pores (internal corrugations,
  opposing charges in one radial plane) — a 3D treatment is required there (T L433-451).

---

## 8. Gaps and ambiguities (questions for the author)

- **G1 — "every 100 fs" is impossible.** T L280-281 says the 50 frames were taken from the final 5 ns
  "i.e. every 100 fs". 50 frames over 5 ns is **every 100 ps**, and coordinates were only written
  every 5 ps (T L273-274). Assume 100 ps. **Evidence, 25 September 2026 (§1.1):** the archived PQR
  files are named `…_aligned_100ps_NN`, 99 of them, and the analysis notebook reads the DCD at
  `dt=100`. **CLOSED [tested], §1.1:** the DCD frames are the PQRs at 100 ps, in time order. The final
  5 ns are PQRs 50–99 (DCD frames 48–97).
- **G2 — 25 % isolevel is unjustified.** No rationale, no sensitivity study, no comparison against
  the solvent-excluded surface. Since pore radius enters conductance roughly as r^2, this is the
  single largest untested lever in the geometry. Ask what other isolevels were tried.
- **G3 — the manual vertex edit is unreproducible.** The final boundary polyline is not published and
  its vertex count is not stated; the 30-degree-wedge claim is qualitative. Without the vertex list a
  bit-for-bit geometry match is impossible; treat +-1 % on conductance as the tolerance floor.
- **G4 — `q_i/(2 pi r_i)` vs `/(2 pi r)`.** The prose (T L404-408) divides by the **atom's** radial
  position `r_i`; the implementation (COMSOL, KB 01 §5) divides by the **field point's** `r`. These
  differ within the Gaussian's support and diverge differently near the axis. The COMSOL form is what
  produced -72.9 e, so implement that; but the discrepancy should be confirmed.
- **G5 — CLOSED [tested], §3.1.** The file stores the sum *without* `e`, in `e/m^2`: its planar
  integral is the integer -72, to 4.7e-12. `e_const` in the COMSOL assembly supplies the coulombs
  exactly once, and the `e` printed inside eq. `eq:scdpore` is not also in the table.
- **G6 — pore averages omit the `2 pi r` Jacobian.** `eq:pore_surface_integral` integrates
  `beta * X dr dz`, an unweighted area average in the (r,z) half-plane, while the main text calls it
  an average "over the entire pore volume" (T L823). A true volume average needs `2 pi r dr dz`.
  Every number in §6.3 that is a pore average (Na+/Cl- ratios, PS/PB charges) depends on this choice;
  the wall-adjacent PS region is systematically under-weighted without the Jacobian. Must be resolved
  before those become regression targets. Related: `<Q_ion>_PS` and `<Q_ion>_PB` are quoted in units
  of `e` (i.e. counts, hence genuine volume integrals), not averages, despite the `< >` notation.
- **G7 — radial potential at 0.15 M is internally inconsistent.** T L1117-1118 states the lumen value
  as "approx -14 mV" (and that it is below 1 kT/e) and the constriction as "approx -47 mV", but
  `tab:radial_potential` gives **-29 mV** and **-57 mV** at 0.15 M. -29 mV is *above* 1 kT/e, so the
  prose claim fails against its own table. The -14/-30 pair matches the **0.5 M** table row, so the
  text may have been written against a different row. Trust the table.
- **G8 — constriction z-range sign typo.** T L1043 prints "1.85 < z < 1.6 nm"; everywhere else it is
  **-1.85 < z < 1.6 nm** (T L881, L1076, TA). Use -1.85.
- **G9 — bilayer placement in z is never stated.** Thickness 2.8 nm is given but its z-centre is not.
  The pore spans -1.85 to 12.25 nm and the constriction is symmetric about z ~ 0, so a bilayer
  centred at z = 0 (spanning -1.4 to +1.4 nm) is the obvious reading, but it is an inference.
  Compounding this, the MD/electrostatics frame places the structure's centre of mass at
  (0, 0, 55 Angstrom) (TA `eq:internal_radius` discussion) — the shift from MD coordinates to model
  coordinates is not given anywhere. **Evidence, 25 September 2026 (§1.1):** the protein-only MD
  archive carries no lipids, so the bilayer cannot fix it. But the MD frame's all-atom extent
  brackets the model's pore extent to within 0.3–0.4 nm at each end, which is consistent with an
  offset near zero. **CLOSED by the author, 25 September 2026:** the MD trajectory was centred on
  the middle of the bilayer, so ClyA's `centre_z_nm` is 0 in the MD frame.
- **G10 — CLOSED [tested], §3.1.** `r` in [0, 7] nm, `z` in [-3.5, 13.5] nm at 0.005 nm:
  1401 x 3401 = 4.76e6 nodes, the order the estimate predicted.
- **G11 — nothing on mesh or solver tolerances.** See §4 and §5. No convergence study of any kind is
  reported, so the published numbers carry no stated discretisation error bar.
- **G12 — MD ion parameters unspecified beyond "CHARMM36"** (no NBFIX / Beglov-Roux statement).
  Irrelevant to the continuum solve, needed only if the MD is rerun.
- **G13 — "average between cis and trans" arithmetic.** T L770-774 says the measured 0.66 corresponds
  to the average of 0.57 (1 M) and 0.84 (0.15 M); the arithmetic mean is 0.705, and for `P_Na` the
  mean of 1.3 and 5.4 is 3.35 versus the measured 1.9. The claim is qualitative, not arithmetic.

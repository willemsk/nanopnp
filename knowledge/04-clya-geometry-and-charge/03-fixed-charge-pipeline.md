---
type: Pipeline
title: 3. Fixed-charge pipeline
description: 'The fixed-charge pipeline: the delivered table, the 1.25 % aliasing
  and the closed-form kernel.'
tags:
- clya
- pipeline
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
verified:
- by: process:arithmetic
  at: '2026-10-14T00:00:00Z'
- by: process:tests/tier1/test_charge_deposit.py::test_ver01_truncated_patch_fails_the_producer_leg
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_charge_deposit.py::test_ver01_ver02_correct_deposit_passes_every_gate
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_charge_kernel.py::test_ver58_kernel_integrates_to_its_charge
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_charge_kernel.py::test_ver58_tiled_sum_equals_the_direct_sum
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_charge_kernel.py::test_ver58_unrenormalised_axis_sum_is_short_by_the_end_correction
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_knowledge_arithmetic.py::test_charge_kernel_z_marginal_and_erfc_cumulative
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_charge_potential_axis.py::test_ver58_deposited_potential_converges_at_the_potentials_own_rate_on_the_axis
  at: '2026-10-16T00:00:00Z'
sources:
- id: wp28-plan
  resource: docs/plans/wp28-charge-projection.md
  title: WP28 charge projection plan, Design §1
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
computational domains** (T L418-429). Axis guard, verbatim COMSOL (see `knowledge/01-physics-epnpns/05-fixed-charge-from-structure.md`):

```
scd_pore = if(r < 0.01[nm], 0, e_const * rhoq_pore(r,z) / (2*pi*r))     [C m^-3]
```

**Net charge check (a regression target):** integrating the resulting volumetric density over the
final mesh gives **-72.9 e**, against **-72 e** for the atomistic model (T L425-427). Any
reimplementation must land within ~1 % of -72 e.

### 3.1 The delivered table, measured [verified][^wp28-plan] {#31-the-delivered-table-measured}

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

### 3.2 The reference's 1.25 % is the *consumer's*, and it is aliasing [verified][^wp28-plan] {#32-the-references-125-is-the-consumers-and-it-is-aliasing}

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
the assembly order; see `knowledge/06-numerics-fem/index.md`.)

**The cause is the field's own structure.** Along the densest `z` the table changes sign **49
times**, with extrema a **median 0.035 nm** apart — an order below the finest element the reference
mesh places. Pointwise quadrature of the bilinear interpolant therefore samples an oscillation it
cannot resolve, and an aliased integral converges in neither `h` nor order. The remedy is on the
producer side: depositing onto the finite-element space and rescaling to `Q_net` conserves by
construction, where sampling somebody else's interpolant at quadrature points cannot.

### 3.3 The closed-form kernel on the 0.005 nm lattice **[tested: tests/tier1/test_charge_kernel.py::test_ver58_unrenormalised_axis_sum_is_short_by_the_end_correction]** **[tested: tests/tier1/test_charge_kernel.py::test_ver58_kernel_integrates_to_its_charge]** **[tested: tests/tier1/test_charge_kernel.py::test_ver58_tiled_sum_equals_the_direct_sum]** {#33-the-closed-form-kernel-on-the-0005-nm-lattice}

PHY-16 step 5's kernel, `ρ̄_i = q_i π^(−3/2) w⁻³ exp(−((r − r_i)² + (z − z_i)²)/w²) Ĩ₀(2 r r_i/w²)` with
`Ĩ₀ = scipy.special.i0e`, measured 1 October 2026 while planning WP28:

| Atom | `∫ ρ̄ 2πr dr dz` (adaptive quadrature) | Trapezoid sum on the `h = 0.005` nm lattice, node on `r = 0` |
|---|---|---|
| `r_i = 0`, `w = 0.05` nm | 1 to 10⁻¹⁵ | −1.67 × 10⁻³ |
| `r_i = 0.02`, `w = 0.05` | 1 | −1.42 × 10⁻³ |
| `r_i = 0.05`, `w = 0.1` | 1 | −3.25 × 10⁻⁴ |
| `r_i = 0.1`, `w = 0.0112` (CHARMM polar H) | 1 | −1.4 × 10⁻¹⁵ |
| `r_i = 3`, `w = 0.0112` and `w = 0.1` | 1 | ≤ 10⁻¹⁵ |

- **Off the axis the lattice sum is exact** even for the smallest CHARMM width, `w = 0.5 × 0.2245 Å`
  (`w/h = 2.24`): the trapezoid rule on a Gaussian errs by `~2 exp(−π² w²/h²)`, 10⁻²¹ here.
- **Near the axis it is short by `h²/(6 w²)`.** The integrand `2πr ρ̄` rises linearly from `r = 0`,
  and the Euler–Maclaurin end correction `(h²/12) f'(0)` divided by the atom's charge gives
  `h²/(6w²)`, which is −1.67 × 10⁻³ at `w = 0.05` nm: above QR-03's 10⁻³. Renormalising each atom on
  the lattice removes it. ClyA's innermost atoms sit at `r ≳ 1.6` nm, where it does not arise.
- **The kernel is separable**, `Z_i(z) · R_i(r)`, so a frame's lattice is one sparse product and an
  atom's lattice sum is a product of two 1D sums. `exp(−(r − r_i)²/w²) · Ĩ₀(...)` overflows nowhere,
  even at `2 r r_i/w² ~ 10⁶`.
- **The z-marginal survives azimuthal averaging exactly**: `∫ ρ̄_i 2πr dr = q_i exp(−(z − z_i)²/w²)/(w√π)`.
  So under the weight `½ erfc((z − p)/s)` an atom's charge below plane `p` is
  `q_i ½ erfc((z_i − p)/√(s² + w²))`, which agrees with adaptive quadrature to round-off
  [tested: tests/tier1/test_knowledge_arithmetic.py::test_charge_kernel_z_marginal_and_erfc_cumulative]. That is the closed-form per-plane reference of the §4.4 NOTE on the producer path.

Measured implementing it (WP28, 1 October 2026) **[tested: tests/tier1/test_charge_deposit.py::test_ver01_truncated_patch_fails_the_producer_leg]** **[tested: tests/tier1/test_charge_deposit.py::test_ver01_ver02_correct_deposit_passes_every_gate]** **[tested: tests/tier2/test_charge_potential_axis.py::test_ver58_deposited_potential_converges_at_the_potentials_own_rate_on_the_axis]** **[verified][^wp28-plan]**:

- **A `2w` patch without renormalisation loses 0.83 %, not the continuum's 0.933 %.** The
  continuum loss `1 − erf(2)²` is offset by the trapezoid rule's own end terms at the cut,
  `2h e⁻⁴/(w√π)`, at `h = 0.005` and `w = 0.1` nm. The pipeline's box is `6 w_max` beyond the atoms
  whatever the patch, so a truncated patch fails the producer leg, never the boundary ring.
- **An atom on the axis keeps its end correction in its shape after renormalisation.** The total
  is exact, but `O(h²/w²)` of the charge is redistributed near `r = 0` and does not fall with the
  mesh. In VER-58's sphere (`w = 0.25` nm, `P2`, 0.05 nm near the atom) it is the disc error's
  floor: 4.1 × 10⁻⁵, 1.9 × 10⁻⁵ and 1.7 × 10⁻⁵ at `h` = 0.01, 0.005 and 0.0025 nm, with the on-axis
  error 1.2 × 10⁻³, 3.3 × 10⁻⁴ and 1.1 × 10⁻⁴. ClyA's innermost atoms are at `r ≳ 1.6` nm.
- **The deposit's per-plane error is the mesh's `P2` fit to the erf weight, and falls as `h³`.** On
  the cylindrical test pore (`P2`, `s = 0.5` nm) the worst mesh plane against the atoms is 3.15 ×
  10⁻³, 2.30 × 10⁻⁴, 7.84 × 10⁻⁶ and 1.68 × 10⁻⁷ at `maxh` 1, 0.5, 0.25 and 0.125 nm, and about six
  times smaller at `s = 1` nm. So a 1 nm mesh fails the 10⁻³ gate by the check's own error, as
  *Design* §3 of the WP28 plan predicts, and the lattice side holds to 10⁻¹⁴ throughout.
- **The protonated 2WCD deposits with five orders to spare.** At pH 7.5 (53,760 charged atoms,
  `Q_net` −60 e) on its generated mesh at the default sizes (44,987 elements, `P2`), both legs hold
  to 4 × 10⁻¹⁴, the worst lattice plane to 5 × 10⁻¹⁵ and the worst mesh plane to 4.0 × 10⁻⁶; at
  `size_scale` 4 (6,185 elements) the mesh plane is 1.6 × 10⁻⁴. The lattice is 1334 × 3090 nodes.
  97.7 % of `Σ|q_i|` has its atom centres in the solids, and the deposit puts −84.8 e in the protein,
  +24.0 e in the electrolyte and +0.7 e in the membrane: the Gaussians of the surface's charged side
  chains reach past the 25 % isolevel. Stage 7 cold takes 9.0 s (sum 2.7, deposit 5.5, gates 0.4)
  and 0.92 GB peak, split as measured before the solid-share check moved ahead of the sum: it was
  counted in `deposit` then and is in `gates` now, and the total is unchanged; 50 frames sum in 119.8 s, 2.40 s per frame, at 0.96 GB.
- **The reference's 2D construction differs from the azimuthal mean at first order, not second.**
  Off the axis, `2πr ρ̄_i` is the 2D Gaussian times `(r/r_i)^½ (1 + O(w²/r r_i))`. The difference is
  `(r − r_i)/(2 r_i)` of the local value, odd about the atom, and peaks at
  `(w/2r_i)/√(2e) = 0.214 w/r_i` of the peak. The charge and every z-marginal agree, and the 3D
  construction's radial centroid lies `w²/(4 r_i)` further out: 0.6 pm for a 0.1 nm atom at
  `r_i = 1.6` nm.

---

[^wp28-plan]: `docs/plans/wp28-charge-projection.md`, Design §1 (`prod5_clya_charge` table and reference-mesh quadrature audit).

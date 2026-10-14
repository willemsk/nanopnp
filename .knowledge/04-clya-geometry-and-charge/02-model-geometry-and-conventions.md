---
type: Pipeline
title: 2. Model geometry and conventions
description: The model geometry and its conventions, with the bilayer profile and the ion-exclusion shell
  measured.
tags:
- clya
- pipeline
sources:
- id: paper
  resource: https://doi.org/10.1039/D0NR03114C
  title: Willems et al., Nanoscale 12, 16775-16795 (2020)
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
verified:
- by: process:arithmetic
  at: '2026-10-14T00:00:00Z'
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

### 2.1 The bilayer on a structure-derived profile, measured [tested: pending] {#21-the-bilayer-on-a-structure-derived-profile-measured}

Stage 5 (WP21) derives the membrane's inner edge from the profile rather than drawing it. On each
plane `z = ±1.4` nm (model frame) the lumen-adjacent body interval is the profile's two smallest
crossings, and the edge is the chord between the two intervals with the widest margin to the
profile (SPECIFICATION.md §5.2.1 NOTE on the membrane junction).

| | ClyA fixture | 2WCD, stage 4 |
|---|---|---|
| Profile vertices | 185 | 161 |
| Frame shift `centre_z_nm` | 0 | 4.62887 (trans tip 2.77887 + 1.85) |
| Lumen-adjacent intervals (nm) | [1.725, 2.7524], [2.96, 4.88] | [1.630, 2.8373], [3.089, 4.8256] |
| Widest-margin chord (nm) | (1.9818, 3.4700) | (1.9321, 3.4690) |
| Clearance (nm) | 0.2365 | 0.3017 |
| Drawn chord, for comparison | (2.0, 3.5), clearance 0.214 | — |
| Face areas (nm²): protein, membrane, electrolyte | equal to the drawn region's to 1e-10 relative | 28.109, 688.42, 97,458 |

- **The chord between the intervals' mid-points is wrong on both profiles.** On the fixture it
  runs (2.2387, −1.4) to (3.92, +1.4) and crosses the fluid cleft under the cap between
  (3.070, −0.016) and (3.235, 0.260), splitting the electrolyte in two. **[tested: pending]**
- **Any admissible chord gives the same region**: a pocket between two chords would be enclosed by
  them, the body and the plane stretches between their ends, which are body too, yet the
  complement of a simple polygon is connected. **[verified]**
- **A plane that crosses the profile more than twice always splits a domain.** The gap between
  the first two intervals is fluid bounded by body at both ends, and the arms either side of it
  join above the plane or below it. Joined above, the fluid over the gap is enclosed and is a
  second electrolyte face; joined below, the pocket under it is a second membrane face (and
  electrolyte where it passes the other plane). So "the membrane meets the body at `r₂`, not
  `r₄`" cannot be tested on a four-crossing body: no such body assembles. **[verified]** by the
  argument, **[tested: pending]** on a hook and a bridge profile, refused naming each face's centroid.
- **The 1.85 nm trans-tip offset is the fixture's own** (pore axial extent −1.85 ≤ z, bilayer
  centre 0). Applying it to 2WCD is a test-time registration, not a VAL-05 claim.

### 2.2 The ion-exclusion shell and the derived `χ` on 2WCD, measured [tested: pending] {#22-the-ion-exclusion-shell-and-the-derived-on-2wcd-measured}

WP30 (FR-15, VER-59), on the prepared 2WCD registered by its C-alpha centroid (VAL-05's frame),
`h_c` = 0.05 nm, with the shell at `a` = 0.25 nm (`a_Na/2`) and `δ` = 0.15 nm
(`tests/tier2/test_exclusion_2wcd.py`). Stage 5 offsets the 2WCD profile, which has about 160
vertices, closes it and resamples its ring at uniform arc length near `1.05 h_c`. The ring has 692
vertices, and step 6 removes none of them. No pocket closes, so no hole is filled.

| Quantity | Value |
|---|---|
| Deepest ring edge from the body | 0.24689 nm, against the gated 0.24 nm (`.knowledge/06-numerics-fem/09-ngsolve-traps-found-by-implementing.md#814-a-geos-round-join-offset-then-step-6-is-not-within-a-chords-sagitta-of-the-offset`) |
| Farthest ring vertex | 0.29891 nm: grooves the `2h_c` closing filled |
| `wall` nodes of the default-size mesh | [0.24753, 0.28177] nm from the body; 8.1 % of 605 beyond `a + 10⁻⁶` |
| Areas (nm²) | shell 7.885, protein 28.109 (unchanged by the shell) |
| Mesh at the default sizes | 51,599 triangles, min SICN 0.634, min gamma 0.586; wall segments mean 1.045 and max 1.050 × the target |
| Stage 5 / stage 6 | 1.2 s / 11 s |
| `χ` means at `size_scale` 4 with the deposit (`pnp`, 14,036 triangles) | protein 0.985, `exclusion` 0.056, membrane 1, electrolyte 0 |
| `χ` lattice at `δ` = 0.15 nm | 584 × 1926 samples, 0.28 s, 20 MB peak allocation |
| `χ` lattice at `δ = h_c` | 1669 × 5694 samples (76 MB), 1.4 s, 171 MB peak allocation: 2.25 lattices, with the step taken in place (390 MB, five lattices, through `smooth_step`'s temporaries) |
| `χ` worst error in the band, clear of the membrane | 7.8e-3 at `δ = h_c`, 1.1e-2 at 0.15 nm; 95th percentile 1.3e-3 |

- **The shell's mean `χ` is the planar estimate.** `3δ/(32a)` = 0.0563 at these values, measured
  0.056 on 2WCD and 0.0539 on the convex VER-59 parallelogram, where the corners spread the step.
  A remap of the stage-3 mean would not have given a width independent of `|∇ρ|` (WP30 plan,
  *Design* §1). **[verified]** by the arithmetic, **[tested: pending]** by the means.
- **The worst `χ` error sits at the profile's concave vertices**, where the medial axis crosses the
  band and `χ` has a kink. Measured, it is 1.1e-2 against *Design* §1's estimate of `0.75 h · 3/δ`
  ≈ 0.04 there. Off the vertices the bilinear bound `0.75 (h/δ)²` = 1.9e-3 holds: the 95th
  percentile is 1.3e-3.
- **The shell does not reach the membrane's outer region.** It is carved against the unchanged
  quadrilateral and starts at the junction `r₂` on each plane, so the membrane, its chord and its
  junction are the shell-free region's, and so is the protein's area.

---


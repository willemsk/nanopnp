---
type: Test Evidence
title: 'Tier-2 test evidence: electro-osmosis, electrophoresis and the force routes'
description: What the Tier-2 tests of electro-osmosis, electrophoresis and the drag and Maxwell force routes establish.
tags:
- analyte
- test-evidence
sources:
- id: electrophoretic-mobility-3782c43
  resource: git:3782c43:tests/tier2/test_electrophoretic_mobility.py
  title: Module docstring of tests/tier2/test_electrophoretic_mobility.py before WP45
    (commit 3782c43)
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
verified:
- by: process:arithmetic
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_electroosmosis.py::test_ver14_rice_and_whitehead_capillary_profile
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_electroosmosis.py::test_ver15_helmholtz_smoluchowski_limit_and_its_approach_rate
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_electrophoretic_mobility.py::test_ver21_the_huckel_limit_is_recovered_at_small_kappa_a
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_electrophoretic_mobility.py::test_ver21_the_mobility_climbs_towards_the_smoluchowski_limit
  at: '2026-10-14T00:00:00Z'
- by: process:tests/tier2/test_electrophoretic_mobility.py::test_ver21_the_mobility_follows_henrys_function_at_every_screening_ratio
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_electrophoretic_mobility.py::test_ver21_the_zeta_potential_is_the_same_in_both_solves
  at: '2026-10-14T00:00:00Z'
- by: process:tests/tier2/test_maxwell_sphere.py::test_ver20_a_charged_body_in_a_uniform_field_feels_q_e_zero
  at: '2026-11-10T00:00:00Z'
- by: process:tests/tier2/test_maxwell_sphere.py::test_ver20_the_net_force_on_a_dielectric_sphere_vanishes
  at: '2026-11-10T00:00:00Z'
- by: process:tests/tier2/test_stokes_drag.py::test_ver19_a_uniform_far_field_measures_the_wall_correction_instead
  at: '2026-11-10T00:00:00Z'
- by: process:tests/tier2/test_stokes_drag.py::test_ver19_stokes_drag_converges_to_the_closed_form
  at: '2026-11-10T00:00:00Z'
---

## Tier-2 test evidence: electro-osmosis, electrophoresis and the force routes

- **[tested: tests/tier2/test_electroosmosis.py::test_ver14_rice_and_whitehead_capillary_profile]** Electro-osmosis in a cylindrical capillary (Rice & Whitehead, *J. Phys. Chem.* **69**, 4017, 1965): for radius `a`, Debye length `λ` and zeta potential `ζ` under a uniform axial field `E`, the fully developed velocity is `u_z(r) = −(εζE/η)[1 − I₀(κr)/I₀(κa)]`. In the NUM-09 variables (potential in `V_T`, velocity in `u₀ = εV_T²/(ηL₀)`) it carries no material constant: `ũ_z(r) = Ẽζ̃[I₀(r/λ)/I₀(a/λ) − 1]`. **[tested: tests/tier2/test_electroosmosis.py::test_ver15_helmholtz_smoluchowski_limit_and_its_approach_rate]** Its thin-double-layer limit approaches the Helmholtz-Smoluchowski slip `−ζ̃Ẽ` at the centreline with deviation exactly `1/I₀(a/λ)`. Source: `tests/tier2/test_electroosmosis.py` (VER-14, VER-15).
- **[tested: tests/tier2/test_electroosmosis.py::test_ver14_rice_and_whitehead_capillary_profile]** In the electro-osmosis solve the radial part of the electrical body force, `2Sψ̃ψ̃′`, is a pure gradient and is taken into the pressure, with the body force built from the applied potential `−Ẽz`; this leaves `p̃ = 0` at both ends, so the traction-free condition holds exactly rather than approximately. Source: `test_electroosmosis.py` (module docstring at `3782c43`, before WP45).
- **[tested: tests/tier2/test_electrophoretic_mobility.py::test_ver21_the_mobility_follows_henrys_function_at_every_screening_ratio]** Electrophoresis of a charged sphere (VER-21): the free particle's mobility is the ratio of the field-solve force `F_E` to the drag-solve force `F_U`, `μ̃_e = F_E Ũ₀/(F_U Ẽ₀)`, in units of `εV_T/η`. **[tested: tests/tier2/test_electrophoretic_mobility.py::test_ver21_the_huckel_limit_is_recovered_at_small_kappa_a]** Henry's function is `μ_e = (2εζ/3η) f(κa)` with `f(0) = 1` (Hückel, `μ̃ = 2ζ̃/3`) and `f(∞) = 3/2` (Smoluchowski, `μ̃ = ζ̃`). The reference is Ohshima's approximation (*J. Colloid Interface Sci.* **168**, 269, 1994): `f(x) = 1 + 1/(2[1 + 2.5/(x(1 + 2e^{−x}))]³)`. Source: `tests/tier2/test_electrophoretic_mobility.py`.
- **[tested: tests/tier2/test_electrophoretic_mobility.py::test_ver21_the_mobility_climbs_towards_the_smoluchowski_limit]** The approach to Smoluchowski goes as `1/κa` and is slow: at `κa = 16.5`, the largest the Tier-2 budget affords (about 44 000 dof, 16 s; a 5 % gate needs about 40), Henry is still 11.5 % below `εζ/η`. The Smoluchowski gate is therefore 15 %, and the Henry gate (5 % at every `κa`) carries the verification. The Hückel end needs no allowance: at `κa = 0.5`, `f = 1.014`. Source: `test_electrophoretic_mobility.py` (`test_ver21_the_mobility_climbs_towards_the_smoluchowski_limit`).
- **[verified][^electrophoretic-mobility-3782c43]** The far field of the force-free pair is uniform to `O((a/R)³)`, because a force-free particle radiates no Stokeslet; imposing the exact translating-sphere field on the outer boundary would inject an `O(a/R)` Stokeslet that the physical solution does not have. A single confined drag solve at `R = 10a` instead carries a 28 % wall correction (the `1 + (9/4)(a/b)` form), **[tested: tests/tier2/test_electrophoretic_mobility.py::test_ver21_the_mobility_follows_henrys_function_at_every_screening_ratio]** which divides out of the force ratio. Source: `test_electrophoretic_mobility.py` (module docstring at `3782c43`, before WP45).
- **[tested: tests/tier2/test_electrophoretic_mobility.py::test_ver21_the_zeta_potential_is_the_same_in_both_solves]** `ζ` is read back as the `r`-weighted mean of `φ̃` over the body surface, not prescribed: prescribing `φ̃ = ζ` makes the body an equipotential, which expels the applied field and gives a different `f(κa)`. The applied perturbation is odd in `z` and averages out of the mean. Source: `test_electrophoretic_mobility.py` (`_surface_mean_potential`, `test_ver21_the_zeta_potential_is_the_same_in_both_solves`).
- **[tested: tests/tier2/test_electrophoretic_mobility.py::test_ver21_the_mobility_follows_henrys_function_at_every_screening_ratio]** Measured departures from Henry's `2f(κa)/3` are 2.3 %, 0.9 % and 1.5 % at `κa = 0.50`, `2.08` and `16.5`; they are set by the finite domain and by reading a nonlinear `ζ` into a linear-response formula. Source: `test_electrophoretic_mobility.py` (`HENRY_TOLERANCE`).

- **[tested: tests/tier2/test_stokes_drag.py::test_ver19_stokes_drag_converges_to_the_closed_form]** **[tested: tests/tier2/test_stokes_drag.py::test_ver19_a_uniform_far_field_measures_the_wall_correction_instead]** **[tested: tests/tier2/test_maxwell_sphere.py::test_ver20_the_net_force_on_a_dielectric_sphere_vanishes]** **[tested: tests/tier2/test_maxwell_sphere.py::test_ver20_a_charged_body_in_a_uniform_field_feels_q_e_zero]** **[tested: tests/tier2/test_electrophoretic_mobility.py::test_ver21_the_mobility_follows_henrys_function_at_every_screening_ratio]** The force routes on a sphere (VER-19 to VER-21; `tests/tier2/`). On a P2 sphere of
  radius 1 nm in a box of radius 10 nm, `a = 1 nm` mesh units, the numbers are:

  | Check | Measured | Reference |
  |---|---|---|
  | Stokes drag, three meshes (VER-19) | 0.430870, 0.430522, 0.430500 pN | `6πηaU` = 0.430491 pN |
  | its relative error | 8.80 × 10⁻⁴ → 7.11 × 10⁻⁵ → 1.98 × 10⁻⁵ | rates 3.63 and 1.85 per halving |
  | Maxwell integral on an uncharged dielectric sphere (VER-20) | −8.6 × 10⁻⁸ pN (domain), +7.0 × 10⁻⁵ pN (surface) | 0 |
  | `F = qE₀` anchor, −4 e at 5.1 MV/m (VER-20) | −8.21704 pN (domain), −8.18903 pN (surface) | −8.23281 pN, i.e. 0.19 % and 0.53 % |
  | Henry mobility at κa = 0.50 / 2.08 / 16.47 (VER-21) | `μ̃_e/ζ̃` = 0.661, 0.704, 0.872 | `2f(κa)/3` = 0.676, 0.711, 0.885 |

  Two findings worth carrying forward. **The far field decides whether VER-19 measures anything**:
  a uniform stream at `R = 10a` gives 1.285 × the drag, the `1 + (9/4)(a/b)` wall correction of a
  sphere in a concentric container, so the exact Stokes field has to be imposed instead. And **the
  zero test cannot stand alone**: a net force of zero on a polarised sphere is invariant under a
  uniform scale factor, so the `qE₀` anchor is what pins the magnitude of the Maxwell route, which
  has no reaction-route oracle because `φ` is not constrained on the body's surface.

[^electrophoretic-mobility-3782c43]: `git show 3782c43:tests/tier2/test_electrophoretic_mobility.py`, module docstring (before WP45).

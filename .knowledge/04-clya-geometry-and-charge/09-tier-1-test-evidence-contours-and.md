---
type: Test Evidence
title: 'Tier-1 test evidence: contours and charge deposition (WP45 item 20)'
---

## Tier-1 test evidence: contours and charge deposition (WP45 item 20)

- **[tested]** A square pyramid's level set is exact to round-off when `a(1 − l) = (k + ½)h`: `f` is linear along every grid edge, and the loop's area is the square's less `h²/2`, since each corner cell cuts a triangle of legs `h/2`. A transposed axis, a half-bin shift or a `w/h` scale misplaces a vertex by at least `h/2`. Source: `tests/tier1/test_contour.py` (`test_ver51_pyramid_contour_is_exact`).
- **[tested]** On a grid line through a Gaussian's centre, linear interpolation of `f` misplaces the 0.25-level crossing by at most `h²|f″|/(8|f′|)`, 4.7 × 10⁻⁴ nm at the test's spacing. Source: `test_contour.py` (`test_ver51_gaussian_section_subpixel`).
- **[tested]** Taubin smoothing scales a regular 64-gon's area by `f(k₁)^{2N}` with `f = (1 − λk₁)(1 − μk₁)` and `k₁ = 1 − cos(2π/64)`; the Laplacian (`μ = 0`) scales it by `(1 − λk₁)^{2N}`. At `N = 10` the two differ by 5 %. Source: `test_contour.py` (`test_ver51_taubin_keeps_area_laplace_shrinks`).
- **[tested]** Closing and opening by `2h` fill a 0.1 nm slot, remove a 0.1 nm fin and keep a 0.3 nm slot; each concave corner of a hole moves by at most `δ²(1 − π/4)`. Source: `test_contour.py` (`test_ver51_closing_fills_subresolution_slot`).
- **[tested]** Charge patch truncated at `±2w` and not renormalised loses `1 − erf(2)² = 0.93 %`; the end nodes keep their trapezoid weight and give back `h·exp(−4)/(w√π) = 5 × 10⁻⁴` per axis, 0.83 % on the lattice. Source: `tests/tier1/test_charge_deposit.py` (`test_ver01_truncated_patch_fails_the_producer_leg`).
- **[tested]** An unrenormalised on-axis lattice sum is short by `h²/(6w²)` (10 % at the test's spacing); renormalised it is exact. Source: `tests/tier1/test_charge_kernel.py` (`test_ver58_unrenormalised_axis_sum_is_short_by_the_end_correction`).
- **[tested]** A P0 deposit conserves charge but fails the Galerkin first-moment test that P1 passes (Design §5). Dropping the renormalisation on an axis atom fails the producer leg only, at −1.67 × 10⁻³. Source: `test_charge_deposit.py`.
- **[tested]** Dropping the `2πr` Jacobian and rescaling globally to `Q_net` passes both conservation legs and fails the per-plane check (1.6 for 1.0). Source: `test_charge_deposit.py` (`test_ver02_…`).
- **[tested]** The kernel's limit from 3D Cartesian Gaussian deposition binned by exact annular overlaps converges at ≥ 3.5× per halving of the spacing, below 10⁻³ at the finest. Source: `test_charge_kernel.py` (`test_ver58_kernel_is_the_limit_of_the_3d_deposition…`).
- **[tested]** At 1 nm elements the deployed field's per-plane error under the 0.5 nm weight is 3.2 × 10⁻³ (refused by the gate); at 0.5 nm it is 2.3 × 10⁻⁴. Source: `tests/tier1/test_charge_stage.py` (`test_ver01_the_producer_stage_deposits_keys_and_records_its_report`).
- **[tested]** At the reference mesh the 0.01 nm axis guard is a fifteenth of an element, so no mesh integral sees its edge. The whole-grid conservation integral is a trapezium rule on a field that decays to zero (exact beyond all orders); the guard's partial integral carries an `O(h²)` term. What the guard leaves is about a seventh of the grid's charge, and its element-scale step costs a fixed fraction of the total. Source: `tests/tier1/test_charge_fields.py` (`test_ver29_the_axis_guard_deficit_is_reported_rather_than_assumed`).
- **[tested]** `yaml.safe_dump` writes a NumPy NaN as `.nan`, and NaN passes every `> tol` gate; a NaN `q_net_e` once made three of five conservation legs NaN without any gate catching it. Source: `test_charge_fields.py` (`test_ver29_a_header_value_that_is_not_finite_is_refused`).
- **[tested]** CCP4 is written through gridData's MRC writer (no `CCP4` registry entry) as `float32`, so that round trip is not bit-exact. Source: `test_charge_fields.py` (`test_ver29_a_grid_round_trips_through_opendx_and_ccp4`).
- **[tested]** A charge field continued by its box's edge value over a 250 nm reservoir would make a charge sheet about a thousand times the grid's own footprint, hence zero padding outside the box. Source: `test_charge_fields.py` (`test_ver29_the_interpolant_is_zero_outside_the_grid_box`).


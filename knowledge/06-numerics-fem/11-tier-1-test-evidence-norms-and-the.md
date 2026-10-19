---
type: Test Evidence
title: 'Tier-1 test evidence: norms and the attribution identity (WP45 item 20)'
description: What the Tier-1 tests of norms and the attribution identity establish, recorded at WP45 item
  20.
tags:
- numerics
- test-evidence
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
verified:
- by: process:tests/tier1/test_comparison_norms.py::test_val01_axis_defect_is_invisible_to_the_weighted_norm
  at: '2026-10-14T00:00:00Z'
- by: process:tests/tier1/test_comparison_norms.py::test_val01_pressure_gauge_offset_does_not_register
  at: '2026-10-14T00:00:00Z'
- by: process:tests/tier1/test_comparison_norms.py::test_val01_relative_l2_on_a_known_field
  at: '2026-10-14T00:00:00Z'
---

## Tier-1 test evidence: norms and the attribution identity (WP45 item 20)

- **[tested: tests/tier1/test_comparison_norms.py::test_val01_relative_l2_on_a_known_field]** For `r_i = i h` and a reference `g = 1`, with `s − g = r`: `rel_L2_r² = Σr³/Σr = h² n(n − 1)/2` and `rel_l2² = Σr²/n = h²(n − 1)(2n − 1)/6` (Faulhaber). The constant patch weight and the `z` sum cancel from both ratios. Source: `tests/tier1/test_comparison_norms.py` (`test_val01_relative_l2_on_a_known_field`).
- **[tested: tests/tier1/test_comparison_norms.py::test_val01_axis_defect_is_invisible_to_the_weighted_norm]** On the reference probe grid a defect on the axis (1 610 of 6 205 points, all within 0.045 nm of the axis) gives `sqrt(1610/6205) = 0.51` in the unweighted norm and about 4 × 10⁻⁴ in the `r`-weighted norm, because those points carry a weight of `0.001 nm² · r` against `6 nm² · r` out to 60 nm. Source: `test_comparison_norms.py` (`test_val01_axis_defect_is_invisible_to_the_weighted_norm`).
- **[tested: tests/tier1/test_comparison_norms.py::test_val01_pressure_gauge_offset_does_not_register]** A constant offset of 1 000 Pa in `p` against a 10 Pa physical pressure is a 100-fold raw "discrepancy" that is not one; the gauge-free comparison removes it, and `φ` is not gauge-shifted. Source: `test_comparison_norms.py` (`test_val01_pressure_gauge_offset_does_not_register`).
- The ladder's five deltas telescope to `Δ_resid` identically, for any four rung errors, so the telescoping identity alone cannot detect rungs measured against different goldens; the hash check is what does. Source: `tests/tier1/test_attribution.py` (`test_val01_the_identity_cannot_see_a_stale_golden`).


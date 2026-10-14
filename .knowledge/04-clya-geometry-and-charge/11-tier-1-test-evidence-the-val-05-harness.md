---
type: Test Evidence
title: 'Tier-1 test evidence: the VAL-05 harness and its closed forms (WP45 item 24)'
---

## Tier-1 test evidence: the VAL-05 harness and its closed forms (WP45 item 24)

- **[verified]** A uniform radial scale `r → (1 + s) r` maps each innermost crossing to `(1 + s)` times itself, so `Δ/r = s` on every plane, the first-order sum `ε_G = 2s` is exact, and the exact series ratio is `(1 + s)² − 1`. A 6 % wider lumen is therefore `ε_G = 12 %`, over the 10 % of 2WCD and the 5 % of the ensemble. Source: `tests/tier1/test_val05_geometry.py`.
- **[tested]** A 0.2 nm notch of four planes moves `r_c` by 0.15 nm and barely moves `ε_G` or the rms: the constriction tolerance is the measure that sees a local notch. Source: `tests/tier1/test_val05_geometry.py` (`test_val05_the_constriction_tolerance_fires_naming_both_minima`).
- **[tested]** The reference's z extent of 29.5 h rounds to 30 planes; the mid-planes sit 0.025 nm off each 0.3 nm vertex (`0.3 × (1 − 0.025/0.5)`). The crossing test is half-open, so the plane on the top tip is never crossed and is dropped, or the reference would be refused against itself. Source: `tests/tier1/test_val05_geometry.py` (`test_val05_no_plane_sits_on_a_reference_tip`).
- **[tested]** The constriction window's `Δr_c` is the difference of two minima at different z, not a difference at one plane. Source: `tests/tier1/test_val05_geometry.py`.


---
type: Test Evidence
title: 'Tier-3 test evidence: the charged-tube sweep, the table''s margin and the
  ClyA-AS prediction (WP45 item 27)'
description: What the Tier-3 tests of the charged-tube sweep, the table's margin and
  the ClyA-AS prediction establish, recorded at WP45 item 27.
tags:
- clya
- test-evidence
sources:
- id: wp31-plan
  resource: docs/plans/wp31-gui-charge-pipeline.md
  title: WP31 GUI charge pipeline plan, Outcomes
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
verified:
- by: process:arithmetic
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_reproduce_diagnostics.py::test_charged_tube_fixture_defaults_and_gaussian_peak_shift
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier3/test_reference_charge_map.py::test_val15_the_delivered_table_is_not_truncated
  at: '2026-10-14T00:00:00Z'
---

## Tier-3 test evidence: the charged-tube sweep, the table's margin and the ClyA-AS prediction (WP45 item 27)

- **[verified][^wp31-plan]** The deployed charged-tube field's worst-plane error against the 1e-3 quadrature gate of PHY-19 is 5.7 × 10⁻³ of `Q_net` at `size_scale` 20, 1.9 × 10⁻³ at 10 and 1.2 × 10⁻⁴ at 5, which is why the charged-tube fixture uses 5 **[tested: tests/tier1/test_reproduce_diagnostics.py::test_charged_tube_fixture_defaults_and_gaussian_peak_shift]**. Source: `tests/conftest.py` (`write_charged_tube`); `docs/plans/wp31-gui-charge-pipeline.md`, Outcomes.
- **[tested: tests/tier3/test_reference_charge_map.py::test_val15_the_delivered_table_is_not_truncated]** The reference charge table's boundary ring lies 24 orders of magnitude below its interior maximum, so nothing is lost to the interpolant's zero padding, and the 1.25 % consumer leg of §3.2 is not a truncation effect. Source: `tests/tier3/test_reference_charge_map.py` (`test_val15_the_delivered_table_is_not_truncated`).
- **Prediction, not a measurement:** before the ClyA-AS ensemble was run, the WP22 plan's Design §7 predicted `ε_G` ≈ −4.5 %, `Δr_c` = −0.040 nm and rms ≈ 0.09 nm, a pass narrowly on `ε_G`. The earlier measured `ε_G` of −5.56 % (§1.5) is outside the 5 % tolerance. Source: `tests/tier3/test_val05_ensemble.py` (module docstring at `3782c43`, before WP45); `docs/plans/wp22-val05-reference-geometry.md`, Design §7.
- **[tested: tests/tier1/test_reproduce_diagnostics.py::test_charged_tube_fixture_defaults_and_gaussian_peak_shift]** The charged tube's two atoms sit 0.75 Å in Gaussian width (`w` = 0.075 nm), so an areal peak lies `w²/2r` < 0.001 nm off its atom at `r` ≥ 3.25 nm. Source: `tests/conftest.py` (`CHARGED_TUBE_ATOMS`).

[^wp31-plan]: `docs/plans/wp31-gui-charge-pipeline.md`, Outcomes (2 October 2026).

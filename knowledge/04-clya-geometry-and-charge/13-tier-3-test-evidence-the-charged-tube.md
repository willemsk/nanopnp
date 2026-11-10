---
type: Test Evidence
title: 'Tier-3 test evidence: the charged-tube sweep and the table''s margin'
description: What the Tier-3 tests of the charged-tube sweep and the reference charge table's margin establish.
tags:
- clya
- test-evidence
sources:
- id: wp31-plan
  resource: docs/plans/phase-3/wp31-gui-charge-pipeline.md
  title: WP31 GUI charge pipeline plan, Outcomes
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
verified:
- by: process:arithmetic
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier3/test_reference_charge_map.py::test_val15_the_delivered_table_is_not_truncated
  at: '2026-10-14T00:00:00Z'
---

## Tier-3 test evidence: the charged-tube sweep and the table's margin

- **[verified][^wp31-plan]** The deployed charged-tube field's worst-plane error against the 1e-3 quadrature gate of PHY-19 is 5.7 × 10⁻³ of `Q_net` at `size_scale` 20, 1.9 × 10⁻³ at 10 and 1.2 × 10⁻⁴ at 5, which is why the charged-tube fixture uses 5. Source: `src/nanopnp/validation/charged_tube.py` (`write_charged_tube`); `docs/plans/phase-3/wp31-gui-charge-pipeline.md`, Outcomes.
- **[tested: tests/tier3/test_reference_charge_map.py::test_val15_the_delivered_table_is_not_truncated]** The reference charge table's boundary ring is 8.5 × 10⁻²⁴ of its interior maximum (asserted below 10⁻²⁰), so nothing is lost to the interpolant's zero padding, and the 1.25 % consumer leg of §3.2 is not a truncation effect. Source: `tests/tier3/test_reference_charge_map.py` (`test_val15_the_delivered_table_is_not_truncated`).
- **[verified][^tube-atoms]** The charged tube's two atoms sit 0.75 Å in Gaussian width (`w` = 0.075 nm), so an areal peak lies `w²/2r` < 0.001 nm off its atom at `r` ≥ 3.25 nm. Source: `src/nanopnp/validation/charged_tube.py` (`CHARGED_TUBE_ATOMS`).

[^wp31-plan]: `docs/plans/phase-3/wp31-gui-charge-pipeline.md`, Outcomes (2 October 2026).
[^tube-atoms]: `src/nanopnp/validation/charged_tube.py`, `CHARGED_TUBE_ATOMS` (the two atoms at 3.25 nm and 4.75 nm from the axis), with the offset by arithmetic: 0.075² / (2 × 3.25) = 8.7 × 10⁻⁴ nm.

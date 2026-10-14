---
type: Test Evidence
title: 'Tier-1 test evidence: the Langevin cutoff (WP45 item 21)'
description: What the Tier-1 tests of the Langevin cutoff establish, recorded at WP45 item 21.
tags:
- numerics
- test-evidence
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
verified:
- by: process:tests/tier1/test_electrolyte.py::test_langevin_is_accurate_across_the_series_cutoff
  at: '2026-10-14T00:00:00Z'
---

## Tier-1 test evidence: the Langevin cutoff (WP45 item 21)

- **[tested: tests/tier1/test_electrolyte.py::test_langevin_is_accurate_across_the_series_cutoff]** A Langevin series cutoff set too small hands the `coth` branch an argument with no significant digits left: at `x` = 1e-8 the `coth(x) - 1/x` form returned exactly zero, where the limit is `x/3`. The cutoff at `x = 3e-4` (`knowledge/01-physics-epnpns/index.md`) keeps both branches clear of that cancellation. Source: `tests/tier1/test_electrolyte.py` (`test_langevin_is_accurate_across_the_series_cutoff`).


---
type: Test Evidence
title: 'Tier-1 test evidence: the Langevin cutoff (WP45 item 21)'
---

## Tier-1 test evidence: the Langevin cutoff (WP45 item 21)

- **[tested]** A Langevin series cutoff set too small hands the `coth` branch an argument with no significant digits left: at `x` = 1e-8 the `coth(x) - 1/x` form returned exactly zero, where the limit is `x/3`. The cutoff at `x = 3e-4` (`.knowledge/01-physics-epnpns/index.md`) keeps both branches clear of that cancellation. Source: `tests/tier1/test_electrolyte.py` (`test_langevin_is_accurate_across_the_series_cutoff`).


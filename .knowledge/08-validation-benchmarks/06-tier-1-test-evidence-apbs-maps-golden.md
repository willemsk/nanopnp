---
type: Test Evidence
title: 'Tier-1 test evidence: APBS maps, golden archives and the density cap (WP45
  item 20)'
---

## Tier-1 test evidence: APBS maps, golden archives and the density cap (WP45 item 20)

- **[tested]** An interface a quarter of the way along a `z` edge, between `ε = 2` below and `ε = 80` above, gives the exact harmonic mean `h / (h/4 / 2 + 3h/4 / 80)`; the eight-sample raster mean is exact there because the edge lies on a cell face. Source: `tests/tier1/test_apbs_maps.py` (`test_val06_each_z_edge_takes_the_exact_harmonic_mean_of_a_layered_dielectric`).
- **[tested]** The `%.17g` writer round-trips `float64` exactly, so a `%Grid` table re-ingested from its own text reproduces its array bit for bit. Source: `tests/tier1/test_comsol_golden.py` (`test_val03_grid_table_round_trips_through_npz`).
- **[tested]** The published density cap is quoted to three figures (1.19 × 10³ against the fit's 1193.6), so the caps test's tolerance follows the published precision, not the fit's. Source: `tests/tier1/test_corrections.py` (`test_parameter_file_mobilities_and_caps_agree_with_the_evaluated_model`).


---
type: Test Evidence
title: 'Tier-1 test evidence: the domain indicator and the quality measures (WP45 item 22)'
description: What the Tier-1 tests of the domain indicator and the quality measures establish, recorded
  at WP45 item 22.
tags:
- numerics
- test-evidence
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
verified:
- by: process:tests/tier1/test_indicator.py::test_num24_smoothstep_has_vanishing_slope_at_both_ends
  at: '2026-10-14T00:00:00Z'
- by: process:tests/tier1/test_indicator.py::test_num24_the_indicator_is_built_on_the_fluid_and_that_is_load_bearing
  at: '2026-10-14T00:00:00Z'
- by: process:tests/tier1/test_mesh_quality.py::test_ver10_gamma_is_blind_to_inversion_and_sicn_is_not
  at: '2026-10-14T00:00:00Z'
---

## Tier-1 test evidence: the domain indicator and the quality measures (WP45 item 22)

- **[tested: tests/tier1/test_indicator.py::test_num24_the_indicator_is_built_on_the_fluid_and_that_is_load_bearing]** On the VER-11 configuration, interpolating the indicator `psi` over the whole mesh, rather than over the fluid alone, leaks it onto an electrode where it must be zero, and costs a factor of 170 in the agreement of the two current routes. The default therefore restricts `psi` to the fluid. Source: `tests/tier1/test_indicator.py` (`test_num24_the_indicator_is_built_on_the_fluid_and_that_is_load_bearing`).
- **[tested: pending]** On the deliberately coarse indicator mesh, the interpolated step leaks a fraction of a per cent past its band; the test checks orientation, not precision. Source: `tests/tier1/test_indicator.py` (`test_num24_the_indicator_is_one_on_cis_and_zero_on_trans`).
- **[tested: tests/tier1/test_indicator.py::test_num24_smoothstep_has_vanishing_slope_at_both_ends]** The C1 smoothstep `S` has maximum slope 3/2 per unit of its scaled coordinate, so `dS/dz` peaks at `1.5 / width`. Source: `tests/tier1/test_indicator.py` (`test_num24_smoothstep_has_vanishing_slope_at_both_ends`).
- **[tested: tests/tier1/test_mesh_quality.py::test_ver10_gamma_is_blind_to_inversion_and_sicn_is_not]** `gamma` is blind to inversion and SICN is not: a clockwise equilateral triangle scores `gamma` +1 and is caught only by SICN. Source: `tests/tier1/test_mesh_quality.py` (`test_ver10_gamma_is_blind_to_inversion_and_sicn_is_not`).


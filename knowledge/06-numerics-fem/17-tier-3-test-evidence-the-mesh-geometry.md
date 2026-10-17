---
type: Test Evidence
title: 'Tier-3 test evidence: the mesh geometry digest (WP45 item 27)'
description: What the Tier-3 tests of the mesh geometry digest establish, recorded
  at WP45 item 27.
tags:
- numerics
- test-evidence
sources:
- id: conftest-3782c43
  resource: git:3782c43:tests/conftest.py
  title: tests/conftest.py clya_reference_mesh comment and WP33 Outcomes at 3782c43
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
verified:
- by: process:arithmetic
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_reproduce_diagnostics.py::test_conftest_seed_and_stability_invariants
  at: '2026-10-16T00:00:00Z'
---

## Tier-3 test evidence: the mesh geometry digest (WP45 item 27)

- **[verified][^conftest-3782c43]** NGSolve's pickle round-trips a mesh's vertices to the bit, whereas its `.vol` text moves them by up to 5.6 × 10⁻¹⁷ nm, which changes the mesh's geometry digest. Hence the session's reference mesh is pickled **[tested: tests/tier1/test_reproduce_diagnostics.py::test_conftest_seed_and_stability_invariants]**. Source: `tests/conftest.py` (`clya_reference_mesh`); WP33 Outcomes.
- **[tested: tests/tier1/test_reproduce_diagnostics.py::test_conftest_seed_and_stability_invariants]** A difference of two routes amplifies round-off by the inverse of its size, so the VER-62 number-stability golden leaves `route_agreement` out and holds the routes' own scalars. Source: `tests/conftest.py` (`STABILITY_QUANTITIES`).
- **[tested: tests/tier1/test_reproduce_diagnostics.py::test_conftest_seed_and_stability_invariants]** The seeded stages 1 to 3 key on the structure's source, point group and density settings alone: a case that differs in any of them misses the seed and computes its own. Source: `tests/conftest.py` (`SEED_CASE`).

[^conftest-3782c43]: `git show 3782c43:tests/conftest.py`, `clya_reference_mesh` comment (WP33 Outcomes).

---
type: Test Evidence
title: 'Tier-3 test evidence: the mesh geometry digest (WP45 item 27)'
---

## Tier-3 test evidence: the mesh geometry digest (WP45 item 27)

- **[tested]** NGSolve's pickle round-trips a mesh's vertices to the bit, whereas its `.vol` text moves them by up to 5.6 × 10⁻¹⁷ nm, which changes the mesh's geometry digest. Hence the session's reference mesh is pickled. Source: `tests/conftest.py` (`clya_reference_mesh`); WP33 Outcomes.
- **[verified]** A difference of two routes amplifies round-off by the inverse of its size, so the VER-62 number-stability golden leaves `route_agreement` out and holds the routes' own scalars. Source: `tests/conftest.py` (`STABILITY_QUANTITIES`).
- **[verified]** The seeded stages 1 to 3 key on the structure's source, point group and density settings alone: a case that differs in any of them misses the seed and computes its own. Source: `tests/conftest.py` (`SEED_CASE`).

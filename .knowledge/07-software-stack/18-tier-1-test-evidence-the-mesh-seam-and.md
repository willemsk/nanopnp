---
type: Test Evidence
title: 'Tier-1 test evidence: the mesh seam and the layering ratchet (WP45 item 22)'
---

## Tier-1 test evidence: the mesh seam and the layering ratchet (WP45 item 22)

- **[tested]** meshio writes a whole cell block under the first geometrical tag it carries, so boundary groups packed into one block all read back under the first group's name, with no error raised. Source: `tests/tier1/test_mesh_adapter.py` (`test_if06_a_tagged_mesh_survives_an_msh41_round_trip`).
- **[verified]** Each module into which `io/case.py` was split measures at most 1,266 lines (WP38 D14). Source: `tests/tier1/test_layering.py` (`test_mod13_no_module_of_the_io_split_exceeds_the_bound`).


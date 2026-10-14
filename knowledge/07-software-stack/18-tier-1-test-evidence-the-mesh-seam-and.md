---
type: Test Evidence
title: 'Tier-1 test evidence: the mesh seam and the layering ratchet (WP45 item 22)'
description: What the Tier-1 tests of the mesh seam and the layering ratchet establish, recorded at WP45
  item 22.
tags:
- software
- test-evidence
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
verified:
- by: process:tests/tier1/test_layering.py::test_mod13_no_module_of_the_io_split_exceeds_the_bound
  at: '2026-10-14T00:00:00Z'
- by: process:tests/tier1/test_mesh_adapter.py::test_if06_a_tagged_mesh_survives_an_msh41_round_trip
  at: '2026-10-14T00:00:00Z'
---

## Tier-1 test evidence: the mesh seam and the layering ratchet (WP45 item 22)

- **[tested: tests/tier1/test_mesh_adapter.py::test_if06_a_tagged_mesh_survives_an_msh41_round_trip]** meshio writes a whole cell block under the first geometrical tag it carries, so boundary groups packed into one block all read back under the first group's name, with no error raised. Source: `tests/tier1/test_mesh_adapter.py` (`test_if06_a_tagged_mesh_survives_an_msh41_round_trip`).
- **[tested: tests/tier1/test_layering.py::test_mod13_no_module_of_the_io_split_exceeds_the_bound]** Each module into which `io/case.py` was split measures at most 1,266 lines (WP38 D14). Source: `tests/tier1/test_layering.py` (`test_mod13_no_module_of_the_io_split_exceeds_the_bound`).


---
type: Test Evidence
title: 'Tier-1 test evidence: the mesh seam and the layering ratchet'
description: What the Tier-1 tests of the mesh seam and the layering ratchet establish.
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

## Tier-1 test evidence: the mesh seam and the layering ratchet

- **[tested: tests/tier1/test_mesh_adapter.py::test_if06_a_tagged_mesh_survives_an_msh41_round_trip]** A tagged mesh survives the MSH 4.1 round trip with one cell block per group; why one block per group is needed is meshio's writer behaviour in `04-geometry-meshing-and-io.md`.
- **[tested: tests/tier1/test_layering.py::test_mod13_no_module_of_the_io_split_exceeds_the_bound]** Each module into which `io/case.py` was split measures at most 1,266 lines (WP38 D14).


---
type: Test Evidence
title: 'Tier-2 test evidence: budgets, timings and reference checks (WP45 item 25)'
description: What the Tier-2 tests of budgets, timings and reference checks establish,
  recorded at WP45 item 25.
tags:
- software
- test-evidence
sources:
- id: example05-3782c43
  resource: git:3782c43:tests/tier2/test_examples_05_clya_reference.py
  title: tests/tier2/test_examples_05_clya_reference.py module docstring at 3782c43
    (WP16 D11 Outcome)
- id: example07-3782c43
  resource: git:3782c43:tests/tier2/test_examples_07_pdb_to_charged_run.py
  title: tests/tier2/test_examples_07_pdb_to_charged_run.py module docstring at 3782c43
    (WP32 D9)
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
verified:
- by: process:arithmetic
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_density_2wcd.py::test_ver49_2wcd_budget
  at: '2026-10-14T00:00:00Z'
- by: process:tests/tier2/test_examples_05_clya_reference.py::test_ver46_the_frozen_case_solves_on_the_reference_mesh
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_examples_06_pdb_to_mesh.py::test_ver46_06_the_exported_map_overlays_the_aligned_structure
  at: '2026-10-14T00:00:00Z'
- by: process:tests/tier2/test_examples_07_pdb_to_charged_run.py::test_ver46_07_the_prepared_entry_walks_every_stage_to_a_charged_solve
  at: '2026-10-16T00:00:00Z'
---

## Tier-2 test evidence: budgets, timings and reference checks (WP45 item 25)

- **[tested: tests/tier2/test_density_2wcd.py::test_ver49_2wcd_budget]** The WP19/WP20 plan predicted stages 2 and 3 on the 2WCD structure at 0.05 nm to take at most 60 s and under 1.5 GB peak RSS (plan, Design §5). The budget test records the wall clock and `ru_maxrss` (kB on Linux) in a fresh interpreter and never gates on them. Source: `tests/tier2/test_density_2wcd.py` (`test_ver49_2wcd_budget`).
- **[verified][^example05-3782c43]** Example 05's frozen solve on the ClyA reference mesh took 2,512 s on one core (WP16 D11 Outcome); its Tier-2 wrapper is `slow` and records rather than gates, and the budget assumes about twice that **[tested: tests/tier2/test_examples_05_clya_reference.py::test_ver46_the_frozen_case_solves_on_the_reference_mesh]**. Source: `tests/tier2/test_examples_05_clya_reference.py`.
- **[tested: tests/tier2/test_examples_06_pdb_to_mesh.py::test_ver46_06_the_exported_map_overlays_the_aligned_structure]** A PDB coordinate column is written to 0.001 Å, so a written atom lies at most half of that from the true one; the map bound of example 06 therefore allows `√3` times that rounding. For a single Gaussian frame the map at distance `d` from an atom is at least `exp(−d²/(σR)²)`; the grid node nearest the written atom lies within `√3h/2` of it. `R` is the smallest shipped radius of any heavy atom, which gives 0.928 at `h = 0.05 nm` (WP25 plan, Design §2), so a map in nm or with transposed axes fails. Source: `tests/tier2/test_examples_06_pdb_to_mesh.py` (`test_ver46_06_the_exported_map_overlays_the_aligned_structure`).
- **[tested: tests/tier2/test_examples_06_pdb_to_mesh.py::test_ver46_06_the_exported_map_overlays_the_aligned_structure]** A residue table names some hydrogens without a leading `H` (NAD's `NH2T`), so a radius looked up by name filtered on `H` takes a hydrogen's radius and makes a bound vacuous; the lookup goes through the set's own table. Source: `test_examples_06_pdb_to_mesh.py` (comment at the bound).
- **[verified][^example07-3782c43]** Example 07's ePNP-NS solve at `size_scale` 4 (chosen for runtime) takes a few minutes on one core (WP32 D9) **[tested: tests/tier2/test_examples_07_pdb_to_charged_run.py::test_ver46_07_the_prepared_entry_walks_every_stage_to_a_charged_solve]**. Source: `tests/tier2/test_examples_07_pdb_to_charged_run.py`.

[^example05-3782c43]: `git show 3782c43:tests/tier2/test_examples_05_clya_reference.py`, module docstring (WP16 D11 Outcome).
[^example07-3782c43]: `git show 3782c43:tests/tier2/test_examples_07_pdb_to_charged_run.py`, module docstring (WP32 D9).

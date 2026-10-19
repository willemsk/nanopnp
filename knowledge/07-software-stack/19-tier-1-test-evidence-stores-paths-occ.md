---
type: Test Evidence
title: 'Tier-1 test evidence: stores, paths, OCC names, NaN and reduction tolerances
  (WP45 item 23)'
description: What the Tier-1 tests of stores, paths, OCC names, NaN and reduction
  tolerances establish, recorded at WP45 item 23.
tags:
- software
- test-evidence
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
verified:
- by: process:tests/tier1/test_nan_gates.py::test_ver70_a_nan_permissive_gate_is_found_at_its_line
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_primitives.py::test_name_edges_leaves_an_already_named_edge_alone
  at: '2026-10-14T00:00:00Z'
- by: process:tests/tier1/test_reduction.py::test_ver50_cos_modulation
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_reduction.py::test_ver50_off_axis_gaussian_closed_forms
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_run.py::test_ver32_a_run_removes_its_scratch_once_the_store_holds_the_payloads
  at: '2026-10-14T00:00:00Z'
---

## Tier-1 test evidence: stores, paths, OCC names, NaN and reduction tolerances (WP45 item 23)

- **[tested: tests/tier1/test_run.py::test_ver32_a_run_removes_its_scratch_once_the_store_holds_the_payloads]** `Store.put` copies every payload, so a run's scratch workspace would hold a second copy of each. The driver removes the scratch it made once the store holds the payloads and leaves a caller-named workspace alone. Source: `tests/tier1/test_run.py` (`test_ver32_a_run_removes_its_scratch_once_the_store_holds_the_payloads`).
- `repr` doubles every backslash, so a message that quotes a Windows path with `repr` names `C:\\Users\\...` where the file is `C:\Users\...`. A POSIX backslash is a legal file-name character, so a diagnostic check must drive a separator on either platform. Source: `tests/tier1/test_reproduce_diagnostics.py`.
- **[tested: tests/tier1/test_primitives.py::test_name_edges_leaves_an_already_named_edge_alone]** A boolean result of OCC is a compound and refuses a `name` query, so an edge's name is read off its one face. Source: `tests/tier1/test_primitives.py` (`test_name_edges_leaves_an_already_named_edge_alone`).
- **[tested: tests/tier1/test_nan_gates.py::test_ver70_a_nan_permissive_gate_is_found_at_its_line]** Every ordering comparison with NaN is false, so `if value > tol: raise` is skipped by a NaN; the house form `if not value <= tol: raise` fails it. Source: `tests/tier1/test_nan_gates.py`.
- The sub-agent frontmatter keys that code.claude.com documented on 12 October 2026 are the set that the files of `.claude/agents/` were written against; the test that checked them, `test_plan_shape.py`, was deleted by the test scope (WP50, §8.2.13 N3).
- **[tested: tests/tier1/test_reduction.py::test_ver50_off_axis_gaussian_closed_forms]** The VER-50 tolerances rest on values the WP19 plan recorded when it was written: the off-axis Gaussian's Cn variance is 1.2 × 10⁻⁵ (limit 3 × 10⁻⁵) and its raw variance 3.2 × 10⁻⁴ (limit 10⁻³), with the Cn variance 0.8 % of its peak; the `cos(mθ)` mean is 2.5 × 10⁻⁴ of its peak **[tested: tests/tier1/test_reduction.py::test_ver50_cos_modulation]**. Source: `tests/tier1/test_reduction.py` (`test_ver50_off_axis_gaussian_closed_forms`, `test_ver50_cos_modulation`).


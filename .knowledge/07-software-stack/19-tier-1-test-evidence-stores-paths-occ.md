---
type: Test Evidence
title: 'Tier-1 test evidence: stores, paths, OCC names, NaN and reduction tolerances
  (WP45 item 23)'
---

## Tier-1 test evidence: stores, paths, OCC names, NaN and reduction tolerances (WP45 item 23)

- **[tested]** `Store.put` copies every payload, so a run's scratch workspace would hold a second copy of each. The driver removes the scratch it made once the store holds the payloads and leaves a caller-named workspace alone. Source: `tests/tier1/test_run.py` (`test_ver32_a_run_removes_its_scratch_once_the_store_holds_the_payloads`).
- **[verified]** `repr` doubles every backslash, so a message that quotes a Windows path with `repr` names `C:\\Users\\...` where the file is `C:\Users\...`. A POSIX backslash is a legal file-name character, so a diagnostic check must drive a separator on either platform. Source: `tests/tier1/test_reproduce_diagnostics.py`.
- **[verified]** A boolean result of OCC is a compound and refuses a `name` query, so an edge's name is read off its one face. Source: `tests/tier1/test_primitives.py` (`test_name_edges_leaves_an_already_named_edge_alone`).
- **[verified]** Every ordering comparison with NaN is false, so `if value > tol: raise` is skipped by a NaN; the house form `if not value <= tol: raise` fails it. Source: `tests/tier1/test_nan_gates.py`.
- **[verified]** The sub-agent frontmatter keys that code.claude.com documented on 12 October 2026 are the set that `tests/tier1/test_plan_shape.py` checks.
- **[tested]** The VER-50 tolerances rest on values the WP19 plan recorded when it was written: the off-axis Gaussian's Cn variance is 1.2 × 10⁻⁵ (limit 3 × 10⁻⁵) and its raw variance 3.2 × 10⁻⁴ (limit 10⁻³), with the Cn variance 0.8 % of its peak; the `cos(mθ)` mean is 2.5 × 10⁻⁴ of its peak. Source: `tests/tier1/test_reduction.py` (`test_ver50_off_axis_gaussian_closed_forms`, `test_ver50_cos_modulation`).


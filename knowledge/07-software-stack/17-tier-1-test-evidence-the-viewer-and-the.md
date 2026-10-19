---
type: Test Evidence
title: 'Tier-1 test evidence: the viewer and the positivity gate (WP45 item 21)'
description: What the Tier-1 tests of the viewer and the positivity gate establish, recorded at WP45 item
  21.
tags:
- software
- test-evidence
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
verified:
- by: process:tests/tier1/test_gates.py::test_ver08_positivity_gate_rejects_exactly_zero
  at: '2026-10-14T00:00:00Z'
---

## Tier-1 test evidence: the viewer and the positivity gate (WP45 item 21)

- **** A webgui scene of the reference mesh is 23 to 39 MB, and it is written twice, once as data and once inside the document. The render child therefore keeps only one field's pair and re-renders the next field, about a second, rather than keeping five. Source: `tests/tier1/test_gui_render.py` (`test_ver44_only_one_fields_scene_is_kept`).
- **[tested: tests/tier1/test_gates.py::test_ver08_positivity_gate_rejects_exactly_zero]** On Linux, `Set` projects element-wise, so a coordinate field set to zero at a wall comes back as about -3e-16, not 0; the positivity gate therefore evaluates the coefficient function, which samples `x = 0` exactly. **[tested: tests/tier1/test_gates.py::test_ver08_positivity_gate_rejects_exactly_zero]** The test's author records the same round-off, of positive sign, on macOS and Windows. Source: `tests/tier1/test_gates.py` (`test_ver08_positivity_gate_rejects_exactly_zero`).


---
type: Test Evidence
title: 'Tier-1 test evidence: the viewer and the positivity gate (WP45 item 21)'
---

## Tier-1 test evidence: the viewer and the positivity gate (WP45 item 21)

- **[tested]** A webgui scene of the reference mesh is 23 to 39 MB, and it is written twice, once as data and once inside the document. The render child therefore keeps only one field's pair and re-renders the next field, about a second, rather than keeping five. Source: `tests/tier1/test_gui_render.py` (`test_ver44_only_one_fields_scene_is_kept`).
- **[tested]** On Linux, `Set` projects element-wise, so a coordinate field set to zero at a wall comes back as about -3e-16, not 0; the positivity gate therefore evaluates the coefficient function, which samples `x = 0` exactly. **[verified]** The test's author records the same round-off, of positive sign, on macOS and Windows. Source: `tests/tier1/test_gates.py` (`test_ver08_positivity_gate_rejects_exactly_zero`).


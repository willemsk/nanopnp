---
type: Background
title: 7. Ionic current rectification
description: "α(V) = G(+V)/G(−V): what makes a pore rectify, ClyA's strong rectification and its concentration dependence."
tags:
- electrokinetics
- background
sources:
- id: thesis
  resource: https://github.com/willemsk/phdthesis-text
  title: Willems, PhD thesis (LaTeX source)
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
---

## 7. Ionic current rectification

`alpha(V_bias) = G(+V_bias)/G(-V_bias)` [`eq:icr`] **[verified][^thesis]**. Requires charged walls **and** an axial asymmetry, the usual source being the geometry (intrinsic, or induced by
gating/electrostriction) **[verified][^thesis]**; an asymmetry of the fixed charge along a geometrically symmetric pore is expected to
rectify too, but no test or source in this knowledge base establishes it. ClyA rectifies strongly (negative interior; cis
~6 nm vs trans ~3.3 nm entries) **[verified][^thesis]**. `alpha` rises monotonically with `|V_bias|`, but versus concentration is
**non-monotonic**, peaking at 0.15 M and decaying to 1 at saturating salt **[verified][^thesis]**. The peak coincides with the
slope change of the negative-bias conductance — evidence of a mechanism change (co-ion exclusion) rather than
geometry (unverified). There is a matching EO rectification `alpha_Q = G_Q(+V)/G_Q(-V)`, passing through 1 near 0.45 M **[verified][^thesis]**.

[^thesis]: Willems, PhD thesis, LaTeX source, `github.com/willemsk/phdthesis-text` at `43d0f0f`; the `.tex` file and label beside each claim locate it.

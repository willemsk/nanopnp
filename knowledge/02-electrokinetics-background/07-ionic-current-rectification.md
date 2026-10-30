---
type: Background
title: 7. Ionic current rectification
description: Ionic current rectification.
tags:
- electrokinetics
- background
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
---

## 7. Ionic current rectification

`alpha(V_bias) = G(+V_bias)/G(-V_bias)` [`eq:icr`]. Requires charged walls **and** an axial asymmetry, the usual source being the geometry (intrinsic, or induced by
gating/electrostriction); an asymmetry of the fixed charge along a geometrically symmetric pore is expected to
rectify too, but no test or source in this knowledge base establishes it (one dry run of the sweep session gave
0.91 at 50 mV). ClyA rectifies strongly (negative interior; cis
~6 nm vs trans ~3.3 nm entries). `alpha` rises monotonically with `|V_bias|`, but versus concentration is
**non-monotonic**, peaking at 0.15 M and decaying to 1 at saturating salt. The peak coincides with the
slope change of the negative-bias conductance — evidence of a mechanism change (co-ion exclusion) rather than
geometry. There is a matching EO rectification `alpha_Q = G_Q(+V)/G_Q(-V)`, passing through 1 near 0.45 M.


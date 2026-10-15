---
type: Orientation
title: Conventions used throughout
description: The notation and the marking of claims used throughout the knowledge base.
tags:
- orientation
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
---

## Conventions used throughout

- Plain-text notation, not LaTeX macros: `phi`, `c_i`, `eps_r`, `nabla`.
- `⟨c⟩` is `(1/n)Σc_i`, not the ionic strength, and `d` is the distance to the nearest pore
  boundary (`.claude/rules/physics-numerics.md`).
- Correction functions take dimensionless `c̄ = ⟨c⟩/(1 M)` and `d̄ = d/(1 nm)`.
- A claim verified by running code is marked `[tested: <test>]`, naming the test, or `[tested: pending]`
  while no test names it; a claim verified by arithmetic or by reading a source is marked `[verified]`
  and cites a source by footnote. Anything unverified says so.

---


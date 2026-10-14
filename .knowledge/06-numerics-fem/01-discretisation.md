---
type: Numerics
title: 1. Discretisation
description: 'The discretisation: elements, spaces and assembly.'
tags:
- numerics
- numerics
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
---

## 1. Discretisation

**Elements.** Continuous Galerkin: `P2` for `φ` and each `c_i`; Taylor–Hood `P2/P1` for `(u, p)`.
Triangles. All measures `r`-weighted (§2).

**Nernst–Planck formulation: primitive concentrations `c_i`,** with a log-variable branch behind a
flag as fallback.

| Form | Positivity | Conditioning at ±200 mV | Verdict |
|---|---|---|---|
| Primitive `c_i` | not guaranteed | good | **default** |
| Slotboom `c_i = c₀e^{−z_iφ̃}ρ_i` | yes | coefficient spread `e^{2φ̃}` ≈ 5.8 × 10⁶ | **reject** |
| Log/entropy `c_i = e^{w_i}` | exact | moderate, needs damping | fallback branch |
| Mixed / HDG | yes | locally conservative | later, if flux conservation demands |

`φ̃ = φF/RT` spans ±7.78 at ±200 mV, which is what kills Slotboom.

---


---
type: Numerics
title: 1. Discretisation
description: 'The discretisation: elements, spaces and assembly.'
tags:
- numerics
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
---

## 1. Discretisation

**Elements.** Continuous Galerkin: `P2` for `φ` and each `c_i`; Taylor–Hood `P2/P1` for `(u, p)`.
Triangles. All measures `r`-weighted (`02-axisymmetric-weak-forms.md`). NUM-01 and NUM-03 state them.

**Nernst–Planck formulation.** Primitive `c_i` by default, a log branch behind a flag, Slotboom
rejected: NUM-02, with its table and the ±7.78 `φ̃` range that rules Slotboom out.

---


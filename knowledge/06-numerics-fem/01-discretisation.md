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
rejected: NUM-02, with its table and the ±7.78 `φ̃` range that rules Slotboom out. The flag is the case key
`numerics.log_variables`, off by default: a switch record of `io/switches.py` that brings no term in force, excludes
PHY-23's switch, and is a deviation in the manifest when on; the NUM-18 ladder refuses it, so a case that sets it runs
with `numerics.continuation: none` (WP6.11) [tested: tests/tier1/test_switches.py]. On example 02's guard walk it
repeats its stored numbers to 4.1e-16 entered by the key (VER-80) [tested: tests/tier2/test_guard_numbers.py].

---


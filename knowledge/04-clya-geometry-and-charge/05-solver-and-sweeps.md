---
type: Pipeline
title: 5. Solver and sweeps
description: The solver and sweep settings of the reference case.
tags:
- clya
- pipeline
sources:
- id: thesis
  resource: https://github.com/willemsk/phdthesis-text
  title: Willems, PhD thesis (LaTeX source)
- id: paper
  resource: https://doi.org/10.1039/D0NR03114C
  title: Willems et al., Nanoscale 12, 16775-16795 (2020)
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
---

## 5. Solver and sweeps

Stated: **COMSOL Multiphysics v5.4** (`epnpns.tex` L234-235). Everything else — PARDISO direct
solver, damped Newton with a lower-bounded variable damping factor — is author correspondence, not
the thesis; see `knowledge/01-physics-epnpns/07-implementation-notes-carried-forward.md`. No tolerances, no continuation/ramping scheme, no initial
guess, and no sweep ordering are recorded.

What the *outputs* imply about the sweep: `c_bulk` spans **0.005 to 5 M** and `V_bias` spans
**-200 to +200 mV** on a grid dense enough for contour plots (T L663-665). Tabulated points are
`c_bulk` in {0.005, 0.05, 0.15, 0.5, 1, 2, 5} M and `V_bias` in {+-50, +-100, +-150} mV (TA
`tab:ion_selectivities`). Experimental comparison used {0.05, 0.15, 0.5, 1, 3} M, +-200 mV, n = 3,
25 +- 1 C. The energy-barrier figure distinguishes **+0 mV from -0 mV** (they diverge for
c_bulk < 0.3 M), i.e. zero was approached from both signs rather than solved once (T L1160-1163).

---


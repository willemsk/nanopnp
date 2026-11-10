---
type: Background
title: 9. Quantities the thesis computes
description: The quantities the thesis computes, and the model each needs; FR-23 and PHY-21 state what nanopnp extracts.
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

## 9. Quantities the thesis computes

What nanopnp extracts, and by which routes, is FR-23's; the selectable models are PHY-21's.

| Quantity | Definition | Model |
|---|---|---|
| `I` | the boundary flux by the variational reaction route and by the ψ-indicator route, cross-checked (FR-23, QR-04); never the cross-section integral of the CG flux (`knowledge/06-numerics-fem/07-quantities-of-interest-and-the-flux-trap.md`) | PNP-NS |
| `G`, per-species `G_i` | `I/V_bias` | PNP-NS |
| `t_Na` | `G_Na/(G_Na+G_Cl)` | PNP-NS |
| `alpha` | `G(+V)/G(-V)` | PNP-NS, both signs |
| `V_rev` | bias where `I = 0` under asymmetric reservoirs | PNP-NS + root find |
| `Q`, `G_Q`, `alpha_Q` | `∫(n·u) dS` [`eq:flowrate`], `Q/V_bias` | NS **[verified][^thesis]** |
| Fields `phi`, `c_i`, `u`, `p` | primary unknowns | PNP-NS |
| `lambda_D`, local `<c>`, EDL charge | diagnostics; also drive the corrections | any |
| On-axis `phi(z)` vs circuit model | access-resistance sanity check | PNP-NS |
| Force on analyte | Maxwell + hydrodynamic stress-tensor surface integrals | PNP-NS |
| `dG_elec` landscape | `G(pore+part) - G(pore) - G(part)` | **PB** |
| Averaged potential maps | radial `phi_r(r,z)`, cylindrical `phi_z(z)` | **PB** |

The last two need PB: the whole electrostatics chapter — selectivity rationalisation, DNA translocation
barriers, pore-engineering guidance — rests on PB alone, at a fraction of the cost of a PNP-NS solve. PB is
a distinct selectable model (PHY-21, PHY-24).

[^thesis]: Willems, PhD thesis, LaTeX source, `github.com/willemsk/phdthesis-text` at `43d0f0f`; the `.tex` file and label beside each claim locate it.

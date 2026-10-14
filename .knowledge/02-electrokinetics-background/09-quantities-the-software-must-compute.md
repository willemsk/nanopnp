---
type: Background
title: 9. Quantities the software must compute
---

## 9. Quantities the software must compute

| Quantity | Definition | Model |
|---|---|---|
| `I` | `∫ F*sum_i z_i*(n·J_i) dS` on a reservoir boundary | PNP-NS |
| `G`, per-species `G_i` | `I/V_bias` | PNP-NS |
| `t_Na` | `G_Na/(G_Na+G_Cl)` | PNP-NS |
| `alpha` | `G(+V)/G(-V)` | PNP-NS, both signs |
| `V_rev` | bias where `I = 0` under asymmetric reservoirs | PNP-NS + root find |
| `Q`, `G_Q`, `alpha_Q` | `∫(n·u) dS` [`eq:flowrate`], `Q/V_bias` | NS |
| Fields `phi`, `c_i`, `u`, `p` | primary unknowns | PNP-NS |
| `lambda_D`, local `<c>`, EDL charge | diagnostics; also drive the corrections | any |
| On-axis `phi(z)` vs circuit model | access-resistance sanity check | PNP-NS |
| Force on analyte | Maxwell + hydrodynamic stress-tensor surface integrals | PNP-NS |
| `dG_elec` landscape | `G(pore+part) - G(pore) - G(part)` | **PB** |
| Averaged potential maps | radial `phi_r(r,z)`, cylindrical `phi_z(z)` | **PB** |

The last two are why PB must be a first-class selectable model: the whole electrostatics chapter — selectivity
rationalisation, DNA translocation barriers, pore-engineering guidance — rests on PB alone, at a fraction of
the cost of a PNP-NS solve.

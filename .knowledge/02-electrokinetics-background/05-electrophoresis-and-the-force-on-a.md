---
type: Background
title: 5. Electrophoresis and the force on a charged body
---

## 5. Electrophoresis and the force on a charged body

| Force | Expression | Label |
|---|---|---|
| Electrophoretic | `F_ep = ∫_V rho*E dV = q*E` | `eq:nanopores_lorentz_force` |
| Dielectrophoretic | `F_dep = (p·grad)E` | `eq:nanopores_dep_force` |
| Electric, exact | `F_ele = ∮_Gamma (T_M·n) dGamma`, `T_M = eps*E*E - 0.5*eps*(E·E)*Id` | `eq:nanopores_electric_force` |
| Drag, 1st order | `F_drag = -6*pi*eta*R_h*u` | `eq:nanopores_drag_force` |
| Hydrodynamic, exact | `F_hyd = ∮_Gamma (T_H·n) dGamma`, `T_H = p*Id - eta*(grad u + grad u^T)` | `eq:nanopores_hydrodynamic_force` |

`q*E` is strictly valid only in a uniform field. The **stress-tensor forms assume nothing about particle shape
or field uniformity and are what to implement**; `T_H` also captures pressure build-up ahead of a
translocating particle, which Stokes drag does not. Typical in-pore EP/EO forces: **1–100 pN** (ClyA at
−50 mV: ~3 mV/nm → ~4 pN on a +10 e protein; a 5 nm sphere in 100 mm/s flow → ~4 pN). Reynolds ~5e-4, always
laminar. EP dominates for DNA; for proteins the balance is even or EO-dominated — which is how ClyA captures
proteins *against* the field.

**Electrophoretic mobility [std]:** `mu_ep = v_drift/E`; `q/(6*pi*eta*R_h)` in the thick-EDL (Hückel) limit,
`eps0*eps_r*zeta/eta` in the thin-EDL (Smoluchowski) limit — the exact negative of `mu_eo`. The thesis computes
forces directly instead. Do not use "effective charge" shortcuts without stating the EOF assumption: for dsDNA
in ClyA, EOF is estimated to halve it from −2 to −1 e/bp.


---
type: Background
title: 1. The electrical double layer
description: "The Bjerrum and Debye lengths, the Gouy-Chapman-Stern layers, surface and zeta potential, the Grahame equation, confinement and the timescale separation."
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

## 1. The electrical double layer

**Bjerrum length** — separation at which Coulomb energy between two elementary charges equals `kB*T`
[`eq:nanopores_bjerrum_length`]: `lambda_B = e^2/(4*pi*eps0*eps_r*kB*T) ≈ 0.7 nm` (water, room T). Comparable
to the radius of many biological pores, so electrostatics is never a perturbation here **[verified][^thesis]**.

**Debye length** — thickness of the diffuse layer and the screening length [`eq:nanopores_debye_length`]:

```
lambda_D = sqrt( eps0*eps_r*kB*T / (e^2*N_A*sum_i c_i0*z_i^2) ) = (8*pi*lambda_B*N_A*I)^(-1/2)
I = 0.5*sum_i c_i0*z_i^2      (ionic strength)
```

`c_i0` bulk molar conc., `z_i` valence **[verified][^thesis]**. `lambda_D ∝ I^(-1/2)`:

| NaCl (M) | 0.01 | 0.05 | 0.1 | 1 | >3 |
|---|---|---|---|---|---|
| `lambda_D` (nm) | 3.1 | 1.4 | 0.97 | 0.31 | <0.2 **[verified][^thesis]** |

The thesis's values **[verified][^thesis]**, at `eps_r ≈ 80`. At `eps_r,f⁰ = 78.15` they are 3.0, 1.36, 0.96 and 0.30 nm **[verified][^arith-debye]**.

**Gouy–Chapman–Stern structure** (the thesis names the layers, not the model,
`fig:nanopores_edl_overview`): a **Stern** layer of semi-permanently bound, partly dehydrated counterions
(thickness `lambda_S ~ 0.1 nm`, one ionic radius — used only in the EDL relaxation time; ePNP-NS has **no
explicit Stern layer**), and a **diffuse (Gouy–Chapman)** layer of mobile excess counterions / depleted
co-ions decaying over ~`lambda_D` **[verified][^thesis]**.

**Surface vs zeta potential [std] (unverified).** `psi_0` is the potential at the wall; `zeta` is the potential at the
hydrodynamic shear plane (~Stern/diffuse boundary) and is what electrokinetic experiments report,
`|zeta| <= |psi_0|`. The thesis never uses `zeta`: solving the full ion distribution on an atomistic charge
map makes zeta an *output* diagnostic. Any zeta the software reports must state its shear-plane convention.

**Grahame equation [std] (unverified)** — converts between fixed-charge and fixed-potential wall specifications (symmetric
z:z salt): `sigma_s = sqrt(8*eps0*eps_r*kB*T*c0*N_A) * sinh(z*e*psi_0/(2*kB*T))`; linearised
`sigma_s = eps0*eps_r*psi_0/lambda_D`.

**Confinement.** In a ~1 nm-radius pore EDLs overlap even at 0.1 M [§`sec:np:edl`], causing concentration
depletion/enrichment, surface conductance, permselectivity and pre-concentration **[verified][^thesis]**. The interior is then not
electroneutral anywhere — the regime where bulk-fitted electrolyte properties are least justified (`knowledge/01-physics-epnpns/04-rationale-worth-preserving.md`) and
where every thin-EDL formula below fails.

**Timescale separation.** EDL relaxation `tau ~ lambda_D*L/D - lambda_D^2/D - lambda_D*lambda_S/D` [`eq:nanopores_relaxation_time`] is 0.1–10 ns
(4.5 ns for L=10 nm, D=2 nm²/ns, `lambda_D`=1 nm) versus 1 µs–1 s analyte dwell times **[verified][^thesis]**. This is the formal
justification for solving ions and water at **steady state** with the analyte fixed [§`sec:np:dynamics`] **[verified][^thesis]**.

[^thesis]: Willems, PhD thesis, LaTeX source, `github.com/willemsk/phdthesis-text` at `43d0f0f`; the `.tex` file and label beside each claim locate it.
[^arith-debye]: Recomputed from `lambda_D = sqrt(eps0*eps_r*kB*T/(2*e^2*N_A*c))` for a 1:1 salt at T = 298.15 K with CODATA constants. At `eps_r` = 78.15 and c = 0.01, 0.05, 0.1, 1 M it gives 3.035, 1.357, 0.960, 0.304 nm, which round to the 3.0, 1.36, 0.96 and 0.30 nm of the note (at `eps_r` = 80: 3.07, 1.37, 0.97, 0.31 nm).

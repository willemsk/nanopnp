---
type: Background
title: 3. PB vs PNP — equilibrium vs non-equilibrium
description: Why Poisson-Boltzmann is a distinct model from PNP at zero bias.
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

## 3. PB vs PNP — equilibrium vs non-equilibrium

PB has no diffusion coefficients and cannot represent flux under bias; PNP(-NS) adds dynamics and PB is its
zero-flux limit. Setting `J_i = 0`, `u = 0` in the NP flux (`knowledge/01-physics-epnpns/02-governing-equations.md#22-size-modified-nernstplanck`, no steric term):

```
D_i*grad(c_i) + z_i*mu_i*c_i*grad(phi) = 0   =>   c_i = c_i0 * exp( -z_i*phi / (D_i/mu_i) )
```

This is Boltzmann **only if** `D_i/mu_i = V_T = kB*T/e = R*T/F = 25.693 mV` (Nernst–Einstein). The thesis
warns Nernst–Einstein holds only at infinite dilution and "should not be used at finite concentrations (even
though it often is)" [text after `eq:nanopores_nernst_planck`] **[verified][^thesis]**.

> **Consequence.** ePNP-NS fits `D_i(c)` and `mu_i(c)` to independent datasets, so `D_i/μ_i` drifts away
> from `V_T`: Na⁺ to 1.67×, Cl⁻ to 1.28× at 3 M (`knowledge/01-physics-epnpns/03-the-corrections.md` §3.0).
> **The equilibrium limit of ePNP-NS is therefore not a Boltzmann distribution**, and the two species do not
> even share an effective thermal voltage. Poisson–Boltzmann is a distinct model with its own `kT/e`, not
> the PNP solver at zero bias (PHY-24).

Practically: PB is solved over the whole domain (protein + membrane included), needs no flux BCs, and takes
only fixed charge, bulk concentration and the permittivity map; it yields potentials and energies. Only
PNP-NS yields current, selectivity and flow.

[^thesis]: Willems, PhD thesis, LaTeX source, `github.com/willemsk/phdthesis-text` at `43d0f0f`; the `.tex` file and label beside each claim locate it.

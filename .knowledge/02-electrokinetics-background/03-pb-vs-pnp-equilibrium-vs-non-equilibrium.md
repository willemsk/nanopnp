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
zero-flux limit. Setting `J_i = 0`, `u = 0` in the NP flux (`.knowledge/01-physics-epnpns/02-governing-equations.md#22-size-modified-nernstplanck`, no steric term):

```
D_i*grad(c_i) + z_i*mu_i*c_i*grad(phi) = 0   =>   c_i = c_i0 * exp( -z_i*phi / (D_i/mu_i) )
```

This is Boltzmann **only if** `D_i/mu_i = V_T = kB*T/e = R*T/F = 25.693 mV` (Nernst–Einstein). The thesis
warns Nernst–Einstein holds only at infinite dilution and "should not be used at finite concentrations (even
though it often is)" [text after `eq:nanopores_nernst_planck`].

> **Consequence, computed from `data/corrections/willems2020_nacl.yaml`:** ePNP-NS fits `D_i(c)` and `mu_i(c)`
> to independent datasets, so their ratio drifts from `V_T`. `D_Na/mu_Na` = 26.2, 31.1, 37.7, 42.8 mV at
> `<c>` = 0.001, 0.15, 1.0, 3.0 M (i.e. up to 1.67×`V_T`); `D_Cl/mu_Cl` = 26.1, 29.1, 31.4, 32.8 mV.
> **The equilibrium limit of ePNP-NS is therefore not a Boltzmann distribution**, and the two species do not
> even share an effective thermal voltage. A "Poisson–Boltzmann" mode is a genuinely different model, not the
> PNP solver at zero bias. Give PB its own `kT/e`, and print `D_i/mu_i` vs `V_T` as a solve-time diagnostic.

Practically: PB is solved over the whole domain (protein + membrane included), needs no flux BCs, and takes
only fixed charge, bulk concentration and the permittivity map; it yields potentials and energies. Only
PNP-NS yields current, selectivity and flow.


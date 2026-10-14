---
type: Domain
title: 5. From energy landscape to rates (no Boltzmann inversion, no Kramers)
description: From an energy landscape to rates, without Boltzmann inversion or Kramers theory.
tags:
- analyte
- domain
sources:
- id: thesis
  resource: https://github.com/willemsk/phdthesis-text
  title: Willems, PhD thesis (LaTeX source)
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
---

## 5. From energy landscape to rates (no Boltzmann inversion, no Kramers)

The PMF is built **forward** (energy → rates), never inverted from a force profile.

1. **Equilibrium landscape:** `E_elec(z) = G_pore+part − G_pore − G_part` (`electrostatics.tex
   eq:electrostatic_energy`), one APBS triple per z.
2. **Tilt by bias** (`trapping.tex eq:external_energy_model`), N_tot = N_body + N_tag + N_eo:
   `E_ext = N_tot·(V_b/14 nm)·(z − 11 nm)` for −3 < z < 11 nm; `0` for z ≥ 11 nm; `N_tot·V_b` for
   z < −3 nm. Total `E_V = E_elec + E_ext`.
3. **Escape rate:** from a Boltzmann kinetic-energy distribution, energy-independent density of
   states Z, step transmission `c(E)=c₀·θ(E−ΔG)` → `k = Z c₀ exp(−ΔG/kT) ≡ k₀ exp(−ΔG/kT)`.
   Arrhenius, **not Kramers** — no friction or curvature prefactor anywhere.
4. **Double barrier:** `1/τ = k = k_eff^cis·exp(−ΔG^cis/kT) + k_eff^trans·exp(−ΔG^trans/kT)`,
   ΔG = ΔG_steric,0 + ΔG_static,0 + N_tag·e·Ψ_tag ∓ (N_net+N_eo)·e·(Δx/L)·V_b (`eq:double_barrier_complex`).
5. **Translocation probability:** `P_trans = k^trans/(k^cis + k^trans)` (`eq:ptrans`).
6. **Dwell-time statistics:** single bound state → exponential, τ = 1/k, Var = τ². Multi-state →
   sum of exponentials whose expectation is the **arithmetic mean of the level lifetimes**
   (`eq:tau_arithmetic_mean`) — hence the experimental τ is a plain mean.


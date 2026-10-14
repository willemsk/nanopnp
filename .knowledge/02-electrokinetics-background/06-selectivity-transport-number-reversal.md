---
type: Background
title: 6. Selectivity, transport number, reversal potential
---

## 6. Selectivity, transport number, reversal potential

`t_Na = P_Na/(P_Na + 1) = G_Na/(G_Na + G_Cl)` [`eq:tna`] — the fraction of current carried by Na⁺;
`P_Na = G_Na/G_Cl` is the permeability ratio. `t > 0.5` cation-selective. Bulk NaCl `t_Na0 = 0.3963`.

Experimentally, `t` comes from the **reversal potential** `V_rev` (the bias at which `I = 0` under a cis/trans
salt gradient), converted via the **Goldman–Hodgkin–Katz** equation. The thesis lists three reasons this is
not the simulated quantity: GHK ignores EOF-carried flux; GHK assumes Nernst–Einstein at all concentrations;
and since selectivity depends on ionic strength, a gradient measurement reports selectivity at an undetermined
intermediate concentration. Example: measured `t_Na = 0.66` for ClyA vs simulated 0.57 at 1 M (cis) and 0.84
at 0.15 M (trans) — the measurement sits near their average. Simulated ClyA-AS is cation-selective up to
~2 M, bottoming at `t_Na = 0.45` at 5 M (still 1.27× bulk), and selectivity is voltage-dependent.


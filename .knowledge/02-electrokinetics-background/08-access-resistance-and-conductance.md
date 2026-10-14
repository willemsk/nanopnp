---
type: Background
title: 8. Access resistance and conductance decomposition
---

## 8. Access resistance and conductance decomposition

`R_total = R_pore + 2*R_access` [§`sec:np:potential`]. Access (a.k.a. convergence/spreading) resistance is the
cost of funnelling current from bulk into the aperture — a property of the reservoir, and it does not vanish
as the pore shortens.

```
R_pore   = 4*L/(pi*sigma*d^2)              R_access = 1/(2*sigma*d)
I        = dV*sigma*(4*L/(pi*d^2) + 1/d)^-1  ==  dV*sigma*2*pi*d_c
d_c      = (1/(2*pi)) * (4*L/(pi*d^2) + 1/d)^-1
```

`sigma` electrolyte conductivity (constant in bulk, **position-dependent in a pore**), `L` length, `d`
diameter. Profiles follow from `dphi/dz = I/(sigma*S(z))` with `S = pi*d^2/4` inside, `pi*z^2` outside
[`eq:nanopores_potential_profile`, `eq:nanopores_efield_profile`]: outside, `phi ∝ 1/z` and `E ∝ 1/z^2` (a
short-ranged but non-zero capture field); inside a uniform cylinder `E` is constant; in a real pore `E`
tracks `1/S(z)`, so a 2× diameter change is a 4× field change. Baseline: d = 3 nm, L = 10 nm, 0.15 M KCl →
G ≈ 1 nS → 100 pA at 0.1 V ≈ 6e8 ions/s.

| Decomposition | Terms |
|---|---|
| Series | `1/G = R_pore + 2*R_access` |
| Per species | `G = G_Na + G_Cl` (gives `t_Na`) |
| Bulk vs surface | bulk-electrolyte + EDL/counterion conduction; ClyA is bulk-dominated above ~0.15 M, counterion-dominated below (co-ions excluded) |
| Per mechanism | migration + diffusion + convection (the three NP flux terms); the convective term is absent from GHK and is not negligible |


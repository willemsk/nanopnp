---
type: Pipeline
title: 6. Validation targets
description: 'The validation targets: transport number, radial potential, conductance, rectification and
  electro-osmosis.'
tags:
- clya
- pipeline
sources:
- id: paper
  resource: https://doi.org/10.1039/D0NR03114C
  title: Willems et al., Nanoscale 12, 16775-16795 (2020)
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
---

## 6. Validation targets

### 6.1 Cation transport number `t_Na = G_Na/(G_Na+G_Cl)` and `P_Na = G_Na/G_Cl` (TA `tab:ion_selectivities`)

| c_bulk [M] | +150 mV | +100 | +50 | -150 | -100 | -50 |
|---|---|---|---|---|---|---|
| 0.005 | 0.996 (235) | 0.997 (313) | 0.998 (410) | 0.998 (500) | 0.998 (535) | 0.998 (542) |
| 0.050 | 0.906 (9.62) | 0.925 (12.3) | 0.941 (16.0) | 0.967 (29.6) | 0.966 (28.2) | 0.962 (25.1) |
| 0.150 | 0.786 (3.68) | 0.805 (4.13) | 0.824 (4.69) | 0.882 (7.51) | 0.874 (6.91) | 0.860 (6.16) |
| 0.500 | 0.642 (1.79) | 0.649 (1.85) | 0.657 (1.91) | 0.687 (2.20) | 0.680 (2.12) | 0.672 (2.05) |
| 1.000 | 0.566 (1.30) | 0.569 (1.32) | 0.572 (1.33) | 0.582 (1.39) | 0.579 (1.38) | 0.577 (1.36) |
| 2.000 | 0.502 (1.00) | 0.503 (1.01) | 0.503 (1.01) | 0.505 (1.02) | 0.505 (1.02) | 0.504 (1.02) |
| 5.000 | 0.445 (0.803) | 0.445 (0.803) | 0.445 (0.803) | 0.445 (0.802) | 0.445 (0.802) | 0.445 (0.802) |

Derived claims: cation-selective (`t_Na > 0.5`) for all voltages up to **c_bulk ~ 2 M**; minimum
**0.445 at 5 M**, still **~1.27x** the bulk NaCl value **0.35** (T L758-764). `t_Na ~ 0.9` requires
0.05 M at +150 mV but only 0.125 M at -150 mV (T L766-768).

### 6.2 Peak radially averaged equilibrium potential, V_bias = 0 (TA `tab:radial_potential`) [mV]

| c_bulk [M] | cis, z ~ 10 nm | lumen, z ~ 5 nm | trans, z ~ 0 nm |
|---|---|---|---|
| 0.005 | -80 | -108 | -144 |
| 0.05 | -34 | -50 | -86 |
| 0.15 | -19 | -29 | -57 |
| 0.5 | -9.3 | -14 | -30 |
| 5 | -1.9 | -1.7 | -4.2 |

Thermal voltage used for kT/e conversions: **25.7 mV** (-86 mV = -3.35 kT/e, checked).

### 6.3 Conductance, rectification, ion populations

| Quantity | Value | Source |
|---|---|---|
| Ionic conductance G | contour data only; no table. G is flat vs V for c > 1 M; log-log G(c) at +150 mV is linear, at -150 mV bi-linear with a knee near 0.15 M | T L662-679 |
| PNP-NS vs ePNP-NS | PNP-NS overestimates G over the whole range, converging to ePNP-NS below 0.01 M | T L683-685 |
| ICR = G(+V)/G(-V) | rises monotonically with abs(V); non-monotonic in c with a **peak at c = 0.15 M**, decaying to 1 at saturation | T L702-708 |
| Pore-average Na+ (rel.) | 0 mV: **34 at 0.005 M -> 4.4 at 0.05 M**; **2.1 at 0.15 M**; 1.14 >= x >= 1 for c >= 1 M | T L866-871 |
| Pore-average Cl- (rel.) | 0 mV: **0.05 at 0.005 M -> 0.31 at 0.05 M**; **0.58 at 0.15 M**; 0.89 <= x <= 1 for c >= 1 M | T L866-871 |
| Voltage sensitivity at 0.15 M | -150 -> +150 mV: Na+ **1.6 -> 2.7** (1.7x), Cl- **0.28 -> 1.06** (3.8x) | T L876-878 |
| Mobile charge in pore | up to ~0.15 M split evenly: **PS ~ +27 e**, **PB ~ +22 e**; at 5 M **PS = +58 e**, **PB ~ 0 e**; PT is **+10 to +15 e** higher at +150 than -150 mV across all c | T L961-969 |
| PS/PB split | wall distance d = 0.5 nm | T L951-955, TA |
| Debye length | ~1.4 nm at 0.05 M; < 0.2 nm at 5 M | T L721, L762 |
| Trans energy barrier | 0.005 -> 0.15 M: **1.8 -> 0.73 kT** at +150 mV; **4.4 -> 1.5 kT** at -150 mV; falls below 1 kT for c > 0.1-0.5 M | T L1243-1245, L1236-1238 |
| Cis anion barrier | 1.7 -> 0.5 kT for 0.005 -> 0.05 M | T L1195-1197 |

### 6.4 Electro-osmosis and pressure

| Quantity | Value | Source |
|---|---|---|
| Water velocity | at -100 mV, 0.5 M: **~0.07 m/s** at the lumen centre, **~0.21 m/s** at the constriction centre | T L1372-1374 |
| Profile shape | parabolic at low c; plug-like above 0.5 M; a **central dimple** in the constriction for c >= 1 M (self-induced pressure gradient at the pore exit) | T L1376-1386 |
| EOF conductance Q/V at -150 mV | **1.85** nm^3 ns^-1 V^-1 at 0.005 M -> **11.3** at 0.5 M (peak) -> **4.00** at 5 M | T L1400-1405 |
| EOF rectification EOR(V)=Q/V(+V) / Q/V(-V) | maximum at **c ~ 0.045 M**; crosses **unity at c ~ 0.45 M**; minimum at ~1 M; -> 1 at 5 M | T L1409-1414 |
| Pressure | osmotic hotspots **5-30 atm** at 0.15 M, 0 mV, peaking at **z = 11 nm** (cis entry), **z = 4.5 nm** (mid-lumen), **z = -1 nm** (constriction); magnitude roughly c-independent up to ~0.5 M | T L1444-1467 |

Cross-check (derived here): `Q(-100 mV, 0.5 M) ~ 1.13 nm^3/ns`; over a constriction of radius 1.65 nm
that is a mean velocity 0.13 m/s, parabolic peak 0.26 m/s, against the stated 0.21 m/s — consistent
to ~25 %, as expected for a partly flattened profile. Treat both as loose targets.

### 6.5 Correction-ablation targets (T `sec:transport:comparison_corrections`)

| Model | Ionic conductance vs full ePNP-NS | Water conductance vs full |
|---|---|---|
| no WDF (`D^w = mu^w = eta^w = 1`) | **+10 %** | **+25 to +50 %** |
| no CDF (`eps^c = D^c = mu^c = eta^c = rho^c = 1`) | **+5 %, +13 %, +29 %, +152 %** at 0.005, 0.05, 0.5, 5 M | -9 % at 0.005 M, +2 % at 1 M, **+82 % between 1 and 5 M** |
| no SMP (`beta = 0`) | within **+-3 %** everywhere | **-10 % at 0.5 M** |

### 6.6 Auxiliary formulas needed to compute the targets

- Simulated current: `I = F * integral_S ( SUM_i z_i * n . J_i ) dS` over the **cis** boundary (`eq:currentsim`).
- Bulk two-resistor reference: `I = (sigma(c) * pi / 4) * (l_cis/d_cis^2 + l_trans/d_trans^2)^-1 * V_bias`
  with `l_cis = 10 nm, d_cis = 6 nm, l_trans = 4 nm, d_trans = 3.3 nm` (`eq:bulk_nanopore_current`). No access resistance.
- Flow rate: `Q = integral_S (n . u) dS` (`eq:flowrate`).
- Radial average: `<phi>(z) = (1/(pi R(z)^2)) * integral_0^R(z) phi(r,z) 2 pi r dr` (`eq:epnp-ns_radpot`).
- Pore average: `<X>_a = II beta_a X dr dz / II beta_a dr dz` (`eq:pore_surface_integral`) — see gap G6.
- B-factor: `B_i = (8/3) pi^2 MSD_i`, last 10 ns, QCP via MDAnalysis (`eq:bfactor`).

---


---
type: Domain
title: 2. Charge representation — both forms, and where each is used
description: The analyte's charge representation, in both forms and where each is used.
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

## 2. Charge representation — both forms, and where each is used

**(a) Analyte, ACS Nano 2019 — discrete per-bead point charges, B-spline discretised.** Each bead
carries the net charge of the residues it represents; PDB2PQR assigns CHARMM36 radii/charges at
pH 7.5, and APBS spreads charge onto its grid with cubic B-splines (`chgm spl2`, `srfm spl2`).
Body beads: **Q_i = N_body/7** each. Tag beads: **δ_i = −3 … +3 e**.

> **Internal inconsistency.** `fig:trapping_apbs_model` and `§methods` give Q_i = **−1.43 e**
> (7 × −1.43 = −10 e = N_body of DHFR-4S); the running text gives Q_i = **−1.7143 e**
> (7 × = −12 e = N_body of the -I/-C/-O1 variants). Both are self-consistent for *different*
> variants. Implement as `Q_i = N_body / 7`.

**(b) Pore, ePNP-NS ch. 6 — Gaussian-smeared charge, "surface" then volumetric.** `transport.tex
eq:scdpore`. Written as a 2-D areal density in the (r,z) half-plane:

```
σ_pore(r,z) = Σ_i [ e·δ_i / (π (s·R_i)²) ] · exp( −[(r−r_i)² + (z−z_i)²] / (s·R_i)² )
```

with sharpness `s = 0.5`, R_i the CHARMM36 atom radius, r_i = sqrt(x_i²+y_i²), each atom
pre-weighted by the azimuthal factor δ_i/(2π r_i), grid spacing **0.005 nm**. Then, *inside
COMSOL*, "*the surface charge density σ_pore(r,z) was imported as a 2-D linear interpolation
function and **converted into a pseudo-3-D volumetric charge density by normalization over the
local circumference of each element (2πr)***", "*applied across all computational domains*".
Check: ∫ρ dV = **−72.9 e** vs −72 e atomistic (1.2 % error).

The two forms are therefore **one pipeline at two stages** — areal in (r,z), volumetric after the
1/(2πr) conversion — not two competing models. **No analyte-surface charge density σ_s appears
anywhere in the thesis**; an σ_s option on an analyte boundary is a new modelling choice, default
it off.


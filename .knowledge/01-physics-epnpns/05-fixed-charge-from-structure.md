---
type: Physics
title: 5. Fixed charge from structure
description: How the fixed charge is obtained from the structure.
tags:
- physics
- physics
sources:
- id: paper
  resource: https://doi.org/10.1039/D0NR03114C
  title: Willems et al., Nanoscale 12, 16775-16795 (2020)
- id: esi
  resource: https://www.rsc.org/suppdata/d0/nr/d0nr03114c/d0nr03114c1.pdf
  title: Electronic supplementary information of the paper
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
---

## 5. Fixed charge from structure

From the paper/ESI (see also `knowledge/04-*.md`):

- CHARMM36 partial charges and radii, protonation at **pH 7.5** via PROPKA + PDB2PQR.
- Per-atom Gaussian smearing with **σ_i = 0.5 · R_i** (sharpness factor 0.5 × atomic radius).
- Ensemble of **50 aligned MD frames** from the final 5 ns of a 30 ns run (VMD RMSD alignment).
- Azimuthal contribution `δ_i / (2π r_i)`; gridded at **0.005 nm**; loaded as a linear
  interpolation function `rhoq_pore(r,z)`.
- Axis guard, verbatim COMSOL:
  `scd_pore = if(r < 0.01[nm], 0, e_const * rhoq_pore(r,z) / (2*pi*r))` [C m⁻³].

The density map used for the **geometry** is a separate object: 0.5 Å grid, per-atom Gaussian
using each atom's VdW radius with width factor **σ = 0.93**, radially averaged, pore surface taken
as the **25 % contour**. Do not confuse the two sharpness factors (0.93 for the geometry density,
0.5 for the charge smearing).

---


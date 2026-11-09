---
type: Physics
title: 5. Fixed charge from structure
description: "The reference's fixed-charge construction, which nanopnp does not reproduce, and the geometry density map's separate sharpness factor."
tags:
- physics
sources:
- id: paper
  resource: https://doi.org/10.1039/D0NR03114C
  title: Willems et al., Nanoscale 12, 16775-16795 (2020)
- id: esi
  resource: https://www.rsc.org/suppdata/d0/nr/d0nr03114c/d0nr03114c1.pdf
  title: Electronic supplementary information of the paper
- id: thesis
  resource: https://github.com/willemsk/phdthesis-text
  title: Willems, PhD thesis (LaTeX source)
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
---

## 5. Fixed charge from structure

**As the reference ran it** (thesis `transport.tex`:398-429). nanopnp does not reproduce steps 4 and
5: it smears each charge in 3D and takes the closed-form azimuthal mean (PHY-16, PHY-17); the axis
guard applies only to a supplied areal density (PHY-18). See also
`knowledge/04-clya-geometry-and-charge/index.md`.

1. CHARMM36 partial charges and radii, protonation at **pH 7.5** via PROPKA + PDB2PQR.
2. Ensemble of **50 aligned MD frames** from the final 5 ns of a 30 ns run (VMD RMSD alignment).
3. Per-atom Gaussian with width **σ · R_i, σ = 0.5** (sharpness factor 0.5 × atomic radius).
4. Each atom's charge is a normalised 2D Gaussian taken directly in (r, z) about `(r_i, z_i)`
   (`eq:scdpore`), an areal density in C m⁻², gridded at **0.005 nm** and loaded as a linear
   interpolation function `rhoq_pore(r,z)`.
5. The areal density becomes a volume density once, by the `1/(2πr)` at the field point, with the
   axis guard, verbatim COMSOL:
   `scd_pore = if(r < 0.01[nm], 0, e_const * rhoq_pore(r,z) / (2*pi*r))` [C m⁻³].

Net charge: −72 e atomistic, −72.9 e integrated on the COMSOL mesh (`transport.tex`:424-426;
ruling 8).

The density map used for the **geometry** is a separate object: 0.5 Å grid, per-atom Gaussian
using each atom's VdW radius with width factor **σ = 0.93**, radially averaged, pore surface taken
as the **25 % contour**. Do not confuse the two sharpness factors (0.93 for the geometry density,
0.5 for the charge smearing).

---


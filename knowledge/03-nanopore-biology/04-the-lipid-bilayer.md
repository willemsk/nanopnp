---
type: Domain
title: 4. The lipid bilayer
description: The lipid bilayer in experiments and in the model.
tags:
- biology
- domain
sources:
- id: thesis
  resource: https://github.com/willemsk/phdthesis-text
  title: Willems, PhD thesis (LaTeX source)
- id: paper
  resource: https://doi.org/10.1039/D0NR03114C
  title: Willems et al., Nanoscale 12, 16775-16795 (2020)
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
---

## 4. The lipid bilayer

Experiments and simulations use **DPhPC** (1,2-diphytanoyl-*sn*-glycero-3-phosphocholine), a branched-chain
lipid chosen for stable, low-noise planar bilayers. Modelling parameters:

| Property | Value | Where |
|---|---|---|
| Thickness | **2.8 nm** | ePNP-NS model (`knowledge/01-physics-epnpns/02-governing-equations.md#24-domains-and-boundaries`); consistent with FraC's 3.5 nm TMD helices spanning it |
| Relative permittivity | **3.2** (Gramse 2013) | ePNP-NS |
| — in the APBS work | 2 | electrostatics.tex `tab:pdb2pqr_apbs_parameters` |
| APBS slab thickness | 27 Å, with a conical hole | `draw_membrane2` |

Electrostatically the bilayer is an **uncharged, ion-impermeable, low-permittivity dielectric slab** — very
different from the surrounding `eps_r ≈ 78` electrolyte, and it measurably reshapes the potential. APBS does
not support membranes natively; the external `draw_membrane2` tool patches them into the permittivity,
ion-accessibility and charge grids at a large I/O cost (5 grids >2 GiB per run; 20 → 200 min). The thesis
therefore included the bilayer only for the ~20 pore-only potential maps and omitted it for the >500 energy
calculations, having checked it does not change the qualitative conclusions.


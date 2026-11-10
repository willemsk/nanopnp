---
type: Domain
title: 3. Dielectric constant and boundary conditions
description: The dielectric constant and boundary conditions at an analyte.
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

## 3. Dielectric constant and boundary conditions

| Quantity | Trapping / APBS (`trapping.tex §methods`) | ePNP-NS (`knowledge/01-physics-epnpns/index.md`) |
|---|---|---|
| Solute (protein) ε_r | **10** (cites Li 2013; `trapping.tex` L1340-1341) | **20** (ε_r,p, cites Li 2013; `epnpns.tex` L452) **[verified][^thesis]** |
| Solvent ε_r | 78.15 (`trapping.tex` L1340-1341) | 78.15 × ε_r,f^c(⟨c⟩) (`epnpns.tex` L454) **[verified][^thesis]** |
| Salt | 0.150 M monovalent, ion radius 0.2 nm (`trapping.tex` L1340) **[verified][^thesis]** | full ePNP |
| Solver | non-linear PBE `npbe`, `mg-auto`, `bcfl mdh`; coarse box 40×40×110 nm @ 0.138/0.138/0.122 nm; focused box 15×15×70 nm @ 0.052 nm (`trapping.tex` L1335-1339) **[verified][^thesis]** | FEM |

10 is APBS's value in that workflow, and 20 is ePNP-NS's. `ε_protein` is a calibration parameter,
default 20 (ruling 5; PHY-20's `Ω_a` row).

**Analyte boundary conditions.** The thesis gives none, because no analyte appeared in the
transport model; the only ones given are the pore's and the membrane's (`n·J_i = 0`, `u = 0`, ε
jump; `knowledge/01-physics-epnpns/02-governing-equations.md`). The author ruled them for an
analyte: no-flux, no-slip and a dielectric jump, as at the pore wall (ruling 4; FR-21).

[^thesis]: Willems, PhD thesis, LaTeX source, `github.com/willemsk/phdthesis-text` at `43d0f0f`. `trapping.tex` = `chapters/trapping/trapping.tex`, `epnpns.tex` = `chapters/epnpns/epnpns.tex`; `Lnnn` is the line in that commit.

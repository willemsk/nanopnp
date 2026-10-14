---
type: Domain
title: 3. Dielectric constant and boundary conditions
---

## 3. Dielectric constant and boundary conditions

| Quantity | Trapping / APBS (`trapping.tex §methods`) | ePNP-NS (`01-physics-epnpns.md`) |
|---|---|---|
| Solute (protein) ε_r | **10** (cites Li 2013) | **20** (ε_r,p, cites Li 2013) |
| Solvent ε_r | 78.15 | 78.15 × ε_r,f^c(⟨c⟩) |
| Salt | 0.150 M monovalent, ion radius 0.2 nm | full ePNP |
| Solver | non-linear PBE `npbe`, `mg-auto`, `bcfl mdh`; coarse box 40×40×110 nm @ 0.138/0.138/0.122 nm; focused box 15×15×70 nm @ 0.052 nm | FEM |

The **ε_p = 10 vs 20 conflict is real and unexplained** — same reference, two chapters. Make it a
config value.

**Analyte boundary conditions: not specified anywhere in the thesis**, because no analyte appeared
in the transport model. The only BCs given are pore + membrane (`n·J_i = 0`, `u = 0`, ε jump;
`01-physics-epnpns.md §2`). Reusing those three on an analyte surface is an *inference* — mark it
as such in code.


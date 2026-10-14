---
type: Orientation
title: Author rulings (2026-08) — these override the sources
---

## Author rulings (2026-08) — these override the sources

Given directly by the author; where they conflict with a printed source, **these win**.

| # | Question | Ruling |
|---|---|---|
| 1 | D/μ wall coefficient `P₁` | **6.2 nm⁻¹.** Table 5.2 is correct; the running-text value and the 0.62 correction are wrong. |
| 2 | Permittivity fit parameters | **Gavish (30.08, 11.5) govern**, as the model file records; the printed 42.12 cap is stale, the correct cap is 42.67 (`SPECIFICATION.md` §4.6 erratum 6; `09` §D3). |
| 3 | Meaning of `⟨c⟩` | **Configurable, default eq. 5.3**, `(1/n)Σcᵢ`; ionic strength is a named option. |
| 4 | Analyte boundary conditions | **No-flux, no-slip, dielectric jump:** a hard dielectric body, like the pore wall. |
| 5 | `ε_protein` | **A calibration parameter, not a constant.** Default 20 for ePNP-NS; in the case file, reported as fitted. APBS's 10 belongs to that workflow. |
| 6 | Pore-averaging convention | **True volume average, with the `2πr` Jacobian**; the omission is a transcription issue. Published pore averages are usable as regression targets. |
| 7 | Radial potential at 0.15 M (−14/−47 vs −29/−57 mV) | **Unresolved**; excluded from regression targets. |
| 8 | Net charge (−72.9 / −72 / −60 e) | **Different constructs**; a run records which construct and PDB it started from. −72.9 and −72 are one construct: `rhoq_pore` integrates to −72 e, and −72.9 is COMSOL's mesh-quadrature aliasing. → `04` §3.2. |
| 9 | Analyte force chain | **Forces + PMF** (`ΔU = −∫F dz`); Brownian dynamics out of scope. |
| 10 | PlyAB as a second reference case | **Yes, after v1.0.** |
| 11 | Density-map radii and atoms | **CHARMM Rmin/2** from PDB2PQR's `CHARMM.DAT`; the map used the **full-atom** MD trajectory, hydrogens included. → `SPECIFICATION.md` §5.3.1 NOTE on `geometry.density`; `04` §1.1. |
| 12 | Axial offset G9 | **0 in the MD frame** (centred on the bilayer's middle). → `04` §8 G9. |
| 13 | `⟨c⟩` inside a solid | **Has no meaning: ions do not exist there.** `ε_r,f(⟨c⟩)` is evaluated only in the fluid; water off the fluid is ion-free, `ε_r,f⁰`. → `SPECIFICATION.md` §4.4 NOTE, §5.3.1 NOTE on `exclusion`; `06` §8.1. |
| 14 | The reference polygon and VAL-05 | The 185-vertex table used **`pqr2grid`'s radial binning at L = 15 nm**; the **hand edit moved vertices**. → `SPECIFICATION.md` §7.4 NOTE on VAL-05; `04` §1.2, §1.4. |


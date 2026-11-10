---
type: Domain
title: 0. Read this first — the ACS Nano 2019 work contains no continuum analyte
description: The ACS Nano 2019 work contains no continuum analyte.
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

## 0. Read this first — the ACS Nano 2019 work contains no continuum analyte

**There is no ePNP-NS simulation of an analyte anywhere in the thesis.** The trapping chapters
solve (a) equilibrium Poisson–Boltzmann in **APBS** for a coarse-grained bead analyte, and (b) a
**1-D analytic double-barrier rate model** fitted to experimental dwell times (`trapping.tex`, `eq:double_barrier`, `eq:double_barrier_complex`) **[verified][^thesis]**. No Maxwell-stress
integral, no hydrodynamic-stress integral, no ALE/moving mesh, no analyte surface in a
Navier–Stokes domain, no computed force profile F(z). The single force number quoted (9 pN) comes
from a **fitted charge parameter**, not a stress integral (`trapping.tex`, `eq:osmoticforce` evaluated at −50 mV) **[verified][^thesis]**.

The thesis contains no continuum analyte; the force computation exists in the PlyAB work of 2022,
**Angew. Chem. Int. Ed. 2022, 61, e202206227** ([§10](11-correction-continuum-force-computation.md)). In the thesis, coupled ePNP-NS with
an embedded particle is **future work** (`conclusion.tex §sec:con:perspectives`: "*low-hanging
fruits: … (2) computing the net force exerted on translocating analyte molecules … the full
electrophoretic and hydrodynamic force landscape*") **[verified][^thesis]**. FR-21's force (NUM-28, NUM-29; VAL-11)
re-implements the 2022 computation; the thesis's own anchors for it are (i) the APBS energy
landscape, (ii) the fitted N_eo ≈ +15.5 e, (iii) the pore-only ePNP-NS fields of ch. 6 (`trapping.tex`, `tab:fitting_params_complex`; `conclusion.tex`) **[verified][^thesis]**.

---

[^thesis]: Willems, PhD thesis, LaTeX source, `github.com/willemsk/phdthesis-text` at `43d0f0f`. `trapping.tex` = `chapters/trapping/trapping.tex`, `conclusion.tex` = `chapters/conclusion/conclusion.tex`; `Lnnn` is the line in that commit.

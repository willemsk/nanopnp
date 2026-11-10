---
type: Domain
title: 8. Stated limitations, and off-axis behaviour
description: The stated limitations and the off-axis behaviour.
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

## 8. Stated limitations, and off-axis behaviour

- Bead model is **on-axis only**; free energy declared orientation-independent *by construction*
  (near-axial symmetry). Off-axis positions were never computed (`trapping.tex`, "Energy landscape of DHFR in ClyA") **[verified][^thesis]**.
- Energy **maxima are "indicative and not absolute"** — the body was shrunk to avoid overlap in the
  constriction, so real steric blocking is under-represented. All steric physics is dumped into the
  constants ΔG_steric,0, absorbed into k_eff (`trapping.tex`, "Energy landscape of DHFR in ClyA", `eq:double_barrier_complex`; `trapping_appendix.tex` `eq:cisbarrier`) **[verified][^thesis]**.
- The model depends on **N_tag only**; variants with identical N_body but different charge
  *locations* (DHFR-4I / -4C / -4O1) differ 10-fold in dwell time and are **not** describable
  (`trapping_appendix.tex §sec:trapping_appendix:body_charge_variations`; `trapping.tex` L630, 10-fold lower dwell times) **[verified][^thesis]**. Verdict: a location-aware
  analytic model "*would drastically increase in complexity*", use refined APBS or MD **[verified][^thesis]**. Charges far
  from the tag are harmless; charges near it effectively renormalise N_tag (unverified).
- Multiple current levels (L1/L2/L3) imply **several axial minima**, uninvestigated (`trapping.tex`, `sec:trapping:conclusion`) **[verified][^thesis]**.
- Generally, `conclusion.tex`: axisymmetric averaging "*imposes an inherent limit on the accuracy*",
  smears corrugation, and puts some charge in the electrolyte rather than the dielectric. 3D is the
  long-term fix; 2D-axisymmetric is kept for speed/screening (`conclusion.tex`, `sec:con:perspectives`) **[verified][^thesis]**.

[^thesis]: Willems, PhD thesis, LaTeX source, `github.com/willemsk/phdthesis-text` at `43d0f0f`. `trapping.tex` = `chapters/trapping/trapping.tex`, `trapping_appendix.tex` = `chapters/trapping_appendix/trapping_appendix.tex`, `conclusion.tex` = `chapters/conclusion/conclusion.tex`; `Lnnn` is the line in that commit.

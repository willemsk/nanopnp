---
type: Domain
title: 8. Stated limitations, and off-axis behaviour
---

## 8. Stated limitations, and off-axis behaviour

- Bead model is **on-axis only**; free energy declared orientation-independent *by construction*
  (near-axial symmetry). Off-axis positions were never computed.
- Energy **maxima are "indicative and not absolute"** — the body was shrunk to avoid overlap in the
  constriction, so real steric blocking is under-represented. All steric physics is dumped into the
  constants ΔG_steric,0, absorbed into k_eff.
- The model depends on **N_tag only**; variants with identical N_body but different charge
  *locations* (DHFR-4I / -4C / -4O1) differ 10-fold in dwell time and are **not** describable
  (`trapping_appendix.tex §sec:trapping_appendix:body_charge_variations`). Verdict: a location-aware
  analytic model "*would drastically increase in complexity*", use refined APBS or MD. Charges far
  from the tag are harmless; charges near it effectively renormalise N_tag.
- Multiple current levels (L1/L2/L3) imply **several axial minima**, uninvestigated — a v1 F(z)
  sweep should resolve them.
- Generally, `conclusion.tex`: axisymmetric averaging "*imposes an inherent limit on the accuracy*",
  smears corrugation, and puts some charge in the electrolyte rather than the dielectric. 3D is the
  long-term fix; 2D-axisymmetric is kept for speed/screening.


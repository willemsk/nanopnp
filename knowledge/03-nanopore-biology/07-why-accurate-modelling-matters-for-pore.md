---
type: Domain
title: 7. Why accurate modelling matters for pore engineering
description: "Why a blockade is hard to predict, what pore-engineering campaigns cost, and what a predictive model would replace."
tags:
- biology
- domain
sources:
- id: thesis
  resource: https://github.com/willemsk/phdthesis-text
  title: Willems, PhD thesis (LaTeX source)
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
---

## 7. Why accurate modelling matters for pore engineering

The measured blockade depends jointly on pore, analyte, and conditions (ionic strength, pH, bias), making
signals "notoriously difficult to predict and interpret unambiguously" [§"Ionic current spectroscopy"] **[verified][^thesis]**.
Engineering campaigns are correspondingly expensive: Franceschini et al. built and screened >20 ClyA variants
to find the single one that translocates dsDNA at physiological salt. A model that predicts conductance,
selectivity and EOF direction from a mutated structure turns that search into a computation. The thesis's
own worked examples: PB potential maps explained why ReFraC (D10R/K159E) reverses selectivity, EOF
direction and DNA-translocation ability relative to WtFraC; why PlyAB-R's opposed cis/trans charges suppress
EOF and change protein capture; and why ClyA-RR alone works at 0.15 M (unverified). Unmodified continuum transport theory
is quantitatively poor for ionic currents — which is exactly the gap ePNP-NS closes.

[^thesis]: Willems, PhD thesis, LaTeX source, `github.com/willemsk/phdthesis-text` at `43d0f0f`; the `.tex` file and label beside each claim locate it.

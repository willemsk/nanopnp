---
type: Domain
title: 2. Charge representation — both forms, and where each is used
description: The analyte's charge representation, in both forms and where each is used.
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

## 2. Charge representation — both forms, and where each is used

**(a) Analyte, ACS Nano 2019 — discrete per-bead point charges, B-spline discretised.** Each bead
carries the net charge of the residues it represents; PDB2PQR assigns CHARMM36 radii/charges at
pH 7.5, and APBS spreads charge onto its grid with cubic B-splines (`chgm spl2`, `srfm spl2`).
Body beads: **Q_i = N_body/7** each. Tag beads: **δ_i = −3 … +3 e** (`trapping.tex`, `sec:trapping:methods`, "Energy landscape of DHFR in ClyA", `tab:dhfr_variants`) **[verified][^thesis]**.

> **Internal inconsistency.** `fig:trapping_apbs_model` and `§methods` give Q_i = **−1.43 e**
> (7 × −1.43 = −10 e = N_body of DHFR-4S); the running text gives Q_i = **−1.7143 e**
> (7 × = −12 e = N_body of the -I/-C/-O1 variants) **[verified][^thesis]**. Both are self-consistent for *different*
> variants. Implement as `Q_i = N_body / 7`.

**(b) Pore, ePNP-NS ch. 6.** The pore's charge is the one pipeline of
`knowledge/04-clya-geometry-and-charge/03-fixed-charge-pipeline.md` §3, areal in (r, z), then
volumetric after the 1/(2πr) conversion (thesis `transport.tex`, `eq:scdpore`) **[verified][^thesis]**.

The two forms of the pore's charge are therefore **one pipeline at two stages**, not two competing
models. **No analyte-surface charge density σ_s appears
anywhere in the thesis**; an σ_s option on an analyte boundary is a new modelling choice, default
it off.

[^thesis]: Willems, PhD thesis, LaTeX source, `github.com/willemsk/phdthesis-text` at `43d0f0f`. `trapping.tex` = `chapters/trapping/trapping.tex`, `transport.tex` = `chapters/transport/transport.tex`; `Lnnn` is the line in that commit.

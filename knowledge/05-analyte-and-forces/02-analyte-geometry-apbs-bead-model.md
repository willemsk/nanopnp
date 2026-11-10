---
type: Domain
title: 1. Analyte geometry (APBS bead model)
description: The analyte geometry, an APBS bead model.
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

## 1. Analyte geometry (APBS bead model)

`trapping.tex §sec:trapping:methods`, `fig:trapping_apbs_model`.

| Item | Value |
|---|---|
| Analyte | *E. coli* DHFR + C-terminal polypeptide tag ("DHFR_Ntag_X") |
| Representation | coarse-grained beads, treated as **pseudo-atoms** in a PQR file |
| Body | **7 beads**, r = 0.8 nm (1.6 nm dia.), spherical arrangement, **0.8 nm** spacing → ~3.2 nm overall (`trapping.tex` `fig:trapping_apbs_model`, `sec:trapping:methods`) **[verified][^thesis]** |
| Tag | **9 beads**, r = 0.5 nm (1.0 nm dia.), **linear** string, **0.6 nm** spacing, one bead per 3 residues (α-helix) (`trapping.tex` `fig:trapping_apbs_model`, `sec:trapping:methods`) **[verified][^thesis]** |
| Body of revolution? | **No** — but deliberately built to be *nearly* axially symmetric |
| Positioning | placed on the **pore central z-axis** with custom Python + Biopython (`trapping.tex` `sec:trapping:methods`) **[verified][^thesis]** |
| Scan | z_body = **−12.5 nm → +27.5 nm** rel. bilayer centre, **0.5 nm** steps inside the pore (`trapping.tex` `sec:trapping:methods`) **[verified][^thesis]** |
| Per position | **new PQR + full APBS solve** (Cartesian grid). No ALE, no moving mesh, no remesh — the concept does not apply to a finite-difference PB solver |
| Real DHFR size | 3.5–4 nm; ClyA *trans* constriction 3.3 nm dia. × 4 nm; *cis* lumen 5.5 nm dia. × 10 nm; pore length **L = 14 nm** (`trapping.tex`, `sec:trapping:intro`, `sec:trapping:conclusion`, `tab:fitting_params_complex`) **[verified][^thesis]** |

Two stated reasons for coarse-graining (`trapping.tex`, "Energy landscape of DHFR in ClyA"):
(1) "*the high degree of axial symmetry in the bead model resulted in a free energy that was
independent of the precise orientation of DHFR*" **[verified][^thesis]** — the author already relies on the analyte being
effectively a body of revolution; (2) the **shrunken body** (3.2 vs 3.5–4 nm) lets it pass the
3.3 nm constriction without atom overlap, since APBS cannot model conformational change.
Consequence, verbatim: the **energy maxima "should be viewed as indicative and not absolute."** (`trapping.tex`, "Energy landscape of DHFR in ClyA") **[verified][^thesis]**

[^thesis]: Willems, PhD thesis, LaTeX source, `github.com/willemsk/phdthesis-text` at `43d0f0f`. `trapping.tex` = `chapters/trapping/trapping.tex`; `Lnnn` is the line in that commit.

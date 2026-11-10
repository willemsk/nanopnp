---
type: Open Item
title: 8. Gaps and ambiguities (questions for the author)
description: Gaps and ambiguities in the source, as questions for the author.
tags:
- clya
- open-item
sources:
- id: thesis
  resource: https://github.com/willemsk/phdthesis-text
  title: Willems, PhD thesis (LaTeX source)
- id: paper
  resource: https://doi.org/10.1039/D0NR03114C
  title: Willems et al., Nanoscale 12, 16775-16795 (2020)
- id: wp18-plan
  resource: git:0ff2d619:docs/plans/wp18-structure-ingestion.md
  title: WP18 structure stage plan, Design §4
- id: wp28-plan
  resource: git:0ff2d619:docs/plans/wp28-charge-deposition.md
  title: WP28 charge projection plan, Design §1
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
verified:
- by: process:arithmetic
  at: '2026-10-16T00:00:00Z'
---

## 8. Gaps and ambiguities (questions for the author)

Citation keys: T = `chapters/transport/transport.tex`, TA = `chapters/transport_appendix/transport_appendix.tex`;
`Lnnn` is the line at transcription ([the overview](00-overview.md)).

- **G1 — closed: the frames are 100 ps apart, not 100 fs.** T L280-281's "every 100 fs" is a typo; the DCD
  frames are the archived PQRs at 100 ps, in time order, and the final 5 ns are PQRs 50–99 (DCD frames
  48–97) **[verified][^wp18-plan]** ([§1.1](01-geometry-pipeline-as-executed.md#11-the-authors-md-archive-measured)).
- **G2 — 25 % isolevel is unjustified.** No rationale, no sensitivity study, no comparison against
  the solvent-excluded surface. Since pore radius enters conductance roughly as r^2, this is the
  single largest untested lever in the geometry. Ask what other isolevels were tried.
  **Measured on 2WCD, 28 September 2026 ([§1.4](01-geometry-pipeline-as-executed.md#14-2wcd-against-the-reference-polygon-and-the-isolevel-lever)):**
  ±0.1 of isolevel moves the bulk-resistor conductance by about ±5 %.
- **G3 — the manual vertex edit is unreproducible.** The final boundary polyline is not published and
  its vertex count is not stated; the 30-degree-wedge claim is qualitative. **For VAL-05 the list is
  delivered**, and its construction (`pqr2grid` binning at L = 15 nm, then a hand edit that moved
  vertices; §1.2, §1.4; ruling 14) puts ±1 % out of reach. The author's tolerances are in the
  `SPECIFICATION.md` §7.4 NOTE on VAL-05.
- **G4 — `q_i/(2 pi r_i)` vs `/(2 pi r)`.** The prose (T L404-408) **[verified][^thesis]** divides by the **atom's** radial
  position `r_i`; the reference's implementation (COMSOL,
  `knowledge/01-physics-epnpns/05-fixed-charge-from-structure.md`) divides by the **field point's** `r`.
  These differ within the Gaussian's support and diverge differently near the axis. The reference's
  table is the field-point form. nanopnp produces the exact azimuthal mean of a 3D Gaussian instead
  (PHY-16 step 5, PHY-17), and keeps the reference's assembly only for a supplied areal table (PHY-16
  step 6). The difference is in [§3.3](03-fixed-charge-pipeline.md#33-the-closed-form-kernel-on-the-0005-nm-lattice).
- **G5 — closed: the table stores the sum without `e`, in `e/m^2`.** Its planar integral is the integer
  −72, to 4.7e-12; `e_const` in the COMSOL assembly supplies the coulombs once **[verified][^wp28-plan]**
  ([§3.1](03-fixed-charge-pipeline.md#31-the-delivered-table-measured)).
- **G6 — ruled (ruling 6): pore averages are true volume averages.** `eq:pore_surface_integral`
  prints `beta * X dr dz` without the `2 pi r` Jacobian, while the figure caption calls it an average "over the
  entire pore volume" (T L823) **[verified][^thesis]**. The average is `2 pi r dr dz`; the printed omission is a transcription
  issue, and the [§6.3](06-validation-targets.md#63-conductance-rectification-ion-populations) pore
  averages are regression targets. `<Q_ion>_PS` and `<Q_ion>_PB` are quoted in units of `e` (counts,
  hence volume integrals), not averages, despite the `< >` notation.
- **G7 — radial potential at 0.15 M is internally inconsistent.** T L1117-1118 **[verified][^thesis]** states the lumen value
  as "approx -14 mV" (and that it is below 1 kT/e) and the constriction as "approx -47 mV", but
  `tab:radial_potential` gives **-29 mV** and **-57 mV** at 0.15 M. -29 mV is *above* 1 kT/e, so the
  prose claim fails against its own table. The prose lumen value, −14 mV, matches the 0.5 M row; its
  −47 mV matches no row. Unresolved (ruling 7, OPN-01): neither pair is a regression target.
- **G8 — constriction z-range sign typo.** T L1043 prints "1.85 < z < 1.6 nm" **[verified][^thesis]**; everywhere else it is
  **-1.85 < z < 1.6 nm** (T L881, L1076, TA) **[verified][^thesis]**. Use -1.85.
- **G9 — closed: `centre_z_nm` = 0 in the MD frame.** The thesis gives the bilayer's thickness, 2.8 nm,
  but not its z-centre; the author ruled that the MD trajectory was centred on the middle of the
  bilayer (ruling 12; [§1.1](01-geometry-pipeline-as-executed.md#11-the-authors-md-archive-measured)).
- **G10 — closed: the table's grid.** `r` in [0, 7] nm, `z` in [-3.5, 13.5] nm at 0.005 nm: 1401 x 3401
  = 4.76e6 nodes **[verified][^wp28-plan]** ([§3.1](03-fixed-charge-pipeline.md#31-the-delivered-table-measured)).
- **G11 — nothing on mesh or solver tolerances.** See §4 and §5. No convergence study of any kind is
  reported, so the published numbers carry no stated discretisation error bar.
- **G12 — MD ion parameters unspecified beyond "CHARMM36"** (no NBFIX / Beglov-Roux statement).
  Irrelevant to the continuum solve, needed only if the MD is rerun.
- **G13 — "average between cis and trans" arithmetic.** T L770-774 says the measured 0.66 corresponds
  to the average of 0.57 (1 M) and 0.84 (0.15 M) **[verified][^thesis]**; the arithmetic mean is 0.705, and for `P_Na` the
  mean of 1.3 and 5.4 is 3.35 versus the measured 1.9. The claim is qualitative, not arithmetic.

[^thesis]: Willems, PhD thesis, LaTeX source, `github.com/willemsk/phdthesis-text` at `43d0f0f`. T = `chapters/transport/transport.tex`, TA = `chapters/transport_appendix/transport_appendix.tex`, E = `chapters/electrostatics/electrostatics.tex`; `Lnnn` is the line in that commit.
[^wp18-plan]: `git show 0ff2d619:docs/plans/wp18-structure-ingestion.md`, Design §4 (MD archive frame spacing and PQR correspondence).
[^wp28-plan]: `git show 0ff2d619:docs/plans/wp28-charge-deposition.md`, Design §1 (`prod5_clya_charge` grid dimensions and integral).

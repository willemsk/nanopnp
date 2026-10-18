---
type: Open Item
title: 8. Gaps and ambiguities (questions for the author)
description: Gaps and ambiguities in the source, as questions for the author.
tags:
- clya
- open-item
sources:
- id: paper
  resource: https://doi.org/10.1039/D0NR03114C
  title: Willems et al., Nanoscale 12, 16775-16795 (2020)
- id: wp18-plan
  resource: docs/plans/wp18-structure-ingestion.md
  title: WP18 structure stage plan, Design §4
- id: wp28-plan
  resource: docs/plans/wp28-charge-deposition.md
  title: WP28 charge projection plan, Design §1
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
verified:
- by: process:arithmetic
  at: '2026-10-16T00:00:00Z'
---

## 8. Gaps and ambiguities (questions for the author)

- **G1 — "every 100 fs" is impossible.** T L280-281 says the 50 frames were taken from the final 5 ns
  "i.e. every 100 fs". 50 frames over 5 ns is **every 100 ps**, and coordinates were only written
  every 5 ps (T L273-274). Assume 100 ps. **Evidence (§1.1):** the archived PQR
  files are named `…_aligned_100ps_NN`, 99 of them, and the analysis notebook reads the DCD at
  `dt=100`. **CLOSED [verified][^wp18-plan], §1.1:** the DCD frames are the PQRs at 100 ps, in time order. The final
  5 ns are PQRs 50–99 (DCD frames 48–97).
- **G2 — 25 % isolevel is unjustified.** No rationale, no sensitivity study, no comparison against
  the solvent-excluded surface. Since pore radius enters conductance roughly as r^2, this is the
  single largest untested lever in the geometry. Ask what other isolevels were tried.
  **Measured on 2WCD, 28 September 2026 (§1.4):** ±0.1 of isolevel moves the bulk-resistor
  conductance by about ±5 %.
- **G3 — the manual vertex edit is unreproducible.** The final boundary polyline is not published and
  its vertex count is not stated; the 30-degree-wedge claim is qualitative. Without the vertex list a
  bit-for-bit geometry match is impossible; treat +-1 % on conductance as the tolerance floor.
  **For VAL-05 the list is delivered**, and its construction
  (`pqr2grid` binning at L = 15 nm, then a hand edit that moved vertices; §1.2, §1.4) puts ±1 %
  out of reach. The author's tolerances are in the `SPECIFICATION.md` §7.4 NOTE on VAL-05.
- **G4 — `q_i/(2 pi r_i)` vs `/(2 pi r)`.** The prose (T L404-408) divides by the **atom's** radial
  position `r_i`; the implementation (COMSOL, `knowledge/01-physics-epnpns/05-fixed-charge-from-structure.md`) divides by the **field point's** `r`. These
  differ within the Gaussian's support and diverge differently near the axis. The COMSOL form is what
  produced -72.9 e, so implement that; but the discrepancy should be confirmed.
- **G5 — CLOSED [verified][^wp28-plan], §3.1.** The file stores the sum *without* `e`, in `e/m^2`: its planar
  integral is the integer -72, to 4.7e-12. `e_const` in the COMSOL assembly supplies the coulombs
  exactly once, and the `e` printed inside eq. `eq:scdpore` is not also in the table.
- **G6 — pore averages omit the `2 pi r` Jacobian.** `eq:pore_surface_integral` integrates
  `beta * X dr dz`, an unweighted area average in the (r,z) half-plane, while the main text calls it
  an average "over the entire pore volume" (T L823). A true volume average needs `2 pi r dr dz`.
  Every number in §6.3 that is a pore average (Na+/Cl- ratios, PS/PB charges) depends on this choice;
  the wall-adjacent PS region is systematically under-weighted without the Jacobian. Must be resolved
  before those become regression targets. Related: `<Q_ion>_PS` and `<Q_ion>_PB` are quoted in units
  of `e` (i.e. counts, hence genuine volume integrals), not averages, despite the `< >` notation.
- **G7 — radial potential at 0.15 M is internally inconsistent.** T L1117-1118 states the lumen value
  as "approx -14 mV" (and that it is below 1 kT/e) and the constriction as "approx -47 mV", but
  `tab:radial_potential` gives **-29 mV** and **-57 mV** at 0.15 M. -29 mV is *above* 1 kT/e, so the
  prose claim fails against its own table. The -14/-30 pair matches the **0.5 M** table row, so the
  text may have been written against a different row. Trust the table.
- **G8 — constriction z-range sign typo.** T L1043 prints "1.85 < z < 1.6 nm"; everywhere else it is
  **-1.85 < z < 1.6 nm** (T L881, L1076, TA). Use -1.85.
- **G9 — bilayer placement in z is never stated.** Thickness 2.8 nm is given but its z-centre is not.
  The pore spans -1.85 to 12.25 nm and the constriction is symmetric about z ~ 0, so a bilayer
  centred at z = 0 (spanning -1.4 to +1.4 nm) is the obvious reading, but it is an inference.
  Compounding this, the MD/electrostatics frame places the structure's centre of mass at
  (0, 0, 55 Angstrom) (TA `eq:internal_radius` discussion) — the shift from MD coordinates to model
  coordinates is not given anywhere. **Evidence (§1.1):** the protein-only MD
  archive carries no lipids, so the bilayer cannot fix it. But the MD frame's all-atom extent
  brackets the model's pore extent to within 0.3–0.4 nm at each end, which is consistent with an
  offset near zero. **CLOSED by the author:** the MD trajectory was centred on
  the middle of the bilayer, so ClyA's `centre_z_nm` is 0 in the MD frame.
- **G10 — CLOSED [verified][^wp28-plan], §3.1.** `r` in [0, 7] nm, `z` in [-3.5, 13.5] nm at 0.005 nm:
  1401 x 3401 = 4.76e6 nodes, the order the estimate predicted.
- **G11 — nothing on mesh or solver tolerances.** See §4 and §5. No convergence study of any kind is
  reported, so the published numbers carry no stated discretisation error bar.
- **G12 — MD ion parameters unspecified beyond "CHARMM36"** (no NBFIX / Beglov-Roux statement).
  Irrelevant to the continuum solve, needed only if the MD is rerun.
- **G13 — "average between cis and trans" arithmetic.** T L770-774 says the measured 0.66 corresponds
  to the average of 0.57 (1 M) and 0.84 (0.15 M); the arithmetic mean is 0.705, and for `P_Na` the
  mean of 1.3 and 5.4 is 3.35 versus the measured 1.9. The claim is qualitative, not arithmetic.

[^wp18-plan]: `docs/plans/wp18-structure-ingestion.md`, Design §4 (MD archive frame spacing and PQR correspondence).
[^wp28-plan]: `docs/plans/wp28-charge-deposition.md`, Design §1 (`prod5_clya_charge` grid dimensions and integral).

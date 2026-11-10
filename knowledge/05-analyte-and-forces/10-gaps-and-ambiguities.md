---
type: Open Item
title: 9. Gaps and ambiguities
description: Gaps and ambiguities in the analyte work.
tags:
- analyte
- open-item
sources:
- id: thesis
  resource: https://github.com/willemsk/phdthesis-text
  title: Willems, PhD thesis (LaTeX source)
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
---

## 9. Gaps and ambiguities

1. **Stress-tensor forces on an analyte are absent from the trapping chapters.** The tensor
   expressions come from background ch. 2 and were never evaluated for an analyte *in the thesis*;
   [§10](11-correction-continuum-force-computation.md) has them evaluated for PlyAB + haemoglobin, with regression targets in
   [§10.6](11-correction-continuum-force-computation.md#106-validation-targets-plyab-hb). nanopnp's analytic checks of both routes
   (VER-19 to VER-21) are in [the Tier-2 test evidence](13-tier-2-test-evidence-electro-osmosis.md).
2. **"Surface charge density vs smeared volumetric charge" resolves to one pipeline, not two
   models** ([§2](03-charge-representation-both-forms-and.md)). If the author meant a genuine σ_s on an analyte boundary in other work, it is not
   in the thesis — ask.
3. **ε_protein = 10 (trapping) vs 20 (ePNP-NS)**, same citation (`trapping.tex` L1341; `epnpns.tex` L452) **[verified][^thesis]**. Ruled (ruling 5): a calibration
   parameter, default 20 for ePNP-NS; APBS's 10 belongs to that workflow.
4. **Body bead charge printed as both −1.43 e and −1.7143 e** ([§2](03-charge-representation-both-forms-and.md) (a); `trapping.tex` `fig:trapping_apbs_model`, "Energy landscape of DHFR in ClyA") **[verified][^thesis]**. Resolve as N_body/7.
5. **`eq:threshold_voltage_complex` has a typo:** it prints `log(Δx_trans / Δx_trans)` ≡ 0 (`trapping.tex` L1431) **[verified][^thesis]**;
   re-deriving dk/dV_b = 0 gives `log(Δx_trans / Δx_cis)`. The published table `tab:threshold_voltages_and_dwelltimes` lists 87.3 and 60.4 mV for N_tag +4 and +9 **[verified][^thesis]**.
   With the fitted parameters of `tab:fitting_params_complex` (kT/e = 25.69 mV), the corrected form gives 87.6 and 61.1 mV and the zero term 85.1 and 59.6 mV **[verified][^threshold-arithmetic]**:
   the corrected form is the closer to the published table, by 0.3 to 0.7 mV against 2.2 to 0.8 mV.
6. **Sign convention is sloppy:** V_b is negative throughout, yet V_thresh is tabulated positive
   (the leading minus makes it a magnitude) (`trapping.tex` `eq:external-barrier`, `eq:threshold_voltage_complex`, `tab:threshold_voltages_and_dwelltimes`) **[verified][^thesis]**. Pick one convention and assert it in tests.
7. **`f(t) = k·e^{−kT}`** (`trapping_appendix.tex §single_bound_state`) is a typo for `k·e^{−kt}`;
   the correct exponent appears two lines later **[verified][^thesis]**.
8. **Δx_cis is ill-defined by the author's own admission** (voltage-dependent barrier location; `trapping.tex` `sec:trapping:biased_landscape`) **[verified][^thesis]** — a
   fit parameter, not a geometric constant. A v1 PMF that locates the *cis* barrier should report
   against both 2.7 nm and 5.21 nm.
9. **Caption/text conflict:** `trapping_translocation_voltage` says the threshold voltage
   "increases" ≈5.21 mV per tag charge; the text says "decrease of ≈5 mV". Both describe |V_thresh|
   falling 87.3 → 60.4 mV; the caption means the signed value (`trapping.tex` `fig:trapping_translocation_voltage` caption, "Characteristics of the trapping") **[verified][^thesis]**.
10. **N_eo "depends solely on size and shape"** — asserted by the source (`trapping.tex`, after `eq:external-barrier`) **[verified][^thesis]**, not tested there.
    Hypothesis, not result.

---

[^thesis]: Willems, PhD thesis, LaTeX source, `github.com/willemsk/phdthesis-text` at `43d0f0f`. `trapping.tex` = `chapters/trapping/trapping.tex`, `trapping_appendix.tex` = `chapters/trapping_appendix/trapping_appendix.tex`, `epnpns.tex` = `chapters/epnpns/epnpns.tex`; `Lnnn` is the line in that commit.
[^threshold-arithmetic]: By arithmetic from `eq:threshold_voltage_complex` (`trapping.tex` L1427-1437) with `log(Δx_trans/Δx_cis)` and `tab:fitting_params_complex`: ln k_trans = −3.44, ln k_cis = 7.39, Δx_trans = 3.5 nm, Δx_cis = 5.21 nm, Ψ_tag trans 0.860 and cis 0.218, N_eo = 15.5, N_body = −13, L = 14 nm: 87.64 mV (N_tag +4) and 61.06 mV (+9); without the log term, 85.11 and 59.63 mV.

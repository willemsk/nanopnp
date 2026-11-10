---
type: Domain
title: 7. Validation targets
description: The validation targets of the analyte work.
tags:
- analyte
- domain
sources:
- id: thesis
  resource: https://github.com/willemsk/phdthesis-text
  title: Willems, PhD thesis (LaTeX source)
- id: paper
  resource: https://doi.org/10.1039/D0NR03114C
  title: Willems et al., Nanoscale 12, 16775-16795 (2020)
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
---

## 7. Validation targets

**Forces / fields** (V_b negative = *cis*→*trans*; F_eo pushes *cis*→*trans*, i.e. **into** the pore):

| Quantity | Value | Condition |
|---|---|---|
| F_eo | **≈ 9 pN** (0.178 pN/mV; recompute: 8.87 pN **[verified][^feo-arithmetic]**) | V_b = −50 mV, N_eo = 15.5, L = 14 nm |
| F_ep on DHFR_7_O2 (N_net = −6) | 3.4 pN, opposing **[verified][^feo-arithmetic]** | same |
| Axial field | ≈ 3.5 × 10⁶ V/m | −50 mV over 14 nm (`trapping.tex`, after `eq:static-barrier`) **[verified][^thesis]** |
| Coulomb force, 10 e protein (background) | ≈ 4 pN | `nanopores.tex` **[verified][^thesis]** |
| Stokes drag, 5 nm sphere at 0.1 m/s (background) | ≈ 4 pN | `nanopores.tex` **[verified][^thesis]** |

EOF and pressure of the pore alone: `knowledge/04-clya-geometry-and-charge/06-validation-targets.md` §6.4.

**Landscape geometry (APBS, DHFR_Ntag_O2):** minimum z_body = **+3 nm**; *cis* max **+5.7 nm**;
*trans* max **−0.6 nm**; Δx_trans = **3.5 nm** (fixed); Δx_cis = 2.7 nm at equilibrium but
**5.21 ± 1.32 nm** fitted — the *cis* barrier vanishes above |V_b| ≈ 50 mV and relocates to the
*cis* entry (z ≈ 10–13 nm) (`trapping.tex` `fig:apbs_simulation_results`, `sec:trapping:biased_landscape`, `tab:fitting_params_complex`) **[verified][^thesis]**.

**Barrier gradients [kT per elementary charge]:**

| Source | trans | cis |
|---|---|---|
| APBS, per extra **body** negative charge (−10→−13 e) | 1.46 | 0.04 |
| APBS, per extra **tag** positive charge (+4→+9 e) | 0.875 | 0.621 |
| Fitted Ψ_tag (Table `tab:fitting_params_complex`) | **0.860 ± 0.078** | **0.218 ± 0.167** |

Gradients and fitted Ψ_tag as printed in `trapping.tex` (`fig:apbs_simulation_results`, `tab:fitting_params_complex`) **[verified][^thesis]**.

**Fitted attempt rates:** ln(k_eff^trans/Hz) = −3.44 ± 1.24 (3.21 × 10⁻² Hz);
ln(k_eff^cis/Hz) = 7.39 ± 1.02 (1.62 × 10³ Hz). Fixed: N_body = −13, L = 14 nm, Δx_trans = 3.5 nm (`trapping.tex` `tab:fitting_params_complex`) **[verified][^thesis]**.

**Peak dwell times τ_thresh and threshold voltages |V_thresh|** (complex model, DHFR_Ntag_O2, 150 mM
NaCl / 15 mM Tris pH 7.5 / 28 °C; `trapping.tex` `tab:threshold_voltages_and_dwelltimes`, `fig:trapping_dwell_times_body`; `trapping_appendix.tex` `fig:trapping_traces`; **[verified][^thesis]**):

| N_tag | +4 | +5 | +6 | +7 | +8 | +9 |
|---|---|---|---|---|---|---|
| τ_thresh [s] | 2.28 | 4.16 | 7.59 | 13.9 | 25.3 | 46.2 |
| \|V_thresh\| [mV] | 87.3 | 79.2 | 73.0 | 68.1 | 64.1 | 60.4 |

≈ 5.2–5.4 mV less bias per added tag charge. Also: P_trans = **0.002 %** at zero bias and zero tag
charge; V(P_trans = 99.9 %) shifts −130 → −85 mV over N_tag +4 → +9 while the *cis* (0.01 %) line
moves only −40 → −35 mV (`trapping.tex` "Characteristics of the trapping", `eq:ptrans`) **[verified][^thesis]**; DHFR_5_O2 τ = 0.32 ± 0.17 s at −60 mV (`trapping.tex`, "Binding of NADPH") **[verified][^thesis]**; I_res ≈ 67–75 % (L1), 46–58 % (L2),
~39 % (L3) (`trapping_appendix.tex` `tab:dhfr_iresp`) **[verified][^thesis]**; NADPH k_on = 1.39–2.03 × 10³ s⁻¹ mM⁻¹, k_off = 56–71 s⁻¹ at −60 mV (`trapping_appendix.tex` `tab:nadph_rates`) **[verified][^thesis]**; residual current
rises ≈ 2.5 % from −60 → −100 mV (position shift, not stretching — unfolding needs 27 pN apo /
98 pN NADPH-bound) (`trapping.tex`, "Binding of NADPH") **[verified][^thesis]**.

[^feo-arithmetic]: By arithmetic from [§4](05-force-computation-the-analytic-model.md)'s `F_eo = e·N_eo·V_b/L`: 1.602 × 10⁻¹⁹ C × 15.5 × 0.050 V / 14 × 10⁻⁹ m = 8.87 × 10⁻¹² N; with N_net = −6 in place of N_eo, 3.43 × 10⁻¹² N.

[^thesis]: Willems, PhD thesis, LaTeX source, `github.com/willemsk/phdthesis-text` at `43d0f0f`. `trapping.tex` = `chapters/trapping/trapping.tex`, `trapping_appendix.tex` = `chapters/trapping_appendix/trapping_appendix.tex`, `nanopores.tex` = `chapters/nanopores/nanopores.tex`; `Lnnn` is the line in that commit.

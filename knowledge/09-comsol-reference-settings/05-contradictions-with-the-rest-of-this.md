---
type: Erratum
title: D. Contradictions with the rest of this knowledge base
description: Contradictions between the model report and the rest of the knowledge
  base.
tags:
- comsol
- erratum
sources:
- id: esi
  resource: https://www.rsc.org/suppdata/d0/nr/d0nr03114c/d0nr03114c1.pdf
  title: Electronic supplementary information of the paper
- id: comsol-report
  resource: COMSOL Multiphysics 5.4 model report of 22 May 2020
  title: COMSOL model report (5.4)
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
verified:
- by: process:arithmetic
  at: '2026-10-14T00:00:00Z'
- by: process:tests/tier1/test_knowledge_arithmetic.py::test_permittivity_cap_gavish_and_buchner_at_5_3_m
  at: '2026-10-16T00:00:00Z'
---

## D. Contradictions with the rest of this knowledge base

| # | KB statement | Report says | Action |
|---|---|---|---|
| 1 | this directory: stabilisation OPEN, both branches live | **Streamline + crosswind ON in tds and spf; crosswind = Do Carmo and Galeão; approximate residual; isotropic off** | Settle `knowledge/06-numerics-fem/04-stabilisation.md`; the "no stabilisation" policy is *not* like-for-like |
| 2 | `knowledge/06-numerics-fem/05-nonlinear-solution.md`: "PARDISO direct + Newton with a lower-bounded variable damping factor", unverified provenance | **Confirmed exactly**: PARDISO, pivot perturbation 1e-13, damping 0.2 initial / 0.01 minimum / 0.2 recovery, 100 iterations, fully coupled | Mark `[verified]`, cite this file |
| 3 | ruling 2 of `knowledge/00-orientation/05-author-rulings-2026-08-these-override.md`: permittivity fit = authors' Buchner values (29.50, 11.74); "confirmed by the 42.12 cap" | **The model used Gavish: `epsr_ms = 30.08`, `epsr_alpha = 11.5`**, matching the ESI text | **Settled: the shipped model used Gavish, so those govern.** With 30.08/11.5, `εr(5.3 M) = 42.67`; with 29.50/11.74, 42.13. The stale 42.12 cap came from the Buchner fit, **not** from what was solved. Ruling 2, index §"Still open" and `knowledge/01-physics-epnpns/08-errata-in-the-source-with-the-arithmetic.md` E5 now record Gavish as governing; `SPECIFICATION.md` §4.6 erratum 6 carries the arithmetic. **[verified][^comsol-report][^esi]** **[tested: tests/tier1/test_knowledge_arithmetic.py::test_permittivity_cap_gavish_and_buchner_at_5_3_m]** |
| 4 | this directory: ESI is 143 pages | 162 pages; 143 is the ToC page of §5 | Corrected above |
| 5 | `knowledge/06-numerics-fem/08-mesh-resolution-and-adaptivity.md`: mesh design = boundary layers, `h₁ ≈ λ_D/5`, ~15 geometric layers | **No boundary-layer mesh at all**; isotropic free triangles, 0.05 nm on the pore wall, growth 1.05, 120 917 triangles | Our BL mesh is a deliberate deviation; keep it, but do not describe it as matching COMSOL |
| 6 | `knowledge/06-numerics-fem/08-mesh-resolution-and-adaptivity.md`: "no discretisation error bar" | Report gives element counts and quality (0.6378 / 0.9765) but **no DOF and no convergence study** | Narrow the claim: quality yes, convergence no |
| 7 | trap 1 of `knowledge/00-orientation/02-the-five-things-most-likely-to-trip-you.md`: wall function `1 − exp(−6.2(d + 0.01))` | Verbatim `1 - exp(-0.62e1*(wdf.dwd + 0.01))` | Confirmed **[verified][^comsol-report][^esi]** |
| 8 | trap 3 of `knowledge/00-orientation/02-the-five-things-most-likely-to-trip-you.md`: no dielectric-gradient body force | Body Force is `E·ρ_ion` only | Confirmed **[verified][^comsol-report][^esi]** |
| 9 | ruling 3 of `knowledge/00-orientation/05-author-rulings-2026-08-these-override.md`: `⟨c⟩` = arithmetic mean of ion concentrations | `cdf.dcav = (cdf.dcpos + cdf.dcneg)*0.5` | Confirmed **[verified][^comsol-report][^esi]** |
| 10 | ruling 5 of `knowledge/00-orientation/05-author-rulings-2026-08-these-override.md`: `ε_protein` = 20 | `epsr_nanopore = 20`; `epsr_membrane = 3.2` | Confirmed **[verified][^comsol-report][^esi]** |

---

[^esi]: Electronic supplementary information of the paper.
[^comsol-report]: COMSOL model report (5.4).

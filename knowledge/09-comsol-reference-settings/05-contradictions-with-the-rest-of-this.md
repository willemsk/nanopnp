---
type: Erratum
title: D. Reconciliations with the model report
description: What the model report settled against the rest of the knowledge base, and the permittivity arithmetic.
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

## D. Reconciliations with the model report

What the model report settled against the rest of this knowledge base. Each settlement is now
recorded where it governs; this file keeps the one that rests on arithmetic.

**The permittivity parameters.** The model used Gavish's parameters, `epsr_ms = 30.08`,
`epsr_alpha = 11.5`, as the ESI text says, not the authors' Buchner fit (29.50, 11.74). With
30.08/11.5, `εr(5.3 M) = 42.67`; with 29.50/11.74, 42.13. The printed 42.12 cap came from the Buchner
fit, **not** from what was solved. Ruling 2 and `knowledge/01-physics-epnpns/08-errata-in-the-source-with-the-arithmetic.md`
E6 record Gavish as governing; `SPECIFICATION.md` §4.6 erratum 6 carries the arithmetic
**[verified][^comsol-report][^esi]** **[tested: tests/tier1/test_knowledge_arithmetic.py::test_permittivity_cap_gavish_and_buchner_at_5_3_m]**.

**Settled by the report, recorded elsewhere** **[verified][^comsol-report]**: streamline and
crosswind stabilisation on (`knowledge/06-numerics-fem/04-stabilisation.md`); no boundary layers,
isotropic free triangles, 0.05 nm on the pore wall, growth 1.05, 120 917 triangles, quality given
but no DOF and no convergence study ([A](02-mesh-27.md)); PARDISO, the damping and the fully coupled
solver ([B](03-solver-3-4.md)); the wall function `1 − exp(−6.2(d + 0.01))`, the body force `E·ρ_ion`
only, `⟨c⟩` the arithmetic mean, `ε_protein` 20 ([C](04-physics-settings.md)); 143 is the ToC page
of the report's §5, which runs to p. 162 ([the overview](00-overview.md)). The default mesh is
isotropically graded, as the reference was; boundary layers are an optional later strategy (FR-11).

---

[^esi]: Electronic supplementary information of the paper.
[^comsol-report]: COMSOL model report (5.4), §1.1 Parameters, pp. 3–5, for the permittivity parameters, and §2.4, §2.5, §2.7, §3 and §4, pp. 66–142, for the settings settled there; pages as in [the document map](01-document-map.md), the PDF as [the overview](00-overview.md) says.

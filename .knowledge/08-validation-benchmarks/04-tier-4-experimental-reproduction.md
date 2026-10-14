---
type: Benchmark
title: Tier 4 — Experimental reproduction (release gate)
description: Tier 4, experimental reproduction, the release gate.
tags:
- validation
- benchmark
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

## Tier 4 — Experimental reproduction (release gate)

Reproduce the published ClyA results:

- Conductance vs salt over the experimental range **0.05–3 M** (simulated 0.005–5 M).
- I–V and rectification `α(V_b)` over **±200 mV** — not ±150 mV, which drops the highest-|V|
  quarter of the envelope, precisely where rectification is largest and Newton convergence hardest.
- Cation transport number `t_Na⁺`.

**Acceptance: agreement no worse than the paper's own agreement with experiment.**

**Also reproduce the failure.** Classical PNP-NS must reproduce the paper's reported
*over-estimation* of current. Reproducing the failure of the uncorrected model is as diagnostic as
reproducing the success of the corrected one — it proves the corrections are actually active and
doing what they should.

Detailed numeric targets — transport numbers, peak radial potentials, pore-averaged ion ratios,
energy barriers, EOF velocities, pressure hotspots, and the correction-ablation percentages — are
tabulated in `.knowledge/04-clya-geometry-and-charge/06-validation-targets.md`.

> **Caveat on all Tier-4 targets.** The published results carry no discretisation error bar: the
> thesis reports no element counts, no mesh convergence study, no solver tolerances. Small
> disagreements may be *their* discretisation error rather than ours. Where a target is a
> pore-average, check which averaging convention it uses — the thesis's pore averages appear to
> omit the `2πr` Jacobian while being described as volume averages.

---


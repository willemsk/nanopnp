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

VAL-07 to VAL-10 state the targets, the ±200 mV envelope and the acceptance, and require the
classical model to reproduce the paper's over-estimation of current (`SPECIFICATION.md` §7.5).
Detailed numeric targets are tabulated in `knowledge/04-clya-geometry-and-charge/06-validation-targets.md`.

> **Caveat on all Tier-4 targets.** The published results carry no discretisation error bar: the
> thesis reports no element counts, no mesh convergence study, no solver tolerances. Small
> disagreements may be *their* discretisation error rather than ours. A pore-averaged target is a
> true volume average with the `2πr` Jacobian; the thesis's printed integral omits it, a
> transcription issue (ruling 6).

---


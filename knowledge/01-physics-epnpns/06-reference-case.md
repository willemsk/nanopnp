---
type: Physics
title: 6. Reference case
description: "The ClyA-AS reference case: structure, electrolyte, bias, temperature, solver and validated quantities."
tags:
- physics
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

## 6. Reference case

| | |
|---|---|
| Structure | PDB **2WCD** (Mueller et al., *Nature* **459**, 726, 2009), dodecameric ClyA, C₁₂ |
| Variant | **ClyA-AS** (directed-evolution variant), not wild type |
| Electrolyte | NaCl, 0.05–3 M experimental, 0.005–5 M simulated |
| Bias | −200 … +200 mV |
| Temperature | 298.15 K (25 ± 1 °C experimentally) |
| Solver used | COMSOL Multiphysics 5.4, PARDISO direct + damped Newton |
| Validated QoIs | conductance G, cation transport number t_Na⁺, rectification α(V_b) |

The rows are read from the thesis **[verified][^transport]**, except the solver's linear method:
PARDISO with a damped Newton is the author's report (`07-implementation-notes-carried-forward.md`),
which the thesis does not print.

---

[^transport]: Thesis at `43d0f0f`: `chapters/transport/transport.tex` (structure and variant
    82-85, 124; experimental temperature 484; electrolyte and bias 485, 506, 664-665; conductance,
    selectivity and rectification in §"Transport of ions through ClyA", 496-784) and
    `chapters/epnpns/epnpns.tex` (COMSOL Multiphysics v5.4, 234; the solve's 298.15 K, Table 5.1
    note (b), 496).

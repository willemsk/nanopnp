---
type: Physics
title: 4. Rationale worth preserving
description: "Why the ion wall offset is 0.01 nm, why the viscosity wall function was fitted inverted, and why bulk fits are used near walls."
tags:
- physics
sources:
- id: paper
  resource: https://doi.org/10.1039/D0NR03114C
  title: Willems et al., Nanoscale 12, 16775-16795 (2020)
- id: thesis
  resource: https://github.com/willemsk/phdthesis-text
  title: Willems, PhD thesis (LaTeX source)
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
verified:
- by: process:tests/tier1/test_corrections.py::test_ver03_ion_wall_function_check_values
  at: '2026-11-09T00:00:00Z'
- by: process:tests/tier1/test_corrections.py::test_ver03_viscosity_wall_function_check_values
  at: '2026-11-09T00:00:00Z'
---

## 4. Rationale worth preserving

**Why the wall offset is 0.01 nm and not Simakov's 0.22 nm.** With Simakov's form
`1 − exp(−P₁(d̄ − P₂))` and `P₂ = 0.22`, the function is negative over the first 0.22 nm
(thesis `epnpns.tex`:844-845). Pederson et al. clamped it to an arbitrary positive floor, which
leaves a dead zone of nearly 0.2 nm with diffusivity orders of magnitude below bulk (846-848), so a
pore narrower than ~0.5 nm carries essentially no current — contradicted experimentally (Rigo 2019). Willems et al. instead assign the
full offset to the heavy atom, i.e. assume the ion-inaccessible volume is *already* excluded by the
geometry. The model keeps the offset at 0.01 nm and adds it (`d̄ + P₂`, errata E1), so
`f^w(0) = 0.06` and `f^w(0.75 nm) = 0.99`. **[tested: tests/tier1/test_corrections.py::test_ver03_ion_wall_function_check_values]**

**Why the viscosity wall function was fitted inverted.** Pronk's MD viscosity data were offset by
each protein's hydrodynamic radius so that `d = 0` means "at the wall" independent of protein
size, then normalised and inverted (`η_0/η^w`) so the fit ranged over [0,1]. Resulting values:
`η_0/η^w(0) = 0.379` (thesis: 0.37; i.e. ~2.6× bulk viscosity at the wall), `η_0/η^w(1.45 nm) = 0.99`. **[tested: tests/tier1/test_corrections.py::test_ver03_viscosity_wall_function_check_values]**

**Why bulk fits are used inside the double layer.** Acknowledged as the model's main
approximation: there is no non-bulk experimental data and no tractable analytical model. Justified
*a posteriori* by agreement with experiment except at the lowest salt (< 0.05 M), where double
layers overlap and selectivity dominates.

---


---
type: Pipeline
title: 7. Stated limitations and caveats
description: The limitations and caveats the source work states.
tags:
- clya
- pipeline
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
---

## 7. Stated limitations and caveats

- ePNP-NS **slightly overestimates** the current for c_bulk < 0.15 M; agreement is best for
  c_bulk >= 0.15 M (T L646-654).
- ICR does not match quantitatively below 0.5 M — trends only (T L711-715).
- Two reasons offered for the low-salt failure: (i) mobilities were fitted to *bulk* conductances in
  locally electroneutral solution, and inside a co-ion-depleted pore only one ion species is present,
  so the mobility model breaks down; (ii) the pore may narrow slightly at low salt, which a static
  geometry and static charge map cannot capture (T L724-731).
- Results are steady-state continuum: they represent a **10-100 ns time average** (T L847-849).
- Reversal-potential selectivity is not the symmetric-condition selectivity: the measured
  `t_Na = 0.66` (`P_Na = 1.9`) of Franceschini et al. sits between the simulated cis (1 M, 0.57) and
  trans (0.15 M, 0.84) values; the GHK equation ignores EOF-driven flux and assumes Nernst-Einstein
  holds at all concentrations (T L770-781).
- Radial averaging is expected to fail for narrow or non-axisymmetric pores (internal corrugations,
  opposing charges in one radial plane) — a 3D treatment is required there (T L433-451).

---


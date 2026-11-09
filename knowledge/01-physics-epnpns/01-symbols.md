---
type: Physics
title: 1. Symbols
description: "Points to §4.1.2 for the symbols and explains the two easily misread ones, ⟨c⟩ and d."
tags:
- physics
sources:
- id: thesis
  resource: https://github.com/willemsk/phdthesis-text
  title: Willems, PhD thesis (LaTeX source)
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
---

## 1. Symbols

Symbols, units and constants: §4.1.2 of `SPECIFICATION.md`. Two of them are easily misread:

> **⟨c⟩ is the average ion concentration, not the ionic strength.** Thesis eq. 5.3 defines
> `⟨c⟩ = (1/n) Σ_i c_i`; its prose says "local ionic strength" (`epnpns.tex`:815). The two coincide
> for a symmetric 1:1 salt. PHY-01 (ruling 3) makes the mean the default and the ionic strength a
> named option.

> **`d` excludes the membrane.** The wall-distance field is the distance to the pore boundary
> only. The bilayer is deliberately not a source of wall distance, because electrolyte properties
> near the membrane do not affect the pore's figures of merit. In COMSOL this was implemented with
> a general extrusion operator and was **not smoothed** (author, 2026-08). The validated field is
> the unsmoothed C⁰ field; C¹ mollification is an optional deviation, off by default (PHY-02,
> NUM-31).

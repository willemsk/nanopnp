---
type: Physics
title: 1. Symbols
description: The symbols, units and notation of the model.
tags:
- physics
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

| Symbol | Meaning | Units |
|---|---|---|
| `φ` | electric potential | V |
| `c_i` | concentration of ion *i* | mol m⁻³ |
| `u` | fluid velocity | m s⁻¹ |
| `p` | pressure | Pa |
| `J_i` | total molar flux of ion *i* | mol m⁻² s⁻¹ |
| `ρ_pore` | fixed (protein) space charge density | C m⁻³ |
| `ρ_ion` | mobile ionic charge density = `F Σ_i z_i c_i` | C m⁻³ |
| `⟨c⟩` | **average ion concentration** = `(1/n) Σ_i^n c_i` | mol L⁻¹ |
| `d` | distance to the **nearest pore boundary** | nm |
| `ε_0` | vacuum permittivity 8.85419 × 10⁻¹² | F m⁻¹ |
| `F` | Faraday constant 96485.33 | C mol⁻¹ |
| `N_A` | Avogadro 6.022 × 10²³ | mol⁻¹ |
| `a_i`, `a_0` | steric cubic diameters, ion / water | m |

> **⟨c⟩ is the average ion concentration, not the ionic strength.** The thesis defines
> `⟨c⟩ = (1/n) Σ_i c_i` in eq. 5.3 while the prose elsewhere says "local ionic strength". For a
> symmetric 1:1 salt the two coincide, so the distinction never surfaced in the published work —
> but it must be decided explicitly before any multivalent species is added. Implement `⟨c⟩` as
> the arithmetic mean per eq. 5.3, and make the choice a named, documented option.

> **`d` excludes the membrane.** The wall-distance field is the distance to the pore boundary
> only. The bilayer is deliberately not a source of wall distance, because electrolyte properties
> near the membrane do not affect the pore's figures of merit. In COMSOL this was implemented with
> a general extrusion operator and was **not smoothed** (author, 2026-08). See §7 for why we
> nevertheless recommend mollifying it in the new implementation.

---


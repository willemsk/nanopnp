---
type: Physics
title: 3. The corrections
description: "The infinite-dilution values and their sources, the data behind the fits and the measured Einstein ratio; §4.3 states the corrections."
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
- by: process:tests/tier1/test_corrections.py::test_ver05_einstein_ratio_drifts_with_concentration
  at: '2026-10-16T00:00:00Z'
---

## 3. The corrections

`SPECIFICATION.md` §4.3 states them: the product form PHY-10, the forms PHY-11, the coefficients
PHY-12 and `data/corrections/willems2020_nacl.yaml`, the capping PHY-13, the derived mobility PHY-14
and the omission PHY-15. The ion wall function's `+` offset is §4.6's erratum 1, with its arithmetic in
errata E1; the viscosity wall function's `−` offset is printed consistently and checked by PHY-12's
`η⁰/η^w(0) = 0.379`.

**Infinite-dilution values (298.15 K):**

| | value | source |
|---|---|---|
| `D_Na⁰` | 1.334 × 10⁻⁹ m² s⁻¹ | Mills 1989 |
| `D_Cl⁰` | 2.032 × 10⁻⁹ m² s⁻¹ | Mills 1989 |
| `μ_Na⁰` | 5.192 × 10⁻⁸ m² V⁻¹ s⁻¹ | Bianchi 1989 |
| `μ_Cl⁰` | 7.909 × 10⁻⁸ m² V⁻¹ s⁻¹ | Bianchi 1989 |
| `η⁰` | 8.904 × 10⁻⁴ Pa s | Hai-Lang 1996 |
| `ϱ⁰` | 997 kg m⁻³ | Hai-Lang 1996 |
| `ε_r,f⁰` | 78.15 | Gavish 2016 |
| `ε_r,p` | 20 (default; a calibration parameter, PHY-20, ruling 5) | Li/Li/Zhang/Alexov 2013 |
| `ε_r,m` | 3.2 | Gramse 2013 |
| `t_Na⁰` | 0.3963 | Bianchi 1989 |

**The data behind the fits.** Fits cover 0–5.3 M NaCl, from data reaching 4 M for `D` and 5 M for
`μ` (thesis `epnpns.tex`:640-642, 665-666). Both are extrapolated beyond their data (`epnpns.tex`:646,
679-680).

### 3.0 The Einstein ratio, measured

`D_i/μ_i` in units of `kT/e`, evaluated from the shipped coefficients far from any wall
(`f^w = 1`), computed with the implementation in `nanopnp.materials`. **[tested: tests/tier1/test_corrections.py::test_ver05_einstein_ratio_drifts_with_concentration]**

| `⟨c⟩` | 0.15 M | 1 M | 3 M | 5.3 M |
|---|---|---|---|---|
| Na⁺ | 1.208 | 1.468 | 1.665 | 1.818 |
| Cl⁻ | 1.132 | 1.221 | 1.279 | 1.300 |

The frequently quoted "1.2–1.7 × kT/e between 0.15 and 3 M" describes **Na⁺**; Cl⁻ drifts far
less, reaching only 1.28 at 3 M. Both rise monotonically with concentration, because `D` is fitted
to self-diffusion data and `μ` to conductivity data and the two fits differ.

### 3.1 ePNP-NS → PNP-NS

PHY-21 states the reduction (thesis `epnpns.tex`:425-428).

### 3.2 Auxiliary: the transport-number fit

`t_Na^c(c̄)` shares the inverse-polynomial form. It is **not needed at solve time** — it was used
to split measured molar conductivity `Λ(c)` into per-ion mobilities via
`μ_i(c) = Λ(c) t_i(c) / (z_i F)`, with `t_Cl = 1 − t_Na`. Keep it in the data file: it is exactly
what someone re-parameterising a different salt will need.

---


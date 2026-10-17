---
type: Physics
title: 3. The corrections
description: The concentration- and wall-distance-dependent corrections, the Einstein
  ratio as measured, and the reduction to PNP-NS.
tags:
- physics
sources:
- id: paper
  resource: https://doi.org/10.1039/D0NR03114C
  title: Willems et al., Nanoscale 12, 16775-16795 (2020)
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
verified:
- by: process:tests/tier1/test_corrections.py::test_ver05_einstein_ratio_drifts_with_concentration
  at: '2026-10-16T00:00:00Z'
---

## 3. The corrections

Each property is `X(⟨c⟩, d) = X⁰ · f^c(c̄) · f^w(d̄)`, with `c̄ = ⟨c⟩/(1 M)` and `d̄ = d/(1 nm)`
dimensionless. Numeric parameters live in `data/corrections/willems2020_nacl.yaml`.

| Property | `f^c` | `f^w` |
|---|---|---|
| `D_i` | `(1 + P₁c̄^½ + P₂c̄ + P₃c̄^{3/2} + P₄c̄²)⁻¹` | `1 − exp(−P₁(d̄ + P₂))` |
| `μ_i` | same form, own coefficients | `1 − exp(−P₁(d̄ + P₂))` |
| `η` | `1 + P₁c̄^½ + P₂c̄ + P₃c̄² + P₄c̄^{7/2}` | `1 + exp(−P₁(d̄ − P₂))` |
| `ϱ` | `1 + P₁c̄ + P₂c̄²` | — |
| `ε_r,f` | `1 − (1 − P₁/P₀) · L(3P₂c̄/(P₀−P₁))`, `L(x) = coth x − 1/x` | — |

**Note the two wall functions have opposite offset signs** — `(d̄ + P₂)` for D and μ,
`(d̄ − P₂)` for η. This is not a typo in this file; both are verified in §8.

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
| `ε_r,p` | 20 | Li/Li/Zhang/Alexov 2013 |
| `ε_r,m` | 3.2 | Gramse 2013 |
| `t_Na⁰` | 0.3963 | Bianchi 1989 |

**Validity and capping.** Fits cover 0–5.3 M NaCl. Above 5.3 M every property is **clamped** to
its 5.3 M value. Diffusivities between 4 and 5.3 M are extrapolated (no experimental data beyond
4 M). Implement clamping explicitly and log when it activates — a silently clamped run at high
salt is a plausible source of confusion.

**Deliberate omission.** Simakov and Pederson additionally reduce ion motility by the ratio of
ion radius to pore radius. Willems et al. **chose not to include this**, on the grounds that
extrapolating it to ions whose hydrodynamic radius is comparable to a solvent molecule is
questionable. Do not add it silently; if ever added, it must be an opt-in experimental model.

### 3.0 The Einstein ratio, measured

`D_i/μ_i` in units of `kT/e`, evaluated from the shipped coefficients far from any wall
(`f^w = 1`), computed with the implementation in `nanopnp.materials`. **[tested: tests/tier1/test_corrections.py::test_ver05_einstein_ratio_drifts_with_concentration]**

| `⟨c⟩` | 0.15 M | 1 M | 3 M | 5.3 M |
|---|---|---|---|---|
| Na⁺ | 1.208 | 1.468 | 1.665 | 1.818 |
| Cl⁻ | 1.132 | 1.221 | 1.279 | 1.300 |

The frequently quoted "1.2–1.7 × kT/e between 0.15 and 3 M" describes **Na⁺**; Cl⁻ drifts far
less, reaching only 1.28 at 3 M. Both rise monotonically with concentration, because `D` is fitted
to self-diffusion data and `μ` to conductivity data and the two fits differ. A regression test
should assert monotonicity plus per-ion bounds rather than a single shared range.

### 3.1 ePNP-NS → PNP-NS

The classical equations are recovered exactly by setting

```
β_i = 0  and  ε_r,f^c = D_i^c = μ_i^c = η^c = ϱ^c = 1  and  D_i^w = μ_i^w = η^w = 1
```

This is why the correction registry should treat "off" as just another named model: the
PNP-vs-ePNP comparison, and the contribution of each individual correction, then becomes a
configuration sweep rather than a code branch.

### 3.2 Auxiliary: the transport-number fit

`t_Na^c(c̄)` shares the inverse-polynomial form. It is **not needed at solve time** — it was used
to split measured molar conductivity `Λ(c)` into per-ion mobilities via
`μ_i(c) = Λ(c) t_i(c) / (z_i F)`, with `t_Cl = 1 − t_Na`. Keep it in the data file: it is exactly
what someone re-parameterising a different salt will need.

---


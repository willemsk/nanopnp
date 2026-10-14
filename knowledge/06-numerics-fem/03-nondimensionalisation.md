---
type: Numerics
title: 3. Nondimensionalisation
description: The nondimensionalisation and the scales that keep every field of order one.
tags:
- numerics
- numerics
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
---

## 3. Nondimensionalisation

| Scale | Definition | Value / range |
|---|---|---|
| Length | `L₀ = a` (pore radius) | ~2 nm |
| Potential | `φ̃ = φ/V_T`, `V_T = RT/F` | 25.693 mV at 298.15 K |
| Concentration | `c̃ = c/c₀` | — |
| Diffusivity | `D₀` | 1.334 × 10⁻⁹ m² s⁻¹ |
| Velocity | `u₀ = εV_T²/(ηa)` | — |
| Pressure | `p₀ = εV_T²/a²` | — |
| Debye | `λ̃ = λ_D/a`, `λ_D² = εRT/(2F²c₀)` | λ̃ ∈ [0.088, 0.679] for a = 2 nm |
| Péclet | `Pe = εV_T²/(ηD₀)` | **0.386** at 298.15 K (η = 0.890 mPa·s) |

Debye lengths (1:1, 25 °C): 1.357 nm at 0.05 M, 0.304 nm at 1 M, **0.175 nm at 3 M**.

Follow with field-wise row scaling (`-ksp_diagonal_scale` or equivalent) so all diagonal Jacobian
blocks have O(1) norm.

---


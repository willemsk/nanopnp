---
type: Reference Settings
title: E. What we must replicate for a like-for-like comparison
---

## E. What we must replicate for a like-for-like comparison

Ordered by expected effect on the ionic-current QoI.

| # | Setting to match | Value | Why it matters |
|---|---|---|---|
| 1 | **TDS stabilisation** | streamline + crosswind on, crosswind = Do Carmo and Galeão, approximate residual, isotropic off | Adds a residual-based term to the transport operator that our unstabilised solve does not have; biases the current on any practical mesh |
| 2 | **Flow element pair + stabilisation** | P1+P1 with streamline + crosswind | Their pressure stabilisation is what makes equal-order legal; a Taylor-Hood P2/P1 solve is a *different* discretisation of the same PDE |
| 3 | **Convective term form** | Conservative form | Changes the assembled operator and the mass balance at coarse resolution |
| 4 | **Discretisation orders** | V quadratic, c quadratic, u/w/p linear | Directly sets the EDL resolution per element |
| 5 | **Wall-distance definition** | closest-point general extrusion onto the **pore surface only**, membrane excluded, Euclidean | Sets every wall correction; including the membrane would change EOF and current near the mouth |
| 6 | **Permittivity parameters** | `epsr_ms = 30.08`, `epsr_alpha = 11.5`, `epsr0 = 78.15` | See D3 — this is what was solved, whatever the ruling says |
| 7 | **Concentration clamps** | `cdf` argument clamped to [10⁻⁶ M, 5.3 M]; charge density clamped to `c ≥ 0` | Without them the fits extrapolate and Newton diverges at 5 M |
| 8 | **ε values** | pore 20, membrane 3.2 | Sets the fixed-charge screening |
| 9 | **Mesh resolution** | 0.05 nm max on the pore wall, growth 1.05, 0.1 nm in the pore domain, 0.001 nm global min, ~1.2 × 10⁵ triangles, min quality ≥ 0.64 | Comparable resolution, not identical elements |
| 10 | **Nonlinear strategy** | fully coupled, damping 0.2 → min 0.01, ≤ 100 iterations, rel. tol. 1e-6 | Same converged state; different paths are fine as long as the tolerance matches |
| 11 | **Continuation** | ramp `V_bias`, reuse previous solution | Determines which branch is found at high bias / low salt |
| 12 | **Current extraction** | variational boundary flux, integration order 4 | Cross-section integrals of the CG flux disagree at the percent level |
| 13 | **Steric flux weak form** | as printed in C.6, `α_i = k_i/(1 − Σ c_j v_j)` | Sign and prefactor as given; trap 2 of `.knowledge/00-orientation/02-the-five-things-most-likely-to-trip-you.md` |


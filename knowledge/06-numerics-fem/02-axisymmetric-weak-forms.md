---
type: Numerics
title: 2. Axisymmetric weak forms
description: The axisymmetric weak forms, the axis and the quadrature order that avoids
  NaN.
tags:
- numerics
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
verified:
- by: process:tests/tier1/test_stabilisation.py::test_ver41_element_size_is_about_93_per_cent_of_an_equilateral_edge
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_stabilisation.py::test_ver41_element_size_is_the_square_root_of_twice_the_element_area
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_axis_weight_order.py::test_num07_weight_order_on_example_05
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_axis_weight_order.py::test_num07_weight_order_on_the_coupled_manufactured_solution
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_poisson_layers.py::test_ver56_poisson_reproduces_the_three_layer_capacitor_to_round_off
  at: '2026-10-16T00:00:00Z'
---

## 2. Axisymmetric weak forms

`dV = 2πr dr dz`; the `2π` cancels and is dropped. `∇ = (∂_r, ∂_z)`.

**Poisson** (over all of `Ω`, including protein and membrane):
```
∫ ε ∇φ·∇v  r dr dz  =  ∫ (ρ_pore + F Σ z_i c_i) v  r dr dz  +  ∫_Γ σ_s v  r ds
```

**Nernst–Planck** (over `Ω_w` only), test `w`:
```
∫ [ −D_i∇c_i − z_i μ_i c_i ∇φ − D_i β_i c_i + u c_i ] · ∇w   r dr dz  =  0
```

**Stokes/NS** (over `Ω_w` only), with the cylindrical hoop-strain term:
```
∫ [ 2η ε̂(u):ε̂(v) + 2η u_r v_r / r²  −  p d̂iv v  −  q d̂iv u ]  r dr dz  =  ∫ f·v  r dr dz
d̂iv u = ∂_r u_r + u_r/r + ∂_z u_z
```

Verified algebra: `2η ε_θθ(u) ε_θθ(v) = 2η u_r v_r / r²`, and multiplying by the `r` weight leaves
`2η u_r v_r / r`, integrable because `u_r → 0` on the axis. The strong-form counterpart is the
`−u_r/r²` term that COMSOL hides inside its axisymmetric interface. **Omitting it is a silent
correctness bug** producing plausible but wrong flow fields.

> The published model uses the **variable-density** Axelsson formulation (three equations — see
> `knowledge/01-physics-epnpns/02-governing-equations.md#23-navierstokes-variable-density-and-viscosity`), not the constant-density Stokes above. Implement the variable-
> density system as the default to match the validated model, and constant-density Stokes as a
> flag. The `r`-weighting and hoop term apply identically.

### 2.1 The axis, `r = 0`

Impose **only** `u_r = 0` as essential. `∂φ/∂r = ∂c_i/∂r = ∂u_z/∂r = 0` are **natural** — the `r`
weight annihilates the boundary term. Imposing Dirichlet on `φ` or `c_i` at the axis is a common
and fatal error. Analysis lives in weighted spaces `H¹_1(Ω)` (Mercier & Raugel 1982; Bernardi,
Dauge & Maday) with standard convergence rates.

### 2.2 Quadrature — verified experimentally

It is tempting to assume Gauss rules on triangles never sample `r = 0`. **They do.** NGSolve's
order-2 triangle rule places all three points at edge midpoints — (0, ½), (½, 0), (½, ½) — so an
element with an edge on the axis is sampled exactly at `r = 0`. Reproduced on NGSolve 6.2.2606:

```
Integrate(gf*gf/(x*x)*x, mesh, order=2)  ->  nan
Integrate(gf*gf/(x*x)*x, mesh, order=3)  ->  correct
```

**Requirement:** assert integration order ≥ 3 on every form containing `1/r`, and keep a unit test
that integrates a known `1/r`-weighted quantity on an axis-touching mesh.

**The default order does not count the `r` weight [tested: tests/tier2/test_poisson_layers.py::test_ver56_poisson_reproduces_the_three_layer_capacitor_to_round_off].** NGSolve estimates an integrand's
order from its trial and test functions, not from coefficient functions such as `x`, so a
non-singular `r`-weighted term is integrated one order below its degree. At P2 the stiffness
`eps grad(u).grad(v) r` (degree 3) and the source `rho v r` (degree 3) are integrated at order 2.
Measured on NGSolve 6.2.2606 with a bare `BilinearForm`/`LinearForm` pair on the WP26 three-layer
capacitor (`tests/tier2/test_poisson_layers.py`: `r` in [0, 3], `z` in [0, 10] nm, membrane on
[4, 6] at eps 3.2/78.15, `rho_0 = -1e7 C m^-3`, 130 triangles at `maxh = 0.7`), whose exact
piecewise-quadratic solution P2 contains: max error 0.38 `V_T` (3 % of `max |phi~|`), largest on
the axis inside the membrane; with `bonus_intorder=1` on both terms, 1.1e-13. The planar forms and
a uniform-permittivity problem with no source are exact at the default. With uniform permittivity
and the source the error is 3.4e-2 `V_T`: the source is short too. `poisson` assembles with
`RADIAL_WEIGHT_ORDER = 1`; the coupled models keep the default (SPECIFICATION.md NUM-07 NOTE on the
`r` weight). Source: WP26 implementation session, 30 September 2026.

**What the extra order moves in the coupled models** **[tested: tests/tier2/test_axis_weight_order.py::test_num07_weight_order_on_the_coupled_manufactured_solution]** **[tested: tests/tier2/test_axis_weight_order.py::test_num07_weight_order_on_example_05]**. Measured through
`Measures.weight_extra_order` (0 against 1, added to every non-singular axisymmetric `volume` and
`surface` term) by `tests/tier2/test_axis_weight_order.py`, NGSolve 6.2.2606, stabilisation `none`:

| Case | At 0 → at +1 |
|---|---|
| VER-18 MMS, L2 error at `maxh` 0.1 nm | `c_Cl-` 4.61e-7 → 1.95e-7; `c_Na+` 6.33e-7 → 4.88e-7; `phi` 7.14e-6 → 7.03e-6; `u` 2.94e-6 → 2.88e-6; `p` 2.65e-4 → 2.41e-4. Finest-pair rates unchanged (about 3; `p` about 2.7); the coarse-pair rates of `c_Cl-` and `c_Na+` fall from 3.98 and 3.55 to 3.65 and 2.99, inflated at 0 by the quadrature error |
| Example 05, 0.5 M, +50 mV, reference mesh | States differ by 4.9e-7 relative. `I` 2.414877e-10 A and `G` 4.829754e-9 S move by 1.7e-12 relative, `t+` 0.3746647 by 1.3e-10, `Q_EOF` 2.3335e-21 m³/s by 7.6e-8. In-pore (lumen within -1.85 ≤ z ≤ 12.25 nm, element centroids): `<c_Na+>` 0.50292 M, `<c_Cl->` 0.49632 M, mobile charge 1.530 e (1.098 e within 0.5 nm of the wall), all by ≤ 1e-9 |

The example-05 change is real and not solver noise: each converged state is a root of its own form
(`|R|` 2.1e-11 and 1.8e-11 on the free dofs) and violates the other variant's at 7.3e-4. On the MMS
meshes (0.1–0.4 nm) the quadrature error is the same order as the discretisation error; on the
reference mesh (0.05 nm at the wall) it is invisible in every integrated quantity. A run of
`nanopnp mesh` inside pytest calls `logging.basicConfig(force=True)` and silences `--log-cli-level`;
the test restores the root handlers. Source: WP34, 4 October 2026.

### 2.3 `specialcf.mesh_size` is `sqrt(2|K|)`, and it evaluates pointwise **[tested: tests/tier1/test_stabilisation.py::test_ver41_element_size_is_the_square_root_of_twice_the_element_area]** **[tested: tests/tier1/test_stabilisation.py::test_ver41_element_size_is_about_93_per_cent_of_an_equilateral_edge]** {#23-specialcfmesh_size-is-sqrt2k-and-it-evaluates-pointwise}

On a 2D triangular element NGSolve's `specialcf.mesh_size` returns `√(2|K|)`, verified elementwise
against `Integrate(1, ...)` per element on a 14-element unstructured mesh of the unit square to a
maximum relative deviation of **2.4 × 10⁻¹⁵**. For the equilateral triangle of side `a` that is
`a√(√3/2) = 0.9306 a`, so the measure sits 7 % below the edge length — inside any stabilisation
tuning constant, and constant across element shapes to within the shape factor.

It also evaluates at a **located point**, `mesh(x, y)`, returning the containing element's value
rather than only working inside a quadrature loop. That is what lets a cell-Péclet diagnostic be a
sampler over the P2 nodal set rather than an element loop.

Both facts matter because every `τ` in `physics/stabilisation.py` is defined against this
convention: a change upstream would retune the whole stabilised mode with no diagnostic, which is
why `tests/tier1/test_stabilisation.py` measures it rather than assuming it (VER-41).

---


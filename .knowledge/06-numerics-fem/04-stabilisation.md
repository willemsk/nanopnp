---
type: Numerics
title: 4. Stabilisation
---

## 4. Stabilisation

Electromigration is advection with `b_i = z_i D_i ∇φ̃ / L₀`. Cell Péclet
`Pe_h = ½ |z_i| |∇φ̃| h̃`. In the double layer `|∇φ̃| ≈ |ζ̃|/λ̃_D`, so resolving it with 5 elements
(`h̃ = λ̃_D/5`) gives `Pe_h = |z_i||ζ̃|/10` — below 1 for a monovalent electrolyte whenever
|ζ| ≲ 257 mV, comfortably satisfied here.

Caveat: `Pe_h < 1` is a *heuristic sufficient condition* from 1D linear constant-coefficient
advection–diffusion on a uniform mesh. It is a design rule, not a proof for this system.

> **SETTLED: the reference ran WITH stabilisation.** From the COMSOL model report — Transport of
> Diluted Species: streamline diffusion on, crosswind diffusion on, crosswind type *Do Carmo and
> Galeão*, equation residual *Approximate residual*, isotropic diffusion off, convective term in
> conservative form. Laminar Flow: streamline on, crosswind on, isotropic off, **P1+P1** elements
> (which is why that interface needs it). Crosswind assembles at integration order 6, streamline
> at 4. Pseudo-time stepping is present but gated off (`spf.usePseudoTimeStepping = 0`).
>
> Consequence: an unstabilised solve is a *different discretisation of the same PDE*. Per-cent-level
> disagreement with the published currents is an implementation difference, not a bug. Provide a
> matching stabilised mode before setting any tight cross-comparison tolerance.
> → `09-comsol-reference-settings.md`.

**Policy:** no stabilisation on the production mesh; SUPG available as a flag for coarse
continuation meshes, off for the final solve (SUPG biases the current QoI and breaks Jacobian
symmetry). If needed, use Chaudhry, Comer, Aksimentiev & Olson (*Commun. Comput. Phys.* **15**,
93, 2014): `σ_± = (h_τ/2‖b_±‖)·ψ(Pe_τ)`, `ψ(q) = min(q,1)` — they report spurious *negative
concentrations* near charged nanopore walls with plain Galerkin.

### 4.1 The mode as built

Three named models, never a code branch: `none` assembles nothing, `supg` the streamline term
alone, `reference` NUM-14's whole setting table. The advective velocity is the flux bracket itself,

```
b̃_i = z_i μ̃_i ∇φ̃ + D̃_i β̃_i − Pe ũ        so that   J̃_i = −[ D̃_i ∇c̃_i + b̃_i c̃_i ]
```

term for term — note that the *true* advective velocity is `−b̃_i`; the sign is carried by the
negated bracket. Every parameter below is evaluated at the **iterate**, never at the trial function
(COMSOL's `nojac()`), so none of `max(0, ·)`, `1/‖b̃_i‖` or `1/‖∇c̃_i‖` reaches the Jacobian.

**Streamline.** `τ_i = (h_K/2‖b̃_i‖)·ψ(Pe_K)`, `ψ(q) = min(q,1)`, `Pe_K = ‖b̃_i‖h_K/(2D̃_i)`. Written
as the two branches rather than as a `min`, because the diffusive branch `h_K²/(4D̃_i)` is the finite
limit of a `0/0`; the two agree at `Pe_K = 1`, so `τ_i` is continuous at the crossover.

**Crosswind (Do Carmo–Galeão type).** `ν_K = max(0, C_cw h_K‖R̃_i‖/(2‖∇c̃_i‖) − D̃_i)` with
`C_cw = 1`, acting through `P_b = I − b̂⊗b̂`. Both terms enter with a **minus**, the sign of the
Galerkin diffusion they augment in this flux-form residual. The residual is *approximate* (NUM-14):
every second derivative of a trial field is dropped, leaving `R̃_i = b̃_i·∇c̃_i − s̃_i`.

### 4.2 The ratio SUPG adds is `Pe_K²`, exactly **[verified]** {#42-the-ratio-supg-adds-is-pe_k2-exactly}

Below unit Péclet `τ_i = h_K²/(4D̃_i)`, so the artificial streamline diffusivity `τ_i‖b̃_i‖²` against
the physical `D̃_i` is

```
τ_i‖b̃_i‖² / D̃_i  =  ( ‖b̃_i‖ h_K / 2D̃_i )²  =  Pe_K²
```

— independent of every material parameter. Put NUM-30's `h = λ_D/5` into it with
`‖∇φ̃‖ ≈ |ζ̃|/λ̃` inside the double layer and `Pe_h = |z_i||ζ̃|/10`, independently of concentration:
at 1 M, `λ_D = 0.304 nm`, `h̃ = 0.0304`, `‖∇φ̃‖ = 19.7`, `Pe_h = 0.300`; at 0.05 M,
`λ_D = 1.357 nm`, `h̃ = 0.1357`, `‖∇φ̃‖ = 4.42`, `Pe_h = 0.300`. The added artificial diffusion is
therefore **`ζ̃²/100`** — 4 % at `ζ̃ = 2`, 9 % at `ζ̃ = 3`, 16 % at `ζ̃ = 4`. In the pore lumen the
gradient is set by the bias over the pore length (`‖∇φ̃‖ ≈ 1.2` at 200 mV over 13 nm), so
`Pe_h ≈ 0.03` and the added diffusion is 0.09 %: the stabilisation is a double-layer effect by three
orders of magnitude. Applying PHY-14's `μ̃_i/D̃_i` (1.2–1.7 between 0.15 M and 3 M) scales every
`Pe_h` by 0.59–0.83 and every added diffusion by its square.

### 4.2.1 The SUPG bias on the current is `S_i(ψ)` almost exactly **[tested]** {#421-the-supg-bias-on-the-current-is-s_i-almost-exactly}

Under a stabilisation mode the assembled residual carries the stabilisation term, so the NUM-25
reaction flux carries it too; the NUM-24 indicator form must therefore add
`2π F z_i S_I S_i(c̃; ψ)` or the two routes differ by that quantity. That correction, reported per
species as `stabilisation_current_A`, is also the **bias on the current**, and the two facts are not
independent: the *bare* `∫ J̃_i·∇ψ` integral turns out to be nearly mode-independent, so the whole
difference between a stabilised and an unstabilised current lives in the added term.

Measured on the VER-11 benchmark pore — 2 nm lumen, 13 nm membrane, 25 nm reservoir, 0.5 M,
+50 mV, −0.05 C/m², `maxh` 5.0 nm, `wall_h` 0.4 nm, `max Pe_K = 0.775`:

| Quantity | `none` | `reference` |
|---|---|---|
| bare `∫ J̃_i·∇ψ` route, total | 2.5288 × 10⁻¹⁰ A | 2.5327 × 10⁻¹⁰ A |
| `S_i(ψ)` contribution, total | 0.0 exactly | −1.9059 × 10⁻¹¹ A |
| reported current (either route) | 2.5288 × 10⁻¹⁰ A | 2.3421 × 10⁻¹⁰ A |

So: the bare integrals differ by 0.15 %, the two currents by 7.38 %, and `S_i(ψ)` is 8.14 % of the
stabilised current. The single-run number reproduces the two-run difference to `1.6 × 10⁻³` of the
current — which is why the bias can be reported from one solve instead of from a pair, and why
subtracting it is a meaningful operation rather than a coincidence at one operating point.

`none` contributes `0.0` exactly, not approximately: that mode assembles no term, so the integral is
never taken.

8 % rather than the 0.09 % of §4.2's *lumen* estimate or the `ζ̃²/100` of its double-layer one,
because this mesh is sized for the solve and not for NUM-30: at `Pe_K = 0.775` the added-diffusivity
ratio `Pe_K²` is 0.60, not 0.09. The closed form is unchanged; only the substitution is.

### 4.3 The crosswind switches itself off at `C_cw Pe_K ≤ 1` **[verified]** {#43-the-crosswind-switches-itself-off-at-c_cw-pe_k-1}

In production `s̃_i = 0`, so `R̃_i = b̃_i·∇c̃_i` exactly and Cauchy–Schwarz gives
`‖R̃_i‖ ≤ ‖b̃_i‖‖∇c̃_i‖`, whence

```
ν_K  ≤  D̃_i max(0, C_cw Pe_K − 1)
```

Two consequences worth having in writing. The term is **identically zero wherever
`C_cw Pe_K ≤ 1`** — everywhere on a mesh meeting NUM-30, so switching `reference` on cannot change a
production answer through this term. And it is bounded above by the diffusivity that brings the
effective cell Péclet number to `1/C_cw`, so it cannot run away. The bound also makes
"crosswind-active ⊆ Péclet-exceeding" a *containment* rather than an equality, which is the
assertable form of "the same elements the NUM-12 warning names": the warning is a point sample and
the term is an element quantity, so the two fractions are not comparable but the inclusion is.

### 4.3.1 Measured: where the mode earns its place, and where it does not **[tested]** {#431-measured-where-the-mode-earns-its-place-and-where-it-does-not}

The claim `reference` exists to support is that plain Galerkin loses concentration positivity on an
under-resolved double layer and the stabilised mode does not. It is true, and it is true of a
**band** of configurations rather than of the coarse-mesh regime as a whole. On a 2 nm/13 nm
cylindrical pore, `maxh` 5 nm, 0.5 M, +50 mV, climbing stages 1–5 of the NUM-18 ladder:

| `wall_h` | σ (C/m²) | elements | `max Pe_K` | `none` | `reference` |
|---|---|---|---|---|---|
| 1.0 | −0.12 | 313 | 4.712 | NUM-17 gate, `Na+ = −72.9` | converges, 126 iterations |
| 0.8 | −0.12 | 346 | 3.159 | converges | converges |
| 0.8 | −0.08 | 346 | 2.088 | converges | converges |
| 0.6 | −0.08 | 481 | 1.616 | converges | converges |

So `Pe_K > 1` is necessary and nowhere near sufficient: the mesh is under-resolved from `wall_h`
0.6 nm up and plain Galerkin still converges to 3.2. Push the other way, onto a 1.5 nm pore at
0.05 M and −0.30 C/m² with `wall_h` 1.0 nm, and *both* modes lose positivity — `reference` reaching
`Cl− = −0.385` where `none` reaches `−0.826`, so the term halves the undershoot without removing it.
Between the two lies the band the claim holds in. A benchmark asserting "the stabilisation fixes
positivity" therefore has to pin its configuration, and one that drifts coarser will start failing
for a reason that is not a defect.

Two figures from the same runs. On the 313-element mesh the crosswind is active at 125 of 1 344
fluid samples for `Na+` and 123 for `Cl−`, with peak `ν_K` of 3.71 and 5.61, and at **zero** samples
with `Pe_K ≤ 1` — the §4.3 containment, asserted sample by sample. Refine to `wall_h` 0.2 nm
(1 491 elements, `max Pe_K = 0.457`) and the assembled crosswind linear form is `0.000e+00` in every
entry, for both species.

With corrections off, `Pe_K` is **the same for both species of a 1:1 salt** to every digit: the
classical model satisfies the Einstein relation exactly, so `Pe_K = |z_i| ‖∇φ̃‖ h_K / 2` with the
`μ̃_i/D̃_i` ratio cancelled. The per-species split in the NUM-12 record only becomes informative once
PHY-14's corrections are on.

### 4.3.2 The stabilisation bias falls at `O(h²)`, approaching it from below **[tested]** {#432-the-stabilisation-bias-falls-at-oh2-approaching-it-from-below}

`|I_reference − I_none| / |I_none|` on the pore above at 0.5 M, +50 mV, −0.05 C/m², refining only
the wall spacing (the stabilisation is a double-layer effect by three orders of magnitude, §4.2, so
`maxh` stays at 5 nm):

| `wall_h` (nm) | elements | difference |
|---|---|---|
| 0.8 | 346 | 2.00 × 10⁻¹ |
| 0.4 | 708 | 7.38 × 10⁻² |
| 0.2 | 1 491 | 1.99 × 10⁻² |

Rates **1.441** then **1.889**: the `Pe_K²` scaling of §4.2 gives `O(h²)` and the sequence reaches it
from below, so the coarse interval is pre-asymptotic. A benchmark gating this on a fixed rate of 1.8
fails its first interval for no defect; gate the *monotone fall* and report the rate.

That the difference vanishes at all is the substantive result: a stabilisation bias surviving
refinement would make `reference` a different model rather than a different discretisation, and the
§7.4 attribution would be subtracting something that never goes away.

### 4.3.3 On a stable element pair the flow terms cost an order, and 20× the time **[tested]** {#433-on-a-stable-element-pair-the-flow-terms-cost-an-order-and-20-the-time}

Measured on VER-18's manufactured solution — a 2 × 4 nm cylinder, P2 potential, concentration and
velocity, P1 pressure, `maxh` 0.4/0.2/0.1 nm, 0.1 M, every correction off. `max Pe_K ≤ 0.084` there,
so by §4.3 the crosswind viscosity is **identically zero** (sampled, both species) and `supg` and
`reference` differ by the flow GLS and grad-div pair alone.

| Mode | `c_Na+` L² at 0.4 / 0.2 / 0.1 nm | rate | velocity L² at 0.4 nm | Newton | wall clock at 0.4 / 0.2 nm |
|---|---|---|---|---|---|
| `none` | 6.4131e−05 · 5.4653e−06 · 6.3266e−07 | 3.55, 3.11 | 2.7567e−04 | 5 | 0.8 s · 4.7 s |
| `supg` | 3.7397e−04 · 9.2731e−05 · 2.2549e−05 | **2.01, 2.04** | 2.7617e−04 | 5 | 7.2 s · 25.1 s |
| `reference` | 3.1107e−03 · 1.5722e−03 · — | **0.98** (`Cl−` 0.70) | 3.4483e−02 | 31 | 126 s · 436 s |

Three things follow. The streamline term on its own hits NUM-14's predicted 2 to within 2 %, so the
approximate-residual prediction is confirmed where it was made. The flow pair takes the mode to
**first order**: its momentum residual drops the viscous second derivative on the same rule, and
PSPG's consistency error enters the continuity equation weighted by `τ_m ≈ h̃²/4η̃` against a test
gradient, which is `O(h)` rather than `O(h²)`. And the velocity error — which no transport term can
reach, `supg` moving it by 0.2 % — rises by a factor of **125**, which is what makes the attribution
a measurement rather than an inference.

The flow equation-residual setting is *not recorded* in the reference's model report (NUM-14's
table), so this approximation is ours; and the reference ran its flow stabilisation on a P1/P1 pair
(RSK-18), where the term is what makes the pair admissible. No configuration the reference itself ran
loses an order. The combination that does — the full mode on a Taylor–Hood pair — exists only as the
middle rung of the §7.4 attribution ladder, and `Δ_stab` measured there is the flow pair's, not the
transport term's.

The 20× wall clock is two effects: the streamline term alone costs 8× per solve at unchanged Newton
count, which is assembly, and the flow pair takes Newton from 5 iterations to 31, which is the lagged
`τ_m` — relagging a large parameter at each iterate turns Newton into a fixed-point iteration in `τ`
and the contraction weakens as `τ` grows.

Most of that assembly cost is the **manufactured source**, not the streamline term itself **[tested]**.
With the setup above (5 Newton iterations in every case), a solve at `maxh` 0.4, 0.2 and 0.1 nm took
0.4 s, 2.0 s and 8.0 s in `none` and 6.6 s, 27.6 s and 107.5 s in `supg`. At 0.2 nm, withholding
`s̃_i` from `R̃_i` (§4.3.4) brings `supg` from 30 s down to 5.0 s. The sympy-generated source
polynomial sits inside the nonlinear SUPG integrand, and `AssembleLinearization` carries that whole
constant subtree through every quadrature point. `CoefficientFunction.Compile()` (graph flattening
only, with no C++ JIT, so CON-07 is untouched) recovers only 20 % (37 s to 29.6 s at 0.4 plus 0.2 nm)
and leaves the errors identical to 13 digits. This cost belongs to the MMS benchmark. A production
run carries no manufactured source, so it does not pay it.

**The cost is the source's *representation*, and it is removed in the harness [tested].** `_reduce`
puts each species source over one common denominator (`cancel(together(·))`) so the removable `1/r`
cancels. The result is about 3,800 operations. `lambdify` writes it as a tree in which every
repeated subexpression is its own node, so NGSolve evaluates all of them at every quadrature point:
one `Integrate` of the `c_Na+` source at order 12 on the 0.1 nm mesh takes 1.08 s, against 0.001 s
for the exact concentration. `CoefficientFunction.Freeze()` changes nothing, bitwise or in time, so
automatic differentiation is not the cost. Built with `lambdify(..., cse=True)` and then
`Compile()`, the repeated subexpressions are shared and each is evaluated once: 0.057 s (19×), with
the source values moving by 1.5e-15 relative. `to_coefficient_function` does this. VER-42's
three-level `supg` fixture went from 208 s to 26 s, and `none` from 11 s to 7.5 s (serial, one BLAS
thread, NGSolve 6.2.2606). The errors equal the recorded ones to every printed digit (`supg`
`c_Na+` 3.7396590029e-04, 9.2730603940e-05, 2.2549195484e-05; rates 2.0118, 2.0400), and every
Tier-1 and Tier-2 test passes unchanged. The weak forms are untouched, so the §4.3.4 footprint test
discriminates exactly as before. Source: test-suite timing work, 30 September 2026.

Two things measured and rejected. First, `TaskManager()` makes the same solve 3.9× faster on four
idle cores (158 s to 41 s at 0.1 nm). But the push gate runs four workers on four cores, so no core
is idle. Second, the form's derivative of the source is identically zero, so freezing it is exact
but buys nothing.

### 4.3.4 A stabilisation residual missing its source switches the term **off** **[tested]** {#434-a-stabilisation-residual-missing-its-source-switches-the-term-off}

`R̃_i = b̃_i·∇c̃_i − s̃_i`, and on the exact solution the two sides balance the diffusion that was
dropped: `b̃_i·∇c̃_i − s̃_i = ∇·(D̃∇c̃_i)`. Withholding `s̃_i` — the easiest wiring mistake in the
module — is usually described as making the term inconsistent. On a **diffusion-dominated** problem
it does the opposite. At `Pe_K ≤ 0.084` the source *is* the residual, so dropping it nearly erases
the term: the `supg` rate rises from 2.01 towards `none`'s 2.91, and the coarse-level error falls
from 3.7397e−04 to 6.8278e−05 against `none`'s 6.4131e−05.

A rate floor with no ceiling passes that. The discriminating quantity is the term's **footprint**,
`error(mode)/error(none) − 1` on the same mesh:

| Field, `maxh` | intact | source withheld | ratio |
|---|---|---|---|
| `c_Na+`, 0.4 nm | 4.831 | 0.065 | 74.7 |
| `c_Na+`, 0.2 nm | 15.967 | 0.666 | 24.0 |
| `c_Cl−`, 0.4 nm | 2.985 | 0.014 | 212.2 |
| `c_Cl−`, 0.2 nm | 15.768 | 0.198 | 79.5 |

Two orders of separation, and no dependence on which direction the rate moves.

### 4.4 At `Re = 6 × 10⁻⁴` the flow stabilisation is pure PSPG **[verified]** {#44-at-re-6-104-the-flow-stabilisation-is-pure-pspg}

`NondimensionalCoefficients.reynolds = ρ₀ε V_T²/η₀²` is length-independent and equals
**6 × 10⁻⁴**. In the Shakib parameter with `h̃ ≈ 0.03` and `‖ũ‖ ~ 1`:

```
(2 Re ρ̃‖ũ‖ / h_K)  =  2 · 6e−4 / 0.03  =  4.0e−2
(4 η̃ / h_K²)       =  4 / 9.0e−4       =  4.4e+3
τ_m = [ (4.0e−2)² + (4.4e+3)² ]^(−1/2) =  2.25e−4  =  h_K²/(4η̃) to five figures
```

The convective branch is **five orders** below the viscous one, so the `τ_m ∫∇q·∇p̃` piece inside
the GLS operator is the whole of what makes an equal-order pair legal. The grad-div parameter
`τ_c = Re ρ̃‖ũ‖h_K/2 = 9 × 10⁻⁶` is numerically inert by the same margin. Both are assembled
regardless, so a later case at a Reynolds number this project does not yet reach is not silently
running a Stokes-only stabilisation.

The two GLS rows do **not** share an orientation. The velocity row is the coercive one and takes a
`+`; the continuity row is written `−∫ q ρ̃ d̂iv ũ`, which is minus the orientation in which
`+τ_m ∫∇q·∇p̃` is the stabilising pressure block, so the pressure-test piece takes a `−`. The saddle
structure is `[[A, B], [Bᵀ, −C]]`. One signed term for both stabilises one row and destabilises the
other.

---


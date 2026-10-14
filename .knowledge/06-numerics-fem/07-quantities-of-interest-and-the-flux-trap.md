---
type: Numerics
title: 7. Quantities of interest — and the flux trap
---

## 7. Quantities of interest — and the flux trap

**Do not compute the ionic current by integrating the CG flux over an interior cross-section.**
CG fluxes are not pointwise conservative; the current differs between cross-sections by
percent-level amounts, **which can exceed the physical rectification signal at low bias**. This is
the most likely route to a subtly wrong published number.

Two correct routes; implement both and CI-check that they agree.

**(a) Domain/indicator form — recommended.** Smooth `ψ` with `ψ = 1` in cis, `0` in trans:
```
I     = F Σ_i z_i ∫_Ω J_i·∇ψ  r dr dz
Q_EOF =           ∫_Ω u·∇ψ    r dr dz
```
Superconvergent and cross-section independent.

**The sign is the one that references the current to the grounded cis electrode. [verified]**
By the divergence theorem with `∇·J_i = 0`, `∫_Ω J_i·∇ψ r dr dz = ∮_{Γ_cis} J_i·n` with `n` the
outward normal, so with `ψ = 1` on cis the integral *is* the efflux through the cis cap. With `φ = 0`
on cis and `φ = V_bias` on trans (§5.2.2 of the specification), a positive bias drives positive
charge trans → cis, i.e. out through cis, so the plus sign gives `G = I/V_bias > 0` — which VER-17
asserts. A minus references the trans electrode instead, negates every conductance, *and* negates
this route relative to (b) taken on the same electrode, so the two would never agree. Printed forms
of this expression carry a minus; that pairs with the trans electrode, not with `ψ = 1` on cis.

**ψ must be built on the fluid domain alone. [tested]** The two routes agree because `ψ` differs
from the (b) boundary indicator by a function vanishing on both electrodes, hence by a legitimate
test function of the converged residual — an identity that needs `ψ` to be *exactly* 1 and 0 there.
Interpolated over the whole mesh it is not: the membrane spans the transition band, and an element
straddling the band shares its corner vertex with a reservoir cap. Measured on a charged pore at
0.5 M, ±50 mV: `ψ` reaches 7.7 × 10⁻³ at the trans cap, and the route agreement degrades from
3.8 × 10⁻⁶ to 6.5 × 10⁻⁴ — a factor of 170, and still inside a 10⁻³ tolerance while being a real
error. Restricting the interpolation to the fluid removes the membrane, and with it the only path
from the band to a cap; the leak is then identically zero.

**Use a C¹ transition, not a linear ramp.** `S(t) = t²(3 − 2t)` has `S'(0) = S'(1) = 0`, so `∇ψ` is
continuous at both ends of the band and the integrand has no jump inside an element.

**(b) Variational reaction flux.** Evaluate the assembled residual against a test function equal
to 1 on a Dirichlet electrode (Hughes, Engel, Mazzei & Larson, *J. Comput. Phys.* **163**, 467,
2000 — "the continuous Galerkin method is locally conservative").

**Derived QoIs.** `t₊ = I₊/(I₊ + I₋)` from the same `ψ` integrals. Rectification
`α = |I(+V)|/|I(−V)|`. Conductance `G = I/V_b`.

### 7.1 Measured: the two routes agree, and the band does not matter **[tested]** {#71-measured-the-two-routes-agree-and-the-band-does-not-matter}

Charged pore (`a` = 2 nm, `L` = 13 nm, σ_s = −0.05 C/m²), 0.5 M, classical PNP, ±50 mV, reached
through the continuation ladder.

| quantity | measured |
|---|---|
| route agreement, total current | 3.8 × 10⁻⁶ at +50 mV, 4.0 × 10⁻⁶ at −50 mV |
| ... at 3 400 to 7 300 DOF | 3.8 × 10⁻⁶ throughout — set by the Newton residual, not the mesh |
| route agreement on VER-17's uncharged pore | 5 × 10⁻⁷ |
| current across five `ψ` bands (moved ±2 nm, widths 0.3–0.98 of the lumen) | spread 9 × 10⁻⁶ |
| spurious rectification on a pore symmetric in `z` | `RR` = 1.000021 |

The last row is the one that matters for RSK-03. `CylindricalPoreGeometry` cannot rectify — it is
symmetric about `z = 0` — so any `RR ≠ 1` it reports is manufactured by the extraction. A
cross-section integral of a non-conservative CG flux is exactly an extraction whose error depends on
the direction of the flux, which is how a percent-level flux error becomes a fabricated
rectification signal.

**Maxwell–Hall, measured. [tested]** Uncharged pore at 1 M, classical PNP,
`G = σ[L/(πa²) + 1/(2a)]⁻¹` with `σ = F Σ z_i² μ_i⁰ c_i` = 12.64 S/m: 0.15 % error at a 50 nm
reservoir and 0.39 % at 100 nm, with `G` moving 0.23 % between them, so the benchmark measures the
discretisation and not the truncation of the domain. The transport number comes out 0.3963, the
NaCl value `D_Na/(D_Na + D_Cl)`. This is the only Tier-2 benchmark that pins an *absolute* current,
so it is what verifies the `2π` convention and the NUM-09 current scale `F D₀ c₀ a`; route agreement
alone would not notice both routes being scaled by the same wrong constant.

**Force on an embedded body.** `F = ∮_S (T_M + T_H)·n dS` with `T_M = ε(E⊗E − ½|E|²I)` and
`T_H = −pI + η(∇u + ∇uᵀ)`, but **evaluate in domain form** for the same superconvergence reason:
`F_z = −∫_Ω (T_M + T_H) : ∇w dV` with `w` a smooth extension of `e_z` from the body.

> **No code or field data to regress against.** The thesis's trapping work used equilibrium APBS
> Poisson–Boltzmann on a coarse-grained bead model plus a 1D analytic rate model, with no
> Maxwell/hydrodynamic stress integral and no computed force profile. The one published continuum
> force computation, Angew. Chem. 2022 (PlyAB + haemoglobin), evaluates exactly this tensor
> framework, but its simulation details sit in a Supporting Information that was not retrievable;
> the main-text values are the regression targets of `.knowledge/05-analyte-and-forces/11-correction-continuum-force-computation.md#106-validation-targets-plyab-hb`.
> Consequence: verify the analyte force first against **analytic** benchmarks
> (Smoluchowski/Hückel electrophoretic mobility limits, Stokes drag on a sphere, Maxwell stress on
> a sphere in a uniform field), then against those published targets.

**Pore-averaged quantities.** The thesis's pore averages appear to omit the `2πr` Jacobian while
being described as volume averages (flagged in `.knowledge/04-clya-geometry-and-charge/index.md`). Any regression
target that is a pore average must state which convention it uses.

### 7.1.1 Measured: with the wall corrections on, route agreement *is* a mesh statement **[tested]** {#711-measured-with-the-wall-corrections-on-route-agreement-is-a-mesh-statement}

§7.1's "3.8 × 10⁻⁶ throughout — set by the Newton residual, not the mesh" was measured on
**classical PNP**, where every coefficient is constant. It does not carry over to ePNP-NS. The same
pore (`a` = 2 nm, `L` = 6 nm, reservoir 10 nm), 0.1 M NaCl, +20 mV, `willems2020_nacl` corrections
with `wall: true` on diffusivity, mobility and viscosity, `default_ladder`, stabilisation `none`,
`ψ` band ±2.4 nm, P2:

| mesh (`maxh`/`wall_h`, nm) | elements | ndof | NUM-25 reaction (A) | NUM-24 indicator (A) | relative difference |
|---|---|---|---|---|---|
| 4.0 / 1.0 | 124 | 1 232 | 8.7622 × 10⁻¹¹ | 1.46142 × 10⁻¹⁰ | **4.00 × 10⁻¹** |
| 2.0 / 0.5 | 257 | 2 408 | 2.93993 × 10⁻¹¹ | 2.94022 × 10⁻¹¹ | 9.63 × 10⁻⁵ |
| 1.0 / 0.25 | 793 | 7 357 | 2.61972 × 10⁻¹¹ | 2.61972 × 10⁻¹¹ | 1.56 × 10⁻⁶ |

The coarsest row converges — Newton reports no complaint, the gates pass, and both routes return a
plausible current — and the two routes disagree by 40 %, five hundred times NUM-26's 10⁻³. The cause
is resolution of the wall functions, not of the fields: `1 − exp(−6.2(d̄ + 0.01))` rises over a
tenth of the pore radius, and on the 124-element mesh the PHY-02 distance field carries 273 degrees
of freedom in total. The reaction flux and the indicator form disagree because they sample that
coefficient differently — the residual on the constrained `cis` dofs, against `∇ψ` over the fluid.

**The mechanism is sharper than "under-resolved", and it is a sign error the field commits on its
own [tested].** The P2 Varadhan distance field *undershoots below zero* at the re-entrant corner of
the pore mouth (`r ≈ 2.0`, `z ≈ ±3.0`), and `FittedCorrection.evaluate` clamps the concentration
driver but not `d`. A negative `d` puts `1 − exp(−6.2(d + 0.01))` below zero, so the diffusivity and
mobility factors change sign in that neighbourhood: ions are driven *up* their own gradient there.
Measured on the same pore, sampling the fluid domain:

| mesh (`maxh`/`wall_h`, nm) | elements | fluid area with `d < 0` | min `d` (nm) | min `f^w_D` | samples with `f^w_D < 0` |
|---|---|---|---|---|---|
| 4.0 / 1.0 | 124 | 2.186 % | −0.9913 | −437.7 | 8.257 % |
| 2.0 / 0.5 | 257 | 0.687 % | −1.2347 | −1983.1 | 2.373 % |
| 1.0 / 0.25 | 793 | 0.101 % | −0.9628 | −366.8 | 0.264 % |
| 0.5 / 0.125 | 2 618 | 0.000 % | +0.0079 | +0.1 | 0.000 % |

The undershoot is a genuine property of the discrete field and not an export artefact: the same
negative values reach the IF-07 export and the correction chain alike. It vanishes by `maxh` 0.5 nm
on this toy pore, and WP8's ClyA reference mesh (44 316 triangles) is far finer than that
everywhere, so production runs are expected clean.

**Closed out under WP11: PHY-02's clamp and NUM-34's gate, and neither alone. [tested]**
`FittedCorrection.evaluate` now clips `d̄` at zero before either wall form reads it, and
`solve/stage.py` gates `min d̄ ≥ −1 × 10⁻³ nm` over the fluid once per solve wherever a wall
correction is active. The arithmetic behind the threshold is in `SPECIFICATION.md` NUM-34.

**The transition is a regime change, not a gradient, and `wall_h` alone decides it. [tested]**
Measured on the same toy pore, sampling the fluid at the P2 nodal set the NUM-17 gates walk:

| `maxh` / `wall_h` (nm) | elements | min `d̄` (nm) | fraction of samples < 0 |
|---|---|---|---|
| 4.0 / 1.0   | 124 | −0.9401 | 9.75 % |
| 6.0 / 0.6   | 199 | −1.4557 | 11.94 % |
| 5.0 / 0.4   | 354 | −1.0800 | 0.31 % |
| 2.0 / 0.5   | 257 | −1.2377 | 2.14 % |
| 1.0 / 0.25  | 793 | −0.9749 | 0.31 % |
| **4.0 / 0.35** | **392** | **+9.48 × 10⁻⁶** | **0** |
| 4.0 / 0.3   | 461 | +7.80 × 10⁻⁶ | 0 |
| 4.0 / 0.25  | 529 | +5.96 × 10⁻⁶ | 0 |
| 2.0 / 0.15  | 956 | +4.00 × 10⁻⁶ | 0 |
| 6.0 / 0.09  | 1 539 | +2.47 × 10⁻⁶ | 0 |

`maxh` barely moves the answer — 4.0/0.35 gives 392 elements against 2.0/0.35's 419, and both give
`+9.5 × 10⁻⁶` — while `wall_h` moves it from −1.08 nm to +9.5 × 10⁻⁶ nm across a single step from
0.4 to 0.35. Two consequences: the coarsest admissible wall spacing on this geometry is
**0.35 nm**, and a test that wants a cheap mesh with the corrections on should coarsen `maxh` and
leave `wall_h` alone.

Note also that the residual `Set` leaves behind here is a few times `10⁻⁶` nm and *positive*, two
orders inside NUM-34's threshold — the "few times `10⁻⁴` with a platform-dependent sign" of §8.1
below is the unzeroed-projection case, which `physics/distance.py` does not produce.

**The clamp alone would have been worse than nothing, and this is the measurement that says so.
[tested]** With the driver clamped, the toy pore at 0.1 M and +20 mV gives:

| `maxh` / `wall_h` (nm) | min `d̄` (nm) | current (A) | NUM-26 route difference |
|---|---|---|---|
| 4.0 / 1.0  | −0.94 | 1.539 × 10⁻¹¹ | 5.5 × 10⁻² |
| 4.0 / 0.5  | −1.2  | 2.303 × 10⁻¹¹ | **2.6 × 10⁻⁵** |
| 2.0 / 0.5  | −1.24 | 2.204 × 10⁻¹¹ | **3.0 × 10⁻⁵** |
| 4.0 / 0.35 | +9.5 × 10⁻⁶ | 2.6468 × 10⁻¹¹ | 5.9 × 10⁻⁶ |
| 2.0 / 0.35 | +9.5 × 10⁻⁶ | 2.6514 × 10⁻¹¹ | 6.0 × 10⁻⁶ |
| 2.0 / 0.25 | +6.0 × 10⁻⁶ | 2.6538 × 10⁻¹¹ | 1.6 × 10⁻⁶ |

The `wall_h` 0.5 nm rows are the ones that matter. They **pass NUM-26 comfortably** — forty times
inside the tolerance — and their current is 13 to 17 % below the resolved value. Removing the sign
inversion removed the only signal an unresolved wall had: unclamped, the 124-element row disagreed
between the routes by 40 % (§7.1.1's original table) and the 257-element row by 9.6 × 10⁻⁵. So the
clamp turns "loudly wrong" into "quietly wrong" wherever the field is genuinely negative, and
NUM-34 is what turns it back into "refused". `tests/tier2/test_current_routes.py` asserts exactly
this pair of facts about the 0.5 nm mesh.

Two consequences worth keeping:

- **NUM-26 is a resolution diagnostic as well as an extraction check.** A run that fails it with
  corrections on is more likely under-resolved at the wall than wrong in its extraction, and the
  refinement to look at is `wall_h`, not `maxh`.
- **A mesh sized for a classical run is not sized for the corrected one.** Any correction-on test
  that asserts a current needs the route agreement asserted with it, or it is measuring the mesh.

### 7.1.2 Measured: a reassembled residual reproduces the live one bit for bit **[tested]** {#712-measured-a-reassembled-residual-reproduces-the-live-one-bit-for-bit}

The NUM-25 route needs `ModelSolution.residual`, which a state loaded from disk does not have. Built
by re-running the rung construction against the **stored** wall-distance coefficient vector, the
restored residual gives `reaction_flux_currents` identical to the live solution's in every bit —
`{'Na+': 1.4334969509489461e-11, 'Cl-': 2.1835946796916437e-11}` from both, on the 124-element mesh
above with corrections off. Reassembly is therefore exact, and the storage of the distance vector is
what makes it so: the screened-Poisson solve behind that field is not bit-reproducible across
library versions, so a re-solved field would give a different operator with no diagnostic.

### 7.2 The force on an embedded body: three routes, and the term NUM-28 hides

The domain form of NUM-28 is the divergence theorem applied to the traction on the body. With `w`
equal to `e_z` on the body, zero on every other boundary, and `T = T_M + T_H`:

```
F_z = ∮_∂B (T·n_B)·e_z dS = −∫_Ω T:∇w dV − ∫_Ω (∇·T)·w dV
```

**NUM-28 prints only the first term, and the second is not zero in this model. [verified]**
`∇·T_M = ρ_ion E − ½|E|²∇ε` and `∇·T_H = −f_total + Re ϱ(u·∇)u`, so each *component* carries a
body-force term of the same order as the force itself — `∫ρ_ion E·w` is the electrical body force
on the fluid inside the shell where `w` varies, an O(10 pN) number that depends entirely on where
that shell was put. **Omit it and each half of the force is a function of the band you chose**,
while the sum is unaffected, because the two body-force terms cancel between the halves. That is
the RSK-04 failure mode exactly: a total that agrees between routes over a split that is wrong.

**Three routes, and what each is good for. [tested]**

| Route | What it is | Independent of `w`? |
|---|---|---|
| A, domain | `−∫T:∇w` plus each component's consistency term | no — that is the point |
| B, surface | `∮(T·n)·e_z r ds` over the body's own boundary | yes; shares no quadrature point with A |
| C, reaction | the assembled momentum residual paired with a velocity-block test function equal to `e_z` on the body | **exactly**, being a discrete identity |

A and B agree **component by component whatever the model omits**, because A's `F^em` carries
`∇·T_M` and its `F^hd` carries `∇·T_H`, which are the divergences of the very tensors B takes the
tractions of. So B is a check on quadrature, not on the split. C is the check on the split: the
body's surface is Dirichlet for `u`, the residual vanishes on every free degree of freedom, and the
result is `F^hd` from the solve itself. **There is no route-C analogue for `F^em`** — `φ` is not
constrained on the body — which is why the `F = qE₀` anchor of VER-20 is not optional.

Measured on a charged sphere in an applied field at 0.3 M, with `F^em = −15.45 pN` against
`F^hd = +9.95 pN` (`tests/tier2/`): A against B is 1.3–2.7 × 10⁻² pN and wanders under refinement,
being surface quadrature on a different support; A against C is 4.6 × 10⁻⁴ → 1.3 × 10⁻⁴ →
3.4 × 10⁻⁵ pN and falls monotonically, being consistency error in A alone. **[tested]**

**The residual `−∫ ½|E|²∇ε·w` is the Korteweg–Helmholtz force PHY-23 omits**, not a discretisation
error: it is the gap between NUM-28 *as printed* and the force all three routes agree on. It is
identically zero classically and −4.0 × 10⁻⁴ pN on the reference-shaped ePNP-NS case, i.e. 0.02 %
of `F^em` there. **[tested]**

**No `1/r` term, and `singular=True` is not needed.** For an axial `w`, `(∇w)_φφ = w_r/r = 0`, so
the hoop components of both tensors are contracted against zero and `T:∇w = T_rz ∂_r w_z +
T_zz ∂_z w_z`. The integrals still go through `Measures` for the `r` weight and the order floor.
`physics/flow.strain_rate`'s documented omission of `ε_θθ = u_r/r` is harmless here for the same
reason. **[verified]**

**The `2π` is restored once**, in `post/forces.py`, exactly as `post/qoi.py` does it: every solver
integral is `∫ f r dr dz`. The force scale is `ε V_T² = 4.5677 × 10⁻¹³ N` — `p₀ a²` with the `a²`
cancelling, so it does **not** depend on the reference length. NUM-29's 0.1 pN is 0.219 in those
units. **[verified]**

---


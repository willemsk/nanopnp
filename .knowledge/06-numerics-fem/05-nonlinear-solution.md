---
type: Numerics
title: 5. Nonlinear solution
description: 'The nonlinear solution: damped Newton, convergence tests and the continuation ladder.'
tags:
- numerics
- numerics
sources:
- id: comsol-report
  resource: COMSOL Multiphysics 5.4 model report of 22 May 2020
  title: COMSOL model report (5.4)
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
verified:
- by: process:arithmetic
  at: '2026-10-14T00:00:00Z'
---

## 5. Nonlinear solution

**Primary strategy: monolithic damped Newton.** The author reports efficient convergence in
COMSOL for this exact system using **PARDISO direct + Newton with a lower-bounded variable damping
factor**. That is direct empirical evidence and outranks the general literature warning.
*Confirmed from the model report:* Fully Coupled, PARDISO (pivoting perturbation 1e-13), initial
damping 0.2, **minimum damping 0.01**, recovery damping 0.2, max 100 iterations, relative tolerance
1e-6, sparsity pattern reused. Continuation on `V_bias`. → `.knowledge/09-comsol-reference-settings/03-solver-3-4.md`.

Implement:
1. Damped Newton, damping factor adapted on residual reduction, with a **lower bound** (COMSOL's
   scheme: if the damped step still fails, accept the minimum damping rather than aborting).
2. Cap `‖δφ‖_∞ ≤ V_T` per step.
3. Monitor `min_i c_i` **every** Newton step; fail loudly on negativity with the location.
4. Assert the packing fraction `Σ_j N_A a_j³ c_j < 1` every step — `β_i` is singular at 1.

**Fallbacks, in order:**
- *Pseudo-transient continuation* (Kelley & Keyes, *SIAM J. Numer. Anal.* **35**, 508, 1998): add
  `M/Δt` to the Poisson and NP diagonal blocks, grow Δt by SER. Trivial to add to a steady code
  and the most robust safety net.
- *Hybrid segregated* (Mitscha-Baude et al., *J. Comput. Phys.* **338**, 452, 2017): Newton on the
  PNP block, fixed point for Stokes, with a **corrected Poisson step** — add the linearised-PB
  screening term `χ_F(2q²c₀/kT)φ^{k+1}` to the LHS, evaluated at `φ^k` on the RHS. This is the
  semiconductor Gummel map. They report both segregated schemes clearly outperform monolithic
  Newton *at high surface charge with constant properties*.
- *PB initial guess.* Initialise from the Poisson–Boltzmann solution rather than
  `φ=0, u=0, c_i=c₀`. Specifically cures the high-surface-charge failure mode. **Note:** because
  ePNP-NS violates the Einstein relation (see `.knowledge/02-electrokinetics-background/index.md`), PB is an
  approximate initialiser here, not the exact zero-bias limit.

**The convergence criterion must not be the residual alone.** A relative test measured against the
residual on *entry* — `‖r‖ ≤ 1e-6 ‖r₀‖` — has a pathology that only shows up once continuation is
wired in: re-solving an already-converged state demands another six orders of magnitude from a
residual that is already at its floor, so a warm start onto its own solution either burns the
iteration cap or fails outright. That is precisely the operation every rung of the ladder performs.
**[tested: pending]**

COMSOL's own "relative tolerance" is on the **solution update**, not on the residual. A relative
residual test `‖r‖ ≤ 1e-6 ‖r₀‖` hides under-converged fields: one norm over all fields is dominated
by the largest, and on the seven gated walks it closed every rung but one, leaving example 03's flow
8.2 × 10⁻⁶ and pressure 2.0 × 10⁻⁶ relatively unconverged with the ions at 2 × 10⁻⁸ and the global
relative update at 9 × 10⁻⁹ (WP41 D4, REV-08). The relative residual test closes nothing. Testing the
absolute residual floor `‖r‖ ≤ 1e-12`, or the **per-field** relative Newton update
`max_f ‖δu_f‖ / max(‖u_f‖, 10⁻⁶ · max(‖u‖, 1)) ≤ rtol`, restores idempotence and tests every field
to the tolerance **[tested: pending]**. Use the **undamped** Newton direction in that test, not the damped step:
a heavily damped step is small for reasons that have nothing to do with convergence, and testing it
would report success in the middle of a difficult ramp. Guard it further by never accepting convergence
on a step that failed to reduce the residual.

The floor of 1 on `‖u‖` is not arbitrary: NUM-09 leaves every field O(1), so a state near zero is
genuinely small rather than merely badly scaled; and the ratio `10⁻⁶` tests fields whose root is zero
(e.g. potential at zero bias, velocity in an uncharged pore) against a fraction of the state norm.

### 5.1 Continuation ladder

```
linear PB → nonlinear PB → equilibrium PNP (V=0, u=0)
  → ramp ρ_pore 0 → target
  → ramp V 0 → ±200 mV (≈10 mV steps near onset)
  → enable Stokes coupling
  → enable ⟨c⟩- and d-dependent D, μ, ε, ϱ    ← last, deliberately
  → enable steric flux β_i                     ← last of the last
  → sweep salt 0.05 → 3 M
```

Warm-start each rung from the previous. Adapt the mesh *between* rungs, never within them.
Enabling corrections last isolates their contribution to any convergence failure.

**A warm start across a *changed field set* is not free.** Three transitions change it — PB to
equilibrium PNP adds the concentrations, the Stokes rung adds `u` and `p`, and any change of element
order — and a solver that warm-starts by reusing the previous space cannot cross them. The target
space has to be built, cold-started so the new fields begin somewhere the positivity gate accepts,
and the shared fields interpolated by name. Where the field sets match, copy the vector rather than
interpolating: interpolation of a function already in the space is the identity only to round-off,
and most rungs of the ladder are same-space.

**Re-solving a converged rung costs one Newton iteration, not zero. [tested: pending]** The update-based
criterion cannot be evaluated without assembling the Jacobian and solving once; the entry-side
residual test is measured relative to the entry residual, so a converged warm start never passes it.
The state then moves by ~5 × 10⁻⁹ relative. This is the property to test a cross-space transfer with:
a transfer that scrambles a component needs many iterations to recover.

**Changing `c₀` between rungs is a vector copy, not an interpolation. [verified]** It changes the
whole NUM-09 scale set — `S`, `Pe`, every nondimensional coefficient — but not the field set, and the
previous solution stays a good guess because the nondimensionalisation leaves every field O(1) in the
*new* scaling too: `c̃_i = 1` is bulk by the definition of `c₀`, and `φ̃` is in `V_T`, which does not
move with the salt. Note also that the charge scales `ε V_T/a²` and `ε V_T/a` carry no `c₀` at all,
so a fixed or surface charge ramped at one concentration keeps its dimensionless value at another.

**The wall grading decides whether the charge ramp converges, not only how accurate it is.
[tested: pending]** The ladder raises `σ_s` while the model is still classical, and the field that fails
first is the **co-ion**, not the counter-ion: against a negative wall the anion is depleted as
`exp(−|φ̃|)`, so a Newton step in the primitive variable of the concentration overshoots a small
positive number straight through zero. At `λ_D(3 M)/5` = 0.035 nm the ramp climbs −0.05 C/m²; at
0.09 nm the positivity gate aborts on the first sub-step with `c_Cl⁻ = −0.76` at `r = 2 nm`, on the
wall. Both are correct: the coarse mesh does not resolve the layer, the step is too long, and the
gate stops a negative concentration becoming a plausible wrong current. So a reduced wall mesh costs
robustness at the charged end and not only accuracy; the log branch is the structural cure, and a
strongly charged pore also wants the Poisson–Boltzmann initial guess the fallback list names.

**The whole 0.05-3 M x +/-200 mV envelope, measured. [tested: pending]** Thirty operating points on a
2 nm x 13 nm pore at -0.02 C/m^2, every correction active against a real distance field, reached by
climbing the ladder once to the easiest corner and warm-starting every other point from a converged
neighbour: 13 rungs and 51 iterations for the climb, then 205 iterations over 621 s for the grid, no
gate violation and no rung below 0.1 damping. Conductance and selectivity against salt, at +50 mV:

| salt | G (S) | t+ | bulk t+ | excess |
|---|---|---|---|---|
| 0.05 M | 4.80e-10 | 0.870 | 0.388 | 0.482 |
| 0.15 M | 1.06e-9 | 0.662 | 0.383 | 0.280 |
| 0.50 M | 3.11e-9 | 0.486 | 0.373 | 0.113 |
| 1.0 M | 5.77e-9 | 0.432 | 0.366 | 0.066 |
| 3.0 M | 1.33e-8 | 0.384 | 0.356 | 0.028 |

Two things worth carrying. **The bulk transport number is not a constant**: the two ions carry
different mobility corrections, so `t+` of the unconfined electrolyte drifts from 0.388 at 0.05 M to
0.356 at 3 M, and a pore's selectivity has to be measured against the value at its own concentration
or the wall gets credit for what the electrolyte did. And NaCl is **anion**-selective to begin with
(`D_Cl` exceeds `D_Na` by 52 %), so "a negatively charged pore has `t+ > 1/2`" is false for any wall
charge weak enough not to overturn that -- at -0.02 C/m^2 it holds only below about 0.3 M.

**The correction set is worth a factor of two in conductance at 3 M. [tested: pending]** ePNP-NS against
classical PNP-NS at 3 M, +200 mV, `-0.02 C/m^2`, same mesh and same code path: `G` falls by a factor
0.452, which is the mobility correction (`mu/mu0` = 0.465 for Na+, 0.552 for Cl-) showing through
almost undiluted, and `t+` moves 0.433 -> 0.384. The classical arm doubles as a Maxwell-Hall check at
the top of the salt range: with the double layer a tenth of the pore radius it gives 2.9495e-8 S
against the closed form's 2.95e-8 S.

**A rung reports no Newton step for two unrelated reasons, and the silence is identical. [tested: pending]**
Measured 21 September 2026 on the default ladder of an `epnp-ns` case at 0.1 M and 20 mV, twelve
rungs on a cheap cylindrical pore. Two rungs (`1-pb-linear`, `2-pb`) are not coupled models, so
`SolveStage._instrumented` injects no damped-Newton callback into them at all — a callback is a
keyword their `solve` would reject. Three more (`3-equilibrium-pnp`, `7-corrections`, `8-steric`)
*are* coupled and still record `iterations: 0`: `damped_newton` found the transferred state's
residual already at or below `max(rtol * initial, atol)` and returned before its first step. Only
the remaining seven took steps, five each on the bias and salt rungs and four on the flow rung.

So five of twelve rungs keep no Newton history, and a consumer told only "no steps" cannot say
which kind of rung it is looking at. Anything reporting the ladder has to carry that distinction
explicitly — it is knowable only where the callback is injected — or it will describe a warm-started
rung that converged on entry as one that is not a Newton solve.

**Measured, on a charged 2 nm × 13 nm pore. [tested: pending]** The only rungs needing damping below the
0.2 initial value were the surface-charge ramp, at 0.08; every other rung of every ladder tried held
at 0.2. A full climb to the hard corner — 3 M, ±200 mV, every correction active, wall graded to
`λ_D(3 M)/5`, 66 000 DOF — is 22 rungs, 106 Newton iterations and 500 s. At `λ_D(3 M)/2` (25 000 DOF)
the same climb is 74 iterations and 134 s, so the reduction costs nothing in convergence.

---


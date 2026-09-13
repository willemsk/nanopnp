# Numerics — FEM formulation, solvers, and quantities of interest

Reference for agents implementing or modifying the solver. Companion to
`01-physics-epnpns.md` (which holds the equations) and `08-validation-benchmarks.md` (which holds
the tests). Everything here has been verified against primary sources; see §8 for what has not.

---

## 1. Discretisation

**Elements.** Continuous Galerkin: `P2` for `φ` and each `c_i`; Taylor–Hood `P2/P1` for `(u, p)`.
Triangles. All measures `r`-weighted (§2).

**Nernst–Planck formulation: primitive concentrations `c_i`,** with a log-variable branch behind a
flag as fallback.

| Form | Positivity | Conditioning at ±200 mV | Verdict |
|---|---|---|---|
| Primitive `c_i` | not guaranteed | good | **default** |
| Slotboom `c_i = c₀e^{−z_iφ̃}ρ_i` | yes | coefficient spread `e^{2φ̃}` ≈ 5.8 × 10⁶ | **reject** |
| Log/entropy `c_i = e^{w_i}` | exact | moderate, needs damping | fallback branch |
| Mixed / HDG | yes | locally conservative | later, if flux conservation demands |

`φ̃ = φF/RT` spans ±7.78 at ±200 mV, which is what kills Slotboom.

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
> `01-physics-epnpns.md` §2.3), not the constant-density Stokes above. Implement the variable-
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

---

## 5. Nonlinear solution

**Primary strategy: monolithic damped Newton.** The author reports efficient convergence in
COMSOL for this exact system using **PARDISO direct + Newton with a lower-bounded variable damping
factor**. That is direct empirical evidence and outranks the general literature warning.
*Confirmed from the model report:* Fully Coupled, PARDISO (pivoting perturbation 1e-13), initial
damping 0.2, **minimum damping 0.01**, recovery damping 0.2, max 100 iterations, relative tolerance
1e-6, sparsity pattern reused. Continuation on `V_bias`. → `09-comsol-reference-settings.md` §B.

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
  ePNP-NS violates the Einstein relation (see `02-electrokinetics-background.md`), PB is an
  approximate initialiser here, not the exact zero-bias limit.

**The convergence criterion must not be the residual alone.** A relative test measured against the
residual on *entry* — `‖r‖ ≤ 1e-6 ‖r₀‖` — has a pathology that only shows up once continuation is
wired in: re-solving an already-converged state demands another six orders of magnitude from a
residual that is already at its floor, so a warm start onto its own solution either burns the
iteration cap or fails outright. That is precisely the operation every rung of the ladder performs.
**[tested]**

COMSOL's own "relative tolerance" is on the **solution update**, not on the residual, which sidesteps
this. Testing either condition — the residual has fallen by the tolerance, *or* the relative Newton
update `‖δu‖/max(‖u‖, 1)` is below it — restores idempotence and is closer to the reference. Use the
**undamped** Newton direction in that test, not the damped step: a heavily damped step is small for
reasons that have nothing to do with convergence, and testing it would report success in the middle
of a difficult ramp. Guard it further by never accepting convergence on a step that failed to reduce
the residual.

The floor of 1 on `‖u‖` is not arbitrary: NUM-09 leaves every field O(1), so a state near zero is
genuinely small rather than merely badly scaled.

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

**Re-solving a converged rung costs one Newton iteration, not zero. [tested]** The update-based
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
[tested]** The ladder raises `σ_s` while the model is still classical, and the field that fails
first is the **co-ion**, not the counter-ion: against a negative wall the anion is depleted as
`exp(−|φ̃|)`, so a Newton step in the primitive variable of the concentration overshoots a small
positive number straight through zero. At `λ_D(3 M)/5` = 0.035 nm the ramp climbs −0.05 C/m²; at
0.09 nm the positivity gate aborts on the first sub-step with `c_Cl⁻ = −0.76` at `r = 2 nm`, on the
wall. Both are correct: the coarse mesh does not resolve the layer, the step is too long, and the
gate stops a negative concentration becoming a plausible wrong current. So a reduced wall mesh costs
robustness at the charged end and not only accuracy; the log branch is the structural cure, and a
strongly charged pore also wants the Poisson–Boltzmann initial guess the fallback list names.

**The whole 0.05-3 M x +/-200 mV envelope, measured. [tested]** Thirty operating points on a
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

**The correction set is worth a factor of two in conductance at 3 M. [tested]** ePNP-NS against
classical PNP-NS at 3 M, +200 mV, `-0.02 C/m^2`, same mesh and same code path: `G` falls by a factor
0.452, which is the mobility correction (`mu/mu0` = 0.465 for Na+, 0.552 for Cl-) showing through
almost undiluted, and `t+` moves 0.433 -> 0.384. The classical arm doubles as a Maxwell-Hall check at
the top of the salt range: with the double layer a tenth of the pore radius it gives 2.9495e-8 S
against the closed form's 2.95e-8 S.

**Measured, on a charged 2 nm × 13 nm pore. [tested]** The only rungs needing damping below the
0.2 initial value were the surface-charge ramp, at 0.08; every other rung of every ladder tried held
at 0.2. A full climb to the hard corner — 3 M, ±200 mV, every correction active, wall graded to
`λ_D(3 M)/5`, 66 000 DOF — is 22 rungs, 106 Newton iterations and 500 s. At `λ_D(3 M)/2` (25 000 DOF)
the same climb is 74 iterations and 134 s, so the reduction costs nothing in convergence.

---

## 6. Linear solvers

At 2D axisymmetric sizes **direct is correct**. 2D nested-dissection fill is O(N log N),
factorisation O(N^1.5). It is 3D where direct collapses (~10⁵–10⁶ DOF).

**Constraint verified during review:** the **NGSolve pip wheel ships without MUMPS**.
`ngsolve.config` reports `USE_MUMPS: False` (also `USE_HYPRE`, `USE_PARDISO`, `USE_MKL` all
False), and `inverse="mumps"` raises `SparseMatrix::InverseMatrix: no inverse available for type
mumps`. Getting MUMPS needs a source build with MPI — reintroducing the compiler dependency the
backend choice exists to avoid.

| Path | Solver | Notes |
|---|---|---|
| Desktop / pip wheel | `umfpack`, or scipy `superlu` (BSD) | `sparsecholesky` is SPD-only and **cannot** be used for this unsymmetric system |
| HPC / source build | MUMPS via ngsPETSc/PETSc, `icntl_14 = 40`, BLR via `icntl_35` | also unlocks `PCFIELDSPLIT` for 3D |

SuiteSparse UMFPACK is GPL-2+ — relevant to what a redistributable bundle may contain.

### 6.1 Measured: UMFPACK and SuperLU at production size **[tested]**

The five-field system of NUM-01 on the analytic cylindrical pore — `φ` P2 on all of Ω, `c_±` P2,
`u` P2 vector and `p` P1 on the fluid only — assembled with every coupling block present, then
factorised. One configuration per process, because `ru_maxrss` is a high-water mark and successive
factorisations in one process report the largest so far. Development laptop, WSL2, 24 cores, 15 GB.

| cells | DOF | nonzeros | UMFPACK | peak RSS | SuperLU | peak RSS |
|---|---|---|---|---|---|---|
| 1.50 × 10⁴ | 1.43 × 10⁵ | 8.4 × 10⁶ | 4.4 s | 855 MB | 24.0 s | 2593 MB |
| 3.84 × 10⁴ | 3.68 × 10⁵ | 2.2 × 10⁷ | 14.0 s | 2157 MB | 140.3 s | 8656 MB |
| 1.09 × 10⁵ | 1.04 × 10⁶ | 6.2 × 10⁷ | 41.1 s | 6171 MB | OOM-killed | > 15.4 GB |

**UMFPACK is comfortably viable at the reference mesh size**: 41 s and 6.2 GB at 1.09 × 10⁵ cells.
Its memory grows almost linearly in DOF (×2.52, ×2.86 for DOF ratios ×2.57, ×2.84), consistent with
the O(N log N) fill quoted above, and its time grows as roughly N^1.1 — better than the O(N^1.5)
worst case, which is what good nested dissection on a 2D mesh buys.

**SuperLU is a licence fallback, not a performance one.** It costs ≈ 3.4× the memory and 6–10× the
time, and both gaps widen with size: its time scales as ≈ N^1.8 and its memory superlinearly. At the
reference mesh size it was OOM-killed twice at 15.4 GB anonymous RSS; extrapolating the two smaller
points puts it near 28 GB and ~15 minutes. Converting the NGSolve matrix to scipy CSR costs a
further 0.2–0.7 s and is not the bottleneck.

The consequence bears on CON-11 and ADR-003: **a redistributable bundle cannot simply swap GPL-2+
UMFPACK for BSD SuperLU and keep the same capability.** At half the reference mesh size SuperLU
works but is ten times slower; at the reference size it does not run on a 15 GB laptop at all. If
the copyleft dependency has to go, the replacement is the iterative `PCFIELDSPLIT` path, not
SuperLU.

**Iterative path (held in reserve, required for 3D):** multiplicative `PCFIELDSPLIT` splitting
`{(φ, c_±), (u, p)}` — multiplicative reflects the weak PNP→NS coupling — AMG per scalar block,
Stokes Schur with `selfp` or the pressure mass matrix `S ≈ −μ⁻¹M_p`. See FEniCSx-pctools
(arXiv:2402.02523) for how such nested specifications are automated.

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

### 7.1 Measured: the two routes agree, and the band does not matter **[tested]**

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

> **No reference implementation exists for this.** The thesis's trapping work used equilibrium
> APBS Poisson–Boltzmann on a coarse-grained bead model plus a 1D analytic rate model — there is
> no Maxwell/hydrodynamic stress integral and no computed force profile anywhere in it, and
> embedded-particle force computation is listed as *future work*. See `05-analyte-and-forces.md`.
> Consequence: the analyte force feature must be verified against **analytic** benchmarks
> (Smoluchowski/Hückel electrophoretic mobility limits, Stokes drag on a sphere, Maxwell stress on
> a sphere in a uniform field), not against prior results.

**Pore-averaged quantities.** The thesis's pore averages appear to omit the `2πr` Jacobian while
being described as volume averages (flagged in `04-clya-geometry-and-charge.md`). Any regression
target that is a pore average must state which convention it uses.

### 7.1.1 Measured: with the wall corrections on, route agreement *is* a mesh statement **[tested]**

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
below is the unzeroed-projection case, which `mesh/distance.py` does not produce.

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

### 7.1.2 Measured: a reassembled residual reproduces the live one bit for bit **[tested]**

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

## 8. Mesh resolution and adaptivity

- First wall layer `h₁ ≈ λ_D/5` — 0.035 nm at 3 M. Geometric ratio 1.15–1.2 over ~15 layers,
  growing to 5–10 nm in the far reservoir. Expect 5 × 10⁴ – 2 × 10⁵ cells.
- **Compute the wall-distance field once per mesh and mollify it to C¹** (eikonal or
  screened-Poisson). `D`, `μ`, `η` all depend on `d`, so a kinked `d` propagates into the Jacobian.
- Goal-oriented (DWR) adaptivity on the current QoI: Becker & Rannacher, *Acta Numerica* **10**, 1
  (2001). Mitscha-Baude's economy — build the estimator from the **linear PB surrogate** rather
  than the full coupled adjoint — is heuristic but empirically retains the optimal O(h²) rate in
  the QoI at a fraction of the cost. Ship as an optional loop, not a v1 default.
- **The published results carry no discretisation error bar.** The *thesis* states only "COMSOL
  Multiphysics v5.4" and mentions "the final mesh" in passing: no element counts, no types, no
  refinement strategy, no tolerances, no convergence study. **[verified]** by grep over
  `thesis/chapters/`. Our mesh convergence study is therefore new work, and small disagreements
  with published numbers may be *their* discretisation error rather than ours.
  **Correction to the above, added later:** the paper's *ESI* is a 143-page COMSOL-generated model
  report that **does** contain a Mesh section (§2.7), Solver Configurations for both studies
  (§3.2, §4.3) and a "Mesh quality" results section (§5.4). Those numbers exist; they have not yet
  been extracted (`WebFetch` truncates the PDF at ~p. 66 of 143). Still no convergence study.
  → `09-comsol-reference-settings.md`.

### Measured: the reference region meshes to a third of COMSOL's element count **[tested]**

The ClyA region of §5.2.1 — the delivered 185-vertex profile, the membrane quadrilateral with its
slanted inner edge, a 250 nm reservoir half-disc, glued — meshed by netgen at the §5.2.2 size fields
(global 10 nm, pore boundary 0.05 nm, pore domain 0.1 nm, reservoir domain 2.8 nm, reservoir arc
5 nm, axis-in-pore 0.075 nm), `grading = 0.2`, `optsteps2d = 5`:

| | netgen, here | COMSOL, §5.2.2 |
|---|---|---|
| triangles | 44,316 | 120,917 |
| minimum element quality | 0.6559 (SICN), 0.6157 (gamma) | 0.6378 |
| mean element quality | 0.9870 (SICN) | 0.9765 |
| time | 6.5 s | — |

A third of the elements in the same quality band. The counts are *not* comparable as a convergence
statement — the two meshers' size fields are not the same knobs, and COMSOL's single "element
quality" is not stated to be SICN — but the quality band is, and it is met without boundary layers,
by isotropic grading alone, which is what §5.2.2 says the reference model did.

**The quality gate is cheap enough to run unconditionally**: ≈1.1 s on a 121k-element mesh, a
fraction of the time to build one. The measured margin on the geometries this project generates is
wide (minimum SICN 0.647 against a 0.3 floor), so gating only *imported* meshes would leave the ones
we build ourselves unwatched for no saving.

**The gate's first run found a degenerate mesh, and the answer was not to weaken it.** VER-16's
Gouy-Chapman slab is 2000 nm × 0.5 nm meshed at 50 nm: a chain of 100:1 triangles at minimum SICN
0.019. That anisotropy is not a defect — the transverse extent is an artefact of solving a
one-dimensional problem on a two-dimensional mesh, and the stretched direction is the one the
solution is constant in, so those elements carry zero interpolation error rather than merely bounded
error. A gate that measures isotropy has nothing to say about such a mesh; the exemption belongs at
that call site, with its reasoning, not in the floor.

---

## 8.1 NGSolve traps found by implementing this — all silent

Eighteen ways this project's own code was wrong while raising nothing. All reproduced on NGSolve
6.2.2606. **[tested]**

**1. A nonlinear form must be written in the trial function, not the grid function.**
`AssembleLinearization(gfu.vec)` differentiates the form with respect to the *trial* function and
substitutes the state vector. Written the intuitive way —

```python
a += (grad(gfu) * grad(v) + sinh(gfu) * v) * dx  # WRONG: Jacobian is identically zero
a += (grad(u) * grad(v) + sinh(u) * v) * dx  # right, with u = V.TrialFunction()
```

— the assembled Jacobian is **all zeros**, with no warning. Newton then fails inside the linear
solver with `UmfpackInverse: Numeric factorization failed` / "matrix is singular", pointing at the
solver rather than at the form. Cost of diagnosis: an hour.

**2. The higher-order basis is hierarchical, so its shape functions are not a partition of unity.**
Building a boundary indicator by setting the boundary DOFs of a P2 space to 1 gives a function whose
integral over that boundary is **11/12 of its length**, not its length. A reaction flux normalised
on the assumption gives a clean, stable, mesh-independent **8.33 % error** — which reads as a
modelling difference, not a bug. Build the indicator by interpolation instead:
`psi.Set(CF(1.0), definedon=mesh.Boundaries(name))`.

**3. `GridFunction.Set` projects element-wise, so Dirichlet data comes back approximate.**
Interpolating `-sqrt(t)*log(w)` for the wall-distance field left `d ≈ -4e-4 nm` *on* the wall
instead of 0. Small, but `f^w_D(0) = 0.0601` is 6 % of its bulk value, so a slightly negative `d`
shifts the near-wall diffusivity by percent. Zero the constrained DOFs explicitly afterwards.
**The sign of that round-off is platform-dependent**, so no test may assert it: projecting `x` onto
P2 on the slab leaves −3.5e−16 at the wall on Linux and a positive value of the same size on macOS
and Windows, which silently turned a strict `c > 0` gate test green on one platform and red on the
other two. Sample the coefficient function itself when a test needs an exact boundary value.
**[tested]**

**4. `Integrate`'s `order=` replaces NGSolve's default of 5, it does not raise it.**
`ngsolve.Integrate(cf, mesh)` uses order 5 when none is given. A helper that computes an order and
passes it explicitly therefore *lowers* the accuracy of every integral that did not need raising:
integrating `x^3` over the unit square at the order-2 rule returns 0.20005 for an exact 0.2, while
the bare call returns 0.2 to machine precision. Any wrapper around `Integrate` must floor its
computed order at 5. **[tested]**

**5. `bonus_intorder` is added to NGSolve's own estimate for the integrand, which is not knowable.**
So a minimum integration order cannot be guaranteed by passing the *deficit* between that minimum
and an assumed base — the assumption is unverifiable, and for a quotient NGSolve's estimate can be
as low as 2. A guarantee of order `n` has to come from a bonus of `n` on its own. Measured orders
for the axis trap: order 2 gives NaN on `1/r`, orders 3, 4, 5 and 8 do not. **[tested]**

**6. The reaction flux is the residual `a(u,v) - f(v)`, so the load form must be subtracted.**
`BilinearForm.Apply` gives `a(u, ·)` alone. Omitting `f` on a problem with a source biases the flux
by `int f psi` over the boundary-adjacent elements: for `-lap(phi) = 1` on the unit square with two
constrained sides, the closed boundary integral of `dphi/dn` came back as −0.913 instead of the
exact −1. Poisson-Boltzmann hides this, having a zero right-hand side. The identity also holds only
where the solve *constrained* the boundary; asked for a free one, the residual returns a plausible
non-zero number instead of the flux. **[tested]**

**7. `FESpace.components` raises on a non-compound space rather than being absent.**
`getattr(space, "components", None)` does **not** protect against it: the default applies only when
the attribute is missing, not when the property itself throws. On an `H1` space the access raises
`NgException: components only available for ProductSpace`, so any code that branches on "is this a
compound space" with `getattr` breaks the moment it is handed a single field. Use `try/except`.

**8. NGSolve registers its own `superlu` inverse type, so `mat.Inverse(inverse="superlu")`
silently succeeds.** `ngsolve/directsolvers.py` calls `ngsolve.la.RegisterInverseType("superlu",
SuperLU)` at import, wrapping `scipy.sparse.linalg.factorized`. A project that also ships its own
SuperLU path — because it wants row equilibration, or a specific error message — therefore ends up
with **two implementations behind one name**, and which one a call site gets depends on whether it
routes through the project helper or through `mat.Inverse`. Nothing raises; the answers agree to
1e-14 on a well-scaled system, so the divergence only shows on the badly scaled one the
equilibration was added for. Resolve a solver name in exactly one function. **[tested]**

**9. A direct solver factorises a singular system without complaint.** A five-field block system
assembled with no essential conditions anywhere — pure-Neumann Poisson has the constant null mode,
and the Stokes block has nothing fixing the pressure — is factorised happily by both UMFPACK and
scipy SuperLU. The "solutions" come back finite: `‖x‖_inf` of 2e16 from SuperLU and 8e33 from
UMFPACK on the same 1.5e4-dof system, with residuals of 5e3 and 6e20. So `np.isfinite(x).all()` is
**not** evidence that a factorisation is usable; assert on the residual `‖Ax − b‖`, which is 1e-13
once the reservoir caps are constrained. **[tested]**

**10. `GridFunction.Set(cf, definedon=region)` zeroes every degree of freedom outside `region`.**
It is an interpolation onto the whole function, not a write into part of it. So the natural order —
write an initial guess over the domain, then apply the essential boundary data — silently discards
the initial guess, and a coupled solve starts from `c_i = 0`, which the NUM-17 positivity gate then
(correctly) aborts on before Newton takes a step. The same call on a warm start discards the state
being warm-started from, which is worse, because that one converges to something plausible.
Interpolate onto a scratch function and copy only the region's degrees of freedom:
`gf.vec.data = Projector(dofs, False) * gf.vec + Projector(dofs, True) * scratch.vec`. **[tested]**

**11. A point on a facet shared by two elements may be located in either of them, so a field
defined on a subdomain reads zero there.** The NUM-17 gates sample the P2 nodal set; a node on the
fluid/membrane interface belongs to elements on both sides, and `mesh(r, z)` may resolve it into
the membrane, where `c_i` is not defined and evaluates to 0 — not positive. Filtering the *elements*
by material is not enough, because the node still has the interface's coordinates. Pulling each
element's sample points a small fraction towards that element's own centroid fixes it; the fraction
has to be big enough to beat the location tolerance. Measured on the analytic pore at `maxh` 6 nm
and 2 nm: 1e-6 still resolves into the solid, 1e-5 is the first that does not, and 1e-4 leaves an
order of margin while moving a P2 value by 1e-4 of its variation across the element. **[tested]**

**12. `GridFunction.Set` on a compound space raises rather than dispatching to the components.**
`gf.Set(CF(1.0), definedon=mesh.Boundaries(name))` on a product space raises `CompoundFESpace does
not have an evaluator for BND!`. Build the boundary indicator of NUM-25 on one component —
`gf.components[i].Set(...)` — which is what you want anyway: the inner product with the residual
then picks out one equation's flux rather than the sum over all of them. **[tested]**

**13. `ngsolve.grad(gridfunction)` evaluated on a boundary region returns the *surface* gradient of
the trace, silently dropping the normal derivative.** The surface route of NUM-28 needs the volume
gradient lifted to the body's boundary, and `grad(u)` there gives the tangential part only — a
traction missing its normal component, which on a no-slip surface is most of it, with no error and
no NaN. The cure is `ngs.BoundaryFromVolumeCF(grad(u))`, which lifts the volume expression rather
than differentiating the trace. Note also that **`ngs.BoundaryCF` is a method of the mesh**, not a
module function: `mesh.BoundaryCF({...})`. **[tested]**

**14. `ngs.LinearForm(term)` raises; a linear form must be built on a space and then added to.**
`ngs.LinearForm(charge_source(rho, v, AXISYMMETRIC))` fails with `NgException: Linearform must have
TestFunction`, which reads as a problem with the term. It is not — the constructor takes the *space*:
`f = ngs.LinearForm(space); f += term; f.Assemble()`. **[tested]**

**15. Netgen's OCC kernel does not put axis vertices at exactly `r = 0`.** A revolved geometry comes
back with vertices at `r = -1.5e-15` nm and `r = +7e-16` nm — round-off in the rotation, not a mesh
that crosses the axis. Two things break on it. The CON-04 gate asks for `r >= 0` *exactly*, and has
to go on asking exactly, because the failure it exists to catch is a mesh mirrored about the axis,
which is a sign error; a tolerance wide enough to pass round-off is a tolerance that has to justify
its width. And a content hash over the coordinate bytes makes two runs of the same mesher two
different meshes and two cache entries. Snap `|r| < 1e-9` nm to zero on the way into the in-memory
mesh, for every route in, the meshers' own included. **[tested]**

**16. `VoxelCoefficient`'s value array is indexed `[axis-2, axis-1]`.** For a 2D grid over
`(r, z)` the array must be `values[i_z, i_r]`. Passing the transpose raises nothing: a field built
to be `10r + z` returned 1.0 at `(r=1, z=0)` where 10.0 was intended, and **agreed exactly** at the
symmetric sample `(0.5, 0.5)` — so a test that samples on the diagonal passes on a transposed field.
Assert against a field that is not symmetric in its arguments, at an off-diagonal point. **[tested]**

**17. `VoxelCoefficient` continues by the clamped edge value outside its box, not by zero** — as its
docstring says, and as measured beyond the box in `r` and in `z`. For a charge grid this is not a
detail: the reference mesh is a half-disc of radius 250 nm (98,175 nm²) against a grid footprint of
~93 nm², so a residual edge value is amplified over an area **1056 times** the grid's own. Pad the
value array with a ring of zeros and extend the box by one spacing each way; the field is then zero
outside *and* continuous, where an `IfPos` window would be zero and discontinuous. Gate what the
padding threw away by refusing a grid whose boundary ring is not negligible against its interior.
**[tested]**

**18. `extra_order=3` on a singular form is not a refinement.** `Measures.bonus_order(singular=True)`
takes `max(extra, 3)` — NUM-07's floor for a form carrying `1/r` — so asking for three extra orders
on such a form evaluates at *exactly* the assembly order and returns a bit-identical number. A
quadrature-agreement gate written that way compares a value with itself and passes unconditionally.
Measured on the delivered ClyA charge table: `extra=0` and `extra=3` both give -71.289538 e, while
`extra=6` gives -71.957178 e. Ask for enough extra orders to clear the floor. **[tested]**

### 8.1.1 Mesh-integral error on a sub-element-scale field converges in neither `h` nor order

The finding that costs the most to rediscover, from ingesting the reference model's own 0.005 nm
`rhoq_pore` table (`04-clya-geometry-and-charge.md` §3.2 carries the full tables). Integrating a
`VoxelCoefficient` over the deployed mesh is *not* a discretisation error that refinement reduces:
the table's radial structure alternates sign 49 times along its densest `z`, with extrema a median
0.035 nm apart, an order below the finest element the reference mesh places. Pointwise quadrature of
the bilinear interpolant is then **aliased**, and

- refining `h` from 44,316 to **3,463,372** elements moved the error from +9.9e-3 to **-1.1e-2** —
  worse, and non-monotone in between (669 s to mesh, 80 s to integrate);
- raising the integration order from 8 to 37 on the fixed mesh oscillated through +5.9e-4, -3.0e-3,
  +2.8e-3, -7.4e-4, +4.8e-4 without settling.

Two consequences. First, a conservation gate on such a field is a *resolution* gate: report the
order/order+N quadrature agreement beside the conservation figure, and let it be the one that fires,
so the diagnostic says "the mesh under-resolves the supplied field" rather than "charge was lost".
Second, the fix is on the producer side — deposit onto the finite-element space and rescale to
`Q_net`, which conserves by construction — and no amount of consumer-side effort substitutes for it.
**[tested]**

### 8.1.3 An OCC-generated extent is one ulp off the number the geometry was given **[tested]**

`CylindricalPoreGeometry(membrane_thickness_nm=6.0, ...)` produces a mesh whose `membrane` vertices
span `z ∈ [−3.0, 3.000000000000001]`: the upper face is one unit in the last place high, and
identically so at `maxh` 4.0 and 2.0, so it is the OCC revolve's round-off and not a meshing
artefact. Anything derived from a material's own extent — the NUM-24 indicator band read off the
mesh rather than off the geometry object is the case that found it — therefore agrees with the
geometry formula to about 4 × 10⁻¹⁶ nm and not exactly. Assert such an identity on a hand-built
`MeshData` with exact coordinates, and assert the meshed one to a tolerance far below any length in
the problem; an `==` against a meshed extent is a test that will fail on some other platform's OCC.

### 8.1.2 An unstructured netgen mesh is not a portable measurement

A corollary of §8.1.1 that only shows up on a CI matrix. Because the aliased quadrature error is a
function of where the vertices happen to fall, *any* assertion on its magnitude inherits the
mesher's own arbitrariness. Netgen's unstructured triangulation of the same rectangle at the same
`maxh = 0.2 nm` gave, for the same field, an order/order+3 agreement of **2.3e-4 on Linux, 7.8e-5 on
Windows and 2.2e-5 on macOS** — a factor of ten, straddling a 1e-4 threshold three different ways
**[tested]**. Nothing about the physics differs; the meshes do.

Coarsening is not the repair, because the quantity is non-monotone in `h` (§8.1.1) — it re-rolls the
dice. `ngsolve.meshes.MakeStructured2DMesh` places every vertex arithmetically from `(nx, ny)` and a
mapping, so the mesh, and therefore the number, is identical on every platform. On the same box and
field it reads 3.7e-4 at `(27, 70)`, 7.4e-5 at `(23, 59)` and 5.0e-6 at `(25, 65)` — one coarser and
one finer than the first, both *below* what it exceeds, which is the non-monotonicity again and the
reason the resolution has to be picked by measurement.

The rule: **a test that asserts a quadrature-error magnitude must run on a structured mesh.** A test
that asserts a converged physical quantity may use whatever mesh the pipeline deploys, because that
number is mesh-independent by construction and an unstructured mesh is then the more honest one.

### 8.2 Measured: the reaction flux really is worth it

Gouy-Chapman at 0.1 M, ζ̃ = 2, P2, planar slab. Wall gradient recovered two ways and compared with
the analytic `-φ̃'(0) = (2/λ_D) sinh(ζ̃/2)`. **[tested]**

| mesh | variational reaction flux | pointwise `grad(u)` at the wall |
|---|---|---|
| `h = λ/4` | +0.004 % | −0.84 % |
| `h = λ/8` | +0.0001 % | −0.28 % |
| `h = λ/16` | +0.00003 % | −0.08 % |

Two hundred times better on the coarsest mesh, and it is *already converged* where the pointwise
gradient still has percent-level error. This is the quantitative case for NUM-24/NUM-25 over any
gradient- or cross-section-based extraction.

### 8.3 Convergence and solver facts

- **P2 gives clean O(h³) in L² on the r-weighted axisymmetric form.** Debye-Hückel in a cylinder,
  relative weighted L² error against `ζ I₀(r/λ)/I₀(a/λ)`: 1.12e-3 → 1.48e-4 → 1.99e-5 → 2.46e-6 for
  `maxh` 0.4 → 0.05 nm, i.e. rates 2.92, 2.90, 3.01. The axisymmetric weak form and the natural
  axis condition are correct. **[tested]**
- **UMFPACK *is* built into the pip wheel**: `ngsolve.config.USE_UMFPACK` is True and
  `mat.Inverse(freedofs, inverse="umfpack")` works. `USE_MUMPS`, `USE_PARDISO` and `USE_MKL` remain
  False, and `inverse="pardiso"` raises "MKL Pardiso is not available". So the default direct path
  of NUM-21 is available out of the box; only the GPL-2+ licensing of UMFPACK is at issue, not its
  presence. **[tested]**
- **The coupled axisymmetric system converges at the Taylor-Hood rates under MMS.** Manufactured
  `φ, c_i, u, p` on a 2 × 4 nm cylinder, constant transport coefficients with the steric `β_i`
  retained, `maxh` 0.4 → 0.2 → 0.1 nm (2 × 10⁴ DOF at the finest). Relative `r`-weighted L² rates:
  2.9–3.6 for `φ`, 3.0–4.0 for `c_i`, 3.0–3.5 for `u`, and **2.7 for `p`**. The pressure rate is the
  P1 half of the P2/P1 pair, not a shortfall — asserting O(h³) there would be asserting something
  untrue of a correct solver. **[tested]**
- **`CoefficientFunction.Diff` and `Operator("hesse")` both work on a component of a product
  space**, and `Diff` works with respect to a `GridFunction` as well as a trial proxy. That is what
  makes the PHY-23 dielectric terms expressible: `∇ε_r = Σ_i (∂ε_r/∂c_i) ∇c_i` by the chain rule,
  with the sensitivities taken symbolically rather than by finite differences. **[tested]**
- **A `BilinearForm` term carrying no trial function assembles and linearises correctly.**
  `a += (-f*v)*dx` with `f` a coefficient function contributes to `Apply` and contributes nothing to
  `AssembleLinearization`, which is exactly right for a manufactured or body source in a nonlinear
  residual. There is no need for a separate `LinearForm` on the Newton path. **[tested]**
- **Varadhan screened-Poisson distance is accurate enough.** `w - t Δw = 0`, `w = 1` on the source,
  `d = -√t ln w`, solved **planar** in (r, z) — for a surface of revolution the meridian-plane
  distance *is* the 3D distance. Against the exact `a - r` of a cylinder, within 1.5 nm of the
  wall: √t = 0.1 nm → 0.6 pm worst error, 1.1 % gradient jump; √t = 0.2 → 1.4 pm, 0.17 %; √t = 0.3
  → 10 pm, 0.08 %. **[tested]**
- **…but the diffusion length must be resolved by the mesh it is solved on, and the default is
  sized for the wall corrections, not for a force band.** Reusing `DEFAULT_DIFFUSION_LENGTH_NM`
  (0.2 nm) to build the NUM-28 extension `w` on a mesh whose elements are 1.6 nm across leaves the
  screened Poisson unresolved: it oscillates, undershoots the exponential floor, and the recovered
  `d` jumps to its cap *inside an element touching the body* — so the smoothstep is no longer zero
  there and `w` comes off the surface at 1 − 10⁻⁴ instead of 1. The symptom was an assertion on `w`
  failing at a mean-square departure of 8.2 × 10⁻⁹; the cause was a distance field, not an
  extension. Sizing √t at a quarter of the shell width instead cured it and improved the Stokes-drag
  benchmark by a factor of thirty, from a 6 × 10⁻⁴ plateau to 2.0 × 10⁻⁵ falling monotonically.
  **The rule: √t is set by the feature the field has to resolve, and there is no single default that
  serves both a sub-nanometre wall correction and a several-nanometre force band.** **[tested]**

### 8.4 Sweeps: the warm start, the forest, and what parallel scaling measures

Measured under WP11 on the toy pore (`a` = 2 nm, `L` = 6 nm, reservoir 10 nm) at `maxh` 4.0 /
`wall_h` 0.35 nm — 392 elements, the coarsest mesh NUM-34 admits with the wall corrections on —
0.1 M NaCl, `willems2020_nacl` with every correction active, `default_ladder`, stabilisation
`none`.

- **A warm start does not move the answer, and the figure is 3.4 × 10⁻⁹. [tested]** A 2 × 2 grid
  (two concentrations × ±50 mV) solved twice: once warm through the forest, once cold into a store
  that had never seen a neighbour. Worst relative difference over every scalar every member
  reported: `3.367 × 10⁻⁹`, on `conductance_S`, against the `1 × 10⁻⁶` nonlinear relative tolerance
  the comparison is stated at. On the deepest point the current agreed to `9.8 × 10⁻¹⁰`
  (`1.825414947 × 10⁻¹⁰` A warm against `1.825414949 × 10⁻¹⁰` A cold). This is the premise
  §5.3.2 relies on when it keeps the warm-start source out of the stage-10 key, and it is measured
  rather than assumed.
- **The warm start is worth 2.81× in Newton iterations on four points. [tested]** 77 iterations
  warm against 216 cold, with 3 of 4 members warm-started; the root is cold in both passes by
  construction. A warm member solves the target rung alone — NUM-18 stage 9 generalised to the
  other axes — where a cold one climbs twelve rungs.
- **Measure that saving in iterations, not in seconds.** The wall clock said 10.5 s against 22.3 s
  on an idle machine and **34.3 s against 26.7 s** — the two passes swapped — when the same code
  ran alongside the rest of the test suite. A wall-time comparison between two passes of the same
  work is a statement about what else the machine is doing; the iteration counts are a property of
  the solves. `MemberResult` carries both, and only the second is ever asserted on. **[tested]**
- **What differs across an edge, by axis. [tested]** A bias step differs from its parent in
  `solve_hash` alone; a salt step differs in `solve_hash` **and** `model.scales`, the NUM-09 scale
  set being a function of `concentration_M`. Both are operator keys the §5.3.2 partition permits;
  a gate on either would refuse the axis outright.
- **The §8.3 reference grid is 42 waves of mean width 87.5. [tested]** 5 physics cases × 35 biases ×
  21 concentrations = 3,675 points, one root, deepest point at depth 41, peak wave width 174. The
  dependency structure is therefore not what limits QR-06 on twelve cores; the serial tail is the
  last few waves and it is short.
- **Parallel efficiency on four cores: 1.00, 0.76, 0.50 at N = 1, 2, 4. [tested]** 25 points in
  seven waves of widths 1, 3, 5, 5, 5, 4, 2; fresh store each run, every member a miss, thread
  counts pinned to 1 per worker. Wall clock 33.5 → 22.1 → 16.8 s, so 2.0× at four workers on a
  four-core machine that is also running the parent process. Throughput over uncached members:
  2 686 → 2 034 → 1 337 points per worker-hour.
- **One pool per plan, not one per wave, and it is worth a factor of the same size. [tested]**
  `spawn` re-imports the package in each worker at about a second apiece. Creating the pool per
  wave put that cost into the measurement: on a nine-point grid in five waves it took
  `efficiency(4)` from 0.75 to **0.29**. The pool is now held open across the whole plan.
- **A single-axis grid caps the curve at N = 2 whatever the runner does.** A one-axis sweep rooted
  in its middle has waves two points wide, so a scaling measurement on one reports the *grid*. Two
  axes are the minimum for a curve that says anything about the dispatch.

### 8.5 Measured: NUM-26's relative route check is inapplicable at exactly zero bias **[tested]**

At `V = 0` the current is zero, and both extraction routes return round-off:
`I_ψ = 2.288 × 10⁻²⁷` A against `I_reaction = 4.606 × 10⁻²⁵` A on the toy pore above. The relative
difference is then `0.995` and the NUM-26 gate aborts the run — on a solve that converged, on a
mesh that is admissible, at the one operating point where the answer is known exactly.

`RouteAgreement.relative_difference` divides by `max(|I_ψ|, |I_reaction|)` and returns `0.0` only
when *both* are exactly zero, which round-off never is. So the check is not wrong about these two
numbers; it is being asked a question — "do these two currents agree to one part in a thousand" —
that has no answer when there is no current.

**Consequence for a sweep:** a bias axis containing `0.0` aborts one member per remaining axis
combination, with exit class 4 and a diagnostic about the extraction. The checked-in
`docs/sweeps/phase1-reference.sweep.yaml` therefore roots its bias axis at **+5 mV** rather than at
0 V and carries 17 exactly-opposite pairs plus that one unpaired value: 35 values, 3,675 points,
1,785 rectification pairs, 42 waves — the §8.3 grid, with the degenerate point moved off it.

Not fixed here. Making the check inapplicable rather than failing at zero current means deciding
what "no current" is, which is a scale the extraction does not currently carry, and NUM-26 is a
Phase-1 headline gate. Recorded for whoever owns it next.

---

## 9. Unverified / to measure

- The O(h^{2p}) vs O(h^p) superconvergence rate claimed for variational reaction flux (the
  qualitative superconvergence result is established; the specific rate pair is not confirmed).
- The practical DOF ceiling for direct solves in 2D (~2–5 × 10⁶ is engineering judgement).

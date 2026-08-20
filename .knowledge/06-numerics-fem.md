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
I     = −F Σ_i z_i ∫_Ω J_i·∇ψ  r dr dz
Q_EOF =            ∫_Ω u·∇ψ    r dr dz
```
Superconvergent and cross-section independent.

**(b) Variational reaction flux.** Evaluate the assembled residual against a test function equal
to 1 on a Dirichlet electrode (Hughes, Engel, Mazzei & Larson, *J. Comput. Phys.* **163**, 467,
2000 — "the continuous Galerkin method is locally conservative").

**Derived QoIs.** `t₊ = I₊/(I₊ + I₋)` from the same `ψ` integrals. Rectification
`α = |I(+V)|/|I(−V)|`. Conductance `G = I/V_b`.

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

---

## 8.1 NGSolve traps found by implementing this — all silent

Seven ways this project's own code was wrong while raising nothing. All reproduced on NGSolve
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
- **Varadhan screened-Poisson distance is accurate enough.** `w - t Δw = 0`, `w = 1` on the source,
  `d = -√t ln w`, solved **planar** in (r, z) — for a surface of revolution the meridian-plane
  distance *is* the 3D distance. Against the exact `a - r` of a cylinder, within 1.5 nm of the
  wall: √t = 0.1 nm → 0.6 pm worst error, 1.1 % gradient jump; √t = 0.2 → 1.4 pm, 0.17 %; √t = 0.3
  → 10 pm, 0.08 %. **[tested]**

---

## 9. Unverified / to measure

- The O(h^{2p}) vs O(h^p) superconvergence rate claimed for variational reaction flux (the
  qualitative superconvergence result is established; the specific rate pair is not confirmed).
- The practical DOF ceiling for direct solves in 2D (~2–5 × 10⁶ is engineering judgement).

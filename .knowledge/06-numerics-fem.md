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

Three ways this project's own code was wrong while raising nothing. All reproduced on NGSolve
6.2.2606. **[tested]**

**1. A nonlinear form must be written in the trial function, not the grid function.**
`AssembleLinearization(gfu.vec)` differentiates the form with respect to the *trial* function and
substitutes the state vector. Written the intuitive way —

```python
a += (grad(gfu)*grad(v) + sinh(gfu)*v)*dx      # WRONG: Jacobian is identically zero
a += (grad(u)*grad(v)   + sinh(u)*v)*dx        # right, with u = V.TrialFunction()
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

- Whether UMFPACK factorises the five-field axisymmetric system at production mesh sizes in
  acceptable time and memory on a laptop. **Phase 0 exit criterion.**
- The O(h^{2p}) vs O(h^p) superconvergence rate claimed for variational reaction flux (the
  qualitative superconvergence result is established; the specific rate pair is not confirmed).
- The practical DOF ceiling for direct solves in 2D (~2–5 × 10⁶ is engineering judgement).

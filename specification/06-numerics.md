---
type: Specification
title: "6. Numerical methods specification"
description: "Fixes the discretisation and solution algorithm for the §4 model as NUM-nn requirements, and records where the reference implementation differs."
---

## 6. Numerical methods specification

This section fixes the discretisation and the solution algorithm for the model of §4. Requirements
carry `NUM-nn` identifiers and use the keywords of §1.5; verification activities that exercise them
are in §7. Settings of the reference implementation (§2.2) that differ from what is required here
are recorded, so that the cross-implementation comparison of §7.4 can account for them.

### 6.1 Discretisation

**NUM-01.** The discretisation SHALL be continuous Galerkin on triangles in the (r, z) half-plane,
with the element degrees below, and every volume and surface measure SHALL carry the `r` weight
of §6.2.

| Field | Element | Domain | Reference implementation |
|---|---|---|---|
| `φ` | P2 | `Ω` | Lagrange, quadratic |
| `c_i` | P2 | `Ω_w` | Lagrange, quadratic |
| `u` | P2, vector-valued | `Ω_w` | Lagrange, linear |
| `p` | P1 | `Ω_w` | Lagrange, linear |

Rationale: the Taylor–Hood P2/P1 pair is inf-sup stable, so the flow block needs no pressure
stabilisation of its own.

**NUM-02.** The Nernst–Planck equations SHALL be discretised in primitive concentrations `c_i` by
default. A log-variable branch `c_i = exp(w_i)` SHALL be provided behind a flag. Slotboom variables
SHALL NOT be used.

| Form | Positivity | Conditioning at ±200 mV | Status |
|---|---|---|---|
| Primitive `c_i` | not guaranteed | good | default |
| Slotboom `c_i = c₀ e^(−z_i φ̃) ρ_i` | yes | coefficient spread `e^(2φ̃)` ≈ 5.8 × 10⁶ | rejected |
| Log / entropy `c_i = e^(w_i)` | exact | moderate, requires damping | fallback branch |
| Mixed / HDG | yes | locally conservative | deferred to post-v1 |

Rationale: `φ̃ = φF/RT` spans ±7.78 over the ±200 mV envelope, so the Slotboom exponential weights
span six decades within one solve. The log form (Metti, Xu & Liu, *J. Comput. Phys.* **306**, 1,
2016) gives provable positivity and a discrete energy law, at the cost of a harder nonlinear
problem.

**NUM-03.** The velocity–pressure element pair SHALL be configurable. Equal-order P1/P1 SHALL be
selectable only together with the flow stabilisation of §6.4.2. The element degree of every field
SHALL be recorded in the run provenance record.

The reference used P1+P1 for velocity and pressure and quadratic elements for potential and
concentrations (NUM-01, last column). That flow pair is a known source of cross-implementation
discrepancy: a stabilised P1+P1 solve and a Taylor–Hood solve are different discretisations of the
same PDE, so only the converged velocity field is comparable, not the operator.

### 6.2 Axisymmetric weak forms

**NUM-04.** The weak forms SHALL be those below, with `∇ = (∂_r, ∂_z)` and the `r` weight on every
integral. The `2π` factor cancels and SHALL be dropped consistently from both sides.

Poisson, over all of `Ω` including protein and membrane, test function `v`:

```
∫ ε ∇φ·∇v  r dr dz  =  ∫ ( ρ_pore + F Σ_i z_i c_i ) v  r dr dz  +  ∫_Γ σ_s v  r ds
```

Nernst–Planck, per species on `Ω_w`, test function `w`, with `J_i` as defined in PHY-04:

```
∫ J_i·∇w  r dr dz  =  0
J_i = −[ D_i ∇c_i  +  z_i μ_i c_i ∇φ  +  D_i β_i c_i  −  u c_i ]
```

Navier–Stokes / Stokes on `Ω_w`, test functions `(v, q)`:

```
∫ [ 2η ε̂(u):ε̂(v) + 2η u_r v_r / r²  −  p d̂iv v  −  q d̂iv u ]  r dr dz  =  ∫ f·v  r dr dz
d̂iv u = ∂_r u_r + u_r/r + ∂_z u_z
```

**NUM-05.** The cylindrical hoop-strain term `2η u_r v_r / r²` SHALL be assembled. After
multiplication by the `r` weight it appears as `2η u_r v_r / r`, which is integrable because
`u_r → 0` on the axis.

Rationale: the term is the weak-form counterpart of the strong-form `−u_r/r²` contribution the
reference carries inside its axisymmetric interface. Omitting it produces plausible but incorrect
flow fields with no solver diagnostic.

**NUM-06.** At `r = 0` the only essential condition SHALL be `u_r = 0`. The conditions
`∂_r φ = ∂_r c_i = ∂_r u_z = 0` SHALL be left natural. Dirichlet conditions on `φ` or `c_i` at the
axis SHALL NOT be imposed.

Rationale: the `r` weight annihilates the axis boundary term. The analysis is set in the weighted
space `H¹_1(Ω)` (Mercier & Raugel 1982; Bernardi, Dauge & Maday) with standard convergence rates.

**NUM-07.** Every form containing a `1/r` factor SHALL be assembled at integration order ≥ 3, and
the implementation SHALL assert this at assembly time rather than rely on defaults.

Rationale: Gauss rules on triangles do sample `r = 0`. The NGSolve order-2 triangle rule places its
three points at the edge midpoints (0, ½), (½, 0), (½, ½), so an element with an edge on the axis is
sampled exactly at `r = 0`: on NGSolve 6.2.2606 `Integrate(gf*gf/(x*x)*x, mesh, order=2)` returns
NaN, while orders 3 and 4 return the correct value. Any term left at order 2 (a P1 pressure block, a
coarse continuation mesh, an unset `bonus_intorder`) silently yields NaN in the hoop-strain term.

**NUM-08.** A unit test SHALL integrate a known `1/r`-weighted quantity on an axis-touching mesh
and SHALL fail on NaN or on deviation from the analytic value.

NOTE: the reference assembled its flow momentum, continuity, stabilisation and density-continuity
terms at integration order 2. NUM-07 governs here irrespective of that setting.

NOTE (the `r` weight and the default order; WP26): NGSolve estimates
an integrand's order from its trial and test functions and does not count the coordinate, so a form
that is not singular is integrated one order short of its degree in `r`: at P2 the axisymmetric
stiffness `ε ∇u·∇v r` and the source `ρ v r` are of degree 3 and are integrated at order 2. It is a
consistency error, not a NaN, and it converges with the mesh. `poisson` assembles both terms with
one extra order: on the three-layer capacitor of VER-56, whose exact solution the P2 space contains,
the error is 0.38 `V_T` (3 %) next to the axis at the default and 1.1 × 10⁻¹³ with it. The coupled
models keep the default here, and whether their forms should gain the same order is open: it moves
every number they produce, so it is a decision with a measurement, not a side effect of WP26
(`knowledge/06-numerics-fem/02-axisymmetric-weak-forms.md#22-quadrature-verified-experimentally`). A supplied field's source term is assembled at order 8
(PHY-19's NOTE on one rule), which settles that term and not this question. **Measured by WP34**, through `Measures.weight_extra_order`, a seam no case key,
option or flag reaches (`tests/tier2/test_axis_weight_order.py`, `slow`, stabilisation `none`). On
VER-18's coupled manufactured solution at `maxh` 0.4, 0.2 and 0.1 nm, one extra order leaves the
finest-pair rates at about 3 for the P2 fields and 2.7 for the P1 pressure (`c_Cl−` 3.19 → 3.01,
`c_Na+` 3.11 → 3.03), and lowers the error at fixed `h`. The coarse-pair rates of the
concentrations fall, `c_Cl−` 3.98 → 3.65 and `c_Na+` 3.55 → 2.99: at 0 the quadrature error is a
larger share of the coarse-mesh error, and its faster decay inflates the observed rate. At 0.1 nm the error ratio is 0.42 for `c_Cl−`, 0.77 for `c_Na+`, 0.98 for `φ` and `u`
and 0.91 for `p`. So it is a consistency constant of the same order as the discretisation error, as
this NOTE predicts. On example 05's frozen case, 0.5 M at +50 mV on the reference mesh, each state
is a root of its own form (`|R|` about 2 × 10⁻¹¹) and violates the other's at 7.3 × 10⁻⁴. The
states differ by 4.9 × 10⁻⁷ relative. The current, the conductance and `t₊` move by about 10⁻¹⁰
relative or less, the electro-osmotic flow by 7.6 × 10⁻⁸, and the in-pore concentrations, mobile
charge and mean potential by 10⁻⁹ or less. At the reference mesh, the order is invisible in every
number VAL-16 and VAL-17 compare. Phase 6 decides (§8.2.5 E4, §8.2.6 F1).

### 6.3 Scaling

**NUM-09.** The equations SHALL be solved in the nondimensional variables below.

| Scale | Definition | Value or range |
|---|---|---|
| Length | `L₀ = a`, the pore radius | ≈ 2 nm |
| Potential | `φ̃ = φ/V_T`, `V_T = RT/F` | 25.693 mV at 298.15 K |
| Concentration | `c̃ = c/c₀` | — |
| Diffusivity | `D₀` | 1.334 × 10⁻⁹ m² s⁻¹ |
| Velocity | `u₀ = ε V_T²/(η a)` | — |
| Pressure | `p₀ = ε V_T²/a²` | — |
| Debye parameter | `λ̃ = λ_D/a`, `λ_D² = ε RT/(2 F² c₀)` | `λ̃ ∈ [0.088, 0.679]` at a = 2 nm |
| Péclet number | `Pe = ε V_T²/(η D₀)` | 0.386 at 298.15 K, η = 0.890 mPa·s |

NOTE: the commonly quoted `Pe` = 0.34 corresponds to η = 1.00 mPa·s, that is ≈ 20 °C; the
temperature SHALL be consistent across all material properties. At either value, convective
transport of ions is not dominant.

Debye lengths for a 1:1 electrolyte at 25 °C, which set the near-wall mesh requirement of §6.8:

| Salt concentration | `λ_D` |
|---|---|
| 0.05 M | 1.357 nm |
| 1 M | 0.304 nm |
| 3 M | 0.175 nm |

**NUM-10.** Row scaling SHALL be applied after nondimensionalisation so that the factorised system
is equilibrated. The direct solvers discharge it: UMFPACK applies its default row scaling, and the
SuperLU path divides each row by its largest magnitude (`equilibrate`). No separate field-wise block
scaling is applied; the nondimensionalisation (NUM-09) is what keeps the diagonal blocks within a few
orders of magnitude.

### 6.4 Stabilisation

#### 6.4.1 Production policy

Electromigration is the advective operator in the Nernst–Planck equation, with velocity
`b_i = z_i D_i ∇φ̃ / L₀` and cell Péclet number `Pe_h = ½ |z_i| |∇φ̃| h̃`. Inside the double layer
`|∇φ̃| ≈ |ζ̃|/λ̃_D`, so resolving it with five elements (`h̃ = λ̃_D/5`, NUM-30) gives
`Pe_h = |z_i| |ζ̃| / 10`, below 1 for a monovalent electrolyte whenever |ζ| ≲ 257 mV.

`Pe_h < 1` is a heuristic sufficient condition derived for one-dimensional linear
constant-coefficient advection–diffusion on a uniform mesh. It is stated here as a mesh design rule,
not as a proof for this nonlinear, coupled, `r`-weighted system. Chaudhry, Comer, Aksimentiev &
Olson (*Commun. Comput. Phys.* **15**, 93, 2014) report spurious negative concentrations near
charged nanopore walls with plain Galerkin on under-resolved meshes, removed by SUPG with
`σ_± = (h_τ / 2‖b_±‖)·ψ(Pe_τ)`, `ψ(q) = min(q, 1)`.

**NUM-11.** The production solve SHALL run without stabilisation. SUPG SHALL be available behind a
flag for coarse continuation meshes and default to off for the final solve.

Rationale: SUPG biases the current quantity of interest and destroys Jacobian symmetry.

**NUM-12.** The solver SHALL evaluate `Pe_h` on the assembled mesh and SHALL emit a warning naming
the element location when `Pe_h ≥ 1` anywhere in `Ω_w`.

NOTE (which `Pe_h`): the form printed above assumes the Einstein relation, `μ_i = D_i/V_T`, which
PHY-14 and VER-05 forbid at finite concentration — `D` and `μ` carry different concentration
corrections and `D_i/μ_i` drifts to 1.2–1.7 × kT/e between 0.15 M and 3 M. The implementation SHALL
therefore evaluate the cell Péclet as `Pe_K = ‖b_i‖ h_K / (2 D_i)` on the advective velocity it
actually assembles, `b_i = z_i μ_i ∇φ̃ + D_i β_i − Pe u`, and SHALL record which expression produced
the number. The printed form is the `c → 0` limit of that one and overestimates it by
`D_i/(μ_i V_T)`, so it errs towards warning early rather than late.

NOTE (when): there is no `∇φ̃` before a solve, so "on the assembled mesh" means on that mesh's
converged state. The evaluation SHALL run in every stabilisation mode, `none` included: a diagnostic
that runs only when the stabilisation is on is a diagnostic that never runs in production.

**NUM-13.** The stabilisation mode in force SHALL be recorded in the run provenance record.

#### 6.4.2 Optional reference-matching stabilised mode

The published currents were computed with consistent stabilisation active in both the transport and
the flow interfaces. An unstabilised solve is therefore a different discretisation of the same PDE,
and per-cent-level disagreement is an implementation difference rather than a defect.

**NUM-14.** An optional stabilised mode reproducing the reference settings below SHALL be provided,
and SHALL be used for like-for-like comparison against published currents (§7.4).

| Setting | Transport of Diluted Species | Flow |
|---|---|---|
| Streamline diffusion | on | on |
| Crosswind diffusion | on | on |
| Crosswind diffusion type | Do Carmo and Galeão | not recorded in the report |
| Equation residual | Approximate residual | not recorded in the report |
| Isotropic diffusion | off | off |
| Convective term | conservative form | not applicable |

NOTE (what the reference's setting names are taken to mean): COMSOL exports none of
`tds.streamline`, `tds.crosswind`, `spf.streamlinens` or `spf.crosswindns`, so the mode above
reproduces the reference's *settings* and not its operator, and the difference between the two is an
irreducible systematic in any §7.4 comparison, bounded only by mesh refinement. Three readings are
therefore fixed here rather than left to the implementation.

- **Approximate residual** means every second derivative of a trial field is dropped from the
  residual the stabilisation is built on, leaving the advective residual and its sources. The
  streamline term is then inconsistent by construction — its residual does not vanish on the exact
  solution — and the resulting loss of one order in the L² convergence rate of VER-18 is a property
  of the mode rather than a defect, and SHALL be measured and reported rather than assumed away.
- **Crosswind diffusion, Do Carmo and Galeão** means a term of that family: residual-scaled, acting
  across the streamline, and vanishing identically where the element Péclet number is at or below
  the reciprocal of its tuning constant. On a mesh meeting NUM-30 that condition holds everywhere, so
  the term SHALL be verified on a mesh coarse enough to activate it, and the fraction of elements on
  which it is active SHALL be reported with any comparison that relies on the mode.
- **Convective term in conservative form** costs nothing to match: the Nernst–Planck weak form of
  NUM-04 is already the divergence form integrated by parts.
- **The flow row's equation residual is not recorded in the report**, so the approximation above is
  applied to the momentum residual on the same rule, and that choice is this project's rather than
  the reference's. Its cost SHALL be measured and reported rather than assumed: on a stable
  (Taylor–Hood) velocity–pressure pair the flow terms are **not** asymptotically inert, and the
  resulting loss is one further order in L² — the mode converges at first order where the transport
  stabilisation alone converges at second. The reference ran its flow stabilisation on an equal-order
  pair (RSK-18), where it is what makes the pair admissible at all, so no configuration the reference
  itself ran is affected. A §7.4 comparison that pairs this mode with a stable element pair SHALL
  record that its residual is dominated by the flow terms rather than by the transport ones.

NOTE (the zero-wind linearisation): every magnitude the mode takes of a vector SHALL be floored
inside the square root. The parameters are evaluated at the iterate, so their derivative with
respect to the trial functions is structurally zero — but a backend that evaluates
`d/du ‖g‖ = (g · ∂g/∂u)/‖g‖` numerically rather than folding that zero away returns `0/0` wherever
`g` vanishes identically, and the assembled Jacobian is then singular with no diagnostic naming a
stabilisation term. `b̃_i = 0` exactly is the converged state of every rung of the NUM-18 ladder
below stage 4, so this is the ordinary path and not a corner of the envelope. The floor SHALL be
small enough to be invisible against any magnitude a solve produces, and the property SHALL be
verified on the assembled Jacobian and not on the residual, which is finite there in every mode
(VER-41).

**NUM-15.** In the mode of NUM-14 the crosswind term SHALL be assembled at integration order 6 and
the streamline term at integration order 4.

NOTE: "at integration order *n*" SHALL be read as a lower bound. The quadrature order reaching the
finite-element backend is a bonus added to an integrand-dependent estimate rather than an absolute
setting, so an implementation SHALL request a bonus of *n*, which guarantees at least order *n*.
Overshoot costs quadrature points and not correctness, which is the same trade NUM-07 already makes.

NOTE: the reference gated pseudo-time stepping off (`spf.usePseudoTimeStepping = 0`). Its
equal-order P1+P1 flow elements are LBB-unstable without this stabilisation (NUM-03).

### 6.5 Nonlinear solution and continuation

**NUM-16.** The primary nonlinear strategy SHALL be monolithic damped Newton on the fully coupled
system with a direct linear solve (§6.6), damping adapted on residual reduction and bounded below.
If the minimally damped step still fails to reduce the residual, that step SHALL be accepted rather
than the solve aborted. The reference settings SHALL be the starting point for the defaults:

| Setting | Value |
|---|---|
| Coupling | fully coupled, no segregation groups |
| Initial damping factor | 0.2 |
| Minimum damping factor | 1.0 × 10⁻² |
| Recovery damping factor | 0.2 |
| Maximum iterations | 100 |
| Relative tolerance | 1 × 10⁻⁶ |

NOTE on the relative tolerance. A criterion measured on the residual alone, relative to the
residual on entry, makes a warm start onto an already-converged state demand a further six orders of
magnitude from a residual already at its floor — which is the operation every rung of the ladder in
NUM-18 performs. The implementation therefore converges on a relative-update test evaluated on the undamped
Newton direction, field by field: for every field `f`, `‖δu_f‖ ≤ rtol · max(‖u_f‖, 10⁻⁶ · max(‖u‖, 1))`,
or when the residual is at its absolute floor, 10⁻¹². One norm over all fields is dominated by the
largest, and the residual relative to its entry value is one norm too: measured on the seven gated
walks, it closed every rung but one, and on a warm-started rung of example 03 it left the velocity
8.2 × 10⁻⁶ and the pressure 2.0 × 10⁻⁶ relatively unconverged with the ions at 2 × 10⁻⁸ (WP41 D4,
REV-08). A step that failed to reduce the residual never counts as convergence. `numerics.nonlinear.rtol` SHALL
be finite and lie in (0, 1) and `max_iter` SHALL be at least 1, because the update test can never pass
for a NaN `rtol` and every rung would then report a divergence the case caused.

**NUM-17.** The following SHALL be asserted at every Newton step, and a violation SHALL abort the
solve with a diagnostic naming the field and the spatial location:

| Assertion | Condition |
|---|---|
| Concentration positivity | `min_i c_i > 0` |
| Packing fraction | `Φ = Σ_j N_A a_j³ c_j < 1` |
| Potential increment cap | `‖δφ‖_∞ ≤ V_T` |

Rationale: `β_i` is singular at `Φ = 1`. A silently negative concentration produces a plausible but
wrong current.

**NUM-18.** The solve SHALL proceed along the continuation ladder below, each rung warm-started
from the converged state of the previous one.

1. Linear Poisson–Boltzmann.
2. Nonlinear Poisson–Boltzmann.
3. Equilibrium PNP at `V_bias` = 0, `u` = 0.
4. Ramp `σ_s` and `ρ_pore` from 0 to target.
5. Ramp `V_bias` from 0 to ±200 mV, in steps of ≈ 10 mV near onset.
6. Enable the Stokes / Navier–Stokes coupling.
7. Enable the `⟨c⟩`- and `d`-dependent `D`, `μ`, `ε`, `ϱ` corrections.
8. Enable the steric flux `β_i`.
9. Sweep salt concentration from 0.05 M to 3 M.

Rationale: enabling the corrections last isolates their contribution to any convergence failure.

NOTE: the ladder above is a fixed path, not a configuration. Flow is enabled at rung 6 and the
corrections at rung 7, so a run with `physics.flow` off, `variable_density` off, `inertia` off, or
the PHY-23 dielectric-gradient forces on is not a rung of this ladder but a different run. An
implementation SHALL NOT read those four switches from the case when `numerics.continuation` selects
the ladder, and SHALL refuse such a case rather than solve it: the FR-25 manifest would otherwise
record a deviation the solve never carried, which §5.3.3 exists to make impossible. The same applies
to `physics.model: pnp`, whose flow-free transport no rung above 6 carries. Single-rung runs
(`numerics.continuation: none`) take all four switches as given; that is how an ablation asks for a
configuration the ladder cannot express.

NOTE (FR-24, a member warm-started from a neighbour): a sweep member that starts from the converged
state of a neighbouring operating point SHALL solve the target rung alone rather than re-climbing the
ladder. That is not a departure from the fixed path above but stage 9 of it — the salt sweep, whose
rungs are warm starts one step apart — generalised to the other axes of the envelope, and re-solving
the nine rungs below a converged neighbour would re-derive the answer the neighbour already is. The
provenance manifest SHALL record the rungs actually run and the artefact hash of the state the member
started from, and a member whose neighbour is unavailable SHALL take the full ladder and record that
it did, so that a sweep's timings say which members paid for what.

**NUM-19.** The mesh SHALL be adapted between continuation rungs only, never within a rung.

**NUM-20.** The fallbacks below SHOULD be implemented in the order given, after NUM-16 is in
place.

| Fallback | Specification | Source |
|---|---|---|
| Pseudo-transient continuation | Add `M/Δt` to the Poisson and Nernst–Planck diagonal blocks and grow `Δt` by SER | Kelley & Keyes, *SIAM J. Numer. Anal.* **35**, 508 (1998) |
| Hybrid segregated | Newton on the PNP block, fixed point for Stokes, with a corrected Poisson step adding the linearised screening term `χ_F (2q²c₀/kT) φ^(k+1)` to the LHS, evaluated at `φ^k` on the RHS | Mitscha-Baude et al., *J. Comput. Phys.* **338**, 452 (2017); semiconductor Gummel map |
| Poisson–Boltzmann initial guess | Initialise from the PB solution rather than `φ = 0`, `u = 0`, `c_i = c₀`, to cure the high-surface-charge failure mode | Mitscha-Baude et al. (2017) |
| Damped Newton with ℓ₂ backtracking | Backtracking line search under the NUM-17 increment cap | Bank & Rose, *Numer. Math.* **37**, 279 (1981) |

NOTE: because the ePNP-NS model violates the Einstein relation (§4.3), the PB solution is an
approximate initialiser and not the exact zero-bias limit.

### 6.6 Linear solution

**NUM-21.** The linear systems of the 2D axisymmetric problem SHALL be solved by a sparse direct
method by default, per the configuration table below. `sparsecholesky` SHALL NOT be used.

| Path | Solver | Settings and constraints |
|---|---|---|
| Desktop, pip wheel (default) | `umfpack`, or scipy `superlu` as a BSD-licensed fallback | `sparsecholesky` is SPD-only and cannot factorise this unsymmetric coupled system; SuiteSparse UMFPACK is GPL-2+, which bears on the redistributable bundle (ADR-003) |
| HPC, source build | MUMPS via ngsPETSc / PETSc | `icntl_14 = 40` because the block system is badly scaled; BLR via `icntl_35` when memory-constrained; also unlocks `PCFIELDSPLIT` for the 3D phase |

Rationale: in 2D, nested-dissection fill is O(N log N) and factorisation O(N^1.5); direct methods
become impractical in 3D at 10⁵ to 10⁶ DOF. The NGSolve pip wheel reports `USE_MUMPS: False`
(likewise `USE_HYPRE`, `USE_PARDISO`, `USE_MKL`) and `inverse="mumps"` raises
`SparseMatrix::InverseMatrix: no inverse available for type mumps`, so MUMPS requires a source
build with MPI.

NOTE: measured on the development laptop (WSL2, 24 cores, 15 GB) on the five-field system of
NUM-01 over the analytic cylindrical pore, one configuration per process. This discharges §8.2
criterion 3 and closes the measurement RSK-10 asked for.

| Cells | DOF | Nonzeros | UMFPACK | Peak RSS | scipy SuperLU | Peak RSS |
|---|---|---|---|---|---|---|
| 1.50 × 10⁴ | 1.43 × 10⁵ | 8.4 × 10⁶ | 4.4 s | 855 MB | 24.0 s | 2593 MB |
| 3.84 × 10⁴ | 3.68 × 10⁵ | 2.2 × 10⁷ | 14.0 s | 2157 MB | 140.3 s | 8656 MB |
| 1.09 × 10⁵ | 1.04 × 10⁶ | 6.2 × 10⁷ | 41.1 s | 6171 MB | OOM-killed | > 15.4 GB |

UMFPACK meets criterion 3 with margin, at 41 s and 6.2 GB for the reference mesh size. scipy
SuperLU costs about 3.4 × the memory and 6–10 × the time, both gaps widening with problem size, and
**did not complete the reference-sized factorisation at all**, being killed by the kernel at
15.4 GB on two separate runs.

> **This conflicted with CON-11**, which said the bundled build SHOULD default to scipy SuperLU with
> UMFPACK opt-in. On this evidence that default would ship a bundle unable to run the reference
> problem. **Resolved** in favour of the measurement: the bundle defaults to
> UMFPACK and accepts the GPL-2+ obligation, the alternatives — restricting the bundled build to
> smaller meshes, or bringing NUM-22's iterative fallback forward as the BSD-licensed path — being
> rejected as shipping less capability than the reference implementation. CON-11 and ADR-003 carry
> the amended wording; the core library remains BSD-3 and depends on neither solver, UMFPACK being
> built into the NGSolve wheel.

NOTE: the reference used PARDISO with pivoting perturbation 1 × 10⁻¹³ and sparsity-pattern reuse.
PARDISO is likewise absent from the NGSolve wheel, so the reference linear solver cannot be
reproduced on the default path. The converged solution does not depend on this choice; timings do.

**NUM-22.** An iterative fallback SHALL be implemented before any 3D capability: multiplicative
`PCFIELDSPLIT` over the blocks `{(φ, c_i), (u, p)}`, algebraic multigrid per scalar block, and a
Stokes Schur complement approximated by `selfp` or the pressure mass matrix `S ≈ −μ⁻¹ M_p`.

Rationale: the multiplicative split reflects the weak PNP-to-NS coupling direction.

### 6.7 Quantity-of-interest extraction

**NUM-23.** The ionic current SHALL NOT be computed by integrating the continuous-Galerkin flux
over an interior cross-section.

Rationale: CG fluxes are not pointwise conservative, so the current differs between cross-sections
by per-cent-level amounts, which can exceed the rectification signal at low bias.

**NUM-24.** The domain-indicator form SHALL be implemented, `ψ` being a smooth indicator equal to 1
in the cis reservoir and 0 in the trans reservoir:

```
I     = F Σ_i z_i ∫_Ω J_i·∇ψ  r dr dz
Q_EOF =           ∫_Ω u·∇ψ  r dr dz
```

Rationale: it is superconvergent and cross-section independent.

NOTE (sign): with `ψ = 1` on cis, `∫_Ω J_i·∇ψ r dr dz` is by the divergence theorem and
`∇·J_i = 0` the flux of species `i` *out through the cis cap*, so the sign above references the
current to the grounded cis electrode of §5.2.2 and a positive current flows trans → cis, in `+z`.
That is the sign for which an uncharged ohmic pore has `G = I/V_bias > 0` at either sign of the
bias, which is what VER-17 asserts; earlier revisions of this clause carried a minus, which
references the trans electrode instead and negates every conductance. It is also the sign that
makes this route agree with NUM-25 evaluated on `Γ_w,c`, whose reaction flux is the same
`∮ ψ J_i·n` with the same outward normal — so a minus here would have made the NUM-26 agreement
check fail on every solution.

NOTE (`boundary_conditions.ground: trans`): the case may ground trans instead, which puts its bias
on cis. The current is still referenced to cis, so every quantity SHALL be reported against the
cis-referenced bias `φ_trans − φ_cis`, which is the negative of the case's `bias_V`, and that is the
bias the quantities record. One physical state then reports one set of numbers whichever electrode
is grounded, `G > 0` holds under either, and a sweep pairs its rectification members by the biases
they recorded (code review CR-3).

NOTE (a stabilised mode, NUM-14): under a stabilisation mode the functional above SHALL carry the
stabilisation form of the species evaluated with `ψ` as its test function, in addition to
`∫ J_i·∇ψ r dr dz`. The NUM-26 identity below is an identity between two evaluations of *the
assembled residual*, and in a stabilised mode the assembled residual contains that term; omitting it
from this route alone would make the two routes differ by exactly the quantity the mode exists to
measure, failing NUM-26 on every stabilised solve for the one reason that is not a defect. The
difference the term makes SHALL be reported per species as the stabilisation's contribution to the
current, which is NUM-11's "SUPG biases the current quantity of interest" turned into a number from a
single run rather than from a difference of two.

**NUM-25.** The variational reaction flux SHALL also be implemented: the assembled residual
evaluated against a test function equal to 1 on a Dirichlet electrode (Hughes, Engel, Mazzei &
Larson, *J. Comput. Phys.* **163**, 467, 2000).

**NUM-26.** Both routes SHALL be exercised on the same solution in continuous integration and their
agreement asserted against a declared tolerance. **That tolerance is 1 × 10⁻³ relative**, on the
total current, at every operating point of the FR-17 envelope.

Rationale for the number: the tolerance has to sit well below the smallest signal the current is
asked to resolve, which is the rectification signal `|RR − 1|` at the lowest envelope bias of
±50 mV — of order 10⁻¹ for a charged pore. A tenth of a per cent leaves two orders of margin. It is
a ceiling on a bug rather than a numerical budget: `ψ` differs from the NUM-25 boundary indicator by
a function vanishing on both electrodes, hence by a legitimate test function of the converged
residual, so the two routes are the *same* integral and what remains between them is quadrature and
the residual Newton left behind. Measured: 6 × 10⁻⁶ on the VER-11 configuration (0.5 M,
−0.05 C/m², ±50 mV, classical PNP) and 5 × 10⁻⁷ on VER-17's uncharged pore. The remainder does not
fall with the mesh — it is unchanged from 3 400 to 7 300 degrees of freedom — because it is set by
the residual Newton leaves behind and not by the discretisation.

NOTE (a precondition, not a detail): the identity above holds only where `ψ` is *exactly* 1 and 0 on
the two electrodes. Interpolated over the whole mesh it is not — the membrane spans the transition
band, and an element straddling the band shares its corner vertex with a reservoir cap, smearing
about 8 × 10⁻³ of `ψ` onto an electrode where it must vanish. `ψ` SHALL therefore be built on the
fluid domain alone. Over the whole mesh the measured route agreement on the VER-11 configuration
degrades by a factor of 170, from 4 × 10⁻⁶ to 6 × 10⁻⁴, which would pass this tolerance while being
a real error.

NOTE: the reference computed `F*(z_cpos*tds.ntflux_cpos + z_cneg*tds.ntflux_cneg)` at integration
order 4, `ntflux` being the variational reaction flux from the assembled weak residual, so the
published currents are unaffected by NUM-23.

**NUM-27.** The derived quantities below SHALL be computed from the same `ψ` integrals as NUM-24.

| Quantity | Definition |
|---|---|
| Transport number | `t₊ = I₊ / (I₊ + I₋)` |
| Rectification ratio | `RR = |I(+V)| / |I(−V)|` |
| Conductance | `G = I / V_bias` |
| Electro-osmotic flow rate | `Q_EOF` as defined in NUM-24 |

NOTE: any pore-averaged quantity reported as a regression target SHALL state whether the `2πr`
Jacobian is included, because the source work's pore averages appear to omit it while being
described as volume averages.

NOTE (this implementation's convention): the axisymmetric weak forms of §6.2 carry the `r` weight
only, the `2π` having cancelled from both sides, so every integral in the solver — including both
current routes above — is `∫ f r dr dz`. The `2π` is restored **once**, in the quantity-of-interest
extraction, so every SI quantity reported (`I`, `Q_EOF`, and everything derived from them) is a true
three-dimensional quantity and includes the full Jacobian. Because both routes inherit the same
convention, their NUM-26 agreement is independent of it while their SI values are not.

NOTE (zero bias): at `V_bias = 0` exactly, as on the equilibrium rung of §6.5 or the 0 V member of an
I–V sweep, every current is round-off (1e-27 A against 1e-25 A for the two routes on a coarse
uncharged pore), so the transport number and the conductance, each a ratio to it, SHALL be
reported as undefined (`null`) rather than computed, and the NUM-26 check SHALL NOT be applied,
because a relative difference between two round-offs is of order one whatever the extraction does.
The summary records `routes_checked: false`. The currents and `Q_EOF` are still reported, and a
case asking only for `eof_rate` at zero bias SHALL run (code review
CR-8).

**NUM-28.** The force on an embedded analyte SHALL be evaluated in domain form,

```
F_z = −∫_Ω ( T_M + T_H ) : ∇w  dV
T_M = ε ( E⊗E − ½|E|² I )        T_H = −p I + η ( ∇u + ∇uᵀ )
```

with `w` a smooth extension of `e_z` from the body, rather than as the surface integral
`F = ∮_S (T_M + T_H)·n dS`, for the superconvergence reason of NUM-24.

NOTE: the form as printed is exact only where `∇·(T_M + T_H) = 0` in the fluid. The divergence
theorem gives, in full,

```
F_z = ∮_∂B (T·n_B)·e_z dS = −∫_Ω T : ∇w dV − ∫_Ω (∇·T)·w dV
```

and in this model neither tensor is divergence-free: `∇·T_M = ρ_ion E − ½|E|²∇ε` and, from PHY-07
and PHY-08, `∇·T_H = −f + Re ϱ(u·∇)u` with `f` the body force the momentum equation actually
carries. Each contribution SHALL therefore carry its own consistency term,

```
F^em = −∫ T_M : ∇w − ∫ f_ion·w − ∫ f_KH·w
F^hd = −∫ T_H : ∇w + ∫ f·w − Re ∫ ϱ (u·∇)u·w
```

with `f_ion = ρ_ion E` (PHY-08) and `f_KH = −½|E|²∇ε` the Korteweg–Helmholtz force. Written this
way each contribution equals the traction of its own tensor over the body's surface, so the domain
and surface routes agree contribution by contribution. Omitting the consistency terms leaves the
*split* a function of where the transition shell of `w` was placed — `∫ f_ion·w` is the electrical
force on all the fluid inside that shell, a quantity of the same order as the contributions
themselves — while leaving the total almost unaffected, which is exactly the plausible wrong answer
RSK-04 describes.

NOTE: the two consistency terms cancel in the sum only when the momentum equation carries every
force the Maxwell tensor implies, that is when `f = f_ion + f_KH`. The validated model omits `f_KH`
(PHY-23), so wherever the permittivity correction is active the printed form above differs from the
force by exactly `−∫ f_KH·w`. That term SHALL be reported alongside the force rather than absorbed
into it, so that the omission is a recorded measurement and not an unexplained route discrepancy.
It vanishes identically in a classical configuration and whenever the dielectric-gradient body force
is enabled, which is why VER-22 gates classically.

NOTE: the contraction carries no `1/r` factor. For an axial `w`, `(∇w)_φφ = w_r/r = 0`, so the hoop
components of both tensors are contracted against zero and `T : ∇w = T_rz ∂_r w_z + T_zz ∂_z w_z`.
The integrals still carry the `r` weight and the NUM-07 integration-order floor, but they are not
singular forms.

NOTE: `w` SHALL be built by interpolation on the fluid alone, for the reasons NUM-24 gives for `ψ`,
and SHALL be verified to equal `e_z` on the body and zero on every other boundary before it is used;
an inverted or leaking extension returns the force on a different body with no other symptom
(QR-12).

**NUM-29.** The electromechanical and hydrodynamic contributions SHALL each be resolved to well
below 1 pN, the domain-form and surface-integral evaluations SHALL agree to better than 0.1 pN, and
the force feature SHALL carry its own mesh convergence study.

Rationale: at `V_bias` = +50 mV, `q_Hb` = −4 e and 300 mM NaCl the reference analyte case has
`|F^em| ≈ |F^hd| ≈ 10 pN` of opposite sign, so the net force is a near-cancellation of two
approximately 10 pN terms; an error in either integral flips the sign of the total and with it the
trapping landscape (RSK-04).

NOTE: agreement of the two routes on the *total* does not establish the split, and the split is what
RSK-04 concerns. An implementation MAY take a third route for `F^hd` alone — the analyte surface is
a Dirichlet boundary for `u`, so the assembled momentum residual paired with a test function equal
to `e_z` there is the traction integral itself, by the NUM-25 argument. It is independent of `w`
exactly, so it disagrees with the domain form precisely when a NUM-28 consistency term is missing or
mis-signed, which no comparison of the two stress routes can detect.

### 6.8 Mesh resolution and adaptivity

**NUM-30.** The mesh SHALL resolve the double layer to the following targets.

| Parameter | Value |
|---|---|
| First wall layer `h₁` | `λ_D/5`; 0.035 nm at 3 M, 0.27 nm at 0.05 M |
| Geometric growth ratio | 1.15 to 1.2 over ≈ 15 layers |
| Far-reservoir element size | 5 to 10 nm |
| Expected element count | 5 × 10⁴ to 2 × 10⁵ |

NOTE (the wall target and its ceiling; WP21): `h₁` is resolved as
`min(0.05 nm, λ_D/5)`, so the table's 0.27 nm at 0.05 M is never used. It would be coarser than the
ion wall function's decay length, 1/6.2 = 0.161 nm, and than stage 4's contour resolution, and
five times the validated reference's pore-boundary size. λ_D is taken at `ε_r,f⁰`, as are the
values above. The §5.3.1 NOTE on `numerics.mesh` is the contract.

NOTE: the reference reached the published results with graded free triangular meshing and no
boundary-layer node, at 120,917 triangles with minimum element quality 0.6378 and average 0.9765.

**NUM-31.** The wall-distance field `d` SHALL be computed once per mesh (eikonal solve or
screened-Poisson smoothing) as a continuous field, as required by PHY-02. A mollification pass to C¹
MAY be applied; it is a deviation from the validated model and off by default.

Rationale: `D`, `μ` and `η` depend on `d`, so a kinked distance field enters the Jacobian and
degrades Newton convergence.

**NUM-32.** Goal-oriented dual-weighted-residual adaptivity targeting the ionic current (Becker &
Rannacher, *Acta Numerica* **10**, 1, 2001) MAY be provided as an optional refinement loop. It
SHALL NOT be a v1 default.

**NUM-33.** Where the loop of NUM-32 is provided, the error estimator SHOULD be built from the
linear Poisson–Boltzmann surrogate rather than the full coupled adjoint.

Rationale: the surrogate estimator is justified on heuristic grounds only, but empirically retains
the optimal O(h²) rate in the quantity of interest at a fraction of the cost of the full adjoint.

NOTE: the published results carry no discretisation error bar. The COMSOL model report gives
element counts and mesh quality but no convergence study, so the mesh convergence study of §7 is new
work, and small disagreements with published numbers may originate in the reference's own
discretisation error.

**NUM-34.** Where any wall correction is active, the discrete wall-distance field of NUM-31 — as the
corrections read it, after mollification where the smoothing pass is applied — SHALL satisfy
`min d̄ ≥ −1 × 10⁻³ nm` over the fluid domain. A field violating it SHALL abort the run with the
QR-12 diagnostic naming the gate, the measured minimum, its location and the fraction of samples
below zero, and the measured minimum SHALL be recorded in the provenance manifest. A configuration
activating no wall correction reads no distance field and SHALL NOT be gated.

Rationale: the threshold is bounded on both sides and chosen between them. It cannot be zero,
because interpolating the field projects element-wise and leaves an interior residual of a few times
`10⁻⁴` nm whose sign is platform-dependent, so a gate at zero would gate the rounding mode. It
cannot be `10⁻²` nm, which is the ion wall function's own root `−P₂`: a gate there admits a
diffusivity of exactly zero as its last passing state, and it would restate a fitted coefficient
outside the correction data. One order inside the root and one order outside the projection residual
leaves the PHY-02 clamp free to absorb round-off — worst effect `5.8 × 10⁻³` on a factor whose wall
value is `6.0 × 10⁻²` — while refusing a field that is genuinely negative. Such a field is
under-resolved at the wall rather than marginally inaccurate, which NUM-26's route disagreement
reports independently and which the measured transition confirms: the minimum steps from
`−9.6 × 10⁻¹` nm to `+7.9 × 10⁻³` nm across a single refinement, so this gate discriminates a regime
and does not shave a tolerance.


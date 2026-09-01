# Phase 0 (Spike): coupled ePNP-NS on an analytic cylindrical pore

**Status: WP1–WP6 merged. Phase 0 complete on criteria 1–3; criterion 4 is out of scope by
amendment A2.** Last revised 1 September 2026, after WP6. Everything gated — tiers 1 and 2,
VER-11 … VER-22 included — is green; the thirty-point envelope run is recorded under criterion 2
and the force benchmarks under criterion 1.

This is the delivery plan for Phase 0 of `SPECIFICATION.md` §8.1, as amended by §8.2.1. The
specification remains normative: where this file and the specification disagree, the specification
governs and this file is wrong. Requirement identifiers here are pointers into it, not restatements
of it.

## Context

Phase 0 is the spike: coupled ePNP-NS on an *analytic* cylindrical pore — no structure pipeline, no
contour extraction, no mesh generation from density — with the continuation ladder, the Tier 1 and
Tier 2 suites, and the §8.2 exit criteria as the gate. Estimate in the specification: 3–5 weeks.

The point of the phase is criterion 1: the analytic benchmarks establish that the physics and the
axisymmetric discretisation are correct *independently of any other implementation*, before anything
is compared against COMSOL or experiment. An analytic test localises an error to a single term; a
whole-model comparison localises nothing.

Amendments agreed with the user on 19 August 2026 are recorded normatively in §8.2.1 as A1, A2 and
A3: Tier-2 scope is the full VER-12 … VER-22 including the analyte-force benchmarks; criterion 4
(the PySide6 + `webgui` Windows bundle) is deferred and recorded as deliberately unmet, leaving
RSK-13 open; and the COMSOL comparison moves to Phase 1 in full.

**Delivery is one PR per work package**, each green on tiers 1 and 2 before the next starts.

## Design decisions

- **Nondimensional solve** per NUM-09 (length `a`, potential `V_T`, concentration `c₀`, `D₀`,
  `u₀ = εV_T²/(ηa)`, `p₀ = εV_T²/a²`), with field-wise row scaling (NUM-10). QoIs are converted back
  to SI at the boundary of `post/`. Implemented in `core/scaling.py`.
- **Correction forms are written once against a dispatchable math namespace** so the same expression
  evaluates with floats/NumPy (unit tests, VER-03) and with NGSolve `CoefficientFunction`s
  (assembly, where the symbolic Jacobian needs them). No duplicated formulae.
- **Both a `dx_axi` and a planar measure.** The 1D benchmarks (VER-12 Gouy–Chapman, VER-16 PNP
  limiting current) are exact in planar geometry and misleading if forced onto an axisymmetric slab;
  the same weak-form code takes the measure as an argument.
- **Configuration stays minimal and deliberately unfrozen** — a small pydantic model in `core/`, not
  the `nanopnp/case/v1` schema. Freezing the case file is v0.5 / Phase 1 work (FR-26, VER-09), and
  freezing it against a spike's needs would be the wrong shape.
- **New base dependency: `sympy`** (BSD, pure Python, wheels everywhere) for the manufactured
  solutions of VER-18. It is imported by `validation/`, a shipped module, so it belongs in the base
  dependencies rather than the dev group. Added in WP4.

## Conventions established by WP1–WP3

These were not in the original plan. They were settled by the merged work and its reviews, and
WP4–WP6 inherit them.

- **`core/typing.py` carries the NGSolve protocol aliases.** NGSolve ships no usable type
  information, so annotations go through those aliases rather than `Any`; `mypy --strict` stays
  clean over `src/`. New modules extend that file rather than importing `ngsolve` for its types.
- **`ngsolve`, `netgen` and `numpy` are imported inside the function that uses them**; everything
  else is imported at module scope. The CLI, GUI and sweep runner import stage modules purely to
  introspect a stage (FR-27) without assembling anything, and a job array pays that cost per
  process. The rule and its measurements are in `CLAUDE.md`.
- **`.claude/hooks/gate.sh` runs the full gate before any commit Claude Code makes** and refuses the
  commit with the failing output.
- **`physics/measures.Measures` is the only route to an integration measure.** It owns the radial
  weight and the NUM-07/NUM-08 order guarantee, and it refuses a `bonus_intorder` passed behind that
  guarantee. Forms carrying `1/r` ask for `singular=True` rather than choosing an order themselves.
- **`materials/models.py` is the template for a registry**: `register` / `registered_models` /
  `create`, with `none` a registered model rather than a code branch. `physics/models.py` follows it.
- **Newton tests both the residual and the relative update on the undamped direction.** A criterion
  on the residual alone, relative to entry, demands another six orders of magnitude from an
  already-converged state — which is exactly what every rung of the continuation ladder does. A
  forced step never counts as convergence.
- **`post/reaction_flux.py` landed in WP2**, ahead of the plan, because the WP2 review would not
  accept a quadrature guarantee that nothing exercised. NUM-25 is therefore done; WP5 is left with
  the ψ-indicator route and the QoIs derived from it.
- **The `2π` is restored once, in `post/qoi.py`, and nowhere else.** `Measures` cancels it from both
  sides of the weak form, so every integral in the solver is `∫ f r dr dz`; every SI quantity `post/`
  reports is a true three-dimensional one. Recorded under NUM-27 in the specification, as its NOTE
  requires. WP6's forces inherit the convention and must not apply the factor a second time.
- **A converged solution carries the residual form it solves and the wall-distance field it was
  assembled with.** Rebuilding the form to take a NUM-25 flux is not merely wasteful: a coupled
  residual reassembled without the same `wall_distance_nm` is a *different operator*, and the flux
  taken against it is wrong with no diagnostic.
- **A model can be cold-started through `cold_state`, which is part of the `PhysicsModel` protocol.**
  The ladder transfers a solution onto a larger field set and must fill the new fields from something
  the model itself calls admissible; `c̃_i = 0` fails the NUM-17 positivity gate on entry.

## Work packages

### WP1 — Correction registry and materials layer — **merged, PR #2**

`materials/forms.py`, `materials/models.py`, `materials/electrolyte.py`; spec amendment §8.2.1.

Delivered: the five functional forms of PHY-11, each written once and dispatchable over NumPy or
NGSolve, including the two wall functions with their *opposite* offset signs; the `CorrectionModel`
protocol of §5.4.2 with `none` registered rather than branched (PHY-22), which is what makes
`pnp-ns` a configuration (PHY-21); `⟨c⟩` as the arithmetic mean with per-species clamping to
[1e-6 M, 5.3 M] (PHY-01) and ionic strength as a separately named option, clamping logged with
property and location (PHY-13); `μ_i` derived from `D_i⁰` per PHY-14, never fitted independently.
Discharges VER-03, VER-04, VER-05, and exact recovery of PNP-NS when every correction is `none`.

### WP2 — Axisymmetric forms, meshes, wall distance, electrostatic benchmarks — **merged, PR #3**

`physics/measures.py`, `physics/poisson.py`, `physics/pb.py`, `mesh/primitives.py`,
`mesh/distance.py`, and — beyond the plan — `core/typing.py` and `post/reaction_flux.py`.

Delivered: `dx_axi` with the asserted integration order ≥ 3 on every form carrying `1/r`, enforced
at assembly rather than left to defaults; analytic geometries via `netgen.occ` (planar slab,
cylinder, cylindrical pore with hemispherical reservoirs and a membrane slab), graded to
`h₁ ≈ λ_D/5` at the wall (NUM-30); the wall-distance field (PHY-02, NUM-31), mollified to C¹, with
the membrane excluded from the source set; the `poisson`, `pb` and `pb-linear` models, `pb` being a
distinct model and never the PNP solver at zero bias (PHY-24). Discharges VER-06, VER-07, VER-12,
VER-13, and implements NUM-25.

### WP3 — Scaling, damped Newton, gates, linear solver — **merged, PR #4**

`core/scaling.py`, `solve/newton.py`, `solve/linear.py`, `solve/gates.py`.

Delivered: NUM-09 nondimensionalisation and its inverse, and NUM-10 field-wise row scaling; damped
Newton with the reference settings as defaults, accepting a minimally damped step rather than
aborting (NUM-16); the three NUM-17 / PHY-06 gates, each aborting with the field and the spatial
location; `umfpack` with a scipy `superlu` fallback and `sparsecholesky` rejected explicitly as
SPD-only (NUM-21). Discharges VER-08 and §8.2 criterion 3.

Two findings worth carrying forward. **Criterion 3 is met by UMFPACK with margin** — 41 s and 6.2 GB
on the reference mesh size (1.09 × 10⁵ cells, 1.04 × 10⁶ DOF), memory near-linear in DOF and time
≈ N^1.1, better than the O(N^1.5) worst case; NUM-22's iterative fallback is not needed for the 2D
phase. And **scipy SuperLU never completed that factorisation**, being killed by the kernel at
15.4 GB on two separate runs, which puts the measurement in conflict with CON-11. The full table and
the conflict are recorded under §6.6 of the specification.

### WP4 — Nernst–Planck, flow, the coupled model, MMS — **merged**

`physics/nernst_planck.py`, `physics/flow.py`, `physics/models.py`, `validation/mms.py`, and —
beyond the plan — `physics/coefficients.py`; adds `sympy` to the base dependencies.

Delivered: Nernst–Planck in primitive `c_i` with the NUM-02 log branch behind a flag and Slotboom
rejected in the docstring; the steric `β_i` with the PHY-05 sign discipline, the sum retained over
all species and the `a_i³/a_0³` prefactor kept (4.16 for NaCl, asserted). Taylor–Hood P2/P1 flow
with the hoop-strain term, the variable-density continuity of PHY-07 and the `ρ_ion E` body force
of PHY-08; `dielectric_gradient_forces` enables the momentum and Nernst–Planck terms together and
only together, default off (PHY-23). The `PhysicsModel` registry of §5.4.3 with `epnp-ns`,
`pnp-ns`, `pnp`, `pb`, `pb-linear` and `poisson`, `pnp-ns` being the same class as `epnp-ns` with
every correction resolving to `none`. MMS machinery on the full coupled axisymmetric system, and
the WP3 state gates wired into the coupled solve. Discharges VER-14, VER-15, VER-16, VER-18 and
implements FR-20, NUM-02, NUM-03, NUM-05.

Five things settled by the work that WP5 and WP6 inherit.

- **`physics/coefficients.py` is the single conversion to nondimensional material coefficients.**
  It owns `D̃_i`, `μ̃_i`, `η̃`, `ϱ̃`, `ε̃_r` and the three groups `S = F c₀ L₀²/(ε V_T)`, `Pe` and
  `Re`. **The reference length is the mesh unit**: `mesh_unit_scales` builds a `Scales` with
  `length_nm = 1.0` and the constructor refuses anything else, because the mesh is in nm and
  scaling lengths by a 2 nm pore radius instead would leave every gradient wrong by that factor
  with no diagnostic. `S` is the `1/(2λ²)` of `physics/pb.py`, computed from its definition so an
  asymmetric electrolyte is right too.
- **`d̂iv u` is a `1/r` form in its own right.** The `u_r/r` piece is evaluated before the `r`
  weight multiplies it, so the continuity and pressure blocks need the NUM-07 guarantee exactly as
  the hoop term does. Every measure touching a divergence passes `singular=True`.
- **Velocity continuity is assembled as `ϱ̃ d̂iv ũ`.** PHY-07's `∇·(ϱu) − u·∇ϱ` collapses to that
  identically, so forming the two terms would add a symbolic derivative of the whole correction
  chain to the Jacobian for no change in the answer. The consequence is worth stating: the
  variable-density system leaves the velocity field satisfying `d̂iv ũ = 0` just as the
  constant-density one does, and the density reaches the answer through the inertia term alone.
- **`Set(cf, definedon=region)` zeroes everything outside the region**, so applying essential data
  after an initial guess destroys the guess — and destroys the state a warm start is starting
  from. `models._set_boundary_values` interpolates on a scratch function and copies only the
  region's degrees of freedom. WP5's ladder depends on that.
- **A gate sampling a subdomain field must sample only that subdomain, and strictly inside it.**
  `FieldSampler` gained a `materials` filter, because a concentration evaluated outside its
  `definedon` region returns zero and the positivity gate would abort on the membrane before Newton
  took a step. Filtering elements is not enough: a node on the fluid/solid interface can still
  resolve into the solid, so the points are pulled `1e-4` towards their own element's centroid —
  measured, 1e-6 is too small and 1e-5 is the first that works.

Two findings worth carrying forward. **The MMS rates are clean**: 3.0–3.6 for `φ`, `c_i` and `u`
and 2.7 for the Taylor–Hood pressure, over `maxh` 0.4 → 0.1 nm on a 2 × 4 nm cylinder, about
2 × 10⁴ DOF at the finest — three orders below the WP3 budget. The P1 pressure converging at O(h²)
rather than O(h³) is the pair's own rate, not a shortfall. And **the envelope is going to need the
ladder**: a cold `epnp-ns` solve at 5 M with a wall at −4 `V_T` aborts on the co-ion positivity
gate, and the classical configuration aborts on packing. Both aborts are correct; both are exactly
what NUM-18's warm start exists to avoid, and WP5 should not read them as defects.

### WP5 — Continuation ladder, QoI extraction, the envelope — **merged**

`solve/continuation.py`, `post/qoi.py`, `post/indicator.py`. Implementation plan:
`wp5-continuation-qoi-envelope.md`. Discharges FR-17, FR-23, QR-04, VER-11, VER-17 and §8.2
criterion 2, and retires RSK-03.

- The nine stages of NUM-18, warm-started rung to rung, corrections enabled last (stages 7–8) so
  that a convergence failure attributes to one term. Stages 4, 5 and 9 are ramps and expand into
  several rungs each, so every `Rung` carries the stage it belongs to and conformance to NUM-18's
  order is a property of the sequence rather than of its length. NUM-19 is satisfied structurally:
  the mesh is a rung's own property and nothing changes it during a solve.
- The ψ-domain-indicator current (NUM-24), the variational reaction flux from WP2 (NUM-25), their
  agreement checked before any number is returned (NUM-26), and `t₊`, `RR`, `G`, `Q_EOF` derived
  from the same ψ integrals (NUM-27). Never a cross-section integral of the CG flux (NUM-23).
- VER-11 and VER-17 as Tier-2 gates, and the §8.2 criterion 2 envelope as a `slow`, non-gating
  measurement that records the mesh it ran on.

Eleven things settled by the work, which WP6 inherits.

- **`transfer` is the mechanism the plan identified as missing, and it was.** `CoupledModel.solve`
  warm-starts by reusing `initial.space`, which is right whenever the field set is unchanged; stage
  2 → 3 adds the concentrations and stage 5 → 6 adds `u` and `p`. `continuation.transfer` builds the
  target space, cold-starts it, and interpolates the shared fields by name — or copies the vector
  verbatim where the field sets match, which is both faster and exact, and which stages 4, 5, 7, 8
  and 9 all take.
- **Warm-start idempotence costs one iteration, not zero.** NUM-16's convergence test is on the
  relative update, and an update is not knowable without assembling the Jacobian and solving once;
  the entry-side test is on the residual, which a converged warm start does not pass because it is
  measured relative to itself. So every rung pays one assembly and one solve to establish that it
  has nothing to do, and the re-solved state moves by 5 × 10⁻⁹ relative. The alternative is worse: a
  residual-only criterion demands another six orders of magnitude and the ladder never leaves stage 2.
- **NUM-24's printed sign was wrong for its own electrode convention, and the specification is
  amended.** With `ψ = 1` on cis, `∫_Ω J_i·∇ψ` is the efflux through the cis cap, so the minus
  references the *trans* electrode — which makes `G = I/V_bias` negative for an ohmic pore against
  VER-17, and negates this route relative to NUM-25 on the same boundary, so NUM-26's agreement
  check could never have passed. The clause now carries the plus, with the derivation.
- **ψ must be built on the fluid domain alone, and this is load-bearing.** The two routes agree
  because ψ differs from the NUM-25 boundary indicator by a function vanishing on both electrodes;
  that needs ψ to be *exactly* 1 and 0 there. Over the whole mesh it is not — the membrane spans the
  transition band and a straddling element shares its corner vertex with a reservoir cap, leaking
  8 × 10⁻³ onto an electrode. Cost: a factor of 170 in the route agreement, 6 × 10⁻⁴ instead of
  4 × 10⁻⁶, which would have passed the declared tolerance while being a real error.
- **The surface-charge term was missing.** `physics/poisson.py` has had `surface_charge_source` since
  WP2 and nothing called it, so NUM-18 stage 4 could not ramp `σ_s` as written. `CoupledModel`
  now assembles it, and `Scales` gained the `charge_density` and `surface_charge` scales that put an
  SI value on the ramp.
- **A saturated distance field disables half the correction set, silently.** Every correction is a
  concentration factor times a wall factor in `d`, so `SATURATED_WALL_DISTANCE_NM` — the honest way
  to say "no wall correction is active" at a call site — leaves a run exercising the concentration
  half alone while looking, from the switches, fully corrected. Every configuration in WP5 that
  claims "every correction active" is handed a real PHY-02 distance field from the pore wall alone.
  And because `d` is a *discrete* field, it travels with the solution rather than being recomputed:
  two calls to the distance solver differ at round-off, and a residual reassembled against the second
  is a different operator from the one that was solved.
- **The ablation now measures what it is for.** ePNP-NS against PNP-NS at 3 M, +200 mV, same mesh,
  same operating point, same code path: the corrections reduce the conductance by a factor **0.452**,
  which is the mobility correction (`μ/μ⁰` = 0.465 for Na⁺, 0.552 for Cl⁻) showing through almost
  undiluted. Before the fix below it measured 1.0009. The classical arm is also a free check on
  VER-17 at the other end of the salt range: at 3 M with a double layer a tenth of the pore radius it
  gives `G` = 2.9495 × 10⁻⁸ S against Maxwell–Hall's 2.95 × 10⁻⁸ S, four digits.
- **An electrolyte's switches were a record, not the behaviour — and WP5's ablation is what caught
  it.** `Electrolyte` resolves its correction switches to correction models once, at construction,
  and every property accessor reads the resolved dict; `switches` is never consulted again. So
  `replace(electrolyte, switches=classical())` returned an object that reported PNP-NS in its FR-25
  provenance and evaluated the full ePNP-NS set. Two callers did exactly that — `models.create`'s
  `classical=True` path whenever an electrolyte is passed explicitly, and `default_ladder` — so every
  stage of every ladder ran fully corrected, the ones labelled classical included. The ablation
  measured a conductance ratio of 1.0009 at 3 M where the mobility correction alone is a factor of
  about 0.5, which is what exposed it. `Electrolyte.with_switches` now rebuilds the resolved models
  and `__post_init__` refuses a pair that disagrees. **A configuration that cannot be trusted to be
  the configuration it names makes §7.4's ablation compare a run against itself**, so WP6's force
  ablations depend on this too.
- **VER-16 was passing on two errors that cancelled**, and the fix above turned it red. It passes an
  electrolyte explicitly, so it had never once run classically. Its 100 nm film is
  space-charge-limited rather than electroneutral — the giveaway is that the plateau current does not
  depend on the electrode concentration at all — which reads 14 % high against the closed form, while
  the silently-active corrections broke the Einstein relation the factor of 2 rests on and pulled it
  down by about as much. The screening length that governs is not the bulk 0.30 nm but the 9.6 nm at
  the depleted electrode. Measured convergence: 1.138 at L = 100 nm, 1.050 at 400, 1.026 at 1000,
  1.017 at 2000. The film is now 2000 nm at no extra cost.
- **The wall grading of NUM-30 decides whether the ladder converges, not only how accurate it is.**
  Stage 4 ramps `σ_s` while the model is still classical, and the field that fails first is the
  *co-ion*: against a negative wall the anion is depleted as `exp(−|φ̃|)`, so a Newton step in the
  primitive variable overshoots it through zero. At the full `λ_D(3 M)/5` grading the ladder climbs
  −0.05 C/m²; on a wall mesh 2.6 times coarser the NUM-17 positivity gate aborts at the first charge
  sub-step, naming `c_Cl⁻ = −0.76` at `r = 2 nm` — on the wall, exactly where it should look. Both
  behaviours are correct: the coarse mesh does not resolve the layer, the step is too long, and the
  gate is what stops a negative concentration becoming a plausible wrong current. The consequence for planning is
  that a reduced mesh buys less than its element count suggests — it costs robustness at the charged
  end — and that a strongly charged pore will want the Poisson–Boltzmann initial guess NUM-20 names
  for exactly this failure mode. `default_ladder` already takes a `wall_potential_V` for it.
- **A symmetric pore is the sharp test for RSK-03, not a rectifying one.** VER-11 asks for agreement
  finer than the rectification signal, but the reference pore's signal is a property of *its*
  asymmetry and no Tier-2 geometry has it. `CylindricalPoreGeometry` cannot rectify at all, so any
  `RR ≠ 1` it reports is manufactured by the extraction — which is exactly the failure mode. The
  benchmark measures the spurious signal instead: `RR` = 1.000021.

### WP6 — Analyte body and force benchmarks — **merged**

`geometry/analyte.py`, `post/forces.py`. Implementation plan: `wp6-analyte-and-forces.md`.
Discharges FR-21, CON-02, VER-19, VER-20, VER-21, VER-22, implements NUM-28 and NUM-29, closes
§8.2 criterion 1 and retires RSK-04.

- Rigid body of revolution on the axis, glued into the fluid domain as a named `analyte` material
  rather than cut out of it, and treated as a hard dielectric: no ion flux, no-slip, dielectric
  jump (FR-21, author ruling 4). `SphereBody` and `SpheroidBody`, an `AnalyteInBoxGeometry` for the
  benchmarks and a `PoreWithAnalyte` that keeps the whole `axis` / `wall` / `membrane` / `cis` /
  `trans` vocabulary intact, so `lumen_band`, `axial_indicator` and the default `CoupledBoundaries`
  work on it unchanged. Because the fluid regex already excludes the body, `n·J_i = 0` and the
  dielectric jump are natural (PHY-09) and only no-slip is essential.
- Force in **domain form**, `F_z = −∫_Ω (T_M + T_H) : ∇w dV` with `w` a smooth extension of `e_z`
  (NUM-28), the surface form `∮_S (T_M + T_H)·n dS` as the cross-check, and the variational
  reaction force on the no-slip surface as a third route for the hydrodynamic half. Two corrections
  to the bullets this section carried before the work:
  - **The `∇w` contraction carries no `1/r` hoop component.** For an axial `w`, `(∇w)_φφ = w_r/r`
    is identically zero, so the hoop stresses are contracted against nothing and
    `T:∇w = T_rz ∂_r w_z + T_zz ∂_z w_z`. The integrals still go through `Measures` for the `r`
    weight, the order floor and the non-finite abort, but `singular=True` is not required and
    asserting it would have been cargo cult.
  - **The domain form is exact only once each component carries its body-force consistency term.**
    `∇·T ≠ 0` in this model, so `F_z = −∫T:∇w − ∫(∇·T)·w`; the two consistency terms cancel in the
    total but not in the split, and the `∫ρ_ion E·w` piece is an O(10 pN) function of where `w`'s
    transition shell was put. Omitting it leaves the routes in perfect agreement on a total that is
    right and a split that is wrong — which is exactly the plausible wrong answer RSK-04 describes.
- Tests: VER-19 Stokes drag `6πηaU`, VER-20 Maxwell stress on a dielectric sphere in a uniform
  field (net force zero, and the `F = qE₀` magnitude anchor a zero test cannot supply), VER-21 the
  Hückel and Smoluchowski mobility limits against Henry's function, VER-22 the routes agreeing to
  better than 0.1 pN on one solution (NUM-29), and a `slow` mesh convergence study with a
  reference-shaped record. Measured results under criterion 1 below.

Five things settled by the work.

- **Route C is the oracle on the split, and it is a discrete identity rather than a third
  approximation.** The analyte surface is Dirichlet for `u`, so the assembled momentum residual
  paired with a velocity-block test function equal to `e_z` there *is* `∮(T_H·n)·e_z`. The residual
  vanishes on every free degree of freedom, so route C never sees `w` at all: it disagrees with
  route A precisely when a consistency term is missing or mis-signed, and in no other case. On the
  VER-22 configuration it confirms route A's `F^hd` to 1.3 × 10⁻⁴ pN and on the finest mesh of the
  study to 3.4 × 10⁻⁵ pN, three to four orders inside the 0.1 pN NUM-29 asks of routes A and B.
- **The routes' agreement does not fall monotonically under refinement; the oracle's does.** A–B
  measured 1.76 × 10⁻², 2.72 × 10⁻² and 1.30 × 10⁻² pN over the three meshes — two independent
  quadratures of two different objects, each converging at its own rate, so their difference need
  not be monotone and asserting that it is would have been asserting something untrue. A–C fell
  4.62 × 10⁻⁴ → 1.30 × 10⁻⁴ → 3.40 × 10⁻⁵ pN, which is monotone and is asserted.
- **`T_H`'s sign convention has to be pinned in one place and never mixed.** `post/forces` returns
  `−p I + 2η sym ∇u`, the convention the momentum equation is assembled in; `.knowledge/05` §4
  prints the negative of that. Both are defensible and the difference is invisible in a zero test,
  so the docstring states which one the code holds and the reaction route is what would catch a
  slip. `T_M` has no such ambiguity — `E` appears twice.
- **A far field chosen for convenience can make a benchmark measure nothing.** VER-19 imposes the
  closed-form Stokes field on the outer boundary rather than a uniform `u = U`, because the latter
  adds a Faxén wall correction of order `a/R` and the test would then be measuring the truncation
  of the domain. VER-21 reverses the rule: there the force-free translating-plus-field combination
  radiates no Stokeslet, so a uniform far field is the right one and the exact-Stokes boundary
  would be wrong.
- **The Varadhan distance field's diffusion length must be sized for the feature it has to
  resolve.** `w`'s transition shell is nanometres wide, not the 0.2 nm the wall corrections want;
  at the default `√t` the field is unresolvable on a benchmark-sized mesh and corrupts `w` rather
  than failing. `axial_extension` now defaults `diffusion_length_nm` to a quarter of its own shell
  width, and `check_extension` asserts `w = e_z` on the body and `w = 0` on the outer boundaries
  so a leaking or inverted band is a loud failure instead of a wrong force.

## Open decisions

| # | Decision | Status |
|---|---|---|
| ADR-003 / CON-11 | CON-11 says the redistributable bundle SHOULD default to scipy SuperLU (BSD) with UMFPACK (GPL-2+) opt-in. The WP3 measurement shows SuperLU cannot factorise the reference problem on the development laptop at all. Resolving it means accepting the GPL-2+ obligation for the bundle, restricting the bundled build to smaller meshes, or bringing NUM-22's iterative fallback forward as the BSD path. | **Open — for the user.** Recorded in §6.6, not resolved unilaterally. Does not block WP4; it blocks any statement about what the bundle ships. |

## Verification

Every work package must leave `uv run pytest` green before the next starts; that is tiers 1 and 2,
which is exactly the Phase 0 acceptance gate.

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src/ && uv run pytest
uv run pytest -m tier2 -v                       # the analytic benchmark ladder, VER-12 … VER-22
uv run pytest -m slow --log-cli-level=INFO      # envelope run and factorisation benchmark, not gating
```

Phase 0 is complete when, on the analytic cylindrical pore:

1. **VER-12 … VER-22 all pass**, including MMS convergence at O(h³) in L² for P2 on the full coupled
   axisymmetric system, and the two force routes agreeing to better than 0.1 pN. **Met**, VER-11 …
   VER-18 in WP2–WP5 and VER-19 … VER-22 in WP6. VER-17 came in at 0.15 % against the Maxwell–Hall
   form on a 50 nm reservoir and 0.39 % on a 100 nm one, `G` moving 0.23 % between them — so the
   2 % is measuring the discretisation, not the truncation of the domain. The four force
   benchmarks, all at a stated tolerance:

   | benchmark | reference | measured | tolerance |
   |---|---|---|---|
   | VER-19 Stokes drag | `6πηaU` = 0.430491 pN | 0.430870, 0.430522, 0.430500 pN over three meshes — relative error 8.80 × 10⁻⁴ → 7.11 × 10⁻⁵ → 1.98 × 10⁻⁵, observed rates 3.63 and 1.85 | 1 % on the finest |
   | VER-20 dielectric sphere, net force | 0 | −8.6 × 10⁻⁸ pN by the domain route, +7.0 × 10⁻⁵ pN by the surface route | ≪ 0.1 pN |
   | VER-20 magnitude anchor | `qE₀` = −8.23281 pN | −8.21704 pN (1.9 × 10⁻³) domain, −8.18903 pN (5.3 × 10⁻³) surface | 1 % |
   | VER-21 mobility | Henry's `f(κa)` | κa = 0.50: `μ̃_e` 0.3282 against Hückel 0.3312 and Henry 0.3360. κa = 2.08: 0.3501 against Henry 0.3534. κa = 16.47: 0.4317 against Henry 0.4383 and Smoluchowski 0.4953 | 5 % against Henry and Hückel; 15 % against Smoluchowski at the largest κa, argued below |
   | VER-22 route agreement | routes A, B, C on one solution | A–B 0.027 pN, A–C 1.3 × 10⁻⁴ pN, on a solution whose halves are `F^em` = −15.4 pN and `F^hd` = +9.9 pN | 0.1 pN absolute; 10⁻³ pN for the oracle |

   The tolerance is **absolute** throughout, because a relative test on a total that is a small
   difference of two large numbers reports an agreement the split does not have. NUM-29's
   convergence study is a `slow`, non-gating measurement: three refinements at 1 033, 1 734 and
   3 360 elements (9 980 → 32 342 dof), each of `F^em`, `F^hd` and `F^tot` resolved with a last
   refinement step under 0.01 pN. The reference-shaped record — a 6.7 × 5.8 nm spheroid in a
   4.5 nm-radius lumen at 300 mM, +50 mV, `q` = −4 e, `ε_p` = 20, −0.02 C/m² of wall charge, all
   corrections active, reached in 19 rungs — reports `F^em` = −1.9492 pN against `F^hd` = +4.3284 pN
   for a net +2.3792 pN, with the omitted Korteweg–Helmholtz term of PHY-23 measured at
   −4.02 × 10⁻⁴ pN rather than assumed zero.
2. **The envelope converges**: 0.05–3 M × ±200 mV with all corrections active, reached through the
   continuation ladder, with no negative concentration at any Newton iterate. **Met in WP5.** All
   thirty points of a five-concentration × six-bias grid, every correction genuinely active against a
   real PHY-02 distance field, at −0.02 C/m² on a reduced mesh (3 236 elements, `maxh` 6 nm,
   `wall_h` 0.09 nm): one climb of 13 rungs and 51 iterations, then 205 warm-started iterations over
   621 s, **no gate violation and no rung below 0.1 damping**. The hard corner — 3 M, +200 mV,
   −0.05 C/m² — is also climbed from cold on the full NUM-30 `λ_D(3 M)/5` mesh: 22 rungs, 114
   iterations, 252 s at 64 784 degrees of freedom, minimum damping 0.051.

   | salt | G (S) | t₊ | bulk t₊ | excess over bulk |
   |---|---|---|---|---|
   | 0.05 M | 4.80 × 10⁻¹⁰ | 0.870 | 0.388 | 0.482 |
   | 0.15 M | 1.06 × 10⁻⁹ | 0.662 | 0.383 | 0.280 |
   | 0.50 M | 3.11 × 10⁻⁹ | 0.486 | 0.373 | 0.113 |
   | 1.0 M | 5.77 × 10⁻⁹ | 0.432 | 0.366 | 0.066 |
   | 3.0 M | 1.33 × 10⁻⁸ | 0.384 | 0.356 | 0.028 |

   The two current routes agree to between 5 × 10⁻⁹ and 1.4 × 10⁻⁶ at every one of the thirty points,
   three to six orders inside NUM-26's declared 10⁻³. The selectivity the wall charge buys over the
   bulk electrolyte is screened away as the salt rises — 94 % of it gone by 3 M, where the double
   layer is a tenth of the pore radius — which is the physics the envelope exists to demonstrate.
3. **The factorisation benchmark reports** time and peak memory for a production-sized problem on
   this laptop, with a verdict on whether UMFPACK or SuperLU is viable (RSK-10). **Met in WP3**:
   UMFPACK, 41 s and 6.2 GB at 1.04 × 10⁶ DOF; SuperLU not viable at that size.
4. Criterion 4 (Windows GUI bundle) is **explicitly not met**, by amendment A2; the specification
   says so and RSK-13 stays open. It is the only criterion outstanding: 1, 2 and 3 are met, so
   Phase 0 is complete on everything A2 left in scope.

## End-of-phase report

The report the plan asks for: the observed MMS convergence rates, the factorisation timing, which
ladder rungs needed damping below 0.1, and any benchmark whose tolerance had to be argued rather
than met — the last being the one that matters most for Phase 1's COMSOL comparison.

**Observed MMS convergence rates.** VER-18, the full coupled axisymmetric system with P2 elements,
converges at O(h³) in L² as specified; the electrostatic and transport benchmarks of WP2 and WP4
carry their own rates in `tests/tier2/`. VER-19's drag is the one rate measured under WP6, and it
is not an MMS rate: 3.63 between the first two meshes and 1.85 between the second and third, the
fall reflecting that the error has reached the 2 × 10⁻⁵ floor set by the truncation of the domain
at `R = 10a` rather than any loss of order.

**Factorisation timing.** UMFPACK, 41 s and 6.2 GB at 1.04 × 10⁶ degrees of freedom on the
development laptop; SuperLU cannot factorise the reference problem at that size at all (WP3,
RSK-10). The consequence for the redistributable bundle is ADR-003 / CON-11, which stays open under
"Open decisions" above.

**Damping below 0.1 is needed only by the stage-4 charge ramp, and only at the charged end.** The
thirty-point envelope at −0.02 C/m² never went below the initial 0.2 on any rung, and the hard
corner at 3 M / +200 mV / −0.05 C/m² reached 0.051 on the second charge sub-step and nowhere else.
Every other rung of every ladder in Phase 0 held at 0.2, the reference-shaped WP6 case with an
embedded charged body included: 19 rungs, minimum damping 0.2 throughout.

**Tolerances argued rather than met — one, and it is VER-21's.** Everything else came in with
orders of margin: VER-17 at 0.15 % against 2 %, the NUM-26 current-route agreement between
5 × 10⁻⁹ and 1.4 × 10⁻⁶ against a declared 10⁻³, VER-22's route agreement at 0.027 pN against
0.1 pN with the oracle three further orders inside that, and VER-19 at 2 × 10⁻⁵ against 1 %.

VER-21's Smoluchowski limit is the exception, and the specification was amended rather than the
number accommodated. The specified reference `μ_e = εζ/η` is a `κa → ∞` limit; the largest κa that
fits in a Tier-2 budget is 16.5, and **Henry's own function is 11.5 % below `εζ/η` there**. A 5 %
assertion against Smoluchowski at that κa would have been asserting something untrue of the
physics, so §7.3 now states Henry as the reference — recovered to better than 5 % at every κa
tested — with the Smoluchowski gap allowed 15 % and required to be no larger than Henry's own gap
at the same κa. That is a real tolerance on a real quantity rather than a slackened one on the
wrong quantity, but it is an argued tolerance and Phase 1's COMSOL comparison should treat it as
the one place where Phase 0's evidence is a trend towards a limit rather than agreement with it.

Two further things Phase 1 inherits, neither a tolerance but both able to produce a plausible wrong
answer. **The `F^em` / `F^hd` split, not the total, is where a force error lives** — the body-force
consistency terms cancel in the sum, so routes A and B agree perfectly on a split that can be wrong
by O(10 pN), and only route C detects it. And **a benchmark's far field can silently make it
measure nothing**: VER-19 needs the exact Stokes field on the outer boundary and VER-21 needs a
uniform one, for the same reason in opposite directions.

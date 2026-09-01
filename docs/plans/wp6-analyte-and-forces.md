# WP6 — Analyte body and force benchmarks

**Status: planned, not started.** Written 1 September 2026 after WP5 merged. Nothing below has been
run; every number in it is arithmetic or a quotation, and the **Outcome** annotations that
`wp5-continuation-qoi-envelope.md` carries are what this file gains as the work lands.

The implementation plan for work package 6 of `phase-0-spike.md`, the last package of Phase 0.
`SPECIFICATION.md` remains normative: where this file and the specification disagree, the
specification governs and this file is wrong. Requirement identifiers here are pointers into it, not
restatements of it.

## Context

WP1–WP5 built everything the pore needs and nothing the *analyte* needs. `src/nanopnp/geometry/` is
an empty package whose docstring reserves the slot ("… analyte bodies"); `src/nanopnp/post/` has no
`forces.py` though its docstring reserves that one too. Phase 0 exit criterion 1 is outstanding on
exactly four benchmarks — **VER-19 … VER-22** — and all four need an embedded body. Amendment A1
pulled part of FR-21 and FR-22 forward into the spike for that reason, "to the extent the benchmarks
exercise them"; the case-file surface for analytes stays v1.0 work.

The risk the package exists to retire is **RSK-04**. At the reference operating point (+50 mV,
`q_Hb` = −4 e, 300 mM NaCl) the PlyAB continuum reference has `|F^em| ≈ |F^hd| ≈ 10 pN` of *opposite
sign*, so the net force is a small difference of two large numbers and an error in either integral
flips the sign of the trapping landscape. NUM-29 sets the bar accordingly: each contribution resolved
well below 1 pN, the two routes agreeing to better than 0.1 pN, and a mesh convergence study of its
own. In the project's nondimensional scaling the force unit is `ε V_T² = 4.57 × 10⁻¹³ N`, so 0.1 pN
is **0.219** dimensionless — a tolerance the discretisation can meet, not a heroic one.

WP6 delivers `geometry/analyte.py` and `post/forces.py`, plus four small seams, discharging VER-19,
VER-20, VER-21, VER-22, implementing NUM-28 and NUM-29, and closing §8.2 criterion 1.

## Decisions taken before implementation

| Decision | Choice | Why |
|---|---|---|
| How the body enters the mesh | **A named domain `analyte`, glued, not a hole** | Poisson is solved over all of Ω with a piecewise permittivity, so a dielectric jump *is* a material entry: `solid_permittivities={"analyte": eps_p}`. The fluid regex `ELECTROLYTE_DOMAINS` matches in full and already excludes it, so `n·J_i = 0` and the jump are natural (PHY-09) and only no-slip is essential — `CoupledBoundaries.velocity = "wall\|membrane\|analyte"`, no code change. Author ruling 4; §5.2.3 rejects level-set and immersed-boundary outright |
| `w`, the smooth extension of `e_z` | **`smoothstep` of the analyte distance field, on the fluid alone** | `post/indicator.py`'s ψ is the same object one rank up. Reuse `smoothstep` and `mesh.distance.wall_distance(mesh, "analyte")`; build by interpolation, never by writing dofs (the hierarchical-basis trap, 8.3 % and mesh-independent); restrict with `definedon` to the fluid, which was worth a factor of 170 to ψ and is load-bearing here for the same reason — `w` must be *exactly* `e_z` on the body and *exactly* zero elsewhere |
| Force scale | **`Scales.force_N = permittivity * potential_V**2`** = `ε V_T²` ≈ 0.4568 pN | `pressure_Pa · length_m²` with the `a²` cancelling: the force scale is independent of the reference length. The `2π` is restored **once**, as `post/qoi.py` does it — `TWO_PI * scales.force_N * ∫(…) r dr dz` — and never twice (NUM-27 NOTE) |
| The two components' split | **Each carries its own body-force consistency term** | See below. `−∫T_M:∇w` and `−∫T_H:∇w` taken alone are *w-dependent* and therefore not quantities; only their sum is nearly w-independent. Since RSK-04 is about the split, getting the split wrong is the whole failure mode |
| Route C, the oracle | **The variational reaction force**, `post/reaction_flux` generalised to a vector test function | The analyte surface is a Dirichlet boundary for `u`, so pairing the assembled residual with a function equal to `e_z` there gives `F^hd` *discretely exactly* and, because the residual vanishes on every free dof, **exactly independently of `w`**. It is the NUM-25 analogue for forces and the sign oracle for routes A and B |
| VER-19/20/21 configuration | **Classical** (`classical=True`), constant `η`, `ε`, `D` | `6πηaU`, the dielectric-sphere stress and the Hückel/Smoluchowski limits all assume constant coefficients and the Einstein relation. With corrections active `η` is position-dependent (the integrand inherits the wall correction) and none of the three closed forms is the right target. Same reasoning as VER-17's "why this runs classical and uncharged" |
| VER-19's far field | **The exact Stokes solution imposed on the outer boundary** | A bounded domain with `u = U` on the outer boundary adds a Faxén wall correction of order `a/R`, so the benchmark would measure the truncation. Imposing the closed-form Stokes field instead makes the FE solution exact on the annulus, the residual error purely discretisation, and `R = 10a` sufficient. This is the MMS idiom the repo already uses |
| Analyte as a wall-distance source | **No, by default; behind a flag** | `d` is the distance to the nearest *pore* boundary (PHY-02) and the reference model has no analyte at all. Driving `f^w_D`, `f^w_μ`, `f^w_η` from proximity to the body is a model change; it goes behind `include_analyte`, default off, and is recorded in the FR-25 manifest as a switch away from the validated default |
| Analyte charge | **Volumetric by default, surface available, both off unless a benchmark asks** | `fixed_charge=mesh.MaterialCF({"analyte": rho}, default=0)` needs no new code; σ_s rides the existing `surface_charge_boundary`. §10.3 of `.knowledge/05` settles the reference in favour of `ρ_part = q/V`; an analyte σ_s has no textual support anywhere, so it is off by default |
| VER-22's configuration | **Cheap gate, slow record** | Tier 2 gates on a sphere in a box — seconds, both routes, both components. The PlyAB-shaped pore-with-analyte case at 300 mM, +50 mV, `q` = −4 e runs `slow` and is the actual RSK-04 evidence, reporting `F^em` and `F^hd` separately. Same code path, two budgets; the Tier-2 suite already carries VER-11 and VER-17 on every push across seven CI configurations |

## Design

### The identity behind NUM-28, and the term it hides

This is the load-bearing piece of the package and it is not in the phase plan. With `w` equal to `e_z`
on the body, zero on every other boundary, and `T = T_M + T_H`, the divergence theorem gives

```
F_z = ∮_∂B (T·n_B)·e_z dS = −∫_Ω T:∇w dV − ∫_Ω (∇·T)·w dV
```

NUM-28 prints only the first term, which is exact **iff `∇·T = 0` in the fluid**. In this model it is
not. The momentum equation carries the body force `f = ρ_ion E` (PHY-08) and the inertia term, so
`∇·T_H = −f + Re ϱ(u·∇)u`; and `∇·T_M = ρ_ion E − ½|E|²∇ε`. Three consequences, in increasing order
of importance:

1. **Per component the consistency term is large, and the split is meaningless without it.**
   `F^em = −∫T_M:∇w − ∫(ρ_ion E − ½|E|²∇ε)·w` and `F^hd = −∫T_H:∇w + ∫(ρ_ion E + …)·w`. The
   `∫ρ_ion E·w` piece is the electrical body force on the fluid inside the shell where `w` varies —
   an O(10 pN) number that depends entirely on where that shell is. Omit it and each component is a
   function of the band you chose; report the pair and you have reported the band. This is exactly the
   plausible wrong answer RSK-04 describes.
2. **The two body-force terms cancel in the sum**, leaving `F_tot = −∫T:∇w + ∫½|E|²∇ε·w − Re(…)`. So
   the printed NUM-28 form is right for the *total* up to the dielectric-gradient residual.
3. **That residual is the Korteweg–Helmholtz force the validated model deliberately omits** (PHY-23).
   With the `ε_r` correction active `∇ε ≠ 0` and the domain and surface routes differ by exactly the
   omitted term; with `dielectric_gradient_forces=True` they agree identically. Implemented as a named,
   reported term, this becomes a measurement of the omission rather than a mystery. VER-22 gates
   classically, where it is identically zero.

`SPECIFICATION.md` gains a NOTE under NUM-28 recording the identity and the consistency term — the same
treatment WP5 gave NUM-24's sign and NUM-26's precondition.

One correction to the phase plan while we are here: **the domain form carries no `1/r` factor.** For an
axial `w`, `(∇w)_φφ = w_r/r = 0`, so the hoop components of `T_M` and `T_H` are contracted against zero
and `T:∇w = T_rz ∂_r w_z + T_zz ∂_z w_z`. The `phase-0-spike.md` bullet claiming a hoop component in
`1/r` is wrong. The integrals still go through `Measures` — for the `r` weight, the order floor and the
non-finite abort — but `singular=True` is not required and claiming it would be cargo cult. The
consistency term is likewise regular. `physics/flow.strain_rate` is reused with its documented caveat:
its 2×2 tensor omits `ε_θθ = u_r/r`, which is correct here precisely because nothing contracts it.

### `geometry/analyte.py` — FR-21, CON-02

- `AnalyteBody` protocol: `face()` returning a `netgen.occ` Face named `analyte` with its edges named
  `analyte`, plus `volume_nm3` (for `ρ_part = q/V`) and `z_nm`.
- `SphereBody(radius_nm, z_nm=0.0)` and `SpheroidBody(semi_radial_nm, semi_axial_nm, z_nm=0.0)` — the
  half-profile revolved, i.e. a half-disc / half-ellipse in the `(r, z)` half-plane on the axis.
  CON-02 restricts v1 to bodies of revolution on the axis; the profile hook that a revolved polyline
  would need is deferred, not designed around.
- `AnalyteInBoxGeometry(body, outer_radius_nm, *, analyte_h_nm)` — the benchmark domain for
  VER-19/20/21 and the cheap VER-22: a half-disc of fluid named `electrolyte`, the body cut out and
  glued back as `analyte`, boundaries `axis`, `analyte`, `outer`. `generate(maxh_nm=…, wall_h_nm=…)`
  matching the duck-typed signature the three existing primitives share.
- `PoreWithAnalyte(pore: CylindricalPoreGeometry, body, *, analyte_h_nm)` — the reference-shaped case.
  Cuts the body from the lumen and re-glues, keeping the whole `axis` / `wall` / `membrane` /
  `membrane_outer` / `cis` / `trans` vocabulary intact so `lumen_band`, `axial_indicator` and the
  default `CoupledBoundaries` keep working unchanged.

Two mechanics worth naming. The body's edges are named **before** the boolean, because
`CylindricalPoreGeometry.generate`'s classification is an unconditional `if/elif` chain on edge
centroids and a body edge would fall through it to `default`; `mesh/primitives.py` gains a guard so
already-named edges survive, and a centroid-against-profile fallback if OCC turns out not to propagate
names through the cut. And the body is meshed with `edge.maxh = analyte_h_nm` exactly as the pore wall
is — WP5's finding that the NUM-30 wall grading decides *whether the ladder converges*, not only how
accurate it is, applies with equal force to a charged body in a double layer.

`mesh/primitives.py` is refactored so the pore's OCC shape is available before meshing, so the
analyte variant composes rather than copies the geometry.

### `post/forces.py` — NUM-28, NUM-29, FR-22 (partial)

- `axial_extension(mesh, *, inner_nm, outer_nm, order=2, fluid=ELECTROLYTE_DOMAINS, body="analyte",
  check=True) -> GridFunction` — the vector `w`. Built as `(1 − S(d))·e_z` from the `analyte` distance
  field through the existing `smoothstep`, interpolated on a `VectorH1` restricted to the fluid,
  with a `check_extension` asserting `w = e_z` on the body and `w = 0` on every outer boundary — the
  direct analogue of `check_indicator`, and the thing that turns an inverted or leaking band into a
  loud failure rather than a wrong force.
- `maxwell_stress(potential, permittivity)` and `hydrodynamic_stress(velocity, pressure, viscosity)`
  returning the in-plane 2×2 tensors of NUM-28, with the sign convention pinned in the docstring
  against `.knowledge/05` §4, which writes `T_H` with the opposite overall sign.
- `domain_force(solution, measures, extension, *, wall_distance_nm=None) -> ForceComponents`
  — **route A**, NUM-28 plus the consistency terms of each component. Coefficients come from the
  model's own public seams (`concentration_variables`, `coefficients`) against
  `solution.wall_distance_nm`, exactly as `qoi.indicator_currents` does, so the `η` and `ε` in the
  integrand are the ones the residual was assembled from.
- `surface_force(solution, measures, *, boundary="analyte") -> ForceComponents` — **route B**, the
  cross-check `∮ (T·n)·e_z r ds`.
- `reaction_force(solution) -> float` — **route C**, `F^hd` from the assembled residual paired with a
  velocity-block test function equal to `e_z` on the analyte boundary. Requires one small extension to
  `reaction_flux.boundary_indicator`: accept a vector value, since `Set(CF(1.0))` cannot fill a
  `VectorH1` block. Reuses the existing "no free dofs on this boundary" guard, which is what makes the
  result a boundary flux rather than a plausible wrong number.
- `ForceComponents(em_N, hd_N)` with `total_N`; `ForceAgreement(domain, surface, reaction)` whose
  `check(tolerance_N=1e-13)` raises `ForceDisagreementError` naming all three values and the absolute
  differences. **Absolute, not relative** — `RouteAgreement`'s relative test is meaningless on a sum
  that is nearly zero by construction, which is the whole of RSK-04.
- `extract(solution, measures, extension, …) -> AnalyteForces` with a `summary()` emitting
  `two_pi_included: True` and the stabilisation/switch record, matching `QuantitiesOfInterest`.

FR-22's `ΔU(z) = −∫F dz` over a z-sweep stays out: A1 limits WP6 to what the benchmarks exercise, and
`continuation.transfer` refuses to cross meshes by design, so a scan is N independent climbs — Phase 1
work, not a signature change.

### Seams added to existing modules

Additive; none changes existing behaviour.

- `core/scaling.py` — `force_N` property, its entry in the `_scale` dict, and its line in `summary()`,
  which feeds the FR-25 manifest.
- `post/reaction_flux.py` — `boundary_indicator` gains a vector `value`.
- `mesh/primitives.py` — the shape/mesh split, and the "don't overwrite an already-named edge" guard.
- `mesh/distance.py` — docstring amendment: the source set is the pore wall *by default*, and what
  passing the analyte too would mean.

## Tests

Placement decides the tier. Tier 2 runs on every push on seven CI configurations, so per-test wall time
is a design constraint; `slow` never runs in CI.

| File | Tier | Discharges | Content |
|---|---|---|---|
| `tests/tier1/test_analyte.py` | 1 | FR-21, CON-02 | `SphereBody`/`SpheroidBody` volumes and profiles; the meshed box carries an `analyte` domain and an `analyte` boundary; the fluid regex still selects the fluid and *not* the body; the pore-with-analyte geometry keeps every existing boundary name; a body larger than the lumen raises rather than producing a degenerate mesh |
| `tests/tier1/test_forces.py` | 1 | NUM-28, NUM-27 | `axial_extension` is `e_z` on the body and 0 on `outer`, and `check_extension` catches an inverted band; the `force_N` scale arithmetic and the single `2π`; **the domain form is invariant to the pressure datum**, because `∫_Ω div w = ∮_∂B n_z = 0` for a closed body of revolution; `ForceAgreement.check` is absolute and names all three routes |
| `tests/tier2/test_stokes_drag.py` | 2 | **VER-19** | Uncharged sphere, `classical`, flow only, exact Stokes field on `outer` at `R = 10a`. `F_z` against `−6πηaU` over three refinements: floor error and observed rate both asserted, tolerance **stated at 1 %** on the finest mesh. Sanity anchor from `.knowledge/05` §7: a 5 nm sphere at 0.1 m/s is ≈ 4 pN. Negative control: the surface route on the same solution agrees, and the drag is *not* the wall-corrected value a `u = U` outer boundary would give |
| `tests/tier2/test_maxwell_sphere.py` | 2 | **VER-20**, FR-21 | Dielectric sphere, `ε_p` in `ε_m`, uniform field via `φ = −E₀ z` on `outer`, no flow. Net `F_z` ≈ 0 to well below 0.1 pN by both routes, and the traction distribution against the analytic surface stress. **Plus the magnitude anchor**: give the body `ρ_part = q/V` at `ε_p = ε_m` and assert `F_z = q E₀` in closed form — a zero test cannot catch a scale error in the Maxwell route, and this is the only Tier-2 test that pins it (`.knowledge/05` §9.1) |
| `tests/tier2/test_electrophoretic_mobility.py` | 2 | **VER-21**, FR-22 | Two solves per limit: the body held fixed under an applied field, and the body translating with no field (which *is* VER-19's operator). `μ_e = −F_field · U₀ / F_drag / E₀`. Hückel at `κa ≈ 0.1` against `2εζ/3η`, Smoluchowski at `κa ≈ 20` against `εζ/η`, both at `ζ ≲ V_T` so the linear closed forms apply. Tolerance **stated at 5 %**, with Henry's `f(κa)` logged as the reference — at `κa = 20` Smoluchowski is itself 3 % above Henry, and asserting 1 % there would be asserting something untrue |
| `tests/tier2/test_force_routes.py` | 2 | **VER-22**, NUM-29, RSK-04 | Sphere in a box, `pnp-ns` classical, charged body under a bias — a solution with both components genuinely non-zero. Domain (A) against surface (B) to better than **0.1 pN absolute**, and route C against A's `F^hd` as the independent oracle on the split. Classical, so the `∇ε` consistency term is identically zero and the identity is exact |
| `tests/tier2/test_force_convergence.py` | 2, `slow` | **NUM-29**, RSK-04 | The mesh convergence study NUM-29 mandates: three refinements, `F^em`, `F^hd`, `F^tot` and the A/B disagreement against dof, logged as a table. **Plus the PlyAB-shaped record**: `PoreWithAnalyte` at 300 mM, +50 mV, `q` = −4 e, `ε_p = 20`, reached through the ladder — reporting `F^em` and `F^hd` separately, their sum, and the `∇ε` consistency term with the corrections active. A measurement, not a gate; VAL-11 is Tier 4 |

The idiom is WP2–WP5's: expensive work in one module-scoped fixture with thin assertion tests over the
shared result, measurements through a module logger with lazy `%` args, any shared helper in
`src/nanopnp/validation/` rather than in `tests/`. Every non-obvious assert carries an f-string naming
the measured value, the reference and the tolerance in pN, and says what a failure would mean.

## Documentation to change in the same commits

- **`SPECIFICATION.md`** — a NOTE under NUM-28 giving the divergence identity, the per-component
  consistency term, and the statement that the printed form is exact only where `∇·(T_M + T_H) = 0`,
  which the validated model's omission of the Korteweg–Helmholtz force (PHY-23) breaks whenever the
  `ε_r` correction is active. NUM-29's stale "(RSK-17)" cross-reference is corrected to RSK-04.
  §4.1.1's domain list and PHY-20's permittivity table gain the analyte domain, pointing at author
  ruling 5 for `ε_p` as a calibration parameter rather than a constant. VER-19's and VER-21's
  tolerances, which the specification deliberately leaves open, are stated.
- **`phase-0-spike.md`** — WP6 merged, criterion 1 met, Phase 0 complete on criteria 1–3 with 4
  outstanding by A2; the end-of-phase report the plan asks for; and the correction to the WP6 bullet's
  claim that the `∇w` contraction carries a `1/r` hoop component.
- **`.knowledge/05-analyte-and-forces.md`** — §9.1's "analytic tests remain the right first check"
  becomes **[tested]** with the measured numbers; the `T_H` sign discrepancy between §4 and NUM-28 is
  resolved in place.
- **`.knowledge/06-numerics-fem.md`** — the domain/surface/reaction force identity, the consistency
  term, and any new silent NGSolve trap found on the way.

## Risks

**The `F^em` / `F^hd` split is where a silent error lives, not the total.** Both components carry a
large body-force term whose omission is invisible in the sum and fatal to the split. The mitigation is
route C: it computes `F^hd` from the assembled residual, is exactly `w`-independent because the residual
vanishes on every free dof, and therefore disagrees with route A precisely when the consistency term is
wrong or mis-signed. It is the reason route C is in the package at all.

**`F^em` has no reaction-route oracle.** `φ` is not constrained on the analyte surface, so the Maxwell
half rests on quadrature alone. VER-20's zero test cannot catch a scale error, which is why the
`F = q E₀` anchor is not optional.

**VER-21 is the budget risk.** Smoluchowski wants `κa ≫ 1` with `λ_D/5` resolution on the body, and
Hückel wants a domain many Debye lengths across. Sizing starts at `a = 20 nm` in 300 mM (`κa ≈ 36`,
`λ_D = 0.56 nm`) and `a = 1 nm` in 1 mM (`κa ≈ 0.10`, `λ_D = 9.6 nm`), with the outer boundary at
≥ 20 `λ_D`. If either lands above about a minute it moves to `slow` and a coarser variant holds the
Tier-2 gate — the closed forms are limits, so a looser tolerance on a cheaper mesh still discharges
VER-21 honestly. That trade is stated in the test docstring rather than hidden in a mesh size.

**A Dirichlet velocity on every boundary leaves the pressure undetermined.** VER-19 and VER-21 impose
`u` on both the body and `outer`, so `pressure_constraint=True` is required; the existing
`PRESSURE_MEAN` field handles it. The force is invariant to the datum, and the Tier-1 test asserts
that rather than assuming it.

**The gap between body and pore wall.** In the PlyAB-shaped case the body (5.8 nm wide) nearly fills
the lumen, and two `λ_D/5`-graded surfaces a fraction of a nanometre apart is where the mesher will
produce slivers. The QR-12 quality gates (min SICN/gamma > 0.3) are the diagnostic; if they fire, the
`slow` case widens the lumen rather than loosening the gate.

## Verification

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src/ && uv run pytest
uv run pytest -m tier2 -v                                       # VER-19 … VER-22
uv run pytest tests/tier2/test_force_routes.py -v               # VER-22 alone
uv run pytest -m slow --log-cli-level=INFO -v                   # NUM-29 convergence + the PlyAB record
```

WP6 is done when `uv run pytest` is green with VER-19 … VER-22 passing; the two force routes agree to
better than 0.1 pN with route C confirming the split; the `slow` convergence study completes and its log
carries `F^em`, `F^hd`, `F^tot` and the route disagreement against dof; and `phase-0-spike.md` records
criterion 1 as met, with Phase 0 complete on criteria 1–3.

## Delivery

One pull request on `claude/wp6-implementation-plan-11c767`, sequenced so each commit is green on
tiers 1 and 2.

1. `feat:` the `force_N` scale, the vector `boundary_indicator`, and the `mesh/primitives` shape split
   and edge-name guard, with their Tier-1 tests
2. `feat:` `geometry/analyte.py` — the bodies, the box geometry and the pore-with-analyte geometry
   (FR-21, CON-02), with `tests/tier1/test_analyte.py`
3. `feat:` `post/forces.py` — `w`, the three routes and `ForceAgreement` (NUM-28), with
   `tests/tier1/test_forces.py`, and the NUM-28 NOTE written into the specification in the same commit
4. `test:` VER-19 and VER-20 with the `q E₀` anchor, and their stated tolerances into the specification
5. `test:` VER-21, and VER-22 with route C as the oracle
6. `test:` the NUM-29 convergence study and the PlyAB-shaped `slow` record
7. `docs:` the phase plan, the knowledge base, and the measured numbers

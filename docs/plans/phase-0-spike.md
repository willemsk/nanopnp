# Phase 0 (Spike): coupled ePNP-NS on an analytic cylindrical pore

**Status: WP1–WP3 merged, WP4–WP6 outstanding.** Last revised 30 August 2026, after the WP3 review.

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
  dependencies rather than the dev group. Still to be added, in WP4.

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

### WP4 — Nernst–Planck, flow, the coupled model, MMS — *next*

`physics/nernst_planck.py`, `physics/flow.py`, `physics/models.py`, `validation/mms.py`; adds
`sympy` to the base dependencies.

- Nernst–Planck in primitive `c_i` (NUM-02), log-variable branch behind a flag, Slotboom rejected.
  The steric flux `β_i` gets the sign discipline of PHY-05 with the warning comment the knowledge
  base asks for: `+` inside the bracket, bracket negated, sum retained over all species, the
  `a_i³/a_0³` prefactor kept — it is 4.16 for NaCl, not a droppable normalisation.
- Flow: constant-density Stokes first (Taylor–Hood P2/P1, **with the hoop-strain term
  `2η u_r v_r / r²`** — omitting it is a silent correctness bug), then the variable-density Axelsson
  three-equation system as the default (PHY-07). Body force is `ρ_ion E` only;
  `dielectric_gradient_forces` enables both the momentum and the Nernst–Planck term together,
  default off (PHY-08, PHY-23).
- `PhysicsModel` registry: `epnp-ns`, `pnp-ns`, `pnp`, `pb`, `pb-linear`, `poisson` (PHY-21, FR-20),
  with `pnp-ns` a configuration of `epnp-ns`, not a second code path. Follows the
  `materials/models.py` registry pattern.
- Forms are written in the nondimensional variables of `core/scaling.Scales`, and take their
  measures from `Measures` — `singular=True` wherever `1/r` appears, which includes the hoop-strain
  term.
- **Wire the WP3 state gates into the coupled solve.** `PositivityGate` and `PackingFractionGate`
  exist but are exercised only on constructed states: `pb` carries no independent concentration
  field, so WP4 is their first real use. A test SHALL drive a coupled solve into a violation and
  assert the abort, not merely assert the gate in isolation.
- MMS machinery: sympy-manufactured `φ, c_i, u, p` with consistent source terms on the full coupled
  axisymmetric system, and a convergence-rate utility.
- Tests: VER-14 Rice & Whitehead (thick and thin EDL), VER-15 Helmholtz–Smoluchowski limit, VER-16
  1D PNP with the limiting-current plateau, VER-18 MMS at O(h³) in L² for P2 — the only route that
  verifies the `u_r/r²` term and the axis treatment.
- **Budget note, from the WP3 measurement.** A factorisation at 1.04 × 10⁶ DOF costs 41 s and 6.2 GB
  on the development laptop, and memory is near-linear in DOF. An MMS refinement sequence SHALL
  therefore state its finest level and stay inside that budget; three levels that fit are worth more
  than five that swap. The observed rate, not the number of levels, is the deliverable.

### WP5 — Continuation ladder, QoI extraction, the envelope

`solve/continuation.py`, `post/qoi.py`, `post/indicator.py`.

- The nine-rung ladder of NUM-18 with warm start between rungs, corrections enabled last (rungs 7–8)
  so that a convergence failure attributes to one term; mesh adaptation between rungs only (NUM-19).
  The warm start is safe to rely on: WP3's update-based convergence test is what makes re-solving a
  converged state terminate.
- The ψ-domain-indicator current (NUM-24) and the derived QoIs `t₊`, `RR`, `G`, `Q_EOF` from the
  same ψ integrals (NUM-27). The variational reaction flux (NUM-25) already exists from WP2; this
  package supplies the second route and the comparison. **Never a cross-section integral of the CG
  flux** (NUM-23).
- Tests: VER-11 (the two routes agree to better than the rectification signal at the lowest bias);
  VER-17 Maxwell–Hall access conductance to better than 2 %, using the *diameter* form
  `G = σ[4L/(πd²) + 1/d]⁻¹` — the widely-copied `1/a` variant is wrong by a factor of two in the
  access term and would fail a correct solver.
- Plus the §8.2 criterion 2 run as a slow, non-gating test: converged solutions across
  0.05–3 M × ±200 mV with every correction active, no negative concentration at any Newton step.
  **The envelope run SHALL record the mesh it ran on.** Nine rungs × the bias and concentration grid
  × several Newton steps each, at 41 s per factorisation at reference size, is hours; running it at
  a reduced mesh is legitimate and running it without saying which mesh is not.

### WP6 — Analyte body and force benchmarks

`geometry/analyte.py`, `post/forces.py`.

- Rigid body of revolution on the axis, subtracted from the fluid domain, treated as a hard
  dielectric: no ion flux, no-slip, dielectric jump (FR-21, author ruling 4).
- Force in **domain form**, `F_z = −∫_Ω (T_M + T_H) : ∇w dV` with `w` a smooth extension of `e_z`
  (NUM-28), and the surface form `∮_S (T_M + T_H)·n dS` implemented alongside purely as the
  cross-check. In axisymmetry the `∇w` contraction carries a hoop component in `1/r`, so the domain
  form goes through `Measures.volume(singular=True)` like every other such term.
- Tests: VER-19 Stokes drag `6πηaU`, VER-20 Maxwell stress on a dielectric sphere in a uniform field
  (net force zero, stress distribution matched), VER-21 Hückel and Smoluchowski mobility limits,
  VER-22 the two force routes agreeing to better than 0.1 pN on the same solution (NUM-29). This is
  RSK-04, a near-cancellation of two approximately 10 pN terms, and it is the reason A1 pulled the
  analyte body forward into the spike.

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
   axisymmetric system, and the two force routes agreeing to better than 0.1 pN.
   *Outstanding: VER-14 … VER-22. Discharged: VER-12, VER-13.*
2. **The envelope converges**: 0.05–3 M × ±200 mV with all corrections active, reached through the
   continuation ladder, with no negative concentration at any Newton iterate. *Outstanding, WP5.*
3. **The factorisation benchmark reports** time and peak memory for a production-sized problem on
   this laptop, with a verdict on whether UMFPACK or SuperLU is viable (RSK-10). **Met in WP3**:
   UMFPACK, 41 s and 6.2 GB at 1.04 × 10⁶ DOF; SuperLU not viable at that size.
4. Criterion 4 (Windows GUI bundle) is **explicitly not met**, by amendment A2; the specification
   says so and RSK-13 stays open.

Report at the end of the phase: the observed MMS convergence rates, the factorisation timing, which
ladder rungs needed damping below 0.1, and any benchmark whose tolerance had to be argued rather
than met — the last being the one that matters most for Phase 1's COMSOL comparison.

# WP5 — Continuation ladder, QoI extraction, the envelope

**Status: planned, not started.** Written 31 August 2026, after WP4 merged.

The implementation plan for work package 5 of `phase-0-spike.md`. `SPECIFICATION.md` remains
normative: where this file and the specification disagree, the specification governs and this file
is wrong. Requirement identifiers here are pointers into it, not restatements of it.

## Context

WP1–WP4 built everything a *single* solve needs — the correction registry, the axisymmetric weak
forms, damped Newton with the NUM-17 gates, the coupled `epnp-ns` model and the manufactured
solutions. What they did not build is anything that *drives* a solve to a hard operating point, or
anything that turns a converged field set into a number worth publishing. Two Phase 0 exit criteria
stand open because of it:

- **Criterion 1** is short of VER-11 (the two current-extraction routes agree) and VER-17
  (Maxwell–Hall access conductance). VER-19 … VER-22 belong to WP6.
- **Criterion 2** — converged solutions across 0.05–3 M × ±200 mV with every correction active,
  reached through the continuation ladder, with no negative concentration at any Newton iterate — is
  outstanding in full. WP4 established that it *needs* the ladder: a cold `epnp-ns` solve at high
  salt against a strongly charged wall aborts on the co-ion positivity gate, and the classical
  configuration aborts on packing. Both aborts are correct, and both are exactly what NUM-18's warm
  start exists to avoid.

WP5 delivers `solve/continuation.py`, `post/indicator.py` and `post/qoi.py`, discharging FR-17,
FR-23, QR-04, VER-11, VER-17 and §8.2 criterion 2.

The risk the package exists to retire is **RSK-03**. A current obtained by integrating the
continuous-Galerkin flux over an interior cross-section is wrong by per-cent amounts that *exceed
the rectification signal at low bias* — a stable, plausible, publishable wrong number with no solver
diagnostic. NUM-23 bans that route; NUM-24 and NUM-25 mandate two independent ones; VER-11 checks
them against each other in continuous integration. That check is the deliverable, not a nicety.

## Decisions taken before implementation

| Decision | Choice | Why |
|---|---|---|
| Mesh across the ladder | **One fixed mesh**, graded to `λ_D(3 M)/5 ≈ 0.035 nm` at the wall, held for every rung | Satisfies NUM-19 trivially: there is no adaptation to confine to rung boundaries. It also keeps the warm start on rungs 6–9 a same-space vector copy. The ladder API still takes a per-rung mesh, so adaptation drops in later without a signature change |
| Envelope grid | **5 concentrations × 6 biases on a reduced mesh** — 0.05, 0.15, 0.5, 1.0, 3.0 M × ±50, ±100, ±200 mV | Demonstrates the envelope in about an hour. It is a measurement, not a gate, and the mesh it ran on is recorded |
| `ψ` construction | **C¹ smoothstep in `z`**, transition band configurable, defaulting to the lumen | `∇ψ` is then supported in the band alone, so the integral is a smeared cross-section. Cross-section independence becomes directly testable by moving and widening the band — the demonstration of *why* NUM-23 is banned |
| The `2π` | Applied **once, in `post/`** | `Measures` cancels `2π` from both sides of the weak form, so `Measures.integrate` returns `∫ f r dr dz`. Both QoI routes inherit that, so their *agreement* is independent of the convention — but neither is an ampere until `post/` restores the factor. NUM-27's NOTE requires the convention be stated; it is stated in the module docstring and in the specification |
| VER-17 configuration | `pnp` with `classical=True`, uncharged wall | With the corrections active `μ_i` varies with `⟨c⟩` and `d`, and there is then no single bulk `σ` for the closed form to be compared against. The benchmark tests the axisymmetric discretisation and the access geometry, not the corrections |

## Design

### Seams added to existing modules

Additive; none changes existing behaviour.

`physics/models.py`

- `ModelSolution` gains `residual: AssembledForm | None` and `wall_distance_nm: Expression`, both
  populated by `solve`. Today `solve` builds the `BilinearForm` and discards it, so a caller wanting
  the NUM-25 reaction flux rebuilds it, as `tests/tier2/test_pnp_benchmarks.py` does. That is safe
  for a classical model and a **silent trap** for `epnp-ns`: rebuilding without the same
  `wall_distance_nm` gives a different operator, and the reaction flux is then wrong with no
  diagnostic. Carrying both on the solution removes the trap and halves the assembly.
- Both models gain a public `cold_state(mesh, boundaries, *, initial_concentrations=None)`, replacing
  the private `_initialise`. `solve` uses it; `continuation.transfer` needs it and must not reach
  into a private.
- `CoupledModel.solve` gains `callback`, passed straight through to `damped_newton`, which already
  documents it as "for continuation logging". `_reject_unknown` means it has to be declared, not
  smuggled through `**kwargs`.

`core/scaling.py`

- `Scales.volumetric_flow_m3_s = velocity_m_s * length_m**2`, registered as `volumetric_flow` in
  `_scale`. `Q_EOF` has no scale today; `current_A = F D₀ c₀ a` already exists and is exactly right
  for the `ψ` current.

`physics/poisson.py` already provides `surface_charge_source`, unused by `CoupledModel`. WP5 wires
it in as `surface_charge: Expression | None` on `residual_form` and `solve`, applied on the pore
wall, so that NUM-18 rung 4 can ramp `σ_s` as well as `ρ_pore`, as the specification writes it.
This is the only genuinely new physics term in the package.

### `solve/continuation.py` — NUM-18, NUM-19

Model-agnostic, driven by the `PhysicsModel` protocol: §5.5 promises a new physics model gets
continuation for free.

- `Rung` — name, model, mesh, boundaries and the per-rung solve keywords.
- `RungResult` / `LadderResult` — the rung name, the model, `NewtonResult.summary()`, wall time and
  the fields transferred, plus a `summary()` for the FR-25 manifest and a `minimum_damping_used`,
  which is the diagnostic the end-of-phase report asks for.
- `run_ladder(rungs)` — solve each rung warm-started from the last. A `GateViolationError` propagates
  with the rung name prepended (QR-12); the ladder never swallows a gate.
- `transfer(previous, model, mesh, boundaries)` — the piece that does not exist today.
  `CoupledModel.solve` accepts `initial: ModelSolution` but **reuses `initial.space`**, so it only
  warm-starts a rung whose field set is unchanged. Rungs 2→3 (add `c_i`) and 5→6 (add `u`, `p`) each
  change the space. `transfer` builds the target space, cold-starts it, and interpolates every field
  present in both models by name, taking concentrations through `ModelSolution.concentration` so the
  NUM-02 log branch is unwrapped on the way out and reapplied on the way in. The result is a
  `ModelSolution` on the target space, so `model.solve(initial=transferred)` needs no change to
  `models.py`. A mesh mismatch raises, naming the deferred cross-mesh path rather than silently
  point-evaluating outside the source domain.
- `default_ladder(...)` builds the nine rungs of NUM-18:

  | # | NUM-18 | Model | Space change |
  |---|---|---|---|
  | 1 | Linear Poisson–Boltzmann | `pb-linear` | — |
  | 2 | Nonlinear Poisson–Boltzmann | `pb` | none |
  | 3 | Equilibrium PNP, `V = 0`, `u = 0` | `pnp`, classical | φ → φ, `c_i` |
  | 4 | Ramp `σ_s` and `ρ_pore` 0 → target | `pnp`, classical | none |
  | 5 | Ramp `V_bias` 0 → ±200 mV | `pnp`, classical | none |
  | 6 | Enable the flow coupling | `pnp-ns`, classical | add `u`, `p` |
  | 7 | Enable the `D`, `μ`, `ε`, `ϱ` corrections | `CorrectionSwitches.for_model(...).without("steric")` | none |
  | 8 | Enable the steric flux `β_i` | `epnp-ns` | none |
  | 9 | Sweep salt 0.05 → 3 M | `replace(model, concentration_M=...)` | none |

  Rungs 4, 5 and 9 sub-step on a scalar. `bias_schedule` gives ≈10 mV steps to 50 mV and 25 mV
  beyond, which is NUM-18's "≈ 10 mV near onset".

  **Why rung 9 warm-starts across a changed `concentration_M`.** It changes `Scales`, hence `S`, `Pe`
  and every nondimensional coefficient — but not the field set, so the space is identical and the
  transfer is a vector copy. The previous solution remains a good guess because NUM-09 leaves every
  field O(1) in the *new* scaling too: `c̃_i = 1` is bulk by the definition of `c₀`, and `φ̃` is in
  `V_T`, which does not move. That is the payoff of solving nondimensionally.

### `post/indicator.py` — `ψ` for NUM-24

`ψ(z) = S((z − lower)/(upper − lower))` with `S(t) = t²(3 − 2t)` clamped to [0, 1]: C¹, 0 on the
trans side, 1 on the cis side. `cis` is at `+z` in `CylindricalPoreGeometry`, so `ψ` increases with
`z`. Built by **interpolation**, never by writing degrees of freedom: NGSolve's P2 basis is
hierarchical, and a degree-of-freedom-set indicator carries a clean, mesh-independent 8.33 % error
that reads as a modelling difference rather than a bug (`.knowledge/06-numerics-fem.md` §8.1, and
the same reasoning already written into `post/reaction_flux.py`).

`check_indicator` asserts `ψ ≈ 1` on the cis boundary and `≈ 0` on trans, so an inverted band fails
loudly rather than returning a sign-flipped current.

### `post/qoi.py` — NUM-24, NUM-26, NUM-27, FR-23

- `indicator_currents` rebuilds `J̃_i` from the converged state through the public seams already on
  `CoupledModel` — `concentration_variables`, `coefficients` — and then
  `physics.nernst_planck.species_flux`. `wall_distance_nm` defaults to the one carried on the
  solution, which is the whole reason for adding it. Integration goes through `Measures.integrate`,
  which floors the order at 5 and aborts on a non-finite result.
- `I_i = −F z_i · 2π · scales.current_A · ∫ J̃_i·∇ψ r dr dz`;
  `Q_EOF = 2π · scales.volumetric_flow_m3_s · ∫ ũ·∇ψ r dr dz`.
- `reaction_flux_currents` wraps the existing `boundary_reaction_flux` component-wise, with each
  species' block index read off `model.fields`. Both routes carry the same `2π` and the same
  `current_A`, so their agreement is independent of the convention while their SI values are not.
- `transport_number`, `rectification_ratio` and `conductance` all derive from the same `ψ` integrals,
  as NUM-27's "from the same `ψ` integrals" clause requires — never from a second extraction.
- `RouteAgreement.check(tolerance)` raises `RouteDisagreementError` naming both values and the
  relative difference (QR-04, QR-12).

**Sign convention**, fixed once and pinned by a test: positive current flows trans → cis, in `+z`,
the direction in which `ψ` increases. VER-17 anchors it, an uncharged Ohmic pore having `G > 0`.

## Tests

Placement decides the tier. Anything unmarked in `tests/tier2/` runs on seven CI configurations on
every push, so per-test wall time is a design constraint; `slow` never runs in CI at all.

| File | Tier | Discharges | Content |
|---|---|---|---|
| `tests/tier1/test_indicator.py` | 1 | NUM-24 | Smoothstep endpoints and C¹ continuity; `ψ = 1` on `cis` and 0 on `trans`; an inverted band raises; the `volumetric_flow` scale |
| `tests/tier1/test_qoi.py` | 1 | NUM-27, QR-04 | `t₊`, `RR`, `G` arithmetic; the `2π` convention against an analytic flux whose `ψ` integral is known in closed form; `RouteDisagreementError` names both values |
| `tests/tier1/test_continuation.py` | 1 | NUM-18 | `bias_schedule` steps ≈10 mV to onset and hits the target exactly, both signs; `default_ladder` emits nine rungs in NUM-18's order with the corrections last; `transfer` raises on a mesh mismatch |
| `tests/tier2/test_current_routes.py` | 2 | **VER-11**, FR-23, QR-04 | Charged pore, `pnp`, coarse mesh, ±50 mV — the lowest envelope bias. Both routes, both signs; route disagreement below the declared tolerance, which is below \|RR − 1\| there. **Plus cross-section independence**: move and widen the `ψ` band and assert the current is unchanged, which is the direct evidence for NUM-24 |
| `tests/tier2/test_access_conductance.py` | 2 | **VER-17**, QR-01 | Uncharged pore at 1 M, `pnp` classical, small bias. `G = I/V_bias` against `σ[L/(πa²) + 1/(2a)]⁻¹` to better than 2 %, with `σ = F Σ z_i² μ_i⁰ c_i` derived in the docstring from the model's own mobilities |
| `tests/tier2/test_ladder.py` | 2 | NUM-18, NUM-19 | Nine rungs on a deliberately tiny mesh at mild conditions: every rung completes and carries a `NewtonResult`; the transfer preserves `φ` across a space change; and **re-solving a converged rung from its own output takes zero iterations** — the warm-start idempotence WP3's update-based criterion buys, and the property the whole ladder rests on |
| `tests/tier2/test_envelope.py` | 2, `slow` | **§8.2 criterion 2**, FR-17 | Five concentrations × six biases, every correction active, through the ladder. Asserts every point converged with no gate violation. Logs the mesh, the degrees of freedom, `maxh`, `wall_h`, and per-rung iterations and minimum damping |

The idiom to follow is the one WP2–WP4 established: expensive work in one module-scoped fixture with
thin assertion tests over the shared result, measurements logged through a module logger and asserted
loosely, and any shared helper in `src/nanopnp/validation/` rather than in `tests/`.

## Documentation to change in the same commits

- **`SPECIFICATION.md`.** QR-04 requires the route-agreement tolerance to be *stated*, and the
  specification gives it only relationally ("smaller than the rectification signal at the lowest
  bias"); the declared number and its derivation go in as a NOTE under NUM-26. NUM-27's NOTE requires
  the `2πr` convention to be stated; §6.7 records that `Measures` cancels `2π` and `post/` restores
  it, so every SI quantity of interest is a true three-dimensional one.
- **`phase-0-spike.md`.** WP5 merged, criterion 2 met, criterion 1 outstanding only on VER-19 … VER-22.
- **`.knowledge/06-numerics-fem.md`.** The measured route agreement, and the measured cross-section
  spread the `ψ` form removes — §7's flux trap is currently asserted from the literature and becomes
  **[tested]** — plus any new silent NGSolve trap found on the way.

## Risks

**VER-17's 2 % against a finite reservoir.** The Maxwell–Hall form assumes access to infinity. At
`a = 2 nm`, `L = 13 nm`, `R_pore = L/(πσa²) = 1.034/σ` and `2 R_access = 1/(2σa) = 0.25/σ`, so the
access term is about 19.5 % of the total. At the default 50 nm reservoir the truncation error on the
access term is of order `a/R`, a few per cent of that 19.5 %, so about 1 % on `G`: inside the
tolerance, but not comfortably. Run at a larger reservoir, 100–150 nm, and assert that `G` moves by
well under the tolerance between two radii, so the benchmark measures the discretisation rather than
the truncation. What makes that affordable is that VER-17's pore is **uncharged** — there is no
double layer, so no `λ_D/5` wall grading is needed; grade at the pore mouth, where the current
density is singular.

**The envelope may need a NUM-20 fallback.** If a rung stalls at 3 M with the corrections active,
NUM-20 gives the order: pseudo-transient continuation, then the hybrid segregated scheme, then the
Poisson–Boltzmann initial guess, then ℓ₂ backtracking. Rungs 1–2 already *are* that initial guess.
Finer sub-stepping inside rungs 4, 5 and 9 comes first and costs nothing — the schedules are
parameters, not code.

**Warm start across a changed space is the one novel mechanism here**, and it is where a silent error
would live: an interpolation landing the potential on the wrong component, or a log/primitive
mismatch on the concentrations, converges to something plausible and wrong. Hence the explicit
assertion that a converged rung re-solved from its own output takes zero iterations, which fails
immediately if the transfer scrambles anything.

## Verification

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src/ && uv run pytest
uv run pytest -m tier2 -v                                    # VER-11, VER-17 and the ladder
uv run pytest tests/tier2/test_current_routes.py -v          # VER-11 alone
uv run pytest tests/tier2/test_access_conductance.py -v      # VER-17 alone
uv run pytest -m slow --log-cli-level=INFO -v                # the envelope; its mesh goes to the log
```

WP5 is done when `uv run pytest` is green with VER-11 and VER-17 passing; the envelope run completes
every point with no gate violation and its log names the mesh it ran on; and `phase-0-spike.md`
records criterion 2 as met, with criterion 1 outstanding only on WP6's VER-19 … VER-22.

## Delivery

One pull request, sequenced so that each commit is green on tiers 1 and 2.

1. `feat:` the `ModelSolution`, `cold_state`, `callback` and `volumetric_flow` seams, and the
   surface-charge term on `CoupledModel` (FR-23, NUM-18)
2. `feat:` `post/indicator.py` and `post/qoi.py` with their Tier 1 tests (NUM-24, NUM-27)
3. `feat:` `solve/continuation.py` with its Tier 1 tests (NUM-18, NUM-19)
4. `test:` VER-11 and VER-17, with the declared tolerance and the `2π` convention written into the
   specification in the same commit
5. `test:` the ladder and the envelope run
6. `docs:` the phase plan, the knowledge base, and the measured numbers

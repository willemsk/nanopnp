# Code review 100: WP6.10, the composition (PR #227)

2026-11-27 · branch `claude/relaxed-heisenberg-axbj47`, head `640c88b` on base `5332fbd` · scope: 48 files, +2,779
and −1,062, read from `git diff 5332fbd...640c88b`, against
[the plan](../plans/phase-6/wp6.10-the-composition.md), FR-40, QR-13, VER-65, VER-81, VER-14, VER-15, VER-41,
VER-42, VER-62, VER-80, NUM-12's and NUM-14's NOTEs, NUM-24, PHY-23, §8.2.62 BL1, BL5 and BL6, REV-300, REV-302,
`CLAUDE.md` and the two rule files · reviewer: `np-reviewer`, Opus 5.5 at high effort, with the eight findings of
the `/code-review` hunt on the same head · status: completed.

Static review of the kernel, the coupled terms and their readers, with the carried tests. Probes: each slot of
`coupled.py` against the integral it replaces in `CoupledModel.residual_form`, `_flow_residual`, `_flow_state` and
`poisson.py` at `5332fbd` (integrand, sign, domain, `singular`, `extra_order`, `rule_order`); `measures.py` for what
`volume`, `surface` and `integrate` do with each; `materials/models.py` `FittedCorrection.evaluate` for the factor
that comes back as the float 1.0; the readers in `post/qoi.py`, `solve/continuation.py` and `post/forces.py`; the
test changes against the test scope (§8.2.13 N1). No benchmark, sweep, `gate.sh` or nightly run. After the fixes,
`uv run pytest` on the 31 files that cover the kernel, the flow, the transport, the stabilisation, the readers, the
forces, the surface charge and the backend guard, in two runs: 128 passed, then 362 passed and 6 skipped. Line
numbers are the reviewed head's.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Medium | `src/nanopnp/post/forces.py:466-469`; `physics/flow.py:106` | Hunt 1. Axis 3, QR-12. `permittivity_gradient` returns None wherever `permittivity_varies` is False, and that holds with a fitted permittivity whose concentration part is off: `FittedCorrection.evaluate` returns the float 1.0 (`materials/models.py:126-141`). With no solid fraction, `_integrands` reaches the `else` branch (the model is not `none`) and `assert gradient is not None` aborts every force QoI; under `-O` it raises TypeError. At `5332fbd` the same case took a zero Korteweg–Helmholtz force. Confirmed | Fixed: a None gradient takes the zero vector, as before |
| 2 | Low | `src/nanopnp/physics/models.py:1078-1081` | Hunt 2. Axis 1. `CoupledModel.context` built the permittivity for every context, so `cell_peclet`, `indicator_currents` and `stabilisation_currents`, which read none, each logged the unassigned-solid warning of `relative_permittivity_field` again. Confirmed | Fixed: the permittivity is built only for a context given the potential's test function, the one that can close a Poisson slot; `_permittivity_flux`'s refusal says so |
| 3 | Low | `CHANGELOG.md:44-48` | Hunt 3. Axis 1, `.claude/rules/python.md` (a break of a public name goes into `CHANGELOG.md`). The entry listed the deleted functions but not the changed signatures and records: the operators argument of `ConcentrationVariables.primitive`, `logarithmic_branch` and `excess_potential_gradient`; `measures` before `wall_distance_nm` in `cell_peclet`; `TransportModel`'s two added methods; the fields of `TransportState` and `FlowState`; the mappings the modes return; `permittivity_gradient`'s None; `stabilisation.element_size` and `StabilisationIntegrand` removed. A call `cell_peclet(state, distance)` fails with a TypeError, as `wall_distance_nm` has no default; it does not bind silently, as the hunt said. Confirmed | Fixed: a *Changed* entry for the interface, the two removals added |
| 4 | Low | `src/nanopnp/post/qoi.py:83-126` | Hunt 4. Axis 3, NUM-26. The hunt says the route check lost an independence it had. Refuted: at `5332fbd` the reaction flux came from `residual_form`, which integrated `species_flux`, and the indicator integrated the same `species_flux`; the stabilisation's two routes both called `transport_contributions`. A sign flip in the steric term reached both routes then as now. The 6.5 × 10⁻³ failure is the prototype's, whose indicator wrote the flux apart. D4 and BL5 rule that the indicator reads the `flux` slot, and `docs/design/kernel.md` and §8.7 of the NGSolve traps name the guards that see a dropped or flipped term: VER-81 (b) and the stored walks | Refuted |
| 5 | Low | `physics/flow.py:1,71`; `nernst_planck.py:1,203`; `stabilisation.py:1`; `kernel.py:76,205`; `numerics/gates.py:383`; `models.py:877`; `post/qoi.py:160` | Hunt 5. Axis 1, §8.4.2 (identifiers live in test names and commit messages, not prose). Docstrings and a comment written or rewritten by the package cite PHY-23, NUM-07, NUM-12, NUM-26 and the clause lists of three module lines. The `KernelTerm` `clause` fields are data and stay. Confirmed | Fixed: the prose says what it names, without identifiers |
| 6 | Low | `tests/tier2/test_electroosmosis.py:23`; `tests/tier1/test_flow.py:37`; `post/qoi.py:90` | Hunt 6. Axis 1, §8.4.2 (no docstring on a test or on private code). `_UnitViscosity`, `_UnitCoefficients`, which the hunt missed, and `_indicator_integrals` carry docstrings. Confirmed | Fixed: the two classes keep their reason as a comment; the function's docstring is removed |
| 7 | Low | `src/nanopnp/physics/coupled.py:181-183`; `poisson.py:51-54` | Hunt 7. Axis 3, the surface charge's sign. `surface_charge_term` says its residual sign "is written here and nowhere else", and the coupled models now write it in `_surface_charge`. A sign edit in one place alone would solve the single-field and the coupled models on mirror fields. A shared constant would add an import from `poisson.py`, which the term modules' guard does not cover; naming the pair is the smaller fix. Confirmed | Fixed: each place names the other |
| 8 | Low | `knowledge/06-numerics-fem/07-quantities-of-interest-and-the-flux-trap.md:288` | Hunt 8. Axis 1. The concept names `physics/flow.strain_rate`, removed by the package; its `[tested:]` test now calls `physics/operators.strain`. Confirmed | Fixed |

The pass fixed seven findings, the hunt's 1 to 3 and 5 to 8, and refuted one, the hunt's 4. No finding of the review's
own beyond the hunt's widened ones (6 adds `_UnitCoefficients`). No test is outside the test scope, so none is
dropped.

## Checked and found true

- **Each slot is the integral it replaces.** Poisson: `ε̃_r ∇φ̃ · ∇v` over Ω, `−S Σz_i c̃_i v` on the fluid, `−ρ̃_fixed
  v` at the charge's rule, `−σ̃ v` on the charged boundary with no `singular`, as `poisson_operator`, the two
  `charge_source` calls and `surface_charge_term(side="residual")` did. Flux: `−(D̃∇c̃ + c̃ Σb) · ∇w` on the fluid at
  the estimated rule, the old bracket in another order. Flow: `2η̃ ε(ũ):ε(v)` estimated; `2η̃ (ũ_r/r)(v_r/r)`,
  `−p̃ div(v)` and `−q ρ̃ div(ũ)` singular; `momentum.force` closes `−f · v` with `f = −Re ρ̃(∇ũ)ũ − S Σz_i c̃_i ∇φ̃ −
  ½|∇φ̃|²∇ε̃_r`, which gives the old `+` inertia, `+` ionic and `+` dielectric integrals. The measure is `r dr dz`
  throughout, through `Measures`, and every `1/r` slot is singular. The sources close `−s · test`, φ's on Ω.
- **The stabilisation.** `momentum_residual` is `∇p̃ − f − s`, the old `∇p̃ + Re ρ̃(∇ũ)ũ − f_body − s` with inertia
  gated by the term in force rather than the flag; `flow_state`'s density is 1 without the variable density, as
  before; `crosswind_projector` takes the geometry's identity, `Id(2)` in 2D. The lagged side is the trial side
  where no state is given, as before.
- **The quadrature reaches the integral.** `kernel.integrals` hands each slot's `singular`, `extra_order` and
  `rule_order` to `Measures.volume` or `surface` (`kernel.py:298-310`); the indicator integrates at the slot's
  `singular` and `extra_order`, the old order for the flux and the mode's bonuses for the two stabilisation slots.
  The carried quadrature tests read the slot table, which is what `integrals` reads.
- **The readers.** The wind, the cell Péclet number, the approximate residual and the indicator read the drifts of
  `context.terms`, the decrement among them (BL5); `_report_peclet` passes the solution's solid fraction and records
  `wind_text` of the terms in force; the default text equals NUM-12's printed one, which VER-81 (c) asserts.
- **In force.** `terms_in_force` reads `Steric flux`'s leaf as `CoupledModel.steric` and every display record's
  switches; `pnp` drops the flow's terms and the advection, and the slots of an absent field are left out. The log
  branch beside PHY-23 is refused at construction (`models.py:654`), so the decrement's drift never meets it.
- **The backend guard.** VER-65's two added tests read each build, drift, force and closing's `__module__` and find
  no backend reference in the four term modules, `kernel.py` or `operators.py`; the substituted import on line 1 of
  `flow.py` is returned. `coefficients.py` and `materials/fields.py` keep theirs, behind the context (§5.4.1).
- **The tests.** VER-81 (a) to (c) are as the row states: one integral within 10⁻¹² and apart above 10⁻⁶; a term
  left out moves its own slots alone; each reader within 10⁻¹², each flux and force term moving its reader by more
  than 10⁻⁶. The carried VER-14 and VER-15 load is `−(−f · v)` with `f = −S ρ ∇φ`, the old load. No tolerance moved.

## Not assessed

- The thirteen walks and REV-302's timings, which the plan's Outcomes record and this review did not repeat.
- Whether REV-302's recommendation holds; it stays open with WP6.11's plan.

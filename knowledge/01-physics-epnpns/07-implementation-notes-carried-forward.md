---
type: Physics
title: 7. Implementation notes carried forward
description: Implementation notes carried forward from the source work.
tags:
- physics
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
verified:
- by: process:tests/tier1/test_electrolyte.py::test_langevin_is_accurate_across_the_series_cutoff
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_electrolyte.py::test_phy21_switches_and_corrections_cannot_disagree
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_electrolyte.py::test_phy21_with_switches_changes_the_behaviour_not_only_the_record
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_knowledge_arithmetic.py::test_limiting_current_depletion_debye_and_mobility_ratios
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_solution_state.py::test_ver34_the_wall_distance_field_is_restored_and_not_re_solved
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_ladder.py::test_num18_re_solving_a_converged_rung_costs_one_iteration_and_moves_nothing
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_pnp_benchmarks.py::test_ver16_current_saturates_at_the_limiting_value
  at: '2026-10-16T00:00:00Z'
---

## 7. Implementation notes carried forward

- **Mollify the wall-distance field.** The original used an unsmoothed COMSOL general-extrusion
  distance. Because `D`, `μ` and `η` all depend on `d`, a kinked `d` propagates straight into the
  Jacobian. Compute `d` once per mesh (eikonal or screened-Poisson) and smooth it to C¹. This is a
  deviation from the original *implementation* but not from the *model*, and should improve Newton
  behaviour rather than change the answer. Verify against COMSOL either way. **Superseded by the
  author's ruling of 2026-10-19:** the validated default is the unsmoothed C⁰ field and the C¹
  smoothing is an optional deviation, off by default (`SPECIFICATION.md` PHY-02, NUM-31).
- **Direct solver + damped Newton is known to work.** The author reports efficient convergence in
  COMSOL using PARDISO with a Newton method and a **lower-bounded variable damping factor**. This
  is direct empirical evidence for this exact system and outweighs the general literature warning
  (Mitscha-Baude et al. 2017) that monolithic Newton struggles at high surface charge. Make damped
  monolithic Newton the primary strategy; keep segregated/Gummel as fallback.
- **Clamping and packing.** Assert `Σ_j N_A a_j³ c_j < 1` every Newton step; a packing fraction
  reaching 1 makes `β_i` singular. Fail loudly with the offending location.
- **A saturated distance field silently disables half the correction set.** Every correction is a
  product of a concentration factor and a wall factor in `d`, so passing a constant `d` large enough
  that `f^w = 1` — the honest way to say "no wall correction is active" at a call site — leaves the
  run exercising the concentration half alone while looking, from the switches, fully corrected. A
  configuration claiming "every correction active" must be handed a real `d`, from the **pore wall
  only**; the membrane is deliberately not a source (PHY-02). The failure is silent because the
  answer is a perfectly reasonable one for a different model.
- **An electrolyte's correction switches are a *record*; the resolved models are the behaviour.**
  Resolve the switches to correction models once, at construction, and every property accessor reads
  the resolved model — the switches are never consulted again. Swapping the switches alone therefore
  produces an object that reports one configuration in its provenance and evaluates another, and the
  run that follows calls itself PNP-NS, converges, and is ePNP-NS. That makes the PHY-21 ablation
  compare a configuration against itself. Rebuild the resolved models whenever the switches change,
  and refuse a pair that disagrees. **[tested: tests/tier1/test_electrolyte.py::test_phy21_with_switches_changes_the_behaviour_not_only_the_record]** **[tested: tests/tier1/test_electrolyte.py::test_phy21_switches_and_corrections_cannot_disagree]**
- **Two errors can cancel and hide both.** The 1D limiting-current benchmark passed for a while at
  the wrong film length *because* of the bug above: a 100 nm film is space-charge-limited and reads
  14 % high against the electroneutral closed form, while the silently-active corrections broke the
  Einstein relation (`mu/mu0` = 0.63 against `D/D0` = 0.92 at 1 M) and pulled the current down by
  about as much. Fixing either alone turns a passing benchmark red. **[tested: tests/tier1/test_knowledge_arithmetic.py::test_limiting_current_depletion_debye_and_mobility_ratios]**
- **The screening length that matters at a depleted electrode is not the bulk one.** `lambda_D` goes
  as `c^(-1/2)`, so at 1e-3 of bulk it is thirty-two times larger — 9.6 nm at 1 M. A benchmark that
  justifies its geometry with the bulk value can be an order of magnitude out. The signature of a
  space-charge-limited film is that the plateau current stops depending on the electrode
  concentration at all. **[tested: tests/tier1/test_knowledge_arithmetic.py::test_limiting_current_depletion_debye_and_mobility_ratios]** **[tested: tests/tier2/test_pnp_benchmarks.py::test_ver16_current_saturates_at_the_limiting_value]**
- **`d` is a discrete field, so it must travel with the solution, not be recomputed.** Two calls to
  the same distance solver return grid functions that differ at round-off, and a residual reassembled
  against the second is a *different operator* from the one that was solved. Any post-processing that
  rebuilds the flux — the ψ-indicator current does — or any warm start that re-solves a converged
  state must read `d` back off the solution. **[tested: tests/tier1/test_solution_state.py::test_ver34_the_wall_distance_field_is_restored_and_not_re_solved]** **[tested: tests/tier2/test_ladder.py::test_num18_re_solving_a_converged_rung_costs_one_iteration_and_moves_nothing]**
- **The Langevin function switches to its `x/3` limit at `x = 3e-4`.** `coth(x) - 1/x` has relative
  error about `3 eps / x^2` and the series `x/3` has `x^2/15`; they cross near `3e-4`, both accurate to
  about 7e-9. A cutoff of 1e-8 is inside the cancellation region: `L(1.1e-8)` evaluates to exactly zero
  instead of 3.667e-9. **[tested: tests/tier1/test_electrolyte.py::test_langevin_is_accurate_across_the_series_cutoff]** (source: `materials/forms.py`, `_LANGEVIN_SERIES_CUTOFF`)

---


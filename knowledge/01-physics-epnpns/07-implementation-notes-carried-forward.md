---
type: Physics
title: 7. Implementation notes carried forward
description: "Implementation lessons for the physics, from the source work and from building nanopnp: the
  unsmoothed d, damped Newton, the packing assert, a saturated d, switches versus resolved models, the
  Langevin cutoff."
tags:
- physics
sources:
- id: thesis
  resource: https://github.com/willemsk/phdthesis-text
  title: Willems, PhD thesis (LaTeX source)
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
- by: process:tests/tier2/test_ladder.py::test_num18_re_solving_a_converged_rung_costs_one_iteration_and_moves_nothing
  at: '2026-10-16T00:00:00Z'
---

## 7. Implementation notes carried forward

- **The wall-distance field is unsmoothed.** The original used an unsmoothed COMSOL
  general-extrusion distance. The validated field is the unsmoothed C⁰ field; C¹ mollification is an
  optional deviation, off by default (PHY-02, NUM-31). Because `D`, `μ` and `η` all depend on `d`, a
  kinked `d` reaches the Jacobian, which is why the option exists.
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
- **The limiting-current benchmark's two lessons** (two errors that cancel, and the screening
  length at a depleted electrode) are under VER-16's benchmark,
  `knowledge/08-validation-benchmarks/02-tier-2-analytic-benchmarks-minutes.md` §2.5.
- **`d` travels with the solution and is not recomputed**: why is in
  `knowledge/06-numerics-fem/15-tier-1-test-evidence-scaling-the-wall.md`, the restore. A warm start
  that re-solves a converged rung, with `d` read off the solution, costs at most one Newton
  iteration and moves nothing. **[tested: tests/tier2/test_ladder.py::test_num18_re_solving_a_converged_rung_costs_one_iteration_and_moves_nothing]**
- **The Langevin function switches to its `x/3` limit at `x = 3e-4`.** `coth(x) - 1/x` has relative
  error about `3 eps / x^2` and the series `x/3` has `x^2/15`; they cross near `3e-4`, both accurate to
  about 7e-9. A cutoff of 1e-8 is inside the cancellation region: `L(1.1e-8)` evaluates to exactly zero
  instead of 3.667e-9. **[tested: tests/tier1/test_electrolyte.py::test_langevin_is_accurate_across_the_series_cutoff]** (source: `materials/forms.py`, `_LANGEVIN_SERIES_CUTOFF`)

---


---
type: Test Evidence
title: 'Tier-2 test evidence: ladder walks, block systems and extraction routes'
description: "The access-conductance benchmark, the wall-pinned trivial state, the block system's constraints, the force tolerance and reference record, the envelope walk, and the route agreement under stabilisation."
tags:
- numerics
- test-evidence
sources:
- id: factorisation-doc-3782c43
  resource: git:3782c43:tests/tier2/test_factorisation_benchmark.py
  title: tests/tier2/test_factorisation_benchmark.py module docstring at 3782c43
- id: envelope-doc-3782c43
  resource: git:3782c43:tests/tier2/test_envelope.py
  title: tests/tier2/test_envelope.py module docstring at 3782c43
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
verified:
- by: process:arithmetic
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_access_conductance.py::test_ver17_the_access_term_is_a_fifth_of_the_resistance_and_carries_the_factor_two
  at: '2026-10-14T00:00:00Z'
- by: process:tests/tier2/test_access_conductance.py::test_ver17_the_finite_reservoir_is_not_what_the_benchmark_measures
  at: '2026-10-14T00:00:00Z'
- by: process:tests/tier2/test_coupled_gates.py::test_num17_packing_gate_aborts_a_coupled_solve_at_high_salt
  at: '2026-10-14T00:00:00Z'
- by: process:tests/tier2/test_current_routes.py::test_num26_the_routes_agree_in_reference_only_because_psi_carries_the_term
  at: '2026-10-14T00:00:00Z'
- by: process:tests/tier1/test_wall_distance.py::test_num34_the_coarse_mesh_is_refused_naming_everything_it_measured
  at: '2026-10-14T00:00:00Z'
- by: process:tests/tier2/test_envelope.py::test_82_bias_walk_emits_waypoints_verbatim
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_force_convergence.py::test_rsk04_the_reference_shaped_case_is_recorded
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_force_routes.py::test_ver22_both_halves_of_the_force_are_large_and_opposed
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_access_conductance.py::test_ver17_the_model_s_own_bulk_conductivity_of_1_m_nacl_is_12_6_s_per_m
  at: '2026-10-18T00:00:00Z'
---

## Tier-2 test evidence: ladder walks, block systems and extraction routes

- **[tested: tests/tier2/test_access_conductance.py::test_ver17_the_access_term_is_a_fifth_of_the_resistance_and_carries_the_factor_two]** For the Maxwell-Hall pore (`a = 2 nm`, `L = 13 nm`) the access term `1/(2a)` is 19.5 % of the total resistance (`1/(2a) = 2.5e8 /m` against `L/(πa²) = 1.035e9 /m`); halving the access resistance would move `G` by about 10 % and doubling it by about 16 %.
- **[tested: tests/tier2/test_access_conductance.py::test_ver17_the_finite_reservoir_is_not_what_the_benchmark_measures]** A finite reservoir truncates the access term by of order `a/R`: a few per cent of the 19.5 % at `R = 50 nm`, about 1 % on `G`. Running `R = 50` and `100 nm` measures that truncation; `G` moves 0.23 % between them.
- **[tested: tests/tier2/test_access_conductance.py::test_ver17_the_model_s_own_bulk_conductivity_of_1_m_nacl_is_12_6_s_per_m]** The infinite-dilution conductivity of 1 M NaCl from the model's own mobilities is 12.6 S/m, against about 8.5 S/m measured for real 1 M brine; the gap is the concentration correction a classical run switches off, so the closed form must be compared with 12.6, not 8.5. Source: `test_access_conductance.py` (`bulk_conductivity_S_m`).
- **[tested: tests/tier2/test_coupled_gates.py::test_num17_packing_gate_aborts_a_coupled_solve_at_high_salt]** With the potential fixed on the wall alone, a uniform `φ̃` at the wall value and a uniform `c̃ᵢ = 1` satisfy every coupled equation exactly, and the solve returns that trivial state; the reservoir ends must carry essential data too for a real solve to be forced.
- **[verified][^factorisation-doc-3782c43]** The reservoir-cap Dirichlet constraints of the five-field block system remove 4.50 % of the degrees of freedom at the production size, 5.73 % at the SuperLU size and 8.96 % at `maxh` 3.0, so the timed factorisations are slightly smaller than the unconstrained table of §6.1 and its figures are upper bounds. Source: `tests/tier2/test_factorisation_benchmark.py` (module docstring at `3782c43`, before WP45, and `build_coupled_system`).
- **[tested: tests/tier2/test_force_routes.py::test_ver22_both_halves_of_the_force_are_large_and_opposed]** NUM-29's 0.1 pN absolute force tolerance is 0.219 in the nondimensional force unit `εV_T²`, the unit the force routes are compared in; the tolerance is absolute rather than relative because a relative test on a total that is a small difference of two large forces reports agreement the split does not have. Source: `tests/tier2/test_force_routes.py` (module docstring at `3782c43`, before WP45).
- **[tested: tests/tier2/test_force_convergence.py::test_rsk04_the_reference_shaped_case_is_recorded]** The reference-shaped record (ePNP-NS, every correction, 300 mM, +50 mV, `q = −4 e`, `ε_p = 20`) gives two opposed forces of a few piconewtons, not the reference's ten: the analytic cylinder carries a uniform wall charge, no cis cone or constriction, and a lumen widened from the reference's 7.2 nm diameter to 9 nm (the QR-12 sliver risk of grading two surfaces a fraction of a nanometre apart). The structure, `F^em` towards trans and `F^hd` towards cis, carries over. Source: `tests/tier2/test_force_convergence.py` (module docstring at `3782c43`, before WP45).
- **[tested: tests/tier2/test_envelope.py::test_82_bias_walk_emits_waypoints_verbatim]** The envelope's bias walk must be built from its waypoints outwards, not from a uniform step: a uniform walk from +50 mV to +200 mV has span `0.15000000000000002` in binary floating point, so `ceil(span/0.05)` is 4 and the walk steps 0.0875, 0.125, 0.1625, 0.2 and passes over +100 mV, an envelope point. Emitting each waypoint verbatim avoids this. Source: `tests/tier2/test_envelope.py` (`_walk`).
- **[tested: tests/tier2/test_envelope.py::test_82_bias_walk_emits_waypoints_verbatim]** Recording the envelope on the way past each point (the monotone walks from the concentration spine) costs 45 warm-started rungs for the whole 30-point grid; restarting each target from the spine instead covers the same ground about five times over and nearly doubles the run **[verified][^envelope-doc-3782c43]**. Source: `test_envelope.py` (module docstring at `3782c43`, before WP45).
- **[tested: tests/tier1/test_wall_distance.py::test_num34_the_coarse_mesh_is_refused_naming_everything_it_measured]** On the 124-element toy pore of `07-quantities-of-interest-and-the-flux-trap.md` §7.1.1 the signed distance field reaches −0.94 nm over the fluid, with 9.7 % of the samples negative. The stabilisation term's share of the current on the VER-11 pore, −8.1 %, and why it exceeds the NUM-30 estimate: `04-stabilisation.md` §4.2.1.
- **[tested: tests/tier2/test_current_routes.py::test_num26_the_routes_agree_in_reference_only_because_psi_carries_the_term]** Subtracting the stabilisation term from the bare indicator integral `∫J̃·∇ψ` leaves the NUM-24 route and the NUM-25 reaction flux agreeing to within NUM-26's tolerance, and the uncorrected routes differ by about eighty times it; the NUM-26 identity asserts the gap equals the independently computed contribution, species by species.

[^factorisation-doc-3782c43]: `git show 3782c43:tests/tier2/test_factorisation_benchmark.py`, module docstring (before WP45).
[^envelope-doc-3782c43]: `git show 3782c43:tests/tier2/test_envelope.py`, module docstring (before WP45).

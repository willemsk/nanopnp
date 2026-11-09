---
type: Test Evidence
title: 'Tier-1 test evidence: scaling, the wall-distance clamp and the warm-start rationale'
description: "The Péclet number and force scale, the wall forms' clamp and gate, the restore of a stored distance field, the zero-wind stabilisation, and the reference sweep's pairing."
tags:
- numerics
- test-evidence
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
verified:
- by: process:tests/tier1/test_scaling.py::test_num09_peclet_at_twenty_degrees_is_the_commonly_quoted_value
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_scaling.py::test_num09_peclet_number_is_below_one
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_scaling.py::test_num09_summary_carries_every_scale_for_the_manifest
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_scaling.py::test_num28_force_scale_does_not_depend_on_the_reference_length
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_scaling.py::test_num28_force_scale_is_the_permittivity_times_the_thermal_voltage_squared
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_scaling.py::test_num28_force_scale_is_the_pressure_scale_through_a_pore_sized_area
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_solution_state.py::test_ver34_the_wall_distance_field_is_restored_and_not_re_solved
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_stabilisation.py::test_num14_every_term_vanishes_at_a_state_with_no_wind
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_stabilisation.py::test_ver41_the_linearisation_is_finite_at_the_zero_wind_cold_state
  at: '2026-10-14T00:00:00Z'
- by: process:tests/tier1/test_sweep_plan.py::test_ver36_the_reference_sweep_parses_and_enumerates_the_section_8_3_grid
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_wall_distance.py::test_num31_the_gradient_jump_survives_the_file_round_trip
  at: '2026-10-14T00:00:00Z'
- by: process:tests/tier1/test_wall_distance.py::test_num34_threshold_is_one_named_constant_between_the_root_and_the_residual
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_wall_distance.py::test_ver40_both_wall_forms_return_their_wall_value_for_every_non_positive_sample
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_wall_distance.py::test_ver40_the_clamp_is_continuous_across_zero
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_warm_start_descriptor.py::test_val01_a_warm_start_across_an_element_order_is_refused
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_warm_start_descriptor.py::test_ver37_the_loaded_state_carries_no_residual_and_no_stored_distance
  at: '2026-10-16T00:00:00Z'
---

## Tier-1 test evidence: scaling, the wall-distance clamp and the warm-start rationale

- **[tested: tests/tier1/test_scaling.py::test_num09_peclet_number_is_below_one]** The frequently quoted Péclet number 0.386 needs `ε_r` near 78.4. The model's own fitted `ε_r,f0 = 78.15` gives `Pe = 0.3847`, 0.3 % lower (NUM-09 quotes 0.385), with no physical effect; the value is pinned rather than rediscovered. **[tested: tests/tier1/test_scaling.py::test_num09_peclet_at_twenty_degrees_is_the_commonly_quoted_value]** At 20 °C and `η = 1.00 mPa s` the frequently quoted 0.34 is the same ratio at the other viscosity temperature, so the two are never mixed across material properties.
- **[tested: tests/tier1/test_scaling.py::test_num28_force_scale_is_the_permittivity_times_the_thermal_voltage_squared]** The force scale `F_0 = p_0 a² = ε V_T²` is 0.4568 pN, so the NUM-29 tolerance of 0.1 pN is 0.219 `F_0`. **[tested: tests/tier1/test_scaling.py::test_num28_force_scale_is_the_pressure_scale_through_a_pore_sized_area]** **[tested: tests/tier1/test_scaling.py::test_num28_force_scale_does_not_depend_on_the_reference_length]** `p_0 a²` does not depend on the reference length `a`, so 0.1 pN means the same on a 2 nm pore and a 20 nm one.
- **[tested: tests/tier1/test_scaling.py::test_num09_summary_carries_every_scale_for_the_manifest]** A manifest that omits the viscosity cannot say whether a run took it at 20 °C or 25 °C, which is a silent per-cent error in `u_0`, `p_0` and `Pe`.
- **[tested: tests/tier1/test_wall_distance.py::test_ver40_both_wall_forms_return_their_wall_value_for_every_non_positive_sample]** The viscosity wall form `f^w_η(0) = 1 + exp(−3.36 · (−0.147))` has no root and cannot be inverted: it is 17.7 times wrong at the measured minimum of `d` on the toy pore, which is why the PHY-02 clamp sits on the shared driver and not in the ion form.
- **[tested: tests/tier1/test_wall_distance.py::test_ver40_the_clamp_is_continuous_across_zero]** The ion wall function's slope at the wall is `P1 exp(−P1 P2) = 5.83` per nm, so `d = 10⁻⁹ nm` lies at `10⁻⁷` of the wall value. A `10⁻⁶` tolerance bounds that and still catches a step, which is the discontinuity a clamp on the factor would introduce.
- **[tested: tests/tier1/test_wall_distance.py::test_num31_the_gradient_jump_survives_the_file_round_trip]** On the toy pore (2 nm radius, 30 nm reservoir, 0.15 nm wall) the normalised facet jump of the unsmoothed `grad d` is 0.494. `JUMP_TOL` was measured on a cylinder at 0.1 nm wall resolution, so the two figures are not comparable; the file round trip is held to floating-point equality, which is sharper than any threshold.
- **[tested: tests/tier1/test_wall_distance.py::test_num34_threshold_is_one_named_constant_between_the_root_and_the_residual]** The NUM-34 threshold lies between the ion function's root and the residual `Set` leaves behind: why, in the gate constants of `09-ngsolve-traps-found-by-implementing.md`.
- **[tested: tests/tier1/test_solution_state.py::test_ver34_the_wall_distance_field_is_restored_and_not_re_solved]** A distance field re-solved on the same build matches the stored one to ten digits, so agreement cannot show that a restore reads the stored vector; **[tested: tests/tier1/test_warm_start_descriptor.py::test_ver37_the_loaded_state_carries_no_residual_and_no_stored_distance]** restore tests therefore move the stored vector and require the moved field.
- **[tested: tests/tier1/test_stabilisation.py::test_num14_every_term_vanishes_at_a_state_with_no_wind]** The stabilisation terms vanish identically at `φ̃ = 0`, `c̃_i = 1`, `ũ = 0`, `p̃ = 0` (no wind, symmetric salt at bulk), so every mode is identical at the entry rung of the NUM-18 ladder.
- **[tested: tests/tier1/test_stabilisation.py::test_ver41_the_linearisation_is_finite_at_the_zero_wind_cold_state]** The linearisation at zero wind is finite only with `MAGNITUDE_FLOOR` inside the root: trap 19 of `09-ngsolve-traps-found-by-implementing.md`.
- **[tested: tests/tier1/test_warm_start_descriptor.py::test_val01_a_warm_start_across_an_element_order_is_refused]** `P1/P1` is not inf-sup stable and `resolve` refuses it outside the reference stabilisation (NUM-03); the warm-start element-order refusal therefore uses P2 against P3.
- A rectification pairing must be exact: a tolerance would report 100 mV against −95 mV as a rectification, a ratio between two unrelated operating points. Source: `tests/tier1/test_sweep_plan.py`.
- **[tested: tests/tier1/test_sweep_plan.py::test_ver36_the_reference_sweep_parses_and_enumerates_the_section_8_3_grid]** The `SPECIFICATION.md` §8.3 reference axis roots its bias at +5 mV, not 0 V (`09-ngsolve-traps-found-by-implementing.md` §8.5), and enumerates in 42 waves: the bias origin is 0 V and the salt origin the low end, so the deepest point is `4 + 17 + 20 = 41`.


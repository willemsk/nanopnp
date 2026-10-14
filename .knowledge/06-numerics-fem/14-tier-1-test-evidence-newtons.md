---
type: Test Evidence
title: 'Tier-1 test evidence: Newton''s counterexamples, the band and the vector indicator
  (WP45 item 23)'
---

## Tier-1 test evidence: Newton's counterexamples, the band and the vector indicator (WP45 item 23)

- **[verified]** Undamped Newton on `arctan(u) = 0` from `u = 10` steps to the tangent's zero, `u − (1 + u²) arctan u ≈ −138.6`, where the residual is larger than before. At minimum damping 0.5 no admissible step reduces the residual, so the step must be accepted, not aborted (NUM-16). Source: `tests/tier1/test_newton.py` (`test_num16_minimally_damped_step_is_accepted_not_aborted`).
- **[verified]** Newton on `sqrt(u) = 0.1` has the map `u ↦ 0.2√u − u`, so from `u = 4` the first step lands at `u = −3.6`, where `√u` is NaN. A NaN trial residual compares false against `current`, so a forced step must be recorded as forced. Source: `tests/tier1/test_newton.py` (`test_num16_a_nan_trial_residual_at_minimum_damping_is_a_forced_step`).
- **[tested]** On the reference mesh, the current over bands of half-width 0.6, 1.5, 2.4 and 2.9 nm varies by 6.7 × 10⁻¹⁰ relative: the band is not a quadrature choice. The mesh-derived band equals the geometry band to 10⁻¹² nm, which is round-off and not a band anyone meant. Source: `tests/tier1/test_qoi_stage.py` (`test_fr23_the_current_does_not_depend_on_where_the_band_sits`, `test_fr23_the_generated_mesh_gives_the_same_band_to_mesh_round_off`).
- **[verified]** `ngsolve.CF(1.0)` cannot fill a `VectorH1` block, so the vector-valued boundary indicator of NUM-25 (the axial reaction force of NUM-28) needs a vector coefficient. Source: `tests/tier1/test_reaction_flux.py`.
- **[tested]** With the permittivity correction `none`, the sensitivity is the float 1.0; `.Diff` on a float raised `AttributeError` inside the residual assembly, naming neither the switch nor the correction. The sensitivity is identically zero there. Source: `tests/tier1/test_nernst_planck.py` (`test_phy23_the_permittivity_sensitivity_is_zero_when_the_correction_is_off`).


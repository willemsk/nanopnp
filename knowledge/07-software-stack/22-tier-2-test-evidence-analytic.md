---
type: Test Evidence
title: 'Tier-2 test evidence: analytic benchmarks and reference checks (WP45 item
  26)'
description: What the Tier-2 tests of analytic benchmarks and reference checks establish,
  recorded at WP45 item 26.
tags:
- software
- test-evidence
sources:
- id: pnp-benchmarks-3782c43
  resource: git:3782c43:tests/tier2/test_pnp_benchmarks.py
  title: Module docstring of tests/tier2/test_pnp_benchmarks.py before WP45 (commit
    3782c43)
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
verified:
- by: process:arithmetic
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_stability_golden.py::test_ver62_fold_refuses_a_tolerance_above_the_ceiling
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_charge_potential_axis.py::test_ver58_deposited_potential_converges_at_the_potentials_own_rate_on_the_axis
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_charge_potential_axis.py::test_ver58_the_closed_form_vanishes_on_the_sphere
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_maxwell_sphere.py::test_ver20_a_charged_body_in_a_uniform_field_feels_q_e_zero
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_maxwell_sphere.py::test_ver20_the_dielectric_sphere_matches_its_closed_form
  at: '2026-10-14T00:00:00Z'
- by: process:tests/tier2/test_maxwell_sphere.py::test_ver20_the_net_force_on_a_dielectric_sphere_vanishes
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_mesh_backends.py::test_ver54_the_frozen_case_conducts_alike_on_both_backends_meshes
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_mms.py::test_ver18_taylor_hood_pressure_converges_at_its_own_order
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_pipeline_2wcd.py::test_ver53_2wcd_meshes_at_the_default_sizes
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_pipeline_2wcd.py::test_ver53_2wcd_walks_to_the_report_and_the_manifest_keys_every_stage
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_pnp_benchmarks.py::test_ver16_current_saturates_at_the_limiting_value
  at: '2026-10-14T00:00:00Z'
- by: process:tests/tier2/test_pnp_benchmarks.py::test_ver16_the_plateau_is_the_departure_from_ohm_s_law
  at: '2026-10-14T00:00:00Z'
- by: process:tests/tier2/test_poisson_layers.py::test_ver56_the_capacitor_distinguishes_the_permittivity_it_was_given
  at: '2026-10-14T00:00:00Z'
- by: process:tests/tier2/test_poisson_layers.py::test_ver56_the_closed_form_reproduces_the_plans_check_values
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_reference_geometry.py::test_ver28_the_assembled_topology_matches_the_section_5_2_1_count
  at: '2026-10-14T00:00:00Z'
- by: process:tests/tier2/test_reference_geometry.py::test_ver28_the_junction_is_conformal_and_lands_on_the_pore_outer_surface
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_reference_geometry.py::test_ver28_the_region_has_three_domains_and_carries_the_vocabulary
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_region_reference.py::test_ver53_the_wall_gate_passes_at_both_measured_sizes
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_reproducibility.py::test_ver35_a_run_reproduces_into_a_fresh_store
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_reproducibility.py::test_ver35_an_input_whose_contents_moved_aborts_naming_it
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_reproducibility.py::test_ver35_reproducing_into_the_store_that_holds_the_run_is_refused
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_self_golden_round_trip.py::test_val01_self_golden_reproduces_its_own_solution
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_self_golden_round_trip.py::test_val01_the_round_trip_preserves_the_masked_points_as_nan
  at: '2026-10-14T00:00:00Z'
- by: process:tests/tier2/test_stabilised_mode.py::test_num17_plain_galerkin_trips_positivity_where_reference_converges
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_stabilised_mode.py::test_ver42_the_equal_order_pair_is_recorded_and_not_gated
  at: '2026-10-14T00:00:00Z'
- by: process:tests/tier2/test_stabilised_mode.py::test_ver42_the_flow_pair_and_not_the_transport_term_sets_the_reference_rate
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_stabilised_mode.py::test_ver42_the_stabilised_mode_loses_an_order_and_no_more
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_stabilised_mode.py::test_ver42_the_two_modes_currents_converge_to_each_other_under_refinement
  at: '2026-10-14T00:00:00Z'
- by: process:tests/tier2/test_stabilised_mode.py::test_ver42_withholding_the_manufactured_source_switches_the_term_off
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_stern_layer.py::test_ver31_the_shell_potential_drop_is_linear_in_the_thickness
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_stern_layer.py::test_ver31_the_stern_layer_raises_the_wall_potential_by_the_closed_form
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_stokes_drag.py::test_ver19_a_uniform_far_field_measures_the_wall_correction_instead
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_stokes_drag.py::test_ver19_stokes_drag_converges_to_the_closed_form
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_sweep.py::test_fr25_the_manifest_of_a_warm_member_records_how_it_was_reached
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_sweep.py::test_ver37_a_warm_start_does_not_move_the_answer
  at: '2026-10-14T00:00:00Z'
- by: process:tests/tier2/test_sweep.py::test_ver37_the_warm_path_costs_strictly_fewer_newton_iterations
  at: '2026-10-14T00:00:00Z'
- by: process:tests/tier2/test_sweep.py::test_ver38_a_member_whose_parent_is_absent_falls_back_to_the_full_ladder
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_sweep_generated_mesh.py::test_ver37_a_generated_mesh_sweep_warm_starts_from_its_parent
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_sweep_throughput.py::test_ver39_the_scaling_curve_is_measured_and_recorded
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_val05_2wcd.py::test_val05_2wcd_against_the_reference_polygon
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_val05_2wcd.py::test_val05_2wcd_frozen_case_conductance
  at: '2026-10-14T00:00:00Z'
- by: process:tests/tier2/test_val06_2wcd.py::test_val06_2wcd_a_focused_grid_confirms_apbs_converges_at_first_order_or_better
  at: '2026-10-14T00:00:00Z'
- by: process:tests/tier2/test_val06_2wcd.py::test_val06_2wcd_apbs_is_unchanged_by_a_cubic_angstrom_slip_at_its_coarse_grid
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_val06_ring.py::test_val06_ring_every_broken_construction_exceeds_half_the_tolerance
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_val06_ring.py::test_val06_the_ring_series_is_grounded_continuous_and_kirkwood_at_infinity
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_qoi.py::test_num26_round_off_currents_at_zero_bias_fail_the_relative_check
  at: '2026-10-18T00:00:00Z'
---

## Tier-2 test evidence: analytic benchmarks and reference checks (WP45 item 26)

- **[tested: tests/tier2/test_maxwell_sphere.py::test_ver20_the_dielectric_sphere_matches_its_closed_form]** A dielectric sphere `ε_p` in a uniform field `E₀` has `φ = −E₀z·3/(ε_p+2)` inside and `φ = −E₀z(1 − βa³/R³)` outside, `β = (ε_p−1)/(ε_p+2)`. With the far boundary carrying `−E₀z` rather than this closed form, the computed field differs from the unbounded one by `β(a/R)³`, 3.3 × 10⁻⁴ at the test's `R`. Source: `tests/tier2/test_maxwell_sphere.py` (`test_ver20_the_dielectric_sphere_matches_its_closed_form`).
- **[tested: tests/tier2/test_maxwell_sphere.py::test_ver20_a_charged_body_in_a_uniform_field_feels_q_e_zero]** On the test's sphere mesh the magnitude anchor `F_z = qE₀` misses by 0.19 % on the domain route and 0.53 % on the surface route, both set by the straight-sided facets; VER-20 leaves its tolerance open and the test states 1 %. The anchor's reference charge `q = −4e` at 5.1 MV/m is 8.2 pN, inside RSK-04's range. Source: `tests/tier2/test_maxwell_sphere.py`.
- **[tested: tests/tier2/test_maxwell_sphere.py::test_ver20_the_net_force_on_a_dielectric_sphere_vanishes]** `electrostatic_domain_force` carries no consistency term, which is exact where `div(T_M) = 0` over the region `w` varies on; the fluid of the VER-20 problems is charge-free and uniform, so it is the right entry point. Source: `tests/tier2/test_maxwell_sphere.py`.
- **[tested: tests/tier2/test_mesh_backends.py::test_ver54_the_frozen_case_conducts_alike_on_both_backends_meshes]** The Gmsh and netgen conductances of the reference fixture at `size_scale` 2 differ by 1.25 × 10⁻⁴; refining netgen from `size_scale` 2 to 1 moves its own conductance by 2.0 × 10⁻⁴. The 1 × 10⁻³ bound in VER-54 is eight times the measured value, chosen from that comparison (WP23 plan, Design §4) and not fitted. Source: `tests/tier2/test_mesh_backends.py`.
- **[tested: tests/tier2/test_mms.py::test_ver18_taylor_hood_pressure_converges_at_its_own_order]** The Taylor-Hood pressure of the MMS problem converges at `O(h²)`, the pair's own rate, and asserting `O(h³)` there would assert something untrue of a correct solver. The MMS sequence is a 2 × 4 nm cylinder at `maxh` 0.4, 0.2 and 0.1 nm, with the finest level near 2 × 10⁴ degrees of freedom, three orders below the 1.04 × 10⁶ at which WP3 measured 41 s and 6.2 GB for one factorisation. Source: `tests/tier2/test_mms.py`.
- **[tested: tests/tier2/test_pipeline_2wcd.py::test_ver53_2wcd_meshes_at_the_default_sizes]** The prepared 2WCD structure meshes at the default sizes with VER-10 and the D9 wall gate passing (RSK-05 retired). Its axial registration places the C-alpha centroid of residues 8 to 292 at `Z_MD`; WP21 used the trans tip plus 1.85 nm, which is 0.056 nm away. Source: `tests/tier2/test_pipeline_2wcd.py`.
- **[tested: tests/tier2/test_pipeline_2wcd.py::test_ver53_2wcd_walks_to_the_report_and_the_manifest_keys_every_stage]** The 2WCD walk to stage 12 uses `pnp` at `size_scale` 4, with flow and corrections off, because the electrostatic models refuse a solid domain with no transport to screen it (section 5.3.1 NOTE). Source: `tests/tier2/test_pipeline_2wcd.py`.
- **[tested: tests/tier2/test_pnp_benchmarks.py::test_ver16_current_saturates_at_the_limiting_value]** Limiting current of the thin film. With the anion blocked at the electrode, `J₋ = 0` gives `c₋ = A exp(φ̃)`; electroneutrality outside the double layers gives `J₊ = −2D₊ grad c`, linear `c`, and `|J₊| = 2D₊c₀(1 − δ)/L`, so `|J̃₊| = 2D̃₊(1 − δ)/L̃`. The factor 2 is migration doubling diffusion and depends on the reservoir convention, which is why the test states the derivation rather than a published number. Source: `tests/tier2/test_pnp_benchmarks.py` (`test_ver16_current_saturates_at_the_limiting_value`).
- **[tested: tests/tier2/test_pnp_benchmarks.py::test_ver16_current_saturates_at_the_limiting_value]** The benchmark's two ionic diffusivities are set equal, a property of the test electrolyte; NaCl's `D_Na` and `D_Cl` differ by 52 %. Source: `tests/tier2/test_pnp_benchmarks.py`.
- **[tested: tests/tier2/test_pnp_benchmarks.py::test_ver16_current_saturates_at_the_limiting_value]** The factor 2 holds only where `μ̃ᵢ = D̃ᵢ` (infinite dilution, PHY-14, VER-05). With the concentration corrections active, `μ/μ₀` is 0.63 at 1 M against `D/D₀` = 0.92, the factor falls to about 1.7 and the current drops by about 15 %. An earlier version of this benchmark passed because two errors cancelled: space-charge limitation raised the current by 14 % and silently active corrections lowered it by about as much. Source: `tests/tier2/test_pnp_benchmarks.py`.
- **[verified][^pnp-benchmarks-3782c43]** At `δ` = 10⁻³ and classical PNP, the current over the closed form is 1.138 at `L` = 100 nm, 1.050 at 400 nm, 1.026 at 1000 nm and 1.017 at 2000 nm. `λ_D` is 0.30 nm at 1 M but goes as `c^(−1/2)`, so at the electrode's 10⁻³ of bulk it is 9.6 nm, 32 times larger; a 100 nm film is then space-charge limited, which is why the benchmark uses 2000 nm. Source: `tests/tier2/test_pnp_benchmarks.py` (module docstring at `3782c43`, before WP45).
- **[tested: tests/tier2/test_pnp_benchmarks.py::test_ver16_the_plateau_is_the_departure_from_ohm_s_law]** The ohmic prediction at the top of the sweep, `2Ṽ/L̃` with conductivity `Σ z²μ̃c̃ = 2`, is twenty times what a depleting solve returns at 20 `V_T` (514 mV). Source: `tests/tier2/test_pnp_benchmarks.py` (`test_ver16_the_plateau_is_the_departure_from_ohm_s_law`).
- **[tested: tests/tier2/test_pnp_benchmarks.py::test_ver16_current_saturates_at_the_limiting_value]** The quality gate is off for the 2000 nm × 0.5 nm strip at `maxh` 50 nm: it is a chain of 100:1 triangles with minimum SICN 0.019, and the solution is constant along the stretched direction, so the interpolation error of those elements is zero. Source: `tests/tier2/test_pnp_benchmarks.py`.
- **[tested: tests/tier2/test_poisson_layers.py::test_ver56_the_closed_form_reproduces_the_plans_check_values]** The three-layer capacitor: `D(z) = D₀ + ρ₀z` with `D₀ = −(V + ρ₀I₂)/I₁`, `φ(z) = −[D₀F₁(z) + ρ₀F₂(z)]`, `F₁ = ∫₀ᶻ ds/(ε₀ε_r)`, `F₂ = ∫₀ᶻ s ds/(ε₀ε_r)`; `φ` is piecewise quadratic, so P2 on a mesh with edges at `z = a` and `z = b` holds it exactly. The `r` weight adds `RADIAL_WEIGHT_ORDER` to both terms so that they integrate exactly (NUM-07 NOTE). Check values: `L` = 10, `a` = 4, `b` = 6 nm, `ε_f` = 78.15, `ε_s` = 3.2, `ρ₀` = −10⁷ C m⁻³, `V` = 0.05 V, 298.15 K. Source: `tests/tier2/test_poisson_layers.py`.
- **[tested: tests/tier2/test_poisson_layers.py::test_ver56_the_capacitor_distinguishes_the_permittivity_it_was_given]** Without an entry for the membrane's permittivity, the membrane is ion-free water (`ε_r,f⁰`) and its middle moves by volts; the three-layer test therefore discriminates a model that dropped `solid_permittivities`. Source: `tests/tier2/test_poisson_layers.py` (`test_ver56_the_capacitor_distinguishes_the_permittivity_it_was_given`).
- **[tested: tests/tier2/test_reference_geometry.py::test_ver28_the_region_has_three_domains_and_carries_the_vocabulary]** The reference region has three domains, not four: the cap's underside is re-entrant, and the membrane fills a cleft beneath it that opens downward past the cap edge at `z ≈ −0.7` and is continuous with the bilayer. Source: `tests/tier2/test_reference_geometry.py`.
- **[tested: tests/tier2/test_reference_geometry.py::test_ver28_the_junction_is_conformal_and_lands_on_the_pore_outer_surface]** The drawn membrane corners `(2, −1.4)` and `(3.5, +1.4)` lie 0.275 and 0.540 nm inside the pore body, so gates read the junction from the fixture (`r_out(−1.4) = 2.7524`, `r_out(+1.4) = 4.88`). A coincident-chain junction gives conforming coordinates and a non-conformal mesh. Source: `tests/tier2/test_reference_geometry.py`.
- **[tested: tests/tier2/test_reference_geometry.py::test_ver28_the_assembled_topology_matches_the_section_5_2_1_count]** The assembled topology adds three vertices and three edges to section 5.2.1's count of 190 vertices and 192 boundaries: two from splitting the axis at the pore's axial extent (the only way the 0.075 nm axis-in-pore size field applies) and one from the seam OCC places on the closed circle at `(250, 0)`. A glued three-face region lists 383 edges and 766 vertices for the 195 and 193 that exist, because OCC reports an edge once per face it bounds. Source: `tests/tier2/test_reference_geometry.py` (`test_ver28_the_assembled_topology_matches_the_section_5_2_1_count`).
- **[tested: tests/tier2/test_reference_geometry.py::test_ver28_the_junction_is_conformal_and_lands_on_the_pore_outer_surface]** `membrane_outer` is an arc, and its mid-height radius exceeds its ends by the sagitta of a 1.4 nm half-chord. Source: `tests/tier2/test_reference_geometry.py`.
- **[tested: tests/tier2/test_region_reference.py::test_ver53_the_wall_gate_passes_at_both_measured_sizes]** The derived region's wall statistics were logged at 0.05 and 0.035 nm for the WP21 Outcomes; the derived chord mesh is within 0.1 % of the drawn one's element count. Source: `tests/tier2/test_region_reference.py`.
- **[tested: tests/tier2/test_reproducibility.py::test_ver35_reproducing_into_the_store_that_holds_the_run_is_refused]** A reproduction must not be served from the cache: `Store.get_or_compute` would return the stored solution and show only that a dictionary lookup is deterministic, so the reproduction runs into a store that does not hold the run, and that the fresh store missed. Source: `tests/tier2/test_reproducibility.py`.
- **[tested: tests/tier2/test_reproducibility.py::test_ver35_an_input_whose_contents_moved_aborts_naming_it]** An input whose contents moved since the run is fatal by name, because the reproduction would be a different sum. A library version that moved is recorded, and a quantity comparison catches it if it moved a number; refusing on the version would fail for a reason no number connects to. Source: `tests/tier2/test_reproducibility.py`.
- **[tested: tests/tier2/test_reproducibility.py::test_ver35_a_run_reproduces_into_a_fresh_store]** A deterministic direct solve in one process is expected to reproduce every scalar exactly; the measured worst relative difference is logged so that a drift is visible inside tolerance. Source: `tests/tier2/test_reproducibility.py`.
- **[tested: tests/tier2/test_self_golden_round_trip.py::test_val01_self_golden_reproduces_its_own_solution]** The VAL-01 round trip is exactly zero, not 1e-14: `%.17g` round-trips `float64`, so a one-ulp difference is a defect in the transport format. Source: `tests/tier2/test_self_golden_round_trip.py`.
- **[tested: tests/tier2/test_self_golden_round_trip.py::test_val01_the_round_trip_preserves_the_masked_points_as_nan]** NGSolve returns `0` outside a `definedon` region, so a masked point must travel as `NaN` through the text format, `np.fromstring` and the archive, or it enters the norm as fabricated agreement. The text reader was verified against the 77 MB reference table to 4.7 × 10⁻¹². Source: `tests/tier2/test_self_golden_round_trip.py` (`test_val01_the_round_trip_preserves_the_masked_points_as_nan`).
- **[tested: tests/tier2/test_stabilised_mode.py::test_ver42_the_stabilised_mode_loses_an_order_and_no_more]** Stabilised mode, MMS: with `supg`, the concentration rate is 2.012 and 2.040 on `maxh` 0.4, 0.2 and 0.1 nm (none: 3 on the same meshes), 26 s (208 s before the manufactured sources shared subexpressions, `knowledge/06-numerics-fem/04-stabilisation.md#433-on-a-stable-element-pair-the-flow-terms-cost-an-order-and-20-the-time`). With `reference` the Na⁺ rate is 0.984 and the Cl⁻ rate 0.702 against `supg`'s 2.012 and 1.908 on the same meshes, with 31 Newton iterations against 5, and 126 s and 436 s against 7 s and 25 s. Source: `tests/tier2/test_stabilised_mode.py`.
- **[tested: tests/tier2/test_stabilised_mode.py::test_ver42_withholding_the_manufactured_source_switches_the_term_off]** Withholding the manufactured source `s̃ᵢ` from `R̃ᵢ` makes the error footprint `error(mode)/error(none) − 1` collapse. Intact it is 4.83 and 15.97 for Na⁺ and 2.99 and 15.77 for Cl⁻ at `maxh` 0.4 and 0.2 nm; withheld, 0.065, 0.666, 0.014 and 0.198, a ratio of 24 to 213. The gate's factor is a floor with five times that headroom. Source: `tests/tier2/test_stabilised_mode.py`.
- **[tested: tests/tier2/test_stabilised_mode.py::test_ver42_the_flow_pair_and_not_the_transport_term_sets_the_reference_rate]** The velocity error of `supg` (2.7617 × 10⁻⁴) is 0.2 % from `none`'s (2.7567 × 10⁻⁴), so the flow pair owns any velocity error an order above both: `reference` measures 3.4483 × 10⁻², a factor of 125. Source: `tests/tier2/test_stabilised_mode.py`.
- **[tested: tests/tier2/test_stabilised_mode.py::test_num17_plain_galerkin_trips_positivity_where_reference_converges]** On the coarse pore (313 elements, `max Pe_K` = 4.71), `none` reaches Na⁺ = −72.9 at `(r, z)` = (1.001, −4.376) nm and the NUM-17 gate stops it; `reference` converges in 126 Newton iterations over ten classical rungs, with the crosswind active at 125 of 1344 fluid samples for Na⁺ and 123 for Cl⁻ (peak `ν_K` 3.71 and 5.61). The fine pore (1491 elements, `max Pe_K` = 0.457) has no crosswind anywhere. Source: `tests/tier2/test_stabilised_mode.py`.
- **[tested: tests/tier2/test_stabilised_mode.py::test_num17_plain_galerkin_trips_positivity_where_reference_converges]** The surface charge of `−0.05 C/m²` is a benchmark choice. Below about `−0.10 C/m²` on that mesh both modes converge and the comparison measures nothing. Source: `tests/tier2/test_stabilised_mode.py`.
- **[tested: tests/tier2/test_stabilised_mode.py::test_ver42_the_two_modes_currents_converge_to_each_other_under_refinement]** The climbs refine `wall_h` and not `maxh`, because the stabilisation is a double-layer effect by three orders of magnitude (`knowledge/06-numerics-fem/04-stabilisation.md#42-the-ratio-supg-adds-is-pe_k2-exactly`); the reservoir spacing is held at 5 nm. Source: `tests/tier2/test_stabilised_mode.py`.
- **[tested: tests/tier2/test_stabilised_mode.py::test_ver42_the_two_modes_currents_converge_to_each_other_under_refinement]** The `reference`-minus-`none` current difference at 0.5 M, +50 mV and `−0.05 C/m²`, `maxh` 5 nm, falls with rates 1.44 and 1.89; the assertions are on the falling ratio and the measured rate, since the plan predicts the exponent and not the constant. Source: `tests/tier2/test_stabilised_mode.py` (`test_ver42_the_two_modes_currents_converge_to_each_other_under_refinement`).
- **[tested: tests/tier2/test_stabilised_mode.py::test_ver42_the_equal_order_pair_is_recorded_and_not_gated]** An equal-order P1/P1 pair in `reference`, against Taylor-Hood on 708 elements at `wall_h` 0.4 nm, 0.5 M, +50 mV: 6.86 × 10⁻² relative `r`-weighted L² velocity difference, 34 Newton iterations either way. Recorded, not gated. Source: `tests/tier2/test_stabilised_mode.py` (`test_ver42_the_equal_order_pair_is_recorded_and_not_gated`).
- **[tested: tests/tier2/test_stabilised_mode.py::test_ver42_the_flow_pair_and_not_the_transport_term_sets_the_reference_rate]** On the MMS mesh `max Pe_K` ≤ 0.084, so the crosswind viscosity is identically zero and `supg` and `reference` differ by the flow pair alone; the first interval of the mode-to-mode convergence is pre-asymptotic, so the gate's finest-rate floor is 1.5, not the asymptotic 2. Source: `tests/tier2/test_stabilised_mode.py`.
- **[tested: tests/tier2/test_stern_layer.py::test_ver31_the_stern_layer_raises_the_wall_potential_by_the_closed_form]** Gouy-Chapman-Stern: an ion-free layer of thickness `λ_S` carries no space charge, so `φ` is linear across it and `φ₀ = φ_d + σ_s λ_S/(ε₀ε_r)`, `σ_s = (8εRTc₀)^(1/2) sinh(ζ̃_d/2)`. At 0.1 M, `ζ̃_d` = 2, 298.15 K, `ε_r` = 78.15 and `λ_S` = 0.25 nm: `σ_s` = 0.0435342 C m⁻², `Δφ_S` = 15.7287 mV, and the wall potential rises from 51.3852 to 67.1139 mV, 30.6 %. A shell that is silently fluid is wrong by 24 %. Source: `tests/tier2/test_stern_layer.py`.
- **[tested: tests/tier2/test_stern_layer.py::test_ver31_the_shell_potential_drop_is_linear_in_the_thickness]** The Stern profile is linear to the nonlinear solve's own tolerance (measured 2.5 × 10⁻⁶); a shell holding ions would curve by percent. The shell agreement is 2.8 × 10⁻⁵ at `λ/4`, 7.2 × 10⁻⁷ at `λ/8` and 1.2 × 10⁻⁹ at `λ/16`. Source: `tests/tier2/test_stern_layer.py`.
- **[tested: tests/tier2/test_stokes_drag.py::test_ver19_a_uniform_far_field_measures_the_wall_correction_instead]** The Stokes far field imposed on `R` = 10 `a` is the exact solution, `u_r = −(3aU/4) z r/R³ + (3a³U/4) z r/R⁵`, `u_z = U − (3aU/4)(1/R + z²/R³) − (a³U/4)(1/R³ − 3z²/R⁵)`. A uniform stream there adds a wall correction of about `a/R`, measured as 28.5 % on this domain and near 22 % in the negative control, against the `1 + (9/4)(a/b)` of a concentric container. Source: `tests/tier2/test_stokes_drag.py`.
- **[tested: tests/tier2/test_stokes_drag.py::test_ver19_stokes_drag_converges_to_the_closed_form]** The domain route's error on the finest Stokes mesh is 2.0 × 10⁻⁵, so the 1 % gate has three orders of headroom. The classical model is required because `6πηaU` assumes constant viscosity. Source: `tests/tier2/test_stokes_drag.py`.
- **[tested: tests/tier2/test_stokes_drag.py::test_ver19_stokes_drag_converges_to_the_closed_form]** Sanity anchor: a 5 nm sphere at 0.1 m/s drags at about 4 pN. The test's `Ũ = 0.05` in `u₀ = εV_T²/(ηL₀)`, which is 0.0592 m/s on a 1 nm sphere, gives 0.43 pN. Source: `tests/tier2/test_stokes_drag.py`.
- **[tested: tests/tier2/test_sweep.py::test_ver37_a_warm_start_does_not_move_the_answer]** The smallest admissible mesh with wall corrections has 392 elements: `wall_h` 0.4 nm gives a negative minimum distance and is refused, and 0.35 nm gives `min d` = +9.5 × 10⁻⁶ nm. Source: `tests/tier2/test_sweep.py`.
- **[tested: tests/tier2/test_sweep.py::test_ver37_a_warm_start_does_not_move_the_answer]** Warm against cold Newton solves of one fixed point differ by the residual each left, which `numerics.nonlinear.rtol` (NUM-16) bounds; the test compares every reported scalar, not only the current. Source: `tests/tier2/test_sweep.py` (`test_ver37_a_warm_start_does_not_move_the_answer`).
- **[tested: tests/tier2/test_sweep.py::test_ver37_the_warm_path_costs_strictly_fewer_newton_iterations]** Warm 34.3 s against cold 26.7 s when measured alongside the rest of the suite; on an idle machine the same code gave 10.0 s against 21.6 s. The warm test therefore asserts Newton iterations, which are a property of the solves. Source: `tests/tier2/test_sweep.py` (`test_ver37_the_warm_path_costs_strictly_fewer_newton_iterations`).
- **[tested: tests/tier2/test_sweep.py::test_fr25_the_manifest_of_a_warm_member_records_how_it_was_reached]** A `canonical` manifest encodes each float as `{"__f__": <hex>}` for an exact digest, so a decoder is required beside it (§5.3.2) and a comparison against a recorded number has to use it. Source: `tests/tier2/test_sweep.py`.
- **[tested: tests/tier2/test_sweep.py::test_ver38_a_member_whose_parent_is_absent_falls_back_to_the_full_ladder]** The cold pass runs members in reverse index order into an empty store, so no parent has been solved when its child looks for it: the state of a job-array member on a machine that has seen nothing else (FR-24). Source: `tests/tier2/test_sweep.py` (`swept`).
- **[tested: tests/tier1/test_qoi.py::test_num26_round_off_currents_at_zero_bias_fail_the_relative_check]** A zero-bias member makes the route check inapplicable: `I_ψ` = 2.3 × 10⁻²⁷ A against `I_reaction` = 4.6 × 10⁻²⁵ A is a relative difference of 0.995 and aborts the member. Source: `tests/tier2/test_sweep_throughput.py`.
- **[tested: tests/tier2/test_sweep_throughput.py::test_ver39_the_scaling_curve_is_measured_and_recorded]** The throughput measurement uses 25 points in seven waves of widths 1, 3, 5, 5, 5, 4 and 2, over two axes; the one-worker point runs in-process so that `efficiency(1)` does not pay `spawn`. The development machine reports four cores, so N = 4 is the whole machine. Source: `tests/tier2/test_sweep_throughput.py`.
- **[tested: tests/tier2/test_sweep_generated_mesh.py::test_ver37_a_generated_mesh_sweep_warm_starts_from_its_parent]** A sweep over a generated mesh keys its parent from the stored stage-6 artefact. Until that was fixed, the member runner keyed the parent from the bare case, raised for every such sweep, and fell back to cold starts silently, so every member climbed the full ladder. Source: `tests/tier2/test_sweep_generated_mesh.py`.
- **[tested: tests/tier2/test_val05_2wcd.py::test_val05_2wcd_against_the_reference_polygon]** VAL-05's predicted values from the plan's prototype are `ε_G` = −8.08 %, `Δr_c` = −0.0205 nm and rms 0.158 nm; the isolevel steps are 2.0 to 5.3 percentage points against a conditioning rms of 0.01 nm. Source: `tests/tier2/test_val05_2wcd.py`.
- **[tested: tests/tier2/test_val05_2wcd.py::test_val05_2wcd_frozen_case_conductance]** The frozen-case conductance on the generated mesh is recorded beside `ε_G` as a bulk-resistor proxy: access resistance dilutes the difference. Source: `tests/tier2/test_val05_2wcd.py` (`test_val05_2wcd_frozen_case_conductance`).
- **[tested: tests/tier2/test_val06_2wcd.py::test_val06_2wcd_a_focused_grid_confirms_apbs_converges_at_first_order_or_better]** APBS's error is bounded by `|φ(h) − φ(2h)|` only at first order or better; the focused check is a 193³ grid at 0.05 nm whose faces come from APBS's own 0.1 nm solution, and the ratio `(φ(0.1) − φ(0.2))/(φ(0.05) − φ(0.1))` is `2^p`. Source: `tests/tier2/test_val06_2wcd.py` (`test_val06_2wcd_a_focused_grid_confirms_apbs_converges_at_first_order_or_better`).
- **[tested: tests/tier2/test_val06_2wcd.py::test_val06_2wcd_apbs_is_unchanged_by_a_cubic_angstrom_slip_at_its_coarse_grid]** The 0.2 nm APBS run tracks the 0.1 nm run within the budget; a cubic Ångström slip at its coarse grid would move it by a factor of 8. Source: `tests/tier2/test_val06_2wcd.py`.
- **[tested: tests/tier2/test_val06_ring.py::test_val06_ring_every_broken_construction_exceeds_half_the_tolerance]** At `h` = 0.1 nm = 1 Å, `e` per node and `e` per cubic Ångström are the same number, so the charge-density row of the ring's construction table is invisible on the fine grid and runs on the nested 0.2 nm grid, where the factor is 8. Source: `tests/tier2/test_val06_ring.py`.
- **[tested: tests/tier2/test_val06_ring.py::test_val06_the_ring_series_is_grounded_continuous_and_kirkwood_at_infinity]** The Gaussian ring's exterior is the point ring to `erfc` of the gap over `w`, about 10⁻³⁵ here. The series in `ρ` is `(b/a)^l` = 0.56^l inside, so 80 terms converge; the APBS box is 6.4 nm at 0.1 nm, which holds the ring 1.8 nm inside every face. Source: `tests/tier2/test_val06_ring.py`.
- **[tested: tests/tier2/test_val06_ring.py::test_val06_the_ring_series_is_grounded_continuous_and_kirkwood_at_infinity]** Ring coefficients per `l`: with `β'ₗ = k pₗ (b/a)^l/(ε₁a)` and `γ = (a/R)^(2l+1)`, grounding gives `B' = −γC'`, continuity `A' = (1 − γ)C' − β'`, and `C' = ε₁(2l+1)β'/(ε₁l(1 − γ) + ε₂(l(1 + γ) + 1))`. As `R → ∞`, `C_l` tends to Kirkwood's `k pₗ bˡ(2l+1)/(ε₁l + ε₂(l+1))`. Source: `tests/tier2/test_val06_ring.py`.
- **[tested: tests/tier2/test_charge_potential_axis.py::test_ver58_the_closed_form_vanishes_on_the_sphere]** The VER-58 oracle, one smeared atom in a uniform dielectric inside a grounded sphere of radius `R`: a unit smeared charge at `(r_i, z_i)` has `φ = (q/4πε)⟨erf(d/w)/d⟩_θ − (qR/a)/(4πε)⟨1/d′⟩_θ`, with `a = (r_i² + z_i²)^(1/2)`, the image of each ring point a charge `−qR/a` at `R²/a` along the same ray, and the azimuthal mean taken by the periodic trapezoid rule, spectrally accurate for these smooth periodic integrands. Source: `tests/tier2/ver58_sphere.py`.
- **[tested: tests/tier2/test_charge_potential_axis.py::test_ver58_deposited_potential_converges_at_the_potentials_own_rate_on_the_axis]** VER-58's on-axis lattice spacing `H` = 0.0025 nm is the one at which the disc-error rate reaches 2.99 (deposit and solve); at 0.005 nm the floor holds the rate to 2.80. Source: `tests/tier2/ver58_sphere.py`.
- **[tested: tests/tier1/test_stability_golden.py::test_ver62_fold_refuses_a_tolerance_above_the_ceiling]** The folding procedure for the number-stability golden (`tests/tier2/data/merge_number_stability.py`): a walk run with `NANOPNP_RECORD_STABILITY=<dir>` writes `<dir>/<walk>.json`, folded by `uv run tests/tier2/data/merge_number_stability.py <dir>`, with `--entry` for a record a CI leg printed. Folding widens that walk's mesh-moved tolerance for every unseen mesh and is refused past the ceiling; a known mesh's values change only with `--replace`, which a G10 re-pin uses in the commit that rules the change (section 8.2.7 G10).

[^pnp-benchmarks-3782c43]: `git show 3782c43:tests/tier2/test_pnp_benchmarks.py`, module docstring (before WP45).

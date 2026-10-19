---
type: Library Behaviour
title: 8.1 NGSolve traps found by implementing this — all silent
description: NGSolve traps found by implementing the model, all of them silent.
tags:
- numerics
- library-behaviour
sources:
- id: wp45-validation-strip
  resource: git:3872426:src/nanopnp/validation/attribution.py
  title: Validation prose strip from attribution.py and mms.py (commit 3872426)
- id: wp9-clya-aliasing
  resource: git:0ea0789:.knowledge/06-numerics-fem.md
  title: WP9 delivered ClyA charge-table aliasing and unstructured mesh quadrature
    study (commit 0ea0789)
- id: wp35-simd-dispatch
  resource: git:6c0a249:.knowledge/06-numerics-fem.md
  title: WP35 SIMD dispatch and number-stability mesh study (commits 6c0a249, 1a2e383)
- id: wp45-numerics-strip
  resource: git:7597814:src/nanopnp/numerics/gates.py
  title: Numerics prose strip recording 144,628-element FieldSampler timings (commit
    7597814)
- id: wp3-singular-system
  resource: git:0f8b57b:.knowledge/06-numerics-fem.md
  title: WP3 singular five-field system measurements and residual warning
- id: wp11-sweep-timings
  resource: git:5abcf42:.knowledge/06-numerics-fem.md
  title: WP11 toy-pore sweep timings and parallel-efficiency measurements
generated:
  by: claude-code/0.5.0-alpha.13
  at: '2026-10-14T00:00:00Z'
verified:
- by: process:arithmetic
  at: '2026-10-14T00:00:00Z'
- by: process:tests/tier1/test_attribution.py::test_val01_ladder_rungs_are_separate_warm_start_components
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_charge_deposit.py::test_ver01_ver02_correct_deposit_passes_every_gate
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_charge_fields.py::test_ver29_the_interpolant_is_zero_outside_the_grid_box
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_charge_fields.py::test_ver29_the_interpolant_reproduces_a_field_that_is_not_symmetric
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_charge_fields.py::test_ver29_the_quadrature_check_compares_two_genuinely_different_orders
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_charge_fields.py::test_ver29_the_truncation_gate_names_the_ring_value_and_its_location
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_charge_quadrature.py::test_qr03_every_fixed_charge_source_carries_the_charge_s_rule
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_charge_quadrature.py::test_qr03_the_gate_measures_the_charge_the_solve_assembles
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_dielectric_field.py::test_ver30_blend_takes_the_whole_solid_branch_not_one_constant
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_dielectric_field.py::test_ver30_water_off_the_fluid_is_ion_free_water
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_exclusion_shell.py::test_ver59_an_outer_surface_inside_the_bound_is_refused_naming_where
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_exclusion_shell.py::test_ver59_every_wall_node_lies_within_the_band_about_the_exact_offset
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_exclusion_shell.py::test_ver59_netgen_cuts_a_shell_wall_edge_into_equal_segments_of_at_most_1_1_h
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_exclusion_shell.py::test_ver59_the_shell_meshes_at_a_wall_target_its_whole_edges_failed
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_forces.py::TestAxialExtension::test_num28_extension_is_ez_on_the_body_and_zero_on_the_outer_boundary
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_gates.py::test_sampler_covers_the_p2_nodal_set
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_gates.py::test_sampler_locates_its_points_once
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_knowledge_arithmetic.py::test_ngsolve_physics_small_facts
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_linear_solver.py::test_num21_both_licensed_paths_are_available
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_mesh_adapter.py::test_if06_a_mesh_off_the_half_plane_is_refused
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_nernst_planck.py::test_phy23_the_permittivity_sensitivity_is_zero_when_the_correction_is_off
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_ngsolve_traps.py::test_ngsolve_trap_3_set_projection_and_dof_zeroing
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_ngsolve_traps.py::test_ngsolve_trap_4_integrate_order_replaces_default_five
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_ngsolve_traps.py::test_ngsolve_trap_6_reaction_flux_subtracts_load_form
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_ngsolve_traps.py::test_ngsolve_trap_gouy_chapman_reaction_flux_and_solver_facts
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_ngsolve_traps.py::test_ngsolve_trap_structured_mesh_cpu_features_sampler_and_gate_constants
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_ngsolve_traps.py::test_ngsolve_traps_10_12_13_14_and_19_forms_and_spaces
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_ngsolve_traps.py::test_ngsolve_traps_15_16_17_18_and_occ_extent
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_ngsolve_traps.py::test_ngsolve_traps_1_2_and_7_trial_function_p2_indicator_and_components
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_ngsolve_traps.py::test_ngsolve_traps_8_and_9_superlu_registration_and_singular_factorisation
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_qoi.py::test_num26_two_vanishing_currents_do_not_divide_by_zero
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_qoi_stage.py::test_fr23_the_generated_mesh_gives_the_same_band_to_mesh_round_off
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_qoi_stage.py::test_num28_the_extension_shell_scales_to_the_body_in_the_mesh
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_reaction_flux.py::test_num25_vector_indicator_selects_one_block_of_a_product_space
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_stabilisation.py::test_ver41_the_linearisation_is_finite_at_the_zero_wind_cold_state
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_stability_golden.py::test_ver62_a_recorded_mesh_holds_round_off
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_stability_golden.py::test_ver62_mesh_moved_tolerance_is_the_safety_factor_on_the_spread
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_sweep_plan.py::test_ver36_the_reference_sweep_parses_and_enumerates_the_section_8_3_grid
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_wall_distance.py::test_ver06_distance_matches_the_exact_field_near_the_wall
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_wall_distance.py::test_ver06_gradient_is_continuous_to_the_stated_tolerance
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_warm_start_descriptor.py::test_val01_a_warm_start_across_an_element_order_is_refused
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_warm_start_descriptor.py::test_ver37_a_neighbour_along_the_bias_axis_loads_and_records_the_difference
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_warm_start_descriptor.py::test_ver37_a_neighbour_along_the_salt_axis_loads_and_records_the_scales
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_axis_quadrature.py::test_ver07_order_two_returns_nan_on_an_axis_touching_mesh
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_axis_quadrature.py::test_ver07_singular_integral_is_correct_at_the_guaranteed_order
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_charge_conservation.py::test_ver29_a_coarsened_mesh_fails_the_quadrature_gate_not_the_conservation_one
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_charge_potential_axis.py::test_ver58_deposited_potential_converges_at_the_potentials_own_rate_on_the_axis
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_charge_potential_off_axis.py::test_ver58_deposited_potential_converges_at_the_potentials_own_rate_off_the_axis
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_coupled_gates.py::test_num17_gates_sample_the_fluid_only
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_electrostatic_benchmarks.py::test_ver12_grahame_surface_charge
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_electrostatic_benchmarks.py::test_ver13_axis_condition_is_natural_not_dirichlet
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_electrostatic_benchmarks.py::test_ver13_debye_huckel_in_a_cylinder
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_mms.py::test_ver18_second_order_fields_converge_at_third_order
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_mms.py::test_ver18_taylor_hood_pressure_converges_at_its_own_order
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_sweep.py::test_ver37_a_warm_start_does_not_move_the_answer
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_sweep.py::test_ver37_the_warm_path_costs_strictly_fewer_newton_iterations
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_sweep_generated_mesh.py::test_ver37_a_generated_mesh_sweep_warm_starts_from_its_parent
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier2/test_sweep_throughput.py::test_ver39_the_scaling_curve_is_measured_and_recorded
  at: '2026-10-16T00:00:00Z'
- by: process:tests/tier1/test_qoi.py::test_num26_round_off_currents_at_zero_bias_fail_the_relative_check
  at: '2026-10-18T00:00:00Z'
tested_with:
  ngsolve: 6.2.2606
  netgen-mesher: 6.2.2606
  numpy: 2.5.2
  scipy: 1.18.0
  sympy: 1.14.0
---

## 8.1 NGSolve traps found by implementing this — all silent

Nineteen ways this project's own code was wrong while raising nothing. All reproduced on NGSolve
6.2.2606. **[tested: tests/tier1/test_ngsolve_traps.py::test_ngsolve_traps_1_2_and_7_trial_function_p2_indicator_and_components]**

**1. A nonlinear form must be written in the trial function, not the grid function.**
`AssembleLinearization(gfu.vec)` differentiates the form with respect to the *trial* function and
substitutes the state vector. Written the intuitive way —

```python
a += (grad(gfu) * grad(v) + sinh(gfu) * v) * dx  # WRONG: Jacobian is identically zero
a += (grad(u) * grad(v) + sinh(u) * v) * dx  # right, with u = V.TrialFunction()
```

— the assembled Jacobian is **all zeros**, with no warning. Newton then fails inside the linear
solver with `UmfpackInverse: Numeric factorization failed` / "matrix is singular", pointing at the
solver rather than at the form. Cost of diagnosis: an hour.

**2. The higher-order basis is hierarchical, so its shape functions are not a partition of unity.**
Building a boundary indicator by setting the boundary DOFs of a P2 space to 1 gives a function whose
integral over that boundary is **11/12 of its length**, not its length. A reaction flux normalised
on the assumption gives a clean, stable, mesh-independent **8.33 % error** — which reads as a
modelling difference, not a bug. Build the indicator by interpolation instead:
`psi.Set(CF(1.0), definedon=mesh.Boundaries(name))`.

**3. `GridFunction.Set` projects element-wise, so Dirichlet data comes back approximate.**
Interpolating `-sqrt(t)*log(w)` for the wall-distance field left `d ≈ -4e-4 nm` *on* the wall
instead of 0. Small, but `f^w_D(0) = 0.0601` is 6 % of its bulk value, so a slightly negative `d`
shifts the near-wall diffusivity by percent. Zero the constrained DOFs explicitly afterwards.
**The sign of that round-off is platform-dependent**, so no test may assert it: projecting `x` onto
P2 on the slab leaves −3.5e−16 at the wall on Linux and a positive value of the same size on macOS
and Windows, which silently turned a strict `c > 0` gate test green on one platform and red on the
other two. Sample the coefficient function itself when a test needs an exact boundary value.
**[tested: tests/tier1/test_ngsolve_traps.py::test_ngsolve_trap_3_set_projection_and_dof_zeroing]**

**4. `Integrate`'s `order=` replaces NGSolve's default of 5, it does not raise it.**
`ngsolve.Integrate(cf, mesh)` uses order 5 when none is given. A helper that computes an order and
passes it explicitly therefore *lowers* the accuracy of every integral that did not need raising:
integrating `x^4` over the unit square at order 2 underintegrates the exact value 0.2, while
the bare call returns 0.2 to machine precision. Any wrapper around `Integrate` must floor its
computed order at 5. **[tested: tests/tier1/test_ngsolve_traps.py::test_ngsolve_trap_4_integrate_order_replaces_default_five]**

**5. `bonus_intorder` is added to NGSolve's own estimate for the integrand, which is not knowable.**
So a minimum integration order cannot be guaranteed by passing the *deficit* between that minimum
and an assumed base — the assumption is unverifiable, and for a quotient NGSolve's estimate can be
as low as 2. A guarantee of order `n` has to come from a bonus of `n` on its own. Measured orders
for the axis trap: order 2 gives NaN on `1/r`, orders 3, 4, 5 and 8 do not. **[tested: tests/tier2/test_axis_quadrature.py::test_ver07_order_two_returns_nan_on_an_axis_touching_mesh]** **[tested: tests/tier2/test_axis_quadrature.py::test_ver07_singular_integral_is_correct_at_the_guaranteed_order]**

**6. The reaction flux is the residual `a(u,v) - f(v)`, so the load form must be subtracted.**
`BilinearForm.Apply` gives `a(u, ·)` alone. Omitting `f` on a problem with a source biases the flux
by `int f psi` over the boundary-adjacent elements: for `-lap(phi) = 1` on the unit square with two
constrained sides, the closed boundary integral of `dphi/dn` came back as −0.913 instead of the
exact −1. Poisson-Boltzmann hides this, having a zero right-hand side. The identity also holds only
where the solve *constrained* the boundary; asked for a free one, the residual returns a plausible
non-zero number instead of the flux. **[tested: tests/tier1/test_ngsolve_traps.py::test_ngsolve_trap_6_reaction_flux_subtracts_load_form]**

**7. `FESpace.components` raises on a non-compound space rather than being absent.**
`getattr(space, "components", None)` does **not** protect against it: the default applies only when
the attribute is missing, not when the property itself throws. On an `H1` space the access raises
`NgException: components only available for ProductSpace`, so any code that branches on "is this a
compound space" with `getattr` breaks the moment it is handed a single field. Use `try/except`.

**8. NGSolve registers its own `superlu` inverse type, so `mat.Inverse(inverse="superlu")`
silently succeeds.** `ngsolve/directsolvers.py` calls `ngsolve.la.RegisterInverseType("superlu",
SuperLU)` at import, wrapping `scipy.sparse.linalg.factorized`. A project that also ships its own
SuperLU path — because it wants row equilibration, or a specific error message — therefore ends up
with **two implementations behind one name**, and which one a call site gets depends on whether it
routes through the project helper or through `mat.Inverse`. Nothing raises; the answers agree to
1e-14 on a well-scaled system, so the divergence only shows on the badly scaled one the
equilibration was added for. Resolve a solver name in exactly one function. **[tested: tests/tier1/test_ngsolve_traps.py::test_ngsolve_traps_8_and_9_superlu_registration_and_singular_factorisation]**

**9. A direct solver factorises a singular system without complaint.** A five-field block system
assembled with no essential conditions anywhere — pure-Neumann Poisson has the constant null mode,
and the Stokes block has nothing fixing the pressure — is factorised happily by both UMFPACK and
scipy SuperLU. The "solutions" come back finite: `‖x‖_inf` of 2e16 from SuperLU and 8e33 from
UMFPACK on the same 1.5e4-dof system, with residuals of 5e3 and 6e20. So `np.isfinite(x).all()` is
**not** evidence that a factorisation is usable; assert on the residual `‖Ax − b‖`, which is 1e-13
once the reservoir caps are constrained. These are WP3's recorded five-field measurements.
**[verified][^wp3-singular-system]** The current scalar-Poisson reproduction separately checks
that a finite singular solution has a non-small residual and that constraining the system restores
a small residual; it does not reproduce those five-field magnitudes.
**[tested: tests/tier1/test_ngsolve_traps.py::test_ngsolve_traps_8_and_9_superlu_registration_and_singular_factorisation]**

**10. `GridFunction.Set(cf, definedon=region)` zeroes every degree of freedom outside `region`.**
It is an interpolation onto the whole function, not a write into part of it. So the natural order —
write an initial guess over the domain, then apply the essential boundary data — silently discards
the initial guess, and a coupled solve starts from `c_i = 0`, which the NUM-17 positivity gate then
(correctly) aborts on before Newton takes a step. The same call on a warm start discards the state
being warm-started from, which is worse, because that one converges to something plausible.
Interpolate onto a scratch function and copy only the region's degrees of freedom:
`gf.vec.data = Projector(dofs, False) * gf.vec + Projector(dofs, True) * scratch.vec`. **[tested: tests/tier1/test_ngsolve_traps.py::test_ngsolve_traps_10_12_13_14_and_19_forms_and_spaces]**

**11. A point on a facet shared by two elements may be located in either of them, so a field
defined on a subdomain reads zero there.** The NUM-17 gates sample the P2 nodal set; a node on the
fluid/membrane interface belongs to elements on both sides, and `mesh(r, z)` may resolve it into
the membrane, where `c_i` is not defined and evaluates to 0 — not positive. Filtering the *elements*
by material is not enough, because the node still has the interface's coordinates. Pulling each
element's sample points a small fraction towards that element's own centroid fixes it; the fraction
has to be big enough to beat the location tolerance. Measured on the analytic pore at `maxh` 6 nm
and 2 nm: 1e-6 still resolves into the solid, 1e-5 is the first that does not, and 1e-4 leaves an
order of margin while moving a P2 value by 1e-4 of its variation across the element. **[tested: tests/tier1/test_gates.py::test_sampler_covers_the_p2_nodal_set]** **[tested: tests/tier2/test_coupled_gates.py::test_num17_gates_sample_the_fluid_only]**

**12. `GridFunction.Set` on a compound space raises rather than dispatching to the components.**
`gf.Set(CF(1.0), definedon=mesh.Boundaries(name))` on a product space raises `CompoundFESpace does
not have an evaluator for BND!`. Build the boundary indicator of NUM-25 on one component —
`gf.components[i].Set(...)` — which is what you want anyway: the inner product with the residual
then picks out one equation's flux rather than the sum over all of them. **[tested: tests/tier1/test_ngsolve_traps.py::test_ngsolve_traps_10_12_13_14_and_19_forms_and_spaces]** **[tested: tests/tier1/test_reaction_flux.py::test_num25_vector_indicator_selects_one_block_of_a_product_space]**

**13. `ngsolve.grad(gridfunction)` evaluated on a boundary region returns the *surface* gradient of
the trace, silently dropping the normal derivative.** The surface route of NUM-28 needs the volume
gradient lifted to the body's boundary, and `grad(u)` there gives the tangential part only — a
traction missing its normal component, which on a no-slip surface is most of it, with no error and
no NaN. The cure is `ngs.BoundaryFromVolumeCF(grad(u))`, which lifts the volume expression rather
than differentiating the trace. Note also that **`ngs.BoundaryCF` is a method of the mesh**, not a
module function: `mesh.BoundaryCF({...})`. **[tested: tests/tier1/test_ngsolve_traps.py::test_ngsolve_traps_10_12_13_14_and_19_forms_and_spaces]**

**14. `ngs.LinearForm(term)` raises; a linear form must be built on a space and then added to.**
`ngs.LinearForm(charge_source(rho, v, AXISYMMETRIC))` fails with `NgException: Linearform must have
TestFunction`, which reads as a problem with the term. It is not — the constructor takes the *space*:
`f = ngs.LinearForm(space); f += term; f.Assemble()`. **[tested: tests/tier1/test_ngsolve_traps.py::test_ngsolve_traps_10_12_13_14_and_19_forms_and_spaces]**

**15. Netgen's OCC kernel does not put axis vertices at exactly `r = 0`.** A revolved geometry comes
back with vertices at `r = -1.5e-15` nm and `r = +7e-16` nm — round-off in the rotation, not a mesh
that crosses the axis. Two things break on it. The CON-04 gate asks for `r >= 0` *exactly*, and has
to go on asking exactly, because the failure it exists to catch is a mesh mirrored about the axis,
which is a sign error; a tolerance wide enough to pass round-off is a tolerance that has to justify
its width. And a content hash over the coordinate bytes makes two runs of the same mesher two
different meshes and two cache entries. Snap `|r| < 1e-9` nm to zero on the way into the in-memory
mesh, for every route in, the meshers' own included. **[tested: tests/tier1/test_ngsolve_traps.py::test_ngsolve_traps_15_16_17_18_and_occ_extent]** **[tested: tests/tier1/test_mesh_adapter.py::test_if06_a_mesh_off_the_half_plane_is_refused]**

**16. `VoxelCoefficient`'s value array is indexed `[axis-2, axis-1]`.** For a 2D grid over
`(r, z)` the array must be `values[i_z, i_r]`. Passing the transpose raises nothing: a field built
to be `10r + z` returned 1.0 at `(r=1, z=0)` where 10.0 was intended, and **agreed exactly** at the
symmetric sample `(0.5, 0.5)` — so a test that samples on the diagonal passes on a transposed field.
Assert against a field that is not symmetric in its arguments, at an off-diagonal point. **[tested: tests/tier1/test_charge_fields.py::test_ver29_the_interpolant_reproduces_a_field_that_is_not_symmetric]** **[tested: tests/tier1/test_ngsolve_traps.py::test_ngsolve_traps_15_16_17_18_and_occ_extent]**

**17. `VoxelCoefficient` continues by the clamped edge value outside its box, not by zero** — as its
docstring says, and as measured beyond the box in `r` and in `z`. For a charge grid this is not a
detail: the reference mesh is a half-disc of radius 250 nm (98,175 nm²) against a grid footprint of
~93 nm², so a residual edge value is amplified over an area **1056 times** the grid's own. Pad the
value array with a ring of zeros and extend the box by one spacing each way; the field is then zero
outside *and* continuous, where an `IfPos` window would be zero and discontinuous. Gate what the
padding threw away by refusing a grid whose boundary ring is not negligible against its interior.
**[tested: tests/tier1/test_charge_fields.py::test_ver29_the_interpolant_is_zero_outside_the_grid_box]** **[tested: tests/tier1/test_charge_fields.py::test_ver29_the_truncation_gate_names_the_ring_value_and_its_location]**

**18. `extra_order=3` on a singular form is not a refinement.** `Measures.bonus_order(singular=True)`
takes `max(extra, 3)` — NUM-07's floor for a form carrying `1/r` — so asking for three extra orders
on such a form evaluates at *exactly* the assembly order and returns a bit-identical number. A
quadrature-agreement gate written that way compares a value with itself and passes unconditionally.
Measured on the delivered ClyA charge table: `extra=0` and `extra=3` both give -71.289538 e, while
`extra=6` gives -71.957178 e. Ask for enough extra orders to clear the floor. **[tested: tests/tier1/test_charge_fields.py::test_ver29_the_quadrature_check_compares_two_genuinely_different_orders]** **[tested: tests/tier1/test_ngsolve_traps.py::test_ngsolve_traps_15_16_17_18_and_occ_extent]**[^wp9-clya-aliasing]

**19. `sqrt` of an exactly-zero vector puts `NaN` in the Jacobian, but not in the residual.** A
stabilisation parameter built from the lagged grid function is constant with respect to the trial
functions, so its derivative is structurally zero — but `AssembleLinearization` evaluates the chain
rule *numerically*, and never folds that zero away:

```python
g = GridFunction(fes)
g.vec[:] = 0.0  # a lagged field, identically zero
a += sqrt(grad(g) * grad(g)) * u * v * dx
a.Assemble()  # clean: 0 NaN
a.AssembleLinearization(x.vec)  # 34 of 34 entries NaN
```

`d/du √(g·g) = (g · ∂g/∂u)/√(g·g)` is `0/0` at `g = 0`, and `NaN` survives the multiplication by the
structural zero that follows. The failure surfaces as
`UmfpackInverse: Numeric factorization failed` inside Newton with nothing naming the form — the same
symptom as trap 1, from the opposite cause. `Apply` is unaffected, so a residual-based test of the
same state passes.

Two things make this expensive rather than merely annoying. `b̃_i = z_i μ̃_i ∇φ̃ + D̃_i β̃_i − Pe ũ` is
**exactly** zero at every rung of the NUM-18 ladder below stage 4 (zero bias, zero charge, no flow),
so it is the ordinary path; and the scalar sibling `|s|` written as `IfPos(s, s, −s)` is immune,
because `IfPos` differentiates branchwise with no division, which is why the scalar case in
`physics/stabilisation.py` never showed it.

Fix: floor inside the root, `√(v·v + ε²)` with `ε` the same floor already guarding the reciprocal.
At `ε = 1e-30` the perturbation to a magnitude of order 1 is `5e-61`, below the last bit of a double,
and the derivative becomes `0/1e-30 = 0` exactly. Verify on the **assembled Jacobian entries**: a
residual norm reports zero, not `NaN`. **[tested: tests/tier1/test_stabilisation.py::test_ver41_the_linearisation_is_finite_at_the_zero_wind_cold_state]** **[tested: tests/tier1/test_ngsolve_traps.py::test_ngsolve_traps_10_12_13_14_and_19_forms_and_spaces]**

**Trap: a coefficient built from `definedon` fields reads their zero everywhere else.** The
concentrations live on the fluid, so off it they evaluate to 0, `average_concentration` clamps
that to 1e-6 M, and anything derived from them returns its value at the clamp floor with no
diagnostic. Measured on `CoupledModel.permittivity` at 3 M with the permittivity correction on:
ε_r = **78.1499885** in the `exclusion` shell against **51.09** in the electrolyte beside it. That
number was near the right one only by accident: under author ruling 13 `⟨c⟩` has no meaning off the
fluid, and water there is ion-free, `ε_r,f⁰` = 78.15, which the code now sets as such. The same trap
made the fluid side of a χ blend discard χ, because its solid branch defaulted to the fluid value.
Any expression evaluated on a material its inputs are not defined on has to be given a value there
deliberately. (Codebase review of 2026-09-28, CR-2.) **[tested: tests/tier1/test_dielectric_field.py::test_ver30_water_off_the_fluid_is_ion_free_water]** **[tested: tests/tier1/test_dielectric_field.py::test_ver30_blend_takes_the_whole_solid_branch_not_one_constant]**

**20. An explicit integration rule in `dx` agrees with `Integrate(·, order=...)` to round-off.**
`dx(intrules={ngs.TRIG: ngs.IntegrationRule(ngs.TRIG, n), ngs.QUAD: ngs.IntegrationRule(ngs.QUAD, n)})`
in a `LinearForm` (and in a residual `BilinearForm` applied to zero) gives the same number as
`ngsolve.Integrate(·, mesh, order=n)` to 4 × 10⁻¹⁶. Without the explicit rule, NGSolve assembles
`fixed_charge · v · r · dx` at its own estimate, order 3, while `Integrate` floors at 5; on a
resolved 0.5 nm alternating field, order 3 against 8 was 1.2 × 10⁻² off, leaving the solve with
a charge 12 times QR-03's conservation budget while the order-8 gate passed at 2 × 10⁻⁵.
Sharing one rule through `Measures.volume(..., rule_order=n)` and `Measures.integrate(..., rule_order=n)`
makes the operator and its gate one rule exactly. **[tested: tests/tier1/test_charge_quadrature.py::test_qr03_the_gate_measures_the_charge_the_solve_assembles]** **[tested: tests/tier1/test_charge_quadrature.py::test_qr03_every_fixed_charge_source_carries_the_charge_s_rule]**

### 8.1.1 Mesh-integral error on a sub-element-scale field converges in neither `h` nor order

The finding that costs the most to rediscover, from ingesting the reference model's own 0.005 nm
`rhoq_pore` table (`knowledge/04-clya-geometry-and-charge/03-fixed-charge-pipeline.md#32-the-references-125-is-the-consumers-and-it-is-aliasing` carries the full tables). Integrating a
`VoxelCoefficient` over the deployed mesh is *not* a discretisation error that refinement reduces:
the table's radial structure alternates sign 49 times along its densest `z`, with extrema a median
0.035 nm apart, an order below the finest element the reference mesh places. Pointwise quadrature of
the bilinear interpolant is then **aliased**, and

- refining `h` from 44,316 to **3,463,372** elements moved the error from +9.9e-3 to **-1.1e-2** —
  worse, and non-monotone in between (669 s to mesh, 80 s to integrate);
- raising the integration order from 8 to 37 on the fixed mesh oscillated through +5.9e-4, -3.0e-3,
  +2.8e-3, -7.4e-4, +4.8e-4 without settling.

Two consequences. First, a conservation gate on such a field is a *resolution* gate: report the
order/order+N quadrature agreement beside the conservation figure, and let it be the one that fires,
so the diagnostic says "the mesh under-resolves the supplied field" rather than "charge was lost".
Second, the fix is on the producer side — deposit onto the finite-element space and rescale to
`Q_net`, which conserves by construction — and no amount of consumer-side effort substitutes for it.
**[tested: tests/tier2/test_charge_conservation.py::test_ver29_a_coarsened_mesh_fails_the_quadrature_gate_not_the_conservation_one]** **[tested: tests/tier1/test_charge_deposit.py::test_ver01_ver02_correct_deposit_passes_every_gate]**[^wp9-clya-aliasing]

### 8.1.3 An OCC-generated extent is one ulp off the number the geometry was given **[tested: tests/tier1/test_qoi_stage.py::test_fr23_the_generated_mesh_gives_the_same_band_to_mesh_round_off]** **[tested: tests/tier1/test_ngsolve_traps.py::test_ngsolve_traps_15_16_17_18_and_occ_extent]** {#813-an-occ-generated-extent-is-one-ulp-off-the-number-the-geometry-was-given}

`CylindricalPoreGeometry(membrane_thickness_nm=6.0, ...)` produces a mesh whose `membrane` vertices
span `z ∈ [−3.0, 3.000000000000001]`: the upper face is one unit in the last place high, and
identically so at `maxh` 4.0 and 2.0, so it is the OCC revolve's round-off and not a meshing
artefact. Anything derived from a material's own extent — the NUM-24 indicator band read off the
mesh rather than off the geometry object is the case that found it — therefore agrees with the
geometry formula to about 4 × 10⁻¹⁶ nm and not exactly. Assert such an identity on a hand-built
`MeshData` with exact coordinates, and assert the meshed one to a tolerance far below any length in
the problem; an `==` against a meshed extent is a test that will fail on some other platform's OCC.

### 8.1.4 A GEOS round-join offset, then step 6, is not "within a chord's sagitta" of the offset **[tested: tests/tier1/test_exclusion_shell.py::test_ver59_every_wall_node_lies_within_the_band_about_the_exact_offset]** **[tested: tests/tier1/test_exclusion_shell.py::test_ver59_an_outer_surface_inside_the_bound_is_refused_naming_where]** {#814-a-geos-round-join-offset-then-step-6-is-not-within-a-chords-sagitta-of-the-offset}

Found building stage 5's ion-exclusion shell (WP30). `Polygon(P).buffer(a, quad_segs=8)` places
every vertex of its round joins exactly on the offset circle: the vertex distance to `P` equals `a`
to 1e-12 at `a` = 0.12, 0.25, 0.5 and 1 nm on the VER-59 parallelogram. Its straight offset edges lie
at exactly `a`. So the raw offset lies inside the exact one only by its chords' sagittas,
`a(1 − cos(π/32))` = 0.0048a. Each arc chord is `aπ/16` long: 0.0244 nm at `a` = 0.12 and 0.0491
at 0.25, just under `h_c` = 0.05.

§5.2.1's step 6 drops the cheapest endpoint of the shortest edge until no edge is shorter than
`h_c`. On such a ring it merges **runs** of chords, not pairs: a sub-`h_c` chord left between two
merged ones merges into one of them. The longest chord it leaves reaches about `3h_c`. Its sagitta
exceeds the `h_c²/a` that a chord of `2h_c` would give, and the shell's thickness bound,
`max(h_c²/a, a/100)`, was argued on that `2h_c`. The closing by `2h_c` re-discretises the joins,
even on a convex body, so the chord lengths are not the buffer's own. The ratio of the deepest edge
to the bound, with offset, closing and step 6 alone:

| `a` (nm) | 0.11 | 0.12 | 0.2 | 0.25 | 0.5 | 1.0 |
|---|---|---|---|---|---|---|
| Rectangle | 0.55 | 0.77 | 0.79 | **1.06** | 0.67 | 0.58 |
| Keyhole (a necked pocket) | 0.55 | 0.66 | 0.42 | 0.62 | **1.09** | 0.58 |
| Parallelogram | 0.85 | 0.92 | 0.85 | 0.94 | 0.72 | 0.62 |

Choosing the segment count per `a`, so that the joins' chords are at least `h_c`, fixes small `a`
and still fails the keyhole at 0.5 nm. What works is to **resample the ring at uniform arc length
before step 6**, at `s = L/⌊L/(F h_c)⌋`:

- `F` = 1.0 leaves chords under `h_c` on the curves, step 6 chains again, and the ratio reaches
  1.15.
- `F` = 1.05 and 1.5 leave nothing to merge, and the ratio is at most 0.53 and 0.76.
- `F` = 2 reaches 1.02 at `a` = 0.5 nm, from the chord's own sagitta.

The construction is `F` = 1.05, because netgen leaves an edge of 1.5 times its size target as one
segment. At `F` = 1.5 the Stern tube's mean wall segment was 1.49 times the 0.05 nm target, and
stage 6's wall-size gate refused it. With `F` = 1.05 every chord is above `h_c`, and the surface is
at most `0.0048a + s²/(8a)` inside the offset, with `s < 1.15 h_c`, which is 0.62 of the bound at
worst [tested: tests/tier1/test_exclusion_shell.py::test_ver59_every_wall_node_lies_within_the_band_about_the_exact_offset]. Stage 5 also gates the bound on every edge: the least distance of a segment to a
polygon is the least of four endpoint distances (`chord_clearances`).

The closing moves the surface outward where it fills a groove. On 2WCD at `a` = 0.25 nm, 8 % of the
`wall` nodes lie beyond `a + 10⁻⁶` nm (`knowledge/04-clya-geometry-and-charge/02-model-geometry-and-conventions.md#22-the-ion-exclusion-shell-and-the-derived-on-2wcd-measured`).

**Netgen keeps every ring vertex and rounds each edge's segment count, so a shell's wall fails the
gate in bands of wall target** **[tested: tests/tier1/test_exclusion_shell.py::test_ver59_netgen_cuts_a_shell_wall_edge_into_equal_segments_of_at_most_1_1_h]** **[tested: tests/tier1/test_exclusion_shell.py::test_ver59_the_shell_meshes_at_a_wall_target_its_whole_edges_failed]** (WP30 review, 2 October 2026, netgen 6.2.2606). Given
`maxh = h` on a straight edge of length `L` whose ends it must keep, netgen cuts it into about
`⌊L/h + 0.4⌋` segments: one up to `L/h` ≈ 1.5, two from about 1.6, three from about 2.6. The ring's
edges are 1.05–1.15 `h_c` ≈ 0.0525 nm, so the mean segment is up to 1.6 × the target wherever the
target is a little under `L` or under `L/2`, and the wall-size gate's 1.15 refuses it. Measured at
`a` = 0.25 nm, `size_scale` 1, mean wall segment over the target, refusals in bold:

| Target (nm) | 0.05 | 0.045 | 0.04 | 0.035 | 0.03 | 0.0272 | 0.0225 |
|---|---|---|---|---|---|---|---|
| Parallelogram, ring edges whole | 1.030 | 1.144 | **1.287** | **1.455** | 0.873 | 0.962 | **1.164** |
| 2WCD, ring edges whole | 1.045 | **1.163** | **1.306** | **1.457** | 0.884 | 0.964 | **1.165** |
| 2WCD, cut into `⌈L/(1.1h)⌉` | 1.045 | 0.583 | 0.655 | 0.749 | 0.874 | 0.962 | 0.776 |
| 2WCD, Gmsh 4.15.2, unaided | 0.524 | 0.583 | 0.655 | 0.749 | 0.873 | 0.963 | 0.776 |

`auto` reaches the refused targets between about 1.5 and 1.9 M and at 3 M (0.0350 nm); 5 M
(0.0272 nm) passes by the rounding alone. A shell-free profile does not see this: step 6 leaves
its edges long (2WCD's median 0.22 nm, the ClyA reference table's longer), and plain 2WCD and the
reference passed at every target above with means of 1.04–1.09. Stage 6 therefore sets each shell
`wall` edge's `maxh` to `L/n`, `n = ⌈L/(1.1h)⌉`, keeping `h` where `n` = 1
(`mesh/sizing.py` `EXCLUSION_WALL_DIVISION`). The count is then `n` whatever the rounding; netgen
added one node once, where the membrane cuts a 0.01 nm edge off the ring. The 0.05 nm default
leaves every 2WCD ring edge whole, so that mesh is the one measured before (51,599 triangles). At
3 M, 2WCD's shelled mesh has 68,477 triangles, min SICN 0.695, wall mean 0.748 and max 0.941.
Gmsh cuts each edge into `⌈L/h⌉` unaided, so it gets no rule.

Two other routes were measured and set aside. One periodic OCC spline through the ring
(`SplineInterpolation`) leaves netgen no forced vertices and passed every target at means of
1.04–1.10, with as many elements as a plain profile. But it bulges past the offset between
vertices (2WCD wall nodes to 0.2908 nm against the polyline's 0.2818; the parallelogram's 0.2 pm
past `a + 10⁻⁶`), and the Gmsh backend's `geo` kernel cannot reproduce OCC's curve. OCC's own
offset (`WorkPlane.Offset`) gives the exact dilation, lines and arcs at exactly `a`, in 0.8 s on
2WCD. But netgen's binding casts the result to one wire, and raises
`Standard_TypeMismatch: TopoDS::Wire` whenever the dilation encloses a pocket, even at a single
offset by `a`, which VER-59's necked pocket requires.

### 8.1.2 An unstructured netgen mesh is not a portable measurement

A corollary of §8.1.1 that only shows up on a CI matrix. Because the aliased quadrature error is a
function of where the vertices happen to fall, *any* assertion on its magnitude inherits the
mesher's own arbitrariness. Netgen's unstructured triangulation of the same rectangle at the same
`maxh = 0.2 nm` gave, for the same field, an order/order+3 agreement of **2.3e-4 on Linux, 7.8e-5 on
Windows and 2.2e-5 on macOS** — a factor of ten, straddling a 1e-4 threshold three different ways
**[tested: tests/tier1/test_ngsolve_traps.py::test_ngsolve_trap_structured_mesh_cpu_features_sampler_and_gate_constants]**[^wp9-clya-aliasing]. Nothing about the physics differs; the meshes do.

Coarsening is not the repair, because the quantity is non-monotone in `h` (§8.1.1) — it re-rolls the
dice. `ngsolve.meshes.MakeStructured2DMesh` places every vertex arithmetically from `(nx, ny)` and a
mapping, so the mesh, and therefore the number, is identical on every platform. On the same box and
field it reads 3.7e-4 at `(27, 70)`, 7.4e-5 at `(23, 59)` and 5.0e-6 at `(25, 65)` — one coarser and
one finer than the first, both *below* what it exceeds, which is the non-monotonicity again and the
reason the resolution has to be picked by measurement.

The rule: **a test that asserts a quadrature-error magnitude must run on a structured mesh.** A test
that asserts a converged physical quantity may use whatever mesh the pipeline deploys, because that
number is mesh-independent by construction and an unstructured mesh is then the more honest one.

### 8.1.5 Within one build, a deployed walk's quantities repeat bit for bit **[tested: tests/tier1/test_stability_golden.py::test_ver62_a_recorded_mesh_holds_round_off]** **[verified]**[^wp35-simd-dispatch] {#815-within-one-build-a-deployed-walks-quantities-repeat-bit-for-bit}

The converse of §8.1.2, measured for VER-62 (WP35). On one Linux x86-64 build (Python 3.12,
`uv.lock` at `v0.4.0`, `OMP_NUM_THREADS=OPENBLAS_NUM_THREADS=MKL_NUM_THREADS=1`), seven gated walks
were run twice: once under `pytest -n auto --dist loadfile`, once serially. Examples 01, 02 (both
cases), 03 (four sweep members, warm-started across waves on two workers) and 07, and the charged
2WCD walk with and without the ion-exclusion shell. Every current, conductance, transport number,
EOF rate and the deposited `q_mesh_e` agreed **exactly**, relative drift 0, and so did each deployed
mesh's content hash. Process placement, worker count and the sweep's worker assignment do not
enter the numbers. Across platforms the mesh itself differs (§8.1.2, `knowledge/07-software-stack/05-gui-and-packaging.md`), which is why the
golden is keyed per platform and asserts the mesh hash before any number.

**Within one `<platform>-<machine>` key, NumPy's SIMD dispatch moves a PDB-derived mesh**
**[verified]**[^wp35-simd-dispatch] (WP35 review, 5 October 2026). WP35's first CI run on `ubuntu-latest` produced a
different deployed mesh for the 2WCD shell walk (`289b175e…`) from the one recorded on an AVX-512
build machine (`47b8e51f…`), both `linux-x86_64`, same `uv.lock`, threads pinned to 1. Locally,
`NPY_DISABLE_CPU_FEATURES="X86_V4 AVX512_ICL AVX512_SPR"` reproduces CI's hash exactly, while
`OPENBLAS_CORETYPE=Haswell` alone leaves the recorded one: the cause is NumPy's runtime-dispatched
kernels (last-bit differences upstream of meshing, in the structure → density → contour stages),
not BLAS. On the other mesh the shell walk's current moves by 2.6 × 10⁻⁵ relative (`Cl⁻` 5.2 × 10⁻⁵,
`Na⁺` 4.5 × 10⁻⁶) and `q_mesh_e` by 1.6 × 10⁻¹⁴. The profile-driven examples 01–03 kept their meshes
and held to ≤ 1.9 × 10⁻¹³. So equal mesh hashes and zero drift hold on one machine's dispatch level,
not across every machine sharing a platform key.

**The split is AVX-512 against everything below it, and a moved mesh is not always a moved number**
**[tested: tests/tier1/test_stability_golden.py::test_ver62_mesh_moved_tolerance_is_the_safety_factor_on_the_spread]** **[verified]**[^wp35-simd-dispatch] (WP35 amendment, 5 October 2026; NumPy 2.5.2, Python 3.12, threads pinned to 1). The
seven walks were recorded on an AVX2 machine at its native `X86_V3` and again with
`NPY_DISABLE_CPU_FEATURES` capping it at the `X86_V2` baseline. All seven deploy the same mesh at both
levels, and every value agrees **bit for bit**. Against the `X86_V4` (AVX-512) recording:

| walk | mesh | largest relative drift |
|---|---|---|
| examples 01, 02 (both), 03 | same | 1.4 × 10⁻¹³ (example 01's EOF); ≤ 8 × 10⁻¹⁶ otherwise |
| example 07 | moved | 9.1 × 10⁻¹⁵ |
| 2WCD charged | moved | 2.4 × 10⁻¹⁴ (`q_mesh_e`) |
| 2WCD with the exclusion shell | moved | 5.2 × 10⁻⁵ (`Cl⁻` current) |

Three lessons for any golden. A content hash moves on a last-bit coordinate difference that changes
no number, so it is the wrong thing to assert. The same mesh across dispatch levels agrees to round-off,
not bit for bit, because the solve-side NumPy kernels dispatch too. And only the shell walk, whose
offset surface adds a geometric construction downstream of the contour, moves materially. VER-62 now
uses the hash only to choose its tolerance: 10⁻⁸ on a recorded mesh, and ten times the measured
spread between meshes on an unseen one (`nanopnp.validation.stability`; SPECIFICATION §7.6 NOTE).

**`NPY_DISABLE_CPU_FEATURES` ignores a name the platform does not dispatch** **[tested: tests/tier1/test_ngsolve_traps.py::test_ngsolve_trap_structured_mesh_cpu_features_sampler_and_gate_constants]**. NumPy
2.4.6 (Python 3.11) and 2.5.2 (Python 3.12) both start silently with ARM names on x86-64, and both
report the cap through `numpy._core._multiarray_umath.__cpu_features__`. The converse, x86 names
on arm64, was not run locally: CI's macOS leg, which sets `"X86_V4 AVX512_ICL AVX512_SPR"` like
every leg, is its first test.

### 8.2 Measured: the reaction flux really is worth it

Gouy-Chapman at 0.1 M, ζ̃ = 2, P2, planar slab. Wall gradient recovered two ways and compared with
the analytic `-φ̃'(0) = (2/λ_D) sinh(ζ̃/2)`. **[tested: tests/tier1/test_ngsolve_traps.py::test_ngsolve_trap_gouy_chapman_reaction_flux_and_solver_facts]** **[tested: tests/tier2/test_electrostatic_benchmarks.py::test_ver12_grahame_surface_charge]**

| mesh | variational reaction flux | pointwise `grad(u)` at the wall |
|---|---|---|
| `h = λ/4` | +0.004 % | −0.84 % |
| `h = λ/8` | +0.0001 % | −0.28 % |
| `h = λ/16` | +0.00003 % | −0.08 % |

Two hundred times better on the coarsest mesh, and it is *already converged* where the pointwise
gradient still has percent-level error. This is the quantitative case for NUM-24/NUM-25 over any
gradient- or cross-section-based extraction.

### 8.3 Convergence and solver facts

- **P2 gives clean O(h³) in L² on the r-weighted axisymmetric form.** Debye-Hückel in a cylinder,
  relative weighted L² error against `ζ I₀(r/λ)/I₀(a/λ)`: 1.12e-3 → 1.48e-4 → 1.99e-5 → 2.46e-6 for
  `maxh` 0.4 → 0.05 nm, i.e. rates 2.92, 2.90, 3.01. The axisymmetric weak form and the natural
  axis condition are correct. **[tested: tests/tier2/test_electrostatic_benchmarks.py::test_ver13_debye_huckel_in_a_cylinder]** **[tested: tests/tier2/test_electrostatic_benchmarks.py::test_ver13_axis_condition_is_natural_not_dirichlet]**
- **UMFPACK *is* built into the pip wheel**: `ngsolve.config.USE_UMFPACK` is True and
  `mat.Inverse(freedofs, inverse="umfpack")` works. `USE_MUMPS`, `USE_PARDISO` and `USE_MKL` remain
  False, and `inverse="pardiso"` raises "MKL Pardiso is not available". So the default direct path
  of NUM-21 is available out of the box; only the GPL-2+ licensing of UMFPACK is at issue, not its
  presence. **[tested: tests/tier1/test_ngsolve_traps.py::test_ngsolve_trap_gouy_chapman_reaction_flux_and_solver_facts]** **[tested: tests/tier1/test_linear_solver.py::test_num21_both_licensed_paths_are_available]**
- **The coupled axisymmetric system converges at the Taylor-Hood rates under MMS.** Manufactured
  `φ, c_i, u, p` on a 2 × 4 nm cylinder, constant transport coefficients with the steric `β_i`
  retained, `maxh` 0.4 → 0.2 → 0.1 nm (2 × 10⁴ DOF at the finest). Relative `r`-weighted L² rates:
  2.9–3.6 for `φ`, 3.0–4.0 for `c_i`, 3.0–3.5 for `u`, and **2.7 for `p`**. The pressure rate is the
  P1 half of the P2/P1 pair, not a shortfall — asserting O(h³) there would be asserting something
  untrue of a correct solver. **[tested: tests/tier2/test_mms.py::test_ver18_second_order_fields_converge_at_third_order]** **[tested: tests/tier2/test_mms.py::test_ver18_taylor_hood_pressure_converges_at_its_own_order]**
- **An uncurved mesh of a curved Dirichlet boundary costs the P2 rate an order.** Netgen meshes
  are affine unless `Curve` is called, so a grounded sphere of radius `R` is a polygon whose chords
  sag by `h²/(8R)`, and the potential inside carries that `O(h²)` geometric error whatever the
  element order. In WP28's VER-58 benchmark (one smeared atom inside a 10 nm grounded sphere,
  `poisson`, `P2`), letting the arc follow the far field's 1.6/0.8/0.4 nm held the disc error's rate
  at 2.02 between the finest two levels; fixing the arc at 0.02 nm at every level gave 3.00, the
  potential's own. An analytic benchmark on a curved boundary pins the boundary's element size, or
  curves the mesh, before it reads a rate. **[tested: tests/tier2/test_charge_potential_axis.py::test_ver58_deposited_potential_converges_at_the_potentials_own_rate_on_the_axis]** **[tested: tests/tier2/test_charge_potential_off_axis.py::test_ver58_deposited_potential_converges_at_the_potentials_own_rate_off_the_axis]**
- **`CoefficientFunction.Diff` and `Operator("hesse")` both work on a component of a product
  space**, and `Diff` works with respect to a `GridFunction` as well as a trial proxy. That is what
  makes the PHY-23 dielectric terms expressible: `∇ε_r = Σ_i (∂ε_r/∂c_i) ∇c_i` by the chain rule,
  with the sensitivities taken symbolically rather than by finite differences. **[tested: tests/tier1/test_ngsolve_traps.py::test_ngsolve_trap_gouy_chapman_reaction_flux_and_solver_facts]** **[tested: tests/tier1/test_nernst_planck.py::test_phy23_the_permittivity_sensitivity_is_zero_when_the_correction_is_off]**
- **A `BilinearForm` term carrying no trial function assembles and linearises correctly.**
  `a += (-f*v)*dx` with `f` a coefficient function contributes to `Apply` and contributes nothing to
  `AssembleLinearization`, which is exactly right for a manufactured or body source in a nonlinear
  residual. There is no need for a separate `LinearForm` on the Newton path. **[tested: tests/tier1/test_ngsolve_traps.py::test_ngsolve_trap_gouy_chapman_reaction_flux_and_solver_facts]**
- **Varadhan screened-Poisson distance is accurate enough.** `w - t Δw = 0`, `w = 1` on the source,
  `d = -√t ln w`, solved **planar** in (r, z) — for a surface of revolution the meridian-plane
  distance *is* the 3D distance. Against the exact `a - r` of a cylinder, within 1.5 nm of the
  wall: √t = 0.1 nm → 0.6 pm worst error, 1.1 % gradient jump; √t = 0.2 → 1.4 pm, 0.17 %; √t = 0.3
  → 10 pm, 0.08 %. **[tested: tests/tier1/test_wall_distance.py::test_ver06_distance_matches_the_exact_field_near_the_wall]** **[tested: tests/tier1/test_wall_distance.py::test_ver06_gradient_is_continuous_to_the_stated_tolerance]**
- **…but the diffusion length must be resolved by the mesh it is solved on, and the default is
  sized for the wall corrections, not for a force band.** Reusing `DEFAULT_DIFFUSION_LENGTH_NM`
  (0.2 nm) to build the NUM-28 extension `w` on a mesh whose elements are 1.6 nm across leaves the
  screened Poisson unresolved: it oscillates, undershoots the exponential floor, and the recovered
  `d` jumps to its cap *inside an element touching the body* — so the smoothstep is no longer zero
  there and `w` comes off the surface at 1 − 10⁻⁴ instead of 1. The symptom was an assertion on `w`
  failing at a mean-square departure of 8.2 × 10⁻⁹; the cause was a distance field, not an
  extension. Sizing √t at a quarter of the shell width instead cured it and improved the Stokes-drag
  benchmark by a factor of thirty, from a 6 × 10⁻⁴ plateau to 2.0 × 10⁻⁵ falling monotonically.
  **The rule: √t is set by the feature the field has to resolve, and there is no single default that
  serves both a sub-nanometre wall correction and a several-nanometre force band.** **[tested: tests/tier1/test_forces.py::TestAxialExtension::test_num28_extension_is_ez_on_the_body_and_zero_on_the_outer_boundary]** **[tested: tests/tier1/test_qoi_stage.py::test_num28_the_extension_shell_scales_to_the_body_in_the_mesh]**

### 8.4 Sweeps: the warm start, the forest, and what parallel scaling measures

Measured under WP11 on the toy pore (`a` = 2 nm, `L` = 6 nm, reservoir 10 nm) at `maxh` 4.0 /
`wall_h` 0.35 nm — 392 elements, the coarsest mesh NUM-34 admits with the wall corrections on —
0.1 M NaCl, `willems2020_nacl` with every correction active, `default_ladder`, stabilisation
`none`.

- **A warm start does not move the answer, and the figure is 3.4 × 10⁻⁹. [tested: tests/tier2/test_sweep.py::test_ver37_a_warm_start_does_not_move_the_answer]** A 2 × 2 grid
  (two concentrations × ±50 mV) solved twice: once warm through the forest, once cold into a store
  that had never seen a neighbour. Worst relative difference over every scalar every member
  reported: `3.367 × 10⁻⁹`, on `conductance_S`, against the `1 × 10⁻⁶` nonlinear relative tolerance
  the comparison is stated at. On the deepest point the current agreed to `9.8 × 10⁻¹⁰`
  (`1.825414947 × 10⁻¹⁰` A warm against `1.825414949 × 10⁻¹⁰` A cold). This is the premise
  §5.3.2 relies on when it keeps the warm-start source out of the stage-10 key, and it is measured
  rather than assumed.
- **The warm start is worth 2.81× in Newton iterations on four points. [tested: tests/tier2/test_sweep.py::test_ver37_the_warm_path_costs_strictly_fewer_newton_iterations]** 77 iterations
  warm against 216 cold, with 3 of 4 members warm-started; the root is cold in both passes by
  construction. A warm member solves the target rung alone — NUM-18 stage 9 generalised to the
  other axes — where a cold one climbs twelve rungs.
- **Measure that saving in iterations, not in seconds.** The wall clock said 10.5 s against 22.3 s
  on an idle machine and **34.3 s against 26.7 s** — the two passes swapped — when the same code
  ran alongside the rest of the test suite. A wall-time comparison between two passes of the same
  work is a statement about what else the machine is doing; the iteration counts are a property of
  the solves. `MemberResult` carries both, and only the second is ever asserted on. **[tested: tests/tier2/test_sweep.py::test_ver37_the_warm_path_costs_strictly_fewer_newton_iterations]**
- **What differs across an edge, by axis.** **[tested: tests/tier1/test_warm_start_descriptor.py::test_ver37_a_neighbour_along_the_bias_axis_loads_and_records_the_difference]** **[tested: tests/tier1/test_warm_start_descriptor.py::test_ver37_a_neighbour_along_the_salt_axis_loads_and_records_the_scales]** A bias step differs from its parent in
  `solve_hash` alone; a salt step differs in `solve_hash` **and** `model.scales`, the NUM-09 scale
  set being a function of `concentration_M`. Both are operator keys the §5.3.2 partition permits;
  a gate on either would refuse the axis outright.
- **The §8.3 reference grid is 42 waves of mean width 87.5. [tested: tests/tier1/test_sweep_plan.py::test_ver36_the_reference_sweep_parses_and_enumerates_the_section_8_3_grid]** 5 physics cases × 35 biases ×
  21 concentrations = 3,675 points, one root, deepest point at depth 41, peak wave width 174. The
  dependency structure is therefore not what limits QR-06 on twelve cores; the serial tail is the
  last few waves and it is short.
- **Parallel efficiency on four cores: 1.00, 0.76, 0.50 at N = 1, 2, 4. [verified][^wp11-sweep-timings]** 25 points in
  seven waves of widths 1, 3, 5, 5, 5, 4, 2; fresh store each run, every member a miss, thread
  counts pinned to 1 per worker. Wall clock 33.5 → 22.1 → 16.8 s, so 2.0× at four workers on a
  four-core machine that is also running the parent process. Throughput over uncached members:
  2 686 → 2 034 → 1 337 points per worker-hour.
  These are the historical WP11 timings, not asserted performance bounds. The current benchmark
  checks completion and records a new curve. **[tested: tests/tier2/test_sweep_throughput.py::test_ver39_the_scaling_curve_is_measured_and_recorded]**
- **One pool per plan, not one per wave, and it is worth a factor of the same size.** **[tested: tests/tier1/test_ngsolve_traps.py::test_ngsolve_trap_structured_mesh_cpu_features_sampler_and_gate_constants]** **[tested: tests/tier2/test_sweep_throughput.py::test_ver39_the_scaling_curve_is_measured_and_recorded]**
  `spawn` re-imports the package in each worker at about a second apiece. Creating the pool per
  wave put that cost into the measurement: on a nine-point grid in five waves it took
  `efficiency(4)` from 0.75 to **0.29**. **[verified][^wp11-sweep-timings]**
  The pool is now held open across the whole plan.
- **A single-axis grid caps the curve at N = 2 whatever the runner does.** A one-axis sweep rooted
  in its middle has waves two points wide, so a scaling measurement on one reports the *grid*. Two
  axes are the minimum for a curve that says anything about the dispatch.
- **A generated mesh's parent is keyed through the store, not the case. [tested: tests/tier2/test_sweep_generated_mesh.py::test_ver37_a_generated_mesh_sweep_warm_starts_from_its_parent]** The stage-10
  key needs the mesh artefact, and a generated mesh exists only as stage 6's stored artefact, keyed
  on the stage-5 recipe. Keying the parent from its bare case raised for every such sweep, and the
  runner's broad `except` turned that into a cold start, so every member climbed the ladder:
  44 Newton iterations instead of 5 on the Tier-1 synthetic profile. `pipeline.run.stored_upstream` now
  keys the parent's walk through the solve's inputs with every payload taken from the store, and only a
  missing artefact is a cold fallback (CR-1, `tests/tier2/test_sweep_generated_mesh.py`).

### 8.4.1 A sweep axis over a space key severs the forest, and the gate that fires is `fields` **[tested: tests/tier1/test_attribution.py::test_val01_ladder_rungs_are_separate_warm_start_components]** **[tested: tests/tier1/test_warm_start_descriptor.py::test_val01_a_warm_start_across_an_element_order_is_refused]** {#841-a-sweep-axis-over-a-space-key-severs-the-forest-and-the-gate-that-fires-is-fields}

An axis varying `numerics.elements`, `numerics.stabilisation`, `inputs.mesh`, `physics.model`,
`physics.flow` or `boundary_conditions.ground` writes a descriptor key `load_initial` refuses, so
the warm-start forest is **planned** with one component per value of that axis rather than built and
then refused member by member. The WP13 attribution ladder is a sweep of exactly this shape: 4 rungs
× 5 cases plans as 4 roots in wave 0 and 20 points in 3 waves, with no edge crossing the rung axis.

A detail that is easy to get wrong when writing the test for it: an element-order change cannot move
without moving `fields` and `ndof` with it, and `fields` comes **first** in `SPACE_KEYS`. So the
refusal a P2 → P3 crossing actually produces names `fields` and prints both field records with their
orders; `model.elements` is the same fact restated per field kind, gated on the same side so the two
cannot disagree, and is the belt to `fields`'s braces rather than the key that fires. [tested: tests/tier1/test_warm_start_descriptor.py::test_val01_a_warm_start_across_an_element_order_is_refused]

### 8.5 Measured: NUM-26's relative route check is inapplicable at exactly zero bias **[tested: tests/tier1/test_qoi.py::test_num26_two_vanishing_currents_do_not_divide_by_zero]** **[tested: tests/tier1/test_qoi.py::test_num26_round_off_currents_at_zero_bias_fail_the_relative_check]** **[tested: tests/tier1/test_sweep_plan.py::test_ver36_the_reference_sweep_parses_and_enumerates_the_section_8_3_grid]** {#85-measured-num-26s-relative-route-check-is-inapplicable-at-exactly-zero-bias}

At `V = 0` the current is zero, and both extraction routes return round-off:
`I_ψ = 2.288 × 10⁻²⁷` A against `I_reaction = 4.606 × 10⁻²⁵` A on the toy pore above. The relative
difference is then `0.995` and the NUM-26 gate aborts the run — on a solve that converged, on a
mesh that is admissible, at the one operating point where the answer is known exactly.

`RouteAgreement.relative_difference` divides by `max(|I_ψ|, |I_reaction|)` and returns `0.0` only
when *both* are exactly zero, which round-off never is. So the check is not wrong about these two
numbers; it is being asked a question — "do these two currents agree to one part in a thousand" —
that has no answer when there is no current.

**Consequence for a sweep:** a bias axis containing `0.0` aborts one member per remaining axis
combination, with exit class 4 and a diagnostic about the extraction. The checked-in
`docs/sweeps/phase1-reference.sweep.yaml` therefore roots its bias axis at **+5 mV** rather than at
0 V and carries 17 exactly-opposite pairs plus that one unpaired value: 35 values, 3,675 points,
1,785 rectification pairs, 42 waves — the §8.3 grid, with the degenerate point moved off it.

Not fixed here. Making the check inapplicable rather than failing at zero current means deciding
what "no current" is, which is a scale the extraction does not currently carry, and NUM-26 is a
Phase-1 headline gate. Recorded for whoever owns it next.

### 8.6 Measured: locating the gate sample points costs 100× evaluating on them **[tested: tests/tier1/test_gates.py::test_sampler_locates_its_points_once]** **[tested: tests/tier1/test_ngsolve_traps.py::test_ngsolve_trap_structured_mesh_cpu_features_sampler_and_gate_constants]**[^wp45-numerics-strip] {#86-measured-locating-the-gate-sample-points-costs-100-evaluating-on-them}

On a 144,628-element mesh, `FieldSampler` over the fluid holds 1,012,396 points (duplicates kept on
purpose, so each stays inside its own element) and takes 2.7 s to build and **21.7 s** to locate;
over the whole mesh, 434,885 points take 2.9 s and 9.4 s. Evaluating a field on the located points
takes 0.23 s. Without sharing, each rung builds two samplers and each solve three more, about 36 s a
rung at that size.
`FieldSampler.shared` keeps one per mesh and material
set, cached **on the mesh object**: `ngsolve.comp.Mesh` is unhashable, so a `WeakKeyDictionary`
raises `TypeError`, but it takes attributes and weak references, and the mesh ↔ sampler reference
cycle is collected with the mesh. **[tested: tests/tier1/test_ngsolve_traps.py::test_ngsolve_trap_structured_mesh_cpu_features_sampler_and_gate_constants]**

**Gate constants** (`numerics/gates.py`, `numerics/linear.py`). **[tested: tests/tier1/test_ngsolve_traps.py::test_ngsolve_trap_structured_mesh_cpu_features_sampler_and_gate_constants]**

- `INTERIOR_OFFSET = 1e-4`: sample points are pulled towards their element's centroid by this
  fraction, because a vertex or midpoint on the fluid/solid interface can resolve into the solid
  element, where a fluid-only concentration evaluates to 0, not positive. On the analytic pore at
  `maxh` 6 nm and 2 nm, 1e-6 still resolves into the solid and 1e-5 is the first fraction that does
  not; 1e-4 keeps an order of margin and moves a P2 sample by 1e-4 of the field's variation across
  the element.
- `PACKING_WARNING = 0.8` is not a specified threshold; it leaves a log trace before `Phi = 1`.
- `MINIMUM_WALL_DISTANCE_NM = -1e-3` (NUM-34): zero would gate the rounding mode, since
  `GridFunction.Set` leaves an interior residual of a few 1e-4 nm of platform-dependent sign;
  `-P2 = -1e-2` nm is the ion wall function's root, so a gate there admits `D = 0` and restates a
  fitted coefficient. At `d = -1e-3` the PHY-02 clamp absorbs 5.8e-3 (unclamped `1 - exp(-0.0558)
  = 0.0543` against the clamped 0.0601).
- The Poisson diagonal block scales as `1/lambda~^2`, 130 at 3 M and a 2 nm pore (NUM-10).

### 8.5.1 Small facts recorded from the `physics/` prose strip **[tested: tests/tier1/test_knowledge_arithmetic.py::test_ngsolve_physics_small_facts]** {#851-small-facts-recorded-from-the-physics-prose-strip}

- NGSolve's `SumOfIntegrals` has no unary minus: a surface-charge term is built with its sign in the
  integrand, because a form built and then negated is a `TypeError`
  (`physics/pb.py`, `solve_pb_recorded`).
- The grad-div coefficient `tau_c = Re rho~ ||u~|| h_K / 2` is about 9e-6 at `Re` = 6e-4, `h~` = 0.03 and
  `||u~||` of order 1: the term is numerically inert here and is assembled anyway
  (`physics/stabilisation.py`).
- `phi~` at P2 has an element-wise constant Hessian, which is why the PHY-23 chain rule needs no
  further NGSolve construct (`physics/nernst_planck.py`, `excess_potential_gradient`).

### 8.5.2 Small facts recorded from the `validation/` prose strip **[verified][^wp45-validation-strip]** {#852-small-facts-recorded-from-the-validation-prose-strip}

- On the VER-11 benchmark pore, `Delta_transport` and `stabilisation_currents_A` agree to 1.55e-3 of the
  current: both measure the same physics, but the report prints them under distinct names
  (`validation/attribution.py`).
- `validation/mms.py` imports `sympy` at module scope (about 150 ms) because nothing on the CLI, GUI or
  sweep-dispatch path imports `nanopnp.validation`: `import nanopnp.cli` stays at 34 ms and
  `import nanopnp.physics.models` at 28 ms with the module present. Revisit if stage introspection reaches it.

---

[^wp45-validation-strip]: `git show 3872426`, prose strip of `src/nanopnp/validation/attribution.py` and `src/nanopnp/validation/mms.py` (WP45, 13 October 2026).
[^wp9-clya-aliasing]: `git show 0ea0789` and `git show c27c35c`, WP9 delivered ClyA charge-table aliasing and multi-OS unstructured mesh quadrature records.
[^wp35-simd-dispatch]: `git show 6c0a249` and `git show 1a2e383`, WP35 NumPy SIMD dispatch and VER-62 number-stability mesh records (5 October 2026).
[^wp45-numerics-strip]: `git show 7597814`, prose strip of `src/nanopnp/numerics/gates.py` recording the 144,628-element `FieldSampler` timings (WP45, 13 October 2026).
[^wp3-singular-system]: `git show 0f8b57b:.knowledge/06-numerics-fem.md`, trap 9 (singular five-field block system, solver norms and residuals, WP3 review).
[^wp11-sweep-timings]: `git show 5abcf42:.knowledge/06-numerics-fem.md`, section 8.4 (WP11 toy-pore setup, one thread per worker, worker counts 1/2/4 and pool lifetime).

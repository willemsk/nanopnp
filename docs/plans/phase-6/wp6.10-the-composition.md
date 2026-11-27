# WP6.10 — The composition

**Status: planned, not started.** Written 27 November 2026 by Fable 5.2 at high effort, on the code at `5332fbd`. Inherits §8.2.62 BL1, BL2, BL5 and BL6, [the kernel's design](../../design/kernel.md), REV-300 and the test
scope (§8.2.13 N1). Its last commit on `main`
takes `v0.7.0-alpha.10` (§8.4.1).

The [Phase 6 plan](phase-6-library-foundations.md)'s WP6.10 entry sets this scope. `SPECIFICATION.md` governs:
where they disagree this plan is wrong, and identifiers are pointers into it.

## In brief

**What changes.** At the default settings a user notices nothing: the same equations are assembled, now from small
registered pieces in place of one long routine. Each piece is written once, and the optional stabilisation, the
read-out of the current and the flow diagnostic read that one statement. No piece names the finite-element
library or assumes two dimensions, and a test fails if one does. One change is deliberate, as you ruled: with the dielectric forces and the stabilisation both on, the stabilisation steers by every part
of the ions' drift, so that combination computes slightly differently from the last release. No stored number takes
it.

**Cost.** About 3 sessions, 3 to 7 agent hours and 5 times you act. The trial build took 0.7 agent hours, without tests, review or ship.

**What could go wrong.** A piece could be lost, or get a wrong sign, in the move. So the old routine's result is
stored first, the new assembly is compared with it entry by entry on twelve variants, and the
thirteen stored runs are repeated. A number that moves beyond round-off falls under your rule: explained and listed in
the pull request, or back to you. The layer that hides the library is tested with one library alone.

**Your call.** No decision is open: the phase plan left the technical choices to this plan, and your rulings cover
the rest. Do you approve this plan? *Recommendation:* approve. One choice to note: the
pieces are cut along today's integrals, with the forces on the fluid joined into one, because a bolder cut was
measured to change how accurately an integral is evaluated.

## Execution brief

Scope: the Phase 6 plan's WP6.10 entry. The kernel's records and `compose`; the coupled residual of `pnp`, `pnp-ns`
and `epnp-ns` composed, and `CoupledModel.residual_form`'s body removed; the stabilisation, the cell Péclet number
and NUM-24's indicator current reading the terms' one statement. Nothing unmerged is needed.

It discharges FR-40 in part, and QR-13 for the coupled models. It claims **VER-81**, new, Tier 1. It
amends NUM-12's NOTE, NUM-14's NOTE by one sentence, VER-65, the NOTEs of §5.4.1 and §5.4.4 and Appendix A's FR-40
and QR-13 rows, each in the item that builds it. It fixes REV-300. Nine decisions: the phase plan's open decision 19 is
D2, D3, D5.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| **D1 The records and their modules** | `physics/kernel.py` holds the records and `compose`; `operators.py` the operators' protocol and the geometry; `backend.py` NGSolve's implementation; `coupled.py` the coupled terms and slots. `nernst_planck.py`, `flow.py` and `stabilisation.py` become term modules. `CoupledModel.context` is the one builder | §5.4.4; §5.4.1. Decided by the plan |
| **D2 The slots' cut** | A slot is one integral: its test field, domain, closing and rule. Today's integrals are the slots, with one merge: the inertia, the ionic force and PHY-23's force are `momentum.force`, closing `−(Σf)·v` | Every other pair differs in one of the four, sources apart, which are inputs; a merge across closings moves a rule (*Grounding*). BL1. Decided by the plan |
| **D3 The operators and the geometry** | A term writes `+ − * /` only with a scalar on one side. Every other product, derivative and elementary function is a method of `context.ops`; the dimension, the coordinates, the axial and radial directions and the identity are `context.geometry`'s | Ruled by the author, BL6 ("Terms name no library"); the names by the plan |
| **D4 One statement, every reader** | A flux term states its drift and a force term its density, once, with no flag. The wind is the sum of the drifts in force, the flow residual's force the sum of the densities; the cell Péclet number reads the wind; the indicator current is the species' `flux` slot closed with `ψ`. The approximate residual takes the wind whole, the decrement's `∇∇φ̃` included. The manifest's Péclet expression lists the drifts in force | Ruled by the author, BL5 ("Read it"); NUM-12's NOTE |
| **D5 In force, until WP6.11** | `CoupledModel.terms_in_force()` alone decides, from each display record's switches and correction leaf and the model's options | WP6.11's records replace it. Decided by the plan |
| **D6 What goes and what stays** | The functions of *Grounding* D6 are deleted, with no alias. `poisson.py`, `pb.py` and the single-field models are not edited; `post/forces.py` changes one call. A test of a deleted function keeps its assertion and tolerance, through the kernel | BL1; §5.4.1's NOTE; the test scope. Decided by the plan |
| **D7 A moved number** | Predicted: round-off. Today's operator is stored before the first edit, and the composed one equals it within 10⁻¹² on the design's ten variants; the thirteen stored walks hold 10⁻⁸. A miss is re-pinned on VER-62's three conditions or stops the package | Ruled by the author, BL2 ("Re-pin when explained") |
| **D8 VER-65's rule** | The modules defining a term's function or a slot's closing equal `term_modules:` of `modularity-layering.yaml` in both directions, and none imports the backend; `kernel.py` and `operators.py` neither | Ruled by the author, BL6; its mechanism by the plan |
| **D9 VER-81** | Tier 1, `tests/tier1/test_kernel.py`: one integral a slot; a term left out changes its own slots alone; each reader reads every statement | §5.4.4's tests. Decided by the plan |

### Grounding

Verified at `5332fbd`, on NGSolve 6.2.2606.

**D1**

- `physics/models.py:CoupledModel.residual_form` builds the coupled residual from `poisson_operator`,
  `charge_source`, `surface_charge_term`, `species_flux` with `nernst_planck_residual`, the mode's `transport_term`,
  `_flow_residual` and the mode's `flow_term`. It runs on every coupled solve: `CoupledModel.solve` and
  `solve/state.py:restore` call it, with no option between. Its signature and its five refusals stay; its body
  becomes one `compose` call.
- NGSolve is named in `nernst_planck.py` (`grad`, `exp`, `Operator("hesse")`, `Diff`), `flow.py` (`grad`, `.trans`,
  `Trace`, `InnerProduct`, `velocity[0]`, `ngs.x`, `CF((0.0, 0.0))`, an `isinstance` on `CoefficientFunction`) and
  `stabilisation.py` (`specialcf.mesh_size`, `sqrt`, `IfPos`, `Id(2)`, `OuterProduct`, `grad`).
- `materials/forms.py:MathOps` is the protocol the correction forms already take, with `NGSolveOps` beside it;
  `NondimensionalCoefficients.ops` holds one. `coefficients.py` and `materials/fields.py` keep their backend
  imports: a coefficient stands behind the context (§5.4.1).
- `tests/tier1/test_layering.py:test_ver61_top_level_module_imports_are_acyclic` reads module-scope imports alone,
  so `kernel.py` may name a term module's type under `TYPE_CHECKING`. `physics` already imports `numerics`,
  `materials`, `mesh`, `io` and `core`, and `post`, `solve` and `validation` import `physics`: no row of
  `relation:` moves.
- `physics/terms.py:EPNP_NS_TERMS` holds the twelve display records the coupled term list wraps, for all three
  coupled models, as the prototype did; the per-model lists are WP6.12's.

**D2**

- On a triangle NGSolve integrates at twice the element's order, plus the bonus, less the least derivative order
  among the integral's trial functions and the least among its test functions; orders 3 and 4 are one rule.
  Measured on a P2 product space, relative to the largest entry of the residual: the diffusion and the migration
  integrated apart differ from their one integral by 7.9 × 10⁻⁵ where `D̃` is constant and by 1.8 × 10⁻¹⁶ where it
  is corrected; the viscous stress and the pressure in one integral differ from today's two by 6.0 × 10⁻⁴; the
  inertia with the ionic force, and the ionic force with PHY-23's, differ from their separate integrals by at most
  1.9 × 10⁻¹⁶.
- `_flow_residual` closes the inertia with `+·v` and the two forces with `−·v` on the fluid at the estimated rule,
  so the inertia is the force density `−Re ρ̃ (∇ũ)ũ` under one closing.
  `stabilisation.py:momentum_residual` with `CoupledModel._flow_state`, and `post/forces.py` (`_integrands`,
  `_domain_force`), each write the three again.
- A source's slot agrees with another's in all four: the velocity's with `momentum.force`, the potential's with
  `poisson.fixed_charge` where the input states no rule. It stays apart, so that the densities WP6.11's forces
  read hold no manufactured source.
- The slots are 4 for Poisson, 3 a species, 9 for the flow and one a source, against the design's 4, 3, 11 and one.

**D3**

- `mesh.dim`, `ngs.Id(mesh.dim)` and `ngs.grad` of a `VectorH1` trial function give 3 and 3 × 3 on a tetrahedral
  mesh.
- `flow.py:axisymmetric_divergence` and the hoop integrand of `viscous_operator` are the two places a term reads
  `measures.is_axisymmetric`, `velocity[0]` and `ngs.x`.

**D4**

- `stabilisation.py:advective_velocity` sums the migration, the steric part and the advection, and leaves out
  PHY-23's decrement. `streamline_parameter`, `crosswind_projector`, `crosswind_viscosity`, `approximate_residual`
  and `cell_peclet` read it.
- `post/qoi.py:indicator_currents` integrates `species_flux(...) · ∇ψ` with `Measures.integrate`, and
  `stabilisation_currents` calls the mode's `indicator_term`, which integrates `transport_contributions` with `ψ`
  as the test function at each contribution's bonus.
- `CoupledModel.cell_peclet(state, wall_distance_nm)` and `transport_states` take no solid fraction, and
  `solve/continuation.py:_report_peclet` passes none. Under PHY-23 with a supplied solid fraction the decrement's
  drift takes the blend (`materials/fields.py:blend_sensitivity`), so both readers get `solution.solid_fraction` and
  its gradient, as `indicator_currents` does today.
- A Hessian of a component of the solved state evaluates at located points and assembles under a lagged `τ`, its
  residual and Jacobian finite.
- `numerics/gates.py:PecletMeasurement.expression` defaults to
  `"||b_i|| h_K / (2 D_i), b_i = z_i mu_i grad(phi~) + D_i beta_i - Pe u~"`. No test and no stored file pins it.
- `tests/tier2/data/number_stability.json` holds no walk with PHY-23's switch and a stabilised mode (§8.2.62).

**D5**

- `physics/terms.py:Term.switches` names attributes of `CoupledModel`; the one `correction` leaf in use is
  `electrolyte.corrections.steric.model`, read as `CoupledModel.steric`. A term in force today is one whose
  switches are all true and whose leaf is not `none`.
- `Pressure constraint`, `Stabilisation` and `Sources` have no display record. They are in force with
  `pressure_constraint`, while the mode's `terms` is not empty, and always.
- `Variable density` and `Corrections` add nothing to a slot. The first decides `Side.density`, which the
  continuity and the inertia read: `None` holds `ρ̃ = 1`.

**D6**

- Deleted: `nernst_planck.py` `species_flux`, `nernst_planck_residual`; `flow.py` `viscous_operator`,
  `pressure_term`, `continuity_term`, `inertia_term`, `electrical_body_force`, `dielectric_gradient_force`,
  `strain_rate`, `axisymmetric_divergence`; `stabilisation.py` `advective_velocity`, `StabilisationIntegrand`,
  `_assemble` and each mode's `transport_term`, `flow_term` and `indicator_term`; `models.py`
  `CoupledModel._flow_residual`, `_flow_state`, `_transport_state`, `transport_states`.
- The test files that call them, or `ConcentrationVariables`' two constructors: `tests/tier1/test_flow.py` (6
  tests in all), `test_nernst_planck.py` (11), `test_stabilisation.py` (34), `test_knowledge_arithmetic.py`,
  `test_dielectric_field.py`, `test_backend_registries.py`, `tests/tier2/test_electroosmosis.py` (VER-14, VER-15,
  a Stokes problem under a given charge) and `test_stabilised_mode.py` (VER-42). `test_stabilisation.py` builds
  its states in two local helpers, `_state` and `_flow_state`.
- `poisson.py`'s three functions also serve `pb.py`, the two single-field models, `tests/tier1/test_charge_quadrature.py`
  and `tests/tier2/test_maxwell_sphere.py`.
- `validation/costs.py:A8_BUILD` names `CoupledModel.residual_form`, which keeps its name.

**D7**

- `prototype/compare_operators.py` on `origin/prototype/wp6.09-kernel` assembles the ten variants at one smooth
  state on a cylinder of 118 elements through `create`, `space` and `residual_form`, whose signatures this package
  keeps. It uses the prototype's `compose_integrals` and `CoupledModel._reference_residual_form`, which no tree
  of this package has.
- The thirteen walks ran in 294.7 s at WP6.08, each printing its largest relative drift under
  `number stability on <environment>` (`tests/conftest.py:pytest_terminal_summary`).

**D8**

- `validation/modularity.py:backend_imports(sources=)` returns a `BackendImport(node, path, line, kind, target)`
  for each reference, with `path` as `physics/flow.py`. `modularity-layering.yaml` has `backend:`, which keeps
  `physics`: `backend.py`, `models.py`, `coefficients.py`, `pb.py`, `poisson.py`, `spaces.py` and `distance.py`
  import it.

### Implementation details

**Item 1, the records.** `physics/operators.py`, no backend import:

- `Operators(MathOps, Protocol)` adds `grad(f)`, `hessian(f)`, `dot(a, b)` (two vectors), `inner(a, b)` (two
  tensors), `apply(tensor, vector)`, `outer(a, b)`, `transpose(t)`, `trace(t)`, `component(vector, index)`,
  `derivative(expression, variable)` and `element_size()`.
- `Geometry`, frozen: `dimension`, `coordinates`, `axial` (an index), `radial` (an index; `None` unless the measure
  is axisymmetric), `identity`.
- `strain(ops, w)`; `hoop(ops, geometry, w)`, which is `w_r / r` or `None`; `divergence(ops, geometry, w)`, the
  trace of the gradient plus the hoop.

`physics/backend.py`: `NGSolveOperators(NGSolveOps)` and `geometry_of(mesh, measures)`, with `dimension = mesh.dim`,
`axial = dimension − 1` and `radial = 0` under the axisymmetric measure.

`physics/kernel.py`, which imports no term module at run time:

- `Contribution(slot, build)`, `build(context) -> Expression | None`.
- `KernelTerm(name, clause, display=None, contributions=(), drift=None, drift_text="", force=None)`, with
  `drift(context, side, species)` and `force(context, side)`, each an expression or `None`. A drift adds
  `c̃_i · b` of the trial side to `flux`, and a density `f` to `momentum.force`. `slots` lists the families it adds
  to.
- `Slot(family, test, domain, close, kind="volume", singular=False, extra_order=0, rule_order=None, species=None)`;
  `domain` is `omega`, `fluid` or `surface`; `close(total, context)` returns the integrand; `name` is the family, or
  `family:species`.
- `Side(functions, variables, coefficients, density)`; `Inputs(permittivity, solid, fixed_charge, surface_charge,
  surface_region, sources)`; `Context(ops, geometry, measures, fluid, trial, lagged, tests, inputs, steric,
  stabilisation, terms=(), species=None)`.
- `contributions(terms, slot, context)`, the sum before the closing; `integrand(...)`; `integrals(terms, slots,
  context)`, a named integral a slot, in order, through `Measures.volume` or `surface` with the slot's rule, on
  `context.fluid` or `inputs.surface_region` by its domain; `compose(...)`, their sum. Each binds `context.terms` to
  the list it is given and `context.species` to the slot's.
- `wind(context, side, species)` and `force_density(context, side)` sum over `context.terms`; `wind_text(terms)`
  joins each `drift_text` with ` + `, a leading minus written as ` - `.

**Item 2, the terms and slots.** Each contribution keeps today's expression. The prototype's `physics/kernel.py`
shows the shape; the code is written anew.

| Slot | Test, domain | Closing | Rule | Filled by |
|---|---|---|---|---|
| `poisson.stiffness` | φ, Ω | `Σ·∇v` | estimated | Poisson: `ε̃_r ∇φ̃` |
| `poisson.mobile_charge` | φ, fluid | `Σ v` | estimated | Poisson: `−S Σ z_i c̃_i` |
| `poisson.fixed_charge` | φ, Ω | `Σ v` | the input's `rule_order` | Poisson: `−ρ̃_fixed` |
| `poisson.surface_charge` | φ, the charged boundary | `Σ v` | estimated, surface | Poisson: `−σ̃` |
| `flux`, a species | `c_i`, fluid | `−Σ·∇w` | estimated | Nernst–Planck: `D̃_i ∇c̃_i` and the drift `z_i μ̃_i ∇φ̃`; the drifts of Steric flux `D̃_i β̃_i`, Advection `−Pe ũ`, Dielectric decrement `D̃_i ∇μ̃_ex,i` |
| `streamline`, `crosswind`, a species | `c_i`, fluid | identity | bonus 4, bonus 6 | Stabilisation |
| `momentum.viscous` | u, fluid | `Σ : ε(v)` | estimated | Momentum: `2η̃ ε(ũ)` |
| `momentum.hoop` | u, fluid | `Σ · hoop(v)` | singular | Momentum: `2η̃ hoop(ũ)`; absent without a radial direction |
| `momentum.pressure` | u, fluid | `Σ div(v)` | singular | Momentum: `−p̃` |
| `continuity` | p, fluid | `−q Σ` | singular | Velocity continuity: `ρ̃ div(ũ)` |
| `momentum.force` | u, fluid | `−Σ·v` | estimated | The densities of Inertia `−Re ρ̃ (∇ũ)ũ`, Body force `−S (Σ z_i c̃_i) ∇φ̃`, Dielectric-gradient force `−½ ‖∇φ̃‖² ∇ε̃_r` |
| `constraint` | p̄, fluid | identity | estimated | Pressure constraint |
| `flow.gls_momentum`, `flow.gls_pressure`, `flow.grad_div` | u, p, u; fluid | identity | bonus 4; the last singular | Stabilisation |
| `source.<field>` | the field; Ω for φ, else fluid | `Σ · test` | estimated | Sources: `−s` |

- The slots stand in this order, the species' three together. `coupled.py:coupled_slots(species, fields,
  fixed_charge_rule, sources)` returns them; `COUPLED_TERMS` holds the terms in `EPNP_NS_TERMS`' order, then
  `Pressure constraint`, `Stabilisation`, `Sources`.
- `ConcentrationVariables.primitive` and `logarithmic_branch`, and `excess_potential_gradient`, take `ops`.
  `permittivity_gradient` keeps its signature and returns `None` where it returns a zero vector today:
  `NondimensionalCoefficients.permittivity_varies` replaces its `isinstance`, `materials/fields.py:blend_gradient`
  takes `None` for a fluid gradient that is zero, and PHY-23's force then adds nothing. `post/forces.py` reaches
  it only where it is not `None`, and asserts so.
- `stabilisation.py`: `TransportState(species, diffusivity, gradient, wind, ops, geometry)` and `FlowState(velocity,
  pressure, density, viscosity, reynolds, force, source, ops, geometry)`, built by `transport_state(context, side,
  species)` and `flow_state(context, side)`. `momentum_residual` is `∇p̃ − f − s`. A mode keeps `name`,
  `parameters`, `provenance`, `terms` and `permits_equal_order`, and returns `transport_contributions(trial,
  lagged, test, source)` and `flow_contributions(trial, lagged, velocity_test, pressure_test)` as mappings from a
  slot's family to an integrand; `TRANSPORT_SLOTS` names the first's two families.
- `CoupledModel.context(mesh, measures, *, trial, tests=None, lagged=None, wall_distance_nm, fixed_charge,
  solid_fraction, solid_fraction_gradient, surface_charge, surface_charge_boundary, sources)` computes what
  today's body computes before its first integral, with `steric_form` and `stabilisation_model`; `lagged=None`
  takes the trial side. `TransportModel` gains `context` and `terms_in_force` and loses `transport_states`.
- A carried test of `test_electroosmosis.py` composes `Momentum` and `Velocity continuity` in a context built by
  hand, its charge as a force term written in the test.
- `species_flux` stays through item 2, for `post/qoi.py` and its own tests.

**The comparison (items 1 and 2).** Keep the script and its files in `"$(git rev-parse --git-dir)/wp6.10/"`,
uncommitted. Take `prototype/compare_operators.py` from the prototype's branch, drop its two uses of the prototype's names, add
`dielectric_gradient_forces` with `reference` and with `supg` to its variants, and give it `--write <file>` (each
variant's residual vector and Jacobian values to one `.npz`) and `--against <file>` (the largest difference of each,
relative to the stored largest entry). Item 1 writes the file before it edits `src/`. A lost file is written again
in a `git worktree` of `5332fbd`.

**Item 4, the readers.**

- `post/qoi.py:indicator_currents` builds `model.context(mesh, measures, trial=functions, tests={each
  concentration field: ψ}, wall_distance_nm=..., solid_fraction=..., solid_fraction_gradient=...)` and integrates
  `kernel.integrand` of each species' `flux` slot with `Measures.integrate`, on the fluid, at the slot's `singular`
  and `extra_order`. `stabilisation_currents` does the same over `TRANSPORT_SLOTS`.
- `CoupledModel.cell_peclet(state, measures, wall_distance_nm, *, solid_fraction=None,
  solid_fraction_gradient=None)`; `_report_peclet` passes the solution's.
- `PecletDiagnostic` gains `expression`, which `measure` hands to `PecletMeasurement`: `"||b_i|| h_K / (2 D_i),
  b_i = " + wind_text(model.terms_in_force())`. The drift texts are `z_i mu_i grad(phi~)`, `D_i beta_i`, `- Pe u~`
  and `D_i grad(mu~_ex,i)`.
- NUM-12's NOTE: the velocity assembled is the sum of the drifts of the flux terms in force (§5.4.4), the printed
  three at the validated default and `D_i ∇μ̃_ex,i` with PHY-23's switch. NUM-14's NOTE, under *Approximate
  residual*: the wind is taken whole, a second derivative inside a drift with it; what is dropped is the divergence
  of the diffusive flux and of the wind (BL5).

**Item 5.** `term_modules:` lists `physics/coupled.py`, `flow.py`, `nernst_planck.py` and `stabilisation.py`.

**The run (item 6).** WP6.08's command for the thirteen walks (its plan, *Item 2, the run*), its log at
`"$(git rev-parse --git-dir)/wp6.10/walks.log"`.

### Work items

- [x] 1. e482296 The stored operator, then `src/nanopnp/physics/operators.py`, `backend.py`, `kernel.py` and
  `tests/tier1/test_kernel.py` (D1, D2, D3, D9); done when the twelve variants are stored from the unedited
  tree and VER-81's first test passes. **Executor:** main
- [x] 2. 750c63f `physics/nernst_planck.py`, `flow.py`, `stabilisation.py`, `coupled.py`, `models.py`, `coefficients.py`,
  `materials/fields.py`, `post/forces.py`, and the tests of *Grounding* D6 (D1, D2, D4 to D7); done when the comparison is within 10⁻¹² on
  the ten variants, and on the two PHY-23 variants under a stabilised mode with the decrement's drift left out of
  the wind in a local edit that is not committed, and VER-81's second test and the carried tests pass. The Outcome
  lists each difference. **Executor:** main

  > **Outcome — ten variants at round-off, PHY-23 under a stabilised mode moved as ruled, and that pair assembles
  > fifty times slower.** Against the operator stored at `2ba10ab9`, on the comparison's 118 elements: the ten
  > design variants differ by at most 3.1 × 10⁻¹⁶ in the residual and 1.2 × 10⁻¹⁶ in the Jacobian, relative to the
  > largest entry. `dielectric_gradient_forces` with `reference` moves by 7.4 × 10⁻⁶ and 2.1 × 10⁻⁵, with `supg` by
  > 6.5 × 10⁻⁶ and 4.2 × 10⁻⁶: the decrement's drift in the wind (D4; BL5). With that drift left out of
  > `kernel.wind` in an uncommitted edit, all twelve are within 2.1 × 10⁻¹⁶. No other difference. The pair's one
  > assembly (`Apply` and `AssembleLinearization`) takes 69.6 s under `reference` and 33.8 s under `supg`, against
  > 1.25 s and 0.48 s without PHY-23; the streamline and crosswind slots take 16 s and 18 s a species: REV-302.
  > Beyond the plan, so that the build stays green: `post/qoi.py:stabilisation_currents` reads the kernel's
  > `TRANSPORT_SLOTS` in this item, not item 4; `Context` binds the slot's test field (`field`) beside its species,
  > and `Slot.per_field` names the sources' slots `source.<field>`; `concentration_field_name` moves to
  > `io/vocabulary.py`, which `coupled.py` reads, and `models.py` re-exports it.
- [x] 3. Compaction checkpoint. **Executor:** main
- [x] 4. 44d2dd8 `post/qoi.py`, `models.py`, `solve/continuation.py`, `numerics/gates.py`, `nernst_planck.py`
  (`species_flux` deleted, its tests carried), `specification/06-numerics.md`, and VER-81's row in
  `specification/07-verification/02-tier-1.md` (D4, D9); done when VER-81's third test and
  `tests/tier2/test_current_routes.py` pass. **Executor:** main

  > **Outcome — the readers read the kernel; VER-81's third group is five tests.** `indicator_currents` and
  > `stabilisation_currents` share one context and integrate the `flux`, `streamline` and `crosswind` slots closed
  > with `ψ`. The third group asserts each reader within 10⁻¹² on the 0.4 nm cylinder, and that leaving out each of
  > the four flux terms and the three force terms moves its reader by more than 10⁻⁶, so that no comparison passes
  > on a zero part; the finite assembly under PHY-23 and `reference` runs on a 1.5 nm mesh, 3.4 s. NUM-14's
  > *Approximate residual* bullet is reworded beside its added sentence, as "every second derivative is dropped"
  > contradicted the wind's `∇∇φ̃`. `test_current_routes.py` with `test_solution_state.py`: 39 passed.
- [x] 5. b8ffdf7 `docs/project/modularity-layering.yaml`, `tests/tier1/test_backend_guard.py` and VER-65's row (D8); done
  when VER-65's tests pass. **Executor:** main
- [ ] 6. The thirteen walks, a `RUN` hand-back with no commit (D7); done when the log shows thirteen walks, none
  failed or skipped. **Executor:** main, the run by the main session
- [ ] 7. The records: `specification/05-software-design/04-component-design.md`,
  `specification/a-traceability-matrix.md`, `docs/design/kernel.md`, `CHANGELOG.md`,
  `knowledge/06-numerics-fem/09-ngsolve-traps-found-by-implementing.md`, `knowledge/log.md`,
  `docs/project/review-findings.md`, `review-items.md`, this plan, the Phase 6 plan, `docs/plans/current.md`; done
  when the code and review say so. **Executor:** main

### Verification

Rows 1 to 3 are `tests/tier1/test_kernel.py`: vectors by `BilinearForm.Apply`, on the comparison script's mesh
and state.

| Test | Tier | Identifiers | Oracle | Tolerance |
|---|---|---|---|---|
| One integral a slot. Two terms written in the test, a diffusion `∇c` and a drift `∇φ`, on a P2 product space, in a context built by hand | 1 | VER-81; NUM-07 | The slot's vector equals that of the one integral written in NGSolve in the test; the two terms composed apart and added do not | 10⁻¹² of the largest entry, round-off; apart, above 10⁻⁶ (7.9 × 10⁻⁵ measured) |
| A term left out. `model.context`, `kernel.integrals`, each slot applied alone | 1 | VER-81 | With Steric flux, Advection, Inertia or Body force left out under mode `none`, every slot outside `term.slots` is equal entry for entry and each slot in it differs | Exact; above 10⁻⁸ of the slot's largest entry |
| Every reader. `epnp-ns`, `dielectric_gradient_forces`, `reference` | 1 | VER-81; NUM-12, NUM-14, NUM-24, PHY-23 | Each asserted: the wind is `z μ̃ ∇φ̃ + D̃ β̃ + D̃ ∇μ̃_ex − Pe ũ` written in the test; each of the four flux terms left out changes it by that term's drift; the flow state's force is the sum of the three densities; `cell_peclet` is `‖wind‖ h / (2 D̃)`; a species' indicator integrand is PHY-04's bracket written in the test, times `∇ψ`; the residual and the Jacobian are finite; `wind_text` at the default is today's string | 10⁻¹² relative in the L² norm over the fluid; the string exact |
| `test_backend_guard.py`, two tests added | 1 | VER-65; QR-13 | The `__module__` of each function of `COUPLED_TERMS` and of each closing, as a set, equals `term_modules:`, and `backend_imports()` holds no reference in it; `import ngsolve` substituted at line 1 of `physics/flow.py` fails naming it | Set equality |
| The carried tests (*Grounding* D6) | 1, 2 | VER-14, VER-15, VER-41, VER-42 | Each test's own | Unchanged |
| The push gate, on the land | 1, 2 | VER-16 to VER-18, VER-77; VER-62's push walks | Each test's own | Unchanged |
| Item 6's run | 2 | VER-62, VER-80 | The stored values | 10⁻⁸ (VER-62) |

```bash
uv run pytest tests/tier1/test_kernel.py tests/tier1/test_backend_guard.py tests/tier1/test_stabilisation.py -q
```

### Out of scope

- The switch records, the log branch's key, `post/forces.py` reading the densities: WP6.11.
- The per-model term lists, the single-field models composed, Poisson's stiffness stated once, `models.py` split,
  the full check, MOD-10: WP6.12.
- A planar 3D measure: WP6.13. The indicator's axis from the geometry (`post/indicator.py`): WP6.15.
- A registry of terms, the registrar: WP6.16.

### Open questions

None.

# Kernel design

The design of the kernel of registered terms that Phase 6 builds (FR-40; §8.2.53 BC1, BC2), written by WP6.09 and
tried in a prototype that is thrown away. **It is a proposal.** It amends no clause: the author rules it at the round
on the design, `/np-plan amend 6`, which rewrites ADR-005, §5.4 and §5.5 from what is ruled and numbers the kernel's
packages from WP6.10. Where this page and the specification disagree, the specification governs until then.

The prototype is the branch
[`prototype/wp6.09-kernel`](https://github.com/willemsk/nanopnp/tree/prototype/wp6.09-kernel), at `1b5f5e3`, forked
from `main` and never merged (§8.2.60 BJ3). Its code survives while the branch does; the author deletes it after the
kernel's last package. The kernel's packages write their code anew.

## The kernel in brief

Five pieces, each a record a reader can list without building a model:

- **A term** is one part of the equations, written from one PHY or NUM clause: its display `Term` of
  `physics/terms.py`, which already says when it is in force, and the contributions it adds. A flux term also states
  its *drift*, and a force term its *force density*, each written once (below).
- **A slot** is one integral of one equation: the field whose test function it takes, its domain (Ω, the fluid, or a
  boundary), its quadrature rule and how the summed contributions close into the integrand. The kernel sums a slot's
  contributions and integrates once. A flux integrated term by term may move its rule, because the engine estimates
  the order from the trial and test functions each integral carries, not from its coefficients (NUM-07's NOTE on the
  `r` weight), so a term never owns an integral.
- **A coefficient** is a corrected property, built once for an assembly from its registered correction model
  (PHY-22) and handed to every term that reads it.
- **A switch** is a record: its name, case path, validated default, the terms it brings in force, and what it
  requires and excludes. PHY-08's rule is two terms under one record.
- **A model** is a list of terms with a field set, a boundary vocabulary and a strategy (§5.4.3). A variant is a
  difference of lists or of switch values, not a class.

`compose(terms, slots, context)` returns the sum over the slots, in order, of one integral each, leaving out a slot
with no contribution in force. `context` holds the trial, test and lagged functions, the coefficients of both sides,
the measures, the mesh, the fluid region, the inputs (the fixed charge, the surface charge, the sources) and the
species at hand.

The two Poisson–Boltzmann rungs of the NUM-18 ladder, `pb-linear` and `pb`, and the `poisson` model keep today's code
(BJ1): the prototype composes `CoupledModel.residual_form` alone, which builds `pnp`, `pnp-ns` and `epnp-ns` and every
rung past the second.

## Today's integrals as slots

The slots are today's integrals, in today's order (`CoupledModel.residual_form` and `_flow_residual`). Another
partition is a re-pin, which only a ruling makes (§8.2.7 G10). "Estimated" is NGSolve's order from the trial and test
functions with the measure's bonus; "singular" takes the rule of order 3 or more that a `1/r` form needs (VER-07).

| Slot | Test | Domain | Rule | Today's function | Terms that contribute |
|---|---|---|---|---|---|
| `poisson.stiffness` | φ | Ω | estimated | `poisson_operator` | Poisson |
| `poisson.mobile_charge` | φ | fluid | estimated | `charge_source` | Poisson |
| `poisson.fixed_charge` | φ | Ω | `FixedCharge.rule_order` | `charge_source` | Poisson, from the input |
| `poisson.surface_charge` | φ | the charged wall | estimated, surface | `surface_charge_term` | Poisson, from the input |
| `flux`, per species | `c_i` | fluid | estimated | `nernst_planck_residual` of `species_flux` | Nernst–Planck (diffusion, migration), Steric flux, Dielectric decrement, Advection |
| `streamline`, per species | `c_i` | fluid | streamline bonus | the mode's `transport_term` | Stabilisation |
| `crosswind`, per species | `c_i` | fluid | crosswind bonus | the mode's `transport_term` | Stabilisation |
| `momentum.viscous` | u | fluid | estimated | `viscous_operator` | Momentum |
| `momentum.hoop` | u | fluid | singular | `viscous_operator` | Momentum, under the axisymmetric measure alone |
| `momentum.pressure` | u | fluid | singular | `pressure_term` | Momentum |
| `continuity` | p | fluid | singular | `continuity_term` | Velocity continuity, scaled by Variable density |
| `momentum.inertia` | u | fluid | estimated | `inertia_term` | Inertia, scaled by Variable density |
| `momentum.body_force` | u | fluid | estimated | `electrical_body_force` | Body force |
| `constraint` | p̄ | fluid | estimated | in `_flow_residual` | Pressure constraint |
| `momentum.dielectric_force` | u | fluid | estimated | `dielectric_gradient_force` | Dielectric-gradient force |
| `flow.gls_momentum`, `flow.gls_pressure` | u, p | fluid | flow bonus | the mode's `flow_term` | Stabilisation |
| `flow.grad_div` | u | fluid | flow bonus, singular | the mode's `flow_term` | Stabilisation |
| `source.<field>` | each field | Ω for φ, fluid otherwise | estimated | in `residual_form` | Sources (manufactured solutions) |

The `flux` slot is the one that D3 of the plan exists for: `species_flux` sums diffusion, migration, the steric part,
the decrement and advection into one bracket and negates it once, and the slot closes the same way, `−(Σ) · ∇v_i`.
With two species the coupled model has 4 + 3·2 + 11 slots and a source slot for each field; a slot that no term in
force fills is left out.

Three things the prototype taught about slots, none a contradiction of D3:

- **A slot's closing belongs to the slot.** Most slots take the summed expression times the test function, or times
  its gradient. The stabilisation's integrands already carry their test function, so their slots close with the
  identity. A term never chooses its test function.
- **A contribution may be absent by geometry.** The hoop term returns nothing under a planar measure, so its slot is
  left out; the kernel needs no branch for it.
- **The order of a sum is round-off.** At item 1 every slot was bit for bit today's except PHY-23's two flux slots
  (3.0 × 10⁻¹⁶), whose bracket the composition sums in another order. Item 2's drift written as `c̃_i b` moved the
  flux slots to at most 3.2 × 10⁻¹⁶ and left the stabilisation's slots bit for bit.

## Coefficients and corrections

`physics/coefficients.py:NondimensionalCoefficients` is built once in `residual_form` for the trial side and once for
the lagged state, and its constructor builds the driver once for every property. The kernel keeps this: the context
holds both sides' coefficients, and every term reads the same object. A correction stays its property's registered
model (PHY-22, §5.4.2); switching one to `none` changes the coefficient, never a term. A term whose whole effect is a
correction, the steric flux, is in force while its correction leaf is not `none`, which `Term.correction` already
says.

The prototype held this unchanged. Its context grew to twenty fields, the inputs among them; the kernel splits it into
the functions, the coefficients of each side and the inputs, so a term states which it reads.

## Switches as data and PHY-08's rule

Today a switch is code. `physics/models.py:SWITCHES` is a closed tuple of four names, read by the case checks,
`api/project.py` and two screens; `io/defaults.py:SWITCH_PATHS` holds the same four once more; and
`CoupledModel._deviations` and `io/defaults.py:deviations` each list the deviations from the validated default.

The kernel holds one record for each switch and derives all four lists from the records:

| Switch | Case path | Default | Terms in force | Requires | Excludes |
|---|---|---|---|---|---|
| `flow` | `physics.flow` | true | Advection, Momentum, Inertia, Velocity continuity, Body force | | |
| `variable_density` | `physics.variable_density` | true | Variable density | | |
| `inertia` | `physics.inertia` | true | Inertia | | |
| `dielectric_gradient_forces` | `physics.dielectric_gradient_forces` | false | Dielectric-gradient force, Dielectric decrement | `flow` | `log_variables` |

PHY-08 and PHY-23 bind the force and the decrement: either alone is thermodynamically inconsistent. The record states
the binding once, as one switch that brings both terms in force; nothing can switch one without the other, because no
record names one alone. `requires` and `excludes` replace the two refusals in `CoupledModel.__post_init__` and no
more. `variable_density` and `inertia` require nothing: their terms already need `flow` through their display
switches, and `epnp-ns` with the flow off and both at their defaults runs today, so a `requires` there would refuse
it. The prototype's records carry `requires=("flow",)` on both, written and never read. A
model's declaration names the records it honours, with the value sets of §5.4.3's NOTE. A value away from the default is a deviation in the manifest (FR-25), read from the record.

**What the prototype did not try.** It wrote the four records and decided "in force" from each display `Term`'s
switches, as today; `SWITCHES`, `SWITCH_PATHS` and the two deviation lists were not touched. Switches as data is on
paper.

## One expression and its three readers

The ionic force `−S ρ ∇φ` is written three times today: `flow.py:electrical_body_force`, `CoupledModel._flow_state`
(for the flow stabilisation) and `post/forces.py:_integrands`. PHY-23's force is written in the same three places,
and the inertia in three others. `stabilisation.py:advective_velocity` writes the migration, the steric part and
the advection a second time.

In the kernel a flux term states its drift `b` once, and its contribution to the `flux` slot is `c̃_i b`; a force term
states its density `f` once, and its slot takes `−f · v`. The three readers read the same function:

1. **The weak form**, through the term's contribution.
2. **The stabilisation**, which takes `b̃_i` as the sum of the drifts in force and `f` as the sum of the densities in
   force.
3. **The forces** of `post/forces.py`, which take the densities in force at the converged state.

The prototype built the first two readers: `advective_velocity` and `_flow_state` read the terms in force, and the
operator was unchanged to 3.2 × 10⁻¹⁶. `post/forces.py` was not edited (the plan's scope), so the third reader is on
paper, with VER-22's routes as its check.

**Where the prototype contradicted D4.** Not every drift is read by every reader. Today `advective_velocity` leaves
out PHY-23's decrement, so the stabilisation's wind and its approximate residual omit a part of the flux that the weak
form keeps. The prototype reproduced this with a per-term flag, `in_drift=False` on the decrement, and the guard walks
hold. NUM-12's NOTE writes the wind as `b_i = z_i μ_i ∇φ̃ + D_i β_i − Pe u`, without the decrement, and no clause
says whether that holds under PHY-23: NUM-14's reference settings were recorded for a model without it. The design
keeps the flag and puts the question to the author below (REV-300).

**A fourth reader the prototype left alone.** NUM-24's indicator current takes each species' flux from
`nernst_planck.py:species_flux`, the function today's weak form integrates, so the two read one flux (PHY-23's NOTE;
FR-23). The prototype composed the flux from the drifts and left the indicator on `species_flux`, so its flux is
written twice; that is why the control below was refused at NUM-26's route check. With the indicator reading the
drifts in force, as D4 asks, a term dropped from the model is dropped from both routes, and the route check no longer
sees it: the stored walks and the Tier 1 check that a term left out changes its own slots alone remain the guards.

## A model as a list of terms

A model is its field set, its boundary vocabulary, its strategies and a list of terms. Today three names, `pnp`,
`pnp-ns` and `epnp-ns`, build one class, `CoupledModel`, told apart by the electrolyte's switches and `flow`; their
display lists `PNP_TERMS`, `PNP_NS_TERMS` and `EPNP_NS_TERMS` are separate. In the kernel each is a registered list of
the same terms: `pnp-ns` is `epnp-ns` with the classical correction set, and `pnp` is `epnp-ns` without the flow's
terms, its corrections as the case sets them. A variant is a difference: a list of terms left out or a switch's value, never a
subclass. `ModelDeclaration.terms` is derived from the list, so the workbench's equations and the assembled operator
read one source.

The single-field models, `poisson`, `pb` and `pb-linear`, become compositions in the kernel's packages; the prototype
did not compose them (BJ1), and their checks are VER-12, VER-13 and VER-31.

**`physics/models.py`** (2,076 lines) loses `residual_form`'s body, `_flow_residual` and the second writing of the
drift and the force, 265 lines in the prototype, which a context builder of about 160 replaces while the terms'
expressions move to the kernel. It splits in three: the coupled model's class, the
registry with `create`, `declaration`, `case_model` and `role_conditions`, and the shipped models' term lists.
**`default_ladder`** (293 lines) keeps naming models, as §5.4.3's NOTE allows: §6.5 defines the ladder as a path
through named models. Its rungs past the second already call `create`; they read their terms from the registry, and
its body shrinks by the builder it shares with `create`, not by a redesign.

## The nine names the workbench reads

The workbench imports nine names of `physics/` (§8.2.53 BC1). The kernel keeps five, moves three with the registry,
and derives one:

| Name | Today | In the kernel |
|---|---|---|
| `SWITCHES` | `physics.models`, a tuple of four | Derived from the switch records |
| `Term` | `physics.terms`, re-exported by `physics.models` | Kept: the display part of a kernel term |
| `case_model` | `physics.models` | Moved to the registry's module |
| `declaration` | `physics.models` | Moved to the registry's module; its `terms` derived |
| `role_conditions` | `physics.models` | Moved to the registry's module |
| `CONDITIONS` | `physics.terms` | Kept |
| `Symbol` | `physics.terms` | Kept |
| `symbols_in` | `physics.terms` | Kept |
| `written` | `physics.terms` | Kept |

The shell follows a moved name, and no screen changes (BC1). `SWITCHES` keeps its name and its type, a tuple of
names, so its four readers do not change.

## Installed packages

An installed package declares its terms, corrections, shapes or solvers (§8.2.53 BC5). The design:

- **Found by entry point.** A package declares an entry point in the group `nanopnp.extensions`, resolving to a
  function that receives one registrar and registers through it. The kernel reads
  `importlib.metadata.entry_points(group="nanopnp.extensions")` at the first use of any registry, once a process, so
  the command line, the workbench and the API find the same set and a process that registers nothing pays nothing.
- **A failure is a refusal.** An extension that fails to import or to register is refused, naming its package and
  version; it is never skipped, since a run that silently lacks a term is a plausible wrong answer.
- **Named in the manifest.** Each registration an extension makes is recorded with its package and version; a run's
  manifest names every extension whose registration the run used, with its package and version (FR-25).
- **Unverified until a test says otherwise.** A term states the analytic case that verifies it, a VER identifier or
  a manufactured solution; one that states none is marked unverified in the manifest and on the workbench's
  equations.

Which registering names become public, a registrar or the nine `register_*` functions, is REV-67's question, which
the installed packages' package settles (BC5). The design proposes the registrar: one public type, and the registries
behind it stay private.

## §5.4.1's interface

§5.4.1 lists the names a second backend would implement, `FunctionSpace`, `TrialFn`, `TestFn`, `grad`, `dx_axi`,
`ds` and `Coefficient`, and §8.2.8 H3 left it unbuilt (MOD-10). The kernel gives the interface a place: the context
holds the trial and test functions and the coefficients, the slot holds the domain and the rule, and `Measures` holds
the measure. These are the table's names but `grad`, which a term's body still writes as backend algebra
(`ngs.grad`, with `ngs.InnerProduct` and the coordinate `ngs.x`): in the prototype 11 of the kernel's functions import
NGSolve.

Two readings follow, put to the author below: the seam is the context, the slot and the measure, and a term keeps
NGSolve's algebra until a second backend is planned (H3's argument stands: a wrapper with one implementation cannot
be tested for what it exists for); or a term also reads its few operators from the context, which makes its body
backend-neutral in form but tests nothing more today. VER-65 remains the guard either way.

## What the prototype showed

The pass marks were registered in the plan before any run (D5). The runs of marks (b) to (e) used the prototype's
head, one thread for each library and `NPY_DISABLE_CPU_FEATURES="X86_V4 AVX512_ICL AVX512_SPR"`, in
`linux-x86_64/X86_V3`. Mark (a) ran at `0867e2d`, whose code the head leaves unchanged: `1b5f5e3` adds
`prototype/three_d.py` alone.

| Mark | Command on the branch | Result | Mode |
|---|---|---|---|
| (a) The composed operator equals today's on ten variants, within 10⁻¹² | `uv run python prototype/compare_operators.py --slots` | Passed: the largest difference 2.1 × 10⁻¹⁶ in the residual and 1.2 × 10⁻¹⁶ in the Jacobian, at `0867e2d` | `none`, `reference` and `supg` |
| (b) Example 01's walk within 10⁻⁸ | the thirteen walks, below | Passed: 8.7 × 10⁻¹⁴ (`eof_m3_s`) | `none` |
| (c) The other twelve walks, reported | the thirteen walks | No miss: example 02 classical 2.6 × 10⁻¹⁶, ePNP-NS 2.2 × 10⁻¹⁶, example 03 charged 6.3 × 10⁻¹⁶, example 07 4.3 × 10⁻¹⁵, 2WCD charged 2.9 × 10⁻¹², 2WCD shell 1.3 × 10⁻¹²; the guards constant density 3.8 × 10⁻¹⁶, dielectric 1.8 × 10⁻¹⁶, log 2.1 × 10⁻¹⁶, no inertia 1.8 × 10⁻¹⁶ | `none` |
| | | the guards reference 2.3 × 10⁻¹⁶ and SUPG 5.3 × 10⁻¹⁶ | `reference`, `supg` |
| (d) Example 02's ePNP-NS walk without the steric term misses | `NANOPNP_PROTOTYPE_DROP="Steric flux" uv run pytest tests/tier2/test_examples_02_epnpns.py -q` | Missed: `nanopnp run` exits 4 at the route check | `none` |
| (e) The push gate's selection passes | `.claude/hooks/gate.sh run` | Passed in 474 s on the tree `c0171d4` | each test's own |

The ten variants are `epnp-ns` at its default; one change each of `dielectric_gradient_forces`, `log_variables`,
`stabilisation="reference"`, `"supg"`, `variable_density=False`, `inertia=False` and `pressure_constraint=True`; and
`pnp-ns` and `pnp`. Each is assembled at one smooth state set from the manufactured fields of VER-18 on a cylinder of
118 elements, with a fixed charge, a surface charge and a source for each field, so every slot is filled. The
dielectric variant has no solid fraction, because `nearest_solid_permittivity` refuses a mesh with no solid, so
PHY-23's blend under a solid fraction (PHY-20's NOTE) was not compared. With `NANOPNP_PROTOTYPE_DROP="Steric
flux,Inertia"` every variant misses, from 6.9 × 10⁻⁶ to 3.3 × 10⁻²: the comparison sees a term.

The thirteen walks are VER-62's seven and VER-80's six, through their own tests, as WP6.08's plan runs them (item 2):
`uv run pytest -q -rsfE -n auto --dist loadfile` on the files of examples 01, 02 (both), 03 and 07, of 2WCD's two
walks and of the guard numbers. 43 tests passed, none skipped, in 426 s; every walk ran on its stored mesh.

**The control.** With the steric flux dropped, the four tests of example 02's ePNP-NS file error at setup, since the
run is refused before its numbers are compared: NUM-24's indicator current, 6.2718 × 10⁻¹¹ A, and NUM-25's reaction
flux, 6.3127 × 10⁻¹¹ A, differ by 6.5 × 10⁻³, above the route tolerance of 10⁻³. Against the stored total current,
6.2876 × 10⁻¹¹ A, they drift by 2.5 × 10⁻³ and 4.0 × 10⁻³, five orders above 10⁻⁸. The refusal itself shows that the
solve reads the composition: the reaction flux is taken from the composed form, while the indicator writes the steric
flux from the state. Today the route check is a guard of its own against a term that the form drops and the
post-processing keeps; once the indicator reads the drifts in force it is not (*A fourth reader*, above).

**What the prototype does not show.** It is a quick build. Where it holds the numbers it shows that the design can
hold them, not that the kernel will: the kernel's packages write new code and pass the same marks again (BC4). It did
not compose the single-field models, did not read the switch records, did not edit `post/forces.py` and did not
compare PHY-23's blend.

## The 3D benchmark's price

CON-01 says that nothing may preclude 3D, and no test can fail it (BC5). The bounded trial (BJ2), at `1b5f5e3`,
`uv run python prototype/three_d.py`, 7 s:

- **VER-13 solved in 3D.** VER-13's cylinder (radius 2, length 4, its lateral face `wall`), meshed with Netgen at
  `maxh=0.4` and curved to order 2: 2,868 tetrahedra and 4,883 unknowns, meshed in 0.25 s and solved in 0.07 s by
  today's `solve_pb_recorded`, unchanged, under the planar measure. Its r-weighted relative error against
  `I₀(r/λ)/I₀(a/λ)` along a radius at mid-height is 3.8 × 10⁻³, against 1.1 × 10⁻³ on VER-13's 2D mesh of 118
  triangles and 267 unknowns.
- **VER-17's fluid counted.** The lumen and two half-ball reservoirs of 50 nm at VER-17's sizes (`maxh=50/12`, the
  wall at 0.5 nm, grading 0.2), the membrane not meshed: 58,445 tetrahedra in 5.4 s, 86,802 order-2 `H1` degrees of
  freedom, and 260,406 unknowns for VER-17's three fields. Not solved.
- **What refuses or mishandles a 3D mesh.** `mesh/adapter.py:from_ngsolve` refuses it (CON-01; its message cites
  CON-04), and so every quality
  gate. `Measures.volume(rule_order=)` has no `TET` rule and falls back to NGSolve's estimate without a word (at
  order 20 an explicit rule moves the vector by 8.5 × 10⁻⁴); `AXISYMMETRIC` weights by `ngs.x` on any mesh. Written
  for two dimensions: the eight `OCCGeometry(dim=2)` calls of `mesh/` and `geometry/`; `MeshData` and `to_ngsolve`;
  `Measures.symmetry` and `coordinate_names`; the two-vector velocity and the hoop terms of `flow.py` and of the
  prototype's kernel; `ngs.Id(2)` in `stabilisation.py` and `post/forces.py`; the axial direction as the second
  component in `post/forces.py` and as `ngs.y` in `post/indicator.py`.

The weak forms did not stop the trial; the measure and the mesh adapters did. Priced in §8.3's units:

| Option | Scope | Price |
|---|---|---|
| A. VER-13 in 3D | A planar 3D symmetry in `Measures` with `TET` rules, and the axisymmetric measure refused on a 3D mesh; the benchmark meshes with Netgen in its fixture, outside the 2D adapters (their refusal stands), and checks its convergence rate on three meshes, the error at each falling as the mesh is halved | One package after the kernel: about 3 sessions, 2 to 4 agent hours, 5 touches |
| B. A and VER-17 in 3D | A, and a 3D path in the mesher, the indicator current along a 3D axis, and a Newton solve of 260,406 unknowns at the coarsest size, whose direct factorisation is unmeasured | A, and about two more packages: 6 sessions, 5 to 10 agent hours, 10 touches, and machine time not known |
| C. Neither | CON-01 stays a statement no test can fail; this list is its record | None |

## The kernel's packages

Four packages, BC1's count, each pushed on the per-push selection (BA14), the last one holding the full check (BC4).
The prices come from measured work: the prototype composed the whole coupled model, 1,405 lines with its two scripts,
in 0.7 agent hours over two helpers and about 15 minutes of machine time; WP6.08, carried, took 1.5 agent hours and
4 touches, and WP6.06 3.3 agent hours and 5 touches. A kept package adds its tests, its review, its ship and CI to a
quick build, and writes the code anew.

| Package | Scope | Tier 1 | Tier 2 | Price |
|---|---|---|---|---|
| 1. The composition | `physics/kernel.py`: term, slot, contribution, `compose`; the coupled residual composed and today's body removed; the stabilisation reads the drifts and densities, and NUM-24's indicator current the drifts in force | A slot with two contributions assembles as one integral, where the term-by-term sum under a moved rule does not (the silent failure D3 exists for); a term left out changes its own slots alone | VER-14 to VER-18, VER-42 and VER-77 unchanged; VER-62's two push walks; VER-80 nightly | 3 sessions, 2 to 4 agent hours, 5 touches |
| 2. Switches as data and the forces | The switch records; `SWITCHES`, the switch paths and both deviation lists derived; the two refusals as `requires` and `excludes`; `post/forces.py` reads the densities (BC3); REV-298 as ruled | PHY-23's switch brings both terms or neither; each switch away from its default is a deviation in the manifest | VER-22's routes unchanged; VER-80's dielectric and log guards | 3 sessions, 2 to 4 agent hours, 5 touches |
| 3. A model as a list of terms | `pnp`, `pnp-ns` and `epnp-ns` as term lists; `poisson`, `pb` and `pb-linear` composed; the declaration's terms derived; `physics/models.py` split; the three moved names, the shell following | VER-56 restated: a model registered as a list of terms runs from a case file; the declaration's terms are those assembled | VER-12, VER-13 and VER-31 unchanged, the single-field models' checks | 3 sessions, 3 to 5 agent hours, 5 touches |
| 4. The full check | VER-62's seven walks and VER-80's six to 10⁻⁸ before the merge (BC4); VER-12 to VER-22, VER-31, VER-42 and VER-77 unchanged; §5.4.1's ruled reading written; MOD-10 closed | none new | the full check | 3 sessions, 2 to 3 agent hours, 4 touches |

Together about 12 sessions, 9 to 16 agent hours and 19 touches, against §8.3's 20 sessions, 12 to 24 agent hours and
32 touches for the kernel. The installed packages' package follows at its own price (BC5), and the 3D benchmark, if
ruled, after it.

## What the author rules

Each choice with its options; the recommendation first.

1. **The design**: term, slot, coefficient, switch record and model as above. *Approve* (recommended: the prototype
   held every mark, the operator to 2.1 × 10⁻¹⁶); approve with named changes; or redesign before any package.
2. **The decrement in the stabilisation's wind** (REV-300). *Keep it out*, as today, and say so in NUM-12's NOTE,
   which writes `b_i` without it (recommended: the approximate residual is already inexact, and the guard numbers
   hold today's operator); or read it, a re-pin of the stabilised modes under PHY-23 by ruling (G10).
3. **The kernel's packages.** *Four, as above* (recommended); three, with the full check folded into the third; or
   another cut the author names.
4. **MOD-10, §5.4.1's interface.** *The seam is the context, the slot and the measure*, with NGSolve's algebra in the
   terms until a second backend is planned (recommended: H3's argument stands); or the terms also read their operators
   from the context.
5. **REV-298, the log branch.** *A case key recorded as a deviation*, a switch record that excludes PHY-23
   (recommended: with switches as data it costs a record, and a run that takes the branch is then reproducible from
   its case file); or a library option that the manifest names.
6. **REV-67, the public registering names.** *One registrar handed to each entry point*, the registries private
   (recommended); or the `register_*` functions made public. The installed packages' package settles it (BC5).
7. **The 3D benchmark.** *Option A, VER-13 in 3D* (recommended: one package makes CON-01 a test that can fail);
   option B; or option C.

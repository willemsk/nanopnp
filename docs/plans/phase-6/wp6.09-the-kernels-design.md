# WP6.09 — The kernel's design

**Status: planned, not started.** Written 26 November 2026 on Fable 5.2 at high effort, grounded in the code at
`3cc0fbd`. Inherits §8.2.53 BC1, BC2, BC4 and BC5, this plan's rulings (§8.2.60 BJ1 to BJ3), §8.2.7 G10 and
§8.2.13 N1. Its last commit on `main` takes `v0.7.0-alpha.9` (§8.4.1).

The [Phase 6 plan](phase-6-library-foundations.md)'s WP6.09 entry sets this scope; `SPECIFICATION.md` governs, and
where it and this plan disagree this plan is wrong. Identifiers are pointers into it.

## In brief

**What changes.** Nothing a user runs. This package writes the design for rebuilding the core of the physics from
small registered pieces, and tries that design in a prototype that is thrown away. The prototype rebuilds the whole
coupled model, its optional settings included, and is checked three ways: against today's equations piece by piece,
against all thirteen stored reference runs, and against the tests that every push runs. The first worked example
must hold to one part in a hundred million. A short trial also measures what a 3D check of the model would cost. The
page ends with what you rule at the next round: the design, the kernel's packages and the 3D check.

**Cost.** About 3 sessions, 4 to 7 agent hours and 8 times you act, one of them to push the prototype's branch from
your computer if the session cannot.

**What could go wrong.** The prototype may miss the stored numbers. A miss on the first example comes to you before
any kernel package is planned; a miss elsewhere is reported at the round. The prototype is a quick build: where it
holds the numbers, it shows that the design can hold them, not that the kernel will. Its branch is never merged, so
its code survives only while that branch does. No rule of the specification changes until you rule.

**Your call.** Settled today: the prototype covers the whole model, the 3D price is measured, and the prototype
lives on a branch of its own. Still yours: approve this plan. *Recommendation:* approve; it changes no code a user
runs.

## Execution brief

Scope: the Phase 6 plan's WP6.09 entry (BC2, BC5; BJ1 to BJ3). The package delivers `docs/design/kernel.md` and the
records of a prototype kept on another branch. **Its own tree changes no file under `src/` or `tests/`.** It depends
on nothing unmerged. It discharges no requirement: it prepares FR-40, FR-20, QR-13 and QR-14, proposes answers to
MOD-10, REV-298 and REV-67, and meets the phase's criterion 5. No `OPN-` is open in this area.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| **D1 What the prototype rebuilds** | Every branch of `CoupledModel.residual_form`, composed from terms. `residual_form` is the composition; today's body stays beside it, renamed, for the comparison alone. The two Poisson–Boltzmann rungs and `poisson` keep today's code | Example 01's walk builds one class on six rungs (*Grounding*). Ruled by the author: the whole model (BJ1) |
| **D2 Where it lives** | The branch `prototype/wp6.09-kernel`, forked from `origin/main`, never merged. The session tries its push once; where refused, the author pushes a bundle. The package's branch is checked out at every hand-back and turn end. The pull request merges only once `origin` holds the sha the page names | Ruled by the author: a branch of its own (BJ3). `just land` and the stop hook read the checked-out branch (*Grounding*) |
| **D3 A term enters a slot, and a slot is integrated once** | A slot is one integral of one equation, with its domain and quadrature rule. A term is today's display `Term` with its contributions, each an expression added to one slot. The kernel sums a slot's contributions and integrates once. The slots are today's integrals; another partition is a re-pin by ruling | The engine sets each integral's rule from its trial and test functions, so a flux integrated term by term moves its quadrature (the physics reviewer at BC2; NUM-07's NOTE). G10. Decided by the plan |
| **D4 A shared coefficient, a switch as data, one expression** | The corrected properties are built once for an assembly and handed to each term; a correction stays its property's registered model (PHY-22). A switch is a record: name, case path, validated default, the terms it brings in force, what it requires and excludes. PHY-23's force and decrement stand under one switch (PHY-08). Each flux term's drift and each force term's density is written once: the weak form and the stabilisation read it in the prototype, the forces on paper | The physics reviewer's findings (BC2); today the ionic force is written three times and the drift twice. Decided by the plan |
| **D5 Pass marks, registered before any run** | (a) The composed operator equals today's on ten variants at one state, within 10⁻¹² of the largest entry. (b) Example 01's walk within 10⁻⁸; a miss stops the package and goes to the author. (c) The other twelve walks, reported; a miss is never tuned or re-recorded. (d) Example 02's walk without the steric term must miss. (e) The push gate's selection passes on the prototype's tree | (a) localises a miss to one integral (§7.1): round-off lies near 10⁻¹⁵, a moved rule above 10⁻⁷. (b), (c): BC2; BJ1. (d): the walks read the composition. (e): BC1. Decided by the plan |
| **D6 The 3D price** | One stretch on the prototype's branch: VER-13's cylinder meshed and solved in 3D with today's forms; VER-17's pore meshed and counted, not solved; each place that refuses or mishandles a 3D mesh. The page prices the benchmark in packages from these | Ruled by the author: measured, bounded (BJ2). VER-13 is one linear solve of one field |
| **D7 The page** | `docs/design/kernel.md`, in the site's Project section, about 3,500 words, a proposal. It amends no clause. It closes with each choice the author rules, as options with a recommendation: the design, the kernel's packages with their tests and price, MOD-10, REV-298, REV-67, the 3D benchmark | BC2; ADR-005, §5.4 and §5.5 are the round's. Decided by the plan |
| **D8 What the package's tree holds** | The page, the records and no code. A defect found in today's code is a `REV` row, not fixed here. No test is kept | The phase entry; BH1. Decided by the plan |

### Grounding

Read at `3cc0fbd`.

**D1**

- `examples/01-quickstart/quickstart.case.yaml` sets `physics.model: epnp-ns`, every switch at its default,
  `numerics.continuation: default_ladder` and `stabilisation: none`. `solve/continuation.py:default_ladder` builds
  rungs 1 and 2 with `create("pb-linear" | "pb", …)`, which solve through `physics/pb.py:solve_pb_recorded`, and
  every later rung through its local `_coupled`, which calls `create("pnp" | "pnp-ns" | "epnp-ns", …)`: one class,
  `physics/models.py:CoupledModel`.
- `residual_form` has two callers for a coupled model: `CoupledModel.solve` and `solve/state.py:restore`, which
  rebuilds the form of a stored state. A composition placed in it runs on every path.
- `physics/terms.py:Term` is display alone: `EPNP_NS_TERMS` holds twelve, read by `ModelDeclaration.terms` and
  the workbench; nothing assembles from them. `Term.switches` and `Term.correction` already say when a term is in
  force.
- `CoupledModel.__post_init__` refuses `dielectric_gradient_forces` beside `log_variables` or without `flow`;
  `physics/nernst_planck.py:excess_potential_gradient` and `physics/flow.py:permittivity_gradient` raise in the
  log branch.

**D2**

- `.claude/scripts/land.sh` lands `git branch --show-current`; `~/.claude/stop-hook-git-check.sh` tests `HEAD`
  alone for unpushed commits. A local branch that is not checked out trips neither.
- `.claude/hooks/gate.sh` gates each `git commit` on any branch, and lets a push through only where
  `gate.sh run` stamped its tree. `.github/workflows/tag.yml` records that a cloud session's credentials push its
  own branch alone.
- The package's tree changes no `src/`, so `origin/main` holds the same code as the package's branch.

**D3**

- Today's integrals of `CoupledModel.residual_form` and `_flow_residual`, one `Measures.volume` or `surface`
  call each, in order: Poisson's stiffness on Ω (`poisson_operator`); the mobile charge on the fluid and the fixed
  charge under `FixedCharge.rule_order` (`charge_source`); the surface charge (`surface_charge_term`); for each
  species the flux (`nernst_planck_residual` of `species_flux`), then the mode's streamline and crosswind integrals;
  the viscous term and the hoop term (`viscous_operator`, the second `singular`); the pressure and the continuity
  (`singular`); the inertia; the ionic force (`electrical_body_force`); the mean-pressure constraint; PHY-23's
  force (`dielectric_gradient_force`); the mode's three flow integrals; one source for each field.
- `species_flux` sums the diffusion, the migration, the steric part, the decrement and the advection into one
  bracket and negates it once. The flow block is up to eleven integrals, not one.
- `numerics/measures.py:Measures.volume` passes `bonus_intorder` or `intrules` for each call;
  `knowledge/06-numerics-fem/02-axisymmetric-weak-forms.md` records that the engine estimates the order from the
  trial and test functions.

**D4**

- `physics/coefficients.py:NondimensionalCoefficients` is built once in `residual_form`, and once more for the
  lagged state; its `__post_init__` builds the driver once for every property.
- The ionic force `−S ρ ∇φ` is written in `flow.py:electrical_body_force`, `CoupledModel._flow_state` and
  `post/forces.py:_integrands`. PHY-23's force is written in the same three, on one `permittivity_gradient`. The
  inertia is written in `flow.py:inertia_term`, `stabilisation.py:momentum_residual` and
  `forces.py:_domain_force`.
- `stabilisation.py:advective_velocity` writes the migration, the steric part and the advection again, and leaves
  out the decrement.
- `physics/models.py:SWITCHES` is read by `pipeline/checks.py:_check_physics_switches`, `api/project.py` and
  `gui/web/physics_tools.py` and `screens.py`; `io/defaults.py:SWITCH_PATHS` holds the same four once more.
  `CoupledModel._deviations` and `io/defaults.py:deviations` each list the deviations.
- The workbench imports nine names: `SWITCHES`, `Term`, `case_model`, `declaration` and `role_conditions` of
  `physics.models`; `CONDITIONS`, `Symbol`, `symbols_in` and `written` of `physics.terms`.
- `src/` has nine registries, and `core/public.py:PUBLIC` holds `register_model` and `registered_models` of them.
  No entry point is declared in `pyproject.toml`, and nothing reads one.

**D5**

- `validation/mms.py:ManufacturedSolution.polynomial(model).coefficient_functions()` returns smooth fields by
  field name; `tests/tier2/test_mms.py` builds its model, mesh and `BOUNDARIES`.
- `form.Apply(state.vec, out)` and `form.AssembleLinearization(state.vec)` are how `post/reaction_flux.py` and
  `PoissonModel.solve` read a form; `form.mat.AsVector().FV().NumPy()` is `tests/tier1/test_library_behaviour.py`'s.
- WP6.08's plan, item 2, holds the command of the thirteen walks: 295 s with `-n auto`, each guard walk repeating
  to 0.000e+00 and example 01's to 6.9e-14. The guard walks run only in `linux-x86_64/X86_V3`, the gate's cap.
- Example 01's pore is uncharged, so its numbers barely read the steric term; example 02's ePNP-NS walk,
  `tests/tier2/test_examples_02_epnpns.py`, runs on every push and has a charged wall.

**D6**

- Every `OCCGeometry` call of `mesh/` and `geometry/` passes `dim=2`; `mesh/adapter.py:from_ngsolve` refuses a
  mesh with a third coordinate (CON-04).
- VER-13, `tests/tier2/test_electrostatic_benchmarks.py:test_ver13_debye_huckel_in_a_cylinder`, calls
  `solve_pb_recorded(mesh, AXISYMMETRIC, debye_length_nm=0.5, dirichlet="wall", boundary_values=ngs.CF(1.0),
  nonlinear=False)` on a cylinder of radius 2 and length 4. Its forms take any `Measures`; `PLANAR` has weight 1.
- VER-17, `tests/tier2/test_access_conductance.py`, solves `pnp` on `mesh_cylinder_pore(CylinderPore(…),
  maxh_nm=reservoir_radius_nm / 12, wall_h_nm=0.5)`, reservoir radii 50 and 100 nm.
- `Measures.volume` builds an explicit rule for `SEGM`, `TRIG` and `QUAD` alone; `physics/stabilisation.py`
  writes `ngs.Id(2)` and `physics/flow.py` a two-vector; `Measures.symmetry` has two values.
- Context7, NGSolve: `netgen.occ.Cylinder((0, 0, 0), Z, r=…, h=…)`, `shape.faces`, `face.name`,
  `OCCGeometry(shape).GenerateMesh(maxh=…)`, `ngs.Mesh(…).Curve(order)`.

**D7**

- `mkdocs.yml`'s Project section lists `Workbench design: design/workbench.md`; `docs/design/` is a documentation
  source, so `uv run just docs` builds it. `docs/scripts/generate.py` and `index_records.py` index no design page.
- MOD-10 is a row of `docs/project/modularity-findings.md` with its section in `modularity.md`; REV-298 and REV-67
  are rows of `review-findings.md` with sections in `review-items.md`.

### Implementation details

**The two branches.** `<package>` is the package's branch. Work on the prototype between `git checkout
prototype/wp6.09-kernel` and `git checkout <package>`, with a clean tree at each. A prototype commit is `chore:
prototype, <what>`, under the commit hook, whose ruff reads `prototype/` too, and is never cherry-picked. An item on
the prototype is ticked on `<package>` with the prototype commit's sha.

**Item 1, the kernel.** `git fetch origin main`, then `git checkout -b prototype/wp6.09-kernel origin/main`.

- `src/nanopnp/physics/kernel.py`. `Slot`: name, the field whose test function it takes, `volume` or `surface`,
  domain, `singular`, `extra_order`, `rule_order`, and a function that closes the summed contributions into the
  integrand (the flux slot negates the bracket and takes its product with the test function's gradient).
  `Contribution`: a slot's name and a function of the context that returns an expression or nothing.
  `KernelTerm`: a display `Term` and its contributions. `Switch`: D4's record. `Context`: the trial, test and
  lagged functions, the concentration variables, the coefficients, the measures, the mesh, the fluid, the solid
  blend, the species at hand and the model. `compose(terms, slots, context)`: the sum over the slots, in order,
  of one integral each; a slot with no contribution is left out.
- A term is in force when each of its display `Term`'s switches is true on the model and its correction leaf is
  not `none`. A term whose name is in the environment variable `NANOPNP_PROTOTYPE_DROP` is left out.
- `physics/models.py`: `CoupledModel.residual_form` builds the context and returns `compose(…)`; its body and
  `_flow_residual` stay as `_reference_residual_form` and `_reference_flow_residual`. The constraint, the sources
  and the stabilisation's integrals are contributions of the model, with no display `Term`.
- `prototype/compare_operators.py`, run as `uv run python prototype/compare_operators.py`. The mesh is
  `CylinderGeometry(radius_nm=2.0, length_nm=4.0).generate(maxh_nm=0.4)`, with `BOUNDARIES` and `fluid` as
  `tests/tier2/test_mms.py` has them. The fields are those of `ManufacturedSolution.polynomial` on that test's
  model, set on each component of the variant's state; the log branch takes their logarithm. Each variant is
  called with `wall_distance_nm = 2.0 − r`, a `FixedCharge` of a smooth density at `rule_order=8`, a surface
  charge on `wall`, a smooth source for each field and `state=`.
- The ten variants: `epnp-ns` at its default; then one change each: `dielectric_gradient_forces=True`, with no
  solid fraction (`materials/fields.py:nearest_solid_permittivity` refuses a mesh with no solid, so the blend's
  branch is not compared, and the page says so); `log_variables=True`; `stabilisation="reference"`; `"supg"`;
  `variable_density=False`; `inertia=False`; `pressure_constraint=True`; then `pnp-ns` and `pnp`.
- For each it prints `max|new − old| / max|old|` of the residual vector and of the Jacobian's entries, and
  exits 1 above 10⁻¹². With `--slots` it prints the residual's difference for each slot composed alone.

**Item 2, one expression.** On the prototype: each flux term states its drift, and each force term its density.
`stabilisation.py:advective_velocity` and `CoupledModel._flow_state` read them from the terms in force; the
decrement stays out of the drift, as today. `post/forces.py` is not edited.

**Item 4, the trial.** `prototype/three_d.py`, on the prototype, one stretch.

- VER-13 in 3D: the cylinder of *Grounding* D6 with its lateral face named `wall`, at `maxh=0.4`, curved to
  order 2, solved by the call of *Grounding* D6 under `PLANAR`. It prints the unknowns, the seconds and the
  relative error against `I₀(r/λ)/I₀(a/λ)` along a radius at mid-height, and the same error on VER-13's 2D mesh.
- VER-17's fluid in 3D: the pore and its two reservoirs at 50 nm, at the test's sizes. It prints the elements
  and three times the unknowns of an order-2 `H1` space. No solve.
- The list of *Grounding* D6, completed by a search of `src/` for what is written for two dimensions.

Whatever the stretch does not reach is reported as not reached.

**Item 5, the runs.** Each with the prototype checked out, `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS` and
`MKL_NUM_THREADS` at 1 and `NPY_DISABLE_CPU_FEATURES="X86_V4 AVX512_ICL AVX512_SPR"`, its log under the git
directory; under `/np-carry` each is a `RUN` whose command checks the prototype out first and `<package>` last.

1. The thirteen walks: the command of WP6.08's plan, item 2, to `wp609-walks.log`.
2. The control: `NANOPNP_PROTOTYPE_DROP="Steric flux" uv run pytest tests/tier2/test_examples_02_epnpns.py -q`,
   to `wp609-control.log`. It must fail on its stored numbers.
3. The gate: `.claude/hooks/gate.sh run`, to `wp609-gate.log`, closed by `echo "exit $?"`.

The Outcome under item 5 holds each walk's largest drift, its mode and its stabilisation mode, the control's
drift, the gate's counts and time, and the prototype's sha. Example 01 above 10⁻⁸, or a control that passes,
stops the package: `BLOCKED`, with the log.

**Item 6, the hand-over.** Item 5's gate stamped the head's tree, so `git push -u origin prototype/wp6.09-kernel`
goes through the hook; try it once. If it is refused, `git bundle create "$(git rev-parse
--git-dir)/wp6.09-prototype.bundle" origin/main..prototype/wp6.09-kernel`; the main session sends the author the
file with these commands and asks whether it is pushed:

```bash
git fetch <the bundle> prototype/wp6.09-kernel:prototype/wp6.09-kernel
git push --no-verify origin prototype/wp6.09-kernel
```

`--no-verify`: the author's clone has no stamp for a tree that the session gated.

**Item 8, the page.** `docs/design/kernel.md`, and its line under `Workbench design` in `mkdocs.yml`. Sections, in
order: what the page is and who rules it; the kernel in brief (term, slot, coefficient, switch, model); today's
integrals as slots, a table; coefficients and corrections; switches as data and PHY-08's rule; one expression and
its three readers; a model as a list of terms, a variant as a difference, the single-field models, and what
`physics/models.py` and `default_ladder` become; the nine names, each kept, moved or derived; installed packages
(`importlib.metadata.entry_points(group="nanopnp.extensions")`, read at the first use of a registry, each named
in the manifest with its package and version, a term with no analytic case marked unverified); §5.4.1's
interface; what the prototype showed (D5's five marks, with the branch, its sha, the commands and each mode);
the 3D benchmark's price; the kernel's packages, each with its Tier 1 and Tier 2 tests and its price in §8.3's
units, set from the prototype's measured hours; what the author rules. Where the prototype contradicted D3 or
D4, the page says so and proposes what held.

**Item 9, the records.** A section of `knowledge/06-numerics-fem/09-ngsolve-traps-found-by-implementing.md` on
what a composed residual must keep, each claim `[verified]` with the prototype's sha and log, with the index line
and `knowledge/log.md`; a `**Proposed**` line under MOD-10, REV-298 and REV-67 that links the page; a `REV` row
for each defect found; `CHANGELOG.md`'s `## [0.7.0-alpha.9]`; `holds-now.yaml` (BJ1 to BJ3 `spent`; BC2's
`open:` names the round alone); this plan's status and Outcomes; the Phase 6 plan's entry and criterion 5;
`docs/plans/current.md`.

### Work items

- [ ] 1. On the prototype: `src/nanopnp/physics/kernel.py`, `src/nanopnp/physics/models.py`,
  `prototype/compare_operators.py`: the composition and the comparison (D1, D3 to D5); done when it prints ten
  variants within 10⁻¹², or names each slot above it with what was tried. **Executor:** main
- [ ] 2. On the prototype: `src/nanopnp/physics/stabilisation.py`, `src/nanopnp/physics/models.py`,
  `src/nanopnp/physics/kernel.py`: the drift and the force density read from the terms (D4); done when the
  comparison's result is unchanged. **Executor:** main
- [ ] 3. Compaction checkpoint. **Executor:** main
- [ ] 4. On the prototype: `prototype/three_d.py`, and its printed result as this plan's Outcome (D6); done when
  each of its three results is printed or reported as not reached. **Executor:** main
- [ ] 5. The three runs of D5 on the prototype's head, and their Outcome in this plan; done when the log lists
  thirteen walks with example 01 within 10⁻⁸, the control fails and the gate's log ends `exit 0`. **Executor:**
  main, the runs by the main session
- [ ] 6. The hand-over of the prototype's branch (D2); done when `git ls-remote origin
  refs/heads/prototype/wp6.09-kernel` prints the sha the Outcome names. **Executor:** main, the push by the author
  where the session's is refused
- [ ] 7. Compaction checkpoint. **Executor:** main
- [ ] 8. `docs/design/kernel.md`, `mkdocs.yml`: the page (D7); done when `uv run just docs` passes and the code and
  review say so. **Executor:** main
- [ ] 9. `knowledge/06-numerics-fem/09-ngsolve-traps-found-by-implementing.md`, `knowledge/06-numerics-fem/index.md`,
  `knowledge/log.md`, `docs/project/modularity.md`, `docs/project/review-items.md`,
  `docs/project/review-findings.md`, `CHANGELOG.md`, `specification/history/holds-now.yaml`, this plan, the Phase 6
  plan, `docs/plans/current.md`: the records (D8); done when the code and review say so. **Executor:** main

### Verification

No test is kept (N1). The prototype's checks run on its branch and are reported with its sha:

| Check | Tier | Identifier | Oracle | Tolerance source | Command |
|---|---|---|---|---|---|
| The operator comparison, each variant at a state set from the manufactured fields | none | PHY-05, PHY-08, PHY-23, NUM-02, NUM-07, NUM-11, NUM-14 | Today's `residual_form`, kept beside the composition: the residual vector and the Jacobian's entries | 10⁻¹² of the largest entry (D5) | `uv run python prototype/compare_operators.py` |
| The thirteen walks, each through its own test | 2 | VER-62, VER-80 | `tests/tier2/data/number_stability.json` as `main` holds it, through the `number_stability` fixture | 10⁻⁸ relative; example 01's is the pass mark (BC2; BJ1) | item 5, run 1 |
| The control | 2 | VER-62 | Example 02's ePNP-NS walk without the steric term fails on its numbers | 10⁻⁸ relative, exceeded | item 5, run 2 |
| The per-push selection | 1, 2 | VER-12 to VER-22, VER-31, VER-42, VER-77 | Each test as `main` holds it | each test's own (BC1) | item 5, run 3 |
| VER-13 in 3D | none | VER-13; CON-01 | `ζ I₀(r/λ)/I₀(a/λ)`, beside the 2D mesh's error; gates nothing | none (BJ2) | `uv run python prototype/three_d.py` |

The package's own tree: the push gate and `uv run just docs`; the page and records, the review (N3).

### Out of scope

- Building the kernel, and BC4's full check: the kernel's packages, numbered at the round.
- Rewriting ADR-005, §5.4 and §5.5, closing MOD-10, REV-298 and REV-67, a case key for the log branch, and the 3D
  benchmark's ruling: the round on the design, `/np-plan amend 6`.
- `post/forces.py` reading the terms, and the single-field models as compositions: the kernel's packages.
- Finding an installed package's registration: the installed packages' package (BC5).
- A defect found in today's code: its `REV` row's owner.
- Merging the prototype: never; the kernel's packages write their code anew.

### Open questions

None. BJ1 to BJ3 settle D1, D2 and D6.

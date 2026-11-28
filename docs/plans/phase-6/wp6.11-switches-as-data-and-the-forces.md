# WP6.11 — Switches as data and the forces

**Status: delivered, 28 November 2026.** Each switch is a record of `io/switches.py`: name, case path, validated
default, the terms it brings in force, `requires` and `excludes` (D1; FR-40 in part; §5.4.4). Every list of switches,
the validated default, the deviations, the case checks, the ladder's refusal and the terms in force read the records;
`physics.models.SWITCHES` and `Term`'s field are gone (D3; BL1). NUM-02's log branch is the fifth record, the case key
`numerics.log_variables`, which excludes PHY-23's switch, is a deviation in the manifest and is refused by the ladder
(BL7; BM1 to BM3; FR-25; REV-298 fixed). `post/forces.py` reads the kernel's force densities (NUM-28). VER-82, new,
Tier 1, and VER-81 (c)'s force split pass; eight variants' forces hold to 2.6 × 10⁻¹⁶ (item 4) and the six guard
walks to 5.0 × 10⁻¹⁶, `guard-log` entered by the key (item 5). Live: `CoupledModel` holds the three coupled models
until WP6.12; the ladder does not carry the log branch (BM2); REV-302.

Written 28 November 2026 by Fable 5.2 at high effort, on the code at `e42272a`.
Inherits §8.2.62 BL1, BL2 and BL7, §8.2.63 BM1 to BM3, [the kernel's design](../../design/kernel.md),
[WP6.10](wp6.10-the-composition.md)'s kernel, REV-298 and the test scope (§8.2.13 N1). Its last commit on `main`
takes `v0.7.0-alpha.11` (§8.4.1).

The [Phase 6 plan](phase-6-library-foundations.md)'s WP6.11 entry sets this scope. `SPECIFICATION.md` governs:
where they disagree this plan is wrong, and identifiers are pointers into it.

## In brief

**What changes.** Each on-off setting of the model becomes one record: its name, where a case file sets it, its
validated value, the pieces of the equations it brings in, and what it needs or forbids. Every list of settings
in the program is read from the records, so no part can forget one. A case file gains one setting: solving for
the logarithm of each ion concentration, a numerical fallback that only a script could reach until now and that
a run's record never named. It is off by default, excludes the optional dielectric forces, and a run that uses it
says so in its record. As you ruled, it sits with the numerical settings, the workbench shows it, and the stepwise
start refuses it. The force on a particle is computed from the equations' own statements of the forces. At the
default settings no number changes, and results already computed stay valid.

**Cost.** About 3 sessions, 2 to 4 agent hours and 5 times you act. The package before took 1 session, 4.0 agent
hours and 7.

**What could go wrong.** A record could name a piece wrongly, and the piece be assembled when it should not: a
test checks every combination of settings against a table written by hand. The force could shift: it is stored
on eight variants before the change and compared after, and its three routes must still agree. The stored run on
the logarithm is repeated through the new setting.

**Your call.** Do you approve this plan? *Recommendation:* approve; it holds your three answers and leaves no
decision open.

## Execution brief

Scope: the switch records with the log branch's case key, every list derived from them, and `post/forces.py`
reading the force densities. Nothing unmerged is needed.

It discharges FR-40 in part and FR-25 for the log branch, and fixes REV-298. It claims **VER-82**, new, Tier 1,
and amends VER-81 (c), VER-80, NUM-02, NUM-18's NOTE, §5.3.1, the NOTEs of §5.4.3 and §5.4.4 and Appendix A's
FR-40 row, each in the item that builds it. The phase plan's open decision 20 is D1 and D2.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| **D1 The records and their home** | `io/switches.py` holds a `Switch` for each of five switches: name, case path, validated default, terms, `requires` and `excludes`, with the functions that read them | `io/defaults.py` derives its lists at run time, and `io` imports `core` alone (VER-61). Decided by the plan |
| **D2 The log key's path** | `numerics.log_variables`, a Boolean, the physics model's file owning it | Ruled by the author, BM1; BL7 |
| **D3 Every list derived** | `physics.models.SWITCHES`, `Term`'s `switches` field, the model switches' rows of `SWITCH_PATHS`, `MODEL_SWITCH_PATHS` and the validated default, `_LADDER_PHYSICS` and `CoupledModel._deviations` are deleted or derived; `Term.switches` is a property. No alias | Ruled by the author, BL1 ("readers take the switch records"); §5.4.4 |
| **D4 In force** | A term is in force when each record naming it is true, with each switch those records require. One record names PHY-23's two terms, none one alone. `conflicts` refuses at the model's construction and at the case check | §5.4.4; PHY-08, PHY-23. Decided by the plan |
| **D5 The log branch beside the ladder** | Refused, as each switch the ladder does not read; `numerics.continuation: none` runs it | Ruled by the author, BM2; NUM-18's NOTE |
| **D6 An existing case keeps its keys** | At `false` the key is left out of the case artefact's parameters and of `model_options`; the model record's `switches` keeps its seven names | The keys `tests/tier1/test_model_interface.py` pins hold, as with an untyped part size. Decided by the plan |
| **D7 The workbench** | The Equations tool lists the records' switches, the fifth as "Log concentrations" | Ruled by the author, BM3 |
| **D8 The forces read the densities** | The hydrodynamic half's consistency term is the sum of the densities in force; the electromagnetic half's is the ionic and the dielectric density, in force or not; the omitted term is zero while its term is in force | §5.4.4's Term rule; NUM-28. Decided by the plan |
| **D9 A moved number** | Predicted: none. The forces of eight variants are stored before the edit and equal after within 10⁻¹²; the stored walks hold 10⁻⁸ | Ruled by the author, BL2; no stored walk holds a force |
| **D10 A force the log branch cannot give** | `analyte_force` beside the key is refused at resolution where the permittivity's concentration fit applies | It fails today after the solve. Decided by the plan |
| **D11 The clauses** | VER-82, Tier 1, `tests/tier1/test_switches.py`; VER-81 (c) gains the forces; VER-80's `guard-log` enters by the key | §5.4.4's tests. Decided by the plan |

### Grounding

Verified at `e42272a`.

**D1**

- Each module of `io/` imports `core` alone at run time; `io/resolved.py` names `ModelDeclaration` under
  `TYPE_CHECKING`. `physics`, `pipeline`, `api`, `gui` and `post` each hold a `static` edge to `io` in
  `modularity-layering.yaml`: no row moves.
- `physics/terms.py:EPNP_NS_TERMS` names switches on eight display records: `("flow",)` on Advection, Momentum,
  Velocity continuity and Body force; `("flow", "inertia")` on Inertia; `("flow", "variable_density")` on Variable
  density; `("flow", "dielectric_gradient_forces")` on Dielectric decrement and Dielectric-gradient force.
  `PNP_NS_TERMS` repeats five under the same names and tuples; `PNP_TERMS` and the single-field lists name none.
- The design page's table leaves Variable density out of `flow`'s terms. The record names it: without it the term
  would be in force with the flow off.

**D2**

- `io/case.py:Physics` holds the four switches, and `Numerics` holds `stabilisation` and `continuation`.
  `io/models.py:OWNERS` gives `physics`, `numerics.elements`, `numerics.stabilisation` and
  `numerics.wall_distance` to the physics model's file; a `numerics` leaf with no row is the study's.
- `CoupledModel.log_variables` is read by `concentration_variables`, `cold_state`, `_apply_essential`,
  `ModelSolution.concentration`, `solve/continuation.py:transfer`, `post/export.py` and the descriptor's space key
  `model.switches.log_variables`. `tests/tier2/test_guard_numbers.py:_run_log` reaches it by replacing
  `ResolvedCase.model_options`.
- A new leaf needs a row in `validation/case_leaves.py:LEAVES` and in
  `tests/tier1/test_case_leaves.py:SOLVE_PROBES` (VER-71), and its path in `SWITCH_PATHS`
  (`tests/tier1/test_manifest.py`). `cli/reference.py` writes the case reference from the schema's walk.

**D3**

- `physics/models.py:SWITCHES` is read by `ModelDeclaration.__post_init__`, the coupled declarations,
  `pipeline/checks.py:_check_physics_switches`, `api/project.py` (the choice of a model), `gui/web/screens.py`
  (the Equations tool's paths) and `gui/web/physics_tools.py`, twice. Each reader outside `physics/` builds the
  path as `f"physics.{switch}"`.
- `Term.switches` is read by `CoupledModel._in_force`, `ModelDeclaration.__post_init__`,
  `gui/web/physics_tools.py:term_state` and `tests/tier1/test_model_interface.py`. `terms.py` passes it in nine
  constructions, positionally in each.
- `io/defaults.py`: `SWITCH_PATHS` lists the four paths, `MODEL_SWITCH_PATHS` them and the steric leaf, and
  `_VALIDATED_DEFAULTS["physics"]` their defaults. `deviations(document)` walks `SWITCH_PATHS` and is the
  manifest's list (`io/manifest.py`). `CoupledModel._deviations` writes the four and the steric leaf again and
  omits the log branch.
- `gui/web/physics_tools.py:lead` walks `declared.switches` and indexes `FIELDS[f"physics.{each}"]`; other
  readers of `FIELDS` fall back to the path.

**D4**

- `CoupledModel._in_force` decides from `display.switches`, the steric leaf and three rules for the terms with no
  display record. `CoupledModel.__post_init__` refuses the dielectric forces with the log branch and without the
  flow; its refusal of `pressure_constraint` without the flow is of no switch and stays.
- `_check_physics_switches` refuses the dielectric forces without the flow before it checks the honoured values,
  its remedy read from `declared.switches["flow"]`. `tests/tier1/test_physics_models.py` asserts the model's
  refusal of the log branch by `match="log branch"`; no test asserts its refusal without the flow.
- `ModelDeclaration.switches` must hold exactly `SWITCHES`' names, so six declarations gain the fifth.

**D5**

- `pipeline/checks.py:_LADDER_PHYSICS` fixes the four switches, and `_check_ladder_can_honour` refuses a case away
  from it. `solve/continuation.py:default_ladder` builds its coupled rungs in `_coupled`, with no `log_variables`;
  `transfer` and `cold_state` already convert between the branches.
- `tests/tier1/test_case_schema.py:test_fr25_a_switch_the_ladder_cannot_honour_is_refused_not_dropped` asserts
  the refusal for each of the four switches: the message holds the switch's path and
  `numerics.continuation: none`.

**D6**

- `io/artefact.py:CaseArtefact` hashes the whole validated dump, and deletes `numerics.mesh.sizes` where none is
  typed. `pipeline/case.py:_model_options` feeds `ResolvedCase.provenance["model_options"]`, and so the solve key.
- `tests/tier1/test_model_interface.py` pins `SOLVE_HASHES`, five solve keys, and `RUNG_HASHES`, the digest of
  each rung's model provenance.
- `CoupledModel.provenance["switches"]` holds `flow`, `variable_density_flow`, `inertia`, `steric`,
  `dielectric_gradient_forces`, `log_variables` and `pressure_constraint`. `solve/state.py` gates a restore on
  them, so a renamed key refuses a state stored under an unchanged solve key.

**D8**

- `post/forces.py:_integrands` writes the ionic force and the dielectric force again, the second in three
  branches, and `_domain_force` the inertia. `_domain_force` and `_dielectric_gradient_residual` branch on
  `model.dielectric_gradient_forces` and `model.inertia`. The callers of `_integrands` are `domain_force`,
  `surface_force`, `dielectric_gradient_residual` and `extract`, and each holds `measures`.
- `CoupledModel.context` sets `Inputs.solid` only under the dielectric switch. The forces blend whenever a solid
  fraction is given, the switch on or off (PHY-23's NOTE).
- `flow.py:dielectric_force` returns `None` where the permittivity does not vary and no blend is given, and
  `permittivity_gradient` raises `NotImplementedError` on the log branch where it varies. Today
  `_Integrands.korteweg` raises it when the domain route integrates, and the surface route never asks.
- `Measures.integrate` takes a fixed order, so one integral of a sum equals the integrals apart to round-off.
- Measured at this commit on a sphere in a box (`AnalyteInBoxGeometry`, radius 2 nm in 12 nm, `maxh_nm=1.5`,
  `wall_h_nm=0.4`, 383 elements) at a smooth state: the two halves and the omitted term, computed from the
  kernel's densities, equal today's within 6.4 × 10⁻¹⁶ on six variants, a solid fraction with the switch off among
  them. The mesh takes 0.03 s and a variant 0.1 s. The inertia moves the hydrodynamic half by 1.2 × 10⁻⁷ there.
- `tests/tier2/test_force_routes.py` (VER-22) solves `pnp-ns` with no inertia and a constant density, and runs in
  under 20 s. The corrected case of `tests/tier2/test_force_convergence.py` is `slow`.
  `tests/tier2/data/number_stability.json` holds no force.

**D10**

- `pipeline/checks.py:_check_switch_partners` holds the predicate: the model reads
  `electrolyte.corrections.permittivity.concentration`, it is true, and `applies_part(model, "permittivity",
  "concentration")`. `_check_outputs` is where an output is refused.

### Implementation details

**Item 1, the records.** `io/switches.py` imports nothing of the package.

- `Relation(switch, why)`. `Switch(name, path, default, terms=(), requires=(), excludes=())`, the last two tuples
  of `Relation`. `Conflict(switch, kind, other, why)`, `kind` being `requires` or `excludes`.
- `SWITCHES`, in this order:

| `name` | `path` | `default` | `terms` | `requires` | `excludes` |
|---|---|---|---|---|---|
| `flow` | `physics.flow` | true | Advection, Momentum, Inertia, Velocity continuity, Variable density, Body force | | |
| `variable_density` | `physics.variable_density` | true | Variable density | | |
| `inertia` | `physics.inertia` | true | Inertia | | |
| `dielectric_gradient_forces` | `physics.dielectric_gradient_forces` | false | Dielectric decrement, Dielectric-gradient force | `flow` | |
| `log_variables` (item 2) | `numerics.log_variables` | false | none | | `dielectric_gradient_forces` |

- Each `why` is today's reason: for `flow`, that PHY-23 adds the force on the fluid and the term in each ion's
  flux together; for the exclusion, that `d(eps~_r)/d(c~_i)` would be differentiated in `w_i`. The model's
  message for the exclusion keeps the words "log branch", which the test matches.
- `switch(name)`, a `KeyError` naming the records; `switch_at(path)`, or `None`; `governing(term)`, the records
  that name the term and those they require, in `SWITCHES`' order; `in_force(term, values)`, every governing
  record true; `conflicts(values)`, a `Conflict` for each record that is true with a required one false or an
  excluded one true; `away(values)`, the records off their default. A name `values` lacks takes its default.
- `physics/terms.py`: `Term` loses the field; `Term.switches` returns the names of `governing(self.name)`.
- `physics/models.py`: `SWITCHES` leaves the module and `__all__`. `CoupledModel.switch_values()` maps each
  record's name to the attribute of that name. `_in_force` calls `in_force`, and keeps the steric leaf and the
  three rules. `__post_init__` raises a `ValueError` with the `why` of each of `conflicts`; its refusal of the
  log branch stays as written until item 2's record states it. `_deviations` is the paths of `away`, and the
  steric leaf. `ModelDeclaration.__post_init__` compares with the records' names.
- `io/defaults.py`: the records' paths stand where the four rows stood in `SWITCH_PATHS`; `MODEL_SWITCH_PATHS`
  is their set with the steric leaf; each record's default is written into `_VALIDATED_DEFAULTS` at its path.
- `pipeline/checks.py`: `_check_physics_switches` reads each value by `value_at(document, record.path)`, refuses
  each of `conflicts` first, with today's remedy by `declared.switches`, then the honoured values.
  `_check_ladder_can_honour` refuses the paths of `away`. `pipeline/case.py:_model_options` reads each record
  the declaration lists as an option.
- `api/project.py` and the two `gui/web` modules import `SWITCHES` from `io.switches` and use `record.path`; a
  label is `FIELDS[path].label`, else the path.

**Item 2, the key.**

- `io/case.py`: `Numerics.log_variables`, a Boolean, default false, with a description that names NUM-02.
  `io/models.py:OWNERS` gives `numerics.log_variables` to `physics`.
- `io/artefact.py:CaseArtefact` deletes the key from its parameters where it is false. `_model_options` passes
  `log_variables` only where it is true; `_COUPLED_OPTIONS` gains it.
- The declarations: `(False,)` for `pb`, `pb-linear` and `poisson`; both values for `epnp-ns`, `pnp-ns` and `pnp`.
- `_check_outputs` refuses `analyte_force` beside the key under D10's predicate, naming both keys.
- `gui/web/tools.py:FIELDS` gains the path as `Field("Log concentrations", "switch")` (D7).
- `tests/tier2/test_guard_numbers.py`: `_run_log` goes; `guard-log` runs `_run` with `SINGLE_RUNG` and the key,
  and asserts the key's path among those of `result.manifest.deviations`.
- NUM-02: the flag is the case key, a switch record that excludes PHY-23's switch and is a deviation. NUM-18's
  NOTE: the ladder reads no switch record, and refuses a case that sets one off its default. §5.3.1: the key in
  both listings, and its NOTE. VER-80: `guard-log` enters by the key.

**Item 4, the forces.** Keep the script and its file in `"$(git rev-parse --git-dir)/wp6.11/"`, uncommitted.

- The script builds *Grounding* D8's mesh with `solid_permittivities={"analyte": 20.0}`, sets a smooth state as
  `tests/tier1/test_kernel.py:_coupled_state` does, and writes `em_N`, `hd_N` and
  `dielectric_gradient_residual` of `epnp-ns` for eight variants: the default; `inertia=False`;
  `variable_density=False`; `dielectric_gradient_forces=True`; a solid fraction with its gradient, the switch off
  and on; `pnp-ns`; and `log_variables=True` with the permittivity model `none`. The extension is any smooth
  `VectorH1` function on the fluid. Run it before the first edit, then with `--against`.
- `_integrands(solution, measures, wall_distance_nm)` builds `model.context(mesh, measures, trial=...,
  wall_distance_nm=..., solid_fraction=..., solid_fraction_gradient=...)` and replaces `inputs.solid` with
  `model.solid_blend(...)`. `_Integrands` keeps the context, the stresses' fields and the two permittivities, and
  loses `body_force`, `korteweg_force`, `mass_density`, `reynolds` and `korteweg`.
- `physics/coupled.py` exports `BODY_FORCE`, `DIELECTRIC_FORCE` and `term(name)`.
- `_domain_force`: the ionic work is `∫ f·w` of `term(BODY_FORCE).force(context, context.trial)`, the dielectric
  work that of `term(DIELECTRIC_FORCE)`'s, zero where it is `None`; `em_N` subtracts both. `hd` adds the work of
  `kernel.force_density(context, context.trial)`. The omitted term is zero where `DIELECTRIC_FORCE` names a term
  of `context.terms`. Only the domain route asks for the dielectric density.

**The run (item 5).**

```bash
NPY_DISABLE_CPU_FEATURES="X86_V4 AVX512_ICL AVX512_SPR" \
  OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 \
  uv run pytest --slow tests/tier2/test_guard_numbers.py tests/tier2/test_force_convergence.py \
  -q -rsfE -n auto --dist loadfile > "$(git rev-parse --git-dir)/wp6.11/run.log" 2>&1
```

The cap is the gate's (`.claude/hooks/gate.sh`; §7.6): without it an AVX-512 host is not the reference
environment, and the guard walks skip (BI2).

> **Outcome — the first run skipped the guard walks.** On `2d7936d`, without the cap, on a
> `linux-x86_64/AVX512_SPR` host: `test_force_convergence.py` 5 passed, the six guard walks skipped, 104 s.
> The guard walks run again under the cap.

> **Outcome — the guard walks hold.** On `2ac73dd`, under the cap, on `linux-x86_64/X86_V3`:
> `tests/tier2/test_guard_numbers.py` 6 passed, none skipped, in 230 s. The largest relative drift on the same
> mesh, against VER-62's 10⁻⁸: `guard-supg` 5.0 × 10⁻¹⁶, `guard-no-inertia` 4.1 × 10⁻¹⁶, `guard-log`, now entered
> by the key, 4.1 × 10⁻¹⁶, `guard-reference` 3.8 × 10⁻¹⁶, `guard-constant-density` 2.2 × 10⁻¹⁶,
> `guard-dielectric` 0. The force tests passed in the first run.

### Work items

- [x] 1. cd0d299 `src/nanopnp/io/switches.py` with four records; `io/defaults.py`, `physics/terms.py`,
  `physics/models.py`, `pipeline/checks.py`, `pipeline/case.py`, `api/project.py`, `gui/web/screens.py`,
  `gui/web/physics_tools.py`; `tests/tier1/test_switches.py` and the tests *Grounding* D3 and D4 name; the NOTEs
  of §5.4.3 and §5.4.4 and VER-82's row (D1, D3, D4, D11); done when `tests/tier1/test_switches.py`,
  `test_model_interface.py`, `test_manifest.py`, `test_physics_models.py`, `test_physics_model.py`,
  `test_case_schema.py`, `test_case_leaves.py` and `test_kernel.py` pass. **Executor:** main
- [x] 2. 0dd7ec9 The fifth record and the key: `io/switches.py`, `io/case.py`, `io/artefact.py`, `io/models.py`,
  `validation/case_leaves.py`, `physics/models.py`, `pipeline/case.py`, `pipeline/checks.py`,
  `gui/web/tools.py`, `tests/tier1/test_switches.py`, `test_case_leaves.py`, `test_case_schema.py`,
  `tests/tier2/test_guard_numbers.py`;
  §5.3.1, NUM-02, NUM-18's NOTE, VER-80's and VER-82's rows (D2, D5 to D7, D10, D11); done when
  `tests/tier1/test_switches.py`, `test_case_leaves.py`, `test_case_schema.py`, `test_case_json_schema.py`,
  `test_gui_screens.py` and `test_model_interface.py`, no hash re-recorded, pass. **Executor:** main
- [x] 3. Compaction checkpoint. **Executor:** main
- [x] 4. 40a24a5 The stored forces, then `post/forces.py`, `physics/coupled.py`, `tests/tier1/test_forces.py` and VER-81's
  row (D8, D9, D11); done when the eight variants are stored from the unedited tree and equal after within
  10⁻¹², and `tests/tier1/test_forces.py` and `tests/tier2/test_force_routes.py` pass. The Outcome lists each
  difference. **Executor:** main

  > **Outcome — no force moved.** The eight variants on *Grounding* D8's mesh (383 elements), stored from
  > `847704e` and compared after the edit, relative to the larger half: the hydrodynamic half moves by 2.6 × 10⁻¹⁶
  > without the variable density and on the log branch, and by 1.3 × 10⁻¹⁶ under `pnp-ns`; every other number,
  > the omitted term included, is equal bit for bit. The state is `test_kernel.py`'s with the `r²` factors of the
  > concentrations at 0.005 for 0.05, so that both stay positive out to 12 nm and the log branch takes their
  > logarithm. There the inertia moves the hydrodynamic half by 1.6 × 10⁻⁵ and the omitted term is 1.1 × 10⁻³ of
  > the electromagnetic half. The log branch with a varying permittivity now raises `flow.py`'s
  > `NotImplementedError` from the dielectric density, where `_Integrands.korteweg` raised its own.
- [x] 5. The run, a `RUN` hand-back with no commit (D9); done when the log shows the six guard walks and the
  force tests, none failed or skipped. **Executor:** main, the run by the main session
- [x] 6. 8e18208 The records: `CHANGELOG.md`, `specification/a-traceability-matrix.md`, `docs/design/kernel.md`,
  `docs/model/index.md`, `docs/project/physics-models.md`, `knowledge/06-numerics-fem/01-discretisation.md`,
  `knowledge/log.md`, `docs/project/review-findings.md`, `review-items.md` (REV-298 fixed),
  `specification/history/holds-now.yaml`, this plan, the Phase 6 plan, `docs/plans/current.md`; done when the code
  and review say so. **Executor:** main

### Verification

Rows 1 to 4 are `tests/tier1/test_switches.py`; a document is `VALIDATED_DEFAULT_CASE` with one path assigned
(`test_manifest.py:_assigned`).

| Test | Tier | Identifiers | Oracle | Tolerance |
|---|---|---|---|---|
| Both terms or neither | 1 | VER-82; PHY-08, PHY-23 | No record names one of PHY-23's terms without the other. Over every set of values `conflicts` admits, `in_force` of each of the twelve display terms equals a table written in the test. `CoupledModel` with the switch holds both in `terms_in_force()`, the drift and the density not `None` at `test_kernel.py`'s state; without it, neither. The switch without the flow, and with the log branch, each raise | Exact |
| A switch off its default is a deviation | 1 | VER-82; FR-25, NUM-02 | For each record flipped alone: `deviations(document)` holds its path with both values, and the model built with it holds the path in `provenance["deviations_from_validated_default"]`; the default holds none | Exact |
| The records are the schema's | 1 | VER-82 | For each record: `schema_default(path)` and the validated default equal its `default`; each term it names is one of `COUPLED_TERMS`; each relation names a record. Each registered declaration states the records' names | Exact |
| An unset key moves no key | 1 | VER-82 | At false, `CaseArtefact`'s parameters and `resolve(...).model_options` hold no `log_variables`, and the artefact's hash is the literal recorded on the unedited tree; at true both hold it. The document resolves as `test_manifest.py:test_ver24_the_model_and_the_case_agree_on_the_switches_they_share` makes it | Exact |
| The forces read the densities, `tests/tier1/test_forces.py`, *Grounding* D8's mesh and state | 1 | VER-81; NUM-28, PHY-23 | For the default, no inertia, the dielectric switch, a solid fraction with the switch off and on, and a permittivity wall fit built in the test with the switch off and on (REV-303): `hd_N` less the stress work is `∫(Σf)·w` over the densities in force, written in the test; `em_N` less the Maxwell work is `−∫(f_ion + f_KH)·w`; the omitted term is `−∫f_KH·w`, or zero with the switch. The inertia's and the dielectric density's work are not zero | 10⁻¹² relative; above 10⁻⁹ of the half (1.2 × 10⁻⁷ measured) |
| `tests/tier1/test_case_schema.py`, the ladder's refusal, the key added | 1 | FR-25; NUM-18 | Each record off its default beside the ladder is refused, naming its path and `numerics.continuation: none` | Exact |
| `tests/tier1/test_case_leaves.py`, the key's probe | 1 | VER-71 | Each model honours the key or refuses it | Unchanged |
| `tests/tier1/test_model_interface.py` | 1 | VER-56 | The pinned solve keys and rung digests | Unchanged |
| `tests/tier2/test_force_routes.py` | 2 | VER-22 | Its own | Unchanged |
| Item 5's run | 2 | VER-80; NUM-29 | The stored values, `guard-log` by the key, its deviation in the manifest; the corrected case's routes | 10⁻⁸ (VER-62); 0.1 pN |

```bash
uv run pytest tests/tier1/test_switches.py tests/tier1/test_forces.py tests/tier2/test_force_routes.py -q
```

> **Outcome — the package's cost.** Measured, to the review: 1 session, 9 sub-agents, 2.2 agent hours, 4 touches
> (the estimate: about 3 sessions, 2 to 4 agent hours, 5 touches); claude-fable-5-2 0.18 M out, claude-opus-5-5
> 0.22 M out. The review ([CODE_REVIEW_103](../../code_reviews/CODE_REVIEW_103.md)) fixed five findings and left one,
> REV-303.

### Out of scope

- The ladder carrying the log branch: ruled out (BM2); Phase 7's speed-up compares the branch (BC24) and may
  reopen it. PHY-23's terms on the branch: no package (BL7).
- The per-model term lists, the declaration's terms derived, `models.py` split, the full check, MOD-10: WP6.12.

### Open questions

None.

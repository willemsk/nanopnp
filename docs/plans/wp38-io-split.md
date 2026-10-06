# WP38 — The `io` split

**Status: delivered, 6 October 2026.** Written 6 October 2026 on `claude/wp-plan-38-gm0s7s` at
`fd4308f`, after WP37 merged as `v0.5.0-alpha.3` and the Phase 4 plan was amended for the review
register (§8.2.9). It inherits everything the [current brief](current.md) lists as not to be
re-decided, and in particular:

- WP36's stage protocol and walk: a stage declares its walk facts in the registry and defines
  `key`, and VER-64 derives the walk from the registry;
- WP37's cuts, `numerics/`, and the three ratchets: `upward:` and `deferred_upward:` only shrink,
  `backend:` grows only by ruling, and a cut removes a dependency rather than deferring it (WP37
  D12);
- VER-61's recorded layering and VER-62's golden, which it must keep green.

This is the fourth work package of the [Phase 4 plan](phase-4-polish-and-user-testing.md). It fixes
`MOD-04`, the `io/case.py` part of `MOD-13`, and `MOD-15`, and finishes `MOD-03`. It also resolves
REV-03, REV-27, REV-54 and REV-63 (§8.2.8 H1, H6, H8, H12; §8.2.9 I3). `SPECIFICATION.md` governs,
and the identifiers below are pointers into it. **This commit amends the specification**: §5.1
gains `pipeline/` and restates `io/` as the base. `CLAUDE.md`'s structure list follows §5.1, and the
phase plan's open decision on the base half of `io` is closed by D1. VER-64's amended row, and the
findings and register rows, are claimed by `/wp-implement` in the commit that implements them.

## Execution brief

This brief runs to about 2,400 words, twice the 1,200-word target. The split, the four review items
and the stage-input change each need a decision that fixes a home or a check, and three of them
(D5, D7, D11) guard against a plausible wrong answer. Splitting the package would leave the stages
half-converted to D4, with VER-61's ratchet recording a tree no one gates.

### Scope

`io` is two things at once (`MOD-04`). It holds the artefact and case types that every stage
needs, and it holds the resolver, which consults the model, stabilisation and solver registries
and builds the electrolyte. Every stage calls `resolve(inputs.case)` itself, so every stage
imports the registries upward through `io` (*Design* §1). The cut is not a move of definitions
alone. The resolved case has to reach a stage as an input, built once by the assembler above it
(D4).

One PR delivers:

- **The split (`MOD-04`, `MOD-03`, `MOD-15`).** `io` becomes the base, directly above `core`, and
  a new subpackage, `pipeline/`, takes `io`'s old place in the order as the assembler (D1–D3). The
  stages are handed the resolved case (D4, D5), and the schema stops consulting registries (D7).
- **`io/case.py` divided (`MOD-13`)** into three base modules and two assembler modules, none
  above 1,266 lines (D14).
- **REV-03** (D9), **REV-27** (D8), **REV-54** (D12) and **REV-63** (D11).

**Breaks** (F4; `CHANGELOG.md`):

- `StageInputs(case=…)` becomes `StageInputs(resolved=…)`. Anyone implementing `Stage`, which is
  in `PUBLIC`, reads the resolved case from the inputs.
- `ResolvedCase.physics_model()` and `.model_declaration()` are replaced (D5).
- `load_case` and `loads_case` refuse an inf-sup-unstable element pair at load (D8).
- `nanopnp run --upto X` walks X's inputs only (D11).
- Internal modules move (IF-01: internal paths are not API).

`PUBLIC`'s names keep their meaning. Six of its module strings change (D12).

Pointers:

- §5.1, §5.2, §5.3.1, §5.3.2; IF-01, IF-02, IF-03; FR-27, FR-25; QR-11, QR-12; NUM-03;
- VER-25, VER-43, VER-45, VER-46, VER-47, VER-55, VER-60, VER-61, VER-62, VER-63, VER-64,
  VER-65;
- §8.2.8 H1, H6, H11, H12; §8.2.9 I3;
- the [report](../project/modularity.md)'s `MOD-03`, `MOD-04`, `MOD-13` and `MOD-15`;
- the [register](../project/review-items.md)'s REV-03, REV-27, REV-54 and REV-63.

No `OPN-` is open here. The phase plan's open decision "the base half of `io`" closes in D1.

### Decisions

| # | Decision | Choice | Why/source |
|---|---|---|---|
| D1 | Which half keeps the name | **`io` is the base**, and the assembler is a new subpackage, `pipeline/`. The order becomes `core`, **`io`**, `structure`, …, `post`, **`pipeline`**, `sweep`, `validation`, `cli`, `gui`, `nanopnp` | §5.1's `io` row already describes the base. The stages' ~60 imports of artefact and schema types stay. A base in `core` would make `core` reach `materials`, `numerics` and `physics` by annotation (D2). `pipeline` takes `io`'s old slot |
| D2 | The base | Unchanged: `io/artefact.py`, `store.py`, `defaults.py`, `manifest.py`. New: `io/case.py` (schema, errors, problem rendering, structural `read_case`/`read_case_text`, dump, v1 upgrade); `io/case_paths.py` (`field_at`, `case_fields`, `schema_default`, `field_description`, `field_bounds`, `value_at`, `substitute`, `with_*`); `io/resolved.py` (the three resolved types, `SOLVE_IRRELEVANT_PROVENANCE`, and the resolution constants a stage reads); `io/vocabulary.py` (D9). Runtime imports: `core` and `io` only. Annotations of `Electrolyte`, `NewtonSettings` and `ModelDeclaration` stay as static edges annotated `MOD-04` | H6 targets `top`, and an annotation is a cut (WP37 D12) |
| D3 | The assembler | `pipeline/case.py`: `load_case` and `loads_case` (D7), `resolve` and its `_resolve_*` helpers, `_switches` (taking `CorrectionChoiceSpec.to_choice`), `_model_options` and `CaseStage`. `pipeline/checks.py`: `check_document` (D7, D8), the `_check_*` functions, `_require_runnable`, `registry_options` and `options_at`. `pipeline/run.py` and `pipeline/reproduce.py` are `io/run.py` and `io/reproduce.py`, moved unchanged apart from D11. The registry target of stage 9 becomes `nanopnp.pipeline.case:CaseStage` | These are the definitions that use `charge`, `materials`, `numerics` or `physics` at run time (*Design* §2). `FIELD_FORMAT` is read only by `_require_runnable`, so `io → charge` goes with it |
| D4 | How a stage gets its resolved case | `StageInputs` gains `resolved: ResolvedCase` and loses `case`. No stage calls `resolve`. Every constructor resolves once: the walk passes `_Walk.resolved`, and the sweep, the shell, `validation/comsol.py` and the tests pass `resolve(document)`. `CaseStage.key` reads `inputs.resolved.document` and `.provenance`. `solve/state.restore` takes a `ResolvedCase` | Stages below `materials` read values only resolution can make (*Design* §1). A rename, not a retype: a `CaseDocument` passed as `case=` would answer `.structure` with another type. A stage alone is `StageInputs(resolved=resolve(doc))` (FR-27) |
| D5 | `ResolvedCase` without registry calls | Two fields, filled by `resolve` from the model it already builds once: `declaration: ModelDeclaration` and `essential_boundaries: Mapping[str, str]`, the latter being `model.essential_boundaries(DEFAULT_BOUNDARIES)`. `deposits_charge` reads `self.declaration`. `model_declaration()` and `physics_model()` go. `build_model` moves to `physics/models.py` as `case_model(resolved)`, the one place a case's model is built (WP26 D6), called by `resolve` and `solve/state.py` | The mesh gate (`mesh/ingest.py:309`, `:348`, `:745`) is the only consumer below `physics`, and reads the values it computes today. Both fields are functions of the document; `provenance` is unchanged |
| D6 | The schema's own runtime imports | `CorrectionChoiceSpec.to_choice` goes to `pipeline/case.py` as `_choice(spec)`. Nothing in the base imports `materials` or `charge` at run time | *Design* §2: `to_choice` is the schema's only runtime use of `materials` |
| D7 | Registry checks leave the schema | `CaseDocument._check_registries` keeps its corrections and outputs checks, which read only `core`. Its three registry checks (`physics.model`, `numerics.stabilisation`, `numerics.linear.solver`) move to `pipeline.checks.check_document`. `pipeline.case.load_case`/`loads_case` are `io.case.read_case`/`read_case_text` followed by `check_document`. `resolve` calls `check_document` first, so a document built in memory (`substitute`, `with_section`, a sweep member) is checked when resolved. The shell's `CaseModel.commit` calls `check_document` after `substitute` (QR-11). Each refusal's text is unchanged, character for character, on the command line and in the editor | The phase plan. `load_case` keeps its `PUBLIC` contract. The base loader is renamed so that no two `load_case`s differ in strictness. WP39 replaces the three checks' sets with registries here |
| D8 | REV-27 | `check_document` also runs the element-order checks, moved out of `resolve`: the order labels, `phi` and `c` at one order, and `inf_sup_problem`. A case's validation, at load and in the editor, therefore reports the inf-sup refusal. No new command | `nanopnp validate` is the Tier-3 harness (`cli/__init__.py:1143`) and validates no case. The register's intent is that validation reports every check against the document alone. Checks reading the parameter file or a supplied file stay in `resolve`, which `--upto case` runs. Open question 1 |
| D9 | REV-03 | `io/vocabulary.py` holds `POTENTIAL`, `VELOCITY`, `VELOCITY_AXIS`, `PRESSURE` and `PRESSURE_MEAN`. `mesh/primitives.py` and `physics/models.py` import them, with no re-export. Every importer is updated (*Design* §3) | The lowest consumer is `mesh`, so the one home is in the base. `ELECTROLYTE_DOMAINS` is a region pattern, not a field, and stays in `mesh/primitives.py`. `concentration_field_name` is the model's naming rule and stays in `physics` |
| D10 | `io/fields.py`, the IF-07 export | It moves whole to `post/export.py`, `FIXED_CHARGE_ATTRIBUTE` with it | It imports `mesh` and `physics` at run time and NGSolve when called, and `post` is its main consumer. This removes `io → mesh`, the last `io → physics`, and `io` from VER-65's set, which shrinks to eleven |
| D11 | REV-63 | (a) Every stage declares each upstream artefact it reads. The audit adds at least `charge` (optional) to `solve`, and `mesh` and `charge` to `qoi` and `report`. (b) `_Walk.inputs(name)` offers only the stage's declared inputs, plus its own artefact in the deviations pass. (c) `selected_stages(resolved, upto)` returns the walked stages in `upto`'s transitive input closure, in walk order. `upto=None` and every refusal text are unchanged. (d) A Tier-1 check reads each registered stage's module and refuses a literal name passed to `inputs.require`, `inputs.upstream.get` or `inputs.upstream[…]` that the stage does not declare | `solve` reads `charge` undeclared (`solve/stage.py:279`), so a closure alone would converge the uncharged problem: a plausible wrong answer. (b) makes a missed declaration fail every walk; (d) names its line. VER-64's derivation stands. *Design* §4 |
| D12 | REV-54 and `PUBLIC` | `Surface` records the module of each mirrored import. The MOD-12 test asserts that `PUBLIC[name]` is that module, for every name. `resolve`, `load_case` and `loads_case` point at `nanopnp.pipeline.case`, and `run_case`, `run_document` and `RunResult` at `nanopnp.pipeline.run` | Before this check, a name could be mirrored from the module it used to live in. The names are unchanged |
| D13 | `MOD-15` | `core/stages.py` keeps its `TYPE_CHECKING` import of `Artefact` and `StageInputs`, which now come from the base. The edge `core → io` stays static and is annotated `MOD-15`, and the finding becomes `fixed` | This is the report's first recommended branch: "the annotated type moves to the base half of `io`". The consequence the finding names, that the base depends on the assembler, no longer holds. Moving `StageInputs` into `core` would drag `ResolvedCase` after it |
| D14 | `MOD-13`'s bound | No module the split produces exceeds 1,266 lines, the smallest module `MOD-13` names. Predicted: `io/case.py` ≈ 1,050, `io/case_paths.py` ≈ 650, `io/resolved.py` ≈ 300, `pipeline/checks.py` ≈ 700, `pipeline/case.py` ≈ 550 | The finding states no threshold, so the plan sets one. A module over the bound is split again before the PR, not recorded as an Outcome |
| D15 | VER-61's records | `LAYER_ORDER` and the YAML header take D1's order. `edges:` is re-recorded. `upward:` shrinks to `cli → nanopnp` (REV-05, WP39). `deferred_upward:` is unchanged. `backend:` loses `io` (D10). If the measured `top` relation has no component, `MOD-03` becomes `fixed`. H6's assertion itself stays WP39's | *Design* §1 simulates this on `fd4308f`: one upward `top` edge, no component. A ratchet that holds only `cli → nanopnp`, where `nanopnp` imports nothing at module scope, already forbids a cycle |
| D16 | Shims | None at an old path | WP37 D10; IF-01 |
| D17 | Numbers and keys | Zero drift: VER-62 at 10⁻⁸, and no artefact key changes. A key that moves is an Outcome to explain, not a value to re-pin | Keys are taken from the document and from `provenance`, neither of which changes. `StageInputs` is not hashed. G10 |
| D18 | Records | `MOD-03` (per D15), `MOD-04`, `MOD-13` and `MOD-15` become `fixed`. `MOD-13`'s remainder stays deferred by H1, to Phase 5 and Phase 6. REV-03, REV-27, REV-54 and REV-63 become `fixed`, and REV-27's section records D8's reading of "`nanopnp validate`" | VER-63; §8.2.8 H12 |
| D19 | Release | `v0.5.0-alpha.4`, with a `CHANGELOG.md` section listing the breaks above and a table of moves | §2.7; G11 |

> **Outcome — the author ruled open question 1: `nanopnp validate case <file>` is added (D8).** It
> loads and resolves the case, so it makes the registry, element-order and inf-sup checks and every
> check `resolve` makes against the parameter file, and prints the model, the stabilisation and the
> stages a run walks; a refusal exits 3 with a run's text (`tests/tier1/test_cli.py`). D8's
> "no new command" no longer holds; REV-27's section records the ruling.

> **Outcome — `build_model` became `physics.models.build_case_model`, beside `case_model` (D5).**
> `resolve` builds the model before the `ResolvedCase` exists, to fill `declaration` and
> `essential_boundaries` and to surface a builder's refusal, so it calls `build_case_model` on the
> parts. `case_model(resolved)` calls the same function, for `solve/state.py` and the stages. There
> is still one place a case's model is built.

> **Outcome — a document failing both a structural check and a registry check reports the
> structural one alone (D7).** The installed-file checks (corrections, parameters, outputs) stay in
> the schema and the three registry checks run after it, so a document naming both an uninstalled
> correction file and an unregistered model is refused for the correction file only, where the
> schema used to list both in one refusal. Each refusal's text is unchanged; the second appears
> once the first is fixed.

> **Outcome — `--upto materials` no longer stages the solve's inputs (D11), so `stored_upstream`
> takes `feeding=`.** A sweep keyed a warm-start parent by walking it to `materials`, which used
> to mesh and build the charge on the way; under the closure that walk is `case`, `materials`, and
> the parent's solve key could not be made, which the sweep runner takes as a cold start: a
> silently slower sweep, not a failure. `pipeline.run.stored_upstream(…, feeding="solve")` walks
> the closure of the stage it feeds instead, and the shell's assessment uses `feeding="contour"`.
> `tests/tier2/test_exclusion_keys.py` and example 04's `tour.py` keyed the solve the same way and
> now walk to `charge` (or `mesh`) and then to `materials`; the keys equal `KEYS_V2` unchanged.

> **Outcome — the modules D14 bounds, measured.** `io/case.py` 1,058 lines, `io/case_paths.py`
> 676, `io/resolved.py` 280, `pipeline/checks.py` 954, `pipeline/case.py` 436; `pipeline/run.py`
> is 1,119. All are under 1,266 (`tests/tier1/test_layering.py`). `pipeline/checks.py` is larger
> than predicted because the pure checks `resolve` calls went with it, as *Design* §2 says.

### Work items

In dependency order. The moves land as one commit, as WP37's did, because VER-61 pins the YAML in
both directions. The YAML, `LAYER_ORDER` and the tests go in the same commit. Mechanical work runs
on Sonnet (`.claude/model-policy.md`): the import rewrites, the 112 `StageInputs(` sites and the
`monkeypatch` strings. D5, D7, D8 and D11 need Opus, because each can produce a plausible wrong
answer: a dropped check, a changed refusal text or a stage starved of an input.

1. `io/vocabulary.py`; `mesh/primitives.py` and `physics/models.py` import from it (D9).
2. `post/export.py` from `io/fields.py` (D10).
3. Split `io/case.py` into `io/case.py`, `io/case_paths.py` and `io/resolved.py`, and create
   `pipeline/case.py` and `pipeline/checks.py` (D2, D3, D6, D7, D8). Read *Design* §2 first.
4. `ResolvedCase.declaration` and `.essential_boundaries`; `physics.models.case_model` (D5).
5. `StageInputs.resolved` (D4). Convert every stage and every constructor; `restore(resolved, …)`.
6. `pipeline/run.py` and `pipeline/reproduce.py`. Then D11: the declarations audit, the filtered
   inputs and the closure. Read *Design* §4 first.
7. The shell: `CaseModel.commit` runs `check_document`, and every import follows (QR-11, VER-43).
8. `nanopnp/__init__.py`'s `PUBLIC` and mirror; `validation/modularity.py`'s `Surface`,
   `LAYER_ORDER` and the YAML (D12, D15).
9. The tests, the user guide's `--upto` sentence in `docs/guide/running.md`, `.knowledge/07`'s
   paths, VER-64's row (D11, plus the `io/run.py` path) and Appendix A, the findings log and the
   register, `CHANGELOG.md`, and the phase plan's Outcome.

### Verification

| Test | Tier | Identifiers | Oracle |
|---|---|---|---|
| `tests/tier1/test_layering.py` | 1 | VER-61 | The YAML equals the relation. `upward:` is `{cli → nanopnp}`. A `top` import of `nanopnp.pipeline.case` substituted into `mesh/ingest.py` fails naming `mesh → pipeline`. With `io/resolved.py`'s `Electrolyte` import moved out of `TYPE_CHECKING` through `sources=`, the test fails naming `io → materials` |
| `tests/tier1/test_backend_guard.py` | 1 | VER-65 | `backend:` is the eleven measured. `io` is gone and nothing has joined |
| `tests/tier1/test_stage_conformance.py` | 1 | VER-64, FR-27 | (d) passes on the tree. A synthetic stage module reading `inputs.upstream.get("charge")` without declaring it is refused, naming the stage, the name and the line. `selected_stages(example 07, "protonation") == ("case", "structure", "protonation")`. On a depositing case, `"charge"` is in the closure of `"solve"`. The 13-name walk order is unchanged. Each stage is handed exactly its declared inputs |
| `tests/tier1/test_public_api.py` | 1 | VER-45, IF-01 (REV-54) | Every mirrored name's module equals `PUBLIC`'s. An `__init__.py` substituted to mirror `resolve` from `nanopnp.io.case` fails naming `resolve` and both modules |
| `tests/tier1/test_case_*.py`, `test_cli.py` | 1 | IF-03, VER-47, NUM-03, QR-12 | Each registry refusal's text is unchanged, through `load_case` and through `nanopnp run`. A P1/P1 flow case with `stabilisation: none` is refused at `load_case` naming inf-sup, and is accepted with `reference`. A `substitute`d unknown model is refused at `resolve`. A case's model declaration and essential boundaries equal the registry's |
| `tests/tier1/test_gui_case_model.py` (or its present home) | 1 | QR-11, VER-43 | A commit naming an unregistered model, or an inf-sup-unstable pair, is refused with the command line's text |
| `tests/tier1/test_modularity_sizes.py` (new, or in `test_layering.py`) | 1 | `MOD-13` | Each module of D14 is at most 1,266 lines |
| The seven VER-62 walks (`extended`) | 2 | VER-62 | Zero drift at 10⁻⁸ on the recorded meshes. Through D11(b), these include the 2WCD walks whose solve reads the deposited charge |
| `tests/tier1/test_findings_logs.py` | 1 | VER-63 | D18's rows `fixed`, each with this plan's link |
| Executed examples and guide (`extended`) | 2 | VER-46 | Every documented `--upto mesh`, `--upto charge` and `--upto contour` command still runs, and walks the stages it did (*Design* §4) |

Command: `.claude/hooks/gate.sh run`, then the documentation build of `CLAUDE.md`'s table (VER-45).

### Out of scope

- The three backend registries, and H6's acyclicity assertion: WP39 (H7, H6). The checks D7
  moves are where WP39 replaces the frozensets.
- `cli → nanopnp` and `gui → nanopnp`: WP39 (REV-05).
- The stale release strings in the moved refusals: WP40 (`MOD-14`). They move verbatim here.
- `MOD-13`'s remainder: `cli/__init__.py` in Phase 5, and `physics/models.py` and
  `default_ladder` in Phase 6 (H1).
- `MOD-17`'s repeated default: post-1.0 (H5).

### Open questions

1. **REV-27's command (not blocking; D8 is the default).** §8.2.9 I3 says "`nanopnp validate`",
   which is the Tier-3 harness and checks no case. D8 makes a case's validation (`load_case` and
   the editor) report the inf-sup check, and adds no command. If the author wants a case checker
   on the command line, for example `nanopnp validate case <file>`, it is one subcommand on
   `check_document`, and this package can add it.

## Design

### 1. Why the stages must be handed the resolved case

At `fd4308f`, these stages import `resolve` from `io.case` at module scope and call it on
`inputs.case`: `structure`, `density`, `symmetry`, `geometry` (`contour`, `region`), `mesh`
(`ingest`), `charge` (`stage`, `protonation`), `materials`, `solve` and `post`. `resolve` builds
the `Electrolyte` (`materials`), the Newton settings (`numerics`) and the model (`physics`), and
checks the case against the three registries. Below `materials`, the stages read
materials-derived and physics-derived values:

- `mesh` reads `electrolyte.permittivity_0`, `electrolyte.relative_permittivity(c)`, the built
  model's essential boundaries and the declaration's `wall_distance` and `solids`;
- `charge` reads `deposits_charge`, which reads the declaration.

A definition move cannot put those values below `mesh`. They must arrive as data.

The simulation, in this session's scratchpad and repeatable from `validation.modularity`, takes
`import_edges()` at `fd4308f`, keeps the `top` kind, and makes three changes:

- it remaps `io.run` and `io.reproduce` to `pipeline` and `io.fields` to `post`;
- it moves `io/case.py`'s imports of `charge`, `materials`, `numerics` and `physics` to `pipeline`;
- it applies D1's order.

The upward edges are `{cli → nanopnp}`, and `components` finds none of more than one subpackage.
The stages' imports of `io.case` stay in the simulation and point down, so the prediction does not
depend on D4. D4 is still required, because without it the stages' `resolve` would sit in
`pipeline`.

### 2. What in `io/case.py` uses a registry at run time

A survey of the 3,180 lines, with the import block at 52–81, found these runtime uses:

| Definition | Uses | Goes to |
|---|---|---|
| `CorrectionChoiceSpec.to_choice` (504) | `CorrectionChoice` | `pipeline/case.py` (D6) |
| `CaseDocument._check_registries` (690–741) | `registered_models`, `registered_stabilisations`, `AVAILABLE_SOLVERS`; the corrections and outputs checks use `core` only | split (D7) |
| `registry_options`, `options_at` (797–877) | the three registries | `pipeline/checks.py` |
| `ResolvedCase.deposits_charge`, `.model_declaration`, `.physics_model` | `declaration`, `create` | fields and `case_model` (D5) |
| `_switches`, `_require_runnable` (`FIELD_FORMAT`, `LADDER_STRATEGY`), `_admitting`, `_honouring`, `_accepting`, `_check_physics_switches`, `_check_strategy`, `_check_outputs`, `_model_options`, `build_model`, `resolve`, `CaseStage` | `CorrectionSwitches`, `declaration`, `SWITCHES`, `create`, `inf_sup_problem`, `Electrolyte`, `NewtonSettings` | `pipeline/` |

Everything else uses no imported name. That covers the schema models (83–785), the field walk and
edits (990–1622), load, dump and upgrade (1623–1835), the pure checks (`_check_charge`,
`_check_profile*`, `_check_smearing`, `_check_generation`, `_check_operating_point`,
`_check_ladder_can_honour`) and the resolved types (1907–2124, apart from the three members above).
The pure checks are called only by `resolve`, so they go to `pipeline/checks.py` with it.
`LinearSpec.solver`, `numerics.stabilisation` and `numerics.continuation` are hard-coded
`Literal`s, so the schema imports nothing from `numerics` once D7 has moved the checks.

### 3. The field-name vocabulary (REV-03)

At `fd4308f`, `POTENTIAL`, `VELOCITY` and `VELOCITY_AXIS` are defined in `mesh/primitives.py`, and
`PRESSURE` and `PRESSURE_MEAN` in `physics/models.py`. They are imported by:

- `mesh/ingest.py`, `physics/models.py`;
- `io/fields.py`, which becomes `post/export.py`;
- `post/forces.py`, `post/qoi.py`;
- `validation/apbs.py`, `validation/compare.py`, `validation/mms.py`.

None of them is read by attribute access, so each change is an import line. The strings do not
change, and neither does any key: a field's name enters a key only as its value.

### 4. The closure walk and the declarations (REV-63)

The registry declares `solve: (case, materials, mesh)`. Yet `solve/stage.py:279` reads
`inputs.upstream.get("charge")`. `post/stage.py:459–460` and `:691–707` read `mesh` and `charge`
for `qoi` and `report`. Today the walk offers every artefact produced so far
(`io/run.py:296`), so an undeclared read works in a complete walk. A walk truncated to a declared
closure would hand `solve` no charge. It would then converge the uncharged problem under a
different key, and nothing would fail. Hence D11, in this order:

1. The audit completes the declarations. A read that only some cases make is `optional_inputs`,
   as `charge`'s `protonation` already is.
2. The walk filters `upstream` to the declared names, so a missed declaration starves its stage in
   every walk. The 2WCD walks then fail VER-62, and fail loudly.
3. The static check names the module and line, which (2) does not.

The documented truncated walks are unchanged, because each documented target's closure is
everything before it in walk order:

| Target | Closure | Unchanged? |
|---|---|---|
| `contour` | `case`, `structure`, `density`, `symmetry`, `contour` | Yes |
| `mesh` | adds `region` and `mesh` | Yes |
| `charge` | adds `protonation` on a depositing case | Yes. `materials` comes after `charge` |

The walk changes for two kinds of target:

- `protonation` loses the five geometry stages (REV-63);
- `materials` alone becomes `case`, `materials`.

VER-55 and VER-60 assert the `upto: mesh` and `upto: charge` walks, and both stay as written.

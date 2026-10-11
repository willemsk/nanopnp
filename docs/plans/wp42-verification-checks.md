# WP42 — The verification checks

PR: [#91](https://github.com/willemsk/nanopnp/pull/91), branch feat/wp42-verification-checks

**Status: in progress (extension).** Items 1–9 delivered 10 October 2026 as `v0.5.0-alpha.8`. Extended 11 October 2026 with Items 10–13 (parameter and identifier centralisation). Written 9 October 2026 at `c306256`, after WP41 was delivered as
`v0.5.0-alpha.7`. It inherits everything the [current brief](current.md) lists as not to be
re-decided, and in particular: VER-62's golden at 10⁻⁸ (no number moves in this package); WP40's
rule that a refusal names its requirement (VER-67); WP38's split (`pipeline/checks.py` refuses at
resolution); WP41's per-field Newton test and order-8 field rule.

This is the eighth work package of the [Phase 4 plan](phase-4-polish-and-user-testing.md), the second
of the three §8.2.9 I1 and I2 add. It resolves REV-11, REV-12, REV-13, REV-23, REV-29, REV-34, REV-42,
REV-44 and REV-48, and, as a consequence of D3, REV-66. `SPECIFICATION.md` governs; identifiers are
pointers. **This commit amends the specification**: the VER-70 and VER-71 rows, the VER-56 clause the
author's ruling overturns, the §5.4.3 NOTE on what a model does not read, the PHY-22 NOTE on a
switch with nothing to switch, the §5.3.1 compatibility NOTE on the first move, and Appendix A. The
brief exceeds 1,200 words and the package is not split: the author ruled it one package (9 October
2026), and the refusals, the schema move and the probe that proves them cannot land separately
without a release that narrows and does not move its identifier.

**Author rulings taken for this plan (9 October 2026):** (1) every (model, leaf) pair a model
accepts and never applies is refused, declaration-driven (D3, D5, D6); (2) the v2 upgrade carries
exactly and refuses what a document wrote (D10); (3) the implementing session stops **before and
after every work item** (*Author checkpoints*); (4) one package.

**Author rulings taken for the extension (11 October 2026):** (1) Broad parameter audit covering
schemas, stage identifiers, and defaults; (2) Canonical schemas defined in `nanopnp.io.artefact` and
imported downward by domain packages, with Tier-1 parity verification against `core.stages` (D14);
(3) Stage identifiers encapsulated in `StageName` `StrEnum` in `nanopnp.core.stages` (D15);
(4) Domain defaults modules `mesh.defaults` and `numerics.defaults` referenced by `io.case`,
`io.defaults` and CLI (D16); (5) Shared `make_case_dict` and `case_yaml_template` fixtures in
`tests/conftest.py` (D17); (6) Author checkpoints before and after every work item (P10–P13, R10–R13).

## Execution brief

### Scope

| Item | Today | Fix |
|---|---|---|
| REV-11 | A gate written `if v > tol: raise` passes a NaN; 38 such sites | VER-70 (D1, D2) |
| REV-12 | No test shows each case leaf is read; ~75 (model, leaf) pairs are accepted and inert | VER-71 (D3–D8) |
| REV-42 | `pnp` accepts `variable_density`, `inertia` true and ignores them | D5 |
| REV-66 | `pb` with `flow` left true is refused on an inf-sup pair it never solves | D8 |
| — | The narrowing moves the schema to `nanopnp/case/v0.5` | D9, D10 |
| REV-13 | Example 06's stage-7 keys are asserted against themselves | D11 |
| REV-23 | One Einstein-ratio range for both ions | D12 |
| REV-29, -34, -44, -48 | Copied fixtures, constants and a re-solved slab | D13 |
| — | Schemas duplicated in domain modules and `core/stages.py` | Canonical in `io/artefact.py`, imported downward (D14) |
| — | Stage identifiers passed as raw loose string literals | `StageName` (`StrEnum` + typed `Literal`) in `core/stages.py` (D15) |
| — | Mesh and numerics defaults scattered across models and CLI | Domain modules `mesh/defaults.py`, `numerics/defaults.py` (D16) |
| — | 80+ test files hardcode `schema: nanopnp/case/v0.5` | Shared `case_yaml_template`, `make_case_dict` in `tests/conftest.py` (D17) |

**Breaks** (`CHANGELOG.md`, `0.5.0-alpha.8`, with a section *Migrating a nanopnp/case/v2
document*): the case schema is `nanopnp/case/v0.5`; a case setting a value its model never applies
is refused; `pnp` cases write `variable_density: false, inertia: false` (carried for v2); `pnp`
manifests now list those two as deviations, and a `pnp-ns` manifest lists its corrections as
deviations (it read none before and recorded none). Stage-10 keys of `pnp`, `pnp-ns`, `pb`,
`pb-linear` cases move (their documents change); **no number moves** (VER-62 at 10⁻⁸). Exit codes do
not change.

Pointers: QR-12, FR-25, PHY-13, PHY-21, PHY-22, IF-03, §5.3.1 NOTE (compatibility), §5.4.3 NOTEs,
§8.2.7 G6, §8.2.9 I2, VER-24, VER-43, VER-47, VER-56, VER-62, VER-63, VER-67, VER-70, VER-71, VER-72.
No `OPN-` is open here.

### Decisions

| # | Decision | Choice | Why/source |
|---|---|---|---|
| D1 | VER-70's rule | `nanopnp.validation.modularity` gains `gate_classes(errors_source) -> frozenset[str]` (the class-4 entries of `core/errors.py`'s table, read by AST; 39 today), `nan_permissive_gates(package, *, gates, exempt) -> NanGateFindings(violations, stale)`, `NanGate(path, line, function, test)` whose `str` is `src/nanopnp/<path>:<line>: <function>: if <test> (VER-70)`, and `NAN_EXEMPT: dict[str, str]` keyed `<path>:<function>: <ast.unparse(test)>`. Scope: every `if` outside `gui/` whose body (not entering a nested def) raises a gate class or `.append`s one. Open comparison: an ordering op not under `not`, inside calls included, not all-integer by syntax; a test calling `isfinite`/`isnan` is safe | *Design* §1; the prototype found 44 sites. Line-free exemption keys survive edits above them |
| D2 | The 44 sites | 38 rewritten to the negated form (`a > t` → `not a <= t`, `a < t` → `not a >= t`, `a >= t` → `not a < t`, `a <= t` → `not a > t`; `x or y` → `not (x' and y')`; `np.any(e > t)` → `not np.all(e <= t)`), behaviour unchanged for finite values; 6 exempt with reasons (*Design* §1) | QR-12. The house idiom (`numerics/gates.py`) |
| D3 | What a model does not read | `ModelDeclaration.unread: frozenset[str]` (case paths). Values: test `UNREAD` in `test_case_leaves.py`, *Design* §2. `pipeline/checks._check_unread(document)` in `require_runnable`, after `_check_physics_switches`: refuses every unread leaf whose value differs from `schema_default`, one message, text *Design* §4; a leaf without a default is skipped | Author ruling 1; VER-56 (declaration, never name). Prototype: the inert set equals `UNREAD` exactly (*Design* §3) |
| D4 | The leaf classification | `src/nanopnp/validation/case_leaves.py`: `KINDS = ("solve","solver","stage","post","fixed","checked","provenance")`, `Leaf(kind, consumer, reason)`, `LEAVES` (105 entries), `unclassified(paths, leaves) -> (missing, stale)`. Membership of every kind but `stage` is fixed by the planned test; `stage` leaves (50: `inputs.*` but three artefacts, `structure.*` but `variant`, `geometry.*`, `charge.*` but `axis_cutoff_nm`, `numerics.mesh.*`) each name their consuming stage. Pure data; no import beyond `typing`/`dataclasses` | REV-12; phase plan's oracle "a leaf added and consumed nowhere fails" |
| D5 | Switch sets (REV-42) | `pnp`: `variable_density`, `inertia` `(False,)`. `pnp-ns`: `variable_density` `(True,)`, `dielectric_gradient_forces` `(False,)`. Refused by the existing generated text | `pb`'s precedent; `pnp-ns`'s `ρ̃ ≡ 1` and `∂ε̃/∂c̃ ≡ 0` make the other value an identity (`physics/flow.py:permittivity_gradient`); probe bit-identical |
| D6 | Data-driven refusals | `materials.models` states which parts (`concentration`, `wall`) a correction model applies per property (`fc`/`fw`, or `ion_wall_function` for D, μ; `none` applies neither). `_check_correction_parts` refuses `false` on a part not applied, for leaves the model reads; `_check_driver` refuses `ionic_strength` for two species of unit valence, when the model reads the driver. Texts *Design* §4 | PHY-22 NOTE (this commit); probe: `permittivity.wall`, `density.wall`, driver inert under every model |
| D7 | VER-71's oracles | Solve leaves: the residual probe of `test_case_leaves.py` (`fingerprint`: top rung via `ladder`, residual at a fixed non-electroneutral state, essential potential data, rung signature). Solver leaves: `damped_newton` reached with the case's settings (patched in `physics.models`, `physics.pb`); a runtime-registered probe solver reached. Stage leaves: the consumer's key moves and no stage upstream of it does | *Design* §3: an electroneutral state hid every concentration dependence of `pnp-ns` in the prototype |
| D8 | REV-66 | `check_document`'s inf-sup check runs only when `numerics.elements.u` is not in the model's `unread` | Falls out of D3; author confirms at checkpoint |
| D9 | Identifier | `CASE_SCHEMA = "nanopnp/case/v0.5"`, `CASE_SCHEMA_V2`, `CASE_SCHEMA_V1` in `io/artefact.py`; `core/stages.py`'s `artefact_schema`; unknown identifier text *Design* §4. `upgrade_v1`'s texts keep naming v2 | G6; §5.3.1 NOTE |
| D10 | The upgrade | `io` reads v2 (and v1 via v2) as v0.5, setting `CaseDocument.upgraded_from` (a `PrivateAttr`, kept by `model_copy`). `pipeline.checks.carry_upgrade(document, source)`, run by `load_case`/`loads_case` before `check_document`: for each `physics:` switch not in `model_fields_set` whose value the model does not honour and whose honoured set has one value, set that value and log INFO (logger `nanopnp.pipeline.checks`, *Design* §4). A refusal by D3, D5, D6 or the switch check of an upgraded document ends with the migration line | Author ruling 2. `io` stays model-agnostic (VER-61) |
| D11 | REV-13 | `test_validation_identity.py` pins example 06's stage-7 keys: protonation `5fefd7b11d04851ddffda38cddbff769282a325cc597baec432507209e86f732`, charge grid `969ad260dfde8107d883a6d96d1fc357d680acb18479b05c72688c5cc7c519ba` (structure `bbf72688…`), before and after `case_identity` | Measured at `c306256` |
| D12 | REV-23 | Per ion, `|D/μ/V_T − table| ≤ 1e-3` at 0.15, 1, 3 M: Na⁺ 1.208, 1.468, 1.665; Cl⁻ 1.132, 1.221, 1.279; monotone | `.knowledge/01` §3.0 **[tested]**; table rounds to 3 d.p.; measured 1.20818, 1.4682, 1.66538 / 1.13184, 1.22129, 1.2794 |
| D13 | Hygiene moves | REV-29: one `cylindrical_pore_case` fixture in `tests/conftest.py` for `test_cli`, `test_run`, `test_solve_hook`, `test_gui_solver_process`. REV-34: the VAL-05 frozen case, `as_yaml`, `REFERENCE_TRIANGLES` and the D10 figures as fixtures in `tests/conftest.py`; rendered case text byte-identical before and after (sha256 in the commit body). REV-44: the drawn slab solved once per module. REV-48: the 2WCD exclusion constants as one fixture. Fixtures, never `from conftest import` at run time | Moves, not new assertions (§7.6 NOTE levers) |
| D14 | Canonical schemas & downward adoption | `nanopnp.io.artefact` defines all canonical schema constants (`CASE_SCHEMA`, `STRUCTURE_SCHEMA`, `DENSITY_SCHEMA`, `REDUCED_SCHEMA`, `PROFILE_ARTEFACT_SCHEMA`, `REGION_SCHEMA`, `MATERIALS_SCHEMA`, `MESH_ARTEFACT_SCHEMA`, `PROTONATION_SCHEMA`, `CHARGE_GRID_SCHEMA`, `FIELDS_SCHEMA`, `SOLUTION_SCHEMA`, `QOI_SCHEMA`, `REPORT_SCHEMA`, `SWEEP_SCHEMA`). Domain modules (`mesh/adapter.py:MESH_SCHEMA`, `geometry/region.py:REGION_SCHEMA`, `geometry/profile.py:PROFILE_SCHEMA`, etc.) import them downward from `io.artefact`. `core/stages.py` stage descriptions are validated against `io.artefact` in Tier 1 (`test_stages.py`) to prevent drift without creating upward edges | Rulings 1 & 2 (11 Oct 2026); preserves `upward: []` |
| D14b | Repo-wide schema migration to v0.5 | All schemas across `nanopnp` take `v0.5` prior to release v1.0, generalising SPECIFICATION.md §8.2.7 G6. Canonical constants in `io.artefact`, stage descriptions in `core.stages`, domain schemas in `charge`, `density`, `io.manifest`, `pipeline.run`, `post.export`, `materials.corrections`, `sweep.plan`, `validation`, data YAML files, and examples take `/v0.5`. Hash pins in `test_validation_identity.py` and `test_model_interface.py` re-recorded under the migrated schemas | Author ruling (11 Oct 2026) |
| D15 | Stage identifiers | `nanopnp.core.stages` defines `StageName(StrEnum)` (`CASE = "case"`, `STRUCTURE = "structure"`, `DENSITY = "density"`, `SYMMETRY = "symmetry"`, `CONTOUR = "contour"`, `REGION = "region"`, `MESH = "mesh"`, `PROTONATION = "protonation"`, `MATERIALS = "materials"`, `CHARGE = "charge"`, `SOLVE = "solve"`, `QOI = "qoi"`, `REPORT = "report"`), `StageNameLiteral = Literal[...]`, and `StageIdentifier = StageName | StageNameLiteral`. `create()`, `describe()`, and `require()` accept `StageIdentifier`. Stage descriptions and consumers use `StageName` | Ruling 3 (11 Oct 2026); IDE autocompletion and static type checks |
| D16 | Domain sizing and defaults | Group default parameters in domain modules: `mesh/defaults.py` (`DEFAULT_PORE_RADIUS_NM: Final = 2.0`, `DEFAULT_MEMBRANE_THICKNESS_NM: Final = 4.0`, `DEFAULT_RESERVOIR_RADIUS_NM: Final = 10.0`, `DEFAULT_MAXH_NM: Final = 4.0`, `DEFAULT_WALL_H_NM: Final = 0.2`, `DEFAULT_CYLINDER_WALL_H_NM: Final = 0.35`); `numerics/defaults.py` (`DEFAULT_NONLINEAR_RTOL: Final = 1e-4`, `DEFAULT_NONLINEAR_MAX_ITER: Final = 30`, `DEFAULT_ELEMENT_ORDER_U: Final = 2`, `DEFAULT_ELEMENT_ORDER_P: Final = 1`). `io/case.py` Pydantic models, `io/defaults.py` (`_VALIDATED_DEFAULTS`), and `cli/__init__.py` subparser defaults reference these constants directly | Ruling 4 (11 Oct 2026); single source of truth for physical/numerical defaults |
| D17 | Test fixture centralisation | `tests/conftest.py` introduces `case_yaml_template()` fixture and `make_case_dict(**overrides)` helper, dynamically injecting active `CASE_SCHEMA`. Test files with inline schema YAML strings are migrated to reference `CASE_SCHEMA` or use the fixtures | Ruling 5 (11 Oct 2026); insulates test suite against future schema version bumps |

### Author checkpoints (binding)

The implementing session is not Opus (Google Antigravity CLI) and the author verifies every item.
**Before** each item (`Pk`) it stops and posts: the decision rows, the files and seams it found
(`file:line`), the planned tests it will turn green with their current `XFAIL` output run verbatim,
and anything in the plan it believes wrong. **After** each item (`Rk`), with the commit made, it
stops and posts: the short SHA, `git show --stat`, each command it ran with its output tail verbatim,
and the item's evidence packet below. It proceeds only on the author's explicit `go Pk` or
`approved Rk` in the session; silence, a timeout or its own judgement is not approval. A change the
author asks for is a new commit before the next item; a changed decision is an Outcome here. Each
ruling is a row of *Checkpoint log*. A non-interactive run must not execute this plan.

Evidence packets: **numerics** (R1): the 44-site table old → new test, the six exemptions, the NaN
tests, `tests/tier1/test_gates.py` and the gate suites green. **Physics** (R2–R4, R6): the probe's
outcome table per model (`refused`/`live`/`inert` per leaf and value), the bypass table, the
`LEAVES` table by kind with each `stage` consumer, the VER-62 walks unchanged. **User interaction**
(R5, R7, R9): a transcript, run verbatim, of `uv run nanopnp validate` on each case in *Design* §5
(exit code, stderr), a v2 `pnp` case with `--log-level INFO` showing the carry, and the rendered
`CHANGELOG.md` migration section and case-file reference page.

### Work items

- [x] f9878c6 non-Opus 1. [Opus] — a rewritten comparison inverted passes every finite test. Read *Design* §1. `validation/modularity.py` (D1), the 38 rewrites and `NAN_EXEMPT` (D2). Done when `test_nan_gates.py` passes and the gate suites stay green.
- [x] 9d73180 non-Opus 2. [Opus] — an identifier move and upgrade path are read by every case. `io/artefact.py`, `io/case.py` (`upgraded_from`, v2 → v0.5), `core/stages.py`, `io/defaults.py`; the D9 texts. No narrowing yet; v2 documents read unchanged. Done when the D9 tests of `test_case_schema_v05.py` pass and the suite is green.
- [x] 075696e non-Opus 3. [Opus] — a declaration that over- or under-claims refuses a live leaf or passes an inert one. `physics/models.py` (`unread`, D3; switch sets, D5), `pipeline/checks.py` (`_check_unread`, D8's gating), `carry_upgrade` (D10). Update `test_model_interface.py`'s quick-start variants (`pnp-ns`, `pb`, `pb-linear` without corrections; `pnp` with the two switches false, without viscosity and density corrections) and re-record `SOLVE_HASHES` for those four, after showing in the commit body each edited variant's `fingerprint` bit-identical to the unedited one's with `_check_unread` lifted (VER-56 as amended). Repair v2 test documents that wrote an unread value. Done when the D3, D5, D8, D10 tests pass and VER-62 is unchanged at 10⁻⁸.
- [x] fe08c4a non-Opus 4. [Opus] — a part or driver rule wrongly scoped refuses a live case. `materials/models.py`, `pipeline/checks.py` (D6). Done when the D6 tests pass.
- [x] bb6583c non-Opus 5. [Opus] — a classification is a plausible wrong answer. `validation/case_leaves.py` (D4); first, in its own `test:` commit, `test_ver71_stage_leaves_move_their_consumers_key` per D7, shown at P5. Done when every `test_case_leaves.py` test passes. Record VER-61 edges if any.
- [x] ba3b484 non-Opus 6. [any] Retire `nanopnp/case/v1` and `v2` entirely: remove `upgrade_v1`, `CASE_SCHEMA_V1`, `CASE_SCHEMA_V2`, `upgraded_from`, `carry_upgrade`, and `_migration_suffix` from `src/`; delete `test_case_schema_v2.py` and `tests/tier1/data/case_v1/`; migrate Python interpreter range check to `test_case_schema_v05.py`; move all remaining `nanopnp/case/v2` literals in `examples/`, `docs/`, `tests/`, `src/` docstrings and `CLAUDE.md` to `nanopnp/case/v0.5` (writing `variable_density: false, inertia: false` where `pnp` requires them); update IF-03, stage-9 row, §5.3 format table, VER-43 and VER-47 texts (G6). Done when full gate and strict docs build pass.
- [x] 0bbf432 non-Opus 7. [any] REV-13 (D11) and REV-23 (D12): the exact assertions given. Done when both tests pass.
- [x] 0e5a6b7 non-Opus 8. [any] REV-29, REV-34, REV-44, REV-48 (D13). Done when the moved tests pass with unchanged assertions and `--durations` shows the slab solved once.
- [x] bef6f7c non-Opus 9. [any] Records: REV-11, -12, -13, -23, -29, -34, -42, -44, -48, -66 `fixed`; a `REV-nn` row for *Out of scope*'s cross-leaf inertness; `CHANGELOG.md` `0.5.0-alpha.8` with the breaks and the migration section; `docs/project/physics-models.md` lists each model's unread leaves; this plan's status, the phase plan, the brief. Done when VER-63, VER-67, VER-72 and the strict docs build pass.
- [x] 73fc2a6 non-Opus 10. [Opus] Canonical schema constants in `io/artefact.py` and downward adoption. Domain modules (`mesh/adapter.py`, `geometry/region.py`, `geometry/profile.py`, etc.) import schemas from `io/artefact` (D14). Tier-1 test asserts parity between `core/stages.py` descriptions and `io/artefact` constants without creating upward edges. Done when `test_stages.py` and `test_layering.py` pass.
- [x] ab970db non-Opus 10b. [any] Repo-wide schema migration to `v0.5` per author ruling (11 October 2026; G6 extension). Move all schema constants and references across `io/artefact.py`, `core/stages.py`, domain packages, `data/`, `examples/`, `docs/`, and `tests/` to `/v0.5`. Re-pin stage-7 keys in `test_validation_identity.py` and `SOLVE_HASHES` in `test_model_interface.py`. Update `SPECIFICATION.md` §5.3.2 table. Done when full test suite, strict docs build, ruff and mypy pass.
- [x] c8477e1 non-Opus 11. [Opus] StageName enum and stage identifier centralisation in `core/stages.py` (D15). Define `StageName(StrEnum)`, `StageNameLiteral`, `StageIdentifier` in `core/stages.py`; update stage registry definitions and `create()`/`describe()` signatures. Done when `test_stages.py` and `test_cli.py` pass.
- [x] f3e40a3 non-Opus 12. [Opus] Domain defaults modules `mesh/defaults.py` and `numerics/defaults.py` (D16). Wire constants into `io/case.py` Pydantic models, `io/defaults.py`, and `cli/__init__.py` arguments. Done when `test_manifest.py`, `test_case_schema.py`, and `test_cli.py` pass.
- [ ] 13. [any] Test fixture centralisation in `tests/conftest.py` (`make_case_dict`, `case_yaml_template`) (D17). Migrate test files containing inline schema strings to reference `CASE_SCHEMA` or use the fixture. Done when full test suite passes with zero hardcoded schema regressions.

### Verification

| Test | Tier | Identifiers | Oracle |
|---|---|---|---|
| `tests/tier1/test_nan_gates.py` (planned here) | 1 | VER-70, QR-12 | 39 gate classes; synthetic package: 4 violations at their lines, safe forms and `gui/` silent, a stale exemption reported; tree clean, exemptions = D2's six; NaN wall ratio and NaN `psi` abort |
| `tests/tier1/test_case_leaves.py` (planned here) | 1 | VER-71, PHY-21, PHY-22, REV-42, REV-66 | Classification both ways and per kind; `unread` per model exact; switch sets; no solve leaf accepted and inert; with D3 lifted, unread ⇔ inert; Newton settings reach `damped_newton` (37, 1e-7) or are unread; probe solver reached by all six; five refusal texts verbatim; fixed leaves refused; `name` moves no solve key. One plain test (driver live off 1:1) passes today |
| `tests/tier1/test_case_schema_v05.py` (planned here) | 1 | G6, VER-47 | Identifiers; v0.5 reads as itself; unknown identifier text; v2 `pnp` carried with two INFO records, hash equal to the hand-written v0.5 document; written values refused with the migration line; no line for v0.5; v1 through both; mark survives `model_copy` |
| Item 5's stage-key test (written at item 5) | 1 | VER-71 | Each `stage` leaf moves its consumer's key and no upstream key |
| `test_validation_identity.py`, `test_corrections.py` | 1 | VAL-03, VER-05 | D11 hashes; D12 per-ion values to 1e-3 |
| VER-56 tests in `test_model_interface.py` | 1 | VER-56 | As amended; four keys re-recorded under item 3's proof |
| The seven VER-62 walks | 2 | VER-62 | Unchanged at 10⁻⁸ after items 1, 3, 4 |
| `tests/tier1/test_stages.py`, `test_layering.py` | 1 | VER-61, VER-25 | Schema parity between `core/stages.py` and `io/artefact.py` holds; `upward: []` unchanged (D14) |
| `tests/tier1/test_stages.py`, `test_cli.py` | 1 | VER-25 | `StageName` members match registered stage strings; stage lookup accepts enum and strings (D15) |
| `tests/tier1/test_manifest.py`, `test_case_schema.py` | 1 | FR-25 | Mesh and numerics defaults match Pydantic model defaults and `_VALIDATED_DEFAULTS` (D16) |
| `tests/tier1/test_case_schema.py`, full suite | 1 | G6, VER-47 | Full test suite passes; case builder / template fixtures construct valid `CASE_SCHEMA` cases (D17) |

Commands: `uv run pytest <file> -v`; `uv run pytest -m tier1`; `.claude/hooks/gate.sh run`; the docs
command of `CLAUDE.md`. Probe runtime measured at 11 s for six models.

### Out of scope

- Cross-leaf inertness (a leaf inert because of another's value: `variable_density` beside a `none`
  density correction, `dielectric_gradient_forces` beside no permittivity concentration fit, the
  wall distance with every wall part off). VER-71 probes single leaves from each model's base; item
  9 opens a `REV-nn` row for the author.
- REV-71 (stage 10's algorithm revision) and REV-72 (the charge carrying its rule): open, not I2's.
- Recording the upgrade in the FR-25 manifest: the carried document is what is hashed and recorded.
- The desktop shell's editor offering unread leaves: Phase 5 (F5).

### Open questions

None blocking. Close calls the author confirms at their checkpoints: D6's driver refusal (not named
in the ruling question, same class as the wall parts); D8 resolving REV-66; the INFO level of the
carry log (D10); `poisson`'s required, unread `concentration_M` being recorded, not refused.

## Design

### 1. VER-70: the sites (prototype at `c306256`)

Rewritten (38): `charge/deposit.py:517` `deposit`; `charge/kernel.py:277` `check_spacing`;
`charge/protonation.py:1008` `_gate`; `charge/stage.py:563` `check_water_facing`; `density/grid.py:198`
`from_axes`; `density/map.py:190` `_read_interchange`; `geometry/analyte.py:179, 230, 301, 371, 378`;
`geometry/contour.py:723, 743, 808, 819` `measure`; `geometry/region.py:673, 702` `exclusion_shell`,
`:1313` `check_junction`; `mesh/adapter.py:496` `_read_meshio`, `:595` `from_ngsolve`;
`mesh/generate.py:183, 190` `check_wall_size`; `mesh/quality.py:272` `check_quality`;
`post/forces.py:242, 247` `axial_extension`, `:350, 362` `check_extension`; `post/indicator.py:84`
`smoothstep`, `:247, 255` `check_indicator`; `structure/axis.py:408, 418, 424` `gate_axis`, `:510`
`check_z_axis`; `structure/read.py:558` `select_frames`; `validation/apbs.py:337` `check_box`;
`validation/comsol.py:1073` `_read_patch`; `validation/probe.py:539` `_check_within`.

Exempt (6), with reasons for `NAN_EXEMPT`: `structure/axis.py:measure_axis: n < 2` (an integer
order); `mesh/adapter.py:_insert_physical_names: start < 0` (`bytes.find`'s index);
`mesh/adapter.py:_validate: …` (integer indices); `structure/read.py:select: counts[chain] <
COVERAGE_FRACTION * most` (residue counts); `structure/read.py:select_frames: count > len(window)`
(an integer count); `sweep/collect.py:_rectification: …` (its `!=` term is true for a NaN, so a NaN
raises). Exact keys in `test_nan_gates.py`. The prototype is `ver70_probe.py` of this session's
scratchpad; the planned test is the record.

### 2. What each model does not read

`C` = the fifteen correction leaves, `steric.model` and `electrolyte.driver`; `W` = the two
`numerics.wall_distance` leaves; `V` = `numerics.elements.u`, `.p`; `L` = `numerics.nonlinear.max_iter`,
`.rtol`. `epnp-ns`: none. `pnp`: viscosity and density `{model, concentration, wall}`, `V`
(no flow). `pnp-ns`: `C`, `W` (classical: every correction `none`, no wall factor). `pb`: `C`, `V`,
`W`, `numerics.stabilisation` (no transport; `ε_r,f⁰`, PHY-21 NOTE). `pb-linear`: `pb`'s and `L`
(one linear system; `settings` "accepted and unused"). `poisson`: `pb-linear`'s and
`electrolyte.concentration_M` (no ions).

### 3. The probe, measured

At `c306256` with the identifier swapped to v2, `test_case_leaves.py`'s `fingerprint` over
`SOLVE_PROBES` gives inert exactly: under every model the driver, `permittivity.wall`,
`density.wall` (D6); `pnp` the six viscosity and density leaves, `u`, `p`, and `variable_density`,
`inertia` true (D5); `pnp-ns` all seventeen of `C`, `W`, `variable_density` false,
`dielectric_gradient_forces` true; `pb`, `pb-linear` twenty-three (`C`, `V`, `W`, stabilisation);
`poisson` those and `concentration_M`. Everything else is live or refused. With an electroneutral
state (both ions equal), `pnp-ns`'s `concentration_M` read inert: the Poisson source and the body
force vanish there. Hence the fixed state differs per species. Newton probe: 37 and 1e-7 reach
`damped_newton` for `epnp-ns`, `pnp-ns`, `pnp`, `pb`; `poisson`, `pb-linear` complete without it.
Solver probe reached by all six. Cost 11 s.

### 4. Texts

Unread (n = 1 / n > 1): `physics.model '<m>' does not read 1 key this case sets; it would be recorded
in the manifest and never applied (PHY-21, section 5.4.3), so leave it at its default:` /
`… does not read <n> keys this case sets; each would be recorded … so leave each at its default:`,
then per key, in `case_fields` order, `\n  <path>: <value> (default <default>; read by <models>)`;
a bool shown `true`/`false`, any other value by `str`; readers sorted, or `no registered model`.
Parts: `electrolyte.corrections switches off <n> part(s) no correction model applies; it/each would
be recorded in the manifest as a deviation and never applied (PHY-22), so leave it/each at its
default, true:` then `\n  electrolyte.corrections.<p>.<part>: false (<p> model '<model>' has no
<part> fit)`. Driver: as `test_ver71_the_ionic_strength_driver_of_a_one_one_salt_is_refused`.
Identifier: `<source>: expected schema 'nanopnp/case/v0.5', or 'nanopnp/case/v2' or
'nanopnp/case/v1' (each read as its upgrade), found '<x>'`. Carry log and migration line: as
`test_case_schema_v05.py` (the declared identifier substituted for a v1 document). The tests are
the record of each exact string.

### 5. The user-interaction transcript (R5, R7, R9)

`uv run nanopnp validate` on: example 01 (exit 0); example 01 as `pnp-ns` unedited (exit 3, D3's
text, six keys); as `pnp` writing only `flow: false` (exit 3, D5's text); the same declaring v2
(exit 0, with the two carry records at INFO); a `pb` case with `stabilisation: supg`; an `epnp-ns`
case with `permittivity: {wall: false}`; one with `driver: ionic_strength`; one declaring
`nanopnp/case/v0.6`. Each with stdout, stderr and exit code, and no traceback (VER-32).

### 6. Parameter and identifier centralisation (Extension, D14–D17)

- **Schema centralisation (D14):** All 15 canonical schema strings remain declared in `io/artefact.py`.
  Domain modules (`mesh/adapter.py:MESH_SCHEMA`, `geometry/region.py:REGION_SCHEMA`,
  `geometry/profile.py:PROFILE_SCHEMA`, etc.) import directly from `io/artefact.py`. Layering is
  strictly downward: `mesh` and `geometry` already import `io` statically. `core/stages.py` remains
  without an upward static import to `io/artefact.py`; parity between registered `artefact_schema`
  attributes and `io/artefact.py` constants is tested in `tests/tier1/test_stages.py` (VER-25).
- **Stage identifiers (D15):** `core/stages.py` defines `StageName(StrEnum)` covering all 13 stages
  (`case`, `structure`, `density`, `symmetry`, `contour`, `region`, `mesh`, `protonation`, `materials`,
  `charge`, `solve`, `qoi`, `report`), accompanied by `StageNameLiteral` and `StageIdentifier = StageName | StageNameLiteral`.
  `create()`, `describe()`, and `require()` signatures accept `StageIdentifier`, providing IDE autocompletion
  and type-safety while preserving string compatibility across pipelines.
- **Domain sizing and defaults (D16):** Domain-specific constants are grouped at their natural layers:
  `mesh/defaults.py` (`DEFAULT_PORE_RADIUS_NM: Final = 2.0`, `DEFAULT_MEMBRANE_THICKNESS_NM: Final = 4.0`,
  `DEFAULT_RESERVOIR_RADIUS_NM: Final = 10.0`, `DEFAULT_MAXH_NM: Final = 4.0`, `DEFAULT_WALL_H_NM: Final = 0.2`,
  `DEFAULT_CYLINDER_WALL_H_NM: Final = 0.35`); `numerics/defaults.py` (`DEFAULT_NONLINEAR_RTOL: Final = 1e-4`,
  `DEFAULT_NONLINEAR_MAX_ITER: Final = 30`, `DEFAULT_ELEMENT_ORDER_U: Final = 2`, `DEFAULT_ELEMENT_ORDER_P: Final = 1`).
  Pydantic models in `io/case.py`, `_VALIDATED_DEFAULTS` in `io/defaults.py`, and CLI arguments in `cli/__init__.py`
  reference these canonical constants.
- **Test fixtures (D17):** Shared `case_yaml_template()` fixture and `make_case_dict(**overrides)` builder in
  `tests/conftest.py` inject `CASE_SCHEMA`. Tests are progressively migrated to use these helpers, preventing
  widespread test churn on future schema increments.

## Checkpoint log

| Checkpoint | Date | Author's ruling |
|---|---|---|
| P1 | 2026-10-09 | go P1 |
| R1 | 2026-10-09 | approved R1 |
| P2 | 2026-10-09 | go P2 |
| R2 | 2026-10-09 | approved R2 |
| P3 | 2026-10-09 | go P3 |
| R3 | 2026-10-09 | approved R3 |
| P4 | 2026-10-09 | go P4 |
| R4 | 2026-10-09 | approve R4, go P5 |
| P5 | 2026-10-09 | approve R4, go P5 |
| R5 | 2026-10-10 | approved R5 |
| P6 | 2026-10-10 | go P6 |
| R6 | 2026-10-10 | approved R6 and go P7 |
| P7 | 2026-10-10 | approved R6 and go P7 |
| R7 | 2026-10-10 | approved R7 and go P8 |
| P8 | 2026-10-10 | approved R7 and go P8 |
| R8 | 2026-10-10 | approved R8 and go P9 |
| P9 | 2026-10-10 | approved R8 and go P9 |
| R9 | 2026-10-10 | approved R9 |
| P10 | 2026-10-11 | go P10 |
| R10 | 2026-10-11 | approved R10 |
| P10b | 2026-10-11 | Go 10b |
| R10b | 2026-10-11 | Approved R10b, go P11 |
| P11 | 2026-10-11 | Approved R10b, go P11 |
| R11 | 2026-10-11 | Approve R11, go P12 |
| P12 | 2026-10-11 | Approve R11, go P12 |
| R12 | 2026-10-11 | Approve R12, go P13 |
| P13 | 2026-10-11 | Approve R12, go P13 |
| R13 | 2026-10-11 | pending |

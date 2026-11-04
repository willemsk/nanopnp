# WP5.07 — Variables and the rebuild forecast

**Status: planned, not started.** Planned 4 November 2026 on `main` (`4323c95`). It inherits
§8.2.19 U4, §8.2.31 AG2 to AG5 and REV-139.

This plan belongs to [the Phase 5 plan](phase-5-workbench.md). `SPECIFICATION.md` governs. An
identifier here points to a clause and never restates it.

## In brief

**What changes.** A case can define named values, each with its unit, such as a radius of 2 nm or a bias of 50 mV, and
formulas of them. Any number in the case can then be a name or a formula. A value in other units of the same kind is
converted exactly; one of the wrong kind, a voltage where a length belongs, is refused, naming the field. Two cases that come to the same numbers share their stored results. Before a sweep runs, the program
says which steps each swept value will redo and how many meshes and other builds come before the solves, as a warning.

**Cost.** About two weeks. One small, free units library. Reading a case takes a tenth of a second longer.

**What could go wrong.** A formula could run code; a parser accepts only numbers, names, arithmetic and six functions,
and a test tries each forbidden form. A conversion could be off in its last digit; the units library works in exact
fractions, and tests compare exactly. The forecast could disagree with what a sweep redoes; a test runs a small sweep
and compares them step by step. A case without names could change its stored results; the recorded results and the
gated example numbers are checked unchanged.

**Your call.** None open; the round of 3 November 2026 ruled the design.

## Execution brief

**Scope.** FR-39's variables, units, resolved keys and forecast (AG2 to AG5; REV-139). **Depends on:** WP5.06.
**Requirements:** FR-39, FR-24, FR-25, FR-27, IF-03; VER-24, VER-56, VER-61, VER-62, VER-64, VER-72. **Constrained
by:** G6 (`nanopnp/case/v0.6` stays), CON-07, the §5.3.1 NOTE on `models:`. **Implementing session:** Sonnet, high
effort. Tag `v0.6.0-alpha.7`.

**Amended in this commit:** none. **Amended when it lands (item 9):** §5.3.1, a NOTE on `variables:`; §5.3.3, the
inputs group's `variables`; §5.3.4, an axis over a variable and the forecast; §5.5, the optional `forecast_parameters`;
IF-03's and FR-39's Appendix A rows; REV-139 `fixed`.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| D1 Writing a variable | A top-level `variables:` mapping, name to `{value: <number>, unit: <text>}` or `{expression: <text>, unit: <text>}`. A string at a numeric leaf is an expression of variables, unless the field accepts it as a literal (`wall_h_nm: auto`). `variables:` is the study's: a model file holding it or an expression is refused, naming the file and the key | AG2, AG3; a model serves many studies |
| D2 Expressions and units | A walker over `ast.parse(text, mode="eval")` admits numbers, variable names, the four operations, powers, unary signs and six functions; Python evaluates nothing. Units through one `pint.UnitRegistry(non_int_type=Fraction)`. A field's unit comes from its name's suffix (`SUFFIX_UNITS`), else it is dimensionless. Another dimension is refused at the field, naming field, expression and both units; the same dimension is converted. An integer field takes only an integral value | AG2, AG3; float pint gives 20 Å = 1.9999999999999998 nm |
| D3 Resolution and records | `io/models.py` resolves the case's own mapping before it merges any model, so stages and identity see numbers only. `CaseDocument._variables`, a `VariableRecord`, is outside the dump, equality and every hash. `dumps_case` and `Case.dumps(study=True)` write the case as written; a file case keeps its text. The manifest's inputs group gains `variables` only when the case defines some | AG4; FR-25; VER-62 at zero drift |
| D4 Substitution and sweeps | `substitute` sends `variables.<name>`, and every assignment to a document with a record, through `VariableRecord.carried`, which reads the case as written again with the assignments. A number at `variables.<name>` is in its declared unit; a number at a field drops its expression. The sweep's barrier and wall-size checks read a variable axis as the fields it reaches | AG2; §5.3.2's barriers |
| D5 The forecast | `pipeline/forecast.py:keyed_walk` keys a member's stages without running one: an upstream is the stored artefact, else a stand-in whose payload raises `NotBuilt`. A key that raises it takes a forecast identity from the stage, its inputs' identities and its optional `forecast_parameters` (the mesh's), else the case hash. `sweep/forecast.py:forecast` runs it over the points in plan order | AG5, VER-64; a payload is fixed by its artefact's hash |
| D6 Where it shows | `Sweep.forecast()`; `run_plan` logs its warnings before the first wave and never refuses; `nanopnp sweep plan` prints them and adds `forecast` to `--json` | AG5; W2 |

### Grounding

**D1.**
- `io/models.py:reads` validates at once when the mapping has no `models:` key or no v0.6 schema; otherwise it
  `_resolve`s the study with its model files. `CaseDocument` forbids extra keys, so `variables` is popped first.
- `io/models.py:owner_of("variables")` is `"study"`, so `_read_model_file` already refuses `variables:` in a model file
  ("belongs to the study"). A string at a model's numeric leaf fails only pydantic's float check today.
- `io/case_paths.py:case_fields` raises `NotImplementedError` for a mapping whose values are blocks. `variables` is
  therefore no schema field: VER-76's JSON Schema, VER-71's `LEAVES` and `OWNERS` stay unchanged.
- Numeric leaves (`case_fields`, `float` or `int`, not `bool`) carry the suffixes `_nm`, `_ns`, `_V`, `_M`, `_K`, `_e`,
  `_C_m2`. The dimensionless ones are `sharpness` (twice), `isolevel`, `ph`, `radius_scale`, `size_scale`, `rtol`,
  `frames.count`, `species.0.z`, `max_iter` and the values of `physics.solid_permittivities`.
  `numerics.mesh.wall_h_nm` is `float | Literal["auto"]`.

**D2.**
- pint 0.25.3: BSD-3-Clause; needs `flexcache`, `flexparser`, `platformdirs`, `typing-extensions`, all pure Python;
  no NumPy. Import 0.26 s; a registry 0.24 s, built at first use. 0.26 requires Python 3.12, and the floor is 3.11
  (QR-09), so the dependency is `pint>=0.25.3,<0.26`.
- Measured with the fraction registry: 20 Å → 2.0 nm, 3.5 Å → 0.35, 0.3 Å → 0.03, 50 mV → 0.05 V, 100 mM → 0.1 M,
  25 degC → 298.15 K, each `==` the decimal. Float pint gives 20 Å → 1.9999999999999998.
- With the fraction registry, `str()` or `format()` of a unit or dimensionality with a power raises `ValueError`, and
  so does a `DimensionalityError`'s text. A message names the unit texts the case wrote and the suffix table's text.
- pint parses `a` as a year and `M` as molar; an unknown unit raises `pint.UndefinedUnitError`.

**D3.**
- `api/case.py:Case.loads` keeps the file text for a case without models; `Case.source` gives it, and `Session.run`
  records it as the run's `case.yaml`. An edited case or a study writes `dumps_case(self)` instead.
- `CaseDocument.__eq__` and `__hash__` compare `model_dump()`; `CaseArtefact`'s hash is the dump. `models` and
  `_models` are outside both, the precedent for `_variables`.
- `io/manifest.py:input_group(..., overrides=)` adds `overrides` only for a study; `pipeline/run.py:_manifest` passes
  `record.overrides`. `api/sweep.py:plan_sweep` writes the base case with `case.dumps(study=...)`.
- `io/case.py` imports `ModelRecord` under `TYPE_CHECKING`; `io/models.py` imports `io/case_paths.py` at module level.
  So `VariableRecord` lives in `io/models.py`, and `io/variables.py` imports neither.

**D4.**
- `io/case_paths.py:substitute` sends `models.*` through `ModelRecord.carried`, then validates each path with
  `field_at(path).validate`; `_revalidated` reattaches the model record. Callers: `api/case.py:Case.with_`,
  `sweep/plan.py:_member` and `_wall_size_barriers`, `gui/case_model.py`, `validation/costs.py`.
- `sweep/plan.py:_check_axes` calls `field_at(path).validate(value)`, which refuses `variables.a` as an unknown path.
  `_barriers` and `_wall_size_barriers` match axis paths against `WARM_START_BARRIERS` and `WALL_SIZE_PATHS` by prefix.
- `sweep/plan.py:_pairs` pairs points by `boundary_conditions.bias_V` in their assignments.

**D5.**
- A key-only walk on examples 01 and 02 keys `case` and `region`, then fails at `mesh`: `MeshStage._recipe` reads
  `read_region(region.payload["region"])`, though only the region's names, its kind and whether it has an exclusion
  shell enter the key. The names follow from the region's hash.
- On a real mesh, `charge`, `materials`, `solve`, `qoi` and `report` key from keys. `SolveStage._prepare(load=False)`
  calls `deployed_mesh` and discards it; `QoIStage._prepare` reads the mesh for its band and key parameters, and its
  key carries the case hash.
- `RegionStage.key` calls `_profile_input`, which reads `contour.payload["profile"]` and discards it.
- `deployed_mesh` tests `MESH_PAYLOAD not in generated.payload`, so the stand-in raises on `__contains__` as well.
- `pipeline/run.py:stored_upstream` builds stages as `create(name, store=store)` or `create(name)`, with no workspace.
- `api/sweep.py:run_point` walks `plan.case(index, base=base)` beside `plan.base_path.parent`, with the warm start as
  a solve constructor argument outside the key.
- `pipeline/extension.py:FunctionStage.key` reads only input hashes.
- `density/stage.py:atoms_key` drops charge edits, so a charge variant's density keys as its parent's.
- The exclusion shell exists exactly when `charge.exclusion_offset_nm > 0` (`geometry/region.py`); a region is
  idealised exactly when `resolved.pore` is set.

**D6.**
- `cli/__init__.py:_sweep` holds a `Store` for `plan`, and prints `plan.warnings` as `warning` lines and in `--json`.
- A key-is-artefact stage absent from the store is a miss, so the walk records it as not cached.

### Implementation details

**Item 2.** `io/variables.py` holds `Variable` (pydantic, strict: `value: float | None`, `expression: str | None`,
`unit: str = "dimensionless"`, exactly one of the first two); a name matches `[A-Za-z][A-Za-z0-9_]*` and is neither a
function nor `auto`. `FUNCTIONS = ("sqrt", "exp", "log", "abs", "min", "max")`; `exp` and `log` take a dimensionless
argument, `min` and `max` one dimension. The walker admits `Expression`, `BinOp` (`Add`, `Sub`, `Mult`, `Div`, `Pow`),
`UnaryOp` (`UAdd`, `USub`), `Constant` of `int` or `float` (not `bool`), `Name` and `Call` of a `FUNCTIONS` name with
positional arguments; text of at most 256 characters. A number enters as `Fraction(repr(value))`; a power is taken in
floats, its exponent dimensionless, an `OverflowError` refused. `SUFFIX_UNITS = {"_C_m2": "coulomb / meter ** 2",
"_nm": "nanometer", "_ns": "nanosecond", "_V": "volt", "_M": "molar", "_K": "kelvin", "_e": "elementary_charge"}`,
longest suffix first; `field_unit(path)`, `numeric_paths()`, and `resolve(raw, source) -> (dict, Resolution | None)`.
`Resolution` holds `definitions`, `values` (float, declared unit) and `expressions` (path → text). Variables resolve in
dependency order; a cycle is refused naming its members, an unknown name naming it. A field path is generic when its
list indices read `0`, as `case_fields` writes them. Refuse a division by zero and a non-finite result, naming the
expression. Each refusal is a `CaseValidationError` that starts with `source`, and formats no pint object.

**Item 3.** `io/models.py`: split `reads` into `yaml.safe_load` and `read_mapping(raw, *, base, source, model)`, which
calls `io/variables.resolve` on the case's own mapping before the `models:` branch and attaches
`VariableRecord(definitions, values, expressions)` to the result. `VariableRecord.written(mapping)` restores each
expression at its path and puts `variables:` first after `name`. `VariableRecord.reaches(name)` gives the field paths a
variable reaches, through other variables too. `VariableRecord.carried(document, assignments)` takes the study form
(`study_layer`) or the dump, applies `written`, sets the assignments, and returns `read_mapping(..., model=type(document))`
with the model record's `base`. `CaseDocument` gains `_variables` and `variables_record`; `Case` gains `variables`
(definitions) and `expressions` (path → text), each a read-only mapping. The manifest's group is
`{"definitions": {name: {"written": <definition>, "value": <float>, "unit": <text>}}, "fields": {path: {"expression":
<text>, "value": <number>}}}`.

**Item 6.** `core/stages.py`: `class NotBuilt(LookupError)`, raised with the stage name; `@runtime_checkable class
Forecastable(Protocol)` with `forecast_parameters(self, inputs: StageInputs) -> Mapping[str, Canonicalisable]`.
`MeshStage`: factor `_recipe`'s sizing into `_sizing(resolved, *, idealised, exclusion)`; `forecast_parameters` returns
`{"sizing": ...}` for a generated mesh, with `idealised = resolved.pore is not None` and `exclusion =
charge.exclusion_offset_nm > 0`. `RegionStage.key` takes the contour's hash without its payload.
`SolveStage._prepare` calls `deployed_mesh` only when `load` or no mesh artefact is given. No key value moves.

`pipeline/forecast.py`: `keyed_walk(resolved, *, store, stages, planned) -> dict[str, Identity]`, with `Identity =
(hash, built: bool)`. For each stage of `selected_stages(resolved, None, stages=stages)`: try `stage.key(inputs)`. On
success the identity is the key's hash. It is built when neither the store (`store.get(schema, hash)`) nor `planned`
holds it. The stage's upstream for later stages is the stored artefact, or the key with a `_NotBuiltPayload(name)`
whose `__getitem__`, `__contains__`, `__iter__` and `__len__` raise `NotBuilt`. On `NotBuilt` the identity is
`content_hash("nanopnp/forecast/v0.6", {"stage": name, "parameters": <forecast_parameters, else {"case":
case_hash}>}, {input: identity})`, built unless planned. Its stand-in is `Artefact(schema=<the stage's schema>,
parameters={"forecast": identity}, inputs={}, payload=_NotBuiltPayload(name))`. Add each built identity to `planned`.
The case hash is the `case` stage's identity. Build each stage as `stored_upstream` does, with no workspace, and never
call `run`. `forecast(plan, *, store, stages=None)` resolves each point as `run_point` walks it:
`resolve(plan.case(index, base=base), base=plan.base_path.parent)`, in plan order, sharing one `planned` set.

`sweep/forecast.py`: `Forecast(builds: Mapping[str, int], reused: Mapping[str, int], points: tuple[tuple[str, ...],
...], axes: Mapping[str, tuple[str, ...]])` with `summary()` and `warnings()`. `points` lists each point's built stages,
in plan order. An axis moves a stage when two points that differ only in that axis's coordinate differ in the stage's
identity. `warnings()` gives one line per axis that moves a stage before `solve`: the stages it moves, then the builds
of each stage before `solve` whose key is not its artefact, as "axis 'radius_nm' moves case, region, mesh, solve, qoi,
report; 2 region and 2 mesh builds come before the solves".

### Work items

- [x] 33184dd 1. Vet pint (`supermatt:dependency-vetting`); `uv add "pint>=0.25.3,<0.26"`; a `knowledge/07-software-stack/` concept
  with D2's measured facts, its index line, `knowledge/log.md` (D2). Done when the review says so. **Executor:** main.
- [x] ecfc1c2 2. `src/nanopnp/io/variables.py` (D1, D2). Done when rows 1 to 3 and 9 pass. **Executor:** main.
- [x] 3. `io/models.py` (`read_mapping`, `VariableRecord`, the model-file refusal), `io/case.py` (`_variables`,
  `dumps_case`), `io/case_paths.py:substitute`, `api/case.py` (`variables`, `expressions`, `dumps`), `io/manifest.py`,
  `pipeline/run.py:_manifest` (D3, D4). Done when rows 4 and 5 and `uv run pytest -m tier1` pass. **Executor:** main.
- [ ] 4. Compaction checkpoint. **Executor:** main.
- [ ] 5. `sweep/plan.py`: `_check_axes` accepts a variable's number or definition; `_barriers` and
  `_wall_size_barriers` expand a variable axis by `reaches` (D4). Done when row 6 passes. **Executor:** main.
- [ ] 6. `core/stages.py`, `mesh/ingest.py`, `geometry/region.py`, `solve/stage.py`, `pipeline/forecast.py`,
  `sweep/forecast.py`, `api/sweep.py` (`Sweep.forecast`, the log line in `run_plan`) (D5, D6). Done when rows 7 and 8,
  `test_model_interface.py` and `test_layering.py` pass. **Executor:** main.
- [ ] 7. `cli/__init__.py:_sweep`: `forecast(plan, store=store)`; a `forecast  <line>` per warning; `"forecast":
  forecast.summary()` in the payload (D6). Done when `nanopnp sweep plan examples/03-iv-sweep/charged.sweep.yaml` prints
  them. **Executor:** `general-purpose` on Haiku.
- [ ] 8. Compaction checkpoint. **Executor:** main.
- [ ] 9. The Execution brief's amendments; `CHANGELOG.md`; REV-139 `fixed`; Outcome notes. Done when the review says
  so and the strict documentation build passes. **Executor:** main.
- [ ] 10. `.claude/hooks/gate.sh run`: the VER-62 walks unmoved, no re-pin. **Executor:** main.

### Verification

Rows 1 to 6 and 9 are in `tests/tier1/test_variables.py`, rows 7 and 8 in `tests/tier1/test_forecast.py`; each runs by
`uv run pytest <file> -k <word>`.

| Test | Tier | Identifiers | Oracle and tolerance | `-k` |
|---|---|---|---|---|
| 1 `test_fr39_an_expression_off_the_whitelist_is_refused` | 1 | FR-39 | One refusal each: `a.real`, `x[0]`, `__import__('os')`, an unlisted `f(a)`, `sqrt(a, base=2)`, `lambda: 1`, `a if a else a`, `a < 2`, `a and a`, `'2'`, `True`, `[a]`, `*a`, an unknown name, a cycle, 257 characters. with `eval`, `exec` and `compile` patched to raise, a valid case resolves | `whitelist` |
| 2 `test_fr39_a_variable_of_another_dimension_is_refused_at_the_field` | 1 | FR-39 | Refused, naming field and units: an nm variable at `bias_V`; `2*a` there; `a + V`; `exp(a)`, `a` in nm; a declared unit unlike its expression's; 2.5 at `frames.count` | `dimension` |
| 3 `test_fr39_a_conversion_of_the_same_dimension_is_exact` | 1 | FR-39 | `==`: 20 Å → `radius_nm` 2.0; 3.5 Å → 0.35; 50 mV → `bias_V` 0.05; 100 mM → `concentration_M` 0.1; 25 degC → `temperature_K` 298.15; `2*a`, `a` = 2 nm → 4.0 | `exact` |
| 4 `test_fr39_variables_key_by_the_values_they_resolve_to` | 1 | FR-39, FR-25 | The quick-start with `radius_nm: 2*a`, `a` = 1 nm, against the plain case: equal; one `CaseArtefact` hash; one hash per stage through `mesh`. Its `case.yaml` and `inputs.variables` hold `variables:` and `2*a`, `value` 2.0 | `resolve_to` |
| 5 `test_ver62_a_case_without_variables_writes_what_it_did` | 1 | VER-62, VER-24 | The quick-start's `dumps_case` text and manifest hold no `variables`; `SOLVE_HASHES` and `RUNG_HASHES` unchanged | `without` |
| 6 `test_fr39_a_sweep_over_a_variable_moves_every_field_that_uses_it` | 1 | FR-39, FR-24 | `radius_nm: a`, `thickness_nm: 3*a`; axis `variables.a` over 1.5 and 2: both move; the axis is a barrier | `sweep` |
| 7 `test_fr39_the_forecast_equals_the_stages_the_walk_rebuilds` | 1 | FR-39, VER-64 | The `pnp` cylinder of `test_session.py::test_fr24_…`, swept over `geometry.pore.radius_nm` (2, 2.5) × `bias_V` (0, 0.05). Each point's forecast stages equal its walk's uncached stages (`run_plan`, then `Session.read` per member). Radius moves `case`, `region`, `mesh`, `solve`, `qoi`, `report`; bias moves `case`, `solve`, `qoi`, `report`; `builds["mesh"]` is 2. Forecast again: every count 0 | `equals` |
| 8 `test_fr39_the_forecast_never_runs_a_stage` | 1 | FR-39 | With every stage's `run` patched to raise, row 7's forecast completes and the store gains nothing | `never` |
| 9 `test_fr39_every_numeric_field_has_a_unit_or_is_dimensionless` | 1 | FR-39 | Each `numeric_paths()` entry has a `SUFFIX_UNITS` suffix or is listed dimensionless; a test-added `width_um` fails | `unit_or` |
| 10 The VER-62 walks; `test_model_interface.py`, `test_layering.py`, `test_source_conventions.py` | 1, 2 | VER-62, VER-56, VER-61, VER-72 | Unmoved at 10⁻⁸, no re-pin; goldens and layering unchanged; pint imported at module top | `gate.sh run` |

### Out of scope

- The Sweep tool's warning: WP5.11.
- Rectification over a bias set through a variable: `_pairs` reads assignments, so the plan refuses it (no matched
  pair). A `REV-nn` row for WP5.11.
- Variables in model files (D1): a later ruling.
- A forecast for a single run: the shell needs the sweep's.

### Open questions

None.

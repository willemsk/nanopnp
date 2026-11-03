# WP5.05 — Named models and study overrides in the case

**Status: planned, not started.** Planned 3 November 2026, on `v0.6.0-alpha.4`. It inherits §8.2.18 T2, §8.2.28 AD3,
§8.2.31 AG4 and AG5, and AG12 and AG13, ruled at this plan.

This plan belongs to [the Phase 5 plan](phase-5-workbench.md). `SPECIFICATION.md` governs. An
identifier here points to a clause and never restates it.

## In brief

**What changes.** A case can now name a molecular model and a continuum model, each kept in its own file, instead of
holding every value itself. A case that does so is a study. It sets its own run settings, and it may override any value
of the models it names. Each run writes the one complete case it resolved to, which the command line runs as it is. It
records the model files it read and every override, beside the model's value. A study reuses everything its models
built: only the stages an override moves run again. A sweep can now range over the models themselves, such as one study run against three variants. A case can also
name a mesh already in the store by its key. A case that names no model keeps every number and every key.

**Cost.** About a week. A study costs nothing over the equivalent single case. A sweep over models reuses every stage
its members share.

**What could go wrong.** A study and its single-file twin could drift apart; tests run both through one store and
require the second to rebuild nothing. An override could be lost when a study is edited or swept; tests check that it
survives and is recorded.

**Your call.** None open. You ruled the two questions at this plan: a study may override any value, and the sweep over
models belongs to this package.

## Execution brief

**Scope.** The `models:` block, the two model file schemas, their resolution into one complete case, the overrides, the
sweep over models, and `inputs.mesh.artefact` (REV-62). **Depends on:** `v0.6.0-alpha.4`. **Requirements:** FR-39,
FR-32's model files, IF-03, FR-25, FR-27, FR-24, IF-01; VER-24, VER-47, VER-62, VER-64, VER-71. **Implementing
session:** Sonnet, high effort; every item stays `main` except item 9. Tag `v0.6.0-alpha.5`.

**Amended when it lands:** §5.3.1's NOTEs on `models:` and on `inputs:`; §5.3's format table; §5.3.3's inputs group;
§5.2's stage-6 row; FR-39's and IF-03's Appendix A rows; REV-62 `fixed`. In this commit (AG12, AG13): FR-39, its
Appendix A row, and the design document's WB-16 row and *Override* entry.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| D1 Files | A case gains `models: {molecular: <path>, continuum: <path>}`, at least one. A model file holds `schema` (`nanopnp/molecular-model/v0.6` or `nanopnp/continuum-model/v0.6`), `name`, and only the keys its kind owns. Ownership is one table, `io/models.py:OWNERS` (item 2's rows), by longest dotted prefix; every other path is the study's. A relative path reads beside the file that names it. A model names no model | WB-11, WB-16, FR-32. The suites read the table. The case keeps `nanopnp/case/v0.6` (G6) |
| D2 Resolution | The study's mapping is merged over the molecular, then the continuum, model's: mappings key by key, a list or free mapping whole. The result validates once. A named model must hold every required value of its kind: the *view* (the models under the study's own keys only) must validate, or the model is refused, naming its file. A refusal names the case path and the file the value came from | WB-11. A model that cannot stand alone cannot be reused |
| D3 Identity | `models` is left out of the case artefact's parameters, `dumps_case`, `Case.__eq__` and `Case.__hash__`. So a study equals its resolved case and shares its keys, and a case without `models` keeps every key. The resolved case is `case.yaml` and `case_text`. `inputs.files` gains roles `models.molecular` and `models.continuum`, and `inputs` gains `overrides` when the case names a model | FR-39; FR-25; VER-62 at zero drift; AG4's rule, applied to models |
| D4 Overrides | An override is a leaf of a named model's domain whose value in the case differs from the view's. A leaf is the deepest path where both sides are blocks; a value equal to the model's is none. It is recomputed on every `substitute`, so it survives `with_` and sweeps. `Case.overrides` maps path to `(model value, study value)`. `Case.dumps(study=True)` writes the study as written: `schema`, `name`, `models` (absolute), every study-owned block and every override | AG12. WB-28's outlined mark reads it; the API sweep's base file needs the study form |
| D5 Model sweep | In `substitute`, an assignment to `models.molecular` or `models.continuum` merges again: the new model files, under the study's own leaves and its overrides. A relative path reads against the study's directory. Other assignments apply after it. The sweep plan's files include the model files | AG13. A sweep file and `session.sweep` both build members through `substitute` |
| D6 REV-62 | `inputs.mesh.artefact` takes a 64-character store hash. The mesh stage takes the store (`takes_store=True`), and its key is the stored stage-6 artefact unchanged, so a stored generated mesh keeps its hash. An absent hash is refused, naming the store's root; so are `format` and `groups`. A supplied path's refusals hold: no `structure:` or `geometry:`, `numerics.mesh` at its defaults | T2. A stored mesh is gated already; its frame against a structure is unknown |

### Grounding

**D1.**
- `io/case.py:CaseDocument` has no `models` field. `SuppliedArtefact` already has `path` or `artefact`.
- `io/case_paths.py:case_fields`, `block_paths` and `path_fields` read the schema. A `Path` field under `models` joins
  `path_fields`, so `api/case.py:_rebased_paths` makes it absolute in `with_`.
- `validation/case_leaves.py:LEAVES` must classify `models.molecular` and `models.continuum` (VER-71). It lists
  `inputs.mesh.artefact` as `fixed`, "deferred to v0.6".
- `io/case_paths.py:field_path` maps a bare name to its leaf. No leaf is named `molecular` or `continuum` today.

**D2.**
- `io/case.py:read_case` and `read_case_text` call `_validate(raw, source, model)`, which checks `schema` and runs
  `model_validate`. They take no base directory.
- Readers of a case file: `pipeline/case.py:load_case` and `loads_case` (sweep plans, the Qt shell, run directories), and
  `api/case.py:Case.load` and `Case.loads` (the command line, reproduction, `validation/`). `validation/costs.py`
  reads example cases with `read_case`.
- `io/` imports only `core` and `io` at module scope (`docs/project/modularity-layering.yaml`). `io/models.py` may
  import `io/case.py` and `io/case_paths.py`, so `io/case.py` cannot import it.
- `io/case.py:render_problems(source, error)` renders one line per pydantic location.
- `io/case_paths.py:schema_default`, `api/case.py:_rebased_paths` and `core/paths.py:names_a_path` already exist.

**D3.**
- `io/artefact.py:CaseArtefact` hashes `document.model_dump(by_alias=True, mode="json")`. Its hash keys stage 11
  (`post/stage.py:QoIStage.key`), stage 12 and `pipeline/run.py:_run_key`.
- Stages 1 to 8 and 10 key on their own slices. `io/resolved.py:solve_provenance` drops `name`, `outputs` and `schema`.
- `pipeline/run.py:read_run` requires `case.yaml` to equal `manifest.case_text` and loads it with `loads_case`.
- `api/case.py:Case.source` returns `_text`, or `dumps()` when `_text` is `None`. `Session.run` passes it to
  `run_document` as `case_text`.
- `pipeline/run.py:input_files(resolved, case_path)` builds `inputs.files` by role. `io/manifest.py:input_group`
  hashes each file at run time.
- `api/case.py:Case.__eq__` and `__hash__` compare `model_dump()`.

**D4.**
- `io/case_paths.py:substitute` dumps, sets, then calls `type(document).model_validate`, which drops private
  attributes. `Case.with_` and `sweep/plan.py:_member` both go through it.
- `api/sweep.py:plan_sweep` writes `case.dumps()` as the sweep's base file, refuses a relative input path, and
  rebuilds every member from that file.

**D5.**
- `sweep/plan.py:_check_axes` validates each axis path with `field_at(path).validate(value)`.
- `sweep/plan.py:_planned_files` digests `input_files(member, None)`, and `SweepPlan.base_case` re-checks
  `CaseArtefact(base).hash`.
- `sweep/document.py:Axis.points` expands `path:` and `values:`.

**D6.**
- `pipeline/checks.py:require_runnable` and `mesh/ingest.py:_source_path` raise `io/case.py:stored_artefact_refused`.
  `pipeline/checks.py` refuses `structure:` or `geometry:` beside `inputs.mesh`. `CaseDocument._check_supplied`
  refuses a non-default `numerics.mesh` beside it.
- `mesh/ingest.py:MeshStage.key` ingests a supplied path. `deployed_mesh(resolved, generated)` ingests
  `resolved.mesh` whenever it is not `None`.
- `core/stages.py`: the mesh stage has `takes_store=False`. `charge/protonation.py:ProtonationStage.__init__` shows
  the `store=` pattern, and `pipeline/run.py:_Walk.construct` passes it.
- `io/store.py:Store.get(schema, digest)` returns the stored artefact, or `None`. A stored mesh's schema is
  `io/artefact.py:MESH_ARTEFACT_SCHEMA`. `_resolve_stage`'s `get_or_compute` returns a key the store holds.
- Other readers of `resolved.mesh`: `sweep/plan.py:_gate_meshes` (asserts a path), `solve/state.py:wall_distance_remedy`,
  `pipeline/run.py:input_files` (path only) and `gui/render.py`.

### Implementation details

**Item 1.**
- `io/case.py:Models(_Strict)`: `molecular: Path | None = None`, `continuum: Path | None = None`. A validator refuses
  both `None`. `CaseDocument.models: Models | None = None`. Export `Models` from `nanopnp/case.py`.
- In `io/case.py:_validate`, a mapping with `models` raises `CaseValidationError`: "<source> names models:; read it with
  nanopnp.case.Case.load or nanopnp.pipeline.case.load_case, which resolve them". Add public
  `validate_mapping(raw, source, model)`: `_validate` without that check.
- `dumps_case` and `CaseArtefact` dump with `exclude={"models"}`.

**Item 2.** `io/models.py`:
- `OWNERS` rows. Molecular: `structure`, `charge.ph`, `charge.forcefield`, `charge.titration`, `charge.edits`,
  `inputs.pqr`. Continuum: `geometry`, `charge.exclusion_offset_nm`, `numerics.mesh`, `inputs.mesh`, `inputs.profile`,
  `physics`, `electrolyte`, `boundary_conditions`.
- `MOLECULAR_SCHEMA`, `CONTINUUM_SCHEMA`; `Kind = Literal["molecular", "continuum", "study"]`; `OWNERS: dict[str, Kind]`
  (D1); `owner_of(path) -> Kind`, by longest prefix, with `"study"` as the default.
- `ModelFile(kind, name, path, sha256)` and `ModelRecord(files, view, overrides, base)` are frozen dataclasses.
  `view` is a `CaseDocument`.
- `read(path, *, model=CaseDocument)` and `reads(text, *, base=None, source, model)`. Without `models`, they call
  `validate_mapping`. With `models`:
  1. Read each file named. Refuse a missing file, a wrong `schema`, a missing `name`, a `models` key and any key whose
     owner is not the file's kind. Each refusal names the file and the key.
  2. Rebase each relative path leaf (`path_fields()`, and each correction leaf where `names_a_path`) against the model's
     directory.
  3. `merged = merge(molecular, continuum, study)`; `view = merge(molecular, continuum, study minus every leaf in a
     named model's domain)`.
  4. Validate the view, then the merged mapping, each with `validate_mapping`. Before raising, append to each problem
     line the file its path came from, by longest prefix (`origins`).
  5. Attach `ModelRecord` to the document's private `_models`, with `overrides = differences(document, view)`.
- `differences(document, view) -> dict[str, tuple[FieldValue, FieldValue]]` walks both `model_dump(mode="json",
  exclude={"models"})` together. It recurses where both sides are dicts and the path is in `block_paths()`, compares
  elsewhere, and keeps the paths whose owner is a named kind.
- `carried(document, record, assignments) -> CaseDocument`: with an assignment under `models.`, it re-reads the models
  as in step 1, rebuilds the study layer (the study-owned leaves of `document`, then `record.overrides`' study values),
  merges again, and applies the remaining assignments. Without one, it recomputes `overrides` against `record.view`. A
  relative path resolves against `record.base`, and a path equal to the record's does not re-read.

**Item 3.**
- `CaseDocument` gains `_models: ModelRecord | None = PrivateAttr(None)`, typed under `TYPE_CHECKING`, and a read-only
  `models_record` property.
- `io/case_paths.py:substitute` calls `carried` when `document.models_record` is set. A `models.*` path goes
  through `carried` alone.
- `pipeline/case.py:load_case` and `loads_case` call `io/models.py:read` and `reads`.
- `Case.loads(text, base=…)` calls `reads(…, base=base, model=cls)`. For a study, `_text` is `None`, so `source.text` is
  the resolved `dumps()`.
- `Case.__eq__` and `__hash__` exclude `models`.
- `Case.overrides` returns `MappingProxyType`, empty without models.
- `Case.dumps(*, study: bool = False)` and `dump(path, *, study=False)`. `study=True` on a case without models raises
  `ValueError`.

**Item 4.**
- `pipeline/run.py:input_files` adds `models.<kind>` per `ModelFile`.
- `io/manifest.py:input_group(…, overrides=None)` writes `overrides: {path: {"model": a, "study": b}}` only when it is
  not `None`. `build` passes it, and `_manifest` passes `walk.document.models_record`'s.

**Item 5.**
- `api/sweep.py:plan_sweep` writes `case.dumps(study=True)` when the case names models.
- `sweep/plan.py:_check_axes` accepts a `models.*` path whose value names an existing file.

**Item 7.**
- `io/case.py:SuppliedArtefact.artefact` matches `^[0-9a-f]{64}$`.
- `require_runnable` allows it on `mesh` and refuses `format` or `groups` beside it.
- `core/stages.py`: the mesh stage gets `takes_store=True`. `MeshStage.__init__(…, store=None)`.
- `MeshStage.key`, for a store-named mesh: `self._store.get(MESH_ARTEFACT_SCHEMA, hash)`. It raises
  `FileNotFoundError` naming the hash and `store.root` when the result is `None`, as `_source_path` does for a missing
  path, and `ValueError` when there is no store.
- `deployed_mesh` ingests only a supplied path; otherwise it reads `generated`'s payload.
- `_gate_meshes` skips an artefact as it skips a generated mesh. `wall_distance_remedy` names the hash.

### Work items

- [x] 32dee19 1. `io/case.py:Models`, `CaseDocument.models`, `validate_mapping`, the `models:` refusal, `dumps_case` and `CaseArtefact` exclusions; `nanopnp/case.py`; `validation/case_leaves.py` (D1, D3). Done when `uv run pytest -m tier1 -k "case or manifest or leaves"` passes. **Executor:** main.
- [x] 22ac84c 2. `io/models.py`: `OWNERS`, the readers, `differences`, `carried`; row 6 (D1, D2, D4). Done when row 6 passes. **Executor:** main.
- [x] f7c2456 3. The private record, `substitute`, the loaders, `Case.overrides`, `Case.dumps(study=)`; rows 1 and 3 (D2 to D4). Done when those rows pass. **Executor:** main.
- [x] 7492fbd 4. `input_files`, `input_group`, `_manifest`; rows 2 and 4 (D3). Done when those rows pass. **Executor:** main.
- [x] 50059fc 5. `api/sweep.py`, `sweep/plan.py`; row 5 (D5). Done when row 5 passes. **Executor:** main.
- [x] 6. Compaction checkpoint. **Executor:** main.
- [ ] 7. REV-62: `SuppliedArtefact`, `require_runnable`, the mesh stage's store, `deployed_mesh`, `_gate_meshes`, `wall_distance_remedy`; `inputs.mesh.artefact` reclassified in `LEAVES`; row 7 (D6). Done when row 7 passes. **Executor:** main.
- [ ] 8. `tests/tier2/test_named_models.py`, row 8. Done when it passes. **Executor:** main.
- [ ] 9. The clauses of the Execution brief; `CHANGELOG.md`; `cli/reference.py`'s prose on `models:`; REV-62 `fixed`; a REV row for a stored mesh beside a structure (D6). Done when the code and review say so, and the strict documentation build passes. **Executor:** `general-purpose` on Sonnet.

### Verification

Fixtures: model files in `tmp_path`, split by `OWNERS` from `examples/01-quickstart/quickstart.case.yaml` and
`examples/07-pdb-to-charged-run/2wcd.case.yaml`; runs through `Session(Store(tmp_path / "store"), write=False)`.

| Test | Tier | Identifiers | Oracle and tolerance | Command |
|---|---|---|---|---|
| `tests/tier1/test_models.py::test_fr39_a_study_resolves_to_its_case_written_inline` | 1 | FR-39, IF-03 | Examples 01 and 07: `Case.load(study)` equals `Case.load(example).with_()`, with equal `CaseArtefact` hashes and no overrides; `Case.loads(study.dumps())` equals the example | `uv run pytest tests/tier1/test_models.py` |
| `tests/tier1/test_models.py::test_fr39_a_study_reuses_every_stage_its_twin_built` | 1 | FR-39, VER-64 | Example 01 run `upto="mesh"` inline, then as a study in the same store: every stage record is `cached`, with equal hashes | same |
| `tests/tier1/test_models.py::test_fr39_an_override_moves_only_the_stages_that_read_it` | 1 | FR-39, VER-64 | After the base study: overriding `geometry.pore.radius_nm: 2.5` recomputes `region` and `mesh`, with `overrides` `{"geometry.pore.radius_nm": (2.0, 2.5)}`; overriding `bias_V: 0.1` recomputes only `case` through `mesh`; `bias_V` at the model's value lists nothing; both survive `with_(outputs=["current"])` | same |
| `tests/tier1/test_models.py::test_fr39_a_run_records_its_model_files_and_overrides` | 1 | FR-39, FR-25, VER-24 | `inputs.files["models.continuum"].sha256` is the file's digest; `inputs.overrides` equals `Case.overrides`; `case_text` is `case.dumps()`; example 01's manifest has no `overrides` | same |
| `tests/tier1/test_models.py::test_fr39_a_sweep_over_models_resolves_each_member` | 1 | FR-39, FR-24 | `substitute(study, {"models.continuum": b})` equals the study naming `b`, overrides included; a sweep file's plan gives the same members and lists both files; `Case.loads(case.dumps(study=True), base=…)` equals `case`, `overrides` and `models` | same |
| `tests/tier1/test_models.py::test_fr39_every_case_leaf_has_one_owner` | 1 | FR-39 | Every path of `case_fields()` and `block_paths()` has one owner. Every `OWNERS` row names a path of the schema | same |
| `tests/tier1/test_mesh_ingest.py::test_a_mesh_named_by_store_key_is_the_stored_artefact` | 1 | FR-27 (REV-62) | After example 01 `upto="mesh"`, a case naming that mesh's hash, without `geometry:`, gets a `cached` mesh of that hash; `deployed_mesh` gives the generating case's element count and content hash | `uv run pytest tests/tier1/test_mesh_ingest.py -k store_key` |
| `tests/tier2/test_named_models.py::test_fr39_a_study_rebuilds_only_what_its_override_moves` | 2 | FR-39, VER-26 | `wall_h_nm: 1.0`. After the base study: `bias_V: 0.1` leaves `region`, `mesh`, `materials` `cached` and computes `solve`, `qoi`, `report`; `outputs: [current]` leaves `solve` `cached`; a sweep over `models.continuum` [base, base at 0.1 V] leaves both members' `region` to `solve` `cached` | `uv run pytest tests/tier2/test_named_models.py` |
| The VER-62 walks | 2 | VER-62 | Unmoved at 10⁻⁸, with no re-pin | `.claude/hooks/gate.sh run` |

### Out of scope

- The project folder, its index and writing model files from the library: WP5.08 (FR-32).
- The suites that edit models and mark overrides: WP5.09 to WP5.11.
- Variables in a model file, and the forecast over a model axis: WP5.07 (AG2 to AG5).
- A stored mesh beside a structure: refused (D6); a REV row.

### Open questions

None. The author ruled AG12 and AG13 at this plan.

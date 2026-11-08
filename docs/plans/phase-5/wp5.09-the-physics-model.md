# WP5.09 — The physics model

**Status: delivered, 8 November 2026.** Planned 6 November 2026 on `main` (`4de067b`). It inherits §8.2.34 AJ2, AJ3, AJ5
and AJ10, and the author's rulings at this plan, §8.2.35 AK1 to AK3.

This plan belongs to [the Phase 5 plan](phase-5-workbench.md). `SPECIFICATION.md` governs. An identifier here points to
a clause and never restates it.

## In brief

**What changes.** The equations, the salt, the voltages and the walls become a model of their own, a physics model,
which a study pairs with a molecule and a pore. One set of physics can then serve many pores, and a pore many salts,
without either being rebuilt. Importing a case now writes three models and a study instead of two models and a study.
Each model also names the few values a study shows first: the salt and the voltage for physics, the pH for a molecule,
the mesh fineness for a pore. A model may name its own. Nothing a case computes changes, and no stored result is
rebuilt.

**Cost.** About three to four days. No new library.

**What could go wrong.** A study could resolve to a slightly different case, which would rebuild stored results; a test
checks that the example cases split three ways keep every stored result, and the recorded example numbers stay
checked. Model files written in the last two weeks, with the salt inside a pore model, are refused, naming the value
and the model it now belongs to; nothing reads them wrongly. A pore paired with a stronger salt may build a new mesh;
the sweep's warning already says so, and a test checks it.

**Your call.** None open. On 6 November 2026 you ruled the three open points: the wall-distance setting belongs to the
physics, the pore's mesh follows the physics' salt unless pinned, and each kind has a default list that a file may
replace.

## Execution brief

**Scope.** The physics model of AJ2 and AJ3, its place in the project folder, and AJ5's exposed values. **Depends
on:** WP5.08 (the project folder). **Requirements:** FR-39, FR-32, FR-25, FR-34, IF-03; VER-24, VER-53, VER-62,
VER-71, VER-78. **Constrained by:** G6 and F4 (`nanopnp/case/v0.6` stays; a model schema may change before v1.0),
VER-56. **Implementing session:** Sonnet, high effort. Tag `v0.6.0-alpha.9`.

**Amended in this commit:** §5.3.1's NOTE on `models:` and the project NOTE; §5.3.2's model row; §5.3.3's inputs
group (AJ2, AJ3, AK1 to AK3). **Amended when it lands (item 7):** FR-39's and FR-32's Appendix A rows.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| D1 The physics kind | Schema `nanopnp/physics-model/v0.6`, named by `models.physics`. `OWNERS` moves `physics`, `electrolyte` and `boundary_conditions` from continuum to physics, and adds `numerics.elements`, `numerics.stabilisation` and `numerics.wall_distance` to physics. The merge reads molecular, continuum, then physics | AJ3; AK1, ruled by the author; decided by the plan for the order, which no disjoint table can feel |
| D2 The wall mesh | No code: `resolve_wall_size` already reads the resolved case's electrolyte. A test pins that a continuum model's mesh follows the paired physics' salt, and that `wall_for_concentration_M` pins it | AK2, ruled by the author |
| D3 Exposed values | `EXPOSED`, a default list per kind in `io/models.py`; a model file's optional `exposes:` replaces it. `ExposedValue(name, path, unit, low, high, default)`, carried on `ModelFile.exposed`; unit from `field_unit`, bounds from the declared range else `schema_bounds`, default from the model's own value else `schema_default`. `exposes:` never enters the merge | AJ5; AK3, ruled by the author; decided by the plan for the record's shape |
| D4 The project | `ITEM_KINDS`, `FOLDERS` (`models/physics`), `Library.physics` and `LIBRARY_FIELDS` gain physics; `_split` writes three models. A physics item or path points to the Continuum suite (`_SUITE_OF["physics"] = "continuum"`), which holds *Physics defaults* until WP5.15 adds the Physics suite. The frame's rail and changed list read physics models | AJ2; FR-32, FR-34; decided by the plan |
| D5 Earlier model files | A continuum file holding a physics key is refused by the existing ownership check, which now names the owning kind; no migration | F4, G6: no release holds the format; decided by the plan |
| D6 Records and sweeps | `models.physics` reaches the manifest's input files, the sweep axis and `Case.with_` through the existing generic paths; VER-71's `LEAVES` gains `models.physics` as provenance | FR-39, FR-25, VER-71; decided by the plan |

### Grounding

**D1.**
- `io/models.py:OWNERS` is the one table; `owner_of` takes the longest prefix. `Kind`, `MODEL_KINDS`, `SCHEMAS`,
  `ModelFile.kind`, `_read_model_file` and `check_model_file` type the kinds as `Literal["molecular", "continuum"]`.
- `_resolve`, `_prune`, `differences`, `study_layer`, `check_dropped` and `ModelRecord.carried` loop over
  `MODEL_KINDS` or `record.kinds`, so a third kind reaches them through the table. `_named_files` and
  `ModelRecord.carried` spell "molecular, continuum" in their refusals.
- `io/case.py:Models` has `molecular` and `continuum`; `_names_one` refuses neither. `models` is excluded from every
  dump and hash, so keys cannot move.
- `numerics` holds `elements`, `mesh`, `nonlinear`, `continuation`, `stabilisation`, `wall_distance` and `linear`.
  The quick-start's study keeps `numerics.continuation` and its physics model gets `numerics.stabilisation`.
- `numerics.wall_distance` is read by `pipeline/case.py` into `ResolvedCase.wall_distance_*`, and recorded as a
  deviation through `io/defaults.py`; both read the resolved document.

**D2.**
- `mesh/sizing.py:resolve_wall_size` reads `document.electrolyte` and `numerics.mesh` of the resolved case;
  `WallSize.key` carries the resolved `wall_h_nm`, `source` and `size_scale`, not the salt.
- `sweep/forecast.py:forecast` over a `models.physics` axis counts `builds["mesh"]` without running a stage.

**D3.**
- `io/variables.py:field_unit(path)` gives the unit text; `numeric_paths()` holds `electrolyte.concentration_M`,
  `boundary_conditions.bias_V`, `charge.ph` and `numerics.mesh.size_scale`.
- `Charge.ph` carries `Ge(0.0)`, `Le(14.0)` in `FieldInfo.metadata`; `Mesh.size_scale` carries `Gt(0.0)`.
  `case_paths.schema_default` walks `FieldInfo` per path; `schema_bounds` follows it.
- `_read_model_file` strips `schema` and `name` before the owner check; `exposes` joins them. `api/project.py:_body`
  strips the same two for `mapping_changes`, which would read `exposes` as a leaf.
- `Project._copy_model` copies a model body whole, so `exposes:` survives an import.

**D4.**
- `io/project.py:ItemKind`, `ITEM_KINDS`, `FOLDERS`, `Library`, `LIBRARY_FIELDS`; `Library` forbids extras and
  defaults each list, so an older project file reads.
- `api/project.py:_split` builds `layers` for molecular, continuum and study and writes each `MODEL_KINDS` layer;
  `_bodies` and `_problems_of` loop over fixed kinds; `_owner_suite` maps `owner_of` through `_SUITE_OF`.
- `gui/web/screens.py:SUITES` has four suites; Continuum's tools end in *Physics defaults*.
  `gui/web/frame.py:KINDS` and `listed_changes` list molecular, continuum and study.
- `gui/web/states.py:boot`'s `refused` state replaces `bias_V: 0.05` in the continuum model. After the split, the
  continuum model of the charged tube holds `radius_nm: 30.0` once, and `test_gui_screens.py` expects a
  `continuum/` problem.

**D5.**
- `_read_model_file` refuses each leaf whose `owner_of` differs from the file's kind ("belongs to the …"). No
  shipped example holds a model file; the tests' `split_case` and tier 2's `_study` write them.

**D6.**
- `pipeline/run.py` writes `files[f"models.{kind}"]` per `record.files`; `io/manifest.py` writes `overrides` generically.
- `api/sweep.py` rebases any `models.` axis beside the study; `sweep/plan.py` checks any `models.` value is a file.
- `validation/case_leaves.py:LEAVES` lists `models.molecular` and `models.continuum`; `test_case_leaves.py` asserts
  the provenance set. `cli/reference.py` spells the ownership and the model axes in prose.

### Implementation details

**Item 1.** `ModelKind = Literal["molecular", "continuum", "physics"]`; `Kind = ModelKind | Literal["study"]`;
`PHYSICS_SCHEMA = "nanopnp/physics-model/v0.6"`. `OWNERS` gains `numerics.elements`, `numerics.stabilisation` and
`numerics.wall_distance` under physics, and `physics`, `electrolyte` and `boundary_conditions` move to it. The
ownership refusal reads `f"{path}: {leaf}: belongs to the {owner} model, not to a {kind} model"` (or `the study`), so
an old continuum file names `electrolyte.…` and *physics model*. Refusals list "molecular, continuum, physics".
`Models.physics: Path | None` with a description beside its siblings; `_names_one` names all three.
`LEAVES["models.physics"]` as provenance. `cli/reference.py` names the three kinds and the three axes.

**Item 2.** In `io/models.py`:

```python
@dataclass(frozen=True)
class ExposedValue:
    name: str
    path: str
    unit: str
    low: float | None
    high: float | None
    default: FieldValue


EXPOSED: dict[ModelKind, tuple[tuple[str, str], ...]] = {
    "molecular": (("pH", "charge.ph"),),
    "continuum": (("size_scale", "numerics.mesh.size_scale"),),
    "physics": (
        ("concentration", "electrolyte.concentration_M"),
        ("bias", "boundary_conditions.bias_V"),
    ),
}
```

`exposed_values(kind, raw, source) -> tuple[ExposedValue, ...]` takes the file's whole mapping, before `schema`,
`name` and `exposes` are stripped: it reads `raw.get("exposes")`, else the default list, and each default from `raw`;
it refuses each case of the NOTE, naming `source` and the entry. `ModelFile` gains
`exposed: tuple[ExposedValue, ...] = ()`. `case_paths.schema_bounds(path) -> tuple[float | None, float | None]` reads
`Ge`/`Gt` and `Le`/`Lt` from the field's metadata; an open bound is given as its limit, and the checks treat a range
as closed, since it only guides. `_body` drops `exposes`.

**Item 3.** `ItemKind`, `ITEM_KINDS` and `LIBRARY_FIELDS` gain physics; `FOLDERS["physics"] = "models/physics"`;
`Library.physics: list[str]`; `_SUITE_OF["physics"] =
"continuum"`, with the comment that WP5.15 gives it its own suite. `_split`'s layers and `_bodies` loop over
`MODEL_KINDS`. `frame.py:KINDS` gains `("physics", "Physics models", "continuum")`; `listed_changes` loops
over molecular, continuum, physics and study; the glossary's *Model* names three kinds. `states.py` replaces
`radius_nm: 30.0` with `radius_nm: wide` and raises if the text is absent.

**Item 1's tests.** `split_case`'s default `models` becomes the three kinds, with `PHYSICS_SCHEMA` in `schemas`. Each
test that edits `boundary_conditions` in `continuum.yaml` edits `physics.yaml`. Tier 2's `_study` writes `geometry` and
`numerics.mesh` to `continuum.yaml`, and `electrolyte`, `boundary_conditions`, `physics` and `numerics.stabilisation`
to `physics.yaml`. Its model sweep ranges over `models.physics`. `test_project.py`'s FR-34 fixture splits `CONTINUUM`
into `models/continuum/tube.yaml` (`geometry`, `numerics`) and `models/physics/tube.yaml` (`electrolyte`,
`boundary_conditions`, `physics`), which `STUDY` names too; `physics.flow`'s owner is physics, and
`changes("physics", "tube")` holds it. `test_case_leaves.py`'s provenance set gains `models.physics`.

**Item 4.** Row 5 copies the split's `physics.yaml` to four files at 0.1, 0.5, 3 and 5 M, sets the split continuum
model's `wall_h_nm` from the quick-start's 0.35 to `auto`, and reads
`plan_sweep(case, session=Session(Store(tmp_path / "store"), write=False), axis="models.physics", values=[…],
check_meshes=False).forecast().builds["mesh"]` over two files at a time, against an empty store.

### Work items

- [x] a03086f 1. `src/nanopnp/io/models.py`, `src/nanopnp/io/case.py`, `src/nanopnp/validation/case_leaves.py`,
  `src/nanopnp/cli/reference.py`, with the split fixtures of `tests/tier1/test_models.py`,
  `tests/tier1/test_project.py`, `tests/tier1/test_case_leaves.py` and `tests/tier2/test_named_models.py` in the same
  commit, since the hook runs Tier 1: the physics kind and its ownership (D1, D5, D6); done when rows 1 to 3, 6 and 8
  pass. **Executor:** main.

  > **Outcome — item 1 carried the project's physics kind and the refused state.** `_split` writes a physics
  > model and `problems()` walks every item kind, so Tier 1 needed `io/project.py`'s kinds, `_SUITE_OF`, `_split`
  > and `_bodies` in this commit; `test_gui_screens.py` also asserted `bias_V` in the refused problem, and now
  > asserts `radius_nm`. Item 3 keeps the frame.
- [x] 34b5f14 2. `src/nanopnp/io/models.py`, `src/nanopnp/io/case_paths.py`, `src/nanopnp/api/project.py:_body`,
  `tests/tier1/test_models.py`: exposed values (D3); done when row 4 passes. **Executor:** main.
- [x] b09cf2c 3. `src/nanopnp/io/project.py`, `src/nanopnp/api/project.py`, `src/nanopnp/gui/web/frame.py`,
  `src/nanopnp/gui/web/states.py`, `tests/tier1/test_project.py`: the project and the frame (D4); done when rows 7
  and 9 pass. **Executor:** main.
- [x] d039cdc 4. `tests/tier1/test_models.py`: row 5, the wall following the physics salt (D2); done when it passes.
  **Executor:** main.
- [x] 5. Compaction checkpoint. **Executor:** main.
- [x] 6. `.claude/hooks/gate.sh run` and the strict documentation build, which item 1's reference text and
  `Models.physics` description regenerate: VER-62's walks unmoved, no re-pin. **Executor:** main.

  > **Outcome — the gate passed and the walks did not move.** `gate.sh run` passed in 250 s at `3f6d7b7`, and the
  > strict documentation build passed with no `mkdocs.yml` change. On the deployed meshes the golden holds, example
  > 01's largest relative drift is 6.9 × 10⁻¹⁴ (`eof_m3_s`) and example 02's ePNP-NS walk's 1.1 × 10⁻¹⁶
  > (`currents_A[Cl-]`), both well within 10⁻⁸; no re-pin. `np-gui render shell` showed no page error and no failed
  > contrast, non-text or target check; the rail lists *Physics models*, and the refused state lists
  > `continuum/charged-tube` at `geometry.reservoir.radius_nm`.
- [x] 7. FR-39's and FR-32's Appendix A rows name the tests; `CHANGELOG.md`; Outcome notes; `current.md`. Done when
  the review says so. **Executor:** main.

### Verification

Rows 1 to 6 are in `tests/tier1/test_models.py`, row 7 in `tests/tier1/test_project.py`, row 8 in
`tests/tier2/test_named_models.py`; each runs by `uv run pytest <file> -k <word>`.

| Test | Tier | Identifiers | Oracle and tolerance | `-k` |
|---|---|---|---|---|
| 1 `test_fr39_every_case_leaf_has_one_owner` | 1 | FR-39 | Every row names a schema path; every path's owner is one of four; `owner_of` is physics for `electrolyte.concentration_M`, `numerics.elements.u`, `numerics.stabilisation`, `numerics.wall_distance.max_distance_nm`, continuum for `numerics.mesh.wall_for_concentration_M`, study for `numerics.continuation`, `numerics.linear.solver` | `one_owner` |
| 2 `test_fr39_a_study_resolves_to_its_case_written_inline`; `…_reuses_every_stage_its_twin_built` | 1 | FR-39, VER-62 | Quick-start and 2WCD split in three: `==` the inline case, one `CaseArtefact` hash, no overrides; every stage to `mesh` cached, hashes equal | `inline or twin` |
| 3 `test_fr39_a_study_keeps_only_the_keys_no_model_owns` | 1 | FR-39 | Study keys `schema`, `name`, `models`, `outputs`, `numerics` with `continuation` alone; physics holds `electrolyte`, `boundary_conditions`, `physics`, `numerics.stabilisation` | `keeps_only` |
| 4 `test_fr39_a_model_exposes_its_kinds_list_unless_its_file_replaces_it` | 1 | FR-39 | Quick-start split: physics exposes `concentration` (molar, default 0.1) and `bias` (volt, 0.05); continuum `size_scale` (dimensionless, 1.0, low 0.0). With `exposes: [{name: salt, path: electrolyte.concentration_M, range: [0.05, 3.0]}]`, physics exposes `salt` alone with that range, and the `CaseArtefact` hash is unchanged | `exposes` |
| 5 `test_fr39_a_continuum_models_wall_follows_the_physics_salt_unless_pinned` | 1 | FR-39, VER-53 | Item 4's details. The continuum model at `wall_h_nm: auto`, swept over `models.physics` at 0.1 and 0.5 M: `forecast(...).builds["mesh"] == 1`; at 3 and 5 M: 2; with `wall_for_concentration_M: 3.0`, at 3 and 5 M: 1 | `wall_follows` |
| 6 `…_model_swap_…`, `…_run_records_its_model_files_and_overrides`, `…_sweep_over_models_resolves_each_member` | 1 | FR-39, FR-25 | As today, with the bias in `physics.yaml` and the axis `models.physics`; `files["models.physics"]["sha256"]` is the file's hash | `swap or records or sweep_over` |
| 7 `test_fr32_a_case_imported_into_a_project_keys_as_it_did`; `…_imports_them_and_a_second_import_reuses_them`; `test_fr34_the_changed_list_…` | 1 | FR-32, FR-34 | `items("physics")` holds the import; keys equal through `charge` and `mesh`; a second import reuses every file the split wrote, the quick-start's continuum and physics models; `problems() == ()`; the changed list as item 1's tests say | `fr32 or fr34` |
| 8 `test_fr39_a_study_rebuilds_only_what_its_override_moves` | 2 | FR-39, VER-26 | As today, the bias in the physics model; the sweep over `models.physics` reuses region to solve | `rebuilds` |
| 9 The VER-62 walks; `test_case_leaves.py`, `test_gui_screens.py`, `test_layering.py` | 1, 2 | VER-62, VER-71, VER-78, VER-61 | Unmoved at 10⁻⁸, no re-pin; the provenance set holds `models.physics`; the refused state lists a `continuum/` problem; no new edge | `gate.sh run` |

### Out of scope

- The Physics suite, its *Exposed values* tool and the suite id `physics`: WP5.18 and WP5.15.
- The Study suite's list of exposed values, and the Sweep tool's use of a range: WP5.19.
- A concentration range drawn from the electrolyte file's validity: WP5.18, when the suite shows it.
- Migrating model files written before this package: none (D5).

### Open questions

None.

# Code review 054: WP5.16, the Molecular suite

2026-11-12 · PR #183, branch `ccr-9b77d38b-j3hc4f`, head `08436b9` on base `73482d5` · scope: the PR's 75 files.
The code and tests were read in full with each touched function: `structure/cavity.py`, `structure/stage.py`
(`align`, `_gates`), `structure/read.py:select`, `structure/axis.py`, `structure/orient.py` (`orient_pore`,
`_channel_line`, `prepared_pore`), `structure/protonated.py`, `io/resolved.py`, `io/case.py`, `io/models.py`
(`read_model_file`, `_variant_of`, `_merge`), `pipeline/case.py:_resolve_structure`, `pipeline/run.py`
(`input_files`, `keyed_walk`), `api/project.py` (`kept_artefacts`, `_built_stages`, `build_case`, `set_value`,
`set_exposed`, `save_variant`, `_checked_write`, `changes`, `_copy_model`, `reset`, `problems`), `charge/edits.py`,
`density/radii.py`, `density/stage.py`, `cli/building.py`, `cli/running.py`, `gui/solver.py`, and every changed
module of `gui/web/` with its assets (`molecular.py`, `molview.py`, `tools.py`, `pages.py`, `frame.py`,
`screens.py`, `link.py`, `settings.py`, `server.py`, `bridge.js`). Every caller of a changed or removed name was
read (`resolve_protonated_radii`, `radius_scales`, `measure_axis`, `frame_rotation`, `read_model_file`,
`map_png`, `parse_chains`). The dev scripts `.claude/scripts/gui/{render_shell.py,shoot.cjs}`, §5.2's NOTE on
stage 1, IF-02's NOTE on `prepare` and the knowledge concept 04/15 were read against the code · level: xhigh, with
`--fix` · status: completed.

Static review (`/np-ship`, `/code-review xhigh --fix`). No gate, benchmark, sweep or nightly walk ran; `/np-ship`
gates the fixes. Ruff, ruff format and mypy ran clean on the fixed tree. These tests ran on the fixed tree and
pass: `tests/tier1/test_project.py`, `test_models.py`, `test_nan_gates.py`, `test_structure_axis.py`,
`test_cli.py`, `test_structure_stage.py`, `test_protonation.py`, `test_density.py` and `test_gui_settings.py`.
`test_gui_screens.py` (headless Chromium) did not run in the review; the gate runs it.

Probed:

- `read_model_file` on a linked variant naming itself, and on two naming each other, raised `RecursionError`.
  After the fix each is a `CaseValidationError` naming the variant.
- With one molecular model file holding a YAML syntax error, `Project.store_usage()` raised `yaml.ParserError`;
  `problems()` listed the file. After the fix `store_usage()` returns and the model adds nothing to the kept set.
- On a model from `new_model`, `set_value(..., "structure.source.path", ...)` is refused with
  "structure.symmetry: Field required", and `set_value(..., "structure.symmetry.point_group", "C7")` with
  "structure.source: Field required". Not fixed (finding 5).

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | High | `io/models.py:read_model_file`; `api/project.py:_built_stages`; `gui/web/molecular.py` | `read_model_file` let `yaml.YAMLError` through, and neither `_REFUSED` catches it. One molecular model file with a YAML syntax error therefore makes `kept_artefacts`, and so `store_usage` and `clean_store`, raise (probed); the settings page calls `store_usage` on every view. `MolecularModel.case()` and `problem()` raise on it too. A linked variant whose parent is malformed makes `problems()` raise, where before the PR a model read only its own file, which `_problems_of` had already parsed | Fixed: the reader refuses a YAML error as a `CaseValidationError` naming the file; the header checks move to `_model_mapping` to keep the reader within the complexity limit |
| 2 | High | `io/models.py:read_model_file` (the parent's read) | The parent of a linked variant is read before it is checked. A variant naming itself, or two naming each other, recurse until `RecursionError` (probed), which no caller catches: `problems()`, a study's read, `kept_artefacts` and every tool page raise | Fixed: the parent is read as a parent, and a parent that is itself a variant is refused before its own parent is read, with the existing message |
| 3 | Medium | `gui/web/tools.py:edit_section` | The Charge edit residue list takes its names from `molview.residues`, which reads the protonation table once the model is protonated, and the table names a residue by its state: HSD, HSE, HSP, ASPP, GLUP, LSN. *Add edit* then writes `{residue: HSD 25}`, which the build refuses ("the residue on chain 'A' is HIS, not HSD"), and `ASPP 21`, which the schema's three-letter pattern refuses at once. Histidines and every titrated acid or base could not be edited on a built model | Fixed: the list names each residue by `parent_residue` |
| 4 | Medium | `gui/web/molview.py:annotation` (`changed`) | The same cause: an edit names its parent, the table its state, so *Changed residues* left an edited histidine or protonated acid uncoloured | Fixed: the match uses `parent_residue` |
| 5 | Medium | `api/project.py:set_value`; `gui/web/tools.py:set_source` | A molecular model without a `structure:` block can never gain one. Each value is checked as a whole case, and `structure.source.path` needs `structure.symmetry` while `structure.symmetry.point_group` needs `structure.source` (probed). A model from `new_model`, or one holding neither block, dead-ends: Prepare's *Open structure…* shows the refusal at the field and the point group's field is disabled | Not fixed: the way out is a decision (several values set at once, or a point group the first structure takes); put to `/np-ship` |
| 6 | Medium | `gui/web/molecular.py:MolecularModel.poll` | `poll` drained the child's events and then asked whether it ran. A child that posts `Finished` and exits between the two is taken for one that stopped without a word: the build is recorded as refused, "the build stopped before it finished", its last event is never read, and the refusal is listed among the frame's problems | Fixed: whether the child has ended is read before the drain; a child that ended by then has flushed its queue |
| 7 | Medium | `structure/cavity.py:refit` | A centre whose carried tetrahedra are all flat is skipped. With fewer than two centres left, `fit_line` of one point returns the SVD's first row, `[1, 0, 0]`, and stage 1 records a drift of 90° for the frame; with none it raises a `LinAlgError`. Flat tetrahedra are what an exactly symmetric structure gives (the `_voids` comment) | Fixed: `refit` refuses with a `SymmetryGateError` naming how many centres could be carried, rather than recording an angle to an arbitrary line |
| 8 | Medium | `structure/cavity.py:_voids` | `Delaunay` raises `QhullError` (a `RuntimeError`) on atoms that span no volume. `orient_pore`'s fallback catches only `SymmetryGateError` and the CLI only `ValueError`, so `nanopnp prepare` on such a selection fails with a Qhull error instead of a refusal, as stage 1 does | Fixed: `_voids` refuses it as the channel gate's `SymmetryGateError` |
| 9 | Low | `gui/web/assets/bridge.js:nano.scene` | The scene's `fetch` sat outside the `try`. A request that fails (the server stopping, a dropped connection) rejects past it, so `reveal()` never runs, `screenReady` stays `0`, and the Python side's `run_javascript` times out after 60 s | Fixed: the fetch is inside the `try` |
| 10 | Low | `api/project.py:set_exposed` | A linked variant with no `exposes:` of its own reads its parent's list (`read_model_file`). `set_exposed` on it started from `EXPOSED[kind]` instead, so exposing one value silently dropped every other entry the parent exposes | Fixed: such a variant starts from its parent's list |
| 11 | Low | `gui/web/tools.py:readout` | A stage-1 artefact stored before this PR has no `axis.method`; §5.2's NOTE reads its absence as a permutation's. Prepare showed "Axis found by ?" for it | Fixed: the default is `permutation` |
| 12 | Low | `gui/web/tools.py:_unapplied_keys` | The pick key used the summary's chain as written, where every other key goes through `_chain_id` (one character, a blank one "A"). A segment-named chain gave `PROA:25`, which `nano.show` never finds | Fixed: `_chain_id` |
| 13 | Low | `gui/web/tools.py:add_edit` | A charge change was `int(float(value))`: 1.5 e became 1 and −0.7 e became 0, silently | Fixed: a value that is not whole is refused with a notice |
| 14 | Low | `cli/building.py` `--axis` | argparse reads `--axis -1,0,0` as an option, so an axis whose first component is negative fails with "expected one argument" | Fixed in the help: it names `--axis=-X,Y,Z` |
| 15 | Low | `api/project.py:_copy_model` | Only a linked variant carries its parent on import. A full copy keeps `variant_of.model` naming a file of the source project, which in the destination is missing or another model, and `changes()` then compares the copy with that model | Not fixed: whether an imported copy keeps, drops or carries its parent is a decision; put to `/np-ship` |
| 16 | Low | `structure/stage.py:_gates` | Under the channel the header's `gates` holds `straightness` with a `limit_nm`, though it is a warning and not a gate (AO4). Prepare's readout shows it as "Gate, straightness: … of … allowed", which reads as a breach on a build that passed | Not fixed: the header's shape is §5.2's; put to `/np-ship` |
| 17 | Cleanup (efficiency) | `gui/web/molecular.py:MolecularModel.artefacts` | Each call resolves the model and keys the walk, which hashes the structure and trajectory files (`file_hash` reads every byte). A tool's `refresh` calls it through `states`, `readout`, `charged` and `warnings`, once a second while a build runs, on the event loop; `Project._built_stages` already holds such identities by a stamp | Not fixed: a cache needs the store's state in its key; put to `/np-ship` |
| 18 | Cleanup (efficiency) | `gui/web/pages.py:molecular_scene` | One scene request writes the first frame's PDB text to stamp the address, builds the whole annotation to test it for emptiness, and reads the table or ensemble again in `frame_count` and `_extent_a`: about five keyed walks and `.npz` reads, before the browser fetches the structure and the annotation, which repeat them | Not fixed, with finding 17 |
| 19 | Cleanup (reuse) | `gui/web/molview.py:_pdb` | A copy of `link._pdb`'s line format | Fixed: `link._pdb_text` writes both |
| 20 | Cleanup (reuse) | `gui/web/tools.py:card` | `next(t for t in SUITES[0].tools if path in t.fields)` re-implements `screens.tool_for` | Fixed: `tool_for` |
| 21 | Cleanup (reuse) | `api/project.py:_holder` | A copy of `io/models._holder`, beside `_put`, which the module already imports from there | Fixed: imported |
| 22 | Cleanup | `pipeline/case.py:_resolve_structure` | `if groups is not None and chains is not None` tested one condition twice, and a sorted set was built only for its length | Fixed |
| 23 | Cleanup | `api/project.py:_REFUSED` | It listed `CaseValidationError` and `FileNotFoundError` beside `ValueError` and `OSError`, which hold them | Fixed |
| 24 | Cleanup | `io/resolved.py:ResolvedStructure.groups` | Set by `_resolve_structure` and read nowhere; `select` parses the chains string again | Not fixed: the plan names the field (items 1 and 2) |
| 25 | Altitude | `gui/web/molecular.py:refused_path`, `_GATE_PATHS` | A refusal finds its field by a regular expression and a keyword table: any message holding "channel" goes to `structure.symmetry.axis`. The root fix is a gate error that carries its case path | Not fixed: it spans every stage's errors |
| 26 | Conventions | `structure/cavity.py` (module docstring) | It cites "(FR-02)". `.claude/rules/python.md`: "Requirement identifiers live in the names of in-scope tests and commit messages, not in prose" | Fixed |
| 27 | Conventions | `gui/web/tools.py:write` | A comment cites "(WB-12)", against the same rule | Fixed |
| 28 | Low | `docs/plans/index.md` | The PR changed the WP5.16 plan's and the Phase 5 plan's status lines but did not run `index_records.py`; the index still quoted WP5.16 as "planned, not started" | Fixed: the indexes are regenerated, `docs/code_reviews/index.md` with this report |

Not findings:

- `tools.py:save_prepared`'s `if written is None: return` looked dead, since `prepared_pore` returns a path. NiceGUI's
  `run.io_bound` returns None when the app is stopping, so it stays.
- `_section_centres` cannot reach `found[last]` empty: the seed's `pick` meets the enclosed candidate the seed
  search found first, and a later plane joins only with a non-empty tie.
- `prepared_pore` stages the record as `.<stem>.<pid>.partial.prepare.json`, the name `orient_pore` writes beside
  `out`, so the pair is renamed whole.
- In `_resolve_structure` the comprehension variables named `group` do not leak, so the error messages' `{group}`
  is still the point group.
- `resolve_protonated_radii` now applies the radius edits, and its only caller in `src/`, the density stage, no
  longer does, so no radius is scaled twice. The tests that compare it with the table's radii hold no radius edit,
  so the scales they meet are 1.

## At `/np-ship`

Each applied fix was read as a diff against §5.2's NOTE on stage 1, §5.3.1 and the plan, and all 21 were kept;
finding 7's refusal fires only where a frame's line is undefined. Finding 16 is fixed in the workbench: Prepare
reads the straightness as "…, warned above 0.03 nm" and no longer as a gate, and the header keeps its shape. Findings
5, 15, 17, 18 and 25 are REV-242; finding 24 stays, as the plan names the field.

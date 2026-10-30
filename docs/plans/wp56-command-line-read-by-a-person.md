# WP56 — The command line read by a person

**Status: planned, not started.** Written 29 October 2026, grounded in the code at `597818c` (§8.2.15
Q1). Inherits §8.2.21 W1 to W8, the test scope (§8.2.13 N1 to N6) and FR-30's figures (§8.2.14, §8.2.20).

The [Phase 4 plan](phase-4-polish-and-user-testing.md) owns the phase. `SPECIFICATION.md` governs;
where this plan and it disagree, this plan is wrong. Identifiers are pointers, never restatements.

## In brief

The author's testing sessions found the command line hard to read: a run shown as its whole record, a
sweep as raw data, nothing drawn, a long solve silent, and two messages naming a setting the user cannot
change. This package fixes each at its cause.

**What changes.** Reading a run gives a short account: the model, each solver step with its time, the
results and every departure from the validated model; the full record stays one flag away. Two runs
can be compared side by side. A sweep reads as a table, each rectification ratio beside its salt. A
new command draws any step's picture to a file. A long solve prints a line per step. A refused mesh
names the tool that made it; a charge stated twice with opposite signs is refused by name. The help
says which flags shape the pore, when a run does not reproduce, and how workers share the processor.
The slow solve on a fine mesh is measured.

**Cost.** Two to three days of work. The checks before each push grow by under a minute.

**What could go wrong.** The short account could omit something a user needs; a test reads every
departure back, and the full record is unchanged. The picture command needs the plotting extra; without
it, it says so. The measurement could show a fault, not a cost; it is then reported to you.

**Your call.** None open: the four decisions were ruled when this was planned.

## Execution brief

Scope: the Phase 4 plan's WP56 entry; §8.2.21 W2 to W6 and W8; UT-01 to UT-09, UT-11, UT-12; REV-154.
Depends on WP55, delivered. Claims FR-44 and the NOTEs on IF-02 (reading) and QR-12 (the remedy),
written in this plan's commit. Tag `v0.5.0-alpha.22`. Implementing session: Sonnet, high effort. No
case schema, `PUBLIC` name or `--json` payload changes.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| D1 One reader of a run directory | `pipeline/run.py` gains `read_run(directory) -> RecordedRun` (the case document, the `Manifest` and the run record, no store) and `open_run(directory, *, store=None) -> RunResult` (adds the artefacts from the store the record names, and the resolved case). `Manifest.from_document` rebuilds a manifest and refuses one whose recomputed hash differs from its `hash`. `sweep/collect.py:read_dataset(directory) -> SweepArtefact` reads `dataset.json` with `plan.json` beside it. A missing file raises `FileNotFoundError`; a hash that disagrees, a new `io/manifest.py:ManifestHashError`, classified at 3 in `core/errors.py:EXIT_CODES` | Four ad hoc readers exist; `inspect`, the comparison and `plot` need one; the hash check keeps a hand-edited record from reading as the run |
| D2 `inspect` reads by schema | `cli/reading.py` renders: a run directory or `manifest.json` as its summary; `dataset.json` as two tables; a stored artefact's `meta.json` as schema, key, parameters and summary; any other JSON key by key, as today. `--section GROUP` prints one manifest group. `--json` prints what it prints today. The first line is still the path read | W2; IF-02's NOTE on reading |
| D3 Two runs compared | `inspect A B`, both run directories: the case leaves that differ, the deviations of each, each quantity side by side with `(B − A)/|A|`. Anything else as B is a usage error (exit 2). Exit 0 | W2; UT-03's fourth point |
| D4 `nanopnp plot` | `nanopnp plot TARGET [STAGE] --out PATH [--store DIR]`. TARGET is a case file (walked to STAGE through the store, `write=False`), a run directory (`open_run`, STAGE default `solve`) or a sweep directory or its `dataset.json` (`read_dataset`, no STAGE). The suffix (`.png`, `.svg`, `.pdf`), a STAGE that is unknown or on `FIGURE_FREE`, and a missing STAGE for a case file are refused by `parser.error` before any walk. Drawn by `RunResult.figure` or `core.stages.draw`, saved to a temporary file beside PATH, then renamed | W3; FR-44. No `cli → plot` import: VER-61's rows do not move |
| D5 Progress on standard error | `run` and `stage` take `--progress/--no-progress`, default `sys.stderr.isatty()`. One object is passed as `on_stage` and `on_solve`; it prints `stage <n> <name>` when a stage starts and `  rung <i>/<total> <name>` when a rung starts, with the previous rung's accepted steps and seconds | W4. The hooks are not inputs (VER-44): no key moves |
| D6 A remedy names what the run reads | `WallDistanceGate` takes `remedy: str`; `solve/state.py:wall_distance_remedy(resolved)` gives `numerics.mesh.wall_h_nm` when `resolved.generates_mesh`, else the supplied file and `nanopnp mesh cylinder --wall-h-nm`, and `check_wall_distance` passes it. `register_form` takes `charge_parameter=`; `gaussian_ring` names `charge_e`. `FieldDocument._check` refuses a `q_net_e` whose sign differs from that parameter's (zero counts as a sign); the producer leg's refusal names both keys for a form | W5; QR-12's NOTE on the remedy; REV-154. Sign only: a ring on the axis integrates to half its charge (`test_ver29_the_axis_guard_deficit_is_reported_rather_than_assumed`) |

### Grounding

**D1**
- Run directories are read by hand in `gui/run_model.py:run_outcome`, `gui/render.py:_state_path` and
  `_recorded_artefact`, `validation/runs.py:reopen` and `pipeline/reproduce.py`. None returns a
  `RunResult`. They stay; the Qt shell leaves in Phase 5.
- `pipeline/run.py:RunResult.record` writes `run.json`: `schema`, `case`, `manifest`, `directory`,
  `store` (absolute: `io/store.py:Store.__init__` resolves the root), `stages` (each
  `StageRecord.summary`), `artefacts` (`{name: {schema, hash}}`), `quantities`, `files`.
- `io/manifest.py:Manifest.document` writes `schema`, `created_at`, `hash`, `case: {hash, text}` and the
  eight groups of `GROUPS`; `deviations` is `{count, switches: [Deviation.summary], contributed:
  [ContributedDeviation.summary]}`. `Deviation(path, validated, value)` writes
  `{path, value, validated_default}` (`io/defaults.py`). `io/manifest.py:read` returns the parsed JSON;
  floats are `{"__f__": hex}` until `core/hashing.py:decode_floats`.
- `RunResult(directory, manifest, artefacts, stages, store, resolved)`; `StageRecord(name, number,
  schema, hash, cached, seconds)`. `open_run` builds `resolved` as `validation/runs.py:reopen` does:
  `load_case(directory / CASE_FILENAME)`, then `pipeline/case.py:resolve`. An artefact absent from the
  store is left out of `artefacts`, not refused; `plot` refuses it by name.
- `sweep/plan.py:PLAN_FILENAME` is `plan.json`, `read_plan(path)`; `SweepArtefact(plan_hash,
  base_hash, name, points, payload, summary)` (`io/artefact.py`); `collect` writes `dataset.json` as
  `{"schema": SWEEP_SCHEMA, **summary}`. `read_dataset` refuses a dataset whose `plan` is not the
  plan's hash.

**D2, D3**
- `cli/__init__.py:_inspect` picks `manifest.json`, `meta.json` or `run.json` in a directory and prints
  `f"{key:<20} {json.dumps(value)}"` per key; `_emit(payload, lines, as_json=)` prints `payload` as
  sorted JSON under `--json`. `tests/tier2/test_examples_06_pdb_to_mesh.py` asserts `run-profile` in
  `inspect`'s stdout: the path line stays.
- The ladder is `manifest["solver"]["run"]["rungs"]`, each `RungResult.summary`: `rung`, `stage`,
  `model`, `seconds`, `newton` (`None` for a linear rung, else `iterations`, `minimum_damping_used`).
  A run stopped before stage 10 records `not_run(...)` there (example 06's `run-profile`).
- A dataset row has `id`, `status`, `assignments` (dotted paths), `quantities`; a rectification entry
  has `forward_id`, `reverse_id`, `bias_V`, `rectification` (`sweep/collect.py:_rectification`).
- Case leaves are compared on `CaseDocument.model_dump(mode="json")` flattened to dotted paths, lists
  by index: `case_fields()` lists paths with a sequence wildcard, which `value_at` does not take.

**D4**
- `core/stages.py:FIGURE_FREE` is `{"case", "report"}`; `figure_target(schema)`; `draw(artefact,
  inputs, *, scale)` raises `MissingExtraError` (exit 3, `core/errors.py:EXIT_CODES`) without
  matplotlib; `RunResult.figure(stage)` builds its `StageInputs` from `offered`. The sweep figure is
  registered for `nanopnp/sweep/v0.5` and reads `summary["rows"]` (`plot/data.py:sweep_rows`).
- `describe(name)` raises for an unknown stage; `describe(name).artefact_schema` gives the schema to
  test against `figure_target` before the walk.
- The returned `matplotlib.figure.Figure` has `savefig`; the CLI imports no Matplotlib.
- `test_ver32_no_flag_changes_what_is_solved` lists every option of every subparser except `mesh`'s:
  `--out`, `--store`, `--progress` pass it.

**D5**
- `core/stages.py:StageHook.__call__(name, index, total)`; `SolveHook.rung(name, stage, index, total,
  reporting, tolerance)` and `.step(iteration, residual, update, damping, trials, forced)`.
  `cli/__init__.py:_run` and `_stage` call `run_case(..., write=False)`, which forwards `on_stage` and
  `on_solve` to `run_document`.

**D6**
- `numerics/gates.py:WallDistanceGate.checked` ends its detail with "refine the mesh at the wall
  (numerics.mesh.wall_h_nm), do not widen this gate". Its callers: `solve/state.py:check_wall_distance`
  (from `solve/stage.py`) and `sweep/plan.py`; both hold `resolved`. `io/resolved.py:generates_mesh` is
  `self.mesh is None`. The supplied path is `resolved.document.inputs.mesh.path`.
- `charge/fields.py:register_form(name, builder)`, `_FORMS`; the forms `uniform`, `gaussian_ring`
  (`charge_e`), `slab`. `FieldDocument._check` collects `problems` into one `ValueError`, which
  `load_document` turns into `FieldDocumentError` (exit 4). `check_conservation` raises the producer
  leg's `ChargeFieldError` from a `ConservationReport`, built by `conservation(field, ...)`, which holds
  the field and so its document's form; the new text field is not in `ConservationReport.summary`, so
  no charge artefact key moves.
- Every shipped field document with a form states `charge_e` and `q_net_e` equal (`examples/02`, `03`,
  sessions 02, 04, 05).

**W6, W8 (items 8 and 9)**
- `cli/__init__.py:build_parser`: `cylinder` adds `--pore-radius-nm`, `--membrane-thickness-nm`,
  `--reservoir-radius-nm`, `--maxh-nm`, `--wall-h-nm` and `--out` to one group; `reproduce` and
  `sweep run` have no `description`. `sweep/run.py:pin_threads` sets `THREAD_VARIABLES` to `1` in
  each worker.
- `cli/reference.py:render_case_reference` and `docs/scripts/generate.py:main` (its `pages` dict)
  generate the case-file reference; `FieldDocument`, `FormSpec`, `GridSpec`, `DataSpec` and
  `FieldProvenance` carry no `description`. `FormSpec.shape` is `(n_r, n_z)` (`create_form`).
- Session 03 writes `wall-100.msh` and runs `coarse.case.yaml`, in a `refused` block that VER-69 runs.
- The solve's rungs record `seconds`; the linear solve is `numerics/linear.py:UmfpackSolver.solve`.

### Implementation details

**Item 2, the run summary** (one line each, label padded to 10):
`run`, the path; `case`, name and `case.hash[:12]`; `model`, `solver.model`, then
`stabilisation.mode`; one `stage` line per `run.json` stage as `_run` prints them; one `rung` line
per ladder rung: name, model, iterations or `linear`, minimum damping, seconds; the quantities as
`_run` prints them; one `deviation` line per switch, `path: value (validated default)`, and per
contributed entry, `source: description`, or `deviations none`. A group that is `not_run` prints its
reason. `--section` takes a name of `GROUPS` or `case`, and prints that group as indented YAML-like
`key: value` lines; another name is a usage error naming them.

**Item 2, the dataset**: `dataset   <path>   <points> points: <counts>`; a table with columns `id`,
`status`, each assignment by its last component (the full path where two share one), then each scalar
quantity present among `current_A`, `conductance_S`, `transport_number`, `eof_m3_s`, values `.4g`;
then `rectification`, one row per entry: the forward row's assignments other than
`boundary_conditions.bias_V` (the sweep axis's path; corrected from `operating_conditions`), `bias_V`, the ratio; then each note as `note  <text>`.

**Item 3, `--json`**: `{"left": A, "right": B, "case": [{"path", "left", "right"}], "deviations":
{"left": [...], "right": [...]}, "quantities": [{"name", "left", "right", "relative_difference"}]}`;
a mapping quantity is flattened (`currents_A.Na+`); the difference is `null` where A is zero, absent
or not a number.

**Item 9, the measurement**, in the background:
`nanopnp mesh cylinder --maxh-nm 0.175 --out fine.msh`; session 03's `wall-0175.case.yaml` with
`inputs.mesh.path: fine.msh`; run it under `cProfile` through `nanopnp.cli.main([...])` from a scratch
script with `uv run`; record total seconds, each rung's seconds from `inspect --section solver`, the
Newton steps, and the cumulative share of `UmfpackSolver.solve`. Write the numbers into the Outcome and
REV-156. A share below 50 %, or a rung far above its neighbours, is put to the author before the PR.

### Work items

- [x] 1. 61e63b3 `io/manifest.py`, `pipeline/run.py`, `sweep/collect.py`: `Manifest.from_document`,
  `RecordedRun`, `read_run`, `open_run`, `read_dataset` (D1); done when
  `test_qr08_a_manifest_read_back_keeps_its_hash` passes. **Executor:** main
- [x] 2. f6d3a8c `cli/reading.py`, `cli/__init__.py:_inspect`: the summary, the tables, `--section` (D2); done
  when `test_fr25_inspect_reads_back_every_deviation_and_compares_the_runs`' reading half passes.
  **Executor:** main
- [ ] 3. `cli/reading.py`, `cli/__init__.py`: `inspect A B` (D3); `examples/02-charged-pore/README.md`
  names the command in prose (a tagged one would match `only=("run-epnpns",)` per push); done when the
  same test passes. **Executor:** main
- [ ] 4. `cli/__init__.py:_plot` and its parser (D4); session 01's README gains `$ nanopnp plot
  run-pore solve --out fields.png` in its `run` block; done when both FR-44 tests pass.
  **Executor:** main
- [ ] 5. Compaction checkpoint. **Executor:** main
- [ ] 6. `cli/__init__.py`: the progress object, `--progress` on `run` and `stage` (D5); done when the
  code and review say so. **Executor:** main
- [ ] 7. `numerics/gates.py`, `solve/state.py`, `sweep/plan.py`, `charge/fields.py` (D6); done when the
  NUM-34 and QR-03 tests pass. **Executor:** main
- [ ] 8. Help and reference (W6): `mesh cylinder`'s flags in a `geometry` and a `mesh` group;
  `description=` for `reproduce` (a run fails to reproduce when an input file changed, the libraries or
  platform moved the numbers past the tolerance, or the store served a stale artefact; it solves in a
  fresh store) and for `sweep run` (each worker is pinned to one thread; `--workers` sets the cores);
  `description=` on every field of the five field-document models; `cli/reference.py:
  render_field_reference` beside `render_case_reference`, written by `generate.py` to
  `reference/field-document.md`; session 03's `coarse.case.yaml` renamed `wall-100.case.yaml`, with
  every reference; done when the code and review say so and the strict documentation build passes.
  **Executor:** `general-purpose` on Sonnet
- [ ] 9. The UT-09 measurement (W8; *Implementation details*); done when the Outcome and REV-156 hold the
  numbers. **Executor:** main
- [ ] 10. Compaction checkpoint. **Executor:** main
- [ ] 11. `CHANGELOG.md` (`plot`, `inspect`'s reading and comparison, `--progress`, the field-document
  refusal), Appendix A's FR-44 row to the test names, REV-154 `fixed`, the WP56 UT rows `fixed`; gate
  and push. **Executor:** main

### Verification

| Test | Tier | Identifiers | Oracle | Tolerance source | Command |
|---|---|---|---|---|---|
| `tests/tier1/test_manifest.py::test_qr08_a_manifest_read_back_keeps_its_hash` | 1 | QR-08, FR-25 | `from_document(m.document()).hash == m.hash`, deviations equal; one edited group is refused | exact | `uv run pytest tests/tier1/test_manifest.py` |
| `tests/tier2/test_examples_01_quickstart.py::test_fr44_plot_draws_each_figure_of_the_run_from_its_directory` | 2 | FR-44 | `open_run` gives `run.json`'s stage hashes and quantities; `plot run <stage>` exits 0 and writes a PNG for each stage with a figure | exact | `uv run pytest tests/tier2/test_examples_01_quickstart.py` |
| `tests/tier1/test_cli.py::test_fr44_plot_refuses_a_suffix_or_a_figureless_stage_before_any_stage_runs` | 1 | FR-44 | `.txt`, `report` and a case without STAGE each exit 2, the store directory empty | exact | `uv run pytest tests/tier1/test_cli.py` |
| `tests/tier2/test_examples_02_classical.py::test_fr25_inspect_reads_back_every_deviation_and_compares_the_runs` | 2, nightly | FR-25 | `inspect run-classical` has one `deviation` line per switch path of the manifest; `--json` equals the decoded manifest; `inspect run-epnpns run-classical --json` lists the six correction paths under `case` and six deviations right, none left | exact | `uv run pytest tests/tier2/test_examples_02_classical.py` |
| `tests/tier1/test_gates.py::test_num34_refusal_names_a_setting_the_run_reads` | 1 | NUM-34, QR-12 | generated: the remedy names `numerics.mesh.wall_h_nm`; supplied: names the file and `--wall-h-nm`, not `numerics.mesh`; the raised gate's message carries it | exact | `uv run pytest tests/tier1/test_gates.py` |
| `tests/tier1/test_charge_fields.py::test_qr03_a_charge_stated_twice_with_opposite_signs_is_refused_when_read` | 1 | QR-03, PHY-19 | `charge_e=6, q_net_e=-6` and `charge_e=0, q_net_e=-6` raise naming both keys; equal signs, and `q_net_e` absent, load; a producer-leg failure on a form names `charge_e` | exact | `uv run pytest tests/tier1/test_charge_fields.py` |

The gate: `.claude/hooks/gate.sh run`, and the documentation build of `CLAUDE.md`'s *Commands*.

### Out of scope

- The guide's prose for UT-02, UT-05, UT-06 and UT-09: documentation increment 4 (W1).
- UT-10, `MOD-11`, `Case.run`'s controls, a public `open_run`: WP57 (W7).
- The cost fix of UT-09, REV-60's symbolic reuse: Phase 6 (W8, REV-156).
- Field and case export: FR-28, v0.7 (W3). The workbench comparison: FR-34, v0.6.

### Open questions

None blocking: the four were ruled when this was planned (§8.2.21).

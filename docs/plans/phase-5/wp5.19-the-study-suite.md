# WP5.19 — The Study suite

**Status: planned, not started.** Planned 16 November 2026 on `main` (`51059ff`). It inherits AG5, AG7, AJ5, AJ8, AN1,
AN4, AP5, AQ1 and this plan's AR3 to AR5 (§8.2.31 to §8.2.42).

This plan belongs to [the Phase 5 plan](phase-5-workbench.md). `SPECIFICATION.md` governs; an identifier points to a
clause.

## In brief

**What changes.** The Study suite works: the three kinds of model are paired and run. Overview shows
the study as its run sees it. Study setup lists each model's main values first, then the rest, as a form or, as
you ruled, a clickable graph; *New study* pairs three models. Sweep varies a value, a variable or a
model, warning before one that rebuilds the mesh. Charge on the mesh shows the protein beside its charge map,
with axes and a colour bar; a residue picked on one side is found on the other. Runs starts a study, follows its
convergence in the queue and keeps its record. Two settings set how many runs go at once and the threads each uses;
the thread count is recorded, not used to tell results apart.

**Cost.** About six sessions, 9 to 14 agent hours and 14 of your touches, with the 2WCD round. The Physics
suite took 5.7 agent hours and 11 touches. No new library.

**What could go wrong.** Several solves at once could slow each other; the default stays one. The charge map could
disagree with the molecule; both come from one stored charge, and a test checks the map against the record. A
shifted outline may pass the charge check; its reach is measured and stated.

**Your call.** At the round: the charge screen, the graph and the fields' look. *Recommendation:* rule them on the
drawn screens. The 200 ms redraw needs your machine with a graphics card: one command in a local session.

## Execution brief

**Scope.** The phase entry's WP5.19 with AR4's *New study* and graph; REV-41's `upto`, REV-197, REV-205, REV-206,
REV-209, REV-215, REV-247, REV-251; REV-246 (AP5); the round's points of REV-240, REV-252, REV-254, REV-255 and REV-256.
**Depends on:** WP5.18 (merged). **Requirements:** FR-25, FR-27, FR-33, FR-35, FR-39; QR-08; VER-35, VER-36, VER-44,
VER-59, VER-60, VER-62, VER-78. **Constrained by:** AJ5, AJ8, AN1, AN6, AR3, QR-13, CON-09, ADR-004.
**Implementing session:** Opus, high; sub-agents Sonnet, high. Tag `v0.6.0-alpha.19`.

**Amended when it lands:** VER-78; FR-25 and §5.3.3 (AR3); §5.3.5's NOTE; AP5's two NOTEs; AP1's consequence and
VER-55's NOTE (AR5); §5.3.1's NOTE on `outputs:`; QR-08's NOTE; the design document's Study rows; FR-33's and FR-39's
matrix rows.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| D1 The suite | Tools `overview`, `setup`, `sweep`, `charge`, `runs` at `/study/<tool>`; `gui/web/study.py:StudyModel(BuiltModel)`, kind `study`, built to `charge`; panes in `study_tools.py`; the study picked per pane (`Shell.study`); `st-charge` and `link.py` retire | WB-05; decided by the plan |
| D2 A study's values | `Project.new_study`, `set_study_value` (own key, override or `models.<kind>`), `set_variable`, `study_values` (exposed values first); written when the file loads as a study, a resolve refusal shown at its field | FR-39 (a), AJ5, AG12; decided by the plan |
| D3 Study setup | The form, and the graph beside it (`ui.mermaid`), a node opening its section; *Run study* | AR4, ruled by the author, against the recommendation; WB-33 |
| D4 Sweep | `sweeps/<study>.sweep.yaml`, the existing document; axes over a value, a variable or a model; the forecast's warnings at each axis; members queued wave by wave; rectification paired by resolved bias | FR-39 (b), (f), AG5; REV-197; decided by the plan |
| D5 Charge on the mesh | Mol* and the canvas side by side: the lattice map with bar and axes, the worst planes, the deployed field under IF-07's name; residue and map linked through `plot/data.py:ResidueCharges`; the walk writes its run record | FR-33, VER-60, REV-205, REV-209, QR-13; decided by the plan |
| D6 Runs | *Run study* queues a walk into `runs/<study>/`; its entry unfolds to the convergence plot and rung table; Runs lists the records | VER-44, RE2; decided by the plan |
| D7 Compute | *Solves at once* and *Threads per solve*, user scope; builds, runs and members wait for a slot; the child sets the BLAS threads; the solve and run record state the count, no key moves | AN1, AN6; AR3, ruled by the author |
| D8 The opening walk | Boot walks the first study to `charge`, else `mesh` | REV-251; decided by the plan |
| D9 Library steps | `upto` on reproduce; REV-206's export limits; AP5's shell spacing; REV-247 measured, AP1's consequence narrowed to its reach | REV-41, REV-206, AP5; AR5, ruled by the author |
| D10 The round | The tools and graph on 2WCD, with REV-256's mockups; reviewed, published, collected with REV-240's, REV-252's and REV-255's points; finished | AJ8, REV-215, ruled by the author |
| D11 The 200 ms line | `.claude/scripts/gui/redraw.cjs`, run by the author with a GPU: median and p95 of 20 picks, front end and whole repaint; a miss profiled | AG7, ruled by the author |

### Grounding

**D1.**
- `gui/web/screens.py:SUITES` holds Study's Overview, Study setup, Sweep and Runs with empty ids and `Tool("charge")`;
  Study is not in `TOOL_SUITES`, so `/study` is `pages.suite_page`'s list, printing `State: <name>` (REV-205's F16).
- `SCREENS`' `st-charge` (`/study/charge`) is `pages.charge`, drawn from `Workbench.link`, a `gui/web/link.py:Link` that
  `states.boot_project` builds; `molview.py` takes `_chain_id` and `_pdb_text` from `link.py`, `plane.py` `png`.
- `builds.py:BuiltModel` keys `_MODELS` by `(root, kind, name)`; `refusals()` maps a kind by `io/project.py:ITEM_SUITES`,
  which holds `study`; `api/project.py:BUILD_UPTO` has `molecular` and `continuum` rows only.
- `BuiltModel.kind` is a `ModelKind`, which excludes `study`. `BuiltModel.build` calls `Project.build_case(kind, …)`,
  which reads a model file and merges `BUILD_LAYER` over it; `Project.kept_artefacts` keys each `BUILD_UPTO` kind
  through it.
- `pages.py:ROUTES` reads `VIEWS[suite.id]` for each of `TOOL_SUITES`; `frame.py:Route.view`, `VIEWS`, `tool_view`
  and `tool_controls` take `molecule` and `plane` only.
- `frame.py:_Frame.show_host(name)` shows one of `hosts` and hides the other; `Views` has `show_molecule` and
  `show_plane`.
- `tools.py:_Pane` is generic over `BuiltModel` and draws `Tool.fields`; `physics_tools.py:physics_page` is a page
  whose `view="page"` draws its own view, the route then hiding the frame's view region.

**D2.**
- `Project.set_value(kind: ModelKind, …)` refuses a path `owner_of` gives another kind; no method writes a study.
  `Project.reset("study", …)` deletes an override from the study file, else the value from its model's file;
  `Project.changes("study", n)` lists the overrides.
- Example 01 imported: the study holds `schema`, `name`, `models` (`../models/<kind>/<name>.yaml`),
  `numerics.continuation`, `outputs`.
- `io/models.py:exposed_values(kind, raw, source)` gives `ExposedValue(name, path, unit, low, high, default)`;
  `ModelRecord.overrides` maps a path to (model value, study value).
- `Project.new_model` writes `{schema, name, exposes}` through `_write_item`, then `write_project`.

**D3.**
- NiceGUI 3.18.0 ships `ui.mermaid(content, config, on_node_click=…)` (since 3.3.0), its library in
  `nicegui/elements/mermaid/dist`, served from the server's origin. Its `mermaid.js` binds a `click` listener to each
  `g.node` and emits that node's SVG id, which contains the flowchart's node id; `securityLevel` plays no part.

**D4.**
- `sweep/document.py:SweepDocument`: `schema` `nanopnp/sweep/v0.5`, `name`, `base` (against the file's folder), `axes`
  (`Axis`: `path` and `values`, or `assignments`; no range form), `workers`. `sweep/plan.py:_check_model_files` takes a
  `models.*` value as a file beside the base; `_check_variable_axes` takes `variables.<n>`.
- `sweep/plan.py:_pairs(points)` pairs by `boundary_conditions.bias_V` in the assignments, the other assignments equal,
  before the members resolve; `build_plan` raises `SweepPlanError` where `rectification` finds no pair. `_member`
  sets each member's `name` to `<base>-<point id>`; `_resolve_every_point` holds each member's `ResolvedCase`.
- A study's `models_record.base` is its own folder, so a `models.*` axis value reads `../models/<kind>/<name>.yaml`.
- `sweep/forecast.py:Forecast` holds `builds`, `reused`, `points`, `axes` (the stages each axis moves); `warnings()`.
- `Store.sweep_directory(name, digest)` is `<sweeps>/<name>-<short>`. `api/sweep.py:run_point(plan, index, *, session,
  directory)` writes `members/<index:06d>.json` and the member's run under `runs/<base name>-<point id>/`; it takes no
  cancel token or solve hook, which `Session._walk` takes. `run_plan`'s pool runs `sweep/run.py:pin_threads`, each
  variable at 1. `Project.kept_artefacts` reads `run.json` and `members/*.json` under `runs/` and `sweeps/`.
- `modularity-layering.yaml` has `gui -> api` and `plot -> charge`, and no `gui -> sweep`.

**D5.**
- `gui/charge.py:charge_image(lattice)` gives `ChargeMap` (an `ImageModel` in the model frame, `limit`, `quantity`,
  `units`); `ConservationView.from_record(summary)` the five legs and the worst planes; both Qt-free.
- `Link.residues_at` sums `charge/kernel.volume_density` per residue in the server; no test covers `Link`.
- `plane.py:_image` writes an `image` layer with its `bar`; `plane.js` draws the `model` frame's ticked axes.
- `gui/render.py:deployed_coefficient(run, quantity)` reads a run directory's case and recorded stage 6 and 7 in a
  spawned child (NGSolve); `post/export.py:FIXED_CHARGE_ATTRIBUTE` is `rho_fixed_C_m3`.

**D6.**
- `gui/run_model.py:RunModel.consume(events)` feeds `Rung` and `Iteration` to `gui/convergence.py:ConvergenceModel`,
  whose `Band.note()` names the silent rung and the rung converged on entry and `closed_on()` the test the numbers
  prove; nothing in `gui/web/` imports them. `test_gui_solver_process.py` builds one through `RunModel` and reads
  its outcome; no test reads its bands.
- `gui/solver.py:RunRequest` is `case, store, upto, write`; `_worker` runs `Session(Store(store))`, so a run lands
  in `<store>/runs/`; `Store(…, runs=)` gives `runs/<name>/<short>` and `upto-<stage>-<short>`.
- `frame.py:bottom_panel` draws `queue.Entry.line()` labels once; `queue_moved` refreshes the status line only.

**D7.**
- `settings.py:register(Setting(…))` adds to `SETTINGS`; `SECTIONS` has `appearance`, `keyboard`, `runs`, `numbers`;
  `tests/tier1/test_gui_settings.py:CHANGED` needs one value per setting.
- No thread setting exists in the solve path; nothing imports NumPy or NGSolve before `Session.run` in the child.
- `Artefact.hash` covers schema, parameters and inputs; the solve's summary is `LadderResult.summary()` and the manifest's
  `solver_group(...)["run"]`; `RunResult.record()` has no thread field.

**D8.**
- `states.boot_project` walks `upto="charge"` with `session.write = False`, so it leaves no run record; a study that
  deposits none raises `UnknownStageError` (REV-251).
  `nanopnp gui <project>` walks nothing.

**D9.**
- `api/reproduce.py:reproduce` refuses a record with no `quantities`; `check_mesh` compares the content hash; the run
  record holds each stage's key in `artefacts`.
- `Project._export_runs` copies each `files` entry to `results/<name>`; `_gathering` flattens a sub-folder input;
  `export` writes into the destination directly. `run.json`'s `files` are the store paths of the report artefact's
  payload (`RunResult.files`), not its keys; `artefacts.report` names that artefact.
- `io/resolved.py:contour_spacing_nm` is the density's grid (default 0.05 nm) for a supplied outline;
  `geometry/region.py:region_parameters` keys `h_c_nm` only with the shell on, so no VER-62 walk moves;
  `ProfileProvenance.min_vertex_spacing_nm` is checked against the vertices and is 0 for a repeated vertex;
  `geometry/region.py` divides by `h_c` in the shell's resampling; `pipeline/checks.py` bounds the offset by `2 h_c` on
  the document.
- 2WCD's `membrane.centre_z_nm` is 0, so its frames coincide.

**D10.**
- `render_shell.py` builds the cached 2WCD project (`cached_project`) and serves groups by `--project`.

### Implementation details

**Item 1.**
- `new_study(name, molecular, continuum, physics) -> Path`: `{schema: nanopnp/case/v0.6, name, models: {<kind>:
  ../models/<kind>/<n>.yaml}}`; refused for a taken name or a missing model.
- `set_study_value(name, path, value)`: `models.<kind>` takes a project model's name; any other path is put into the
  study's body; staged, read by `Case.load`, moved into place; None deletes.
- `set_variable(name, variable, *, value=None, expression=None, unit="dimensionless")`; None for both deletes.
- `StudyValue(kind, name, path, unit, low, high, model, study)`; `study_values(name)`: each model's `exposed_values`
  in model order, then each study-owned leaf set, then each override. *More values* adds an override of any path of
  `io/case_paths.py:case_fields()` that a model owns.
- Export: each result under `results/<its path relative to Store.location of the record's artefacts.report>`; the copy's `run.json` gets `directory`, `files` and
  `store` (None without `store=True`) of the copy; an input keeps its path under `inputs/`; an unnamed input whose name
  a linked one takes is refused, naming both; the copy is written into `<destination>.partial-<pid>` beside it and
  renamed, removed on failure.

**Item 2.**
- `_pairs(points, resolved)` after `_resolve_every_point`, before the mesh gate: key each point by `canonical` of
  `resolved[i].document` dumped without `name`, `boundary_conditions.bias_V` and `variables`; pair opposite resolved
  biases. The refusal follows it; its comment says why it now waits for the resolve.
- `run_point(..., cancel=None, on_solve=None)`, passed to `_walk`. `pin_threads(count: int = 1)`.
- `RunRequest` gains `runs: str | None`, `threads: int = 1`, `plan: str | None`, `index: int | None`. `_worker` calls
  `pin_threads(threads)` first, then `run_point` where `plan` is set, else `Session.run`.
- The solve stage's summary gains `threads`: the `OPENBLAS_NUM_THREADS` it ran with as an int, None where unset,
  which FR-25's text says is the libraries' own default, not pinned. `RunResult.record()` gains `threads`, the
  solve's, or None.
- `docs/project/modularity-layering.yaml` gains `gui -> sweep`, static (VER-61), in this item's commit.

**Item 3** (Sonnet).
1. `reproduce(directory, *, upto=None, …)`. A record whose `stages` end before `qoi` is reproduced to its last stage;
   `upto` past it is refused, naming both. The walk is `Session.run(case, upto=…)`.
2. Compare each reached stage's key with the record's `artefacts` hash, exact, a mismatch a `Drift` named
   `artefacts.<stage>`; `check_mesh` as today; each number of the manifest's `charge` group within `tolerance`;
   quantities only where `qoi` is reached. The solve-served check holds where `solve` is reached.
3. `nanopnp reproduce --upto <stage>`; `--json` carries `upto`.
4. Check: `uv run pytest tests/tier2/test_reproducibility.py`. QR-08's NOTE is main's, in the item's commit.

**Item 4.** `ResolvedCase.shell_spacing_nm`: a supplied outline's `provenance.min_vertex_spacing_nm` (the file read
once at resolve), else `contour_spacing_nm`; read by `RegionStage._key`, `derive_region` and the offset check, which
moves to the resolved case. A recorded spacing that is not positive, a repeated vertex, is refused at resolve, naming
the outline's file. The share: 2WCD's built outline, its z shifted by 1, 2, 3, 5 and 8 nm, supplied beside the
structure (AP1), each deposited; `solid_share` per shift goes into a concept of
`knowledge/04-clya-geometry-and-charge/`, listed in its `index.md`, with a line in `knowledge/log.md`. Where no shift
is refused, AP1's consequence names the largest shift measured, which passes.

**Item 6.**
- `Queue.limit` from *Solves at once*; `Entry` gains `start: Callable[[], None] | None` and `run: RunModel | None`;
  `Queue.pump()` starts waiting entries in order while fewer run; a member waits until its earlier waves end.
  `app.timer(0.25, …)` polls and pumps. A waiting build holds its `_Build` with the process unstarted, which `poll`
  reads as waiting, not as ended.
- *Run sweep* writes the plan into `Store.sweep_directory` and queues one entry per point; `collect` runs when the
  last ends. A model axis value is written `../models/<kind>/<name>.yaml`.
- A run entry is a `ui.expansion`: the plot on `plane.js`'s plot frame, the y axis `log` (decade ticks), a band per rung
  titled, a silent rung's band labelled, no threshold; a Quasar table of rungs: name, steps, `closed_on`, last value
  against its tolerance, least damping, forced steps, `note()`.
- `Views.show_pair(scene_url, plane_url)` shows both hosts side by side.
- Settings `solves_at_once`, `threads_per_solve`: `Annotated[int, Field(ge=1, le=64)]`, default 1, scope `user`,
  `applies="next run"`, section `compute`.

**Item 7.** `plot/data.py:ResidueCharges.of(protonation, charge, resolved)`: `residues()`, `markers(key)`, `at(r_nm,
z_nm, n=5)`, `Link`'s body moved; `residue_key` with it; `png` moves to `plane.py`, `_pdb_text` and `_chain_id` to `molview.py`. `gui/render.py:render_charge_elements(ChargeRequest)` writes
each element's r-weighted mean of the deployed coefficient, ∫ρ r dA / ∫ r dA at the solve's order, so that the
layer's ∫ 2πr dA keeps `q_mesh_e`, with the vertices and triangles to `<run>/viewer/charge.elements.npz`; `plane.py` draws it as a `mesh` layer with its bar.

**Item 8.**
- Tools: `overview`, `sweep`, `runs` with `view="page"`; `setup` with fields `models.molecular`, `models.continuum`,
  `models.physics`, `outputs`, `numerics.continuation` and `view="page"`; `charge` with `view="pair"`, a new
  `Tool.view` value routed as `Route("study", "pair")` and shown by `show_pair`. `Route.view`, `tool_view` and
  `VIEWS` (`"study": "pair"`) take `pair`; `tool_controls` gives it `molecule` and `plane`.
- `BuiltModel` gains `upto: ClassVar[str]`, read where `builds.py` reads `BUILD_UPTO[self.kind]`; `build()` takes
  `self.case()`; `kind` widens to `ItemKind`. `StudyModel`: `stages` 1 to 7 in walk order, `upto = "charge"`,
  `_built_case` and `body` reading `Project.study(name)` and its file, `paths` any case path. `api/project.py:BUILD_UPTO`
  gains no row. Its build passes `write=True` and the project's `runs`, so `deployed_coefficient` reads its record.
- The deployed layer reads the study's newest `upto-charge` record; with none, as after the boot walk, the pane offers
  *Build*. Runs lists only the records that reached `qoi`.
- Overview: the resolved study dumped by `dumps_case`; the three models, each a link; the physics it runs (model,
  electrolyte, corrections, `role_conditions` per side), each marked the model's or the study's (`changes`); the sweep's
  axes; the runs.
- `/api/study/{name}/charge/plane?layer=lattice|deployed&pick=<key>` and `/api/study/{name}/residues?r=&z=`.
- The graph: a mermaid flowchart, each model into *Charge on the mesh* or *Solve*, *Solve* into each output; node ids
  `node-<section>`, a click matched by the SVG id containing it; mermaid's default `securityLevel`, never `loose`;
  its colours from the theme's tokens.
- `render_shell.py` group `study`: the cached 2WCD project walked to `charge`, served by `--project`; each
  `/study/<id>` light and dark, a residue picked, *New study*; the charged tube run once, its queue entry unfolded;
  REV-256's mockups under `docs/design/mockups/fields/`, shot by `/np-gui render mockups`.

**Item 9** (Sonnet). `redraw.cjs <url>` drives `/study/charge` of a served 2WCD project: 20 picks on the map after a
warm-up, 1.5 s apart; per pick the time to the markers' paint and to Mol*'s second frame after the selection; prints
median and p95 of each, the browser's GPU string and `--json`. Check: it runs headless here (software GL).

### Work items

- [x] 229439d 1. `api/project.py` (D2's methods, REV-206), §5.3.5's NOTE (D2, D9); done when `test_study.py` and
  `test_project.py` pass. **Executor:** main
- [ ] 2. `sweep/plan.py`, `api/sweep.py`, `sweep/run.py`, `solve/stage.py`, `pipeline/run.py`, `gui/solver.py`, the layering file, FR-25's
  and §5.3.3's text, §5.3.1's NOTE on `outputs:` (D4, D7); done when `test_sweep_plan.py` and
  `test_gui_solver_process.py` pass. **Executor:** main
- [ ] 3. `api/reproduce.py`, `cli/running.py` (D9); done when its check passes. **Executor:** general-purpose on
  Sonnet, high; QR-08's NOTE main
- [ ] 4. `io/resolved.py`, `geometry/region.py`, `pipeline/checks.py`, AP5's NOTEs; REV-247's shares, AP1's
  consequence and VER-55's NOTE (D9); done when `test_exclusion_shell.py` passes and the `physics-reviewer` has read it.
  **Executor:** main
- [ ] 5. Compaction checkpoint. **Executor:** main
- [ ] 6. `gui/web/queue.py`, `frame.py`, `builds.py`, `settings.py`, `states.py`, `assets/plane.js` (D6 to D8); done when
  `test_study_runs.py` and `test_gui_settings.py` pass. **Executor:** main
- [ ] 7. `plot/data.py:ResidueCharges`, `gui/render.py` (D5); done when `test_study_charge.py` passes. **Executor:** main
- [ ] 8. `gui/web/study.py`, `study_tools.py`, `screens.py`, `pages.py`, `shell.py`, `modularity-layering.yaml`;
  `link.py` and `st-charge` removed; `render_shell.py` group `study` with REV-256's mockups; `/np-gui render shell`, `review`, `publish` (D1, D3
  to D6, D10); done when the digest is published and VER-78 passes. **Executor:** main
- [ ] 9. `.claude/scripts/gui/redraw.cjs` (D11); done when its check passes. **Executor:** general-purpose on Sonnet,
  high
- [ ] 10. Compaction checkpoint; the author's verdicts; the author runs `redraw.cjs`. **Executor:** main
- [ ] 11. `/np-gui collect`; REV-215, REV-240's, REV-252's, REV-255's and REV-256's points ruled or carried; the
  design document's rows (D10); done when the code and review say so. **Executor:** main
- [ ] 12. The tools finished to the verdicts, REV-254's Study words (D10); done when VER-78, VER-60 and VER-44 pass.
  **Executor:** main
- [ ] 13. Compaction checkpoint. **Executor:** main
- [ ] 14. `/np-gui render shell` and `review`, each finding fixed or a `REV-nn` row; AG7's numbers or a `REV-nn` row;
  VER-78's text, FR-33's and FR-39's matrix rows; `current.md`; done when the code and review say so. **Executor:** main

### Verification

| Test | Tier | Identifiers | Oracle and tolerance | Command |
|---|---|---|---|---|
| `tests/tier1/test_study.py::test_fr39_a_study_edited_in_the_suite_resolves_to_the_case_it_shows` | 1 | FR-39 | Example 01: `new_study`, then an own key, an override, `models.physics` and a variable, one each: each `study_values` value equals `value_at` of the resolved study, exact; each override in `changes` and the manifest; `reset` removes it; a refused leaf leaves the file's bytes | `uv run pytest tests/tier1/test_study.py` |
| `tests/tier1/test_study.py::test_fr39_a_studys_sweep_plans_over_a_variable_and_a_model` | 1 | FR-39 (b), (f) | Over `variables.v` and `models.physics`: each member resolves with its value and model; `Forecast.points` equal `keyed_walk`'s unbuilt stages | as above |
| `tests/tier1/test_sweep_plan.py::test_ver36_a_bias_set_through_a_variable_pairs_its_rectification` | 1 | VER-36 | `bias_V: v`, axis `variables.v` −0.05, 0, 0.05: one pair, (+0.05, −0.05); `v` also in another field: no pair, refused | `uv run pytest tests/tier1/test_sweep_plan.py` |
| `tests/tier1/test_gui_solver_process.py::test_fr25_a_run_records_its_thread_count_and_keys_as_at_one_thread` | 1 | FR-25; AR3 | A cylinder solved in a child at 2 threads: the solve summary and `run.json` say 2; each key equals the 1-thread walk's; a run at 1 thread is then served, saying 2 | `uv run pytest tests/tier1/test_gui_solver_process.py` |
| `tests/tier1/test_study_runs.py::test_ver44_the_unfolded_run_names_each_silence_and_what_closed_each_rung` | 1 | VER-44 | Events of a silent rung, one converged on entry, one closed by a forced step, one by the update, a served solve; one each: each row's words, `closed_on`, forced count, least damping; no threshold layer | `uv run pytest tests/tier1/test_study_runs.py` |
| `tests/tier1/test_study_charge.py::test_ver60_the_studys_charge_on_the_mesh_shows_the_walks_record` | 1 | VER-60 | `charged-tube` built to `charge`: each stage's hash equals the walk's; the image's `integral_e` equals `q_grid_e` to 10⁻¹²; rules at the worst planes; legs as `ConservationView`; the mesh layer `rho_fixed_C_m3`, its ∫ρ 2πr dA `q_mesh_e` to 10⁻¹²; `at()` on a charged atom ranks its residue first | `uv run pytest tests/tier1/test_study_charge.py` |
| `tests/tier2/test_reproducibility.py::test_ver35_a_run_stopped_at_its_charge_reproduces_to_that_stage` | 2 | VER-35; QR-08 | The tube's `upto-charge` record reproduces into a fresh store, its misses asserted, every key equal; a moved input aborts naming it; `upto: solve` refused | `uv run pytest tests/tier2/test_reproducibility.py` |
| `tests/tier1/test_exclusion_shell.py::test_ver59_a_supplied_outlines_shell_takes_the_outlines_recorded_spacing` | 1 | VER-59; AP5 | Recorded spacing 0.08 nm, offset 0.2 nm: `h_c_nm` keyed 0.08; offset 0.15 nm refused, naming 0.16 nm; a repeated vertex refused, naming the file; the derived case keys as before (VER-62) | `uv run pytest tests/tier1/test_exclusion_shell.py` |
| `tests/tier1/test_project.py::test_fr32_an_export_keeps_every_result_and_points_its_records_at_the_copy` | 1 | FR-32 | One assertion per REV-206 limit; a failed export leaves nothing | `uv run pytest tests/tier1/test_project.py` |
| `tests/tier1/test_gui_screens.py` | 1 | VER-78 (a) to (d), (m) | The Study pages in each state; (m): Charge on the mesh shows both hosts, each built once, and back to Molecular keeps them | `NANOPNP_REQUIRE_BROWSER=1 uv run pytest tests/tier1/test_gui_screens.py` |

### Out of scope

- New models from scratch (REV-242), the canvas's handles and keyboard pass, REV-255's Conditions view: WP5.21.
- A run opening its result, the field in 3D, REV-240's variation view: WP5.20.
- REV-41's `prepare` (FR-37) and region export (FR-28, v0.7).

### Open questions

None; the round's go to the author at item 10.

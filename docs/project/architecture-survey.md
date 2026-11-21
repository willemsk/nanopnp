# Architecture survey

A closed survey, dated at `8f4b09a` (21 November 2026, after WP5.22's design round). It changed no code. Two read-only
agents read the workbench (`src/nanopnp/gui/`) and the library core (`src/nanopnp/` but `gui/` and `validation/`)
and answered one question: do they make a robust, extensible system, or a patchwork? Their reports follow unedited.
The main claims were checked by hand: the one `Shell` per server (`gui/web/server.py:171`), the polling timers, the
shell's coefficient (`gui/render.py:737`), the fields file written by the shell (`gui/render.py:867`), the raw
`run.json` readers, the line counts and the closed `SWITCHES` tuple. The severities, efforts and orders are the
agents' inferences.

The author ruled on 21 November 2026 that the restructure they propose opens Phase 6, after a scope round and a
cleanup of the records and instructions, and that Phase 5 closes as soon as it can (REV-272). For a finding's
outcome, read REV-272 and the Phase 6 plan; the numbers below are those of `8f4b09a`.

## The workbench

**Verdict.** Neither a robust system nor a patchwork. [V] = verified in code, [I] = inferred.

[V] The shell has a real spine:

- a declarative registry of suites, tools and screens (`web/screens.py`);
- one pane base class shared by five of the six suites (`_Pane`, `web/tools.py:391`);
- one base for a model's build state (`BuiltModel`, `web/builds.py:113`);
- renderer-neutral specs for charts and (r, z) drawings (`Chart`, `Plane`), built by pure functions that the Tier 1
  tests cover;
- centralised tokens.

[I] That spine was built for one view per screen, one selection per page and one user per process. All five planned
features land exactly where it stops. Built on today's `Views` protocol, they would become a patchwork. If four seams
are added first, they need not.

### Inventory

| Concept | In code | Shared? |
|---|---|---|
| Suite and tool | `screens.SUITES`/`Tool`; `tools.BUILDS` (`tools.py:196`); `<id>_section` methods (`tools.py:566`); `pages.page_of` | Yes, but split across three places |
| Screen and route | `screens.SCREENS`, `pages.ROUTES`, `ui.sub_pages` | Yes |
| Frame | `_Frame` (`frame.py`, 1,313 lines): bars, rail, panel, dialogs, four view hosts | One |
| Tool pane | `_Pane`, about 957 lines with about 35 overridable hooks, in the same file as the Molecular pane; `_AnalysisPage` is separate | Five of six suites |
| Settings forms | `_Pane.field`; Study's `value_row`; `settings_page`; Analysis controls; `ChartView` axis fields | Five implementations |
| Tree | Project rail only (`frame.rail_items`) | n/a |
| Renderers | Mol* (`bridge.js`); hand-drawn canvas (`plane.js`, 950 lines); uPlot (`chart.js`); webgui iframe; DOM histogram; KaTeX; Mermaid | One per kind, three feeding styles |
| State | `Shell` bag, global to the process; `_MODELS`; about 20 module caches | Ad hoc |
| Style | `tokens.css`, `theme.py`, `frame.css` (325 `var(--)` uses, 3 hex literals) | Centralised |
| Layout | `SuiteLayout` (four fields, `io/project.py:72`); `frame.js` separators | Fixed |

**The top-level `gui/*.py` [V].** The Qt shell is about 3,540 lines: `app.py`, `widgets/`, `case_model.py`,
`scene.py` and `probe.py`, used only by Qt and its tests. `nanopnp-gui` still launches it (`pyproject.toml:90`), and
`gui/__init__.py:1` still describes the package as the PySide6 desktop application. The web shell shares `solver.py`,
`render.py`, `assess.py`, `convergence.py` and `run_model.py`, plus parts of `geometry.py` (`ImageModel`,
`lookup_table`, `ProfileEditor`, `density_section`, `reduced_image`) and `charge.py` (`ChargeMap`, `charge_image`,
`ConservationView`); the other halves of those two files are Qt-only. `workbench.md:405` says the `geometry.py`
duplicates "retire with Qt", yet `plane.py:20` and `analysis.py:14` import them.

### Smells

| Sev. | Smell | Evidence |
|---|---|---|
| High | The view region is four singleton hosts, and the `Views` protocol is named after its renderers | `frame.py:166-214`, `1247-1253`. Panes bypass it: `meso_tools.py:1062` and `:1025`, `tools.py:1776`. Analysis draws its own views: `analysis_tools.py:772`, `807`, `1123` |
| High | View events are global, one handler per event name, replaced on each sub-page; only `plane_point` carries its host | `frame.py:510`; `plane.js:846`, `883`. Two plots of one kind cannot be told apart |
| High | Selection and the shown run live in one process-global `Shell`, so every browser tab shares them | `shell.py:16-35`; `server.py:171` |
| High | Changes propagate by navigation plus polling: a 1 s timer and a JSON signature compare per pane | `tools.py:543`, `1117-1121`; `frame.py:1264`; `pages.py:617` |
| High | Links are a boolean per page, written twice | `analysis_tools.py:313`, `538-551`; `meso_tools.py:119`, `611-618`, `1052` |
| High (QR-13) | Physics in the shell: the solve's coefficient assembled, and `ngs.Integrate` element means | `render.py:737-886` (on VER-60, but in `gui`, which the yaml's backend list includes) |
| High (QR-13) | Block-weighted charge means and `integral_C` computed in the shell | `charge.py:95-230` |
| Med (QR-13) | A colour scale that duplicates `plot/data.py:849` with a different zero rule | `analysis.py:335-353`, `MAP_PERCENTILE` at `:59` |
| Med (QR-13) | Cut sampling, histogram counts, axis↔angle conversion written to the case, the membrane-offset gate | `analysis.py:570-581`; `continuum_tools.py:331`, `368`; `tools.py:319-336`; `tools.py:2151-2167` with `:86` |
| Med | One tool's metadata sits in three places; dispatch by string | `getattr` at `tools.py:566` and `study_tools.py:428` |
| Med | 13 private names imported across modules | `_Pane`, `_ContinuumPane`, `_keyed`, `_mapping`, `_value_of`, `_range`, `_view_table`, `_tex`, `_mtext`, `_field_tex`, `_chain_id`… |
| Med | Field-row markup hand-written six times | `tools.py:636`, `647`; `study_tools.py:624`, `712`, `939`; `meso_tools.py:680` |
| Med | (r, z) layers are untyped dicts, and their schema lives only in `plane.js` | `plane.py:236` |
| Med | Two registries of render children | `analysis_tools.py:58`, `meso_tools.py:68` |
| Med | About 20 mutable module caches | `builds.py:57`, `plane.py:626-632`, `meso.py:47`, `tools.py:279`… |
| Low | The shared state type imports the drawing module, just for a colour list | `states.py:18` → `runs.py:21` → `plane.SERIES` |
| Low | Data colours hard-coded rather than tokens | `plane.py:124-160`, `molview.py:146-159` |
| Low | The "screen ready" flag is set in 7 places | |
| Low | Six identical page factories; `open_result` duplicated | `frame.py:928`, `study_tools.py:1284` |

Duplication is moderate, not rampant [V]. The `_Pane` hooks are overridden, not copied. The copying is concentrated in
forms, links, page factories and Analysis.

### Seams worth keeping

- **The spec builders.** Pure functions that return data specs: `Chart`, `Plane`, `molview.scene`,
  `convergence_chart`, `cut_chart`, `charge_plane`, pinned by `test_meso_charge` and `test_study_runs`.
- **The registry.** `screens.SCREENS` drives the routes, the controls and the browser test's matrix
  (`test_gui_screens.py:97`).
- **The process bridges.** `SolverProcess`, `RenderProcess` and `AssessProcess` exchange plain data with child
  processes.
- **`BuiltModel` and the `ToolModel` protocol.** The library-backed state of each model's build.
- **Styling.** `tokens.css` plus theme attributes; Quasar colours pointed at tokens (`frame.py:1301`); class-first CSS
  (458 `.classes`, about 10 inline `.style`).
- **The guards.** The settings registry (WB-37), the vocabulary test, and the backend and layering ratchets.

### Target

1. **Library data, not shell numbers.** The library exposes field samples, cuts, probes, definitions, colour scales,
   element means, histogram counts and orientation maths, each with its Tier 1 test. The shell receives arrays with
   names and units. `render.py` keeps only the process plumbing.
2. **Typed view specs and a spec→Plotly translation.** `PlotGroup` holds typed layers (surface, contour, arrows, line,
   polygon, mesh, points, label), axes and a colour bar; `Chart` stays. Picking and editing are declared in the spec.
   A pure `to_plotly(spec, template) -> dict` is tested without a browser. A Plotly template generated from the
   tokens gives one style.
3. **View hosts.** A `ViewHost` mounts, `show(spec)`s, `dispose()`s, and emits events tagged with its view id.
   `PlotlyHost` can have many instances. Mol* stays one host, moved between slots rather than rebuilt [I: WebGL
   survives reparenting; spike it]. Every host sets `data-view-ready` and registers in `window.nano.views` for the
   tests.
4. **Per-client store and link bus.** A typed state per browser client holds the project, the shown run, the
   selection, the links and pins, and the selected node. Subscribers redraw on change. Polling stays only at the
   child-process boundary, which posts into the bus.
5. **Workspace.** The frame owns a layout tree: `Split(direction, sizes)`, `TabGroup`, `Slot(view_id)`, drawn with
   Quasar's `QSplitter` and `QTabs` (WB-33) and saved as a schema'd successor of `SuiteLayout`. Tools stop drawing
   views; they declare which views they want.
6. **Nodes and one form.** A suite's tools and the results tree share one node protocol: `label`, `children()`,
   `properties() -> FormSpec`, `views()`, `actions()`. A single `FormRenderer` does marks, reset, aside, validation
   and units. The properties pane is a dock panel bound to the selected node. One registry entry per tool replaces
   `BUILDS`, `<id>_section` and `page_of`.

### Order (the app works after every step)

1. **Test probes**: `data-view-ready` and `nano.views` beside today's renderers; the seven browser tests that read
   renderer internals move onto them (`test_gui_screens.py:246-341`, `583-653`).
2. **Library step**: the P2 point read, cut sampling, one colour-scale rule, histogram counts and the axis maths move
   into the library with their tests; VER-60's element and block means leave `render.py` and `charge.py`.
3. **Store and bus, per client**, carrying `Shell`'s selection fields and the two link booleans.
4. **`ViewHost` and events per view**, wrapping the four hosts first, then `PlotlyHost` with the token template.
5. **`FormSpec` and `FormRenderer`**, porting `_Pane.field` first.
6. **A minimal workspace**: one slot, plus *Split* to a second.
7. **The tree** on nodes, the store and `PlotlyHost`.
8. **Views move one suite at a time**: Electrolyte, Runs, Continuum, Physics, Meso; the outline editor last [I: Plotly
   has no filled 2D triangle mesh and no native vertex drag; spike both first]. `plane.js`, `chart.js`, uPlot and
   webgui leave with their last user.
9. **Full layout**: tabs and docking, then the separate properties pane.
10. **Cleanup**: `_Pane` hooks to nodes and forms; one tool registry; one artefact cache. Qt leaves (ADR-004 places it
    at WP5.27), with the Qt halves of `geometry.py` and `charge.py`.
11. **The finer style**, carried by the fewer components.

**Tests [V].** The SCREENS × STATES Playwright matrix and the Tier 1 spec-builder tests survive, provided the
`data-control` vocabulary and the spec builders are kept. Seven browser tests read renderer internals and break by
design at Plotly. The tests of the Qt and shared modules need their imports changed as modules move. Nothing tests the
panes, the links or the layout without a browser; the store and `FormSpec` would make those testable at Tier 1.

## The library core

**Verdict.** The pipeline core is a robust system: the stages, artefacts and store, the registries and the layering
guard hold up. The results side is a patchwork: `post/`, `plot/` and `gui/web/analysis.py` each own part of "a run's
fields and quantities", the run record has no type, and `Project` is a god class. File:line references are under
`src/nanopnp/`.

### 1. Layering: sound at the subpackage level

- **Verified:** the import graph, rebuilt from the AST, matches `modularity-layering.yaml`: no upward edge at module
  scope or inside a function outside `gui`/`validation`, and no cycle at module scope.
- **Upward imports for type annotations only:** `core/stages.py:88-89`→io; `io/resolved.py:24-26`,
  `io/artefact.py:21`, `io/manifest.py:31`→materials/numerics/physics (MOD-04, MOD-15): a 15-module cycle across
  `core.stages`, `io.*`, `geometry`, `mesh` and `physics.models`. **Low.**
- **Lazy imports hiding cycles inside a package:** `mesh/ingest.py:637,705` ↔ `mesh/generate.py:17` (`MeshStage`
  lives in `ingest.py:561`); `api/session.py:343` ↔ `api/sweep.py:17`, and `api/sweep.py:377` calls
  `session._member()._walk`. **Low–medium.**
- **Oversized modules:** `api/project.py` 1,884 lines (`Project` 1,522 lines, 49 public methods; **high**);
  `physics/models.py` 2,076 (`CoupledModel` 756); `plot/data.py` 1,508 (every stage's arrays, the QoI table, cuts and
  sweeps); `pipeline/run.py` 1,438 (`RunResult` with plotting, run reading, stage selection, the manifest and the
  walk); `pipeline/checks.py` 1,151 (every cross-registry check).

### 2. Extension points (core files touched)

- **A new physics model: 1–2 files.** `register_model` plus its declaration (`physics/models.py:1730`); model names
  are hard-coded only in the continuation ladder (`solve/continuation.py:602-735`). A good seam.
- **A new physics term or switch: about 10 files.** `inertia` appears in 11 core modules. `SWITCHES` is a closed tuple
  (`physics/models.py:146`), and every declaration states every switch (`:304`). The momentum terms are assembled a
  second time in `post/forces.py:545-551`; REV-224 and REV-257 are drift between the two. **High.**
- **A new correction:** the corrected properties are listed four times (`io/case.py:32`, `physics/models.py:1970`,
  `materials/models.py:18`, `materials/electrolyte.py:87`). The correction-model registry (`materials/models.py:149`)
  is bypassed: `io/case.py:704-713` accepts only installed files, and `registered_models()` there has no caller.
  **Medium.**
- **A new output quantity: 1–2 files.** `register_output` with its needs (`post/outputs.py:77`) is a good seam, but
  `Need` is a closed Literal (`:37`), `provided()` hard-codes the mapping (`:144-150`), and the unit comes from a
  suffix table (`plot/data.py:1235`). **Low.**
- **A new field sample: three layers per sample, no abstraction.** Cuts in `plot/data.py:1373-1406`, the grid and
  difference in `post/fields.py`, the mirror in `gui/web/analysis.py`. **Medium.**
- **A new schema version:** about 37 schema identifiers, each reader with its own equality check
  (`io/project.py:164,190`, `post/export.py:516`, `io/models.py:752`, `sweep/plan.py:778`, …); only the case has a
  retired list (`io/case.py:22`). Artefact schema strings are duplicated between `core/stages.py:443-688` and
  `io/artefact.py:23-58`. `nanopnp/fields/v0.5` (stage 7's charge fields) and `nanopnp/fields/v0.6` (the solved-fields
  file, `post/export.py:470`) share a family name for different documents. **Medium.**
- **Registries:** 10, in at least 5 shapes (H5 keeps them to after v1.0); the correction forms are a closed dict
  (`materials/forms.py:188`); the map from case path to registry is written by hand (`pipeline/checks.py:79-102`); two
  modules define `registered_models`. Some stages build their upstream stages instead of taking them from the walk:
  `solve/stage.py:196-208`, `post/stage.py:117`, `api/sweep.py:286`. **Medium.**

### 3. Data model: overlapping representations

- **"Run" has seven representations:** `RunResult`, `RecordedRun`, `StageRecord` (`pipeline/run.py:118-445`),
  `MemberResult` (`sweep/run.py:42`), `RunState` (`api/project.py:115`), `RunChoice` (`gui/web/analysis.py:76`) and
  `RunOutcome`. `run.json` (`nanopnp/run/v0.5`) has no Pydantic model and is parsed as raw JSON in `api/project.py`,
  `api/reproduce.py`, `gui/web/analysis.py`, `gui/render.py`, `gui/web/runs.py`, `gui/web/study.py` and
  `gui/web/study_tools.py`, against the rule of a Pydantic model at every serialisation boundary. **High** for run
  labels and Data nodes.
- **The solved-fields file is written by a GUI worker** (`gui/render.py:885-906`, `viewer/fields.npz`), not the
  library; the same data has three caches (`post/fields.py:157`, `post/export.py:387`, `gui/web/analysis.py:164`).
  **Medium.**
- **One vocabulary written many times:** four tables turn a key's suffix into a unit (`post/fields.py:46`,
  `io/variables.py:23`, `plot/data.py:1235` with `DISPLAY` at `:132`, `validation/comsol.py:113`); three functions
  list or name a run's fields (`post/fields.py:117`, `plot/data.py:1312`, `gui/web/analysis.py:275`).
- **The base layer holds GUI state:** `io/project.py` carries suite layouts in pixels and comparison views (`:49-66`,
  `:140`). **Low.**

### 4. `post/`: a sound sampling kernel behind per-screen helpers

- **Sound:** the cached P2 split, bucket point location, NaN outside the domain, and the difference over two fluids'
  overlap.
- **The interface:** each function takes a quantity as a string and returns bare tuples; every `field_at` locates its
  points again (`post/fields.py:262-265`); the locator is imported from `charge/deposit.py:145`.
- **What blocks REV-270:** `SolutionFields` (`post/export.py:364`) carries neither each field's order nor which fields
  are solved as ln c. P3 elements are allowed (`pipeline/checks.py:223`), but the file stores values only at the P2
  nodes (`post/export.py:139`).
- **What blocks definitions:** AG2's evaluator works on one exact scalar at a time (`Fraction`, `math.exp`, checks on
  `magnitude`; `io/variables.py:304-440`) and raises `CaseValidationError`; it cannot evaluate arrays. A species'
  current density needs the model's coefficients (`physics/nernst_planck.py:162`).

### 5. `api/` and `pipeline/`

`Session` (366 lines) is a clean facade for running a case. The GUI reaches past it: it imports 17 core subpackages
(81 imports from `io`, 29 from `pipeline`, 3 from `api.session`) and calls `resolve`, `selected_stages`,
`keyed_walk`, `read_run`, `open_run`, `restore` and `deployed_mesh` directly (`gui/render.py:449-913`,
`gui/web/plane.py:30`, `gui/charge.py:17-21`, `gui/web/states.py:22`). **Medium.**

### 6. Typing and errors

`type: ignore` (10) and `cast` (9) are few; `Any` is by design for the backend types (`core/typing.py`) and
`FieldValue = Any` (`io/case.py:29`, 72 uses). `Project` edits raw YAML dicts through private helpers from `io.models`
(`api/project.py:48-49`; 37 uses of `Any`). 54 exception classes with no common base; exit codes are looked up by
string path (`core/errors.py`); the `post` refusals are bare `KeyError`s (`post/fields.py:89-104`), so they exit as
"unexpected". **Medium–low.**

### 7. Duplication and dead code (low)

- **Dead:** `plot/data.py:1332` `default_potential_range_mV`; `post/fields.py:418` `joint_range` and `post/qoi.py:512`
  `summarise` (tests only); `materials.models.registered_models`.
- **Duplicated:** the guard for a solve with no saved state (`post/export.py:286`, `post/stage.py:245`,
  `gui/render.py:482`); the field-sampling loop (`post/export.py:342`, `validation/compare.py:153`); the steric "off"
  value (`physics/steric.py:9`, `materials/electrolyte.py:45`).
- **Name collisions:** `field_at` (`io/case_paths.py:103`, `post/fields.py:251`), `field_unit` (three modules),
  `value_at` (two), and three unrelated `probe` modules.

### Seams worth keeping

The stage registry (stages described without importing them, a figure found by schema, `FunctionStage`);
content-hashed artefacts and the store; the VER-61 layering guard; outputs that declare what they need of a model
(AH1); a `ModelDeclaration` readable without building the model; `MathOps` in `materials/forms.py` (one formula on
NGSolve or NumPy); AG2's whitelisted parser with pint units; the split between `Case` and `Session`.

### Target

- **`post/quantities.py`:** one catalogue of quantities (key, label, pint unit, display unit, domain, linear or log,
  components); every suffix table becomes a lookup in it.
- **`post/fields.py`:** `RunFields` carrying a `FieldInfo` (order, log, domain) per field, and `fields.locate(points)`
  to locate once and evaluate many quantities through the P2 basis; the locator moves to `mesh/`.
- **`post/samples.py`:** a registered `Sampling` protocol for Point, Line, Grid, Revolution and Overlap, returning
  coordinates, values, unit and mask.
- **`post/definitions.py`:** AG2 split into parse-and-dimension-check and evaluation, with a vectorised NumPy
  evaluator in the `MathOps` style; a registered list of variables; quantities that need the model's coefficients
  (current density, space charge) sampled when the fields are exported.
- **`io/runs.py`:** a Pydantic `RunRecord` with a label, and one reader.
- **`io/results.py`:** the `ResultsFile` model, and one shared reader for versioned documents that applies migrations.
- **`api/results.py`:** a `Results` facade (the default tree, run names, the comparisons migrated into Data), not more
  methods on `Project`. The GUI goes through `api` only.
- **The library writes the fields file**, under a new schema name.
- **Registries:** one generic `Registry[T]`, each entry naming the case path it serves; switches declared as data,
  a switch a model leaves unstated defaulting to off.

### Order (each step behaviour-preserving, Tiers 1 and 2 green)

1. **R1:** `RunRecord` and one reader; the readers move onto it.
2. **R2:** the quantity catalogue; the old functions become wrappers.
3. **R3:** fields with their order, `locate`, the P2 basis (REV-270), the library writing the fields file; a test that
   a quadratic is reproduced exactly and the log branch is right; a run above order 2 refused or read through NGSolve.
4. **R4:** AG2's evaluator split, and `post/definitions` with a Tier 1 test of the array evaluator against the scalar
   one (RSK-15).
5. **R5:** `io/results.py` and `api/results.py`, the comparisons' migration, the declaration listing the fields it
   provides (AH1), run labels; the edge `api → post` added to `modularity-layering.yaml` in the same commit (VER-61).
6. **R6:** `Project` split.
7. **R7:** `MeshStage` to `mesh/stage.py`; no stage builds its own upstream stages.
8. **R8:** one registry shape and switches as data (reopens MOD-08, ruled after v1.0 by H5).
9. **R9:** `post/forces` shares the weak form's terms (REV-224, REV-257).
10. **R10:** the dead code swept.

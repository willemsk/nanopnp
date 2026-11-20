# WP5.21 — The Analysis suite

**Status: delivered, 20 November 2026.** Planned 19 November 2026 on `main` (`2eaf29f`). It inherits AG6, AJ8, AN5, WB-06's
links and this plan's AU1 to AU3 (§8.2.31 to §8.2.45).

This plan belongs to [the Phase 5 plan](phase-5-workbench.md). `SPECIFICATION.md` governs; an identifier points to a
clause.

## In brief

**What changes.** The sixth suite, Analysis, opens a finished run: its field as a map, with a cut along the axis and
probes you place, or on its mesh in 3D; the current against the voltage; its numbers and changed settings. Comparison
saves two runs, side by side on one scale as maps or in 3D, or as their difference where both have fluid. As you ruled,
every plot moves to a borrowed chart library whose axes you set, with any Matplotlib colour map. A run cleaned from the
store is rebuilt on request and checked against its record. Study's recorded runs show their convergence.

**Cost.** About eight sessions, 12 to 18 agent hours and 16 touches with the round; your rulings add about two. The
install grows by about 10 MB; the checks before each push, about half a minute.

**What could go wrong.** The 3D viewer could fail to draw in the test browser; it drew a test square here, and a
failure shows its reason. Moving the convergence plot could change what it claims of a solve; its tests carry over
unweakened. A rebuilt run could differ from its record; the rebuild names each moved number.

**Your call.** At the round on 2WCD: the tiles' layout, whether a run opens on the map or in 3D, and where a probe's
values stand. *Recommendation:* rule them on the drawn screens.

## Execution brief

**Scope.** The phase entry's WP5.21 with AU1 to AU3: AG6's difference; comparisons; AN5's rebuild; REV-28, REV-30,
REV-253 and REV-260; REV-240's colour-map point; Q37 to Q41. **Depends on:** WP5.20 (merged). **Requirements:** FR-31,
FR-32, FR-33, FR-27; VER-44, VER-60, VER-62, VER-78; QR-08. **Constrained by:** AJ8, CON-07, CON-09, ADR-004's NOTE,
QR-13. **Implementing session:** Opus, high; sub-agents Sonnet, high. Tag `v0.6.0-alpha.21`.

**Amended when it lands:** FR-31's to FR-33's matrix rows; VER-78 (a) and (o); VER-44's restated NOTE (the recorded
convergence, the fetched scene); ADR-004's NOTE (AU1); §2.6's NOTE (AU2); §5.3.5's NOTE (comparisons, the rebuild); the
design document's renderer table, Analysis rows, rows Q37 to Q41, links 3 and 4, and the round's WB row.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| D1 Fields at points, the difference | `post/fields.py`, NumPy only: `field_at` interpolates a `SolutionFields` quantity linearly on its P2 cells split in four, NaN outside its domain; `field_difference` samples both runs on one cell-centred (r, z) grid over their fluids' overlap, NaN where either lacks the cell, `second − first`. `plot/data.py:sampled` calls `field_at` | AG6; decided by the plan |
| D2 A run's fields in the server | A render child writes `<run>/viewer/fields.npz` from `open_run(run).fields`, with the solve's hash; the server, importing no NGSolve, samples maps, cuts, probes and differences from it | VER-43's restated NOTE; decided by the plan |
| D3 The field on the mesh | `/vendor/webgui` serves the shipped renderer; a workbench render writes `scene-<field>[-<range>].json` once, which an iframe's host page fetches when a tile opens it. Comparison's pair takes the joint range, in its own file | REV-28, REV-30, VER-44, CON-09; AU3, ruled by the author |
| D4 The suite | Tools `explorer` and `compare` at `/analysis/<tool>`, `view="page"`. The explorer picks a study's run or sweep point; tiles: Field (a map, the cut's line and probes; *On the mesh*), I–V, Quantities (numbers, deviations, folder; Q37 to Q39), Axial cut. A click places the cut or a probe; typed values move them; a row's *Remove* unlinks one; dragging is WP5.23's | WB-06 links 3, 4; REV-238; decided by the plan |
| D5 Comparisons | `nanopnp/comparison/v0.6`: `name`, `runs` (two run folders relative to the project), `quantity`, `view` (`difference`, `maps`, `mesh`), `colour_map`, `range`; `Project.new_comparison`, `comparison`, `set_comparison`; a missing run is a problem. Any two runs, a quantity both carry. The pair's cut and probes stand on both maps; the cut's chart holds a series per run | FR-32, WB-04; AU2, AU3, ruled by the author |
| D6 Plots | uPlot 1.6.32 at `assets/uplot/`, served at `/vendor/uplot`; `gui/web/chart.py:Chart`, `assets/chart.js`. Every XY plot moves: Electrolyte's two, Runs' convergence, the I–V, the cuts. Each axis linear, logarithmic or square root, its range typed; drag-zoom, hover | REV-253; AU1, ruled by the author |
| D7 Colour maps | `matplotlib>=3.8` joins the `gui` extra; `gui/geometry.py:lookup_table` takes any registered name (`_r` reversed). Defaults: viridis; diverging where the range spans zero; a difference symmetric | WB-20; AU2, ruled by the author |
| D8 A recorded run's convergence | The solve stage adds each rung's `reporting` and `tolerance` to `newton_history.json` (no key moves); `runs.py:recorded_convergence` replays it; a rung without `reporting` claims neither silence. Runs' records are buttons (`aria-pressed`) | REV-260, VER-44; decided by the plan |
| D9 The rebuild | `Project.run_state(run)`: `solved`, `removed` or `unsolved`. *Rebuild* queues `RunRequest(rebuild=<run>)`; its child calls `Project.rebuild(run)`, `reproduce` into the project's store, every scalar compared at 10⁻⁶; a drift fails the entry, naming each | AN5 ("on request"), QR-08; decided by the plan |
| D10 Run and result | A done run's queue line keeps *Open* (WB-45) and gains *Result*; the explorer names its run, with *Open in Runs*; an I–V point picks its member | WB-06 link 4; decided by the plan |
| D11 The `solved` state | The charged tube: a run at 0.05 V, a sweep at ±0.05 V, comparison `tube-bias`; for VER-78 (o) alone | VER-78; decided by the plan |
| D12 The round | Render group `analysis`: the cached 2WCD project, a bias sweep and a Charge edit variant solved; reviewed, published, collected; then built | AJ8; decided by the plan |

### Grounding

**D1.**
- `post/export.py:SolutionFields` holds `whole` and `fluid` as `(points_m, cells, fields)`: P2 Triangle_6 cells, SI
  values, the log branch exponentiated at the nodes (`sampled_fields`). `fluid` is
  `mesh/primitives.py:ELECTROLYTE_DOMAINS`.
- `plot/data.py:sampled` uses Matplotlib's `LinearTriInterpolator` on `subdivided(cells)`, NaN outside; `axial_cutline`,
  `radial_cutline`, `field_values` (aliases `potential`, `u_r`, `u_z`) and `field_menu` call it. Matplotlib is the
  `plot` extra only (`pyproject.toml`), and `post` sits below `plot` (`modularity-layering.yaml`).
- `charge/deposit.py:locate(data, points_nm, *, cell_nm)` reads only `data.vertices` and `data.triangles` and returns
  the lowest-indexed containing triangle or −1 (`BARYCENTRIC_TOL` 10⁻¹²); `post -> charge` is a row.
- Importing `post.export`, `plot.data` and `charge.deposit` loads neither NGSolve nor Matplotlib (measured).

**D2.**
- `pipeline/run.py:open_run` leaves out an artefact the store lacks. `RunResult.fields` restores `solve` through
  `post/export.py:solution_fields`, using NGSolve, and raises `KeyError` without it.
- `gui/render.py:RenderProcess` spawns one child per request, which posts one event. `ChargeRequest(elements=True)`
  writes `viewer/charge.elements.npz`. `meso_tools.py:_RENDERS` keeps one child per record, and its `tick` drains it.
- `test_gui_viewmodels.py:test_if09_the_view_models_import_no_qt_and_no_ngsolve` imports `gui.render` and
  `gui.web.plane` in a fresh process.

**D3.**
- `render.py:render` writes `viewer/scene-<field>.json` and an `.html` that embeds the same JSON (REV-30's double
  write), sweeping stale `scene-*`. `host_document` sets `window.__nanopnp_viewer`.
- `render` names its pair `scene-<field>` alone and unlinks every other `scene-*` in `viewer/`, so a second range of one
  field overwrites the first.
- `RENDERER_SOURCE` is a `file:` URI under `RENDERER_DIRECTORY`, `gui/assets/webgui/`, not `gui/web/assets/`;
  `gui/web` serves no webgui. `pages.py` mounts `/vendor/molstar` and
  `/vendor/katex`. VER-78 (d) fails a request off the origin.
- `shoot.cjs --self-check` drew a webgui unit square in this container's headless Chromium (19 November 2026).
- A fixed range needs `funcmin`, `funcmax`, `autoscale` and `gui_settings` (knowledge 07/05; `render_charge`).

**D4.**
- `screens.py:SUITES`' analysis entry is `_later(...)`: its tools have empty ids, so `TOOL_SUITES` omits it.
- `frame.py:KINDS` lists comparisons in the rail, and `Frame.open_item` goes to `/analysis`. `Frame.run_entry`'s
  *Open* goes to `/study/runs`, with `shell.run_shown` set.
- `Project.runs(study)` lists `runs/<study>/*` folders that hold `run.json`. A record's `quantities` is the qoi summary,
  and `plot/data.py:qoi_rows` gives its rows. The manifest's `deviations` hold `switches` and `contributed`.
- A sweep is `sweeps/<study>-<short>/`: `sweep/collect.py:read_members`, each with `assignments`, `status`,
  `quantities` and a `directory`; `read_dataset`; `plot/data.py:sweep_curves` and `cis_referenced_bias_V`.
- `plane.js:nano.plot(hostId, drawing)` makes a view per host. `point_pick` emits `plane_point`. A `plot` frame
  neither pans nor zooms.

**D5.**
- `io/project.py` has the `comparison` kind, folder and suite. `Project._problems_of` returns nothing for one after
  its file check. `_export_plan` copies it unchanged. No schema or creator exists.

**D6.**
- uPlot 1.6.32 (npm, MIT, no dependencies, 14 March 2025): `dist/uPlot.iife.min.js` 51,081 B and `uPlot.min.css`
  1,857 B. The tarball matched npm's integrity `sha512-KIMVnG68…QIw==`. Scale `distr` 1 is linear, 3 logarithmic,
  100 custom with `fwd`/`bwd`; cursor `drag` zooms (`uPlot.d.ts`).
- The XY plots are `runs.py:convergence_plane` (a band per rung, log y) and `plane.py:electrolyte_plane` (two panels,
  the driver on a square-root axis). Both are drawn on `plane.js`'s `plot` frame. `test_study_runs.py` asserts the
  bands, the lines kept inside them and the absent threshold.
- `test_gui_screens.py:test_con09_the_vendored_libraries_are_unmodified` checks each file's sha256 in its `NOTICE.md`.
- VER-44 omits and counts a sample no log axis can place; `ConvergenceModel.count_omitted` counts it today.
- REV-253's WP5.18 points (the fitted range's shading, the dark key's swatch) and REV-260's lead with the conductance
  are the round's (D12).

**D7.** `gui/geometry.py:lookup_table(palette)` holds five fixed palettes. `ImageModel.rgba` draws NaN transparent.
`plane.py:_stops` feeds the bars.

**D8.**
- `solve/stage.py:_instrumented` writes each rung's `name` and `stage`, and each step's `iteration`, `residual`,
  `update`, `damping`, `trials` and `forced`. It computes `reporting` and `settings.relative_tolerance` for the hook
  alone.
- `io/artefact.py:Artefact.hash` covers schema, parameters and inputs, not the payload.
- `gui/convergence.py:ConvergenceModel.rung(name, stage, index, total, reporting, tolerance)`, `step`, `settle`.
  `study_tools.py:_StudyPane.runs_view`'s *Recorded runs* cannot be picked.

**D9.**
- `api/reproduce.py:reproduce(directory, store=…, progress, cancel)` loads `case.yaml` against the recorded base. It
  refuses a moved input or mesh and a solve served from the store, and returns `Reproduction` with its drifts.
- *Corrected in Item 3:* `check_inputs` compared a study's run's `case.yaml`, the merged case, with the study file's
  recorded hash, so `reproduce` refused every project run. A study's `case` and `models.*` roles are no longer
  re-read (§5.3.2's NOTE on reproduction).
- `clean_store(everything=True)` leaves run folders. `render.py:_state_path` raises naming a removed state.
- `gui/solver.py:_worker` runs a case or a sweep member; `RunRequest` carries strings: `case`, `store`, `runs`, `plan`.
- `Project.set_study_value(name, path, value)` sets a study's bias.

**D11.** `states.py:STATES` has four states, none of them solved; `boot` refuses a state outside `STATES`. `boot`
imports `write_charged_tube` (pnp-ns, 0.05 V). Its solve takes about 8 s (`render_shell.py`). `write_sweep` is
`gui/web/runs.py`'s; `run_plan` is `api/sweep.py`'s.

**Tests.** `test_project.py` walks the charged tube to `charge` and solves nothing. `test_study_runs.py` drives
`RunModel` from a written `LADDER` and solves nothing.

**D12.** `render_shell.py:filled_cache` walks 2WCD's study to `charge`; no group solves. Example 07, at
`size_scale: 4`, runs in about five minutes on one core.

### Implementation details

**Item 1.**
- `charge/deposit.py:locate_points(vertices_nm, triangles, points_nm, *, cell_nm)` holds `locate`'s body; `locate`
  calls it.
- `field_at(fields, quantity, r_nm, z_nm) -> ndarray`: `field_values`' choice of set and component. Points in nm;
  triangles `subdivided(cells)`; `cell_nm` is the median edge of those triangles; values are barycentric. Move
  `FIELD_ALIASES`, `field_values` and `subdivided` from `plot/data.py` to `post/fields.py`, and re-export them.
  `field_at` keeps the located split of the last four `(points, cells)` pairs, by identity, as `field_triangulation`
  does, which then goes.
- `GRID_CELLS = 1_000_000`. `FieldDifference(quantity, unit, r_nm, z_nm, first, second, difference)`, arrays `[iz, ir]`.
  `field_difference(first, second, quantity, *, window_nm=None, cells=GRID_CELLS)`: the box is the two fluids' point
  boxes intersected, with r ≥ 0, and the window. The spacing is `sqrt(area / cells)`; `n_r = ceil(width / spacing)`,
  `n_z` likewise, centres at `low + (i + ½)·width / n_r`. Each run is read on its own set. The mask is `isfinite` of
  both fluids' sampling of a constant. Refuse a quantity either run lacks, naming both runs' quantities.
- `field_grid(fields, quantity, *, window_nm=None, cells=GRID_CELLS) -> (r_nm, z_nm, values)`: one run's map over its
  field's box, on the grid rule `field_difference` uses.
- `joint_range(first, second, quantity) -> (low, high)` over both runs' nodal values.
- `post/export.py:fields_of(state) -> SolutionFields` is `solution_fields`' body after its restore; the tests and the
  child build fields with it.

**Item 2.**
- `post/export.py:write_solution_fields(fields, path, *, solve)` and
  `read_solution_fields(path) -> tuple[SolutionFields, str]`. Use `np.savez` with `allow_pickle=False`. Keys: `solve`,
  `model`, `{whole,fluid}_points_m`, `{whole,fluid}_cells`, `{whole,fluid}:<attribute>`, `wall_extent_nm` (empty when
  None) and `bulk:<attribute>`.
- `render.py`: `FieldsRequest(run)` posts `RenderedFields(path, solve, quantities)`. `RenderRequest` gains
  `document: bool = True` (False writes the JSON alone) and `colour_range: tuple[float, float] | None` (written as
  `render_charge` writes its range). With a range the stem gains `-` and the range's 8-hex digest; the sweep keeps
  the asked pair and the field's unranged pair, and a swept scene is rendered again when asked. The server reuses a
  file of that name.
  `host_page(scene_url, renderer_url, title)` fetches the scene, then initialises it as `host_document` does.

**Item 3.**
- `io/project.py:COMPARISON_SCHEMA` and `ComparisonFile` (`extra="forbid"`): `quantity` defaults to `potential`;
  `view` to `difference`; `colour_map` and `range` to None.
- The test's module fixture: `write_charged_tube`, `import_case`, `session().run` of the study; then
  `set_study_value(study, "boundary_conditions.bias_V", -0.05)` and a second run.
- `Project.new_comparison(name, first, second) -> Path`, `comparison(name)`, `set_comparison(name, **values)` (read
  back before it is written), and `sweeps(study) -> tuple[Path, ...]` (folders holding `plan.json`).
- `Project.run_state(run)` and `Project.rebuild(run, *, progress=None, cancel=None) -> Reproduction`.
- `_problems_of` refuses a file `ComparisonFile` refuses, and a run without `run.json`, at `runs`.

**Item 4.**
- History rungs gain `reporting` and `tolerance`. `plot/data.py:NewtonRung` gains `stage`, `trials`, `forced`,
  `reporting: bool | None` and `tolerance: float | None`.
- `Band.reporting: bool | None`. None notes "no step recorded; this record does not say which silence".
- `recorded_convergence(directory) -> ConvergenceModel | None`. A missing tolerance takes the resolved case's
  `newton.relative_tolerance`. A record whose `solve` stage is `cached` adds the served note.
- The replay test solves the charged tube once with `on_solve` a hook that feeds a `ConvergenceModel`, then replays
  the run's directory.

**Item 6** (Sonnet). Copy the tarball's `dist/uPlot.iife.min.js`, `dist/uPlot.min.css` and `LICENSE` (as
`LICENSE.uplot`) into `src/nanopnp/gui/web/assets/uplot/`, with a `NOTICE.md` laid out as KaTeX's. Mount `/vendor/uplot`
and `/vendor/webgui` (from `render.py:RENDERER_DIRECTORY`) in `pages.py`. Add `uplot` to the CON-09 parametrisation. Add
`matplotlib>=3.8` to the `gui` extra and run `uv lock`. Check: `uv run pytest tests/tier1/test_gui_screens.py -k con09`.

**Item 7.**
- `Chart(axes, series, bands, marks, panels)` serialises; each axis has `scale` (`linear`, `log`, `sqrt`) and
  `range`.
- `chart.js:nano.chart(hostId, spec)` builds uPlot. A log axis takes values, not log10; it nulls a value ≤ 0, and the
  chart's note counts it (VER-44). Silent rungs are null gaps. Bands are drawn in a `draw` hook. Axis controls are
  NiceGUI fields under the chart.
- `lookup_table` looks up its five own names first (`diverging` is the diverging default, `diverging_dark` on the dark
  theme), then `matplotlib.colormaps`; `Palette` becomes `str`.
- `convergence_chart` and `electrolyte_chart` replace the two `Plane("plot")` builders. `test_study_runs.py` reads
  the chart, its assertions unchanged in meaning.

**Item 8.**
- `gui/web/analysis.py:AnalysisModel` reads the runs, the sweeps, `run_state` and the fields files, keeping four, and
  the comparisons. `analysis_tools.py`.
- Routes under `/api/analysis/`: `scene?run=&field=` (the JSON file), `view?run=&field=&range=` (the host page),
  `image?run=&quantity=` (one run's map), `compare/{name}/image?which=first|second|difference` and
  `compare/{name}/cut`.
- `RunRequest.rebuild: str | None`, the run directory; the child opens `Project(<runs>/..)`.
- The cut is a `line` layer and probes a `points` layer. A tile is ready once its canvas, chart or iframe flag
  (ready or error) has drawn.

**Item 9.** `boot("solved")`: as `charged-tube`; then `session.run(study)` written, `write_sweep` over
`boundary_conditions.bias_V` `[-0.05, 0.05]`, `run_plan`, `collect`, and `new_comparison("tube-bias", run, member at
−0.05 V)`. `solved` stays out of `STATES`; `boot`'s guard admits it.

**Item 11** (Sonnet). In `render_shell.py`, group `analysis`. Copy the 2WCD cache. Sweep its study over `bias_V`
`[-0.1, -0.05, 0.05, 0.1]`. Add a linked variant flipping one charged residue, a study over it at 0.05 V, and a
comparison of the two studies' runs. Shoot each `/analysis/<tool>` light and dark, with the map, a cut, a probe,
*On the mesh*, the pair, the difference and a cleaned run's *Rebuild*. Add the 2WCD cache's group set. Check:
`render_shell.py --only analysis <dir>` exits 0.

### Work items

- [x] b86fd0f 1. `post/fields.py`, `charge/deposit.py:locate_points`, `plot/data.py` (D1); done when `test_analysis.py`'s
  difference tests pass and the `physics-reviewer` has read it. **Executor:** main
- [x] bb23417 2. `post/export.py` (the fields file), `gui/render.py` (`FieldsRequest`, `document`, `colour_range`,
  `host_page`) (D2, D3); done when `test_analysis.py`'s file test passes. **Executor:** main
- [x] 835274a 3. `io/project.py`, `api/project.py` (comparisons, `sweeps`, `run_state`, `rebuild`); §5.3.5's NOTE (D5, D9);
  done when `test_project.py`'s comparison and rebuild tests pass. **Executor:** main
- [x] 8d988a9 4. `solve/stage.py`, `plot/data.py:newton_history`, `gui/convergence.py`, `gui/web/runs.py` (D8); done when
  `test_study_runs.py`'s replay test passes and the `physics-reviewer` has read it. **Executor:** main
- [x] 5. Compaction checkpoint. **Executor:** main
- [x] f911e0c 6. uPlot vendored, `/vendor/uplot` and `/vendor/webgui`, Matplotlib in `gui` (D6, D7); done when CON-09's test
  passes. **Executor:** general-purpose on Sonnet, high
- [x] 7085e44 7. `gui/web/chart.py`, `assets/chart.js`, the two plots moved, `lookup_table` (D6, D7); ADR-004's NOTE, §2.6's
  NOTE; done when `test_study_runs.py` and VER-78 pass. **Executor:** main
- [x] 31a9e32 8. `screens.py`, `gui/web/analysis.py`, `analysis_tools.py`, `pages.py`, `frame.py`, `study_tools.py`,
  `gui/solver.py` (D3 to D5, D8 to D10); VER-78 (a); done when VER-78 passes. **Executor:** main
- [x] 1f2bcbf 9. `states.py` `solved`; VER-78 (o) (D11); done when (o) passes. **Executor:** main
- [x] 10. Compaction checkpoint. **Executor:** main
- [x] 969e763 11. `render_shell.py` group `analysis` (D12); done when its check passes. **Executor:** general-purpose on
  Sonnet, high
- [x] 4651541 12. `/np-gui render shell`, `review`, `publish`: the round (D12); done when the digest is published.
  **Executor:** main
- [x] 13. Compaction checkpoint; the author's verdicts collected. **Executor:** main
- [x] fc2ec53 14. The verdicts built; the round's WB row; the texts of *Amended when it lands*; a final render reviewed (D4 to
  D7, D12); done when the review's blocking findings are fixed. **Executor:** main

> **Outcome — the round's verdicts ([the record](../../design/reviews/2026-11-20-analysis.md)).** 8 keep, 6 change, 1
> drop of 15 picks. Built at item 14 (WB-50): a *Map · 3D* switch in the field tile's title bar; the 3D view on the
> map's range, framed on the pore through the scene's camera settings, its background the theme's; an *Outline*
> option; Comparison's *Mirrored* view (`view: mirrored`); *Solve again* for a cleaned run (D9's rebuild, renamed);
> the rungs as a table; a click placed to 0.01 nm. The tiles' layout, the probes' pane, the quantities shown and the
> chart library go to a tree of results, a design round and a package before WP5.22 (WB-51, REV-268). The author took
> a wording rule and sixteen examples, applied here; WP5.23 sweeps the rest (WB-52, REV-269).

> **Outcome — REV-264, ruled to this package at WP5.19's ship.** The solve records, per converged field, its r-weighted
> L2 norm, its gradient's and each component's integral (`field_norms`, in its summary, the manifest's solver group and
> the run record); a reproduction that re-enters the solve compares them within 10⁻⁶ of each number, or of 10⁻⁶ of the
> largest of its kind, NUM-16's floor (QR-08's NOTE; `test_reproducibility.py`). The gradient and the signed integral
> answer the physics review's point that a whole-domain norm is dominated by the reservoirs and blind to a reversed
> flow. A record written before them says it compared no number of the solve.

> **Outcome — the render's copied runs.** `render_shell.py:retarget` rewrote every JSON and YAML under a copied run, its
> manifest and case among them, which broke the manifest's hash; the earlier rounds drew 3D only from scenes already
> written. It now leaves `manifest.json` and `case.yaml` as the run wrote them, as a project's export does.

> **Outcome — the ship ([code review 065](../../code_reviews/CODE_REVIEW_065.md)).** The test-scope read dropped two tests
> outside §8.2.13 N1: a refusal's wording and a comparison file's round trip. The physics review's points closed
> QR-08's NOTE, which now names all three numbers and the floor; its doubt on the maps' linear reads stays open as
> REV-270. Code review 065 found 8 important findings and 10 nits, all fixed:
> - the explorer opens on the newest run;
> - a comparison says why a run cannot draw, and does not retry a failed read;
> - a component's 3D pair takes the range of the vector's size;
> - a drag-zoom no longer picks an I–V point.
>
> Measured to here: 4 sessions, 7.7 agent hours and 11 touches; the ship ran in the implementing session. The estimate
> was about eight sessions, 12 to 18 agent hours and 16 touches.

> **Outcome — round 2 ([the record](../../design/reviews/2026-11-20-analysis-2.md)).** Collected after the merge: 11
> keep and 6 change of 17 picks. Built at the collect (WB-53): a map draws the whole domain beneath the pore's
> close-up, on its scale, a comparison's the whole overlap; the outline is 1 px, drawn whole; the axial cut stands
> above the quantities. Three cards asked whether the 3D view was a mesh view. It is the field on the solve's flat
> mesh, and the author chose "Mesh now, 3D in tree": the view is named *Mesh*, and a true 3D view, the field turned
> about the axis, joins REV-268's round.

### Verification

| Test | Tier | Identifiers | Oracle and tolerance | Command |
|---|---|---|---|---|
| `tests/tier1/test_analysis.py` | 1 | FR-32 (AG6) | Two `ModelSolution`s populated as `test_field_export.py:_populated`, but linear, on cylinder pores of radius 2 and 2.5 nm at different `maxh`: each scalar's difference is the analytic one at every unmasked cell to 10⁻¹⁰ of its range (P2 holds a linear field; the split interpolates it exactly); one run twice gives exactly 0.0; a cell 10⁻³ nm inside both fluids is kept, one in either membrane or past either box NaN; the potential is masked to the fluids' overlap. Built by `fields_of` | `uv run pytest tests/tier1/test_analysis.py` |
| same | 1 | FR-27 | A `SolutionFields` written to the fields file reads back array-equal, with its solve hash | same |
| `tests/tier1/test_project.py` | 1 | FR-32, FR-27, QR-08 | A comparison of the charged tube's runs is written, read back, listed and exported with its runs; its run removed, a problem, not a refusal. After `clean_store(everything=True)`, `run_state` is `removed`; `rebuild` returns the record's solve hash to the store and every quantity within 10⁻⁶ | `uv run pytest tests/tier1/test_project.py` |
| `tests/tier1/test_study_runs.py` | 1 | VER-44 | The charged tube solved live and its stored history replayed by `recorded_convergence` give equal rung rows and chart bands; a history without `reporting` notes neither silence; a sample ≤ 0 on a log axis is null and counted; the existing assertions hold over the chart | `uv run pytest tests/tier1/test_study_runs.py` |
| `tests/tier1/test_gui_screens.py` | 1 | VER-78, CON-09, VER-44 | (a) every state loads `/analysis/<tool>`; (o) in `solved` the explorer draws its run's map, a two-point I–V and its conductance; *On the mesh* loads `/vendor/webgui/webgui.js`, fetches `/api/analysis/scene` from the origin, its flag ready; the comparison draws its difference and its cut's two series, its pair's scenes one `funcmin` and `funcmax`; uPlot's files unmodified. Each assertion separate | `uv run pytest tests/tier1/test_gui_screens.py` |
| The per-push VER-62 walks | 1, 2 | VER-62 | Unmoved by the history's keys | `.claude/hooks/gate.sh run` |

### Out of scope

- Dragging on the canvas: WP5.23 (REV-238).
- The 200 ms line on Analysis's views: WP5.22 (REV-258).
- Figure and field export: FR-28, v0.7. The 3D view keeps the renderer's colour map (AU2).

### Open questions

None blocking; the round's are in *Your call* (D12).

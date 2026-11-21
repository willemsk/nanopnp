# WP5.27 — Qt's removal and the short guide

**Status: in progress.** Planned 21 November 2026 on `main` (`0a7c24f`). It inherits S12, S13, S17, T5, U1,
AM15, AW1, AW3, AW7 and this plan's AW9 to AW11 (§8.2.17 to §8.2.47).

This plan belongs to [the Phase 5 plan](phase-5-workbench.md). `SPECIFICATION.md` governs; an identifier points to a
clause.

## In brief

**What changes.** The old desktop program leaves: one way to start the workbench, and about 650 MB less to install.
Before it goes, the browser workbench gains what you ruled. A running solve names its stage and step in the queue and
writes its log. Study setup reaches every setting that had no field, the choice of linear solver among them. The
results screen no longer says "None" under the changed settings when a stage recorded one. A self-test command checks
that an installation's compiled parts work, on Windows, macOS and Linux, in place of the Windows bundle. The guide's
desktop page becomes a short page on the workbench, with one picture a suite. The specification's sentences about the
desktop program become the ones written for the workbench.

**Cost.** About seven sessions, 7 to 13 agent hours and 10 of your touches: six as estimated, and one for the two
additions you ruled. The checks before each push lose the desktop tests and gain the self-test, about 20 seconds.

**What could go wrong.** A capability of the desktop program could be missing beyond the ones found: the package
checks all 41 on drawn screens before it deletes anything, and a new miss comes to you. The self-test could pass
where an install is broken: it is tested against a hidden solver and a broken protonation. A stored result could
move: the reference walks are compared, and none may change.

**Your call.** None now: you ruled the three open points on 21 November. *Recommendation:* approve the plan.

## Execution brief

**Scope.** The phase entry's WP5.27 with AW9 to AW11: the capability check; run progress and the run log; *More
values* over every unfielded setting; the contributed deviations; Qt, the bundle and the probe removed; the server's
self-test; the restated NOTEs made their clauses; the short guide; REV-134 and REV-228 closed. **Depends on:** WP5.21
(merged). **Requirements:** IF-09, FR-25, FR-27; VER-43, VER-44, VER-55, VER-60, VER-62, VER-78; CON-08, CON-09,
CON-11; RSK-13. **Constrained by:** CON-07, VER-61, VER-65, VER-79, N1. **Implementing session:** Opus, high;
sub-agents Sonnet, high. Tag `v0.6.0-alpha.27`.

**Amended when it lands:** each NOTE marked "lands with WP5.27" becomes its clause's text and the NOTE goes (D9);
§2.4 to §2.6, §5.1's `gui/` row, §5.3.1, §6.6, ADR-003, ADR-004, §7.6, §8.1 and Appendix A's CON-11 and CON-13 rows,
wherever they name the desktop shell, the bundle or the probe; the design document's Q rows.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| D1 The capability check | Rows Q01 to Q41 are checked on rendered screens against the design document's *Tabs or areas*, after items 1 to 3, and recorded in `docs/design/reviews/<date>-qt-capabilities.md`: row, shot, verdict. Q16 is the typed move. REV-274's five details are carried. Any other miss stops the package and goes to the author; nothing of Qt is deleted before the record is committed | Criterion 3; AW7, AW11, ruled by the author |
| D2 Run progress and the log | `RunModel` keeps the last `Rung` and gives `progress_line()`; a running run's queue line ends with it; the run's poll copies each new `RunModel.log` line to the queue's log, under the entry's label | Q33, Q34; AW9, ruled by the author |
| D3 *More values* | Study setup's list offers every case path with no field in the study's lists, except a file's header, `inputs.*`, `models.*`, `variables.*` and a path that crosses a list index; it writes through `Project.set_study_value` | Q05, Q07; CON-11's selectable solver; AW10, ruled by the author |
| D4 Contributed deviations | `AnalysisModel.deviations` lists the manifest's `switches` and its `contributed` entries; the tile says "None" for an empty list, only where `count` is 0 | FR-25; Q39; decided by the plan |
| D5 What leaves | The modules, scripts, tests and jobs of *Implementation details*, item 7. A view-model stays where the browser shell imports it or an in-scope test of a restated clause reads it; it leaves where only Qt's widgets read it. So `ProtonationView`, `ChargeView` and their loaders stay, and Phase 6's frame picker reads the first | S17; VER-60's kept tests (N1); AW11; decided by the plan |
| D6 The self-test | `nanopnp gui --selftest` runs `gui/web/selftest.py:main` in its own process: each payload exercised once, a server child started and asked for its health and for the shipped renderer, one line a payload, exit 0. A payload that fails raises `PayloadError` naming it, exit class 3. CI runs it in the `tier12` action, so on the three platforms on every push to `main`, nightly and before a release, and on a pull request's Tier 1 leg | ADR-004's packaging NOTE; RSK-13; J4, N4; decided by the plan |
| D7 The licence notice | `packaging/LICENSES-BUNDLE.md` becomes `src/nanopnp/THIRD-PARTY-LICENSES.md`, rewritten for an installation, a row for each payload of D6 and each front-end library; `nanopnp --env` states the GPL-2+ obligation and the notice's path. `packaging/` goes | CON-09, CON-11 as restated; decided by the plan |
| D8 The manifest's row | `io/manifest.py:DISTRIBUTIONS` loses `PySide6` and gains `nicegui` and `fastapi`. No stage key reads it | §5.3.3 with §2.6 as restated; decided by the plan |
| D9 The clauses | Each restated NOTE becomes the text. Four sentences are corrected to the program as they land: VER-43's (the view-models import no front-end framework; neither they nor the server import NGSolve); VER-43's and VER-44's self-test (a server child serves the renderer, compared by its bytes); VER-55's (the Mesh tool draws the stored mesh through `plot/data.py:mesh_elements`, no render child); RSK-13's ("on every push to `main`"). A hand edit's description says "workbench" | S17, T5; AM1; decided by the plan |
| D10 The guide and the site | `docs/guide/workbench.md` replaces `desktop.md`: install, start, the project folder, one section and one picture a suite, the self-test. `generate.py` copies the four register pages that link plans and reviews, so those links lead to GitHub | AW3; AM15, REV-228; decided by the plan |

### Grounding

**D1.**
- `docs/design/workbench.md` holds the rows Q01 to Q41 and, under *Tabs or areas*, where each lives in the browser.
- `.claude/scripts/gui/render_shell.py` renders ten groups (`GROUP_ENTRIES`); a shot is
  `shell-<group>-<name>-<scheme>.png`, listed in `index.json`.
- A code survey on `0a7c24f` found Q33 and Q34 missing, Q05 and Q07 short, Q39 wrong, and the details of REV-274;
  every other row has its code.

**D2.**
- `gui/run_model.py:RunModel._apply` already writes `log` lines for `Started`, `Stage` ("stage i of N: name"),
  `Produced`, `Progress`, `Finished`, `Failed` and `Cancelled`; it passes a `Rung` to `convergence.rung`, which
  discards `total`.
- `gui/solver.py:Rung` holds `name`, `stage`, `index`, `total`; `Stage` holds `name`, `index` (from 0), `total`.
- `gui/web/queue.py:Entry.line` returns glyph, status and label; `Entry.run` is the run's `RunModel`.
- `gui/web/runs.py`'s `poll`, set on the entry it queues, calls `control.poll()` each tick and writes to the queue
  only when the run settles. `frame.py:watch_queue` redraws when `Queue.moved` changes; `Queue.say` raises it.
- `frame.py:log_rows` draws `Queue.log`; `run_entry` draws `entry.line()`.
- `Rung.stage` is the ladder's stage (`solve/stage.py`'s `on_rung`), not the walk's `Stage.index`; a `Rung` comes
  only inside the solve stage. A failed run's `poll` says `{label}: {diagnosis}`, which the log's `failed` or
  `cancelled` line repeats.

**D3.**
- `gui/web/study_tools.py:more_values` offers `case_fields()` paths whose `owner_of` is a model kind, less `inputs.`
  and `models.`. It omits the study's own: `charge.smearing.*` (three), `charge.dielectric_transition_nm`,
  `numerics.nonlinear.*` (four), `numerics.linear.solver`, `numerics.continuation` and `outputs`, a list typed as
  YAML (`_parsed`). It offers `electrolyte.species.0.*` and
  `charge.edits.0.*`, which `io/models.py:_put` would write under a key `"0"`.
- `api/project.py:Project.set_study_value` writes a study's own key or an override, and refuses `variables.*` and a
  header key (`io/models.py:METADATA_KEYS`).
- `case_fields()` gives 122 paths; `gui/web/tools.py:FIELDS` covers 74.

**D4.**
- `io/manifest.py:_deviations_payload` writes `count`, `switches` and `contributed`, each contributed entry a
  `ContributedDeviation.summary()`; `mesh/ingest.py` and `charge/stage.py` contribute.
- `gui/web/analysis.py:AnalysisModel.deviations` reads `switches` only; `analysis_tools.py`'s quantities tile prints
  "None: every switch holds its validated default." for an empty list.

**D5.**
- PySide6 is imported by `gui/app.py`, `gui/probe.py` and `gui/widgets/*.py` only; `gui/case_model.py` and
  `gui/scene.py` are read by those and by `gui/geometry.py:load_structure`.
- `gui/web/` imports from `gui/geometry.py`: `ImageModel`, `ProfileEditor`, `colour_maps`, `lookup_table`,
  `density_section`, `reduced_image`; from `gui/charge.py`: `ChargeMap`, `ConservationView`, `charge_image`; and the
  modules `assess`, `convergence`, `render`, `run_model`, `solver`.
- `tests/tier1/test_gui_charge.py`, `test_gui_charge_protonation.py` and `tests/tier2/test_charge_2wcd.py` read
  `load_protonation` and `load_charge`; `molview.py:titration_states` gives the browser frame 0's rows itself.
- `tests/tier1/test_gui_solver_process.py` reads `run_outcome`, the reader REV-134 names; `open_run` is imported
  there.
- `gui/render.py:MeshRequest`, `render_mesh`, `RenderedMesh`, `renderer_source` and `readiness_script` have no
  reader outside Qt. `host_document` and `RENDERER_SOURCE` are read by `shoot.cjs`; `host_page` by `pages.py`.
- `tests/tier1/test_gui_widgets.py` is named by `.claude/hooks/gate.sh`, `.github/actions/tier12/action.yml`,
  `ci.yml` (two calls, the `bundle` job, `nightly-issue`'s `needs`), `justfile`'s `test-parallel`, `CLAUDE.md` and
  the steward skill, which also describes the `bundle` job. `.gitignore` excepts `packaging/nanopnp-probe.spec`.
- `gui/geometry.py:STAGE_1_FRAME` is read by `reduced_image` and `density_section`, which stay.
- `tests/tier1/test_source_conventions.py` lists `PySide6` among the extras' import names; `core/errors.py` lists
  `nanopnp.gui.probe:PayloadError` among the classes no command reaches.

**D6.**
- `gui/probe.py:exercise_payloads` and its helpers exercise MDAnalysis, gemmi, scikit-image, Shapely, Gmsh and the
  protonation, without Qt; `scene_document` meshes a unit square and takes `ngsolve.webgui.Draw(...).GetData()`.
- `python -m nanopnp.gui.web.server --no-browser --state empty` boots with no project and prints `READY`'s line.
  The guard wants the token; `/api/health` answers; `pages.py` serves `RENDERER_DIRECTORY` at `/vendor/webgui`.
- Importing `nanopnp.gui.web.server` loads `fastapi`, `nicegui` and `uvicorn`, and no NGSolve or structure payload
  (measured).
- `cli/workbench.py:_gui` reaches the server by `importlib.import_module`; `cli -> gui` is a string row of
  `modularity-layering.yaml` (REV-174). `core/errors.py:EXIT_CODES` sets `MissingExtraError` to `EXIT_CASE`: the
  installation is wrong.
- `gui` is in the layering file's `backend:` list (VER-65) and stays.

**D7, D8.**
- `pyproject.toml` force-includes the notice into the wheel; `gui/probe.py:licence_notice` finds it.
  `data/radii/pdb2pqr_charmm.yaml` needs PDB2PQR's notice in the wheel. `.github/scripts/prose-only.sh` treats
  `packaging/` and `src/` as code.
- `cli/workbench.py:_environment` and `_env` build `nanopnp --env`'s payload and lines. `cli` imports no `gui`
  module statically (VER-61), so the notice's path is `core/paths.py:LICENCE_NOTICE`,
  `PACKAGE_ROOT / "THIRD-PARTY-LICENSES.md"`; hatchling packs a file under `src/nanopnp/` unasked.
- `io/manifest.py:environment` maps `DISTRIBUTIONS` to versions, None where absent; `api/reproduce.py` reports a
  changed key as drift and fails nothing on it.

**D9, D10.**
- `gui/geometry.py:ProfileEditor.document` writes "Edited by hand in the nanopnp desktop shell from …" into the
  profile, and `geometry/profile.py:profile_digest` hashes it. No file under `data/`, `examples/` or `tests/` holds
  the sentence, so no pinned key moves; an edit saved again takes a new digest.
- `docs/scripts/generate.py:_copies` lists the copied pages and `rewrite_links` points a link that leaves the site at
  GitHub. `mkdocs.yml` takes no hooks. Of the site's pages, only `docs/project/review-findings.md`, `review-items.md`,
  `modularity.md` and `modularity-findings.md` link into `plans/` or `code_reviews/` (245 links).
- `docs/guide/desktop.md` is linked from `docs/index.md`, `guide/index.md`, `guide/geometry.md`,
  `guide/structures.md` and `mkdocs.yml`; its pictures are `docs/guide/img/{editor,run,convergence}.png`, written by
  `docs/scripts/capture_gui.py`.

### Implementation details

**Item 1 (D2).** `RunModel` gains `rung: Rung | None`, set in the `Rung` branch and cleared on `Started` and on each `Stage`.
`progress_line()` returns `""` unless `state == "running"`, else `stage {index + 1} of {total}: {name}`, with
`, rung {index + 1} of {total}` appended while `rung` is set. `Entry.line()` appends `: ` and the line when
it is not empty. The `poll` of `runs.py` keeps how many log lines it has copied and the last progress line; it calls
`queue.say(f"{label}: {line}")` for each new line, raises `queue.moved` when the progress line changed, and no longer says the diagnosis itself. Add
`shell-study-tube-running` to the render's `study` group, light scheme only, before `shell-study-tube-run`: it takes
that shot's click on `study-run` and a `wait_ms` of 2000, so the queue entry is shot while the tube runs.

**Item 2 (D3).** In `more_values`, drop the `owner_of` test; keep `not in listed`; exclude a path whose head is in
`METADATA_KEYS` or is `inputs` or `variables`, and a path with a numeric part.

**Item 3 (D4).** A contributed entry reads `<source>: <description>`, as its summary's keys give them. The test
writes a `manifest.json` into `tmp_path` and reads `AnalysisModel.deviations` on it; the tile keeps its sentence for
the empty list.

**Item 4 (D1).** Run `/np-gui render shell` (all groups). The record's table: `Q | Capability | Where in the
browser | Shot | Verdict`, the verdict `present`, `present as ruled (AW7)`, `carried (REV-274, point n)` or
`missing`.

**Item 6 (D6).** `gui/web/selftest.py`:

- `PAYLOADS` is the probe's tuple less its two PySide6 names, so the kept tests of the set hold; `FRAGMENT`, `FRAGMENT_Q_NET_E`, `PayloadError` and the exercise helpers are copied from
  `gui/probe.py` unchanged; the probe and `test_gui_probe.py` stay whole until item 7.
- `ngsolve`, `netgen`: mesh the unit square (`maxh=0.3`) and take the scene's data; no triangle, or no data, fails.
- `ngsolve.webgui`: spawn `[sys.executable, "-m", "nanopnp.gui.web.server", "--no-browser", "--state", "empty"]` with pipes;
  read the ready line within 60 s; GET `/api/health?token=…` (200), then `/vendor/webgui/webgui.js` with the cookie
  the first answer set; its bytes equal `RENDERER_DIRECTORY / "webgui.js"`; `host_page` names that URL; close the
  child's input and wait. The check is `_exercise_renderer(expected: Path)`, so a test passes a file of other bytes. A server that does not start fails naming `nanopnp.gui.web.server`.
- `gmsh` is skipped, with a line saying so, where `importlib.util.find_spec("gmsh")` is None.
- `main()` prints `exercised <line>` per payload to standard output and returns `EXIT_OK`; `PayloadError` propagates
  to the command line, classified `EXIT_CASE` in `core/errors.py:EXIT_CODES` as
  `nanopnp.gui.web.selftest:PayloadError`; the probe's row leaves the unreachable table in item 7.
- `cli/workbench.py`: `gui --selftest`, refused with `--state`, `--dev` or a project; `_gui` imports the module by
  name, as it does the server.
- CI: in `.github/actions/tier12/action.yml`, a step `uv run nanopnp gui --selftest` after the tests, with
  `inputs.code == 'true'`; the same step in `ci.yml`'s `tests` job on the `tier1` shard. `.claude/hooks/gate.sh`
  runs it in `run` mode after pytest.

**Item 7 (D5, D7).** Move the notice to `src/nanopnp/THIRD-PARTY-LICENSES.md`, rewritten, with
`core/paths.py:LICENCE_NOTICE`; the notice's two tests join `test_gui_selftest.py` and read that path. Delete:

- `src/nanopnp/gui/{app,case_model,scene,probe}.py`, `gui/widgets/`; `packaging/nanopnp-probe.spec`;
  `docs/scripts/capture_gui.py`, `.claude/scripts/gui/capture_qt.py`; `docs/guide/img/{editor,run,convergence}.png`;
  `tests/tier1/test_gui_widgets.py`, `test_gui_probe.py`.
- From `gui/geometry.py`: `StageStatus`, `StageRow`, `planned_stages`, `can_build`, `StageList`,
  `load_structure`, `membrane_slab`, `ViewTransform`, `nearest_vertex`, `nearest_edge`, `SummaryView`, `ImageView`,
  `OutlineView`, `StageView`, `load_view`, `GEOMETRY_STAGES`, then each private helper, import and `__all__` name
  left without a reader.
- From `gui/charge.py`: `BuildOffer`, `build_offer`, `charge_stages`.
- From `gui/run_model.py`: `RunOutcome`, `run_outcome`, `RunModel.outcome`, `RunControl.start`.
- From `gui/render.py`: `MeshRequest`, `render_mesh`, `RenderedMesh`, `renderer_source`, `readiness_script`, and
  their branch of `_worker`.
- `pyproject.toml`: `PySide6`, the scripts `nanopnp-gui` and `nanopnp-probe`, the `packaging` group, the notice's
  force-include; then `uv lock`.
- `ci.yml`: the `bundle` job, its name in `nightly-issue`'s `needs`, each `--ignore=tests/tier1/test_gui_widgets.py`
  and `QT_QPA_PLATFORM`; the action's widget step; `gate.sh`'s `--ignore` and its PySide6 branch;
  `prose-only.sh`'s `packaging/` case; `justfile`'s widget line; `.gitignore`'s exception.
- `test_source_conventions.py`'s `PySide6` entry; the `qt` target of `.claude/skills/np-gui/render.md`; the widget
  file's and the `bundle` job's lines in `CLAUDE.md` and the steward skill; `gui/__init__.py`'s docstring names the
  workbench.

Tests that change: `test_gui_viewmodels.py` drops `case_model`,
`probe` and `scene` from its import list; `test_gui_solver_process.py` reads the run's record through `open_run`
where it read `outcome`.

**Item 10 (D10).** The page: *Install* (`uv sync --all-extras`, then `nanopnp gui --selftest`), *Start*
(`nanopnp gui [<project>]`, `nanopnp project import`), *The window* (suites, tools, the queue, problems), then
Molecular, Meso, Continuum, Physics, Study, Analysis, each two to four sentences and one picture, and *Known gaps*
(QR-16's keyboard gaps; REV-274). Pictures, light scheme, copied to `docs/guide/img/workbench-<suite>.png` from the
shots `shell-2wcd-m-protonation`, `shell-meso-charge`, `shell-2wcd-c-mesh`, `shell-physics-electrolyte`,
`shell-study-tube-convergence` and `shell-analysis-explorer`. `generate.py:_copies` adds the four register pages
under `OUTPUT / "project"`; their sources join `exclude_docs`; the navigation and each link to them follow
(`docs/project/index.md`, `links.py`).

### Work items

- [x] e5ddd51 1. `gui/run_model.py`, `gui/web/queue.py`, `gui/web/runs.py`, `render_shell.py`: run progress and the log
  (D2); done when the code and review say so, on the running shot. **Executor:** main
- [x] 157a2b4 2. `gui/web/study_tools.py`: *More values* (D3); the design document's Q05 to Q08 row; done when the code and
  review say so, `numerics.linear.solver` set to `superlu` on a rendered study. **Executor:** main
- [x] a7a7f6e 3. `gui/web/analysis.py`, `analysis_tools.py`: contributed deviations (D4); done when its test passes.
  **Executor:** main
- [ ] 4. The capability record (D1); done when every row has a verdict and none is `missing`. **Executor:** main,
  with the `gui-reviewer` sub-agent on the shots
- [ ] 5. Compaction checkpoint. **Executor:** main
- [ ] 6. `gui/web/selftest.py`, `cli/workbench.py`, `core/errors.py`, `tests/tier1/test_gui_selftest.py`, CI and
  the gate (D6); done when its tests pass and the command exits 0 here. **Executor:** main
- [ ] 7. The removal, the notice (D5, D7); done when Tier 1 and the two Tier 2 files pass and `uv lock --check`
  is clean. **Executor:** main
- [ ] 8. `nanopnp --env`, `io/manifest.py` (D7, D8); done when `--env`'s test passes. **Executor:** main
- [ ] 9. The clauses (D9): `specification/`, `SPECIFICATION.md`, `gui/geometry.py`'s description,
  `knowledge/07-software-stack/05-gui-and-packaging.md` and `06-licence-summary.md`, `README.md`, `CONTRIBUTING.md`,
  `CLAUDE.md`; done when `clause.py` prints each clause without its NOTE and the strict build passes.
  **Executor:** main
- [ ] 10. The guide and the site (D10); REV-134 and REV-228 set `fixed`; done when the strict build and `links.py`
  pass. **Executor:** `general-purpose` on Sonnet, high effort, for the page's text from *Implementation details*;
  main for `generate.py` and the registers

### Verification

| Test file | Tier | Identifiers | Oracle | Tolerance source | Command |
|---|---|---|---|---|---|
| `tests/tier1/test_analysis.py` | 1 | FR-25 | A manifest with one contributed deviation and no switch lists that deviation; the list is empty only at `count` 0 | exact | `uv run pytest tests/tier1/test_analysis.py` |
| `tests/tier1/test_gui_selftest.py` | 1 | VER-43, VER-44, VER-55, VER-60, RSK-13 | The kept probe tests, unweakened: the payload set; no undeclared payload imported; the fragment at 0 e and −3 e; charges that ignore the pH fail naming `propka`. New: `ngsolve` hidden in `sys.modules` fails naming `ngsolve`; the served renderer against a file of other bytes fails naming `ngsolve.webgui`; the whole self-test passes | VER-60's 10⁻⁶ e | `uv run pytest tests/tier1/test_gui_selftest.py` |
| `tests/tier1/test_gui_selftest.py` | 1 | CON-11, VER-60 | The notice has a row for each payload and names GPL-2+, LGPL-2.1, LGPL-3 and BSD-3-Clause; `nanopnp --env` states the GPL-2+ obligation | exact | as above |
| `tests/tier1/test_gui_viewmodels.py` | 1 | VER-43, VER-55, VER-60, CON-09 | In a fresh process the view-models load no Qt, NiceGUI, NGSolve, Netgen or structure payload; importing the server loads no NGSolve, Netgen or structure payload | exact | `uv run pytest tests/tier1/test_gui_viewmodels.py` |
| `tests/tier1/test_gui_charge*.py`, `tests/tier2/test_charge_2wcd.py`, `test_gui_geometry_2wcd.py` | 1, 2 | VER-55, VER-60 | Unchanged | their clauses | `uv run pytest <file>` |
| `tests/tier1/test_gui_screens.py`, `test_layering.py` and the goldens | 1, 2 | VER-78, VER-61, VER-65, VER-79, VER-62 | Unchanged; no edge added, no key moved | their clauses | `.claude/hooks/gate.sh run` |

Items 1, 2, 4, 9 and 10 are outside the test scope (N1): the code and review say so, with VER-45's strict build.

### Out of scope

- REV-274's five details: Phase 6's layers and polish pass.
- Dragging a vertex, QR-16's keyboard gaps, the full guide, the guided route: Phase 6 (AW1, AW3, AW7, AW8).
- Plotly in place of `webgui` and uPlot: Phase 6's tree of results (WB-57).

### Open questions

None; D1 names the one stop.

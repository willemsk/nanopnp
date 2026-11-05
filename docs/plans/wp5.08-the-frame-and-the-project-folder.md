# WP5.08 — The frame and the project folder

**Status: planned, not started.** Planned 5 November 2026 on `main` (`1e4497e`). It inherits §8.2.17 S11, S12,
§8.2.18 T2, T8, §8.2.31 AG1, §8.2.33 AI1, REV-32, REV-52 and MOD-13's command-line part.

It belongs to [the Phase 5 plan](phase-5-workbench.md). `SPECIFICATION.md` governs; an identifier points to a clause.

## In brief

**What changes.** The workbench gets its document and its window. A project is a plain folder of models, studies,
comparisons, input files, run records and stored results, with a project file holding no physics. A case file imports
into a project, split into its two models and its study, and computes exactly what it did. A project exports as a
portable copy of readable files. The window gains its frame: menus, a command palette and shortcuts, the four suites,
the project list, the queue and log, the changed values with a reset each, the problems list, and the settings, with
light, dark and your own colour themes. The store can remove what an older release wrote.

**Cost.** About two and a half weeks. No new library.

**What could go wrong.** An imported case could compute something else; a test compares every step's key with the
original's. An export could miss a file; it refuses an input outside the project, and a test reads the copy back. The
store could remove a current entry; a test removes the old ones and walks again from the store.

**Your call.** None open. You ruled the colour themes: they come now, and your own theme sets its own contrast.

## Execution brief

**Scope.** The frame and the project folder, as the phase plan states. **Depends on:** WP5.07. **Requirements:**
FR-31, FR-32, FR-34, FR-35, FR-25, FR-27, IF-01, IF-02, IF-09, QR-16; VER-61, VER-62, VER-64, VER-78. **Constrained
by:** ADR-004's NOTEs, CON-07, CON-09, VER-60, G6. **Implementing session:** Sonnet, high effort. Tag
`v0.6.0-alpha.8`.

**Amended in this commit:** QR-16 (AI1). **When it lands (item 13):** NOTEs on FR-32, FR-34, FR-35, §5.3.2 (older
entries) and §5.5 (optional members); VER-64 and VER-78 as rows 4 and 8 state; Appendix A; the design document's folder;
REV-32, REV-52 and MOD-13's command-line part `fixed`.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| D1 The folder | `<project>/nanopnp-project.yaml` (`nanopnp/project/v0.6`, Item 1), `models/molecular/`, `models/continuum/`, `studies/`, `comparisons/`, `inputs/`, `runs/<study>/<run>/`, `sweeps/`, `store/`. An item's name is its file's stem and its `name:`. The folder is the truth: an unindexed file is appended on open, an indexed name without its file is a problem. A run is `runs/<study>/<short key>`, `upto-<stage>-<short key>` when truncated. Format in `io/project.py`; `api/project.py:Project`, in `PUBLIC` | S11; WB-11, WB-13; FR-32 |
| D2 Import and export | `Project.import_case` splits a plain case by `owner_of` into the two models and the study, copying each input into `inputs/`, written relative; an expression stays in the study; a study is refused. `Project.export(destination, *, store=False)` copies the project file, the items, `inputs/`, each run's three files and results, each sweep's records; an input absolute or outside the project is refused before anything is written | FR-32; keys hash file contents, not paths (§5.3.2) |
| D3 Changed and problems | `io/defaults.changes(document)` lists each leaf away from its default (validated for a switch, else the schema's) and each study override, with kind, value, default and the model's value. `Project.reset` deletes the key from the item setting it. `Project.problems()` lists each missing file, mismatched name and item refused on load, with the refusal's case path and its suite | FR-34, FR-35; VER-60: the shell computes nothing |
| D4 REV-52 and REV-32 | `core/stages.py:ContributesDeviations`, runtime-checkable like `SolveReporting`; the walk tests it by `isinstance`; VER-64 checks each optional member's signature. `Store.stale()` lists each entry of an older version of a schema a stage writes now, never a newer one; `Store.remove` deletes them | T2; §5.3.2 |
| D5 The command line | `cli/__init__.py` keeps `main` and re-exports `build_parser`; each command family is a module with `register(subparsers)`; no `cli/` module over 600 lines, no function over 100. `nanopnp gui [<project>]` opens a project, creates one in a missing or empty folder, refuses anything else; with none, the last project, else none open. New: `nanopnp project new|import|export`, `nanopnp store prune [--remove]` | MOD-13; IF-02 |
| D6 The frame | Each suite a page in the frame; palette, changed list, problems and settings as overlays opened by a query; one command registry for menus, palette and shortcuts, keys taken by a client listener; the queue a server-side list; settings and user themes under `config_root()` (`NANOPNP_CONFIG`), a theme a base and its colour tokens, a shipped one read-only, none contrast-checked. The four states boot projects | FR-31, FR-34, FR-35; WB-03, WB-09, WB-13, WB-18, WB-19, WB-30, WB-31; AI1 |

### Grounding

**D1.**
- `io/store.py:Store.run_directory(name, digest)` returns `<root>/runs/<name>-<short>`; its one caller,
  `pipeline/run.py:run_document`, passes `label`, which is `f"{document.name}-upto-{stages[-1]}"` for a truncated walk.
  A `runs=` root and an `upto=` argument keep the default paths identical. `Store.sweep_directory` returns
  `<root>/sweeps/<name>-<short>`, so a project's sweeps need their own root to leave `store/` with it.
- `api/session.py:Session(store)` takes a `Store` as is and sets `_store_given`; `Session.open` then reads that store.
- `io/models.py` already reads `models: {molecular, continuum}` beside the study and `MOLECULAR_SCHEMA`,
  `CONTINUUM_SCHEMA`; a model file holds `schema`, `name` and its kind's keys. Comparisons have no schema until WP5.12:
  the project indexes and exports their files unread.
- `io` imports only `core` outside itself at run time (`docs/project/modularity-layering.yaml`); `api` may import
  `io`, `pipeline` and `sweep`. `nanopnp.PUBLIC` and its `TYPE_CHECKING` mirror are checked by `test_layering.py`.
- `core/errors.py` enumerates every public exception (IF-02's NOTE): `ProjectError` joins it as `EXIT_CASE`.

**D2.**
- `io/case_paths.py:path_fields()` gives `inputs.mesh.path`, `inputs.charge.path`, `inputs.eps_r.path`,
  `inputs.profile.path`, `inputs.pqr.path`, `structure.source.path`, `structure.ensemble.trajectory`, `models.*`. A
  correction value is a file when `core/paths.py:names_a_path` holds; `correction_identity` keys it by its file name.
- `io/models.py:owner_of` and `OWNERS` decide a leaf's kind; `_flat` walks a dump through `block_paths()`; `_rebased`
  reads a model's relative path beside its file.
- `validation/charged_tube.py:write_charged_tube` writes a case with `inputs.pqr` and `inputs.profile` at absolute
  paths, so its import exercises both models and the copy into `inputs/`.
- A walk with `write=True` writes `case.yaml`, `manifest.json` and `run.json` (`RunResult.write`); `run.json`'s
  `files` lists the report's payload in the store. `pipeline/run.py:read_run` checks a run directory without a store.

**D3.**
- `io/defaults.py:deviations` covers `SWITCH_PATHS` only; `io/case_paths.py:schema_default(path)` gives
  `(has_default, default)` per leaf. `CaseDocument.models_record.overrides` maps a path to `(model value, study value)`.
- `CaseValidationError.errors` holds pydantic's `ValidationError` when the schema refused; its `errors()[0]["loc"]`
  is the case path. A refusal by a check carries none: its problem has no path and leads to the item's suite.

**D4.**
- `pipeline/run.py:_contributed` reads `getattr(stage, "deviations", None)`. `charge/stage.py` and `mesh/ingest.py`
  define `deviations(self, inputs)`; `solve/stage.py` defines `with_solve_hook(self, hook)`; `mesh/ingest.py` defines
  `forecast_parameters(self, inputs)`. `validation/modularity.py:stage_conformance` reads `describe`, `key`, `run`
  statically, over `parse_package(root, sources)`, so row 4's non-conforming stage is a `sources=` tree registering it;
  `isinstance` on a runtime-checkable protocol checks names only, never a signature.
- Stages put `nanopnp/protonation-frame/v0.5` and `nanopnp/charge-grid/v0.5` besides their registered schemas
  (`charge/protonation.py`, `charge/stage.py`); a stage of one's own writes `nanopnp/stage/<name>/v1`. An entry's
  `meta.json` records its `schema`; `io/case.py:RETIRED_SCHEMAS` names `nanopnp/case/v0.5`.

**D5.**
- `cli/__init__.py` is 1,631 lines; `build_parser` is about 360. Tests import only `main`, `build_parser` and
  `nanopnp.cli.reading`; `cli/reference.py` imports `build_parser`. `_gui` imports the server by string (REV-174's row).
- `cli/__init__.py:_environment` feeds `nanopnp --env`; `config` and `NANOPNP_CONFIG` join it.

**D6.**
- NiceGUI 3.18.0 is installed. `ui.keyboard` handles keys on the server and cannot prevent a browser default, so a
  listener in `assets/frame.js` calls `preventDefault` and `emitEvent('command', id)`, as `bridge.js` emits `mol_pick`
  to `ui.on`. `ui.splitter(value=…, on_change=…)` takes a percentage; `ui.menu`, `ui.menu_item`, `ui.dialog` exist.
- ADR-004's NOTE starts the wrapper's server as `nanopnp gui --no-browser --port 0`, with no path, so the bare
  command must not refuse.
- `docs/design/tokens.css` sets the dark theme under `prefers-color-scheme` unless `data-theme="light"`, and under
  `data-theme="dark"`; `data-density="compact"` sets the compact sizes. Its colour tokens are the `--x: #rrggbb` lines.
- `gui/web/states.py:boot_case` walks to `charge` with `write=False` and keeps a case or gate refusal as text;
  `.claude/scripts/gui/render_shell.py` reads `STATES` and `SCREENS`, so new screens render with no script change.
- `core/paths.py` has no configuration directory; `store_root()` with `NANOPNP_STORE` is the pattern.

### Implementation details

**Item 1.** `io/project.py`: `PROJECT_SCHEMA = "nanopnp/project/v0.6"`, `PROJECT_FILENAME = "nanopnp-project.yaml"`,
`ITEM_NAME = r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$"`, `FOLDERS = {"molecular": "models/molecular", "continuum":
"models/continuum", "study": "studies", "comparison": "comparisons"}`. Strict pydantic: `SuiteLayout(rail_percent=18.0,
bottom_percent=25.0, rail_folded=False, bottom_folded=True)`; `ProjectFile(schema, name, library: {molecular,
continuum, studies, comparisons: list[str]}, open: list[str], current: str | None, layout: dict[Literal["molecular",
"continuum", "study", "analysis"], SuiteLayout])`, an item written `"<kind>/<name>"`. `read_project`, `write_project`
(atomic). `io/store.py`: `Store(root, *, runs=None, sweeps=None)`; `run_directory(name, digest, *, upto=None)`; `sweep_directory`
under `sweeps` when given; `StaleEntry(schema, hash, path)`; `stale()` walks `artefacts/*/*/*/meta.json`; the current
schemas are every registered stage's `artefact_schema` and the two auxiliary ones; an entry is stale when its schema's
family (`nanopnp/<family>/`) is a current one's and its version is lower, compared as numbers, so a newer release's
entries in a shared store, and every `nanopnp/stage/` entry, stay; `remove(entries) -> int`.

**Item 3.** `api/project.py`: `ProjectError(ValueError)`; `Project.create(folder, name=None)`, `Project.open(folder)`,
`import_case(case, name=None) -> str`, `add_input(path) -> Path` (a different file of a taken name is refused, naming
both), `items(kind)`, `path(kind, name)`, `study(name) -> Case`, `changes(kind, name)`, `reset(kind, name, path)`,
`problems()`, `export(destination, *, store=False)`, `session() -> Session` over `Store(<project>/store,
runs=<project>/runs, sweeps=<project>/sweeps)`, `runs(study)`, `save_layout(suite, layout)`, `open_item(item)`. `Problem(item, path, message,
suite)`. Export writes into a missing or empty `destination`; a run's result files go to `runs/<study>/<run>/results/`.
`changes` of a model reads its file's leaves; a leaf with no default is not a change unless overridden.

**Item 5.** `cli/common.py` (shared flags, logging, `_emit`, `_refuse`, `_destination`, `_Progress`, the positive
parsers, `_store`), `cli/parser.py:build_parser`, `cli/running.py` (run, stage, inspect, plot, reproduce),
`cli/building.py` (geometry, mesh), `cli/sweeping.py`, `cli/validating.py` (validate and its helpers),
`cli/workbench.py` (gui, project, store, env). Move code unchanged; only imports change.

**Item 8.** `gui/web/commands.py`: `Command(id, title, menu, shortcut)`. Menus File (New project…, Open project…,
Import case…, Export project…, Settings…, Quit), View (the four suites, Toggle the bottom panel, Changed values,
Problems, Reset layout), Help (Glossary, About). Shortcuts: palette `Ctrl+K` and `F1`; suites `Alt+Shift+1` to `4`;
bottom panel `Alt+Shift+J`; changed values `Alt+Shift+D`; problems `Alt+Shift+P`; settings `Ctrl+,`. Quit stops the
server as SIGTERM does. Frame controls: `menu-file`, `menu-view`, `menu-help`, `project-name`, `changed-count`,
`palette-open`, `suite-molecular`, `suite-continuum`, `suite-study`, `suite-analysis`, `rail`, `rail-fold`,
`queue-status`, `panel-toggle`, `problems-count`. Screens: `molecular`, `continuum`, `study`, `analysis` at `/<suite>`
(`suite-body`, its tools listed as not built yet, no working control); `changes` at `/study?panel=changes`
(`changes-list`); `problems` at `/study?panel=problems` (`problems-list`); `palette` at `/molecular?palette=1`
(`palette-input`, `palette-list`); `settings` at `/molecular?dialog=settings` (`settings-theme`, `settings-density`,
`settings-spacing`, `settings-background`, `theme-colours`, `theme-duplicate`); `st-charge` stays; `/` redirects to
the current suite.

**Item 10.** `core/paths.py:config_root()`: `NANOPNP_CONFIG`, else `%APPDATA%\nanopnp`, `~/Library/Application
Support/nanopnp`, or `$XDG_CONFIG_HOME/nanopnp` (`~/.config/nanopnp`). `gui/web/settings.py`: `Settings(theme="system",
density="medium", spacing="default", viewer_background="near-black")` at `workbench.yaml`. `gui/web/theme.py`:
`Theme(name, base, colours)` at `themes/<name>.yaml` (`nanopnp/workbench-theme/v0.6`); `shipped()` parses the two
built-ins from `pages.TOKENS`, the wheel's copy or the checkout's; `css(theme)` writes the overrides on `:root[data-user-theme]`. Spacing `tight` is
`data-spacing="tight"`, two thirds of `--gap` and `--pad`, added to `tokens.css`. `states.py`: each state but `empty`
writes its fixture, imports it, walks the study to `charge` and records the queue entry.

### Work items

- [ ] 1. `io/project.py`; `io/store.py` (`runs`, `upto`, `stale`, `remove`); `pipeline/run.py:run_document`'s call
  (D1, D4). Done when rows 5 and 6 pass. **Executor:** main.
- [ ] 2. `core/stages.py:ContributesDeviations`; `pipeline/run.py:_contributed`;
  `validation/modularity.py:stage_conformance` reads the three optional members (D4). Done when row 4 passes.
  **Executor:** main.
- [ ] 3. `api/project.py`, `io/defaults.py:changes`, `core/errors.py`, `nanopnp/__init__.py` (D1 to D3). Done when rows
  1 to 3 pass. **Executor:** main.
- [ ] 4. Compaction checkpoint. **Executor:** main.
- [ ] 5. The `cli/` split (D5). Done when `test_cli.py`, `test_sweep_cli.py` and `test_layering.py` pass and the review
  finds the bounds held. **Executor:** `general-purpose` on Sonnet.
- [ ] 6. `cli/workbench.py`: `gui [<project>]`, `project new|import|export`, `store prune [--remove]`, `--env`'s
  `config` (D5). Done when row 7 passes. **Executor:** main.
- [ ] 7. Compaction checkpoint. **Executor:** main.
- [ ] 8. `gui/web/commands.py`, `frame.py`, `queue.py`, `screens.py`, `pages.py`, `assets/frame.js` (D6). Done when
  row 8 (a) to (d) passes. **Executor:** main.
- [ ] 9. The changed list, its resets and the problems list (D3, D6). Done when row 8 (i) passes.
  **Executor:** main.
- [ ] 10. `core/paths.py:config_root`, `gui/web/settings.py`, `theme.py`, the settings overlay, `tokens.css`'s spacing,
  `states.py` as projects, `server.py` (D6). Done when row 8 passes whole. **Executor:** main.
- [ ] 11. Compaction checkpoint. **Executor:** main.
- [ ] 12. `/np-gui render shell` and `/np-gui review`; fix what they find. Done when the review says so. **Executor:** main.
- [ ] 13. `CHANGELOG.md` (`nanopnp gui` takes a project, not a case); the brief's amendments; Outcome notes. Done when the strict documentation build passes. **Executor:** main.
- [ ] 14. `.claude/hooks/gate.sh run`: VER-62's walks unmoved. **Executor:** main.

### Verification

In `tests/tier1/`: rows 1 to 3 `test_project.py`, 4 `test_stage_conformance.py`, 5 and 6 `test_store.py`, 7
`test_cli.py`, 8 `test_gui_screens.py`; run by `uv run pytest <file> -k <word>`.

| Test | Tier | Identifiers | Oracle and tolerance | `-k` |
|---|---|---|---|---|
| 1 `test_fr32_a_case_imported_into_a_project_keys_as_it_did` | 1 | FR-32, VER-62 | The charged tube and the quick-start, walked to `charge` into the project's store, imported, walked again: every stage but `case` has its original hash and is served from the store; the tube writes both models and two inputs | `imported` |
| 2 `test_fr32_an_exported_project_reads_back` | 1 | FR-32, FR-25 | The imported tube with one run: the copy opens with the same index; `read_run` gives the original manifest hash; each copied file is byte-identical; no `store/`; with `store=True` a walk of the copy is served whole from its store | `exported` |
| 3 `test_fr34_the_changed_list_holds_every_value_away_from_its_default_and_every_override` | 1 | FR-34, FR-25 | A continuum model with `physics.flow: false`, `numerics.mesh.size_scale: 2` and a default written out; a study overriding the bias: exactly three changes with kind, value and default, the bias with the model's value; each reset removes its change and the study loads | `changed` |
| 4 `test_ver64_each_optional_member_a_stage_defines_has_its_protocols_signature` | 1 | VER-64 | `charge` and `mesh` define `deviations(self, inputs)` and are `ContributesDeviations`; `solve` is `SolveReporting`; `mesh` is `Forecastable`; no other stage is any; a test stage with `deviations(self)` does not conform | `optional` |
| 5 `test_rev32_the_store_lists_and_removes_only_entries_of_an_older_schema` | 1 | FR-27 | A walked quick-start and hand-written `nanopnp/case/v0.5`, `nanopnp/fields/v0.4`, `nanopnp/fields/v0.7` and `nanopnp/stage/x/v1` entries: `stale()` lists exactly the first two; `remove` deletes only them; the walk again is served whole from the store | `older` |
| 6 `test_ver62_a_store_given_no_runs_root_writes_run_directories_where_it_did` | 1 | VER-62 | `run_directory("a", d)` and `run_directory("a", d, upto="mesh")` equal today's paths; with `runs=` they are `runs/a/<short>` and `runs/a/upto-mesh-<short>` | `runs_root` |
| 7 `test_ver78_nanopnp_gui_opens_or_creates_a_project` | 1 | VER-78 | `nanopnp gui --no-browser <empty folder>` prints the ready line and writes `nanopnp-project.yaml` naming the folder | `creates` |
| 8 VER-78's tests over the new `SCREENS` and the four states | 1 | VER-78, QR-16 | (a) to (h) over each frame screen in each state; (i) in `refused` the problems list holds the refusal, and choosing it opens `/continuum`; (j) a theme chosen in the settings sets `data-theme` on the root and holds after a reload; each test server's `NANOPNP_CONFIG` is a temporary folder | `ver78` |

### Out of scope

- The suites' tools, WP5.09 to WP5.12; a queued build or study and its convergence, WP5.11.
- The comparison's schema and difference field, WP5.12; the guided route and Qt's removal, WP5.13.
- Importing a case that names models: later, if asked.

### Open questions

None. AI1 was ruled at this plan.

# WP5.15 — The frame on Quasar's components

**Status: in progress; items 1 to 7 done.** Planned 10 November 2026 on `main` (`ce43a48`). It inherits §8.2.34 AJ1, AJ2, AJ6
to AJ9 and this plan's, §8.2.38 AN1 to AN8.

This plan belongs to [the Phase 5 plan](phase-5-workbench.md). `SPECIFICATION.md` governs. An identifier here points to
a clause and never restates it.

## In brief

**What changes.** The frame is rebuilt from the toolkit's ready-made parts: a project tree headed by the project's
name, an icon per suite, and colours every control takes from the theme. Changing suite no longer reloads the page,
and a molecule drawn once stays drawn. Five suites show in two groups, those that build models and those that use
them; Physics stays empty until its package. The palette becomes one box that suggests as you type, finds a command
by its keywords, and greys out one that cannot run, saying why. The settings become a page with searchable sections,
a filter for changed values, and your settings or the project's. The changed values become one dense table with
units. The store gains a size cap and two clean-up buttons.

**Cost.** About ten sessions, 13 to 21 agent hours and 14 of your touches; the first frame package took 7 to 11 hours.
No new library, and nothing is asked of the internet.

**What could go wrong.** A clean-up could delete a result a run needs or is reading, in any program; tests check that a
removed result is rebuilt, that a half-removed one is never read, that the first button keeps every run's results,
and that a run elsewhere stops a clean-up. A setting could reach the page but not its file or the palette; one test
walks every setting through each. A suite change could still rebuild the molecule; a test counts its builds. An
accessibility miss is caught by rendering and reviewing every screen.

**Your call.** None left: you ruled the settings, the clean-up and its lock, and the shortcuts.

## Execution brief

**Scope.** The phase entry's WP5.15, AN3's settings and AN5's clean-up: REV-203's frame part, REV-204, REV-207, REV-208,
REV-210 to REV-214. **Depends on:** WP5.14 (merged). **Requirements:** FR-27, FR-31, FR-34, FR-35; QR-16; VER-61,
VER-62, VER-72, VER-78. **Constrained by:** AJ1 (hand-written only where no component serves), AN2, ADR-004 (no request
leaves the origin), CON-07 (no build step). **Implementing session:** Opus, high effort; sub-agents Sonnet, high.
Tag `v0.6.0-alpha.15`.

**Amended when it lands:** VER-78 (five suites, the settings page, (l), (m)); §5.3.2's NOTE on older entries; §5.3.5's
NOTE (a project's settings); the matrix rows of FR-27, FR-31, FR-34 and FR-35.

### Decisions

Eleven: the phase entry's six parts, and AN5's library step.

| Decision | Choice | Why/source |
|---|---|---|
| D1 The layout | `gui/web/frame.py:frame` builds Quasar's layout: `ui.header`; one `ui.left_drawer` holding the activity bar and the rail, `mini` while the rail folds; `ui.footer` holding the bottom panel and the status line; a main column with `ui.sub_pages` and the view region. Hand-written separators resize the drawer and the panel, saved on release in px per suite. The tokens reach Quasar's colour variables | AJ1, ruled by the author; decided by the plan for one drawer and the separators |
| D2 Routes and views | One page at `/` and `/{_:path}` builds the frame once; `ui.sub_pages` routes the five suites, `/study/charge` and `/settings`. The frame owns the view region: one Mol* host, built when a route first shows the molecule, hidden, never rebuilt | AJ1, ruled by the author; decided by the plan for views the frame owns |
| D3 Five suites | `screens.SUITES` holds five, each with its group and icon; `io/project.py:Suite` gains `physics`, whose items open in Physics; Alt+Shift+1 to 5 follow the bar, and the changelog names the move | AJ2, AJ10, AN7, ruled by the author |
| D4 Rail and title | `ui.tree` with the project's name as its root, then the kinds and their items, each opening its suite; the page title is the name; with no project, *New*, *Open* and the recent projects (`core/paths.py`) | AJ7, REV-210, ruled by the author |
| D5 Palette | `gui/web/palette.py:Palette` wraps Quasar's searchable select: empty until a word is typed, matched on title and keywords, a command that cannot run disabled with its reason, a command per setting | REV-208, REV-211, AJ9, ruled by the author; decided by the plan for the component |
| D6 Settings | One registry, `gui/web/settings.py:SETTINGS`; the user's values in `workbench.yaml`, a project's under `settings:` in its file, the project's winning where the scope allows; the page `/settings` with search and sections, *User* or *Project*, *Modified only*, each value's mark and reset | AJ9, AN2, AN3, ruled by the author; decided by the plan for keeping today's keys |
| D7 Store clean-up | `io/store.py:Store` marks each read, measures itself and evicts the least recently read entries outside a kept set, each renamed away before it is deleted, as `remove` then does. `api/project.py:Project` keeps what a run record, a sweep member or the shown walk names, with their inputs, cleans the unused or all, and applies the cap, unused only, after its walks. A walk holds the store's lock, which a clean-up checks | AN5, AN6, ruled by the author; decided by the plan for the cap and the rename |
| D8 Changed table | A dense `ui.table`: a group row per item, then mark, field, value, default, unit, reset; numbers in the user's figures and style; units from `io/variables.py:field_unit`; a row opens its suite at `?field=<path>` | AJ7, REV-204, REV-214, ruled by the author |
| D9 Accessibility and guards | Landmarks, named `nav` regions, a skip link, headings, live regions for the three counts; dialogs built once; Reset, *Reset layout* and *Quit* ask while the guard is on; About and the Glossary as dialogs | REV-203, REV-204, REV-207, REV-210, ruled by the author; decided by the plan for the means |
| D10 Render set | `server.main --project` boots through `states.boot_project`; `render_shell.py` caches a 2WCD project from example 07 and adds REV-210's states; `shoot.cjs` takes clicks | AJ8, REV-210, ruled by the author; decided by the plan for the cache |
| D11 `impeccable` | `np-gui review` adds the plugin's critique; a session reads its quality floor before building a screen; `design_md.py` writes `DESIGN.md` from `tokens.css`, marked as derived; a host without the plugin skips them | AJ6, ruled by the author |

### Grounding

**D1.**
- `frame.py:frame` builds a `div.frame` with two `ui.splitter`s sized in percent and hand-made bars; `frame.css`
  recolours Quasar by selector. `_Frame.save_layout` writes the project file at every splitter step (REV-207).
- Two `ui.left_drawer`s render overlapping, and the page is padded for the last one only: the layout takes one drawer
  per side (probed, NiceGUI 3.18.0). QDrawer has `width`, `mini`, `mini-width` and the classes `q-mini-drawer-hide` and
  `q-mini-drawer-only`.
- Neither QDrawer nor QSplitter resizes by keys; QSplitter's separator has no role and no tabindex (probed).
- `ui.footer` is sized by its content and reserved by the layout. The layout renders `header`, `aside`, `main` and
  `footer` (probed).
- `elements/colors.js` sets `--q-primary` and its siblings on `body` verbatim, and `var(--accent)` follows a later
  change of `--accent` (probed). `ui.dark_mode` sets `body--dark`.
- `io/project.py:SuiteLayout` is strict: `rail_percent`, `bottom_percent`, `rail_folded`, `bottom_folded`.
- `theme.shipped()` parses `tokens.css`, and `theme.user_themes()` reads every theme file, at each call (REV-207).
- NiceGUI serves Material Icons and Symbols from its own `static/fonts.css`; `sym_o_<name>` is Symbols Outlined; no
  request leaves the origin (probed).

**D2.**
- `pages.install` registers `/api/structure`, `/api/map` and the static files, then one `@ui.page` per suite and
  `/charge`; each page builds the whole frame.
- With `@ui.page('/')` and `@ui.page('/{_:path}')`, a path change rebuilds only the `SubPages` element; an element
  outside it keeps its DOM node, Back swaps the sub-page, and a flat key `'/study/charge'` routes (probed). A builder
  reads a query parameter by name. A sub-page's timers and element handlers go with it.
- `functions/navigate.py:to` hands a path to `sub_pages_router._handle_navigate` when the page holds a `SubPages`.
  `context.client.sub_pages_router.on_path_changed` reports each change.
- `assets/bridge.js:nano.init` creates the Mol* viewer in `#mol` and sets `data-screen-ready` once drawn.
- `ui.skip_link` needs a stable target, outside the sub-pages.

**D3.**
- `screens.SUITES` holds four; Continuum lists *Physics defaults*. `io/project.py:Suite` and `SUITES` hold four, and
  `ITEM_SUITES["physics"]` is `continuum`. Their readers: `api/project.py` (`save_layout`, `problems`) and
  `gui/web/{screens,pages,frame}.py`.
- `commands.COMMANDS` binds Alt+Shift+1 to 4; a user's rebinding is keyed by the command's id.

**D4.**
- `_Frame.rail` lists buttons per kind; the name is a title-bar label, `data-control=project-name`.
- `core/paths.py:remember_project` overwrites `last-project` with one path; no list exists. Callers: `gui/web/frame.py`
  and `cli/workbench.py`, whose `_project_to_open` opens `last_project()` when no folder is given.
- `ui.tree(nodes, node_key=, label_key=, children_key=, on_select=)` renders `role=tree` with a roving tabindex.
  `ui.page_title` can be set after the page loads.

**D5.**
- `_Frame.fill_palette` and `first_match` filter by title twice (REV-207), and an empty input lists every command.
- `elements/select.js:findFilteredOptions` filters by label alone, and an empty input shows every option. QSelect
  renders `role=combobox`, options carry `aria-disabled`, and an option may set `disable`.
- An `Element` subclass names its Vue file with `component=`, relative to its module.

**D6.**
- `settings.py:Settings` is a strict model of `theme`, `density`, `spacing`, `viewer_background` and `keys`, read from
  `config_root()/workbench.yaml`; a file that fails validation is ignored whole.
- `overlay.Overlay` is one dialog of stacked sections. `theme.appearance` sets the root's attributes before the first
  paint.
- `io/project.py:ProjectFile` is strict and holds no settings; `io` imports no `gui` (VER-61).
- `tokens.css` honours `prefers-reduced-motion` and has no `data-motion` selector.

**D7.**
- An entry is `artefacts/<schema>/<digest[:2]>/<digest>/`: its payload and `meta.json`. `contains` is true when
  `meta.json` exists; `get` returns None without it, does not check the payload, and raises `StoreError` on a corrupt
  `meta.json`. Nothing records a read or a size.
- `put` stages in a hidden `.<digest>.<pid>.<token>` and renames it in; `_publish` clears a directory without
  `meta.json`; `_sweep_staging` clears hidden directories older than `STALE_STAGING_SECONDS`.
- `Store.remove` runs `rmtree` in place, so `meta.json` can outlive a payload mid-delete.
- No lock exists: `gui/solver.py` and `api/sweep.py`'s workers write the same root. `filelock` is a dev dependency
  only; the standard library has `fcntl.flock` on POSIX and `msvcrt.locking` on Windows.
- Every walk enters `pipeline/run.py:_walk` through `run_document`: `Session.run`, `states.boot_project` and each
  sweep member (`api/sweep.py`'s `run_point`). `keyed_walk`, the forecast's, and `stored_upstream` key through
  `_keying_walk`, whose `_Walk.stored` calls `contains` or `get`.
- `run.json` holds `artefacts: {stage: {schema, hash}}`; `pipeline/run.py:open_run` leaves out what the store lacks.
  `sweep/run.py:MemberResult.row` names a member's `directory` and `solution`. `Project.session` gives
  `Store(<project>/store, runs=<project>/runs, sweeps=<project>/sweeps)`.
- `states.boot_project` walks to the charge with `session.write = False`: the walk the frame shows writes no run
  record, and `Workbench.stages` holds stage names, not hashes.
- A stored record's `inputs` names the upstream entries it was made from: the charge's `protonation` and
  `charge_grid` (auxiliary schemas no run record names), a mesh's `region`. `charge/stage.py` reads the grid back,
  and a field's frame check raises `FileNotFoundError` when the region is gone.
- `Path.glob("*/*/*/meta.json")` matches hidden directories (probed, Python 3.14): `put`'s staging directory holds a
  `meta.json` before its rename, and `stale()` already lists one.
- `cli/workbench.py` and the frame's `switch` call `remember_project`; `_project_to_open` reads no setting.
- `tests/tier1/test_store.py:_put` stores a 1000-byte artefact with no mesh.

**D8.**
- `_Frame.changes_list` writes a 48 px row per change; `listed_changes` skips an item that does not load.
- `io/defaults.py:Change` has `path`, `kind`, `owner`, `value`, `default` (None where none) and `model`.
- `io/variables.py:field_unit(path)` returns a numeric field's unit and raises `KeyError` for any other leaf.
- QTable has no grouping; a `body` slot renders a group row; `dense` tightens its rows.

**D9.**
- The frame has no landmark, heading or live region; the activity bar is text; each dialog is created per use and never
  deleted; an empty path reads as the server's folder (REV-203, REV-207, REV-210).
- `_Frame.actions["quit"]` sends SIGTERM at once; `layout-reset` and `reset` act at once.
- The design document's *Glossary* has 26 terms; `frame.GLOSSARY` has 5.

**D10.**
- `server.main` takes a case or `--state`; `cli/workbench.py` takes a project folder, which walks nothing.
- `render_shell.py` starts one server per `STATES` entry and caches nothing. `shoot.cjs` reads `viewport`, `scheme`,
  `via`, `url`, `ready`, `wait_ms` and `expand`.
- `examples/07-pdb-to-charged-run/2wcd.case.yaml` reads `2wcd-prepared.pdb`, which `examples/06-pdb-to-mesh/prepare.py`
  writes from the shipped `tests/data/structures/2wcd.pdb.gz`; its walk takes minutes on one core.

**D11.**
- `np-gui/review.md` starts the `gui-reviewer` alone. No root `DESIGN.md` exists; the plugin reads one there, and its
  `reference/craft-floor.md` before an edit.

### Implementation details

**Item 1.**
- `READ_MARK = "last-read"`. `Store._mark_read(entry)` runs `(entry / READ_MARK).touch()` and ignores `OSError`; `get`
  and `contains` call it on a hit unless `mark=False`, which `keyed_walk`'s `_Walk.stored` passes. An entry's last
  read is the marker's mtime, else `meta.json`'s.
- `StoreUsage(total_bytes, entries, kept_bytes, kept_entries)`, a frozen dataclass; `Store.usage(keep=frozenset())`.
- `Store.evict(*, keep: frozenset[str], to_bytes: int | None = None) -> tuple[StaleEntry, ...]` takes the entries with
  a `meta.json` and no leading `.`, as `usage` and `stale` then do, oldest read first (ties by path), outside `keep`,
  and removes them until the total is at most `to_bytes`, or all when None. `StaleEntry`
  documents any entry.
- `_discard(entry)` renames it to `entry.parent / f".{entry.name}.evict.{os.getpid()}.{token}"`, then runs
  `rmtree`; `remove` calls it.
- Locks, in `<root>/.locks/` by `fcntl.flock` or `msvcrt.locking`: `Store.using()`, held by `_walk`, locks its own
  `walk-<pid>-<token>` under a brief lock on `gate` and deletes it on exit; `Store.cleaning()`, held by `evict` and
  `remove`, holds `gate`, deletes each `walk-*` it can lock, and on one it cannot raises `StoreBusy`: "A run is in
  progress in another program; nothing was removed."
- `Project.kept_artefacts() -> frozenset[str]`: the `artefacts` hashes of every `run.json` under `runs/` and `sweeps/`,
  and each member record's `solution`, closed over each kept entry's `meta.json` `inputs`. `Project.store_usage()`.
  `Project.clean_store(*, everything=False, cap_bytes=None, holding=frozenset())`: `holding` joins the kept set;
  `everything` evicts with an empty `keep`. `cap_bytes` is `store_cap_gb × 10⁹`.
- `Workbench` gains `held: frozenset[str]`, its walk's hashes; the frame calls
  `clean_store(cap_bytes=..., holding=workbench.held)` after each walk it starts and on opening a project, skipped on
  `StoreBusy`; the two buttons ask first, with the bytes each frees, and report it.
- The test fills a store with `_put`, setting each marker's mtime with `os.utime`; for (6) it imports the quickstart
  case into a project and runs its study `upto="mesh"`, once recorded and once `write=False` as `held`; for (8) a
  `subprocess` child enters `using()` and waits on its stdin.

**Item 2.**
- `Setting`, frozen: `id`, `section`, `title`, `description`, `keywords`, `scope` (`user`, `project`, `both`),
  `default`, `adapter: TypeAdapter[Any]`, `choices: Mapping[str, str] | None`, `applies` (`at once`, `next run`,
  `next start`). `register(setting)` refuses a taken id. `search(text)`: every word in the title, description or
  keywords. `rows(section)` feeds the page.
- Sections: `appearance` *Appearance and accessibility*, `keyboard` *Keyboard and editing guards*, `runs` *Runs and
  storage*, `numbers` *Units and numbers*.
- The settings (id, section, scope, default, applies): `theme`, appearance, user, `system`, at once; `density`,
  `medium`; `spacing`, `default`; `viewer_background`, `near-black`; `reduced_motion` (`system`, `on`, `off`), `system`;
  `keys`, keyboard, `{}`; `confirm`, keyboard, true; `recent_projects`, runs, 8 (1 to 30); `open_last_project`, runs,
  true, next start; `store_cap_gb`, runs, both, none (0.5 to 10 000), next run; `significant_figures`, numbers, both,
  4 (2 to 10); `number_style` (`prefixes`, `powers`), numbers, both, `prefixes`.
- The user's file is `{id: value}`, each entry validated alone, an unknown or invalid one dropped with a warning.
  `ProjectFile.settings: dict[str, JsonValue]`, `Project.settings` and `Project.save_setting(id, value)` (None removes
  it).
- `SuiteLayout`: `rail_px` 240 (160 to 480), `bottom_px` 220 (120 to 560) and the folds; a `mode="before"` validator
  drops `rail_percent` and `bottom_percent`.
- `core/paths.py`: `recent-projects`, one absolute path a line, newest first, at most 30; `remember_project` prepends
  and deduplicates; `recent_projects(limit)` skips a missing folder; `last_project()` is its first, else the old
  `last-project` file's path. `cli/workbench.py:_project_to_open` returns None when `open_last_project` is off.
- The user's themes (`theme.user_themes()`) list under `theme`, outside the registry.
- `tokens.css`: the reduced-motion `@media` block applies to `:root:not([data-motion="full"])`, and
  `:root[data-motion="reduce"]` takes its values; `theme.appearance` sets `data-motion` `reduce` for `on`, `full`
  for `off`.

**Item 3.**
- `Command` gains `keywords: tuple[str, ...] = ()` and `needs_project: bool = False`, true for `project-import` and
  `project-export`; without a project, `unavailable` gives such a command "Open or create a project first".
- `screens.SUITES`: *Build* holds `molecular` (`sym_o_hub`), `continuum` (`sym_o_grid_on`) and `physics`
  (`sym_o_function`); *Use* `study` (`sym_o_science`) and `analysis` (`sym_o_monitoring`). Chords Alt+Shift+1
  to 5, in order; in `chords`, a user's binding wins, and the default it takes goes unbound.
- Keywords: `settings` preferences, options; `changes` modified, defaults; `problems` errors, refused; `panel-toggle`
  queue, log; `layout-reset` panels, sizes; `glossary` terms; each `suite-*` its tools' names.
- `setting_commands()` yields `Command(f"setting-{s.id}", f"Settings: {s.title}", "file", keywords=s.keywords)`, which
  opens `/settings?setting=<id>`.
- Continuum drops *Physics defaults*; Physics lists *Equations*, *Electrolyte*, *Conditions* and *Exposed values*.

**Item 4.**
- `ui.colors(primary="var(--accent)", secondary="var(--muted)", accent="var(--accent)", dark="var(--panel)",
  dark_page="var(--bg)", positive="var(--ok)", negative="var(--err)", info="var(--accent)", warning="var(--warn)")`.
  `ui.dark_mode` is None for `system`, else the theme's base, set wherever `theme.appearance` runs.
- The activity bar is 88 px: each suite a 24 px icon over its name, in two `role=group` blocks. The
  drawer's width is the bar plus `rail_px`; its `mini-width` the bar plus 32 px.
- A separator is `role=separator`, `tabindex=0`, with `aria-orientation`, `aria-valuemin`, `aria-valuemax`,
  `aria-valuenow` and `aria-label`. `frame.js` moves it by pointer, arrow keys (16 px), Home and End,
  emitting `resize` at most every 50 ms (the drawer's `width` or the panel's height) and `resized` on release (saving
  the layout).
- `theme.shipped` takes `functools.cache`; `user_themes` is cached on its folder's newest mtime, and `save` clears it.
  `frame.css` loses every rule that recolours Quasar, and `workbench.css` its `@layer theme` block.

**Item 5.**
- `/api/*` and the static files stay registered first. `ROUTES: dict[str, Route]` holds each suite's `/<id>`,
  `/study/charge` and `/settings`; `Route(suite, view)`, `view` `"molecule"` or None. Both pages call one builder,
  reading `panel`, `palette` and `dialog`; `/` opens the current suite.
- The view region holds `ui.element("div").props("id=mol data-control=molecule")`. On a path change the frame shows it
  where `view == "molecule"` and calls `nano.init` once; `nano.builds` counts builds.
- `/study/charge` keeps `pages.charge`'s strip and map; `screens`' `st-charge` takes the path. Each change sets
  `data-screen-ready` to 0; the built sub-page sets 1.

**Item 7.** Folded, the rail shows the open item's initial and its unfold button. The diamond is `aria-hidden` beside
the word "changed" or "override". *Quit* names the queue's running entries. The New, Open, Import and Export
dialogs list recent projects and refuse an empty field. `glossary.py` holds the design document's *Glossary* rows.

**Item 8.** `palette.js` wraps `<q-select use-input hide-dropdown-icon input-debounce="0">`. Its `@filter` splits the
text into lower-case words: none lists nothing; else an option shows when each word is in its label or keywords.
The `option` slot shows the title, the chord and, when disabled, the reason; `no-option` says "No command matches".
`?palette=<text>` opens it with the text typed.

**Item 10.** A missing default reads "not set"; an item that does not load has one row, "not counted: it does not
load", leading to *Problems*.

**Item 12.** `render_shell.py` keeps, in `<r>`'s parent, `cache/2wcd-<12 hex of sha256(case, structure)>/`: the prepared
PDB, the case, and a project with the case imported, which it starts with `--project`. A second config folder holds
`workbench.yaml` (compact, tight, a user theme) and the theme file. `shoot.cjs` clicks each selector of `entry.click`
before its wait.

### Work items

- [x] 65d133d 1. `io/store.py`, `api/project.py`, `pipeline/run.py`, §5.3.2's NOTE (D7); done when `tests/tier1/test_store.py`
  passes with VER-62 unmoved. **Executor:** main
- [x] 97bf4e2 2. `gui/web/settings.py`, `io/project.py`, `core/paths.py`, `docs/design/tokens.css`, §5.3.5's NOTE (D3, D4, D6);
  done when `tests/tier1/test_gui_settings.py` passes. **Executor:** main
  > **Outcome — two parts move.** `Command.keywords` and `setting_commands()` land here, which the test needs;
  > `SuiteLayout`'s pixels land with the frame in item 4, which is their one reader.
- [x] d74b9b3 3. `gui/web/commands.py`, `gui/web/screens.py` (D3, D5); done when the code and review say so. **Executor:**
  general-purpose on Sonnet
- [x] 5d0f934 4. `gui/web/frame.py`, `gui/web/theme.py`, `assets/frame.js`, `assets/frame.css`, `assets/workbench.css` (D1);
  done when VER-78 (a) to (d) pass. **Executor:** main
- [x] e70c885 5. `gui/web/pages.py`, `assets/bridge.js`, VER-78's text (D2); done when VER-78 (a) to (d), (i) and (m) pass.
  **Executor:** main
- [x] 6. Compaction checkpoint. **Executor:** main
- [x] 7b052a8 7. `gui/web/frame.py`, `gui/web/glossary.py` (D4, D9); done when the code and review say so. **Executor:** main
- [ ] 8. `gui/web/palette.py`, `assets/palette.js` (D5); done when the code and review say so. **Executor:** main
- [ ] 9. `gui/web/settings_page.py` with the store's section, `overlay.py` removed (D6, D7); done when VER-78 (j), (k)
  and (l) pass. **Executor:** main
- [ ] 10. `gui/web/frame.py`'s changed table (D8); done when VER-78 (a) passes on `changes`. **Executor:** main
- [ ] 11. Compaction checkpoint. **Executor:** main
- [ ] 12. `gui/web/server.py`, `.claude/scripts/gui/render_shell.py`, `shoot.cjs` (D10); done when `/np-gui render
  shell` renders every state, 2WCD from its cache the second time. **Executor:** general-purpose on Sonnet
- [ ] 13. `.claude/skills/np-gui/`, `.claude/scripts/gui/design_md.py`, `DESIGN.md` (D11); done when the code and review
  say so. **Executor:** general-purpose on Sonnet
- [ ] 14. `/np-gui render shell` and `review`, each finding fixed or a `REV-nn` row; REV-203's frame part, REV-204,
  REV-207, REV-208 and REV-210 to REV-214 `fixed`; the matrix rows; `current.md`. **Executor:** main

### Verification

| Test | Tier | Identifiers | Oracle and tolerance (exact) | Command |
|---|---|---|---|---|
| `tests/tier1/test_store.py::test_fr27_a_cleaned_store_rebuilds_what_it_removed_and_never_reads_half_an_entry` | 1 | FR-27; AN5, AN6 | One assertion each: (1) the least recently read goes first; (2) a kept digest survives `to_bytes=0`; (3) an evicted key misses, and `get_or_compute` rebuilds its digest and payload bytes; (4) an entry without `meta.json` is a miss; (5) a young staging directory survives; (6) a run's artefacts, their `inputs` and a held walk's survive the unused clean, go with `everything`, and a re-run rebuilds them; (7) a hidden directory is never evicted; (8) a child process inside `using()` makes a clean-up raise `StoreBusy`, removing nothing; (9) `keyed_walk` moves no read mark | `uv run pytest tests/tier1/test_store.py` |
| `tests/tier1/test_gui_settings.py::test_ver78_every_declared_setting_reaches_its_search_its_command_and_its_file` | 1 | VER-78 (l) | Per setting, one assertion each: its default validates; its section's page rows list it; each keyword finds it; one palette command opens it; a value saved in its scope reads back from that file; an invalid entry is dropped alone | `uv run pytest tests/tier1/test_gui_settings.py` |
| `tests/tier1/test_gui_screens.py` | 1 | VER-78 (a) to (d), (i) to (k) | The registry's screens in the four states; (j) and (k) on `/settings` | `NANOPNP_REQUIRE_BROWSER=1 uv run pytest tests/tier1/test_gui_screens.py` |
| the same file | 1 | VER-78 (l), (m) | (l): "compact" lists *Density*, the palette lists its command, *Compact* sets `data-density` and writes `workbench.yaml`; a project-scope value writes the project file. (m): `/study/charge`, `/study`, `/study/charge` keeps a window marker, and `nano.builds` is 1 | as above |

### Out of scope

- The compute settings: WP5.19 (AN1, AN4). Rebuilding a cleaned run's solution on viewing: WP5.20 (AN5).
- The suites' tools, their *Modified only* filters and the field a changed row opens: WP5.16 to WP5.19.
- The keyboard pass over the canvases: WP5.21. A command-line clean of current results.

### Open questions

None.

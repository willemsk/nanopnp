# Code review 052: WP5.15, the frame on Quasar's components

2026-11-11 · PR #181, branch `ccr-4b90fcd6-fjrv03`, head `be6eae0` on base `b9d9b99` · scope: the PR's 53 files. The
code and tests were read in full with each touched function: `io/store.py` (`get`, `put`, `contains`, `remove`,
`evict`, `usage`, `inputs_closure`, `using`, `cleaning` and the lock helpers), `core/paths.py`, `api/project.py`
(`kept_artefacts`, `store_usage`, `clean_store`, `save_setting`, `export`), `io/project.py`, `pipeline/run.py`
(`_Walk.stored`, `run_document`, `keyed_walk`), `cli/workbench.py`, and every module of `gui/web/` with its
assets (`frame.py`, `pages.py`, `settings.py`, `settings_page.py`, `states.py`, `server.py`, `commands.py`,
`palette.py`, `numbers.py`, `theme.py`, `screens.py`, `frame.js`, `palette.js`, `bridge.js`). Every caller of a
changed name was read (`Store.get`, `Store.contains`, `Store.remove`, `cap_store`, `recent_projects`,
`field_unit`), as were the sweep's warm start (`api/sweep.py:_parent_artefact`), the stages' own store reads,
`.claude/scripts/gui/{render_shell.py,design_md.py,shoot.cjs}`, §5.3.2's NOTE, §5.3.5's NOTEs and VER-78 (l, m) ·
level: xhigh, with `--fix` · status: completed.

Static review (`/np-ship`, `/code-review xhigh --fix`). No gate, benchmark, sweep or nightly walk ran; `/np-ship`
gates the fixes. Ruff and mypy ran on the edited modules. These tests ran on the fixed tree and pass:
`tests/tier1/test_store.py`, `test_gui_settings.py`, `test_artefact_hashing.py`, `test_project.py`,
`test_stages.py`, `test_cli.py` and `test_gui_screens.py` (in headless Chromium).

Probed:

- With `fcntl.flock` raising `ENOSYS`, as on a Lustre client mounted without `flock`, `Store.using()` raised
  from the first line of every walk at the head. After the fix, the walk runs and logs a warning, and
  `Store.evict` raises `StoreError` and removes nothing.
- `numbers.shown(999.96, "nanometer", figures=4, style="prefixes")` gave `1000 nm` and `shown(0.99996, …)` gave
  `1000 pm`. After the fix they give `1 µm` and `1 nm`.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | High | `io/store.py:Store.using`, `_lock` | Every walk now takes the store's lock, and `_lock` catches only `BlockingIOError`. Two cases make every walk raise `OSError` before its first stage. A filesystem with no `flock` raises `ENOSYS`: a Lustre client mounted without `flock`, which is the default. An NFS mount without `lockd` raises `ENOLCK`. FR-24's job arrays run on such filesystems (§5.3.2, *workspace locality*). The second case is a read-only store whose `.locks/` already exists: `_lock_folder`'s `mkdir(exist_ok=True)` succeeds, and opening the gate raises `PermissionError`. The NOTE says that such a store takes no lock | Fixed: `_hold_walk` takes the gate and the walk's lock. Any `OSError` there means no lock, logged as a warning, and the walk runs. `cleaning()` raises `StoreError`, removing nothing, when the gate cannot be taken. §5.3.2's NOTE says so |
| 2 | Medium | `gui/web/states.py:cap_store`; `settings_page.py:_clean` | Both catch only `StoreBusy`. Several errors escape: a `StoreError`, an `OSError` from `_discard`'s rename (Windows refuses to rename a directory that holds an open file), and finding 1's refusal. From `server._boot`, one ends the server's start. From `Frame.switch`, it escapes after the bench has already switched. From the page, the click fails without a word | Fixed: `cap_store` catches `StoreError` and `OSError`, logs a warning and removes nothing more. `_clean` notifies them |
| 3 | Medium | `io/store.py:_remove` | The first entry whose rename fails aborts the clean-up halfway, and every entry after it stays. `evict` returned the entries it had chosen, not those it removed | Fixed: a rename that fails is logged and that entry is skipped. `_remove` returns the entries removed; `evict` returns them and `remove` counts them |
| 4 | Medium | `io/store.py:Store.using`, `Store.cleaning` (Windows) | The walk's lock file is unlinked outside the gate. On Windows, a file another process holds open cannot be deleted. A walk that ends while a clean-up is probing its file raises `PermissionError` from `using()`'s `finally`, and the finished walk's result is lost. A clean-up that unlinks a file whose walk has not yet closed its handle raises in the same way | Fixed: both unlinks suppress `OSError`. The next clean-up clears the leftover, as it clears a killed program's |
| 5 | Medium | `gui/web/frame.py:on_path`, `reset_layout`, `separator` | A drag or an arrow key starts from the separator's `aria-valuenow`, which is set only when the frame is built. After a change to a suite with other saved sizes, or after Reset layout, the first drag starts from the old size and the rail or panel jumps. A screen reader also reads the stale value | Fixed: the frame keeps its separators. `sync_separators` sets their values on a suite change and on a reset |
| 6 | Medium | `gui/web/assets/frame.js`; `frame.py:listen` | `window.frame.capturing` outlives the settings page. Start a key capture, then click a suite. The next chord typed anywhere (Ctrl+K, say) is swallowed and sent as `chord`. `listen` still routes `chord` to the old page's `_on_chord`, because no suite page replaces it, so the chord is bound to the command being captured or refused with a notice | Fixed: `on_path` sets `window.frame.capturing = false` with the ready flag |
| 7 | Medium | `gui/web/settings_page.py:_write`, `_reset` | The scope decides the file, whatever the setting allows. Start a capture in the User scope, switch to Project, then press the chord. `_write(keys)` saves `keys` into the project file, `with_project` drops it with a warning, and the binding is lost | Fixed: only a setting whose scope allows it is written to the project |
| 8 | Low | `gui/web/frame.py:_Frame.settled` | `asyncio.wait_for` raises `TimeoutError` after 20 s. The comment says that the page reports ready anyway, but `ready()` raised before it set the flag. `opening` stayed set, so every later sub-page waited 20 s and failed in the same way | Fixed: the timeout is suppressed and `opening` cleared |
| 9 | Low | `gui/web/assets/bridge.js:ensure` | `viewer` is set only once `Viewer.create` resolves. Leave `/study/charge` while Mol* builds and come back, and `init` runs again: two viewers in `#mol`, and `builds` is 2, which VER-78 (m) forbids | Fixed: `building` holds the build under way, and a call during it waits for that build |
| 10 | Low | `gui/web/numbers.py:shown` | The prefix is chosen before the rounding. When rounding reaches 1000 the prefix is not advanced: 999.96 nm at four figures shows `1000 nm`, and 0.99996 nm shows `1000 pm` (probed) | Fixed: a carry to 1000 moves to the next prefix |
| 11 | Low | `gui/web/frame.py:applied` | The changed table is built once per window. A change to the significant figures or the number style, settings that apply at once, left the table's numbers as they were until a reload | Fixed: `applied()` rebuilds the table's rows from the held list |
| 12 | Low | `gui/web/settings_page.py:_control` (`store_cap_gb`) | In the Project scope an empty field reads "empty for no cap". `save_setting(None)` removes the project's value, so the user's cap holds: the page cannot take a project off a cap | Fixed: in the Project scope the field reads "empty for your own cap". Whether a project may opt out of the user's cap is not ruled; the file can say it with `null`, and the page cannot |
| 13 | Low | `gui/web/frame.py:no_project` | A recent project's button calls `open_project` unguarded. A folder that no longer holds a project of this release raises `ProjectError` in the click handler, and the user sees nothing. The dialog's path catches it | Fixed: `open_recent` notifies the refusal |
| 14 | Low | `gui/web/frame.py:_unit` | `field_unit` lists dimensionless fields at a sequence's index 0, and every other caller converts the path to that form first. `_unit` passed the concrete path, so `electrolyte.species.1.z` and `charge.edits.1.radius_scale` had no unit and were shown raw, without the figures setting | Fixed: the path is made generic first, as `io/models.py` does |
| 15 | Low | `io/store.py:Store.get` | A reader outside a walk can pass the `meta.json` check while a clean-up renames the entry away. `read_text` then raises `FileNotFoundError`, where the docstring promises the entry whole or not at all | Fixed: that read returns None |
| 16 | Low | `io/store.py:_discard`, `evict` | A renamed directory whose deletion stopped (a file held open) is skipped by every listing. `usage` under-counts the disk, a cap is never met on disk, and only a put into the same fan-out folder after 24 hours sweeps it | Fixed: every clean-up deletes the `.<key>.evict.*` directories it finds, holding the lock. §5.3.2's NOTE says so |
| 17 | Low | `gui/web/theme.py:shipped` | `shipped()` copies the cached dict but not its themes. A caller that changes a shipped theme changes it for the whole process. `render_shell.py:write_config` does this: a shallow `model_copy` and then `colours.update`. `user_themes()` already returns deep copies | Fixed: `shipped()` returns deep copies |
| 18 | Low | `gui/web/frame.py:reset_layout` | The window keeps the shown suite's panel open or folded, but every suite was saved as `SuiteLayout()`, folded. The saved and shown layouts disagreed, and a reload folded the panel | Fixed: the shown suite is saved as shown |
| 19 | Low | `pipeline/run.py:keyed_walk` | `walk.mark = False` reaches `_Walk.stored` only. A stage's own `key()` that reads the store still marks: the mesh stage's `_stored` for `inputs.mesh.artefact`, and the charge stage's `check_stored_frame`. A forecast of such a case therefore moves read marks, which the NOTE says it never does | No change in the pass. Fixed by `/np-ship`: `Store.unmarked()` is a reader that records no mark, and the forecast's keying walk, and so the stages it builds, read through it |
| 20 | Low | `api/sweep.py:_parent_artefact`, `run_point` | A member reads its parent's solution before its own walk takes `Store.using()`. An "everything" clean-up in between removes the warm start's payload, and the member fails where it would have started cold | No change in the pass. Fixed by `/np-ship`: `run_point` holds `Store.using()` from the parent's lookup to the end of the member's walk |
| 21 | Low | `io/project.py:ProjectFile`, `SuiteLayout` | The project file gains `settings:`, `rail_px` and `bottom_px` and a `physics` layout key under the same `nanopnp/project/v0.6`, with `extra="forbid"`. alpha.14 then refuses a project this build has saved with a pydantic error, not with `ProjectFormatError`'s message | No change in the pass. The author ruled (2026-11-11): the alphas of one release share `nanopnp/project/v0.6`, as the case file did when WP5.07 added `variables:`; the changelog says an older alpha cannot open a project this one saved |
| 22 | Cleanup | `io/store.py:inputs_closure` | It called `_entries()`, which stats every file of every entry to size it, only to map keys to directories. `store_usage` and `clean_store` therefore walked the store twice, sizing it both times. The settings page does this on every refresh (search cleared, scope or *Modified only* toggled, theme chosen, reset), on the event loop | Fixed: the closure maps keys from the `meta.json` glob, unsized |
| 23 | Cleanup | `api/project.py:kept_artefacts` | It hard-coded `"run.json"` and `"members"` | Fixed: `io.manifest.RUN_RECORD_FILENAME` and `sweep.run.MEMBERS_DIRNAME` |
| 24 | Cleanup | `gui/web/frame.py` `RAIL_PX`, `BOTTOM_PX`; `settings.py` `recent_projects` | The frame restated `SuiteLayout`'s bounds. `model_copy(update=…)` does not validate, so a drift would save a size that the project file then refuses on opening. The setting's `le=30` restated `RECENT_PROJECTS_KEPT` | Fixed: `io/project.py` declares `RAIL_PX_LIMITS` and `BOTTOM_PX_LIMITS` once, and the setting reads `RECENT_PROJECTS_KEPT` |
| 25 | Cleanup | `gui/web/settings_page.py:_refresh` | With *Modified only* on and nothing changed, the store flag still kept "Runs and storage" as an empty section | Fixed: the flag includes *Modified only*, and the inner check goes |
| 26 | Conventions | `gui/web/numbers.py:_GAP` | Its docstring cites "(WB-21)". `.claude/rules/python.md`: "Requirement identifiers live in the names of in-scope tests and commit messages, not in prose" | Fixed: the identifier is dropped |
| 27 | Cleanup | `gui/web/settings_page.py` | `TOGGLE_MOST`'s docstring followed `COLOUR_NAMES`'s, so `TOGGLE_MOST` had none and `COLOUR_NAMES` had two | Fixed: moved under `TOGGLE_MOST` |
| 28 | Low | `docs/plans/index.md` | Item 14 changed the status lines of the WP plan and the Phase 5 plan but did not run `index_records.py`. The index still quoted WP5.15 as "planned, not started" | Fixed: the index is regenerated, along with `docs/code_reviews/index.md` for this report |

Not findings:

- `cleaning()` probes a walk's lock through its own descriptor. `flock` locks belong to an open file description,
  so closing the probe never releases the walk's lock, and a walk in the same process is seen as busy too.
- `boot_project` caps the store after its walk has left `using()`, and keeps the walk's own hashes. `Link.from_run`,
  which reads them after the cap, therefore finds them.
- `bindings` gives a user's binding the default chord it takes, and `refusal` still refuses to bind a chord that a
  default holds, so a clash can come only from a hand-edited file.

# Code review 033: WP5.08, the frame and the project folder

Reviewed head `c631d0c4f9d5b9d86bc3a02326bad87a53839b39` against base `ce2e8ec5c2e680c8b8ad64f892068fb7a4dd134d`
(PR 161). Status: completed. Static review at `xhigh` with `--max-findings all`. Eleven findings; eight fixed,
three recorded in two rows. No physics or numerics file changed.

| # | Where | Finding | Outcome |
|---|---|---|---|
| 1 | `api/project.py` | A refused `import_case` removed the files it wrote but left their names in the open project's index, and left the input files it had copied. A later `open_item` or `save_layout` then wrote the names to the project file, and `problems()` listed items that do not exist. | Fixed: the index and the new input files are restored. |
| 2 | `gui/web/overlay.py` | A settings dialog dismissed by its backdrop, while a key was waiting for its chord, left the page capturing: the next shortcut pressed anywhere rebound that command. Reopening the dialog showed a stale "Press a chord…". | Fixed: the dialog's `hide` releases the capture and redraws the keys. |
| 3 | `gui/web/theme.py`, `frame.py` | A theme read from disk, and the key bindings read from the settings file, reached an inline `<script>` through `json.dumps`, which leaves `</script>` whole; a shared theme file could break out of the script. A theme's token names and values were not checked on reading, as `save` checks them. | Fixed: `script_json` escapes `<`; `css` emits only a token name and a `#rrggbb` value; a theme file whose name is not a theme name is left out. |
| 4 | `gui/web/assets/frame.js` | A chord of Shift and a letter was accepted as a shortcut, so binding one stopped capital letters from being typed in every field. | Fixed: a chord needs Ctrl, Alt or Meta, except an F key. |
| 5 | `api/project.py` | `problems()` caught `ProjectError` but not `UnicodeDecodeError`; an item file that is not UTF-8 raised from the title bar of every page. | Fixed: it catches `ValueError`. |
| 6 | `gui/web/frame.py` | One page build loaded every item three to seven times: `counts` twice (each loading the changes and the problems), then the changes list and the problems list. | Fixed: a page builds each list once. |
| 7 | `io/project.py`, `gui/web/settings.py` | Two new temporary-file writers repeat `io.store.atomic_write_bytes`. | Fixed: both call it. |
| 8 | `gui/web/frame.py` | `title_bar` built the bindings table once per menu entry. | Fixed: once per bar. |
| 9 | `api/project.py` | `export`: result files of one run with the same name replace each other; the copied `run.json` keeps the old paths; an input in a sub-folder of `inputs/` is flattened without its item being rewritten; an unreferenced input can share a linked input's name; a failure leaves a half-written destination. | Recorded, REV-206. |
| 10 | `gui/web/frame.py`, `theme.py` | The layout is written on every drag step; the theme files and `tokens.css` are parsed at every call; dialogs are never deleted; an empty folder field reads as the working folder. | Recorded, REV-207. |
| 11 | `gui/web/frame.py` | The palette's filter is written twice, in `fill_palette` and `first_match`. | Recorded, REV-207. |

Test scope: all five test files the PR adds or changes were read against `CLAUDE.md`'s *Testing*. None was dropped. The
frame tests (i), (j) and (k) of VER-78 are the plan's own rows; whether they are a thin smoke test of the entry point
is put to the author in the report.

Checked on the fixes: `ruff check`, `ruff format`, `mypy src/`, `tests/tier1/test_project.py`, `test_store.py`,
`test_stage_conformance.py` and the VER-78 screen tests. `gate.sh run` follows in `/np-ship`.

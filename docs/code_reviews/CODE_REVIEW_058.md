# Code review 058: WP5.18, the Physics suite

2026-11-16 · PR #187, branch `claude/hopeful-hamilton-3xq15p`, head `ab7ace0` on base `d632951` · scope: the package's
source diff, 28 files of `src/` less the vendored KaTeX, read through ten angles (line by line, removed behaviour,
callers, language pitfalls, wrappers, reuse, simplification, efficiency, altitude, conventions) and a sweep:
`api/project.py` (`physics_case`, `choose_physics`, `set_exposed`, `problems`, `_error_path`), `gui/web/physics.py`,
`gui/web/physics_tools.py`, `gui/web/tools.py` (the cards, `flag`, `lead`, the `switch` and `materials` fields),
`gui/web/plane.py` (`electrolyte_plane`, `physics_plane`, `_conditions_plane`, `mesh_stored`, `shown_solids`, the
caches), `gui/web/pages.py` (`/api/physics/{name}/plane`), `gui/web/screens.py`, `gui/web/frame.py`,
`assets/plane.js` (the plot frame, the key), `assets/frame.js` (`frameMath`), `plot/data.py`, `pipeline/case.py`,
`pipeline/run.py` (`keyed_walk(upto=)`), `physics/models.py`, `physics/terms.py` and the refusal texts of `io/` ·
level: xhigh, with `--fix` · status: completed.

Static review: `ruff`, `mypy` on the touched files and 41 Tier 1 tests near the fixes ran; `/np-ship` gates the fixes.
The `physics-reviewer` read the physics diff before this review and found no error (the PR's **Verification**).

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Medium | `physics_tools.py:exposed_row`, `expose_as` | Each end of an exposed value's range was written with the other end as listed when the row was drawn, and `set_exposed` takes a range only whole, so a typed end was dropped and the row drawn blank: no range could be set from the pane (D9) | Fixed: both ends are read from their fields; a half-typed range writes nothing until the other end is typed; a rename keeps the stored range |
| 2 | Medium | `tools.py:material_row` | A material's reset and edits wrote the model but left its number, its ◆ and its reset as drawn, since a refresh does not rebuild a field's rows | Fixed: `reset_material` clears the field once the file no longer sets it; `show_material` shows the mark and reset as the file now reads |
| 3 | Low | `physics_tools.py:solids`; `plane.py:shown_solids` | The solids were read from `model.case()`, None whenever the shown study refuses, and keyed past the mesh, where a solid with no permittivity is refused: the pane fell back to every solid, the analyte too | Fixed: the shown case as formed, keyed to the mesh alone |
| 4 | Low | `physics_tools.py:show_cards` | A refusal of a molecular-model value or of the study's own was titled "cannot run with this model", putting it on the physics model | Fixed: the title names the model that holds the value, or the study's own values |
| 5 | Low | `physics_tools.py:undo` | Undo broke off at the first value refused, such as one unset since the change, and the note was already gone | Fixed: a value unset since is skipped; each other is written back and a refusal is reported without stopping |
| 6 | Low | `physics_tools.py:correction_row` | A correction's Bulk and Wall boxes kept the enabled state they were drawn with after its model changed to none | Fixed: `correction_parts` after each write of a correction's model |
| 7 | Low | `physics_tools.py:aside` | A study's own permittivities were written as a Python mapping under the field | Fixed: each material with its number |
| 8 | Low | `physics_tools.py:expose_as` | A name cleared to be retyped was written as the path's last part ("bias_V") after the debounce | Fixed: a blank name writes nothing |
| 9 | Low | `physics_tools.py:lead` | With no switch held wrong, the card led with "Turn . pnp cannot run otherwise." | Fixed: the base line instead |
| 10 | Low | `physics_tools.py:fitted`, `set_diameters` | A parameter set named by a path beside the model was looked for against the server's directory, so its hints were missing | Fixed: `parameter_set` finds it as resolution does |
| 11 | Low | `physics_tools.py:conditions_section` | A build of Conditions resolves the shown case three or four times outside the model's cache and keys the walk each time; a supplied mesh is read at each refresh | REV-255 |
| 12 | Low | `pages.py:physics_view` | The drawing was wrapped in `model.keyed_once()`, though it reads nothing of the model | Fixed: removed |
| 13 | Low | `_field_tex`, `_tex`, `_mtext`, `_listed`, `_curve_style`, `_plain` | Private functions carried docstrings, against `.claude/rules/python.md` ("No docstring on a test or on private code") | Fixed: removed, a comment kept where the code cannot say it |
| 14 | Low | `plane.py:Plane.json` | A plot's extent and points travel as `extent_nm` and `points_nm`, though they hold M, distances and factors (`python.md`: units in the name at the boundary) | REV-255: a change to the plot frame's contract in `plane.py` and `plane.js` |
| 15 | Low | `tools.py:_plain`, `api/project.py:_error_path`, `physics_tools.py:problem_path` | A refusal's place is read back out of its words in three ways; a refusal that carried its case path and file would end them | REV-254, with the pass over the diagnostics |

Not findings:

- `choose_physics` removes exactly the leaves `_check_unread` refuses: both skip a leaf with no schema default.
- `keyed_walk(upto=)` raises `UnknownStageError` for a stage the case does not walk; both callers resolve a supplied
  mesh first and catch the refusal, a `KeyError`.
- The rewritten refusals change no condition (the physics review); the GUI's gate words (`axis: z`, `displacement
  gate`, `stage 4 contour gate`, `expects`) still occur in the unchanged stage modules.
- `set_exposed` replacing a listed entry with the path's name and no range when called without them is its documented
  behaviour (D9); the Expose checkboxes of the other suites fire only on a toggle.

## Fixes

| File | Change |
|---|---|
| `src/nanopnp/gui/web/physics_tools.py` | Findings 1, 3 to 10, 13 |
| `src/nanopnp/gui/web/tools.py` | Findings 2, 13 |
| `src/nanopnp/gui/web/plane.py` | Findings 3, 13 |
| `src/nanopnp/gui/web/pages.py` | Finding 12 |
| `docs/project/review-items.md` | Findings 11 and 14 in REV-255; 15 in REV-254 |

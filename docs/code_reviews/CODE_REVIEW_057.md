# Code review 057: WP5.18's plan, the Physics suite

2026-11-13 · PR #186, branch `claude/trusting-bell-hhyxbe`, head `4502076` on base `e3c5f54` · scope: the plan commit's
13 files, `docs/plans/phase-5/wp5.18-the-physics-suite.md` first, its claims read against the code at the head:
`api/project.py` (`build_case`, `_build_case`, `molecular_for`, `set_value`, `set_exposed`, `_checked_write`,
`changes`, `problems`, `_delete`, `BUILD_LAYER`), `io/models.py` (`OWNERS`, `owner_of`, `EXPOSED`, `exposed_values`,
`_exposable_paths`), `pipeline/checks.py` (`element_orders`, `options_at`, `_ORDERS`, `_check_physics_switches`,
`_check_unread`, the walls' check), `physics/models.py` (`ModelDeclaration`, `SWITCHES`, the `boundary_conditions`
vocabularies, `case_model`), `mesh/adapter.py:MeshData`, `mesh/ingest.py` (`BOUNDARY_VOCABULARY`, `deployed_mesh`),
`plot/data.py` (`MeshElements`, `mesh_elements`, `mesh_of`, `correction_curves`), `materials/` (`Electrolyte`,
`load_corrections`), and `gui/web/` (`builds.py:BuiltModel`, `plane.py`, `pages.py`, `frame.py:_Frame.route`,
`on_path`, `screens.py`, `tools.py:Field`, `BUILDS`, `shell.py:Shell`, `states.py:boot`), with
`.claude/scripts/gui/render_shell.py` and `tests/tier1/test_gui_screens.py` · level: high, with `--fix` · status:
completed.

Static review of a plan commit: no test and no gate ran; the review turn gates the fixes.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | Medium | Implementation details, item 3.1 | `boundary_edges` was to return `(n, 2, 2)` segments in m from `edges_of(name)`; `MeshData.vertices` are in nm, `edges_of` returns `(k, 2)` vertex indices, and every `Plane` layer carries `points_nm` | Fixed: segments in nm, `data.vertices[data.edges_of(name)]`; the units and shapes in D7's grounding |
| 2 | Medium | Item 3.3 | Conditions read "the mesh the store holds under the case's keys": a case supplying `inputs.mesh` has no stage-6 artefact, and `mesh_of` and `_elements` give `MeshElements`, which hold no edges | Fixed: `deployed_mesh(resolved, <the stage-6 artefact or None>).data`, the region where it raises `KeyError`; D7's grounding names both |
| 3 | Medium | Item 3.2; D8 | The plot frame's `extent` and `points` keys were not `Plane`'s: `json()` writes `extent_nm`, `_bounds` reads `extent_nm` and `points_nm`, and `Frame` is `Literal["structure", "model"]` | Fixed: `Frame` gains `plot`; a plot holds its data extent and coordinates in `extent_nm` and `points_nm`, in data units, and `_bounds` returns None for it; D8's grounding states today's fields |
| 4 | Medium | D1; item 5 | `Tool` has no `view` field and `pages.ROUTES` routes `/<suite>` and each tool by `VIEWS[suite]`, which has no Physics row; `/physics` opens the last tool used, a page or a plane | Fixed: `Tool.view`'s type and default named, `ROUTES` routing each tool by it, and `_Frame.route` reading `/<suite>` as its last tool's route; `frame.py` added to item 5 |
| 5 | Medium | Item 5, `PhysicsModel` | `within()` read `Shell.shown_in`, but `BuiltModel` holds no shell, and `case()` and `problem()` go through `_built_case` to `build_case`, which refuses a physics model | Fixed: `PhysicsModel.shown_in`, set by the pane from `Shell.shown_in`; `_built_case` returns `physics_case(name, within())` |
| 6 | Low | D4's grounding | `_check_physics_switches` also refuses `charge.dielectric_transition_nm`, `inputs.pqr` and a generated mesh against the declaration; those are the continuum's or molecular model's values, which `choose_physics` cannot write | Fixed: named as left by `choose_physics` and shown at the shown study's card (D3), as AQ2's consequence says of a study's own values |
| 7 | Low | Verification, the FR-39 row | "A bias the study sets" named no way to set it: example 01's study holds no physics value, and no API sets a study's value before WP5.19 | Fixed: written into the study's YAML |
| 8 | Low | Item 2, `physics_case` | The no-study fallback's molecular model was "where C reads one"; `_build_case`'s rule is `own_outline` of the continuum model's body | Fixed: the rule named |
| 9 | Low | D7's grounding | `BOUNDARY_VOCABULARY` read as `mesh/adapter.py`'s; it is `mesh/ingest.py`'s | Fixed |
| 10 | Low | Work items 8 and 10 | Neither had a done-criterion (`np-plan/wp.md`, *Work items*) | Fixed: "done when the code and review say so" |

Not findings:

- The undo oracle holds: a path `choose_physics` sets from unset is removed by `set_value(path, None)`, a removed one is
  written back, and each write is checked leaf by leaf, so the order of the writes does not matter.
- `options_at` is read by `cli/reference.py` for the generated case reference, which is built, not committed.
- `charged-tube` is imported by `Project.import_case`, so its project holds a study and one model of each kind, as the
  VER-78 (m) row needs.
- `_build_layer`'s comment states that no stage up to the mesh reads a physics value, so the fallback case keys its
  mesh as the continuum model built alone.

The plan after the fixes: 3,377 words; 1,567 outside Grounding and Implementation details; Implementation details 964:
within `np-plan/wp.md`'s caps.

## Fixes

| File | Change |
|---|---|
| `docs/plans/phase-5/wp5.18-the-physics-suite.md` | Findings 1 to 10 |
| `docs/plans/current.md` | The lane's next step, `/np-implement wp 5.18` |

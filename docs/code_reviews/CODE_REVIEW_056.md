# Code review 056: WP5.17, the Continuum suite

2026-11-13 · PR #185, branch `claude/wp-5-17-implement-0junxj`, head `c959dfb` on base `be772b4` · scope: the PR's 112
files. The code was read in full with each touched function and its callers: `geometry/` (`outlines.py`, `pore.py`,
`region.py`, `analyte.py`, `defaults.py`), `mesh/` (`generate.py:generate`, `idealised.py`, `ingest.py:MeshStage`,
`primitives.py`, `sizing.py`), `pipeline/` (`case.py:resolve`, `_resolve_density`, `checks.py:_check_pore`,
`_check_profile`, `run.py:selected_stages`, `keyed_walk`), `io/` (`case.py:Mesh`, `MeshSizes`, `_check_supplied`,
`models.py:merge_layers`, `project.py:ProjectFile`, `artefact.py:CaseArtefact`), `api/project.py` (`build_case`,
`molecular_for`, `set_built_with`, `derive_model`, `_checked_write`, `kept_artefacts`, `_built_stages`), `plot/data.py`,
`charge/stage.py`, `post/indicator.py` and `post/stage.py`'s case hash, `cli/building.py`, `gui/assess.py`,
`gui/geometry.py`, and `gui/web/` (`builds.py`, `continuum.py`, `continuum_tools.py`, `plane.py`, `assets/plane.js`,
`tools.py`, `molecular.py`, `frame.py`, `pages.py`, `screens.py`, `queue.py`, `glossary.py`). The tests, the
specification's diff and `.claude/scripts/gui/` were read against them · level: xhigh, with `--fix` · status:
completed.

Static review. `ruff check`, `ruff format --check` and `mypy` ran on the fixed tree and passed, with one Tier 1 test
(`test_gui_viewmodels.py`'s import guard); no gate, benchmark or `--nightly` walk ran: `/np-ship` gates the fixes.

## Findings

| # | Severity | Where | Finding | Disposition |
|---|---|---|---|---|
| 1 | High | `gui/web/continuum_tools.py:IDEALISED_PARTS` | It held `electrolyte`, whose row is `numerics.mesh.sizes.electrolyte_nm`. For a model declaring `geometry.pore` the Mesh tool showed the table's 2.8 nm × the scale as the electrolyte's size, though an idealised pore meshes it at the global size, and opened a field whose typed value `_check_pore` refuses: one keystroke left the model's file forming no case | Fixed: the set is the membrane, the wall and the global size, as its docstring says |
| 2 | Medium | `gui/web/continuum_tools.py:before_fields` | The *Built over* choice was hidden and disabled while the model forms no case. A paired molecular model that is refused makes `build_case` raise, so the one control that re-pairs the model was gone exactly when it was needed | Fixed: offered whenever the model reads a molecular model, enabled while the project holds one |
| 3 | Medium | `gui/web/assets/plane.js:show` | Nothing ordered two drawings in flight: a later request that answered first was overwritten by an earlier one, so quick colourings, or the tick's redraw after a measurement beside a restyle, left the view on a drawing the pane no longer names, and marked the screen ready early | Fixed: each request is numbered and only the latest one draws and marks the screen ready |
| 4 | Medium | `gui/web/continuum.py:ContinuumModel.paths` | `\bgeometry(?:\.[a-z_]+)*` matched the bare word: "carries a geometry: section and supplies inputs.mesh" named `geometry` instead of `inputs.mesh`, and the charge stage's "element geometry digest" named `geometry`, a path no field holds | Fixed: `geometry` must be followed by a dotted part |
| 5 | Medium (efficiency) | `gui/web/continuum_tools.py`: `show_parts`, `show_part`, `show_edit`, `show_histogram`, `show_element` | Run from events outside `keyed_once`, each read built the case again and re-keyed the walk, which hashes the structure: one click on a part built the case three or four times and keyed the walk twice, and a picked element keyed it twice; REV-242's measured cost, which the pane's build and refresh had been cut to once | Fixed: each runs in one `keyed_once` (`_keyed`) |
| 6 | Low | `gui/web/continuum_tools.py:field`, `on_plane_value` | For an idealised pore Region offered `geometry.membrane.centre_z_nm`, also typed on the drawing's label, and Mesh offered `numerics.mesh.backend`; `_check_pore` refuses both away from 0 and netgen | Fixed: both are shown disabled for such a model, and a label's value is not written to a disabled field |
| 7 | Low | `gui/web/builds.py:BuiltModel.build` | A build started at `self.stages[0]`, `density`, for every continuum model. One with a supplied outline or an idealised pore said "Smearing the density…", put the progress bar under Pore geometry, and a refusal before the walk's first word was recorded at a stage it does not walk, so no tool showed it | Fixed: the first of the model's stages that it walks |
| 8 | Low (memory) | `gui/web/plane.py:_MESHES` | Every mesh's elements ever drawn stayed held for the server's life (about 45,000 triangles each on 2WCD, with sizes, both qualities and materials); each size or scale tried adds one | Fixed: the four last read, under a lock, since a drawing request runs in the thread pool |
| 9 | Low | `gui/assess.py:_context`, `measure_loop` | A case with `structure:` beside `inputs.profile` now resolves no density, against the assert's "a structure case always resolves one"; such a case, as the Qt shell may open, reached `stored_upstream` and was refused with the walk's raw words | Fixed: refused naming `inputs.profile`; the assert's comment states the invariant |
| 10 | Low | `gui/web/continuum_tools.py:start_assess` | It guarded on a running process. One that had ended but was not yet polled was replaced: its temporary folder was never removed and its answer was lost | Fixed: a held process blocks a new one until the next tick reads it |
| 11 | Low | `gui/web/continuum.py:save_edit`; `api/project.py:derive_model` | The saved edit drops `geometry.density`, as `_check_profile` requires beside `inputs.profile`, so `h_c` falls back to 0.05 nm: the exclusion shell is keyed and checked at another `h_c`, and an offset in (2 `h_c` of the parent, 0.1 nm] is refused only at the build. `derive_model` promises a refusal where "its values form no case", which a continuum model's leaf-by-leaf check does not make | Not fixed: keeping the parent's `h_c` beside a supplied profile is a specification decision; put to `/np-ship` |
| 12 | Low | `gui/web/continuum.py:save_edit` | The outline is written into `inputs/` before `derive_model`; a refused derivation leaves the file there, named by nothing | Not fixed: it is named by its digest and may be another model's; removing it needs that check |
| 13 | Low | `gui/web/continuum_tools.py:__init__` | `walked` and `supplied` are read once, when the pane is built. After *Built over* changes the pairing, to a molecular model that reads a PQR, *Build geometry* still targets `contour`, and `unbuilt` calls the stage "supplied" | Not fixed: the page is rebuilt on the next visit; a pairing to a PQR model is rare |
| 14 | Low | `gui/web/screens.py:tool_for` | `geometry.pore.radius_nm` is set in Region but is in no tool's fields or parts, so a problem or change naming it opens the suite's last tool | Not fixed: listing it in Region's fields shows it for every model |
| 15 | Low | `io/case.py:Mesh.sizes` | The block dumps as nulls when nothing is typed, so every case's `CaseArtefact` hash moves, and with it every stored QoI and report key, though stages 1 to 6 do not | Not fixed: D5's grounding states the move; noted that it is not limited to typed sizes |
| 16 | Cleanup (efficiency) | `gui/web/plane.py:_mesh_layer`; `plane.js:pathsOf` | Every restyle, pick or histogram bar sends the whole mesh again, vertices, triangles and one value per element, and the canvas rebuilds its paths, since they are cached by layer object | Not fixed: the drawing's protocol, for a later package |
| 17 | Cleanup (efficiency) | `gui/web/continuum_tools.py:__init__` | `walked()` and `own_outline()` run before the pane's `keyed_once`, one more case build and resolution per page | Not fixed: small beside finding 5 |
| 18 | Cleanup (reuse) | `gui/web/continuum.py`: `OWN_OUTLINE`, `_holds` | A copy of `api/project.py`'s `_OWN_OUTLINE` and `_holds`: the pane could say "reads no molecular model" for a model the library pairs | Fixed: `api/project.py:own_outline` decides for both |
| 19 | Cleanup (reuse) | `gui/web/tools.py:_Pane.body` | A copy of `ContinuumModel.body` | Fixed: `BuiltModel.body`, which the pane calls |
| 20 | Cleanup (reuse) | `gui/web/plane.py:_mesh_layer` | It sampled the palette as `_stops` does | Fixed: `_stops` |
| 21 | Cleanup (reuse) | `gui/web/continuum.py:save_edit` | `../../inputs/` is written by hand, not derived from `FOLDERS` | Not fixed: the Molecular tools write it the same way |
| 22 | Cleanup (simplification) | `gui/web/builds.py:ToolModel` | The protocol is used nowhere: `_Pane` is generic over `BuiltModel` | Not fixed: D6 names it; put to `/np-ship` |
| 23 | Cleanup (simplification) | `mesh/generate.py:generate` | The region branch scales the table twice | Not fixed: trivial |
| 24 | Conventions | `geometry/outlines.py` (module docstring), `continuum_tools.py:PART_ROWS`, `frame.py:changes_list`, `tools.py` (`keyed_once`, `tool_list`) | They cite FR-09, WB-41, REV-237 and REV-242. `.claude/rules/python.md`, which CLAUDE.md's *Prose in code* names: "Requirement identifiers live in the names of in-scope tests and commit messages, not in prose" | Fixed |
| 25 | Low | `gui/web/tools.py` (module docstring) | "The Molecular suite's tool pages", for the module that now holds every suite's pane | Fixed |

Not findings:

- `api/project.py:_built_stages` keeps `if not identity.built`: `Identity.built` means a walk builds the stage, so
  the filter keeps what the store holds, as its comment says.
- `numerics.mesh.sizes` beside `inputs.mesh` is refused by `CaseDocument._check_supplied`, which compares the block
  with its default; the removed `maxh_nm` refusal for a case with no pore is replaced by that and by `_check_pore`.
- `size_wall` after `shape()` sizes the same edges `name_edges` sized, so no idealised or test mesh moves.
- The region stage reads `contour` as an optional input, so dropping stages 2 to 4 beside a supplied profile leaves
  it fed.

## Fixes

| File | Change |
|---|---|
| `src/nanopnp/gui/web/continuum_tools.py` | Findings 1, 2, 5, 6, 10, 24 |
| `src/nanopnp/gui/web/continuum.py` | Findings 4, 18 |
| `src/nanopnp/api/project.py` | Finding 18: `OWN_OUTLINE` and `own_outline` |
| `src/nanopnp/gui/web/builds.py` | Findings 7, 19 |
| `src/nanopnp/gui/web/tools.py` | Findings 19, 24, 25 |
| `src/nanopnp/gui/web/plane.py` | Findings 8, 20 |
| `src/nanopnp/gui/web/assets/plane.js` | Finding 3 |
| `src/nanopnp/gui/assess.py` | Finding 9 |
| `src/nanopnp/geometry/outlines.py`, `src/nanopnp/gui/web/frame.py` | Finding 24 |

## At `/np-ship`

Each applied fix was read as a diff against the specification, the plan and the round's record
(`docs/design/reviews/2026-11-12-continuum.md`).

| # | Decision |
|---|---|
| 2 | Reverted. The round's F12 kept "a file that forms no case disables the pane" as built; the way out is to fix the paired molecular model in its own suite |
| 4 | Kept, with the lookahead tightened to a dotted name (`geometry(?=\.[a-z_])`), so a sentence ending "geometry." names nothing |
| 11 | The docstring fixed: `derive_model` refuses a continuum model whose values are refused alone, not one that forms no case. The grid a supplied outline's shell takes is REV-246, a question for the author |
| 15 | Fixed. AP3 rules that a case typing no size keys as before, and AP4 that no existing key moves; D5's grounding stated the move, which the PR did not. `CaseArtefact` leaves out a `numerics.mesh.sizes` that types nothing, and §5.2.2's NOTE says so. Every loadable example case (15 of 15) hashes as on `main` (`be772b4`); before the fix all 15 moved |
| 12, 13, 14, 16, 17, 21, 23 | REV-248, then fixed on the author's ruling of 13 November 2026 ("Fix them now") |
| 22 | Kept: the plan's D6 names `ToolModel` for `MolecularModel` and `ContinuumModel` |

The `physics-reviewer`'s pass before the review found the electrolyte row of finding 1 and three doubts. The refusal
of a typed size beside `inputs.mesh` named the block with an object's repr. It now names each typed leaf, as §5.3.1's
NOTE on `numerics.mesh` asks. The solid-share gate's reach against an outline supplied in another frame is REV-247.
VER-53's test types `protein_nm` alone, which is what VER-53's row asks; `case_sizes` maps every part by name.

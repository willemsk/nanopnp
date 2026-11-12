# WP5.17 — The Continuum suite

**Status: planned, not started.** Planned 12 November 2026 on `main` (`c6b85ce`). It inherits §8.2.28 AD4, §8.2.34 AJ8,
§8.2.36 AL22 and this plan's §8.2.40 AP1 to AP4.

This plan belongs to [the Phase 5 plan](phase-5-workbench.md). `SPECIFICATION.md` governs. An identifier here points to
a clause and never restates it.

## In brief

**What changes.** The Continuum suite starts working. From a prepared molecule you build the protein's outline, edit
it by hand, set the membrane and the reservoirs, and build and inspect the mesh, each drawn in a flat cross-section of
the pore. As you ruled, an edited outline runs with the protein's own charge, a model builds on its own over a molecule
you choose, and every part of the mesh can be sized, following the size scale. First the library's inside is tidied so
both kinds of pore share one interface, moving no stored result. The tools are drafted on 2WCD, shown to you, then
finished to your verdicts.

**Cost.** About three sessions, 9 to 15 agent hours and 12 of your touches, the prototype round included. The Molecular
suite measured 6 agent hours and 10 touches; this one adds four library steps and a drawing surface. No new library.

**What could go wrong.** The tidying could move a mesh; every recorded and test mesh is checked unchanged. An outline
drawn in another frame could misplace the charge; the check that most of the charge sits in the solids refuses it, and
an unedited outline must give the original charge to twelve digits. A mesh built alone is sized for
0.15 M salt, so a study at another salt builds its own; the pane says so. A typed size could fail the mesh's quality
check, which then refuses the build.

**Your call.** None for the plan: you ruled the four points. At the prototype round: the cross-section's look, the
editor's handles and the mesh's quality view. *Recommendation:* rule them on the drawn screens.

## Execution brief

**Scope.** The phase entry's WP5.17 as AP1 to AP4 amend it: REV-170 (CODE_REVIEW_036 candidate 3, C3.1, C3.2, corrected
in D2), REV-39 and REV-56's workbench part fixed; REV-242's third point measured. **Depends on:** WP5.16 (merged,
`v0.6.0-alpha.16`). **Requirements:** FR-09, FR-10, FR-27, FR-33, FR-34, FR-35, FR-39; QR-12; VER-53, VER-55 (restated), VER-61, VER-62,
VER-78. **Constrained by:** AJ1, AJ8, AL22, G10, I4, CON-09, CON-10, ADR-004.
**Implementing session:** Opus, high effort; sub-agents Sonnet, high. Tag `v0.6.0-alpha.17`.

**Amended when it lands:** VER-53, VER-61, VER-55's restated NOTE; §5.2.2's NOTE on the size table; §5.3.1's NOTEs on
`inputs:`, `inputs.profile`, `numerics.mesh` and model files; FR-33's and FR-39's matrix rows; Q10 to Q12, Q14 to Q23.

### Decisions

Ten: the rulings AP1 to AP4 added three library steps to the phase entry's seven.

| Decision | Choice | Why/source |
|---|---|---|
| D1 The region interface | `RegionOutlines` and the `Stage5Region` protocol in `geometry/outlines.py`, which both records implement and every consumer reads; `mesh/generate.py:generate` picks the mesher in one `match` on the class | REV-170, D3.1, D3.4, C3.1; decided by the plan for the module (`region.py` imports `pore.py`) and the `match` (mypy narrows a class pattern, not a property) |
| D2 Wall sizing and one cylinder | `CylinderPore` names, never sizes; `mesh/sizing.py:size_wall` sizes `wall` edges alone; `mesh_cylinder_pore` and `mesh_pore_with_analyte` replace `CylindricalPoreGeometry` and `PoreWithAnalyte.generate`; MOD-03's row goes; no mesh moves | D3.2, D3.3, C3.2; decided by the plan where the review's sketch would move meshes |
| D3 An outline beside a structure | `structure:` beside `inputs.profile` resolves where the case deposits a charge and is refused otherwise, naming both; stages 2 to 4 drop under a supplied outline; the Contour tool saves through `Project.derive_model` | AP1, ruled by the author |
| D4 A continuum model built alone | `build_case("continuum", name)` to the mesh: `BUILD_LAYER` with its parameter set's solid permittivities, the paired molecular model and the continuum model, merged as a study merges; the pair held in the project file | AP2, ruled by the author; decided by the plan for where the pair is held |
| D5 Part sizes | `maxh_nm` read beside any generated region; `numerics.mesh.sizes` for the other four rows, optional, refused beside `geometry.pore`; `mesh/sizing.py:case_sizes` the typed table that `size_scale` scales | AP3, AP4, ruled by the author; decided by the plan for the names, `SizeTable`'s |
| D6 A second suite | A `ToolModel` protocol for `MolecularModel` and `ContinuumModel`; the frame, routes and pane read the suite; pages at `/continuum/<tool>`; REV-242's keying cached if a refresh's exceeds 0.25 s | WB-05, WB-07, FR-27, FR-35, M2; decided by the plan |
| D7 The (r, z) view | One canvas per window, `assets/plane.js`, beside Mol* and built once, drawing the layers `gui/web/plane.py` writes from `plot/data.py`; pan, zoom, equal scale, r right and z up; edits return by `emitEvent` | The design document's renderers, WB-05, CON-09; decided by the plan |
| D8 Contour | Opens on the built outline or the model's `inputs.profile` (REV-39); `ProfileEditor` edits; measuring and seeding run in a child (REV-56); unsaved edits are asked about before they go; *Save edit…* by D3 | REV-39, REV-56, T1; decided by the plan |
| D9 Geometry, Region, Mesh | Protein geometry's layers; Region's values typed in the pane or on the drawing, one value (FR-33); the mesh by material, SICN or gamma, a histogram's bars outlining their elements | FR-33, Q14 to Q23; decided by the plan |
| D10 The round | The tools drafted on 2WCD in each state, reviewed, published and collected with REV-235's and REV-237's points; then finished | AJ8, ruled by the author |

### Grounding

**D1.**
- `geometry/region.py:read_region` returns `RegionRecord | IdealisedRegionRecord`; the second lives in `geometry/pore.py`,
  which `region.py` imports. Nine sites branch on the class: `mesh/generate.py:generate` three times (the recipe, the
  mesher, the `exclusion` flag), `mesh/ingest.py:MeshStage._recipe`, `plot/data.py:region_drawing`, `cli/building.py:_mesh`,
  `gui/geometry.py:load_view`, `charge/stage.py:check_stored_frame` (the membrane's centre, 0.0 for a pore) and the
  fields stage's `assert isinstance(record, RegionRecord)` before `derive_fields`, which the case's refusal of an idealised
  transition guards. `region.py:write_region` branches on its own records.
- `region_drawing` draws an idealised membrane to `reservoir_radius_nm` and a profile region's from its inner chord to
  `reservoir_radius_nm + half`; `load_view`'s chord is the first and last point of that membrane outline.
- `MeshStage.forecast_parameters` picks by `resolved.pore` and `resolved.exclusion_offset_nm`, with no record; it stays.

**D2.**
- `CylinderPore.name_edges` sets `edge.maxh` on `wall`; `shape(name_mouths=True)` names the mouths `interface`.
  `mesh/idealised.py:generate_idealised` meshes with the mouths named and `optsteps2d=3`; `CylindricalPoreGeometry.generate`
  with them unnamed, `grading=0.2`, netgen's default steps, gated by `_gated`.
- `mesh/sizing.py:apply_sizes` also sizes the arcs, the axis in the pore and the faces: through it every idealised mesh
  would move, so D2 adds `size_wall` instead of the review's "through `apply_sizes`". The review's
  `mesh_cylinder_pore` returned `GeneratedMesh` with a default wall size; tests take a `Mesh` and most pass no wall size.
- `CylindricalPoreGeometry` has 48 constructor calls in 35 test files and `tests/conftest.py`; `post/indicator.py:lumen_band`
  types it; three knowledge files name it.
- `PoreWithAnalyte.shape` passes `wall_h_nm` to the pore's `name_edges`; its `generate` (three callers,
  `test_forces.py`, `test_force_convergence.py`, `test_analyte.py`) and `AnalyteInBoxGeometry.generate` mesh in `geometry/`; the latter
  sizes only its body's surface, which REV-170 does not name, and stays.
- `mesh/defaults.py:DEFAULT_PORE_RADIUS_NM` is 2.0, and `geometry` may not import `mesh`.
- `tests/tier1/test_layering.py`'s two annotation-cut tests assert the static relation unchanged by a substituted
  `from nanopnp.mesh.primitives import CylindricalPoreGeometry`, true only while MOD-03's row stands; VER-61's row says
  the same. `test_ver61_top_subpackage_cycle_is_detected_naming_components` still holds.
- VER-62: examples 01 and 02's ePNP-NS walk run per push; 02 classical, 03, 07 and both 2WCD walks are `nightly`;
  `tests/tier1/test_idealised_pore.py::test_ver62_a_declared_cylinder_meshes_to_the_recorded_mesh` runs per push.

**D3.**
- `pipeline/checks.py:_check_profile` refuses `structure:` beside `inputs.profile` on the document;
  `ResolvedCase.deposits_charge` (the case protonates and its model declares `fixed_charge`) exists only after
  `pipeline/case.py:resolve`. `pb` declares no coefficient; an `inputs.charge` case does not protonate.
  `pb` and `pb-linear`, the two models without `fixed_charge`, carry no solids, so a case that generates its mesh
  under either is refused before the pair is reached (PHY-21's NOTE); `inputs.charge` is the case beside a profile
  that deposits nothing.
- `pipeline/run.py:selected_stages` drops a stage whose `needs_section` is absent; density, symmetry and contour need
  `structure`, so beside it they would run. Charge reads `protonation` and `region`.
- `geometry/region.py:_profile_input` takes `resolved.profile` before the contour. Stage 4's outline is in stage 1's
  frame (§5.3.1's NOTE on `geometry.contour`), the frame of the protonated atoms.
- `charge/deposit.py:check_solid_share` refuses under 0.5 of Σ|q| in the solids; 2WCD measures 0.977
  (`knowledge/04-clya-geometry-and-charge/03-fixed-charge-pipeline.md`).
- `io/case_paths.py:with_profile` drops `structure`; only the Qt shell calls it, and it stays.
- `tests/tier2/test_gui_geometry_2wcd.py`'s case runs `epnp-ns` on a structure, so it deposits; it is `nightly`. No test
  asserts the refusal's text.

**D4.**
- `api/project.py:_build_case` merges `{**BUILD_LAYER, **body}` shallowly; two bodies share `charge`, `inputs` and
  `numerics`, which `io/models.py:_merge_all` merges key by key.
- An idealised continuum model over `BUILD_LAYER` is refused for `physics.solid_permittivities.membrane`; one over the
  2WCD structure resolves and walks to the mesh through stage 1, the protonation and stages 2 to 6 (probed).
  `api/case.py:Case.cylinder` reads the permittivities from `load_corrections(parameters).dielectrics`.
- `mesh/sizing.py:resolve_wall_size` sizes `auto` at the case's Debye length or at `wall_for_concentration_M`, as
  `min(0.05 nm, λ_D/5)`: the ceiling holds below about 1.5 M NaCl, so a 1 M study keys stage 6 as 0.15 M does.
- `_checked_write` validates a kind in `BUILD_UPTO` as its build case; `kept_artefacts` and `_built_stages` iterate
  `BUILD_UPTO`, cached per `(kind, name)`.
- `io/project.py:ProjectFile` is strict: `library`, `open`, `current`, `layout`, `settings`.
- `pipeline/checks.py:_check_pore` refuses `structure:` beside `geometry.pore`. `io/models.py:_merge_all(models, study)`
  folds `_merge` over the models, then the study.
- `_built_stages`' stamp hashes the merged case's text and its input files, so it follows a changed pair.

**D5.**
- `pipeline/checks.py:_check_pore` refuses `maxh_nm` without `geometry.pore`. `mesh/generate.py:idealised_recipe` takes
  `(maxh_nm or SIZES.global_nm) × size_scale`; a region takes `SIZES.scaled(size_scale)` in `generate` and in
  `MeshStage._sizing`, whose recipe keys `table`. Both meshers take a `SizeTable`.
- `SizeTable`'s fields are §5.2.2's rows: global, pore domain (`protein_nm`), reservoir domain (`electrolyte_nm`),
  reservoir outer boundary (`arc_nm`), axis inside the pore.
- `io/defaults.py` records mesh sizes as configuration, never as deviations.
- `io/artefact.py:CaseArtefact` hashes the whole validated dump, so `numerics.mesh.sizes` moves the case artefact's and
  the run's keys, never stages 1 to 6's, which key on their own parameters; the PR says so.

**D6.**
- `gui/web/screens.py`: Continuum's tools are `_later(...)`, with empty ids; `TOOL_CONTROLS` and `SCREENS` read
  `SUITES[0]`. `pages.ROUTES` and `install` read `MOLECULAR_TOOLS`. `tools.py`'s `_Pane`, `tool_list`, `tool_page` and
  `current_model` name `"molecular"`; a tool's section is `<id>_section`.
- `frame.py`: `Route.view` is `"molecule"` or None, and `on_path` hides the view region otherwise; `mark_suite` marks a
  running build on Molecular alone; `problems` adds `molecular.refusals`.
- `molecular.py:MolecularModel.artefacts` keys the walk on every call (REV-242); `refused_path` reads `structure|charge`
  paths and stage-1 gate words. Neither `molecular.py` nor `link.py` imports NiceGUI (checked).

**D7.**
- No (r, z) drawing exists in the browser; `/study/charge` shows a server PNG (`link.py:png`, `Extent`) under SVG
  markers, and `gui/geometry.py:lookup_table` colours rasters.
- `plot/data.py` gives `density_section` (y = 0, stage 1's frame), `reduced_map`, `contour_polygon_m`, `region_drawing`
  (model frame) and `mesh_elements` (vertices, triangles, size, SICN; gamma and material are in `QualityReport.gamma` and
  `MeshData.triangle_material`). Stage 4's gate record holds `radius_profile` (`z_nm`, `probe_nm`, `lumen_nm`).
- 2WCD's mesh has about 45,000 triangles at the default sizes. `bridge.js` reports picks by `emitEvent`, which `frame.py`
  binds with `ui.on`.

**D8.**
- `gui/geometry.py:ProfileEditor` is Qt-free: `from_profile`, `from_seed`, `move`, `insert`, `delete`, `undo`, `redo`,
  `document()` refusing with the loader's words, `save(directory)`. `gui/assess.py:AssessProcess` runs `measure_loop` or
  `seed` in a spawned child from `AssessRequest(case, store, vertices)`, `case` a file.
- `gui/web/states.py`: `charged-tube` and `uncharged` continuum models supply `inputs.profile`; `refused` breaks one's
  `radius_nm`.

**D9.**
- `io/models.py:OWNERS` gives the continuum model `geometry`, `charge.exclusion_offset_nm`, `numerics.mesh`,
  `inputs.mesh` and `inputs.profile`; `structure.symmetry.point_group` is the molecular model's.

**D10.**
- `.claude/scripts/gui/render_shell.py` shoots `SCREENS` in every state and a cached 2WCD project from example 07's
  case. `docs/design/mockups/a/02-geometry.html` holds `g-geometry`, `g-contour`, `g-region`; `03-mesh.html` holds
  `s-size`, `s-quality`; their generator is `generators/mockups/s_continuum.py`.

### Implementation details

**Item 1.** `RegionOutlines(pore_nm, membrane_nm, exclusion_nm, membrane_half_thickness_nm, reservoir_radius_nm,
z_extent_nm)` carries `region_drawing`'s values today, with `chord_nm` the membrane outline's first and last points.
`region_drawing`, `MeshStage._recipe` (`idealised=record.is_idealised, exclusion=record.has_exclusion`) and `load_view`
read the protocol, and `check_stored_frame` its `membrane_centre_z_nm`, a field `RegionOutlines` adds; `generate`'s one
`match` picks the recipe and the mesher, its flag `record.has_exclusion`; the fields stage's assert stays. `cli/building.py` reads `read_idealised_region(path)`, which raises `ValueError` on a profile's
region.

**Item 2** (Sonnet), in `geometry/pore.py`, `geometry/analyte.py`, `mesh/sizing.py`, `mesh/primitives.py`,
`mesh/idealised.py`, `mesh/defaults.py`, `post/indicator.py`, `tests/tier1/test_layering.py`, the test callers and three
knowledge files.
1. Before any edit, a scratchpad script records `from_ngsolve(mesh).content_hash` for each distinct construction of
   `CylindricalPoreGeometry` and `PoreWithAnalyte` in `tests/`, and for `generate_idealised` at example 01's sizes.
2. `CylinderPore(pore_radius_nm=DEFAULT_PORE_RADIUS_NM, membrane_thickness_nm=13.0, reservoir_radius_nm=50.0)`;
   the constant moves to `geometry/defaults.py`, which `geometry/pore.py` imports and `mesh/defaults.py` re-exports,
   so the command line loads no `pydantic` through it. `name_edges(shape)` and
   `shape(*, name_mouths=True)` lose `wall_h_nm`.
3. `size_wall(shape, wall_h_nm: float | None) -> None`: each edge named `wall` takes `maxh`; nothing for None.
4. `mesh_cylinder_pore(pore=CylinderPore(), *, maxh_nm, wall_h_nm=None, check_quality=True) -> Mesh`:
   `shape(name_mouths=False)`, `size_wall`, `GenerateMesh(maxh=maxh_nm, grading=0.2)`, `_gated` with today's `where`.
   `mesh_pore_with_analyte(geometry, *, maxh_nm, wall_h_nm=None) -> Mesh`, also in `mesh/primitives.py`: `geometry.shape()`,
   whose `wall_h_nm` goes, then `size_wall` and `GenerateMesh(maxh=maxh_nm, grading=0.2)`, ungated as today.
   `generate_idealised` calls `shape()` and `size_wall`.
5. `CylindricalPoreGeometry(a, b, c).generate(**kw)` becomes `mesh_cylinder_pore(CylinderPore(a, b, c), **kw)`; an
   attribute read stays on `CylinderPore`; `PoreWithAnalyte(...).generate(**kw)` becomes `mesh_pore_with_analyte(...)`.
6. Delete the class, `geometry/analyte.py`'s `TYPE_CHECKING` block (`CylinderPore` imported at the top) and MOD-03's
   row; reword the docstrings naming the class, and the three knowledge files, each with a `knowledge/log.md` line.
7. The two annotation tests substitute `from nanopnp.mesh.primitives import mesh_cylinder_pore` and assert the static
   relation gains `geometry -> mesh`; item 3 amends VER-61's row to say so.
8. Re-run the script: every hash equal.

> **Outcome — item 2.** Defined in `geometry/pore.py`, the constant made `import nanopnp.cli` load `io.case` and
> `pydantic` through `mesh/defaults.py`, which `test_cli.py::test_ver32_classifying_imports_no_exception_module`
> refuses; it has a module of its own. Every construction the tests build kept its content hash: 31 cylinders, 2 pores
> with an analyte and 5 `generate_idealised` calls, 38 of 38 equal, recorded by a pytest plugin before and after; the
> command line's default cylinder at example 01's sizes gives `546c34f4…` both times. Examples 01 and 02's ePNP-NS
> walk held their recorded meshes (6.9e-14 and 1.1e-16 relative).

**Item 4.** `resolve` raises `CaseValidationError` where `resolved.profile` and `resolved.structure` are set and the
case deposits no charge, naming both keys; `_check_profile` drops its clause. Under `resolved.profile`,
`selected_stages` adds `density`, `symmetry`, `contour` to `dropped`. `Project.derive_model(kind, parent, name, values)`
copies the parent's own body, sets or removes each path by `_put` or `_delete` and writes through `_checked_write`; the
Contour tool sets `inputs.profile` to `{path: <the outline in inputs/>, format: profile1}` and removes
`geometry.density` and `geometry.contour`.

> **Outcome — item 4.** `pb` and `pb-linear`, the models without `fixed_charge`, carry no solids and are refused on any
> generated mesh first, so `inputs.charge` is the case beside a profile that deposits nothing. On 2WCD the null edit beside
> its structure deposits 24.05 e on the electrolyte, 0.72 e on the membrane and −84.77 e on the protein, equal to the
> structure's walk to 10⁻¹², and the moved edit passes the solid-share gate at 0.977. Here the structure's walk to stage 7
> took 40.2 s, each edit's 1.9 and 1.8 s.

**Item 5.** `ProjectFile.built_with: dict[str, str]`; `Project.molecular_for(name)`, `set_built_with(name, molecular)`.
`_build_case` merges `[BUILD_LAYER + {physics: {solid_permittivities: {protein, membrane}}}, molecular body, continuum
body]` with `io/models.py:merge_layers(layers)`, the fold `_merge_all` then calls with the study appended; the molecular
body only where the continuum body holds none of `geometry.pore`, `inputs.profile` and `inputs.mesh` (AP2). The permittivities from
`load_corrections` of `io/case.py:Electrolyte`'s default `parameters`, its `dielectrics`. `_checked_write` builds a case for `molecular` only;
`_built_stages` keeps its stamp.

> **Outcome — item 5.** The `auto` wall is `min(0.05 nm, λ_D/5)`, so below about 1.5 M a study keys stage 6 as the model
> built alone does; the test pairs 0.15 M with 3 M. A continuum model that supplies `inputs.mesh` reads no molecular model
> either. The store's clean-up keeps a build's stored stages only: a forecast of the quickstart's built mesh, never stored,
> failed `test_store.py`'s clean-up test.

**Item 6.** `io/case.py:MeshSizes`, four `float | None` fields, `gt=0`, finite; `Mesh.sizes` defaults to it.
`case_sizes(document)` is `SIZES` with each typed field and `global_nm` from `maxh_nm` replaced; `idealised_recipe`,
`generate` and `MeshStage._sizing` read it, scaled by `size_scale`.

**Item 8.**
- `ToolModel`: `kind`, `name`, `project`, `states()`, `build(upto)`, `cancel()`, `refusal()`, `problem()`,
  `running_stage()`, `dismiss()`. Builds stop at `contour` (Protein geometry, Contour), `region` or `mesh`.
- Routes `/continuum/geometry`, `contour`, `region`, `mesh`, each `Route("continuum", "plane")`; screens `c-<id>`;
  `last_tool` per suite. Protein geometry draws stage 2's section, stage 3's mean, `cn_variance` or `raw_variance`,
  stage 4's loop and probe radius, and shows the point group as Prepare's. Region sets the membrane's thickness and
  centre, the reservoir's radius, the exclusion offset, or the pore's radius. Mesh sets the backend, the scale and the
  part table, typed and scaled.
- `/api/continuum/{name}/plane?tool=…` returns `{frame, extent_nm: [r0, r1, z0, z1], layers: [{id, kind, …}]}`, `kind`
  one of `image` (a PNG address and its extent), `line`, `polygon`, `mesh` (flat `vertices_nm`, `triangles`, one value
  per triangle, a palette) and `label` (a case path, its value, its anchor).
- `nano.plane(url)`: the first call builds the canvas; later calls replace the layers and keep the view unless the
  frame changes. Events: `plane_pick {layer, index}`, `plane_move {index, r, z}`, `plane_insert {edge}`,
  `plane_delete {index}`, `plane_value {path, value}`.

> **Outcome — item 8.** The build machinery `MolecularModel` held moved to `gui/web/builds.py`'s `BuiltModel`, which
> both models subclass and `ToolModel` describes; a queue entry names its suite, so a Continuum build marks Continuum. The
> pane split the same way: `tools.py`'s generic `_Pane` and its Molecular subclass, `continuum_tools.py`'s Continuum one,
> kept apart from `continuum.py` so the import guard reads no NiceGUI there. A tool whose stage a supplied outline drops
> builds nothing, and every Continuum status line names what the model is built over, so (b) finds it in every state.
> The canvas reads `plot/data.py`, a new `gui -> plot` edge recorded in `modularity-layering.yaml`. On the charged tube
> the first Continuum page draws in 1.4 s, a tool change in 0.7 to 1.3 s (1047 elements); the 23 Continuum screen loads,
> (i) and (m) run in 55 s.

**Item 9.** `render_shell.py`'s 2WCD project builds its continuum model alone; shots of each `/continuum/<id>` built,
building, refused (an isolevel stage 4 refuses) and with an unsaved edit.

> **Outcome — item 9.** Contour's edit is held per model by the server (`ContinuumModel.start_edit`, `save_edit`
> through `derive_model`), drawn editable over the outline it came from; Measure and Seed run `AssessProcess` on the
> model's build case, so an edit is measured only where the model walks stages 2 to 4. Region's labels take a value
> typed on the drawing (`plane_value`); Mesh's histogram outlines a tenth's elements. Stage 4 refuses 2WCD at isolevel
> 0.9 (the loop splits into nine). The reviewer gave 16 major and 9 minor findings, none blocking, and the critique
> 15; the canvas fixes (a halo over a picture or mesh, the legend on a panel, the view refit and *Fit*, r from the
> axis, the membrane as its open outline), the salt read from the case and the isolevel named by the refusal landed
> here, and the rest went to the author as the digest's questions. The render of 206 shots shows no page error and no
> contrast, non-text or target failure; the digest, 14 picks for 58 shots, is
> [published](https://claude.ai/artifact/BPJ8ojhCzRkresApCL5qht).

**Item 11.**

> **Outcome — item 11.** The author marked the 14 picks: 8 `keep`, 6 `change`
> ([the record](../../design/reviews/2026-11-12-continuum.md)). At the collect the author merged Contour into *Pore
> geometry*, had Region draw and select each domain now, the CAD tooling left to the sketcher, and sent the mesh's
> sizes to a brainstorm: three layouts drawn over the live 2WCD page
> ([published](https://claude.ai/artifact/Thfn4DykmSfimP6iEG5J1W)), of which the author preferred the tree of the
> mesh's parts. The tool list becomes rows in both suites, at the author's note. WB-41 records the rulings; REV-244
> carries a suite between Molecular and Continuum, the CAD tooling and subdivisions for meshing. None of REV-235's
> points was put; REV-237's `?field=` and one-line list go to item 12.

### Work items

- [x] 800581b 1. `geometry/outlines.py`, `region.py`, `pore.py`, `plot/data.py`, `mesh/ingest.py`, `mesh/generate.py`,
  `cli/building.py`, `gui/geometry.py` (D1); done when `test_idealised_pore.py` and `test_region.py` pass.
  **Executor:** main
- [x] f169b56 2. The files of Implementation details' item 2, `modularity-layering.yaml` (D2); done when tiers 1 and 2
  pass and every recorded hash is equal. **Executor:** general-purpose on Sonnet, high
- [x] 88cbe81 3. VER-61's text; VER-62's walks run by their files (D1, D2); then a compaction checkpoint. **Executor:** main
- [x] 4cc106a 4. `pipeline/checks.py`, `case.py`, `run.py`, `api/project.py`, §5.3.1's NOTEs on `inputs:` and `inputs.profile`,
  VER-55's restated NOTE (D3); done when `test_region.py` and `test_gui_geometry_2wcd.py` pass. **Executor:** main
- [x] 682cc30 5. `api/project.py`, `io/project.py`, `io/models.py`, §5.3.1's NOTE on model files (D4); done when
  `test_project.py` passes. **Executor:** main
- [x] 641758a 6. `io/case.py`, `pipeline/checks.py`, `mesh/sizing.py`, `generate.py`, `ingest.py`, VER-53, §5.2.2's and §5.3.1's
  NOTEs (D5); done when `test_mesh_sizing.py` passes, VER-62 unmoved. **Executor:** main
- [x] 7. Compaction checkpoint. **Executor:** main
- [x] 45d3f65 8. `gui/web/continuum.py`, `plane.py`, `assets/plane.js`, the frame, pages and pane, `plot/data.py:mesh_elements`,
  VER-78's text (D6, D7); done when VER-78 (a) to (d), (m) and the import guard pass. **Executor:** main
- [x] 641feae 9. The four tools drafted on 2WCD (D8, D9); `render_shell.py`; `/np-gui render shell`, `review`, `publish` (D10);
  done when the digest is published. **Executor:** main
- [x] 10. Compaction checkpoint; the author's verdicts. **Executor:** main
- [ ] 11. `/np-gui collect`; REV-235's and REV-237's points ruled or carried; the design document's rows (D10).
  **Executor:** main
- [ ] 12. The tools finished to the verdicts, with *Modified only*, `?field=` and REV-242's measure (D6 to D9); done when
  VER-78 passes. **Executor:** main
- [ ] 13. `/np-gui render shell` and `review`, each finding fixed or a `REV-nn` row; REV-170 and REV-39 `fixed`; the
  matrix rows; `current.md`. **Executor:** main

### Verification

| Test | Tier | Identifiers | Oracle and tolerance | Command |
|---|---|---|---|---|
| `tests/tier1/test_idealised_pore.py::test_ver62_a_declared_cylinder_meshes_to_the_recorded_mesh`; the golden walks | 1, 2 | VER-62 | Unmoved by items 1, 2 and 6 with no part typed | `.claude/hooks/gate.sh run`; `uv run pytest tests/tier2/test_examples_0*.py tests/tier2/test_pipeline_2wcd.py tests/tier2/test_exclusion_2wcd_walk.py` |
| `tests/tier1/test_layering.py` | 1 | VER-61 | MOD-03's row gone; the substituted import fails as a new static edge and as an upward or deferred-upward one, naming module and line | `uv run pytest tests/tier1/test_layering.py` |
| `tests/tier1/test_region.py::test_ver55_an_outline_beside_a_structure_walks_the_charge_chain_alone` | 1 | VER-55; AP1 | One each, on `prepared_2wcd` with an outline: under `epnp-ns` `selected_stages` holds structure, protonation, region, mesh and charge, not stages 2 to 4; beside `inputs.charge` refused naming both keys | `uv run pytest tests/tier1/test_region.py` |
| `tests/tier2/test_gui_geometry_2wcd.py::test_ver55_2wcd_a_null_edit_beside_its_structure_deposits_the_same_charge` | 2 | VER-55; AP1 | Null edit, structure kept: stage 5's outline bitwise; stage 6's content hash, the deposit per material and both conservation legs equal to 10⁻¹² relative; no stage 2 to 4 artefact recorded; the moved edit passes the deposit's gates | `uv run pytest tests/tier2/test_gui_geometry_2wcd.py` |
| `tests/tier1/test_project.py::test_fr39_a_continuum_model_built_alone_keys_as_a_study_at_its_salt` | 1 | FR-39; AP2 | One each: 2WCD's stages 1 to 6 built alone key as a study's at 0.15 M NaCl, exact; at 3 M stage 6 differs, stage 5 not; an idealised model builds with no molecular model; the charged tube's built model is in `kept_artefacts` | `uv run pytest tests/tier1/test_project.py` |
| `tests/tier1/test_mesh_sizing.py::test_ver53_typed_part_sizes_key_as_the_table_and_follow_the_scale` | 1 | VER-53; AP3, AP4 | One each, on the charged tube: parts typed at §5.2.2's values key as untyped, exact; `protein_nm` doubled moves stage 6's key, not stage 5's, and thins the protein's elements at `size_scale` 2 (at the tube's 5 its 1 nm band is sized by its width); at `size_scale` 2 the table holds twice the typed value; `sizes` beside `geometry.pore` refused | `uv run pytest tests/tier1/test_mesh_sizing.py` |
| `tests/tier1/test_gui_viewmodels.py::test_if09_the_view_models_import_no_qt_and_no_ngsolve` | 1 | VER-55 (restated); CON-10 | The probe adds `gui.web.continuum`, `gui.web.plane` and `nicegui` | `uv run pytest tests/tier1/test_gui_viewmodels.py` |
| `tests/tier1/test_gui_screens.py` | 1 | VER-78 (a) to (d), (m) | The Continuum pages in each state; (m): two Continuum tools build the canvas once; Molecular, Continuum, Molecular build Mol* once | `NANOPNP_REQUIRE_BROWSER=1 uv run pytest tests/tier1/test_gui_screens.py` |

### Out of scope

- Handles dragged in the (r, z) view and the canvases' keyboard pass: WP5.21 (QR-16). Refinement regions, boundary
  layers: later phases (FR-11).
- The sketcher (FR-42); a new-model action, for REV-242's two points and REV-241's PQR point.
- The Physics, Study and Analysis tools, WP5.18 to WP5.20; pairing a saved edit in a study is WP5.19's.

### Open questions

None; the round's go to the author at item 11.

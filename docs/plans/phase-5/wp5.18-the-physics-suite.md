# WP5.18 — The Physics suite

**Status: planned, not started.** Planned 13 November 2026 on `main` (`e3c5f54`). It inherits §8.2.34 AJ2 to AJ5 and
AJ8, §8.2.35 AK1 to AK3 and this plan's §8.2.41 AQ1, AQ2.

This plan belongs to [the Phase 5 plan](phase-5-workbench.md). `SPECIFICATION.md` governs. An identifier here points to
a clause and never restates it.

## In brief

**What changes.** The Physics suite starts working. Four tools edit a physics model: Equations picks the set of
equations and its switches and shows them written out; Electrolyte sets the salt, its concentration and the
corrections, drawing each correction's curve; Conditions sets the bias, the grounded side, the walls and the solids'
permittivities, drawing the pore's boundaries; Exposed values lists what a study sees first. As you ruled, each tool
shows the model inside a study you pick, so what you see is what that study runs, and picking another set of
equations sets its switches for you, with a note and Undo. The tools are drafted on the quick-start salt case, shown
to you, then finished to your verdicts.

**Cost.** About three sessions, 3 to 6 agent hours and 8 of your touches, the prototype round included. The Continuum
suite measured 2.9 agent hours and 8 touches. No new library.

**What could go wrong.** The written-out equations are a second copy of the specification's; the physics review
checks each against it. A value a study cannot run with is saved and flagged, not refused, so a study can stay broken
until its own settings are fixed, which the Study suite brings. Boundaries are drawn only once the pore's mesh is
built; until then the list stands alone. A test checks that every value shown equals what the study resolves to.

**Your call.** None for the plan: you ruled the two points. At the prototype round: the panes' layout, the curves'
look and how a boundary is picked. *Recommendation:* rule them on the drawn screens.

## Execution brief

**Scope.** The phase entry's WP5.18 with AQ1 and AQ2; REV-235's and REV-245's points that the Physics screens raise,
put at the round. **Depends on:** WP5.17 (merged, `v0.6.0-alpha.17`). **Requirements:** FR-31, FR-33, FR-34, FR-35,
FR-39; PHY-09, PHY-21; VER-56, VER-61, VER-78. **Constrained by:** AJ4, AJ5, AJ8, AK3, QR-13, CON-09, ADR-004.
**Implementing session:** Opus, high effort; sub-agents Sonnet, high. Tag `v0.6.0-alpha.18`.

**Amended when it lands:** VER-78's text; §5.3.1's NOTE on model files (AQ1, AQ2); §5.4.3's NOTE on what a model
declares (its terms); FR-31's and FR-39's matrix rows.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| D1 The suite's model | `gui/web/physics.py:PhysicsModel(BuiltModel)`, no stages and no build, its case the shown case (D2); tools `equations`, `electrolyte`, `conditions`, `exposed` at `/physics/<tool>`, panes `gui/web/physics_tools.py:_PhysicsPane`; `Tool.view` per tool, `plane` for Electrolyte and Conditions, `page` for the others, drawn beside the pane | WB-05, WB-07, WP5.17's pattern; decided by the plan |
| D2 The shown case | `Project.physics_case(name, study=None)`: the study's file less its physics-owned keys, `models.physics` naming this model; with no study, the open continuum model with its `molecular_for` model. *Shown in* lists the studies, held per model by the shell; each dropped key marked with the outlined diamond and the study's value | AQ1, ruled by the author; decided by the plan for the fallback and where the choice is held |
| D3 Writes and refusals | A value is written when valid alone (`set_value`); the shown case's refusal is a card at its field naming the study, blocking nothing; φ's order writes c's | §5.3.1's NOTE on model files; `element_orders`; decided by the plan |
| D4 A change of model | `Project.choose_physics(name, model)`: the model, each switch it does not honour set to its first honoured value, each value its declaration refuses removed, in one checked write; returns each changed path's earlier value, which *Undo* writes back | AQ2, ruled by the author; VER-56 |
| D5 Equations | `ModelDeclaration.terms`: `Term(name, clause, equation, switch)` per registered model, written from §4; the view lists the terms on or off, the fields, the corrections in force and the stabilisation; a switch the model does not honour disabled, saying why; the composer's banner | The design row; AJ4; VER-56; decided by the plan for the place |
| D6 Electrolyte | The parameter set, the ions, the concentration (blank, "No default: set the salt"), temperature, driver, a corrections table, steric, wall distance; the view: `correction_curves` of the shown case on the plot frame, against the driver or the wall distance; the validity range as a hint | The design row; WP5.09's deferral; decided by the plan |
| D7 Conditions | Bias, ground, walls (v0.6's values, the rest named later), wall charge (an idealised pore only), one permittivity per solid the pore holds; each role's text from `physics/models.py:role_conditions(model, ground)`; the view: the shown case's stored mesh by named edges, else its region | PHY-09; decided by the plan |
| D8 The plot frame | `plane.js` draws `frame: "plot"`: axes scaled apart, ticks, a legend; `line`, `band` and `rule` layers in data units | The renderer table; decided by the plan |
| D9 Exposed values | The model's list: each name and range edited, removed, a value added from its numeric fields; `Project.set_exposed(..., label=None, span=None)`; the view as a study lists it | AK3, AJ5; decided by the plan |
| D10 The round | Drafted on example 01's NaCl case in its states, reviewed, published, collected with REV-235's and REV-245's points; then finished | AJ8, ruled by the author |

### Grounding

**D1.**
- `gui/web/screens.py:SUITES` lists Physics's tools with empty ids (`_later`); `TOOL_SUITES` holds suites whose first
  tool has one; `VIEWS` maps a suite to `molecule` or `plane`, read by `tool_controls` and `pages.ROUTES`, which routes
  `/<suite>` (its last tool) and each tool with `VIEWS[suite]`. `Tool` has no `view` field.
- `gui/web/tools.py:_Pane` is generic over `BuiltModel`; `refresh_pane` reads `states()`, `problem()`, `refusal()`,
  `running_stage()`; `show_actions` draws *Build* only where `BUILDS[tool.id]` names a stage; `field` takes `text`,
  `number`, `choice`, `chains`, `list`, no boolean.
- `builds.py:BuiltModel` holds `project`, `name`, `queue`, no shell; `case()` and `problem()` read `_built_case`, which
  calls `Project.build_case`, raising `ProjectError` for `physics` (no `BUILD_UPTO` row); `_walked` and `_artefacts`
  catch `REFUSED`, which holds `KeyError`.
- `frame.py:Route.view` is `molecule`, `plane` or None, None hiding the view region; `frame.css` gives a tool pane's
  sub-page a fixed 31 rem. A sub-page with no view sets `data-screen-ready` itself (`pages.suite_page`'s `ready`).
- `io/project.py:ITEM_SUITES` sends `physics` items to the `physics` suite; `Project.changes("physics", n)` is
  `mapping_changes` of the body.

**D2.**
- On example 01's project with the charged tube imported beside it, each of the four study and physics pairings,
  the study's mapping with `models.physics` set to the absolute path and loaded by `Case.loads`, resolves in about
  10 ms; `models: {continuum, physics}` alone resolves too (probed).
- `Case.with_({"models.physics": …})` keeps the study's overrides (`ModelRecord.carried`).
- Example 01's study holds `numerics.continuation` and `outputs`, no physics value; the charged tube's physics model is
  `pnp-ns` at 1.0 M with `protein` and `membrane` permittivities.
- `io/models.py:owner_of` gives the physics model `physics`, `electrolyte`, `boundary_conditions`,
  `numerics.elements`, `numerics.stabilisation`, `numerics.wall_distance`.
- `gui/web/shell.py:Shell` holds per-window choices (`last_tool`, `changes_view`); `tools.py:current_name` gives the
  open model of a kind, else the first.

**D3.**
- `Project._checked_write` checks a physics model's leaves alone; `physics.model: pnp` is written, and the study then
  refuses at `resolve`, naming `physics.flow` (probed). `Project.problems()` reads a study by `Case.load`, so the
  switch, unread, strategy and output checks of `require_runnable` do not run there.
- `pipeline/checks.py:element_orders` refuses c's order unequal to φ's; `options_at("numerics.elements.phi")` is None;
  `_ORDERS` holds P1 to P3. `physics.solid_permittivities.<material>` is a path `set_value` writes (probed).
- `BuiltModel.refused_path` finds a path by the class's `paths` pattern.

**D4.**
- `physics/models.py:ModelDeclaration` holds `switches`, `solids`, `coefficients`, `unread`. `pnp` honours `flow`,
  `variable_density` and `inertia` false only and reads neither the viscosity and density corrections nor `u`, `p`;
  `pnp-ns` reads no correction leaf, driver or wall distance; `pb` and `pb-linear` carry no solids.
- `_check_physics_switches` reads the switches, the permittivities against `solids` and `wall_charge_C_m2` against
  `surface_charge`; `_check_unread` the `unread` leaves; `_check_strategy`, `_check_outputs` and the ladder's check the
  study's values. It also refuses `charge.dielectric_transition_nm` without `solid_fraction`, `inputs.pqr` without
  `fixed_charge` and a generated mesh without solids: the continuum's or molecular model's values, which
  `choose_physics` leaves, shown at the shown study's card (D3).
- `modularity-layering.yaml` records no `api -> physics`, `gui -> physics` or `gui -> materials` edge; `pipeline/case.py` imports
  `physics.models`, whose `case_model` imports no backend.

**D5.**
- No equation text exists in `src/`; `case_model(resolved)` gives `fields` (name, element, order, domain).
- §4's PHY-03, PHY-04, PHY-05, PHY-07, PHY-08, PHY-10, PHY-11, PHY-23 and PHY-24 state what the six registered
  models solve.

**D6.**
- `plot/data.py:correction_curves` and `CorrectionCurves` exist, fed `resolved.electrolyte` by
  `plot/figures.py:materials_figure` and tested by `test_figures.py::test_correction_curve_follows_the_declared_driver`.
- `materials/electrolyte.py:Electrolyte` holds `species` (`IonSpecies`: name, valence, `diffusivity_0`, steric
  diameter), `validity_M` and `corrections`.
- `willems2020_nacl.yaml`, the one parameter set: Na⁺ and Cl⁻, validity 0 to 5.3 M. `electrolyte.concentration_M`
  has no default and no schema bounds. `options_at` lists the parameter sets, correction models, steric models and
  drivers.
- A correction's schema default is `none`, its changed mark's default `willems2020_nacl` (`io/defaults.py:_default_of`):
  an unset correction resolves to `none`, unmarked (REV-249).

**D7.**
- `boundary_conditions` of each model maps field to boundary to text, writing `cis: phi = 0`, `trans: phi = V_bias`
  whatever the ground; `solve/state.py:single_rung` and `solve/continuation.py`'s `_potential` put φ = 0 on `ground`
  and `V_bias/V_T` on the other electrode.
- `mesh/adapter.py:MeshData` holds `vertices` in nm, `edges`, `edge_group`, `boundaries`; `edges_of(name)` returns
  `(k, 2)` vertex indices. `plot/data.py:MeshElements` (what `mesh_of` and `plane.py:_elements` return) holds no
  edges; `mesh/ingest.py:deployed_mesh(resolved, artefact)` gives a supplied mesh or the stage-6 payload as
  `MeshData`. `mesh/ingest.py:BOUNDARY_VOCABULARY` also names `analyte`, `interface`, `membrane_outer`, which no
  model's vocabulary gives a condition; cis lies at z > 0.
- `require_runnable` refuses walls other than `no_flux`, `no_slip`; `wall_charge_C_m2` is read beside `geometry.pore`
  alone.
- `gui/web/plane.py:_region_layers` draws stage 5's domains; `BuiltModel._artefacts` finds stored stages by
  `keyed_walk` of a resolved case.

**D8.**
- `assets/plane.js` (779 lines) draws the `structure` and `model` frames at equal scale, layers `image`, `line`,
  `polygon`, `domain`, `mesh`, `label`, and marks the screen ready once a drawing's layers are drawn.
- `gui/web/plane.py:Frame` is `Literal["structure", "model"]`; `Plane.json()` writes `extent_nm`, and `_bounds` reads
  `extent_nm` and `points_nm`.

**D9.**
- `Project.set_exposed(kind, name, path, on)` names an entry by its path's last part and writes no range;
  `io/models.py:exposed_values` refuses a repeated or ill-formed name, a foreign or non-numeric path and a model value
  outside the range. `_Pane.field` offers *Expose* on a number.

**D10.**
- `render_shell.py`'s groups: `states`, `2wcd`, `extra`, `compact`, `molecular`, `continuum`; `server --project` walks
  the first study to the charge. `SCREENS` drives `test_gui_screens.py`'s (a) to (d) and the `2wcd` shots.
- REV-235's points wait for "the round of a suite that needs them"; REV-245's layout, colours and words for this one.

### Implementation details

**Item 1.** `Term(name: str, clause: str, equation: str, switches: tuple[str, ...] = (), correction: str | None =
None)`, frozen, in `physics/terms.py` (RUF001 off there alone, for §4's symbols);
`ModelDeclaration.terms: tuple[Term, ...] = ()`, each registration stating its own, in Unicode text from §4's and §6's
clauses as the model assembles them, a term on where each of its `switches` is true and its `correction` leaf is not
`none`. `role_conditions(model: PhysicsModel, ground: Literal["cis", "trans"]) -> dict[str, dict[str, str]]`, by
boundary, then field: `model.boundary_conditions` inverted, the potential's `cis` and `trans` texts placed so the
`ground` boundary reads `phi = 0` and the other `phi = V_bias`.

> **Outcome — the term carries every switch it needs and a correction leaf.** One `switch` could not say that the
> inertia needs the flow too, nor that the steric flux is left out by `steric.model: none`; the physics review also
> moved the inertia and the continuity to NUM-04's assembled forms (REV-223) and put the decrement in a flux's units.
> PHY-23's two departures it found are REV-250.

**Item 2.**
- `physics_case(name, study=None) -> Case`. With `study`: the study file's mapping; every leaf outside
  `schema`, `name`, `models` and `variables` whose `owner_of` is `physics` deleted (`_delete`); `models.physics` set to
  the model's absolute path; `Case.loads(text, base=<the study's folder>, source="<study S with physics model P>")`.
  Without: `{schema, name: P, models: {continuum: C, physics: P, molecular: M}}`, absolute, C the current continuum
  model else the first, M `molecular_for(C)` and no `molecular` where `own_outline(<C's body>)` is set, as
  `_build_case`; `ProjectError` where the project holds no continuum model.
- `choose_physics(name, model) -> dict[str, FieldValue | None]`: for each of `SWITCHES` whose value (set, else the
  schema's) is not honoured, the first honoured value, removed where it equals the default; removed: each set leaf in
  `declaration(model).unread` away from its schema default (one with none is kept, as `_check_unread` keeps it), `physics.solid_permittivities` where `solids` is false,
  `boundary_conditions.wall_charge_C_m2` without `surface_charge`. One `_checked_write`; the result maps each changed
  path to its earlier value, None where unset.
- `set_exposed(kind, name, path, on, *, label=None, span=None)`: an entry `{name: label or the path's last part,
  path, range: list(span)}`, `range` only with `span`; an existing entry for the path is replaced.
- `io/models.py:exposable_paths(kind)`, public, the kind's paths of today's `_exposable_paths`.
- `pipeline/checks.py`: `ELEMENT_LABELS = tuple(_ORDERS)`; `options_at` returns it for `numerics.elements.*`; the docs
  build regenerates the case reference that reads it.

**Item 3** (Sonnet), in `plot/data.py`, `assets/plane.js`, `gui/web/plane.py`:
1. `plot/data.py:boundary_edges(data: MeshData) -> dict[str, np.ndarray]`: per name in `data.boundaries`, its
   `(k, 2, 2)` segments in nm, `data.vertices[data.edges_of(name)]`.
2. `plane.py:Frame` gains `plot`; a plot's `Plane` holds its data extent `[x0, x1, y0, y1]` in `extent_nm` and its
   layers' coordinates in `points_nm`, both in data units, and `_bounds` returns None for it. `plane.js`: a drawing
   with `frame: "plot"` scales each axis alone, five ticks each, titled by `axes`; layers `{kind: "line", id, title,
   points_nm: [x0, y0, …], colour}`, `{kind: "band", id, title, x: [low, high]}` filled at 15% under the lines,
   `{kind: "rule", id, title, x}` dashed; a legend lists each titled layer. No pan or zoom on a plot; a change of frame
   refits.
3. `gui/web/plane.py:physics_plane(case: Case | None, store: Store, tool, *, against, pick) -> Plane`, `case` the
   shown case: Electrolyte, one `line` per curve,
   `band` the validity range, `rule` the operating driver, or the factors against the wall distance in nm with no
   band; Conditions, `deployed_mesh(resolved, <the stage-6 artefact the store holds under the case's keys, by
   keyed_walk as BuiltModel._artefacts, or None>).data`, so a supplied mesh draws too, by material and one `line`
   per role (`role-<name>`), the picked one drawn `picked`; where it raises `KeyError`, the region's domains; else a
   note naming Continuum › Mesh. A refused or absent case: no layer, a note.
4. Check: `uv run pytest tests/tier1/test_figures.py`, and a scratchpad script that imports example 01 into a
   project, walks its study to the mesh and prints both tools' layers: a `role-<name>` line per boundary of
   `role_conditions`, and a line per correction with one band and one rule.

> **Outcome — a role is drawn as segments.** A boundary is separate edges, some not joined (the membrane's two faces),
> so a role's `line` carries `segments: true`, `points_nm` holding each segment's two ends; `physics_plane` takes
> `mesh_held` as `plane()` does, which item 5's route passes through; a plot's `json()` sets `framed` false; the
> deployed mesh is cached by its stage-6 key and the case's digest, so `ingest`'s refusal is not hidden. Run on Opus
> at the author's word.

**Item 5.**
- `Tool("equations", "Equations", ("physics.model", "physics.flow", "physics.variable_density", "physics.inertia",
  "physics.dielectric_gradient_forces", "numerics.elements.phi", "numerics.elements.c", "numerics.elements.u",
  "numerics.elements.p", "numerics.stabilisation"), view="page")`.
- `Tool("electrolyte", "Electrolyte", ("electrolyte.parameters", "electrolyte.species", "electrolyte.concentration_M",
  "electrolyte.temperature_K", "electrolyte.driver"), parts=(each `electrolyte.corrections.<property>.<model |
  concentration | wall>` of the five properties, `electrolyte.corrections.steric.model`, `.a_ion_nm`, `.a_water_nm`,
  `numerics.wall_distance.sources`, `.max_distance_nm`), view="plane")`: parts, so `tool_for` finds them, drawn by
  `electrolyte_section` as one table, a row per property; `Tool.parts`' docstring says a list or a table.
- `Tool("conditions", "Conditions", ("boundary_conditions.bias_V", "boundary_conditions.ground",
  "boundary_conditions.walls.ion_flux", "boundary_conditions.walls.slip", "physics.solid_permittivities"),
  conditional=("boundary_conditions.wall_charge_C_m2",), view="plane")`; `Tool("exposed", "Exposed values",
  view="page")`.
- `Field` gains the kinds `switch` and `materials` (a row per solid); screens `p-<id>`; a page view is
  `div.tool-view` (`data-control=tool-view`), and `frame.css` widens the sub-page that holds one.
- `/api/physics/{name}/plane?tool=…&within=…&against=driver|distance&pick=…` returns `physics_plane(...).json()`.
- `PhysicsModel` gains `shown_in: str | None = None`, which the pane sets from `Shell.shown_in: dict[str, str]` (by
  model); `within()`, `shown_in` while it names a study, else the first study whose `models.physics` resolves to the
  model's file, else the first study, else None (the pairing); `_built_case` returns `physics_case(name, within())`,
  so `case()` is the shown case; `problem()`, its refusal prefixed `In study <S>: `; `paths` matches `physics`, `electrolyte`,
  `boundary_conditions` and `numerics.(elements|stabilisation|wall_distance)`; `study_values()`, the physics-owned leaves of the
  shown study's file, each field's outlined diamond with the study's value in its title; `shown(path)`, the body's
  value, else the schema's default, which the test reads.
- Equations' view, where the shown case is refused, lists the terms by the body's switches and no field. Electrolyte's
  ions are the resolved case's; the concentration's hint and the exposed list's range, where none is typed, read
  `load_corrections(<parameter set>).concentration_validity_M` (a new `gui -> materials` edge). Conditions' solids
  are the stored mesh's materials less the fluids and `exclusion`, else the keys the model sets; `walls` offers
  `no_flux` and `no_slip`, the others disabled and named as later.
- `BUILDS` gains `(None, "", "")` for the four ids; `pages.page_of` sends Physics tools to
  `physics_tools.physics_page`. `Tool.view: Literal["molecule", "plane", "page"] | None = None`, None reading
  `VIEWS[suite]`; `ROUTES` routes each tool by it, `page` as view None, which puts `tool-view` in `tool_controls`.
  `frame.py:_Frame.route` reads `/<suite>` as `/<suite>/<Shell.last_tool, else the first>`'s route, so `/physics`
  opening Equations hides the view region as `/physics/equations` does.

> **Outcome — the base pane draws the two new kinds; the model also resolves.** `_Pane` draws `switch` and `materials`
> fields, its rows from a `solids()` hook (the stored mesh's, by `plane.py:shown_solids`, else the model's keys), and the
> outlined diamond from an `aside()` hook. `PhysicsModel.resolved()` holds the shown case resolved, which the roles, the
> ions and the Equations view read. φ's order and c's are written one after the other, each valid alone. A change of
> model's note is held per model across the page's rebuild that shows it. `materials_figure` calls
> `case_correction_curves`.

**Item 6.** `render_shell.py` group `physics`: a project from example 01's case with the charged tube imported, served
by `--project`; shots of each `/physics/<id>`, a model with no concentration (`new_model`, its ions written), the
shown study refusing (`physics.model: pnp` by `set_value`), a role picked, and *Choose model*'s note.

### Work items

- [x] 2c22fa2 1. `physics/models.py` (`Term`, the six models' terms, `role_conditions`), §5.4.3's NOTE (D5, D7); done when
  `test_model_interface.py` passes; then the `physics-reviewer` reads the terms against §4. **Executor:** main
- [x] d2c9a6a 2. `api/project.py`, `pipeline/checks.py`, `modularity-layering.yaml`, §5.3.1's NOTE on model files (D2 to D4,
  D9); done when `test_physics_model.py` and `test_layering.py` pass. **Executor:** main
- [x] 0ef0d10 3. The files of Implementation details' item 3 (D6 to D8); done when its check passes. **Executor:**
  general-purpose on Sonnet, high
- [x] 4. Compaction checkpoint. **Executor:** main
- [ ] 5. `gui/web/physics.py`, `physics_tools.py`, `screens.py`, `pages.py`, `frame.py`, `tools.py`'s `Field`, `frame.css`,
  `modularity-layering.yaml`, VER-78's text (D1 to D9); done when VER-78 (a) to (d), (m) and the import guard pass. **Executor:** main
- [ ] 6. The four tools drafted on example 01 (D10); `render_shell.py`; `/np-gui render shell`, `review`, `publish`;
  done when the digest is published. **Executor:** main
- [ ] 7. Compaction checkpoint; the author's verdicts. **Executor:** main
- [ ] 8. `/np-gui collect`; REV-235's and REV-245's points ruled or carried; the design document's rows (D10); done
  when the code and review say so. **Executor:** main
- [ ] 9. The tools finished to the verdicts, with *Modified only* and `?field=`; done when VER-78 and
  `test_physics_model.py` pass. **Executor:** main
- [ ] 10. `/np-gui render shell` and `review`, each finding fixed or a `REV-nn` row; FR-31's and FR-39's matrix rows;
  `current.md`; done when the code and review say so. **Executor:** main

### Verification

| Test | Tier | Identifiers | Oracle and tolerance | Command |
|---|---|---|---|---|
| `tests/tier1/test_physics_model.py::test_fr39_a_physics_model_edited_in_the_suite_resolves_to_the_case_it_shows` | 1 | FR-39; AQ1 | On example 01's project beside the charged tube, each field of the four tools set through `set_value` or `choose_physics`; one each: every field's `shown` equals `value_at` of the resolved shown case, exact; the shown case in its own study equals the study resolved, dump and stage keys 1 to 9 exact; in the other study its physics-owned values are this model's, and a bias the study sets (written into its YAML; no API sets a study's value before WP5.19) is left out and listed | `uv run pytest tests/tier1/test_physics_model.py` |
| `tests/tier1/test_physics_model.py::test_ver56_choosing_a_model_leaves_no_value_its_declaration_refuses` | 1 | VER-56; AQ2 | For each registered model, chosen from example 01's and the charged tube's physics models, one each: every switch honoured; no unread leaf off its default; no permittivity without solids; no wall charge without surface charge; the earlier values written back by `set_value` restore the body, mapping equal; ePNP-NS and PNP-NS chosen, the shown study resolves | as above |
| `tests/tier1/test_physics_model.py::test_fr39_an_exposed_value_named_and_ranged_reads_back` | 1 | FR-39; AK3 | A renamed, ranged entry reads back through `exposed_values` with its unit and the model's value | as above |
| `tests/tier1/test_model_interface.py::test_ver56_every_registered_model_states_its_terms` | 1 | VER-56 | Each registered model states a term or more, each naming a PHY or NUM clause §4 or §6 defines, only switches of `SWITCHES` it honours true and only a correction leaf it reads | `uv run pytest tests/tier1/test_model_interface.py` |
| `tests/tier1/test_model_interface.py::test_phy09_the_grounded_electrode_reads_zero_potential` | 1 | PHY-09 | One each for `cis` and `trans`: the ground reads `phi = 0`, the other `phi = V_bias`, the other fields' texts unmoved | as above |
| `tests/tier1/test_gui_viewmodels.py::test_if09_the_view_models_import_no_qt_and_no_ngsolve` | 1 | CON-10 | The probe adds `gui.web.physics` | `uv run pytest tests/tier1/test_gui_viewmodels.py` |
| `tests/tier1/test_gui_screens.py` | 1 | VER-78 (a) to (d), (m) | The Physics pages in each state; (m), in `charged-tube`: Continuum's Region, then Physics's Electrolyte and Conditions, and back, build the canvas once and Mol* once | `NANOPNP_REQUIRE_BROWSER=1 uv run pytest tests/tier1/test_gui_screens.py` |

### Out of scope

- The composer (FR-40), its own phase (AJ4); walls other than no-flux and no-slip, which no release schedules.
- A new-model action, with REV-242's ruling and REV-249; the guided route's card at the salt step, WP5.21.
- A study's own values (continuation, outputs) and its overrides, WP5.19; handles and the canvas's keyboard pass,
  WP5.21.

### Open questions

None; the round's go to the author at item 8.

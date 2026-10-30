# WP57 — An idealised pore as geometry, and the Python interface rebuilt on a Case and a Session

**Status: planned, not started.** Written 30 October 2026, re-planned the same day after §8.2.23 and
grounded in the code at `ec2a266` (§8.2.15 Q1). Inherits §8.2.21 W4 and W7, §8.2.22 X1 to X8,
§8.2.23 Y1 to Y11, the test scope (§8.2.13 N1 to N6) and FR-30's figures (§8.2.14, §8.2.20). Its
plan carries no word or decision cap and keeps its compaction checkpoints (Y11).

The [Phase 4 plan](phase-4-polish-and-user-testing.md) owns the phase. `SPECIFICATION.md` governs;
where this plan and it disagree, this plan is wrong. Identifiers are pointers, never restatements.

## In brief

The testing sessions found that a cylindrical pore's shape and mesh were set by one command that
ignored the case file's mesh settings, and that the Python interface sat on top of the program
instead of being its front door.

**What changes.** A cylinder is described in the case file and meshed like any other pore; the old
command goes. The pore wall can carry a fixed surface charge, checked against two textbook results.
In Python, a case is one object built from named, checked parts and edited by copy; a session runs,
sweeps and reopens it, and the command line, the window and the sweep runner all run through it.
Figures are drawn from what a run returns. Open review notes are cleared.

**Cost.** About three weeks. The checks before each push grow by about a minute.

**What could go wrong.** The recorded reference numbers could shift; a measurement shows the new
route makes the same mesh, and a test holds it there. Scripts using the old names break; each break
is listed with its replacement. A notebook could break; each runs nightly.

**Your call.**
- Keep the old command's lighter mesh smoothing, so every recorded number stays?
  *Recommendation:* yes; heavier smoothing moves every number for no gain.
- Read every file a case names beside the case file, as correction files already are?
  *Recommendation:* yes; a case then runs the same from any folder.

## Execution brief

Scope: the Phase 4 plan's WP57 entry; §8.2.21 W4, W7; §8.2.22 X1 to X8; §8.2.23 Y1 to Y11; UT-02,
UT-10; `MOD-11`; REV-111, REV-120, REV-122, REV-144, REV-145, REV-153, REV-155, REV-157. Depends on
WP56, merged at `e775c29`. Claims VER-32 (the geometry command), VER-77 (new), NUM-29's force-surface
NOTE, §5.3.1's NOTEs on a correction file read by path and on a relative path, and IF-01's NOTE on the
shape of the interface; keeps VER-25, VER-44, VER-45, VER-61, VER-62 and VER-65 green. Tag
`v0.5.0-alpha.23`.

This plan's commit amends §5.1 (the `api/` module, D7) and §5.3.1 (a NOTE on a relative path, D12). The earlier commits of this PR amended §5.3.1 (`geometry.pore`,
`numerics.mesh.maxh_nm`, a correction file by path), §5.2.2 (an idealised pore's size field), IF-02's
generators NOTE, IF-01 and its NOTEs, §5.3.2's workspace sentence and §5.5 (§8.2.22, §8.2.23).

Implementing session: Sonnet, high effort. Breaks, each listed in `CHANGELOG.md` with its migration:
`nanopnp mesh cylinder`; the names of Y5 leaving `PUBLIC` (`run_case`, `run_document`, `resolve`,
`load_case`, `loads_case`, `dump_case`, `dumps_case`, `CaseDocument`, `plan_from_document`,
`run_plan`, `Stage`, `registered_stages`) and `mesh_cylinder`; `Case`'s store, `write`, `run` and
`"debye"` wall; `nanopnp.sweep.sweep`; the `SolveHook` protocol (a new method); the case schema's
three new keys and its JSON Schema's definition titles under `nanopnp/case/v0.5`; a relative path in
a case read beside the case file (D12).

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| D1 The idealised region (stage 5) | `io/case.py` gains `Pore(shape: Literal["cylinder"], radius_nm: float > 0)` as `Geometry.pore: Pore \| None = None`. A new `geometry/pore.py` holds `CylinderPore`, the faces and edge naming moved out of `mesh/primitives.py:CylindricalPoreGeometry` (which keeps its API and delegates), and `IdealisedRegionRecord` (schema `nanopnp/region/v0.5`, key `pore` present). `RegionStage` builds it when `resolved.pore` is set: key parameters `pore`, `membrane`, `reservoir`, `constants`, inputs `{}`. `read_region` returns `RegionRecord \| IdealisedRegionRecord` and every reader branches on the type. `pipeline/checks.py` refuses as §5.3.1's `geometry.pore` NOTE lists | X1; §5.3.1's NOTE. Moved, not imported, to keep VER-61's `upward` list empty (Grounding D1) |
| D2 The idealised size field (stage 6) | `numerics.mesh.maxh_nm: float \| None = None`, read only beside `geometry.pore`. A new `mesh/idealised.py:mesh_idealised(record, *, maxh_nm, wall_h_nm) -> MeshData` meshes `CylinderPore.shape(wall_h_nm=…)` with `GenerateMesh(maxh=…, grading=0.2, optsteps2d=3)`, nothing else. `mesh/generate.py:generate` calls it for an `IdealisedRegionRecord`, with `maxh_nm` (or `SIZES.global_nm`) and the resolved wall size, each times `size_scale`; the stage-6 recipe is `idealised_parameters`. The mouths are named `interface` in the shape, so the mesh carries no `default` group | §5.2.2's NOTE; it reproduces VER-62's recorded mesh bit for bit (Grounding D2), so X4's re-pin should not be needed. `optsteps2d` 3 is the first Your call |
| D3 The commands | `nanopnp geometry cylinder [--pore-radius-nm 2] [--membrane-thickness-nm 6] [--reservoir-radius-nm 10] --out FILE.yaml` writes an `IdealisedRegionRecord` through stage 5's builder and prints the case's `geometry:` block. `nanopnp mesh SOURCE [--maxh-nm] [--wall-h-nm] --out FILE.msh`: SOURCE `reference` is the preset and refuses either flag (exit 2); any other SOURCE is a geometry file, meshed by `mesh_idealised` at 4 and 0.35 nm by default, gated and written as today; a structure's region file exits 2. `nanopnp plot FILE.yaml --out` draws a region file. `mesh cylinder`, `mesh/cylinder.py` and `PUBLIC["mesh_cylinder"]` go. The supplied-mesh remedy names `nanopnp mesh <geometry file> --wall-h-nm` | X1, X2; IF-02's generators NOTE; VER-32 |
| D4 The examples and sessions | Examples 01 to 04 and sessions 01 to 03 and 05 declare `geometry.pore` with `numerics.mesh: {maxh_nm: 4, wall_h_nm: 0.35}` and the old generator's geometry (2, 6, 10 nm), and drop their `mesh cylinder` step. Example 04's tour runs through a `Session` (D7), edits `maxh_nm` where it swapped a mesh file, and shows a byte-identical copy of a supplied mesh keeping its key | X2, X4. The four VER-62 walks keep mesh `546c34f4…`; a moved hash takes X4's gate, reported in the PR |
| D5 The wall surface charge | `BoundaryConditions.wall_charge_C_m2: float = 0.0`. `"surface_charge"` joins `physics/models.py:COEFFICIENTS`; `CoupledModel` already takes it, `ElectrostaticModel` and `PoissonModel` gain `surface_charge`/`surface_charge_boundary` through `physics/poisson.py:surface_charge_source`, and `physics/pb.py:solve_pb_recorded` uses that function in place of its own term. `solve/state.py:ladder` passes `surface_charge_C_m2`; `single_rung` passes the scaled charge where the model declares the coefficient. Zero passes nothing. Recorded in the case's provenance, not as a deviation | X3; PHY-09's NOTE ("added once to the one expression"); VER-77 |
| D6 The `Case` | The schema's root stays `io/case.py:CaseDocument`, internal: `io` is the base layer and `Case.load` checks the registries above it. Every block drops `Spec` (`MembraneSpec` → `Membrane`, `ElectrolyteSpec` → `Electrolyte`, …); `_Strict` becomes `frozen=True`; the root's JSON Schema title is `Case`. A new `api/case.py:Case(CaseDocument)` adds no field and carries the methods: `load(path)`, `loads(text, *, base=None)`, `dump(path)`, `dumps()`, `__getitem__`, `with_(edits=None, /, **named)`, the presets `cylinder` and `from_structure(source, *, orient=None, structures=None, …)`, and private `_path`, `_text`, `_base` (Y3). `substitute`, `with_profile` and `with_section` build `type(document)`, so a `Case` edited stays a `Case`. A new root module `nanopnp/case.py` re-exports `Case`, `CaseValidationError` and every block. `pipeline/handle.py` is deleted | Y1, Y2, Y3, Y7; REV-144, REV-145, UT-10. A subclass is the one way to keep `io` importing only `core` (Grounding D6) |
| D7 The `Session` and its layer | A new subpackage `api/`, placed in `LAYER_ORDER` after `sweep`, holds `api/session.py:Session(store=None, *, write=True, workspace=None, overwrite_workspace=False)` with `run`, `sweep` (D8), `open`, `stages`, `register_stage` (D9). `run` walks `pipeline/run.py:run_document`, which stays internal, loses `options`, and gains `base` and `stages` (D9, D12). `run_case` is deleted; `pipeline/reproduce.py` moves to `api/reproduce.py`. The command line, the shell's solver, `reproduce`, `validation/costs.py` and `validation/geometry.py` run through a `Session`; `nanopnp stage --list` prints `Session().stages` | Y4, Y5, Y8. Above `sweep`, because `Session.sweep` calls the planner; every caller of a run sits above it (Grounding D7) |
| D8 The sweep through the Session | `session.sweep(case, *, axis, values, origin=0, workers=1, check_meshes=True) -> SweepResult` plans as `sweep/inmemory.py:sweep` did, runs and collects. The executor (`run_point`, `run_plan`, `_pool`, `_worker`, `_parent_artefact`) moves from `sweep/run.py` to `api/sweep.py`, and each member walks through the `Session`; `sweep/run.py` keeps `MemberResult`, `member_from_row`, `MEMBERS_DIRNAME`, `THREAD_VARIABLES` and `pin_threads`. `nanopnp sweep run` calls `api/sweep.py:run_plan(plan, directory, session=…)`. A sweep's members always write their run directories and take no workspace of the Session's. `workers > 1` on a Session with stages of its own is refused naming them, before any member runs. `sweep/inmemory.py` and `nanopnp.sweep`'s lazy exports go | Y4, Y6. A notebook's function cannot cross a `spawn` boundary; the dataset names member directories, so they must exist |
| D9 A stage of one's own | `session.register_stage(function, *, name=None) -> str` builds `pipeline/extension.py:FunctionStage` and keeps it in the Session's own ordered mapping; nothing enters `core/stages.py`'s registry. `run_document(stages=…)` walks own stages after every built-in one, in registration order; `selected_stages`, the walk's descriptions and `_Walk.construct` read own stages before the registry. `FunctionStage` keys `{"code": digest}` and the read artefacts' hashes. Registering again under a name on that Session replaces it | Y10; §5.5's NOTE; `MOD-11` (`register`, `StageDescription` internal); REV-155's session 04 variation |
| D10 Figures from the results, the notebooks and session 04 | `RunResult` gains `plot_field(quantity, *, zoom_nm=None \| "lumen" \| (r, z), relative=False, halfrange=None, ax=None)`, `plot_cutline(quantity, *, along="z" \| "r", at_nm=0.0, relative=False, ax=None)`, `field_choices(*, radial=True)` and `quantity_rows()`, over `plot/panels.py` and `plot/data.py`. `SweepResult` has `plot_iv(*, ax=None, annotate=True)` and `figure()`. Notebooks 01 to 06 and session 04 import only `nanopnp` and `nanopnp.case`: a `Session` runs, `Case.from_structure(name, orient=…)` builds, `session.stages` titles a tab, `figure("charge")` replaces `plot_charge` | Y6, Y7, Y8; REV-155 |
| D11 The end of a rung, and REV-157's rest | `SolveHook` gains `rung_solved(self, name: str, seconds: float, iterations: int) -> None`; `solve/continuation.py:run_ladder` takes `on_solved: Callable[[int, RungResult], None]`, called after each `RungResult`; the solve stage forwards it. `cli/__init__.py:_Progress` prints a rung's steps and seconds there; `gui/solver.py:QueueSolve` implements it as a no-op. `validation/runs.py:reopen` reads through `read_run`; `inspect` reads a run's manifest once; `Manifest.hash` is cached; `wall_distance_remedy` loses its dead branch | REV-157; W4. The printed seconds become the manifest's |
| D12 Paths read beside the case file, and a correction file by path | Every relative path a case names is taken against `base`: the directory of the case file the run read, or the working directory for a case in memory. `resolve(document, *, base=None)` makes each `SuppliedArtefact.path`, `structure.source.path`, `structure.ensemble.trajectory` and correction file absolute in `ResolvedCase`; `check_referenced_files(document, *, base=None)` checks them there. A value of `electrolyte.parameters` or `electrolyte.corrections.*.model` ending in `.yaml` is a path, resolved by `core/paths.py:correction_source(name, *, base)`; stage 8's key, the manifest's materials group and `inputs.files` record it by absolute path and hash. `input_files` records every file, the case's included, by absolute path. `Case.with_` first makes each relative path absolute against `_base`; `reproduce` loads the run's `case.yaml` with `base` the recorded case file's directory | X6; Y3; §5.3.1's NOTEs. The second Your call; the case hash keeps the paths as written, so no key moves |
| D13 The small review items | REV-120: `post/forces.py:check_force_surface(data, boundary)` refuses an edge set whose sides are not one material pair, called by `extract`. REV-153: one bulk constant shared by the model and `post/export.py`; `prepared_pore`'s digest reads `read.py` too; the triangulation cache holds weak references; the Debye wall and the mesher list go with D6 and D3. REV-155: `validation/examples.py:untagged_commands` serves the session and example tests; the rectification sentence softened. REV-111: the claim narrowed | X6 to X8 |
| D14 The surface and its records | `core/public.py:PUBLIC` after: `Case` (`nanopnp.api.case`), `Session` (`nanopnp.api.session`), `RunResult`, `SweepResult` (`nanopnp.api.sweep`), `Artefact` (`nanopnp.io.artefact`), `Store`, `orient_pore`, the five physics-model names, `Progress`, `CancelToken`, `CancelFlag`, `Cancelled` and the three hooks; the `TYPE_CHECKING` mirror in `nanopnp/__init__.py` follows. `cli/reference.py:render_api_reference` adds a `## The case schema` section, `::: nanopnp.case`, and its opening line names `from nanopnp import Session`. Every test calling `run_case`, `run_plan` or `nanopnp.sweep.sweep` moves to a `Session` | Y5; F4; IF-01's public-surface NOTE. `SweepResult` enters beside `RunResult` as the type `session.sweep` returns |

### Grounding

**D1**
- `geometry/region.py:RegionRecord` is profile-based (`profile`, `membrane: MembraneRecord` with the
  chord, `axis_split_nm`, `junction_nm`, `face_areas_nm2`, `edge_counts`, `exclusion`); `extra="forbid"`.
  `read_region` checks `schema == REGION_SCHEMA` (`io/artefact.py`, `nanopnp/region/v0.5`).
  `build_region` assembles a protein face; a cylinder has none and a different reservoir: one disc
  centred at 0 against two quarter discs centred on the mouths (`mesh/primitives.py:CylindricalPoreGeometry.faces`).
- Readers of `read_region`: `mesh/meshers.py` (`NetgenMesher.mesh`, `GmshMesher.mesh`),
  `mesh/ingest.py:MeshStage._recipe` and `_generate`, `mesh/generate.py`, `charge/stage.py:FieldStage.run`
  (only when `resolved.derives_eps_r`, which a pore case cannot set: `pipeline/checks.py:_check_profile_keys`
  refuses `charge.dielectric_transition_nm` without a structure or profile), `plot/data.py:region_drawing`,
  `gui/geometry.py` (the `region` outline view), `mesh/reference.py` (builds a `RegionRecord`).
- `RegionStage.key` reads `_profile_input`, which raises `UnsupportedCaseSection` with no structure and
  no profile; `region_parameters(membrane, reservoir, …)` dumps both blocks and `KEY_CONSTANTS`.
  `geometry/region.py:measure(shape)` returns the face areas and edge counts of any named shape.
- `pipeline/case.py:resolve` sets `membrane`/`reservoir` whenever no mesh is supplied; `ResolvedCase`
  gains `pore: Pore | None`. `pipeline/run.py:selected_stages` drops stages 1 to 4 for a case with
  no `structure:` (their `needs_section`) and keeps `region` when `generates_mesh`.
- `pipeline/checks.py:require_runnable` refuses a case with no `inputs.mesh`, no `inputs.profile` and no
  `structure:`; it must admit `geometry.pore`. `_check_generation` refuses `geometry.analyte` on a
  generated mesh and checks the membrane, reservoir and wall sizes; the new refusals go there.
  `_check_solid_permittivity_keys` knows `membrane` among `SOLID_MATERIALS`.
- `mesh/primitives.py:CylindricalPoreGeometry.name_edges` leaves the two mouth seams unnamed (netgen
  writes `default`); its tier tests and `post/indicator.py`, `geometry/analyte.py` (annotation only) keep
  using it. The layering file has `geometry → mesh` only as a `TYPE_CHECKING` edge (MOD-03),
  `upward: []`, and `mesh → geometry` static.
- A `Literal` leaf is either a switch or a configuration: `io/defaults.py:CONFIGURATION_PATHS` needs
  `geometry.pore.shape`; `validation/case_leaves.py:LEAVES` needs `geometry.pore.shape`,
  `geometry.pore.radius_nm`, `numerics.mesh.maxh_nm` and `boundary_conditions.wall_charge_C_m2`
  (VER-71's `test_case_leaves.py`); VER-76's JSON-schema leaves follow the model by themselves.

**D2**
- Measured at `e775c29` on `linux-x86_64/X86_V3`: `CylindricalPoreGeometry(2, 6, 10).shape(wall_h_nm=0.35)`
  with the mouths named `interface`, meshed at `maxh` 4, grading 0.2, gives 392 elements and content
  hash `546c34f4fb4b…`, the reference mesh of `example-01`, `example-02-*` and `example-03-charged` in
  `tests/tier2/data/number_stability.json`, with no `optsteps2d` and with `optsteps2d=3`; `optsteps2d=5`
  gives 392 elements and `129fe5b26987…`. At `maxh` 2: 419 elements, `1bcd5cb618f7…` both ways, and
  `a2e88567e399…` at 5. The wall segments measure 1.0714 × 0.35 nm on average and 1.1387 × at most,
  inside `mesh/generate.py:WALL_MEAN_BOUND` (1.15) and `WALL_MAX_BOUND` (2.0).
- `MeshData.content_hash` (`mesh/adapter.py`) covers vertices, triangles, material and boundary names;
  the old route's `{default: interface}` group gives the same canonical form as naming the seams.
- `mesh/generate.py:generate` resolves the wall (`mesh/sizing.py:resolve_wall_size`, explicit value ×
  `size_scale`, `auto` = `min(0.05, λ_D/5)` × `size_scale`), calls `mesh_region` (the mesher registry),
  writes `mesh.msh`, re-ingests it and gates the wall. `sizing_parameters` builds the structure recipe
  (`table`, `grading`, the mesher's `optsteps2d` 5, `gate`). `MeshStage._recipe` builds the key from the
  region hash, `face_areas_nm2`, `edge_counts` and that recipe; `_generate` refuses names lost or invented.
- `pipeline/checks.py:check_document` refuses an unregistered backend; `io/case.py:CaseDocument._check_supplied`
  refuses any `numerics.mesh` key away from default beside `inputs.mesh`, which covers `maxh_nm`.

**D3**
- `cli/__init__.py:build_parser` registers `mesh` with subparsers `cylinder` (geometry and mesh argument
  groups, defaults from `mesh/defaults.py`) and `reference`; `_mesh` calls `mesh/cylinder.py:generate_cylinder`
  or `ReferenceGeometry.from_fixture().generate`, then `write_gated_msh` (staging file, `apply_groups`,
  `check_quality`, `check_radii`) and prints hash, groups and an `inputs:` block. `write_gated_msh`
  moves to `mesh/idealised.py`; `mesh reference` keeps it.
- `cli/__init__.py:_plot` classifies TARGET as a sweep, a run or, for any file, a case. A region file is
  recognised by its YAML `schema`; `core.stages.draw` draws a `RegionArtefact` built around the file
  (`payload={"region": path}`) through `plot/figures.py:region_figure`.
- `PUBLIC["mesh_cylinder"]` (`core/public.py`), its `TYPE_CHECKING` mirror (`nanopnp/__init__.py`) and
  `mesh/__init__.py`'s lazy export go; `pipeline/handle.py`, their last other user, goes with D6. A
  `cli → geometry` static edge is new (`docs/project/modularity-layering.yaml`).
- `solve/state.py:wall_distance_remedy` names `nanopnp mesh cylinder --wall-h-nm` for a supplied mesh.
- VER-32's tests in `tests/tier1/test_cli.py`: `test_ver32_mesh_cylinder_writes_a_mesh_its_printed_groups_ingest`,
  `…_quality_gate_exits_four…` (via `--membrane-thickness-nm 0.01`), `…_mesh_help_imports_no_netgen`
  (parametrised on `cylinder`, `reference`); `tests/tier2/test_mesh_generators.py` covers `mesh reference`.

**D4**
- Examples 01 to 04 run `nanopnp mesh cylinder --out pore.msh` (04 also `--maxh-nm 2 --out finer.msh`);
  their cases read `inputs.mesh: {path: pore.msh, format: msh41, groups: {default: interface}}` and set
  `physics.solid_permittivities: {membrane: 3.2}`. The VER-62 test reads the manifest's
  `geometry_and_mesh.content_hash`, which a generated mesh's `GeneratedMesh.summary` records.
- `examples/04-python-api/tour.py` imports `registered_stages` and `run_case` from `nanopnp`.
  `tests/tier2/test_examples_04_python_api.py:test_ver46_a_substituted_mesh_moves_exactly_the_keys_that_read_it`
  asserts `finer` moves `mesh` and not `materials`, `renamed` moves neither; a supplied mesh is keyed by
  content (`MeshStage.artefact`) and a generated one by recipe, so the comparison is between two
  supplied copies.
- Sessions 01, 02, 03 and 05 name `mesh cylinder` in their READMEs and cases (03: `wall-0175`, `-025`,
  `-035`, `-100`); session 03's `wall-100` must still exit 4 on NUM-34, now naming `numerics.mesh.wall_h_nm`.
  `docs/guide/meshes.md` and `running.md` name `mesh cylinder`.

**D5**
- `physics/models.py:CoupledModel.residual_form` subtracts `surface_charge_source(surface_charge, …,
  definedon=mesh.Boundaries(surface_charge_boundary))`. `ElectrostaticModel.residual_form`/`solve` and
  `PoissonModel.residual_form` take no surface charge; `physics/pb.py:solve_pb_recorded` adds its own
  `measures.surface(sign * surface_charge * test, …)`.
- `solve/continuation.py:default_ladder(surface_charge_C_m2=…)` ramps it with the fixed charge in stage 4,
  scaled by `reference.scales.surface_charge_C_m2`; the PB rungs carry none. `solve/state.py:ladder` passes
  none today; `single_rung` builds `supplied` from `declaration(...).coefficients`.
- `io/resolved.py:ResolvedCase.provenance` enumerates what the manifest records and, less
  `SOLVE_IRRELEVANT_PROVENANCE`, what keys the solve; it names no surface charge. It gains
  `wall_charge_C_m2` only when nonzero (a new `ResolvedCase.wall_charge_C_m2`), so a charged wall
  misses the cache and no existing solve key moves.
- `ModelDeclaration.__post_init__` refuses a coefficient outside `COEFFICIENTS`; `_COUPLED` and `poisson`
  declare `coefficients=COEFFICIENTS`, `pb` and `pb-linear` none. `pb` declares `solids=False`, so
  `_check_physics_switches` refuses it on a generated mesh: a pore case runs a coupled model or `poisson`.

**D6**
- `io/case.py` holds the root `CaseDocument` and 30 block classes on `_Strict(BaseModel)` with
  `extra="forbid"` and no `frozen`; no module of `src/` assigns to a document's field. Twenty carry
  `Spec`. Two renamed blocks meet a name in `materials/electrolyte.py` (`Electrolyte`,
  `CorrectionChoice`): `pipeline/case.py` imports both, and takes the schema's under a module alias.
- `pipeline/case.py:load_case`/`loads_case` are `read_case`/`read_case_text` then
  `pipeline/checks.py:check_document`, which asks the physics, mesher, stabilisation and solver
  registries. `read_case`, `_validate`, `substitute`, `with_profile` and `with_section` each build
  `CaseDocument.model_validate(...)`. `dump_case`/`dumps_case` write YAML under the aliases.
- `pipeline/handle.py:Case` is a frozen dataclass of `document`, `store`, `source`, `write`; `Case.load`
  rebases every relative input path absolute (`_rebased`, `input_paths`, `_path_fields`); `cylinder`
  meshes into the store through `mesh_cylinder`; `from_structure` takes an oriented file;
  `_electrolyte` and `_debye_wall_nm` read `materials/corrections.py:load_corrections`. Its only
  importers are `sweep/inmemory.py` and the tests `test_case_handle.py`, `test_sweep*.py`.
- The manifest's `case_hash` is `CaseArtefact(document).hash`, over the document, not its text
  (`pipeline/run.py:_manifest`); `_run_key` hashes `case_hash` and the input files' digests. A rebase
  in `Case.load` would move the case hash of a command-line run, which Y3 forbids; `_base` defers it
  to the first edit.
- `structure/orient.py:prepared_pore(source, *, directory, chains, cis_end, registration_residues,
  centroid_z_nm)` writes once under `directory`, named by a digest; `core/paths.py:structure_file(name)`
  finds a shipped structure; `core/paths.py:store_root()` is `$NANOPNP_STORE` or the default store.
- `io/case_paths.py:field_at` resolves a block path too; `_model_of(field_at(p).annotation)` is not
  `None` exactly for a block. `with_section` adds only `NEUTRAL_SECTIONS` (`charge`); `gui/case_model.py`
  and `validation/modularity.py`'s `MOD-11` measure use it.

**D7**
- `validation/modularity.py:LAYER_ORDER` ends `pipeline, sweep, validation, cli, gui, nanopnp`; a
  subpackage with no place raises naming it. `docs/project/modularity-layering.yaml`'s header repeats the
  order; `upward` and `deferred_upward` are empty and only shrink. `sweep → pipeline` is static, so a
  `Session` in `pipeline` calling `sweep` would be an upward edge; `pipeline/reproduce.py` runs a case,
  so it moves up with the Session. Root modules of `src/nanopnp/` are node `nanopnp`, which already
  imports `io`, `pipeline` and `sweep`.
- `run_document` takes 15 keywords; no caller in `src/` or `tests/` passes `options`; only
  `sweep/run.py:run_point` passes `arguments` (`{"solve": {"warm_start", "cold_reason"}}`), which
  `api/sweep.py` keeps through `Session._walk(case_or_document, *, case_text, case_path, base, arguments)`.
- Callers of `run_case`: `cli/__init__.py:_run`, `_stage`, `_plot` (a case target);
  `gui/solver.py:_worker` (all four hooks, `CancelFlag` over an `Event`); `pipeline/reproduce.py:reproduce`
  (`workspace`, `write=False`, `progress`, `cancel`); `validation/costs.py` (two),
  `validation/geometry.py` (one); 169 lines in 46 test files, `tests/conftest.py` included.
  `cli/__init__.py:_plot` reads a run through `open_run`; `_stage --list` through `registered_stages`.
- `pipeline/run.py:open_run(directory, *, store)` returns a `RunResult`; `read_run` returns a
  `RecordedRun`. `RunResult` holds `directory`, `manifest`, `artefacts`, `stages`, `store`, `resolved`.
- `core/stages.py:StageDescription` carries `name`, `number`, `title`, `inputs`, `outputs`,
  `artefact_schema` and the walk's facts; `StageEntry.figure` says whether a figure is declared.
  `session.stages` returns a new frozen `api/session.py:StageInfo(name, number, title, inputs, outputs,
  schema, figure)` per stage, read from descriptions alone, so it imports no stage module (VER-25).

**D8**
- `sweep/inmemory.py:sweep(case, *, axis, values, origin, check_meshes)` refuses a relative input path,
  writes `base.case.yaml` and `sweep.yaml` into a staging directory, builds the plan, moves both under
  `store.sweep_directory(name, hash)` and returns `Sweep(plan, directory, store)`, whose `run(workers)`
  writes the plan, calls `run_plan` and returns `collect(plan, directory)`, a `SweepArtefact`.
- `sweep/run.py:_worker(plan_path, index, root, directory)` rebuilds a `Store` in a `spawn` process;
  `run_point` builds the member's document, its warm start (`_parent_artefact`, which reads
  `stored_upstream` and `SolveStage`) and calls `run_document(..., arguments=…)`, writing run
  directories (the default). `sweep/collect.py` imports `MEMBERS_DIRNAME`, `MemberResult` and
  `member_from_row` from `sweep/run.py`; `cli/__init__.py` imports `run_plan`, `run_point` and
  `THREAD_VARIABLES`.
- §5.3.4: a member is a case assembled in memory; its relative paths read against the working directory.

**D9**
- `pipeline/run.py:selected_stages(resolved, upto)` walks `core/stages.py:walk_order()` and drops a stage
  whose required input is dropped; `_walk` reads `describe(name).weight` and `.number`; `_Walk.construct`
  calls `create(name, …)`; `stored_upstream` and `offered` read the registry. `core/stages.py:register`
  refuses a duplicate name. `validation/modularity.py` asserts `with_section` and `register` stay outside
  `PUBLIC`.

**D10**
- Notebooks import `nanopnp.core.paths.structure_file`, `nanopnp.core.stages.describe`,
  `nanopnp.structure.prepared_pore` (01, 02, 06), `nanopnp.plot.data` (`field_menu`,
  `default_potential_range_mV`, `fields_lumen_nm`, `qoi_rows`, `charge_grids`), `nanopnp.plot.panels.plot_charge`,
  `nanopnp.plot` panels (03 to 06), `nanopnp.sweep.sweep` (04, 05), `nanopnp.mesh.defaults` (05);
  they run through `Case.run(upto=…, **edits)`. Session 04 imports `run_document`, `dumps_case`,
  `core.stages` (`StageDescription`, `register`, `walk_order`) and `with_section`.
- `plot/panels.py` imports no Matplotlib at module scope; `plot_field`, `plot_axial_cutline`,
  `plot_radial_cutline` take `SolutionFields` (`RunResult.fields`) and return `Axes`; `plot_iv` takes a
  sweep artefact. `plot/figures.py:charge_figure` draws `plot_charge`. `pipeline → plot` is a new static
  edge, down the order.

**D11**
- `solve/continuation.py:run_ladder` takes `on_rung` only; the `RungResult` with `seconds` is built after
  each solve. `solve/stage.py:_instrumented` builds `on_rung` from the hook. `cli/__init__.py:_Progress`
  closes a rung on the next `rung` or stage call. `tests/tier1/test_solve_hook.py:Recorder` implements
  `SolveHook`.
- `validation/runs.py:reopen` reads `run.json` through its own `_record` and `load_case`;
  `pipeline/run.py:read_run` adds the manifest-hash and case-text checks. `cli/__init__.py:_inspect`
  reads the manifest raw, then again through `read_run`; `Manifest.hash` recomputes on every call.

**D12**
- `pipeline/run.py:input_files(resolved, case_path)` records `case_path` as given and each
  `SuppliedArtefact.path` as written; stages read those paths against the working directory; no test
  or golden compares a recorded path. `pipeline/checks.py:check_referenced_files(document)` checks the
  named files exist.
- `io/case.py:CaseDocument._check_installed` refuses any name not in `core/paths.py:available_corrections()`.
  Names are resolved by `correction_file` in `materials/corrections.py:load_corrections` (which already
  takes a `.yaml` path), `materials/stage.py:MaterialsStage.key` (file hashes into the key),
  `io/manifest.py` materials group (`parameter_file_hashes`), `materials/models.py` (lookup by name),
  `pipeline/checks.py:registry_options`, `sweep/plan.py`.
- `pipeline/reproduce.py:check_inputs` re-hashes each recorded file; `reproduce` runs `run/case.yaml`.
  Other callers that resolve a case read from a file: `gui/assess.py`, `gui/render.py` (a run's
  `case.yaml`, three), `cli/__init__.py` (`_check`, `_explain`), `sweep/plan.py`.

**D13**
- `post/forces.py:_oriented_normal` fixes the sign by `n·(x − c)`; `MeshData.oriented_edges` puts the
  first material by name on the left. `QoIStage._force` calls `force_post.extract` with `ANALYTE_BOUNDARY`.
  `mesh/ingest.py:MeshVocabularyError` maps to exit 4 (`core/errors.py`).
- `post/export.py:DIRICHLET_BULK = 1.0` mirrors `CoupledModel._apply_essential`'s default bulk.
  `structure/orient.py:prepared_pore` digests the source, the choices and `orient.py`.
  `plot/data.py:field_triangulation` keeps four `(points, cells, Triangulation)` in a module list.
- `tests/tier2/test_user_testing_sessions.py:_untagged_program_lines` re-parses console fences beside
  `validation/examples.py:TAGGED_BLOCK`; no example test checks for untagged commands.
- The claims: `knowledge/07-software-stack/01-fem-backend-ngsolvenetgen.md` (MPI symbols),
  `knowledge/02-electrokinetics-background/07-ionic-current-rectification.md` (axial asymmetry).

**D14**
- `core/public.py:PUBLIC` maps 29 names to modules; `validation/modularity.py:surface` reads it and the
  `TYPE_CHECKING` mirror and reports any name in one only. `tests/tier1/test_public_api.py` holds VER-45's
  import-cost test. `cli/reference.py:API_SECTIONS` maps each `PUBLIC` module to a section of the
  generated API page and raises `KeyError` on one it lacks.
- Knowledge naming the old route: `knowledge/07-software-stack/05-gui-and-packaging.md` (`load_case`,
  `resolve`), `11-a-stages-workspace-falls-back-to-the.md` (`run_case`).

### Implementation details

**Item 1.** Drop `Spec` from each block class of `io/case.py` and every importer (`git grep -l Spec
src tests`); where a module imports `Electrolyte` or `CorrectionChoice` from `materials/electrolyte.py`
too, import the schema as `from nanopnp.io import case as schema`. `_Strict` and `CaseDocument` take
`frozen=True`; `CaseDocument` takes `title="Case"`. A test that assigns to a block builds a new one.

**Items 3–4.** `geometry/pore.py`: `CylinderPore(pore_radius_nm, membrane_thickness_nm,
reservoir_radius_nm)` with `faces()`, `name_edges(shape, *, wall_h_nm)` and `shape(*, wall_h_nm=None,
name_mouths=True)`, the bodies moved verbatim from `CylindricalPoreGeometry`; with `name_mouths`, every
edge still unnamed is named `interface`. `CylindricalPoreGeometry.shape` calls it with
`name_mouths=False`, so its meshes are unchanged. `IdealisedRegionRecord` YAML:

```yaml
schema: nanopnp/region/v0.5
pore: {shape: cylinder, radius_nm: 2.0}
membrane_thickness_nm: 6.0
reservoir_radius_nm: 10.0
face_areas_nm2: {cis: …, electrolyte: …, membrane: …, trans: …}
edge_counts: {axis: …, cis: …, interface: 2, membrane: 2, membrane_outer: …, trans: …, wall: 1}
```

`derive_idealised_region(pore, membrane, reservoir)` builds the shape, refuses a radius not below the
reservoir's, and fills the two maps by `measure`. `summary()` gives `pore`, `thickness_nm`,
`reservoir_radius_nm`, `face_areas_nm2`, `edge_counts`. `mesh/idealised.py`:
`IDEALISED_OPTIMISATION_STEPS = 3`; `idealised_parameters(wall, maxh_nm)` returns
`{"backend": "netgen", "recipe": "idealised", "wall": wall.key(), "maxh_nm": maxh_nm, "grading": GRADING,
"optsteps2d": 3, "gate": dict(GATE_CONSTANTS)}`, with `maxh_nm` already times `size_scale`.
`GeneratedMesh` gains `recipe: Mapping[str, Canonicalisable]`, which `sizing()` reports in place of
calling `sizing_parameters`, and `MeshStage._recipe` builds the same one, so key and manifest agree.

**Item 5.** `nanopnp geometry cylinder` prints `region`, `faces`, then
`geometry:\n  pore: {shape: cylinder, radius_nm: R}\n  membrane: {thickness_nm: H}\n  reservoir: {radius_nm: L}`;
`--json` the record's summary and path. `nanopnp mesh FILE` prints as today with `groups: {}`.

**Item 6.** VER-77 (a): add `mesh/primitives.py:AxialSlabGeometry(radius_nm, length_nm)`, edges `wall`
(`z = 0`), `bulk` (`z = L`), `axis`, `lateral`, domain `electrolyte`, graded to `wall`. Solve
`create("pb", …).solve(mesh, AXISYMMETRIC, boundaries=replace(DEFAULT_BOUNDARIES, potential="bulk"),
surface_charge=σ̃, surface_charge_boundary="wall")`, σ̃ = σ_s / `scales.surface_charge_C_m2`; read ζ̃ at
`(0.5 r, 0)`. (b): a case with `geometry.pore` `R` = 5 λ_D, `thickness_nm` = 10 R, reservoir 3 R,
`pnp-ns` with every correction and steric `none`, `solid_permittivities: {membrane: 0.01}`,
`bias_V: 0`, `wall_h_nm` = λ_D/5; integrate `F Σ z_i c_i` over the lumen between `|z| ≤ h/2 − max(5 λ_D, 2R)`
with the `r` weight.

**Item 8, the Case.** `api/__init__.py` has a one-line docstring and nothing else. `Case.load(path)`: `text =
path.read_bytes().decode("utf-8")`, then `loads(text, base=path.parent)` with `_path` set to the
resolved path. `loads(text, *, base=None)`: `check_document(Case.model_validate(...))` through
`read_case_text`'s schema check, `_text = text`, `_base = base.resolve()` if given. A typed block value
of `with_` replaces the block whole; a mapping is flattened into dotted leaves under its block, nested
mappings recursing into nested blocks only, each absent block created as `{}`; a leaf whose type is a
mapping (`groups`, `solid_permittivities`) takes the mapping whole; then one `substitute` and one
`check_document`. `with_` first rebases each relative path of `input_paths` and each relative `.yaml`
correction path against `_base` when set; the copy has no `_path`, `_text` or `_base`. The ambiguity
message of `field_path` adds "or pass the block as a mapping". `Case.cylinder(*, concentration_M,
bias_V, pore_radius_nm=2, membrane_thickness_nm=6, reservoir_radius_nm=10, charge=None,
parameters="willems2020_nacl", wall_charge_C_m2=0.0, maxh_nm=4.0, wall_h_nm=0.35 | "auto",
outputs=…, name="cylinder")` writes `geometry: {pore, membrane, reservoir}` and `numerics.mesh` and no
mesh. `Case.from_structure(source, *, point_group, concentration_M, bias_V, orient=None,
structures=None, chains="all", parameters=…, size_scale=1.0, outputs=…, name=None)`: `source` not an
existing file is `structure_file(source)`; `orient`, a mapping of `orient_pore`'s keywords
`chains`, `cis_end`, `registration_residues`, `centroid_z_nm` (an unknown key a `TypeError` naming
it), calls `prepared_pore(source, directory=structures or store_root() / "structures", **orient)`.
`nanopnp/case.py`'s `__all__` lists `Case`, `CaseValidationError` and every block.

**Item 8, the Session.** `Session.run(case, *, upto=None, only=False, progress=None, cancel=None,
on_stage=None, on_solve=None, on_artefact=None)` calls `run_document(case, case_text=case._text or
case.dumps(), case_path=case._path, store=self.store, workspace=…, overwrite_workspace=…,
write=self.write, …)`; item 9 adds `base=case._base` and item 11 `stages=self._own`. `Session.open(directory)`
is `open_run(directory, store=self.store)`. The command line: `_run` and `_stage` call
`Session(Store(args.store), write=False).run(Case.load(args.case), …)`; `_plot` of a case likewise, of
a run `session.open`. `gui/solver.py:_worker`: `Session(store).run(Case.load(request.case), …)` with
its four hooks. `api/reproduce.py:reproduce`: `Session(target, write=False, workspace=scratch /
"work").run(Case.loads(case_text), progress=…, cancel=…)`, `base=` the recorded case directory from
item 9. `api/sweep.py:sweep(case, *, session, axis, values, origin, check_meshes)` writes into
`session.store`; `Session.sweep` calls it until item 10. `run_case` stays until item 14.

**Item 9.** `correction_source(name, *, base)`: `name.endswith(".yaml")` → `Path(name)` if absolute
else `base / name`, `FileNotFoundError` naming the key otherwise; else `correction_file(name)`.
`resolve(document, *, base=None)` (`base` defaulting to `Path.cwd()`) checks every named file once
(`CaseValidationError` naming the key) and stores absolute paths on `ResolvedCase`, the corrections on
`correction_files: Mapping[str, Path]` (key path → file). `input_files` adds role
`electrolyte.parameters` and `electrolyte.corrections.<p>.model` for path-named files. A caller that
resolves a run directory's `case.yaml` passes the recorded case file's directory.

**Item 11.** Digest: `sha256` over canonical bytes: for a code object, `co_code`, `co_names`,
`co_varnames`, and each of `co_consts` (a nested code object recursing), joined with `repr` of
non-code constants; plus `function.__defaults__` by `repr`. `FunctionStage.run` calls
`function(**{p: inputs.require(p) for p in params})`, checks the result with
`core/hashing.py:canonical`, and returns `Artefact(f"nanopnp/stage/{name}/v1", parameters={"code":
digest}, inputs={p: a.hash for …}, summary=result)`. Description: `number` = 1 + the largest built-in
or own number, `weight` 0.01, `takes_workspace`/`takes_store`/`key_is_artefact` False, `needs_section`
None, `optional_inputs` (). `run_document(stages=…)` takes `Mapping[str, FunctionStage]`.

**Item 14.** In each test and `tests/conftest.py`: `run_case(path, store=s, upto=u, only=o,
write=w, <hooks>)` becomes `Session(s, write=w).run(Case.load(path), upto=u, only=o, <hooks>)`, with
`from nanopnp import Case, Session`; `run_plan(plan, directory, store=s, …)` becomes
`nanopnp.api.sweep.run_plan(plan, directory, session=Session(s), …)`. Then delete `run_case`, and apply D14 to `PUBLIC`, the mirror and
`API_SECTIONS`.

**Item 16.** Tour step 4: `maxh_nm` 2 walked to `mesh` and to `materials` (`finer`); then the generated
mesh's payload copied to `pore.msh` and `renamed.msh`, two cases with `inputs.mesh` and no `geometry:`
walked to both (`supplied`, `renamed`); `tour.json` records all three; the test asserts `finer` moves
`mesh` only and `renamed` equals `supplied`.

### Work items

- [x] dddbebe 1. `io/case.py` and every importer in `src/` and `tests/`: the blocks without `Spec`, frozen,
  the root titled `Case` (D6); done when `uv run pytest -m tier1` passes. **Executor:**
  `general-purpose` on Sonnet
- [x] 72cf920 2. `io/case.py`, `pipeline/checks.py`, `pipeline/case.py`, `io/resolved.py`, `io/defaults.py`,
  `validation/case_leaves.py`: the three keys, `ResolvedCase.pore`, and the refusals of §5.3.1's
  `geometry.pore` NOTE and `maxh_nm` (D1, D2, D5); done when `test_phy09_*` of *Verification* and
  `test_case_leaves.py`, `test_case_json_schema.py`, `test_case_fields.py` pass. **Executor:** main
- [x] 72cf920 3. `geometry/pore.py` (new), `geometry/region.py`, `mesh/primitives.py`, `plot/data.py`,
  `plot/figures.py`, `gui/geometry.py`, `charge/stage.py`: the idealised region in stage 5 and every
  reader (D1); done when `test_primitives.py`, `test_region.py`, `test_figures.py` pass and the code
  and review say so. **Executor:** main
- [x] 72cf920 4. `mesh/idealised.py` (new), `mesh/generate.py`, `mesh/ingest.py`: stage 6 (D2); done when
  `test_ver62_a_declared_cylinder_meshes_to_the_recorded_mesh` passes. **Executor:** main
- [x] 0189045 5. `cli/__init__.py`, `core/public.py`, `nanopnp/__init__.py`, `mesh/__init__.py`,
  `solve/state.py`, `docs/project/modularity-layering.yaml`, `tests/tier1/test_cli.py`; delete
  `mesh/cylinder.py` (D3); done when VER-32's rows pass with VER-61 and VER-65. **Executor:** main
> **Outcome — item 5.** `mesh/cylinder.py`, `PUBLIC["mesh_cylinder"]` and `mesh/__init__.py`'s export stay until item 8: `pipeline/handle.py` calls `mesh_cylinder` until the `Case` replaces it, and Tier 1 must pass at each commit. Items 2 to 4 are one commit (`72cf920`): the VER-71 stage-key probe needs stages 5 and 6 together.
- [x] 3d2a7a7 6. `physics/models.py`, `physics/pb.py`, `solve/state.py`, `mesh/primitives.py`,
  `tests/tier2/test_wall_surface_charge.py` (new): the wall charge (D5); done when VER-77's rows and
  `test_electrostatic_benchmarks.py` pass. **Executor:** main
- [x] b17e9ff 7. Compaction checkpoint. **Executor:** main
- [x] cf1b18e 8. `api/__init__.py`, `api/case.py`, `api/session.py` (new), `nanopnp/case.py` (new),
  `api/reproduce.py` (moved from `pipeline/reproduce.py`), `api/sweep.py` (moved from
  `sweep/inmemory.py`, taking the Session's store), `io/case_paths.py`, `pipeline/run.py`,
  `cli/__init__.py`, `gui/solver.py`, `validation/costs.py`, `validation/geometry.py`, `sweep/__init__.py`,
  `validation/modularity.py` (`LAYER_ORDER`), `docs/project/modularity-layering.yaml`; delete
  `pipeline/handle.py`; `tests/tier1/test_case_handle.py` → `tests/tier1/test_case.py`, new
  `tests/tier1/test_session.py`, and the tests importing `nanopnp.sweep.sweep`: the `Case` and the
  `Session`, every caller on it (D6, D7); done when the D6 and D7 rows, `test_cli.py`,
  `test_reproduce_diagnostics.py`, `test_sweep_cli.py` and VER-61 pass. **Executor:** main
> **Outcome — item 8.** `run_case` stays until item 14, so tests walk it unchanged; `run_document` lost `options` (no caller passed one). `Session.sweep` returns `api/sweep.py:Sweep` until item 10 brings `SweepResult`. `api/session.py` imports the pipeline inside its methods, which VER-72 allows for a `nanopnp` module, so `Session().stages` and `nanopnp stage --list` import no stage module. `nanopnp/case.py` is a root module: `validation/modularity.py:ROOT_MODULES` names it so `node_of` reads it as node `nanopnp`, not a subpackage `case`. A case file's relative paths are still read from the working directory until item 9, so `test_case.py` and `test_session.py` change into the example's directory. Notebooks 01 to 06, session 04 and example 04's tour still call `Case.cylinder(..., store=)` and `.run`; items 15 and 16 move them.
- [x] b77488f 9. `core/paths.py`, `io/case.py`, `pipeline/case.py`, `pipeline/checks.py`, `pipeline/run.py`,
  `materials/stage.py`, `materials/models.py`, `io/manifest.py`, `sweep/plan.py`, `api/case.py`,
  `api/session.py`, `api/reproduce.py`, `gui/assess.py`, `gui/render.py`, `cli/__init__.py`: paths
  read against the base, and a correction file by path (D12); done when the D12 rows pass.
  **Executor:** main
> **Outcome — item 9.** `resolve(document, *, base=None)` holds every named path absolute in `ResolvedCase` and refuses a missing correction file naming its key; an input file that is missing is still refused by the stage that reads it (`FileNotFoundError`), as before. A sweep member and a GUI document, both held in memory, read against the working directory (§5.3.4). `core/paths.py:reads_a_file` and `correction_source` serve stage 8, the manifest and the models; `pipeline/run.py:recorded_base` gives a recorded run its case file's directory.
- [x] 96a2a07 10. `api/sweep.py`, `api/session.py`, `sweep/run.py`, `sweep/collect.py`, `cli/__init__.py`: the
  executor through the Session and `SweepResult` (D8); done when `test_sweep_cli.py`,
  `test_sweep_plan.py` and `uv run pytest tests/tier2/test_sweep.py` pass. **Executor:** main
> **Outcome — item 10.** `api/sweep.py` holds the executor (`run_point`, `run_plan`, `_pool`, `_worker`, `_parent_artefact`) and `plan_sweep`, which plans without running; `sweep` and `Session.sweep` plan, run and collect into a `SweepResult` (`dataset`, `plan`, `directory`, `rows`). A member walks through `Session(session.store)`, so it writes its run directory and takes no workspace of the session's. `PUBLIC["run_plan"]` points at `api.sweep` until item 14 removes it. The plotting methods of `SweepResult` are item 15's.
- [x] SHA11 11. `pipeline/extension.py` (new), `pipeline/run.py`, `api/session.py`: `register_stage` (D9); done
  when the D9 row passes. **Executor:** main
> **Outcome — item 11.** An own stage is keyed by the digest of its code and defaults and the hashes of the artefacts it reads; a parameter must name a pipeline stage or one registered earlier on that Session. A sweep member walks the Session's own stages at `workers=1`; `workers > 1` is refused naming them. `RunResult.figure` of an own stage returns `None` (no figure is declared for its schema).
- [ ] 12. `core/stages.py`, `solve/continuation.py`, `solve/stage.py`, `cli/__init__.py`,
  `gui/solver.py`: the end of a rung (D11); done when the D11 row passes. **Executor:** main
- [ ] 13. Compaction checkpoint. **Executor:** main
- [ ] 14. Every test file and `tests/conftest.py` naming `run_case` or `run_plan`, then
  `pipeline/run.py` (delete `run_case`), `core/public.py`, `nanopnp/__init__.py`, `cli/reference.py`
  (D14); done when `uv run pytest` passes and `git grep -n "run_case" src tests` is empty.
  **Executor:** `general-purpose` on Sonnet
- [ ] 15. `pipeline/run.py` (`RunResult`'s four methods), `api/sweep.py` (`SweepResult.plot_iv`,
  `figure`), notebooks 01 to 06, session 04 (`notebook.py`, `selectivity.py`, `README.md`), its
  variation re-registering an edited function (D10); done when `test_notebooks.py` and the session's
  test pass. **Executor:** main
- [ ] 16. Examples 01 to 04 (cases, READMEs, `tour.py`) and `tests/tier2/test_examples_04_python_api.py`
  (D4); done when `uv run pytest --nightly tests/tier2/test_examples_0[1-4]*.py` passes with VER-62
  unchanged, or X4's gate is met and reported. **Executor:** main
- [ ] 17. Sessions 01 to 03 and 05 (READMEs, cases), `docs/guide/meshes.md`, `docs/guide/running.md`
  (D4); done when `uv run pytest tests/tier2/test_user_testing_sessions.py` passes for them.
  **Executor:** `general-purpose` on Sonnet
- [ ] 18. Compaction checkpoint. **Executor:** main
- [ ] 19. `post/forces.py`, `tests/tier1/test_forces.py`: REV-120 (D13); done when the REV-120 row
  passes. **Executor:** main
- [ ] 20. `validation/runs.py`, `cli/__init__.py`, `io/manifest.py`: REV-157's reader, single read and
  cached hash (D11); `physics/models.py`, `post/export.py`, `structure/orient.py`, `plot/data.py`:
  REV-153 (D13); done when Tier 1 passes and the code and review say so. **Executor:**
  `general-purpose` on Sonnet
- [ ] 21. `validation/examples.py`, `tests/tier2/test_user_testing_sessions.py`, the example tests:
  `untagged_commands` (D13); done when the example and session tests pass. **Executor:**
  `general-purpose` on Sonnet
- [ ] 22. The two knowledge sentences (REV-111, REV-155), the two concepts naming the old route (D14)
  and their `knowledge/log.md` lines; `CLAUDE.md`'s project structure gains `api/`; done when the code
  and review say so. **Executor:** `general-purpose` on Haiku
- [ ] 23. Records: `CHANGELOG.md` (each break with its migration), the REV rows and sections set
  `fixed`, UT-02 and UT-10 in `docs/user-testing/findings.md`, `MOD-11` in
  `docs/project/modularity-findings.md`, the Phase 4 plan's WP57 entry, `current.md`; the strict
  documentation build. **Executor:** main

### Verification

| Test | Tier | Identifiers | Oracle | Tolerance and source | Command |
|---|---|---|---|---|---|
| `tests/tier1/test_idealised_pore.py:test_ver62_a_declared_cylinder_meshes_to_the_recorded_mesh` | 1 | VER-62, X4 | Stages 5 and 6 of a `geometry.pore` case at (2, 6, 10, 4, 0.35) give the reference mesh hash of `example-01` in `number_stability.json`; `nanopnp mesh` of the same geometry file gives the same hash | Equality; D2's measurement | `uv run pytest tests/tier1/test_idealised_pore.py` |
| `…:test_phy09_a_pore_case_without_a_membrane_permittivity_is_refused` | 1 | PHY-09, PHY-20 | `CaseValidationError` naming `physics.solid_permittivities.membrane` | Exact; §5.3.1's NOTE | as above |
| `…:test_phy09_a_wall_charge_beside_no_idealised_pore_is_refused` | 1 | PHY-09 | A supplied-mesh case with `wall_charge_C_m2` refused naming the key | Exact; §5.3.1's NOTE | as above |
| `tests/tier2/test_wall_surface_charge.py:test_ver77_grahame_zeta_from_a_wall_charge_on_an_axial_slab` | 2 | VER-77 (a), PHY-09 | Grahame's ζ̃ at 0.1 M, ζ̃ = 2, on meshes λ/2, λ/4, λ/8; the opposite σ_s | Error falls with each refinement and is below 1 × 10⁻⁴ relative on the finest (VER-12's Grahame tolerance); the opposite σ_s gives −ζ̃ within 10⁻⁶ relative (NUM-16's `rtol`) | `uv run pytest tests/tier2/test_wall_surface_charge.py` |
| `…:test_ver77_gauss_balance_in_a_long_charged_lumen` | 2 | VER-77 (b) | `Q_ion = −σ_s 2πRℓ` between the two planes | 10⁻³ relative (QR-03) | as above; `slow` if over 60 s on four cores |
| `…:test_ver77_zero_wall_charge_adds_no_term` | 2 | VER-77, FR-20 | The assembled residual of a case with `wall_charge_C_m2: 0` and without the key, on one state | Equal to round-off, 10⁻¹⁴ relative in the max norm | as above |
| `tests/tier1/test_cli.py` VER-32 rows | 1 | VER-32, IF-02 | `geometry cylinder` writes a region file that `plot` draws; `mesh FILE`'s printed groups and hash are what a case's manifest records; a sliver (`--membrane-thickness-nm 0.01`) exits 4 leaving no file; `--help` of `geometry` and `mesh` imports no netgen; `mesh reference --maxh-nm 1` and a structure's region file exit 2 | Exact | `uv run pytest tests/tier1/test_cli.py` |
| `tests/tier1/test_case.py:test_fr27_a_block_edit_equals_its_leaf_edits` | 1 | FR-27 | A mapping edit equals the leaf edits; a typed block replaces the block whole; `charge={}` adds the section; the original case is unchanged and its blocks refuse assignment | Equal documents | `uv run pytest tests/tier1/test_case.py` |
| `…:test_fr25_an_unedited_loaded_case_records_its_file_and_an_edited_one_does_not` | 1 | FR-25, Y3 | `Session.run(Case.load(f), upto="case")` and `nanopnp run f --upto case` record one case hash, one case text (the file's), `inputs.files.case` = `f`; after `with_`, no `inputs.files.case`, the dumped text as the case text | Equal records | as above |
| `…:test_fr25_a_relative_input_path_is_read_beside_the_case_file` | 1 | FR-25, D12 | A case in a temporary directory naming `pore.msh` by a relative path, loaded and walked to `mesh` from another working directory, unedited and after `with_`, ingests that file; the manifest records its absolute path and the case hash of the as-written case | Exact | as above |
| `tests/tier1/test_session.py:test_ver44_session_run_passes_on_its_hooks_and_moves_no_key` | 1 | VER-44, Y4 | `Session.run` with each hook calls it and gives the artefact hashes and store entries of a run without hooks | Equal hashes | `uv run pytest tests/tier1/test_session.py` |
| `…:test_fr27_only_runs_one_stage_on_its_stored_inputs` | 1 | FR-27, Y8 | `run(case, upto="materials", only=True)` after a run to `materials` walks it alone; on an empty store it raises `MissingUpstreamError` naming the stage | Exact | as above |
| `tests/tier1/test_stages.py:test_ver25_session_stages_describe_without_importing` | 1 | VER-25, Y8 | In a fresh process, `Session().stages` lists every built-in stage with the registry's name, number, inputs and outputs, and imports no stage module (`sys.modules`) | Exact | `uv run pytest tests/tier1/test_stages.py` |
| `…:test_fr27_a_function_stage_is_keyed_by_its_code_and_its_inputs` | 1 | FR-27, QR-14 | Same function: cached; edited body: new key; re-registration on the Session replaces; a second Session neither lists nor walks it; a built-in name, an unknown parameter and a non-mapping return refused | Exact | as above |
| `tests/tier1/test_solve_hook.py:test_ver44_the_end_of_rung_call_carries_the_manifests_seconds` | 1 | VER-44 | One `rung_solved` per rung, its `seconds` and `iterations` those of the ladder record | Exact | `uv run pytest tests/tier1/test_solve_hook.py` |
| `tests/tier1/test_materials_path.py:test_fr16_a_correction_file_by_path_keys_stage_8_and_the_manifest` | 1 | FR-16, FR-25 | An edited copy moves the stage-8 key; the manifest's `inputs.files` records its absolute path and hash; the deviation is listed; a relative path resolves beside the case file | Exact | `uv run pytest tests/tier1/test_materials_path.py` |
| `tests/tier1/test_forces.py:test_num29_a_force_surface_meeting_two_fluids_is_refused` | 1 | NUM-29, QR-12 | A hand-built `MeshData` whose `analyte` edges meet `cis` and `electrolyte` is refused naming both; one pair passes | Exact | `uv run pytest tests/tier1/test_forces.py` |
| `tests/tier2/test_sweep.py`, existing rows through `Session.sweep` | 2 | FR-24, QR-06 | Unchanged oracles; members walk through the Session | Unchanged | `uv run pytest tests/tier2/test_sweep.py` |
| Examples 01 to 04, VER-62 | 2, nightly | VER-46, VER-62 | The recorded golden, every walk on its recorded mesh | 10⁻⁸ relative (VER-62) | `uv run pytest --nightly tests/tier2/test_examples_0[1-4]*.py` |

VER-61 stays green with `api` in `LAYER_ORDER` and its edges recorded, `upward` and `deferred_upward`
still empty; VER-45 and VER-65 stay green.

### Out of scope

- A structure's region meshed by `nanopnp mesh`, and the Gmsh backend for an idealised pore: refused,
  no owner until asked for.
- Other idealised shapes: `Pore.shape` admits them later.
- Running stages of one's own in a sweep's worker processes: refused (D8), no owner until asked for.
- The guide's prose for UT-02 and the API page: documentation increment 4.
- REV-121 (no package) and REV-156's question (the author's, for Phase 6).
- Public backend registration functions: REV-67, with the composer phase (§8.2.18 T3).

### Open questions

None blocking. The In brief's two calls stand as recommended unless ruled before items 4 and 8. If
the second is ruled no, D12 keeps the working directory for input files, `Case.with_` still rebases
against `_base`, and §5.3.1's new NOTE is reverted.

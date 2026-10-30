# WP57 — An idealised pore as geometry, and the Python interface designed for its user

**Status: planned, not started.** Written 30 October 2026, grounded in the code at `e775c29` (§8.2.15
Q1). Inherits §8.2.21 W4 and W7, §8.2.22 X1 to X8, the test scope (§8.2.13 N1 to N6) and FR-30's
figures (§8.2.14, §8.2.20). Exempt from the plan cap: at most 6,000 words outside its Outcomes, 2,500
of them outside Grounding and Implementation details, and ten decisions (§8.2.22 X5).

The [Phase 4 plan](phase-4-polish-and-user-testing.md) owns the phase. `SPECIFICATION.md` governs;
where this plan and it disagree, this plan is wrong. Identifiers are pointers, never restatements.

## In brief

The testing sessions found that a simple cylindrical pore was made by one command that set its
shape and its mesh together, ignoring the case file's mesh settings, and that the Python interface
exposed the program's internals.

**What changes.** A cylinder is described in the case file and meshed like any other pore, its mesh
settings read from the case and recorded. A command writes its shape to a file that can be drawn and
meshed; the old one-step command goes. The pore wall can carry a fixed surface charge, checked
against two textbook results. From Python, a run can be watched and stopped, a section of a case
edited at once, and a step of one's own written as a plain function. Open review notes are cleared.

**Cost.** About two weeks. The checks before each push grow by about a minute.

**What could go wrong.** The recorded reference numbers could shift; a measurement shows the new
route makes the very same mesh, and a test holds it there. A notebook could break; each runs nightly.
A step of one's own reading something outside its inputs could serve a stale result; the limit is
stated where its user meets it.

**Your call.**
- Keep the old command's lighter mesh smoothing, so every recorded number stays as it is?
  *Recommendation:* yes; heavier smoothing moves every number for no gain.
- Key a step of one's own by its code and inputs only? *Recommendation:* yes; nothing more can be
  checked reliably.

## Execution brief

Scope: the Phase 4 plan's WP57 entry; §8.2.21 W4, W7; §8.2.22 X1 to X8; UT-02, UT-10; `MOD-11`;
REV-111, REV-120, REV-122, REV-144, REV-145, REV-153, REV-155, REV-157. Depends on WP56, merged at
`e775c29`. Claims VER-32 (the geometry command), VER-77 (new), NUM-29's force-surface NOTE and the
§5.3.1 NOTE on a correction file read by path; keeps VER-61, VER-62 and VER-65 green. This plan's
commit amends §5.3.1 (the `geometry.pore` NOTE, `numerics.mesh.maxh_nm`, the reproduction of a
correction path), §5.2.2 (a NOTE on an idealised pore's size field), IF-02's generators NOTE and §5.5
(the NOTE on a stage of one's own, which W7 assigned to this package). Tag `v0.5.0-alpha.23`.
Implementing session: Sonnet, high effort. Breaks, each listed in `CHANGELOG.md` with its migration:
`nanopnp mesh cylinder`, `nanopnp.mesh_cylinder`, `Case.cylinder`'s mesh and its `"debye"` wall, the
`SolveHook` protocol (a new method), and the case schema's three new keys under `nanopnp/case/v0.5`.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| D1 The idealised region (stage 5) | `io/case.py` gains `PoreSpec(shape: Literal["cylinder"], radius_nm: float > 0)` as `Geometry.pore: PoreSpec \| None = None`. A new `geometry/pore.py` holds `CylinderPore`, the faces and edge naming moved out of `mesh/primitives.py:CylindricalPoreGeometry` (which keeps its API and delegates), and `IdealisedRegionRecord` (schema `nanopnp/region/v0.5`, key `pore` present). `RegionStage` builds it when `resolved.pore` is set: key parameters `pore`, `membrane`, `reservoir`, `constants`, inputs `{}`. `read_region` returns `RegionRecord \| IdealisedRegionRecord` and every reader branches on the type. `pipeline/checks.py` refuses as §5.3.1's `geometry.pore` NOTE lists | X1; §5.3.1's NOTE. Moved, not imported, to keep VER-61's `upward` list empty (Grounding D1) |
| D2 The idealised size field (stage 6) | `numerics.mesh.maxh_nm: float \| None = None`, read only beside `geometry.pore`. A new `mesh/idealised.py:mesh_idealised(record, *, maxh_nm, wall_h_nm) -> MeshData` meshes `CylinderPore.shape(wall_h_nm=…)` with `GenerateMesh(maxh=…, grading=0.2, optsteps2d=3)`, nothing else. `mesh/generate.py:generate` calls it for an `IdealisedRegionRecord`, with `maxh_nm` (or `SIZES.global_nm`) and the resolved wall size, each times `size_scale`; the stage-6 recipe is `idealised_parameters`. The mouths are named `interface` in the shape, so the mesh carries no `default` group | §5.2.2's new NOTE; it reproduces VER-62's recorded mesh bit for bit (Grounding D2), so X4's re-pin should not be needed |
| D3 The commands | `nanopnp geometry cylinder [--pore-radius-nm 2] [--membrane-thickness-nm 6] [--reservoir-radius-nm 10] --out FILE.yaml` writes an `IdealisedRegionRecord` through stage 5's builder and prints the case's `geometry:` block. `nanopnp mesh SOURCE [--maxh-nm] [--wall-h-nm] --out FILE.msh`: SOURCE `reference` is the preset and refuses either flag (exit 2); any other SOURCE is a geometry file, meshed by `mesh_idealised` at 4 and 0.35 nm by default, gated and written as today; a structure's region file exits 2. `nanopnp plot FILE.yaml --out` draws a region file. `mesh cylinder`, `mesh/cylinder.py` and `PUBLIC["mesh_cylinder"]` go. The supplied-mesh remedy names `nanopnp mesh <geometry file> --wall-h-nm` | X1, X2; IF-02's generators NOTE; VER-32 |
| D4 The examples, sessions and notebooks | Examples 01 to 04 and sessions 01 to 03 and 05 declare `geometry.pore` with `numerics.mesh: {maxh_nm: 4, wall_h_nm: 0.35}` and the old generator's geometry (2, 6, 10 nm), and drop their `mesh cylinder` step. Example 04's tour edits `maxh_nm` where it swapped a mesh file, and shows a byte-identical copy of a supplied mesh keeping its key. Notebooks 03 to 05 take `Case.cylinder` as rewritten (D6) | X2, X4. The four VER-62 walks keep mesh `546c34f4…`; a moved hash takes X4's gate, reported in the PR |
| D5 The wall surface charge | `BoundaryConditions.wall_charge_C_m2: float = 0.0`. `"surface_charge"` joins `physics/models.py:COEFFICIENTS`; `CoupledModel` already takes it, `ElectrostaticModel` and `PoissonModel` gain `surface_charge`/`surface_charge_boundary` through `physics/poisson.py:surface_charge_source`, and `physics/pb.py:solve_pb_recorded` uses that function in place of its own term. `solve/state.py:ladder` passes `surface_charge_C_m2`; `single_rung` passes the scaled charge where the model declares the coefficient. Zero passes nothing. Recorded in the case's provenance, not as a deviation | X3; PHY-09's NOTE ("added once to the one expression"); VER-77 |
| D6 `Case` designed for its user | `Case.cylinder(..., wall_charge_C_m2=0.0, maxh_nm=4.0, wall_h_nm=0.35 \| "auto")` builds a `geometry.pore` case and writes no mesh; `"debye"` becomes `"auto"`, the case's own word. `Case.with_` and `Case.run` take a mapping at a block path (`charge={}`, `inputs={"mesh": {"path": p}}`, `geometry={"pore": {"radius_nm": 3}}`), merged into the block, an absent block created, the whole validated once. `Case.run` passes on `progress`, `cancel`, `on_stage`, `on_solve`, `on_artefact` | W4, W7; REV-144, REV-145; UT-10; `with_section` stays internal |
| D7 A stage of one's own | `nanopnp.register_stage(function, *, name=None) -> str`, in a new `pipeline/extension.py`, as §5.5's NOTE states. `core/stages.py:StageEntry` gains `factory: Callable[..., Stage] \| None`; `create` uses it when set; `register` gains `replace: bool = False`, allowed only over an entry that has a factory. `FunctionStage` keys `{"code": digest}` and the read artefacts' hashes | W7; `MOD-11` (internal `register`, `StageDescription`); REV-155's session 04 variation (a re-run cell re-registers the edited function) |
| D8 The end of a rung, and REV-157's rest | `SolveHook` gains `rung_solved(self, name: str, seconds: float, iterations: int) -> None`; `solve/continuation.py:run_ladder` takes `on_solved: Callable[[int, RungResult], None]`, called after each `RungResult`; the solve stage forwards it. `cli/__init__.py:_Progress` prints a rung's steps and seconds there; `gui/solver.py:QueueSolve` implements it as a no-op. `validation/runs.py:reopen` reads through `read_run`; `inspect` reads a run's manifest once; `Manifest.hash` is cached; `wall_distance_remedy` loses its dead branch | REV-157; W4. The printed seconds become the manifest's |
| D9 A correction file by path | A value of `electrolyte.parameters` or `electrolyte.corrections.*.model` ending in `.yaml` is a path. `core/paths.py:correction_source(name, *, base) -> Path` resolves it; `pipeline/case.py:load_case(path, *, base=None)` and `resolve(document, *, base=None)` carry the base (the case file's directory, else the working directory); stage 8's key, the manifest's materials group and `inputs.files` record the absolute path and hash; `reproduce` passes the recorded case's directory | X6; §5.3.1's NOTE on a correction file outside the package. Already a deviation: both keys are in `io/defaults.py:SWITCH_PATHS` |
| D10 The small review items | REV-120: `post/forces.py:check_force_surface(data, boundary)` refuses an edge set whose sides are not one material pair, called by `extract`. REV-153: one bulk constant shared by the model and `post/export.py`; `prepared_pore`'s digest reads `read.py` too; the triangulation cache holds weak references; the Debye wall and the mesher list go with D6 and D3. REV-155: `validation/examples.py:untagged_commands` serves the session and example tests; the rectification sentence softened. REV-111: the claim narrowed | X6 to X8 |

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
  no profile; `region_parameters(membrane, reservoir, …)` dumps both specs and `KEY_CONSTANTS`.
  `geometry/region.py:measure(shape)` returns the face areas and edge counts of any named shape.
- `pipeline/case.py:resolve` sets `membrane`/`reservoir` whenever no mesh is supplied; `ResolvedCase`
  gains `pore: PoreSpec | None`. `pipeline/run.py:selected_stages` drops stages 1 to 4 for a case with
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
  `mesh/__init__.py`'s lazy export go. `pipeline/handle.py` imports `mesh_cylinder` and `mesher_identity`
  (D6 removes both uses). A `cli → geometry` static edge is new (`docs/project/modularity-layering.yaml`).
- `solve/state.py:wall_distance_remedy` names `nanopnp mesh cylinder --wall-h-nm` for a supplied mesh.
- VER-32's tests in `tests/tier1/test_cli.py`: `test_ver32_mesh_cylinder_writes_a_mesh_its_printed_groups_ingest`,
  `…_quality_gate_exits_four…` (via `--membrane-thickness-nm 0.01`), `…_mesh_help_imports_no_netgen`
  (parametrised on `cylinder`, `reference`); `tests/tier2/test_mesh_generators.py` covers `mesh reference`.

**D4**
- Examples 01 to 04 run `nanopnp mesh cylinder --out pore.msh` (04 also `--maxh-nm 2 --out finer.msh`);
  their cases read `inputs.mesh: {path: pore.msh, format: msh41, groups: {default: interface}}` and set
  `physics.solid_permittivities: {membrane: 3.2}`. The VER-62 test reads the manifest's
  `geometry_and_mesh.content_hash`, which a generated mesh's `GeneratedMesh.summary` records.
- `tests/tier2/test_examples_04_python_api.py:test_ver46_a_substituted_mesh_moves_exactly_the_keys_that_read_it`
  asserts `finer` moves `mesh` and not `materials`, `renamed` moves neither; a supplied mesh is keyed by
  content (`MeshStage.artefact`) and a generated one by recipe, so the comparison is between two
  supplied copies.
- Sessions 01, 02, 03 and 05 name `mesh cylinder` in their READMEs and cases (03: `wall-0175`, `-025`,
  `-035`, `-100`); session 03's `wall-100` must still exit 4 on NUM-34, now naming `numerics.mesh.wall_h_nm`.
  Notebook 05 offers `"debye"`; notebooks 03 and 04 pass no mesh argument. `docs/guide/meshes.md` and
  `running.md` name `mesh cylinder`.

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
- `pipeline/handle.py:Case.cylinder` meshes into `store/meshes/cylinder-<key>.msh` by `mesh_cylinder`,
  keyed by `mesher_identity()` and sets `inputs.mesh`; `_debye_wall_nm` duplicates
  `mesh/sizing.py:case_debye_length_nm` (REV-153). `Case.with_` maps names through `field_path` to
  `io/case_paths.py:substitute`, which validates each leaf with `field_at(path).validate` and sets it with
  `_set_at`, refusing an absent block. `Case.run(upto, only, **edits)` calls `run_document` with no hooks.
- `io/case_paths.py:field_at` resolves a block path too; `_model_of(field_at(p).annotation)` is not
  `None` exactly for a block. `with_section` adds only `NEUTRAL_SECTIONS` (`charge`); `gui/case_model.py`
  and `validation/modularity.py`'s `MOD-11` measure use it.

**D7**
- `core/stages.py:register` refuses a duplicate name and a target not `module:attribute`; `create`
  imports the target. `StageDescription` has twelve fields. `pipeline/run.py:_Walk.construct` creates
  each stage and `selected_stages` walks every registered stage in registration order, dropping one whose
  required input is dropped. `validation/modularity.py` asserts `with_section` and `register` stay outside
  `PUBLIC`.

**D8**
- `solve/continuation.py:run_ladder` takes `on_rung` only; the `RungResult` with `seconds` is built after
  each solve. `solve/stage.py:_instrumented` builds `on_rung` from the hook. `cli/__init__.py:_Progress`
  closes a rung on the next `rung` or stage call. `tests/tier1/test_solve_hook.py:Recorder` implements
  `SolveHook`.
- `validation/runs.py:reopen` reads `run.json` through its own `_record` and `load_case`;
  `pipeline/run.py:read_run` adds the manifest-hash and case-text checks. `cli/__init__.py:_inspect`
  reads the manifest raw, then again through `read_run`; `Manifest.hash` recomputes on every call.

**D9**
- `io/case.py:CaseDocument._check_installed` refuses any name not in `core/paths.py:available_corrections()`.
  Names are resolved by `correction_file` in `materials/corrections.py:load_corrections` (which already
  takes a `.yaml` path), `materials/stage.py:MaterialsStage.key` (file hashes into the key),
  `io/manifest.py` materials group (`parameter_file_hashes`), `materials/models.py` (lookup by name),
  `pipeline/checks.py:registry_options`, `sweep/plan.py`, `pipeline/handle.py`.
- `pipeline/run.py:input_files` builds `inputs.files`; `pipeline/reproduce.py:check_inputs` re-hashes
  each and `reproduce` runs `run_case(run/case.yaml)`.

**D10**
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

### Implementation details

**Items 2–3.** `geometry/pore.py`: `CylinderPore(pore_radius_nm, membrane_thickness_nm,
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

**Item 4.** `nanopnp geometry cylinder` prints `region`, `faces`, then
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

**Item 7.** `Case.with_`: for each edit, `path = field_path(name)`; if the value is a `Mapping` and
`_model_of(field_at(path).annotation)` is not `None`, flatten it into dotted leaves under `path` (nested
mappings recursing into nested blocks only), creating each absent block in the payload as `{}` first;
then one `substitute` of all leaves. A leaf whose type is itself a mapping (`groups`,
`solid_permittivities`) takes the mapping whole. The ambiguity message of `field_path` adds "or pass
the block as a mapping".

**Item 8.** Digest: `sha256` over `marshal`-free canonical bytes: for a code object, `co_code`,
`co_names`, `co_varnames`, and each of `co_consts` (a nested code object recursing), joined with
`repr` of non-code constants; plus `function.__defaults__` by `repr`. `FunctionStage.run` calls
`function(**{p: inputs.require(p) for p in params})`, checks the result with
`core/hashing.py:canonical`, and returns `Artefact(f"nanopnp/stage/{name}/v1", parameters={"code":
digest}, inputs={p: a.hash for …}, summary=result)`. Description: `number` = 1 + the largest registered,
`weight` 0.01, `takes_workspace`/`takes_store`/`key_is_artefact` False, `needs_section` None,
`optional_inputs` ().

**Item 10.** Tour step 4: `maxh_nm` 2 walked to `mesh` and to `materials` (`finer`); then the generated
mesh's payload copied to `pore.msh` and `renamed.msh`, two cases with `inputs.mesh` and no `geometry:`
walked to both (`supplied`, `renamed`); `tour.json` records all three; the test asserts `finer` moves
`mesh` only and `renamed` equals `supplied`.

**Item 13.** `correction_source(name, *, base)`: `name.endswith(".yaml")` → `Path(name)` if absolute
else `base / name`, `FileNotFoundError` naming the key otherwise; else `correction_file(name)`.
`resolve(document, *, base=None)` checks every named file once (CaseValidationError naming the key)
and stores absolute paths on `ResolvedCase.correction_files: Mapping[str, Path]` (key path → file).
`input_files` adds role `electrolyte.parameters` and `electrolyte.corrections.<p>.model` for path-named
files. `reproduce` passes `base = Path(files["case"]["path"]).parent`.

### Work items

- [ ] 1. `io/case.py`, `pipeline/checks.py`, `pipeline/case.py`, `io/resolved.py`, `io/defaults.py`,
  `validation/case_leaves.py`: the three keys, `ResolvedCase.pore`, and the refusals of §5.3.1's
  `geometry.pore` NOTE and `maxh_nm` (D1, D2, D5); done when `test_phy09_*` of *Verification* and
  `test_case_leaves.py`, `test_case_json_schema.py`, `test_case_fields.py` pass. **Executor:** main
- [ ] 2. `geometry/pore.py` (new), `geometry/region.py`, `mesh/primitives.py`, `plot/data.py`,
  `plot/figures.py`, `gui/geometry.py`, `charge/stage.py`: the idealised region in stage 5 and every
  reader (D1); done when `test_primitives.py`, `test_region.py`, `test_figures.py` pass and the code
  and review say so. **Executor:** main
- [ ] 3. `mesh/idealised.py` (new), `mesh/generate.py`, `mesh/ingest.py`: stage 6 (D2); done when
  `test_ver62_a_declared_cylinder_meshes_to_the_recorded_mesh` passes. **Executor:** main
- [ ] 4. `cli/__init__.py`, `core/public.py`, `nanopnp/__init__.py`, `mesh/__init__.py`,
  `solve/state.py`, `docs/project/modularity-layering.yaml`, `tests/tier1/test_cli.py`; delete
  `mesh/cylinder.py` (D3); done when VER-32's rows pass with VER-61 and VER-65. **Executor:** main
- [ ] 5. Compaction checkpoint. **Executor:** main
- [ ] 6. `physics/models.py`, `physics/pb.py`, `solve/state.py`, `mesh/primitives.py`,
  `tests/tier2/test_wall_surface_charge.py` (new): the wall charge (D5); done when VER-77's rows and
  `test_electrostatic_benchmarks.py` pass. **Executor:** main
- [ ] 7. `pipeline/handle.py`, `core/stages.py`, `solve/continuation.py`, `solve/stage.py`,
  `cli/__init__.py`, `gui/solver.py`: `Case` (D6) and the end of a rung (D8); done when the D6 and D8
  rows pass. **Executor:** main
- [ ] 8. `pipeline/extension.py` (new), `core/stages.py`, `core/public.py`, `nanopnp/__init__.py`:
  `register_stage` (D7); done when the D7 row and `test_stages.py` pass. **Executor:** main
- [ ] 9. Compaction checkpoint. **Executor:** main
- [ ] 10. Examples 01 to 04 (cases, READMEs, `tour.py`) and `tests/tier2/test_examples_04_python_api.py`
  (D4); done when `uv run pytest --nightly tests/tier2/test_examples_0[1-4]*.py` passes with VER-62
  unchanged, or X4's gate is met and reported. **Executor:** main
- [ ] 11. Sessions 01 to 03 and 05 (READMEs, cases), `docs/guide/meshes.md`, `docs/guide/running.md`
  (D4); done when `uv run pytest tests/tier2/test_user_testing_sessions.py` passes for them.
  **Executor:** `general-purpose` on Sonnet
- [ ] 12. Session 04 rewritten on `Case.run` hooks, `Case.with_` and `register_stage`, its variation
  re-registering an edited function; notebooks 03 to 05 (D6, D7); done when the session's test and
  `test_notebooks.py` pass. **Executor:** main
- [ ] 13. `core/paths.py`, `io/case.py`, `pipeline/case.py`, `materials/stage.py`, `materials/models.py`,
  `io/manifest.py`, `pipeline/run.py`, `pipeline/reproduce.py`: a correction file by path (D9); done
  when the D9 row passes. **Executor:** main
- [ ] 14. `post/forces.py`, `tests/tier1/test_forces.py`: REV-120 (D10); done when the REV-120 row
  passes. **Executor:** main
- [ ] 15. `validation/runs.py`, `cli/__init__.py`, `io/manifest.py`: REV-157's reader, single read and
  cached hash (D8); `physics/models.py`, `post/export.py`, `structure/orient.py`, `plot/data.py`:
  REV-153 (D10); done when Tier 1 passes and the code and review say so. **Executor:**
  `general-purpose` on Sonnet
- [ ] 16. `validation/examples.py`, `tests/tier2/test_user_testing_sessions.py`, the example tests:
  `untagged_commands` (D10); done when the example and session tests pass. **Executor:**
  `general-purpose` on Sonnet
- [ ] 17. The two knowledge sentences (REV-111, REV-155) and their `knowledge/log.md` lines (D10); done
  when the code and review say so. **Executor:** `general-purpose` on Haiku
- [ ] 18. Compaction checkpoint. **Executor:** main
- [ ] 19. Records: `CHANGELOG.md` (each break with its migration), the REV rows and sections set
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
| `tests/tier1/test_case_handle.py:test_case_block_mapping_edits_equal_their_dotted_paths` | 1 | FR-27 | A mapping edit equals the leaf edits; `charge={}` adds the section | Equal documents | `uv run pytest tests/tier1/test_case_handle.py` |
| `…:test_ver44_case_run_passes_on_its_hooks_and_moves_no_key` | 1 | VER-44, W4 | `Case.run` with each hook calls it and gives the artefact hashes of a run without hooks | Equal hashes | as above |
| `tests/tier1/test_solve_hook.py:test_ver44_the_end_of_rung_call_carries_the_manifests_seconds` | 1 | VER-44 | One `rung_solved` per rung, its `seconds` and `iterations` those of the ladder record | Exact | `uv run pytest tests/tier1/test_solve_hook.py` |
| `tests/tier1/test_stages.py:test_fr27_a_function_stage_is_keyed_by_its_code_and_its_inputs` | 1 | FR-27, QR-14 | Same function: cached; edited body: new key; re-registration replaces; a built-in name, an unknown parameter and a non-mapping return refused | Exact | `uv run pytest tests/tier1/test_stages.py` |
| `tests/tier1/test_materials_path.py:test_fr16_a_correction_file_by_path_keys_stage_8_and_the_manifest` | 1 | FR-16, FR-25 | An edited copy moves the stage-8 key; the manifest's `inputs.files` records its absolute path and hash; the deviation is listed; a relative path resolves beside the case file | Exact | `uv run pytest tests/tier1/test_materials_path.py` |
| `tests/tier1/test_forces.py:test_num29_a_force_surface_meeting_two_fluids_is_refused` | 1 | NUM-29, QR-12 | A hand-built `MeshData` whose `analyte` edges meet `cis` and `electrolyte` is refused naming both; one pair passes | Exact | `uv run pytest tests/tier1/test_forces.py` |
| Examples 01 to 04, VER-62 | 2, nightly | VER-46, VER-62 | The recorded golden, every walk on its recorded mesh | 10⁻⁸ relative (VER-62) | `uv run pytest --nightly tests/tier2/test_examples_0[1-4]*.py` |

VER-61 and VER-65 stay green with the layering file's new `cli → geometry` row.

### Out of scope

- A structure's region meshed by `nanopnp mesh`, and the Gmsh backend for an idealised pore: refused,
  no owner until asked for.
- Other idealised shapes: `PoreSpec.shape` admits them later.
- The guide's prose for UT-02 and the API page: documentation increment 4.
- REV-121 (no package) and REV-156's question (the author's, for Phase 6).
- Public backend registration functions: REV-67, with the composer phase (§8.2.18 T3).

### Open questions

None blocking. The In brief's two calls stand as recommended unless ruled before items 3 and 8.

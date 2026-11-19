# WP5.20 — The meso suite

**Status: planned, not started.** Planned 19 November 2026 on `main` (`dbe34da`). It inherits AJ8, AN7, AP1, AP2,
AR8, AS1 and AS3, and this plan's AT1 and AT2 (§8.2.34 to §8.2.44).

This plan belongs to [the Phase 5 plan](phase-5-workbench.md). `SPECIFICATION.md` governs; an identifier points to a
clause.

## In brief

**What changes.** A sixth suite sits between Molecular and Continuum. It shows how the molecule becomes the pore's
shape and charge, each picture beside the molecule cut open along its axis. *Density* shows the smeared atoms
and their average around the axis. *Outline* shows the pore's outline, which you edit: the molecule marks the
residues your edit moves into the water or into the protein. *Charge map* shows the charge on the mesh and its checks.
A residue picked on the molecule is found on the map; a point on the map names its residue once, not per chain. As you ruled, the round also shows a working overlay of the charge in 3D and its average around the axis. The
three tools leave Continuum and Study, which keep the rest.

**Cost.** About six sessions, 7 to 12 agent hours and 15 of your touches, with the 2WCD round. The Study suite took 7.2
agent hours and 18 touches in six sessions. No new library.

**What could go wrong.** A moved tool could move a stored result; no key changes, and the stored-fingerprint
tests check it. A value could open the wrong suite; a problem or a change is now routed by the value,
not the model. The overlay could cost more than estimated; it stays a draft until you keep it.

**Your call.** At the round: the suite's name, the pair's layout at 1280 px, the residues as a strip or a table, the
outline's radius plot and vertex list, and the overlay. *Recommendation:* rule them on the drawn screens; *Meso* as
the name, your word, naming a scale as its neighbours do.

## Execution brief

**Scope.** The phase entry's WP5.20 with AT1 and AT2; REV-259; REV-244's radius against z and vertex list; REV-240's
overlay; REV-261's charge-screen points. **Depends on:** WP5.19 (merged). **Requirements:** FR-27, FR-31, FR-33,
FR-39; VER-60, VER-62, VER-78. **Constrained by:** AJ8, AN7, AP1, AP2, AR8, QR-13, CON-09, ADR-004.
**Implementing session:** Opus, high; sub-agents Sonnet, high. Tag `v0.6.0-alpha.20`.

**Amended when it lands:** FR-31 and its matrix row; FR-33's matrix row; §2's v0.6 row; §8.1's Phase 5 deliverable and
exit row; §3's `nanopnp gui` sentence; VER-78 (a), (m); VER-60's restated NOTE; the design document's areas,
organisation, tools, *Tabs or areas* rows Q14 to Q20 and Q24 to Q30, glossary, WB-34 and WB-41, and a WB row for the
round.

### Decisions

| Decision | Choice | Why/source |
|---|---|---|
| D1 The suite | Id `meso`, title *Meso* until the round names it; Build group, second; tools `density`, `outline`, `charge` at `/meso/<tool>`, each `view="pair"`; `gui/web/meso.py:MesoModel`, `gui/web/meso_tools.py`. Pore geometry leaves Continuum (Region first); Charge on the mesh leaves Study. Shortcuts follow the bar | AR8, AS1, AS3, AN7; decided by the plan |
| D2 The model and its pick | Every meso tool edits the continuum model, over the molecular model `Project.molecular_for` names; the pane's pick is Continuum's *Built over*, one choice for both suites | AR8, AP2; decided by the plan |
| D3 Routing | `Suite.edits` names the item kind a suite's tools edit; `screens.place(kind, path)` finds the suite and tool whose pane holds a path among those editing that kind; `open_field`, `refusals` and `_Pane.tool_of` use it. `_Pane` names its suite and its model's kind apart | Decided by the plan |
| D4 Charge map's build | `Project.charge_case(name)`: the continuum model over its molecular model and the build layer, to `charge`, the molecular model layered under a supplied outline too; an idealised pore or a supplied mesh deposits none, said in the pane. A `charge` build writes its record under the store's `runs/`; `kept_artefacts` keys each continuum model's charge case. The study graph's charge node opens Charge map with the study's pair picked | AR8, AP1, AP2; decided by the plan |
| D5 A residue once | `plot/data.py:ResidueCopies` from stage 1's header: under C<sub>n</sub>, n ≥ 2, the chains at one position of their units are copies (FR-03). `ResidueCharges.at` sums a residue's copies under its first unit's key; `residues()` lists it once, its charge per copy and its count; `markers` and `copies` give every copy. Under C1, or without stage 1, each chain's residue stands alone | REV-259's physics point; decided by the plan |
| D6 The atoms an edit moves | `plot/data.py:ResidueAtoms` over the protonation table's atoms, every frame, in stage 1's frame reduced to (r, z): `moved(before, after)`, the atoms inside one outline and outside the other, each way, by residue (D5); `nearest(r, z)` for Density's point, ranking residues by their atoms' distance in kernel widths, since stage 2 is a union and not a sum | AT1, ruled by the author; Density's rule decided by the plan |
| D7 The overlay | `plot/data.py:charge_volumes`: on one 3D grid in stage 1's frame, the deposit's charge density and its mean about the axis, written as OpenDX; Charge map draws each as a positive and a negative isosurface over the structure cut at the axis, each toggled. Built to the round's verdict, or removed | AT2, ruled by the author, against the recommendation; REV-240 |
| D8 The round | The three tools and the overlay on 2WCD, render group `meso`; reviewed, published, collected with REV-259's questions, REV-244's two views and REV-261's charge points; the name; then built | AJ8, AS3; REV-259 |
| D9 The old places | Each text naming a moved tool changes in the commit that moves it: the clauses of *Amended when it lands*, `render_shell.py`, `redraw.cjs` and the tests | AR8; the core's *Normativity* |

### Grounding

**D1.**
- `io/project.py:Suite` and `SUITES` list five ids; `ProjectFile.layout` is keyed by them, so an old project file loads.
- `screens.py:SUITES` drives `FRAME_CONTROLS`, `SCREENS`, `TOOL_SUITES`, `pages.ROUTES`, the activity bar and
  `commands.py`'s `Alt+Shift+<position>`; `VIEWS` and `pages.py:page_of` are written out by hand.
- Screen ids are `<suite initial>-<tool>`: `m-density`, `m-outline`, `m-charge` stay distinct from Molecular's.
- `tools.py:BUILDS` is keyed by tool id: `geometry` builds to `contour`, `charge` to `charge`.
- `continuum_tools.py:_ContinuumPane` serves three tools. Geometry's own: `outline_verdict`, `geometry_section`,
  `show_edit`, the assess and edit methods, `on_plane_insert`, `on_plane_delete`, and the `tool.id == "geometry"`
  branches of `before_fields`, `own_status`, `unbuilt`, `on_plane_pick`, `readout` and `plane_url`; `save_edit`
  navigates to `/continuum/geometry`.
- `plane.py:plane(model, tool, …)` draws geometry's layers (`_outline_layers`, `_probe`, `_edited`); `pages.py`'s
  `/api/continuum/{name}/plane` and `/image` serve them.
- `study_tools.py:_StudyPane` draws the charge tool (`show_charge`, `on_mol`, `on_point`, `select`, `start_render`,
  `scene_url`, `plane_url`); `pages.py` serves `/api/study/{name}/charge/plane`, `/charge/image`, `/residues`,
  `/structure`, `/annotation`, `/scene`.

**D2.**
- `ContinuumModel.pair` writes `built_with` through `Project.set_built_with`; `molecular_for` takes that choice, else
  the first study's molecular model, else the project's first; `ContinuumModel.molecular()` is None for an own outline.
- `_Pane.kind` is both the suite (`self.suite`, the tool links) and the model's kind (`subject`, exposed values).

**D3.**
- `frame.py:open_field` takes `ITEM_SUITES[kind]`, then `tool_for(suite, field)`; `builds.py:refusals` sets
  `Problem.suite` from `ITEM_SUITES`; `_Pane.tool_of` searches its suite, then every suite in order.
- No tool's paths hold `inputs.profile`.

**D4.**
- `Project._build_case` layers `molecular_for` only where `own_outline(body)` is None; `BUILD_UPTO["continuum"]` is
  `mesh`; `kept_artefacts` keys the `BUILD_UPTO` kinds and reads `run.json` under `runs/` and `sweeps/` only;
  `states.cap_store` cleans by it on opening.
- `geometry/region.py:_profile_identity` keys a supplied outline by its digest, so the molecular layer moves no
  stage 5 or 6 key.
- Stage 7's key reads the element order and the solids' names (`charge/stage.py:gate_parameters`, `produced_gates`)
  beside the protonation, the kernel and the mesh: built alone, it keys as a study at the build layer's physics.
- `Store(root)` without `runs=` writes a run at `<root>/runs/<name>-upto-<stage>-<short>`;
  `gui/render.py:deployed_coefficient` reads a record's `artefacts` and `store`.
- `BuiltModel.__init_subclass__` registers every subclass in `_KINDS` by `kind`; `_MODELS` holds one build per
  project, kind and name.
- `StudyModel` reads the charge (`charge_record`, `elements`, `charge_map`, `conservation`, `charges`, `pqr`, `table`);
  its `STAGES` run from `structure` to `charge`.
- `study_tools.py`'s graph navigates `node_charge` to `/study/charge`; `states.boot_project` walks the first study to
  `charge`.

**D5.**
- `plot/data.py:residue_key` is `<chain>:<resid><icode>`; `ResidueCharges.at` totals by it, so a C<sub>n</sub> point
  lists one entry per chain; `residues()` lists the first chain's; `ResidueCharges.of` reads no stage-1 artefact.
- Stage 1's header holds `n` and `chains_cyclic_order`, each a chain or a group's chains joined by `+`;
  `structure/read.py` refuses two chains at one position whose names differ at a shared number (FR-03).
- `assets/bridge.js:show(key)` selects one residue by equality; `key(loc)` is `auth_asym_id:auth_seq_id icode`.
- `ProtonationTable.positions_nm` hold every frame's atoms, hydrogens included, in stage 1's frame;
  `charge/kernel.py:source_atoms` shifts them by `frame_shift_nm`.

**D6.**
- Stage 2 is `density/union.py`'s probabilistic union, `1 − Π(1 − g)`; its atoms are the protonation table's.
- Outlines, built or supplied, are in stage 1's frame (`plane.py`'s frame `structure`; AP1).
- `ContinuumModel.outline()` gives the stored contour, else the supplied file. `ProfileEditor` keeps `vertices` and
  `parent_digest`, not its start; `from_seed` starts from a refused loop.
- `charge/dielectric.py:_inside` is an even-odd test over a grid's rows; Shapely is an extra.

**D7.**
- The vendored Mol* 5.13.1 carries MolViewSpec's `volume_representation` with `absolute_isovalue` and parses `dx`;
  `validation/apbs.py:write_dx(path, values, origin_nm, spacing_nm)` writes OpenDX in Å; `gui -> validation` is a
  layering row.
- `charge/kernel.py:volume_density` is one atom's charge density averaged about the axis.
- `molview.py:scene` writes the MolViewSpec document; `study_side_view` cuts it at the axis.

**D8.**
- `render_shell.py:GROUPS` ends with `study`; `study_project` walks the cached 2WCD project to `charge` and renders its
  elements; `c-geometry-edit` and the `refused` and `building` shots open `/continuum/geometry`.
- `redraw.cjs` opens `/study/charge` and fetches `/api/study/<s>/charge/plane` and `/residues`.

**D9.**
- `test_gui_screens.py`: the rebound-shortcut test presses `Alt+Shift+Digit4` for Study; the (m) test opens
  `/study/charge`; the two Continuum (m) tests wait for `/continuum/geometry`.
- `test_study_charge.py`'s `studied` fixture builds a `StudyModel`; `test_project.py` builds the imported charged tube's
  continuum model alone to `mesh`.
- "Five suites" stands in FR-31, §3's `nanopnp gui` sentence, §2's v0.6 row, §8.1's Phase 5 rows, the design
  document's areas, organisation and glossary, and `gui/web/glossary.py`.

### Implementation details

**Item 1.**
- `ResidueCopies.of(structure: Artefact | None)`: from the header's `n` and `chains_cyclic_order`, a map from chain
  to its first unit's chain at the same position; `group(key)` and `copies(key)`, keys as `residue_key` makes them.
  None, or n = 1, maps each chain to itself.
- `ResidueCharges.of(protonation, charge, resolved, structure=None)`. `_keys` hold group keys; `at` returns
  `(key, e_per_nm3)`, a group's value the sum over its copies; `residues()` gives `(key, name, charge_e, copies)`, the
  charge per copy the group's sum over copies; `markers(key)` every copy's atoms; `copies(key)`.
- `inside_outline(loop, r_nm, z_nm) -> bool array`: even-odd, an edge counted where `z0 <= z < z1`, as `_inside`.
- `ResidueAtoms.of(protonation, structure)`: every atom, (r, z) in nm in stage 1's frame, radius, charge, group key.
  `moved(before, after) -> Moved(out: dict[key, Count], in_: dict[key, Count])`, `Count(atoms, charge_e)` per copy;
  `markers(key)`; `nearest(r_nm, z_nm, sharpness, n=5)`: each group's least `hypot(r − r_i, z − z_i) / (sharpness ·
  radius_i)`, ascending.
- `ProfileEditor` gains `start: list[Vertex]`, set by `from_profile` and `from_seed`.

**Item 2.** `Project.charge_case(name) -> Case`: as `_build_case`, with `molecular_for(name)` layered unless the body
holds `geometry.pore` or `inputs.mesh`, which raise `ProjectError("Continuum model <n> draws its own pore; it deposits
no molecule's charge.")`; a project with no molecular model raises naming it. `kept_artefacts` adds
`_built_stages` over `charge_case` to `charge` for each continuum model whose case forms; a refusal adds nothing.

**Item 3.** `charge_volumes(table, resolved, spacing_nm=0.3) -> ChargeVolumes(origin_nm, spacing_nm, full, revolved)`
in e/nm³, `[ix, iy, iz]`, stage 1's frame: the box spans every charged atom plus four widths. `full` sums each atom's
`q/frames · π^−3/2 w^−3 exp(−|x − x_i|²/w²)` over its stencil within four widths; `revolved` sums
`q/frames · volume_density(hypot(x, y), z, r_i, z_i, w)` the same way. The widths are `source_atoms`'. The server keeps them by the protonation and charge hashes, as `study.py:_kept` does.

**Item 5.**
- `Suite` gains `edits: ItemKind | None`: molecular, continuum (Meso and Continuum), physics, study, comparison.
- `place(kind, path) -> tuple[Suite, Tool] | None`: the suites whose `edits` is `kind`, in bar order, the first tool
  holding the path. Density's fields are `geometry.density.*`; Outline's `geometry.contour.*`, conditional
  `inputs.profile`; Charge map's none.
- `BUILDS`: `density` to `symmetry`, *Build density*; `outline` to `contour`, *Build outline*; `geometry` removed.
- `_Pane.kind` stays the suite; `_Pane.holds: ClassVar[ModelKind]` names the model, read by `subject` and exposed
  values. `subject` reads "Continuum model <c>, over molecular model <m>".
- `__init_subclass__` registers a class only where `"kind" in cls.__dict__`.

**Item 6.**
- `MesoModel(ContinuumModel)`: `stages` = `study.STAGES`, `upto = "charge"`, `_built_case` from `charge_case`;
  `request` sets `write=True` for `upto == "charge"` and no `runs`. `StudyModel`'s charge readers move here; its
  `charge_record` scans `<store>/runs/<name>-upto-charge-*`.
- Routes `/api/meso/{continuum}/plane?tool=density|outline`, `/image`, `/charge/plane`, `/charge/image`, `/residues`,
  `/atoms?r=&z=`, `/structure`, `/annotation`, `/scene?subunit=&colour=charge|chain`, `/volume?which=full|revolved`;
  the `/api/study/{name}/charge/*`, `/residues`, `/structure`, `/annotation` and `/scene` routes go.
- Every meso tool's model is `MesoModel`. `plane()`'s geometry branch splits: `density` draws the chosen image and the
  membrane; `outline` the mean map under the outline, the probe and the editor. A residue's atoms are marked at (r, z),
  on the density section at x = r. The scene colours by chain in Density and Outline, by charge in Charge map.
- `bridge.js:show(keys)` takes a list; a pick from Mol* is mapped to its group before `select`. `save_edit` goes to
  `/meso/outline`.
- Outline's pane lists `moved` under the editor, *Into the water* and *Into the protein*, each row a residue with its
  copies, atoms and charge, picking it in Mol*.
- VER-60's NOTE: "The meso suite's Charge map drives a continuum model's walk over its molecular model to `upto:
  charge`" replaces "The study's charge on the mesh drives the walk to `upto: charge`"; it adds that a point names a
  residue once, its copies together, that an edit names the atoms it moves, each way, and that the overlay's mean
  about the axis is its 3D charge's.
- `test_meso_charge.py`'s fixture walks the tube's `charge_case` as `MesoModel.request` asks.
- The graph's node is *Charge map*; a click opens `continuum/<c>`, sets `built_with` to the study's molecular model where
  it differs, and goes to `/meso/charge`.

**Item 7.** The scene gains, behind *Overlay* in Charge map's pane, two volumes from `/volume`, each an isosurface at
±the level the pane sets, default a tenth of the larger `|full|` maximum, in the charge colours at opacity 0.5.

**Item 9** (Sonnet). `render_shell.py` group `meso`: the cached 2WCD project, its continuum model's charge case walked
with `write=True` and its elements rendered; each `/meso/<tool>` light and dark; a residue picked; an edit with a
vertex moved inward; the overlay on. `GROUPS` gains `meso`; the `/continuum/geometry` shots move to
`/meso/outline`; `STUDY_TOOLS` loses `charge`. `redraw.cjs` opens `/meso/charge` and fetches
`/api/meso/<c>/charge/plane` and `/residues`, `--continuum` naming the model. Check: `uv run python
.claude/scripts/gui/render_shell.py --only meso` runs and `node .claude/scripts/gui/redraw.cjs --help` prints.

### Work items

- [ ] 1. `plot/data.py` (`ResidueCopies`, `ResidueCharges`, `ResidueAtoms`, `inside_outline`), `gui/geometry.py`
  (D5, D6); done when `test_meso.py`'s copy and moved-atom tests pass and the `physics-reviewer` has read it.
  **Executor:** main
- [ ] 2. `api/project.py` (`charge_case`, `kept_artefacts`) (D4); done when `test_project.py`'s charge case passes.
  **Executor:** main
- [ ] 3. `plot/data.py:charge_volumes` (D7); done when `test_meso.py`'s volume test passes and the `physics-reviewer` has read it. **Executor:** main
- [ ] 4. Compaction checkpoint. **Executor:** main
- [ ] 5. `io/project.py`, `screens.py`, `tools.py`, `builds.py`, `frame.py`, `commands.py`; FR-31, §2, §3, §8.1 (D1, D3);
  done when `test_gui_screens.py` and `test_gui_settings.py` pass. **Executor:** main
- [ ] 6. `gui/web/meso.py`, `meso_tools.py`, `pages.py`, `plane.py`, `molview.py`, `bridge.js`, `continuum_tools.py`,
  `study_tools.py`, `study.py`; `test_study_charge.py` moved to `test_meso_charge.py`; VER-60's NOTE, VER-78 (a), (m),
  the matrix rows, the design document's rows (D2, D4 to D6, D9); done when VER-78 and `test_meso_charge.py` pass. **Executor:** main
- [ ] 7. The overlay in the scene and the pane (D7); done when the code and review say so. **Executor:** main
- [ ] 8. Compaction checkpoint. **Executor:** main
- [ ] 9. `render_shell.py`, `redraw.cjs` (D8); done when its check passes. **Executor:** general-purpose on Sonnet, high
- [ ] 10. `/np-gui render shell`, `review`, `publish`: the round (D8); done when the digest is published.
  **Executor:** main
- [ ] 11. Compaction checkpoint; the author's verdicts collected. **Executor:** main
- [ ] 12. The verdicts built: the name, REV-259's and REV-261's points, the overlay kept or removed; the round's
  WB row; a final render reviewed (D1, D7 to D9); done when the review's blocking
  findings are fixed. **Executor:** main

### Verification

| Test | Tier | Identifiers | Oracle and tolerance | Command |
|---|---|---|---|---|
| `tests/tier1/test_meso.py` | 1 | VER-60 | A C3 table of one charged residue per chain, built in place: `at` names it once, its value the copies' sum of `q · volume_density` to 10⁻¹²; `residues()` once with its charge per copy; `markers` every copy; under C1, three keys | `uv run pytest tests/tier1/test_meso.py` |
| same | 1 | VER-60 | A square outline and an edit moving one vertex in: `moved` holds exactly the atoms inside the cut triangle, *out*, and none *in*; moving it out, the reverse; an unedited outline none; a seeded edit against its seed. `nearest` ranks each atom's residue first at the atom | same |
| same | 1 | VER-60 | `charge_volumes` on three atoms: `revolved` equals `volume_density` summed, to 10⁻¹²; the mean of `full` over 360 azimuths at five (r, z) equals `revolved` to 10⁻⁶ relative (a periodic trapezoid, spectral in the azimuth); each sums to the charge per frame to 10⁻⁶ (four widths truncate at e⁻¹⁶) | same |
| `tests/tier1/test_project.py` | 1 | FR-27, FR-39 | The charged tube's continuum model: `charge_case` walked to `charge` keys stage 7 as the imported study's walk does; its stages are in `kept_artefacts` and survive `clean_store`; an idealised pore is refused, naming its pore | `uv run pytest tests/tier1/test_project.py` |
| `tests/tier1/test_meso_charge.py` | 1 | VER-60 | WP5.19's two VER-60 tests over `MesoModel`: the map's block means carry `q_grid_e` to 10⁻¹², the deployed elements `q_mesh_e` to 10⁻¹², the stage hashes, legs and planes the record's | `uv run pytest tests/tier1/test_meso_charge.py` |
| `tests/tier1/test_gui_screens.py` | 1 | VER-78 | Every state loads each `/meso/<tool>` with its controls; (m) at `/meso/charge`; Continuum opens on Region; Study's old chord is `Alt+Shift+Digit5` | `uv run pytest tests/tier1/test_gui_screens.py` |
| The per-push VER-62 walks | 1, 2 | VER-62 | Unmoved: no stage's key changes | `.claude/hooks/gate.sh run` |

### Out of scope

- Handles dragged on the canvas or in Mol*: WP5.23 (REV-238).
- The 200 ms line on the Charge map: WP5.22 (REV-258).
- A study's own charge with its overrides, in Charge map: later, if asked; Study › Runs keeps each run's record.

### Open questions

None blocking. The name and REV-259's questions are the round's (D8).

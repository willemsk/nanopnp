# WP5.16 — The Molecular suite

**Status: delivered 11 November 2026, awaiting its merge and `/np-ship`.** Planned 11 November 2026 on `main` (`0b75c30`). It inherits §8.2.24 Z5, §8.2.34 AJ5
and AJ8, §8.2.36 AL22 and this plan's §8.2.39 AO1 to AO3.

This plan belongs to [the Phase 5 plan](phase-5-workbench.md). `SPECIFICATION.md` governs. An identifier here points to
a clause and never restates it.

## In brief

**What changes.** The Molecular suite starts working: you open a structure, orient it, choose its frames, build its
protonation, edit a residue's charge and look at the result. First the program learns to find the axis of any
pore: a ring of identical chains, a ring of repeating units such as PlyAB's pairs, or a one-chain pore from its
channel; a file's own axis is checked, not trusted. A command prepares a structure from the terminal. An edited
molecule is saved as a variant that follows its parent, or as a full copy. The tools are drafted on 2WCD, shown to
you, then finished to your verdicts.

**Cost.** About five sessions, five to ten agent hours and 14 of your touches, the prototype round included; the frame
package measured about two sessions, two agent hours and six touches. No new library.

**What could go wrong.** The channel's axis could sit off the true one; on 2WCD it is held against the ring's axis, and
synthetic pores of known axis test both methods and each refusal. Tidying the atom radii could move a stored result;
every recorded result is checked unmoved. A model built alone could miss what a study later reuses; a test compares
their fingerprints. A tool could save a value no study accepts; each is checked before it is written, a refusal
shown at its field.

**Your call.** None for the plan: you ruled the axis, the Prepare view and variants. At the prototype round: where
should the 3D view sit, a settings window or page, and how should the rail fold? *Recommendation:* rule them on the
drawn screens, which show each choice.

## Execution brief

**Scope.** The phase entry's WP5.16 as AO1 amends it; REV-121, REV-41's `prepare`, REV-218, REV-231 and REV-234 fixed;
REV-235's and REV-237's items put at the prototype round. **Depends on:** WP5.15 (merged). **Requirements:** FR-02,
FR-03, FR-27, FR-34, FR-37, FR-38, FR-39; QR-12; VER-48, VER-62, VER-78. **Constrained by:** AJ1, AJ8, ADR-004 (no
request leaves the origin), CON-07, CON-09 (Mol* unmodified). **Implementing session:** Opus, high effort; sub-agents
Sonnet, high. Tag `v0.6.0-alpha.16`.

**Amended when it lands:** §5.2's NOTE on stage 1; §5.3.1's NOTEs on `structure:` and on model files; VER-48; VER-78;
the matrix rows of FR-37 and FR-38; the design document's Q09, Q13 and Q27.

### Decisions

Nine: three library steps, two project mechanisms the tools write through, and the tools' pages, view and round.

| Decision | Choice | Why/source |
|---|---|---|
| D1 The pore's axis | `symmetry.axis` gains `cavity`; `source.chains` takes groups, `A+B,C+D`. Under C2 and above `auto` superposes the ring of chains or groups; under C1 `auto`, and `cavity` anywhere, take the channel's axis (D2) without the chain rules; `z` is checked against the axis that applies, with its budget | AO1, ruled by the author; decided by the plan for the syntax, which moves no key |
| D2 The channel's axis | `structure/cavity.py:channel_axis`: from the file's z, the line fitted through the centres of planes 0.5 nm apart, each the centroid of the enclosed points tied at the plane's largest clearance where it cuts a Voronoi edge of the ensemble-mean heavy atoms, followed plane by plane from the widest, iterated to a fixed line. Gated on convergence, orientation, coverage and straightness; the limit and `z`'s budget measured on 2WCD against its ring axis, into §5.2's NOTE | Z5, REV-121; decided by the plan, corrected at item 2 |
| D3 `prepare` | `orient_pore(..., axis=None)` takes a typed axis; with no distinct covariance axis it takes the channel's axis instead of refusing; it writes `<out>.prepare.json` beside the file; `nanopnp prepare` wraps it | REV-41, FR-37, decided by the plan |
| D4 Radii in one place | CODE_REVIEW_036's D4.1, D4.2, C4.1 and C4.2 as written; REV-231's comment with them | AL22 and CODE_REVIEW_036, ruled by the author |
| D5 A model built alone | `Project.build_case(kind, name)`: the model with each required value it lacks from `BUILD_LAYER`, which no stage up to protonation reads; walked by `SolverProcess` with `write=False`; the clean-up keeps each model's built stages | WB-11, decided by the plan |
| D6 Values and variants | `Project.set_value`, `new_model`, `set_exposed` and `save_variant(parent, name, edits, copy=False)`, each checking the edited body before writing it; `variant_of` names the parent's file; a linked variant holds only `charge.edits` over an unedited parent; its changes are its differences from its parent | AO3, AG11, WB-12, ruled by the author; decided by the plan for the path and one level |
| D7 Tool pages | `/molecular/<tool>` per tool, the pane drafted left of the view, its place REV-234's ruling at the round; each field with its mark, reset, refusal and *Expose*; *Modified only*; `?field=` focuses its field; each tool's state from the store; a build queued, cancellable, its child tracked | WB-05, WB-07, WB-12, FR-27; decided by the plan |
| D8 The 3D view | Each view a MolViewSpec document the server writes and `nano.scene` loads, keeping the camera: the structure, its representation, colour from a per-atom annotation (charge diverging about zero, chain, changed), the axis a tube, the membrane two discs, a clip | VER-60, WB-20, CON-09; decided by the plan |
| D9 The round | After D1 to D8, the five tools drafted on 2WCD and rendered empty, building, built and refused; reviewed, published, collected; then REV-234, REV-235's and REV-237's questions to the author; then finished to the verdicts | AJ8, ruled by the author |

### Grounding

**D1.**
- `io/case.py:Symmetry.axis` is `Literal["auto", "z"]`. `structure/stage.py:structure_parameters` keys stage 1 on
  `spec.model_dump`, so a new value of a field moves no existing key, and a new field would move every key.
- `pipeline/case.py:_resolve_structure` refuses `auto` on C1 and a chain list not numbering n. `io/resolved.py:parse_chains`
  splits on commas; `structure/read.py:select`, `structure/orient.py:orient_pore` and `_resolve_structure` call it.
  `ResolvedStructure` holds `spec`, `n` and `chains`.
- `structure/read.py:select` refuses a count other than n, a chain under `COVERAGE_FRACTION` of the most complete
  chain's C-alpha and a residue name that differs from the first chain's; `common_index` is (n, common C-alpha), matched
  by residue number and insertion code.
- `structure/stage.py:align`: `auto` calls `detect_axis` and `frame_rotation(record, chains[0].mean(axis=0))`; `z`
  with n ≥ 2 calls `gate_axis(measure_axis(...))` and `check_z_axis`; C1 under `z` records "unchecked".
  `drift_deg` comes from `cyclic_fit` per frame, `frame_check` from `measure_axis` on the aligned mean.
- `structure/axis.py:chain_order` and `cyclic_fit` take an (n, m, 3) array, so a group's joined C-alpha is one row.
  `measure_axis` raises below n = 2.
- `tests/tier1/test_structure_axis.py:test_ver48_gates_fire` holds `c1-auto`, a refusal AO1 removes.
- REV-231: `axis.py`'s threshold comment names `knowledge/07-software-stack/index.md`; the margins are the WP18 plan's.

**D2.**
- `align` holds every selected atom's ensemble mean, `positions.mean(axis=0)`, and `chosen.atoms.element`.
- `axis.py:ORIENTATION_LIMIT_DEG` is 10, `DISPLACEMENT_BUDGET_NM` 0.01; `z_displacement` measures a line against z
  over the C-alpha extent.
- `test_structure_axis.py:_protomer` and `_assembly` build wedges between 2 and 5 nm about a known axis;
  `tests/conftest.py:prepared_2wcd` is a PDB of chains A–L tilted 4° and shifted (0.6, −0.35, 1.2) nm;
  `structure_2wcd` is a store holding its stage 1 under `auto`.

**D3.**
- `orient.py:orient_pore` estimates by `_pore_axis`, which refuses when no covariance eigenvalue stands apart
  (`DEGENERACY`), signs by `_signed`, places the registration centroid and returns the path. `prepared_pore` names the
  file by a digest of the source, the choices, `orient.py` and `read.py`, staged then renamed.
- `examples/06-pdb-to-mesh/prepare.py` and two Tier 1 tests call it.
- `cli/parser.py:build_parser` registers `building.register` (`geometry`, `mesh`); `cli/common.py:_emit`, which
  `building` imports, prints text or JSON.
- `api/case.py:_ORIENT_KEYS` lists the keywords `Case.from_structure(orient=...)` passes to `prepared_pore`.

**D4.**
- `density/stage.py` multiplies `resolve_protonated_radii(...).radii_nm` by `radius_scales(table)`.
- `charge/edits.py:_owner` and `density/radii.py:resolve_protonated_radii` each index residues; `_owner` raises
  `KeyError` on an atom with no residue row, the other maps it to −1.
- `geometry/contour.py:probe_radius_edits` and `gate_inputs` build `RadiusEdit`s; `charge/kernel.py` imports
  `ProtonationTable` from `charge.protonation`; `gui/assess.py` (Qt) calls `probe_radius_edits`.

**D5.**
- A molecular body alone fails validation: `electrolyte` (its `species` and `concentration_M`) and `boundary_conditions`
  are required. With Na⁺ and Cl⁻ at 0.15 M and `bias_V: 0.0` added, it validates and resolves protonating (probed). Stage 1 keys on
  `structure:`; `charge/protonation.py:protonation_parameters` on `charge.ph`, `forcefield`, `titration`, the edits and
  stage 1's hash.
- `pipeline/run.py` stops at `upto="protonation"`, refusing a case that does not protonate; `keyed_walk(resolved,
  store=, planned=)` returns each stage's identity and runs none.
- `gui/solver.py:RunRequest` holds `case` (a file), `store` and `upto`; `_worker` runs `Session(store).run`, which writes a
  run record unless `write` is False. `gui/web/server.py:track` cancels a child when the server stops.
- `api/project.py:Project.kept_artefacts` keeps what run records and sweep members name, closed over their inputs.
- `gui/web/states.py:boot_project` walks the first study to its charge once, at start; nothing walks after it.

**D6.**
- `api/project.py:Project` writes items through `_write_item`, `reset` and `import_case`; no method sets a value or
  creates a model. `changes` reads `io/defaults.py:mapping_changes` of the body.
- `io/models.py:HEADER_KEYS` is `schema`, `name`, `exposes`; `read_model_file(kind, path, *, rebase, source)` refuses a
  key `owner_of` gives another kind, a study-owned `variant_of` included, and validates no value's type;
  `exposed_values` reads `exposes:` or `EXPOSED[kind]`, pH for molecular.
- `charge/protonation.py:_parent_parameters` keys a variant's parent as its case without edits.
- `io/project.py:FOLDERS["molecular"]` is `models/molecular`.

**D7.**
- `gui/web/screens.py:Suite.tools` are strings; `pages.py:suite_page` labels each "in a later package"; `pages.ROUTES`
  holds `/<suite>`, `/study/charge`, `/settings`; `frame.py:Route.view` is `"molecule"` or None.
- `frame.py:_Frame.on_open_field` opens `/<suite>?field=<path>`, which no page reads. `queue.py:Queue` shows entries and
  starts nothing.
- `tests/tier1/test_gui_screens.py` runs VER-78 (a) to (d) over `screens.SCREENS` in `states.STATES`; no state holds a
  structure, `charged-tube` taking `inputs.pqr`.

**D8.**
- `assets/bridge.js:nano.ensure` builds Mol* once and then ignores its URL; nothing colours, restyles, clips or loads
  another structure.
- The vendored Mol* 5.13.1 has `Viewer.loadMvsData(data, format, options)` with `keepCamera`, MolViewSpec's `tube` and
  `ellipse` (`as_circle`), `color_from_uri` with a `continuous` palette and a `clip` node (read in `molstar.js`).
- `/api/structure` serves `link.py:_pdb`, the protonation table's first frame, from the walk at start.
  `structure/ensemble.py:AlignedEnsemble.export` writes a PDB and a DCD.

**D9.**
- `.claude/scripts/gui/render_shell.py:build_cache` caches the 2WCD project, whose server walks its study to the charge.
- `docs/design/mockups/a/01-molecular.html` holds `m-prepare` to `m-view`, from
  `docs/design/generators/mockups/s_molecular.py`.

### Implementation details

**Items 1 and 2.**
- `parse_chain_groups(chains) -> tuple[tuple[str, ...], ...] | None` in `io/resolved.py`; `parse_chains` returns the
  flattened chains. `ResolvedStructure.groups` holds the groups, one chain each without `+`. Refused at resolution,
  naming the key: an empty member, a repeated chain, groups of unequal size, groups not numbering n, `+` under C1.
- Under groups, `select` checks coverage and residue names per position in the group; `common_index` joins each group's
  common C-alpha in position order, the positions in the listed order, not the file's. `select` reads the groups from
  `chains` and gains a `channel` keyword. Under the channel it skips the count, coverage and residue-name rules, and `common_index` is
  every C-alpha as one row.
- `cavity.py` holds `SLAB_NM = 0.5`, `REACH_NM = 1.0`, `GAP_DEG = 90.0`, `MIN_CLEARANCE_NM = 0.2`,
  `TIE_NM = 1e-3`, `COVERAGE_FRACTION = 0.5`, `TURN_TOL_RAD = 1e-6`, `MOVE_TOL_NM = 1e-6`, `MAX_ITERATIONS = 50`, and
  the measured `STRAIGHTNESS_NM` and `CAVITY_BUDGET_NM`, each commented with §5.2's NOTE. `ChannelRecord(axis,
  foot_nm, centroid_nm, centres_nm, planes, straightness_nm, iterations, turn_rad, move_nm, carried)`, `summary()`;
  `gate_channel` raises `SymmetryGateError` naming the gate and the measured value.
- A plane's centre is the centroid of its enclosed candidates within `TIE_NM` of its largest clearance; a candidate
  is a point where the plane cuts a Voronoi edge, a hull face's edge running on along its normal. Under C<sub>n</sub>
  the n images of a candidate tie, so at the true axis each centre lies on it, and the axis is the iteration's fixed
  line; one candidate picked would sit off it. `TIE_NM` is ten times the PDB format's 0.001 Å step, so a pore built
  with imposed symmetry ties as an exact one does.
- The Delaunay tetrahedra of the heavy atoms are built once per fit, their circumcentres the Voronoi vertices, a flat
  tetrahedron taking its neighbour's; the iterations cut the edges again (1.6 s for 26,844 atoms, measured). Under the
  channel, `drift_deg` carries each mean centre into a frame with the atoms of its edge's first tetrahedron, refits the
  line, with no new tessellation, and takes its angle to the mean's axis; `frame_check` measures the channel's line
  again on the aligned mean. `Alignment.record` holds the `ChannelRecord`; the frame's turn puts the first listed
  chain's C-alpha centroid on +x; `chains_cyclic_order` is the file order. C1 under `z` is checked against the
  channel's line, so the `unchecked` status, `Symmetry.axis`'s description and `_resolve_structure`'s C1 message change
  with it.

> **Outcome — D2's method corrected at item 2.** The Voronoi vertices alone left 12 of 2WCD's 28 slabs without one
> near the axis, and each took a void of the wall; the centres are now the points where planes cut the Voronoi edges,
> followed from the widest enclosed space, a candidate enclosed by the atoms within 0.25 nm of its plane. Measured on
> the prepared 2WCD: 0.0073 nm from the ring's axis (0.042°), the farthest centre 0.0148 nm from the line, 28 of 28
> planes, 3 iterations, 4 s for the stage. `CAVITY_BUDGET_NM = 0.015`, `STRAIGHTNESS_NM = 0.03`. A ragged rim is the
> method's weakness: [the concept](../../../knowledge/04-clya-geometry-and-charge/15-the-channel-axis-of-2wcd.md),
> REV-239.

- The header's `axis` gains `method` (`permutation` or `channel`) and `groups`; a reader takes their absence as
  `permutation` and none.
- Item 2 measures on `prepared_2wcd` under `cavity` against `auto`: the displacement over the C-alpha extent and the
  largest centre distance. The budget is twice that displacement, at most 0.1 nm; the limit twice the distance. A
  displacement over 0.1 nm is investigated, never budgeted. The numbers go into §5.2's NOTE and a concept in
  `knowledge/04-clya-geometry-and-charge/`.

**Item 3** (Sonnet).
- `orient_pore(source, *, chains="all", cis_end, registration_residues=None, centroid_z_nm=0.0, axis=None, out)`:
  `axis` a 3-tuple, normalised, signed by `cis_end`; `ValueError` on a zero vector. Where `_pore_axis` raises,
  `cavity.channel_axis` on the kept heavy atoms in nm, started from each covariance axis, keeping the one that passes
  coverage and straightness with the least straightness; none passing is refused.
- `PreparationRecord`, a strict Pydantic model: `source` (`name`, `sha256`), `chains`, `cis_end`,
  `registration_residues`, `centroid_z_nm`, `axis` (file frame), `tilt_deg`, `method` (`covariance`, `channel`,
  `typed`), `off_axis_nm`. Written to `out.with_suffix(".prepare.json")`, staged with the PDB in `prepared_pore`, which
  also digests `cavity.py`. `prepared_pore` and `_ORIENT_KEYS` take `axis`, a digested choice; the record is renamed
  into place before the PDB, whose presence marks a whole pair.
- `nanopnp prepare SOURCE --cis-end {wider,narrower} --out OUT [--chains C] [--registration FIRST:LAST]
  [--centroid-z-nm Z] [--axis X,Y,Z]`; `_emit` prints the record, `--json` the record itself.

> **Outcome — item 3.** `off_axis_nm` is the registration centroid's distance from the axis line used. A ring always
> has two equal covariance eigenvalues and one apart, so the channel is reached only where other matter evens them; a
> start across the wall never fixes a line and runs all 50 iterations, about 80 s on a 5,000-atom wall, so the fallback
> can take minutes on a large pore (REV-239).

**Item 4** (Sonnet). CODE_REVIEW_036, candidate 4, section 3, verbatim; `charge/edits.py` raises `EditError` naming
frame, chain, residue and atom for an atom it would edit at −1; `radius_scales(table)` becomes the method.

> **Outcome — item 4.** `geometry/contour.py` already converted at its own boundary and is unchanged;
> `ProtonationTable.radius_edits()` is new; every atom without a residue row is refused, not only one an edit names.
> The `2wcd-charged` walk reads the same drift, 2.912e-12, before and after.

**Item 6.**
- `Project.set_value(kind, name, path, value)`: `owner_of(path)` is `kind`, else `ProjectError`; the body edited by
  `io/models.py:_put`, read back by `read_model_file(rebase=False)`, then validated as `build_case` validates it,
  through `loads_case`; `CaseValidationError` propagates and nothing is written. `None` deletes as `reset` does.
  On a linked variant it refuses a path other than `charge.edits`; on a model a linked variant names, `charge.edits`.
- `Project.new_model(kind, name)` writes `{schema, name, exposes}` with `EXPOSED[kind]`; `set_exposed(kind, name,
  path, on)` edits `exposes:`.
- `HEADER_KEYS` gains `variant_of`. A linked variant: `{schema, name, variant_of: {model: 2wcd.yaml, linked: true},
  charge: {edits: [...]}}`; a copy: the parent's body, its edits and `variant_of` with `linked: false`.
  `read_model_file` merges only a linked variant's body over its parent's.
- `BUILD_LAYER`: `electrolyte: {species: [{name: Na+, z: 1}, {name: Cl-, z: -1}], concentration_M: 0.15}` and
  `boundary_conditions: {bias_V: 0.0}`, under the model; `BUILD_UPTO = {"molecular": "protonation"}`.
- `RunRequest.write: bool = True`; `_worker` sets `Session.write`.
- `kept_artefacts` adds, per model, the identities `keyed_walk` gives `build_case`'s stages up to `BUILD_UPTO`. A
  model that does not resolve adds none and stays in `problems`; the identities are held per model, keyed by its
  file's digest and its input files' size and modification time, so `store_usage` hashes no structure twice.
- `set_exposed` names an entry by the path's last part, refused where another entry has that name. `changes` of a
  variant compares `io/models.py:leaves` of its parent's body and of its own merged body, `Change.default` the
  parent's value.

> **Outcome — item 6.** `build_case` returns a `Case`; an edit is staged beside the item, read as a study reads it and
> as `build_case` validates it, then moved into place. A model's identities are held only once the store holds every
> stage, since a stage not yet built is keyed by a forecast. `ModelFile` gains `variant_of` and `parent`; the manifest
> lists a linked variant's parent, and an import brings it along. `variant_of` is refused off a molecular model.

**Item 7.**
- `screens.Tool(id, title, fields)`; molecular `prepare`, `ensemble`, `protonation`, `edit`, `view`; `on_open_field`
  opens the tool whose `fields` holds the path's prefix. `ROUTES` gains
  `/molecular/<id>` as `Route("molecular", "molecule")`; a `Screen` per tool with `tool-pane`, `tool-status` and its
  controls.
- `gui/web/molecular.py:MolecularModel(project, name)`: `state(stage)` (`empty`, `building`, `built`, `refused`, the
  last refusal held in memory), `build(upto)`, which writes `build_case`'s text to a temporary folder removed when the
  child ends, and the stage-1 and protonation summaries read by `stored_upstream`.
- Endpoints `/api/molecular/{name}/structure` (the source, the prepared file, stage 1's frames as PDB models, or the
  table's), `/annotation?by=charge|chain|changed` and `/scene?tool=…` (MolViewSpec JSON).
- `nano.scene(url)`: the first call builds Mol*; each later one runs `loadMvsData(json, 'mvsj', {replaceExisting:
  true, keepCamera: true})`. `show_molecule` loads through it too, so `/study/charge` never keeps a tool's scene.
- In a state with no structure each tool screen shows its empty `tool-status`; on a model from `inputs.pqr`, Prepare
  and Ensemble name the PQR there. VER-78 (m) runs in `empty`.

> **Outcome — item 7.** The panes are `gui/web/tools.py`, beside `molecular.py` and `molview.py`. A colouring is one
> colour per residue, computed by the server (the charge on VER-60's diverging scale, saturating at 1 e) and read by
> `color_from_uri`; no palette of Mol*'s is used. A primitive is `{kind: primitive, params: {kind: tube}}` in the
> vendored Mol*. The membrane's discs and the clip come with the Prepare and View drafts of item 8. The charge screen
> loads through `/api/scene` too. `server._stop_children` cancels a window's builds through `molecular.cancel_builds`.

**Item 8.** `render_shell.py`'s 2WCD project gains `/molecular/<tool>` shots built, a refused stage 1 (`axis: z` off
the budget) and a build held mid-walk.

> **Outcome — item 8's review.** The reviewer's 25 findings on the render at `a6b9ae5`, decided: fixed before the
> digest, the pane scrolling by itself, full-width controls, the charge read from the table's residue charges, a PQR
> model's fields disabled, Ensemble's draft block, the colour bar out of the draft block with its ends named, the queue
> line following a build, and a stage after a refused one reading not built. Put to the author on the digest: the
> view's place and size and the charge screen's order (REV-234), the colour's direction, the point group in Prepare,
> and which action is each tool's primary one. Item 11's, with the verdicts: the tool list on every tool's page with
> each tool's state (WB-05, WB-07), *Open structure…* and a project-relative path, Prepare opened side-on with the
> slab, the residue strip and the states on the pane, View's background, slab and residue list, a refusal marked at
> its field and listed among the problems, the warnings and unapplied states opened from their counts, the state
> glyphs and colours (WB-20), the build's stage, numbers through `numbers.shown`, the later-phase banners, and the
> empty states' wording. `impeccable`'s critique runs with item 12's review. The digest, 14 cards over 154 shots of
> the render at `d5995eb`, is published at <https://claude.ai/artifact/HRDfKwmg4WRYnowGuVB51g>, round 1; the colour
> bar's ends measured 2.55:1 on the dark theme in that render and stand on a white plate since.

> **Outcome — item 10.** All 14 picks marked, 6 `keep` and 8 `change`
> (`docs/design/reviews/2026-11-11-molecular.md`). Ruled at the collect: every tool's pane on the left of its view
> (REV-234); positive blue and negative red on every charge and potential display, the direction a setting; the
> settings a window over the tool and the folded bar a strip of icons with state (REV-237); the channel's
> straightness limit warns and does not refuse (REV-239; §8.2.39 AO4). Item 11 takes the tools' notes with them: both
> actions side by side, dense controls, the stage bar with its progress and a small *Cancel*, the refusal card, the
> counts opening their lists, no build on View, and the tool list beside every pane. REV-240 carries the ensemble's
> variation view, maps beyond the two directions and one rule for safeguards; REV-235's and REV-237's other points
> wait for a later suite's round. The design document's row is WB-39.

**Item 11.**
- Prepare: *Open structure…* a path field over `Project.add_input`; the chains or groups; *Estimate* runs `orient_pore`
  off the event loop, or a typed tilt and azimuth in degrees; *Flip* swaps `cis_end`; the registration residues and the
  centre; *Save prepared structure* writes `prepared_pore` into `inputs/` and sets `structure.source.path`, then builds
  stage 1 and shows its gates (Q13).
- Ensemble: `structure.ensemble.trajectory`, `frames.count` or `last_ns`; *Build ensemble* walks stage 1; one frame or
  the frames overlaid.
- Protonation: `charge.ph`, `forcefield`, `titration`; *Build molecular model* walks to the protonation; each residue's
  state, Q<sub>net</sub> per frame and PROPKA's warnings from its summary (Q27).
- Charge edit: a residue picked in 3D or in the list; a state, a charge change or a radius scale; on a model without
  edits *Save as variant…* asks a name and *Linked* or *Full copy*, and on a variant it edits that variant; a model
  holding edits and no `variant_of` edits them in place.
- View: representation, colour, the `viewer_background` setting, clip at the axis, the residue list.

> **Outcome — item 11.** Built to the verdicts of item 10. A tool's page is the tool list with each tool's state, the
> pane and the view; the pane heads with a block per stage and a thin bar under the running one, the tool's actions
> side by side with a small *Cancel* while a build runs, and a card per refusal or warning that unfolds its text and
> goes to the field it names. A refusal is also among the frame's problems, and a value's change clears it. Fields
> are one dense row each. Prepare: *Open structure…* lists the project's inputs or copies a file in; *Estimate*
> and *Save prepared structure* run `orient_pore` and `prepared_pore` off the event loop, the choices read back from
> the prepared file's record; the view opens side-on with the plane z = 0. Ensemble: a frame, or the first ten
> overlaid. Protonation: the titratable groups, the unapplied states and the warnings each open a window; a row
> selects its residue. Charge edit: edits are written in place on a variant or a model that holds some, and otherwise
> held until *Save as variant…*, which opens the variant; a linked variant's other values are disabled and name its
> parent. View: representation, colouring, the background setting, a cut-away through the axis (a MolViewSpec `clip`
> node) and a residue finder; no build. Charge and potential draw positive blue, with the `charge_colours` setting;
> the settings open as a window over the tool, `/settings` kept as an address; folded, the drawer is the suites' icons
> with a dot for a problem or a running build; every pane stands left of its view, the charge screen's too. The
> structure's address carries a digest of its text, since Mol* keeps what it read from an address. The channel's
> straightness warning (`b236007`) shows as a card in Prepare and Ensemble. Not built: the frames table of an
> ensemble beyond its per-frame net charge, the residue strip under the view (a finder stands in the pane), and the
> colour bar as an overlay of the view.

> **Outcome — item 12.** The render `shell-r2` at `def8265`: 202 shots, light and dark, every page loaded; one
> measured failure, the paging icons of the titratable groups' table at 2.64:1 on the dark theme, fixed. The GUI
> reviewer raised 21 findings and the critique 12 (24 of 40), none blocking. Fixed: one label style and one width for
> every pane, the view the window's height, secondary buttons in the control's edge, the build's glyph and a full-size
> *Cancel*, the progress under the running block, a refusal that finds its field from the gate's words, the card's
> longer text, the warnings worded, the counts named, the unapplied states' rows selecting their residue, *Expose* and
> View's controls disabled where the model cannot use them, the Prepare draft kept for the window, the colour bar
> shown once charges are built with its ends as bounds, and the table's headings. Left open as REV-241: Prepare's
> view does not follow the typed values (against AO2), a PQR model's View, *Open structure…* without an upload, and
> the frame's points. The render script's cost was measured at the author's request and cut from seven minutes to two
> for the same 140 shots (`95abcf7`).

### Work items

- [x] 58f9ab6 1. `io/case.py`, `io/resolved.py`, `pipeline/case.py`, `structure/read.py`, `structure/stage.py`, `structure/axis.py`
  (D1; REV-231); done when `tests/tier1/test_structure_axis.py` and `test_structure_stage.py` pass, VER-62 unmoved.
  **Executor:** main
- [x] 3ffaac5 2. `structure/cavity.py`, `structure/stage.py`, §5.2's NOTE on stage 1, §5.3.1's NOTE on `structure:`, VER-48, a
  knowledge concept (D1, D2); done when the same files pass. **Executor:** main
- [x] 142183d 3. `structure/orient.py`, `cli/building.py` (D3); done when `test_structure_axis.py` and `test_cli.py` pass.
  **Executor:** general-purpose on Sonnet
- [x] 5446186 4. `structure/protonated.py`, `charge/edits.py`, `charge/kernel.py`, `density/radii.py`, `density/stage.py`,
  `geometry/contour.py` (D4); done when `test_protonation.py` and `test_density.py` pass, VER-62 unmoved.
  **Executor:** general-purpose on Sonnet
- [x] 6b175ef 5. Compaction checkpoint. **Executor:** main
- [x] 30b7430 6. `io/models.py`, `api/project.py`, `gui/solver.py`, §5.3.1's NOTE on model files (D5, D6); done when
  `tests/tier1/test_project.py` and `test_models.py` pass. **Executor:** main
- [x] e46a48b 7. `gui/web/screens.py`, `pages.py`, `frame.py`, `molecular.py`, `molview.py`, `assets/bridge.js`, VER-78's text
  (D7, D8); done when VER-78 (a) to (d) and (m) pass. **Executor:** main
- [x] d5995eb 8. The five tools drafted; `render_shell.py`; `/np-gui render shell`, `review` and `publish` (D9); done when the
  digest is published. **Executor:** main
- [x] 9. Compaction checkpoint; the author's verdicts. **Executor:** main
- [x] ee52015 10. `/np-gui collect`; REV-234, REV-235's and REV-237's questions to the author; the design document's rows (D9);
  done when each is ruled or carried. **Executor:** main
- [x] def8265 11. The tools finished: Prepare (Q09, Q13; AO2), Ensemble, Protonation (Q27), Charge edit (FR-38; AO3), View;
  *Expose* and *Modified only* (D6 to D8); done when VER-78 passes. **Executor:** main
- [x] 41abc6c 12. `/np-gui render shell` and `review`, each finding fixed or a `REV-nn` row; REV-121, REV-41's `prepare`,
  REV-218, REV-231 and REV-234 `fixed`; the matrix rows; `current.md`. **Executor:** main

### Verification

| Test | Tier | Identifiers | Oracle and tolerance | Command |
|---|---|---|---|---|
| `tests/tier1/test_structure_axis.py::test_ver48_the_channel_axis_recovers_a_known_axis` | 1 | VER-48; FR-02 | C7, C8 and C12 walls with closed rims, tilted 8° and offset by (3, −1.5, 40) nm: axis to 10⁻⁶ rad, line to 10⁻⁶ nm, the iteration's stop, the axis being its fixed point; at 35° before the orientation gate, the same; one chain of any kind taken by `select` under the channel | `uv run pytest tests/tier1/test_structure_axis.py` |
| the same file, `test_ver48_the_channel_axis_gates_fire` | 1 | VER-48; QR-12 | One assertion each, naming gate and value: a solid ball (coverage), a channel bent 2 nm (straightness), an axis 12° from z (orientation), `z` beyond the budget, no convergence | as above |
| the same file, `test_ver48_chain_groups_superpose_as_one_ring` | 1 | VER-48; FR-03 | Eight A+B units of two shapes: axis to 10⁻⁹; refused, one each: a repeated chain, unequal groups, a residue name differing at one position, groups not numbering n | as above |
| `tests/tier1/test_structure_stage.py::test_ver48_2wcd_channel_axis_agrees_with_its_ring_axis` | 1 | VER-48 | `cavity`'s displacement from `structure_2wcd`'s `auto` axis equals §5.2's recorded value to 10⁻⁴ nm; C1 with all 12 chains under `auto` routes to the channel: equal to `cavity`, exact; `cavity` run on `prepared_2wcd.path`, `write=False` | `uv run pytest tests/tier1/test_structure_stage.py` |
| `tests/tier1/test_models.py::test_fr39_a_model_built_alone_keys_as_its_study_walk` | 1 | FR-39; WB-11 | Stage-1 and protonation identities of `build_case` equal the study's, exact | `uv run pytest tests/tier1/test_models.py` |
| `tests/tier1/test_project.py::test_fr38_a_linked_variant_follows_its_parent_and_a_copy_does_not` | 1 | FR-38; AO3 | One each: a variant resolves to parent plus edits; the parent's pH reaches it; not a copy; a variant's changes are its edits; a set value reads back; a refused one writes nothing | `uv run pytest tests/tier1/test_project.py` |
| Tier 2's golden walks | 2 | VER-62 | Unmoved by items 1, 2 and 4 | `.claude/hooks/gate.sh run` |
| `tests/tier1/test_gui_screens.py` | 1 | VER-78 (a) to (d), (m) | The tool screens in each state; (m): Prepare, View, Prepare keeps the window and `nano.builds` is 1 | `NANOPNP_REQUIRE_BROWSER=1 uv run pytest tests/tier1/test_gui_screens.py` |
| `tests/tier1/test_cli.py::test_prepare_writes_the_oriented_pore_and_its_record` | 1 | — (smoke) | Exit 0; the record's tilt within 0.5° of the ring's | `uv run pytest tests/tier1/test_cli.py` |

### Out of scope

- Dragging the axis and the membrane: REV-238 (AO2). A trajectory's upload and alignment beyond stage 1's.
- The Continuum, Physics, Study and Analysis tools: WP5.17 to WP5.20; the keyboard pass over the canvases: WP5.21.
- Preparing or aligning a model from `inputs.pqr`, which has no structure: its Prepare and Ensemble screens name
  the PQR (item 7).

### Open questions

None.

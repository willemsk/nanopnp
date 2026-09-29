# WP24 — GUI increment 2: the geometry pipeline surfaced

**Status: planned, not started.** Written 29 September 2026, after WP23 merged on `main`
(`4232eeb`, tagged `v0.9.0-alpha.7`). This package inherits the desktop shell of WP14 and WP15:

- the `RunEvent` queue from a spawned child;
- `StageHook` and `SolveHook`, and the rule that a hook is never an input;
- the Qt-free view-models, asserted on `sys.modules`;
- the render child that writes a webgui scene as a file;
- the probe bundle and its CON-11 notice.

From WP20 and WP21 it inherits stage 4's `nanopnp/profile/v1` artefact, in the stage-1 frame, and
`inputs.profile`, which stage 5 already consumes. It also inherits WP23's open question: whether the
bundle carries Gmsh.

This is a work package of the [Phase 2 plan](phase-2-geometry-pipeline.md). `SPECIFICATION.md`
governs. Where this file and the specification disagree, the specification is right and this file
is wrong. Identifiers here are pointers, never restatements. This plan's commit amends the
specification in the places listed under [Pointers](#pointers).

## Execution brief

### Scope

The §8.1 GUI increment for Phase 2, which is phase criterion 4:

- load a structure;
- build stages 1–6 from the shell, and inspect each stage's artefact as it lands;
- override the contour by hand, and run the edit through to a mesh.

The packaging probe gains the geometry pipeline's binary payloads, and **Gmsh**
([§8.2.2 B8](#pointers)). The package adds **VER-55**. It touches:

- the interface and API: IF-09, QR-11, FR-27;
- the stage-4 and stage-5 behaviour: FR-07, FR-08, FR-09, CON-04, FR-06;
- licensing and packaging: CON-09, CON-10, CON-11, RSK-13;
- the shell's scope: RSK-15.

No weak form, no gate threshold and no case key changes.

**This brief runs to about 2,600 words, over its 1,200-word target.** There are three reasons.

- A hand edit crosses two frames and three provenance fields, and each crossing is a way to write a
  plausible wrong geometry.
- Two author rulings, B8 and B9, change what the package must ship.
- The probe's new payload set is the RSK-13 surface itself.

The package is not split. The viewers and the editor share one new seam, the artefact hook (D1).
Without the editor, the viewers do not meet criterion 4.

### Pointers

- **Normative:**
  - IF-09, QR-10, QR-11, FR-27, ADR-004 and its packaging NOTE;
  - CON-09, CON-10, CON-11, CON-13;
  - §5.2 rows 1–6, §5.2.1 and its NOTE on a supplied fixture;
  - the §5.3.1 NOTEs on `inputs:` and on `geometry.contour`, and the §5.3.2 canonical-serialisation
    NOTE;
  - §8.1 (the GUI increments), §8.2.1 A4;
  - VER-43, VER-44, VER-51, VER-52, VER-53.
- **Amended in this commit:**
  1. §8.2.2 gains **B8**: the bundle carries Gmsh. The probe imports it and exercises it, the
     notice names it, and netgen stays the default.
  2. §8.2.2 gains **B9**: the hand editor may start from a loop that stage 4's gate refused.
  3. The §5.3.1 NOTE on `geometry.contour` states how a hand edit's provenance is written (D5).
- **Amended with the code:**
  - the VER-55 row in §7.2;
  - Appendix A: IF-09, QR-11, FR-27, CON-09, CON-10 and CON-11 gain VER-55;
  - the ADR-004 packaging NOTE's payload list;
  - the recount line.
- **Read first:**
  - [WP14](wp14-gui-shell-packaging-probe.md) §Design 2 and 4, and their Outcomes;
  - [WP15](wp15-live-convergence-and-viewer.md) D1, D2, D7–D10, and their Outcomes;
  - [WP21](wp21-cad-assembly-and-meshing.md) D5 and D14 (the region key; `inputs.profile`'s
    refusals);
  - `.knowledge/07` §5.

### Decisions

| # | Decision | Choice | Why / source |
|---|---|---|---|
| D1 | How a stage's artefact reaches the shell | A third structural hook, `ArtefactHook.__call__(name, schema, hash, cached)`, is added in `core/stages.py`. It is threaded as `on_artefact` through `run_case` → `run_document` → `_walk`, and fires **after** the artefact is in the store, or is found there. The child forwards it as `Produced(name, schema, hash, cached, store)`. The shell reads the payload through `Store(store).get(schema, hash)` | `StageHook` fires *before* a stage and carries no hash. Parsing a caption is barred (VER-43). A cached stage still has an artefact to inspect, so, unlike a cached solve (WP15 D4), it is not silent |
| D2 | The hook is not an input | The stage keys are computed before the hook is bound, and are never passed to it | WP15 D2. VER-55 runs the same case watched and unwatched, and requires one run record and one set of store entries |
| D3 | Building geometry | `RunRequest` gains `upto`. The **Build geometry** control runs `upto="mesh"` through the same spawned child and the same cancel token. It is enabled only when the resolved case walks stage 6 | The CLI's `run --upto` already writes a truncated walk (`io/run.py` `run_case`). A second driver would be a second pipeline |
| D4 | Frames on screen | The structure, density, reduced-map and contour views draw in the **stage-1 frame**, the frame of the profile document. The membrane slab is drawn at `centre_z_nm ± thickness_nm/2`. The region and mesh views draw in the **model frame**. Every view's axis caption names its frame | Stage 5 shifts `z ← z − centre_z_nm` (§5.3.1 NOTE on `geometry.contour`). An editor that wrote stage 5's model-frame vertices back would shift them twice on the next run. [Design §1](#1-two-frames-one-tab) |
| D5 | What a hand edit writes | A `nanopnp/profile/v1` document with these values: <ul><li>`provenance.source: hand-edit` (never a reference source);</li><li>`sha256`: the canonical `profile_digest` of the profile it was edited from, or, under B9, the stage-3 payload digest that stage 4 would have recorded;</li><li>`citation`: the parent's name.</li></ul> The measurements are re-derived from the edited vertices, and the file is named by its own digest | FR-27; §5.3.1 NOTE, amended here. The loader re-checks every recorded measurement against the vertices (`mesh/profile.py`), so a stale provenance block cannot be written. Editing the reference fixture must stop it being the reference: `require_reference` then refuses it |
| D6 | How the edit enters a run | `io/case.py` gains `with_profile(document, path) -> CaseDocument`. It does four things: <ul><li>removes `structure:`;</li><li>resets `geometry.density` and `geometry.contour` to their defaults;</li><li>sets `inputs.profile: {path, format: profile1}`;</li><li>keeps everything else.</li></ul> The result is validated by the same loader. The shell writes a **new** case file beside the original, which is never modified | `substitute` cannot create an absent block. The WP21 D14 refusals then accept the document by construction, and a CLI user gets the identical file. A derived file keeps both runs reproducible |
| D7 | Paths the shell writes | Absolute, for the structure picked by the file dialog and for the edit's profile. The derived case's other `inputs` entries are copied verbatim | Case paths resolve against the process's working directory (`docs/guide/case-files.md`), and a double-clicked shell has no meaningful one. Inputs are hashed by content, not by path (§5.3.2), so no key moves |
| D8 | What the editor enforces | **On every edit:** `PoreProfile`'s own validators (finite, `r ≥ 0`, no repeated vertex, simple, non-zero area), reported naming the vertex. A document that would fail them cannot be saved. **On demand, and recorded without enforcing:** the §5.2.1 criteria (axis clearance, spacing, feature size, the radius-profile band). These are measured in a spawned child against the case's stored stage-1 and stage-3 artefacts, with thresholds taken from that measurement and never written in `gui/`. Stages 5 and 6 apply their own gates as always | A hand edit enters as a supplied profile, which the §5.2.1 NOTE gates only on validity, simplicity and topology. The same validator that loads the file checks it, so the two cannot disagree. The criteria stay visible, because silently accepting a contour inside the probe radius is the plausible wrong geometry |
| D9 | Measuring without refusing | `geometry/contour.py` gains `measure(loop, *, spacing_nm, planes_nm, probe_nm) -> record`, which returns every criterion's value, threshold and (r, z). `gate` becomes `measure` plus a raise at the first failure. Its messages and its record are unchanged | One implementation of the criteria. VER-51's tests hold `gate` unchanged, and VER-55 holds `measure` equal to the stage-4 summary's `gate` record on that artefact's own loop |
| D10 | Seeding after a refusal (B9) | If stage 4's gate refused the contour, the editor can start from `condition()` recomputed on the stored stage-3 map with the case's contour parameters. The recomputation runs in the spawned assess child. The editor shows the refusal's QR-12 diagnostic and marks its (r, z) | Author ruling, 29 September 2026. A refused gate writes no artefact (QR-12), so there is otherwise nothing to override. The source work's manual vertex editing is exactly this recovery |
| D11 | Density views | <ul><li>**Stage 2:** the axial section of the 3D map at `y = 0`, over `x ∈ [−R, R]`, so the Cₙ asymmetry shows.</li><li>**Stage 3:** the mean, and both variances (FR-06, CON-04), selectable.</li><li>Density and mean share a fixed [0, 1] scale (VER-49's bounds). Each variance is shown on its own labelled scale.</li><li>Pixel centres sit at the grid's own node coordinates.</li><li>The loaded arrays are read off the Qt thread.</li></ul> | Placing bin j at its edge is the `pqr2grid` erratum (`.knowledge/04` §1.2). The display must not reintroduce it. [Design §2](#2-where-a-pixel-sits) |
| D12 | Mesh view | The render child gains a mesh request. It draws the stage-6 MSH through `ngsolve.webgui`, by material, into a file under the run directory's `viewer/`. The artefact's gate summary is shown beside it: SICN, gamma, the worst element's location, and the wall-size gate | The pore wall is 0.05 nm against a 250 nm reservoir, and webgui's zoom already covers that span. One renderer path (WP15 D8–D10, D14) |
| D13 | Drawing | Hand-stroked `QPainter` over a Qt-free transform, as the convergence plot is drawn. There is no new plotting dependency. The images are `QImage`s over RGBA bytes built in the view-model from a fixed perceptual lookup table | WP15 D7. The transform and hit-testing are asserted Qt-free |
| D14 | Editor operations | Move a vertex (drag or typed coordinates), insert a vertex at an edge's midpoint, delete a vertex, undo and redo. There is no automatic smoothing or simplification | The pipeline's conditioning is stage 4's, keyed by its parameters. An editor that re-conditioned would be an unkeyed stage 4 |
| D15 | Layout | One new tab, **Geometry**, after Case. It holds a stage list (name, status, hash, cached) and one view pane per stage: structure summary, density, contour/editor, region record, mesh | Thin increment (RSK-15). There is no 3D molecular view |
| D16 | The bundle carries Gmsh (B8) | Author ruling, 29 September 2026. `numerics.mesh.backend: gmsh` works in the bundle, and netgen stays the default | The bundle is already GPL-2+ under CON-11, so the licence is no obstacle. CON-10 holds: nothing on the default path imports it |
| D17 | The probe's new payloads | `PAYLOADS` gains `MDAnalysis`, `gemmi`, `skimage`, `shapely` and `gmsh`. `--selftest` **exercises** each once and fails naming the payload: <ul><li>MDAnalysis and gemmi each read a three-atom structure;</li><li>`find_contours` runs on a 3×3 array;</li><li>a Shapely polygon is checked with `is_valid`;</li><li>Gmsh meshes a unit square and finalises.</li></ul> `LICENSES-BUNDLE.md` gains a row per payload, with Shapely's GEOS (LGPL-2.1). `excludes` is unchanged | RSK-13 is detected through compiled extensions that import but fail to load their libraries. The phase plan names MDAnalysis, scikit-image and Shapely. gemmi is stage 1's other compiled reader, and Gmsh follows B8 |
| D18 | `profile_digest` | Moves to `mesh/profile.py`, and is re-exported from `geometry/region.py` | The editor needs the region key's digest without importing stage 5 |

### Work items

In dependency order.

1. `core/stages.py`: `ArtefactHook`. `io/run.py`: `on_artefact` threaded through `_walk`, after
   `Store.put` or the cache hit (D1, D2).
2. `mesh/profile.py`: `profile_digest` moved, and a `HAND_EDIT_SOURCE` constant (D5, D18).
   `geometry/contour.py`: `measure`, with `gate` built on it (D9).
3. `io/case.py`: `with_profile` (D6).
4. `gui/solver.py`: the `Produced` event and `RunRequest.upto` (D1, D3). `gui/run_model.py`:
   `RunControl.start(..., upto=)`.
5. `gui/geometry.py` (a Qt-free view-model):
   - `StageList`;
   - `ImageModel`: the array to RGBA bytes, the transform, and the orientation;
   - `ProfileEditor`: the operations, undo, the validators, `save` to a profile and a derived case.

   Numpy is imported inside functions only (`CLAUDE.md`).
6. `gui/assess.py` (child side, spawned): measure an edit (D8) and seed after a refusal (D10). It
   imports `geometry.contour` inside the function. Without the `structure` extra it is refused
   naming the extra.
7. `gui/render.py`: the mesh request (D12).
8. `gui/widgets/geometry.py`, and `app.py`'s sixth tab (D13, D15).
9. `gui/probe.py`, `packaging/nanopnp-probe.spec`, `packaging/LICENSES-BUNDLE.md`, and the
   `bundle` job (D16, D17). Measure the collection that each payload needs. `.knowledge/07` §5
   gains what is learned, marked **[tested]**.
10. `docs/guide/desktop.md`: the Geometry tab. `CHANGELOG.md` under `v0.9.0-alpha.8`. The
    specification rows listed under [Pointers](#pointers).

### Verification

**VER-55**, *Geometry pipeline surfaced in the desktop shell*, is proposed here and written into
§7.2 with the code.

| Test file | Tier | Asserts |
|---|---|---|
| `tier1/test_artefact_hook.py` | 1 | Checks three things. <ul><li>On a supplied-profile case, the hook fires once per walked stage, after its store entry exists, with the run record's `schema` and `hash`.</li><li>A re-run reports `cached=True`.</li><li>Watched and unwatched runs give one run record and one set of store entries. The hook is not reachable from any stage key (D1, D2)</li></ul> |
| `tier1/test_gui_geometry.py` | 1 | Six checks.<ul><li>**Orientation.** A planted off-axis Gaussian's maximum lands in the pixel whose centre is its `(r, z)`, with the top row at maximum z and r increasing to the right. The stage-2 section is symmetric about `x = 0` for an axisymmetric map (D11, Design §2).</li><li>**Edit operations.** Insert, delete, move, undo and redo return exactly to the prior vertices.</li><li>**Refused saves.** A self-crossing, `r < 0` or repeated-vertex edit is refused, naming the vertex, with the loader's text.</li><li>**The null edit.** Saved, it reproduces the parent's vertices bitwise. Its provenance has `source: hand-edit` and `sha256` equal to the parent's `profile_digest`, and every measurement re-derives.</li><li>**The reference fixture.** Edited, it is refused by `require_reference`.</li><li>**The derived case** (`with_profile`) has no `structure:`, loads and resolves through `load_case`, and is otherwise equal to the original, field by field over `case_fields()` (D5–D7)</li></ul> |
| `tier1/test_gui_viewmodels.py` | 1 | The fresh-process test lists `gui.geometry` and `gui.assess`. Beyond the existing set, it adds `MDAnalysis`, `skimage`, `shapely` and `gmsh` to the modules that must be absent. The no-vocabulary grep covers the new modules |
| `tier1/test_contour.py` (extend) | 1 | `measure` equals `gate`'s record wherever `gate` passes. Where `gate` raises, `measure` reports the same criterion failing with the same value (D9). VER-51 is unchanged |
| `tier1/test_gui_solver_process.py` | 1 | A spawned `upto="mesh"` run of a supplied-profile case emits `Produced` for region, then mesh, and then `Finished`. Cancelling it writes no artefact |
| `tier1/test_gui_render.py` | 1 | The mesh request writes a scene whose element count is the MSH's triangle count, under `viewer/`, and never as an artefact |
| `tier1/test_gui_probe.py`, `test_gui_widgets.py` | 1 | The probe's declared payloads and imports agree in both directions, and the notice has a row for every payload. `test_gui_widgets.py` runs only on Windows and macOS: six tabs, and a drag in the editor widget moves the view-model's vertex |
| `tier2/test_gui_geometry_2wcd.py` | 2 | This test uses the prepared 2WCD, through `prepared_2wcd`, and checks four things. <ul><li>A spawned build emits `Produced` for stages 1–6 in order.</li><li>`measure` on stage 4's loop equals its summary's `gate` record exactly.</li><li>The null edit, run through `with_profile`, gives stage 5 a model-frame profile equal to the original's to the bit, and a mesh whose **content hash** equals the original's.</li><li>Moving the constriction vertex outward by 0.1 nm changes both hashes, and the manifest records `inputs.profile` by content and no stage 1–4 artefact (D4–D6, Design §3). The runtime is measured and reported</li></ul> |
| `tier1/test_gui_assess.py` | 1 | On a synthetic reduced map whose contour fails the feature-size criterion, the seed returns `condition()`'s loop and the refusal's criterion and (r, z). The saved edit's `sha256` is that map's payload digest (D10) |
| CI `bundle` | — | The frozen `--selftest` exercises every payload, Gmsh included, on `windows-latest` (D16, D17) |

```bash
uv run pytest tests/tier1/test_artefact_hook.py tests/tier1/test_gui_geometry.py tests/tier1/test_gui_viewmodels.py -v
uv run pytest tests/tier2/test_gui_geometry_2wcd.py -v
.claude/hooks/gate.sh run
```

### Out of scope

- **Shipping the shell, rather than the probe, as the bundle's executable:** the Phase 4 GUI
  increment, with QR-10.
- **A 3D molecular view, and editing stages 1–3:** not part of §8.1's increment (RSK-15).
- **Adding `with_profile` to `nanopnp.PUBLIC`:** a later decision in `test_public_api.py`.
- **The pipeline guide and example 06:** WP25.
- **Anchoring case paths to the case file:** unchanged, and documented.

### Open questions

None. B8 and B9 were ruled by the author on 29 September 2026, before this commit.

## Design

### 1. Two frames, one tab

Stage 1 places the axis on z at r = 0, with `z = â·x`, and stage 4's loop stays in that frame. Stage
5 maps each vertex `(r, z_s) ↦ (r, z_s − c)`, with `c = geometry.membrane.centre_z_nm` (region.py
`to_model_frame`). The membrane therefore occupies `|z_m| ≤ t/2`, which is
`c − t/2 ≤ z_s ≤ c + t/2` in the stage-1 frame. The editor draws that slab in the stage-1 frame and
writes `z_s`.

Suppose an editor read the region record's model-frame vertices and wrote them back. The next run
would give `z_s − 2c`, a shift that is invisible at `c = 0`, which is ClyA's value (ruling 12). A
test at `c = 0` cannot catch it, so VER-55's derived-case check runs at `c = 1.5` nm as well.

### 2. Where a pixel sits

`ReducedMap.r_nm[j] = j·h` is a bin **centre** (`symmetry/reduce.py`), and the density axes are
node coordinates (`DensityGrid.axis_nm`). An image of `n_r` columns therefore spans
`[−h/2, (n_r − ½)h]`, and pixel j is centred on `j·h`. Drawing the image on `[0, n_r·h]` shifts
every wall outward by h/2, which is 0.025 nm at the default spacing. That is the same order as
stage 4's feature tolerance, and it is the `pqr2grid` erratum again. The contour overlay uses the
profile's own coordinates, so a mismatch shows as the overlay sitting off the isolevel. The
orientation test pins the mapping.

### 3. Why the null edit meshes to the same content hash

- `profile_digest` covers the whole validated document, provenance included. A null edit changes
  `source`, `sha256` and `citation`, so the region's **key** moves, and stage 5 re-runs.
- Stage 5 reads only the vertices and the membrane and reservoir sections. Its model-frame profile,
  and therefore the glued region, are equal to the bit.
- The mesh key is the recipe, which moves with the region key. The mesh **content hash** is a
  function of the geometry, which is identical, on one platform, because netgen is deterministic in
  a process but not across platforms (`.knowledge/07` §4).

The oracle is therefore: key changed, content hash equal. That asserts that the edit's route adds
nothing to the geometry. A 0.1 nm move at the constriction must change both hashes.

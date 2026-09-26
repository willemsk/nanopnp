# WP21 — CAD assembly and graded meshing from a profile (stages 5 and 6)

**Status: planned, not started.** Written 26 September 2026, after WP20 merged (PR
[#41](https://github.com/willemsk/nanopnp/pull/41), to be tagged `v0.9.0-alpha.4`). This package
inherits stage 4's `nanopnp/profile/v1` document. It is in the stage-1 frame, spaced at least h
apart, with feature size above 2h (WP20 D9, D10). It also inherits `ReferenceGeometry` and
`plane_crossings` in `mesh/reference.py`, stage 6's ingestion gate (VER-27, VER-10) in
`mesh/ingest.py`, and `refuse_walk`, which it retires. Stage 5 is the last gap between a structure
and a solve.

This is a work package of the [Phase 2 plan](phase-2-geometry-pipeline.md). `SPECIFICATION.md`
governs: where this file and the specification disagree, the specification is right and this file
is wrong. Requirement identifiers here are pointers into it, never restatements of it. This plan's
commit amends the specification and the phase plan in the places listed under
[Pointers](#pointers).

## Execution brief

### Scope

- **Stage 5, `region` (FR-09).** It turns any profile, from stage 4 or `inputs.profile`, into the
  tagged (r, z) region: the model-frame shift, the membrane quadrilateral with a derived inner
  edge, the reservoir half-disc, the fragmentation, and a junction gate. It emits a declarative
  region record.
- **Stage 6, generating (FR-10).** The region is meshed under the §5.2.2 size fields, with
  `wall_h_nm: auto` resolved and `size_scale` applied. The mesh passes the same VER-27 and VER-10
  gates as an ingested mesh, plus a wall-size gate. Stages 7, 10 and 11 read the generated mesh
  from the stage-6 artefact.
- **The walk.** A `structure:` case runs from structure to report without `inputs.mesh`.
  `inputs.profile` is consumed. `refuse_walk` is removed.

It adds VER-52 and VER-53 and retires RSK-05.

**This brief runs to about 2,700 words, over its 1,200-word target.** Two of the phase plan's
premises failed on measurement, and each moves a number or a verdict.
[Design §1](#1-the-membranes-inner-edge): the mid-point chord leaves the pore body on both
the reference fixture and 2WCD. [Design §2](#2-the-wall-size): NUM-30 read literally puts
0.27 nm elements on the wall at 0.05 M, five times the validated mesh's size.

### Pointers

- **Normative:** FR-09, FR-10, FR-27, QR-08, QR-12, CON-10; NUM-30, NUM-34; §5.2 rows 5–6;
  §5.2.1 NOTEs on the membrane junction, the vertex counts and a supplied fixture; §5.2.2; §5.3.1
  NOTEs on `inputs:`, `structure:`, `inputs.mesh.groups` and a solid without a permittivity;
  §5.3.2; §6.3; RSK-05; VER-10, VER-27, VER-28.
- **Amended in this commit:**
  1. §5.2 row 5: inputs, outputs and gate (D2–D6). Row 6: the wall-size gate (D9).
  2. §5.2.1: a NOTE on the membrane junction for any profile (D3, D4).
  3. §5.3.1: a NOTE on `geometry.membrane`, `geometry.reservoir` and `numerics.mesh` (D7, D8,
     D14). The `inputs:` NOTE now says `inputs.profile` is consumed. The `structure:` NOTE's walk
     sentence now says that the walk runs the whole pipeline. The NOTE on a solid without a
     permittivity now covers generated meshes (D11).
  4. §5.3.2 row 5: a region record, not a BRep (D5). Row 6: the generated mesh's key (D10).
  5. §6.8 NUM-30: a NOTE on the wall target's ceiling (D7).
  6. The phase plan's *Membrane inner edge* decision is superseded by D3, with the reason.
- **Code:** `mesh/reference.py` (`ReferenceGeometry`, `plane_crossings`, `name_edges`,
  `junction_report`, the size constants); `mesh/ingest.py` (`MeshStage`, `ingest`,
  `check_solid_permittivities`); `mesh/profile.py` (`PoreProfile`, `load_profile`);
  `mesh/adapter.py` (`from_ngsolve`, `write_msh41`, `content_hash`); `io/artefact.py`
  (`MeshArtefact`); `core/stages.py`; `core/scaling.py` (`debye_length_nm`);
  `materials/electrolyte.py` (ionic strength, `permittivity_0`); `io/case.py` (`MeshSpec`,
  `MembraneSpec`, `ReservoirSpec`, `_require_runnable`, `_UNCONSUMED_INPUTS`, `refuse_walk`,
  `STRUCTURE_WALK`, `require_mesh`); `io/run.py` (`PIPELINE`, `_selected`, `WORKSPACE_STAGES`,
  `_WEIGHTS`); `io/manifest.py` (`_geometry_group`); `sweep/plan.py` (`WARM_START_BARRIERS`,
  `_barriers`); `charge/stage.py`, `solve/stage.py` and `post/stage.py` (their `require_mesh`
  call sites); the reproduction check of the §5.3.2 QR-08 NOTE.

### Decisions

| # | Decision | Choice | Why / source |
|---|---|---|---|
| D1 | Stages | Stage 5 is `region`: number 5, inputs `("case", "contour")`, schema `nanopnp/region/v1`, target `nanopnp.geometry.region:RegionStage`, no extra, and a workspace stage. The `mesh` stage's inputs become `("case", "region")`. `PIPELINE` inserts `region` after `contour`. `_selected` drops `region` when `inputs.mesh` is supplied, and drops stages 1–4 on an `inputs.profile` case | FR-27. Stages 5 and 6 import netgen and NumPy only, deferred, so `inputs.profile` runs on a base install. `CLAUDE.md` places CAD assembly in `geometry/` |
| D2 | Model frame | `z_model = z_profile − geometry.membrane.centre_z_nm`, applied to every vertex before anything else, for stage-4 and supplied profiles alike | The phase plan's model-frame decision; the §5.3.1 NOTE on `geometry.contour` |
| D3 | Membrane inner edge | On each plane `z = ±t/2`, take the **lumen-adjacent body interval** `[r₁, r₂]`: the two smallest `plane_crossings`. The inner edge is the chord between those intervals with the **largest minimum clearance** to the loop, searched on the 63 × 63 interior points `rₖ = r₁ + (r₂ − r₁)k/64`. `ReferenceGeometry` keeps its drawn (2.0, 3.5) corners | [Design §1](#1-the-membranes-inner-edge). The phase plan's chord between the intervals' mid-points exits the body through the cap's cleft on the reference fixture and on 2WCD, and splits the electrolyte in two. Any chord inside the body yields the same region, so the one with the widest margin is chosen. The reference mesh keeps its hash |
| D4 | Junction gate | The stage refuses, naming the criterion, the value, the threshold and the (r, z): a plane with fewer than two crossings, naming the profile's z extent and `centre_z_nm`; a best chord whose clearance is below `JUNCTION_CLEARANCE_NM = 0.01`; any domain assembled as other than one face, naming each face's centroid and area; any vertex not strictly inside the reservoir disc; and a membrane whose innermost radius on either plane differs from that plane's `r₂` by more than `TOL_NM`. The last criterion is VER-28's measure made generic | FR-09, QR-12. 0.01 nm is 10⁵ times OCC's confusion tolerance and a fifth of the smallest half-thickness a stage-4 body can have, h. Measured clearances: 0.237 nm on the fixture and 0.302 nm on 2WCD |
| D5 | Stage-5 artefact | `RegionRecord`, a pydantic model written as `region.yaml`. It holds the profile vertices in the model frame, the membrane (thickness, `centre_z_nm`, the chord and its clearance), the reservoir radius, the axis split heights, the junction radii, each face's area and each edge name's count. `build_region(record)` rebuilds the glued, named OCC shape from the record alone. Key: `content_hash("nanopnp/region/v1", {membrane, reservoir, constants: {chord grid, clearance, reservoir overshoot}}, inputs={"profile": …})`. The profile input is the stage-4 key, or the canonical digest of a supplied profile's validated payload | The phase plan's stage-artefact decision: a record hashes by content, and a BRep's bytes need not be stable. §5.3.2 row 5 amended. A hand edit of a supplied profile is a new key (FR-27) |
| D6 | Edge naming | `ReferenceGeometry`'s classification chain is generalised with the chord as the membrane's inner edge. Pore-boundary edges inside the slab and right of the chord are `interface`, and the rest are `wall`. `plane_crossings` moves to `mesh/profile.py` and is re-exported | The chain and its reasons are VER-28's. The classification is invariant under the chord for the same reason the region is |
| D7 | `wall_h_nm: auto` | `size_scale × min(0.05 nm, λ_D/5)`. λ_D is §6.3's, `√(ε₀ ε_r,f⁰ RT / (2F² I))`, with `ε_r,f⁰` from the case's `electrolyte.parameters`, the case temperature, and the ionic strength I of the bulk species. It routes through `core/scaling.py` as the one implementation. An explicit number is used as given, times `size_scale`. A wall size coarser than λ_D/5 is logged and recorded, not refused | [Design §2](#2-the-wall-size). The ceiling is §5.2.2's pore-boundary maximum, which the validated reference used at every concentration. It governs below 1.474 M, keeps the mesh finer than the ion wall function's 0.161 nm decay length, and matches stage 4's `h_c`. `ε_r,f⁰` reproduces NUM-30's own check values. It also keeps an ablation of the permittivity correction on one mesh. NUM-30 gains a NOTE |
| D8 | Other size fields | §5.2.2's table as `ReferenceGeometry` applies it: global 10, protein 0.1, electrolyte 2.8, arc 5 and axis-in-pore 0.075 nm, each times `size_scale`. Grading 0.2 and `optsteps2d` 5 are unchanged. The axis is split at the profile's model-frame z extent | FR-10. One size table, shared by `ReferenceGeometry` and the generic path |
| D9 | Wall-size gate | After meshing, the `wall` segments' mean length must be at most 1.15 × the target and the longest at most 2.0 × the target. Otherwise the stage aborts, naming the statistic, the segment and its midpoint. Both statistics are recorded | [Design §3](#3-the-wall-size-gate). Netgen treats `maxh` as a target: measured means are 1.045–1.078 and maxima 1.25–1.62. If the wall size field is dropped, the protein's 0.1 nm field governs, and the mean doubles |
| D10 | Stage-6 artefact | Generated meshes use `MeshArtefact`, schema `nanopnp/mesh/v1`, keyed on the **recipe**: `{materials, boundaries, groups: {}, sizing: {backend, wall_h_nm resolved, its source and λ_D, size_scale, the table, grading, optsteps, the D9 constants}}`, with `inputs={"region": key}`. The canonical content hash goes in the summary and the manifest. The mesh is written as MSH 4.1 and re-read through `ingest`, which puts it through VER-27 and VER-10. A supplied mesh is keyed on content, as today | A content key would re-mesh at every store lookup, 6–8 s per member. Netgen is deterministic in one process and platform (measured), not across platforms (`.knowledge/07` §4). So the recipe is the honest key, and the content hash is the recorded fact |
| D11 | Solid permittivities | A generated mesh is gated like an ingested one: `protein` and `membrane` each need a `physics.solid_permittivities` entry, or the run aborts naming the material | The §5.3.1 NOTE exempts meshes the benchmark geometries build. A pipeline mesh carries a structure's body, so the NOTE's reason for aborting applies |
| D12 | Downstream consumers | One helper, `deployed_mesh(inputs, resolved)` in `mesh/ingest.py`, replaces `require_mesh()` at the stage 7, 10 and 11 call sites. It ingests `inputs.mesh` where one is supplied, and otherwise reads the stage-6 artefact's payload. A consumer never regenerates a mesh | One ingestion route for every consumer. Regenerating downstream would be a second chance to disagree |
| D13 | Reproduction | The QR-08 check compares the regenerated mesh's content hash with the recorded one. A difference is fatal and names the mesh and both hashes, as an input drift is | A cross-platform netgen difference would otherwise surface as a QoI mismatch with no named cause |
| D14 | Case refusals | Each is refused naming the key and its value: `backend: gmsh` (WP23); `boundary_layer: true` (FR-11, post-1.0); `geometry.analyte` on a generated mesh (FR-21, v1.0); a thickness or reservoir radius that is non-finite or non-positive; an explicit `wall_h_nm` that is non-finite or non-positive; `structure:` beside `inputs.profile`; `geometry.density` or `geometry.contour` written beside `inputs.profile`; `inputs.profile` given with `groups`, with `artefact:`, or with a format other than `profile1`; any `numerics.mesh` key away from its default beside `inputs.mesh` | The §5.3.1 upstream rule and its rule against knobs with no effect, which already refuses `size_scale` beside `inputs.mesh`. No shipped case file sets a mesh key away from its default, so VER-47's corpus is untouched |
| D15 | Sweep barriers | `structure`, `geometry` and `inputs.profile` join `WARM_START_BARRIERS`. On a generated mesh with `wall_h_nm: auto`, an axis over `electrolyte.concentration_M`, `.temperature_K`, `.parameters` or `.species` is a barrier if its values resolve to more than one wall size | Each moves the mesh, and `load_initial` would refuse the edge member by member. Below 1.474 M the wall size is constant, so ordinary salt sweeps keep their warm starts |
| D16 | Manifest | `geometry_and_mesh` gains `region` (frame shift, thickness, chord and clearance, junction radii, face areas) and a `sizing` block (resolved wall size, its source, λ_D, `size_scale`, the D9 statistics, the NUM-30 ratio). The mesh's content hash stays where it is | FR-25, §5.3.3 |
| D17 | Public API | No new name | IF-01 NOTE |

### Work items

1. **Generic assembly** (`geometry/region.py`, new): `RegionRecord`, `derive_region(profile,
   membrane, reservoir)` (D2–D4), and `build_region(record)` (D6, D8). `ReferenceGeometry`
   delegates its faces, naming and sizing to it, keeping its drawn corners. `plane_crossings`
   moves (D6). Read Design §1 first. The existing VER-28 and VER-10 tests must pass unchanged, and
   `nanopnp mesh reference` must print the same hash as before the refactor.
2. **Sizing** (`mesh/sizing.py`, new): `resolve_wall_size(resolved)` (D7) and the size table
   (D8). Read Design §2 first.
3. **Case** (`io/case.py`): the D14 refusals, `inputs.profile` removed from `_UNCONSUMED_INPUTS`,
   and `refuse_walk` and `STRUCTURE_WALK` removed with their callers. `require_mesh` becomes an
   internal of D12.
4. **Stage 5** (`RegionStage`), registered (D1) and keyed (D5).
5. **Stage 6** (`mesh/generate.py`, new, and `MeshStage`): generate from the record, gate (D9,
   D11), write, re-ingest, and emit the recipe-keyed artefact (D10). `MeshArtefact` takes either
   input form.
6. **Consumers and walk**: `deployed_mesh` (D12); `io/run.py`; the manifest (D16); the
   reproduction check (D13); the sweep barriers (D15).
7. **Specification and knowledge**: the Appendix A rows for VER-52 and VER-53 (FR-09, FR-10,
   FR-27, QR-12, CON-10); RSK-05 retired in §9; `.knowledge/04` §2 and `.knowledge/06` §8 gain the
   Design §1–§3 measurements, re-measured. The docs pages that say stages 1 to 4 run are updated,
   and CHANGELOG `v0.9.0-alpha.5` is written.

### Verification

| Test file | Tier | Identifiers | Assertion / oracle | Tolerance source |
|---|---|---|---|---|
| `tests/tier1/test_region.py` | 1 | VER-52, FR-09, QR-12 | A parallelogram body's best chord is its mid-line, with clearance half its perpendicular width. On the fixture the drawn and derived chords give face areas equal to 1e-10 relative and equal edge-name counts. A profile translated by Δ with `centre_z_nm = Δ` gives the untranslated region. On a body cut four times by a plane, the membrane meets it at `r₂`, not `r₄`. Each D4 criterion fires on a profile built to fail it, naming criterion, value, threshold and (r, z). The record round-trips, `build_region` rebuilds equal areas, the key is stable across processes and moves with each constant, and a hand edit is recorded. The stage is listed without importing netgen | Closed forms; OCC round-off, measured at 4e-13 (Design §1) |
| `tests/tier1/test_mesh_sizing.py` | 1 | VER-53, FR-10, NUM-30 | `λ_D/5` is 0.035 at 3 M and 0.27 at 0.05 M, and `auto` gives 0.05, 0.05, 0.03505 and 0.02715 nm at 0.05, 1, 3 and 5 M, crossing at 1.4741 M. `size_scale` multiplies every size, and temperature enters as √T. Each D14 refusal names its key. The D15 barrier fires on [1, 3] M and not on [0.1, 1] M | Design §2, to 1e-4 nm |
| `tests/tier1/test_mesh_generate.py` | 1 | VER-53, VER-10, CON-10 | A coarse synthetic region (`size_scale` 20) meshes, passes VER-27 and VER-10, and round-trips its content hash through MSH 4.1. Two fresh processes give one content hash. The D9 gate fires with the wall field withheld, naming the segment. Stages 5–6 in a fresh process leave `gmsh` out of `sys.modules`. A generated mesh missing a `protein` permittivity aborts naming it | Exact equality on one platform (Design §4) |
| `tests/tier2/test_region_reference.py` | 2 | VER-52, VER-53, VER-28, VER-10 | The fixture through `inputs.profile`, stages 5–6: 193 vertices and 195 edges (151 `wall`, 35 `interface`, 3 `axis`, 2 `membrane`, 2 `membrane_outer`, and one each of `cis` and `trans`); junction at 2.7524 and 4.88 nm; one node chain at the junction; no membrane element in the fluid. Element count within 0.1 % of `ReferenceGeometry`'s, and the quality band met. D9's statistics at `wall_h_nm` 0.05 and 0.035 are recorded | VER-28 counts; netgen band, `.knowledge/07` §4 |
| `tests/tier2/test_pipeline_2wcd.py` | 2 | VER-53, VER-10, FR-27, RSK-05 | The prepared 2WCD at the default sizes: stages 1–6, with `centre_z_nm` registered at test time as the profile's *trans* tip plus 1.85 nm (not a VAL-05 claim). The mesh passes VER-10 and D9. Then, at `size_scale` 4 with `pnp` and every correction off, the whole walk to stage 12. The manifest records every stage's key, and the recorded content hash equals the re-ingested payload's. Stage times are logged. The electrostatic models refuse solids (the §5.3.1 NOTE on a solid without a permittivity), so none of them can serve. If the walk exceeds two minutes, its solve half moves to `slow` and the walk is gated to stage 9 | Gates' own thresholds; the prediction is in Design §4 |

```bash
uv run pytest tests/tier1/test_region.py tests/tier1/test_mesh_sizing.py tests/tier1/test_mesh_generate.py
uv run pytest tests/tier2/test_region_reference.py tests/tier2/test_pipeline_2wcd.py --log-cli-level=INFO
```

### Out of scope

VAL-05, the axial registration of 2WCD and the reference comparison (WP22). The Gmsh backend
(WP23). The GUI's region and mesh views (WP24). The documentation increment and example 06 (WP25);
this package makes only the edits that keep the current pages true. The analyte on a generated
region (FR-21, v1.0): `PoreWithAnalyte`'s subtract-then-glue pattern is the seam, and the record
leaves room for it. Boundary layers (FR-11, post-1.0). The charge pipeline (Phase 3): a
`structure:` case solves uncharged unless `inputs.charge` is supplied. Making netgen reproducible
across platforms: D13 detects the difference and does not remove it.

### Open questions

None blocks implementation. Two choices were close calls and are reported rather than asked: D7's
ceiling and its use of `ε_r,f⁰`. Each is argued in Design §2 and written into the specification by
this commit.

## Design

### 1. The membrane's inner edge

The phase plan chose the chord between the body's radial mid-points on `z = ±t/2`. On the
fixture those are 2.2387 nm (the interval [1.725, 2.7524]) and 3.92 nm ([2.96, 4.88]). Between
z = −0.6 and +0.26, the cap's underside is re-entrant and the body is two intervals: at z = 0,
[2.00, 3.07] and [3.42, 4.72]. The mid-point chord crosses the gap between them from
(3.070, −0.016) to (3.235, 0.260), through the cleft the membrane fills. The electrolyte then
assembles as two faces. On 2WCD's stage-4 profile the mid-point chord also leaves the body.

Any chord works if it starts and ends in the lumen-adjacent interval and lies inside the body.
Such a chord leaves the same region, for this reason. Left of the chord, within the slab, lie
the lumen and body material. A fluid pocket that sat left of one valid chord and right of another
would be enclosed by the two chords, the body, and the stretches of the planes between the chord
endpoints. Those stretches lie inside the lumen-adjacent intervals, so they are body too. The
pocket would then be cut off from the unbounded fluid, but the complement of a simple polygon is
connected. So no such pocket exists.

The widest-margin chord is taken because it is the choice furthest from every failure. On the
fixture it is (1.982, 3.464) nm, with clearance 0.237 nm. The drawn (2.0, 3.5) has 0.214 nm. On
2WCD it is (1.932, 3.469), with clearance 0.302 nm. The fixture meshed with the drawn and the
derived chord gives identical connectivity (44,316 triangles), vertices within 4.2e-9 nm, and
face areas within 4e-13 relative. The grid includes each interval's mid-point (k = 32), so a
symmetric body's optimum is on the grid exactly.

### 2. The wall size

`λ_D` from `core.scaling.debye_length_nm` at `ε_r,f⁰ = 78.15`, 298.15 K:

| c (M) | 0.005 | 0.05 | 0.15 | 1 | 3 | 5 |
|---|---|---|---|---|---|---|
| λ_D (nm) | 4.293 | 1.357 | 0.784 | 0.3035 | 0.1752 | 0.1357 |
| λ_D/5 (nm) | 0.859 | 0.271 | 0.157 | 0.0607 | 0.0350 | 0.0271 |
| `auto` (nm) | 0.05 | 0.05 | 0.05 | 0.05 | 0.0350 | 0.0271 |

NUM-30 read literally gives 0.27 nm at 0.05 M and 0.86 nm at 0.005 M. That is coarser than three
length scales:

- The ion wall function `1 − exp(−6.2(d̄ + 0.01))` decays over 1/6.2 = 0.161 nm, and NUM-34's
  distance gate is a wall-resolution statement.
- Stage 4's contour is resolved at `h_c = 0.05` nm (WP20 Design §4).
- The validated reference meshed its pore boundary at 0.05 nm across its whole concentration
  range (§5.2.2).

So `min(0.05, λ_D/5)` is NUM-30's target where that is finer, and the validated mesh everywhere
else. The crossover is `λ_D = 0.25` nm, at 1.4741 M.

`ε_r,f⁰` rather than `ε_r,f(c)`: the latter gives 0.0283 nm at 3 M (ε = 51.09), 19 % finer.
NUM-30's check values are at `ε_r,f⁰`. With `ε_r,f(c)`, turning the permittivity correction off
would move the mesh, so a PNP-NS against ePNP-NS comparison would mix discretisation into the
physics. The ratio to `ε_r,f(c)`'s λ_D/5 is recorded (D16).

### 3. The wall-size gate

Measured with netgen 6.2.2606 on Linux, on 26 September 2026 (scratch prototype). The statistics
are the `wall` segment lengths divided by the target.

| Region | Target (nm) | Segments | Mean | 95th percentile | Maximum |
|---|---|---|---|---|---|
| Fixture | 0.05 | 569 | 1.045 | 1.200 | 1.600 |
| Fixture | 0.035 | 792 | 1.073 | 1.194 | 1.616 |
| Fixture | 0.0304 | 907 | 1.078 | 1.196 | 1.471 |
| 2WCD, stage 4 | 0.05 | 582 | 1.062 | 1.233 | 1.485 |
| 2WCD, stage 4 | 0.035 | 831 | 1.062 | 1.172 | 1.252 |

The bounds 1.15 and 2.0 sit above every measured value. With no wall field, the protein's
0.1 nm field and the polygon edges govern. Those edges run up to 20 times the target on the
fixture, so the mean would be about 2.

### 4. Measured on the prototype

| | Fixture, 0.05 | Fixture, 0.035 | 2WCD, 0.05 | 2WCD, 0.035 |
|---|---|---|---|---|
| Triangles | 44,316 | 49,208 | 44,688 | 50,182 |
| Minimum SICN, gamma | 0.6559, 0.6157 | 0.7402, 0.6602 | 0.7111, 0.6196 | 0.7183, 0.6506 |
| Mesh time (s) | 6.4 | 7.0 | 6.3 | 7.2 |

The 2WCD profile came from stages 1–4 on the prepared file in 25 s. It has 161 vertices, a
constriction of 1.630 nm at stage-1 z = 3.125, and a *trans* tip at z = 2.779. Registered at
`centre_z_nm = 4.629`, its planes cut [1.630, 2.837] and [3.089, 4.826]. The reference mesh
generated twice in fresh processes gave one canonical hash, `2fbf66ef…`.

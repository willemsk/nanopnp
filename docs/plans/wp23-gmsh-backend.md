# WP23 — The Gmsh mesher backend

**Status: delivered, 29 September 2026.** Written 29 September 2026, after WP22 merged on `main`
(`32fecf1`, to be tagged `v0.3.0-alpha.6`). This package inherits stage 5's glued, adjacency-named
region and its `nanopnp/region/v1` record (WP21 D5, D6), and stage 6's route: size, mesh, write
MSH 4.1, re-ingest through VER-27 and VER-10, then the D9 wall-size gate, keyed on the recipe with
the content hash recorded (WP21 D9–D13). It also inherits `numerics.mesh.backend`, which is already
in the schema, classified as a configuration path and refused naming WP23 (WP21 D14). WP22's D10
leaves this package one record to make on the new backend.

This is a work package of the [Phase 2 plan](phase-2-geometry-pipeline.md). `SPECIFICATION.md`
governs: where this file and the specification disagree, the specification is right and this file
is wrong. Requirement identifiers here are pointers into it, never restatements of it. This plan's
commit amends the specification in the places listed under [Pointers](#pointers).

## Execution brief

### Scope

- **The optional Gmsh backend of ADR-002, at stage 6 only.** `numerics.mesh.backend: gmsh` meshes
  the stage-5 region under the §5.2.2 size table with the `gmsh` API, called directly (CON-12,
  §5.2.2). The result joins netgen's route at `write_msh41`, so every gate is unchanged.
- **CON-10 kept:** the default path never imports `gmsh`, and a missing extra is refused by name.
- **VER-54**, and the Gmsh leg of WP22's D10 record.

**This brief runs to about 2,450 words, over its 1,200-word target.** The phase plan expected a
plain adapter. The prototype found that Gmsh, given only the §5.2.2 table, clears the VER-10 gate
on the reference fixture at 0.3143 against 0.3, and fails it at `size_scale` 2 and 4. Netgen passes
with margin because it restricts element sizes by itself near short edges, thin strips and domain
boundaries ([Design §2](#2-the-size-field)). Gmsh does not. D3 and D4 make those restrictions
explicit, and each one moves a verdict.

### Pointers

- **Normative:** ADR-002, CON-10, CON-12, FR-10, QR-12, IF-06; §5.2 rows 5–6; §5.2.2; the §5.3.1
  NOTE on `numerics.mesh`; §5.3.2 row 6; §8.2.2 B7; VER-10, VER-27, VER-53.
- **Amended in this commit:**
  1. §5.2 row 5: stage 5 assembles with `netgen.occ` alone. The Gmsh backend meshes that region
     and does not assemble its own (D1).
  2. §5.2.2: "an `optimize("Netgen")` pass" becomes "the backend's own optimisation pass" (D5). A
     NOTE on the Gmsh backend's size field is added (D3, D4).
  3. §5.3.1 NOTE on `numerics.mesh`: the WP23 refusal becomes the Gmsh contract (D8, D9).
- **Code:** `geometry/region.py` (`build_region`, `name_region`, `DOMAINS`); `mesh/sizing.py`
  (`SIZES`, `GRADING`, `apply_sizes`, `resolve_wall_size`); `mesh/generate.py` (`BACKEND`,
  `sizing_parameters`, `mesh_shape`, `generate`); `mesh/adapter.py` (`MeshData`, `write_msh41`);
  `mesh/ingest.py`; `core/stages.py` (`MissingExtraError`); `io/case.py` (`_check_generation`);
  `io/defaults.py` (`CONFIGURATION_PATHS`); `sweep/plan.py` (`WARM_START_BARRIERS` already names
  `numerics.mesh`, so a backend axis severs warm starts with no change); `.github/workflows/ci.yml`.

### Decisions

| # | Decision | Choice | Why / source |
|---|---|---|---|
| D1 | Where Gmsh enters | **Stage 6 only.** Stage 5 still assembles and gates with `netgen.occ`, and its key does not change. The Gmsh backend meshes the glued, named shape that `build_region` rebuilds from the record. §5.2 row 5 loses "Gmsh OCC Python API optional" | One assembly, one junction gate and one region key. A Gmsh OCC assembly would re-implement WP21 D3–D6 (booleans, the chord, naming by adjacency) as a second place to disagree. NGSolve is a core dependency, so netgen is always present |
| D2 | The handoff | `region_graph(shape) -> RegionGraph` in `geometry/region.py` returns the vertices, keyed by topological identity (`.knowledge/07` §4). Each unique edge is (name, end vertices, kind), where kind is `segment` or `arc`, an arc of the reservoir circle about the origin. Each face is (name, edge ids). An edge that is neither is refused, naming its midpoint (QR-12). The graph's edge-name counts and face areas must equal the record's. Gmsh's built-in `geo` kernel builds it: points, lines, arcs, one curve loop per face oriented counter-clockwise, plane surfaces, and one physical group per name | The coordinates are the netgen shape's own, bit for bit. Faces share curves, so they are conformal by construction. No BREP passes between netgen-occt 7.8.1 and Gmsh's own OpenCASCADE. A clockwise loop would mesh inverted elements (§5.2.2 NOTE), so orientation is fixed here once, as `_pore_face` fixes it for OCC. Measured: 193 vertices and 195 edges on the fixture, and all 185 profile vertices survive as mesh nodes ([Design §1](#1-the-handoff)) |
| D3 | The size field | The same table and wall size (`SIZES.scaled`, `resolve_wall_size`), classified by one function shared with `apply_sizes`. Each source is a `Distance` and `Threshold` pair giving `h(d) = h_s + g·d`, with `g = GRADING = 0.2`, capped at the global size. The sources are `wall` at the wall size, the reservoir arc (`cis`, `trans`, `membrane_outer`) at `arc_nm`, and the axis inside the pore at `axis_in_pore_nm`. The boundaries of `protein` and `electrolyte` are also sources, at their domain sizes, and each of those faces gets a `Constant` field inside. The background is their `Min`. `MeshSizeFromPoints`, `MeshSizeFromCurvature` and `MeshSizeExtendFromBoundary` are 0, and `MeshSizeMax` is the global size. `Sampling` is `⌈L_max/h_s⌉ + 2` per source | [Design §2](#2-the-size-field). Netgen grades outwards from a face's `maxh`, and a Gmsh `Constant` field does not. Without the domain-boundary sources the fixture's minimum gamma is 0.3143, in the membrane beside `interface`; with them it is 0.5841. `ExtendFromBoundary` instead doubles the element count (95,103) |
| D4 | Restrictions netgen makes implicitly | **(i) Short curves.** A vertex whose shortest incident curve is shorter than the smallest target of its incident curves becomes a source at that length, graded at g, with one field per distinct length. **(ii) The membrane strip.** `membrane` is sized as D3 sizes the other two domains, at the membrane thickness t, with a `Constant` inside and a graded source on its boundary. t is **not** scaled by `size_scale`, because it is a feature size and not a table entry. Neither is applied to netgen, so its meshes and keys do not move | [Design §2](#2-the-size-field). Without them the fixture fails VER-10 at `size_scale` 2 (gamma 0.2084, beside a 0.0412 nm profile edge) and at 4 (0.2348, where the membrane strip meets the arc). With both, minimum gamma is 0.5840, 0.5241, 0.5655 and 0.5072 at `size_scale` 1, 2, 4 and 8. **Close call:** restricting only below half the target keeps 0.5841 at 1 and drops to 0.3300 at 4. Binning the lengths to powers of √2 costs 0.125 at 1. An ungraded cap leaves 0.1287 at 8 |
| D5 | Mesher settings | `Mesh.Algorithm` 6 (Frontal-Delaunay), `Mesh.Smoothing` 5, `General.NumThreads` 1 and `Mesh.MaxNumThreads2D` 1 | [Design §3](#3-mesher-settings). Algorithm 5 gives 10 % more triangles at a mean gamma of 0.95 against 0.99; MeshAdapt (1) is slower and worse. Smoothing 5 is §5.2.2's optimisation pass on this backend, where netgen's is `optsteps2d` 5: +0.01 on the minimum for 1.2 s. One thread keeps the mesh a function of the recipe (D13 of WP21) |
| D6 | Process hygiene | `gmsh.initialize(readConfigFiles=False, interruptible=False)`, `General.Terminal` 0, and messages captured with `gmsh.logger`, forwarded to `logging` at DEBUG and quoted in any error. The adapter finalises only a session it opened. In a session already open it works in its own model, restores every option it set and removes its model | IF-02 reserves standard output, and the prototype wrote nothing to it. A user's `~/.gmsh-options` would change a mesh under an unchanged key. `interruptible` installs a SIGINT handler, which is valid on the main thread only |
| D7 | Output route | Gmsh's nodes and elements become a `MeshData`: the nodes elements use, and the physical names as its materials and boundaries. From there it goes through `write_msh41`, then `ingest` (VER-27, WP21 D11, VER-10), then the D9 wall-size gate. The mesh is never written with `gmsh.write` | WP21 D10's one route in: one writer, one reader, one canonical hash, and no gate a Gmsh mesh can skip |
| D8 | The recipe key | The netgen `sizing` parameter is **byte-identical** to today's, so no stored key moves. A Gmsh recipe carries `backend: gmsh`, the wall, the table, `grading` and the gate constants. It also carries a `gmsh` block: the algorithm, the smoothing and the D3–D4 rule identifiers, with the membrane cap. It has no `optsteps2d`. The Gmsh version is recorded in the manifest's environment (already listed in `io/manifest.py`), never in the key | §5.3.2: the environment sits beside a key. WP21 D13's content-hash check names a Gmsh-version or platform drift, as it does netgen's |
| D9 | A missing extra | `backend: gmsh` resolves on any install. Stage 6 imports `nanopnp.mesh.gmsh_backend`, which imports `gmsh` at its top, only on the Gmsh branch. A `ModuleNotFoundError` for `gmsh`, or an `OSError` from the wheel's native libraries, becomes `MissingExtraError`. It names the `gmsh` extra and the underlying error, and IF-02 classifies it as a case refusal | `create()`'s handling of an extra, and the `CLAUDE.md` rule for a module reached only through one dispatch. The `OSError` (`libGLU.so.1`) is the measured failure in a bare container (`.knowledge/07` §5). Stages 1–5 are cached, so after installing the extra a re-run costs stage 6 only |
| D10 | Case and switches | `_check_generation` stops refusing `backend: gmsh`. `boundary_layer: true` stays refused (FR-11). `backend` stays in `CONFIGURATION_PATHS`, because it changes the discretisation and not the model. The Gmsh settings are constants and not case keys | WP17 D3's rule against gate thresholds as case keys, extended to mesher internals. A new key would be a v3 schema move |
| D11 | Where the tests run | Every Gmsh-dependent test goes through one helper in `tests/conftest.py`. It skips, naming the error, on `ImportError` or `OSError`, and **fails instead when `NANOPNP_REQUIRE_GMSH=1`**. CI sets that on `windows-latest` and `macos-latest`, and adds `-rs` to every pytest call so each skip names its reason. The implementation records from that output whether `ubuntu-latest` imports Gmsh, and sets the variable there too if it does | A backend whose every test can skip is untested. Main's last run skipped one test on each ubuntu leg, without naming it |
| D12 | Public surface | No new public name. `nanopnp mesh reference` stays netgen, and its hash `2fbf66ef…` is unchanged | IF-01 NOTE. The shipped reference mesh is netgen's by construction |
| D13 | D10 of WP22 on this backend | `test_val05_2wcd.py` and `test_val05_ensemble.py` record the Gmsh mesh at the default sizes beside netgen's: triangles, minimum and mean SICN and gamma. Recorded, not gated | WP22 D10 and its *Out of scope*; the phase plan's *End-of-phase report* asks for both backends |

### Work items

1. **The graph** (`geometry/region.py`): `RegionGraph` and `region_graph` (D2). They need NumPy and
   netgen only, both deferred, and are tested on every leg. Read Design §1 first.
2. **One classification** (`mesh/sizing.py`): the name-to-target function that `apply_sizes`
   and the Gmsh adapter both use (D3). `nanopnp mesh reference` must print `2fbf66ef…` after it.
3. **The adapter** (`mesh/gmsh_backend.py`, new): `mesh_region(graph, wall, sizes, *,
   membrane_thickness_nm, axis_extent_nm) -> MeshData` (D2–D7). Read Design §2 and §3 first.
4. **Stage 6** (`mesh/generate.py`): dispatch on `numerics.mesh.backend`, the D9 refusal and the D8
   key. `BACKEND` goes. The generator's docstring and the wall gate's messages stop saying
   "netgen" where they mean "the mesher".
5. **Case** (`io/case.py`): lift the refusal (D10), and bring its docstring and the §5.3.1 NOTE
   into step.
6. **Tests** ([Verification](#verification)), the `tests/conftest.py` helper and the CI changes
   (D11).
7. **Specification, knowledge and docs.** Add the VER-54 row to §7.2. Appendix A gains VER-54 in
   the FR-10, CON-10, CON-12 and QR-12 rows, with the count recounted. ADR-002 is noted as
   delivered. `.knowledge/07` §4 gets the Gmsh facts of Design §1–§3, re-measured and marked
   **[tested]**. `docs/guide/meshes.md` gets a section on the backend and its extra. Write
   CHANGELOG `v0.3.0-alpha.7`, and add the phase plan's *Delivered* note.

### Verification

| Test file | Tier | Identifiers | Assertion / oracle | Tolerance source |
|---|---|---|---|---|
| `tests/tier1/test_region_graph.py` | 1 | VER-54, QR-12 | Checked on the fixture and on the parallelogram of `test_mesh_generate.py`. The graph's edge-name counts equal the record's `edge_counts`. Every face loop closes and is counter-clockwise, and every `arc` has both ends on the reservoir circle. The vertex coordinates are the shape's own. An edge that is neither kind is refused, naming its midpoint. The graph needs no `gmsh` | Exact; the circle to 1e-9 relative |
| `tests/tier1/test_mesh_gmsh.py` | 1 (the helper, D11) | VER-54, VER-10, VER-27, CON-10, CON-12, FR-10, QR-12 | **Same region, both backends:** the parallelogram region at `size_scale` 20 passes VER-27, VER-10 and D9 on each, with equal material and boundary sets. Each domain's triangle area equals the record's, less the circular segments `R²(θ − sin θ)/2` its arc chords cut off. Every region vertex is a mesh node. A clockwise face is meshed with no inverted element. Two fresh processes give one content hash. The stage-6 key moves with the backend, and netgen's key equals a literal recorded before the change. Standard output stays empty. An open Gmsh session keeps its options. **Everywhere, even without Gmsh:** an import failure, `ImportError` or `OSError` (monkeypatched), raises `MissingExtraError` naming the extra; a netgen walk in a fresh process leaves `gmsh` out of `sys.modules`; and `uv.lock` names none of MeshPy, Triangle, TetGen, pygmsh or pygalmesh | Areas to 1e-10 relative (measured ≤ 2e-12 on both backends, Design §1); hashes exact on one platform |
| `tests/tier2/test_mesh_backends.py` | 2 (the helper) | VER-54, VER-10, FR-10, CON-10 | The fixture through `inputs.profile`, at the default sizes, on both backends: the gates hold, the vocabulary is equal, and the 185 profile vertices are nodes. Counts and quality are logged beside each other. The D9 statistics are recorded at 0.05, 0.03505 and 0.02715 nm. On Gmsh, `size_scale` 1, 2, 4 and 8 each pass VER-10, the D4 regression. **The frozen case** of WP22 D9 at `size_scale` 2 on both meshes: \|G_gmsh/G_netgen − 1\| ≤ 1e-3 | 1e-3 is 8 × the measured 1.25e-4. Netgen's own change from `size_scale` 2 to 1 is 2.0e-4, so the two backends differ by less than a refinement moves either (Design §4) |
| `tests/tier2/test_val05_2wcd.py` | 2 | VAL-05 (recorded), FR-10 | D13: the 2WCD Gmsh mesh at the default sizes, recorded beside netgen's 44,998 triangles | Recorded, not gated |
| `tests/tier3/test_val05_ensemble.py` | 3 | VAL-05 (recorded) | D13 on the ensemble | Recorded |

```bash
uv run pytest tests/tier1/test_region_graph.py tests/tier1/test_mesh_gmsh.py tests/tier1/test_mesh_generate.py
uv run pytest tests/tier2/test_mesh_backends.py tests/tier2/test_region_reference.py --log-cli-level=INFO
uv run pytest tests/tier2/test_val05_2wcd.py --log-cli-level=INFO
NANOPNP_REQUIRE_GMSH=1 uv run pytest -rs tests/tier1/test_mesh_gmsh.py   # fails, rather than skips, without Gmsh
```

Runtime: the Tier-2 file costs about 7 s (netgen) and 3.5 s (Gmsh) per mesh at the default
sizes, two further Gmsh wall sizes at about 4 s each, three coarse Gmsh meshes at under 2 s each,
and two frozen solves at about 9 s each. That is under a minute.

### Outcomes

> **Outcome — delivered as decided; D1 to D13 hold.** Measured on Linux (WSL2), Gmsh 4.15.2, netgen
> 6.2.2606, stabilisation `none` wherever a solve is quoted. VER-54's three files pass:
> `test_region_graph.py` (7), `test_mesh_gmsh.py` (13, of which 7 run without Gmsh) and
> `test_mesh_backends.py` (8, 55 s unpinned on eight cores).

> **Outcome — D2's signature takes the record.** `region_graph(shape, record)`: the record's radius
> classifies the arcs, and its counts and areas are the check. The areas are compared in closed
> form (Green's theorem over segments and arcs) to `GRAPH_AREA_RTOL` = 1e-9. They agree to 1e-15 on
> the electrolyte and 1e-12 on the membrane, so a dropped, split or bent edge fails loudly. A loop
> handed to Gmsh clockwise inverts every triangle of its face (14 of 14 on the parallelogram), which
> `test_ver54_a_clockwise_profile_meshes_with_no_inverted_element` now shows. So D2's orientation
> rule is load-bearing, and not only a precaution.

> **Outcome — D3/D4 as implemented.** Edge sources are grouped by size, one `Distance` per distinct
> size. The fixture meshes to 48,941 triangles against the prototype's 48,929, with the same minima
> at every `size_scale`:
>
> | Gmsh, fixture | Triangles | Min SICN, gamma | Wall segments; mean, p95, max ratio | Stage 6 (s) |
> |---|---|---|---|---|
> | 0.05 nm, `size_scale` 1 | 48,941 | 0.6887, 0.5840 | 654; 0.909, 1.007, 1.029 | 4.2 |
> | 0.03505 nm (3 M) | 55,047 | 0.7102, 0.6137 | 911; 0.931, 1.021, 1.051 | 4.4 |
> | 0.02715 nm (5 M) | 61,270 | 0.7003, 0.6006 | 1,159; 0.945, 1.022, 1.055 | 5.6 |
> | `size_scale` 2 | 18,510 | 0.6448, 0.5241 | 396; 0.751, 1.004, 1.023 | 1.9 |
> | `size_scale` 4 | 11,764 | 0.6753, 0.5655 | 314; 0.474, —, 1.025 | 1.8 |
> | `size_scale` 8 | 10,683 | 0.6275, 0.5072 | 310; 0.240, —, 0.687 | 1.9 |
>
> Netgen on the fixture at the default sizes: 44,316 triangles, 0.6559 and 0.6157, 569 segments,
> mean 1.045, max 1.600, in 6.7 s. `nanopnp mesh reference` still prints `2fbf66ef…` after the
> shared classification (work item 2).

> **Outcome — the frozen case (Design §4) reproduced.** At `size_scale` 2, G is 1.475574e-8 S on
> netgen's 14,511 triangles and 1.475390e-8 S on Gmsh's 18,510, so `G_gmsh/G_netgen − 1` is
> −1.244e-4 against VER-54's 1e-3.

> **Outcome — a Gmsh failure is a gate (exit 4).** `GmshMeshingError` quotes Gmsh's error and
> the end of its log. `cli/errors.py` classifies it with the stage-6 gates, because the mesh is a
> function of the recipe and a retry fails identically. The session is finalised on the way out.

> **Outcome — D8: netgen's key literally unchanged.** The coarse parallelogram case keys stage 6 as
> `afcc0833…` on `2bb1a34` and on this branch (`NETGEN_KEY` in `test_mesh_gmsh.py`). The mesher's
> version is also recorded beside the key in the mesh summary's `sizing.backend_version`, for netgen
> as well. The manifest's environment already carried it. Stage 5's key does not name the backend
> (D1), so the Tier-2 file assembles the region once for both.

> **Outcome — D13 on 2WCD.** At the default sizes Gmsh gives 49,617 triangles, minimum SICN 0.6805
> and gamma 0.5749, with a wall mean of 0.931 and max of 1.010 of the target. Netgen gives 44,762,
> 0.6267 and 0.5222, 1.055 and 1.485, in `test_val05_2wcd.py`. The 44,998 quoted above was WP22's
> figure, taken before `32fecf1` changed the C-alpha centroid's computation. `2bb1a34` gives 44,762
> as well, so the change is not this package's. `.knowledge/04` §1.4 and a WP22 Outcome carry the
> correction. The ensemble leg records the same in `test_val05_ensemble.py`, and it skips here
> without the archive.

> **Outcome — D11 revised by the author: Gmsh is required on every leg.** The PR's first CI
> run (`3358f21`, run 36548648270) was the first with `-rs`. On each of the four ubuntu legs (the
> 3.12 `check` job and the 3.11, 3.13 and 3.14 matrix legs) all 16 Gmsh-dependent tests skipped
> with `gmsh does not import: OSError: libGLU.so.1`, and nothing else skipped: 1,392 passed, 16
> skipped. So the backend ran only on the two 3.12 desktop legs. On review the author chose to
> test it on Linux too, rather than leave `require-gmsh` at `"0"` there as D11 had it. The ubuntu
> jobs, the nightly Tier 3 included, now install `libglu1-mesa`, `libxft2`, `libxinerama1` and
> `libxcursor1`. `NANOPNP_REQUIRE_GMSH` is `"1"` in the workflow's env, and the matrix field is
> gone. On `9634fa2` (run 36574260470) every ubuntu leg and macOS ran all 1,408 tests with no
> skip, and Windows ran 1,403, skipping only the 5 POSIX hook tests. Both local runs also held:
> with the variable set and `gmsh` hidden, every Gmsh test fails; without it, each skips naming
> the error. The one pre-existing Gmsh test (`test_mesh_quality.py`) now goes through the same
> fixture.

### Out of scope

- **Boundary layers** (FR-11, post-1.0), although Gmsh has the best tooling for them (§5.2.2).
- **Gmsh assembling its own region** (D1).
- **Whether the desktop bundle carries Gmsh.** It remains ADR-002's later decision, and WP24 makes
  it when the probe reaches the pipeline. Today the probe does not reach stage 6, so PyInstaller
  collects no `gmsh`. The bundle is already GPL-2+ under CON-11, so the licence alone does not
  settle it.
- **Matching netgen's element count.** The prototype is 10 % above it at the default sizes, and
  VER-54 asserts gates, vocabulary and conductance, not counts.

### Open questions

None blocks implementation. Two choices were close calls and are reported rather than asked.
D4(i)'s threshold is argued in Design §2. D4(ii)'s membrane cap is a Gmsh-only size, because
netgen already meets it implicitly; applying it to netgen would move the shipped reference mesh
for no gain.

## Design

A scratch prototype run on 29 September 2026: Gmsh 4.15.2 and netgen 6.2.2606 on Linux (WSL2),
`uv sync --all-extras`. It is not the implementation. The region is the fixture through
`derive_region` at the default membrane and reservoir, and the target is 0.05 nm unless stated.

### 1. The handoff

The glued shape has 193 vertices and 195 unique edges. The faces list 158 edges (`electrolyte`),
39 (`membrane`) and 186 (`protein`). An edge is straight when its parameter midpoint lies on its
chord to 1e-9. Otherwise it must lie on `r² + z² = R²`. The only curved edges are the reservoir
arcs: `cis`, `trans`, and the two `membrane_outer` arcs either side of OCC's seam at `(R, 0)`.
Each spans less than π, which `geo.addCircleArc` requires. Loops are chained by shared vertex,
and a loop with a negative shoelace area is reversed.

Areas, checked on both backends and at `size_scale` 1 and 20. A chord across an arc of angle θ
removes `R²(θ − sin θ)/2`. Adding those segments back per domain (`cis` and `trans` to
`electrolyte`, `membrane_outer` to `membrane`) recovers the record's `face_areas_nm2`:

| Backend, region | electrolyte | membrane | protein |
|---|---|---|---|
| Gmsh, fixture, `size_scale` 1 | −6.9e-15 | +9.8e-13 | −7.8e-16 |
| Gmsh, parallelogram, `size_scale` 20 | −2.0e-15 | +3.2e-14 | −7.8e-16 |
| netgen, fixture, `size_scale` 1 | −1.4e-14 | +2.0e-12 | −7.8e-16 |

Uncorrected, the fixture's electrolyte is −2.09e-5 short and the parallelogram's −4.3e-3. So
the correction is what makes the oracle exact, and the 1e-10 tolerance sits 50 times above the
worst measured value.

### 2. The size field

Minimum SICN and gamma on the fixture at Algorithm 6 and Smoothing 5, with the worst element by
gamma:

Each row adds to the one above it, apart from the three alternatives at the foot:

| Field | `size_scale` 1 | 2 | 4 | 8 |
|---|---|---|---|---|
| Table only: sources and `Constant` domains | 0.4768, 0.3143, membrane (4.57, −0.47) | — | — | — |
| + domain-boundary sources (D3) | 0.6887, 0.5841 | 0.3848, **0.2084**, protein (4.62, 0.26) | 0.2153, **0.2348**, membrane (246.3, 0.93) | — |
| + membrane `Constant` at t, ungraded | 0.6887, 0.5841 | 0.3848, 0.2084 | 0.3709, 0.3164 | — |
| + short curves at < h, exact (D4 i) | 0.6887, 0.5840 | 0.6448, 0.5241 | 0.5532, 0.4038 | 0.2972, **0.1287**, electrolyte (122.2, −1.93) |
| + the membrane's boundary graded (D4 ii): **the choice** | **0.6887, 0.5840** | **0.6448, 0.5241** | **0.6753, 0.5655** | **0.6275, 0.5072** |
| Alternative: short curves at < h/2, binned to √2, ungraded cap | 0.6887, 0.5841 | 0.5963, 0.4593 | 0.4853, 0.3300 | — |
| Alternative: short curves at < h, binned to √2, ungraded cap | 0.5963, 0.4593 | 0.6088, 0.4784 | 0.5525, 0.4033 | — |
| Alternative: `ExtendFromBoundary` 1 and the ungraded cap, no D4 (i) | 0.6890, 0.5845 at 95,103 triangles | 0.6594, 0.5503 | 0.3709, 0.3876 | — |

The `size_scale` 2 failure is at the profile vertex (4.64, 0.36). An edge of 0.0412 nm sits there
beside a 0.1 nm target, and the fixture's shortest edge is 0.0361 nm. The `size_scale` 4 failure is
at the membrane strip's outer end. There, 1.4 nm `membrane_outer` arcs meet `membrane` edges sized
at 4 × 2.8 = 11.2 nm across a strip 2.8 nm thick. At `size_scale` 8, an ungraded cap leaves a jump
from 2.8 nm on the membrane's surface to 22.4 nm in the electrolyte beside it. The netgen route
passes all three. Its restriction by edge length and by the proximity of close edges is built in
and unconfigured. D4 states the same restrictions as fields, and grades each one as D3 grades a
domain. The choice has the best minimum over the whole range.

With every D3–D4 field, the fixture meshes as follows:

| Wall target (nm) | Triangles | Min SICN, gamma | Wall segments | Mean, p95, max ratio | Mesh (s) |
|---|---|---|---|---|---|
| 0.05 | 48,929 | 0.6887, 0.5840 | 654 | 0.909, 1.007, 1.029 | 3.2–3.7 |
| 0.03505 (3 M) | 55,103 | 0.7088, 0.6116 | 911 | 0.931, 1.021, 1.051 | 4.0 |
| 0.02715 (5 M) | 61,222 | 0.7137, 0.6202 | 1,159 | 0.945, 1.022, 1.055 | 4.3 |
| 0.1 (`size_scale` 2) | 18,518 | 0.6448, 0.5241 | 396 | 0.751, 1.004, 1.023 | 1.9 |
| 0.2 (`size_scale` 4) | 11,758 | 0.6753, 0.5655 | 314 | 0.474, 0.873, 1.025 | 1.6 |
| 0.4 (`size_scale` 8) | 10,673 | 0.6275, 0.5072 | 310 | 0.240, 0.468, 0.687 | 1.7 |

D9's bounds, 1.15 on the mean and 2.0 on the maximum, hold with room to spare. A Gmsh wall is at
or under its target, where netgen's runs 1.045–1.078 over it. At coarse scales the short-curve
sources refine the wall below its target. Netgen's fixture at 0.05 nm: 44,316 triangles, 0.6559,
0.6157, 569 wall segments, 6.4–7.0 s. The parallelogram of `test_mesh_generate.py` at `size_scale`
20 gives 492 triangles, 0.7799 and 0.7152, in 0.08 s.

### 3. Mesher settings

Fixture at 0.05 nm, the table-only field (before D3), which exposes the algorithms' differences
most plainly:

| Algorithm, smoothing | Triangles | Min SICN, gamma | Mean SICN, gamma | Mesh (s) |
|---|---|---|---|---|
| 6, 1 | 48,313 | 0.4636, 0.3143 | 0.9866, 0.9843 | 1.3 |
| 6, 5 | 48,313 | 0.4768, 0.3143 | 0.9878, 0.9857 | 2.7 |
| 5, 1 | 53,359 | 0.4694, 0.3130 | 0.9497, 0.9409 | 1.2 |
| 5, 5 | 53,359 | 0.4845, 0.3296 | 0.9563, 0.9487 | 2.8 |
| 1, 1 | 50,415 | 0.4311, 0.3032 | 0.9559, 0.9490 | 4.1 |

`optimize("Relocate2D")` after generation moved the minimum by less than 0.01, so it is not used.
With every D3–D4 field, two fresh processes gave one content hash (`69e54763…`) and wrote nothing
to standard output.

### 4. The same region, measured by a solve

The frozen case is WP22 D9: uncharged `pnp`, flow off, every correction `none`, 1 M NaCl,
+50 mV, ground *cis*, stabilisation `none`. It was solved on the fixture meshed by netgen (through
`inputs.profile`) and by the prototype (through `inputs.mesh`):

| `size_scale` | netgen G (S), triangles | Gmsh G (S), triangles | G_gmsh/G_netgen − 1 |
|---|---|---|---|
| 2 | 1.475574e-8, 14,511 | 1.475390e-8, 18,518 | −1.25e-4 |
| 1 | 1.475279e-8, 44,316 | 1.475244e-8, 48,929 | −2.4e-5 |

Netgen at `size_scale` 2 reproduces WP22's 1.4756e-8 S. From `size_scale` 2 to 1, netgen's G falls
by 2.0e-4 and Gmsh's by 9.9e-5. The two backends agree at each size to within that discretisation
change, and both approach 1.4752e-8 S. The ungraded cap gave 18,144 triangles at `size_scale` 2
and the same G to seven figures: the extra elements are in the membrane, where an uncharged case
solves only Laplace's equation. Each solve took 9–10 s at `size_scale` 2 and 30–34 s at 1.

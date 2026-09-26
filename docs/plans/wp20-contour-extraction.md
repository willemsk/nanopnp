# WP20 — Contour extraction, conditioning and its gate (stage 4)

**Status: planned, not started.** Written 26 September 2026, after WP19 was delivered on
`claude/wp-plan-19-19570b` (its PR becomes `v0.9.0-alpha.3`). This package inherits stage 3's
`ReducedMap`: the (r, z) mean on bins `r_j = j·h` with exact annular weights and no interpolated
bin (WP19 D8), and `grids()`, which returns it as a `RadialGrid` indexed `[z, r]`. It inherits
stage 1's aligned ensemble in the structure's frame (WP18 D8), the CHARMM radius set (WP19 D3),
`refuse_walk`, which it moves on to stage 5, and the `nanopnp/profile/v1` schema of
`mesh/profile.py`, which it emits. The author's contour script is read, as B6 requires; what ports
is D2.

This is a work package of the [Phase 2 plan](phase-2-geometry-pipeline.md). `SPECIFICATION.md`
governs: where this file and the specification disagree, the specification is right and this file
is wrong. Requirement identifiers here are pointers into it, never restatements of it. This plan's
commit amends the specification in the places listed under [Pointers](#pointers).

## Execution brief

### Scope

The package delivers pipeline stage 4, `contour`:

- **Extraction (FR-07):** the isolevel contour of the reduced mean, assembled into the region above
  the isolevel, with sub-resolution features removed and enclosed voids filled.
- **Conditioning (FR-07):** Taubin smoothing, Douglas–Peucker simplification and a minimum vertex
  spacing, emitting `nanopnp/profile/v1` with `source: pipeline`.
- **The gate (FR-08):** validity, simplicity, topology, spacing, local feature size, and the
  lumen radius against a probe-radius profile computed on the aligned structure (§8.2.2 B5).
- **Walk:** a `structure:` case now walks to stage 4. A walk past it is refused naming stage 5
  (WP21).

It adds VER-51 and closes OPN-02. RSK-06 is retired.

**This brief runs to about 2,700 words, over its 1,200-word target.** Three things in it are new:
the morphological step, the contour's own size target and the radius band. Each moves a number or
a verdict, and WP21 and WP22 inherit all three. The prototype showed that the first two cannot be
chosen apart from each other: the specified pipeline fails its own gate on the reference ensemble
unless they are fixed together.

### Pointers

- **Normative:** FR-07, FR-08, QR-12, FR-27; §5.2 row 4; §5.2.1 and its NOTEs; §5.3.2; the
  §5.3.1 NOTEs on `inputs:` and `structure:`; §8.2.2 B5–B6; OPN-02; RSK-05, RSK-06; WP17 D3 (no
  tuning parameter or gate threshold is a case key).
- **Amended in this commit:**
  1. §5.2.1: the pipeline paragraph and the gate table are made exact (D4–D11). Two NOTEs are
     added: the contour's size target, and the radius band.
  2. §5.2 row 4: inputs and gate.
  3. §5.3.1: a NOTE on `geometry.contour` (D3, D9, D12). The `structure:` NOTE's walk sentence now
     names stage 5.
  4. §5.3.2 row 4: the stage-4 artefact.
  5. §10 OPN-02 is closed and §9 RSK-06 retired, with the finding of [Design §1](#1-the-authors-script-read).
- **Knowledge:** `.knowledge/04` §1.2 (new) records the script and its erratum; `.knowledge/07`
  §7 and the index's *Still open* item 3 are updated.
- **Code:** `symmetry/reduce.py` (`ReducedMap.grids`); `density/radii.py` (`resolve_radii`,
  `KERNEL_RADII`); `structure/ensemble.py` (`AlignedEnsemble.read`); `mesh/profile.py`
  (`PoreProfile`, `min_feature_size`, `min_vertex_spacing`, `signed_area`, `load_profile`);
  `mesh/reference.py` (`plane_crossings`); `core/stages.py` (`register`, `_register_builtins`,
  `extra=`); `io/artefact.py` (`MESH_ARTEFACT_SCHEMA`, the repeated-string precedent);
  `io/run.py` (`PIPELINE`, `STRUCTURE_STAGES`, `WORKSPACE_STAGES`, `_WEIGHTS`); `io/case.py`
  (`ContourSpec`, `STRUCTURE_WALK`, `refuse_walk`, `_UNCONSUMED_INPUTS`); `io/defaults.py`
  (`CONFIGURATION_PATHS`); `io/manifest.py` (`_geometry_group`); `cli/errors.py`.

### Decisions

| # | Decision | Choice | Why / source |
|---|---|---|---|
| D1 | Stage and walk | Stage 4 is `contour`: number 4, inputs `("case", "structure", "symmetry")`, schema `nanopnp/profile/v1`, target `nanopnp.geometry.contour:ContourStage`, `extra="structure"`. `PIPELINE` inserts it after `symmetry`. `STRUCTURE_STAGES` and `STRUCTURE_WALK` gain it, and `refuse_walk` names stage 5, CAD assembly (WP21). It is a workspace stage | scikit-image and Shapely are in the `structure` extra, imported at the top of `geometry/contour.py`, reached only through `create()` (the phase plan's import decision). Stage 1's ensemble feeds the probe profile (D11) |
| D2 | What ports from the author's script | **Ported:** `find_contours` at the isolevel on the (r, z) mean, and Shapely `simplify` with `preserve_topology=True`. **Not ported:** taking `contours[0]` (scan order, not geometry); the index-to-radius map (an erratum, [Design §1](#1-the-authors-script-read)); the 0.1 nm tolerance (the case default stays 0.02); writing at `%.2f` (moves vertices 0.005 nm and can merge them); the z offset (stage 5 applies `centre_z_nm`) | B6, RSK-06. The script is `pqr2grid`, 2019, and has no smoothing, spacing or gate |
| D3 | Case values | No new key (WP17 D3). In `resolve()`: `isolevel` must be finite and in (0, 1). `simplify_tol_nm` must be finite and in (0, h), with h the density grid spacing. Each is refused naming its value, and the second names h too. Neither is narrowed in the schema | WP18 D4's rule. Every isolevel in (0, 1) is a level of a map in [0, 1]. A tolerance of h or more discards resolved geometry and breaks D5's margin ([Design §2](#2-sub-resolution-features)) |
| D4 | Extraction | `skimage.measure.find_contours(mean, isolevel, fully_connected="high", positive_orientation="high")` on `grids()["mean"]` (`[z, r]`). A point `(row, col)` maps to `(r₀ + col·Δr, z₀ + row·Δz)` from the grid's own axes. Closed contours are assembled into the region above the isolevel: outer loops, minus the holes they enclose, told apart by winding. An open contour is refused. At the axis edge the message names the z range where the lumen is closed at this isolevel; at another edge it names the edge | `"high"` joins the protein diagonally, which is the choice D5's closing makes anyway. `r_j = j·h` is the bin centre (WP19 D8), which is exactly where the script erred |
| D5 | Sub-resolution features | The region is **closed, then opened, by a disc of radius δ = 2h**, with h the density grid spacing: Shapely `buffer(δ).buffer(−δ)`, then `buffer(−δ).buffer(δ)`, round joins, `quad_segs = 8`. Gaps and fins narrower than 4h (0.2 nm) go. Every hole that remains is filled, and the count and area are recorded. Exactly one component must remain; otherwise the run is refused naming each other component's centroid and area. The lumen radius's change from the raw contour (maximum, rms, and at the constriction) is recorded | [Design §2](#2-sub-resolution-features). A groove at (3.2, −0.1) nm fails the feature-size gate on the ClyA-AS ensemble at δ = h (0.058 nm against 0.1 nm). δ > h + `simplify_tol_nm` is the margin the gate needs. 0.2 nm is below one water molecule's diameter and one heavy atom's. This automates the author's "manual removal of overlapping vertices". §5.2.1 amended |
| D6 | Smoothing | `taubin`: resample the loop at uniform arc length h/2, then N = 10 passes of λ = 0.5, μ = −0.53 with the uniform umbrella operator. `none` skips both steps. The constants are code, cited here, and keyed | [Design §3](#3-the-taubin-constants): the pass band is wavelengths above 0.33 nm, the grid-scale staircase is attenuated 15-fold, and a regular 64-gon gains 0.28 % in area where a Laplacian of the same length loses 4.7 % |
| D7 | Simplification | Shapely `simplify(simplify_tol_nm, preserve_topology=True)` | §5.2.1; D2 |
| D8 | Minimum spacing | While the shortest edge is below `h_c`, drop the endpoint of that edge whose removal changes the area least, taking the lower index on a tie | §5.2.1's "minimum vertex spacing" step, made deterministic |
| D9 | Canonical form | Clockwise, starting at the lowest-z vertex and then the smallest r, like the reference fixture. Full float64 precision. Coordinates stay in the **stage-1 frame**; stage 5 applies `geometry.membrane.centre_z_nm` (WP21) | A deterministic payload. The phase plan's model-frame decision |
| D10 | Gate | Every threshold is a constant, keyed, never a case key. The loop is valid and simple (`LinearRing`, and the `PoreProfile` validators); one component, no open contour, and clear of the axis by `h_c`; minimum edge ≥ `h_c`; `min_feature_size` (two edges either side) > 2 `h_c`; the radius band of D11. **`h_c` is the density grid spacing h**, 0.05 nm by default. The gate fires after conditioning and never adjusts the loop | [Design §4](#4-the-contours-size-target): "target element size" read as the stage-6 wall size would make the geometry depend on the concentration, at 0.27 nm spacing at 0.05 M. §5.2.1 amended |
| D11 | Radius profile (B5) | `R_p(z) = min_i(√(x_i² + y_i² + (z − z_i)²) − R_i)` per frame, the mean over frames, with each `R_i` from the kernel's radius set. The lumen radius `r_c(z)` is the loop's smallest crossing of the plane `z`, on the mid-planes between z nodes where the plane crosses the loop. Gate: `−h_c ≤ r_c − R_p ≤ 1.5 nm` everywhere | [Design §5](#5-the-radius-band). The lower bound is geometric: inside the axis-centred sphere every atom is at least its radius away. The upper bound is a gross-error check, and the measured maxima are 0.91 nm (2WCD) and 0.87 nm (ClyA-AS). The whole profile goes in the summary |
| D12 | Artefact | `ProfileArtefact`, schema string repeated in `io/artefact.py` as `MESH_ARTEFACT_SCHEMA` is. The payload is `profile.yaml`, written by a new `write_profile` in `mesh/profile.py` that `load_profile` reads back. It has `name: contour-<first 12 hex of the key>`, `provenance.source: pipeline`, the citation "nanopnp stage 4, SPECIFICATION.md §5.2.1", and `sha256` set to the stage-3 payload digest. The summary holds the conditioning record (area and vertex count after each step, holes filled, the constriction radius and its z) and the gate record (each measured value, its threshold, its location, and the probe profile) | FR-27: the payload *is* an `inputs.profile` document. `PoreProfile` stays unchanged, so a hand-edited profile carries no stale record |
| D13 | Key | `content_hash("nanopnp/profile/v1", {geometry.contour, h, closing: "disc-2h", taubin: {λ, μ, N, resample: "h/2"}, spacing: "h", connectivity: "high", band: {low: "−h", high_nm: 1.5}, radius set name + sha256}, inputs=(stage-1 key, stage-3 key))` | A code constant that moves a number or a verdict is in the key (WP19 D11) |
| D14 | Errors | `ContourGateError(ValueError)` names the criterion, the measured value, the threshold and the (r, z), and maps to `EXIT_GATE` | QR-12; WP19 D12 |
| D15 | Manifest | `geometry_and_mesh` gains `contour`: isolevel, smoothing, tolerance, `h_c`, vertex count, spacing, feature size, holes filled, and the band's worst margins with their z | FR-25; WP19 D13 |
| D16 | `inputs.profile` | Unchanged: refused until stage 5 reads it (WP21) | Its consumer is stage 5. The phase plan |
| D17 | Public API | No new name | IF-01 NOTE |

**Handed to WP21:** the profile is in the stage-1 frame. Stage 4 guarantees spacing ≥ h and
feature size > 2h, so a pore-wall element size of h or less satisfies §5.2.1 literally. Where the
resolved wall size (λ_D/5 × `size_scale`) exceeds h, WP21 decides, and VER-10 is the backstop.

### Work items

1. **`geometry/probe.py`** (D11). The probe-radius profile, numpy deferred, cancellable per
   frame. Write the analytic-ring test first. Read [Design §5](#5-the-radius-band).
2. **`geometry/contour.py`** (D4–D10, D14). Region assembly, morphology, resampling, Taubin,
   simplification, spacing and the gate, as pure functions over arrays, then `ContourStage`. Write
   the closed-form tests first. Read [Design §2](#2-sub-resolution-features) and
   [§3](#3-the-taubin-constants).
3. **`mesh/profile.py`** (D12). `write_profile` and a `PIPELINE_SOURCE = "pipeline"` constant,
   outside `REFERENCE_SOURCES`.
4. **Registry, walk, case and errors** (D1, D3, D13, D14). `core/stages.py`, `io/artefact.py`,
   `io/run.py`, `io/case.py`, `cli/errors.py`. Update the reason for `geometry.contour.smoothing`
   in `io/defaults.py`. The `ContourSpec` field descriptions state the NOTE, so VER-45 carries it.
5. **Manifest** (D15), in `io/manifest.py`.
6. **Tests**, per [Verification](#verification). The Tier-2 contour test re-runs stages 1–3 on
   2WCD, about 25 s, because `--dist loadfile` may place it on a different worker from WP19's. The
   Tier-3 test reuses the VER-50 test's stages 1–3 through a module-scoped store, not a shared
   fixture, so a contour-gate failure cannot fail VER-50.
7. **Specification, changelog and knowledge.** Add VER-51 to §7.2 with the text below. Map it in
   Appendix A: FR-07 → VER-51, VAL-05; FR-08 → VER-51. Recount the coverage line. Write
   `CHANGELOG.md` `[0.9.0-alpha.4]`. Add Outcomes here and update `current.md`.

### Verification

**VER-51** (for §7.2): *Contour extraction, conditioning and its gate.*

- A square-pyramid field, linear along every grid edge, is contoured exactly, to round-off. A
  Gaussian torus section is contoured to within the interpolation bound.
- Taubin keeps the area of a regular 64-gon to its closed form, where a Laplacian of the same
  length shrinks it by 4.7 %. The test discriminates.
- Closing and opening by 2h fills a 0.1 nm slot, removes a 0.1 nm fin and keeps a 0.3 nm slot. A
  hole is filled and recorded.
- Each gate criterion fires on constructed input, naming the criterion, the value, the threshold
  and the location.
- The probe profile of an analytic ring of atoms matches its closed form.
- The artefact round-trips through `load_profile`, its key is stable across processes, and a hand
  edit is recorded.
- The case refusals and the walk behave as D1 and D3 state.

| Test | Tier | Identifiers | Oracle | Tolerance and source |
|---|---|---|---|---|
| `tests/tier1/test_contour.py::test_ver51_pyramid_contour_is_exact` | 1 | VER-51, FR-07 | `f = 1 − max(|r − r₀|, |z − z₀|)/a` centred on the node (3, 5), with `a(1 − l) = (k + ½)h`. The kinks lie on the diagonals, which cross no edge between nodes, so `f` is linear along every edge. The level set is a square whose corners sit at cell centres | Every vertex on the square to 1e-12, and the area `(2a(1 − l))² − h²/2` to 1e-12 (measured 6e-15 and 4e-15). A transposed axis, a half-bin shift or the script's `w/h` scale fails by ≥ h/2 |
| `…::test_ver51_gaussian_section_subpixel` | 1 | VER-51, FR-07 | `exp(−((r − 3)² + (z − 5)²)/s²)`, s = 1 nm, h = 0.05, l = 0.25: a circle of radius `s√ln 4` | Distance to the circle ≤ 1e-3 nm. The linear-interpolation bound `h²|f″|/(8|f′|)` on a grid line through the centre is 4.7e-4 nm, and the worst vertex measured 4.67e-4 |
| `…::test_ver51_taubin_keeps_area_laplace_shrinks` | 1 | VER-51 | A regular 64-gon, an eigenvector of the umbrella operator: area ratio `f(k₁)^{2N}`, with `k₁ = 1 − cos(2π/64)` | Both closed forms to 1e-12: Taubin 1.002770, Laplacian 0.952933 |
| `…::test_ver51_closing_fills_subresolution_slot` | 1 | VER-51, FR-07 | A 1 × 2 nm body with slots 0.1 and 0.3 nm wide and 0.5 nm deep, and a fin 0.1 nm thick; h = 0.05, δ = 0.1 | The narrow slot is filled, the fin removed and the wide slot kept. The area change is within the corner-rounding bound `δ²(1 − π/4)` per corner, and the feature size exceeds 2h after |
| `…::test_ver51_topology` | 1 | VER-51, FR-08, QR-12 | A void inside the body; a second body; a lumen closed on the axis over a known z range | Void filled, recorded with its area. The island is refused naming its centroid and area. The closed lumen is refused naming the z range |
| `…::test_ver51_gate_criteria_fire` | 1 | VER-51, FR-08, QR-12 | One constructed loop per criterion: a short edge, a narrow slot past the morphology, a loop touching the axis, a lumen inside the probe sphere by 0.1 nm, and one wider than it by 2 nm | `ContourGateError` names the criterion, value, threshold and (r, z) |
| `…::test_ver51_probe_ring_closed_form` | 1 | VER-51 | N = 12 atoms of radius R_a at (ρ₀, z₀), plus a second frame shifted in z | `√(ρ₀² + (z − z₀)²) − R_a` to 1e-12, and the frame mean |
| `…::test_ver51_artefact_and_key` | 1 | VER-51, FR-27, VER-23 | `write_profile`/`load_profile` round trip; the key in two processes; a hand edit of `profile.yaml`; the key moves with each D13 entry | Exact |
| `…::test_ver51_case_values_and_walk` | 1 | VER-51, IF-02 | `isolevel` of 0, 1 and NaN; `simplify_tol_nm` of 0 and of h; `upto="contour"`; a full walk; a sweep | Refused naming the value, or stage 5 |
| `test_stages.py`, `test_cli.py`, `test_manifest.py`, `test_case_schema*.py` (existing) | 1 | VER-25, VER-32, VER-24, VER-45 | The registry lists `contour` without importing skimage or Shapely; a missing extra is named at `create()`; the error is classified; the reason updated | — |
| `tests/tier2/test_contour_2wcd.py::test_ver51_2wcd_contour` | 2 | VER-51, FR-07, FR-08 | `prepared_2wcd` to `upto="contour"`: the gate passes, and the payload loads through `load_profile` | Gate verdict. Vertex count, spacing, feature size, holes, band margins and constriction are logged ([Design §6](#6-measured-on-the-prototype)) |
| `tests/tier3/test_density_ensemble.py::test_ver51_clya_as_contour` | 3 | VER-51 | `upto="contour"` on the module-scoped store, so stages 1–3 come from the VER-50 run's cache. Skips without the archive | Recorded, with the gate's verdict. The prototype passed at feature size 0.229 nm and band [+0.173, +0.869] nm |

```bash
uv run pytest tests/tier1/test_contour.py -v
uv run pytest tests/tier2/test_contour_2wcd.py -v --log-cli-level=INFO
uv run pytest -m tier3 tests/tier3/test_density_ensemble.py -v --log-cli-level=INFO
.claude/hooks/gate.sh run
```

### Out of scope

- **The comparison against the reference polygon, VAL-05, and the isolevel sensitivity (G2)** go
  to WP22, which inherits [Design §7](#7-against-the-reference-polygon-recorded-for-wp22).
- **CAD assembly and meshing from the profile**, the reading of `inputs.profile`, and the
  `centre_z_nm` shift go to WP21.
- **The optional periodic B-spline fit** of §5.2.1 stays optional and is not implemented.
- **HOLE through `mdahole2`** is an optional cross-check (B5), not built here.
- **The contour viewer and the hand edit** go to WP24. **The guide** goes to WP25.

### Open questions

None blocks this package. Two go to the author, for WP22:

1. **Was the reference polygon made with `pqr2grid`'s radial binning?** If it was, its radii are
   compressed by `h/w` and shifted by `h/2`, and WP22 needs the grid extent that was used. The
   measurement in [Design §7](#7-against-the-reference-polygon-recorded-for-wp22) argues against
   it: the reference lumen is *wider* than the correct contour, where the erratum would make it
   narrower.
2. **What did the hand edit do?** 42 % of the reference vertices have neither coordinate on the
   0.05 nm lattice, which vertex removal alone cannot produce.

## Design

### 1. The author's script, read

The script is the author's `pqr2grid` repository, held locally at `~/repos/pqr2grid` (MIT, per
its `pyproject.toml`). The contour routine first appears in commit `a8e2898`, 7 October 2019,
"Working code in test.py", three months before the preprint. It is carried unchanged into the
2023 package as `Grid2D.create_polygon_contour` (commit `8a581e9`). The same lines serve the PlyAB
and MspA scripts. Nothing in the paper's archive, `will2018-data`, calls it for ClyA. It is 20
lines, and couples to nothing beyond MDAnalysis, scikit-image and Shapely, so RSK-06 is retired.

It runs five steps:

1. It deposits the union density (σ = 0.93, radii from the PQR) on a Cartesian grid over `[−L, L]`
   at spacing h.
2. It averages radially with `np.histogram`, at bin width `w = (x_max − x_min + 1)/N_x`.
3. It takes `find_contours(D, 0.25)` and keeps `contours[0]`.
4. It maps a point to `r = col·h`, `z = row·h + z_min`, then applies `Polygon.simplify(0.1)` and a
   z offset.
5. It writes the vertices with `%.2f`.

It has no smoothing, no spacing step and no gate. §5.2.1's Taubin, spacing and gate are new with
this package.

**The erratum [tested].** With `x ∈ [−L, L]`, `N_x = 2L/h + 1`, so `w/h = (2L + 1)/(2L + h)`, and
not 1: the `+ 1` is in nanometres, where one spacing was meant. Bin j covers `[jw, (j+1)w)`, so its
centre is at `(j + ½)w`, but column j is placed at `jh`. A feature at true radius r therefore
appears at `r_a = (r/w − ½)h`. At L = 15 nm, the PlyAB call, `w/h = 1.0316`: a 1.65 nm constriction
reads 1.574 nm (−0.076) and 5.66 nm reads 5.462 nm (−0.20). Applied to our own 2WCD map
(L = 6.75 nm, `w/h = 1.0701`, as the formula gives), the script's contour lies 0.13–0.24 nm inside
ours at the lumen and 0.21–0.40 nm inside at the outer surface. The same bins placed at their
centres agree with our exact reduction to ≤ 0.01 nm. The error is entirely in the index-to-radius
map, which is why D4 takes coordinates from the grid's own axes. Whether the ClyA reference was made
this way is open question 1.

`contours[0]` is whichever contour the scan meets first. On 2WCD the map carries two, the body and
a 0.0047 nm² void, so the choice is not geometric.

The same repository's 2023 charge map deposits `q/(π(σR)²)·exp(−((r − r_i)² + (z − z_i)²)/(σR)²)`,
a planar Gaussian with no `1/(2πr)`. Its planar integral is the net charge in e/m², consistent with
G5. That is a pointer for Phase 3's FR-13, not an input here.

### 2. Sub-resolution features

**One frame.** On PQR 02's coordinates (hydrogens included), the 0.25 contour conditioned as
§5.2.1 first wrote it (Taubin, then Douglas–Peucker at 0.02 nm) has a minimum feature size of
0.058 nm. Without Taubin it is 0.036 nm. Both are below 2h = 0.1 nm. The pinch is a groove in the
outer surface at r = 3.18–3.25 nm, z = −0.15 to +0.10 nm, 0.036–0.065 nm wide: one grid cell.

**The ensemble.** In the 50-frame mean the same groove is 0.10–0.12 nm wide at its mouth. Closing
by δ = h leaves it open, and Douglas–Peucker's chords then narrow it to 0.058 nm. So the gate
aborts on the reference input at δ = h.

At z = −0.1 the membrane's inner edge sits at r = 2.0 + 1.5 × 1.3/2.8 = 2.70 nm, so the groove lies
inside the membrane quadrilateral. The mesher would fill it with membrane slivers, which is RSK-05.

**The margin.** Closing by a disc of radius δ fills every gap narrower than 2δ, and opening removes
every fin thinner than 2δ. Simplification then moves each wall by up to `simplify_tol_nm`. The
gate's 2h therefore holds with margin only if `2δ − 2·tol > 2h`, that is `δ > h + tol`: 0.07 nm at
the defaults. δ = 2h = 0.1 nm meets it, and D3's `tol < h` keeps it met. A 0.2 nm gap cannot hold a
water molecule (0.28 nm) or an ion. A 0.2 nm fin is thinner than one heavy atom (at least 0.34 nm
across in the CHARMM set). Neither is anything the continuum or the structure resolves.

Minimum feature size after the whole pipeline, against the gate's 0.1 nm:

| δ | 2WCD | One MD frame | ClyA-AS, 50 frames |
|---|---|---|---|
| h | 0.113 | 0.219 | **0.058** |
| 1.5h | 0.155 | 0.219 | 0.167 |
| 2h | 0.173 | 0.137 | 0.229 |

**What δ = 2h costs.** After the morphology, the area moves by +0.009, +0.045 and +0.047 nm²
(2WCD, one frame, ensemble; at most +0.16 % of about 29.6 nm²). The lumen radius moves from the raw
contour's by at most 0.040, 0.035 and 0.101 nm, with an rms of at most 0.012 nm. The largest is on
the ensemble at z = 1.62 nm, where the opening removes a fin at the top of the constriction. The
constriction itself moves by +0.008 nm, mostly through the simplification's chords. That is 0.5 % in
radius, or about 1 % in `G ∝ r²`, which D5 records for WP22.

A 90° concave corner gains `δ²(1 − π/4) = 2.1e-3 nm²`, and a convex one loses the same. The
morphology acts on the region, not on the loop, so an island narrower than 4h vanishes by the same
rule, and the island refusal fires only on a resolved one. It runs before Taubin, so the smoothing
never turns a groove into a smooth, narrow slot. On 2WCD the closing also removes the raw map's
0.0047 nm² void at (4.98, 8.34) nm.

### 3. The Taubin constants

The umbrella operator on a closed loop, `Δx_i = ½(x_{i−1} + x_{i+1}) − x_i`, is circulant. The
Fourier mode `θ = 2πm/n` has eigenvalue `−k`, with `k = 1 − cos θ ∈ [0, 2]`. One Taubin pass, λ
then μ, multiplies that mode by `f(k) = (1 − λk)(1 − μk)` (Taubin, *SIGGRAPH* 1995). With λ = 0.5
and μ = −0.53:

| Quantity | Value |
|---|---|
| Pass-band edge `k_PB = 1/λ + 1/μ` | 0.1132 |
| Largest gain | 1.00085, at k = 0.0566 |
| `f(k)^10` at k = 0.5, 1, 1.5, 2 | 0.59, 0.069, 3.3e-4, 0 |

**Why resample.** Marching squares places vertices from 1e-4 to 0.07 nm apart, and the operator's
scale is in vertices, not nanometres. At a uniform arc length `s = h/2`, a mode's wavelength is
`Λ = 2πs/θ`. The pass band is then `Λ > 13.08 s = 0.33 nm`. The grid-scale staircase, `Λ ≈ 2h = 4s`,
has k = 1 and is cut to 0.069 of its amplitude after N = 10. The largest low-frequency gain,
`1.00085^10 = 1.0085`, falls at Λ = 0.47 nm, where a 0.05 nm corrugation grows by 4e-4 nm.

**Area.** A regular n-gon is an exact eigenvector, so its area scales by `f(k₁)^{2N}`, with
`k₁ = 1 − cos(2π/n)`. At n = 64 that is **1.002770** for Taubin. A Laplacian with the same 2N = 20
applications of λ = 0.5 gives `(1 − λk₁)^20 = `**0.952933**. Both are VER-51 oracles to 1e-12. On
the ClyA contours, resampled to 1,400–1,500 points, Taubin moved the area by +3e-4 and +4e-4 nm².

### 4. The contour's size target

§5.2.1 wrote "≥ target element size" and "> 2 × target element size". Read as the stage-6 wall
size, NUM-30's `h₁ = λ_D/5` is 0.035 nm at 3 M and 0.27 nm at 0.05 M. That reading fails twice:

- **Stage 4 would depend on the electrolyte.** A concentration sweep would re-extract the geometry
  at every member, and conductances across concentrations would compare different pores.
- **At 0.05 M the contour would need 0.27 nm spacing** and a 0.54 nm feature size. That erases the
  lumen's corrugation, which the thesis puts at about 0.25 nm in radius (a 6.0 nm mean diameter
  against the 5.5 nm largest sphere, `.knowledge/04` §1).

The contour's own resolution is the map's, h. So `h_c = h`: 0.05 nm by default, which is also the
reference model's pore-boundary element size (§5.2.2). A mesh whose wall size exceeds h is refined
locally by the short edges, which is not a failure, and WP21 decides how to treat it. The
delivered fixture's exemption, the §5.2.1 NOTE, is unchanged.

### 5. The radius band

**Lower bound.** Let `c = (0, 0, z)` and `R_p = min_i(|x_i − c| − R_i)`. Take a point p on the
plane z at radius `r < R_p`. It lies inside the probe sphere, so `|p − x_i| ≥ |x_i − c| − r ≥
R_i + (R_p − r)`. Each atom's Gaussian there is at most `exp(−(1 + (R_p − r)/R_i)²/σ²)`, which is
`exp(−1/σ²) = 0.315` at `r = R_p`. A lone atom's own 25 % level lies at `σR√ln 4 = 1.095R`,
0.022 nm outside its surface at the largest CHARMM radius, 0.2275 nm. A union of atoms can raise
that. The azimuthal mean, though, averages a ring that touches atoms only at points, which pulls
the contour outward. So the contour can enter the probe sphere by at most a fraction of an atom's
width, and −h is a bound with margin. The minima measured are +0.061 nm (2WCD, z = −1.40), +0.238
(the MD frame, z = 7.40) and +0.173 (the ensemble, z = −0.20).

**Upper bound.** The probe touches the most protruding atom, while the contour is the azimuthal
mean, so their difference is the lumen's corrugation. The maxima measured are 0.908 nm (2WCD,
z = 1.60), 0.886 (the MD frame, z = −2.00) and 0.869 (the ensemble, z = −1.90). 1.5 nm is a
gross-error bound. It catches an isolevel far too high, an inner crossing that falls on the outer
surface, and a profile drawn from another structure.

**What it does not catch.** The script's radial scale error, −0.076 nm at the constriction for
L = 15, sits inside the lower margin on 2WCD. VAL-05 is the check for that, not this gate.

The map is the mean of the per-frame maps (WP19 D4), so the probe profile is the mean of the
per-frame profiles. Marching-squares vertices lie on the z-lattice lines, so the band is sampled on
the mid-planes between them. The cost is frames × atoms × planes, 7.8e8 distances for the
ensemble, batched per frame: under 7 s on the prototype, loading included.

### 6. Measured on the prototype

A scratch prototype of D4–D11, not the implementation, run on 26 September 2026 at the defaults
(isolevel 0.25, Taubin, tolerance 0.02 nm, h = 0.05 nm, δ = 2h). There are three inputs:

- **2WCD** is the author's copy of chains A–L (`md_data/2wcd.pdb`, 1e-4 nm RMSD from the vendored
  chains). The Tier-2 test re-measures on the vendored, prepared file.
- **One MD frame** is `prod5_clya_as.pdb`, PQR 02's coordinates, hydrogens included.
- **The ensemble** is DCD frames 48–97. Stage 2 took 976 s.

| | 2WCD | One MD frame | ClyA-AS, 50 frames |
|---|---|---|---|
| Reduced grid (z × r) | 315 × 136 | 331 × 142 | 339 × 147 |
| Closed contours at 0.25 | the body and a 0.0047 nm² void | the body | the body |
| Vertices: marching squares → resampled → final | 956 → 1,510 → 157 | 870 → 1,389 → 124 | 866 → 1,386 → 114 |
| Area, raw → final (nm²) | 28.145 → 28.118 | 29.764 → 29.775 | 29.541 → 29.545 |
| Minimum spacing (gate ≥ 0.05 nm) | 0.0725 | 0.0725 | 0.0732 |
| Minimum feature size (gate > 0.1 nm) | 0.173 | 0.137 | 0.229 |
| `r_c − R_p` (gate [−0.05, 1.5] nm) | +0.061 … +0.908 | +0.238 … +0.886 | +0.173 … +0.869 |
| Constriction `r_c`, at z (nm) | 1.628 at −1.40 | 1.576 at −1.20 | 1.610 at −1.35 |
| Stage 4 without the probe | 10 ms | 7 ms | 7 ms |

The spacing step removed no vertex on any of the three, so D8 is a guarantee rather than a working
step on these inputs. Douglas–Peucker moves the area most, by −0.034 to −0.043 nm².

For VER-51's Gaussian test, the worst of `find_contours`'s vertices lies 4.67e-4 nm from the true
circle at s = 1 nm (8.4e-4 at s = 0.5 and 2.2e-4 at s = 2). The square pyramid is exact to 6e-15.

### 7. Against the reference polygon, recorded for WP22

Recorded here and not gated: VAL-05 is WP22's, and its tolerance is argued there. The final
contours above were compared with the delivered 185-vertex polygon on 280 mid-planes over its
z-range.

| | 2WCD | One MD frame | ClyA-AS, 50 frames |
|---|---|---|---|
| Lumen, `r_ref − r_ours`: mean, rms (nm) | +0.142, 0.163 | +0.097, 0.106 | +0.075, 0.089 |
| Outer surface, `r_ref − r_ours`: mean, rms (nm) | +0.026, 0.144 | −0.117, 0.180 | −0.125, 0.164 |
| Constriction, ours against the reference's 1.650 at z = −1.24 | 1.628 at −1.39 | 1.578 at −1.19 | 1.610 at −1.34 |
| Fit `r_ref = a·r_ours + b` | a = 0.958, b = +0.245 | a = 0.926, b = +0.277 | a = 0.929, b = +0.250 |

**The reference body is thinner than the ensemble's 25 % contour.** Its lumen is about 0.08 nm
wider and its outer surface about 0.12 nm narrower. The fit compresses towards r ≈ 3.5 nm, inside
the body. The script's erratum cannot produce that: it has `a = h/w < 1` with `b = −h/2 < 0`, and
so moves both surfaces inward. A higher effective isolevel, a different radius set, or the hand
edit would each thin the body. The constriction difference, 1.610 against 1.650 nm, is 5 % in
`G ∝ r²` if it held along the whole constriction. This is the size of discrepancy WP22's tolerance
argument must face, and it is why the two author questions above are addressed to WP22.

**The lattice fingerprint.** In the delivered table, 58 % of the vertices have at least one
coordinate on the 0.05 nm lattice, and 32 % have both. A subset of marching-squares vertices
written at `%.2f` would have at least one on every vertex (`.knowledge/04` §1.2).

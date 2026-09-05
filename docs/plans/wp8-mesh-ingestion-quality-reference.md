# WP8 — Mesh ingestion, tagging, quality gates, and the reference geometry

**Status: delivered, 5 September 2026.** Written 4 September 2026, the second package of Phase 1,
after WP7 landed the case schema, the content-addressed artefact and the provenance manifest. It
inherits a solver that reads exactly one mesh format — netgen's own `.vol` — through fourteen lines
inside `solve/stage.py`, with no tagging, no vocabulary check and no quality gate anywhere between
the file on disk and the assembled weak form. `mesh/` is `primitives.py` (Phase-0 benchmark shapes)
and `distance.py` (PHY-02); `mesh/adapter.py`, `mesh/ingest.py`, `mesh/quality.py` and
`mesh/reference.py` do not exist. The ClyA vertex table, absent when this plan was first written,
landed while it was being written and is in the tree as
`data/geometry/clya_as_radial_geometry.csv`; until then `data/` held one file, and it was a
correction table.

This is the implementation plan for WP8 of `docs/plans/phase-1-solver-core.md`. `SPECIFICATION.md`
remains normative: where this file and the specification disagree, the specification governs and this
file is wrong. Requirement identifiers here are pointers into it, never restatements of it.

## Context

Phase 1's premise is that the solver runs on a mesh it did not build (§8.1). WP7 made that
expressible — `inputs.mesh: {path, format, groups}` validates today — but nothing reads it. The
`format` field is ignored, the `groups` map is ignored (`SuppliedArtefact.groups` is referenced
nowhere outside `io/case.py`), and `SolveStage._mesh_path` rejects anything that is not `.vol`
(`src/nanopnp/solve/stage.py:61`). So the case file promises MSH 4.1 ingestion with an explicit
group mapping, `io/defaults.py:132` writes `format: msh41` into the validated-default document, and
the only code that loads a mesh accepts neither. WP8 closes that gap and is the package that decides
what an externally supplied mesh has to prove before a form is assembled against it.

Four facts about the tree shape the design; all four were established by reading or running code.

- **Boundary conditions select by name, and an unclaimed name is silent.** `DEFAULT_BOUNDARIES`
  (`src/nanopnp/physics/models.py:218`) selects Dirichlet φ and `c_bulk` on `cis|trans`, no-slip on
  `wall|membrane` and `u_r = 0` on `axis`. Under the `r`-weighted forms the natural condition is the
  *free* one (NUM-06), so a mesh whose pore wall is called `Wall`, or `pore_surface`, or nothing at
  all, assembles cleanly, converges, and reports a current that is wrong by whatever leaks through a
  no-flux boundary that was never imposed. There is no residual, no gate and no diagnostic for it.
  This is the single failure the package exists to make impossible.
- **The distance field already refuses an empty source set, and nothing else does.**
  `wall_distance` raises when `mesh.Boundaries(sources).Mask().NumSet() == 0`
  (`src/nanopnp/mesh/distance.py:103`), naming the boundaries the mesh does have. It is the only
  name-existence check in the package, it fires on one name out of five, and it fires after the
  materials stage has already run. The ingestion gate generalises it and moves it to the front.
- **netgen cannot read MSH 4.1. [tested]** `netgen.read_gmsh.ReadGmsh` is an MSH **2.2** parser: it
  scans for `$Elements`, reads a bare element count, and splits fixed-width element lines. Handed a
  4.1 file it dies in `int()` on the entity-block header — `ValueError: invalid literal for int()
  with base 10: '5 30 1 30'` — and handed a 2.2 file it succeeds and recovers both boundary and
  material names. IF-06 names 4.1 as the archival format, so the ingestion route cannot be netgen's
  reader; it is meshio in, arrays through, `netgen.meshing.Mesh` built by hand.
- **The Phase-0 meshes already meet the reference quality figures. [tested]** Measured over the
  geometries Tier 1 and Tier 2 use today (table in §Design), minimum SICN runs 0.647–0.786 and mean
  SICN 0.938–0.975, against the reference model's 0.6378 minimum and 0.9765 mean. Nothing in the
  tree is anywhere near the 0.3 gate, so the gate can be unconditional rather than opt-in, and
  turning it on cannot break Tier 2.

- **The reference vertex table is in the tree, and it settles the membrane junction. [tested]**
  185 `r,z` pairs in nm, a simple closed loop with no duplicate vertex, `r ∈ [1.65, 5.66]`,
  `z ∈ [−1.85, 12.25]` — the published extents to the digit. It refutes what this plan first assumed
  about that junction: the pore's outer surface passes through `r = 2.7524` at `z = −1.4` and
  `r = 4.88` at `z = +1.4`, *not* through the membrane quadrilateral's drawn corners at 2.0 and 3.5,
  which lie inside the pore body. The membrane is a boolean subtraction, not a glue against matching
  coordinates, and the conformality gate changes with it (§Design).

The package delivers `mesh/adapter.py`, `mesh/ingest.py`, `mesh/quality.py`, `mesh/reference.py`,
the ClyA profile fixture and its loader, a stage-6 registration, changes to `solve/stage.py` and
`io/manifest.py`, and seven amendments to `SPECIFICATION.md` — two of which take OPN-05 down to a
single outstanding number, and one of which gives the pore's dielectric body a name. It discharges **IF-06, VER-10, QR-12**, re-verifies **VER-06** and **NUM-31** on
an ingested mesh, adds **VER-27** and **VER-28**, and carries **CON-10** for the first time. No new
dependency: `meshio` 5.3.5 is already a core dependency and `gmsh` is already the optional extra.

## Decisions taken before implementation

| Decision | Choice | Why |
|---|---|---|
| Direction of `inputs.mesh.groups` | **`{group name in the file: vocabulary name}`** — the key is what the mesh says, the value is what the solver speaks. Many-to-one is allowed and expected | A CAD export splits one physical wall into several curves, so several file groups map to `wall`; the reverse direction cannot express that without a list. Keying on the file's names also makes "every group must be claimed" a statement about the keys, which is the gate's whole content. §5.3.1's example currently reads the other way and names `pore`/`reservoir`/`bulk`, none of which the solver speaks — amendment B fixes both |
| Which names are *required* | Derived from the **resolved case**, never a constant list: the names `CoupledBoundaries.potential`, `.concentration`, `.velocity`, `.velocity_axis` and `numerics.wall_distance.sources` select on, plus the fluid material regex `ELECTROLYTE_DOMAINS` | A constant list is wrong in both directions — it demands `cis`/`trans` of a Debye–Hückel cylinder that has neither, and it says nothing when a case moves the distance sources to `wall\|membrane` and the mesh has no `membrane`. Deriving it makes the abort message exactly true: *this run will select on this name and no group supplies it* |
| What an unmapped group does | **Aborts**, in one diagnostic listing every unclaimed file group *and* every required vocabulary name no group supplies, with the mesh's own group names quoted back | QR-12 wants the gate, the quantity and its location. Both halves matter and neither implies the other: a typo in the map leaves a group unclaimed *and* a name unsupplied, but a mesh with an extra decorative group leaves only the first, and a case widening `wall_distance.sources` leaves only the second |
| Vocabulary | Materials `electrolyte`, `cis`, `trans`, **`protein`**, `membrane`, `analyte`; boundaries `axis`, `wall`, `membrane`, `membrane_outer`, `cis`, `trans`, `analyte`. **No aliases**, and `pore` is not a name | The names `mesh/primitives.py` assigns and `ELECTROLYTE_DOMAINS`, `DEFAULT_BOUNDARIES`, `ANALYTE_DOMAIN` and `ANALYTE_BOUNDARY` already select on, plus the one the Phase-0 shapes never needed. An alias table is how a vocabulary rots: two names for one region means two regexes, and the day they diverge the fluid loses a domain silently — the trap `ELECTROLYTE_DOMAINS` was written to document |
| The protein body | A material of its own, `protein`, decided by the author. The phase plan's `pore` is dropped **not** as a synonym of `electrolyte` but as ambiguous between the lumen and the dielectric body | The reference geometry has three domains and one of them is the protein (§2.2, §Design). Phase-0's shapes have no solid but the membrane, so this is the first geometry that needs the name; `physics/models.py:399` already takes it as a `solid_permittivities` key, so nothing else changes |
| A solid with no permittivity | On an **ingested** mesh, **abort** naming the material; the in-process benchmark geometries keep today's warning (`models.py:670`) | Poisson is solved over the whole domain, so the fallback is the electrolyte's ε_r, about 24× too large in a solid — QR-12's plausible wrong answer. The asymmetry is deliberate: the benchmark meshes' material names are written by this codebase and covered by tests, an ingested mesh's are not |
| Reversed `groups:` map | Detected and named: a mapping whose keys are all vocabulary names while its values are not aborts with "this looks reversed", not with every group unclaimed | The one ergonomic cost of keying on the file's names is that a reader writing the map from the solver's side gets a diagnostic pointing at the wrong thing. Two lines of check buy the right one |
| One route in | Every readable format lands in one `MeshData` and every mesh goes through the same tagging and the same gate, **`.vol` included** | A second route that skips the gate is the hole the gate exists to close. `.vol` round-trips names [tested, WP7] and stays readable, but it earns no exemption: today it is the *only* format the solver accepts and the only one nothing checks |
| Archival write | **MSH 4.1 through meshio**, with the entity bookkeeping constructed by us: one cell block per physical group, `gmsh:geometrical` constant within a block, `gmsh:dim_tags` on every node, and every entity owning at least one node | IF-06. meshio's 4.1 writer derives `$Entities` from node `dim_tags` alone and writes one entity per *cell block*, so the naive construction silently collapses four boundary groups into one and the naive node map omits entities the elements reference. Both failure modes are reproduced in §Design with the arithmetic and the fix |
| Reading MSH | **meshio**, never `netgen.read_gmsh.ReadGmsh` | It is a 2.2 parser (§Context). Using it would make the archival format unreadable by the code that writes it |
| Building the NGSolve mesh | `netgen.meshing.Mesh` assembled from arrays — `MeshPoint` per vertex, `Element2D` against one `FaceDescriptor` per material, `Element1D(index=k)` against `SetBCName(k-1, name)` — then `ngsolve.Mesh(ngmesh)` | Verified end to end: materials, boundaries, regex selection, `dirichlet=` spaces and boundary integrals all come out correct (§Design). It is also the only route that does not require an OCC geometry, which an ingested mesh does not have |
| Quality measures | **Both SICN and gamma**, gate `min > 0.3` on each, and a separate named failure for `SICN ≤ 0` | They are not the same gate. A triangle at SICN = 0.3 has gamma = 0.1298, and one at gamma = 0.3 has SICN = 0.4687 [verified], so "min SICN/gamma > 0.3" admits two different meshes depending on which you read. Gating both takes the strict reading. And gamma is unsigned — an inverted equilateral scores gamma = 1 and SICN = −1 — so gamma alone cannot see an inverted element at all |
| Where the metric comes from | Computed in project code from the vertex coordinates, by the formulas in §Design | They agree with `gmsh.model.mesh.getElementQualities(..., "minSICN")` and `"gamma"` **to every digit printed** on five reference triangles [tested]. The threshold is therefore calibrated against the implementation that set it, without gmsh on the default path (CON-10) |
| The gmsh cross-check | A Tier-1 test skipping on `ImportError` **and `OSError`**, comparing `abs(SICN)` rather than SICN | The gmsh wheel dlopens X and GL at import: in a bare container it raises `OSError: libGLU.so.1: cannot open shared object file`, not `ImportError`, so a bare `pytest.importorskip` errors the suite instead of skipping it [tested]. And gmsh returns +1 for a clockwise triangle in a discrete 2-D entity, so the sign convention is ours alone and only the magnitude is comparable |
| Where the gate fires | At ingestion, and after every mesh this package generates. `primitives.generate` gains `check_quality: bool = True` | The measured margin (min SICN 0.647 against a 0.3 gate) says an unconditional gate costs nothing and would have caught a degenerate benchmark mesh had one ever been produced. A gate that only guards imported meshes leaves the geometry we build ourselves unwatched |
| Mesh artefact identity | `sha256` over **vertices, element connectivity and the tag maps in file order**, not over file bytes; the source file's `file_hash` is recorded in the summary for provenance | The phase plan's decision. A mesh rewritten by meshio with a different header is the same mesh; a mesh whose `wall` group gained an edge is not. The cost is that `MeshStage.key(inputs)` must read the mesh — seconds against a solve of minutes, and the alternative files one mesh under two keys |
| Stage 6 | Registered as `mesh` → `nanopnp.mesh.ingest:MeshStage`, and `SolveStage` takes the mesh artefact from `upstream` when given one and computes it itself otherwise | Exactly the WP7 precedent for materials: one code path builds the key whether the pipeline ran the stage or the stage was invoked alone, so a pipeline run and a stage-alone run fill one store entry rather than two |
| Reference geometry input | A **profile fixture**, `data/geometry/clya_reference_profile.yaml`, derived from the delivered CSV and loaded through a pydantic model like every other serialisation boundary; `mesh/reference.py` assembles and meshes it and does not extract it | The polygon is data (the *corrections are data* rule, applied to geometry). The CSV stays beside it verbatim as the delivered artefact, and the fixture's `provenance:` block records which table it is and the sha256 it was derived from, so a later reconciliation is a data drop |
| Membrane-to-pore junction | **Boolean subtraction**, not a glue against matching coordinates: the membrane is the quadrilateral minus the pore body, and the conformality gate asserts the two cut radii taken from the fixture, not the drawn corners | Measured on the delivered table: the drawn corners (2, −1.4) and (3.5, +1.4) are 0.275 and 0.540 nm inside the pore body, so a coordinate gate against them fails on the real geometry (§Design) |
| Contour extraction | **Not in this package.** `reference.py` consumes a vertex table; it never produces one | FR-07/FR-08 are the Phase-2 contour pipeline. Assembling a region from a supplied polygon is FR-09's CAD half and is what WP13's comparison needs; conflating them would pull the density and marching-squares stack into Phase 1 |

## Design

### The vertex count: OPN-05 is two numbers counting two things

The specification says the pore boundary is a "closed 196-vertex polygon" (§2.2 line 120, §5.2.1),
while `.knowledge/09-comsol-reference-settings.md` §C.9, mined from the model report's geometry
section, records **190 vertices for the pore polygon** and **3 domains / 198 boundaries / 196
vertices** for the whole geometry. `CLAUDE.md` says the model report governs, and it is unambiguous:
the two numbers count the pore polygon and the assembled geometry respectively, and §2.2's "196" is
the geometry-wide figure attached to the wrong object.

The counts corroborate each other once the membrane's construction is right — and it is not the one
this plan first wrote down. The quadrilateral's inner edge is *buried* in the pore body, so its drawn
corners survive nothing; what the assembly adds to the 190 polygon vertices is the two points where
the planes `z = ±1.4` cut the pore's **outer** surface, each splitting a polygon edge (+2 vertices,
+2 edges); the membrane's two outer corners on the reservoir arc at
`r = √(250² − 1.4²) = 249.99608` (+2, +2); and the arc's two endpoints on the axis at `(0, ±250)`
(+2, +2). Closing the region takes six further edges: the axis, the `cis` and `trans` arc segments,
the `membrane_outer` arc between the corners, and the membrane's two faces at `z = ±1.4`.

```
vertices    190 + 2 + 2 + 2                 = 196
boundaries  190 + 2 (splits) + 6 (closures) = 198
Euler       196 − 198 + 4 faces             = 2
```

Both reported numbers, and the mesh's 196 vertex elements (§5.2.2) — one per geometry vertex — are
the same 196, none of them the polygon's. The delivered table has 185 vertices and already carries a
vertex exactly on the cis plane at `(4.88, +1.4)`, so it needs one split rather than two and
assembles to 190 vertices and 192 boundaries, Euler closing at 2 again. Amendments A and F record
all of this; the five-vertex difference is the last thing OPN-05 is open on.

> **Outcome — the assembly delivers 193 vertices and 195 edges, not 190 and 192.** The
> arithmetic above is right about the geometry and silent about the kernel, and the kernel adds
> three of each, both deliberately. Two come from breaking the side on `r = 0` into three collinear
> segments at the pore's axial extent (+2 vertices, +2 edges): OCC keeps collinear segments apart,
> the pore polygon never touches the axis, and this is the only way §5.2.2's 0.075 nm "symmetry axis
> inside pore" size can be applied as a size field at all. The third is the seam OCC places at
> parameter zero on a closed circle, at `(250, 0)`, which survives the clip to `r ≥ 0` and halves
> `membrane_outer` into two arcs meeting there (+1, +1) — a closed circle has a seam somewhere.
> VER-28 asserts 193/195 and the per-name breakdown: 186 edges around the pore (151 `wall`,
> 35 `interface`), 3 `axis`, 2 `membrane`, 2 `membrane_outer`, one each of `cis` and `trans`.
> §5.2.1 carries the same NOTE. The 185-versus-190 count is untouched by any of it.

### The reference geometry, written out

All lengths in nm, all from §5.2.1, §5.2.2 and `.knowledge/04` §2.

| Element | Definition |
|---|---|
| Reservoir | half-disc `r ∈ [0, 250]`, `r² + z² ≤ 250²`; the outer arc splits at `z = 0` into `cis` (z > 0) and `trans` (z < 0) |
| Membrane | quadrilateral (2, −1.4), (3.5, +1.4), (250, +1.4), (250, −1.4); thickness 2.8, mid-plane `z = 0` |
| Pore | closed polygon, `z ∈ [−1.85, 12.25]`, `r ∈ [1.65, 5.66]` |

The membrane is a quadrilateral and not a rectangle: its inner edge slants from `r = 2.0` at
`z = −1.4` to `r = 3.5` at `z = +1.4`, a slope of `1.5/2.8 = 0.535714` nm per nm, 28.18° from the
axis. The delivered table says why, and it is not the reason this plan first gave. That edge lies
**inside** the pore body along its whole length [tested]:

| Plane | Pore spans | Edge enters at | Clear of the lumen | Clear of the outer surface |
|---|---|---|---|---|
| `z = −1.4` | `r ∈ [1.725, 2.7524]` | 2.0 | 0.275 | 0.752 |
| `z = +1.4` | `r ∈ [2.96, 4.88]` | 3.5 | 0.540 | 1.380 |

The lumen wall passes through `(2.0, 0)` exactly and has opened to `r = 2.96` by `z = +1.4`, so a
*vertical* inner edge at `r = 2` would put membrane material inside the electrolyte for every
`z > 0`. The slant is the fix, and burying the edge is the point: the assembled membrane is the
quadrilateral **minus** the pore body, meeting the pore on the pore's own outer surface wherever that
runs. There is nothing to make coincide, so the gate this plan first wrote — `|r_out(−1.4) − 2.0|`
and `|r_out(+1.4) − 3.5|` under a gluing tolerance — asserts the wrong numbers and would fail on the
reference geometry. It is replaced by four assertions on the fragmented region:

```
r_out(−1.4) = 2.7524 ± tol        r_out(+1.4) = 4.88 ± tol
```

both read from the fixture rather than hard-coded; the membrane-facing part of the pore boundary is
**one** edge chain shared with the membrane face, not two coincident chains, because two coincident
chains give conforming coordinates and a non-conformal mesh; no membrane material anywhere inside
`ELECTROLYTE_DOMAINS`; and the region has exactly three domains.

Three, not four, and the delivered table is what makes that non-obvious. The cap's underside is
re-entrant — the boundary runs inward from `(4.29, −0.7)` to `(3.33, −0.14)`, back out to
`(3.48, 0.15)` and over a closed top at `z ≈ 0.26` — so the membrane fills a cleft under the cap and
its boundary is not monotone in `z`. That cleft opens downward past the cap edge at `z ≈ −0.7`, so it
is continuous with the rest of the membrane, and the membrane is one domain; the electrolyte is a
second, single domain because the lumen joins the two reservoirs; the pore body is the third. An
implementation that fragments the cleft off as its own face has a bug, and the domain count is the
cheapest test for it.

The membrane's outer edge at `r = 250` lies outside the arc (`250² + 1.4² > 250²`), so the
quadrilateral is intersected with the half-disc and `membrane_outer` is the resulting arc segment
`|z| ≤ 1.4`, not a straight segment. An implementation that builds `membrane_outer` as a segment at
`r = 250` leaves a sliver between it and the arc.

> **Outcome — the four assertions hold as written; two kernel details were not foreseen.**
> `r_out(−1.4) = 2.7524` and `r_out(+1.4) = 4.88` are what the fragmented region reports, the
> membrane-facing part of the pore boundary is one shared chain, no membrane element lies inside
> `ELECTROLYTE_DOMAINS`, and the region has exactly three domains — the cleft under the cap is not
> fragmented off. What the plan did not predict: (i) the quadrilateral must be traced *past*
> `r = 250`, by one membrane half-thickness, and clipped back by the intersection. Ending it exactly
> on the reservoir radius makes its outer edge touch the arc at the single point `(250, 0)` instead
> of crossing it, a boolean the kernel has to resolve exactly for no gain; any overshoot removes the
> contact. (ii) `membrane_outer` is the arc segment as predicted, but it is *two* arcs, not one, for
> the circle-seam reason recorded above — a test asserting a single `membrane_outer` edge would
> fail on a correct geometry.

### The delivered vertex table, and what it does not settle

`data/geometry/clya_as_radial_geometry.csv` is the ClyA-AS radial geometry as supplied by the
reference model's author, kept **verbatim** — CRLF line endings included — so that its sha256
`d0c2008…b0b386` identifies the delivered artefact and not our reformatting of it. Every row below
was measured on the file [tested]:

| Property | Value |
|---|---|
| Vertices | 185, no duplicates, closing edge implied rather than repeated |
| Extent | `r ∈ [1.65, 5.66]`, `z ∈ [−1.85, 12.25]` — §2.2's published extents to the digit |
| Topology | simple closed loop, no self-intersection |
| Orientation | clockwise in `(r, z)`; signed area −26.4939 nm² |
| Vertex spacing | min 0.0361 nm; 10 of 185 edges below 0.05 nm |
| Local feature size | min 0.0806 nm |

Three things follow.

**The fixture is derived, and the derivation is tested.** `mesh/profile.py` converts the CSV once
into `data/geometry/clya_reference_profile.yaml` — `provenance: {source: author-supplied, citation,
sha256, vertex_count}` — and a Tier-1 test re-derives the YAML from the CSV in the tree and asserts
they agree, so the two cannot drift. `data/` is force-included into the wheel already
(`pyproject.toml:78`), so `data/geometry/` ships with no packaging change. The nominal stand-in this
plan previously specified is **dropped**: nothing nominal ships, and `is_reference` becomes
`source in {model-report, author-supplied}` rather than `source == model-report`.

**Two of §5.2.1's conditioning criteria would reject the reference polygon.** At the reference wall
size of 0.05 nm its minimum vertex spacing is 0.0361 nm and its minimum local feature size 0.0806 nm
against a 0.1 nm threshold — and that same polygon, at that same wall size, produced the reference
mesh with minimum element quality 0.6378. The criteria are about contours the FR-08 pipeline
*produces*, not about a supplied fixture; amendment F says so, and the fixture is gated on validity,
simplicity and topology instead, with its spacing and feature size recorded in provenance.

**Five vertices are unaccounted for.** The model report's 190 against the delivered 185, with the
assembly arithmetic above consistent for either. Nothing in this package depends on which is cited;
§Open questions carries it.

### Element quality: the two measures, and why both

For a straight-sided triangle `p₀, p₁, p₂` let `A = [p₁ − p₀, p₂ − p₀]` be the Jacobian of the
affine map from the unit triangle, `E = [[1, ½], [0, √3/2]]` the same for the unit equilateral, and
`J = A E⁻¹`. Then

```
SICN  = sign(det J) · 2 / (‖J‖_F ‖J⁻¹‖_F)
gamma = 2 r_in / R_circ = (8 A²) / (s · a · b · c)         s = (a+b+c)/2
```

Both are 1 on the equilateral element and scale-invariant. Check values, computed and confirmed
against `gmsh.model.mesh.getElementQualities` to every printed digit [tested]:

| Triangle | SICN | gamma |
|---|---|---|
| equilateral | 1.000000 | 1.000000 |
| right isoceles, unit legs | 0.866025 = √3/2 | 0.828427 = 2√2 − 2 |
| isoceles, unit base, height 0.2 | 0.438494 | 0.265631 |
| isoceles, unit base, height 0.05 | 0.115086 | 0.019753 |
| equilateral × 1000 | 1.000000 | 1.000000 |
| equilateral, clockwise | **−1.000000** | **+1.000000** |

The last row is why both are gated: gamma is blind to inversion. And the middle rows are why "min
SICN/gamma > 0.3" needs reading as a conjunction — solving each for the isoceles family on a unit
base gives `SICN = 0.3` at height 0.132966, where `gamma = 0.129841`, and `gamma = 0.3` at height
0.215508, where `SICN = 0.468673`. The two thresholds differ by a factor of 1.56 in element height.
Amendment D records this in §5.2.2.

> **Outcome — the factor is 1.6208, not 1.56.** `0.21550836/0.13296607 = 1.62078`, computed by
> `brentq` on the two closed forms in `tests/tier1/test_mesh_quality.py`
> (`test_ver10_the_two_measures_are_not_interchangeable`, asserted to 10⁻⁴). The plan and
> §5.2.2 both carried 1.56, which is neither ratio of any pair of the four numbers printed here;
> the specification is corrected in the same commit as the code comment. Nothing depends on the
> figure — it is the *argument* for reading the gate as a conjunction, and it is stronger than
> stated, not weaker.

gmsh returns **+1** for the clockwise triangle: a 2-D element in a discrete entity has no intrinsic
orientation there, so the sign is ours. In an axisymmetric (r, z) mesh it is load-bearing — a
negative-Jacobian element contributes negative area under the `r` weight and nothing else complains
— so `SICN ≤ 0` is reported as `inverted element`, separately from `below the quality gate`, and the
gmsh calibration test compares `abs(SICN)`.

Measured on the geometries the suite uses today [tested]:

| Geometry | elements | min SICN | mean SICN | min gamma | mean gamma |
|---|---|---|---|---|---|
| `SlabGeometry(3.0)`, maxh 0.5, wall 0.05 | 192 | 0.7860 | 0.9608 | 0.7489 | 0.9551 |
| `CylinderGeometry(2, 4)`, maxh 0.5, wall 0.05 | 811 | 0.6473 | 0.9700 | 0.5510 | 0.9661 |
| `CylindricalPoreGeometry(2, 6, 10)`, maxh 4, wall 1 | 124 | 0.7138 | 0.9384 | 0.6860 | 0.9286 |
| `CylindricalPoreGeometry(2, 6, 10)`, maxh 1, wall 0.1 | 1,665 | 0.7644 | 0.9666 | 0.7200 | 0.9616 |
| `CylindricalPoreGeometry(2, 13, 50)`, maxh 2, wall 0.05 | 8,141 | 0.7008 | 0.9749 | 0.6384 | 0.9714 |

Against the reference model's 0.6378 minimum and 0.9765 mean on 120,917 triangles (§5.2.2), netgen's
graded free meshing is already in the same band at a fortieth of the size. Two consequences: the
gate is unconditional, and the end-of-phase comparison of the reference-geometry mesh against those
two figures has a real chance of being a pass rather than an excuse.

> **Outcome — it is a pass, and the unconditional gate immediately earned its keep.** The ClyA
> region at the §5.2.2 size fields, `grading = 0.2`, `optsteps2d = 5`, meshes in 6.5 s to **44,316
> triangles, minimum SICN 0.6559, mean 0.9870, minimum gamma 0.6157, mean 0.9852**, no inverted
> elements — a third of COMSOL's 120,917 elements in the same quality band (0.6378 minimum, 0.9765
> average), without boundary layers. The gate itself costs ≈1.1 s on a 121k-element mesh, a fraction
> of the time to build one, which is what makes "unconditional" cheap. Its first run then rejected a
> mesh the suite had been solving on for two packages: VER-16's Gouy–Chapman slab is 2000 nm ×
> 0.5 nm at `maxh = 50 nm`, a chain of 100:1 triangles at minimum SICN 0.019. That anisotropy is not
> a defect — the transverse extent is an artefact of solving a one-dimensional problem on a
> two-dimensional mesh, and the stretched direction is the one the solution is constant in — so the
> exemption is one keyword-only `check_quality=False` at that call site, with its reasoning beside
> it, and the floor is untouched. `mesh/quality.py` and `.knowledge/06-numerics-fem.md` §8 carry the
> numbers.

### Writing MSH 4.1 through meshio, and the two ways it goes wrong silently

meshio's 4.1 writer needs entity bookkeeping that a mesh built from a tagged FE mesh does not
naturally carry, and it fails in three distinguishable ways [all tested, meshio 5.3.5]:

1. **No `gmsh:dim_tags` at all** → `WriteError: Specify entity information (gmsh:dim_tags in
   point_data) to deal with more than one cell type`. Loud; not the problem.
2. **An entity that owns no node is never written.** `_write_entities` builds `$Entities` from
   `np.unique(point_data["gmsh:dim_tags"])` alone, so an entity referenced by a cell but owning no
   node is omitted, and reading the file back raises `KeyError` inside `_read_elements` — after the
   write reported success. Any node-ownership rule must therefore guarantee **every entity owns at
   least one node**: assign each node the lowest-dimensional entity touching it, then, for any group
   still unrepresented, reassign one of its nodes to it.
3. **One cell block is one entity.** `_write_elements` takes `tag_data["gmsh:geometrical"][ci][0]` —
   the *first* tag of the block — and writes the whole block under it. Four boundary groups packed
   into a single `line` block came back from a round trip with all four physical tags equal to the
   first. Nothing raised. The mesh was silently one-quarter right, which for a boundary vocabulary
   means three no-flux walls became one.

So the writer emits **one cell block per (physical group, element type)**, a constant
`gmsh:geometrical` per block, and the node map above. With that construction a 4-group, 1-material
mesh round-trips through meshio with names, per-group physical tags and connectivity intact
[tested], and the same `meshio.Mesh` written as 2.2 is read by netgen with both name sets recovered
— which is how the archival format and the legacy reader are kept honest against each other.

### Building the NGSolve mesh from arrays

Verified recipe [tested], on a 16-vertex, 18-element mesh with four boundary groups:

```python
ngmesh = netgen.meshing.Mesh(dim=2)
for k, name in enumerate(materials, start=1):  # one FaceDescriptor per material
    fd = ngmesh.Add(FaceDescriptor(surfnr=k, domin=k, bc=k))
    ngmesh.SetMaterial(k, name)
points = [ngmesh.Add(MeshPoint(Pnt(r, z, 0.0))) for r, z in vertices]
for tri, material in zip(triangles, triangle_material):
    ngmesh.Add(Element2D(descriptor[material], [points[i] for i in tri]))
for k, name in enumerate(boundaries, start=1):
    ngmesh.Add(FaceDescriptor(surfnr=k, domin=1, bc=k))
    ngmesh.SetBCName(k - 1, name)
    for a, b in edges[name]:
        ngmesh.Add(Element1D([points[a], points[b]], index=k))
mesh = ngsolve.Mesh(ngmesh)
```

`SetBCName` is **0-based** while `Element1D(index=…)` is **1-based**; getting that pair wrong shifts
every boundary name by one, which is a mesh where `wall` is the axis and nothing raises. After
construction `mesh.GetMaterials()`, `sorted(set(mesh.GetBoundaries()))`, `Boundaries("wall")`,
`H1(..., dirichlet="wall")` and boundary integrals all behave as they do on an OCC-generated mesh
(unit square: area 1.0, `wall` length 1.0, both to 4 × 10⁻¹⁵).

Extraction runs the other way through `ngmesh.Points()` and `ngmesh.Elements2D()`, whose
`el.vertices[i].nr` is **1-based** [tested] — the same off-by-one, in the same package, in the
opposite direction.

### Findings this plan established by running code

Six facts above were established by executing NGSolve 6.2.2606, netgen, meshio 5.3.5 and gmsh
4.15.2 in this environment rather than by reading documentation, and `/wp-implement` SHALL write
them into `.knowledge/06-numerics-fem.md` §8 marked **[tested]** as it lands the code: netgen's
`ReadGmsh` is an MSH 2.2 parser and fails on 4.1; meshio's 4.1 writer collapses a multi-group cell
block to one physical tag and omits an entity that owns no node, both silently on write; the
array-to-`netgen.meshing.Mesh` recipe with its two opposite 0-/1-based index conventions; the SICN
and gamma formulas agreeing with gmsh to every printed digit; gmsh's +1 for a clockwise 2-D element;
and the gmsh wheel raising `OSError` rather than `ImportError` when X and GL are absent. Each of
them cost an experiment to find and would cost the same one twice.

### What the ingestion gate actually checks, in order

1. The file exists and its format is readable (extension, or `inputs.mesh.format` when given).
2. It reads into `MeshData`: vertices, triangles with a material index, edges with a group index,
   and the two name tables.
3. Every file group is claimed by `inputs.mesh.groups`; every required name (derived from the
   resolved case, §Decisions) is supplied by some group. Otherwise abort, naming both lists.
4. `SICN` and `gamma` per element; abort if `min ≤ 0.3` on either, or if any `SICN ≤ 0`, reporting
   the worst element's index, its (r, z) centroid and both metric values (QR-12).
5. `min(r) ≥ 0` over all vertices — an (r, z) mesh with negative radius integrates to negative
   volume under the `r` weight, and the `1/r` forms are worse.
6. Only then is the NGSolve mesh built and the PHY-02 distance field taken from the mapped `wall`.

Steps 3–5 are the abort surface, and each names its gate. Step 6 is where VER-06 and NUM-31 are
re-verified against tags that came from a file rather than from `name_edges`.

> **Outcome — the order is as delivered; the vocabulary gained an eighth boundary name, and
> step 5 needed a snap in front of it.** `interface` is now in `BOUNDARY_VOCABULARY`: fragmenting a
> region produces an interior seam wherever two domains meet with no physical boundary between them
> — `CylindricalPoreGeometry`'s two pore mouths, which OCC leaves at NGSolve's `default`, and the
> reference geometry's 35-edge protein-to-membrane seam. Without a name for it, an ingested
> fragmented mesh either fails step 3 or has its seams mapped to a boundary that *is* selected on,
> which is the silent-open-boundary failure the gate exists to prevent. Amendment G's `protein`
> landed with it. Step 5's `min(r) ≥ 0` also cannot be applied to netgen's own output as it stands:
> the OCC kernel places axis vertices at `r = −1.5 × 10⁻¹⁵` and `+7 × 10⁻¹⁶` nm, so `MeshData`
> snaps `|r| < 10⁻⁹` nm to zero on every route in and the gate keeps asking for `r ≥ 0` exactly —
> the failure it catches is a sign error, not a rounding one, and slackening it to `r ≥ −ε` would
> hide the former to tolerate the latter.

## Work items

| File | Delivers | Identifiers |
|---|---|---|
| `mesh/adapter.py` | `MeshData` (vertices, triangles, material index, edge blocks, name tables, `content_hash`); `read(path, *, format=None) -> MeshData` over meshio and netgen `.vol`; `write_msh41(data, path)` with the entity construction of §Design; `to_ngsolve(data) -> Mesh`; `from_ngsolve(mesh) -> MeshData` | IF-06 |
| `mesh/ingest.py` | `VOCABULARY` (materials incl. `protein`, boundaries, no aliases); `required_names(resolved) -> frozenset[str]`; `apply_groups(data, groups) -> MeshData` with the reversed-map diagnostic; `MeshVocabularyError`; `check_solid_permittivities(mesh, model)`; `ingest(supplied, resolved) -> Mesh`; `MeshStage` (stage 6) with `key(inputs)` beside `run(inputs)` | IF-06, QR-12, PHY-03, FR-27 |
| `mesh/quality.py` | `element_quality(data) -> QualityReport` (per-element SICN and gamma, min/mean/worst with centroid); `QUALITY_FLOOR = 0.3`; `check_quality(data)` raising `MeshQualityError(gate, quantity, location)`; `inverted_elements(data)` | VER-10, QR-12 |
| `mesh/reference.py` | `ReferenceGeometry` from a profile fixture: the membrane quadrilateral, the 250 nm half-disc, fragmentation, edge naming into the vocabulary, the §5.2.2 size fields and the `optimize("Netgen")` pass; `junction_report()` for the conformality gate | FR-09 (CAD half), VER-28 |
| `mesh/profile.py` | `PoreProfile` pydantic model over the fixture — `provenance: {source, citation, sha256, vertex_count}`, `vertices: list[tuple[float, float]]` — with `is_reference` gating Tier-3/4 use; `load_profile(name)` through `core/paths.py`; `profile_from_csv(path)`, the one-way conversion the fixture is built and re-checked with | §5.2.1, IF-03 pattern |
| `data/geometry/clya_as_radial_geometry.csv` | **Landed.** The delivered 185-vertex table, verbatim, beside a `README.md` recording its provenance, hash and measured properties | §5.2.1, OPN-05 |
| `data/geometry/clya_reference_profile.yaml` | The fixture derived from that CSV, `source: author-supplied`, with the sha256 it came from | §5.2.1 |
| `mesh/primitives.py` (edit) | `generate(..., check_quality: bool = True)` on all three geometries, routed through `mesh/quality.py` | VER-10 |
| `mesh/distance.py` (edit) | Docstring pointer to the ingestion gate as the thing that makes `sources="wall"` mean the pore wall on an ingested mesh; no behaviour change | PHY-02 |
| `solve/stage.py` (edit) | `_mesh_path` and `MESH_SUFFIXES` replaced by `mesh.ingest.ingest`; the mesh enters the digest as the artefact's content hash, not `file_hash`; the mesh artefact is taken from `upstream` when supplied | §5.3.2, FR-27 |
| `core/stages.py` (edit) | `register(StageDescription(name="mesh", number=6, …), "nanopnp.mesh.ingest:MeshStage")` | FR-27, IF-01 |
| `io/manifest.py` (edit) | The `geometry_and_mesh` group gains the quality statistics, the vocabulary mapping actually applied and the profile fixture's provenance — the extension its docstring at `manifest.py:410` already names | FR-25, IF-08 |
| `core/paths.py` (edit) | `geometry_dir()` beside the corrections directory, dual-location as `data/corrections` already is | — |

`MeshData` is the seam behind the mesher adapters of §5.1: meshio, netgen and (in a later package)
gmsh all produce it, and nothing downstream of `adapter.py` knows which one did. It is the mesh
analogue of QR-13's rule for the weak forms, not a discharge of it.

> **Outcome — every row delivered; three carry more than the row asked for.** `mesh/adapter.py`
> also gained `canonical()` and `renamed()` — the hash is taken over a canonicalised form because a
> 4.1 round trip permutes nodes and cells, so a byte-for-byte identical mesh written twice by meshio
> hashes differently otherwise — and `_snap_to_axis()`, for the kernel's `−1.5 × 10⁻¹⁵` nm axis
> vertices. `mesh/ingest.py`'s vocabulary gained `interface` beside amendment G's `protein`, and its
> `required_names` reads `wall_distance.sources` and the flow model as well as the boundary
> selections, so a case widening either aborts at ingestion rather than at form assembly.
> `mesh/profile.py`'s local feature size skips the vertex's own two-edge neighbourhood; measured
> over one edge instead, the delivered table's feature size collapses from 0.0806 nm to its
> minimum vertex spacing, 0.0361 nm, and the criterion measures spacing twice rather than
> proximity once.

## Specification changes in this commit

- **A. §2.2 and §5.2.1: the pore polygon has 190 vertices, the assembled geometry 196.** Both places
  currently say 196 for the pore boundary. The model report's geometry section records 190 for the
  pore and 3 domains / 198 boundaries / 196 vertices for the geometry, and `CLAUDE.md` makes the
  model report govern. §5.2.2's "196 vertex elements" is then the same 196, one vertex element per
  geometry vertex, rather than a third number. VAL-05 (§7.4) and RSK-05 lose "196-vertex" for
  "published pore polygon". Amendment F then corrects the *composition* of the extra six and records
  the delivered table.
- **B. §5.3.1's `inputs.mesh.groups` gains a NOTE and its example is corrected.** The example reads
  `groups: {pore: pore, membrane: membrane, reservoir: bulk}`, whose direction is unstated and whose
  three values name nothing the solver speaks. It becomes
  `groups: {pore_wall: wall, bilayer: membrane, lumen: electrolyte, upper: cis, lower: trans}`, with
  a NOTE fixing the direction (file group → vocabulary name), allowing many-to-one, listing the
  vocabulary, and stating that every group must be claimed and every name the run selects on must be
  supplied, on pain of an abort naming both (QR-12).
- **C. §5.2.2 gains a NOTE on the quality gate**: SICN and gamma are distinct measures, both are
  gated at 0.3, and the arithmetic showing they are not interchangeable (SICN 0.3 ↔ gamma 0.1298;
  gamma 0.3 ↔ SICN 0.4687). It also records that gamma cannot detect an inverted element and that
  `SICN ≤ 0` is reported as its own failure.
- **D. §7.2 gains VER-27 and VER-28.** VER-27, mesh ingestion and tagging: a mesh written as MSH 4.1
  and read back preserves per-group tags and names; an unmapped group or an unsupplied required name
  aborts naming both sides; the default ingestion path imports neither `gmsh` nor netgen's Gmsh
  reader, asserted on `sys.modules`. VER-28, reference-geometry conformance: the assembled region is
  conformal at the membrane-to-pore junction — coordinates within the gluing tolerance *and* one
  shared edge, not two — carries exactly the vocabulary, and meets the §5.2.2 quality figures.
- **E. Appendix A**: IF-06 gains VER-27 (it reads "None yet" today), CON-10 gains VER-27, FR-09
  gains VER-28 beside VAL-05. FR-10's row already names VER-10, and QR-13 stays "None yet" — it is
  about the weak forms, not the mesher adapters, and `MeshData` discharges nothing of it. The
  coverage sentence under the table is corrected in passing from "26 of the 67 … 41 recorded as
  none yet" to **35 and 32**, which is what the table has actually said since WP7 filled six rows
  without updating the count.

- **F. §2.2 and §5.2.1 record the delivered table and correct the junction.** §2.2's membrane row
  said the inner edge is "slanted to meet the pore's outer surface"; measured against the table it is
  slanted so as to lie *inside* the pore body, and the assembled membrane is a subtraction. §5.2.1
  gains the table's location and measured properties, a NOTE deriving the junction and the three-domain
  count, the corrected 190 + 6 = 196 composition with the 198-boundary and Euler checks, and a NOTE
  exempting a supplied fixture from the two conditioning criteria it does not meet — with the reason,
  which is that the reference mesh was built from this polygon at 0.05 nm and reached quality 0.6378.
  OPN-05 is rewritten: delivered, open only on the 185-versus-190 count, with no implementation
  consequence either way.

- **G. §5.3.1's vocabulary gains `protein` and two rules.** The pore's dielectric body is a domain of
  the reference geometry and had no name; `protein` is it, `pore` is excluded in both its readings,
  and the `groups:` example gains `clya: protein`. A NOTE adds the reversed-map diagnostic, and a
  second NOTE makes a solid with no `physics.solid_permittivities` entry abort on an ingested mesh
  (PHY-03, QR-12) where `models.py:670` warns today. VER-28's wording is corrected to the delivered
  geometry with it.

## Verification

| Test file | Tier | Identifiers | What it asserts |
|---|---|---|---|
| `tests/tier1/test_mesh_adapter.py` | 1 | IF-06 | A tagged `MeshData` written as MSH 4.1 and read back has identical vertices, connectivity, per-group physical tags and names; the same data written as 2.2 is read by netgen with both name sets; a four-group mesh packed into one cell block is refused by the writer rather than collapsing to one tag; `to_ngsolve` then `from_ngsolve` is the identity on the tag maps; the content hash is stable across processes, ignores a rewritten header, and changes when one edge moves group |
| `tests/tier1/test_mesh_ingest.py` | 1 | IF-06, QR-12, PHY-03, VER-27 | A misspelt group aborts naming the unclaimed group *and* the vocabulary name left unsupplied; a map written vocabulary-first aborts saying it looks reversed; a mesh carrying a `protein` material with no `solid_permittivities` entry aborts naming it, while the same material on a primitives-built mesh only warns; an extra unclaimed group aborts; a case widening `wall_distance.sources` to a name no group supplies aborts; a correct mapping ingests and `mesh.GetMaterials()`/`GetBoundaries()` are exactly the vocabulary; ingesting imports neither `gmsh` nor `netgen.read_gmsh`, asserted on `sys.modules` in a fresh process (CON-10); a mesh with a negative-`r` vertex aborts |
| `tests/tier1/test_mesh_quality.py` | 1 | VER-10, QR-12 | SICN and gamma reproduce the six §Design check values to 10⁻¹² — equilateral (1, 1), right isoceles (√3/2, 2√2 − 2), the two slivers, scale invariance, and the clockwise element at (−1, +1); a mesh carrying one deliberate sliver aborts with the worst element's index, (r, z) centroid and both metrics in the message; an inverted element aborts under its own name; the five Phase-0 geometries pass with the measured minima; **optional**: our per-element values match `gmsh.model.mesh.getElementQualities` in magnitude, skipped on `ImportError` or `OSError` |
| `tests/tier1/test_wall_distance.py` (edit) | 1 | VER-06, NUM-31 | The existing gradient-jump and `d = 0`-on-the-wall assertions, re-run on an **ingested** mesh; the membrane is absent from the source set and `d` at the membrane exceeds `d` at the pore wall by the geometric separation |
| `tests/tier1/test_mesh_profile.py` | 1 | §5.2.1, IF-03 | The fixture round-trips through the pydantic model; an unknown key is named; `profile_from_csv(data/geometry/clya_as_radial_geometry.csv)` reproduces the shipped fixture exactly, and the CSV's sha256 matches the one in its provenance block; the delivered table's measured properties — 185 vertices, `r ∈ [1.65, 5.66]`, `z ∈ [−1.85, 12.25]`, simple, closed, area 26.4939 nm² — hold to 10⁻⁹; a profile whose `provenance.source` is `nominal` refuses a Tier-3/4 caller |
| `tests/tier1/test_stages.py` (edit) | 1 | VER-25, FR-27 | Stage 6 describes itself without importing `nanopnp.mesh.ingest`; `MeshStage.key(inputs)` equals the hash of the artefact `run` produces |
| `tests/tier2/test_reference_geometry.py` | 2 | VER-28, FR-09 | The assembled ClyA region has exactly three domains — pore body, one membrane (the cleft under the cap is not fragmented off), one electrolyte; the junction is conformal — `r_out(−1.4) = 2.7524` and `r_out(+1.4) = 4.88` within the fragmentation tolerance, read from the fixture, *and* one shared edge chain rather than two coincident ones; no membrane material inside `ELECTROLYTE_DOMAINS`; `membrane_outer` is the arc segment and not a straight edge; the meshed region passes the quality gate and its min/mean SICN are recorded against 0.6378/0.9765 |
| `tests/tier2/test_artefact_cache.py` (edit) | 2 | §5.3.2, QR-08 | The solve keyed on a mesh **content** hash: the same mesh rewritten with a different header is a store hit; a mesh with one boundary edge moved to another group is a miss |

Tolerances and where they come from: the quality check values are exact rationals and surds and are
asserted to 10⁻¹² (they agreed with gmsh to every printed digit, so the tolerance is round-off, not
physics); the gate is 0.3 from §5.2.2 and VER-10; the junction tolerance is OCC's gluing tolerance,
read from the kernel rather than hard-coded; the distance-field tolerances are VER-06's, unchanged
from Phase 0. Everything else in the package is an equality or an exception.

Gate before commit, unchanged:

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src/ && uv run pytest
```

Note for CI: the optional gmsh comparison needs `libGLU`, `libXft`, `libXinerama` and `libXcursor`
present at import [tested — the wheel dlopens them and raises `OSError`, not `ImportError`, when
they are absent]. The test skips rather than fails, so CI stays green either way; whether the
runner installs them is a workflow decision, not this package's.

> **Outcome — 78 test functions across the five new files, all green; two rows landed elsewhere
> than planned.** The stage-6 assertions are in `tests/tier1/test_mesh_ingest.py` rather than in
> `test_stages.py`, beside the stage they describe
> (`test_ver25_the_mesh_stage_is_stage_six_and_describes_itself`,
> `test_ver27_the_artefact_key_is_the_contents_and_the_mapping`, and the progress and cancellation
> pair FR-27 asks for); the two mesh-content cache assertions are in
> `tests/tier2/test_artefact_cache.py`, keyed on VER-26 and VER-27. The gmsh comparison skipped in this environment on the
> `OSError` the plan predicted, so the SICN and gamma check values stand on the closed forms and the
> six exact values, not on the oracle. `tests/tier2/test_reference_geometry.py` runs in 7.3 s; the
> full gate is 489 passed, 1 skipped, 10 deselected in 78 s.

## Out of scope

- **Contour extraction and conditioning** — FR-07, FR-08, §5.2.1's marching-squares and Taubin
  pipeline. Phase 2. `reference.py` consumes a vertex table; it never produces one.
- **Mesh *generation* from a case** — `numerics.mesh` stays the v0.9 block it is today, and stage 6
  ingests rather than meshes for any case the solver runs. `reference.py` generates one specific
  geometry for the Tier-3 comparison, which is a fixture, not the pipeline.
- **Gmsh as a mesher backend** — ADR-002's optional backend. WP8 uses gmsh only as the quality
  oracle in one skipped-by-default test, and asserts that ingestion never imports it (CON-10).
- **Boundary layers** — FR-11, post-1.0. The reference reached the published results without them.
- **External charge and dielectric fields** — WP9. `inputs.charge` and `inputs.eps_r` keep raising
  `UnsupportedCaseSection`; the QR-03 conservation check on the deployed mesh belongs with the field
  that declares `Q_net`.
- **The stabilised mode** — WP12; `SUPPORTED_STABILISATIONS` stays `{"none"}`.
- **Analyte remeshing per axial position** — §5.2.3. `geometry/analyte.py` builds the body and WP6
  verified the forces; sweeping `z_a` is WP11's job over WP8's ingestion.

## Open questions

One blocks part of the deliverable; the rest are assumed and stated so that none of them stops the
work.

1. **The five vertices (OPN-05, what is left of it).** The table landed while this plan was being
   written and is in the tree; the fixture, VAL-05 and VER-28 all proceed on it, and nothing in the
   package is blocked. What remains is a count: the model report records 190 vertices for the pore
   polygon, the delivered table has 185, and the assembly arithmetic of §Design closes consistently
   for either (196/198 for the report's, 190/192 for the delivered one). The delivered table also
   carries a vertex exactly on the cis membrane plane, which the report's polygon cannot have if its
   196 is to come out right — consistent with the delivered file being the curve *before* COMSOL's
   import conditioning, or after a later cleanup. Worth one sentence from the author; until then the
   fixture's provenance reads `author-supplied`, not `model-report`, and a Tier-3 comparison cites
   the file it actually used.

   > **Outcome — still open, and still costs nothing.** The delivered geometry assembles,
   > meshes into the published quality band and passes VER-28 on the 185-vertex table. The count
   > is a provenance question about which curve COMSOL imported, not a modelling one; §5.2.1
   > records both numbers and OPN-05 stays open on that alone.
2. **Settled by the author, 4 September 2026.** The mapping reads file group → vocabulary name, as
   assumed; the protein dielectric body is `protein` and `pore` stays out of the vocabulary in both
   its readings; and an ingested mesh whose solid has no permittivity aborts rather than warns. The
   decisions table and amendments B and G carry all three.
3. **The quality floor stays a constant**, also settled: `QUALITY_FLOOR = 0.3` is a module constant,
   not a case field, so it needs no `SWITCH_PATHS` entry and cannot be relaxed to make a bad mesh
   pass. Adding a field later is a compatible change and removing one is not, which is the argument
   for starting closed; if a real case ever needs the escape hatch it is a CLI flag that taints the
   manifest and refuses the store, not a case-file knob.

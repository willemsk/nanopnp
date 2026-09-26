# Phase 2 (Geometry pipeline): from a structure to a gated mesh

**Status: in progress. WP17 delivered, 24 September 2026; WP18 delivered, 25 September 2026; WP19 delivered, 25 September 2026; WP20 delivered, 26 September 2026; WP21 planned in detail, 26 September 2026; WP22–WP25 planned.** Written 24 September 2026, after Phase 1 (WP7–WP16) delivered the
solver core on an externally supplied mesh (main at `v0.5.0-alpha.10`). Two things come first:
the Phase 1 end-of-phase report, which merges as tag `v0.5.0`, and the author's double-click
observation that closes Phase 0 criterion 4. That ordering is ruling B1 of `SPECIFICATION.md`
§8.2.2. **Both were met on 24 September 2026** (the double-click is recorded in the NOTE to §8.2.1).

This is the delivery plan for Phase 2 of `SPECIFICATION.md` §8.1. With Phase 3 it makes up release
v0.9. The specification is normative: where this file and the specification disagree, the
specification governs and this file is wrong. Requirement identifiers here are pointers into it,
never restatements of it. The rulings behind this plan are recorded in §8.2.2 (B1–B7) and are not
re-argued here.

## Context

Phases 0 and 1 answered whether the physics is right and whether someone other than the author can
run it. Phase 2 answers a third question: **can the geometry the physics runs on be produced from a
structure, reproducibly, without the manual vertex editing the source work records?** The Methods
section of the source says the ClyA outline was obtained by "manual removal of overlapping and
superfluous vertices" (`.knowledge/04-clya-geometry-and-charge.md` §1, gap G3). This phase replaces
that step with the gated pipeline of §5.2 stages 1–6 and §5.2.1–§5.2.2. The gate is **VAL-05**: the
auto-generated geometry reproduces the hand-conditioned reference polygon.

The physics does not change. No weak form is touched, and nothing downstream of stage 6 needs to
know whether a mesh was generated or supplied. The mesh artefact and the VER-27 ingestion gate are
the seam between the two.

Four things are true of the codebase today and shape every package below.

- **Stages 6–12 exist; stages 1–5 do not.** `core/stages.py` registers `mesh`, `charge`,
  `materials`, `case`, `solve`, `qoi` and `report`. `structure/` and `symmetry/` are empty slots.
  `geometry/` holds only the analyte bodies, and `density/` holds only `grid.py`.
- **The two artefacts at the ends already have schemas.** `density/grid.py`'s `RadialGrid` is the
  (r, z) container that stage 3's reduced map fills. `mesh/profile.py`'s `nanopnp/profile/v1` is a
  validated closed polygon with a provenance block, which is exactly what stage 4 emits. Stage 4
  therefore writes the schema the reference fixture already uses, with `source: pipeline`.
- **`mesh/reference.py` is stage 5 for one polygon.** `ReferenceGeometry` assembles profile,
  membrane quadrilateral and reservoir with `occ.Glue`, names the edges into the §5.3.1 vocabulary,
  and meshes under the VER-10 gate. Its membrane corners and size fields are constants for ClyA.
  Generalising it, not rewriting it, is WP21.
- **The case schema has the blocks but refuses them.** `structure:` and `geometry:` validate, and
  `io/case.py` `_require_runnable` raises `UnsupportedCaseSection` on either. Schema v1 lacks two
  keys this phase needs, which is why the schema moves first (B3).

Risks this phase is scheduled to retire or move. **RSK-05**: slivers at the constriction, retired by
the FR-08 gate and the VER-10 gates on generated meshes. **RSK-06**: the author's contour script
proving non-portable; the script exists (B6) and is read before WP20 is planned. **RSK-07**: an
invalid axisymmetric reduction, made visible by the FR-06 variance output. **RSK-13** reopens
narrowly, because the desktop bundle gains MDAnalysis, scikit-image and Shapely, all of which carry
compiled extensions. **RSK-15** stays live: GUI increment 2 surfaces steps and adds no physics.

Deliberately excluded: structure *preparation* (mutations, missing residues, PDBFixer); the charge
and dielectric pipeline, FR-12 to FR-15 (Phase 3); FR-20 (Phase 3, B7); FR-11 boundary layers
(post-1.0); revolved-profile analytes of FR-21 (v1.0).

## Design decisions

Settled before the first package is planned. Each package's own `/wp-plan` decides the rest, in
its decisions table.

| Decision | Choice | Why |
|---|---|---|
| Order of evidence | Every stage is verified on a synthetic input with a closed form before it sees 2WCD, and on 2WCD before the ensemble | §7.1: an analytic test localises an error to one stage. A VAL-05 miss seen first localises nothing |
| Stage artefacts | Stage 1: aligned coordinates, atom table (element, chain, residue) and the axis transform record. The van der Waals radius moved to stage 2 (WP18 D10, 25 September 2026): it is a density-kernel parameter, so it belongs in stage 2's key. Stage 2: the 3D map, native `.npz` float32, with OpenDX/CCP4 export through GridDataFormats (IF-05). Stage 3: a `RadialGrid` map plus its variance grid. Stage 4: `nanopnp/profile/v1`, `source: pipeline`, carrying the conditioning record. Stage 5: a declarative region record (profile hash, membrane, reservoir) that rebuilds the OCC region deterministically, rather than a BRep blob. Stage 6: MSH 4.1 | §5.3.2. Reusing `RadialGrid` and the profile schema keeps one reader per artefact. A region record hashes by content, where a BRep's bytes need not be stable |
| Model frame | z = 0 at the membrane centre. The structure maps to the model frame by the FR-02 axis plus `geometry.membrane.centre_z_nm`, a v2 key in the structure's own frame, measured along the axis. Its default, 0, is the OPM convention for membrane-protein coordinate files | Closes gap G9 generically. ClyA's own value is the author's to give (open decision G9) |
| Membrane inner edge | Derived, not configured, and gated to lie strictly inside the body. The reference fixture keeps its (2.0, 3.5) corners. **Superseded in part by the [WP21 plan](wp21-cad-assembly-and-meshing.md), D3, 26 September 2026:** the chord is the widest-margin one between the lumen-adjacent body intervals on `z = ±t/2`, not the chord between their mid-points. That chord crosses the cleft under the cap on the reference fixture and on 2WCD, and splits the electrolyte in two (WP21 Design §1) | §5.2.1 NOTE: the assembled membrane is the quadrilateral minus the body, so any edge strictly inside the body yields the same region. A configurable edge would be a knob with no effect when right and a gap or overlap when wrong |
| Structure preparation | Out of scope. The pipeline consumes a prepared structure and records `structure.source.variant` and the chain set (OPN-04) | FR-01 says ingest, not prepare. PDBFixer brings OpenMM onto the end-user path for a step the author performed by hand in the source work |
| Nothing is tuned to the target | The isolevel (0.25) and the density sharpness (0.93) stay case values cited to `.knowledge/04` §1. The isolevel sensitivity is recorded, never fitted to VAL-05 | Gap G2: the 25 % level is unjustified in the source, and radius enters conductance as r². Fitting it to the polygon would make VAL-05 pass by construction |
| Radius-profile check | In-project probe-radius profile on the aligned structure: the largest sphere centred on the known axis that clears every atom's van der Waals radius. `mdahole2` is an optional cross-check that skips when absent | B5. The axis is known from FR-02, so HOLE's axis search is not needed |
| Optional dependencies | MDAnalysis, scikit-image, Shapely and gridData are imported at the top of the stage implementation modules. Those modules are reached only through the lazy registry, and a missing `structure` extra is a named diagnostic when the stage is created. NumPy, NGSolve and Netgen stay deferred as today | The `CLAUDE.md` import rule. VER-25 introspection stays free of the pipeline's imports |
| Cₙ averaging method | Decided in WP19 with its derivation: rotate the atoms and deposit n copies, or rotate the voxel map by interpolation. The WP19 plan must show which one leaves the FR-06 variance statistic meaning what CON-04 says it means | A 30° trilinear rotation smooths the map, and the smoothing moves the reported variance |
| Memory and runtime | The 3D map is float32 at 0.05 nm (about 90 MB for the ClyA dodecamer). Deposition is vectorised over local stencils, truncated where the Gaussian falls below 10⁻⁶. The Tier-2 2WCD leg's runtime is measured and bounded in WP19 | FR-04's grid range. Tier 2 must stay at minutes (§7.1) |
| Mesher adapters | Netgen stays the default. Gmsh arrives behind the same adapter in WP23, under the `gmsh` extra, never imported on the default path | B7, ADR-002, CON-10 |

## Conventions established by Phase 1

Inherited, and not re-decided by any package below. Read each where it points.

- **The case document is the unit of reproducibility, and no stage reads YAML.** `io/case.py`
  resolves; a stage takes typed inputs. Unknown keys are refused, naming the key and its block
  (IF-03).
- **Every switch-typed field is classified**, in `SWITCH_PATHS` or `CONFIGURATION_PATHS`, in both
  directions (VER-24). A new geometry switch fails Tier 1 until it is classified.
- **Artefact keys are canonical hashes over validated payloads** (§5.3.2). A mesh is hashed over its
  canonical form, not its file bytes. The environment is recorded beside a key, never in it.
- **A stage is introspectable without importing its implementation** (VER-25), and cancellable
  through a `CancelToken`.
- **An ingested or generated mesh passes the VER-27 vocabulary gate and the VER-10 quality gate**,
  both SICN and gamma, with the worst element and its location reported (QR-12).
- **netgen.occ traps, all measured** (`.knowledge/07-software-stack.md` §4): a clockwise wire makes
  a negative face; `Glue` is conformal and `Compound` is not; an arc's `center` lies off the curve;
  a closed circle's seam survives a clip; netgen meshes are not bit-reproducible across platforms,
  so assert a band on element counts.
- **A documented command is executed verbatim by VER-46**, and no number appears in the docs as a
  result unless a test asserts it. The generated references pick up new case fields without a docs
  edit.
- **The desktop shell holds no physics**: view-models import no Qt, and the editor is generated from
  the schema (VER-43).

## Work packages

Each package gets its own `/wp-plan <n>` with a decisions table before implementation, and is green
on tiers 1 and 2 before the next starts. Verification identifiers from VER-47 on are **proposed**
here. Each package claims its identifiers and adds its Appendix A rows when it implements them.

### WP17 — Case schema v2 and the 3.11 floor

The one breaking change, taken first so that every later package builds on it (B3, B4). It moves
the schema to `nanopnp/case/v2`, carrying every key Phases 2 and 3 are foreseen to need: stage
hand substitution under `inputs:` (at least `profile`, the stage-4 output the GUI's hand edit
writes), `geometry.membrane.centre_z_nm`, and whatever the Phase 3 charge stage needs, such as a
supplied PQR. A v1 document upgrades losslessly. The WP17 plan decides whether the upgrade
preserves v1 artefact keys or deliberately moves them, and records the choice in §5.3.1. It raises
`requires-python` to 3.11, lifts the `structure` extra's floors to MDAnalysis 2.10 and
GridDataFormats 1.2, drops the 3.10 CI leg, and retires the IF-05 NOTE's conditional CCP4 writer.
Discharges IF-03, FR-26 and QR-09 as amended. Adds **VER-47**: a v1 document resolves to the same
run configuration as its v2 upgrade; every new key is classified; the VER-09, VER-24, VER-43 and
VER-45 walks cover the new paths in both directions.

> **Delivered, 24 September 2026** ([plan](wp17-case-schema-v2.md), tag `v0.9.0-alpha.1`). The
> schema is `nanopnp/case/v2` with the §5.3.1 key set, and a v1 file is read through
> `upgrade_v1`. The floor is Python 3.11, with MDAnalysis 2.10, GridDataFormats 1.2 and CCP4
> written everywhere. IF-03, FR-26, QR-09 and VER-47 are discharged, and VER-29 is amended. **The
> solve keys moved once:** the v1 key carried the schema string, so every stored solve re-solves
> once and the export contract's `case_hash` changed (author ruling; the §5.3.2 NOTE). Constraints
> inherited by later packages: `inputs.profile` and `inputs.pqr` are refused through
> `_UNCONSUMED_INPUTS` in `io/case.py` until WP21 and Phase 3 remove their entries. The two new
> charge floats are FR-25 switches with a validated default of 0. Any later key is a v3 move.

### WP18 — Structure ingestion, alignment and the Cₙ axis (stage 1)

MDAnalysis readers for PDB, mmCIF, DCD, XTC, TRR and NetCDF (IF-04), frame selection by
`last_ns` and `count`, and superposition of every frame on a reference frame's Cα set (FR-01). The
Cₙ axis comes from chain-permutation superposition, as the eigenvector of eigenvalue 1, and is
placed on z at r = 0 (FR-02; `.knowledge/07` §2 says why principal axes fail). The oligomeric state
is checked and a missing chain aborts (FR-03, QR-12). 2WCD is vendored as test data (B2). Stage 1
is registered and `run_case` runs it. Adds **VER-48**: a synthetic Cₙ assembly about a known,
tilted and offset axis recovers that axis to a stated angle, and a principal-axes estimate is shown
to fail on the same input; a missing chain and a wrong point group each abort naming what is
missing; each trajectory format reads; a rigidly moved frame superposes to zero RMSD.

> **Planned in detail, 25 September 2026** ([plan](wp18-structure-ingestion.md)). Two things
> differ from the paragraph above. mmCIF is read by gemmi, because MDAnalysis 2.10 has none
> (author ruling; §2.6 and CON-09 amended). The stage runs alone through `nanopnp stage
> structure`, and a full walk is refused naming stage 2 until WP19. The sign of the axis follows
> the file's +z, gated at 10° (author ruling). The §5.3.1 NOTE on `structure:` is the stage's
> contract.

> **Delivered, 25 September 2026** ([plan](wp18-structure-ingestion.md), to be tagged
> `v0.9.0-alpha.2`). Stage 1, `structure`, reads PDB, mmCIF (through gemmi) and the four trajectory
> formats. It superposes the selected frames and puts the permutation Cₙ axis on z at r = 0. It
> emits `nanopnp/structure/v1`, and the manifest records it. VER-48 discharges IF-04, FR-01, FR-02
> and FR-03, and adds to QR-12. The registry names a missing extra (`MissingExtraError`, FR-27).
> Constraints inherited by later packages:
>
> - A walk or sweep past stage 1 is refused naming stage 2, and WP19 lifts that through
>   `refuse_walk` in `io/case.py`.
> - `structure:` beside `inputs.mesh` is refused.
> - The deposited 2WCD is in its crystal frame, 22.9° from z, and stage 1 refuses it. **WP22's
>   Tier-2 VAL-05 leg needs it in an admitted frame**, as the stage-one test prepares it (the WP18
>   D16 Outcome; `.knowledge/04` §1.1).

### WP19 — Density map and symmetry reduction (stages 2 and 3)

The probabilistic-union density `ρ = 1 − Π(1 − exp(−d²/(σR_i)²))`, accumulated additively as
`Σ log(1 − g_i)` over local stencils (FR-04; `.knowledge/04` §1). Maps are averaged over frames in
3D, then over the n rotated copies, and only then azimuthally, by area-weighted binning over exact
annular volumes with the innermost bins interpolated (FR-05). Residual azimuthal variance is a
first-class output (FR-06, CON-04, RSK-07). Maps are written to OpenDX and CCP4 (IF-05, write
side). Adds **VER-49**: single- and two-atom closed forms of the union density; values stay in
[0, 1]; the stencil truncation is bounded. Adds **VER-50**: the annular weights sum to the exact
annulus volumes; the azimuthal average of an off-axis Gaussian matches its closed form
`exp(−(r² + r_i² + (z − z_i)²)/w²) · I₀(2 r r_i/w²)`; the variance is zero on an axisymmetric input
and matches its closed form on a `cos(nθ)` modulation.

> **Planned in detail, 25 September 2026** ([plan](wp19-density-and-reduction.md)). Four things
> differ from the paragraph above, and the §5.3.1 NOTE on `geometry.density` is now the contract.
>
> - **The radius set is CHARMM Rmin/2 from PDB2PQR's `CHARMM.DAT`.** This is an author ruling; it
>   is the set in the reference ensemble's PQR files.
> - **The Cₙ average is taken in the angular harmonic basis**, which closes the open decision
>   below: it is exact, and costs one deposition per frame.
> - **No bin is interpolated.** The overlap weights are exact.
> - **The variance is computed after subtracting the binned mean** at each cell's own radius. Without
>   that, the radial gradient reads as azimuthal variance.
>
> The stages are `density` and `symmetry`, and a walk past stage 3 is refused naming stage 4.

> **Delivered, 25 September 2026** ([plan](wp19-density-and-reduction.md), to be tagged
> `v0.9.0-alpha.3`). Stage 2, `density`, deposits each frame's probabilistic union on a canonical
> grid. The widths come from the CHARMM radius set in `data/radii/`, and the frame mean is emitted
> as `nanopnp/density/v1`, exportable to OpenDX and CCP4. Stage 3, `symmetry`, bins the map by
> exact overlap weights and takes the Cₙ average in the harmonic basis. It emits
> `nanopnp/reduced/v1`: the mean, the detrended Cₙ and raw variances, and the harmonic counts.
> VER-49 and VER-50 discharge FR-04, FR-06 and CON-04, and add to FR-05, IF-05 and QR-12. 2WCD
> runs stages 2–3 in 24 s. Constraints inherited by later packages:
>
> - A walk or sweep past stage 3 is refused naming stage 4, and WP20 lifts that through
>   `refuse_walk`.
> - `geometry:` beside `inputs.mesh` is refused.
> - Stage 4 reads `ReducedMap.grids()`. Below `n h/π` the variance is unresolved, not zero.
> - Phase 3's FR-13 reuses `symmetry/annular.py`.

### WP20 — Contour extraction, conditioning and its gate (stage 4)

Planned only after the author's contour script has been read (B6, RSK-06). What ports is taken, and
the §5.2.1 pipeline remains the fallback: sub-pixel marching squares at the isolevel, the longest
closed contour, Taubin smoothing, Douglas–Peucker simplification, and minimum vertex spacing. The
FR-08 gate covers validity, simplicity, spacing, local feature size (measured two edges either
side, `.knowledge/04` §4), loop topology, and the radius profile against the probe-radius profile
(B5). The output is `nanopnp/profile/v1` and is hand-substitutable through `inputs.profile`.
Discharges FR-07 and FR-08, and closes OPN-02. Adds **VER-51**: the contour of an analytic field
at a known isolevel is recovered; Taubin preserves enclosed area where plain Laplacian smoothing
visibly shrinks it, which makes the test discriminating; each gate criterion fires on constructed
input with its QR-12 diagnostic; the probe-radius profile of an analytic ring of atoms matches its
closed form.

> **Delivered, 26 September 2026** ([plan](wp20-contour-extraction.md), to be tagged
> `v0.9.0-alpha.4`). Stage 4, `contour`, runs marching squares on the reduced mean, placed by the
> grid's own axes. The region is closed and opened by 2h, then Taubin-smoothed at h/2, simplified
> and thinned to spacing h. The gate checks validity, topology, spacing ≥ h, feature size > 2h,
> and the radius band `[−h, +1.5 nm]` against the frame-mean probe radius. The stage emits
> `nanopnp/profile/v1` with `source: pipeline`. VER-51 discharges FR-08 and adds to FR-07, FR-27
> and QR-12. OPN-02 is closed and RSK-06 retired. 2WCD and the ClyA-AS ensemble both pass the gate
> (`.knowledge/04` §1.3). Constraints inherited by later packages:
>
> - A walk or sweep past stage 4 is refused naming stage 5, and WP21 lifts that through
>   `refuse_walk`.
> - The profile is in the stage-1 frame. Stage 5 applies `centre_z_nm` and reads `inputs.profile`.
> - Stage 4 guarantees spacing ≥ h and feature size > 2h. The wall-size question is WP21's.

### WP21 — CAD assembly and graded meshing from a profile (stages 5 and 6)

`ReferenceGeometry` generalises to any profile plus the membrane and reservoir specification: the
derived inner edge, the model-frame shift, and a junction gate that asserts the plane cuts land on
the body's own outer surface, read from the profile (FR-09). Size fields follow §5.2.2 and NUM-30,
with `numerics.mesh.wall_h_nm: auto` resolving to `λ_D/5` at the case's concentration (FR-10).
Stages 5 and 6 are registered, `_require_runnable` lifts, and `run_case` runs from structure to
solve without `inputs.mesh`. Retires RSK-05. Adds **VER-52**: three domains, one shared edge chain
at the junction, the membrane edge strictly inside the body, the §5.3.1 vocabulary, and the
reference fixture through the generic path reproducing VER-28's counts. Adds **VER-53**: the wall
size target is met on the wall, the VER-10 gates hold on generated meshes, and the default path
imports no gmsh.

> **Planned, 26 September 2026** ([plan](wp21-cad-assembly-and-meshing.md)). Two premises above
> changed on measurement. The membrane's inner edge is the widest-margin chord (D3), because the
> mid-point chord leaves the body. `auto` is `size_scale × min(0.05 nm, λ_D/5)` (D7), because
> NUM-30 read literally puts 0.27 nm on the wall at 0.05 M. A generated mesh is keyed on its
> recipe, and its content hash is recorded (D10).

### WP22 — VAL-05: the pipeline against the reference geometry

The phase gate, on both legs of B2. The 2WCD leg runs stages 1–6 in Tier 2 and is gated. The
ensemble leg reads `NANOPNP_REFERENCE_DATA`, runs at Tier 3, and skips visibly without the archive.
Both compare the radius profile and the constriction radius against the 185-vertex polygon over
`z ∈ [−1.85, 12.25]` nm. The axial registration uses the author's G9 value if given; otherwise it
is fitted as one reported degree of freedom. The WP22 plan states each leg's tolerance, argued from
`G ∝ r²` and the ±1 % conductance floor of `.knowledge/04` G3. Recorded, not gated: isolevel
sensitivity (G2), the FR-06 variance along z, element count and quality against the reference mesh
(§5.2.2), and the conductance of one frozen case on the generated mesh against the reference mesh.

### WP23 — The Gmsh mesher backend

The optional GPLv2+ backend of ADR-002 behind the WP21 adapter, selected by
`numerics.mesh.backend: gmsh` and installed by the `gmsh` extra (B7). The `gmsh` API is called
directly, never through pygmsh (CON-12). Adds **VER-54**: the same region meshed by both backends
passes the same VER-10 and VER-27 gates with the same vocabulary; the default path imports no
`gmsh`, asserted in a fresh process (CON-10); the tests skip without the extra.

### WP24 — GUI increment 2: the geometry pipeline surfaced

The §8.1 increment: load a structure, inspect the density, contour and mesh artefacts as each stage
produces them, and override the contour by hand. A hand edit writes a `nanopnp/profile/v1` artefact
substituted through `inputs.profile`, so it is recorded by content hash like any supplied input
(FR-27). The shell adds viewers and no physics (RSK-15). The packaging probe gains MDAnalysis,
scikit-image and Shapely, so the `bundle` job detects a packaging break on every push (RSK-13).
Adds **VER-55**, extending VER-43 and VER-44 to the new views, with the view-models importing no Qt.

### WP25 — Documentation increment 2

The §8.1 documentation increment: a guide to structure and trajectory input, density, symmetry
reduction, contour and meshing, and example `06-pdb-to-mesh` from the vendored 2WCD entry to a
gated mesh, executed verbatim by VER-46. Its oracle is a model property, not a transcribed number:
for example, the profile closes and passes its gate, and the reduced map is invariant under the
Cₙ rotation. The generated references pick up the v2 fields without a docs edit (VER-45).

## Open decisions

| # | Decision | Owner and status |
|---|---|---|
| G9 | The axial offset from the MD frame to the model frame for ClyA, which sets ClyA's `geometry.membrane.centre_z_nm` (`.knowledge/04` §8) | **Settled by the author, 25 September 2026: 0 in the MD frame**, which was centred on the middle of the bilayer. WP22 uses it for the ensemble leg and must register the vendored 2WCD to the MD frame. Superseded: **Author, open.** The archive has no lipids, so the bilayer cannot fix it. The MD frame's extent suggests ≈ 0 (`.knowledge/04` §1.1). Fallback: WP22 fits the offset as one degree of freedom and reports it |
| Ensemble delivery | Format, frame count, and whether lipids and waters are included in the archived ClyA-AS ensemble; the file names it carries under `NANOPNP_REFERENCE_DATA` | **Answered, 25 September 2026.** `prod5_clya_as.{pdb,dcd}`: 98 frames, protein with hydrogens, no lipids or waters. The DCD's frames are the archived PQRs 02–99 at 100 ps, in time order, so the paper's final-5-ns ensemble is DCD frames 48–97 (`.knowledge/04` §1.1) |
| VAL-05 tolerances | Radius-profile and constriction-radius tolerances per leg | WP22 plan, argued from `G ∝ r²` and gap G3 |
| Schema v2 contents | The exact v2 key list, including Phase 3's, and whether v1 artefact keys survive the upgrade | **Settled** in the [WP17 plan](wp17-case-schema-v2.md), D1–D6, and in the `SPECIFICATION.md` §5.3.1 v2 NOTE: the solve keys survive and the stage-9 key moves |
| Cₙ averaging method | Rotate atoms or interpolate the voxel map | **Settled** in the [WP19 plan](wp19-density-and-reduction.md), D7 and Design §2: neither. The average is taken in the angular harmonic basis, where it keeps the multiples of n. That is exact, and costs one deposition per frame. §5.2 and the §5.3.1 NOTE on `geometry.density` are amended |
| Contour script | Which parts of the author's script port | **Settled** in the [WP20 plan](wp20-contour-extraction.md), D2 and Design §1: the script is `pqr2grid`'s `create_polygon_contour` (2019). Marching squares and topology-preserving Douglas–Peucker port. Its index-to-radius map is an erratum and does not (`.knowledge/04` §1.2). OPN-02 closed, RSK-06 retired |

## Verification

Every package leaves `uv run pytest` green before the next starts (tiers 1 and 2), and the push gate
is unchanged:

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src/ && uv run pytest
uv run pytest -m tier3 -v                       # the VAL-05 ensemble leg: recorded, skips without the archive
uv run pytest -m slow --log-cli-level=INFO      # deposition and meshing budgets, measured
```

| Package | Tier | Identifiers |
|---|---|---|
| WP17 | 1 | VER-47, VER-09, VER-24, VER-43, VER-45 |
| WP18 | 1 | VER-48 |
| WP19 | 1, 2 | VER-49, VER-50 |
| WP20 | 1 | VER-51 |
| WP21 | 1, 2 | VER-52, VER-53, VER-10, VER-27, VER-28 |
| WP22 | 2 (2WCD), 3 (ensemble) | VAL-05 |
| WP23 | 1 (skips without the extra) | VER-54 |
| WP24 | 1 | VER-55 |
| WP25 | 1, 2 | VER-45, VER-46 |

The phase is complete when:

1. **Tiers 1 and 2 pass**, including every Phase 0 and Phase 1 gate, on a generated mesh as well as
   an ingested one.
2. **A case with `structure:` and `geometry:` and no `inputs.mesh` runs end to end** from the CLI,
   and its manifest records every stage's artefact hash.
3. **VAL-05 passes on the ensemble leg** within the tolerance WP22 states, and the 2WCD leg is gated
   on every push.
4. **The GUI increment** loads a structure, shows each geometry stage, and runs a hand-edited
   contour through to a mesh.
5. **Example 06** runs verbatim from a PDB entry to a mesh.

## End-of-phase report

To be written at the end of the phase, naming numbers rather than adjectives:

- VAL-05 on both legs: the maximum and RMS radius-profile deviation, the constriction radius
  against the polygon's, and the axial offset used, with its source (the author's value or a fit).
- The isolevel sensitivity: constriction radius and the conductance consequence at isolevels around
  0.25.
- The FR-06 residual azimuthal variance along z for ClyA, and where it is largest.
- The generated mesh against the reference figures (120,917 triangles, minimum quality 0.6378,
  average 0.9765), on both backends.
- The conductance of one frozen case on the generated mesh against the reference mesh.
- Deposition and meshing wall-clock times and peak memory for 2WCD and for the ensemble.
- Whether the desktop bundle still builds with the pipeline's dependencies in it.

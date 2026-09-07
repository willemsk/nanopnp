# Phase 1 (Solver core): the production solver on an externally supplied mesh

**Status: WP7, WP8, WP9 and WP10 delivered; WP11–WP12 planned.** Written 2 September 2026, after Phase 0
(WP1–WP6) and its consolidation (WP-A1, WP-B1, WP-B2, WP-C1). It inherited a verified physics core
and a bare pipeline: tiers 1 and 2 green, `mypy --strict` and `ruff` clean, and `io/`, `sweep/`,
`charge/`, `structure/`, `density/`, `symmetry/`, `gui/` still empty reserved slots. `io/` is filled
and `mesh/` is complete for ingestion as of WP8; `sweep/`, `charge/`, `structure/`, `density/`,
`symmetry/` and `gui/` are still empty.

This is the delivery plan for Phase 1 of `SPECIFICATION.md` §8.1 — release v0.5. The specification
remains normative: where this file and the specification disagree, the specification governs and
this file is wrong. Requirement identifiers here are pointers into it, never restatements of it.

## Context

Phase 0 answered "does the physics come out right?" against closed forms. Phase 1 answers a
different question: **can somebody other than the author run it, reproduce it, and compare it to
COMSOL?** The physics does not change. What changes is that the run stops being a Python script and
becomes an artefact chain — a case file in, a manifest and a dataset out, every stage separately
invocable — and that the solver stops meshing its own geometry and starts consuming one.

Four things are true of the codebase today that shape every package below.

- **The solver core exists and is verified.** `physics/`, `solve/`, `post/` and `materials/` carry
  VER-03 … VER-22. Nothing in Phase 1 should touch a weak form except WP12, which adds a
  *configuration* (stabilisation) rather than a term.
- **There is no serialisation layer at all.** The only serialisation boundary in the package is the
  correction file, which WP-B2 gave a typed pydantic schema. That schema is the template the case
  file copies, deliberately: it rejects an unknown key by naming it, which is exactly IF-03.
- **`mesh/` builds geometry; it cannot read one.** `mesh/primitives.py` constructs `netgen.occ`
  shapes and names their edges. Ingesting a mesh means inverting that: a file arrives carrying
  physical groups, and something must decide which group is the no-flux wall and which is the open
  boundary. That decision is where a silently wrong answer enters this phase.
- **The gate the phase must clear is `Tier 1 and Tier 2 pass; Tier 3 enabled and differences
  attributed`.** Attribution, not agreement — §7.4 makes agreement conditional on the stabilised
  mode existing and the meshes being convergence-matched, and Phase 1 is where both preconditions
  are built.

Risks this phase is scheduled to retire or move: **RSK-13** (desktop packaging defeated by a binary
dependency, open since amendment A2 deferred Phase-0 criterion 4), **RSK-14** (COMSOL licence lapses
before the reference set is archived — the author has confirmed access, so VAL-03 is live work this
phase), and **RSK-09** (the reference carries no mesh convergence study, so a Tier-3 discrepancy may
originate in the reference; VAL-04 bounds it while the licence lasts). **RSK-15** (GUI scope drawing
effort from validation) becomes live for the first time: WP14 is the largest single package here.

Deliberately excluded: the structure → density → contour → CAD pipeline (Phase 2), the PDB2PQR
charge pipeline (Phase 3), and everything tagged v1.0 or post-1.0 in §3.2. Phase 1 *consumes*
meshes and charge fields; it does not produce them.

## Decisions taken before implementation

Everything an implementer would otherwise settle at 2 a.m., settled here.

| Decision | Choice | Why |
|---|---|---|
| Case-file layering | `io/case.py` holds pydantic models mirroring §5.3.1 verbatim; `resolve()` turns a validated case into the Phase-0 objects (`Electrolyte`, `CoupledModel`, `Rung` ladder, `CoupledBoundaries`, `Measures`). **No stage ever reads YAML.** | Keeps IF-03 in one file and leaves every stage callable from Python with typed arguments (IF-01). A stage that parses its own config cannot be driven by the GUI without re-parsing. |
| Unknown keys | `extra="forbid"` on every model, and the error message names the key and its path (`electrolyte.corrections.diffusivty`) | IF-03 requires the diagnostic to name the key. WP-B2's `CorrectionDocument` established the pattern; copying it is cheaper than inventing a second one. |
| Round-trip semantics (FR-26, VER-09) | Semantic identity is asserted on the **resolved objects' provenance**, not on YAML text | A YAML text comparison passes on a file that resolves to a different run (comment loss, key order, `1.0` vs `1`), and fails on one that resolves identically. The provenance dict is what FR-25 already declares to be the run's identity. |
| Artefact identity | `sha256` over canonical JSON: sorted keys, floats emitted as `float.hex()`, arrays hashed as their C-contiguous bytes plus dtype and shape, prefixed by the artefact's schema name and the hashes of its inputs | Content hash is the cache key (§5.3.2), so it must be stable across platforms and Python versions. `repr()` of a float is round-trip exact but formatting has changed between versions; `float.hex()` has not. |
| Mesh hash | Over vertices, elements and tag maps in file order — **not** over the file bytes | A mesh rewritten by meshio with a different header is the same mesh; a mesh whose `wall` group gained an edge is not. Hashing bytes gets both cases wrong. |
| Manifest assembly | `io/manifest.py` collects component `.provenance` / `.summary` dicts; the *Deviations* group is computed by diffing the resolved case against the canonical validated-default case | §5.3.3 requires "every switch set away from the validated default". Computing the diff means a switch added in a later phase is recorded without anybody remembering to extend the manifest writer — the failure mode WP-B1 found for the stabilisation mode. |
| Mesh vocabulary | Materials `electrolyte`/`cis`/`trans`, `membrane`, `pore`, `analyte`; boundaries `axis`, `wall`, `cis`, `trans`, `membrane_outer`. An ingested mesh carries an explicit group→name mapping in the case file | The names the solver already speaks (`mesh/primitives.py`, `DEFAULT_BOUNDARIES`, the `ELECTROLYTE_DOMAINS` regex). Everything downstream keeps working unchanged. |
| Unmapped groups | Ingestion **aborts**, naming every unmapped group and every required name that no group supplies (QR-12) | An unmapped boundary silently becomes a natural condition: a no-flux wall turns into an open boundary and the current is wrong with no diagnostic. This is the single highest-value gate in the phase. |
| Quality metric | SICN and gamma computed in project code from vertex coordinates, gate `min > 0.3`, worst element reported with its centroid and metric value; an *optional* Tier-1 test cross-checks our values against `gmsh.model.mesh.getElementQualities` and skips when the GPL extra is absent | Reverses the WP-B3 deferral on the ground that made it: the threshold is only meaningful against the measure it was calibrated for, so we implement the measure *and* calibrate it, rather than inventing a metric or linking gmsh on the default path (CON-10). Derivation in §Design. |
| External charge/dielectric fields | One typed `FieldArtefact` with two admissible sources — a named analytic expression, or a gridded (r, z) table with documented interpolation — plus an OpenDX/CCP4 reader behind the `structure` extra (IF-05, import inside the function) | "Externally supplied material and charge fields" is the v0.5 release text. Reading is the consumer side and belongs here; *writing* those grids belongs with the producers in Phases 2–3. |
| Conservation on ingest | If the artefact declares `Q_net`, assert `\|∫ρ 2πr dr dz − Q_net\|/\|Q_net\| < 10⁻³` on the deployed mesh and abort on failure. If it does not, **record that the check could not run** in the manifest | QR-03 / PHY-19's mesh half. Silently skipping an assertion because its reference is absent is how a conservation failure reaches a published number. The per-z-slice check against a sorted PQR (VER-02) needs the charge pipeline and stays Phase 3. |
| Stage protocol | `core/stages.py`: `run(inputs, *, progress=None, cancel=None) -> Artefact`. Cancellation is **cooperative**, checked between Newton iterations (the existing `damped_newton` callback) and between rungs — never mid-factorisation | FR-27 asks for cancellable and progress-reporting. A cancel that must interrupt a UMFPACK factorisation means a subprocess and a kill signal; a cancel between iterations is a boolean. The GUI runs the solver in a background process anyway (ADR-004), so a hard kill remains available above this layer. |
| Sweep dispatch | A sweep is a base case plus substitutions on dotted schema paths, validated against the schema so a typo names the key. The runner writes an index file; `nanopnp sweep run --index i` executes one point, which is what a SLURM/PBS array calls. Local execution is `multiprocessing` over the same entry point | FR-24 says "dispatch the points as independent jobs" and QR-06 wants linear scaling in independent workers. Depending on a scheduler library would put a scheduler on the end-user path (CON-07); an index file and an integer do not. |
| Warm-start ordering | Points sorted by concentration then by \|bias\|, each warm-started from its converged predecessor's stored solution artefact; a point whose predecessor failed falls back to the full ladder and records that it did | NUM-18's ladder is the cold path and it is expensive; §8.3's 3,675-solve datum is only reachable warm. Recording the fallback is what keeps a sweep's timings interpretable. |
| Field IO | XDMF + HDF5 for fields (IF-07) via meshio, plus a solver-native round-trip of the raw coefficient vector for warm starts | XDMF is the archival, viewer-readable format; a warm start needs the exact vector on the exact space, and interpolating through XDMF would perturb a converged state. Two formats, two purposes, both hashed. |
| Stabilisation | `stabilisation: none | reference` resolving through a registry, exactly as corrections do; `none` stays the production default (NUM-11) | PHY-22's rule generalised: "off" is a named model, not a code branch. `CoupledModel.stabilisation` and its `SUPPORTED_STABILISATIONS` gate already exist from WP-B1 and were built for this. |
| Tier-3 comparison surface | Our probe grid, shipped with the frozen case; COMSOL interpolates onto it. Goldens are `.npz` with a manifest naming the model file, COMSOL version, export date and the case hash | §7.4 asks for "a common probe grid". Making it *ours* means the comparison does not depend on COMSOL's mesh, and re-exporting later cannot silently move the sample points. |
| Attribution, not agreement | WP13's report decomposes any discrepancy by re-running our solver in the matching configuration: unstabilised P2/P1 → stabilised P2/P1 → stabilised P1/P1, each against the same golden, and reports the three deltas | The phase gate is "differences attributed". A single number against a golden attributes nothing; three deltas say how much of it is the stabilisation, how much the element pair, and how much is left over. Left-over is the only part that can be a defect. |
| GUI construction | The case editor is **generated from the pydantic schema**, not hand-laid-out; the field viewer is `webgui` in a `QWebEngineView`; the solver runs in a background process and reports through the existing `damped_newton` callback | QR-11 demands a graphical surface at every release from v0.5 onward, so the editor has to survive schema changes without GUI work. Generating it is what makes that true. RSK-15 is managed by keeping the GUI a shell with no physics in it (IF-09, ADR-004). |
| Bundle linear solver | UMFPACK, with the GPL-2+ obligation accepted and stated (**CON-11 amended in this commit**) | The §6.6 measurement: SuperLU was OOM-killed on the reference-sized factorisation. A bundle that cannot run the published case is not a product. The library itself stays BSD-3 and depends on neither. |

## Design

The derivations the packages above lean on, written out.

### Element quality: what the 0.3 threshold means

VER-10 and §5.2.2 gate on `min SICN/gamma > 0.3`. Both are gmsh's names, and the Phase-0
consolidation deferred the gate because netgen exposes no per-element quality and inventing a metric
makes the threshold a property of the metric rather than of the mesh. Both measures are, however,
defined quantities computable from the vertex coordinates alone, and Phase 1 ingests meshes from
outside — which is precisely when a quality gate earns its keep.

For a straight-sided triangle with vertices `p₀, p₁, p₂`, let `A = [p₁ − p₀, p₂ − p₀]` be the
Jacobian of the affine map from the *unit* triangle, and let `E` be the same matrix for the
equilateral reference triangle of unit edge, `E = [[1, ½], [0, √3/2]]`. The Jacobian relative to the
equilateral reference is `J = A E⁻¹`, and

```
SICN = sign(det J) · 2 / κ_F(J) ,    κ_F(J) = ‖J‖_F ‖J⁻¹‖_F
```

For any real 2 × 2 matrix `κ_F ≥ 2`, with equality iff `J` is a scaled rotation — that is, iff the
element is equilateral — so `SICN ∈ [−1, 1]` with 1 exactly on the equilateral element and a
negative value on an inverted one. The companion measure is the normalised inradius-to-circumradius
ratio `gamma = 2 r_in / R_circ`, which is likewise 1 on the equilateral element (`R = 2r`) and 0 on a
degenerate one.

The threshold is inherited, not derived, so it must be calibrated against the implementation that
set it: a Tier-1 test compares our per-element values against
`gmsh.model.mesh.getElementQualities(..., "minSICN")` on a mesh carrying a deliberate sliver, and
skips when the optional GPL extra is not installed. That satisfies both halves of the Phase-0
objection — the measure is the one the threshold was calibrated for, and the default path never
imports gmsh (CON-10, ADR-002).

Reference figures the gate is checked against, from the COMSOL model report: minimum element quality
0.6378, average 0.9765 on 120,917 triangles (§5.2.2, VER-10).

### Why mesh ingestion is where a wrong answer enters

The solver's boundary conditions are selected by *name*: `DEFAULT_BOUNDARIES` maps `cis`/`trans` to
Dirichlet φ and `c_bulk`, `wall` to no-slip, and everything unnamed falls through to the natural
condition. Under the `r`-weighted axisymmetric forms the natural condition is `n·J_i = 0` and
`n·D = 0` on the axis (NUM-06) — which is *correct* on the axis and *silently wrong* on a mismatched
wall, where it turns a no-flux protein surface into a free boundary. There is no residual, no gate
and no diagnostic for that error: the solve converges and the current is wrong by whatever leaks.

Hence the ingestion rule above: the mapping is explicit in the case file, every group must be
claimed, every required name must be supplied, and the abort names both sides of the mismatch. The
test that matters is the negative one — a mesh whose `wall` group is misspelt must abort, not solve.

### The Tier-3 attribution ladder

§7.4 forbids gating until the stabilised mode exists and the meshes are convergence-matched, and
`.knowledge/09` §F lists what can never be matched: COMSOL's stabilisation operators are not
exported, "approximate residual" is internal, the element sets differ, and the reference's own
discretisation error is unquantified (RSK-09). So the deliverable is a decomposition:

```
Δ_total = [ our unstabilised P2/P1 ]      → the number Phase 0 would have produced
Δ_stab  = [ our stabilised   P2/P1 ]      → how much of Δ_total the stabilisation accounts for
Δ_pair  = [ our stabilised   P1/P1 ]      → how much the equal-order flow pair accounts for
Δ_resid = golden − stabilised P1/P1       → the unattributed remainder
```

`Δ_resid` is the only quantity that can indicate a defect, and VAL-04 (the reference re-solved at two
refinement levels while the licence lasts) is what bounds the part of it that belongs to the
reference rather than to us. The phase reports all four for every frozen case; §7.4's 1 % / 0.5 %
targets apply to `Δ_resid` alone and only once both preconditions hold.

### What the stabilised mode must not do

NUM-14's mode is for comparison, never for production (NUM-11: SUPG biases the current QoI and
destroys Jacobian symmetry). Two properties are asserted rather than assumed:

- **Consistency.** SUPG is residual-based, so the manufactured solution of VER-18 must still
  converge in the stabilised mode. The *rate* is measured and reported rather than predicted — the
  crosswind term is not a Galerkin-consistent perturbation in the same sense, and asserting an
  unmeasured order would be asserting something untrue.
- **Vanishing difference.** The stabilised and unstabilised currents on the same case must approach
  each other under refinement, at a measured rate. This is the quantitative form of `.knowledge/09`
  §F's "irreducible systematic bounded only by mesh refinement", and it is what licenses the
  attribution ladder above.

NUM-15 fixes the quadrature: crosswind at integration order 6, streamline at 4 — both above the
NUM-07 floor, and both requested through `Measures` rather than by passing `bonus_intorder` behind
its guarantee.

## Conventions established by Phase 0

Carried into every package below; they are recorded in `docs/plans/phase-0-spike.md` in full.

- `ngsolve`, `netgen` and `numpy` are imported **inside the function that uses them**; everything
  else at module scope. The CLI, the GUI and the sweep runner exist to introspect stages without
  assembling anything, and a job array pays that import cost per process — which is why the rule
  matters more in this phase than it did in Phase 0.
- `physics/measures.Measures` is the only route to an integration measure, and it owns the NUM-07
  order guarantee. New integrals in `post/` or `validation/` go through it.
- `materials/models.py` is the registry template: `register` / `registered_models` / `create`, with
  `none` a registered model rather than a code branch. The stabilisation registry follows it.
- A configuration that names itself must *be* itself: `Electrolyte.with_switches` rebuilds the
  resolved correction models because `replace(...)` once produced an object that reported PNP-NS and
  evaluated ePNP-NS. Any Phase-1 code that derives a variant case must go through the same discipline
  — the sweep runner is the obvious place to repeat that mistake.
- A converged solution carries the residual form it solves and the discrete wall-distance field it
  was assembled with. Warm-start serialisation must carry both; a residual reassembled against a
  freshly solved distance field is a *different operator*.
- The `2π` is restored once, in `post/qoi.py`. Nothing in `io/`, `sweep/` or `gui/` may re-apply it.
- Tests are named for the requirement they discharge, and the tier is decided by the directory.

## Work packages

One PR per package, green on tiers 1 and 2 before the next starts. WP7 first because everything else
produces or consumes artefacts; WP8 before WP13 because the comparison needs the reference geometry;
WP12 before WP13 because attribution needs the stabilised mode.

### WP7 — Case-file schema, artefacts, provenance manifest — **delivered**

`io/case.py`, `io/artefact.py`, `io/manifest.py`, `io/store.py`, `io/defaults.py`, `core/hashing.py`,
`core/stages.py`, and — beyond the plan — `materials/stage.py`, `solve/stage.py`, with changes to
`solve/continuation.py`, `physics/models.py` and `core/paths.py`; spec amendments adding VER-23 …
VER-26 and six Appendix A rows.

Delivered: the `nanopnp/case/v1` schema of §5.3.1 as pydantic models with `extra="forbid"`
everywhere, rejecting an unknown key by naming the key *and* the block it appeared in, and refusing
a v0.9 section (`structure:`, `geometry:`, `charge:`) with `UnsupportedCaseSection` rather than
ignoring it; `resolve()` onto the Phase-0 electrolyte, model and solver objects, going through the
WP1 resolution discipline rather than `replace(...)`; the content-addressed artefact base of §5.3.2
with one canonical digest over schema, parameters and input hashes; the result store with
`get_or_compute`, hit/miss counters and payload-file hashes; the §5.3.3 manifest writer with all
eight groups always present and the Deviations group computed by diff against an explicit
validated-default case document; and the `Stage` protocol of FR-27 with a registry, progress
reporting and cooperative cancellation. Discharges **IF-03, IF-08, FR-25, FR-26, FR-27, VER-09**,
adds **VER-23, VER-24, VER-25, VER-26**, begins **IF-01**, and carries **QR-08** in part. The schema
is frozen: from here on a change to it is a schema version, not an edit.

Beyond the plan, two stages exist because the manifest and the cache had to be tested against a real
run rather than a fixture: `materials/stage.py` (stage 8) and `solve/stage.py` (stage 10), the latter
with a public `key(inputs)` beside `run(inputs)` so the key the store is asked about and the key the
solve produces are built by one code path (`_prepare`). `solve/continuation.py` gained an `on_rung`
hook and a `Cancelled` clause; `physics/models.py` gained its own deviation enumeration.

Six things settled by the work that WP8 onwards inherit.

- **The validated default is a document, not a `model_dump(exclude_defaults=True)`.** The schema's
  `CorrectionChoiceSpec.model` defaults to `none` — the *classical* configuration — so a default-diff
  reports validated ePNP-NS as nine deviations and classical PNP-NS as none, exactly backwards.
  `io/defaults.py` spells the PHY-21/PHY-22 configuration out as a case document and diffs against
  it along an enumerated list of dotted paths.
- **Every switch-typed field must be classified, in both directions.** `SWITCH_PATHS` (31 paths) and
  `CONFIGURATION_PATHS` (9, each with a written reason) partition the schema's switches, and the
  Tier-1 test walks the schema tree *and* the two lists, so a switch added later without a validated
  default fails Tier 1 rather than vanishing from the manifest, and a path left behind by a renamed
  field fails too. That reverse walk is what found three wrong rows in the plan's own table.
- **A stage must be introspectable without importing its implementation.** `core/stages.py` carries
  the name, number, inputs, outputs and artefact schema in the registry, asserted in a subprocess on
  `sys.modules`: describing all three stages imports neither `ngsolve` nor the stage modules. That is
  what FR-27 buys the CLI, the GUI and the sweep runner, and it is why the deferred-import rule is
  not negotiable.
- **An electrostatic rung rejects a Newton callback.** `ElectrostaticModel.solve` ends in
  `_reject_unknown(kwargs, ...)`, so passing `callback=` down the ladder aborts on stages 1–2.
  Cancellation therefore hangs off `run_ladder`'s `on_rung` hook for the between-rungs granularity
  and off the Newton callback only for coupled rungs.
- **`default_ladder` had two manifest-integrity bugs, both found by writing the manifest.** It
  re-enabled corrections the case had switched off when resolving the canonical models, and it
  ignored `boundary_conditions.ground`. A manifest is only evidence if the thing it describes is the
  thing that ran.
- **Netgen `.vol` round-trips boundary and material names [tested]**, so a mesh can enter the digest
  as a file hash rather than a path; a payload file edited on disk loads as `hand_substituted`
  rather than aborting, which FR-27 requires.
- **The NUM-18 ladder reads none of the four physics switches from the case, and `resolve()` now
  refuses the combination.** `default_ladder` builds its own rungs: it passes `flow` explicitly (off
  for the early rungs, on from stage 6) and leaves `variable_density`, `inertia` and
  `dielectric_gradient_forces` at the `CoupledModel` defaults, so a case setting any of them and
  still selecting the ladder converged while the FR-25 Deviations group recorded a deviation the
  solve never carried. `physics.model: pnp` was the worse case — the ladder would have solved
  `pnp-ns` under a manifest naming `pnp`. Found by the WP7 review pass, not by the implementation.
  §6.5 gains a NOTE making the ladder's fixed path normative, and single-rung runs
  (`continuation: none`) remain the way an ablation asks for a configuration the ladder cannot
  express. Threading the switches into the ladder is solver-numerics work with its own verification
  burden and is deliberately not attempted here.
- **`numerics.stabilisation` is safe from the same trap only because `SUPPORTED_STABILISATIONS` is
  `{"none"}`.** The ladder does not pass `stabilisation` to its rungs either; the schema refuses
  anything but `none` this phase, so nothing is silently dropped today. WP12 adds the reference mode
  and must thread it through `default_ladder` in the same package, or inherit this bug.

Reference measurement, stabilisation `none`: `CylindricalPoreGeometry(pore_radius_nm=2.0,
membrane_thickness_nm=6.0, reservoir_radius_nm=10.0)` at `maxh_nm=4.0`, `wall_h_nm=1.0` → 124
elements, 75 vertices; 0.1 M, 20 mV, `epnp-ns`, `default_ladder` → 12 rungs over stages
[1, 2, 3, 5, 6, 7, 8, 9] (stage 4 empty — Phase 1 is uncharged), 36 Newton iterations, minimum
damping 0.2, ≈ 0.7 s.

### WP8 — Mesh ingestion, tagging, quality gates, reference geometry — **delivered**

`mesh/adapter.py`, `mesh/ingest.py`, `mesh/quality.py`, `mesh/profile.py`, `mesh/reference.py`,
`data/geometry/` (the delivered 185-vertex ClyA table, its README and the fixture derived from it),
with changes to `mesh/primitives.py`, `mesh/distance.py`, `solve/stage.py`, `core/stages.py`,
`core/paths.py` and `io/manifest.py`; spec amendments A–G adding VER-27 and VER-28, the `protein`
and `interface` vocabulary names, and the corrected 190/196 vertex composition.

Delivered: `MeshData` as the mesher-adapter seam of §5.1 — vertices, triangles with a material
index, edge blocks with a boundary index, both name tables and a content hash taken over a
canonical form, because a 4.1 round trip permutes nodes and cells and a byte-identical mesh would
otherwise hash differently twice; MSH 4.1 read and write through meshio with one cell block per
(group, element type) and a node-ownership rule that guarantees every entity owns a node, the two
constructions meshio's writer needs to stop failing silently; MSH 2.2 as the archival format netgen
can still read; `to_ngsolve`/`from_ngsolve` identity on the tag maps; the group → vocabulary mapping
with the reversed-map, unclaimed-group and unsupplied-name diagnostics, each naming both sides; the
SICN and gamma gates at `QUALITY_FLOOR = 0.3` with worst-element index, `(r, z)` centroid and both
metrics in the message, inverted elements reported under their own name; `MeshStage` as stage 6 with
`key(inputs)` beside `run(inputs)`; the `PoreProfile` fixture and its one-way derivation from the
delivered CSV, re-checked against the file in the tree; and `ReferenceGeometry`, which assembles the
ClyA region — the 185-vertex profile, the slanted-edge membrane quadrilateral, the 250 nm reservoir
half-disc — names every edge into the vocabulary and meshes it at the §5.2.2 size fields. Discharges
**IF-06, VER-10, QR-12**, adds **VER-27** and **VER-28**, re-verifies **VER-06** and **NUM-31** on
an ingested mesh, carries the CAD half of **FR-09**, and lands the §5.2.1 regression fixture.

Beyond the plan: `interface` joins the boundary vocabulary beside amendment G's `protein`, because a
fragmented region carries interior fluid-to-fluid and solid-to-solid seams that nothing selects on;
`required_names` reads `wall_distance.sources` and the flow model as well as the boundary
selections, so a case widening either aborts at ingestion rather than at form assembly;
`check_solid_permittivities` turns `models.py`'s warning into an abort on an ingested mesh (PHY-03);
`MeshData._snap_to_axis` snaps `|r| < 10⁻⁹` nm to zero on every route in; `mesh/primitives.py`
routes all three Phase-0 geometries through the gate with a keyword-only `check_quality`;
`io/manifest.py`'s `geometry_and_mesh` group gains the quality statistics, the mapping actually
applied and the fixture's provenance; and `solve/stage.py` now takes its mesh from the ingestion
artefact's content hash rather than a file hash, so a mesh rewritten with a different header is a
store hit and a mesh with one edge moved to another group is a miss.

Reference measurement, stabilisation `none`: the ClyA region at §5.2.2's size fields (global 10 nm,
pore boundary 0.05 nm, pore domain 0.1 nm, reservoir domain 2.8 nm, reservoir arc 5 nm, axis-in-pore
0.075 nm), `grading = 0.2`, `optsteps2d = 5` → **44,316 triangles in 6.5 s, minimum SICN 0.6559,
mean 0.9870, minimum gamma 0.6157, mean 0.9852**, no inverted elements, against COMSOL's 120,917
triangles at minimum quality 0.6378 and average 0.9765 — a third of the elements in the same band,
by isotropic grading alone. The gate costs ≈1.1 s on a 121k-element mesh.

Six things settled by the work that WP9 onwards inherit.

- **An unmapped boundary is silent, and that is the whole argument for the ingestion gate.** Under
  the `r`-weighted forms the natural condition is the free one (NUM-06), so a wall no name claims is
  an open boundary that raises nothing and converges. Every file group must be claimed and every
  name the resolved case selects on must be supplied, or the run aborts naming both lists.
- **A fragmented region has seams, and they need a name.** Without `interface`, an ingested
  fragmented mesh either fails the gate or has its seams mapped onto a boundary that *is* selected
  on — the failure the gate exists to prevent, arriving through the gate itself.
- **The quality gate is cheap and unconditional, and it found a degenerate mesh on its first run.**
  VER-16's Gouy–Chapman slab is 2000 nm × 0.5 nm at `maxh = 50 nm`: a chain of 100:1 triangles at
  minimum SICN 0.019. The anisotropy is deliberate — the stretched direction is the one the solution
  is constant in — so the exemption is one keyword-only `check_quality=False` at that call site with
  its reasoning beside it, and the floor is untouched. A gate is only worth having if the answer to
  a failure is a reason, not a lower number.
- **SICN and gamma are both gated because neither subsumes the other.** Gamma is blind to inversion
  (it returns +1 on a clockwise element, where SICN returns −1), and the two thresholds differ by a
  factor of **1.6208** in element height on the isoceles family — not the 1.56 the plan and §5.2.2
  carried, both corrected. In an axisymmetric mesh the sign is load-bearing: a negative-Jacobian
  element contributes negative area under the `r` weight and nothing else complains.
- **The kernel adds vertices the geometry does not.** The assembled reference region has 193
  vertices and 195 edges against the 190/192 §5.2.1 derives: two of each from breaking the axis into
  three collinear segments, so that the 0.075 nm axis-in-pore size can be applied at all, and one of
  each from the seam OCC places at parameter zero on a closed circle, at `(250, 0)`, which halves
  `membrane_outer` into two arcs. Both are asserted rather than tolerated (VER-28).
- **The membrane's inner edge is buried in the pore body**, so the assembled membrane is the
  quadrilateral *minus* the pore and there is nothing to make coincide: the junction gate asserts
  `r_out(−1.4) = 2.7524` and `r_out(+1.4) = 4.88` on the pore's own outer surface, one shared edge
  chain rather than two coincident ones, and exactly three domains — the cleft under the cap must
  not fragment off as a fourth.

**OPN-05 is closed.** §2.2's "196-vertex pore polygon" was the geometry-wide count attached to
the wrong object; the model report's 190 for the polygon and 196/198 for the assembly both stand,
and the delivered table's 185 assembles consistently to 190/192 by the same arithmetic. The author
settled the remaining question on 5 September 2026: **the delivered 185-vertex table is the geometry
of record** — what the fixture ships, what `mesh/reference.py` assembles, and what VAL-05 and any
Tier-3 comparison cite. The report's 190 is the count after COMSOL's import conditioning and the
five vertices are not chased. The fixture's `source: author-supplied` and `REFERENCE_SOURCES` were
already written for this answer, so nothing in the code moves.

### WP9 — External material and charge fields — **delivered**

`density/grid.py`, `charge/fields.py`, `charge/stage.py`, `materials/fields.py`, with changes to
`core/paths.py`, `core/stages.py`, `io/artefact.py`, `io/case.py`, `io/defaults.py`,
`io/manifest.py`, `mesh/ingest.py`, `mesh/primitives.py`, `physics/models.py`, `physics/pb.py`,
`solve/continuation.py` and `solve/stage.py`; spec amendments A–H from the plan commit, plus five
that implementation forced (§7.1's reference archive, §5.3.1's `comsolgrid` format, §4.4's NOTE on
the consumer leg, VAL-15 in §7.4, and §3.1's NOTE narrowing IF-05's CCP4 *write* side to the
interpreters whose GridDataFormats carries the writer).

Delivered: `RadialGrid` as the seam behind every gridded field — origin, uniform spacing checked to
`10⁻⁹` nm, `values[i_z, i_r]` float64, planar integral, ramped cumulative, boundary-ring maximum,
zero padding and a content hash — read and written over `.npz` natively, OpenDX and MRC behind the
`structure` extra with `writable_formats()` reporting which of them this install can actually write,
and the reference model's own `%Grid`/`%Data` table read-only; `FieldDocument`
(`nanopnp/field/v1`, `extra="forbid"`) carrying quantity, units, grid descriptor, axis cutoff,
declared `Q_net` and provenance, with an absolute `ε_r` refused naming PHY-11; the named analytic
form registry (`uniform`, `gaussian_ring`, `slab`); `ChargeField.assemble` applying the `1/(2πr)`
projection and PHY-18's axis guard to `areal_charge_density` alone; `conservation` and
`check_conservation` reporting the producer and consumer legs separately with the quadrature
agreement, ring ratio, guard deficit and worst ramped plane beside them; `SolidFractionField` and
the §4.4 blend with its range and per-material-mean gates; `FieldStage` as stage 7 over
`("case", "mesh")` with `key(inputs)` beside `run(inputs)`; the `exclusion` material, exempt from
`check_solid_permittivities` and contributed to the manifest as a deviation through a new
stage-contributed channel; `default_ladder(..., fixed_charge_field=…)` on the stage-4 ramp; and the
manifest's `charge` group populated from the conservation report. Discharges the consumer halves of
**FR-14**, **FR-15**, **QR-03**, **PHY-18** and **PHY-19**, the read side of **IF-05**, and adds
**VER-29**, **VER-30**, **VER-31** and **VAL-15**. VER-01's producer side and VER-02 stay Phase 3.

Beyond the plan: the `comsolgrid` reader, once the author delivered the real table; `core/paths.py`
gained `reference_data_root()`/`reference_file()` over `$NANOPNP_REFERENCE_DATA`, because that table
is 77 MB and no reduction of it is a fair reference — a `10⁻⁶`-threshold crop still costs 28 MB and
subsampling by four moves the planar integral by 1.5 %, fifteen times the budget it would check; and
a Tier-3 file that skips rather than fails where the archive is absent.

Reference measurements, stabilisation `none`, on the WP8 reference mesh (44,316 elements, §5.2.2
size fields, 7.4 s to generate, 1.6 s to check):

| Field | `Q_grid` vs `Q_net` | `Q_mesh` vs `Q_grid` | Quadrature agreement | Worst ramped plane |
|---|---|---|---|---|
| Gaussian rings on the contour, `w = 0.085 nm` (VER-29, Tier 2) | 0.0 | **1.37e-05** | 2.13e-05 | 1.37e-05 |
| The delivered `prod5_clya_charge` (VAL-15, Tier 3) | 4.68e-12 | **9.87e-03** | 9.27e-03 | 2.03e-02 |

The two rows are the package's most useful result, and they are the same mesh. QR-03's `10⁻³` is
met with a factor of 73 to spare on a field smeared at the reference's own width; it is missed by a
factor of ten on the reference's own table. VER-31: the Stern shell raises the wall potential from
51.3852 mV to 67.1139 mV, a ratio of **1.30606** against the closed form to `10⁻⁵`, and `λ_S = 0`
returns `ζ̃ = 2` to `10⁻³` on the same mesh.

Seven things settled by the work that WP10 onwards inherit.

- **A mesh integral of a sub-element-scale field converges in neither `h` nor quadrature order.**
  The delivered table alternates sign 49 times along its densest `z`, extrema a median 0.035 nm
  apart. Refining to 3,463,372 elements made the consumer leg *worse* (−1.06e-2, non-monotone in
  between, 669 s to mesh); raising the order from 8 to 37 oscillated at the 1e-3 to 1e-2 level
  without settling. This is aliasing, not inaccuracy, and it is why the conservation gate reports
  the quadrature agreement beside the number rather than the number alone. The remedy is the
  producer's — deposit onto the FE space and rescale to `Q_net` — and it belongs to v0.9's stage 7.
- **OPN-06 is closed, and the answer is "the consumer's".** The delivered table's planar integral is
  the integer −72 e to 4.7e-12, so the published `−72.9 e` is COMSOL's own quadrature of its own
  table, not a smearing error; our own leg by the same route is −0.99 % — same size, opposite sign.
  WP13's Tier-3 comparison of pore charge is therefore two consumer legs, with ours gated ten times
  more strictly than the reference achieved.
- **The `2πr` cancels, so a single conservation number attributes nothing.** Under `dV = 2πr dr dz`
  the Jacobian and PHY-16 step 6's `1/(2πr)` cancel identically for an areal source, which is
  exactly the compensating error PHY-19's rationale warns of. Two legs, gated separately, is the
  only form of the check that names which side of the interface failed.
- **`extra_order=3` on a singular form is not a refinement**, because `Measures.bonus_order` takes
  `max(extra, 3)` for NUM-07's floor. The agreement gate as the plan specified it would have
  compared a value with itself and passed unconditionally. Any future route-agreement gate on a
  form carrying `1/r` has to clear the floor explicitly.
- **A ramped plane indicator is not a refinement of a step, it is the only workable one.** A step is
  integrated by quadrature inside every element the plane crosses; measured on the reference mesh
  the ramp is inside `10⁻³` at every plane while a near-step indicator is outside it, so the check
  would have been measuring its own discretisation.
- **A test that asserts a quadrature-error magnitude must run on a structured mesh.** The corollary
  of the aliasing above, and it only showed up on the CI matrix: netgen's unstructured triangulation
  of the same box at the same `maxh` gave 2.3e-4 on Linux, 7.8e-5 on Windows and 2.2e-5 on macOS for
  the same field — a factor of ten, straddling the 1e-4 gate three ways. Coarsening re-rolls the
  dice, because the quantity is non-monotone in `h`. `MakeStructured2DMesh` places every vertex
  arithmetically, so the number is the same everywhere; the gate now runs at `(27, 70)` divisions.
  A test asserting a *converged physical* quantity is the opposite case and should keep the
  unstructured mesh the pipeline deploys.
- **The optional dependency's version is part of the interface, and 3.10 is where it bites.**
  GridDataFormats 1.2 needs Python ≥ 3.11, so on 3.10 the resolver takes 1.0.2, which reads MRC and
  CCP4 and writes neither. "Is the module importable?" is therefore the wrong guard for anything
  that writes: ask the capability. Every optional-dependency guard added from here should be a
  capability probe with the refusal asserted on the other branch, not a skip — one of the two
  branches then runs on every row of the matrix.

**No boundary layers** (the author, 5 September 2026). WP8 measured the reference region into the
published quality band — 44,316 triangles at minimum SICN 0.6559 — by isotropic grading alone, which
is what the reference model did (§5.2.2), so a Debye-layer resolution study here does not reopen
FR-11. It stays a post-1.0 element-count optimisation, and WP9 posed no anisotropic meshing.

### WP10 — Case-driven runs, the CLI, field output — **delivered**

`cli/__init__.py`, `cli/errors.py`, `io/run.py`, `io/fields.py`, `io/reproduce.py`,
`post/stage.py`, `solve/state.py`, with changes to `core/hashing.py`, `core/stages.py`,
`io/artefact.py` and `solve/stage.py`; the plan's seven spec amendments plus three that
implementation forced (§5.3.2's canonical-serialisation NOTE extended to say the encoding is the
on-disk format and a decoder SHALL exist beside it; a new §5.3.2 workspace-locality NOTE; and
§5.3.2's QR-08 NOTE extended to require the reproduction check be reachable as a command).

Delivered: stages 11 (`qoi`, `nanopnp/qoi/v1`) and 12 (`report`, `nanopnp/report/v1`) registered, so
`run` is a walk over the stage graph rather than physics inside the CLI, with the indicator band
derived from the `membrane` material's z-extent and asserted identical to `lumen_band(fraction=0.8)`;
`io/run.py` as the driver — `PIPELINE` in dependency order, `PAYLOAD_FREE` and `WORKSPACE_STAGES`
both enumerated with tests against the constructors themselves, `Progress`/`CancelToken` threaded
through, the FR-25 manifest and a third run-directory file `run.json` carrying what the run
*produced*, and a `deviations(inputs)` protocol extension letting each stage report the deviations
its own artefact records; `solve/state.py` as the `nanopnp/solution/v2` `.npz` payload — one
coefficient array per component plus the stored wall-distance vector plus a descriptor gate that
aborts naming the first differing key — where `restore` reassembles the *operator* and not only the
state, because NUM-25 is the assembled residual and a restored solution without one can answer only
half of QR-04; `io/fields.py` as the IF-07 export, `Triangle_6` at the P2 node set with midside nodes
matched by vertex pair, split into an Ω pair and a fluid-only Ω_w pair, SI units in the attribute
names and gzip on the heavy data; `cli/errors.py` as the IF-02 exit enumeration, keyed on
`"module:qualname"` strings and walked over the MRO so that classifying an error imports no exception
module; five subcommands over the IF-01 objects, none of whose flags changes what is solved; and
`io/reproduce.py` making QR-08 a callable check rather than only a test assertion. Discharges
**IF-01**, **IF-02**, **IF-07**, **FR-27** and **QR-08**, and adds **VER-32**, **VER-33**, **VER-34**
and **VER-35**.

Beyond the plan: `core/hashing.py` gained `decode_floats`, the inverse of the `{"__f__": x.hex()}`
float encoding — `canonical()` is the on-disk format of `manifest.json` and `run.json` as well as the
hash input, and without a decoder the recorded and live sides of QR-08's comparison speak different
encodings and a present number reads as a missing one; and `io/run.py` gained a workspace under the
store in use, because all four file-writing stages fall back to `store_root()` — the *process*
default — when constructed without one, so a run into a caller's store left its scratch mesh
somewhere the caller never named. `nanopnp-store/` is gitignored besides.

Reference measurements, stabilisation `none`, on `CylindricalPoreGeometry(2, 6, 10)` at `maxh` 4 nm /
`wall_h` 1 nm (124 elements, min SICN 0.7138), 0.1 M NaCl at +20 mV, `ground: cis`,
`solid_permittivities: {membrane: 3.2}`, `default_ladder`:

| Quantity | Value |
|---|---|
| `current_A` | 3.6170916294619195e-11 |
| `currents_A["Na+"]` / `["Cl-"]` | 1.4334969520459997e-11 / 2.18359467741592e-11 |
| `transport_number` | 0.3963120370990567 |
| `conductance_S` | 1.8085458147309597e-09 |
| `eof_m3_s` | 4.484668242351342e-25 |
| Route agreement, relative | **3.25861342399385e-10** |
| QR-08 reproduction, worst relative | **0.0**, 0 store hits / 6 misses |

The route figure is four orders inside NUM-26's `1e-3` and does not depend on the band: over
half-widths 0.6, 1.5, 2.4 and 2.9 nm it stays ≤ 6.7e-10. `import nanopnp.cli` costs 55.6 ms
cumulative and 0.082 s as a cold process, against `import ngsolve`'s ~370 ms — which is what the
string-keyed exit table and the target-string registry buy.

Inherited by WP11: a latent defect, recorded and deliberately not fixed here. The P2 Varadhan
distance field undershoots to −0.99 nm at the re-entrant pore-mouth corner, and
`FittedCorrection.evaluate` clamps the concentration driver but not `wall_distance_nm` — so
`1 − exp(−6.2(d + 0.01))` returns a **negative** diffusivity and mobility factor there. It does not
move the numbers above, the corner being one quadrature neighbourhood, but it is a wrong sign in a
correction and belongs to whichever package owns the distance field's boundary behaviour
(`.knowledge/06-numerics-fem.md` §7.1.1).

### WP11 — Sweep runner

`sweep/plan.py`, `sweep/run.py`, `sweep/collect.py`, CLI subcommand `sweep`.

Substitution on dotted schema paths; the index file and the single-point entry point a job array
calls; the warm-start ordering and its recorded fallback; collection into one dataset with per-point
provenance; a `slow` throughput measurement against QR-06's linear-scaling claim.

Discharges **FR-24**, measures **QR-06**.

### WP12 — Reference-matching stabilised mode

`physics/stabilisation.py`, wired through `CoupledModel`.

SUPG on the Nernst–Planck operator and a Do Carmo–Galeão-type crosswind term, both residual-based;
the P1/P1 equal-order flow pair enabled *only* together with flow stabilisation (NUM-03); the `Pe_h`
evaluation and its element-locating warning (NUM-12); quadrature at NUM-15's orders. Production
default stays `none` (NUM-11), and the mode is already in the provenance record (WP-B1).

Discharges **NUM-03, NUM-12, NUM-14, NUM-15**; adds the two Tier-2 assertions of §Design (MMS in the
stabilised mode, and stabilised → unstabilised under refinement).

### WP13 — Tier 3 harness and the COMSOL comparison

`validation/comsol.py`, `tests/tier3/`, the frozen case set and probe grid, the archived goldens.

The export contract (probe grid, field list, scalar QoIs, golden manifest); the loader and the
relative-L² comparison; the attribution ladder of §Design; the nightly Tier-3 CI job, recorded and
not gated.

Discharges **VAL-01, VAL-02, VAL-03, VAL-04**, retires **RSK-14**, and bounds **RSK-09**. Depends on
the author's exports and on WP8's reference geometry — until both land, the harness is exercised
against a golden generated by our own solver, which tests the machinery and nothing else, and the
report says so.

### WP14 — GUI increment

`gui/`, packaging configuration.

The §8.1 Phase-1 increment in full: case editor generated from the frozen schema, run control, live
convergence plot off the `damped_newton` callback, and the `webgui` field viewer in a
`QWebEngineView`, with the solver in a background process (ADR-004). The packaging probe comes
**first** in the package, not last: it is the RSK-13 detector that amendment A2 deferred out of Phase
0, and a bundle that will not build is worth knowing about before the editor is written.

Discharges **IF-09, QR-11**, closes the deferred Phase-0 criterion 4 and retires **RSK-13**.
Constraint to record: a Windows bundle cannot be built or verified from the Linux development
session, so that step needs the author's machine or a Windows CI runner, and the criterion stays
outstanding until it has run there.

## Open decisions

| # | Decision | Status |
|---|---|---|
| OPN-05 | Pore-polygon vertex count: the specification says 196, the model report's geometry section says 190 for the pore and 196 for the whole geometry | **Closed, 5 September 2026.** The two counts count two objects (§5.2.1); the author designated the delivered 185-vertex table the geometry of record. §10 of the specification records it. |
| VAL-03 export scope | Which frozen cases the reference set covers — the envelope corners at minimum, and whether the analyte case of §7.5.1 joins them | **Open — for the author**, before WP13 starts. Does not block WP7–WP12. |
| GUI packaging target | Whether the Windows bundle is built on the author's machine or on a Windows CI runner | **Open — for the author**, before WP14's probe. RSK-13 stays open until one of them runs. |
| CON-11 / ADR-003 | Bundle default linear solver | **Closed, 2 September 2026.** UMFPACK, GPL-2+ obligation accepted and stated; the library stays BSD-3. `SPECIFICATION.md` CON-11, ADR-003 and §6.6 amended in this commit. |

## Verification

Every package leaves `uv run pytest` green before the next starts — tiers 1 and 2, which is the
phase's acceptance gate.

```bash
uv run ruff check . && uv run ruff format --check . && uv run mypy src/ && uv run pytest
uv run pytest -m tier2 -v                       # the analytic ladder, unchanged from Phase 0
uv run pytest -m tier3 -v                       # the COMSOL comparison: recorded, never gated
uv run pytest -m slow --log-cli-level=INFO      # envelope, factorisation, sweep throughput
```

New verification activities this phase, each named for the requirement it discharges:

| Test file | Tier | Identifiers | What it asserts |
|---|---|---|---|
| `tests/tier1/test_case_schema.py` | 1 | VER-09, IF-03, FR-26 | A written and re-read case resolves to identical provenance; an unknown key is rejected with the key named in the message |
| `tests/tier1/test_artefact_hashing.py` | 1 | FR-27, §5.3.2 | The hash is stable across processes, changes with any payload or parameter change, and a hand-substituted artefact registers as a changed input |
| `tests/tier1/test_manifest.py` | 1 | FR-25, IF-08, §5.3.3 | Every field group of §5.3.3 is present; a switch moved off its validated default appears under Deviations without the writer being told about it |
| `tests/tier1/test_mesh_ingest.py` | 1 | IF-06, QR-12 | A misspelt or unmapped group aborts, naming the group and the missing vocabulary name; a correct mapping round-trips through MSH 4.1 with tags intact |
| `tests/tier1/test_mesh_quality.py` | 1 | VER-10, QR-12 | The gate fires on a known-bad mesh, reports the worst element and its location, and our SICN matches gmsh's on the same elements (skipped without the optional extra) |
| `tests/tier1/test_charge_fields.py` | 1 | QR-03, PHY-19 | Conservation holds to 10⁻³ of a declared `Q_net` on the deployed mesh; a field with no declared `Q_net` records that the check could not run |
| `tests/tier2/test_reproducibility.py` | 2 | QR-08 | A case re-run from its manifest reproduces every scalar QoI to solver tolerance |
| `tests/tier2/test_stabilised_mode.py` | 2 | NUM-14, NUM-15, VER-18 | MMS converges in the stabilised mode at a measured rate; the stabilised and unstabilised currents approach each other under refinement |
| `tests/tier2/test_sweep.py` | 2 | FR-24 | A two-axis sweep warm-starts, collects, and reproduces the same QoIs as the same points run cold |
| `tests/tier3/test_comsol_comparison.py` | 3 | VAL-01, VAL-02, VAL-04 | Relative L² per field and relative error per QoI against the archived goldens, decomposed by the §Design attribution ladder; recorded, not gated |
| `tests/tier1/test_gui_viewmodels.py` | 1 | IF-09, QR-11 | The case editor's model round-trips a case through the schema; the convergence view consumes `NewtonStep` records. No test asserts pixels |

The phase is complete when:

1. **Tiers 1 and 2 pass**, including everything Phase 0 gated, on an *ingested* mesh as well as a
   constructed one.
2. **A case file drives a full run end to end** from the CLI, emits a manifest sufficient to
   reconstruct it, and the reconstruction reproduces every scalar QoI (QR-08).
3. **Tier 3 is enabled and the differences are attributed** by the four-way decomposition, with the
   archived reference set independent of continued licence access (VAL-03).
4. **A sweep of the published shape runs** as independent jobs with warm starts and collects into one
   dataset, with a measured throughput figure against QR-06.
5. **The GUI increment runs a case unaided** on the author's platform, and the packaging probe has
   either produced a double-clickable Windows bundle or named the binary dependency that defeats it
   (RSK-13).

## End-of-phase report

To be written at the end of the phase, naming numbers rather than adjectives:

- The four-way Tier-3 attribution for every frozen case: `Δ_total`, `Δ_stab`, `Δ_pair`, `Δ_resid`,
  and what fraction of `Δ_resid` VAL-04 bounds to the reference's own discretisation error.
- The measured MMS rate in the stabilised mode, and the rate at which the stabilised and
  unstabilised currents converge on each other.
- Sweep throughput: points per worker-hour, and how far from linear the scaling to N workers falls.
- Quality statistics of the reference-geometry mesh against the reference figures (0.6378 minimum,
  0.9765 average on 120,917 triangles), and whether our mesh needed more elements to reach them.
- Any Tier-1 or Tier-2 tolerance that had to be argued rather than met — the one thing Phase 0's
  report flagged as most consequential for this phase's comparison.
- Whether the Windows bundle built, and on what.

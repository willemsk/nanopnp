# WP10 — Case-driven runs, the CLI, field output

**Status: planned, not started.** Written 7 September 2026, the fourth package of Phase 1, after
WP7 landed the case schema, the content-addressed artefact and the provenance manifest, WP8 landed
mesh ingestion and the element-quality gates, and WP9 landed the external charge and dielectric
fields. It inherits a solver that can be driven end to end *from Python* and by nothing else:
`src/nanopnp/cli/__init__.py` is 52 lines of argparse with `--version` and `--env` and no
`add_subparsers` call; `io/store.py` can cache an artefact but nothing walks the stage graph through
it; `solve/stage.py:451` writes `state.gfu` and no `.Load(` exists anywhere in `src/nanopnp` to read
it back; `post/qoi.py` extracts every scalar the phase promises and is reachable only from a test.

This is the implementation plan for WP10 of `docs/plans/phase-1-solver-core.md`. `SPECIFICATION.md`
remains normative: where this file and the specification disagree, the specification governs and this
file is wrong. Requirement identifiers here are pointers into it, never restatements of it.

## Context

Phase 1's premise is that the solver runs on inputs it did not produce and produces results somebody
else can reproduce. WP8 and WP9 made the first half true. WP10 makes the second half true, and it is
the package where the pipeline stops being a library that tests drive and becomes a program a case
file drives.

Five facts about the tree shape the design; all five were established by reading or running code.

- **The stage registry ends at stage 10.** `core/stages.py:_REGISTRY` carries `mesh` (6), `charge`
  (7), `materials` (8), `case` (9) and `solve` (10). Stages 11 (QoI) and 12 (report/export) of §5.2
  have no entry, so the only place a `nanopnp run` could compute a current today is inside the CLI —
  which §5.1 forbids, and which would leave QR-08 with no scalar-QoI artefact to reproduce.
- **`outputs:` is parsed and discarded.** `io/case.py` validates the list against
  `OUTPUTS = {current, transport_numbers, rectification, eof_rate, analyte_force, fields}` and
  `ResolvedCase` carries it as a tuple. Nothing reads that tuple. The vocabulary exists; the
  behaviour behind each word does not.
- **The solution payload is write-only.** `SolveStage` calls `state.Save(str(target))` and no code
  path ever loads it. A warm start today is in-process only: `solve/continuation.py:transfer` takes a
  live `ModelSolution` and refuses one whose mesh differs. WP11's sweeps warm-start from a converged
  neighbour across processes, and there is nothing on disk they can start from.
- **The indicator band cannot be derived for an ingested mesh.** `post/indicator.lumen_band` takes a
  `CylindricalPoreGeometry`, which the WP8 ingestion path never constructs. Every current extracted
  from an ingested mesh today gets its band from a test that hard-codes one.
- **`meshio` and `h5py` are already unconditional core dependencies** in `pyproject.toml`, and
  `h5py` is imported nowhere in `src/`. IF-07 needs no new dependency, only the module that was
  always going to use them.

The risk this package exercises is **RSK-03** — "Current QoI wrong from non-conservative CG flux",
rated High/Med, detection phase Phase 1. WP5 built both NUM-24 and NUM-25 routes and cross-checked
them at 10⁻³ relative in a test. WP10 is where that check moves from a fixture onto the production
path: every `nanopnp run` that asks for `current` computes both routes and records their agreement in
the QoI artefact and hence in the manifest. Quantified: the failure mode RSK-03 names is a current
that is plausible, stable and publishable and wrong by more than the rectification signal —
measured on the VER-11 configuration, a whole-mesh `ψ` costs a factor of 170 in route agreement
(6.5 × 10⁻⁴ against 3.8 × 10⁻⁶) with no other symptom. After WP10 no number leaves the pipeline
without that ratio beside it.

## Decisions taken before implementation

| Decision | Choice | Why |
|---|---|---|
| CLI framework | **argparse, unchanged.** No new dependency | `import nanopnp.cli` is ~70 ms and the deferred-import rule exists to keep it there; typer or click adds `click` + `typing_extensions` to the import path of a shell that holds no logic. The CLI is a shell over IF-01 objects (§5.1), and argparse's subparsers express that shape exactly |
| Subcommand set | `run`, `stage`, `inspect`, `reproduce`, `env`; `--env` retained as an alias | The phase plan names `run`, `stage`, `inspect`, `env`. `reproduce` is added because QR-08 is an *executable* promise, not only a test assertion — see the Design section. `--env` stays because `tests/tier1/test_cli.py` asserts it and removing a working flag is not this package's business |
| Where the pipeline driver lives | `io/run.py`, not `core/` | The driver needs `io.store`, `io.manifest` and the lazy `core.stages.create()`. Putting it in `core/` would make the base layer depend on `io/`, which is the wrong direction in §5.1's table |
| No CLI flag changes the run configuration | Flags choose **where output goes and how much is logged**, never what is solved | Two sources of truth for a physics setting is the failure WP7's frozen schema exists to prevent. A `--fields` override would silently disagree with `outputs:` and the manifest would record one of them. Everything that changes the answer lives in the case file |
| Stages 11 and 12 | **Register `qoi` (11, `nanopnp/qoi/v1`) and `report` (12, `nanopnp/report/v1`)** | Otherwise `nanopnp run` computes physics inside the CLI, violating §5.1, and QR-08 has no scalar artefact to reproduce. `qoi` takes `("case", "solve")`; `report` takes `("case", "qoi", "solve")` |
| What goes in the report artefact's *parameters* | The case, QoI and solution hashes and the export selection only; the environment goes in summary/payload | Parameters are hashed (§5.3.2). A library version in the parameters makes the cache key machine-dependent and every machine a miss |
| Indicator band | **Derived from the mesh**: 0.8 of the `membrane` material's z-extent, taken from the mesh artefact's `MeshData`; no `membrane` material aborts naming it (QR-12); `StageInputs.options["indicator_band_nm"]` overrides, for tests | It must reach the manifest, so it must be a stage parameter rather than a CLI default. On the Phase-0 `CylindricalPoreGeometry` the derivation reproduces `lumen_band(fraction=0.8)` exactly — that identity is the check that it is not a new convention. On the ClyA reference (membrane z ∈ [−1.4, +1.4]) it gives [−1.12, +1.12] |
| The band is **not** a case-file key | The case schema stays frozen | WP7 established that a schema change is a version bump, not an edit. A band in the case file is a physics knob with a derivable default whose wrong value is silent — exactly what §5.3.1 keeps out |
| `outputs:` becomes load-bearing | `current`, `transport_numbers`, `eof_rate` select QoIs; `fields` gates the IF-07 export; `analyte_force` is honoured when the mesh carries an `analyte` material and **refused naming the missing material** otherwise; `rectification` on a single operating point is **refused**, naming it a two-point quantity | Using the frozen vocabulary rather than changing it. Rectification is `I(+V)/I(−V)`; producing it from one bias would have to invent the other, and the sweep runner (WP11, FR-24) is what produces a pair |
| IF-07 topology | **`Triangle_6` at the P2 node set** — vertices plus edge midpoints, `ndof = nv + nedge` | A P2 function on a straight-sided triangle is determined by its six nodal values, so sampling there loses nothing; a P1 function's midpoint value is the mean of its endpoints, so writing `p` at the same nodes is consistent rather than an interpolation error. One node set serves both NUM-01 orders exactly |
| IF-07 file layout | **Two grids as two file pairs**: `omega` (all materials: φ, ε_r, ρ_fixed, material id) and `omega_w` (fluid only: c_i, u, p, wall distance) | meshio writes one grid per XDMF file [tested]. Writing the fluid-only fields as zeros over the membrane is worse than splitting: in a viewer a zero concentration inside the wall reads as physics, not as absence |
| Midside-node matching | **By vertex pair**, never by NGSolve's local edge index | A permutation of the three midside nodes gives a picture that looks right and is wrong; matching by the pair of endpoint vertices assumes no local-ordering convention. Asserted by exporting a quadratic and reproducing it exactly at all six nodes |
| IF-07 units | Coordinates in **nm** (matching the MSH 4.1 archival mesh), declared in an XDMF `Information` element; values in **SI with the unit in the attribute name** (`phi_V`, `c_Na+_mol_m3`, `u_m_s`, `p_Pa`); the `Scales` set recorded in the file | The house rule is SI internally with units at the boundary, and a file is a boundary. Recording the scale set keeps the nondimensional reading recoverable without a second solve |
| The 2π is **not** applied in `io/fields.py` | Exported fields are pointwise | The Phase-0 rule is that the 2π is restored exactly once, in `post/qoi.py`. `io/` re-applying it to a pointwise field would be wrong twice over |
| Exported set | The model's own fields, plus wall distance and material id. **Nothing derived** | Every derived quantity written here is a term whose sign nobody checks against an analytic result. Flux densities, current densities and energy densities are post-processing, and post-processing has its own tier |
| Compression | **gzip on** for HDF5 heavy data | ≈9.2 MB per solve uncompressed (arithmetic below); over WP11's 3 675-point envelope that is ≈33 GB. It is also why `fields` is off unless `outputs:` asks for it |
| Warm-start persistence lives in `solve/state.py` | Not in `io/fields.py` | §5.1 assigns "warm start" to `solve/`. The same reasoning put `RadialGrid` in `density/` in WP9: the module that owns the concept owns its serialisation |
| Warm-start format | **`.npz`**, one coefficient array per field component from `np.asarray(gf.vec)`, **plus the wall-distance coefficient vector**, plus a descriptor | `.npz` follows `density/grid.py`'s native-format precedent and hashes as arrays under WP7's rule. Storing the distance vector rather than re-solving it removes the cross-platform determinism question entirely and honours the Phase-0 rule that a residual reassembled against a freshly solved distance field is a *different operator* |
| Restore is gated, not trusted | The descriptor carries mesh hash, ordered field names, per-field element type/order/`definedon`/ndof, model name and options, case provenance hash, wall-distance sources and `max_distance_nm`, and the stabilisation mode; restore **aborts naming the first differing key** | A coefficient vector loaded into the wrong space is silently a different function. QR-12: name the gate, the quantity and its location |
| `SOLUTION_SCHEMA` → **`nanopnp/solution/v2`** | Bumped | The payload contract changes from `state.gfu` to `state.npz`, and the payload is excluded from the hash — an old cached artefact would otherwise be a *hit* whose payload the new loader cannot read. A changed payload contract is a changed artefact schema |
| Exit codes | 0 success; 1 unexpected; 2 argparse usage; 3 case validation/schema; 4 gate failure (QR-12 family); 5 non-convergence; 130 cancelled | A job array (FR-24, QR-06, WP11) branches on these. `1` for "unexpected" keeps a traceback-worthy bug distinguishable from a case that was refused for a stated reason |
| How exit codes are assigned | An **explicit exception → code table** in `cli/errors.py`, with a Tier-1 test that walks every public exception class in `src/nanopnp/**` and requires each to be classified or listed in a reasoned exclusion list | The same both-directions enumeration discipline WP7 used for `SWITCH_PATHS`/`CONFIGURATION_PATHS`. It catches an error type added later without a base-class refactor, and without a bare `except Exception` swallowing a new gate as "unexpected" |
| Streams | Logging to **stderr** (`-v`/`-vv` → INFO/DEBUG, WARNING default, `--log-file`); **stdout carries only the CLI's own output**, `--json` for machine-readable | `print()` outside the CLI is already forbidden; this is the other half of that rule. A sweep parsing stdout must not receive log lines |
| Tracebacks | Suppressed by default, `--traceback` restores them | A gate abort's diagnostic *is* the message (QR-12); a 40-line traceback in front of it is noise |
| `stage --list` | Prints the registry importing **no** stage module, no ngsolve, no netgen | VER-25 already asserts this of the registry; the CLI is where a user could observe it, so the assertion extends to the subprocess that runs `nanopnp stage --list` |
| `stage NAME CASE` | Computes upstream through the store; `--only` refuses to compute anything upstream and **aborts naming what is missing** | `--only` is what makes a hand-substituted upstream artefact (FR-27) testable: it proves the stage read the substituted file rather than recomputing past it |
| Route agreement | Stays **on** by default; `check_routes=False` reaches the manifest through WP9's stage-contributed deviation channel | The case schema cannot express it, and a NUM-26 check switched off silently is precisely RSK-03 |
| QR-08's reproduction test | Runs against a **fresh store** and asserts the store missed and Newton was re-entered | `get_or_compute` would otherwise serve the cached artefact and the test would assert that a dictionary lookup is deterministic |

## Design

### Stage 11 (`qoi`) and stage 12 (`report`)

`§5.2` numbers twelve stages; the registry stops at ten. Registering the two missing ones is what
lets `run` be a walk over the graph rather than a script.

```
qoi     11  inputs ("case", "solve")           -> nanopnp/qoi/v1
report  12  inputs ("case", "qoi", "solve")    -> nanopnp/report/v1
```

`QoIStage.key(inputs)` is the artefact hash over the case hash, the solution hash, the selected
outputs, the indicator band and the route-check flag — everything that changes a number. `ReportStage`
adds the export selection. Neither carries a library version in its parameters: the environment is
recorded in the manifest, which is beside the artefact and not inside its hash.

The QoI artefact's summary is `QuantitiesOfInterest.summary()` as it stands, plus the `RouteAgreement`
figure. That agreement figure in the summary is the RSK-03 instrument: it is what makes a wrong
current *visible* rather than merely plausible.

### The indicator band, derived

`post/indicator.lumen_band` takes a `CylindricalPoreGeometry`. An ingested mesh has no such object,
so the band is derived from the mesh itself:

```
z_lo, z_hi = z-extent of the elements whose material is `membrane`
z_mid      = (z_lo + z_hi)/2
half       = 0.5 * (z_hi - z_lo) * fraction          # fraction = 0.8
band       = (z_mid - half, z_mid + half)
```

On `CylindricalPoreGeometry` the membrane spans `±half_thickness_nm`, so `z_mid = 0` and
`half = half_thickness_nm * 0.8` — **identically `lumen_band(geometry, fraction=0.8)`**. That
identity is asserted, and it is what says the derivation is the existing convention read off a
different object rather than a second convention that happens to be close. On the WP8 ClyA reference
the membrane spans z ∈ [−1.4, +1.4] nm, giving a band of [−1.12, +1.12] nm.

A mesh carrying no `membrane` material aborts naming the material and listing the materials the mesh
does carry (QR-12). It does not fall back to the whole domain: a band spanning the reservoirs puts
`grad ψ` on the caps and `check_indicator` would then fail with a less informative message.

### IF-07: the export contract

**Node set.** For a P2 space on triangles, `ndof = nv + nedge`; measured on a small mesh,
`21 == 8 + 13` [tested]. The export writes `Triangle_6` cells over exactly that node set: the three
vertices of each element followed by the three edge midpoints, each midpoint identified by the
*unordered pair of vertices* it lies between. Values are sampled by vectorised point evaluation,
`mesh(r_array, z_array)` then `gf(mps)`, which NGSolve supports directly [tested].

Exactness: a P2 polynomial restricted to a straight-sided triangle is uniquely determined by its
values at those six points, so writing them loses nothing — a quadratic exported and read back
reproduces at all six nodes to round-off, and that is the Tier-1 assertion. For `p` (P1) the midpoint
value is the average of the endpoint values, so the same six-node record is the exact P1 function
too, written in a P2 container. One node set, both NUM-01 orders, no interpolation error in either.

**Two grids.** meshio writes one grid per file [tested]: a `meshio.Mesh` with `points` (n, 3) and
`[("triangle6", cells)]` and `point_data` writes `<name>.xdmf` + `<name>.h5` with
`TopologyType="Triangle_6" NodesPerElement="6"` and `Format="HDF"`, and reads back with cell type and
every attribute intact. So the export writes two pairs:

| File pair | Domain | Attributes |
|---|---|---|
| `fields_omega.xdmf` / `.h5` | every material | `phi_V`, `eps_r`, `rho_fixed_C_m3`, `material_id` |
| `fields_omega_w.xdmf` / `.h5` | fluid only (`ELECTROLYTE_DOMAINS`) | `c_<ion>_mol_m3`, `u_m_s` (vector), `p_Pa`, `wall_distance_nm` |

The fluid split is not tidiness. `c_i`, `u` and `p` live on Ω_w by NUM-01; padding them with zeros
over the membrane produces a file in which a reader sees zero concentration *inside the wall* and has
no way to tell that from a converged depletion.

**Units.** Coordinates nm; values SI with the unit in the attribute name. The `Scales` set
(`potential_V`, `concentration_mol_m3`, `velocity_m_s`, `pressure_Pa`) is written into the XDMF as an
`Information` element so the nondimensional state is recoverable arithmetically. The 2π is **not**
applied: the field values are pointwise, and the Phase-0 rule puts the single restoration in
`post/qoi.py`.

**Storage arithmetic.** On the WP8 reference mesh, 44 316 triangles. Euler for a disc:
`V = 1 + E − F`, and `3F = 2E − E_boundary` gives, with the delivered counts,

```
V = 22 159 vertices,  E = 66 474 edges,  P2 nodes = 88 633
points     88 633 × 3 × 8 B = 2.13 MB
topology   44 316 × 6 × 8 B = 2.13 MB   (1.06 MB as int32)
~7 float64 attribute arrays  ≈ 4.96 MB
                              ------------
                              ≈ 9.2 MB per solve
```

Over WP11's 3 675-point envelope that is ≈33 GB uncompressed. gzip is therefore on, and `fields` is
off unless `outputs:` asks for it.

### Warm-start persistence (`solve/state.py`)

The payload of a `nanopnp/solution/v2` artefact is `state.npz`, holding

- one coefficient array per field component, `np.asarray(gf.vec)` per component;
- **the wall-distance coefficient vector**, stored rather than recomputed;
- a descriptor: mesh content hash, ordered field names, per-field element type / order / `definedon`
  / ndof, physics-model name and options, the case provenance hash, the wall-distance `sources` and
  `max_distance_nm`, and the stabilisation mode.

`gf.Save` / `gf.Load` round-trips to max difference exactly `0.0` [tested], so the arrays are the
right level of abstraction; `.npz` is chosen over the native binary because it is self-describing,
hashes under WP7's array rule, and can be inspected without NGSolve.

Storing the distance vector is the load-bearing choice. Phase 0 established that "a residual
reassembled against a freshly solved distance field is a *different operator*". Re-solving the
distance field on restore would make the restored residual depend on the mesh-partitioning and
floating-point details of the machine that restored it; storing 22 159 doubles removes the question
rather than bounding it.

`restore(path, *, case)` rebuilds the space from the case, compares the descriptor key by key, and on
the first difference raises naming the key, the stored value and the rebuilt one (QR-12). It does not
attempt to adapt: a coefficient vector loaded into a space that differs in order, in `definedon` or in
ndof is silently a different function, and there is no residual it would fail to reduce.

> **Outcome — `restore` must rebuild the *operator*, not only the state, so the ladder moved with it.**
> The plan predicted `solve/state.py` would hold `save` and `restore`. It cannot: NUM-25 is the
> assembled residual evaluated on the constrained degrees of freedom, so a restored solution with no
> `residual` can answer only the NUM-24 half of the QR-04 cross-check — and stage 11 served from a
> stage-10 cache hit has no live solution to check against. `restore` therefore reassembles the
> residual from the rung the ladder ends on. Reconstructing that rung by hand would be writing the
> ladder's model construction a second time, so `_single_rung` and `SolveStage._ladder` moved out of
> `solve/stage.py` into `solve/state.py` as `single_rung` and `ladder`; the save path and the restore
> path now build the top rung through one function and cannot differ in a switch. `stage.py` imports
> `state.py` and `state.py` imports `continuation.py`, so nothing is circular. The residual's
> coefficient keywords are separated from the rung's *solve* keywords by exclusion
> (`SOLVE_ONLY_KEYWORDS`): a keyword added to `residual_form` and forgotten there still reaches the
> form, while a new solve keyword forgotten there is rejected loudly by the model's own
> `_reject_unknown` rather than silently dropped.

> **Outcome — measured.** Reference solve: `CylindricalPoreGeometry(2, 6, 10)` at `maxh` 4 nm /
> `wall_h` 1 nm (124 elements, 75 vertices), 0.1 M NaCl, +20 mV, `epnp-ns`, `default_ladder`,
> stabilisation **`none`**, 12 rungs, 40 Newton iterations.
>
> | quantity | corrections off | `willems2020_nacl`, `wall: true` |
> |---|---|---|
> | `state.npz` payload | 11 117 B | 13 688 B |
> | solve-space ndof | 1 232 | 1 232 |
> | wall-distance ndof stored | — (constant) | 273 |
> | round-trip coefficient difference | **exactly 0.0** | **exactly 0.0** |
> | restored vs live NUM-25 flux | identical in every bit | identical in every bit |
>
> The 9.2 MB-per-solve estimate for the WP8 reference mesh stands: 13 688 B at 1 232 ndof is 11.1 B
> per degree of freedom against the design section's 12.5 B, gzip doing slightly better on a coarse
> field than the arithmetic assumed.
>
> Route agreement on the *restored* solution is the oracle for the reassembled operator, and it is
> not free: with the wall corrections on, the NUM-24 and NUM-25 routes disagree by **4.0 × 10⁻¹** on
> the 124-element mesh, by 9.6 × 10⁻⁵ at 257 elements and by 1.6 × 10⁻⁶ at 793. That is resolution of
> the 6.2 nm⁻¹ wall function, not extraction error — `.knowledge/06-numerics-fem.md` §7.1.1. The
> Tier-1 test therefore asserts NUM-26 on the 257-element mesh and does its wiring check on the
> cheaper one. **This sizes the WP10 QoI-stage tests too:** a mesh chosen for a classical solve will
> fail `check_routes` with corrections on.

### `reproduce`, and why it is a verb

QR-08 says a result's manifest is sufficient to reconstruct the run. `nanopnp reproduce RUN_DIR`:

1. reads `case.yaml` and `manifest.json` from the run directory;
2. re-verifies every recorded input hash, **aborting naming any input whose content moved**;
3. re-runs the pipeline into a fresh store;
4. diffs every scalar QoI and exits non-zero on drift.

Library-version drift is **reported, not fatal**, unless `--strict-environment`: a NumPy patch
release is not a reason to refuse to reproduce, and a version difference that *does* move a number is
caught by the QoI diff, which is the assertion that matters.

Tolerance: relative agreement better than the Newton `rtol = 1 × 10⁻⁶` on every scalar QoI, with the
**measured** difference reported rather than only the pass. In-process on a deterministic direct
solve the expected difference is exactly 0; WP9's lesson is that the first honest cross-platform
figure appears on the 3-OS CI matrix, and the test reports the number so that figure is on the record
from the first run.

**The cache must be defeated or the test asserts nothing.** `Store.get_or_compute` would serve the
cached solution artefact and the "reproduction" would be a dictionary lookup. The Tier-2 test runs
against a fresh store and asserts both that the store missed and that Newton was re-entered — the
same construction VER-26 used from the other side to prove that a *hit* does not re-enter Newton.

### Exit-code classification

`cli/errors.py` holds an explicit table:

| Code | Class | Members |
|---|---|---|
| 0 | success | — |
| 1 | unexpected | anything unclassified; traceback suppressed unless `--traceback` |
| 2 | usage | argparse |
| 3 | case | `CaseValidationError`, `UnsupportedCaseSection`, pydantic `ValidationError` at the case boundary |
| 4 | gate | the QR-12 family: `GateViolationError`, `RouteDisagreementError`, `IndicatorError`, ingestion/vocabulary/quality/conservation aborts |
| 5 | convergence | Newton and ladder non-convergence |
| 130 | cancelled | `Cancelled`, SIGINT |

The Tier-1 test enumerates every public exception class under `src/nanopnp/**` and requires each to be
either in the table or in an exclusion list carrying a written reason. A class added later is a test
failure, not a silent `1`.

### Spec amendments this package makes

All seven are edited into `SPECIFICATION.md` in the same commit as this plan.

1. **§5.3.1, NOTE (`outputs:`)** — the vocabulary's meaning: which words select QoIs, that `fields`
   gates the IF-07 export, that `analyte_force` requires an `analyte` material and is refused naming
   it otherwise, and that `rectification` is refused on a single operating point.
2. **§3.1, NOTE (IF-07)** — the XDMF contract: `Triangle_6` at the P2 node set, one grid per domain
   in its own file pair, nm coordinates, SI values with units in the attribute names, gzip HDF5 heavy
   data, and that the 2π factor is not applied to pointwise fields.
3. **§5.3.2, NOTE (solution payload)** — the `nanopnp/solution/v2` payload contract and the descriptor
   gate on restore.
4. **§3.3 / §5.3.2, NOTE (QR-08)** — the reproduction check SHALL re-enter the solve rather than be
   served from the store.
5. **§3.1, NOTE (IF-02)** — the exit-code contract, since a job array (FR-24, QR-06) branches on it.
6. **§7.2 / §7.3** — new rows **VER-32** (CLI surface, exit-code classification, introspection without
   imports), **VER-33** (field-export exactness and the Ω/Ω_w split), **VER-34** (solution-state round
   trip and descriptor gate), **VER-35** (end-to-end reproduction defeating the cache).
7. **Appendix A** — rows for IF-01, IF-02, IF-07 and QR-08, three of which currently read "None yet".

## Work items

| File | Delivers | Identifiers |
|---|---|---|
| `src/nanopnp/cli/__init__.py` | Subparsers `run`, `stage`, `inspect`, `reproduce`, `env`; `--env` alias retained; logging to stderr with `-v`/`-vv`/`--log-file`; `--json`; `--traceback`; `--store`, `--run-dir`; `--env` extended with `store_root()`, `NANOPNP_STORE`, `NANOPNP_REFERENCE_DATA` | IF-02, FR-27 |
| `src/nanopnp/cli/errors.py` | The exception → exit-code table and the classifier | IF-02, QR-12 |
| `src/nanopnp/io/run.py` | The pipeline driver: walks stages 6 → 12 through a `Store`, threads `Progress`/`CancelToken`, writes the run directory and the FR-25 manifest | FR-27, QR-08, IF-01 |
| `src/nanopnp/io/fields.py` | XDMF + HDF5 export: P2 node set, midside matching by vertex pair, the Ω / Ω_w split, SI attribute naming, gzip | IF-07 |
| `src/nanopnp/solve/state.py` | `save(solution, path)` / `restore(path, *, case)`, the `.npz` payload and the descriptor gate | FR-27, QR-08 |
| `src/nanopnp/solve/stage.py` | Payload switched from `state.gfu` to `state.npz`; `SOLUTION_SCHEMA` → `nanopnp/solution/v2` | FR-27 |
| `src/nanopnp/post/stage.py` (new) | `QoIStage` (11) and `ReportStage` (12); the mesh-derived indicator band; `outputs:` honoured and refused where it cannot be met | FR-23, QR-04, IF-01 |
| `src/nanopnp/core/stages.py` | Registry entries for `qoi` and `report` | FR-27, IF-01 |
| `src/nanopnp/io/artefact.py` | `QOI_SCHEMA`, `REPORT_SCHEMA`; `SOLUTION_SCHEMA` bump | §5.3.2 |
| `SPECIFICATION.md` | The seven amendments above | IF-02, IF-07, QR-08, VER-32 … VER-35 |

## Verification

| Test file | Tier | Identifiers | What it asserts |
|---|---|---|---|
| `tests/tier1/test_cli.py` (extended) | 1 | IF-02, VER-32 | Every subcommand parses and dispatches; `--env` still works; `stage --list` runs in a subprocess importing no stage module, no `ngsolve`, no `netgen`, asserted on `sys.modules`; each exit code is produced by a case that triggers its class; every public exception class in `src/nanopnp/**` is classified or excluded with a reason, in both directions; stdout carries only CLI output while logs go to stderr; a gate abort prints its diagnostic and no traceback unless `--traceback` |
| `tests/tier1/test_field_export.py` (new) | 1 | IF-07, VER-33 | A P2 quadratic exported and read back reproduces **exactly at all six nodes** of every element, which a midside permutation fails; `ndof == nv + nedge` on the exported space; the Ω file carries φ/ε_r/ρ_fixed/material id and the Ω_w file carries c_i/u/p/wall distance and no membrane nodes; attribute names carry SI units and values match `Scales` conversion to round-off; the 2π is absent (a known analytic field exports at its pointwise value); gzip is set on the heavy data |
| `tests/tier1/test_solution_state.py` (new) | 1 | FR-27, VER-34 | Save → restore reproduces every component coefficient to **exactly 0.0** difference; the stored wall-distance vector is restored rather than re-solved; a descriptor differing in mesh hash, element order, `definedon`, ndof, model options, wall-distance `sources`/`max_distance_nm` or stabilisation mode each abort naming the offending key with both values; a `nanopnp/solution/v1` payload is refused by schema rather than misread |
| `tests/tier1/test_qoi_stage.py` (new) | 1 | FR-23, QR-04, VER-32 | The mesh-derived band reproduces `lumen_band(geometry, fraction=0.8)` **exactly** on `CylindricalPoreGeometry`; a mesh with no `membrane` material aborts naming it and listing the materials present; `outputs:` selects exactly the QoIs asked for; `analyte_force` without an `analyte` material is refused naming it; `rectification` at one operating point is refused naming it a two-point quantity; the route-agreement figure appears in the artefact summary; `check_routes=False` appears in the manifest as a contributed deviation |
| `tests/tier2/test_reproducibility.py` (new) | 2 | QR-08, VER-35 | A converged case run end to end through `nanopnp run`, then reproduced from its run directory **into a fresh store**, reproduces every scalar QoI to better than the Newton `rtol = 1 × 10⁻⁶` relative, with the measured difference reported; the store is asserted to have **missed** and Newton to have been **re-entered**, so the cache cannot satisfy the test; an input file whose contents moved aborts naming it; a library-version difference is reported and non-fatal without `--strict-environment` and fatal with it |

Tolerance provenance: `1 × 10⁻⁶` is the case schema's own `numerics.nonlinear.rtol` (§5.3.1, NUM-16),
not a number chosen for this test — reproduction to solver tolerance is exactly what QR-08 asks for.
The route-agreement tolerance is NUM-26's `1 × 10⁻³`, unchanged from WP5.

## Out of scope

- **Sweeps and job arrays** (FR-24, QR-06) — WP11. `reproduce` is single-case; the warm-start
  serialisation this package delivers is what WP11 consumes, and delivering it here is the reason
  WP11 can be a sweep runner rather than a sweep runner plus a state format.
- **The GUI** (IF-09, ADR-004) — WP12. Every seam the GUI needs (`Progress`, `CancelToken`,
  `describe()`, the stage registry) is exercised by the CLI here, deliberately.
- **A shipped reference case set** — WP13 / VAL-03. WP10 ships a small case in `tests/` only; the
  frozen reference set waits on the author's still-open VAL-03 export-scope decision.
- **Figures and plots** (stage 12's "figures" column in §5.3.2) — the `report` stage registered here
  writes the manifest and the export selection; plotting is v0.9.
- **COMSOL import or export** (N7) — permanently out of scope.
- **Profiles and derived field quantities** in the XDMF — flux densities, current densities and
  energy densities are post-processing with their own verification tier, and each is a term whose
  sign nobody would check.

## Open questions

None of these block implementation; each has a stated proposal that the plan proceeds on.

1. **QR-08's tolerance across platforms.** Proposal: `1 × 10⁻⁶` relative with the *measured*
   difference reported on every run, so that when the 3-OS matrix produces a larger figure it is on
   the record before anyone has to argue about it. Should the cross-platform figure instead be
   recorded as a separate, looser gate from the outset?
2. **Does `reproduce` earn a subcommand at v0.5**, or is QR-08 adequately discharged by the Tier-2
   test alone? Proposal: keep the subcommand — QR-08 is a promise to a *user* who has a run directory
   and no test harness, and a promise only a test can exercise is not one.
3. **Should WP10 ship an example case outside `tests/`?** Proposal: no. A case file in `examples/`
   becomes a reference the moment somebody runs it, and the reference set is VAL-03's, whose export
   scope is still open (§10).

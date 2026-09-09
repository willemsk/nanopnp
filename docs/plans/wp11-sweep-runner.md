# WP11 — Sweep runner

**Status: delivered, 8 September 2026.** Written 8 September 2026, the fifth package of Phase 1, after WP7
landed the case schema, the content-addressed artefact and the provenance manifest, WP8 mesh
ingestion and the quality gates, WP9 the external charge and dielectric fields, and WP10 the CLI, the
run driver and the on-disk solution payload. It inherits a pipeline that runs *one* case end to end
and has never run two: `src/nanopnp/sweep/__init__.py` is a one-line docstring and nothing else;
`io/run.py` drives a single case and its own module docstring names the sweep runner as the third
walker over the stage graph that does not yet exist; `solve/stage.py:265` calls
`run_ladder(prepared, on_rung=on_rung)` with no `initial=`, so every solve in the package to date has
started cold; and `io/case.py` can *read* a dotted path (through `io/defaults.value_at`) and cannot
write one.

This is the implementation plan for WP11 of `docs/plans/phase-1-solver-core.md`. `SPECIFICATION.md`
remains normative: where this file and the specification disagree, the specification governs and this
file is wrong. Requirement identifiers here are pointers into it, never restatements of it.

## Context

FR-24 is one sentence with four verbs — *sweep any case-file field, dispatch the points as
independent jobs, warm-start each solve from a converged neighbour, collect results into one
dataset* — and the second and third contradict each other on their face. Independent jobs have no
predecessors; a warm start is a predecessor. The package is mostly the work of making both true at
once, and the shape of the answer is a **forest**: the points are ordered so that each has exactly
one parent one grid step away, the tree is broken into waves of mutually independent points, and a
point whose parent is not in the store takes the full NUM-18 ladder and records that it did.

Five facts about the tree shape the design, each established by reading or running the code.

- **`sweep/` is an empty reserved slot** and three modules already forward-reference what will fill
  it. `io/store.py:14-17` explains its atomic-rename write path by naming the WP11 job array;
  `core/stages.py:70-73` explains why `CancelFlag` exists by naming the sweep runner beside the
  desktop shell; `cli/errors.py:113-115` explains `EXIT_CONVERGENCE` as "the member a sweep may
  usefully re-dispatch from a neighbour". The seams were cut for this package; none of them is
  connected to anything.
- **Warm start exists in process and nowhere else.** `run_ladder(rungs, *, initial=...)` is the
  entry point and its own docstring describes the sweep use — "the ladder is climbed once to one
  corner and every other operating point is one rung away from a converged neighbour". No caller
  passes `initial=` except the ladder's own loop. `solve/state.restore` reconstructs a
  `ModelSolution` from a stored `nanopnp/solution/v2` payload, but it re-ingests the mesh itself and
  gates on `solve_hash`, which is by construction *different* for every neighbour. Restoring a
  neighbour's state through the only loader that exists therefore aborts, correctly, every time.
- **`transfer` compares meshes by identity, not by hash.** `solve/continuation.py:453-459` raises
  `TransferError` unless `previous.space.mesh is mesh`. A warm start assembled on its own mesh
  object is refused however equal the two meshes are, so the loader this package adds must build its
  space on the mesh the target run already ingested.
- **Dirichlet data is re-applied over a warm start.** `physics/models.py:1040-1049` reuses
  `initial.space`, copies the vector, and then calls `_apply_essential` unconditionally. The
  neighbour's bias on the constrained potential dofs is therefore overwritten by the target's own
  before Newton takes a step — which is what makes a warm start across the bias axis safe rather
  than merely convergent.
- **There is no dotted-path setter anywhere in the package.** `io/defaults.value_at` walks a path
  with `getattr` and raises `UnknownSwitchPathError`; nothing writes one. "Sweep any case-file field"
  is, mechanically, that function's inverse plus a re-validation.

The risk this package carries is **RSK-15** only at one remove — the phase plan puts GUI scope
against validation effort — but its own exposure is different and worth naming: a sweep is the first
thing in this project that produces *thousands* of numbers, and every failure mode the previous four
packages built gates against now runs three thousand times unattended. Quantified from §8.3: the
reference sweep is 3,675 solves in 41 h on 12 cores, so a member that silently converges to the
wrong answer has 3,674 siblings to hide among, and a member that fails for a reason nobody records
is indistinguishable from one that was never dispatched. That is why the dataset carries a per-member
status and exit class rather than a table of currents, and why the Tier-2 test asserts that a warm
start does not move the answer.

**RSK-02** (under-resolved Debye layer at 3 M giving a plausible wrong current) becomes live in bulk
here for the same reason, and the author's ruling of 8 September 2026 hands this package the one
concrete instance of it that WP10 recorded and left open: the P2 wall-distance field undershoots
below zero at the re-entrant corner of the pore mouth, the ion wall function reads that negative
distance, and the diffusivity and mobility it returns there change sign. WP11 therefore ships the
clamp and the gate that close it — the derivation and the arithmetic are in the Design section — and
carries the NUM-26 route agreement WP10 put on the production path into the dataset row of every
member, so that an under-resolved corner of the envelope is visible in the collected table rather
than only in a log nobody reads.

## Decisions taken before implementation

| Decision | Choice | Why |
|---|---|---|
| Where the sweep is specified | A **separate document**, `schema: nanopnp/sweep/v1`, naming a base case by path and the axes to vary. **Nothing is added to the case schema** | WP7 froze `nanopnp/case/v1` and established that a change to it is a schema version, not an edit. A sweep is also not a property of one case: the same base case is swept three different ways in a week, and a sweep block inside it would make the case document's hash — hence every artefact key downstream — a function of a sweep the run does not perform |
| Axis form | An axis is a named list of **assignments**; an assignment is a mapping of dotted case paths to values. A single-path axis may be written as `path:` + `values:` as sugar. Axes combine as a **Cartesian product** in declaration order | The reference sweep of §8.3 is "5 physics cases × 35 bias values × 21 salt concentrations": the bias and salt axes vary one path each, and each of the five physics cases moves several correction switches *together*. An assignment-valued axis expresses all three without a second concept, and a `zip:` operator would be a fourth way to say what an assignment already says |
| Where the sweep is *not* specified | No CLI flag varies a case-file field | The IF-02 configuration NOTE, applied one level up. A `--bias 0.1,0.2` flag would be a second source of truth for a physics quantity and would reach no manifest |
| Dotted-path substitution | `io/case.substitute(document, assignments) -> CaseDocument`: dump to a plain dict by alias, set each path into the dict, and re-validate the **whole document** through `CaseDocument` | Re-validation is what makes a typo'd path a named diagnostic for free: an unknown key hits `extra="forbid"` and `io/case._render`'s existing "did you mean" message. `model_copy(update=...)` would accept the typo, and building the object by `replace(...)` is the Phase-0 mistake the WP1 resolution discipline exists to prevent — a configuration that names itself must be itself |
| Path validation, before any substitution | `io/case.field_at(path)` walks `CaseDocument.model_fields` through nested models and returns the declared annotation; an unknown component raises naming the prefix that exists and the component that does not. `io/defaults.value_at` is rebased onto the same walker | Two loud failures are better than one: the walk catches a path that does not exist *and* names the type expected, so a string where a float belongs is refused at plan time. Re-validation alone would catch it too, but only per point, and only after the plan committed to 3,675 of them |
| When a plan is validated | **Every point is substituted, validated and `resolve()`d at plan time**, before a single solve | `resolve()` is pure Python — no NGSolve, no mesh — and it is where the NUM-18 refusals live (a case setting `physics.flow` and still selecting `default_ladder` is refused). A 3,675-point plan whose 2,000th point is inadmissible must fail in seconds, not at hour twenty-two |
| Point identity | `point_id` is the first 12 hex characters of `content_hash("nanopnp/sweep/point/v1", assignments)`; the **index** is its position in the plan file | A job array needs an integer and an integer is not an identity: inserting one concentration renumbers everything after it, and a dataset keyed on the index would silently re-label last week's results. The id keys the dataset; the index keys the dispatch |
| Member naming | The sweep rewrites `name:` to `f"{base_name}-{point_id}"` and records that it did | `name` reaches the manifest and the run-directory name and nothing else — it is excluded from `solve_provenance`, so rewriting it moves no field and costs no cache entry. A member whose own manifest cannot say which point it is is not evidence, and QR-06 wants a failed member identifiable |
| Warm-start topology | A **forest over the axis grid**. Each axis declares an `origin` index (default: the first declared value); the parent of a point is the point one index nearer the origin along the **last** axis whose index differs from its origin. The root of each tree is the all-origins point, solved cold by the full ladder | Every edge is one grid step, which is the step the envelope walk already demonstrated warm-starts. Depth is `Σ_j |i_j − origin_j|`, so the wave a point belongs to is that sum and every point in a wave is independent of every other. On the §8.3 grid, with the bias axis rooted at 0 mV, that is 3,675 points in 42 waves at a mean width of 87 — far wider than 12 cores, so the dependency structure is not what limits QR-06 |

> **Outcome — measured: 3,675 points, 42 waves, mean width 87.5, peak width 174, one root.** The
> arithmetic was right. There is exactly one root because a Cartesian grid with one origin per axis
> is one tree, not a forest — "forest" is the correct name for what the rule builds on a grid with
> a mesh axis, where cross-mesh edges are refused, and a single tree is what it builds otherwise.
| Why the origin is declared, not assumed | An axis running −200 … +200 mV has its *hardest* corner at index 0 | Rooting the forest at the first declared value would climb the ladder cold at −200 mV and then walk 400 mV in one direction. The envelope test already walks outward from the easy corner in both directions; `origin` is that behaviour made declarative instead of hard-coded |
| Cold fallback | A point whose parent's stage-10 artefact is absent from the store runs the **full NUM-18 ladder** and records `warm_start: {status: "cold", reason: ...}` in its manifest and in the dataset row | This is what makes "independent jobs" true. A member must be runnable alone, in any order, on a machine that has seen nothing else; the warm start is an optimisation the store may or may not be able to supply, never a precondition |
| What a warm start gates on | The stage-10 descriptor's keys are partitioned into **space-determining** and **operator-determining**; a warm-start load gates the first set exactly as `restore` does and *permits* the second to differ, recording every key that did. The partition is enumerated in both directions and walked by a Tier-1 test | `restore`'s gate includes `solve_hash`, which differs for every neighbour by construction, and `model`, which carries `scales` — a function of `concentration_M`. Gating on either refuses the two axes the sweep exists to walk. Derivation and the partition itself in §Design |

> **Outcome — the partition is over dotted *prefixes*, and a leaf is covered by the longest match.**
> `model.scales` and `model.materials` are keyed by species and by parameter name, so a
> leaf-by-leaf enumeration would have been a function of the electrolyte rather than of the
> descriptor's contract; an entry therefore names a subtree and covers every leaf beneath it.
> `covering_key` takes the longest match, which is what lets `model.switches.log_variables` sit on
> the space side while its siblings sit on the operator side. The Tier-1 test walks the descriptor
> a real solve produced, requires every leaf to be covered exactly once and every entry of both
> lists to cover something, and asserts the two lists are disjoint as written — four assertions
> where the plan foresaw two.
| The warm-start source is provenance, never a key | The stage-10 artefact of a point is the same artefact whether it was reached warm or cold; the neighbour's hash is recorded in the summary and the manifest and enters no digest | Two points differing only in where Newton started must key one artefact or the store holds two entries for one converged state, and QR-08's reproduction compares a warm result against a cold key. This is admissible only because the Tier-2 test asserts the premise — warm and cold agree to the nonlinear tolerance — rather than assuming it |
| The rung a warm-started member runs | The **target rung alone**, not the twelve-rung ladder; the manifest's solver group records the rungs actually run | NUM-18 stage 9 *is* the concentration sweep, and its rungs are warm starts one step apart. Climbing the whole ladder from a converged neighbour would re-solve nine rungs that are already the answer. §6.5 gains a NOTE making the sweep's stage-9 form explicit rather than leaving it inferred |
| Reproducing a warm-started member | `nanopnp reproduce` on a member's run directory re-solves it **cold** and reports the difference against the recorded scalars | QR-08 demands a fresh store, and a fresh store has no neighbour. The cold path is the only one available and it is also the stronger check: it asserts the very property the warm start is licensed by. A reproduction that could only be performed with the neighbour present would be a reproduction of the sweep, not of the result |
| Is a sweep a pipeline stage? | **No.** `sweep/` holds a driver over `io/run.py`, registered in no stage registry. The collected dataset *is* an artefact, `nanopnp/sweep/v1`, built in `sweep/collect.py` with its schema constant beside the others in `io/artefact.py` | A stage takes `StageInputs` and produces one artefact from a bounded set of upstream ones; a stage with 3,675 inputs has no meaningful `key(inputs)` and no meaningful progress fraction. §5.2's twelve stages describe one run, and a sweep is a set of runs |
| Dispatch surface | `nanopnp sweep plan`, `nanopnp sweep run`, `nanopnp sweep collect`, as sub-subcommands of one `sweep` subparser. `run` takes `--index i` (one member, the job-array entry point), `--wave w`, or `--workers N` (the whole plan locally, wave by wave) | FR-24's "dispatch the points as independent jobs" is `--index`; QR-06's "independent workers" is `--workers`. The plan file orders points by wave, so a wave is a **contiguous index range** and a scheduler submits one dependent array per wave from ranges the plan prints. Generating scheduler scripts is not done: a job-array submission is two lines of the user's own shell, and a scheduler library on the end-user path is what CON-07 forbids |
| Exit status | `--index` exits with **that member's own** exit code, through the existing `cli/errors.classify`. `--workers` exits 0 when every member reached a terminal state and the dataset was written, printing the per-class counts; `--fail-fast` makes the first failure abort | The IF-02 exit NOTE exists so a job array can branch per member, and per-member codes are what it means. A local sweep is different: non-convergence at the corners of a hard envelope is an expected *result*, and turning it into a nonzero exit makes a sweep that worked indistinguishable from one that was broken |
| Worker start method and thread pinning | `multiprocessing.get_context("spawn")`, with each worker's initialiser setting `OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS` and `MKL_NUM_THREADS` to `1` **before** the first deferred import. The setting is recorded in the sweep provenance | "Throughput scaling linearly with the number of independent workers" (QR-06) is a claim about independent workers, and N processes sharing one BLAS thread pool are not independent — the measurement would report the pool. `fork` would inherit a parent that had already imported NumPy and make the environment set too late; `spawn` plus the house deferred-import rule means the initialiser runs before anything reads those variables. It is also the only start method Windows has |
| Working directory | The sweep **never** `chdir`s, and workers inherit the parent's | `inputs.mesh.path` and the field documents resolve against the process working directory today. A `chdir` into a member's run directory would silently change which mesh a member reads, with no diagnostic |
| Store | Every member runs into **one shared store**, which is what makes the warm start reachable at all; member run directories are the existing `Store.run_directory`, and the sweep's own files go to a new `Store.sweep_directory(name, digest)` under `<root>/sweeps/` | The store is already content-addressed with atomic renames and a pid-tagged temp name, and its docstring says a job array hits that on its first run. Nothing about concurrency needs building; what needs building is the discipline of giving every member the same store, which the §5.3.2 workspace-locality NOTE already requires per member |
| Resuming | Free, and not a flag: a member whose artefacts are in the store is a cache hit and its dataset row is rebuilt without re-solving | A `--resume` flag would be a second mechanism for what the content hash already is. The dataset row records `cached: true` so the throughput measurement can subtract the hits rather than report a sweep that did no work as infinitely fast |
| Dataset of record | `dataset.json`, written through `canonical()` exactly as `manifest.json` and `run.json` are. One row per point: index, id, assignments, status, exit class, the QoI summary or `null`, run directory, manifest hash, solve artefact hash, seconds, `cached`, and the warm-start record | A failed member's current must not read as a number. Canonical JSON has `null` and CSV has the empty string, which a reader parses as `0.0` on a bad day — and QR-06's whole demand is that a failed member be distinguishable. The encoding is the one WP7 froze and WP10 gave a decoder, so the floats round-trip exactly |
| CSV | `nanopnp sweep collect --csv` writes a flat table beside it whose **first column is `status`** and whose QoI cells are empty on any non-`ok` row | The format the author actually opens. It is a derived export, not the artefact, and it says so in its header comment; making `status` unmissable is the cheapest form of the same protection |
| Rectification | The sweep **strips `rectification` from each member's `outputs:`** and the collector produces it from matched pairs — two rows differing only in `boundary_conditions.bias_V`, with biases exactly opposite. A plan asking for it whose axes produce **no** such pair is refused at plan time, naming it | §5.3.1 already says `rectification` is a two-point quantity that "can only come from a sweep", and `post.qoi.rectification(forward, reverse)` already exists and already refuses two biases of the same sign. This is the package that connects them. Refusing at plan time rather than reporting an empty column is the QR-12 shape: name the gate and what it wanted |
| Two public exceptions, no more | `SweepPlanError(ValueError)` → exit 3, `SweepCollectionError(RuntimeError)` → exit 4, both entered in `cli/errors.EXIT_CODES` | The Tier-1 enumeration test requires every public exception to be classified or excluded with a reason. A plan refused is a case refused (retry will not help); a dataset that cannot be built from members that ran is a gate abort |

> **Outcome — four public exceptions, not two.** `io/case.UnknownCasePathError` (exit 3) and
> `solve/state.WarmStartError` (exit 4) are the other two, and neither was foreseeable from the
> table: the first is what the dotted-path walker raises and is reached from a switch path as well
> as from a sweep axis, and the second is what `load_initial` raises when a neighbour's payload
> does not describe a space this run could load into. Both are in `EXIT_CODES` with their reason
> written beside them. A sweep never lets a `WarmStartError` reach the CLI — FR-24 makes the warm
> start an optimisation, so a refused neighbour falls back to the full ladder and records why —
> but it is a public class and the enumeration is in both directions.
| No new dependency | `multiprocessing`, `csv` and `json` are stdlib; the dataset is canonical JSON | pandas, xarray or pyarrow would each buy a `DataFrame` this package does not need and would put a heavyweight import on the path of a job-array member that pays it 3,675 times |
| The WP10 wall-distance undershoot is fixed **here** | Two changes, and only together: the wall correction reads `max(d̄, 0)`, and a new **NUM-34** gate refuses a mesh whose distance field undershoots below `−1 × 10⁻³ nm` anywhere a wall correction reads it | The author's ruling of 8 September 2026: this package owns it. It is also where it bites. A defect that silently reverses a diffusivity is worth one wrong run today and 3,675 wrong rows the moment this package works, and a sweep is the first thing here that runs unattended. Clamp without gate hides an unresolved mesh behind a plausible number; gate without clamp aborts on projection round-off. §Design carries the arithmetic |
| Clamp the driver, not the factor | `FittedCorrection.evaluate` clips `wall_distance_nm` at zero before the wall form reads it, in the same statement shape as the PHY-13 concentration clip three lines above it, on the float and the CoefficientFunction path alike | A distance is non-negative by definition and the fits are stated for `d̄ ≥ 0`, so a negative sample is a discretisation artefact whose nearest admissible value is zero. Clamping the *factor* at zero instead would set `D_i = μ_i = 0` on that neighbourhood — a degenerate operator, and a lie of the same size as the one it replaces. Clamping in the shared evaluator rather than in the two wall forms keeps the corrections data: a new electrolyte's wall fit inherits it by shipping a YAML |

> **Outcome — `MathOps.clip` gained a one-sided form.** The plan's `ops.clip(wall_distance_nm,
> 0.0, None)` did not type-check: `clip(x, lower, upper)` took two floats. `upper` is now
> `float | None`, NumPy accepts `None` natively and the NGSolve path drops to a single `IfPos`.
> That is a widening of an existing operation rather than a new one, and it is the honest shape:
> the PHY-13 concentration driver is bounded at both ends by the validity range of its fit, and the
> PHY-02 distance driver has no upper bound of its own — the field's saturation distance supplies
> one — and needs only the floor.
| Gate threshold | `min d̄ ≥ −1 × 10⁻³ nm` over the fluid sample set, on the field the corrections actually read — after mollification where it is on | Not zero, because `Set` projects and the sign of the interior residual is platform-dependent; `.knowledge/06` §8.1 already records a strict `> 0` gate that was green on Linux and red on the other two. Not `10⁻²` nm, which is the ion wall function's own root: a gate there admits a diffusivity of exactly zero as its last passing state, and it would put a fit coefficient in Python. One order inside the root, three orders clear of the measured undershoot in either direction |
| When the gate runs | In `solve/stage.py` once per solve, after the field is built and before the first rung, and only when an active correction reads `d̄`; and once per distinct mesh at `sweep plan` time whenever any point of the plan activates a wall correction | Per member it is one evaluation on a sampler the NUM-17 gates build anyway. At plan time it costs one linear solve and the NGSolve import on a command run once, and it is the difference between a 3,675-member sweep refused in seconds and 3,675 identical aborts at wave 0 — the same argument this plan already makes for resolving every point at plan time. A classical run reads no distance field, and gating its mesh would be a gate on nothing |

> **Outcome — the plan-time check memoises the mesh *ingest*, not just the gate.** Keying the
> "already checked" set on the mesh's content hash still read the file once per point, because the
> content hash is only available after the read: a 3,675-point plan sharing one mesh ingested it
> 3,675 times. The memo is now on what the case *says* about the mesh — path, format and vocabulary
> mapping — which two cases naming the same file agree on by construction.
| Existing tests are audited, not exempted | Every Tier-1 and Tier-2 test that builds a real distance field with a wall correction active has its `min d̄` measured and recorded in this commit; one that fails the gate is re-meshed, or switches `wall: false` where the coarse mesh is the point of the test | `tests/tier2/test_envelope.py` is Phase 1's headline convergence evidence and runs every correction at `wall_h` 0.09 nm — finer than the 0.125 nm that came back clean in `.knowledge/06` §7.1.1, so it is expected to pass. Expected is not measured, and if it fails the finding is about the envelope's numbers rather than about the gate. Disabling a correction selects the `none` model rather than taking a branch, so the fallback costs no code |

> **Outcome — one test was re-meshed; the envelope passed as predicted.** `test_envelope.py` at
> `maxh` 6.0 / `wall_h` 0.09 nm measures `min d̄ = +2.47 × 10⁻⁶` nm and passed unchanged, as did
> every other Tier-2 module. The one casualty was `tests/tier1/test_solution_state.py`, whose two
> meshes (4.0/1.0 and 2.0/0.5) both sit on the wrong side of the gate; both were re-meshed to
> `wall_h` 0.35 nm and **collapsed into one**, because NUM-34's floor on `wall_h` dominates the
> element count and 4.0/0.35 gives 392 elements against 2.0/0.35's 419 — "the cheapest mesh that
> carries all four domains" and "the mesh that resolves the wall functions" are now the same mesh.
> `test_current_routes.py` and `test_clamp_logging.py` are classical and were not gated, as
> predicted. The full `min d̄` table for every mesh tried is in `.knowledge/06` §7.1.1.
| Where the 3,675-point sweep is actually run | **Not here.** The `slow` test measures *scaling* on this four-core machine; the §8.3 reference sweep ships as a checked-in document under `docs/sweeps/` and the author runs it on twelve cores at the end of Phase 1 | The author's ruling of 8 September 2026. A day-scale run inside a package's own gate is not a gate, and the scaling curve is the half of QR-06 a four-core machine can honestly measure. What WP11 owes the deferred run is that it be one command against a document in the repository, not a reconstruction from a plan file |
| A sweep axis over `inputs.mesh` | **Warns** at plan time, naming the axis that defeated the warm start; it does not refuse | The author's ruling of 8 September 2026. The forest degenerates to one-point trees and every member is cold — correct, only slower — and VAL-04's mesh-convergence study is a sweep of exactly that shape |

> **Outcome — the bias axis of the reference sweep is rooted at +5 mV, not at 0 V.** The grid is
> still 5 × 35 × 21 = 3,675 points in 42 waves with 1,785 rectification pairs, but the innermost
> value is +5 mV and the axis carries 17 exactly-opposite pairs plus that one unpaired value rather
> than 17 pairs plus zero. The reason is a defect this package found and did not fix: **at exactly
> zero bias the NUM-26 route check is inapplicable, and aborts.** The current is zero, both
> extraction routes return round-off — `I_ψ = 2.288 × 10⁻²⁷` A against `I_reaction = 4.606 × 10⁻²⁵`
> A on the toy pore — and the *relative* difference is 0.995, five hundred times NUM-26's tolerance,
> on a solve that converged at the one operating point whose answer is known exactly. A bias axis
> containing 0 V therefore aborts one member per remaining axis combination. Moving the origin off
> zero keeps the §8.3 grid intact and the checked-in document runnable; making the check
> *inapplicable* rather than failing means deciding what "no current" is, which is a scale the
> extraction does not carry and which NUM-26, a Phase-1 headline gate, would have to gain.
> Recorded in `.knowledge/06` §8.5 for whoever owns it next; deliberately not taken here.

## Design

### The descriptor partition: what a warm start may and may not ignore

`solve/state.py` writes eight descriptor keys with the solution payload and `restore` gates all
eight, aborting on the first difference. That is exactly right for its purpose — reloading *this*
run's own converged state — and exactly wrong for a warm start, because two of the eight differ for
every neighbour by construction:

```
solve_hash  = content_hash(SOLUTION_SCHEMA, resolved.solve_provenance)
```
carries `bias_V` and everything else that keys a solve, so it differs across the bias axis; and

```
model       = dict(CoupledModel.provenance)
            = {model, fields, switches, deviations_from_validated_default,
               stabilisation, scales, materials}
```
carries `scales`, which is the NUM-09 scale set, which is a function of `concentration_M`. Gating on
either refuses the two axes the sweep exists to walk.

The partition that is correct is not "which keys changed" but **what a coefficient vector is**. A
vector is a function only relative to a space, and the space is fixed by the mesh, the per-field
element/order/domain record, the total degree count, the constrained-dof set, and — invisibly — the
NUM-02 branch, since a log-variable model and a primitive one declare the same field names at the
same order with the same `ndof` and mean different things by them. Everything else in the descriptor
fixes the *operator*, and the operator is the target run's own; a warm start supplies a starting
point, not an operator.

So:

| Descriptor key | Class | Gated on a warm start? |
|---|---|---|
| `mesh_content_hash` | space | **yes** — `transfer` refuses a cross-mesh interpolation and so must this |
| `fields` | space | **yes** — names, element, order, domain, per-field ndof |
| `ndof` | space | **yes** |
| `boundaries` | space | **yes** — the Dirichlet *sets* fix which dofs are constrained; a `ground` flip moves them |
| `model.model`, `model.fields` | space | **yes** — the declared field set |
| `model.switches.log_variables` | space | **yes** — the NUM-02 branch; nothing about the shape of the two spaces would catch it |
| `model.switches.pressure_constraint` | space | **yes** — it adds a degree of freedom |
| `model.switches.{flow, variable_density, inertia, steric, dielectric_gradient_forces}` | operator | no — `flow` changes the field set and is caught by `fields` regardless |
| `model.scales`, `model.materials`, `model.deviations_from_validated_default` | operator | no — this is the concentration axis |
| `solve_hash` | operator | no — this is every axis |
| `stabilisation`, `model.stabilisation` | operator | **yes**, by choice — see below |
| `wall_distance.{sources, max_distance_nm}` | operator | no — the target solves its own field |
| `wall_distance.ndof` | space | **yes** — derived from mesh and order, so a difference means one of those moved |

`stabilisation` is the one key placed against its class. It changes the form and not the space, so a
warm start across it would load; it is gated anyway because WP12 introduces the reference mode
precisely to compare two numbers, and a comparison whose two sides were reached through each other
is not one. The cost is zero this phase — `SUPPORTED_STABILISATIONS` is `{"none"}` — and the reason
is written beside the entry.

The partition is enumerated as two explicit tuples of dotted descriptor paths, and a Tier-1 test
walks the descriptor a real solve produces, flattens it to leaves, and requires every leaf to appear
in exactly one of them — in **both** directions, so a key added later fails Tier 1 rather than
silently becoming ungated, and a path left behind by a rename fails too. This is WP7's
`SWITCH_PATHS`/`CONFIGURATION_PATHS` discipline, which found three wrong rows in its own plan's
table, applied to the one place in this package where being wrong is silent.

The loader itself is a second entry point in `solve/state.py`, not a flag on `restore`:

```python
def load_initial(path, *, resolved, mesh, measures, distance, fields) -> ModelSolution
```

It takes the **already-ingested mesh object** — `transfer` compares meshes with `is`, so a loader
that ingests its own is refused however equal the two are — builds the target model's space on it,
gates the space keys, loads the `field.*` arrays and returns a `ModelSolution` with `newton=None`
and **no residual**. No residual, deliberately: `restore`'s residual exists so the NUM-25 reaction
flux can be taken from a reloaded solution, and a warm start is not a solution. The stored
wall-distance vector is likewise not used — the target run computes its own, because the operator
being assembled is the target's.

### The forest, and why it is not a path

The two extremes are a Hamiltonian path through the grid — minimum total work, zero parallelism —
and no warm start at all — maximum parallelism, maximum work. The parent rule above sits between
them and its arithmetic is worth writing down.

For a grid of axis lengths `n_1 … n_k` with origins `o_j`, the parent of a point at indices
`(i_1 … i_k)` is that point with the **last** index differing from its origin moved one step towards
it. Every point therefore has exactly one parent, every edge is one grid step, and the depth of a
point is

```
depth(i) = Σ_j |i_j − o_j|
```

so the wave containing a point is its depth and every point of a wave is independent of every other.
On the §8.3 reference grid — 5 physics cases × 35 biases × 21 concentrations, with the bias origin
at 0 mV and the concentration origin at the low end — the deepest point is at
`4 + 17 + 20 = 41`, so 3,675 points fall into 42 waves at a mean width of 87 and a peak width in the
hundreds. Against QR-06's 12 cores, the dependency structure is not the constraint; the serial
tail is the last few waves, and it is short.

The property that makes it correct rather than merely convenient is that every edge is a step the
envelope walk has already demonstrated: 50 mV in bias and one multiplicative step in concentration,
which `tests/tier2/test_envelope.py` records as "45 warm-started rungs" against "thirty climbs from
cold", the difference between three quarters of an hour and four.

### Why "collect" produces the rectification ratio and nothing else derived

`RR = |I(+V)| / |I(−V)|` is the only quantity in §6.7 that a single operating point cannot produce,
and §5.3.1 already anticipates that it comes from a sweep. Two points form a pair when their
assignment mappings are equal except at `boundary_conditions.bias_V`, and those two values are
exactly opposite. Exactly opposite, not approximately: `post.qoi.rectification` already refuses two
biases of the same sign, and a tolerance on the pairing would let a sweep whose bias axis is not
symmetric report a ratio between 100 mV and −95 mV as though it were a rectification. A plan that
asks for `rectification` and produces no pair is refused at plan time naming the axis, which is the
QR-12 shape and is cheaper than a column of nulls.

Nothing else derived is collected. Conductance and transport number are already per-point (§6.7,
NUM-27) and come out of the member's own QoI artefact; an I–V slope, a selectivity curve or a fitted
conductance would each be a term nobody checks against an analytic result, and post-processing has
its own tier.

### What QR-06's measurement can and cannot say here

QR-06 is a SHOULD with two halves: *3,675 solves within a day-scale wall clock on 12 cores*, and
*throughput scaling linearly with the number of independent workers*. The first is the author's
machine — this development environment reports 4 cores — and is a Phase-1 end-of-phase number, not
something a test can assert. The second is measurable anywhere, and what is measured is:

```
efficiency(N) = T(1) / (N · T(N))
```

over a grid small enough to run in a `slow` test, with the same grid at N = 1, 2 and 4 workers,
against a **fresh store each time** so that cache hits do not manufacture a speedup. Reported, never
gated: the sweep completing is the assertion, exactly as the envelope test frames its own numbers,
and a scaling figure measured on shared CI hardware is a statement about the runner.

Two things the measurement must carry with it or it means nothing. The **thread pinning** above,
because without it N workers contend for one BLAS pool and the curve measures the pool. And
`points_per_worker_hour` computed over **uncached** members only, because a resumed sweep is a
dictionary lookup and would report unbounded throughput.

The first half is deferred by the author's ruling of 8 September 2026: the 3,675-point run happens
on twelve cores at the end of Phase 1, and the author runs it. What that ruling costs this package
is one obligation, and it is worth stating as a deliverable rather than a hope. The reference sweep
is **checked in** — `docs/sweeps/phase1-reference.sweep.yaml` and the base case it names — so that
the deferred run is `nanopnp sweep plan` followed by `nanopnp sweep run --workers 12` against a
document under version control, and the number it produces is attributable to a commit. A reference
sweep reconstructed from prose four weeks later would measure a different grid and nobody would
know. The document is checked at Tier 1 for the cheap half of its correctness — it parses, its base
case resolves, and its plan enumerates 3,675 points in 42 waves — which is everything about it that
can be verified without spending the day.

### The wall-distance undershoot: the clamp, the gate, and why neither alone

The author's ruling of 8 September 2026 gives this package the defect `.knowledge/06` §7.1.1
records. It is worked out here in full.

**What is measured.** On a toy pore (`a` = 2 nm, `L` = 6 nm), 0.1 M NaCl, +20 mV, `willems2020_nacl`
with `wall: true` on diffusivity, mobility and viscosity, the P2 Varadhan field of PHY-02/NUM-31
undershoots below zero at the re-entrant corner of the pore mouth (`r ≈ 2.0`, `z ≈ ±3.0`):

| mesh (`maxh`/`wall_h`, nm) | elements | fluid area with `d < 0` | min `d` (nm) | min `f^w_D` | samples with `f^w_D < 0` |
|---|---|---|---|---|---|
| 4.0 / 1.0 | 124 | 2.186 % | −0.9913 | −437.7 | 8.257 % |
| 2.0 / 0.5 | 257 | 0.687 % | −1.2347 | −1983.1 | 2.373 % |
| 1.0 / 0.25 | 793 | 0.101 % | −0.9628 | −366.8 | 0.264 % |
| 0.5 / 0.125 | 2 618 | 0.000 % | +0.0079 | +0.1 | 0.000 % |

**Why a negative sample is not a small error.** The ion wall function is
`f^w_D(d̄) = 1 − exp(−P1(d̄ + P2))` with `P1 = 6.2 nm⁻¹` and `P2 = 0.01 nm` — the
`exponential_saturation_plus` form, shared by `D_i` and `μ_i`. Its **root is exactly `d̄ = −P2`**,
so the function does not decay towards zero as the wall is approached and then stay there: it
crosses. At the wall itself `f^w_D(0) = 1 − e^{−0.062} = +0.0601`, which is the `check:` value the
YAML carries. One hundredth of a nanometre further in it is zero, and at the measured minimum
`f^w_D(−0.9913) = 1 − e^{+6.0841} = −437.7`, reproducing the table's own figure. A negative
diffusivity and mobility over 8 % of the sampled fluid is an anti-diffusion operator: ions are
driven *up* their own gradient, in the one neighbourhood where PHY-11's wall function is supposed to
hold them back. The viscosity function is `f^w_η(d̄) = 1 + exp(−P1(d̄ − P2))` with `P1 = 3.36 nm⁻¹`,
`P2 = 0.147 nm` — `logistic_plus`, an exponential added to one, strictly greater than one, with no
root and no sign change. It cannot invert; it is merely wrong by a factor of 17.7 at the same point
(46.8 against 2.639 at `d̄ = 0`). So the sign defect is the ion function's alone, and the magnitude
defect is shared — which is the argument for fixing this where **both** read the driver.

**The clamp: on the driver, not the factor.** `FittedCorrection.evaluate` already clips the
concentration driver for PHY-13 and passes `wall_distance_nm` through untouched; the fix is the same
statement shape three lines below, `ops.clip(wall_distance_nm, 0.0, None)` on the float and the
CoefficientFunction path alike. A distance is non-negative by definition and the fits are stated for
`d̄ ≥ 0`, so a negative sample is a discretisation artefact whose nearest admissible value is zero.
Clamping the *factor* at zero instead would set `D_i = μ_i = 0` there — a degenerate operator, and a
lie of the same size as the one it replaces. It goes in the shared evaluator rather than in the two
wall forms because the corrections are data: a new electrolyte's wall fit inherits the clamp by
shipping a YAML file, which is what the house rule means by never touching solver code to add one.

**The gate: NUM-34, `min d̄ ≥ −1 × 10⁻³ nm`.** The threshold is derived, not chosen, and it is
bounded on both sides.

- It cannot be **zero**. `GridFunction.Set` projects element-wise, and although `mesh/distance.py`
  zeroes the constrained dofs outright so the wall is exact, the interior residual is a few times
  `10⁻⁴` nm with a **platform-dependent sign**: `.knowledge/06` §8.1 records a strict `> 0` gate
  that was green on Linux and red on macOS and Windows. A gate at zero is a gate on the rounding
  mode.
- It cannot be `10⁻²` **nm**. That is `−P2`, the ion function's own root, so a gate there admits a
  diffusivity of exactly zero as its last passing state — and it would put a fitted coefficient in
  Python, which the corrections-are-data rule forbids outright.

`1 × 10⁻³` nm sits one order inside the root and one order outside the projection residual. What the
clamp can then silently do on an *admissible* mesh is bounded: at `d̄ = −10⁻³` the unclamped factor
is `1 − e^{−0.0558} = 0.0543` against the clamped `0.0601`, a difference of `0.0058` — under 0.6 % of
the bulk factor, in a neighbourhood where the factor is already sixteen times below bulk. The
threshold is also not a knife edge, because the measured transition is not graded: min `d̄` runs
−0.99, −1.23, −0.96 and then **+0.0079** across one refinement step. The field either resolves the
corner or it does not, and the gate discriminates a regime rather than shaving a tolerance.

**Why both, and never one.** The clamp alone would turn the 124-element row into a plausible number:
its 40 % NUM-24/NUM-26 route disagreement is a statement about *resolution*, and clamping the
driver removes the sign inversion without resolving anything, so the run would come back converged,
gated, and 40 % wrong in the current. The gate alone would abort on the projection round-off that
`Set` leaves behind, on some platforms only. Together they say the honest thing: a field within
round-off of admissible is treated as admissible and clamped, and a field that is genuinely negative
is refused with the QR-12 diagnostic naming the gate, the measured minimum, its `(r, z)` and the
fraction of samples below zero.

**Where it runs.** In `solve/stage.py`, immediately after `wall_distance_field` returns and before
`ladder(...)` builds the first rung, on the field the corrections actually read — after mollification
where NUM-31's smoothing pass is on, since a mollified field is a different field and gating the
un-mollified one would gate something no form evaluates. It runs only when `reads_wall(...)` is
already true, the condition the same module uses to decide whether to solve for the field at all: a
classical run reads no distance field and gating its mesh would be a gate on nothing. The sampler is
`FieldSampler` restricted to the fluid materials, the same P2 nodal set the NUM-17 positivity and
packing gates walk, so the cost is one `minimum()` call on an object the solve builds anyway. And
once per **distinct mesh** at `sweep plan` time whenever any point of the plan activates a wall
correction — one linear solve and the NGSolve import, on a command run once, buying the difference
between a 3,675-member sweep refused in seconds and 3,675 identical aborts at wave 0. That is the
same argument this plan already makes for resolving every point at plan time.

**Blast radius, and what is not assumed.** The two Tier-2 tests that build real meshes on the
coarsest settings in the suite are classical — `test_current_routes.py` (`maxh` 5.0 / `wall_h` 0.4,
classical rungs only, `stage <= 5`) and `test_clamp_logging.py` (`maxh` 6.0 / `wall_h` 0.6,
explicitly classical) — so their existing cases read no distance field and the gate cannot fire on
them. The corrections-on case `test_current_routes.py` gains is a *new* case, added to assert the
refusal, and its coarse mesh is chosen to violate the gate on purpose.
`tests/tier1/test_wall_distance.py` builds real fields at `maxh` 2.0 / `wall_h` 0.15 with no
correction attached to them. The one existing test exposed to the gate is
`tests/tier2/test_envelope.py`, Phase 1's headline convergence evidence, which runs every correction
at `maxh` 6.0 / `wall_h` 0.09 nm — finer at the wall than the 0.125 nm row that came back clean — so
it is *expected* to pass. Expected is not measured: every such test has its `min d̄` measured and
recorded in this commit, and a failure there is a finding about the envelope's numbers rather than a
reason to move the gate.

### Spec amendments this package makes

Written in the same commit as this plan.

- **A — §5.3.4, new: sweep specification and dataset.** FR-24 has no normative surface at all today.
  The new subsection fixes the `nanopnp/sweep/v1` document (base case, axes as lists of assignments,
  per-axis origin), the plan file and its point identity, the warm-start forest and its parent rule,
  the cold fallback, and the `nanopnp/sweep/v1` dataset with its per-member status. §5.3.2's artefact
  table gains the dataset row.
- **B — §5.3.1, `outputs:` NOTE, extended.** The NOTE already refuses `rectification` at a single
  operating point because "the second bias can only come from a sweep". It gains the other half: a
  sweep strips it from each member and the collector produces it from matched opposite-bias pairs,
  refusing at plan time when the axes produce none.
- **C — §5.3.2, solution-payload NOTE, extended.** The descriptor's keys partition into
  space-determining and operator-determining; a warm start from a neighbour SHALL gate the first set
  and record every key of the second that differed; the partition SHALL be enumerated in both
  directions so that a key added later fails verification rather than becoming ungated. And: the
  warm-start source SHALL be recorded in provenance and SHALL NOT enter the stage-10 key, because a
  converged state that depended on where Newton started is a defect the sweep must expose rather
  than cache.
- **D — §6.5, NUM-18 NOTE, extended.** A sweep member warm-started from a converged neighbour SHALL
  run the target rung alone; that is stage 9 of the ladder, not a departure from its fixed path. The
  manifest SHALL record the rungs actually run and the neighbour's artefact hash, and a member whose
  neighbour is unavailable SHALL take the full ladder and record that it did.
- **E — §3.1, IF-02 exit NOTE, extended.** A single-member dispatch SHALL exit with that member's own
  code; a local multi-worker sweep SHALL exit `0` when every member reached a terminal state and the
  dataset was written, the per-member codes being recorded in the dataset rather than reduced to one.
- **F — §7.2 and §7.3.** VER-36, VER-37, VER-38, VER-39 and VER-40 added; Appendix A rows for
  FR-24 and QR-06, which read "None yet" today, and additions to the IF-01, IF-02, QR-04, QR-08 and
  QR-12 rows.
- **G — §8.3, throughput datum, NOTE added.** Linear scaling is a claim about *independent* workers;
  workers sharing a BLAS thread pool are not independent, and a measurement taken without pinning
  reports the pool.
- **H — §4.1, PHY-02, NOTE added.** The wall functions of PHY-11 are stated for `d̄ ≥ 0` and the ion
  form `1 − exp(−P₁(d̄ + P₂))` has its root at `d̄ = −P₂`, so a negative sample does not attenuate a
  coefficient, it reverses its sign. The correction driver `d̄` SHALL therefore be clamped to
  `max(d̄, 0)` before any wall form evaluates it, as PHY-13 already requires of the concentration
  driver. The clamp is a floor on a discretisation artefact and SHALL NOT be relied on to make an
  under-resolved field admissible; NUM-34 is what decides that.
- **I — §6.8, NUM-34 added** at the end of the section, keeping the specification's identifier
  order monotone, with its rationale pointing back at NUM-31 whose field it constrains. The discrete wall-distance
  field, as the corrections read it and after mollification where NUM-31's smoothing pass is
  applied, SHALL satisfy `min d̄ ≥ −1 × 10⁻³ nm` over the fluid domain wherever a wall correction is
  active; a mesh that violates it SHALL abort with the QR-12 diagnostic naming the gate, the
  measured minimum, its location and the fraction of samples below zero, and the measured minimum
  SHALL be recorded in the provenance manifest. Rationale: the threshold is one order inside the ion
  function's root at `−P₂ = −0.01 nm` and one order outside the element-wise projection residual
  that `Set` leaves behind, whose sign is platform-dependent. A run whose distance field is
  genuinely negative is under-resolved at the wall, which NUM-26's route disagreement independently
  reports; the clamp of PHY-02 keeps such a run from returning a *plausible* wrong current, and this
  gate keeps it from returning one at all.

## Work items

| File | Delivers | Discharges |
|---|---|---|
| `src/nanopnp/sweep/document.py` (new) | `SweepDocument` (`nanopnp/sweep/v1`), `Axis`, `Assignment`, `extra="forbid"` throughout with the `io/case._render` diagnostic shape; `load_sweep` / `loads_sweep`, base-case path resolved relative to the sweep document | FR-24, IF-03 |
| `src/nanopnp/sweep/plan.py` (new) | `Point` (index, id, assignments, parent index, wave), `SweepPlan`; the Cartesian product, the origin-rooted forest and its wave ordering; per-point substitution, validation and `resolve()`; the rectification-pair gate; the NUM-34 check once per distinct mesh where any point activates a wall correction; the `inputs.mesh` axis warning; `SweepPlanError`; `write_plan` / `read_plan` through `canonical()` | FR-24, QR-12, NUM-34 |
| `src/nanopnp/io/case.py` (changed) | `field_at(path)` walking `CaseDocument.model_fields`, and `substitute(document, assignments)` through dump → set → re-validate; `io/defaults.value_at` rebased onto the same walker | IF-03, FR-24 |
| `src/nanopnp/solve/state.py` (changed) | `SPACE_KEYS` / `OPERATOR_KEYS` as dotted descriptor paths partitioning the descriptor, with a written reason on each operator entry; `load_initial(...)` on a caller-supplied mesh, gating the space keys, returning a residual-free `ModelSolution` | §5.3.2 NOTE (amendment C) |

> **Outcome — `load_initial` returns a `WarmStart` record, not a bare `ModelSolution`, and takes
> the target's `mesh_content_hash`.** Amendment C requires every operator key that differed to be
> recorded, and a bare solution carries nowhere to put them; `WarmStart` holds the solution, the
> neighbour's artefact hash and the differing keys, and `summary()` is what reaches the manifest.
> The mesh hash is a parameter because the gate compares the stored one against the *target's*, and
> the target has already ingested its mesh — re-ingesting inside the loader would both cost a read
> and defeat `transfer`, which compares meshes with `is`. `warm_start_payload(artefact)` is a
> second addition: the `nanopnp/solution/v1` refusal the plan asks for is a check on the
> **artefact**, not on the file, because a v1 payload is a backend binary this module cannot open
> at all and "not a payload of the version I read" is a better diagnostic than NumPy's.
| `src/nanopnp/solve/stage.py` (changed) | `SolveStage(..., warm_start=SolutionArtefact \| None)`: passes `initial=` to `run_ladder` and runs the target rung alone when one is supplied; the neighbour's hash and the differing operator keys into the artefact summary; **no change to `key(inputs)`** | FR-17, FR-24 |

> **Outcome — the stage also takes `cold_reason`, and `run_document` gained an `arguments`
> parameter to get either of them there.** A warm start is an *artefact*, so it cannot ride on
> `StageInputs.options`, whose values are canonicalisable by contract because they reach a digest.
> `run_document(..., arguments={"solve": {...}})` passes constructor arguments through
> `_Walk.construct` to `create(name, **kwargs)`; nothing passed that way enters a key, which is
> exactly right for a warm start (§5.3.2). `cold_reason` is there because "no parent" and "the
> parent's state was refused" are different facts and QR-06 asks that a sweep's timings say which
> members paid for what.
| `src/nanopnp/sweep/run.py` (new) | The member entry point (`run_point`) resolving the parent artefact from the store and falling back to cold with a recorded reason; the `spawn` pool, its thread-pinning initialiser and per-wave dispatch; `Progress`/`CancelToken` per member; per-member exception capture and classification | FR-24, FR-27, QR-06 |
| `src/nanopnp/sweep/collect.py` (new) | `SweepArtefact` assembly, the row schema, `dataset.json` through `canonical()`, the CSV export, the opposite-bias pairing and `rectification`; `SweepCollectionError` | FR-24, FR-23 |
| `src/nanopnp/io/artefact.py` (changed) | `SWEEP_SCHEMA = "nanopnp/sweep/v1"` and `SweepArtefact` beside the other schemas | §5.3.2 |
| `src/nanopnp/io/store.py` (changed) | `sweep_directory(name, digest)` under `<root>/sweeps/` | §5.3.2 |
| `src/nanopnp/io/manifest.py` (changed) | The solver group carries the warm-start record — status, neighbour artefact hash, differing operator keys, rungs actually run — and the mesh group carries the measured `min d̄` where a wall correction was active | FR-25, §5.3.3, NUM-34 |
| `src/nanopnp/materials/models.py` (changed) | `FittedCorrection.evaluate` clips `wall_distance_nm` at zero before the wall form reads it, on both `MathOps` paths, with the PHY-11 root written beside it | PHY-02 (amendment H) |
| `src/nanopnp/solve/gates.py` (changed) | `WallDistanceGate(sampler, distance, minimum_nm=-1e-3)`: a `Gate` returning the measured minimum and its `(r, z)`, raising `GateViolationError` naming the gate, the quantity, the value, the location and the below-zero sample fraction | NUM-34, QR-12 |
| `src/nanopnp/solve/stage.py` (changed) | The gate checked once per solve, after `wall_distance_field` and before the first rung, only when `reads_wall(...)`; the measured minimum into the artefact summary and the manifest | NUM-34 |
| `src/nanopnp/cli/__init__.py` (changed) | The `sweep` subparser and its `plan` / `run` / `collect` sub-subcommands, every physics quantity still in the case file | IF-02 |
| `src/nanopnp/cli/errors.py` (changed) | `SweepPlanError` → 3, `SweepCollectionError` → 4 | IF-02 |
| `docs/sweeps/phase1-reference.sweep.yaml` (new), with its base case | The §8.3 reference sweep — 5 physics cases × 35 biases × 21 concentrations — checked in, so the deferred twelve-core run is one command against a commit rather than a reconstruction | QR-06, §8.3 |
| `SPECIFICATION.md` | Amendments A–I above | — |
| `.knowledge/06-numerics-fem.md` | The measured warm-start saving and the measured scaling curve, marked **[tested]**; §7.1.1's "recorded here rather than fixed under WP10" closed out with the clamp, the gate and the measured `min d̄` of every correction-on test | — |

## Verification

| Test file | Tier | Identifiers | What it asserts |
|---|---|---|---|
| `tests/tier1/test_sweep_plan.py` (new) | 1 | FR-24, IF-03, QR-12, VER-36 | A product of three axes enumerates the right points in the right order; an assignment-valued axis moves several paths together; a `point_id` is stable across processes and unchanged by inserting a value on another axis, while the index is not; every point has exactly one parent one grid step nearer the origin, wave equals depth, and every point of a wave is pairwise independent; a `±` axis roots at its declared origin and walks outward both ways; a misspelt path is refused naming the component and the prefix that exists; a value of the wrong declared type is refused at plan time; a point that `resolve()` refuses (`physics.flow: false` with `default_ladder`) fails the plan naming the point and the case-file reason; `rectification` with no opposite-bias pair is refused naming the axis; the checked-in `docs/sweeps/phase1-reference.sweep.yaml` parses, its base case resolves, and its plan enumerates 3,675 points in 42 waves — everything about the deferred twelve-core run that can be verified without spending the day |
| `tests/tier1/test_warm_start_descriptor.py` (new) | 1 | VER-37, §5.3.2 | Every leaf of a descriptor taken from a real solve appears in exactly one of `SPACE_KEYS` and `OPERATOR_KEYS`, and every entry of both lists appears in the descriptor — both directions; `load_initial` accepts a payload differing only in `solve_hash`, `scales` and `materials` and records each; it aborts naming the key and both values on a differing mesh hash, `ndof`, field record, `boundaries`, `log_variables` or `stabilisation`; a `nanopnp/solution/v1` payload is refused by schema; the returned solution carries no residual and does not read the stored distance vector |
| `tests/tier1/test_sweep_cli.py` (new) | 1 | IF-02, FR-27, VER-38 | `sweep plan`, `sweep run` and `sweep collect` parse and dispatch; no flag changes a case-file field; `sweep run --index` exits with the member's own class for each of the case, gate, convergence and cancellation classes; `--workers` exits 0 with a failed member and nonzero with `--fail-fast`; `SweepPlanError` and `SweepCollectionError` are in the exit enumeration (inherited from the existing both-directions test); the worker initialiser sets the three thread variables before any deferred import, asserted in a spawned subprocess on `sys.modules` and `os.environ`; the dataset round-trips write → read to identical values; the CSV's first column is `status` and a failed row's QoI cells are empty |
| `tests/tier1/test_wall_distance.py` (extended) | 1 | NUM-34, VER-40, PHY-02 | The clamp returns `f^w_D(0) = 0.0601` for every `d̄ ≤ 0` and is continuous across zero, on the float and the CoefficientFunction path alike, and the viscosity form is clamped by the same statement; the `WallDistanceGate` refuses the 124-element mesh of `.knowledge/06` §7.1.1 naming the gate, the measured minimum, its `(r, z)` and the below-zero fraction, and passes on the 2,618-element one; the un-mollified and mollified fields are both gated when NUM-31's smoothing is on, and it is the mollified one the gate reads; a classical case builds no distance field and is not gated; the gate's own threshold is read from one named constant, not repeated |
| `tests/tier2/test_sweep.py` (new) | 2 | FR-24, VER-37, VER-38 | On a 2 × 2 grid (two concentrations × ±50 mV) on the WP10 reference pore: every point warm-started from its parent reproduces the same point run cold to better than the `1 × 10⁻⁶` nonlinear relative tolerance, with the **measured** worst difference reported; the warm run costs strictly fewer Newton iterations in total; a member whose parent artefact is deleted from the store falls back to the full ladder, converges, and records `cold` with the reason; the collected dataset carries one row per point with its NUM-26 route agreement, and the `rectification` of the ± pair equals `post.qoi.rectification` of the two rows exactly; a member run with `--index` alone into an empty store produces the same scalars as the same member inside the sweep |

> **Outcome — measured. Worst warm-against-cold difference `3.367 × 10⁻⁹`** (on `conductance_S`),
> against the `1 × 10⁻⁶` tolerance; on the deepest point the current agreed to `9.8 × 10⁻¹⁰`. The
> warm pass cost **77 Newton iterations against the cold pass's 216, a factor of 2.81** with 3 of 4
> members warm-started; the wall clock was 10.5 s against 22.3 s on an idle machine. One departure
> from the plan's wording: the cold pass runs every member in **reverse index order into a fresh
> store** rather than deleting a parent artefact — a point's parent always has a lower index, so
> running downwards leaves every member without one, which is the state a job-array member finds on
> a machine that has seen nothing else and needs no special casing.
>
> The comparison was briefly on **wall time**, and that was a mistake the suite caught rather than
> a judgement call: run alongside the rest of the suite, the same code gave 34.3 s warm against
> 26.7 s cold — the two passes swapped places — where an idle machine gave 10.0 s against 21.6 s.
> `seconds` is a statement about the machine. `MemberResult` therefore gained an `iterations`
> field, taken from the ladder's own record and carried into the dataset row and the CSV beside
> the seconds, and it is what the assertion is on. The plan said "Newton iterations" and was
> right.
| `tests/tier2/test_current_routes.py` (extended) | 2 | NUM-34, NUM-26, VER-40 | With the wall corrections on, the coarse mesh that returned a 40 % NUM-24/NUM-26 route disagreement is **refused by the gate** rather than returning a plausible current, and the refined mesh passes the gate and agrees between the two routes to better than NUM-26's `1 × 10⁻³`. This is the half of VER-40 that cannot be asserted on the correction functions alone: it is the statement that the gate discriminates the regime the route disagreement was reporting |
| `tests/tier2/test_sweep_throughput.py` (new, `slow`) | 2 | QR-06, VER-39 | A grid large enough to fill the waves, run at 1, 2 and 4 workers into a fresh store each time; points per worker-hour over *uncached* members and `efficiency(N) = T(1)/(N·T(N))` are logged with the core count, the pinning setting and the wave widths. Recorded, never gated: completing the sweep is the assertion |

> **Outcome — measured, and the first attempt measured the runner's own startup cost.**
> `efficiency(1, 2, 4) = 1.00, 0.76, 0.50` on four cores: 25 points in seven waves of widths
> 1, 3, 5, 5, 5, 4, 2, wall clock 33.5 → 22.1 → 16.8 s, throughput 2 686 → 2 034 → 1 337 points per
> worker-hour over uncached members. Two things the measurement changed. **The pool is now held
> open for the whole plan rather than created per wave**: `spawn` re-imports the package in each
> worker at about a second apiece, and paying that five times took `efficiency(4)` from 0.75 to
> **0.29** — a defect in the runner that only a scaling measurement could have surfaced. And the
> grid needed **two axes**: a one-axis sweep rooted in its middle has waves two points wide and
> caps the curve at N = 2 whatever the runner does, so the measurement would have reported the grid.

Every Tier-1 and Tier-2 test that builds a real distance field with a wall correction active has its
`min d̄` measured and recorded in the commit that adds the gate — `tests/tier2/test_envelope.py`
above all, which is expected to pass at `wall_h` 0.09 nm and is not assumed to.

Tolerance provenance: `1 × 10⁻⁶` is the case schema's own `numerics.nonlinear.rtol` (§5.3.1,
NUM-16), the same number QR-08's reproduction check uses and for the same reason — two Newton solves
converged to one fixed point from different starting points differ by the residual each left behind,
and that is what `rtol` bounds. The route-agreement figure carried into every dataset row is
NUM-26's `1 × 10⁻³`, unchanged since WP5.

## Out of scope

- **The stabilised mode.** WP12 adds `stabilisation: reference` and must thread it through
  `default_ladder`, as WP7's own record warns. The warm-start gate here refuses to cross the two
  modes, which is what makes WP13's attribution ladder a comparison rather than a chain.
- **Cross-mesh warm starts.** `transfer` refuses them deliberately — interpolating outside the
  source domain returns a plausible number rather than raising — and NUM-19's mesh adaptation
  between rungs is not exercised this phase. A sweep over a mesh-changing axis is therefore a forest
  of one-point trees, and the plan says so rather than approximating.
- **Retry policy.** A member that fails to converge is recorded and not re-dispatched from a
  different neighbour, although `EXIT_CONVERGENCE` exists to make that possible later. Choosing a
  second parent automatically is a heuristic whose failure is a converged wrong answer.
- **Scheduler integration.** No SLURM or PBS script is generated (CON-07). The plan prints the
  contiguous index range of each wave; the submission is the user's two lines.
- **Figures.** §5.2's stage 12 mentions figures; nothing here plots. An I–V curve drawn from the
  dataset is v0.9's reporting work.
- **Re-meshing to satisfy NUM-34.** The gate refuses an inadmissible mesh and names what it
  measured; it does not refine one. Automatic refinement in response to a gate is NUM-19's
  adaptivity, which is not exercised this phase, and a mesher that silently changes the mesh a
  manifest names would defeat the provenance the gate exists to protect.
- **Any second use of the clamped driver.** The clamp is a floor inside `FittedCorrection.evaluate`
  and changes nothing that reads the distance field for another purpose — the IF-07 export, the
  stored wall-distance vector, VER-06's continuity measure. Those still see the field as solved,
  which is what makes the gate's diagnostic meaningful.

## Open questions

None. All three were put to the author and ruled on, 8 September 2026; each ruling is carried into
the Decisions table above and into the design and verification sections it changes.

1. **Who owns the P2 distance-field undershoot?** *Ruled: this package does, and it is to be worked
   out here.* WP10 recorded it deliberately unfixed and this plan, as first written, proposed to
   pass it to WP12 or to a package of its own. That is reversed: §Design derives the clamp and the
   NUM-34 gate in full, amendments H and I make them normative, and VER-40 verifies them. The
   argument that carried it is that a sweep is the first thing in this project to run unattended, so
   a defect worth one wrong run today is worth 3,675 wrong rows the moment this package works.
2. **Where is QR-06's headline number measured?** *Ruled: not here — deferred to the end of Phase 1,
   and the author runs it on twelve cores.* The `slow` test measures the scaling curve only, which
   is the half a four-core machine can honestly measure. What WP11 owes the deferred run is that it
   be one command against a checked-in `docs/sweeps/` document, which is now a work item.
3. **Should a sweep axis be allowed to vary `inputs.mesh`?** *Ruled: warn, do not refuse* — the
   assumption this plan carried is confirmed. The forest degenerates to one-point trees, every
   member is cold, and the plan-time warning names the axis that defeated the warm start. VAL-04's
   mesh-convergence study is a sweep of exactly that shape.

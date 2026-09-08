# WP11 — Sweep runner

**Status: planned, not started.** Written 8 September 2026, the fifth package of Phase 1, after WP7
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
here for the same reason. It is not this package's to retire; what this package owes it is that the
NUM-26 route agreement WP10 put on the production path is carried into the dataset for every member,
so an under-resolved corner of the envelope is visible in the collected table rather than only in a
log nobody reads.

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
| Why the origin is declared, not assumed | An axis running −200 … +200 mV has its *hardest* corner at index 0 | Rooting the forest at the first declared value would climb the ladder cold at −200 mV and then walk 400 mV in one direction. The envelope test already walks outward from the easy corner in both directions; `origin` is that behaviour made declarative instead of hard-coded |
| Cold fallback | A point whose parent's stage-10 artefact is absent from the store runs the **full NUM-18 ladder** and records `warm_start: {status: "cold", reason: ...}` in its manifest and in the dataset row | This is what makes "independent jobs" true. A member must be runnable alone, in any order, on a machine that has seen nothing else; the warm start is an optimisation the store may or may not be able to supply, never a precondition |
| What a warm start gates on | The stage-10 descriptor's keys are partitioned into **space-determining** and **operator-determining**; a warm-start load gates the first set exactly as `restore` does and *permits* the second to differ, recording every key that did. The partition is enumerated in both directions and walked by a Tier-1 test | `restore`'s gate includes `solve_hash`, which differs for every neighbour by construction, and `model`, which carries `scales` — a function of `concentration_M`. Gating on either refuses the two axes the sweep exists to walk. Derivation and the partition itself in §Design |
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
| No new dependency | `multiprocessing`, `csv` and `json` are stdlib; the dataset is canonical JSON | pandas, xarray or pyarrow would each buy a `DataFrame` this package does not need and would put a heavyweight import on the path of a job-array member that pays it 3,675 times |
| The WP10 distance-field undershoot is **not** fixed here | Recorded again, unfixed, and raised as an open question | It changes every number a coarse-mesh test reports and needs a specification amendment (`.knowledge/06` §7.1.1). It belongs to a numerics package, not to a dispatcher. What this package owes it is that the NUM-26 route agreement — the diagnostic that catches it — reaches every dataset row |

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
- **F — §7.2 and §7.3.** VER-36, VER-37, VER-38 and VER-39 added; Appendix A rows for FR-24 and
  QR-06, which read "None yet" today, and additions to the IF-01, IF-02 and QR-08 rows.
- **G — §8.3, throughput datum, NOTE added.** Linear scaling is a claim about *independent* workers;
  workers sharing a BLAS thread pool are not independent, and a measurement taken without pinning
  reports the pool.

## Work items

| File | Delivers | Discharges |
|---|---|---|
| `src/nanopnp/sweep/document.py` (new) | `SweepDocument` (`nanopnp/sweep/v1`), `Axis`, `Assignment`, `extra="forbid"` throughout with the `io/case._render` diagnostic shape; `load_sweep` / `loads_sweep`, base-case path resolved relative to the sweep document | FR-24, IF-03 |
| `src/nanopnp/sweep/plan.py` (new) | `Point` (index, id, assignments, parent index, wave), `SweepPlan`; the Cartesian product, the origin-rooted forest and its wave ordering; per-point substitution, validation and `resolve()`; the rectification-pair gate; `SweepPlanError`; `write_plan` / `read_plan` through `canonical()` | FR-24, QR-12 |
| `src/nanopnp/io/case.py` (changed) | `field_at(path)` walking `CaseDocument.model_fields`, and `substitute(document, assignments)` through dump → set → re-validate; `io/defaults.value_at` rebased onto the same walker | IF-03, FR-24 |
| `src/nanopnp/solve/state.py` (changed) | `SPACE_KEYS` / `OPERATOR_KEYS` as dotted descriptor paths partitioning the descriptor, with a written reason on each operator entry; `load_initial(...)` on a caller-supplied mesh, gating the space keys, returning a residual-free `ModelSolution` | §5.3.2 NOTE (amendment C) |
| `src/nanopnp/solve/stage.py` (changed) | `SolveStage(..., warm_start=SolutionArtefact \| None)`: passes `initial=` to `run_ladder` and runs the target rung alone when one is supplied; the neighbour's hash and the differing operator keys into the artefact summary; **no change to `key(inputs)`** | FR-17, FR-24 |
| `src/nanopnp/sweep/run.py` (new) | The member entry point (`run_point`) resolving the parent artefact from the store and falling back to cold with a recorded reason; the `spawn` pool, its thread-pinning initialiser and per-wave dispatch; `Progress`/`CancelToken` per member; per-member exception capture and classification | FR-24, FR-27, QR-06 |
| `src/nanopnp/sweep/collect.py` (new) | `SweepArtefact` assembly, the row schema, `dataset.json` through `canonical()`, the CSV export, the opposite-bias pairing and `rectification`; `SweepCollectionError` | FR-24, FR-23 |
| `src/nanopnp/io/artefact.py` (changed) | `SWEEP_SCHEMA = "nanopnp/sweep/v1"` and `SweepArtefact` beside the other schemas | §5.3.2 |
| `src/nanopnp/io/store.py` (changed) | `sweep_directory(name, digest)` under `<root>/sweeps/` | §5.3.2 |
| `src/nanopnp/io/manifest.py` (changed) | The solver group carries the warm-start record — status, neighbour artefact hash, differing operator keys, rungs actually run | FR-25, §5.3.3 |
| `src/nanopnp/cli/__init__.py` (changed) | The `sweep` subparser and its `plan` / `run` / `collect` sub-subcommands, every physics quantity still in the case file | IF-02 |
| `src/nanopnp/cli/errors.py` (changed) | `SweepPlanError` → 3, `SweepCollectionError` → 4 | IF-02 |
| `SPECIFICATION.md` | Amendments A–G above | — |
| `.knowledge/06-numerics-fem.md` | The measured warm-start saving and the measured scaling curve, marked **[tested]** | — |

## Verification

| Test file | Tier | Identifiers | What it asserts |
|---|---|---|---|
| `tests/tier1/test_sweep_plan.py` (new) | 1 | FR-24, IF-03, QR-12, VER-36 | A product of three axes enumerates the right points in the right order; an assignment-valued axis moves several paths together; a `point_id` is stable across processes and unchanged by inserting a value on another axis, while the index is not; every point has exactly one parent one grid step nearer the origin, wave equals depth, and every point of a wave is pairwise independent; a `±` axis roots at its declared origin and walks outward both ways; a misspelt path is refused naming the component and the prefix that exists; a value of the wrong declared type is refused at plan time; a point that `resolve()` refuses (`physics.flow: false` with `default_ladder`) fails the plan naming the point and the case-file reason; `rectification` with no opposite-bias pair is refused naming the axis |
| `tests/tier1/test_warm_start_descriptor.py` (new) | 1 | VER-37, §5.3.2 | Every leaf of a descriptor taken from a real solve appears in exactly one of `SPACE_KEYS` and `OPERATOR_KEYS`, and every entry of both lists appears in the descriptor — both directions; `load_initial` accepts a payload differing only in `solve_hash`, `scales` and `materials` and records each; it aborts naming the key and both values on a differing mesh hash, `ndof`, field record, `boundaries`, `log_variables` or `stabilisation`; a `nanopnp/solution/v1` payload is refused by schema; the returned solution carries no residual and does not read the stored distance vector |
| `tests/tier1/test_sweep_cli.py` (new) | 1 | IF-02, FR-27, VER-38 | `sweep plan`, `sweep run` and `sweep collect` parse and dispatch; no flag changes a case-file field; `sweep run --index` exits with the member's own class for each of the case, gate, convergence and cancellation classes; `--workers` exits 0 with a failed member and nonzero with `--fail-fast`; `SweepPlanError` and `SweepCollectionError` are in the exit enumeration (inherited from the existing both-directions test); the worker initialiser sets the three thread variables before any deferred import, asserted in a spawned subprocess on `sys.modules` and `os.environ`; the dataset round-trips write → read to identical values; the CSV's first column is `status` and a failed row's QoI cells are empty |
| `tests/tier2/test_sweep.py` (new) | 2 | FR-24, VER-37, VER-38 | On a 2 × 2 grid (two concentrations × ±50 mV) on the WP10 reference pore: every point warm-started from its parent reproduces the same point run cold to better than the `1 × 10⁻⁶` nonlinear relative tolerance, with the **measured** worst difference reported; the warm run costs strictly fewer Newton iterations in total; a member whose parent artefact is deleted from the store falls back to the full ladder, converges, and records `cold` with the reason; the collected dataset carries one row per point with its NUM-26 route agreement, and the `rectification` of the ± pair equals `post.qoi.rectification` of the two rows exactly; a member run with `--index` alone into an empty store produces the same scalars as the same member inside the sweep |
| `tests/tier2/test_sweep_throughput.py` (new, `slow`) | 2 | QR-06, VER-39 | A grid large enough to fill the waves, run at 1, 2 and 4 workers into a fresh store each time; points per worker-hour over *uncached* members and `efficiency(N) = T(1)/(N·T(N))` are logged with the core count, the pinning setting and the wave widths. Recorded, never gated: completing the sweep is the assertion |

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
- **The distance-field undershoot** of `.knowledge/06` §7.1.1 — see below.

## Open questions

1. **Who owns the P2 distance-field undershoot?** WP10 recorded it, deliberately unfixed: the
   Varadhan field reaches −0.99 nm at the re-entrant pore mouth and `FittedCorrection.evaluate`
   clamps the concentration driver but not `wall_distance_nm`, so `1 − exp(−6.2(d + 0.01))` returns a
   negative diffusivity and mobility there. Either cure — clamping `d` at zero inside the correction,
   or gating on `min d ≥ −0.01 nm` — moves every number a coarse-mesh test reports and needs a
   specification amendment. It is a numerics fix, not a dispatcher's, so this package does not take
   it; **the author's ruling is asked on whether it goes to WP12 or to a package of its own**. What
   WP11 does regardless is carry the NUM-26 route agreement into every dataset row, which is the
   diagnostic that makes it visible in bulk.
2. **Where is QR-06's headline number measured?** "3,675 solves within a day-scale wall clock on 12
   cores" is the specification's figure and this development environment has four. The plan assumes
   the `slow` test measures the *scaling* here and that the 12-core wall-clock figure is taken on the
   author's machine for the end-of-phase report. If that is wrong, the throughput test needs a
   different shape before it is written.
3. **Should a sweep axis be allowed to vary `inputs.mesh`?** The forest degenerates to one-point
   trees and every member is cold, which is correct but silent. A plan-time warning naming the axis
   that defeated the warm start seems right; a refusal seems wrong, since a mesh-convergence sweep is
   a legitimate thing to want and VAL-04 will want one. **Assumed: warn, do not refuse** — confirm.

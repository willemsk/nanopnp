---
type: Specification
title: "5.3.4 Sweep specification and dataset"
description: "Specifies sweeps, sets of runs described by their own declarative document that names a base case and the axes to vary."
---

#### 5.3.4 Sweep specification and dataset

A sweep (FR-24) is a set of runs, not a pipeline stage: it produces no field, and a stage keyed on
thousands of upstream artefacts has no meaningful key. It is specified by its own declarative
document, `schema: nanopnp/sweep/v0.5`, which names a base case by path and the axes to vary. Nothing
is added to the case schema for it: a sweep block inside a case would make that case's
content hash — and every artefact key derived from it — a function of a sweep the run does not
perform.

An **axis** is a named, ordered list of **assignments**, an assignment being a mapping of dotted
case-file paths to values; an axis varying one path may be written as a path and a list of values.
An axis MAY range over `models.molecular` or `models.continuum` (FR-39; WP5.05): each value is a model file, of a kind the base study names (§5.3.1 NOTE on `models:`), that exists beside the base case, and the point resolves the study again under that model, the study's own values and its overrides. A point on such an axis is its own warm-start component, since a model file may move any value a warm-start barrier names, and the plan lists the model files among its input files. A sweep over a study names the study as written, the form `Case.dumps(study=True)` gives, as its base case. A sweep planned in Python (`plan_sweep`) reads a relative model path beside the study file, as `Case.with_` does, and writes it absolute into the plan (REV-189).
An axis MAY range over `variables.<name>` (FR-39; WP5.07; §5.3.1 NOTE on `variables:`): each value is a number in the variable's declared unit, or a definition `{value|expression, unit}`; a name the base case does not define SHALL be refused, naming it. The point reads the case as written again, so the axis moves every field the variable reaches, through other variables too. The warm-start barriers and the wall-size warnings read such an axis as the fields it reaches, not as the variable's path, so an axis over a variable used for a barrier field starts its own warm-start component. An axis over a variable that no field of the base case reads adds a plan warning, since its points are one case. The plan records the `variables:` block and the expressions of the base case as written, and carries them in its digest. Building a member SHALL refuse a base case whose variables or expressions have moved, even where its resolved numbers hash the same, because the barriers, warm-start parents and variable reach were planned from what was written. The rectification pairs (§5.3.1 NOTE on `outputs:`) read assignments only, so a bias set through a variable is not matched.

Before the first solve, `forecast(plan, store=...)` and `Sweep.forecast()` SHALL say which stages each axis moves and how many builds of each stage the plan makes against the store (FR-39, VER-64; §8.2.31 AG5). The forecast keys each point's stages without running one: a stage whose upstream artefact the store does not hold, and the plan has not already counted as built, is keyed from what it reads (§5.5 NOTE on `forecast_parameters`), and it is built unless the store or an earlier point holds its key. An axis **moves** a stage when two points that differ only in that axis's coordinate differ in the stage's identity. For each axis that moves a stage before `solve`, the forecast gives one warning, the stages it moves and the builds of each stage before the solves whose artefact is not its key, as "axis 'radius' moves case, region, mesh, charge, solve, qoi, report; 2 region and 2 mesh and 2 charge builds come before the solves". The warning is advisory: `run_plan` logs it before the first wave and `nanopnp sweep plan` prints it as a `forecast` line and in `--json`, and neither refuses a plan for it. The plan resolves each member once, and the forecast and the run read those members. When the forecast cannot be made, `nanopnp sweep plan --json` gives `forecast: null` and the reason in `forecast_unavailable`. Tier 1: each point's forecast stages equal the stages its walk rebuilds, and a second forecast after the run counts none.

Axes combine as a Cartesian product in declaration order. Each axis MAY declare the index of its
**origin**, defaulting to its first value. A dotted path SHALL be validated against the case schema's
own field tree before any substitution, refusing an unknown component by naming it and the prefix
that does exist, and a value whose type the schema does not accept SHALL be refused there too.
Substitution SHALL re-validate the whole document, so that a path which resolves but produces an
inadmissible case is refused by the same diagnostic a hand-written case would receive (IF-03). Every
point SHALL be substituted, validated and resolved when the plan is built, before any solve: a plan
whose two-thousandth point is inadmissible must fail in seconds rather than after a day of compute.
The plan SHALL also record the content hash of every input file its points name (a mesh, a profile,
a field, a structure or a trajectory), by the path as the case writes it, and carry those hashes in
its own digest: a case's hash covers the path strings and not the bytes behind them, and a path
resolves against the working directory of whoever dispatches. Building a member SHALL refuse a file
whose hash has moved, or which is not there, naming the path and both digests, and reading a plan
file that records no digests SHALL be refused with an instruction to re-plan (CODE_REVIEW_003 CR-5, QR-12).

A point's **identity** is the content hash of its assignment mapping; its **index** is its position
in the plan. The identity keys the collected dataset and the index keys the dispatch, because
inserting one value on one axis renumbers every index after it and a dataset keyed on the index would
relabel results the sweep did not re-run. A member's `name:` SHALL carry its point identity, `name`
reaching the manifest and the run directory and nothing that keys a solve.

Warm starting and independent dispatch are reconciled by a **forest** over the axis grid. The parent
of a point is that point with the last index differing from its axis origin moved one step towards
it; every point therefore has exactly one parent one grid step away, the depth of a point is the sum
of its index distances from the origins, and all points at one depth are mutually independent. A plan
SHALL order its points by depth, so that each wave is a contiguous range of indices a job array can
be submitted over. A member whose parent's stage-10 artefact is not in the store SHALL run the full
NUM-18 ladder and SHALL record that it did, with the reason: a member must be runnable alone, in any
order, on a machine that has seen nothing else, and the warm start is an optimisation the store may
or may not be able to supply.

Members SHALL share one artefact store, which is what makes a neighbour's converged state reachable
at all, and the workspace-locality NOTE above applies to each member individually. Independent
workers SHALL be independent: each worker SHALL be started with the thread counts of the underlying
linear-algebra libraries pinned to one before those libraries are imported, and the pinning SHALL be
recorded, because N workers sharing one thread pool are not N independent workers and QR-06's scaling
claim would otherwise measure the pool.

The collected **dataset** is an artefact, `schema: nanopnp/sweep/v0.5`, written through the canonical
serialisation above, carrying one record per point: its index and identity, its assignments, its
status and — where it failed — the exit class of §3.1, the scalar quantities of interest or their
explicit absence, the run directory, the manifest and solution hashes, the elapsed time, whether it
was served from cache, and the warm-start record. The quantities of a member that did not succeed
SHALL be absent rather than defaulted, QR-06 requiring that a failed member be distinguishable from a
refused one and from one that was never dispatched. A flat tabular export MAY be written beside it
and is derived rather than normative.

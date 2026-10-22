---
type: Specification
title: "5.3.4 Sweep specification and dataset"
description: "Specifies sweeps, sets of runs described by their own declarative document that names a base case and the axes to vary."
---

#### 5.3.4 Sweep specification and dataset

A sweep (FR-24) is a set of runs, not a pipeline stage: it produces no field, and a stage keyed on
thousands of upstream artefacts has no meaningful key. It is specified by its own declarative
document, `schema: nanopnp/sweep/v1`, which names a base case by path and the axes to vary. Nothing
is added to the case schema for it: a sweep block inside a case would make that case's
content hash — and every artefact key derived from it — a function of a sweep the run does not
perform.

An **axis** is a named, ordered list of **assignments**, an assignment being a mapping of dotted
case-file paths to values; an axis varying one path may be written as a path and a list of values.
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

The collected **dataset** is an artefact, `schema: nanopnp/sweep/v1`, written through the canonical
serialisation above, carrying one record per point: its index and identity, its assignments, its
status and — where it failed — the exit class of §3.1, the scalar quantities of interest or their
explicit absence, the run directory, the manifest and solution hashes, the elapsed time, whether it
was served from cache, and the warm-start record. The quantities of a member that did not succeed
SHALL be absent rather than defaulted, QR-06 requiring that a failed member be distinguishable from a
refused one and from one that was never dispatched. A flat tabular export MAY be written beside it
and is derived rather than normative.


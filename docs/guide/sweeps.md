# Sweeps and HPC

A sweep solves one base case at many points: a bias series, a salt series, an ablation over the
model's corrections, or their product (FR-24). It is specified by its own document, `schema:
nanopnp/sweep/v1` (§5.3.4).

## The sweep document

```yaml
schema: nanopnp/sweep/v1
name: iv
base: pore.case.yaml
workers: 4                     # optional; `sweep run --workers` overrides it
axes:
  - name: bias
    path: boundary_conditions.bias_V
    origin: 2
    values: [-0.1, -0.05, 0.05, 0.1]
  - name: salt
    path: electrolyte.concentration_M
    values: [0.1, 0.5, 1.0]
```

- `base` is a case file, relative to the sweep document.
- Each axis varies one dotted case-file path over a list of `values`. An axis may instead give
  `assignments`, a list of mappings that move several paths together. That is how an ablation
  switches a set of corrections at once: see `docs/sweeps/phase1-reference.sweep.yaml`.
- The points are the product of the axes. Each one is a complete case, validated before anything is
  solved. A misspelt path is refused, naming the component that does not exist. A value of the wrong
  type is refused, naming the point. A point the solver would refuse fails when the plan is built,
  not hours into the run.
- `origin` is the index each axis starts from; it defaults to the first value.

## Waves and warm starts

Every point has one **parent**, a point one grid step nearer the origin, and warm-starts from the
parent's converged solution rather than climbing the whole continuation ladder. A point's **wave**
is its distance from the root, and the points of one wave are independent of each other, so a wave
runs in parallel. Put the origin at the easiest point, such as the lowest bias or the lowest salt,
so that every edge of the tree is a small step. If a parent's solution is missing, because it
failed or has not run, the member falls back to the full ladder and records why.

Some axes cannot be warm-started across, because a solution on one side is not a valid starting
point on the other. These are the mesh (`inputs.mesh`, `numerics.mesh`), the element orders, the
stabilisation mode, the physics model and its flow switch, and which electrode is grounded. An axis
over one of these is a **barrier**. Each of its values roots its own tree, which starts from the full
ladder.

## Running a sweep locally

```console
$ nanopnp sweep plan iv.sweep.yaml --store store
$ nanopnp sweep run <the plan path it printed> --store store --workers 4 --csv
```

`sweep plan` writes `plan.json` into `store/sweeps/<name>-<hash>/`, or into `--directory` if you
give one, and prints each wave's index range. `sweep run` solves wave by wave on independent worker
processes, each pinned to one BLAS thread. It then writes the dataset: `dataset.json`, and with
`--csv` a flat `dataset.csv`.

`sweep run` exits `0` once every member has finished and the dataset is written, **even if some
members failed**. At the corners of a hard envelope, non-convergence is an expected result, and the
dataset records each member's own exit class. Pass `--fail-fast` to stop at the first failure
instead.

## Running a sweep on a cluster

The wave ranges `sweep plan` prints are the whole scheduler integration. nanopnp ships no scheduler
library (CON-07). A job array is two lines of your own shell over those ranges: one dependent array
per wave, each element running

```console
$ nanopnp sweep run <plan.json> --store <store> --index <point index>
```

Submit each wave's array counting from 0, and pass the wave's first index to the element, which
adds `$SLURM_ARRAY_TASK_ID` to it. SLURM refuses a task index at or above its `MaxArraySize`, 1001
by default, and a large sweep's point indices run well past that.

A single member dispatched with `--index` exits with **its own** code, which is what the array
branches on (the IF-02 exit NOTE). Once the arrays finish, `nanopnp sweep collect <plan.json> --csv`
builds the dataset from the member records on disk, and any it cannot find are listed as not
dispatched. [Example 05](../_generated/examples/05-clya-reference.md) renders a complete SLURM
submission for the Phase-1 reference sweep.

The members' case paths resolve against the working directory (see [Case files](case-files.md)),
so run the members from the directory the base case's paths are written relative to.

## Rectification

Rectification is a two-point quantity: the current at `+V` against the current at `−V` (NUM-27).
A member cannot compute it, so the collector does. It pairs every two points that differ only in an
exactly opposite bias, and reports each ratio in `dataset.json` with the two members it came from.
A sweep asking for `rectification` whose axes produce no such pair is refused at plan time. `nanopnp
inspect <sweep directory>/dataset.json` prints the ratios.

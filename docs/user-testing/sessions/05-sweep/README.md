# 05 · A sweep over voltage and salt

**Area:** `cli`. **Time:** twenty to forty minutes.

## The task

A pore with its fixed charge on one side conducts differently in the two directions: it
rectifies. You want to see how much, at two salt concentrations and two voltages. Plan a sweep over
both, run it, collect the results and read them.

## You start with

- `charged.case.yaml`: the pore with a ring of negative charge in its cis half, in 0.1 M NaCl at a
  positive bias.
- `cis-ring.field.yaml`: the fixed charge.
- `grid.sweep.yaml`: the sweep. Two axes: the bias, at ±50 and ±100 mV, and the salt, at 0.1 and
  1 M.

Work in this directory.

## Steps

<!-- example: run -->
```console
$ nanopnp sweep plan grid.sweep.yaml --store store --directory iv-grid
$ nanopnp sweep run iv-grid/plan.json --store store --workers 2 --fail-fast --csv
$ nanopnp sweep collect iv-grid/plan.json --csv
$ nanopnp inspect iv-grid/dataset.json
```

1. `sweep plan` checks every point and prints how they are grouped to run.
2. `sweep run` solves the points on two worker processes and writes each point's record. With `--fail-fast` it
   stops, with a non-zero exit, at the first point that does not converge; without it a point that fails is
   only a gap in the table.
3. `sweep collect` rebuilds the dataset from the records on disk.
4. `inspect` reads the dataset: its points, and the rectification ratio of each opposite pair.

## What to expect

- Every point after the first starts from a converged neighbour.
- At 0.1 M the rectification ratio departs from unity, and by more at 100 mV than at 50 mV.
- At 1 M it returns towards unity.

If what you see differs, that is a finding.

## Then try

Make an uncharged copy of the case and sweep it over the same grid. Say what its rectification
should be before you look, then check.

## Record

Log every surprise in `findings.md` as it happens: the command, its output and what you expected.

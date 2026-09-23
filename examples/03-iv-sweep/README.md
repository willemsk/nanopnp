# 03 · An I–V sweep, and a pore that rectifies

**For:** the collaborating computational scientist (P2) comparing the model against a measured
I–V curve.
**Runtime:** about a minute. **Needs:** nanopnp installed, with the `examples` extra for the plot.
**Exercises:** FR-23, FR-24, IF-02, QR-06.

A pore whose fixed charge sits on one side conducts differently in the two directions: it
*rectifies*. This example sweeps the bias across a pore charged on its cis half, and across the
uncharged pore of [example 01](../01-quickstart/README.md) as a control. It then plots both curves.

Run every command from this directory; in a development checkout, put `uv run` in front of each.

## The sweep documents

A sweep is its own document (`schema: nanopnp/sweep/v1`). It names a base case and the axes to vary
by their dotted case-file paths; `charged.sweep.yaml` varies `boundary_conditions.bias_V` over four
values. Every point is a complete case, validated before anything is solved. A misspelt path or an
inadmissible value is refused at plan time, naming the point.

Points are solved in **waves**. Each point warm-starts from a converged neighbour one grid step
nearer the axis origin, and the points of one wave are independent of each other, so a wave can run
in parallel. `nanopnp sweep plan` prints each wave's index range. On a cluster those ranges are the
whole scheduler integration: see [example 05](../05-clya-reference/README.md).

## The commands

<!-- example: run -->
```console
$ nanopnp mesh cylinder --out pore.msh
$ nanopnp sweep plan charged.sweep.yaml --store store --directory iv-charged
$ nanopnp sweep run iv-charged/plan.json --store store --workers 2 --csv
$ nanopnp sweep plan uncharged.sweep.yaml --store store --directory iv-uncharged
$ nanopnp sweep run iv-uncharged/plan.json --store store --workers 2 --csv
$ nanopnp sweep collect iv-charged/plan.json --csv
$ python plot_iv.py iv-charged iv-uncharged
```

- `--directory` puts the plan and its member records somewhere you chose. Without it they go under
  `store/sweeps/<name>-<hash>/`.
- `sweep run --workers 2` solves the members of each wave on two independent processes, with one
  BLAS thread each. It exits `0` once every member has finished and the dataset is written, even if
  a member failed to converge: at the corners of a hard envelope that is an expected result, and
  each member's own exit code is recorded in the dataset (the IF-02 exit NOTE).
- `sweep collect` rebuilds the dataset from whatever member records are on disk. It is how the
  results of a cluster job array come together, and here it is harmless: it rebuilds the same table.
- Each sweep directory holds `dataset.json`, the dataset artefact. It carries every member's
  quantities and the **rectification ratio** of each exactly-opposite bias pair (FR-23). `dataset.csv`
  is a flat export of the per-member rows. Read the ratios with
  `nanopnp inspect iv-charged/dataset.json`.

## What the test asserts

`tests/tier2/test_examples_03_iv_sweep.py` runs the commands above, verbatim, from a copy of this
directory, and checks properties of the model:

- **the uncharged control rectifies to unity**, within the tolerance the solver's route check gates
  on. Reversing the bias maps a z-symmetric, uncharged pore onto its own mirror image, so its
  current reverses exactly. Anything else is a numerical artefact, and a large one would mean the
  sweep machinery, not the physics, manufactured a signal;
- every member of both sweeps exits `0`, and the charged pore's CSV has a current in every row.

The charged pore's ratio is shown by the plot, not asserted. Its size depends on the charge, the
mesh and the salt; that it departs from unity only because the charge breaks the symmetry is what
the control demonstrates.

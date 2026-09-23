# Checked-in sweeps

A sweep is specified by its own document (`schema: nanopnp/sweep/v1`, SPECIFICATION.md
§5.3.4), naming a base case by path and the axes to vary. The ones here are checked in
because they are *evidence*: a sweep reconstructed from prose measures a different grid,
and nobody can tell.

## `phase1-reference`

The throughput datum of §8.3 — 5 physics cases × 35 bias values × 21 salt concentrations,
3,675 solves, which the reference implementation ran in 41 h on 12 cores. It is the QR-06
headline measurement and it is **not** run in the test suite: a day-scale run inside a
package's own gate is not a gate. `tests/tier2/test_sweep_throughput.py` measures the
*scaling* half of QR-06 on a small grid instead, which is what a four-core machine can
honestly measure.

The mesh is not checked in — 44,316 triangles is not a repository file — and is
reproducible from the ClyA profile in `data/geometry/` at the §5.2.2 "Finer" preset, by the
generator of the §3.1 IF-02 NOTE:

```bash
uv run nanopnp mesh reference --out docs/sweeps/clya-reference.msh
```

It gates the mesh on element quality before writing it and prints the content hash the run's
manifest will record. The reference geometry names every group in the solver's vocabulary, so
the case maps nothing: `inputs.mesh.groups: {}`.

Then, from the repository root — `inputs.mesh.path` in the base case resolves against the
process working directory, because the sweep runner never changes directory:

```bash
uv run nanopnp sweep plan docs/sweeps/phase1-reference.sweep.yaml
uv run nanopnp sweep run <the plan path it printed> --csv
```

`sweep plan` enumerates and validates all 3,675 points, resolves every one of them, and
runs the NUM-34 wall-distance gate once on the mesh, before a single solve — so a
misconfiguration fails in seconds rather than at hour twenty-two. It prints the contiguous
index range of each of the 42 waves; a job array is two lines of your own shell over those
ranges, one dependent array per wave, and `nanopnp sweep collect` builds the dataset from
whatever member records arrived.

# 05 · The ClyA reference geometry, and a sweep on a cluster

**For:** method developers (P1) and collaborating computational scientists (P2) working at production
scale. **Runtime:** under an hour on one core for the single case, and a few GB of memory; the
reference sweep is a cluster job.
**Needs:** nanopnp installed, and SLURM for the last step.
**Exercises:** IF-02, FR-17, FR-23, FR-24, QR-06, VAL-03.

Examples 01–04 use an idealised pore. This one uses the **ClyA reference geometry**: the
hand-conditioned contour of the Cytolysin A pore the published ePNP-NS results were computed on,
meshed at the published "Finer" preset (SPECIFICATION.md §5.2.2). It then plans the Phase-1
reference sweep and renders a SLURM submission for it.

Run every command from this directory; in a development checkout, put `uv run` in front of each.

## One frozen case on the reference mesh

<!-- example: run -->
```console
$ nanopnp mesh reference --out clya-reference.msh
$ nanopnp run clya-0.5M-plus50mV.case.yaml --store store --run-dir run
```

`nanopnp mesh reference` takes no geometric flag: the geometry and the mesh preset are fixed by
the specification. The mesh names every group in the solver's vocabulary, so the case maps
nothing (`inputs.mesh.groups: {}`).

`clya-0.5M-plus50mV.case.yaml` is one of the five frozen cases of the Tier-3 comparison against
the reference COMSOL model (§7.4): the validated ePNP-NS model at 0.5 M and +50 mV. It is a copy of
`docs/validation/cases/clya-0.5M-plus50mV.case.yaml` with only the mesh path changed, and a Tier-1
test asserts that the two have the same case identity. The solve takes tens of minutes, not seconds, and
reaches its operating point by the continuation ladder (FR-17): salt and bias are raised in steps,
each warm-started from the last.

## The reference sweep, on a cluster

`docs/sweeps/phase1-reference.sweep.yaml` is the throughput datum of §8.3: five configurations of
the model, from classical PNP-NS to validated ePNP-NS, crossed with 35 biases and 21
concentrations. Planning it checks every point before anything is solved:

<!-- example: plan -->
```console
$ nanopnp sweep plan ../../docs/sweeps/phase1-reference.sweep.yaml --no-mesh-check --store store --directory phase1
$ python render_slurm.py phase1/plan.json --workdir ../.. --store store --out phase1.sh
```

- `sweep plan` enumerates and validates every point, arranges them in waves, and prints each wave's
  index range. `--no-mesh-check` skips the wall-distance gate on the mesh the points would solve
  on. It is there so this step runs anywhere. For a real submission, write the mesh to
  `docs/sweeps/clya-reference.msh` and plan from the repository root without it, so that a
  mesh the gate refuses fails now rather than on the cluster.
- `render_slurm.py` turns the wave ranges into `phase1.sh`, which submits one job array per wave,
  each depending on the one before. It also writes `phase1.member.sbatch`, the job every array
  element runs: `nanopnp sweep run phase1/plan.json --index <point>`. Each array counts from 0
  within its wave and the member adds the wave's first index, because SLURM refuses a task index
  at or above its `MaxArraySize` (1001 by default) and this sweep's indices run to 3,674. A
  member's exit code is its own (the IF-02 exit NOTE). The dependency is `afterany`, because a member that fails to
  converge at a hard corner is a result, not a broken dispatch, and its children fall back to the
  full ladder and record why. `--workdir` is where the members run. The base case names its mesh
  from the repository root, so that is the working directory here.
- Review both files, set your account and partition, then `bash phase1.sh` on the login node.
  When the arrays finish, `nanopnp sweep collect phase1/plan.json --csv` builds the dataset from
  the member records.

nanopnp ships no scheduler library and never will (CON-07). The wave ranges are the whole
integration, and `render_slurm.py` is two loops over them: adapt it to PBS or LSF in minutes.

## What the tests assert

- **Tier 1** (`tests/tier1/test_examples_plan.py`, every push): the `plan` block runs verbatim and
  enumerates the sweep's points in waves, exactly as §8.3 and the sweep's own README specify; the
  rendered submission has one job array per wave, and together they cover every point once, in
  order; this directory's case has the frozen case's identity.
- **Tier 2, slow** (`tests/tier2/test_examples_05_clya_reference.py`, recorded, not gated): the
  `run` block runs verbatim, exits `0`, and the two current-extraction routes of FR-23 agree to the
  tolerance the solver gates on.

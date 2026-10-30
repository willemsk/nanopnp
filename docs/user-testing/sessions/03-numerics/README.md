# 03 · The numerics: mesh refinement, and a refused mesh

**Area:** `numerics`. **Time:** twenty to forty minutes.

## The task

Before you trust a current, check that the mesh does not decide it. Refine the mesh at the pore
wall in two steps and see whether the current settles. Then try a mesh too coarse for the model,
and see what the program says.

## You start with

- `wall-035.case.yaml`, `wall-025.case.yaml`, `wall-0175.case.yaml`: the same uncharged pore in
  0.1 M NaCl, each with its own element size at the wall (`numerics.mesh.wall_h_nm`).
- `wall-100.case.yaml`: the same case, with a coarse wall (1 nm).

Work in this directory.

## Steps

<!-- example: run -->
```console
$ nanopnp run wall-035.case.yaml --store store --run-dir run-wall-035
$ nanopnp run wall-025.case.yaml --store store --run-dir run-wall-025
$ nanopnp run wall-0175.case.yaml --store store --run-dir run-wall-0175
$ nanopnp inspect run-wall-0175
```

The refusal:

<!-- example: refused -->
```console
$ nanopnp run wall-100.case.yaml --store store --run-dir run-wall-100
```

1. `numerics.mesh.wall_h_nm` sets the element size at the pore wall. The first three cases refine it.
2. The three runs mesh the pore once each. Compare their currents.
3. `inspect` reads the finest run back.
4. The refused run has the coarse wall. Read what it says.

## What to expect

- The current changes less between the two finer meshes than between the two coarser ones.
- The manifest records the stabilisation mode and each rung of the continuation ladder.
- The refusal names the gate that stopped the run, the quantity it checked, where, and the setting
  that would change it. The program makes the coarse mesh without complaint; the refusal is at the
  run.

If what you see differs, that is a finding.

## Then try

Refine the mesh away from the wall instead: in a copy of the finest case, set a smaller `numerics.mesh.maxh_nm` and run it. Decide whether the current is converged.

## Record

Log every surprise in `findings.md` as it happens: the command, its output and what you expected.

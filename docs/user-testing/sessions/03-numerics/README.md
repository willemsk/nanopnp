# 03 · The numerics: mesh refinement, and a refused mesh

**Area:** `numerics`. **Time:** twenty to forty minutes.

## The task

Before you trust a current, check that the mesh does not decide it. Refine the mesh at the pore
wall in two steps and see whether the current settles. Then try a mesh too coarse for the model,
and see what the program says.

## You start with

- `wall-035.case.yaml`, `wall-025.case.yaml`, `wall-0175.case.yaml`: the same uncharged pore in
  0.1 M NaCl, each reading its own mesh.
- `coarse.case.yaml`: the same case, reading a mesh with a coarse wall.

Work in this directory. The cases name `wall-*.msh` files, which the first block writes.

## Steps

<!-- example: run -->
```console
$ nanopnp mesh cylinder --wall-h-nm 0.35 --out wall-035.msh
$ nanopnp mesh cylinder --wall-h-nm 0.25 --out wall-025.msh
$ nanopnp mesh cylinder --wall-h-nm 0.175 --out wall-0175.msh
$ nanopnp mesh cylinder --wall-h-nm 1.0 --out wall-100.msh
$ nanopnp run wall-035.case.yaml --store store --run-dir run-wall-035
$ nanopnp run wall-025.case.yaml --store store --run-dir run-wall-025
$ nanopnp run wall-0175.case.yaml --store store --run-dir run-wall-0175
$ nanopnp inspect run-wall-0175
```

The refusal:

<!-- example: refused -->
```console
$ nanopnp run coarse.case.yaml --store store --run-dir run-coarse
```

1. `--wall-h-nm` sets the element size at the pore wall. The first three meshes refine it.
2. The three runs read one mesh each. Compare their currents.
3. `inspect` reads the finest run back.
4. The refused run reads the coarse mesh. Read what it says.

## What to expect

- The current changes less between the two finer meshes than between the two coarser ones.
- The manifest records the stabilisation mode and each rung of the continuation ladder.
- The refusal names the gate that stopped the run, the quantity it checked, where, and the setting
  that would change it. The program makes the coarse mesh without complaint; the refusal is at the
  run.

If what you see differs, that is a finding.

## Then try

Refine the mesh away from the wall instead: make a mesh with a smaller `--maxh-nm` and the finest wall, point a copy of a case at it and run it. Decide whether the current is converged.

## Record

Log every surprise in `findings.md` as it happens: the command, its output and what you expected.

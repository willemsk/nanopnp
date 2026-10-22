# 06 · From a PDB entry to a solve

Example 07's 2WCD case through every stage, one block of cells each, from the deposited structure to
the quantities of interest: the structure, the density, the symmetry reduction, the contour, the
region, the mesh, the protonation, the charge, the materials, the solve and the quantities of
interest. A block shows what the stage is, lists its settings as plain values to edit (the point
group, the grid spacing, the isolevel, the membrane, the mesh size, the pH and force field, the
smearing, the salt, the bias, the outputs), runs the stage and shows what it stored. A stage reads
everything before it from the store and refuses to recompute it, so run the blocks in order. The
walk takes about eleven minutes from an empty store, nearly all of it the solve. With nanopnp
installed with the `notebook` extra, run every command from this directory; in a development
checkout, put `uv run` in front of each.

<!-- example: run -->
```console
$ python notebook.py
```

The structure block prepares its input with example 06's `prepare.py`, so nothing is run
beforehand. The command runs the notebook headless and exits `0` once every cell has run. To work
in it, open it in the browser:

```console
$ marimo edit notebook.py
```

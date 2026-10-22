# 01 · Geometry

Example 06's case, walked from the deposited structure to the mesh, one block of cells per stage: the
structure, the density, the symmetry reduction, the contour, the region and the mesh. A block shows what
the stage is, lists its settings as plain values to edit (the point group, the grid spacing, the isolevel,
the membrane, the mesh size), runs the stage and shows what it stored. A stage reads everything before it
from the store and refuses to recompute it, so run the blocks in order. With nanopnp installed with the
`notebook` extra, run every command from this directory; in a development checkout, put `uv run` in front
of each.

<!-- example: run -->
```console
$ python notebook.py
```

The structure block prepares the entry as example 06 does, so nothing is run beforehand. The command runs
the notebook headless and exits `0` once every cell has run. To work in it, open it in the browser:

```console
$ marimo edit notebook.py
```

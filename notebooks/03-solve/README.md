# 03 · The solve

Example 02's charged pore, one block of cells per stage at the end of the pipeline: the ePNP-NS solve
(the potential, the concentrations, the velocity and the pressure, and how the Newton iteration
converged) and the quantities of interest read off it. A block shows what the stage is, lists its
settings as plain values to edit (the bias, the model, the stabilisation, the reach of the wall
functions, the outputs), runs the stage and shows what it stored. The notebook starts at the solve, so a
set-up cell writes the pore mesh and runs the stages before it; each block then reads everything before
it from the store and refuses to recompute it, so run the blocks in order. With nanopnp installed with
the `notebook` extra, run every command from this directory; in a development checkout, put `uv run` in
front of each.

<!-- example: run -->
```console
$ python notebook.py
```

The set-up cell writes the pore mesh the case reads, so nothing is run beforehand. The command runs the
notebook headless and exits `0` once every cell has run. To work in it, open it in the browser:

```console
$ marimo edit notebook.py
```

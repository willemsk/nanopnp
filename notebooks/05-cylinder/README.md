# 05 · The cylindrical pore, end to end

Example 03's charged pore through every stage, one block of cells each: the mesh, the charge, the
materials, the solve and the quantities of interest, and then an I-V sweep of the same case. A block
shows what the stage is, lists its settings as plain values to edit (the cylinder's size, the field the
charge is read from, the salt and the correction models, the bias, the outputs, the sweep's values), runs
the stage and shows what it stored. A stage reads everything before it from the store and refuses to
recompute it, so run the blocks in order. With nanopnp installed with the `notebook` extra, run every
command from this directory; in a development checkout, put `uv run` in front of each.

<!-- example: run -->
```console
$ python notebook.py
```

The mesh block writes the mesh the case reads, so nothing is run beforehand. The command runs it
headless and exits `0` once every cell has run. To work in it, open it in the browser:

```console
$ marimo edit notebook.py
```

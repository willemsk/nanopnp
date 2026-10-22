# 02 · Charge and materials

Example 07's case, one block of cells per stage after the mesh: the protonation of each residue, the
charge deposited on the mesh, and the materials with their correction functions. A block shows what the
stage is, lists its settings as plain values to edit (the pH and force field, the smearing, the salt and
the correction models), runs the stage and shows what it stored. The notebook starts after the mesh, so a
set-up cell prepares the structure and runs the stages before it; each block then reads everything before
it from the store and refuses to recompute it, so run the blocks in order. With nanopnp installed with the
`notebook` extra, run every command from this directory; in a development checkout, put `uv run` in front
of each.

<!-- example: run -->
```console
$ python notebook.py
```

The set-up cell prepares the entry as example 07 does, so nothing is run beforehand. The command runs the
notebook headless and exits `0` once every cell has run. To work in it, open it in the browser:

```console
$ marimo edit notebook.py
```

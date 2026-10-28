# 06 · From a PDB entry to a solve

The 2WCD pore of notebooks 01 and 02, solved with the validated ePNP-NS model at a salt, bias and
stabilisation set in a form. The notebook shows the current and the conductance, the figures of the stages
before the solve and of the Newton history, each solved field as its own figure (the potential in mV with its
range on a slider, the concentrations against the bulk, the flow), profiles along and across the pore on
sliders, and every quantity of interest in a table. The case is built by the same `Case.from_structure(...)`
call as notebooks 01 and 02, so the stages up to the materials come from the store the six notebooks share,
`notebooks/.store` unless `$NANOPNP_STORE` names another. From an empty store the walk takes about eleven
minutes, nearly all of it the solve; the mesh is four times coarser than the default sizes, for runtime only.
With nanopnp installed with the `notebook` extra, run every command from this directory; in a development
checkout, put `uv run` in front of each.

<!-- example: run -->
```console
$ python notebook.py
```

The command runs the notebook headless with its default settings and exits `0` once every cell has run.
To work in it, open it in the browser:

```console
$ marimo edit notebook.py
```

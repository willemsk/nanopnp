# 03 · The solve

Example 02's charged pore, solved with the ePNP-NS model: the potential, the concentrations, the
velocity and the pressure, and how the Newton iteration converged. A slider sets the bias. With
nanopnp installed with the `notebook` extra, run every command from this directory; in a development
checkout, put `uv run` in front of each.

<!-- example: run -->
```console
$ nanopnp mesh cylinder --out ../../examples/02-charged-pore/pore.msh
$ python notebook.py
```

The first command writes the pore mesh the case reads. The second runs the notebook headless. To work
in it, open it in the browser:

```console
$ marimo edit notebook.py
```

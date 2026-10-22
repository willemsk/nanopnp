# 03 · The solve

Example 02's charged pore, solved with the ePNP-NS model: the potential, the concentrations, the
velocity and the pressure, and how the Newton iteration converged. A slider sets the bias. With
nanopnp installed with the `notebook` extra, run every command from this directory; in a development
checkout, put `uv run` in front of each.

<!-- example: run -->
```console
$ python notebook.py
```

The notebook's first cell writes the pore mesh the case reads, so nothing is run beforehand. The command
runs it headless. To work in it, open it in the browser:

```console
$ marimo edit notebook.py
```

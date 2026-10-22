# 04 · The sweep

Example 03's charged pore solved at four biases, as a sweep: a base case and the axes to vary, by their
case-file paths. The notebook lists the settings as plain values to edit (the pore mesh's size, the salt,
the model, the outputs, the sweep's values and its `origin`), writes the sweep document, runs it and shows
each quantity against the bias, with the row of every point beside it. A sweep computes its own points, so
the notebook needs no set-up beyond the pore mesh. With nanopnp installed with the `notebook` extra, run
every command from this directory; in a development checkout, put `uv run` in front of each.

<!-- example: run -->
```console
$ python notebook.py
```

The mesh cell writes the pore mesh the case reads, so nothing is run beforehand. The command runs the
notebook headless and exits `0` once every cell has run. To work in it, open it in the browser:

```console
$ marimo edit notebook.py
```

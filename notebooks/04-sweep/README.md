# 04 · The sweep

Example 03's charged I-V sweep: each quantity against the bias, and the row of any one point, which a
selector chooses. With nanopnp installed with the `notebook` extra, run every command from this
directory; in a development checkout, put `uv run` in front of each.

<!-- example: run -->
```console
$ nanopnp mesh cylinder --out ../../examples/03-iv-sweep/pore.msh
$ python notebook.py
```

The first command writes the pore mesh the case reads. The second runs the notebook headless. To work
in it, open it in the browser:

```console
$ marimo edit notebook.py
```

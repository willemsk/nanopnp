# 04 · The sweep

A charged cylindrical pore, its fixed charge the cis ring of example 03, solved at four biases with one call,
`sweep(case, axis="bias_V", values=...)`. Each point warm-starts from a converged neighbour one step nearer
the bias solved first, and opposite biases pair into a rectification ratio. The notebook shows each quantity
against the bias, with the row of every point beside it. Edit the salt or the biases and press **Sweep**;
the sweep's files and every point's artefacts go to the store the six notebooks share, `notebooks/.store`
unless `$NANOPNP_STORE` names another. With nanopnp installed with the `notebook` extra, run every command
from this directory; in a development checkout, put `uv run` in front of each.

<!-- example: run -->
```console
$ python notebook.py
```

The command runs the notebook headless with its default settings and exits `0` once every cell has run.
To work in it, open it in the browser:

```console
$ marimo edit notebook.py
```

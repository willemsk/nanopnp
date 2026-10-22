# 06 · From a PDB entry to a solve

Example 07's 2WCD case through every stage, from the deposited structure to the quantities of interest. Sliders set the bias and the salt concentration; a Run button starts the walk, which takes minutes the first time, and a selector chooses the stage shown. With nanopnp installed with the `notebook` extra, run every command from this directory; in a
development checkout, put `uv run` in front of each.

<!-- example: run -->
```console
$ python notebook.py
```

The notebook's first cell prepares its input, so nothing is run beforehand. The command runs it
headless and exits `0` once every cell has run. To work in it, open it in the browser:

```console
$ marimo edit notebook.py
```

# 01 · Geometry

Example 06's case, walked from the structure to the mesh, one picture per stage. A selector chooses
the stage shown. With nanopnp installed with the `notebook` extra, run every command from this
directory; in a development checkout, put `uv run` in front of each.

<!-- example: run -->
```console
$ python ../../examples/06-pdb-to-mesh/prepare.py ../../tests/data/structures/2wcd.pdb.gz ../../examples/06-pdb-to-mesh/2wcd-prepared.pdb
$ python notebook.py
```

The first command prepares the entry as example 06 does. The second runs the notebook headless and
exits `0` once every cell has run. To work in it, open it in the browser:

```console
$ marimo edit notebook.py
```

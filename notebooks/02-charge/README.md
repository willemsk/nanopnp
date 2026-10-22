# 02 · Charge and materials

Example 07's case, walked to the materials stage: the protonation of each residue, the charge and
permittivity grids, and the correction functions. A selector chooses the stage shown, and a slider
sets the salt concentration. With nanopnp installed with the `notebook` extra, run every command from
this directory; in a development checkout, put `uv run` in front of each.

<!-- example: run -->
```console
$ python ../../examples/06-pdb-to-mesh/prepare.py ../../tests/data/structures/2wcd.pdb.gz ../../examples/07-pdb-to-charged-run/2wcd-prepared.pdb
$ python notebook.py
```

The first command prepares the entry as example 07 does. The second runs the notebook headless. To
work in it, open it in the browser:

```console
$ marimo edit notebook.py
```

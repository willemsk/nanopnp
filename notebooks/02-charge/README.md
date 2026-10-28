# 02 · Charge and materials

The 2WCD pore of notebook 01, charged: the structure protonated by PDB2PQR and PROPKA at a pH and force field
set in a form, the atoms' charges deposited on the mesh, drawn about zero with the solid's edge, and the
electrolyte's correction functions at a salt set in a second form. The case is built by the same
`Case.from_structure(...)` call as notebooks 01 and 06, so the stages they share come from the store the six
notebooks share, `notebooks/.store` unless `$NANOPNP_STORE` names another. From an empty store the notebook
first prepares the entry and walks it to the mesh, about a minute. In a running notebook each figure pans and
zooms.
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

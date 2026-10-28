# 01 · Geometry

The cytolysin A pore as deposited in the Protein Data Bank (2WCD), prepared with `nanopnp.structure.orient_pore`
and taken through the geometry stages with `Case.from_structure(...)`: the structure, the density, the symmetry
reduction, the contour, the region and the mesh. The preparation's choices are yours and sit in a form: the
chains, which end faces *cis*, and the residues whose C-alpha centroid places the membrane. A slider sets the
contour's isolevel and redraws the contour, the region and the mesh in a few seconds. Every run takes the stages
it does not change from the store the six notebooks share, `notebooks/.store` unless `$NANOPNP_STORE` names
another; notebooks 02 and 06 build the same case, so they share these stages.
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

# 03 · The solve

A charged cylindrical pore built in one line of Python, `Case.cylinder(...)`, and solved with the validated
ePNP-NS model; its fixed charge is the ring of example 02. The notebook shows the current and the
conductance, each solved field as its own figure (the potential in mV and the concentrations against the
bulk, each coloured about zero, and the axial flow with its streamlines), profiles along and across the pore
at a radius and a height set by sliders, and every quantity of interest. Edit the pore, the salt, the bias or
the stabilisation and press **Solve**: the run takes every stage it does not change from the store the six
notebooks share, `notebooks/.store` unless `$NANOPNP_STORE` names another. The views and the sliders redraw
at once, from the fields sampled once per solve.
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

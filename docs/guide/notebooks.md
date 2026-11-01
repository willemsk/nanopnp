# Notebooks

This page lists the six interactive notebooks that ship with the repository and says how to run them.

The notebooks are [marimo](https://marimo.io) documents in the `notebooks/` directory of the repository. They
need the `notebook` extra, which brings in `plot` and marimo. They share one store, `notebooks/.store`, unless
`$NANOPNP_STORE` names another. This site lists them and does not render them.

| Notebook | What it shows | README |
|---|---|---|
| `01-geometry` | The 2WCD pore taken through the geometry stages, from the structure to the mesh, with the contour and the mesh size set by sliders. | [01-geometry](https://github.com/willemsk/nanopnp/blob/main/notebooks/01-geometry/README.md) |
| `02-charge` | The same pore protonated and charged, with the deposited charge on the mesh and the electrolyte's correction functions. | [02-charge](https://github.com/willemsk/nanopnp/blob/main/notebooks/02-charge/README.md) |
| `03-solve` | A charged cylindrical pore built with `Case.cylinder(...)` and solved, with its fields, profiles and quantities of interest. | [03-solve](https://github.com/willemsk/nanopnp/blob/main/notebooks/03-solve/README.md) |
| `04-sweep` | A charged cylindrical pore solved at several biases with one `session.sweep(...)` call, with its rectification ratio. | [04-sweep](https://github.com/willemsk/nanopnp/blob/main/notebooks/04-sweep/README.md) |
| `05-cylinder` | A cylindrical pore end to end: its mesh, its solve, its profiles and its I-V sweep. | [05-cylinder](https://github.com/willemsk/nanopnp/blob/main/notebooks/05-cylinder/README.md) |
| `06-2wcd` | The 2WCD pore taken from the PDB entry to a solve, with the figures of every stage and the solved fields. | [06-2wcd](https://github.com/willemsk/nanopnp/blob/main/notebooks/06-2wcd/README.md) |

Each README gives the notebook's settings and what a first run costs. The README links point to GitHub because
`notebooks/` lies outside this site.

## Run a notebook

Run both commands from the notebook's directory. In a development checkout, put `uv run` in front of each.

```bash
python notebook.py
marimo edit notebook.py
```

The first runs the notebook as a script, headless, with its default settings. The second opens it in the browser
to work in.

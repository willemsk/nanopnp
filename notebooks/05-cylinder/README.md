# 05 · The cylindrical pore, end to end

A charged cylindrical pore in four steps, each built on `Case.cylinder(...)`: its mesh, by element size and,
in the lumen, by quality with the double-layer target λ_D/5 drawn to scale, its wall sized at the mesh
command's fixed 0.35 nm or at λ_D/5 of the salt; the ePNP-NS solve, each field its own figure, the
potential's colour range set by a slider; profiles along and across the pore at a radius and a height set by sliders; and an I-V sweep of
the same pore, `sweep(case, axis="bias_V", values=[...])`, with its rectification ratios and conductance. The
fixed charge is the ring near the cis mouth of example 03, so the pore rectifies. A step that computes waits for its button and runs only the stages
its settings change, taking the rest from the store the six notebooks share, `notebooks/.store` unless
`$NANOPNP_STORE` names another. With nanopnp installed with the `notebook` extra, run every command from this
directory; in a development checkout, put `uv run` in front of each.

<!-- example: run -->
```console
$ python notebook.py
```

The command runs the notebook headless with its default settings and exits `0` once every cell has run.
To work in it, open it in the browser:

```console
$ marimo edit notebook.py
```

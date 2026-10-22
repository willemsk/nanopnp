import marimo

app = marimo.App(width="medium")


@app.cell
def _():
    import os
    from pathlib import Path

    import marimo as mo

    from nanopnp import Case

    example = (
        Path(__file__).resolve().parent / ".." / ".." / "examples" / "02-charged-pore"
    ).resolve()
    os.chdir(example)
    case = Case.load("epnpns.case.yaml", store=example / "store", write=False)
    return case, example, mo


@app.cell
def _(mo):
    mo.md(
        """
        # The ePNP-NS solve

        Example 02's charged pore. Change the bias and the solve re-runs, warm from
        nothing; the figure shows the fields and how the Newton iteration converged.
        """
    )
    return


@app.cell
def _(example, mo):
    from nanopnp.cli import main

    mesh = example / "pore.msh"
    if not mesh.exists():
        main(["mesh", "cylinder", "--out", str(mesh)])
    mo.md(f"**Step 0.** Wrote `{mesh.name}` with `nanopnp mesh cylinder`, the mesh the case reads.")
    return (mesh,)


@app.cell
def _(case, mo):
    bias = mo.ui.slider(-0.2, 0.2, step=0.05, value=case["bias_V"], label="Bias (V)")
    bias
    return (bias,)


@app.cell
def _(bias, case, mesh):
    result = case.run(bias_V=bias.value)
    return (result,)


@app.cell
def _(mo):
    size = mo.ui.slider(0.5, 3.0, step=0.25, value=1.5, label="Figure size")
    zoom = mo.ui.switch(label="Zoom and pan")
    mo.hstack([size, zoom])
    return size, zoom


@app.cell
def _(mo, result, size, zoom):
    _figure = result.figure("solve", scale=size.value)
    mo.mpl.interactive(_figure) if zoom.value else _figure
    return


@app.cell
def _(result):
    result
    return


if __name__ == "__main__":
    app.run()

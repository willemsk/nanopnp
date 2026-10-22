import marimo

app = marimo.App(width="medium")


@app.cell
def _():
    import os
    from pathlib import Path

    import marimo as mo

    from nanopnp import Case, Store
    from nanopnp.sweep.collect import collect
    from nanopnp.sweep.plan import plan_from_document, write_plan
    from nanopnp.sweep.run import run_plan

    example = (Path(__file__).resolve().parent / ".." / ".." / "examples" / "03-iv-sweep").resolve()
    os.chdir(example)
    case = Case.load("charged.case.yaml", store=example / "store", write=False)
    return Store, case, collect, example, mo, plan_from_document, run_plan, write_plan


@app.cell
def _(mo):
    mo.md(
        """
        # The cylindrical pore, end to end

        Example 03's charged pore: its mesh, the charge on it, the materials, the
        ePNP-NS solve and its quantities of interest, and then an I-V sweep over the
        same case. Change the bias or the salt and the stages re-run; the store keeps
        every stage a change does not touch.
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
    stage = mo.ui.dropdown(
        ["mesh", "charge", "materials", "solve", "qoi"], value="solve", label="Stage"
    )
    bias = mo.ui.slider(-0.1, 0.1, step=0.05, value=case["bias_V"], label="Bias (V)")
    salt = mo.ui.slider(0.05, 1.0, step=0.05, value=case["concentration_M"], label="NaCl (M)")
    mo.hstack([stage, bias, salt])
    return bias, salt, stage


@app.cell
def _(bias, case, mesh, salt):
    result = case.run(
        upto="qoi",
        bias_V=bias.value,
        concentration_M=salt.value,
        outputs=["current", "transport_numbers"],
    )
    return (result,)


@app.cell
def _(mo):
    size = mo.ui.slider(0.5, 3.0, step=0.25, value=1.5, label="Figure size")
    zoom = mo.ui.switch(label="Zoom and pan")
    mo.hstack([size, zoom])
    return size, zoom


@app.cell
def _(mo, result, size, stage, zoom):
    _figure = result.figure(stage.value, scale=size.value)
    mo.mpl.interactive(_figure) if zoom.value else _figure
    return


@app.cell
def _(result):
    result
    return


@app.cell
def _(mo):
    mo.md(
        """
        ## The I-V sweep

        Example 03's sweep of this case: four biases, each warm-started from a
        converged neighbour. Pick a point to read its row.
        """
    )
    return


@app.cell
def _(Store, collect, example, mesh, plan_from_document, run_plan, write_plan):
    directory = example / "iv-charged"
    plan = plan_from_document(example / "charged.sweep.yaml")
    write_plan(plan, directory)
    run_plan(plan, directory, store=Store(example / "store"))
    dataset = collect(plan, directory)
    return (dataset,)


@app.cell
def _(dataset, mo, size, zoom):
    from nanopnp.plot import figure as _draw

    _curves = _draw(dataset, scale=size.value)
    mo.mpl.interactive(_curves) if zoom.value else _curves
    return


@app.cell
def _(dataset, mo):
    rows = dataset.summary["rows"]
    point = mo.ui.dropdown(
        {str(index): index for index in range(len(rows))}, value="0", label="Point"
    )
    point
    return point, rows


@app.cell
def _(mo, point, rows):
    mo.json(rows[point.value])
    return


@app.cell
def _(dataset):
    dataset
    return


if __name__ == "__main__":
    app.run()

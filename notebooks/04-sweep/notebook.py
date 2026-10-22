import marimo

app = marimo.App(width="medium")


@app.cell
def _():
    import os
    from pathlib import Path

    import marimo as mo

    from nanopnp.io.store import Store
    from nanopnp.sweep.collect import collect
    from nanopnp.sweep.plan import plan_from_document, write_plan
    from nanopnp.sweep.run import run_plan

    example = (Path(__file__).resolve().parent / ".." / ".." / "examples" / "03-iv-sweep").resolve()
    os.chdir(example)
    return Store, collect, example, mo, plan_from_document, run_plan, write_plan


@app.cell
def _(mo):
    mo.md(
        """
        # An I-V sweep

        Example 03's charged pore, solved at four biases. The figure plots each
        quantity against the bias; pick a point to read its row.
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
def _(Store, collect, example, mesh, plan_from_document, run_plan, write_plan):
    directory = example / "iv-charged"
    plan = plan_from_document(example / "charged.sweep.yaml")
    write_plan(plan, directory)
    run_plan(plan, directory, store=Store(example / "store"))
    dataset = collect(plan, directory)
    return (dataset,)


@app.cell
def _(mo):
    size = mo.ui.slider(0.5, 3.0, step=0.25, value=1.5, label="Figure size")
    zoom = mo.ui.switch(label="Zoom and pan")
    mo.hstack([size, zoom])
    return size, zoom


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

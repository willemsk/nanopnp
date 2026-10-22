import marimo

app = marimo.App(width="medium")


@app.cell
def _():
    import os
    from pathlib import Path

    import marimo as mo

    from nanopnp import Case

    example = (
        Path(__file__).resolve().parent / ".." / ".." / "examples" / "07-pdb-to-charged-run"
    ).resolve()
    os.chdir(example)
    case = Case.load("2wcd.case.yaml", store=example / "store", write=False)
    return case, example, mo


@app.cell
def _(mo):
    mo.md(
        """
        # Charge and materials

        Example 07's case, walked to the materials stage. Change the salt concentration
        to see the correction functions move; pick a stage to see what it stored.
        """
    )
    return


@app.cell
def _(example, mo):
    import importlib.util

    script = example.parent / "06-pdb-to-mesh" / "prepare.py"
    prepared = example / "2wcd-prepared.pdb"
    if not prepared.exists():
        # Preparing a structure is the user's job, not the pipeline's: stage 1 refuses an
        # unaligned file, so the notebook does it here, as example 06's script does.
        spec = importlib.util.spec_from_file_location("prepare", script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.prepare(
            example.parents[1] / "tests" / "data" / "structures" / "2wcd.pdb.gz", prepared
        )
    mo.md(
        f"**Step 0.** Prepared `{prepared.name}` with `{script.name}`: "
        "the dodecamer, its pore axis on z, *cis* up."
    )
    return (prepared,)


@app.cell
def _(case, mo):
    stage = mo.ui.dropdown(["protonation", "charge", "materials"], value="materials", label="Stage")
    salt = mo.ui.slider(0.05, 1.0, step=0.05, value=case["concentration_M"], label="NaCl (M)")
    mo.hstack([stage, salt])
    return salt, stage


@app.cell
def _(case, prepared, salt):
    result = case.run(upto="materials", concentration_M=salt.value)
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


if __name__ == "__main__":
    app.run()

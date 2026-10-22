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
        # From a PDB entry to a solve

        Example 07's case, from the deposited 2WCD entry through every stage to the
        quantities of interest. The whole walk takes minutes the first time, so it runs
        when you press Run (and always when the notebook runs headless); the store
        keeps every stage a change does not touch. Pick any stage to see its figure.
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
    stages = [
        "structure",
        "density",
        "symmetry",
        "contour",
        "region",
        "mesh",
        "protonation",
        "charge",
        "materials",
        "solve",
        "qoi",
    ]
    stage = mo.ui.dropdown(stages, value="solve", label="Stage")
    bias = mo.ui.slider(-0.1, 0.1, step=0.05, value=case["bias_V"], label="Bias (V)")
    salt = mo.ui.slider(0.05, 1.0, step=0.05, value=case["concentration_M"], label="NaCl (M)")
    run = mo.ui.run_button(label="Run")
    mo.hstack([stage, bias, salt, run])
    return bias, run, salt, stage


@app.cell
def _(bias, case, mo, prepared, run, salt):
    # Headless, nobody can press the button, and the notebook exists to be run.
    mo.stop(not (run.value or mo.app_meta().mode == "script"), mo.md("Press **Run**."))
    result = case.run(upto="qoi", bias_V=bias.value, concentration_M=salt.value)
    return (result,)


@app.cell
def _(result, stage):
    result.figure(stage.value)
    return


@app.cell
def _(result):
    result
    return


if __name__ == "__main__":
    app.run()

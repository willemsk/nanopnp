import marimo

app = marimo.App(width="medium")


@app.cell
def _():
    import os
    from pathlib import Path

    import marimo as mo

    from nanopnp.io.case import dumps_case
    from nanopnp.io.store import Store
    from nanopnp.pipeline.case import load_case
    from nanopnp.pipeline.run import run_document

    example = (
        Path(__file__).resolve().parent / ".." / ".." / "examples" / "07-pdb-to-charged-run"
    ).resolve()
    os.chdir(example)
    document = load_case("2wcd.case.yaml")
    return Store, document, dumps_case, example, mo, run_document


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
def _(document, mo):
    stage = mo.ui.dropdown(["protonation", "charge", "materials"], value="materials", label="Stage")
    salt = mo.ui.slider(
        0.05, 1.0, step=0.05, value=document.electrolyte.concentration_M, label="NaCl (M)"
    )
    mo.hstack([stage, salt])
    return salt, stage


@app.cell
def _(Store, document, dumps_case, example, prepared, run_document, salt):
    edited = document.model_copy(
        update={
            "electrolyte": document.electrolyte.model_copy(update={"concentration_M": salt.value})
        }
    )
    result = run_document(
        edited,
        case_text=dumps_case(edited),
        store=Store(example / "store"),
        upto="materials",
        write=False,
    )
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

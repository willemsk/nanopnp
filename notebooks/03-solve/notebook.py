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
        Path(__file__).resolve().parent / ".." / ".." / "examples" / "02-charged-pore"
    ).resolve()
    os.chdir(example)
    document = load_case("epnpns.case.yaml")
    return Store, document, dumps_case, example, mo, run_document


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
def _(document, mo):
    bias = mo.ui.slider(
        -0.2, 0.2, step=0.05, value=document.boundary_conditions.bias_V, label="Bias (V)"
    )
    bias
    return (bias,)


@app.cell
def _(Store, bias, document, dumps_case, example, mesh, run_document):
    edited = document.model_copy(
        update={
            "boundary_conditions": document.boundary_conditions.model_copy(
                update={"bias_V": bias.value}
            )
        }
    )
    result = run_document(
        edited, case_text=dumps_case(edited), store=Store(example / "store"), write=False
    )
    return (result,)


@app.cell
def _(result):
    result
    return


if __name__ == "__main__":
    app.run()

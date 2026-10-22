import marimo

app = marimo.App(width="medium")


@app.cell
def _():
    import os
    from pathlib import Path

    import marimo as mo

    from nanopnp.io.store import Store
    from nanopnp.pipeline.run import run_case

    example = (
        Path(__file__).resolve().parent / ".." / ".." / "examples" / "06-pdb-to-mesh"
    ).resolve()
    os.chdir(example)
    return Store, example, mo, run_case


@app.cell
def _(mo):
    mo.md(
        """
        # From a PDB entry to a mesh

        Example 06's case, walked from the structure to the mesh. Pick a stage to see
        what it stored.
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
def _(mo):
    stage = mo.ui.dropdown(
        ["structure", "density", "symmetry", "contour", "region", "mesh"],
        value="mesh",
        label="Stage",
    )
    stage
    return (stage,)


@app.cell
def _(Store, example, prepared, run_case):
    result = run_case("2wcd.case.yaml", store=Store(example / "store"), upto="mesh", write=False)
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

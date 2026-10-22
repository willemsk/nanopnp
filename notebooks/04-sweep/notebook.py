import marimo

app = marimo.App(width="medium")


@app.cell
def _():
    import hashlib
    import os
    from pathlib import Path

    import marimo as mo
    import yaml

    from nanopnp import Case
    from nanopnp.cli import main
    from nanopnp.io.case import dumps_case
    from nanopnp.plot import figure as draw
    from nanopnp.sweep.collect import collect
    from nanopnp.sweep.plan import plan_from_document, write_plan
    from nanopnp.sweep.run import run_plan

    example = (Path(__file__).resolve().parent / ".." / ".." / "examples" / "03-iv-sweep").resolve()
    os.chdir(example)
    case = Case.load("charged.case.yaml", store=example / "store", write=False)

    return (
        Case,
        Path,
        case,
        collect,
        draw,
        dumps_case,
        example,
        hashlib,
        main,
        mo,
        plan_from_document,
        run_plan,
        write_plan,
        yaml,
    )


@app.cell
def _(mo):
    mo.md(
        """
        # An I-V sweep

        Example 03's charged pore, solved at four biases. A sweep is its own document: a base
        case and the axes to vary, by their case-file paths. Each point is a complete case,
        warm-started from a converged neighbour one step nearer the `origin` value, and the
        stages a point does not change come from the store.

        A sweep computes its own points, so this notebook needs no set-up beyond the pore mesh.
        After you edit a setting, run its cell; marimo then offers to re-run the cells that
        follow.
        """
    )
    return


@app.cell
def _():
    # How the figures are drawn: a multiplier on their size, and whether they zoom and pan.
    scale = 1.5
    interactive = False
    return interactive, scale


@app.cell
def _():
    # The arguments of `nanopnp mesh cylinder`, in nm. The file is named by them, so an edited
    # value makes a new file instead of reusing an old one.
    cylinder = {
        "--pore-radius-nm": 2.0,
        "--membrane-thickness-nm": 6.0,
        "--reservoir-radius-nm": 10.0,
        "--maxh-nm": 4.0,  # the largest element anywhere
        "--wall-h-nm": 0.35,  # the element size on the pore wall
    }
    return (cylinder,)


@app.cell
def _():
    base_settings = {
        "electrolyte.concentration_M": 0.1,  # the bulk salt, mol/L
        "physics.model": "epnp-ns",  # "pnp-ns" leaves out the finite-size and correction terms
        "numerics.stabilisation": "none",  # "supg" adds streamline stabilisation
        # `rectification` compares each bias with its opposite, so the biases come in pairs.
        "outputs": ["current", "transport_numbers", "eof_rate", "rectification"],
    }
    axes = [
        {
            "name": "bias",
            "path": "boundary_conditions.bias_V",
            "values": [-0.1, -0.05, 0.05, 0.1],  # V
            "origin": 2,  # the index of the value solved first: +50 mV, the easiest point
        }
    ]
    return axes, base_settings


@app.cell
def _(
    axes,
    base_settings,
    case,
    collect,
    cylinder,
    dumps_case,
    example,
    hashlib,
    main,
    plan_from_document,
    run_plan,
    write_plan,
    yaml,
):
    mesh_file = example / ("pore-" + "-".join(f"{value:g}" for value in cylinder.values()) + ".msh")
    if not mesh_file.exists():
        flags = [str(item) for pair in cylinder.items() for item in pair]
        main(["mesh", "cylinder", *flags, "--out", str(mesh_file)])
    # The sweep reads its base from a file, so the case is written out; its inputs are
    # absolute because the file does not sit beside them.
    base = case.with_(
        **base_settings,
        **{
            "inputs.mesh.path": str(mesh_file),
            "inputs.charge.path": str(example / "cis-ring.field.yaml"),
        },
    )
    sweep_text = yaml.safe_dump(
        {
            "schema": "nanopnp/sweep/v0.5",
            "name": "iv-notebook",
            "base": "base.case.yaml",
            "axes": axes,
        },
        sort_keys=False,
    )
    case_text = dumps_case(base.document)
    # A directory holds one plan, so an edited setting makes a new directory.
    directory = example / (
        "iv-notebook-" + hashlib.sha256((sweep_text + case_text).encode()).hexdigest()[:8]
    )
    directory.mkdir(exist_ok=True)
    (directory / "base.case.yaml").write_text(case_text, encoding="utf-8")
    (directory / "sweep.yaml").write_text(sweep_text, encoding="utf-8")
    plan = plan_from_document(directory / "sweep.yaml")
    write_plan(plan, directory)
    run_plan(plan, directory, store=base.store)
    dataset = collect(plan, directory)
    return (dataset,)


@app.cell
def _(dataset, draw, interactive, mo, scale):
    curves = draw(dataset, scale=scale)
    mo.vstack(
        [
            mo.mpl.interactive(curves) if interactive else curves,
            mo.ui.table(dataset.summary["rows"], selection=None),
        ]
    )
    return


if __name__ == "__main__":
    app.run()

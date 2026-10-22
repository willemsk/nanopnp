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
    from nanopnp.core.stages import describe
    from nanopnp.io.case import dumps_case
    from nanopnp.plot import figure as draw
    from nanopnp.sweep.collect import collect
    from nanopnp.sweep.plan import plan_from_document, write_plan
    from nanopnp.sweep.run import run_plan

    example = (Path(__file__).resolve().parent / ".." / ".." / "examples" / "03-iv-sweep").resolve()
    os.chdir(example)
    case = Case.load("charged.case.yaml", store=example / "store", write=False)

    def stage_card(name, what):
        stage = describe(name)
        reads = ", ".join(f"`{item}`" for item in stage.inputs)
        return mo.md(
            f"## Stage {stage.number} · {stage.title}\n\n{what}\n\n"
            f"*Reads* {reads} · *emits* `{stage.artefact_schema}`"
        )

    def show(result, name, *, scale, interactive):
        record = next(item for item in result.stages if item.name == name)
        where = "from the store" if record.cached else "computed"
        figure = result.figure(name, scale=scale)
        if figure is None:
            drawn = mo.md("*This stage has no figure.*")
        else:
            drawn = mo.mpl.interactive(figure) if interactive else figure
        return mo.vstack(
            [
                mo.md(f"`{record.hash[:12]}` · {where} in {record.seconds:.1f} s"),
                mo.accordion({"Artefact summary": mo.json(dict(result.artefacts[name].summary))}),
                drawn,
            ]
        )

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
        show,
        stage_card,
        write_plan,
        yaml,
    )


@app.cell
def _(mo):
    mo.md(
        """
        # The cylindrical pore, end to end

        Example 03's charged pore, one block of cells per stage: the mesh, the charge on
        it, the materials, the ePNP-NS solve and its quantities of interest, and then an
        I-V sweep of the same case. Each block has four cells: what the stage is, its
        settings as plain values you can edit, the line that runs it, and what it stored.

        A stage's run takes everything before it from the store and refuses to recompute
        it (`only=True`), so the blocks go in order. After you edit a setting, run its
        cell; marimo then offers to re-run the cells that follow.
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
def _(stage_card):
    stage_card(
        "mesh",
        "The finite-element mesh the solve runs on. This case supplies one, made by "
        "`nanopnp mesh cylinder`: the stage reads it, tags its boundaries and gates its quality.",
    )
    return


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
def _(case, cylinder, example, main):
    mesh_file = example / ("pore-" + "-".join(f"{value:g}" for value in cylinder.values()) + ".msh")
    if not mesh_file.exists():
        flags = [str(item) for pair in cylinder.items() for item in pair]
        main(["mesh", "cylinder", *flags, "--out", str(mesh_file)])
    case_mesh = case.with_(**{"inputs.mesh.path": str(mesh_file)})
    run_mesh = case_mesh.run(upto="mesh", only=True)
    return case_mesh, mesh_file, run_mesh


@app.cell
def _(interactive, run_mesh, scale, show):
    show(run_mesh, "mesh", scale=scale, interactive=interactive)
    return


@app.cell
def _(stage_card):
    stage_card(
        "charge",
        "The fixed charge on the mesh. This case supplies it as a field file: a ring of "
        "negative charge on the cis half of the pore, which makes the pore rectify.",
    )
    return


@app.cell
def _():
    charge_settings = {
        "inputs.charge.path": "cis-ring.field.yaml",  # the fixed-charge field the stage reads
    }
    return (charge_settings,)


@app.cell
def _(case_mesh, charge_settings, run_mesh):
    assert run_mesh.stages[-1].name == "mesh"  # the mesh block ran first; its artefact is stored
    case_charge = case_mesh.with_(**charge_settings)
    run_charge = case_charge.run(upto="charge", only=True)
    return case_charge, run_charge


@app.cell
def _(interactive, run_charge, scale, show):
    show(run_charge, "charge", scale=scale, interactive=interactive)
    return


@app.cell
def _(stage_card):
    stage_card(
        "materials",
        "The electrolyte and its correction functions: how its diffusivity, mobility, "
        "viscosity, permittivity and density change with the salt and near the wall.",
    )
    return


@app.cell
def _():
    materials_settings = {
        "electrolyte.concentration_M": 0.1,  # the bulk salt, mol/L
        # Each correction is a named model; "none" switches it off, and the manifest records that.
        "electrolyte.corrections.diffusivity.model": "willems2020_nacl",
        "electrolyte.corrections.mobility.model": "willems2020_nacl",
        "electrolyte.corrections.viscosity.model": "willems2020_nacl",
        "electrolyte.corrections.permittivity.model": "willems2020_nacl",
        "electrolyte.corrections.density.model": "willems2020_nacl",
        "electrolyte.corrections.steric.model": "borukhov",
    }
    return (materials_settings,)


@app.cell
def _(case_charge, materials_settings, run_charge):
    assert run_charge.stages[-1].name == "charge"  # the charge block ran first
    case_materials = case_charge.with_(**materials_settings)
    run_materials = case_materials.run(upto="materials", only=True)
    return case_materials, run_materials


@app.cell
def _(interactive, run_materials, scale, show):
    show(run_materials, "materials", scale=scale, interactive=interactive)
    return


@app.cell
def _(stage_card):
    stage_card(
        "solve",
        "The ePNP-NS solve: Poisson, Nernst-Planck and Navier-Stokes together, reached by "
        "continuation from a gentle start to the case's own bias.",
    )
    return


@app.cell
def _():
    solve_settings = {
        "boundary_conditions.bias_V": 0.05,  # applied across the pore, V
        "physics.model": "epnp-ns",  # "pnp-ns" leaves out the finite-size and correction terms
        "numerics.stabilisation": "none",  # "supg" adds streamline stabilisation
        "numerics.wall_distance.max_distance_nm": 3.0,  # how far the wall functions reach
    }
    return (solve_settings,)


@app.cell
def _(case_materials, run_materials, solve_settings):
    assert run_materials.stages[-1].name == "materials"  # the materials block ran first
    case_solve = case_materials.with_(**solve_settings)
    run_solve = case_solve.run(upto="solve", only=True)
    return case_solve, run_solve


@app.cell
def _(interactive, run_solve, scale, show):
    show(run_solve, "solve", scale=scale, interactive=interactive)
    return


@app.cell
def _(stage_card):
    stage_card(
        "qoi",
        "The quantities of interest read off the solution: the ionic current, the "
        "transport numbers and the electro-osmotic flow rate.",
    )
    return


@app.cell
def _():
    qoi_settings = {
        "outputs": ["current", "transport_numbers", "eof_rate"],
    }
    return (qoi_settings,)


@app.cell
def _(case_solve, qoi_settings, run_solve):
    assert run_solve.stages[-1].name == "solve"  # the solve block ran first
    case_qoi = case_solve.with_(**qoi_settings)
    run_qoi = case_qoi.run(upto="qoi", only=True)
    return case_qoi, run_qoi


@app.cell
def _(interactive, run_qoi, scale, show):
    show(run_qoi, "qoi", scale=scale, interactive=interactive)
    return


@app.cell
def _(mo):
    mo.md(
        """
        ## The I-V sweep

        A sweep is its own document: a base case and the axes to vary, by their case-file
        paths. Here the base is the case the blocks above built, and the axis is the bias.
        Each point is a complete case, warm-started from a converged neighbour one step
        nearer the `origin` value, and the stages a point does not change come from the store.
        """
    )
    return


@app.cell
def _():
    sweep_settings = {
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
    return axes, sweep_settings


@app.cell
def _(
    axes,
    case_qoi,
    collect,
    dumps_case,
    example,
    hashlib,
    mesh_file,
    plan_from_document,
    run_plan,
    run_qoi,
    sweep_settings,
    write_plan,
    yaml,
):
    assert run_qoi.stages[-1].name == "qoi"  # the stage blocks ran first
    # The sweep reads its base from a file, so the case is written out; its inputs are
    # absolute because the file does not sit beside them.
    base = case_qoi.with_(
        **sweep_settings,
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

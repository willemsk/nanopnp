import marimo

app = marimo.App(width="medium")


@app.cell
def _():
    import os
    from pathlib import Path

    import marimo as mo

    from nanopnp import Case
    from nanopnp.cli import main
    from nanopnp.core.stages import describe

    example = (
        Path(__file__).resolve().parent / ".." / ".." / "examples" / "02-charged-pore"
    ).resolve()
    os.chdir(example)
    case = Case.load("epnpns.case.yaml", store=example / "store", write=False)

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

    return Case, case, example, main, mo, show, stage_card


@app.cell
def _(mo):
    mo.md(
        """
        # The ePNP-NS solve

        Example 02's charged pore, one block of cells per stage: the solve and the quantities
        of interest read off it. Each block has four cells: what the stage is, its settings
        as plain values you can edit, the line that runs it, and what it stored.

        This notebook starts at the solve. A stage's run takes everything before it from the
        store and refuses to recompute it (`only=True`), so the **set-up** cell below runs
        the stages before it first. After you edit a setting, run its cell; marimo then
        offers to re-run the cells that follow.
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
def _(case, example, main, mo):
    # Set-up: write the pore mesh the case reads, `nanopnp mesh cylinder` at its defaults, then
    # run the stages the solve reads: the mesh and charge, and the materials. Notebook 05 has a
    # block for each.
    mesh = example / "pore.msh"
    if not mesh.exists():
        main(["mesh", "cylinder", "--out", str(mesh)])
    run_charge = case.run(upto="charge")
    run_materials = case.run(upto="materials")
    mo.md(
        f"**Set-up.** Wrote `{mesh.name}` and ran {len(run_charge.stages)} stages up to the "
        "charge, and the materials."
    )
    return run_charge, run_materials


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
        "physics.solid_permittivities.membrane": 3.2,  # relative permittivity of the membrane
        "numerics.stabilisation": "none",  # "supg" adds streamline stabilisation
        "numerics.wall_distance.max_distance_nm": 3.0,  # how far the wall functions reach
    }
    return (solve_settings,)


@app.cell
def _(case, run_charge, run_materials, solve_settings):
    assert run_charge.stages[-1].name == "charge" and run_materials.stages[-1].name == "materials"
    case_solve = case.with_(**solve_settings)
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


if __name__ == "__main__":
    app.run()

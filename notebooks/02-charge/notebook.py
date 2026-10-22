import marimo

app = marimo.App(width="medium")


@app.cell
def _():
    import importlib.util
    import os
    from pathlib import Path

    import marimo as mo

    from nanopnp import Case
    from nanopnp.core.stages import describe

    example = (
        Path(__file__).resolve().parent / ".." / ".." / "examples" / "07-pdb-to-charged-run"
    ).resolve()
    os.chdir(example)
    case = Case.load("2wcd.case.yaml", store=example / "store", write=False)

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

    return Case, Path, case, example, importlib, mo, show, stage_card


@app.cell
def _(mo):
    mo.md(
        """
        # Charge and materials

        Example 07's case, one block of cells per stage: the protonation of the structure,
        the charge deposited on the mesh and the materials. Each block has four cells: what
        the stage is, its settings as plain values you can edit, the line that runs it, and
        what it stored.

        This notebook starts after the mesh. A stage's run takes everything before it from
        the store and refuses to recompute it (`only=True`), so the **set-up** cell below
        runs the stages before it first. After you edit a setting, run its cell; marimo then
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
def _(case, example, importlib, mo):
    # Set-up: prepare the structure as example 06 does, then run stages 1 to 6, the structure
    # to the mesh, with their settings as they stand in the case. Notebook 06 has a block each.
    script = example.parent / "06-pdb-to-mesh" / "prepare.py"
    prepared = example / "2wcd-prepared.pdb"
    if not prepared.exists():
        spec = importlib.util.spec_from_file_location("prepare", script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.prepare(
            example.parents[1] / "tests" / "data" / "structures" / "2wcd.pdb.gz", prepared
        )
    run_setup = case.run(upto="mesh")
    mo.md(
        f"**Set-up.** Prepared `{prepared.name}` and ran {len(run_setup.stages)} stages "
        f"in {sum(item.seconds for item in run_setup.stages):.1f} s, up to the mesh."
    )
    return (run_setup,)


@app.cell
def _(stage_card):
    stage_card(
        "protonation",
        "The structure protonated by PDB2PQR, with PROPKA choosing each titratable residue's "
        "state at one pH. Each atom comes out with a partial charge and a radius.",
    )
    return


@app.cell
def _():
    protonation_settings = {
        "charge.ph": 7.5,  # the pH PROPKA works at
        "charge.forcefield": "CHARMM",  # also "PEOEPB" or "SWANSON"
    }
    return (protonation_settings,)


@app.cell
def _(case, protonation_settings, run_setup):
    assert run_setup.stages[-1].name == "mesh"  # the set-up ran first
    case_protonation = case.with_(**protonation_settings)
    run_protonation = case_protonation.run(upto="protonation", only=True)
    return case_protonation, run_protonation


@app.cell
def _(interactive, run_protonation, scale, show):
    show(run_protonation, "protonation", scale=scale, interactive=interactive)
    return


@app.cell
def _(stage_card):
    stage_card(
        "charge",
        "The fixed charge on the mesh: each atom smeared into a Gaussian, averaged exactly "
        "around the axis and deposited element by element. The run stops if the charge on the "
        "mesh is not the charge of the atoms.",
    )
    return


@app.cell
def _():
    charge_settings = {
        "charge.smearing.sharpness": 0.5,  # the width of each atom's Gaussian
        "charge.smearing.grid_spacing_nm": 0.005,  # the lattice the average is taken on
        "charge.dielectric_transition_nm": 0.0,  # above 0 grades the permittivity at the wall
    }
    return (charge_settings,)


@app.cell
def _(case_protonation, charge_settings, run_protonation):
    assert run_protonation.stages[-1].name == "protonation"  # the protonation block ran first
    case_charge = case_protonation.with_(**charge_settings)
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
        "electrolyte.concentration_M": 0.15,  # the bulk salt, mol/L
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


if __name__ == "__main__":
    app.run()

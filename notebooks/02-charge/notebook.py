import marimo

app = marimo.App(width="medium")


@app.cell
def _():
    import os
    from pathlib import Path

    import marimo as mo

    from nanopnp import Case, Session, Store

    here = Path(__file__).resolve().parent
    store = Store(os.environ.get("NANOPNP_STORE") or here.parent / ".store")
    session = Session(store, write=False)
    stages = {info.name: info for info in session.stages}
    return Case, mo, session, stages, store


@app.cell
def _(mo):
    mo.md(
        """
        # Charge and materials

        The 2WCD pore of notebook 01, charged: PDB2PQR and PROPKA protonate the structure,
        its atoms' charges are deposited on the mesh, and the electrolyte's correction
        functions are evaluated. The case is built as notebooks 01 and 06 build it, so the
        stages they share come from the store. In a running notebook each figure pans and
        zooms.
        """
    )
    return


@app.cell
def _(Case, mo, session, store):
    # Notebook 01's preparation at its defaults, and the same case: stages 1 to 6 are shared.
    case = Case.from_structure(
        "2wcd.pdb.gz",
        orient={
            "chains": "A,B,C,D,E,F,G,H,I,J,K,L",
            "cis_end": "wider",
            "registration_residues": (8, 292),
            "centroid_z_nm": 5.655,
        },
        structures=store.root / "structures",
        point_group="C12",
        concentration_M=0.15,
        bias_V=0.05,
        size_scale=4.0,
        name="2wcd",
    )
    meshed = session.run(case, upto="mesh")
    mo.md(
        f"**Stages 1 to 6**, the structure to the mesh: "
        f"{sum(record.cached for record in meshed.stages)} of {len(meshed.stages)} from the store."
    )
    return (case,)


@app.cell
def _(mo):
    mo.md(
        """
        ## 1 · Protonation and the deposited charge

        PROPKA chooses each titratable residue's state at the pH, and PDB2PQR gives every
        atom a partial charge and a radius in the force field. Each atom's charge is then
        smeared into a Gaussian, averaged exactly about the axis and deposited element by
        element; the run stops if the charge on the mesh is not the charge of the atoms.
        """
    )
    return


@app.cell
def _(mo):
    CHARGE_DEFAULTS = {"ph": 7.5, "forcefield": "CHARMM"}
    charge_form = mo.ui.dictionary(
        {
            "ph": mo.ui.number(2.0, 12.0, 0.1, CHARGE_DEFAULTS["ph"], label="pH"),
            "forcefield": mo.ui.dropdown(
                ["CHARMM", "PEOEPB", "SWANSON"],
                CHARGE_DEFAULTS["forcefield"],
                label="force field",
            ),
        }
    ).form(submit_button_label="Charge")
    charge_form
    return CHARGE_DEFAULTS, charge_form


@app.cell
def _(CHARGE_DEFAULTS, case, charge_form, session):
    charging = charge_form.value or CHARGE_DEFAULTS
    charged = session.run(
        case.with_({"charge.ph": charging["ph"], "charge.forcefield": charging["forcefield"]}),
        upto="charge",
    )
    return (charged,)


@app.cell
def _(charged, mo, stages):
    def where(name):
        record = next(item for item in charged.stages if item.name == name)
        stage = stages[name]
        found = "from the store" if record.cached else f"computed in {record.seconds:.1f} s"
        return mo.md(f"*Stage {stage.number}, {stage.title}:* `{record.hash[:12]}`, {found}")

    mo.ui.tabs(
        {
            "protonation": mo.vstack(
                [where("protonation"), mo.mpl.interactive(charged.figure("protonation"))]
            ),
            "deposited charge and solid fraction": mo.vstack(
                [where("charge"), mo.mpl.interactive(charged.figure("charge"))]
            ),
        }
    )
    return


@app.cell
def _(mo):
    mo.md(
        """
        ## 2 · The materials

        The electrolyte's correction functions: how the diffusivity, mobility, viscosity,
        permittivity and density change with the salt and near the wall, each read from the
        parameter file, the operating salt marked. The stage reads nothing of the mesh, so a
        new salt re-evaluates it alone.
        """
    )
    return


@app.cell
def _(mo):
    MATERIALS_DEFAULTS = {"concentration_M": 0.15}
    materials_form = mo.ui.dictionary(
        {
            "concentration_M": mo.ui.number(
                0.01, 3.0, 0.01, MATERIALS_DEFAULTS["concentration_M"], label="NaCl (M)"
            )
        }
    ).form(submit_button_label="Evaluate")
    materials_form
    return MATERIALS_DEFAULTS, materials_form


@app.cell
def _(MATERIALS_DEFAULTS, case, materials_form, mo, session):
    salt = materials_form.value or MATERIALS_DEFAULTS
    materials = session.run(case.with_(concentration_M=salt["concentration_M"]), upto="materials")
    mo.mpl.interactive(materials.figure("materials"))
    return


if __name__ == "__main__":
    app.run()

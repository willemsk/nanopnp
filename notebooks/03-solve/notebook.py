import marimo

app = marimo.App(width="medium")


@app.cell
def _():
    import os
    from pathlib import Path

    import marimo as mo

    from nanopnp import Case, Store

    here = Path(__file__).resolve().parent
    store = Store(os.environ.get("NANOPNP_STORE") or here.parent / ".store")
    ring = here.parents[1] / "examples" / "02-charged-pore" / "ring.field.yaml"
    return Case, mo, ring, store


@app.cell
def _(mo):
    mo.md(
        """
        # The ePNP-NS solve

        A charged cylindrical pore in 0.1 M NaCl, built in one line of Python and solved
        with the validated ePNP-NS model: Poisson, Nernst-Planck and Navier-Stokes together,
        every correction on. The fixed charge is the ring of example 02.

        Edit the settings and press **Solve**. The run takes every stage it does not change
        from the store, so a new bias re-solves without meshing again.
        """
    )
    return


@app.cell
def _(mo):
    SOLVE_DEFAULTS = {
        "pore_radius_nm": 2.0,
        "membrane_thickness_nm": 6.0,
        "concentration_M": 0.1,
        "bias_mV": 50.0,
        "stabilisation": "none",
    }
    solve_form = mo.ui.dictionary(
        {
            "pore_radius_nm": mo.ui.number(
                0.5, 5.0, 0.1, SOLVE_DEFAULTS["pore_radius_nm"], label="pore radius (nm)"
            ),
            "membrane_thickness_nm": mo.ui.number(
                2.0, 12.0, 0.5, SOLVE_DEFAULTS["membrane_thickness_nm"], label="membrane (nm)"
            ),
            "concentration_M": mo.ui.number(
                0.01, 3.0, 0.01, SOLVE_DEFAULTS["concentration_M"], label="NaCl (M)"
            ),
            "bias_mV": mo.ui.number(
                -200.0, 200.0, 5.0, SOLVE_DEFAULTS["bias_mV"], label="bias (mV)"
            ),
            "stabilisation": mo.ui.dropdown(
                ["none", "supg"], SOLVE_DEFAULTS["stabilisation"], label="stabilisation"
            ),
        }
    ).form(submit_button_label="Solve")
    solve_form
    return SOLVE_DEFAULTS, solve_form


@app.cell
def _(Case, SOLVE_DEFAULTS, ring, solve_form, store):
    settings = solve_form.value or SOLVE_DEFAULTS
    case = Case.cylinder(
        pore_radius_nm=settings["pore_radius_nm"],
        membrane_thickness_nm=settings["membrane_thickness_nm"],
        concentration_M=settings["concentration_M"],
        bias_V=settings["bias_mV"] * 1e-3,
        charge=ring,
        name="charged-cylinder",
        store=store,
        write=False,
    ).with_(stabilisation=settings["stabilisation"])
    run = case.run()
    return (run,)


@app.cell
def _(mo, run):
    conductance = run.conductance_nS
    mo.vstack(
        [
            mo.md(
                f"**I = {run.current_nA:.4g} nA**"
                + ("" if conductance is None else f" · **G = {conductance:.4g} nS**")
                + f" · {sum(record.cached for record in run.stages)} of {len(run.stages)} "
                "stages from the store"
            ),
            run.figure("solve"),
        ]
    )
    return


@app.cell
def _(mo, run):
    mo.accordion({"Every quantity of interest": run.figure("qoi")})
    return


if __name__ == "__main__":
    app.run()

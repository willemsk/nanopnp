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
    ring = here.parents[1] / "examples" / "02-charged-pore" / "ring.field.yaml"
    return Case, mo, ring, session


@app.cell
def _(mo):
    mo.md(
        """
        # The ePNP-NS solve

        A charged cylindrical pore in 0.1 M NaCl, built in one line of Python and solved
        with the validated ePNP-NS model: Poisson, Nernst-Planck and Navier-Stokes together,
        every correction on. The fixed charge is the ring of example 02, 2.6 nm from the axis,
        so the pore radius stops at 2.2 nm: a wider pore would hold the ring in its lumen.

        Edit the settings and press **Solve**. The run takes every stage it does not change
        from the store, so a new bias re-solves without meshing again. The views below the
        solve redraw at once: they read the solved fields, sampled once per solve. In a
        running notebook each figure pans and zooms.
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
                0.5, 2.2, 0.1, SOLVE_DEFAULTS["pore_radius_nm"], label="pore radius (nm)"
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
def _(Case, SOLVE_DEFAULTS, ring, session, solve_form):
    settings = solve_form.value or SOLVE_DEFAULTS
    case = Case.cylinder(
        pore_radius_nm=settings["pore_radius_nm"],
        membrane_thickness_nm=settings["membrane_thickness_nm"],
        concentration_M=settings["concentration_M"],
        bias_V=settings["bias_mV"] * 1e-3,
        charge=ring,
        name="charged-cylinder",
    ).with_(stabilisation=settings["stabilisation"])
    run = session.run(case)
    return run, settings


@app.cell
def _(mo, run):
    conductance = run.conductance_nS
    mo.md(
        f"**I = {run.current_nA:.4g} nA**"
        + ("" if conductance is None else f" · **G = {conductance:.4g} nS**")
        + f" · {sum(record.cached for record in run.stages)} of {len(run.stages)} "
        "stages from the store"
    )
    return


@app.cell
def _(mo, run, settings):
    fields = run.fields
    quantities = run.field_choices()
    window = mo.ui.radio(
        {"around the pore": None, "the lumen": "lumen"},
        value="around the pore",
        inline=True,
        label="window",
    )
    # The ring's charge sits in the membrane; a range from the bias keeps the pore's drop in view.
    potential_range = mo.ui.slider(
        5.0,
        1000.0,
        5.0,
        max(10.0, 2.0 * abs(settings["bias_mV"])),
        debounce=True,
        show_value=True,
        label="potential colour range ± (mV)",
    )
    mo.hstack([window, potential_range], justify="start", gap=2)
    return fields, potential_range, quantities, window


@app.cell
def _(mo, potential_range, quantities, run, window):
    # One figure per field; a concentration is drawn as log10(c / c_bulk), so depletion shows.
    mo.ui.tabs(
        {
            label: mo.mpl.interactive(
                run.plot_field(
                    quantity,
                    zoom_nm=window.value,
                    relative=True,
                    halfrange=potential_range.value if quantity == "potential" else None,
                )
            )
            for label, quantity in quantities.items()
        }
    )
    return


@app.cell
def _(fields, mo, quantities, settings):
    z_extent_nm = fields.fluid[0][:, 1] * 1e9
    cutline_quantity = mo.ui.dropdown(list(quantities), value="potential φ", label="profile of")
    z_nm = mo.ui.slider(
        round(float(z_extent_nm.min()), 1),
        round(float(z_extent_nm.max()), 1),
        0.1,
        0.0,
        debounce=True,
        show_value=True,
        label="across the pore at z (nm)",
    )
    r_nm = mo.ui.slider(
        0.0,
        settings["pore_radius_nm"],
        0.05,
        0.0,
        debounce=True,
        show_value=True,
        label="along the pore at r (nm)",
    )
    mo.hstack([cutline_quantity, r_nm, z_nm], justify="start", gap=2)
    return cutline_quantity, r_nm, z_nm


@app.cell
def _(cutline_quantity, mo, quantities, r_nm, run, z_nm):
    profile = quantities[cutline_quantity.value]
    mo.hstack(
        [
            mo.mpl.interactive(
                run.plot_cutline(profile, along="z", at_nm=r_nm.value, relative=True)
            ),
            mo.mpl.interactive(
                run.plot_cutline(profile, along="r", at_nm=z_nm.value, relative=True)
            ),
        ],
        widths="equal",
    )
    return


@app.cell
def _(mo, run):
    mo.vstack(
        [
            mo.md("**Every quantity of interest**"),
            mo.ui.table(run.quantity_rows(), selection=None),
        ]
    )
    return


if __name__ == "__main__":
    app.run()

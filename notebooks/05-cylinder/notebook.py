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
    ring = here.parents[1] / "examples" / "03-iv-sweep" / "cis-ring.field.yaml"
    return Case, mo, ring, session


@app.cell
def _(mo):
    mo.md(
        """
        # The cylindrical pore, end to end

        A charged cylinder in four steps: its mesh, the ePNP-NS solve, profiles through
        the solved fields, and an I-V sweep of the same pore. Each step that computes
        waits for its button; each runs only the stages its settings change, and takes
        the rest from the store. The fixed charge is a ring near the cis mouth, as in
        notebook 04, so the pore rectifies. In a running notebook each figure pans and
        zooms.
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        """
        ## 1 · The mesh

        The pore's size sets the mesh; the radius stops at 2.2 nm because the fixed charge's
        ring sits 2.6 nm from the axis, and a wider pore would hold it in the lumen. The
        figure shows the whole domain by element size and, beside it, the lumen by element
        quality, with the double-layer target λ_D/5 drawn to scale. The wall is sized either
        at a fixed 0.35 nm, as examples 02 and 03 are, or as stage 6 sizes
        an idealised pore's mesh, at λ_D/5 of the salt below but at most 0.05 nm; the second
        resolves the ion wall function's decay length, and meshes again only where λ_D/5
        falls below 0.05 nm, above about 1.5 M.
        """
    )
    return


@app.cell
def _(mo):
    FIXED_WALL_H_NM = 0.35
    WALLS = {
        f"fixed, {FIXED_WALL_H_NM:g} nm": FIXED_WALL_H_NM,
        "stage 6's target, at most 0.05 nm": "auto",
    }
    MESH_DEFAULTS = {
        "pore_radius_nm": 2.0,
        "membrane_thickness_nm": 6.0,
        "reservoir_radius_nm": 10.0,
        "wall_h_nm": FIXED_WALL_H_NM,
    }
    mesh_form = mo.ui.dictionary(
        {
            "pore_radius_nm": mo.ui.number(
                0.5, 2.2, 0.1, MESH_DEFAULTS["pore_radius_nm"], label="pore radius (nm)"
            ),
            "membrane_thickness_nm": mo.ui.number(
                2.0, 12.0, 0.5, MESH_DEFAULTS["membrane_thickness_nm"], label="membrane (nm)"
            ),
            "reservoir_radius_nm": mo.ui.number(
                6.0, 40.0, 1.0, MESH_DEFAULTS["reservoir_radius_nm"], label="reservoir (nm)"
            ),
            "wall_h_nm": mo.ui.dropdown(WALLS, value=next(iter(WALLS)), label="wall size"),
        }
    ).form(submit_button_label="Mesh")
    mesh_form
    return MESH_DEFAULTS, mesh_form


@app.cell
def _(MESH_DEFAULTS, mesh_form):
    geometry = mesh_form.value or MESH_DEFAULTS
    return (geometry,)


@app.cell
def _(case, mo, session):
    # The λ_D/5 bar follows the salt of the solve below.
    mo.mpl.interactive(session.run(case, upto="mesh").figure("mesh"))
    return


@app.cell
def _(mo):
    mo.md(
        """
        ## 2 · The solve

        The salt and the bias leave the mesh as it is, so a new value re-solves only.
        Each field is its own figure; a concentration is drawn against the bulk, so
        depletion and enrichment show either side of zero.
        """
    )
    return


@app.cell
def _(mo):
    SOLVE_DEFAULTS = {"concentration_M": 0.1, "bias_mV": 50.0}
    solve_form = mo.ui.dictionary(
        {
            "concentration_M": mo.ui.number(
                0.01, 3.0, 0.01, SOLVE_DEFAULTS["concentration_M"], label="NaCl (M)"
            ),
            "bias_mV": mo.ui.number(
                -200.0, 200.0, 5.0, SOLVE_DEFAULTS["bias_mV"], label="bias (mV)"
            ),
        }
    ).form(submit_button_label="Solve")
    solve_form
    return SOLVE_DEFAULTS, solve_form


@app.cell
def _(Case, SOLVE_DEFAULTS, geometry, ring, session, solve_form):
    settings = solve_form.value or SOLVE_DEFAULTS
    case = Case.cylinder(
        **geometry,
        concentration_M=settings["concentration_M"],
        bias_V=settings["bias_mV"] * 1e-3,
        charge=ring,
        name="cylinder-end-to-end",
    )
    run = session.run(case)
    return case, run, settings


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
def _(run):
    fields = run.fields
    quantities = run.field_choices(radial=False)
    return fields, quantities


@app.cell
def _(mo, settings):
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
    potential_range
    return (potential_range,)


@app.cell
def _(mo, potential_range, quantities, run):
    mo.ui.tabs(
        {
            label: mo.mpl.interactive(
                run.plot_field(
                    quantity,
                    relative=True,
                    halfrange=potential_range.value if quantity == "potential" else None,
                )
            )
            for label, quantity in quantities.items()
        }
    )
    return


@app.cell
def _(mo):
    mo.md(
        """
        ## 3 · Profiles through the pore

        A profile along the pore at a radius, and one across it at a height. They read
        the fields already sampled, so a slider redraws them at once. Across the pore,
        a concentration ends at the wall; the potential carries on into the membrane.
        """
    )
    return


@app.cell
def _(fields, geometry, mo, quantities):
    z_extent_nm = fields.fluid[0][:, 1] * 1e9
    cutline_quantity = mo.ui.dropdown(list(quantities), value="potential φ", label="profile of")
    r_nm = mo.ui.slider(
        0.0,
        geometry["pore_radius_nm"],
        0.05,
        0.0,
        debounce=True,
        show_value=True,
        label="along the pore at r (nm)",
    )
    z_nm = mo.ui.slider(
        round(float(z_extent_nm.min()), 1),
        round(float(z_extent_nm.max()), 1),
        0.1,
        0.0,
        debounce=True,
        show_value=True,
        label="across the pore at z (nm)",
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
def _(mo):
    mo.md(
        """
        ## 4 · The I-V sweep

        The same pore at several biases, in one call. Each point warm-starts from a
        converged neighbour one step nearer the bias solved first, and the stages a
        point does not change come from the store. Opposite biases pair into a
        rectification ratio.
        """
    )
    return


@app.cell
def _(mo):
    SWEEP_DEFAULTS = {"biases_mV": "-100, -50, 50, 100"}
    sweep_form = mo.ui.dictionary(
        {"biases_mV": mo.ui.text(SWEEP_DEFAULTS["biases_mV"], label="biases (mV)")}
    ).form(submit_button_label="Sweep")
    sweep_form
    return SWEEP_DEFAULTS, sweep_form


@app.cell
def _(SWEEP_DEFAULTS, case, session, settings, sweep_form):
    biases_V = [
        float(text) * 1e-3 for text in (sweep_form.value or SWEEP_DEFAULTS)["biases_mV"].split(",")
    ]
    first = min(range(len(biases_V)), key=lambda i: abs(biases_V[i] - settings["bias_mV"] * 1e-3))
    swept = case.with_(
        bias_V=biases_V[first],
        outputs=["current", "transport_numbers", "eof_rate", "rectification"],
    )
    swept = session.sweep(swept, axis="bias_V", values=biases_V, origin=first)
    return (swept,)


@app.cell
def _(mo, swept):
    mo.vstack(
        [
            mo.mpl.interactive(swept.plot_iv()),
            mo.ui.table(swept.rows, selection=None),
        ]
    )
    return


if __name__ == "__main__":
    app.run()

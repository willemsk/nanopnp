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
    return Case, mo, session, store


@app.cell
def _(mo):
    mo.md(
        """
        # From a PDB entry to a solve

        The 2WCD pore of notebooks 01 and 02, solved with the validated ePNP-NS model. The
        case is built as they build it, so the stages up to the materials come from the
        store when they have run; from an empty store the whole walk takes about eleven
        minutes, most of it the solve. By default the mesh is four times coarser than the
        default sizes, for runtime only; the form's mesh size scale refines it, at the cost
        the table below gives. In a running notebook each figure pans and zooms.
        """
    )
    return


@app.cell
def _(Case, store):
    # Notebook 01's preparation at its defaults, and the same case: stages 1 to 8 are shared.
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
    return (case,)


@app.cell
def _(mo):
    mo.md(
        """
        ## The solve

        The form sets the salt, the bias, the stabilisation and the mesh size scale, which
        multiplies every element size. What the scale costs, measured once at the defaults,
        on one cloud machine, with the stages before the charge in the store:

        | mesh size scale | elements | solve | G at +50 mV |
        |---:|---:|---:|---:|
        | 4 | 6,223 | 5 min | 0.9734 nS |
        | 3 | 7,955 | 7 min | 0.9731 nS |
        | 2 | 14,072 | 7.5 min | 0.9732 nS |
        | 1.5 | 21,799 | 10.5 min | 0.9731 nS |
        | 1 | 44,811 | 47 min | 0.9730 nS |

        The conductance moves by less than 0.05 % between the coarsest and the finest
        mesh; a finer mesh resolves the fields near the wall, and costs a new charge
        deposition as well as the solve.
        """
    )
    return


@app.cell
def _(mo):
    SOLVE_DEFAULTS = {
        "concentration_M": 0.15,
        "bias_mV": 50.0,
        "stabilisation": "none",
        "size_scale": 4.0,
    }
    solve_form = mo.ui.dictionary(
        {
            "concentration_M": mo.ui.number(
                0.05, 1.0, 0.01, SOLVE_DEFAULTS["concentration_M"], label="NaCl (M)"
            ),
            "bias_mV": mo.ui.number(
                -200.0, 200.0, 5.0, SOLVE_DEFAULTS["bias_mV"], label="bias (mV)"
            ),
            "stabilisation": mo.ui.dropdown(
                ["none", "supg"], SOLVE_DEFAULTS["stabilisation"], label="stabilisation"
            ),
            "size_scale": mo.ui.slider(
                steps=[1.0, 1.5, 2.0, 3.0, 4.0],
                value=SOLVE_DEFAULTS["size_scale"],
                show_value=True,
                label="mesh size scale",
            ),
        }
    ).form(submit_button_label="Solve")
    solve_form
    return SOLVE_DEFAULTS, solve_form


@app.cell
def _(SOLVE_DEFAULTS, case, session, solve_form):
    settings = solve_form.value or SOLVE_DEFAULTS
    run = session.run(
        case.with_(
            {"numerics.mesh.size_scale": settings["size_scale"]},
            concentration_M=settings["concentration_M"],
            bias_V=settings["bias_mV"] * 1e-3,
            stabilisation=settings["stabilisation"],
        )
    )
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
def _(mo, run):
    mo.ui.tabs(
        {
            name: mo.mpl.interactive(run.figure(name))
            for name in ("structure", "symmetry", "contour", "mesh", "charge", "materials")
        }
        | {"Newton and continuation": mo.mpl.interactive(run.figure("solve"))}
    )
    return


@app.cell
def _(mo):
    mo.md(
        """
        ## The solved fields

        Each field is its own figure. The potential is coloured about zero, its range set
        by the slider; a concentration is drawn against the bulk, as log₁₀(c / c_bulk), so
        depletion and enrichment show either side of zero.
        """
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
def _(fields, mo, quantities):
    z_extent_nm = fields.fluid[0][:, 1] * 1e9
    cutline_quantity = mo.ui.dropdown(list(quantities), value="potential φ", label="profile of")
    r_nm = mo.ui.slider(
        0.0, 5.0, 0.05, 0.0, debounce=True, show_value=True, label="along the pore at r (nm)"
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

import marimo

app = marimo.App(width="medium")


@app.cell
def _():
    import hashlib
    import json
    import os
    from pathlib import Path

    import marimo as mo

    from nanopnp import Case, Store
    from nanopnp.core.paths import structure_file
    from nanopnp.plot import plot_axial_cutline, plot_field, plot_radial_cutline
    from nanopnp.plot.data import LUMEN_NM, qoi_rows
    from nanopnp.structure import orient_pore

    here = Path(__file__).resolve().parent
    store = Store(os.environ.get("NANOPNP_STORE") or here.parent / ".store")
    entry = structure_file("2wcd.pdb.gz")
    return (
        Case,
        LUMEN_NM,
        entry,
        hashlib,
        json,
        mo,
        orient_pore,
        plot_axial_cutline,
        plot_field,
        plot_radial_cutline,
        qoi_rows,
        store,
    )


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
def _(Case, entry, hashlib, json, orient_pore, store):
    # Notebook 01's preparation at its defaults, and the same case: stages 1 to 8 are shared.
    preparation = {
        "chains": "A,B,C,D,E,F,G,H,I,J,K,L",
        "cis_end": "wider",
        "first_residue": 8,
        "last_residue": 292,
        "centroid_z_nm": 5.655,
    }
    key = hashlib.sha256(json.dumps(preparation, sort_keys=True).encode()).hexdigest()[:12]
    prepared = store.root / "structures" / f"2wcd-{key}.pdb"
    if not prepared.is_file():
        prepared.parent.mkdir(parents=True, exist_ok=True)
        orient_pore(
            entry,
            chains=preparation["chains"],
            cis_end=preparation["cis_end"],
            registration_residues=(preparation["first_residue"], preparation["last_residue"]),
            centroid_z_nm=preparation["centroid_z_nm"],
            out=prepared,
        )
    case = Case.from_structure(
        prepared,
        point_group="C12",
        concentration_M=0.15,
        bias_V=0.05,
        size_scale=4.0,
        name="2wcd",
        store=store,
        write=False,
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
def _(SOLVE_DEFAULTS, case, solve_form):
    settings = solve_form.value or SOLVE_DEFAULTS
    run = case.run(
        concentration_M=settings["concentration_M"],
        bias_V=settings["bias_mV"] * 1e-3,
        stabilisation=settings["stabilisation"],
        **{"numerics.mesh.size_scale": settings["size_scale"]},
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
def _(LUMEN_NM, mo, run, settings):
    fields = run.fields
    quantities = {
        "potential φ": "potential",
        **{
            f"{key.removesuffix('_mol_m3')} against the bulk": key
            for key in sorted(fields.fluid[2])
            if key.endswith("_mol_m3")
        },
        "axial velocity u_z": "u_z",
        "radial velocity u_r": "u_r",
        "pressure p": "p_Pa",
    }
    window = mo.ui.radio(
        {"around the pore": None, "the lumen": LUMEN_NM},
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
def _(fields, mo, plot_field, potential_range, quantities, settings, window):
    mo.ui.tabs(
        {
            label: mo.mpl.interactive(
                plot_field(
                    fields,
                    quantity,
                    zoom_nm=window.value,
                    relative_to_M=settings["concentration_M"],
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
def _(
    cutline_quantity,
    fields,
    mo,
    plot_axial_cutline,
    plot_radial_cutline,
    quantities,
    r_nm,
    settings,
    z_nm,
):
    profile = quantities[cutline_quantity.value]
    bulk_M = settings["concentration_M"]
    mo.hstack(
        [
            mo.mpl.interactive(
                plot_axial_cutline(fields, profile, r_nm=r_nm.value, relative_to_M=bulk_M)
            ),
            mo.mpl.interactive(
                plot_radial_cutline(fields, profile, z_nm=z_nm.value, relative_to_M=bulk_M)
            ),
        ],
        widths="equal",
    )
    return


@app.cell
def _(mo, qoi_rows, run):
    mo.vstack(
        [
            mo.md("**Every quantity of interest**"),
            mo.ui.table(qoi_rows(run.quantities), selection=None),
        ]
    )
    return


if __name__ == "__main__":
    app.run()

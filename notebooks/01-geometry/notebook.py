import marimo

app = marimo.App(width="medium")


@app.cell
def _():
    import os
    from pathlib import Path

    import marimo as mo

    from nanopnp import Case, Store
    from nanopnp.core.paths import structure_file
    from nanopnp.core.stages import describe
    from nanopnp.structure import prepared_pore

    here = Path(__file__).resolve().parent
    store = Store(os.environ.get("NANOPNP_STORE") or here.parent / ".store")
    entry = structure_file("2wcd.pdb.gz")
    return Case, describe, entry, mo, prepared_pore, store


@app.cell
def _(mo):
    mo.md(
        """
        # From a PDB entry to a mesh

        The cytolysin A pore as deposited (2WCD), prepared and taken through the geometry
        stages: the structure, the density, the symmetry reduction, the contour, the region
        and the mesh. Each step that computes waits for its button, and each run takes
        every stage it does not change from the store, which notebooks 02 and 06 share:
        they build the same case. In a running notebook each figure pans and zooms.
        """
    )
    return


@app.cell
def _(mo):
    mo.md(
        """
        ## 1 · Prepare the entry

        Stage 1 refuses a file whose pore axis is more than 10° from z, and never turns
        one itself. `orient_pore` does it, with the choices that are yours: the chains,
        which end faces *cis* (+z), and where the membrane sits, by placing the C-alpha
        centroid of a run of residues on the axis. For ClyA, the first dodecamer, its
        wide cap *cis*, and residues 8 to 292 at 5.655 nm, which puts the bilayer centre
        at z = 0.
        """
    )
    return


@app.cell
def _(mo):
    PREPARE_DEFAULTS = {
        "chains": "A,B,C,D,E,F,G,H,I,J,K,L",
        "cis_end": "wider",
        "first_residue": 8,
        "last_residue": 292,
        "centroid_z_nm": 5.655,
    }
    prepare_form = mo.ui.dictionary(
        {
            "chains": mo.ui.text(PREPARE_DEFAULTS["chains"], label="chains"),
            "cis_end": mo.ui.dropdown(
                ["wider", "narrower"], PREPARE_DEFAULTS["cis_end"], label="cis end"
            ),
            "first_residue": mo.ui.number(
                1, 400, 1, PREPARE_DEFAULTS["first_residue"], label="from residue"
            ),
            "last_residue": mo.ui.number(
                1, 400, 1, PREPARE_DEFAULTS["last_residue"], label="to residue"
            ),
            "centroid_z_nm": mo.ui.number(
                -20.0, 20.0, 0.005, PREPARE_DEFAULTS["centroid_z_nm"], label="at z (nm)"
            ),
        }
    ).form(submit_button_label="Prepare")
    prepare_form
    return PREPARE_DEFAULTS, prepare_form


@app.cell
def _(PREPARE_DEFAULTS, entry, prepared_pore, prepare_form, store):
    preparation = prepare_form.value or PREPARE_DEFAULTS
    prepared = prepared_pore(
        entry,
        directory=store.root / "structures",
        chains=preparation["chains"],
        cis_end=preparation["cis_end"],
        registration_residues=(preparation["first_residue"], preparation["last_residue"]),
        centroid_z_nm=preparation["centroid_z_nm"],
    )
    return (prepared,)


@app.cell
def _(Case, prepared, store):
    # The same call in notebooks 01, 02 and 06, so the three share stages 1 to 8.
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
        ## 2 · Structure, density and symmetry

        Stage 1 finds the exact axis by superposing the twelve chains and checks the
        symmetry; stage 2 smears each atom into a Gaussian on a grid; stage 3 averages the
        map about the axis, reducing it to the (r, z) half-plane the solve works on. These
        take about half a minute from an empty store.
        """
    )
    return


@app.cell
def _(case, describe, mo):
    reduced = case.run(upto="symmetry")

    def stage_tab(result, name):
        record = next(item for item in result.stages if item.name == name)
        stage = describe(name)
        where = "from the store" if record.cached else f"computed in {record.seconds:.1f} s"
        return mo.vstack(
            [
                mo.md(f"*Stage {stage.number}, {stage.title}:* `{record.hash[:12]}`, {where}"),
                mo.mpl.interactive(result.figure(name)),
                mo.accordion({"Artefact summary": mo.json(dict(result.artefacts[name].summary))}),
            ]
        )

    mo.ui.tabs({name: stage_tab(reduced, name) for name in ("structure", "density", "symmetry")})
    return (stage_tab,)


@app.cell
def _(mo):
    mo.md(
        """
        ## 3 · Contour, region and mesh

        The pore wall is the contour of the reduced density at one isolevel, and the region
        joins it to a 2.8 nm bilayer and two reservoirs. The sliders re-draw the contour and
        the mesh behind it in seconds; the stages before come from the store. Near either
        end of the isolevel's range the contour gates refuse the wall, and the refusal says
        which gate and where.

        The mesh size scale multiplies every element size. Notebooks 02 and 06 use 4, four
        times coarser than the default, so that the solve stays near five minutes; the
        table below says what a finer mesh costs in 06 and what it changes.
        """
    )
    return


@app.cell
def _(mo):
    isolevel = mo.ui.slider(
        0.01, 0.99, 0.01, 0.25, debounce=True, show_value=True, label="contour isolevel"
    )
    size_scale = mo.ui.slider(
        steps=[1.0, 1.5, 2.0, 3.0, 4.0],
        value=4.0,
        debounce=True,
        show_value=True,
        label="mesh size scale",
    )
    mo.hstack([isolevel, size_scale], justify="start", gap=2)
    return isolevel, size_scale


@app.cell
def _(case, isolevel, mo, size_scale, stage_tab):
    try:
        meshed = case.run(
            upto="mesh",
            **{
                "geometry.contour.isolevel": isolevel.value,
                "numerics.mesh.size_scale": size_scale.value,
            },
        )
    except ValueError as refusal:
        shown = mo.callout(mo.md(f"**The walk stopped.** {refusal}"), kind="warn")
    else:
        shown = mo.ui.tabs(
            {name: stage_tab(meshed, name) for name in ("contour", "region", "mesh")}
        )
    shown
    return


@app.cell
def _(mo):
    mo.md(
        """
        **What the mesh size scale costs** in notebook 06, measured once at its defaults (0.15 M,
        +50 mV), on one cloud machine, with the stages before the charge in the store:

        | mesh size scale | elements | solve | G at +50 mV |
        |---:|---:|---:|---:|
        | 4 | 6,223 | 5 min | 0.9734 nS |
        | 3 | 7,955 | 7 min | 0.9731 nS |
        | 2 | 14,072 | 7.5 min | 0.9732 nS |
        | 1.5 | 21,799 | 10.5 min | 0.9731 nS |
        | 1 | 44,811 | 47 min | 0.9730 nS |

        The conductance moves by less than 0.05 % between the coarsest and the finest
        mesh, so 4 is enough for it; a finer mesh resolves the fields near the wall, where the
        double layer is thinnest, and costs a new charge deposition as well as the solve.
        """
    )
    return


if __name__ == "__main__":
    app.run()

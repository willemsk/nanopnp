import marimo

app = marimo.App(width="medium")


@app.cell
def _():
    import hashlib
    import importlib.util
    import os
    from pathlib import Path

    import marimo as mo

    from nanopnp import Case
    from nanopnp.core.stages import describe

    example = (
        Path(__file__).resolve().parent / ".." / ".." / "examples" / "06-pdb-to-mesh"
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

    return Case, Path, case, example, hashlib, importlib, mo, show, stage_card


@app.cell
def _(mo):
    mo.md(
        """
        # From a PDB entry to a mesh

        Example 06's case, one block of cells per stage, from the deposited 2WCD entry to
        the finite-element mesh. Each block has four cells: what the stage is, its settings
        as plain values you can edit, the line that runs it, and what it stored.

        A stage's run takes everything before it from the store and refuses to recompute it
        (`only=True`), so the blocks go in order. After you edit a setting, run its cell;
        marimo then offers to re-run the cells that follow.
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
        "structure",
        "The deposited entry, prepared and read. Preparing a structure is your job, not the "
        "pipeline's: stage 1 refuses a file whose pore axis is more than 10° from z, so "
        "example 06's `prepare.py` takes one dodecamer of 2WCD, turns its axis onto z and puts "
        "the cap *cis*. Stage 1 then finds the axis itself and checks the symmetry.",
    )
    return


@app.cell
def _():
    # The values `prepare.py` uses, which this cell sets on it.
    preparation = {
        "CHAINS": "A B C D E F G H I J K L",  # the first dodecamer of the entry
        "REGISTRATION_RESIDUES": "8:292",  # the C-alpha centroid of these goes on the axis
        "CENTROID_Z_NM": 5.655,  # and at this height, with the bilayer centre at 0
    }
    structure_settings = {
        "structure.symmetry.point_group": "C12",  # the expected symmetry; stage 1 checks it
    }
    return preparation, structure_settings


@app.cell
def _(case, example, hashlib, importlib, preparation, structure_settings):
    script = example.parent / "06-pdb-to-mesh" / "prepare.py"
    prepared = example / (
        "2wcd-prepared-" + hashlib.sha256(repr(preparation).encode()).hexdigest()[:8] + ".pdb"
    )
    if not prepared.exists():
        spec = importlib.util.spec_from_file_location("prepare", script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for key, value in preparation.items():
            setattr(module, key, value)
        module.prepare(
            example.parents[1] / "tests" / "data" / "structures" / "2wcd.pdb.gz", prepared
        )
    case_structure = case.with_(**structure_settings, **{"structure.source.path": str(prepared)})
    run_structure = case_structure.run(upto="structure", only=True)
    return case_structure, run_structure


@app.cell
def _(interactive, run_structure, scale, show):
    show(run_structure, "structure", scale=scale, interactive=interactive)
    return


@app.cell
def _(stage_card):
    stage_card(
        "density",
        "The atoms smeared into a density map: each atom a Gaussian sized by its van der "
        "Waals radius, summed on a grid. The pore wall is a contour of this map.",
    )
    return


@app.cell
def _():
    density_settings = {
        "geometry.density.grid_spacing_nm": 0.05,  # the grid spacing; this sets the mesh floor
        "geometry.density.sharpness": 0.93,  # how tightly each Gaussian hugs its atom
    }
    return (density_settings,)


@app.cell
def _(case_structure, density_settings, run_structure):
    assert run_structure.stages[-1].name == "structure"  # the structure block ran first
    case_density = case_structure.with_(**density_settings)
    run_density = case_density.run(upto="density", only=True)
    return case_density, run_density


@app.cell
def _(interactive, run_density, scale, show):
    show(run_density, "density", scale=scale, interactive=interactive)
    return


@app.cell
def _(stage_card):
    stage_card(
        "symmetry",
        "The density averaged around the pore axis, which reduces the 3D map to the (r, z) "
        "half-plane the solve works on. The spread around the mean shows how well the "
        "dodecamer obeys its symmetry.",
    )
    return


@app.cell
def _():
    # This stage has no setting of its own: it follows the point group (stage 1) and the grid
    # spacing (stage 2), so those are the values to change.
    symmetry_settings = {}
    return (symmetry_settings,)


@app.cell
def _(case_density, run_density, symmetry_settings):
    assert run_density.stages[-1].name == "density"  # the density block ran first
    case_symmetry = case_density.with_(**symmetry_settings)
    run_symmetry = case_symmetry.run(upto="symmetry", only=True)
    return case_symmetry, run_symmetry


@app.cell
def _(interactive, run_symmetry, scale, show):
    show(run_symmetry, "symmetry", scale=scale, interactive=interactive)
    return


@app.cell
def _(stage_card):
    stage_card(
        "contour",
        "The pore wall: the contour of the reduced density at one isolevel, smoothed and "
        "simplified to a clean profile. The feature-size gate runs here.",
    )
    return


@app.cell
def _():
    contour_settings = {
        "geometry.contour.isolevel": 0.25,  # the density that counts as the wall
        "geometry.contour.smoothing": "taubin",  # "none" keeps the raw contour
        "geometry.contour.simplify_tol_nm": 0.02,  # must stay below the grid spacing
    }
    return (contour_settings,)


@app.cell
def _(case_symmetry, contour_settings, run_symmetry):
    assert run_symmetry.stages[-1].name == "symmetry"  # the symmetry block ran first
    case_contour = case_symmetry.with_(**contour_settings)
    run_contour = case_contour.run(upto="contour", only=True)
    return case_contour, run_contour


@app.cell
def _(interactive, run_contour, scale, show):
    show(run_contour, "contour", scale=scale, interactive=interactive)
    return


@app.cell
def _(stage_card):
    stage_card(
        "region",
        "The computational domain: the pore profile joined to a bilayer and two reservoirs, "
        "each region and boundary named for the mesh and the solve.",
    )
    return


@app.cell
def _():
    region_settings = {
        "geometry.membrane.thickness_nm": 2.8,  # the bilayer
        "geometry.membrane.centre_z_nm": 0.0,  # in the structure's frame
        "geometry.reservoir.radius_nm": 250.0,
        # The ion-exclusion shell, `charge.exclusion_offset_nm`, is a setting of example 07's case.
    }
    return (region_settings,)


@app.cell
def _(case_contour, region_settings, run_contour):
    assert run_contour.stages[-1].name == "contour"  # the contour block ran first
    case_region = case_contour.with_(**region_settings)
    run_region = case_region.run(upto="region", only=True)
    return case_region, run_region


@app.cell
def _(interactive, run_region, scale, show):
    show(run_region, "region", scale=scale, interactive=interactive)
    return


@app.cell
def _(stage_card):
    stage_card(
        "mesh",
        "The finite-element mesh of that domain, refined at the pore wall where the electrical "
        "double layer lives. The quality gates run here.",
    )
    return


@app.cell
def _():
    mesh_settings = {
        "numerics.mesh.size_scale": 1.0,  # a multiplier on every element size
        "numerics.mesh.wall_h_nm": "auto",  # or a size in nm; auto follows the Debye length
        # None sizes `auto` at this case's own salt. A concentration here sizes it there, so a
        # salt sweep below that concentration shares one mesh.
        "numerics.mesh.wall_for_concentration_M": None,
    }
    return (mesh_settings,)


@app.cell
def _(case_region, mesh_settings, run_region):
    assert run_region.stages[-1].name == "region"  # the region block ran first
    case_mesh = case_region.with_(**mesh_settings)
    run_mesh = case_mesh.run(upto="mesh", only=True)
    return case_mesh, run_mesh


@app.cell
def _(interactive, run_mesh, scale, show):
    show(run_mesh, "mesh", scale=scale, interactive=interactive)
    return


if __name__ == "__main__":
    app.run()

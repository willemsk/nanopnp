import marimo

app = marimo.App(width="medium")


@app.cell
def _():
    from pathlib import Path

    import marimo as mo

    from nanopnp import CancelFlag, Cancelled, Case, Store, dumps_case, run_document
    from nanopnp.core.stages import StageDescription, register, walk_order
    from nanopnp.io.case_paths import with_section

    here = Path(__file__).resolve().parent
    store = Store(here / "store")
    return (
        CancelFlag,
        Cancelled,
        Case,
        StageDescription,
        dumps_case,
        here,
        mo,
        register,
        run_document,
        store,
        walk_order,
        with_section,
    )


@app.cell
def _(mo):
    mo.md(
        """
        # The Python interface

        A charged pore in 0.1 M NaCl, run from Python. Each section does one thing a
        modeller does with the interface: run with progress, stop a run, read the
        result, substitute a stage's input, edit the case, and add a stage of one's own.
        The store beside this file keeps what each step computes.
        """
    )
    return


@app.cell
def _(Case, here, store):
    case = Case.cylinder(
        concentration_M=0.1,
        bias_V=0.05,
        charge=here / "ring.field.yaml",
        outputs=["current", "transport_numbers"],
        name="notebook-pore",
        store=store,
        write=False,
    )
    return (case,)


@app.cell
def _(mo):
    mo.md("## 1 · Stop a run")
    return


@app.cell
def _(CancelFlag, Cancelled, case, dumps_case, mo, run_document):
    # The flag is set as the solve is about to start, so the run ends there.
    flag = CancelFlag()

    def at_solve(name, index, total):
        if name == "solve":
            flag.cancel()

    try:
        run_document(
            case.document,
            case_text=dumps_case(case.document),
            store=case.store,
            cancel=flag,
            on_stage=at_solve,
            write=False,
        )
        stopped = "The run was not stopped."
    except Cancelled as reason:
        stopped = f"The run stopped: {reason}."
    mo.md(stopped)
    return


@app.cell
def _(mo):
    mo.md("## 2 · Run with progress, and read the result")
    return


@app.cell
def _(case, dumps_case, run_document):
    reports = []
    result = run_document(
        case.document,
        case_text=dumps_case(case.document),
        store=case.store,
        progress=lambda fraction, message: reports.append((fraction, message)),
        write=False,
    )
    result
    return reports, result


@app.cell
def _(mo, reports, result):
    fields = result.fields
    mo.md(
        f"{len(reports)} progress reports. I = {result.current_nA:.4g} nA. "
        f"The fluid is {len(fields.fluid[0])} nodes. "
        + " ".join(
            f"{record.name}: {'stored' if record.cached else 'computed'}."
            for record in result.stages
        )
    )
    return


@app.cell
def _(mo):
    mo.md(
        """
        ## 3 · Substitute a stage's input

        A finer mesh in place of the case's own. A stage's key moves when one of its
        inputs does, so the mesh key moves and the materials key, which never reads the
        mesh, does not.
        """
    )
    return


@app.cell
def _(Case, case, mo, store):
    finer = Case.cylinder(concentration_M=0.1, bias_V=0.05, maxh_nm=2.0, store=store, write=False)
    swapped = case.with_(**{"inputs.mesh.path": finer["inputs.mesh.path"]})

    def keys(handle):
        # A walk to a stage runs that stage's inputs alone, so each stage is walked to.
        return {
            r.name: r.hash[:12]
            for stop in ("mesh", "materials")
            for r in handle.run(upto=stop).stages
        }

    before = keys(case)
    after = keys(swapped)
    mo.md(
        "| stage | with its mesh | with the finer mesh |\n|---|---|---|\n"
        + "\n".join(
            f"| {name} | {before[name]} | {after[name]} |" for name in ("mesh", "materials")
        )
    )
    return


@app.cell
def _(mo):
    mo.md(
        """
        ## 4 · Edit the case

        The same case with a `charge:` section added. Which stages does that leave
        alone?
        """
    )
    return


@app.cell
def _(case, dumps_case, mo, result, run_document, with_section):
    edited = with_section(case.document, "charge")
    again = run_document(edited, case_text=dumps_case(edited), store=case.store, write=False)
    mo.md(
        " ".join(
            f"{record.name}: {'stored' if record.cached else 'computed'}"
            f"{'' if record.hash == result.artefacts[record.name].hash else ', new key'}."
            for record in again.stages
        )
    )
    return


@app.cell
def _(mo):
    mo.md(
        """
        ## 5 · Add a stage

        `selectivity.py` beside this file is a stage of one's own. It reads the
        quantities of interest and says which ion the pore passes. Registered, it is
        walked after the report.
        """
    )
    return


@app.cell
def _(StageDescription, register, walk_order):
    if "selectivity" not in walk_order():
        register(
            StageDescription(
                name="selectivity",
                number=13,
                title="Selectivity",
                inputs=("case", "qoi"),
                outputs=("a verdict",),
                artefact_schema="nanopnp/selectivity-notebook/v1",
                takes_workspace=False,
                takes_store=False,
                key_is_artefact=False,
                weight=0.01,
                needs_section=None,
                optional_inputs=(),
            ),
            "selectivity:SelectivityStage",
        )
    return


@app.cell
def _(case, dumps_case, mo, run_document):
    extended = run_document(
        case.document, case_text=dumps_case(case.document), store=case.store, write=False
    )
    verdict = extended.artefacts["selectivity"].summary
    mo.md(
        f"The last two stages: {', '.join(r.name for r in extended.stages[-2:])}. "
        f"t₊ = {verdict['transport_number']:.3f}: the pore passes the {verdict['verdict']}."
    )
    return


if __name__ == "__main__":
    app.run()

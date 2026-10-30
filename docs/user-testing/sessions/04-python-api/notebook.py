import marimo

app = marimo.App(width="medium")


@app.cell
def _():
    import shutil
    from pathlib import Path

    import marimo as mo
    from selectivity import selectivity

    from nanopnp import CancelFlag, Cancelled, Case, Session, Store
    from nanopnp.case import Charge

    here = Path(__file__).resolve().parent
    # A stage found in the store is not run, so a cancel cannot stop it: the account each section
    # gives of what is computed and what is stored holds only from an empty store.
    shutil.rmtree(here / "store", ignore_errors=True)
    session = Session(Store(here / "store"), write=False)
    return CancelFlag, Cancelled, Case, Charge, here, mo, selectivity, session


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
def _(Case, here):
    case = Case.cylinder(
        concentration_M=0.1,
        bias_V=0.05,
        charge=here / "ring.field.yaml",
        outputs=["current", "transport_numbers"],
        name="notebook-pore",
    )
    return (case,)


@app.cell
def _(mo):
    mo.md("## 1 · Stop a run")
    return


@app.cell
def _(CancelFlag, Cancelled, case, mo, session):
    # The flag is set as the solve is about to start, so the run ends there.
    flag = CancelFlag()

    def at_solve(name, index, total):
        if name == "solve":
            flag.cancel()

    try:
        session.run(case, cancel=flag, on_stage=at_solve)
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
def _(case, session):
    reports = []
    result = session.run(
        case, progress=lambda fraction, message: reports.append((fraction, message))
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

        A finer mesh in place of the case's own: the element size of the pore's mesh, set
        from 4 nm to 2 nm. A stage's key moves when one of its inputs does, so the mesh key
        moves and the materials key, which never reads the mesh, does not.
        """
    )
    return


@app.cell
def _(case, mo, session):
    finer = case.with_(maxh_nm=2.0)

    def keys(candidate):
        # A walk to a stage runs that stage's inputs alone, so each stage is walked to.
        return {
            r.name: r.hash[:12]
            for stop in ("mesh", "materials")
            for r in session.run(candidate, upto=stop).stages
        }

    before = keys(case)
    after = keys(finer)
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
def _(Charge, case, mo, result, session):
    again = session.run(case.with_(charge=Charge()))
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

        `selectivity.py` beside this file is a stage of one's own: a function whose
        parameter names the stage it reads. It reads the quantities of interest and says
        which ion carries more than half of the current. Registered on the session, it is
        walked after the report.
        """
    )
    return


@app.cell
def _(selectivity, session):
    session.register_stage(selectivity)
    registered = "selectivity" in {info.name for info in session.stages}
    return (registered,)


@app.cell
def _(case, mo, registered, session):
    # Read from the cell above so that the walk below is ordered after the registration.
    assert registered
    extended = session.run(case)
    verdict = extended.artefacts["selectivity"].summary
    mo.md(
        f"The last two stages: {', '.join(r.name for r in extended.stages[-2:])}. "
        f"t₊ = {verdict['transport_number']:.3f}: the majority carrier: {verdict['verdict']}."
    )
    return


if __name__ == "__main__":
    app.run()

import marimo

app = marimo.App(width="medium")


@app.cell
def _():
    import os
    from pathlib import Path

    import marimo as mo

    from nanopnp import Case, Store
    from nanopnp.plot import figure as draw
    from nanopnp.plot import plot_iv
    from nanopnp.sweep import sweep

    here = Path(__file__).resolve().parent
    store = Store(os.environ.get("NANOPNP_STORE") or here.parent / ".store")
    ring = here.parents[1] / "examples" / "03-iv-sweep" / "cis-ring.field.yaml"
    return Case, draw, mo, plot_iv, ring, store, sweep


@app.cell
def _(mo):
    mo.md(
        """
        # An I-V sweep

        A charged cylindrical pore, its fixed charge a ring near the cis mouth, solved at
        several biases in one call. Each point warm-starts from a converged neighbour one
        step nearer the first bias solved, and the stages a point does not change come from
        the store. Opposite biases pair into a rectification ratio.

        Edit the biases and press **Sweep**.
        """
    )
    return


@app.cell
def _(mo):
    SWEEP_DEFAULTS = {
        "concentration_M": 0.1,
        "biases_mV": "-100, -50, 50, 100",
        "first_mV": 50.0,
    }
    sweep_form = mo.ui.dictionary(
        {
            "concentration_M": mo.ui.number(
                0.01, 3.0, 0.01, SWEEP_DEFAULTS["concentration_M"], label="NaCl (M)"
            ),
            "biases_mV": mo.ui.text(SWEEP_DEFAULTS["biases_mV"], label="biases (mV)"),
            "first_mV": mo.ui.number(
                -200.0, 200.0, 5.0, SWEEP_DEFAULTS["first_mV"], label="solved first (mV)"
            ),
        }
    ).form(submit_button_label="Sweep")
    sweep_form
    return SWEEP_DEFAULTS, sweep_form


@app.cell
def _(Case, SWEEP_DEFAULTS, ring, store, sweep, sweep_form):
    settings = sweep_form.value or SWEEP_DEFAULTS
    biases_V = [float(text) * 1e-3 for text in settings["biases_mV"].split(",")]
    first = min(range(len(biases_V)), key=lambda i: abs(biases_V[i] - settings["first_mV"] * 1e-3))
    case = Case.cylinder(
        concentration_M=settings["concentration_M"],
        bias_V=biases_V[first],
        charge=ring,
        outputs=("current", "transport_numbers", "eof_rate", "rectification"),
        name="iv-cylinder",
        store=store,
        write=False,
    )
    dataset = sweep(case, axis="bias_V", values=biases_V, origin=first).run()
    return (dataset,)


@app.cell
def _(dataset, draw, mo, plot_iv):
    mo.vstack(
        [
            plot_iv(dataset).get_figure(),
            mo.ui.table(dataset.summary["rows"], selection=None),
            mo.accordion({"Every quantity against the bias": draw(dataset)}),
        ]
    )
    return


if __name__ == "__main__":
    app.run()

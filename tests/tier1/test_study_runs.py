"""A queued run, unfolded: each silence named and each rung's closing test."""

from __future__ import annotations

import math

from nanopnp.gui.run_model import RunModel
from nanopnp.gui.solver import Finished, Iteration, RunEvent, Rung, Stage, Started
from nanopnp.gui.web.runs import convergence_plane, rung_rows

TOLERANCE = 1e-8

LADDER: tuple[RunEvent, ...] = (
    Started(case="tube.case.yaml", store=None),
    Stage("solve", 9, 11),
    # A rung whose model takes no Newton callback.
    Rung("Poisson", 1, 0, 4, reporting=False, tolerance=TOLERANCE),
    # A warm rung whose entry residual already met its target.
    Rung("bias 0.01 V", 2, 1, 4, reporting=True, tolerance=TOLERANCE),
    # A rung whose last step was forced: only the residual test can have closed it.
    Rung("bias 0.05 V", 2, 2, 4, reporting=True, tolerance=TOLERANCE),
    Iteration(1, 1e-2, 1e-1, 0.25, 3, forced=False),
    Iteration(2, 1e-9, 5e-7, 0.0625, 5, forced=True),
    # A rung closed by the update test; its first update is no number a decade can place.
    Rung("bias 0.1 V", 2, 3, 4, reporting=True, tolerance=TOLERANCE),
    Iteration(1, 1e-3, 0.0, 1.0, 1, forced=False),
    Iteration(2, 1e-6, 2e-9, 1.0, 1, forced=False),
    Finished(directory="runs/tube/0123"),
)


def _run(events: tuple[RunEvent, ...]) -> RunModel:
    model = RunModel()
    model.consume(events)
    return model


def test_ver44_the_unfolded_run_names_each_silence_and_what_closed_each_rung() -> None:
    # Two silences drawn alike, or a rung credited to a test its numbers do not prove, misstate
    # the solve.
    model = _run(LADDER).convergence
    rows = rung_rows(model)
    assert [row["rung"] for row in rows] == ["Poisson", "bias 0.01 V", "bias 0.05 V", "bias 0.1 V"]
    silent, entry, forced, update = rows
    assert silent["note"] == "no Newton steps: this rung's model takes no Newton callback"
    assert (silent["steps"], silent["closed_on"], silent["damping"]) == ("—", "—", "—")
    assert entry["note"].startswith("converged on entry")
    assert (entry["steps"], entry["closed_on"], entry["forced"]) == ("0", "—", "0")
    assert (forced["closed_on"], forced["forced"], forced["damping"]) == (
        "residual test",
        "1",
        "0.0625",
    )
    assert forced["last"] == "5.00e-07 > 1e-08"
    assert "1 forced (NUM-16)" in forced["note"]
    assert (update["closed_on"], update["forced"], update["damping"]) == ("update test", "0", "1")
    assert update["last"] == "2.00e-09 ≤ 1e-08"

    drawing = convergence_plane(model).json()
    kinds = [layer["kind"] for layer in drawing["layers"]]
    assert "rule" not in kinds  # no threshold: the tolerance is each rung's own
    bands = [layer for layer in drawing["layers"] if layer["kind"] == "band"]
    assert [(band["label"], band["note"]) for band in bands] == [
        ("Poisson", "no Newton steps"),
        ("bias 0.01 V", "converged on entry"),
        ("bias 0.05 V", ""),
        ("bias 0.1 V", ""),
    ]
    # Each band's curves stay inside it: none is drawn across a silent rung.
    lines = {
        layer["id"]: layer["points_nm"] for layer in drawing["layers"] if layer["kind"] == "line"
    }
    assert sorted(lines) == ["residual-2", "residual-3", "update-2", "update-3"]
    start, _ = bands[2]["x"]
    assert lines["residual-2"] == [start + 0.5, -2.0, start + 1.5, -9.0]
    assert lines["update-3"] == [bands[3]["x"][0] + 1.5, math.log10(2e-9)]
    (panel,) = drawing["panels"]
    assert panel["y_scale"] == "log"
    # Nine decades, 1e-9 to 1e-1, ticked at every other one.
    assert panel["extent_nm"][2:] == [-9.0, -1.0]
    assert panel["y_ticks"] == [-9.0, -7.0, -5.0, -3.0, -1.0]
    # The update no decade can place is omitted and counted, not drawn at the floor; the entry
    # shows the count in its summary above the plot.
    assert "1 sample(s) omitted" in model.summary

    # A solve served from the store is said to be one, not drawn as an empty plot.
    served = _run((Started("tube.case.yaml", None), Stage("solve", 9, 11), Finished("runs/t/1")))
    assert served.convergence.state == "served"
    assert rung_rows(served.convergence) == []
    drawing = convergence_plane(served.convergence).json()
    assert drawing["layers"] == []
    assert "served from the artefact store" in drawing["notes"][0]

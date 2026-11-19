"""A queued run, unfolded: each silence named and each rung's closing test."""

from __future__ import annotations

import json
import math
from collections.abc import Callable
from pathlib import Path
from typing import Any

from nanopnp.api.case import Case
from nanopnp.api.session import Session
from nanopnp.gui.convergence import ConvergenceModel
from nanopnp.gui.run_model import RunModel
from nanopnp.gui.solver import Finished, Iteration, RunEvent, Rung, Stage, Started
from nanopnp.gui.web.runs import (
    OTHER_SOLVE_NOTE,
    SERVED_NOTE,
    convergence_plane,
    recorded_convergence,
    rung_rows,
)
from nanopnp.io.store import Store
from nanopnp.solve.state import NEWTON_HISTORY_KEY
from nanopnp.validation.charged_tube import write_charged_tube

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


class _Feed:
    """A solve hook that drives a convergence model, as the shell's queue does."""

    def __init__(self, model: ConvergenceModel) -> None:
        self.model = model

    def rung(
        self, name: str, stage: int, index: int, total: int, reporting: bool, tolerance: float
    ) -> None:
        self.model.rung(name, stage, index, total, reporting, tolerance)

    def step(
        self,
        iteration: int,
        residual: float,
        update: float,
        damping: float,
        trials: int,
        forced: bool,
    ) -> None:
        self.model.step(iteration, residual, update, damping, trials, forced)

    def rung_solved(self, name: str, seconds: float, iterations: int) -> None:
        del name, seconds, iterations


def _bands(model: ConvergenceModel) -> list[dict[str, object]]:
    return [layer for layer in convergence_plane(model).json()["layers"] if layer["kind"] != "line"]


def test_ver44_a_recorded_run_replays_the_convergence_its_solve_reported(tmp_path: Path) -> None:
    # A replay that dropped which rungs report, their tolerance or a forced step would credit a
    # recorded rung to a test, or a silence, its solve never showed.
    live = ConvergenceModel()
    session = Session(Store(tmp_path / "store", runs=tmp_path / "runs"))
    run = session.run(Case.load(write_charged_tube(tmp_path / "tube")), on_solve=_Feed(live))
    live.settle(finished=True)
    live.count_omitted()
    replayed = recorded_convergence(run.directory)
    assert replayed is not None
    assert live.bands and any(band.steps for band in live.bands)
    assert rung_rows(replayed) == rung_rows(live)
    assert _bands(replayed) == _bands(live)
    assert convergence_plane(replayed).json() == convergence_plane(live).json()
    assert replayed.summary == live.summary
    assert replayed.note == ""

    # Served from the store, the record replays its maker's steps and says so; a run whose solve
    # was its own, its earlier stages served, says nothing of the kind.
    again = Session(Store(tmp_path / "store", runs=tmp_path / "again")).run(
        Case.load(tmp_path / "tube" / "case.yaml")
    )
    served = recorded_convergence(again.directory)
    assert served is not None and served.summary.endswith(SERVED_NOTE)
    assert rung_rows(served) == rung_rows(live)
    text = (tmp_path / "tube" / "case.yaml").read_text(encoding="utf-8")
    other = tmp_path / "tube" / "bias.yaml"
    other.write_text(text.replace("bias_V: 0.05", "bias_V: 0.04"), encoding="utf-8")
    biased = Session(Store(tmp_path / "store", runs=tmp_path / "biased")).run(Case.load(other))
    assert [stage.cached for stage in biased.stages if stage.name == "mesh"] == [True]
    own = recorded_convergence(biased.directory)
    assert own is not None and own.note == ""

    history = run.artefacts["solve"].payload[NEWTON_HISTORY_KEY]
    original = history.read_text(encoding="utf-8")
    stepped = next(index for index, band in enumerate(live.bands) if band.steps)

    def replay_edited(edit: Callable[[list[dict[str, Any]]], None]) -> ConvergenceModel:
        record = json.loads(original)
        edit(record["rungs"])
        history.write_text(json.dumps(record), encoding="utf-8")
        found = recorded_convergence(run.directory)
        assert found is not None
        return found

    # A forced last step closes on the residual test even with its update below the tolerance;
    # a step that does not say whether it was forced is credited to neither test.
    def forced_below(rungs: list[dict[str, Any]]) -> None:
        last = rungs[stepped]["steps"][-1]
        last["update"], last["forced"] = 0.1 * live.bands[stepped].tolerance, True

    assert replay_edited(forced_below).bands[stepped].closed_on() == "residual"

    def unsaid(rungs: list[dict[str, Any]]) -> None:
        forced_below(rungs)
        for step in rungs[stepped]["steps"]:
            del step["forced"]

    assert replay_edited(unsaid).bands[stepped].closed_on() == ""

    # A history rewritten under the key, by a rebuild or a warm start, is named as another solve's.
    def rewritten(rungs: list[dict[str, Any]]) -> None:
        rungs[stepped]["steps"].pop()

    assert replay_edited(rewritten).summary.endswith(OTHER_SOLVE_NOTE)

    # A history written before the rungs recorded whether they report claims neither silence,
    # and takes the tolerance the solve was keyed with.
    def older_history(rungs: list[dict[str, Any]]) -> None:
        for rung in rungs:
            del rung["reporting"], rung["tolerance"]

    older = replay_edited(older_history)
    silent = [band for band in older.bands if not band.steps]
    assert silent, "the charged tube's ladder has a rung with no step"
    for band in silent:
        assert band.note() == "no step recorded; this record does not say which silence"
    assert [band.tolerance for band in older.bands] == [band.tolerance for band in live.bands]
    notes = {layer["label"]: layer["note"] for layer in _bands(older)}
    assert {notes[band.name] for band in silent} == {"no step recorded"}

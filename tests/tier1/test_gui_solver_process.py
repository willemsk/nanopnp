"""VER-43: a real spawned solve, reporting and cancelling across the boundary."""

from __future__ import annotations

import json
import time
from pathlib import Path

from nanopnp.core.hashing import decode_floats
from nanopnp.gui.run_model import RunModel, run_outcome
from nanopnp.gui.solver import (
    Cancelled,
    Failed,
    Finished,
    Iteration,
    Progress,
    RunEvent,
    Rung,
    RunRequest,
    SolverProcess,
    Stage,
    Started,
)
from nanopnp.io.manifest import CASE_FILENAME, MANIFEST_FILENAME
from nanopnp.pipeline.run import RUN_RECORD_FILENAME

TIMEOUT_S = 300.0


def _settle(process: SolverProcess) -> tuple[RunEvent, ...]:
    found: list[RunEvent] = []
    deadline = time.monotonic() + TIMEOUT_S
    while time.monotonic() < deadline:
        found.extend(process.drain())
        if any(isinstance(event, (Finished, Failed, Cancelled)) for event in found):
            process.join(TIMEOUT_S)
            found.extend(process.drain())
            return tuple(found)
        if not process.running:
            time.sleep(0.05)
            found.extend(process.drain())
            break
        time.sleep(0.02)
    process.join(1.0)
    return tuple(found)


def test_fr27_a_spawned_run_reports_progress_and_finishes(
    cylindrical_pore_case: Path, tmp_path: Path
) -> None:
    store = tmp_path / "store"
    process = SolverProcess(RunRequest(case=str(cylindrical_pore_case), store=str(store)))
    process.start()
    events = _settle(process)

    assert isinstance(events[0], Started)
    assert any(isinstance(event, Stage) for event in events)
    assert any(isinstance(event, Progress) for event in events)
    finished = [event for event in events if isinstance(event, Finished)]
    assert finished, [type(event).__name__ for event in events]
    assert process.exit_code == 0

    stages = [event for event in events if isinstance(event, Stage)]
    assert [event.index for event in stages] == list(range(len(stages)))
    assert {event.total for event in stages} == {len(stages)}

    directory = Path(finished[0].directory)
    for name in (MANIFEST_FILENAME, CASE_FILENAME, RUN_RECORD_FILENAME):
        assert (directory / name).is_file(), name

    rungs = [event for event in events if isinstance(event, Rung)]
    steps = [event for event in events if isinstance(event, Iteration)]
    assert rungs, [type(event).__name__ for event in events]
    assert steps, "a real spawned solve reported no Newton step"
    assert [event.index for event in rungs] == list(range(len(rungs)))
    assert {event.total for event in rungs} == {len(rungs)}
    for step in steps:
        assert isinstance(step.residual, float)
        assert isinstance(step.update, float)
    manifest = decode_floats(
        json.loads((directory / MANIFEST_FILENAME).read_text(encoding="utf-8"))
    )
    recorded = {
        entry["rung"]: entry["newton"]
        for entry in manifest["solver"]["run"]["rungs"]
        if isinstance(entry["newton"], dict)
    }
    banded: dict[str, list[Iteration]] = {}
    current = ""
    for event in events:
        if isinstance(event, Rung):
            current = event.name
            banded[current] = []
        elif isinstance(event, Iteration):
            banded[current].append(event)
    reported = {name: taken for name, taken in banded.items() if taken}
    assert reported, "no rung reported a step"
    for name, taken in reported.items():
        assert taken[-1].residual == recorded[name]["residual"], name
        assert len(taken) == recorded[name]["iterations"], name

    model = RunModel()
    model.consume(events)
    assert model.state == "finished"
    assert model.fraction == 1.0
    outcome = model.outcome()
    assert outcome is not None
    assert outcome.directory == directory
    assert "current_A" in outcome.quantities
    assert outcome.stages
    switches = {entry["path"] for entry in outcome.deviations["switches"]}
    assert "electrolyte.corrections.viscosity.model" in switches
    assert run_outcome(directory).quantities == outcome.quantities

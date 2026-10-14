"""VER-43: a real spawned solve, reporting and cancelling across the boundary."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from nanopnp.core.hashing import decode_floats
from nanopnp.gui.run_model import RunControl, RunModel, run_outcome
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


def test_fr27_a_child_killed_without_reporting_settles_the_run_as_failed(
    cylindrical_pore_case: Path, tmp_path: Path
) -> None:
    control = RunControl()
    control.start(cylindrical_pore_case, store=tmp_path / "store")
    assert control.process is not None
    child = control.process._process
    assert child is not None
    child.kill()
    child.join(TIMEOUT_S)
    deadline = time.monotonic() + TIMEOUT_S
    model = control.poll()
    while not model.settled and time.monotonic() < deadline:
        time.sleep(0.02)
        model = control.poll()

    assert model.state == "failed"
    assert model.exit_code != 0
    assert "without reporting a result" in model.diagnosis
    assert str(control.process.exit_code) in model.diagnosis


def test_fr27_cancelling_a_spawned_run_writes_no_artefact(
    cylindrical_pore_case: Path, tmp_path: Path
) -> None:
    store = tmp_path / "store"
    process = SolverProcess(RunRequest(case=str(cylindrical_pore_case), store=str(store)))
    process.start()
    process.cancel()
    events = _settle(process)

    cancelled = [event for event in events if isinstance(event, Cancelled)]
    assert cancelled, [type(event).__name__ for event in events]
    assert "cancelled before" in cancelled[0].where
    assert not process.running

    model = RunModel()
    model.consume(events)
    assert model.state == "cancelled"
    assert model.outcome() is None

    written = [path for path in store.rglob("*") if path.is_file()] if store.exists() else []
    assert not written, f"a cancelled run left {written} in the store"


def test_fr27_a_case_the_schema_refuses_comes_back_as_the_case_exit_class(
    tmp_path: Path,
) -> None:
    from nanopnp.core.errors import EXIT_CASE

    path = tmp_path / "broken.yaml"
    path.write_text("schema: nanopnp/case/v0.5\nname: broken\n", encoding="utf-8")
    process = SolverProcess(RunRequest(case=str(path), store=str(tmp_path / "store")))
    process.start()
    events = _settle(process)

    failed = [event for event in events if isinstance(event, Failed)]
    assert failed, [type(event).__name__ for event in events]
    assert failed[0].exit_code == EXIT_CASE
    assert "electrolyte" in failed[0].message


PROFILE_CASE = """
schema: nanopnp/case/v0.5
name: shell-geometry
inputs:
  profile: {{path: {profile}}}
geometry: {{reservoir: {{radius_nm: 30.0}}}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 1.0
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics: {{model: pnp-ns, solid_permittivities: {{protein: 20.0, membrane: 3.2}}}}
numerics: {{mesh: {{size_scale: 20.0}}}}
"""


@pytest.fixture(scope="module")
def profile_case(tmp_path_factory: pytest.TempPathFactory) -> Path:
    import numpy as np

    from nanopnp.geometry.profile import (
        PROFILE_SCHEMA,
        PoreProfile,
        ProfileProvenance,
        min_feature_size,
        min_vertex_spacing,
        signed_area,
        write_profile,
    )

    work = tmp_path_factory.mktemp("geometry")
    points = [(2.0, -3.0), (3.0, -3.0), (6.0, 3.0), (5.0, 3.0)]
    array = np.asarray(points)
    profile = write_profile(
        PoreProfile(
            schema=PROFILE_SCHEMA,
            name="parallelogram",
            provenance=ProfileProvenance(
                source="test",
                citation="tests/tier1/test_gui_solver_process.py",
                sha256="0" * 64,
                vertex_count=len(points),
                min_vertex_spacing_nm=min_vertex_spacing(array),
                min_feature_size_nm=min_feature_size(array),
                signed_area_nm2=signed_area(array),
            ),
            vertices=points,
        ),
        work / "profile.yaml",
    )
    path = work / "case.yaml"
    path.write_text(PROFILE_CASE.format(profile=profile), encoding="utf-8")
    return path


def test_ver55_a_spawned_geometry_build_reports_each_stored_artefact(
    profile_case: Path, tmp_path: Path
) -> None:
    from nanopnp.gui.solver import Produced
    from nanopnp.io.store import Store

    store = tmp_path / "store"
    process = SolverProcess(RunRequest(case=str(profile_case), store=str(store), upto="mesh"))
    process.start()
    events = _settle(process)

    produced = [event for event in events if isinstance(event, Produced)]
    assert [event.name for event in produced] == ["case", "region", "mesh"]
    assert isinstance(events[-1], Finished), [type(event).__name__ for event in events]
    last_produced = max(index for index, event in enumerate(events) if isinstance(event, Produced))
    assert last_produced < len(events) - 1
    for event in produced:
        assert Path(event.store) == store.resolve()
        assert Store(event.store).get(event.schema, event.hash) is not None, event.name
        assert not event.cached

    model = RunModel()
    model.consume(events)
    assert model.state == "finished"
    assert [event.name for event in model.produced] == ["case", "region", "mesh"]
    assert model.convergence.state == "idle"
    record = json.loads((Path(events[-1].directory) / RUN_RECORD_FILENAME).read_text("utf-8"))
    assert [stage["hash"] for stage in record["stages"]] == [event.hash for event in produced]


def test_ver55_cancelling_a_geometry_build_writes_no_artefact(
    profile_case: Path, tmp_path: Path
) -> None:
    store = tmp_path / "store"
    process = SolverProcess(RunRequest(case=str(profile_case), store=str(store), upto="mesh"))
    process.start()
    process.cancel()
    events = _settle(process)

    assert any(isinstance(event, Cancelled) for event in events), events
    written = [path for path in store.rglob("*") if path.is_file()] if store.exists() else []
    assert not written, f"a cancelled build left {written} in the store"


def test_ver60_a_spawned_charge_build_reports_both_halves_of_stage_7(
    charged_tube, tmp_path: Path
) -> None:
    from nanopnp.gui.solver import Produced
    from nanopnp.io.store import Store

    case = charged_tube.write(tmp_path / "case")
    store = tmp_path / "store"
    process = SolverProcess(RunRequest(case=str(case), store=str(store), upto="charge"))
    process.start()
    events = _settle(process)

    produced = [event for event in events if isinstance(event, Produced)]
    assert [event.name for event in produced] == [
        "case",
        "region",
        "mesh",
        "protonation",
        "charge",
    ]
    assert isinstance(events[-1], Finished), [type(event).__name__ for event in events]
    for event in produced:
        assert Store(event.store).get(event.schema, event.hash) is not None, event.name


def test_ver60_cancelling_a_charge_build_writes_no_artefact(charged_tube, tmp_path: Path) -> None:
    case = charged_tube.write(tmp_path / "case")
    store = tmp_path / "store"
    process = SolverProcess(RunRequest(case=str(case), store=str(store), upto="charge"))
    process.start()
    process.cancel()
    events = _settle(process)

    assert any(isinstance(event, Cancelled) for event in events), events
    written = [path for path in store.rglob("*") if path.is_file()] if store.exists() else []
    assert not written, f"a cancelled build left {written} in the store"

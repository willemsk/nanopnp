"""VER-43 — a real spawned solve, reporting and cancelling across the boundary.

Not a mock. What ADR-004 asks for is a *background process*, and the failure
modes it has are exactly the ones a mock cannot have: an event that does not
pickle, a queue that empties after the child exits, a cancellation that never
reaches the child because the token was copied instead of shared, and an
artefact left in the store by a run that was stopped.

What WP15 adds to it is the second half of the same claim (VER-44): the
continuation rung and the Newton step cross as *numbers*. The residual reaches a
progress caption only inside a ``:.3e``, which is three significant figures of
something a convergence plot needs six orders of, and the relative update reaches
it not at all — so what is asserted below is that the last step of each rung
equals the ``newton`` record the run's own manifest carries, to the last bit.

The case is the cheapest one that walks the whole pipeline — the same
cylindrical pore ``tests/tier1/test_run.py`` uses, whose full run takes about a
second — because a driver defect that only an expensive solve reveals is not a
driver defect. The stabilisation mode is ``none`` (NUM-11).
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

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
from nanopnp.io.run import RUN_RECORD_FILENAME
from nanopnp.mesh.primitives import CylindricalPoreGeometry

PORE = CylindricalPoreGeometry(
    pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0
)
MAXH_NM = 4.0
WALL_H_NM = 1.0

CASE = """
schema: nanopnp/case/v2
name: shell-run
inputs:
  mesh:
    path: {mesh_path}
    format: vol
    groups: {{default: interface}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 0.1
  parameters: willems2020_nacl
  corrections:
    diffusivity:  {{model: none}}
    mobility:     {{model: none}}
    viscosity:    {{model: none}}
    permittivity: {{model: none}}
    density:      {{model: none}}
boundary_conditions: {{bias_V: 0.02, ground: cis}}
physics: {{model: epnp-ns, solid_permittivities: {{membrane: 3.2}}}}
numerics: {{continuation: default_ladder, stabilisation: none}}
outputs: [current, transport_numbers, eof_rate]
"""

TIMEOUT_S = 300.0
"""Generous: the child pays a ``spawn`` re-import of the package and of NGSolve
before it does any work, and a loaded CI runner is slow at both."""


@pytest.fixture(scope="module")
def case_file(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Write the case and the mesh it names, once for the module."""
    work = tmp_path_factory.mktemp("shell")
    mesh_path = work / "pore.vol"
    PORE.generate(maxh_nm=MAXH_NM, wall_h_nm=WALL_H_NM).ngmesh.Save(str(mesh_path))
    path = work / "case.yaml"
    path.write_text(CASE.format(mesh_path=mesh_path), encoding="utf-8")
    return path


def _settle(process: SolverProcess) -> tuple[RunEvent, ...]:
    """Drain until the child posts a terminal event, or time out saying so."""
    found: list[RunEvent] = []
    deadline = time.monotonic() + TIMEOUT_S
    while time.monotonic() < deadline:
        found.extend(process.drain())
        if any(isinstance(event, (Finished, Failed, Cancelled)) for event in found):
            process.join(TIMEOUT_S)
            found.extend(process.drain())
            return tuple(found)
        if not process.running:
            # The child exited without reporting: drain whatever is left and
            # fail on it below rather than spinning to the deadline.
            time.sleep(0.05)
            found.extend(process.drain())
            break
        time.sleep(0.02)
    process.join(1.0)
    return tuple(found)


def test_fr27_a_spawned_run_reports_progress_and_finishes(case_file: Path, tmp_path: Path) -> None:
    """A real run posts its start, its stages, its progress and its directory.

    And everything it posted crossed a process boundary, which is the claim: an
    event carrying a ``Path``, an artefact or a live token would have failed to
    pickle here and nowhere else.
    """
    store = tmp_path / "store"
    process = SolverProcess(RunRequest(case=str(case_file), store=str(store)))
    process.start()
    events = _settle(process)

    assert isinstance(events[0], Started)
    assert any(isinstance(event, Stage) for event in events)
    assert any(isinstance(event, Progress) for event in events)
    finished = [event for event in events if isinstance(event, Finished)]
    assert finished, [type(event).__name__ for event in events]
    assert process.exit_code == 0

    # The stage hook forwarded positions as data, not as a parsed caption.
    stages = [event for event in events if isinstance(event, Stage)]
    assert [event.index for event in stages] == list(range(len(stages)))
    assert {event.total for event in stages} == {len(stages)}

    directory = Path(finished[0].directory)
    for name in (MANIFEST_FILENAME, CASE_FILENAME, RUN_RECORD_FILENAME):
        assert (directory / name).is_file(), name

    # VER-44: the ladder crossed as data too, and the numbers are the solver's.
    rungs = [event for event in events if isinstance(event, Rung)]
    steps = [event for event in events if isinstance(event, Iteration)]
    assert rungs, [type(event).__name__ for event in events]
    assert steps, "a real spawned solve reported no Newton step"
    assert [event.index for event in rungs] == list(range(len(rungs)))
    assert {event.total for event in rungs} == {len(rungs)}
    for step in steps:
        # Floats, not the three significant figures of a ``:.3e`` caption. A
        # string that survived the queue would pass ``isinstance(str)`` and fail
        # here, which is the point.
        assert isinstance(step.residual, float)
        assert isinstance(step.update, float)
    # And they are the numbers the run's own record carries. The manifest's
    # solver group is written by the solve stage from the same ``NewtonResult``
    # the hook's last step came from, so agreeing to the last bit is what makes
    # the plot the solver's numbers rather than a parse of a display format.
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
    # Read back out of the run directory, not carried through the queue: the
    # directory is the run's own record (§5.3.3), and a panel reading anything
    # else would show what the QR-08 reproduction check could not reconstruct.
    outcome = model.outcome()
    assert outcome is not None
    assert outcome.directory == directory
    assert "current_A" in outcome.quantities
    assert outcome.stages
    # Five corrections off against the validated default, and the model that
    # follows from them: the panel shows them beside the number (FR-25).
    switches = {entry["path"] for entry in outcome.deviations["switches"]}
    assert "electrolyte.corrections.viscosity.model" in switches
    assert run_outcome(directory).quantities == outcome.quantities


def test_fr27_cancelling_a_spawned_run_writes_no_artefact(case_file: Path, tmp_path: Path) -> None:
    """A cancelled run says where it stopped, exits, and leaves the store empty.

    §5.3.2: a cancelled stage writes no artefact, so the store never holds a
    partial result. Cancelling immediately means the first
    :func:`~nanopnp.core.stages.check_cancelled` of the walk fires, before any
    stage has run — which is the case where an artefact left behind would be
    most obviously wrong.
    """
    store = tmp_path / "store"
    process = SolverProcess(RunRequest(case=str(case_file), store=str(store)))
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
    """The child classifies its own failure and reports the §3.1 class.

    Run through the real boundary rather than through
    :func:`~nanopnp.gui.solver.failure_event` alone, because what is in doubt is
    not the classifier but whether a failure in the child reaches the parent at
    all: an exception that escaped ``_worker`` would leave the parent waiting on
    a queue that never carries another event.
    """
    from nanopnp.cli.errors import EXIT_CASE

    path = tmp_path / "broken.yaml"
    path.write_text("schema: nanopnp/case/v2\nname: broken\n", encoding="utf-8")
    process = SolverProcess(RunRequest(case=str(path), store=str(tmp_path / "store")))
    process.start()
    events = _settle(process)

    failed = [event for event in events if isinstance(event, Failed)]
    assert failed, [type(event).__name__ for event in events]
    assert failed[0].exit_code == EXIT_CASE
    assert "electrolyte" in failed[0].message

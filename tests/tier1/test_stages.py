"""VER-25 — the stage protocol, the registry, and the three promises FR-27 makes.

Every stage of section 5.2 must be independently invocable, cancellable and
introspectable. Each of those is a claim that fails quietly:

- *introspectable* fails by working — ``nanopnp stage --list`` answers correctly
  while importing NGSolve, and nobody notices until a sweep dispatches a job
  array and pays 370 ms per worker for a question about a stage's inputs. The
  subprocess tests below are the only way to see it;
- *cancellable* fails by leaving a partial artefact behind, or by not stopping
  until the stage would have finished anyway;
- the registry's descriptions fail by drifting from the stages they describe,
  because they are deliberately written somewhere else.
"""

from __future__ import annotations

import importlib
import json
import subprocess
import sys

import pytest

from nanopnp.core.stages import (
    CancelFlag,
    Cancelled,
    StageDescription,
    _catalogue,
    check_cancelled,
    create,
    describe,
    register,
    registered_stages,
    report,
)
from nanopnp.io.artefact import StageInputs
from nanopnp.io.case import loads_case

MINIMAL = """
schema: nanopnp/case/v1
name: minimal
inputs: {mesh: {path: pore.vol, format: vol}}
electrolyte:
  species: [{name: Na+, z: +1}, {name: Cl-, z: -1}]
  concentration_M: 1.0
  parameters: willems2020_nacl
boundary_conditions: {bias_V: 0.1}
physics: {model: pnp-ns}
"""


def _in_subprocess(script: str) -> dict[str, object]:
    """Run ``script`` in a fresh interpreter and return the JSON it prints."""
    completed = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=True
    )
    result: dict[str, object] = json.loads(completed.stdout)
    return result


# -- introspection ------------------------------------------------------------


def test_ver25_every_stage_describes_itself_without_importing_it() -> None:
    """Listing and describing stages imports neither NGSolve nor the stage modules.

    The registry holds each description beside a ``module:attribute`` target
    string precisely so this is true. Asserted in a subprocess because this
    session has imported everything many times over, and the in-process check
    would pass no matter what the registry did.
    """
    script = (
        "import sys, json;"
        "from nanopnp.core.stages import registered_stages;"
        "names = [d.name for d in registered_stages()];"
        "print(json.dumps({'names': names,"
        " 'ngsolve': 'ngsolve' in sys.modules,"
        " 'solve': 'nanopnp.solve.stage' in sys.modules,"
        " 'materials': 'nanopnp.materials.stage' in sys.modules,"
        " 'charge': 'nanopnp.charge.stage' in sys.modules,"
        " 'mesh': 'nanopnp.mesh.ingest' in sys.modules,"
        " 'post': 'nanopnp.post.stage' in sys.modules}))"
    )
    reported = _in_subprocess(script)
    assert reported["names"] == ["mesh", "charge", "materials", "case", "solve", "qoi", "report"]
    assert reported["ngsolve"] is False
    assert reported["solve"] is False
    assert reported["materials"] is False
    assert reported["charge"] is False
    assert reported["mesh"] is False
    assert reported["post"] is False


def test_ver25_a_stage_description_matches_the_stage_it_describes() -> None:
    """Each registered target resolves, and its ``describe()`` is the registry's row.

    The description is written in the registry rather than beside the class, so
    that answering a question about a stage need not import it. The cost of that
    is that the two can drift; this is what stops them.
    """
    for name, entry in _catalogue().items():
        module_name, _, attribute = entry.target.partition(":")
        stage = getattr(importlib.import_module(module_name), attribute)()
        assert stage.name == name
        assert stage.describe() == entry.description


def test_ver25_the_pipeline_numbers_match_section_5_2() -> None:
    """Stages are numbered by their position in the section 5.2 table."""
    numbered = {entry.name: entry.number for entry in registered_stages()}
    assert numbered == {
        "mesh": 6,
        "charge": 7,
        "materials": 8,
        "case": 9,
        "solve": 10,
        "qoi": 11,
        "report": 12,
    }


def test_ver25_an_unknown_stage_is_refused_by_name() -> None:
    """The diagnostic lists the stages that exist, because this is a typo's home."""
    with pytest.raises(KeyError, match="materials"):
        describe("solver")
    with pytest.raises(KeyError, match="materials"):
        create("solver")


def test_ver25_a_stage_cannot_be_registered_twice() -> None:
    """Replacing a registered stage would let two runs share a manifest."""
    description = StageDescription(
        name="solve",
        number=10,
        title="Solve",
        inputs=(),
        outputs=(),
        artefact_schema="nanopnp/solution/v2",
    )
    with pytest.raises(ValueError, match="already registered"):
        register(description, "nanopnp.solve.stage:SolveStage")


def test_ver25_a_malformed_target_is_refused() -> None:
    """A target must name a module and an attribute, or nothing can resolve it."""
    description = StageDescription(
        name="not-a-stage",
        number=99,
        title="",
        inputs=(),
        outputs=(),
        artefact_schema="x/v1",
    )
    with pytest.raises(ValueError, match="module:attribute"):
        register(description, "nanopnp.solve.stage.SolveStage")


# -- progress and cancellation ------------------------------------------------


def test_ver25_progress_is_clamped_into_the_unit_interval() -> None:
    """A stage that miscounts its rungs still drives a progress bar."""
    seen: list[float] = []
    report(lambda fraction, message: seen.append(fraction), 1.7, "over")
    report(lambda fraction, message: seen.append(fraction), -0.2, "under")
    assert seen == [1.0, 0.0]


def test_ver25_a_cancelled_token_raises_naming_where_it_stopped() -> None:
    """``Cancelled`` says how far the run got, which is what an operator asks."""
    flag = CancelFlag()
    check_cancelled(flag, "the solve")  # not set: nothing happens
    flag.cancel()
    with pytest.raises(Cancelled, match="the solve"):
        check_cancelled(flag, "the solve")


def test_ver25_cancellation_is_not_an_error_subclass_of_the_gates() -> None:
    """A cancelled run is distinguishable from a diverged one.

    Both unwind the same call stack. If cancellation were caught by the same
    ``except`` an operator uses for a gate violation, "I stopped it" and "it
    produced a wrong answer" would read identically in the log.
    """
    from nanopnp.solve.gates import GateViolationError

    assert not issubclass(Cancelled, GateViolationError)
    assert issubclass(Cancelled, RuntimeError)


# -- the materials stage, which needs no mesh ---------------------------------


def test_ver25_the_materials_stage_reports_progress_ending_at_one() -> None:
    """Stage 8 runs alone, from the case and nothing else."""
    seen: list[float] = []
    stage = create("materials")
    artefact = stage.run(
        StageInputs(case=loads_case(MINIMAL)),
        progress=lambda fraction, message: seen.append(fraction),
    )
    assert seen == sorted(seen)
    assert seen[-1] == 1.0
    assert artefact.schema == stage.describe().artefact_schema
    assert artefact.hash


def test_ver25_a_cancelled_stage_returns_no_artefact() -> None:
    """Cancellation raises rather than returning a partial result (section 5.3.2)."""
    flag = CancelFlag()
    flag.cancel()
    with pytest.raises(Cancelled):
        create("materials").run(StageInputs(case=loads_case(MINIMAL)), cancel=flag)


def test_ver25_a_stage_invoked_without_its_upstream_says_which_one() -> None:
    """Running a stage alone is exactly when a missing input shows up."""
    inputs = StageInputs(case=loads_case(MINIMAL))
    with pytest.raises(KeyError, match="materials"):
        inputs.require("materials")

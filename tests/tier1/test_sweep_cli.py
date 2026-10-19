"""VER-38 (Tier 1): the sweep dispatch and collection surface (FR-24, IF-02, FR-23)."""

from __future__ import annotations

import json
import multiprocessing
import subprocess
import sys
from pathlib import Path

import pytest

from nanopnp.cli import build_parser, main
from nanopnp.core.errors import EXIT_OK
from nanopnp.core.hashing import decode_floats
from nanopnp.sweep.collect import DATASET_CSV, DATASET_FILENAME, collect
from nanopnp.sweep.plan import plan_from_document, write_plan
from nanopnp.sweep.run import THREAD_VARIABLES, MemberResult, pin_threads

BASE = """
schema: nanopnp/case/v0.5
name: base
inputs:
  mesh: {{path: {mesh}, format: vol, groups: {{default: interface}}}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 0.1
  parameters: willems2020_nacl
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics: {{model: epnp-ns, solid_permittivities: {{membrane: 3.2}}}}
numerics: {{continuation: default_ladder}}
outputs: [current]
"""

SWEEP = """
schema: nanopnp/sweep/v0.5
name: probe
base: base.yaml
axes:
  - name: bias
    path: boundary_conditions.bias_V
    values: [-0.05, 0.05]
"""


@pytest.fixture
def planned(tmp_path: Path) -> Path:
    (tmp_path / "base.yaml").write_text(BASE.format(mesh=tmp_path / "pore.vol"), encoding="utf-8")
    (tmp_path / "sweep.yaml").write_text(SWEEP, encoding="utf-8")
    plan = plan_from_document(tmp_path / "sweep.yaml", check_meshes=False)
    return write_plan(plan, tmp_path / "run")


# -- the parser ---------------------------------------------------------------


# FR-25
def test_ver38_no_sweep_flag_changes_a_case_file_field() -> None:
    from nanopnp.io.case import CaseDocument

    fields = {name for name in CaseDocument.model_fields} | {
        "bias_V",
        "concentration_M",
        "temperature_K",
        "model",
        "flow",
        "continuation",
        "stabilisation",
    }
    parser = build_parser()
    actions = [
        action
        for group in parser._subparsers._group_actions
        for sub in group.choices.values()
        if sub.prog.endswith("sweep")
        for nested in sub._subparsers._group_actions
        for parsed in nested.choices.values()
        for action in parsed._actions
    ]
    assert actions, "the sweep subparsers must have been walked"
    for action in actions:
        assert action.dest not in fields, (
            f"'--{action.dest}' names a case-file field; a flag duplicating one would make the "
            "manifest describe one of two disagreeing sources of truth (IF-02)"
        )


# -- the exit-code contract ---------------------------------------------------


# -- the worker initialiser ---------------------------------------------------


# QR-06
def test_ver38_the_thread_pinning_is_set_before_numpy_is_imported() -> None:
    script = (
        "import sys, json;"
        "from nanopnp.sweep.run import pin_threads;"
        "before = 'numpy' in sys.modules;"
        "found = pin_threads();"
        "print(json.dumps({'numpy_before': before, 'set': found}))"
    )
    found = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=True
    )
    payload = json.loads(found.stdout)
    assert payload["numpy_before"] is False, (
        "importing nanopnp.sweep.run must not import numpy, or the initialiser is too late"
    )
    assert payload["set"] == dict.fromkeys(THREAD_VARIABLES, "1")


def test_ver38_a_spawned_worker_inherits_the_pinned_environment() -> None:
    context = multiprocessing.get_context("spawn")
    with context.Pool(processes=1, initializer=pin_threads) as pool:
        found = pool.apply(_environment_of_worker)
    assert found == dict.fromkeys(THREAD_VARIABLES, "1")


def _environment_of_worker() -> dict[str, str]:
    import os

    return {variable: os.environ.get(variable, "") for variable in THREAD_VARIABLES}


# -- the dataset and its export ----------------------------------------------


def _member(index: int, *, ok: bool) -> MemberResult:
    return MemberResult(
        index=index,
        point_id=f"{index:012x}",
        assignments={"boundary_conditions.bias_V": 0.05 * (1 if index else -1)},
        wave=index,
        status="ok" if ok else "failed",
        exit_class=EXIT_OK if ok else 5,
        error=None if ok else "NewtonDivergenceError: the residual grew",
        quantities=(
            {"current_A": 1.5e-11 * (1 if index else -1), "bias_V": 0.05 * (1 if index else -1)}
            if ok
            else None
        ),
        seconds=1.25,
    )


def test_ver38_the_dataset_round_trips_to_identical_values(planned: Path) -> None:
    from nanopnp.sweep.plan import read_plan

    plan = read_plan(planned)
    members = (_member(0, ok=True), _member(1, ok=True))
    artefact = collect(plan, planned.parent, members=members)
    written = decode_floats(
        json.loads((planned.parent / DATASET_FILENAME).read_text(encoding="utf-8"))
    )
    assert written["rows"] == [member.row() for member in members]
    assert artefact.summary["rows"] == written["rows"]
    assert artefact.parameters == {"name": "probe", "points": 2}
    assert artefact.inputs["plan"] == plan.hash


# QR-06
def test_ver38_a_failed_member_keeps_its_quantities_absent(planned: Path) -> None:
    from nanopnp.sweep.plan import read_plan

    plan = read_plan(planned)
    artefact = collect(plan, planned.parent, members=(_member(0, ok=True), _member(1, ok=False)))
    rows = list(artefact.summary["rows"])
    assert rows[1]["quantities"] is None
    assert rows[1]["exit_class"] == 5
    assert artefact.summary["counts"] == {"failed": 1, "ok": 1}
    assert artefact.summary["exit_classes"] == {"5": 1}


# QR-06
def test_ver38_a_point_no_member_ran_is_a_row_and_not_a_gap(planned: Path) -> None:
    from nanopnp.sweep.plan import read_plan

    plan = read_plan(planned)
    artefact = collect(plan, planned.parent, members=(_member(0, ok=True),))
    rows = list(artefact.summary["rows"])
    assert len(rows) == 2
    assert rows[1]["status"] == "not_dispatched"
    assert rows[1]["quantities"] is None
    assert rows[1]["exit_class"] is None


def test_ver38_collect_reads_the_member_files_a_job_array_left_behind(
    planned: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["sweep", "run", str(planned), "--index", "1", "--store", str(tmp_path / "s")])
    capsys.readouterr()

    code = main(["sweep", "collect", str(planned), "--csv", "--json"])
    assert code == EXIT_OK
    summary = json.loads(capsys.readouterr().out)
    assert summary["counts"] == {"failed": 1, "not_dispatched": 1}
    rows = {int(row["index"]): row for row in summary["rows"]}
    assert rows[0]["status"] == "not_dispatched"
    assert rows[1]["status"] == "failed"
    assert (planned.parent / DATASET_FILENAME).is_file()
    assert (planned.parent / DATASET_CSV).is_file()


def test_ver23_a_trans_grounded_pair_is_oriented_by_the_biases_its_members_recorded() -> None:
    from types import SimpleNamespace

    from nanopnp.sweep.collect import _rectification

    def member(index: int, bias_V: float, current_A: float) -> MemberResult:
        return MemberResult(
            index=index,
            point_id=f"p{index}",
            assignments={"boundary_conditions.bias_V": -bias_V},
            wave=0,
            status="ok",
            quantities={"bias_V": bias_V, "current_A": current_A},
        )

    rows = {0: member(0, -0.1, -1.0e-9), 1: member(1, 0.1, 3.0e-9)}
    produced, notes = _rectification(SimpleNamespace(pairs=((0, 1),)), rows)  # type: ignore[arg-type]
    assert notes == []
    assert produced == [
        {
            "forward": 1,
            "reverse": 0,
            "forward_id": "p1",
            "reverse_id": "p0",
            "bias_V": 0.1,
            "rectification": pytest.approx(3.0),
        }
    ]

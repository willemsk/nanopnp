"""VER-38 (Tier 1): the sweep dispatch and collection surface (FR-24, IF-02, FR-23)."""

from __future__ import annotations

import json
import multiprocessing
import subprocess
import sys
from pathlib import Path

import pytest

from nanopnp.cli import build_parser, main
from nanopnp.core.errors import EXIT_CASE, EXIT_GATE, EXIT_OK
from nanopnp.core.hashing import decode_floats
from nanopnp.sweep.collect import DATASET_CSV, DATASET_FILENAME, collect, write_csv
from nanopnp.sweep.plan import PLAN_FILENAME, plan_from_document, write_plan
from nanopnp.sweep.run import MEMBERS_DIRNAME, THREAD_VARIABLES, MemberResult, pin_threads

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


def test_ver38_the_three_sub_subcommands_parse_and_dispatch() -> None:
    parser = build_parser()
    for argv, action in (
        (["sweep", "plan", "s.yaml"], "plan"),
        (["sweep", "run", "p.json", "--index", "3"], "run"),
        (["sweep", "collect", "p.json", "--csv"], "collect"),
    ):
        args = parser.parse_args(argv)
        assert args.command == "sweep"
        assert args.action == action
        assert callable(args.handler)


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


# CON-07
def test_ver38_sweep_plan_writes_a_plan_and_prints_its_waves(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "base.yaml").write_text(BASE.format(mesh=tmp_path / "pore.vol"), encoding="utf-8")
    (tmp_path / "sweep.yaml").write_text(SWEEP, encoding="utf-8")

    code = main(
        [
            "sweep",
            "plan",
            str(tmp_path / "sweep.yaml"),
            "--store",
            str(tmp_path / "store"),
            "--no-mesh-check",
            "--json",
        ]
    )
    assert code == EXIT_OK
    payload = json.loads(capsys.readouterr().out)
    assert payload["points"] == 2
    assert payload["waves"] == [[0, 1], [1, 2]]
    assert Path(payload["plan"]).name == PLAN_FILENAME
    assert Path(payload["plan"]).is_file()
    assert "sweeps" in Path(payload["directory"]).parts


def test_ver38_sweep_plan_directory_moves_the_plan_and_refuses_another_plan(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "base.yaml").write_text(BASE.format(mesh=tmp_path / "pore.vol"), encoding="utf-8")
    (tmp_path / "sweep.yaml").write_text(SWEEP, encoding="utf-8")
    target = tmp_path / "iv"
    argv = ["sweep", "plan", str(tmp_path / "sweep.yaml"), "--no-mesh-check"]
    argv += ["--store", str(tmp_path / "store"), "--directory", str(target), "--json"]

    assert main(argv) == EXIT_OK
    first = json.loads(capsys.readouterr().out)
    assert first["plan"] == str(target / PLAN_FILENAME)
    assert main(argv) == EXIT_OK, "the same plan into the same directory is not a conflict"
    capsys.readouterr()

    (tmp_path / "sweep.yaml").write_text(SWEEP.replace("[-0.05, 0.05]", "[-0.1, 0.1]"))
    assert main(argv) == EXIT_CASE
    assert "different sweep" in capsys.readouterr().err
    written = json.loads((target / PLAN_FILENAME).read_text(encoding="utf-8"))
    assert decode_floats(written)["hash"] == first["hash"]


def test_ver38_a_misspelt_axis_exits_with_the_case_class(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "base.yaml").write_text(BASE.format(mesh=tmp_path / "pore.vol"), encoding="utf-8")
    (tmp_path / "sweep.yaml").write_text(
        SWEEP.replace("boundary_conditions.bias_V", "boundary_conditions.bais_V"),
        encoding="utf-8",
    )
    code = main(["sweep", "plan", str(tmp_path / "sweep.yaml"), "--store", str(tmp_path / "store")])
    assert code == EXIT_CASE
    assert "did you mean 'bias_V'" in capsys.readouterr().err


# -- the exit-code contract ---------------------------------------------------


# VER-32, QR-12
def test_ver38_both_sweep_exceptions_are_in_the_exit_enumeration() -> None:
    from nanopnp.core.errors import EXIT_CODES

    assert EXIT_CODES["nanopnp.sweep.plan:SweepPlanError"] == EXIT_CASE
    assert EXIT_CODES["nanopnp.sweep.collect:SweepCollectionError"] == EXIT_GATE


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        ("nanopnp.io.case:CaseValidationError", EXIT_CASE),
        ("nanopnp.numerics.gates:GateViolationError", EXIT_GATE),
        ("nanopnp.numerics.newton:NewtonDivergenceError", 5),
        ("nanopnp.core.stages:Cancelled", 130),
    ],
)
def test_ver38_a_member_records_the_exit_class_of_what_it_raised(error: str, expected: int) -> None:
    from nanopnp.core.errors import classify

    module, _, name = error.partition(":")
    raised = getattr(__import__(module, fromlist=[name]), name)
    assert classify(raised.__new__(raised)) == expected


def test_ver38_a_run_index_exits_with_the_members_own_class(
    planned: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(
        [
            "sweep",
            "run",
            str(planned),
            "--index",
            "0",
            "--store",
            str(tmp_path / "store"),
            "--json",
        ]
    )
    assert code == EXIT_CASE
    row = json.loads(capsys.readouterr().out)
    assert row["status"] == "failed"
    assert row["exit_class"] == EXIT_CASE
    assert row["quantities"] is None, "a failed member's current must not read as a number"
    assert "FileNotFoundError" in row["error"]
    assert (planned.parent / MEMBERS_DIRNAME / "000000.json").is_file()


def test_ver38_a_local_sweep_exits_zero_with_a_failed_member(
    planned: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(["sweep", "run", str(planned), "--store", str(tmp_path / "store"), "--json"])
    assert code == EXIT_OK
    summary = json.loads(capsys.readouterr().out)
    assert summary["counts"] == {"failed": 2}
    assert (planned.parent / DATASET_FILENAME).is_file()


def test_ver38_fail_fast_stops_and_exits_with_the_first_failure(
    planned: Path, tmp_path: Path
) -> None:
    code = main(["sweep", "run", str(planned), "--store", str(tmp_path / "store"), "--fail-fast"])
    assert code == EXIT_CASE
    written = sorted((planned.parent / MEMBERS_DIRNAME).glob("*.json"))
    assert len(written) == 1, "fail-fast stops after the first wave that failed"


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


def test_ver38_the_csv_leads_with_status_and_empties_a_failed_rows_quantities(
    planned: Path,
) -> None:
    import csv

    from nanopnp.sweep.plan import read_plan

    plan = read_plan(planned)
    artefact = collect(plan, planned.parent, members=(_member(0, ok=True), _member(1, ok=False)))
    path = write_csv(artefact, planned.parent)
    assert path.name == DATASET_CSV

    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0].startswith("#") and "derived export" in lines[0]
    rows = list(csv.reader(lines[1:]))
    header, ok_row, failed_row = rows[0], rows[1], rows[2]
    assert header[0] == "status"
    assert ok_row[0] == "ok"
    assert failed_row[0] == "failed"

    current = header.index("current_A")
    assert ok_row[current] != ""
    assert failed_row[current] == "", "a failed member's current must be empty, never zero"


def test_ver38_a_directory_belonging_to_another_sweep_is_refused(planned: Path) -> None:
    from nanopnp.sweep.collect import SweepCollectionError
    from nanopnp.sweep.plan import read_plan

    plan = read_plan(planned)
    stray = _member(0, ok=True)
    stray = MemberResult(**{**stray.__dict__, "index": 99})
    with pytest.raises(SweepCollectionError, match="another sweep"):
        collect(plan, planned.parent, members=(stray,))


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


# QR-06
def test_ver38_an_unreadable_member_record_is_named_rather_than_skipped(planned: Path) -> None:
    from nanopnp.sweep.collect import SweepCollectionError, read_members

    members = planned.parent / MEMBERS_DIRNAME
    members.mkdir(parents=True, exist_ok=True)
    (members / "000000.json").write_text("{ this is not json", encoding="utf-8")
    with pytest.raises(SweepCollectionError, match="not a readable member record"):
        read_members(planned.parent)


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


def test_qr06_a_member_record_is_replaced_whole_and_leaves_no_temporary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from nanopnp.io import store as store_module

    directory = tmp_path / MEMBERS_DIRNAME
    first = MemberResult(index=3, point_id="p3", assignments={}, wave=0, status="failed")
    path = first.write(directory)
    second = MemberResult(
        index=3, point_id="p3", assignments={}, wave=0, status="ok", quantities={"current_A": 1.0}
    )
    second.write(directory)
    assert decode_floats(json.loads(path.read_text(encoding="utf-8")))["status"] == "ok"
    assert [entry.name for entry in directory.iterdir()] == [path.name]

    def refuse(self: Path, target: Path) -> Path:
        raise OSError("the rename was interrupted")

    monkeypatch.setattr(store_module.Path, "replace", refuse)
    with pytest.raises(OSError, match="interrupted"):
        first.write(directory)
    assert decode_floats(json.loads(path.read_text(encoding="utf-8")))["status"] == "ok"
    assert [entry.name for entry in directory.iterdir()] == [path.name]

"""VER-38 (Tier 1) — the sweep dispatch and collection surface (FR-24, IF-02, FR-23).

Three sub-subcommands over one plan file, and the properties that make them a
usable job-array surface rather than a wrapper.

**No flag changes a case-file field.** The axes are in the sweep document, which
is where a physics quantity belongs (the §3.1 configuration NOTE applied one level
up). ``--index``, ``--wave`` and ``--workers`` choose which members run and on how
many processes; a ``--bias`` flag would be a second source of truth reaching no
manifest.

**A single-member dispatch exits with that member's own code, and a local sweep
does not.** The IF-02 exit NOTE exists so a job array can branch per member; a
local sweep is different, because non-convergence at the corners of a hard
envelope is an expected *result* and turning it into a nonzero exit would make a
sweep that worked indistinguishable from one that was broken.

**The thread pinning is in place before the linear-algebra libraries are
imported.** QR-06's scaling claim is about independent workers, and N processes
sharing one BLAS pool are not independent. Asserted in a spawned subprocess on
``sys.modules`` and ``os.environ``, because it is a claim about import *order*
that no in-process assertion can make.

The equivalence of a member solved alone and the same member solved inside the
sweep is the other half of VER-38 and needs two converged solves; it is
``tests/tier2/test_sweep.py``.
"""

from __future__ import annotations

import json
import multiprocessing
import subprocess
import sys
from pathlib import Path

import pytest

from nanopnp.cli import build_parser, main
from nanopnp.cli.errors import EXIT_CASE, EXIT_GATE, EXIT_OK
from nanopnp.core.hashing import decode_floats
from nanopnp.sweep.collect import DATASET_CSV, DATASET_FILENAME, collect, write_csv
from nanopnp.sweep.plan import PLAN_FILENAME, plan_from_document, write_plan
from nanopnp.sweep.run import MEMBERS_DIRNAME, THREAD_VARIABLES, MemberResult, pin_threads

BASE = """
schema: nanopnp/case/v1
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
schema: nanopnp/sweep/v1
name: probe
base: base.yaml
axes:
  - name: bias
    path: boundary_conditions.bias_V
    values: [-0.05, 0.05]
"""


@pytest.fixture
def planned(tmp_path: Path) -> Path:
    """Write a two-point plan into a sweep directory and return the plan path.

    Nothing here solves: the mesh path is never read, because every assertion in
    this module is about the command-line surface, the record shapes and the
    exit codes.
    """
    (tmp_path / "base.yaml").write_text(BASE.format(mesh=tmp_path / "pore.vol"), encoding="utf-8")
    (tmp_path / "sweep.yaml").write_text(SWEEP, encoding="utf-8")
    plan = plan_from_document(tmp_path / "sweep.yaml", check_meshes=False)
    return write_plan(plan, tmp_path / "run")


# -- the parser ---------------------------------------------------------------


def test_ver38_the_three_sub_subcommands_parse_and_dispatch() -> None:
    """``sweep plan``, ``sweep run`` and ``sweep collect`` all reach one handler."""
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


def test_ver38_no_sweep_flag_changes_a_case_file_field() -> None:
    """IF-02, one level up: the axes are in the document, never on the command line.

    Enumerated against the case schema's own field tree rather than against a
    list written here, so a flag added later that happens to be named after a
    case-file field fails this rather than becoming a second source of truth
    the FR-25 manifest cannot see.
    """
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


def test_ver38_sweep_plan_writes_a_plan_and_prints_its_waves(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The plan lands in the store's sweep directory, and the wave ranges are printed.

    The ranges *are* the scheduler integration: a job array is two lines of the
    user's own shell over them, one dependent array per wave, and a scheduler
    library on the end-user path is what CON-07 forbids.
    """
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
    """``--directory`` chooses where the plan goes, and never mixes two sweeps.

    Re-planning the same document into the same directory is allowed, since it
    is the same plan; planning a different one there exits with the case class
    and leaves the first plan in place.
    """
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
    """``SweepPlanError`` is exit 3: the fix is an edit, and a retry fails identically."""
    (tmp_path / "base.yaml").write_text(BASE.format(mesh=tmp_path / "pore.vol"), encoding="utf-8")
    (tmp_path / "sweep.yaml").write_text(
        SWEEP.replace("boundary_conditions.bias_V", "boundary_conditions.bais_V"),
        encoding="utf-8",
    )
    code = main(["sweep", "plan", str(tmp_path / "sweep.yaml"), "--store", str(tmp_path / "store")])
    assert code == EXIT_CASE
    assert "did you mean 'bias_V'" in capsys.readouterr().err


# -- the exit-code contract ---------------------------------------------------


def test_ver38_both_sweep_exceptions_are_in_the_exit_enumeration() -> None:
    """VER-32's both-directions test covers them; this names the codes they carry.

    ``SweepPlanError`` is 3 because a plan is refused by an edit to a document.
    ``SweepCollectionError`` is 4 because the members have already run and the
    fix is to run the missing ones — a gate in the QR-12 sense rather than a
    case error.
    """
    from nanopnp.cli.errors import EXIT_CODES

    assert EXIT_CODES["nanopnp.sweep.plan:SweepPlanError"] == EXIT_CASE
    assert EXIT_CODES["nanopnp.sweep.collect:SweepCollectionError"] == EXIT_GATE


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        ("nanopnp.io.case:CaseValidationError", EXIT_CASE),
        ("nanopnp.solve.gates:GateViolationError", EXIT_GATE),
        ("nanopnp.solve.newton:NewtonDivergenceError", 5),
        ("nanopnp.core.stages:Cancelled", 130),
    ],
)
def test_ver38_a_member_records_the_exit_class_of_what_it_raised(error: str, expected: int) -> None:
    """Each failure class of the §3.1 NOTE reaches the member's row as its own code.

    Classified through the same :func:`~nanopnp.cli.errors.classify` the CLI
    uses, so a member dispatched with ``--index`` exits exactly as the same
    failure would from ``nanopnp run``. The four classes are the four a sweep
    member can actually produce: a bad case, a gate abort, non-convergence — the
    one a sweep may usefully re-dispatch from another neighbour — and
    cancellation.
    """
    from nanopnp.cli.errors import classify

    module, _, name = error.partition(":")
    raised = getattr(__import__(module, fromlist=[name]), name)
    assert classify(raised.__new__(raised)) == expected


def test_ver38_a_run_index_exits_with_the_members_own_class(
    planned: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """One member, one exit code — the IF-02 NOTE's whole purpose.

    The mesh this plan names does not exist, so the member fails with a
    ``FileNotFoundError``, which IF-02 classifies as the case class: the path is
    wrong and it will be just as wrong on the retry. What is asserted is the
    *wiring* — that the member's own class is what the process exits with —
    rather than which class this particular failure has.
    """
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
    """Every member reached a terminal state and the dataset was written, so 0.

    Non-convergence at the corners of a hard envelope is an expected result. A
    sweep that recorded two failures and wrote its dataset did its job; exiting
    nonzero would make it indistinguishable from one that was broken.
    """
    code = main(["sweep", "run", str(planned), "--store", str(tmp_path / "store"), "--json"])
    assert code == EXIT_OK
    summary = json.loads(capsys.readouterr().out)
    assert summary["counts"] == {"failed": 2}
    assert (planned.parent / DATASET_FILENAME).is_file()


def test_ver38_fail_fast_stops_and_exits_with_the_first_failure(
    planned: Path, tmp_path: Path
) -> None:
    """The other behaviour, for the caller who wants it, and it is opt-in."""
    code = main(["sweep", "run", str(planned), "--store", str(tmp_path / "store"), "--fail-fast"])
    assert code == EXIT_CASE
    written = sorted((planned.parent / MEMBERS_DIRNAME).glob("*.json"))
    assert len(written) == 1, "fail-fast stops after the first wave that failed"


# -- the worker initialiser ---------------------------------------------------


def test_ver38_the_thread_pinning_is_set_before_numpy_is_imported() -> None:
    """QR-06: the pinning must precede the import, or it measures the pool.

    NumPy and the BLAS behind it read these variables *when they are imported*
    and size their pool then; setting them afterwards has no effect at all. So
    this is a claim about import order, and the only honest way to assert it is
    in a fresh process: the initialiser runs, and ``sys.modules`` must not yet
    carry ``numpy``.

    The house rule deferring ``numpy`` and ``ngsolve`` to the function that uses
    them is what makes that true — at module scope they would be imported by the
    time the pool's initialiser ran — so this test is also what keeps that rule
    from being relaxed here.
    """
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
    """The initialiser reaches a real ``spawn`` worker, which is what the pool uses.

    ``spawn`` rather than ``fork``: a forked worker inherits a parent that has
    already imported NumPy, so the variables would be read before the initialiser
    could set them. It is also the only start method Windows has.
    """
    context = multiprocessing.get_context("spawn")
    with context.Pool(processes=1, initializer=pin_threads) as pool:
        found = pool.apply(_environment_of_worker)
    assert found == dict.fromkeys(THREAD_VARIABLES, "1")


def _environment_of_worker() -> dict[str, str]:
    """Return the thread variables as the worker process sees them.

    At module scope because a ``spawn`` worker unpickles it by name; a closure or
    a local function could not cross the process boundary.
    """
    import os

    return {variable: os.environ.get(variable, "") for variable in THREAD_VARIABLES}


# -- the dataset and its export ----------------------------------------------


def _member(index: int, *, ok: bool) -> MemberResult:
    """Return a member record without running anything."""
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
    """Written through ``canonical``, so every float comes back exactly.

    Not to a tolerance: the dataset is the artefact, and a current that changed
    in its last bits between writing and reading would be a difference nobody
    could attribute to physics or to encoding.
    """
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


def test_ver38_a_failed_member_keeps_its_quantities_absent(planned: Path) -> None:
    """``null``, never a zero. QR-06's whole demand is that it be distinguishable."""
    from nanopnp.sweep.plan import read_plan

    plan = read_plan(planned)
    artefact = collect(plan, planned.parent, members=(_member(0, ok=True), _member(1, ok=False)))
    rows = list(artefact.summary["rows"])
    assert rows[1]["quantities"] is None
    assert rows[1]["exit_class"] == 5
    assert artefact.summary["counts"] == {"failed": 1, "ok": 1}
    assert artefact.summary["exit_classes"] == {"5": 1}


def test_ver38_a_point_no_member_ran_is_a_row_and_not_a_gap(planned: Path) -> None:
    """A point nobody ran is a row: one of the three states QR-06 separates."""
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
    """The format the author opens, made unmissable in the one way that matters.

    Canonical JSON has ``null``; a CSV has the empty string, which a reader
    parses as ``0.0`` on a bad day. Putting the status first is the cheapest form
    of the same protection, and the header comment says the file is derived.
    """
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
    """A member record the plan does not enumerate names the mistake, rather than being dropped."""
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
    """``sweep collect`` builds the dataset from ``members/``, which is the job-array path.

    A job array writes those files from independent processes on independent
    machines and nothing ever holds the results in one memory. So the collector
    reads what arrived — and a point no member ran is a row saying so, rather
    than a gap a reader has to notice.
    """
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


def test_ver38_an_unreadable_member_record_is_named_rather_than_skipped(planned: Path) -> None:
    """A member whose result cannot be read is not a member that failed.

    Collecting around it would put a ``not_dispatched`` row in the dataset for a
    member that ran, which is the one distinction QR-06 asks the dataset to keep.
    """
    from nanopnp.sweep.collect import SweepCollectionError, read_members

    members = planned.parent / MEMBERS_DIRNAME
    members.mkdir(parents=True, exist_ok=True)
    (members / "000000.json").write_text("{ this is not json", encoding="utf-8")
    with pytest.raises(SweepCollectionError, match="not a readable member record"):
        read_members(planned.parent)

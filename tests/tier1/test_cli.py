"""VER-32 — the command-line surface, and the exit code as a contract (IF-02).

The CLI is a shell over the IF-01 stage objects (SPECIFICATION.md section 5.1),
so most of what could go wrong here is not arithmetic. It is the four things a
shell gets wrong quietly:

**The exit status is a contract.** FR-24's job array branches on it and QR-06
requires a member that *failed* to be distinguishable from one that was
*refused*. Section 3.1's NOTE (IF-02) therefore requires the exception-to-code
mapping to be an explicit enumeration and every public exception class of the
package to be classified or excluded with a reason, in both directions — so that
a class added later fails this file rather than silently becoming ``1``.

**Introspection must not import a stage.** ``nanopnp stage --list`` answers from
the registry; a stray module-scope import would cost every process of a sweep
``import ngsolve``'s ~370 ms. VER-25 asserts that of the registry, and this
asserts it of the process a user actually runs.

**Standard output carries only the result.** A sweep parsing stdout must not
receive log records, and a ``--json`` reader must be able to parse the whole
stream.

**No flag changes what is solved.** A flag duplicating a case-file setting would
make the FR-25 manifest describe one of two disagreeing sources of truth
(section 3.1 NOTE, IF-02), so the option names are enumerated against the
vocabulary of the case schema.

No solve happens here: exit codes 5 and 130 need one, and are discharged by
classifying an instance of each class — the same route the CLI's own code takes.
The end-to-end run is Tier 2's (VER-35). Stabilisation is ``none`` (NUM-11).
"""

from __future__ import annotations

import argparse
import ast
import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

import nanopnp
from nanopnp import __version__
from nanopnp.cli import build_parser, main
from nanopnp.cli.errors import (
    EXCLUDED,
    EXIT_CANCELLED,
    EXIT_CASE,
    EXIT_CODES,
    EXIT_CONVERGENCE,
    EXIT_GATE,
    EXIT_OK,
    EXIT_UNEXPECTED,
    EXIT_USAGE,
    classify,
)
from nanopnp.core.hashing import CanonicalisationError
from nanopnp.core.paths import (
    REFERENCE_DATA_VARIABLE,
    STORE_ROOT_VARIABLE,
    correction_file,
    reference_data_root,
    reference_file,
)
from nanopnp.io.manifest import MANIFEST_SCHEMA
from nanopnp.io.run import RUN_RECORD_FILENAME, RUN_SCHEMA
from nanopnp.mesh.primitives import CylindricalPoreGeometry
from nanopnp.solve.gates import GateViolationError

PORE = CylindricalPoreGeometry(
    pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0
)
CASE = """
schema: nanopnp/case/v2
name: cli-probe
inputs:
  mesh:
    path: {mesh_path}
    format: vol
    groups: {{default: interface}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 0.1
  temperature_K: 298.15
  parameters: willems2020_nacl
  corrections:
    diffusivity:  {{model: none}}
    mobility:     {{model: none}}
    viscosity:    {{model: none}}
    permittivity: {{model: none}}
    density:      {{model: none}}
boundary_conditions:
  bias_V: 0.02
  ground: cis
physics:
  model: epnp-ns
  solid_permittivities: {{membrane: 3.2}}
numerics:
  continuation: default_ladder
  stabilisation: none
outputs: [current, transport_numbers, eof_rate]
"""


@pytest.fixture(scope="module")
def case_file(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Write the reference case and the mesh it names, once for the module."""
    work = tmp_path_factory.mktemp("cli")
    mesh_path = work / "pore.vol"
    PORE.generate(maxh_nm=4.0, wall_h_nm=1.0).ngmesh.Save(str(mesh_path))
    path = work / "case.yaml"
    path.write_text(CASE.format(mesh_path=mesh_path), encoding="utf-8")
    return path


# -- the environment report ----------------------------------------------------


def test_cli_env_reports_data_location(capsys: pytest.CaptureFixture[str]) -> None:
    """``--env`` is retained as an alias for ``env``: removing it breaks callers."""
    assert main(["--env"]) == 0
    out = capsys.readouterr().out
    assert __version__ in out
    assert "corrections" in out or "data" in out


def test_packaged_correction_file_is_installed() -> None:
    assert correction_file("willems2020_nacl").is_file()


def test_val15_the_reference_archive_is_absent_rather_than_broken(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """An unset, misdirected or incomplete archive all read as "not available".

    Tier 3 compares against reference files far too large to vendor, and the
    skip condition that keeps that tier runnable elsewhere is exactly this
    ``None``. An exception here would turn "you do not have the archive" into a
    failing test run for everyone who does not (section 7.1).
    """
    monkeypatch.delenv(REFERENCE_DATA_VARIABLE, raising=False)
    assert reference_data_root() is None
    assert reference_file("prod5_clya_charge") is None

    monkeypatch.setenv(REFERENCE_DATA_VARIABLE, str(tmp_path / "absent"))
    assert reference_data_root() is None

    monkeypatch.setenv(REFERENCE_DATA_VARIABLE, str(tmp_path))
    assert reference_data_root() == tmp_path.resolve()
    assert reference_file("prod5_clya_charge") is None

    (tmp_path / "prod5_clya_charge").write_text("%Grid\n", encoding="utf-8")
    assert reference_file("prod5_clya_charge") == tmp_path.resolve() / "prod5_clya_charge"


# -- the exit-code enumeration -------------------------------------------------

_SOURCE_ROOT = Path(nanopnp.__file__).resolve().parent


def _public_exception_classes() -> dict[str, str]:
    """Return every public exception class under ``src/nanopnp``, by table key.

    Found by parsing the source rather than by importing it: importing every
    module to enumerate its exceptions would pull in NGSolve, and the point of
    the string-keyed table is that classification imports nothing. A class is an
    exception if it subclasses one of the builtin roots or another class found
    here — the closure below — which is what catches one added under a new base.
    """
    roots = {
        "Exception",
        "BaseException",
        "RuntimeError",
        "ValueError",
        "KeyError",
        "NotImplementedError",
        "TypeError",
        "OSError",
        "ArithmeticError",
        "ImportError",
        "LookupError",
    }
    found: dict[str, str] = {}
    definitions: list[tuple[str, str, list[str]]] = []
    for path in sorted(_SOURCE_ROOT.rglob("*.py")):
        module = ".".join(
            ("nanopnp", *path.relative_to(_SOURCE_ROOT).with_suffix("").parts)
        ).removesuffix(".__init__")
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.ClassDef) and not node.name.startswith("_"):
                definitions.append((module, node.name, [ast.unparse(b) for b in node.bases]))

    known = set(roots)
    for _ in range(len(definitions)):  # closure: a class may subclass one defined later
        for module, name, bases in definitions:
            if any(base.rsplit(".", 1)[-1] in known for base in bases):
                known.add(name)
                found[f"{module}:{name}"] = name
    return found


def test_ver32_every_public_exception_class_is_classified_or_excluded() -> None:
    """Both directions: nothing unlisted, and nothing listed that does not exist.

    Section 3.1's NOTE (IF-02) requires the exception-to-code mapping to be an
    enumeration rather than a base-class test, precisely so that a class added
    later fails here rather than silently becoming an unexplained ``1``. The
    reverse direction matters as much: an entry naming a class that was renamed
    is a rule that stopped applying without anyone noticing.
    """
    classes = _public_exception_classes()
    listed = set(EXIT_CODES) | set(EXCLUDED)

    unclassified = sorted(set(classes) - listed)
    assert not unclassified, (
        f"{unclassified} is a public exception class in src/nanopnp that cli/errors.py neither "
        "classifies nor excludes with a reason; it would exit 1 as 'unexpected' by accident"
    )

    ours = {key for key in listed if key.startswith("nanopnp.")}
    stale = sorted(ours - set(classes))
    assert not stale, f"{stale} is listed in cli/errors.py but no longer exists in src/nanopnp"

    assert not set(EXIT_CODES) & set(EXCLUDED), "a class is both classified and excluded"
    assert all(reason.strip() for reason in EXCLUDED.values()), "an exclusion carries no reason"


@pytest.mark.parametrize(
    ("key", "code"),
    [
        ("nanopnp.io.case:CaseValidationError", EXIT_CASE),
        ("nanopnp.post.stage:SelectionError", EXIT_CASE),
        ("nanopnp.solve.gates:GateViolationError", EXIT_GATE),
        ("nanopnp.post.qoi:RouteDisagreementError", EXIT_GATE),
        ("nanopnp.io.run:MissingUpstreamError", EXIT_GATE),
        ("nanopnp.solve.newton:NewtonDivergenceError", EXIT_CONVERGENCE),
        ("nanopnp.core.stages:Cancelled", EXIT_CANCELLED),
        ("nanopnp.core.stages:MissingExtraError", EXIT_CASE),
        ("nanopnp.structure.read:StructureInputError", EXIT_GATE),
        ("nanopnp.structure.axis:SymmetryGateError", EXIT_GATE),
    ],
)
def test_ver32_each_code_is_produced_by_an_instance_of_its_class(key: str, code: int) -> None:
    """The table is keyed on strings; this checks the strings name the real classes.

    A typo in a key is invisible to the enumeration above, which compares two
    sets of strings built the same way. Importing the class and classifying an
    instance of it is the third route: it fails if the module moved, if the name
    is misspelt, or if ``classify`` stops walking the MRO.
    """
    module_name, _, class_name = key.partition(":")
    klass = getattr(importlib.import_module(module_name), class_name)
    # Built with ``__new__`` rather than called: these constructors take the gate,
    # the quantity and its location (QR-12), and what is under test is that the
    # key names a class ``classify`` recognises, not how each one is raised.
    assert classify(klass.__new__(klass)) == code
    assert EXIT_CODES[key] == code


def test_ver32_classify_walks_the_mro_and_falls_back_to_unexpected() -> None:
    """A subclass inherits its base's code; an unrelated exception does not."""

    class StricterError(GateViolationError):
        """A gate added later under a classified base."""

    stricter = StricterError("packing fraction", "phi", 1.4, (0.0, 0.0))
    assert classify(stricter) == EXIT_GATE
    assert classify(RuntimeError("something else entirely")) == EXIT_UNEXPECTED
    assert classify(KeyboardInterrupt()) == EXIT_CANCELLED
    # Excluded classes classify as 1 *by decision*, which is what the exclusion
    # says; the enumeration above is what records that it was decided.
    assert classify(CanonicalisationError("a set is not canonicalisable")) == EXIT_UNEXPECTED


def test_ver32_classifying_imports_no_exception_module() -> None:
    """``import nanopnp.cli`` must not pull in the modules the table names.

    The table is strings and :func:`classify` walks ``type(error).__mro__``
    exactly so that the CLI's import cost stays at the ~70 ms the deferred-import
    rule protects. Importing ``nanopnp.solve.newton`` to classify a
    ``NewtonDivergenceError`` would drag NGSolve in behind it.
    """
    listed = sorted({key.partition(":")[0] for key in EXIT_CODES} - {"builtins"})
    code = (
        "import sys, json\n"
        "import nanopnp.cli, nanopnp.cli.errors\n"
        f"print(json.dumps([m for m in {listed!r} if m in sys.modules]))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert json.loads(result.stdout) == []


# -- the command surface -------------------------------------------------------


@pytest.mark.parametrize(
    ("argv", "handler"),
    [
        (["run", "case.yaml"], "_run"),
        (["stage", "--list"], "_stage"),
        (["stage", "mesh", "case.yaml"], "_stage"),
        (["inspect", "run-dir"], "_inspect"),
        (["reproduce", "run-dir"], "_reproduce"),
        (["env"], "_env"),
        (["mesh", "cylinder", "--out", "pore.msh"], "_mesh"),
        (["mesh", "reference", "--out", "clya.msh"], "_mesh"),
    ],
)
def test_ver32_every_subcommand_parses_and_dispatches(argv: list[str], handler: str) -> None:
    """Each subcommand of IF-02 reaches its own handler with the shared flags."""
    args = build_parser().parse_args(argv)
    assert args.handler.__name__ == handler
    assert args.json is False and args.verbose == 0 and args.traceback is False


def test_ver32_no_flag_changes_what_is_solved() -> None:
    """Section 3.1's NOTE (IF-02): flags choose where output goes, never the physics.

    Enumerated rather than argued: a flag named after a case-file section would
    make the FR-25 manifest describe one of two disagreeing sources of truth, and
    the way that arrives is somebody adding a convenience override.
    """
    physics = {
        "bias",
        "voltage",
        "concentration",
        "temperature",
        "salt",
        "species",
        "correction",
        "corrections",
        "model",
        "stabilisation",
        "stabilization",
        "ladder",
        "rtol",
        "tolerance",
        "outputs",
        "permittivity",
        "ground",
        "maxh",
        "order",
    }
    parser = build_parser()

    def nested(group: argparse.ArgumentParser) -> list[argparse.ArgumentParser]:
        """Every parser under ``group``, however deep, except the mesh generators.

        ``nanopnp mesh`` is excluded by section 3.1's generators NOTE: its
        geometric flags shape an *input file*, which a run later records by
        content hash through ``inputs.mesh`` like any external mesh, so they do
        not reach what a run solves.
        """
        found: list[argparse.ArgumentParser] = []
        for action in group._actions:
            if isinstance(action, argparse._SubParsersAction):
                for name, choice in action.choices.items():
                    if group is parser and name == "mesh":
                        continue
                    found += [choice, *nested(choice)]
        return found

    named = {
        option.lstrip("-").replace("-", "_")
        for group in (parser, *nested(parser))
        for action in group._actions
        for option in action.option_strings
    }
    # `--tolerance` on `reproduce` is the exception, and it is not physics: it
    # is how closely the *comparison* must agree, not what is solved.
    assert named & physics == {"tolerance"}


def test_ver32_stage_list_imports_no_stage_module(tmp_path: Path) -> None:
    """``nanopnp stage --list`` answers from the registry alone (VER-25, VER-32).

    VER-25 asserts this of the registry; this asserts it of the process a user
    actually runs, which is where a stray module-scope import in the CLI would
    show up. A sweep dispatching a job array pays ``import ngsolve``'s ~370 ms
    per process, so introspection that imports a stage is a real cost.
    """
    code = (
        "import sys, json\n"
        "from nanopnp.cli import main\n"
        "main(['stage', '--list'])\n"
        "loaded = sorted(m for m in sys.modules if m.startswith(('ngsolve', 'netgen')) "
        "or m in {'nanopnp.mesh.ingest', 'nanopnp.charge.stage', 'nanopnp.solve.stage', "
        "'nanopnp.post.stage', 'nanopnp.materials.stage', 'nanopnp.io.stage', "
        "'nanopnp.structure.stage', 'nanopnp.structure.read', 'MDAnalysis', 'gemmi', "
        "'nanopnp.density.stage', 'nanopnp.symmetry.stage', 'nanopnp.geometry.contour', "
        "'nanopnp.geometry.region', 'nanopnp.mesh.generate', 'skimage', 'shapely'})\n"
        "sys.stderr.write(json.dumps(loaded))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert json.loads(result.stderr) == []
    numbers = [line.split()[0] for line in result.stdout.splitlines()]
    assert numbers == ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]


def test_ver32_env_reports_the_store_and_the_reference_archive(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """``env`` names where artefacts go, and which variable moved it."""
    monkeypatch.setenv(STORE_ROOT_VARIABLE, str(tmp_path / "elsewhere"))
    monkeypatch.delenv(REFERENCE_DATA_VARIABLE, raising=False)
    assert main(["env", "--json"]) == 0
    found = json.loads(capsys.readouterr().out)
    assert found["store"] == str(tmp_path / "elsewhere")
    assert found[STORE_ROOT_VARIABLE] == str(tmp_path / "elsewhere")
    assert found["reference_data"] is None


# -- the exit codes, end to end ------------------------------------------------


def test_ver32_a_run_exits_zero_and_writes_where_run_dir_says(
    case_file: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """``run`` walks the pipeline and puts the three files where asked (FR-27).

    ``--run-dir`` moves output and nothing else: the run record's ``manifest``
    hash is the same one the driver computed, so the flag demonstrably did not
    reach the physics (section 3.1 NOTE, IF-02). Stopped at stage 6 — a solve
    belongs to Tier 2 (VER-35), and what is under test here is the shell.
    """
    where = tmp_path / "somewhere" / "else"
    code = main(
        [
            "run",
            str(case_file),
            "--upto",
            "mesh",
            "--store",
            str(tmp_path / "store"),
            "--run-dir",
            str(where),
            "--json",
        ]
    )
    assert code == EXIT_OK
    record = json.loads(capsys.readouterr().out)
    assert record["directory"] == str(where)
    assert [entry["stage"] for entry in record["stages"]] == ["case", "mesh"]
    assert (where / RUN_RECORD_FILENAME).is_file()
    assert json.loads((where / RUN_RECORD_FILENAME).read_text())["manifest"] == record["manifest"]


def test_ver32_a_case_the_schema_refuses_exits_three(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Exit 3: the case file is wrong and a retry will fail identically (QR-06)."""
    path = tmp_path / "bad.yaml"
    path.write_text("schema: nanopnp/case/v2\nname: bad\nnonsense: 1\n", encoding="utf-8")
    assert main(["run", str(path), "--store", str(tmp_path / "store")]) == EXIT_CASE
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "nonsense" in captured.err
    assert "Traceback" not in captured.err


def test_ver32_upto_naming_a_stage_the_run_does_not_walk_exits_three(
    case_file: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Exit 3, not 1: a typo in ``--upto`` is not a failure worth a retry (QR-06).

    ``1`` is the class whose traceback is worth keeping and the class a job
    array re-dispatches; this one fails identically every time, and the fix is
    an edit to the command line.
    """
    code = main(["run", str(case_file), "--upto", "sovle", "--store", str(tmp_path / "store")])
    assert code == EXIT_CASE
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "no stage 'sovle'" in captured.err
    assert "unexpected" not in captured.err
    assert "Traceback" not in captured.err


def test_ver32_only_with_an_empty_store_exits_four(
    case_file: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Exit 4: a gate stopped the run, naming what was missing (QR-12).

    ``--only`` is what makes a hand-substituted artefact testable (FR-27): it
    proves the stage read the substituted file rather than recomputing past it,
    and that only holds if a miss aborts.
    """
    code = main(
        ["stage", "materials", str(case_file), "--only", "--store", str(tmp_path / "empty")]
    )
    assert code == EXIT_GATE
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "mesh" in captured.err and "Traceback" not in captured.err


def test_ver32_a_usage_error_exits_two(capsys: pytest.CaptureFixture[str]) -> None:
    """Exit 2 comes from argparse, and from the CLI's own usage refusals."""
    with pytest.raises(SystemExit) as unknown:
        main(["frobnicate"])
    assert unknown.value.code == EXIT_USAGE

    with pytest.raises(SystemExit) as incomplete:
        main(["stage", "mesh"])  # a name, no case file, no --list
    assert incomplete.value.code == EXIT_USAGE
    assert "--list" in capsys.readouterr().err


def test_ver32_an_unclassified_failure_exits_one_and_says_to_ask_for_the_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exit 1 is the only class whose traceback is worth keeping, so it is offered.

    Exit codes 5 and 130 are not reachable in Tier 1 — forcing Newton to diverge
    or a token to cancel needs a solve — and are discharged above by classifying
    an instance of each class, which is the same route this code takes.
    """

    def explode(*_args: object, **_kwargs: object) -> None:
        raise ZeroDivisionError("a bug, not a refusal")

    monkeypatch.setattr("nanopnp.io.run.run_case", explode)
    assert main(["run", str(tmp_path / "absent.yaml")]) == EXIT_UNEXPECTED
    captured = capsys.readouterr()
    assert "a bug, not a refusal" in captured.err
    assert "--traceback" in captured.err
    assert "Traceback" not in captured.err

    with pytest.raises(ZeroDivisionError):
        main(["run", str(tmp_path / "absent.yaml"), "--traceback"])


def test_ver32_stdout_carries_the_result_and_stderr_carries_the_log(
    case_file: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A caller parsing stdout must not receive log lines (section 3.1, IF-02)."""
    log = tmp_path / "run.log"
    code = main(
        [
            "run",
            str(case_file),
            "--upto",
            "case",
            "--store",
            str(tmp_path / "store"),
            "--run-dir",
            str(tmp_path / "out"),
            "--json",
            "-vv",
            "--log-file",
            str(log),
        ]
    )
    assert code == EXIT_OK
    captured = capsys.readouterr()
    assert json.loads(captured.out)["schema"] == RUN_SCHEMA  # parses whole: nothing else on stdout
    assert "nanopnp.io.run" in captured.err
    assert "nanopnp.io.run" in log.read_text(encoding="utf-8")


def test_ver32_inspect_reads_a_run_directory_back(
    case_file: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """``inspect`` reports what is on disk, from the directory or from the file."""
    where = tmp_path / "out"
    assert (
        main(
            [
                "run",
                str(case_file),
                "--upto",
                "case",
                "--store",
                str(tmp_path / "store"),
                "--run-dir",
                str(where),
            ]
        )
        == EXIT_OK
    )
    capsys.readouterr()

    assert main(["inspect", str(where), "--json"]) == EXIT_OK
    printed = capsys.readouterr().out
    from_directory = json.loads(printed)
    assert from_directory["schema"] == MANIFEST_SCHEMA
    # Both files are written through ``canonical``, which encodes a float as
    # ``{"__f__": <hex>}`` so that the digest is exact. Printing that back is
    # printing the encoding rather than the run: the one command whose job is to
    # read a run back has to undo it (section 5.3.3).
    assert "__f__" not in printed, "inspect printed canonical float wrappers, not numbers"
    rtol = from_directory["solver"]["nonlinear"]["rtol"]
    assert isinstance(rtol, float) and rtol == pytest.approx(1e-6)

    assert main(["inspect", str(where / RUN_RECORD_FILENAME), "--json"]) == EXIT_OK
    assert json.loads(capsys.readouterr().out)["schema"] == RUN_SCHEMA

    assert main(["inspect", str(tmp_path)]) == EXIT_CASE
    assert "run directory" in capsys.readouterr().err


# -- the Tier-3 harness surface (VAL-01, VAL-03) -------------------------------


def test_val01_validate_export_grid_prints_the_hash_a_golden_declares(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``validate export-grid`` emits the probe hash and the %Grid axes, in metres.

    The author pastes those axes into COMSOL, so the command exists to stop them
    being retyped: a hand-entered extent is a silently moved sample point that
    the ``probe_hash`` cannot catch, because the document did not change.
    """
    from nanopnp.validation.probe import load_probe

    probe = Path("docs/validation/probes/clya-reference.probe.yaml")
    assert main(["validate", "export-grid", str(probe), "--json"]) == 0
    record = json.loads(capsys.readouterr().out)
    assert record["probe_hash"] == load_probe(probe).hash
    assert record["points"] == sum(patch["n_r"] * patch["n_z"] for patch in record["patches"])


def test_val03_validate_case_hash_matches_every_rung_of_the_ladder(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``validate case-hash`` prints the identity a golden declares for a frozen case.

    It is the number the export contract tells the author to paste into
    ``manifest.yaml``, so the command and the library must not be able to
    disagree about it.
    """
    from nanopnp.io.case import load_case, resolve
    from nanopnp.validation.comsol import case_identity

    case = Path("docs/validation/cases/clya-0.5M-plus50mV.case.yaml")
    assert main(["validate", "case-hash", str(case), "--json"]) == 0
    record = json.loads(capsys.readouterr().out)
    assert record["case_hash"] == case_identity(resolve(load_case(case)))


def test_val03_validate_ingest_golden_refuses_a_directory_without_a_manifest(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An export without its declaration is a pile of numbers, and exits 4.

    Exit 4 and not 1: the Tier-3 refusals are gates in the QR-12 sense — rather
    than report a comparison it cannot defend, the harness stops and says what is
    missing.
    """
    probe = Path("docs/validation/probes/clya-reference.probe.yaml")
    code = main(["validate", "ingest-golden", str(tmp_path), "--probe", str(probe)])
    assert code == EXIT_GATE
    assert "manifest.yaml" in capsys.readouterr().err


def test_val01_validate_help_does_not_choke_on_the_grid_header(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """``--help`` renders, although the help text contains ``%Grid``.

    argparse percent-formats help strings, so a literal ``%G`` makes ``--help``
    raise ``TypeError`` rather than print — which no test of the handlers would
    ever notice, and which is the first thing a new user hits.
    """
    with pytest.raises(SystemExit) as raised:
        main(["validate", "--help"])
    assert raised.value.code == 0
    printed = capsys.readouterr().out
    assert "%Grid" in printed
    for action in (
        "export-grid",
        "case-hash",
        "ingest-golden",
        "export-golden",
        "compare",
        "report",
    ):
        assert action in printed


# -- the mesh generators (section 3.1 generators NOTE) -------------------------


def test_ver32_mesh_cylinder_writes_a_mesh_its_printed_groups_ingest(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The file ingests through the VER-27 gate with the mapping printed, unchanged.

    And the hash printed is the one the run's FR-25 manifest records for it: the
    generator gates and hashes the file by the route a run reads it, so the two
    cannot disagree without this failing.
    """
    out = tmp_path / "pore.msh"
    assert main(["mesh", "cylinder", "--out", str(out), "--json"]) == EXIT_OK
    printed = json.loads(capsys.readouterr().out)
    assert out.is_file()
    assert printed["path"] == str(out)
    assert printed["groups"] == {"default": "interface"}
    assert printed["elements"] > 0
    assert printed["min_sicn"] > 0.3 and printed["min_gamma"] > 0.3
    assert not list(tmp_path.glob(".*partial*")), "the staging file was left behind"

    groups = ", ".join(f"{key}: {value}" for key, value in printed["groups"].items())
    case = tmp_path / "case.yaml"
    case.write_text(
        CASE.format(mesh_path=out)
        .replace("format: vol", "format: msh41")
        .replace("groups: {default: interface}", f"groups: {{{groups}}}"),
        encoding="utf-8",
    )
    from nanopnp.io.run import run_case
    from nanopnp.io.store import Store

    result = run_case(case, store=Store(tmp_path / "store"), upto="mesh")
    assert result.manifest.geometry_and_mesh["content_hash"] == printed["content_hash"]
    assert result.manifest.geometry_and_mesh["groups"]["default"] == "interface"


def test_ver32_mesh_text_output_carries_a_pasteable_inputs_block(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Without ``--json`` the result ends in the ``inputs.mesh`` block a case needs."""
    out = tmp_path / "pore.msh"
    assert main(["mesh", "cylinder", "--out", str(out)]) == EXIT_OK
    text = capsys.readouterr().out
    assert "    groups: {default: interface}" in text
    assert f"    path: {out}" in text
    assert "    format: msh41" in text


def test_ver32_mesh_failing_the_quality_gate_exits_four_and_leaves_no_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A 0.01 nm membrane meshes to slivers; the VER-10 gate refuses it, exit 4.

    Measured: minimum SICN 0.025 against the 0.3 floor. The refused mesh leaves
    neither the destination nor its staging file behind, so a case cannot pick a
    refused mesh up by name afterwards.
    """
    out = tmp_path / "sliver.msh"
    code = main(["mesh", "cylinder", "--membrane-thickness-nm", "0.01", "--out", str(out)])
    assert code == EXIT_GATE
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "SICN" in captured.err or "gamma" in captured.err
    assert "Traceback" not in captured.err
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "argv",
    [
        ["mesh", "cylinder", "--pore-radius-nm", "0", "--out", "p.msh"],
        ["mesh", "cylinder", "--pore-radius-nm", "12", "--out", "p.msh"],
        ["mesh", "cylinder"],
        ["mesh", "cylinder", "--out", "missing/p.msh"],
        ["mesh", "reference", "--out", "."],
    ],
)
def test_ver32_mesh_refuses_a_bad_geometry_as_a_usage_error(
    argv: list[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A bad geometry or destination is a usage error, exit 2, refused before meshing.

    Non-positive lengths, a pore wider than its reservoir, no ``--out``, or an
    ``--out`` that is a directory or lies in a directory that does not exist.
    """
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as raised:
        main(argv)
    assert raised.value.code == EXIT_USAGE
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("shape", ["cylinder", "reference"])
def test_ver32_mesh_help_imports_no_netgen(shape: str) -> None:
    """``--help`` on either generator answers without importing netgen or NGSolve."""
    code = (
        "import sys, json\n"
        "from nanopnp.cli import main\n"
        "try:\n"
        f"    main(['mesh', {shape!r}, '--help'])\n"
        "except SystemExit:\n"
        "    pass\n"
        "loaded = sorted(m for m in sys.modules if m.startswith(('ngsolve', 'netgen')))\n"
        "sys.stderr.write(json.dumps(loaded))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert json.loads(result.stderr) == []
    assert "--out" in result.stdout

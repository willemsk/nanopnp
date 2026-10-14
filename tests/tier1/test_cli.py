"""VER-32 — the command-line surface, and the exit code as a contract (IF-02)."""

from __future__ import annotations

import argparse
import ast
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

import nanopnp
from nanopnp import __version__
from nanopnp.cli import build_parser, main
from nanopnp.core.errors import (
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
    reference_data_root,
    reference_file,
)
from nanopnp.io.case import CaseValidationError
from nanopnp.io.manifest import MANIFEST_SCHEMA
from nanopnp.numerics.gates import GateViolationError
from nanopnp.pipeline.run import (
    RUN_RECORD_FILENAME,
    RUN_SCHEMA,
)


def test_cli_env_reports_data_location(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--env"]) == 0
    out = capsys.readouterr().out
    assert __version__ in out
    assert "corrections" in out or "data" in out


def test_val15_the_reference_archive_is_absent_rather_than_broken(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
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


_SOURCE_ROOT = Path(nanopnp.__file__).resolve().parent


def _public_exception_classes() -> dict[str, str]:
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
        "AssertionError",
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


# IF-02
def test_ver32_every_public_exception_class_is_classified_or_excluded() -> None:
    classes = _public_exception_classes()
    listed = set(EXIT_CODES) | set(EXCLUDED)

    unclassified = sorted(set(classes) - listed)
    assert not unclassified, (
        f"{unclassified} is a public exception class in src/nanopnp that core/errors.py neither "
        "classifies nor excludes with a reason; it would exit 1 as 'unexpected' by accident"
    )

    ours = {key for key in listed if key.startswith("nanopnp.")}
    stale = sorted(ours - set(classes))
    assert not stale, f"{stale} is listed in core/errors.py but no longer exists in src/nanopnp"

    assert not set(EXIT_CODES) & set(EXCLUDED), "a class is both classified and excluded"
    assert all(reason.strip() for reason in EXCLUDED.values()), "an exclusion carries no reason"


@pytest.mark.parametrize(
    ("key", "code"),
    [
        ("nanopnp.io.case:CaseValidationError", EXIT_CASE),
        ("nanopnp.post.stage:SelectionError", EXIT_CASE),
        ("nanopnp.numerics.gates:GateViolationError", EXIT_GATE),
        ("nanopnp.post.qoi:RouteDisagreementError", EXIT_GATE),
        ("nanopnp.pipeline.run:MissingUpstreamError", EXIT_GATE),
        ("nanopnp.numerics.newton:NewtonDivergenceError", EXIT_CONVERGENCE),
        ("nanopnp.core.stages:Cancelled", EXIT_CANCELLED),
        ("nanopnp.core.stages:MissingExtraError", EXIT_CASE),
        ("nanopnp.structure.read:StructureInputError", EXIT_GATE),
        ("nanopnp.structure.axis:SymmetryGateError", EXIT_GATE),
    ],
)
def test_ver32_each_code_is_produced_by_an_instance_of_its_class(key: str, code: int) -> None:
    module_name, _, class_name = key.partition(":")
    klass = getattr(importlib.import_module(module_name), class_name)
    # Built with ``__new__`` rather than called: these constructors take the gate,
    # the quantity and its location (QR-12), and what is under test is that the
    # key names a class ``classify`` recognises, not how each one is raised.
    assert classify(klass.__new__(klass)) == code
    assert EXIT_CODES[key] == code


def test_ver32_classify_walks_the_mro_and_falls_back_to_unexpected() -> None:

    class StricterError(GateViolationError): ...

    stricter = StricterError("packing fraction", "phi", 1.4, (0.0, 0.0))
    assert classify(stricter) == EXIT_GATE
    assert classify(RuntimeError("something else entirely")) == EXIT_UNEXPECTED
    assert classify(KeyboardInterrupt()) == EXIT_CANCELLED
    # Excluded classes classify as 1 *by decision*, which is what the exclusion
    # says; the enumeration above is what records that it was decided.
    assert classify(CanonicalisationError("a set is not canonicalisable")) == EXIT_UNEXPECTED


def test_ver32_classifying_imports_no_exception_module() -> None:
    listed = sorted({key.partition(":")[0] for key in EXIT_CODES} - {"builtins"})
    code = (
        "import sys, json\n"
        "import nanopnp.cli, nanopnp.core.errors\n"
        f"print(json.dumps([m for m in {listed!r} if m in sys.modules]))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert json.loads(result.stdout) == []


# IF-02
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
    args = build_parser().parse_args(argv)
    assert args.handler.__name__ == handler
    assert args.json is False and args.verbose == 0 and args.traceback is False


# IF-02, FR-25
def test_ver32_no_flag_changes_what_is_solved() -> None:
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


# VER-25
def test_ver32_stage_list_imports_no_stage_module(tmp_path: Path) -> None:
    code = (
        "import sys, json\n"
        "from nanopnp.cli import main\n"
        "main(['stage', '--list'])\n"
        "loaded = sorted(m for m in sys.modules if m.startswith(('ngsolve', 'netgen')) "
        "or m in {'nanopnp.mesh.ingest', 'nanopnp.charge.stage', 'nanopnp.solve.stage', "
        "'nanopnp.post.stage', 'nanopnp.materials.stage', 'nanopnp.io.stage', "
        "'nanopnp.structure.stage', 'nanopnp.structure.read', 'MDAnalysis', 'gemmi', "
        "'nanopnp.density.stage', 'nanopnp.symmetry.stage', 'nanopnp.geometry.contour', "
        "'nanopnp.geometry.region', 'nanopnp.mesh.generate', 'skimage', 'shapely', "
        "'nanopnp.charge.protonation', 'nanopnp.charge.pqr', 'pdb2pqr', 'propka'})\n"
        "sys.stderr.write(json.dumps(loaded))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert json.loads(result.stderr) == []
    numbers = [line.split()[0] for line in result.stdout.splitlines()]
    # Stage 7 is two stages, protonation and then charge, sharing the number so
    # that stages 8 to 12 keep theirs (WP27 D1).
    assert numbers == ["1", "2", "3", "4", "5", "6", "7", "7", "8", "9", "10", "11", "12"]
    names = [line.split()[1] for line in result.stdout.splitlines()]
    assert names[6:8] == ["protonation", "charge"]


def test_ver32_env_reports_the_store_and_the_reference_archive(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv(STORE_ROOT_VARIABLE, str(tmp_path / "elsewhere"))
    monkeypatch.delenv(REFERENCE_DATA_VARIABLE, raising=False)
    assert main(["env", "--json"]) == 0
    found = json.loads(capsys.readouterr().out)
    assert found["store"] == str(tmp_path / "elsewhere")
    assert found[STORE_ROOT_VARIABLE] == str(tmp_path / "elsewhere")
    assert found["reference_data"] is None


# FR-27, IF-02, VER-35
def test_ver32_a_run_exits_zero_and_writes_where_run_dir_says(
    cylindrical_pore_case: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    where = tmp_path / "somewhere" / "else"
    code = main(
        [
            "run",
            str(cylindrical_pore_case),
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


# QR-06
def test_ver32_a_case_the_schema_refuses_exits_three(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text("schema: nanopnp/case/v0.5\nname: bad\nnonsense: 1\n", encoding="utf-8")
    assert main(["run", str(path), "--store", str(tmp_path / "store")]) == EXIT_CASE
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "nonsense" in captured.err
    assert "Traceback" not in captured.err


# QR-06
def test_ver32_upto_naming_a_stage_the_run_does_not_walk_exits_three(
    cylindrical_pore_case: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(
        ["run", str(cylindrical_pore_case), "--upto", "sovle", "--store", str(tmp_path / "store")]
    )
    assert code == EXIT_CASE
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "no stage 'sovle'" in captured.err
    assert "unexpected" not in captured.err
    assert "Traceback" not in captured.err


# QR-12, FR-27
def test_ver32_only_with_an_empty_store_exits_four(
    cylindrical_pore_case: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(
        ["stage", "solve", str(cylindrical_pore_case), "--only", "--store", str(tmp_path / "empty")]
    )
    assert code == EXIT_GATE
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "mesh" in captured.err and "Traceback" not in captured.err


def test_ver32_a_usage_error_exits_two(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as unknown:
        main(["frobnicate"])
    assert unknown.value.code == EXIT_USAGE

    with pytest.raises(SystemExit) as incomplete:
        main(["stage", "mesh"])
    assert incomplete.value.code == EXIT_USAGE
    assert "--list" in capsys.readouterr().err


def test_ver32_an_unclassified_failure_exits_one_and_says_to_ask_for_the_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:

    def explode(*_args: object, **_kwargs: object) -> None:
        raise ZeroDivisionError("a bug, not a refusal")

    monkeypatch.setattr("nanopnp.pipeline.run.run_case", explode)
    assert main(["run", str(tmp_path / "absent.yaml")]) == EXIT_UNEXPECTED
    captured = capsys.readouterr()
    assert "a bug, not a refusal" in captured.err
    assert "--traceback" in captured.err
    assert "Traceback" not in captured.err

    assert main(["run", str(tmp_path / "absent.yaml"), "--traceback"]) == EXIT_UNEXPECTED
    captured = capsys.readouterr()
    assert "Traceback" in captured.err
    assert "ZeroDivisionError: a bug, not a refusal" in captured.err


# IF-02
def test_ver32_stdout_carries_the_result_and_stderr_carries_the_log(
    cylindrical_pore_case: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    log = tmp_path / "run.log"
    code = main(
        [
            "run",
            str(cylindrical_pore_case),
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
    assert json.loads(captured.out)["schema"] == RUN_SCHEMA
    assert "nanopnp.pipeline.run" in captured.err
    assert "nanopnp.pipeline.run" in log.read_text(encoding="utf-8")


def test_ver32_inspect_reads_a_run_directory_back(
    cylindrical_pore_case: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    where = tmp_path / "out"
    assert (
        main(
            [
                "run",
                str(cylindrical_pore_case),
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
    # The files hold ``canonical`` float encodings, which this command undoes (section 5.3.3).
    assert "__f__" not in printed, "inspect printed canonical float wrappers, not numbers"
    rtol = from_directory["solver"]["nonlinear"]["rtol"]
    assert isinstance(rtol, float) and rtol == pytest.approx(1e-6)

    assert main(["inspect", str(where / RUN_RECORD_FILENAME), "--json"]) == EXIT_OK
    assert json.loads(capsys.readouterr().out)["schema"] == RUN_SCHEMA

    assert main(["inspect", str(tmp_path)]) == EXIT_CASE
    assert "run directory" in capsys.readouterr().err


def test_val01_validate_export_grid_prints_the_hash_a_golden_declares(
    capsys: pytest.CaptureFixture[str],
) -> None:
    from nanopnp.validation.probe import load_probe

    probe = Path("docs/validation/probes/clya-reference.probe.yaml")
    assert main(["validate", "export-grid", str(probe), "--json"]) == 0
    record = json.loads(capsys.readouterr().out)
    assert record["probe_hash"] == load_probe(probe).hash
    assert record["points"] == sum(patch["n_r"] * patch["n_z"] for patch in record["patches"])


def test_val03_validate_case_hash_matches_every_rung_of_the_ladder(
    capsys: pytest.CaptureFixture[str],
) -> None:
    from nanopnp.pipeline.case import load_case, resolve
    from nanopnp.validation.comsol import case_identity

    case = Path("docs/validation/cases/clya-0.5M-plus50mV.case.yaml")
    assert main(["validate", "case-hash", str(case), "--json"]) == 0
    record = json.loads(capsys.readouterr().out)
    assert record["case_hash"] == case_identity(resolve(load_case(case)))


# QR-12
def test_val03_validate_ingest_golden_refuses_a_directory_without_a_manifest(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    probe = Path("docs/validation/probes/clya-reference.probe.yaml")
    code = main(["validate", "ingest-golden", str(tmp_path), "--probe", str(probe)])
    assert code == EXIT_GATE
    assert "manifest.yaml" in capsys.readouterr().err


def test_val01_validate_help_does_not_choke_on_the_grid_header(
    capsys: pytest.CaptureFixture[str],
) -> None:
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


# VER-27, FR-25
def test_ver32_mesh_cylinder_writes_a_mesh_its_printed_groups_ingest(
    cylindrical_pore_case: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
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
        cylindrical_pore_case.read_text(encoding="utf-8")
        .replace(str(cylindrical_pore_case.parent / "pore.vol"), str(out))
        .replace("format: vol", "format: msh41")
        .replace("groups: {default: interface}", f"groups: {{{groups}}}"),
        encoding="utf-8",
    )
    from nanopnp.io.store import Store
    from nanopnp.pipeline.run import run_case

    result = run_case(case, store=Store(tmp_path / "store"), upto="mesh")
    assert result.manifest.geometry_and_mesh["content_hash"] == printed["content_hash"]
    assert result.manifest.geometry_and_mesh["groups"]["default"] == "interface"


def test_ver32_mesh_text_output_carries_a_pasteable_inputs_block(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "pore.msh"
    assert main(["mesh", "cylinder", "--out", str(out)]) == EXIT_OK
    text = capsys.readouterr().out
    assert "    groups: {default: interface}" in text
    assert f"    path: {out}" in text
    assert "    format: msh41" in text


# VER-10
def test_ver32_mesh_failing_the_quality_gate_exits_four_and_leaves_no_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
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
    monkeypatch.chdir(tmp_path)
    with pytest.raises(SystemExit) as raised:
        main(argv)
    assert raised.value.code == EXIT_USAGE
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("shape", ["cylinder", "reference"])
def test_ver32_mesh_help_imports_no_netgen(shape: str) -> None:
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


TUBE_CASE = """\
schema: nanopnp/case/v0.5
name: tube
structure:
  source: {{path: {pdb}}}
  symmetry: {{point_group: C12}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 0.1
  parameters: willems2020_nacl
boundary_conditions: {{bias_V: 0.1}}
physics: {{model: epnp-ns, solid_permittivities: {{membrane: 3.2}}}}
"""

PROFILE_CASE = """\
schema: nanopnp/case/v0.5
name: coarse
inputs:
  profile: {{path: {path}}}
geometry: {{reservoir: {{radius_nm: 30.0}}}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 1.0
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics: {{model: pnp-ns, solid_permittivities: {{protein: 20.0, membrane: 3.2}}}}
numerics: {{mesh: {{size_scale: 20.0}}}}
"""


def _stage_json(capsys: pytest.CaptureFixture[str], *argv: str) -> dict[str, object]:
    assert main(["stage", *argv, "--json"]) == EXIT_OK
    found = json.loads(capsys.readouterr().out)
    assert isinstance(found, dict)
    return found


@pytest.fixture(scope="module")
def tube_walk(tube_pdb: Path, tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    root = tmp_path_factory.mktemp("export")
    case = root / "tube.case.yaml"
    case.write_text(TUBE_CASE.format(pdb=tube_pdb), encoding="utf-8")
    store = root / "store"
    assert main(["stage", "contour", str(case), "--store", str(store)]) == EXIT_OK
    return case, store


# IF-05, VER-49
def test_ver32_stage_export_writes_each_interchange_file(
    tube_walk: tuple[Path, Path], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    import MDAnalysis as mda  # noqa: N813 - the alias the library documents
    import numpy as np

    from nanopnp.density.map import DensityMap
    from nanopnp.geometry.profile import load_profile
    from nanopnp.structure.ensemble import AlignedEnsemble

    case, store = tube_walk
    for name in ("structure", "density", "symmetry", "contour"):
        plain = _stage_json(capsys, name, str(case), "--store", str(store))
        suffixes = {
            "structure": (".pdb",),
            "density": (".npz", ".dx", ".ccp4", ".mrc", ".map"),
            "symmetry": (".npz",),
            "contour": (".yaml",),
        }[name]
        for suffix in suffixes:
            out = tmp_path / f"{name}{suffix}"
            found = _stage_json(
                capsys, name, str(case), "--store", str(store), "--export", str(out)
            )
            assert found["hash"] == plain["hash"], "--export moved the artefact key"
            assert all(entry["cached"] for entry in found["stages"])  # type: ignore[union-attr, index]
            payload = {key: Path(value) for key, value in found["payload"].items()}  # type: ignore[union-attr]
            (stored,) = payload.values()
            if name == "structure":
                assert found["export"] == [str(out), str(out.with_suffix(".dcd"))]
                ensemble = AlignedEnsemble.read(stored)
                universe = mda.Universe(str(out), str(out.with_suffix(".dcd")))
                assert universe.trajectory.n_frames == ensemble.frames
                for frame in universe.trajectory:
                    tolerance = 1e-6
                    moved = np.abs(
                        universe.atoms.positions / 10.0 - ensemble.positions_nm[frame.frame]
                    )
                    assert float(moved.max()) <= tolerance
                first = mda.Universe(str(out))
                moved = np.abs(first.atoms.positions / 10.0 - ensemble.positions_nm[0])
                assert float(moved.max()) <= 5e-5 + 1e-6
            elif suffix in {".npz", ".yaml"}:
                assert found["export"] == [str(out)]
                assert out.read_bytes() == stored.read_bytes()
            else:
                exported = DensityMap.read(out)
                assert exported.grid == DensityMap.read(stored).grid
        if name == "contour":
            assert load_profile(tmp_path / "contour.yaml").provenance.source == "pipeline"
    assert not list(tmp_path.glob(".*partial*")), "a staging file was left behind"


# IF-06
def test_ver32_stage_export_copies_the_generated_mesh(
    parallelogram_profile: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from nanopnp.mesh.adapter import read

    case = tmp_path / "coarse.case.yaml"
    case.write_text(PROFILE_CASE.format(path=parallelogram_profile), encoding="utf-8")
    out = tmp_path / "coarse.msh"
    store = str(tmp_path / "store")
    found = _stage_json(capsys, "mesh", str(case), "--store", store, "--export", str(out))
    stored = Path(found["payload"]["mesh"])  # type: ignore[index]
    assert out.read_bytes() == stored.read_bytes()
    assert read(out, format="msh41").content_hash == found["summary"]["content_hash"]  # type: ignore[index]
    assert _stage_json(capsys, "mesh", str(case), "--store", store)["hash"] == found["hash"]


@pytest.mark.parametrize(
    ("name", "destination", "message"),
    [
        ("region", "region.yaml", "has no export"),
        ("case", "case.yaml", "has no export"),
        ("density", "density.vtk", "writes .npz, .dx, .ccp4, .mrc, .map"),
        ("contour", "contour.yml", "writes .yaml"),
        ("structure", "aligned", "no suffix"),
        ("mesh", "missing/mesh.msh", "does not exist"),
        ("protonation", "protonation.pdb", "writes .pqr"),
    ],
)
def test_ver32_stage_export_refuses_before_any_stage_runs(
    name: str,
    destination: str,
    message: str,
    tube_pdb: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    case = tmp_path / "tube.case.yaml"
    case.write_text(TUBE_CASE.format(pdb=tube_pdb), encoding="utf-8")
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    store = tmp_path / "store"
    with pytest.raises(SystemExit) as raised:
        main(["stage", name, str(case), "--store", str(store), "--export", destination])
    assert raised.value.code == EXIT_USAGE
    assert message in capsys.readouterr().err
    assert not store.exists() or not any(store.rglob("*.json"))
    assert list(work.iterdir()) == []


def test_ver32_stage_export_that_fails_leaves_no_file(
    tube_walk: tuple[Path, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from nanopnp.density.map import DensityMap

    def half_written(self: DensityMap, path: Path) -> Path:
        path.write_bytes(b"half a map")
        raise OSError("the disk filled up")

    monkeypatch.setattr(DensityMap, "export", half_written)
    case, store = tube_walk
    out = tmp_path / "density.dx"
    code = main(["stage", "density", str(case), "--store", str(store), "--export", str(out)])
    assert code == EXIT_UNEXPECTED
    assert "the disk filled up" in capsys.readouterr().err
    assert list(tmp_path.iterdir()) == []


# IF-02
def test_ver32_stage_export_replaces_a_structure_pair_whole_or_not_at_all(
    tube_walk: tuple[Path, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    case, store = tube_walk
    pdb, dcd = tmp_path / "aligned.pdb", tmp_path / "aligned.dcd"
    pdb.write_bytes(b"an earlier export's PDB")
    dcd.write_bytes(b"an earlier export's DCD")
    argv = ["stage", "structure", str(case), "--store", str(store), "--export", str(pdb)]

    replace = Path.replace
    refused: list[Path] = []

    def fails_once_onto_the_pdb(self: Path, target: str | Path) -> Path:
        if Path(target) == pdb and self.parent != pdb.parent and not refused:
            refused.append(self)
            raise OSError("the PDB could not be renamed into place")
        return replace(self, target)

    monkeypatch.setattr(Path, "replace", fails_once_onto_the_pdb)
    assert main(argv) == EXIT_UNEXPECTED
    assert "the PDB could not be renamed into place" in capsys.readouterr().err
    assert refused, "the failure was never injected"
    assert pdb.read_bytes() == b"an earlier export's PDB"
    assert dcd.read_bytes() == b"an earlier export's DCD"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["aligned.dcd", "aligned.pdb"]

    monkeypatch.undo()
    assert main(argv) == EXIT_OK
    capsys.readouterr()
    assert pdb.read_bytes() != b"an earlier export's PDB"
    assert dcd.read_bytes() != b"an earlier export's DCD"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["aligned.dcd", "aligned.pdb"]


def test_ver32_stage_export_help_imports_no_stage_module() -> None:
    code = (
        "import sys, json\n"
        "from nanopnp.cli import main\n"
        "try:\n"
        "    main(['stage', '--help'])\n"
        "except SystemExit:\n"
        "    pass\n"
        "loaded = sorted(m for m in sys.modules if (m.startswith(('ngsolve', 'netgen', 'numpy', "
        "'MDAnalysis', 'nanopnp.structure', 'nanopnp.density')) "
        "or (m.startswith('nanopnp.mesh') and "
        "m not in ('nanopnp.mesh', 'nanopnp.mesh.defaults'))))\n"
        "sys.stderr.write(json.dumps(loaded))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert json.loads(result.stderr) == []
    assert "--export" in result.stdout and ".mrc" in result.stdout


def test_rev27_validate_case_accepts_a_runnable_case_and_lists_its_walk(
    cylindrical_pore_case: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(["validate", "case", str(cylindrical_pore_case), "--json"])
    assert code == EXIT_OK
    reported = json.loads(capsys.readouterr().out)
    assert reported["valid"] is True
    assert reported["model"] == "epnp-ns"
    assert reported["stages"][0] == "case"
    assert reported["stages"][-1] == "report"


# IF-02
@pytest.mark.parametrize(
    ("old", "new", "named"),
    [
        ("model: epnp-ns", "model: epnp-nz", "is not registered"),
        ("stabilisation: none", "stabilisation: none\n  elements: {u: P1}", "inf-sup"),
    ],
)
def test_rev27_validate_case_refuses_in_the_words_run_uses(
    cylindrical_pore_case: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    old: str,
    new: str,
    named: str,
) -> None:
    text = cylindrical_pore_case.read_text(encoding="utf-8")
    assert old in text
    bad = tmp_path / "bad.case.yaml"
    bad.write_text(text.replace(old, new), encoding="utf-8")

    assert main(["validate", "case", str(bad)]) == EXIT_CASE
    checked = capsys.readouterr()
    assert checked.out == ""
    assert main(["run", str(bad), "--store", str(tmp_path / "store")]) == EXIT_CASE
    ran = capsys.readouterr()
    assert named in checked.err
    assert checked.err.removeprefix("nanopnp validate: ") == ran.err.removeprefix("nanopnp run: ")


def test_cr1_case_validation_error_with_traceback_preserves_exit_case(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:

    def fail_case(*_args: object, **_kwargs: object) -> None:
        raise CaseValidationError("invalid model configuration")

    monkeypatch.setattr("nanopnp.pipeline.run.run_case", fail_case)
    code = main(["run", str(tmp_path / "case.yaml"), "--traceback"])
    assert code == EXIT_CASE
    captured = capsys.readouterr()
    assert "Traceback" in captured.err
    assert "CaseValidationError: invalid model configuration" in captured.err


def test_cr2_validate_case_checks_referenced_files(
    cylindrical_pore_case: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    text = cylindrical_pore_case.read_text(encoding="utf-8")
    missing_mesh = tmp_path / "nonexistent.msh"
    bad_case = tmp_path / "missing_mesh.case.yaml"
    bad_case.write_text(
        text.replace(str(cylindrical_pore_case.parent / "pore.vol"), str(missing_mesh)),
        encoding="utf-8",
    )

    code = main(["validate", "case", str(bad_case)])
    assert code == EXIT_CASE
    err = capsys.readouterr().err
    assert "inputs.mesh.path" in err
    assert "does not exist" in err

    code = main(["validate", "case", str(bad_case), "--schema-only", "--json"])
    assert code == EXIT_OK
    out = json.loads(capsys.readouterr().out)
    assert out["valid"] is True


def test_cr2_check_referenced_files_all_leaves(tmp_path: Path) -> None:
    from nanopnp.io.case import (
        Ensemble,
        Structure,
        StructureSource,
        SuppliedArtefact,
        SymmetrySpec,
    )
    from nanopnp.pipeline.case import loads_case
    from nanopnp.pipeline.checks import check_referenced_files

    base_yaml = """
schema: nanopnp/case/v0.5
name: minimal
electrolyte:
  species: [{name: Na+, z: +1}, {name: Cl-, z: -1}]
  concentration_M: 0.1
  temperature_K: 298.15
  parameters: willems2020_nacl
  corrections:
    diffusivity: {model: none}
    mobility: {model: none}
    viscosity: {model: none}
    permittivity: {model: none}
    density: {model: none}
boundary_conditions:
  bias_V: 0.0
  ground: cis
physics:
  model: epnp-ns
numerics:
  stabilisation: none
"""
    doc = loads_case(base_yaml)

    assert doc.structure is None
    check_referenced_files(doc)

    for leaf in ("mesh", "pqr", "profile", "charge", "eps_r"):
        missing = tmp_path / f"missing_{leaf}.dat"
        setattr(doc.inputs, leaf, SuppliedArtefact(path=missing))
        with pytest.raises(FileNotFoundError, match=f"inputs\\.{leaf}\\.path"):
            check_referenced_files(doc)

        existing = tmp_path / f"existing_{leaf}.dat"
        existing.touch()
        setattr(doc.inputs, leaf, SuppliedArtefact(path=existing))
        check_referenced_files(doc)

        setattr(doc.inputs, leaf, None)

    doc.inputs.mesh = SuppliedArtefact(artefact="dummyhash")
    check_referenced_files(doc)
    doc.inputs.mesh = None

    missing_source = tmp_path / "missing_source.pdb"
    doc.structure = Structure(
        source=StructureSource(path=missing_source),
        symmetry=SymmetrySpec(point_group="C1"),
    )
    with pytest.raises(FileNotFoundError, match=r"structure\.source\.path"):
        check_referenced_files(doc)

    existing_source = tmp_path / "existing_source.pdb"
    existing_source.touch()
    doc.structure = Structure(
        source=StructureSource(path=existing_source),
        symmetry=SymmetrySpec(point_group="C1"),
    )
    check_referenced_files(doc)

    missing_traj = tmp_path / "missing_traj.xtc"
    doc.structure = Structure(
        source=StructureSource(path=existing_source),
        ensemble=Ensemble(trajectory=missing_traj),
        symmetry=SymmetrySpec(point_group="C1"),
    )
    with pytest.raises(FileNotFoundError, match=r"structure\.ensemble\.trajectory"):
        check_referenced_files(doc)

    existing_traj = tmp_path / "existing_traj.xtc"
    existing_traj.touch()
    doc.structure = Structure(
        source=StructureSource(path=existing_source),
        ensemble=Ensemble(trajectory=existing_traj),
        symmetry=SymmetrySpec(point_group="C1"),
    )
    check_referenced_files(doc)

    doc.structure = Structure.model_construct(
        source=StructureSource.model_construct(path=None),
        ensemble=None,
        symmetry=SymmetrySpec(point_group="C1"),
    )
    check_referenced_files(doc)

    doc.structure = Structure.model_construct(
        source=None,
        ensemble=Ensemble.model_construct(trajectory=None),
        symmetry=SymmetrySpec(point_group="C1"),
    )
    check_referenced_files(doc)


def test_cr3_sweep_run_mutually_exclusive_and_workers_validation(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    plan = tmp_path / "dummy.plan.json"
    plan.write_text("{}", encoding="utf-8")

    with pytest.raises(SystemExit) as exc1:
        main(["sweep", "run", str(plan), "--index", "0", "--wave", "0"])
    assert exc1.value.code == EXIT_USAGE
    err1 = capsys.readouterr().err
    assert "not allowed with argument" in err1

    with pytest.raises(SystemExit) as exc2:
        main(["sweep", "run", str(plan), "--workers", "0"])
    assert exc2.value.code == EXIT_USAGE
    err2 = capsys.readouterr().err
    assert "must be at least 1, found 0" in err2

    with pytest.raises(SystemExit) as exc3:
        main(["sweep", "run", str(plan), "--workers", "notanint"])
    assert exc3.value.code == EXIT_USAGE
    err3 = capsys.readouterr().err
    assert "is not a valid integer" in err3


def test_cr4_global_flags_accepted_before_subcommand(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["-v", "env"]) == EXIT_OK
    capsys.readouterr()
    assert main(["--traceback", "env"]) == EXIT_OK
    capsys.readouterr()
    assert main(["--json", "env"]) == EXIT_OK
    out = json.loads(capsys.readouterr().out)
    assert "version" in out


def test_cr5_mesh_cylinder_invalid_number_clean_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out_msh = str(tmp_path / "test.msh")
    with pytest.raises(SystemExit) as exc1:
        main(["mesh", "cylinder", "--pore-radius-nm", "abc", "--out", out_msh])
    assert exc1.value.code == EXIT_USAGE
    err1 = capsys.readouterr().err
    assert "_positive_nm" not in err1
    assert "'abc' is not a valid number" in err1

    with pytest.raises(SystemExit) as exc2:
        main(["mesh", "cylinder", "--pore-radius-nm", "-1.5", "--out", out_msh])
    assert exc2.value.code == EXIT_USAGE
    err2 = capsys.readouterr().err
    assert "_positive_nm" not in err2
    assert "'-1.5' is not a positive length in nm" in err2


def test_cr6_format_quantity_value() -> None:
    from nanopnp.cli import _format_quantity_value

    assert _format_quantity_value(-0.0) == "0.0"
    assert _format_quantity_value(0.0) == "0.0"
    assert _format_quantity_value(2.400000000000001) == "2.4"
    assert _format_quantity_value({"Na+": 0.0, "Cl-": -0.0}) == "{'Cl-': 0.0, 'Na+': 0.0}"
    assert _format_quantity_value([-2.4, 2.400000000000001]) == "[-2.4, 2.4]"
    assert _format_quantity_value("abc") == "abc"
    assert _format_quantity_value(42) == "42"


# IF-02
def test_cr4_reproduce_without_a_tolerance_takes_the_pipelines_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from nanopnp.pipeline.reproduce import DEFAULT_TOLERANCE

    seen: list[float] = []

    def handler(args: argparse.Namespace) -> int:
        seen.append(args.tolerance)
        return EXIT_OK

    monkeypatch.setattr("nanopnp.cli._reproduce", handler)
    assert main(["reproduce", "run-dir"]) == EXIT_OK
    assert main(["reproduce", "run-dir", "--tolerance", "0.5"]) == EXIT_OK
    assert seen == [DEFAULT_TOLERANCE, 0.5]


def test_cr4_verbosity_given_before_and_after_the_subcommand_adds_up(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    levels: list[int] = []
    monkeypatch.setattr(
        "nanopnp.cli._configure_logging", lambda verbose, log_file: levels.append(verbose)
    )
    for argv in (["env"], ["-v", "env"], ["env", "-v"], ["-vv", "env", "-v"]):
        assert main(argv) == EXIT_OK
    assert levels == [0, 1, 1, 3]


def test_cr7_run_threads_flag_sets_environment(
    cylindrical_pore_case: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured_env: dict[str, str | None] = {}
    # ``main`` writes these into ``os.environ``; ``monkeypatch`` restores them at teardown.
    for variable in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        monkeypatch.setenv(variable, "1")

    def capture_run(*_args: object, **_kwargs: object) -> object:
        captured_env["OMP_NUM_THREADS"] = os.environ.get("OMP_NUM_THREADS")
        captured_env["OPENBLAS_NUM_THREADS"] = os.environ.get("OPENBLAS_NUM_THREADS")
        captured_env["MKL_NUM_THREADS"] = os.environ.get("MKL_NUM_THREADS")
        raise CaseValidationError("abort after checking env")

    monkeypatch.setattr("nanopnp.pipeline.run.run_case", capture_run)
    code = main(
        ["run", str(cylindrical_pore_case), "--threads", "4", "--store", str(tmp_path / "store")]
    )
    assert code == EXIT_CASE
    assert captured_env["OMP_NUM_THREADS"] == "4"
    assert captured_env["OPENBLAS_NUM_THREADS"] == "4"
    assert captured_env["MKL_NUM_THREADS"] == "4"

    with pytest.raises(SystemExit) as exc:
        main(["run", str(cylindrical_pore_case), "--threads", "0"])
    assert exc.value.code == EXIT_USAGE
    assert "--threads: must be at least 1, found 0" in capsys.readouterr().err


def test_cr8_cr9_env_store_resolution_and_flag_json(capsys: pytest.CaptureFixture[str]) -> None:
    from nanopnp.cli import _environment

    env = _environment()
    assert Path(str(env["store"])).is_absolute()

    assert main([]) == EXIT_OK
    help_out = capsys.readouterr().out
    assert "nanopnp" in help_out

    assert main(["--env", "--json"]) == EXIT_OK
    data = json.loads(capsys.readouterr().out)
    assert Path(data["store"]).is_absolute()
    assert data["store"] == env["store"]

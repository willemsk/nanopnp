"""VER-32 — the command-line surface, and the exit code as a contract (IF-02)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import pytest

from nanopnp.cli import build_parser, main
from nanopnp.core.errors import (
    EXIT_CODES,
    EXIT_GATE,
    EXIT_OK,
)
from nanopnp.pipeline.run import (
    RUN_RECORD_FILENAME,
)


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
    # that stages 8 to 12 keep theirs.
    assert numbers == ["1", "2", "3", "4", "5", "6", "7", "7", "8", "9", "10", "11", "12"]
    names = [line.split()[1] for line in result.stdout.splitlines()]
    assert names[6:8] == ["protonation", "charge"]


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


def test_fr44_plot_refuses_a_suffix_or_a_figureless_stage_before_any_stage_runs(
    tmp_path: Path,
) -> None:
    case = tmp_path / "pore.case.yaml"
    case.write_text("schema: nanopnp/case/v0.5\nname: never-read\n", encoding="utf-8")
    store = tmp_path / "store"
    for given in (
        ["mesh", "--out", str(tmp_path / "figure.txt")],
        ["report", "--out", str(tmp_path / "figure.png")],
        ["no-such-stage", "--out", str(tmp_path / "figure.png")],
        ["--out", str(tmp_path / "figure.png")],
    ):
        with pytest.raises(SystemExit) as raised:
            main(["plot", str(case), *given, "--store", str(store)])
        assert raised.value.code == 2, given
    assert not store.exists()
    assert sorted(path.name for path in tmp_path.iterdir()) == [case.name]


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

"""A project is a folder: a case imported into it computes what it did, and it exports whole."""

from __future__ import annotations

import filecmp
import json
from pathlib import Path

import yaml
from test_models import split_case

from nanopnp.api.case import Case
from nanopnp.api.project import Project
from nanopnp.io.artefact import CaseArtefact
from nanopnp.io.project import PROJECT_FILENAME
from nanopnp.pipeline.run import read_run
from nanopnp.validation.charged_tube import write_charged_tube

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"
QUICKSTART = EXAMPLES / "01-quickstart" / "quickstart.case.yaml"


def _keys(project: Project, case: Case, upto: str) -> dict[str, tuple[str, bool]]:
    result = project.session().run(case, upto=upto)
    return {record.name: (record.hash, record.cached) for record in result.stages}


def _same_keys_from_the_store(project: Project, original: Case, study: str, upto: str) -> None:
    before = _keys(project, original, upto)
    after = _keys(project, project.study(study), upto)
    assert before.keys() == after.keys()
    for name, (digest, _) in before.items():
        if name == "case":
            continue
        assert after[name] == (digest, True), name


def test_fr32_a_case_imported_into_a_project_keys_as_it_did(tmp_path: Path) -> None:
    project = Project.create(tmp_path / "project")
    tube = Case.load(write_charged_tube(tmp_path / "tube"))
    study = project.import_case(tube)
    assert study == "charged-tube"
    assert project.items("study") == ("charged-tube",)
    assert project.items("molecular") == project.items("continuum") == ("charged-tube",)
    assert project.items("physics") == ("charged-tube",)
    assert sorted(path.name for path in (project.root / "inputs").iterdir()) == [
        "atoms.pqr",
        "profile.yaml",
    ]
    _same_keys_from_the_store(project, tube, study, "charge")

    quick = Case.load(QUICKSTART)
    quick_study = project.import_case(quick)
    _same_keys_from_the_store(project, quick, quick_study, "mesh")

    # Linked inputs are not copied; an item names the original.
    linked = Project.create(tmp_path / "linked")
    linked.import_case(tube, link=True)
    assert list((linked.root / "inputs").iterdir()) == []
    originals = {tmp_path / "tube" / "atoms.pqr", tmp_path / "tube" / "profile.yaml"}
    assert set(linked.linked()) == {path.resolve() for path in originals}
    _keys(linked, tube, "charge")
    embedded = linked.embed(tmp_path / "tube" / "atoms.pqr")
    assert embedded == linked.root / "inputs" / "atoms.pqr"
    assert set(linked.linked()) == {(tmp_path / "tube" / "profile.yaml").resolve()}
    _same_keys_from_the_store(linked, tube, "charged-tube", "charge")


def test_fr32_a_study_naming_model_files_imports_them_and_a_second_import_reuses_them(
    tmp_path: Path,
) -> None:
    (tmp_path / "models").mkdir()
    study_file = split_case(QUICKSTART, tmp_path / "models")
    files = (tmp_path / "models").glob("*.yaml")
    written = {path.stem for path in files if "case" not in path.stem}
    assert written
    project = Project.create(tmp_path / "project")
    first = project.import_case(Case.load(study_file), name="first")
    kinds = ("molecular", "continuum", "physics")
    held = {kind: project.items(kind) for kind in kinds}
    assert {kind for kind in held if held[kind]} == written == {"continuum", "physics"}
    assert all(held[kind] == (f"my-{kind}",) for kind in written)
    project.import_case(Case.load(study_file), name="second")
    assert {kind: project.items(kind) for kind in kinds} == held
    assert project.study(first) == project.study("second").with_(name=first)
    assert project.problems() == ()


def test_fr32_an_exported_project_reads_back(tmp_path: Path) -> None:
    project = Project.create(tmp_path / "project")
    tube = Case.load(write_charged_tube(tmp_path / "tube"))
    project.import_case(tube, link=True)
    project.embed(tmp_path / "tube" / "profile.yaml")
    run = project.session().run(tube, upto="charge")
    assert run.directory.parent == project.root / "runs" / "charged-tube"
    # A walk that stops before the report lists no files; name one so that the copy has to carry it.
    result = project.root / "store" / "report.txt"
    result.write_text("a result\n", encoding="utf-8")
    record = json.loads((run.directory / "run.json").read_text(encoding="utf-8"))
    record["files"] = [str(result)]
    (run.directory / "run.json").write_text(json.dumps(record), encoding="utf-8")

    copy = project.export(tmp_path / "copy")
    assert not (copy / "store").exists()
    reopened = Project.open(copy)
    assert reopened.problems() == ()
    for kind in ("molecular", "continuum", "physics", "study", "comparison"):
        assert reopened.items(kind) == project.items(kind)
    assert (copy / PROJECT_FILENAME).read_bytes() == (project.root / PROJECT_FILENAME).read_bytes()

    [original_run] = project.runs("charged-tube")
    [copied_run] = reopened.runs("charged-tube")
    assert read_run(copied_run).manifest.hash == read_run(original_run).manifest.hash
    assert (copied_run / "results" / "report.txt").read_text(encoding="utf-8") == "a result\n"

    rewritten = {"models/molecular/charged-tube.yaml"}
    for source in sorted(project.root.rglob("*")):
        relative = source.relative_to(project.root)
        if not source.is_file() or relative.parts[0] in {"store", "runs"}:
            continue
        assert (copy / relative).is_file(), relative
        if relative.as_posix() not in rewritten and relative.name != PROJECT_FILENAME:
            assert filecmp.cmp(source, copy / relative, shallow=False), relative
    moved = yaml.safe_load((copy / "models/molecular/charged-tube.yaml").read_text())
    assert moved["inputs"]["pqr"]["path"] == "../../inputs/atoms.pqr"
    pqr = (tmp_path / "tube" / "atoms.pqr").read_bytes()
    assert (copy / "inputs" / "atoms.pqr").read_bytes() == pqr

    whole = project.export(tmp_path / "whole", store=True)
    again = _keys(Project.open(whole), Project.open(whole).study("charged-tube"), "charge")
    assert all(cached for name, (_, cached) in again.items() if name != "case")


CONTINUUM = """\
schema: nanopnp/continuum-model/v0.6
name: tube
geometry:
  pore: {shape: cylinder, radius_nm: 2}
  membrane: {thickness_nm: 2.8}
  reservoir: {radius_nm: 250.0}
numerics: {mesh: {size_scale: 2}}
"""

PHYSICS = """\
schema: nanopnp/physics-model/v0.6
name: tube
electrolyte:
  species: [{name: Na+, z: 1}, {name: Cl-, z: -1}]
  concentration_M: 0.1
  parameters: willems2020_nacl
  corrections:
    diffusivity: {model: willems2020_nacl}
    mobility: {model: willems2020_nacl}
    viscosity: {model: willems2020_nacl}
    permittivity: {model: willems2020_nacl}
    density: {model: willems2020_nacl}
    steric: {model: borukhov}
boundary_conditions: {bias_V: 0.05, ground: cis}
physics: {model: epnp-ns, flow: false, inertia: true}
"""

STUDY = """\
schema: nanopnp/case/v0.6
name: tube-study
models: {continuum: ../models/continuum/tube.yaml, physics: ../models/physics/tube.yaml}
boundary_conditions: {bias_V: 0.3}
"""


def test_fr34_the_changed_list_holds_every_value_away_from_its_default_and_every_override(
    tmp_path: Path,
) -> None:
    project = Project.create(tmp_path / "project")
    (project.root / "models/continuum/tube.yaml").write_text(CONTINUUM, encoding="utf-8")
    (project.root / "models/physics/tube.yaml").write_text(PHYSICS, encoding="utf-8")
    (project.root / "studies/tube-study.yaml").write_text(STUDY, encoding="utf-8")
    project = Project.open(project.root)
    assert project.problems() == ()

    found = {change.path: change for change in project.changes("study", "tube-study")}
    assert set(found) == {
        "physics.flow",
        "numerics.mesh.size_scale",
        "boundary_conditions.bias_V",
    }
    flow = found["physics.flow"]
    assert (flow.kind, flow.owner, flow.value, flow.default) == ("value", "physics", False, True)
    scale = found["numerics.mesh.size_scale"]
    assert (scale.kind, scale.value, scale.default) == ("value", 2.0, 1.0)
    bias = found["boundary_conditions.bias_V"]
    assert (bias.kind, bias.value, bias.model, bias.default) == ("override", 0.3, 0.05, None)
    assert {change.path for change in project.changes("continuum", "tube")} == {
        "numerics.mesh.size_scale",
    }
    assert {change.path for change in project.changes("physics", "tube")} == {"physics.flow"}

    remaining = set(found)
    for path in sorted(found):
        project.reset("study", "tube-study", path)
        remaining.discard(path)
        assert {c.path for c in project.changes("study", "tube-study")} == remaining
    assert project.study("tube-study")["bias_V"] == 0.05


def test_fr32_a_case_with_an_expression_at_a_models_value_imports_as_the_same_case(
    tmp_path: Path,
) -> None:
    raw = yaml.safe_load(QUICKSTART.read_text(encoding="utf-8"))
    raw["variables"] = {"v": {"value": 50, "unit": "mV"}, "zz": {"value": 1}}
    raw["boundary_conditions"]["bias_V"] = "v"
    raw["electrolyte"]["species"][0]["z"] = "zz"
    path = tmp_path / "case.yaml"
    path.write_text(yaml.safe_dump(raw, sort_keys=False), encoding="utf-8")
    case = Case.load(path)
    project = Project.create(tmp_path / "project")
    study = project.import_case(case)
    physics = yaml.safe_load(project.path("physics", study).read_text(encoding="utf-8"))
    assert physics["boundary_conditions"]["bias_V"] == 0.05, "the model holds the number"
    assert physics["electrolyte"]["species"][0]["z"] == 1
    written = yaml.safe_load(project.path("study", study).read_text(encoding="utf-8"))
    assert written["boundary_conditions"]["bias_V"] == "v", "the study keeps the expression"
    assert written["electrolyte"]["species"][0]["z"] == "zz"
    imported = project.study(study)
    assert CaseArtefact(imported).hash == CaseArtefact(case).hash
    edited = imported.with_({"variables.v": {"value": 80, "unit": "mV"}})
    assert edited.boundary_conditions.bias_V == 0.08, "a variable edit still reaches the field"
    assert project.problems() == ()

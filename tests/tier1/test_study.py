"""A study made and edited through the project resolves to the case the Study suite shows."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from pydantic_core import to_jsonable_python

from nanopnp.api.case import Case
from nanopnp.api.project import Project, ProjectError
from nanopnp.api.session import Session
from nanopnp.io.case import CaseValidationError
from nanopnp.io.case_paths import value_at
from nanopnp.pipeline.case import resolve
from nanopnp.pipeline.run import keyed_walk
from nanopnp.sweep.document import loads_sweep
from nanopnp.sweep.forecast import forecast
from nanopnp.sweep.plan import build_plan

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"
QUICKSTART = EXAMPLES / "01-quickstart" / "quickstart.case.yaml"


def _project(tmp_path: Path) -> Project:
    project = Project.create(tmp_path / "project")
    project.import_case(Case.load(QUICKSTART))
    project.derive_model("physics", "quickstart", "salty", {"electrolyte.concentration_M": 0.2})
    return project


def test_fr39_a_study_edited_in_the_suite_resolves_to_the_case_it_shows(tmp_path: Path) -> None:
    # A form that shows one value while the run takes another misleads every study.
    project = _project(tmp_path)
    location = project.new_study("edited", "quickstart", "quickstart", "quickstart")
    assert project.items("study") == ("quickstart", "edited")
    with pytest.raises(ProjectError, match="holds no physics model 'absent'"):
        project.new_study("other", "quickstart", "quickstart", "absent")

    project.set_study_value("edited", "numerics.continuation", "none")
    project.set_study_value("edited", "boundary_conditions.bias_V", 0.08)
    project.set_study_value("edited", "models.physics", "salty")
    project.set_variable("edited", "r", value=25, unit="angstrom")
    project.set_study_value("edited", "geometry.pore.radius_nm", "r")

    case = project.study("edited")
    resolved = resolve(case, base=case.source.base)
    shown = project.study_values("edited")
    assert [value.name for value in shown] == [
        "pH",
        "size_scale",
        "concentration",
        "bias",
        "numerics.continuation",
        "geometry.pore.radius_nm",
    ]
    for value in shown:
        if value.path == "charge.ph":
            continue  # the uncharged tube has no charge block; its model's default is shown
        assert value.value == to_jsonable_python(value_at(resolved.document, value.path)), value
    by_path = {value.path: value for value in shown}
    assert by_path["electrolyte.concentration_M"].model == 0.2
    assert (
        by_path["boundary_conditions.bias_V"].model,
        by_path["boundary_conditions.bias_V"].study,
    ) == (0.05, 0.08)
    assert by_path["geometry.pore.radius_nm"].kind == "continuum"
    assert by_path["geometry.pore.radius_nm"].study == 2.5
    assert by_path["numerics.continuation"].kind == "study"

    overrides = {"boundary_conditions.bias_V": (0.05, 0.08), "geometry.pore.radius_nm": (2.0, 2.5)}
    listed = {
        c.path: (c.model, c.value)
        for c in project.changes("study", "edited")
        if c.kind == "override"
    }
    assert listed == overrides
    run = Session(project.root / "store", write=False).run(case, upto="case")
    recorded = run.manifest.inputs["overrides"]
    assert {path: (entry["model"], entry["study"]) for path, entry in recorded.items()} == overrides

    project.reset("study", "edited", "boundary_conditions.bias_V")
    assert "boundary_conditions.bias_V" not in project.study("edited").overrides

    # A refused value, model or variable leaves the file as it was.
    before = location.read_bytes()
    with pytest.raises(CaseValidationError):
        project.set_study_value("edited", "boundary_conditions.ground", "middle")
    with pytest.raises(ProjectError, match="holds no physics model 'absent'"):
        project.set_study_value("edited", "models.physics", "absent")
    with pytest.raises(CaseValidationError):
        project.set_variable("edited", "r", value=2, unit="volt")
    assert location.read_bytes() == before
    assert yaml.safe_load(before)["variables"] == {"r": {"value": 25, "unit": "angstrom"}}


SWEEP = """\
schema: nanopnp/sweep/v0.5
name: over-models
base: ../studies/swept.yaml
axes:
  - {name: v, path: variables.v, values: [0.0, 0.05]}
  - name: salt
    path: models.physics
    values: [../models/physics/quickstart.yaml, ../models/physics/salty.yaml]
"""


def test_fr39_a_studys_sweep_plans_over_a_variable_and_a_model(tmp_path: Path) -> None:
    # A sweep that drops the study's values or its model at a member runs another case than shown.
    project = _project(tmp_path)
    project.new_study("swept", "quickstart", "quickstart", "quickstart")
    project.set_variable("swept", "v", value=0.02, unit="V")
    project.set_study_value("swept", "boundary_conditions.bias_V", "v")
    project.set_study_value("swept", "numerics.mesh.maxh_nm", 3.5)

    source = project.root / "sweeps" / "over-models.sweep.yaml"
    source.parent.mkdir()
    source.write_text(SWEEP, encoding="utf-8")
    plan = build_plan(loads_sweep(SWEEP), source=source, check_meshes=False)
    members = plan.resolved_members
    assert len(members) == 4
    for index, member in enumerate(members):
        bias, salt = plan.points[index].assignments.values()
        assert member.bias_V == bias
        assert member.concentration_M == (0.1 if salt.endswith("quickstart.yaml") else 0.2)
        assert value_at(member.document, "numerics.mesh.maxh_nm") == 3.5

    store = Session(project.root / "store", write=False).store
    predicted = forecast(plan, store=store)
    planned: set[str] = set()
    for index, member in enumerate(members):
        walked = keyed_walk(member, store=store, planned=planned)
        assert predicted.points[index] == tuple(n for n, i in walked.items() if i.built)
    # The quick-start pins its wall's size, so neither the bias nor the salt moves its mesh.
    assert (predicted.builds["mesh"], predicted.builds["solve"]) == (1, 4)

"""A physics model edited in the Physics suite: the case it shows, a change of model, its list."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

from nanopnp.api.case import Case
from nanopnp.api.project import Project
from nanopnp.io.case import FieldValue
from nanopnp.io.case_paths import schema_default
from nanopnp.io.models import exposed_values, leaves, owner_of
from nanopnp.io.store import Store
from nanopnp.physics import models
from nanopnp.pipeline.case import resolve
from nanopnp.pipeline.run import keyed_walk
from nanopnp.validation.charged_tube import write_charged_tube

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"
QUICKSTART = EXAMPLES / "01-quickstart" / "quickstart.case.yaml"

EDITS: tuple[tuple[str, FieldValue], ...] = (
    ("physics.inertia", False),
    ("numerics.elements.phi", "P1"),
    ("numerics.elements.c", "P1"),
    ("electrolyte.concentration_M", 0.5),
    ("electrolyte.corrections.viscosity.model", "none"),
    ("electrolyte.corrections.steric.a_ion_nm", 0.45),
    ("numerics.wall_distance.max_distance_nm", 8.0),
    ("boundary_conditions.bias_V", 0.1),
    ("boundary_conditions.ground", "trans"),
    ("boundary_conditions.wall_charge_C_m2", -0.01),
    ("physics.solid_permittivities", {"membrane": 4.0}),
)
"""One value of each kind of field of the four tools, each valid alone on the quick-start model."""


@pytest.fixture
def paired(tmp_path: Path) -> Project:
    project = Project.create(tmp_path / "project")
    project.import_case(Case.load(QUICKSTART))
    project.import_case(Case.load(write_charged_tube(tmp_path / "tube")))
    return project


def _body(project: Project, name: str) -> dict[str, Any]:
    loaded = yaml.safe_load(project.path("physics", name).read_text(encoding="utf-8"))
    assert isinstance(loaded, dict)
    return loaded


def _dumped(case: Case, path: str) -> object:
    node: object = case.model_dump(mode="json", by_alias=True)
    for part in path.split("."):
        assert isinstance(node, dict), path
        node = node[part]
    return node


def _identities(case: Case, store: Store) -> dict[str, str]:
    walked = keyed_walk(resolve(case), store=store, planned=set())
    return {name: identity.hash for name, identity in walked.items()}


def test_fr39_a_physics_model_edited_in_the_suite_resolves_to_the_case_it_shows(
    paired: Project, tmp_path: Path
) -> None:
    store = Store(tmp_path / "store")
    for study in ("quickstart", "charged-tube"):
        own = paired.physics_case(study, study)
        assert own.dumps() == paired.study(study).dumps(), study
        assert _identities(own, store) == _identities(paired.study(study), store), study

    location = paired.path("study", "quickstart")
    written = yaml.safe_load(location.read_text(encoding="utf-8"))
    written["boundary_conditions"] = {"bias_V": 0.2}
    location.write_text(yaml.safe_dump(written, sort_keys=False), encoding="utf-8")
    assert paired.study("quickstart")["boundary_conditions.bias_V"] == 0.2
    other = paired.physics_case("charged-tube", "quickstart")
    for path, value in leaves(_body(paired, "charged-tube")):
        if owner_of(path) == "physics":
            assert _dumped(other, path) == value, path
    assert other["boundary_conditions.bias_V"] == 0.05
    assert other.models_record is not None
    assert other.models_record.overrides == {}

    for path, value in EDITS:
        paired.set_value("physics", "quickstart", path, value)
    edited = paired.physics_case("quickstart", "quickstart")
    for path, value in EDITS:
        assert _dumped(edited, path) == value, path
    paired.choose_physics("quickstart", "pnp")
    shown = paired.physics_case("quickstart", "quickstart")
    assert shown["physics.model"] == "pnp"
    assert shown["physics.flow"] is False


def test_ver56_choosing_a_model_leaves_no_value_its_declaration_refuses(paired: Project) -> None:
    for start in ("quickstart", "charged-tube"):
        before = _body(paired, start)
        for model in models.registered_models():
            earlier = paired.choose_physics(start, model)
            declared = models.declaration(model)
            own = dict(leaves(_body(paired, start)))
            assert own["physics.model"] == model
            for switch in models.SWITCHES:
                path = f"physics.{switch}"
                value = own[path] if path in own else schema_default(path)[1]
                assert value in declared.switches[switch], (start, model, switch)
            for path, value in own.items():
                if path in declared.unread:
                    has_default, default = schema_default(path)
                    assert not has_default or value == default, (start, model, path)
            if not declared.solids:
                assert "physics.solid_permittivities" not in own, (start, model)
            if "surface_charge" not in declared.coefficients:
                assert "boundary_conditions.wall_charge_C_m2" not in own, (start, model)
            if model in ("epnp-ns", "pnp-ns"):
                resolve(paired.physics_case(start, start))
            for path, value in earlier.items():
                paired.set_value("physics", start, path, value)
            assert _body(paired, start) == before, (start, model)


def test_fr39_an_exposed_value_named_and_ranged_reads_back(paired: Project) -> None:
    paired.set_exposed(
        "physics",
        "quickstart",
        "boundary_conditions.bias_V",
        True,
        label="voltage",
        span=(-0.2, 0.2),
    )
    body = _body(paired, "quickstart")
    listed = exposed_values("physics", body, "quickstart")
    assert [value.path for value in listed] == [
        "electrolyte.concentration_M",
        "boundary_conditions.bias_V",
    ]
    voltage = listed[1]
    assert (voltage.name, voltage.unit, voltage.low, voltage.high) == ("voltage", "volt", -0.2, 0.2)
    assert voltage.default == 0.05

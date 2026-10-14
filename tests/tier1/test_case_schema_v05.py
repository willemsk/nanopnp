"""VER-47, G6 — the case schema ``nanopnp/case/v0.5``."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest
import yaml
from packaging.specifiers import SpecifierSet

ROOT = Path(__file__).resolve().parents[2]

PNP = """
schema: {schema}
name: quickstart
inputs: {{mesh: {{path: absent.msh, format: msh41}}}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 0.1
  parameters: willems2020_nacl
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics: {{model: pnp, flow: false{switches}, solid_permittivities: {{membrane: 3.2}}}}
numerics: {{continuation: none}}
outputs: [current]
"""

WRITTEN = ", variable_density: false, inertia: false"


def test_the_schema_is_v05() -> None:
    from nanopnp.io.artefact import CASE_SCHEMA
    from nanopnp.io.defaults import VALIDATED_DEFAULT_CASE

    assert CASE_SCHEMA == "nanopnp/case/v0.5"
    assert VALIDATED_DEFAULT_CASE.schema_id == "nanopnp/case/v0.5"


def test_a_v05_document_loads_cleanly() -> None:
    from nanopnp.pipeline.case import loads_case

    document = loads_case(PNP.format(schema="nanopnp/case/v0.5", switches=WRITTEN))
    assert document.schema_id == "nanopnp/case/v0.5"
    assert document.physics.model == "pnp"
    assert document.physics.variable_density is False
    assert document.physics.inertia is False


@pytest.mark.parametrize("schema", ["nanopnp/case/v2", "nanopnp/case/v1", "nanopnp/case/v0.6"])
def test_any_other_schema_identifier_is_refused(schema: str) -> None:
    from nanopnp.io.case import CaseValidationError
    from nanopnp.pipeline.case import loads_case

    with pytest.raises(CaseValidationError) as raised:
        loads_case(PNP.format(schema=schema, switches=WRITTEN))
    assert str(raised.value) == f"<string>: expected schema 'nanopnp/case/v0.5', found '{schema}'"


def _minor_versions(first: str, last: str) -> list[str]:
    low, high = (int(version.split(".")[1]) for version in (first, last))
    return [f"3.{minor}" for minor in range(low, high + 1)]


def _specified_range() -> list[str]:
    text = (ROOT / "SPECIFICATION.md").read_text(encoding="utf-8")
    found = re.search(r"^\| Python \| (3\.\d+) to (3\.\d+)", text, flags=re.MULTILINE)
    assert found is not None, "section 2.5 no longer has a 'Python | 3.x to 3.y' row"
    return _minor_versions(found.group(1), found.group(2))


def _python_versions(node: object) -> set[str]:
    found: set[str] = set()
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "python-version":
                values = value if isinstance(value, list) else [value]
                found.update(str(item) for item in values if "${{" not in str(item))
            else:
                found |= _python_versions(value)
    elif isinstance(node, list):
        for item in node:
            found |= _python_versions(item)
    return found


def test_ver47_the_declared_python_range_agrees() -> None:
    specified = _specified_range()
    assert specified == ["3.11", "3.12", "3.13", "3.14"]
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    requires = SpecifierSet(project["project"]["requires-python"])
    admitted = [version for version in _minor_versions("3.8", "3.20") if f"{version}.0" in requires]
    assert admitted == specified, f"requires-python {requires} admits {admitted}"

    prefix = "Programming Language :: Python :: "
    classified = [
        entry.removeprefix(prefix)
        for entry in project["project"]["classifiers"]
        if entry.startswith(prefix) and entry.removeprefix(prefix).count(".") == 1
    ]
    assert classified == specified

    target = project["tool"]["ruff"]["target-version"]
    assert target == f"py{specified[0].replace('.', '')}"

    workflow = yaml.safe_load((ROOT / ".github" / "workflows" / "ci.yml").read_text("utf-8"))
    # Before a release, CI's full matrix runs every supported Python (section 7.6).
    tested = _python_versions(workflow["jobs"]["full-matrix"])
    assert sorted(tested) == specified, f"CI tests {sorted(tested)}"


@pytest.mark.parametrize(
    ("path", "bad_val"),
    [
        ("charge.exclusion_offset_nm", -0.1),
        ("charge.exclusion_offset_nm", float("inf")),
        ("charge.exclusion_offset_nm", float("nan")),
        ("charge.dielectric_transition_nm", -0.1),
        ("charge.dielectric_transition_nm", float("inf")),
        ("charge.dielectric_transition_nm", float("nan")),
        ("numerics.mesh.size_scale", -0.1),
        ("numerics.mesh.size_scale", 0.0),
        ("numerics.mesh.size_scale", float("inf")),
        ("numerics.mesh.size_scale", float("nan")),
    ],
)
def test_ver47_value_range_refusals(path: str, bad_val: float) -> None:
    from nanopnp.io.case import CaseValidationError
    from nanopnp.pipeline.case import loads_case

    raw = yaml.safe_load(PNP.format(schema="nanopnp/case/v0.5", switches=WRITTEN))
    parts = path.split(".")
    cur = raw
    for part in parts[:-1]:
        cur = cur.setdefault(part, {})
    cur[parts[-1]] = bad_val
    with pytest.raises(CaseValidationError):
        loads_case(yaml.safe_dump(raw))


def test_ver47_deviations_offset_and_transition() -> None:
    from nanopnp.io.defaults import deviations
    from nanopnp.pipeline.case import load_case, loads_case

    quickstart = ROOT / "examples" / "01-quickstart" / "quickstart.case.yaml"
    assert deviations(load_case(quickstart)) == ()

    raw = yaml.safe_load(quickstart.read_text(encoding="utf-8"))
    raw["charge"] = {"exclusion_offset_nm": 0.3}
    listed = {dev.path: dev for dev in deviations(loads_case(yaml.safe_dump(raw)))}
    assert set(listed) == {"charge.exclusion_offset_nm"}
    assert listed["charge.exclusion_offset_nm"].validated == 0.0
    assert listed["charge.exclusion_offset_nm"].value == 0.3

    raw["charge"] = {"dielectric_transition_nm": 0.2}
    listed = {dev.path: dev for dev in deviations(loads_case(yaml.safe_dump(raw)))}
    assert set(listed) == {"charge.dielectric_transition_nm"}

    raw["charge"] = {}
    assert deviations(loads_case(yaml.safe_dump(raw))) == ()


def test_ver47_pqr_input_sets_protonates() -> None:
    from nanopnp.pipeline.case import loads_case, resolve

    raw = yaml.safe_load(PNP.format(schema="nanopnp/case/v0.5", switches=WRITTEN))
    raw["inputs"]["pqr"] = {"path": "supplied.pqr", "format": "pqr"}
    resolved = resolve(loads_case(yaml.safe_dump(raw)))
    assert resolved.pqr is not None
    assert resolved.protonates


@pytest.mark.parametrize(
    ("upstream", "downstream"), [("profile", "mesh"), ("pqr", "charge")], ids=lambda value: value
)
def test_ver47_an_input_and_one_downstream_of_it_are_not_both_supplied(
    upstream: str, downstream: str
) -> None:
    from nanopnp.io.case import CaseValidationError
    from nanopnp.pipeline.case import loads_case

    raw = yaml.safe_load(PNP.format(schema="nanopnp/case/v0.5", switches=WRITTEN))
    raw["inputs"][upstream] = {"path": f"supplied.{upstream}"}
    raw["inputs"][downstream] = {"path": f"supplied.{downstream}"}
    with pytest.raises(CaseValidationError) as raised:
        loads_case(yaml.safe_dump(raw))
    message = str(raised.value)
    assert f"inputs.{upstream}" in message
    assert f"inputs.{downstream}" in message
    assert "both supplied" in message


@pytest.mark.parametrize(
    ("key", "value"),
    [("size_scale", 0.5), ("wall_h_nm", 0.3), ("backend", "gmsh"), ("boundary_layer", True)],
)
def test_ver47_a_mesher_key_beside_a_supplied_mesh_is_refused(key: str, value: object) -> None:
    from nanopnp.io.case import CaseValidationError
    from nanopnp.pipeline.case import loads_case

    raw = yaml.safe_load(PNP.format(schema="nanopnp/case/v0.5", switches=WRITTEN))
    raw["numerics"]["mesh"] = {key: value}
    with pytest.raises(CaseValidationError) as raised:
        loads_case(yaml.safe_dump(raw))
    message = str(raised.value)
    assert f"numerics.mesh.{key}" in message
    assert "inputs.mesh" in message

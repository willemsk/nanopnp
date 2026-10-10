"""VER-47, G6 — the case schema ``nanopnp/case/v0.5``.

Every case document must declare schema ``nanopnp/case/v0.5`` exactly (IF-03).
Any other schema identifier is refused immediately.
"""

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
    """The identifier is ``nanopnp/case/v0.5`` and default case declares it."""
    from nanopnp.io.artefact import CASE_SCHEMA
    from nanopnp.io.defaults import VALIDATED_DEFAULT_CASE

    assert CASE_SCHEMA == "nanopnp/case/v0.5"
    assert VALIDATED_DEFAULT_CASE.schema_id == "nanopnp/case/v0.5"


def test_a_v05_document_loads_cleanly() -> None:
    """A valid v0.5 document loads cleanly."""
    from nanopnp.pipeline.case import loads_case

    document = loads_case(PNP.format(schema="nanopnp/case/v0.5", switches=WRITTEN))
    assert document.schema_id == "nanopnp/case/v0.5"
    assert document.physics.model == "pnp"
    assert document.physics.variable_density is False
    assert document.physics.inertia is False


@pytest.mark.parametrize("schema", ["nanopnp/case/v2", "nanopnp/case/v1", "nanopnp/case/v0.6"])
def test_any_other_schema_identifier_is_refused(schema: str) -> None:
    """Any other schema identifier is refused with expected schema message."""
    from nanopnp.io.case import CaseValidationError
    from nanopnp.pipeline.case import loads_case

    with pytest.raises(CaseValidationError) as raised:
        loads_case(PNP.format(schema=schema, switches=WRITTEN))
    assert str(raised.value) == f"<string>: expected schema 'nanopnp/case/v0.5', found '{schema}'"


# -- the supported interpreter range (QR-09, section 2.5, VER-47) ----------------


def _minor_versions(first: str, last: str) -> list[str]:
    """Return ``3.x`` strings from ``first`` to ``last`` inclusive."""
    low, high = (int(version.split(".")[1]) for version in (first, last))
    return [f"3.{minor}" for minor in range(low, high + 1)]


def _specified_range() -> list[str]:
    """Return the interpreters section 2.5 names, read from the specification."""
    text = (ROOT / "SPECIFICATION.md").read_text(encoding="utf-8")
    found = re.search(r"^\| Python \| (3\.\d+) to (3\.\d+)", text, flags=re.MULTILINE)
    assert found is not None, "section 2.5 no longer has a 'Python | 3.x to 3.y' row"
    return _minor_versions(found.group(1), found.group(2))


def _python_versions(node: object) -> set[str]:
    """Return every literal ``python-version`` under a workflow node."""
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
    """``requires-python``, the classifiers, ruff's target and the CI matrix all say 3.11-3.14."""
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
    tested = _python_versions(workflow["jobs"]["check"]) | _python_versions(
        workflow["jobs"]["test-matrix"]
    )
    assert sorted(tested) == specified, f"CI tests {sorted(tested)}"

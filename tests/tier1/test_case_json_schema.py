"""VER-76: the case schema's JSON Schema export and the fields the editors walk agree."""

from __future__ import annotations

import copy
import json
from typing import Any

import pytest

from nanopnp.io.case_paths import (
    FieldReference,
    _literal_options,
    case_fields,
    case_json_schema,
    schema_leaves,
)


def _field_paths() -> set[str]:
    return {field.path for field in case_fields()}


def test_ver76_schema_leaves_equal_case_fields() -> None:
    assert set(schema_leaves(case_json_schema())) == _field_paths()


def test_ver76_an_extra_schema_leaf_fails() -> None:
    schema = copy.deepcopy(case_json_schema())
    schema["$defs"]["ElectrolyteSpec"]["properties"]["added"] = {"type": "number"}
    assert set(schema_leaves(schema)) - _field_paths() == {"electrolyte.added"}


def test_ver76_a_missing_schema_leaf_fails() -> None:
    schema = copy.deepcopy(case_json_schema())
    del schema["$defs"]["ElectrolyteSpec"]["properties"]["temperature_K"]
    assert _field_paths() - set(schema_leaves(schema)) == {"electrolyte.temperature_K"}


def test_ver76_an_extra_case_field_fails() -> None:
    fields = (*case_fields(), FieldReference(path="electrolyte.added", annotation=float))
    assert {field.path for field in fields} - set(schema_leaves(case_json_schema())) == {
        "electrolyte.added"
    }


def test_ver76_a_mapping_of_blocks_is_refused() -> None:
    schema: dict[str, Any] = {
        "properties": {
            "blocks": {
                "type": "object",
                "additionalProperties": {"type": "object", "properties": {"a": {"type": "number"}}},
            }
        }
    }
    with pytest.raises(NotImplementedError, match="mapping of blocks"):
        schema_leaves(schema)


def test_ver76_lists_unions_and_maps_walk_as_case_fields_does() -> None:
    leaves = set(schema_leaves(case_json_schema()))
    assert {"electrolyte.species.0.name", "electrolyte.species.0.z"} <= leaves
    assert "electrolyte.species" not in leaves
    assert {"structure.symmetry.point_group", "structure.source.path"} <= leaves
    assert {"physics.solid_permittivities", "inputs.mesh.groups"} <= leaves
    assert "physics.solid_permittivities.membrane" not in leaves


def test_ver76_every_literal_leaf_carries_its_choices() -> None:
    schema = case_json_schema()
    json.dumps(schema)
    leaves = schema_leaves(schema)
    checked = 0
    for field in case_fields():
        options = _literal_options(field.annotation)
        if options is None:
            continue
        node = leaves[field.path]
        branches = [node, *node.get("anyOf", ())]
        found: set[str] = set()
        for branch in branches:
            found.update(str(value) for value in branch.get("enum", ()))
            if "const" in branch:
                found.add(str(branch["const"]))
        assert found == set(options), field.path
        checked += 1
    assert checked > 0

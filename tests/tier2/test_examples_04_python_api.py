"""VER-46 (with IF-01, IF-07, FR-27 and NUM-11): example 04, the Python API tour."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nanopnp.io.vocabulary import (
    POTENTIAL,
    PRESSURE,
    VELOCITY,
)
from nanopnp.physics.models import concentration_field_name
from nanopnp.post.export import (
    WALL_DISTANCE,
    attribute_name,
)
from nanopnp.validation.examples import copy_example, run_tagged

pytestmark = pytest.mark.extended

REPOSITORY = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def tour(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    example = copy_example(
        REPOSITORY / "examples" / "04-python-api",
        tmp_path_factory.mktemp("examples"),
        repository=REPOSITORY,
    )
    run_tagged(example, "run")
    record = json.loads((example / "tour.json").read_text(encoding="utf-8"))
    assert isinstance(record, dict)
    return record


def test_ver46_a_substituted_mesh_moves_exactly_the_keys_that_read_it(
    tour: dict[str, object],
) -> None:
    stages = tour["stages"]
    substituted = tour["substituted"]
    assert isinstance(stages, dict) and isinstance(substituted, dict)
    finer, renamed = substituted["finer.msh"], substituted["renamed.msh"]
    assert finer["mesh"] != stages["mesh"]
    assert finer["materials"] == stages["materials"]
    assert renamed["mesh"] == stages["mesh"]
    assert renamed["materials"] == stages["materials"]


def test_ver46_exported_fields_carry_the_if07_attribute_names(tour: dict[str, object]) -> None:
    species = tour["species"]
    assert isinstance(species, list)
    fields = [POTENTIAL, VELOCITY, PRESSURE, *(concentration_field_name(s) for s in species)]
    expected = {attribute_name(field) for field in fields} | {WALL_DISTANCE}
    assert set(tour["field_names"]) == expected  # type: ignore[arg-type]

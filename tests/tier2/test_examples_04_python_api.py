"""VER-46 — example 04, the Python API tour (IF-01, IF-07, FR-27).

``tour.py`` runs through the public surface alone and records what it saw in
``tour.json``. Two oracles. Substitution (FR-27): a stage's key is the hash of what
it reads, so a different mesh moves the stage-6 key and leaves stage 8's — which
never reads the mesh — where it was, and a byte-identical copy under another name
moves nothing, because a mesh is keyed by content and not by path (section 5.3.2).
And the exported fields carry exactly the IF-07 attribute names of this model's
fields, taken from :func:`nanopnp.io.fields.attribute_name` rather than written out.
Stabilisation is ``none`` (NUM-11).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from nanopnp.io.fields import WALL_DISTANCE, attribute_name
from nanopnp.physics.models import (
    POTENTIAL,
    PRESSURE,
    VELOCITY,
    concentration_field_name,
)
from nanopnp.validation.examples import copy_example, run_tagged

REPOSITORY = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def tour(tmp_path_factory: pytest.TempPathFactory) -> dict[str, object]:
    """Copy the example, run its ``run`` block, and return ``tour.json``."""
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
    """A different mesh moves stage 6 and not stage 8; the same bytes renamed move neither."""
    stages = tour["stages"]
    substituted = tour["substituted"]
    assert isinstance(stages, dict) and isinstance(substituted, dict)
    finer, renamed = substituted["finer.msh"], substituted["renamed.msh"]
    assert finer["mesh"] != stages["mesh"]
    assert finer["materials"] == stages["materials"]
    assert renamed["mesh"] == stages["mesh"]
    assert renamed["materials"] == stages["materials"]


def test_ver46_exported_fields_carry_the_if07_attribute_names(tour: dict[str, object]) -> None:
    """Potential, each concentration, velocity, pressure, and the wall distance."""
    species = tour["species"]
    assert isinstance(species, list)
    fields = [POTENTIAL, VELOCITY, PRESSURE, *(concentration_field_name(s) for s in species)]
    expected = {attribute_name(field) for field in fields} | {WALL_DISTANCE}
    assert set(tour["field_names"]) == expected  # type: ignore[arg-type]

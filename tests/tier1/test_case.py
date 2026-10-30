"""FR-27, FR-25: a Case edits by copy and a file case records its file."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from nanopnp.api.case import Case
from nanopnp.api.session import Session
from nanopnp.case import Mesh
from nanopnp.cli import main
from nanopnp.io.case_paths import UnknownCasePathError
from nanopnp.io.store import Store

CASE = Path(__file__).resolve().parents[2] / "examples" / "02-charged-pore" / "epnpns.case.yaml"


def test_fr27_a_block_edit_equals_its_leaf_edits() -> None:
    case = Case.load(CASE)
    by_block = case.with_(numerics={"mesh": {"size_scale": 0.5}}, bias_V=0.1)
    by_leaves = case.with_(**{"numerics.mesh.size_scale": 0.5, "boundary_conditions.bias_V": 0.1})
    assert by_block == by_leaves
    # A mapping sets the leaves it names: the example's own element sizes stay.
    assert by_block["numerics.mesh.maxh_nm"] == 4.0
    # A typed block replaces the block whole, so the sizes return to their defaults.
    replaced = (
        case.with_(mesh=case.numerics.mesh)
        if False
        else case.with_(**{"numerics.mesh": Mesh(size_scale=0.5)})
    )
    assert replaced["numerics.mesh.maxh_nm"] is None
    assert case.charge is None
    assert case.with_(charge={}).charge is not None
    # The original is unchanged, and its blocks refuse assignment.
    assert case.numerics.mesh.size_scale == 1.0
    with pytest.raises(ValidationError):
        case.numerics.mesh.size_scale = 0.5  # type: ignore[misc]


def test_fr27_a_leaf_name_resolves_to_its_one_field_and_two_fields_are_refused() -> None:
    case = Case.load(CASE)
    assert case.with_(bias_V=0.1)["bias_V"] == 0.1
    assert case["bias_V"] != 0.1
    with pytest.raises(UnknownCasePathError, match="more than one field"):
        case.with_(grid_spacing_nm=1.0)


def test_fr25_an_unedited_loaded_case_records_its_file_and_an_edited_one_does_not(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Until a case's paths are read beside it (D12), the charge file is read from the working
    # directory.
    monkeypatch.chdir(CASE.parent)
    store = tmp_path / "store"
    assert main(["run", str(CASE), "--upto", "case", "--store", str(store), "--json"]) == 0
    loaded = Case.load(CASE)
    run = Session(store, write=False).run(loaded, upto="case")
    recorded = json.loads((next((store / "runs").iterdir()) / "manifest.json").read_text())
    assert run.manifest.case_hash == recorded["case"]["hash"]
    assert run.manifest.case_text == CASE.read_text(encoding="utf-8")
    assert run.manifest.inputs["files"]["case"]["path"] == str(CASE)
    edited = Session(store, write=False).run(loaded.with_(bias_V=0.1), upto="case")
    assert "case" not in edited.manifest.inputs["files"]
    assert edited.manifest.case_text == loaded.with_(bias_V=0.1).dumps()
    assert edited.manifest.case_hash != run.manifest.case_hash


def test_fr25_a_case_preset_round_trips_through_its_text() -> None:
    built = Case.cylinder(concentration_M=0.1, bias_V=0.05, pore_radius_nm=1.5)
    assert Case.loads(built.dumps()) == built
    assert built.geometry is not None and built.geometry.pore is not None
    assert built.geometry.pore.radius_nm == 1.5
    assert built.inputs.mesh is None
    assert isinstance(built.with_(bias_V=0.1), Case)


def test_fr27_cylinder_wall_charge_is_a_boundary_condition_of_the_preset() -> None:
    plain = Case.cylinder(concentration_M=0.1, bias_V=0.0)
    charged = Case.cylinder(concentration_M=0.1, bias_V=0.0, wall_charge_C_m2=-0.01)
    assert plain.boundary_conditions.wall_charge_C_m2 == 0.0
    assert charged.boundary_conditions.wall_charge_C_m2 == -0.01


def test_fr27_from_structure_names_an_unknown_orient_key() -> None:
    with pytest.raises(TypeError, match="registration"):
        Case.from_structure(
            "2wcd",
            point_group="C7",
            concentration_M=0.1,
            bias_V=0.0,
            orient={"cis_end": "wider", "registration": (1, 2)},
        )


def test_fr27_a_session_stores_in_its_store_not_the_default(tmp_path: Path) -> None:
    session = Session(tmp_path / "held", write=False)
    assert isinstance(session.store, Store)
    assert session.store.root == tmp_path / "held"

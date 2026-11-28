"""VER-80: the guard numbers, example 02's charged pore with one setting off its default."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

from nanopnp import Case, Session, Store
from nanopnp.solve.state import DESCRIPTOR_ENTRY, STATE_KEY
from nanopnp.validation import stability

if TYPE_CHECKING:
    from collections.abc import Mapping

    from conftest import NumberStability
    from nanopnp.io.case import FieldValue
    from nanopnp.pipeline.run import RunResult

pytestmark = pytest.mark.nightly

REPOSITORY = Path(__file__).resolve().parents[2]

CASE = REPOSITORY / "examples" / "02-charged-pore" / "epnpns.case.yaml"

SINGLE_RUNG: dict[str, FieldValue] = {"numerics.continuation": "none"}

DEFAULT = {
    "flow": True,
    "variable_density_flow": True,
    "inertia": True,
    "dielectric_gradient_forces": False,
    "log_variables": False,
}


@pytest.fixture(autouse=True)
def _reference_environment_only() -> None:
    where = stability.environment()
    if where != stability.REFERENCE_ENVIRONMENT:
        pytest.skip(
            f"the guard numbers are held in {stability.REFERENCE_ENVIRONMENT} alone, not {where}"
        )


@pytest.fixture(scope="module")
def store(tmp_path_factory: pytest.TempPathFactory) -> Store:
    return Store(tmp_path_factory.mktemp("guard-store"))


def _run(store: Store, workspace: Path, edits: Mapping[str, FieldValue]) -> RunResult:
    case = Case.load(CASE).with_(edits)
    return Session(store, workspace=workspace, write=False).run(case)


def _solved(result: RunResult) -> dict[str, Any]:
    import numpy as np

    with np.load(result.artefacts["solve"].payload[STATE_KEY], allow_pickle=False) as archive:
        descriptor: dict[str, Any] = json.loads(str(archive[DESCRIPTOR_ENTRY]))
    model: dict[str, Any] = descriptor["model"]
    return model


def _mesh_hash(result: RunResult) -> str:
    return str(result.manifest.geometry_and_mesh["content_hash"])


def _check_model(result: RunResult, changed: Mapping[str, bool], mode: str) -> None:
    model = _solved(result)
    assert {name: model["switches"][name] for name in DEFAULT} == {**DEFAULT, **changed}
    assert model["stabilisation"] == mode


def _currents(result: RunResult) -> dict[str, float]:
    currents = result.quantities["stabilisation_currents_A"]
    assert isinstance(currents, dict)
    return {
        f"stabilisation_currents_A[{species}]": float(value) for species, value in currents.items()
    }


def test_ver80_dielectric_gradient_forces_hold_their_numbers(
    store: Store, tmp_path: Path, number_stability: NumberStability
) -> None:
    result = _run(store, tmp_path, {**SINGLE_RUNG, "physics.dielectric_gradient_forces": True})
    _check_model(result, {"dielectric_gradient_forces": True}, "none")
    number_stability("guard-dielectric", _mesh_hash(result), result.quantities)


def test_ver80_the_log_branch_holds_its_numbers(
    store: Store, tmp_path: Path, number_stability: NumberStability
) -> None:
    result = _run(store, tmp_path, {**SINGLE_RUNG, "numerics.log_variables": True})
    _check_model(result, {"log_variables": True}, "none")
    assert "numerics.log_variables" in {deviation.path for deviation in result.manifest.deviations}
    number_stability("guard-log", _mesh_hash(result), result.quantities)


def test_ver80_the_reference_stabilisation_holds_its_numbers(
    store: Store, tmp_path: Path, number_stability: NumberStability
) -> None:
    result = _run(store, tmp_path, {"numerics.stabilisation": "reference"})
    _check_model(result, {}, "reference")
    number_stability("guard-reference", _mesh_hash(result), result.quantities, _currents(result))


def test_ver80_supg_holds_its_numbers(
    store: Store, tmp_path: Path, number_stability: NumberStability
) -> None:
    result = _run(store, tmp_path, {"numerics.stabilisation": "supg"})
    _check_model(result, {}, "supg")
    number_stability("guard-supg", _mesh_hash(result), result.quantities, _currents(result))


def test_ver80_a_constant_density_flow_holds_its_numbers(
    store: Store, tmp_path: Path, number_stability: NumberStability
) -> None:
    result = _run(store, tmp_path, {**SINGLE_RUNG, "physics.variable_density": False})
    _check_model(result, {"variable_density_flow": False}, "none")
    number_stability("guard-constant-density", _mesh_hash(result), result.quantities)


def test_ver80_a_flow_without_inertia_holds_its_numbers(
    store: Store, tmp_path: Path, number_stability: NumberStability
) -> None:
    result = _run(store, tmp_path, {**SINGLE_RUNG, "physics.inertia": False})
    _check_model(result, {"inertia": False}, "none")
    number_stability("guard-no-inertia", _mesh_hash(result), result.quantities)

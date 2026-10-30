from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from nanopnp import Case, Session
from nanopnp.io.case import CaseValidationError
from nanopnp.io.store import Store
from nanopnp.pipeline.case import loads_case, resolve

GOLDEN = Path(__file__).parents[1] / "tier2" / "data" / "number_stability.json"

CASE: dict[str, object] = {
    "schema": "nanopnp/case/v0.5",
    "name": "idealised",
    "geometry": {
        "pore": {"shape": "cylinder", "radius_nm": 2.0},
        "membrane": {"thickness_nm": 6.0},
        "reservoir": {"radius_nm": 10.0},
    },
    "electrolyte": {
        "species": [{"name": "Na+", "z": 1}, {"name": "Cl-", "z": -1}],
        "concentration_M": 0.1,
        "parameters": "willems2020_nacl",
    },
    "boundary_conditions": {"bias_V": 0.05},
    "physics": {"solid_permittivities": {"membrane": 3.2}},
    "numerics": {"mesh": {"maxh_nm": 4.0, "wall_h_nm": 0.35}},
}


def _text(**edits: object) -> str:
    document = json.loads(json.dumps(CASE))
    for path, value in edits.items():
        *parents, leaf = path.split("__")
        target = document
        for parent in parents:
            target = target.setdefault(parent, {})
        if value is None:
            target.pop(leaf, None)
        else:
            target[leaf] = value
    return yaml.safe_dump(document)


def test_ver62_a_declared_cylinder_meshes_to_the_recorded_mesh(tmp_path: Path) -> None:
    recorded = json.loads(GOLDEN.read_text(encoding="utf-8"))["walks"]["example-01"]
    case = tmp_path / "case.yaml"
    case.write_text(_text(), encoding="utf-8")
    result = Session(Store(tmp_path / "store"), write=False).run(Case.load(case), upto="mesh")
    mesh = result.artefacts["mesh"]
    assert mesh.summary["content_hash"] == recorded["reference_mesh"]
    assert "default" not in mesh.summary["boundaries"]


def test_phy09_a_pore_case_without_a_membrane_permittivity_is_refused() -> None:
    document = loads_case(_text(physics__solid_permittivities=None))
    with pytest.raises(CaseValidationError, match=r"physics\.solid_permittivities\.membrane"):
        resolve(document)


def test_phy09_a_wall_charge_beside_no_idealised_pore_is_refused(tmp_path: Path) -> None:
    mesh = tmp_path / "pore.msh"
    mesh.write_text("")
    document = json.loads(json.dumps(CASE))
    del document["geometry"], document["numerics"]
    document["inputs"] = {"mesh": {"path": str(mesh), "format": "msh41"}}
    document["boundary_conditions"]["wall_charge_C_m2"] = 0.01
    with pytest.raises(CaseValidationError, match=r"boundary_conditions\.wall_charge_C_m2"):
        resolve(loads_case(yaml.safe_dump(document)))

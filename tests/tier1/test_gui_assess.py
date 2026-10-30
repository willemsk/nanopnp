"""VER-55: measuring an edit and seeding after a refusal, from the case's stored stages."""

from __future__ import annotations

from pathlib import Path

import pytest

from nanopnp import Case, Session
from nanopnp.geometry.profile import load_profile
from nanopnp.gui.assess import (
    AssessRequest,
    assess,
)
from nanopnp.io.store import Store

CASE = """\
schema: nanopnp/case/v0.5
name: {name}
structure:
  source: {{path: {pdb}}}
  symmetry: {{point_group: C12}}
geometry: {{contour: {{isolevel: {isolevel}}}}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 0.1
  parameters: willems2020_nacl
boundary_conditions: {{bias_V: 0.1}}
physics: {{model: epnp-ns, solid_permittivities: {{membrane: 3.2}}}}
"""


@pytest.fixture(scope="module")
def tube_store(tube_pdb: Path, tmp_path_factory: pytest.TempPathFactory):
    root = tmp_path_factory.mktemp("assess")
    store = Store(root / "store")
    cases = {}
    for name, isolevel in (("accepted", 0.25), ("refused", 0.1)):
        path = root / f"{name}.case.yaml"
        path.write_text(CASE.format(name=name, pdb=tube_pdb, isolevel=isolevel), encoding="utf-8")
        cases[name] = path
    return root, store, cases


def test_ver55_an_accepted_loop_measures_to_its_gate_record(tube_store) -> None:
    _root, store, cases = tube_store
    result = Session(store, write=False).run(Case.load(cases["accepted"]), upto="contour")
    artefact = result.artefacts["contour"]
    loop = load_profile(artefact.payload["profile"]).vertices

    measured = assess(
        AssessRequest(case=str(cases["accepted"]), store=str(store.root), vertices=tuple(loop))
    )
    assert measured.passed
    assert measured.record == artefact.summary["gate"]

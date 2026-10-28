"""FR-30: a leaf name that two fields share is refused, never resolved to one of them silently."""

from __future__ import annotations

from pathlib import Path

import pytest

import nanopnp
from nanopnp.io.case_paths import UnknownCasePathError

CASE = Path(__file__).resolve().parents[2] / "examples" / "02-charged-pore" / "epnpns.case.yaml"


def test_case_edit_by_leaf_name_matches_the_dotted_path() -> None:
    case = nanopnp.Case.load(CASE, write=False)
    by_name = case.with_(bias_V=0.1)
    by_path = case.with_(**{"boundary_conditions.bias_V": 0.1})
    assert by_name.document == by_path.document
    assert by_name["bias_V"] == 0.1
    assert case["bias_V"] != 0.1


def test_case_leaf_name_shared_by_two_fields_is_refused() -> None:
    case = nanopnp.Case.load(CASE, write=False)
    with pytest.raises(UnknownCasePathError, match="more than one field"):
        case.with_(grid_spacing_nm=1.0)


def test_case_load_rebases_relative_inputs_on_the_case_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    case = nanopnp.Case.load(CASE, write=False)
    inputs = case.document.inputs
    assert inputs is not None
    for supplied in (inputs.mesh, inputs.charge):
        assert supplied is not None and supplied.path is not None
        assert supplied.path.is_absolute()
        assert supplied.path.parent == CASE.parent

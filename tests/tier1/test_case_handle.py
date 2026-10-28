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


@pytest.mark.parametrize(
    ("concentration_M", "wall_nm"),
    [(0.1, 0.05), (1.0, 0.05), (3.0, 0.035)],
)
def test_cylinder_debye_wall_is_num30s_first_layer_with_its_ceiling(
    concentration_M: float, wall_nm: float, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # NUM-30: min(0.05 nm, lambda_D/5) at eps_r,f0. The absolute values are NUM-30's own (0.035 nm
    # at 3 M), so a mol/L slip shared with stage 6's Debye length cannot pass; stage 6's wall
    # is the second oracle, and 0.1 M and 1 M sit on the ceiling an uncapped lambda_D/5 misses.
    import nanopnp.pipeline.handle as handle
    from nanopnp.materials.corrections import load_corrections
    from nanopnp.mesh.sizing import resolve_wall_size

    meshed: dict[str, float] = {}

    def recorded(*, out: Path, **geometry: float) -> Path:
        meshed.update(geometry)
        out.touch()
        return out

    monkeypatch.setattr(handle, "mesh_cylinder", recorded)
    case = nanopnp.Case.cylinder(
        concentration_M=concentration_M, bias_V=0.0, wall_h_nm="debye", store=tmp_path
    )
    permittivity = load_corrections(case.document.electrolyte.parameters).solvent.permittivity
    wall = resolve_wall_size(case.document, permittivity_0=permittivity.eps_r0)
    assert meshed["wall_h_nm"] == pytest.approx(wall.wall_h_nm, rel=1e-12)
    assert meshed["wall_h_nm"] == pytest.approx(wall_nm, abs=5e-4)


def test_cylinder_mesh_is_remade_when_the_mesher_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A cached mesh is keyed by its numbers and the mesher's identity: a mesher or gate fix must
    # not silently reuse the file an older one wrote.
    import nanopnp.pipeline.handle as handle

    made: list[Path] = []

    def recorded(*, out: Path, **geometry: float) -> Path:
        made.append(out)
        out.touch()
        return out

    monkeypatch.setattr(handle, "mesh_cylinder", recorded)
    for identity in ("before", "before", "after"):
        monkeypatch.setattr(handle, "mesher_identity", lambda identity=identity: identity)
        nanopnp.Case.cylinder(concentration_M=0.1, bias_V=0.0, store=tmp_path)
    assert len(made) == 2
    assert made[0] != made[1]

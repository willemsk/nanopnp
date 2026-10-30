"""A Session runs a case into its store; a hook is not an input, and `only` never computes."""

from __future__ import annotations

from pathlib import Path

import pytest

from nanopnp.api.case import Case
from nanopnp.api.session import Session
from nanopnp.core.stages import CancelFlag
from nanopnp.pipeline.run import MissingUpstreamError

QUICKSTART = (
    Path(__file__).resolve().parents[2] / "examples" / "01-quickstart" / "quickstart.case.yaml"
)


@pytest.fixture
def case() -> Case:
    return Case.load(QUICKSTART)


def test_ver44_session_run_passes_on_its_hooks_and_moves_no_key(case: Case, tmp_path: Path) -> None:
    plain = Session(tmp_path / "plain", write=False).run(case, upto="mesh")
    seen: dict[str, list[object]] = {"stage": [], "artefact": [], "progress": []}
    hooked = Session(tmp_path / "hooked", write=False).run(
        case,
        upto="mesh",
        progress=lambda fraction, message: seen["progress"].append((fraction, message)),
        cancel=CancelFlag(),
        on_stage=lambda name, index, total: seen["stage"].append((name, index, total)),
        on_artefact=lambda name, schema, key, cached: seen["artefact"].append((name, key)),
    )
    assert [stage[0] for stage in seen["stage"]] == [record.name for record in hooked.stages]
    assert seen["progress"]
    assert {name: key for name, key in seen["artefact"]} == {
        name: artefact.hash for name, artefact in plain.artefacts.items()
    }
    assert {name: artefact.hash for name, artefact in hooked.artefacts.items()} == {
        name: artefact.hash for name, artefact in plain.artefacts.items()
    }
    assert sorted(path.name for path in (tmp_path / "hooked").rglob("*.json")) == sorted(
        path.name for path in (tmp_path / "plain").rglob("*.json")
    )


def test_fr27_only_refuses_an_upstream_the_store_does_not_hold(case: Case, tmp_path: Path) -> None:
    session = Session(tmp_path / "store", write=False)
    with pytest.raises(MissingUpstreamError, match="'region'"):
        session.run(case, upto="solve", only=True)
    session.run(case, upto="mesh")
    again = session.run(case, upto="mesh", only=True)
    assert all(record.cached for record in again.stages)


def test_fr24_session_sweep_warm_starts_each_member_from_its_neighbour(tmp_path: Path) -> None:
    case = Case.cylinder(
        concentration_M=0.1, bias_V=0.0, maxh_nm=4.0, wall_h_nm=1.0, outputs=("current",)
    ).with_(
        **{
            "physics.model": "pnp",
            "physics.flow": False,
            "physics.variable_density": False,
            "physics.inertia": False,
            "physics.dielectric_gradient_forces": False,
            "numerics.continuation": "none",
            "electrolyte.corrections": {
                name: {"model": "none"}
                for name in ("diffusivity", "mobility", "viscosity", "permittivity", "density")
            }
            | {"steric": {"model": "none"}},
        }
    )
    result = Session(tmp_path / "store", write=False).sweep(
        case, axis="bias_V", values=[0.0, 0.05, 0.1], check_meshes=False
    )
    assert result.dataset.summary["counts"] == {"ok": 3}
    assert [row["warm_start"]["status"] for row in result.rows] == ["cold", "warm", "warm"]
    assert all(row["directory"] is not None for row in result.rows), "members write their runs"


def test_a_run_short_of_the_solve_refuses_its_field_figures_naming_the_solve(
    case: Case, tmp_path: Path
) -> None:
    run = Session(tmp_path / "store", write=False).run(case, upto="mesh")
    with pytest.raises(KeyError, match="'solve'"):
        run.plot_field("potential")
    with pytest.raises(KeyError, match="'solve'"):
        run.plot_cutline("potential", along="r")
    with pytest.raises(KeyError, match="'solve'"):
        run.field_choices()
    with pytest.raises(ValueError, match="'z' or 'r'"):
        run.plot_cutline("potential", along="x")  # type: ignore[arg-type]

"""VER-44: the render child: a restored state, a scene on disk, named refusals (NUM-11)."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from nanopnp.gui.render import (
    CHI_RANGE,
    VIEWER_DIRNAME,
    ChargeRequest,
    deployed_coefficient,
    render_charge,
)
from nanopnp.io.store import Store
from nanopnp.pipeline.run import run_case

DELTA_AND_SHELL = "{dielectric_transition_nm: 0.2, exclusion_offset_nm: 0.3}"


@pytest.fixture(scope="module")
def charged_run(tmp_path_factory: pytest.TempPathFactory, charged_tube) -> Path:
    work = tmp_path_factory.mktemp("charge-picture")
    case = charged_tube.write(work / "case", charge_block=DELTA_AND_SHELL)
    return run_case(case, store=Store(work / "store"), upto="charge").directory


def _charge_record(run: Path) -> dict[str, object]:
    record = json.loads((run / "run.json").read_text(encoding="utf-8"))
    entry = record["artefacts"]["charge"]
    artefact = Store(Path(record["store"])).get(entry["schema"], entry["hash"])
    assert artefact is not None
    return artefact.summary


def test_ver60_the_drawn_rho_integrates_to_the_record_s_q_mesh(charged_run: Path) -> None:
    from scipy.constants import elementary_charge

    deployed = deployed_coefficient(charged_run, "charge")
    integral_C = (
        2.0
        * math.pi
        * 1e-27
        * deployed.measures.integrate(deployed.coefficient, deployed.mesh, what="the picture")
    )
    conservation = _charge_record(charged_run)["charge"]["conservation"]  # type: ignore[index]
    assert integral_C / elementary_charge == pytest.approx(conservation["q_mesh_e"], rel=1e-12)
    assert integral_C / elementary_charge == pytest.approx(
        conservation["q_net_e"], rel=conservation["consumer"]["tolerance"]
    )


def test_ver60_the_chi_scene_is_the_derived_chi_on_the_unit_range(charged_run: Path) -> None:
    import ngsolve as ngs

    render_charge(ChargeRequest(run=str(charged_run)))
    rendered = render_charge(ChargeRequest(run=str(charged_run), quantity="chi"))

    assert rendered.quantity == "chi"
    assert rendered.units == "1"
    assert rendered.colour_range == CHI_RANGE == (0.0, 1.0)
    assert 0.0 < rendered.limit <= 1.0
    assert Path(rendered.scene) == charged_run / VIEWER_DIRNAME / "chi.json"
    assert (charged_run / VIEWER_DIRNAME / "charge.json").is_file()

    deployed = deployed_coefficient(charged_run, "chi")
    protein = deployed.mesh.Materials("protein")
    mean = deployed.measures.integrate(
        deployed.coefficient, deployed.mesh, definedon=protein, what="chi over protein"
    ) / deployed.measures.integrate(ngs.CF(1.0), deployed.mesh, definedon=protein)
    recorded = {
        entry["material"]: entry["mean"]
        for entry in _charge_record(charged_run)["eps_r"]["material_means"]  # type: ignore[index]
    }
    assert mean == pytest.approx(recorded["protein"], rel=1e-12)
    assert 0.0 < recorded["protein"] < 1.0

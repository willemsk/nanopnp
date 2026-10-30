"""VER-35 (QR-08 end to end): a run directory back to the same numbers."""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass
from pathlib import Path

import pytest

from nanopnp.api.reproduce import (
    DEFAULT_TOLERANCE,
    InputMovedError,
    ReproductionError,
    compare,
    reproduce,
)
from nanopnp.io.store import Store
from nanopnp.mesh.primitives import CylindricalPoreGeometry
from nanopnp.pipeline.run import (
    RUN_RECORD_FILENAME,
    run_case,
)

logger = logging.getLogger(__name__)

PORE = CylindricalPoreGeometry(
    pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0
)
MAXH_NM = 4.0
WALL_H_NM = 1.0
CASE = """
schema: nanopnp/case/v0.5
name: reproduction-probe
inputs:
  mesh:
    path: {mesh_path}
    format: vol
    groups: {{default: interface}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 0.1
  temperature_K: 298.15
  parameters: willems2020_nacl
boundary_conditions:
  bias_V: 0.02
  ground: cis
physics:
  model: epnp-ns
  solid_permittivities: {{membrane: 3.2}}
numerics:
  continuation: default_ladder
  stabilisation: none
outputs: [current, transport_numbers, eof_rate]
"""


@dataclass
class Archived:
    directory: Path
    store: Store
    mesh_path: Path
    case_path: Path


@pytest.fixture(scope="module")
def archived(tmp_path_factory: pytest.TempPathFactory) -> Archived:
    work = tmp_path_factory.mktemp("reproduce")
    mesh_path = work / "pore.vol"
    PORE.generate(maxh_nm=MAXH_NM, wall_h_nm=WALL_H_NM).ngmesh.Save(str(mesh_path))
    case_path = work / "case.yaml"
    case_path.write_text(CASE.format(mesh_path=mesh_path), encoding="utf-8")

    store = Store(work / "store")
    result = run_case(case_path, store=store, workspace=work / "fields")
    logger.info(
        "archived %s: %d stages, quantities %s, stabilisation %s",
        result.directory,
        len(result.stages),
        sorted(result.quantities),
        result.manifest.groups()["stabilisation"],
    )
    return Archived(
        directory=result.directory, store=store, mesh_path=mesh_path, case_path=case_path
    )


# QR-08
def test_ver35_the_run_directory_carries_what_a_reproduction_needs(archived: Archived) -> None:
    record = json.loads((archived.directory / RUN_RECORD_FILENAME).read_text(encoding="utf-8"))
    assert [entry["stage"] for entry in record["stages"]][-1] == "report"
    assert set(record["quantities"]) >= {"current_A", "transport_number", "eof_m3_s"}


def test_ver35_a_run_reproduces_into_a_fresh_store(archived: Archived) -> None:
    found = reproduce(archived.directory)
    solve = next(record for record in found.run.stages if record.name == "solve")
    store = found.run.store

    assert found.reproduced, [drift.summary() for drift in found.drifts]
    assert found.worst is not None
    assert found.worst <= DEFAULT_TOLERANCE
    assert not solve.cached, "the reproduction was served from a store, so it asserted nothing"
    assert store is not None and store.misses > 0
    logger.info(
        "reproduced %d quantities, worst relative difference %.3e, store %d hits / %d misses",
        len(found.quantities),
        found.worst,
        store.hits,
        store.misses,
    )


def test_ver35_reproducing_into_the_store_that_holds_the_run_is_refused(
    archived: Archived,
) -> None:
    with pytest.raises(ReproductionError) as refused:
        reproduce(archived.directory, store=archived.store)
    assert str(archived.store.root) in str(refused.value)
    assert "re-entered" in str(refused.value)


def test_ver35_an_input_whose_contents_moved_aborts_naming_it(
    archived: Archived, tmp_path: Path
) -> None:
    original = archived.mesh_path.read_bytes()
    try:
        archived.mesh_path.write_bytes(original + b"\n# edited\n")
        with pytest.raises(InputMovedError) as moved:
            reproduce(archived.directory)
        assert str(archived.mesh_path) in str(moved.value)
        assert "sha256" in str(moved.value)
    finally:
        archived.mesh_path.write_bytes(original)

    absent = tmp_path / "not-a-run"
    absent.mkdir()
    with pytest.raises(ReproductionError, match="not a run directory"):
        reproduce(absent)


def test_ver35_a_library_difference_is_reported_and_only_fatal_when_asked(
    archived: Archived, monkeypatch: pytest.MonkeyPatch
) -> None:
    from nanopnp.api import reproduce as module

    # Captured before the patch: ``drifted`` reads through the same name it is
    # about to replace, so reaching for it through the module would recur.
    unpatched = module.environment

    def drifted() -> dict[str, object]:
        found = dict(unpatched())
        packages = dict(found["packages"])  # type: ignore[arg-type]
        packages["numpy"] = "0.0.0-not-a-release"
        found["packages"] = packages
        return found

    monkeypatch.setattr(module, "environment", drifted)

    reported = reproduce(archived.directory)
    assert reported.reproduced
    assert any(item.key == "packages.numpy" for item in reported.environment)

    with pytest.raises(ReproductionError, match="strict_environment"):
        reproduce(archived.directory, strict_environment=True)


# QR-12
def test_ver35_compare_localises_a_drift_to_the_scalar_that_moved() -> None:
    recorded = {"currents_A": {"Na+": 1.0, "Cl-": 2.0}, "two_pi_included": True}
    reproduced = {"currents_A": {"Na+": 1.0, "Cl-": 2.0 * (1 + 1e-3)}, "two_pi_included": False}

    drifts, worst = compare(recorded, reproduced, tolerance=DEFAULT_TOLERANCE)
    paths = {drift.path for drift in drifts}
    assert paths == {"currents_A.Cl-", "two_pi_included"}
    assert worst == pytest.approx(1e-3, rel=1e-9)
    assert next(d for d in drifts if d.path == "two_pi_included").relative is None

    with pytest.raises(ReproductionError, match="produced no value for"):
        compare(recorded, {"currents_A": {"Na+": 1.0}}, tolerance=DEFAULT_TOLERANCE)


@pytest.mark.parametrize(
    ("recorded", "reproduced", "drifted"),
    [
        (1.0, math.nan, True),
        (math.nan, 1.0, True),
        (1.0, math.inf, True),
        (math.inf, 1.0, True),
        (math.nan, math.nan, False),
        (math.inf, math.inf, False),
    ],
)
def test_qr08_a_number_that_became_nan_has_not_reproduced(
    recorded: float, reproduced: float, drifted: bool
) -> None:
    drifts, worst = compare(
        {"current_A": recorded}, {"current_A": reproduced}, tolerance=DEFAULT_TOLERANCE
    )
    assert bool(drifts) is drifted
    assert worst == (math.inf if drifted else 0.0)

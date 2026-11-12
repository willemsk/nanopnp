"""VER-55 (VAL-05, VER-53): 2WCD's outline built, measured, edited and run beside its structure."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
import pytest

from nanopnp import Case, Session
from nanopnp.geometry.profile import load_profile
from nanopnp.geometry.region import read_region
from nanopnp.gui.assess import AssessRequest, assess
from nanopnp.gui.geometry import ProfileEditor
from nanopnp.gui.solver import Cancelled, Failed, Finished, Produced, RunRequest, SolverProcess
from nanopnp.io.store import Store
from nanopnp.pipeline.case import load_case
from nanopnp.structure.ensemble import PAYLOAD_NAME as ENSEMBLE_PAYLOAD
from nanopnp.structure.ensemble import AlignedEnsemble
from nanopnp.validation.geometry import register_by_centroid

pytestmark = pytest.mark.nightly

if TYPE_CHECKING:
    from conftest import Prepared2WCD
    from nanopnp.gui.solver import RunEvent
    from nanopnp.pipeline.run import RunResult

logger = logging.getLogger(__name__)

# VER-53, VER-55
CASE = """\
schema: nanopnp/case/v0.6
name: 2wcd-geometry
structure:
  source: {{path: {pdb}}}
  symmetry: {{point_group: C12}}
{geometry}electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 0.15
  parameters: willems2020_nacl
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics: {{model: epnp-ns, solid_permittivities: {{protein: 20.0, membrane: 3.2}}}}
numerics: {{mesh: {{size_scale: 4.0}}}}
"""

TIMEOUT_S = 900.0

GEOMETRY_STAGES = ("case", "structure", "density", "symmetry", "contour", "region", "mesh")

WALKED_BESIDE_STRUCTURE = ("case", "structure", "protonation", "region", "mesh", "charge")


@pytest.fixture(scope="module")
def registered(
    prepared_2wcd: Prepared2WCD, tmp_path_factory: pytest.TempPathFactory
) -> tuple[Path, Path]:
    root = tmp_path_factory.mktemp("2wcd-geometry")
    probe = root / "probe.case.yaml"
    probe.write_text(
        CASE.format(pdb=prepared_2wcd.path, geometry="geometry: {density: {atoms: as_loaded}}\n"),
        encoding="utf-8",
    )
    result = Session(Store(root / "scratch"), write=False).run(Case.load(probe), upto="structure")
    ensemble = AlignedEnsemble.read(result.artefacts["structure"].payload[ENSEMBLE_PAYLOAD])
    centre = register_by_centroid(
        ensemble.positions_nm, name=ensemble.name, resid=ensemble.resid, chain=ensemble.chain
    )
    case = root / "2wcd.case.yaml"
    geometry = (
        f"geometry: {{density: {{atoms: as_loaded}}, membrane: {{centre_z_nm: {centre!r}}}}}\n"
    )
    case.write_text(CASE.format(pdb=prepared_2wcd.path, geometry=geometry), encoding="utf-8")
    return case, root / "store"


def _settle(process: SolverProcess) -> tuple[RunEvent, ...]:
    found: list[RunEvent] = []
    deadline = time.monotonic() + TIMEOUT_S
    while time.monotonic() < deadline:
        found.extend(process.drain())
        if any(isinstance(event, (Finished, Failed, Cancelled)) for event in found):
            process.join(TIMEOUT_S)
            found.extend(process.drain())
            return tuple(found)
        if not process.running:
            time.sleep(0.05)
            found.extend(process.drain())
            break
        time.sleep(0.05)
    process.join(1.0)
    return tuple(found)


def test_ver55_2wcd_builds_measures_and_meshes_a_null_edit_to_the_same_content(
    registered: tuple[Path, Path],
) -> None:
    case, store_root = registered

    started = time.perf_counter()
    process = SolverProcess(RunRequest(case=str(case), store=str(store_root), upto="mesh"))
    process.start()
    events = _settle(process)
    build_s = time.perf_counter() - started
    assert isinstance(events[-1], Finished), [type(event).__name__ for event in events]
    produced = [event for event in events if isinstance(event, Produced)]
    assert tuple(event.name for event in produced) == GEOMETRY_STAGES
    store = Store(store_root)
    for event in produced:
        assert store.get(event.schema, event.hash) is not None, event.name
        assert not event.cached, event.name

    result = Session(store, write=False).run(Case.load(case), upto="mesh")
    assert all(record.cached for record in result.stages)
    assert [result.artefacts[name].hash for name in GEOMETRY_STAGES[1:]] == [
        event.hash for event in produced[1:]
    ]

    contour = result.artefacts["contour"]
    profile = load_profile(contour.payload["profile"])
    started = time.perf_counter()
    measured = assess(
        AssessRequest(case=str(case), store=str(store_root), vertices=tuple(profile.vertices))
    )
    assess_s = time.perf_counter() - started
    assert measured.passed
    assert measured.record == contour.summary["gate"]

    original = load_case(case)
    editor = ProfileEditor.from_profile(profile)
    started = time.perf_counter()
    _, null_case = editor.save_case(original, case)
    null = Session(store).run(Case.load(null_case), upto="mesh")
    null_s = time.perf_counter() - started
    region = read_region(result.artefacts["region"].payload["region"])
    null_region = read_region(null.artefacts["region"].payload["region"])
    assert null.artefacts["region"].hash != result.artefacts["region"].hash
    assert null_region.profile == region.profile
    assert null.artefacts["mesh"].hash != result.artefacts["mesh"].hash
    assert (
        null.artefacts["mesh"].summary["content_hash"]
        == result.artefacts["mesh"].summary["content_hash"]
    )

    loop = np.asarray(profile.vertices)
    constriction = contour.summary["constriction"]
    target = (constriction["r_nm"], constriction["z_nm"])  # type: ignore[index]
    index = int(np.argmin(np.hypot(loop[:, 0] - target[0], loop[:, 1] - target[1])))
    r, z = profile.vertices[index]
    editor.move(index, r + 0.1, z)
    started = time.perf_counter()
    _, moved_case = editor.save_case(original, case)
    moved = Session(store).run(Case.load(moved_case), upto="mesh")
    moved_s = time.perf_counter() - started
    assert moved.artefacts["region"].hash != null.artefacts["region"].hash
    assert (
        moved.artefacts["mesh"].summary["content_hash"]
        != null.artefacts["mesh"].summary["content_hash"]
    )
    artefacts = moved.manifest.inputs["artefacts"]
    assert not {"structure", "density", "symmetry", "contour"} & set(artefacts)  # type: ignore[arg-type]
    files = moved.manifest.inputs["files"]
    assert "profile" in files and "structure" not in files  # type: ignore[operator]

    logger.info(
        "2WCD geometry tab: spawned cold build to stage 6 %.1f s (%d triangles), assess %.2f s, "
        "null edit to stage 6 %.1f s, moved edit %.1f s; constriction vertex %d at "
        "(%.4f, %.4f) nm of %d",
        build_s,
        result.artefacts["mesh"].summary["elements"],
        assess_s,
        null_s,
        moved_s,
        index,
        r,
        z,
        len(profile.vertices),
    )


def _deposit(result: RunResult) -> dict[str, Any]:
    record = result.artefacts["charge"].summary["charge"]
    assert isinstance(record, dict)
    return record


def test_ver55_2wcd_a_null_edit_beside_its_structure_deposits_the_same_charge(
    prepared_2wcd: Prepared2WCD, registered: tuple[Path, Path], tmp_path: Path
) -> None:
    case, store_root = registered
    store = Store(store_root)
    started = time.perf_counter()
    original = Session(store, write=False).run(Case.load(case), upto="charge")
    original_s = time.perf_counter() - started
    contour = original.artefacts["contour"]
    profile = load_profile(contour.payload["profile"])
    geometry = load_case(case).geometry
    assert geometry is not None
    centre = geometry.membrane.centre_z_nm
    editor = ProfileEditor.from_profile(profile)

    def beside_structure(name: str) -> RunResult:
        outline = editor.save(tmp_path)
        lines = (
            f"geometry: {{membrane: {{centre_z_nm: {centre!r}}}}}\n"
            f"inputs:\n  profile: {{path: {outline}, format: profile1}}\n"
        )
        path = tmp_path / f"{name}.case.yaml"
        path.write_text(CASE.format(pdb=prepared_2wcd.path, geometry=lines), encoding="utf-8")
        return Session(store, write=False).run(Case.load(path), upto="charge")

    started = time.perf_counter()
    null = beside_structure("null")
    null_s = time.perf_counter() - started
    assert [record.name for record in null.stages] == list(WALKED_BESIDE_STRUCTURE)
    assert null.artefacts["protonation"].hash == original.artefacts["protonation"].hash
    region = read_region(original.artefacts["region"].payload["region"])
    assert read_region(null.artefacts["region"].payload["region"]).profile == region.profile
    assert (
        null.artefacts["mesh"].summary["content_hash"]
        == original.artefacts["mesh"].summary["content_hash"]
    )
    found, expected = _deposit(null), _deposit(original)
    materials = expected["material_charge_e"]
    assert found["material_charge_e"] == pytest.approx(materials, rel=1e-12)
    for leg in ("producer", "consumer"):
        assert found["conservation"][leg]["relative_error"] == pytest.approx(
            expected["conservation"][leg]["relative_error"], rel=1e-12
        )
    for total in ("q_net_e", "q_grid_e", "q_mesh_e"):
        assert found["conservation"][total] == pytest.approx(
            expected["conservation"][total], rel=1e-12
        )
    artefacts = null.manifest.inputs["artefacts"]
    assert {"structure", "protonation", "region", "mesh", "charge"} <= set(artefacts)  # type: ignore[arg-type]
    assert not {"density", "symmetry", "contour"} & set(artefacts)  # type: ignore[arg-type]
    files = null.manifest.inputs["files"]
    assert {"profile", "structure"} <= set(files)  # type: ignore[arg-type]

    loop = np.asarray(profile.vertices)
    constriction = contour.summary["constriction"]
    target = (constriction["r_nm"], constriction["z_nm"])  # type: ignore[index]
    index = int(np.argmin(np.hypot(loop[:, 0] - target[0], loop[:, 1] - target[1])))
    r, z = profile.vertices[index]
    editor.move(index, r + 0.1, z)
    started = time.perf_counter()
    moved = beside_structure("moved")
    moved_s = time.perf_counter() - started
    assert (
        moved.artefacts["mesh"].summary["content_hash"]
        != null.artefacts["mesh"].summary["content_hash"]
    )
    share = _deposit(moved)["solid_share"]

    logger.info(
        "2WCD outline beside its structure: original to stage 7 %.1f s, null edit %.1f s, moved "
        "edit %.1f s; deposit by material %s e; moved edit's solid share %s",
        original_s,
        null_s,
        moved_s,
        materials,
        share,
    )

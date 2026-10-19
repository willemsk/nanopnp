"""VER-55 (with VAL-05, VER-53): the Geometry tab's build, measure and edit on 2WCD."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pytest

from nanopnp.geometry.profile import load_profile
from nanopnp.geometry.region import read_region
from nanopnp.gui.assess import AssessRequest, assess
from nanopnp.gui.geometry import ProfileEditor
from nanopnp.gui.solver import Cancelled, Failed, Finished, Produced, RunRequest, SolverProcess
from nanopnp.io.store import Store
from nanopnp.pipeline.case import load_case
from nanopnp.pipeline.run import run_case
from nanopnp.structure.ensemble import PAYLOAD_NAME as ENSEMBLE_PAYLOAD
from nanopnp.structure.ensemble import AlignedEnsemble
from nanopnp.validation.geometry import register_by_centroid

if TYPE_CHECKING:
    from conftest import Prepared2WCD
    from nanopnp.gui.solver import RunEvent

logger = logging.getLogger(__name__)

# VER-53, VER-55
CASE = """\
schema: nanopnp/case/v0.5
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


@pytest.fixture(scope="module")
def registered(
    prepared_2wcd: Prepared2WCD, tmp_path_factory: pytest.TempPathFactory
) -> tuple[Path, Path]:
    root = tmp_path_factory.mktemp("2wcd-geometry")
    probe = root / "probe.case.yaml"
    probe.write_text(CASE.format(pdb=prepared_2wcd.path, geometry=""), encoding="utf-8")
    result = run_case(probe, store=Store(root / "scratch"), upto="structure", write=False)
    ensemble = AlignedEnsemble.read(result.artefacts["structure"].payload[ENSEMBLE_PAYLOAD])
    centre = register_by_centroid(
        ensemble.positions_nm, name=ensemble.name, resid=ensemble.resid, chain=ensemble.chain
    )
    case = root / "2wcd.case.yaml"
    geometry = f"geometry: {{membrane: {{centre_z_nm: {centre!r}}}}}\n"
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

    result = run_case(case, store=store, upto="mesh", write=False)
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
    null = run_case(null_case, store=store, upto="mesh")
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
    moved = run_case(moved_case, store=store, upto="mesh")
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

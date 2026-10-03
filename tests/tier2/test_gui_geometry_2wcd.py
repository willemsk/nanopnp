"""VER-55 on a real structure: the Geometry tab's build, measurement and hand edit on 2WCD.

The Tier 1 files hold each part of WP24 to an oracle on a synthetic tube; this
one runs the same parts on the prepared 2WCD, through the root conftest's
``prepared_2wcd``, registered as VAL-05 registers it (the C-alpha centroid of
residues 8-292 at ``Z_MD``, WP22 D6). Four things:

- the spawned build, ``upto="mesh"``, reports ``Produced`` for stages 1 to 6 in
  walk order, each naming an entry the store holds, and then ``Finished``;
- :func:`~nanopnp.gui.assess.assess` on stage 4's own loop reproduces the
  ``gate`` record of its summary exactly (D9);
- the null edit, written through ``with_profile``, gives stage 5 the same
  model-frame profile to the bit and stage 6 the same mesh content under a new
  key (Design §3);
- moving the constriction vertex 0.1 nm outward changes both, and the manifest
  records the profile by content and no stage 1-4 artefact (D4-D6).

The runtime of each is logged: ``--log-cli-level=INFO``.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pytest

from nanopnp.geometry.region import read_region
from nanopnp.gui.assess import AssessRequest, assess
from nanopnp.gui.geometry import ProfileEditor
from nanopnp.gui.solver import Cancelled, Failed, Finished, Produced, RunRequest, SolverProcess
from nanopnp.io.case import load_case
from nanopnp.io.run import run_case
from nanopnp.io.store import Store
from nanopnp.mesh.profile import load_profile
from nanopnp.structure.ensemble import PAYLOAD_NAME as ENSEMBLE_PAYLOAD
from nanopnp.structure.ensemble import AlignedEnsemble
from nanopnp.validation.geometry import register_by_centroid

if TYPE_CHECKING:
    from conftest import Prepared2WCD
    from nanopnp.gui.solver import RunEvent

logger = logging.getLogger(__name__)

CASE = """\
schema: nanopnp/case/v2
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
"""At ``size_scale`` 4 (WP33 D5): VER-55's claims are about the shell's plumbing and the
stage-4 gate, and none depends on element size. The default-size 2WCD mesh is gated by
``test_pipeline_2wcd.py`` (VER-53)."""

TIMEOUT_S = 900.0
"""A cold walk of 2WCD through stage 6 takes tens of seconds; the wait is not the test."""

GEOMETRY_STAGES = ("case", "structure", "density", "symmetry", "contour", "region", "mesh")


@pytest.fixture(scope="module")
def registered(
    prepared_2wcd: Prepared2WCD, tmp_path_factory: pytest.TempPathFactory
) -> tuple[Path, Path]:
    """Return a 2WCD case registered by the C-alpha centroid, and an empty store root.

    Stage 1 runs once in a scratch store to read the registration off the
    aligned structure, so the store the spawned build writes into starts empty
    and its walk is a cold one.
    """
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
    """Drain the build until it posts a terminal event, or time out."""
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
    """The four VER-55 claims on 2WCD, in the order the tab would make them."""
    case, store_root = registered

    # 1. The spawned build: every geometry stage reported, in walk order, stored.
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

    # The in-process walk reads what the child stored: every stage from the store.
    result = run_case(case, store=store, upto="mesh", write=False)
    assert all(record.cached for record in result.stages)
    assert [result.artefacts[name].hash for name in GEOMETRY_STAGES[1:]] == [
        event.hash for event in produced[1:]
    ]

    # 2. measure on stage 4's own loop is its gate record, exactly.
    contour = result.artefacts["contour"]
    profile = load_profile(contour.payload["profile"])
    started = time.perf_counter()
    measured = assess(
        AssessRequest(case=str(case), store=str(store_root), vertices=tuple(profile.vertices))
    )
    assess_s = time.perf_counter() - started
    assert measured.passed
    assert measured.record == contour.summary["gate"]

    # 3. The null edit: stage 5's model-frame profile to the bit, the mesh content equal.
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

    # 4. The constriction vertex 0.1 nm outward: both hashes move.
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

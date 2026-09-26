"""VER-53 on a real structure: the prepared 2WCD from its PDB file to a mesh, and on to a report.

RSK-05 was that a structure-derived profile would not assemble and mesh without a
hand-drawn membrane. This file retires it: the root conftest's ``prepared_2wcd``
runs through stages 1 to 6 at the default sizes, and the mesh passes VER-10 and
the D9 wall-size gate. The axial registration is a test-time choice, the
profile's *trans* tip plus 1.85 nm (the fixture's own offset), and is **not** a
VAL-05 claim; registering 2WCD against the reference is WP22's.

The second half walks the same structure to stage 12 at ``size_scale`` 4 with
``pnp``, flow off and every correction off. That is the cheapest coupled model a
structure case can solve: the electrostatic models refuse a solid domain with no
transport to screen it (section 5.3.1 NOTE), and this case carries two. The
manifest must key every stage and record the mesh the solve actually read.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest

from nanopnp.geometry.contour import PAYLOAD_NAME
from nanopnp.io.run import PIPELINE, run_case
from nanopnp.io.store import Store
from nanopnp.mesh.adapter import read
from nanopnp.mesh.profile import load_profile
from nanopnp.mesh.quality import QUALITY_FLOOR

if TYPE_CHECKING:
    from conftest import Prepared2WCD

logger = logging.getLogger(__name__)

TRANS_TIP_OFFSET_NM = 1.85
"""The fixture's bilayer centre sits 1.85 nm above its *trans* tip; 2WCD is registered alike."""

STRUCTURE = """\
structure:
  source: {{path: {pdb}}}
  symmetry: {{point_group: C12}}
"""

MESH_CASE = """\
schema: nanopnp/case/v2
name: 2wcd-mesh
{structure}{geometry}electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 0.15
  parameters: willems2020_nacl
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics: {{model: epnp-ns, solid_permittivities: {{protein: 20.0, membrane: 3.2}}}}
"""

SOLVE_CASE = """\
schema: nanopnp/case/v2
name: 2wcd-solve
{structure}{geometry}electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 0.15
  parameters: willems2020_nacl
  corrections:
    diffusivity:  {{model: none}}
    mobility:     {{model: none}}
    viscosity:    {{model: none}}
    permittivity: {{model: none}}
    density:      {{model: none}}
    steric:       {{model: none}}
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics:
  model: pnp
  flow: false
  solid_permittivities: {{protein: 20.0, membrane: 3.2}}
numerics:
  continuation: none
  mesh: {{size_scale: 4.0}}
outputs: [current]
"""


@pytest.fixture(scope="module")
def registered(prepared_2wcd: Prepared2WCD, tmp_path_factory: pytest.TempPathFactory):
    """Return the store, the structure block and the membrane block registering 2WCD.

    Stages 1 to 4 run once, and the *trans* tip is read off the profile they
    produce; every later run reuses them from the store.
    """
    root = tmp_path_factory.mktemp("2wcd")
    store = Store(root / "store")
    structure = STRUCTURE.format(pdb=prepared_2wcd.path)
    case = root / "contour.case.yaml"
    case.write_text(MESH_CASE.format(structure=structure, geometry=""), encoding="utf-8")
    result = run_case(case, store=store, upto="contour", write=False)
    profile = load_profile(result.artefacts["contour"].payload[PAYLOAD_NAME])
    tip = float(profile.as_array()[:, 1].min())
    centre = tip + TRANS_TIP_OFFSET_NM
    logger.info(
        "2WCD stages 1-4: %s s; trans tip z = %.4f nm, centre_z_nm = %.4f nm",
        {record.name: round(record.seconds, 2) for record in result.stages},
        tip,
        centre,
    )
    geometry = f"geometry: {{membrane: {{centre_z_nm: {centre!r}}}}}\n"
    return root, store, structure, geometry


def test_ver53_2wcd_meshes_at_the_default_sizes(registered) -> None:
    """Stages 1-6 on 2WCD: VER-10 and D9 pass; the region and sizing are recorded (RSK-05)."""
    root, store, structure, geometry = registered
    case = root / "mesh.case.yaml"
    case.write_text(MESH_CASE.format(structure=structure, geometry=geometry), encoding="utf-8")
    result = run_case(case, store=store, upto="mesh", write=False)
    cached = {record.name for record in result.stages if record.cached}
    assert {"structure", "density", "symmetry", "contour"} <= cached

    region = result.artefacts["region"].summary
    mesh = result.artefacts["mesh"].summary
    quality = mesh["quality"]
    statistics = mesh["sizing"]["wall_statistics"]
    assert quality["min_sicn"] > QUALITY_FLOOR
    assert statistics["mean_ratio"] <= 1.15
    assert statistics["max_ratio"] <= 2.0
    assert region["edge_counts"]["membrane"] == 2

    chord = region["chord"]
    logger.info(
        "2WCD region: chord (%.4f, %.4f) nm, clearance %.4f nm, junction %s nm, "
        "%d profile vertices, face areas %s nm^2",
        chord["trans_nm"],
        chord["cis_nm"],
        chord["clearance_nm"],
        region["junction_nm"],
        region["profile_vertices"],
        region["face_areas_nm2"],
    )
    logger.info(
        "2WCD mesh at %.4f nm: %d triangles, min SICN %.4f, min gamma %.4f; D9 %d segments, "
        "mean %.3f, p95 %.3f, max %.3f",
        statistics["target_nm"],
        mesh["elements"],
        quality["min_sicn"],
        quality["min_gamma"],
        statistics["segments"],
        statistics["mean_ratio"],
        statistics["p95_ratio"],
        statistics["max_ratio"],
    )
    logger.info(
        "2WCD stage times: %s s",
        {record.name: round(record.seconds, 2) for record in result.stages},
    )


def test_ver53_2wcd_walks_to_the_report_and_the_manifest_keys_every_stage(registered) -> None:
    """FR-27: every stage keyed in the manifest; the recorded mesh is the one on disk (FR-25)."""
    root, store, structure, geometry = registered
    case = root / "solve.case.yaml"
    case.write_text(SOLVE_CASE.format(structure=structure, geometry=geometry), encoding="utf-8")
    result = run_case(case, store=store, workspace=root / "work")

    ran = [record.name for record in result.stages]
    assert ran == [name for name in PIPELINE if name != "charge"]
    keyed = result.manifest.inputs["artefacts"]
    for record in result.stages:
        if record.name != "report":
            assert keyed[record.name]["hash"] == record.hash  # type: ignore[index]

    group = result.manifest.geometry_and_mesh
    assert group["generated"] is True
    assert set(group) >= {"structure", "density", "reduction", "contour", "region", "sizing"}
    payload = result.artefacts["mesh"].payload["mesh"]
    assert read(payload, format="msh41").content_hash == group["content_hash"]

    currents = result.quantities["currents_A"]
    logger.info("2WCD pnp at +50 mV, 0.15 M, size_scale 4: currents %s A", currents)
    logger.info(
        "2WCD walk stage times: %s s",
        {record.name: round(record.seconds, 2) for record in result.stages},
    )

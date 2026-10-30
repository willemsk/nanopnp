"""VER-53 on a real structure: the prepared 2WCD from its PDB file to a mesh, and on to a report."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest

from nanopnp import Case, Session
from nanopnp.core.stages import walk_order
from nanopnp.io.store import Store
from nanopnp.mesh.adapter import read
from nanopnp.mesh.quality import QUALITY_FLOOR

pytestmark = pytest.mark.nightly

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from conftest import NumberStability, Prepared2WCD, Seed2WCD

logger = logging.getLogger(__name__)

STRUCTURE = """\
structure:
  source: {{path: {pdb}}}
  symmetry: {{point_group: C12}}
"""

MESH_CASE = """\
schema: nanopnp/case/v0.5
name: 2wcd-mesh
{structure}{geometry}electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 0.15
  parameters: willems2020_nacl
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics: {{model: epnp-ns, solid_permittivities: {{protein: 20.0, membrane: 3.2}}}}
"""

SOLVE_CASE = """\
schema: nanopnp/case/v0.5
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
  variable_density: false
  inertia: false
  solid_permittivities: {{protein: 20.0, membrane: 3.2}}
numerics:
  continuation: none
  mesh: {{size_scale: 4.0}}
outputs: [current]
"""


@pytest.fixture(scope="module")
def registered(
    prepared_2wcd: Prepared2WCD,
    seeded_2wcd: Seed2WCD,
    seeded_protonated_2wcd: Callable[[Path], Path],
    tmp_path_factory: pytest.TempPathFactory,
):
    root = tmp_path_factory.mktemp("2wcd")
    store = Store(seeded_protonated_2wcd(root / "store"))
    structure = STRUCTURE.format(pdb=prepared_2wcd.path)
    logger.info("2WCD centre_z_nm = %.4f nm by the C-alpha centroid", seeded_2wcd.centre_z_nm)
    return root, store, structure, seeded_2wcd.geometry


# VER-10
def test_ver53_2wcd_meshes_at_the_default_sizes(registered) -> None:
    root, store, structure, geometry = registered
    case = root / "mesh.case.yaml"
    case.write_text(MESH_CASE.format(structure=structure, geometry=geometry), encoding="utf-8")
    result = Session(store, write=False).run(Case.load(case), upto="mesh")
    cached = {record.name for record in result.stages if record.cached}
    assert {"structure", "density", "symmetry", "contour", "region", "mesh"} <= cached

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


# FR-27, FR-25
def test_ver53_2wcd_walks_to_the_report_and_the_manifest_keys_every_stage(
    registered, number_stability: NumberStability
) -> None:
    root, store, structure, geometry = registered
    case = root / "solve.case.yaml"
    case.write_text(SOLVE_CASE.format(structure=structure, geometry=geometry), encoding="utf-8")
    result = Session(store, workspace=root / "work").run(Case.load(case))

    ran = [record.name for record in result.stages]
    assert ran == list(walk_order())
    assert "protonation" in {record.name for record in result.stages if record.cached}
    group = result.manifest.charge
    charge = group["charge"]
    assert isinstance(charge, dict)
    assert charge["source"] == "deposited"
    assert charge["q_net_e"] == pytest.approx(-60.0, abs=1e-9)
    conservation = charge["conservation"]
    assert conservation == result.artefacts["charge"].summary["charge"]["conservation"]  # type: ignore[index]
    assert group["protonation"]["source"] == "pdb2pqr"  # type: ignore[index]
    assert result.artefacts["solve"].inputs["charge"] == result.artefacts["charge"].hash
    logger.info(
        "2WCD charged walk at size_scale 4 (%d elements): Q_net %.6f e, legs %.3e and %.3e, "
        "worst plane %.3e (lattice) and %.3e (mesh), solid share %.3f",
        result.artefacts["mesh"].summary["elements"],
        charge["q_net_e"],
        conservation["producer"]["relative_error"],  # type: ignore[index]
        conservation["consumer"]["relative_error"],  # type: ignore[index]
        conservation["per_plane"]["grid_worst_relative_error"],  # type: ignore[index]
        conservation["per_plane"]["mesh_worst_relative_error"],  # type: ignore[index]
        charge["solid_share"]["solid_share"],  # type: ignore[index]
    )
    keyed = result.manifest.inputs["artefacts"]
    for record in result.stages:
        if record.name != "report":
            assert keyed[record.name]["hash"] == record.hash  # type: ignore[index]

    geometry_group = result.manifest.geometry_and_mesh
    assert geometry_group["generated"] is True
    assert set(geometry_group) >= {
        "structure",
        "density",
        "reduction",
        "contour",
        "region",
        "sizing",
    }
    payload = result.artefacts["mesh"].payload["mesh"]
    assert read(payload, format="msh41").content_hash == geometry_group["content_hash"]

    # The golden was recorded on v0.4.0; the mesh hash is asserted before the numbers.
    number_stability(
        "2wcd-charged",
        geometry_group["content_hash"],
        result.quantities,
        {"q_mesh_e": conservation["q_mesh_e"]},  # type: ignore[index]
    )
    currents = result.quantities["currents_A"]
    logger.info("2WCD charged pnp at +50 mV, 0.15 M, size_scale 4: currents %s A", currents)
    logger.info(
        "2WCD walk stage times: %s s",
        {record.name: round(record.seconds, 2) for record in result.stages},
    )

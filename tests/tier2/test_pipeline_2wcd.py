"""VER-53 on a real structure: the prepared 2WCD from its PDB file to a mesh, and on to a report.

RSK-05 was that a structure-derived profile would not assemble and mesh without a
hand-drawn membrane. This file retires it: the root conftest's ``prepared_2wcd``
runs through stages 1 to 6 at the default sizes, and the mesh passes VER-10 and
the D9 wall-size gate. The axial registration is VAL-05's (WP22 D6): the C-alpha
centroid of residues 8-292 is placed at the MD structure's ``Z_MD``, through
:func:`~nanopnp.validation.geometry.register_by_centroid`, so the suite registers
2WCD one way. WP21 used the profile's *trans* tip plus 1.85 nm, 0.056 nm away.

The second half walks the same structure to stage 12 at ``size_scale`` 4 with
``pnp``, flow off and every correction off. That is the cheapest coupled model a
structure case can solve: the electrostatic models refuse a solid domain with no
transport to screen it (section 5.3.1 NOTE), and this case carries two. Since
WP28 it is exit criterion 4's charged walk (D14): ``pnp`` declares ``fixed_charge``,
so both halves of stage 7 run, the protonation read from a store seeded with the
session's ``protonated_2wcd``. The manifest must key every stage, record the mesh
the solve actually read, and record ``Q_net`` and the conservation report.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest

from nanopnp.core.stages import walk_order
from nanopnp.io.store import Store
from nanopnp.mesh.adapter import read
from nanopnp.mesh.quality import QUALITY_FLOOR
from nanopnp.pipeline.run import run_case

pytestmark = pytest.mark.extended

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
def registered(
    prepared_2wcd: Prepared2WCD,
    seeded_2wcd: Seed2WCD,
    seeded_protonated_2wcd: Callable[[Path], Path],
    tmp_path_factory: pytest.TempPathFactory,
):
    """Return the store, the structure block and the membrane block registering 2WCD.

    Stages 1 to 6 and the protonation come from the session's seeds, and so does
    the registration, read off the aligned structure stage 1 produced (WP33 D2);
    every later run reuses them from the store.
    """
    root = tmp_path_factory.mktemp("2wcd")
    store = Store(seeded_protonated_2wcd(root / "store"))
    structure = STRUCTURE.format(pdb=prepared_2wcd.path)
    logger.info("2WCD centre_z_nm = %.4f nm by the C-alpha centroid", seeded_2wcd.centre_z_nm)
    return root, store, structure, seeded_2wcd.geometry


def test_ver53_2wcd_meshes_at_the_default_sizes(registered) -> None:
    """Stages 1-6 on 2WCD: VER-10 and D9 pass; the region and sizing are recorded (RSK-05)."""
    root, store, structure, geometry = registered
    case = root / "mesh.case.yaml"
    case.write_text(MESH_CASE.format(structure=structure, geometry=geometry), encoding="utf-8")
    result = run_case(case, store=store, upto="mesh", write=False)
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


def test_ver53_2wcd_walks_to_the_report_and_the_manifest_keys_every_stage(
    registered, number_stability: NumberStability
) -> None:
    """FR-27: every stage keyed in the manifest; the recorded mesh is the one on disk (FR-25).

    The walk is charged (WP28 D14): every stage of :func:`~nanopnp.core.stages.walk_order` runs, the
    protonation from the seeded store, and the manifest's Charge group records
    ``Q_net`` and the conservation report the deposit was gated on.
    """
    root, store, structure, geometry = registered
    case = root / "solve.case.yaml"
    case.write_text(SOLVE_CASE.format(structure=structure, geometry=geometry), encoding="utf-8")
    result = run_case(case, store=store, workspace=root / "work")

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

    # VER-62 (G10): the charged walk's numbers and its deposited charge hold the
    # golden recorded on v0.4.0's tree, the mesh hash asserted first.
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

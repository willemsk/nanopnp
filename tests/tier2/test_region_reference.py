"""VER-52, VER-53: the ClyA fixture through ``inputs.profile``, stages 5 and 6 (VER-28, VER-10)."""

from __future__ import annotations

import logging

import numpy as np
import pytest

from nanopnp.core.paths import profile_file
from nanopnp.geometry.profile import PoreProfile, load_profile
from nanopnp.geometry.region import build_region, read_region
from nanopnp.geometry.tolerance import TOL_NM
from nanopnp.io.store import Store
from nanopnp.mesh.adapter import from_ngsolve, read
from nanopnp.mesh.quality import QUALITY_FLOOR
from nanopnp.pipeline.run import (
    RunResult,
    run_case,
)

logger = logging.getLogger(__name__)

REFERENCE_MIN_QUALITY = 0.6378

REFERENCE_MEAN_QUALITY = 0.9765

ELEMENT_COUNT_TOLERANCE = 1e-3

EDGE_COUNTS = {
    "axis": 3,
    "cis": 1,
    "interface": 35,
    "membrane": 2,
    "membrane_outer": 2,
    "trans": 1,
    "wall": 151,
}

CASE = """\
schema: nanopnp/case/v0.5
name: fixture-{concentration}
inputs:
  profile: {{path: {path}}}
electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: {concentration}
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics: {{model: pnp-ns, solid_permittivities: {{protein: 20.0, membrane: 3.2}}}}
"""


def _inside_polygon(profile: PoreProfile, points: np.ndarray) -> np.ndarray:
    starts = profile.as_array()
    ends = np.roll(starts, -1, axis=0)
    inside = np.zeros(len(points), dtype=bool)
    for (r0, z0), (r1, z1) in zip(starts, ends, strict=True):
        if z0 == z1:
            continue
        straddles = (points[:, 1] >= min(z0, z1)) & (points[:, 1] < max(z0, z1))
        crossing_r = r0 + (points[:, 1] - z0) / (z1 - z0) * (r1 - r0)
        inside ^= straddles & (crossing_r > points[:, 0])
    return inside


def _run(tmp_path_factory: pytest.TempPathFactory, concentration: float) -> RunResult:
    root = tmp_path_factory.mktemp(f"fixture-{concentration}")
    case = root / "fixture.case.yaml"
    case.write_text(
        CASE.format(path=profile_file("clya_reference_profile"), concentration=concentration),
        encoding="utf-8",
    )
    return run_case(case, store=Store(root / "store"), upto="mesh", write=False)


@pytest.fixture(scope="module")
def at_1M(tmp_path_factory: pytest.TempPathFactory):
    return _run(tmp_path_factory, 1.0)


def test_ver52_the_derived_region_has_the_reference_topology(at_1M) -> None:
    region = at_1M.artefacts["region"].summary
    assert region["edge_counts"] == EDGE_COUNTS
    assert region["profile_vertices"] == 185
    shape = build_region(read_region(at_1M.artefacts["region"].payload["region"]))
    assert len({(round(v.p[0], 9), round(v.p[1], 9)) for v in shape.vertices}) == 193
    junction = region["junction_nm"]
    assert junction["trans"] == pytest.approx(2.7523809523809524, abs=TOL_NM)
    assert junction["cis"] == pytest.approx(4.88, abs=TOL_NM)
    assert region["frame_shift_nm"] == 0.0
    chord = region["chord"]
    logger.info(
        "fixture chord (%.6f, %.6f) nm, clearance %.6f nm",
        chord["trans_nm"],
        chord["cis_nm"],
        chord["clearance_nm"],
    )


def test_ver53_the_generated_mesh_is_conformal_with_no_bilayer_in_the_fluid(at_1M) -> None:
    artefact = at_1M.artefacts["mesh"]
    data = read(artefact.payload["mesh"], format="msh41")
    assert data.content_hash == artefact.summary["content_hash"]
    assert set(data.materials) == {"electrolyte", "membrane", "protein"}
    assert set(data.boundaries) == set(EDGE_COUNTS)

    unique = np.unique(np.round(data.vertices, 9), axis=0)
    assert len(unique) == len(data.vertices)

    profile = load_profile(profile_file("clya_reference_profile"))

    def centroids(material: str) -> np.ndarray:
        index = data.materials.index(material)
        return data.vertices[data.triangles[data.triangle_material == index]].mean(axis=1)

    membrane = centroids("membrane")
    assert np.all(np.abs(membrane[:, 1]) <= 1.4 + TOL_NM)
    assert not np.any(_inside_polygon(profile, membrane))
    assert not np.any(_inside_polygon(profile, centroids("electrolyte")))
    assert np.all(_inside_polygon(profile, centroids("protein")))


def test_ver10_the_generated_mesh_matches_the_drawn_one_and_meets_the_band(
    at_1M, clya_reference_mesh
) -> None:
    summary = at_1M.artefacts["mesh"].summary
    drawn = from_ngsolve(clya_reference_mesh())
    generated = int(summary["elements"])
    assert abs(generated - drawn.element_count) <= ELEMENT_COUNT_TOLERANCE * drawn.element_count
    quality = summary["quality"]
    assert quality["min_sicn"] > QUALITY_FLOOR
    assert quality["min_sicn"] >= REFERENCE_MIN_QUALITY
    assert quality["mean_sicn"] >= REFERENCE_MEAN_QUALITY
    logger.info(
        "fixture at 0.05 nm: %d triangles (drawn %d), min SICN %.4f, min gamma %.4f",
        generated,
        drawn.element_count,
        quality["min_sicn"],
        quality["min_gamma"],
    )


# NUM-30
@pytest.mark.parametrize(("concentration", "wall_nm"), [(1.0, 0.05), (3.0, 0.03505)])
def test_ver53_the_wall_gate_passes_at_both_measured_sizes(
    tmp_path_factory: pytest.TempPathFactory, at_1M, concentration: float, wall_nm: float
) -> None:
    result = at_1M if concentration == 1.0 else _run(tmp_path_factory, concentration)
    sizing = result.artefacts["mesh"].summary["sizing"]
    statistics = sizing["wall_statistics"]
    assert sizing["wall"]["wall_h_nm"] == pytest.approx(wall_nm, abs=1e-4)
    assert statistics["mean_ratio"] <= 1.15
    assert statistics["max_ratio"] <= 2.0
    quality = result.artefacts["mesh"].summary["quality"]
    logger.info(
        "fixture D9 at %.5f nm: %d segments, mean %.3f, p95 %.3f, max %.3f; "
        "%d triangles, min SICN %.4f, min gamma %.4f",
        statistics["target_nm"],
        statistics["segments"],
        statistics["mean_ratio"],
        statistics["p95_ratio"],
        statistics["max_ratio"],
        result.artefacts["mesh"].summary["elements"],
        quality["min_sicn"],
        quality["min_gamma"],
    )
    stage_seconds = {record.name: round(record.seconds, 2) for record in result.stages}
    logger.info("fixture stage times at %.2f M: %s s", concentration, stage_seconds)

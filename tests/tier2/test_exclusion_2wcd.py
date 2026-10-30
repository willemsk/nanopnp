"""VER-59 (with VAL-05, VER-10): 2WCD with an ion-exclusion shell, and a derived chi."""

from __future__ import annotations

import logging
import time
import tracemalloc
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pytest

from nanopnp import Case, Session
from nanopnp.charge.dielectric import derive_solid_fraction, smooth_step, water_facing
from nanopnp.geometry.region import distance_to_loop, distance_to_segments, read_region
from nanopnp.io.store import Store
from nanopnp.mesh.ingest import deployed_mesh
from nanopnp.mesh.quality import QUALITY_FLOOR
from nanopnp.pipeline.case import resolve

pytestmark = pytest.mark.nightly

if TYPE_CHECKING:
    from conftest import Exclusion2WCD, Prepared2WCD, Seed2WCD

logger = logging.getLogger(__name__)

STRUCTURE = """\
structure:
  source: {{path: {pdb}}}
  symmetry: {{point_group: C12}}
"""

MESH_CASE = """\
schema: nanopnp/case/v0.5
name: 2wcd-shell
{structure}{geometry}electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 0.15
  parameters: willems2020_nacl
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics: {{model: epnp-ns, solid_permittivities: {{protein: 20.0, membrane: 3.2}}}}
{charge}"""


@pytest.fixture(scope="module")
def registered(
    prepared_2wcd: Prepared2WCD,
    seeded_2wcd: Seed2WCD,
    tmp_path_factory: pytest.TempPathFactory,
):  # type: ignore[no-untyped-def]
    root = tmp_path_factory.mktemp("2wcd-shell")
    store = Store(seeded_2wcd(root / "store"))
    structure = STRUCTURE.format(pdb=prepared_2wcd.path)
    return root, store, structure, seeded_2wcd.geometry


@pytest.fixture(scope="module")
def meshed(registered, exclusion_2wcd: Exclusion2WCD):  # type: ignore[no-untyped-def]
    root, store, structure, geometry = registered
    case = root / "shell.case.yaml"
    case.write_text(
        MESH_CASE.format(
            structure=structure,
            geometry=geometry,
            charge=f"charge: {{exclusion_offset_nm: {exclusion_2wcd.offset_nm}}}\n",
        ),
        encoding="utf-8",
    )
    return case, Session(store, write=False).run(Case.load(case), upto="mesh")


# VER-10
def test_ver59_2wcd_with_a_shell_meshes_and_every_wall_node_clears_the_lower_bound(
    meshed, exclusion_2wcd: Exclusion2WCD
) -> None:  # type: ignore[no-untyped-def]
    from nanopnp.pipeline.case import load_case

    case, result = meshed
    record = read_region(Path(result.artefacts["region"].payload["region"]))
    shell = record.exclusion
    assert shell is not None
    mesh = result.artefacts["mesh"]
    data = deployed_mesh(resolve(load_case(case)), mesh).data
    wall = data.boundaries.index("wall")
    nodes = np.unique(data.edges[data.edge_group == wall])
    distance = distance_to_loop(data.vertices[nodes], record.points())
    low = exclusion_2wcd.offset_nm - max(
        exclusion_2wcd.h_c_nm**2 / exclusion_2wcd.offset_nm, exclusion_2wcd.offset_nm / 100.0
    )
    assert float(distance.min()) >= low, float(distance.min())
    beyond = float(np.mean(distance > exclusion_2wcd.offset_nm + 1e-6))

    quality = mesh.summary["quality"]
    statistics = mesh.summary["sizing"]["wall_statistics"]
    assert quality["min_sicn"] > QUALITY_FLOOR
    assert quality["min_gamma"] > QUALITY_FLOOR
    assert statistics["mean_ratio"] <= 1.15
    assert statistics["max_ratio"] <= 2.0
    areas = record.face_areas_nm2
    logger.info(
        "VER-59 2WCD shell a = %g nm: %d loop vertices (%d removed by step 6), %d holes filled "
        "(%.4g nm^2), loop edges from %.5f nm to vertices at %.5f nm, wall nodes [%.5f, %.5f] "
        "nm, %.4f of %d beyond a + 1e-6 nm; shell %.4f nm^2 against protein %.4f nm^2; %d "
        "triangles, min SICN %.4f, min gamma %.4f, wall mean %.3f and max %.3f x the target",
        exclusion_2wcd.offset_nm,
        len(shell.loop),
        shell.removed_vertices,
        shell.holes.count,
        shell.holes.area_nm2,
        shell.distance_nm[0],
        shell.distance_nm[1],
        float(distance.min()),
        float(distance.max()),
        beyond,
        len(nodes),
        areas["exclusion"],
        areas["protein"],
        mesh.summary["elements"],
        quality["min_sicn"],
        quality["min_gamma"],
        statistics["mean_ratio"],
        statistics["max_ratio"],
    )
    logger.info(
        "VER-59 2WCD shell stage times: %s s",
        {record.name: round(record.seconds, 2) for record in result.stages},
    )


# VER-10
def test_ver59_2wcd_with_a_shell_meshes_at_3_m(registered, exclusion_2wcd: Exclusion2WCD) -> None:  # type: ignore[no-untyped-def]
    root, store, structure, geometry = registered
    case = root / "shell-3m.case.yaml"
    case.write_text(
        MESH_CASE.format(
            structure=structure,
            geometry=geometry,
            charge=f"charge: {{exclusion_offset_nm: {exclusion_2wcd.offset_nm}}}\n",
        ).replace("concentration_M: 0.15", "concentration_M: 3.0"),
        encoding="utf-8",
    )
    mesh = Session(store, write=False).run(Case.load(case), upto="mesh").artefacts["mesh"]
    sizing = mesh.summary["sizing"]
    statistics = sizing["wall_statistics"]
    quality = mesh.summary["quality"]
    assert sizing["wall"]["wall_h_nm"] == pytest.approx(0.03505, abs=5e-5)
    assert statistics["mean_ratio"] <= 1.1
    assert statistics["max_ratio"] <= 2.0
    assert quality["min_sicn"] > QUALITY_FLOOR
    assert quality["min_gamma"] > QUALITY_FLOOR
    logger.info(
        "VER-59 2WCD shell at 3 M: %d triangles, min SICN %.4f, %d wall segments, mean %.3f and "
        "max %.3f x the %.5f nm target",
        mesh.summary["elements"],
        quality["min_sicn"],
        statistics["segments"],
        statistics["mean_ratio"],
        statistics["max_ratio"],
        sizing["wall"]["wall_h_nm"],
    )


@pytest.mark.slow
def test_ver59_2wcd_chi_at_delta_h_c_costs_and_errors_are_recorded(
    meshed, exclusion_2wcd: Exclusion2WCD
) -> None:  # type: ignore[no-untyped-def]
    from scipy.interpolate import RegularGridInterpolator

    from nanopnp.charge.dielectric import _inside

    _, result = meshed
    record = read_region(Path(result.artefacts["region"].payload["region"]))
    membrane = {
        "half_thickness_nm": record.membrane.half_thickness_nm,
        "inner_trans_nm": record.membrane.inner_trans_nm,
        "inner_cis_nm": record.membrane.inner_cis_nm,
    }
    points = record.points()
    for delta in (exclusion_2wcd.h_c_nm, exclusion_2wcd.delta_nm):
        tracemalloc.start()
        started = time.perf_counter()
        grid = derive_solid_fraction(points, transition_nm=delta, **membrane)
        seconds = time.perf_counter() - started
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        water, _ = water_facing(points, **membrane)
        rng = np.random.default_rng(59)
        (r_low, r_high), (z_low, z_high) = grid.extent_nm
        candidates = np.column_stack(
            (rng.uniform(r_low, r_high, 400_000), rng.uniform(z_low, z_high, 400_000))
        )
        near = candidates[distance_to_segments(candidates, water) < delta][:20_000]
        exact_distance = distance_to_segments(near, water)
        inside = np.array([_inside(points, np.array([r]), np.array([z]))[0, 0] for r, z in near])
        exact = smooth_step(np.where(inside, exact_distance, -exact_distance) / delta + 0.5)
        interpolant = RegularGridInterpolator(
            (grid.z_nm, grid.r_nm), grid.values, bounds_error=False, fill_value=0.0
        )
        error = np.abs(interpolant(near[:, ::-1]) - exact)
        # Away from the membrane, where the held solids override the step.
        clear = np.abs(near[:, 1]) > record.membrane.half_thickness_nm + delta
        logger.info(
            "VER-59 2WCD chi at delta = %g nm: %d x %d samples (%.1f MB), derived in %.2f s, peak "
            "allocation %.1f MB; worst error against the exact step %.3e over %d band points "
            "clear of the membrane (95th percentile %.3e), %.3e over all %d",
            delta,
            grid.shape[0],
            grid.shape[1],
            grid.values.nbytes / 1e6,
            seconds,
            peak / 1e6,
            float(error[clear].max()),
            int(clear.sum()),
            float(np.percentile(error[clear], 95)),
            float(error.max()),
            len(error),
        )

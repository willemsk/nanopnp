"""VER-59 on a real structure: 2WCD with an ion-exclusion shell, and with a derived ``chi``.

The prepared 2WCD, registered as VAL-05 registers it (WP22 D6), with stages 1 to
3 and the protonation from the session's seeded store. With ``a`` = 0.25 nm
(WP30 D15) it meshes at the default sizes: every ``wall`` node lies at least
``a - max(h_c^2/a, a/100)`` from the body, and the share of nodes beyond
``a + 1e-6`` nm, which the closing and the filled pockets leave, is recorded
rather than bounded (section 5.2.1 NOTE on the ion-exclusion shell). With
``delta`` = 0.15 nm added, WP28's charged walk at ``size_scale`` 4 runs to stage
12 with every gate passing, and its manifest names both switches and the mesh's
``exclusion`` material: that walk is ``test_exclusion_2wcd_walk.py``, a file of its own
so the shell meshes here do not wait on PROPKA (WP33 D7).

Under ``-m slow``: the derivation of ``chi`` at ``delta = h_c``, its time and the
peak of its allocations, and the largest error of the lattice against the exact
step anywhere in the band, the vertices included (*Design* section 1).
"""

from __future__ import annotations

import logging
import time
import tracemalloc
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pytest

from nanopnp.charge.dielectric import derive_solid_fraction, smooth_step, water_facing
from nanopnp.geometry.region import distance_to_loop, distance_to_segments, read_region
from nanopnp.io.store import Store
from nanopnp.mesh.ingest import deployed_mesh
from nanopnp.mesh.quality import QUALITY_FLOOR
from nanopnp.pipeline.case import resolve
from nanopnp.pipeline.run import run_case

pytestmark = pytest.mark.extended

if TYPE_CHECKING:
    from conftest import Prepared2WCD, Seed2WCD

logger = logging.getLogger(__name__)

OFFSET_NM = 0.25
"""``a``: ``a_Na/2`` of ``willems2020_nacl`` (WP30 D15)."""

DELTA_NM = 0.15
"""``delta``: the middle of PHY-20's 1-2 Angstrom (WP30 D15)."""

H_C_NM = 0.05
"""The contour's size target at the default density grid spacing."""

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
    """Return the store, the structure block and the membrane block registering 2WCD.

    Stages 1 to 4 and the registration are the session's seed (WP33 D2). The
    shell gives stage 5 a key of its own, so stages 5 and 6 run here. The
    protonation is not needed by the shell meshes, so this module does not wait
    on PROPKA: the charged walk is ``test_exclusion_2wcd_walk.py`` (WP33 D7).
    """
    root = tmp_path_factory.mktemp("2wcd-shell")
    store = Store(seeded_2wcd(root / "store"))
    structure = STRUCTURE.format(pdb=prepared_2wcd.path)
    return root, store, structure, seeded_2wcd.geometry


@pytest.fixture(scope="module")
def meshed(registered):  # type: ignore[no-untyped-def]
    """Walk 2WCD with the shell to stage 6 at the default sizes."""
    root, store, structure, geometry = registered
    case = root / "shell.case.yaml"
    case.write_text(
        MESH_CASE.format(
            structure=structure,
            geometry=geometry,
            charge=f"charge: {{exclusion_offset_nm: {OFFSET_NM}}}\n",
        ),
        encoding="utf-8",
    )
    return case, run_case(case, store=store, upto="mesh", write=False)


def test_ver59_2wcd_with_a_shell_meshes_and_every_wall_node_clears_the_lower_bound(
    meshed,
) -> None:  # type: ignore[no-untyped-def]
    """The lower band at every ``wall`` node; VER-10 and D9 pass; the closed share recorded."""
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
    low = OFFSET_NM - max(H_C_NM**2 / OFFSET_NM, OFFSET_NM / 100.0)
    assert float(distance.min()) >= low, float(distance.min())
    beyond = float(np.mean(distance > OFFSET_NM + 1e-6))

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
        OFFSET_NM,
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


def test_ver59_2wcd_with_a_shell_meshes_at_3_m(registered) -> None:  # type: ignore[no-untyped-def]
    """At 3 M the ``auto`` wall target is 0.035 nm, where the ring's whole edges were refused.

    Netgen left each 0.0525 nm ring edge as one segment, and the wall-size gate
    refused the mean of 1.457 (``.knowledge/06`` section 8.1.4). Cut into
    ``ceil(L / 1.1 h)`` segments, the mesh passes VER-10 and the gate.
    """
    root, store, structure, geometry = registered
    case = root / "shell-3m.case.yaml"
    case.write_text(
        MESH_CASE.format(
            structure=structure,
            geometry=geometry,
            charge=f"charge: {{exclusion_offset_nm: {OFFSET_NM}}}\n",
        ).replace("concentration_M: 0.15", "concentration_M: 3.0"),
        encoding="utf-8",
    )
    mesh = run_case(case, store=store, upto="mesh", write=False).artefacts["mesh"]
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
def test_ver59_2wcd_chi_at_delta_h_c_costs_and_errors_are_recorded(meshed) -> None:  # type: ignore[no-untyped-def]
    """Recorded: the derivation's time and peak allocation at ``delta = h_c``, and its worst error.

    The worst error is against the exact ``S(s/delta + 1/2)``, with ``s`` from
    the distance to ``W`` and the scanline's sign, at 20 000 points drawn
    uniformly in the band ``|s| < delta``, vertices and the medial axis included,
    where the edge-midpoint bound of *Design* section 1 does not hold.
    """
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
    for delta in (H_C_NM, DELTA_NM):
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

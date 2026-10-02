"""VER-59 on a real structure: 2WCD with an ion-exclusion shell, and with a derived ``chi``.

The prepared 2WCD, registered as VAL-05 registers it (WP22 D6), with stages 1 to
3 and the protonation from the session's seeded store. With ``a`` = 0.25 nm
(WP30 D15) it meshes at the default sizes: every ``wall`` node lies at least
``a - max(h_c^2/a, a/100)`` from the body, and the share of nodes beyond
``a + 1e-6`` nm, which the closing and the filled pockets leave, is recorded
rather than bounded (section 5.2.1 NOTE on the ion-exclusion shell). With
``delta`` = 0.15 nm added, WP28's charged walk at ``size_scale`` 4 runs to stage
12 with every gate passing, and its manifest names both switches and the mesh's
``exclusion`` material.

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

from nanopnp.geometry.region import distance_to_loop, distance_to_segments, read_region
from nanopnp.io.case import resolve
from nanopnp.io.run import PIPELINE, run_case
from nanopnp.io.store import Store
from nanopnp.materials.fields import derive_solid_fraction, smooth_step, water_facing
from nanopnp.mesh.ingest import deployed_mesh
from nanopnp.mesh.quality import QUALITY_FLOOR
from nanopnp.structure.ensemble import PAYLOAD_NAME as ENSEMBLE_PAYLOAD
from nanopnp.structure.ensemble import AlignedEnsemble
from nanopnp.validation.geometry import register_by_centroid

if TYPE_CHECKING:
    from collections.abc import Callable

    from conftest import Prepared2WCD

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
schema: nanopnp/case/v2
name: 2wcd-shell
{structure}{geometry}electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 0.15
  parameters: willems2020_nacl
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics: {{model: epnp-ns, solid_permittivities: {{protein: 20.0, membrane: 3.2}}}}
{charge}"""

SOLVE_CASE = """\
schema: nanopnp/case/v2
name: 2wcd-shell-solve
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
{charge}outputs: [current]
"""


@pytest.fixture(scope="module")
def registered(
    prepared_2wcd: Prepared2WCD,
    seeded_protonated_2wcd: Callable[[Path], Path],
    tmp_path_factory: pytest.TempPathFactory,
):  # type: ignore[no-untyped-def]
    """Return the store, the structure block and the membrane block registering 2WCD."""
    root = tmp_path_factory.mktemp("2wcd-shell")
    store = Store(seeded_protonated_2wcd(root / "store"))
    structure = STRUCTURE.format(pdb=prepared_2wcd.path)
    case = root / "contour.case.yaml"
    case.write_text(MESH_CASE.format(structure=structure, geometry="", charge=""), encoding="utf-8")
    result = run_case(case, store=store, upto="contour", write=False)
    ensemble = AlignedEnsemble.read(result.artefacts["structure"].payload[ENSEMBLE_PAYLOAD])
    centre = register_by_centroid(
        ensemble.positions_nm, name=ensemble.name, resid=ensemble.resid, chain=ensemble.chain
    )
    geometry = f"geometry: {{membrane: {{centre_z_nm: {centre!r}}}}}\n"
    return root, store, structure, geometry


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
    from nanopnp.io.case import load_case

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


def test_ver59_2wcd_with_the_shell_and_a_derived_chi_walks_to_the_report(registered) -> None:  # type: ignore[no-untyped-def]
    """WP28's charged walk with both switches on: every gate, both switches and the material."""
    root, store, structure, geometry = registered
    case = root / "solve.case.yaml"
    charge = f"charge: {{exclusion_offset_nm: {OFFSET_NM}, dielectric_transition_nm: {DELTA_NM}}}\n"
    case.write_text(
        SOLVE_CASE.format(structure=structure, geometry=geometry, charge=charge),
        encoding="utf-8",
    )
    result = run_case(case, store=store, workspace=root / "work")
    assert [record.name for record in result.stages] == list(PIPELINE)
    stage7 = result.artefacts["charge"]
    assert stage7.inputs["region"] == result.artefacts["region"].hash
    assert stage7.parameters["fields"]["eps_r"]["source"] == "derived"  # type: ignore[index]
    record = stage7.summary["eps_r"]
    means = {mean["material"]: mean for mean in record["material_means"]}  # type: ignore[index]
    assert means["exclusion"]["mean"] < 0.5
    assert means["protein"]["mean"] >= 0.9
    assert means["electrolyte"]["mean"] <= 0.1
    manifest = result.manifest
    paths = {deviation.path for deviation in manifest.deviations}
    assert {"charge.exclusion_offset_nm", "charge.dielectric_transition_nm"} <= paths
    sources = {deviation.source for deviation in manifest.contributed_deviations}
    assert "mesh material 'exclusion'" in sources
    assert "inputs.eps_r" not in sources
    assert manifest.charge["eps_r"]["source"] == "derived"  # type: ignore[index]
    logger.info(
        "VER-59 2WCD charged walk with a = %g nm and delta = %g nm at size_scale 4 (%d "
        "elements): chi means %s; currents %s A; stage times %s s",
        OFFSET_NM,
        DELTA_NM,
        result.artefacts["mesh"].summary["elements"],
        {name: round(mean["mean"], 5) for name, mean in means.items()},
        result.quantities["currents_A"],
        {record.name: round(record.seconds, 2) for record in result.stages},
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

    from nanopnp.materials.fields import _inside

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

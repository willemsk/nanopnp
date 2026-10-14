"""VAL-05, the 2WCD leg: the vendored structure against the reference polygon."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from itertools import pairwise
from pathlib import Path
from types import ModuleType
from typing import TYPE_CHECKING

import numpy as np
import pytest

from nanopnp.core.paths import profile_file
from nanopnp.geometry.contour import PAYLOAD_NAME as CONTOUR_PAYLOAD
from nanopnp.geometry.profile import load_profile
from nanopnp.geometry.region import PAYLOAD_NAME as REGION_PAYLOAD
from nanopnp.geometry.region import read_region, to_model_frame
from nanopnp.io.store import Store
from nanopnp.pipeline.run import (
    RunResult,
    run_case,
)
from nanopnp.structure.ensemble import PAYLOAD_NAME as ENSEMBLE_PAYLOAD
from nanopnp.structure.ensemble import AlignedEnsemble
from nanopnp.validation.geometry import (
    ISOLEVELS,
    ProfileComparison,
    attribute_to_construction,
    calpha_centroid_z_nm,
    compare_profiles,
    register_by_centroid,
    rms_optimal_offset,
    sweep_isolevels,
    zero_crossing,
)

pytestmark = pytest.mark.extended

if TYPE_CHECKING:
    from collections.abc import Callable

    from conftest import D10Figures, Prepared2WCD, Seed2WCD

logger = logging.getLogger(__name__)

FROZEN_SIZE_SCALE = 2.0

STRUCTURE = """\
structure:
  source: {{path: {pdb}}}
  symmetry: {{point_group: C12}}
"""

GEOMETRY_CASE = """\
schema: nanopnp/case/v0.5
name: 2wcd-val05
{structure}{geometry}electrolyte:
  species: [{{name: Na+, z: +1}}, {{name: Cl-, z: -1}}]
  concentration_M: 0.15
  parameters: willems2020_nacl
boundary_conditions: {{bias_V: 0.05, ground: cis}}
physics: {{model: epnp-ns, solid_permittivities: {{protein: 20.0, membrane: 3.2}}}}
"""


@dataclass(frozen=True)
class Walked:
    root: Path
    store: Store
    structure: str
    geometry: str
    centre_z_nm: float
    centroid_z_nm: float
    stage1: RunResult
    region: RunResult
    stage4: np.ndarray
    ours: np.ndarray
    comparison: ProfileComparison


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def _stage_time(result: RunResult, name: str) -> str:
    record = next(entry for entry in result.stages if entry.name == name)
    return "read from the store" if record.cached else f"{record.seconds:.2f} s"


@pytest.fixture(scope="module")
def reference() -> np.ndarray:
    return load_profile(profile_file("clya_reference_profile")).as_array()


@pytest.fixture(scope="module")
def walked(
    prepared_2wcd: Prepared2WCD,
    seeded_2wcd: Seed2WCD,
    tmp_path_factory: pytest.TempPathFactory,
    reference: np.ndarray,
) -> Walked:
    root = tmp_path_factory.mktemp("2wcd-val05")
    store = Store(seeded_2wcd(root / "store"))
    structure = STRUCTURE.format(pdb=prepared_2wcd.path)
    case = _write(
        root / "contour.case.yaml", GEOMETRY_CASE.format(structure=structure, geometry="")
    )
    stage1 = run_case(case, store=store, upto="contour", write=False)
    ensemble = AlignedEnsemble.read(stage1.artefacts["structure"].payload[ENSEMBLE_PAYLOAD])
    atoms = {"name": ensemble.name, "resid": ensemble.resid, "chain": ensemble.chain}
    centroid = calpha_centroid_z_nm(ensemble.positions_nm, **atoms)
    centre = register_by_centroid(ensemble.positions_nm, **atoms)
    assert centre == seeded_2wcd.centre_z_nm

    geometry = f"geometry: {{membrane: {{centre_z_nm: {centre!r}}}}}\n"
    case = _write(
        root / "region.case.yaml", GEOMETRY_CASE.format(structure=structure, geometry=geometry)
    )
    region = run_case(case, store=store, upto="region", write=False)
    assert {"structure", "density", "symmetry", "contour", "region"} <= {
        record.name for record in region.stages if record.cached
    }
    record = read_region(region.artefacts["region"].payload[REGION_PAYLOAD])
    stage4 = load_profile(stage1.artefacts["contour"].payload[CONTOUR_PAYLOAD]).as_array()
    assert np.array_equal(record.points(), to_model_frame(stage4, centre))
    assert record.membrane.centre_z_nm == centre
    logger.info(
        "2WCD stages 1-5: %s s; C-alpha centroid z = %.4f nm in the stage-1 frame, "
        "centre_z_nm = %.4f nm",
        {entry.name: round(entry.seconds, 2) for entry in region.stages},
        centroid,
        centre,
    )
    return Walked(
        root=root,
        store=store,
        structure=structure,
        geometry=geometry,
        centre_z_nm=centre,
        centroid_z_nm=centroid,
        stage1=stage1,
        region=region,
        stage4=stage4,
        ours=record.points(),
        comparison=compare_profiles(record.points(), reference, strict=False),
    )


def test_val05_2wcd_against_the_reference_polygon(
    walked: Walked, reference: np.ndarray, as_yaml: Callable[[object], str]
) -> None:
    comparison = compare_profiles(walked.ours, reference)
    logger.info("VAL-05, 2WCD leg:\n%s", as_yaml(comparison))
    assert comparison.planes == 282
    # compare_profiles is strict: an uncrossed plane outside the tip band has already failed.
    assert comparison.compared_planes >= 282 - 4

    attribution = attribute_to_construction(walked.ours, reference, comparison)
    logger.info(
        "VAL-05, 2WCD leg, attribution to the reference's construction (D7):\n%s",
        as_yaml(attribution),
    )
    conditioning = walked.stage1.artefacts["contour"].summary["conditioning"]
    logger.info("2WCD conditioning's lumen change (D7): %s", conditioning["lumen_change"])  # type: ignore[index]

    fitted = rms_optimal_offset(walked.stage4, reference, centre_nm=walked.centre_z_nm)
    logger.info(
        "2WCD registration (D6): centroid %.4f nm, centre_z_nm %.4f nm; rms-optimal offset "
        "%.4f nm (%+.4f nm from the centroid's, a diagnostic never used)",
        walked.centroid_z_nm,
        walked.centre_z_nm,
        fitted,
        fitted - walked.centre_z_nm,
    )
    comparison.check("2wcd")


def test_val05_2wcd_isolevel_sweep_is_strictly_increasing(
    walked: Walked, reference: np.ndarray
) -> None:
    case = _write(
        walked.root / "sweep.case.yaml",
        GEOMETRY_CASE.format(structure=walked.structure, geometry=walked.geometry),
    )
    points = sweep_isolevels(
        case,
        store=walked.store,
        reference=reference,
        workspace=walked.root / "sweep",
    )
    assert [point.isolevel for point in points] == list(ISOLEVELS)
    for point in points:
        if point.comparison is None:
            logger.info("isolevel %g: refused: %s", point.isolevel, point.refusal)
            continue
        c = point.comparison
        logger.info(
            "isolevel %.2f: ε_G %+.2f %%, exact %+.2f %%, mean Δ %+.4f nm, rms %.4f nm, "
            "r_c %.4f nm at z = %.3f nm, %d vertices, %d planes compared, uncrossed %s",
            point.isolevel,
            100 * c.conductance_deviation,
            100 * c.conductance_ratio_exact,
            c.mean_nm,
            c.rms_nm,
            c.constriction_ours.value_nm,
            c.constriction_ours.z_nm,
            point.vertices,
            c.compared_planes,
            [round(z, 3) for z in c.uncrossed_planes_nm],
        )
    default = next(point for point in points if point.isolevel == 0.25)
    assert default.comparison == walked.comparison
    passing = [p.comparison.conductance_deviation for p in points if p.comparison is not None]
    assert all(b > a for a, b in pairwise(passing)), passing
    logger.info("2WCD ε_G crosses zero at isolevel %s (a diagnostic, D8)", zero_crossing(points))


def test_val05_2wcd_mesh_against_the_reference_figures(
    walked: Walked, d10_figures: D10Figures
) -> None:
    case = _write(
        walked.root / "mesh.case.yaml",
        GEOMETRY_CASE.format(structure=walked.structure, geometry=walked.geometry),
    )
    result = run_case(case, store=walked.store, upto="mesh", write=False)
    assert all(record.cached for record in result.stages if record.name != "case")
    mesh = result.artefacts["mesh"].summary
    quality = mesh["quality"]
    logger.info(
        "2WCD mesh at the default sizes (D10): %d triangles (reference %d), min SICN %.4f, "
        "mean SICN %.4f, min gamma %.4f, mean gamma %.4f (reference min %.4f, mean %.4f, by a "
        "measure the model report does not state); stage 6 %s",
        mesh["elements"],
        d10_figures.triangles,
        quality["min_sicn"],  # type: ignore[index]
        quality["mean_sicn"],  # type: ignore[index]
        quality["min_gamma"],  # type: ignore[index]
        quality["mean_gamma"],  # type: ignore[index]
        d10_figures.min_quality,
        d10_figures.mean_quality,
        _stage_time(result, "mesh"),
    )
    reduction = result.artefacts["symmetry"].summary
    for quantity, where in reduction["maximum"].items():  # type: ignore[union-attr]
        logger.info(
            "2WCD stage 3 (D11): largest %s %.4g at r = %.2f nm, z = %.2f nm",
            quantity,
            where["value"],
            where["r_nm"],
            where["z_nm"],
        )


def test_val05_2wcd_mesh_on_both_backends(gmsh_module: ModuleType, walked: Walked) -> None:
    recorded = {}
    for backend in ("netgen", "gmsh"):
        case = _write(
            walked.root / f"mesh-{backend}.case.yaml",
            GEOMETRY_CASE.format(structure=walked.structure, geometry=walked.geometry)
            + f"numerics: {{mesh: {{backend: {backend}}}}}\n",
        )
        result = run_case(case, store=walked.store, upto="mesh", write=False)
        recorded[backend] = result
    assert recorded["gmsh"].artefacts["region"].hash == recorded["netgen"].artefacts["region"].hash
    for backend, result in recorded.items():
        mesh = result.artefacts["mesh"].summary
        quality = mesh["quality"]
        statistics = mesh["sizing"]["wall_statistics"]  # type: ignore[index]
        logger.info(
            "2WCD mesh on %s at the default sizes (WP23 D13): %d triangles, min SICN %.4f, "
            "mean SICN %.4f, min gamma %.4f, mean gamma %.4f; wall %d segments, mean %.3f, max "
            "%.3f x the target; stage 6 %s",
            backend,
            mesh["elements"],
            quality["min_sicn"],  # type: ignore[index]
            quality["mean_sicn"],  # type: ignore[index]
            quality["min_gamma"],  # type: ignore[index]
            quality["mean_gamma"],  # type: ignore[index]
            statistics["segments"],
            statistics["mean_ratio"],
            statistics["max_ratio"],
            _stage_time(result, "mesh"),
        )


@pytest.mark.slow
def test_val05_2wcd_frozen_case_conductance(walked: Walked, val05_frozen_case: str) -> None:
    # The model declares a fixed charge, so the generated leg reads the walked mesh through
    # inputs.mesh and stays uncharged; size_scale is refused beside inputs.mesh.
    walk = run_case(
        _write(
            walked.root / "frozen-walk.case.yaml",
            val05_frozen_case.format(
                name="2wcd-frozen-walk",
                source=walked.structure + walked.geometry,
                size_scale=FROZEN_SIZE_SCALE,
            ),
        ),
        store=walked.store,
        upto="mesh",
        write=False,
    )
    mesh_file = walk.artefacts["mesh"].payload["mesh"]
    generated = run_case(
        _write(
            walked.root / "frozen-generated.case.yaml",
            val05_frozen_case.format(
                name="2wcd-frozen",
                source=f"inputs:\n  mesh: {{path: {mesh_file}, format: msh41}}\n",
                size_scale=1.0,
            ),
        ),
        store=walked.store,
        workspace=walked.root / "frozen-generated",
    )
    assert generated.manifest.charge["status"] == "not run", generated.manifest.charge
    fixture = run_case(
        _write(
            walked.root / "frozen-fixture.case.yaml",
            val05_frozen_case.format(
                name="fixture-frozen",
                source=f"inputs:\n  profile: {{path: {profile_file('clya_reference_profile')}}}\n",
                size_scale=FROZEN_SIZE_SCALE,
            ),
        ),
        store=walked.store,
        workspace=walked.root / "frozen-fixture",
    )
    g_generated = float(generated.quantities["conductance_S"])  # type: ignore[arg-type]
    g_fixture = float(fixture.quantities["conductance_S"])  # type: ignore[arg-type]
    assert g_generated > 0.0 and g_fixture > 0.0
    logger.info(
        "2WCD frozen case (D9) at size_scale %g: G generated %.6e S (%d triangles), fixture "
        "%.6e S (%d triangles); G_gen/G_ref - 1 = %+.2f %% against ε_G %+.2f %% (exact series "
        "%+.2f %%); solve %.1f s and %.1f s",
        FROZEN_SIZE_SCALE,
        g_generated,
        generated.artefacts["mesh"].summary["elements"],
        g_fixture,
        fixture.artefacts["mesh"].summary["elements"],
        100 * (g_generated / g_fixture - 1.0),
        100 * walked.comparison.conductance_deviation,
        100 * walked.comparison.conductance_ratio_exact,
        sum(entry.seconds for entry in generated.stages),
        sum(entry.seconds for entry in fixture.stages),
    )

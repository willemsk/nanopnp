"""VAL-05, the ensemble leg and the Phase 2 gate: ClyA-AS against the reference polygon."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from types import ModuleType

import numpy as np
import pytest
import yaml

from nanopnp.core.paths import REFERENCE_DATA_VARIABLE, profile_file, reference_file
from nanopnp.geometry.contour import PAYLOAD_NAME as CONTOUR_PAYLOAD
from nanopnp.geometry.profile import load_profile
from nanopnp.geometry.region import PAYLOAD_NAME as REGION_PAYLOAD
from nanopnp.geometry.region import read_region
from nanopnp.io.store import Store
from nanopnp.pipeline.run import run_case
from nanopnp.structure.ensemble import PAYLOAD_NAME as ENSEMBLE_PAYLOAD
from nanopnp.structure.ensemble import AlignedEnsemble
from nanopnp.validation.geometry import (
    Z_MD_NM,
    Z_MD_TOLERANCE_NM,
    attribute_to_construction,
    calpha_centroid_z_nm,
    compare_profiles,
    sweep_isolevels,
    zero_crossing,
)

logger = logging.getLogger(__name__)

needs_archive = pytest.mark.skipif(
    reference_file("prod5_clya_as.pdb") is None or reference_file("prod5_clya_as.dcd") is None,
    reason=f"prod5_clya_as.pdb and .dcd are not in ${REFERENCE_DATA_VARIABLE}",
)

GEOMETRY = "geometry: {membrane: {centre_z_nm: 0.0}}\n"

FROZEN_SIZE_SCALE = 1.0


@pytest.fixture(scope="module")
def reference() -> np.ndarray:
    return load_profile(profile_file("clya_reference_profile")).as_array()


@needs_archive
def test_val05_ensemble_pins_z_md(
    tmp_path: Path, ensemble_store: Store, ensemble_case: Callable[..., Path]
) -> None:
    result = run_case(ensemble_case(tmp_path), store=ensemble_store, upto="structure", write=False)
    summary = result.artefacts["structure"].summary
    assert summary["frames"]["indices"] == list(range(48, 98))  # type: ignore[index]
    ensemble = AlignedEnsemble.read(result.artefacts["structure"].payload[ENSEMBLE_PAYLOAD])
    atoms = {"name": ensemble.name, "resid": ensemble.resid, "chain": ensemble.chain}
    centroid = calpha_centroid_z_nm(ensemble.positions_nm, **atoms)
    with_residue_7 = calpha_centroid_z_nm(ensemble.positions_nm, residues=(7, 292), **atoms)
    logger.info(
        "Z_MD measured on DCD frames 48-97: %.4f nm (constant %.2f nm, %+.4f nm); with residue 7 "
        "%.4f nm",
        centroid,
        Z_MD_NM,
        centroid - Z_MD_NM,
        with_residue_7,
    )
    assert abs(centroid - Z_MD_NM) <= Z_MD_TOLERANCE_NM


@needs_archive
def test_val05_ensemble_against_the_reference_polygon(
    tmp_path: Path,
    ensemble_store: Store,
    ensemble_case: Callable[..., Path],
    reference: np.ndarray,
    as_yaml: Callable[[object], str],
) -> None:
    case = ensemble_case(tmp_path, name="clya-as-val05", geometry=GEOMETRY)
    result = run_case(case, store=ensemble_store, upto="region", write=False)
    logger.info(
        "ClyA-AS stages 1-5: %s s; from the store: %s",
        {entry.name: round(entry.seconds, 1) for entry in result.stages},
        [entry.name for entry in result.stages if entry.cached],
    )
    record = read_region(result.artefacts["region"].payload[REGION_PAYLOAD])
    stage4 = load_profile(result.artefacts["contour"].payload[CONTOUR_PAYLOAD]).as_array()
    assert record.membrane.centre_z_nm == 0.0
    assert np.array_equal(record.points(), stage4)
    ours = record.points()

    comparison = compare_profiles(ours, reference)
    logger.info("VAL-05, ensemble leg:\n%s", as_yaml(comparison))
    attribution = attribute_to_construction(ours, reference, comparison)
    logger.info(
        "VAL-05, ensemble leg, attribution to the reference's construction (D7):\n%s",
        as_yaml(attribution),
    )
    conditioning = result.artefacts["contour"].summary["conditioning"]
    logger.info("ClyA-AS conditioning's lumen change (D7): %s", conditioning["lumen_change"])  # type: ignore[index]

    points = sweep_isolevels(
        case,
        store=ensemble_store,
        reference=reference,
        workspace=tmp_path / "sweep",
    )
    for point in points:
        if point.comparison is None:
            logger.info("isolevel %g: refused: %s", point.isolevel, point.refusal)
            continue
        c = point.comparison
        logger.info(
            "isolevel %.2f: ε_G %+.2f %%, exact %+.2f %%, mean Δ %+.4f nm, rms %.4f nm, "
            "r_c %.4f nm at z = %.3f nm, %d planes compared",
            point.isolevel,
            100 * c.conductance_deviation,
            100 * c.conductance_ratio_exact,
            c.mean_nm,
            c.rms_nm,
            c.constriction_ours.value_nm,
            c.constriction_ours.z_nm,
            c.compared_planes,
        )
    logger.info("ClyA-AS ε_G crosses zero at isolevel %s (a diagnostic, D8)", zero_crossing(points))

    comparison.check("ensemble")


@needs_archive
def test_val05_ensemble_mesh_and_frozen_case_conductance(
    tmp_path: Path,
    ensemble_store: Store,
    ensemble_case: Callable[..., Path],
    val05_frozen_case: str,
    reference_triangles: int,
) -> None:
    source = yaml.safe_load(ensemble_case(tmp_path, geometry=GEOMETRY).read_text("utf-8"))
    structure = yaml.safe_dump({"structure": source["structure"], "geometry": source["geometry"]})
    generated_case = tmp_path / "frozen-generated.case.yaml"
    generated_case.write_text(
        val05_frozen_case.format(
            name="clya-as-frozen",
            source=structure,
            size_scale=FROZEN_SIZE_SCALE,
        ),
        encoding="utf-8",
    )
    fixture_case = tmp_path / "frozen-fixture.case.yaml"
    fixture_case.write_text(
        val05_frozen_case.format(
            name="fixture-frozen",
            source=f"inputs:\n  profile: {{path: {profile_file('clya_reference_profile')}}}\n",
            size_scale=FROZEN_SIZE_SCALE,
        ),
        encoding="utf-8",
    )
    generated = run_case(generated_case, store=ensemble_store, workspace=tmp_path / "generated")
    fixture = run_case(fixture_case, store=ensemble_store, workspace=tmp_path / "fixture")

    mesh = generated.artefacts["mesh"].summary
    quality = mesh["quality"]
    logger.info(
        "ClyA-AS mesh at the default sizes (D10): %d triangles (reference %d), min SICN %.4f, "
        "mean SICN %.4f, min gamma %.4f, mean gamma %.4f (reference min 0.6378, mean 0.9765, "
        "by a measure the model report does not state)",
        mesh["elements"],
        reference_triangles,
        quality["min_sicn"],  # type: ignore[index]
        quality["mean_sicn"],  # type: ignore[index]
        quality["min_gamma"],  # type: ignore[index]
        quality["mean_gamma"],  # type: ignore[index]
    )
    reduction = generated.artefacts["symmetry"].summary
    for quantity, where in reduction["maximum"].items():  # type: ignore[union-attr]
        logger.info(
            "ClyA-AS stage 3 (D11): largest %s %.4g at r = %.2f nm, z = %.2f nm",
            quantity,
            where["value"],
            where["r_nm"],
            where["z_nm"],
        )
    g_generated = float(generated.quantities["conductance_S"])  # type: ignore[arg-type]
    g_fixture = float(fixture.quantities["conductance_S"])  # type: ignore[arg-type]
    assert g_generated > 0.0 and g_fixture > 0.0
    logger.info(
        "ClyA-AS frozen case (D9) at size_scale %g: G generated %.6e S (%d triangles), fixture "
        "%.6e S (%d triangles); G_gen/G_ref - 1 = %+.2f %%",
        FROZEN_SIZE_SCALE,
        g_generated,
        mesh["elements"],
        g_fixture,
        fixture.artefacts["mesh"].summary["elements"],
        100 * (g_generated / g_fixture - 1.0),
    )


@needs_archive
def test_val05_ensemble_mesh_on_both_backends(
    gmsh_module: ModuleType,
    tmp_path: Path,
    ensemble_store: Store,
    ensemble_case: Callable[..., Path],
) -> None:
    base = ensemble_case(tmp_path, geometry=GEOMETRY).read_text("utf-8")
    for backend in ("netgen", "gmsh"):
        document = yaml.safe_load(base)
        document["name"] = f"clya-as-mesh-{backend}"
        document.setdefault("numerics", {}).setdefault("mesh", {})["backend"] = backend
        case = tmp_path / f"mesh-{backend}.case.yaml"
        case.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
        result = run_case(case, store=ensemble_store, upto="mesh", write=False)
        mesh = result.artefacts["mesh"].summary
        quality = mesh["quality"]
        statistics = mesh["sizing"]["wall_statistics"]  # type: ignore[index]
        logger.info(
            "ClyA-AS mesh on %s at the default sizes (WP23 D13): %d triangles, min SICN %.4f, "
            "mean SICN %.4f, min gamma %.4f, mean gamma %.4f; wall %d segments, mean %.3f, max "
            "%.3f x the target",
            backend,
            mesh["elements"],
            quality["min_sicn"],  # type: ignore[index]
            quality["mean_sicn"],  # type: ignore[index]
            quality["min_gamma"],  # type: ignore[index]
            quality["mean_gamma"],  # type: ignore[index]
            statistics["segments"],
            statistics["mean_ratio"],
            statistics["max_ratio"],
        )

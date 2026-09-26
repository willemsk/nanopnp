"""VER-49 to VER-51 on the author's ClyA-AS ensemble: the paper's 50 frames to stage 4.

The archive is ``prod5_clya_as.{pdb,dcd}`` under ``$NANOPNP_REFERENCE_DATA``: 98
frames of 54,075 atoms, hydrogens included (``.knowledge/04-clya-geometry-and-charge.md``
§1.1). The paper averaged the final 5 ns; ``frames: {count: 50}`` takes the stride
floor(98/50) = 1 ending on the last frame, so DCD frames 48 to 97, and the test
asserts exactly those. Every other number is recorded, not gated (section 7.1:
Tier 3 is recorded): the stage times, the peak memory, and the largest Cn and
non-Cn variance with where they sit.

Stage 4's test runs on the same module-scoped store, so it reads stages 1 to 3
from the VER-50 run's cache rather than depositing the ensemble again; it shares
the store and not a fixture, so a contour-gate failure cannot fail VER-50 (WP20
plan, work item 6). Its gate verdict is the assertion; the measurements are
logged and recorded in the WP20 plan's Outcomes.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest

from nanopnp.core.paths import REFERENCE_DATA_VARIABLE, reference_file
from nanopnp.io.run import run_case
from nanopnp.io.store import Store

logger = logging.getLogger(__name__)

TOPOLOGY = reference_file("prod5_clya_as.pdb")
TRAJECTORY = reference_file("prod5_clya_as.dcd")

needs_archive = pytest.mark.skipif(
    TOPOLOGY is None or TRAJECTORY is None,
    reason=f"prod5_clya_as.pdb and .dcd are not in ${REFERENCE_DATA_VARIABLE}",
)


def _session_peak_rss_GB() -> float | None:
    """Return this session's peak RSS in GB, an upper bound on the run's; ``None`` on Windows.

    ``resource`` is POSIX only, so it is imported here: at module scope it fails the
    module's collection on Windows, where every tier collects it.
    """
    if sys.platform == "win32":
        return None
    import resource

    # ru_maxrss is kB on Linux and bytes on macOS.
    scale = 1e9 if sys.platform == "darwin" else 1e6
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / scale


@pytest.fixture(scope="module")
def ensemble_store(tmp_path_factory: pytest.TempPathFactory) -> Store:
    """One store for the module, so stage 4 reads stages 1 to 3 from the VER-50 run."""
    return Store(tmp_path_factory.mktemp("clya-as-store"))


def _case(directory: Path) -> Path:
    """Write the ClyA-AS case: the paper's 50 frames, C12, the default geometry blocks."""
    case = directory / "clya-as.case.yaml"
    case.write_text(
        "schema: nanopnp/case/v2\n"
        "name: clya-as-density\n"
        "structure:\n"
        f"  source: {{path: {TOPOLOGY}, variant: ClyA-AS}}\n"
        f"  ensemble: {{trajectory: {TRAJECTORY}, frames: {{count: 50}}}}\n"
        "  symmetry: {point_group: C12}\n"
        "electrolyte:\n"
        "  species: [{name: Na+, z: +1}, {name: Cl-, z: -1}]\n"
        "  concentration_M: 0.15\n"
        "  parameters: willems2020_nacl\n"
        "boundary_conditions: {bias_V: 0.1}\n"
        "physics: {model: epnp-ns, solid_permittivities: {protein: 20.0, membrane: 3.2}}\n",
        encoding="utf-8",
    )
    return case


@needs_archive
def test_ver50_clya_as_ensemble(tmp_path: Path, ensemble_store: Store) -> None:
    """The paper's final 50 frames run to stage 3; times, memory and variance maxima logged."""
    result = run_case(_case(tmp_path), store=ensemble_store, upto="symmetry", write=False)
    structure = result.artefacts["structure"].summary
    density = result.artefacts["density"].summary
    reduction = result.artefacts["symmetry"].summary

    assert structure["frames"]["indices"] == list(range(48, 98))  # type: ignore[index]
    assert density["frames"]["indices"] == list(range(48, 98))  # type: ignore[index]

    seconds = {record.name: round(record.seconds, 1) for record in result.stages}
    peak_GB = _session_peak_rss_GB()
    logger.info(
        "ClyA-AS, 50 frames: %s s; peak RSS of the session %s; grid %s (z, y, x); "
        "%d atoms of which %d hydrogens",
        seconds,
        "not measured on Windows" if peak_GB is None else f"{peak_GB:.2f} GB",
        density["grid"]["shape_zyx"],  # type: ignore[index]
        density["atoms"]["total"],  # type: ignore[index]
        density["hydrogens"],
    )
    for quantity, where in reduction["maximum"].items():  # type: ignore[union-attr]
        logger.info(
            "largest %s: %.4g at r = %.2f nm, z = %.2f nm",
            quantity,
            where["value"],
            where["r_nm"],
            where["z_nm"],
        )


@needs_archive
def test_ver51_clya_as_contour(tmp_path: Path, ensemble_store: Store) -> None:
    """Stage 4 on the 50-frame mean: the gate passes, and every measurement is logged.

    The prototype passed at a feature size of 0.229 nm, with ``r_c - R_p`` from
    +0.173 to +0.869 nm and the constriction 1.610 nm at z = -1.35 nm (WP20 plan,
    Design §6). The contour is in the stage-1 frame, the MD frame, whose bilayer
    centre is z = 0 (G9).
    """
    result = run_case(_case(tmp_path), store=ensemble_store, upto="contour", write=False)
    seconds = {record.name: round(record.seconds, 1) for record in result.stages}
    cached = [record.name for record in result.stages if record.cached]
    summary = result.artefacts["contour"].summary
    logger.info("ClyA-AS contour: stage times %s s; from the store: %s", seconds, cached)
    logger.info(
        "ClyA-AS contour: %d vertices, spacing %.4f nm, feature size %.4f nm, area %.4f nm^2",
        summary["vertex_count"],
        summary["min_vertex_spacing_nm"],
        summary["min_feature_size_nm"],
        -float(summary["signed_area_nm2"]),  # type: ignore[arg-type]
    )
    conditioning = summary["conditioning"]
    logger.info("ClyA-AS conditioning steps: %s", conditioning["steps"])  # type: ignore[index]
    logger.info(
        "ClyA-AS holes filled %s; spacing step removed %s; lumen change %s",
        summary["holes_filled"],
        conditioning["spacing_removed"],  # type: ignore[index]
        conditioning["lumen_change"],  # type: ignore[index]
    )
    logger.info("ClyA-AS band %s; constriction %s", summary["band"], summary["constriction"])
    assert summary["min_feature_size_nm"] > 2 * summary["h_c_nm"]  # type: ignore[operator]

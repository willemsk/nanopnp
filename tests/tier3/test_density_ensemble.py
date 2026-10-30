"""VER-49 to VER-51 on the author's ClyA-AS ensemble: the paper's 50 frames to stage 4."""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

from nanopnp import Case, Session
from nanopnp.core.paths import REFERENCE_DATA_VARIABLE, reference_file
from nanopnp.io.store import Store

logger = logging.getLogger(__name__)

TOPOLOGY = reference_file("prod5_clya_as.pdb")
TRAJECTORY = reference_file("prod5_clya_as.dcd")

needs_archive = pytest.mark.skipif(
    TOPOLOGY is None or TRAJECTORY is None,
    reason=f"prod5_clya_as.pdb and .dcd are not in ${REFERENCE_DATA_VARIABLE}",
)


def _session_peak_rss_GB() -> float | None:
    if sys.platform == "win32":
        return None
    import resource

    # ru_maxrss is kB on Linux and bytes on macOS.
    scale = 1e9 if sys.platform == "darwin" else 1e6
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / scale


@needs_archive
def test_ver50_clya_as_ensemble(
    tmp_path: Path, ensemble_store: Store, ensemble_case: Callable[..., Path]
) -> None:
    result = Session(ensemble_store, write=False).run(
        Case.load(ensemble_case(tmp_path)), upto="symmetry"
    )
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
def test_ver51_clya_as_contour(
    tmp_path: Path, ensemble_store: Store, ensemble_case: Callable[..., Path]
) -> None:
    result = Session(ensemble_store, write=False).run(
        Case.load(ensemble_case(tmp_path)), upto="contour"
    )
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

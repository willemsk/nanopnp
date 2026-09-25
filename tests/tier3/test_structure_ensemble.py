"""VER-48 on the author's ClyA-AS ensemble: stage 1 over all 98 frames, recorded.

The archive is ``prod5_clya_as.{pdb,dcd}`` under ``$NANOPNP_REFERENCE_DATA``:
54,075 atoms, protein and hydrogens only, chains A-L with 286 C-alpha each, and a
DCD whose time metadata reads 1.0 ps per frame
(``.knowledge/04-clya-geometry-and-charge.md`` §1.1). It is the author's and is
not vendored, so the test skips visibly without it.

Every frame is taken, because which 50 made the paper's ensemble is unresolved
(WP18 open question 1, gap G1). The gates must pass; the drift, the RMSD and the
tilt are recorded, not gated (section 7.1: Tier 3 is recorded).
"""

from __future__ import annotations

import logging
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


@needs_archive
def test_ver48_clya_as_ensemble(tmp_path: Path) -> None:
    """All 98 frames pass the stage-1 gates; drift, RMSD and tilt are logged (VER-48)."""
    case = tmp_path / "clya-as.case.yaml"
    case.write_text(
        "schema: nanopnp/case/v2\n"
        "name: clya-as-ensemble\n"
        "structure:\n"
        f"  source: {{path: {TOPOLOGY}, variant: ClyA-AS}}\n"
        f"  ensemble: {{trajectory: {TRAJECTORY}}}\n"
        "  symmetry: {point_group: C12}\n"
        "electrolyte:\n"
        "  species: [{name: Na+, z: +1}, {name: Cl-, z: -1}]\n"
        "  concentration_M: 0.15\n"
        "  parameters: willems2020_nacl\n"
        "boundary_conditions: {bias_V: 0.1}\n"
        "physics: {model: epnp-ns, solid_permittivities: {protein: 20.0, membrane: 3.2}}\n",
        encoding="utf-8",
    )
    result = run_case(case, store=Store(tmp_path / "store"), upto="structure", write=False)
    summary = result.artefacts["structure"].summary
    axis = summary["axis"]["file_frame"]
    frames = summary["frames"]
    rmsd = summary["superposition"]["rmsd_nm"]
    drift = summary["drift_deg"]

    assert summary["n"] == 12
    assert summary["common_ca"] == 286
    assert frames["available"] == 98
    assert len(frames["indices"]) == 98
    logger.info(
        "ClyA-AS, %d frames (interval %.4g ns as read): angle %.4f deg, worst spacing %.3f deg, "
        "permutation RMSD %.4f nm, tilt %.4f deg, offset %.4f nm",
        len(frames["indices"]),
        frames["interval_ns"],
        axis["angle_deg"],
        axis["spacing_error_deg"],
        axis["rmsd_nm"],
        axis["tilt_deg"],
        float(sum(value**2 for value in axis["foot_nm"][:2]) ** 0.5),
    )
    logger.info(
        "superposition RMSD to frame 0: %.4f to %.4f nm; per-frame axis drift up to %.4f deg",
        min(rmsd[1:]),
        max(rmsd),
        max(drift),
    )
    logger.info("frame check on the output: %s", summary["frame_check"])

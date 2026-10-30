"""VER-48 on the author's ClyA-AS ensemble: stage 1 over all 98 frames, recorded."""

from __future__ import annotations

import logging
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


@needs_archive
def test_ver48_clya_as_ensemble(tmp_path: Path) -> None:
    case = tmp_path / "clya-as.case.yaml"
    case.write_text(
        "schema: nanopnp/case/v0.5\n"
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
    result = Session(Store(tmp_path / "store"), write=False).run(Case.load(case), upto="structure")
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

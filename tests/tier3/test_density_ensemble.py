"""VER-49 and VER-50 on the author's ClyA-AS ensemble: the paper's 50 frames to stage 3.

The archive is ``prod5_clya_as.{pdb,dcd}`` under ``$NANOPNP_REFERENCE_DATA``: 98
frames of 54,075 atoms, hydrogens included (``.knowledge/04-clya-geometry-and-charge.md``
§1.1). The paper averaged the final 5 ns; ``frames: {count: 50}`` takes the stride
floor(98/50) = 1 ending on the last frame, so DCD frames 48 to 97, and the test
asserts exactly those. Every other number is recorded, not gated (section 7.1:
Tier 3 is recorded): the stage times, the peak memory, and the largest Cn and
non-Cn variance with where they sit.
"""

from __future__ import annotations

import logging
import resource
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


@needs_archive
def test_ver50_clya_as_ensemble(tmp_path: Path) -> None:
    """The paper's final 50 frames run to stage 3; times, memory and variance maxima logged."""
    case = tmp_path / "clya-as.case.yaml"
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
    result = run_case(case, store=Store(tmp_path / "store"), upto="symmetry", write=False)
    structure = result.artefacts["structure"].summary
    density = result.artefacts["density"].summary
    reduction = result.artefacts["symmetry"].summary

    assert structure["frames"]["indices"] == list(range(48, 98))  # type: ignore[index]
    assert density["frames"]["indices"] == list(range(48, 98))  # type: ignore[index]

    seconds = {record.name: round(record.seconds, 1) for record in result.stages}
    # ru_maxrss is kB on Linux and bytes on macOS; this session's peak, an upper bound.
    scale = 1e9 if sys.platform == "darwin" else 1e6
    peak_GB = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / scale
    logger.info(
        "ClyA-AS, 50 frames: %s s; peak RSS of the session %.2f GB; grid %s (z, y, x); "
        "%d atoms of which %d hydrogens",
        seconds,
        peak_GB,
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

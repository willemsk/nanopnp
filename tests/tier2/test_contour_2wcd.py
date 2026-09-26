"""VER-51 on a real structure: the vendored 2WCD through stage 4.

The root conftest's ``prepared_2wcd`` is chains A-L of the deposited entry, rigidly
moved into a frame stage 1 admits (WP19 D14). Stages 1 to 3 are re-run here rather
than shared with ``test_density_2wcd.py``, because ``--dist loadfile`` may place the
two files on different workers (WP20 plan, work item 6). The gate must pass and the
payload must load through ``load_profile``; every measurement is logged, and
recorded in the WP20 plan's Outcomes beside the prototype's (Design §6).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from nanopnp.geometry.contour import PAYLOAD_NAME
from nanopnp.io.run import run_case
from nanopnp.io.store import Store
from nanopnp.mesh.profile import PIPELINE_SOURCE, load_profile, min_feature_size

if TYPE_CHECKING:
    from conftest import Prepared2WCD

logger = logging.getLogger(__name__)


def _case(tmp_path: Path, pdb: Path) -> Path:
    """Write the 2WCD case: C12, the default density and contour blocks."""
    path = tmp_path / "2wcd.case.yaml"
    path.write_text(
        "schema: nanopnp/case/v2\n"
        "name: 2wcd-contour\n"
        "structure:\n"
        f"  source: {{path: {pdb}}}\n"
        "  symmetry: {point_group: C12}\n"
        "electrolyte:\n"
        "  species: [{name: Na+, z: +1}, {name: Cl-, z: -1}]\n"
        "  concentration_M: 0.15\n"
        "  parameters: willems2020_nacl\n"
        "boundary_conditions: {bias_V: 0.1}\n"
        "physics: {model: epnp-ns, solid_permittivities: {membrane: 3.2}}\n",
        encoding="utf-8",
    )
    return path


def test_ver51_2wcd_contour(prepared_2wcd: Prepared2WCD, tmp_path: Path) -> None:
    """2WCD runs to stage 4: the gate passes and the payload is a loadable profile.

    The gate's verdict is the assertion; the measurements are logged. The profile
    is in the stage-1 frame, so its z extent brackets the constriction the plan
    measured at z = -1.40 nm on the author's copy.
    """
    result = run_case(
        _case(tmp_path, prepared_2wcd.path),
        store=Store(tmp_path / "store"),
        upto="contour",
        write=False,
    )
    seconds = {record.name: round(record.seconds, 2) for record in result.stages}
    logger.info("2WCD stage times: %s s", seconds)
    artefact = result.artefacts["contour"]
    summary = artefact.summary
    profile = load_profile(artefact.payload[PAYLOAD_NAME])
    assert profile.provenance.source == PIPELINE_SOURCE
    assert profile.is_clockwise
    assert profile.provenance.sha256 == summary["reduced_payload_digest"]
    assert min_feature_size(profile.as_array()) > 2 * 0.05

    conditioning = summary["conditioning"]
    band = summary["band"]
    logger.info(
        "2WCD contour: %d vertices, spacing %.4f nm, feature size %.4f nm, area %.4f nm^2",
        summary["vertex_count"],
        summary["min_vertex_spacing_nm"],
        summary["min_feature_size_nm"],
        -float(summary["signed_area_nm2"]),  # type: ignore[arg-type]
    )
    logger.info("2WCD conditioning steps: %s", conditioning["steps"])  # type: ignore[index]
    logger.info(
        "2WCD holes filled: %s; spacing step removed %s vertices; lumen change %s",
        summary["holes_filled"],
        conditioning["spacing_removed"],  # type: ignore[index]
        conditioning["lumen_change"],  # type: ignore[index]
    )
    logger.info(
        "2WCD band: r_c - R_p from %+.4f nm at z = %.2f to %+.4f nm at z = %.2f; constriction %s",
        band["low"]["value_nm"],  # type: ignore[index]
        band["low"]["z_nm"],  # type: ignore[index]
        band["high"]["value_nm"],  # type: ignore[index]
        band["high"]["z_nm"],  # type: ignore[index]
        summary["constriction"],
    )
    low, high = profile.extent_z_nm
    assert low < float(summary["constriction"]["z_nm"]) < high  # type: ignore[index, arg-type]
    assert artefact.inputs == {
        "structure": result.artefacts["structure"].hash,
        "symmetry": result.artefacts["symmetry"].hash,
    }
    assert pytest.approx(0.05) == summary["h_c_nm"]

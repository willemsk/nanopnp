"""VER-51: the vendored 2WCD through stage 4; its gate passes and its profile loads."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from nanopnp.geometry.contour import PAYLOAD_NAME
from nanopnp.geometry.profile import PIPELINE_SOURCE, load_profile, min_feature_size
from nanopnp.io.store import Store
from nanopnp.pipeline.run import run_case

pytestmark = pytest.mark.nightly

if TYPE_CHECKING:
    from conftest import Prepared2WCD, Seed2WCD

logger = logging.getLogger(__name__)


def _case(tmp_path: Path, pdb: Path) -> Path:
    path = tmp_path / "2wcd.case.yaml"
    path.write_text(
        "schema: nanopnp/case/v0.5\n"
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


def test_ver51_2wcd_contour(
    prepared_2wcd: Prepared2WCD, seeded_2wcd: Seed2WCD, tmp_path: Path
) -> None:
    result = run_case(
        _case(tmp_path, prepared_2wcd.path),
        store=Store(seeded_2wcd(tmp_path / "store")),
        upto="contour",
        write=False,
    )
    assert all(record.cached for record in result.stages if record.name != "case")
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

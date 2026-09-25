"""VER-49 and VER-50 on a real structure: the vendored 2WCD through stages 1 to 3.

The root conftest's ``prepared_2wcd`` is chains A-L of the deposited entry, rigidly
moved into a frame stage 1 admits (WP19 D14). Every heavy atom must resolve against
the CHARMM set, the map must stay in [0, 1], stage 3 must conserve it, and the
reduced mean must show an open lumen on the axis. The budget test records the
wall-clock and memory of stages 2 and 3 for the plan's Design §5 prediction; it is
measured, never gated.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import numpy as np
import pytest

from nanopnp.density.map import PAYLOAD_NAME as DENSITY_PAYLOAD
from nanopnp.density.map import DensityMap
from nanopnp.io.run import run_case
from nanopnp.io.store import Store
from nanopnp.structure.ensemble import PAYLOAD_NAME as ENSEMBLE_PAYLOAD
from nanopnp.structure.ensemble import AlignedEnsemble
from nanopnp.symmetry.annular import annular_weights
from nanopnp.symmetry.reduce import PAYLOAD_NAME as REDUCED_PAYLOAD
from nanopnp.symmetry.reduce import ReducedMap

if TYPE_CHECKING:
    from conftest import Prepared2WCD

logger = logging.getLogger(__name__)


def _case(tmp_path: Path, pdb: Path) -> Path:
    """Write the 2WCD case: C12, the default density block (h = 0.05 nm, sigma = 0.93)."""
    path = tmp_path / "2wcd.case.yaml"
    path.write_text(
        "schema: nanopnp/case/v2\n"
        "name: 2wcd-density\n"
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


def test_ver49_ver50_2wcd_to_stage_three(prepared_2wcd: Prepared2WCD, tmp_path: Path) -> None:
    """2WCD runs to stage 3: every atom resolves, the map is bounded and conserved, the lumen open.

    Conservation to 1e-9 relative, slice by slice: ``sum_j mu_j A_j`` against
    ``sum_p rho_p h^2``. The Cn variance cannot exceed the raw variance by more
    than sampling, 1e-4. The axis bin's mean is below the 0.25 isolevel over the
    central 80 % of the C-alpha extent, so stage 4 will find a pore there.
    """
    result = run_case(
        _case(tmp_path, prepared_2wcd.path),
        store=Store(tmp_path / "store"),
        upto="symmetry",
        write=False,
    )
    seconds = {record.name: record.seconds for record in result.stages}
    logger.info("2WCD stage times: %s s", {name: round(s, 2) for name, s in seconds.items()})
    density_artefact = result.artefacts["density"]
    summary = density_artefact.summary
    assert summary["atoms"]["total"] == 26844  # type: ignore[index]
    assert summary["hydrogens"] == 0
    density = DensityMap.read(density_artefact.payload[DENSITY_PAYLOAD])
    reduced = ReducedMap.read(result.artefacts["symmetry"].payload[REDUCED_PAYLOAD])
    logger.info(
        "2WCD grid %s (z, y, x) at %.3f nm; reduction maxima %s",
        density.grid.shape,
        density.grid.spacing_nm,
        result.artefacts["symmetry"].summary["maximum"],
    )

    values = density.values.astype(np.float64)
    assert np.all(np.isfinite(values))
    assert values.min() >= 0.0
    assert values.max() <= 1.0

    weights = annular_weights(density.grid.half_width, density.grid.spacing_nm)
    binned = reduced.mean @ weights.areas_nm2
    direct = values.sum(axis=(1, 2)) * density.grid.spacing_nm**2
    occupied = direct > 0.0
    relative = np.abs(binned[occupied] - direct[occupied]) / direct[occupied]
    logger.info("conservation: worst relative slice error %.3g", float(relative.max()))
    assert relative.max() <= 1e-9

    excess = float(np.max(reduced.cn_variance - reduced.raw_variance))
    logger.info("Cn variance above the raw variance by at most %.3g", excess)
    assert excess <= 1e-4

    ensemble = AlignedEnsemble.read(result.artefacts["structure"].payload[ENSEMBLE_PAYLOAD])
    ca = ensemble.positions_nm[0][ensemble.name == "CA"].astype(np.float64)
    low, high = float(ca[:, 2].min()), float(ca[:, 2].max())
    margin = 0.1 * (high - low)
    central = (reduced.z_nm >= low + margin) & (reduced.z_nm <= high - margin)
    axis = reduced.mean[central, 0]
    logger.info(
        "axis mean over z in [%.2f, %.2f] nm: at most %.3g",
        low + margin,
        high - margin,
        float(axis.max()),
    )
    assert axis.max() < 0.25


_BUDGET_SCRIPT = """
import json, resource, sys
from nanopnp.io.run import run_case
from nanopnp.io.store import Store
result = run_case(sys.argv[1], store=Store(sys.argv[2]), upto="symmetry", write=False)
print(json.dumps({
    "seconds": {record.name: record.seconds for record in result.stages},
    "peak_rss_GB": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1e6,
    "shape": result.artefacts["density"].summary["grid"]["shape_zyx"],
}))
"""


@pytest.mark.slow
@pytest.mark.skipif(sys.platform == "win32", reason="ru_maxrss is POSIX")
def test_ver49_2wcd_budget(prepared_2wcd: Prepared2WCD, tmp_path: Path) -> None:
    """Record the wall-clock and peak memory of stages 2 and 3 on 2WCD at 0.05 nm.

    In a fresh interpreter, so the peak is the run's own and not this session's.
    Recorded, never gated; the plan predicted at most 60 s and under 1.5 GB
    (Design §5). ``ru_maxrss`` is in kB on Linux.
    """
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            _BUDGET_SCRIPT,
            str(_case(tmp_path, prepared_2wcd.path)),
            str(tmp_path / "store"),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    measured = json.loads(completed.stdout.splitlines()[-1])
    logger.info(
        "2WCD budget: density %.1f s, symmetry %.1f s, peak RSS %.2f GB, grid %s (z, y, x)",
        measured["seconds"]["density"],
        measured["seconds"]["symmetry"],
        measured["peak_rss_GB"],
        measured["shape"],
    )

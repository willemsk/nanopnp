"""FR-30: each notebook runs headless from its README and exits 0."""

from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path

import pytest

from nanopnp.validation.examples import copy_example, run_tagged

pytestmark = pytest.mark.nightly

logger = logging.getLogger(__name__)

REPOSITORY = Path(__file__).resolve().parents[2]
NOTEBOOKS = {
    "01-geometry": "06-pdb-to-mesh",
    "02-charge": "07-pdb-to-charged-run",
    "03-solve": "02-charged-pore",
    "04-sweep": "03-iv-sweep",
}


@pytest.mark.parametrize("notebook", NOTEBOOKS)
def test_notebook_runs_headless(notebook: str, tmp_path: Path) -> None:
    # A cell that raises must fail the run: a stale notebook is the silent failure.
    directory = copy_example(REPOSITORY / "notebooks" / notebook, tmp_path, repository=REPOSITORY)
    # The notebook prepares its own input: the examples it reads sit beside it, as in the repo.
    examples = REPOSITORY / "examples"
    for name in {NOTEBOOKS[notebook], "06-pdb-to-mesh"}:
        shutil.copytree(
            examples / name,
            tmp_path / "examples" / name,
            ignore=shutil.ignore_patterns("*.msh", "store", "*-prepared.pdb"),
            dirs_exist_ok=True,
        )
    structures = Path("tests", "data", "structures")
    (tmp_path / structures).mkdir(parents=True)
    shutil.copy2(REPOSITORY / structures / "2wcd.pdb.gz", tmp_path / structures)
    started = time.perf_counter()
    run_tagged(directory, "run")
    logger.info("notebook %s: %.1f s", notebook, time.perf_counter() - started)

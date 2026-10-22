"""FR-30: each notebook runs headless from its README and exits 0."""

from __future__ import annotations

import logging
import time
from pathlib import Path

import pytest

from nanopnp.validation.examples import copy_example, run_tagged

pytestmark = pytest.mark.nightly

logger = logging.getLogger(__name__)

REPOSITORY = Path(__file__).resolve().parents[2]
NOTEBOOKS = ("01-geometry", "02-charge", "03-solve", "04-sweep")


@pytest.mark.parametrize("notebook", NOTEBOOKS)
def test_notebook_runs_headless(notebook: str, tmp_path: Path) -> None:
    # A cell that raises must fail the run: a stale notebook is the silent failure.
    directory = copy_example(REPOSITORY / "notebooks" / notebook, tmp_path, repository=REPOSITORY)
    started = time.perf_counter()
    run_tagged(directory, "run")
    logger.info("notebook %s: %.1f s", notebook, time.perf_counter() - started)

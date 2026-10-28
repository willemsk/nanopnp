"""FR-30: each notebook runs headless from its README, in place, and exits 0."""

from __future__ import annotations

import logging
import subprocess
import time
from pathlib import Path

import pytest

from nanopnp.validation.examples import run_tagged

pytestmark = pytest.mark.nightly

logger = logging.getLogger(__name__)

REPOSITORY = Path(__file__).resolve().parents[2]
NOTEBOOKS = ("01-geometry", "02-charge", "03-solve", "04-sweep", "05-cylinder", "06-2wcd")


@pytest.fixture(scope="module")
def store(tmp_path_factory: pytest.TempPathFactory) -> Path:
    # One store for the six, as a reader has: the 2WCD notebooks share their walk.
    return tmp_path_factory.mktemp("store")


def _status() -> str:
    return subprocess.run(
        ["git", "status", "--porcelain", "--", "notebooks", "examples"],
        cwd=REPOSITORY,
        capture_output=True,
        text=True,
        check=True,
    ).stdout


@pytest.mark.parametrize("notebook", NOTEBOOKS)
def test_notebook_runs_headless(notebook: str, store: Path) -> None:
    # A cell that raises must fail the run, and a notebook that writes beside itself or into
    # an example fails too: a reader's checkout stays as it was.
    before = _status()
    started = time.perf_counter()
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("NANOPNP_STORE", str(store))
        run_tagged(REPOSITORY / "notebooks" / notebook, "run")
    logger.info("notebook %s: %.1f s", notebook, time.perf_counter() - started)
    assert _status() == before

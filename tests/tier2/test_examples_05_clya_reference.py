"""VER-46 (with FR-23, NUM-11, NUM-26): example 05, one frozen case on the ClyA mesh."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from nanopnp.core.hashing import decode_floats
from nanopnp.post.qoi import ROUTE_AGREEMENT_TOLERANCE
from nanopnp.validation.examples import copy_example, run_tagged

logger = logging.getLogger(__name__)

pytestmark = pytest.mark.slow

REPOSITORY = Path(__file__).resolve().parents[2]


def test_ver46_the_frozen_case_solves_on_the_reference_mesh(tmp_path: Path) -> None:
    example = copy_example(
        REPOSITORY / "examples" / "05-clya-reference", tmp_path, repository=REPOSITORY
    )
    run_tagged(example, "run", timeout_s=7200.0)
    record = decode_floats(json.loads((example / "run" / "run.json").read_text("utf-8")))
    assert isinstance(record, dict)
    quantities = record["quantities"]
    logger.info("example 05 quantities: %s", quantities)
    assert quantities["route_agreement"]["relative_difference"] < ROUTE_AGREEMENT_TOLERANCE

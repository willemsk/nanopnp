"""VER-46 — example 05, one frozen Tier-3 case on the ClyA reference mesh.

``slow``: the solve on the reference mesh takes tens of minutes, so it is recorded and not
gated (VER-46, WP16 D11). Its planning half runs at Tier 1 in
``tests/tier1/test_examples_plan.py``, and the reference generator's output is
gated at Tier 2 by ``test_mesh_generators.py``. The oracle: every command exits 0
and the FR-23 routes agree to the NUM-26 tolerance. Stabilisation is ``none``
(NUM-11).
"""

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
    """Both commands exit 0, and the current routes agree."""
    example = copy_example(
        REPOSITORY / "examples" / "05-clya-reference", tmp_path, repository=REPOSITORY
    )
    # Measured at 2,512 s on one core (WP16 D11 Outcome): twice that, not the default.
    run_tagged(example, "run", timeout_s=7200.0)
    record = decode_floats(json.loads((example / "run" / "run.json").read_text("utf-8")))
    assert isinstance(record, dict)
    quantities = record["quantities"]
    logger.info("example 05 quantities: %s", quantities)
    assert quantities["route_agreement"]["relative_difference"] < ROUTE_AGREEMENT_TOLERANCE

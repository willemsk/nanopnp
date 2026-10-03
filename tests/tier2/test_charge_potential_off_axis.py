"""VER-58 at Tier 2 off the axis: an atom at ``r_i = 1.5`` nm, resolved and unresolved.

The problem, the oracle and the shared work are :mod:`ver58_sphere`'s; the atom on
the axis and the oracle's own test are ``test_charge_potential_axis.py`` (WP33 D4).
The unresolved atom is solved on the 0.1 nm level's mesh, which the convergence
test has already built in this process.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Iterator

import pytest
from ver58_sphere import errors_and_rates, release, solve_error

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module", autouse=True)
def _released() -> Iterator[None]:
    """Release :mod:`ver58_sphere`'s caches once this file's tests are done."""
    yield
    release()


def test_ver58_deposited_potential_converges_at_the_potentials_own_rate_off_the_axis() -> None:
    """The P2 deposit's potential error falls at >= 2.5 between the finest two meshes; P0's at 2."""
    errors, rates = errors_and_rates(1.5, logger)
    assert rates[2][-1] >= 2.5
    assert rates[0][-1] < rates[2][-1]
    assert errors[2][-1] < errors[0][-1]


def test_ver58_an_unresolved_atom_is_recorded_beside_p0() -> None:
    """Recorded: a CHARMM polar hydrogen on 0.1 nm elements, the error at >= 1 nm from it."""
    width = 0.0112
    found = {}
    for order in (2, 0):
        error, _, elements = solve_error(1.5, width, 0.1, order, beyond_nm=1.0)
        found[order] = error
        logger.info(
            "VER-58 unresolved atom (w = %.4f nm) on 0.1 nm elements (%d), P%d deposit: L2(r) "
            "error at >= 1 nm from it %.3e",
            width,
            elements,
            order,
            error,
        )
    assert all(math.isfinite(value) for value in found.values())

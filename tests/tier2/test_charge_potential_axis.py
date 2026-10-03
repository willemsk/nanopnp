"""VER-58 at Tier 2 on the axis: the closed form, and an atom at ``r_i = 0`` deposited and solved.

The problem, the oracle and the shared work are :mod:`ver58_sphere`'s; the atom
off the axis is ``test_charge_potential_off_axis.py`` (WP33 D4).
"""

from __future__ import annotations

import logging
import math
from collections.abc import Iterator

import numpy as np
import pytest
from ver58_sphere import (
    SPHERE_NM,
    WIDTH_NM,
    Z_ATOM_NM,
    errors_and_rates,
    exact_potential_V,
    release,
)

from nanopnp.core.constants import ELEMENTARY_CHARGE, VACUUM_PERMITTIVITY

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module", autouse=True)
def _released() -> Iterator[None]:
    """Release :mod:`ver58_sphere`'s caches once this file's tests are done."""
    yield
    release()


def test_ver58_the_closed_form_vanishes_on_the_sphere() -> None:
    """The oracle first: the potential is zero on the grounded sphere, to 1e-17 of its peak."""
    eps = VACUUM_PERMITTIVITY * 78.15
    for r_i in (0.0, 1.5):
        angles = np.linspace(-0.5 * math.pi, 0.5 * math.pi, 41)
        on_sphere = exact_potential_V(
            SPHERE_NM * np.cos(angles), SPHERE_NM * np.sin(angles), r_i, Z_ATOM_NM, WIDTH_NM, eps
        )
        peak = float(
            exact_potential_V(
                np.array([r_i]), np.array([Z_ATOM_NM]), r_i, Z_ATOM_NM, WIDTH_NM, eps
            )[0]
        )
        assert np.max(np.abs(on_sphere)) <= 1e-12 * abs(peak)
    # On the axis every ring point is equidistant: the closed form's own special case.
    rho = math.hypot(1.5, 2.0 - Z_ATOM_NM) * 1e-9
    a = math.hypot(1.5, Z_ATOM_NM)
    scale = SPHERE_NM**2 / a**2
    rho_image = math.hypot(scale * 1.5, 2.0 - scale * Z_ATOM_NM) * 1e-9
    axis = (
        ELEMENTARY_CHARGE
        / (4 * math.pi * eps)
        * (math.erf(rho / (WIDTH_NM * 1e-9)) / rho - SPHERE_NM / a / rho_image)
    )
    found = exact_potential_V(np.array([0.0]), np.array([2.0]), 1.5, Z_ATOM_NM, WIDTH_NM, eps)
    assert float(found[0]) == pytest.approx(axis, rel=1e-13)


def test_ver58_deposited_potential_converges_at_the_potentials_own_rate_on_the_axis() -> None:
    """The P2 deposit's potential error falls at >= 2.5 between the finest two meshes; P0's at 2."""
    errors, rates = errors_and_rates(0.0, logger)
    assert rates[2][-1] >= 2.5
    assert rates[0][-1] < rates[2][-1]
    assert errors[2][-1] < errors[0][-1]

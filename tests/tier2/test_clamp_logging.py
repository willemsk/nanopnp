"""PHY-13 (with NUM-17): a high-salt solve logs the clamp; a solve in range stays silent."""

import logging

import pytest

from nanopnp.mesh.primitives import CylindricalPoreGeometry
from nanopnp.numerics.measures import AXISYMMETRIC
from nanopnp.physics import models
from nanopnp.post import qoi

PORE = CylindricalPoreGeometry(
    pore_radius_nm=2.0, membrane_thickness_nm=13.0, reservoir_radius_nm=25.0
)

HIGH_SALT_M = 5.4

WITHIN_RANGE_M = 1.0

MEMBRANE_PERMITTIVITY = {"membrane": 2.0}


def _converged(concentration_M: float) -> models.ModelSolution:
    mesh = PORE.generate(maxh_nm=6.0, wall_h_nm=0.6)
    model = models.create(
        "pnp",
        classical=True,
        concentration_M=concentration_M,
        solid_permittivities=MEMBRANE_PERMITTIVITY,
    )
    return model.solve(mesh, AXISYMMETRIC)


def test_phy13_a_high_salt_solve_logs_the_clamp(caplog: pytest.LogCaptureFixture) -> None:
    solution = _converged(HIGH_SALT_M)
    with caplog.at_level(logging.WARNING, logger="nanopnp.materials.electrolyte"):
        count = qoi.report_clamp_activations(solution, AXISYMMETRIC)
    assert count > 0, "a uniform 5.4 M solve is past the 5.3 M fit limit at every node"
    assert "concentration correction clamped" in caplog.text
    assert "worst at" in caplog.text, "PHY-13 requires the activation's location"
    assert "concentration" in caplog.text


def test_phy13_a_solve_within_the_fit_range_stays_silent(
    caplog: pytest.LogCaptureFixture,
) -> None:
    solution = _converged(WITHIN_RANGE_M)
    with caplog.at_level(logging.WARNING, logger="nanopnp.materials.electrolyte"):
        count = qoi.report_clamp_activations(solution, AXISYMMETRIC)
    assert count == 0
    assert "clamped" not in caplog.text

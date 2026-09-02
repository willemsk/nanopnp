"""PHY-13: a high-salt solve emits the clamp record the requirement asks for.

The concentration fits hold to 5.3 M for NaCl; above it every property is capped
at its value there by clamping the correction driver. That clamp is silent inside
the symbolic solve — the driver is clamped *before* the average is taken, so it
can never report the extrapolation itself — which ``.knowledge/01`` §3 names as a
plausible source of confusion. PHY-13 requires the extrapolation to be logged
with its location and property; :func:`nanopnp.post.qoi.report_clamp_activations`
is where the solve/extract path discharges it, over the converged concentrations
sampled on the fluid nodal set, exactly as the NUM-17 gates sample.

Both directions are asserted: a solve above the cap must emit the record, and one
comfortably inside the fit range must stay silent. Without the second half a
diagnostic that fired unconditionally would pass the first.
"""

import logging

import pytest

from nanopnp.mesh.primitives import CylindricalPoreGeometry
from nanopnp.physics import models
from nanopnp.physics.measures import AXISYMMETRIC
from nanopnp.post import qoi

PORE = CylindricalPoreGeometry(
    pore_radius_nm=2.0, membrane_thickness_nm=13.0, reservoir_radius_nm=25.0
)
"""A coarse pore: nothing is compared against a closed form here, so the mesh is
sized only for the trivial uniform solves below to converge."""

HIGH_SALT_M = 5.4
"""Bulk above the 5.3 M NaCl fit limit, so every fluid node extrapolates the fits."""

WITHIN_RANGE_M = 1.0
"""Bulk comfortably inside the fit range, where nothing should be clamped."""

MEMBRANE_PERMITTIVITY = {"membrane": 2.0}


def _converged(concentration_M: float) -> models.ModelSolution:
    """Return a classical PNP solution at a uniform bulk, zero bias and no charge.

    The cold state — bulk ions, zero potential — already solves this problem, so
    Newton converges at once; the point is a genuine converged field to sample,
    not a hard operating point. Classical rather than corrected because the clamp
    record is about the concentration validity range, not about whether a wall
    correction reads the driver, and a classical solve needs no distance field.
    """
    mesh = PORE.generate(maxh_nm=6.0, wall_h_nm=0.6)
    model = models.create(
        "pnp",
        classical=True,
        concentration_M=concentration_M,
        solid_permittivities=MEMBRANE_PERMITTIVITY,
    )
    return model.solve(mesh, AXISYMMETRIC)


def test_phy13_a_high_salt_solve_logs_the_clamp(caplog: pytest.LogCaptureFixture) -> None:
    """A converged solve above the fit limit emits the located clamp record (PHY-13)."""
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
    """A solve inside the validity range clamps nothing, so the record is empty."""
    solution = _converged(WITHIN_RANGE_M)
    with caplog.at_level(logging.WARNING, logger="nanopnp.materials.electrolyte"):
        count = qoi.report_clamp_activations(solution, AXISYMMETRIC)
    assert count == 0
    assert "clamped" not in caplog.text

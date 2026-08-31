"""The NUM-24 domain indicator: its shape, its orientation and the ``2 pi``.

The indicator is the whole content of NUM-24's claim to cross-section
independence, and everything that can go wrong with it is silent. An inverted
band flips the sign of every current; a band outside the domain makes
``grad(psi)`` vanish and every current zero; a band with no width makes
``grad(psi)`` a delta no quadrature rule can see. Each of those is checked here
rather than discovered in a benchmark, where it would look like a modelling
difference.
"""

import math

import ngsolve as ngs
import pytest

from nanopnp.mesh.primitives import CylindricalPoreGeometry
from nanopnp.physics.measures import AXISYMMETRIC
from nanopnp.post.indicator import (
    IndicatorError,
    axial_indicator,
    check_indicator,
    lumen_band,
    smoothstep,
)
from nanopnp.post.qoi import TWO_PI

LOWER_NM = -2.0
UPPER_NM = 2.0

PORE = CylindricalPoreGeometry(
    pore_radius_nm=2.0, membrane_thickness_nm=6.0, reservoir_radius_nm=10.0
)
"""A small pore; nothing here is solved on it, only interpolated."""


@pytest.fixture(scope="module")
def mesh() -> ngs.Mesh:
    """Return a coarse mesh of the pore; nothing is solved on it, only interpolated."""
    return PORE.generate(maxh_nm=2.0)


def _at(expression: ngs.CoefficientFunction, mesh: ngs.Mesh, r: float, z: float) -> float:
    """Evaluate a coefficient function at one point of the half-plane."""
    return float(expression(mesh(r, z)))


@pytest.mark.parametrize(
    ("z", "expected"),
    [(-5.0, 0.0), (LOWER_NM, 0.0), (0.0, 0.5), (UPPER_NM, 1.0), (5.0, 1.0)],
)
def test_num24_smoothstep_runs_from_zero_to_one_across_the_band(
    mesh: ngs.Mesh, z: float, expected: float
) -> None:
    """``S(0) = 0``, ``S(1/2) = 1/2``, ``S(1) = 1``, and it is clamped outside."""
    step = smoothstep(ngs.y, lower_nm=LOWER_NM, upper_nm=UPPER_NM)
    assert _at(step, mesh, 1.0, z) == pytest.approx(expected, abs=1e-12)


def test_num24_smoothstep_has_vanishing_slope_at_both_ends(mesh: ngs.Mesh) -> None:
    """``S'(0) = S'(1) = 0``, which is why the step is cubic and not linear.

    A linear ramp leaves ``grad(psi)`` discontinuous at both ends of the band, so
    the integrand has a jump inside an element and the quadrature resolves it
    only by accident. The C1 step removes the jump, and with it the dependence of
    the answer on where the band ends fall relative to the mesh.
    """
    step = smoothstep(ngs.y, lower_nm=LOWER_NM, upper_nm=UPPER_NM)
    slope = step.Diff(ngs.y)
    for z in (LOWER_NM, UPPER_NM):
        assert _at(slope, mesh, 1.0, z) == pytest.approx(0.0, abs=1e-12)
    # ... and it is not identically zero: the maximum slope of S is 3/2 per unit
    # of the scaled coordinate, so 1.5 / width here.
    assert _at(slope, mesh, 1.0, 0.0) == pytest.approx(1.5 / (UPPER_NM - LOWER_NM), rel=1e-12)


def test_num24_a_zero_width_band_is_refused(mesh: ngs.Mesh) -> None:
    """A step with no transition has a delta gradient and integrates to nothing."""
    with pytest.raises(IndicatorError, match="positive width"):
        smoothstep(ngs.y, lower_nm=1.0, upper_nm=1.0)


def test_num24_indicator_is_one_on_cis_and_zero_on_trans(mesh: ngs.Mesh) -> None:
    """``cis`` is at ``+z``, so ``psi`` increases with ``z`` (the sign convention)."""
    lower, upper = lumen_band(PORE)
    indicator = axial_indicator(mesh, lower_nm=lower, upper_nm=upper)
    check_indicator(indicator, mesh)
    # Orientation, not precision: on this deliberately coarse mesh the
    # interpolation of the step leaks a fraction of a per cent past the band.
    assert _at(indicator, mesh, 0.5, PORE.half_thickness_nm + 1.0) > 0.99
    assert _at(indicator, mesh, 0.5, -PORE.half_thickness_nm - 1.0) < 0.01


def test_num24_an_inverted_band_fails_loudly(mesh: ngs.Mesh) -> None:
    """A ``psi`` that decreases towards cis flips the sign of every current.

    Built here the way a miswiring would produce it — ``1 - S`` rather than
    ``S`` — because :func:`axial_indicator` cannot be asked for it directly.
    """
    lower, upper = lumen_band(PORE)
    inverted = ngs.GridFunction(ngs.H1(mesh, order=2), name="psi")
    inverted.Set(1.0 - smoothstep(ngs.y, lower_nm=lower, upper_nm=upper))
    with pytest.raises(IndicatorError, match="inverted band"):
        check_indicator(inverted, mesh)


def test_num24_a_band_outside_the_domain_fails_loudly(mesh: ngs.Mesh) -> None:
    """``grad(psi) = 0`` everywhere gives every current as zero, plausibly."""
    far = PORE.reservoir_radius_nm * 10.0
    indicator = axial_indicator(mesh, lower_nm=far, upper_nm=far + 1.0)
    with pytest.raises(IndicatorError, match="psi must be 1"):
        check_indicator(indicator, mesh)


def test_num24_check_indicator_names_the_boundaries_the_mesh_has(mesh: ngs.Mesh) -> None:
    """A mistyped boundary name is a typo, not a physics result."""
    lower, upper = lumen_band(PORE)
    indicator = axial_indicator(mesh, lower_nm=lower, upper_nm=upper)
    with pytest.raises(IndicatorError, match="no boundary matching"):
        check_indicator(indicator, mesh, cis="top")


def test_num24_lumen_band_stays_inside_the_lumen() -> None:
    """The default band is centred on the membrane and away from both mouths."""
    lower, upper = lumen_band(PORE)
    assert -PORE.half_thickness_nm < lower < 0.0 < upper < PORE.half_thickness_nm
    assert lower == pytest.approx(-upper)


@pytest.mark.parametrize("fraction", [0.0, -0.1, 1.5])
def test_num24_lumen_band_rejects_a_fraction_outside_the_lumen(fraction: float) -> None:
    """A band wider than the lumen would put ``grad(psi)`` in the reservoir."""
    with pytest.raises(IndicatorError, match=r"\(0, 1\]"):
        lumen_band(PORE, fraction=fraction)


def test_num27_the_two_pi_convention_makes_an_integral_three_dimensional(
    mesh: ngs.Mesh,
) -> None:
    """``2 pi int f r dr dz`` is the volume integral; ``Measures`` returns the rest.

    This is the convention NUM-27's NOTE requires to be stated: the ``2 pi``
    cancels from both sides of the weak form and is restored exactly once, in
    ``post/qoi.py``. Integrating 1 over the trans reservoir must therefore give
    its volume — half a sphere of the reservoir radius — and not that over
    ``2 pi``.
    """
    volume = TWO_PI * AXISYMMETRIC.integrate(ngs.CF(1.0), mesh, definedon=mesh.Materials("trans"))
    hemisphere = 2.0 / 3.0 * math.pi * PORE.reservoir_radius_nm**3
    assert volume == pytest.approx(hemisphere, rel=0.02)

"""NUM-24, NUM-27: the domain indicator's shape, orientation and the ``2 pi`` convention."""

import math

import ngsolve as ngs
import pytest

from nanopnp.mesh.primitives import CylindricalPoreGeometry
from nanopnp.numerics.measures import AXISYMMETRIC
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
    return PORE.generate(maxh_nm=2.0)


def _at(expression: ngs.CoefficientFunction, mesh: ngs.Mesh, r: float, z: float) -> float:
    return float(expression(mesh(r, z)))


@pytest.mark.parametrize(
    ("z", "expected"),
    [(-5.0, 0.0), (LOWER_NM, 0.0), (0.0, 0.5), (UPPER_NM, 1.0), (5.0, 1.0)],
)
def test_num24_smoothstep_runs_from_zero_to_one_across_the_band(
    mesh: ngs.Mesh, z: float, expected: float
) -> None:
    step = smoothstep(ngs.y, lower_nm=LOWER_NM, upper_nm=UPPER_NM)
    assert _at(step, mesh, 1.0, z) == pytest.approx(expected, abs=1e-12)


def test_num24_smoothstep_has_vanishing_slope_at_both_ends(mesh: ngs.Mesh) -> None:
    step = smoothstep(ngs.y, lower_nm=LOWER_NM, upper_nm=UPPER_NM)
    slope = step.Diff(ngs.y)
    for z in (LOWER_NM, UPPER_NM):
        assert _at(slope, mesh, 1.0, z) == pytest.approx(0.0, abs=1e-12)
    assert _at(slope, mesh, 1.0, 0.0) == pytest.approx(1.5 / (UPPER_NM - LOWER_NM), rel=1e-12)


def test_num24_a_zero_width_band_is_refused(mesh: ngs.Mesh) -> None:
    with pytest.raises(IndicatorError, match="positive width"):
        smoothstep(ngs.y, lower_nm=1.0, upper_nm=1.0)


def test_num24_indicator_is_one_on_cis_and_zero_on_trans(mesh: ngs.Mesh) -> None:
    lower, upper = lumen_band(PORE)
    indicator = axial_indicator(mesh, lower_nm=lower, upper_nm=upper)
    check_indicator(indicator, mesh)
    assert 0.99 < _at(indicator, mesh, 0.5, PORE.half_thickness_nm + 1.0) < 1.0
    assert 0.0 < _at(indicator, mesh, 0.5, -PORE.half_thickness_nm - 1.0) < 0.01


def test_num24_an_inverted_band_fails_loudly(mesh: ngs.Mesh) -> None:
    from nanopnp.mesh.primitives import ELECTROLYTE_DOMAINS

    lower, upper = lumen_band(PORE)
    space = ngs.H1(mesh, order=2, definedon=mesh.Materials(ELECTROLYTE_DOMAINS))
    inverted = ngs.GridFunction(space, name="psi")
    inverted.Set(1.0 - smoothstep(ngs.y, lower_nm=lower, upper_nm=upper))
    with pytest.raises(IndicatorError, match="inverted band"):
        check_indicator(inverted, mesh)


def test_num24_a_band_outside_the_domain_fails_loudly(mesh: ngs.Mesh) -> None:
    far = PORE.reservoir_radius_nm * 10.0
    with pytest.raises(IndicatorError, match="psi must be 1"):
        axial_indicator(mesh, lower_nm=far, upper_nm=far + 1.0)


# NUM-25, VER-11
def test_num24_the_indicator_is_built_on_the_fluid_and_that_is_load_bearing(
    mesh: ngs.Mesh,
) -> None:
    lower, upper = lumen_band(PORE)
    over_the_solid = axial_indicator(mesh, lower_nm=lower, upper_nm=upper, fluid=None, check=False)
    with pytest.raises(IndicatorError, match="psi must be 1"):
        check_indicator(over_the_solid, mesh)

    on_the_fluid = axial_indicator(mesh, lower_nm=lower, upper_nm=upper)
    check_indicator(on_the_fluid, mesh)
    trans_dofs = on_the_fluid.space.GetDofs(mesh.Boundaries("trans"))
    leak = max(
        abs(on_the_fluid.vec[index])
        for index in range(on_the_fluid.space.ndof)
        if trans_dofs[index]
    )
    assert leak == 0.0, f"psi must vanish identically on the trans electrode, got {leak:.3e}"


def test_num24_check_indicator_names_the_boundaries_the_mesh_has(mesh: ngs.Mesh) -> None:
    lower, upper = lumen_band(PORE)
    indicator = axial_indicator(mesh, lower_nm=lower, upper_nm=upper)
    with pytest.raises(IndicatorError, match="no boundary matching"):
        check_indicator(indicator, mesh, cis="top")


def test_num24_lumen_band_stays_inside_the_lumen() -> None:
    lower, upper = lumen_band(PORE)
    assert -PORE.half_thickness_nm < lower < 0.0 < upper < PORE.half_thickness_nm
    assert lower == pytest.approx(-upper)


@pytest.mark.parametrize("fraction", [0.0, -0.1, 1.5])
def test_num24_lumen_band_rejects_a_fraction_outside_the_lumen(fraction: float) -> None:
    with pytest.raises(IndicatorError, match=r"\(0, 1\]"):
        lumen_band(PORE, fraction=fraction)


def test_num27_the_two_pi_convention_makes_an_integral_three_dimensional(
    mesh: ngs.Mesh,
) -> None:
    volume = TWO_PI * AXISYMMETRIC.integrate(ngs.CF(1.0), mesh, definedon=mesh.Materials("trans"))
    hemisphere = 2.0 / 3.0 * math.pi * PORE.reservoir_radius_nm**3
    assert volume == pytest.approx(hemisphere, rel=0.02)

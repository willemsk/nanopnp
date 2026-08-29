"""VER-06: the wall-distance field is smooth, vanishes on the wall, and ignores the membrane."""

import numpy as np
import pytest

from nanopnp.mesh.distance import gradient_jump, mollify, wall_distance
from nanopnp.mesh.primitives import CylinderGeometry, CylindricalPoreGeometry

ACCURACY_TOL_NM = 5e-3
"""Stated tolerance on d within the range where the wall corrections vary."""

JUMP_TOL = 1e-2
"""Stated C1 tolerance: the normalised facet jump of grad(d) (NUM-31)."""


@pytest.fixture(scope="module")
def cylinder():
    """Return a cylinder mesh, where the exact distance is a - r."""
    return CylinderGeometry(radius_nm=2.0, length_nm=4.0).generate(maxh_nm=0.1)


def test_ver06_distance_matches_the_exact_field_near_the_wall(cylinder) -> None:
    """The distance reproduces a - r, over the range where f^w actually varies."""
    distance = wall_distance(cylinder, "wall")
    # 0.5 nm is the innermost radius of the 1.5 nm band where f^w still varies.
    radii = np.linspace(0.5, 2.0, 61)
    errors = [abs(distance(cylinder(float(r), 2.0)) - (2.0 - r)) for r in radii]
    assert max(errors) < ACCURACY_TOL_NM


def test_ver06_distance_vanishes_on_the_wall_and_is_never_negative(cylinder) -> None:
    """PHY-02: the field vanishes on the pore boundary.

    A slightly negative d would shift the ion wall function at the wall by
    percent - f^w_D(0) = 0.0601 is itself only 6 % of its bulk value - so the
    constrained degrees of freedom are zeroed rather than left to the projection.
    """
    distance = wall_distance(cylinder, "wall")
    assert distance(cylinder(2.0, 2.0)) == 0.0
    sampled = [distance(cylinder(float(r), 2.0)) for r in np.linspace(0.0, 2.0, 81)]
    assert min(sampled) >= 0.0


def test_ver06_gradient_is_continuous_to_the_stated_tolerance(cylinder) -> None:
    """The mollified field has a small facet jump; a kinked d enters the Jacobian."""
    distance = wall_distance(cylinder, "wall")
    jump = gradient_jump(distance)
    assert jump < JUMP_TOL, f"normalised gradient jump {jump:.4f} exceeds {JUMP_TOL}"


def test_ver06_further_mollification_reduces_the_jump(cylinder) -> None:
    """The smoothing pass does what it claims, so it is worth having on a real mesh."""
    distance = wall_distance(cylinder, "wall", diffusion_length_nm=0.1)
    smoothed = mollify(distance, 0.2, sources="wall")
    assert gradient_jump(smoothed) < gradient_jump(distance)


def test_ver06_membrane_is_not_a_distance_source() -> None:
    """PHY-02: the bilayer is excluded from the source set, deliberately.

    Including it would be a model change, not an improvement: electrolyte
    properties near the membrane do not affect the pore's figures of merit, and
    the reference model measured from the pore boundaries only.
    """
    mesh = CylindricalPoreGeometry(
        pore_radius_nm=2.0, membrane_thickness_nm=13.0, reservoir_radius_nm=30.0
    ).generate(maxh_nm=2.0, wall_h_nm=0.15)
    distance = wall_distance(mesh, "wall")

    at_pore_wall = distance(mesh(1.9, 0.0))
    just_above_membrane = distance(mesh(10.0, 6.6))
    assert at_pore_wall == pytest.approx(0.1, abs=2e-2)
    assert just_above_membrane > 1.0, (
        "a point 0.1 nm above the membrane is far from the pore; a small distance "
        "there means the membrane leaked into the source set"
    )


def test_missing_source_boundary_fails_loudly(cylinder) -> None:
    with pytest.raises(ValueError, match="no boundary matching 'pore'"):
        wall_distance(cylinder, "pore")

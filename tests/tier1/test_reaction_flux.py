"""The NUM-25 machinery the force routes borrow: a vector boundary indicator.

The scalar reaction flux is exercised end to end by VER-11 in
``tests/tier2/test_current_routes.py``. What is new here is the vector case: the
axial reaction force of NUM-28 pairs the momentum residual with ``e_z`` on the
analyte's no-slip surface, and ``ngsolve.CF(1.0)`` cannot fill a ``VectorH1``
block at all. These tests pin the interpolation, not the physics.
"""

import ngsolve as ngs
import pytest

from nanopnp.mesh.primitives import CylinderGeometry
from nanopnp.post.reaction_flux import boundary_indicator


@pytest.fixture(scope="module")
def mesh() -> ngs.Mesh:
    """Return a cylinder, whose ``wall`` boundary the indicator is built on."""
    return CylinderGeometry(radius_nm=1.0, length_nm=2.0).generate(maxh_nm=0.25)


def _boundary_mean(field: ngs.CF, mesh: ngs.Mesh, boundary: str) -> float:
    """Return the mean of ``field`` over a boundary, unweighted by ``r``."""
    region = mesh.Boundaries(boundary)
    length = float(ngs.Integrate(ngs.CF(1.0), mesh, definedon=region))
    return float(ngs.Integrate(field, mesh, definedon=region)) / length


def test_num25_vector_indicator_is_the_axial_unit_vector_on_its_boundary(
    mesh: ngs.Mesh,
) -> None:
    """``value=(0, 1)`` interpolates to ``e_z`` on the boundary and to zero off it.

    Exactness matters for the same reason it does for the scalar indicator: the
    residual pairing is the boundary traction only insofar as the test function
    really is the constant it claims to be, and the hierarchical basis makes
    "set the boundary dofs to 1" give 11/12 of that.
    """
    space = ngs.VectorH1(mesh, order=2, dirichlet="wall")
    indicator = boundary_indicator(space, "wall", value=(0.0, 1.0))
    assert _boundary_mean((indicator[0] - 0.0) ** 2, mesh, "wall") == pytest.approx(0.0, abs=1e-24)
    assert _boundary_mean((indicator[1] - 1.0) ** 2, mesh, "wall") == pytest.approx(0.0, abs=1e-24)
    # ``axis`` shares no vertex with ``wall``, so the indicator is exactly zero
    # there. The ``end`` boundaries do share their corner dofs with it and are
    # not zero near them, which is the interpolation working as intended.
    assert _boundary_mean(indicator * indicator, mesh, "axis") == pytest.approx(0.0, abs=1e-24)


def test_num25_scalar_indicator_is_unchanged_by_the_new_argument(mesh: ngs.Mesh) -> None:
    """The default is still 1, so every existing NUM-25 current is untouched."""
    space = ngs.H1(mesh, order=2, dirichlet="wall")
    assert _boundary_mean(
        (boundary_indicator(space, "wall") - 1.0) ** 2, mesh, "wall"
    ) == pytest.approx(0.0, abs=1e-24)


def test_num25_vector_indicator_selects_one_block_of_a_product_space(mesh: ngs.Mesh) -> None:
    """On a product space the vector value fills its own block and leaves the rest at zero.

    That is what makes the pairing pick the *momentum* residual rather than the
    sum over every equation, exactly as ``component`` does for the currents.
    """
    scalar = ngs.H1(mesh, order=2, dirichlet="wall")
    vector = ngs.VectorH1(mesh, order=2, dirichlet="wall")
    product = scalar * vector
    indicator = boundary_indicator(product, "wall", component=1, value=(0.0, 1.0))
    potential, velocity = indicator.components
    assert _boundary_mean(potential**2, mesh, "wall") == pytest.approx(0.0, abs=1e-24)
    assert _boundary_mean((velocity[1] - 1.0) ** 2, mesh, "wall") == pytest.approx(0.0, abs=1e-24)

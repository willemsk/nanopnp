"""NUM-16: Newton's convergence test holds every field to the tolerance."""

from __future__ import annotations

LARGE = 1.0e3

SMALL = 0.1


def test_num16_every_field_is_relatively_converged_when_the_solve_closes() -> None:
    import ngsolve as ngs
    import numpy as np
    from netgen.geom2d import unit_square

    from nanopnp.numerics.newton import DEFAULT_SETTINGS, damped_newton

    mesh = ngs.Mesh(unit_square.GenerateMesh(maxh=0.5))
    space = ngs.H1(mesh, order=1) * ngs.H1(mesh, order=1)
    (u, v), (w, z) = space.TnT()
    residual = ngs.BilinearForm(space)
    residual += (u - LARGE) * w * ngs.dx + (v * v - SMALL * SMALL) * z * ngs.dx
    solution = ngs.GridFunction(space)
    solution.components[1].Set(1.0)

    result = damped_newton(residual, solution)

    assert result.converged
    rtol = DEFAULT_SETTINGS.relative_tolerance
    large = np.asarray(solution.components[0].vec.FV().NumPy())
    small = np.asarray(solution.components[1].vec.FV().NumPy())
    assert np.max(np.abs(large - LARGE)) / LARGE <= rtol
    assert np.max(np.abs(small - SMALL)) / SMALL <= rtol
    last = result.history[-1]
    assert not last.forced
    assert last.update <= rtol


def test_num16_a_field_whose_root_is_zero_converges_against_the_floor() -> None:
    import ngsolve as ngs
    import numpy as np
    from netgen.geom2d import unit_square

    from nanopnp.numerics.newton import DEFAULT_SETTINGS, damped_newton

    mesh = ngs.Mesh(unit_square.GenerateMesh(maxh=0.5))
    space = ngs.H1(mesh, order=1) * ngs.H1(mesh, order=1)
    (u, v), (w, z) = space.TnT()
    residual = ngs.BilinearForm(space)
    residual += (u * u - LARGE * LARGE) * w * ngs.dx + v * z * ngs.dx
    solution = ngs.GridFunction(space)
    solution.components[0].Set(0.5 * LARGE)
    solution.components[1].Set(0.0)

    result = damped_newton(residual, solution)

    assert result.converged
    rtol = DEFAULT_SETTINGS.relative_tolerance
    large = np.asarray(solution.components[0].vec.FV().NumPy())
    small = np.asarray(solution.components[1].vec.FV().NumPy())
    assert np.max(np.abs(large - LARGE)) / LARGE <= rtol
    assert np.max(np.abs(small)) <= rtol
    last = result.history[-1]
    assert not last.forced
    assert last.update <= rtol


# NUM-18
def test_num16_a_warm_start_onto_its_own_state_closes_in_one_step() -> None:
    import ngsolve as ngs
    from netgen.geom2d import unit_square

    from nanopnp.numerics.newton import NewtonSettings, damped_newton

    mesh = ngs.Mesh(unit_square.GenerateMesh(maxh=0.5))
    space = ngs.H1(mesh, order=1) * ngs.H1(mesh, order=1)
    (u, v), (w, z) = space.TnT()
    residual = ngs.BilinearForm(space)
    residual += (u - LARGE) * w * ngs.dx + (v * v - SMALL * SMALL) * z * ngs.dx
    solution = ngs.GridFunction(space)
    solution.components[1].Set(1.0)

    settings = NewtonSettings(absolute_tolerance=1.0e-18)
    first = damped_newton(residual, solution, settings=settings)
    assert first.converged

    second = damped_newton(residual, solution, settings=settings)
    assert second.converged
    assert second.iterations == 1
    assert not second.history[-1].forced
    assert second.history[-1].update <= settings.relative_tolerance


def test_num16_field_floor_ratio_validation() -> None:
    import pytest

    from nanopnp.numerics.newton import NewtonSettings

    with pytest.raises(ValueError, match="field_floor_ratio must be positive"):
        NewtonSettings(field_floor_ratio=0.0)
    with pytest.raises(ValueError, match="field_floor_ratio must be positive"):
        NewtonSettings(field_floor_ratio=-1.0e-6)
    # NaN passes a ``<= 0`` test, and an infinite floor makes every update zero.
    with pytest.raises(ValueError, match="field_floor_ratio must be positive and finite"):
        NewtonSettings(field_floor_ratio=float("nan"))
    with pytest.raises(ValueError, match="field_floor_ratio must be positive and finite"):
        NewtonSettings(field_floor_ratio=float("inf"))


def test_num16_a_nan_field_update_is_never_dropped_from_the_maximum() -> None:
    import math

    from nanopnp.numerics.newton import _largest_update

    assert _largest_update([1.0e-9, 3.0e-7]) == 3.0e-7
    assert math.isnan(_largest_update([1.0e-9, float("nan")]))
    assert math.isnan(_largest_update([float("nan"), 1.0e-9]))

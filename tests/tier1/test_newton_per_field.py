"""NUM-16 (WP41 D4) — Newton's convergence test holds every field to the tolerance.

One norm over all fields is dominated by the largest. On example 03's sweep a rung
closed by the residual test, ``‖R‖ ≤ rtol ‖R₀‖``, with the velocity 8.2e-6 and the
pressure 2.0e-6 relatively unconverged while the ions were at 2e-8 and the global
relative update at 9e-9 (WP41 *Design* §2). The constructed problem here has the
same shape: a large linear block that converges in one undamped step, and a small
nonlinear block that the one norm cannot see.
"""

from __future__ import annotations

LARGE = 1.0e3
"""Block A's root: it dominates every norm taken over both blocks."""

SMALL = 0.1
"""Block B's root, ``v² = SMALL²``: four decades below block A in norm."""


def test_num16_every_field_is_relatively_converged_when_the_solve_closes() -> None:
    """Both blocks end within the relative tolerance of their own roots.

    Today the residual test closes the solve once block A has converged, because
    block B's residual is a small share of the entry residual; block B is then
    left far from its root in its own terms. The per-field update test keeps
    iterating until block B's own relative update is below the tolerance.
    """
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
    # The recorded update is the largest per-field ratio, the number the test read.
    assert last.update <= rtol


def test_num16_a_field_whose_root_is_zero_converges_against_the_floor() -> None:
    """A field whose root is zero converges against the per-field floor.

    A field that is identically zero (such as velocity in an uncharged pore or
    potential at zero bias) has norm zero. The per-field floor
    rho * max(‖u‖, reference_norm) prevents division by zero and tests that
    field's update against the floor rather than an empty norm.
    """
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


def test_num16_a_warm_start_onto_its_own_state_closes_in_one_step() -> None:
    """A warm start onto an already converged state closes in one step.

    When the transferred state is already converged and above the absolute
    residual floor, damped Newton evaluates the undamped direction, finds the
    relative update within tolerance, and closes at step 1 (NUM-16, NUM-18).
    """
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

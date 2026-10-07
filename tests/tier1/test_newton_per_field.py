"""NUM-16 (WP41 D4) — Newton's convergence test holds every field to the tolerance.

One norm over all fields is dominated by the largest. On example 03's sweep a rung
closed by the residual test, ``‖R‖ ≤ rtol ‖R₀‖``, with the velocity 8.2e-6 and the
pressure 2.0e-6 relatively unconverged while the ions were at 2e-8 and the global
relative update at 9e-9 (WP41 *Design* §2). The constructed problem here has the
same shape: a large linear block that converges in one undamped step, and a small
nonlinear block that the one norm cannot see.
"""

from __future__ import annotations

import pytest

LARGE = 1.0e3
"""Block A's root: it dominates every norm taken over both blocks."""

SMALL = 0.1
"""Block B's root, ``v² = SMALL²``: four decades below block A in norm."""


@pytest.mark.xfail(strict=True, reason="planned: WP41 D4")
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

"""Canonical solver defaults read outside the case schema (the damped-Newton settings)."""

from __future__ import annotations

from typing import Final

# NUM-16 reference damped-Newton settings. The case schema's other defaults (elements,
# linear solver, continuation, stabilisation, wall distance) live in io/case.py and
# io/defaults.py, which test_defaults.py holds equal.
DEFAULT_NONLINEAR_RTOL: Final[float] = 1.0e-6
DEFAULT_NONLINEAR_MAX_ITER: Final[int] = 100

__all__ = [
    "DEFAULT_NONLINEAR_MAX_ITER",
    "DEFAULT_NONLINEAR_RTOL",
]

"""Canonical solver and discretisation defaults for coupled numerics."""

from __future__ import annotations

from typing import Final

# NUM-16 reference damped-Newton settings
DEFAULT_NONLINEAR_RTOL: Final[float] = 1.0e-6
DEFAULT_NONLINEAR_MAX_ITER: Final[int] = 100
DEFAULT_NONLINEAR_STRATEGY: Final[str] = "newton"
DEFAULT_NONLINEAR_DAMPING: Final[str] = "residual"

# Taylor-Hood discretisation orders
DEFAULT_ELEMENT_ORDER_U: Final[int] = 2
DEFAULT_ELEMENT_ORDER_P: Final[int] = 1
DEFAULT_ELEMENTS_U: Final[str] = "P2"
DEFAULT_ELEMENTS_P: Final[str] = "P1"
DEFAULT_ELEMENTS_PHI: Final[str] = "P2"
DEFAULT_ELEMENTS_C: Final[str] = "P2"

# Solvers and continuation
DEFAULT_LINEAR_SOLVER: Final[str] = "umfpack"
DEFAULT_CONTINUATION: Final[str] = "default_ladder"
DEFAULT_STABILISATION: Final[str] = "none"

# PHY-02 distance field
DEFAULT_WALL_DISTANCE_SOURCES: Final[str] = "wall"
DEFAULT_WALL_DISTANCE_MAX_NM: Final[float] = 3.0

__all__ = [
    "DEFAULT_CONTINUATION",
    "DEFAULT_ELEMENTS_C",
    "DEFAULT_ELEMENTS_P",
    "DEFAULT_ELEMENTS_PHI",
    "DEFAULT_ELEMENTS_U",
    "DEFAULT_ELEMENT_ORDER_P",
    "DEFAULT_ELEMENT_ORDER_U",
    "DEFAULT_LINEAR_SOLVER",
    "DEFAULT_NONLINEAR_DAMPING",
    "DEFAULT_NONLINEAR_MAX_ITER",
    "DEFAULT_NONLINEAR_RTOL",
    "DEFAULT_NONLINEAR_STRATEGY",
    "DEFAULT_STABILISATION",
    "DEFAULT_WALL_DISTANCE_MAX_NM",
    "DEFAULT_WALL_DISTANCE_SOURCES",
]

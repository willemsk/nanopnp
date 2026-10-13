"""The empirical correction forms of PHY-11, written once."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Protocol, TypeAlias

from nanopnp.core.typing import Numeric

__all__ = [
    "FORMS",
    "FORM_PARAMETERS",
    "NGSOLVE_OPS",
    "NUMPY_OPS",
    "MathOps",
    "NGSolveOps",
    "Numeric",
    "NumpyOps",
    "exponential_saturation_plus",
    "gavish_langevin",
    "get_form",
    "inverse_poly_half",
    "langevin",
    "logistic_plus",
    "poly_jones_dole",
    "poly_quadratic",
]

_LANGEVIN_SERIES_CUTOFF = 3e-4


class MathOps(Protocol):
    def sqrt(self, x: Numeric) -> Numeric: ...

    def exp(self, x: Numeric) -> Numeric: ...

    def sinh(self, x: Numeric) -> Numeric: ...

    def cosh(self, x: Numeric) -> Numeric: ...

    def where_positive(
        self, condition: Numeric, if_true: Numeric, if_false: Numeric
    ) -> Numeric: ...

    def clip(self, x: Numeric, lower: float, upper: float | None) -> Numeric: ...


class NumpyOps:
    def sqrt(self, x: Numeric) -> Numeric:
        import numpy as np

        return np.sqrt(x)

    def exp(self, x: Numeric) -> Numeric:
        import numpy as np

        return np.exp(x)

    def sinh(self, x: Numeric) -> Numeric:
        import numpy as np

        return np.sinh(x)

    def cosh(self, x: Numeric) -> Numeric:
        import numpy as np

        return np.cosh(x)

    def where_positive(self, condition: Numeric, if_true: Numeric, if_false: Numeric) -> Numeric:
        import numpy as np

        return np.where(np.asarray(condition) > 0.0, if_true, if_false)

    def clip(self, x: Numeric, lower: float, upper: float | None) -> Numeric:
        import numpy as np

        return np.clip(x, lower, upper)


class NGSolveOps:
    def sqrt(self, x: Numeric) -> Numeric:
        import ngsolve as ngs

        return ngs.sqrt(x)

    def exp(self, x: Numeric) -> Numeric:
        import ngsolve as ngs

        return ngs.exp(x)

    def sinh(self, x: Numeric) -> Numeric:
        import ngsolve as ngs

        return ngs.sinh(x)

    def cosh(self, x: Numeric) -> Numeric:
        import ngsolve as ngs

        return ngs.cosh(x)

    def where_positive(self, condition: Numeric, if_true: Numeric, if_false: Numeric) -> Numeric:
        import ngsolve as ngs

        return ngs.IfPos(condition, if_true, if_false)

    def clip(self, x: Numeric, lower: float, upper: float | None) -> Numeric:
        import ngsolve as ngs

        if upper is None:
            return ngs.IfPos(x - lower, x, lower)
        return ngs.IfPos(x - lower, ngs.IfPos(x - upper, upper, x), lower)


NUMPY_OPS: MathOps = NumpyOps()

NGSOLVE_OPS: MathOps = NGSolveOps()


def langevin(x: Numeric, ops: MathOps = NUMPY_OPS) -> Numeric:
    guard = x - _LANGEVIN_SERIES_CUTOFF
    safe = ops.where_positive(guard, x, 1.0)
    return ops.where_positive(guard, ops.cosh(safe) / ops.sinh(safe) - 1.0 / safe, x / 3.0)


def inverse_poly_half(p: Mapping[str, float], c: Numeric, ops: MathOps = NUMPY_OPS) -> Numeric:
    root = ops.sqrt(c)
    return 1.0 / (1.0 + p["P1"] * root + p["P2"] * c + p["P3"] * c * root + p["P4"] * c * c)


def poly_jones_dole(p: Mapping[str, float], c: Numeric, ops: MathOps = NUMPY_OPS) -> Numeric:
    root = ops.sqrt(c)
    return 1.0 + p["P1"] * root + p["P2"] * c + p["P3"] * c * c + p["P4"] * c * c * c * root


def poly_quadratic(p: Mapping[str, float], c: Numeric, ops: MathOps = NUMPY_OPS) -> Numeric:
    del ops  # no transcendental operation needed
    return 1.0 + p["P1"] * c + p["P2"] * c * c


def gavish_langevin(p: Mapping[str, float], c: Numeric, ops: MathOps = NUMPY_OPS) -> Numeric:
    p0, p1, p2 = p["P0"], p["P1"], p["P2"]
    return 1.0 - (1.0 - p1 / p0) * langevin(3.0 * p2 * c / (p0 - p1), ops)


def exponential_saturation_plus(
    p: Mapping[str, float], d: Numeric, ops: MathOps = NUMPY_OPS
) -> Numeric:
    return 1.0 - ops.exp(-p["P1"] * (d + p["P2"]))


def logistic_plus(p: Mapping[str, float], d: Numeric, ops: MathOps = NUMPY_OPS) -> Numeric:
    return 1.0 + ops.exp(-p["P1"] * (d - p["P2"]))


FormFunction: TypeAlias = Callable[[Mapping[str, float], Numeric, MathOps], Numeric]

FORMS: Mapping[str, FormFunction] = {
    "inverse_poly_half": inverse_poly_half,
    "poly_jones_dole": poly_jones_dole,
    "poly_quadratic": poly_quadratic,
    "gavish_langevin": gavish_langevin,
    "exponential_saturation_plus": exponential_saturation_plus,
    "logistic_plus": logistic_plus,
}

FORM_PARAMETERS: Mapping[str, frozenset[str]] = {
    "inverse_poly_half": frozenset({"P1", "P2", "P3", "P4"}),
    "poly_jones_dole": frozenset({"P1", "P2", "P3", "P4"}),
    "poly_quadratic": frozenset({"P1", "P2"}),
    "gavish_langevin": frozenset({"P0", "P1", "P2"}),
    "exponential_saturation_plus": frozenset({"P1", "P2"}),
    "logistic_plus": frozenset({"P1", "P2"}),
}


def get_form(name: str) -> FormFunction:
    try:
        return FORMS[name]
    except KeyError:
        known = ", ".join(sorted(FORMS))
        raise KeyError(f"unknown correction form {name!r}; registered forms are {known}") from None

"""The empirical correction forms of PHY-11, written once.

Every concentration- and wall-dependent property of the ePNP-NS model is
``X(<c>, d) = X0 * f_c(c_bar) * f_w(d_bar)`` with ``c_bar = <c>/(1 M)`` and
``d_bar = d/(1 nm)`` (PHY-10). This module holds the five ``f_c`` forms and the
two ``f_w`` forms, and nothing else.

Each form is evaluated through a small operation namespace so that the *same*
expression serves both the numeric path (floats and NumPy arrays, used by the
VER-03 conformance tests) and the symbolic path (NGSolve ``CoefficientFunction``
expressions, where the assembled Jacobian is differentiated symbolically). The
formulae must never be written twice: a correction that is right in the test and
wrong in the solver is precisely the failure mode this indirection exists to
prevent.

The two wall functions carry **opposite offset signs** — ``(d_bar + P2)`` for
diffusivity and mobility, ``(d_bar - P2)`` for viscosity. See PHY-11 and the
errata of section 4.6; ``.knowledge/01-physics-epnpns.md`` section 8 carries the
arithmetic.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any, Protocol, TypeAlias

Numeric: TypeAlias = Any
"""A float, a NumPy array or an NGSolve ``CoefficientFunction``.

These three share no common protocol, so the annotation is deliberately loose;
the ``MathOps`` implementation, not the type checker, is what keeps a form
consistent across the numeric and symbolic paths.
"""

_LANGEVIN_SERIES_CUTOFF = 3e-4
"""Below this argument the Langevin function is taken as its ``x/3`` limit.

Chosen where the two branches are equally accurate rather than as small as
possible. ``coth(x) - 1/x`` subtracts two quantities of size ``1/x`` to leave a
result of size ``x/3``, so its relative error grows like ``3 eps / x^2``; the
truncated series ``x/3`` has relative error ``x^2/15``. The two cross near
``3e-4``, where both are accurate to about 7e-9. A cutoff of 1e-8 sits deep
inside the cancellation region: ``L(1.1e-8)`` then evaluates to exactly zero
instead of 3.667e-9.
"""


class MathOps(Protocol):
    """The operations a correction form is allowed to use.

    Kept as small as the forms require: adding an operation here means adding it
    to every backend, so a form that needs something exotic is a signal to
    reconsider the form rather than to widen this protocol.
    """

    def sqrt(self, x: Numeric) -> Numeric:
        """Return the square root of ``x``."""
        ...

    def exp(self, x: Numeric) -> Numeric:
        """Return the exponential of ``x``."""
        ...

    def sinh(self, x: Numeric) -> Numeric:
        """Return the hyperbolic sine of ``x``."""
        ...

    def cosh(self, x: Numeric) -> Numeric:
        """Return the hyperbolic cosine of ``x``."""
        ...

    def where_positive(self, condition: Numeric, if_true: Numeric, if_false: Numeric) -> Numeric:
        """Return ``if_true`` where ``condition > 0`` and ``if_false`` elsewhere."""
        ...

    def clip(self, x: Numeric, lower: float, upper: float) -> Numeric:
        """Return ``x`` limited to ``[lower, upper]``."""
        ...


class NumpyOps:
    """Numeric evaluation with NumPy, for scalars, arrays and tests."""

    def sqrt(self, x: Numeric) -> Numeric:  # noqa: D102 - documented on MathOps
        import numpy as np

        return np.sqrt(x)

    def exp(self, x: Numeric) -> Numeric:  # noqa: D102
        import numpy as np

        return np.exp(x)

    def sinh(self, x: Numeric) -> Numeric:  # noqa: D102
        import numpy as np

        return np.sinh(x)

    def cosh(self, x: Numeric) -> Numeric:  # noqa: D102
        import numpy as np

        return np.cosh(x)

    def where_positive(  # noqa: D102
        self, condition: Numeric, if_true: Numeric, if_false: Numeric
    ) -> Numeric:
        import numpy as np

        return np.where(np.asarray(condition) > 0.0, if_true, if_false)

    def clip(self, x: Numeric, lower: float, upper: float) -> Numeric:  # noqa: D102
        import numpy as np

        return np.clip(x, lower, upper)


class NGSolveOps:
    """Symbolic evaluation, building an NGSolve ``CoefficientFunction`` tree.

    NGSolve exposes ``sinh`` and ``cosh`` but no ``tanh``, which is why the
    Langevin function below is written with ``cosh/sinh`` rather than
    ``1/tanh``.
    """

    def sqrt(self, x: Numeric) -> Numeric:  # noqa: D102
        import ngsolve as ngs

        return ngs.sqrt(x)

    def exp(self, x: Numeric) -> Numeric:  # noqa: D102
        import ngsolve as ngs

        return ngs.exp(x)

    def sinh(self, x: Numeric) -> Numeric:  # noqa: D102
        import ngsolve as ngs

        return ngs.sinh(x)

    def cosh(self, x: Numeric) -> Numeric:  # noqa: D102
        import ngsolve as ngs

        return ngs.cosh(x)

    def where_positive(  # noqa: D102
        self, condition: Numeric, if_true: Numeric, if_false: Numeric
    ) -> Numeric:
        import ngsolve as ngs

        return ngs.IfPos(condition, if_true, if_false)

    def clip(self, x: Numeric, lower: float, upper: float) -> Numeric:  # noqa: D102
        import ngsolve as ngs

        return ngs.IfPos(x - lower, ngs.IfPos(x - upper, upper, x), lower)


NUMPY_OPS: MathOps = NumpyOps()
"""Default operation namespace; the symbolic one is built on demand."""


def langevin(x: Numeric, ops: MathOps = NUMPY_OPS) -> Numeric:
    """Return the Langevin function ``L(x) = coth(x) - 1/x``.

    The singularity at ``x = 0`` is removable — ``L(x) -> x/3`` — and is taken
    as the series limit below a small cutoff, so that a zero-concentration
    evaluation returns 0 rather than a division by zero. Both branches are
    evaluated on a guarded argument, because neither backend short-circuits.

    Parameters
    ----------
    x
        Function argument.
    ops
        Operation namespace to evaluate with.

    Returns
    -------
    Numeric
        ``L(x)``.
    """
    guard = x - _LANGEVIN_SERIES_CUTOFF
    safe = ops.where_positive(guard, x, 1.0)
    return ops.where_positive(guard, ops.cosh(safe) / ops.sinh(safe) - 1.0 / safe, x / 3.0)


def inverse_poly_half(p: Mapping[str, float], c: Numeric, ops: MathOps = NUMPY_OPS) -> Numeric:
    """Return ``(1 + P1 c^1/2 + P2 c + P3 c^3/2 + P4 c^2)^-1``.

    The concentration correction of both diffusivity and mobility (PHY-11), with
    separate coefficients per ion and per property. Half-integer powers are
    formed from ``sqrt`` rather than ``**``, which keeps the symbolic tree small
    and avoids a fractional power of a coefficient function.
    """
    root = ops.sqrt(c)
    return 1.0 / (1.0 + p["P1"] * root + p["P2"] * c + p["P3"] * c * root + p["P4"] * c * c)


def poly_jones_dole(p: Mapping[str, float], c: Numeric, ops: MathOps = NUMPY_OPS) -> Numeric:
    """Return the Jones-Dole viscosity form ``1 + P1 c^1/2 + P2 c + P3 c^2 + P4 c^7/2``."""
    root = ops.sqrt(c)
    return 1.0 + p["P1"] * root + p["P2"] * c + p["P3"] * c * c + p["P4"] * c * c * c * root


def poly_quadratic(p: Mapping[str, float], c: Numeric, ops: MathOps = NUMPY_OPS) -> Numeric:
    """Return the mass-density form ``1 + P1 c + P2 c^2``."""
    del ops  # no transcendental operation needed
    return 1.0 + p["P1"] * c + p["P2"] * c * c


def gavish_langevin(p: Mapping[str, float], c: Numeric, ops: MathOps = NUMPY_OPS) -> Numeric:
    """Return the permittivity form ``1 - (1 - P1/P0) L(3 P2 c / (P0 - P1))``.

    ``P0`` is the infinite-dilution permittivity, ``P1`` the limiting
    permittivity ``eps_r,ms`` and ``P2`` the excess polarisation ``alpha``. The
    parameters actually used by the published model are Gavish's NaCl values
    (30.08, 11.5), not the authors' own Buchner fit; the distinction moves the
    5.3 M cap from 42.13 to 42.67 (erratum 6).
    """
    p0, p1, p2 = p["P0"], p["P1"], p["P2"]
    return 1.0 - (1.0 - p1 / p0) * langevin(3.0 * p2 * c / (p0 - p1), ops)


def exponential_saturation_plus(
    p: Mapping[str, float], d: Numeric, ops: MathOps = NUMPY_OPS
) -> Numeric:
    """Return the ion wall function ``1 - exp(-P1 (d + P2))``.

    Shared by diffusivity and mobility. The offset is **plus**: thesis eq. 5.11
    prints a minus, which makes the function negative at the wall
    (``f(0) = -0.0640``) and is erratum 1. With the plus, ``f(0) = 0.0601`` and
    ``f(0.75 nm) = 0.9910``, matching the published check values.
    """
    return 1.0 - ops.exp(-p["P1"] * (d + p["P2"]))


def logistic_plus(p: Mapping[str, float], d: Numeric, ops: MathOps = NUMPY_OPS) -> Numeric:
    """Return the viscosity wall function ``1 + exp(-P1 (d - P2))``.

    The offset is **minus** here, opposite to the ion wall function above, and
    the function is greater than one: viscosity rises towards the wall, so
    ``eta0/eta_w(0) = 0.3790``.
    """
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
"""Correction forms by the name a parameter file uses to select them."""


def get_form(name: str) -> FormFunction:
    """Return the correction form registered under ``name``.

    Raises
    ------
    KeyError
        If no such form exists; the message lists the registered names.
    """
    try:
        return FORMS[name]
    except KeyError:
        known = ", ".join(sorted(FORMS))
        raise KeyError(f"unknown correction form {name!r}; registered forms are {known}") from None

"""Integration measures for the (r, z) half-plane (NUM-04, NUM-07).

Every volume and surface integral of the axisymmetric weak forms carries an ``r``
weight, the ``2*pi`` having cancelled from both sides. Forgetting that weight
produces a plausible, wrong answer with no solver diagnostic, so the weight is
not something a call site supplies: it is applied here, by construction, and a
form is written as ``measures.volume(integrand)`` rather than as
``integrand * x * dx``.

The same code serves planar geometry, where the weight is 1. The 1D analytic
benchmarks (Gouy-Chapman, the PNP limiting current) are genuinely planar; forcing
them onto an axisymmetric slab would compare the solver against the wrong closed
form.

Quadrature is the other trap. NGSolve's order-2 triangle rule places its points
at the edge midpoints, so an element with an edge on the axis is sampled exactly
at ``r = 0`` and any ``1/r`` factor returns NaN rather than raising. Forms that
carry such a factor must declare it — ``singular=True`` — and this module then
guarantees an integration order of at least 3 (NUM-07, VER-07).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from nanopnp.core.typing import Expression, IntegralTerm, Mesh, Numeric, Option

Symmetry: TypeAlias = Literal["axisymmetric", "planar"]

SINGULAR_MIN_ORDER = 3
"""Minimum integration order for any form carrying a ``1/r`` factor (NUM-07)."""

NGSOLVE_INTEGRATE_ORDER = 5
"""The order ``ngsolve.Integrate`` uses when none is given.

``integrate`` below passes an explicit order, which *replaces* NGSolve's default
rather than adding to it, so the order it computes is floored here. Without the
floor, routing an integral through this class would be less accurate than the
bare ``ngsolve.Integrate`` it wraps: at ``element_order = 2`` the computed order
is 2, and integrating ``x**3`` over the unit square then returns 0.20005 for an
exact 0.2.
"""


def _gradient_default_order(element_order: int) -> int:
    """Return the integration order NGSolve uses for a gradient-gradient term.

    Assumed as ``2 * (p - 1)``: two P2 gradients integrate at order 2, which is
    *below* the singular minimum and is exactly how a ``1/r`` term ends up
    sampled at the axis. This is a model of NGSolve's own estimate and cannot be
    relied on to be conservative, which is why the singular bonus of
    ``bonus_order`` no longer measures a deficit against it.
    """
    return 2 * max(element_order - 1, 1)


@dataclass(frozen=True)
class Measures:
    """Volume and surface measures for one symmetry and one element order."""

    symmetry: Symmetry = "axisymmetric"
    element_order: int = 2

    @property
    def is_axisymmetric(self) -> bool:
        """Whether integrals carry the ``r`` weight."""
        return self.symmetry == "axisymmetric"

    @property
    def radial_weight(self) -> Numeric:
        """The ``r`` weight itself: the radial coordinate, or 1 in planar geometry."""
        if not self.is_axisymmetric:
            return 1.0
        import ngsolve as ngs

        return ngs.x

    def bonus_order(self, *, singular: bool = False, extra: int = 0) -> int:
        """Return the quadrature bonus to add for one term.

        Parameters
        ----------
        singular
            Whether the integrand carries a ``1/r`` factor.
        extra
            Additional orders requested by the caller, for a strongly varying
            coefficient.
        """
        bonus = extra
        if singular:
            # The bonus alone must reach the minimum. ``bonus_intorder`` is added
            # to the order NGSolve estimates for the integrand, and that estimate
            # is not knowable here - for a quotient it can be as low as 2. A
            # bonus computed as a deficit against ``_gradient_default_order``
            # comes out zero for every ``element_order >= 3``, which would leave
            # the NUM-07 guarantee resting entirely on that estimate.
            bonus = max(bonus, SINGULAR_MIN_ORDER)
        return bonus

    def integration_order(self, *, singular: bool = False, extra: int = 0) -> int:
        """Return the order :meth:`integrate` evaluates at.

        Floored at ``NGSOLVE_INTEGRATE_ORDER`` so that going through this class
        is never coarser than calling ``ngsolve.Integrate`` directly, and raised
        by the bonus of :meth:`bonus_order` on top of that.
        """
        base = max(_gradient_default_order(self.element_order), NGSOLVE_INTEGRATE_ORDER)
        return base + self.bonus_order(singular=singular, extra=extra)

    def volume(
        self,
        integrand: Expression,
        *,
        singular: bool = False,
        extra_order: int = 0,
        **kwargs: Option,
    ) -> IntegralTerm:
        """Return the weighted volume integral term of ``integrand``.

        Parameters
        ----------
        integrand
            The unweighted integrand; the ``r`` weight is applied here.
        singular
            Set when the integrand carries a ``1/r`` factor, which raises the
            integration order to at least ``SINGULAR_MIN_ORDER`` (NUM-07).
        extra_order
            Additional quadrature orders.
        **kwargs
            Passed to ``ngsolve.dx``, e.g. ``definedon``.

        Raises
        ------
        ValueError
            If a caller passes ``bonus_intorder`` directly, which would bypass
            the singular guarantee.
        """
        import ngsolve as ngs

        if "bonus_intorder" in kwargs:
            raise ValueError("pass extra_order, not bonus_intorder, so the 1/r guarantee holds")
        bonus = self.bonus_order(singular=singular, extra=extra_order)
        return integrand * self.radial_weight * ngs.dx(bonus_intorder=bonus, **kwargs)

    def surface(
        self,
        integrand: Expression,
        *,
        singular: bool = False,
        extra_order: int = 0,
        **kwargs: Option,
    ) -> IntegralTerm:
        """Return the weighted surface integral term of ``integrand``.

        The axis boundary term is annihilated by the ``r`` weight, which is why
        the axis conditions on ``phi``, ``c_i`` and ``u_z`` are natural and must
        not be imposed as Dirichlet conditions (NUM-06).
        """
        import ngsolve as ngs

        if "bonus_intorder" in kwargs:
            raise ValueError("pass extra_order, not bonus_intorder, so the 1/r guarantee holds")
        bonus = self.bonus_order(singular=singular, extra=extra_order)
        return integrand * self.radial_weight * ngs.ds(bonus_intorder=bonus, **kwargs)

    def integrate(
        self,
        integrand: Expression,
        mesh: Mesh,
        *,
        singular: bool = False,
        extra_order: int = 0,
        what: str = "integral",
        **kwargs: Option,
    ) -> float:
        """Evaluate a weighted integral, failing loudly on a non-finite result.

        A NaN from an axis-sampled ``1/r`` factor propagates silently through an
        assembled form; here it aborts with the name of the quantity and the
        order that produced it (NUM-07, QR-12).

        Raises
        ------
        ValueError
            If the result is NaN or infinite.
        """
        import math

        import ngsolve as ngs

        order = self.integration_order(singular=singular, extra=extra_order)
        value = float(ngs.Integrate(integrand * self.radial_weight, mesh, order=order, **kwargs))
        if not math.isfinite(value):
            raise ValueError(
                f"{what} evaluated to {value} at integration order {order}"
                f"{' (singular form)' if singular else ''}: a 1/r factor sampled on the axis is "
                "the usual cause; see NUM-07"
            )
        return value


AXISYMMETRIC = Measures(symmetry="axisymmetric", element_order=2)
"""The production measure: P2 fields on the (r, z) half-plane."""

PLANAR = Measures(symmetry="planar", element_order=2)
"""Planar measure, for the 1D analytic benchmarks."""

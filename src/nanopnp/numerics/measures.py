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

import math
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


def _check_rule_order(rule_order: int, *, singular: bool, extra_order: int) -> None:
    """Refuse an explicit rule below NUM-07's floor, or beside the bonus arguments (WP41 D2).

    ``rule_order`` replaces the bonus logic, so it carries NUM-07's floor itself,
    and it cannot be combined with the two arguments that logic reads.

    Raises
    ------
    ValueError
        Naming ``rule_order`` and its value, or the argument passed beside it.
    """
    if rule_order < SINGULAR_MIN_ORDER:
        raise ValueError(
            f"rule_order is {rule_order}; it must be at least NUM-07's minimum of "
            f"{SINGULAR_MIN_ORDER}"
        )
    if singular:
        raise ValueError("rule_order cannot be combined with singular=True")
    if extra_order != 0:
        raise ValueError(f"rule_order cannot be combined with extra_order={extra_order}")


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
    weight_extra_order: int = 0
    """Orders added to every non-singular axisymmetric :meth:`volume` and :meth:`surface` term.

    NUM-07's NOTE on the ``r`` weight: NGSolve does not count the coordinate when
    it estimates an integrand's order, so those terms are integrated one order
    short of their degree in ``r``. This is the seam WP34 measures that through
    (D7, D8). No case key, model option or CLI flag reaches it, and at 0 every
    form is assembled exactly as before; the decision is Phase 6's (section 8.2.6
    F1). :meth:`integrate` and singular terms, already at NUM-07's floor, ignore it,
    and so does a term given an explicit ``rule_order``, which fixes its rule outright.
    """

    def __post_init__(self) -> None:
        """Refuse a negative ``weight_extra_order``, which would lower NUM-07's quadrature."""
        if self.weight_extra_order < 0:
            raise ValueError(
                f"weight_extra_order is {self.weight_extra_order}; it adds orders for the r "
                "weight and cannot remove any (NUM-07 NOTE on the r weight)"
            )

    @property
    def is_axisymmetric(self) -> bool:
        """Whether integrals carry the ``r`` weight."""
        return self.symmetry == "axisymmetric"

    @property
    def coordinate_names(self) -> tuple[str, str]:
        """Names of the two mesh coordinates, for diagnostics naming a location."""
        return ("r", "z") if self.is_axisymmetric else ("x", "y")

    @property
    def radial_weight(self) -> Numeric:
        """The ``r`` weight itself: the radial coordinate, or 1 in planar geometry."""
        if not self.is_axisymmetric:
            return 1.0
        import ngsolve as ngs

        return ngs.x

    def _form_bonus(self, *, singular: bool, extra: int) -> int:
        """Return a :meth:`volume` or :meth:`surface` term's bonus, with ``weight_extra_order``."""
        bonus = self.bonus_order(singular=singular, extra=extra)
        if self.is_axisymmetric and not singular:
            bonus += self.weight_extra_order
        return bonus

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
        rule_order: int | None = None,
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
        rule_order
            An explicit integration rule order, which replaces NGSolve's order
            estimate and the bonus logic with an explicit rule on every element
            type of the mesh (WP41 D2).
        **kwargs
            Passed to ``ngsolve.dx``, e.g. ``definedon``.

        Raises
        ------
        ValueError
            If a caller passes ``bonus_intorder`` directly, which would bypass
            the singular guarantee; or if ``rule_order`` is below NUM-07's
            minimum of 3 or combined with ``singular`` or ``extra_order``.
        """
        import ngsolve as ngs

        if "bonus_intorder" in kwargs:
            raise ValueError("pass extra_order, not bonus_intorder, so the 1/r guarantee holds")
        if rule_order is not None:
            _check_rule_order(rule_order, singular=singular, extra_order=extra_order)
            # Every element type a volume term can meet, the 1D benchmarks' SEGM
            # among them: a type missing here would fall back to NGSolve's own
            # estimate while ``integrate`` honours ``order=`` on it, and the
            # source and its gate would no longer be one rule.
            intrules = {
                kind: ngs.IntegrationRule(kind, rule_order)
                for kind in (ngs.SEGM, ngs.TRIG, ngs.QUAD)
            }
            return integrand * self.radial_weight * ngs.dx(intrules=intrules, **kwargs)
        bonus = self._form_bonus(singular=singular, extra=extra_order)
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
        bonus = self._form_bonus(singular=singular, extra=extra_order)
        return integrand * self.radial_weight * ngs.ds(bonus_intorder=bonus, **kwargs)

    def integrate(
        self,
        integrand: Expression,
        mesh: Mesh,
        *,
        singular: bool = False,
        extra_order: int = 0,
        rule_order: int | None = None,
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
            If the result is NaN or infinite; or if ``rule_order`` is below
            NUM-07's minimum of 3 or combined with ``singular`` or ``extra_order``.
        """
        import ngsolve as ngs

        if rule_order is not None:
            _check_rule_order(rule_order, singular=singular, extra_order=extra_order)
            order = rule_order
        else:
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

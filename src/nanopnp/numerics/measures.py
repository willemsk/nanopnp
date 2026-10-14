"""Integration measures for the (r, z) half-plane (NUM-04, NUM-07)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, TypeAlias

from nanopnp.core.typing import Expression, IntegralTerm, Mesh, Numeric, Option

Symmetry: TypeAlias = Literal["axisymmetric", "planar"]

# The minimum order on a form carrying 1/r: SPECIFICATION.md NUM-07.
SINGULAR_MIN_ORDER = 3

NGSOLVE_INTEGRATE_ORDER = 5


def _check_rule_order(rule_order: int, *, singular: bool, extra_order: int) -> None:
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
    return 2 * max(element_order - 1, 1)


@dataclass(frozen=True)
class Measures:
    """Volume and surface measures for one symmetry and one element order."""

    symmetry: Symmetry = "axisymmetric"
    element_order: int = 2
    weight_extra_order: int = 0

    def __post_init__(self) -> None:
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
        bonus = self.bonus_order(singular=singular, extra=extra)
        if self.is_axisymmetric and not singular:
            bonus += self.weight_extra_order
        return bonus

    def bonus_order(self, *, singular: bool = False, extra: int = 0) -> int:
        """Return the quadrature bonus for one term; ``singular`` marks a ``1/r`` factor."""
        bonus = extra
        if singular:
            # The bonus alone must reach the minimum: NGSolve's own estimate is unknowable
            # here and can be 2 for a quotient (.knowledge/06-numerics-fem.md section 8.1).
            bonus = max(bonus, SINGULAR_MIN_ORDER)
        return bonus

    def integration_order(self, *, singular: bool = False, extra: int = 0) -> int:
        """Return the order integrate evaluates at, never coarser than ngsolve.Integrate."""
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
        """Return the weighted volume integral term of ``integrand``, with the ``r`` weight.

        Raises
        ------
        ValueError
            For a direct ``bonus_intorder``, or an invalid ``rule_order``.
        """
        import ngsolve as ngs

        if "bonus_intorder" in kwargs:
            raise ValueError("pass extra_order, not bonus_intorder, so the 1/r guarantee holds")
        if rule_order is not None:
            _check_rule_order(rule_order, singular=singular, extra_order=extra_order)
            # Every element type, SEGM included: a missing one falls back to NGSolve's estimate.
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
        """Return the weighted surface integral term; the axis conditions are natural."""
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
        """Evaluate a weighted integral; ValueError on a non-finite result."""
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

PLANAR = Measures(symmetry="planar", element_order=2)


@dataclass(frozen=True)
class FixedCharge:
    """A fixed-charge density and the integration rule it is assembled with.

    Parameters
    ----------
    density
        Dimensionless where a model takes it, SI before scaling.
    """

    density: Expression
    rule_order: int | None

    def scaled(self, factor: Numeric) -> FixedCharge:
        """Return the density times ``factor``, with the same rule."""
        return FixedCharge(density=factor * self.density, rule_order=self.rule_order)

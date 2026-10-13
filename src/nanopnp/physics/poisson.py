"""The axisymmetric Poisson operator (PHY-03, NUM-04)."""

from __future__ import annotations

from nanopnp.core.typing import Expression, IntegralTerm, Numeric
from nanopnp.numerics.measures import Measures


def poisson_operator(
    trial: Expression,
    test: Expression,
    measures: Measures,
    *,
    permittivity: Numeric = 1.0,
    extra_order: int = 0,
) -> IntegralTerm:
    import ngsolve as ngs

    return measures.volume(permittivity * ngs.grad(trial) * ngs.grad(test), extra_order=extra_order)


def charge_source(
    charge_density: Numeric,
    test: Expression,
    measures: Measures,
    *,
    rule_order: int | None = None,
    **kwargs: Expression,
) -> IntegralTerm:
    return measures.volume(charge_density * test, rule_order=rule_order, **kwargs)


def surface_charge_source(
    surface_density: Numeric,
    test: Expression,
    measures: Measures,
    **kwargs: Expression,
) -> IntegralTerm:
    return measures.surface(surface_density * test, **kwargs)

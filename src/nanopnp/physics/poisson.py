"""The axisymmetric Poisson operator (PHY-03, NUM-04)."""

from __future__ import annotations

from nanopnp.core.typing import Expression, IntegralTerm, Mesh, Numeric
from nanopnp.numerics.measures import Measures


def poisson_operator(
    trial: Expression,
    test: Expression,
    measures: Measures,
    *,
    permittivity: Numeric = 1.0,
    extra_order: int = 0,
) -> IntegralTerm:
    """Return the Poisson stiffness term ``int eps grad(phi) . grad(v) r``."""
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
    """Return the volumetric charge source term ``int rho v r``."""
    return measures.volume(charge_density * test, rule_order=rule_order, **kwargs)


def surface_charge_source(
    surface_density: Numeric,
    test: Expression,
    measures: Measures,
    **kwargs: Expression,
) -> IntegralTerm:
    """Return the prescribed surface charge term ``int_Gamma sigma_s v r ds``."""
    return measures.surface(surface_density * test, **kwargs)


def surface_charge_region(mesh: Mesh, boundary: str) -> Expression:
    """Return the boundary a prescribed surface charge is applied to.

    Parameters
    ----------
    boundary
        The boundary name or pattern the charge is applied to. A name matching nothing is
        refused: the term would vanish and the solve would converge on the uncharged answer.
    """
    region = mesh.Boundaries(boundary)
    if region.Mask().NumSet() == 0:
        carried = ", ".join(sorted(set(mesh.GetBoundaries())))
        raise ValueError(
            f"surface_charge_boundary={boundary!r} matches no boundary of the mesh; it carries "
            f"{carried}. A charge applied to nothing leaves the wall uncharged and the solve "
            "converges (NUM-06, QR-12)"
        )
    return region

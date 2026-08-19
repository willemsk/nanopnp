"""The axisymmetric Poisson operator (PHY-03, NUM-04).

Poisson is solved over the *whole* domain - electrolyte, protein and membrane -
while Nernst-Planck and Navier-Stokes are solved on the electrolyte only. The
weak form is

    int eps grad(phi) . grad(v) r dr dz
        = int (rho_pore + rho_ion) v r dr dz + int_Gamma sigma_s v r ds

with the ``r`` weight supplied by ``Measures`` rather than by the call site.
"""

from __future__ import annotations

from nanopnp.core.typing import Expression, IntegralTerm, Numeric
from nanopnp.physics.measures import Measures


def poisson_operator(
    trial: Expression,
    test: Expression,
    measures: Measures,
    *,
    permittivity: Numeric = 1.0,
) -> IntegralTerm:
    """Return ``int eps grad(phi) . grad(v) r``, the Poisson stiffness term.

    Parameters
    ----------
    trial, test
        Trial and test functions, or a grid function and a test function for a
        residual form.
    measures
        Symmetry and quadrature policy.
    permittivity
        ``eps = eps_0 eps_r``, piecewise over the domains, in units consistent
        with the source term.
    """
    import ngsolve as ngs

    return measures.volume(permittivity * ngs.grad(trial) * ngs.grad(test))


def charge_source(
    charge_density: Numeric,
    test: Expression,
    measures: Measures,
    **kwargs: Expression,
) -> IntegralTerm:
    """Return ``int rho v r``, the volumetric charge source term."""
    return measures.volume(charge_density * test, **kwargs)


def surface_charge_source(
    surface_density: Numeric,
    test: Expression,
    measures: Measures,
    **kwargs: Expression,
) -> IntegralTerm:
    """Return ``int_Gamma sigma_s v r ds``, a prescribed surface charge."""
    return measures.surface(surface_density * test, **kwargs)

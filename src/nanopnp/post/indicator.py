"""The domain indicator ``psi`` of the NUM-24 current form.

NUM-23 forbids computing the ionic current by integrating the continuous-Galerkin
flux over a cross-section. A CG flux is not pointwise conservative, so that
integral depends on which cross-section is taken, by amounts that can exceed the
rectification signal at low bias (RSK-03). The cure NUM-24 prescribes is to
replace the surface integral by a volume one,

    I = F sum_i z_i int_Omega J_i . grad(psi) r dr dz

with ``psi`` a smooth function equal to 1 on the cis side of the pore and 0 on
the trans side. The sign is the one that references the current to the grounded
cis electrode, and :mod:`nanopnp.post.qoi` is where that convention is stated and
defended. ``grad(psi)`` is supported only where ``psi`` varies, so the
integral is a *smeared* cross-section: it averages over a band of the domain
rather than sampling one line, and the averaging is what removes the
cross-section dependence. Widening or moving the band must not change the
answer, and that is directly testable (VER-11).

The transition is a C1 smoothstep, ``S(t) = t^2 (3 - 2t)``, rather than a linear
ramp. ``grad(psi)`` is then continuous across both ends of the band instead of
jumping, so the integrand has no kink for the quadrature to resolve and the
result converges in the band width rather than oscillating with it.

``psi`` is built by *interpolation*, never by writing degrees of freedom. The
NGSolve higher-order basis is hierarchical and its shape functions do not form a
partition of unity, so setting a nominal set of coefficients to 1 gives a
function that is not 1 — an error of 8.3 % on a P2 edge, mesh-independent, and
convincingly like a modelling difference rather than a bug. The same reasoning
is written out in :mod:`nanopnp.post.reaction_flux`.
"""

from __future__ import annotations

import logging

from nanopnp.core.typing import Expression, GridFunction, Mesh, Option
from nanopnp.mesh.primitives import CylindricalPoreGeometry

__all__ = [
    "IndicatorError",
    "axial_indicator",
    "check_indicator",
    "lumen_band",
    "smoothstep",
]

logger = logging.getLogger(__name__)


class IndicatorError(ValueError):
    """The indicator does not separate the two reservoirs.

    Raised rather than returned, because an inverted or mispositioned ``psi``
    gives a current with the wrong sign or the wrong magnitude and no other
    symptom (QR-12).
    """


def smoothstep(coordinate: Expression, *, lower_nm: float, upper_nm: float) -> Expression:
    """Return ``S((z - lower)/(upper - lower))``, clamped to ``[0, 1]``.

    ``S(t) = t^2 (3 - 2t)`` is the cubic Hermite step: ``S(0) = 0``, ``S(1) = 1``
    and ``S'(0) = S'(1) = 0``, so the derivative is continuous at both ends of
    the band and ``grad(psi)`` has no jump for the quadrature to straddle.

    Parameters
    ----------
    coordinate
        The coordinate the step runs in, in nm; ``ngsolve.y`` in the ``(r, z)``
        half-plane.
    lower_nm, upper_nm
        Where the step begins and ends. ``upper_nm`` must exceed ``lower_nm``.

    Raises
    ------
    IndicatorError
        If the band has no width, which would divide by zero and produce a step
        function whose gradient is a delta the quadrature cannot see.
    """
    import ngsolve as ngs

    width = upper_nm - lower_nm
    if width <= 0.0:
        raise IndicatorError(
            f"the transition band must have positive width, got lower={lower_nm} nm and "
            f"upper={upper_nm} nm; a zero-width band makes grad(psi) a delta that no "
            "quadrature rule can integrate"
        )
    raw = (coordinate - lower_nm) / width
    clamped = ngs.IfPos(raw, ngs.IfPos(raw - 1.0, 1.0, raw), 0.0)
    return clamped * clamped * (3.0 - 2.0 * clamped)


def lumen_band(geometry: CylindricalPoreGeometry, *, fraction: float = 0.8) -> tuple[float, float]:
    """Return the transition band spanning the middle of the pore lumen, in nm.

    The default puts ``grad(psi)`` wholly inside the lumen and away from both
    mouths, which is where the flux is most nearly one-dimensional and where a
    cross-section integral would have been taken. It is a default, not a
    requirement: the answer must not depend on it, and VER-11 checks that by
    moving and widening the band.

    Parameters
    ----------
    geometry
        The pore. The lumen spans ``+/- half_thickness_nm`` in ``z``.
    fraction
        Fraction of the membrane thickness the band occupies.

    Raises
    ------
    IndicatorError
        If ``fraction`` is not in ``(0, 1]``.
    """
    if not 0.0 < fraction <= 1.0:
        raise IndicatorError(f"fraction must lie in (0, 1], got {fraction}")
    half = geometry.half_thickness_nm * fraction
    return (-half, half)


def axial_indicator(
    mesh: Mesh,
    *,
    lower_nm: float,
    upper_nm: float,
    order: int = 2,
    definedon: Option = None,
) -> GridFunction:
    """Return ``psi``: 0 below ``lower_nm`` in ``z``, 1 above ``upper_nm``.

    ``cis`` lies at ``+z`` in :class:`~nanopnp.mesh.primitives.CylindricalPoreGeometry`,
    so ``psi`` increases with ``z`` and the sign convention of NUM-27 follows:
    a positive current flows trans to cis, in ``+z``.

    Parameters
    ----------
    mesh
        The meshed domain.
    lower_nm, upper_nm
        Ends of the transition band, in nm.
    order
        Element order. It must match the order of the fields the indicator is
        integrated against, or ``grad(psi)`` is represented in a coarser space
        than the flux and the two no longer test the same discretisation.
    definedon
        Region the indicator lives on, e.g. the fluid. ``None`` is the whole
        mesh; the ion flux is zero outside the fluid in any case, but restricting
        keeps the interpolation off the solid where it has no meaning.

    Returns
    -------
    GridFunction
        The interpolated indicator.
    """
    import ngsolve as ngs

    space = (
        ngs.H1(mesh, order=order)
        if definedon is None
        else ngs.H1(mesh, order=order, definedon=definedon)
    )
    indicator = ngs.GridFunction(space, name="psi")
    indicator.Set(smoothstep(ngs.y, lower_nm=lower_nm, upper_nm=upper_nm))
    return indicator


def check_indicator(
    indicator: GridFunction,
    mesh: Mesh,
    *,
    cis: str = "cis",
    trans: str = "trans",
    tolerance: float = 1e-4,
) -> None:
    """Assert that ``psi`` is 1 on the cis boundary and 0 on the trans boundary.

    An inverted band flips the sign of every current, and a band that has run off
    the end of the domain makes ``grad(psi)`` vanish and every current zero.
    Both are silent, so both are checked here before any number is reported
    (QR-12).

    Parameters
    ----------
    indicator
        The indicator to check.
    mesh
        The meshed domain.
    cis, trans
        Boundary-name regular expressions of the two reservoir caps.
    tolerance
        Mean-square departure permitted on each cap. The default is loose on
        purpose. This is a check on *orientation and support*, the two failures
        that are otherwise silent, and both of them put the mean square near 1.
        It is not a check on interpolation accuracy: the reservoir meets the
        membrane at ``z = +/- half_thickness``, so on a coarse mesh an element
        that straddles the transition band shares a vertex with the reservoir
        cap and leaks a fraction of a per cent of ``psi`` onto it. That leak is
        harmless — the flux density on the far cap is negligible, and it shrinks
        with the mesh — but it is not zero, and a tolerance that refused it would
        be refusing the mesh rather than the indicator.

    Raises
    ------
    IndicatorError
        If either cap departs from its value by more than ``tolerance``, with
        the measured values in the message.
    """
    import ngsolve as ngs

    def _mean_square(target: float, boundary: str) -> float:
        region = mesh.Boundaries(boundary)
        length = float(ngs.Integrate(ngs.CF(1.0), mesh, definedon=region))
        if length <= 0.0:
            known = ", ".join(sorted(set(mesh.GetBoundaries())))
            raise IndicatorError(f"no boundary matching {boundary!r} in this mesh; it has {known}")
        deviation = float(ngs.Integrate((indicator - target) ** 2, mesh, definedon=region))
        return deviation / length

    on_cis = _mean_square(1.0, cis)
    on_trans = _mean_square(0.0, trans)
    if on_cis > tolerance or on_trans > tolerance:
        raise IndicatorError(
            f"psi must be 1 on {cis!r} and 0 on {trans!r}; the mean-square departures are "
            f"{on_cis:.3e} and {on_trans:.3e} against a tolerance of {tolerance:.3e}. An "
            "inverted band flips the sign of every current and a band outside the domain "
            "makes them all zero"
        )
    logger.debug("psi separates %r from %r: %.2e, %.2e", cis, trans, on_cis, on_trans)

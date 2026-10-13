"""The domain indicator psi of the NUM-24 current form."""

from __future__ import annotations

import logging

from nanopnp.core.typing import Expression, GridFunction, Mesh
from nanopnp.mesh.primitives import ELECTROLYTE_DOMAINS, CylindricalPoreGeometry

__all__ = [
    "IndicatorError",
    "axial_indicator",
    "check_indicator",
    "lumen_band",
    "smoothstep",
]

logger = logging.getLogger(__name__)


class IndicatorError(ValueError):
    """The indicator does not separate the two reservoirs."""


def smoothstep(coordinate: Expression, *, lower_nm: float, upper_nm: float) -> Expression:
    """Return the cubic Hermite step of ``coordinate`` from ``lower_nm`` to ``upper_nm``."""
    import ngsolve as ngs

    width = upper_nm - lower_nm
    if not width > 0.0:
        raise IndicatorError(
            f"the transition band must have positive width, got lower={lower_nm} nm and "
            f"upper={upper_nm} nm; a zero-width band makes grad(psi) a delta that no "
            "quadrature rule can integrate"
        )
    raw = (coordinate - lower_nm) / width
    clamped = ngs.IfPos(raw, ngs.IfPos(raw - 1.0, 1.0, raw), 0.0)
    return clamped * clamped * (3.0 - 2.0 * clamped)


def lumen_band(geometry: CylindricalPoreGeometry, *, fraction: float = 0.8) -> tuple[float, float]:
    """Return the transition band across the middle of the pore lumen, in nm.

    Parameters
    ----------
    fraction
        Fraction of the membrane thickness the band occupies; IndicatorError unless in (0, 1].
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
    fluid: str | None = ELECTROLYTE_DOMAINS,
    cis: str = "cis",
    trans: str = "trans",
    check: bool = True,
) -> GridFunction:
    """Return the indicator psi, 0 below ``lower_nm`` and 1 above ``upper_nm``.

    Parameters
    ----------
    fluid
        Material-name regular expression the indicator lives on; None puts it over the whole mesh.
    check
        Whether to verify the result with ``check_indicator``.
    """
    import ngsolve as ngs

    space = (
        ngs.H1(mesh, order=order)
        if fluid is None
        else ngs.H1(mesh, order=order, definedon=mesh.Materials(fluid))
    )
    indicator = ngs.GridFunction(space, name="psi")
    indicator.Set(smoothstep(ngs.y, lower_nm=lower_nm, upper_nm=upper_nm))
    if check and _boundary_length(mesh, cis) > 0.0 and _boundary_length(mesh, trans) > 0.0:
        # Matched by measure: a regular-expression pattern is not itself a boundary name.
        check_indicator(indicator, mesh, cis=cis, trans=trans)
    return indicator


def _boundary_length(mesh: Mesh, boundary: str) -> float:
    import ngsolve as ngs

    return float(ngs.Integrate(ngs.CF(1.0), mesh, definedon=mesh.Boundaries(boundary)))


def check_indicator(
    indicator: GridFunction,
    mesh: Mesh,
    *,
    cis: str = "cis",
    trans: str = "trans",
    tolerance: float = 1e-12,
) -> None:
    """Assert that psi is 1 on the cis boundary and 0 on the trans boundary.

    Raises
    ------
    IndicatorError
        If either cap departs from its value by more than ``tolerance``.
    """
    import ngsolve as ngs

    def _mean_square(target: float, boundary: str) -> float:
        region = mesh.Boundaries(boundary)
        length = _boundary_length(mesh, boundary)
        if not length > 0.0:
            known = ", ".join(sorted(set(mesh.GetBoundaries())))
            raise IndicatorError(f"no boundary matching {boundary!r} in this mesh; it has {known}")
        deviation = float(ngs.Integrate((indicator - target) ** 2, mesh, definedon=region))
        return deviation / length

    on_cis = _mean_square(1.0, cis)
    on_trans = _mean_square(0.0, trans)
    if not on_cis <= tolerance or not on_trans <= tolerance:
        raise IndicatorError(
            f"psi must be 1 on {cis!r} and 0 on {trans!r}; the mean-square departures are "
            f"{on_cis:.3e} and {on_trans:.3e} against a tolerance of {tolerance:.3e}. An "
            "inverted band flips the sign of every current and a band outside the domain "
            "makes them all zero"
        )
    logger.debug("psi separates %r from %r: %.2e, %.2e", cis, trans, on_cis, on_trans)

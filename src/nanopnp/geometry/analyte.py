"""Rigid analyte bodies of revolution and the geometries that embed them (FR-21)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from nanopnp.core.constants import ELEMENTARY_CHARGE
from nanopnp.core.typing import Mesh, Shape
from nanopnp.geometry.tolerance import TOL_NM

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.mesh.primitives import CylindricalPoreGeometry

__all__ = [
    "ANALYTE_BOUNDARY",
    "ANALYTE_DOMAIN",
    "AnalyteBody",
    "AnalyteGeometryError",
    "AnalyteInBoxGeometry",
    "PoreWithAnalyte",
    "SphereBody",
    "SpheroidBody",
]

ANALYTE_DOMAIN = "analyte"

ANALYTE_BOUNDARY = "analyte"

NM3_PER_M3 = 1e27


class AnalyteGeometryError(ValueError):
    """The body and the domain it is to be embedded in are incompatible."""


class AnalyteBody(Protocol):
    """One rigid body of revolution on the symmetry axis."""

    @property
    def z_nm(self) -> float:
        """Axial position of the body's centre, in nm."""

    @property
    def bounding_radius_nm(self) -> float:
        """Largest radius the profile reaches, in nm."""

    @property
    def bounding_half_length_nm(self) -> float:
        """Largest departure from ``z_nm`` the profile reaches, in nm."""

    @property
    def volume_nm3(self) -> float:
        """Volume of the revolved body, in nm^3."""

    def charge_density_C_m3(self, charge_e: float) -> float:
        """Return the body's charge density ``q/V`` in C/m^3."""

    def face(self, *, maxh_nm: float | None = None) -> Shape:
        """Return the profile as a named OCC face, its surface edges named."""


def _named_profile(profile: Shape, body: AnalyteBody, maxh_nm: float | None) -> Shape:
    import netgen.occ as occ

    half_length = body.bounding_half_length_nm
    clip = occ.MoveTo(0.0, body.z_nm - half_length).Rectangle(
        body.bounding_radius_nm, 2.0 * half_length
    )
    face = profile * clip.Face()
    face.name = ANALYTE_DOMAIN
    for edge in face.edges:
        if abs(edge.center[0]) < TOL_NM:
            continue
        edge.name = ANALYTE_BOUNDARY
        if maxh_nm is not None:
            edge.maxh = maxh_nm
    return face


def _charge_density_C_m3(volume_nm3: float, charge_e: float) -> float:
    return charge_e * ELEMENTARY_CHARGE / (volume_nm3 / NM3_PER_M3)


@dataclass(frozen=True)
class SphereBody:
    """A sphere of radius ``radius_nm`` centred on the axis at ``z_nm``."""

    radius_nm: float
    z_nm: float = 0.0

    def __post_init__(self) -> None:
        if not self.radius_nm > 0.0:
            raise AnalyteGeometryError(f"radius_nm must be positive, got {self.radius_nm} nm")

    @property
    def bounding_radius_nm(self) -> float:
        """Largest radius the profile reaches, in nm."""
        return self.radius_nm

    @property
    def bounding_half_length_nm(self) -> float:
        """Largest departure from ``z_nm`` the profile reaches, in nm."""
        return self.radius_nm

    @property
    def volume_nm3(self) -> float:
        """``4/3 pi a^3``."""
        return 4.0 / 3.0 * math.pi * self.radius_nm**3

    def charge_density_C_m3(self, charge_e: float) -> float:
        """Return the body's charge density ``q/V`` in C/m^3."""
        return _charge_density_C_m3(self.volume_nm3, charge_e)

    def face(self, *, maxh_nm: float | None = None) -> Shape:
        """Return the profile as a named OCC face, its surface edges named."""
        import netgen.occ as occ

        disc = occ.WorkPlane().Circle(0.0, self.z_nm, self.radius_nm).Face()
        return _named_profile(disc, self, maxh_nm)


@dataclass(frozen=True)
class SpheroidBody:
    """A spheroid with semi-axes ``semi_radial_nm`` and ``semi_axial_nm``."""

    semi_radial_nm: float
    semi_axial_nm: float
    z_nm: float = 0.0

    def __post_init__(self) -> None:
        for name in ("semi_radial_nm", "semi_axial_nm"):
            value = float(getattr(self, name))
            if not value > 0.0:
                raise AnalyteGeometryError(f"{name} must be positive, got {value} nm")

    @property
    def bounding_radius_nm(self) -> float:
        """Largest radius the profile reaches, in nm."""
        return self.semi_radial_nm

    @property
    def bounding_half_length_nm(self) -> float:
        """Largest departure from ``z_nm`` the profile reaches, in nm."""
        return self.semi_axial_nm

    @property
    def volume_nm3(self) -> float:
        """``4/3 pi b^2 c`` with ``b`` the radial and ``c`` the axial semi-axis."""
        return 4.0 / 3.0 * math.pi * self.semi_radial_nm**2 * self.semi_axial_nm

    def charge_density_C_m3(self, charge_e: float) -> float:
        """Return the body's charge density ``q/V`` in C/m^3."""
        return _charge_density_C_m3(self.volume_nm3, charge_e)

    def face(self, *, maxh_nm: float | None = None) -> Shape:
        """Return the profile as a named OCC face, its surface edges named."""
        import netgen.occ as occ

        plane = occ.WorkPlane().MoveTo(0.0, self.z_nm)
        if self.semi_axial_nm > self.semi_radial_nm:
            # ``Ellipse`` lays its major axis along the current direction and
            # refuses a minor axis longer than the major, so a prolate body is
            # the same ellipse with the plane turned a quarter turn.
            ellipse = plane.Rotate(90).Ellipse(self.semi_axial_nm, self.semi_radial_nm)
        else:
            ellipse = plane.Ellipse(self.semi_radial_nm, self.semi_axial_nm)
        return _named_profile(ellipse.Face(), self, maxh_nm)


@dataclass(frozen=True)
class AnalyteInBoxGeometry:
    """A body of revolution alone in a half-disc of electrolyte.

    The medium is truncated at ``outer_radius_nm``, far from the body. The boundaries are
    ``axis``, ``analyte`` and ``outer``; the fluid is ``electrolyte``.
    """

    body: AnalyteBody
    outer_radius_nm: float = 10.0

    def __post_init__(self) -> None:
        reach = math.hypot(
            self.body.bounding_radius_nm,
            abs(self.body.z_nm) + self.body.bounding_half_length_nm,
        )
        if not reach < self.outer_radius_nm - TOL_NM:
            raise AnalyteGeometryError(
                f"the body reaches {reach:.4g} nm from the origin but the domain ends at "
                f"{self.outer_radius_nm:.4g} nm; a body touching the outer boundary makes the "
                "far field it carries meaningless and the mesh degenerate"
            )

    def shape(self, *, wall_h_nm: float | None = None) -> Shape:
        """Return the glued, fully named shape, unmeshed."""
        import netgen.occ as occ

        radius = self.outer_radius_nm
        disc = occ.WorkPlane().Circle(0.0, 0.0, radius).Face()
        fluid = disc * occ.MoveTo(0.0, -radius).Rectangle(radius, 2.0 * radius).Face()
        body = self.body.face(maxh_nm=wall_h_nm)
        fluid = fluid - body
        fluid.name = "electrolyte"
        glued = occ.Glue([fluid, body])
        for edge in glued.edges:
            if edge.name is not None:
                continue
            edge.name = "axis" if abs(edge.center[0]) < TOL_NM else "outer"
        return glued

    def generate(self, *, maxh_nm: float, wall_h_nm: float | None = None) -> Mesh:
        """Return the meshed geometry with named domains and boundaries."""
        import netgen.occ as occ
        import ngsolve as ngs

        geometry = occ.OCCGeometry(self.shape(wall_h_nm=wall_h_nm), dim=2)
        return ngs.Mesh(geometry.GenerateMesh(maxh=maxh_nm, grading=0.2))


@dataclass(frozen=True)
class PoreWithAnalyte:
    """A body of revolution held in the lumen of the analytic cylindrical pore.

    The pore's boundary vocabulary survives, and ``analyte`` is added.
    """

    pore: CylindricalPoreGeometry
    body: AnalyteBody
    analyte_h_nm: float | None = None

    def __post_init__(self) -> None:
        if not self.body.bounding_radius_nm < self.pore.pore_radius_nm - TOL_NM:
            raise AnalyteGeometryError(
                f"the body reaches r = {self.body.bounding_radius_nm:.4g} nm but the lumen ends "
                f"at {self.pore.pore_radius_nm:.4g} nm; a body touching the wall leaves no fluid "
                "to carry the flow and no surface to take a force over"
            )
        span = abs(self.body.z_nm) + self.body.bounding_half_length_nm
        if not span < self.pore.half_thickness_nm - TOL_NM:
            raise AnalyteGeometryError(
                f"the body spans to |z| = {span:.4g} nm but the lumen ends at "
                f"{self.pore.half_thickness_nm:.4g} nm; a body crossing a pore mouth is not the "
                "geometry this benchmark poses"
            )

    def shape(self, *, wall_h_nm: float | None = None) -> Shape:
        """Return the glued, fully named shape, unmeshed."""
        import netgen.occ as occ

        lumen, membrane, cis, trans = self.pore.faces()
        body = self.body.face(maxh_nm=self.analyte_h_nm)
        lumen = lumen - body
        lumen.name = "electrolyte"
        glued = occ.Glue([lumen, body, membrane, cis, trans])
        self.pore.name_edges(glued, wall_h_nm=wall_h_nm)
        return glued

    def generate(self, *, maxh_nm: float, wall_h_nm: float | None = None) -> Mesh:
        """Return the meshed geometry with named domains and boundaries."""
        import netgen.occ as occ
        import ngsolve as ngs

        geometry = occ.OCCGeometry(self.shape(wall_h_nm=wall_h_nm), dim=2)
        return ngs.Mesh(geometry.GenerateMesh(maxh=maxh_nm, grading=0.2))

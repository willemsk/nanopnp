"""Rigid analyte bodies of revolution, and the geometries that embed them (FR-21).

Phase 0 needs an analyte for one reason: VER-19 to VER-22 are the four
outstanding benchmarks of exit criterion 1 and every one of them is a force on an
embedded body. Amendment A1 pulls that much of FR-21 and FR-22 into the spike
"to the extent the benchmarks exercise them"; the case-file surface for analytes
is v1.0 work and is not here.

**The body is a named domain, glued, not a hole.** Poisson is solved over all of
Omega with a piecewise permittivity, so the dielectric jump PHY-09 asks for *is*
a material entry — ``solid_permittivities={"analyte": eps_p}`` — and nothing else
about the coupled model has to change. The fluid regular expression
``ELECTROLYTE_DOMAINS`` matches a material name in full and so already excludes
``analyte``, which makes ``n.J_i = 0`` on the body natural rather than something
to impose; only the no-slip condition is essential, and that is a boundary name
in ``CoupledBoundaries.velocity``. Section 5.2.3 rejects level-set and immersed
boundary treatments outright, and author ruling 4 of ``.knowledge/00-index.md``
confirms the trio: no flux, no slip, dielectric jump.

CON-02 restricts v1 to bodies of revolution on the axis, so a body is a profile
in the ``(r, z)`` half-plane revolved about ``r = 0``: a half-disc for a sphere,
a half-ellipse for a spheroid. The revolved-polyline profile a contour-derived
body would need is deferred rather than designed around.

Two mechanics are worth naming because both are silent when wrong.

**The body's edges are named before the boolean.** The classifier of
:meth:`~nanopnp.mesh.primitives.CylindricalPoreGeometry.name_edges` matches on
edge position, so a body surface inside the lumen would fall through it to
NGSolve's ``default`` — or worse, be swept into ``wall`` — and the force integral
would then be taken over the wrong boundary. OCC propagates edge names through a
cut and a glue [tested], and the classifier now skips an edge that already has a
name, so pre-naming is enough. The one edge deliberately left unnamed is the
body's own segment on ``r = 0``: it is part of the axis, and the classifier calls
it ``axis``, which is where NUM-06 imposes ``u_r = 0``.

**The body is graded like the pore wall.** WP5's finding was that the NUM-30 wall
resolution decides *whether the continuation ladder converges*, not merely how
accurate the answer is. A charged body sitting in its own double layer is the
same situation, so ``analyte_h_nm`` exists and defaults to nothing rather than to
the global size.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Protocol

from nanopnp.core.constants import ELEMENTARY_CHARGE
from nanopnp.core.typing import Mesh, Shape
from nanopnp.mesh.primitives import TOL_NM, CylindricalPoreGeometry

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
"""Material name of the body. ``ELECTROLYTE_DOMAINS`` deliberately excludes it."""

ANALYTE_BOUNDARY = "analyte"
"""Boundary name of the body's surface.

The same string as :data:`ANALYTE_DOMAIN` and separately named because the two
live in different namespaces — ``mesh.Materials`` and ``mesh.Boundaries`` — and
a call site reads better saying which one it means. ``membrane`` is already both
in :mod:`nanopnp.mesh.primitives`.
"""

NM3_PER_M3 = 1e27
"""Cubic nanometres per cubic metre; volumes cross this boundary here only."""


class AnalyteGeometryError(ValueError):
    """The body and the domain it is to be embedded in are incompatible.

    Raised rather than left to the mesher, which answers a body larger than its
    lumen with slivers, a negative-area face or a mesh that is simply wrong in a
    region no assertion looks at (QR-12).
    """


class AnalyteBody(Protocol):
    """One rigid body of revolution on the symmetry axis (FR-21, CON-02)."""

    @property
    def z_nm(self) -> float:
        """Axial position of the body's centre, in nm."""
        ...

    @property
    def bounding_radius_nm(self) -> float:
        """Largest radius the profile reaches, in nm."""
        ...

    @property
    def bounding_half_length_nm(self) -> float:
        """Largest departure from ``z_nm`` the profile reaches, in nm."""
        ...

    @property
    def volume_nm3(self) -> float:
        """Volume of the revolved body, in nm^3."""
        ...

    def face(self, *, maxh_nm: float | None = None) -> Shape:
        """Return the profile as a named OCC face, its surface edges named."""
        ...


def _named_profile(profile: Shape, body: AnalyteBody, maxh_nm: float | None) -> Shape:
    """Return ``profile`` clipped to ``r >= 0``, named, and graded.

    Every edge is named ``analyte`` except the segment on the axis, which is left
    for the embedding geometry's own classifier to call ``axis``; see the module
    docstring.
    """
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
    """Return ``rho_part = q / V`` in C/m^3 for a uniformly charged body.

    The reference continuum treatment of a protein analyte smears its net charge
    uniformly over its own volume (``.knowledge/05-analyte-and-forces.md``
    section 10.3); a surface charge on an analyte has no textual support anywhere
    and is therefore available but never a default.
    """
    return charge_e * ELEMENTARY_CHARGE / (volume_nm3 / NM3_PER_M3)


@dataclass(frozen=True)
class SphereBody:
    """A sphere of radius ``radius_nm`` centred on the axis at ``z_nm``.

    The body of VER-19 (Stokes drag), VER-20 (Maxwell stress) and VER-21
    (electrophoretic mobility): every one of those closed forms is a sphere's.
    """

    radius_nm: float
    z_nm: float = 0.0

    def __post_init__(self) -> None:
        """Reject a body with no volume.

        Raises
        ------
        AnalyteGeometryError
            If the radius is not positive.
        """
        if self.radius_nm <= 0.0:
            raise AnalyteGeometryError(f"radius_nm must be positive, got {self.radius_nm} nm")

    @property
    def bounding_radius_nm(self) -> float:  # noqa: D102 - documented on the protocol
        return self.radius_nm

    @property
    def bounding_half_length_nm(self) -> float:  # noqa: D102
        return self.radius_nm

    @property
    def volume_nm3(self) -> float:
        """``4/3 pi a^3``."""
        return 4.0 / 3.0 * math.pi * self.radius_nm**3

    def charge_density_C_m3(self, charge_e: float) -> float:
        """Return ``rho_part = q/V`` in C/m^3; see :func:`_charge_density_C_m3`."""
        return _charge_density_C_m3(self.volume_nm3, charge_e)

    def face(self, *, maxh_nm: float | None = None) -> Shape:  # noqa: D102
        import netgen.occ as occ

        disc = occ.WorkPlane().Circle(0.0, self.z_nm, self.radius_nm).Face()
        return _named_profile(disc, self, maxh_nm)


@dataclass(frozen=True)
class SpheroidBody:
    """A spheroid with semi-axes ``semi_radial_nm`` and ``semi_axial_nm``.

    The shape a globular protein is idealised as: PlyAB's haemoglobin reference
    is 6.7 nm along the axis by 5.8 nm across (``.knowledge/05`` section 10).
    Prolate and oblate are both permitted; a sphere is the degenerate case and
    :class:`SphereBody` is the same body written more plainly.
    """

    semi_radial_nm: float
    semi_axial_nm: float
    z_nm: float = 0.0

    def __post_init__(self) -> None:
        """Reject a body with no volume.

        Raises
        ------
        AnalyteGeometryError
            If either semi-axis is not positive.
        """
        for name in ("semi_radial_nm", "semi_axial_nm"):
            value = float(getattr(self, name))
            if value <= 0.0:
                raise AnalyteGeometryError(f"{name} must be positive, got {value} nm")

    @property
    def bounding_radius_nm(self) -> float:  # noqa: D102 - documented on the protocol
        return self.semi_radial_nm

    @property
    def bounding_half_length_nm(self) -> float:  # noqa: D102
        return self.semi_axial_nm

    @property
    def volume_nm3(self) -> float:
        """``4/3 pi b^2 c`` with ``b`` the radial and ``c`` the axial semi-axis."""
        return 4.0 / 3.0 * math.pi * self.semi_radial_nm**2 * self.semi_axial_nm

    def charge_density_C_m3(self, charge_e: float) -> float:
        """Return ``rho_part = q/V`` in C/m^3; see :func:`_charge_density_C_m3`."""
        return _charge_density_C_m3(self.volume_nm3, charge_e)

    def face(self, *, maxh_nm: float | None = None) -> Shape:  # noqa: D102
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

    The benchmark domain of VER-19 to VER-22: an unbounded medium truncated at
    ``outer_radius_nm``, with the body on the axis at its centre. The truncation
    is deliberately far — the plan sizes it at ten body radii — and VER-19
    imposes the closed-form Stokes far field on ``outer`` rather than a uniform
    stream, so that the benchmark measures discretisation error and not the
    Faxen wall correction of order ``a/R`` that a bounded domain otherwise adds.

    Boundaries are ``axis`` (``r = 0``, including the body's own segment of it),
    ``analyte`` (the body's surface) and ``outer``. The fluid is ``electrolyte``,
    so ``ELECTROLYTE_DOMAINS`` selects it and not the body.
    """

    body: AnalyteBody
    outer_radius_nm: float = 10.0

    def __post_init__(self) -> None:
        """Reject a body that does not fit strictly inside the half-disc.

        The test is against the far corner of the body's bounding rectangle, so
        it is conservative for anything but a cylinder — a sphere of radius
        ``a`` is admitted only out to ``R > a sqrt(2)``. That is the right way to
        be wrong here: the alternative is a mesher answering an escaping body
        with slivers rather than with an error (QR-12).

        Raises
        ------
        AnalyteGeometryError
            If the body reaches or crosses the outer boundary.
        """
        reach = math.hypot(
            self.body.bounding_radius_nm,
            abs(self.body.z_nm) + self.body.bounding_half_length_nm,
        )
        if reach >= self.outer_radius_nm - TOL_NM:
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
        """Return the meshed geometry with named domains and boundaries.

        Parameters
        ----------
        maxh_nm
            Global maximum element size, in nm.
        wall_h_nm
            Element size on the analyte surface, in nm — the only wall this
            geometry has. NUM-30 asks for about ``lambda_D / 5`` on a boundary
            carrying a double layer.
        """
        import netgen.occ as occ
        import ngsolve as ngs

        geometry = occ.OCCGeometry(self.shape(wall_h_nm=wall_h_nm), dim=2)
        return ngs.Mesh(geometry.GenerateMesh(maxh=maxh_nm, grading=0.2))


@dataclass(frozen=True)
class PoreWithAnalyte:
    """A body of revolution held in the lumen of the analytic cylindrical pore.

    The reference-shaped case: everything VER-22's cheap gate leaves out, and the
    configuration RSK-04 is stated on. The pore's whole vocabulary — ``axis``,
    ``wall``, ``membrane``, ``membrane_outer``, ``cis``, ``trans`` and the three
    fluid domains — survives untouched, so ``lumen_band``, ``axial_indicator``
    and the default :class:`~nanopnp.physics.models.CoupledBoundaries` keep
    working and only ``analyte`` is new.
    """

    pore: CylindricalPoreGeometry
    body: AnalyteBody
    analyte_h_nm: float | None = None

    def __post_init__(self) -> None:
        """Reject a body that does not fit strictly inside the lumen.

        Exact here, the lumen being a rectangle: the body clears the wall if its
        bounding radius does, and clears both mouths if its bounding span does.

        Raises
        ------
        AnalyteGeometryError
            If the body touches or crosses the pore wall or either mouth.
        """
        if self.body.bounding_radius_nm >= self.pore.pore_radius_nm - TOL_NM:
            raise AnalyteGeometryError(
                f"the body reaches r = {self.body.bounding_radius_nm:.4g} nm but the lumen ends "
                f"at {self.pore.pore_radius_nm:.4g} nm; a body touching the wall leaves no fluid "
                "to carry the flow and no surface to take a force over"
            )
        span = abs(self.body.z_nm) + self.body.bounding_half_length_nm
        if span >= self.pore.half_thickness_nm - TOL_NM:
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
        """Return the meshed geometry with named domains and boundaries.

        Parameters
        ----------
        maxh_nm
            Global maximum element size, in nm.
        wall_h_nm
            Element size on the pore wall, in nm (NUM-30). The body's own size is
            ``analyte_h_nm``, set on the geometry, because the two surfaces are
            resolved for different reasons and in the reference-shaped case sit a
            fraction of a nanometre apart.
        """
        import netgen.occ as occ
        import ngsolve as ngs

        geometry = occ.OCCGeometry(self.shape(wall_h_nm=wall_h_nm), dim=2)
        return ngs.Mesh(geometry.GenerateMesh(maxh=maxh_nm, grading=0.2))

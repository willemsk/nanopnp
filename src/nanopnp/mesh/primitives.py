"""Analytic benchmark and spike geometries in the (r, z) half-plane.

Phase 0 works on shapes that have closed-form solutions or a published target:
a planar slab for Gouy-Chapman, a cylinder for Debye-Hueckel, and the analytic
cylindrical pore through a membrane for the coupled solve and the Maxwell-Hall
access conductance. The geometry pipeline that builds a pore from a density
contour is Phase 2 (FR-07 to FR-09) and does not belong here.

Lengths are in **nanometres** throughout. The corrections are fitted in nm
(``d_bar = d/(1 nm)``) and the Debye length at the salt concentrations of
interest is a fraction of a nanometre, so a nm-scaled mesh keeps both the
geometry and the coefficient fields at O(1) and avoids the conditioning penalty
of metre-scaled coordinates.

Boundary names are stable across the geometries, because the weak forms and the
benchmarks select on them:

``axis``
    ``r = 0``. Carries no essential condition except ``u_r = 0`` (NUM-06).
``wall``
    The pore boundary. The only source of the wall-distance field (PHY-02).
``membrane``
    The bilayer surfaces. Deliberately *not* a distance source.
``cis``, ``trans``
    The outer reservoir boundaries, where the bias is applied.

``CylindricalPoreGeometry`` additionally carries ``membrane_outer`` (the outer
rim of the bilayer annulus) and leaves the two pore-mouth interfaces at
NGSolve's ``default``.

**Domain** names are a separate namespace from boundary names, and the pore
geometry reuses ``cis`` and ``trans`` in both. Its fluid is therefore *three*
domains - ``electrolyte`` for the lumen and ``cis``/``trans`` for the reservoirs
- so ``Materials("electrolyte")`` selects the lumen alone. Select the fluid with
``ELECTROLYTE_DOMAINS``.
"""

from __future__ import annotations

from dataclasses import dataclass

from nanopnp.core.typing import Mesh, Shape

TOL_NM = 1e-9
"""Geometric tolerance for classifying an edge by its centre of mass.

Public because :mod:`nanopnp.geometry.analyte` classifies against the same
tolerance when it embeds a body in one of these geometries; two tolerances that
can drift apart would put an edge in one geometry's vocabulary and not the
other's.
"""

ELECTROLYTE_DOMAINS = "electrolyte|cis|trans"
"""Regular expression selecting every fluid domain of these geometries.

Nernst-Planck and Navier-Stokes are solved on the electrolyte only, so their
forms select on this rather than on ``"electrolyte"``. NGSolve matches a
material regular expression in full, and ``CylindricalPoreGeometry`` names its
two reservoirs ``cis`` and ``trans`` so that a reservoir can be addressed on its
own; ``Materials("electrolyte")`` would therefore silently drop both of them and
leave a solve with no ions and no flow outside the lumen.
"""


@dataclass(frozen=True)
class SlabGeometry:
    """A planar slab of electrolyte against a charged wall.

    The wall is at ``x = 0`` and the bulk at ``x = width_nm``; the ``y`` extent
    is an artefact of solving a one-dimensional problem on a two-dimensional
    mesh, and its boundaries carry natural conditions.
    """

    width_nm: float
    height_nm: float = 1.0

    def generate(self, *, maxh_nm: float, wall_h_nm: float | None = None) -> Mesh:
        """Return a meshed slab, graded towards the wall if ``wall_h_nm`` is given."""
        import netgen.occ as occ
        import ngsolve as ngs

        face = occ.Rectangle(self.width_nm, self.height_nm).Face()
        face.name = "electrolyte"
        for edge in face.edges:
            centre = edge.center
            if abs(centre[0]) < TOL_NM:
                edge.name = "wall"
                if wall_h_nm is not None:
                    edge.maxh = wall_h_nm
            elif abs(centre[0] - self.width_nm) < TOL_NM:
                edge.name = "bulk"
            else:
                edge.name = "lateral"
        return ngs.Mesh(occ.OCCGeometry(face, dim=2).GenerateMesh(maxh=maxh_nm, grading=0.2))


@dataclass(frozen=True)
class CylinderGeometry:
    """An axisymmetric cylinder of electrolyte, ``0 <= r <= radius_nm``.

    The axis edge is named so that a test can confirm nothing essential is
    imposed there; the ends carry natural conditions, which is consistent with
    the z-independent Debye-Hueckel solution.
    """

    radius_nm: float
    length_nm: float

    def generate(self, *, maxh_nm: float, wall_h_nm: float | None = None) -> Mesh:
        """Return a meshed cylinder cross-section, graded towards the wall."""
        import netgen.occ as occ
        import ngsolve as ngs

        face = occ.Rectangle(self.radius_nm, self.length_nm).Face()
        face.name = "electrolyte"
        for edge in face.edges:
            centre = edge.center
            if abs(centre[0]) < TOL_NM:
                edge.name = "axis"
            elif abs(centre[0] - self.radius_nm) < TOL_NM:
                edge.name = "wall"
                if wall_h_nm is not None:
                    edge.maxh = wall_h_nm
            else:
                edge.name = "end"
        return ngs.Mesh(occ.OCCGeometry(face, dim=2).GenerateMesh(maxh=maxh_nm, grading=0.2))


@dataclass(frozen=True)
class CylindricalPoreGeometry:
    """A cylindrical pore through a membrane, with a reservoir on each side.

    The idealised stand-in for ClyA used through Phase 0: a straight lumen of
    radius ``pore_radius_nm`` and length ``membrane_thickness_nm``, a solid
    membrane annulus around it, and a quarter-disc reservoir either side. It
    carries the features the solver must handle - an axis, a wall the distance
    field measures from, a membrane that it must *not* measure from, and the
    reservoir-to-pore transition where the access resistance lives - without any
    of the contour machinery of Phase 2.

    The lumen is the domain ``electrolyte`` and the reservoirs are ``cis`` and
    ``trans``, so the fluid is selected with ``ELECTROLYTE_DOMAINS`` and not with
    ``"electrolyte"``.
    """

    pore_radius_nm: float = 2.0
    membrane_thickness_nm: float = 13.0
    reservoir_radius_nm: float = 50.0

    @property
    def half_thickness_nm(self) -> float:
        """Half the membrane thickness; the lumen spans ``+/- half_thickness_nm``."""
        return 0.5 * self.membrane_thickness_nm

    def faces(self) -> tuple[Shape, Shape, Shape, Shape]:
        """Return the four named faces — lumen, membrane, cis, trans — unglued.

        Public so that a geometry embedding something *in* the lumen can cut the
        body out of that face before the glue, rather than copying this
        construction. :class:`nanopnp.geometry.analyte.PoreWithAnalyte` is the
        only such caller in Phase 0; the lumen is returned first for it.
        """
        import netgen.occ as occ

        half = self.half_thickness_nm
        radius = self.reservoir_radius_nm
        lumen = (
            occ.MoveTo(0, -half).Rectangle(self.pore_radius_nm, self.membrane_thickness_nm).Face()
        )
        lumen.name = "electrolyte"
        membrane = (
            occ.MoveTo(self.pore_radius_nm, -half)
            .Rectangle(radius - self.pore_radius_nm, self.membrane_thickness_nm)
            .Face()
        )
        membrane.name = "membrane"
        reservoirs = []
        for side, sign in (("cis", 1.0), ("trans", -1.0)):
            centre_z = sign * half
            disc = occ.WorkPlane().Circle(0.0, centre_z, radius).Face()
            box = (
                occ.MoveTo(0, centre_z).Rectangle(radius, radius).Face()
                if sign > 0
                else occ.MoveTo(0, centre_z - radius).Rectangle(radius, radius).Face()
            )
            half_disc = disc * box
            half_disc.name = side
            reservoirs.append(half_disc)
        return lumen, membrane, reservoirs[0], reservoirs[1]

    def name_edges(self, shape: Shape, *, wall_h_nm: float | None = None) -> None:
        """Name every **unnamed** edge of ``shape`` by its centre of mass, in place.

        An edge that already carries a name is left alone. The chain below is
        unconditional and matches on position, so an edge belonging to something
        this geometry does not know about — the surface of an embedded analyte —
        would otherwise be swept into ``cis`` or dropped to NGSolve's
        ``default``. Names survive an OCC boolean and a glue [tested], so
        pre-naming the intruder and skipping it here is enough to keep the two
        vocabularies apart.

        The one edge deliberately left to this chain is the body's own segment
        on ``r = 0``: it is part of the axis, and calling it anything else would
        take it out of the ``axis`` region that NUM-06 imposes ``u_r = 0`` on.
        """
        half = self.half_thickness_nm
        radius = self.reservoir_radius_nm
        for edge in shape.edges:
            if edge.name is not None:
                continue
            centre = edge.center
            r_c, z_c = centre[0], centre[1]
            on_axis = abs(r_c) < TOL_NM
            inside_membrane_span = abs(z_c) < half - TOL_NM
            if on_axis:
                edge.name = "axis"
            elif abs(r_c - self.pore_radius_nm) < TOL_NM and inside_membrane_span:
                edge.name = "wall"
                if wall_h_nm is not None:
                    edge.maxh = wall_h_nm
            elif abs(abs(z_c) - half) < TOL_NM and r_c > self.pore_radius_nm + TOL_NM:
                edge.name = "membrane"
            elif abs(r_c - radius) < TOL_NM and inside_membrane_span:
                edge.name = "membrane_outer"
            elif z_c > half:
                edge.name = "cis"
            elif z_c < -half:
                edge.name = "trans"

    def shape(self, *, wall_h_nm: float | None = None) -> Shape:
        """Return the glued, fully named shape, unmeshed."""
        import netgen.occ as occ

        glued = occ.Glue(list(self.faces()))
        self.name_edges(glued, wall_h_nm=wall_h_nm)
        return glued

    def generate(self, *, maxh_nm: float, wall_h_nm: float | None = None) -> Mesh:
        """Return the meshed geometry with named domains and boundaries.

        Parameters
        ----------
        maxh_nm
            Global maximum element size, in nm.
        wall_h_nm
            Element size on the pore wall, in nm; NUM-30 asks for about
            ``lambda_D / 5`` there.
        """
        import netgen.occ as occ
        import ngsolve as ngs

        geometry = occ.OCCGeometry(self.shape(wall_h_nm=wall_h_nm), dim=2)
        return ngs.Mesh(geometry.GenerateMesh(maxh=maxh_nm, grading=0.2))

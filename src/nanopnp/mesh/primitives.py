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
"""

from __future__ import annotations

from dataclasses import dataclass

from nanopnp.core.typing import Mesh

_TOL_NM = 1e-9
"""Geometric tolerance for classifying an edge by its centre of mass."""


@dataclass(frozen=True)
class SlabGeometry:
    """A planar slab of electrolyte against a charged wall.

    The wall is at ``x = 0`` and the bulk at ``x = width``; the ``y`` extent is
    an artefact of solving a one-dimensional problem on a two-dimensional mesh,
    and its boundaries carry natural conditions.
    """

    width: float
    height: float = 1.0

    def generate(self, *, maxh: float, wall_h: float | None = None) -> Mesh:
        """Return a meshed slab, graded towards the wall if ``wall_h`` is given."""
        import netgen.occ as occ
        import ngsolve as ngs

        face = occ.Rectangle(self.width, self.height).Face()
        face.name = "electrolyte"
        for edge in face.edges:
            centre = edge.center
            if abs(centre[0]) < _TOL_NM:
                edge.name = "wall"
                if wall_h is not None:
                    edge.maxh = wall_h
            elif abs(centre[0] - self.width) < _TOL_NM:
                edge.name = "bulk"
            else:
                edge.name = "lateral"
        return ngs.Mesh(occ.OCCGeometry(face, dim=2).GenerateMesh(maxh=maxh, grading=0.2))


@dataclass(frozen=True)
class CylinderGeometry:
    """An axisymmetric cylinder of electrolyte, ``0 <= r <= radius``.

    The axis edge is named so that a test can confirm nothing essential is
    imposed there; the ends carry natural conditions, which is consistent with
    the z-independent Debye-Hueckel solution.
    """

    radius: float
    length: float

    def generate(self, *, maxh: float, wall_h: float | None = None) -> Mesh:
        """Return a meshed cylinder cross-section, graded towards the wall."""
        import netgen.occ as occ
        import ngsolve as ngs

        face = occ.Rectangle(self.radius, self.length).Face()
        face.name = "electrolyte"
        for edge in face.edges:
            centre = edge.center
            if abs(centre[0]) < _TOL_NM:
                edge.name = "axis"
            elif abs(centre[0] - self.radius) < _TOL_NM:
                edge.name = "wall"
                if wall_h is not None:
                    edge.maxh = wall_h
            else:
                edge.name = "end"
        return ngs.Mesh(occ.OCCGeometry(face, dim=2).GenerateMesh(maxh=maxh, grading=0.2))


@dataclass(frozen=True)
class CylindricalPoreGeometry:
    """A cylindrical pore through a membrane, with a reservoir on each side.

    The idealised stand-in for ClyA used through Phase 0: a straight lumen of
    radius ``pore_radius`` and length ``membrane_thickness``, a solid membrane
    annulus around it, and a half-disc reservoir either side. It carries the
    features the solver must handle - an axis, a wall the distance field
    measures from, a membrane that it must *not* measure from, and the
    reservoir-to-pore transition where the access resistance lives - without any
    of the contour machinery of Phase 2.
    """

    pore_radius: float = 2.0
    membrane_thickness: float = 13.0
    reservoir_radius: float = 50.0

    @property
    def half_thickness(self) -> float:
        """Half the membrane thickness; the lumen spans ``+/- half_thickness``."""
        return 0.5 * self.membrane_thickness

    def generate(self, *, maxh: float, wall_h: float | None = None) -> Mesh:
        """Return the meshed geometry with named domains and boundaries.

        Parameters
        ----------
        maxh
            Global maximum element size, in nm.
        wall_h
            Element size on the pore wall, in nm; NUM-30 asks for about
            ``lambda_D / 5`` there.
        """
        import netgen.occ as occ
        import ngsolve as ngs

        half = self.half_thickness
        radius = self.reservoir_radius
        lumen = occ.MoveTo(0, -half).Rectangle(self.pore_radius, self.membrane_thickness).Face()
        lumen.name = "electrolyte"
        membrane = (
            occ.MoveTo(self.pore_radius, -half)
            .Rectangle(radius - self.pore_radius, self.membrane_thickness)
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
            reservoirs.append((side, sign, half_disc))

        shape = occ.Glue([lumen, membrane, *(r[2] for r in reservoirs)])
        for edge in shape.edges:
            centre = edge.center
            r_c, z_c = centre[0], centre[1]
            on_axis = abs(r_c) < _TOL_NM
            inside_membrane_span = abs(z_c) < half - _TOL_NM
            if on_axis:
                edge.name = "axis"
            elif abs(r_c - self.pore_radius) < _TOL_NM and inside_membrane_span:
                edge.name = "wall"
                if wall_h is not None:
                    edge.maxh = wall_h
            elif abs(abs(z_c) - half) < _TOL_NM and r_c > self.pore_radius + _TOL_NM:
                edge.name = "membrane"
            elif abs(r_c - radius) < _TOL_NM and inside_membrane_span:
                edge.name = "membrane_outer"
            elif z_c > half:
                edge.name = "cis"
            elif z_c < -half:
                edge.name = "trans"
        geometry = occ.OCCGeometry(shape, dim=2)
        return ngs.Mesh(geometry.GenerateMesh(maxh=maxh, grading=0.2))

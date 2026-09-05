"""The ClyA reference geometry, assembled from a supplied pore profile (FR-09).

This is the CAD half of FR-09 and nothing more. The contour that becomes the
pore polygon is produced by the Phase-2 density and marching-squares pipeline
(FR-07, FR-08); here the polygon arrives as a validated fixture
(:mod:`nanopnp.mesh.profile`) and the job is to put a region around it: a
reservoir, a bilayer, and a conformal junction between the three.

The region, all lengths in nm and all from section 5.2.1, section 5.2.2 and
``.knowledge/04`` section 2:

============  ===============================================================
Reservoir     half-disc ``r in [0, 250]``, ``r^2 + z^2 <= 250^2``; the outer
              arc splits at ``z = 0`` into ``cis`` above and ``trans`` below
Membrane      quadrilateral ``(2, -1.4), (3.5, +1.4), (250, +1.4),
              (250, -1.4)``; thickness 2.8, mid-plane ``z = 0``
Pore          the fixture's closed polygon, ``z in [-1.85, 12.25]``,
              ``r in [1.65, 5.66]``
============  ===============================================================

Two features of that table are easy to get wrong and both are gated here.

**The membrane's inner edge is buried.** It slants from ``r = 2.0`` at
``z = -1.4`` to ``r = 3.5`` at ``z = +1.4``, and measured against the delivered
ClyA table it lies *inside* the pore body along its whole length [tested]: the
pore's outer surface is at ``r = 2.7524`` on the lower plane and ``r = 4.88`` on
the upper, so the drawn corners are 0.275 nm and 0.540 nm in. The slant is not
decoration - the lumen wall passes through ``(2.0, 0)`` and has opened to
``r = 2.96`` by ``z = +1.4``, so a vertical inner edge at ``r = 2`` would put
membrane material inside the electrolyte for every ``z > 0``. The assembly is
therefore a **boolean subtraction**: the membrane is the quadrilateral minus the
pore body, meeting the pore on the pore's own outer surface wherever that runs.
There is nothing to make coincide, and a gate written against the drawn corners
asserts the wrong numbers. :meth:`ReferenceGeometry.junction_report` asserts the
cut radii the polygon actually gives, read from the fixture (VER-28).

**There are three domains, not four.** The cap's underside is re-entrant - the
delivered boundary runs inward from ``(4.29, -0.7)`` to ``(3.33, -0.14)``, back
out to ``(3.48, 0.15)`` and over a closed top at ``z ~ 0.26`` - so the membrane
fills a cleft under the cap and its boundary is not monotone in ``z``. That
cleft opens downward past the cap edge at ``z ~ -0.7``, so it is continuous with
the rest of the bilayer: the membrane is one domain, the electrolyte is a second
(the lumen joins the two reservoirs), the pore body is the third. An assembly
that fragments the cleft off as its own face has a bug, and the domain count is
the cheapest test for it.

The membrane's outer edge at ``r = 250`` lies outside the arc, so the
quadrilateral is intersected with the half-disc and ``membrane_outer`` is the
resulting **arc segment** ``|z| <= 1.4``. Building it as a straight segment at
``r = 250`` leaves a sliver between it and the reservoir arc.

Faces are assembled and then glued. ``netgen.occ.Glue`` is what makes the
junction conformal: a compound of the same three faces meshes with two
coincident node chains along every seam and a glue meshes with one [tested], and
coincident chains are exactly the failure VER-28 exists to catch - the
coordinates agree and the mesh does not.
"""

from __future__ import annotations

from dataclasses import dataclass

from nanopnp.core.typing import Mesh, Shape
from nanopnp.mesh.adapter import from_ngsolve
from nanopnp.mesh.primitives import TOL_NM
from nanopnp.mesh.profile import PoreProfile, load_profile
from nanopnp.mesh.quality import QualityReport, check_quality

REFERENCE_PROFILE = "clya_reference_profile"
"""Fixture name of the ClyA-AS radial geometry (section 5.2.1)."""

RESERVOIR_RADIUS_NM = 250.0
"""Reservoir half-disc radius (section 2.2)."""

MEMBRANE_THICKNESS_NM = 2.8
"""Bilayer thickness, mid-plane at ``z = 0`` (section 2.2)."""

MEMBRANE_INNER_TRANS_NM = 2.0
"""Radius of the membrane's drawn inner corner on ``z = -1.4``."""

MEMBRANE_INNER_CIS_NM = 3.5
"""Radius of the membrane's drawn inner corner on ``z = +1.4``.

Both corners are inside the pore body on the delivered geometry, which is the
point of :meth:`ReferenceGeometry.junction_report`; they are kept because they
define the *quadrilateral being subtracted from*, not the junction.
"""

GLOBAL_MAXH_NM = 10.0
"""Global maximum element size; the reference model's "Finer" preset."""

WALL_MAXH_NM = 0.05
"""Element size on the pore boundary (section 5.2.2, NUM-30: about lambda_D/5)."""

RESERVOIR_ARC_MAXH_NM = 5.0
"""Element size on the reservoir's outer boundary (section 5.2.2)."""

PORE_DOMAIN_MAXH_NM = 0.1
"""Element size inside the pore body; section 5.2.2's "Extremely fine" preset.

Section 5.2.2 names a *pore domain* and the assembled region has one electrolyte
face, lumen and reservoirs together (VER-28 requires exactly three domains), so
there is no separate lumen face to size. The lumen is refined instead by grading
away from its 0.05 nm wall, which is how the reference mesh reached 0.05 nm
there in the first place.
"""

RESERVOIR_DOMAIN_MAXH_NM = 2.8
"""Element size in the electrolyte away from a size field (section 5.2.2)."""

AXIS_IN_PORE_MAXH_NM = 0.075
"""Element size on the symmetry axis over the pore's axial span (section 5.2.2)."""

GRADING = 0.2
"""Netgen grading. Smaller grades faster; 0.2 is what the Phase-0 shapes use."""

OPTIMISATION_STEPS = 5
"""``optsteps2d``: the ``optimize("Netgen")`` pass section 5.2.2 requires."""

_ARC_RTOL = 1e-9
"""Relative tolerance for deciding that a point lies on the reservoir arc."""


class ReferenceGeometryError(ValueError):
    """Raised when the assembled region is not the one section 5.2.2 describes."""


@dataclass(frozen=True)
class JunctionReport:
    """Where the membrane actually meets the pore, measured two ways (VER-28).

    ``expected_*`` come from the fixture polygon - the outermost radius at which
    it crosses each bilayer plane - and ``assembled_*`` from the glued region,
    as the innermost radius the ``membrane`` boundary reaches on that plane. The
    two agreeing is the statement that the boolean cut landed on the pore's own
    outer surface; the drawn corners at ``r = 2.0`` and ``r = 3.5`` appear
    nowhere in it.

    Attributes
    ----------
    expected_trans_nm, expected_cis_nm
        Outermost polygon crossing of ``z = -h`` and ``z = +h``, in nm.
    assembled_trans_nm, assembled_cis_nm
        Innermost radius of the ``membrane`` boundary on the same two planes.
    materials, boundaries
        The assembled region's domain and boundary names, sorted.
    """

    expected_trans_nm: float
    expected_cis_nm: float
    assembled_trans_nm: float
    assembled_cis_nm: float
    materials: tuple[str, ...]
    boundaries: tuple[str, ...]

    @property
    def offsets_nm(self) -> tuple[float, float]:
        """Signed ``assembled - expected`` on the trans and cis planes, in nm."""
        return (
            self.assembled_trans_nm - self.expected_trans_nm,
            self.assembled_cis_nm - self.expected_cis_nm,
        )

    @property
    def worst_offset_nm(self) -> float:
        """The larger of the two offsets in magnitude, in nm."""
        return max(abs(offset) for offset in self.offsets_nm)

    def summary(self) -> dict[str, object]:
        """Return the report as plain data, for a provenance manifest (FR-25)."""
        return {
            "expected_trans_nm": self.expected_trans_nm,
            "expected_cis_nm": self.expected_cis_nm,
            "assembled_trans_nm": self.assembled_trans_nm,
            "assembled_cis_nm": self.assembled_cis_nm,
            "worst_offset_nm": self.worst_offset_nm,
            "materials": list(self.materials),
            "boundaries": list(self.boundaries),
        }


def plane_crossings(profile: PoreProfile, z_nm: float) -> tuple[float, ...]:
    """Return the radii at which ``profile``'s closed polygon crosses ``z = z_nm``.

    Parameters
    ----------
    profile
        The pore profile. Its closing edge is implied, and is included here.
    z_nm
        The plane, in nm.

    Returns
    -------
    tuple of float
        The crossing radii, sorted ascending. A closed simple polygon crosses a
        plane an even number of times, so the first and last entries bracket the
        body; the pore gives two on each bilayer plane, the lumen wall and the
        outer surface.

    Notes
    -----
    A vertex lying exactly on the plane is counted once, not twice: the interval
    test is half-open in ``z``, which is the standard fix for the double-count
    and is why the delivered table's vertex at ``(4.88, +1.4)`` gives ``4.88``
    rather than a duplicate.
    """
    import numpy as np

    points = profile.as_array()
    starts = points
    ends = np.roll(points, -1, axis=0)
    z0, z1 = starts[:, 1], ends[:, 1]
    lower = np.minimum(z0, z1)
    upper = np.maximum(z0, z1)
    crossing = (lower <= z_nm) & (z_nm < upper)
    if not bool(np.any(crossing)):
        return ()
    fraction = (z_nm - z0[crossing]) / (z1[crossing] - z0[crossing])
    radii = starts[crossing, 0] + fraction * (ends[crossing, 0] - starts[crossing, 0])
    return tuple(sorted(float(value) for value in radii))


@dataclass(frozen=True)
class ReferenceGeometry:
    """The ClyA reference region in the ``(r, z)`` half-plane, in nm.

    Parameters
    ----------
    profile
        The pore polygon. :meth:`from_fixture` loads the shipped one.
    reservoir_radius_nm, membrane_thickness_nm
        Section 2.2's 250 nm and 2.8 nm.
    membrane_inner_trans_nm, membrane_inner_cis_nm
        The quadrilateral's inner corners on the two bilayer planes. Both lie
        inside the pore body on the delivered geometry; see the module
        docstring.
    """

    profile: PoreProfile
    reservoir_radius_nm: float = RESERVOIR_RADIUS_NM
    membrane_thickness_nm: float = MEMBRANE_THICKNESS_NM
    membrane_inner_trans_nm: float = MEMBRANE_INNER_TRANS_NM
    membrane_inner_cis_nm: float = MEMBRANE_INNER_CIS_NM

    @classmethod
    def from_fixture(cls, name: str = REFERENCE_PROFILE) -> ReferenceGeometry:
        """Return the geometry built on a shipped profile fixture."""
        return cls(profile=load_profile(name))

    @property
    def half_thickness_nm(self) -> float:
        """Half the bilayer thickness; the membrane spans ``+/- this``."""
        return 0.5 * self.membrane_thickness_nm

    def faces(self) -> tuple[Shape, Shape, Shape]:
        """Return the three named faces - electrolyte, membrane, pore - unglued.

        The booleans are the assembly: the membrane is the quadrilateral clipped
        to the reservoir and cut by the pore body, and the electrolyte is what
        the half-disc has left once both are removed. Names are set after the
        booleans, because a face's name does not survive being cut.
        """
        pore = self._pore_face()
        disc = self._reservoir_face()
        quad = self._membrane_face()

        membrane = (quad * disc) - pore
        electrolyte = (disc - quad) - pore
        for face, name in ((electrolyte, "electrolyte"), (membrane, "membrane"), (pore, "protein")):
            face.name = name
        self._check_face_counts(electrolyte, membrane, pore)
        return electrolyte, membrane, pore

    def _pore_face(self) -> Shape:
        """Return the pore polygon as a face, from the fixture's vertices.

        The vertices are reversed when the fixture traces its loop clockwise,
        which the delivered ClyA table does (signed area -26.4939 nm^2). A
        clockwise wire gives OCC a face of negative area, and a negative face is
        not merely upside down: it subtracts as an addition, so
        ``disc - quad`` returns the disc split in two rather than the disc with
        a hole, and ``quad * disc`` returns nothing at all [tested]. Orientation
        is fixed here, once, rather than asked of every fixture.
        """
        import netgen.occ as occ

        vertices = self.profile.as_array()
        if self.profile.is_clockwise:
            vertices = vertices[::-1]
        plane = occ.WorkPlane().MoveTo(float(vertices[0][0]), float(vertices[0][1]))
        for radius, height in vertices[1:]:
            plane = plane.LineTo(float(radius), float(height))
        return plane.Close().Face()

    def _reservoir_face(self) -> Shape:
        """Return the reservoir half-disc, ``r >= 0`` of a 250 nm circle.

        The clipping box is traced by hand rather than taken from
        ``Rectangle`` so that its side on ``r = 0`` is broken into three
        collinear segments at the pore's axial extent. OCC keeps collinear
        segments as separate edges, and that is the only way section 5.2.2's
        "symmetry axis inside pore, 0.075 nm" can be a size field at all: the
        pore polygon never touches the axis, so nothing else splits it.

        The half-disc's arc carries one vertex the construction did not ask for.
        ``Circle(...).Face()`` is a single closed edge whose seam OCC places at
        parameter zero, ``(250, 0)``, and clipping to ``r >= 0`` keeps it: the
        arc between the membrane's two outer corners is therefore two arcs
        meeting there, both named ``membrane_outer`` and both carrying the same
        size field, and the assembled region has 193 vertices and 195 edges
        rather than the 192 and 194 the axis split alone would give [tested].
        A closed circle has a seam somewhere; putting it at ``z = 0`` costs one
        vertex element on the reservoir rim and nothing else.
        """
        import netgen.occ as occ

        radius = self.reservoir_radius_nm
        lower, upper = self.profile.extent_z_nm
        disc = occ.WorkPlane().Circle(0.0, 0.0, radius).Face()
        box = (
            occ.WorkPlane()
            .MoveTo(0.0, -radius)
            .LineTo(radius, -radius)
            .LineTo(radius, radius)
            .LineTo(0.0, radius)
            .LineTo(0.0, upper)
            .LineTo(0.0, lower)
            .Close()
            .Face()
        )
        return disc * box

    def _membrane_face(self) -> Shape:
        """Return the membrane quadrilateral, unclipped and uncut.

        Traced counter-clockwise, for the reason :meth:`_pore_face` gives.

        It is traced *past* the reservoir radius, by one membrane half-thickness,
        and the intersection with the half-disc clips it back. Ending it exactly
        on ``r = 250`` makes its outer edge touch the reservoir arc at the single
        point ``(250, 0)`` rather than crossing it, which is a boolean the mesher
        would have to resolve exactly for no gain. Any overshoot removes the
        contact; a half-thickness scales with the geometry.
        """
        import netgen.occ as occ

        half = self.half_thickness_nm
        outer = self.reservoir_radius_nm + half
        return (
            occ.WorkPlane()
            .MoveTo(self.membrane_inner_trans_nm, -half)
            .LineTo(outer, -half)
            .LineTo(outer, half)
            .LineTo(self.membrane_inner_cis_nm, half)
            .Close()
            .Face()
        )

    def _check_face_counts(self, electrolyte: Shape, membrane: Shape, pore: Shape) -> None:
        """Raise unless each of the three domains came out as a single face.

        The membrane is the one at risk: the cleft under the cap is continuous
        with the rest of the bilayer only because the cap's underside opens
        downward past ``z ~ -0.7``, and an assembly that got the polygon or the
        quadrilateral wrong fragments it off as a fourth face. Counting is
        cheaper than discovering it in the domain names of a solved mesh.
        """
        named = ((electrolyte, "electrolyte"), (membrane, "membrane"), (pore, "protein"))
        for shape, name in named:
            count = len(list(shape.faces))
            if count != 1:
                raise ReferenceGeometryError(
                    f"the {name} domain assembled as {count} faces rather than one; the "
                    "reference region has exactly three domains (section 5.2.2, VER-28)"
                )

    def _inside_membrane_quad(self, radius: float, height: float) -> bool:
        """Return whether ``(r, z)`` is strictly inside the membrane quadrilateral.

        Used to split the pore's boundary: a segment of it whose midpoint is
        inside the quadrilateral is buried in the bilayer and is the pore-to-
        membrane seam, and one outside it faces the electrolyte and is ``wall``.
        The slant is what makes the test work - the lumen wall runs from
        ``r = 1.725`` to ``r = 2.96`` across the bilayer and stays inside the
        drawn corners, while the outer surface runs from 2.7524 to 4.88 and
        stays outside them.
        """
        half = self.half_thickness_nm
        if abs(height) >= half - TOL_NM:
            return False
        span = self.membrane_inner_cis_nm - self.membrane_inner_trans_nm
        inner = self.membrane_inner_trans_nm + span * (height + half) / self.membrane_thickness_nm
        return bool(inner + TOL_NM < radius < self.reservoir_radius_nm - TOL_NM)

    def name_edges(self, shape: Shape, *, wall_h_nm: float | None = WALL_MAXH_NM) -> None:
        """Name every edge of ``shape`` into the section 5.3.1 vocabulary, in place.

        Classification is by a point *on* the curve rather than by
        ``edge.center``: the reservoir arc's centre of mass is the circle's
        centre, nowhere near the arc [tested], so the centre-of-mass chain
        :class:`~nanopnp.mesh.primitives.CylindricalPoreGeometry` uses does not
        carry over to a geometry with curved boundaries.

        The order of the chain is the argument. The arc is taken first because
        the bilayer planes cut it; the bilayer surfaces next, and only as
        *horizontal* edges, because the pore polygon crosses ``z = +1.4``
        without running along it; then the buried part of the pore boundary,
        which is the pore-to-membrane seam and is named ``interface`` rather
        than ``wall`` so that PHY-02's distance field does not measure from it;
        and everything left is the pore boundary facing the electrolyte.

        Parameters
        ----------
        shape
            The glued region.
        wall_h_nm
            Element size imposed on ``wall``; ``None`` leaves the global size.
        """
        half = self.half_thickness_nm
        radius = self.reservoir_radius_nm
        lower, upper = self.profile.extent_z_nm
        for edge in shape.edges:
            start, end = _endpoints(edge)
            r_mid, z_mid = _curve_midpoint(edge)
            on_axis = abs(r_mid) < TOL_NM
            on_arc = abs(_norm(r_mid, z_mid) - radius) < _ARC_RTOL * radius
            horizontal = abs(start[1] - end[1]) < TOL_NM
            if on_axis:
                edge.name = "axis"
                if lower - TOL_NM < z_mid < upper + TOL_NM:
                    edge.maxh = AXIS_IN_PORE_MAXH_NM
            elif on_arc:
                edge.maxh = RESERVOIR_ARC_MAXH_NM
                if abs(z_mid) < half + TOL_NM:
                    edge.name = "membrane_outer"
                else:
                    edge.name = "cis" if z_mid > 0.0 else "trans"
            elif horizontal and abs(abs(z_mid) - half) < TOL_NM:
                edge.name = "membrane"
            elif self._inside_membrane_quad(r_mid, z_mid):
                edge.name = "interface"
            else:
                edge.name = "wall"
                if wall_h_nm is not None:
                    edge.maxh = wall_h_nm

    def shape(self, *, wall_h_nm: float | None = WALL_MAXH_NM) -> Shape:
        """Return the glued, fully named region, unmeshed.

        The glue is not cosmetic: it is what makes the membrane-to-pore junction
        one node chain instead of two coincident ones (VER-28).
        """
        import netgen.occ as occ

        electrolyte, membrane, pore = self.faces()
        glued = occ.Glue([electrolyte, membrane, pore])
        self.name_edges(glued, wall_h_nm=wall_h_nm)
        for face in glued.faces:
            if face.name == "protein":
                face.maxh = PORE_DOMAIN_MAXH_NM
            elif face.name == "electrolyte":
                face.maxh = RESERVOIR_DOMAIN_MAXH_NM
        return glued

    def generate(
        self,
        *,
        maxh_nm: float = GLOBAL_MAXH_NM,
        wall_h_nm: float | None = WALL_MAXH_NM,
        check_quality: bool = True,
    ) -> Mesh:
        """Return the meshed reference region.

        Parameters
        ----------
        maxh_nm
            Global maximum element size, in nm. Section 5.2.2's "Finer" preset
            is 10 nm; the reference mesh reached 120,917 triangles from it.
        wall_h_nm
            Element size on the pore boundary, in nm. Section 5.2.2's 0.05.
        check_quality
            Gate the result on SICN and gamma (VER-10, QR-12).

        Returns
        -------
        Mesh
            The NGSolve mesh, domains and boundaries named.
        """
        import netgen.occ as occ
        import ngsolve as ngs

        geometry = occ.OCCGeometry(self.shape(wall_h_nm=wall_h_nm), dim=2)
        mesh = ngs.Mesh(
            geometry.GenerateMesh(maxh=maxh_nm, grading=GRADING, optsteps2d=OPTIMISATION_STEPS)
        )
        if check_quality:
            check_quality_report(mesh)
        return mesh

    def junction_report(self, *, wall_h_nm: float | None = WALL_MAXH_NM) -> JunctionReport:
        """Measure the membrane-to-pore junction on the assembled region (VER-28).

        Returns
        -------
        JunctionReport
            The polygon's own crossing radii against the ones the assembly
            produced, and the region's two name tables.

        Raises
        ------
        ReferenceGeometryError
            If either bilayer plane carries no ``membrane`` edge, which means
            the quadrilateral did not reach the pore and there is no junction to
            report on.
        """
        half = self.half_thickness_nm
        glued = self.shape(wall_h_nm=wall_h_nm)
        materials = sorted({face.name for face in glued.faces if face.name is not None})
        boundaries = sorted({edge.name for edge in glued.edges if edge.name is not None})
        assembled: list[float] = []
        for plane, label in ((-half, "trans"), (half, "cis")):
            radii = [
                point[0]
                for edge in glued.edges
                if edge.name == "membrane"
                for point in _endpoints(edge)
                if abs(point[1] - plane) < TOL_NM
            ]
            if not radii:
                raise ReferenceGeometryError(
                    f"no membrane boundary on the {label} bilayer plane z = {plane:g} nm; the "
                    "quadrilateral did not meet the pore body (VER-28)"
                )
            assembled.append(min(radii))
        expected = tuple(max(plane_crossings(self.profile, z)) for z in (-half, half))
        return JunctionReport(
            expected_trans_nm=expected[0],
            expected_cis_nm=expected[1],
            assembled_trans_nm=assembled[0],
            assembled_cis_nm=assembled[1],
            materials=tuple(materials),
            boundaries=tuple(boundaries),
        )


def check_quality_report(mesh: Mesh, *, where: str = "the reference geometry") -> QualityReport:
    """Gate a meshed reference region and return its quality report (VER-10)."""
    return check_quality(from_ngsolve(mesh), where=where)


def _norm(radius: float, height: float) -> float:
    """Return the distance of ``(r, z)`` from the origin."""
    return float((radius * radius + height * height) ** 0.5)


def _endpoints(edge: Shape) -> tuple[tuple[float, float], tuple[float, float]]:
    """Return an edge's two endpoints as ``(r, z)`` pairs, in nm."""
    start, end = edge.start, edge.end
    return (float(start[0]), float(start[1])), (float(end[0]), float(end[1]))


def _curve_midpoint(edge: Shape) -> tuple[float, float]:
    """Return the point halfway along ``edge`` in its own parameter, as ``(r, z)``.

    ``edge.center`` is the centre of mass and lies off the curve for an arc, so
    it cannot classify a boundary that has any; ``Value`` on the midpoint of
    ``parameter_interval`` is on the curve for both an arc and a segment.
    """
    lower, upper = edge.parameter_interval
    point = edge.Value(0.5 * (lower + upper))
    return float(point[0]), float(point[1])

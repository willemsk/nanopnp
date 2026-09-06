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
from nanopnp.mesh.adapter import from_ngsolve
from nanopnp.mesh.quality import check_quality as _check_quality

TOL_NM = 1e-9
"""Geometric tolerance for classifying an edge by its centre of mass.

Public because :mod:`nanopnp.geometry.analyte` classifies against the same
tolerance when it embeds a body in one of these geometries; two tolerances that
can drift apart would put an edge in one geometry's vocabulary and not the
other's.
"""

PERMITTIVITY_EXEMPT: frozenset[str] = frozenset({"exclusion"})
"""Solid materials that need no ``physics.solid_permittivities`` entry.

``exclusion`` is the ion-exclusion shell of FR-15: a solid for Nernst-Planck and
for the flow, so the no-slip surface sits at its outer edge — the conventional
hydrodynamic shear plane — and the **fluid's** ``eps_r`` for Poisson, which is
what :meth:`nanopnp.physics.models.CoupledModel.permittivity`'s default already
gives anything with no entry of its own (§5.3.1 NOTE). Demanding a value for it
would invite one to be invented, and any value but the electrolyte's would put a
dielectric jump at the shear plane, which is not what a Stern layer is.

Here rather than in :mod:`nanopnp.mesh.ingest`, beside the fluid set and for the
same reason: ``physics/`` reads both, and ``ingest`` imports ``physics``, so the
vocabulary constants the forms consult live on this side of that edge.
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


def _gated(mesh: Mesh, *, check: bool, where: str) -> Mesh:
    """Return ``mesh``, gated on element quality unless ``check`` is false (VER-10).

    The gate runs on every mesh this module builds, not only on imported ones.
    The margin measured on the reference shapes is wide - minimum SICN 0.647
    against the 0.3 floor of section 5.2.2 [tested] - so an unconditional gate
    costs a fraction of a second and catches the degenerate mesh a badly chosen
    ``wall_h_nm`` would otherwise hand to the solver.

    Parameters
    ----------
    mesh
        The freshly generated NGSolve mesh.
    check
        False to skip the gate. Reserved for a mesh whose element shapes are a
        deliberate choice rather than a defect - a test building a bad mesh on
        purpose, or a one-dimensional benchmark whose anisotropy lies in the
        direction the solution is constant in (VER-16). It is keyword-only at
        every call site so that skipping the gate is visible where it happens.
    where
        What to call the mesh in a diagnostic (QR-12).

    Returns
    -------
    Mesh
        ``mesh`` itself, unchanged.

    Raises
    ------
    nanopnp.mesh.quality.MeshQualityError
        If any element is inverted or either quality measure is at or below the
        floor, naming the gate, the value and the element's centroid.
    """
    if check:
        _check_quality(from_ngsolve(mesh), where=where)
    return mesh


@dataclass(frozen=True)
class SlabGeometry:
    """A planar slab of electrolyte against a charged wall.

    The wall is at ``x = 0`` and the bulk at ``x = width_nm``; the ``y`` extent
    is an artefact of solving a one-dimensional problem on a two-dimensional
    mesh, and its boundaries carry natural conditions.

    With ``exclusion_nm`` set, the first ``lambda_S`` of the slab is the
    ``exclusion`` material of §5.3.1's NOTE rather than electrolyte: ions and
    flow are excluded from it and Poisson is solved across it at the fluid's
    ``eps_r``, which is the Gouy-Chapman-**Stern** geometry of VER-31. The wall
    stays at ``x = 0``, so the surface charge is on the same plane in both
    configurations and ``exclusion_nm = 0`` reproduces the plain slab exactly.
    """

    width_nm: float
    height_nm: float = 1.0
    exclusion_nm: float = 0.0

    def __post_init__(self) -> None:
        """Refuse a shell that is not inside the slab.

        Raises
        ------
        ValueError
            If the layer is negative or reaches the bulk boundary, which would
            leave no electrolyte for the diffuse layer this geometry exists to
            resolve.
        """
        if not 0.0 <= self.exclusion_nm < self.width_nm:
            raise ValueError(
                f"exclusion_nm={self.exclusion_nm} must lie in [0, width_nm) and the slab is "
                f"{self.width_nm} nm wide; an exclusion layer spanning the slab leaves no "
                "electrolyte for the diffuse layer"
            )

    def _name_edges(self, shape: Shape, *, wall_h_nm: float | None) -> None:
        """Name every edge of ``shape`` by its centre of mass, in place."""
        for edge in shape.edges:
            centre = edge.center
            if abs(centre[0]) < TOL_NM:
                edge.name = "wall"
                if wall_h_nm is not None:
                    edge.maxh = wall_h_nm
            elif abs(centre[0] - self.width_nm) < TOL_NM:
                edge.name = "bulk"
            elif abs(centre[0] - self.exclusion_nm) < TOL_NM:
                # The shell's outer face: an interior seam between two domains
                # this run solves different equations on, and nothing selects on
                # it. Calling it ``wall`` would put it in the PHY-02 distance
                # source set and impose no-slip in the middle of the slab.
                edge.name = "interface"
            else:
                edge.name = "lateral"

    def generate(
        self, *, maxh_nm: float, wall_h_nm: float | None = None, check_quality: bool = True
    ) -> Mesh:
        """Return a meshed slab, graded towards the wall if ``wall_h_nm`` is given.

        ``check_quality`` gates the result through :func:`_gated`; see there for
        why it defaults to on.
        """
        import netgen.occ as occ
        import ngsolve as ngs

        if self.exclusion_nm > 0.0:
            shell = occ.Rectangle(self.exclusion_nm, self.height_nm).Face()
            shell.name = "exclusion"
            fluid = (
                occ.MoveTo(self.exclusion_nm, 0)
                .Rectangle(self.width_nm - self.exclusion_nm, self.height_nm)
                .Face()
            )
            fluid.name = "electrolyte"
            face = occ.Glue([shell, fluid])
        else:
            face = occ.Rectangle(self.width_nm, self.height_nm).Face()
            face.name = "electrolyte"
        self._name_edges(face, wall_h_nm=wall_h_nm)
        mesh = ngs.Mesh(occ.OCCGeometry(face, dim=2).GenerateMesh(maxh=maxh_nm, grading=0.2))
        return _gated(mesh, check=check_quality, where=f"a {self.width_nm:g} nm slab")


@dataclass(frozen=True)
class CylinderGeometry:
    """An axisymmetric cylinder of electrolyte, ``0 <= r <= radius_nm``.

    The axis edge is named so that a test can confirm nothing essential is
    imposed there; the ends carry natural conditions, which is consistent with
    the z-independent Debye-Hueckel solution.
    """

    radius_nm: float
    length_nm: float

    def generate(
        self, *, maxh_nm: float, wall_h_nm: float | None = None, check_quality: bool = True
    ) -> Mesh:
        """Return a meshed cylinder cross-section, graded towards the wall.

        ``check_quality`` gates the result through :func:`_gated`; see there for
        why it defaults to on.
        """
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
        mesh = ngs.Mesh(occ.OCCGeometry(face, dim=2).GenerateMesh(maxh=maxh_nm, grading=0.2))
        return _gated(mesh, check=check_quality, where=f"a {self.radius_nm:g} nm cylinder")


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

    def generate(
        self, *, maxh_nm: float, wall_h_nm: float | None = None, check_quality: bool = True
    ) -> Mesh:
        """Return the meshed geometry with named domains and boundaries.

        Parameters
        ----------
        maxh_nm
            Global maximum element size, in nm.
        wall_h_nm
            Element size on the pore wall, in nm; NUM-30 asks for about
            ``lambda_D / 5`` there.
        check_quality
            Gate the result through :func:`_gated`; see there for why it
            defaults to on.
        """
        import netgen.occ as occ
        import ngsolve as ngs

        geometry = occ.OCCGeometry(self.shape(wall_h_nm=wall_h_nm), dim=2)
        mesh = ngs.Mesh(geometry.GenerateMesh(maxh=maxh_nm, grading=0.2))
        return _gated(
            mesh,
            check=check_quality,
            where=f"a {self.pore_radius_nm:g} nm x {self.membrane_thickness_nm:g} nm pore",
        )

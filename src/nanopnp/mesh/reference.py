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

**The assembly, naming and sizing are stage 5's and stage 6's** (WP21). This
class is the stage-5 region of :mod:`nanopnp.geometry.region` with the drawn
inner corners in place of the derived chord, sized by the one table of
:mod:`nanopnp.mesh.sizing`. Any chord inside the body yields the same region,
and the fixture meshed with the drawn and the derived chord has one connectivity
(section 5.2.1 NOTE on the membrane junction on any profile), so the reference
mesh keeps its content hash.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from nanopnp.core.typing import Mesh, Shape
from nanopnp.geometry.region import (
    MembraneRecord,
    RegionRecord,
    assemble_faces,
    build_region,
    membrane_radii,
    name_region,
)
from nanopnp.mesh.adapter import from_ngsolve
from nanopnp.mesh.profile import PoreProfile, load_profile, plane_crossings
from nanopnp.mesh.quality import QualityReport, check_quality
from nanopnp.mesh.sizing import SIZES, WALL_CEILING_NM, apply_sizes

__all__ = [
    "REFERENCE_PROFILE",
    "JunctionReport",
    "ReferenceGeometry",
    "check_quality_report",
    "plane_crossings",
]

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

WALL_MAXH_NM = WALL_CEILING_NM
"""Element size on the pore boundary: section 5.2.2's 0.05 nm, NUM-30's ceiling."""


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

    def record(self) -> RegionRecord:
        """Return this geometry as a stage-5 record, with the drawn inner corners.

        The profile is already in the model frame (the bilayer's mid-plane is
        ``z = 0``), and the junction radii are the outermost plane crossings,
        which on this profile are the lumen-adjacent intervals' ``r2``.
        """
        half = self.half_thickness_nm
        return RegionRecord(
            profile=[(float(r), float(z)) for r, z in self.profile.vertices],
            membrane=MembraneRecord(
                thickness_nm=self.membrane_thickness_nm,
                centre_z_nm=0.0,
                inner_trans_nm=self.membrane_inner_trans_nm,
                inner_cis_nm=self.membrane_inner_cis_nm,
            ),
            reservoir_radius_nm=self.reservoir_radius_nm,
            axis_split_nm=self.profile.extent_z_nm,
            junction_nm={
                "trans": max(plane_crossings(self.profile, -half)),
                "cis": max(plane_crossings(self.profile, half)),
            },
        )

    def faces(self) -> tuple[Shape, Shape, Shape]:
        """Return the three named faces - electrolyte, membrane, pore - unglued.

        :func:`nanopnp.geometry.region.assemble_faces` on :meth:`record`, which
        raises :class:`~nanopnp.geometry.region.RegionGateError` if a domain
        assembled as other than one face.
        """
        return assemble_faces(self.record())

    def name_edges(self, shape: Shape, *, wall_h_nm: float | None = WALL_MAXH_NM) -> None:
        """Name every edge of ``shape`` into the section 5.3.1 vocabulary and size it, in place.

        The naming is stage 5's (:func:`nanopnp.geometry.region.name_region`),
        by adjacency in the glued shape, and the sizes are section 5.2.2's
        (:func:`nanopnp.mesh.sizing.apply_sizes`).

        Parameters
        ----------
        shape
            The glued region.
        wall_h_nm
            Element size imposed on ``wall``; ``None`` leaves the global size.
        """
        name_region(shape, reservoir_radius_nm=self.reservoir_radius_nm)
        apply_sizes(shape, wall_h_nm=wall_h_nm, axis_extent_nm=self.profile.extent_z_nm)

    def shape(self, *, wall_h_nm: float | None = WALL_MAXH_NM) -> Shape:
        """Return the glued, fully named and sized region, unmeshed.

        The glue is not cosmetic: it is what makes the membrane-to-pore junction
        one node chain instead of two coincident ones (VER-28).
        """
        glued = build_region(self.record())
        apply_sizes(glued, wall_h_nm=wall_h_nm, axis_extent_nm=self.profile.extent_z_nm)
        return glued

    def generate(
        self,
        *,
        maxh_nm: float = SIZES.global_nm,
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
        from nanopnp.mesh.generate import mesh_shape

        mesh = mesh_shape(self.shape(wall_h_nm=wall_h_nm), replace(SIZES, global_nm=maxh_nm))
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
        nanopnp.geometry.region.RegionGateError
            If either bilayer plane carries no ``membrane`` edge, which means
            the quadrilateral did not reach the pore and there is no junction to
            report on.
        """
        glued = self.shape(wall_h_nm=wall_h_nm)
        materials = sorted({face.name for face in glued.faces if face.name is not None})
        boundaries = sorted({edge.name for edge in glued.edges if edge.name is not None})
        assembled = membrane_radii(glued, self.half_thickness_nm)
        record = self.record()
        return JunctionReport(
            expected_trans_nm=record.junction_nm["trans"],
            expected_cis_nm=record.junction_nm["cis"],
            assembled_trans_nm=assembled[0],
            assembled_cis_nm=assembled[1],
            materials=tuple(materials),
            boundaries=tuple(boundaries),
        )


def check_quality_report(mesh: Mesh, *, where: str = "the reference geometry") -> QualityReport:
    """Gate a meshed reference region and return its quality report (VER-10)."""
    return check_quality(from_ngsolve(mesh), where=where)

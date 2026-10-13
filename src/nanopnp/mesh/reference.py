"""The ClyA reference geometry, assembled from a supplied pore profile (FR-09)."""

from __future__ import annotations

from dataclasses import dataclass, replace

from nanopnp.core.typing import Mesh, Shape
from nanopnp.geometry.profile import PoreProfile, load_profile, plane_crossings
from nanopnp.geometry.region import (
    MembraneRecord,
    RegionRecord,
    assemble_faces,
    build_region,
    membrane_radii,
    name_region,
)
from nanopnp.mesh.adapter import from_ngsolve
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
    expected_trans_nm: float
    expected_cis_nm: float
    assembled_trans_nm: float
    assembled_cis_nm: float
    materials: tuple[str, ...]
    boundaries: tuple[str, ...]

    @property
    def offsets_nm(self) -> tuple[float, float]:
        return (
            self.assembled_trans_nm - self.expected_trans_nm,
            self.assembled_cis_nm - self.expected_cis_nm,
        )

    @property
    def worst_offset_nm(self) -> float:
        return max(abs(offset) for offset in self.offsets_nm)

    def summary(self) -> dict[str, object]:
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
    profile: PoreProfile
    reservoir_radius_nm: float = RESERVOIR_RADIUS_NM
    membrane_thickness_nm: float = MEMBRANE_THICKNESS_NM
    membrane_inner_trans_nm: float = MEMBRANE_INNER_TRANS_NM
    membrane_inner_cis_nm: float = MEMBRANE_INNER_CIS_NM

    @classmethod
    def from_fixture(cls, name: str = REFERENCE_PROFILE) -> ReferenceGeometry:
        return cls(profile=load_profile(name))

    @property
    def half_thickness_nm(self) -> float:
        return 0.5 * self.membrane_thickness_nm

    def record(self) -> RegionRecord:
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

    def faces(self) -> tuple[Shape, ...]:
        return assemble_faces(self.record())

    def name_edges(self, shape: Shape, *, wall_h_nm: float | None = WALL_MAXH_NM) -> None:
        name_region(shape, reservoir_radius_nm=self.reservoir_radius_nm)
        apply_sizes(shape, wall_h_nm=wall_h_nm, axis_extent_nm=self.profile.extent_z_nm)

    def shape(self, *, wall_h_nm: float | None = WALL_MAXH_NM) -> Shape:
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
        from nanopnp.mesh.meshers import mesh_shape

        mesh = mesh_shape(self.shape(wall_h_nm=wall_h_nm), replace(SIZES, global_nm=maxh_nm))
        if check_quality:
            check_quality_report(mesh)
        return mesh

    def junction_report(self, *, wall_h_nm: float | None = WALL_MAXH_NM) -> JunctionReport:
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
    return check_quality(from_ngsolve(mesh), where=where)

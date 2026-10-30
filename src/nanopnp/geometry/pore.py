"""An idealised cylindrical pore: its faces, edge names and stage-5 region record (FR-09)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

from nanopnp.core.hashing import Canonicalisable
from nanopnp.geometry.tolerance import TOL_NM
from nanopnp.io.artefact import REGION_SCHEMA
from nanopnp.io.case import Pore

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.core.typing import Shape

MOUTH = "interface"


@dataclass(frozen=True)
class CylinderPore:
    """A cylindrical pore through a membrane, with a reservoir on each side.

    The lumen is the domain ``electrolyte`` and the reservoirs are ``cis`` and ``trans``.
    """

    pore_radius_nm: float
    membrane_thickness_nm: float
    reservoir_radius_nm: float

    @property
    def half_thickness_nm(self) -> float:
        """Half the membrane thickness, in nm."""
        return 0.5 * self.membrane_thickness_nm

    def faces(self) -> tuple[Shape, Shape, Shape, Shape]:
        """Return the four named faces (lumen, membrane, cis, trans), unglued."""
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
        """Name every unnamed edge of ``shape`` by its centre of mass, in place."""
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

    def shape(self, *, wall_h_nm: float | None = None, name_mouths: bool = True) -> Shape:
        """Return the glued, fully named shape, unmeshed.

        Parameters
        ----------
        name_mouths
            Name the two seams where the lumen meets a reservoir ``interface``; without it
            the mesher leaves them in its ``default`` group.
        """
        import netgen.occ as occ

        glued = occ.Glue(list(self.faces()))
        self.name_edges(glued, wall_h_nm=wall_h_nm)
        if name_mouths:
            for edge in glued.edges:
                if edge.name is None:
                    edge.name = MOUTH
        return glued


class IdealisedRegionRecord(BaseModel):
    """Stage 5's artefact for an idealised pore: its declaration and what its shape measured."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_id: str = Field(alias="schema", default=REGION_SCHEMA)
    pore: Pore
    membrane_thickness_nm: float
    reservoir_radius_nm: float
    face_areas_nm2: dict[str, float] = Field(default_factory=dict)
    edge_counts: dict[str, int] = Field(default_factory=dict)

    def geometry(self) -> CylinderPore:
        """Return the cylinder the record declares."""
        return CylinderPore(
            pore_radius_nm=self.pore.radius_nm,
            membrane_thickness_nm=self.membrane_thickness_nm,
            reservoir_radius_nm=self.reservoir_radius_nm,
        )

    def summary(self) -> dict[str, Canonicalisable]:
        """Return what the manifest's Geometry group records as ``region``."""
        return {
            "pore": self.pore.model_dump(mode="json"),
            "thickness_nm": self.membrane_thickness_nm,
            "reservoir_radius_nm": self.reservoir_radius_nm,
            "face_areas_nm2": dict(sorted(self.face_areas_nm2.items())),
            "edge_counts": dict(sorted(self.edge_counts.items())),
        }

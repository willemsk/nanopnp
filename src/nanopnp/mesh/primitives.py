"""Analytic benchmark and spike geometries in the (r, z) half-plane."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from nanopnp.core.typing import Mesh, Shape
from nanopnp.geometry.tolerance import TOL_NM
from nanopnp.mesh.adapter import from_ngsolve
from nanopnp.mesh.defaults import DEFAULT_PORE_RADIUS_NM
from nanopnp.mesh.quality import check_quality as _check_quality

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from collections.abc import Mapping


@dataclass(frozen=True)
class CoupledBoundaries:
    potential: str = "cis|trans"
    concentration: str | Mapping[str, str] = "cis|trans"
    velocity: str = "wall|membrane"
    velocity_axis: str = "axis"

    def concentration_boundary(self, species: str) -> str:
        if isinstance(self.concentration, str):
            return self.concentration
        try:
            return self.concentration[species]
        except KeyError:
            known = ", ".join(sorted(self.concentration))
            raise KeyError(
                f"no concentration boundary for {species!r}; the mapping names {known}"
            ) from None


DEFAULT_BOUNDARIES = CoupledBoundaries()
"""The boundary vocabulary of the analytic pore geometry of this module."""


PERMITTIVITY_EXEMPT: frozenset[str] = frozenset({"exclusion"})
"""Solid materials that need no ``physics.solid_permittivities`` entry.

``exclusion`` is the ion-exclusion shell of FR-15: a solid for Nernst-Planck and
for the flow, so the no-slip surface sits at its outer edge — the conventional
hydrodynamic shear plane — and **water** for Poisson. Ions do not exist in it,
so ``<c>`` has no meaning there and the water is ion-free: ``eps_r,f^0``, which
:meth:`nanopnp.physics.models.CoupledModel.permittivity` gives every material off
the fluid that has no entry of its own (§5.3.1 NOTE, author ruling 13). Demanding
a value for it would invite one to be invented.

Here rather than in :mod:`nanopnp.mesh.ingest`, beside the fluid set and the
boundary vocabulary and for the same reason: ``physics/`` and ``mesh/ingest`` read
all of them, and ``mesh/`` sits below ``physics/`` (section 8.2.8 H11), so the
vocabulary the forms consult lives on the lower side of that edge.
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
    if check:
        _check_quality(from_ngsolve(mesh), where=where)
    return mesh


@dataclass(frozen=True)
class SlabGeometry:
    width_nm: float
    height_nm: float = 1.0
    exclusion_nm: float = 0.0

    def __post_init__(self) -> None:
        if not 0.0 <= self.exclusion_nm < self.width_nm:
            raise ValueError(
                f"exclusion_nm={self.exclusion_nm} must lie in [0, width_nm) and the slab is "
                f"{self.width_nm} nm wide; an exclusion layer spanning the slab leaves no "
                "electrolyte for the diffuse layer"
            )

    def _name_edges(self, shape: Shape, *, wall_h_nm: float | None) -> None:
        for edge in shape.edges:
            centre = edge.center
            if abs(centre[0]) < TOL_NM:
                edge.name = "wall"
                if wall_h_nm is not None:
                    edge.maxh = wall_h_nm
            elif abs(centre[0] - self.width_nm) < TOL_NM:
                edge.name = "bulk"
            elif abs(centre[0] - self.exclusion_nm) < TOL_NM:
                # An interior seam: ``wall`` would add it to the PHY-02 distance sources and
                # impose no-slip mid-slab.
                edge.name = "interface"
            else:
                edge.name = "lateral"

    def generate(
        self, *, maxh_nm: float, wall_h_nm: float | None = None, check_quality: bool = True
    ) -> Mesh:
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
    radius_nm: float
    length_nm: float

    def generate(
        self, *, maxh_nm: float, wall_h_nm: float | None = None, check_quality: bool = True
    ) -> Mesh:
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
    pore_radius_nm: float = DEFAULT_PORE_RADIUS_NM
    membrane_thickness_nm: float = 13.0
    reservoir_radius_nm: float = 50.0

    @property
    def half_thickness_nm(self) -> float:
        return 0.5 * self.membrane_thickness_nm

    def faces(self) -> tuple[Shape, Shape, Shape, Shape]:
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
        import netgen.occ as occ

        glued = occ.Glue(list(self.faces()))
        self.name_edges(glued, wall_h_nm=wall_h_nm)
        return glued

    def generate(
        self, *, maxh_nm: float, wall_h_nm: float | None = None, check_quality: bool = True
    ) -> Mesh:
        import netgen.occ as occ
        import ngsolve as ngs

        geometry = occ.OCCGeometry(self.shape(wall_h_nm=wall_h_nm), dim=2)
        mesh = ngs.Mesh(geometry.GenerateMesh(maxh=maxh_nm, grading=0.2))
        return _gated(
            mesh,
            check=check_quality,
            where=f"a {self.pore_radius_nm:g} nm x {self.membrane_thickness_nm:g} nm pore",
        )

"""The size fields of section 5.2.2, and the wall target NUM-30 resolves to (FR-10)."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from nanopnp.core.scaling import debye_length_nm

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.core.hashing import Canonicalisable
    from nanopnp.core.typing import Shape
    from nanopnp.io.case import CaseDocument
    from nanopnp.io.resolved import ResolvedCase

logger = logging.getLogger(__name__)

WALL_CEILING_NM = 0.05
"""The wall target's ceiling: section 5.2.2's pore-boundary maximum."""

DEBYE_FRACTION = 5.0
"""NUM-30's wall target is ``lambda_D`` divided by this."""

GRADING = 0.2
"""Netgen grading. Smaller grades faster; 0.2 is what the Phase-0 shapes use."""

OPTIMISATION_STEPS = 5
"""``optsteps2d``: netgen's own optimisation pass, which section 5.2.2 requires."""

GMSH_ALGORITHM = 6
"""``Mesh.Algorithm`` on the Gmsh backend: Frontal-Delaunay (WP23 D5).

On the reference fixture, algorithm 5 (Delaunay) gives 10 % more triangles at a
mean gamma of 0.95 against 0.99, and 1 (MeshAdapt) is slower and worse (WP23
plan, Design section 3).
"""

GMSH_SMOOTHING = 5
"""``Mesh.Smoothing`` on the Gmsh backend: its optimisation pass, as ``optsteps2d`` is netgen's."""

GMSH_FIELD_RULES: tuple[str, ...] = (
    "boundary-sources-graded",
    "domain-boundary-sources-graded",
    "short-curve-vertices-below-target",
    "membrane-at-thickness-unscaled",
)
"""The Gmsh backend's size-field rules, as the stage-6 key names them (WP23 D3, D4, D8).

Each changes the mesh, so each keys it: a rule edited in code is a new
identifier here, and the mesh it makes a new store entry. Their statement is the
section 5.2.2 NOTE on the Gmsh backend's size field.
"""


@dataclass(frozen=True)
class SizeTable:
    """The element sizes of section 5.2.2 other than the wall's, in nm."""

    global_nm: float = 10.0
    protein_nm: float = 0.1
    electrolyte_nm: float = 2.8
    arc_nm: float = 5.0
    axis_in_pore_nm: float = 0.075

    def scaled(self, scale: float) -> SizeTable:
        """Return this table with every size multiplied by ``scale``."""
        return replace(
            self,
            global_nm=self.global_nm * scale,
            protein_nm=self.protein_nm * scale,
            electrolyte_nm=self.electrolyte_nm * scale,
            arc_nm=self.arc_nm * scale,
            axis_in_pore_nm=self.axis_in_pore_nm * scale,
        )

    def summary(self) -> dict[str, Canonicalisable]:
        """Return the table as plain data, for the stage-6 key and the manifest."""
        return {
            "global_nm": self.global_nm,
            "protein_nm": self.protein_nm,
            "electrolyte_nm": self.electrolyte_nm,
            "arc_nm": self.arc_nm,
            "axis_in_pore_nm": self.axis_in_pore_nm,
        }


SIZES = SizeTable()
"""Section 5.2.2's table, unscaled."""


@dataclass(frozen=True)
class WallSize:
    """The resolved wall target in nm, and its provenance."""

    wall_h_nm: float
    source: str
    debye_length_nm: float
    size_scale: float

    @property
    def debye_target_nm(self) -> float:
        """Return ``lambda_D / 5``, the target wall size, in nm."""
        return self.debye_length_nm / DEBYE_FRACTION

    @property
    def coarser_than_num30(self) -> bool:
        """Whether the wall size exceeds ``lambda_D / 5``; logged and recorded, not refused."""
        return self.wall_h_nm > self.debye_target_nm

    def summary(self) -> dict[str, Canonicalisable]:
        """Return the record the stage-6 key and the manifest carry."""
        return {
            "wall_h_nm": self.wall_h_nm,
            "source": self.source,
            "debye_length_nm": self.debye_length_nm,
            "size_scale": self.size_scale,
        }


def ionic_strength_M(document: CaseDocument) -> float:
    """Return the bulk ionic strength ``I = 1/2 sum z_i^2 c``, in mol/L."""
    concentration = document.electrolyte.concentration_M
    return 0.5 * sum(species.z**2 * concentration for species in document.electrolyte.species)


def case_debye_length_nm(document: CaseDocument, *, permittivity_0: float) -> float:
    """Return the case's Debye length ``lambda_D`` at ``eps_r,f0``, in nm."""
    return debye_length_nm(
        ionic_strength_M(document),
        relative_permittivity=permittivity_0,
        temperature_K=document.electrolyte.temperature_K,
    )


def resolve_wall_size(document: CaseDocument, *, permittivity_0: float) -> WallSize:
    """Return the wall target in nm: ``auto`` or the explicit value, times ``size_scale``."""
    mesh = document.numerics.mesh
    debye = case_debye_length_nm(document, permittivity_0=permittivity_0)
    if mesh.wall_h_nm == "auto":
        base = min(WALL_CEILING_NM, debye / DEBYE_FRACTION)
        source = "auto"
    else:
        base = float(mesh.wall_h_nm)
        source = "explicit"
    return WallSize(
        wall_h_nm=base * mesh.size_scale,
        source=source,
        debye_length_nm=debye,
        size_scale=mesh.size_scale,
    )


def corrected_debye_ratio(resolved: ResolvedCase, wall: WallSize) -> float:
    """Return the wall size over ``lambda_D / 5`` at the corrected ``eps_r,f(c)``."""
    concentration = resolved.concentration_M
    permittivity = float(resolved.electrolyte.relative_permittivity(concentration))
    corrected = debye_length_nm(
        ionic_strength_M(resolved.document),
        relative_permittivity=permittivity,
        temperature_K=resolved.temperature_K,
    )
    return wall.wall_h_nm / (corrected / DEBYE_FRACTION)


ARC_NAMES = frozenset({"cis", "trans", "membrane_outer"})
"""The boundary names of the reservoir arc, sized at ``arc_nm``."""

AXIS_TOLERANCE_NM = 1e-9
"""Slack on the test that an ``axis`` edge lies within the pore's axial extent."""


def edge_size(
    name: str,
    z_mid_nm: float,
    *,
    wall_h_nm: float | None,
    axis_extent_nm: tuple[float, float],
    sizes: SizeTable,
) -> float | None:
    """Return the size of a named boundary edge in nm, or ``None`` for none."""
    if name == "wall":
        return wall_h_nm
    if name in ARC_NAMES:
        return sizes.arc_nm
    if name == "axis":
        lower, upper = axis_extent_nm
        if lower - AXIS_TOLERANCE_NM < z_mid_nm < upper + AXIS_TOLERANCE_NM:
            return sizes.axis_in_pore_nm
    return None


EXCLUSION_SIZE = "wall_h_nm"
"""What the ``exclusion`` domain is sized at: the resolved wall target (WP30 D9).

A 0.25 nm shell then has about five elements across it at the default wall size,
and the protein-to-shell dielectric jump keeps the resolution the wall had there
before the shell moved ``wall`` outward. Keyed in a generated mesh's recipe only
when its region carries a shell, so no shell-free key moves.
"""


EXCLUSION_WALL_DIVISION = 1.1
"""On netgen, a shell's ``wall`` edge is cut into ``ceil(L / (1.1 wall_h))`` equal segments (WP30).

The shell's outer surface is a ring of straight edges ``L`` = 1.05-1.15 ``h_c``
long (:data:`nanopnp.geometry.region.EXCLUSION_RESAMPLE`), and netgen must keep
a node at each of their ends. Given only ``maxh = wall_h``, it cuts an edge into
about ``floor(L / wall_h + 0.4)`` segments [tested], so a wall target a little
under ``L``, or under ``L/2``, leaves segments up to 1.6 times it, and the
wall-size gate's 1.15 refuses the mesh. On 2WCD at ``a`` = 0.25 nm it did so at
0.045, 0.04, 0.035 and 0.0225 nm, which ``auto`` reaches between about 1.5 and
1.9 M and at 3 M, while 0.05, 0.03 and 0.0272 nm passed (``.knowledge/06``
section 8.1.4). Setting each such edge's ``maxh`` to ``L/n`` makes the count
``n`` whatever netgen's rounding, so the segments average at most 1.1 times
the target, under the gate's 1.15. Netgen's optimisation moves nodes along an
edge, and the longest measured was 1.15 times the target, against the gate's 2.
Where ``n`` is 1 the edge keeps ``wall_h``, so a mesh that needed no division
is unchanged: the default 0.05 nm leaves every edge of 2WCD's ring whole. Gmsh
needs no rule: it already cuts each edge into ``ceil(L / wall_h)`` segments, and
passes at every one of those targets [tested].
"""

EXCLUSION_WALL_RULE = f"ceil(L/({EXCLUSION_WALL_DIVISION:g} wall_h)) equal segments"
"""The rule as a netgen recipe with a shell records it, so that a change to it moves the key."""


def wall_divisions(length_nm: float, wall_h_nm: float) -> int:
    """Return how many equal segments a shell's ``wall`` edge is cut into."""
    return max(1, math.ceil(length_nm / (EXCLUSION_WALL_DIVISION * wall_h_nm)))


def divided_wall_size(length_nm: float, wall_h_nm: float) -> float:
    """Return the ``maxh`` that cuts a shell's ``wall`` edge into :func:`wall_divisions`."""
    count = wall_divisions(length_nm, wall_h_nm)
    return wall_h_nm if count == 1 else length_nm / count


def domain_size(name: str, sizes: SizeTable, *, wall_h_nm: float | None = None) -> float | None:
    """Return the size of a named domain in nm, or ``None`` for the global size."""
    if name == "protein":
        return sizes.protein_nm
    if name == "exclusion":
        return sizes.protein_nm if wall_h_nm is None else wall_h_nm
    if name == "electrolyte":
        return sizes.electrolyte_nm
    return None


def apply_sizes(
    shape: Shape,
    *,
    wall_h_nm: float | None,
    axis_extent_nm: tuple[float, float],
    sizes: SizeTable = SIZES,
    divide_wall: bool = False,
) -> None:
    """Set the size fields on a named region, in place, for netgen.

    Parameters
    ----------
    divide_wall
        Whether ``wall`` edges are cut into equal segments; set for ion-exclusion shells.
    """
    for edge in shape.edges:
        z_mid = 0.5 * (float(edge.start[1]) + float(edge.end[1]))
        name = str(edge.name)
        size = edge_size(
            name,
            z_mid,
            wall_h_nm=wall_h_nm,
            axis_extent_nm=axis_extent_nm,
            sizes=sizes,
        )
        if divide_wall and name == "wall" and wall_h_nm is not None:
            size = divided_wall_size(float(edge.mass), wall_h_nm)
        if size is not None:
            edge.maxh = size
    for face in shape.faces:
        size = domain_size(str(face.name), sizes, wall_h_nm=wall_h_nm)
        if size is not None:
            face.maxh = size

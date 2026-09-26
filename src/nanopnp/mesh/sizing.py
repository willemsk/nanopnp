"""The size fields of section 5.2.2, and the wall target NUM-30 resolves to (FR-10).

One table serves every region meshed from a profile. The reference geometry of
:mod:`nanopnp.mesh.reference` and stage 6's generator both apply it, so the
shipped reference mesh and a pipeline mesh of the same profile are meshed by the
same numbers, and a change to one is a change to both.

**The wall target has a ceiling** (section 5.3.1 NOTE on ``numerics.mesh``, and
the NUM-30 NOTE). ``wall_h_nm: auto`` resolves to
``size_scale * min(0.05 nm, lambda_D / 5)``. NUM-30's ``lambda_D / 5`` read
alone gives 0.27 nm at 0.05 M and 0.86 nm at 0.005 M, which is coarser than the
ion wall function's decay length, ``1 / 6.2 = 0.161`` nm
(``.knowledge/01-physics-epnpns.md`` section 8), coarser than stage 4's contour
resolution, and five times the 0.05 nm the validated reference used on its pore
boundary at every concentration (section 5.2.2). So the ceiling governs below
1.474 M and NUM-30 above it.

**lambda_D is taken at eps_r,f0**, the infinite-dilution permittivity of the
parameter file, and not at the concentration-corrected ``eps_r,f(c)``. NUM-30's
own check values are at ``eps_r,f0``, and with ``eps_r,f(c)`` switching the
permittivity correction off would move the mesh, so an ePNP-NS against PNP-NS
comparison would mix a discretisation change into the physics. The ratio to the
corrected value is recorded beside the mesh, not used (WP21 D7, D16).

Nothing here imports NGSolve or NumPy: the wall size is resolved when a sweep
plan decides its warm-start barriers (WP21 D15), which is no place to pay for a
mesher.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

from nanopnp.core.scaling import debye_length_nm
from nanopnp.materials.corrections import load_corrections

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.core.hashing import Canonicalisable
    from nanopnp.core.typing import Shape
    from nanopnp.io.case import CaseDocument, ResolvedCase

logger = logging.getLogger(__name__)

WALL_CEILING_NM = 0.05
"""The wall target's ceiling: section 5.2.2's pore-boundary maximum."""

DEBYE_FRACTION = 5.0
"""NUM-30's wall target is ``lambda_D`` divided by this."""

GRADING = 0.2
"""Netgen grading. Smaller grades faster; 0.2 is what the Phase-0 shapes use."""

OPTIMISATION_STEPS = 5
"""``optsteps2d``: the ``optimize("Netgen")`` pass section 5.2.2 requires."""


@dataclass(frozen=True)
class SizeTable:
    """The element sizes of section 5.2.2 other than the wall's, in nm.

    Parameters
    ----------
    global_nm
        Global maximum; the reference model's "Finer" preset.
    protein_nm
        Inside the pore body; section 5.2.2's "Extremely fine" preset. The
        assembled region has one electrolyte face, lumen and reservoirs
        together (VER-28 requires exactly three domains), so there is no lumen
        face to size: the lumen is refined by grading away from its wall.
    electrolyte_nm
        In the electrolyte away from a size field.
    arc_nm
        On the reservoir's outer boundary.
    axis_in_pore_nm
        On the symmetry axis over the pore's axial span.
    """

    global_nm: float = 10.0
    protein_nm: float = 0.1
    electrolyte_nm: float = 2.8
    arc_nm: float = 5.0
    axis_in_pore_nm: float = 0.075

    def scaled(self, scale: float) -> SizeTable:
        """Return this table with every size multiplied by ``scale`` (``size_scale``)."""
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
    """The resolved wall target, and what it was resolved from (NUM-30, WP21 D7).

    Parameters
    ----------
    wall_h_nm
        The element size imposed on ``wall``, ``size_scale`` applied.
    source
        ``auto`` or ``explicit``.
    debye_length_nm
        lambda_D at ``eps_r,f0``, the case temperature and the bulk ionic
        strength.
    size_scale
        ``numerics.mesh.size_scale``.
    """

    wall_h_nm: float
    source: str
    debye_length_nm: float
    size_scale: float

    @property
    def debye_target_nm(self) -> float:
        """NUM-30's ``lambda_D / 5``, in nm."""
        return self.debye_length_nm / DEBYE_FRACTION

    @property
    def coarser_than_num30(self) -> bool:
        """Whether the wall size exceeds ``lambda_D / 5``: logged and recorded, not refused."""
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
    """Return the bulk ionic strength ``I = 1/2 sum z_i^2 c``, in mol/L.

    Every species is at ``electrolyte.concentration_M`` in the bulk, which is the
    concentration scale's definition (NUM-09), so ``I = c`` for a 1:1 salt.
    """
    concentration = document.electrolyte.concentration_M
    return 0.5 * sum(species.z**2 * concentration for species in document.electrolyte.species)


def case_debye_length_nm(document: CaseDocument) -> float:
    """Return section 6.3's ``lambda_D`` for the case, at ``eps_r,f0`` (WP21 D7).

    ``sqrt(eps_0 eps_r,f0 R T / (2 F^2 I))``, through the one implementation in
    :func:`nanopnp.core.scaling.debye_length_nm`: a unit valence and the ionic
    strength in place of the concentration is the same formula for any salt.
    """
    permittivity = load_corrections(document.electrolyte.parameters).solvent.permittivity.eps_r0
    return debye_length_nm(
        ionic_strength_M(document),
        relative_permittivity=permittivity,
        temperature_K=document.electrolyte.temperature_K,
    )


def resolve_wall_size(document: CaseDocument) -> WallSize:
    """Return the wall target a generated mesh uses (section 5.3.1 NOTE on ``numerics.mesh``).

    ``auto`` is ``size_scale * min(0.05 nm, lambda_D / 5)``; an explicit number is
    used as written, times ``size_scale``. The case resolver has already refused
    an explicit value that is not finite and positive.

    Parameters
    ----------
    document
        The validated case. Taken rather than the resolved case so that a sweep
        plan can ask it of every point cheaply.
    """
    mesh = document.numerics.mesh
    debye = case_debye_length_nm(document)
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
    """Return the wall size over ``lambda_D / 5`` at the corrected ``eps_r,f(c)`` (WP21 D16).

    Recorded, not used: it says how far the mesh is from NUM-30 read against the
    permittivity the run actually solves with, which is what a reader comparing
    meshes across the correction switches wants to know.
    """
    concentration = resolved.concentration_M
    permittivity = float(resolved.electrolyte.relative_permittivity(concentration))
    corrected = debye_length_nm(
        ionic_strength_M(resolved.document),
        relative_permittivity=permittivity,
        temperature_K=resolved.temperature_K,
    )
    return wall.wall_h_nm / (corrected / DEBYE_FRACTION)


def apply_sizes(
    shape: Shape,
    *,
    wall_h_nm: float | None,
    axis_extent_nm: tuple[float, float],
    sizes: SizeTable = SIZES,
    tolerance_nm: float = 1e-9,
) -> None:
    """Set the section 5.2.2 size fields on a named region, in place.

    Applied by name, after naming, so the one table reaches every region the
    same way: ``wall`` at the wall target, the reservoir arc (``cis``, ``trans``,
    ``membrane_outer``) at ``arc_nm``, the stretch of ``axis`` over the pore's
    axial span at ``axis_in_pore_nm``, and the ``protein`` and ``electrolyte``
    faces at their domain sizes. The global size is the mesher's ``maxh``.

    Parameters
    ----------
    shape
        The glued region, every edge and face named.
    wall_h_nm
        The wall target; ``None`` leaves the wall to the other fields.
    axis_extent_nm
        The pore's axial extent, where the axis is split.
    sizes
        The table, with ``size_scale`` already applied.
    tolerance_nm
        Slack on the axial extent test.
    """
    lower, upper = axis_extent_nm
    arc = {"cis", "trans", "membrane_outer"}
    for edge in shape.edges:
        if edge.name == "wall":
            if wall_h_nm is not None:
                edge.maxh = wall_h_nm
        elif edge.name in arc:
            edge.maxh = sizes.arc_nm
        elif edge.name == "axis":
            start, end = edge.start, edge.end
            z_mid = 0.5 * (float(start[1]) + float(end[1]))
            if lower - tolerance_nm < z_mid < upper + tolerance_nm:
                edge.maxh = sizes.axis_in_pore_nm
    for face in shape.faces:
        if face.name == "protein":
            face.maxh = sizes.protein_nm
        elif face.name == "electrolyte":
            face.maxh = sizes.electrolyte_nm

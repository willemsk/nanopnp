"""Stage 6's generator: the stage-5 region meshed under the section 5.2.2 size fields (FR-10).

A generated mesh goes through the gates an ingested one does, by the route an
ingested one takes: it is written as MSH 4.1 and read back through
:func:`nanopnp.mesh.ingest.ingest`, which applies VER-27's naming gate, the
solid-permittivity gate of the section 5.3.1 NOTE (WP21 D11) and VER-10's
quality gate. One route in means a generated mesh cannot skip a gate a supplied
one would fail.

It then passes one gate an ingested mesh does not, because only here is there a
target to hold it to: the **wall-size gate** (section 5.3.1 NOTE on
``numerics.mesh``, WP21 D9). Netgen treats a size as a target, not a bound, and
on the reference profile and on 2WCD's stage-4 profile the ``wall`` segments'
mean length is 1.045-1.078 times the target and the longest 1.25-1.62 times
(WP21 plan, Design section 3). The bounds 1.15 and 2.0 sit above every measured
value. What they catch is a size field that did not reach the wall: the protein's
0.1 nm field and the polygon's own edges then govern, and the mean doubles.

Netgen is deterministic within one process and platform [tested] and not across
platforms (``.knowledge/07`` section 4), which is why the stage-6 artefact of a
generated mesh is keyed on its recipe and records its content hash beside the
key (WP21 D10, D13).
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.core.hashing import Canonicalisable
from nanopnp.geometry.region import RegionRecord, build_region
from nanopnp.io.case import SuppliedArtefact
from nanopnp.mesh.adapter import from_ngsolve, write_msh41
from nanopnp.mesh.ingest import IngestedMesh, ingest
from nanopnp.mesh.sizing import (
    GRADING,
    OPTIMISATION_STEPS,
    SIZES,
    SizeTable,
    WallSize,
    apply_sizes,
    corrected_debye_ratio,
    resolve_wall_size,
)

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.core.typing import Mesh, Shape
    from nanopnp.io.case import ResolvedCase
    from nanopnp.mesh.adapter import MeshData

logger = logging.getLogger(__name__)

BACKEND = "netgen"
"""The mesher this module drives; the Gmsh adapter is WP23's (CON-10)."""

WALL_MEAN_BOUND = 1.15
"""The ``wall`` segments' mean length may be at most this times the target (D9)."""

WALL_MAX_BOUND = 2.0
"""The longest ``wall`` segment may be at most this times the target (D9)."""

GATE_CONSTANTS: Mapping[str, Canonicalisable] = {
    "wall_mean_bound": WALL_MEAN_BOUND,
    "wall_max_bound": WALL_MAX_BOUND,
}
"""The wall-size gate's thresholds, which key the stage-6 artefact (D10)."""

MESH_FILENAME = "mesh.msh"
"""The generated mesh's file in the stage-6 workspace, and its payload file name."""


class WallSizeGateError(ValueError):
    """A generated mesh's ``wall`` is coarser than its size field asked for (QR-12).

    Parameters
    ----------
    criterion
        ``"mean wall segment length"`` or ``"longest wall segment"``.
    measured
        The measured value, as a length and a ratio to the target.
    threshold
        The bound, likewise.
    where
        The segment and its midpoint.
    """

    def __init__(self, criterion: str, measured: str, threshold: str, where: str) -> None:
        self.criterion = criterion
        self.measured = measured
        self.threshold = threshold
        self.where = where
        super().__init__(
            f"stage 6 wall-size gate, {criterion}: {measured}, against {threshold}, {where} "
            "(section 5.3.1 NOTE on numerics.mesh, FR-10)"
        )


@dataclass(frozen=True)
class WallStatistics:
    """The ``wall`` segment lengths of a mesh, against the target (D9).

    Parameters
    ----------
    target_nm
        The resolved wall size.
    count
        How many ``wall`` segments the mesh carries.
    mean_ratio, p95_ratio, max_ratio
        Mean, 95th percentile and maximum segment length over the target.
    longest
        The longest segment's index among the ``wall`` segments.
    longest_midpoint_nm
        Its midpoint ``(r, z)``.
    """

    target_nm: float
    count: int
    mean_ratio: float
    p95_ratio: float
    max_ratio: float
    longest: int
    longest_midpoint_nm: tuple[float, float]

    def summary(self) -> dict[str, Canonicalisable]:
        """Return the statistics the manifest's ``sizing`` block records (D16)."""
        return {
            "target_nm": self.target_nm,
            "segments": self.count,
            "mean_ratio": self.mean_ratio,
            "p95_ratio": self.p95_ratio,
            "max_ratio": self.max_ratio,
            "longest_midpoint_nm": list(self.longest_midpoint_nm),
        }


def wall_statistics(data: MeshData, target_nm: float) -> WallStatistics:
    """Measure the ``wall`` segments of ``data`` against ``target_nm``."""
    import numpy as np

    segments = data.edges_of("wall")
    ends = data.vertices[segments]
    lengths = np.linalg.norm(ends[:, 1] - ends[:, 0], axis=1)
    longest = int(np.argmax(lengths))
    midpoint = ends[longest].mean(axis=0)
    return WallStatistics(
        target_nm=target_nm,
        count=len(lengths),
        mean_ratio=float(lengths.mean() / target_nm),
        p95_ratio=float(np.percentile(lengths, 95.0) / target_nm),
        max_ratio=float(lengths[longest] / target_nm),
        longest=longest,
        longest_midpoint_nm=(float(midpoint[0]), float(midpoint[1])),
    )


def check_wall_size(statistics: WallStatistics) -> None:
    """Abort unless the ``wall`` segments meet the D9 bounds.

    Raises
    ------
    WallSizeGateError
        Naming the statistic, its value and bound, and the longest segment with
        its midpoint.
    """
    target = statistics.target_nm
    r_mid, z_mid = statistics.longest_midpoint_nm
    where = (
        f"the longest being wall segment {statistics.longest} of {statistics.count}, midpoint "
        f"(r, z) = ({r_mid:.4f}, {z_mid:.4f}) nm"
    )
    if statistics.mean_ratio > WALL_MEAN_BOUND:
        raise WallSizeGateError(
            "mean wall segment length",
            f"{statistics.mean_ratio * target:.5f} nm, {statistics.mean_ratio:.3f} x the target",
            f"{WALL_MEAN_BOUND} x the {target:.5f} nm target",
            where,
        )
    if statistics.max_ratio > WALL_MAX_BOUND:
        raise WallSizeGateError(
            "longest wall segment",
            f"{statistics.max_ratio * target:.5f} nm, {statistics.max_ratio:.3f} x the target",
            f"{WALL_MAX_BOUND} x the {target:.5f} nm target",
            where,
        )


def sizing_parameters(document_wall: WallSize, sizes: SizeTable) -> dict[str, Canonicalisable]:
    """Return the stage-6 recipe's ``sizing`` parameter (D10).

    The backend, the resolved wall size with its source and lambda_D,
    ``size_scale``, the scaled table, the grading, the optimisation steps and
    the wall-size gate's constants: everything that moves a vertex of a
    generated mesh or a verdict of its gate.
    """
    return {
        "backend": BACKEND,
        "wall": document_wall.summary(),
        "table": sizes.summary(),
        "grading": GRADING,
        "optsteps2d": OPTIMISATION_STEPS,
        "gate": dict(GATE_CONSTANTS),
    }


def mesh_shape(shape: Shape, sizes: SizeTable) -> Mesh:
    """Mesh a named, sized region with netgen at the table's global size.

    The one call both the reference geometry and stage 6 make, so the two cannot
    mesh the same region with different mesher settings.
    """
    import netgen.occ as occ
    import ngsolve as ngs

    geometry = occ.OCCGeometry(shape, dim=2)
    return ngs.Mesh(
        geometry.GenerateMesh(maxh=sizes.global_nm, grading=GRADING, optsteps2d=OPTIMISATION_STEPS)
    )


@dataclass(frozen=True)
class GeneratedMesh:
    """A generated mesh that passed every gate, and the record of how it was sized.

    Parameters
    ----------
    ingested
        The mesh as :func:`~nanopnp.mesh.ingest.ingest` read it back.
    wall
        The resolved wall size.
    sizes
        The table applied, ``size_scale`` included.
    statistics
        The wall-size gate's measurements.
    corrected_ratio
        The wall size over ``lambda_D / 5`` at ``eps_r,f(c)`` (D16).
    """

    ingested: IngestedMesh
    wall: WallSize
    sizes: SizeTable
    statistics: WallStatistics
    corrected_ratio: float

    def sizing(self) -> dict[str, Canonicalisable]:
        """Return the manifest's ``sizing`` block (D16)."""
        return {
            **sizing_parameters(self.wall, self.sizes),
            "debye_target_nm": self.wall.debye_target_nm,
            "num30_ratio": self.wall.wall_h_nm / self.wall.debye_target_nm,
            "num30_ratio_corrected": self.corrected_ratio,
            "wall_statistics": self.statistics.summary(),
        }

    def summary(self) -> dict[str, Canonicalisable]:
        """Return what the manifest's geometry-and-mesh group records (FR-25)."""
        summary: dict[str, Canonicalisable] = {
            "generated": True,
            "source": self.ingested.source.name,
            "source_sha256": self.ingested.source_hash,
            "content_hash": self.ingested.content_hash,
            **self.ingested.data.summary(),
            "groups": {},
            "quality": self.ingested.quality.summary(),
            "sizing": self.sizing(),
        }
        return summary


def generate(record: RegionRecord, resolved: ResolvedCase, directory: Path) -> GeneratedMesh:
    """Mesh the region, write it, read it back through the gate and check its wall (FR-10).

    Parameters
    ----------
    record
        Stage 5's region.
    resolved
        The case, which sets the sizes and says which names the run selects on.
    directory
        Where ``mesh.msh`` is written.

    Returns
    -------
    GeneratedMesh
        The gated mesh and its sizing record.

    Raises
    ------
    nanopnp.mesh.ingest.MeshVocabularyError
        On a naming failure, or a solid with no permittivity (D11).
    nanopnp.mesh.quality.MeshQualityError
        On a sliver, an inverted element or a negative radius (VER-10).
    WallSizeGateError
        On a wall coarser than its size field asked for (D9).
    """
    wall = resolve_wall_size(resolved.document)
    sizes = SIZES.scaled(wall.size_scale)
    if wall.coarser_than_num30:
        logger.warning(
            "the wall size %.4f nm is coarser than NUM-30's lambda_D/5 = %.4f nm; recorded, "
            "not refused (section 5.3.1 NOTE on numerics.mesh)",
            wall.wall_h_nm,
            wall.debye_target_nm,
        )
    shape = build_region(record)
    apply_sizes(shape, wall_h_nm=wall.wall_h_nm, axis_extent_nm=record.axis_split_nm, sizes=sizes)
    data = from_ngsolve(mesh_shape(shape, sizes))

    directory.mkdir(parents=True, exist_ok=True)
    path = write_msh41(data, directory / MESH_FILENAME)
    ingested = ingest(SuppliedArtefact(path=path, format="msh41"), resolved)
    statistics = wall_statistics(ingested.data, wall.wall_h_nm)
    check_wall_size(statistics)
    logger.info(
        "generated mesh: %d elements, wall %.4f nm (%s), wall segments mean %.3f and max %.3f "
        "x the target",
        ingested.data.element_count,
        wall.wall_h_nm,
        wall.source,
        statistics.mean_ratio,
        statistics.max_ratio,
    )
    return GeneratedMesh(
        ingested=ingested,
        wall=wall,
        sizes=sizes,
        statistics=statistics,
        corrected_ratio=corrected_debye_ratio(resolved, wall),
    )

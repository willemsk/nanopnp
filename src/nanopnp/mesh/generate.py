"""Stage 6's generator: the stage-5 region meshed under the section 5.2.2 size fields (FR-10)."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.core.hashing import Canonicalisable
from nanopnp.geometry.region import RegionRecord
from nanopnp.io.case import SuppliedArtefact
from nanopnp.mesh.adapter import write_msh41
from nanopnp.mesh.ingest import IngestedMesh, ingest
from nanopnp.mesh.meshers import create_mesher
from nanopnp.mesh.sizing import (
    EXCLUSION_SIZE,
    GRADING,
    SIZES,
    SizeTable,
    WallSize,
    corrected_debye_ratio,
    resolve_wall_size,
)

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.io.resolved import ResolvedCase
    from nanopnp.mesh.adapter import MeshData

logger = logging.getLogger(__name__)

WALL_MEAN_BOUND = 1.15
"""The ``wall`` segments' mean length may be at most this times the target."""

WALL_MAX_BOUND = 2.0
"""The longest ``wall`` segment may be at most this times the target."""

GATE_CONSTANTS: Mapping[str, Canonicalisable] = {
    "wall_mean_bound": WALL_MEAN_BOUND,
    "wall_max_bound": WALL_MAX_BOUND,
}
"""The wall-size gate's thresholds, which key the stage-6 artefact."""

COMMON_RECIPE_KEYS: frozenset[str] = frozenset(
    {"backend", "wall", "table", "grading", "gate", "exclusion"}
)
"""The stage-6 recipe's entries every backend shares; a mesher's own settings name none of them."""

MESH_FILENAME = "mesh.msh"
"""The generated mesh's file in the stage-6 workspace, and its payload file name."""


class WallSizeGateError(ValueError):
    """A generated mesh's ``wall`` is coarser than its size field asked for."""

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
    """The ``wall`` segment lengths of a mesh, against the target."""

    target_nm: float
    count: int
    mean_ratio: float
    p95_ratio: float
    max_ratio: float
    longest: int
    longest_midpoint_nm: tuple[float, float]

    def summary(self) -> dict[str, Canonicalisable]:
        """Return the statistics the manifest's ``sizing`` block records."""
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
    """Abort unless the ``wall`` segments meet the size bounds."""
    target = statistics.target_nm
    r_mid, z_mid = statistics.longest_midpoint_nm
    where = (
        f"the longest being wall segment {statistics.longest} of {statistics.count}, midpoint "
        f"(r, z) = ({r_mid:.4f}, {z_mid:.4f}) nm"
    )
    if not statistics.mean_ratio <= WALL_MEAN_BOUND:
        raise WallSizeGateError(
            "mean wall segment length",
            f"{statistics.mean_ratio * target:.5f} nm, {statistics.mean_ratio:.3f} x the target",
            f"{WALL_MEAN_BOUND} x the {target:.5f} nm target",
            where,
        )
    if not statistics.max_ratio <= WALL_MAX_BOUND:
        raise WallSizeGateError(
            "longest wall segment",
            f"{statistics.max_ratio * target:.5f} nm, {statistics.max_ratio:.3f} x the target",
            f"{WALL_MAX_BOUND} x the {target:.5f} nm target",
            where,
        )


def sizing_parameters(
    document_wall: WallSize, sizes: SizeTable, backend: str = "netgen", *, exclusion: bool = False
) -> dict[str, Canonicalisable]:
    """Return the stage-6 recipe's ``sizing`` parameter: everything that moves a generated mesh."""
    settings = create_mesher(backend).settings(exclusion=exclusion)
    clash = sorted(set(settings) & COMMON_RECIPE_KEYS)
    if clash:
        raise ValueError(
            f"mesher {backend!r} returns settings {', '.join(clash)}, which the common stage-6 "
            "recipe already keys; a mesher's settings carry only its own entries"
        )
    recipe: dict[str, Canonicalisable] = {
        "backend": backend,
        "wall": document_wall.summary(),
        "table": sizes.summary(),
        "grading": GRADING,
        **settings,
        "gate": dict(GATE_CONSTANTS),
    }
    if exclusion:
        recipe["exclusion"] = EXCLUSION_SIZE
    return recipe


def mesh_region(
    record: RegionRecord, wall_h_nm: float | None, sizes: SizeTable, backend: str
) -> tuple[MeshData, str]:
    """Mesh stage 5's region with the named backend; return the mesh and the version."""
    return create_mesher(backend).mesh(record, wall_h_nm, sizes)


@dataclass(frozen=True)
class GeneratedMesh:
    """A generated mesh that passed every gate, and the record of how it was sized.

    Parameters
    ----------
    wall
        The resolved wall size, in nm.
    exclusion
        Whether the region carries an ion-exclusion shell, which keys its size.
    """

    ingested: IngestedMesh
    wall: WallSize
    sizes: SizeTable
    statistics: WallStatistics
    corrected_ratio: float
    backend: str
    backend_version: str
    exclusion: bool = False

    def sizing(self) -> dict[str, Canonicalisable]:
        """Return the manifest's ``sizing`` block, the mesher's version beside it."""
        return {
            **sizing_parameters(self.wall, self.sizes, self.backend, exclusion=self.exclusion),
            "backend_version": self.backend_version,
            "debye_target_nm": self.wall.debye_target_nm,
            "num30_ratio": self.wall.wall_h_nm / self.wall.debye_target_nm,
            "num30_ratio_corrected": self.corrected_ratio,
            "wall_statistics": self.statistics.summary(),
        }

    def summary(self) -> dict[str, Canonicalisable]:
        """Return what the manifest's geometry-and-mesh group records."""
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
    """Mesh the region, write it, read it back through the gate and check its wall.

    Raises
    ------
    MeshVocabularyError, MeshQualityError, WallSizeGateError
        On the naming, quality and wall-size gates.
    """
    wall = resolve_wall_size(resolved.document, permittivity_0=resolved.electrolyte.permittivity_0)
    sizes = SIZES.scaled(wall.size_scale)
    backend = resolved.document.numerics.mesh.backend
    if wall.coarser_than_num30:
        logger.warning(
            "the wall size %.4f nm is coarser than NUM-30's lambda_D/5 = %.4f nm; recorded, "
            "not refused (section 5.3.1 NOTE on numerics.mesh)",
            wall.wall_h_nm,
            wall.debye_target_nm,
        )
    data, version = mesh_region(record, wall.wall_h_nm, sizes, backend)

    directory.mkdir(parents=True, exist_ok=True)
    path = write_msh41(data, directory / MESH_FILENAME)
    ingested = ingest(SuppliedArtefact(path=path, format="msh41"), resolved)
    statistics = wall_statistics(ingested.data, wall.wall_h_nm)
    check_wall_size(statistics)
    logger.info(
        "generated mesh (%s %s): %d elements, wall %.4f nm (%s), wall segments mean %.3f and max "
        "%.3f x the target",
        backend,
        version,
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
        backend=backend,
        backend_version=version,
        exclusion=record.exclusion is not None,
    )

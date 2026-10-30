"""Stage 6 for an idealised pore, and the gated .msh writer behind the mesh command."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.core.hashing import Canonicalisable
from nanopnp.mesh.adapter import MeshData, from_ngsolve, read, write_msh41
from nanopnp.mesh.ingest import apply_groups
from nanopnp.mesh.quality import QualityReport, check_quality, check_radii
from nanopnp.mesh.sizing import GATE_CONSTANTS, GRADING, WallSize

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.core.typing import Mesh
    from nanopnp.geometry.pore import IdealisedRegionRecord

IDEALISED_OPTIMISATION_STEPS = 3
"""``optsteps2d`` for an idealised pore: the old generator's mesh, which VER-62 records."""


def idealised_parameters(wall: WallSize, maxh_nm: float) -> dict[str, Canonicalisable]:
    """Return the stage-6 recipe of an idealised pore: everything that moves its mesh.

    Parameters
    ----------
    maxh_nm
        The global element size, already times ``size_scale``.
    """
    return {
        "backend": "netgen",
        "recipe": "idealised",
        "wall": wall.key(),
        "maxh_nm": maxh_nm,
        "grading": GRADING,
        "optsteps2d": IDEALISED_OPTIMISATION_STEPS,
        "gate": dict(GATE_CONSTANTS),
    }


def generate_idealised(record: IdealisedRegionRecord, *, maxh_nm: float, wall_h_nm: float) -> Mesh:
    """Mesh an idealised pore's shape with netgen, ungated; ``write_gated_msh`` gates the file."""
    import netgen.occ as occ
    import ngsolve as ngs

    geometry = occ.OCCGeometry(record.geometry().shape(wall_h_nm=wall_h_nm), dim=2)
    return ngs.Mesh(
        geometry.GenerateMesh(
            maxh=maxh_nm, grading=GRADING, optsteps2d=IDEALISED_OPTIMISATION_STEPS
        )
    )


def mesh_idealised(record: IdealisedRegionRecord, *, maxh_nm: float, wall_h_nm: float) -> MeshData:
    """Mesh an idealised pore into the adapter's form; its mouths are already named."""
    return from_ngsolve(generate_idealised(record, maxh_nm=maxh_nm, wall_h_nm=wall_h_nm))


def write_gated_msh(generated: Mesh, out: Path) -> tuple[MeshData, QualityReport, dict[str, str]]:
    """Write a generated mesh as msh41 at ``out`` after the quality and radius gates.

    Returns the mesh as read back with its groups mapped, its quality report and the group map.
    """
    data = from_ngsolve(generated)

    # The reference geometry leaves the two pore-mouth fluid-fluid seams at default; map them to
    # interface. Other unknown groups are refused by apply_groups.
    groups = {"default": "interface"} if "default" in data.boundaries else {}

    # The process id keeps two generators aimed at one destination from sharing a staging file.
    partial = out.with_name(f".{out.stem}.{os.getpid()}.partial{out.suffix}")
    where = f"the generated mesh {out.name!r}"
    try:
        write_msh41(data, partial)
        mapped, _applied = apply_groups(read(partial, format="msh41"), groups)
        quality = check_quality(mapped, where=where)
        check_radii(mapped, where=where)
        partial.replace(out)
    finally:
        partial.unlink(missing_ok=True)
    return mapped, quality, groups

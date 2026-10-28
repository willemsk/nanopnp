"""The cylindrical-pore mesher and the gated .msh writer behind the mesh command."""

from __future__ import annotations

import hashlib
import os
from importlib import metadata
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.mesh.adapter import MeshData, from_ngsolve, read, write_msh41
from nanopnp.mesh.defaults import (
    DEFAULT_CYLINDER_MEMBRANE_THICKNESS_NM,
    DEFAULT_CYLINDER_RESERVOIR_RADIUS_NM,
    DEFAULT_CYLINDER_WALL_H_NM,
    DEFAULT_MAXH_NM,
    DEFAULT_PORE_RADIUS_NM,
)
from nanopnp.mesh.ingest import apply_groups
from nanopnp.mesh.primitives import CylindricalPoreGeometry
from nanopnp.mesh.quality import QualityReport, check_quality, check_radii

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.core.typing import Mesh

__all__ = ["generate_cylinder", "mesh_cylinder", "mesher_identity", "write_gated_msh"]

# What decides a cylinder mesh beside its numbers: the mesher and the code that makes and gates it,
# the edge-naming tolerance included.
_MESHER_SOURCES = (
    "mesh/cylinder.py",
    "mesh/primitives.py",
    "mesh/quality.py",
    "mesh/ingest.py",
    "mesh/adapter.py",
    "geometry/tolerance.py",
)


def mesher_identity() -> str:
    """Return a digest of the mesher's version and of the sources that build and gate a cylinder.

    A cached mesh is reused only while this is unchanged.
    """
    package = Path(__file__).resolve().parents[1]
    digest = hashlib.sha256(metadata.version("ngsolve").encode())
    for name in _MESHER_SOURCES:
        digest.update((package / name).read_bytes())
    return digest.hexdigest()


def write_gated_msh(generated: Mesh, out: Path) -> tuple[MeshData, QualityReport, dict[str, str]]:
    """Write a generated mesh as msh41 at ``out`` after the quality and radius gates.

    Returns the mesh as read back with its groups mapped, its quality report and the group map.
    """
    data = from_ngsolve(generated)

    # OCC leaves the two pore-mouth fluid-fluid seams at default; map them to interface.
    # Other unknown groups are refused by apply_groups.
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


def generate_cylinder(
    *,
    pore_radius_nm: float = DEFAULT_PORE_RADIUS_NM,
    membrane_thickness_nm: float = DEFAULT_CYLINDER_MEMBRANE_THICKNESS_NM,
    reservoir_radius_nm: float = DEFAULT_CYLINDER_RESERVOIR_RADIUS_NM,
    maxh_nm: float = DEFAULT_MAXH_NM,
    wall_h_nm: float = DEFAULT_CYLINDER_WALL_H_NM,
) -> Mesh:
    """Mesh a cylindrical pore in a membrane, ungated; ``write_gated_msh`` gates the file."""
    if pore_radius_nm >= reservoir_radius_nm:
        raise ValueError(
            f"pore radius {pore_radius_nm:g} nm must be smaller than "
            f"reservoir radius {reservoir_radius_nm:g} nm"
        )
    geometry = CylindricalPoreGeometry(
        pore_radius_nm=pore_radius_nm,
        membrane_thickness_nm=membrane_thickness_nm,
        reservoir_radius_nm=reservoir_radius_nm,
    )
    # Ungated here; gated once in write_gated_msh, on the file as written.
    return geometry.generate(maxh_nm=maxh_nm, wall_h_nm=wall_h_nm, check_quality=False)


def mesh_cylinder(
    *,
    pore_radius_nm: float = DEFAULT_PORE_RADIUS_NM,
    membrane_thickness_nm: float = DEFAULT_CYLINDER_MEMBRANE_THICKNESS_NM,
    reservoir_radius_nm: float = DEFAULT_CYLINDER_RESERVOIR_RADIUS_NM,
    maxh_nm: float = DEFAULT_MAXH_NM,
    wall_h_nm: float = DEFAULT_CYLINDER_WALL_H_NM,
    out: Path,
) -> Path:
    """Mesh a cylindrical pore in a membrane, gate it and write it to ``out`` as msh41."""
    generated = generate_cylinder(
        pore_radius_nm=pore_radius_nm,
        membrane_thickness_nm=membrane_thickness_nm,
        reservoir_radius_nm=reservoir_radius_nm,
        maxh_nm=maxh_nm,
        wall_h_nm=wall_h_nm,
    )
    write_gated_msh(generated, out)
    return out

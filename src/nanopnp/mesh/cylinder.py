"""The cylindrical-pore mesher and the gated .msh writer behind the mesh command."""

from __future__ import annotations

import hashlib
from importlib import metadata
from pathlib import Path
from typing import TYPE_CHECKING

from nanopnp.mesh.defaults import (
    DEFAULT_CYLINDER_MEMBRANE_THICKNESS_NM,
    DEFAULT_CYLINDER_RESERVOIR_RADIUS_NM,
    DEFAULT_CYLINDER_WALL_H_NM,
    DEFAULT_MAXH_NM,
    DEFAULT_PORE_RADIUS_NM,
)
from nanopnp.mesh.idealised import write_gated_msh
from nanopnp.mesh.primitives import CylindricalPoreGeometry

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

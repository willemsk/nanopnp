"""Canonical sizing and mesh defaults for domain geometries and CLI meshers."""

from typing import Final

# Mesh cylinder defaults (CLI and idealised benchmark pore)
DEFAULT_PORE_RADIUS_NM: Final[float] = 2.0
DEFAULT_CYLINDER_MEMBRANE_THICKNESS_NM: Final[float] = 6.0
DEFAULT_CYLINDER_RESERVOIR_RADIUS_NM: Final[float] = 10.0
DEFAULT_MAXH_NM: Final[float] = 4.0
DEFAULT_WALL_H_NM: Final[float] = 0.2
DEFAULT_CYLINDER_WALL_H_NM: Final[float] = 0.35

# Geometry analytical specs (stage 5: membrane and reservoir half-disc)
DEFAULT_MEMBRANE_THICKNESS_NM: Final[float] = 2.8
DEFAULT_MEMBRANE_CENTRE_Z_NM: Final[float] = 0.0
DEFAULT_RESERVOIR_RADIUS_NM: Final[float] = 250.0

__all__ = [
    "DEFAULT_CYLINDER_MEMBRANE_THICKNESS_NM",
    "DEFAULT_CYLINDER_RESERVOIR_RADIUS_NM",
    "DEFAULT_CYLINDER_WALL_H_NM",
    "DEFAULT_MAXH_NM",
    "DEFAULT_MEMBRANE_CENTRE_Z_NM",
    "DEFAULT_MEMBRANE_THICKNESS_NM",
    "DEFAULT_PORE_RADIUS_NM",
    "DEFAULT_RESERVOIR_RADIUS_NM",
    "DEFAULT_WALL_H_NM",
]

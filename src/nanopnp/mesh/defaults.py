"""Canonical sizing and mesh defaults for domain geometries and CLI meshers."""

from __future__ import annotations

from typing import Final

# Mesh cylinder defaults (CLI and idealised benchmark pore). The case schema's own defaults
# (membrane 2.8 nm, reservoir 250 nm: SPECIFICATION.md section 4.1.1) live in io/case.py.
DEFAULT_PORE_RADIUS_NM: Final[float] = 2.0
DEFAULT_CYLINDER_MEMBRANE_THICKNESS_NM: Final[float] = 6.0
DEFAULT_CYLINDER_RESERVOIR_RADIUS_NM: Final[float] = 10.0
DEFAULT_MAXH_NM: Final[float] = 4.0
DEFAULT_WALL_H_NM: Final[float] = 0.2
DEFAULT_CYLINDER_WALL_H_NM: Final[float] = 0.35

__all__ = [
    "DEFAULT_CYLINDER_MEMBRANE_THICKNESS_NM",
    "DEFAULT_CYLINDER_RESERVOIR_RADIUS_NM",
    "DEFAULT_CYLINDER_WALL_H_NM",
    "DEFAULT_MAXH_NM",
    "DEFAULT_PORE_RADIUS_NM",
]

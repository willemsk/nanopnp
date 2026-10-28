"""Mesher adapters (netgen, gmsh), size fields, boundary layers, quality gates."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - annotations only; resolved lazily below
    from nanopnp.mesh.cylinder import mesh_cylinder as mesh_cylinder

__all__ = ["mesh_cylinder"]


def __getattr__(name: str) -> object:
    if name != "mesh_cylinder":
        raise AttributeError(f"module 'nanopnp.mesh' has no attribute {name!r}")
    value = importlib.import_module("nanopnp.mesh.cylinder").mesh_cylinder
    globals()[name] = value
    return value

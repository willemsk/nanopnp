"""PDB/mmCIF and trajectory IO, alignment, symmetry-axis detection, and structure preparation."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - annotations only
    from nanopnp.structure.orient import orient_pore as orient_pore

__all__ = ["orient_pore"]


def __getattr__(name: str) -> object:
    if name != "orient_pore":
        raise AttributeError(f"module 'nanopnp.structure' has no attribute {name!r}")
    value = getattr(importlib.import_module("nanopnp.structure.orient"), name)
    globals()[name] = value
    return value

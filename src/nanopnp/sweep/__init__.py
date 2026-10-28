"""Parameter sweeps, job-array dispatch and result collection (FR-24, SPECIFICATION.md §5.3.4)."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - annotations only; resolved lazily below
    from nanopnp.sweep.inmemory import Sweep as Sweep
    from nanopnp.sweep.inmemory import sweep as sweep

__all__ = ["Sweep", "sweep"]


def __getattr__(name: str) -> object:
    if name not in __all__:
        raise AttributeError(f"module 'nanopnp.sweep' has no attribute {name!r}")
    value = getattr(importlib.import_module("nanopnp.sweep.inmemory"), name)
    globals()[name] = value
    return value

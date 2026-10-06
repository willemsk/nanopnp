"""The exit-code table of section 3.1 NOTE (IF-02), as the CLI's own names for it.

The table and its classifier live in :mod:`nanopnp.core.errors`, because the
sweep runner, the example walker and the desktop shell classify a failure by the
same table and none of them sits above the CLI (``MOD-05``). This module names
them where a reader of the CLI looks first.
"""

from __future__ import annotations

from nanopnp.core.errors import (
    EXCLUDED,
    EXIT_CANCELLED,
    EXIT_CASE,
    EXIT_CODES,
    EXIT_CONVERGENCE,
    EXIT_GATE,
    EXIT_MEANINGS,
    EXIT_OK,
    EXIT_UNEXPECTED,
    EXIT_USAGE,
    classify,
)

__all__ = [
    "EXCLUDED",
    "EXIT_CANCELLED",
    "EXIT_CASE",
    "EXIT_CODES",
    "EXIT_CONVERGENCE",
    "EXIT_GATE",
    "EXIT_MEANINGS",
    "EXIT_OK",
    "EXIT_UNEXPECTED",
    "EXIT_USAGE",
    "classify",
]

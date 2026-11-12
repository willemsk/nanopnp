"""The default pore radius, in a module of its own so the CLI avoids loading pydantic and yaml."""

from __future__ import annotations

from typing import Final

DEFAULT_PORE_RADIUS_NM: Final[float] = 2.0

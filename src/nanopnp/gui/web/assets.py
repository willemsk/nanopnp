"""Where the workbench's static files are: the assets folder and the design tokens."""

from __future__ import annotations

from pathlib import Path

__all__ = ["ASSETS", "TOKENS"]

ASSETS = Path(__file__).resolve().parent / "assets"
# The wheel carries tokens.css beside the assets; a checkout reads the design's own copy.
TOKENS = (
    ASSETS / "tokens.css"
    if (ASSETS / "tokens.css").is_file()
    else Path(__file__).resolve().parents[4] / "docs" / "design" / "tokens.css"
)

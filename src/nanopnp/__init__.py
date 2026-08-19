"""nanopnp: continuum simulation of biological nanopores with the ePNP-NS framework.

The normative model is specified in ``SPECIFICATION.md`` section 4 and documented,
with its errata, in ``.knowledge/01-physics-epnpns.md``.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("nanopnp")
except PackageNotFoundError:  # pragma: no cover - only when running from a bare source tree
    __version__ = "0.0.0.dev0"

__all__ = ["__version__"]

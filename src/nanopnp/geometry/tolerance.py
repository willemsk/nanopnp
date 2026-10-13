"""The geometric tolerance the analytic geometries and the analyte share.

A module of its own, importing nothing, so :mod:`nanopnp.mesh.primitives` and
:mod:`nanopnp.geometry.analyte` reach it without loading pydantic and yaml
through :mod:`nanopnp.geometry.profile` (WP37 D6; REV-01).
"""

from __future__ import annotations

TOL_NM = 1e-9

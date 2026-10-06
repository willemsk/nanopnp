"""The geometric tolerance the analytic geometries and the analyte share.

A module of its own, importing nothing, so :mod:`nanopnp.mesh.primitives` and
:mod:`nanopnp.geometry.analyte` reach it without loading pydantic and yaml
through :mod:`nanopnp.geometry.profile` (WP37 D6; REV-01).
"""

from __future__ import annotations

TOL_NM = 1e-9
"""Geometric tolerance for classifying an edge by its centre of mass.

Public because :mod:`nanopnp.mesh.primitives` names the edges of its analytic
geometries against it and :mod:`nanopnp.geometry.analyte` classifies against the
same tolerance when it embeds a body in one of them; two tolerances that can
drift apart would put an edge in one geometry's vocabulary and not the other's.
"""

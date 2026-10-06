"""The public surface and package version (D9, REV-05).

Placed here rather than in the root ``__init__.py`` so that the root facade
can re-export both without inducing upward imports from ``cli/`` and ``gui/``
(§8.2.8 H6, REV-05). The facade re-exports them lazily or directly, and
:data:`nanopnp.PUBLIC` is :data:`nanopnp.core.public.PUBLIC`.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("nanopnp")
except PackageNotFoundError:  # pragma: no cover - only when running from a bare source tree
    __version__ = "0.0.0.dev0"

PUBLIC: dict[str, str] = {
    # Running a case (FR-27, IF-01).
    "run_case": "nanopnp.pipeline.run",
    "run_document": "nanopnp.pipeline.run",
    "RunResult": "nanopnp.pipeline.run",
    # The case file (IF-03, section 5.3.1).
    "CaseDocument": "nanopnp.io.case",
    "load_case": "nanopnp.pipeline.case",
    "loads_case": "nanopnp.pipeline.case",
    "dump_case": "nanopnp.io.case",
    "dumps_case": "nanopnp.io.case",
    "resolve": "nanopnp.pipeline.case",
    # The artefact store (section 5.3.2).
    "Store": "nanopnp.io.store",
    # The physics-model interface (FR-20, section 5.4.3): one class and a
    # declaration add a model (WP26 D16).
    "PhysicsModel": "nanopnp.physics.models",
    "TransportModel": "nanopnp.physics.models",
    "ModelDeclaration": "nanopnp.physics.models",
    "register_model": "nanopnp.physics.models",
    "registered_models": "nanopnp.physics.models",
    # Sweeps (FR-24, section 5.3.4).
    "plan_from_document": "nanopnp.sweep.plan",
    "run_plan": "nanopnp.sweep.run",
    # The stage protocol and its plumbing (FR-27).
    "Stage": "nanopnp.core.stages",
    "registered_stages": "nanopnp.core.stages",
    "Progress": "nanopnp.core.stages",
    "CancelToken": "nanopnp.core.stages",
    "CancelFlag": "nanopnp.core.stages",
    "Cancelled": "nanopnp.core.stages",
    "StageHook": "nanopnp.core.stages",
    "SolveHook": "nanopnp.core.stages",
    "ArtefactHook": "nanopnp.core.stages",
}
"""Each public name and the module that defines it; the API reference documents these."""

__all__ = ["PUBLIC", "__version__"]

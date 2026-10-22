"""The public surface and package version."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("nanopnp")
except PackageNotFoundError:  # pragma: no cover - only when running from a bare source tree
    __version__ = "0.0.0.dev0"

PUBLIC: dict[str, str] = {
    "run_case": "nanopnp.pipeline.run",
    "run_document": "nanopnp.pipeline.run",
    "RunResult": "nanopnp.pipeline.run",
    "Case": "nanopnp.pipeline.handle",
    "CaseDocument": "nanopnp.io.case",
    "load_case": "nanopnp.pipeline.case",
    "loads_case": "nanopnp.pipeline.case",
    "dump_case": "nanopnp.io.case",
    "dumps_case": "nanopnp.io.case",
    "resolve": "nanopnp.pipeline.case",
    "Store": "nanopnp.io.store",
    "PhysicsModel": "nanopnp.physics.models",
    "TransportModel": "nanopnp.physics.models",
    "ModelDeclaration": "nanopnp.physics.models",
    "register_model": "nanopnp.physics.models",
    "registered_models": "nanopnp.physics.models",
    "plan_from_document": "nanopnp.sweep.plan",
    "run_plan": "nanopnp.sweep.run",
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

__all__ = ["PUBLIC", "__version__"]

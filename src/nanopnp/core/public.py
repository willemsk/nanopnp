"""The public surface and package version."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("nanopnp")
except PackageNotFoundError:  # pragma: no cover - only when running from a bare source tree
    __version__ = "0.0.0.dev0"

PUBLIC: dict[str, str] = {
    "Case": "nanopnp.api.case",
    "Session": "nanopnp.api.session",
    "RunResult": "nanopnp.pipeline.run",
    "SweepResult": "nanopnp.api.sweep",
    "Artefact": "nanopnp.io.artefact",
    "Store": "nanopnp.io.store",
    "orient_pore": "nanopnp.structure.orient",
    "PhysicsModel": "nanopnp.physics.models",
    "TransportModel": "nanopnp.physics.models",
    "ModelDeclaration": "nanopnp.physics.models",
    "register_model": "nanopnp.physics.models",
    "registered_models": "nanopnp.physics.models",
    "Progress": "nanopnp.core.stages",
    "CancelToken": "nanopnp.core.stages",
    "CancelFlag": "nanopnp.core.stages",
    "Cancelled": "nanopnp.core.stages",
    "StageHook": "nanopnp.core.stages",
    "SolveHook": "nanopnp.core.stages",
    "ArtefactHook": "nanopnp.core.stages",
}

__all__ = ["PUBLIC", "__version__"]

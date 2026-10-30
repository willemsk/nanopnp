"""nanopnp: continuum simulation of biological nanopores with the ePNP-NS framework."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

from nanopnp.core.public import PUBLIC, __version__

if TYPE_CHECKING:  # pragma: no cover - annotations only; resolved lazily below
    # ``X as X`` marks a re-export; the type checker cannot read ``__all__`` through ``PUBLIC``.
    from nanopnp.api.case import Case as Case
    from nanopnp.api.session import Session as Session
    from nanopnp.core.stages import ArtefactHook as ArtefactHook
    from nanopnp.core.stages import CancelFlag as CancelFlag
    from nanopnp.core.stages import Cancelled as Cancelled
    from nanopnp.core.stages import CancelToken as CancelToken
    from nanopnp.core.stages import Progress as Progress
    from nanopnp.core.stages import SolveHook as SolveHook
    from nanopnp.core.stages import Stage as Stage
    from nanopnp.core.stages import StageHook as StageHook
    from nanopnp.core.stages import registered_stages as registered_stages
    from nanopnp.io.case import CaseDocument as CaseDocument
    from nanopnp.io.case import dump_case as dump_case
    from nanopnp.io.case import dumps_case as dumps_case
    from nanopnp.io.store import Store as Store
    from nanopnp.physics.models import ModelDeclaration as ModelDeclaration
    from nanopnp.physics.models import PhysicsModel as PhysicsModel
    from nanopnp.physics.models import TransportModel as TransportModel
    from nanopnp.physics.models import register_model as register_model
    from nanopnp.physics.models import registered_models as registered_models
    from nanopnp.pipeline.case import load_case as load_case
    from nanopnp.pipeline.case import loads_case as loads_case
    from nanopnp.pipeline.case import resolve as resolve
    from nanopnp.pipeline.run import RunResult as RunResult
    from nanopnp.pipeline.run import run_case as run_case
    from nanopnp.pipeline.run import run_document as run_document
    from nanopnp.structure.orient import orient_pore as orient_pore
    from nanopnp.sweep.plan import plan_from_document as plan_from_document
    from nanopnp.sweep.run import run_plan as run_plan

__all__ = ["__version__", *PUBLIC]


def __getattr__(name: str) -> object:
    module = PUBLIC.get(name)
    if module is None:
        raise AttributeError(f"module 'nanopnp' has no attribute {name!r}")
    value = getattr(importlib.import_module(module), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted({*globals(), *PUBLIC})

"""nanopnp: continuum simulation of biological nanopores with the ePNP-NS framework.

The normative model is specified in ``SPECIFICATION.md`` section 4 and documented,
with its errata, in ``.knowledge/01-physics-epnpns.md``.

The stable API is the set of names in :data:`__all__` (SPECIFICATION.md section 3.1,
the IF-01 public-surface NOTE). Every other module is internal and may change
before v1.0. The names are resolved lazily, on first attribute access (PEP 562), so
``import nanopnp`` imports neither NGSolve, Netgen nor NumPy: the command line, the
desktop shell and the sweep runner all import this package purely to introspect it,
and an eager re-export would charge each of them for a solver it never assembles.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

from nanopnp.core.public import PUBLIC, __version__

if TYPE_CHECKING:  # pragma: no cover - annotations only; resolved lazily below
    # The ``X as X`` spelling marks each as a re-export for the type checker and
    # the linter, which cannot read ``__all__`` through the ``PUBLIC`` table.
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
    from nanopnp.sweep.plan import plan_from_document as plan_from_document
    from nanopnp.sweep.run import run_plan as run_plan

__all__ = ["__version__", *PUBLIC]


def __getattr__(name: str) -> object:
    """Resolve a public name from its defining module on first access (PEP 562)."""
    module = PUBLIC.get(name)
    if module is None:
        raise AttributeError(f"module 'nanopnp' has no attribute {name!r}")
    value = getattr(importlib.import_module(module), name)
    globals()[name] = value  # later accesses skip this function
    return value


def __dir__() -> list[str]:
    """List the public surface alongside the module's own attributes."""
    return sorted({*globals(), *PUBLIC})

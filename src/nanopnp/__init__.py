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
from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING

try:
    __version__ = version("nanopnp")
except PackageNotFoundError:  # pragma: no cover - only when running from a bare source tree
    __version__ = "0.0.0.dev0"

if TYPE_CHECKING:  # pragma: no cover - annotations only; resolved lazily below
    # The ``X as X`` spelling marks each as a re-export for the type checker and
    # the linter, which cannot read ``__all__`` through the ``PUBLIC`` table.
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
    from nanopnp.io.case import load_case as load_case
    from nanopnp.io.case import loads_case as loads_case
    from nanopnp.io.case import resolve as resolve
    from nanopnp.io.run import RunResult as RunResult
    from nanopnp.io.run import run_case as run_case
    from nanopnp.io.run import run_document as run_document
    from nanopnp.io.store import Store as Store
    from nanopnp.sweep.plan import plan_from_document as plan_from_document
    from nanopnp.sweep.run import run_plan as run_plan

PUBLIC: dict[str, str] = {
    # Running a case (FR-27, IF-01).
    "run_case": "nanopnp.io.run",
    "run_document": "nanopnp.io.run",
    "RunResult": "nanopnp.io.run",
    # The case file (IF-03, section 5.3.1).
    "CaseDocument": "nanopnp.io.case",
    "load_case": "nanopnp.io.case",
    "loads_case": "nanopnp.io.case",
    "dump_case": "nanopnp.io.case",
    "dumps_case": "nanopnp.io.case",
    "resolve": "nanopnp.io.case",
    # The artefact store (section 5.3.2).
    "Store": "nanopnp.io.store",
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
}
"""Each public name and the module that defines it; the API reference documents these."""

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

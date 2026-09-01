"""Type aliases for values that cross the numeric/symbolic boundary.

NGSolve's ``CoefficientFunction``, a NumPy array and a plain float share no
common protocol, and its type information is not usable by a type checker.
NGSolve does ship pybind11-stubgen output — 24 ``.pyi`` files at 6.2.2606 — but
the package carries no ``py.typed`` marker, so PEP 561 has mypy skip them and
every name resolves to ``Any`` regardless. Supplying the marker only exposes
why: ``ngsolve/__init__.pyi`` does not parse, ending in ``ngslib =`` and
``ngsolve =`` with empty right-hand sides. Netgen ships no stubs at all.

So the aliases here are ``Any`` and will stay ``Any`` until upstream ships
parsing stubs behind a marker. Rather than scatter bare ``Any`` through the
signatures — which says nothing — they name what a value *is*, so a reader
learns from the annotation even though the type checker cannot.
"""

from __future__ import annotations

from typing import Any, TypeAlias

Numeric: TypeAlias = Any
"""A float, a NumPy array or an NGSolve ``CoefficientFunction``."""

Expression: TypeAlias = Any
"""A symbolic expression: coefficient, trial or test function, or a form of them."""

IntegralTerm: TypeAlias = Any
"""One assembled integral term, NGSolve's ``SumOfIntegrals``."""

AssembledForm: TypeAlias = Any
"""An ``ngsolve.BilinearForm`` or ``ngsolve.LinearForm``, carrying a matrix or a
vector rather than an unevaluated expression."""

Mesh: TypeAlias = Any
"""An ``ngsolve.Mesh``."""

Shape: TypeAlias = Any
"""A ``netgen.occ`` shape: a named face, or a glued compound of them."""

FESpace: TypeAlias = Any
"""An ``ngsolve.FESpace`` or a product of them."""

GridFunction: TypeAlias = Any
"""An ``ngsolve.GridFunction``."""

Option: TypeAlias = Any
"""A keyword argument passed straight through to NGSolve."""

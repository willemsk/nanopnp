"""Type aliases for values that cross the numeric/symbolic boundary.

NGSolve's ``CoefficientFunction``, a NumPy array and a plain float share no
common protocol, and NGSolve ships no type information at all. Rather than
scatter bare ``Any`` through the signatures — which says nothing — the aliases
here name what a value *is*, so a reader learns from the annotation even though
the type checker cannot.
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

FESpace: TypeAlias = Any
"""An ``ngsolve.FESpace`` or a product of them."""

GridFunction: TypeAlias = Any
"""An ``ngsolve.GridFunction``."""

Option: TypeAlias = Any
"""A keyword argument passed straight through to NGSolve."""

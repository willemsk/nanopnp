"""VER-72: a function-level import names only a costly or optional package."""

from __future__ import annotations

import ast
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest

from nanopnp.validation.modularity import Module, _scoped_imports, parse_package

DEFERRABLE: frozenset[str] = frozenset(
    {
        # The package itself: VER-61's `deferred_upward:` ratchet governs these.
        "nanopnp",
        # Costly to import (CLAUDE.md); timings in knowledge/07-software-stack/index.md.
        "ngsolve",
        "netgen",
        "numpy",
        "scipy",
        "meshio",
        "h5py",
        # Import names of pyproject.toml's optional extras; apbs_binary is test-only.
        "MDAnalysis",
        "gridData",
        "skimage",
        "shapely",
        "pdb2pqr",
        "propka",
        "gemmi",
        "PySide6",
        "gmsh",
        "matplotlib",
        "apbs_binary",
    }
)


@dataclass(frozen=True, order=True)
class Violation:
    path: str
    line: int
    name: str
    rule: str

    def __str__(self) -> str:
        return f"src/nanopnp/{self.path}:{self.line}: {self.name} ({self.rule})"


def _function_imports(module: Module) -> Iterator[ast.Import | ast.ImportFrom]:
    for statement, kind in _scoped_imports(module.tree):
        if kind == "deferred":
            yield statement


def deferred_imports(modules: tuple[Module, ...]) -> list[Violation]:
    found = []
    for module in modules:
        for statement in _function_imports(module):
            if isinstance(statement, ast.ImportFrom):
                names = ["nanopnp" if statement.level else statement.module or ""]
            else:
                names = [alias.name for alias in statement.names]
            for name in names:
                if name.split(".")[0] not in DEFERRABLE:
                    rule = "imported inside a function; import it at module scope"
                    found.append(Violation(module.path, statement.lineno, name, rule))
    return sorted(found)


def _report(violations: list[Violation]) -> str:
    return "\n".join(str(violation) for violation in violations)


# -- the package -------------------------------------------------------------------


def test_ver72_functions_import_only_costly_or_optional_packages() -> None:
    violations = deferred_imports(parse_package())
    assert violations == [], _report(violations)


# -- each guard fires --------------------------------------------------------------

ORACLE = "mesh/oracle_conventions.py"


@pytest.fixture
def oracle(tmp_path: Path) -> Callable[[str], tuple[Module, ...]]:

    def parse(source: str) -> tuple[Module, ...]:
        return parse_package(tmp_path, sources={ORACLE: source})

    return parse


@pytest.mark.parametrize(
    ("source", "line", "name"),
    [
        ("def f():\n    from collections.abc import Callable\n", 2, "collections.abc"),
        ("def f():\n    import json\n", 2, "json"),
        ("def f():\n    g = lambda: __import__('x')\n    import pydantic\n", 3, "pydantic"),
    ],
)
def test_ver72_a_function_level_stdlib_import_is_named(
    source: str, line: int, name: str, oracle: Callable[[str], tuple[Module, ...]]
) -> None:
    violations = [v for v in deferred_imports(oracle(source)) if v.path == ORACLE]
    assert [(v.line, v.name) for v in violations] == [(line, name)]
    assert f"src/nanopnp/{ORACLE}:{line}: {name}" in _report(violations)


def test_ver72_deferrable_and_type_checking_imports_are_admitted(
    oracle: Callable[[str], tuple[Module, ...]],
) -> None:
    source = (
        "from typing import TYPE_CHECKING\n"
        "if TYPE_CHECKING:\n    import json\n"
        "def f():\n    import numpy\n    import gmsh\n    from . import adapter\n"
        "    from nanopnp.core import errors\n    import scipy.sparse\n"
    )
    assert [v for v in deferred_imports(oracle(source)) if v.path == ORACLE] == []
    assert {"ngsolve", "numpy", "scipy", "meshio", "h5py"} <= DEFERRABLE

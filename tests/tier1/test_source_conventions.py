"""VER-72: the source conventions of CLAUDE.md, read from the syntax tree."""

from __future__ import annotations

import ast
import re
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from pathlib import Path

import pytest

from nanopnp.validation.modularity import PACKAGE, Module, _scoped_imports, parse_package

DEFERRABLE: frozenset[str] = frozenset(
    {
        # The package itself: VER-61's `deferred_upward:` ratchet governs these.
        "nanopnp",
        # Costly to import (CLAUDE.md); timings in .knowledge/07-software-stack/index.md.
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

PRIVATE_IMPORTS: Mapping[tuple[str, str, str], str] = {
    ("density/map.py", "nanopnp.density.grid", "_grid_data_module"): (
        "GridDataFormats' deferred loader, shared inside density"
    ),
    ("io/case_paths.py", "nanopnp.io.case", "_keys_of"): (
        "the schema walker, shared inside io since the case-path helpers moved out of case.py"
    ),
    ("io/case_paths.py", "nanopnp.io.case", "_model_of"): (
        "the schema walker, shared inside io since the case-path helpers moved out of case.py"
    ),
    ("pipeline/checks.py", "nanopnp.io.case_paths", "_literal_options"): (
        "a Literal's options, which check_document reads to name the accepted values"
    ),
    ("validation/charge.py", "nanopnp.charge.kernel", "_accumulate"): (
        "the deposit kernel's inner loop, which the charge harness drives directly"
    ),
    ("validation/charge.py", "nanopnp.charge.kernel", "_patches"): (
        "the deposit kernel's patch table, which the charge harness drives directly"
    ),
}

AMERICAN = re.compile(r"[iy]z(?:e|ing|ation|abl)")

WORDS = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+")

SIZE_STEM = re.compile(
    r"(?:re|over|under|down|up|out|cap|sub|pre"
    r"|max|min|step|chunk|batch|cell|mesh|grid|block|file|page)?(?:s|se|pr)"
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


def _absolute(module: Module, node: ast.ImportFrom) -> str:
    if not node.level:
        return node.module or ""
    package = module.name if module.is_package else module.name.rpartition(".")[0]
    for _ in range(node.level - 1):
        package = package.rpartition(".")[0]
    return f"{package}.{node.module}" if node.module else package


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


def private_imports(modules: tuple[Module, ...]) -> list[tuple[Violation, tuple[str, str, str]]]:
    found = []
    for module in modules:
        for node in ast.walk(module.tree):
            if not isinstance(node, ast.ImportFrom):
                continue
            source = _absolute(module, node)
            if source.split(".")[0] != "nanopnp" or source == module.name:
                continue
            for alias in node.names:
                if alias.name.startswith("_") and not alias.name.startswith("__"):
                    rule = f"private name of {source}; make it public or keep it there"
                    violation = Violation(module.path, node.lineno, alias.name, rule)
                    found.append((violation, (module.path, source, alias.name)))
    return sorted(found)


def unrecorded_private_imports(
    found: list[tuple[Violation, tuple[str, str, str]]],
    recorded: Mapping[tuple[str, str, str], str] = PRIVATE_IMPORTS,
) -> list[Violation]:
    return [violation for violation, key in found if key not in recorded]


def stale_private_imports(
    found: list[tuple[Violation, tuple[str, str, str]]],
    recorded: Mapping[tuple[str, str, str], str] = PRIVATE_IMPORTS,
) -> list[tuple[str, str, str]]:
    return sorted(set(recorded) - {key for _, key in found})


def _defined_names(tree: ast.AST) -> Iterator[tuple[str, int]]:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            yield node.name, node.lineno
        elif isinstance(node, ast.arg):
            yield node.arg, node.lineno
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            yield node.id, node.lineno
        elif isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store):
            yield node.attr, node.lineno


def _is_american(name: str) -> bool:
    for word in WORDS.findall(name):
        lowered = word.lower()
        for match in AMERICAN.finditer(lowered):
            if not SIZE_STEM.fullmatch(lowered[: match.start()]):
                return True
    return False


def american_names(modules: tuple[Module, ...]) -> list[Violation]:
    found = {
        Violation(module.path, line, name, "American spelling; nanopnp writes -ise")
        for module in modules
        for name, line in _defined_names(module.tree)
        if _is_american(name)
    }
    return sorted(found)


PRAGMA = re.compile(r"#\s*pragma[:\s]?\s*no\s*cover(?!\s*-\s*\S)", re.IGNORECASE)


def bare_pragmas(texts: Mapping[str, str]) -> list[Violation]:
    rule = "write the reason after it: # pragma: no cover - <why no test reaches it>"
    return sorted(
        Violation(path, number, "pragma: no cover", rule)
        for path, text in texts.items()
        for number, line in enumerate(text.splitlines(), start=1)
        if PRAGMA.search(line)
    )


def _report(violations: list[Violation]) -> str:
    return "\n".join(str(violation) for violation in violations)


# -- the package -------------------------------------------------------------------


def test_ver72_functions_import_only_costly_or_optional_packages() -> None:
    violations = deferred_imports(parse_package())
    assert violations == [], _report(violations)


def test_ver72_no_private_name_crosses_a_module_beyond_the_shrinking_list() -> None:
    found = private_imports(parse_package())
    unrecorded = unrecorded_private_imports(found)
    assert unrecorded == [], _report(unrecorded)
    stale = stale_private_imports(found)
    assert stale == [], f"no longer imported; delete from PRIVATE_IMPORTS: {stale}"


def test_ver72_every_defined_name_is_spelt_the_british_way() -> None:
    violations = american_names(parse_package())
    assert violations == [], _report(violations)


def test_ver72_every_coverage_exclusion_gives_its_reason() -> None:
    texts = {
        path.relative_to(PACKAGE).as_posix(): path.read_text(encoding="utf-8")
        for path in sorted(PACKAGE.rglob("*.py"))
    }
    violations = bare_pragmas(texts)
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


@pytest.mark.parametrize(
    ("source", "module"),
    [
        ("from nanopnp.numerics.linear import _REJECTED, __all__\n", "nanopnp.numerics.linear"),
        ("from .meshers import _REJECTED, __all__\n", "nanopnp.mesh.meshers"),
        ("from ..numerics.linear import _REJECTED, __all__\n", "nanopnp.numerics.linear"),
    ],
)
def test_ver72_a_private_import_across_modules_is_named(
    source: str, module: str, oracle: Callable[[str], tuple[Module, ...]]
) -> None:
    found = [(v, key) for v, key in private_imports(oracle(source)) if v.path == ORACLE]
    assert [(v.line, v.name, key[1]) for v, key in found] == [(1, "_REJECTED", module)]
    assert f"src/nanopnp/{ORACLE}:1: _REJECTED" in _report([v for v, _ in found])


def test_ver72_an_unused_allowlist_entry_is_stale() -> None:
    source = "from nanopnp.core.errors import classify\n"
    modules = parse_package(sources={"density/map.py": source})
    entry = ("density/map.py", "nanopnp.density.grid", "_grid_data_module")
    assert entry in PRIVATE_IMPORTS
    assert stale_private_imports(private_imports(modules)) == [entry]
    assert stale_private_imports(private_imports(parse_package())) == []


def test_ver72_a_private_import_missing_from_the_list_is_unrecorded(
    oracle: Callable[[str], tuple[Module, ...]],
) -> None:
    source = "from nanopnp.numerics.linear import _REJECTED\n"
    found = private_imports(oracle(source))
    unrecorded = [v for v in unrecorded_private_imports(found) if v.path == ORACLE]
    assert [(v.line, v.name) for v in unrecorded] == [(1, "_REJECTED")]
    recorded = {(ORACLE, "nanopnp.numerics.linear", "_REJECTED"): "a reason"}
    assert [v for v in unrecorded_private_imports(found, recorded) if v.path == ORACLE] == []


@pytest.mark.parametrize(
    ("source", "line", "name"),
    [
        ("class GmshInitializationError(Exception):\n    pass\n", 1, "GmshInitializationError"),
        ("def normalize(x):\n    return x\n", 1, "normalize"),
        ("def f(optimizer):\n    return optimizer\n", 1, "optimizer"),
        ("x = 1\nlinearized = x\n", 2, "linearized"),
        ("class A:\n    def f(self):\n        self.discretization = 1\n", 3, "discretization"),
        # A stem ending in s is no excuse: emphasize and synthesize must not pass as size.
        ("def emphasize(x):\n    return x\n", 1, "emphasize"),
        ("def f(synthesizer):\n    return synthesizer\n", 1, "synthesizer"),
        ("class Hypothesizer:\n    pass\n", 1, "Hypothesizer"),
        ("def analyze(x):\n    return x\n", 1, "analyze"),
        ("def f(x):\n    wall_analyzer = x\n    return wall_analyzer\n", 2, "wall_analyzer"),
        ("def f(serializable):\n    return serializable\n", 1, "serializable"),
        ("ANALYZABLE = 1\n", 1, "ANALYZABLE"),
    ],
)
def test_ver72_an_american_spelling_is_named(
    source: str, line: int, name: str, oracle: Callable[[str], tuple[Module, ...]]
) -> None:
    violations = [v for v in american_names(oracle(source)) if v.path == ORACLE]
    assert [(v.line, v.name) for v in violations] == [(line, name)]
    assert f"src/nanopnp/{ORACLE}:{line}: {name}" in _report(violations)


def test_ver72_size_seize_prize_and_foreign_calls_are_not_american(
    oracle: Callable[[str], tuple[Module, ...]],
) -> None:
    source = (
        "def sizing(wall_size, sizes, seized, prized):\n"
        "    gmsh.initialize()\n    model.isInitialized()\n    a.AssembleLinearization(b)\n"
        "class WallSize:\n    resize = 1\n    horizon = 2\n"
        "def oversized(capsize, presizing, downsized, sizeof, seizes, outsize):\n    pass\n"
        "def batched(maxsize, stepsize, chunksize, resizable, sizable):\n    pass\n"
    )
    assert [v for v in american_names(oracle(source)) if v.path == ORACLE] == []


def test_ver72_a_coverage_exclusion_without_a_reason_is_named() -> None:
    source = (
        "if a:  # pragma: no cover - the optional extra is missing\n"
        "    pass\n"
        "if b:  # pragma: no cover\n"
        "    pass\n"
        "if c:  # pragma: no cover -\n"
        "if d:  # pragma no cover\n"
        "if e:  # PRAGMA: NO COVER\n"
        "if f:  #pragma:no  cover\n"
        "if g:  # pragma no cover - spelt without a colon, with a reason\n"
    )
    violations = bare_pragmas({ORACLE: source})
    assert [(v.line, v.name) for v in violations] == [
        (3, "pragma: no cover"),
        (5, "pragma: no cover"),
        (6, "pragma: no cover"),
        (7, "pragma: no cover"),
        (8, "pragma: no cover"),
    ]
    assert f"src/nanopnp/{ORACLE}:3: pragma: no cover" in _report(violations)

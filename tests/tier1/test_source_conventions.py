"""VER-72: the source conventions of ``CLAUDE.md`` that a review would otherwise have to catch.

Four rules are read from the source, with no module of the package imported; the
first three from the syntax tree, through
:func:`nanopnp.validation.modularity.parse_package`:

- (a) an import inside a function names only what ``CLAUDE.md`` lets a function
  import: ``nanopnp`` itself (VER-61's ``deferred_upward:`` governs those), the
  costly core packages and an optional extra's package (:data:`DEFERRABLE`);
- (b) no module imports another module's private name, beyond the recorded
  :data:`PRIVATE_IMPORTS`, a list that only shrinks;
- (c) every name the package defines is spelt the British way: ``-ise`` and ``-yse``,
  not ``-ize`` and ``-yze`` (:data:`AMERICAN`);
- (f) every ``# pragma: no cover`` gives its reason on the same line, as
  ``# pragma: no cover - <reason>``: the push gate requires every changed line
  of ``src/nanopnp`` to be covered, and an exclusion is a claim a reviewer reads.

Checks (d) and (e) are the plans' records, in ``test_plan_records.py``.

Each check is shown to fire on a source substituted into the package, naming the
file, the line and the name, so none can pass by accepting everything.
"""

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
        # Core dependencies costly to import (CLAUDE.md, *Coding conventions*):
        # ngsolve ~370 ms, numpy ~67 ms, scipy.sparse ~260 ms (section 8.2.8 H12);
        # meshio ~170 ms and h5py ~140-180 ms (`python -X importtime`, measured for VER-72).
        "ngsolve",
        "netgen",
        "numpy",
        "scipy",
        "meshio",
        "h5py",
        # The import names of pyproject.toml's [project.optional-dependencies]:
        # `structure` (MDAnalysis, GridDataFormats, scikit-image, shapely, pdb2pqr
        # with its propka, gemmi), `gui`, `gmsh` and `examples`; and apbs-binary,
        # from the test-only `apbs` group, whose wheel exists on some platforms only.
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
"""The top-level packages a function may import (VER-72 a)."""

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
"""``(importing file, module, name)`` of each private import across modules kept for now.

The list only shrinks: an entry the source no longer makes fails, so renaming a
helper public removes its row in the same commit, and a new private import is
never fixed by recording it (VER-72 b).
"""

AMERICAN = re.compile(r"[iy]z(?:e|ing|ation|abl)")
"""An ``-ize`` or ``-yze`` family ending inside one lower-cased word of a name (VER-72 c).

``-ize``, ``-izes``, ``-ized``, ``-izer``, ``-izing``, ``-ization`` and ``-izable``
(*serializable*, *analyzable*), and the same after ``y``.
"""

WORDS = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z]+")
"""One word of a snake_case, CamelCase or UPPER_CASE name."""

SIZE_STEM = re.compile(
    r"(?:re|over|under|down|up|out|cap|sub|pre"
    r"|max|min|step|chunk|batch|cell|mesh|grid|block|file|page)?(?:s|se|pr)"
)
"""What may precede ``iz`` in ``size``, ``seize`` and ``prize`` and their compounds.

Only these: a stem ending in ``s`` is no excuse, or ``emphasize`` and
``synthesize`` would pass as ``size`` does. The compounds are written out, the
run-together ones of numerical code (``maxsize``, ``stepsize``, ``chunksize``)
among them.
"""


@dataclass(frozen=True, order=True)
class Violation:
    """One breach of a convention, where it is and what it names."""

    path: str
    line: int
    name: str
    rule: str

    def __str__(self) -> str:
        """Return ``src/nanopnp/<path>:<line>: <name> (<rule>)``, the diagnostic line."""
        return f"src/nanopnp/{self.path}:{self.line}: {self.name} ({self.rule})"


def _function_imports(module: Module) -> Iterator[ast.Import | ast.ImportFrom]:
    """Yield each import statement inside a function or lambda, once.

    VER-61's own reading of the syntax tree, whose ``deferred`` kind is exactly
    this, so the two checks cannot disagree on what a function-level import is.
    """
    for statement, kind in _scoped_imports(module.tree):
        if kind == "deferred":
            yield statement


def _absolute(module: Module, node: ast.ImportFrom) -> str:
    """Return the module an ``import from`` names, a relative one resolved against ``module``."""
    if not node.level:
        return node.module or ""
    package = module.name if module.is_package else module.name.rpartition(".")[0]
    for _ in range(node.level - 1):
        package = package.rpartition(".")[0]
    return f"{package}.{node.module}" if node.module else package


def deferred_imports(modules: tuple[Module, ...]) -> list[Violation]:
    """Return each function-level import of a package outside :data:`DEFERRABLE`."""
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
    """Return each ``from nanopnp.x import _name`` of another module, with its allowlist key.

    A relative import is resolved first, so ``from .kernel import _accumulate`` is
    the same breach as its absolute spelling.
    """
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
    """Return the private imports in ``found`` that ``recorded`` does not list."""
    return [violation for violation, key in found if key not in recorded]


def stale_private_imports(
    found: list[tuple[Violation, tuple[str, str, str]]],
    recorded: Mapping[tuple[str, str, str], str] = PRIVATE_IMPORTS,
) -> list[tuple[str, str, str]]:
    """Return the ``recorded`` entries that ``found`` no longer imports."""
    return sorted(set(recorded) - {key for _, key in found})


def _defined_names(tree: ast.AST) -> Iterator[tuple[str, int]]:
    """Yield ``(name, line)`` of each name a module defines.

    Definitions, classes, arguments and assignment targets, including attributes
    assigned (``self.x = …``). A call or an attribute read is someone else's API,
    ``gmsh.initialize`` among them, and is not a definition.
    """
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
    """Return each defined name with an ``-ize`` or ``-yze`` ending (British spelling)."""
    found = {
        Violation(module.path, line, name, "American spelling; nanopnp writes -ise")
        for module in modules
        for name, line in _defined_names(module.tree)
        if _is_american(name)
    }
    return sorted(found)


PRAGMA = re.compile(r"#\s*pragma[:\s]?\s*no\s*cover(?!\s*-\s*\S)", re.IGNORECASE)
"""A ``no cover`` pragma with no ``- <reason>`` after it (VER-72 f).

It reads every spelling coverage.py's own exclusion pattern does (``# pragma no
cover``, ``#pragma:no  cover``, upper case), because each of them excludes the line.
"""


def bare_pragmas(texts: Mapping[str, str]) -> list[Violation]:
    """Return each ``# pragma: no cover`` in ``{path: text}`` that gives no reason."""
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
"""A module substituted into the package by the tests below; it never exists on disk."""


@pytest.fixture
def oracle(tmp_path: Path) -> Callable[[str], tuple[Module, ...]]:
    """Return a parser of one substituted module, in an otherwise empty package.

    The checks judge each module alone, so the rest of the package would only
    cost a parse per case.
    """

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
        # Relative, resolved against the oracle's package, nanopnp.mesh.
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
    """The list shrinks: delete the import, and the recorded row is reported."""
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
        # `size` is no excuse for a stem that merely ends in `s`, and CLAUDE.md's own
        # example of the British spelling is `analyse`.
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

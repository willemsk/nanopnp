"""VER-45 — the public surface of ``nanopnp`` (IF-01, the section 3.1 public-surface NOTE).

The stable API is the set of names in ``nanopnp.__all__``, and the user documentation's
API reference is generated from the same table, so this file pins three things: the
set is what the documentation says it is, in both directions; every name is the
object at its documented module path rather than a copy or a wrapper; and the
top-level import stays solver-free, because the command line, the desktop shell and
the sweep runner all import the package purely to introspect it. The ``TYPE_CHECKING``
mirror the type checker reads is a second, hand-kept copy of the table, so it is
checked against it in both directions (``MOD-12``).
"""

from __future__ import annotations

import importlib
import json
import re
import subprocess
import sys

import pytest

import nanopnp
from nanopnp.cli.reference import render_api_reference
from nanopnp.validation.modularity import surface

EXPECTED = {
    "__version__",
    "run_case",
    "run_document",
    "RunResult",
    "CaseDocument",
    "load_case",
    "loads_case",
    "dump_case",
    "dumps_case",
    "resolve",
    "Store",
    "plan_from_document",
    "run_plan",
    "Stage",
    "registered_stages",
    "Progress",
    "CancelToken",
    "CancelFlag",
    "Cancelled",
    "StageHook",
    "SolveHook",
    # WP24 D1: ``run_case`` and ``run_document`` take ``on_artefact``, so the
    # protocol a caller implements for it is public beside the other two hooks.
    "ArtefactHook",
    # WP26 D16: a model is added as one class against the section 5.4.3 interface
    # and registered with its declaration (FR-20), so the interface is public.
    "PhysicsModel",
    "TransportModel",
    "ModelDeclaration",
    "register_model",
    "registered_models",
    # WP34 D9: ``with_section``, parked by WP31, is deliberately not here. It is an
    # editor affordance that changes no resolved case (WP31 D13), so adding it later
    # costs nothing, and Phase 4's API pass reviews it with the rest of the public
    # surface (section 8.2.6 F3, F4).
}
"""Written out, not derived: adding to the stable API is a decision, and this is where
it is seen being made."""


def test_ver45_all_is_the_documented_public_surface() -> None:
    """``__all__`` is the documented set, and the API reference documents exactly it.

    Read back from the rendered page's mkdocstrings directives, both directions,
    with each directive's module path the one the name is resolved from.
    """
    assert set(nanopnp.__all__) == EXPECTED
    assert len(nanopnp.__all__) == len(set(nanopnp.__all__)), "a name is listed twice"
    directives = re.findall(r"^::: ([\w.]+)\.(\w+)$", render_api_reference(), flags=re.M)
    documented = {name: module for module, name in directives}
    assert len(documented) == len(directives), "a name is documented twice"
    assert set(documented) == EXPECTED - {"__version__"}, "API reference and __all__ disagree"
    assert documented == nanopnp.PUBLIC


@pytest.mark.parametrize("name", sorted(EXPECTED - {"__version__"}))
def test_ver45_each_public_name_is_its_modules_object(name: str) -> None:
    """``nanopnp.<name>`` is the very object at its documented module path."""
    module = importlib.import_module(nanopnp.PUBLIC[name])
    assert getattr(nanopnp, name) is getattr(module, name)
    assert name in dir(nanopnp)


def test_ver45_an_unknown_name_raises_attribute_error() -> None:
    """The lazy lookup answers a misspelling the way a module does."""
    with pytest.raises(AttributeError, match="run_cases"):
        _ = nanopnp.run_cases  # type: ignore[attr-defined]


def test_ver45_the_type_checking_mirror_is_public() -> None:
    """``PUBLIC`` and its ``TYPE_CHECKING`` re-exports name the same set (``MOD-12``).

    The mirror is what mypy and the linter read, since neither can follow the
    lazy lookup. A name added to one and not the other type-checks a name that
    does not resolve, or resolves a name that does not type-check. Read from the
    syntax tree, and checked against the runtime table so the two readings agree.
    """
    shown = surface()
    assert shown.mirror_differs == ()
    assert set(shown.public) == set(nanopnp.PUBLIC)


def test_ver45_a_name_dropped_from_the_mirror_is_named() -> None:
    """The oracle: a package written by hand, one name short in its mirror."""
    sources = {
        "__init__.py": (
            "from typing import TYPE_CHECKING\n"
            "if TYPE_CHECKING:\n"
            "    from nanopnp.io.run import run_case as run_case\n"
            'PUBLIC = {"run_case": "nanopnp.io.run", "Store": "nanopnp.io.store"}\n'
        ),
    }
    assert surface(sources=sources).mirror_differs == ("Store",)


def test_ver45_import_nanopnp_imports_no_solver_and_no_numpy() -> None:
    """A fresh ``import nanopnp`` leaves NGSolve, Netgen and NumPy unimported.

    Asserted on ``sys.modules`` in a spawned interpreter, because this process
    has long since imported all three.
    """
    code = (
        "import sys, json\n"
        "import nanopnp\n"
        "dir(nanopnp)\n"
        "heavy = ('ngsolve', 'netgen', 'numpy')\n"
        "print(json.dumps(sorted(m for m in sys.modules if m.split('.')[0] in heavy)))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True
    )
    assert json.loads(result.stdout) == []

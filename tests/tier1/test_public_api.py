"""VER-45 — the public surface of ``nanopnp`` (IF-01, the section 3.1 public-surface NOTE).

The stable API is the set of names in ``nanopnp.__all__``, and the user documentation's
API reference is generated from the same table, so this file pins three things: the
set is what the documentation says it is, in both directions; every name is the
object at its documented module path rather than a copy or a wrapper; and the
top-level import stays solver-free, because the command line, the desktop shell and
the sweep runner all import the package purely to introspect it.
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

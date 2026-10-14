"""VER-45: the public surface of nanopnp (IF-01, the section 3.1 public-surface NOTE)."""

from __future__ import annotations

import importlib
import json
import re
import subprocess
import sys

import pytest

import nanopnp
import nanopnp.core.public
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
    # The protocol a caller implements for ``on_artefact`` is public beside the other hooks.
    "ArtefactHook",
    # A model is one class against the model interface, so the interface is public.
    "PhysicsModel",
    "TransportModel",
    "ModelDeclaration",
    "register_model",
    "registered_models",
    # ``with_section`` is deliberately absent: it changes no resolved case.
}


def test_ver45_all_is_the_documented_public_surface() -> None:
    assert nanopnp.PUBLIC is nanopnp.core.public.PUBLIC
    assert nanopnp.__version__ is nanopnp.core.public.__version__
    assert set(nanopnp.__all__) == EXPECTED
    assert len(nanopnp.__all__) == len(set(nanopnp.__all__)), "a name is listed twice"
    directives = re.findall(r"^::: ([\w.]+)\.(\w+)$", render_api_reference(), flags=re.M)
    documented = {name: module for module, name in directives}
    assert len(documented) == len(directives), "a name is documented twice"
    assert set(documented) == EXPECTED - {"__version__"}, "API reference and __all__ disagree"
    assert documented == nanopnp.PUBLIC


@pytest.mark.parametrize("name", sorted(EXPECTED - {"__version__"}))
def test_ver45_each_public_name_is_its_modules_object(name: str) -> None:
    module = importlib.import_module(nanopnp.PUBLIC[name])
    assert getattr(nanopnp, name) is getattr(module, name)
    assert name in dir(nanopnp)


def test_ver45_an_unknown_name_raises_attribute_error() -> None:
    with pytest.raises(AttributeError, match="run_cases"):
        _ = nanopnp.run_cases  # type: ignore[attr-defined]


# MOD-12
def test_ver45_the_type_checking_mirror_is_public() -> None:
    shown = surface()
    assert shown.mirror_differs == ()
    assert set(shown.public) == set(nanopnp.PUBLIC)


def test_ver45_each_mirrored_name_comes_from_the_module_public_names() -> None:
    shown = surface()
    assert shown.module_differs == ()
    assert dict(shown.public_modules) == nanopnp.PUBLIC
    assert nanopnp.PUBLIC["resolve"] == "nanopnp.pipeline.case"
    assert nanopnp.PUBLIC["run_case"] == "nanopnp.pipeline.run"


def test_ver45_a_name_mirrored_from_another_module_is_named() -> None:
    sources = {
        "__init__.py": (
            "from typing import TYPE_CHECKING\n"
            "if TYPE_CHECKING:\n"
            "    from nanopnp.io.case import resolve as resolve\n"
        ),
        "core/public.py": ('PUBLIC = {"resolve": "nanopnp.pipeline.case"}\n'),
    }
    assert surface(sources=sources).module_differs == (
        ("resolve", "nanopnp.pipeline.case", "nanopnp.io.case"),
    )


def test_ver45_a_name_dropped_from_the_mirror_is_named() -> None:
    sources = {
        "__init__.py": (
            "from typing import TYPE_CHECKING\n"
            "if TYPE_CHECKING:\n"
            "    from nanopnp.pipeline.run import run_case as run_case\n"
        ),
        "core/public.py": (
            'PUBLIC = {"run_case": "nanopnp.pipeline.run", "Store": "nanopnp.io.store"}\n'
        ),
    }
    assert surface(sources=sources).mirror_differs == ("Store",)


def test_ver45_import_nanopnp_imports_no_solver_and_no_numpy() -> None:
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

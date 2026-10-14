"""VER-65: the subpackages that reach the finite-element backend are the recorded ones (QR-13)."""

from __future__ import annotations

from pathlib import Path

import pytest

from nanopnp.validation.modularity import (
    PACKAGE,
    BackendImport,
    accepted_backend,
    backend_imports,
    compare_backend,
)

AXIS = PACKAGE / "structure" / "axis.py"
GRID = PACKAGE / "density" / "grid.py"


def test_ver65_live_backend_set_equals_the_record() -> None:
    comparison = compare_backend(backend_imports(), accepted_backend())
    assert comparison.equal, comparison.describe()


def test_ver65_the_record_holds_the_eleven_subpackages_of_h3_h11_and_wp38() -> None:
    assert set(accepted_backend()) == {
        "charge",
        "density",
        "geometry",
        "gui",
        "materials",
        "mesh",
        "numerics",
        "physics",
        "post",
        "solve",
        "validation",
    }


def test_ver65_a_new_backend_import_fails_naming_subpackage_module_and_line() -> None:
    text = AXIS.read_text(encoding="utf-8")
    use = backend_imports(sources={"structure/axis.py": f"import ngsolve\n{text}"})
    comparison = compare_backend(use, accepted_backend())
    assert not comparison.equal
    assert comparison.gained == (
        BackendImport("structure", "structure/axis.py", 1, "top", "ngsolve"),
    )
    assert comparison.lost == ()
    message = comparison.describe()
    assert "structure now reaches the finite-element backend" in message
    assert "structure/axis.py:1" in message
    assert "modularity-layering.yaml" in message


def test_ver65_a_subpackage_that_stops_reaching_the_backend_fails_as_lost() -> None:
    text = GRID.read_text(encoding="utf-8")
    assert text.count("    import ngsolve as ngs\n") == 1
    use = backend_imports(
        sources={"density/grid.py": text.replace("    import ngsolve as ngs\n", "")}
    )
    comparison = compare_backend(use, accepted_backend())
    assert comparison.gained == ()
    assert comparison.lost == ("density",)
    assert "density no longer reaches the finite-element backend" in comparison.describe()


SYNTHETIC = {
    "__init__.py": '"""Root; ``ngsolve.comp`` in a docstring is not a reference."""\n',
    "top/__init__.py": "",
    "top/m.py": "import netgen.occ\n",
    "deferred/__init__.py": "",
    "deferred/m.py": ("def f() -> None:\n    from ngsolve import H1\n"),
    "typing/__init__.py": "",
    "typing/m.py": (
        "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    from ngsolve.comp import Mesh\n"
    ),
    "string/__init__.py": "",
    "string/m.py": (
        'MODULE = "ngsolve.webgui"\n'
        'MESHER = "netgen"\n'  # 2: the mesher's name in a case file, not a module
    ),
    "clean/__init__.py": "",
    "clean/m.py": "import numpy\nfrom .. import top\n",
}
"""Five subpackages: one reference of each kind, and one with none; lines written by hand."""


def test_ver65_classifier_catches_each_kind_by_hand(tmp_path: Path) -> None:
    for relative, text in SYNTHETIC.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    use = backend_imports(tmp_path)
    assert use.imports == (
        BackendImport("deferred", "deferred/m.py", 2, "deferred", "ngsolve"),
        BackendImport("string", "string/m.py", 1, "string", "ngsolve.webgui"),
        BackendImport("top", "top/m.py", 1, "top", "netgen.occ"),
        BackendImport("typing", "typing/m.py", 3, "typing", "ngsolve.comp"),
    )
    assert list(use.modules) == ["deferred", "string", "top", "typing"]
    comparison = compare_backend(use, ["top", "clean"])
    assert [reference.node for reference in comparison.gained] == ["deferred", "string", "typing"]
    assert comparison.lost == ("clean",)


def test_ver65_accepted_backend_refuses_a_repeated_entry(tmp_path: Path) -> None:
    path = tmp_path / "layering.yaml"
    path.write_text("backend:\n  - mesh\n  - mesh\n", encoding="utf-8")
    with pytest.raises(ValueError, match="backend entry 2 repeats mesh"):
        accepted_backend(path)

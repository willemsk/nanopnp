"""VER-72 (h): the public API and every module carry the docstring the prose rule requires (L4)."""

from __future__ import annotations

import ast
from pathlib import Path

from nanopnp.core.public import PUBLIC

REPOSITORY = Path(__file__).resolve().parents[2]
SOURCE = REPOSITORY / "src"


def _tree(path: Path) -> ast.Module:
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def _module_path(source: Path, module: str) -> Path:
    base = source.joinpath(*module.split("."))
    return base / "__init__.py" if base.is_dir() else base.with_suffix(".py")


def missing_docstrings(source: Path, public: dict[str, str]) -> list[str]:
    problems = []
    for path in sorted(source.rglob("*.py")):
        if not ast.get_docstring(_tree(path)):
            problems.append(f"{path.relative_to(source).as_posix()}: no module docstring")
    for name, module in sorted(public.items()):
        path = _module_path(source, module)
        for node in _tree(path).body:
            if (
                isinstance(node, ast.FunctionDef | ast.ClassDef)
                and node.name == name
                and not ast.get_docstring(node)
            ):
                problems.append(f"{path.relative_to(source).as_posix()}:{node.lineno}: {name}")
    return problems


def test_ver72_h_every_module_and_public_name_has_a_docstring() -> None:
    assert missing_docstrings(SOURCE, PUBLIC) == []


def test_ver72_h_a_bare_module_and_a_bare_public_name_are_named(tmp_path: Path) -> None:
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "__init__.py").write_text('"""Package."""\n', encoding="utf-8")
    (package / "bare.py").write_text("x = 1\n", encoding="utf-8")
    (package / "api.py").write_text(
        '"""Api."""\n\n\ndef documented():\n    """Yes."""\n\n\ndef undocumented():\n    pass\n',
        encoding="utf-8",
    )
    problems = missing_docstrings(tmp_path, {"documented": "pkg.api", "undocumented": "pkg.api"})
    assert sorted(problems) == ["pkg/api.py:8: undocumented", "pkg/bare.py: no module docstring"]

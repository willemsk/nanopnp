"""VER-75: docstrings stay on public src names only and the prose share stays under its ceiling."""

from __future__ import annotations

import ast
import functools
import importlib.util
import io
import itertools
import tokenize
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_SCRIPT = _ROOT / ".claude/scripts/same_tree.py"
_spec = importlib.util.spec_from_file_location("same_tree", _SCRIPT)
assert _spec is not None and _spec.loader is not None
same_tree = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(same_tree)

# Measured at WP45's close, every bare string counted (src 11.48 %, tests 2.48 %), plus 1 point.
CEILING_SRC = 0.1248
CEILING_TESTS = 0.0348


def _is_private(name: str) -> bool:
    return name.startswith("_") and not (name.startswith("__") and name.endswith("__"))


def _string(node: ast.AST) -> ast.Constant | None:
    if (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    ):
        return node.value
    return None


def _docstring_node(node: ast.AST) -> ast.Constant | None:
    body = getattr(node, "body", None)
    return _string(body[0]) if body else None


def _assigned_name(node: ast.stmt) -> str | None:
    target = (
        node.targets[0]
        if isinstance(node, ast.Assign) and len(node.targets) == 1
        else node.target
        if isinstance(node, ast.AnnAssign)
        else None
    )
    return target.id if isinstance(target, ast.Name) else None


def _violations(tree: ast.Module, display: str, *, is_test: bool) -> list[str]:
    found: list[str] = []
    module_doc = _docstring_node(tree)
    if module_doc is not None:
        assert isinstance(module_doc.value, str)
        if len(module_doc.value.strip().splitlines()) > 1:
            found.append(f"{display}:{module_doc.lineno}: module docstring is not one line")

    def walk(node: ast.AST, public: bool, scope: str) -> None:
        local = isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        body = getattr(node, "body", None)
        if not is_test and isinstance(body, list):
            for before, statement in itertools.pairwise(body):
                name, doc = _assigned_name(before), _string(statement)
                if (
                    name is not None
                    and doc is not None
                    and (local or not public or _is_private(name))
                ):
                    found.append(f"{display}:{doc.lineno}: docstring on non-public {scope}{name}")
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
                name = f"{scope}{child.name}"
                child_public = public and not local and not _is_private(child.name) and not is_test
                doc = _docstring_node(child)
                if doc is not None and not child_public:
                    found.append(f"{display}:{doc.lineno}: docstring on non-public {name}")
                walk(child, child_public, f"{name}.")
            else:
                walk(child, public and not local, scope)

    walk(tree, True, "")
    return found


def _prose_lines(text: str, tree: ast.Module) -> tuple[int, int]:
    prose: set[int] = set()
    for node in ast.walk(tree):
        doc = _string(node) if isinstance(node, ast.stmt) else None
        if doc is not None and doc.end_lineno is not None:
            prose.update(range(doc.lineno, doc.end_lineno + 1))
    for tok in tokenize.generate_tokens(io.StringIO(text).readline):
        if tok.type == tokenize.COMMENT and not same_tree.is_directive(tok.string):
            prose.add(tok.start[0])
    return len(prose), len(text.splitlines())


def _scan(root: Path, *, is_test: bool) -> tuple[list[str], float]:
    violations: list[str] = []
    prose = total = 0
    for path in sorted(root.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        tree = ast.parse(text)
        violations += _violations(tree, str(path.relative_to(root)), is_test=is_test)
        p, t = _prose_lines(text, tree)
        prose += p
        total += t
    return violations, prose / total if total else 0.0


@functools.cache
def _scan_tree(root: Path, is_test: bool) -> tuple[tuple[str, ...], float]:
    violations, share = _scan(root, is_test=is_test)
    return tuple(violations), share


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_ver75_a_src_docstrings_only_on_public_names_and_modules_one_line() -> None:
    violations, _ = _scan_tree(_ROOT / "src" / "nanopnp", False)
    assert not violations, "\n".join(violations)


def test_ver75_a_tests_carry_no_function_or_class_docstring() -> None:
    violations, _ = _scan_tree(_ROOT / "tests", True)
    assert not violations, "\n".join(violations)


def test_ver75_a_private_function_docstring_fails_naming_file_line_and_name(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "m.py", '"""Module."""\n\n\ndef _helper() -> None:\n    """Private."""\n')
    violations, _ = _scan(tmp_path, is_test=False)
    assert violations == ["m.py:5: docstring on non-public _helper"]


def test_ver75_a_method_of_private_class_fails(tmp_path: Path) -> None:
    _write(
        tmp_path / "m.py",
        '"""Module."""\n\n\nclass _C:\n    def run(self) -> None:\n        """Doc."""\n',
    )
    violations, _ = _scan(tmp_path, is_test=False)
    assert violations == ["m.py:6: docstring on non-public _C.run"]


def test_ver75_a_public_function_docstring_passes(tmp_path: Path) -> None:
    _write(tmp_path / "m.py", '"""Module."""\n\n\ndef run() -> None:\n    """Run."""\n')
    assert _scan(tmp_path, is_test=False)[0] == []


def test_ver75_a_test_docstring_fails_naming_file_line_and_name(tmp_path: Path) -> None:
    _write(tmp_path / "t.py", '"""Module."""\n\n\ndef test_x() -> None:\n    """Doc."""\n')
    violations, _ = _scan(tmp_path, is_test=True)
    assert violations == ["t.py:5: docstring on non-public test_x"]


def test_ver75_a_two_line_module_docstring_fails(tmp_path: Path) -> None:
    _write(tmp_path / "m.py", '"""Module.\n\nMore.\n"""\n')
    violations, _ = _scan(tmp_path, is_test=False)
    assert violations == ["m.py:1: module docstring is not one line"]


def test_ver75_a_private_constant_docstring_fails_naming_file_line_and_name(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "m.py", '"""Module."""\n\nPUBLIC = 1\n"""Doc."""\n_LIMIT = 2\n"""Doc."""\n')
    violations, _ = _scan(tmp_path, is_test=False)
    assert violations == ["m.py:6: docstring on non-public _LIMIT"]


def test_ver75_a_function_nested_under_a_block_of_a_function_is_not_public(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "m.py",
        '"""Module."""\n\n\ndef run() -> None:\n    """Run."""\n    if True:\n'
        '        def inner() -> None:\n            """Doc."""\n',
    )
    violations, _ = _scan(tmp_path, is_test=False)
    assert violations == ["m.py:8: docstring on non-public run.inner"]


def test_ver75_b_attribute_docstrings_count_in_the_share(tmp_path: Path) -> None:
    _write(tmp_path / "m.py", 'X = 1\n"""What X is."""\n')
    assert _scan(tmp_path, is_test=False)[1] == pytest.approx(0.5)


def test_ver75_b_directive_comments_are_not_prose(tmp_path: Path) -> None:
    _write(
        tmp_path / "m.py",
        "x = 1  # type: ignore[assignment]\ny = 2  # noqa: F841\nz = 3  # pragma: no cover - r\n",
    )
    assert _scan(tmp_path, is_test=False)[1] == 0.0


def test_ver75_b_shebang_and_coding_line_are_not_prose(tmp_path: Path) -> None:
    _write(tmp_path / "m.py", "#!/usr/bin/env python\n# -*- coding: utf-8 -*-\nx = 1\n")
    assert _scan(tmp_path, is_test=False)[1] == 0.0


def test_ver75_b_docstring_and_comment_lines_count_in_the_share(tmp_path: Path) -> None:
    _write(tmp_path / "m.py", '"""Module."""\n# a comment\nx = 1\ny = 2\n')
    assert _scan(tmp_path, is_test=False)[1] == pytest.approx(0.5)


def test_ver75_b_substituted_tree_over_the_ceiling_fails_naming_the_share(
    tmp_path: Path,
) -> None:
    _write(tmp_path / "m.py", '"""Module."""\n# one\n# two\nx = 1\n')
    share = _scan(tmp_path, is_test=False)[1]
    with pytest.raises(AssertionError, match=r"prose share 75\.0%"):
        _check_share(share, CEILING_SRC, "src/nanopnp")


def _check_share(share: float, ceiling: float, label: str) -> None:
    assert share <= ceiling, f"{label}: prose share {share:.1%} exceeds the ceiling {ceiling:.1%}"


def test_ver75_b_src_prose_share_is_at_most_its_ceiling() -> None:
    _check_share(_scan_tree(_ROOT / "src" / "nanopnp", False)[1], CEILING_SRC, "src/nanopnp")


def test_ver75_b_tests_prose_share_is_at_most_its_ceiling() -> None:
    _check_share(_scan_tree(_ROOT / "tests", True)[1], CEILING_TESTS, "tests")

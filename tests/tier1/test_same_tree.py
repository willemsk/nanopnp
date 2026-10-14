"""The prose-strip tree check accepts prose-only edits and refuses any other (§8.2.11 L5)."""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[2] / ".claude/scripts/same_tree.py"
_spec = importlib.util.spec_from_file_location("same_tree", _SCRIPT)
assert _spec is not None and _spec.loader is not None
same_tree = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(same_tree)

pytestmark = pytest.mark.skipif(shutil.which("git") is None, reason="needs git")

_BASE = '''"""Module."""

from __future__ import annotations


def f(x: int) -> int:  # pragma: no cover - reason
    """Return x."""
    y = x  # type: ignore[assignment]
    z = y  # noqa: F841
    return x


def g() -> None:
    """Only a docstring."""


class C:
    """A class."""

    def m(self) -> int:
        # a comment that is
        # wrapped over two lines
        return 1
'''


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *args],
        check=True,
        capture_output=True,
    )


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        monkeypatch.delenv(name, raising=False)
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / "mod.py").write_text(_BASE, encoding="utf-8")
    _git(tmp_path, "add", "-A")
    _git(tmp_path, "commit", "-qm", "init")
    return tmp_path


def _failures(repo: Path, new: str | None) -> dict[str, str]:
    path = repo / "mod.py"
    if new is None:
        path.unlink()
    else:
        path.write_text(new, encoding="utf-8")
    return same_tree.check(repo, "HEAD")


def test_l5_unchanged_file_passes(repo: Path) -> None:
    assert _failures(repo, _BASE) == {}


def test_l5_removed_docstrings_pass(repo: Path) -> None:
    new = _BASE.replace('    """Return x."""\n', "").replace('    """A class."""\n\n', "")
    assert _failures(repo, new) == {}


def test_l5_docstring_only_body_replaced_by_ellipsis_passes(repo: Path) -> None:
    assert _failures(repo, _BASE.replace('    """Only a docstring."""', "    ...")) == {}


def test_l5_rewrapped_comment_passes(repo: Path) -> None:
    new = _BASE.replace("# a comment that is\n        # wrapped over two lines", "# one line")
    assert _failures(repo, new) == {}


def test_l5_changed_statement_fails_naming_the_file(repo: Path) -> None:
    assert _failures(repo, _BASE.replace("return 1", "return 2")) == {
        "mod.py": "syntax tree changed"
    }


@pytest.mark.parametrize(
    "directive", ["  # pragma: no cover - reason", "  # type: ignore[assignment]", "  # noqa: F841"]
)
def test_l5_removed_directive_comment_fails(repo: Path, directive: str) -> None:
    assert _failures(repo, _BASE.replace(directive, "")) == {"mod.py": "directive comments changed"}


def test_l5_renamed_function_fails(repo: Path) -> None:
    assert _failures(repo, _BASE.replace("def g()", "def h()")) == {"mod.py": "syntax tree changed"}


def test_l5_deleted_file_fails(repo: Path) -> None:
    assert _failures(repo, None) == {"mod.py": "file deleted"}


def test_l5_added_file_fails(repo: Path) -> None:
    (repo / "new.py").write_text("x = 1\n", encoding="utf-8")
    assert same_tree.check(repo, "HEAD") == {"new.py": "file added"}


def test_l5_path_filter_limits_the_check(repo: Path) -> None:
    (repo / "mod.py").write_text(_BASE.replace("return 1", "return 2"), encoding="utf-8")
    assert same_tree.check(repo, "HEAD", ["other"]) == {}


def test_l5_unparsable_file_fails_naming_it(repo: Path) -> None:
    assert _failures(repo, _BASE.replace('    """Only a docstring."""', "")) == {
        "mod.py": "does not parse"
    }


def test_l5_module_reading_its_doc_keeps_its_first_line(repo: Path) -> None:
    reads = _BASE.replace("class C:", "DESCRIPTION = __doc__\n\n\nclass C:")
    (repo / "mod.py").write_text(reads, encoding="utf-8")
    _git(repo, "commit", "-qam", "reads")
    assert _failures(repo, reads.replace('"""Module."""', '"""Module, now longer."""')) == {
        "mod.py": "module docstring's first line changed, and the module reads __doc__"
    }
    assert _failures(repo, reads.replace('"""Module."""', '"""Module.\n\nMore."""')) == {}

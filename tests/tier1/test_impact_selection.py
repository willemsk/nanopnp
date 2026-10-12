"""VER-74 — the commit hook's test-impact selection is sound (WP43 D2 to D5; §8.2.10 J2).

A toy repository, with a package under ``src/toy`` and its own tests, is recorded
once by ``tests/impact.py``'s pytest plugin. Each case then plants one change in a
copy and asks ``impact.select`` which tests it touches. Under-selection is the
failure that passes silently, so every route by which a test can depend on a
change has a case: a call, a module fixture, a session fixture, a child process,
a source file read as text and a changed test file. Every change the map cannot
attribute to functions falls back to the whole development selection, naming the
path that forced it.
"""

from __future__ import annotations

import importlib
import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path
from types import ModuleType

import pytest

TESTS = Path(__file__).resolve().parents[1]
pytestmark = [
    pytest.mark.skipif(
        sys.version_info < (3, 12), reason="the recorder uses sys.monitoring, Python 3.12 or later"
    ),
    pytest.mark.skipif(shutil.which("git") is None, reason="the map is keyed by a git tree"),
]

TOY: dict[str, str] = {
    "pyproject.toml": """
        [tool.pytest.ini_options]
        markers = ["extended: an end-to-end walk"]
        """,
    "src/toy/__init__.py": "",
    "src/toy/core.py": """
        LIMIT = 3


        def add(a, b):
            return a + b


        def scale(x):
            return x * 2
        """,
    "src/toy/prep.py": """
        def prepare():
            return 41
        """,
    "src/toy/deco.py": """
        REGISTRY = {}


        def register(name):
            def wrap(function):
                REGISTRY[name] = function
                return function

            return wrap


        @register("a")
        def a():
            return 1
        """,
    "src/toy/cli.py": """
        def main():
            from toy.core import add

            print(add(1, 2))
        """,
    "src/toy/data.yaml": "value: 1\n",
    "README.md": "# Toy\n",
    "tests/conftest.py": """
        import pytest


        @pytest.fixture(scope="session")
        def seeded():
            from toy.core import scale

            return scale(2)
        """,
    "tests/test_add.py": """
        def test_add():
            from toy.core import add

            assert add(1, 2) == 3
        """,
    "tests/test_module_fixture.py": """
        import pytest


        @pytest.fixture(scope="module")
        def prepared():
            from toy.prep import prepare

            return prepare()


        def test_first(prepared):
            assert prepared == 41


        def test_second(prepared):
            assert prepared + 1 == 42
        """,
    "tests/test_session_a.py": """
        def test_seed_a(seeded):
            assert seeded == 4
        """,
    "tests/test_session_b.py": """
        def test_seed_b(seeded):
            assert seeded == 4
        """,
    "tests/test_process.py": """
        import os
        import subprocess
        import sys
        from pathlib import Path


        def test_cli_in_a_child_process():
            source = Path(__file__).resolve().parents[1] / "src"
            env = {**os.environ, "PYTHONPATH": str(source)}
            out = subprocess.run(
                [sys.executable, "-c", "from toy.cli import main; main()"],
                capture_output=True, text=True, env=env, check=True,
            )
            assert out.stdout.strip() == "3"
        """,
    "tests/test_reads_source.py": """
        from pathlib import Path


        def test_core_defines_add():
            core = Path(__file__).resolve().parents[1] / "src/toy/core.py"
            assert "def add" in core.read_text()
        """,
    "tests/test_walk.py": """
        import pytest

        pytestmark = pytest.mark.extended


        def test_walk():
            from toy.core import add

            assert add(2, 2) == 4
        """,
    "tests/test_other.py": """
        def test_registry():
            from toy.deco import REGISTRY

            assert REGISTRY["a"]() == 1
        """,
}

ADD = "tests/test_add.py::test_add"
PROCESS = "tests/test_process.py::test_cli_in_a_child_process"
READS = "tests/test_reads_source.py::test_core_defines_add"
WALK = "tests/test_walk.py::test_walk"
OTHER = "tests/test_other.py::test_registry"
MODULE = ("tests/test_module_fixture.py::test_first", "tests/test_module_fixture.py::test_second")
SESSION = ("tests/test_session_a.py::test_seed_a", "tests/test_session_b.py::test_seed_b")


def _impact() -> ModuleType:
    if str(TESTS) not in sys.path:
        sys.path.insert(0, str(TESTS))
    return importlib.import_module("impact")


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _record(repo: Path, *extra: str) -> Path:
    """Record the toy suite's map with the plugin, as the push gate does; return its path."""
    path = repo.parent / f"{repo.name}-map.json"
    env = {
        **{k: v for k, v in os.environ.items() if not k.startswith(("GIT_", "PYTEST_", "COV"))},
        "PYTHONPATH": os.pathsep.join([str(TESTS), str(repo / "src")]),
    }
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "-p",
            "impact",
            "-p",
            "no:cacheprovider",
            f"--impact-record={path}",
            "--impact-source=src/toy",
            *extra,
            "tests",
        ],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return path


@pytest.fixture(scope="module")
def recorded(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    """Return the toy repository, committed, and the map recorded on its tree."""
    repo = tmp_path_factory.mktemp("toy") / "repo"
    for name, text in TOY.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(textwrap.dedent(text).lstrip(), encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-qm", "toy")
    return repo, _record(repo)


@pytest.fixture
def toy(recorded: tuple[Path, Path], tmp_path: Path) -> tuple[Path, Path]:
    """Return a private copy of the recorded repository, to plant one change in."""
    repo, recorded_map = recorded
    copy = tmp_path / "repo"
    shutil.copytree(repo, copy)
    # Each test gets its own copy of the map: some cases damage the one they are given.
    map_copy = tmp_path / recorded_map.name
    shutil.copy(recorded_map, map_copy)
    return copy, map_copy


def _edit(repo: Path, name: str, old: str, new: str) -> None:
    path = repo / name
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == 1, (name, old)
    path.write_text(text.replace(old, new), encoding="utf-8")


def test_ver74_an_unchanged_tree_selects_nothing(toy: tuple[Path, Path]) -> None:
    repo, path = toy
    selection = _impact().select(repo, path)
    assert selection.fallback is None
    assert selection.tests == ()


def test_ver74_a_body_change_selects_its_callers_children_and_readers(
    toy: tuple[Path, Path],
) -> None:
    """A call, a child process and a source read all select; an unrelated test does not."""
    repo, path = toy
    _edit(repo, "src/toy/core.py", "return a + b", "return b + a")
    selection = _impact().select(repo, path)
    assert selection.fallback is None
    assert {ADD, PROCESS, READS} <= set(selection.tests)
    assert OTHER not in selection.tests
    assert not set(MODULE) & set(selection.tests)


def test_ver74_the_development_selection_never_holds_an_extended_test(
    toy: tuple[Path, Path],
) -> None:
    """The hook asks without the walks (J2); the push gate's follow-up asks with them (J3)."""
    repo, path = toy
    _edit(repo, "src/toy/core.py", "return a + b", "return b + a")
    impact = _impact()
    assert WALK not in impact.select(repo, path).tests
    assert WALK in impact.select(repo, path, include_extended=True).tests


def test_ver74_a_function_only_a_module_fixture_calls_selects_the_whole_file(
    toy: tuple[Path, Path],
) -> None:
    """The fixture runs in the first test's setup; every test reading its value is selected."""
    repo, path = toy
    _edit(repo, "src/toy/prep.py", "return 41", "return 40 + 1")
    assert set(MODULE) <= set(_impact().select(repo, path).tests)


def test_ver74_a_function_only_a_session_fixture_calls_selects_every_user(
    toy: tuple[Path, Path],
) -> None:
    """A session fixture is set up once, by whichever test asks first; both users are selected."""
    repo, path = toy
    _edit(repo, "src/toy/core.py", "return x * 2", "return 2 * x")
    assert set(SESSION) <= set(_impact().select(repo, path).tests)


def test_ver74_a_changed_test_file_selects_itself_alone(toy: tuple[Path, Path]) -> None:
    repo, path = toy
    _edit(repo, "tests/test_other.py", '["a"]() == 1', '["a"]() >= 1')
    selection = _impact().select(repo, path)
    assert selection.fallback is None
    assert selection.tests == (OTHER,)


def test_ver74_a_prose_change_selects_nothing(toy: tuple[Path, Path]) -> None:
    repo, path = toy
    _edit(repo, "README.md", "# Toy", "# The toy")
    selection = _impact().select(repo, path)
    assert selection.fallback is None
    assert selection.tests == ()


@pytest.mark.parametrize(
    ("name", "old", "new"),
    [
        ("src/toy/core.py", "LIMIT = 3", "LIMIT = 4"),
        ("src/toy/core.py", "def add(a, b):", "def add(a, b=0):"),
        ("src/toy/deco.py", '@register("a")', '@register("b")'),
        ("src/toy/data.yaml", "value: 1", "value: 2"),
        ("tests/conftest.py", "return scale(2)", "return scale(2) + 0"),
        ("pyproject.toml", "an end-to-end walk", "a walk"),
    ],
    ids=["module-level", "signature", "decorator", "data", "conftest", "configuration"],
)
def test_ver74_a_change_outside_a_function_body_falls_back_naming_its_path(
    toy: tuple[Path, Path], name: str, old: str, new: str
) -> None:
    repo, path = toy
    _edit(repo, name, old, new)
    selection = _impact().select(repo, path)
    assert selection.fallback is not None
    assert name in selection.fallback


@pytest.mark.parametrize("change", ["added", "deleted", "renamed"])
def test_ver74_an_added_deleted_or_renamed_module_falls_back(
    toy: tuple[Path, Path], change: str
) -> None:
    repo, path = toy
    module = repo / "src/toy/prep.py"
    if change == "added":
        (repo / "src/toy/extra.py").write_text("def f():\n    return 1\n", encoding="utf-8")
        named = "src/toy/extra.py"
    elif change == "deleted":
        module.unlink()
        named = "src/toy/prep.py"
    else:
        module.rename(repo / "src/toy/preparation.py")
        named = "src/toy/prep.py"
    selection = _impact().select(repo, path)
    assert selection.fallback is not None
    assert named in selection.fallback


def test_ver74_changes_accumulate_from_the_recorded_tree_across_commits(
    toy: tuple[Path, Path],
) -> None:
    """A change committed after the map was recorded is still selected for at the next commit."""
    repo, path = toy
    _edit(repo, "src/toy/prep.py", "return 41", "return 40 + 1")
    _git(repo, "commit", "-qam", "first")
    _edit(repo, "tests/test_other.py", '["a"]() == 1', '["a"]() >= 1')
    tests = set(_impact().select(repo, path).tests)
    assert set(MODULE) | {OTHER} <= tests


@pytest.mark.parametrize("state", ["missing", "corrupt", "unknown-tree"])
def test_ver74_a_missing_or_unusable_map_falls_back(toy: tuple[Path, Path], state: str) -> None:
    repo, path = toy
    _edit(repo, "src/toy/core.py", "return a + b", "return b + a")
    if state == "missing":
        path = path.with_name("absent.json")
        expected = "no impact map"
    elif state == "corrupt":
        path.write_text("{not json", encoding="utf-8")
        expected = "unreadable"
    else:
        text = path.read_text(encoding="utf-8")
        tree = _git(repo, "rev-parse", "HEAD^{tree}")
        path.write_text(text.replace(tree, "0" * len(tree)), encoding="utf-8")
        expected = "tree"
    selection = _impact().select(repo, path)
    assert selection.fallback is not None
    assert expected in selection.fallback


def test_ver74_a_map_recorded_under_xdist_selects_as_a_serial_one(
    recorded: tuple[Path, Path], tmp_path: Path
) -> None:
    """Each worker writes its share; the merged map selects exactly what the serial one does."""
    repo, serial = recorded
    copy = tmp_path / "repo"
    shutil.copytree(repo, copy)
    parallel = _record(copy, "-n", "2")
    _edit(copy, "src/toy/core.py", "return a + b", "return b + a")
    impact = _impact()
    assert impact.select(copy, parallel).tests == impact.select(copy, serial).tests

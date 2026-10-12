"""Test-impact selection for the commit hook: a recorder, its map and a selector (WP43 D2-D4).

VER-74. A pytest plugin (``-p impact --impact-record=PATH --impact-source=src/nanopnp``)
notes, per test, every function under the source root the test started, every
Python or Markdown file it read as data, every directory it listed and whether it
started a process. ``select()`` then reads what changed between the tree the map
was recorded on and the working tree, from the git objects, and returns the tests
a change can affect, or a fallback naming the path that forced it.

The soundness argument is the plan's (``docs/plans/wp43-development-loop.md``,
Design section 1): a test whose started functions, read files and listed
directories are unchanged, in a tree whose import-time code is unchanged,
executes as it did when it was recorded. Every route the recorder cannot see
falls back to the whole development selection.

Recording, in more detail:

- ``sys.monitoring`` ``PY_START`` on a free tool id, each event disabled after
  its first hit and re-armed whenever a collector is pushed (a test, a fixture
  scoped wider than a function, its teardown) and whenever a module body starts,
  so a function already seen is seen again when an import calls it.
- A function started while a module body other than the interpreter's own entry
  point is on the stack runs at import: in a test module's body it is credited
  to every test of that file (``module:<path>``), in any other module's body, or
  with no test running at all, it is ``outside``, and a change to it falls back.
- A fixture scoped wider than a function is recorded under
  ``fixture:<baseid>::<name>``, setup and teardown, and credited to every test
  that requests it, on whichever ``pytest-xdist`` worker it ran.
- Audit hooks: ``open`` of a ``.py`` or ``.md`` file under the repository (the
  import system's own reads aside), ``os.listdir`` and ``os.scandir`` of a
  directory under it, and every way of starting a process, ``multiprocessing``'s
  included.

The module imports nothing from ``nanopnp``, so it records a toy repository as
well as this one. It is a command line too; ``.claude/hooks/gate.sh`` uses it::

    uv run python tests/impact.py select --map M [--extended]
    uv run python tests/impact.py merge --map M --part P --tree T
    uv run python tests/impact.py durations LOG
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import tempfile
from collections.abc import Generator, Iterable
from dataclasses import dataclass
from pathlib import Path
from types import CodeType, FrameType
from typing import Any

import pytest

SCHEMA = "nanopnp/impact/v1"
DURATIONS_SCHEMA = "nanopnp/durations/v1"
FALLBACK_EXIT = 3
"""The command line's exit status for a fallback: the caller runs the development selection."""

_TOOL_IDS = (3, 4)
_TOOL_NAME = "nanopnp-impact"
_PROCESS_EVENTS = frozenset(
    {
        "subprocess.Popen",
        "os.system",
        "os.exec",
        "os.posix_spawn",
        "os.spawn",
        "os.fork",
        "os.forkpty",
        "pty.spawn",
    }
)
_DIRECTORY_EVENTS = frozenset({"os.listdir", "os.scandir"})
_AUDITED = _PROCESS_EVENTS | _DIRECTORY_EVENTS | {"open"}
# multiprocessing's forkserver and spawn start their helpers through
# _posixsubprocess directly, which raises no audit event: the start is noted here.
_PROCESS_STARTERS = frozenset({("process.py", "BaseProcess.start")})
_SKIPPED_ROOTS = frozenset({".git", ".venv", ".tox", ".mypy_cache", ".ruff_cache", ".pytest_cache"})
_CO_OPTIMIZED = 0x0001
_STATUS = {"A": "added", "D": "deleted", "M": "modified", "T": "type changed", "U": "unmerged"}
_GIT_ENV_DROPPED = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_PREFIX")


# --------------------------------------------------------------------------- git


def _git_env() -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k not in _GIT_ENV_DROPPED}


def _git(repo: Path, *args: str, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        env=env if env is not None else _git_env(),
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {result.stderr.strip()}")
    return result.stdout


def working_tree(repo: Path) -> str:
    """Return the tree the working copy would commit as with ``git add -A``.

    Built in a throwaway index, as ``gate.sh`` builds its stamp, so it is
    independent of HEAD and of how the changes are later split into commits.
    Bytecode caches are left out, for a repository that does not ignore them.
    """
    index_path = Path(_git(repo, "rev-parse", "--git-path", "index").strip())
    if not index_path.is_absolute():
        index_path = repo / index_path
    with tempfile.TemporaryDirectory() as scratch:
        index = Path(scratch) / "index"
        if index_path.is_file():
            index.write_bytes(index_path.read_bytes())
        env = {**_git_env(), "GIT_INDEX_FILE": str(index)}
        _git(
            repo,
            "add",
            "-A",
            "--",
            ".",
            ":(exclude,glob)**/__pycache__/**",
            ":(exclude,glob)**/*.pyc",
            env=env,
        )
        return _git(repo, "write-tree", env=env).strip()


def default_map_path(repo: Path) -> Path:
    """Return ``<git common dir>/nanopnp-impact/map.json``, which every worktree shares."""
    common = Path(_git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir").strip())
    return common / "nanopnp-impact" / "map.json"


# --------------------------------------------------------------------- recording


class _Record:
    """What one scope executed and read: a test, a wide fixture, a test module's body."""

    __slots__ = ("dirs", "files", "functions", "process")

    def __init__(self) -> None:
        self.functions: set[str] = set()
        self.files: set[str] = set()
        self.dirs: set[str] = set()
        self.process = False

    def as_json(self) -> dict[str, Any]:
        return {
            "functions": sorted(self.functions),
            "files": sorted(self.files),
            "dirs": sorted(self.dirs),
            "process": self.process,
        }


class _Recorder:
    """Collects the records; one per process, installed while ``--impact-record`` is set."""

    def __init__(self, root: Path, source: str) -> None:
        self.root = os.path.realpath(root)
        self.prefix = self.root + os.sep
        self.source = source.strip("/").replace(os.sep, "/")
        self.source_prefix = self.source + "/"
        self.active: list[_Record] = []
        self.tests: dict[str, dict[str, Any]] = {}
        self.scopes: dict[str, _Record] = {}
        self.outside = _Record()
        self.base: frozenset[int] = frozenset()
        self.identities: dict[CodeType, str | None] = {}
        self.relpaths: dict[str, str | None] = {}
        self.preloaded: set[str] = set()
        self.recording = False
        self.tool: int | None = None

    # -- paths

    def relpath(self, path: str) -> str | None:
        """Return ``path`` relative to the repository, ``/``-separated, or None outside it."""
        cached = self.relpaths.get(path)
        if cached is not None or path in self.relpaths:
            return cached
        rel: str | None = None
        # "<frozen runpy>", "<string>": code with no file, never a path relative to the cwd.
        full = "" if path.startswith("<") else os.path.realpath(path)
        if full.startswith(self.prefix):
            rel = full[len(self.prefix) :].replace(os.sep, "/")
            if rel.split("/", 1)[0] in _SKIPPED_ROOTS or "/site-packages/" in rel:
                rel = None
        if len(self.relpaths) < 200_000:
            self.relpaths[path] = rel
        return rel

    def identity(self, code: CodeType) -> str | None:
        """Return ``<path>::<outer qualname>`` for a function under the source root, else None.

        A nested def, lambda or generator expression counts as its outer function.
        A module body and a class body are not functions: their code runs at import.
        """
        rel = self.relpath(code.co_filename)
        if rel is None or not rel.startswith(self.source_prefix):
            if (os.path.basename(code.co_filename), code.co_qualname) in _PROCESS_STARTERS:
                return "process"
            return None
        if not code.co_flags & _CO_OPTIMIZED:
            return None
        return f"{rel}::{code.co_qualname.split('.<locals>', 1)[0]}"

    # -- scopes

    def push(self, record: _Record) -> None:
        self.active.append(record)
        sys.monitoring.restart_events()

    def pop(self, record: _Record) -> None:
        for position in range(len(self.active) - 1, -1, -1):
            if self.active[position] is record:
                del self.active[position]
                return

    def targets(self, frame: FrameType | None) -> Iterable[_Record]:
        """Return the records an event at ``frame`` belongs to."""
        while frame is not None:
            code = frame.f_code
            if code.co_name == "<module>" and id(frame) not in self.base:
                rel = self.relpath(code.co_filename)
                if rel is not None and _is_test_file(rel):
                    return (self.scopes.setdefault(f"module:{rel}", _Record()),)
                return (self.outside,)
            frame = frame.f_back
        return self.active or (self.outside,)

    # -- events

    def on_start(self, code: CodeType, offset: int) -> object:
        if code.co_name == "<module>":
            # A module body (or exec'd code) is starting: re-arm every event, so a
            # function this test already started is seen again if the import calls it.
            sys.monitoring.restart_events()
            return sys.monitoring.DISABLE
        try:
            name = self.identities[code]
        except KeyError:
            name = self.identities[code] = self.identity(code)
        if name is not None:
            records = self.targets(sys._getframe(1))
            if name == "process":
                for record in records:
                    record.process = True
            else:
                for record in records:
                    record.functions.add(name)
        return sys.monitoring.DISABLE

    def on_audit(self, event: str, args: tuple[Any, ...], caller: FrameType) -> None:
        if caller.f_code.co_filename.startswith("<frozen importlib"):
            return  # the import system finding and reading a module, not a test reading data
        if event == "open":
            path = args[0]
            if isinstance(path, bytes):
                path = os.fsdecode(path)
            if not isinstance(path, str) or not path.endswith((".py", ".md", ".pyc")):
                return
            if path.endswith(".pyc"):
                path = _source_of_bytecode(path)
            rel = self.relpath(os.path.join(os.getcwd(), path))
            if rel is not None:
                for record in self.credited(caller):
                    record.files.add(rel)
        elif event in _DIRECTORY_EVENTS:
            directory = "." if args[0] is None else args[0]
            if isinstance(directory, bytes):
                directory = os.fsdecode(directory)
            if not isinstance(directory, str):
                return
            rel = self.relpath(os.path.join(os.getcwd(), directory))
            if rel is not None:
                for record in self.credited(caller):
                    record.dirs.add("" if rel == "." else rel)
        elif event in _PROCESS_EVENTS:
            for record in self.credited(caller):
                record.process = True

    def credited(self, caller: FrameType) -> Iterable[_Record]:
        """Return the records an audited event belongs to.

        Outside a test, only an event the repository's own code caused counts:
        pytest collecting files, or xdist starting its workers, is not a dependency.
        """
        records = self.targets(caller)
        if records == (self.outside,) and not self.from_repository(caller):
            return ()
        return records

    def from_repository(self, frame: FrameType | None) -> bool:
        """Return whether code of the repository, this module aside, is on the stack."""
        while frame is not None:
            filename = frame.f_code.co_filename
            if filename != __file__ and self.relpath(filename) is not None:
                return True
            frame = frame.f_back
        return False

    # -- life cycle

    def start(self) -> None:
        monitoring = sys.monitoring
        taken = {tool: monitoring.get_tool(tool) for tool in _TOOL_IDS}
        free = [tool for tool, owner in taken.items() if owner is None]
        if not free:
            names = ", ".join(f"{tool} by {owner}" for tool, owner in taken.items())
            raise pytest.UsageError(
                f"--impact-record needs a free sys.monitoring tool id; both are in use: {names}"
            )
        self.tool = free[0]
        monitoring.use_tool_id(self.tool, _TOOL_NAME)
        monitoring.register_callback(self.tool, monitoring.events.PY_START, self.on_start)
        frames = set()
        frame: FrameType | None = sys._getframe(0)
        while frame is not None:
            if frame.f_code.co_name == "<module>":
                frames.add(id(frame))
            frame = frame.f_back
        self.base = frozenset(frames)
        source = self.prefix + self.source.replace("/", os.sep) + os.sep
        for module in list(sys.modules.values()):
            origin = getattr(module, "__file__", None)
            if isinstance(origin, str) and os.path.realpath(origin).startswith(source):
                rel = self.relpath(origin)
                if rel is not None:
                    self.preloaded.add(rel)
        self.recording = True
        monitoring.set_events(self.tool, monitoring.events.PY_START)

    def stop(self) -> None:
        self.recording = False
        if self.tool is not None:
            monitoring = sys.monitoring
            monitoring.set_events(self.tool, 0)
            monitoring.register_callback(self.tool, monitoring.events.PY_START, None)
            monitoring.free_tool_id(self.tool)
            self.tool = None

    def as_json(self, tree: str | None, extended: bool) -> dict[str, Any]:
        outside = self.outside.as_json()
        outside["preloaded"] = sorted(self.preloaded)
        return {
            "schema": SCHEMA,
            "tree": tree,
            "source": self.source,
            "extended": extended,
            "tests": self.tests,
            "scopes": {key: record.as_json() for key, record in sorted(self.scopes.items())},
            "outside": outside,
        }


def _source_of_bytecode(path: str) -> str:
    """Map ``pkg/__pycache__/mod.cpython-312.pyc`` to ``pkg/mod.py``."""
    head, name = os.path.split(path)
    if os.path.basename(head) == "__pycache__":
        return os.path.join(os.path.dirname(head), name.split(".", 1)[0] + ".py")
    return path[:-1]


def _is_test_file(rel: str) -> bool:
    name = rel.rsplit("/", 1)[-1]
    return rel.startswith("tests/") and name.startswith("test_") and name.endswith(".py")


_RECORDER: _Recorder | None = None


def _audit(event: str, args: tuple[Any, ...]) -> None:
    # The event is checked first: sys._getframe raises an audit event of its own.
    if event in _AUDITED:
        recorder = _RECORDER
        if recorder is not None and recorder.recording:
            recorder.on_audit(event, args, sys._getframe(1))


# ------------------------------------------------------------------ pytest hooks


def pytest_addoption(parser: pytest.Parser) -> None:
    group = parser.getgroup("impact", "test-impact recording (tests/impact.py, WP43)")
    group.addoption(
        "--impact-record",
        metavar="PATH",
        default=None,
        help="record which source functions and files each test touches into the map at PATH",
    )
    group.addoption(
        "--impact-source",
        metavar="DIR",
        default="src/nanopnp",
        help="the source root, relative to the rootdir (default: src/nanopnp)",
    )


@pytest.hookimpl(tryfirst=True)
def pytest_load_initial_conftests(early_config: pytest.Config) -> None:
    """Start recording before the conftests import the package under test."""
    global _RECORDER
    path = early_config.known_args_namespace.impact_record
    if not path or _RECORDER is not None:
        return
    if sys.version_info < (3, 12):
        version = ".".join(map(str, sys.version_info[:3]))
        raise pytest.UsageError(
            f"--impact-record needs sys.monitoring, Python 3.12 or later; this is Python {version}"
        )
    recorder = _Recorder(early_config.rootpath, early_config.known_args_namespace.impact_source)
    _RECORDER = recorder
    sys.addaudithook(_audit)
    recorder.start()


def pytest_configure(config: pytest.Config) -> None:
    recorder = _RECORDER
    if recorder is None or not config.getoption("impact_record"):
        return
    config.pluginmanager.register(_Plugin(config, recorder), "impact-recorder")


class _Plugin:
    """The per-session half of the recorder: scopes, and the map written at the end."""

    def __init__(self, config: pytest.Config, recorder: _Recorder) -> None:
        self.config = config
        self.recorder = recorder
        self.path = Path(config.getoption("impact_record")).resolve()
        workerinput = getattr(config, "workerinput", None)
        self.worker: str | None = workerinput["workerid"] if workerinput else None
        self.tree: str | None = None
        if self.worker is None:
            for stale in self.path.parent.glob(f"{self.path.name}.*.part"):
                stale.unlink(missing_ok=True)
            self.tree = working_tree(Path(recorder.root))

    @pytest.hookimpl(wrapper=True)
    def pytest_runtest_protocol(
        self, item: pytest.Item, nextitem: pytest.Item | None
    ) -> Generator[None, object, object]:
        record = _Record()
        self.recorder.push(record)
        try:
            return (yield)
        finally:
            self.recorder.pop(record)
            entry = record.as_json()
            entry["fixtures"] = _wide_fixtures(item)
            entry["extended"] = item.get_closest_marker("extended") is not None
            self.recorder.tests[item.nodeid] = entry

    @pytest.hookimpl(wrapper=True)
    def pytest_fixture_setup(
        self, fixturedef: pytest.FixtureDef[Any], request: pytest.FixtureRequest
    ) -> Generator[None, object, object]:
        if fixturedef.scope == "function":
            return (yield)
        recorder = self.recorder
        record = recorder.scopes.setdefault(_fixture_key(fixturedef), _Record())
        # Finalisers run last in, first out: the push registered after the fixture's
        # own teardown runs before it, the pop registered now runs after it.
        fixturedef.addfinalizer(lambda: recorder.pop(record))
        recorder.push(record)
        try:
            result = yield
        finally:
            recorder.pop(record)
        fixturedef.addfinalizer(lambda: recorder.push(record))
        return result

    @pytest.hookimpl(trylast=True)
    def pytest_sessionfinish(self, session: pytest.Session) -> None:
        recorder = self.recorder
        extended = bool(self.config.getoption("extended", default=True))
        data = recorder.as_json(self.tree, extended)
        if self.worker is not None:
            _write_json(self.path.with_name(f"{self.path.name}.{self.worker}.part"), data)
            return
        for part in sorted(self.path.parent.glob(f"{self.path.name}.*.part")):
            _merge_into(data, json.loads(part.read_text(encoding="utf-8")), replace_files=False)
            part.unlink()
        _write_json(self.path, data)

    def pytest_unconfigure(self, config: pytest.Config) -> None:
        self.recorder.stop()


def _fixture_key(fixturedef: pytest.FixtureDef[Any]) -> str:
    return f"fixture:{fixturedef.baseid}::{fixturedef.argname}"


def _wide_fixtures(item: pytest.Item) -> list[str]:
    """Return the keys of the fixtures scoped wider than a function that ``item`` requests."""
    info = getattr(item, "_fixtureinfo", None)
    names = getattr(item, "fixturenames", ())
    if info is None:
        return []
    keys = set()
    for name in names:
        definitions = info.name2fixturedefs.get(name)
        if definitions and definitions[-1].scope != "function":
            keys.add(_fixture_key(definitions[-1]))
    return sorted(keys)


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    scratch = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    scratch.write_text(json.dumps(data, sort_keys=True), encoding="utf-8")
    os.replace(scratch, path)


def _union(into: dict[str, Any], other: dict[str, Any]) -> None:
    for key in ("functions", "files", "dirs", "preloaded"):
        if key in other or key in into:
            into[key] = sorted(set(into.get(key, ())) | set(other.get(key, ())))
    into["process"] = bool(into.get("process")) or bool(other.get("process"))


def _merge_into(data: dict[str, Any], part: dict[str, Any], *, replace_files: bool) -> None:
    """Merge ``part``'s records into ``data``; with ``replace_files``, a re-run file replaces."""
    if replace_files:
        rerun = {node.split("::", 1)[0] for node in part["tests"]}
        data["tests"] = {
            node: entry
            for node, entry in data["tests"].items()
            if node.split("::", 1)[0] not in rerun
        }
    data["tests"].update(part["tests"])
    for key, record in part.get("scopes", {}).items():
        _union(data.setdefault("scopes", {}).setdefault(key, {}), record)
    _union(data.setdefault("outside", {}), part.get("outside", {}))


# --------------------------------------------------------------------- selection


@dataclass(frozen=True)
class Selection:
    """The tests a change can affect, or the reason no selection can be trusted."""

    fallback: str | None
    tests: tuple[str, ...]


def _fallback(reason: str) -> Selection:
    return Selection(fallback=reason, tests=())


def skeleton(source: str) -> str:
    """Return the module with every function body replaced by ``pass``, as an AST dump.

    Decorators, arguments, defaults, annotations, class bodies and module-level
    code are kept: they run at import, outside any test (Design section 1).
    """
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            node.body = [ast.Pass()]
    return ast.dump(tree, include_attributes=False)


def function_bodies(source: str) -> dict[str, str]:
    """Return each outer function's qualname and the dump of its body, nested defs included."""
    bodies: dict[str, list[str]] = {}

    def visit(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef):
                dump = "\n".join(ast.dump(statement) for statement in child.body)
                bodies.setdefault(prefix + child.name, []).append(dump)
            elif isinstance(child, ast.ClassDef):
                visit(child, f"{prefix}{child.name}.")
            elif isinstance(child, ast.stmt | ast.excepthandler | ast.match_case):
                visit(child, prefix)

    visit(ast.parse(source), "")
    return {name: "\n\n".join(dumps) for name, dumps in bodies.items()}


def _is_prose(repo: Path, path: str) -> bool:
    """Return whether ``.github/scripts/prose-only.sh`` calls ``path`` prose; no script, yes."""
    script = repo / ".github/scripts/prose-only.sh"
    if not script.is_file():
        return True
    try:
        result = subprocess.run(
            ["bash", str(script)], input=f"{path}\n", capture_output=True, text=True, check=False
        )
    except OSError:
        return False
    return result.returncode == 0


def _blob(repo: Path, tree: str, path: str) -> str:
    return _git(repo, "cat-file", "blob", f"{tree}:{path}")


def _importers(repo: Path, tree: str, path: str) -> set[str]:
    """Return the test files of ``tree`` that name the test module ``path``, as an import does."""
    stem = path.rsplit("/", 1)[-1][: -len(".py")]
    result = subprocess.run(
        ["git", "-C", str(repo), "grep", "-l", "-w", "-F", "-e", stem, tree, "--", "tests"],
        capture_output=True,
        text=True,
        env=_git_env(),
        check=False,
    )
    found = {line.split(":", 1)[1] for line in result.stdout.splitlines() if ":" in line}
    return {name for name in found if _is_test_file(name) and name != path}


def _load_map(map_path: Path) -> dict[str, Any] | str:
    try:
        text = map_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return f"no impact map at {map_path}"
    except OSError as error:
        return f"map unreadable: {error}"
    try:
        data = json.loads(text)
    except ValueError as error:
        return f"map unreadable: {error}"
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        return f"map unreadable: its schema is not {SCHEMA}"
    if not isinstance(data.get("tree"), str) or not isinstance(data.get("tests"), dict):
        return "map unreadable: it names no tree or no tests"
    return data


def select(repo: Path, map_path: Path, *, include_extended: bool = False) -> Selection:
    """Return the tests the working tree's changes since the map's tree can affect.

    Parameters
    ----------
    repo
        The repository's working copy.
    map_path
        The map written by the recorder.
    include_extended
        Keep the ``extended`` walks: the push gate's follow-up asks for them, the
        commit hook does not (section 8.2.10 J2, J3).

    Returns
    -------
    Selection
        Node ids, whole files, sorted; or a fallback naming every path that forced it.
    """
    repo = Path(repo)
    map_path = Path(map_path)
    data = _load_map(map_path)
    if isinstance(data, str):
        return _fallback(data)
    tree: str = data["tree"]
    probe = subprocess.run(
        ["git", "-C", str(repo), "cat-file", "-e", f"{tree}^{{tree}}"],
        capture_output=True,
        env=_git_env(),
        check=False,
    )
    if probe.returncode != 0:
        return _fallback(f"map tree {tree} is not in this repository")
    if include_extended and not data.get("extended"):
        return _fallback(f"the map at {map_path} was recorded without the extended tests")
    current = working_tree(repo)
    raw = _git(repo, "diff", "--name-status", "--no-renames", "-z", tree, current)
    fields = raw.split("\0")
    changes = [(fields[i][:1], fields[i + 1]) for i in range(0, len(fields) - 1, 2)]

    source = str(data.get("source", "src/nanopnp")).strip("/") + "/"
    outside = data.get("outside", {})
    outside_functions = set(outside.get("functions", ()))
    outside_files = set(outside.get("files", ())) | set(outside.get("preloaded", ()))
    outside_dirs = set(outside.get("dirs", ()))
    tests: dict[str, dict[str, Any]] = data["tests"]

    reasons: list[str] = []
    functions: set[str] = set()
    files: set[str] = set()
    dirs: set[str] = set()
    whole_files: set[str] = set()
    starters = False
    for status, path in changes:
        parent = path.rsplit("/", 1)[0] if "/" in path else ""
        if status in "AD":
            dirs.add(parent)
        if path.startswith(source):
            starters = True
            if not path.endswith(".py"):
                reasons.append(f"{path}: {_STATUS.get(status, status)}, not a Python file")
            elif status != "M":
                reasons.append(f"{path}: {_STATUS.get(status, status)} module")
            else:
                reasons.extend(_function_changes(repo, tree, current, path, functions))
                files.add(path)
                if path in outside_files:
                    reasons.append(f"{path}: read outside a test")
        elif path.endswith(".md"):
            files.add(path)
            if not _is_prose(repo, path):
                starters = True
            if path in outside_files or (status in "AD" and parent in outside_dirs):
                reasons.append(f"{path}: read outside a test")
        elif _is_test_file(path) and status in "AMD":
            files.add(path)
            whole_files.add(path)
            whole_files.update(_importers(repo, current if status != "D" else tree, path))
            if path in outside_files:
                reasons.append(f"{path}: read outside a test")
        else:
            reasons.append(f"{path}: {_STATUS.get(status, status)}; the map cannot attribute it")
    for name in sorted(functions & outside_functions):
        reasons.append(f"{name}: runs at import or outside a test")
    if starters and outside.get("process"):
        reasons.append("a process is started outside a test")
    if reasons:
        return _fallback("; ".join(reasons))

    scopes = data.get("scopes", {})

    def touched(record: dict[str, Any]) -> bool:
        return bool(
            (starters and record.get("process"))
            or functions.intersection(record.get("functions", ()))
            or files.intersection(record.get("files", ()))
            or dirs.intersection(record.get("dirs", ()))
        )

    hit = {key for key, record in scopes.items() if touched(record)}
    chosen = set(whole_files)
    for node, entry in tests.items():
        test_file = node.split("::", 1)[0]
        if (
            test_file in chosen
            or touched(entry)
            or f"module:{test_file}" in hit
            or hit.intersection(entry.get("fixtures", ()))
        ):
            chosen.add(test_file)
    selected = {
        node
        for node, entry in tests.items()
        if node.split("::", 1)[0] in chosen and (include_extended or not entry.get("extended"))
    }
    recorded_files = {node.split("::", 1)[0] for node in tests}
    # A test file added since the map was recorded has no node ids yet: its path stands for them.
    selected.update(
        path
        for status, path in changes
        if status == "A" and _is_test_file(path)
        if path not in recorded_files
    )
    return Selection(fallback=None, tests=tuple(sorted(selected)))


def _function_changes(
    repo: Path, old_tree: str, new_tree: str, path: str, functions: set[str]
) -> list[str]:
    """Add the changed outer functions of ``path`` to ``functions``; return any fallback reason."""
    try:
        old = _blob(repo, old_tree, path)
        new = _blob(repo, new_tree, path)
        if skeleton(old) != skeleton(new):
            return [f"{path}: module-level, class-body, signature or decorator change"]
        before, after = function_bodies(old), function_bodies(new)
    except SyntaxError as error:
        return [f"{path}: does not parse ({error.msg}, line {error.lineno})"]
    functions.update(
        f"{path}::{name}"
        for name in before.keys() | after.keys()
        if before.get(name) != after.get(name)
    )
    return []


# ------------------------------------------------------------------- durations


_DURATION_LINE = re.compile(r"^\s*(\d+(?:\.\d+)?)s\s+(setup|call|teardown)\s+(\S+?)::")


def durations(log: Path) -> dict[str, Any]:
    """Return ``tests/durations.json``'s document from a ``--durations=0`` log, per file."""
    totals: dict[str, float] = {}
    for line in log.read_text(encoding="utf-8", errors="replace").splitlines():
        match = _DURATION_LINE.match(line)
        if match:
            seconds, _, path = match.groups()
            totals[path] = totals.get(path, 0.0) + float(seconds)
    return {
        "schema": DURATIONS_SCHEMA,
        "files": {path: round(seconds, 1) for path, seconds in sorted(totals.items())},
    }


# ----------------------------------------------------------------- command line


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tests/impact.py", description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)
    chooser = commands.add_parser("select", help="print the node ids a change can affect")
    chooser.add_argument("--map", type=Path, default=None)
    chooser.add_argument("--repo", type=Path, default=Path.cwd())
    chooser.add_argument("--extended", action="store_true", help="keep the extended walks")
    merger = commands.add_parser("merge", help="fold a follow-up's part into the map")
    merger.add_argument("--map", type=Path, required=True)
    merger.add_argument("--part", type=Path, required=True)
    merger.add_argument("--tree", required=True)
    timer = commands.add_parser("durations", help="write tests/durations.json from a log")
    timer.add_argument("log", type=Path)
    timer.add_argument("--out", type=Path, default=Path(__file__).with_name("durations.json"))
    arguments = parser.parse_args(argv)

    if arguments.command == "select":
        map_path = arguments.map or default_map_path(arguments.repo)
        selection = select(arguments.repo, map_path, include_extended=arguments.extended)
        if selection.fallback is not None:
            print(f"FALLBACK: {selection.fallback}")
            return FALLBACK_EXIT
        for node in selection.tests:
            print(node)
        return 0
    if arguments.command == "merge":
        data = _load_map(arguments.map)
        part = _load_map(arguments.part)
        for loaded in (data, part):
            if isinstance(loaded, str):
                print(loaded, file=sys.stderr)
                return 1
        assert isinstance(data, dict) and isinstance(part, dict)
        _merge_into(data, part, replace_files=True)
        data["tree"] = arguments.tree
        _write_json(arguments.map, data)
        return 0
    document = durations(arguments.log)
    arguments.out.write_text(
        json.dumps(document, indent=1, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(_main())

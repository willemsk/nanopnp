from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

_HOOK = Path(__file__).resolve().parents[2] / ".claude/hooks/session-start.sh"
_BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(
    os.name == "nt" or _BASH is None or shutil.which("git") is None,
    reason="Claude's shell hooks require a POSIX environment with bash and git",
)


@pytest.fixture
def hook_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        monkeypatch.delenv(name, raising=False)
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_CODE_REMOTE", "false")
    return tmp_path


def _startup(repo: Path) -> subprocess.CompletedProcess[str]:
    assert _BASH is not None
    return subprocess.run([_BASH, str(_HOOK)], cwd=repo, capture_output=True, text=True, timeout=10)


@pytest.mark.parametrize("has_brief", [False, True])
def test_session_start_context_does_not_grow_with_archived_plans(
    hook_repo: Path, has_brief: bool
) -> None:
    plans = hook_repo / "docs/plans"
    plans.mkdir(parents=True)
    (plans / "archive.md").write_text("**Status: delivered**\n", encoding="utf-8")
    if has_brief:
        (plans / "current.md").write_text("# Current work\n", encoding="utf-8")
    before = _startup(hook_repo)
    for number in range(200):
        (plans / f"wp{number}.md").write_text("**Status: delivered**\n" * 100, encoding="utf-8")
    after = _startup(hook_repo)
    assert before.returncode == after.returncode == 0
    assert before.stdout == after.stdout
    assert "workflow: /wp-plan" in after.stdout
    assert "delivered" not in after.stdout
    assert len(after.stdout.encode("utf-8")) < 1024
    if has_brief:
        assert "docs/plans/current.md" in after.stdout
    else:
        assert "current brief unavailable" in after.stdout


@pytest.mark.parametrize("remote,exit_code", [(False, 0), (True, 0), (True, 1)])
def test_session_start_preserves_remote_frozen_sync(
    hook_repo: Path, monkeypatch: pytest.MonkeyPatch, remote: bool, exit_code: int
) -> None:
    binaries = hook_repo / "bin"
    binaries.mkdir()
    uv = binaries / "uv"
    uv.write_text(
        '#!/bin/sh\nprintf "sync-call: %s\\n" "$*"\n' + f"exit {exit_code}\n",
        encoding="utf-8",
    )
    uv.chmod(0o755)
    monkeypatch.setenv("PATH", f"{binaries}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("CLAUDE_CODE_REMOTE", str(remote).lower())
    result = _startup(hook_repo)
    assert result.returncode == (exit_code if remote else 0)
    assert "sync-call" not in result.stdout
    assert ("sync-call: sync --all-extras --frozen" in result.stderr) == remote
    assert ("workflow:" in result.stdout) == (not remote or exit_code == 0)


@pytest.mark.parametrize("apt_works", [True, False])
def test_session_start_installs_gmsh_libraries_or_names_them(
    hook_repo: Path, monkeypatch: pytest.MonkeyPatch, apt_works: bool
) -> None:
    """A Gmsh that cannot find libGLU gets its libraries, or one line naming them.

    ``gate.sh run`` requires Gmsh as CI does, so a fresh container without the
    libraries would fail the push gate; installing them at start-up, where no
    prompt is needed, keeps Gmsh's tests running instead of failing or skipping.
    """
    venv = hook_repo / ".venv/bin"
    venv.mkdir(parents=True)
    fake_python = venv / "python"
    fake_python.write_text(
        "#!/bin/sh\necho 'OSError: libGLU.so.1: cannot open shared object file' >&2\nexit 1\n",
        encoding="utf-8",
    )
    fake_python.chmod(0o755)
    binaries = hook_repo / "bin"
    binaries.mkdir()
    calls = hook_repo / "apt-calls"
    scripts = {
        "ldconfig": "exit 0\n",
        "sudo": '[ "$1" = -n ] && shift\nexec "$@"\n',
        "apt-get": f'echo "$*" >> "{calls}"\nexit {0 if apt_works else 1}\n',
    }
    for name, body in scripts.items():
        (binaries / name).write_text(f"#!/bin/sh\n{body}", encoding="utf-8")
        (binaries / name).chmod(0o755)
    monkeypatch.setenv("PATH", f"{binaries}{os.pathsep}{os.environ['PATH']}")
    result = _startup(hook_repo)
    assert result.returncode == 0, result.stderr
    assert "libglu1-mesa libxft2 libxinerama1 libxcursor1" in calls.read_text(encoding="utf-8")
    if apt_works:
        assert "- installed Gmsh's system libraries" in result.stdout
    else:
        assert "- warning: gmsh cannot import (libGLU.so.1)" in result.stdout
    assert "workflow:" in result.stdout


_GATE = Path(__file__).resolve().parents[2] / ".claude/hooks/gate.sh"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture
def worktree_pair(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    """Return a main checkout whose tree is stamped as passed, and a worktree with an edit.

    ``uv`` on ``PATH`` always fails, so any tree the gate actually checks is refused:
    an empty stdout from the hook means it gated nothing, or a stamped tree.
    """
    if shutil.which("jq") is None:
        pytest.skip("the gate hook reads its payload with jq")
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        monkeypatch.delenv(name, raising=False)
    main = tmp_path / "main"
    (main / "src/nanopnp").mkdir(parents=True)
    (main / "pyproject.toml").write_text("[project]\nname = 'fake'\n", encoding="utf-8")
    (main / "src/nanopnp/__init__.py").write_text("", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(main)], check=True)
    _git(main, "add", "-A")
    _git(main, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init")
    worktree = tmp_path / "worktree"
    _git(main, "worktree", "add", "-q", str(worktree))
    (worktree / "src/nanopnp/__init__.py").write_text("broken = (\n", encoding="utf-8")
    # The stamp the gate writes after a pass: the tree id of the working copy and
    # the selection that passed, here the commit hook's own.
    (Path(_git(main, "rev-parse", "--absolute-git-dir")) / "nanopnp-gate.pass").write_text(
        f"{_git(main, 'write-tree')} development", encoding="utf-8"
    )
    binaries = tmp_path / "bin"
    binaries.mkdir()
    uv = binaries / "uv"
    uv.write_text("#!/bin/sh\necho 'fake uv refused' >&2\nexit 1\n", encoding="utf-8")
    uv.chmod(0o755)
    monkeypatch.setenv("PATH", f"{binaries}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(main))
    return main, worktree


def _hook(started_in: Path, session_dir: Path, command: str) -> str:
    """Run the gate in hook mode from ``started_in``, as the harness does, and return stdout."""
    assert _BASH is not None
    payload = json.dumps({"cwd": str(session_dir), "tool_input": {"command": command}})
    result = subprocess.run(
        [_BASH, str(_GATE)],
        cwd=started_in,
        input=payload,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


@pytest.mark.parametrize(
    ("session", "command"),
    [
        ("worktree", "git commit -m 'edit'"),
        ("worktree", "git add -A && git commit -m 'edit'"),
        ("parent", "git -C worktree commit -m 'edit'"),
    ],
    ids=["plain", "compound", "relative-C"],
)
def test_gate_hook_gates_the_worktree_a_session_commits_from(
    worktree_pair: tuple[Path, Path], session: str, command: str
) -> None:
    """Started from the stamped main checkout, the hook still gates the session's worktree.

    The harness starts the hook in the project directory, the main checkout, and
    the payload's ``cwd`` says where the command runs; a relative ``-C`` resolves
    against it, as git resolves it. Gating the hook's own directory let a worktree
    commit through on the main checkout's stamp (WP32).
    """
    main, worktree = worktree_pair
    session_dir = worktree if session == "worktree" else worktree.parent
    output = json.loads(_hook(main, session_dir, command))["hookSpecificOutput"]
    assert output["permissionDecision"] == "deny"
    assert "fake uv refused" in output["permissionDecisionReason"]


def test_gate_hook_follows_a_cd_before_the_commit(worktree_pair: tuple[Path, Path]) -> None:
    """``cd <worktree> && git commit`` gates the worktree, wherever the session stood."""
    main, worktree = worktree_pair
    decision = json.loads(_hook(main, main, f"cd {worktree} && git add -A && git commit -m x"))
    assert decision["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_gate_hook_still_lets_a_stamped_tree_through(worktree_pair: tuple[Path, Path]) -> None:
    """The session in the stamped main checkout commits without re-running anything."""
    main, _ = worktree_pair
    assert _hook(main, main, "git commit -m 'edit'") == ""


def test_gate_run_does_not_take_a_development_pass_for_its_own(
    worktree_pair: tuple[Path, Path],
) -> None:
    """``gate.sh run`` adds the ``extended`` tests, so the hook's pass does not stand in for it.

    The skills run it before they push, and CI gates the ``extended`` tests on every
    push (section 7.6 NOTE): a tree that passed only the development selection is
    gated again, here reaching the fake ``uv`` that refuses.
    """
    assert _BASH is not None
    main, _ = worktree_pair
    result = subprocess.run(
        [_BASH, str(_GATE), "run"], cwd=main, capture_output=True, text=True, timeout=60
    )
    assert result.returncode != 0
    assert "already passed" not in result.stdout


def test_gate_run_on_a_clean_tree_runs_the_extended_tests_on_unpushed_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``gate.sh run`` on a committed tree reaches pytest with ``--extended``.

    The skills commit, then run the gate before they push. Judged against HEAD,
    that clean tree is all prose and pytest would be skipped while the stamp
    claimed the extended pass; ``run`` judges what the push would send, here a
    code commit on a branch never pushed (section 7.6 NOTE).
    """
    assert _BASH is not None
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        monkeypatch.delenv(name, raising=False)
    repo = tmp_path / "repo"
    (repo / "src/nanopnp").mkdir(parents=True)
    (repo / ".github/scripts").mkdir(parents=True)
    (repo / "pyproject.toml").write_text("[project]\nname = 'fake'\n", encoding="utf-8")
    (repo / "src/nanopnp/__init__.py").write_text("", encoding="utf-8")
    shutil.copy(_GATE.parents[2] / ".github/scripts/prose-only.sh", repo / ".github/scripts")
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    identity = ("-c", "user.name=t", "-c", "user.email=t@t")
    _git(repo, "add", "-A")
    _git(repo, *identity, "commit", "-qm", "init")
    _git(repo, "checkout", "-qb", "work")
    (repo / "src/nanopnp/code.py").write_text("x = 1\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, *identity, "commit", "-qm", "code")
    calls = tmp_path / "uv-calls"
    binaries = tmp_path / "bin"
    binaries.mkdir()
    uv = binaries / "uv"
    uv.write_text(f'#!/bin/sh\necho "$*" >> "{calls}"\nexit 0\n', encoding="utf-8")
    uv.chmod(0o755)
    monkeypatch.setenv("PATH", f"{binaries}{os.pathsep}{os.environ['PATH']}")

    result = subprocess.run(
        [_BASH, str(_GATE), "run"], cwd=repo, capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 0, result.stderr
    ran = calls.read_text(encoding="utf-8").splitlines()
    assert any("pytest" in call and "--extended" in call for call in ran), ran
    stamp = Path(_git(repo, "rev-parse", "--absolute-git-dir")) / "nanopnp-gate.pass"
    assert stamp.read_text(encoding="utf-8").split()[-1] == "extended"


def test_gate_run_on_an_already_pushed_branch_still_runs_the_extended_tests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``gate.sh run`` judges the whole branch against ``main``, not its upstream.

    ``/wp-ship`` and the steward run it on a branch already pushed, often from a
    fresh container with no stamp. Against the upstream that clean branch has
    nothing to send, reads as prose, and passed on ruff alone while stamping the
    extended selection; CI's pull_request check compares base...head and runs
    pytest (section 7.6 NOTE, PR 74 review).
    """
    assert _BASH is not None
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        monkeypatch.delenv(name, raising=False)
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(origin)], check=True)
    repo = tmp_path / "repo"
    (repo / "src/nanopnp").mkdir(parents=True)
    (repo / ".github/scripts").mkdir(parents=True)
    (repo / "pyproject.toml").write_text("[project]\nname = 'fake'\n", encoding="utf-8")
    (repo / "src/nanopnp/__init__.py").write_text("", encoding="utf-8")
    shutil.copy(_GATE.parents[2] / ".github/scripts/prose-only.sh", repo / ".github/scripts")
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    identity = ("-c", "user.name=t", "-c", "user.email=t@t")
    _git(repo, "add", "-A")
    _git(repo, *identity, "commit", "-qm", "init")
    _git(repo, "remote", "add", "origin", str(origin))
    _git(repo, "push", "-q", "-u", "origin", "main")
    _git(repo, "checkout", "-qb", "work")
    (repo / "src/nanopnp/code.py").write_text("x = 1\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, *identity, "commit", "-qm", "code")
    _git(repo, "push", "-q", "-u", "origin", "work")
    assert _git(repo, "rev-parse", "@{upstream}") == _git(repo, "rev-parse", "HEAD")
    calls = tmp_path / "uv-calls"
    binaries = tmp_path / "bin"
    binaries.mkdir()
    uv = binaries / "uv"
    uv.write_text(f'#!/bin/sh\necho "$*" >> "{calls}"\nexit 0\n', encoding="utf-8")
    uv.chmod(0o755)
    monkeypatch.setenv("PATH", f"{binaries}{os.pathsep}{os.environ['PATH']}")

    result = subprocess.run(
        [_BASH, str(_GATE), "run"], cwd=repo, capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 0, result.stderr
    ran = calls.read_text(encoding="utf-8").splitlines()
    assert any("pytest" in call and "--extended" in call for call in ran), ran


_PROSE_ONLY = Path(__file__).resolve().parents[2] / ".github/scripts/prose-only.sh"


@pytest.mark.parametrize(
    ("path", "prose"),
    [
        ("docs/x/notes.md", True),
        ("docs/x/findings.md", False),
        ("docs/project/modularity-findings.md", False),
        ("docs/project/modularity-layering.yaml", False),
        ("SPECIFICATION.md", False),
        ("docs/project/modularity.md", False),
        ("docs/project/review-items.md", False),
        ("docs/project/contributing.md", True),
    ],
)
def test_prose_only_reads_a_findings_log_as_not_prose(path: str, prose: bool) -> None:
    """A findings log, and the pages VER-63 reads with it, must run the tests (WP35 D19; H12)."""
    assert _BASH is not None
    result = subprocess.run(
        [_BASH, str(_PROSE_ONLY)], input=f"{path}\n", capture_output=True, text=True, timeout=10
    )
    assert result.returncode == (0 if prose else 1)


def _branch_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, changed: str) -> Path:
    """Return a repository on a branch ``work`` whose one commit past ``main`` adds ``changed``."""
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.delenv("NANOPNP_REQUIRE_GMSH", raising=False)
    repo = tmp_path / "repo"
    (repo / "src/nanopnp").mkdir(parents=True)
    (repo / ".github/scripts").mkdir(parents=True)
    (repo / "pyproject.toml").write_text("[project]\nname = 'fake'\n", encoding="utf-8")
    (repo / "src/nanopnp/__init__.py").write_text("", encoding="utf-8")
    shutil.copy(_PROSE_ONLY, repo / ".github/scripts")
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    identity = ("-c", "user.name=t", "-c", "user.email=t@t")
    _git(repo, "add", "-A")
    _git(repo, *identity, "commit", "-qm", "init")
    _git(repo, "checkout", "-qb", "work")
    (repo / changed).parent.mkdir(parents=True, exist_ok=True)
    (repo / changed).write_text("x = 1\n", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, *identity, "commit", "-qm", "code")
    return repo


def _recording_uv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, body: str = "") -> Path:
    """Put a fake ``uv`` on ``PATH`` that logs ``<NANOPNP_REQUIRE_GMSH>|<args>`` per call."""
    calls = tmp_path / "uv-calls"
    binaries = tmp_path / "bin"
    binaries.mkdir()
    uv = binaries / "uv"
    uv.write_text(
        f'#!/bin/sh\necho "${{NANOPNP_REQUIRE_GMSH:-unset}}|$*" >> "{calls}"\n{body}exit 0\n',
        encoding="utf-8",
    )
    uv.chmod(0o755)
    monkeypatch.setenv("PATH", f"{binaries}{os.pathsep}{os.environ['PATH']}")
    return calls


def test_gate_run_requires_gmsh_and_checks_the_branch_coverage_of_changed_lines(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``gate.sh run`` gates as CI's lint job: branch coverage, skips listed, Gmsh required.

    pytest writes a branch-coverage XML report, and diff-cover judges it against
    the merge base with ``main``, the base the prose rule uses, at 100 % of the
    changed lines of ``src/nanopnp`` outside ``gui/`` (VER-72; the workflow rulings).
    """
    assert _BASH is not None
    repo = _branch_repo(tmp_path, monkeypatch, "src/nanopnp/code.py")
    calls = _recording_uv(tmp_path, monkeypatch)
    result = subprocess.run(
        [_BASH, str(_GATE), "run"], cwd=repo, capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 0, result.stderr
    ran = calls.read_text(encoding="utf-8").splitlines()
    tests = [call for call in ran if "pytest" in call and "--extended" in call]
    assert len(tests) == 1, ran
    assert tests[0].startswith("1|")
    arguments = tests[0].split("|", 1)[1].split()
    for flag in ("-rsfE", "--cov=src/nanopnp", "--cov-branch"):
        assert flag in arguments, (flag, tests[0])
    assert any(argument.startswith("--cov-report=xml:") for argument in arguments), tests[0]
    covered = [call for call in ran if "diff-cover" in call]
    assert len(covered) == 1, ran
    base = _git(repo, "merge-base", "HEAD", "main")
    for flag in (
        f"--compare-branch={base}",
        "--branch-coverage",
        "--fail-under=100",
        "src/nanopnp/**/*.py",
        "*/src/nanopnp/gui/*",
    ):
        assert flag in covered[0], (flag, covered[0])


@pytest.mark.parametrize(
    ("system", "machine", "required"),
    [
        ("Linux", "x86_64", "1"),
        ("Darwin", "arm64", "1"),
        ("Linux", "aarch64", "unset"),
        ("MINGW64_NT-10.0", "x86_64", "unset"),
    ],
)
def test_gate_run_requires_apbs_only_where_its_wheel_installs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, system: str, machine: str, required: str
) -> None:
    """``gate.sh run`` requires APBS where ``apbs-binary`` installs, as CI's legs do (VAL-06).

    The wheel exists for Linux x86_64 and macOS only (``pyproject.toml``, the
    ``apbs`` group); elsewhere uv installs no binary, and requiring one would fail
    VAL-06 on every run of the gate.
    """
    assert _BASH is not None
    monkeypatch.delenv("NANOPNP_REQUIRE_APBS", raising=False)
    repo = _branch_repo(tmp_path, monkeypatch, "src/nanopnp/code.py")
    seen = tmp_path / "apbs-seen"
    _recording_uv(tmp_path, monkeypatch, f'echo "${{NANOPNP_REQUIRE_APBS:-unset}}" >> "{seen}"\n')
    uname = tmp_path / "bin" / "uname"
    uname.write_text(
        f'#!/bin/sh\ncase "$1" in -m) echo {machine};; *) echo {system};; esac\n',
        encoding="utf-8",
    )
    uname.chmod(0o755)
    result = subprocess.run(
        [_BASH, str(_GATE), "run"], cwd=repo, capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 0, result.stderr
    assert set(seen.read_text(encoding="utf-8").split()) == {required}


@pytest.mark.parametrize(
    ("changed", "content", "required"),
    [
        ("src/nanopnp/mesh/gmsh_backend.py", "y = 2\n", "1"),
        ("tests/tier1/test_mesh_gmsh.py", "y = 2\n", "1"),
        ("tests/tier2/test_mesh_backends.py", "y = 2\n", "1"),
        # A test taking the fixture is Gmsh's wherever it lives, and so is the fixture.
        ("tests/tier1/test_mesh_quality.py", "def test_x(gmsh_module):\n    pass\n", "1"),
        ("tests/conftest.py", "def import_gmsh():\n    pass\n", "1"),
        ("tests/tier1/test_mesh_quality.py", "y = 2\n", "unset"),
        ("src/nanopnp/core/units.py", "y = 2\n", "unset"),
    ],
)
def test_gate_hook_requires_gmsh_only_for_a_change_to_gmsh(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, changed: str, content: str, required: str
) -> None:
    """The commit hook fails Gmsh's tests on a missing library only when the change is Gmsh's."""
    if shutil.which("jq") is None:
        pytest.skip("the gate hook reads its payload with jq")
    repo = _branch_repo(tmp_path, monkeypatch, "src/nanopnp/other.py")
    (repo / changed).parent.mkdir(parents=True, exist_ok=True)
    (repo / changed).write_text(content, encoding="utf-8")
    calls = _recording_uv(tmp_path, monkeypatch)
    _hook(repo, repo, "git commit -am x")
    ran = calls.read_text(encoding="utf-8").splitlines()
    tests = [call for call in ran if "pytest" in call and "-rsfE" in call.split("|", 1)[1].split()]
    assert tests, ran
    assert {call.split("|", 1)[0] for call in tests} == {required}
    assert not any("diff-cover" in call for call in ran)


def test_gate_names_the_system_libraries_when_gmsh_cannot_import(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A Gmsh that cannot import fails ``run`` with the ``apt-get`` line that fixes it."""
    assert _BASH is not None
    repo = _branch_repo(tmp_path, monkeypatch, "src/nanopnp/code.py")
    failing = (
        'case "$*" in *--extended*) echo "Failed: NANOPNP_REQUIRE_GMSH=1 and gmsh does not '
        'import: OSError: libGLU.so.1"; exit 1;; esac\n'
    )
    _recording_uv(tmp_path, monkeypatch, failing)
    result = subprocess.run(
        [_BASH, str(_GATE), "run"], cwd=repo, capture_output=True, text=True, timeout=60
    )
    assert result.returncode != 0
    assert "libGLU.so.1" in result.stderr
    assert "apt-get install -y --no-install-recommends libglu1-mesa" in result.stderr


def test_gate_hook_requires_gmsh_for_a_tracked_change_beside_an_untracked_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A tracked Gmsh change still counts when an untracked file follows it in the path list.

    ``grep -q`` exits at the first match; piped under ``pipefail`` the writer's
    SIGPIPE once made the match read as a miss.
    """
    if shutil.which("jq") is None:
        pytest.skip("the gate hook reads its payload with jq")
    repo = _branch_repo(tmp_path, monkeypatch, "src/nanopnp/mesh/gmsh_backend.py")
    (repo / "src/nanopnp/mesh/gmsh_backend.py").write_text("x = 2\n", encoding="utf-8")
    (repo / "src/nanopnp/untracked.py").write_text("z = 3\n", encoding="utf-8")
    calls = _recording_uv(tmp_path, monkeypatch)
    _hook(repo, repo, "git commit -am x")
    ran = calls.read_text(encoding="utf-8").splitlines()
    tests = [call for call in ran if "pytest" in call and "-rsfE" in call.split("|", 1)[1].split()]
    assert tests, ran
    assert {call.split("|", 1)[0] for call in tests} == {"1"}


def test_gate_run_without_a_merge_base_fails_before_the_selection(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``gate.sh run`` names the fetch that supplies the merge base, and runs nothing first."""
    assert _BASH is not None
    repo = _branch_repo(tmp_path, monkeypatch, "src/nanopnp/code.py")
    _git(repo, "branch", "-m", "main", "trunk")
    calls = _recording_uv(tmp_path, monkeypatch)
    result = subprocess.run(
        [_BASH, str(_GATE), "run"], cwd=repo, capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 1
    assert "git fetch origin main" in result.stderr
    assert not calls.exists() or "pytest" not in calls.read_text(encoding="utf-8")

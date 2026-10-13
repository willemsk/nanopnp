from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
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
    tree, selection, commit = stamp.read_text(encoding="utf-8").splitlines()[-1].split()
    # The pass names its tree and a commit object of it whose parent is the merge
    # base it was judged against, which a follow-up compares with (WP43 D7).
    assert (tree, selection) == (_git(repo, "rev-parse", "HEAD^{tree}"), "extended")
    assert _git(repo, "rev-parse", f"{commit}^{{tree}}") == tree
    assert _git(repo, "rev-parse", f"{commit}^1") == _git(repo, "merge-base", "HEAD", "main")


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


def _impact_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, selector: str, pytest_status: int = 0
) -> Path:
    """Return a branch repository with an impact map, and a fake ``uv`` running ``selector``.

    ``selector`` is the shell body run for ``uv run python tests/impact.py select``, and
    ``pytest_status`` the exit status of the selection's own pytest call; every call is
    logged as in ``_recording_uv``.
    """
    repo = _branch_repo(tmp_path, monkeypatch, "src/nanopnp/other.py")
    (repo / "tests").mkdir(exist_ok=True)
    (repo / "tests/impact.py").write_text("", encoding="utf-8")
    common = Path(_git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    (common / "nanopnp-impact").mkdir()
    (common / "nanopnp-impact/map.json").write_text("{}", encoding="utf-8")
    (repo / "src/nanopnp/other.py").write_text("x = 2\n", encoding="utf-8")
    body = (
        f'case "$*" in *"impact.py select"*) {selector};; '
        f'*"not extended"*) exit {pytest_status};; esac\n'
    )
    _recording_uv(tmp_path, monkeypatch, body)
    return repo


def _log(repo: Path) -> list[str]:
    path = Path(_git(repo, "rev-parse", "--absolute-git-dir")) / "nanopnp-gate.log"
    return path.read_text(encoding="utf-8").splitlines()


def test_gate_hook_runs_the_impact_selection_by_whole_file_and_stamps_impact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The hook runs the files the selector names, never their walks, and stamps ``impact`` (D5)."""
    if shutil.which("jq") is None:
        pytest.skip("the gate hook reads its payload with jq")
    selector = (
        "printf '%s\\n' tests/tier1/test_a.py::test_x 'tests/tier1/test_a.py::test_y[1]' "
        "tests/tier2/test_b.py::test_z; exit 0"
    )
    repo = _impact_repo(tmp_path, monkeypatch, selector)
    output = _hook(repo, repo, "git commit -am x")
    calls = (tmp_path / "uv-calls").read_text(encoding="utf-8").splitlines()
    runs = [call for call in calls if "pytest" in call and "-rsfE" in call and "gui" not in call]
    assert len(runs) == 1, calls
    arguments = runs[0].split("|", 1)[1]
    assert arguments.endswith("-- tests/tier1/test_a.py tests/tier2/test_b.py"), arguments
    assert "not extended" in arguments
    assert "--extended" not in arguments
    assert "-n 0" in arguments  # three tests: no workers to start
    assert "impact selection, 3 tests" in json.loads(output)["systemMessage"]
    stamp = Path(_git(repo, "rev-parse", "--absolute-git-dir")) / "nanopnp-gate.pass"
    assert stamp.read_text(encoding="utf-8").split()[-1] == "impact"
    mode, selection, count = _log(repo)[-1].split()[1:4]
    assert (mode, selection, count) == ("hook", "impact", "3")
    assert _log(repo)[-1].endswith(" passed")


@pytest.mark.parametrize(("status", "passes"), [(5, True), (1, False)])
def test_gate_hook_takes_exit_5_of_the_impact_selection_for_no_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, status: int, passes: bool
) -> None:
    """A new Tier 3 file is named by path and the marker expression deselects all of it (D5).

    pytest exits 5 then ("no tests ran"); the selection held nothing to run, which is
    no failure, whereas any other nonzero status still denies the commit.
    """
    if shutil.which("jq") is None:
        pytest.skip("the gate hook reads its payload with jq")
    selector = "printf '%s\\n' tests/tier3/test_new.py; exit 0"
    repo = _impact_repo(tmp_path, monkeypatch, selector, pytest_status=status)
    output = json.loads(_hook(repo, repo, "git commit -am x"))
    if passes:
        assert "impact selection, 1 tests" in output["systemMessage"]
    else:
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_gate_hook_reads_node_ids_from_stdout_alone_and_keeps_the_gui_file_serial(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A warning ``uv`` writes to stderr is never a path; the GUI file stays out of xdist (D5)."""
    if shutil.which("jq") is None:
        pytest.skip("the gate hook reads its payload with jq")
    selector = (
        "echo 'warning: UV_NATIVE_TLS is deprecated' >&2; "
        "printf '%s\\n' tests/tier1/test_a.py::test_x "
        "tests/tier1/test_gui_widgets.py::test_w; exit 0"
    )
    repo = _impact_repo(tmp_path, monkeypatch, selector)
    output = _hook(repo, repo, "git commit -am x")
    calls = (tmp_path / "uv-calls").read_text(encoding="utf-8").splitlines()
    runs = [call for call in calls if "pytest" in call and "not extended" in call]
    assert len(runs) == 1, calls
    assert runs[0].split("|", 1)[1].endswith("-- tests/tier1/test_a.py"), runs[0]
    assert "warning" not in json.loads(output)["systemMessage"]


def test_gate_hook_falls_back_to_the_development_selection_naming_the_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A selector fallback runs the whole development selection, and the message says why."""
    if shutil.which("jq") is None:
        pytest.skip("the gate hook reads its payload with jq")
    repo = _impact_repo(
        tmp_path,
        monkeypatch,
        "echo 'FALLBACK: src/nanopnp/core/units.py: module-level change'; exit 3",
    )
    output = _hook(repo, repo, "git commit -am x")
    calls = (tmp_path / "uv-calls").read_text(encoding="utf-8").splitlines()
    runs = [
        call
        for call in calls
        if "pytest" in call and "--ignore=tests/tier1/test_gui_widgets.py" in call
    ]
    assert len(runs) == 1, calls
    assert "src/nanopnp/core/units.py: module-level change" in json.loads(output)["systemMessage"]
    assert _log(repo)[-1].split()[2] == "development"


@pytest.mark.parametrize(
    ("recorded", "named"),
    [
        ("commit_hook_s: 1\nmargin: 0.0\n", "budget is 1 s, 1 s with its margin"),
        ("commit_hook_s: 1000\nmargin: 0.5\n", None),
    ],
    ids=["over", "within"],
)
def test_gate_hook_judges_its_time_by_the_budgets_the_repository_records(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, recorded: str, named: str | None
) -> None:
    """The hook names an overrun of ``commit_hook_s`` past ``margin``, never failing (VER-73)."""
    if shutil.which("jq") is None:
        pytest.skip("the gate hook reads its payload with jq")
    repo = _impact_repo(tmp_path, monkeypatch, "sleep 2; exit 0")
    (repo / ".github/budgets.yaml").write_text(recorded, encoding="utf-8")
    message = json.loads(_hook(repo, repo, "git commit -am x"))["systemMessage"]
    if named is None:
        assert "Over budget" not in message
    else:
        assert f"Over budget: the commit hook's {named}" in message


def test_gate_hook_without_a_map_falls_back_and_never_calls_the_selector(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if shutil.which("jq") is None:
        pytest.skip("the gate hook reads its payload with jq")
    repo = _impact_repo(tmp_path, monkeypatch, "exit 0")
    common = Path(_git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    (common / "nanopnp-impact/map.json").unlink()
    output = _hook(repo, repo, "git commit -am x")
    calls = (tmp_path / "uv-calls").read_text(encoding="utf-8")
    assert "impact.py select" not in calls
    assert "no impact map" in json.loads(output)["systemMessage"]


def test_gate_hook_pass_keeps_the_extended_stamp_line_last(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A commit-hook pass adds its line and leaves the push gate's ``extended`` line in place."""
    if shutil.which("jq") is None:
        pytest.skip("the gate hook reads its payload with jq")
    repo = _impact_repo(tmp_path, monkeypatch, "exit 0")
    stamp = Path(_git(repo, "rev-parse", "--absolute-git-dir")) / "nanopnp-gate.pass"
    stamp.write_text(f"{'a' * 40} extended\n", encoding="utf-8")
    _hook(repo, repo, "git commit -am x")
    lines = stamp.read_text(encoding="utf-8").splitlines()
    assert lines[-1] == f"{'a' * 40} extended"
    assert len(lines) == 2 and lines[0].endswith(" impact")


def test_gate_map_records_under_the_recorder_and_skips_a_usable_map(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``gate.sh map`` runs the development selection with ``-p impact`` and installs the map.

    A map whose tree the repository holds is kept: the selector reads every change
    since that tree, so it never needs re-recording to stay sound.
    """
    assert _BASH is not None
    if shutil.which("jq") is None:
        pytest.skip("the gate reads the map with jq")
    repo = _branch_repo(tmp_path, monkeypatch, "src/nanopnp/code.py")
    tree = _git(repo, "rev-parse", "HEAD^{tree}")
    writer = (
        # One argument at a time: ${*##...} strips each argument under bash, which
        # is macOS's /bin/sh, and the joined string only under dash.
        "for a; do case $a in --impact-record=*) path=${a#--impact-record=}; "
        f'printf \'{{"tree": "{tree}", "tests": {{"t": {{}}}}}}\' > "$path";; esac; done\n'
    )
    calls = _recording_uv(tmp_path, monkeypatch, writer)
    result = subprocess.run(
        [_BASH, str(_GATE), "map"], cwd=repo, capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 0, result.stderr
    runs = [call for call in calls.read_text(encoding="utf-8").splitlines() if "pytest" in call]
    assert len(runs) == 1 and "-p impact" in runs[0] and "--extended" not in runs[0], runs
    common = Path(_git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    assert (
        json.loads((common / "nanopnp-impact/map.json").read_text(encoding="utf-8"))["tree"] == tree
    )
    assert _log(repo)[-1].split()[1:4] == ["map", "development", "1"]
    again = subprocess.run(
        [_BASH, str(_GATE), "map"], cwd=repo, capture_output=True, text=True, timeout=60
    )
    assert again.returncode == 0
    assert "nothing to record" in again.stdout
    assert len([c for c in calls.read_text(encoding="utf-8").splitlines() if "pytest" in c]) == 1


def test_gate_map_installs_no_map_from_a_run_with_a_failing_test(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A failing test records only what it ran before it failed, so its map would under-select."""
    assert _BASH is not None
    if shutil.which("jq") is None:
        pytest.skip("the gate reads the map with jq")
    repo = _branch_repo(tmp_path, monkeypatch, "src/nanopnp/code.py")
    tree = _git(repo, "rev-parse", "HEAD^{tree}")
    body = (
        'case "$*" in *pytest*) for a; do case $a in --impact-record=*) '
        f'printf \'{{"tree": "{tree}", "tests": {{"t": {{}}}}}}\' > "${{a#--impact-record=}}";; '
        "esac; done; exit 1;; esac\n"
    )
    _recording_uv(tmp_path, monkeypatch, body)
    result = subprocess.run(
        [_BASH, str(_GATE), "map"], cwd=repo, capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 1
    assert "no map recorded" in result.stderr
    common = Path(_git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    assert not (common / "nanopnp-impact/map.json").exists()
    assert _log(repo)[-1].endswith(" failed")


def _passed_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, selector: str
) -> tuple[Path, str, Path]:
    """Return a branch repository after a full ``gate.sh run`` pass, its stamp's commit and calls.

    The fake ``uv`` writes an ``extended`` map of the passed tree wherever the
    recorder is asked to record, runs ``selector`` for ``impact.py select``, and
    logs every call as ``_recording_uv`` does.
    """
    if shutil.which("jq") is None:
        pytest.skip("the gate reads the map with jq")
    repo = _branch_repo(tmp_path, monkeypatch, "src/nanopnp/code.py")
    (repo / "tests").mkdir(exist_ok=True)
    (repo / "tests/impact.py").write_text("", encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "impact")
    monkeypatch.setenv("FAKE_MAP_TREE", _git(repo, "rev-parse", "HEAD^{tree}"))
    body = (
        'case "$*" in\n'
        f'  *"impact.py select"*) {selector};;\n'
        '  *"impact.py merge"*) ;;\n'
        "  *--impact-record=*) for a; do case $a in --impact-record=*) path=${a#--impact-record=}; "
        'printf \'{"tree": "%s", "extended": true, "tests": {"t": {}}}\' "$FAKE_MAP_TREE" '
        '> "$path";; esac; done;;\n'
        "esac\n"
    )
    calls = _recording_uv(tmp_path, monkeypatch, body)
    first = _run(repo)
    assert first.returncode == 0, first.stderr
    stamp = Path(_git(repo, "rev-parse", "--absolute-git-dir")) / "nanopnp-gate.pass"
    commit = stamp.read_text(encoding="utf-8").splitlines()[-1].split()[2]
    calls.write_text("", encoding="utf-8")
    return repo, commit, calls


def _run(repo: Path) -> subprocess.CompletedProcess[str]:
    assert _BASH is not None
    return subprocess.run(
        [_BASH, str(_GATE), "run"], cwd=repo, capture_output=True, text=True, timeout=60
    )


def test_gate_run_full_pass_installs_the_extended_map_of_its_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A full pass records under ``-p impact`` and moves the map with the stamp (Design §7)."""
    repo, _, _ = _passed_repo(tmp_path, monkeypatch, "exit 0")
    common = Path(_git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    recorded = json.loads((common / "nanopnp-impact/map.json").read_text(encoding="utf-8"))
    assert recorded["tree"] == _git(repo, "rev-parse", "HEAD^{tree}")
    assert not (common / "nanopnp-impact/map.json.new").exists()
    assert not (common / "nanopnp-impact/gate.lock").exists()
    assert _log(repo)[-1].split()[1:4] == ["run", "extended", "1"]


def test_gate_run_follow_up_runs_only_its_selection_against_the_passed_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """After a pass on P, a run on T runs only the selection, with its walks, under coverage.

    diff-cover compares with P's commit, two-dot, so it judges the lines changed
    since P alone; the map takes the re-run files' records and the stamp moves to
    T (WP43 D7, J3; Design section 2).
    """
    selector = "printf '%s\\n' tests/tier1/test_a.py::test_x tests/tier2/test_b.py::test_z; exit 0"
    repo, passed, calls = _passed_repo(tmp_path, monkeypatch, selector)
    (repo / "src/nanopnp/code.py").write_text("x = 2\n", encoding="utf-8")
    result = _run(repo)
    assert result.returncode == 0, result.stderr
    assert "follow-up" in result.stdout and "2 tests in 2 files" in result.stdout
    ran = [call.split("|", 1)[1] for call in calls.read_text(encoding="utf-8").splitlines()]
    assert any("impact.py select" in call and "--extended" in call for call in ran), ran
    tests = [call for call in ran if call.startswith("run pytest") and "gui" not in call]
    assert len(tests) == 1, ran
    for flag in ("--extended", "--cov=src/nanopnp", "--cov-branch", "-p impact", ".follow"):
        assert flag in tests[0], (flag, tests[0])
    assert tests[0].endswith("-- tests/tier1/test_a.py tests/tier2/test_b.py"), tests[0]
    assert "--ignore" not in tests[0]
    covered = [call for call in ran if "diff-cover" in call]
    assert len(covered) == 1, ran
    assert f"--compare-branch={passed}" in covered[0]
    assert "--diff-range-notation=.." in covered[0]
    merged = [call for call in ran if "impact.py merge" in call]
    assert len(merged) == 1, ran
    stamp = Path(_git(repo, "rev-parse", "--absolute-git-dir")) / "nanopnp-gate.pass"
    tree, selection, commit = stamp.read_text(encoding="utf-8").splitlines()[-1].split()
    assert selection == "extended" and commit != passed
    assert f"--tree {tree}" in merged[0]
    assert _git(repo, "rev-parse", f"{commit}^{{tree}}") == tree
    assert _log(repo)[-1].split()[1:4] == ["follow-up", "extended", "2"]


def test_gate_run_falls_back_to_the_whole_gate_naming_the_selector_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A selector fallback runs the whole gate against the merge base, saying why (D7)."""
    repo, _, calls = _passed_repo(
        tmp_path, monkeypatch, "echo 'FALLBACK: src/nanopnp/code.py: module-level change'; exit 3"
    )
    (repo / "src/nanopnp/code.py").write_text("x = 2\n", encoding="utf-8")
    result = _run(repo)
    assert result.returncode == 0, result.stderr
    assert "module-level change" in result.stdout
    ran = [call.split("|", 1)[1] for call in calls.read_text(encoding="utf-8").splitlines()]
    tests = [call for call in ran if call.startswith("run pytest") and "--extended" in call]
    assert len(tests) == 1 and "--ignore=tests/tier1/test_gui_widgets.py" in tests[0], ran
    assert ".new" in tests[0]
    covered = [call for call in ran if "diff-cover" in call]
    base = _git(repo, "merge-base", "HEAD", "main")
    assert len(covered) == 1 and f"--compare-branch={base}" in covered[0], ran
    assert "--diff-range-notation" not in covered[0]
    assert _log(repo)[-1].split()[1] == "run"


def test_gate_run_does_not_follow_up_from_a_map_of_another_tree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A map not of the passed tree cannot vouch for the unselected tests: the whole gate runs."""
    repo, _, calls = _passed_repo(tmp_path, monkeypatch, "exit 0")
    common = Path(_git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    (common / "nanopnp-impact/map.json").write_text(
        json.dumps({"tree": "b" * 40, "extended": True, "tests": {}}), encoding="utf-8"
    )
    (repo / "src/nanopnp/code.py").write_text("x = 2\n", encoding="utf-8")
    result = _run(repo)
    assert result.returncode == 0, result.stderr
    assert "not of the passed tree" in result.stdout
    assert "impact.py select" not in calls.read_text(encoding="utf-8")


def test_gate_run_stamps_nothing_when_the_tree_changes_while_it_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A background run vouches only for the tree it started on; an edit during it is refused."""
    repo = _branch_repo(tmp_path, monkeypatch, "src/nanopnp/code.py")
    edit = f'case "$*" in *--extended*) echo "x = 3" > "{repo}/src/nanopnp/code.py";; esac\n'
    _recording_uv(tmp_path, monkeypatch, edit)
    result = _run(repo)
    assert result.returncode == 1
    assert "changed while it ran" in result.stderr
    stamp = Path(_git(repo, "rev-parse", "--absolute-git-dir")) / "nanopnp-gate.pass"
    assert not stamp.exists()
    assert _log(repo)[-1].endswith(" changed")


def test_gate_run_waits_for_a_run_in_progress_and_takes_over_a_stale_lock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One run at a time: a live holder's PID makes a run wait; a dead one's is taken over."""
    repo = _branch_repo(tmp_path, monkeypatch, "src/nanopnp/code.py")
    _recording_uv(tmp_path, monkeypatch)
    common = Path(_git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    lock = common / "nanopnp-impact/gate.lock"
    lock.mkdir(parents=True)
    holder = subprocess.Popen(["sleep", "60"])
    (lock / "pid").write_text(f"{holder.pid}\n", encoding="utf-8")
    assert _BASH is not None
    waiting = subprocess.Popen(
        [_BASH, str(_GATE), "run"],
        cwd=repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        time.sleep(2)
        assert waiting.poll() is None, waiting.communicate()
    finally:
        holder.kill()
        holder.wait()
    stdout, stderr = waiting.communicate(timeout=60)
    assert waiting.returncode == 0, stderr
    assert f"waiting for the gate run in progress (PID {holder.pid})" in stdout
    assert not lock.exists()
    lock.mkdir()
    (lock / "pid").write_text(f"{holder.pid}\n", encoding="utf-8")  # reaped above: stale
    (repo / "src/nanopnp/code.py").write_text("x = 2\n", encoding="utf-8")
    again = _run(repo)
    assert again.returncode == 0, again.stderr
    assert "waiting" not in again.stdout


def test_gate_run_reports_a_pass_in_one_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Started in the background, ``run`` prints its failures, or one line on a pass (D7)."""
    repo = _branch_repo(tmp_path, monkeypatch, "src/nanopnp/code.py")
    _recording_uv(tmp_path, monkeypatch)
    result = _run(repo)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().count("\n") == 0
    assert result.stdout.startswith("gate: passed")


def test_gate_hook_refuses_a_push_in_the_command_that_commits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``git commit && git push`` would push a tree no stamp read before the commit can name."""
    if shutil.which("jq") is None:
        pytest.skip("the gate hook reads its payload with jq")
    repo = _branch_repo(tmp_path, monkeypatch, "src/nanopnp/code.py")
    calls = _recording_uv(tmp_path, monkeypatch)
    stamp = Path(_git(repo, "rev-parse", "--absolute-git-dir")) / "nanopnp-gate.pass"
    stamp.write_text(f"{_git(repo, 'rev-parse', 'HEAD^{tree}')} extended\n", encoding="utf-8")
    decision = json.loads(_hook(repo, repo, "git commit -am x && git push"))["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"
    assert "separate command" in decision["permissionDecisionReason"]
    assert not calls.exists()

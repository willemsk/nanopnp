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

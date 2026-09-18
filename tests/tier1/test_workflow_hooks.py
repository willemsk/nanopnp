from __future__ import annotations

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

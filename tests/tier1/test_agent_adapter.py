"""The Antigravity hook adapter (.agents/hooks/adapter.sh) around the Claude hooks."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[2]
_ADAPTER = _ROOT / ".agents/hooks/adapter.sh"
_BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(
    os.name == "nt" or _BASH is None or shutil.which("git") is None or shutil.which("jq") is None,
    reason="the adapter needs a POSIX environment with bash, git and jq",
)


@pytest.fixture
def agent_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        monkeypatch.delenv(name, raising=False)
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / ".agents/hooks").mkdir(parents=True)
    shutil.copy(_ADAPTER, tmp_path / ".agents/hooks/adapter.sh")
    (tmp_path / ".claude/hooks").mkdir(parents=True)
    return tmp_path


def _stub(repo: Path, name: str, body: str) -> None:
    path = repo / ".claude/hooks" / name
    path.write_text(f"#!/usr/bin/env bash\n{body}\n", encoding="utf-8")
    path.chmod(0o755)


def _run(repo: Path, event: str, payload: str) -> subprocess.CompletedProcess[str]:
    assert _BASH is not None
    return subprocess.run(
        [_BASH, ".agents/hooks/adapter.sh", event],
        cwd=repo,
        input=payload,
        capture_output=True,
        text=True,
        timeout=20,
    )


def _commit(command: str) -> str:
    return json.dumps({"toolCall": {"args": {"CommandLine": command}}})


def test_agent_gate_silent_pass_is_allowed(agent_repo: Path) -> None:
    _stub(agent_repo, "gate.sh", "cat >/dev/null")
    out = _run(agent_repo, "pre-tool", _commit("git commit -m x"))
    assert json.loads(out.stdout) == {"decision": "allow"}


def test_agent_gate_denial_reason_is_passed_on(agent_repo: Path) -> None:
    deny = json.dumps({"hookSpecificOutput": {"permissionDecisionReason": "mypy failed"}})
    _stub(agent_repo, "gate.sh", f"cat >/dev/null; printf '%s' '{deny}'")
    out = json.loads(_run(agent_repo, "pre-tool", _commit("git commit -m x")).stdout)
    assert out == {"decision": "deny", "reason": "mypy failed"}


@pytest.mark.parametrize("body", ["cat >/dev/null; exit 3", "cat >/dev/null; echo oops"])
def test_agent_gate_crash_or_noise_is_a_refusal(agent_repo: Path, body: str) -> None:
    _stub(agent_repo, "gate.sh", body)
    out = json.loads(_run(agent_repo, "pre-tool", _commit("git commit -m x")).stdout)
    assert out["decision"] == "deny"
    assert "did not pass" in out["reason"]


def test_agent_unreadable_payload_is_a_refusal(agent_repo: Path) -> None:
    _stub(agent_repo, "gate.sh", "cat >/dev/null")
    out = json.loads(_run(agent_repo, "pre-tool", "not json").stdout)
    assert out["decision"] == "deny"


def test_agent_payload_without_command_is_allowed(agent_repo: Path) -> None:
    _stub(agent_repo, "gate.sh", "exit 9")
    out = json.loads(_run(agent_repo, "pre-tool", json.dumps({"toolCall": {"args": {}}})).stdout)
    assert out == {"decision": "allow"}


def test_agent_gate_receives_the_working_directory(agent_repo: Path, tmp_path: Path) -> None:
    seen = agent_repo / "seen.json"
    _stub(agent_repo, "gate.sh", f"cat > '{seen}'")
    target = tmp_path / "elsewhere"
    target.mkdir()
    payload = json.dumps({"toolCall": {"args": {"CommandLine": "git commit", "Cwd": str(target)}}})
    _run(agent_repo, "pre-tool", payload)
    received = json.loads(seen.read_text(encoding="utf-8"))
    assert received["cwd"] == str(target)
    assert received["tool_input"]["command"] == "git commit"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (r"\\wsl.localhost\Ubuntu\home\u\a.py", "/home/u/a.py"),
        (r"\\wsl$\Arch\home\u\a.py", "/home/u/a.py"),
        ("//wsl.localhost/Debian/home/u/a.py", "/home/u/a.py"),
        (r"C:\Users\u\a.py", "/mnt/c/Users/u/a.py"),
        (r"c:\Users\u\a.py", "/mnt/c/Users/u/a.py"),
        (r"D:\Data\file.txt", "/mnt/d/Data/file.txt"),
        ("/home/u/a.py", "/home/u/a.py"),
    ],
)
def test_agent_post_tool_path_normalisation(agent_repo: Path, raw: str, expected: str) -> None:
    seen = agent_repo / "seen.json"
    _stub(agent_repo, "format.sh", f"cat > '{seen}'")
    _run(agent_repo, "post-tool", json.dumps({"toolCall": {"args": {"TargetFile": raw}}}))
    assert json.loads(seen.read_text(encoding="utf-8"))["tool_input"]["file_path"] == expected


def test_agent_session_start_does_not_read_stdin(agent_repo: Path) -> None:
    _stub(agent_repo, "session-start.sh", "echo started")
    assert _BASH is not None
    out = subprocess.run(
        [_BASH, ".agents/hooks/adapter.sh", "session-start"],
        cwd=agent_repo,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=20,
    )
    assert out.stdout.strip() == "started"

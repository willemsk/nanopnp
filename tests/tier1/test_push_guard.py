"""The push guard: no branch push without a passing push gate on its tree (§8.2.11 L3).

``gate.sh`` in hook mode also reads a ``git push``. It runs nothing: it reads the
stamp ``gate.sh run`` writes after a pass and refuses the push unless the stamp
names the tree of ``HEAD`` with the ``extended`` selection. A tree that only the
commit hook passed is refused, so the full gate runs once per push and never
silently not at all. A push of tags alone names commits CI already gated on
``main``, and ``--no-verify`` is git's own escape, so both pass.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

_GATE = Path(__file__).resolve().parents[2] / ".claude/hooks/gate.sh"
_BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(
    os.name == "nt" or _BASH is None or shutil.which("git") is None or shutil.which("jq") is None,
    reason="Claude's shell hooks require a POSIX environment with bash, git and jq",
)


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Return a committed nanopnp-shaped repository; a ``uv`` on ``PATH`` fails if run."""
    for name in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"):
        monkeypatch.delenv(name, raising=False)
    root = tmp_path / "repo"
    (root / "src/nanopnp").mkdir(parents=True)
    (root / "pyproject.toml").write_text("[project]\nname = 'fake'\n", encoding="utf-8")
    (root / "src/nanopnp/__init__.py").write_text("", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "init")
    binaries = tmp_path / "bin"
    binaries.mkdir()
    uv = binaries / "uv"
    uv.write_text("#!/bin/sh\necho 'fake uv ran' >&2\nexit 1\n", encoding="utf-8")
    uv.chmod(0o755)
    monkeypatch.setenv("PATH", f"{binaries}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(root))
    return root


def _stamp(repo: Path, tree: str, selection: str) -> None:
    git_dir = Path(_git(repo, "rev-parse", "--absolute-git-dir"))
    (git_dir / "nanopnp-gate.pass").write_text(f"{tree} {selection}\n", encoding="utf-8")


def _hook(repo: Path, command: str) -> str:
    assert _BASH is not None
    payload = json.dumps({"cwd": str(repo), "tool_input": {"command": command}})
    result = subprocess.run(
        [_BASH, str(_GATE)], cwd=repo, input=payload, capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 0, result.stderr
    assert "fake uv ran" not in result.stdout + result.stderr
    return result.stdout


def _denied(output: str) -> str:
    decision = json.loads(output)["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"
    reason = decision["permissionDecisionReason"]
    assert isinstance(reason, str)
    return reason


@pytest.mark.parametrize(
    "command",
    ["git push", "git push -u origin feature", "git status && git push origin feature"],
    ids=["bare", "upstream", "compound"],
)
def test_a_push_with_no_stamp_is_refused_naming_the_push_gate(repo: Path, command: str) -> None:
    assert ".claude/hooks/gate.sh run" in _denied(_hook(repo, command))


def test_a_push_of_the_tree_the_push_gate_passed_goes_through(repo: Path) -> None:
    _stamp(repo, _git(repo, "rev-parse", "HEAD^{tree}"), "extended")
    assert _hook(repo, "git push -u origin feature") == ""


def test_a_commit_hook_pass_does_not_stand_in_for_the_push_gate(repo: Path) -> None:
    _stamp(repo, _git(repo, "rev-parse", "HEAD^{tree}"), "development")
    assert "gate.sh run" in _denied(_hook(repo, "git push"))


def test_a_stamp_of_another_tree_is_refused(repo: Path) -> None:
    _stamp(repo, _git(repo, "rev-parse", "HEAD^{tree}"), "extended")
    (repo / "src/nanopnp/__init__.py").write_text("x = 1\n", encoding="utf-8")
    _git(repo, "commit", "-qam", "later")
    assert "gate.sh run" in _denied(_hook(repo, "git push"))


@pytest.mark.parametrize(
    "command",
    ["git push --no-verify", "git push origin v0.5.0-alpha.9", "git push --tags", "git status"],
    ids=["no-verify", "one-tag", "all-tags", "not-a-push"],
)
def test_the_escape_a_tag_push_and_other_commands_pass_unstamped(repo: Path, command: str) -> None:
    assert _hook(repo, command) == ""


@pytest.mark.parametrize(
    "command",
    [
        'git commit --no-verify -m "docs: the guard refuses git push without a stamp"',
        "echo 'run git push once the gate has passed'",
        'gh pr create --title t --body "Gate first, then git push -u origin x"',
        "git commit --no-verify -F - <<'EOF'\nfix: x\n\nthe guard doesn't pass git push\nEOF",
        "git commit --no-verify -m \"$(cat <<'EOF'\nfix: it's time to git push\nEOF\n)\"",
        "git commit --no-verify -m $'it\\'s a git push mention'",
    ],
    ids=["message", "echo", "pull-request-body", "heredoc", "command-substitution", "ansi-c"],
)
def test_a_command_that_only_names_a_push_is_not_a_push(repo: Path, command: str) -> None:
    """A commit message or a pull request body that says ``git push`` is text, not a push.

    ``--no-verify`` on the commit never reaches the guard, and ``gh`` has no such flag, so
    refusing these would leave no way to write the words.
    """
    assert _hook(repo, command) == ""


@pytest.mark.parametrize(
    "command",
    [
        "bash -c 'git push origin feature'",
        'sh -lc "git push -u origin feature"',
        "(git push)",
        'echo "git push" && git push origin feature',
        "cat <<EOF\nit's here\nEOF\ngit push",
    ],
    ids=["bash-c", "sh-lc", "subshell", "after-a-mention", "after-a-heredoc"],
)
def test_a_push_in_a_shell_string_or_beside_a_mention_is_still_refused(
    repo: Path, command: str
) -> None:
    assert ".claude/hooks/gate.sh run" in _denied(_hook(repo, command))

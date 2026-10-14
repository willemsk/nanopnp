"""The commit hook, gate script and session-start hook, run on temporary repositories."""

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


def _run(repo: Path) -> subprocess.CompletedProcess[str]:
    assert _BASH is not None
    return subprocess.run(
        [_BASH, str(_GATE), "run"], cwd=repo, capture_output=True, text=True, timeout=60
    )


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
    main, worktree = worktree_pair
    session_dir = worktree if session == "worktree" else worktree.parent
    output = json.loads(_hook(main, session_dir, command))["hookSpecificOutput"]
    assert output["permissionDecision"] == "deny"
    assert "fake uv refused" in output["permissionDecisionReason"]


def test_gate_hook_follows_a_cd_before_the_commit(worktree_pair: tuple[Path, Path]) -> None:
    main, worktree = worktree_pair
    decision = json.loads(_hook(main, main, f"cd {worktree} && git add -A && git commit -m x"))
    assert decision["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_gate_hook_still_lets_a_stamped_tree_through(worktree_pair: tuple[Path, Path]) -> None:
    main, _ = worktree_pair
    assert _hook(main, main, "git commit -m 'edit'") == ""


def test_gate_run_does_not_take_a_development_pass_for_its_own(
    worktree_pair: tuple[Path, Path],
) -> None:
    main, _ = worktree_pair
    result = _run(main)
    assert result.returncode != 0
    assert "already passed" not in result.stdout


def test_gate_run_on_a_clean_tree_runs_the_extended_tests_on_unpushed_code(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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

    result = _run(repo)
    assert result.returncode == 0, result.stderr
    ran = calls.read_text(encoding="utf-8").splitlines()
    assert any("pytest" in call and "--extended" in call for call in ran), ran
    stamp = Path(_git(repo, "rev-parse", "--absolute-git-dir")) / "nanopnp-gate.pass"
    tree, selection = stamp.read_text(encoding="utf-8").splitlines()[-1].split()
    assert (tree, selection) == (_git(repo, "rev-parse", "HEAD^{tree}"), "extended")


def test_gate_run_on_an_already_pushed_branch_still_runs_the_extended_tests(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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

    result = _run(repo)
    assert result.returncode == 0, result.stderr
    ran = calls.read_text(encoding="utf-8").splitlines()
    assert any("pytest" in call and "--extended" in call for call in ran), ran


_PROSE_ONLY = Path(__file__).resolve().parents[2] / ".github/scripts/prose-only.sh"


# VER-63
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
        (".claude/agents/physics-reviewer.md", False),
        (".claude/skills/wp-ship/SKILL.md", False),
        (".claude/rules/python.md", False),
        ("docs/plans/wp43-development-loop.md", False),
        ("docs/plans/notes/sketch.md", False),
    ],
)
def test_prose_only_reads_a_findings_log_as_not_prose(path: str, prose: bool) -> None:
    assert _BASH is not None
    result = subprocess.run(
        [_BASH, str(_PROSE_ONLY)], input=f"{path}\n", capture_output=True, text=True, timeout=10
    )
    assert result.returncode == (0 if prose else 1)


# VER-68
@pytest.mark.parametrize(
    ("path", "text", "prose"),
    [
        ("knowledge/index.md", "x\n", False),
        ("CHANGELOG.md", "see `knowledge/index.md`\n", False),
        ("README.md", "see `knowledge/` too\n", False),
        ("README.md", "no citation\n", True),
        ("deleted.md", None, True),
    ],
)
def test_prose_only_reads_a_citing_markdown_file_as_not_prose(
    tmp_path: Path, path: str, text: str | None, prose: bool
) -> None:
    assert _BASH is not None
    if text is not None:
        (tmp_path / path).parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / path).write_text(text, encoding="utf-8")
    result = subprocess.run(
        [_BASH, str(_PROSE_ONLY)],
        input=f"{path}\n",
        capture_output=True,
        text=True,
        timeout=10,
        cwd=tmp_path,
    )
    assert result.returncode == (0 if prose else 1)


def _branch_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, changed: str) -> Path:
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


def _uv_calls(calls: Path) -> list[str]:
    return [line.split("|", 1)[1] for line in calls.read_text(encoding="utf-8").splitlines()]


def test_gate_run_passes_extended_without_coverage_and_requires_gmsh(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _branch_repo(tmp_path, monkeypatch, "src/nanopnp/code.py")
    calls = _recording_uv(tmp_path, monkeypatch)
    result = _run(repo)
    assert result.returncode == 0, result.stderr
    ran = calls.read_text(encoding="utf-8").splitlines()
    tests = [call for call in ran if "pytest" in call and "--extended" in call]
    assert len(tests) == 1, ran
    assert tests[0].startswith("1|")
    assert "-rsfE" in tests[0].split()
    assert not any("--cov" in call or "diff-cover" in call for call in ran), ran


def test_gate_commit_runs_the_five_steps_in_order_and_stops_at_the_first_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if shutil.which("jq") is None:
        pytest.skip("the gate hook reads its payload with jq")
    repo = _branch_repo(tmp_path, monkeypatch, "src/nanopnp/other.py")
    (repo / "src/nanopnp/other.py").write_text("x = 2\n", encoding="utf-8")
    calls = _recording_uv(tmp_path, monkeypatch)
    assert _hook(repo, repo, "git commit -am x").count("gate: passed") == 1
    ran = _uv_calls(calls)
    assert [call.split()[0:3] for call in ran[:4]] == [
        ["lock", "--check"],
        ["run", "ruff", "check"],
        ["run", "ruff", "format"],
        ["run", "mypy", "src/"],
    ]
    assert ran[4].startswith("run pytest") and "tier1 and not slow" in ran[4]
    assert "--extended" not in ran[4]
    assert "test_gui_widgets.py" in ran[5] and "-n" not in ran[5].split()

    calls.unlink()
    (repo / "src/nanopnp/other.py").write_text("x = 3\n", encoding="utf-8")
    (tmp_path / "bin/uv").write_text(
        f'#!/bin/sh\necho "x|$*" >> "{calls}"\n'
        'case "$*" in *mypy*) echo bad types; exit 1;; esac\n',
        encoding="utf-8",
    )
    decision = json.loads(_hook(repo, repo, "git commit -am y"))["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"
    assert "mypy" in decision["permissionDecisionReason"]
    assert "bad types" in decision["permissionDecisionReason"]
    assert not any("pytest" in call for call in _uv_calls(calls))


def test_gate_commit_keeps_the_gui_file_out_of_the_parallel_call(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if shutil.which("jq") is None:
        pytest.skip("the gate hook reads its payload with jq")
    repo = _branch_repo(tmp_path, monkeypatch, "src/nanopnp/other.py")
    (repo / "src/nanopnp/other.py").write_text("x = 2\n", encoding="utf-8")
    calls = _recording_uv(tmp_path, monkeypatch)
    _hook(repo, repo, "git commit -am x")
    parallel = [call for call in _uv_calls(calls) if "--dist" in call]
    assert len(parallel) == 1
    assert "--ignore=tests/tier1/test_gui_widgets.py" in parallel[0]


def test_gate_commit_of_a_prose_only_change_runs_ruff_alone(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if shutil.which("jq") is None:
        pytest.skip("the gate hook reads its payload with jq")
    repo = _branch_repo(tmp_path, monkeypatch, "docs/x/notes.md")
    (repo / "docs/x/notes.md").write_text("more\n", encoding="utf-8")
    calls = _recording_uv(tmp_path, monkeypatch)
    _hook(repo, repo, "git commit -am x")
    assert [call.split()[1] for call in _uv_calls(calls)] == ["ruff", "ruff"]


def test_gate_commit_of_an_unchanged_tree_is_not_rerun(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if shutil.which("jq") is None:
        pytest.skip("the gate hook reads its payload with jq")
    repo = _branch_repo(tmp_path, monkeypatch, "src/nanopnp/other.py")
    (repo / "src/nanopnp/other.py").write_text("x = 2\n", encoding="utf-8")
    calls = _recording_uv(tmp_path, monkeypatch)
    _hook(repo, repo, "git commit -am x")
    first = len(_uv_calls(calls))
    assert _hook(repo, repo, "git commit -am x") == ""
    assert len(_uv_calls(calls)) == first


def test_gate_commit_pass_keeps_the_push_gates_extended_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if shutil.which("jq") is None:
        pytest.skip("the gate hook reads its payload with jq")
    repo = _branch_repo(tmp_path, monkeypatch, "src/nanopnp/other.py")
    stamp = Path(_git(repo, "rev-parse", "--absolute-git-dir")) / "nanopnp-gate.pass"
    stamp.write_text(f"{'a' * 40} extended\n{'b' * 40} development\n", encoding="utf-8")
    (repo / "src/nanopnp/other.py").write_text("x = 2\n", encoding="utf-8")
    _recording_uv(tmp_path, monkeypatch)
    assert "gate: passed" in _hook(repo, repo, "git commit -am x")
    lines = stamp.read_text(encoding="utf-8").splitlines()
    assert lines[0] == f"{'a' * 40} extended"
    assert len(lines) == 2 and lines[1].endswith(" development") and "b" * 40 not in lines[1]


# VAL-06
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
    result = _run(repo)
    assert result.returncode == 0, result.stderr
    assert set(seen.read_text(encoding="utf-8").split()) == {required}


@pytest.mark.parametrize(
    ("changed", "content", "required"),
    [
        ("src/nanopnp/mesh/gmsh_backend.py", "y = 2\n", "1"),
        ("tests/tier1/test_mesh_gmsh.py", "y = 2\n", "1"),
        ("tests/tier2/test_mesh_backends.py", "y = 2\n", "1"),
        ("tests/tier1/test_mesh_quality.py", "def test_x(gmsh_module):\n    pass\n", "1"),
        ("tests/conftest.py", "def import_gmsh():\n    pass\n", "1"),
        ("tests/tier1/test_mesh_quality.py", "y = 2\n", "unset"),
        ("src/nanopnp/core/units.py", "y = 2\n", "unset"),
    ],
)
def test_gate_hook_requires_gmsh_only_for_a_change_to_gmsh(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, changed: str, content: str, required: str
) -> None:
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
    repo = _branch_repo(tmp_path, monkeypatch, "src/nanopnp/code.py")
    failing = (
        'case "$*" in *--extended*) echo "Failed: NANOPNP_REQUIRE_GMSH=1 and gmsh does not '
        'import: OSError: libGLU.so.1"; exit 1;; esac\n'
    )
    _recording_uv(tmp_path, monkeypatch, failing)
    result = _run(repo)
    assert result.returncode != 0
    assert "libGLU.so.1" in result.stderr
    assert "apt-get install -y --no-install-recommends libglu1-mesa" in result.stderr


def test_gate_hook_requires_gmsh_for_a_tracked_change_beside_an_untracked_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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


def test_gate_run_without_a_merge_base_runs_the_whole_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _branch_repo(tmp_path, monkeypatch, "docs/x/notes.md")
    _git(repo, "branch", "-m", "main", "trunk")
    calls = _recording_uv(tmp_path, monkeypatch)
    assert _run(repo).returncode == 0
    assert any("--extended" in call for call in _uv_calls(calls))


def _log(repo: Path) -> list[str]:
    path = Path(_git(repo, "rev-parse", "--absolute-git-dir")) / "nanopnp-gate.log"
    return path.read_text(encoding="utf-8").splitlines()


def test_gate_run_stamps_extended_only_on_a_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _branch_repo(tmp_path, monkeypatch, "src/nanopnp/code.py")
    stamp = Path(_git(repo, "rev-parse", "--absolute-git-dir")) / "nanopnp-gate.pass"
    _recording_uv(tmp_path, monkeypatch, 'case "$*" in *--extended*) exit 1;; esac\n')
    assert _run(repo).returncode == 1
    assert not stamp.exists()
    (tmp_path / "bin/uv").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    assert _run(repo).returncode == 0
    assert stamp.read_text(encoding="utf-8").split() == [
        _git(repo, "rev-parse", "HEAD^{tree}"),
        "extended",
    ]


def test_gate_run_stamps_nothing_when_the_tree_changes_while_it_runs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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
    repo = _branch_repo(tmp_path, monkeypatch, "src/nanopnp/code.py")
    _recording_uv(tmp_path, monkeypatch)
    common = Path(_git(repo, "rev-parse", "--path-format=absolute", "--git-common-dir"))
    lock = common / "nanopnp-gate.lock"
    lock.mkdir()
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
    repo = _branch_repo(tmp_path, monkeypatch, "src/nanopnp/code.py")
    _recording_uv(tmp_path, monkeypatch)
    result = _run(repo)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().count("\n") == 0
    assert result.stdout.startswith("gate: passed")


def test_gate_run_failure_names_the_push_gate_and_offers_no_commit_escape(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = _branch_repo(tmp_path, monkeypatch, "src/nanopnp/code.py")
    _recording_uv(tmp_path, monkeypatch, 'case "$*" in *mypy*) echo bad types; exit 1;; esac\n')
    result = _run(repo)
    assert result.returncode == 1
    assert "bad types" in result.stderr
    assert "gate.sh run again" in result.stderr
    assert "commit" not in result.stderr
    assert "--no-verify" not in result.stderr


@pytest.mark.parametrize("argument", ["map", "runn"])
def test_gate_refuses_an_argument_it_does_not_know(argument: str) -> None:
    assert _BASH is not None
    result = subprocess.run(
        [_BASH, str(_GATE), argument], input="", capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 2
    assert argument in result.stderr


def test_gate_hook_refuses_a_push_in_the_command_that_commits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
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
